#!/usr/bin/env bash
# Auditoria formal: contexto fresco, worktree preso ao commit candidato.
# O agente checkpoint-auditor vive em ~/.claude/agents/ (escopo de usuario), nao
# no repositorio: hooks de frontmatter de agente de PROJETO so rodam apos o
# dialogo de confianca da pasta, e um auditor definido pelo commit que ele
# audita e um auditor comprometivel.
set -euo pipefail

PHASE=${1:-}
if ! [[ "$PHASE" =~ ^[0-9]+$ ]]; then
  echo "Uso: bash scripts/start_checkpoint_audit.sh <numero-da-fase>"
  exit 2
fi

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "ERRO: working tree nao esta limpo. Crie o commit candidato antes da auditoria."
  exit 1
fi

HEAD_SHA=$(git rev-parse HEAD)
mkdir -p .aurora-worktrees
# Caminho FIXO de proposito. A confianca de workspace do Claude Code e por
# caminho: um diretorio novo a cada auditoria seria sempre nao-confiado, e os
# hooks de nivel de projeto seriam silenciosamente pulados.
WT="$ROOT/.aurora-worktrees/audit"

# O worktree NAO e removido ao final: manter o caminho preserva a confianca de
# workspace e permite reler o checkout auditado. Ele e recriado a cada execucao.
trap - EXIT INT TERM

git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || true
git -C "$ROOT" worktree prune >/dev/null 2>&1 || true
rm -rf "$WT"
git worktree add --detach "$WT" "$HEAD_SHA" >/dev/null
cd "$WT"

echo "Auditoria Fase $PHASE — commit $HEAD_SHA"
echo "Worktree de auditoria: $WT"
echo

set +e
claude --agent checkpoint-auditor --permission-mode default \
  "Audite a Fase $PHASE. Este checkout esta fixado no commit candidato $HEAD_SHA. Leia spec + diff contra main + testes reais e emita o formato obrigatorio PASS/FAIL. Nao corrija nada."
CLAUDE_RC=$?
set -e

mkdir -p "$ROOT/docs/progress"
printf '{"ts":"%s","phase":%s,"head_sha":"%s","launcher_exit":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PHASE" "$HEAD_SHA" "$CLAUDE_RC" \
  >> "$ROOT/docs/progress/audit_log.jsonl"

exit "$CLAUDE_RC"
