"""A trilha de auditoria do ACADEMUS — escrita encadeada e verificacao.

`02` §4 e `05` §7. O mecanismo esta em `alembic/versions/0004_trilha_de_auditoria.py`
— tabela, role, `REVOKE`, trigger; aqui esta o que a aplicacao faz com ele.

A CADEIA USA A PRIMITIVA DO CORE, E NAO UMA COPIA — D3
--------------------------------------------------------
`range_core.events.integrity` ja encadeava por SHA-256 sobre forma canonica mais
hash anterior, para o event store. Duas implementacoes do mesmo encadeamento e a
duplicacao de mecanismo que a Fase 1 pagou para desfazer, entao a peca 3 EXTRAIU
a primitiva — `canonical_json`, `chained_hash`, `verify_hash_chain` — e as duas
camadas a usam.

**O que NAO atravessa a fronteira e a semantica.** O core nao sabe o que e uma
alteracao de nota, nao sabe o que e `within_window` e nao conhece as cinco
categorias de `02` §4.1. Isso e adapter, e mora aqui. `domains/` importa
`range-core/`; o contrario e o invariante 1, e ha teste de AST.

A TRILHA NAO E O EVENT STORE, e a distincao decide o esquema
--------------------------------------------------------------
`01` §4 poe as duas em camadas diferentes. A trilha e artefato de **negocio** —
e o que a equipe azul investiga, e o que a Linha B povoa. O event store e a
maquina de exercicio, com `truth_layer` e envelope de `09` §1.1. Uma linha de
trilha nao tem `truth_layer`, nao tem `simulation_epoch` e nao e rebobinada por
rollback: `01` §4.3 diz que reverter business state geraria "evento na trilha de
auditoria sem correspondente no banco", que e o estado impossivel que aquela
secao existe para impedir.

A ESCRITA E NA MESMA TRANSACAO DO FATO — D4
---------------------------------------------
`registrar` recebe a **sessao aberta** de quem esta escrevendo o fato, e nao um
engine. Ou as duas linhas existem, ou nenhuma. Trilha como efeito colateral
depois do `commit` produz, na primeira falha, nota sem registro — e a sala
descobre isso investigando, que e o pior lugar possivel.

A SERIALIZACAO, E POR QUE ELA E TRAVA DE TABELA
------------------------------------------------
`previous_hash` e o `row_hash` da linha imediatamente anterior. Duas transacoes
concorrentes que lessem a mesma "ultima linha" produziriam duas linhas com o
mesmo `previous_hash` e a mesma `sequence` — a segunda falharia pela chave
primaria, o que ja e correto, mas ao custo de um erro que o participante veria.

`pg_advisory_xact_lock` sobre um identificador fixo serializa ANTES da leitura,
e e liberada no fim da transacao sem `unlock` explicito. As alternativas medidas
em desenho: `SELECT ... FOR UPDATE` na ultima linha nao protege contra duas
transacoes que ainda nao tem linha anterior nenhuma (tabela vazia, nada a
travar), e `LOCK TABLE ... IN EXCLUSIVE MODE` bloquearia leitura concorrente da
verificacao — que e rota de exercicio.

O CUSTO ESTA DECLARADO: a escrita da trilha e serial por construcao. Para o
volume desta aplicacao — alteracao de nota, emissao de diploma — isso e o certo;
se um dia houver categoria de alto volume, a saida e particionar a cadeia por
categoria, e ai sao N cadeias com N verificacoes, nao uma cadeia mais rapida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from range_core.events.integrity import (
    FIRST_SEQUENCE,
    GENESIS_HASH,
    ChainBroken,
    canonical_json,
    chained_hash,
    verify_hash_chain,
)

#: AS CINCO CATEGORIAS DE `02` §4.1, e a quinta nao tem produtor.
#:
#: `DECLARACAO_DE_EXERCICIO` existe e nada a escreve. Isso e a **P5-2**:
#: declarada com destinatario em vez de omitida, porque categoria que some do
#: codigo some da revisao — e `09` §4 chama "o `event_type` que nunca dispara" de
#: a falha mais cara possivel.
#:
#: A REDACAO ANTERIOR DIZIA "nada a escreve ate a Fase 6, que e onde nascem as
#: acoes `declare_*`", e envelheceu: as nove acoes nasceram na peca 3 da Fase 6 e
#: NAO escrevem aqui. A decisao daquela peca foi que declaracao e ato de
#: participante, mora no nucleo com RBAC por persona (`01` §6), e vai para o
#: event store; `audit_trail` e mecanismo de DOMINIO, sobre as entidades do
#: Academus. O gatilho apontava para o lugar errado, e nao para o momento errado.
#:
#: MIGRADA PARA A FASE 7, com gatilho novo: a primeira acao de participante que
#: ALTERE ESTADO DE DOMINIO — e ai que esta trilha tem o que registrar.
#: `docs/progress/fase_7.md`.
ALTERACAO_DE_NOTA = "grade_change"
EMISSAO_DE_DIPLOMA = "diploma_issue"
BANCO_DE_QUESTOES = "exam_bank_access"
PESQUISA_ACADEMICA = "research_access"
DECLARACAO_DE_EXERCICIO = "exercise_declaration"

CATEGORIAS = (
    ALTERACAO_DE_NOTA,
    EMISSAO_DE_DIPLOMA,
    BANCO_DE_QUESTOES,
    PESQUISA_ACADEMICA,
    DECLARACAO_DE_EXERCICIO,
)

#: A ROLE DE `02` §4, assumida DENTRO da transacao que escreve.
#:
#: `SET LOCAL` e nao `SET`: `LOCAL` volta sozinho no fim da transacao, e sem ele
#: a conexao voltaria ao pool com a role trocada — toda consulta seguinte daquela
#: conexao correria restrita, e o defeito apareceria numa rota que nao tem nada a
#: ver com trilha.
ROLE_DA_APLICACAO = "academus_app"

#: O identificador da trava. Constante arbitraria e estavel: duas transacoes que
#: escrevem na trilha precisam pedir a MESMA, e qualquer outro uso de advisory
#: lock neste banco precisa usar outra.
TRAVA_DA_TRILHA = 0x41554449  # "AUDI"


@dataclass(frozen=True, slots=True)
class Registro:
    """Uma linha de trilha, antes de ter sequencia e hash.

    Os campos sao os de `02` §4.1. `within_window` e `authorization_id` sao
    opcionais porque so a alteracao de nota os tem — emissao de diploma nao
    acontece dentro de janela nenhuma.
    """

    category: str
    actor_user_id: str
    source_ip: str
    object_type: str
    object_id: str
    occurred_at: datetime
    payload: dict
    user_agent: str | None = None
    within_window: bool | None = None
    authorization_id: str | None = None

    def forma_canonica(self, sequence: int) -> str:
        """O material hasheado. **A `sequence` ENTRA, e o `previous_hash` nao.**

        A `sequence` entra porque, sem ela, duas linhas identicas em conteudo —
        duas consultas ao banco de questoes pelo mesmo usuario no mesmo segundo —
        produziriam o mesmo canonico; nao e falha de seguranca, mas apaga a
        distincao entre "duas linhas" e "uma linha duplicada" para quem le o
        hash.

        O `previous_hash` fica de fora porque ele entra no `chained_hash`, e
        contar duas vezes nao acrescenta nada.

        `recorded_at` TAMBEM fica de fora, e essa e a exclusao que precisa de
        motivo: ele e atribuido pelo banco no instante da escrita, e incluir um
        valor que a verificacao teria de reler exatamente igual torna a cadeia
        refem da precisao de timestamp do driver. `occurred_at`, que e o fato,
        entra.
        """
        return canonical_json(
            {
                "sequence": sequence,
                "category": self.category,
                "actor_user_id": self.actor_user_id,
                "source_ip": self.source_ip,
                "user_agent": self.user_agent,
                "object_type": self.object_type,
                "object_id": self.object_id,
                "occurred_at": self.occurred_at.isoformat(),
                "payload": self.payload,
                "within_window": self.within_window,
                "authorization_id": self.authorization_id,
            }
        )


@dataclass(frozen=True, slots=True)
class Quebra:
    """O que a verificacao devolve quando a cadeia nao fecha."""

    sequence: int | None
    motivo: str


@dataclass(frozen=True, slots=True)
class Resultado:
    """O veredito da verificacao. `06` T7 exige a POSICAO exata da quebra."""

    linhas: int
    integra: bool
    quebra: Quebra | None = field(default=None)


def dentro_da_janela(sessao: Session, semestre: str, quando: date) -> bool | None:
    """`within_window` de `02` §2 — contra a JANELA DE RETIFICACAO do semestre.

    Devolve `None` quando o semestre nao existe no calendario: nao saber e
    diferente de "fora", e gravar `False` por ausencia de calendario poria um
    caso na Linha B por defeito de dado. `02` §3 e explicito sobre o custo de
    "fora da janela = fraude".
    """
    linha = sessao.execute(
        text(
            "SELECT rectification_start, rectification_end "
            "FROM academic_calendar WHERE semester = :s"
        ),
        {"s": semestre},
    ).first()
    if linha is None:
        return None
    return linha[0] <= quando <= linha[1]


def registrar(sessao: Session, registro: Registro) -> int:
    """Grava uma linha encadeada. **Usa a sessao de quem escreve o fato.**

    Devolve a `sequence` atribuida. Levanta se a categoria nao for do catalogo de
    `02` §4.1 — categoria digitada errada nunca seria consultada, e ninguem
    perceberia ate o exercicio.
    """
    if registro.category not in CATEGORIAS:
        raise ValueError(
            f"categoria {registro.category!r} nao e de `02` §4.1. As cinco estao "
            f"em `CATEGORIAS`: {', '.join(CATEGORIAS)}"
        )

    # A ORDEM IMPORTA: trava, depois le, depois escreve. Ler antes de travar e
    # exatamente a corrida que a trava existe para fechar.
    sessao.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": TRAVA_DA_TRILHA})

    # A ROLE ASSUMIDA DEPOIS DA TRAVA e antes da escrita. `SET LOCAL` volta
    # sozinho no fim da transacao.
    sessao.execute(text(f"SET LOCAL ROLE {ROLE_DA_APLICACAO}"))

    ultima = sessao.execute(
        text("SELECT sequence, row_hash FROM audit_trail ORDER BY sequence DESC LIMIT 1")
    ).first()
    sequence = FIRST_SEQUENCE if ultima is None else ultima[0] + 1
    previous_hash = GENESIS_HASH if ultima is None else ultima[1]

    sessao.execute(
        text(
            "INSERT INTO audit_trail ("
            "  sequence, category, actor_user_id, source_ip, user_agent,"
            "  occurred_at, recorded_at, object_type, object_id, payload,"
            "  within_window, authorization_id, previous_hash, row_hash"
            ") VALUES ("
            "  :sequence, :category, :actor, :ip, :ua,"
            "  :occurred_at, now(), :object_type, :object_id, :payload,"
            "  :within_window, :authorization_id, :previous_hash, :row_hash"
            ")"
        ),
        {
            "sequence": sequence,
            "category": registro.category,
            "actor": registro.actor_user_id,
            "ip": registro.source_ip,
            "ua": registro.user_agent,
            "occurred_at": registro.occurred_at,
            "object_type": registro.object_type,
            "object_id": registro.object_id,
            "payload": canonical_json(registro.payload),
            "within_window": registro.within_window,
            "authorization_id": registro.authorization_id,
            "previous_hash": previous_hash,
            "row_hash": chained_hash(registro.forma_canonica(sequence), previous_hash),
        },
    )
    return sequence


def verificar(sessao: Session) -> Resultado:
    """Percorre a trilha e reporta a PRIMEIRA quebra, com a posicao.

    Le em ordem de sequencia e recomputa cada `row_hash`. Nao levanta: devolve
    `Resultado`, porque quem chama e uma rota HTTP e a quebra e a resposta
    esperada da rota — nao um erro dela. `ChainBroken` continua sendo a forma
    do core, e e traduzida aqui.

    TRILHA VAZIA E INTEGRA, e isso e decisao: nao ha nada que nao feche. O
    contrario — vazia reprovar — faria toda base recem-migrada parecer
    adulterada, e alarme que toca sempre e alarme que se desliga.
    """
    linhas = sessao.execute(
        text(
            "SELECT sequence, category, actor_user_id, source_ip, user_agent,"
            "       occurred_at, object_type, object_id, payload, within_window,"
            "       authorization_id, previous_hash, row_hash "
            "FROM audit_trail ORDER BY sequence"
        )
    ).all()

    materiais = []
    for linha in linhas:
        registro = Registro(
            category=linha.category,
            actor_user_id=linha.actor_user_id,
            source_ip=linha.source_ip,
            user_agent=linha.user_agent,
            object_type=linha.object_type,
            object_id=linha.object_id,
            occurred_at=linha.occurred_at,
            payload=linha.payload,
            within_window=linha.within_window,
            authorization_id=linha.authorization_id,
        )
        materiais.append(
            (
                linha.sequence,
                linha.previous_hash,
                linha.row_hash,
                registro.forma_canonica(linha.sequence),
            )
        )

    try:
        verify_hash_chain(materiais)
    except ChainBroken as quebra:
        # A POSICAO SAI DA MENSAGEM DO CORE, e nao de uma segunda contagem aqui:
        # duas fontes para o mesmo numero divergem, e a que diverge em silencio e
        # sempre a que ninguem le.
        return Resultado(
            linhas=len(materiais),
            integra=False,
            quebra=Quebra(sequence=_posicao(str(quebra)), motivo=str(quebra)),
        )
    return Resultado(linhas=len(materiais), integra=True)


def _posicao(mensagem: str) -> int | None:
    """A `sequence` citada na mensagem do core, para a resposta ter campo proprio.

    Extrair da mensagem parece fragil e e a alternativa menos fragil: a outra e
    recontar aqui, e ai a posicao reportada pode discordar da explicada.
    """
    for palavra in mensagem.replace(":", " ").replace(",", " ").split():
        if palavra.isdigit():
            return int(palavra)
    return None
