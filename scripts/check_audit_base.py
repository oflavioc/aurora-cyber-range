#!/usr/bin/env python3
"""A auditoria desta fase ainda e PORTA, ou ja virou laudo?

O QUE ESTE VERIFICADOR EXISTE PARA FECHAR
------------------------------------------
`docs/process/WORKFLOW.md` fixa a ordem: commit candidato, auditoria, DEPOIS
`gh pr create`. Rodando a auditoria sobre trabalho que ja esta em `main`,
qualquer BLOCKER encontrado JA ESTA na branch default — o checkpoint deixa de ser
porta e vira laudo.

**Este e o terceiro predicado.** Os dois anteriores erraram o alvo, e os dois
erraram do mesmo jeito: degradaram para "ok" quando nao sabiam.

1. O primeiro nao existia: o lancador entregava a base e seguia. Com
   `BASE_SHA == HEAD_SHA` o diff era vazio por construcao e o auditor improvisava
   uma base em silencio. Foi o H1 da primeira auditoria da Fase 3.
2. O segundo perguntava `git merge-base --is-ancestor HEAD BASE` — "o candidato
   esta contido na base?". Isso e `BASE == HEAD` e pouco mais: **o caso
   degenerado**. A inversao que de fato aconteceu nas Fases 2 e 3 e merge PECA A
   PECA, e nela o candidato nao esta contido na base: no instante da segunda
   auditoria, cinco das seis pecas da Fase 3 estavam em `main`, a guarda nao
   disparou, e o diff entregue ao auditor nao continha NENHUM dos quatro itens da
   DoD. Foi o H2 da segunda auditoria.

O erro dos dois nao e de rigor, e de EIXO: eles perguntam sobre contencao do
CANDIDATO; a propriedade e a ausencia do TRABALHO DA FASE na base. As duas
coincidem so quando a fase inteira ja esta mergeada.

A PROPRIEDADE, E AS DUAS METADES QUE A PROVAM
----------------------------------------------
    A auditoria e porta  <=>  nada do trabalho da fase esta na branch default.

**(ii) Topologia, contra a ancora.** Nenhum commit da fase pode ser alcancavel a
partir da base. Com `START` = onde a fase comecou (`docs/process/phase_anchors.tsv`),
isso e uma igualdade exata:

    git merge-base BASE HEAD  ==  START

Se parte da fase foi mergeada, o merge-base SOBE para dentro dos commits da
fase e a igualdade quebra. Se `main` avancou com trabalho de OUTRA fase, o
merge-base nao se move: o caso normal continua passando, e isso e o que distingue
este predicado do anterior.

**(iii) Conteudo, por identidade de patch.** A topologia nao sobrevive a merge que
nao preserva identidade de commit. Duas checagens fecham a parte que da para
fechar, e as duas sao DERIVADAS do proprio git — sem lista, sem manifesto:

    (iii-a)  o diff contra a base nao pode ser VAZIO
    (iii-b)  nenhum commit de BASE..HEAD pode ter patch-id ja presente na base

A alternativa que se considerou para (iii) — cruzar o diff com uma lista do que a
fase "deveria conter" — foi RECUSADA: lista paralela do mesmo fato e a classe de
defeito da P3-1, e uma lista que envelhece produziria gate que mente. Identidade
de patch responde a mesma pergunta sem lista nenhuma.

O QUE ESTE PREDICADO NAO PEGA, DECLARADO E NAO OMITIDO
-------------------------------------------------------
**Squash-merge seguido de commits novos na branch.** O squash reescreve N patches
num so: os patch-ids individuais deixam de casar, o merge-base fica em `START`
porque a identidade mudou, e o diff nao e vazio porque a branch andou depois. As
duas metades passam, e o conteudo da fase ESTA em `main`.

Este furo nao e condicao do repositorio: e um clique. `docs/process/WORKFLOW.md`
fixa **rebase, nunca squash** no merge de branch de fase, e a regra mora la — e
nao so na pendencia — porque quem clica e o operador, e a pendencia nao esta
aberta na hora do clique.

Furo declarado vale mais que gate que mente.

ANCORA AUSENTE RECUSA
---------------------
Sem `START` nao ha como afirmar contencao, e "nao da para afirmar" e exatamente o
caso em que os dois predicados anteriores disseram "ok". Aqui ele recusa. Vale
tambem para ancora que nao resolve neste repositorio e para ancora que nao e
ancestral de `HEAD` — uma ancora que nao esta na historia do candidato nao
descreve esta branch.

Stdlib pura. Chamado por `scripts/start_checkpoint_audit.sh` antes de o worktree
existir e antes de o Docker ser tocado; exercido por
`scripts/check_audit_base_probes.py` em sete eixos.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REGRA = "P3-7 - a base de comparacao mostra o trabalho da fase"

ANCORAS = Path("docs") / "process" / "phase_anchors.tsv"


@dataclass(frozen=True, slots=True)
class Falha:
    """Uma condicao que nao vale, com o texto que o operador precisa ler."""

    eixo: str
    texto: str


def _git(repo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=False
    )


def _sha(repo: str, ref: str) -> str | None:
    r = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return r.stdout.strip() or None


def _e_ancestral(repo: str, a: str, b: str) -> bool:
    """`a` e ancestral-ou-igual de `b`?"""
    return _git(repo, "merge-base", "--is-ancestor", a, b).returncode == 0


def ancora(repo: str, fase: int) -> tuple[str | None, str]:
    """Le a linha da fase. Devolve (sha_declarado_ou_None, motivo_se_ausente)."""
    caminho = Path(repo) / ANCORAS
    if not caminho.is_file():
        return None, f"o arquivo de ancoras nao existe: {ANCORAS.as_posix()}"

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        campos = [c.strip() for c in linha.split("\t") if c.strip()]
        if len(campos) >= 2 and campos[0] == str(fase):
            return campos[1], ""
    return None, f"nao ha linha para a fase {fase} em {ANCORAS.as_posix()}"


def avalia(repo: str, fase: int, base: str, head: str) -> list[Falha]:
    """As quatro condicoes, na ordem em que a mensagem fica mais util.

    Devolve a lista de falhas. Vazia = a auditoria e porta.
    """
    falhas: list[Falha] = []

    base_sha = _sha(repo, base)
    head_sha = _sha(repo, head)
    if base_sha is None or head_sha is None:
        qual = base if base_sha is None else head
        return [Falha("ref", f"'{qual}' nao resolve para um commit neste repositorio.")]

    declarada, motivo = ancora(repo, fase)
    if declarada is None:
        return [
            Falha(
                "ancora",
                f"ANCORA AUSENTE — {motivo}.\n"
                f"    Sem saber onde a fase comecou nao da para afirmar que ela nao\n"
                f"    foi mergeada, e 'nao da para afirmar' e o caso em que os dois\n"
                f"    predicados anteriores disseram 'ok'. Escreva a linha:\n"
                f"        {fase}<TAB><sha em que a branch nasceu><TAB><descricao>",
            )
        ]

    start = _sha(repo, declarada)
    if start is None:
        return [
            Falha(
                "ancora",
                f"a ancora da fase {fase} e '{declarada}', que NAO RESOLVE neste\n"
                f"    repositorio. Ancora que nao existe nao prova nada.",
            )
        ]
    if not _e_ancestral(repo, start, head_sha):
        return [
            Falha(
                "ancora",
                f"a ancora {start[:12]} NAO E ANCESTRAL do candidato {head_sha[:12]}.\n"
                f"    Ela nao descreve esta branch: ou aponta para outra historia, ou\n"
                f"    ficou para tras de um rebase. Regrave-a.",
            )
        ]

    # ------------------------------------------------------------------
    # (ii) TOPOLOGIA. O merge-base tem de ser EXATAMENTE a ancora.
    # ------------------------------------------------------------------
    r = _git(repo, "merge-base", base_sha, head_sha)
    mb = r.stdout.strip() if r.returncode == 0 else ""
    if not mb:
        falhas.append(
            Falha(
                "ii",
                f"a base {base_sha[:12]} e o candidato {head_sha[:12]} nao tem\n"
                f"    ancestral comum. Nao ha comparacao possivel.",
            )
        )
    elif mb != start:
        if _e_ancestral(repo, head_sha, base_sha):
            # O caso degenerado, que o predicado anterior ja pegava. Mantido com
            # mensagem propria porque a leitura dele e mais simples e mais grave.
            falhas.append(
                Falha(
                    "ii",
                    f"o candidato {head_sha[:12]} JA ESTA CONTIDO na base.\n"
                    f"    A fase inteira foi mergeada antes do checkpoint: o diff e\n"
                    f"    vazio por construcao e nao ha nada a auditar como porta.",
                )
            )
        elif _e_ancestral(repo, start, mb):
            adiantados = _git(
                repo, "rev-list", "--count", f"{start}..{mb}"
            ).stdout.strip()
            falhas.append(
                Falha(
                    "ii",
                    f"a base ja contem {adiantados} commit(s) POSTERIOR(es) a ancora\n"
                    f"    da fase.\n"
                    f"        ancora     : {start[:12]}\n"
                    f"        merge-base : {mb[:12]}\n"
                    f"    Duas leituras, e as duas exigem acao:\n"
                    f"      - a fase foi mergeada PECA A PECA antes do checkpoint. E a\n"
                    f"        inversao real, e foi o H2 da segunda auditoria da Fase 3;\n"
                    f"      - ou a branch foi rebaseada e a ancora ficou desatualizada:\n"
                    f"        o ponto de bifurcacao mudou de verdade. Regrave a linha.",
                )
            )
        else:
            falhas.append(
                Falha(
                    "ii",
                    f"o merge-base {mb[:12]} nao e a ancora {start[:12]} e nem vem\n"
                    f"    depois dela: a base esta ATRAS da ancora. Topologia\n"
                    f"    inesperada — resolva antes de auditar.",
                )
            )

    # ------------------------------------------------------------------
    # (iii-a) CONTEUDO. Diff vazio com topologia sa e a assinatura do squash.
    # ------------------------------------------------------------------
    if _git(repo, "diff", "--quiet", base_sha, head_sha).returncode == 0:
        falhas.append(
            Falha(
                "iii-a",
                f"o diff contra a base e VAZIO: as duas arvores sao identicas.\n"
                f"    O conteudo da fase ja esta na base — tipicamente por\n"
                f"    squash-merge, que troca a identidade dos commits e deixa a\n"
                f"    topologia com cara de intacta.",
            )
        )

    # ------------------------------------------------------------------
    # (iii-b) CONTEUDO. Patch ja presente na base, com outra identidade.
    # ------------------------------------------------------------------
    cherry = _git(repo, "cherry", base_sha, head_sha)
    if cherry.returncode == 0:
        repetidos = [
            linha.split()[1][:12]
            for linha in cherry.stdout.splitlines()
            if linha.startswith("- ")
        ]
        if repetidos:
            falhas.append(
                Falha(
                    "iii-b",
                    f"{len(repetidos)} commit(s) de BASE..HEAD tem patch-id que JA\n"
                    f"    EXISTE na base: {', '.join(repetidos[:6])}"
                    + (" ..." if len(repetidos) > 6 else "")
                    + "\n"
                    f"    Parte do trabalho da fase chegou na base por cherry-pick ou\n"
                    f"    rebase — identidade diferente, conteudo o mesmo.",
                )
            )

    return falhas


def relata(falhas: list[Falha], fase: int, base_ref: str, explicito: bool) -> int:
    if not falhas:
        print(f"{REGRA}: fase {fase}, base '{base_ref}' — a auditoria e PORTA.")
        return 0

    corpo = "\n".join(f"  [{f.eixo}] {f.texto}" for f in falhas)

    if explicito:
        print(
            "\nAVISO: a base explicita NAO mostra todo o trabalho da fase.\n"
            f"{corpo}\n\n"
            "       Voce passou --base explicitamente, entao a auditoria segue —\n"
            "       mas ela e LAUDO, e nao porta: BLOCKER encontrado aqui pode ja\n"
            "       estar mergeado.\n",
            file=sys.stderr,
        )
        return 0

    print(
        f"\nERRO: a base de comparacao nao mostra o trabalho da fase {fase}.\n\n"
        f"{corpo}\n\n"
        "A ordem que 'docs/process/WORKFLOW.md' fixa e:\n\n"
        '    git commit -m "fase-<n>: checkpoint candidate"     # na branch da fase\n'
        "    bash scripts/start_checkpoint_audit.sh <n>          # <- aqui\n"
        "    gh pr create                                        # so depois\n\n"
        "O QUE FAZER:\n\n"
        "  (a) audite ANTES do merge, a partir da branch da fase;\n"
        "  (b) se o merge ja aconteceu e voce quer o laudo assim mesmo, passe a\n"
        "      base explicitamente e assuma que isto nao e mais um gate:\n"
        "          bash scripts/start_checkpoint_audit.sh <n> --base <ref>\n",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="A auditoria da fase ainda e porta?")
    p.add_argument("--phase", type=int, required=True)
    p.add_argument("--base", required=True, help="ref ou sha da base de comparacao")
    p.add_argument("--head", default="HEAD", help="o commit candidato")
    p.add_argument("--repo", default=".", help="raiz do repositorio a inspecionar")
    p.add_argument(
        "--explicit",
        action="store_true",
        help="o operador passou --base: avisa em vez de recusar",
    )
    a = p.parse_args(argv)

    raiz = _git(a.repo, "rev-parse", "--show-toplevel")
    if raiz.returncode != 0:
        print(f"{REGRA}: '{a.repo}' nao e um repositorio git.", file=sys.stderr)
        return 2

    return relata(
        avalia(raiz.stdout.strip(), a.phase, a.base, a.head),
        a.phase,
        a.base,
        a.explicit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
