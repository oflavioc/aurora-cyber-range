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

E entre fases consecutivas — a entrega da peca 1 da Fase 7:

  4. **todo item NAO-FECHADO da fase N aparece na tabela da fase N+1.**

A PAUTA HERDADA, E POR QUE ELA E A MESMA PERGUNTA
---------------------------------------------------
Os tres primeiros predicados cruzam tabela e secao DENTRO de um registro. O
quarto cruza a tabela de um registro com a do seguinte, e o defeito e o mesmo da
§1.6: afirmacao verdadeira quando escrita, falsa quando o artefato andou. Aqui o
artefato que anda e a FASE.

**Medido:** `e571091` abriu a branch da Fase 7 sem cinco pendencias da Fase 6, e
nenhum gate viu. As cinco foram achadas por leitura, transcritas a mao, e a mao
que transcreve e exatamente o que nao pode ser o mecanismo.

A DIRECAO E DE N PARA N+1, e ela e escolhida: e a que pega OMISSAO. A inversa —
*"todo item da N+1 veio de algum lugar"* — pegaria invencao, que nao e o defeito
que aconteceu.

O VOCABULARIO DE ESTADO, fechado a partir da Fase 7 e declarado no registro dela:

    ABERTA · LATENTE · DECIDIDA · VENCIDA   -> NAO-FECHADOS, e migram
    RESOLVIDA                               -> fechada, nao migra
    ENTREGA                                 -> trabalho da propria fase, nao migra

Estado fora do enum REPROVA. Ele nao pode ser classificado como fechado nem como
aberto, e escolher um dos dois em silencio degradaria onde a pergunta e.

DUAS DEGRADACOES, e as duas se ANUNCIAM. Fase seguinte que nao existe, e registro
cuja tabela-resumo nao declara coluna de estado — `fase_1.md` ate `fase_5.md`,
anteriores ao vocabulario — sao PULADOS com a razao impressa. Par nao conferido
que nao se anuncia e indistinguivel de par conferido e verde, e essa confusao e a
classe que este arquivo inteiro persegue.

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

#: `| P6-7 | ...o que e... | `VENCIDA` | ...gatilho... |` — a TERCEIRA celula.
#: Casa so a tabela de quatro colunas; a de tres nao produz par nenhum, e e assim
#: que `estados_da_tabela` distingue "sem estado declarado" de "sem pendencia".
LINHA_COM_ESTADO = re.compile(
    r"^\|\s*\*{0,2}(P\d+(?:-\d+)?)\*{0,2}\s*\|[^|]*\|\s*[`*]*([A-Z]+)[`*]*\s*\|"
)

#: O ENUM, FECHADO — a mesma lista que o registro da Fase 7 declara em prosa.
#: Valor fora daqui REPROVA, e nao e ignorado: estado que o verificador nao
#: entende e estado que ele nao pode classificar como fechado nem como aberto, e
#: escolher um dos dois em silencio seria degradar exatamente onde a pergunta e.
NAO_FECHADOS = ("ABERTA", "LATENTE", "DECIDIDA", "VENCIDA")
FECHADOS = ("RESOLVIDA",)

#: `ENTREGA` e trabalho da PROPRIA fase, e nao pendencia a carregar. Nao migra, e
#: nao e cobrada na fase seguinte — o que a cobra e a Definition of Done dela.
NAO_MIGRA = ("ENTREGA",)

ESTADOS = frozenset(NAO_FECHADOS + FECHADOS + NAO_MIGRA)


def _linhas_da_tabela(
    linhas: list[str], inicio: int, *, ancorada: bool
) -> list[str] | None:
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
    corpo: list[str] = []
    vista = False
    for linha in linhas[inicio:]:
        if linha.startswith("##"):
            break
        if linha.lstrip().startswith("|"):
            vista = True
            corpo.append(linha.strip())
        elif vista and linha.strip() == "":
            # Linha em branco depois da tabela: ela terminou.
            if ancorada or any(LINHA_TABELA.match(c) for c in corpo):
                break
    return corpo if vista else None


def _localiza(linhas: list[str]) -> list[str] | None:
    """As linhas da tabela-resumo, pelo marcador quando ele existe.

    UM UNICO lugar decide QUAL tabela e a tabela-resumo, e os dois consumidores
    — `tabela_resumo` e `estados_da_tabela` — leem daqui. Duas localizacoes sobre
    a mesma fronteira divergem, e a que diverge em silencio e a que ninguem esta
    olhando: um leitor de estado com a sua propria heuristica poderia classificar
    a tabela errada enquanto o de ids lia a certa.
    """
    marcador = next((i for i, l in enumerate(linhas) if MARCADOR.match(l)), None)
    if marcador is not None:
        return _linhas_da_tabela(linhas, marcador + 1, ancorada=True)

    inicio = next(
        (i for i, l in enumerate(linhas) if CABECALHO_PENDENCIAS.match(l)), None
    )
    if inicio is None:
        return None
    return _linhas_da_tabela(linhas, inicio + 1, ancorada=False)


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
    corpo = _localiza(linhas)
    if corpo is None:
        return None
    return [m.group(1) for m in map(LINHA_TABELA.match, corpo) if m]


