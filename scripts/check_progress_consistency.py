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

ESCOPO DA TABELA — E ELE PASSOU A SER DECLARADO, EM VEZ DE ADIVINHADO
----------------------------------------------------------------------
A tabela-resumo agora se ANUNCIA, com o marcador `<!-- tabela-resumo-de-pendencias
-->` na linha acima dela. O parser procura o marcador e le a tabela que o segue.

**Por que deixou de ser por posicao.** A regra anterior era *"a primeira tabela,
depois do cabecalho de pendencias, que tenha ids"* — heuristica, e ela ficou
fragil no dia em que o registro da Fase 7 ganhou uma tabela de enum de estados
ANTES da tabela-resumo. Aquela tabela nao quebrou nada, mas so por causa da
guarda `if ids:` logo abaixo: ela marca `vista` sem contribuir id, e sem a guarda
a linha em branco seguinte encerraria a varredura e a tabela-resumo sumiria. Uma
tabela intercalada com id na primeira coluna — uma tabela de ocorrencias, por
exemplo — sequestraria a leitura sem nada acusar.

Isso importa mais do que o caso: o verificador de transcricao de pauta da Fase 7
le ESTAS MESMAS tabelas, e nascer sobre um parser que adivinha seria construir o
mecanismo com o defeito que ele existe para pegar.

**Por que comentario HTML, e nao cabecalho proprio.** Tres criterios:

  - **invisivel na renderizacao** — o marcador e ruido de mecanismo, e nao
    conteudo do registro; um `### Tabela-resumo` apareceria no sumario do GitHub
    e mudaria a estrutura de um documento que ja fechou auditado;
  - **inequivoco no parser** — string literal, linha inteira, ancorada;
  - **nao colide com a varredura** — e este e o argumento que elimina o
    cabecalho: `"###".startswith("##")` e VERDADEIRO em Python, entao um
    cabecalho de nivel 3 dispararia o `break` de fim de secao e mataria a leitura
    antes da tabela.

DEGRADACAO DELIBERADA. Registro SEM o marcador cai no comportamento anterior — a
primeira tabela com ids depois do cabecalho de pendencias. `fase_5.md` e
anteriores nao o tem e nao serao reprovados por isso: o marcador e melhoria, e
transformar melhoria em exigencia retroativa seria escopo que ninguem pediu.

Outras tabelas do documento podem citar identificadores de pendencia em outra
coluna — a tabela de ocorrencias da propria secao 1.6 faz isso — e conta-las
produziria falso positivo. Foi medido: sem este escopo, P1-14 e P1-15 apareciam
como duplicadas.

Arquivo sem cabecalho de pendencias e sem marcador e ignorado, e nao e erro:
`fase_0.md` registra as suas em secoes sem tabela-resumo.

Prova negativa em `scripts/check_progress_consistency_probes.py`, e o eixo que
decide e o da tabela intercalada: ela planta uma tabela com id ANTES da
tabela-resumo e exige que o marcador faca o parser ler a certa.

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

#: O MARCADOR, e ele e a linha inteira. Comentario HTML porque nao renderiza —
#: ver o cabecalho para os tres criterios e para por que cabecalho proprio nao
#: serve. Tolera espaco em volta e dentro; nao tolera texto ao lado, porque
#: marcador que casa por substring casaria tambem numa MENCAO a ele em prosa —
#: e este proprio docstring o menciona.
MARCADOR = re.compile(r"^\s*<!--\s*tabela-resumo-de-pendencias\s*-->\s*$")


def _colhe(linhas: list[str], inicio: int, *, ancorada: bool) -> list[str] | None:
    """Ids da proxima tabela a partir de `inicio`, em ordem.

    `ancorada` diz se um MARCADOR apontou para esta tabela, e e a unica diferenca
    de comportamento entre os dois modos — ela decide o que fazer com a linha em
    branco que encerra uma tabela sem id nenhum:

      - **ancorada**: para. O marcador declarou QUAL tabela e; se ela nao tem id,
        essa e a resposta, e procurar outra seria voltar a adivinhar.
      - **nao ancorada**: segue procurando, que e o comportamento herdado — a
        tabela-resumo e a primeira COM ids, e uma tabela sem id antes dela nao a
        esconde. E o unico motivo pelo qual a tabela de enum da Fase 7 nao
        quebrou a leitura antes do marcador existir.
    """
    ids: list[str] = []
    vista = False
    for linha in linhas[inicio:]:
        if linha.startswith("##"):
            break
        if linha.lstrip().startswith("|"):
            vista = True
            m = LINHA_TABELA.match(linha.strip())
            if m:
                ids.append(m.group(1))
        elif vista and linha.strip() == "":
            # Linha em branco depois da tabela: ela terminou.
            if ancorada or ids:
                break
    return ids if vista else None


def tabela_resumo(linhas: list[str]) -> list[str] | None:
    """Ids da tabela-resumo, pelo marcador quando ele existe.

    DUAS ROTAS, e a segunda e degradacao declarada e nao esquecimento:

      1. o registro DECLARA a tabela com `<!-- tabela-resumo-de-pendencias -->`, e
         a leitura e a tabela que segue o marcador — sem heuristica;
      2. o registro nao declara, e vale a regra herdada: a primeira tabela com
         ids depois do cabecalho de pendencias. `fase_5.md` e anteriores estao
         aqui, e reprova-los por nao terem um marcador criado depois deles seria
         exigencia retroativa.
    """
    marcador = next((i for i, l in enumerate(linhas) if MARCADOR.match(l)), None)
    if marcador is not None:
        return _colhe(linhas, marcador + 1, ancorada=True)

    inicio = next(
        (i for i, l in enumerate(linhas) if CABECALHO_PENDENCIAS.match(l)), None
    )
    if inicio is None:
        return None
    return _colhe(linhas, inicio + 1, ancorada=False)


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
