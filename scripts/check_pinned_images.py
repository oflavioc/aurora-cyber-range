#!/usr/bin/env python3
"""Imagem pinada por digest, e o MESMO digest nos dois lugares que a declaram.

POR QUE ESTA CHECAGEM EXISTE — P3-1
------------------------------------
Na peca 3 eu escrevi um servico de Redis no workflow do CI e **inventei o
digest**, com o `docker-compose.yml` do repositorio ja tendo o valor pinado ao
lado. Foi pego por `grep` no fim da rodada, e nao por mecanismo — o que quer
dizer que na rodada seguinte poderia nao ser pego.

Um digest inventado tem duas saidas, e a segunda e a que preocupa: o job quebra
com "manifest unknown", ou ele **resolve para outra coisa**. No segundo caso o
CI passa a testar contra uma imagem que nao e a que roda localmente, e a
divergencia aparece como teste instavel, longe da causa.

O QUE ELA AFIRMA
----------------
1. **Toda imagem esta pinada por digest.** Tag e ponteiro movel: `redis:7.4.1-
   alpine` de hoje e de daqui a um mes podem ser bytes diferentes, e o
   `00_MASTER_SPEC.md` §8 exige versao pinada. O proprio `docker-compose.yml`
   ja argumentava isso em comentario desde a Fase 1 — agora e verificado.
2. **Imagem declarada nos dois arquivos tem digest identico.** E o eixo que
   pegaria o defeito de origem.
3. **Imagem do CI existe no compose.** O compose e a stack; o CI existe para
   espelha-la. Servico que so o CI conhece e stack que ninguem consegue rodar
   localmente — e foi assim que o digest inventado entrou, sem par com que ser
   comparado.

O LIMITE, DECLARADO
-------------------
Varredura de LINHA por `image:`, e nao parse de YAML. Nao e desleixo: o
`.github/workflows/*.yml` usa `on:` como chave, que o parser estrito de
`tools/_common.py` recusa por construcao, e trazer PyYAML para ca faria um gate
depender de dependencia instalada — a fronteira que o `pyproject.toml` declara e
que a Fase 0 construiu.

A varredura e CONSERVADORA na direcao que importa: ela pode achar um `image:`
dentro de um bloco de comentario e cobrar digest dele, o que custa uma
justificativa humana. O que ela nao faz e PERDER um `image:` de verdade, que
seria o falso negativo. E a mesma regra que `01` §2 fixa para a excecao de
TypeScript.

Stdlib pura. Roda no job `arquitetura`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent

RULE = "imagens pinadas por digest, e iguais nos dois lugares"

#: `(rotulo, caminho)`. O compose e a FONTE — ver o eixo 3.
COMPOSE = ("docker-compose.yml", REPO_ROOT / "docker-compose.yml")
WORKFLOW = (
    ".github/workflows/invariants.yml",
    REPO_ROOT / ".github" / "workflows" / "invariants.yml",
)

MARCA = "image:"
DIGEST = "@sha256:"


def imagens(caminho: Path) -> dict[str, str]:
    """`nome:tag -> digest` de cada `image:` do arquivo. Sem digest, valor vazio.

    Devolver o nome SEM o digest como chave e o que torna a comparacao possivel:
    duas declaracoes da mesma imagem com digests diferentes viram a mesma chave
    com valores distintos, em vez de duas entradas que nao se encontram.
    """
    achadas: dict[str, str] = {}
    if not caminho.is_file():
        return achadas

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        limpa = linha.strip().lstrip("#").strip()
        if not limpa.startswith(MARCA):
            continue
        valor = limpa[len(MARCA):].strip().strip("'\"")
        if not valor:
            continue
        nome, _, digest = valor.partition(DIGEST)
        achadas[nome] = digest
    return achadas


def verifica(
    do_compose: dict[str, str],
    do_workflow: dict[str, str],
) -> list[str]:
    """Os tres eixos. Tudo por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    for rotulo, declaradas in ((COMPOSE[0], do_compose), (WORKFLOW[0], do_workflow)):
        for nome, digest in sorted(declaradas.items()):
            if not digest:
                problemas.append(
                    f"{rotulo}: `{nome}` nao esta pinada por digest.\n"
                    "    Tag e ponteiro movel — o mesmo texto resolve para bytes "
                    "diferentes em datas diferentes. `00` §8 exige versao pinada."
                )

    for nome in sorted(set(do_workflow) - set(do_compose)):
        problemas.append(
            f"{WORKFLOW[0]}: `{nome}` nao existe em {COMPOSE[0]}.\n"
            "    O compose e a stack, e o CI existe para espelha-la. Servico so "
            "do CI e stack que ninguem roda localmente — e digest sem par com "
            "que ser comparado."
        )

    for nome in sorted(set(do_compose) & set(do_workflow)):
        if do_compose[nome] and do_workflow[nome] and do_compose[nome] != do_workflow[nome]:
            problemas.append(
                f"`{nome}` tem digests DIFERENTES nos dois arquivos:\n"
                f"    {COMPOSE[0]}: @sha256:{do_compose[nome]}\n"
                f"    {WORKFLOW[0]}: @sha256:{do_workflow[nome]}\n"
                "    O CI passaria a testar contra uma imagem que nao e a que "
                "roda localmente, e a divergencia apareceria como teste instavel."
            )

    return problemas


def main(argv: list[str] | None = None) -> int:
    do_compose = imagens(COMPOSE[1])
    do_workflow = imagens(WORKFLOW[1])

    # ANTI-VACUIDADE. Sem esta linha, um `MARCA` errado — ou os arquivos mudando
    # de lugar — faria os dois dicionarios virem vazios e a checagem imprimir
    # "0 imagens, todas pinadas". E a forma exata de passar verde por nao
    # enxergar, que os probes da peca 3 acharam duas vezes.
    if not do_compose:
        print(
            f"{RULE}: nenhuma imagem encontrada em {COMPOSE[0]}. A varredura "
            "deixou de enxergar, ou o arquivo mudou de lugar.",
            file=sys.stderr,
        )
        return 2

    problemas = verifica(do_compose, do_workflow)
    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(do_compose)} imagens no compose e {len(do_workflow)} no "
        "workflow, todas pinadas por digest e sem divergencia entre os dois."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
