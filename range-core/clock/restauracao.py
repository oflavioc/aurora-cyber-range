"""Reconstruir o exercicio a partir do event store — os CINCO valores.

AUTORIDADE
----------
`07_IMPLEMENTATION_PHASES.md` Fase 4, item 4 da DoD (*"reinicio do container do
engine restaura o exercicio a partir do event store"*); `06_ACCEPTANCE_TESTS.md`
T5 (*"reinicio com o exercicio pausado o restaura pausado; reinicio depois da
retomada o restaura correndo. **Os dois casos**"*); `01_ARCHITECTURE.md` §3 e
§4.1; `09_EVENT_MODEL.md` §1.1 e §3.

O QUE UM PROCESSO NOVO NAO SABE, E DE ONDE CADA COISA VEM
-----------------------------------------------------------
O clock guarda cinco coisas, e **nenhuma delas esta em disco**. Todas saem do
envelope, que `09` §1.1 desenhou para isto:

    T0                 `exercise_timestamp` do `exercise_started`. No instante
                       do start o decorrido e zero, entao aquela marca E o T0.
    acumulado          `exercise_timestamp` do ULTIMO evento da a distancia ate
                       T0; o trecho desde entao vem do `wall_timestamp` dele.
    multiplicador      `clock_multiplier` do ultimo evento. `09` §1.1 diz que
                       ele e gravado em cada evento "para reconstrucao", e esta
                       e a reconstrucao.
    origem de epoch    a diferenca entre o decorrido de um evento e o rotulo
                       `T+` dele. Ver `_origem_de_epoch`.
    pausa              `paused_in`, sobre o par `exercise_paused`/`exercise_resumed`.

O REINICIO NAO CONGELA O EXERCICIO, e isso e da spec
-----------------------------------------------------
Enquanto o processo esteve fora do ar, o tempo de exercicio **correu**. Nao e
escolha: `01` §3 fixa que, na falha do range, *"o clock de exercicio continua
correndo; apenas a projecao de metricas desconta o intervalo"*. Um reinicio e o
caso tipico dessa falha, e o desconto e do `rollback_performed` com
`reason: technical_failure` — que ja grava os extremos desde a Fase 2.

A alternativa — restaurar congelado no ultimo evento — seria inventar uma pausa
que ninguem declarou, e faria o exercicio andar mais devagar que a sala.

**O que congela e a PAUSA**, e ela e explicita: com o exercicio pausado, o
acumulado e o do ultimo evento e o tempo de parede nao entra na conta.

O QUE ELE RECUSA, E POR QUE ALTO
---------------------------------
Fluxo sem `exercise_started` **nao tem T0**, e nao ha como inventa-lo: usar
"agora" produziria uma linha do tempo plausivel e errada, com todo evento
anterior caindo no futuro. E a mesma disciplina da ancora da auditoria — nao
saber onde comeca nao pode degradar para um palpite.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from contracts.generated.events import (
    EXERCISE_PAUSED,
    EXERCISE_RESET,
    EXERCISE_RESUMED,
    EXERCISE_STARTED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.exercise_clock import ExerciseClock, label_seconds
from range_core.events.envelope import Event

#: A chave do payload de `rollback_performed` que aponta a ancora do corte. O
#: nome vem de `simulation_state`, que e quem o exige — repeti-lo aqui como
#: literal faria as duas pontas divergirem no dia em que uma mudasse.
from range_core.state.simulation_state import TO_EVENT_ID


class RestauracaoError(Exception):
    """O fluxo nao responde ao que a restauracao precisa saber."""


@dataclass(frozen=True, slots=True)
class Restaurado:
    """Os cinco valores, nomeados — para o teste afirmar CADA UM.

    Devolver so o clock faria o teste medir os cinco por consequencia, e a
    consequencia mistura: um erro de T0 e um erro de acumulado produzem o mesmo
    `exercise_timestamp`. Com os cinco separados, o par que discrimina cada um
    pode ser escrito de verdade.
    """

    t_zero: datetime
    elapsed_seconds: float
    multiplier: float
    paused: bool
    epoch_started_at: float


def paused_in(events: Sequence[Event]) -> bool:
    """O exercicio esta pausado, segundo o FLUXO. Pura, e nao consulta relogio.

    LE OS DOIS EVENTOS, e a P2-13 existiu exatamente por isso: `exercise_paused`
    sem nada depois e o MESMO fluxo para *"ainda pausado"* e para *"retomado, e
    nada aconteceu desde entao"*. A heuristica que salvaria o caso — evento
    posterior implica retomada — **nao vale**: `01` §3 bloqueia o disparo
    AGENDADO durante a pausa e §6 mantem o MANUAL, entao um `inject_fired`
    posterior e compativel com o exercicio ainda parado.

    `exercise_started` e `exercise_reset` tambem devolvem o estado a CORRENDO.
    Nao e generosidade: `01` §4.2 chama o reset de recomeco, e exercicio que
    recomeca nao herda a pausa do anterior.

    MORAVA NO `inject_engine`, e mudou de casa nesta peca — nao de forma. Quem
    restaura precisa dela antes de existir engine, e duas copias da mesma regra
    divergiriam na primeira vez que uma das duas fosse corrigida.
    """
    pausado = False
    for evento in events:
        if evento.event_type == EXERCISE_PAUSED:
            pausado = True
        elif evento.event_type in (EXERCISE_RESUMED, EXERCISE_STARTED, EXERCISE_RESET):
            pausado = False
    return pausado


def _instante(marca: str) -> datetime:
    try:
        return datetime.fromisoformat(marca)
    except ValueError as erro:
        raise RestauracaoError(
            f"marca temporal {marca!r} fora do formato ISO do envelope: sem "
            "poder le-la, o exercicio seria restaurado por adivinhacao"
        ) from erro


def _origem_de_epoch(eventos: Sequence[Event], t_zero: datetime) -> float:
    """Onde a epoch corrente comeca, em segundos de exercicio desde T0.

    A DEFINICAO E UMA SO: `exercise_time = decorrido - origem`. Entao, para
    qualquer evento da epoch corrente, `origem = decorrido(evento) - rotulo(evento)`.
    Isso vale para rollbacks encadeados sem caso especial, porque cada rotulo ja
    esta no referencial rebobinado.

    O CASO DE BORDA E O ROLLBACK RECEM-GRAVADO. `inject_engine.rollback` grava o
    evento ANTES de rebobinar — `09` §3 o desenha no fim da epoch abandonada —,
    entao logo depois dele a epoch corrente ainda **nao tem evento nenhum**. Ali a
    origem vem da ancora, exatamente como o engine a calculou.
    """
    ultimo = eventos[-1]
    if ultimo.event_type != ROLLBACK_PERFORMED:
        return (_instante(ultimo.exercise_timestamp) - t_zero).total_seconds() - float(
            label_seconds(ultimo.exercise_time)
        )

    ancora_id = ultimo.payload.get(TO_EVENT_ID)
    ancora = next((e for e in eventos if e.event_id == ancora_id), None)
    if ancora is None:
        raise RestauracaoError(
            f"o ultimo `rollback_performed` aponta para {ancora_id!r}, que nao "
            "esta no fluxo: sem a ancora nao ha como saber onde a epoch corrente "
            "comeca, e chutar zero devolveria o rotulo `T+` ao inicio do exercicio"
        )
    decorrido_no_rollback = (
        _instante(ultimo.exercise_timestamp) - t_zero
    ).total_seconds()
    return decorrido_no_rollback - float(label_seconds(ancora.exercise_time))


def derivar(eventos: Sequence[Event], *, now: Callable[[], float] = time.time) -> Restaurado:
    """Os cinco valores, a partir do fluxo. **Sem construir clock.**"""
    if not eventos:
        raise RestauracaoError(
            "fluxo vazio: nao ha exercicio a restaurar. Um clock novo aqui seria "
            "um exercicio comecando, e nao um exercicio restaurado"
        )

    inicio = next((e for e in eventos if e.event_type == EXERCISE_STARTED), None)
    if inicio is None:
        raise RestauracaoError(
            "fluxo sem `exercise_started`: nao ha T0. Usar o instante do reinicio "
            "poria todo evento anterior no futuro — e a linha do tempo pareceria "
            "normal"
        )

    t_zero = _instante(inicio.exercise_timestamp)
    ultimo = eventos[-1]
    multiplicador = float(ultimo.clock_multiplier)
    pausado = paused_in(eventos)

    decorrido = (_instante(ultimo.exercise_timestamp) - t_zero).total_seconds()
    if not pausado:
        # O trecho entre o ultimo evento e agora: tempo de PAREDE convertido pelo
        # multiplicador vigente. `01` §3 — na falha do range o clock de exercicio
        # continua correndo.
        parede = _instante(ultimo.wall_timestamp).timestamp()
        decorrido += max(0.0, now() - parede) * multiplicador

    return Restaurado(
        t_zero=t_zero,
        elapsed_seconds=decorrido,
        multiplier=multiplicador,
        paused=pausado,
        epoch_started_at=_origem_de_epoch(eventos, t_zero),
    )


def restaurar(
    eventos: Sequence[Event], *, now: Callable[[], float] = time.time
) -> ExerciseClock:
    """O clock do exercicio em curso, a partir do store. Item 4 da DoD.

    Duas funcoes e nao uma: `derivar` responde CADA pergunta separadamente, e e
    contra ela que os pares de T5 sao escritos. Um teste que so olhasse o clock
    mediria os cinco por consequencia — e um erro de T0 e um erro de acumulado
    produzem o mesmo `exercise_timestamp`.
    """
    valores = derivar(eventos, now=now)
    return ExerciseClock.restaurado(
        valores.t_zero,
        elapsed_seconds=valores.elapsed_seconds,
        multiplier=valores.multiplier,
        paused=valores.paused,
        epoch_started_at=valores.epoch_started_at,
        now=now,
    )
