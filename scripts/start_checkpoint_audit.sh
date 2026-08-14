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
  [ -n "$RAW" ] && rm -f "$RAW" 2>/dev/null
  # Sessao nem comecou: nada a capturar.
  [ -z "$CLAUDE_RC" ] && return 0
  python "$ROOT/scripts/audit_report.py" --recover --launcher-exit "$CLAUDE_RC"
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

PROMPT="Audite a Fase $PHASE. Este checkout esta fixado no commit candidato $HEAD_SHA. Leia spec + diff contra main + testes reais e emita o formato obrigatorio PASS/FAIL. Nao corrija nada."

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
