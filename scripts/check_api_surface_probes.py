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
    ESTADO_DE_SIMULACAO,
    FAMILIAS_CONHECIDAS,
    MOTOR_DA_DEGRADACAO,
    PERFIL_DOMINIO,
    PERFIL_NUCLEO,
    SUPERFICIES,
    claims_assinadas,
    catalogo_de_eventos,
    main,
    modulos_que_importam,
    rotas_implementadas,
    parse_yaml,
    superficies_em_disco,
    verifica,
    verifica_canais,
    verifica_chaves,
    verifica_degradacao,
    verifica_escopo,
    verifica_eventos,
    verifica_imports,
    verifica_irreversibilidade,
    verifica_tabela,
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
        "rota PUBLICA que degrada — M2 da auditoria, pelo lado da configuracao",
        [_rota(papeis=[], publica=True, flags=["fixture.uma_flag"], degradacao=[
            {"flag": "fixture.uma_flag", "condicao": "ligada", "efeito": "recusa",
             "status": 503, "mensagem": "Fora do ar."}])],
        {("GET", "/x")},
        "`publica: true` com degradacao declarada",
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
    problemas = verifica(
        [_rota()], {("GET", "/x")}, PAPEIS | {"operador"}, FLAGS, PERFIL_DOMINIO
    )
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
        # A mensagem deixou de nomear "vocabulario de EXERCICIO" como categoria
        # unica e passou a nomear A SUPERFICIE: o conjunto proibido virou do
        # perfil, porque `persona` e proibido no dominio e correto no de
        # participante. Mesmo eixo, mensagem por superficie.
        "nao pode existir no token da superficie",
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
    problemas = verifica_token(declaradas, no_codigo, PERFIL_DOMINIO)
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


TIPOS = {"fixture.uma_flag": "boolean", "fixture.uma_taxa": "number"}

BOA = {
    "flag": "fixture.uma_flag",
    "condicao": "ligada",
    "efeito": "recusa",
    "status": 503,
    "mensagem": "O servico esta temporariamente fora do ar.",
}


def _degradada(**mudancas):
    entrada = dict(BOA)
    entrada.update(mudancas)
    return [_rota(flags=[entrada["flag"]], degradacao=[entrada])]


#: `(rotulo, declaradas, trecho esperado)` — a degradacao declarativa, peca 5.
PROBES_DE_DEGRADACAO = [
    (
        "`degradacao` ainda em prosa",
        [_rota(flags=[], degradacao="fica lento e cai")],
        "prosa nao executa",
    ),
    (
        "efeito sobre flag que a rota nao declara",
        [_rota(flags=[], degradacao=[BOA])],
        "que nao esta em `flags`",
    ),
    (
        "flag declarada sem dizer o que ela faz",
        [_rota(flags=["fixture.uma_flag"], degradacao=[])],
        "nao diz o que ela faz",
    ),
    (
        "condicao fora do vocabulario fechado",
        _degradada(condicao="as vezes"),
        "fora de ['ligada', 'proporcional']",
    ),
    (
        "efeito fora do vocabulario fechado",
        _degradada(efeito="explode"),
        "fora de ['latencia', 'recusa']",
    ),
    (
        "`ligada` sobre flag `number` — o defeito que ficaria ligado o exercicio inteiro",
        _degradada(flag="fixture.uma_taxa", condicao="ligada"),
        "e `number`",
    ),
    (
        "`proporcional` sobre flag booleana",
        _degradada(flag="fixture.uma_flag", condicao="proporcional"),
        "exige flag `number`",
    ),
    (
        "recusa sem status HTTP de erro",
        _degradada(status=200),
        "nao e codigo de erro HTTP",
    ),
    (
        "recusa sem mensagem de negocio",
        _degradada(mensagem=""),
        "sem `mensagem`",
    ),
    (
        "latencia de zero segundos",
        _degradada(efeito="latencia", status=None, segundos=0),
        "nao se observa",
    ),
    (
        "A MENSAGEM NOMEIA A FLAG",
        _degradada(mensagem="Indisponivel: fixture.uma_flag esta ativa."),
        "nomeia a flag",
    ),
    (
        "a mensagem usa vocabulario de MECANISMO",
        _degradada(mensagem="Servico derrubado pelo inject desta rodada."),
        "vocabulario de MECANISMO",
    ),
    (
        "declaracao coerente: nada a acusar",
        _degradada(),
        None,
    ),
]


