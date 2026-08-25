#!/usr/bin/env bash
# Executor do pipeline declarado em pipeline.yaml (Onda 1: paralelismo real).
#
#   bash .claude/verify/run.sh                   # todos os stages
#   bash .claude/verify/run.sh --stage=baseline  # um stage
#   bash .claude/verify/run.sh --no-mutate       # pula stages que regeneram arquivos
#   bash .claude/verify/run.sh --light           # pula stages heavy (uso do hook Stop)
#
# Ordem: stages sequenciais na ordem declarada; stages parallel:true rodam em
# grupo concorrente quando alcançados. env-doctor com FAIL aborta o pipeline.
# Um run COMPLETO (sem filtros) e verde grava .claude/verify/.last_green
# (epoch + HEAD) — o state-eval injeta a idade a cada prompt.
# Saída: [PASS]/[FAIL] por stage + resumo. Exit = número de stages que falharam.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

PYBIN=python3; command -v python3 >/dev/null 2>&1 || PYBIN=python

FILTRO=""; NO_MUTATE=0; LIGHT=0
for arg in "$@"; do
  case "$arg" in
    --stage=*)   FILTRO="${arg#--stage=}";;
    --no-mutate) NO_MUTATE=1;;
    --light)     LIGHT=1;;
  esac
done

STAGES=$("$PYBIN" - <<'PY'
import re, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
stage, order, data = None, [], {}
for raw in open(".claude/verify/pipeline.yaml", encoding="utf-8"):
    line = raw.rstrip("\n")
    if not line.strip() or line.lstrip().startswith("#") or line.startswith("stages:"):
        continue
    m = re.match(r"^  (\S+):\s*$", line)
    if m:
        stage = m.group(1); data[stage] = {}; order.append(stage); continue
    m = re.match(r"^    (\w+):\s*(.+?)\s*$", line)
    if m and stage:
        k, v = m.groups(); data[stage][k] = v.strip('"')
for s in order:
    d = data[s]
    print("|".join([s,
                    "1" if d.get("parallel") == "true" else "0",
                    "1" if d.get("mutates") == "true" else "0",
                    "1" if d.get("heavy") == "true" else "0",
                    d["run"]]))
PY
) || { echo "pipeline.yaml inválido" >&2; exit 1; }

TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
PASS=0; FAIL=0; ABORT=0
declare -a GRUPO_NOMES=() GRUPO_PIDS=()

executa() { # nome cmd — grava saída e rc em $TMPD
  local nome="$1" cmd="$2"
  cmd="${cmd/#python /$PYBIN }"
  { eval "$cmd" >"$TMPD/$nome.out" 2>&1; echo $? >"$TMPD/$nome.rc"; }
}

reporta() { # nome — imprime resultado acumulado
  local nome="$1" rc
  rc=$(cat "$TMPD/$nome.rc" 2>/dev/null || echo 1)
  if [ "$rc" = "0" ]; then
    PASS=$((PASS+1)); echo "[PASS] $nome"
  else
    FAIL=$((FAIL+1)); echo "[FAIL] $nome"
    sed 's/^/       /' "$TMPD/$nome.out" | head -30
  fi
  return "$rc"
}

drena_grupo() {
  local i
  for i in "${!GRUPO_PIDS[@]}"; do wait "${GRUPO_PIDS[$i]}" 2>/dev/null; done
  for i in "${!GRUPO_NOMES[@]}"; do reporta "${GRUPO_NOMES[$i]}" || true; done
  GRUPO_NOMES=(); GRUPO_PIDS=()
}

while IFS='|' read -r nome par mut heavy cmd; do
  [ "$ABORT" = "1" ] && break
  [ -n "$FILTRO" ] && [ "$nome" != "$FILTRO" ] && continue
  [ "$NO_MUTATE" = "1" ] && [ "$mut" = "1" ] && { echo "[SKIP] $nome (mutates)"; continue; }
  [ "$LIGHT" = "1" ] && [ "$heavy" = "1" ] && { echo "[SKIP] $nome (heavy, --light)"; continue; }
  if [ "$par" = "1" ]; then
    executa "$nome" "$cmd" & GRUPO_NOMES+=("$nome"); GRUPO_PIDS+=($!)
  else
    drena_grupo
    executa "$nome" "$cmd"
    if ! reporta "$nome" && [ "$nome" = "env-doctor" ]; then
      echo "env-doctor FAIL — pipeline abortado (toolchain quebrada)"; ABORT=1
    fi
  fi
done <<< "$STAGES"
drena_grupo

echo "----"
echo "verify: $PASS PASS · $FAIL FAIL"
if [ "$FAIL" = "0" ] && [ -z "$FILTRO" ] && [ "$NO_MUTATE" = "0" ] && [ "$LIGHT" = "0" ]; then
  { date +%s; git rev-parse HEAD 2>/dev/null; } > .claude/verify/.last_green
fi
exit "$FAIL"
