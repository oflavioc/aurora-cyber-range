"""O computador do lado da DECLARACAO — as seis siglas que a equipe move.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3, §3.0 e §3.4; `00_MASTER_SPEC.md` §3.2;
`09_EVENT_MODEL.md` §3.1; `06_ACCEPTANCE_TESTS.md` T10.

O QUE ELE RECEBE, E O QUE ELE NAO TEM
--------------------------------------
`InsumoDeDeclaracao`, e nada alem. **Ele nao alcanca
`verification_predicate_satisfied`**, e e por isso que nenhuma metrica simples
daqui pode ser computada a partir do veredito — o primeiro dos dois defeitos que
`00` §3.2 fecha com uma regra so.

AS SEIS, NA ORDEM DA DERIVACAO DE `03` §3.0
--------------------------------------------
Tres sao **metades de declaracao** de um par, e marcam um instante desde T0:
`TTCD`, `TTRD` e `TTID`. Tres sao **simples**, com start e stop proprios que a
tabela de §3 escreve: `TTA`, `TTT` e `TTCM`.

A ordem e a da tabela de derivacao, e nao a da conveniencia: §3.0 e o resultado
de aplicar a conjuncao de `00` §3.2 sigla a sigla, e sair dela faria a leitura
lado a lado exigir reordenacao mental.

`TTID` APLICA O PREDICADO, E NAO CONFIA NA EMISSAO
---------------------------------------------------
`03` §3.4: *"`TTID` marca o evento que COMPLETA, e nao o primeiro. O calculo e do
consumidor sobre o insumo do lado da declaracao... o par de eventos chega inteiro
ao computador, e e ele quem aplica o predicado."*

O predicado vem de `range-core/declarations/contrassinatura.py`, compartilhado
com o emissor. Escrito duas vezes seria a classe D4, e a divergencia apareceria
como `TTID` marcado num par que a emissao recusou.

**Declaracao isolada nao marca `TTID`** — a clausula herdada, o quarto negativo
de §3.4. Ela e gravada e fica registrada; a ausencia de contrassinatura e achado
do AAR, e nao erro de quem declarou. Aqui isso e consequencia do predicado, e nao
regra a parte: `completa()` e falso para quem nao tem `causation_id`.

`TTCM` E UMA POR INJECT, E POR ISSO CARREGA `referencia`
----------------------------------------------------------
O start e *"inject com `requires_response`"* e o stop e *"submissao
correspondente"*. Um exercicio tem varios, e a correspondencia e
`correlation.inject_id` — o campo de envelope que liga a resposta ao que a
exigiu. Sem a `referencia` na medida, o AAR teria uma lista de duracoes sem saber
a que cada uma responde.

O QUE ESTE MODULO NAO EXIGE, DITO
----------------------------------
`03` §3 escreve o stop de `TTT` como *"`classification_declared` com severidade e
escopo"*. O qualificador descreve o CONTEUDO do evento, e nao ha contrato de
payload para ele: `events.schema.yaml` fecha payload por `event_type` apenas em
`rollback_performed` e `inject_fired`, e cada um nasceu quando o consumidor
nasceu. Exigir as duas chaves aqui seria inventar contrato no consumidor, onde
nenhum verificador o alcanca. Quando o payload de `classification_declared` for
escrito, a exigencia entra por la — e este paragrafo e onde procurar.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from contracts.generated.events import (
    CLASSIFICATION_DECLARED,
    COMMUNICATION_SUBMITTED,
    CONTAINMENT_DECLARED,
    INCIDENT_DECLARED,
    INJECT_FIRED,
    INTEGRITY_VALIDATION_DECLARED,
    REGULATORY_NOTICE_SUBMITTED,
    SERVICE_RESTORATION_DECLARED,
)

from range_core.declarations.contrassinatura import completa
from range_core.events.envelope import Event
from range_core.metrics.epoch import (
    Congelamento,
    apenas,
    congelamentos,
    decorrido,
    epochs_em_calculo,
    instante,
    marco_zero,
)
from range_core.metrics.insumo import InsumoDeDeclaracao
from range_core.metrics.medida import Medida, nao_marcada

#: As chaves do payload de `inject_fired` — `events.schema.yaml`,
#: `inject_fired_payload`. `observable_impact` e o start de `TTA` e
#: `requires_response` o de `TTCM`.
IMPACTO_OBSERVAVEL = "observable_impact"
EXIGE_RESPOSTA = "requires_response"

#: O stop de `TTCM`. Os dois sao `state_effect` por classe e `declaration` por
#: lado — o ATO tem efeito externo (`09` §4.1), e e por isso que a folha de
#: predicado precisa da conjuncao para nao os admitir dos dois lados.
SUBMISSOES = frozenset({COMMUNICATION_SUBMITTED, REGULATORY_NOTICE_SUBMITTED})


def computa(insumo: InsumoDeDeclaracao) -> tuple[Medida, ...]:
    """As metricas do lado da declaracao, na ordem de `03` §3.0.

    Todo o consumo de epoch acontece AQUI, em codigo visivel — `00` §3.2 —, e
    passa por `epochs_em_calculo`, que aplica os QUATRO efeitos de `09` §3.1 e
    nao apenas os dois que `06` T10 nomeia.

    > **A redacao anterior afirmava os quatro efeitos como se fossem do SISTEMA,
    > e eram deste lado so.** Quando ela foi escrita, o computador da verificacao
    > lia apenas o descarte de `rehearsal` — `assessment_submitted` de epoch
    > anulada seguia alimentando o Brier, e `TTIV` marcava em linha temporal
    > rebobinada. A frase nascia verdadeira sobre este modulo e FALSA sobre a
    > propriedade que ela parecia afirmar, e foi o H1 da terceira auditoria.
    >
    > Desde ele, `epochs_em_calculo` e o criterio dos DOIS lados — e a frase
    > passou a valer no escopo em que era lida.
    """
    congelados = congelamentos(insumo.epoch)
    t_zero = marco_zero(insumo.epoch)
    eventos = apenas(insumo.eventos, epochs_em_calculo(insumo.epoch))

    incidente = _primeiro(eventos, INCIDENT_DECLARED)

    medidas = [
        _desde_t0("TTCD", _primeiro(eventos, CONTAINMENT_DECLARED), t_zero, congelados),
        _desde_t0(
            "TTRD", _primeiro(eventos, SERVICE_RESTORATION_DECLARED), t_zero, congelados
        ),
        _desde_t0("TTID", _completa_a_integridade(eventos), t_zero, congelados),
        _entre("TTA", _primeiro_com_impacto(eventos), incidente, congelados),
        _entre("TTT", incidente, _primeiro(eventos, CLASSIFICATION_DECLARED), congelados),
    ]
    medidas.extend(_todas_as_ttcm(eventos, congelados))
    return tuple(medidas)


def _primeiro(eventos: Sequence[Event], tipo: str) -> Event | None:
    """O primeiro do tipo, na ordem do exercicio.

    O PRIMEIRO, e nao o ultimo: `03` §3 mede o tempo ATE a declaracao. Redeclarar
    contencao mais tarde nao move `TTCD` — a equipe declarou quando declarou, e
    marcar a ultima faria a metrica melhorar com a repeticao.
    """
    return min(
        (e for e in eventos if e.event_type == tipo), key=instante, default=None
    )


def _primeiro_com_impacto(eventos: Sequence[Event]) -> Event | None:
    """O start de `TTA` — *"o primeiro inject com impacto observavel"*.

    A escolha e CALCULO sobre o payload, e nao recorte do montador: `00` §3.2 o
    exige por nome, e o marcador viaja em `inject_fired` desde a unidade que
    fechou a P6-2. Montador que ja entregasse "o inject certo" moveria a regra
    para fora do que o teste alcanca.
    """
    return min(
        (
            e
            for e in eventos
            if e.event_type == INJECT_FIRED and e.payload.get(IMPACTO_OBSERVAVEL) is True
        ),
        key=instante,
        default=None,
    )


def _completa_a_integridade(eventos: Sequence[Event]) -> Event | None:
    """O `integrity_validation_declared` que COMPLETA a contrassinatura.

    As anteriores sao as declaracoes de integridade **antes deste ato**, e nao o
    conjunto inteiro: a condicao (4) de `03` §3.4 — antecedente ja completado —
    enxergaria contrassinaturas futuras, e um par valido viraria invalido pelo que
    veio depois dele.

    O PRIMEIRO que completa, se houver mais de um par: `TTID` marca quando a
    integridade passou a estar validada, e nao a ultima vez que alguem a validou.
    """
    integridades = sorted(
        (e for e in eventos if e.event_type == INTEGRITY_VALIDATION_DECLARED),
        key=instante,
    )
    for posicao, evento in enumerate(integridades):
        if completa(evento, integridades[:posicao]):
            return evento
    return None


def _todas_as_ttcm(
    eventos: Sequence[Event], congelados: tuple[Congelamento, ...]
) -> list[Medida]:
    """Uma `TTCM` por inject que exige resposta, com a submissao que responde.

    Inject sem submissao correspondente produz medida NAO MARCADA, e nao some da
    lista: `03` §3.0 registra que metrica que nao dispara e pior que metrica
    ausente, porque a ausencia ao menos se ve. O AAR precisa saber que houve um
    inject exigindo resposta que ninguem respondeu.
    """
    submissoes = sorted(
        (e for e in eventos if e.event_type in SUBMISSOES), key=instante
    )
    medidas: list[Medida] = []

    for inject in sorted(
        (
            e
            for e in eventos
            if e.event_type == INJECT_FIRED and e.payload.get(EXIGE_RESPOSTA) is True
        ),
        key=instante,
    ):
        alvo = inject.correlation.inject_id
        resposta = next(
            (
                s
                for s in submissoes
                if s.correlation.inject_id == alvo and instante(s) >= instante(inject)
            ),
            None,
        )
        if resposta is None:
            medidas.append(nao_marcada("TTCM", referencia=alvo))
            continue
        medidas.append(
            Medida(
                sigla="TTCM",
                inicio=instante(inject),
                fim=instante(resposta),
                decorrido=decorrido(instante(inject), instante(resposta), congelados),
                referencia=alvo,
            )
        )

    # NENHUM INJECT EXIGIU RESPOSTA: a sigla sai UMA VEZ, sem referencia e nao
    # marcada. Devolver lista vazia faria `TTCM` DESAPARECER da saida, e `03`
    # §3.0 escreve o custo disso — *"metrica que nao dispara e pior que metrica
    # ausente, porque a ausencia ao menos se ve"*. Sumindo, o AAR nao teria como
    # distinguir "nenhum inject pedia resposta" de "o computador esqueceu a
    # sigla". Foi o teste das seis siglas que pegou.
    return medidas or [nao_marcada("TTCM")]


def _desde_t0(
    sigla: str,
    evento: Event | None,
    t_zero: datetime,
    congelados: tuple[Congelamento, ...],
) -> Medida:
    """As metades de declaracao de um par: o instante, medido desde T0."""
    if evento is None:
        return nao_marcada(sigla)
    marcado = instante(evento)
    return Medida(
        sigla=sigla,
        inicio=t_zero,
        fim=marcado,
        decorrido=decorrido(t_zero, marcado, congelados),
    )


def _entre(
    sigla: str,
    inicio: Event | None,
    fim: Event | None,
    congelados: tuple[Congelamento, ...],
) -> Medida:
    """As simples: start e stop proprios, os dois vindos deste lado.

    Falta qualquer um dos dois e a medida NAO E MARCADA. Em particular, `TTA` sem
    inject de impacto observavel nao vira "zero desde T0" — a medicao nao comecou,
    e um zero ali seria numero onde nao houve medida.
    """
    if inicio is None or fim is None:
        return nao_marcada(sigla)
    return Medida(
        sigla=sigla,
        inicio=instante(inicio),
        fim=instante(fim),
        decorrido=decorrido(instante(inicio), instante(fim), congelados),
    )
