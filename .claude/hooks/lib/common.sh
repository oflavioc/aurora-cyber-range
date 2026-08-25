#!/usr/bin/env bash
# Biblioteca comum dos hooks (Onda 0 da Estrutura Agêntica).
#
# Contrato — elimina uma classe inteira de bugs:
#   1. O payload JSON do hook é lido do stdin UMA única vez, pelo hook,
#      para a variável PAYLOAD:   PAYLOAD="$(cat)"
#   2. Campos são consultados via payload_get '.a.b' — em Python (dependência
#      que o projeto já tem), nunca jq (incerto no Git Bash do Windows).
#   3. Matching de caminho: use match_path, que aceita / e \ (edge case win32).
#
# Hooks bloqueantes saem com exit 2; hooks informativos SEMPRE exit 0.

PYBIN=python3; command -v python3 >/dev/null 2>&1 || PYBIN=python

project_root() { git rev-parse --show-toplevel 2>/dev/null; }

# payload_get '.tool_input.file_path'  — lê de $PAYLOAD, nunca do stdin
payload_get() {
  PAYLOAD="${PAYLOAD:-}" "$PYBIN" - "$1" <<'PY'
import json, os, sys
try:
    d = json.loads(os.environ.get("PAYLOAD") or "{}")
except Exception:
    d = {}
cur = d
for part in sys.argv[1].lstrip(".").split("."):
    cur = cur.get(part) if isinstance(cur, dict) else None
    if cur is None:
        break
sys.stdout.write(cur if isinstance(cur, str) else ("" if cur is None else json.dumps(cur)))
PY
}

# match_path "<caminho>" "<padrão glob>"  — normaliza \ para / antes do case
match_path() {
  local p="${1//\\//}"
  case "$p" in $2) return 0;; *) return 1;; esac
}
