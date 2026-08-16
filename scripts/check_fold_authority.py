#!/usr/bin/env python3
"""O fold e a unica autoridade de estado — e escrita fora dele e inexprimivel.

O QUE ESTA CHECAGEM PROVA
--------------------------
`01_ARCHITECTURE.md` §4.1: *"toda projecao e reconstruivel do zero"*. Estado que
nao vem do fold nao sobrevive a reconstrucao — e um servico que escrevesse flag
direto produziria mundo invisivel ao rollback, que e exatamente o que a §4.4
deixou de afirmar quando a P2-9 foi corrigida.

A Fase 3 materializa a projecao em Redis, e materializar cria a tentacao: um
caminho de escrita de estado que nao passa pelo fold. A porta
`SimulationStateCache` fecha isso pela FORMA — `refresh` recebe o fluxo e folda
la dentro, e nao ha metodo que aceite um estado pronto.

**Mas forma sem verificacao envelhece.** Esta checagem afirma as duas metades:

1. **`SimulationState` e construido so onde esta declarado.** A procedencia nao
   esta no valor — e um dataclass, qualquer um constroi um —, esta em QUEM
   calcula. Entao a lista de quem constroi e a lista de quem tem autoridade.
2. **Nenhum metodo publico do cache aceita `SimulationState`.** Se aceitasse, o
   ponto 1 nao bastaria: bastaria construir dentro do fold e passar adiante um
   estado obtido de outro jeito.

A SEGUNDA E A QUE A PECA 2 ENSINOU A ESCREVER. Uma checagem que so conferisse
"o declarado existe" ficaria verde com um `write(state)` novo ao lado. A
igualdade e nas duas direcoes: sitio declarado que sumiu tambem reprova.

OS DOIS SITIOS DECLARADOS, E POR QUE SAO DOIS
----------------------------------------------
`project` calcula. `_estado_de` **desserializa** o que o fold ja produziu — e a
diferenca e verificavel, nao de intencao: ali nao ha `Declarations`, nao ha fluxo
e nao ha regra de estado; ha `json.loads` e dois campos. Uma reimplementacao do
fold precisaria dos tres.

Stdlib pura, por AST. Roda no job `arquitetura`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "range-core"

RULE = "o fold e a unica autoridade de estado"

TIPO = "SimulationState"

#: ONDE `SimulationState` PODE SER CONSTRUIDO — `arquivo -> funcao -> motivo`.
#:
#: Whitelist, e nao blocklist: construcao nova reprova ate alguem vir aqui e
#: dizer por que aquele lugar tem autoridade sobre estado de simulacao. O custo
#: e uma conversa, e e esse o ponto.
CONSTRUCAO_AUTORIZADA: dict[tuple[str, str], str] = {
    ("state/simulation_state.py", "project"): "o fold. E ele que a §4.1 declara "
    "reconstruivel do zero, e e dele que todo estado de simulacao vem",
    ("state/cache.py", "_estado_de"): "desserializacao do que o fold ja produziu "
    "— sem `Declarations`, sem fluxo e sem regra de estado; `json.loads` e dois "
    "campos",
}

#: A porta cujo formato garante que escrita de estado nao tem por onde entrar.
PORTA = "state/cache.py"
CLASSE_PORTA = "SimulationStateCache"


def _funcao_que_contem(arvore: ast.AST, alvo: ast.AST) -> str:
    """O nome da funcao que envolve um no, ou `<modulo>` se nao houver."""
    for node in ast.walk(arvore):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for filho in ast.walk(node):
                if filho is alvo:
                    return node.name
    return "<modulo>"


def construcoes(raiz: Path) -> set[tuple[str, str]]:
    """`(arquivo, funcao)` de cada `SimulationState(...)` no core."""
    achadas: set[tuple[str, str]] = set()
    if not raiz.is_dir():
        return achadas

    for caminho in sorted(raiz.rglob("*.py")):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
        for node in ast.walk(arvore):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            nome = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if nome != TIPO:
                continue
            relativo = caminho.relative_to(raiz).as_posix()
            achadas.add((relativo, _funcao_que_contem(arvore, node)))
    return achadas


def metodos_que_aceitam_estado(raiz: Path) -> list[str]:
    """Metodos PUBLICOS da porta com parametro anotado `SimulationState`.

    Anotacao, e nao nome: `write(estado)` sem anotacao passaria por aqui — e por
    isso a garantia real e o formato da porta, com esta checagem afirmando que
    ele nao mudou. O limite esta dito porque e limite.
    """
    caminho = raiz / PORTA
    if not caminho.is_file():
        return [f"{PORTA} nao existe: a porta declarada sumiu"]

    problemas: list[str] = []
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))

    # A CLASSE PRECISA EXISTIR, e este `if` foi o terceiro defeito que os probes
    # acharam nesta checagem. Sem ele, renomear `SimulationStateCache` fazia o
    # laco abaixo nao casar com nada e a checagem devolver "nenhum metodo aceita
    # estado pronto" — verdadeiro por vacuidade, e exatamente a forma de passar
    # verde por nao enxergar. E a mesma classe do eixo de varredura da peca 2.
    if not any(
        isinstance(n, ast.ClassDef) and n.name == CLASSE_PORTA for n in ast.walk(arvore)
    ):
        return [
            f"{PORTA}: a classe {CLASSE_PORTA} nao existe mais.\n"
            "    A porta declarada sumiu, e com ela a garantia de que escrita de "
            "estado nao tem por onde entrar. Renomeou? Atualize a declaracao."
        ]

    for node in ast.walk(arvore):
        if not isinstance(node, ast.ClassDef) or node.name != CLASSE_PORTA:
            continue
        for filho in node.body:
            if not isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if filho.name.startswith("_"):
                continue
            for argumento in filho.args.args + filho.args.kwonlyargs:
                anotacao = argumento.annotation
                texto = (
                    anotacao.id
                    if isinstance(anotacao, ast.Name)
                    else getattr(anotacao, "attr", None)
                )
                if texto == TIPO:
                    problemas.append(
                        f"{PORTA}: {CLASSE_PORTA}.{filho.name} aceita "
                        f"`{argumento.arg}: {TIPO}`.\n"
                        "    A porta nao pode receber estado pronto: quem tem "
                        "autoridade e quem CALCULA, e procedencia nao esta no "
                        "valor. `refresh` recebe o fluxo e folda."
                    )
    return problemas


def main(argv: list[str] | None = None) -> int:
    # LER `sys.argv` AQUI, e nao so aceitar o parametro: sem esta linha o
    # `__main__` chama `main()` sem argumento e a checagem roda sempre contra o
    # core real — inclusive quando o probe passa uma arvore plantada. Os quatro
    # probes reprovaram na primeira execucao por isso, que e exatamente o que
    # eles existem para pegar.
    argv = sys.argv[1:] if argv is None else argv
    raiz = Path(argv[0]).resolve() if argv else CORE_ROOT

    achadas = construcoes(raiz)
    problemas: list[str] = []

    for sitio in sorted(achadas - set(CONSTRUCAO_AUTORIZADA)):
        problemas.append(
            f"{sitio[0]}: {TIPO} construido em `{sitio[1]}`, que nao esta "
            "autorizado.\n"
            "    Estado de simulacao vem do fold — `01` §4.1. Se este lugar tem "
            f"autoridade, declare-o em {Path(__file__).name} com o motivo."
        )

    for sitio in sorted(set(CONSTRUCAO_AUTORIZADA) - achadas):
        problemas.append(
            f"{sitio[0]}: autorizacao declarada para `{sitio[1]}` e nao ha "
            f"construcao de {TIPO} ali.\n"
            "    Autorizacao que sobra e permissao que ninguem pediu."
        )

    problemas.extend(metodos_que_aceitam_estado(raiz))

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(achadas)} sitios de construcao, todos declarados; "
        f"nenhum metodo publico de {CLASSE_PORTA} aceita estado pronto."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
