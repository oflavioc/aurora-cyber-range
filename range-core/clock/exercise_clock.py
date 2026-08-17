"""`exercise-clock` — T0, pausa, multiplicador, e as duas marcas de exercicio.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §3; `00_MASTER_SPEC.md` §5.6; `06_ACCEPTANCE_TESTS.md` T4;
`07_IMPLEMENTATION_PHASES.md` Fase 2, item 3 da DoD.

O QUE ELE E
-----------
Uma funcao do relogio de parede para as quatro marcas, com tres estados
acumulados: T0, quanto tempo de exercicio ja correu, e o multiplicador vigente.

`01` §3: "T0 definido pelo facilitador; PAUSAR congela e impede disparo
agendado; multiplicador 1x / 5x / 20x para ensaio".

AS DUAS MARCAS DE EXERCICIO SAO A MESMA CONTA, LIDAS DE DOIS JEITOS
--------------------------------------------------------------------
`exercise_time` e o rotulo `T+HH:MM:SS`, contado a partir do inicio da EPOCH
corrente — rebobina no rollback. `exercise_timestamp` e datetime absoluto,
contado a partir de T0 e **acumulado**: nao rebobina, e e o que ordena eventos de
epochs distintas entre si.

`01` §3 fixou isso normativamente no `spec-change` `a3aded5`, e antes disso a
propriedade so existia por implicacao. As duas congelam juntas no PAUSAR, porque
sao marcas do MESMO relogio.

O TEMPO DE PAREDE ENTRA POR INJECAO, E NAO POR `time.time()`
--------------------------------------------------------------
`now` e um parametro do construtor. Nao e cerimonia de testabilidade: um clock
que le o relogio do processo nao pode ser testado sem dormir, e teste que dorme
ou e lento ou e intermitente. Com a fonte injetada, "durante o PAUSAR o
`exercise_time` nao avanca e o `wall_timestamp` avanca" — T4 — vira assercao
exata em vez de aproximacao com tolerancia.

O DEFAULT e `time.time`, entao producao nao paga nada por isso.

O QUE ELE NAO FAZ
-----------------
Nao agenda, nao dispara e nao conhece inject. O item 3 da DoD tem duas metades —
"PAUSAR congela o clock" e "bloqueia disparo agendado" —, e a segunda e do
inject-engine. O que o clock oferece e `is_paused`, e o engine consulta: quem
decide nao disparar e quem dispara.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from range_core.clock.port import Marks

#: `01` §3 — "multiplicador 1x / 5x / 20x para ensaio". Conjunto fechado, e nao
#: faixa: multiplicador arbitrario tornaria a timeline do AAR irreconstruivel
#: por combinacao que ninguem testou, e `09` §1.1 grava o multiplicador em cada
#: evento justamente para reconstruir.
ALLOWED_MULTIPLIERS: tuple[float, ...] = (1.0, 5.0, 20.0)


class ClockError(Exception):
    """Operacao que o clock recusa, alto.

    Pausar o que ja esta pausado, retomar o que nao esta, ou pedir multiplicador
    fora do conjunto de `01` §3. Nenhuma delas e ambigua o bastante para ser
    resolvida por conta propria, e resolver por conta propria produziria relogio
    que mente sobre o proprio estado.
    """


class ExerciseClock:
    """Implementa `ExerciseClockPort`.

    Estado: T0, tempo de exercicio acumulado ate a ultima transicao, o instante
    de parede da ultima transicao, o multiplicador e a pausa. Toda leitura e
    derivada — nao ha thread, nem tique, nem tarefa de fundo.
    """

    def __init__(
        self,
        t_zero: datetime,
        *,
        now: Callable[[], float] = time.time,
        multiplier: float = 1.0,
    ) -> None:
        if multiplier not in ALLOWED_MULTIPLIERS:
            raise ClockError(
                f"multiplicador {multiplier} fora de {ALLOWED_MULTIPLIERS}: "
                "`01` §3 fixa o conjunto, e valor livre torna a timeline do AAR "
                "irreconstruivel por combinacao nao testada"
            )
        self._t_zero = t_zero
        self._now = now
        self._multiplier = multiplier
        self._paused = False

        #: Segundos de EXERCICIO ja acumulados ate a ultima transicao.
        self._accumulated = 0.0
        #: Instante de PAREDE da ultima transicao — pausa, retomada ou troca de
        #: multiplicador. O tempo entre ele e agora e o unico trecho que ainda
        #: precisa ser convertido.
        self._since = now()

        #: Inicio da epoch corrente, em segundos de exercicio desde T0. O
        #: rollback o move; e o que faz `exercise_time` rebobinar sem que
        #: `exercise_timestamp` rebobine junto.
        self._epoch_started_at = 0.0

    @classmethod
    def restaurado(
        cls,
        t_zero: datetime,
        *,
        elapsed_seconds: float,
        multiplier: float,
        paused: bool,
        epoch_started_at: float,
        now: Callable[[], float] = time.time,
    ) -> ExerciseClock:
        """Um clock com os cinco valores JA DERIVADOS. Nao le evento nenhum.

        A FRONTEIRA E DELIBERADA, e e a mesma que mantem o clock ignorante de
        inject: quem sabe ler um fluxo e `range_core.clock.restauracao`, e o que
        chega aqui sao cinco numeros. Se este construtor conhecesse `event_type`,
        o clock passaria a depender do catalogo para existir — e o catalogo muda
        por `spec-change`, enquanto o relogio nao.

        NAO HA VALOR PADRAO PARA NENHUM DOS CINCO. Todos sao obrigatorios, e e
        isso que impede a restauracao de "quase acontecer": um default aqui
        produziria um clock plausivel a partir de um fluxo que nao respondia
        aquela pergunta — que e a forma como um reinicio erra sem falhar.
        """
        clock = cls(t_zero, now=now, multiplier=multiplier)
        clock._accumulated = elapsed_seconds
        clock._since = now()
        clock._paused = paused
        clock._epoch_started_at = epoch_started_at
        return clock

    # -- leitura ---------------------------------------------------------

    @property
    def is_paused(self) -> bool:
        """Quem consulta e o inject-engine, para nao disparar agendado."""
        return self._paused

    @property
    def multiplier(self) -> float:
        return self._multiplier

    def elapsed_seconds(self) -> float:
        """Segundos de EXERCICIO desde T0. Congela na pausa."""
        if self._paused:
            return self._accumulated
        return self._accumulated + (self._now() - self._since) * self._multiplier

    def marks(self) -> Marks:
        """As quatro marcas, do MESMO instante.

        Uma leitura do relogio de parede alimenta as quatro. Ler em chamadas
        separadas abriria janela para uma pausa cair no meio, e o evento
        carregaria marcas de instantes diferentes.
        """
        wall = self._now()
        exercise = self.elapsed_seconds()
        return Marks(
            exercise_time=_label(exercise - self._epoch_started_at),
            exercise_timestamp=(self._t_zero + timedelta(seconds=exercise)).isoformat(
                timespec="seconds"
            ),
            wall_timestamp=datetime.fromtimestamp(wall).astimezone().isoformat(
                timespec="seconds"
            ),
            clock_multiplier=self._multiplier,
        )

    # -- transicoes ------------------------------------------------------

    def pause(self) -> None:
        """Congela AS DUAS marcas de exercicio. O de parede segue correndo."""
        if self._paused:
            raise ClockError(
                "pausar relogio ja pausado: a operacao nao e idempotente por "
                "desenho — pausa dupla costuma ser dois facilitadores agindo "
                "sobre o mesmo exercicio, e silenciar isso esconde o conflito"
            )
        self._accumulated = self.elapsed_seconds()
        self._paused = True

    def resume(self) -> None:
        if not self._paused:
            raise ClockError("retomar relogio que nao esta pausado")
        self._since = self._now()
        self._paused = False

    def set_multiplier(self, multiplier: float) -> None:
        """Troca o multiplicador SEM perder o que ja correu.

        O acumulado e fechado com o multiplicador antigo antes da troca. Sem
        isso, mudar de 1x para 20x no meio reescreveria retroativamente o tempo
        ja decorrido — e `09` §1.1 grava o multiplicador em cada evento
        exatamente para que a timeline seja reconstruivel quando ele muda.
        """
        if multiplier not in ALLOWED_MULTIPLIERS:
            raise ClockError(f"multiplicador {multiplier} fora de {ALLOWED_MULTIPLIERS}")
        self._accumulated = self.elapsed_seconds()
        self._since = self._now()
        self._multiplier = multiplier

    def start_new_epoch(self, at_exercise_seconds: float) -> None:
        """Rebobina `exercise_time` ate o ponto de corte. NAO toca o timestamp.

        E a separacao que `01` §3 normatiza: o rotulo `T+` volta, o datetime
        absoluto nao. Quem chama e o rollback; o clock nao sabe o que e rollback.
        """
        if at_exercise_seconds < 0:
            raise ClockError("ponto de corte negativo: nao ha exercicio antes de T0")
        self._epoch_started_at = at_exercise_seconds


def _label(seconds: float) -> str:
    """`T+HH:MM:SS`, truncado — o formato de `01` §3 e `09` §1."""
    total = max(0, int(seconds))
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"T+{horas:02d}:{minutos:02d}:{segundos:02d}"


#: O inverso de `_label`. Mora AQUI, ao lado dele, porque o formato tem um dono
#: so: escrever a leitura em outro modulo faria as duas metades divergirem no
#: dia em que o formato mudasse — que e a classe D4.
_LABEL = re.compile(r"^T\+(?P<horas>\d+):(?P<minutos>[0-5]\d):(?P<segundos>[0-5]\d)$")


def label_seconds(label: str) -> int:
    """`T+HH:MM:SS` -> segundos. Quem le e o engine, e o motivo importa.

    O rotulo `T+` de um evento e a POSICAO DELE NA LINHA DO EXERCICIO, porque
    ele rebobina ate o ponto de corte no rollback (`01` §3). E o que permite ao
    engine ancorar um rollback e reagendar os injects sem guardar memoria de
    nada: a posicao esta no envelope.

    Recusa alto o que nao casa. Um rotulo em outro formato lido por adivinhacao
    produziria corte na posicao errada — e corte na posicao errada nao falha,
    reconstroi outro mundo.
    """
    casado = _LABEL.match(str(label))
    if casado is None:
        raise ClockError(
            f"rotulo de exercise_time {label!r} fora do formato `T+HH:MM:SS` de "
            "`01` §3 e `09` §1"
        )
    return (
        int(casado.group("horas")) * 3600
        + int(casado.group("minutos")) * 60
        + int(casado.group("segundos"))
    )
