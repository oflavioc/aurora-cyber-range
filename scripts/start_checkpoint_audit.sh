#!/usr/bin/env bash
# Auditoria formal: contexto fresco, worktree preso ao commit candidato.
# O agente checkpoint-auditor vive em ~/.claude/agents/ (escopo de usuario), nao
# no repositorio: hooks de frontmatter de agente de PROJETO so rodam apos o
# dialogo de confianca da pasta, e um auditor definido pelo commit que ele
# audita e um auditor comprometivel.
#
# A CAPTURA DO RELATORIO VIVE AQUI, nao no hook SubagentStop. O auditor e
# invocado como agente de TOPO (`claude --agent`), e SubagentStop so dispara
# para subagente despachado pela ferramenta Agent dentro de uma sessao: o evento
# nunca ocorre por este caminho. Ver scripts/audit_report.py.
set -euo pipefail

PHASE=""
MODE=interactive
for arg in "$@"; do
  case "$arg" in
    --headless) MODE=headless ;;
    *)
      if [ -z "$PHASE" ]; then PHASE="$arg"; else
        echo "ERRO: argumento inesperado: $arg" >&2
        exit 2
      fi
      ;;
  esac
done

if ! [[ "$PHASE" =~ ^[0-9]+$ ]]; then
  echo "Uso: bash scripts/start_checkpoint_audit.sh <numero-da-fase> [--headless]"
  echo
  echo "  (padrao)     sessao INTERATIVA: voce acompanha e pode intervir."
  echo "  --headless   sessao nao-interativa (-p), para CI. Nada abre na tela."
  exit 2
fi

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "ERRO: working tree nao esta limpo. Crie o commit candidato antes da auditoria."
  exit 1
fi

HEAD_SHA=$(git rev-parse HEAD)

# ---------------------------------------------------------------------------
# P2-16 — A BASE DE COMPARACAO E `origin/main` ATUALIZADO, e nao `main` local.
#
# A auditoria da Fase 2 emitiu um HIGH que nao procedia: a branch "alterava spec
# e codigo no mesmo diff". O calculo do proprio `spec_freeze` era a prova do
# contrario — contra `origin/main`, SPEC=0 e CODE=26; contra o `main` local, que
# estava tres commits atras, SPEC=6. O gate roda contra
# `github.event.pull_request.base.sha`, que e o primeiro.
#
# O custo de um HIGH inventado e uma rodada inteira, e o defeito se REPETE em
# todo checkpoint cuja branch tenha mergeado um `spec-change` — porque a branch
# sempre estara a frente de um `main` local que ninguem atualizou.
#
# Saida (a) da pendencia: quem fixa a base e o LANCADOR, e nao o auditor. A
# mesma natureza de decisao que ja o faz fixar o commit candidato — mecanismo
# que depende de o auditor lembrar de fazer a coisa certa nao e mecanismo.
# ---------------------------------------------------------------------------
BASE_REF="origin/main"
if git remote get-url origin >/dev/null 2>&1; then
  echo "Atualizando refs de origin para fixar a base de comparacao..."
  if ! git fetch --quiet origin main 2>/dev/null; then
    echo "AVISO: 'git fetch origin main' falhou. A base pode estar desatualizada." >&2
  fi
else
  # Sem remoto, `main` local e a unica base que existe. Declarado em vez de
  # silencioso: o auditor precisa saber contra o que esta comparando.
  BASE_REF="main"
  echo "AVISO: nao ha remoto 'origin'. Base de comparacao: 'main' LOCAL." >&2
fi

if ! BASE_SHA=$(git rev-parse --verify --quiet "$BASE_REF^{commit}"); then
  echo "ERRO: nao foi possivel resolver '$BASE_REF'. Sem base, o diff nao tem sentido." >&2
  exit 1
fi

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

# Identificador da sessao PRE-ATRIBUIDO. Sem isto o relatorio so seria
# localizavel por heuristica ("arquivo mais recente do diretorio") — origem das
# tres confusoes de ID da Fase 0.
SESSION_ID=$(python -c 'import uuid; print(uuid.uuid4())')

