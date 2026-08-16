"""A projecao materializada de `simulation_state`, e quem tem direito de escreve-la.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4 (*"Simulation State — flags do contrato — Redis
(projecao) + event store"*) e §4.1 (*"toda projecao e reconstruivel do zero"*);
`00_MASTER_SPEC.md` §5.5. A medicao que decidiu esta peca esta na §3.8 do
registro da Fase 2.

POR QUE O CACHE EXISTE, COM NUMERO E NAO COM SUPOSICAO
-------------------------------------------------------
Reconstruir do zero custa **2,874 s em 150 mil eventos**, dos quais 64% em
consulta e hidratacao e 3% no fold. Por request e inviavel, e o numero esta
medido — nao estimado.

O QUE ESTA PORTA NAO TEM, E E O PONTO
--------------------------------------
**Nao ha metodo que aceite um `SimulationState`.**

`refresh` recebe o FLUXO e as DECLARACOES, e folda aqui dentro. Um chamador que
quisesse gravar um estado montado a mao nao tem por onde: nao e que seja
proibido, e que e **inexprimivel** — a mesma forma que fez `read_all()` nao ter
parametro na Fase 2.

A alternativa obvia — `write(state)` com verificacao de que o estado veio do fold
— nao funciona: `SimulationState` e um dataclass, e qualquer um constroi um. A
procedencia nao esta no valor, esta em **quem calculou**. Entao a porta calcula.

`scripts/check_fold_authority.py` fecha a outra metade: `SimulationState` e
construido em exatamente um lugar — dentro de `project`.

AS DUAS DECISOES DE COMPORTAMENTO, escritas como propriedade
-------------------------------------------------------------
**CACHE FRIO — a API nunca responde a partir de defaults.**

Defaults NAO sao fallback. Eles sao o resultado correto de foldar um fluxo
**vazio**, e so isso: com `exercise_started` no store, responder defaults
inverteria `academus.federated_session_active`, cujo default e `true` — o caso
concreto que motivou o estado TOTAL do fold (§1.6 do registro da Fase 2).

Entao cache frio nao tem resposta rapida: tem reconstrucao. O custo e de PARTIDA,
pago uma vez, e nao por request — e o que o cache elimina depois e o fold, nao a
consulta de cabeca.

**DIVERGENCIA — quem detecta e QUANDO, senao "o store e autoridade" e frase.**

A cada leitura, e por `StreamHead`: quantos eventos ha e qual e o ultimo. E
comparacao da IDENTIDADE DA ENTRADA, nao do estado — uma consulta de indice, nao
um fold. Divergiu, reconstroi.

Comparar o estado inteiro a cada request seria refazer o fold, que e o que o
cache existe para evitar; nao comparar nada faria da autoridade do store uma
frase. A cabeca e o meio-termo que nao e concessao: ela e exatamente o que muda
quando o fluxo muda.

O LIMITE, DECLARADO
-------------------
Duas leituras concorrentes num cache frio reconstroem **duas vezes**. Nao ha
single-flight aqui, e havera quando houver concorrencia de verdade — a API da
Fase 3 e o primeiro lugar onde isso deixa de ser hipotese. Fica como pendencia,
com dono, em vez de virar comentario.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from range_core.events.envelope import Event
from range_core.events.store import EventStore, StreamHead
from range_core.state.simulation_state import (
    Declarations,
    SimulationState,
    project,
)


@dataclass(frozen=True, slots=True)
class CachedProjection:
    """O estado e a cabeca do fluxo que o produziu, juntos e inseparaveis.

    JUNTOS E O PONTO: um estado sem a cabeca de origem nao pode ser validado, e
    validar e a unica coisa que impede o cache de servir um mundo que nao existe
    mais.
    """

    state: SimulationState
    head: StreamHead


class SimulationStateCache(ABC):
    """A projecao materializada. **Nenhum metodo aceita `SimulationState`.**

    `refresh` recebe o fluxo e folda; os backends implementam so serializacao —
    `_load` e `_store`, privados. Assim a regra de "quem calcula" e escrita UMA
    VEZ e vale para todo backend, em vez de ser reimplementada por cada um.
    """

    def refresh(
        self,
        events: Sequence[Event],
        declarations: Declarations,
        head: StreamHead,
    ) -> SimulationState:
        """Folda o fluxo, grava, devolve. **O unico caminho de escrita.**

        `head` vem do store e acompanha o estado: e o que torna a validacao
        possivel depois. Passa-lo em vez de derivar do `events` e deliberado —
        quem sabe a identidade do fluxo e o store, e derivar aqui seria uma
        segunda opiniao sobre um fato que ja tem dono.
        """
        estado = project(events, declarations)
        self._store(CachedProjection(state=estado, head=head))
        return estado

    def read(self) -> CachedProjection | None:
        """A projecao gravada, ou `None` se o cache esta frio.

        `None` NAO significa "use os defaults". Significa "nao ha projecao" — e
        quem decide o que fazer com isso e `current`, que reconstroi.
        """
        return self._load()

    @abstractmethod
    def _load(self) -> CachedProjection | None:
        """Backend-especifico."""

    @abstractmethod
    def _store(self, projecao: CachedProjection) -> None:
        """Backend-especifico."""


def current(
    store: EventStore,
    declarations: Declarations,
    cache: SimulationStateCache,
) -> SimulationState:
    """O estado corrente — do cache quando ele vale, do fold quando nao vale.

    E AQUI QUE AS DUAS DECISOES VIRAM UMA FUNCAO, e por isso ela e curta: cache
    frio e divergencia sao **o mesmo caso** — a projecao gravada nao corresponde
    ao fluxo —, e tratar os dois com um caminho so e o que impede que um deles
    ganhe um atalho.

    A ordem importa: a cabeca e lida ANTES da projecao. Lida depois, uma escrita
    que caisse no meio faria a validacao comparar a projecao nova com a cabeca
    velha e concluir que vale.
    """
    head = store.head()
    cached = cache.read()

    if cached is not None and cached.head == head:
        return cached.state

    return cache.refresh(store.read_all(), declarations, head)


class InMemoryProjectionCache(SimulationStateCache):
    """Cache em memoria. NAO e duplo de teste — e o segundo backend.

    A distincao vale: um duplo reimplementaria a semantica do Redis e testaria a
    si mesmo. Este implementa a MESMA porta com outra persistencia, exatamente
    como `InMemoryEventStore` faz com o store — e serve ao processo unico, que e
    o caso do DEMO e do engine sem Redis.

    Nao sobrevive ao processo, e e por isso que a Fase 4 exige o outro.
    """

    def __init__(self) -> None:
        self._projecao: CachedProjection | None = None

    def _load(self) -> CachedProjection | None:
        return self._projecao

    def _store(self, projecao: CachedProjection) -> None:
        self._projecao = projecao


class RedisProjectionCache(SimulationStateCache):
    """Cache em Redis — o que `01` §4 nomeia como persistencia da projecao.

    SERIALIZACAO EM JSON, com a cabeca junto. `FlagValue` e `bool | int | float |
    str`, que JSON carrega sem perda — exceto por um caso que o codigo trata
    explicitamente: `True` e `1` sao distintos em Python e iguais em JSON so se
    alguem os confundir na volta. `json` preserva o tipo, e o teste afirma isso.

    NAO HA TTL. Projecao com validade seria projecao que expira sozinha e volta
    fria sem que nada tenha mudado — custo de reconstrucao sem causa. O que a
    invalida e a cabeca do fluxo mudar, e isso `current` ja confere.
    """

    def __init__(self, client, chave: str = "aurora:simulation_state") -> None:
        self._client = client
        self._chave = chave

    def _load(self) -> CachedProjection | None:
        bruto = self._client.get(self._chave)
        if bruto is None:
            return None
        documento = json.loads(bruto)
        return CachedProjection(
            state=_estado_de(documento["state"]),
            head=StreamHead(
                count=documento["head"]["count"],
                last_event_id=documento["head"]["last_event_id"],
            ),
        )

    def _store(self, projecao: CachedProjection) -> None:
        self._client.set(
            self._chave,
            json.dumps(
                {
                    "state": {
                        "flags": dict(projecao.state.flags),
                        "simulation_epoch": projecao.state.simulation_epoch,
                    },
                    "head": {
                        "count": projecao.head.count,
                        "last_event_id": projecao.head.last_event_id,
                    },
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )


def _estado_de(documento: dict) -> SimulationState:
    """Reidrata o estado lido do Redis.

    ESTE E O UNICO LUGAR ALEM DO FOLD QUE CONSTROI `SimulationState`, e
    `scripts/check_fold_authority.py` o declara nominalmente — nao como excecao
    tolerada, mas como o que ele e: **desserializacao do que o fold ja produziu**,
    e nao calculo novo.

    A diferenca e verificavel e nao e de intencao: aqui nao ha `Declarations`, nao
    ha fluxo e nao ha regra de estado — ha `json.loads` e dois campos. Uma
    reimplementacao do fold precisaria dos tres, e nenhum deles esta ao alcance.
    """
    return SimulationState(
        flags=documento["flags"],
        simulation_epoch=documento["simulation_epoch"],
    )
