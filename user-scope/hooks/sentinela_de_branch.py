#!/usr/bin/env python3
"""SENTINELA DE BRANCH — a D15. Recusa ESCRITA, e nao commit.

POR QUE ELE EXISTE, E POR QUE O GUARDA DE BRANCH NAO BASTA
-----------------------------------------------------------
`user-scope/hooks/pre-commit` recusa commit direto na branch default. Ele e
`pre-commit`: olha para onde o commit VAI CAIR. A corrida que
`docs/process/WORKFLOW.md` §"Arvore de trabalho compartilhada" descreve acontece
**antes de existir commit** — `HEAD` se move durante uma LEITURA, e o dano vira
duravel na ESCRITA que vem depois dela, sobre uma arvore que ja nao e aquela.

Entre a leitura e o commit havia uma janela inteira sem nada. Este hook e o
`pre-commit` adiantado ate a primeira escrita, e nesse ponto o erro custa **um
arquivo** em vez de uma sessao.

**Tres ocorrencias, e as tres foram pegas por alguem lembrar de conferir.**
Deteccao por memoria nao e deteccao — e a mesma distincao entre regra e
propriedade que a §1.6 do registro da Fase 1 estabelece, e que ja motivou
mecanizar o guarda de branch uma vez.

AS TRES PERNAS
--------------
1. **`SessionStart`** grava o sentinela: sessao, branch e sha.
2. **`PreToolUse` de `Write`/`Edit`, com `HEAD` na branch DEFAULT: RECUSA.**
3. **`PreToolUse` de `Write`/`Edit`, com a branch DIFERENTE do sentinela:
   RECUSA**, nomeando as duas, e exigindo re-ancoragem explicita.

**A perna 2 e a que decide, e ela nao e a perna 3.** Na terceira ocorrencia a
arvore JA ESTAVA em `main` quando a sessao comecou: um sentinela que so
comparasse "mudou desde o inicio" teria gravado `main` como ancora e ficado
calado. A perna 2 nao compara com nada — ela afirma uma propriedade do projeto:
`CLAUDE.md` diz *uma fase = uma branch*, entao escrita de trabalho nunca nasce na
default.

**A perna 2 NAO tem re-ancoragem.** `scripts/reancorar_sessao.py` recusa a branch
default por construcao. Se tivesse, seria a saida de um clique que a peca 1 desta
fase ja argumentou contra ao proibir `confirmacao` onde nao ha o que confirmar:
confirmar o que tem volta treina o operador a clicar "sim", e e assim que a
confirmacao do que NAO tem volta deixa de ser lida.

MUDANCA DE SHA NA MESMA BRANCH NAO BLOQUEIA, e a assimetria e deliberada
-------------------------------------------------------------------------
Commit do operador na mesma branch e normal. `pull` reescrevendo arquivo sob uma
leitura e a segunda ocorrencia registrada — e essa metade **ja tem cobertura**:
o proprio harness do Claude Code recusa `Edit` de arquivo que mudou em disco
desde o `Read`. Acrescentar bloqueio por sha seria ruido sobre propriedade que ja
existe. Onde nao se sabe, bloqueia; onde se sabe que e normal, nao.

POR QUE ELE MORA FORA DA ARVORE
--------------------------------
Em `~/.claude/hooks/`, instalado por `bootstrap.sh`, com a fonte versionada aqui
— o mesmo desenho do `readonly_bash.py`, e por uma variante do mesmo argumento.

La e *"um auditor definido pelo commit que ele audita pode ser enfraquecido por
esse mesmo commit"*. Aqui e mais direto: **um guarda que mora na arvore que ele
guarda desaparece com ela.** Um `checkout` para um commit anterior a D15 levaria
junto o hook e a configuracao dele — exatamente na situacao para a qual ele
existe. Em `.claude/settings.json` este hook seria um guarda que some quando
precisa.

O CUSTO DISSO, DECLARADO: hook de escopo de usuario vale para TODO projeto da
maquina, e recusar escrita em `main` seria errado na maioria deles. Por isso ele
se auto-escopa: sem `docs/spec/00_MASTER_SPEC.md` na raiz do repositorio, sai
sem dizer nada. O marcador e do projeto e existe desde a Fase 0.

FALHA ABERTA NA INFRAESTRUTURA, FECHADA NA PROPRIEDADE
--------------------------------------------------------
Entrada ilegivel, `git` ausente, alvo fora de repositorio, `HEAD` destacado,
projeto que nao e este: **sai 0**. Sao casos em que o hook nao SABE, e um hook
global que quebrasse a sessao inteira por nao saber seria pior que o problema.

As duas condicoes que ele conhece — branch default, e branch trocada — **saem
2**. `WORKFLOW.md` classifica bloqueio indevido como defeito, e e por isso que a
lista de "sai 0" e explicita em vez de ser o `except` do fim.

LIMITE — E GUARDA LOCAL, NAO GATE
-----------------------------------
Protege ESTE clone e ESTA sessao. Quem clonar sem `bootstrap.sh` nao o tem;
escrita por fora do harness — `python -c`, editor do operador — nao passa por
aqui. A protecao real de `main` continua sendo a branch protection do GitHub.

E ele **nao previne** a corrida: detecta antes de a escrita virar duravel. A
leitura ja feita continua velha, e a mensagem manda reler. Nenhum mecanismo
alcanca a leitura que ja aconteceu.

DUAS SESSOES SIMULTANEAS no mesmo clone sobrescrevem o sentinela uma da outra. O
problema que este hook trata e uma arvore compartilhada por duas pessoas; duas
sessoes de agente no mesmo clone ja esta fora do modelo, e a limitacao esta dita
em vez de omitida.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

#: O marcador que diz "este repositorio e o AURORA". Existe desde a Fase 0 e
#: `bootstrap.sh` recusa rodar sem ele.
MARCADOR = Path("docs") / "spec" / "00_MASTER_SPEC.md"

#: Nome do sentinela DENTRO do git dir — que nao e a arvore de trabalho e nao
#: muda com `checkout`. Em worktree, `.git` e arquivo, entao o caminho vem de
#: `git rev-parse --git-dir` e nao de `<raiz>/.git`.
SENTINELA = "aurora-sentinela-de-branch.json"

FERRAMENTAS_DE_ESCRITA = {"Write", "Edit", "NotebookEdit", "MultiEdit"}


def _git(cwd: Path, *args: str) -> str:
    try:
        saida = subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, timeout=5
        )
    except Exception:
        return ""
    return saida.stdout.strip() if saida.returncode == 0 else ""


def raiz(a_partir_de: Path) -> Path | None:
    """A raiz do repositorio que contem o caminho, ou `None`."""
    topo = _git(a_partir_de, "rev-parse", "--show-toplevel")
    return Path(topo) if topo else None


def e_este_projeto(topo: Path) -> bool:
    return (topo / MARCADOR).is_file()


def branch_default(topo: Path) -> str:
    """Do remoto quando ele existe; `main` quando nao existe.

    Mesma resolucao do `pre-commit`, e de proposito: dois guardas com ideias
    diferentes de qual e a branch default seriam duas politicas.
    """
    remoto = _git(topo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return remoto.removeprefix("origin/") if remoto else "main"


def caminho_do_sentinela(topo: Path) -> Path | None:
    git_dir = _git(topo, "rev-parse", "--absolute-git-dir")
    return Path(git_dir) / SENTINELA if git_dir else None


def le_sentinela(topo: Path) -> dict:
    alvo = caminho_do_sentinela(topo)
    if alvo is None or not alvo.is_file():
        return {}
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except Exception:
        return {}


def grava_sentinela(topo: Path, sessao: str, branch: str) -> None:
    alvo = caminho_do_sentinela(topo)
    if alvo is None:
        return
    try:
        alvo.write_text(
            json.dumps(
                {
                    "session_id": sessao,
                    "branch": branch,
                    "sha": _git(topo, "rev-parse", "HEAD"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        # Nao saber gravar o sentinela nao pode derrubar a sessao. A perna 2
        # continua valendo sem ele: ela nao depende de ancora nenhuma.
        pass


def _recusa_na_default(branch: str) -> str:
    return f"""
  ESCRITA RECUSADA — voce esta em '{branch}', que e a branch default.

  CLAUDE.md: uma fase = uma branch = um PR. Trabalho nao nasce na default, e
  este hook e o `pre-commit` adiantado ate a PRIMEIRA ESCRITA — aqui o erro
  custa um arquivo; no commit, custa a sessao inteira.

  Se HEAD se moveu sob uma leitura em curso — a corrida de WORKFLOW.md
  §"Arvore de trabalho compartilhada", tres ocorrencias registradas —, o que
  voce leu pode ser de OUTRA arvore. Confira antes de escrever:

      git branch --show-current
      git status

  e volte para a branch da fase. NAO ha re-ancoragem para a default: ela
  existiria so para ser aceita sem ler.
