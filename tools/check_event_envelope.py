#!/usr/bin/env python3
"""INVARIANTE 4 — nenhum evento emitido carrega objective_ids.

09_EVENT_MODEL.md secao 1.2 e 06_ACCEPTANCE_TESTS.md T1.

O binding evento -> objetivo ocorre na projecao, via observability_hooks.yaml.
Se a aplicacao souber que uma acao satisfaz um objetivo, o dominio passa a
conhecer o desenho de exercicio e a fronteira core/adapter vaza.

A varredura e por NEGACAO: todo range-core/ e todo domains/ sao caminho de
emissao, exceto as camadas de projecao e pontuacao, unico lugar onde o binding
e legitimo.

A versao anterior usava allowlist de segmentos ("events", "api") e por isso
nao enxergava range-core/engine/, /clock/, /state/, /telemetry/, /evidence/
nem /rubrics/ — sendo que 01_ARCHITECTURE.md secao 6 declara o inject-engine
como emissor de eventos de effect. Allowlist de diretorio falha em silencio a
cada diretorio novo; negacao por padrao falha para o lado seguro.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    REPO_ROOT,
    ContractError,
    Violation,
    fail,
    iter_files,
    parse_python,
    rel,
    report,
)

FORBIDDEN_FIELD = "objective_ids"

SCANNED_DIRS = ("range-core", "domains")
PYTHON_SUFFIXES = (".py",)

#: UNICOS segmentos onde o binding evento->objetivo e legitimo: as projecoes
#: de 09_EVENT_MODEL.md secao 5 (objective_evidence, metrics, calibration) e o
#: relatorio. Qualquer outro lugar sob range-core/ ou domains/ e emissao.
#:
#: Esta lista e a excecao ao invariante, entao vive aqui em cima, nomeada.
#: Acrescentar segmento aqui AFROUXA a verificacao — mudanca que exige
#: justificativa contra 09_EVENT_MODEL.md secao 1.2.
PROJECTION_DIR_PARTS = frozenset({"objectives", "aar", "metrics", "calibration"})

RULE = "INVARIANTE 4 - objective_ids no caminho de emissao"
ADVICE = "O binding evento->objetivo ocorre na projecao, via observability_hooks.yaml."


def _is_emission_path(path: Path) -> bool:
    """Emissao por padrao; projecao apenas quando declarada acima."""
    relative = path.resolve().relative_to(REPO_ROOT)
    return not any(part in PROJECTION_DIR_PARTS for part in relative.parts)


def _hits(tree: ast.Module):
    """Localiza objective_ids como chave, keyword, atributo ou identificador."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == FORBIDDEN_FIELD:
            yield node.lineno, "chave ou literal"
        elif isinstance(node, ast.keyword) and node.arg == FORBIDDEN_FIELD:
            yield getattr(node.value, "lineno", 0), "argumento nomeado"
        elif isinstance(node, ast.Attribute) and node.attr == FORBIDDEN_FIELD:
            yield node.lineno, "acesso a atributo"
        elif isinstance(node, ast.Name) and node.id == FORBIDDEN_FIELD:
            yield node.lineno, "identificador"
        elif isinstance(node, ast.arg) and node.arg == FORBIDDEN_FIELD:
            yield node.lineno, "parametro"


def main() -> int:
    violations: list[Violation] = []
    try:
        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            if not _is_emission_path(path):
                continue
            tree = parse_python(path)
            source = rel(path)
            seen: set[tuple[int, str]] = set()
            for line, kind in _hits(tree):
                if (line, kind) in seen:
                    continue
                seen.add((line, kind))
                violations.append(
                    Violation(
                        source,
                        line,
                        RULE,
                        f"'{FORBIDDEN_FIELD}' presente como {kind}. {ADVICE}",
                    )
                )
    except ContractError as exc:
        return fail(str(exc))

    return report(RULE, violations)


if __name__ == "__main__":
    sys.exit(main())
