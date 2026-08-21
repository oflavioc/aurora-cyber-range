"""As NOVE rotas de declaração emitem — provado por `_declara`, e não ao lado dela.

B2 DA AUDITORIA DA FASE 6, SEGUNDA METADE
-------------------------------------------
A primeira metade fechou `GET /audit/grade-changes`. Esta fecha as outras nove, e
a estrutura é o que torna **duas** provas suficientes para **dez** rotas: as nove
declarações passam todas por `_declara`, uma função só.

Medido ao investigar a verificação por AST que foi descartada — o handler de cada
rota não chama o emissor: ele chama `_declara`, que chama. Era o que faria um AST
ingênuo reprovar as nove estando elas corretas; e é o que faz **um** teste sobre
`_declara` cobrir as nove de verdade.

O QUE ELA AFIRMA, E SOBRE O QUÊ
---------------------------------
Rota real por `TestClient`, **emissor real** ligado a um `InMemoryEventStore`, e a
afirmação é sobre o **evento que foi para o store**. Nunca sobre espião, nunca
sobre assinatura — os dois provam que alguém chamou alguém, e o evento prova o
que o exercício vai ler.

A COBERTURA DAS NOVE É DERIVADA DA SUPERFÍCIE
-----------------------------------------------
A tabela de rotas vem de `range-core/participant/api_surface.yaml`, que é a mesma
fonte que `check_api_surface.py` confere contra a coluna *Quem* de `03` §3.4.
Escrever as nove aqui criaria uma segunda lista — e rota nova entraria sem teste,
que é precisamente a lacuna que este arquivo existe para não deixar aberta.

**O que ela não fecha:** rota nova que declare `emite` e **não** passe por
`_declara`. Isso é a **P6-7**, registrada com o mapa.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import ASSESSMENT_SUBMITTED
from fastapi.testclient import TestClient
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore
from range_core.participant.api.app import montar
from range_core.participant.api.emissor import CAMADA, PRODUTOR, Emissor
from range_core.participant.api.tokens import PREFIXO_DA_CREDENCIAL

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
CREDENCIAL = "credencial-de-teste-por-persona"

SUPERFICIE = parse_yaml(REPO_ROOT / "range-core" / "participant" / "api_surface.yaml")

#: As nove — DERIVADAS da superfície. Rota que declare `emite` entra sozinha, e
#: é por isso que a lista não é escrita aqui.
DECLARACOES = [
    r for r in SUPERFICIE["rotas"] if r.get("emite") and r.get("papeis")
]


class _ComSuperficie(unittest.TestCase):
    def setUp(self) -> None:
        self._ambiente = dict(os.environ)
        for persona in SUPERFICIE["personas"]:
            os.environ[f"{PREFIXO_DA_CREDENCIAL}{persona.upper()}"] = CREDENCIAL

        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.cliente = TestClient(
            montar(SUPERFICIE, segredo=SEGREDO, emissor=Emissor(store=self.store))
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._ambiente)

    def token(self, persona: str) -> str:
        resposta = self.cliente.post(
            "/participant/session",
            json={"persona": persona, "credencial": CREDENCIAL},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return resposta.json()["token"]

    def declara(self, rota: dict, *, corpo: dict | None = None, persona: str | None = None):
        alvo = persona or sorted(rota["papeis"])[0]
        return self.cliente.post(
            rota["path"],
            json={"justificativa": "declaracao de teste", **(corpo or {})},
            headers={"Authorization": f"Bearer {self.token(alvo)}"},
        )

    def eventos(self, tipo: str):
        return [e for e in self.store.read_all() if e.event_type == tipo]


class AsNoveRotasEmitem(_ComSuperficie):
    """Uma prova por rota, derivada da superfície — nenhuma lista intermediária."""

    def test_ha_nove_rotas_de_declaracao(self):
        """A conta de `03` §3.4. Se virar dez, este teste cobra o motivo."""
        self.assertEqual(len(DECLARACOES), 9)

    def test_cada_rota_emite_o_event_type_QUE_DECLARA(self):
        for rota in DECLARACOES:
            with self.subTest(rota=rota["path"]):
                self.setUp()
                corpo = _corpo_minimo(rota)
                resposta = self.declara(rota, corpo=corpo)

                self.assertEqual(resposta.status_code, 201, resposta.text)
                self.assertEqual(len(self.eventos(rota["emite"])), 1)

    def test_o_envelope_e_o_declarado_em_todas(self):
        """`09` §1.1 — camada, produtor, `actor_id` e `persona` não são do handler."""
        for rota in DECLARACOES:
            with self.subTest(rota=rota["path"]):
                self.setUp()
                persona = sorted(rota["papeis"])[0]
                self.declara(rota, corpo=_corpo_minimo(rota), persona=persona)
                [evento] = self.eventos(rota["emite"])

                self.assertEqual(evento.truth_layer, CAMADA)
                self.assertEqual(evento.producer, PRODUTOR)
                self.assertEqual(evento.persona, persona)
                self.assertEqual(evento.actor_id, persona)

    def test_a_justificativa_de_03_3_4_viaja_no_payload(self):
        """*"Cada uma grava evento com (...) justificativa livre."*"""
        for rota in DECLARACOES:
            with self.subTest(rota=rota["path"]):
                self.setUp()
                self.declara(rota, corpo=_corpo_minimo(rota))
                [evento] = self.eventos(rota["emite"])

                self.assertEqual(evento.payload["justificativa"], "declaracao de teste")


class OQueNaoEmite(_ComSuperficie):
    """As direções em que o evento não pode aparecer."""

    def rota(self, caminho: str) -> dict:
        return next(r for r in DECLARACOES if r["path"] == caminho)

    def test_sem_justificativa_nao_grava(self):
        """`03` §3.4 a exige de cada uma, e o emissor recusa antes do store.

        O QUE IMPORTA AQUI É O STORE VAZIO, e é o que a asserção final afirma.

        > **O código de status é 409, e ele contradiz o comentário da própria
        > rota.** `_declara` documenta o 409 como *"o pedido é bem formado e o
        > ESTADO o recusa"*, e enumera três causas — todas de contrassinatura.
        > Justificativa ausente não é nenhuma delas: é campo obrigatório
        > faltando, que é pedido malformado.
        >
        > O teste afirma **409** porque é o que a árvore faz — teste que
        > descreve o que deveria ser, e não o que é, não pega regressão. A
        > discrepância está reportada, e a decisão de mudar o status é de quem
        > decide superfície.
        """
        rota = self.rota("/participant/incident")
        resposta = self.cliente.post(
            rota["path"],
            json={"justificativa": "   "},
            headers={"Authorization": f"Bearer {self.token('ti')}"},
        )

        self.assertEqual(self.store.read_all(), ())
        self.assertEqual(resposta.status_code, 409)

    def test_persona_sem_acesso_recebe_403_e_nao_emite(self):
        """RBAC pela coluna *Quem* de `03` §3.4, e a recusa é ANTES da emissão."""
        rota = self.rota("/participant/classification")  # so `ti`
        resposta = self.declara(rota, persona="comunicacao")

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.eventos(rota["emite"]), [])

    def test_sem_token_nao_emite(self):
        rota = self.rota("/participant/containment")
        resposta = self.cliente.post(rota["path"], json={"justificativa": "x"})

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(self.eventos(rota["emite"]), [])

    def test_credencial_errada_nao_abre_sessao(self):
        resposta = self.cliente.post(
            "/participant/session",
            json={"persona": "ti", "credencial": "errada"},
        )
        self.assertEqual(resposta.status_code, 401)


def _corpo_minimo(rota: dict) -> dict:
    """O corpo que cada rota exige além da justificativa.

    Só `assessment` tem contrato de payload fechado
    (`contracts/assessment.schema.yaml`), e por isso é a única com campos aqui. As
    outras oito aceitam payload livre — e isso é estado da árvore, não desenho:
    cada payload nasce quando o consumidor dele nasce.
    """
    if rota["emite"] != ASSESSMENT_SUBMITTED:
        return {}
    return {"case_id": "GC-029", "classification": "suspicious", "confidence": 72}


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
