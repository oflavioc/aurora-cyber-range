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

# A ARVORE DO CANDIDATO — P7-2. As duas provas gravadas passaram a declarar o
# hash da ARVORE, e nao o SHA do commit, porque o `gh pr merge --rebase` que
# fecha a fase reescreve todo SHA e nao toca no conteudo.
#
# O `HEAD_SHA` acima NAO some, e a divisao e por natureza: ele continua sendo o
# que identifica o commit candidato para o `git worktree add`, para a guarda de
# base — que julga TOPOLOGIA, e topologia e historia — e para o registro da
# rodada. O `HEAD_TREE` e o que identifica o OBJETO MEDIDO, e e ele que aparece
# dentro dos artefatos de prova.
HEAD_TREE=$(git rev-parse "HEAD^{tree}")

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

# ---------------------------------------------------------------------------
# P6-9 — A COPIA INSTALADA DO ESCOPO DE USUARIO E SINCRONIZADA AQUI.
#
# `bootstrap.sh` copia tres arquivos versionados para `~/.claude/`, e ninguem os
# mantinha em dia depois disso. A copia e a que o Claude Code EXECUTA: sem esta
# etapa, o auditor abre constrangido por um hook que nao e o que a arvore
# declara. Ocorreu tres vezes, e as tres remediacoes foram manuais.
#
# AQUI, E NAO EM OUTRO LUGAR, por duas razoes de ordem:
#
#   DEPOIS DA GUARDA DE BASE  ela e a ultima coisa barata. Sincronizar antes
#                             gastaria escrita fora da arvore numa auditoria que
#                             a guarda vai recusar.
#   ANTES DO WORKTREE         montar worktree, venv e stack e o trabalho caro.
#                             Falhar a sincronia depois deles desperdicaria tudo.
#
# ESTE E O UNICO PONTO EM QUE O LANCADOR ESCREVE FORA DA ARVORE. Ate aqui ele so
# tocava `.aurora-worktrees/`, o worktree e `docs/progress/`. O custo esta aceito
# e declarado na P6-9; as guardas sao as do `bootstrap.sh`, que e o precedente —
# destino derivado, escrita so quando diverge, e smoke test depois.
#
# FALHA ALTO. Nao ha ramo de "segue sem sincronizar": ele reabriria a pendencia
# no exato momento em que ela custa mais.
#
# O python e o NU, da arvore principal, como `check_audit_base.py`: esta etapa e
# stdlib pura e roda ANTES de o venv da auditoria existir.
# ---------------------------------------------------------------------------
echo "Sincronizando a copia instalada do escopo de usuario (P6-9)..."
if ! python "$ROOT/scripts/sincroniza_escopo_de_usuario.py"; then
  echo "ERRO: a auditoria NAO segue com o escopo de usuario dessincronizado." >&2
  echo "      O auditor rodaria constrangido por um hook que nao e o da arvore." >&2
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
# DENTRO DO WORKTREE, em `.aurora-audit/venv` — e isto INVERTE a decisao
# anterior, que o punha em `.aurora-worktrees/venv`.
#
# A RAZAO DE ANTES CONTINUA VERDADEIRA, e por isso ela fica escrita: o worktree
# E o objeto da auditoria, e um diretorio de 100 MB no meio dele aparece em
# listagem. O que estava errado nao era a razao — era a conclusao.
#
# Venv descartavel dentro do worktree e INSTRUMENTO, e nao objeto auditado.
# `git status` no worktree segue limpo (`.gitignore` cobre `.aurora-audit/`), e
# o prefixo com ponto o tira do `ls` sem `-a`. O que se ganha em troca e o que
# faltava: o interpretador passa a ser ALCANCAVEL pelo auditor.
#
# O B1 DA FASE 6, e ele e reincidencia por outra porta. `export PATH` nao chega
# a ferramenta de Bash do auditor: ela nasce num shell novo a cada chamada,
# inicializado pelo perfil, e `python` resolve para o interpretador da maquina —
# medido. Com o venv aqui, a invocacao e por caminho relativo, que
# `readonly_bash.py` admite em forma exata e que `_alvo_nao_contido` trata como
# contido porque o cwd E o worktree.
#
# O `export PATH` ABAIXO CONTINUA, e nao e redundancia: ele serve ao proprio
# lancador e a qualquer processo que ele inicie no mesmo shell. O que ele nao
# faz — e agora esta dito — e atravessar para a ferramenta do auditor.
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
INSTRUMENTOS="$WT/.aurora-audit"
mkdir -p "$INSTRUMENTOS"
VENV="$INSTRUMENTOS/venv"
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
# O EXPORT VALE PARA QUEM HERDA O AMBIENTE, E NAO PARA ESTE SCRIPT — H1 da
# quinta auditoria, e a frase esta aqui porque a suposicao contraria ja custou
# uma rodada.
#
# MEDIDO no Git Bash desta maquina: `$VENV_BIN` e `C:/...` — vem de
# `git rev-parse --show-toplevel`, que devolve caminho Windows — e `PATH` e
# separado por DOIS-PONTOS. A entrada e partida em `C` e `/Projetos/...`, e
# nenhuma das duas e o venv: `command -v` com a forma Windows na frente NAO acha
# o executavel, e com a forma POSIX acha.
#
# A regra que sai daqui, e ela nao depende de lembrar: TODA chamada deste script
# que precise da aplicacao instalada usa `"$VENV_BIN/python"` EXPLICITO. As que
# usam `python` nu sao stdlib puro, da arvore PRINCIPAL, e estao assim de
# proposito — `check_audit_base.py`, o `uuid` da sessao e o `audit_report.py`.
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