"""


def _recusa_por_ancora(ancorada: str, atual: str) -> str:
    return f"""
  ESCRITA RECUSADA — a branch mudou no meio desta sessao.

      ancorada no inicio ..... {ancorada}
      agora .................. {atual}

  O que voce leu ate aqui veio da arvore de '{ancorada}'. Escrever agora grava
  em '{atual}' um trabalho pensado sobre outra coisa — e essa e a corrida que
  este hook existe para pegar, nao um aviso de rotina.

  RELEIA os arquivos que importam antes de continuar.

  Se a troca foi deliberada, a re-ancoragem e EXPLICITA e exige que voce
  escreva o nome da branch em que pretende trabalhar:

      python scripts/reancorar_sessao.py <branch>

  Nao ha atalho com o nome ja preenchido, e isso e desenho: uma saida de um
  clique vira o "sim" que se aprende a dar, e ai o guarda so gasta o tempo de
  quem le. O nome esta acima; digite o que voce quer dizer.
"""


def main() -> int:
    try:
        dados = json.load(sys.stdin)
    except Exception:
        return 0

    evento = dados.get("hook_event_name") or ""
    sessao = str(dados.get("session_id") or "")
    entrada = dados.get("tool_input") or {}
    ferramenta = dados.get("tool_name") or ""

    if evento == "SessionStart":
        topo = raiz(Path(dados.get("cwd") or "."))
        if topo is None or not e_este_projeto(topo):
            return 0
        branch = _git(topo, "symbolic-ref", "--short", "HEAD")
        if branch:
            grava_sentinela(topo, sessao, branch)
        return 0

    if ferramenta and ferramenta not in FERRAMENTAS_DE_ESCRITA:
        return 0

    alvo = entrada.get("file_path") or entrada.get("path") or ""
    if not alvo:
        return 0

    # O ESCOPO E O ALVO, e nao o CWD. Escrita no scratchpad ou em qualquer
    # caminho fora deste repositorio nao e trabalho desta arvore, e bloquea-la
    # seria falso bloqueio — que `WORKFLOW.md` classifica como defeito.
    partida = Path(alvo).parent
    if not partida.is_dir():
        partida = Path(dados.get("cwd") or ".")
    topo = raiz(partida)
    if topo is None or not e_este_projeto(topo):
        return 0

    branch = _git(topo, "symbolic-ref", "--short", "HEAD")
    if not branch:
        # HEAD destacado: e assim que o worktree de auditoria roda, e la nao ha
        # branch default a violar nem trabalho de fase a proteger.
        return 0

    if branch == branch_default(topo):
        print(_recusa_na_default(branch), file=sys.stderr)
        return 2

    sentinela = le_sentinela(topo)
    if sentinela.get("session_id") != sessao:
        # Sessao nova, ou hook instalado no meio de uma: ancora agora. Nao ha o
        # que comparar, e recusar aqui seria bloquear a primeira escrita de toda
        # sessao — falso bloqueio, e do tipo que se aprende a contornar.
        grava_sentinela(topo, sessao, branch)
        return 0

    ancorada = sentinela.get("branch") or ""
    if ancorada and ancorada != branch:
        print(_recusa_por_ancora(ancorada, branch), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