def roda_degradacao(rotulo, declaradas, esperado) -> bool:
    problemas = verifica_degradacao(declaradas, TIPOS)
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


def probe_do_escopo() -> bool:
    """A P3-3 como verificacao: regra fora do vocabulario, e papel que nao existe."""
    fora = verifica_escopo([_rota(escopo={"aluno": "quase-proprio"})])
    if not any("fora de ['proprio', 'titular']" in p for p in fora):
        print(f"FALHA: regra de escopo invalida passou: {fora}")
        return False

    orfa = verifica_escopo([_rota(papeis=["aluno"], escopo={"professor": "titular"})])
    if not any("nao esta nos papeis da rota" in p for p in orfa):
        print(f"FALHA: escopo para papel que a rota nao admite passou: {orfa}")
        return False

    if verifica_escopo([_rota(papeis=["aluno"], escopo={"aluno": "proprio"})]):
        print("FALHA: escopo coerente foi acusado")
        return False

    print("OK: reprovou com violacao plantada - regra de escopo fora do vocabulario")
    print("OK: reprovou com violacao plantada - escopo para papel que a rota nao admite")
    return True


def probe_dos_imports() -> bool:
    """O handler nao tem flag ao alcance — a metade forte da D4."""
    fora_do_motor = verifica_imports({"rotas.py", MOTOR_DA_DEGRADACAO}, set())
    if not any("rotas.py: importa" in p for p in fora_do_motor):
        print(f"FALHA: modulo fora do motor lendo estado passou: {fora_do_motor}")
        return False

    com_constante = verifica_imports({MOTOR_DA_DEGRADACAO}, {"rotas.py"})
    if not any("constantes de flag geradas" in p for p in com_constante):
        print(f"FALHA: import de constante de flag passou: {com_constante}")
        return False

    if verifica_imports({MOTOR_DA_DEGRADACAO}, set()):
        print("FALHA: so o motor lendo estado foi acusado")
        return False

    print("OK: reprovou com violacao plantada - estado lido fora do motor")
    print("OK: reprovou com violacao plantada - constante de flag importada em api/")
    return True


def probe_do_motivo_do_verde() -> bool:
    """A REGRA ESTA VERDE PELO MOTIVO CERTO, e nao por nao haver o que olhar.

    A peca 4 tinha uma cerca de transicao — *"enquanto nenhuma rota implementada
    declarar flag, `api/` nao le estado"* — que se calaria sozinha no momento em
    que a peca 5 declarasse a primeira flag. Uma regra que evapora quando o
    assunto dela comeca a existir nao e uma regra.

    Ela foi SUBSTITUIDA pela whitelist, e este probe afirma que a substituicao
    esta viva na arvore real: ha exatamente um modulo lendo estado, e ele e o
    motor. Se um dia o conjunto ficar vazio, a whitelist passaria a ser verdadeira
    por vacuidade — e este probe fica vermelho antes disso virar silencio.
    """
    api = REPO_ROOT / "domains" / "academus" / "api"
    com_estado = modulos_que_importam(api, ESTADO_DE_SIMULACAO)

    if com_estado != {MOTOR_DA_DEGRADACAO}:
        print(
            f"FALHA: quem le estado em api/ e {sorted(com_estado)}, esperado "
            f"exatamente {{{MOTOR_DA_DEGRADACAO!r}}}. Conjunto vazio faria a "
            "whitelist passar por vacuidade."
        )
        return False

    print(f"OK: exatamente um modulo le estado, e e o motor - {MOTOR_DA_DEGRADACAO}")
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
        vistos = modulos_que_importam(api, ESTADO_DE_SIMULACAO)
        if vistos != {"com_estado.py"}:
            print(f"FALHA: modulos_que_importam_estado devolveu {sorted(vistos)}")
            return False

    print("OK: os dois extratores enxergam o que dizem enxergar - arvore plantada")
    return True


