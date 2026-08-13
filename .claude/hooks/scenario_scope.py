#!/usr/bin/env python3
"""PreToolUse — confina Write/Edit do scenario-designer a scenarios/."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def deny(reason: str) -> int:
    print(f"BLOQUEADO: scenario-designer so pode escrever em scenarios/.\n{reason}", file=sys.stderr)
    return 2


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = data.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not raw_path:
        return deny("Write/Edit sem caminho de arquivo identificavel.")

    cwd = Path(data.get("cwd") or ".").resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    candidate = candidate.resolve(strict=False)
    allowed_root = (cwd / "scenarios").resolve(strict=False)

    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        return deny(f"Destino fora do escopo permitido: {candidate}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
