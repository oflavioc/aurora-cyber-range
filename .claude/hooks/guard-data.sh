#!/usr/bin/env bash
# Hook PreToolUse (matcher: Bash) — BLOQUEANTE (exit 2) em `git commit`.
#
# A proibição de commitar dado sensível deixa de ser prosa: padrões sensíveis
# do produto, PDFs novos, segredos e binários grandes são barrados NO COMMIT,
# inclusive em .claude/**.
#
# Padrões DO PRODUTO vêm do manifesto: boundary.json → dados.sensiveis (globs
# fnmatch) e dados.excecoes (globs permitidos, ex.: exemplos sintéticos
# publicados). Os checks genéricos (segredo, PDF novo, binário >200 KB) valem
# sempre.
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

PAYLOAD="$(cat)"
CMD="$(payload_get '.tool_input.command')"
case "$CMD" in *"git commit"*) ;; *) exit 0;; esac

cd "$(project_root)" 2>/dev/null || exit 0
STAGED=$(git diff --cached --name-only 2>/dev/null) || exit 0
[ -z "$STAGED" ] && exit 0

FALHAS=$(STAGED="$STAGED" "$PYBIN" - <<'PY'
import fnmatch, json, os, re, subprocess
staged = [s for s in os.environ["STAGED"].splitlines() if s]
falhas = []
SECRET = re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.|sk-[A-Za-z0-9]{20,}|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY-----|sshpass -p")

try:
    dados = json.load(open(".claude/verify/boundary.json", encoding="utf-8")).get("dados", {})
except Exception:
    dados = {}
sensiveis = dados.get("sensiveis", [])
excecoes = dados.get("excecoes", [])

def in_head(f):
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{f}"], capture_output=True).returncode == 0

for f in staged:
    low = f.lower().replace("\\", "/")
    # 1 · padrão sensível declarado pelo produto (menos as exceções nominais)
    if any(fnmatch.fnmatch(low, g) for g in sensiveis) and not any(fnmatch.fnmatch(low, g) for g in excecoes):
        falhas.append(f"padrão sensível do produto: {f}")
    # 2 · PDF novo (dado de cliente potencial) — evidência entra só por promoção (R11)
    if low.endswith(".pdf") and not in_head(f):
        falhas.append(f"PDF novo: {f} (evidência entra por promoção curada, nunca por commit direto)")
    # 3 · segredos em texto
    blob = subprocess.run(["git", "show", f":0:{f}"], capture_output=True).stdout
    if b"\x00" not in blob[:8000] and SECRET.search(blob.decode("utf-8", errors="ignore")):
        falhas.append(f"padrão de segredo em: {f}")
    # 4 · binário novo > 200 KB
    if b"\x00" in blob[:8000] and len(blob) > 200 * 1024 and not in_head(f):
        falhas.append(f"binário novo de {len(blob)//1024} KB: {f} (>200 KB — use o evidence store, R11)")
print("\n".join(falhas))
PY
)

[ -z "$FALHAS" ] && exit 0
{
  echo "guard-data: commit BLOQUEADO —"
  printf '%s\n' "$FALHAS" | sed 's/^/  · /'
  echo "Regra: dados reais vivem fora deste clone; evidência entra por promoção (R11)."
} >&2
exit 2