def roda(rotulo, declaradas, implementadas, esperado) -> bool:
    problemas = verifica(declaradas, implementadas, PAPEIS, FLAGS, PERFIL_DOMINIO)

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
        "\n"
        # O CANAL E ROTA, e esta linha e do perfil do nucleo. Sem ver
        # `@app.websocket`, um canal implementado ficaria invisivel a varredura —
        # e a direcao que importa, `implementada e nao declarada`, nunca
        # dispararia para ele. O eixo mais forte da checagem teria um buraco do
        # tamanho da unica superficie com WebSocket.
        '@router.websocket("/ws/wallboard")\n'
        "async def canal(ws):\n"
        "    return None\n"
    )
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario) / "api"
        raiz.mkdir()
        (raiz / "rotas.py").write_text(modulo, encoding="utf-8")
        achadas = rotas_implementadas(raiz)

    esperadas = {
        ("POST", "/turmas/{turma_id}/notas"),
        ("GET", "/alunos/{aluno_id}"),
        ("WS", "/ws/wallboard"),
    }
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


# ---------------------------------------------------------------------------
# PERFIL NUCLEO — os eixos que a peca 1 acrescentou.
#
# Sao tres familias novas, e cada uma existe porque o `range-api` nao e leitura:
# ele OPERA o exercicio. As tres tem probe pelo mesmo motivo que as outras cinco:
# regra sem prova negativa e regra que ninguem sabe se enxerga.
# ---------------------------------------------------------------------------

#: Catalogo de fixture, com uma entrada de OUTRA camada de proposito: sem ela, o
#: eixo de `truth_layer` nao teria com que ficar vermelho.
CATALOGO = {
    "inject_fired": "facilitation",
    "exercise_paused": "facilitation",
    "exercise_resumed": "facilitation",
    "containment_declared": "participant_action",
}

NUCLEO = {
    "method": "POST",
    "path": "/x",
    "papeis": ["facilitador"],
    "efeito": "nenhum",
    "status": "planejada",
}


def _nucleo(**mudancas):
    rota = dict(NUCLEO)
    rota.update(mudancas)
    return rota


PROBES_DE_EVENTO = [
    (
        "`emite` fora do catalogo — a quarta porta do nome de evento",
        [_nucleo(efeito="irreversivel", emite="inject_disparado", confirmacao=True)],
        "nao esta no catalogo",
    ),
    (
        "evento de OUTRA camada num comando de console",
        [_nucleo(efeito="irreversivel", emite="containment_declared", confirmacao=True)],
        # A mensagem deixou de nomear `facilitation` como constante e passou a
        # dizer o que O PERFIL admite — a camada virou propriedade do perfil na
        # peca 3 da Fase 6. O eixo e o mesmo: emitir camada de outra superficie.
        "so admite `facilitation`",
    ),
    (
        "rota que move o exercicio e nao emite evento",
        [_nucleo(efeito="irreversivel", confirmacao=True)],
        "nao declara `emite`",
    ),
    (
        "rota que emite evento e diz que nao move o exercicio",
        [_nucleo(efeito="nenhum", emite="inject_fired")],
        "MOVE o exercicio",
    ),
    ("caso verde: leitura sem evento", [_nucleo()], None),
    (
        "caso verde: comando com evento da camada certa",
        [_nucleo(efeito="irreversivel", emite="inject_fired", confirmacao=True)],
        None,
    ),
]

