#!/usr/bin/env python3
"""P37 — todo arquivo versionado esta classificado pelo gate `spec_freeze`.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
`spec_freeze` compara dois conjuntos de caminhos, SPEC e CODE, e reprova o PR que
toca os dois. A regra so vale para o que esta em algum dos conjuntos: **o que nao
esta em nenhum e invisivel ao gate**.

Foi a P37. `docs/process/` estava fora dos dois, e dentro dele mora o
`PHASE_0_CHECKLIST.md`, que e uma **Definition of Done** — auditorias o citam
como "requisito violado". Uma DoD fora dos dois conjuntos pode ser alterada no
mesmo PR que altera o mecanismo que ela julga, e o gate nao ve.

A correcao daquele caso e uma linha no workflow. **Esta checagem existe para o
proximo**: diretorio novo no topo do repositorio nasce invisivel ao gate, e nada
avisa. Aqui ele passa a reprovar ate alguem classifica-lo.

AS TRES CLASSES, E A TERCEIRA E DECLARACAO EXPLICITA
-----------------------------------------------------
- **SPEC** — normativo. Muda so em PR de `spec-change:`, sem codigo junto.
- **CODE** — mecanismo que aplica a spec. Nao muda no mesmo PR que a spec.
- **DESCRITIVO** — nem uma coisa nem outra, e por isso fora do gate. **Precisa
  estar declarado aqui**, com motivo. E a diferenca entre "decidimos que fica de
  fora" e "ninguem olhou".

O QUE ELA NAO E
---------------
Nao julga se a classificacao esta CERTA — julga se ela EXISTE. Um diretorio novo
classificado como descritivo por engano passa; um esquecido, nao. E a mesma forma
da whitelist da P2-2 e da P2-15: o custo de acrescentar e uma conversa.

POR QUE ELA SE CONFERE CONTRA O `git`
--------------------------------------
Os pathspecs sao lidos do proprio workflow e casados aqui em Python, porque a
prova negativa precisa injetar lista de arquivos hipotetica. Casamento reescrito
diverge do original — entao a checagem **compara o proprio resultado com o que o
`git ls-files` devolve** para os mesmos pathspecs, sobre os arquivos reais. Se os
dois discordarem, ela reprova por divergencia de matcher, e nao por
classificacao.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "invariants.yml"

RULE = "P37 - cobertura do gate spec_freeze"

#: DESCRITIVO — fora do gate, por decisao, com motivo.
#:
#: Cada entrada e um pathspec no mesmo dialeto do workflow. Acrescentar aqui e
#: declarar que aquilo NAO e nem norma nem mecanismo — e o custo de fazer isso
#: por engano e que ninguem mais olha para o caminho.
DESCRITIVO: dict[str, str] = {
    "docs/progress/": "registro de fase e relatorios de auditoria: dizem o que "
    "aconteceu, nao o que deve acontecer",
    "docs/BRIEFING.md": "apresentacao do projeto, sem clausula normativa",
    "README.md": "porta de entrada, descritiva",
    "CHANGELOG_V3.md": "historico",
    "tests/": "a suite exercita o mecanismo, nao o define; e alterada junto do "
    "codigo que ela julga, no mesmo PR, por desenho",
    "alembic/": "migrations e configuracao de migration",
    "alembic.ini": "configuracao de migration",
    "pyproject.toml": "manifesto de dependencia",
    "constraints.txt": "fecho transitivo pinado",
    "docker-compose.yml": "composicao local",
    "docker-compose.audit.yml": "stack efemera da auditoria (P2-19). Descritivo "
    "pelo mesmo motivo que a composicao local: nao e mecanismo julgado pelo "
    "gate, e os digests dele ja tem guarda propria em check_pinned_images.py, "
    "que cruza os TRES arquivos que declaram imagem",
    ".env.example": "placeholders; o `.env` real nao e versionado",
    "docs/adr/": "registro de decisao: diz o que foi decidido e por que, nao o "
    "que deve acontecer; a norma que uma decisao cria vive em .claude/rules/ "
    "ou em docs/spec/, cada uma sob seu proprio gate",
    "docs/ADOCAO_ESTRUTURA_AGENTICA.md": "mapa da integracao da Estrutura "
    "Agentica: registra o que foi instalado, o que prevaleceu e as decisoes do "
    "proprietario — registro, como docs/progress/",
}


def _pathspecs(rotulo: str, texto: str) -> list[str]:
    """Extrai a lista de pathspecs de `SPEC=$(...)` ou `CODE=$(...)` do workflow.

    Ler do workflow, e nao repetir a lista aqui, e o ponto: duas copias da mesma
    lista divergem, e a que diverge em silencio e sempre a que nao e executada.
    """
    casado = re.search(
        rf"{rotulo}=\$\(git diff --name-only \"\$BASE_SHA\" HEAD -- (.*?)\| wc -l\)",
        texto,
        re.S,
    )
    if casado is None:
        raise SystemExit(
            f"{RULE}: nao achei o conjunto {rotulo} em {WORKFLOW.name}. "
            "A forma do gate mudou, e esta checagem precisa acompanhar."
        )
    bruto = casado.group(1).replace("\\\n", " ")
    bruto = re.sub(r"#.*", "", bruto)
    return [token.strip().strip("'\"") for token in bruto.split() if token.strip()]


def _casa(caminho: str, pathspec: str) -> bool:
    """As quatro formas de pathspec que o gate de fato usa."""
    if pathspec.startswith(":(exclude)"):
        return False
    if pathspec.startswith(":(glob)"):
        padrao = pathspec[len(":(glob)") :]
        return "/" not in caminho and Path(caminho).match(padrao)
    if pathspec.endswith("/"):
        return caminho.startswith(pathspec)
    return caminho == pathspec


def _classifica(caminho: str, pathspecs: list[str]) -> bool:
    excluidos = [p[len(":(exclude)") :] for p in pathspecs if p.startswith(":(exclude)")]
    if any(caminho == e or caminho.startswith(e.rstrip("/") + "/") for e in excluidos):
        return False
    return any(_casa(caminho, p) for p in pathspecs)


def _git_ls(pathspecs: list[str]) -> set[str]:
    saida = subprocess.run(
        ["git", "ls-files", "--", *pathspecs],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return {linha for linha in saida.stdout.splitlines() if linha}


def verifica(arquivos: list[str], spec: list[str], code: list[str]) -> list[str]:
    """As tres asserções. Recebe a lista de arquivos para a prova negativa poder
    injetar uma hipotetica."""
    problemas: list[str] = []
    descritivo = list(DESCRITIVO)

    for caminho in sorted(arquivos):
        em_spec = _classifica(caminho, spec)
        em_code = _classifica(caminho, code)
        em_desc = _classifica(caminho, descritivo)

        if em_spec and em_code:
            problemas.append(
                f"{caminho}: esta em SPEC **e** em CODE. Todo PR que o tocar "
                "reprova, qualquer que seja o conteudo — o gate deixa de ser gate "
                "e vira bloqueio."
            )
        elif not (em_spec or em_code or em_desc):
            problemas.append(
                f"{caminho}: nao esta em SPEC, nem em CODE, nem declarado como "
                f"descritivo em {Path(__file__).name}. O gate `spec_freeze` nao o "
                "ve: ele pode ser alterado no mesmo PR que a spec ou que o "
                "mecanismo, sem que nada acuse."
            )
        elif em_desc and (em_spec or em_code):
            problemas.append(
                f"{caminho}: declarado descritivo e tambem coberto pelo gate. "
                "A declaracao esta sobrando e mente sobre o que acontece."
            )
    return problemas


def main(argv: list[str] | None = None) -> int:
    texto = WORKFLOW.read_text(encoding="utf-8")
    spec = _pathspecs("SPEC", texto)
    code = _pathspecs("CODE", texto)

    arquivos = sorted(_git_ls(["."]))
    problemas = verifica(arquivos, spec, code)

    # A CONFERENCIA CONTRA O `git`: o matcher daqui e reescrito, e reescrita
    # diverge. Se divergir, e isto que reprova — antes de qualquer conclusao
    # sobre classificacao.
    for rotulo, pathspecs in (("SPEC", spec), ("CODE", code)):
        meu = {c for c in arquivos if _classifica(c, pathspecs)}
        do_git = _git_ls(pathspecs)
        if meu != do_git:
            so_meu = sorted(meu - do_git)[:3]
            so_git = sorted(do_git - meu)[:3]
            problemas.append(
                f"o matcher desta checagem diverge do `git` no conjunto {rotulo}: "
                f"so aqui {so_meu}, so no git {so_git}. A classificacao abaixo nao "
                "vale enquanto isso nao fechar."
            )

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(arquivos)} arquivos versionados, todos classificados — "
        f"{len([c for c in arquivos if _classifica(c, spec)])} em SPEC, "
        f"{len([c for c in arquivos if _classifica(c, code)])} em CODE, "
        f"{len([c for c in arquivos if _classifica(c, list(DESCRITIVO))])} descritivos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