# ---------------------------------------------------------------------------
# O DIAGNOSTICO DA STACK, E POR QUE ELE EXISTE — a rodada de 17/08/2026.
#
# A auditoria do commit `3a5ee71` rodou com `alembic upgrade head` falhando: a
# stack subiu, a migration nao, e 73 dos 335 testes PULARAM — 22% da suite, na
# rodada que decidia a fase mais importante do projeto. O auditor declarou o
# fato e emitiu PASS, que e o comportamento certo dele.
#
# O DEFEITO ESTAVA AQUI. As duas etapas mandavam a saida para `/dev/null`, e o
# ramo de falha chamava `derruba_stack` logo em seguida: a causa morria duas
# vezes — uma no descarte, outra na remocao dos containers que a explicariam.
# Tudo o que sobrou foi a frase "migration falhou".
#
# E ELA NAO FOI REPRODUZIVEL. Depois da rodada, a stack foi subida e a migration
# rodada DUAS vezes — da arvore principal e de dentro do worktree, com o python
# do venv da auditoria —, e as duas saiam `rc=0`, aplicando as duas revisoes.
# **Nao reproduzivel com a informacao que sobrou** e o dado que justifica este
# bloco: sem ele, nao ha como distinguir corrida de porta, bind transitorio e
# defeito de verdade, e cada hipotese custa uma rodada de auditoria inteira.
#
# E A MESMA LICAO QUE A PECA 7 JA APRENDEU NO CI, com o preco maior aqui: la, o
# `container aurora-range-api exited (1)` sem log custava um job vermelho que se
# reroda; aqui custa uma rodada DEGRADADA que ainda assim emite veredito.
#
# DUAS PROPRIEDADES, e as duas foram exigidas pelo operador porque cada uma
# fecha um caminho pelo qual a causa morreria assim mesmo:
#
#   1. IMPRIME ANTES DE `derruba_stack`. Invertida a ordem, o `ps` e o `logs`
#      medem containers que ja nao existem, e o resultado e um arquivo vazio —
#      a mesma perda por outro caminho.
#   2. APARECE QUANDO O LANCADOR SEGUE, e nao so quando ele aborta. Esta falha
#      e de severidade BAIXA por decisao (WORKFLOW.md: falha alto o que faria o
#      veredito falar de outra coisa; falha baixo o que faria o veredito dizer
#      menos) — entao o caminho em que ela aparece e, sempre, o de seguir.
#
# O arquivo fica em `.aurora-audit/`, DENTRO do worktree — invertido junto com o
# venv, e pela mesma razao levada ate o fim: diagnostico FORA DO ALCANCE DE QUEM
# DIAGNOSTICA e a mesma familia do defeito que o venv tinha.
#
# `_alvo_nao_contido` recusa leitura absoluta fora do worktree, entao um
# `stack.log` em `.aurora-worktrees/` era um arquivo que o lancador escrevia
# para o auditor ler e que o auditor nao podia ler. A mensagem de erro apontava
# para ele, o que e pior que nao apontar para lugar nenhum.
# ---------------------------------------------------------------------------
STACK_LOG="$INSTRUMENTOS/stack.log"
rm -f "$STACK_LOG"

