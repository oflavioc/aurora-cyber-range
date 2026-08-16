"""O inject-engine — a metade restante do item 3, e o roteiro do DEMO.

O QUE ESTA SUITE PROVA
----------------------
- **Item 3, segunda metade**: *"PAUSAR ... bloqueia disparo agendado"*. A prova
  esta em `PausaBloqueiaAgendado`, e a construcao dela e o argumento — ver a
  docstring da classe.
- **Item 4**, na forma em que a DoD o escreve: *"aplicar A01 duas vezes produz
  projecao identica"*. O fold ja o prova como propriedade; aqui ele e provado
  pela porta por onde um facilitador de fato o faria.
- **Item 5**, pela mesma porta: rollback grava, incrementa epoch e reconstroi
  sem apagar.
- **O roteiro do DEMO** da fase, ponta a ponta, como teste — para que ele nao
  dependa de alguem rodar o script para saber que continua valendo.

O TEMPO E CONTROLADO PELO TESTE, E O CLOCK E O DE VERDADE
----------------------------------------------------------
Nenhum teste dorme. O clock recebe a fonte de tempo de parede por injecao
(§3.7 do registro), entao o engine e exercitado contra o clock REAL com o tempo
na mao — e nao contra um duplo que poderia concordar com o engine sobre uma
semantica errada de pausa.

OS EVENTOS EMITIDOS SAO CONFERIDOS CONTRA O CONTRATO
-----------------------------------------------------
`ConformeAoContrato` valida cada evento que o engine emite contra
`contracts/events.schema.yaml`. O store nao valida — e decisao dele —, entao sem
isto o engine poderia emitir por anos um envelope que o contrato recusa, e o
primeiro a descobrir seria o consumidor de outra fase.
"""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from contracts.generated.events import (
    DECISION_MADE,
    EXERCISE_PAUSED,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.exercise_clock import ExerciseClock, label_seconds
from range_core.engine.inject_engine import (
    REASON,
    REASON_TECHNICAL_FAILURE,
    TO_INJECT_ID,
    EngineError,
    EngineSite,
    Facilitator,
    InjectEngine,
)
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.events.store import InMemoryEventStore
from range_core.state.simulation_state import TO_EVENT_ID

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK = REPO_ROOT / "tests" / "fixtures" / "pack_minimo"
FLAGS_DO_ADAPTER = Path("domains") / "academus" / "flags.yaml"

CONTRATOS = contract_source.read_contracts()
MOTIVOS = contract_source.rollback_reasons(CONTRATOS)
FLAGS = AdapterFlags.from_document(
    yaml.safe_load((REPO_ROOT / FLAGS_DO_ADAPTER).read_text(encoding="utf-8")),
    source=FLAGS_DO_ADAPTER.as_posix(),
)
PACK_CARREGADO = load_pack(PACK, contracts=CONTRATOS, adapter_flags=FLAGS)

T_ZERO = datetime(2026, 8, 15, 9, 0, 0)

#: Ids do fixture. Vem do pack carregado, e nao escritos aqui: id inventado no
#: teste passaria a divergir do fixture sem nada acusar.
A01, A02, RUIDO = (inject.id for inject in PACK_CARREGADO.injects)
OPCAO = PACK_CARREGADO.injects[1].decision_point.options[1].id

#: Motivo sem exigencia de payload extra — os tres que nao sao
#: `technical_failure`. Escolhido do conjunto lido do contrato.
MOTIVO_SIMPLES = sorted(MOTIVOS - {REASON_TECHNICAL_FAILURE})[0]


class RelogioDeParede:
    """Fonte de tempo de parede sob controle do teste."""

    def __init__(self) -> None:
        self._agora = 1_000_000.0

    def __call__(self) -> float:
        return self._agora

    def avanca(self, segundos: float) -> None:
        self._agora += segundos


class _ComEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.parede = RelogioDeParede()
        self.clock = ExerciseClock(T_ZERO, now=self.parede)
        self.store = InMemoryEventStore(self.clock)
        self.engine = InjectEngine(
            pack=PACK_CARREGADO,
            clock=self.clock,
            store=self.store,
            facilitator=Facilitator(user="facilitador-teste", role="control"),
            rollback_reasons=MOTIVOS,
        )

    def minutos(self, quantos: float) -> None:
        self.parede.avanca(quantos * 60)

    def tipos(self) -> list[str]:
        return [e.event_type for e in self.store.read_all()]

    def flags(self) -> dict:
        return dict(self.engine.state().flags)


class Inicio(_ComEngine):
    def test_start_grava_o_pino_do_pack(self):
        evento = self.engine.start()
        self.assertEqual(evento.event_type, EXERCISE_STARTED)
        self.assertEqual(dict(evento.payload), PACK_CARREGADO.pin_payload())

    def test_segundo_start_e_recusado(self):
        self.engine.start()
        with self.assertRaises(EngineError) as capturado:
            self.engine.start()
        self.assertEqual(capturado.exception.site, EngineSite.ALREADY_STARTED)

    def test_disparar_antes_do_start_e_recusado(self):
        with self.assertRaises(EngineError) as capturado:
            self.engine.fire(A01)
        self.assertEqual(capturado.exception.site, EngineSite.NOT_STARTED)

    def test_inject_fora_do_pack_e_recusado(self):
        self.engine.start()
        with self.assertRaises(EngineError) as capturado:
            self.engine.fire("Z99")
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_INJECT)


