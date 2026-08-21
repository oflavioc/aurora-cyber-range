"""O laco continuo — `03` §3.1, *"o motor avalia continuamente"*.

A peca 4 entregou o avaliador e DECLAROU a fronteira: quem o chama a cada evento
e a peca 5, porque e o consumidor que decide a cadencia. Esta suite prova que a
ligacao existe e que o instante marcado e o certo.

O que ela prova:

1. o veredito e emitido NO DISPARO que satisfaz o predicado, e nao numa
   varredura posterior — `TTCV` marca o instante em que a condicao passou a
   valer, e nao o do proximo evento qualquer;
2. o laco nao emite quando nada passou a valer, e nao reemite dentro da mesma
   epoch — a emissao e por transicao;
3. depois de um rollback, o laco REAVALIA sobre a linhagem corrente;
4. o caminho fecha ate a metrica: o computador do lado da verificacao marca
   `TTCV` no instante que o laco emitiu.

A FRONTEIRA MEDIDA, e ela e testada e nao so escrita: o `Emissor` das nove
declaracoes NAO tem laco, porque por `09` §4.0 nenhuma das nove pode ser folha de
predicado. Ha teste afirmando a conjuncao sobre o catalogo real.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import VERIFICATION_PREDICATE_SATISFIED
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.inject_engine import Facilitator, InjectEngine
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.engine.verificacao import NOME_DO_PREDICADO, LacoDeVerificacao
from range_core.events.store import InMemoryEventStore
from range_core.metrics.insumo import monta
from range_core.metrics.verificacao import PREDICADO_CONTENCAO, computa

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

PACK = REPO_ROOT / "tests" / "fixtures" / "pack_minimo"
CONTRATOS = contract_source.read_contracts()
MOTIVOS = contract_source.rollback_reasons(CONTRATOS)
FLAGS = AdapterFlags.from_document(
    parse_yaml(REPO_ROOT / "domains" / "academus" / "flags.yaml"),
    source="domains/academus/flags.yaml",
)
PACK_CARREGADO = load_pack(PACK, contracts=CONTRATOS, adapter_flags=FLAGS)
A01 = PACK_CARREGADO.injects[0].id

#: A folha do predicado sai do PACK CARREGADO, e nao de um nome escrito aqui.
#: Duas razoes: literal de flag e o invariante 2, e uma folha que o fixture nao
#: movesse faria o teste passar por nunca emitir.
FLAG_QUE_O_A01_LIGA = next(
    flag for flag, valor in PACK_CARREGADO.injects[0].effects.items() if valor is True
)

T_ZERO = datetime(2026, 8, 20, 9, 0, 0)

#: O predicado e escrito aqui e nao lido do fixture: o `pack_minimo` nao tem
#: `ground_truth.yaml`, e nao deve ter — gabarito fica fora do Git (`05` §6). O
#: que esta sob teste e o LACO, e ele recebe os predicados como dado; a forma da
#: arvore de predicado ja tem suite propria.
CONTENCAO_QUANDO_O_PORTAL_CAI = {
    PREDICADO_CONTENCAO: {"all": [{"flag_true": FLAG_QUE_O_A01_LIGA}]}
}


class _ComLaco(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.clock = ExerciseClock(T_ZERO, now=lambda: float(next(parede)))
        self.store = InMemoryEventStore(self.clock)
        self.laco = LacoDeVerificacao(
            store=self.store,
            predicados=CONTENCAO_QUANDO_O_PORTAL_CAI,
            declarations=PACK_CARREGADO.declarations,
        )
        self.engine = InjectEngine(
            pack=PACK_CARREGADO,
            clock=self.clock,
            store=self.store,
            facilitator=Facilitator(user="facilitador-teste", role="control"),
            rollback_reasons=MOTIVOS,
            laco=self.laco,
        )

    def engine_sem_laco(self) -> InjectEngine:
        return InjectEngine(
            pack=PACK_CARREGADO,
            clock=self.clock,
            store=self.store,
            facilitator=Facilitator(user="facilitador-teste", role="control"),
            rollback_reasons=MOTIVOS,
        )

    def vereditos(self):
        return [
            e
            for e in self.store.read_all()
            if e.event_type == VERIFICATION_PREDICATE_SATISFIED
        ]


class OVereditoSaiNoInstanteQueSatisfaz(_ComLaco):
    def test_o_start_sozinho_nao_emite(self):
        """A flag comeca no default, e o predicado nao vale."""
        self.engine.start()
        self.assertEqual(self.vereditos(), [])

    def test_o_disparo_que_move_a_flag_emite_o_veredito_do_predicado(self):
        self.engine.start()
        self.engine.fire(A01)
        [veredito] = self.vereditos()

        self.assertEqual(veredito.payload[NOME_DO_PREDICADO], PREDICADO_CONTENCAO)

    def test_o_veredito_e_o_evento_IMEDIATAMENTE_seguinte_ao_disparo(self):
        """`03` §3.1 — *"no instante em que a condicao passa a valer"*.

        A propriedade e ADJACENCIA, e nao igualdade de `exercise_timestamp`:
        gravar leva tempo, e num relogio real o veredito cai microssegundos
        depois. Igualdade exata so valeria com o relogio-stub desta suite, e
        seria propriedade do teste em vez do sistema.

        O que se afirma e o que importa: entre o disparo e o veredito NAO HA
        outro evento. Um laco que varresse depois — no proximo inject, ou num
        tick — deixaria eventos no meio, e `TTCV` marcaria o instante deles.
        """
        self.engine.start()
        disparo = self.engine.fire(A01)
        fluxo = self.store.read_all()
        posicao = [e.event_id for e in fluxo].index(disparo.event_id)

        self.assertEqual(
            fluxo[posicao + 1].event_type, VERIFICATION_PREDICATE_SATISFIED
        )
        self.assertGreaterEqual(
            fluxo[posicao + 1].exercise_timestamp, disparo.exercise_timestamp
        )

    def test_o_laco_nao_espera_o_proximo_disparo(self):
        """O negativo da adjacencia: o veredito nao pode sair depois do A02.

        Sem este caso, um laco que so rodasse no disparo SEGUINTE passaria em
        `test_o_veredito_e_o_evento_IMEDIATAMENTE_seguinte` por acidente, se o
        teste tivesse um disparo so.
        """
        self.engine.start()
        self.engine.fire(A01)
        segundo = PACK_CARREGADO.injects[1].id
        disparo_seguinte = self.engine.fire(segundo)
        fluxo = [e.event_id for e in self.store.read_all()]

        [veredito] = self.vereditos()
        self.assertLess(
            fluxo.index(veredito.event_id), fluxo.index(disparo_seguinte.event_id)
        )

    def test_nao_reemite_dentro_da_mesma_epoch(self):
        """A emissao e por TRANSICAO — avaliacao continua nao empilha veredito."""
        self.engine.start()
        self.engine.fire(A01)
        self.engine.pause()
        self.engine.resume()

        self.assertEqual(len(self.vereditos()), 1)

    def test_sem_laco_o_engine_nao_emite_veredito_nenhum(self):
        """O controle da ligacao: quem emite e o laco, e nao o `fire`.

        Sem ele, os testes acima passariam por um `fire` que emitisse veredito
        por conta propria — e a peca 4 ficaria sem consumidor de verdade.
        """
        sem_laco = self.engine_sem_laco()
        sem_laco.start()
        sem_laco.fire(A01)

        self.assertEqual(self.vereditos(), [])


class ReavaliaDepoisDoRollback(_ComLaco):
    """`09` §3.1 — *"o avaliador sempre reavalia sobre a corrente"*."""

    def _ate_o_rollback(self):
        self.engine.start()
        abertura = self.store.read_all()[0]
        self.engine.fire(A01)
        self.engine.rollback(to_event_id=abertura.event_id, reason="facilitation")

    def test_rollback_que_desfaz_o_disparo_nao_reemite_na_epoch_nova(self):
        self._ate_o_rollback()
        self.assertEqual(
            [v for v in self.vereditos() if v.simulation_epoch == 1], []
        )

    def test_o_veredito_da_epoch_abandonada_continua_no_fluxo(self):
        """`01` §4.1 — ele nao some; o que ele nao faz e sustentar a corrente."""
        self._ate_o_rollback()
        self.assertEqual(len(self.vereditos()), 1)

    def test_redisparo_na_epoch_nova_reemite(self):
        """O controle do par: sem ele, a regra acima passaria por nunca emitir."""
        self._ate_o_rollback()
        self.engine.fire(A01)

        self.assertEqual(
            len([v for v in self.vereditos() if v.simulation_epoch == 1]), 1
        )


class OCaminhoFechaAteAMetrica(_ComLaco):
    """Do disparo ao numero — e e isto que torna a peca 4 consumida."""

    def medidas(self):
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        _, verificacao = monta(
            self.store.read_all(), lados, limiar_de_calibracao=0.15, defensibilidade={}
        )
        return {m.sigla: m for m in computa(verificacao)}

    def test_ttcv_marca_o_instante_que_o_laco_emitiu(self):
        self.engine.start()
        self.engine.fire(A01)
        [veredito] = self.vereditos()
        ttcv = self.medidas()["TTCV"]

        self.assertTrue(ttcv.marcada)
        self.assertEqual(ttcv.fim, datetime.fromisoformat(veredito.exercise_timestamp))

    def test_sem_o_laco_ttcv_nunca_marca(self):
        """A metrica continuaria SAINDO, e nao marcada — a latencia silenciosa."""
        sem_laco = self.engine_sem_laco()
        sem_laco.start()
        sem_laco.fire(A01)

        self.assertFalse(self.medidas()["TTCV"].marcada)


class AFronteiraDoEmissor(unittest.TestCase):
    """Por que o `Emissor` das nove declaracoes NAO recebe o laco.

    Nao e esquecimento: e consequencia da conjuncao de `09` §4.0. Se um dia uma
    declaracao passar a satisfazer as duas pernas, este teste reprova — e a
    ligacao passa a ser necessaria.
    """

    def registro(self) -> dict:
        return parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")[
            "x-aurora-registry"
        ]

    def test_nenhum_evento_de_lado_declaracao_pode_ser_folha_de_predicado(self):
        registro = self.registro()
        classes = dict(registro["effect_class"])
        lados = dict(registro["metric_side"])

        folhas = {
            nome
            for nome, classe in classes.items()
            if classe == "state_effect" and lados.get(nome) == "verification"
        }
        de_declaracao = {nome for nome, lado in lados.items() if lado == "declaration"}

        self.assertEqual(
            folhas & de_declaracao,
            set(),
            "um evento de lado `declaration` passou a satisfazer a conjuncao de "
            "`09` §4.0. Se ele e emitido pelo `Emissor`, a superficie de "
            "participante precisa do laco — ver `_avalia` em `inject_engine.py`.",
        )

    def test_ha_folha_de_predicado_no_catalogo(self):
        """O controle: sem ele, o teste acima passaria por nao haver folha nenhuma."""
        registro = self.registro()
        classes = dict(registro["effect_class"])
        lados = dict(registro["metric_side"])
        folhas = {
            nome
            for nome, classe in classes.items()
            if classe == "state_effect" and lados.get(nome) == "verification"
        }

        self.assertTrue(folhas)

    def test_o_emissor_nao_tem_campo_de_laco(self):
        """A ausencia e afirmada, para nao ser lida como esquecimento."""
        from range_core.participant.api.emissor import Emissor

        self.assertNotIn("laco", Emissor.__dataclass_fields__)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
