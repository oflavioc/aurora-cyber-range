"""A projecao `aar_timeline` — as janelas dos pares e a divergencia entre avaliadores.

O que esta suite prova:

1. **a janela de asseguracao prematura sai da `aar_timeline`, e nao de um
   computador de metrica** — a prova de que a Fase 6 COMPUTA e a Fase 10
   RENDERIZA, e de que o escopo com as duas metades e este;
2. os **eventos incompativeis** de `03` §3.2 sao os de `ground_truth` DENTRO da
   janela, e so na asseguracao prematura;
3. a **lacuna de consciencia situacional** e o mesmo delta com sinal oposto, e
   NAO carrega lista de incompativeis;
4. a **janela sem contrassinatura** da peca 3 convive ali, no mesmo endereco;
5. **divergencia >= 2 pontos** na mesma competencia gera alerta, e o alerta nao
   resolve — `03` §2.4.

As `Medida` chegam dos computadores REAIS, montadas por `monta` sobre um store
real. Fabrica-las a mao aqui testaria a timeline contra uma forma inventada, e a
forma e metade do que esta sob teste.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import (
    BARS_SCORE_SUBMITTED,
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    FACT_MATERIALIZED,
    INTEGRITY_VALIDATION_DECLARED,
    VERIFICATION_PREDICATE_SATISFIED,
)
from range_core.aar.timeline import (
    ASSEGURACAO_PREMATURA,
    DIVERGENCIA_QUE_ALERTA,
    LACUNA_DE_CONSCIENCIA,
    SEM_CONTRASSINATURA,
    compoe,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.declarations.contrassinatura import (
    PERSONA_QUE_CONTRASSINA,
    PERSONA_QUE_DECLARA_INTEGRIDADE,
)
from range_core.engine.verificacao import NOME_DO_PREDICADO
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics import declaracao as computador_da_declaracao
from range_core.metrics import verificacao as computador_da_verificacao
from range_core.metrics.insumo import monta
from range_core.metrics.verificacao import PREDICADO_CONTENCAO

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402


class _ComExercicio(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.t_zero = datetime(2026, 8, 21, 9, 0, 0)
        self.store = InMemoryEventStore(
            ExerciseClock(self.t_zero, now=lambda: float(next(parede)))
        )
        self.grava(EXERCISE_STARTED, "facilitation")

    def grava(self, tipo: str, camada: str, *, ator=None, persona=None,
              correlation=None, **payload):
        return self.store.append(
            EventDraft(
                event_type=tipo,
                truth_layer=camada,
                producer="teste",
                correlation=correlation or Correlation(),
                actor_id=ator,
                persona=persona,
                payload=payload,
            )
        )

    def declara_contencao(self):
        return self.grava(CONTAINMENT_DECLARED, "participant_action",
                          ator="analista", persona="ti", justificativa="x")

    def verifica_contencao(self):
        return self.grava(VERIFICATION_PREDICATE_SATISFIED, "ground_truth",
                          **{NOME_DO_PREDICADO: PREDICADO_CONTENCAO})

    def fato(self):
        """Um evento de `ground_truth` — o mundo continuando a se mover."""
        return self.grava(FACT_MATERIALIZED, "ground_truth", fact_class="exfiltration")

    def pontua(self, avaliador: str, competencia: str, nota: int):
        return self.grava(BARS_SCORE_SUBMITTED, "evaluator_assessment",
                          ator=avaliador, persona="avaliador",
                          competency=competencia, score=nota)

    def integridade(self, persona: str, ator: str, causation_id=None):
        return self.grava(INTEGRITY_VALIDATION_DECLARED, "participant_action",
                          ator=ator, persona=persona,
                          correlation=Correlation(causation_id=causation_id),
                          justificativa="x")

    def timeline(self):
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        fluxo = self.store.read_all()
        lado_declaracao, lado_verificacao = monta(
            fluxo, lados, limiar_de_calibracao=0.15,
            defensibilidade={}, escopo_revisado=frozenset(),
        )
        return compoe(
            fluxo,
            declaracao=computador_da_declaracao.computa(lado_declaracao),
            verificacao=computador_da_verificacao.computa(lado_verificacao),
        )

    def janelas(self, tipo: str):
        return [j for j in self.timeline().janelas if j.tipo == tipo]


class AJanelaDeAsseguracaoPrematura(_ComExercicio):
    """`03` §3.2 — declaracao ANTES do veredito."""

    def test_declarar_antes_de_verificar_abre_a_janela(self):
        declarada = self.declara_contencao()
        verificada = self.verifica_contencao()
        [janela] = self.janelas(ASSEGURACAO_PREMATURA)

        self.assertEqual(janela.par, ("TTCD", "TTCV"))
        self.assertEqual(
            janela.inicio, datetime.fromisoformat(declarada.exercise_timestamp)
        )
        self.assertEqual(
            janela.fim, datetime.fromisoformat(verificada.exercise_timestamp)
        )

    def test_a_janela_NAO_sai_de_computador_de_metrica_nenhum(self):
        """A prova de que este e o escopo com as duas metades — `00` §3.2.

        Nenhum dos dois computadores tem como produzi-la: o da declaracao nao
        alcanca o veredito, e o da verificacao nao alcanca a declaracao. Se a
        janela aparecesse na saida de um deles, a particao teria furado.
        """
        self.declara_contencao()
        self.verifica_contencao()

        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        lado_declaracao, lado_verificacao = monta(
            self.store.read_all(), lados, limiar_de_calibracao=0.15,
            defensibilidade={}, escopo_revisado=frozenset(),
        )

        do_lado_declaracao = {e.event_type for e in lado_declaracao.eventos}
        do_lado_verificacao = {e.event_type for e in lado_verificacao.eventos}

        self.assertNotIn(VERIFICATION_PREDICATE_SATISFIED, do_lado_declaracao)
        self.assertNotIn(CONTAINMENT_DECLARED, do_lado_verificacao)
        self.assertEqual(len(self.janelas(ASSEGURACAO_PREMATURA)), 1)

    def test_sem_declaracao_nao_ha_janela(self):
        """Nao e janela de tamanho zero: nao houve asseguracao nenhuma."""
        self.verifica_contencao()
        self.assertEqual(self.janelas(ASSEGURACAO_PREMATURA), [])

    def test_sem_veredito_nao_ha_janela(self):
        """Sem ele nao se sabe se a declaracao era prematura."""
        self.declara_contencao()
        self.assertEqual(self.janelas(ASSEGURACAO_PREMATURA), [])


class OsEventosIncompativeis(_ComExercicio):
    """`03` §3.2 — *"os `ground_truth` eventos ocorridos dentro dessa janela"*."""

    def test_o_fato_dentro_da_janela_e_listado(self):
        self.declara_contencao()
        dentro = self.fato()
        self.verifica_contencao()
        [janela] = self.janelas(ASSEGURACAO_PREMATURA)

        self.assertIn(dentro.event_id, [e.event_id for e in janela.incompativeis])

    def test_o_fato_ANTES_da_declaracao_nao_e_listado(self):
        """Ele nao contradiz declaracao nenhuma: nao havia declaracao ainda."""
        fora = self.fato()
        self.declara_contencao()
        self.verifica_contencao()
        [janela] = self.janelas(ASSEGURACAO_PREMATURA)

        self.assertNotIn(fora.event_id, [e.event_id for e in janela.incompativeis])

    def test_acao_de_participante_na_janela_NAO_entra(self):
        """`03` §3.2 diz `ground_truth`, e nao "os eventos".

        O que torna a declaracao prematura e o MUNDO ter continuado a se mover.
        Listar acao de participante misturaria a primeira camada de `00` §3 com a
        terceira.
        """
        self.declara_contencao()
        acao = self.grava(CONTAINMENT_DECLARED, "participant_action",
                          ator="outro", persona="ti", justificativa="x")
        self.verifica_contencao()
        [janela] = self.janelas(ASSEGURACAO_PREMATURA)

        self.assertNotIn(acao.event_id, [e.event_id for e in janela.incompativeis])

    def test_o_proprio_veredito_fecha_a_janela_e_e_de_ground_truth(self):
        """O extremo entra, e e deliberado: recorta-lo abriria buraco na ponta."""
        self.declara_contencao()
        veredito = self.verifica_contencao()
        [janela] = self.janelas(ASSEGURACAO_PREMATURA)

        self.assertIn(veredito.event_id, [e.event_id for e in janela.incompativeis])


class ALacunaDeConscienciaSituacional(_ComExercicio):
    """`03` §3.2 — o mesmo delta, sinal oposto."""

    def test_verificar_antes_de_declarar_abre_a_outra_janela(self):
        verificada = self.verifica_contencao()
        declarada = self.declara_contencao()
        [janela] = self.janelas(LACUNA_DE_CONSCIENCIA)

        self.assertEqual(
            janela.inicio, datetime.fromisoformat(verificada.exercise_timestamp)
        )
        self.assertEqual(
            janela.fim, datetime.fromisoformat(declarada.exercise_timestamp)
        )

    def test_a_lacuna_NAO_carrega_incompativeis(self):
        """A equipe estava contida e nao sabia — nao ha o que contradizer.

        A §3.2 da a esta janela outra leitura: *"manteve degradacao
        desnecessaria"*, que e sobre custo e nao sobre contradicao.
        """
        self.verifica_contencao()
        self.fato()
        self.declara_contencao()
        [janela] = self.janelas(LACUNA_DE_CONSCIENCIA)

        self.assertEqual(janela.incompativeis, ())

    def test_os_dois_sentidos_nao_coexistem_no_mesmo_par(self):
        self.declara_contencao()
        self.verifica_contencao()
        tipos = [j.tipo for j in self.timeline().janelas if j.par == ("TTCD", "TTCV")]

        self.assertEqual(tipos, [ASSEGURACAO_PREMATURA])


class AJanelaSemContrassinatura(_ComExercicio):
    """A clausula herdada da peca 3, no endereco que o registro lhe deu."""

    def test_declaracao_isolada_abre_janela_ABERTA(self):
        declarada = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        [janela] = self.janelas(SEM_CONTRASSINATURA)

        self.assertTrue(janela.aberta)
        self.assertIsNone(janela.fim)
        self.assertEqual(
            janela.inicio, datetime.fromisoformat(declarada.exercise_timestamp)
        )

    def test_o_par_completo_NAO_abre_janela(self):
        primeira = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        self.integridade(
            PERSONA_QUE_CONTRASSINA, "analista-ti", causation_id=primeira.event_id
        )
        self.assertEqual(self.janelas(SEM_CONTRASSINATURA), [])

    def test_contrassinatura_INVALIDA_deixa_a_janela_aberta(self):
        """Mesma credencial nas duas maos: o predicado nao completa, e a janela
        continua sendo achado. O predicado e o mesmo do emissor e do `TTID`."""
        primeira = self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "mesma")
        self.integridade(
            PERSONA_QUE_CONTRASSINA, "mesma", causation_id=primeira.event_id
        )
        self.assertEqual(len(self.janelas(SEM_CONTRASSINATURA)), 1)

    def test_ela_convive_com_a_janela_de_asseguracao(self):
        """As duas sao leitura do AAR e da mesma natureza — o registro da fase."""
        self.integridade(PERSONA_QUE_DECLARA_INTEGRIDADE, "pro-reitora")
        self.declara_contencao()
        self.verifica_contencao()

        tipos = {j.tipo for j in self.timeline().janelas}
        self.assertEqual(tipos, {SEM_CONTRASSINATURA, ASSEGURACAO_PREMATURA})


class ADivergenciaEntreAvaliadores(_ComExercicio):
    """`03` §2.4 — *"divergencia >= 2 pontos na mesma competencia gera alerta"*."""

    def test_dois_pontos_exatos_alertam(self):
        self.pontua("avaliador-a", "incident_triage", 1)
        self.pontua("avaliador-b", "incident_triage", 3)
        [alerta] = self.timeline().divergencias

        self.assertEqual(alerta.competencia, "incident_triage")
        self.assertEqual(alerta.distancia, DIVERGENCIA_QUE_ALERTA)
        self.assertEqual(alerta.avaliadores, ("avaliador-a", "avaliador-b"))

    def test_um_ponto_nao_alerta(self):
        """O controle da borda: sem ele, um `>` no lugar de `>=` passaria."""
        self.pontua("avaliador-a", "incident_triage", 2)
        self.pontua("avaliador-b", "incident_triage", 3)
        self.assertEqual(self.timeline().divergencias, ())

    def test_a_distancia_e_entre_os_EXTREMOS_e_nao_entre_consecutivos(self):
        """Tres avaliadores em 0, 1 e 2: nenhum par consecutivo alcanca dois."""
        for avaliador, nota in (("a", 0), ("b", 1), ("c", 2)):
            self.pontua(avaliador, "escalation", nota)
        [alerta] = self.timeline().divergencias

        self.assertEqual((alerta.menor, alerta.maior), (0, 2))

    def test_competencias_diferentes_nao_divergem_entre_si(self):
        self.pontua("avaliador-a", "incident_triage", 0)
        self.pontua("avaliador-b", "escalation", 4)
        self.assertEqual(self.timeline().divergencias, ())

    def test_um_avaliador_so_nao_diverge(self):
        """Divergencia e entre avaliadores; um so nao discorda de ninguem."""
        self.pontua("avaliador-a", "incident_triage", 0)
        self.assertEqual(self.timeline().divergencias, ())

    def test_a_ULTIMA_nota_do_avaliador_vale(self):
        """Revisar a nota e revisar o juizo — o AAR sinaliza o que ficou."""
        self.pontua("avaliador-a", "incident_triage", 0)
        self.pontua("avaliador-a", "incident_triage", 3)
        self.pontua("avaliador-b", "incident_triage", 4)

        self.assertEqual(self.timeline().divergencias, ())

    def test_o_alerta_nao_resolve_e_carrega_os_dois_extremos(self):
        """`03` §2.4: *"nao resolve automaticamente; sinaliza para o debriefing"*.

        Consolidar numa nota unica seria resolver, e a §2.4 diz que o mecanismo
        nao resolve.
        """
        self.pontua("avaliador-a", "analytical_rigor", 0)
        self.pontua("avaliador-b", "analytical_rigor", 4)
        [alerta] = self.timeline().divergencias

        self.assertEqual((alerta.menor, alerta.maior), (0, 4))
        self.assertFalse(hasattr(alerta, "consolidada"))


class ACompetenciaConfereComORubricario(unittest.TestCase):
    """A competencia pontuada tem de ser uma das nove de `03` §2.3.

    O payload de `bars_score_submitted` NAO a enumera de proposito — a lista vive
    em `rubrics.schema.yaml`, e uma terceira copia divergiria. O cruzamento e
    aqui, na mesma forma do `metric_side` contra o catalogo.
    """

    def test_as_competencias_da_suite_existem_no_contrato_de_rubrica(self):
        rubricas = parse_yaml(REPO_ROOT / "contracts" / "rubrics.schema.yaml")
        declaradas = set(rubricas["properties"]["competency"]["enum"])

        usadas = {"incident_triage", "escalation", "analytical_rigor"}
        self.assertTrue(usadas <= declaradas)

    def test_a_escala_da_rubrica_e_a_do_payload(self):
        """`0-4` na rubrica, `minimum 0 / maximum 4` no payload.

        Divergir faria o limiar de dois pontos de `03` §2.4 significar outra
        coisa: dois pontos em `0-4` sao metade da amplitude, em `0-100` sao ruido.
        """
        rubricas = parse_yaml(REPO_ROOT / "contracts" / "rubrics.schema.yaml")
        eventos = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        nota = eventos["$defs"]["bars_score_payload"]["properties"]["score"]

        self.assertEqual(rubricas["properties"]["scale"]["const"], "0-4")
        self.assertEqual((nota["minimum"], nota["maximum"]), (0, 4))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