diagnostica_stack() {
  MOTIVO="$1"
  # A CAUSA VAI PARA A TELA PRIMEIRO, e ela e o que JA esta no log: a saida do
  # comando que falhou. Anexar `ps` e `logs` antes de imprimir empurraria o
  # traceback para fora da janela do `tail` — MEDIDO na primeira execucao deste
  # bloco: 205 linhas no arquivo, com a causa na 133, e o `tail -30` mostrando
  # boot de Postgres. Diagnostico que existe e nao chega a quem le e a mesma
  # perda, com mais passos.
  echo "AVISO: $MOTIVO. A auditoria SEGUE, e os testes de servico vao PULAR." >&2
  echo "       A causa, do proprio comando que falhou:" >&2
  echo "       ---------------------------------------------------------------" >&2
  tail -n 25 "$STACK_LOG" >&2 || true
  echo "       ---------------------------------------------------------------" >&2
  # O ESTADO DOS CONTAINERS vai para o arquivo, e ANTES de `derruba_stack`:
  # depois dela, `ps` e `logs` medem containers que ja nao existem.
  {
    echo "=== $MOTIVO"
    echo "--- docker compose ps --all"
    docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" ps --all 2>&1 || true
    echo "--- docker compose logs --tail 60"
    docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" logs --no-color --tail 60 2>&1 || true
  } >>"$STACK_LOG" 2>&1 || true
  echo "       Estado dos containers e log completo em: $STACK_LOG" >&2
}

# `--wait` exige compose v2.1.1+. Versao antiga cai no ramo "AUSENTES",
# que e o comportamento certo: melhor declarar que nao subiu do que
# seguir com servico ainda subindo e colher falha intermitente.
if docker compose version >/dev/null 2>&1 && [ -f "$COMPOSE_AUDIT" ]; then
  echo "Subindo a stack efemera da auditoria (Postgres + Redis)..."
  if docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" up -d --wait >>"$STACK_LOG" 2>&1; then
    STACK_ATIVA=1
    # A migration le `DATABASE_URL`; os testes leem `AURORA_TEST_*`. Sao duas
    # variaveis de proposito, e o CI faz exatamente isto.
    #
    # O PYTHON E O DO VENV, EXPLICITO — H1 da quinta auditoria. Esta linha dizia
    # `python` nu, contando com o `export PATH` de mais acima, e o export E
    # INERTE NO WINDOWS: `$VENV_BIN` vem de `git rev-parse --show-toplevel`, que
    # devolve `C:/...`, e `PATH` e separado por DOIS-PONTOS — a entrada e partida
    # em `C` e `/Projetos/...`, e nenhuma das duas e o venv. Medido: com a forma
    # Windows na frente do `PATH`, `command -v` NAO acha o executavel; com a
    # forma POSIX, acha.
    #
    # Entao `alembic` rodava no interpretador da MAQUINA, sem a aplicacao
    # instalada, e falhava — e a falha degrada para `SERVICOS=AUSENTES`. Os 140
    # testes de servico PULAVAM com Postgres e Redis no ar e saudaveis, e o
    # veredito saia dizendo menos sem que nada estivesse errado no commit.
    if DATABASE_URL="$AURORA_AUDIT_DB" "$VENV_BIN/python" -m alembic upgrade head \
       >>"$STACK_LOG" 2>&1; then
      export AURORA_TEST_DATABASE_URL="$AURORA_AUDIT_DB"
      export AURORA_TEST_REDIS_URL="redis://127.0.0.1:16379/1"
      SERVICOS="ATIVOS — Postgres e Redis efemeros no ar, migration aplicada. Os testes que dependem de servico VAO RODAR; skip aqui e defeito, nao ausencia de ambiente."
    else
      # O DIAGNOSTICO VEM ANTES DA DERRUBADA. Invertido, o `logs` mede
      # containers removidos e a causa morre pelo caminho que este bloco
      # existe para fechar.
      diagnostica_stack "a stack subiu e 'alembic upgrade head' FALHOU"
      derruba_stack
      SERVICOS="AUSENTES — a stack subiu e 'alembic upgrade head' falhou. Os testes de Postgres e Redis vao PULAR. Diagnostico em $STACK_LOG."
    fi
  else
    diagnostica_stack "'docker compose up --wait' FALHOU"
    SERVICOS="AUSENTES — 'docker compose up' falhou. Os testes de Postgres e Redis vao PULAR. Diagnostico em $STACK_LOG."
  fi
