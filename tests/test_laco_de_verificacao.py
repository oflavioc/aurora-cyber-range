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

from contracts.generated.events import INJECT_FIRED, VERIFICATION_PREDICATE_SATISFIED
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.inject_engine import Facilitator, InjectEngine
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.engine.verificacao import (
    NOME_DO_PREDICADO,
    LacoDeVerificacao,
    avalia,
    mundo_corrente,
)
from range_core.events.epoch import current_epoch
from range_core.events.linhagem import eventos_da_linhagem_corrente
from range_core.events.store import InMemoryEventStore
from range_core.state.simulation_state import project
from range_core.metrics.insumo import monta
from range_core.metrics.verificacao import PREDICADO_CONTENCAO, computa

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "tests" / "fixtures"))
from pack_completo import materializa  # noqa: E402

#: PACOTE COMPLETO materializado em temporario — B1 da Fase 6.
PACK = materializa()
CONTRATOS = contract_source.read_contracts()
MOTIVOS = contract_source.rollback_reasons(CONTRATOS)
#: Do contrato, pela mesma porta e pelo mesmo motivo que `MOTIVOS`.
QUALIFICADORES = contract_source.since_qualifiers(CONTRATOS)
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

#: O segundo inject e o do ponto de decisao; o terceiro e o ruido.
A02 = PACK_CARREGADO.injects[1].id
R01 = PACK_CARREGADO.injects[2].id

