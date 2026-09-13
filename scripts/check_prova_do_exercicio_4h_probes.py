#!/usr/bin/env python3
"""Prova que `check_prova_do_exercicio_4h.py` REPROVA nas sete direcoes.

Mesma forma dos probes dos pares irmaos: `avalia` recebe tudo por parametro,
entao cada direcao e um documento envenenado injetado — sem tocar disco, sem
git, sem Postgres. O controle positivo e um documento integro que TEM de
passar; sem ele, um `avalia` que reprovasse tudo passaria nos sete venenos.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_prova_do_exercicio_4h import ESQUEMA, avalia  # noqa: E402

ARVORE = "a" * 40


def _integro() -> dict:
    return {
        "esquema": ESQUEMA,
        "tree": ARVORE,
        "pack_dir": "scenarios/academus/ransomware-universidade",
        "maquina": "m", "python": "3.12", "data": "2026-09-13",
        "stack": "pg", "pack_id": "ransomware-universidade",
        "content_hash": "sha256:x", "eventos": 650,
        "caminhos": 4, "pontos": 2,
        "total_s": 0.025, "orcamento_s": 3.0,
        "arquivos": {"manifest.yaml": "h1", "injects.yaml": "h2"},
        "lint_sem_achados": True,
        "item_6_dryrun_todos_os_caminhos": True,
        "item_9_reconstrucao_em_menos_de_3_s": True,
    }


def main() -> int:
    falhas: list[str] = []

    def caso(rotulo, doc, arvore=ARVORE, versionado=False, em_disco=None, espera=None):
        problemas = avalia(doc, arvore, versionado, em_disco)
        if espera is None:
            if problemas:
                falhas.append(f"{rotulo}: controle positivo reprovou: {problemas[0]}")
            else:
                print(f"OK: controle positivo passa - {rotulo}")
            return
        if not problemas:
            falhas.append(f"{rotulo}: o veneno passou limpo")
        elif not any(espera in p for p in problemas):
            falhas.append(f"{rotulo}: reprovou, mas nao pela direcao esperada: {problemas}")
        else:
            print(f"OK: reprovou com veneno plantado - {rotulo}")

    caso("documento integro, pack ausente do checkout", _integro())
    caso(
        "documento integro, pack em disco identico",
        _integro(),
        em_disco={"manifest.yaml": "h1", "injects.yaml": "h2"},
    )
    caso("(a) arquivo ausente", None, espera="nao existe")
    caso("(b) arvore divergente", _integro() | {"tree": "b" * 40}, espera="OUTRO")
    caso("(c) evidencia versionada", _integro(), versionado=True, espera="VERSIONADO")
    caso("(d) contexto faltando", _integro() | {"maquina": ""}, espera="`maquina`")
    caso(
        "(e) item gravado como falha",
        _integro() | {"item_9_reconstrucao_em_menos_de_3_s": False},
        espera="NAO passou",
    )
    caso("(f) esquema desconhecido", _integro() | {"esquema": "outro/9"}, espera="esquema")
    caso(
        "(g) hash do pack divergente no disco",
        _integro(),
        em_disco={"manifest.yaml": "h1", "injects.yaml": "ADULTERADO"},
        espera="nao e o pack medido",
    )
    caso(
        "(g) arquivo do pack sumiu do disco",
        _integro(),
        em_disco={"manifest.yaml": "h1", "injects.yaml": "ausente"},
        espera="nao e o pack medido",
    )
    caso("sem hashes de arquivo", _integro() | {"arquivos": {}}, espera="`arquivos`")

    print()
    if falhas:
        for f in falhas:
            print(f"FALHA: {f}")
        return 1
    print(
        "check_prova_do_exercicio_4h.py reprova nas 7 direcoes (9 venenos) e "
        "aceita os 2 controles positivos — inclusive o modo declarado sem pack "
        "no checkout."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
