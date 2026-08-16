#!/usr/bin/env python3
"""P2-2 — a superficie de leitura do event store nao aceita filtro.

O QUE ESTA CHECAGEM PROVA
-------------------------
`01_ARCHITECTURE.md` §4.1: a leitura do store e total, e nenhum caminho de
leitura compartilhado filtra por epoch, por abandono ou por ponto de corte.

Essa garantia tem duas metades. A primeira esta no tipo do fold: `project`
recebe o fluxo e nao tem parametro por onde um store entre, entao a projecao nao
consegue consultar. A segunda e esta: **o store nao pode oferecer o filtro.**

POR QUE POR SUPERFICIE INTEIRA, E NAO POR LISTA DE PARAMETROS PROIBIDOS
------------------------------------------------------------------------
A P2-2 foi adiada de proposito ate a API existir. O motivo esta escrito no
registro da fase: enumerar `since`, `after`, `epoch`, `cursor` antes de o modulo
existir e inventar vocabulario para prever o modulo — classe da D6, e a proxima
palavra nao estaria na lista.

Com a API escrita, a enumeracao deixa de ser adivinhacao e passa a descrever o
que ha. E o que ha e mais forte que uma lista: `read_all` **nao tem parametro
nenhum**. Nao ha palavra a proibir porque nao ha onde escrever palavra.

Entao esta checagem afirma DUAS coisas, e a segunda e a que segura o futuro:

1. os metodos de leitura declarados nao aceitam parametro alem de `self`;
2. o conjunto de metodos publicos do store e EXATAMENTE o declarado aqui.

A (2) e um whitelist da superficie, e nao um blocklist de vocabulario. Metodo
publico novo reprova ate alguem vir aqui e declara-lo — o que forca a conversa
em vez de deixar `read_since(cursor)` entrar com nome de otimizacao.

POR QUE EM `scripts/` E NAO EM `tools/`
---------------------------------------
`01` §2 normatiza **seis** verificadores, todos em `tools/`. Um setimo arquivo
ali contradiria a contagem que a spec fixa, e exigiria `spec-change` para
acomodar decisao de implementacao. Ver a secao 6 do registro da Fase 2, onde a
distincao esta definida: verificador sao os seis; o que roda em `scripts/` e
checagem ou probe.

Roda no job `arquitetura`, que e stdlib puro — esta checagem tambem e.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = REPO_ROOT / "range-core" / "events" / "store.py"

#: A garantia vale para a BASE E PARA AS SUBCLASSES, e isto foi um buraco.
#:
#: A primeira versao desta checagem olhava so a classe em `store.py`. Uma
#: subclasse em outro arquivo — `PostgresEventStore`, por exemplo — podia
#: acrescentar `read_since(cursor)` e passar, porque a checagem nunca a via.
#: Apareceu ao escrever a segunda implementacao, que e quando esse tipo de
#: buraco aparece: a primeira nao tem com que divergir.
CORE_ROOT = REPO_ROOT / "range-core"

#: A classe cuja superficie e governada.
STORE_CLASS = "EventStore"

#: A SUPERFICIE PUBLICA DECLARADA. Acrescentar metodo publico ao store sem
#: acrescentar aqui reprova, e e o comportamento desejado.
DECLARED_SURFACE = frozenset({"append", "read_all"})

#: Metodos de leitura: nao aceitam NADA alem de `self`.
#:
#: `append` fica de fora desta regra porque recebe o `EventDraft` — escrita tem
#: entrada por natureza. A garantia da §4.1 e sobre LEITURA.
READ_METHODS = frozenset({"read_all"})

RULE = "P2-2 - superficie de leitura do event store"


def _fail(mensagem: str) -> int:
    print(f"{RULE}: {mensagem}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    """Sem argumento, confere o store real. Com um caminho, confere aquele.

    O CAMINHO OPCIONAL EXISTE PARA A PROVA NEGATIVA, e nao afeta a garantia: e
    parametro de CLI, nao de metodo de leitura. `read_all()` continua sem
    parametro, que e o que a §4.1 exige.

    A alternativa era o probe plantar a violacao no arquivo REAL e restaurar.
    Frágil pelo motivo obvio: falha no meio deixa a arvore suja, e o resultado
    passa a mentir sobre o que foi verificado.
    """
    argv = sys.argv[1:] if argv is None else argv
    alvo = Path(argv[0]) if argv else STORE_PATH

    # A RAIZ DO CORE ACOMPANHA O ALVO. Sem argumento, e o core de verdade. Com
    # um caminho — que so a prova negativa usa —, e a arvore ONDE ELE ESTA: e o
    # que permite ao probe montar uma arvore inteira com uma subclasse indireta
    # plantada, sem escrever nada em `range-core/`.
    #
    # Antes desta linha o fecho de subclasses varria sempre o core real, entao o
    # eixo de heranca indireta nao tinha como ser exercitado sem sujar a arvore.
    raiz_core = alvo.resolve().parent if argv else CORE_ROOT

    if not alvo.is_file():
        return _fail(f"{alvo} nao existe")

    tree = ast.parse(alvo.read_text(encoding="utf-8"), str(alvo))

    classe = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == STORE_CLASS:
            classe = node
            break

    if classe is None:
        return _fail(f"classe {STORE_CLASS} nao encontrada")

    publicos = {
        filho.name
        for filho in classe.body
        if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not filho.name.startswith("_")
    }

    problemas: list[str] = []

    sobrando = sorted(publicos - DECLARED_SURFACE)
    if sobrando:
        problemas.append(
            f"metodo publico nao declarado em DECLARED_SURFACE: {', '.join(sobrando)}. "
            "Se e leitura, ele precisa da mesma garantia; se nao e, declare aqui "
            "e diga por que."
        )

    faltando = sorted(DECLARED_SURFACE - publicos)
    if faltando:
        problemas.append(
            f"declarado em DECLARED_SURFACE e ausente da classe: {', '.join(faltando)}. "
            "A lista descreve o que ha, entao ela envelheceu."
        )

    for filho in classe.body:
        if not isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if filho.name not in READ_METHODS:
            continue

        args = filho.args
        posicionais = [a.arg for a in args.posonlyargs + args.args if a.arg != "self"]
        nomeados = [a.arg for a in args.kwonlyargs]
        extras = posicionais + nomeados

        if extras:
            problemas.append(
                f"{filho.name} aceita {', '.join(extras)}. Leitura do store e TOTAL: "
                "qualquer parametro e um lugar onde alguem escreve 'comeca depois "
                "do corte', e o filtro que 01 secao 4.1 proibe entra pela frente."
            )
        if args.vararg is not None or args.kwarg is not None:
            problemas.append(
                f"{filho.name} aceita *args ou **kwargs: parametro sem nome e "
                "parametro do mesmo jeito, e passa por baixo desta checagem."
            )

    if problemas:
        for problema in problemas:
            print(f"{RULE}: {problema}", file=sys.stderr)
        return 1

    problemas.extend(_subclasses_fora_da_linha(alvo, raiz_core))

    if problemas:
        for problema in problemas:
            print(f"{RULE}: {problema}", file=sys.stderr)
        return 1

    print(f"superficie de {STORE_CLASS}: {', '.join(sorted(publicos))}")
    print("leitura sem parametro; nenhum filtro por epoch, abandono ou corte.")
    return 0


def _rotulo(caminho: Path) -> str:
    """Caminho legivel: relativo ao repositorio quando dentro dele, absoluto fora.

    Fora do repositorio acontece na prova negativa, que monta arvore em
    diretorio temporario. `relative_to` levantaria `ValueError` ali, e a checagem
    morreria por erro de ferramenta em vez de reportar a violacao.
    """
    try:
        return caminho.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return caminho.as_posix()


def _descendentes_de(store_class: str, classes: dict) -> set[str]:
    """Fecho TRANSITIVO das classes que descendem de `EventStore`.

    POR QUE TRANSITIVO, E NAO SO FILHO DIRETO
    ------------------------------------------
    A primeira versao casava `bases` por nome contra `EventStore` e parava ai.
    Uma classe declarada `class X(InMemoryEventStore)` tem `bases ==
    {"InMemoryEventStore"}`, nao casava, e podia acrescentar `read_since(cursor)`
    publico sem reprovar — L2 da auditoria de 16/08/2026.

    E o MESMO buraco que o eixo de subclasse ja tinha fechado um nivel acima: a
    versao anterior a essa olhava so a classe da base e uma subclasse em outro
    arquivo passava. Fechar por um nivel de cada vez e o que faz o buraco voltar
    com outro nome; o fecho transitivo nao tem "proximo nivel".
    """
    alcancados = {store_class}
    mudou = True
    while mudou:
        mudou = False
        for nome, dados in classes.items():
            if nome in alcancados:
                continue
            if dados["bases"] & alcancados:
                alcancados.add(nome)
                mudou = True
    return alcancados - {store_class}


def _subclasses_fora_da_linha(ja_conferido: Path, raiz_core: Path) -> list[str]:
    """Toda DESCENDENTE de `EventStore` no core obedece a mesma superficie.

    Sem isto a garantia valeria so para a base, e a primeira implementacao
    concreta que quisesse um atalho o teria de graca — em outro arquivo, longe
    de onde a regra esta escrita.

    O arquivo da base tambem e varrido: `InMemoryEventStore` mora nele, e uma
    excecao por caminho deixaria de fora justamente a implementacao mais
    proxima da regra.
    """
    if not raiz_core.is_dir():
        return []

    # Passo 1: catalogar TODAS as classes do core, com bases e metodos publicos.
    # O fecho transitivo exige o mapa inteiro antes de decidir quem descende de
    # quem — nao da para julgar arquivo a arquivo.
    classes: dict[str, dict] = {}
    for caminho in sorted(raiz_core.rglob("*.py")):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
        for node in ast.walk(arvore):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
            bases |= {b.attr for b in node.bases if isinstance(b, ast.Attribute)}
            classes[node.name] = {
                "bases": bases,
                "arquivo": caminho,
                "publicos": [
                    filho.name
                    for filho in node.body
                    if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not filho.name.startswith("_")
                ],
            }

    # Passo 2: so entao, os descendentes.
    problemas: list[str] = []
    for nome in sorted(_descendentes_de(STORE_CLASS, classes)):
        dados = classes[nome]
        caminho = dados["arquivo"]
        # A superficie da propria base ja foi conferida pelo caminho principal,
        # com uma verificacao mais forte (ausencia de parametro nos metodos de
        # leitura). Aqui interessa quem HERDA dela.
        if caminho.resolve() == ja_conferido.resolve() and nome == STORE_CLASS:
            continue
        relativo = _rotulo(caminho)
        for metodo in dados["publicos"]:
            if metodo not in DECLARED_SURFACE:
                problemas.append(
                    f"{relativo}: {nome}.{metodo} e publico e nao esta "
                    "em DECLARED_SURFACE. Descendente nao amplia a superficie do "
                    "store — a garantia de 01 secao 4.1 vale para todas."
                )
    return problemas


if __name__ == "__main__":
    raise SystemExit(main())
