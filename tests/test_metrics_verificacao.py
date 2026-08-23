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
    ASSESSMENT_SUBMITTED,
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    ROLLBACK_PERFORMED,
    VERIFICATION_PREDICATE_SATISFIED,
    VPN_ACCESS_REVOKED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.epoch import (
    MOTIVO_ENSAIO,
    MOTIVO_FALHA_TECNICA,
    SemMarcoZero,
    marco_zero,
)
from range_core.metrics.insumo import monta
from range_core.metrics.verificacao import (
    NOME_DO_PREDICADO,
    PREDICADO_CONTENCAO,
    PREDICADO_RESTAURACAO,
    SIGLA_POR_PREDICADO,
    computa,
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
            escopo_revisado=frozenset(),
        )
        return verificacao

    def medidas(self) -> dict[str, object]:
        return {m.sigla: m for m in computa(self.insumo())}


class MarcaOsDoisInstantes(_ComExercicio):
    def test_contencao_verificada_marca_ttcv(self):
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        ttcv = self.medidas()["TTCV"]

        self.assertTrue(ttcv.marcada)
        self.assertEqual(ttcv.fim, datetime.fromisoformat(veredito.exercise_timestamp))

    def test_restauracao_verificada_marca_ttrv(self):
        self.satisfaz(PREDICADO_RESTAURACAO)
        self.assertTrue(self.medidas()["TTRV"].marcada)

    def test_um_predicado_nao_arrasta_o_outro(self):
        self.satisfaz(PREDICADO_CONTENCAO)
        medidas = self.medidas()

        self.assertTrue(medidas["TTCV"].marcada)
        self.assertFalse(medidas["TTRV"].marcada)

    def test_sem_veredito_a_medida_e_nao_verificada_e_nao_zero(self):
        """Zero pareceria medicao. `None` diz que nao houve veredito."""
        for sigla, medida in self.medidas().items():
            with self.subTest(sigla=sigla):
                self.assertFalse(medida.marcada)
                self.assertIsNone(medida.fim)
                self.assertIsNone(medida.decorrido)
                self.assertNotEqual(medida.decorrido, timedelta())

    def test_o_decorrido_e_medido_desde_t0(self):
        veredito = self.satisfaz(PREDICADO_CONTENCAO)
        esperado = datetime.fromisoformat(veredito.exercise_timestamp) - self.t_zero

        self.assertEqual(self.medidas()["TTCV"].decorrido, esperado)

    def test_as_tres_siglas_saem_sempre(self):
        """Metrica que some do AAR e pior que metrica ausente — `03` §3.0.

        Sao TRES desde a peca 6: `TTIV` entrou, e o verificador dela nao e o
        mundo (`03` §3.3).
        """
        self.assertEqual(set(self.medidas()), {"TTCV", "TTRV", "TTIV"})


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
        self.assertFalse(self.medidas()["TTCV"].marcada)

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

        self.assertFalse(self.medidas()["TTCV"].marcada)

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

        self.assertTrue(ttcv.marcada)
        self.assertEqual(
            ttcv.fim, datetime.fromisoformat(reemitido.exercise_timestamp)
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

        self.assertEqual(self.medidas()["TTCV"].decorrido, bruto)

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

        descontado = self.medidas()["TTCV"].decorrido
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

        self.assertFalse(self.medidas()["TTCV"].marcada)


class MarcoZero(_ComExercicio):
    def test_t0_sai_do_exercise_started(self):
        self.assertEqual(marco_zero(self.insumo().epoch), self.t_zero)

    def test_t0_sobrevive_ao_descarte_da_epoch_que_o_registrou(self):
        """P6-4, decidida: T0 e atributo do EXERCICIO, e nao da epoch.

        `01` §3 o poe na mao do facilitador, e o `exercise_started` registra o
        ato — nao e a fonte dele. O descarte de `09` §3.1 tira EVENTOS do
        calculo, e T0 nao e um evento: e o zero contra o qual eles sao medidos.
        """
        self.rollback(MOTIVO_ENSAIO)
        self.satisfaz(PREDICADO_CONTENCAO)

        self.assertEqual(marco_zero(self.insumo().epoch), self.t_zero)
        self.assertTrue(self.medidas()["TTCV"].marcada)

    def test_sem_exercise_started_nenhum_levanta_em_vez_de_devolver_nulo(self):
        """A recusa continua; so o gatilho mudou.

        Exercicio sem T0 nao produz metrica. `None` faria todo decorrido virar
        nulo, e o AAR imprimiria ausencia de medicao onde houve medicao.
        """
        parede = iter(range(1_000_000, 1_100_000))
        vazio = InMemoryEventStore(
            ExerciseClock(self.t_zero, now=lambda: float(next(parede)))
        )
        lados = dict(registro()["x-aurora-registry"]["metric_side"])
        _, insumo = monta(
            vazio.read_all(), lados, limiar_de_calibracao=0.15, defensibilidade={}, escopo_revisado=frozenset()
        )

        with self.assertRaises(SemMarcoZero):
            computa(insumo)


class TTIVCruzaOLimiarDeCalibracao(_ComExercicio):
    """`03` §3.3 — o instante em que o conjunto de `assessment_submitted` atinge
    `calibration.threshold`, medido contra a defensibilidade do gabarito."""

    def insumo_com(self, limiar: float, defensibilidade, escopo):
        lados = dict(registro()["x-aurora-registry"]["metric_side"])
        _, verificacao = monta(
            self.store.read_all(),
            lados,
            limiar_de_calibracao=limiar,
            defensibilidade=defensibilidade,
            escopo_revisado=frozenset(escopo),
        )
        return verificacao

    def submete(self, caso: str, confianca: int):
        return self.store.append(
            EventDraft(
                event_type=ASSESSMENT_SUBMITTED,
                truth_layer="participant_action",
                producer="teste",
                correlation=Correlation(),
                actor_id="analista-ti",
                persona="ti",
                payload={
                    "case_id": caso,
                    "classification": "suspicious",
                    "confidence": confianca,
                    "justificativa": "revisao",
                },
            )
        )

    def ttiv(self, limiar, defensibilidade, escopo):
        medidas = {
            m.sigla: m for m in computa(self.insumo_com(limiar, defensibilidade, escopo))
        }
        return medidas["TTIV"]

    def test_sem_submissao_nenhuma_ttiv_nao_marca(self):
        """O Brier comeca alto: caso do escopo nao avaliado conta como zero."""
        self.assertFalse(self.ttiv(0.15, {"GC-001": 1.0}, {"GC-001"}).marcada)

    def test_a_submissao_que_cruza_o_limiar_marca(self):
        submissao = self.submete("GC-001", 100)
        ttiv = self.ttiv(0.15, {"GC-001": 1.0}, {"GC-001"})

        self.assertTrue(ttiv.marcada)
        self.assertEqual(
            ttiv.fim, datetime.fromisoformat(submissao.exercise_timestamp)
        )

    def test_marca_a_PRIMEIRA_que_cruza_e_nao_a_ultima(self):
        """`03` §3 mede o tempo ATE a integridade estar validada.

        Continuar submetendo depois de cruzar nao move o instante em que se
        cruzou.
        """
        primeira = self.submete("GC-001", 100)
        self.submete("GC-002", 50)

        ttiv = self.ttiv(0.15, {"GC-001": 1.0, "GC-002": 0.5}, {"GC-001", "GC-002"})
        self.assertEqual(
            ttiv.fim, datetime.fromisoformat(primeira.exercise_timestamp)
        )

    def test_a_submissao_que_NAO_cruza_nao_marca(self):
        """Confianca alta sobre caso legitimo: o Brier sobe, e nao desce."""
        self.submete("GC-003", 100)
        self.assertFalse(self.ttiv(0.15, {"GC-003": 0.0}, {"GC-003"}).marcada)

    def test_cruzar_e_MENOR_OU_IGUAL_ao_limiar(self):
        """`04` §2 chama o valor de *Brier maximo*, e maximo inclui o valor.

        `confidence 50` sobre `defensibility 1.0` da `(0.5-1.0)^2 = 0.25`, e os
        tres numeros sao EXATOS em binario — por isso a igualdade e testavel.

        Com `confidence 60` o mesmo caso daria `0.16000000000000003`, e o teste
        mediria o arredondamento em vez da regra. O limite fica dito: a
        comparacao e `<=` sobre float, e igualdade exata na borda depende de o
        valor ser representavel. Um epsilon aqui trocaria um arbitrio conhecido
        por outro escondido, e `04` §2 nao o autoriza.
        """
        self.submete("GC-001", 50)
        self.assertTrue(self.ttiv(0.25, {"GC-001": 1.0}, {"GC-001"}).marcada)

    def test_um_fio_acima_do_limiar_nao_marca(self):
        """O controle da borda: sem ele, um `<` no lugar de `<=` passaria."""
        self.submete("GC-001", 50)
        self.assertFalse(self.ttiv(0.2499, {"GC-001": 1.0}, {"GC-001"}).marcada)

    def test_o_limiar_vem_do_INSUMO_e_nao_de_constante(self):
        """Limiar de pack e dado, e `00` §3.2 exige que chegue assim."""
        self.submete("GC-001", 50)

        self.assertFalse(self.ttiv(0.1, {"GC-001": 1.0}, {"GC-001"}).marcada)
        self.assertTrue(self.ttiv(0.9, {"GC-001": 1.0}, {"GC-001"}).marcada)

    def test_escopo_vazio_nao_marca_por_brier_nulo(self):
        """Sem caso no escopo nao ha media, e `None` nao cruza limiar nenhum.

        Marcar aqui daria integridade validada a quem nao declarou escopo.
        """
        self.submete("GC-001", 100)
        self.assertFalse(self.ttiv(0.15, {"GC-001": 1.0}, set()).marcada)

    def test_ttiv_e_medido_desde_t0_como_as_outras_metades(self):
        submissao = self.submete("GC-001", 100)
        ttiv = self.ttiv(0.15, {"GC-001": 1.0}, {"GC-001"})

        self.assertEqual(ttiv.inicio, self.t_zero)
        self.assertEqual(
            ttiv.decorrido,
            datetime.fromisoformat(submissao.exercise_timestamp) - self.t_zero,
        )


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

    def test_a_chave_TEM_DONO_UNICO_e_nao_e_redeclarada(self):
        """A igualdade acima virou tautologia, e este e o teste que sobrou.

        Ate o B1 da nona auditoria a chave era escrita nos DOIS modulos, e o teste
        acima cruzava as copias. A funcao unica do veredito precisa dela, e a
        chave foi junto para `range-core/events/veredito.py`: os dois modulos
        passaram a IMPORTA-LA, e comparar duas importacoes da mesma constante nao
        prova mais nada.

        O que ainda se pode afirmar e o que importa — que nenhum dos dois voltou
        a escrever o literal —, e isso se ve no fonte.
        """
        from range_core.events import veredito as dono

        self.assertEqual(NOME_DO_PREDICADO, dono.NOME_DO_PREDICADO)

        raiz = REPO_ROOT / "range-core"
        redeclaram = [
            caminho.relative_to(raiz).as_posix()
            for caminho in raiz.rglob("*.py")
            if caminho != Path(dono.__file__)
            and f"NOME_DO_PREDICADO = " in caminho.read_text(encoding="utf-8")
        ]

        self.assertEqual(
            redeclaram,
            [],
            "a chave do payload do veredito voltou a ter segunda declaracao. Ela "
            "tem dono unico em `range-core/events/veredito.py` desde o B1 da "
            "nona auditoria — importe de la.",
        )


class TTIVObedeceAOSMESMOSEFEITOSDeEpoch(_ComExercicio):
    """H1 da terceira auditoria — UM criterio de epoch para os DOIS lados.

    `09` §3.1 manda "metricas recomputadas a partir da nova epoch"
    (`facilitation`) e "metricas da nova epoch" (`adjudication`), **sem excecao
    por lado**. O computador da declaracao ja obedecia; o da verificacao lia so o
    descarte de `rehearsal`, e `assessment_submitted` de epoch anulada continuava
    alimentando o Brier — `TTIV` marcava em instante de linha temporal rebobinada.

    E o defeito na forma que esta fase existe para impedir: nada falha, a metrica
    continua sendo calculada.
    """

    def insumo_com(self, limiar, defensibilidade, escopo):
        lados = dict(registro()["x-aurora-registry"]["metric_side"])
        _, verificacao = monta(
            self.store.read_all(), lados, limiar_de_calibracao=limiar,
            defensibilidade=defensibilidade, escopo_revisado=frozenset(escopo),
        )
        return verificacao

    def submete(self, caso: str, confianca: int):
        return self.store.append(
            EventDraft(
                event_type=ASSESSMENT_SUBMITTED, truth_layer="participant_action",
                producer="teste", correlation=Correlation(),
                actor_id="analista-ti", persona="ti",
                payload={"case_id": caso, "classification": "suspicious",
                         "confidence": confianca, "justificativa": "x"},
            )
        )

    def ttiv(self, limiar=0.15, defensibilidade=None, escopo=("GC-001",)):
        insumo = self.insumo_com(limiar, defensibilidade or {"GC-001": 1.0}, escopo)
        return {m.sigla: m for m in computa(insumo)}["TTIV"]

    def test_facilitation_anula_a_submissao_da_epoch_anterior(self):
        """*"Metricas recomputadas a partir da nova epoch"* — sem excecao por lado."""
        self.submete("GC-001", 100)
        self.rollback("facilitation")

        self.assertFalse(self.ttiv().marcada)

    def test_adjudication_anula_igual(self):
        """`09` §3.1 poe `adjudication` como o facilitador ANULANDO decisao por
        informacao fora de banda, e diz que precisa aparecer no debriefing.
        `TTIV` marcando em instante rebobinado e o oposto disso."""
        self.submete("GC-001", 100)
        self.rollback("adjudication")

        self.assertFalse(self.ttiv().marcada)

    def test_a_submissao_da_epoch_NOVA_conta(self):
        """O controle: sem ele, as duas acima passariam por reprovar sempre."""
        self.submete("GC-001", 0)
        self.rollback("facilitation")
        nova = self.submete("GC-001", 100)
        ttiv = self.ttiv()

        self.assertTrue(ttiv.marcada)
        self.assertEqual(ttiv.fim, datetime.fromisoformat(nova.exercise_timestamp))

    def test_technical_failure_NAO_anula_a_submissao(self):
        """A assimetria de `09` §3.1: a equipe nao e penalizada por bug do
        ambiente, e anular o que ela ja submeteu a obrigaria a resubmeter."""
        self.submete("GC-001", 100)
        self.rollback(MOTIVO_FALHA_TECNICA, congela=(self.t_zero, self.t_zero))

        self.assertTrue(self.ttiv().marcada)

    def test_a_SIMETRIA_com_TTID_e_o_ponto(self):
        """`TTID` reinicia na anulacao; `TTIV` medindo de outra linha faria o
        delta do par — *o achado* de `03` §3.2 — comparar duas linhas temporais.
        """
        self.submete("GC-001", 100)
        self.rollback("adjudication")
        medidas = {m.sigla: m for m in computa(self.insumo_com(0.15, {"GC-001": 1.0}, {"GC-001"}))}

        self.assertFalse(medidas["TTIV"].marcada)
        self.assertFalse(medidas["TTCV"].marcada)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
