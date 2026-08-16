#!/usr/bin/env python3
"""Prova que `check_fold_authority.py` REPROVA contra autoridade plantada.

OS DOIS EIXOS QUE IMPORTAM, e o segundo e o que a peca 2 ensinou a escrever:

  construcao de `SimulationState` fora dos sitios declarados  -> reprova
  metodo publico da porta que ACEITA estado pronto            -> reprova

Sem o segundo, bastaria acrescentar `write(state: SimulationState)` ao lado de
`refresh` e a checagem ficaria verde: os sitios de construcao continuariam os
dois declarados, e o caminho de escrita fora do fold estaria aberto.

E os dois eixos de envelhecimento: autorizacao que sobrou, e a porta que sumiu.

COMO OS PROBES PLANTAM. `main` aceita a raiz do core, entao cada probe monta uma
arvore em diretorio temporario com o defeito dentro. Nada e escrito em
`range-core/`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "range-core"
CHECAGEM = REPO_ROOT / "scripts" / "check_fold_authority.py"

#: `(rotulo, arquivo, texto original, texto plantado, trecho esperado)`
PROBES = [
    (
        "construcao de estado fora dos sitios declarados",
        "engine/inject_engine.py",
        "    def state(self) -> SimulationState:",
        "    def forjar(self) -> SimulationState:\n"
        "        return SimulationState(flags={}, simulation_epoch=0)\n"
        "\n"
        "    def state(self) -> SimulationState:",
        "nao esta autorizado",
    ),
    (
        "porta com metodo publico que ACEITA estado pronto",
        "state/cache.py",
        "    def read(self) -> CachedProjection | None:",
        "    def write(self, estado: SimulationState) -> None:\n"
        '        """Atalho: grava sem foldar."""\n'
        "        raise NotImplementedError\n"
        "\n"
        "    def read(self) -> CachedProjection | None:",
        "aceita `estado: SimulationState`",
    ),
    (
        "sitio autorizado que deixou de construir",
        "state/cache.py",
        "    return SimulationState(\n        flags=documento[\"flags\"],",
        "    return _nao_e_mais_estado(\n        flags=documento[\"flags\"],",
        "Autorizacao que sobra",
    ),
    (
        "a porta declarada desaparece",
        "state/cache.py",
        "class SimulationStateCache(ABC):",
        "class OutroNomeQualquer(ABC):",
        "a classe SimulationStateCache nao existe mais",
    ),
]


def roda(rotulo, arquivo, antes, depois, esperado) -> bool:
    with tempfile.TemporaryDirectory() as temporario:
        destino = Path(temporario) / "range-core"
        shutil.copytree(CORE, destino, ignore=shutil.ignore_patterns("__pycache__"))
        alvo = destino / arquivo
        texto = alvo.read_text(encoding="utf-8")

        if texto.count(antes) != 1:
            print(
                f"FALHA: probe '{rotulo}' nao ancorou — o trecho aparece "
                f"{texto.count(antes)}x em {arquivo}, esperado 1"
            )
            return False

        alvo.write_text(texto.replace(antes, depois), encoding="utf-8")
        resultado = subprocess.run(
            [sys.executable, str(CHECAGEM), str(destino)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        saida = resultado.stdout + resultado.stderr

        if resultado.returncode != 1:
            print(f"FALHA: probe '{rotulo}' saiu com rc={resultado.returncode}, esperado 1")
            print(saida)
            return False
        if esperado not in saida:
            print(f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado")
            print(saida)
            return False

    print(f"OK: reprovou com violacao plantada - {rotulo}")
    return True


def main_probes() -> int:
    limpo = subprocess.run(
        [sys.executable, str(CHECAGEM)], capture_output=True, text=True, cwd=REPO_ROOT
    )
    if limpo.returncode != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        print(limpo.stdout + limpo.stderr)
        return 1

    resultados = [roda(*p) for p in PROBES]
    print()
    if all(resultados):
        print(
            f"check_fold_authority.py reprova nos {len(PROBES)} eixos: construcao "
            "nao autorizada, porta aceitando estado pronto, autorizacao que "
            "sobrou, e a porta declarada sumindo."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
