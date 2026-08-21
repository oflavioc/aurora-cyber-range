"""O computador do lado da declaracao — as seis siglas, e a clausula herdada.

O que esta suite prova:

1. as tres metades de declaracao (`TTCD`, `TTRD`, `TTID`) e as tres simples
   (`TTA`, `TTT`, `TTCM`), com start e stop de `03` §3;
2. o insumo **nao alcanca** `verification_predicate_satisfied` — metrica simples
   computada a partir do veredito e o primeiro dos dois defeitos de `00` §3.2;
3. a **clausula herdada** de `03` §3.4: declaracao isolada nao marca `TTID`, e o
   evento que marca e o que COMPLETA, nunca o primeiro;
4. os quatro efeitos de epoch de `09` §3.1 atravessam ate o numero.

O insumo e montado por `monta` sobre um store real, com o mapa de lados lido do
CATALOGO.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from contracts.generated.events import (
    CLASSIFICATION_DECLARED,
    COMMUNICATION_SUBMITTED,
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    INCIDENT_DECLARED,
    INJECT_FIRED,
    INTEGRITY_VALIDATION_DECLARED,
    REGULATORY_NOTICE_SUBMITTED,
    ROLLBACK_PERFORMED,
    SERVICE_RESTORATION_DECLARED,
    VERIFICATION_PREDICATE_SATISFIED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.declarations.contrassinatura import (
    PERSONA_QUE_CONTRASSINA,
    PERSONA_QUE_DECLARA_INTEGRIDADE,
)
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.declaracao import EXIGE_RESPOSTA, IMPACTO_OBSERVAVEL, computa
from range_core.metrics.epoch import (
    MOTIVO_ADJUDICACAO,
    MOTIVO_ENSAIO,
    MOTIVO_FACILITACAO,
    MOTIVO_FALHA_TECNICA,
)
from range_core.metrics.insumo import monta

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

AS_SEIS = {"TTCD", "TTRD", "TTID", "TTA", "TTT", "TTCM"}


class _ComExercicio(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.t_zero = datetime(2026, 8, 20, 9, 0, 0)
        self.store = InMemoryEventStore(
            ExerciseClock(self.t_zero, now=lambda: float(next(parede)))
        )
        self.grava(EXERCISE_STARTED, "facilitation")

    def grava(self, tipo: str, camada: str, *, correlation=None, **payload):
        return self.store.append(
            EventDraft(
                event_type=tipo,
                truth_layer=camada,
                producer="teste",
                correlation=correlation or Correlation(),
                payload=payload,
            )
        )

    def dispara(self, inject_id: str, *, impacto: bool = False, resposta: bool = False):
        return self.grava(
            INJECT_FIRED,
            "facilitation",
            correlation=Correlation(inject_id=inject_id),
            **{IMPACTO_OBSERVAVEL: impacto, EXIGE_RESPOSTA: resposta},
        )

    def submete(self, tipo: str, inject_id: str):
        return self.grava(
            tipo, "participant_action", correlation=Correlation(inject_id=inject_id)
        )

    def integridade(self, persona: str, actor_id: str, causation_id: str | None = None):
        evento = EventDraft(
            event_type=INTEGRITY_VALIDATION_DECLARED,
            truth_layer="participant_action",
            producer="teste",
            correlation=Correlation(causation_id=causation_id),
            payload={},
            actor_id=actor_id,
            persona=persona,
        )
        return self.store.append(evento)

    def rollback(self, motivo: str, *, congela=None):
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
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        declaracao, _ = monta(
            self.store.read_all(), lados, limiar_de_calibracao=0.15, defensibilidade={}
        )
        return declaracao

    def medidas(self):
        return {m.sigla: m for m in computa(self.insumo()) if m.sigla != "TTCM"}

    def ttcm(self):
        return [m for m in computa(self.insumo()) if m.sigla == "TTCM"]


class AsTresMetadesDeDeclaracao(_ComExercicio):
    """`TTCD`, `TTRD` e `TTID` marcam instante desde T0."""

    def test_contencao_declarada_marca_ttcd(self):
        declarado = self.grava(CONTAINMENT_DECLARED, "participant_action")
        ttcd = self.medidas()["TTCD"]

        self.assertTrue(ttcd.marcada)
        self.assertEqual(ttcd.inicio, self.t_zero)
        self.assertEqual(
            ttcd.fim, datetime.fromisoformat(declarado.exercise_timestamp)
        )
        self.assertEqual(ttcd.decorrido, ttcd.fim - self.t_zero)

    def test_restauracao_declarada_marca_ttrd(self):
        self.grava(SERVICE_RESTORATION_DECLARED, "participant_action")
        self.assertTrue(self.medidas()["TTRD"].marcada)

    def test_a_primeira_declaracao_marca_e_nao_a_ultima(self):
        """Redeclarar nao melhora a metrica — `03` §3 mede o tempo ATE."""
        primeira = self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.grava(CONTAINMENT_DECLARED, "participant_action")

        self.assertEqual(
            self.medidas()["TTCD"].fim,
            datetime.fromisoformat(primeira.exercise_timestamp),
        )

    def test_sem_declaracao_a_medida_nao_e_marcada_e_nao_e_zero(self):
        for sigla, medida in self.medidas().items():
            with self.subTest(sigla=sigla):
                self.assertFalse(medida.marcada)
                self.assertIsNone(medida.decorrido)
                self.assertNotEqual(medida.decorrido, timedelta())

    def test_as_seis_siglas_saem_sempre(self):
        saida = {m.sigla for m in computa(self.insumo())}
        self.assertEqual(saida, AS_SEIS)


class AClausulaHerdadaDoTTID(_ComExercicio):
    """`03` §3.4 — o quarto negativo, que e do CONSUMIDOR e nao da emissao."""

    def test_declaracao_isolada_nao_marca_ttid(self):
        """A clausula herdada, literal. Ela e gravada e fica registrada."""
        self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")

        self.assertFalse(self.medidas()["TTID"].marcada)

    def test_a_declaracao_isolada_continua_no_fluxo(self):
        """A ausencia de contrassinatura e achado do AAR, nao erro de emissao."""
        self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        tipos = [e.event_type for e in self.store.read_all()]

        self.assertIn(INTEGRITY_VALIDATION_DECLARED, tipos)

    def test_ttid_marca_o_evento_que_completa_e_nao_o_primeiro(self):
        primeiro = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        segundo = self.integridade(
            PERSONA_QUE_CONTRASSINA, "analista-ti", causation_id=primeiro.event_id
        )
        ttid = self.medidas()["TTID"]

        self.assertTrue(ttid.marcada)
        self.assertEqual(ttid.fim, datetime.fromisoformat(segundo.exercise_timestamp))
        self.assertNotEqual(
            ttid.fim, datetime.fromisoformat(primeiro.exercise_timestamp)
        )

    def test_autocontrassinatura_pela_mesma_credencial_nao_marca(self):
        """Condicao (4) de §3.4 — `actor_id` identifica CREDENCIAL."""
        primeiro = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "mesma")
        self.integridade(
            PERSONA_QUE_CONTRASSINA, "mesma", causation_id=primeiro.event_id
        )

        self.assertFalse(self.medidas()["TTID"].marcada)

    def test_ordem_invertida_nao_marca(self):
        """Condicao (2) — TI nao abre, a competencia nao e simetrica."""
        primeiro = self.integridade(PERSONA_QUE_CONTRASSINA, "analista-ti")
        self.integridade(
            PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora", causation_id=primeiro.event_id
        )

        self.assertFalse(self.medidas()["TTID"].marcada)

    def test_contrassinatura_sem_antecedente_nao_marca(self):
        """Condicao (1) — `causation_id` que nao aponta para uma anterior."""
        self.integridade(
            PERSONA_QUE_CONTRASSINA, "analista-ti", causation_id="nao-existe"
        )

        self.assertFalse(self.medidas()["TTID"].marcada)

    def test_cadeia_de_tres_nao_marca_a_terceira(self):
        """Condicao (3) — o par tem duas maos, e nao tres.

        A SEGUNDA completa e marca; a terceira aponta para uma contrassinatura e
        nao completa nada. `TTID` fica na segunda, que e onde a integridade passou
        a estar validada.
        """
        primeiro = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        segundo = self.integridade(
            PERSONA_QUE_CONTRASSINA, "analista-ti", causation_id=primeiro.event_id
        )
        self.integridade(
            PERSONA_QUE_CONTRASSINA, "outro-ti", causation_id=segundo.event_id
        )

        self.assertEqual(
            self.medidas()["TTID"].fim,
            datetime.fromisoformat(segundo.exercise_timestamp),
        )


class AsTresSimples(_ComExercicio):
    """`TTA`, `TTT` e `TTCM` — start e stop proprios, `03` §3."""

    def test_tta_vai_do_primeiro_inject_observavel_ao_incidente(self):
        self.dispara("A00", impacto=False)
        observavel = self.dispara("A01", impacto=True)
        self.dispara("A02", impacto=True)
        declarado = self.grava(INCIDENT_DECLARED, "participant_action")
        tta = self.medidas()["TTA"]

        self.assertEqual(
            tta.inicio, datetime.fromisoformat(observavel.exercise_timestamp)
        )
        self.assertEqual(tta.fim, datetime.fromisoformat(declarado.exercise_timestamp))

    def test_inject_sem_impacto_observavel_nao_abre_tta(self):
        """`reveals` alimenta crenca, e nao o mundo — `03` §3."""
        self.dispara("A00", impacto=False)
        self.grava(INCIDENT_DECLARED, "participant_action")

        self.assertFalse(self.medidas()["TTA"].marcada)

    def test_tta_sem_inject_observavel_nao_vira_zero_desde_t0(self):
        self.grava(INCIDENT_DECLARED, "participant_action")
        tta = self.medidas()["TTA"]

        self.assertIsNone(tta.inicio)
        self.assertIsNone(tta.decorrido)

    def test_ttt_vai_do_incidente_a_classificacao(self):
        incidente = self.grava(INCIDENT_DECLARED, "participant_action")
        classificacao = self.grava(CLASSIFICATION_DECLARED, "participant_action")
        ttt = self.medidas()["TTT"]

        self.assertEqual(
            ttt.inicio, datetime.fromisoformat(incidente.exercise_timestamp)
        )
        self.assertEqual(
            ttt.fim, datetime.fromisoformat(classificacao.exercise_timestamp)
        )

    def test_incidente_sem_classificacao_nao_marca_ttt(self):
        self.grava(INCIDENT_DECLARED, "participant_action")
        self.assertFalse(self.medidas()["TTT"].marcada)


class TTCMEUmaPorInject(_ComExercicio):
    def test_a_submissao_correspondente_fecha_pelo_inject_id(self):
        inject = self.dispara("A05", resposta=True)
        self.submete(COMMUNICATION_SUBMITTED, "A05")
        resposta = self.store.read_all()[-1]
        [ttcm] = self.ttcm()

        self.assertEqual(ttcm.referencia, "A05")
        self.assertEqual(
            ttcm.inicio, datetime.fromisoformat(inject.exercise_timestamp)
        )
        self.assertEqual(ttcm.fim, datetime.fromisoformat(resposta.exercise_timestamp))

    def test_submissao_de_outro_inject_nao_fecha(self):
        """Sem o `inject_id`, qualquer submissao fecharia qualquer inject."""
        self.dispara("A05", resposta=True)
        self.submete(COMMUNICATION_SUBMITTED, "A09")
        [ttcm] = self.ttcm()

        self.assertFalse(ttcm.marcada)
        self.assertEqual(ttcm.referencia, "A05")

    def test_inject_sem_resposta_produz_medida_nao_marcada_e_nao_some(self):
        """O AAR precisa saber que houve inject exigindo resposta sem resposta."""
        self.dispara("A05", resposta=True)
        [ttcm] = self.ttcm()

        self.assertFalse(ttcm.marcada)

    def test_uma_medida_por_inject_que_exige_resposta(self):
        self.dispara("A05", resposta=True)
        self.dispara("A06", resposta=True)
        self.dispara("A07", resposta=False)
        self.submete(REGULATORY_NOTICE_SUBMITTED, "A06")

        referencias = {m.referencia: m.marcada for m in self.ttcm()}
        self.assertEqual(referencias, {"A05": False, "A06": True})

    def test_os_dois_tipos_de_submissao_fecham(self):
        for inject_id, tipo in (
            ("A10", COMMUNICATION_SUBMITTED),
            ("A11", REGULATORY_NOTICE_SUBMITTED),
        ):
            with self.subTest(tipo=tipo):
                self.dispara(inject_id, resposta=True)
                self.submete(tipo, inject_id)

        self.assertTrue(all(m.marcada for m in self.ttcm()))


class NaoAlcancaOLadoDaVerificacao(_ComExercicio):
    """`00` §3.2 — metrica simples computada do veredito e o primeiro defeito."""

    def test_o_veredito_nao_chega_ao_insumo_de_declaracao(self):
        self.grava(
            VERIFICATION_PREDICATE_SATISFIED, "ground_truth", predicate="containment"
        )
        tipos = {e.event_type for e in self.insumo().eventos}

        self.assertNotIn(VERIFICATION_PREDICATE_SATISFIED, tipos)

    def test_o_veredito_nao_marca_ttcd(self):
        """Contencao verificada nao e contencao declarada."""
        self.grava(
            VERIFICATION_PREDICATE_SATISFIED, "ground_truth", predicate="containment"
        )

        self.assertFalse(self.medidas()["TTCD"].marcada)


class OsQuatroEfeitosDeEpoch(_ComExercicio):
    """`09` §3.1 — cada `reason` tem efeito proprio, e os quatro chegam ao numero."""

    def test_technical_failure_desconta_tempo_e_NAO_descarta_a_declaracao(self):
        """*"A equipe nao e penalizada por bug do ambiente"* — ela nao redeclara."""
        declarado = self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.rollback(
            MOTIVO_FALHA_TECNICA,
            congela=(self.t_zero, datetime.fromisoformat(declarado.exercise_timestamp)),
        )
        ttcd = self.medidas()["TTCD"]

        self.assertTrue(ttcd.marcada)
        self.assertEqual(ttcd.decorrido, timedelta())

    def test_facilitation_recomeca_a_contagem_na_epoch_nova(self):
        """*"Metricas recomputadas a partir da nova epoch"* — a anterior sai."""
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.rollback(MOTIVO_FACILITACAO)

        self.assertFalse(self.medidas()["TTCD"].marcada)

    def test_adjudication_recomeca_igual(self):
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.rollback(MOTIVO_ADJUDICACAO)

        self.assertFalse(self.medidas()["TTCD"].marcada)

    def test_declaracao_da_epoch_nova_conta_depois_de_facilitation(self):
        """O controle: sem ele, as duas regras acima passariam por reprovar sempre."""
        self.rollback(MOTIVO_FACILITACAO)
        self.grava(CONTAINMENT_DECLARED, "participant_action")

        self.assertTrue(self.medidas()["TTCD"].marcada)

    def test_rehearsal_tira_a_epoch_do_calculo(self):
        self.grava(CONTAINMENT_DECLARED, "participant_action")
        self.rollback(MOTIVO_ENSAIO)
        self.grava(EXERCISE_STARTED, "facilitation")

        self.assertFalse(self.medidas()["TTCD"].marcada)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
