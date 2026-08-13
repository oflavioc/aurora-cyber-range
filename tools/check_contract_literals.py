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

Python e TypeScript sao varridos. 01_ARCHITECTURE.md secao 5.4 exige constante
gerada para as DUAS linguagens, e o layout da secao 2 coloca range-core/web/ e
domains/<adapter>/web/ em TypeScript: cobrir so Python deixaria literal de flag
em TSX passar pelo gate real do CI, mesmo com o hook rapido acusando.

Python usa AST. TypeScript usa varredura lexica, porque a stdlib nao traz
analisador de TypeScript — ver iter_web_string_literals em _common.py, onde o
limite esta declarado.
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
    WEB_SUFFIXES,
    ContractError,
    Violation,
    adapter_names,
    fail,
    iter_files,
    iter_web_string_literals,
    load_declared_event_types,
    load_declared_flags,
    parse_python,
    rel,
    report,
)

#: Onde literais de flag e de event_type sao legitimos, ANCORADO a partir da
#: raiz: contracts/ guarda as fontes canonicas, domains/<adapter>/generated/ e
#: contracts/generated/ guardam os artefatos, tools/codegen.py os produz.
#:
#: Casar o segmento em qualquer profundidade autorizava
#: domains/<adapter>/api/contracts/handler.py a conter literal de flag, so por
#: ter um segmento "contracts" no meio do caminho. Isencao e a excecao ao
#: invariante 2: larga demais, ela o anula.
AUTHORIZED_FILES = frozenset({"tools/codegen.py"})
CONTRACTS_ROOT = "contracts"
DOMAINS_ROOT = "domains"

SCANNED_DIRS = ("range-core", "domains")
PYTHON_SUFFIXES = (".py",)

RULE_DECLARED = "INVARIANTE 2 - literal de contrato no codigo"
RULE_UNDECLARED = "INVARIANTE 2 - literal com forma de flag nao declarada"


def _is_authorized(path: Path) -> bool:
    relative = path.resolve().relative_to(REPO_ROOT)
    if relative.as_posix() in AUTHORIZED_FILES:
        return True
    parts = relative.parts
    # contracts/... (inclui contracts/generated/)
    if parts[:1] == (CONTRACTS_ROOT,):
        return True
    # domains/<adapter>/generated/...
    return len(parts) > 3 and parts[0] == DOMAINS_ROOT and parts[2] == GENERATED_DIR


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


def _judge(
    value: str,
    source: str,
    line: int,
    declared_flags: dict[str, str],
    declared_events: dict[str, str],
    adapters: frozenset[str],
    violations: list[Violation],
) -> None:
    if value in declared_flags:
        violations.append(
            Violation(
                source,
                line,
                RULE_DECLARED,
                f"literal '{value}' declarado em {declared_flags[value]}. "
                "Use a constante gerada.",
            )
        )
    elif value in declared_events:
        violations.append(
            Violation(
                source,
                line,
                RULE_DECLARED,
                f"event_type '{value}' declarado em {declared_events[value]}. "
                "Use a constante gerada.",
            )
        )
    elif _looks_like_flag(value, adapters):
        violations.append(
            Violation(
                source,
                line,
                RULE_UNDECLARED,
                f"literal '{value}' tem forma de flag de um adapter existente "
                "mas nao esta declarado em nenhum flags.yaml.",
            )
        )


def main() -> int:
    violations: list[Violation] = []
    try:
        declared_flags = load_declared_flags(REPO_ROOT)
        declared_events = load_declared_event_types(REPO_ROOT)
        adapters = frozenset(adapter_names(REPO_ROOT))

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            if _is_authorized(path):
                continue
            source = rel(path)
            for node in _string_constants(parse_python(path)):
                _judge(
                    node.value, source, node.lineno,
                    declared_flags, declared_events, adapters, violations,
                )

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, WEB_SUFFIXES):
            if _is_authorized(path):
                continue
            source = rel(path)
            for line, value in iter_web_string_literals(path):
                _judge(
                    value, source, line,
                    declared_flags, declared_events, adapters, violations,
                )
    except ContractError as exc:
        return fail(str(exc))

    return report("INVARIANTE 2 - literais de contrato", violations)


if __name__ == "__main__":
    sys.exit(main())
