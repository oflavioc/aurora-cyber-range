#!/bin/sh
# O BUILD DAS TRES TELAS, COM A PROVA NEGATIVA DO PROPRIO GATE.
#
# POR QUE ISTO NAO E "npm ci && npm run build"
# --------------------------------------------
# `vite build` NAO CHECA TIPOS. Ele transpila com esbuild, que apaga a anotacao
# sem olhar para ela, e SAI 0 com o TypeScript quebrado. Um passo de CI que so
# rodasse `vite build` ficaria verde sobre um cliente que nao compila — a
# verificacao que PARECE existir, no lugar mais facil dela acontecer.
#
# Por isso o build e `tsc --noEmit && vite build`. E por isso este arquivo
# existe: **um gate que nunca foi visto reprovando e atestacao**, e foi assim que
# o DEMO da Fase 1 ficou inexecutavel sem nada acusar.
#
# O QUE ELE MEDE, NESTA ORDEM
# ----------------------------
#   1. com um erro de tipo plantado em codigo QUE ENTRA NO BUNDLE,
#      `vite build` sozinho sai 0        -> o risco, reproduzido
#   2. no MESMO estado, `npm run build` sai != 0
#                                        -> o gate reprova
#   3. desplantado, `npm run build` sai 0 -> e o gate nao reprova sempre
#
# O passo 3 nao e formalidade: um gate que reprovasse tudo passaria no passo 2 e
# seria inutil. E o par que discrimina, na forma que esta fase usa em toda peca.
#
# O ERRO E PLANTADO EM ARQUIVO REAL, e nao num arquivo novo que ninguem importa.
# Um arquivo solto provaria menos: `tsc` o veria por estar no `include`, e o
# `vite` o ignoraria por nao estar no grafo — o passo 1 sairia 0 pelo motivo
# errado. O que se quer demonstrar e que o vite ignora tipo em codigo QUE ELE
# BUNDLA.
#
# A RESTAURACAO E POR `trap`, e conferida por `cmp`: este script roda tambem na
# maquina de quem desenvolve, sobre a arvore de verdade, e um Ctrl-C no meio nao
# pode deixar a fonte plantada.

set -eu

ALVO="wallboard-shell/main.tsx"
BACKUP="/tmp/aurora-prova-do-build.bak"
PRISTINO="/tmp/aurora-prova-do-build.pristino"
TELAS="wallboard-shell participant-view gm-console"

restaura() {
  if [ -f "$BACKUP" ]; then
    cp "$BACKUP" "$ALVO"
    rm -f "$BACKUP"
  fi
}
trap restaura EXIT INT TERM

echo "== dependencias, pelo lockfile (npm ci) =="
npm ci

echo
echo "== 1/3 prova negativa: erro de tipo plantado em $ALVO =="
cp "$ALVO" "$BACKUP"
cat >>"$ALVO" <<'PLANTADO'

// PLANTADO POR prova_do_build.sh — removido logo em seguida.
const erro_plantado: number = "isto nao e um numero";
void erro_plantado;
PLANTADO

if npx vite build --mode wallboard-shell >/dev/null 2>&1; then
  echo "   MEDIDO: \`vite build\` sozinho sai 0 com o TypeScript quebrado."
else
  echo "   FALHA DE INSTRUMENTO: \`vite build\` reprovou o erro plantado." >&2
  echo "   A premissa deste gate mudou — o vite passou a checar tipos, ou o" >&2
  echo "   erro plantado deixou de ser um erro de TIPO. Reveja este script." >&2
  exit 1
fi

echo
echo "== 2/3 o gate completo tem de REPROVAR o mesmo estado =="
if npm run build >/dev/null 2>&1; then
  echo "   FALHA: \`npm run build\` saiu 0 com o TypeScript quebrado." >&2
  echo "   O gate do cliente nao esta gateando: confira o script \`build\` do" >&2
  echo "   package.json — ele precisa comecar por \`tsc --noEmit &&\`." >&2
  exit 1
fi
echo "   o gate reprova, como tem de reprovar."

# A CONFERENCIA E CONTRA A COPIA INTACTA, e nao contra o proprio arquivo.
# A primeira versao desta linha era `cmp -s "$ALVO" "$ALVO"` — que compara um
# arquivo consigo mesmo e e verdadeira sempre. Verificacao vacua no caminho da
# limpeza e a que ninguem ve falhar: ela so importa no dia em que a restauracao
# nao acontecer.
cp "$BACKUP" "$PRISTINO"
restaura
if ! cmp -s "$ALVO" "$PRISTINO"; then
  echo "   FALHA: a restauracao de $ALVO nao conferiu contra a copia intacta." >&2
  exit 1
fi
rm -f "$PRISTINO"

echo
echo "== 3/3 o build de verdade =="
npm run build

for tela in $TELAS; do
  if [ ! -f "dist/$tela/index.html" ]; then
    echo "FALHA: dist/$tela/index.html nao foi produzido." >&2
    exit 1
  fi
done

# ARQUIVO UNICO, e nao HTML com `<script src>`: se o bundle deixasse de ser
# inlinado, `GET /sala` serviria um HTML que pede assets por uma rota que NAO
# EXISTE — a tela abriria em branco na sala, e nenhum teste de payload veria.
for tela in $TELAS; do
  if grep -q '<script[^>]*src=' "dist/$tela/index.html"; then
    echo "FALHA: dist/$tela/index.html referencia asset externo." >&2
    echo "O range-api serve UM arquivo por tela; nao ha rota de asset." >&2
    exit 1
  fi
done

# O QUE A SALA NAO PODE ALCANCAR — `06` T6 sobre o artefato CONSTRUIDO, e nao so
# sobre a fonte. `tests/test_telas.py` ja varre a fonte; esta varredura afirma
# que a transformacao preservou a propriedade.
for tela in wallboard-shell participant-view; do
  for proibido in '/injects/' '/exercise/' '/session' 'Authorization'; do
    if grep -q "$proibido" "dist/$tela/index.html"; then
      echo "FALHA: dist/$tela/index.html contem \`$proibido\`." >&2
      echo "Tela publica com caminho de console: uma tela sem token com botao" >&2
      echo "de disparo poria o console na rede." >&2
      exit 1
    fi
  done
done

echo
echo "as tres telas construidas, o gate provado reprovando, e as duas publicas"
echo "sem vocabulario de console."
