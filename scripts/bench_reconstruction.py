#!/usr/bin/env python3
"""P2-10 — mede o item 8 da DoD: reconstrucao completa em menos de 3 s.

POR QUE ISTO EXISTE, E POR QUE NAO E GATE
------------------------------------------
`07` Fase 2, item 8, e `01` §7: "reconstrucao de projecao a partir do event store
deve completar em < 3 s para exercicio de 4 h". A P2-10 fixou que a medicao vem
ANTES de construir em cima do fold — se ela obrigar a trocar a estrategia de
recomputacao, a troca mexe numa decisao que ja tem seis propriedades e oito
mutacoes calibradas sobre ela.

NAO roda no CI. Tempo em runner compartilhado varia com o vizinho, e gate que
falha por vizinho ensina a reexecutar ate passar — o mesmo argumento que tirou o
`sleep` dos testes do clock. Aqui a medicao e deliberada, com numero registrado
no `docs/progress/fase_2.md` e a maquina declarada junto.

DUAS FORMAS, PORQUE O CUSTO NAO E LINEAR NO NUMERO DE EVENTOS
---------------------------------------------------------------
A mascara de sobrevivencia e laco POR INTERVALO ABANDONADO: `R` rollbacks com
intervalos longos custam diferente de `N` eventos sem rollback nenhum.

- **realista** — 4 h com poucos rollbacks, intervalos curtos;
- **patologico** — muitos rollbacks TODOS ancorados no `exercise_started`, o que
  faz cada um marcar o prefixo inteiro. E `O(R x N)`, e e alcancavel: e o
  facilitador rebobinando repetidamente para o inicio.

Medir so a primeira responderia a pergunta facil.

DUAS METADES, PORQUE AS DECISOES SAO DIFERENTES
------------------------------------------------
O item 8 diz "a partir do store", e hoje isso inclui verificar o hash de cada
evento a cada leitura. Se o orcamento apertar, trocar a recomputacao do fold e
trocar a politica de verificacao sao decisoes muito diferentes — entao a medicao
separa `read_all` (consulta + hidratacao + cadeia) de `project` (o fold), e
dentro da primeira separa a cadeia do resto.

A ESCRITA E EM LOTE, E DE PROPOSITO
-----------------------------------
As linhas sao inseridas com a cadeia calculada em Python e um `executemany`, em
vez de `append` por evento. O que se mede aqui e RECONSTRUCAO, nao escrita —
`append` abre conexao por chamada, e o custo dele apareceria como se fosse do
item 8. Fica a nota: para carga real, `append` merece revisao propria.

USO:
    AURORA_TEST_DATABASE_URL=... python scripts/bench_reconstruction.py
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

import psycopg  # noqa: E402

from contracts.generated.events import (  # noqa: E402
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.events.envelope import Correlation, Event  # noqa: E402
from range_core.events.integrity import (  # noqa: E402
    FIRST_SEQUENCE,
    GENESIS_HASH,
    row_hash,
    verify_chain,
)
from range_core.events.postgres_store import (  # noqa: E402
    TABLE,
    PostgresEventStore,
    normalize_dsn,
)
from range_core.state.simulation_state import Declarations, project  # noqa: E402

FLAG = "fixture.written_flag"
PACK = {"pack_id": "bench", "schema_version": 2, "hash": "sha256:bench", "canon": "v1"}


def _event(indice: int, event_type: str, epoch: int, payload: dict, inject: str | None) -> Event:
    return Event(
        event_id=f"BENCH{indice:020d}",
        event_type=event_type,
        truth_layer="facilitation",
        producer="bench",
        exercise_time="T+00:00:00",
        exercise_timestamp="2026-08-13T09:00:00",
        wall_timestamp="2026-08-13T09:00:00-03:00",
        clock_multiplier=1.0,
        simulation_epoch=epoch,
        correlation=Correlation(inject_id=inject),
        payload=payload,
    )


def stream(total: int, rollbacks: int, *, ancorado_no_inicio: bool) -> list[Event]:
    """`total` eventos com `rollbacks` cortes.

    `ancorado_no_inicio` produz o caso patologico: todo rollback ancora no
    `exercise_started`, entao cada um marca o prefixo inteiro.
    """
    eventos = [
        _event(
            0,
            EXERCISE_STARTED,
            0,
            {
                "pack_id": PACK["pack_id"],
                "pack_schema_version": PACK["schema_version"],
                "pack_content_hash": PACK["hash"],
                "pack_canonicalization": PACK["canon"],
            },
            None,
        )
    ]
    posicoes = {round(i * total / (rollbacks + 1)) for i in range(1, rollbacks + 1)}
    epoch = 0
    ancora_anterior = "BENCH" + "0" * 20

    for i in range(1, total):
        if i in posicoes:
            ancora = ancora_anterior if ancorado_no_inicio else eventos[-2].event_id
            eventos.append(_event(i, ROLLBACK_PERFORMED, epoch, {"to_event_id": ancora}, None))
            epoch += 1
            if not ancorado_no_inicio:
                ancora_anterior = eventos[-1].event_id
        else:
            eventos.append(_event(i, INJECT_FIRED, epoch, {}, "A01"))
    return eventos


def declarations() -> Declarations:
    return Declarations(
        pack_id=PACK["pack_id"],
        schema_version=PACK["schema_version"],
        content_hash=PACK["hash"],
        canonicalization=PACK["canon"],
        flag_defaults={FLAG: False},
        inject_effects={"A01": {FLAG: True}},
        option_effects={},
    )


def carrega(dsn: str, eventos: list[Event]) -> None:
    linhas, anterior, sequencia = [], GENESIS_HASH, FIRST_SEQUENCE
    for e in eventos:
        atual = row_hash(e, anterior)
        linhas.append(
            (
                sequencia, e.event_id, e.event_type, e.truth_layer, e.producer,
                e.exercise_time, e.exercise_timestamp, e.wall_timestamp,
                e.clock_multiplier, e.simulation_epoch, e.actor_id, e.persona,
                json.dumps({"scenario_id": None, "inject_id": e.correlation.inject_id,
                            "causation_id": None, "fact_id": None}),
                json.dumps(dict(e.payload)), anterior, atual,
            )
        )
        anterior, sequencia = atual, sequencia + 1

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f"TRUNCATE {TABLE}")
        cur.executemany(
            f"INSERT INTO {TABLE} VALUES ({', '.join(['%s'] * 16)})", linhas
        )


def cronometra(rotulo: str, funcao):
    inicio = time.perf_counter()
    resultado = funcao()
    return time.perf_counter() - inicio, resultado


def main() -> int:
    url = os.environ.get("AURORA_TEST_DATABASE_URL")
    if not url:
        print("AURORA_TEST_DATABASE_URL nao definida.", file=sys.stderr)
        return 1
    dsn = normalize_dsn(url)

    # O NUMERO SO VALE COM O CONTEXTO. Ele e medido contra uma versao de
    # Postgres, de driver e de schema; daqui a tres fases, "2,874 s em 150 mil"
    # sozinho e a secao 1.6 esperando acontecer — afirmacao que era verdadeira
    # quando escrita. E medicao e o tipo de coisa que ninguem repete antes de
    # citar.
    import datetime

    import psycopg as _psycopg

    with psycopg.connect(dsn) as _c, _c.cursor() as _cur:
        _cur.execute("SELECT version()")
        versao_pg = _cur.fetchone()[0].split(",")[0]
        _cur.execute("SELECT version_num FROM alembic_version")
        revisao = _cur.fetchone()[0]

    print(f"data:    {datetime.date.today().isoformat()}")
    print(f"maquina: {platform.platform()} | python {platform.python_version()}")
    print(f"stack:   {versao_pg} | psycopg {_psycopg.__version__} | migration {revisao}")
    print(f"{'forma':<12} {'eventos':>8} {'rb':>5} {'read_all':>10} {'cadeia':>9} "
          f"{'consulta':>9} {'project':>9} {'TOTAL':>8}")
    print("-" * 76)

    pior_total = 0.0
    for forma, rollbacks, ancorado in (("realista", 4, False), ("patologico", 100, True)):
        for total in (1_000, 5_000, 20_000, 50_000):
            eventos = stream(total, rollbacks, ancorado_no_inicio=ancorado)
            carrega(dsn, eventos)
            store = PostgresEventStore(None, url)  # type: ignore[arg-type]

            t_read, lidos = cronometra("read_all", store.read_all)

            with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                cur.execute(f"SELECT sequence, previous_hash, row_hash FROM {TABLE} ORDER BY sequence")
                meta = cur.fetchall()
            linhas = [(m[0], m[1], m[2], e) for m, e in zip(meta, lidos)]
            t_cadeia, _ = cronometra("cadeia", lambda: verify_chain(linhas))

            t_project, _ = cronometra("project", lambda: project(lidos, declarations()))
            total_s = t_read + t_project
            pior_total = max(pior_total, total_s)

            print(f"{forma:<12} {total:>8} {rollbacks:>5} {t_read:>9.3f}s {t_cadeia:>8.3f}s "
                  f"{t_read - t_cadeia:>8.3f}s {t_project:>8.3f}s {total_s:>7.3f}s")

    print("-" * 76)
    print(f"pior caso medido: {pior_total:.3f}s contra o orcamento de 3 s do item 8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