else
  SERVICOS="AUSENTES — nao ha Docker nesta maquina. Os testes de Postgres e Redis vao PULAR."
  echo "AVISO: Docker nao encontrado; a auditoria roda sem os servicos." >&2
fi

# ---------------------------------------------------------------------------
# P4-10 — AS PROVAS DE CONTAINER, RODADAS AQUI PORQUE O AUDITOR NAO PODE RODA-LAS.
#
# Itens 1 e 4 da DoD da Fase 4 — o DEMO ponta a ponta e o reinicio do CONTAINER
# do engine. Os dois exigem Docker e uma stack no ar, e `docker` esta fora da
# allowlist do julgador pelo argumento da P2-19. Na primeira auditoria desta fase
# os dois chegaram ao veredito como NAO VERIFICADO.
#
# E a MESMA saida que a P2-19 ja escolheu uma vez, e a que a P3-4 seguiu depois:
# o que exige rede acontece AQUI, antes da sessao, e o resultado chega pronto.
#
# O QUE SEPARA ISTO DE ATESTACAO E O HASH DA ARVORE — P7-2. O arquivo gravado
# carrega `git rev-parse HEAD^{tree}`, e `scripts/check_provas_de_container.py` —
# que o auditor roda, e que esta na allowlist — REPROVA se ele nao for o do
# worktree que se julga. O auditor continua nao tendo visto rodar; o que muda e
# que a evidencia esta amarrada ao objeto. A condicao e forte por mecanica e nao
# por confianca: um arquivo versionado nao contem o hash da arvore que o contem,
# porque rastrea-lo muda a arvore que ele teria de declarar.
#
# ANTES ERA O SHA DO COMMIT, e a troca fecha um defeito do RITO e nao um bug: o
# `gh pr merge --rebase` que fecha a fase reescreve todo SHA, entao toda prova
# amarrada ao commit morria em todo fechamento. A arvore atravessa.
#
# FALHA BAIXO, AO CONTRARIO DO VENV. A P3-4 para a auditoria porque sem o venv o
# veredito sairia sobre OUTRO nucleo — errado, e nao incompleto. Aqui, sem as
# provas os itens 1 e 4 voltam a ser NAO VERIFICADO, que e a opcao C da P4-10 e e
# honesto. Derrubar a auditoria inteira por falta de Docker trocaria um veredito
# parcial por nenhum.
#
# O PYTHON E O DO VENV: as provas importam `websockets` e falam com o Postgres
# do commit auditado. Rodar com o interpretador do ambiente reintroduziria a
# P3-4 pela porta das provas.
# ---------------------------------------------------------------------------
echo "Rodando as provas de container do commit auditado (P4-10)..."
set +e
PROVAS_SAIDA=$("$VENV_BIN/python" "$WT/scripts/grava_provas_de_container.py" \
               --worktree "$WT" --python "$VENV_BIN/python" 2>&1)
PROVAS_RC=$?
set -e
if [ "$PROVAS_RC" = "0" ]; then
  PROVAS="GRAVADAS e VERDES sobre a arvore $HEAD_TREE (commit $HEAD_SHA). Rode 'python scripts/check_provas_de_container.py' — ele confere o hash da arvore e imprime a saida integra das duas provas."
else
  echo "$PROVAS_SAIDA" >&2
  echo "AVISO: as provas de container nao passaram (rc=$PROVAS_RC)." >&2
  PROVAS="NAO PASSARAM (rc=$PROVAS_RC). Rode 'python scripts/check_provas_de_container.py': ele recusa e imprime o motivo. Enquanto ele recusar, os itens 1 e 4 da DoD sao NAO VERIFICADO — nunca PASS por silencio."
