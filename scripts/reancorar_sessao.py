#!/usr/bin/env python3
"""Re-ancora o sentinela de branch da sessao corrente — D15, perna 3.

POR QUE ISTO EXIGE O NOME DA BRANCH COMO ARGUMENTO
----------------------------------------------------
Porque uma saida de um clique nao seria guarda nenhuma.

A peca 1 desta fase ja argumentou a forma, ao proibir `confirmacao: true` em
rota que tem volta: *"confirmar o que tem volta treina o operador a clicar 'sim',
e e assim que a confirmacao do que NAO tem volta deixa de ser lida"*. Um botao —
ou um comando com o nome ja preenchido, colavel da mensagem de recusa — teria
exatamente esse efeito: o guarda dispararia, alguem colaria, e o unico custo
seria o tempo de quem le.

Escrever o nome da branch e o ato deliberado. Nao da para faze-lo sem olhar em
que branch se esta e afirmar que e essa mesma. E o comando fica no historico,
que e onde uma re-ancoragem indevida vira evidencia em vez de silencio.

O QUE ELE RECUSA, E POR QUE CADA RECUSA
-----------------------------------------
- **nome que nao bate com `HEAD`** — re-ancorar para onde nao se esta e afirmar
  uma coisa e estar em outra, que e o defeito inteiro;
- **a branch DEFAULT** — a perna 2 do sentinela nao tem re-ancoragem por
  construcao. Trabalho nao nasce na default, e um caminho para dizer "pode"
  transformaria a unica perna incondicional numa perna negociavel;
- **fora do repositorio do AURORA** — o sentinela e deste projeto.

Ele NAO cria sentinela onde nao ha: sem sessao ancorada nao ha o que re-ancorar,
e inventar uma entrada aqui deixaria a proxima escrita passar por um caminho que
nunca foi o do hook.

USO
    python scripts/reancorar_sessao.py <branch>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MARCADOR = Path("docs") / "spec" / "00_MASTER_SPEC.md"
SENTINELA = "aurora-sentinela-de-branch.json"


def _git(cwd: Path, *args: str) -> str:
    saida = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, timeout=5
    )
    return saida.stdout.strip() if saida.returncode == 0 else ""


def _erro(mensagem: str) -> int:
    print(mensagem.rstrip(), file=sys.stderr)
    return 1


def reancorar(pedida: str, cwd: Path) -> int:
    topo_bruto = _git(cwd, "rev-parse", "--show-toplevel")
    if not topo_bruto:
        return _erro("fora de um repositorio git.")
    topo = Path(topo_bruto)

    if not (topo / MARCADOR).is_file():
        return _erro(
            f"{topo} nao e o repositorio do AURORA — {MARCADOR.as_posix()} nao existe.\n"
            "O sentinela de branch e deste projeto."
        )

    atual = _git(topo, "symbolic-ref", "--short", "HEAD")
    if not atual:
        return _erro("HEAD destacado: nao ha branch a ancorar.")

    if pedida != atual:
        return _erro(
            f"voce pediu '{pedida}' e HEAD esta em '{atual}'.\n\n"
            "  Re-ancorar para uma branch em que voce nao esta e afirmar uma coisa\n"
            "  e estar em outra — que e o defeito que o sentinela existe para pegar.\n"
            "  Va para a branch que voce quer, confira, e repita o comando."
        )

    remoto = _git(topo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    default = remoto.removeprefix("origin/") if remoto else "main"
    if atual == default:
        return _erro(
            f"'{atual}' e a branch DEFAULT, e ela nao tem re-ancoragem.\n\n"
            "  CLAUDE.md: uma fase = uma branch = um PR. A perna que recusa escrita\n"
            "  na default e incondicional por desenho — um caminho para dizer 'pode'\n"
            "  a transformaria na perna que se aprende a contornar.\n\n"
            "      git switch -c fase-<n>-<slug>"
        )

    git_dir = _git(topo, "rev-parse", "--absolute-git-dir")
    if not git_dir:
        return _erro("nao foi possivel resolver o diretorio git.")
    alvo = Path(git_dir) / SENTINELA

    if not alvo.is_file():
        return _erro(
            "nao ha sentinela para esta arvore.\n\n"
            "  Sem sessao ancorada nao ha o que re-ancorar, e criar uma entrada aqui\n"
            "  deixaria a proxima escrita passar por um caminho que nunca foi o do\n"
            "  hook. Se o hook esta instalado, a proxima sessao grava o sentinela\n"
            "  sozinha no SessionStart."
        )

    dados = json.loads(alvo.read_text(encoding="utf-8"))
    anterior = dados.get("branch") or "(nenhuma)"
    dados["branch"] = atual
    dados["sha"] = _git(topo, "rev-parse", "HEAD")
    alvo.write_text(json.dumps(dados, indent=2), encoding="utf-8")

    print(f"sentinela re-ancorado: {anterior} -> {atual}")
    print("RELEIA os arquivos que importam: o que voce leu antes veio da outra arvore.")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        return _erro(
            "uso: python scripts/reancorar_sessao.py <branch>\n\n"
            "  O nome e obrigatorio e nao tem default. Ele e o ato deliberado:\n"
            "  uma re-ancoragem de um clique seria o 'sim' que se aprende a dar."
        )
    return reancorar(sys.argv[1], Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
