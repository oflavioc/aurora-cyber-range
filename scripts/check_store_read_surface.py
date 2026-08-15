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

    print(f"superficie de {STORE_CLASS}: {', '.join(sorted(publicos))}")
    print("leitura sem parametro; nenhum filtro por epoch, abandono ou corte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