fi

# ---------------------------------------------------------------------------
# A COPIA DA PROVA DO SEED — H1 da terceira auditoria da Fase 5.
#
# CHAMAVA-SE "transporte" ate a P7-2, e o nome carregava um estado que nao existe
# mais: enquanto a prova nomeava o commit, "TRANSPORTADA" era o aviso de que
# divergencia era o caso NORMAL depois de um fechamento de fase. Amarrada a
# arvore, uma prova do mesmo conteudo simplesmente vale. O que resta e uma copia
# de arquivo, e e so isso que o nome precisa dizer.
#
# `check_prova_do_seed.py` entrou na allowlist do auditor COMO SE FUNCIONASSE, e
# nasceu inalcancavel: o artefato e gravado na raiz da arvore de quem mede, o
# worktree de auditoria e criado do zero a partir do commit, e o lancador
# transportava apenas as provas de container. O gate reprovaria em TODA auditoria
# futura — desta fase e das proximas —, por ausencia de um arquivo que nunca
# chegava ali.
#
# O gemeo funciona porque recebeu o transporte; este nao o tinha. A licao e a de
# sempre nesta linhagem, e desta vez ela custou um BLOCKER de sintoma: mecanismo
# admitido sem o caminho pelo qual ele e exercido e mecanismo que so parece
# existir.
#
# COPIA INCONDICIONAL, e a decisao e deliberada: se a prova for de outro commit,
# quem recusa e o verificador — com a arvore gravada ao lado da arvore do
# checkout, que e a leitura que o auditor precisa ver. Filtrar aqui trocaria
# "prova de outro conteudo" por "prova ausente", e as duas mensagens dizem coisas
# diferentes.
#
# AUSENCIA NAO ABORTA, pelo mesmo criterio das provas de container: falha alto o
# que faria o veredito falar de outra coisa; falha baixo o que faria o veredito
# dizer menos. Sem a prova, os itens 1 e 2 da DoD ficam NAO VERIFICADO — e o
# verificador diz isso com todas as letras, em vez de o lancador decidir por ele.
#
# ELE FICA, E DEIXA DE SER O CAMINHO NORMAL — a decisao que a Forma B abaixo
# exigia, com o motivo escrito. Com a medicao acontecendo aqui dentro, o artefato
# NASCE no worktree e sobrescreve o que for copiado por esta etapa. A copia passa
# a ser o caminho DEGRADADO: e o que sobra quando nao ha Docker nesta maquina, e
# a medicao de quem mediu fora continua valendo — o verificador a aceita ou a
# recusa pelo hash da arvore, exatamente como antes. Remove-la trocaria um
# veredito parcial por nenhum na unica situacao em que ela ainda serve.
#
# E DESDE A P7-2 ELA VALE MAIS VEZES: enquanto a prova nomeava o commit, uma
# medicao feita fora praticamente sempre divergia, porque qualquer commit novo a
# invalidava. Nomeando a arvore, ela vale sempre que o CONTEUDO for o mesmo.
#
# E ELE VEM ANTES DA MEDICAO, e nao depois: invertida a ordem, uma copia velha
# sobrescreveria a medicao recem-feita deste commit — que e o defeito que a
# Forma B existe para fechar, entrando pela porta do fallback.
# ---------------------------------------------------------------------------
PROVA_SEED=".aurora-prova-do-seed.json"
SEED_ORIGEM="ausente"
if [ -f "$ROOT/$PROVA_SEED" ]; then
  cp "$ROOT/$PROVA_SEED" "$WT/$PROVA_SEED"
  SEED_ORIGEM="transportada"
fi

