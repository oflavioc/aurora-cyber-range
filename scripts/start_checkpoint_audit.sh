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
BASE_EXPLICITA=""
ESPERANDO_BASE=0
for arg in "$@"; do
  if [ "$ESPERANDO_BASE" = "1" ]; then
    BASE_EXPLICITA="$arg"
    ESPERANDO_BASE=0
    continue
  fi
  case "$arg" in
    --headless) MODE=headless ;;
    --base) ESPERANDO_BASE=1 ;;
    --base=*) BASE_EXPLICITA="${arg#--base=}" ;;
    *)
      if [ -z "$PHASE" ]; then PHASE="$arg"; else
        echo "ERRO: argumento inesperado: $arg" >&2
        exit 2
      fi
      ;;
  esac
done

if [ "$ESPERANDO_BASE" = "1" ]; then
  echo "ERRO: --base exige um ref." >&2
  exit 2
fi

if ! [[ "$PHASE" =~ ^[0-9]+$ ]]; then
  echo "Uso: bash scripts/start_checkpoint_audit.sh <numero-da-fase> [--headless] [--base <ref>]"
  echo
  echo "  (padrao)     sessao INTERATIVA: voce acompanha e pode intervir."
  echo "  --headless   sessao nao-interativa (-p), para CI. Nada abre na tela."
  echo "  --base <ref> base de comparacao explicita. So use para auditar um"
  echo "               commit JA mergeado — e veja o aviso que o script emite."
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
# A BRANCH DEFAULT E RESOLVIDA SEMPRE, mesmo com `--base` explicito. Sao duas
# perguntas diferentes e elas nao se substituem: `--base` decide O QUE O AUDITOR
# VE; a branch default decide SE A AUDITORIA AINDA E PORTA. Confundir as duas
# fazia a guarda declarar "porta" com a fase mergeada, bastando passar a propria
# ancora como base — achado rodando o comando antes de entrega-lo.
DEFAULT_REF="origin/main"
if git remote get-url origin >/dev/null 2>&1; then
  echo "Atualizando refs de origin para fixar a base de comparacao..."
  if ! git fetch --quiet origin main 2>/dev/null; then
    echo "AVISO: 'git fetch origin main' falhou. A base pode estar desatualizada." >&2
  fi
else
  # Sem remoto, `main` local e a unica base que existe. Declarado em vez de
  # silencioso: o auditor precisa saber contra o que esta comparando.
  DEFAULT_REF="main"
  echo "AVISO: nao ha remoto 'origin'. Branch default: 'main' LOCAL." >&2
fi

if ! DEFAULT_SHA=$(git rev-parse --verify --quiet "$DEFAULT_REF^{commit}"); then
  echo "ERRO: nao foi possivel resolver '$DEFAULT_REF'. Sem branch default nao da" >&2
  echo "      para dizer se a auditoria e porta ou laudo." >&2
  exit 1
fi

BASE_REF="${BASE_EXPLICITA:-$DEFAULT_REF}"
if [ -n "$BASE_EXPLICITA" ]; then
  echo "Base de comparacao EXPLICITA: $BASE_REF (branch default: $DEFAULT_REF)"
fi

if ! BASE_SHA=$(git rev-parse --verify --quiet "$BASE_REF^{commit}"); then
  echo "ERRO: nao foi possivel resolver '$BASE_REF'. Sem base, o diff nao tem sentido." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# A BASE MOSTRA O TRABALHO DA FASE? — O TERCEIRO PREDICADO, e o segundo esta