# ---------------------------------------------------------------------------
# P2-19 — A STACK EFEMERA, para o auditor EXECUTAR o que antes ele pulava.
#
# Doze testes pulam sem servico: a persistencia, o criterio de reinicio de
# `06` T3, a deteccao de reescrita por cadeia de hash, a contiguidade de
# `sequence`, os dois escritores concorrentes, e a projecao materializada. O CI
# cobre tudo isso, e o auditor LIA o workflow sem poder executa-lo — metade de
# dois itens de DoD verificada por leitura e configuracao.
#
# Saida (a), decidida pelo operador: o lancador sobe a stack e EXPORTA as duas
# variaveis. A saida (b) — o auditor consultar o CI por `gh` — foi recusada
# porque poria rede na allowlist do julgador, que e superficie permanente para
# resolver um problema de uma vez.
#
# AS VARIAVEIS SAO EXPORTADAS, e nao passadas na linha de comando. O
# `readonly_bash` so admite tres prefixos de ambiente inline, de proposito: um
# hook que aceitasse qualquer `VAR=valor` deixaria o auditor apontar a suite
# para qualquer lugar. Exportadas aqui, elas sao decisao do LANCADOR, e o
# auditor apenas herda o ambiente.
#
# `docker-compose.audit.yml` tem portas proprias e NAO tem volume: apontar a
# auditoria para o compose do projeto faria a suite truncar a tabela de eventos
# do banco de desenvolvimento, que e o que o nome `AURORA_TEST_*` avisa.
# ---------------------------------------------------------------------------
STACK_ATIVA=0
# O compose DO WORKTREE, e nao o da arvore principal: e o commit candidato
# que esta sendo auditado, e a stack dele faz parte do que se audita.
COMPOSE_AUDIT="$WT/docker-compose.audit.yml"
# PROJETO PROPRIO. Sem `-p`, o compose deriva o nome do diretorio, que e o
# mesmo do `docker-compose.yml`, e reconcilia os dois arquivos como uma stack
# so: a primeira execucao recriou e depois removeu o Redis de
# desenvolvimento. Achado rodando o lancador, e nao lendo.
PROJETO_AUDIT="aurora-audit"
AURORA_AUDIT_DB="postgresql+psycopg://aurora_audit:efemero-da-auditoria@127.0.0.1:15432/aurora_audit"

derruba_stack() {
  [ "$STACK_ATIVA" = "1" ] || return 0
  STACK_ATIVA=0
  docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" down --remove-orphans >/dev/null 2>&1 || true
}

# `--wait` exige compose v2.1.1+. Versao antiga cai no ramo "AUSENTES",
# que e o comportamento certo: melhor declarar que nao subiu do que
# seguir com servico ainda subindo e colher falha intermitente.
if docker compose version >/dev/null 2>&1 && [ -f "$COMPOSE_AUDIT" ]; then
  echo "Subindo a stack efemera da auditoria (Postgres + Redis)..."
  if docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" up -d --wait >/dev/null 2>&1; then
    STACK_ATIVA=1
    # A migration le `DATABASE_URL`; os testes leem `AURORA_TEST_*`. Sao duas
    # variaveis de proposito, e o CI faz exatamente isto.
    if DATABASE_URL="$AURORA_AUDIT_DB" python -m alembic upgrade head >/dev/null 2>&1; then
      export AURORA_TEST_DATABASE_URL="$AURORA_AUDIT_DB"
      export AURORA_TEST_REDIS_URL="redis://127.0.0.1:16379/1"
      SERVICOS="ATIVOS — Postgres e Redis efemeros no ar, migration aplicada. Os testes que dependem de servico VAO RODAR; skip aqui e defeito, nao ausencia de ambiente."
    else
      derruba_stack
      SERVICOS="AUSENTES — a stack subiu e 'alembic upgrade head' falhou. Os testes de Postgres e Redis vao PULAR."
      echo "AVISO: migration falhou; seguindo sem servicos." >&2
    fi
  else
    SERVICOS="AUSENTES — 'docker compose up' falhou. Os testes de Postgres e Redis vao PULAR."
    echo "AVISO: nao foi possivel subir a stack efemera; seguindo sem ela." >&2
  fi
else
  SERVICOS="AUSENTES — nao ha Docker nesta maquina. Os testes de Postgres e Redis vao PULAR."
  echo "AVISO: Docker nao encontrado; a auditoria roda sem os servicos." >&2
fi

RAW=""
if [ "$MODE" = headless ]; then
  RAW=$(mktemp)
fi

