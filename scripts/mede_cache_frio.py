#!/usr/bin/env python3
"""Quantas reconstrucoes N leituras simultaneas produzem num cache frio — P3-2.

A ORDEM E MEDIR, DEPOIS ESCOLHER — a D11
------------------------------------------
A P3-2 diz que duas leituras concorrentes sobre cache frio reconstroem duas
vezes, e que cada reconstrucao custa o que a §3.8 da Fase 2 mediu: **2,874 s em
150 mil eventos**. A tentacao e escrever um single-flight e seguir em frente.

Este projeto ja pagou duas vezes por mecanismo sem consumidor, e a pendencia
tinha sido datada por PROXY — *"quando o FastAPI chegar"* — em vez de pela
condicao que ela descreve. A condicao e **o primeiro processo que serve
requisicoes concorrentes**, e ele e o container da peca 7. Entao: medir.

COMO A CONTAGEM E FEITA, E POR QUE ELA E DIRETA
------------------------------------------------
Nao por cronometro: com o `pack_minimo` o fluxo tem poucos eventos e uma
reconstrucao custa microssegundos — o relogio nao distinguiria nada, e a
pendencia nao e sobre ESTE volume.

A contagem e do proprio Redis. Cada reconstrucao **escreve** a projecao, entao o
numero de `SET` na chave e o numero de reconstrucoes:

    CONFIG RESETSTAT   zera os contadores
    DEL <chave>        deixa o cache frio
    N leituras         simultaneas, em threads
    cmdstat_set        quantas escritas aconteceram

Um `SET` para N leituras significa que alguma coisa serializa. N `SET` para N
leituras e a pendencia acontecendo, com numero.

USO
    docker compose up -d
    python scripts/mede_cache_frio.py [N]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RANGE = os.environ.get("AURORA_DEMO_RANGE_URL", "http://127.0.0.1:8000")
REDIS = os.environ.get("AURORA_REDIS_CONTAINER", "aurora-redis")
CHAVE = os.environ.get("AURORA_REDIS_KEY", "aurora:simulation_state")

LEITORES = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def _redis(*argumentos: str) -> str:
    return subprocess.run(
        ["docker", "exec", REDIS, "redis-cli", *argumentos],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _escritas() -> int:
    for linha in _redis("INFO", "commandstats").splitlines():
        if linha.startswith("cmdstat_set:"):
            for parte in linha.split(":", 1)[1].split(","):
                if parte.startswith("calls="):
                    return int(parte.removeprefix("calls="))
    return 0


def _le() -> int:
    with urllib.request.urlopen(f"{RANGE}/wallboard/state", timeout=30) as resposta:
        return len(resposta.read())


def mede(leitores: int) -> tuple[int, int, float]:
    _redis("CONFIG", "RESETSTAT")
    _redis("DEL", CHAVE)
    marca = time.monotonic()
    with ThreadPoolExecutor(max_workers=leitores) as piscina:
        tamanhos = list(piscina.map(lambda _: _le(), range(leitores)))
    return _escritas(), len(set(tamanhos)), time.monotonic() - marca


def main() -> int:
    uma, _, tempo_de_uma = mede(1)
    muitas, formas, tempo_de_muitas = mede(LEITORES)

    print(f"\nP3-2 — cache frio, com o container no ar ({RANGE})\n")
    print(f"  1 leitura ............... {uma} reconstrucao(oes)")
    print(f"  {LEITORES} leituras simultaneas ... {muitas} reconstrucao(oes)")
    print(f"  payloads distintos ...... {formas} (todos iguais e o esperado)")

    # O TEMPO E CONTEXTO, E NAO PROVA DE SERIALIZACAO — e eu quase escrevi que
    # era. A razao abaixo mistura duas coisas: a conexao e o transporte, que
    # correm em PARALELO, e o corpo do handler, que nao corre. Com este pack o
    # fold custa microssegundos, entao a parte serializada e invisivel no
    # relogio e a razao fica perto de 1 — o que NAO contradiz a contagem acima.
    #
    # Quem prova a serializacao e a linha das reconstrucoes: 20 conexoes
    # simultaneas e UMA escrita so. O numero abaixo esta aqui para dizer de onde
    # vem o tempo, e nao para sustentar a conclusao.
    razao = tempo_de_muitas / tempo_de_uma if tempo_de_uma else 0.0
    print(
        f"  tempo de 1 .............. {tempo_de_uma * 1000:.0f} ms\n"
        f"  tempo de {LEITORES} ............. {tempo_de_muitas * 1000:.0f} ms "
        f"({razao:.1f}x o de uma — conexao e transporte correm em paralelo)\n"
    )

    if muitas <= 1:
        print(
            "  A PENDENCIA NAO OCORRE COMO DESCRITA, e a razao NAO e single-flight.\n"
            "  A rota e `async def` com corpo SINCRONO: a corrotina roda ate o fim\n"
            "  sem ceder o laco, entao o segundo leitor so comeca depois que o\n"
            "  primeiro ja gravou o cache. Nao ha voo concorrente para unificar.\n"
            "  Onde ela volta: mais de um worker, ou um caminho de leitura de fato\n"
            "  assincrono. Ver a D22 na §4.9 do registro da fase."
        )
    else:
        print(
            f"  a pendencia OCORRE: {muitas} leituras reconstruiram o estado.\n"
            "  O custo por reconstrucao e o da §3.8 da Fase 2 — 2,874 s em 150\n"
            "  mil eventos —, entao o impacto depende do VOLUME, e nao do numero\n"
            "  de leitores. Ver a decisao na §4.9 do registro da fase."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