# ---------------------------------------------------------------------------
# A MEDICAO DO SEED COMPLETO, FEITA AQUI — Forma B, decidida pelo operador.
#
# O PROBLEMA ERA UM LACO, e ele esta medido: enquanto a prova carregava o SHA do
# checkout, medir, registrar o numero e commitar INVALIDAVA a propria medicao —
# aconteceu duas vezes antes de eu entender o que o mecanismo exigia. A saida
# procedimental existia — "medir por ultimo, depois de o codigo estar congelado" —
# e e disciplina.
#
# E DISCIPLINA NAO SEGURA. A §9.6 do registro daquela fase e a prova pela pior via:
# a correcao herdou o defeito da coisa corrigida, no mesmo turno, escrita por quem
# tinha acabado de descrever o defeito. Tres voltas confirmaram. Entao o vinculo
# deixou de ser procedimental e virou ESTRUTURAL: a medicao acontece aqui, contra
# o worktree congelado, e nao ha "antes" em que esquecer.
#
# O LACO EM SI MORREU NA P7-2, e vale dizer por que esta etapa continua de pe. A
# prova passou a nomear a ARVORE: commitar so a invalida se um arquivo RASTREADO
# mudar, entao "medir -> registrar -> commitar" nao se auto-invalida mais. O que
# mantem a medicao aqui nao e mais o laco — e o custo: Postgres, banco
# descartavel e ~5 min, que e o mesmo argumento da P4-10.
#
# E O PRECEDENTE E A P4-10, inteiro. As provas de container funcionam por esta
# forma exata — o que exige rede, volume e minutos acontece no lancador, fora da
# sessao do julgador, e o resultado chega pronto e amarrado ao objeto por hash. A
# Forma A sozinha (nenhum numero de medicao no registro) tira a ambiguidade do
# texto e deixa o laco de pe; as duas juntas o fecham.
#
# BANCO PROPRIO, E NAO O DA STACK. `prova_seed_completo.py` TRUNCA as vinte
# tabelas DUAS vezes — e por isso exige `AURORA_SEED_DATABASE_URL` em vez de
# `DATABASE_URL`, que e a mesma disciplina do `AURORA_TEST_*`. Aponta-lo para
# `aurora_audit` destruiria o banco em que a suite do auditor vai rodar, na mesma
# sessao. O banco nasce e morre dentro do MESMO servidor efemero: `docker compose
# down` o leva junto, porque o compose da auditoria nao tem volume.
#
# `CREATE ROLE` EXIGE `CREATEROLE`, e aqui existe: `aurora_audit` e a
# `POSTGRES_USER` da imagem, entao e superusuaria do cluster. A `0004` cria
# `academus_app` num `DO` que trata `insufficient_privilege` e explica a saida no
# proprio erro — medido na peca 3. A role e objeto de CLUSTER: se a migration do
# `aurora_audit` ja a criou, esta aqui so faz o `GRANT`.
#
# DEPOIS DO `git worktree add`, E CONTRA O WORKTREE. As tres coisas que isso fixa
# nao sao a mesma: a migration aplicada e a do commit auditado; o codigo medido e
# o do commit auditado; e `prova_seed_completo.py` grava o artefato na raiz da
# arvore de onde ELE foi executado — que passa a ser o worktree — com o SHA que
# `git -C` resolve ali, que e o candidato. As tres saem do mesmo `$WT`.
#
# O `RANDOM_SEED` E FIXO AQUI, pelo mesmo argumento do `grava_provas_de_container`:
# a seed governa determinismo, e uma seed que mudasse a cada rodada faria o item 2
# comparar duas rodadas de uma medicao que nao e comparavel com a anterior. Ela
# nao e credencial e nao sai do lancador.
#
# FALHA BAIXO, como as provas de container e ao contrario do venv: sem a medicao
# os itens 1 e 2 voltam a NAO VERIFICADO, que e honesto. E a falha DIZ POR QUE —
# `.aurora-audit/seed.log`, mesma decisao do `diagnostica_stack`: degradar e
# decisao, degradar em silencio e defeito.
# ---------------------------------------------------------------------------
SEED_DB="aurora_seed"
AURORA_SEED_DB="postgresql+psycopg://aurora_audit:efemero-da-auditoria@127.0.0.1:15432/$SEED_DB"
SEED_RANDOM="20260818"
SEED_LOG="$INSTRUMENTOS/seed.log"
MEDE_MOTIVO=""
rm -f "$SEED_LOG"

psql_efemero() {
  docker compose -p "$PROJETO_AUDIT" -f "$COMPOSE_AUDIT" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U aurora_audit -d postgres -c "$1"
}