PROBES_DE_IRREVERSIBILIDADE = [
    (
        "`efeito` fora do vocabulario fechado",
        [_nucleo(efeito="quase-reversivel")],
        "fora de ['destrutivo', 'irreversivel', 'nenhum', 'reversivel']",
    ),
    (
        "irreversivel SEM confirmacao — o clique que dispara inject por engano",
        [_nucleo(efeito="irreversivel", emite="inject_fired")],
        "sem `confirmacao: true`",
    ),
    (
        "confirmacao onde NAO ha o que confirmar",
        [_nucleo(efeito="nenhum", confirmacao=True)],
        "treina o operador a clicar 'sim'",
    ),
    (
        "reversivel sem inverso — rotulo em vez de propriedade",
        [_nucleo(efeito="reversivel", emite="exercise_paused")],
        "sem `inverso`",
    ),
    (
        "inverso que nao e rota declarada",
        [_nucleo(efeito="reversivel", emite="exercise_paused", inverso="POST /nao-existe")],
        "nao e rota declarada",
    ),
    (
        "inverso de UMA seta so — A aponta para B, e B nao aponta de volta",
        [
            _nucleo(path="/pause", efeito="reversivel", emite="exercise_paused",
                    inverso="POST /resume"),
            _nucleo(path="/resume", efeito="reversivel", emite="exercise_resumed"),
        ],
        "nao declara",
    ),
    (
        "inverso declarado num efeito que nao tem volta",
        [_nucleo(efeito="irreversivel", emite="inject_fired", confirmacao=True,
                 inverso="POST /x")],
        "Se ha comando que desfaz",
    ),
    (
        "rota PUBLICA que move o exercicio — o console entregue a rede",
        [_nucleo(publica=True, papeis=[], efeito="destrutivo",
                 emite="inject_fired", confirmacao=True)],
        "move o exercicio",
    ),
    (
        "caso verde: o par PAUSAR/CONTINUAR, com as duas setas",
        [
            _nucleo(path="/pause", efeito="reversivel", emite="exercise_paused",
                    inverso="POST /resume"),
            _nucleo(path="/resume", efeito="reversivel", emite="exercise_resumed",
                    inverso="POST /pause"),
        ],
        None,
    ),
]

#: `(rotulo, declaradas, projecoes, esperado)` — D3, a metade declarativa.
PROBES_DE_CANAL = [
    (
        "canal e snapshot projetando coisas DIFERENTES",
        [
            _nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                    projecao="wallboard", snapshot="GET /a"),
            _nucleo(method="GET", path="/a", publica=True, papeis=[],
                    projecao="plateia"),
        ],
        ["wallboard", "plateia"],
        "serializacoes do mesmo fato",
    ),
    (
        "canal publico com snapshot autenticado — a assimetria pela autorizacao",
        [
            _nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                    projecao="wallboard", snapshot="GET /a"),
            _nucleo(method="GET", path="/a", papeis=["facilitador"],
                    projecao="wallboard"),
        ],
        ["wallboard"],
        "visibilidades diferentes",
    ),
    (
        "canal sem snapshot — refresh nao teria de onde recuperar",
        [_nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                 projecao="wallboard")],
        ["wallboard"],
        "canal sem `snapshot`",
    ),
    (
        "snapshot apontado que nao existe",
        [_nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                 projecao="wallboard", snapshot="GET /sumiu")],
        ["wallboard"],
        "nao e rota declarada",
    ),
    (
        "projecao usada e nao declarada no topo",
        [
            _nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                    projecao="fantasma", snapshot="GET /a"),
            _nucleo(method="GET", path="/a", publica=True, papeis=[],
                    projecao="fantasma"),
        ],
        [],
        "nao esta em `projecoes`",
    ),
    (
        "projecao declarada e nao usada",
        [],
        ["orfa"],
        "declarada e nao usada",
    ),
    (
        "dois canais para a mesma projecao",
        [
            _nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                    projecao="wallboard", snapshot="GET /a"),
            _nucleo(method="WS", path="/ws/b", publica=True, papeis=[],
                    projecao="wallboard", snapshot="GET /a"),
            _nucleo(method="GET", path="/a", publica=True, papeis=[],
                    projecao="wallboard"),
        ],
        ["wallboard"],
        "o par tem de ser exatamente um de cada",
    ),
    (
        "caso verde: um canal, um snapshot, mesma projecao e mesma visibilidade",
        [
            _nucleo(method="WS", path="/ws/a", publica=True, papeis=[],
                    projecao="wallboard", snapshot="GET /a"),
            _nucleo(method="GET", path="/a", publica=True, papeis=[],
                    projecao="wallboard"),
        ],
        ["wallboard"],
        None,
    ),
]


def _roda_familia(rotulo, problemas, esperado) -> bool:
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


