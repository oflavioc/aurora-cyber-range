"""A porta do `exercise-clock` — o que o store precisa dele, e so isso.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §3; `00_MASTER_SPEC.md` §5.6; `09_EVENT_MODEL.md` §1.1.

POR QUE UMA PORTA, E NAO O CLOCK
--------------------------------
O `append` carimba as quatro marcas a partir do `exercise-clock` — D1 do
checkpoint desta fase. Mas o clock e outra peca, com pausa, multiplicador e T0,
e o store nao precisa de nada disso: precisa de **uma leitura**.

Definir a porta aqui deixa o store completo e testavel antes de o clock existir,
sem inventar o clock por acidente. Quem o implementar preenche esta interface;
quem o testa passa um duplo.

A porta e o LIMITE do que o store sabe sobre tempo. Ele nao pausa, nao consulta
multiplicador e nao converte nada: recebe as quatro marcas prontas e as grava.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Marks:
    """As quatro marcas, lidas juntas e no mesmo instante.

    JUNTAS E O PONTO. Ler `exercise_time` numa chamada e `wall_timestamp` em
    outra abriria janela para o clock avancar — ou ser pausado — entre as duas,
    e o evento carregaria marcas de instantes diferentes. `01` §3 as trata como
    um conjunto, e a porta as devolve como um.

    `exercise_time` e o rotulo `T+` e REBOBINA no rollback; `exercise_timestamp`
    nao rebobina, e e o que ordena eventos de epochs distintas entre si
    (`01` §3). Os dois vem do mesmo relogio e congelam juntos no PAUSAR.
    """

    exercise_time: str
    exercise_timestamp: str
    wall_timestamp: str
    clock_multiplier: float


class ExerciseClockPort(Protocol):
    """O que o event store exige do `exercise-clock`."""

    def marks(self) -> Marks:
        """As quatro marcas do instante corrente."""
        ...
