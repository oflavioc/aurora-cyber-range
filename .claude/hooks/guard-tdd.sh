#!/usr/bin/env bash
# Hook PreToolUse (matcher: Write|Edit) — BLOQUEANTE (exit 2). Onda 3.
#
# Módulo de PRODUTO só é editado com red provado (ou waiver auditável) na
# demanda em curso. Hook que só avisa é a versão nova do gate morto — este
# bloqueia, e as válvulas são explícitas: tipagem de tarefa (R3) e tdd_waiver
# no planning-state (listado pelo compliance a cada execução).
#
# O QUE é módulo de produto vem do MANIFESTO: boundary.json → produto.globs
# (lista de padrões fnmatch sobre o caminho relativo, / normalizado).
# Lista vazia/ausente = guard desativado (Ondas 0–2).
#
# Fora do alcance deste guard: docs, specs, .claude/**, testes (escrever teste
# É a fase red), fixtures. Frozen/generated já são do guard-boundary.
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

PAYLOAD="$(cat)"
ARQ="$(payload_get '.tool_input.file_path')"
[ -z "$ARQ" ] && exit 0

cd "$(project_root)" 2>/dev/null || exit 0

VER=$(PAYLOAD="" ARQ="$ARQ" "$PYBIN" - <<'PY'
import fnmatch, json, os
from pathlib import Path

arq = os.environ["ARQ"].replace("\\", "/")
root = os.getcwd().replace("\\", "/").rstrip("/")
if arq.startswith(root + "/"):
    arq = arq[len(root) + 1:]

try:
    globs = json.load(open(".claude/verify/boundary.json", encoding="utf-8")).get("produto", {}).get("globs", [])
except Exception:
    globs = []
if not globs or not any(fnmatch.fnmatch(arq, g) for g in globs):
    print("FORA_DE_ESCOPO")
    raise SystemExit

DIR = Path(".claude/project-memory/planning-state")
ativos = []
for f in (sorted(DIR.glob("*.json")) if DIR.is_dir() else []):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if d.get("phase") in ("red", "implement", "validate"):
        red = d.get("red") or {}
        ok = (red.get("status") == "proven" and red.get("commit")) or ("tdd_waiver" in d)
        ativos.append((d.get("demanda", f.stem), ok))
if not ativos:
    print("SEM_DEMANDA")
elif any(ok for _, ok in ativos):
    print("LIBERADO")
else:
    print("SEM_RED|" + ", ".join(n for n, _ in ativos))
PY
)

case "$VER" in
  FORA_DE_ESCOPO|LIBERADO) exit 0;;
  SEM_DEMANDA)
    {
      echo "guard-tdd: edição de módulo de produto BLOQUEADA — nenhuma demanda ativa."
      echo "Rito: abra a demanda (skill new-demand) ou, para correção de achado, um planning-state"
      echo "de fix-finding com red provado (R3). Tarefas doc/refactor/chore: registre tdd_waiver."
    } >&2
    exit 2;;
  SEM_RED*)
    {
      echo "guard-tdd: edição de módulo de produto BLOQUEADA — demanda ativa sem red provado."
      echo "Demanda(s): ${VER#SEM_RED|}"
      echo "Rito (R3): o qa-engineer prova e COMMITA o red primeiro (fase 4); ou registre"
      echo "tdd_waiver {motivo, data} no planning-state — o compliance-audit lista todos."
    } >&2
    exit 2;;
  *) exit 0;;
esac
