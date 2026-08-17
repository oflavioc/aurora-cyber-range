#!/usr/bin/env python3
"""Le o event store e deriva os cinco valores — NUM PROCESSO NOVO.

Nao e teste, e por isso o nome comeca com `_`: `unittest discover` procura
`test*.py`, entao este arquivo nao e coletado. Quem o executa e
`tests/test_restauracao.py`, por `subprocess`.

POR QUE UM PROCESSO DE VERDADE
-------------------------------
Restaurar montando objeto na mesma sessao prova a aritmetica e mais nada: as
variaveis ainda estao vivas, e um valor que viesse da memoria em vez do fluxo
passaria. Aqui o interpretador e outro, e a UNICA coisa compartilhada e a tabela
de eventos do Postgres — que e exatamente o que a DoD chama de "a partir do
event store".

O QUE ELE AINDA NAO E: um container. Ver `docs/progress/fase_4.md` §4.4, onde a
divisao entre o que a peca 3 prova e o que so a peca 7 prova esta declarada.

USO
    python tests/_restaura_em_outro_processo.py <instante-de-parede-do-reinicio>
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from range_core.clock.exercise_clock import ExerciseClock
from range_core.clock.restauracao import derivar
from range_core.events.postgres_store import PostgresEventStore


def main() -> int:
    agora = float(sys.argv[1])
    url = os.environ["AURORA_TEST_DATABASE_URL"]

    # O clock e exigido pelo construtor porque o store CARIMBA no append. Este
    # processo so le, entao o valor dele nao entra em nada — e o T0 restaurado
    # sai do fluxo, e nao daqui. Se saisse daqui, o teste do T0 passaria com
    # qualquer coisa.
    store = PostgresEventStore(ExerciseClock(datetime(1970, 1, 1)), url)

    valores = derivar(store.read_all(), now=lambda: agora)
    print(
        json.dumps(
            {
                "t_zero": valores.t_zero.isoformat(),
                "elapsed_seconds": valores.elapsed_seconds,
                "multiplier": valores.multiplier,
                "paused": valores.paused,
                "epoch_started_at": valores.epoch_started_at,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
