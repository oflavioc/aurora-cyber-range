"""A projeção `objective_evidence` — o binding calculado, e a regra de T9.

O que esta suíte prova:

1. o vínculo evento → objetivo é **calculado da projeção**, e não lido do
   evento — o invariante 4 (`09` §1.2). O `Event` nem tem campo onde caberia,
   e o teste afirma isso pela porta que importa: dois objetivos diferentes
   ligados ao mesmo `event_type` são ambos satisfeitos pelo mesmo evento;
2. `06` T9: *objetivo com evidência `auto` não satisfeita não é classificado
   como `excellent`*, e a recusa é de admissibilidade, não de cálculo;
3. `03` §2.1: comparação entre versões de rubrica é recusada.

Os objetivos vêm do exemplo NORMATIVO do contrato, e não de um dicionário
escrito aqui: `03` §1.1 é a forma, e um fixture próprio divergiria dela em
silêncio — que é o defeito que `check_spec_examples.py` existe para fechar.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from contracts.generated.events import (
    AUDIT_QUERY_PERFORMED,
    OBSERVED_MARKER_SET,
    SEPARATE_INCIDENT_DECLARED,
)
from range_core.events.envelope import Correlation, Event
from range_core.objectives.projecao import (
    EvidenciaDeObjetivo,
    ObjectiveProjectionError,
    comparavel,
    objetivos_de,
    project,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRATO = REPO_ROOT / "contracts" / "objectives.schema.yaml"


def objetivos_normativos():
    documento = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))["examples"][0]
    return objetivos_de(documento)


def evento(event_type: str, **payload) -> Event:
    return Event(
        event_id=f"ev-{event_type}-{len(payload)}",
        event_type=event_type,
        truth_layer="participant_action",
        producer="teste",
        exercise_time="T+00:01:00",
        exercise_timestamp="2026-08-19T10:01:00",
        wall_timestamp="2026-08-19T10:01:00-03:00",
        clock_multiplier=1,
        simulation_epoch=0,
        correlation=Correlation(),
        payload=payload or {},
    )


class FormaNormativa(unittest.TestCase):
    def test_le_o_exemplo_do_contrato(self):
        objetivos = objetivos_normativos()
        self.assertEqual(list(objetivos), ["OBJ-03"])
        obj = objetivos["OBJ-03"]
        self.assertEqual(obj.rubric, "incident_triage.v2")
        self.assertEqual(
            set(obj.auto), {AUDIT_QUERY_PERFORMED, SEPARATE_INCIDENT_DECLARED}
        )
        self.assertEqual(
            [m.marker_id for m in obj.observed], ["articulated_competing_hypotheses"]
        )

    def test_marcador_observed_repetido_reprova(self):
        documento = {
            "objectives": {
                "OBJ-01": {
                    "title": "t",
                    "competency": "escalation",
                    "rubric": "escalation.v1",
                    "evidence": {
                        "observed": [
                            {"id": "mesmo", "prompt_to_evaluator": "p1"},
                            {"id": "mesmo", "prompt_to_evaluator": "p2"},
                        ]
                    },
                }
            }
        }
        with self.assertRaises(ObjectiveProjectionError) as capturado:
            objetivos_de(documento)
        self.assertIn("repetido", str(capturado.exception))


class BindingNaProjecao(unittest.TestCase):
    """Invariante 4: o vínculo é calculado aqui, e não viaja no evento."""

    def test_fluxo_vazio_deixa_toda_evidencia_ausente(self):
        evidencia = project([], objetivos_normativos())["OBJ-03"]
        self.assertEqual(evidencia.auto_satisfeita, frozenset())
        self.assertEqual(
            evidencia.auto_ausente,
            frozenset({AUDIT_QUERY_PERFORMED, SEPARATE_INCIDENT_DECLARED}),
        )
        self.assertFalse(evidencia.auto_completa)

    def test_o_mesmo_evento_satisfaz_dois_objetivos_diferentes(self):
        """A prova de que o vínculo NÃO está no evento.

        Se `objective_ids` viajasse no envelope, um evento pertenceria a um
        conjunto fixo de objetivos, decidido por quem o emitiu. Aqui o mesmo
        evento satisfaz quantos objetivos o pack ligar a ele — e é o pack que
        liga, sem que o produtor saiba.
        """
        objetivos = objetivos_de(
            {
                "objectives": {
                    "OBJ-01": {
                        "title": "a",
                        "competency": "escalation",
                        "rubric": "incident_triage.v2",
                        "evidence": {"auto": [AUDIT_QUERY_PERFORMED]},
                    },
                    "OBJ-03": {
                        "title": "b",
                        "competency": "incident_triage",
                        "rubric": "incident_triage.v2",
                        "evidence": {"auto": [AUDIT_QUERY_PERFORMED]},
                    },
                }
            }
        )
        resultado = project([evento(AUDIT_QUERY_PERFORMED)], objetivos)
        self.assertTrue(resultado["OBJ-01"].auto_completa)
        self.assertTrue(resultado["OBJ-03"].auto_completa)

    def test_cobertura_parcial_separa_o_que_apareceu_do_que_falta(self):
        evidencia = project(
            [evento(AUDIT_QUERY_PERFORMED)], objetivos_normativos()
        )["OBJ-03"]
        self.assertEqual(evidencia.auto_satisfeita, frozenset({AUDIT_QUERY_PERFORMED}))
        self.assertEqual(
            evidencia.auto_ausente, frozenset({SEPARATE_INCIDENT_DECLARED})
        )

    def test_marcador_observed_vem_de_observed_marker_set(self):
        eventos = [evento(OBSERVED_MARKER_SET, marker_id="articulated_competing_hypotheses")]
        evidencia = project(eventos, objetivos_normativos())["OBJ-03"]
        self.assertEqual(
            evidencia.observed_marcado, frozenset({"articulated_competing_hypotheses"})
        )
        self.assertEqual(evidencia.observed_ausente, frozenset())

    def test_marcacao_de_outro_marcador_nao_conta(self):
        eventos = [evento(OBSERVED_MARKER_SET, marker_id="outro_marcador")]
        evidencia = project(eventos, objetivos_normativos())["OBJ-03"]
        self.assertEqual(evidencia.observed_marcado, frozenset())


class T9_EvidenciaAntesDeJulgamento(unittest.TestCase):
    """`06` T9 — a regra é de admissibilidade, e só sobre `excellent`."""

    def _com(self, ausente: bool) -> EvidenciaDeObjetivo:
        eventos = [] if ausente else [
            evento(AUDIT_QUERY_PERFORMED),
            evento(SEPARATE_INCIDENT_DECLARED),
        ]
        return project(eventos, objetivos_normativos())["OBJ-03"]

    def test_auto_incompleta_nao_admite_excellent(self):
        self.assertFalse(self._com(ausente=True).admite("excellent"))

    def test_auto_completa_admite_excellent(self):
        completa = self._com(ausente=False)
        self.assertTrue(completa.auto_completa)
        self.assertTrue(completa.admite("excellent"))

    def test_auto_incompleta_ainda_admite_adequate(self):
        """`03` §1.1 admite `adequate` com evidência parcial — é o que ele significa.

        Endurecer a regra para todas as classificações seria a spec sendo
        apertada por conta própria, e o objetivo com evidência parcial deixaria
        de ter classificação nenhuma.
        """
        self.assertTrue(self._com(ausente=True).admite("adequate"))
        self.assertTrue(self._com(ausente=True).admite("poor"))


class ComparacaoEntreVersoesDeRubrica(unittest.TestCase):
    """`03` §2.1 — comparabilidade vale dentro da mesma versão."""

    def _evidencia(self, rubric: str) -> EvidenciaDeObjetivo:
        return EvidenciaDeObjetivo(
            objective_id="OBJ-03",
            rubric=rubric,
            auto_satisfeita=frozenset(),
            auto_ausente=frozenset(),
            observed_marcado=frozenset(),
            observed_ausente=frozenset(),
        )

    def test_mesma_versao_e_comparavel(self):
        self.assertTrue(
            comparavel(
                self._evidencia("incident_triage.v2"),
                self._evidencia("incident_triage.v2"),
            )
        )

    def test_versoes_diferentes_nao_sao_comparaveis(self):
        self.assertFalse(
            comparavel(
                self._evidencia("incident_triage.v1"),
                self._evidencia("incident_triage.v2"),
            )
        )

    def test_a_versao_usada_fica_gravada_na_projecao(self):
        """Sem isto, a recusa acima não teria com que decidir."""
        evidencia = project([], objetivos_normativos())["OBJ-03"]
        self.assertEqual(evidencia.rubric, "incident_triage.v2")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
