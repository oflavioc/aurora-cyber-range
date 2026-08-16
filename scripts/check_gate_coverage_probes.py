#!/usr/bin/env python3
"""Prova que `check_gate_coverage.py` REPROVA contra classificacao plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina da
Fase 0, repetida por todo `*_probes.py` deste repositorio.

POR QUE OS PROBES INJETAM LISTA DE ARQUIVOS
--------------------------------------------
Os defeitos que esta checagem pega sao sobre arquivos que **ainda nao existem**:
um diretorio novo no topo, um caminho em dois conjuntos, uma declaracao que
sobrou. Plantar cada um no repositorio seria escrever na arvore para testar, e
`verifica()` recebe a lista justamente para nao precisar disso.

O RISCO DESSA ESCOLHA, e o que o fecha: lista injetada nao exercita o casamento
de pathspec contra o `git`. Por isso a checagem principal **se confere contra o
`git ls-files`** sobre os arquivos reais, e o quinto probe abaixo prova que essa
conferencia reprova quando os dois discordam.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_gate_coverage import (  # noqa: E402
    WORKFLOW,
    _pathspecs,
    main,
    verifica,
)

SPEC = _pathspecs("SPEC", WORKFLOW.read_text(encoding="utf-8"))
CODE = _pathspecs("CODE", WORKFLOW.read_text(encoding="utf-8"))

#: `(rotulo, arquivos, spec, code, trecho esperado)`.
PROBES = [
    (
        "diretorio novo no topo, invisivel ao gate",
        ["servicos/api/main.py"],
        SPEC,
        CODE,
        "nao esta em SPEC, nem em CODE",
    ),
    (
        "arquivo de spec fora de docs/spec/ e sem classificacao",
        ["docs/NORMATIVO.md"],
        SPEC,
        CODE,
        "nao esta em SPEC, nem em CODE",
    ),
    (
        "caminho nos DOIS conjuntos: o gate vira bloqueio",
        ["docs/spec/00_MASTER_SPEC.md"],
        SPEC,
        CODE + ["docs/spec/"],
        "esta em SPEC **e** em CODE",
    ),
    (
        "declaracao descritiva sobrando sobre caminho ja coberto",
        ["tools/check_core_boundary.py"],
        SPEC,
        CODE,
        None,  # este caso e verde: `tools/` nao esta declarado descritivo
    ),
    (
        "o checklist da Fase 0 voltando a ficar fora dos dois",
        ["docs/process/PHASE_0_CHECKLIST.md"],
        ["docs/spec/"],
        [p for p in CODE if p != ":(exclude)docs/process/PHASE_0_CHECKLIST.md"]
        + [":(exclude)docs/process/"],
        "nao esta em SPEC, nem em CODE",
    ),
]


def roda(rotulo, arquivos, spec, code, esperado) -> bool:
    problemas = verifica(arquivos, spec, code)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': classificacao plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou, mas nao pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com classificacao plantada - {rotulo}")
    return True


def probe_matcher_divergente() -> bool:
    """O eixo que a lista injetada NAO cobre: matcher discordando do `git`.

    Planta um pathspec que o `git` entende e o matcher local nao — um glob com
    barra, que `:(glob)` resolve em profundidade e a regra local recusa por
    exigir caminho sem barra. A checagem tem de reprovar por DIVERGENCIA, e nao
    por classificacao.
    """
    original = WORKFLOW.read_text(encoding="utf-8")
    plantado = original.replace(
        "            docs/spec/ docs/process/PHASE_0_CHECKLIST.md | wc -l)",
        "            docs/spec/ docs/process/PHASE_0_CHECKLIST.md ':(glob)docs/**/*.md' | wc -l)",
    )
    if plantado == original:
        print("FALHA: o probe de matcher nao ancorou — a forma do gate mudou")
        return False

    try:
        WORKFLOW.write_text(plantado, encoding="utf-8")
        if main([]) == 0:
            print("FALHA: matcher divergente do git e a checagem PASSOU")
            return False
    finally:
        WORKFLOW.write_text(original, encoding="utf-8")

    print("OK: reprovou com matcher divergindo do git")
    return True


def arvore_limpa() -> bool:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return False
    return True


def main_probes() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_matcher_divergente())
    print()
    if all(resultados):
        print(
            f"check_gate_coverage.py reprova nos {len(resultados)} eixos: "
            "caminho invisivel, caminho nos dois conjuntos, caso verde de "
            "controle, regressao da P37 e matcher divergente do git."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