mede_seed() {
  # RECRIADO A CADA RODADA, pelo mesmo motivo do venv: banco reaproveitado
  # carrega o esquema do commit anterior, e a medicao sairia sobre outra coisa.
  if ! psql_efemero "DROP DATABASE IF EXISTS $SEED_DB" >>"$SEED_LOG" 2>&1; then
    echo "nao foi possivel remover o banco anterior '$SEED_DB'"
    return 1
  fi
  if ! psql_efemero "CREATE DATABASE $SEED_DB" >>"$SEED_LOG" 2>&1; then
    echo "nao foi possivel criar o banco descartavel '$SEED_DB'"
    return 1
  fi
  # A migration DO COMMIT AUDITADO, com o python do venv EXPLICITO.
  #
  # O IRMAO DO H1 DA QUINTA AUDITORIA, e ele estava escondido atras do primeiro:
  # `mede_seed` so roda com `STACK_ATIVA=1`, e a stack so ficava ativa se a
  # migration de cima passasse — que era justamente o que nao passava. Consertar
  # so o sitio achado teria feito este falhar na rodada seguinte, com a mesma
  # causa e outro sintoma.
  #
  # O comentario anterior afirmava que *"o `python` do PATH ja e o do venv da
  # P3-4"*. Era falso no Windows pelo motivo escrito la em cima: entrada de PATH
  # em forma `C:/...` nao resolve num PATH separado por dois-pontos.
  if ! DATABASE_URL="$AURORA_SEED_DB" "$VENV_BIN/python" -m alembic upgrade head \
       >>"$SEED_LOG" 2>&1; then
    echo "'alembic upgrade head' FALHOU no banco da medicao"
    return 1
  fi
  # `PYTHONIOENCODING` pelo mesmo motivo do gravador de container: a saida tem
  # acento, e no Windows o Python escreve na codepage do locale.
  if ! AURORA_SEED_DATABASE_URL="$AURORA_SEED_DB" \
       RANDOM_SEED="$SEED_RANDOM" \
       PYTHONIOENCODING=utf-8 \
       "$VENV_BIN/python" "$WT/scripts/prova_seed_completo.py" \
       >>"$SEED_LOG" 2>&1; then
    echo "a medicao rodou e saiu diferente de zero"
    return 1
  fi
  return 0
}

if [ "$STACK_ATIVA" = "1" ]; then
  echo "Medindo o seed completo do commit auditado (~5 min; Forma B da Fase 5)..."
  set +e
  MEDE_MOTIVO=$(mede_seed)
  MEDE_RC=$?
  set -e
  if [ "$MEDE_RC" = "0" ]; then
    SEED_ORIGEM="medida"
  else
    # A CAUSA VAI PARA A TELA, e ela e o fim do log — a mesma correcao que a
    # primeira execucao do `diagnostica_stack` exigiu: diagnostico que existe e
    # nao chega a quem le e a mesma perda com mais passos.
    echo "AVISO: a medicao do seed NAO completou: $MEDE_MOTIVO." >&2
    echo "       A auditoria SEGUE. A causa, do proprio comando que falhou:" >&2
    echo "       ---------------------------------------------------------------" >&2
    tail -n 25 "$SEED_LOG" >&2 || true
    echo "       ---------------------------------------------------------------" >&2
    echo "       Log completo em: $SEED_LOG" >&2
    # DUAS FALHAS DIFERENTES, e a mensagem nao pode confundi-las. Se o artefato
    # DESTA ARVORE foi escrito, a medicao ACONTECEU e um dos dois itens
    # REPROVOU — `prova_seed_completo.py` grava mesmo quando falha, de proposito,
    # porque e assim que "falhou" se distingue de "ninguem rodou". Se nao foi
    # escrito, a medicao nao chegou ao fim, e o que vale e o que a copia deixou
    # ali. Chamar a primeira de "copiada" faria o auditor ler divergencia de
    # objeto onde o fato e defeito da fase.
    #
    # E O QUE SE PROCURA E A ARVORE, e nao o SHA — P7-2. Esta linha le o VALOR do
    # campo que o gravador escreve; enquanto ele era `commit`, procurar
    # `$HEAD_SHA` funcionava. Com o campo passando a ser `tree`, procurar o SHA
    # aqui nunca casaria: o lancador leria toda medicao REPROVADA como "nao
    # completou", e o auditor receberia "nao mediu" onde o fato e "mediu e
    # falhou". Predicado que erra o rotulo da falha e pior que predicado ausente.
    if grep -q "\"$HEAD_TREE\"" "$WT/$PROVA_SEED" 2>/dev/null; then
      SEED_ORIGEM="reprovou"
    fi
  fi
