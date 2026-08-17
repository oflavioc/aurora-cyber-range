#!/usr/bin/env python3
"""Sobe o `range-api` com o pack de fixture, para VER a sala — peca 4.

USO
    AURORA_GM_PASSWORD=<credencial local> python scripts/sobe_sala.py
    # e, noutro terminal:
    python scripts/dispara.py A01        # ou o DEMO da peca 7

    Depois abra http://127.0.0.1:8000/sala

O QUE ELE E, E O QUE ELE NAO E
-------------------------------
E o menor processo que monta o exercicio de verdade — pack, clock, store,
engine, cache — e serve a API. **Nao e o container da peca 7**, e nao e o DEMO:
o DEMO e a sequencia exata que `07` fixa, com asserção em cada passo, e roda no
CI. Este script existe para que a fase possa ser VISTA enquanto ela e
construida.

Em memoria, de proposito: `InMemoryEventStore` e `InMemoryProjectionCache`. A
persistencia e da peca 7, e para olhar a sala funcionar ela nao acrescenta nada
— o que a peca 7 acrescenta e o REINICIO, que so faz sentido com o que sobrevive.

`05` §6: bind em `127.0.0.1`, e a porta vem de `AURORA_BIND_*`. Nenhuma porta
publicada, nenhuma interface externa.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

from range_core.api.app import Exercicio, credencial_do_console, montar  # noqa: E402
from range_core.api.tokens import jwt_secret  # noqa: E402
from range_core.clock.exercise_clock import ExerciseClock  # noqa: E402
from range_core.engine.inject_engine import Facilitator, InjectEngine  # noqa: E402
from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack  # noqa: E402
from range_core.events.store import InMemoryEventStore  # noqa: E402
from range_core.state.cache import InMemoryProjectionCache  # noqa: E402

PACK = REPO_ROOT / "tests" / "fixtures" / "pack_minimo"
FLAGS = Path("domains") / "academus" / "flags.yaml"


def monta_exercicio() -> Exercicio:
    contratos = contract_source.read_contracts()
    flags = AdapterFlags.from_document(
        yaml.safe_load((REPO_ROOT / FLAGS).read_text(encoding="utf-8")),
        source=FLAGS.as_posix(),
    )
    pack = load_pack(PACK, contracts=contratos, adapter_flags=flags)
    clock = ExerciseClock(datetime.now().replace(microsecond=0))
    store = InMemoryEventStore(clock)
    return Exercicio(
        engine=InjectEngine(
            pack=pack,
            clock=clock,
            store=store,
            facilitator=Facilitator(user="facilitador", role="control"),
            rollback_reasons=contract_source.rollback_reasons(contratos),
        ),
        cache=InMemoryProjectionCache(),
        declarations=pack.declarations,
        specs=flags.specs,
        textos=pack.textos_para_plateia,
        credencial=credencial_do_console(),
        segredo=jwt_secret(),
    )


def main() -> int:
    host = os.environ.get("AURORA_BIND_HOST", "127.0.0.1")
    porta = int(os.environ.get("AURORA_BIND_PORT", "8000"))
    aplicacao = montar(monta_exercicio())

    print(f"  sala ......... http://{host}:{porta}/sala")
    print(f"  wallboard .... http://{host}:{porta}/wallboard/state")
    print("  console ...... POST /session com a credencial de AURORA_GM_PASSWORD")
    print("\n  Ctrl+C para encerrar.\n")
    uvicorn.run(aplicacao, host=host, port=porta, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
