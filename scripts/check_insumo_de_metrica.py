#!/usr/bin/env python3
"""`00` §3.2 — a superficie do insumo tipado, e o ponto unico de montagem.

O QUE ESTA CHECAGEM PROVA
-------------------------
A §3.2 fecha o bloco *"O que a assinatura verifica, e a costura que e fraca"* com
QUATRO exigencias. Tres delas sao propriedade de superficie e estao aqui; a
quarta ja tem mecanismo em outro lugar:

    (1) cada insumo tem TIPO PROPRIO, recusado se resolver para
        `Sequence[Event]`, `Iterable[Event]`, `list[Event]` ou alias deles;
    (2) o BANIDO e o fluxo total, o event store e o pack como objeto — o insumo
        carrega os escalares de que o lado precisa, e nada por onde buscar mais;
    (3) cada tipo tem UM UNICO PONTO DE MONTAGEM, e o construtor aparece so ali;
    (4) os lados vem do `metric_side` do catalogo, com cobertura total e
        disjuncao checadas sobre o atributo.

A (4) NAO ESTA AQUI de proposito, e a ausencia e declarada para nao ser lida como
buraco: ela e conferida na carga dos contratos, em
`range-core/engine/loader/contract_rules.py`, que reprova tipo sem `metric_side`,
`metric_side` para tipo fora do catalogo, valor fora do conjunto e lado declarado
sem nenhum `event_type`. Repeti-la aqui criaria segunda autoridade para o mesmo
fato — a forma que a §3.2 recusa ao proibir mapa proprio ao lado do catalogo.

POR QUE A (3) PRECISA DE VERIFICADOR, E NAO BASTA O TIPO
--------------------------------------------------------
A §3.2 chama esta costura de FRACA, e diz por que: `NewType` nao e barreira de
execucao. `EventosDeDeclaracao(fluxo_total)` escrito em qualquer lugar da arvore
COMPILA e roda, e o computador que o recebesse leria os dois lados do par sem que
nada falhasse — que e o defeito inteiro da secao, na forma em que ele e invisivel:
*"a metrica continua sendo calculada. Nada falha."*

O que impede nao e o tipo: e checagem de superficie sobre ONDE O CONSTRUTOR
APARECE. Ela e whitelist e nao blocklist, pela razao de sempre — nenhuma lista de
proibicoes preve a proxima palavra, e aqui a "proxima palavra" seria um segundo
montador com nome de conveniencia.

E MAIS FRACA QUE A D4, E ESTA DITO
-----------------------------------
A D4 garante *"nao tem flag ao alcance"*: o fold nao consegue consultar porque
nao ha parametro por onde um store entre. Aqui o veredito chega como DADO, e nao
como ausencia de caminho — o construtor existe e e importavel. A garantia e de
superficie, e vale enquanto esta checagem rodar. A §3.2 escolheu essa fraqueza de
olhos abertos; o que ela nao admite e que a fraqueza seja silenciosa.

O QUE ELA VARRE, E O QUE FICA FORA COM MOTIVO
----------------------------------------------
Varre `range-core/` e `domains/` — o codigo de producao, que e onde a particao
decide metrica de verdade.

`tests/` fica FORA, por decisao e nao por omissao do universo. Teste que monta um
insumo estreito a mao para exercitar um computador nao viola a particao: ele nao
computa metrica de exercicio nenhum, e a particao em si ja tem teste proprio em
`tests/test_metrics_insumo.py`. Varrer `tests/` proibiria a forma normal de
testar um consumidor em isolamento, e o custo cairia sobre a suite sem que a
garantia de producao ficasse mais forte.

IMPORTAR NAO E CONSTRUIR, e a checagem so olha CHAMADA
-------------------------------------------------------
Consumidor anota parametro com o tipo do lado dele — e para isso precisa
importa-lo. Proibir o import mataria a anotacao, que e justamente o que a (1)
existe para exigir. O que reprova e `ast.Call`: o construtor sendo INVOCADO fora
do ponto de montagem.

POR QUE EM `scripts/` E NAO EM `tools/`
---------------------------------------
`01` §2 normatiza SEIS verificadores, todos em `tools/`. Um setimo arquivo ali
contradiria a contagem que a spec fixa. Mesma decisao, mesmo motivo que
`check_store_read_surface.py`.

Roda no job `arquitetura`, que e stdlib puro — esta checagem tambem e.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULO = REPO_ROOT / "range-core" / "metrics" / "insumo.py"

#: As arvores de PRODUCAO varridas pela exigencia (3). Ver o cabecalho sobre
#: `tests/`.
RAIZES = ("range-core", "domains")

#: OS TRES TIPOS PROPRIOS, e a FORMA em que cada um tem de ser definido.
#:
#: Whitelist de forma, e nao lista de bases proibidas: exigir `NewType(nome,
#: tuple)` recusa de uma vez o alias simples — `EventosDeDeclaracao =
#: Sequence[Event]`, que resolve exatamente para o que a (1) bane —, a troca de
#: base e o tipo que deixa de ser proprio. Uma lista de bases banidas teria de
#: prever `Iterable`, `Collection`, `MutableSequence` e o alias que ninguem
#: escreveu ainda.
#:
#: O nome no `NewType` tem de ser o nome da variavel. `X = NewType("Y", tuple)`
#: produz um tipo cujo `__name__` mente, e mensagem de erro de tipo que nomeia
#: outra coisa e pior que nenhuma.
TIPOS: dict[str, str] = {
    "EventosDeDeclaracao": "tuple",
    "EventosDeVerificacao": "tuple",
    "EscrituracaoDeEpoch": "tuple",
}

#: O PONTO UNICO DE MONTAGEM. Uma funcao, e nao um modulo: construtor chamado no
#: topo do modulo, ou numa segunda funcao ao lado, ja seria segundo montador —
#: e a §3.2 exige "um unico ponto de montagem POR LADO", nao "um arquivo".
PONTO_DE_MONTAGEM = "monta"

#: A SUPERFICIE DECLARADA DE CADA INSUMO — exigencia (2), na forma do
#: `DECLARED_SURFACE` de `check_store_read_surface.py`: igualdade nas duas
#: direcoes, e nao ausencia de palavras proibidas.
#:
#: Campo novo reprova ate alguem vir aqui e declara-lo, o que forca a conversa
#: em vez de deixar `store: EventStore` entrar com nome de conveniencia. Campo
#: que some tambem reprova: a lista descreve o que ha, e nao o que se deseja.
#:
#: Os escalares ESTAO na lista de proposito. A §3.2: *"proibe-se ter por onde
#: buscar mais do que lhe foi dado, nao ter o que lhe e necessario"* — o limiar
#: de calibracao e a defensibilidade chegam ao verificador de `TTIV` como dado,
#: e nao por consulta ao pack.
CAMPOS_DECLARADOS: dict[str, dict[str, str]] = {
    "InsumoDeDeclaracao": {
        "eventos": "EventosDeDeclaracao",
        "epoch": "EscrituracaoDeEpoch",
    },
    "InsumoDeVerificacao": {
        "eventos": "EventosDeVerificacao",
        "epoch": "EscrituracaoDeEpoch",
        "limiar_de_calibracao": "float",
        "defensibilidade": "Mapping[str, float]",
    },
}

RULE = "00 secao 3.2 - insumo tipado de metrica"


def _fail(mensagem: str) -> int:
    print(f"{RULE}: {mensagem}", file=sys.stderr)
    return 1


def _rotulo(caminho: Path) -> str:
    """Relativo ao repositorio quando dentro dele, absoluto fora.

    Fora acontece na prova negativa, que monta arvore em diretorio temporario:
    `relative_to` levantaria `ValueError` ali, e a checagem morreria por erro de
    ferramenta em vez de reportar a violacao.
    """
    try:
        return caminho.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return caminho.as_posix()


def _tipos_proprios(arvore: ast.Module) -> list[str]:
    """Exigencia (1): os tres nomes existem, e na forma declarada."""
    achados: dict[str, ast.AST] = {}
    for node in arvore.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        alvo = node.targets[0]
        if isinstance(alvo, ast.Name) and alvo.id in TIPOS:
            achados[alvo.id] = node.value

    problemas: list[str] = []
    for nome, base in TIPOS.items():
        if nome not in achados:
            problemas.append(
                f"{nome} nao e definido no modulo. A (1) exige tipo proprio por "
                "lado; sem ele a assinatura aceita o fluxo inteiro e nao afirma nada."
            )
            continue

        # COMPARACAO ESTRUTURAL, e nao textual. `ast.unparse` normaliza aspas —
        # `NewType("X", tuple)` volta com aspas simples —, entao comparar a
        # string reprovaria a arvore limpa por estilo de citacao. Medido na
        # primeira execucao desta checagem.
        valor = achados[nome]
        if not _e_newtype(valor, nome, base):
            problemas.append(
                f"{nome} e definido como `{ast.unparse(valor)}`, e a forma "
                f'declarada e `NewType("{nome}", {base})`. Alias simples RESOLVE '
                "para o tipo de origem — `Sequence[Event]` nao nega nada, porque "
                "o fluxo inteiro o satisfaz."
            )
    return problemas


def _e_newtype(valor: ast.AST, nome: str, base: str) -> bool:
    """`NewType("<nome>", <base>)`, conferido no no e nao no texto."""
    return (
        isinstance(valor, ast.Call)
        and isinstance(valor.func, ast.Name)
        and valor.func.id == "NewType"
        and not valor.keywords
        and len(valor.args) == 2
        and isinstance(valor.args[0], ast.Constant)
        and valor.args[0].value == nome
        and isinstance(valor.args[1], ast.Name)
        and valor.args[1].id == base
    )


def _superficie_dos_insumos(arvore: ast.Module) -> list[str]:
    """Exigencia (2): os campos de cada insumo sao EXATAMENTE os declarados."""
    classes = {
        node.name: node
        for node in arvore.body
        if isinstance(node, ast.ClassDef) and node.name in CAMPOS_DECLARADOS
    }

    problemas: list[str] = []
    for nome, declarados in CAMPOS_DECLARADOS.items():
        if nome not in classes:
            problemas.append(
                f"classe {nome} nao encontrada no modulo. CAMPOS_DECLARADOS "
                "descreve o que ha, entao a lista envelheceu ou o insumo mudou "
                "de nome sem que ninguem viesse aqui."
            )
            continue

        presentes = {
            filho.target.id: ast.unparse(filho.annotation)
            for filho in classes[nome].body
            if isinstance(filho, ast.AnnAssign) and isinstance(filho.target, ast.Name)
        }

        for campo in sorted(set(presentes) - set(declarados)):
            problemas.append(
                f"{nome}.{campo}: campo nao declarado em CAMPOS_DECLARADOS "
                f"(anotado `{presentes[campo]}`). O banido e o fluxo total, o "
                "event store e o pack como objeto — se o campo e escalar do lado, "
                "declare aqui e diga por que; se e por onde buscar mais do que "
                "lhe foi dado, a (2) o recusa."
            )

        for campo in sorted(set(declarados) - set(presentes)):
            problemas.append(
                f"{nome}.{campo}: declarado em CAMPOS_DECLARADOS e ausente da "
                "classe. A lista descreve o que ha, entao ela envelheceu."
            )

        for campo in sorted(set(declarados) & set(presentes)):
            if presentes[campo] != declarados[campo]:
                problemas.append(
                    f"{nome}.{campo} esta anotado `{presentes[campo]}` e o "
                    f"declarado e `{declarados[campo]}`. Trocar a anotacao do "
                    "insumo e trocar o lado que ele carrega."
                )
    return problemas


def _chamadas_do_construtor(arvore: ast.Module) -> list[tuple[str, int, str | None]]:
    """Toda invocacao dos tres construtores, com a funcao que a contem.

    A funcao contentora e `None` quando a chamada esta no topo do modulo ou
    dentro de uma classe — e os dois casos sao violacao, porque nenhum deles e o
    ponto de montagem.
    """
    achadas: list[tuple[str, int, str | None]] = []

    def visita(node: ast.AST, dentro: str | None) -> None:
        for filho in ast.iter_child_nodes(node):
            if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visita(filho, filho.name)
                continue
            if (
                isinstance(filho, ast.Call)
                and isinstance(filho.func, ast.Name)
                and filho.func.id in TIPOS
            ):
                achadas.append((filho.func.id, filho.lineno, dentro))
            visita(filho, dentro)

    visita(arvore, None)
    return achadas


def _ponto_unico_de_montagem(modulo: Path, raizes: list[Path]) -> list[str]:
    """Exigencia (3): o construtor so aparece dentro de `monta`, no modulo dele."""
    problemas: list[str] = []
    resolvido = modulo.resolve()
    construidos: set[str] = set()

    for raiz in raizes:
        if not raiz.is_dir():
            continue
        for caminho in sorted(raiz.rglob("*.py")):
            try:
                arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
            except SyntaxError as erro:
                problemas.append(f"{_rotulo(caminho)}: nao pode ser lido ({erro}).")
                continue

            for nome, linha, dentro in _chamadas_do_construtor(arvore):
                if caminho.resolve() == resolvido and dentro == PONTO_DE_MONTAGEM:
                    construidos.add(nome)
                    continue

                onde = f"na funcao `{dentro}`" if dentro else "fora de funcao"
                problemas.append(
                    f"{_rotulo(caminho)}:{linha}: `{nome}` e CONSTRUIDO ali, "
                    f"{onde}. O ponto unico de montagem e "
                    f"`{_rotulo(modulo)}::{PONTO_DE_MONTAGEM}`.\n"
                    "    Construir o tipo estreito a partir do fluxo total "
                    "compila e roda, e o computador leria os dois lados do par "
                    "sem que nada falhasse — 00 secao 3.2."
                )

    for nome in sorted(set(TIPOS) - construidos):
        problemas.append(
            f"`{nome}` nunca e construido em "
            f"`{_rotulo(modulo)}::{PONTO_DE_MONTAGEM}`. Tipo proprio que ninguem "
            "monta e tipo que nenhum consumidor recebe — a whitelist ficaria "
            "vazia e passaria por vacuidade."
        )
    return problemas


def main(argv: list[str] | None = None) -> int:
    """Sem argumento, confere a arvore real. Com um caminho, confere aquele modulo.

    O CAMINHO OPCIONAL EXISTE PARA A PROVA NEGATIVA, e nao afeta garantia
    nenhuma: e parametro de CLI. A alternativa era o probe plantar a violacao no
    arquivo REAL e restaurar — fragil pelo motivo obvio, e falha no meio deixa a
    arvore suja.

    A RAIZ VARRIDA ACOMPANHA O ALVO: com argumento, e a arvore ONDE ELE ESTA, o
    que permite ao probe montar um segundo arquivo com o construtor plantado sem
    escrever nada em `range-core/`.
    """
    argv = sys.argv[1:] if argv is None else argv
    modulo = Path(argv[0]) if argv else MODULO

    if not modulo.is_file():
        return _fail(f"{_rotulo(modulo)} nao existe")

    if argv:
        raizes = [modulo.resolve().parent.parent]
    else:
        raizes = [REPO_ROOT / raiz for raiz in RAIZES]

    try:
        arvore = ast.parse(modulo.read_text(encoding="utf-8"), str(modulo))
    except SyntaxError as erro:
        return _fail(f"{_rotulo(modulo)} nao pode ser lido ({erro})")

    problemas = _tipos_proprios(arvore)
    problemas.extend(_superficie_dos_insumos(arvore))
    problemas.extend(_ponto_unico_de_montagem(modulo, raizes))

    if problemas:
        for problema in problemas:
            print(f"{RULE}: {problema}", file=sys.stderr)
        return 1

    print(f"tipos proprios: {', '.join(sorted(TIPOS))}")
    print(
        f"ponto unico de montagem: {_rotulo(modulo)}::{PONTO_DE_MONTAGEM}; "
        f"nenhum construtor invocado em {' nem '.join(_rotulo(r) for r in raizes)}."
    )
    print(
        "campos de insumo conferidos nas duas direcoes: "
        + "; ".join(f"{c} ({len(campos)})" for c, campos in CAMPOS_DECLARADOS.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
