"""Gate do item 4 da DoD da Fase 8 — as SETE acoes de continuidade.

AUTORIDADE
----------
`07_IMPLEMENTATION_PHASES.md` §Fase 8 (DoD item 4); `02_DOMAIN_ACADEMUS.md` §9
(as sete acoes: Acao | Efeito | Custo); `09_EVENT_MODEL.md` §1 e §4;
`contracts/events.schema.yaml` (`$def continuity_action_taken_payload`, fechado
na Wave 1). Decisao ratificada da tabela: `docs/progress/fase_8_plan.md`.

O QUE ESTE GATE PROVA — E POR QUE ELE E O AUTOR, NAO O DA CORRECAO (R3)
-----------------------------------------------------------------------
Escrito ANTES de T811 (`domains/academus/continuidade.py`, a tabela) e de
T814 (`POST /participant/continuity` + o ramo do fold). Roda RED agora: a tabela
nao existe, `montar()` ainda nao aceita `acoes_de_continuidade`, e o fold ainda
resolve `{}` para `continuity_action_taken`. Uma referencia minima o satisfaz.

As sete propriedades, em classes:

1. POSITIVO CANONICO (`AsSeteAcoesEmitem`): cada uma das SETE acoes emite
   `continuity_action_taken` com payload FECHADO valido, verificado no EVENTO que
   foi ao store (store real, padrao de `test_participant_emissao_pela_rota`) e
   contra `contracts/events.schema.yaml`. O conjunto das sete e o ORACLE
   INDEPENDENTE: o enum do contrato, nao uma lista reescrita aqui.

2. EFEITO MECANICO (`OFoldAplicaOEfeito`): o estado de simulacao RECONSTRUIDO
   apos a acao tem a(s) flag(s) no valor do efeito. Provado pelo ESTADO
   projetado (`range_core.state.simulation_state.project`), nao pelo payload. O
   default de cada flag e o OPOSTO do efeito, para que a mudanca seja observavel.

3. O CUSTO VIAJA (`AsSeteAcoesEmitem.test_o_custo_viaja_...`): `cost` esta no
   evento, e nao-vazio, e e o da tabela.

4. NEGATIVO (`ONegativoDaRota`, `OContratoRecusaPayloadInvalido`): `action_id`
   fora do enum e recusado sem emitir; payload fora do `$def` (sem `cost`,
   `effects` vazio, chave extra, `objective_ids` embutido) e recusado pelo
   contrato.

5. INV-4 ADVERSARIAL (`OFoldLeEffectDoPayloadGenerico`): o efeito e aplicado sem
   o nucleo conhecer nome de flag de dominio — o fold le `effects[].flag/value`
   do PAYLOAD (dado), com flag SINTETICA que o core nao poderia ter em import.

6. REGRESSAO CONGELADA (`OProjecaoAutoIgnoraOPayload`): `continuity_action_taken`
   e marcador `auto` de objetivo (`contracts/objectives.schema.yaml`); a projecao
   `auto/observed` (`range_core.objectives.projecao`) liga o marcador por
   `event_type` e NAO le payload. O gate trava se alguem fizer a projecao
   depender do payload. Verde agora; e a linha de nao-regressao que item 4 nao
   pode quebrar em item 2.

7. MUTANTE: cada mutante alvo esta registrado na matriz gate<->mutante do
   relatorio de T808. A prova negativa completa (fold/endpoint mutados) e a
   campanha de T819, que precisa da FONTE implementada para mutar; o RED aqui e a
   mutacao-nula (nada implementado) que discrimina "existe" de "nao existe". A
   discriminacao das guardas contra codigo EXISTENTE (itens 4 e 6) e demonstravel
   ja, via `tests/mutation_harness.py`.

POR QUE `unittest`, POR QUE STORE REAL
--------------------------------------
Como as suites irmas da fase: `pytest` nao esta pinado (T15), e a afirmacao
sobre EMISSAO se faz sobre o evento que foi ao store, nunca sobre espiao — o
espiao prova que alguem chamou alguem; o evento prova o que o exercicio vai ler.

POR QUE AS FLAGS SINTETICAS NAS GUARDAS DE CONTRATO E DE PROJECAO
-----------------------------------------------------------------
O `$def` tipa `flag` como `string` nao-vazia — qualquer nome serve para provar a
FORMA. A projecao liga por `event_type` e nao le `flag`. Nenhuma das duas
guardas precisa do nome real, e usa-lo prenderia o teste ao adapter sem ganho —
o mesmo motivo pelo qual `test_simulation_state` usa flags sinteticas. Os nomes
REAIS entram so pela tabela INJETADA (`OFoldAplicaOEfeito`), como dado de T811.

O CONTRATO DE INJECAO QUE ESTE GATE FIXA (para T811 e T814)
----------------------------------------------------------
- `domains/academus/continuidade.py` exporta `CONTINUIDADE`, dado puro:
  `Mapping[action_id, tuple[Sequence[tuple[flag, value]], cost]]`. `flag` sao as
  CONSTANTES de `domains/academus/generated/flags.py` (sem literais, INV-5);
  `value` e bool/number; `cost` e a coluna "Custo" de `02` §9. Sem import de
  nucleo, sem emissao.
- `montar(superficie, *, segredo, emissor, acoes_de_continuidade=CONTINUIDADE)`:
  o nucleo recebe a tabela como DADO injetado — nao importa `domains/` (INV-4).
- `POST /participant/continuity` recebe `{"action_id": ...}`; deriva
  `effects`+`cost` da tabela; emite `continuity_action_taken` com payload FECHADO
  (sem `justificativa` — o `$def` a proibe por `additionalProperties: false`).
- O fold de `simulation_state` ganha o ramo `continuity_action_taken`, lendo
  `payload["effects"]` como `[{flag, value}]` e escrevendo genericamente.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

from conformidade_de_envelope import ValidacaoDeEnvelope, envelope, validador

from contracts.generated.events import CONTINUITY_ACTION_TAKEN, EXERCISE_STARTED
from fastapi.testclient import TestClient
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation, Event
from range_core.events.store import InMemoryEventStore
from range_core.objectives.projecao import objetivos_de
from range_core.objectives.projecao import project as projetar_objetivos
from range_core.participant.api.app import montar
from range_core.participant.api.emissor import CAMADA, PRODUTOR, Emissor
from range_core.participant.api.tokens import PREFIXO_DA_CREDENCIAL
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    Declarations,
    project as projetar_estado,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
CREDENCIAL = "credencial-de-teste-por-persona"

#: A ROTA e a PERSONA vem da superficie — a mesma fonte que `check_api_surface.py`
#: confere. `/participant/continuity` e de `pro_reitoria` (Fase 8, item 4).
SUPERFICIE = parse_yaml(REPO_ROOT / "range-core" / "participant" / "api_surface.yaml")
PERSONA = "pro_reitoria"
ROTA_CONTINUIDADE = "/participant/continuity"

#: ORACLE INDEPENDENTE do conjunto das sete: o enum FECHADO do contrato. Escrever
#: as sete aqui criaria uma segunda lista — e acao nova entraria sem gate, que e a
#: lacuna que este oracle existe para nao deixar aberta.
_EVENTOS = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
ACOES_DO_CONTRATO = tuple(
    _EVENTOS["$defs"]["continuity_action_taken_payload"]["properties"]["action_id"][
        "enum"
    ]
)

#: Flag SINTETICA das guardas de contrato e de projecao — ver o cabecalho. Nao
#: casa o padrao `<dominio>.*` do adapter de proposito: nome real so pela tabela.
FLAG_SINTETICA = "fixture.continuity_flag"

#: Pino de pack sintetico do fold — o adapter e agnostico para o nucleo. Mesmo
#: pino no `exercise_started` e nas `Declarations`, senao `_verify_pack_pin`
#: recusa antes de aplicar qualquer efeito.
PACK_ID_VALUE = "ransomware-universidade"
SCHEMA_VERSION_VALUE = 2
CONTENT_HASH_VALUE = "sha256:0000"
CANONICALIZATION_VALUE = "v1"


def _tabela_de_continuidade():
    """A tabela de T811, importada TARDE — o RED e o ImportError com endereco.

    Import no topo derrubaria o modulo inteiro na coleta, e as guardas contra
    codigo existente (itens 4 e 6) nunca rodariam. Aqui so as classes que
    consomem a tabela ficam vermelhas, cada uma pelo seu motivo.
    """
    from domains.academus.continuidade import CONTINUIDADE

    return CONTINUIDADE


def _evento_de_fase(event_type: str, *, payload: dict, epoch: int = 0) -> Event:
    """Um `Event` construido a mao, para os folds que nao passam pela rota."""
    return Event(
        event_id=f"ev-{event_type}",
        event_type=event_type,
        truth_layer="participant_action",
        producer="participant-api",
        exercise_time="T+00:00:00",
        exercise_timestamp="2026-08-13T09:00:00",
        wall_timestamp="2026-08-13T09:00:00-03:00",
        clock_multiplier=1.0,
        simulation_epoch=epoch,
        correlation=Correlation(),
        payload=payload,
        actor_id=PERSONA,
        persona=PERSONA,
    )


def _exercise_started() -> Event:
    return Event(
        event_id="e0",
        event_type=EXERCISE_STARTED,
        truth_layer="facilitation",
        producer="inject-engine",
        exercise_time="T+00:00:00",
        exercise_timestamp="2026-08-13T09:00:00",
        wall_timestamp="2026-08-13T09:00:00-03:00",
        clock_multiplier=1.0,
        simulation_epoch=0,
        correlation=Correlation(),
        payload={
            PACK_ID: PACK_ID_VALUE,
            PACK_SCHEMA_VERSION: SCHEMA_VERSION_VALUE,
            PACK_CONTENT_HASH: CONTENT_HASH_VALUE,
            PACK_CANONICALIZATION: CANONICALIZATION_VALUE,
        },
    )


def _oposto(valor):
    """O default que torna o efeito OBSERVAVEL: se o efeito nao for aplicado, a
    flag fica no oposto e a assercao falha. Sem isso, a igualdade poderia passar
    por o default ja ser o valor do efeito."""
    if isinstance(valor, bool):
        return not valor
    return None  # numero: qualquer escrita e observavel contra o sentinela


def _declaracoes(flag_defaults: dict) -> Declarations:
    return Declarations(
        pack_id=PACK_ID_VALUE,
        schema_version=SCHEMA_VERSION_VALUE,
        content_hash=CONTENT_HASH_VALUE,
        canonicalization=CANONICALIZATION_VALUE,
        flag_defaults=flag_defaults,
        inject_effects={},
        option_effects={},
    )


class _ComRota(unittest.TestCase):
    """A rota real, o emissor real e a tabela INJETADA em `montar()`."""

    def setUp(self) -> None:
        self._ambiente = dict(os.environ)
        for persona in SUPERFICIE["personas"]:
            os.environ[f"{PREFIXO_DA_CREDENCIAL}{persona.upper()}"] = CREDENCIAL

        self.tabela = _tabela_de_continuidade()

        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(
                datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede))
            )
        )
        self.cliente = TestClient(
            montar(
                SUPERFICIE,
                segredo=SEGREDO,
                emissor=Emissor(store=self.store),
                acoes_de_continuidade=self.tabela,
            )
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._ambiente)

    def token(self, persona: str = PERSONA) -> str:
        resposta = self.cliente.post(
            "/participant/session",
            json={"persona": persona, "credencial": CREDENCIAL},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return resposta.json()["token"]

    def acao(self, action_id: str, *, persona: str = PERSONA):
        return self.cliente.post(
            ROTA_CONTINUIDADE,
            json={"action_id": action_id},
            headers={"Authorization": f"Bearer {self.token(persona)}"},
        )

    def eventos(self, tipo: str = CONTINUITY_ACTION_TAKEN):
        return [e for e in self.store.read_all() if e.event_type == tipo]


class AsSeteAcoesEmitem(ValidacaoDeEnvelope, _ComRota):
    """Positivo canonico: as sete emitem o payload fechado, e o custo viaja."""

    def test_a_tabela_cobre_exatamente_as_sete_do_contrato(self):
        """ORACLE INDEPENDENTE: o conjunto e o enum do contrato, e a tabela de
        T811 nao pode cobrir mais nem menos."""
        self.assertEqual(set(self.tabela), set(ACOES_DO_CONTRATO))
        self.assertEqual(len(ACOES_DO_CONTRATO), 7)

    def test_cada_acao_emite_evento_valido(self):
        for action_id in ACOES_DO_CONTRATO:
            with self.subTest(action_id=action_id):
                self.setUp()
                resposta = self.acao(action_id)

                self.assertEqual(resposta.status_code, 201, resposta.text)
                emitidos = self.eventos()
                self.assertEqual(len(emitidos), 1)
                [evento] = emitidos
                self.assertEqual(evento.payload["action_id"], action_id)
                self.assertEqual(evento.truth_layer, CAMADA)
                self.assertEqual(evento.producer, PRODUTOR)
                self.assertEqual(evento.persona, PERSONA)
                self.assertConformeAoContrato(
                    [evento], esperados={CONTINUITY_ACTION_TAKEN}
                )

    def test_os_effects_do_payload_vem_da_tabela(self):
        for action_id in ACOES_DO_CONTRATO:
            with self.subTest(action_id=action_id):
                self.setUp()
                self.acao(action_id)
                [evento] = self.eventos()

                effects, _cost = self.tabela[action_id]
                esperado = [{"flag": flag, "value": value} for flag, value in effects]
                self.assertEqual(evento.payload["effects"], esperado)

    def test_o_custo_viaja_e_e_nao_vazio(self):
        for action_id in ACOES_DO_CONTRATO:
            with self.subTest(action_id=action_id):
                self.setUp()
                self.acao(action_id)
                [evento] = self.eventos()

                _effects, cost = self.tabela[action_id]
                self.assertEqual(evento.payload["cost"], cost)
                self.assertTrue(str(evento.payload["cost"]).strip())


class OFoldAplicaOEfeito(_ComRota):
    """Item 2: o efeito e provado pelo ESTADO reconstruido, nunca pelo payload."""

    def _reconstruir(self, evento: Event, effects):
        defaults = {flag: _oposto(value) for flag, value in effects}
        return projetar_estado([_exercise_started(), evento], _declaracoes(defaults))

    def test_cada_acao_aplica_o_efeito_no_estado(self):
        for action_id in ACOES_DO_CONTRATO:
            with self.subTest(action_id=action_id):
                self.setUp()
                self.acao(action_id)
                [evento] = self.eventos()

                effects, _cost = self.tabela[action_id]
                estado = self._reconstruir(evento, effects)
                for flag, value in effects:
                    self.assertEqual(estado.flags[flag], value)

    def test_offline_exam_liga_a_flag(self):
        """O caso `true`: a acao acende o modo de prova offline."""
        self.acao("offline_exam")
        [evento] = self.eventos()
        effects, _cost = self.tabela["offline_exam"]
        estado = self._reconstruir(evento, effects)
        for flag, value in effects:
            self.assertIs(estado.flags[flag], True)
            self.assertIs(value, True)

    def test_emergency_document_issuance_desliga_a_flag(self):
        """O caso `false`: a acao ABAIXA a flag de bloqueio de documentos — e o
        gate so o pega porque o default e o oposto (`True`)."""
        self.acao("emergency_document_issuance")
        [evento] = self.eventos()
        effects, _cost = self.tabela["emergency_document_issuance"]
        estado = self._reconstruir(evento, effects)
        for flag, value in effects:
            self.assertIs(estado.flags[flag], False)
            self.assertIs(value, False)


class OFoldLeEffectDoPayloadGenerico(unittest.TestCase):
    """Item 5 (INV-4): o fold aplica o efeito lendo o PAYLOAD, sem conhecer o
    dominio. A flag e SINTETICA — o nucleo nao poderia te-la em import."""

    FLAG_BOOL = "fixture.continuity_generic_flag"
    FLAG_NUM = "fixture.continuity_generic_number"

    def test_o_fold_escreve_a_flag_nomeada_no_payload(self):
        evento = _evento_de_fase(
            CONTINUITY_ACTION_TAKEN,
            payload={
                "action_id": "offline_exam",
                "effects": [{"flag": self.FLAG_BOOL, "value": True}],
                "cost": "custo sintetico",
            },
        )
        defaults = {self.FLAG_BOOL: False}
        estado = projetar_estado([_exercise_started(), evento], _declaracoes(defaults))
        self.assertIs(estado.flags[self.FLAG_BOOL], True)

    def test_o_fold_carrega_valor_numerico_do_payload(self):
        evento = _evento_de_fase(
            CONTINUITY_ACTION_TAKEN,
            payload={
                "action_id": "offline_exam",
                "effects": [{"flag": self.FLAG_NUM, "value": 3}],
                "cost": "custo sintetico",
            },
        )
        defaults = {self.FLAG_NUM: 0}
        estado = projetar_estado([_exercise_started(), evento], _declaracoes(defaults))
        self.assertEqual(estado.flags[self.FLAG_NUM], 3)


class ONegativoDaRota(_ComRota):
    """As direcoes em que a acao NAO emite."""

    def test_action_id_fora_do_enum_nao_emite(self):
        resposta = self.acao("acao_que_ninguem_implementou")

        self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertEqual(self.eventos(), [])

    def test_persona_sem_acesso_recebe_403_e_nao_emite(self):
        """A rota e de `pro_reitoria` (`03` §6); `ti` nao a alcanca."""
        resposta = self.acao("offline_exam", persona="ti")

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.eventos(), [])

    def test_sem_token_nao_emite(self):
        resposta = self.cliente.post(
            ROTA_CONTINUIDADE, json={"action_id": "offline_exam"}
        )

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(self.eventos(), [])


class OContratoRecusaPayloadInvalido(unittest.TestCase):
    """Item 4, metade do contrato: o `$def` fechado recusa o payload malformado.

    Guarda contra codigo EXISTENTE (o `$def` fechou na Wave 1) — verde agora. E a
    prova de que o CONTRATO e o gate do payload, e nao um `assertEqual` daqui."""

    def _valida(self, payload: dict):
        evento = _evento_de_fase(CONTINUITY_ACTION_TAKEN, payload=payload)
        return sorted(validador().iter_errors(envelope(evento)), key=str)

    def _payload_bom(self) -> dict:
        return {
            "action_id": "offline_exam",
            "effects": [{"flag": FLAG_SINTETICA, "value": True}],
            "cost": "prova sem sistema exige logistica presencial",
        }

    def test_o_payload_fechado_valido_passa(self):
        """Ancora: sem ela, um payload que reprova por OUTRO motivo faria os
        negativos passarem afirmando o contrario do que ha."""
        self.assertEqual(self._valida(self._payload_bom()), [])

    def test_sem_cost_recusado(self):
        payload = self._payload_bom()
        del payload["cost"]
        self.assertNotEqual(self._valida(payload), [])

    def test_effects_vazio_recusado(self):
        payload = self._payload_bom()
        payload["effects"] = []
        self.assertNotEqual(self._valida(payload), [])

    def test_chave_extra_recusada(self):
        payload = self._payload_bom()
        payload["extra"] = "nao contratada"
        self.assertNotEqual(self._valida(payload), [])

    def test_objective_ids_embutido_recusado(self):
        """INV-6 dentro do payload: o binding evento->objetivo e da projecao."""
        payload = self._payload_bom()
        payload["objective_ids"] = ["OBJ-05"]
        self.assertNotEqual(self._valida(payload), [])

    def test_action_id_fora_do_enum_recusado(self):
        payload = self._payload_bom()
        payload["action_id"] = "acao_que_ninguem_implementou"
        self.assertNotEqual(self._valida(payload), [])


class OProjecaoAutoIgnoraOPayload(unittest.TestCase):
    """Item 6, regressao congelada: a projecao `auto/observed` liga o marcador por
    `event_type` e NAO le payload. O gate trava se alguem fizer a projecao
    depender do payload — o cruzamento do item 4 com o item 2.

    Verde agora (a projecao ja e payload-agnostica). O mutante que ela mata:
    projecao que exija uma chave do payload para satisfazer o marcador."""

    def _objetivo_de_continuidade(self):
        return objetivos_de(
            {
                "objectives": {
                    "OBJ-CONT": {
                        "title": "Decidir sobre continuidade",
                        "competency": "business_continuity",
                        "rubric": "business_continuity",
                        "evidence": {"auto": [CONTINUITY_ACTION_TAKEN]},
                    }
                }
            }
        )

    def test_o_marcador_auto_liga_pelo_tipo_com_payload_fechado(self):
        objetivos = self._objetivo_de_continuidade()
        evento = _evento_de_fase(
            CONTINUITY_ACTION_TAKEN,
            payload={
                "action_id": "offline_exam",
                "effects": [{"flag": FLAG_SINTETICA, "value": True}],
                "cost": "prova presencial",
            },
        )
        resultado = projetar_objetivos([evento], objetivos)
        self.assertIn(CONTINUITY_ACTION_TAKEN, resultado["OBJ-CONT"].auto_satisfeita)

    def test_o_marcador_auto_liga_mesmo_com_payload_vazio(self):
        """A prova da INDEPENDENCIA de payload: um evento do tipo, com payload
        VAZIO (que o contrato recusaria — mas a projecao nao valida), ainda
        satisfaz o marcador. Projecao que lesse payload aqui falharia."""
        objetivos = self._objetivo_de_continuidade()
        evento = _evento_de_fase(CONTINUITY_ACTION_TAKEN, payload={})
        resultado = projetar_objetivos([evento], objetivos)
        self.assertIn(CONTINUITY_ACTION_TAKEN, resultado["OBJ-CONT"].auto_satisfeita)
        self.assertEqual(resultado["OBJ-CONT"].auto_ausente, frozenset())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
