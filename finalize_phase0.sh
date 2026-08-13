#!/usr/bin/env bash
# Fecha a Fase 0 somente depois de verificadores, testes negativos, CI e branch protection.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$ROOT" ]; then
  echo "ERRO: execute dentro do repositorio Git do AURORA."
  exit 1
fi
cd "$ROOT"

REQUIRED=(
  tools/check_core_boundary.py
  tools/check_contract_literals.py
  tools/check_event_envelope.py
  tools/check_security_constraints.py
  tools/check_synthetic_data.py
  tools/codegen.py
)

for file in "${REQUIRED[@]}"; do
  if [ ! -f "$file" ]; then
    echo "ERRO: falta $file"
    exit 1
  fi
done

for file in docs/spec/00_MASTER_SPEC.md CLAUDE.md .claude/settings.json .github/workflows/invariants.yml; do
  [ -f "$file" ] || { echo "ERRO: falta $file"; exit 1; }
done

# O auditor e seu hook vivem em escopo de usuario, fora do repositorio.
for file in "$HOME/.claude/agents/checkpoint-auditor.md" "$HOME/.claude/hooks/readonly_bash.py"; do
  [ -f "$file" ] || { echo "ERRO: falta $file — rode: bash bootstrap.sh"; exit 1; }
done

python -m json.tool .claude/settings.json >/dev/null

echo "==> verificadores em arvore limpa"
python tools/check_core_boundary.py
python tools/check_contract_literals.py
python tools/check_event_envelope.py
python tools/check_security_constraints.py
python tools/check_synthetic_data.py
python tools/codegen.py --check

echo "==> testes negativos independentes"
python scripts/phase0_negative_tests.py

echo "==> smoke tests de hooks"
set +e
printf '%s\n' '{"cwd":"'"$ROOT"'","tool_input":{"file_path":"range-core/x.py","content":"from domains.academus import Y"}}' | python .claude/hooks/check_architecture.py >/dev/null 2>&1
RC1=$?
printf '%s\n' '{"cwd":"'"$ROOT"'","tool_input":{"command":"rm -rf range-core"}}' | python "$HOME/.claude/hooks/readonly_bash.py" >/dev/null 2>&1
RC2=$?
printf '%s\n' '{"cwd":"'"$ROOT"'","tool_input":{"file_path":"range-core/nope.py","content":"x = 1"}}' | python .claude/hooks/scenario_scope.py >/dev/null 2>&1
RC3=$?
set -e

[ "$RC1" -eq 2 ] || { echo "ERRO: check_architecture hook nao bloqueou probe (rc=$RC1)"; exit 1; }
[ "$RC2" -eq 2 ] || { echo "ERRO: readonly_bash hook nao bloqueou probe (rc=$RC2)"; exit 1; }
[ "$RC3" -eq 2 ] || { echo "ERRO: scenario_scope hook nao bloqueou probe (rc=$RC3)"; exit 1; }

if ! gh auth status >/dev/null 2>&1; then
  echo "ERRO: gh nao autenticado"
  exit 1
fi

REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
if [ -z "$REPO" ]; then
  echo "ERRO: nao foi possivel resolver o repositorio GitHub."
  exit 1
fi

echo "==> commit candidato da Fase 0"
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  git add -A
  git commit -m "fase-0: specification freeze"
fi

# Repositorio novo pode estar em master/unborn antes do primeiro commit.
git branch -M main
HEAD_SHA=$(git rev-parse HEAD)

PROTECTED=0
if gh api "repos/$REPO/branches/main/protection" >/dev/null 2>&1; then
  PROTECTED=1
fi

echo "==> push de main (tag ainda NAO e criada)"
if [ "$PROTECTED" -eq 1 ] && ! git diff --quiet origin/main HEAD 2>/dev/null; then
  echo "ERRO: main ja esta protegida e ha commits locais nao publicados."
  echo "A Fase 0 ja foi fechada antes. Publique via Pull Request, nao por push direto."
  exit 1
fi
git push -u origin main

echo "==> aguardando CI do commit $HEAD_SHA"
RUN_ID=""
for _ in $(seq 1 30); do
  RUN_ID=$(gh run list --workflow invariants.yml --branch main --limit 20 \
    --json databaseId,headSha \
    --jq '.[] | select(.headSha == "'"$HEAD_SHA"'") | .databaseId' | head -n 1)
  [ -n "$RUN_ID" ] && break
  sleep 2
done

if [ -z "$RUN_ID" ]; then
  echo "ERRO: workflow invariantes nao apareceu para o commit atual."
  exit 1
fi

gh run watch "$RUN_ID" --exit-status

echo "==> aplicando branch protection em $REPO:main"
if ! gh api --method PUT -H "Accept: application/vnd.github+json" \
  "repos/$REPO/branches/main/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["arquitetura", "spec_freeze", "seguranca"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
then
  echo "ERRO: branch protection nao foi aplicada."
  echo "A Fase 0 NAO esta concluida e a tag NAO sera criada."
  echo "Verifique permissao/plano do GitHub ou configure a protecao manualmente e rode este script de novo."
  exit 1
fi

echo "==> alinhando metodos de merge com required_linear_history"
gh repo edit "$REPO" \
  --enable-merge-commit=false \
  --enable-squash-merge=true \
  --enable-rebase-merge=true >/dev/null \
  || echo "AVISO: ajuste manualmente Settings > General > Pull Requests (desligar merge commit)."

echo "==> criando tag somente apos CI + branch protection"
if git rev-parse -q --verify refs/tags/spec-v1.0 >/dev/null; then
  TAG_SHA=$(git rev-list -n 1 spec-v1.0)
  if [ "$TAG_SHA" != "$HEAD_SHA" ]; then
    echo "ERRO: spec-v1.0 ja existe apontando para outro commit ($TAG_SHA)."
    exit 1
  fi
else
  git tag -a spec-v1.0 -m "Specification freeze v1.0"
fi

git push origin spec-v1.0

echo
echo "FASE 0 CONCLUIDA: CI verde, main protegida e spec-v1.0 publicada."
echo "Rode /doctor no Claude Code antes de iniciar a Fase 1."
