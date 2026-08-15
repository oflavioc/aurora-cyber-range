#!/usr/bin/env python3
"""A tabela-resumo de pendencias bate com as secoes de detalhe.

POR QUE ISTO EXISTE
-------------------
A secao 1.6 do registro da Fase 1 nomeia uma classe de defeito: **afirmacao que
era verdadeira quando foi escrita e deixou de ser quando o artefato mudou**. Nao
ha momento em que alguem errou, e por isso nenhuma revisao de commit a pega.

A linha da tabela-resumo e exatamente uma afirmacao de estado sobre uma secao
que pode nao existir. E foi o que aconteceu, DUAS VEZES, no mesmo arquivo: ao
fechar a P1-18 descobriu-se que o texto dela sumira num splice, e a linha da
tabela seguia afirmando a pendencia; o cruzamento manual encontrou a P1-20 na
mesma situacao.

A regra sozinha nao segurou a propriedade — a 1.6 foi escrita e violada no mesmo
dia, enquanto era aplicada. Isto e a regra virando codigo.

O QUE VERIFICA
--------------
Para cada `docs/progress/fase_*.md`:

  1. toda linha da tabela-resumo tem secao de detalhe correspondente;
  2. toda secao de detalhe aparece na tabela-resumo;
  3. nenhum identificador aparece duas vezes na tabela ou duas vezes como secao.

Registro SEM tabela-resumo nao e conferido, e isso e limite declarado: `fase_0.md`
usa estilo cronologico, com uma entrada por rodada de auditoria, e o mesmo id
aparece na entrada do finding e na da resolucao. Sem tabela nao ha o que cruzar.

ESCOPO DA TABELA. So conta a PRIMEIRA tabela depois do cabecalho de pendencias.
Outras tabelas do documento podem citar identificadores de pendencia em outra
coluna — a tabela de ocorrencias da propria secao 1.6 faz isso — e conta-las
produziria falso positivo. Foi medido: sem este escopo, P1-14 e P1-15 apareciam
como duplicadas.

Arquivo sem cabecalho de pendencias ou sem tabela e ignorado, e nao e erro:
`fase_0.md` registra as suas em secoes sem tabela-resumo.

STDLIB PURA, e roda no job `arquitetura`. Nao vira job proprio DE PROPOSITO: job
novo e context novo, e context exigido antes de existir em `main` trava todo PR
que nao o produza — foi a P1-18, e repeti-la para verificar a P1-18 seria
particularmente ruim.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS = REPO_ROOT / "docs" / "progress"

#: `## 6. Pendências`, `## Pendencias`, com ou sem numero e acento.
CABECALHO_PENDENCIAS = re.compile(r"^##\s+(?:\d+\.\s+)?Pend[êe]ncias\s*$", re.I)

#: `| P1-18 | ...` ou `| P23 | ...` — primeira celula, sozinha, e o identificador.
LINHA_TABELA = re.compile(r"^\|\s*\*{0,2}(P\d+(?:-\d+)?)\*{0,2}\s*\|")

#: `#### P1-18 — ...` ou `### P23 — ...`, em qualquer nivel de 3 a 5.
SECAO = re.compile(r"^#{3,5}\s+(P\d+(?:-\d+)?)\s+[—-]")


def tabela_resumo(linhas: list[str]) -> list[str] | None:
    """Ids da PRIMEIRA tabela depois do cabecalho de pendencias, em ordem."""
    inicio = next(
        (i for i, l in enumerate(linhas) if CABECALHO_PENDENCIAS.match(l)), None
    )
    if inicio is None:
        return None

    ids: list[str] = []
    vista = False
    for linha in linhas[inicio + 1 :]:
        if linha.startswith("##"):
            break
        if linha.lstrip().startswith("|"):
            vista = True
            m = LINHA_TABELA.match(linha.strip())
            if m:
                ids.append(m.group(1))
        elif vista and linha.strip() == "":
            # Linha em branco depois da tabela: ela terminou. Tabelas seguintes
            # do mesmo documento nao sao a tabela-resumo.
            if ids:
                break
    return ids if vista else None


def duplicados(itens: list[str]) -> list[str]:
    vistos, repetidos = set(), []
    for i in itens:
        if i in vistos and i not in repetidos:
            repetidos.append(i)
        vistos.add(i)
    return repetidos


def main() -> int:
    arquivos = sorted(PROGRESS.glob("fase_*.md"))
    if not arquivos:
        print(f"ERRO: nenhum registro de fase em {PROGRESS}", file=sys.stderr)
        return 2

    falhas: list[str] = []
    conferidos = 0

    for caminho in arquivos:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        fonte = caminho.relative_to(REPO_ROOT).as_posix()

        ids_tabela = tabela_resumo(linhas)
        ids_secao = [m.group(1) for m in map(SECAO.match, linhas) if m]

        if ids_tabela is None:
            # Registro em estilo CRONOLOGICO, sem tabela-resumo: `fase_0.md`
            # traz a entrada do finding e, rodadas depois, a da resolucao, com o
            # mesmo id. Sao 19 rodadas de historia, e o id repetido ali e
            # deliberado — nao ha o que cruzar sem tabela, e reescrever registro
            # de fase encerrada seria pior que o defeito.
            #
            # LIMITE DECLARADO: registro sem tabela-resumo nao e conferido.
            continue

        conferidos += 1

        for rotulo, lista in (("tabela-resumo", ids_tabela), ("secao", ids_secao)):
            if repetidas := duplicados(lista):
                falhas.append(
                    f"{fonte}: {rotulo} repete {repetidas}. Duas entradas para a "
                    f"mesma pendencia podem afirmar estados diferentes."
                )

        sem_secao = [i for i in dict.fromkeys(ids_tabela) if i not in ids_secao]
        sem_tabela = [i for i in dict.fromkeys(ids_secao) if i not in ids_tabela]

        for i in sem_secao:
            falhas.append(
                f"{fonte}: {i} esta na tabela-resumo e NAO TEM secao de detalhe.\n"
                f"    A linha afirma um estado cujo referente nao existe — foi "
                f"assim que P1-18 e P1-20 se perderam."
            )
        for i in sem_tabela:
            falhas.append(
                f"{fonte}: {i} tem secao de detalhe e NAO ESTA na tabela-resumo.\n"
                f"    Pendencia invisivel no resumo e pendencia que a proxima "
                f"fase nao herda."
            )

    print(f"Registros de fase: {len(arquivos)}")
    print(f"  com tabela-resumo, conferidos: {conferidos}")

    if falhas:
        print(f"\nFALHAS: {len(falhas)}\n", file=sys.stderr)
        for f in falhas:
            print(f"  {f}\n", file=sys.stderr)
        return 1

    print("\nToda linha da tabela-resumo tem secao, e toda secao esta no resumo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