# Estado do lancamento gravado ANTES da sessao. E o que torna a captura
# recuperavel: fechar a janela do auditor mata o processo sem executar trap
# nenhuma, entao NENHUM codigo posterior a sessao roda. Com o estado em disco, a
# captura perdida vira um comando; sem ele, vira transcricao manual.
python "$ROOT/scripts/audit_report.py" --begin \
  --root "$ROOT" --session-id "$SESSION_ID" --phase "$PHASE" \
  --head-sha "$HEAD_SHA" --mode "$MODE" ${RAW:+--fallback-text "$RAW"}

CLAUDE_RC=""
CAPTURA_FEITA=0

capturar() {
  [ "$CAPTURA_FEITA" = "1" ] && return 0
  CAPTURA_FEITA=1
  # A stack efemera morre com a auditoria. Antes da captura, para que a saida
  # do relatorio seja a ultima coisa impressa.
  derruba_stack
  [ -n "$RAW" ] && rm -f "$RAW" 2>/dev/null
  # Sessao nem comecou: nada a capturar.
  [ -z "$CLAUDE_RC" ] && return 0
  python "$ROOT/scripts/audit_report.py" --recover --via launcher-trap --launcher-exit "$CLAUDE_RC"
  CAPTURE_RC=$?
  # A sessao tem precedencia: se o auditor falhou, esse e o erro a propagar.
  [ "$CLAUDE_RC" -ne 0 ] && exit "$CLAUDE_RC"
  # Auditoria rodou mas o relatorio nao foi capturado. audit_report.py ja
  # imprimiu o aviso; o codigo 3 distingue esta falha da falha da sessao.
  [ "$CAPTURE_RC" -ne 0 ] && exit 3
  exit 0
}
# Cobre saida normal, /exit e Ctrl+C. NAO cobre fechar a janela — dai o --recover.
trap capturar EXIT INT TERM

echo "Auditoria Fase $PHASE — commit $HEAD_SHA"
echo "Base de comparacao: $BASE_SHA ($BASE_REF)"
echo "Servicos: $SERVICOS"
echo "Worktree de auditoria: $WT"
if [ "$MODE" = headless ]; then
  echo "Modo: HEADLESS (-p). NENHUMA sessao interativa vai abrir; isto e esperado."
else
  echo "Modo: INTERATIVA. A sessao vai abrir — acompanhe e intervenha se precisar."
fi
echo "session_id: $SESSION_ID"
echo
echo "======================================================================"
echo "  NAO FECHE A JANELA DO AUDITOR NO X. Isso mata o processo sem deixar"
echo "  a captura rodar, e o relatorio nao e gravado. Saia com /exit."
echo
echo "  Se a janela for fechada assim mesmo, recupere o relatorio com:"
echo
echo "      python scripts/audit_report.py --recover"
echo
echo "  O comando funciona enquanto o transcript da sessao existir."
echo "======================================================================"
echo

# O PROMPT CARREGA A BASE E O ESTADO DOS SERVICOS.
#
# "diff contra main" era a formulacao anterior, e ela era o proprio defeito da
# P2-16: deixava a resolucao de `main` para o auditor, dentro de um worktree
# cujos refs locais podem estar atras. Agora a base e um SHA ja resolvido.
#
# E o estado dos servicos vai junto porque o auditor precisa saber se um `skip`
# que ele veja e ausencia de ambiente ou defeito da fase — sem isso, os dois
# sao indistinguiveis para quem le a saida.
PROMPT="Audite a Fase $PHASE. Este checkout esta fixado no commit candidato $HEAD_SHA. Compare contra a base $BASE_SHA ($BASE_REF, atualizado agora pelo lancador) — nao resolva 'main' por conta propria, os refs locais deste worktree podem estar atras. Servicos: $SERVICOS Leia spec + diff + testes reais e emita o formato obrigatorio PASS/FAIL. Nao corrija nada."

set +e
if [ "$MODE" = headless ]; then
  # Em headless o stdout JA e o relatorio; o `tee` guarda uma copia que serve de
  # fallback se a leitura do transcript falhar. Em interativa nao ha pipe: canalizar
  # o stdout converteria a sessao em nao-interativa (`claude --help`).
  claude -p --output-format text \
    --session-id "$SESSION_ID" --agent checkpoint-auditor --permission-mode default \
    "$PROMPT" | tee "$RAW"
  CLAUDE_RC=${PIPESTATUS[0]}
else
  claude --session-id "$SESSION_ID" --agent checkpoint-auditor --permission-mode default \
    "$PROMPT"
  CLAUDE_RC=$?
fi
set -e

# A captura roda pela trap, para cobrir tambem /exit e Ctrl+C.
capturar