else
  echo "AVISO: sem a stack efemera nao ha Postgres para medir o seed." >&2
  MEDE_MOTIVO="a stack efemera nao esta no ar"
fi

case "$SEED_ORIGEM" in
  medida)
    SEED_PROVA="MEDIDA PELO LANCADOR neste worktree, sobre a arvore $HEAD_TREE, com banco descartavel proprio. Rode 'python scripts/check_prova_do_seed.py' — ele confere o hash da arvore gravado contra o deste checkout e imprime a medicao integra."
    ;;
  reprovou)
    SEED_PROVA="MEDIDA PELO LANCADOR neste worktree, sobre a arvore $HEAD_TREE, e REPROVOU. O artefato e desta arvore e diz qual dos dois itens falhou; 'python scripts/check_prova_do_seed.py' recusa e imprime. Isto e defeito da fase, e NAO ausencia de ambiente — nao trate como NAO VERIFICADO."
    ;;
  transportada)
    SEED_PROVA="NAO MEDIDA nesta rodada ($MEDE_MOTIVO); o que esta aqui foi COPIADO da arvore principal. Rode 'python scripts/check_prova_do_seed.py': ele confere o hash da arvore e recusa se divergir — nunca PASS por silencio. Desde a P7-2 divergencia aqui NAO e mais o efeito colateral de um fechamento de fase: ela significa que um arquivo RASTREADO mudou entre a medicao e este checkout."
    ;;
  *)
    echo "       Os itens 1 e 2 da DoD da Fase 5 ficam NAO VERIFICADO." >&2
    SEED_PROVA="AUSENTE ($MEDE_MOTIVO), e nao havia prova na arvore principal para copiar. 'python scripts/check_prova_do_seed.py' recusa por ausencia, e os itens 1 e 2 da DoD sao NAO VERIFICADO — nunca PASS por silencio."
    ;;
esac

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
echo "Provas de container: $PROVAS"
echo "Prova do seed completo: $SEED_PROVA"
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

PROVAS DE CONTAINER (P4-10): $PROVAS
O lancador as rodou na maquina do operador, porque exigem Docker e a allowlist nao o tem. Voce NAO as viu rodar — o que amarra a evidencia a este objeto e o hash da ARVORE que o arquivo carrega, e o verificador reprova se ele divergir. Ausencia tambem reprova: ele nao sai 0 por nao saber.

PROVA DO SEED COMPLETO (M2 da Fase 5): $SEED_PROVA
Mesma forma e mesmo limite das provas de container. O lancador roda a medicao AQUI, contra este worktree — o script exige Postgres, escreve 3,5 milhoes de linhas duas vezes e leva minutos, e a allowlist nao tem nada disso. Voce NAO viu medir; o que amarra a medicao a este objeto e o hash da arvore gravado, conferido contra o deste checkout, e ausencia tambem reprova.

O QUE A ARVORE AFIRMA, E O QUE ELA NAO AFIRMA (P7-2). Os dois artefatos declaram \`git rev-parse HEAD^{tree}\`, e nao o SHA do commit. Isso e deliberado: o rito de fechamento e rebase, rebase reescreve SHA, e uma prova amarrada ao commit morria em TODO fechamento de fase. Duas consequencias para a sua leitura. (1) A prova NAO afirma qual commit a produziu — dois commits com a mesma arvore sao o mesmo objeto para uma prova de desempenho e de comportamento, e isso e o comportamento certo. (2) A arvore cobre so o conteudo RASTREADO: \`scenarios/\` esta no \`.gitignore\` desde a Fase 5, e o pack materializado NAO entra no hash. O SHA do commit tinha a mesma cegueira; a P7-2 nao a criou, so a tornou nomeavel, e ela esta aberta como P7-3. Se o verificador reprovar por divergencia, a leitura e univoca: um arquivo rastreado mudou.

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
