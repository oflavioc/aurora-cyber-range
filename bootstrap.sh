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

# GUARDA DE BRANCH — recusa commit direto na branch default.
#
# Vai para .git/hooks/, e nao para ~/.claude/: e hook do GIT, nao do agente.
# Guarda LOCAL, nao gate: quem clonar sem rodar este script nao o tem, e
# `--no-verify` o contorna por desenho. A protecao real de main e a branch
# protection do GitHub.
mkdir -p .git/hooks
cp user-scope/hooks/pre-commit             .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "==> smoke test do guarda de branch"
if ! git -c core.hooksPath=.git/hooks hook run pre-commit >/dev/null 2>&1; then
  echo "    OK: pre-commit recusa commit na branch default"
else
  echo "    (na branch atual o guarda libera — esperado fora da default)"
fi

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
# NAO AFIRMA EM QUE FASE O PROJETO ESTA.
#
# A versao anterior dizia "Proxima tarefa da Fase 0: implementar os SEIS
# verificadores" e mandava rodar finalize_phase0.sh. Era verdade quando foi
# escrita, e envelheceu duas fases atras — os seis existem desde a Fase 0 e a
# Fase 1 fechou. E a classe da secao 1.6 do registro da Fase 1, no lugar mais
# visivel que existe: a primeira coisa que um clone novo le.
#
# O conserto duravel nao e atualizar o texto a cada fase. E apontar para onde o
# estado mora, em vez de repeti-lo aqui.
echo "Onde esta o projeto agora:"
echo "  docs/progress/     registro por fase, com pendencias e o que a proxima herda"
echo "  docs/spec/07_IMPLEMENTATION_PHASES.md   roadmap e a Definition of Done de cada fase"
echo
echo "Comece lendo o registro da ULTIMA fase concluida: a secao final dele"
echo "e o inventario do que a fase seguinte recebe."
echo
echo "IMPORTANTE: abra o Claude Code com  claude --permission-mode default"
echo "e aceite o dialogo de confianca do workspace na primeira vez, para que os"
echo "hooks de projeto em .claude/settings.json passem a valer."
