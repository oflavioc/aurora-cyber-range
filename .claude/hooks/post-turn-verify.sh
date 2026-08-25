#!/usr/bin/env bash
# Hook Stop — BLOQUEANTE (exit 2 devolve o resumo ao agente para corrigir).
#
# Ao fim do turno, se houver mudança não commitada em superfície de produto
# ou de estrutura, roda os stages leves e não-mutantes do pipeline.
# Anti-loop: stop_hook_active (sinal do harness) + lockfile de 120s.
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

PAYLOAD="$(cat)"
[ "$(payload_get '.stop_hook_active')" = "true" ] && exit 0

PROJ=$(basename "$(project_root)" 2>/dev/null || echo projeto)
LOCK="${TMPDIR:-/tmp}/post-turn-verify-${PROJ}.lock"
AGORA=$(date +%s)
if [ -f "$LOCK" ]; then
  ULTIMO=$(cat "$LOCK" 2>/dev/null || echo 0)
  [ $((AGORA - ULTIMO)) -lt 120 ] && exit 0
fi
echo "$AGORA" > "$LOCK"

cd "$(project_root)" 2>/dev/null || exit 0

MUDOU=$(git status --porcelain 2>/dev/null | grep -E '\.(js|ts|py|css|html|json|yaml|yml|sh)$' || true)
[ -z "$MUDOU" ] && exit 0

SAIDA=$(bash .claude/verify/run.sh --light --no-mutate 2>&1); RC=$?
if [ "$RC" -ne 0 ]; then
  {
    echo "post-turn-verify: o pipeline leve FALHOU com mudanças não commitadas no turno."
    echo "$SAIDA" | grep -E '^\[FAIL\]|^       ' | head -25
    echo "Corrija antes de encerrar — ou declare explicitamente o estado ao usuário."
  } >&2
  exit 2
fi
exit 0
