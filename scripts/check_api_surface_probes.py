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
    claims_assinadas,
    main,
    modulos_que_importam_estado,
    rotas_implementadas,
    verifica,
    verifica_degradacao,
    verifica_token,
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
        "rota `publica: true` com papeis declarados",
        [_rota(publica=True)],
        {("GET", "/x")},
        "Ou a rota e aberta, ou ela exige papel",
    ),
    (
        "rota sem papeis e sem `publica` — vazio significa NINGUEM",
        [_rota(papeis=[])],
        {("GET", "/x")},
        "Lista vazia significa NINGUEM",
    ),
    (
        "declaracao e codigo em acordo: nada a acusar",
        [_rota()],
        {("GET", "/x")},
        None,
    ),
]

#: Eixo da peca 4 que nao passa por `verifica`: a lista de ORIGEM dos papeis.
#: Era o buraco da peca 2 — papel de exercicio na rota reprovava, e em
#: `papeis_de_dominio` passava.
def probe_papel_de_exercicio_na_lista_de_origem() -> bool:
    problemas = verifica([_rota()], {("GET", "/x")}, PAPEIS | {"operador"}, FLAGS)
    if not any("papeis_de_dominio` contem 'operador'" in p for p in problemas):
        print(f"FALHA: papel de exercicio em `papeis_de_dominio` passou: {problemas}")
        return False
    print("OK: reprovou com violacao plantada - papel de EXERCICIO em `papeis_de_dominio`")
    return True


#: `(rotulo, claims declaradas, claims no codigo, trecho esperado)`
PROBES_DE_TOKEN = [
    (
        "claim ASSINADO e ausente da declaracao — a direcao que importa",
        ["sub", "role", "exp"],
        ["sub", "role", "exp", "persona"],
        "e ausente de `token.claims`",
    ),
    (
        "claim declarado que o codigo nao assina",
        ["sub", "role", "exp", "campus"],
        ["sub", "role", "exp"],
        "Declaracao orfa reprova",
    ),
    (
        "claim com vocabulario de EXERCICIO nos dois lados",
        ["sub", "role", "exp", "persona"],
        ["sub", "role", "exp", "persona"],
        "vocabulario de EXERCICIO",
    ),
    (
        "a funcao que monta o payload desapareceu — vacuidade",
        ["sub", "role", "exp"],
        None,
        "passa por VACUIDADE",
    ),
    (
        "declaracao e assinatura em acordo: nada a acusar",
        ["sub", "role", "exp"],
        ["sub", "role", "exp"],
        None,
    ),
]


def roda_token(rotulo, declaradas, no_codigo, esperado) -> bool:
    problemas = verifica_token(declaradas, no_codigo)
    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' nao acusou pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com violacao plantada - {rotulo}")
    return True


def probe_da_degradacao() -> bool:
    """A fronteira entre a peca 4 e a peca 5, verificada nos dois sentidos.

    O segundo caso e o que impede a regra de virar proibicao permanente: assim
    que uma rota IMPLEMENTADA declara flag, ler estado passa a ser legitimo e a
    checagem se cala sozinha.
    """
    acusou = verifica_degradacao([_rota()], {"rotas.py"})
    if not any("nenhuma rota IMPLEMENTADA declara flag" in p for p in acusou):
        print(f"FALHA: import de estado sem rota com flag passou: {acusou}")
        return False

    com_flag = verifica_degradacao([_rota(flags=["fixture.uma_flag"])], {"rotas.py"})
    if com_flag:
        print(f"FALHA: a regra nao saiu de cena com rota que declara flag: {com_flag}")
        return False

    print("OK: reprovou com violacao plantada - estado lido sem flag declarada")
    print("OK: e a regra se cala quando uma rota implementada declara flag")
    return True


def probe_dos_extratores() -> bool:
    """Os DOIS extratores da peca 4, contra arvore plantada.

    Sem isto, `claims_assinadas` podendo devolver sempre `[]` e
    `modulos_que_importam_estado` sempre vazio deixariam TODOS os probes de
    conjunto acima verdes — nenhum deles chama os extratores. E a mesma forma do
    `probe_da_varredura`, e existe pelo mesmo motivo.
    """
    modulo_do_token = (
        "def _payload(sub, role, exp):\n"
        '    return {"sub": sub, "role": role, "exp": exp, "persona": "x"}\n'
    )
    modulo_que_le_estado = (
        "from range_core.state.cache import current\n"
        "def rota():\n"
        "    return current\n"
    )
    modulo_limpo = "import json\ndef rota():\n    return json\n"

    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        alvo = raiz / "tokens.py"
        alvo.write_text(modulo_do_token, encoding="utf-8")
        achadas = claims_assinadas(alvo)
        if achadas != ["sub", "role", "exp", "persona"]:
            print(f"FALHA: claims_assinadas devolveu {achadas}")
            return False

        sem_funcao = raiz / "outro.py"
        sem_funcao.write_text("def qualquer():\n    return {}\n", encoding="utf-8")
        if claims_assinadas(sem_funcao) is not None:
            print("FALHA: claims_assinadas nao distinguiu funcao ausente de vazia")
            return False

        api = raiz / "api"
        api.mkdir()
        (api / "com_estado.py").write_text(modulo_que_le_estado, encoding="utf-8")
        (api / "limpo.py").write_text(modulo_limpo, encoding="utf-8")
        vistos = modulos_que_importam_estado(api)
        if vistos != {"com_estado.py"}:
            print(f"FALHA: modulos_que_importam_estado devolveu {sorted(vistos)}")
            return False

    print("OK: os dois extratores enxergam o que dizem enxergar - arvore plantada")
    return True


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
    resultados.extend(roda_token(*p) for p in PROBES_DE_TOKEN)
    resultados.append(probe_papel_de_exercicio_na_lista_de_origem())
    resultados.append(probe_da_degradacao())
    resultados.append(probe_da_varredura())
    resultados.append(probe_do_limite_declarado())
    resultados.append(probe_dos_extratores())

    print()
    if all(resultados):
        print(
            f"check_api_surface.py reprova nos {len(resultados)} eixos, com a "
            "direcao inversa em primeiro lugar — rota e claim —, mais os tres "
            "extratores por AST e o limite de rota dinamica confirmado."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
