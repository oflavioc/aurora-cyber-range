#!/usr/bin/env python3
"""DoD 9 da Fase 7 — a reconstrucao do exercicio de 4 h, medida contra 3 s.

O QUE ESTE SCRIPT E, E O QUE ELE NAO E
---------------------------------------
`06` T12: *"Reconstrucao da projecao do zero para o exercicio de 4 h do
`ransomware-universidade` roda em < 3 s, com maquina, data e stack
declaradas"*. A Fase 2 entregou a CURVA (`bench_reconstruction.py`, P2-10) e o
proprio cabecalho dela fixa o limite: a curva prova que o motor aguenta N
eventos, nao que o exercicio de 4 h cabe abaixo de N. **Este script e o
veredito**: ele mede O exercicio, derivado do pack REAL.

A relacao com o bench e de parentesco declarado, nao de reuso: o bench gera
fluxo SINTETICO parametrizado por volume, este deriva o fluxo DO PACK — e cada
um serve a uma pergunta. As formas de medicao (as duas metades, a carga em
lote, o contexto por codigo) sao as mesmas, transcritas com este aviso; se uma
mudar, a outra e o primeiro lugar onde conferir.

A COMPOSICAO DO VOLUME E DECLARADA — registro da fase, §8.2
------------------------------------------------------------
A nota de T13/Fase 9 divide as ordens de grandeza: *"injects sao dezenas,
acoes de participante sao centenas, telemetria pode chegar as centenas de
milhares"* — e telemetria e da Fase 9, medida la por desenho. O fluxo deste
exercicio:

- `exercise_started`, com o pino REAL do pack (`LoadedPack.pin_payload`);
- um `inject_fired` por inject do pack, na ordem do engine
  (`(t_relative_seconds, id)`), com os `effects` reais no payload;
- um `decision_made` por `decision_point`, com a PRIMEIRA opcao — escolha
  deterministica declarada; a medicao nao julga a decisao, conta o evento.
  `capability_gap_declared` fica FORA e a exclusao e declarada: o gap nao
  sobe ao `LoadedPack` (o engine nao precisa dele; quem o emite e o fluxo de
  decisao das fases seguintes), e conta-lo aqui exigiria uma segunda leitura
  do documento — no pior caso sao unidades, dentro do que as 600 acoes ja
  superestimam;
- **600 acoes de participante** (`audit_query_performed`, camada
  `participant_action`, com `actor_id` e `persona` como o contrato exige)
  espalhadas uniformemente nas 4 h. E o topo da ordem que a spec nomeia
  ("centenas"; 2,5 acoes/min), e superestimar volume so endurece o criterio.
  Numero declarado e revisavel, nunca inferido;
- **4 `rollback_performed`** com ancora curta — a forma REALISTA do bench
  (facilitador rebobina pontualmente); a patologica e da curva, nao do
  exercicio.

A PROJECAO E RECONSTRUIDA COM AS `Declarations` REAIS do pack carregado —
`flag_defaults` do adapter, `inject_effects` e `option_effects` do proprio
`load_pack`, com todas as guardas da carga.

NAO RODA NO CI, pelo mesmo motivo do bench: tempo em runner compartilhado
varia com o vizinho. A medicao e deliberada, com o numero transcrito no
registro da fase junto do contexto.

USO:
    AURORA_TEST_DATABASE_URL=... python scripts/medida_do_exercicio_4h.py \\
        scenarios/academus/ransomware-universidade

O banco de medicao e TRUNCADO — nunca aponte para o banco semeado do
exercicio; a variavel e separada de DATABASE_URL exatamente por isso.
"""

from __future__ import annotations

import datetime
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
    AUDIT_QUERY_PERFORMED,
    DECISION_MADE,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_cli import lint as lint_de_cenario  # noqa: E402
from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import LoadedPack, load_pack  # noqa: E402
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
from range_core.state.simulation_state import project  # noqa: E402

#: 2,5 acoes/min x 240 min — o topo de "centenas" (nota de T13). Declarado.
ACOES_DE_PARTICIPANTE = 600
#: A forma realista do bench: o facilitador rebobina pontualmente.
ROLLBACKS = 4
ORCAMENTO_S = 3.0


def _tempo(segundos: int) -> tuple[str, str]:
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    exercise_time = f"T+{horas:02d}:{minutos:02d}:{seg:02d}"
    base = datetime.datetime(2026, 9, 13, 9, 0, 0)
    carimbo = (base + datetime.timedelta(seconds=segundos)).isoformat()
    return exercise_time, carimbo


def _event(
    indice: int,
    event_type: str,
    epoch: int,
    payload: dict,
    inject: str | None,
    segundos: int,
    *,
    camada: str = "facilitation",
    actor: str | None = None,
    persona: str | None = None,
) -> Event:
    exercise_time, carimbo = _tempo(segundos)
    return Event(
        event_id=f"EX4H{indice:021d}",
        event_type=event_type,
        truth_layer=camada,
        producer="medida_do_exercicio_4h",
        exercise_time=exercise_time,
        exercise_timestamp=carimbo,
        wall_timestamp=carimbo + "-03:00",
        clock_multiplier=1.0,
        simulation_epoch=epoch,
        actor_id=actor,
        persona=persona,
        correlation=Correlation(inject_id=inject),
        payload=payload,
    )


