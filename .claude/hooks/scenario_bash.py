#!/usr/bin/env python3
"""PreToolUse — Bash allowlist do scenario-designer."""
from __future__ import annotations

import json
import re
import sys

ALLOWED = [
    r"^range-cli\s+scenario\s+(validate|lint|dryrun)\s+scenarios/[A-Za-z0-9_.\-/]+\s*$",
    r"^git\s+diff(?:\s+--[^\s]+)*\s+--\s+scenarios(?:/[A-Za-z0-9_.\-/]+)?\s*$",
    r"^git\s+status(?:\s+--short)?\s*$",
]

DANGEROUS_SHELL = re.compile(r"(?:&&|\|\||;|\||>|<|`|\$\()")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = ((data.get("tool_input") or {}).get("command") or "").strip()
    if not cmd:
        return 0

    if DANGEROUS_SHELL.search(cmd):
        print("BLOQUEADO: encadeamento/redirecionamento nao e permitido ao scenario-designer.", file=sys.stderr)
        return 2

    if not any(re.fullmatch(pattern, cmd) for pattern in ALLOWED):
        print(
            "BLOQUEADO: Bash fora da allowlist do scenario-designer.\n"
            "Permitido: range-cli scenario validate|lint|dryrun em scenarios/; "
            "git diff -- scenarios/...; git status --short.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
