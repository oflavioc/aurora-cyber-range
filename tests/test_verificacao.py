"""O avaliador de predicados — a linhagem como lógica dele, e os três negativos.

`09_EVENT_MODEL.md` §3.1 nomeia três negativos, e esta suíte os planta:

1. **predicado meio-revertido não existe** — as folhas `event` e as de flag leem
   o mesmo mundo;
2. **satisfação de epoch abandonada não conta na corrente**;
3. **rollback atravessando o ato dessatisfaz na corrente**.

Mais o positivo que a norma exige: **reemissão na epoch nova**.

O aparato é o store real com relógio determinista — o mesmo das outras suítes de
fluxo. Um duplo de store aqui provaria que o avaliador concorda com um duplo, e a
propriedade sob teste é justamente sobre o que o rollback faz ao fluxo.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from contracts.generated.events import (
    EXERCISE_STARTED,
    IDENTITY_SCOPE_DISABLED,
    ROLLBACK_PERFORMED,
    VERIFICATION_PREDICATE_SATISFIED,
    VPN_ACCESS_REVOKED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.verificacao import (
    InstanteDeReferencia,
    Mundo,
    PredicadoMalformado,
    SemGramaticaTemporal,
    avalia,
    avaliar_e_emitir,
    instante_de_referencia,
)
from range_core.events.envelope import Correlation
from range_core.events.linhagem import eventos_da_linhagem_corrente
from range_core.events.store import EventDraft, InMemoryEventStore

#: O predicado de contenção do exemplo normativo de `03` §3.1, reduzido às duas
#: folhas `event` — que é o que basta para o eixo desta suíte.
CONTENCAO = {"all": [{"event": VPN_ACCESS_REVOKED}, {"event": IDENTITY_SCOPE_DISABLED}]}

#: Flag SINTÉTICA, e é de propósito: o avaliador é do core, e nomear uma flag do
#: `academus` aqui acoplaria um teste de núcleo a um adapter. É a mesma razão
#: pela qual `tests/test_simulation_state.py` usa flags inventadas — e o oposto
#: de `tests/test_pack_loader.py`, onde o que está sob teste **é** a conferência
#: contra o adapter real.
UMA_FLAG = "fixture.uma_flag"

#: Um instante de referência qualquer, para os testes do avaliador PURO. Ele não
#: deriva linhagem — quem deriva é `instante_de_referencia`, e a classe
#: `InstanteDeReferenciaDaLinhagem` a exercita contra o fluxo real.
_REFERENCIA = InstanteDeReferencia(
    event_id="ev-referencia",
    exercise_time="00:00",
    exercise_timestamp="2026-08-20T09:00:00Z",
    simulation_epoch=0,
    origem=EXERCISE_STARTED,
)


def _relogio() -> ExerciseClock:
    parede = iter(range(1_000_000, 1_100_000))
    return ExerciseClock(
        datetime(2026, 8, 20, 9, 0, 0), now=lambda: float(next(parede))
    )


class _ComFluxo(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryEventStore(_relogio())
        self.grava(EXERCISE_STARTED, "facilitation", "inject-engine")

    def grava(self, tipo: str, camada: str, produtor: str, **payload):
        return self.store.append(
            EventDraft(
                event_type=tipo,
                truth_layer=camada,
                producer=produtor,
                correlation=Correlation(),
                payload=payload,
            )
        )

    def ato(self, tipo: str):
        return self.grava(tipo, "participant_action", "participant-api")

    def rollback(self, ancora_id: str):
        return self.grava(
            ROLLBACK_PERFORMED,
            "facilitation",
            "gm-console",
            to_event_id=ancora_id,
            reason="facilitation",
            by_user="fac",
            role="facilitador",
        )

    def avalia_contencao(self, flags=None):
        return avaliar_e_emitir(self.store, {"containment": CONTENCAO}, flags or {})

    def vereditos(self):
        return [
            e
            for e in self.store.read_all()
            if e.event_type == VERIFICATION_PREDICATE_SATISFIED
        ]


class AvaliadorPuro(unittest.TestCase):
    """A árvore, com o mundo como parâmetro. Não sabe o que é epoch."""

    def mundo(self, tipos=(), fatos=(), flags=None) -> Mundo:
        return Mundo(frozenset(tipos), frozenset(fatos), flags or {})

    def test_all_exige_todas(self):
        self.assertFalse(avalia(CONTENCAO, self.mundo({VPN_ACCESS_REVOKED})))
        self.assertTrue(
            avalia(CONTENCAO, self.mundo({VPN_ACCESS_REVOKED, IDENTITY_SCOPE_DISABLED}))
        )

    def test_any_e_not(self):
        no = {"any": [{"event": VPN_ACCESS_REVOKED}, {"not": {"event": "x"}}]}
        self.assertTrue(avalia(no, self.mundo()))

    def test_flag_false_le_o_mesmo_mundo(self):
        no = {"flag_false": UMA_FLAG}
        self.assertTrue(avalia(no, self.mundo(flags={})))
        self.assertFalse(avalia(no, self.mundo(flags={UMA_FLAG: True})))

    def test_absence_of_por_classe_de_fato(self):
        no = {"absence_of": {"fact_class": "exfiltration"}}
        self.assertTrue(avalia(no, self.mundo()))
        self.assertFalse(avalia(no, self.mundo(fatos={"exfiltration"})))

    def test_before_recusa_alto_em_vez_de_devolver_falso(self):
        """Falso silencioso faria a contenção nunca verificar, sem explicação."""
        with self.assertRaises(PredicadoMalformado):
            avalia({"before": "T+01:00"}, self.mundo())


#: O predicado de contenção do exemplo normativo de `03` §3.1, INTEIRO — as duas
#: folhas `event` e a folha `absence_of` com o qualificador. É a forma que o
#: spec-change #49 fixou, e a que a fixture do pacote completo passou a usar.
CONTENCAO_NORMATIVA = {
    "all": [
        {"event": VPN_ACCESS_REVOKED},
        {"event": IDENTITY_SCOPE_DISABLED},
        {"absence_of": {"fact_class": "exfiltration", "since": "self"}},
    ]
}


class QualificadorSince(unittest.TestCase):
    """`since: self` — `03` §3.1, spec-change #49.

    O QUE ESTA CLASSE PROVA, e o que ela DECLARA não provar
    --------------------------------------------------------
    Prova que o predicado normativo da §3.1 **satisfaz**: um pack que declara
    exfiltração em `T-17d` e escreve a contenção na forma da spec verifica
    contenção quando os dois atos ocorrem. Antes disto o campo era lido e
    descartado (H1 da quarta auditoria), e a ausência valia sobre a linhagem
    inteira — o predicado da própria spec era insatisfazível por construção.

    **Não** prova a comparação temporal, e o motivo é medido: `Mundo.fatos`
    carrega CLASSES, não instantes, e `fact.exercise_time` (`'T-17d 02:14'`) não
    tem gramática — é `minLength: 1` no contrato. Situar um fato em relação ao
    instante de referência exige as duas coisas, e é a P6-3: uma gramática de
    `exercise_time` decide `since`, `before` e `after` de uma vez.

    Por isso a classe presente no mundo **recusa alto** em vez de responder:
    responder seria inventar semântica temporal, e a resposta plausível
    (ausência total) é exatamente o defeito que o #49 corrigiu.
    """

    def mundo(self, tipos=(), fatos=(), flags=None, referencia=_REFERENCIA) -> Mundo:
        return Mundo(frozenset(tipos), frozenset(fatos), flags or {}, referencia)

    def test_o_predicado_normativo_da_secao_3_1_satisfaz(self):
        """O caso canônico: exfiltração em `T-17d`, contenção verificada.

        O fato está no `ground_truth.yaml` do pack e **não** na linhagem — nada
        emite `fact_materialized` na árvore de hoje. Sob a leitura anterior o
        resultado seria o mesmo por acidente; o que mudou é que agora o campo é
        LIDO, e o teste abaixo mostra o que ele faz quando o fato chega.
        """
        self.assertTrue(
            avalia(
                CONTENCAO_NORMATIVA,
                self.mundo({VPN_ACCESS_REVOKED, IDENTITY_SCOPE_DISABLED}),
            )
        )

    def test_sem_os_atos_de_contencao_o_predicado_NAO_satisfaz(self):
        """Sem este negativo, o positivo acima passaria com um `all` vazio."""
        self.assertFalse(avalia(CONTENCAO_NORMATIVA, self.mundo()))

    def test_a_classe_no_mundo_recusa_por_falta_de_gramatica(self):
        """Recusa alta, nomeando o instante de referência e a pendência.

        É a mesma forma do `before`/`after`: falso silencioso faria a contenção
        nunca verificar sem explicação, e verdadeiro silencioso a faria verificar
        com vazamento em curso. As duas são piores que recusar.
        """
        with self.assertRaises(SemGramaticaTemporal) as capturado:
            avalia(
                CONTENCAO_NORMATIVA,
                self.mundo(
                    {VPN_ACCESS_REVOKED, IDENTITY_SCOPE_DISABLED},
                    fatos={"exfiltration"},
                ),
            )
        mensagem = str(capturado.exception)
        self.assertIn("exfiltration", mensagem)
        self.assertIn("exercise_time", mensagem)
        self.assertIn("P6-3", mensagem)
        self.assertIn(_REFERENCIA.event_id, mensagem)

    def test_ausencia_TOTAL_sem_since_continua_lendo_o_mundo_inteiro(self):
        """A forma sem `since` não é afetada: `03` §3.1 a mantém legítima."""
        no = {"absence_of": {"fact_class": "exfiltration"}}
        self.assertTrue(avalia(no, self.mundo()))
        self.assertFalse(avalia(no, self.mundo(fatos={"exfiltration"})))

    def test_valor_nao_definido_recusa_alto_no_avaliador(self):
        """Segunda linha de defesa — a primeira é a guarda de carga.

        Campo desconhecido não some em silêncio, que é o que `verificacao.py`
        fazia com `since` inteiro antes do H1.
        """
        with self.assertRaises(PredicadoMalformado) as capturado:
            avalia(
                {"absence_of": {"fact_class": "exfiltration", "since": "T+01:00"}},
                self.mundo(),
            )
        self.assertIn("T+01:00", str(capturado.exception))

    def test_sem_instante_de_referencia_recusa(self):
        """`since: self` sem linhagem em curso não tem "a partir de quando"."""
        with self.assertRaises(SemGramaticaTemporal):
            avalia(
                {"absence_of": {"fact_class": "exfiltration", "since": "self"}},
                self.mundo(referencia=None),
            )


class InstanteDeReferenciaDaLinhagem(_ComFluxo):
    """De onde sai o "a partir de quando" — `03` §3.1, parágrafo da linhagem.

    A §3.1 diz que depois de um rollback o instante de referência é **o da
    reavaliação na epoch nova**. Sem isso, um `since: self` congelado no primeiro
    instante de avaliação sobreviveria ao corte, e o predicado meio-revertido
    voltaria por esta porta — a mesma que `09` §3.1 fecha para as outras folhas.
    """

    def correntes(self):
        """A linhagem, e não o fluxo cru — a mesma forma que `mundo_corrente` toma."""
        return eventos_da_linhagem_corrente(self.store.read_all())

    def test_na_epoch_zero_e_o_exercise_started(self):
        referencia = instante_de_referencia(self.correntes())
        self.assertEqual(referencia.origem, EXERCISE_STARTED)
        self.assertEqual(referencia.simulation_epoch, 0)

    def test_depois_do_rollback_e_o_rollback_da_linhagem_corrente(self):
        ancora = self.store.read_all()[0]
        self.ato(VPN_ACCESS_REVOKED)
        corte = self.rollback(ancora.event_id)
        referencia = instante_de_referencia(self.correntes())
        self.assertEqual(referencia.origem, ROLLBACK_PERFORMED)
        self.assertEqual(referencia.event_id, corte.event_id)

    def test_o_rollback_ABANDONADO_nao_e_o_instante_de_referencia(self):
        """Encadeado: o corte que outro corte descartou não fixa referência.

        Sem esta direção, a referência viria do fluxo cru, e a linhagem deixaria
        de ser a lógica — que é o que este módulo inteiro existe para impedir.
        """
        ancora = self.store.read_all()[0]
        self.ato(VPN_ACCESS_REVOKED)
        descartado = self.rollback(ancora.event_id)
        corte = self.rollback(ancora.event_id)
        referencia = instante_de_referencia(self.correntes())
        self.assertEqual(referencia.event_id, corte.event_id)
        self.assertNotEqual(referencia.event_id, descartado.event_id)

    def test_sem_exercise_started_nao_ha_referencia(self):
        """Antes do início, `since: self` não tem a partir de quando."""
        self.assertIsNone(instante_de_referencia([]))


class NegativoUm_MeioRevertido(_ComFluxo):
    """As folhas `event` e as de flag leem o MESMO mundo."""

    def test_rollback_atravessa_o_ato_e_a_folha_event_o_perde(self):
        """Antes de `01` §4.1 virar classe, esta folha leria o fluxo cru.

        A flag voltaria atrás e o `vpn_access_revoked` ficaria: predicado
        satisfeito pela metade, e contenção verificada por ato desfeito.
        """
        ancora = self.store.read_all()[0]
        vpn = self.ato(VPN_ACCESS_REVOKED)
        self.ato(IDENTITY_SCOPE_DISABLED)
        self.rollback(ancora.event_id)

        self.assertIn(vpn.event_type, {e.event_type for e in self.store.read_all()})
        self.assertEqual(self.avalia_contencao(), [])


class NegativoDois_SatisfacaoAbandonada(_ComFluxo):
    def test_veredito_de_epoch_abandonada_nao_conta_na_corrente(self):
        ancora = self.store.read_all()[0]
        self.ato(VPN_ACCESS_REVOKED)
        self.ato(IDENTITY_SCOPE_DISABLED)
        primeiro = self.avalia_contencao()
        self.assertEqual(len(primeiro), 1)

        self.rollback(ancora.event_id)

        # O veredito antigo CONTINUA no store — `01` §4.1 —, e o AAR o renderiza.
        self.assertEqual(len(self.vereditos()), 1)
        # O que ele não faz é sustentar a contenção da epoch nova.
        self.assertEqual(self.avalia_contencao(), [])


class NegativoTres_RollbackDessatisfaz(_ComFluxo):
    def test_a_contencao_volta_a_ser_nao_verificada(self):
        """É o que o facilitador quis dizer ao rebobinar."""
        self.ato(VPN_ACCESS_REVOKED)
        depois = self.ato(IDENTITY_SCOPE_DISABLED)
        self.assertEqual(len(self.avalia_contencao()), 1)

        ancora = self.store.read_all()[0]
        self.rollback(ancora.event_id)
        self.assertEqual(self.avalia_contencao(), [])
        self.assertIsNotNone(depois.event_id)


class PositivoDaReemissao(_ComFluxo):
    """`09` §3.1: satisfazendo na corrente, emite **na epoch nova**."""

    def test_reemite_quando_a_condicao_volta_a_valer(self):
        ancora = self.store.read_all()[0]
        self.ato(VPN_ACCESS_REVOKED)
        self.ato(IDENTITY_SCOPE_DISABLED)
        self.assertEqual(len(self.avalia_contencao()), 1)
        epoch_antiga = self.vereditos()[0].simulation_epoch

        self.rollback(ancora.event_id)
        self.assertEqual(self.avalia_contencao(), [])

        # A equipe refaz os dois atos na epoch nova.
        self.ato(VPN_ACCESS_REVOKED)
        self.ato(IDENTITY_SCOPE_DISABLED)
        segundos = self.avalia_contencao()

        self.assertEqual(len(segundos), 1)
        self.assertGreater(segundos[0].simulation_epoch, epoch_antiga)
        self.assertEqual(len(self.vereditos()), 2)

    def test_nao_reemite_dentro_da_mesma_epoch(self):
        """A emissão é por TRANSIÇÃO — avaliação contínua não empilha veredito."""
        self.ato(VPN_ACCESS_REVOKED)
        self.ato(IDENTITY_SCOPE_DISABLED)
        self.assertEqual(len(self.avalia_contencao()), 1)
        self.assertEqual(self.avalia_contencao(), [])
        self.assertEqual(self.avalia_contencao(), [])
        self.assertEqual(len(self.vereditos()), 1)


class NaoAplicavel(_ComFluxo):
    """D5 da Fase 1 — `service_restoration` admite `not_applicable` com motivo."""

    def test_not_applicable_nao_e_avaliado_e_nao_emite(self):
        emitidos = avaliar_e_emitir(
            self.store,
            {"service_restoration": {"not_applicable": "sem servico derrubado"}},
            {},
        )
        self.assertEqual(emitidos, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
