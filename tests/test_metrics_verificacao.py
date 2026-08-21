"""O computador do lado da verificacao — `TTCV` e `TTRV`.

O que esta suite prova:

1. o computador marca os dois instantes, e o insumo dele **nao alcanca**
   `containment_declared` — que e o defeito de `TTCD` computado de `TTCV`, pelo
   lado que nenhuma regra anterior alcancava;
2. **so a linhagem corrente sustenta a metrica** — veredito de epoch abandonada
   nao vira `TTCV` da epoch nova, e o evento continua legivel no fluxo;
3. o **desconto por uniao** e a **exclusao de `rehearsal`** atravessam ate o
   numero, e nao param no modulo de epoch;
4. ausencia de veredito e `NAO VERIFICADA`, e nao zero.

O insumo e montado por `monta` a partir de um store real, com o mapa de lados
lido do CATALOGO. Um insumo escrito a mao aqui testaria o computador contra uma
particao inventada, e a particao e metade do que esta sob teste.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from contracts.generated.events import (
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    ROLLBACK_PERFORMED,
    VERIFICATION_PREDICATE_SATISFIED,
    VPN_ACCESS_REVOKED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.epoch import MOTIVO_ENSAIO, MOTIVO_FALHA_TECNICA
from range_core.metrics.insumo import monta
from range_core.metrics.verificacao import (
    NOME_DO_PREDICADO,
    PREDICADO_CONTENCAO,
    PREDICADO_RESTAURACAO,
    SIGLA_POR_PREDICADO,
    SemMarcoZero,
    computa,
    marco_zero,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402


def registro() -> dict:
    return parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")


class _ComExercicio(unittest.TestCase):
    """Store real, relogio deterministico: cada append avanca um segundo."""

    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.t_zero = datetime(2026, 8, 20, 9, 0, 0)
        self.store = InMemoryEventStore(
            ExerciseClock(self.t_zero, now=lambda: float(next(parede)))
        )
        self.comeca()

    def comeca(self):
        return self.grava(EXERCISE_STARTED, "facilitation")

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

    def satisfaz(self, nome: str):
        return self.grava(
            VERIFICATION_PREDICATE_SATISFIED, "ground_truth", **{NOME_DO_PREDICADO: nome}
        )

    def rollback(
        self, motivo: str, *, congela: tuple[datetime, datetime] | None = None
    ):
        carga: dict[str, object] = {
            "to_event_id": self.store.read_all()[0].event_id,
            "reason": motivo,
            "by_user": "fac",
            "role": "facilitador",
        }
        if congela is not None:
            carga["frozen_interval"] = {
                "start": congela[0].isoformat(),
                "end": congela[1].isoformat(),
            }
        return self.grava(ROLLBACK_PERFORMED, "facilitation", **carga)

    def insumo(self):
        lados = dict(registro()["x-aurora-registry"]["metric_side"])
        _, verificacao = monta(
            self.store.read_all(),
            lados,
            limiar_de_calibracao=0.15,
            defensibilidade={},
        )
        return verificacao

    def medidas(self) -> dict[str, object]:
        return {m.sigla: m for m in computa(self.insumo())}


class MarcaOsDoisInstantes(_ComExercicio):
    def test_contencao_verificada_marca_ttcv(self):
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        ttcv = self.medidas()["TTCV"]

        self.assertTrue(ttcv.verificada)
        self.assertEqual(ttcv.instante, datetime.fromisoformat(veredito.exercise_timestamp))

    def test_restauracao_verificada_marca_ttrv(self):
        self.satisfaz(PREDICADO_RESTAURACAO)
        self.assertTrue(self.medidas()["TTRV"].verificada)

    def test_um_predicado_nao_arrasta_o_outro(self):
        self.satisfaz(PREDICADO_CONTENCAO)
        medidas = self.medidas()

        self.assertTrue(medidas["TTCV"].verificada)
        self.assertFalse(medidas["TTRV"].verificada)

    def test_sem_veredito_a_medida_e_nao_verificada_e_nao_zero(self):
        """Zero pareceria medicao. `None` diz que nao houve veredito."""
        for sigla, medida in self.medidas().items():
            with self.subTest(sigla=sigla):
                self.assertFalse(medida.verificada)
                self.assertIsNone(medida.instante)
                self.assertIsNone(medida.desde_t0)
                self.assertNotEqual(medida.desde_t0, timedelta())

    def test_o_decorrido_e_medido_desde_t0(self):
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        esperado = datetime.fromisoformat(veredito.exercise_timestamp) - self.t_zero

        self.assertEqual(self.medidas()["TTCV"].desde_t0, esperado)

    def test_as_duas_siglas_saem_sempre_as_duas(self):
        """Metrica que some do AAR e pior que metrica ausente — `03` §3.0."""
        self.assertEqual(set(self.medidas()), {"TTCV", "TTRV"})


class NaoAlcancaOLadoDaDeclaracao(_ComExercicio):
    """A razao de a particao existir, pelo lado que nenhuma regra alcancava.

    `00` §3.2: *"`TTCD` computado a partir de `TTCV` e o mesmo defeito pelo outro
    lado, e nenhuma regra anterior o alcancava"*.
    """

    def test_containment_declared_nao_chega_ao_insumo_de_verificacao(self):
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        tipos = {e.event_type for e in self.insumo().eventos}

        self.assertNotIn(CONTAINMENT_DECLARED, tipos)

    def test_a_declaracao_nao_move_o_veredito(self):
        """Declarar contencao nao verifica contencao — `06` T10, segundo criterio."""
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.assertFalse(self.medidas()["TTCV"].verificada)

    def test_a_acao_com_efeito_no_mundo_chega_e_a_afirmacao_nao(self):
        """`03` §3.1: `vpn_access_revoked` e acao com efeito, e e deste lado."""
        self.grava(VPN_ACCESS_REVOKED, "participant_action")
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        tipos = {e.event_type for e in self.insumo().eventos}

        self.assertIn(VPN_ACCESS_REVOKED, tipos)
        self.assertNotIn(CONTAINMENT_DECLARED, tipos)


class SoALinhagemCorrenteSustenta(_ComExercicio):
    """`09` §3.1: *"satisfacao de epoch abandonada nao conta na corrente"*."""

    def test_veredito_de_epoch_abandonada_nao_vira_ttcv_da_nova(self):
        self.satisfaz(PREDICADO_CONTENCAO)
        self.rollback("facilitation")

        self.assertFalse(self.medidas()["TTCV"].verificada)

    def test_o_veredito_abandonado_continua_legivel_no_fluxo(self):
        """`01` §4.1 — ele nao some; o que ele nao faz e sustentar a metrica."""
        self.satisfaz(PREDICADO_CONTENCAO)
        self.rollback("facilitation")
        tipos = [e.event_type for e in self.store.read_all()]

        self.assertIn(VERIFICATION_PREDICATE_SATISFIED, tipos)

    def test_reemissao_na_epoch_nova_sustenta(self):
        """O controle: sem ele, a regra acima passaria por reprovar sempre."""
        self.satisfaz(PREDICADO_CONTENCAO)
        self.rollback("facilitation")
        reemitido = self.satisfaz(PREDICADO_CONTENCAO)
        ttcv = self.medidas()["TTCV"]

        self.assertTrue(ttcv.verificada)
        self.assertEqual(
            ttcv.instante, datetime.fromisoformat(reemitido.exercise_timestamp)
        )


class EpochAtravessaAteONumero(_ComExercicio):
    """As duas regras de `09` §3.1 nao param no modulo de epoch."""

    # O ROLLBACK VEM ANTES DO VEREDITO, nos dois casos, e nao e arranjo de
    # teste: `technical_failure` tambem abandona a epoch, e um veredito emitido
    # ANTES dele nao sustenta a metrica da epoch nova (`09` §3.1). A primeira
    # versao destes dois testes satisfazia primeiro, e as duas medidas vinham
    # NAO VERIFICADAS — a regra da linhagem corrente pegando o teste dela mesma.

    def test_congelamento_de_duracao_zero_nao_altera_o_decorrido(self):
        """O controle do par: prova que o caminho PASSA pelo desconto.

        Sem ele, um `desde_t0` que ignorasse congelamento nenhum passaria neste
        caso e falharia so no seguinte — e a diferenca entre os dois e o que se
        mede."""
        self.rollback(MOTIVO_FALHA_TECNICA, congela=(self.t_zero, self.t_zero))
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        bruto = datetime.fromisoformat(veredito.exercise_timestamp) - self.t_zero

        self.assertEqual(self.medidas()["TTCV"].desde_t0, bruto)

    def test_congelamento_com_duracao_encurta_o_decorrido_pela_medida_exata(self):
        """O intervalo sai de marcas REAIS do fluxo, e nao de segundos chutados.

        Congela de T0 ate a marca do `exercise_started`: um trecho cuja duracao
        o teste conhece sem depender de quantos segundos cada append avanca.
        """
        abertura = datetime.fromisoformat(self.store.read_all()[0].exercise_timestamp)
        congelado = abertura - self.t_zero
        self.rollback(MOTIVO_FALHA_TECNICA, congela=(self.t_zero, abertura))
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        bruto = datetime.fromisoformat(veredito.exercise_timestamp) - self.t_zero

        descontado = self.medidas()["TTCV"].desde_t0
        self.assertLess(descontado, bruto)
        self.assertEqual(descontado, bruto - congelado)

    def test_veredito_de_epoch_descartada_por_rehearsal_nao_conta(self):
        """DUAS regras o excluem aqui, e a redundancia esta dita.

        A epoch descartada nunca e a corrente — o rollback de `rehearsal` conta
        para `current_epoch`, entao ele descarta a epoch que fecha e a corrente
        passa a ser a seguinte. O filtro de linhagem ja bastaria.

        Onde a exclusao de `rehearsal` MORDE sozinha neste computador e em
        `marco_zero`, e e por isso que o teste de T0 e o unico que fica vermelho
        quando `no_calculo` e neutralizado. A regra isolada esta em
        `tests/test_metrics_epoch.py`, sobre o modulo que a implementa.
        """
        self.satisfaz(PREDICADO_CONTENCAO)
        self.rollback(MOTIVO_ENSAIO)
        self.comeca()

        self.assertFalse(self.medidas()["TTCV"].verificada)


class MarcoZero(_ComExercicio):
    def test_t0_sai_do_exercise_started(self):
        self.assertEqual(marco_zero(self.insumo().epoch), self.t_zero)

    def test_sem_exercise_started_em_calculo_levanta_em_vez_de_devolver_nulo(self):
        """P6-4: alcancavel, e nao teorico — o ensaio descartado e o caso de uso.

        Levantar e a decisao: T0 nulo faria todo `desde_t0` virar `None`, e o AAR
        imprimiria ausencia de medicao onde houve medicao.
        """
        self.rollback(MOTIVO_ENSAIO)
        self.satisfaz(PREDICADO_CONTENCAO)

        with self.assertRaises(SemMarcoZero):
            computa(self.insumo())


class OsPredicadosConferemComOContrato(unittest.TestCase):
    """Predicado novo no `ground_truth.schema.yaml` sem sigla aqui reprova.

    Sem este cruzamento, um terceiro predicado existiria no contrato, seria
    avaliado e emitido pela peca 4, e nenhuma metrica o leria — ausencia que so
    apareceria como sigla faltando no AAR, muito depois.
    """

    def contrato(self) -> dict:
        ground_truth = parse_yaml(REPO_ROOT / "contracts" / "ground_truth.schema.yaml")
        return ground_truth["$defs"]["verification_predicates"]

    def test_as_siglas_cobrem_exatamente_os_predicados_do_contrato(self):
        self.assertEqual(
            set(SIGLA_POR_PREDICADO),
            set(self.contrato()["properties"]),
            "os predicados de `verification_predicates` mudaram. Predicado novo "
            "precisa de sigla em `range-core/metrics/verificacao.py`, ou de "
            "decisao escrita de por que nao tem metrica.",
        )

    def test_o_contrato_e_fechado_e_por_isso_a_lista_e_completa(self):
        """A cobertura acima so vale porque o schema recusa chave extra."""
        self.assertFalse(self.contrato()["additionalProperties"])

    def test_a_chave_do_payload_e_a_mesma_do_emissor(self):
        """Duas constantes com o mesmo papel divergem em silencio — D4."""
        from range_core.engine.verificacao import NOME_DO_PREDICADO as DO_EMISSOR

        self.assertEqual(NOME_DO_PREDICADO, DO_EMISSOR)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
