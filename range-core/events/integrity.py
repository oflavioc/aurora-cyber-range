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
from collections.abc import Sequence

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


def canonical_form(event: Event) -> str:
    """A forma canonica do envelope, para hashear.

    JSON com chaves ordenadas e sem espaco insignificante, sobre os campos do
    envelope e nada mais. `sequence`, `previous_hash` e `row_hash` NAO entram:
    sao metadados de ARMAZENAMENTO, e nao do evento — o envelope e o de
    `09` §1.1, e acrescentar campo a ele exigiria mudar o contrato.
    """
    return json.dumps(
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
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def row_hash(event: Event, previous_hash: str) -> str:
    """SHA-256 da forma canonica encadeada ao hash anterior."""
    material = f"{previous_hash}\n{canonical_form(event)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def verify_chain(rows: Sequence[tuple[int, str, str, Event]]) -> None:
    """Confere sequencia, encadeamento e hash de cada linha.

    `rows` e `(sequence, previous_hash, row_hash, event)` na ordem de leitura.
    Levanta `ChainBroken` na primeira divergencia, nomeando a POSICAO — sem a
    posicao a recusa nao e operavel, e `06` T7 exige que a verificacao reporte
    onde a cadeia quebrou.
    """
    esperado_anterior = GENESIS_HASH
    esperada_sequencia = FIRST_SEQUENCE

    for sequencia, anterior, gravado, event in rows:
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
        recomputado = row_hash(event, anterior)
        if recomputado != gravado:
            raise ChainBroken(
                f"sequencia {sequencia}, evento {event.event_id}: o hash gravado "
                "nao corresponde ao conteudo — a linha foi modificada depois de "
                "escrita"
            )
        esperado_anterior = gravado
        esperada_sequencia += 1