# aqui embaixo como historia porque ele errou de um jeito util.
#
# O primeiro nao existia: a base vinha vazia e o auditor improvisava em
# silencio (H1 da primeira auditoria da Fase 3). O segundo perguntava
# `git merge-base --is-ancestor HEAD BASE` — "o candidato esta contido na
# base?" —, que e `BASE == HEAD` e pouco mais. A inversao que de fato acontece
# e merge PECA A PECA: com cinco das seis pecas da Fase 3 em `main`, o
# candidato NAO estava contido na base, a guarda nao disparou, e o diff
# entregue ao auditor nao continha nenhum dos quatro itens da DoD. Foi o H2 da
# segunda auditoria, medido na propria sessao que o encontrou.
#
# Os dois erraram do mesmo jeito: DEGRADARAM PARA "OK" QUANDO NAO SABIAM. O
# terceiro recusa quando nao sabe — ancora ausente, ancora que nao resolve,
# ancora que nao e ancestral do candidato, todas recusam.
#
# O predicado inteiro vive em `scripts/check_audit_base.py`, com os sete eixos
# de prova negativa em `scripts/check_audit_base_probes.py`. Nao mora aqui de
# proposito: guarda que so o lancador executa e guarda que ninguem testa, e
# esta precisa de repositorios sinteticos para ser exercida.
#
# Continua ANTES do worktree e ANTES do Docker: recusar depois de subir
# Postgres e Redis seria recusar caro.
# ---------------------------------------------------------------------------
echo "Conferindo se a auditoria da Fase $PHASE ainda e porta (default: $DEFAULT_REF)..."
GUARDA=(python "$ROOT/scripts/check_audit_base.py"
        --phase "$PHASE" --default "$DEFAULT_SHA" --head "$HEAD_SHA" --repo "$ROOT")
if [ -n "$BASE_EXPLICITA" ]; then
  # `--base` NAO entra na avaliacao: ele so declara que o operador escolheu
  # outra base, o que troca recusa por aviso. O veredito segue sendo contra a
  # branch default.
  GUARDA+=(--base "$BASE_SHA")
fi
# A SAIDA DA GUARDA E CAPTURADA, e nao so impressa. Ela entra no PROMPT: o
# veredito "porta ou laudo" e informacao que o AUDITOR precisa para saber o que
# esta julgando. Na terceira rodada da Fase 3 ele deduziu "porta" da AUSENCIA do
# bloco de aviso no prompt — o aviso ia para o stderr e morria ali, e ele
# auditou como gate o que era laudo. Declaracao que existe e nao chega a quem
# decide com ela e a terceira ocorrencia desta forma na fase; ver 7.3.1.
set +e
GUARDA_SAIDA=$("${GUARDA[@]}" 2>&1)
GUARDA_RC=$?
set -e
echo "$GUARDA_SAIDA"
if [ "$GUARDA_RC" != "0" ]; then
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

# ---------------------------------------------------------------------------
# P3-4 — O NUCLEO EXECUTADO TEM DE VIR DESTE CHECKOUT.
#
# Medido antes desta correcao, com o CWD no worktree: `domains` e `contracts`
# resolviam pelo worktree e `range_core` resolvia pela ARVORE PRINCIPAL. A
# instalacao editavel grava caminho ABSOLUTO, e `range-core/` tem hifen — nao e
# importavel pela arvore, entao nao ha CWD que corrija. O auditor executava o
# adapter e os testes do commit candidato contra o nucleo de outro commit, e o
# resultado parecia normal.
#
# Ate a Fase 3 isso nao mordia por construcao: a auditoria rodava depois do
# merge, e os dois lados coincidiam. A Fase 4 e a primeira auditada ANTES do
# merge — os dois SHAs sao diferentes de verdade, e um commit na arvore
# principal durante a auditoria trocaria o nucleo sob os testes do auditor.
#
# A metade que prova e `tests/test_procedencia_dos_pacotes.py`. Esta e a metade
# que faz a prova passar: um venv proprio, com a arvore AUDITADA instalada.
#
# FORA DO WORKTREE, em `.aurora-worktrees/venv`: o worktree E o objeto da
# auditoria, e um diretorio de 100 MB no meio dele apareceria em toda listagem
# que o auditor fizesse. `.aurora-worktrees/` ja e ignorado pelo Git.
#
# RECRIADO A CADA RODADA. Venv reaproveitado carrega as dependencias do commit
# ANTERIOR — a mesma classe de defeito que esta correcao existe para fechar,
# entrando pela porta das dependencias em vez da do codigo.
#
# FALHA ALTO, e isto e o ponto: auditoria que roda contra o nucleo da arvore
# principal porque o pip falhou em silencio e pior que auditoria que nao roda.
# Sem rede, sem venv; sem venv, sem auditoria.
#
# A REDE E DO LANCADOR, E NAO DO AUDITOR. Esta linha e a mesma que a P2-19
# decidiu ao recusar `gh` na allowlist do julgador: quem prepara o ambiente tem
# rede, quem emite o veredito nao. Ver docs/process/WORKFLOW.md.
# ---------------------------------------------------------------------------
VENV="$ROOT/.aurora-worktrees/venv"
echo "Criando o venv da auditoria e instalando a arvore auditada (P3-4)..."
rm -rf "$VENV"
if ! python -m venv "$VENV" >/dev/null 2>&1; then
  echo "ERRO: nao foi possivel criar o venv em $VENV." >&2
  echo "      Sem ele, o nucleo executado viria da arvore principal." >&2
  exit 1