def probe_da_tabela_de_perfis() -> bool:
    """A generalizacao so nao afrouxa se TODA superficie estiver classificada.

    Este e o eixo que a versao de uma superficie so nao precisava ter, e o que
    responde a pergunta "um verificador parametrizado nao fica mais frouxo que
    dois especificos?". Ele fica — se o perfil puder faltar. Aqui nao pode.
    """
    fora = verifica_tabela(set(SUPERFICIES) | {"outro/api_surface.yaml"})
    if not any("ausente da tabela de perfis" in p for p in fora):
        print(f"FALHA: superficie fora da tabela passou: {fora}")
        return False

    sumida = verifica_tabela(set(list(SUPERFICIES)[1:]))
    if not any("ausente do disco" in p for p in sumida):
        print(f"FALHA: entrada da tabela sem arquivo passou: {sumida}")
        return False

    if verifica_tabela(set(SUPERFICIES)):
        print("FALHA: a tabela coerente foi acusada")
        return False

    print("OK: reprovou com violacao plantada - superficie em disco fora da tabela")
    print("OK: reprovou com violacao plantada - entrada da tabela sem arquivo")
    return True


def probe_das_familias() -> bool:
    """Toda familia conhecida e reivindicada, e nenhuma reivindicada e desconhecida.

    Uma familia que nenhum perfil reivindica e regra escrita que nunca roda — a
    §7.3 da Fase 3 —, e um nome digitado errado a desligaria em silencio. Como as
    familias sao despachadas por nome em `main`, este e o unico ponto em que o
    erro de digitacao fica vermelho.
    """
    reivindicadas = set().union(*(p.familias for p in SUPERFICIES.values()))
    if reivindicadas != set(FAMILIAS_CONHECIDAS):
        print(
            f"FALHA: familias reivindicadas {sorted(reivindicadas)} != conhecidas "
            f"{sorted(FAMILIAS_CONHECIDAS)}"
        )
        return False

    # OS PERFIS PRECISAM SER DISTINGUIVEIS PELO VOCABULARIO, e nao so pelo nome.
    #
    # `probe_do_perfil_trocado` prova que trocar os perfis reprova alto. Essa
    # propriedade e CONSEQUENCIA de as chaves exclusivas serem disjuntas — nao e
    # regra escrita em lugar nenhum. Dois perfis que viessem a compartilhar
    # campos exclusivos fariam a troca voltar a ser silenciosa, e o probe de la
    # continuaria verde porque ele olha os arquivos de hoje.
    exclusivas = [
        p.chaves_de_rota_permitidas - PERFIL_DOMINIO.chaves_de_rota_permitidas
        if p is PERFIL_NUCLEO
        else p.chaves_de_rota_permitidas - PERFIL_NUCLEO.chaves_de_rota_permitidas
        for p in (PERFIL_NUCLEO, PERFIL_DOMINIO)
    ]
    if not exclusivas[0] or not exclusivas[1]:
        print(
            f"FALHA: um dos perfis nao tem campo exclusivo ({exclusivas}). Sem "
            "isso, classificar a superficie no perfil errado volta a ser silencioso."
        )
        return False

    print(f"OK: as {len(reivindicadas)} familias conhecidas sao todas reivindicadas")
    print(
        "OK: os dois perfis tem vocabulario exclusivo - "
        f"nucleo {sorted(exclusivas[0])}, dominio {sorted(exclusivas[1])}"
    )
    return True


