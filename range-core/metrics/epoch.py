"""Epoch como CALCULO do consumidor — o desconto por uniao e o descarte de `rehearsal`.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §3.2, bloco *"Epoch e computacao do consumidor, nunca recorte
na montagem"*; `09_EVENT_MODEL.md` §3.1; `03_EXERCISE_DESIGN.md` §3.5;
`06_ACCEPTANCE_TESTS.md` T10.

POR QUE ISTO E UM MODULO, E NAO UM RECORTE NO MONTADOR
------------------------------------------------------
`range-core/metrics/insumo.py` entrega a escrituracao de epoch INTEIRA aos dois
lados, de proposito. O desconto mora aqui porque a §3.2 exige que ele seja
*"codigo do consumidor, visivel e testado"*, e diz o que se perde na outra
colocacao: recortada na montagem, a regra passa a ser propriedade do montador, o
numero certo aparece por **ausencia de insumo** em vez de por calculo, e evento
perdido por defeito fica indistinguivel de evento corretamente descontado.

E modulo compartilhado pelos dois computadores, e nao codigo repetido em cada um,
pelo motivo da D4: duas implementacoes da mesma regra divergem em silencio.
Compartilhar o calculo nao o tira do consumidor — ele continua sendo chamado
pelo computador, sobre insumo que o computador recebeu.

AS DUAS REGRAS, E ELAS SAO DIFERENTES
--------------------------------------
`09` §3.1 da a cada `reason` um efeito proprio, e so dois deles chegam ate aqui:

- **`technical_failure`** congela o relogio entre o inject falho e a retomada. O
  intervalo e **descontado**, e a equipe nao e penalizada por bug do ambiente.
- **`rehearsal`** descarta a epoch: *"nenhum evento da epoch entra em calculo"*.
  Nao e desconto de tempo — e exclusao de evento, e por isso as duas regras nao
  se reduzem uma a outra.

`facilitation` e `adjudication` nao produzem desconto nem descarte: as metricas
sao recomputadas a partir da nova epoch, com nota, e a nota e do AAR.

UNIAO, NUNCA SOMA — E E POR ISSO QUE O REGISTRO E POR EXTREMOS
---------------------------------------------------------------
Dois congelamentos que se sobrepoem contam o trecho comum **duas vezes** se as
duracoes forem somadas, e a duracao ja somada nao guarda com que detectar isso.
`06` T3 fixa o registro por extremos exatamente para tornar a uniao possivel, e
T10 exige a uniao por nome.

O RELOGIO E `exercise_timestamp`, E OS OUTROS TRES FORAM DESCARTADOS
---------------------------------------------------------------------
`06` T3 percorre os quatro e explica cada recusa. `wall_timestamp` nao, porque o
PAUSAR o avanca sem avancar o exercicio; `exercise_time` nao, porque rebobina no
rollback — os dois extremos de um congelamento caem em epochs diferentes **por
construcao**, e a uniao e operacao de ordem total entre extremos de rollbacks
distintos; duracao nao, pelo paragrafo acima.

**A PAUSA NAO PRECISA DE DESCONTO, e a ausencia e consequencia e nao esquecimento:**
`exercise_timestamp` nao avanca durante o pausar. Descontar a pausa aqui a
contaria duas vezes. E o mesmo fato que descarta `wall_timestamp`, visto do outro
lado.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from contracts.generated.events import ROLLBACK_PERFORMED

from range_core.events.envelope import Event
from range_core.metrics.insumo import EscrituracaoDeEpoch

#: Os dois `reason` que produzem efeito de metrica. O enum completo vive em
#: `contracts/events.schema.yaml` (`$defs/rollback_reason`), e
#: `tests/test_metrics_epoch.py` cruza estas constantes com ele — motivo novo no
#: contrato sem decisao aqui reprova, em vez de cair em nenhum dos dois ramos e
#: sumir.
MOTIVO_FALHA_TECNICA = "technical_failure"
MOTIVO_ENSAIO = "rehearsal"


class JanelaInvertida(ValueError):
    """Fim antes do inicio. Nao e caso de dominio, e defeito de quem chamou.

    `exercise_timestamp` nao rebobina — e a razao de ele existir —, entao uma
    janela invertida so nasce de start e stop trocados no computador. Devolver
    zero ou um negativo esconderia isso dentro de um numero que o AAR imprime.
    """


@dataclass(frozen=True)
class Congelamento:
    """Um intervalo de relogio congelado, pelos extremos.

    Em `datetime`, e nao na string do envelope: a uniao compara e ordena, e
    comparacao de string so coincide com comparacao de instante enquanto o
    formato for exatamente o mesmo em todo produtor.
    """

    inicio: datetime
    fim: datetime

    @property
    def duracao(self) -> timedelta:
        return self.fim - self.inicio


def epochs_descartadas(escrituracao: EscrituracaoDeEpoch) -> frozenset[int]:
    """As epochs que um rollback `rehearsal` descartou.

    **A epoch descartada e a do proprio `rollback_performed`**, e nao a seguinte:
    o store carimba a epoch ANTES do append — `current_epoch` conta os rollbacks
    ja gravados —, entao o evento de rollback carrega a epoch que ele encerra.
    E o que `09` §3 desenha, com o evento dentro da epoch que fecha.
    """
    return frozenset(
        evento.simulation_epoch
        for evento in escrituracao
        if evento.event_type == ROLLBACK_PERFORMED
        and evento.payload.get("reason") == MOTIVO_ENSAIO
    )


def no_calculo(
    eventos: Sequence[Event], descartadas: frozenset[int]
) -> tuple[Event, ...]:
    """Os eventos que entram em calculo — os de epoch descartada ficam de fora.

    Vale para os eventos do LADO, e nao so para a escrituracao: `09` §3.1 diz
    *"nenhum evento da epoch entra em calculo"*, sem restringir a especie. E a
    razao de a escrituracao ir aos dois lados — sem ela, o computador da
    declaracao nao teria como saber que a epoch dele foi descartada, e o
    montador teria de recortar por ele.
    """
    return tuple(e for e in eventos if e.simulation_epoch not in descartadas)


def congelamentos(escrituracao: EscrituracaoDeEpoch) -> tuple[Congelamento, ...]:
    """Os intervalos de `technical_failure`, **ja unidos** e em ordem.

    A uniao acontece aqui, uma vez, e nao em cada chamador: dois chamadores que
    a fizessem por conta propria seriam duas implementacoes da mesma regra.

    Intervalo registrado em epoch descartada NAO conta, e o caso e real: um
    `technical_failure` dentro de uma epoch que um `rehearsal` posterior
    descartou e evento daquela epoch, e a regra de `09` §3.1 nao abre excecao
    por especie de evento.
    """
    descartadas = epochs_descartadas(escrituracao)
    brutos = [
        _intervalo(evento)
        for evento in no_calculo(escrituracao, descartadas)
        if evento.event_type == ROLLBACK_PERFORMED
        and evento.payload.get("reason") == MOTIVO_FALHA_TECNICA
    ]
    return uniao(brutos)


def uniao(intervalos: Iterable[Congelamento]) -> tuple[Congelamento, ...]:
    """Funde os que se tocam ou se sobrepoem. NUNCA soma duracoes.

    Adjacencia exata funde junto — `fim == inicio` do seguinte —, e nao e
    detalhe: dois congelamentos encostados descrevem um unico trecho de relogio
    parado, e mante-los separados nao muda a medida mas faz a saida descrever
    mal o que houve.
    """
    ordenados = sorted(intervalos, key=lambda c: (c.inicio, c.fim))
    fundidos: list[Congelamento] = []
    for atual in ordenados:
        if fundidos and atual.inicio <= fundidos[-1].fim:
            anterior = fundidos[-1]
            if atual.fim > anterior.fim:
                fundidos[-1] = Congelamento(anterior.inicio, atual.fim)
            continue
        fundidos.append(atual)
    return tuple(fundidos)


def decorrido(
    inicio: datetime, fim: datetime, congelados: Sequence[Congelamento]
) -> timedelta:
    """A distancia entre dois instantes, **menos** o relogio congelado no meio.

    Os congelamentos sao RECORTADOS a janela antes de descontar. Um que comece
    antes do start ou termine depois do stop so desconta a parte que cai dentro
    — descontar inteiro subtrairia tempo que a metrica nunca contou, e produziria
    numero menor que o real sem nada acusar.

    Espera `congelados` **ja unidos** (`congelamentos` devolve assim). Sobre
    intervalos crus com sobreposicao, o resultado seria a soma — que e o defeito
    que T10 proibe por nome.
    """
    if fim < inicio:
        raise JanelaInvertida(
            f"janela de metrica invertida: stop {fim.isoformat()} antes do start "
            f"{inicio.isoformat()}. `exercise_timestamp` nao rebobina, entao isto "
            "e start e stop trocados no computador, e nao rollback."
        )

    congelado = timedelta()
    for intervalo in congelados:
        recorte_inicio = max(intervalo.inicio, inicio)
        recorte_fim = min(intervalo.fim, fim)
        if recorte_fim > recorte_inicio:
            congelado += recorte_fim - recorte_inicio
    return (fim - inicio) - congelado


def instante(evento: Event) -> datetime:
    """O instante de um evento na ordem total do exercicio.

    Um so lugar converte, e os computadores nao repetem `fromisoformat`: e o
    ponto onde a escolha de `exercise_timestamp` — e a recusa dos outros tres
    relogios de `06` T3 — fica visivel em vez de espalhada.
    """
    return datetime.fromisoformat(evento.exercise_timestamp)


def _intervalo(evento: Event) -> Congelamento:
    """O `frozen_interval` de um `rollback_performed`, em `datetime`.

    A ausencia do campo NAO e tratada com default: o contrato o exige quando
    `reason` e `technical_failure` (`events.schema.yaml`, o `if/then` do
    `rollback_payload`), e um `KeyError` aqui aponta para o contrato violado. Um
    `.get` com fallback transformaria contrato quebrado em desconto zero — e o
    desconto sumiria sem nada acusar, que e o buraco que aquele `if/then` existe
    para fechar.
    """
    bruto = evento.payload["frozen_interval"]
    return Congelamento(
        inicio=datetime.fromisoformat(bruto["start"]),
        fim=datetime.fromisoformat(bruto["end"]),
    )
