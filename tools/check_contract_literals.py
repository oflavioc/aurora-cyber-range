#!/usr/bin/env python3
"""INVARIANTE 2 — nenhuma string literal de flag ou de event_type no codigo.

00_MASTER_SPEC.md secao 5.1, 01_ARCHITECTURE.md secao 5.4 e 09_EVENT_MODEL.md
secao 4.

O verificador le os contratos canonicos e so entao varre o codigo por AST.
Essa ordem importa: a autoridade sobre o que e uma flag e o contrato, nao um
padrao textual. Um literal so e violacao porque o contrato o declara.

Duas deteccoes complementares:

1. literal exatamente igual a um nome declarado em domains/<adapter>/flags.yaml
   ou no catalogo contracts/events.schema.yaml;
2. literal com forma de flag de um adapter existente (`<adapter>.<nome>`) que
   NAO esta declarado — erro de digitacao que a deteccao 1 nao pegaria e que
   em runtime viraria flag desconhecida.

A lista de adapters vem de domains/<adapter>/, nao de uma constante embutida.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    GENERATED_DIR,
    REPO_ROOT,
    ContractError,
    Violation,
    adapter_names,
    fail,
    iter_files,
    load_declared_event_types,
    load_declared_flags,
    parse_python,
    rel,
    report,
)

#: Onde literais de flag e de event_type sao legitimos.
#: contracts/ guarda as fontes canonicas; */generated/ guarda os artefatos do
#: codegen; tools/codegen.py e quem os produz.
AUTHORIZED_DIR_PARTS = frozenset({"contracts", GENERATED_DIR})
AUTHORIZED_FILES = frozenset({"tools/codegen.py"})

SCANNED_DIRS = ("range-core", "domains")
PYTHON_SUFFIXES = (".py",)

RULE_DECLARED = "INVARIANTE 2 - literal de contrato no codigo"
RULE_UNDECLARED = "INVARIANTE 2 - literal com forma de flag nao declarada"


def _is_authorized(path: Path) -> bool:
    relative = path.resolve().relative_to(REPO_ROOT)
    if relative.as_posix() in AUTHORIZED_FILES:
        return True
    return any(part in AUTHORIZED_DIR_PARTS for part in relative.parts)


def _string_constants(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node


def _looks_like_flag(value: str, adapters: frozenset[str]) -> bool:
    head, separator, tail = value.partition(".")
    if not separator or head not in adapters:
        return False
    if not tail:
        return False
    return all(part.replace("_", "").isalnum() for part in tail.split(".") if part)


def main() -> int:
    violations: list[Violation] = []
    try:
        declared_flags = load_declared_flags(REPO_ROOT)
        declared_events = load_declared_event_types(REPO_ROOT)
        adapters = frozenset(adapter_names(REPO_ROOT))

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            if _is_authorized(path):
                continue
            tree = parse_python(path)
            source = rel(path)
            for node in _string_constants(tree):
                value = node.value
                if value in declared_flags:
                    violations.append(
                        Violation(
                            source,
                            node.lineno,
                            RULE_DECLARED,
                            f"literal '{value}' declarado em {declared_flags[value]}. "
                            "Use a constante gerada.",
                        )
                    )
                elif value in declared_events:
                    violations.append(
                        Violation(
                            source,
                            node.lineno,
                            RULE_DECLARED,
                            f"event_type '{value}' declarado em {declared_events[value]}. "
                            "Use a constante gerada.",
                        )
                    )
                elif _looks_like_flag(value, adapters):
                    violations.append(
                        Violation(
                            source,
                            node.lineno,
                            RULE_UNDECLARED,
                            f"literal '{value}' tem forma de flag de um adapter existente "
                            "mas nao esta declarado em nenhum flags.yaml.",
                        )
                    )
    except ContractError as exc:
        return fail(str(exc))

    return report("INVARIANTE 2 - literais de contrato", violations)


if __name__ == "__main__":
    sys.exit(main())