fi
VENV_BIN="$VENV/bin"
[ -x "$VENV/Scripts/python.exe" ] && VENV_BIN="$VENV/Scripts"
# CAMINHO RELATIVO NUM SUBSHELL, e nao `-e "$WT[test]"`: medido, o pip recusa a
# forma com caminho absoluto e extra — *"is not a valid editable requirement"* —,
# e a recusa so aparece rodando. O `cd` fica dentro do subshell para nao mexer no
# diretorio de quem chama.
if ! ( cd "$WT" && "$VENV_BIN/python" -m pip install --disable-pip-version-check \
       -e ".[test]" -c constraints.txt ) >"$VENV/pip.log" 2>&1; then
  echo "ERRO: a instalacao editavel do checkout auditado FALHOU." >&2
  echo "      Ultimas linhas de $VENV/pip.log:" >&2
  tail -n 15 "$VENV/pip.log" >&2
  echo >&2
  echo "      A auditoria PARA aqui, de proposito. Seguir sem esta instalacao" >&2
  echo "      faria os testes do commit candidato rodarem contra o nucleo da" >&2
  echo "      arvore principal — que e exatamente a P3-4." >&2
  exit 1
fi
export PATH="$VENV_BIN:$PATH"
export VIRTUAL_ENV="$VENV"
echo "Venv da auditoria: $VENV (python de $VENV_BIN)"

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
#
# O VEREDITO DA GUARDA VAI VERBATIM, e nao resumido: porta e laudo mudam o que um
# BLOCKER significa, e na terceira rodada o auditor teve de DEDUZIR qual era —
# pela ausencia do bloco de aviso, que nunca chegava ate aqui.
PROMPT="Audite a Fase $PHASE. Este checkout esta fixado no commit candidato $HEAD_SHA. Compare contra a base $BASE_SHA ($BASE_REF, atualizado agora pelo lancador) — nao resolva 'main' por conta propria, os refs locais deste worktree podem estar atras. Servicos: $SERVICOS

VEREDITO DA GUARDA DE BASE, verbatim do lancador. Porta ou laudo esta DITO aqui, e nao deve ser deduzido do que o prompt deixa de conter:
$GUARDA_SAIDA

Leia spec + diff + testes reais e emita o formato obrigatorio PASS/FAIL. Nao corrija nada."

set +e
if [ "$MODE" = headless ]; then
  # Em headless o stdout JA e o relatorio; o `tee` guarda uma copia que serve de
  # fallback se a leitura do transcript falhar. Em interativa nao ha pipe: canalizar
  # o stdout converteria a sessao em nao-interativa (`claude --help`).
  claude -p --output-format text \
    --session-id "$SESSION_ID" --agent checkpoint-auditor \
    --allowedTools Bash --permission-mode default \
    "$PROMPT" | tee "$RAW"
  CLAUDE_RC=${PIPESTATUS[0]}
else
  # `--allowedTools` E VARIADICO (`<tools...>` no `claude --help`): ele engole
  # todos os argumentos seguintes que nao comecem com `-`. Posto imediatamente
  # antes de "$PROMPT", ele consumia o PROMPT como se fosse nome de ferramenta, e
  # a sessao morria com "Input must be provided either through stdin or as a
  # prompt argument". Por isso ele vem ANTES de `--permission-mode`: a flag
  # seguinte fecha a lista variadica, e o prompt volta a ser operando.
  claude --session-id "$SESSION_ID" --agent checkpoint-auditor \
    --allowedTools Bash --permission-mode default \
    "$PROMPT"
  CLAUDE_RC=$?
fi
set -e

# A captura roda pela trap, para cobrir tambem /exit e Ctrl+C.
capturar