class PausaBloqueiaAgendado(_ComEngine):
    """ITEM 3, SEGUNDA METADE. A construcao e que faz dela prova.

    O risco obvio de um teste assim e passar pelo motivo errado: como a pausa
    CONGELA o relogio, um inject que ainda nao venceu continua nao vencendo, e
    "nada disparou" nao provaria nada sobre o bloqueio.

    Por isso o tempo avanca ATE DEPOIS do `t_relative` ANTES de pausar. No
    momento da pausa o inject ESTA em atraso — `test_o_atraso_existe_antes_da_pausa`
    afirma isso — e a posicao nao muda ao pausar. Entao a unica diferenca entre
    "em atraso" e "vazio" e a consulta a `is_paused`: nao ha outra causa
    disponivel.
    """

    def setUp(self) -> None:
        super().setUp()
        self.engine.start()
        self.minutos(6)  # A01 vence em 00:05

    def test_o_atraso_existe_antes_da_pausa(self):
        self.assertEqual(self.engine.due_injects(), (A01,))

    def test_a_posicao_nao_muda_ao_pausar(self):
        antes = self.engine.position_seconds()
        self.engine.pause()
        self.assertEqual(self.engine.position_seconds(), antes)

    def test_pausado_nao_ha_disparo_agendado(self):
        self.engine.pause()
        self.assertEqual(self.engine.due_injects(), ())
        self.assertEqual(self.engine.fire_due(), ())
        self.assertNotIn(INJECT_FIRED, self.tipos())

    def test_retomado_o_mesmo_inject_volta_a_vencer(self):
        self.engine.pause()
        self.engine.resume()
        self.assertEqual(self.engine.due_injects(), (A01,))
        self.assertEqual(len(self.engine.fire_due()), 1)

    def test_o_relogio_de_parede_correr_na_pausa_nao_solta_nada(self):
        """T4: durante o PAUSAR o de parede avanca e os de exercicio nao."""
        self.engine.pause()
        antes = self.clock.marks()
        self.minutos(30)
        depois = self.clock.marks()
        self.assertEqual(antes.exercise_time, depois.exercise_time)
        self.assertEqual(antes.exercise_timestamp, depois.exercise_timestamp)
        self.assertNotEqual(antes.wall_timestamp, depois.wall_timestamp)
        self.assertEqual(self.engine.due_injects(), ())

    def test_disparo_MANUAL_continua_permitido_na_pausa(self):
        """`01` §3 fala em disparo AGENDADO; `01` §6 lista os dois no console.

        A distincao e da spec. Bloquear o manual junto seria inventar restricao
        que nenhum documento pede, e tirar do facilitador a acao que ele usa
        justamente quando o exercicio esta parado para ajuste.
        """
        self.engine.pause()
        evento = self.engine.fire(A01)
        self.assertEqual(evento.event_type, INJECT_FIRED)
        self.assertEqual(self.engine.due_injects(), ())


