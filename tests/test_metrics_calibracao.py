"""O escore de calibracao — `06` T11, os cinco criterios por nome.

O que esta suite prova:

1. o Brier e calculado **apenas** sobre os casos dentro do escopo revisado;
2. caso dentro do escopo e nao avaliado conta como `confidence = 0`;
3. indevido comprovado fora do escopo e **lacuna de cobertura**, e nao falso
   negativo;
4. `confidence >= 80` sobre `defensibility <= 0.2` gera **overconfidence**;
5. overconfidence e underconfidence aparecem **separados** e nao se compensam.

Os limiares e a formula sao conferidos contra a letra de `03` §5.3 e §5.4 — a
media dos quadrados e escrita a mao nos casos, para que uma formula trocada
reprove em vez de coincidir.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

from contracts.generated.events import ASSESSMENT_SUBMITTED, CONTAINMENT_DECLARED
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.calibracao import (
    CONJUNTO_INDEVIDO,
    CasoDeGabarito,
    SubmissaoForaDoContrato,
    brier,
    escore,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

#: Os tres conjuntos de `03` §5.2, com a defensibilidade que a tabela lhes da.
INDEVIDO = CasoDeGabarito(defensibilidade=1.0, conjunto=CONJUNTO_INDEVIDO)
AMBIGUO = CasoDeGabarito(defensibilidade=0.5, conjunto="ambiguo")
LEGITIMO = CasoDeGabarito(
    defensibilidade=0.0, conjunto="legitimo_aparencia_suspeita"
)


class _ComSubmissoes(unittest.TestCase):
    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede)))
        )

    def submete(self, caso: str, confianca: int, classificacao="suspicious"):
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
                    "classification": classificacao,
                    "confidence": confianca,
                    "justificativa": "revisao",
                },
            )
        )

    def calcula(self, gabarito, escopo):
        return escore(
            self.store.read_all(), gabarito=gabarito, escopo=frozenset(escopo)
        )


class OBrierSoOlhaOEscopoRevisado(_ComSubmissoes):
    """`06` T11: *"Brier calculado apenas sobre casos dentro do escopo revisado"*."""

    def test_a_formula_e_a_media_dos_quadrados(self):
        """`03` §5.3, verbatim: `media((confidence/100 - defensibility)^2)`."""
        self.submete("GC-001", 100)   # (1.0 - 1.0)^2 = 0.00
        self.submete("GC-002", 50)    # (0.5 - 0.5)^2 = 0.00
        self.submete("GC-003", 20)    # (0.2 - 0.0)^2 = 0.04

        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-002": AMBIGUO, "GC-003": LEGITIMO},
            {"GC-001", "GC-002", "GC-003"},
        )
        self.assertAlmostEqual(resultado.brier, 0.04 / 3)

    def test_caso_fora_do_escopo_nao_entra_no_brier(self):
        """Ele foi avaliado, e ainda assim nao pontua — o escopo e que decide."""
        self.submete("GC-001", 100)
        self.submete("GC-009", 0)  # erraria feio, se contasse

        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-009": INDEVIDO}, {"GC-001"}
        )
        self.assertEqual(resultado.casos_no_escore, ("GC-001",))
        self.assertEqual(resultado.brier, 0.0)

    def test_escopo_vazio_produz_brier_NULO_e_nao_zero(self):
        """Zero seria o melhor escore possivel para quem nao declarou escopo."""
        self.submete("GC-001", 100)
        resultado = self.calcula({"GC-001": INDEVIDO}, set())

        self.assertIsNone(resultado.brier)
        self.assertEqual(resultado.casos_no_escore, ())

    def test_caso_no_escopo_ausente_do_gabarito_nao_pontua(self):
        """Sem `defensibility` nao ha contra o que comparar — inventar seria nota
        a partir de nada."""
        self.submete("GC-777", 90)
        resultado = self.calcula({"GC-001": INDEVIDO}, {"GC-001", "GC-777"})

        self.assertEqual(resultado.casos_no_escore, ("GC-001",))

    def test_evento_de_outro_tipo_no_fluxo_e_ignorado(self):
        self.store.append(
            EventDraft(
                event_type=CONTAINMENT_DECLARED,
                truth_layer="participant_action",
                producer="teste",
                correlation=Correlation(),
                actor_id="a",
                persona="ti",
                payload={"justificativa": "x"},
            )
        )
        self.submete("GC-001", 100)

        self.assertEqual(self.calcula({"GC-001": INDEVIDO}, {"GC-001"}).brier, 0.0)

    def test_a_ultima_submissao_do_caso_e_a_que_vale(self):
        """Reavaliar e revisar o juizo; `03` §5 mede o juizo com que se ficou.

        E o oposto de `03` §3, onde a PRIMEIRA declaracao marca — la se mede o
        tempo ate declarar, e aqui a qualidade do que ficou declarado.
        """
        self.submete("GC-001", 10)
        self.submete("GC-001", 100)

        self.assertEqual(self.calcula({"GC-001": INDEVIDO}, {"GC-001"}).brier, 0.0)


class NaoAvaliadoContaComoConfiancaZero(_ComSubmissoes):
    """`06` T11: *"caso dentro do escopo e nao avaliado conta como confidence = 0"*."""

    def test_o_indevido_nao_avaliado_pontua_como_erro_maximo(self):
        resultado = self.calcula({"GC-001": INDEVIDO}, {"GC-001"})

        self.assertEqual(resultado.brier, 1.0)
        self.assertEqual(resultado.nao_avaliados, ("GC-001",))

    def test_o_legitimo_nao_avaliado_nao_e_penalizado(self):
        """`confidence = 0` sobre `defensibility = 0` da quadrado zero.

        Nao e indulgencia: nao acusar um legitimo E a resposta certa, e a
        formula de `03` §5.3 ja produz isso sem caso especial.
        """
        resultado = self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(resultado.brier, 0.0)
        self.assertEqual(resultado.nao_avaliados, ("GC-003",))

    def test_nao_avaliado_e_distinguido_de_avaliado_com_confianca_zero(self):
        """O AAR precisa da diferenca: uma e omissao, a outra e juizo."""
        self.submete("GC-002", 0)
        resultado = self.calcula(
            {"GC-002": AMBIGUO, "GC-004": AMBIGUO}, {"GC-002", "GC-004"}
        )

        self.assertEqual(resultado.nao_avaliados, ("GC-004",))
        self.assertIn("GC-002", resultado.casos_no_escore)


class LacunaDeCoberturaNaoEFalsoNegativo(_ComSubmissoes):
    """`06` T11, terceiro criterio, e `03` §5.4, terceira linha."""

    def test_indevido_fora_do_escopo_vira_lacuna(self):
        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-050": INDEVIDO}, {"GC-001"}
        )
        self.assertEqual(resultado.lacunas_de_cobertura, ("GC-050",))

    def test_a_lacuna_NAO_entra_no_brier(self):
        """Somar as duas diria que quem nao olhou e quem errou falharam igual."""
        self.submete("GC-001", 100)
        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-050": INDEVIDO}, {"GC-001"}
        )

        self.assertEqual(resultado.brier, 0.0)
        self.assertNotIn("GC-050", resultado.casos_no_escore)

    def test_legitimo_fora_do_escopo_NAO_vira_lacuna(self):
        """`03` §5.4 diz *indevido comprovado*, e nao "caso qualquer"."""
        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-060": LEGITIMO}, {"GC-001"}
        )
        self.assertEqual(resultado.lacunas_de_cobertura, ())

    def test_ambiguo_fora_do_escopo_NAO_vira_lacuna(self):
        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-061": AMBIGUO}, {"GC-001"}
        )
        self.assertEqual(resultado.lacunas_de_cobertura, ())

    def test_o_conjunto_decide_e_nao_a_defensibilidade(self):
        """Um pack com `defensibility: 0.7` num indevido continua produzindo
        lacuna: derivar o conjunto do numero apontaria para o caso errado."""
        indevido_atipico = CasoDeGabarito(
            defensibilidade=0.7, conjunto=CONJUNTO_INDEVIDO
        )
        resultado = self.calcula({"GC-070": indevido_atipico}, set())

        self.assertEqual(resultado.lacunas_de_cobertura, ("GC-070",))


class OsSinaisAparecemSeparados(_ComSubmissoes):
    """`03` §5.4 e `06` T11: *"nao se compensam entre si"*."""

    def test_overconfidence_no_limiar_exato(self):
        """`confidence >= 80` sobre `defensibility <= 0.2` — os dois na borda."""
        self.submete("GC-003", 80)
        resultado = self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(len(resultado.overconfidence), 1)
        self.assertEqual(resultado.overconfidence[0].caso, "GC-003")

    def test_um_ponto_abaixo_do_limiar_nao_sinaliza(self):
        """O controle da borda: sem ele, um `>` no lugar de `>=` passaria."""
        self.submete("GC-003", 79)
        self.assertEqual(self.calcula({"GC-003": LEGITIMO}, {"GC-003"}).overconfidence, ())

    def test_overconfidence_na_borda_da_DEFENSIBILIDADE(self):
        """`defensibility <= 0.2`, e a borda e 0.2 — nao 0.0.

        Este caso existe porque a prova negativa o cobrou: com todos os casos de
        overconfidence usando `defensibility = 0.0`, encolher a faixa de 0.2 para
        0.0 passava na suite inteira. A borda que a spec escreve tem de ser a
        borda que o teste exercita.
        """
        quase_legitimo = CasoDeGabarito(
            defensibilidade=0.2, conjunto="legitimo_aparencia_suspeita"
        )
        self.submete("GC-005", 90)

        resultado = self.calcula({"GC-005": quase_legitimo}, {"GC-005"})
        self.assertEqual([s.caso for s in resultado.overconfidence], ["GC-005"])

    def test_um_pouco_acima_da_borda_de_defensibilidade_nao_sinaliza(self):
        """O controle do caso acima: `0.21` esta fora da faixa de `03` §5.4."""
        acima = CasoDeGabarito(
            defensibilidade=0.21, conjunto="legitimo_aparencia_suspeita"
        )
        self.submete("GC-006", 90)

        self.assertEqual(self.calcula({"GC-006": acima}, {"GC-006"}).overconfidence, ())

    def test_confianca_alta_sobre_defensibilidade_alta_nao_sinaliza(self):
        """Acusar com forca o que se sustenta e a resposta certa."""
        self.submete("GC-001", 95)
        self.assertEqual(self.calcula({"GC-001": INDEVIDO}, {"GC-001"}).overconfidence, ())

    def test_underconfidence_exige_defensibilidade_TOTAL(self):
        """`03` §5.4: `confidence <= 30` sobre `defensibility = 1.0`."""
        self.submete("GC-001", 30)
        self.submete("GC-002", 10)  # ambiguo: 0.5, nao sinaliza
        resultado = self.calcula(
            {"GC-001": INDEVIDO, "GC-002": AMBIGUO}, {"GC-001", "GC-002"}
        )

        self.assertEqual([s.caso for s in resultado.underconfidence], ["GC-001"])

    def test_os_dois_sinais_convivem_e_nao_se_anulam(self):
        """A equipe que erra dos dois lados aparece nas DUAS listas.

        Um numero liquido daria zero aqui — a leitura exatamente oposta da
        verdadeira, e o que `03` §5.4 proibe por nome.
        """
        self.submete("GC-003", 90)   # overconfidence
        self.submete("GC-001", 10)   # underconfidence
        resultado = self.calcula(
            {"GC-003": LEGITIMO, "GC-001": INDEVIDO}, {"GC-003", "GC-001"}
        )

        self.assertEqual(len(resultado.overconfidence), 1)
        self.assertEqual(len(resultado.underconfidence), 1)

    def test_o_sinal_carrega_o_caso_e_os_dois_numeros(self):
        """Sinal sem o caso seria deteccao sem localizacao — `06` T2."""
        self.submete("GC-003", 90)
        [sinal] = self.calcula({"GC-003": LEGITIMO}, {"GC-003"}).overconfidence

        self.assertEqual((sinal.caso, sinal.confianca, sinal.defensibilidade),
                         ("GC-003", 90, 0.0))

    def test_o_nao_avaliado_pode_sinalizar_underconfidence(self):
        """`confidence = 0` sobre indevido e `<= 30`: nao olhar tambem e sinal."""
        resultado = self.calcula({"GC-001": INDEVIDO}, {"GC-001"})

        self.assertEqual([s.caso for s in resultado.underconfidence], ["GC-001"])


class ASubmissaoForaDoContratoERecusada(_ComSubmissoes):
    """A P6-11, decidida: **recusa alta**, no computador, com excecao nomeada.

    O que esta classe prova, e as duas metades importam igualmente:

    1. os quatro payloads que o contrato proibe — `900`, `-1`, `100.5` e texto —
       **recusam**, nomeando o caso e o valor;
    2. as quatro bordas exatas de `03` §5.3 e §5.4 — `0`, `30`, `80` e `100` —
       **passam**. Sem a segunda metade, uma recusa que reprovasse tudo
       satisfaria a primeira: e ela que prova que a guarda DISCRIMINA.
    """

    def submete_bruto(self, payload: dict):
        return self.store.append(
            EventDraft(
                event_type=ASSESSMENT_SUBMITTED,
                truth_layer="participant_action",
                producer="teste",
                correlation=Correlation(),
                actor_id="analista-ti",
                persona="ti",
                payload=payload,
            )
        )

    def test_confianca_acima_do_maximo_recusa_nomeando_caso_e_valor(self):
        """`confidence: 900` — o valor medido na L1 da terceira auditoria."""
        self.submete("GC-003", 900)

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(capturado.exception.caso, "GC-003")
        self.assertEqual(capturado.exception.valor, 900)

    def test_confianca_negativa_recusa(self):
        self.submete("GC-003", -1)

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(capturado.exception.valor, -1)

    def test_confianca_fracionaria_recusa(self):
        """`03` §5.4 fixa os limiares em INTEIRO, e o contrato escreve `integer`."""
        self.submete("GC-003", 100.5)

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(capturado.exception.valor, 100.5)

    def test_confianca_em_texto_recusa(self):
        """`"90"` divide por 100 com `TypeError` — recusa nomeada, e nao traceback."""
        self.submete("GC-003", "90")

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(capturado.exception.valor, "90")

    def test_booleano_nao_passa_por_inteiro(self):
        """`isinstance(True, int)` e verdadeiro em Python, e JSON nao tem essa ponte.

        Sem este caso, `True` entraria como `1` e o payload valeria `confidence: 1`
        — numero plausivel, e por isso pior que um erro.
        """
        self.submete("GC-003", True)

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertIs(capturado.exception.valor, True)

    def test_confianca_ausente_recusa(self):
        """O contrato a exige, e `x-aurora-invalid-examples` a lista por nome:
        *"sem ela nao ha Brier nem sinal comportamental"*."""
        self.submete_bruto(
            {"case_id": "GC-003", "classification": "suspicious", "justificativa": "x"}
        )

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertEqual(capturado.exception.caso, "GC-003")
        self.assertIsNone(capturado.exception.valor)

    def test_caso_ausente_recusa_sem_ter_caso_para_nomear(self):
        """Mesma regra, e a excecao diz `caso is None` em vez de inventar um."""
        self.submete_bruto(
            {"classification": "suspicious", "confidence": 72, "justificativa": "x"}
        )

        with self.assertRaises(SubmissaoForaDoContrato) as capturado:
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

        self.assertIsNone(capturado.exception.caso)

    def test_a_recusa_vale_para_o_BRIER_e_nao_so_para_o_escore(self):
        """Os dois consumidores passam por `_por_caso`, e `TTIV` chama o Brier.

        Se so o `escore` recusasse, o computador de `03` §3.3 seguiria recalculando
        o Brier a cada prefixo com o payload corrompido — que e exatamente o
        deslocamento de `TTIV` que a P6-11 mediu.
        """
        self.submete("GC-003", 900)

        with self.assertRaises(SubmissaoForaDoContrato):
            brier(
                self.store.read_all(),
                defensibilidade={"GC-003": 0.0},
                escopo=frozenset({"GC-003"}),
            )

    def test_o_valor_fora_de_faixa_NAO_e_clampado(self):
        """Clampar `900 -> 100` produziria overconfidence PLAUSIVEL e indistinguivel
        da real — `03` §5.4 le overconfidence como *"falsa acusacao"*."""
        self.submete("GC-003", 900)

        with self.assertRaises(SubmissaoForaDoContrato):
            self.calcula({"GC-003": LEGITIMO}, {"GC-003"})

    # -- O CONTROLE POSITIVO: as quatro bordas exatas passam -------------------

    def test_as_quatro_bordas_exatas_do_contrato_passam(self):
        """`0`, `30`, `80` e `100` — os extremos de faixa e os dois limiares.

        O Brier e escrito a mao: `LEGITIMO` tem `defensibility = 0.0`, entao cada
        quadrado e `(c/100)^2`.
        """
        self.submete("GC-001", 0)     # (0.00)^2 = 0.0000
        self.submete("GC-002", 30)    # (0.30)^2 = 0.0900
        self.submete("GC-003", 80)    # (0.80)^2 = 0.6400
        self.submete("GC-004", 100)   # (1.00)^2 = 1.0000

        resultado = self.calcula(
            {c: LEGITIMO for c in ("GC-001", "GC-002", "GC-003", "GC-004")},
            {"GC-001", "GC-002", "GC-003", "GC-004"},
        )

        self.assertAlmostEqual(resultado.brier, 1.73 / 4)

    def test_as_bordas_que_passam_continuam_sinalizando_o_que_sinalizavam(self):
        """A guarda nao pode mexer no que `03` §5.4 decide: `>= 80` sobre `<= 0.2`.

        `80` e `100` sinalizam; `0` e `30` nao. E a prova de que a recusa discrimina
        por CONTRATO, e nao por proximidade da borda.
        """
        self.submete("GC-001", 0)
        self.submete("GC-002", 30)
        self.submete("GC-003", 80)
        self.submete("GC-004", 100)

        resultado = self.calcula(
            {c: LEGITIMO for c in ("GC-001", "GC-002", "GC-003", "GC-004")},
            {"GC-001", "GC-002", "GC-003", "GC-004"},
        )

        self.assertEqual(
            [s.caso for s in resultado.overconfidence], ["GC-003", "GC-004"]
        )


class OsConjuntosConferemComOContrato(unittest.TestCase):
    """`CONJUNTO_INDEVIDO` contra o enum real de `line_b_case.set`."""

    def enum(self) -> list[str]:
        gt = parse_yaml(REPO_ROOT / "contracts" / "ground_truth.schema.yaml")
        return list(gt["$defs"]["line_b_case"]["properties"]["set"]["enum"])

    def test_o_conjunto_que_produz_lacuna_esta_no_enum(self):
        self.assertIn(CONJUNTO_INDEVIDO, self.enum())

    def test_o_enum_nao_cresceu_sem_decisao_neste_modulo(self):
        """Conjunto novo precisa de decisao: produz lacuna de cobertura ou nao?"""
        self.assertEqual(
            set(self.enum()),
            {CONJUNTO_INDEVIDO, "ambiguo", "legitimo_aparencia_suspeita"},
            "o enum de `line_b_case.set` mudou. Conjunto novo precisa de decisao "
            "explicita em `range-core/metrics/calibracao.py`.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
