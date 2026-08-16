#!/usr/bin/env python3
"""A superficie da `academus-api` e exatamente a declarada — nas duas direcoes.

O QUE ESTA CHECAGEM EXISTE PARA IMPEDIR
----------------------------------------
Uma lista de rotas escrita antes do codigo **subestima**, e uma checagem que so
compara "o declarado existe?" transforma a lista em documentacao com sintaxe de
verificador: ela fica verde enquanto a rota que ninguem previu passa ao lado.

Por isso a igualdade e nos DOIS SENTIDOS, e o sentido que importa e o inverso do
obvio:

  rota IMPLEMENTADA e ausente da declaracao         -> reprova
  rota declarada `implementada` e ausente do codigo -> reprova
  rota declarada `planejada` que JA existe no codigo -> reprova

O terceiro eixo e o que impede `planejada` de virar esconderijo permanente:
assim que a rota nasce, a entrada e promovida no mesmo commit. Sem ele, bastaria
declarar tudo como planejado para a checagem nunca cobrar nada.

E o mesmo desenho de `check_store_read_surface.py`, e pelo mesmo motivo — foi a
igualdade nas duas direcoes que fez aquela funcionar.

O QUE MAIS ELA COBRA
--------------------
- **flag de rota existe no adapter.** Mesma regra que o loader aplica ao pack e
  que `check_spec_flags.py` aplica a spec: a terceira porta pela qual um nome de
  flag entra no sistema passa a ter a mesma guarda que as outras duas.
- **papel de rota existe na lista de papeis de dominio.** Papel de EXERCICIO —
  facilitador, operador, avaliador (`03` §7) — e recusado por nome: se aparecer
  aqui, o adapter passou a conhecer desenho de exercicio.

COMO ELA ENXERGA A ROTA IMPLEMENTADA
-------------------------------------
Por **AST**, sobre `domains/<adapter>/api/`, procurando decorador de rota na
forma `@algo.<metodo>("/caminho")` — a forma do FastAPI, que `02` §7 fixa como a
stack da `academus-api`. Nao ha rota nenhuma hoje, e a checagem ja roda: e a
diferenca entre escrever a obrigacao antes e escrever a lista antes.

**O limite, declarado:** rota registrada em tempo de execucao — `add_api_route`
com caminho calculado — nao e vista por AST. E a mesma excecao que
`01` §2 admite para varredura lexica de TypeScript: a alternativa seria importar
a aplicacao dentro do verificador, e um gate que importa o que julga deixa de ser
gate. A forma decorada e a unica usada, e esta checagem so vale enquanto isso
continuar verdade.

Stdlib pura — le YAML pelo parser estrito de `tools/`. Roda no job `arquitetura`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

DOMAINS = REPO_ROOT / "domains"

RULE = "superficie da api x rotas implementadas"

#: Metodos HTTP que contam como declaracao de rota.
METODOS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

#: Papeis de EXERCICIO — `03` §7. Recusados na superficie de dominio por nome.
#:
#: Nao e lista de palavras proibidas por precaucao: sao exatamente os tres que a
#: spec define, e a confusao entre eles e os de dominio e o que poe desenho de
#: exercicio dentro do adapter.
PAPEIS_DE_EXERCICIO = frozenset({"facilitador", "operador", "avaliador"})


def _superficies() -> list[tuple[str, Path, dict]]:
    """`(adapter, caminho, documento)` para cada `api_surface.yaml` declarado."""
    achadas = []
    for caminho in sorted(DOMAINS.glob("*/api_surface.yaml")):
        achadas.append((caminho.parent.name, caminho, parse_yaml(caminho) or {}))
    return achadas


def _flags_declaradas(adapter: str) -> set[str]:
    caminho = DOMAINS / adapter / "flags.yaml"
    if not caminho.is_file():
        return set()
    return {f["name"] for f in (parse_yaml(caminho) or {}).get("flags") or []}


def rotas_implementadas(raiz_api: Path) -> set[tuple[str, str]]:
    """`(METODO, caminho)` de cada rota decorada sob `api/`.

    Aceita `@app.get("/x")`, `@router.post("/x")` e qualquer receptor: o que
    identifica a rota e o ATRIBUTO ser um metodo HTTP e o primeiro argumento ser
    string literal. Caminho calculado nao e visto — ver o limite no cabecalho.
    """
    achadas: set[tuple[str, str]] = set()
    if not raiz_api.is_dir():
        return achadas

    for arquivo in sorted(raiz_api.rglob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), str(arquivo))
        for node in ast.walk(arvore):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorador in node.decorator_list:
                if not isinstance(decorador, ast.Call):
                    continue
                func = decorador.func
                if not isinstance(func, ast.Attribute) or func.attr not in METODOS:
                    continue
                if not decorador.args:
                    continue
                primeiro = decorador.args[0]
                if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                    achadas.add((func.attr.upper(), primeiro.value))
    return achadas


def verifica(
    declaradas: list[dict],
    implementadas: set[tuple[str, str]],
    papeis_de_dominio: set[str],
    flags_do_adapter: set[str],
) -> list[str]:
    """As cinco asserções. Tudo por parametro, para a prova negativa injetar."""
    problemas: list[str] = []
    por_chave = {(r["method"].upper(), r["path"]): r for r in declaradas}

    for chave in sorted(implementadas - set(por_chave)):
        problemas.append(
            f"{chave[0]} {chave[1]}: IMPLEMENTADA e ausente de `api_surface.yaml`.\n"
            "    E a direcao que importa: lista escrita antes do codigo "
            "subestima, e checagem que so confere o inverso vira documentacao "
            "com sintaxe de verificador."
        )

    for chave, rota in sorted(por_chave.items()):
        status = rota.get("status")
        existe = chave in implementadas

        if status == "implementada" and not existe:
            problemas.append(
                f"{chave[0]} {chave[1]}: declarada `implementada` e ausente do "
                "codigo. A declaracao envelheceu — promova de volta a "
                "`planejada` ou remova."
            )
        elif status == "planejada" and existe:
            problemas.append(
                f"{chave[0]} {chave[1]}: declarada `planejada` e JA existe no "
                "codigo. Promova a `implementada` no commit que a criou — senao "
                "`planejada` vira esconderijo permanente."
            )
        elif status not in ("planejada", "implementada"):
            problemas.append(
                f"{chave[0]} {chave[1]}: `status: {status!r}` fora de "
                "`planejada`/`implementada`."
            )

        for papel in rota.get("papeis") or []:
            if papel in PAPEIS_DE_EXERCICIO:
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} e papel de "
                    "EXERCICIO (`03` §7), nao de dominio. O adapter passaria a "
                    "conhecer desenho de exercicio — a fronteira do invariante 1 "
                    "por onde o verificador nao olha."
                )
            elif papel not in papeis_de_dominio:
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} nao esta em "
                    "`papeis_de_dominio`."
                )

        for flag in rota.get("flags") or []:
            if flag not in flags_do_adapter:
                problemas.append(
                    f"{chave[0]} {chave[1]}: consome {flag!r}, que o adapter nao "
                    "declara. Mesma regra que o loader aplica ao pack e que "
                    "`check_spec_flags.py` aplica a spec."
                )

    return problemas


def main(argv: list[str] | None = None) -> int:
    superficies = _superficies()
    if not superficies:
        print(f"{RULE}: nenhum `api_surface.yaml` em {DOMAINS}", file=sys.stderr)
        return 2

    problemas: list[str] = []
    total_rotas = total_implementadas = 0

    for adapter, caminho, documento in superficies:
        declaradas = documento.get("rotas") or []
        implementadas = rotas_implementadas(DOMAINS / adapter / "api")
        total_rotas += len(declaradas)
        total_implementadas += len(implementadas)

        for problema in verifica(
            declaradas,
            implementadas,
            set(documento.get("papeis_de_dominio") or []),
            _flags_declaradas(adapter),
        ):
            problemas.append(f"{caminho.relative_to(REPO_ROOT).as_posix()}: {problema}")

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    planejadas = total_rotas - total_implementadas
    print(
        f"{RULE}: {total_rotas} rotas declaradas — {total_implementadas} "
        f"implementadas e conferidas por AST, {planejadas} planejadas. "
        "Nenhuma rota fora da declaracao."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
