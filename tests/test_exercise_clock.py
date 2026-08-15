"""O `exercise-clock`: T4 inteiro, mais a separacao que o `a3aded5` normatizou.

O TEMPO DE PAREDE E INJETADO, ENTAO AS ASSERCOES SAO EXATAS
------------------------------------------------------------
Nenhum teste aqui dorme. Um clock que lesse `time.time()` exigiria `sleep` e
tolerancia, e teste com tolerancia sobre relogio ou e lento ou e intermitente —
e intermitente e pior que ausente, porque ensina a reexecutar ate passar.

Com a fonte injetada, "durante o PAUSAR o `exercise_time` nao avanca e o
`wall_timestamp` avanca" vira igualdade, e nao aproximacao.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from range_core.clock.exercise_clock import (
    ALLOWED_MULTIPLIERS,
    ClockError,
    ExerciseClock,
)

T_ZERO = datetime(2026, 8, 13, 9, 0, 0)


class RelogioDeParede:
    """Fonte de tempo controlada pelo teste. Avanca so quando mandam."""

    def __init__(self, inicio: float = 1_000_000.0) -> None:
        self.agora = inicio

    def __call__(self) -> float:
        return self.agora

    def avanca(self, segundos: float) -> None:
        self.agora += segundos


def clock(parede: RelogioDeParede, multiplier: float = 1.0) -> ExerciseClock:
    return ExerciseClock(T_ZERO, now=parede, multiplier=multiplier)


class QuatroMarcas(unittest.TestCase):
    def test_toda_leitura_traz_as_quatro(self):
        marcas = clock(RelogioDeParede()).marks()
        self.assertTrue(marcas.exercise_time.startswith("T+"))
        self.assertTrue(marcas.exercise_timestamp.startswith("2026-08-13T09:00"))
        self.assertTrue(marcas.wall_timestamp)
        self.assertEqual(marcas.clock_multiplier, 1.0)

    def test_em_t_zero_o_rotulo_e_zero(self):
        self.assertEqual(clock(RelogioDeParede()).marks().exercise_time, "T+00:00:00")


class Multiplicador(unittest.TestCase):
    def test_5x_faz_o_exercicio_correr_cinco_vezes_mais(self):
        """T4 — com 5x, o intervalo de parede e ~1/5 do de exercicio.

        Aqui e exatamente 1/5, porque a fonte e controlada: 60 s de parede viram
        300 s de exercicio.
        """
        parede = RelogioDeParede()
        relogio = clock(parede, multiplier=5.0)
        parede.avanca(60)
        self.assertEqual(relogio.marks().exercise_time, "T+00:05:00")

    def test_trocar_de_multiplicador_nao_reescreve_o_que_ja_correu(self):
        """O acumulado fecha com o multiplicador ANTIGO antes da troca.

        Sem isso, passar de 1x para 20x no meio multiplicaria retroativamente o
        tempo ja decorrido, e a timeline do AAR ficaria irreconstruivel apesar de
        `09` §1.1 gravar o multiplicador em cada evento.
        """
        parede = RelogioDeParede()
        relogio = clock(parede)
        parede.avanca(60)                       # 60 s a 1x
        relogio.set_multiplier(20.0)
        parede.avanca(60)                       # mais 60 s a 20x = 1200 s
        self.assertEqual(relogio.marks().exercise_time, "T+00:21:00")

    def test_multiplicador_fora_do_conjunto_e_recusado(self):
        for invalido in (0.0, 2.0, 100.0, -1.0):
            with self.subTest(multiplicador=invalido):
                with self.assertRaises(ClockError):
                    clock(RelogioDeParede(), multiplier=invalido)
        self.assertEqual(ALLOWED_MULTIPLIERS, (1.0, 5.0, 20.0))


class Pausar(unittest.TestCase):
    def test_durante_a_pausa_o_exercicio_congela_e_a_parede_avanca(self):
        """T4, e o item 3 da DoD na metade que e do clock."""
        parede = RelogioDeParede()
        relogio = clock(parede)
        parede.avanca(60)
        relogio.pause()

        antes = relogio.marks()
        parede.avanca(3600)
        depois = relogio.marks()

        self.assertEqual(antes.exercise_time, depois.exercise_time)
        self.assertEqual(antes.exercise_timestamp, depois.exercise_timestamp)
        self.assertNotEqual(antes.wall_timestamp, depois.wall_timestamp)

    def test_as_duas_marcas_de_exercicio_congelam_JUNTAS(self):
        """A norma que o `a3aded5` acrescentou ao `01` §3.

        Antes dela, "`exercise_timestamp` congela no PAUSAR" era implicacao de
        ele ser marca do exercise-clock. `06` T4 passou a exigir os dois nomes, e
        este teste e o que a exigencia cobra.
        """
        parede = RelogioDeParede()
        relogio = clock(parede, multiplier=5.0)
        parede.avanca(120)
        relogio.pause()
        congelado = relogio.marks()

        parede.avanca(9999)
        self.assertEqual(relogio.marks().exercise_timestamp, congelado.exercise_timestamp)

    def test_retomar_continua_de_onde_parou(self):
        parede = RelogioDeParede()
        relogio = clock(parede)
        parede.avanca(60)
        relogio.pause()
        parede.avanca(3600)          # uma hora de parede, nenhuma de exercicio
        relogio.resume()
        parede.avanca(60)

        self.assertEqual(relogio.marks().exercise_time, "T+00:02:00")

    def test_pausa_dupla_e_retomada_sem_pausa_sao_recusadas(self):
        """Nao sao idempotentes por desenho.

        Pausa dupla costuma ser dois facilitadores agindo sobre o mesmo
        exercicio, e silenciar isso esconde o conflito.
        """
        relogio = clock(RelogioDeParede())
        with self.assertRaises(ClockError):
            relogio.resume()
        relogio.pause()
        with self.assertRaises(ClockError):
            relogio.pause()

    def test_is_paused_e_o_que_o_engine_consulta(self):
        """A outra metade do item 3 — "bloqueia disparo agendado" — e do engine.

        O clock nao agenda e nao dispara; ele responde. Quem decide nao disparar
        e quem dispara.
        """
        relogio = clock(RelogioDeParede())
        self.assertFalse(relogio.is_paused)
        relogio.pause()
        self.assertTrue(relogio.is_paused)


class EpochRebobina(unittest.TestCase):
    def test_o_rotulo_volta_e_o_timestamp_nao(self):
        """A separacao normatizada em `01` §3, e a razao de haver duas marcas.

        Sem ela, `09` §1.1 nao teria como ordenar eventos de epochs distintas —
        e o intervalo congelado de `06` T3 nao teria onde ser marcado.
        """
        parede = RelogioDeParede()
        relogio = clock(parede)
        parede.avanca(600)
        antes = relogio.marks()
        self.assertEqual(antes.exercise_time, "T+00:10:00")

        relogio.start_new_epoch(at_exercise_seconds=120)
        depois = relogio.marks()

        self.assertEqual(depois.exercise_time, "T+00:08:00", "o rotulo T+ rebobinou")
        self.assertEqual(
            depois.exercise_timestamp,
            antes.exercise_timestamp,
            "o timestamp absoluto NAO rebobina — e o que ordena entre epochs",
        )

    def test_ponto_de_corte_negativo_e_recusado(self):
        with self.assertRaises(ClockError):
            clock(RelogioDeParede()).start_new_epoch(at_exercise_seconds=-1)


class ClockMaisStore(unittest.TestCase):
    """O clock preenchendo a porta que o store ja consumia."""

    def test_evento_gravado_durante_a_pausa_carrega_o_tempo_congelado(self):
        from test_event_store import started_draft
        from range_core.events.store import InMemoryEventStore

        parede = RelogioDeParede()
        relogio = clock(parede)
        store = InMemoryEventStore(relogio)

        parede.avanca(60)
        relogio.pause()
        parede.avanca(3600)
        evento = store.append(started_draft())

        self.assertEqual(evento.exercise_time, "T+00:01:00")


if __name__ == "__main__":
    unittest.main()
