#!/usr/bin/env python3
"""Prova que `check_api_surface.py` REPROVA — e, sobretudo, na direcao inversa.

A DIRECAO QUE IMPORTA
---------------------
Uma checagem de superficie que so confere "o declarado existe?" fica verde
enquanto a rota que ninguem previu passa ao lado. O eixo `rota implementada e
nao declarada` e o que separa verificador de documentacao com sintaxe de
verificador, e por isso e o primeiro probe deste arquivo.

Os outros dois eixos de estado — `implementada` que sumiu e `planejada` que ja
existe — sao o envelhecimento da lista nas duas direcoes. Sem o segundo,
bastaria declarar tudo como planejado para a checagem nunca cobrar nada.

COMO OS PROBES PLANTAM
----------------------
`rotas_implementadas()` le uma arvore de `api/` por AST, e `verifica()` recebe
todos os conjuntos por parametro. Entao os probes de ESTADO injetam conjuntos, e
o probe da VARREDURA escreve um modulo com rota decorada em diretorio
temporario — nada e escrito em `domains/`.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_api_surface import (  # noqa: E402
    main,
    rotas_implementadas,
    verifica,
)

PAPEIS = {"aluno", "professor"}
FLAGS = {"fixture.uma_flag"}

DECLARADA = {
    "method": "GET",
    "path": "/x",
    "papeis": ["aluno"],
    "flags": [],
    "status": "implementada",
}


def _rota(**mudancas):
    rota = dict(DECLARADA)
    rota.update(mudancas)
    return rota


#: `(rotulo, declaradas, implementadas, trecho esperado)`
PROBES = [
    (
        "rota IMPLEMENTADA e ausente da declaracao — a direcao que importa",
        [],
        {("GET", "/nao_declarada")},
        "ausente de `api_surface.yaml`",
    ),
    (
        "rota declarada `implementada` que sumiu do codigo",
        [_rota()],
        set(),
        "ausente do codigo",
    ),
    (
        "rota `planejada` que ja existe no codigo",
        [_rota(status="planejada")],
        {("GET", "/x")},
        "vira esconderijo permanente",
    ),
    (
        "status fora dos dois valores",
        [_rota(status="quase")],
        {("GET", "/x")},
        "fora de `planejada`/`implementada`",
    ),
    (
        "papel de EXERCICIO na superficie de dominio",
        [_rota(papeis=["facilitador"])],
        {("GET", "/x")},
        "papel de EXERCICIO",
    ),
    (
        "papel fora da lista de papeis de dominio",
        [_rota(papeis=["reitor"])],
        {("GET", "/x")},
        "nao esta em `papeis_de_dominio`",
    ),
    (
        "rota consumindo flag que o adapter nao declara",
        [_rota(flags=["fixture.inexistente"])],
        {("GET", "/x")},
        "que o adapter nao declara",
    ),
    (
        "declaracao e codigo em acordo: nada a acusar",
        [_rota()],
        {("GET", "/x")},
        None,
    ),
]


def roda(rotulo, declaradas, implementadas, esperado) -> bool:
    problemas = verifica(declaradas, implementadas, PAPEIS, FLAGS)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': violacao plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou, mas nao pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com violacao plantada - {rotulo}")
    return True


def probe_da_varredura() -> bool:
    """O eixo que o conjunto injetado nao cobre: enxergar a rota no codigo.

    Sem ele, `rotas_implementadas` poderia devolver conjunto vazio sempre — e
    TODOS os probes de estado continuariam verdes, porque nenhum deles a chama.
    Seria a checagem inteira passando por nao enxergar nada.
    """
    modulo = (
        "from fastapi import APIRouter\n"
        "\n"
        "router = APIRouter()\n"
        "\n"
        '@router.post("/turmas/{turma_id}/notas")\n'
        "async def lancar_nota(turma_id: str):\n"
        "    return {}\n"
        "\n"
        '@router.get("/alunos/{aluno_id}")\n'
        "def ler_aluno(aluno_id: str):\n"
        "    return {}\n"
    )
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario) / "api"
        raiz.mkdir()
        (raiz / "rotas.py").write_text(modulo, encoding="utf-8")
        achadas = rotas_implementadas(raiz)

    esperadas = {("POST", "/turmas/{turma_id}/notas"), ("GET", "/alunos/{aluno_id}")}
    if achadas != esperadas:
        print(f"FALHA: a varredura devolveu {sorted(achadas)}, esperado {sorted(esperadas)}")
        return False
    print("OK: a varredura acha rota decorada, com metodo e caminho - modulo plantado")
    return True


def probe_do_limite_declarado() -> bool:
    """O LIMITE, verificado em vez de herdado como crenca.

    Rota registrada em tempo de execucao — `add_api_route` com caminho calculado
    — NAO e vista por AST, e o cabecalho da checagem declara isso. Aqui o limite
    fica vermelho no dia em que deixar de valer, em vez de envelhecer em prosa.
    """
    modulo = (
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "def oculta():\n"
        "    return {}\n"
        'router.add_api_route("/" + "oculta", oculta, methods=["GET"])\n'
    )
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario) / "api"
        raiz.mkdir()
        (raiz / "dinamica.py").write_text(modulo, encoding="utf-8")
        achadas = rotas_implementadas(raiz)

    if achadas:
        print(f"FALHA: o limite deixou de valer — a varredura achou {sorted(achadas)}")
        return False
    print("OK: rota registrada em tempo de execucao NAO e vista - limite confirmado")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1

    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_da_varredura())
    resultados.append(probe_do_limite_declarado())

    print()
    if all(resultados):
        print(
            f"check_api_surface.py reprova nos {len(resultados)} eixos, com a "
            "direcao inversa em primeiro lugar, mais a varredura por AST e o "
            "limite de rota dinamica confirmado."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
