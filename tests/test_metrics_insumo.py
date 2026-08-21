"""O insumo tipado por lado — a partição de `00` §3.2 como código.

O que esta suíte prova:

1. cada lado recebe **apenas** os seus eventos, pelo `metric_side` do catálogo;
2. a **escrituração de epoch vai inteira para os dois**, e não recortada — é o
   que torna o desconto por união cálculo do consumidor;
3. os **escalares** do lado de verificação chegam no insumo, e não por consulta;
4. o veredito de verificação **não alcança** o lado da declaração, e a declaração
   não alcança o de verificação — que é a razão de a partição existir.

O mapa de lados vem do **catálogo real**, e não de um dicionário escrito aqui:
um mapa próprio divergiria do contrato em silêncio, e é exatamente a divergência
que `metric_side` existe para fechar.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import (
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
    VERIFICATION_PREDICATE_SATISFIED,
    VPN_ACCESS_REVOKED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.insumo import (
    EscrituracaoDeEpoch,
    InsumoDeDeclaracao,
    InsumoDeVerificacao,
    monta,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402


def lados_do_catalogo() -> dict[str, str]:
    """O `metric_side` real. Um mapa próprio aqui divergiria em silêncio."""
    registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
    return dict(registro["x-aurora-registry"]["metric_side"])


class _ComFluxo(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 20, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.grava(EXERCISE_STARTED, "facilitation")
        self.grava(INJECT_FIRED, "facilitation", observable_impact=True,
                   requires_response=False)
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.grava(VPN_ACCESS_REVOKED, "participant_action")
        self.grava(VERIFICATION_PREDICATE_SATISFIED, "ground_truth", predicate="containment")

    def grava(self, tipo: str, camada: str, **payload):
        return self.store.append(
            EventDraft(
                event_type=tipo,
                truth_layer=camada,
                producer="teste",
                correlation=Correlation(),
                payload=payload,
            )
        )

    def monta(self):
        return monta(
            self.store.read_all(),
            lados_do_catalogo(),
            limiar_de_calibracao=0.15,
            defensibilidade={"GC-029": 1.0},
        )


class CadaLadoRecebeOSeu(_ComFluxo):
    def test_a_declaracao_nao_alcanca_o_veredito(self):
        """A razão de a partição existir — `00` §3.2."""
        declaracao, _ = self.monta()
        tipos = {e.event_type for e in declaracao.eventos}
        self.assertIn(CONTAINMENT_DECLARED, tipos)
        self.assertNotIn(VERIFICATION_PREDICATE_SATISFIED, tipos)
        self.assertNotIn(VPN_ACCESS_REVOKED, tipos)

    def test_a_verificacao_nao_alcanca_a_declaracao(self):
        """O outro lado do mesmo defeito: `TTCD` computado de `TTCV`."""
        _, verificacao = self.monta()
        tipos = {e.event_type for e in verificacao.eventos}
        self.assertIn(VERIFICATION_PREDICATE_SATISFIED, tipos)
        self.assertIn(VPN_ACCESS_REVOKED, tipos)
        self.assertNotIn(CONTAINMENT_DECLARED, tipos)

    def test_o_start_de_tta_esta_no_lado_da_declaracao(self):
        """`inject_fired` é `metric_side: declaration` — ele fornece os starts."""
        declaracao, _ = self.monta()
        self.assertIn(INJECT_FIRED, {e.event_type for e in declaracao.eventos})


class EpochVaiInteiraParaOsDois(_ComFluxo):
    """Não é recorte na montagem — é insumo próprio, e o desconto é cálculo."""

    def test_a_escrituracao_e_a_mesma_nos_dois_insumos(self):
        # COM `frozen_interval`: o `if/then` de `rollback_payload` o exige quando
        # `reason` e `technical_failure`, e a fixture sem ele descrevia um evento
        # que o contrato recusa. Passava porque o store em memoria nao valida
        # payload — e fixture invalida que passa e a que vira armadilha para o
        # proximo leitor, que e quem monta o computador que le este campo.
        self.grava(
            ROLLBACK_PERFORMED,
            "facilitation",
            to_event_id=self.store.read_all()[0].event_id,
            reason="technical_failure",
            by_user="fac",
            role="facilitador",
            frozen_interval={
                "start": "2026-08-20T09:05:00",
                "end": "2026-08-20T09:25:00",
            },
        )
        declaracao, verificacao = self.monta()
        self.assertEqual(declaracao.epoch, verificacao.epoch)
        self.assertIn(
            ROLLBACK_PERFORMED, {e.event_type for e in declaracao.epoch}
        )

    def test_a_escrituracao_nao_entra_nos_eventos_do_lado(self):
        """`epoch` é lado próprio: `rollback_performed` não é evento de métrica."""
        declaracao, verificacao = self.monta()
        for insumo in (declaracao, verificacao):
            self.assertNotIn(
                ROLLBACK_PERFORMED, {e.event_type for e in insumo.eventos}
            )


class EscalaresNoInsumo(_ComFluxo):
    """`00` §3.2 — proíbe-se ter por onde buscar mais, não ter o necessário."""

    def test_o_verificador_recebe_limiar_e_defensibilidade(self):
        _, verificacao = self.monta()
        self.assertEqual(verificacao.limiar_de_calibracao, 0.15)
        self.assertEqual(verificacao.defensibilidade["GC-029"], 1.0)

    def test_nenhum_insumo_tem_store_pack_ou_fluxo_total(self):
        """A forma do `project` do fold: não consulta porque não tem por onde."""
        declaracao, verificacao = self.monta()
        for insumo, esperados in (
            (declaracao, {"eventos", "epoch"}),
            (
                verificacao,
                {"eventos", "epoch", "limiar_de_calibracao", "defensibilidade"},
            ),
        ):
            with self.subTest(insumo=type(insumo).__name__):
                self.assertEqual(set(vars(insumo)), esperados)


class TipoProprio(unittest.TestCase):
    def test_os_tres_tipos_sao_distintos(self):
        """`Sequence[Event]` não negaria nada — o fluxo inteiro o satisfaz."""
        nomes = {
            InsumoDeDeclaracao.__annotations__["eventos"],
            InsumoDeVerificacao.__annotations__["eventos"],
            EscrituracaoDeEpoch,
        }
        self.assertEqual(len(nomes), 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
