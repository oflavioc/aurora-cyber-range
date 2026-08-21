"""O evento que a rota GRAVA satisfaz o contrato que a spec declara.

POR QUE ESTE TESTE EXISTE
-------------------------
`contracts/assessment.schema.yaml` reivindica os blocos normativos de `03` §5.1 e
`02` §6.2, e `events.schema.yaml` liga o payload de `assessment_submitted` a ele.
Nada disso prova que o **emissor** produz um evento conforme: o event store não
valida payload — medido —, então uma rota que gravasse campo a mais, ou que
esquecesse um obrigatório, sairia com `201` e o defeito viajaria até o AAR.

Foi assim que uma fixture da peça 5 gravou `technical_failure` sem
`frozen_interval` e passou. Aqui a mesma classe é fechada para o caminho que a
produção usa.

E ELE PEGOU UM CASO REAL, ANTES DE EXISTIR
-------------------------------------------
`03` §5.1 dá à submissão cinco campos; `03` §3.4 põe `assessment_submitted` entre
as nove ações de declaração e exige de **cada uma** *"justificativa livre"*. O
emissor grava as duas coisas, e um contrato fechado apenas sobre os cinco campos
recusaria o evento que a rota de fato emite.

Não é redundância a resolver: `rationale` é o raciocínio **sobre o caso**,
`justificativa` é a exigência de §3.4 sobre o **ato de declarar**. O contrato
compõe as duas por `allOf`, e este teste é o que impede a composição de
envelhecer.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from contracts.generated.events import ASSESSMENT_SUBMITTED
from jsonschema import Draft202012Validator
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.loader import contract_source
from range_core.events.envelope import Event
from range_core.events.store import InMemoryEventStore
from range_core.participant.api.emissor import EmissaoRecusada, Emissor

CONTRATOS = contract_source.read_contracts()
REGISTRY = contract_source.registry_for(CONTRATOS)

SUBMISSAO = {
    "case_id": "GC-029",
    "classification": "suspicious",
    "confidence": 72,
    "evidence": ["DBA-28391", "DBA-28402"],
    "rationale": "Alteracao fora da janela, sem autorizacao.",
}


def como_documento(evento: Event) -> dict:
    """O envelope na forma que o contrato valida — sem tipos Python."""
    return {
        "event_id": evento.event_id,
        "event_type": evento.event_type,
        "truth_layer": evento.truth_layer,
        "producer": evento.producer,
        "actor_id": evento.actor_id,
        "persona": evento.persona,
        "exercise_time": evento.exercise_time,
        "exercise_timestamp": evento.exercise_timestamp,
        "wall_timestamp": evento.wall_timestamp,
        "clock_multiplier": evento.clock_multiplier,
        "simulation_epoch": evento.simulation_epoch,
        "payload": dict(evento.payload),
    }


class OEmissorProduzEventoConforme(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.emissor = Emissor(self.store)
        self.validador = Draft202012Validator(
            CONTRATOS["events"], registry=REGISTRY
        )

    def submete(self, **campos) -> Event:
        return self.emissor.declarar(
            ASSESSMENT_SUBMITTED,
            persona="ti",
            actor_id="analista-ti",
            justificativa="Revisao do lote noturno.",
            payload=campos,
        )

    def test_a_submissao_normativa_grava_evento_que_o_contrato_aceita(self):
        evento = self.submete(**SUBMISSAO)
        self.validador.validate(como_documento(evento))

    def test_o_evento_gravado_carrega_os_cinco_campos_E_a_justificativa(self):
        """A composicao das duas normas, no que de fato foi para o store."""
        evento = self.submete(**SUBMISSAO)

        for campo in SUBMISSAO:
            with self.subTest(campo=campo):
                self.assertIn(campo, evento.payload)
        self.assertIn("justificativa", evento.payload)

    def test_a_submissao_minima_tambem_e_conforme(self):
        evento = self.submete(
            case_id="GC-101", classification="legitimate", confidence=5
        )
        self.validador.validate(como_documento(evento))

    def test_campo_nao_declarado_no_payload_e_RECUSADO_pelo_contrato(self):
        """O fechamento vale para o evento gravado, e nao so para o documento.

        Sem `unevaluatedProperties`, a composicao por `allOf` deixaria passar
        qualquer chave — e o fechamento viraria decoracao.
        """
        evento = self.submete(**SUBMISSAO, defensibility=1.0)

        self.assertFalse(self.validador.is_valid(como_documento(evento)))

    def test_confidence_fora_da_faixa_e_RECUSADO_pelo_contrato(self):
        evento = self.submete(
            case_id="GC-029", classification="suspicious", confidence=140
        )

        self.assertFalse(self.validador.is_valid(como_documento(evento)))

    def test_sem_justificativa_o_emissor_nem_grava(self):
        """`03` §3.4 exige de cada uma. A recusa e da emissao, antes do contrato."""
        with self.assertRaises(EmissaoRecusada):
            self.emissor.declarar(
                ASSESSMENT_SUBMITTED,
                persona="ti",
                actor_id="analista-ti",
                justificativa="   ",
                payload=SUBMISSAO,
            )


class OContratoDeAssessmentEstaNoRegistro(unittest.TestCase):
    """Ele precisa ser LIDO, e nao apenas existir no diretorio."""

    def test_o_contrato_e_carregado_pelo_loader(self):
        self.assertIn("assessment", CONTRATOS)

    def test_o_payload_do_evento_referencia_o_contrato_de_assessment(self):
        """A ligacao entre os dois contratos, afirmada e nao suposta.

        Se alguem copiar os campos para `events.schema.yaml` em vez de referenciar,
        este teste reprova — e a copia e a classe D4 que a composicao evita.
        """
        alvo = "assessment.schema.json#/$defs/assessment_submitted_payload"
        encontrados = [
            ramo
            for ramo in CONTRATOS["events"]["allOf"]
            if alvo in str(ramo.get("then", {}))
        ]
        self.assertEqual(len(encontrados), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
