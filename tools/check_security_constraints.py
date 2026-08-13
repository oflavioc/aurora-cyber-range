#!/usr/bin/env python3
"""RESTRICOES DE SEGURANCA — 05_SECURITY_REQUIREMENTS.md secao 1.

Todos os efeitos de incidente sao simulados por estado da aplicacao. Este
verificador recusa comportamento ofensivo funcional: execucao dinamica de
codigo, execucao de shell e rotina de criptografia de arquivo como efeito de
ataque.

O que este verificador NAO faz, deliberadamente: proibir import de biblioteca
criptografica. JWT, hashing e TLS sao seguranca normal da aplicacao. A
proibicao e de efeito ofensivo funcional, nao de import.

A deteccao e por AST e olha CHAMADA, nao texto. Isso importa: os proprios
hooks e o harness de teste negativo carregam esses nomes dentro de strings,
e nenhum deles e violacao. Grep marcaria todos.
"""
from __future__ import annotations

import ast
import sys

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

SCANNED_DIRS = ("range-core", "domains", "tools", "scripts")
PYTHON_SUFFIXES = (".py",)

#: Chamadas a builtin proibidas: executam codigo montado em tempo de execucao.
FORBIDDEN_BUILTIN_CALLS = {
    "eval": "avaliacao dinamica de expressao",
    "exec": "execucao dinamica de codigo",
    "compile": "compilacao dinamica de codigo",
}

#: Chamadas <modulo>.<atributo> proibidas: entregam execucao ao shell do host.
FORBIDDEN_ATTRIBUTE_CALLS = {
    ("os", "system"): "execucao de shell",
    ("os", "popen"): "execucao de shell",
    ("os", "execv"): "substituicao de processo",
    ("os", "execve"): "substituicao de processo",
    ("os", "spawnl"): "criacao de processo arbitrario",
    ("subprocess", "getoutput"): "execucao de shell",
    ("subprocess", "getstatusoutput"): "execucao de shell",
}

#: Nomes de funcao que caracterizam criptografia de arquivo como efeito de
#: ataque. 05_SECURITY_REQUIREMENTS secao 1 proibe ransomware funcional.
FORBIDDEN_FUNCTION_NAMES = {
    "encrypt_files": "criptografia de arquivos como efeito de ataque",
    "encrypt_directory": "criptografia de arquivos como efeito de ataque",
    "ransom_encrypt": "criptografia de arquivos como efeito de ataque",
}

SUBPROCESS_MODULE = "subprocess"
SUBPROCESS_RUNNERS = frozenset({"run", "call", "check_call", "check_output", "Popen"})
SHELL_KEYWORD = "shell"

RULE = "RESTRICAO DE SEGURANCA - 05_SECURITY_REQUIREMENTS secao 1"
ADVICE = "Efeitos de incidente devem ser simulados por estado da aplicacao."


def _attribute_pair(node: ast.expr) -> tuple[str, str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None


def _uses_shell(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg != SHELL_KEYWORD:
            continue
        value = keyword.value
        if isinstance(value, ast.Constant) and value.value is True:
            return True
    return False


def _check_call(node: ast.Call, source: str, violations: list[Violation]) -> None:
    func = node.func

    if isinstance(func, ast.Name):
        label = FORBIDDEN_BUILTIN_CALLS.get(func.id) or FORBIDDEN_FUNCTION_NAMES.get(func.id)
        if label:
            violations.append(
                Violation(source, node.lineno, RULE, f"{label} via '{func.id}'. {ADVICE}")
            )
        return

    pair = _attribute_pair(func)
    if pair is None:
        if isinstance(func, ast.Attribute):
            label = FORBIDDEN_FUNCTION_NAMES.get(func.attr)
            if label:
                violations.append(
                    Violation(source, node.lineno, RULE, f"{label} via '{func.attr}'. {ADVICE}")
                )
        return

    module, attribute = pair
    label = FORBIDDEN_ATTRIBUTE_CALLS.get(pair)
    if label:
        violations.append(
            Violation(source, node.lineno, RULE, f"{label} via '{module}.{attribute}'. {ADVICE}")
        )
        return

    if module == SUBPROCESS_MODULE and attribute in SUBPROCESS_RUNNERS and _uses_shell(node):
        violations.append(
            Violation(
                source,
                node.lineno,
                RULE,
                f"'{module}.{attribute}' com {SHELL_KEYWORD} habilitado entrega a linha "
                f"ao shell do host. {ADVICE}",
            )
        )
        return

    label = FORBIDDEN_FUNCTION_NAMES.get(attribute)
    if label:
        violations.append(
            Violation(source, node.lineno, RULE, f"{label} via '{module}.{attribute}'. {ADVICE}")
        )


def main() -> int:
    violations: list[Violation] = []
    try:
        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            tree = parse_python(path)
            source = rel(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    _check_call(node, source, violations)
    except ContractError as exc:
        return fail(str(exc))

    return report(RULE, violations)


if __name__ == "__main__":
    sys.exit(main())