def probe_das_chaves() -> bool:
    """Campo que ninguem le, e campo obrigatorio que alguem apagou.

    A segunda direcao e a que importa: regra que so roda quando o campo existe se
    desliga apagando o campo, e nada acusa. Foi a forma da `degradacao` como
    prosa na Fase 3 — declarada, lida por ninguem, ate a peca 5.
    """
    topo = {"papeis_de_exercicio": [], "projecoes": [], "rotas": [], "token": {}}
    desconhecida = verifica_chaves(topo, [], PERFIL_NUCLEO)
    if not any("chave de topo 'token' desconhecida" in p for p in desconhecida):
        print(f"FALHA: chave de topo estranha ao perfil passou: {desconhecida}")
        return False

    ausente = verifica_chaves({"rotas": []}, [], PERFIL_NUCLEO)
    if not any("ausente, e o perfil" in p for p in ausente):
        print(f"FALHA: chave de topo obrigatoria ausente passou: {ausente}")
        return False

    coerente = {"papeis_de_exercicio": [], "projecoes": [], "rotas": []}
    campo_de_outro_perfil = verifica_chaves(
        coerente, [_nucleo(flags=list(FLAGS))], PERFIL_NUCLEO
    )
    if not any("campo 'flags' nao existe no perfil" in p for p in campo_de_outro_perfil):
        print(f"FALHA: `flags` na superficie do nucleo passou: {campo_de_outro_perfil}")
        return False

    sem_efeito = verifica_chaves(
        coerente, [{"method": "GET", "path": "/x", "status": "planejada"}], PERFIL_NUCLEO
    )
    if not any("campo obrigatorio 'efeito' ausente" in p for p in sem_efeito):
        print(f"FALHA: rota do nucleo sem `efeito` passou: {sem_efeito}")
        return False

    if verifica_chaves(coerente, [_nucleo()], PERFIL_NUCLEO):
        print("FALHA: superficie coerente foi acusada")
        return False

    print("OK: reprovou com violacao plantada - chave de topo desconhecida")
    print("OK: reprovou com violacao plantada - chave de topo obrigatoria ausente")
    print("OK: reprovou com violacao plantada - campo do outro perfil na rota")
    print("OK: reprovou com violacao plantada - campo obrigatorio de rota ausente")
    return True


def probe_dos_papeis_do_nucleo() -> bool:
    """A ancora de `03` §7, nas duas direcoes — e a disjuncao que ela sustenta.

    O risco da generalizacao esta aqui: um verificador que recebesse "permitidos"
    e "recusados" por argumento aceitaria o par vazio e ficaria verde. Nao ha par
    — ha uma constante, e cada perfil se relaciona com ela de um jeito fixo.
    """
    sobrando = verifica(
        [], set(), {"facilitador", "operador", "avaliador", "aluno"}, set(), PERFIL_NUCLEO
    )
    # A mensagem deixou de nomear "papel de facilitacao" como categoria e passou
    # a nomear A FONTE do perfil — `03` §7 para o nucleo, `03` §6 para a
    # superficie de participante. O eixo e o mesmo: papel fora da ancora.
    if not any("que nao esta em `03` §7" in p for p in sobrando):
        print(f"FALHA: papel de dominio na superficie do nucleo passou: {sobrando}")
        return False

    faltando = verifica([], set(), {"facilitador"}, set(), PERFIL_NUCLEO)
    if not any("nao declara 'avaliador'" in p for p in faltando):
        print(f"FALHA: ancora encolhida passou: {faltando}")
        return False

    na_rota = verifica(
        [_nucleo(papeis=["aluno"])], set(),
        {"facilitador", "operador", "avaliador"}, set(), PERFIL_NUCLEO,
    )
    if not any("nao esta em `papeis_de_exercicio`" in p for p in na_rota):
        print(f"FALHA: papel de dominio numa rota do nucleo passou: {na_rota}")
        return False

    completo = verifica(
        [_nucleo()], set(), {"facilitador", "operador", "avaliador"}, set(), PERFIL_NUCLEO
    )
    if completo:
        print(f"FALHA: a superficie coerente do nucleo foi acusada: {completo}")
        return False

    print("OK: reprovou com violacao plantada - papel de dominio no nucleo")
    print("OK: reprovou com violacao plantada - ancora de `03` §7 encolhida")
    print("OK: reprovou com violacao plantada - papel fora do vocabulario, na rota")
    return True


