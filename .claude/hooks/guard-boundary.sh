#!/usr/bin/env bash
# Hook PreToolUse (matcher: Write|Edit) — BLOQUEANTE (exit 2).
#
# A change boundary deixa de ser prosa: este hook nega a edição direta de
# qualquer path listado em .claude/verify/boundary.json, explicando o RITO que
# autoriza a mudança. (Lição de origem: regra de proteção em prosa de spec não
# impediu a edição de superfícies congeladas em duas fases seguidas.)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

PAYLOAD="$(cat)"
ARQ="$(payload_get '.tool_input.file_path')"
[ -z "$ARQ" ] && exit 0

cd "$(project_root)" 2>/dev/null || exit 0

RES=$(PAYLOAD="" ARQ="$ARQ" "$PYBIN" - <<'PY'
import json, os, sys
arq = os.environ["ARQ"].replace("\\", "/")
try:
    b = json.load(open(".claude/verify/boundary.json", encoding="utf-8"))
except Exception:
    sys.exit(0)   # sem manifesto, não bloqueia (compliance-audit acusa a ausência)
for classe, spec in b.get("classes", {}).items():
    for p in spec["paths"]:
        if arq == p or arq.endswith("/" + p):
            print(f"{classe}|{p}|{spec['rito']}")
            sys.exit(0)
PY
)
[ -z "$RES" ] && exit 0

CLASSE="${RES%%|*}"; RESTO="${RES#*|}"; ALVO="${RESTO%%|*}"; RITO="${RESTO#*|}"
{
  echo "guard-boundary: edição direta de '$ALVO' BLOQUEADA (classe: $CLASSE)."
  echo "Rito autorizado: $RITO"
  echo "Referência: .claude/verify/boundary.json (R6)."
} >&2
exit 2
