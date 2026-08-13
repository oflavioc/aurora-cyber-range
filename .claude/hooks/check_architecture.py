#!/usr/bin/env python3
"""
PreToolUse hook — invariantes arquiteturais do AURORA CYBER RANGE.

Exit 2 bloqueia a chamada; stderr volta ao modelo.
Feedback rapido, NAO gate: o gate real e o CI por AST.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

VIOLATIONS: list[str] = []


def check_core_boundary(path: str, content: str) -> None:
    norm = path.replace("\\", "/")
    if "range-core/" not in norm:
        return
    patterns = [
        (r"^\s*from\s+domains[\.\s]", "import direto de domains"),
        (r"^\s*import\s+domains[\.\s]", "import direto de domains"),
        (r"importlib\.import_module\(\s*['\"]domains", "import dinamico de domains"),
        (r"__import__\(\s*['\"]domains", "import dinamico de domains"),
        (r"from\s+['\"]\.\./\.\./domains", "import relativo de domains (TS/JS)"),
    ]
    for pat, label in patterns:
        for match in re.finditer(pat, content, re.MULTILINE):
            line = content[: match.start()].count("\n") + 1
            VIOLATIONS.append(
                f"INVARIANTE 1 — fronteira core/adapter\n"
                f"  {path}:{line}\n  {label}\n"
                "  range-core/ nao pode importar de domains/. Corrija a abstracao."
            )


def check_flag_literals(path: str, content: str) -> None:
    norm = path.replace("\\", "/")
    if "/generated/" in norm or norm.endswith((".yaml", ".yml", ".json", ".md")):
        return
    if "contracts/" in norm or "/codegen/" in norm:
        return
    for match in re.finditer(r'''['"]((?:academus|prontus|core)\.[a-z_][a-z0-9_]*)['"]''', content):
        line = content[: match.start()].count("\n") + 1
        VIOLATIONS.append(
            f"INVARIANTE 2 — literal de flag\n  {path}:{line}\n"
            f"  literal '{match.group(1)}' no codigo\n"
            "  Use a constante gerada a partir de flags.yaml."
        )


def check_objective_ids_in_events(path: str, content: str) -> None:
    norm = path.replace("\\", "/")
    if not any(seg in norm for seg in ("/events/", "/api/", "domains/")):
        return
    if "/objectives/" in norm or "/aar/" in norm:
        return
    match = re.search(r"objective_ids", content)
    if match:
        line = content[: match.start()].count("\n") + 1
        VIOLATIONS.append(
            f"INVARIANTE 4 — acoplamento dominio x desenho de exercicio\n"
            f"  {path}:{line}\n  objective_ids no caminho de emissao de evento\n"
            "  O binding evento->objetivo ocorre na projecao."
        )


def check_dangerous_execution(path: str, content: str) -> None:
    """Bloqueia padrões inequívocos; cripto legitima nao e proibida por import."""
    patterns = [
        (r"\bos\.system\(", "execucao de shell via os.system"),
        (r"\bsubprocess\.(?:call|run|Popen)\([^)]*shell\s*=\s*True", "subprocess com shell=True"),
        (r"\beval\(", "eval"),
        (r"\bexec\(", "exec"),
        (r"\bencrypt_files\s*\(", "rotina explicita de criptografia de arquivos"),
    ]
    for pat, label in patterns:
        match = re.search(pat, content)
        if match:
            line = content[: match.start()].count("\n") + 1
            VIOLATIONS.append(
                "RESTRICAO DE SEGURANCA — 05_SECURITY_REQUIREMENTS §1\n"
                f"  {path}:{line}\n  {label}\n"
                "  Efeitos de incidente devem ser simulados por estado. "
                "Criptografia legitima de aplicacao nao e proibida por mera importacao."
            )


def check_spec_edit(path: str, cwd: str) -> None:
    norm = path.replace("\\", "/")
    if "docs/spec/" not in norm:
        return

    try:
        branch = subprocess.run(
            ["git", "-C", cwd or ".", "branch", "--show-current"],
            check=False, text=True, capture_output=True, timeout=1,
        ).stdout.strip()
    except Exception:
        branch = ""

    if branch.startswith("spec-change/"):
        return

    VIOLATIONS.append(
        f"SPEC IMUTAVEL\n  {path}\n"
        "  Edicao de docs/spec/ so e permitida em branch dedicada spec-change/<slug>.\n"
        "  O PR tambem deve ter titulo iniciando com 'spec-change:' e nao pode misturar codigo."
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path:
        return 0

    content = tool_input.get("content") or tool_input.get("new_string") or ""
    check_spec_edit(path, data.get("cwd") or ".")

    if content and Path(path).suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        check_core_boundary(path, content)
        check_flag_literals(path, content)
        check_objective_ids_in_events(path, content)
        check_dangerous_execution(path, content)

    if VIOLATIONS:
        print("BLOQUEADO — invariante do AURORA violado\n", file=sys.stderr)
        for violation in VIOLATIONS:
            print(violation + "\n", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