#: A opcao que DESLIGA a flag do predicado, derivada pelo mesmo motivo que a
#: propria flag: literal de flag e o invariante 2, e uma opcao que o fixture nao
#: movesse faria metade da matriz passar por nunca desligar nada.
OPCAO_QUE_DESLIGA = next(
    opcao.id
    for opcao in PACK_CARREGADO.injects[1].decision_point.options
    if opcao.effects.get(FLAG_QUE_O_A01_LIGA) is False
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
            since_qualifiers=QUALIFICADORES,
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

    def medidas(self):
        """Do store ate o numero, pela mesma montagem que a producao usaria.

        Vive no `setUp` compartilhado, e nao em uma classe so, porque o B1 da
        nona auditoria nasceu de as duas metades serem testadas em suites que
        nao se encontravam: os casos de rollback nao chegavam a metrica, e os
        casos de metrica nao passavam pelo engine.
        """
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        _, verificacao = monta(
            self.store.read_all(),
            lados,
            limiar_de_calibracao=0.15,
            defensibilidade={},
            escopo_revisado=frozenset(),
        )
        return {m.sigla: m for m in computa(verificacao)}


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


class RollbackQueNaoAlcancaOVeredito(_ComLaco):
    """O corte ancorado NO veredito — B1 da nona auditoria.

    As duas metades respondiam a mesma pergunta — *"este predicado ja tem
    veredito que sustenta a metrica da epoch corrente?"* — com criterios
    diferentes, e os dois conjuntos divergem exatamente aqui:

    - o engine suprimia a emissao quando havia veredito **na linhagem
      corrente**, sem olhar `simulation_epoch`;
    - o computador selecionava o veredito por **epoch corrente**.

    `range-core/events/linhagem.py` abandona apenas `ancora < j < indice`, entao
    um rollback ancorado EM ou DEPOIS do veredito o deixa vivo na linhagem e em
    epoch antiga. O engine nao reemitia, o computador descartava, e `TTCV` sumia
    — sem nada falhar, que e o modo caro de errar de `03` §3.0.

    E era IRRECUPERAVEL: redisparar o A01 nao muda nada, porque a flag ja e
    `True` e a supressao continuava valendo pelo resto do exercicio.
    """

    def _a_sequencia_do_laudo(self):
        """e0 start, e1 fire(A01), e2 veredito, e3 fire(A02), e4 rollback→e2.

        `technical_failure` e o motivo NORMATIVO aqui — `03` §3.5, *"a equipe
        nao e penalizada por bug do ambiente"* —, e a linha dele em `09` §3.1
        nao descarta epoch nenhuma: as epochs 0 e 1 continuam em calculo. E por
        isso que o veredito de epoch 0 atravessa o `apenas()` e a divergencia
        aparece no filtro seguinte, e nao antes.
        """
        self.engine.start()
        self.engine.fire(A01)
        [veredito] = self.vereditos()
        self.engine.fire(PACK_CARREGADO.injects[1].id)
        self.engine.rollback(
            to_event_id=veredito.event_id, reason="technical_failure"
        )
        return veredito

    def test_o_corte_nao_alcanca_o_veredito(self):
        """O controle da premissa: sem ele o caso passaria por outro motivo.

        Se o corte abandonasse o veredito, os dois criterios concordariam por
        construcao — que e como os tres casos de `ReavaliaDepoisDoRollback`
        ancoram, e a razao de o ramo divergente nunca ter sido exercitado.
        """
        veredito = self._a_sequencia_do_laudo()
        correntes = eventos_da_linhagem_corrente(self.store.read_all())

        self.assertIn(veredito.event_id, [e.event_id for e in correntes])
        self.assertEqual(veredito.simulation_epoch, 0)
        self.assertEqual(current_epoch(self.store.read_all()), 1)

    def test_a_contencao_continua_satisfeita_na_linhagem_corrente(self):
        """A segunda premissa: o corte nao desfaz a flag que o A01 ligou.

        O A02 e o unico evento abandonado, e ele move outra flag. Sem isto, o
        caso poderia estar exigindo veredito de um predicado que deixou de
        valer.
        """
        self._a_sequencia_do_laudo()
        correntes = eventos_da_linhagem_corrente(self.store.read_all())
        flags = project(self.store.read_all(), PACK_CARREGADO.declarations).flags

        self.assertTrue(
            avalia(
                CONTENCAO_QUANDO_O_PORTAL_CAI[PREDICADO_CONTENCAO],
                mundo_corrente(correntes, flags, since_qualifiers=QUALIFICADORES),
            )
        )

    def test_o_veredito_e_reemitido_na_epoch_nova(self):
        """`09` §3.1 — *"se a linhagem corrente satisfaz, emite na epoch nova"*."""
        self._a_sequencia_do_laudo()

        self.assertEqual(
            len([v for v in self.vereditos() if v.simulation_epoch == 1]),
            1,
            "o avaliador nao reemitiu depois do corte, e o veredito que sobrou "
            "e de epoch que a metrica nao le",
        )

    def test_ttcv_continua_marcada(self):
        """O que o participante perde quando o B1 esta vivo.

        Nada falha: a metrica continua saindo, NAO MARCADA, e a janela de
        asseguracao prematura de `03` §3.2 desaparece junto.
        """
        self._a_sequencia_do_laudo()

        self.assertTrue(
            self.medidas()["TTCV"].marcada,
            "`TTCV` sumiu apos um rollback que nem alcancou o veredito",
        )

    def test_o_redisparo_nao_e_a_saida(self):
        """A irrecuperabilidade, afirmada — e nao deduzida do caso acima.

        Se um dia a reemissao passar a depender de o participante repetir a
        acao, este teste reprova: a flag ja esta `True`, e repetir nao produz
        transicao nenhuma.
        """
        self._a_sequencia_do_laudo()
        self.engine.fire(A01)

        self.assertTrue(self.medidas()["TTCV"].marcada)


class AMatrizDoCorteEDoPredicado(_ComLaco):
    """As QUATRO combinacoes — corte x predicado —, e por que elas sao a matriz.

    O B1 entrou pela combinacao que faltava, e a razao esta na forma como as duas
    metades eram testadas: os casos do laco ancoravam SEMPRE na abertura, que
    corta o veredito, e os da metrica punham o rollback ANTES do veredito. As
    duas suites, sem se falar, escolheram a mesma metade da matriz.

    Sao duas variaveis independentes, e cada uma decide uma metade da resposta:

    | # | o corte alcanca o veredito? | o predicado ainda vale? | reemite | TTCV |
    |---|---|---|---|---|
    | A | sim, ancora na abertura     | nao — o A01 caiu junto  | nao | nao marcada |
    | B | sim, ancora no disparo      | sim — o A01 sobreviveu  | sim | marcada |
    | C | **nao**, ancora no veredito | sim                     | sim | marcada |
    | D | **nao**, ancora no desligamento | nao — a opcao desligou | nao | nao marcada |

    A CELULA **C** ERA O B1. A celula **D** e o par dela, e existe para fechar a
    correcao pelo outro lado: nela o veredito de epoch 0 esta VIVO na linhagem
    corrente, e mesmo assim `TTCV` nao marca — porque o mundo corrente deixou de
    satisfazer a contencao. Quem "alinhasse" os dois filtros fazendo a metrica
    aceitar qualquer veredito da linhagem faria C passar e D reprovar, e teria
    trocado uma metade da matriz pela outra em vez de corrigir a pergunta.

    O MOTIVO E `technical_failure` NAS QUATRO, e nao e detalhe: e a linha de `09`
    §3.1 que NAO descarta epoch nenhuma, entao a epoch 0 continua em calculo e a
    resposta depende do filtro de veredito, e nao de `epochs_em_calculo`. Com
    `facilitation`, o piso de `epochs_em_calculo` ja excluiria a epoch antiga, e
    C e D passariam por uma regra que nao e a que esta sob teste.
    """

    MOTIVO = "technical_failure"

    def _ate_o_veredito(self):
        """e0 `exercise_started`, e1 `fire(A01)`, e2 o veredito."""
        self.engine.start()
        self.engine.fire(A01)
        [veredito] = self.vereditos()
        return veredito

    def _desliga(self):
        """A opcao que poe a flag do predicado em `False` — a metade direita.

        Passa pelo `decide`, e nao por escrita direta no store: o ponto da matriz
        e que as combinacoes sejam alcancaveis pela superficie real, que e por
        onde o B1 chegaria em exercicio.
        """
        self.engine.fire(A02)
        return self.engine.decide(
            A02, OPCAO_QUE_DESLIGA, actor_id="user-01", persona="ti"
        )

    def _corta_em(self, ancora):
        """O rollback, com um evento de RUIDO entre a ancora e ele.

        O R01 e o inject sem `effects` do fixture, e e ele de proposito: o corte
        precisa ter conteudo para nao ser degenerado, e o evento abandonado nao
        pode mover a flag que e a outra variavel da matriz.
        """
        self.engine.fire(R01)
        self.engine.rollback(to_event_id=ancora.event_id, reason=self.MOTIVO)

    def na_epoch_nova(self) -> int:
        return len([v for v in self.vereditos() if v.simulation_epoch == 1])

    # -- A: o corte alcanca o veredito, e o predicado deixou de valer ---------

    def test_A_corte_ate_a_abertura_com_o_predicado_desfeito(self):
        veredito = self._ate_o_veredito()
        abertura = self.store.read_all()[0]
        self._corta_em(abertura)

        self.assertNotIn(
            veredito.event_id,
            [e.event_id for e in eventos_da_linhagem_corrente(self.store.read_all())],
        )
        self.assertEqual(self.na_epoch_nova(), 0)
        self.assertFalse(self.medidas()["TTCV"].marcada)

    # -- B: o corte alcanca o veredito, e o predicado continua valendo --------

    def test_B_corte_ate_o_disparo_com_a_flag_sobrevivente(self):
        """A escrita do PROPRIO evento ancorado sobrevive — `linhagem.py`."""
        veredito = self._ate_o_veredito()
        disparo = next(
            e for e in self.store.read_all() if e.event_id != veredito.event_id
            and e.event_type == INJECT_FIRED
        )
        self._corta_em(disparo)

        self.assertNotIn(
            veredito.event_id,
            [e.event_id for e in eventos_da_linhagem_corrente(self.store.read_all())],
        )
        self.assertEqual(self.na_epoch_nova(), 1)
        self.assertTrue(self.medidas()["TTCV"].marcada)

    # -- C: o corte NAO alcanca o veredito, e o predicado continua valendo ----

    def test_C_corte_ancorado_no_veredito_com_o_predicado_de_pe(self):
        """A celula do B1, generalizada — o reprodutor literal esta acima."""
        veredito = self._ate_o_veredito()
        self._corta_em(veredito)

        self.assertIn(
            veredito.event_id,
            [e.event_id for e in eventos_da_linhagem_corrente(self.store.read_all())],
        )
        self.assertEqual(self.na_epoch_nova(), 1)
        self.assertTrue(self.medidas()["TTCV"].marcada)

    # -- D: o corte NAO alcanca o veredito, e o predicado deixou de valer -----

    def test_D_corte_depois_do_desligamento_com_o_veredito_vivo(self):
        """O par da correcao: veredito vivo na linhagem, e `TTCV` NAO marca.

        Sem esta celula, remover o filtro de epoch da metrica — deixando
        qualquer veredito da linhagem sustentar o numero — faria a suite inteira
        passar, e `TTCV` marcaria contencao que o mundo corrente ja desfez.
        """
        veredito = self._ate_o_veredito()
        desligou = self._desliga()
        self._corta_em(desligou)

        self.assertIn(
            veredito.event_id,
            [e.event_id for e in eventos_da_linhagem_corrente(self.store.read_all())],
        )
        self.assertEqual(self.na_epoch_nova(), 0)
        self.assertFalse(self.medidas()["TTCV"].marcada)

    def test_D_o_desligamento_de_fato_desfaz_o_predicado(self):
        """O controle da celula D: sem ele, ela passaria por nunca ter valido."""
        self._ate_o_veredito()
        self._desliga()
        flags = project(self.store.read_all(), PACK_CARREGADO.declarations).flags

        self.assertFalse(flags.get(FLAG_QUE_O_A01_LIGA))


class OCaminhoFechaAteAMetrica(_ComLaco):
    """Do disparo ao numero — e e isto que torna a peca 4 consumida."""

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
