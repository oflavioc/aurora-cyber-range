#!/usr/bin/env bash
# Fecha a Fase 0 somente depois de verificadores, testes negativos, CI,
# branch protection E dos itens 10 e 11 da DoD.
#
# Os itens 10 e 11 exigem PR descartavel comprovando que spec_freeze reprova
# spec+codigo no mesmo PR, e que alteracao so de spec exige titulo
# 'spec-change:'. Este script NAO os executa: ele para antes da tag e instrui
# o operador.
#
# Por que nao automatizar: seria criar PR, esperar CI reprovar, fechar e apagar
# branch — mutacao de remoto que nao pode ser testada antes de rodar de
# verdade. Automacao nao exercitada dentro do unico script que cria a tag de
# imutabilidade e a mesma classe de defeito que a Fase 0 existe para pegar, e
# falha parcial deixaria PR e branch orfaos.
#
# A tag so e criada em uma segunda invocacao explicita:
#
#     bash finalize_phase0.sh --dod-10-11-verificados
#
# Essa flag e a afirmacao do operador de que executou os dois PRs descartaveis
# e viu spec_freeze REPROVAR nos dois. Sem ela, nada e declarado concluido.
set -euo pipefail

CONFIRMA_DOD_10_11=0
case "${1:-}" in
  "") ;;
  --dod-10-11-verificados) CONFIRMA_DOD_10_11=1 ;;
  *)
    echo "Uso: bash finalize_phase0.sh [--dod-10-11-verificados]"
    exit 2
    ;;
esac

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

if [ "$CONFIRMA_DOD_10_11" -eq 0 ]; then
  cat <<INSTRUCOES

================================================================
FASE 0 NAO CONCLUIDA. A tag spec-v1.0 NAO foi criada.
================================================================

CI verde e branch protection aplicada. Faltam os itens 10 e 11 da DoD
(docs/process/PHASE_0_CHECKLIST.md), que este script deliberadamente nao
executa por serem verificacao de comportamento do proprio gate.

Enquanto eles nao forem executados, a spec nao deve virar imutavel: a partir
de spec-v1.0 o mecanismo que a protege passa a valer sem nunca ter sido
demonstrado.

ITEM 10 — spec_freeze deve REPROVAR spec e codigo no mesmo PR

  Os dois arquivos precisam EXISTIR e estar versionados. Nao use contracts/:
  ele e OUTPUT da Fase 1 e hoje esta vazio, entao nao ha o que alterar, e
  'git commit -a' nao estagia arquivo novo. O PR sairia so com docs/spec/,
  reprovaria pela regra do TITULO — que e a do item 11 — e o item 10
  continuaria sem demonstracao.

  tools/ serve porque esta no conjunto CODE e ja tem arquivos versionados.

  git checkout -b dod10-descartavel
  printf '\n<!-- dod10: alteracao descartavel -->\n' >> docs/spec/00_MASTER_SPEC.md
  printf '\n# dod10: alteracao descartavel\n' >> tools/README.md
  git add docs/spec/00_MASTER_SPEC.md tools/README.md
  git commit -m "dod10: PR descartavel, spec e codigo juntos"
  git push -u origin dod10-descartavel
  gh pr create --title "spec-change: dod10 PR descartavel" --body "Verificacao da DoD. Fechar sem merge."

  ESPERADO: spec_freeze FALHA com "PR altera spec e codigo no mesmo PR".
  O titulo leva o prefixo 'spec-change:' DE PROPOSITO: assim a regra do
  titulo nao dispara e a unica reprovacao possivel e a de spec+codigo.
  Confira a mensagem, nao so a cor do job.

  gh pr close dod10-descartavel --delete-branch
  git checkout main && git branch -D dod10-descartavel

ITEM 11 — alteracao so de spec exige titulo 'spec-change:'

  git checkout -b dod11-descartavel
  printf '\n<!-- dod11: alteracao descartavel -->\n' >> docs/spec/00_MASTER_SPEC.md
  git add docs/spec/00_MASTER_SPEC.md
  git commit -m "dod11: PR descartavel, so spec"
  git push -u origin dod11-descartavel
  gh pr create --title "dod11: sem o prefixo exigido" --body "Verificacao da DoD. Fechar sem merge."

  ESPERADO: spec_freeze FALHA exigindo titulo iniciando com 'spec-change:'.
  Aqui nenhum arquivo de codigo e tocado, entao a regra de spec+codigo nao
  dispara e a unica reprovacao possivel e a do titulo.

  gh pr close dod11-descartavel --delete-branch
  git checkout main && git branch -D dod11-descartavel

Os dois PRs sao construidos para que cada um so possa reprovar por UMA das
duas regras. Se a mensagem de reprovacao nao for a esperada, o item nao foi
demonstrado — mesmo com o job vermelho.

Se QUALQUER um dos dois PRs passar no spec_freeze, o gate esta furado: nao
crie a tag e corrija .github/workflows/invariants.yml.

Depois de ver os DOIS reprovarem, rode:

  bash finalize_phase0.sh --dod-10-11-verificados

INSTRUCOES
  exit 0
fi

echo "==> itens 10 e 11 afirmados pelo operador via --dod-10-11-verificados"
echo "==> criando tag somente apos CI + branch protection + DoD 10 e 11"
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
echo "FASE 0 CONCLUIDA: CI verde, main protegida, itens 10 e 11 verificados pelo"
echo "operador e spec-v1.0 publicada."
echo "Rode /doctor no Claude Code antes de iniciar a Fase 1."