class JanelaDeAgendamento(_ComEngine):
    def setUp(self) -> None:
        super().setUp()
        self.engine.start()

    def test_nada_vence_antes_da_hora(self):
        self.minutos(4)
        self.assertEqual(self.engine.due_injects(), ())

    def test_vence_na_ordem_do_t_relative(self):
        self.minutos(40)
        self.assertEqual(self.engine.due_injects(), (A01, A02, RUIDO))

    def test_o_que_ja_disparou_nao_volta(self):
        self.minutos(6)
        self.engine.fire_due()
        self.minutos(1)
        self.assertEqual(self.engine.due_injects(), ())

    def test_inject_de_ruido_dispara_e_nao_move_flag(self):
        """Ruido consome atencao, e nao estado — e o fold precisa aceita-lo.

        Um inject sem `effects` que derrubasse a projecao por `INJECT_NOT_IN_PACK`
        so apareceria no exercicio ao vivo, no momento em que o facilitador
        dispara o ruido.
        """
        self.minutos(21)
        self.engine.fire_due()
        antes = self.flags()

        self.minutos(15)
        eventos = self.engine.fire_due()
        self.assertEqual([e.correlation.inject_id for e in eventos], [RUIDO])
        self.assertEqual(self.flags(), antes)


class Idempotencia(_ComEngine):
    """ITEM 4 da DoD, pela porta do engine."""

    def test_disparar_A01_duas_vezes_produz_projecao_identica(self):
        self.engine.start()
        self.minutos(6)
        self.engine.fire(A01)
        uma = self.flags()
        self.engine.fire(A01)
        self.assertEqual(self.flags(), uma)

    def test_mas_os_dois_disparos_ficam_no_store(self):
        """Idempotencia e da PROJECAO, nao do registro.

        Se o segundo disparo sumisse do store, a timeline do AAR perderia um ato
        do facilitador — e `09` §2 diz que `facilitation` e append-only permanente.
        """
        self.engine.start()
        self.minutos(6)
        self.engine.fire(A01)
        self.engine.fire(A01)
        self.assertEqual(self.tipos().count(INJECT_FIRED), 2)


class Decisao(_ComEngine):
    def setUp(self) -> None:
        super().setUp()
        self.engine.start()
        self.minutos(21)
        self.engine.fire_due()

    def test_a_opcao_escolhida_move_a_flag_pela_projecao(self):
        antes = self.flags()
        self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")
        self.assertNotEqual(self.flags(), antes)

    def test_e_participant_action_com_ator_e_persona(self):
        evento = self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")
        self.assertEqual(evento.event_type, DECISION_MADE)
        self.assertEqual(evento.actor_id, "user-01")
        self.assertEqual(evento.persona, "ti")

    def test_aponta_para_o_inject_fired_que_a_abriu(self):
        disparo = [e for e in self.store.read_all() if e.correlation.inject_id == A02][-1]
        evento = self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")
        self.assertEqual(evento.correlation.causation_id, disparo.event_id)

    def test_opcao_fora_do_decision_point_e_recusada(self):
        with self.assertRaises(EngineError) as capturado:
            self.engine.decide(A02, "opcao_inventada", actor_id="user-01", persona="ti")
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_OPTION)

    def test_decisao_em_inject_sem_decision_point_e_recusada(self):
        with self.assertRaises(EngineError) as capturado:
            self.engine.decide(A01, OPCAO, actor_id="user-01", persona="ti")
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_DECISION_POINT)


