#!/usr/bin/env python3
"""P2-15 — o que o core importa de `contracts/` e exatamente o declarado aqui.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
A §2.1 do registro da Fase 2 declarou um limite e nomeou o gatilho dele:

    tools/check_core_boundary.py detecta, por AST, so o que aponta para
    `domains`. Sobre `contracts` ele nao tem opiniao nenhuma. (...) Vira
    pendencia no dia em que o core importar de `contracts/` algo que nao seja
    constante gerada.

O gatilho disparou na peca do loader: `range-core/engine/loader/contract_source.py`
importa o **pacote** `contracts` — nao o modulo de constantes — para resolver o
diretorio e ler os `.yaml` em tempo de execucao. A superficie deixou de ser
um artefato gerado e passou a ser um diretorio inteiro.

**O import e legitimo, e nao e ele que esta em jogo.** O invariante 1 proibe
`domains/`; `contracts/` e a fonte canonica compartilhada e agnostica de
dominio, e o loader precisa dela para validar pack. O que estava faltando e
GUARDA: sem ela, o proximo import nao encontra nada, e a ausencia de opiniao
passa a valer mais que a permissao.

WHITELIST, E NAO BLOCKLIST — a forma que a P2-2 mostrou ser a certa
--------------------------------------------------------------------
Nao ha lista de coisas proibidas em `contracts/`, porque a proxima nao estaria
nela. Ha a lista do que o core de fato importa, com o motivo de cada entrada, e
a checagem afirma a IGUALDADE:

1. arquivo do core que importa de `contracts/` e nao esta declarado -> reprova;
2. entrada declarada cujo arquivo nao importa mais aquilo -> reprova.

A (2) e o que impede a lista de envelhecer virando permissao ampla: declaracao
que sobrou e permissao que ninguem pediu.

O custo de acrescentar um import novo passa a ser **uma conversa** — vir aqui e
escrever por que. E o mesmo desenho de `check_store_read_surface.py`, e pelo
mesmo motivo: o que segura o futuro nao e a lista, e a obrigacao de edita-la.

POR QUE EM `scripts/` E NAO EM `tools/`
---------------------------------------
`01` §2 normatiza **seis** verificadores, todos em `tools/`. Um setimo ali
contradiria a contagem que a spec fixa. Ver a §6 do registro da Fase 2.

Stdlib puro, roda no job `arquitetura`.

O LIMITE DESTA CHECAGEM, dito
-----------------------------
Ela ve **import**, e nao leitura de arquivo. Um modulo do core que abrisse
`contracts/events.schema.yaml` por caminho literal, sem importar nada, passaria.
Hoje isso nao existe — `contract_source` resolve o diretorio pelo `__path__` do
pacote, que e um import —, e a forma de manter assim e esta lista continuar
sendo o unico caminho de entrada.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "range-core"

CONTRACTS = "contracts"

RULE = "P2-15 - o que o core importa de contracts/"

#: A SUPERFICIE DECLARADA: caminho POSIX relativo a `range-core/` -> (modulos
#: importados, motivo).
#:
#: O motivo nao e comentario: ele entra na mensagem de reprovacao, e e o que
#: permite a quem chegar aqui decidir se o import novo pertence a mesma classe
#: dos existentes ou abre uma classe nova.
DECLARED: dict[str, tuple[frozenset[str], str]] = {
    "state/simulation_state.py": (
        frozenset({"contracts.generated.events"}),
        "constantes geradas de `event_type`: literal de catalogo dentro do core "
        "violaria o invariante 2",
    ),
    "engine/verificacao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o avaliador emite `verification_predicate_satisfied` e "
        "reconhece `fact_materialized` ao montar o mundo. E EMISSAO, e por isso "
        "ele tem store ao alcance: a leitura e total e o estreitamento e logica "
        "dele, como `01` §4.1 passou a exigir de quem reconstroi o mundo corrente",
    ),
    "events/linhagem.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — a linhagem compara contra `rollback_performed` para achar "
        "o corte. O corpo veio de `state/simulation_state.py`, que ja tinha o "
        "import pelo mesmo motivo: o spec-change `linhagem-corrente-e-o-avaliador` "
        "exige UMA definicao, e ela mora em `events/` porque e de la que o fold "
        "e o avaliador dependem — importar de `state/` inverteria a direcao",
    ),
    "events/epoch.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o calculo de epoch compara contra `rollback_performed`",
    ),
    "engine/inject_engine.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o engine emite os tipos do catalogo",
    ),
    "clock/restauracao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — a restauracao acha o `exercise_started` para achar T0 e le "
        "o par pausa/retomada. O CLOCK continua sem este import: ele recebe cinco "
        "numeros ja derivados, e por isso nao depende do catalogo para existir",
    ),
    "api/projecoes.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — a timeline rotula por `event_type` e a plateia acha o "
        "inject corrente pelo `inject_fired`. E LEITURA do catalogo, e nao "
        "emissao: este modulo nao chama `append` e nao tem store ao alcance",
    ),
    "participant/api/emissor.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o emissor da superficie de participante grava os tipos do "
        "catalogo. E EMISSAO, ao contrario de `api/projecoes.py`: por isso ele "
        "tem store ao alcance, e por isso o predicado de contrassinatura de `03` "
        "§3.4 mora nele e nao no handler",
    ),
    "participant/api/app.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — as nove rotas nomeiam o `event_type` que cada uma emite, e "
        "literal de catalogo no handler violaria o invariante 2. O handler NAO "
        "chama `append`: ele passa o tipo ao emissor, que e quem grava",
    ),
    "objectives/projecao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — a projecao acha as marcacoes do avaliador por "
        "`observed_marker_set`. E LEITURA do catalogo, como `api/projecoes.py`: "
        "este modulo nao chama `append` e nao tem store ao alcance",
    ),
    "metrics/epoch.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o desconto de `00` §3.2 acha os congelamentos e as epochs "
        "descartadas pelo `rollback_performed`. E LEITURA do catalogo, como "
        "`objectives/projecao.py`: nao chama `append` e nao tem store ao alcance. "
        "O `reason` NAO vem daqui — e valor de payload, e o enum dele fica em "
        "`events.schema.yaml`, cruzado por teste em `tests/test_metrics_epoch.py`",
    ),
    "aar/timeline.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — a `aar_timeline` acha as notas de rubrica pelo "
        "`bars_score_submitted` e as declaracoes de integridade pelo tipo delas. "
        "E LEITURA do catalogo, e a projecao nao chama `append`: `01` §4.1 diz "
        "que nenhuma projecao escreve no store",
    ),
    "metrics/calibracao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o escore de `03` §5 recorta os `assessment_submitted` do "
        "fluxo que recebe. E LEITURA do catalogo, e a funcao e PURA: nao tem "
        "store nem pack ao alcance, e o escopo revisado chega como dado (P6-5)",
    ),
    "metrics/declaracao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o computador do lado da declaracao acha os starts e stops "
        "de `03` §3 por `event_type`: `inject_fired`, `incident_declared`, as "
        "duas submissoes que fecham `TTCM`, e as tres declaracoes de par. E "
        "LEITURA do catalogo, e o insumo de `00` §3.2 nao tem por onde um store "
        "entrar",
    ),
    "metrics/verificacao.py": (
        frozenset({"contracts.generated.events"}),
        "mesma razao — o computador do lado da verificacao acha o veredito pelo "
        "`verification_predicate_satisfied` e T0 pelo `exercise_started`. E "
        "LEITURA do catalogo: nao chama `append` e nao tem store ao alcance — "
        "por construcao, porque o insumo de `00` §3.2 nao tem por onde um store "
        "entrar",
    ),
    "engine/loader/contract_source.py": (
        frozenset({CONTRACTS}),
        "A EXCECAO, e a unica: importa o PACOTE para resolver o diretorio e ler "
        "os `.yaml` em tempo de execucao. E o gatilho que a §2.1 do registro da "
        "Fase 2 previu. Caminho relativo a este arquivo quebraria fora da "
        "arvore, e `__path__` cobre pacote de namespace e instalacao editavel",
    ),
}


def _targets_contracts(module: str | None) -> bool:
    return bool(module) and (module == CONTRACTS or module.startswith(CONTRACTS + "."))


def _relative_escapes_into_contracts(
    path: Path, level: int, module: str | None, repo_root: Path
) -> bool:
    """`from ...contracts import x` — import relativo que sai do core.

    Coberto porque o AST o ve como outra coisa: `node.module` seria `contracts`
    sem que o import fosse absoluto, e uma checagem que so olhasse o nome
    absoluto deixaria a porta relativa aberta. Mesma forma que
    `tools/check_core_boundary.py` usa para `domains`.

    `repo_root` e PARAMETRO, e nao a constante do modulo. Ancorar na raiz deste
    repositorio faria a resolucao falhar contra a copia temporaria que a prova
    negativa usa — e o probe passaria por rc=0, lendo "nao detectou" como
    "nao ha violacao". Apareceu ao escrever o probe, que e quando esse tipo de
    acoplamento aparece.
    """
    base = path.resolve().parent
    for _ in range(max(level - 1, 0)):
        base = base.parent
    alvo = base
    if module:
        for parte in module.split("."):
            alvo = alvo / parte
    try:
        relativo = alvo.relative_to(repo_root)
    except ValueError:
        return False
    return bool(relativo.parts) and relativo.parts[0] == CONTRACTS


def _literal_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant):
        valor = node.args[0].value
        return valor if isinstance(valor, str) else None
    return None


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def imports_de_contracts(path: Path, repo_root: Path) -> set[str]:
    """Os modulos de `contracts` que o arquivo importa, em qualquer das formas.

    Direto, com alias, relativo que escape, e dinamico via `import_module` ou
    `__import__` — as mesmas quatro que o verificador do invariante 1 cobre. Uma
    checagem que so visse `import x` seria contornavel por acidente, e nao por
    ma fe: `importlib.import_module` e o que alguem escreve para carregar por
    nome calculado.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    encontrados: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _targets_contracts(alias.name):
                    encontrados.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and _relative_escapes_into_contracts(
                path, node.level, node.module, repo_root
            ):
                encontrados.add(f"{'.' * node.level}{node.module or ''}")
            elif not node.level and _targets_contracts(node.module):
                encontrados.add(node.module)
        elif isinstance(node, ast.Call):
            if _callee_name(node) in ("import_module", "__import__"):
                literal = _literal_argument(node)
                if literal is not None and _targets_contracts(literal):
                    encontrados.add(literal)

    return encontrados


