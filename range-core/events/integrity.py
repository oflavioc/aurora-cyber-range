"""Deteccao de reescrita no event store — a garantia, nao o mecanismo.

O QUE ESTA PECA E, E O QUE ELA NAO E
------------------------------------
`02_DOMAIN_ACADEMUS.md` §4 e `05_SECURITY_REQUIREMENTS.md` §7 exigem, para a
trilha de auditoria, role `INSERT`-only, `REVOKE UPDATE/DELETE` e trigger de
bloqueio. Isso e **Fase 5**, e antecipa-lo aqui seria duplicacao: dois lugares
definindo a mesma coisa, e o segundo divergindo.

Mas append-only nao pode ser, ate la, disciplina do codigo Python: qualquer um
com a connection string reescreve historia e **nada acusa**. O que esta fase
entrega e a outra metade — **deteccao**. A tabela guarda o que torna reescrita
visivel, e a leitura confere.

E deteccao continua util DEPOIS do `REVOKE`, e nao vira redundancia: `REVOKE`
nao protege contra quem tem privilegio, e migracao, restauracao de backup e
acesso administrativo continuam existindo.

O `REVOKE` CHEGOU — peca 3 da Fase 5, e a previsao acima se cumpriu
--------------------------------------------------------------------
`alembic/versions/0004_trilha_de_auditoria.py` traz a tabela, a role
`INSERT`-only, o `REVOKE` e o trigger; `domains/academus/audit/trilha.py` escreve
e verifica. A frase de cima nao envelheceu: os dois mecanismos cobrem coisas
diferentes, e a tabela da D13 no registro da Fase 5 diz qual cobre o que.

**A duplicacao foi evitada extraindo a primitiva, e nao copiando o modulo.**
`canonical_json`, `chained_hash` e `verify_hash_chain` sao genericos sobre mapa e
texto; `canonical_form`, `row_hash` e `verify_chain` continuam sendo a leitura de
EVENTO e delegam para eles. A trilha usa os tres primeiros e nao conhece
`Event` — e o adapter importa o core, nunca o contrario.

COMO
----
Encadeamento por hash, mais sequencia sem buracos. Cada linha guarda:

- `sequence` — inteiro contiguo, atribuido pela aplicacao;
- `previous_hash` — o `row_hash` da linha anterior;
- `row_hash` — SHA-256 sobre a forma canonica do envelope mais `previous_hash`.

A verificacao recomputa cada `row_hash` e confere o encadeamento e a
contiguidade. Modificacao de qualquer campo do envelope quebra o hash daquela
linha; remocao ou insercao no meio quebra o encadeamento **e** a sequencia.

A SEQUENCIA E ATRIBUIDA PELA APLICACAO, e nao por `BIGSERIAL`. Sequencia de
banco consome numero em transacao que faz rollback, e o buraco resultante seria
alarme falso — deteccao que grita sem defeito e deteccao que se aprende a
ignorar.

OS DOIS LIMITES, DECLARADOS
---------------------------
**Truncamento da cauda nao e detectavel.** Apagar as ultimas N linhas deixa uma
cadeia integra e uma sequencia contigua. Nenhum mecanismo interno a tabela pega
isso: seria preciso ancora externa — hash publicado fora do banco, ou contagem
assinada em outro lugar. Nao ha, e a Fase 2 nao a inventa.

**Reescrita completa por quem tem o codigo tambem nao.** Quem recomputa a cadeia
inteira produz um store integro e falso. A cadeia detecta adulteracao de quem
NAO recomputa — que e o caso realista de acidente, migracao malfeita e edicao
manual —, nao adversario com privilegio e conhecimento.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from range_core.events.envelope import Event

#: `previous_hash` da primeira linha. Sessenta e quatro zeros: nao e hash de
#: nada, e nenhum evento pode produzi-lo por acaso.
GENESIS_HASH = "0" * 64

#: A primeira sequencia. Comeca em 1 para que ausencia de linha seja distinta de
#: "linha zero" em qualquer leitura descuidada.
FIRST_SEQUENCE = 1


class ChainBroken(Exception):
    """A cadeia nao fecha: houve reescrita, remocao ou insercao.

    Recusa alta e deliberada. Um store adulterado que continua respondendo
    produz projecao plausivel e falsa — e a projecao alimenta o AAR, que e onde
    a mentira teria consequencia.
    """


def canonical_json(conteudo: Mapping[str, object]) -> str:
    """A FORMA CANONICA GENERICA: JSON ordenado, sem espaco insignificante.

    Extraida na peca 3 da Fase 5, e a extracao e a D3 daquele registro. A trilha
    de auditoria de `02` §4 exige `row_hash = SHA256(prev_hash || payload
    canonico)` — a MESMA construcao que este modulo ja fazia para o event store.
    Duas implementacoes de encadeamento por hash no mesmo repositorio e a
    duplicacao de mecanismo que a Fase 1 pagou para desfazer.

    O QUE ATRAVESSA A FRONTEIRA E A PRIMITIVA, e nao a semantica. Esta funcao nao
    sabe o que e um evento nem o que e uma linha de trilha: recebe um mapa e
    devolve texto. A tabela, o trigger, a role e os campos de `02` §4.1 sao do
    adapter, e `domains/` importa `range-core/` — nunca o contrario, que e o
    invariante 1.

    `ensure_ascii=False` porque o dado e em portugues e o hash e sobre bytes
    UTF-8: escapar acento mudaria o material hasheado sem mudar o conteudo, e
    duas serializacoes do mesmo fato produziriam hashes diferentes.
    """
    return json.dumps(
        conteudo, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def chained_hash(canonico: str, previous_hash: str) -> str:
    """SHA-256 de `previous_hash` encadeado a uma forma canonica ja pronta.

    A QUEBRA DE LINHA ENTRE OS DOIS NAO E ENFEITE: sem separador, um
    `previous_hash` que terminasse com o comeco do canonico produziria o mesmo
    material que outro par deslocado. Com `\\n` — que nao ocorre no hexadecimal
    do hash nem no JSON compacto — a concatenacao e inequivoca.
    """
    return hashlib.sha256(f"{previous_hash}\n{canonico}".encode("utf-8")).hexdigest()


def verify_hash_chain(rows: Sequence[tuple[int, str, str, str]]) -> None:
    """Confere sequencia, encadeamento e hash sobre formas canonicas.

    `rows` e `(sequence, previous_hash, row_hash, forma_canonica)` na ordem de
    leitura. Levanta `ChainBroken` na PRIMEIRA divergencia, nomeando a posicao —
    `06` T7 exige que a verificacao reporte onde a cadeia quebrou, e recusa sem
    posicao nao e operavel.

    Generica pelo mesmo motivo de `canonical_json`: quem chama sabe o que a linha
    significa; isto so sabe que ela deveria fechar.
    """
    esperado_anterior = GENESIS_HASH
    esperada_sequencia = FIRST_SEQUENCE

    for sequencia, anterior, gravado, canonico in rows:
        if sequencia != esperada_sequencia:
            raise ChainBroken(
                f"sequencia {sequencia} onde se esperava {esperada_sequencia}: "
                "ha buraco ou reordenacao, e a tabela nao e mais append-only"
            )
        if anterior != esperado_anterior:
            raise ChainBroken(
                f"sequencia {sequencia}: `previous_hash` nao aponta para a linha "
                "anterior — houve remocao ou insercao no meio"
            )
        if chained_hash(canonico, anterior) != gravado:
            raise ChainBroken(
                f"sequencia {sequencia}: o hash gravado nao corresponde ao "
                "conteudo — a linha foi modificada depois de escrita"
            )
        esperado_anterior = gravado
        esperada_sequencia += 1


def canonical_form(event: Event) -> str:
    """A forma canonica do envelope, para hashear.

    JSON com chaves ordenadas e sem espaco insignificante, sobre os campos do
    envelope e nada mais. `sequence`, `previous_hash` e `row_hash` NAO entram:
    sao metadados de ARMAZENAMENTO, e nao do evento — o envelope e o de
    `09` §1.1, e acrescentar campo a ele exigiria mudar o contrato.
    """
    return canonical_json(
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "truth_layer": event.truth_layer,
            "producer": event.producer,
            "exercise_time": event.exercise_time,
            "exercise_timestamp": event.exercise_timestamp,
            "wall_timestamp": event.wall_timestamp,
            "clock_multiplier": event.clock_multiplier,
            "simulation_epoch": event.simulation_epoch,
            "actor_id": event.actor_id,
            "persona": event.persona,
            "correlation": {
                "scenario_id": event.correlation.scenario_id,
                "inject_id": event.correlation.inject_id,
                "causation_id": event.correlation.causation_id,
                "fact_id": event.correlation.fact_id,
            },
            "payload": event.payload,
        }
    )


def row_hash(event: Event, previous_hash: str) -> str:
    """SHA-256 da forma canonica encadeada ao hash anterior."""
    return chained_hash(canonical_form(event), previous_hash)


def verify_chain(rows: Sequence[tuple[int, str, str, Event]]) -> None:
    """Confere a cadeia do EVENT STORE — `(sequence, previous_hash, row_hash, evento)`.

    Delega para `verify_hash_chain` depois de reduzir cada evento a sua forma
    canonica. A reducao e o que este modulo sabe e o generico nao: qual e o
    envelope de `09` §1.1, e quais dos campos gravados sao metadados de
    ARMAZENAMENTO e por isso ficam fora do material hasheado.
    """
    verify_hash_chain(
        [
            (seq, anterior, gravado, canonical_form(evento))
            for seq, anterior, gravado, evento in rows
        ]
    )
