#!/usr/bin/env python3
"""O cliente PINTA o payload. Nao seleciona, nao ordena, nao agrega.

POR QUE ISTO EXISTE, E POR QUE ANTES DO CLIENTE
------------------------------------------------
A D17 moveu o corte de telao para dentro de `wallboard()`: o servidor decide o
que cabe em 10 m, e o orcamento virou teste — *"nunca mais de
`DESTAQUES_NO_TELAO` itens, qualquer que seja o estado"*.

**Essa propriedade morre em silencio se o cliente reordenar, expandir ou
recompor.** Um `.sort()` no TypeScript troca quais tres aparecem; um `.filter()`
troca o criterio; um `.slice()` reimplementa o corte com outro numero. Em todos
os casos o teste de orcamento continua VERDE — ele mede o payload — e a
propriedade real passa a viver no cliente, que e o unico lugar onde defeito nao
fica vermelho (a §2.2 do registro da fase).

E a D2 com nome: **toda derivacao e do servidor; o TS recebe pronto e pinta.**

A FORMA E A DA PECA 1, E ELA E DELIBERADA
-------------------------------------------
Este verificador nasce **antes** das tres telas, como `api_surface.yaml` nasceu
antes das rotas. O que se declara antes do codigo nao e a lista — e a
**obrigacao**: a proxima sessao nao consegue escrever um cliente que deriva sem
que isto reprove.

E ele NAO nasce vacuo: `range-core/web/sala.html` ja e cliente, ja consome os
dois canais e ja e varrido aqui. Verificador que so passa por nao ter o que olhar
e a §7.3 — a verificacao que parece existir.

AS TRES REGRAS
--------------
1. **Metodos de selecao, ordenacao e agregacao sao proibidos.** A whitelist do
   renderizador e curta: `map`, `join`, `forEach`, `push`. Quem precisa de
   `sort`, `filter`, `slice`, `reduce` ou `find` esta decidindo o que mostrar —
   e essa decisao e do servidor.

2. **As colecoes do payload so sao consumidas por `.map(`.** Regra mais estreita
   que a primeira e que se sobrepoe a ela de proposito: contencao por duas
   regras que se cobrem e o desenho deste projeto, e apoiar-se so numa e apostar
   que ela nao mude.

3. **`.length` em comparacao e proibido.** E assim que um orcamento se
   reimplementa no cliente — `if (destaques.length > 3)`. O payload ja traz
   `omitidos` como NUMERO justamente para que o cliente nao precise contar.

O QUE ESTE VERIFICADOR NAO ALCANCA, DECLARADO
-----------------------------------------------
E **varredura lexica**, e nao analise de sintaxe — a mesma excecao que `01` §2
admite para TypeScript e que `tools/check_contract_literals.py` ja usa. Um
cliente determinado escapa: `const f = arr["sor" + "t"]`, ou um helper importado
de outro diretorio.

**O que sustenta a propriedade nao e esta varredura, e sim o payload.** Os blocos
nao carregam texto de item, `omitidos` e um numero e nao uma lista, e o `rotulo`
chega pronto — nao ha partes para recompor. Isto e a segunda camada, e a ordem
de defesa do projeto e essa: hook, gate, auditor, e nenhum substitui outro.

Stdlib pura. Roda no job `arquitetura`, que nao instala nada.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "range-core" / "web"

EXTENSOES = (".ts", ".tsx", ".js", ".jsx", ".html")

#: O renderizador precisa destes. `push` entra porque montar a lista de linhas a
#: partir do que o servidor mandou e renderizacao, e nao selecao.
PERMITIDOS = frozenset({"map", "join", "forEach", "push"})

#: Selecionam, ordenam ou agregam. Cada um troca QUAIS itens aparecem, ou em que
#: ordem — que e a decisao que a D17 poe no servidor.
PROIBIDOS = (
    "sort", "reverse", "filter", "slice", "splice", "reduce", "reduceRight",
    "find", "findIndex", "findLast", "some", "every", "flat", "flatMap",
)

#: As colecoes do payload de telao. Ver `range-core/api/projecoes.py`.
COLECOES = ("destaques", "paineis", "itens", "entradas")

_METODO_PROIBIDO = re.compile(r"\.(" + "|".join(PROIBIDOS) + r")\s*\(")
_COLECAO = re.compile(r"\.(" + "|".join(COLECOES) + r")\s*\.\s*(\w+)\s*\(")
_LENGTH_COMPARADO = re.compile(r"\.length\s*[<>!=]|[<>]=?\s*[\w.]+\.length")


def _exibe(caminho: Path) -> str:
    """Relativo a raiz quando possivel, absoluto quando nao.

    `relative_to` LEVANTA fora da raiz, e o probe da vacuidade aponta `WEB` para
    um diretorio temporario justamente para provar a reprovacao — a mensagem de
    erro estourava antes de ser impressa. **Falha de instrumento no caminho de
    REPROVACAO e a pior que existe:** ela so aparece quando o verificador esta
    certo, e ate la o probe nao consegue afirmar nada. Achado rodando.
    """
    try:
        return caminho.relative_to(RAIZ).as_posix()
    except ValueError:
        return caminho.as_posix()


def _linha(texto: str, posicao: int) -> int:
    return texto[:posicao].count("\n") + 1


def varre(caminho: Path, texto: str) -> list[str]:
    relativo = _exibe(caminho)
    problemas: list[str] = []

    for achado in _METODO_PROIBIDO.finditer(texto):
        problemas.append(
            f"{relativo}:{_linha(texto, achado.start())}\n"
            f"    `.{achado.group(1)}(` seleciona, ordena ou agrega — e o cliente "
            "PINTA.\n"
            "    A D17 poe o corte de telao em `wallboard()`, e um corte no TS o\n"
            "    reimplementa com outro criterio sem nada ficar vermelho: o teste\n"
            "    de orcamento mede o PAYLOAD, e o payload continuaria certo.\n"
            f"    Permitidos: {', '.join(sorted(PERMITIDOS))}."
        )

    for achado in _COLECAO.finditer(texto):
        # `map` E SO `map`, e nao a whitelist inteira. A primeira versao deste
        # laco reusava `PERMITIDOS`, e com isso `forEach` passava sobre uma
        # colecao do payload: a regra 2 virava a regra 1 escrita de novo, e a
        # sobreposicao que ela existe para dar deixava de existir.
        #
        # Quem mostrou foi a prova negativa — o probe do `forEach` nao reprovou.
        # A regra estava certa no enunciado e frouxa no codigo, que e a forma que
        # so a execucao separa.
        if achado.group(2) == "map":
            continue
        problemas.append(
            f"{relativo}:{_linha(texto, achado.start())}\n"
            f"    `{achado.group(1)}.{achado.group(2)}(` — as colecoes do payload "
            "so sao consumidas por `.map(`.\n"
            "    Esta regra se sobrepoe a de cima de proposito: contencao por duas\n"
            "    regras que se cobrem, em vez de apostar que uma nao mude."
        )

    for achado in _LENGTH_COMPARADO.finditer(texto):
        problemas.append(
            f"{relativo}:{_linha(texto, achado.start())}\n"
            "    `.length` em comparacao — e assim que um orcamento se reimplementa\n"
            "    no cliente. O payload ja traz `omitidos` como NUMERO para que o\n"
            "    cliente nao precise contar."
        )

    return problemas


def main() -> int:
    if not WEB.is_dir():
        print(
            f"ERRO: {_exibe(WEB)} nao existe. `01` §2 poe as "
            "tres telas ali, e um verificador que sai verde por nao achar o "
            "diretorio nao verifica nada.",
            file=sys.stderr,
        )
        return 1

    arquivos = sorted(
        caminho
        for caminho in WEB.rglob("*")
        if caminho.is_file()
        and caminho.suffix in EXTENSOES
        and "node_modules" not in caminho.parts
        and "dist" not in caminho.parts
    )

    if not arquivos:
        print(
            f"ERRO: nenhum arquivo de cliente em {_exibe(WEB)}.\n"
            "Verificador que passa por nao ter o que olhar e a verificacao que "
            "PARECE existir — §7.3 do registro da Fase 3.",
            file=sys.stderr,
        )
        return 1

    problemas: list[str] = []
    for caminho in arquivos:
        problemas.extend(varre(caminho, caminho.read_text(encoding="utf-8")))

    if problemas:
        print("o cliente esta DERIVANDO, e a derivacao e do servidor:\n", file=sys.stderr)
        for problema in problemas:
            print(problema + "\n", file=sys.stderr)
        return 1

    print(
        f"cliente sem derivacao: {len(arquivos)} arquivos varridos, "
        f"{len(PROIBIDOS)} metodos proibidos, {len(COLECOES)} colecoes do payload "
        "consumidas so por `.map(`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
