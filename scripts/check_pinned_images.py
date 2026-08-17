#!/usr/bin/env python3
"""Imagem pinada por digest, e o MESMO digest em todo lugar que a declara.

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
2. **Imagem declarada em mais de um arquivo tem digest identico.** E o eixo que
   pegaria o defeito de origem.
3. **Imagem de qualquer arquivo existe no compose.** O compose e a stack; os
   outros existem para espelha-la. Imagem que so um deles conhece e stack que
   ninguem consegue rodar localmente — e foi assim que o digest inventado
   entrou, sem par com que ser comparado.

Sao TRES arquivos desde o fechamento da P2-19, e nao dois: o compose do projeto,
o workflow do CI e o compose efemero da auditoria.

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

RULE = "imagens pinadas por digest, e iguais em todos os lugares que as declaram"

#: `(rotulo, caminho)`. O compose e a FONTE — ver o eixo 3.
COMPOSE = ("docker-compose.yml", REPO_ROOT / "docker-compose.yml")

#: OS DEMAIS ARQUIVOS QUE DECLARAM IMAGEM, e a lista cresce.
#:
#: A primeira versao desta checagem comparava DOIS arquivos, porque dois era
#: quantos existiam. Ao fechar a P2-19 apareceu o terceiro — o compose efemero
#: da auditoria —, e comparar dois de tres teria reintroduzido exatamente o
#: defeito que a P3-1 fechou, com um arquivo a mais em vez de um digest a mais.
OUTROS = [
    (
        ".github/workflows/invariants.yml",
        REPO_ROOT / ".github" / "workflows" / "invariants.yml",
    ),
    ("docker-compose.audit.yml", REPO_ROOT / "docker-compose.audit.yml"),
    # O QUARTO ARQUIVO — peca 7 da Fase 4. Imagem passou a entrar por uma
    # segunda forma sintatica: `FROM`, no `Dockerfile`. Sem esta entrada, o
    # estagio de Node da imagem poderia apontar para um digest DIFERENTE do que
    # o `web-build` usa, e o build do container e o build da maquina de quem
    # desenvolve deixariam de ser o mesmo — que e a P3-1 exata, com `FROM` no
    # lugar de `image:`.
    ("Dockerfile", REPO_ROOT / "Dockerfile"),
]

#: OS ARQUIVOS ISENTOS DO EIXO 3, com o motivo.
#:
#: O eixo 3 pergunta *"esta imagem e um servico que alguem consegue subir
#: localmente?"*, e a resposta para uma imagem-BASE de build e nao — ela nunca
#: sobe como servico. `python:3.12.7-slim` existe so no `Dockerfile`, e exigir
#: que ele aparecesse no compose obrigaria a inventar um servico que ninguem
#: roda, ou a escrever a linha num comentario para enganar a varredura.
#:
#: **O eixo 2 continua valendo para ele**, e e o que importa: `node` esta nos
#: DOIS arquivos, e os dois digests tem de ser iguais. O que a isencao custa e
#: que o digest do `python` nao tem par — e isso e verdade sobre o mundo, nao
#: sobre a checagem: ele so e declarado uma vez.
SEM_ESPELHO = frozenset({"Dockerfile"})

MARCA = "image:"
#: A segunda forma. `FROM <imagem> AS <estagio>` — o sufixo sai antes da
#: comparacao, senao `node:...@sha256:... AS cliente` e `node:...@sha256:...`
#: seriam chaves diferentes e o eixo 2 nunca dispararia.
MARCA_DOCKERFILE = "FROM "
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
        if limpa.startswith(MARCA):
            valor = limpa[len(MARCA):].strip().strip("'\"")
        elif limpa.startswith(MARCA_DOCKERFILE):
            valor = limpa[len(MARCA_DOCKERFILE):].strip().strip("'\"")
            # `FROM <imagem> AS <estagio>` — o estagio nao faz parte do nome.
            for separador in (" AS ", " as "):
                valor = valor.split(separador)[0].strip()
        else:
            continue
        if not valor:
            continue
        nome, _, digest = valor.partition(DIGEST)
        achadas[nome] = digest
    return achadas


def verifica(
    do_compose: dict[str, str],
    outros: list[tuple[str, dict[str, str]]],
    sem_espelho: frozenset[str] = SEM_ESPELHO,
) -> list[str]:
    """Os tres eixos, sobre N arquivos. Tudo por parametro, para o probe injetar.

    `sem_espelho` isenta um arquivo do EIXO 3 — e so dele. Ver `SEM_ESPELHO`.
    """
    problemas: list[str] = []
    todos = [(COMPOSE[0], do_compose), *outros]

    for rotulo, declaradas in todos:
        for nome, digest in sorted(declaradas.items()):
            if not digest:
                problemas.append(
                    f"{rotulo}: `{nome}` nao esta pinada por digest.\n"
                    "    Tag e ponteiro movel — o mesmo texto resolve para bytes "
                    "diferentes em datas diferentes. `00` §8 exige versao pinada."
                )

    for rotulo, declaradas in outros:
        # SO O EIXO 3 e isentado. O `continue` que eu escrevi primeiro pulava o
        # laco inteiro — e levava o EIXO 2 junto, que e justamente o que a
        # entrada do `Dockerfile` existe para exercer: `node` esta nos dois
        # arquivos e os digests tem de ser iguais. A isencao e de uma pergunta,
        # nao do arquivo.
        for nome in sorted(() if rotulo in sem_espelho else set(declaradas) - set(do_compose)):
            problemas.append(
                f"{rotulo}: `{nome}` nao existe em {COMPOSE[0]}.\n"
                "    O compose e a stack, e os outros existem para espelha-la. "
                "Imagem que so um deles conhece e digest sem par com que ser "
                "comparado — que foi como o digest inventado da peca 3 entrou."
            )

        for nome in sorted(set(do_compose) & set(declaradas)):
            if do_compose[nome] and declaradas[nome] and do_compose[nome] != declaradas[nome]:
                problemas.append(
                    f"`{nome}` tem digests DIFERENTES:\n"
                    f"    {COMPOSE[0]}: @sha256:{do_compose[nome]}\n"
                    f"    {rotulo}: @sha256:{declaradas[nome]}\n"
                    "    Seriam dois ambientes para o mesmo papel, e quem julga "
                    "deixaria de julgar o que o desenvolvedor roda."
                )

    return problemas


def main(argv: list[str] | None = None) -> int:
    do_compose = imagens(COMPOSE[1])
    outros = [(rotulo, imagens(caminho)) for rotulo, caminho in OUTROS]

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

    problemas = verifica(do_compose, outros)
    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    detalhe = ", ".join(f"{rotulo}: {len(d)}" for rotulo, d in outros)
    print(
        f"{RULE}: {len(do_compose)} imagens em {COMPOSE[0]} ({detalhe}), todas "
        f"pinadas por digest e sem divergencia entre os {len(outros) + 1} arquivos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