class Rollback(_ComEngine):
    def setUp(self) -> None:
        super().setUp()
        self.engine.start()
        self.minutos(6)
        self.a01 = self.engine.fire_due()[0]
        self.depois_de_a01 = self.flags()
        self.minutos(15)
        self.engine.fire_due()
        self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")

    def test_grava_incrementa_epoch_e_nao_apaga(self):
        antes = len(self.store.read_all())
        evento = self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(evento.event_type, ROLLBACK_PERFORMED)
        self.assertEqual(len(self.store.read_all()), antes + 1)
        self.assertEqual(self.engine.state().simulation_epoch, 1)

    def test_a_projecao_volta_ao_ponto_de_corte(self):
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(self.flags(), self.depois_de_a01)

    def test_a_decisao_da_epoch_abandonada_continua_legivel_e_marcada(self):
        """ITEM 6 da DoD, pela porta do engine — `09` §3 e a D2 do checkpoint."""
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        decisoes = [e for e in self.store.read_all() if e.event_type == DECISION_MADE]
        self.assertEqual(len(decisoes), 1)
        self.assertEqual(decisoes[0].simulation_epoch, 0)

    def test_o_payload_traz_a_ancora_o_inject_e_o_motivo(self):
        evento = self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(evento.payload[TO_EVENT_ID], self.a01.event_id)
        self.assertEqual(evento.payload[TO_INJECT_ID], A01)
        self.assertEqual(evento.payload[REASON], MOTIVO_SIMPLES)

    def test_o_evento_de_rollback_fica_na_posicao_em_que_foi_ordenado(self):
        """Gravado ANTES de o clock rebobinar — `09` §3 o desenha no fim da epoch."""
        posicao = self.engine.position_seconds()
        evento = self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(label_seconds(evento.exercise_time), posicao)

    def test_o_rotulo_rebobina_ate_o_ponto_de_corte(self):
        """`01` §3: `exercise_time` rebobina ATE O CORTE, e nao ate zero."""
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(
            self.clock.marks().exercise_time, self.a01.exercise_time
        )

    def test_o_timestamp_de_exercicio_NAO_rebobina(self):
        antes = self.clock.marks().exercise_timestamp
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(self.clock.marks().exercise_timestamp, antes)

    def test_o_inject_abandonado_volta_a_vencer_e_o_anterior_nao(self):
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(self.engine.due_injects(), ())
        self.minutos(15)
        self.assertEqual(self.engine.due_injects(), (A02,))

    def test_encadeados_compoem_e_o_rotulo_rebobina_de_novo(self):
        self.engine.rollback(to_event_id=self.a01.event_id, reason=MOTIVO_SIMPLES)
        self.minutos(15)
        segundo = self.engine.fire_due()[0]
        self.minutos(5)
        self.engine.rollback(to_event_id=segundo.event_id, reason=MOTIVO_SIMPLES)
        self.assertEqual(self.clock.marks().exercise_time, segundo.exercise_time)
        self.assertEqual(self.engine.state().simulation_epoch, 2)

    def test_ancora_fora_do_store_e_recusada(self):
        with self.assertRaises(EngineError) as capturado:
            self.engine.rollback(to_event_id="01INEXISTENTE", reason=MOTIVO_SIMPLES)
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_ANCHOR)

    def test_motivo_fora_da_taxonomia_e_recusado(self):
        with self.assertRaises(EngineError) as capturado:
            self.engine.rollback(to_event_id=self.a01.event_id, reason="porque_sim")
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_REASON)

    def test_technical_failure_e_recusado_enquanto_o_campo_nao_existe(self):
        """ITEM 7 ESTA ABERTO, e a recusa e o que impede que ele passe por fechado.

        `09` §3.1 da a este motivo o efeito *"relogio de metricas congelado"*, e
        T3 exige que os extremos do intervalo sejam gravados NO EVENTO. O campo
        de payload e a P2-4 e nao existe. Emitir sem ele gravaria um rollback que
        a Fase 6 le como se nao houvesse congelamento — o requisito sumiria sem
        nada ficar vermelho.
        """
        with self.assertRaises(EngineError) as capturado:
            self.engine.rollback(
                to_event_id=self.a01.event_id, reason=REASON_TECHNICAL_FAILURE
            )
        self.assertEqual(capturado.exception.site, EngineSite.INTERVAL_NOT_RECORDABLE)
        self.assertIn("P2-4", str(capturado.exception))

    def test_a_guarda_nao_pode_ficar_orfa(self):
        """Se o contrato renomear o motivo, o engine recusa a construcao.

        Sem isto, um `spec-change` que trocasse o nome deixaria a guarda do item 7
        apontando para um valor que ninguem mais usa — e rollback de falha tecnica
        passaria a ser gravado sem intervalo, em silencio.
        """
        with self.assertRaises(EngineError) as capturado:
            InjectEngine(
                pack=PACK_CARREGADO,
                clock=self.clock,
                store=self.store,
                facilitator=Facilitator(user="x", role="control"),
                rollback_reasons={"rehearsal"},
            )
        self.assertEqual(capturado.exception.site, EngineSite.UNKNOWN_REASON)


