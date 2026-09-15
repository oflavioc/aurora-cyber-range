"""Isolacao da camada `reported` por persona — o gate do item 3 da DoD da Fase 8.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §6:395 — *"Cada persona ve apenas sua camada `reported`"*.
`06_ACCEPTANCE_TESTS.md` T14:164 — *"endpoint de persona nao vaza ground truth"*.
`09_EVENT_MODEL.md` §2 — as quatro verdades (+ `facilitation`).
`range-core/participant/api_surface.yaml` — `GET /participant/view`, D1.

FRONTEIRA DE FASE (ratificada)
------------------------------
A Fase 8 entrega SO a ISOLACAO de leitura da camada `reported`. O CONTEUDO
divergente de `information_distribution.yaml` (subestimativa deliberada, `03` §4)
e a assimetria da Fase 10 — NAO e escopo aqui. Este gate prova isolacao, nunca
divergencia de conteudo. Por isso a fixture e MINIMA e planta eventos direto no
store, sem depender do arquivo de conteudo.

O ORACULO — a forma do frame `reported` por persona (definida por QA, alvo da T813)
----------------------------------------------------------------------------------
`range_core.participant.reported.project(persona, eventos) -> Sequence[Event]`
devolve o frame TOTAL (INV-7: estado total, nunca delta) da camada `reported`
DAQUELA persona. Funcao PURA do fluxo de eventos — espelha o `project` do fold; a
projecao nunca e fonte (R9 §5), o estado canonico e o event store, de onde a rota
le por `read_all()`.

Um evento pertence ao frame `reported` da persona P sse, e so se, a CONJUNCAO:
  1. `truth_layer` E REPORTAVEL — pertence a {`observable_evidence`,
     `participant_action`}. As camadas ACIMA de `reported` — `ground_truth`,
     `evaluator_assessment`, `facilitation` — NUNCA entram (T14 + `03` §6).
  2. o evento e ENDERECADO a P — `event.persona == P`. Evento de outra persona
     e fatia dela, e nao entra (isolacao D1, falha fechada).

Nenhuma perna basta sozinha, e cada perna tem um mutante que a exige — ver a
matriz abaixo. O caso `persona is None` (broadcast/compartilhado) fica em ABERTO
de proposito: e conteudo, portanto Fase 10; este gate nao o pina em nenhuma
direcao para nao obrigar a Fase 10 a desfazer.

A ROTA — `GET /participant/view`, D1
------------------------------------
Autenticada, vinculada ao token da persona (nunca a persona pedida no corpo). O
handler le `read_all()` do store, chama `project(persona_do_token, ...)` e devolve
`{"persona": <persona-do-token>, "reported": [<evento-serializado>, ...]}`, cada
evento com ao menos `event_id`, `truth_layer`, `persona`, `payload`.

MATRIZ GATE <-> MUTANTE (R3 §5, R10 §nascimento)
-------------------------------------------------
  M1  projecao cega a CAMADA (filtra so por persona) -> vaza GT/EVAL/FAC marcados
      para a persona.        Morto por: test_projecao_nao_vaza_ground_truth,
      test_projecao_nao_vaza_camadas_acima, test_projecao_so_camadas_reportaveis,
      test_rota_nao_vaza_ground_truth_nem_camadas_superiores.
  M2  projecao cega a PERSONA (filtra so por camada) -> vaza a fatia de outra
      persona.               Morto por: test_projecao_isola_entre_personas,
      test_rota_isola_entre_personas.
  M3  projecao sem filtro nenhum (devolve tudo). Morto por M1 + M2 juntos.
  M4  projecao que devolve delta (so o ultimo reportavel). Morto por:
      test_projecao_frame_total (igualdade do conjunto, nao subconjunto).

RED
---
`range_core.participant.reported` nao existe e `GET /participant/view` nao esta
registrada -> os testes de projecao dao ModuleNotFoundError e os de rota dao 404.
Registrado em `docs/progress/fase_8_tasks.md` T807. reported.py + rota sao T813
(core-engineer). O QA e AUTOR do gate; nao implementa a correcao (R3 §2).
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import (
    BARS_SCORE_SUBMITTED,
    EVIDENCE_SOURCE_RELEASED,
    FACT_MATERIALIZED,
    INCIDENT_DECLARED,
    INJECT_FIRED,
)
from fastapi.testclient import TestClient
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.participant.api.app import montar
from range_core.participant.api.emissor import Emissor
from range_core.participant.api.tokens import PREFIXO_DA_CREDENCIAL

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
CREDENCIAL = "credencial-de-teste-por-persona"

SUPERFICIE = parse_yaml(REPO_ROOT / "range-core" / "participant" / "api_surface.yaml")

# As duas personas do vocabulario fechado (`03` §6) que a fixture usa: a que le
# (`ti`) e a "outra" (`dpo`), para a isolacao D1. Nomes conferidos contra
# `api_surface.yaml` campo `personas`.
VIEWER = "ti"
OUTRA = "dpo"

# Camadas — os cinco valores de `09` §2. Nao sao event_type nem flag, entao sao
# literais legitimos aqui (o scanner do INV-2/3 nao os reconhece).
GROUND_TRUTH = "ground_truth"
OBSERVABLE_EVIDENCE = "observable_evidence"
PARTICIPANT_ACTION = "participant_action"
EVALUATOR_ASSESSMENT = "evaluator_assessment"
FACILITATION = "facilitation"

REPORTAVEIS = frozenset({OBSERVABLE_EVIDENCE, PARTICIPANT_ACTION})

# Marcas de payload — unicas, para rastrear vazamento em qualquer campo da
# resposta. Nenhuma casa event_type ou flag.
M_TI_ACAO = "TI-DECLAROU"
M_TI_EVIDENCIA = "TI-EVIDENCIA"
M_DPO_ACAO = "DPO-DECLAROU"
M_GT = "GT-SEGREDO"
M_EVAL = "EVAL-SEGREDO"
M_FAC = "FAC-SEGREDO"

SEGREDOS_ACIMA = (M_GT, M_EVAL, M_FAC)


def _carrega_project():
    """Import TARDIO — o RED e ModuleNotFoundError DENTRO do teste, e nao no
    import do arquivo, para que os testes de rota tambem rodem e falhem por 404.
    """
    from range_core.participant.reported import project

    return project


class _ComStore(unittest.TestCase):
    """Planta a fixture minima de eventos `reported` (e nao-reportaveis) no store.

    Os eventos das camadas ACIMA de `reported` sao plantados MARCADOS PARA `ti` de
    proposito: assim uma projecao que filtre so por persona (M1) ainda os
    devolveria, e o gate morre esse mutante em vez de deixa-lo passar por sorte.
    """

    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(
                datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede))
            )
        )
        # Reportaveis da persona que le — DOIS, para provar frame TOTAL (nao delta).
        self._planta(INCIDENT_DECLARED, PARTICIPANT_ACTION, VIEWER, M_TI_ACAO)
        self._planta(EVIDENCE_SOURCE_RELEASED, OBSERVABLE_EVIDENCE, VIEWER, M_TI_EVIDENCIA)
        # Reportavel de OUTRA persona — a fatia que `ti` nunca pode alcancar (D1).
        self._planta(INCIDENT_DECLARED, PARTICIPANT_ACTION, OUTRA, M_DPO_ACAO)
        # Camadas ACIMA de `reported`, marcadas para `ti` (adversarial).
        self._planta(FACT_MATERIALIZED, GROUND_TRUTH, VIEWER, M_GT)
        self._planta(BARS_SCORE_SUBMITTED, EVALUATOR_ASSESSMENT, VIEWER, M_EVAL)
        self._planta(INJECT_FIRED, FACILITATION, VIEWER, M_FAC)

    def _planta(self, event_type: str, camada: str, persona: str, marca: str) -> None:
        self.store.append(
            EventDraft(
                event_type=event_type,
                truth_layer=camada,
                producer="fixture-de-teste",
                correlation=Correlation(),
                actor_id=persona,
                persona=persona,
                payload={"marca": marca},
            )
        )

    @staticmethod
    def _marcas(eventos) -> set:
        return {e.payload.get("marca") for e in eventos}


class ProjecaoReportedIsola(_ComStore):
    """O oraculo, exercitado direto sobre o fluxo de eventos (sem HTTP)."""

    def test_projecao_frame_total(self):
        """Devolve TODOS os reportaveis da persona — igualdade, nao subconjunto
        (INV-7: frame total, nao delta). Mata M4."""
        project = _carrega_project()
        frame = project(VIEWER, self.store.read_all())
        self.assertEqual(self._marcas(frame), {M_TI_ACAO, M_TI_EVIDENCIA})

    def test_projecao_nao_vaza_ground_truth(self):
        """A clausula de isolamento de T14 — mesmo marcado para a persona. Mata M1."""
        project = _carrega_project()
        frame = project(VIEWER, self.store.read_all())
        self.assertNotIn(M_GT, self._marcas(frame))
        self.assertTrue(all(e.truth_layer != GROUND_TRUTH for e in frame))

    def test_projecao_nao_vaza_camadas_acima(self):
        """Nem `evaluator_assessment` nem `facilitation`. Mata M1."""
        project = _carrega_project()
        frame = project(VIEWER, self.store.read_all())
        camadas = {e.truth_layer for e in frame}
        self.assertNotIn(GROUND_TRUTH, camadas)
        self.assertNotIn(EVALUATOR_ASSESSMENT, camadas)
        self.assertNotIn(FACILITATION, camadas)

    def test_projecao_so_camadas_reportaveis(self):
        """Positivo do filtro de camada: todo evento do frame e reportavel. Mata M1."""
        project = _carrega_project()
        frame = project(VIEWER, self.store.read_all())
        for e in frame:
            with self.subTest(event_id=e.event_id):
                self.assertIn(e.truth_layer, REPORTAVEIS)

    def test_projecao_isola_entre_personas(self):
        """`ti` nunca ve a fatia de `dpo`, e `dpo` ve a sua. Mata M2."""
        project = _carrega_project()
        eventos = self.store.read_all()
        frame_ti = project(VIEWER, eventos)
        self.assertNotIn(M_DPO_ACAO, self._marcas(frame_ti))
        frame_dpo = project(OUTRA, eventos)
        self.assertEqual(self._marcas(frame_dpo), {M_DPO_ACAO})
        self.assertNotIn(M_TI_ACAO, self._marcas(frame_dpo))


class RotaViewIsola(_ComStore):
    """`GET /participant/view` — vinculada ao token, autenticada (D1)."""

    def setUp(self) -> None:
        super().setUp()
        self._ambiente = dict(os.environ)
        for persona in SUPERFICIE["personas"]:
            os.environ[f"{PREFIXO_DA_CREDENCIAL}{persona.upper()}"] = CREDENCIAL
        self.cliente = TestClient(
            montar(SUPERFICIE, segredo=SEGREDO, emissor=Emissor(store=self.store))
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._ambiente)

    def _token(self, persona: str) -> str:
        resposta = self.cliente.post(
            "/participant/session",
            json={"persona": persona, "credencial": CREDENCIAL},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return resposta.json()["token"]

    def _view(self, persona: str):
        return self.cliente.get(
            "/participant/view",
            headers={"Authorization": f"Bearer {self._token(persona)}"},
        )

    def test_rota_frame_total_da_persona_do_token(self):
        resposta = self._view(VIEWER)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["persona"], VIEWER)
        marcas = {e["payload"]["marca"] for e in corpo["reported"]}
        self.assertEqual(marcas, {M_TI_ACAO, M_TI_EVIDENCIA})

    def test_rota_nao_vaza_ground_truth_nem_camadas_superiores(self):
        """Substring no corpo INTEIRO — pega vazamento em qualquer campo, nao so
        no que a fixture antecipou. Mata M1 pela rota."""
        resposta = self._view(VIEWER)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        for segredo in SEGREDOS_ACIMA:
            with self.subTest(segredo=segredo):
                self.assertNotIn(segredo, resposta.text)

    def test_rota_isola_entre_personas(self):
        """A fatia de `dpo` nunca aparece na view de `ti`. Mata M2 pela rota."""
        resposta = self._view(VIEWER)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertNotIn(M_DPO_ACAO, resposta.text)

    def test_rota_sem_token_recusa(self):
        """A view e autenticada (D1): ausencia de token recusa, falha fechada."""
        resposta = self.cliente.get("/participant/view")
        self.assertEqual(resposta.status_code, 401)

    def test_rota_token_invalido_recusa(self):
        resposta = self.cliente.get(
            "/participant/view",
            headers={"Authorization": "Bearer isto-nao-e-um-token"},
        )
        self.assertEqual(resposta.status_code, 401)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