def probe_do_catalogo_lido() -> bool:
    """O extrator do catalogo, contra o arquivo real.

    Sem ele, `catalogo_de_eventos` podendo devolver `{}` deixaria os probes de
    evento verdes pelo caminho errado — um catalogo vazio nao acusa camada
    nenhuma; acusa "nao esta no catalogo", que e outro eixo. E a mesma forma do
    `probe_dos_extratores`.
    """
    catalogo = catalogo_de_eventos(REPO_ROOT / "contracts" / "events.schema.yaml")
    if len(catalogo) < 30:
        print(f"FALHA: o catalogo lido tem {len(catalogo)} tipos")
        return False
    if catalogo.get("inject_fired") != "facilitation":
        print(f"FALHA: `inject_fired` veio como {catalogo.get('inject_fired')!r}")
        return False
    if catalogo.get("containment_declared") != "participant_action":
        print("FALHA: a camada de `containment_declared` nao foi lida")
        return False
    print(f"OK: o catalogo real e lido com {len(catalogo)} tipos e suas camadas")
    return True


def probe_do_perfil_trocado() -> bool:
    """Classificar a superficie no perfil ERRADO nao passa em silencio.

    A tabela fecha "superficie sem perfil". Sobra "superficie com o perfil do
    outro", e ela nao e fechavel por tabela nenhuma — a classificacao e
    declaracao de quem escreve.

    O que a fecha e consequencia dos vocabularios de chave serem DISJUNTOS: com
    os perfis trocados, `flags` e `degradacao` viram campo desconhecido e
    `efeito` vira campo obrigatorio ausente. O erro fica barulhento sem que
    ninguem tenha escrito uma regra sobre ele — e este probe e o que impede essa
    propriedade de ser argumento em vez de fato.
    """
    academus = parse_yaml(REPO_ROOT / "domains" / "academus" / "api_surface.yaml") or {}
    como_nucleo = verifica_chaves(academus, academus.get("rotas") or [], PERFIL_NUCLEO)
    if not any("chave de topo 'token' desconhecida" in p for p in como_nucleo):
        print(f"FALHA: superficie de dominio lida como nucleo passou: {como_nucleo}")
        return False
    # O discriminante era `efeito`, e ele DEIXOU de discriminar na peca 3 da
    # Fase 6: o perfil de dominio passou a exigi-lo tambem. Trocado por `flags`,
    # que segue sendo so do dominio — o probe prova que os perfis nao sao
    # intercambiaveis, e nao que um campo especifico existe.
    if not any("campo 'flags' nao existe no perfil 'nucleo'" in p for p in como_nucleo):
        print(f"FALHA: rota de dominio lida como nucleo nao foi acusada: {como_nucleo}")
        return False

    nucleo = parse_yaml(REPO_ROOT / "range-core" / "api_surface.yaml") or {}
    como_dominio = verifica_chaves(nucleo, nucleo.get("rotas") or [], PERFIL_DOMINIO)
    if not any("chave de topo 'projecoes' desconhecida" in p for p in como_dominio):
        print(f"FALHA: superficie do nucleo lida como dominio passou: {como_dominio}")
        return False
    # Mesma troca, pelo mesmo motivo: `projecao` continua sendo so do nucleo.
    if not any("campo 'projecao' nao existe no perfil" in p for p in como_dominio):
        print(f"FALHA: `efeito` numa leitura de dominio nao foi acusado: {como_dominio}")
        return False

    print("OK: perfil trocado reprova nos dois sentidos - dominio x nucleo")
    return True


def probe_da_varredura_de_superficies() -> bool:
    """A varredura acha as superficies em disco — e as duas estao na tabela."""
    em_disco = superficies_em_disco()
    if em_disco != set(SUPERFICIES):
        print(f"FALHA: em disco {sorted(em_disco)}, na tabela {sorted(SUPERFICIES)}")
        return False
    print(f"OK: a varredura acha as {len(em_disco)} superficies, e a tabela as cobre")
    return True


#: (rotulo, rotas, trecho esperado) — a familia `eventos` sob o PERFIL DE
#: DOMINIO. O eixo que estes dois provam e a camada: o adapter e aplicacao
#: instrumentada, e emitir `facilitation` por aqui seria console de facilitacao
#: dentro do dominio.
PROBES_DE_EVENTO_NO_DOMINIO = [
    (
        "adapter emitindo camada de facilitacao",
        [{"method": "post", "path": "/x", "efeito": "reversivel",
          "emite": "inject_fired"}],
        "so admite",
    ),
    (
        "adapter que move o exercicio e nao declara `emite`",
        [{"method": "post", "path": "/x", "efeito": "reversivel"}],
        "nao declara `emite`",
    ),
]


