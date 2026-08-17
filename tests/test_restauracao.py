"""A reconstrucao do exercicio — os CINCO valores, cada um com o par que discrimina.

O QUE "O PAR" QUER DIZER AQUI, E POR QUE ELE E O ARQUIVO INTEIRO
------------------------------------------------------------------
*Reinicio pausado restaura pausado* passa com um engine que sobe **sempre
pausado**. A Fase 2 registrou isso, e `06` T5 exige os DOIS casos por essa
razao. A mesma armadilha vale para os outros quatro, e cada um tem a sua forma
de passar sem restaurar nada:

    T0               um T0 fixo no codigo passa em qualquer teste de um fluxo so
    acumulado        um clock que nasce em zero passa no fluxo que comecou agora
    multiplicador    **1x e o default E o valor mais provavel no teste**: um
                     clock que ignora o fluxo devolve 1.0 e ninguem nota
    origem de epoch  zero passa em todo fluxo que nunca sofreu rollback
    pausa            "sobe sempre pausado" passa no caso pausado

Entao cada valor e medido com DOIS fluxos que so diferem naquele valor, e a
asserção compara os dois resultados entre si. Um valor que viesse de constante,
de default ou da memoria do processo daria o MESMO nos dois — e e isso que fica
vermelho.

O QUE ESTE ARQUIVO NAO PROVA
-----------------------------
O item 4 da DoD e sobre **container**. Aqui a restauracao e provada como funcao
pura e, na classe do Postgres, num PROCESSO NOVO de verdade. Nenhuma das duas e
o container, e a divisao esta declarada em `docs/progress/fase_4.md` §4.4 em vez
de sugerida: chamar processo de container seria trocar a condicao por um proxy,
que e o que a P3-2 custou a esta linhagem.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import (
    EXERCISE_PAUSED,
    EXERCISE_RESUMED,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.clock.restauracao import (
    RestauracaoError,
    derivar,
    paused_in,
    restaurar,
)
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.state.simulation_state import TO_EVENT_ID

T_ZERO = datetime(2026, 8, 16, 9, 0, 0)
#: T0 DIFERENTE, e o par do primeiro valor. Dois dias antes: um T0 constante no
#: codigo daria o mesmo nos dois fluxos.
OUTRO_T_ZERO = datetime(2026, 8, 14, 14, 30, 0)

PAREDE_INICIAL = 1_755_255_600.0


class Parede:
    """Fonte de tempo de parede controlada pelo teste."""

    def __init__(self, inicial: float = PAREDE_INICIAL) -> None:
        self.agora = inicial

    def __call__(self) -> float:
        return self.agora

    def avanca(self, segundos: float) -> None:
        self.agora += segundos


class Exercicio:
    """Um exercicio em curso: clock, store e os eventos que ele produziu.

    Nao e duplo de nada — e o clock de verdade e o store de verdade, com a fonte
    de tempo injetada, que e como a Fase 2 os desenhou.
    """

    def __init__(self, t_zero: datetime = T_ZERO, multiplicador: float = 1.0) -> None:
        self.parede = Parede()
        self.clock = ExerciseClock(t_zero, now=self.parede, multiplier=multiplicador)
        self.store = InMemoryEventStore(self.clock)

    def append(self, event_type: str, payload: dict | None = None, inject_id=None):
        return self.store.append(
            EventDraft(
                event_type=event_type,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack", inject_id=inject_id),
                payload=payload or {},
            )
        )

    @property
    def eventos(self):
        return self.store.read_all()


def _iniciado(**kwargs) -> Exercicio:
    exercicio = Exercicio(**kwargs)
    exercicio.append(EXERCISE_STARTED)
    return exercicio


class TZero(unittest.TestCase):
    """O T0 vem do `exercise_started`, e nao de uma constante."""

    def test_dois_exercicios_com_T0_diferente_restauram_T0_diferente(self) -> None:
        um = _iniciado(t_zero=T_ZERO)
        outro = _iniciado(t_zero=OUTRO_T_ZERO)

        self.assertEqual(derivar(um.eventos, now=um.parede).t_zero, T_ZERO)
        self.assertEqual(derivar(outro.eventos, now=outro.parede).t_zero, OUTRO_T_ZERO)
        self.assertNotEqual(
            derivar(um.eventos, now=um.parede).t_zero,
            derivar(outro.eventos, now=outro.parede).t_zero,
            "os dois fluxos deram o mesmo T0: ele nao esta vindo do fluxo",
        )

    def test_fluxo_sem_exercise_started_RECUSA(self) -> None:
        """Nao saber onde comeca nao pode degradar para um palpite.

        Usar o instante do reinicio como T0 poria todo evento anterior no
        futuro — e a linha do tempo pareceria normal.
        """
        exercicio = Exercicio()
        exercicio.append(INJECT_FIRED, inject_id="A01")
        with self.assertRaises(RestauracaoError) as erro:
            derivar(exercicio.eventos, now=exercicio.parede)
        self.assertIn("nao ha T0", str(erro.exception))

    def test_fluxo_vazio_RECUSA(self) -> None:
        with self.assertRaises(RestauracaoError):
            derivar([], now=Parede())


class Acumulado(unittest.TestCase):
    """Quanto de exercicio ja correu — e o tempo fora do ar conta."""

    def test_exercicio_com_dez_minutos_nao_restaura_no_zero(self) -> None:
        adiantado = _iniciado()
        adiantado.parede.avanca(600)
        adiantado.append(INJECT_FIRED, inject_id="A01")

        recem_comecado = _iniciado()
        recem_comecado.append(INJECT_FIRED, inject_id="A01")

        self.assertAlmostEqual(
            derivar(adiantado.eventos, now=adiantado.parede).elapsed_seconds, 600, places=0
        )
        self.assertAlmostEqual(
            derivar(recem_comecado.eventos, now=recem_comecado.parede).elapsed_seconds,
            0,
            places=0,
        )

    def test_o_tempo_FORA_DO_AR_correu_e_entra_na_conta(self) -> None:
        """`01` §3 — na falha do range o clock de exercicio continua correndo.

        Restaurar congelado no ultimo evento inventaria uma pausa que ninguem
        declarou, e o exercicio andaria mais devagar que a sala.
        """
        exercicio = _iniciado()
        exercicio.parede.avanca(600)
        exercicio.append(INJECT_FIRED, inject_id="A01")

        reinicio = Parede(exercicio.parede.agora + 300)
        self.assertAlmostEqual(
            derivar(exercicio.eventos, now=reinicio).elapsed_seconds, 900, places=0
        )

    def test_pausado_o_tempo_fora_do_ar_NAO_entra(self) -> None:
        """O par do de cima: o que congela e a PAUSA, e ela e declarada."""
        exercicio = _iniciado()
        exercicio.parede.avanca(600)
        exercicio.clock.pause()
        exercicio.append(EXERCISE_PAUSED)

        reinicio = Parede(exercicio.parede.agora + 3600)
        self.assertAlmostEqual(
            derivar(exercicio.eventos, now=reinicio).elapsed_seconds, 600, places=0
        )


class Multiplicador(unittest.TestCase):
    """O valor mais facil de enganar: 1x e o default e o mais provavel no teste."""

    def test_um_exercicio_em_5x_NAO_restaura_em_1x(self) -> None:
        rapido = _iniciado(multiplicador=5.0)
        rapido.append(INJECT_FIRED, inject_id="A01")

        normal = _iniciado()
        normal.append(INJECT_FIRED, inject_id="A01")

        self.assertEqual(derivar(rapido.eventos, now=rapido.parede).multiplier, 5.0)
        self.assertEqual(derivar(normal.eventos, now=normal.parede).multiplier, 1.0)

    def test_a_troca_de_multiplicador_no_meio_vale_a_partir_do_ULTIMO_evento(self) -> None:
        """`09` §1.1 grava o multiplicador em cada evento para reconstruir.

        O que vale no reinicio e o vigente, e nao o do inicio: o exercicio comeca
        em 1x, vai para 20x, e quem restaura tem de encontrar 20x.
        """
        exercicio = _iniciado()
        exercicio.append(INJECT_FIRED, inject_id="A01")
        exercicio.clock.set_multiplier(20.0)
        exercicio.append(INJECT_FIRED, inject_id="A02")

        self.assertEqual(
            derivar(exercicio.eventos, now=exercicio.parede).multiplier, 20.0
        )

    def test_o_multiplicador_converte_o_tempo_fora_do_ar(self) -> None:
        """A segunda forma de observa-lo, e ela e independente da primeira.

        Um `derivar` que lesse o multiplicador do fluxo para o campo e usasse 1x
        na conta do tempo fora do ar passaria no teste de cima e falharia aqui.
        """
        exercicio = _iniciado(multiplicador=5.0)
        exercicio.append(INJECT_FIRED, inject_id="A01")

        reinicio = Parede(exercicio.parede.agora + 60)
        self.assertAlmostEqual(
            derivar(exercicio.eventos, now=reinicio).elapsed_seconds, 300, places=0
        )


class OrigemDeEpoch(unittest.TestCase):
    """O rotulo `T+` rebobina no rollback; o `exercise_timestamp` nao — `01` §3."""

    def _com_rollback(self) -> Exercicio:
        exercicio = _iniciado()
        exercicio.parede.avanca(600)
        ancora = exercicio.append(INJECT_FIRED, inject_id="A01")
        exercicio.parede.avanca(300)
        exercicio.append(
            ROLLBACK_PERFORMED,
            {TO_EVENT_ID: ancora.event_id, "reason": "facilitation"},
            inject_id="A01",
        )
        exercicio.clock.start_new_epoch(
            exercicio.clock.elapsed_seconds() - 600
        )
        return exercicio

    def test_sem_rollback_a_origem_e_zero_e_COM_rollback_nao_e(self) -> None:
        sem = _iniciado()
        sem.parede.avanca(900)
        sem.append(INJECT_FIRED, inject_id="A01")

        self.assertEqual(derivar(sem.eventos, now=sem.parede).epoch_started_at, 0)
        self.assertAlmostEqual(
            derivar(self._com_rollback().eventos, now=Parede(PAREDE_INICIAL + 900))
            .epoch_started_at,
            300,
            places=0,
        )

    def test_o_rotulo_restaurado_e_o_REBOBINADO(self) -> None:
        """A consequencia observavel: o clock restaurado marca T+00:10:00.

        Sem a origem, ele marcaria T+00:15:00 — a posicao absoluta —, e o
        exercicio restaurado estaria cinco minutos adiante de onde a sala parou.
        """
        exercicio = self._com_rollback()
        antes = exercicio.clock.marks().exercise_time

        restaurado = restaurar(
            exercicio.eventos, now=Parede(exercicio.parede.agora)
        )
        self.assertEqual(restaurado.marks().exercise_time, antes)
        self.assertEqual(antes, "T+00:10:00")

    def test_a_origem_sai_igual_do_ROLLBACK_e_do_evento_seguinte(self) -> None:
        """Os dois caminhos de `_origem_de_epoch` dao o mesmo valor.

        Logo apos o rollback a epoch corrente nao tem evento nenhum, e a origem
        vem da ancora; com o proximo evento, ela vem do rotulo dele. Se os dois
        divergissem, a linha do tempo daria um salto no primeiro disparo depois
        de um rollback.
        """
        exercicio = self._com_rollback()
        pelo_rollback = derivar(
            exercicio.eventos, now=Parede(exercicio.parede.agora)
        ).epoch_started_at

        exercicio.parede.avanca(60)
        exercicio.append(INJECT_FIRED, inject_id="A02")
        pelo_evento = derivar(
            exercicio.eventos, now=Parede(exercicio.parede.agora)
        ).epoch_started_at

        self.assertAlmostEqual(pelo_rollback, pelo_evento, places=0)

    def test_rollback_com_ancora_ausente_RECUSA(self) -> None:
        exercicio = _iniciado()
        exercicio.append(
            ROLLBACK_PERFORMED, {TO_EVENT_ID: "01J-nao-existe", "reason": "facilitation"}
        )
        with self.assertRaises(RestauracaoError) as erro:
            derivar(exercicio.eventos, now=exercicio.parede)
        self.assertIn("nao esta no fluxo", str(erro.exception))


class Pausa(unittest.TestCase):
    """T5, os DOIS casos — e a P2-13, que e por que o par existe."""

    def test_pausado_restaura_pausado_e_retomado_restaura_CORRENDO(self) -> None:
        """O par inteiro de T5 numa asserção so.

        Um engine que sobe sempre pausado passa na primeira metade. Um que sobe
        sempre correndo passa na segunda. So o par separa "restaurou" de
        "nasceu assim".
        """
        pausado = _iniciado()
        pausado.append(EXERCISE_PAUSED)

        retomado = _iniciado()
        retomado.append(EXERCISE_PAUSED)
        retomado.append(EXERCISE_RESUMED)

        self.assertTrue(derivar(pausado.eventos, now=pausado.parede).paused)
        self.assertFalse(derivar(retomado.eventos, now=retomado.parede).paused)

    def test_paused_in_le_os_DOIS_eventos(self) -> None:
        """A P2-13 escrita como asserção.

        `exercise_paused` sem nada depois e o MESMO fluxo para "ainda pausado" e
        para "retomado, e nada aconteceu desde entao" — a nao ser que o fim da
        pausa tambem seja evento. Um `paused_in` que so olhasse
        `exercise_paused` devolveria `True` nos tres casos abaixo.
        """
        exercicio = _iniciado()
        exercicio.append(EXERCISE_PAUSED)
        self.assertTrue(paused_in(exercicio.eventos))

        exercicio.append(EXERCISE_RESUMED)
        self.assertFalse(paused_in(exercicio.eventos), "o `exercise_resumed` foi ignorado")

        exercicio.append(EXERCISE_PAUSED)
        self.assertTrue(paused_in(exercicio.eventos), "o ultimo evento do par nao venceu")

    def test_um_evento_DEPOIS_da_pausa_nao_significa_retomada(self) -> None:
        """`01` §3 bloqueia o disparo AGENDADO na pausa; §6 mantem o MANUAL.

        Entao a heuristica "evento posterior implica retomada" e falsa, e e por
        ela que o `exercise_resumed` precisou existir.
        """
        exercicio = _iniciado()
        exercicio.append(EXERCISE_PAUSED)
        exercicio.append(INJECT_FIRED, inject_id="A01")
        self.assertTrue(derivar(exercicio.eventos, now=exercicio.parede).paused)

    def test_o_clock_restaurado_carrega_a_pausa(self) -> None:
        exercicio = _iniciado()
        exercicio.clock.pause()
        exercicio.append(EXERCISE_PAUSED)
        self.assertTrue(restaurar(exercicio.eventos, now=exercicio.parede).is_paused)


DSN_ENV = "AURORA_TEST_DATABASE_URL"
_URL = os.environ.get(DSN_ENV)

RAZAO = (
    f"{DSN_ENV} nao definida. Este teste escreve e limpa a tabela de eventos, "
    "entao exige banco declarado descartavel. Para rodar:\n"
    f"    {DSN_ENV}=postgresql+psycopg://user:senha@127.0.0.1:5432/base \\\n"
    "        python -m unittest discover -s tests"
)


@unittest.skipIf(_URL is None, RAZAO)
class EmOutroProcesso(unittest.TestCase):
    """Os cinco valores atravessando o Postgres E a fronteira de processo.

    Restaurar na mesma sessao prova a aritmetica e mais nada — as variaveis ainda
    estao vivas. Aqui o interpretador e outro e a unica coisa compartilhada e a
    tabela: e a forma mais proxima do item 4 da DoD que esta peca alcanca, e o
    que falta para ele — o container — esta declarado no registro, e nao suposto.
    """

    RAIZ = Path(__file__).resolve().parents[1]
    TABELA = "event_store"

    def setUp(self) -> None:
        import psycopg  # noqa: PLC0415

        from range_core.events.postgres_store import (  # noqa: PLC0415
            PostgresEventStore,
            normalize_dsn,
        )

        with psycopg.connect(normalize_dsn(_URL)) as conn, conn.cursor() as cur:
            cur.execute(f"TRUNCATE {self.TABELA}")

        self.parede = Parede()
        self.clock = ExerciseClock(T_ZERO, now=self.parede, multiplier=5.0)
        self.store = PostgresEventStore(self.clock, _URL)

    def _append(self, event_type: str, payload: dict | None = None, inject_id=None):
        return self.store.append(
            EventDraft(
                event_type=event_type,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack", inject_id=inject_id),
                payload=payload or {},
            )
        )

    def _restaura_em_outro_processo(self, agora: float) -> dict:
        resultado = subprocess.run(
            [
                sys.executable,
                str(self.RAIZ / "tests" / "_restaura_em_outro_processo.py"),
                repr(agora),
            ],
            capture_output=True,
            text=True,
            cwd=self.RAIZ,
        )
        self.assertEqual(
            resultado.returncode, 0,
            f"o processo novo falhou:\n{resultado.stdout}\n{resultado.stderr}",
        )
        return json.loads(resultado.stdout)

    def test_os_cinco_valores_sobrevivem_ao_banco_e_ao_processo(self) -> None:
        self._append(EXERCISE_STARTED)
        self.parede.avanca(120)  # 120 s de parede em 5x = 600 s de exercicio
        ancora = self._append(INJECT_FIRED, inject_id="A01")
        self.parede.avanca(60)  # +300 s de exercicio
        self._append(
            ROLLBACK_PERFORMED,
            {TO_EVENT_ID: ancora.event_id, "reason": "facilitation"},
            inject_id="A01",
        )

        # O processo morre aqui. Volta 60 s de parede depois — 300 s de exercicio.
        restaurado = self._restaura_em_outro_processo(self.parede.agora + 60)

        self.assertEqual(restaurado["t_zero"], T_ZERO.isoformat())
        self.assertEqual(restaurado["multiplier"], 5.0)
        self.assertFalse(restaurado["paused"])
        self.assertAlmostEqual(restaurado["elapsed_seconds"], 1200, places=0)
        self.assertAlmostEqual(restaurado["epoch_started_at"], 300, places=0)

    def test_pausado_no_banco_volta_pausado_no_processo_novo(self) -> None:
        """A metade que discrimina: o mesmo caminho, com o outro resultado."""
        self._append(EXERCISE_STARTED)
        self.parede.avanca(120)
        self.clock.pause()
        self._append(EXERCISE_PAUSED)

        restaurado = self._restaura_em_outro_processo(self.parede.agora + 3600)

        self.assertTrue(restaurado["paused"])
        self.assertAlmostEqual(restaurado["elapsed_seconds"], 600, places=0)


if __name__ == "__main__":
    unittest.main()