def stream_do_pack(pack: LoadedPack) -> list[Event]:
    """O fluxo do exercicio, derivado do pack — a composicao do cabecalho."""
    duracao_s = int(pack.manifest["duration_minutes"]) * 60
    indice = 0

    def proximo(event_type, epoch, payload, inject, segundos, **marcas):
        nonlocal indice
        evento = _event(indice, event_type, epoch, payload, inject, segundos, **marcas)
        indice += 1
        return evento

    # (segundos, ordem-de-desempate, tipo, payload, inject, marcas) — injects
    # e decisoes no relogio do pack, acoes de participante espalhadas.
    agenda: list[tuple[int, int, str, dict, str | None, dict]] = []

    for inject in sorted(pack.injects, key=lambda i: (i.t_relative_seconds, i.id)):
        agenda.append(
            (
                inject.t_relative_seconds,
                0,
                INJECT_FIRED,
                {"effects": dict(inject.effects)},
                inject.id,
                {},
            )
        )
        ponto = inject.decision_point
        if ponto is not None and ponto.options:
            opcao = ponto.options[0]
            agenda.append(
                (
                    inject.t_relative_seconds + 60,
                    1,
                    DECISION_MADE,
                    # A forma que o fold exige (`_writes_of`): `option_id` no
                    # payload e o inject em `correlation` — os effects da opcao
                    # vem das Declarations, nunca do evento.
                    {"decision_point_id": ponto.id, "option_id": opcao.id},
                    inject.id,
                    {},
                )
            )

    personas = list(pack.manifest.get("personas") or ["ti"])
    for i in range(ACOES_DE_PARTICIPANTE):
        t = round((i + 1) * duracao_s / (ACOES_DE_PARTICIPANTE + 1))
        agenda.append(
            (
                t,
                2,
                AUDIT_QUERY_PERFORMED,
                {"query": "periodo", "n": i},
                None,
                {
                    "camada": "participant_action",
                    "actor": f"participante-{i % 7:02d}",
                    "persona": personas[i % len(personas)],
                },
            )
        )

    agenda.sort(key=lambda linha: (linha[0], linha[1]))

    eventos = [proximo(EXERCISE_STARTED, 0, pack.pin_payload(), None, 0)]
    epoch = 0
    posicoes_de_rollback = {
        round((k + 1) * len(agenda) / (ROLLBACKS + 1)) for k in range(ROLLBACKS)
    }
    for n, (segundos, _, event_type, payload, inject, marcas) in enumerate(agenda):
        eventos.append(proximo(event_type, epoch, payload, inject, segundos, **marcas))
        if n in posicoes_de_rollback:
            ancora = eventos[-2].event_id
            eventos.append(
                proximo(
                    ROLLBACK_PERFORMED, epoch, {"to_event_id": ancora}, None, segundos
                )
            )
            epoch += 1
    return eventos


def carrega(dsn: str, eventos: list[Event]) -> None:
    """Carga em lote com a cadeia em Python — a forma do bench, mesmo motivo:
    o que se mede e RECONSTRUCAO, nao escrita."""
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


def cronometra(funcao):
    inicio = time.perf_counter()
    resultado = funcao()
    return time.perf_counter() - inicio, resultado


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if len(argumentos) != 1:
        print(
            "uso: AURORA_TEST_DATABASE_URL=... python "
            "scripts/medida_do_exercicio_4h.py <dir-do-pack>",
            file=sys.stderr,
        )
        return 2
    url = os.environ.get("AURORA_TEST_DATABASE_URL")
    if not url:
        print("AURORA_TEST_DATABASE_URL nao definida.", file=sys.stderr)
        return 1
    dsn = normalize_dsn(url)

    pack_dir = Path(argumentos[0])
    raiz = Path.cwd()
    contracts = contract_source.read_contracts()
    flags = lint_de_cenario.flags_do_pack(pack_dir, raiz)
    pack = load_pack(pack_dir, contracts=contracts, adapter_flags=flags)

    eventos = stream_do_pack(pack)
    carrega(dsn, eventos)

    store = PostgresEventStore(None, url)  # type: ignore[arg-type]
    t_read, lidos = cronometra(store.read_all)

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT sequence, previous_hash, row_hash FROM {TABLE} ORDER BY sequence"
        )
        meta = cur.fetchall()
        cur.execute("SELECT version()")
        versao_pg = cur.fetchone()[0].split(",")[0]
        cur.execute("SELECT version_num FROM alembic_version")
        revisao = cur.fetchone()[0]
    linhas = [(m[0], m[1], m[2], e) for m, e in zip(meta, lidos)]
    t_cadeia, _ = cronometra(lambda: verify_chain(linhas))

    t_project, _ = cronometra(lambda: project(lidos, pack.declarations))
    total_s = t_read + t_project

    decisoes = sum(1 for e in eventos if e.event_type == DECISION_MADE)
    print("DoD 9 da Fase 7 — o exercicio de 4 h do ransomware-universidade")
    print(f"  data:    {datetime.date.today().isoformat()}")
    print(f"  maquina: {platform.platform()} | python {platform.python_version()}")
    print(f"  stack:   {versao_pg} | psycopg {psycopg.__version__} | migration {revisao}")
    print(f"  pack:    {pack.pack_id} | content_hash {pack.content_hash[:24]}…")
    print(
        f"  fluxo:   {len(eventos)} eventos = 1 started + "
        f"{len(pack.injects)} inject_fired + {decisoes} decision_made + "
        f"{ACOES_DE_PARTICIPANTE} acoes de participante + {ROLLBACKS} rollbacks"
    )
    print(
        f"  medida:  read_all {t_read:.3f}s (cadeia {t_cadeia:.3f}s, "
        f"consulta {t_read - t_cadeia:.3f}s) + project {t_project:.3f}s "
        f"= {total_s:.3f}s"
    )
    veredito = "PASSA" if total_s < ORCAMENTO_S else "FALHA"
    print(f"  item 9:  {veredito} — {total_s:.3f}s contra o orcamento de {ORCAMENTO_S:.0f} s")
    return 0 if total_s < ORCAMENTO_S else 1


if __name__ == "__main__":
    raise SystemExit(main())
