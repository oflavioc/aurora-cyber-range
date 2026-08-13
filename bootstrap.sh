#!/usr/bin/env bash
# Prepara a Fase 0. Nao commita, nao faz push, nao cria tag e nao protege branch.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$ROOT" ]; then
  echo "ERRO: execute dentro do repositorio Git do AURORA."
  exit 1
fi
cd "$ROOT"

mkdir -p docs/spec docs/progress docs/process .claude/agents .claude/hooks .github/workflows tools scripts
mkdir -p contracts range-core domains scenarios

if [ ! -f docs/spec/00_MASTER_SPEC.md ]; then
  echo "FALTA: docs/spec/00_MASTER_SPEC.md"
  echo "Copie os documentos 00..09 + KICKOFF_PROMPT.md para docs/spec/ antes de continuar."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERRO: GitHub CLI nao esta autenticado. Rode: gh auth login"
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERRO: remote origin nao configurado."
  exit 1
fi

python -m json.tool .claude/settings.json >/dev/null

echo "==> instalando auditor em escopo de usuario"
# O checkpoint-auditor NAO vive no repositorio de proposito:
#  - hooks de frontmatter de agente de PROJETO so rodam apos o dialogo de
#    confianca da pasta; cada worktree de auditoria seria nao-confiado e o
#    hook readonly_bash seria silenciosamente pulado;
#  - um auditor definido pelo commit que ele audita e comprometivel.
mkdir -p "$HOME/.claude/agents" "$HOME/.claude/hooks"
cp user-scope/agents/checkpoint-auditor.md "$HOME/.claude/agents/checkpoint-auditor.md"
cp user-scope/hooks/readonly_bash.py       "$HOME/.claude/hooks/readonly_bash.py"

echo "==> smoke test do hook do auditor"
if ! printf '%s\n' '{"tool_input":{"command":"rm -rf range-core"}}' \
     | python "$HOME/.claude/hooks/readonly_bash.py" >/dev/null 2>&1; then
  echo "    OK: readonly_bash bloqueia escrita"
else
  echo "ERRO: readonly_bash nao bloqueou 'rm -rf'."
  exit 1
fi

echo "Bootstrap validado. Nenhum commit/push/tag foi executado."
echo
echo "Proxima tarefa da Fase 0: implementar os SEIS verificadores em tools/:"
echo "  check_core_boundary.py"
echo "  check_contract_literals.py"
echo "  check_event_envelope.py"
echo "  check_security_constraints.py"
echo "  check_synthetic_data.py"
echo "  codegen.py (--check)"
echo
echo "Depois execute o checklist e somente entao: bash finalize_phase0.sh"
echo
echo "IMPORTANTE: abra o Claude Code com  claude --permission-mode default"
echo "e aceite o dialogo de confianca do workspace na primeira vez, para que os"
echo "hooks de projeto em .claude/settings.json passem a valer."
