"""Event store em Postgres — o backend que sobrevive ao reinicio.

`06_ACCEPTANCE_TESTS.md` T3: "reinicio do processo restaura a projecao corrente
sem intervencao". `InMemoryEventStore` perde tudo ao morrer; este nao.

O QUE ELE IMPLEMENTA, E O QUE ELE HERDA
---------------------------------------
So `_persist` e `_stored`. O carimbo — id, quatro marcas, epoch — vive no
`append` de `EventStore` e vale para todo backend. Se cada implementacao
carimbasse por conta propria, a regra divergiria na segunda, que e esta.

APPEND-ONLY AQUI E DETECCAO, NAO PREVENCAO
-------------------------------------------
Nao ha `REVOKE`, role `INSERT`-only nem trigger: isso e `02` §4 e `05` §7,
entregue na Fase 5. Ate la, quem tiver a connection string reescreve historia — e
o que esta peca garante e que a reescrita **nao passe em silencio**. Cada leitura
verifica a cadeia; adulteracao vira `ChainBroken` com a posicao.

Os dois limites — truncamento da cauda e reescrita completa por quem tem o
codigo — estao declarados em `range_core.events.integrity`.

CONCORRENCIA: UM ESCRITOR
-------------------------
`_persist` toma `LOCK TABLE ... IN EXCLUSIVE MODE` antes de ler o topo da cadeia,
porque calcular `sequence` e `previous_hash` a partir da ultima linha e depois
inserir e leitura-e-escrita: sem o lock, dois appends concorrentes leriam o mesmo
topo e produziriam duas linhas com a mesma sequencia.

O `EXCLUSIVE` permite leitura concorrente e bloqueia escrita, que e exatamente a
forma do problema. O engine da Fase 2 e escritor unico; o lock existe para que a
propriedade nao dependa disso.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import psycopg

from range_core.clock.port import ExerciseClockPort
from range_core.events.envelope import Correlation, Event
from range_core.events.integrity import (
    FIRST_SEQUENCE,
    GENESIS_HASH,
    row_hash,
    verify_chain,
)
from range_core.events.store import EventStore, StreamHead

TABLE = "event_store"

_COLUMNS = (
    "sequence, event_id, event_type, truth_layer, producer, exercise_time, "
    "exercise_timestamp, wall_timestamp, clock_multiplier, simulation_epoch, "
    "actor_id, persona, correlation, payload, previous_hash, row_hash"
)


def normalize_dsn(url: str) -> str:
    """`postgresql+psycopg://...` -> `postgresql://...`.

    `.env.example` traz a URL no dialeto do SQLAlchemy, que e quem o Alembic
    consome. `psycopg` fala DSN puro. Converter aqui evita duas variaveis de
    ambiente para o mesmo banco, que e a forma de as duas divergirem.
    """
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


class PostgresEventStore(EventStore):
    def __init__(self, clock: ExerciseClockPort, dsn: str) -> None:
        super().__init__(clock)
        self._dsn = normalize_dsn(dsn)

    def _persist(self, event: Event) -> None:
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(f"LOCK TABLE {TABLE} IN EXCLUSIVE MODE")
            cur.execute(f"SELECT sequence, row_hash FROM {TABLE} ORDER BY sequence DESC LIMIT 1")
            topo = cur.fetchone()

            if topo is None:
                sequencia, anterior = FIRST_SEQUENCE, GENESIS_HASH
            else:
                sequencia, anterior = topo[0] + 1, topo[1]

            cur.execute(
                f"INSERT INTO {TABLE} ({_COLUMNS}) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    sequencia,
                    event.event_id,
                    event.event_type,
                    event.truth_layer,
                    event.producer,
                    event.exercise_time,
                    event.exercise_timestamp,
                    event.wall_timestamp,
                    event.clock_multiplier,
                    event.simulation_epoch,
                    event.actor_id,
                    event.persona,
                    json.dumps(
                        {
                            "scenario_id": event.correlation.scenario_id,
                            "inject_id": event.correlation.inject_id,
                            "causation_id": event.correlation.causation_id,
                            "fact_id": event.correlation.fact_id,
                        }
                    ),
                    json.dumps(dict(event.payload)),
                    anterior,
                    row_hash(event, anterior),
                ),
            )

    def _head(self) -> StreamHead:
        """`ORDER BY sequence DESC LIMIT 1` — indice, e nao varredura.

        `sequence` e chave primaria e contigua por construcao (§3.5 do registro
        da Fase 2), entao o maior valor E a contagem. Nao ha `COUNT(*)`, que
        `01` §7 proibe em rota de tempo real e que aqui seria varredura da tabela
        inteira para responder o que o indice ja sabe.

        A CADEIA NAO E VERIFICADA AQUI, e a assimetria com `_stored` e
        deliberada: verificar exigiria ler tudo, que e o custo que este metodo
        existe para nao pagar. Quem verifica e `_stored`, no caminho que de fato
        reconstroi — entao um store adulterado e pego na reconstrucao, nao na
        conferencia de validade do cache.
        """
        with psycopg.connect(self._dsn) as conexao:
            with conexao.cursor() as cur:
                cur.execute(
                    f"SELECT sequence, event_id FROM {TABLE} "
                    "ORDER BY sequence DESC LIMIT 1"
                )
                linha = cur.fetchone()
        if linha is None:
            return StreamHead(count=0, last_event_id=None)
        return StreamHead(count=int(linha[0]), last_event_id=str(linha[1]))

    def _stored(self) -> Sequence[Event]:
        """Tudo, na ordem da sequencia, COM A CADEIA VERIFICADA.

        A verificacao e incondicional, e nao ha como desliga-la: `read_all()` nao
        tem parametro, por `01` §4.1. Um `verify=False` seria a porta que a
        proxima pressa usaria, e store adulterado que responde produz projecao
        plausivel e falsa.
        """
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {_COLUMNS} FROM {TABLE} ORDER BY sequence")
            linhas = cur.fetchall()

        eventos: list[Event] = []
        para_verificar: list[tuple[int, str, str, Event]] = []

        for linha in linhas:
            correlation = linha[12] or {}
            event = Event(
                event_id=linha[1],
                event_type=linha[2],
                truth_layer=linha[3],
                producer=linha[4],
                exercise_time=linha[5],
                exercise_timestamp=linha[6],
                wall_timestamp=linha[7],
                clock_multiplier=linha[8],
                simulation_epoch=linha[9],
                actor_id=linha[10],
                persona=linha[11],
                correlation=Correlation(
                    scenario_id=correlation.get("scenario_id"),
                    inject_id=correlation.get("inject_id"),
                    causation_id=correlation.get("causation_id"),
                    fact_id=correlation.get("fact_id"),
                ),
                payload=linha[13] or {},
            )
            eventos.append(event)
            para_verificar.append((linha[0], linha[14], linha[15], event))

        verify_chain(para_verificar)
        return tuple(eventos)
