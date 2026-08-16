"""A projeção materializada: cache frio, divergência, e quem tem autoridade.

POR QUE NÃO HÁ DUPLO AQUI — e esta é a decisão mais consequente da suíte
------------------------------------------------------------------------
A Fase 2 fechou com **zero mocks** na árvore, e a auditoria PASS registrou isso
como achado. Um duplo de Redis seria a primeira dublagem — e ela testaria a si
mesma: um objeto que reimplementa `get`/`set` prova que o objeto funciona, não
que a integração funciona.

`InMemoryProjectionCache` **não é duplo**: é o segundo backend da mesma porta,
como `InMemoryEventStore` é do store. Ele existe para o processo único — o DEMO,
o engine sem Redis — e é exercitado como implementação de verdade.

Para o Redis, a forma é a que o Postgres já estabeleceu e a auditoria já
aprovou: **variável própria, `skip` declarado que imprime o comando, e o CI
subindo o serviço**. `AURORA_TEST_REDIS_URL`, e não `REDIS_URL`, pelo mesmo
motivo da outra: estes testes **escrevem e apagam** a chave.

O QUE ESTÁ SOB TESTE, e o que cada classe prova
------------------------------------------------
- `Politica` — cache frio e divergência, contra a porta, sem depender de backend.
- `NoRedis` — a mesma porta, contra o Redis de verdade, com serialização real.
- `Autoridade` — que a porta **não tem** por onde receber estado pronto.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime

from contracts.generated.events import EXERCISE_STARTED, INJECT_FIRED
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore, StreamHead
from range_core.state.cache import (
    InMemoryProjectionCache,
    RedisProjectionCache,
    SimulationStateCache,
    current,
)
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    Declarations,
)

REDIS_ENV = "AURORA_TEST_REDIS_URL"
_URL = os.environ.get(REDIS_ENV)

RAZAO = (
    f"{REDIS_ENV} nao definida. Estes testes ESCREVEM e APAGAM a chave da "
    "projecao, e por isso nao usam `REDIS_URL`. Para rodar:\n"
    f"    docker compose up -d redis && {REDIS_ENV}=redis://127.0.0.1:6379/1 "
    "python -m unittest discover -s tests"
)

#: Flag de default `True`. É a forma do `academus.federated_session_active`, e é
#: o caso que torna "responder com defaults" errado em vez de apenas impreciso.
FLAG_LIGADA_POR_DEFAULT = "fixture.sessao_ativa"
FLAG_DESLIGADA = "fixture.portal_fora"

DECLARACOES = Declarations(
    pack_id="pack-de-teste",
    schema_version=2,
    content_hash="0" * 64,
    canonicalization="v1",
    flag_defaults={FLAG_LIGADA_POR_DEFAULT: True, FLAG_DESLIGADA: False},
    inject_effects={"A01": {FLAG_LIGADA_POR_DEFAULT: False, FLAG_DESLIGADA: True}},
    option_effects={},
)


def _relogio() -> ExerciseClock:
    parede = iter(range(1_000_000, 1_100_000))
    return ExerciseClock(datetime(2026, 8, 16, 9, 0, 0), now=lambda: float(next(parede)))


def _store_com_exercicio() -> InMemoryEventStore:
    """Um exercício em curso: `exercise_started` e um inject que move as flags."""
    store = InMemoryEventStore(_relogio())
    store.append(
        EventDraft(
            event_type=EXERCISE_STARTED,
            truth_layer="facilitation",
            producer="inject-engine",
            correlation=Correlation(scenario_id="pack-de-teste"),
            payload={
                PACK_ID: "pack-de-teste",
                PACK_SCHEMA_VERSION: 2,
                PACK_CONTENT_HASH: "0" * 64,
                PACK_CANONICALIZATION: "v1",
            },
        )
    )
    store.append(
        EventDraft(
            event_type=INJECT_FIRED,
            truth_layer="facilitation",
            producer="inject-engine",
            correlation=Correlation(scenario_id="pack-de-teste", inject_id="A01"),
        )
    )
    return store


class Politica(unittest.TestCase):
    """Cache frio e divergência — as duas decisões da D1, como comportamento."""

    def setUp(self) -> None:
        self.store = _store_com_exercicio()
        self.cache = InMemoryProjectionCache()

    def test_cache_frio_NAO_responde_com_defaults(self):
        """A propriedade que motivou a decisão inteira.

        Com `exercise_started` no fluxo, responder defaults inverteria a flag de
        default `True` — o caso que motivou o estado total do fold. Aqui o cache
        está vazio e a resposta ainda é a correta, porque o caminho é reconstruir.
        """
        self.assertIsNone(self.cache.read())

        estado = current(self.store, DECLARACOES, self.cache)

        self.assertFalse(estado.flags[FLAG_LIGADA_POR_DEFAULT])
        self.assertTrue(estado.flags[FLAG_DESLIGADA])
        self.assertNotEqual(
            dict(estado.flags),
            dict(DECLARACOES.flag_defaults),
            "cache frio respondeu o default, que e o mundo antes do inject",
        )

    def test_defaults_NAO_sao_fallback_mas_sao_a_resposta_do_fluxo_vazio(self):
        """A outra metade, e é o que impede a primeira de virar superstição.

        Defaults não são proibidos: são o resultado correto de foldar um fluxo
        vazio. O que é proibido é respondê-los quando há exercício.
        """
        vazio = InMemoryEventStore(_relogio())
        estado = current(vazio, DECLARACOES, InMemoryProjectionCache())
        self.assertEqual(dict(estado.flags), dict(DECLARACOES.flag_defaults))

    def test_a_segunda_leitura_vem_do_cache(self):
        primeira = current(self.store, DECLARACOES, self.cache)
        gravada = self.cache.read()
        self.assertIsNotNone(gravada)
        self.assertEqual(gravada.head, self.store.head())

        segunda = current(self.store, DECLARACOES, self.cache)
        self.assertEqual(dict(segunda.flags), dict(primeira.flags))

    def test_evento_novo_invalida_o_cache(self):
        """Divergência detectada pela CABEÇA, não pelo estado."""
        current(self.store, DECLARACOES, self.cache)
        cabeca_antes = self.cache.read().head

        self.store.append(
            EventDraft(
                event_type=INJECT_FIRED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste", inject_id="A01"),
            )
        )

        self.assertNotEqual(self.store.head(), cabeca_antes)
        current(self.store, DECLARACOES, self.cache)
        self.assertEqual(self.cache.read().head, self.store.head())

    def test_projecao_de_outro_fluxo_e_recusada(self):
        """Cache que ficou para trás não é servido — nem quando o tamanho bate.

        `StreamHead` tem dois campos justamente para isto: contagem igual com
        conteúdo diferente é o caso do store restaurado de backup.
        """
        current(self.store, DECLARACOES, self.cache)
        cabeca_real = self.store.head()

        forjada = StreamHead(count=cabeca_real.count, last_event_id="01OUTRO")
        self.cache.refresh(self.store.read_all(), DECLARACOES, forjada)

        self.assertNotEqual(self.cache.read().head, cabeca_real)
        current(self.store, DECLARACOES, self.cache)
        self.assertEqual(self.cache.read().head, cabeca_real)

    def test_a_cabeca_e_lida_antes_da_projecao(self):
        """A ordem em `current`, e o motivo dela.

        Lida depois, uma escrita que caísse no meio faria a validação comparar a
        projeção nova com a cabeça velha e concluir que vale. O teste afirma a
        ordem observando o store.
        """
        ordem: list[str] = []

        class StoreQueObserva(InMemoryEventStore):
            def head(self):
                ordem.append("head")
                return super().head()

        class CacheQueObserva(InMemoryProjectionCache):
            def read(self):
                ordem.append("read")
                return super().read()

        store = StoreQueObserva(_relogio())
        current(store, DECLARACOES, CacheQueObserva())
        self.assertEqual(ordem[:2], ["head", "read"])


class Autoridade(unittest.TestCase):
    """A porta não tem por onde receber estado pronto — e isso é do tipo, não do teste."""

    def test_a_porta_nao_expoe_metodo_que_aceite_estado(self):
        publicos = {
            nome
            for nome in dir(SimulationStateCache)
            if not nome.startswith("_")
        }
        self.assertEqual(publicos, {"refresh", "read"})

    def test_refresh_recebe_o_fluxo_e_folda(self):
        """Se `refresh` aceitasse estado, procedência viraria confiança."""
        import inspect

        parametros = set(inspect.signature(SimulationStateCache.refresh).parameters)
        self.assertEqual(parametros, {"self", "events", "declarations", "head"})


@unittest.skipIf(_URL is None, RAZAO)
class NoRedis(unittest.TestCase):
    """A mesma porta, contra o Redis de verdade. Sem duplo, por decisão."""

    def setUp(self) -> None:
        import redis

        self.client = redis.Redis.from_url(_URL, decode_responses=True)
        self.chave = "aurora:teste:simulation_state"
        self.client.delete(self.chave)
        self.addCleanup(self.client.delete, self.chave)

        self.store = _store_com_exercicio()
        self.cache = RedisProjectionCache(self.client, chave=self.chave)

    def test_frio_reconstroi_e_grava(self):
        self.assertIsNone(self.cache.read())
        estado = current(self.store, DECLARACOES, self.cache)
        self.assertFalse(estado.flags[FLAG_LIGADA_POR_DEFAULT])
        self.assertEqual(self.cache.read().head, self.store.head())

    def test_a_serializacao_preserva_o_TIPO_do_valor(self):
        """`True` e `1` são distintos em Python, e JSON não os confunde — mas a
        volta pode. Uma flag numérica que voltasse booleana degradaria o endpoint
        errado, e o wallboard mostraria o número como estado."""
        current(self.store, DECLARACOES, self.cache)
        lido = self.cache.read().state.flags[FLAG_LIGADA_POR_DEFAULT]
        self.assertIsInstance(lido, bool)

    def test_sobrevive_a_instancia_nova_sobre_a_mesma_chave(self):
        """É a razão de o Redis existir aqui: o processo morre, a projeção não."""
        import redis

        current(self.store, DECLARACOES, self.cache)
        outro = RedisProjectionCache(
            redis.Redis.from_url(_URL, decode_responses=True), chave=self.chave
        )
        self.assertEqual(outro.read().head, self.store.head())


if __name__ == "__main__":
    unittest.main()
