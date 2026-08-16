#!/usr/bin/env python3
"""Prova que `check_core_contract_imports.py` REPROVA contra violacao plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina
que a Fase 0 fixou em `phase0_negative_tests.py` e que todo `*_probes.py` deste
repositorio repete.

OS EIXOS, e cada um existe por uma forma de burlar diferente
-------------------------------------------------------------
Quatro sao FORMAS DE IMPORT: direto, com alias, dinamico e relativo. Uma
checagem que so visse `from contracts... import` seria contornavel sem ma fe —
`importlib.import_module` e o que alguem escreve para carregar por nome
calculado, e o import relativo e o que aparece quando alguem move um arquivo.

Dois sao DEFEITOS DA PROPRIA LISTA, e sao os que sustentam a forma whitelist:
declaracao que nao corresponde mais ao codigo, e arquivo declarado que deixou de
importar. Sem esses dois, a lista envelheceria virando permissao ampla — que e o
modo de falha de toda whitelist.

COPIA TEMPORARIA, NUNCA A ARVORE. `range-core/` inteiro e copiado para
diretorio temporario e a violacao e plantada la. A checagem aceita o caminho da
raiz do core justamente para isto.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "range-core"
CHECAGEM = REPO_ROOT / "scripts" / "check_core_contract_imports.py"

#: Arquivo do core que HOJE nao importa nada de `contracts/`. E nele que os
#: probes de "arquivo nao declarado" plantam.
LIMPO = "clock/exercise_clock.py"

#: Arquivo declarado, usado nos probes que atacam a propria lista.
DECLARADO = "events/epoch.py"

#: (rotulo, arquivo, texto plantado no topo, trecho esperado no stderr)
PROBES: list[tuple[str, str, str, str]] = [
    (
        "import direto em arquivo nao declarado",
        LIMPO,
        "from contracts.generated.events import EXERCISE_PAUSED\n",
        "NAO esta declarado",
    ),
    (
        "import com alias em arquivo nao declarado",
        LIMPO,
        "import contracts.generated.events as catalogo\n",
        "NAO esta declarado",
    ),
    (
        "import dinamico via import_module",
        LIMPO,
        "from importlib import import_module\n"
        "_c = import_module('contracts.generated.events')\n",
        "NAO esta declarado",
    ),
    (
        "import relativo que escapa para contracts/",
        LIMPO,
        "from ...contracts.generated import events as _e\n",
        "NAO esta declarado",
    ),
    (
        "arquivo declarado importando ALEM do declarado",
        DECLARADO,
        "import contracts\n",
        "declarado ['contracts.generated.events']",
    ),
]


def roda(rotulo: str, arquivo: str, plantado: str, esperado: str) -> bool:
    with tempfile.TemporaryDirectory() as temporario:
        destino = Path(temporario) / "range-core"
        shutil.copytree(CORE, destino, ignore=shutil.ignore_patterns("__pycache__"))
        alvo = destino / arquivo
        alvo.write_text(plantado + alvo.read_text(encoding="utf-8"), encoding="utf-8")

        resultado = subprocess.run(
            [sys.executable, str(CHECAGEM), str(destino)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        saida = resultado.stdout + resultado.stderr

        if resultado.returncode != 1:
            print(
                f"FALHA: probe '{rotulo}' saiu com rc={resultado.returncode}, "
                "esperado 1. rc diferente de 1 indica erro de ferramenta, nao deteccao"
            )
            print(saida)
            return False
        if esperado not in saida:
            print(f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado")
            print(saida)
            return False

    print(f"OK: reprovou com violacao plantada - {rotulo}")
    return True


def roda_declaracao_orfa() -> bool:
    """Entrada declarada cujo arquivo deixou de importar.

    Diferente dos demais: aqui a violacao e a REMOCAO do import, e nao um import
    plantado. E o eixo que impede a lista de virar permissao ampla por inercia.
    """
    with tempfile.TemporaryDirectory() as temporario:
        destino = Path(temporario) / "range-core"
        shutil.copytree(CORE, destino, ignore=shutil.ignore_patterns("__pycache__"))
        alvo = destino / DECLARADO
        texto = alvo.read_text(encoding="utf-8")
        antes = "from contracts.generated.events import ROLLBACK_PERFORMED"
        if texto.count(antes) != 1:
            print(
                f"FALHA: a ancora {antes!r} nao casa exatamente uma vez em "
                f"{DECLARADO}: o probe deixou de plantar o que diz plantar"
            )
            return False
        alvo.write_text(texto.replace(antes, "ROLLBACK_PERFORMED = 'x'"), encoding="utf-8")

        resultado = subprocess.run(
            [sys.executable, str(CHECAGEM), str(destino)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        saida = resultado.stdout + resultado.stderr

        if resultado.returncode != 1 or "nao importa mais" not in saida:
            print(f"FALHA: declaracao orfa nao foi acusada (rc={resultado.returncode})")
            print(saida)
            return False

    print("OK: reprovou com violacao plantada - declaracao orfa")
    return True


def arvore_limpa() -> bool:
    resultado = subprocess.run(
        [sys.executable, str(CHECAGEM)], capture_output=True, text=True, cwd=REPO_ROOT
    )
    if resultado.returncode != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        print(resultado.stdout + resultado.stderr)
        return False
    print("OK: arvore limpa passa (rc=0)")
    return True


def main() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda(*probe) for probe in PROBES]
    resultados.append(roda_declaracao_orfa())
    print()
    if all(resultados):
        print(
            f"check_core_contract_imports.py reprova nos {len(resultados)} eixos: "
            f"{len(PROBES)} de import plantado e 1 de declaracao orfa."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
