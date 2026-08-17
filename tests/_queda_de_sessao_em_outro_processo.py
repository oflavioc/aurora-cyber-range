#!/usr/bin/env python3
"""Calcula quem cai — NUM PROCESSO NOVO. **Nao e teste**, dai o `_`.

POR QUE UM PROCESSO DE VERDADE, e nao uma segunda chamada
-----------------------------------------------------------
A propriedade *"estavel no reinicio"* da D9 e sobre **processos diferentes**, e
ha um modo de falha que so aparece assim: `hash()` de string em Python e salgado
por `PYTHONHASHSEED` e muda a cada interpretador. Uma derivacao escrita com ele
seria perfeitamente estavel dentro de um processo e daria um conjunto de sessoes
diferente a cada boot do container — verde na suite, errado na sala.

`range-core/determinism.py` ja documenta essa armadilha para o dataset. Aqui ela
tem consequencia diferente e igualmente invisivel: o facilitador reinicia o
engine e o exercicio continua, mas quem estava fora do ar passa a ser outro
conjunto de participantes.

O interpretador filho nasce **sem** `PYTHONHASHSEED` fixado, entao a salga dele
e outra — que e exatamente a condicao em que a derivacao errada se separa da
certa.

USO
    python tests/_queda_de_sessao_em_outro_processo.py <seed> <rota> <flag> <taxa> <sujeito>...
"""

from __future__ import annotations

import json
import sys

from domains.academus.api.degradacao import cai


def main() -> int:
    seed, rota, flag, taxa = int(sys.argv[1]), sys.argv[2], sys.argv[3], float(sys.argv[4])
    sujeitos = sys.argv[5:]
    print(json.dumps([s for s in sujeitos if cai(seed, rota, flag, s, taxa)]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