def estados_da_tabela(linhas: list[str]) -> dict[str, str] | None:
    """`{id: estado}` da tabela-resumo, ou `None` se ela nao declara estado.

    `None` NAO e "sem pendencia" nem "tudo fechado": e *"este registro nao
    responde a pergunta"*, e quem chama tem de PULAR o par dizendo por que. A
    tabela de tres colunas — `fase_1.md` ate `fase_5.md` — cai aqui.
    """
    corpo = _localiza(linhas)
    if corpo is None:
        return None
    estados = {
        m.group(1): m.group(2) for m in map(LINHA_COM_ESTADO.match, corpo) if m
    }
    return estados or None


def confere_pauta(
    registros: dict[int, list[str]],
) -> tuple[list[str], list[str]]:
    """TODO ITEM NAO-FECHADO DA FASE N APARECE NA TABELA DA FASE N+1?

    Devolve `(falhas, pulos)`. Os pulos sao impressos: par nao conferido que nao
    se anuncia e indistinguivel de par conferido e verde, e essa confusao e a
    propria classe de defeito que este arquivo persegue.

    A DIRECAO E DE N PARA N+1, e ela e escolhida: e a que pega OMISSAO. A
    inversa — "todo item da N+1 veio de algum lugar" — pegaria invencao, que nao
    e o defeito que aconteceu. O que aconteceu foi `e571091` abrir a branch da
    Fase 7 sem cinco pendencias da Fase 6, e nenhum gate ver.
    """
    falhas: list[str] = []
    pulos: list[str] = []

    for fase in sorted(registros):
        estados = estados_da_tabela(registros[fase])
        if estados is None:
            pulos.append(
                f"fase {fase} -> {fase + 1}: a tabela-resumo da fase {fase} nao "
                "declara coluna de estado (tabela de tres colunas, anterior ao "
                "vocabulario fechado da Fase 7). Sem estado nao da para dizer o "
                "que era para migrar."
            )
            continue

        desconhecidos = sorted(
            {e for e in estados.values() if e not in ESTADOS}
        )
        if desconhecidos:
            falhas.append(
                f"fase {fase}: estado fora do enum: {desconhecidos}.\n"
                f"    O vocabulario e fechado — {sorted(ESTADOS)} —, e valor novo "
                f"nao pode ser classificado como fechado nem como aberto.\n"
                f"    Escolher um dos dois em silencio degradaria exatamente onde "
                f"a pergunta e."
            )
            continue

        seguinte = registros.get(fase + 1)
        if seguinte is None:
            pulos.append(
                f"fase {fase} -> {fase + 1}: nao existe "
                f"`docs/progress/fase_{fase + 1}.md`. A fase seguinte ainda nao "
                "abriu, e nao ha destino contra o que cobrar a pauta."
            )
            continue

        ids_seguinte = tabela_resumo(seguinte)
        if ids_seguinte is None:
            pulos.append(
                f"fase {fase} -> {fase + 1}: a fase {fase + 1} nao tem "
                "tabela-resumo legivel. Nao ha contra o que cruzar."
            )
            continue

        destino = set(ids_seguinte)
        devidos = [i for i, e in estados.items() if e in NAO_FECHADOS]
        faltando = [i for i in devidos if i not in destino]

        for item in faltando:
            falhas.append(
                f"fase {fase} -> {fase + 1}: `{item}` esta `{estados[item]}` na "
                f"fase {fase} e NAO APARECE na tabela da fase {fase + 1}.\n"
                f"    Pendencia nao-fechada que nao e transcrita some sem que "
                f"ninguem decida fecha-la — e sumir por omissao nao e o mesmo "
                f"que fechar.\n"
                f"    Transcreva-a no registro da fase {fase + 1}, ou feche-a na "
                f"fase {fase} com o conserto no repositorio."
            )

    return falhas, pulos


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
    registros: dict[int, list[str]] = {}

    for caminho in arquivos:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        fonte = caminho.relative_to(REPO_ROOT).as_posix()

        if (numero := re.fullmatch(r"fase_(\d+)", caminho.stem)) is not None:
            registros[int(numero.group(1))] = linhas

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

    falhas_de_pauta, pulos = confere_pauta(registros)
    falhas += falhas_de_pauta

    print(f"Registros de fase: {len(arquivos)}")
    print(f"  com tabela-resumo, conferidos: {conferidos}")
    pares = len(registros) - len(pulos)
    print(f"  pares de pauta conferidos: {pares if pares > 0 else 0}")

    # OS PULOS SAO IMPRESSOS, e essa e a diferenca entre "nao conferido" e
    # "conferido e verde". Degradacao que nao se anuncia e a forma de silencio
    # que este arquivo inteiro existe para nao ter.
    for pulo in pulos:
        print(f"  PULADO — {pulo}")

    if falhas:
        print(f"\nFALHAS: {len(falhas)}\n", file=sys.stderr)
        for f in falhas:
            print(f"  {f}\n", file=sys.stderr)
        return 1

    print(
        "\nToda linha da tabela-resumo tem secao, toda secao esta no resumo, e "
        "toda\npendencia nao-fechada de uma fase aparece na tabela da seguinte."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