def probe_do_vocabulario_por_superficie() -> bool:
    """`persona` e proibido no token de dominio e CORRETO no de participante.

    Sem este probe, `vocabulario_proibido_em_claim` poderia ser o mesmo conjunto
    para todos os perfis e o verificador ficaria verde — a generalizacao sem
    prova de que ela generaliza.
    """
    from check_api_surface import PERFIL_PARTICIPANTE

    no_dominio = verifica_token(["sub", "persona", "exp"], ["sub", "persona", "exp"],
                                PERFIL_DOMINIO)
    if not any("nao pode existir no token da superficie" in p for p in no_dominio):
        print(f"FALHA: `persona` passou no token de dominio: {no_dominio}")
        return False

    no_participante = verifica_token(["sub", "persona", "exp"],
                                     ["sub", "persona", "exp"], PERFIL_PARTICIPANTE)
    if no_participante:
        print(f"FALHA: `persona` recusado na superficie dele: {no_participante}")
        return False

    facilitador = verifica_token(["sub", "facilitador", "exp"],
                                 ["sub", "facilitador", "exp"], PERFIL_PARTICIPANTE)
    if not any("nao pode existir no token da superficie" in p for p in facilitador):
        print(f"FALHA: papel de facilitacao passou no token de participante: {facilitador}")
        return False

    print("OK: reprovou com violacao plantada - vocabulario de claim POR SUPERFICIE")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1

    resultados = [roda(*p) for p in PROBES]
    resultados.extend(roda_token(*p) for p in PROBES_DE_TOKEN)
    resultados.extend(roda_degradacao(*p) for p in PROBES_DE_DEGRADACAO)
    resultados.append(probe_papel_de_exercicio_na_lista_de_origem())
    resultados.append(probe_do_escopo())
    resultados.append(probe_do_vocabulario_por_superficie())
    resultados.append(probe_dos_imports())
    resultados.append(probe_do_motivo_do_verde())
    resultados.append(probe_da_varredura())
    resultados.append(probe_do_limite_declarado())
    resultados.append(probe_dos_extratores())
    # PECA 1 DA FASE 4 — o perfil do nucleo.
    resultados.extend(
        _roda_familia(r, verifica_eventos(d, CATALOGO, PERFIL_NUCLEO), e)
        for r, d, e in PROBES_DE_EVENTO
    )
    # PECA 3 DA FASE 6 — a familia passou a rodar tambem no perfil de dominio,
    # e a camada admitida virou propriedade do perfil. Sem estes dois, a
    # generalizacao ficaria sem prova: o probe do nucleo continua verde mesmo
    # que o dominio admita qualquer camada.
    resultados.extend(
        _roda_familia(r, verifica_eventos(d, CATALOGO, PERFIL_DOMINIO), e)
        for r, d, e in PROBES_DE_EVENTO_NO_DOMINIO
    )
    resultados.extend(
        _roda_familia(r, verifica_irreversibilidade(d), e)
        for r, d, e in PROBES_DE_IRREVERSIBILIDADE
    )
    resultados.extend(
        _roda_familia(r, verifica_canais(d, p), e) for r, d, p, e in PROBES_DE_CANAL
    )
    resultados.append(probe_da_tabela_de_perfis())
    resultados.append(probe_das_familias())
    resultados.append(probe_das_chaves())
    resultados.append(probe_dos_papeis_do_nucleo())
    resultados.append(probe_do_catalogo_lido())
    resultados.append(probe_do_perfil_trocado())
    resultados.append(probe_da_varredura_de_superficies())

    print()
    if all(resultados):
        print(
            f"check_api_surface.py reprova nos {len(resultados)} eixos, com a "
            "direcao inversa em primeiro lugar — rota e claim —, mais a "
            "degradacao declarativa, o escopo de objeto, os imports e o limite "
            "de rota dinamica confirmado; e, no perfil do nucleo, o catalogo de "
            "eventos, a irreversibilidade dos comandos e o par canal/snapshot."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
