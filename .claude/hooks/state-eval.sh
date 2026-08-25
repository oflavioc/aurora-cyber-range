#!/usr/bin/env bash
# Hook UserPromptSubmit — INFORMATIVO (sempre exit 0).
#
# Injeta ESTADO REAL no contexto a cada prompt (estado real vale mais que
# lembrete fixo). Nada aqui bloqueia. As âncoras do spot-check vêm dos
# manifestos (boundary.json classes frozen/generated), nunca de hardcode.
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

PAYLOAD="$(cat)" || true
cd "$(project_root)" 2>/dev/null || exit 0

# (a) branch / worktree
BRANCH=$(git branch --show-current 2>/dev/null)
[ -n "$BRANCH" ] && echo "[git] Branch: $BRANCH"

# (b) mudanças pendentes (working tree ≠ HEAD)
PEND=$(git status --porcelain 2>/dev/null | grep -cE '\.(js|ts|py|css|html|json|yaml|yml|sh)$' || true)
[ "$PEND" -gt 0 ] 2>/dev/null && echo "[tree] $PEND arquivo(s) de produto/estrutura com mudança não commitada."

# (c) spot-check do baseline: até 2 âncoras protegidas contra o registry
"$PYBIN" - <<'PY' 2>/dev/null || true
import hashlib, json, subprocess
try:
    pins = json.load(open(".claude/verify/pins.json", encoding="utf-8"))["files"]
except Exception:
    print("[baseline] pins.json ausente — rode: python .claude/verify/gen_pins.py")
    raise SystemExit
try:
    b = json.load(open(".claude/verify/boundary.json", encoding="utf-8"))["classes"]
    anchors = [p for c in ("frozen", "generated") for p in b.get(c, {}).get("paths", [])][:2]
except Exception:
    anchors = []
for f in anchors:
    if f not in pins:
        continue
    blob = subprocess.run(["git", "show", f"HEAD:{f}"], capture_output=True).stdout
    if hashlib.sha256(blob).hexdigest() != pins[f]:
        print(f"[baseline] DIVERGENTE em HEAD: {f} — rode: bash .claude/verify/run.sh --stage=baseline")
PY

# (d) idade do último pipeline completo verde
LG=".claude/verify/.last_green"
if [ -f "$LG" ]; then
  AGORA=$(date +%s); ULT=$(head -1 "$LG" 2>/dev/null || echo 0)
  H=$(( (AGORA - ULT) / 3600 ))
  if [ "$H" -ge 24 ]; then
    echo "[verify] Último pipeline completo verde há ${H}h — rode: bash .claude/verify/run.sh"
  else
    echo "[verify] Último pipeline completo verde há ${H}h."
  fi
else
  echo "[verify] Nenhum pipeline completo verde registrado nesta máquina — rode: bash .claude/verify/run.sh"
fi

# (e) fase de PRODUTO (current_phase.json, se o projeto o adotar) + demandas em curso
"$PYBIN" - <<'PY' 2>/dev/null || true
import json
from pathlib import Path
try:
    cp = json.load(open(".claude/verify/current_phase.json", encoding="utf-8"))
    f = cp["fase_corrente"]
    print(f"[produto] Fase {f['id']} {f['status']} · próxima: {cp['proxima_fase']['status']}")
except Exception:
    pass  # opcional — projetos sem fase formal de produto não o têm
DIR = Path(".claude/project-memory/planning-state")
ativos = []
for p in (sorted(DIR.glob("*.json")) if DIR.is_dir() else []):
    try:
        d = json.load(open(p, encoding="utf-8"))
        if d.get("phase") != "done":
            ativos.append(f"{d.get('demanda', p.stem)}:{d.get('phase')}")
    except Exception:
        pass
print("[demanda] " + ("; ".join(ativos) if ativos else "nenhuma em curso — comportamento novo abre via skill new-demand"))
PY
exit 0
