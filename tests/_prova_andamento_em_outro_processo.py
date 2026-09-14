#!/usr/bin/env python3
"""Calcula o conjunto de sessoes derrubadas no minuto — NUM PROCESSO NOVO.

**Nao e teste**, dai o `_`: `unittest discover -p "test_*.py"` nao o coleta.

POR QUE UM PROCESSO DE VERDADE, e nao uma segunda chamada
-----------------------------------------------------------
A propriedade *"estavel no reinicio"* e sobre **processos diferentes**, e ha um
modo de falha que so aparece assim: `hash()` de string em Python e salgado por
`PYTHONHASHSEED` e muda a cada interpretador. Uma cadencia escrita com ele seria
perfeitamente estavel dentro de um processo e derrubaria OUTRO conjunto de
sessoes a cada boot do container — verde na suite, errado na sala. O filho nasce
sem `PYTHONHASHSEED` fixado, entao a salga dele e outra: e a condicao exata em
que a derivacao errada se separa da certa. E o mesmo desenho de
`_queda_de_sessao_em_outro_processo.py`, aplicado a cadencia por minuto.

USO
    python tests/_prova_andamento_em_outro_processo.py \
        <seed> <rota> <flag> <taxa> <minuto> <sujeito>...
"""

from __future__ import annotations

import json
import sys

from domains.academus.api.prova_andamento import derrubadas


def main() -> int:
    seed = int(sys.argv[1])
    rota, flag = sys.argv[2], sys.argv[3]
    taxa, minuto = float(sys.argv[4]), int(sys.argv[5])
    sujeitos = sys.argv[6:]
    caidos = derrubadas(seed, rota, flag, sujeitos, taxa, minuto)
    print(json.dumps(sorted(caidos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
