"""O predicado de completude da contrassinatura — as três recusas de emissão.

`03_EXERCISE_DESIGN.md` §3.4 nomeia **quatro** negativos. Três são de emissão e
são provados aqui, com violação plantada:

1. contrassinatura **sem antecedente**;
2. **autocontrassinatura** — por persona fora da ordem, ou por reuso de credencial;
3. contrassinatura de **antecedente já completado**.

O quarto — *"declaração isolada não marca `TTID`"* — **não é de emissão**: a
declaração é gravada e fica registrada, e a ausência de contrassinatura é achado
do AAR. Quem o executa é o computador de métrica, que é a **peça 5**. Está
registrado como cláusula herdada em `docs/progress/fase_6.md`, e testá-lo aqui
exigiria inventar o consumidor — que é a forma de um teste passar por motivo
errado.

O que este arquivo prova é o **positivo** correspondente: a declaração isolada
grava, e grava sem sucessor. É a metade que sustenta a outra.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from contracts.generated.events import INTEGRITY_VALIDATION_DECLARED
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore
from range_core.participant.api.emissor import EmissaoRecusada, Emissor


def _relogio() -> ExerciseClock:
    """Relógio determinista — o mesmo aparato das outras suítes de store.

    As marcas são carimbadas pelo store (D1), e um relógio de parede real faria
    o teste depender do momento em que roda.
    """
    parede = iter(range(1_000_000, 1_100_000))
    return ExerciseClock(
        datetime(2026, 8, 20, 9, 0, 0), now=lambda: float(next(parede))
    )


class _ComEmissor(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryEventStore(_relogio())
        self.emissor = Emissor(self.store)

    def declara(self, persona: str, actor_id: str, causation_id: str | None = None):
        return self.emissor.declarar(
            INTEGRITY_VALIDATION_DECLARED,
            persona=persona,
            actor_id=actor_id,
            justificativa="conferido contra a trilha",
            causation_id=causation_id,
        )

    def recusa(self, trecho: str, **kwargs) -> None:
        with self.assertRaises(EmissaoRecusada) as capturado:
            self.declara(**kwargs)
        self.assertIn(trecho, str(capturado.exception))


class OParCompleto(_ComEmissor):
    """Sem o positivo, nenhuma recusa abaixo significa alguma coisa."""

    def test_pro_reitoria_abre_e_ti_contrassina(self):
        primeiro = self.declara("pro_reitoria", "cred-pro")
        segundo = self.declara("ti", "cred-ti", primeiro.event_id)
        self.assertEqual(segundo.correlation.causation_id, primeiro.event_id)

    def test_declaracao_isolada_grava_e_fica_sem_sucessor(self):
        """O POSITIVO do quarto negativo, que é o que cabe a este bloco.

        *"Declaração isolada não marca `TTID`"* é do consumidor, e o consumidor
        é a peça 5. O que se prova aqui é que ela **existe no fluxo** e não tem
        sucessor — sem isso, a cláusula herdada não teria sobre o que operar.
        """
        primeiro = self.declara("pro_reitoria", "cred-pro")
        sucessores = [
            e
            for e in self.store.read_all()
            if e.correlation.causation_id == primeiro.event_id
        ]
        self.assertEqual(sucessores, [])


class TresRecusasDeEmissao(_ComEmissor):
    def test_contrassinatura_sem_antecedente(self):
        self.recusa(
            "sem antecedente",
            persona="ti",
            actor_id="cred-ti",
            causation_id="evento-que-nao-existe",
        )

    def test_autocontrassinatura_pela_mesma_credencial(self):
        """A condição (2) não cobre esta: um operador com duas credenciais
        satisfaria as personas. `actor_id` identifica **credencial**."""
        primeiro = self.declara("pro_reitoria", "cred-unica")
        self.recusa(
            "autocontrassinatura",
            persona="ti",
            actor_id="cred-unica",
            causation_id=primeiro.event_id,
        )

    def test_ordem_invertida_e_recusada(self):
        """TI não abre o par: a competência não é simétrica."""
        self.recusa("nao abre a validacao", persona="ti", actor_id="cred-ti")

    def test_antecedente_ja_completado(self):
        """O par tem duas mãos e **um** fechamento.

        Sem esta recusa, duas contrassinaturas com `actor_id` distintos sobre a
        mesma declaração satisfariam as quatro condições, e o computador de
        `TTID` escolheria sozinho qual delas marca — a ambiguidade que o bloco
        de `03` §3.4 existe para fechar, entrando por porta lateral.
        """
        primeiro = self.declara("pro_reitoria", "cred-pro")
        self.declara("ti", "cred-ti-a", primeiro.event_id)
        self.recusa(
            "ja foi completado",
            persona="ti",
            actor_id="cred-ti-b",
            causation_id=primeiro.event_id,
        )

    def test_cadeia_de_tres_e_recusada(self):
        """Condição (3): o antecedente não pode ser ele próprio um segundo."""
        primeiro = self.declara("pro_reitoria", "cred-pro")
        segundo = self.declara("ti", "cred-ti", primeiro.event_id)
        self.recusa(
            "ja e uma contrassinatura",
            persona="ti",
            actor_id="cred-ti-2",
            causation_id=segundo.event_id,
        )


class JustificativaObrigatoria(_ComEmissor):
    """`03` §3.4 a exige de cada uma — é o que o AAR cita quando o delta vira achado."""

    def test_justificativa_vazia_recusa(self):
        with self.assertRaises(EmissaoRecusada) as capturado:
            self.emissor.declarar(
                INTEGRITY_VALIDATION_DECLARED,
                persona="pro_reitoria",
                actor_id="cred-pro",
                justificativa="   ",
            )
        self.assertIn("justificativa", str(capturado.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
