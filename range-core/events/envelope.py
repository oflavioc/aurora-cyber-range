"""O envelope de evento — a forma de LEITURA, e a de submissao nao vive aqui.

AUTORIDADE
----------
`09_EVENT_MODEL.md` §1 e §1.1; `01_ARCHITECTURE.md` §3;
`contracts/events.schema.yaml`.

POR QUE EM `events/` E NAO EM `state/`
--------------------------------------
O envelope nasceu dentro de `state/simulation_state.py`, porque o fold foi a
primeira peca a precisar dele. Estava invertido: `simulation_state` e UMA das
cinco projecoes SOBRE eventos, e uma projecao definindo o envelope faria
`events/` depender de `state/` no dia em que o store precisasse construir um.

Foi o que aconteceu ao escrever o `append`. Corrigido aqui, no momento mais
barato — um arquivo, com o fold e os testes como unicos consumidores.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: Valor de flag. Os tipos vem de `contracts/state_flags.schema.yaml`; o fold
#: nao os valida — quem valida e o loader, no boot, contra o contrato do adapter
#: (`01` §5.4, e o item 9 da DoD desta fase).
FlagValue = bool | int | float | str


@dataclass(frozen=True, slots=True)
class Correlation:
    """`09` §1 — o bloco `correlation` do envelope."""

    scenario_id: str | None = None
    inject_id: str | None = None
    causation_id: str | None = None
    fact_id: str | None = None


@dataclass(frozen=True, slots=True)
class Event:
    """Envelope de `09` §1.1, na forma de LEITURA.

    A forma de APPEND e outra e nao vive aqui: as tres marcas temporais e o
    `clock_multiplier` sao carimbados pelo event store no append, a partir do
    `exercise-clock`, nunca pelo produtor (D1 do checkpoint, §1.5). Um produtor
    que carimbe o proprio tempo produz fluxo nao-monotonico, e carimba tempo que
    nao existiu se o fizer durante uma pausa.

    NAO HA CAMPO DE VINCULO A OBJETIVO, e a ausencia e o ponto: `09` §1.2 o
    proibe no envelope, e o invariante 4 o guarda por AST em
    `tools/check_event_envelope.py`. O binding evento -> objetivo ocorre na
    projecao. Aqui ele e inexprimivel.
    """

    event_id: str
    event_type: str
    truth_layer: str
    producer: str

    # As quatro marcas. `exercise_time` e o rotulo `T+` e REBOBINA no rollback;
    # `exercise_timestamp` NAO rebobina, e e o que ordena eventos de epochs
    # distintas entre si (`01` §3, `09` §1.1).
    exercise_time: str
    exercise_timestamp: str
    wall_timestamp: str
    clock_multiplier: float

    simulation_epoch: int
    correlation: Correlation
    payload: Mapping[str, object]

    #: Obrigatorios quando `truth_layer` for `participant_action` ou
    #: `evaluator_assessment` (`09` §1.1). A obrigatoriedade e do contrato, nao
    #: deste tipo.
    actor_id: str | None = None
    persona: str | None = None