class RoteiroDoDemo(_ComEngine):
    """O DEMO da fase, como teste: carregar, disparar A01, ler, rollback, ler."""

    def test_a_sequencia_inteira(self):
        self.engine.start()
        so_defaults = self.flags()

        self.minutos(6)
        a01 = self.engine.fire_due()[0]
        depois_de_a01 = self.flags()
        self.assertNotEqual(depois_de_a01, so_defaults)

        self.engine.pause()
        self.minutos(15)
        self.assertEqual(self.engine.due_injects(), ())
        self.engine.resume()
        self.minutos(15)
        self.engine.fire_due()
        self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")
        self.assertNotEqual(self.flags(), depois_de_a01)

        antes_do_rollback = len(self.store.read_all())
        self.engine.rollback(to_event_id=a01.event_id, reason=MOTIVO_SIMPLES)

        self.assertEqual(self.flags(), depois_de_a01)
        self.assertEqual(len(self.store.read_all()), antes_do_rollback + 1)
        self.assertEqual(self.engine.state().simulation_epoch, 1)
        self.assertEqual(
            self.tipos(),
            [
                EXERCISE_STARTED,
                INJECT_FIRED,
                EXERCISE_PAUSED,
                INJECT_FIRED,
                DECISION_MADE,
                ROLLBACK_PERFORMED,
            ],
        )


class ConformeAoContrato(_ComEngine):
    """Todo evento emitido valida contra `contracts/events.schema.yaml`.

    O store nao valida — decisao dele —, entao esta e a unica camada que impede o
    engine de emitir um envelope que o contrato recusa. `truth_layer` errado, ator
    ausente em `participant_action` e `event_type` fora da camada declarada sao
    todos recusados por aquele arquivo, e nenhum deles apareceria nos testes
    acima.
    """

    def test_todos_os_eventos_do_roteiro_validam(self):
        validador = Draft202012Validator(
            CONTRATOS["events"], registry=contract_source.registry_for(CONTRATOS)
        )
        self.engine.start()
        self.minutos(6)
        a01 = self.engine.fire_due()[0]
        self.engine.pause()
        self.engine.resume()
        self.minutos(15)
        self.engine.fire_due()
        self.engine.decide(A02, OPCAO, actor_id="user-01", persona="ti")
        self.engine.rollback(to_event_id=a01.event_id, reason=MOTIVO_SIMPLES)

        for evento in self.store.read_all():
            with self.subTest(event_type=evento.event_type):
                erros = sorted(validador.iter_errors(_envelope(evento)), key=str)
                self.assertEqual(
                    erros, [], f"{evento.event_type}: {erros[0].message if erros else ''}"
                )


def _envelope(evento) -> dict:
    """O evento na forma de documento, como o contrato o descreve.

    Campos opcionais ausentes sao OMITIDOS, e nao enviados como `null`: o
    contrato tipa `actor_id` como string, e `None` seria recusado por um motivo
    que nao tem nada a ver com o que se quer provar.
    """
    documento = {
        "event_id": evento.event_id,
        "event_type": evento.event_type,
        "truth_layer": evento.truth_layer,
        "producer": evento.producer,
        "exercise_time": evento.exercise_time,
        "exercise_timestamp": evento.exercise_timestamp,
        "wall_timestamp": evento.wall_timestamp,
        "clock_multiplier": evento.clock_multiplier,
        "simulation_epoch": evento.simulation_epoch,
        "correlation": {
            chave: valor
            for chave, valor in {
                "scenario_id": evento.correlation.scenario_id,
                "inject_id": evento.correlation.inject_id,
                "causation_id": evento.correlation.causation_id,
                "fact_id": evento.correlation.fact_id,
            }.items()
            if valor is not None
        },
        "payload": dict(evento.payload),
    }
    if evento.actor_id is not None:
        documento["actor_id"] = evento.actor_id
    if evento.persona is not None:
        documento["persona"] = evento.persona
    return documento


if __name__ == "__main__":
    unittest.main()