def main(argv: list[str] | None = None) -> int:
    """Sem argumento, confere o core real. Com um caminho, confere aquele.

    O caminho existe para a prova negativa rodar contra uma copia com violacao
    plantada, sem sujar a arvore — mesma disciplina de
    `check_store_read_surface.py`.
    """
    argv = sys.argv[1:] if argv is None else argv
    raiz = Path(argv[0]).resolve() if argv else CORE_ROOT

    if not raiz.is_dir():
        print(f"{RULE}: {raiz} nao e diretorio", file=sys.stderr)
        return 2

    encontrado: dict[str, set[str]] = {}
    for caminho in sorted(raiz.rglob("*.py")):
        modulos = imports_de_contracts(caminho, raiz.parent)
        if modulos:
            encontrado[caminho.relative_to(raiz).as_posix()] = modulos

    falhas: list[str] = []

    for arquivo in sorted(set(encontrado) - set(DECLARED)):
        falhas.append(
            f"range-core/{arquivo} importa de `contracts/` "
            f"({sorted(encontrado[arquivo])}) e NAO esta declarado.\n"
            f"    Se o import pertence, declare-o em {Path(__file__).name} com o "
            "motivo. A lista e whitelist: o custo de acrescentar e uma conversa, "
            "e e esse o ponto."
        )

    for arquivo in sorted(set(DECLARED) - set(encontrado)):
        falhas.append(
            f"range-core/{arquivo} esta declarado e nao importa mais de "
            "`contracts/`.\n"
            "    Declaracao que sobra e permissao que ninguem pediu: remova a "
            "entrada."
        )

    for arquivo in sorted(set(DECLARED) & set(encontrado)):
        declarados, motivo = DECLARED[arquivo]
        if set(declarados) != encontrado[arquivo]:
            falhas.append(
                f"range-core/{arquivo}: importa {sorted(encontrado[arquivo])}, "
                f"declarado {sorted(declarados)}.\n"
                f"    Motivo declarado: {motivo}"
            )

    if falhas:
        print(f"{RULE}\n", file=sys.stderr)
        for falha in falhas:
            print(f"  {falha}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(DECLARED)} arquivos declarados, todos batendo. "
        "Nenhum outro modulo do core importa de `contracts/`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
