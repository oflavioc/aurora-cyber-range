#!/usr/bin/env python3
"""INVARIANTE 1 — range-core/ nao importa nada de domains/.

00_MASTER_SPEC.md secao 5.1 e 01_ARCHITECTURE.md secao 2.

Deteccao por AST para Python: import direto, import com alias, import
relativo que escape para domains/, importlib.import_module e __import__ com
argumento literal. Grep nao veria alias nem import dinamico.

Arquivos TypeScript/JavaScript sob range-core/web/ passam por extracao de
declaracao de import — a stdlib nao traz analisador de TypeScript. A cobertura
e deliberadamente conservadora e nao e exercitada por nenhum probe da Fase 0,
porque ainda nao existe front-end.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum. Sem isto, o
# import de _common escreveria tools/__pycache__ na arvore auditada.
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

CORE_DIR = "range-core"
DOMAINS_DIR = "domains"

PYTHON_SUFFIXES = (".py",)
WEB_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts")

RULE = "INVARIANTE 1 - fronteira core/adapter"
ADVICE = "Se o core precisa conhecer o dominio, corrija a abstracao, nao o teste."


def _module_targets_domains(module: str | None) -> bool:
    if not module:
        return False
    return module == DOMAINS_DIR or module.startswith(DOMAINS_DIR + ".")


def _relative_escapes_into_domains(path: Path, level: int, module: str | None) -> bool:
    base = path.resolve().parent
    for _ in range(max(level - 1, 0)):
        base = base.parent
    target = base
    if module:
        for part in module.split("."):
            target = target / part
    try:
        relative = target.relative_to(REPO_ROOT)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] == DOMAINS_DIR


def _literal_argument(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _check_python(path: Path, violations: list[Violation]) -> None:
    tree = parse_python(path)
    source = rel(path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_targets_domains(alias.name):
                    detail = f"import de '{alias.name}'"
                    if alias.asname:
                        detail += f" com alias '{alias.asname}'"
                    violations.append(Violation(source, node.lineno, RULE, f"{detail}. {ADVICE}"))
        elif isinstance(node, ast.ImportFrom):
            if node.level and _relative_escapes_into_domains(path, node.level, node.module):
                dots = "." * node.level
                violations.append(
                    Violation(
                        source,
                        node.lineno,
                        RULE,
                        f"import relativo '{dots}{node.module or ''}' resolve dentro de "
                        f"{DOMAINS_DIR}/. {ADVICE}",
                    )
                )
            elif not node.level and _module_targets_domains(node.module):
                violations.append(
                    Violation(
                        source,
                        node.lineno,
                        RULE,
                        f"import de '{node.module}'. {ADVICE}",
                    )
                )
        elif isinstance(node, ast.Call):
            callee = _callee_name(node)
            if callee in ("import_module", "__import__"):
                literal = _literal_argument(node)
                if literal is not None and _module_targets_domains(literal):
                    violations.append(
                        Violation(
                            source,
                            node.lineno,
                            RULE,
                            f"import dinamico de '{literal}' via {callee}. {ADVICE}",
                        )
                    )


def _web_specifiers(text: str):
    """Extrai (linha, especificador) de declaracoes de import/require."""
    keywords = ("from", "import", "require")
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if not any(keyword in line for keyword in keywords):
            continue
        quote = None
        buffer: list[str] = []
        for char in line:
            if quote is None:
                if char in "\"'`":
                    quote = char
                    buffer = []
            elif char == quote:
                specifier = "".join(buffer)
                if specifier:
                    yield number, specifier
                quote = None
            else:
                buffer.append(char)


def _check_web(path: Path, violations: list[Violation]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"{rel(path)}: nao foi possivel ler ({exc})") from exc
    source = rel(path)

    for number, specifier in _web_specifiers(text):
        if specifier.startswith("."):
            target = (path.resolve().parent / specifier).resolve()
            try:
                relative = target.relative_to(REPO_ROOT)
            except ValueError:
                continue
            hits = bool(relative.parts) and relative.parts[0] == DOMAINS_DIR
        else:
            hits = specifier == DOMAINS_DIR or specifier.startswith(DOMAINS_DIR + "/")
        if hits:
            violations.append(
                Violation(
                    source,
                    number,
                    RULE,
                    f"import de '{specifier}' resolve dentro de {DOMAINS_DIR}/. {ADVICE}",
                )
            )


def main() -> int:
    violations: list[Violation] = []
    try:
        for path in iter_files(REPO_ROOT, [CORE_DIR], PYTHON_SUFFIXES):
            _check_python(path, violations)
        for path in iter_files(REPO_ROOT, [CORE_DIR], WEB_SUFFIXES):
            _check_web(path, violations)
    except ContractError as exc:
        return fail(str(exc))

    return report(RULE, violations)


if __name__ == "__main__":
    sys.exit(main())
