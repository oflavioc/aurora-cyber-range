"""O `range-api` — o console, a sala, e o canal que empurra o estado.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4.2 (os comandos do console), §6 (gm-console, wallboard,
participant-view); `03_EXERCISE_DESIGN.md` §7; `05_SECURITY_REQUIREMENTS.md` §6
e §8; `07_IMPLEMENTATION_PHASES.md` Fase 4.

A SUPERFICIE FOI DECLARADA ANTES — `range-core/api_surface.yaml`, peca 1. Esta
peca implementa, e o verificador cobra a promocao de `planejada` para
`implementada` no mesmo commit.

AUTENTICACAO POR MIDDLEWARE, E NAO POR DEPENDENCIA
---------------------------------------------------
A `academus-api` usa dependencia global, e la isso basta. Aqui nao: **o
WebSocket nao passa pelo sistema de dependencias do FastAPI da mesma forma**, e
uma guarda que nao cobre o canal deixaria de fora justamente a rota que empurra o
estado da simulacao.

O middleware ASGI ve `http` e `websocket` com o mesmo codigo, e a decisao e por
lista de PUBLICOS lida da superficie — falha fechada: caminho que ninguem
declarou publico exige token. E o mesmo argumento do `papeis: []` da Fase 3, onde
lista vazia significa NINGUEM.

**Limite declarado:** o canal autenticado nao existe. Os dois canais desta fase
sao publicos por `05` §8, e o navegador nao envia cabecalho `Authorization` no
handshake de WebSocket — resolver isso exigiria token em query string ou
subprotocolo, e nenhum dos dois tem consumidor nesta fase.

O QUE CADA ROTA QUE MOVE O EXERCICIO TEM DE FAZER
---------------------------------------------------
Gravar o evento **e publicar**. Esquecer o segundo produz o pior defeito
possivel nesta fase: o exercicio anda e a sala nao ve. Por isso ha teste que
varre esta superficie por AST e exige `publicar` em toda rota cujo `efeito` na
declaracao nao seja `nenhum` — a coluna `efeito` da peca 1 ganhando o segundo
consumidor.
"""

from __future__ import annotations

import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket, WebSocketDisconnect

from range_core.api import projecoes, tokens
from range_core.api.hub import Hub
from range_core.api.superficie import Superficie
from range_core.engine.inject_engine import EngineError, InjectEngine
from range_core.events.epoch import current_epoch
from range_core.state.cache import SimulationStateCache, current
from range_core.state.simulation_state import Declarations

#: `05` §8 — a credencial do console vem do AMBIENTE, sem default. E a mesma
#: disciplina do `AURORA_JWT_SECRET` da Fase 3, e pelo mesmo motivo: senha
#: copiada de um exemplo versionado FUNCIONA, e um segredo que se comporta e
#: pior que um que se anuncia.
VARIAVEL_DA_CREDENCIAL = "AURORA_GM_PASSWORD"
MINIMO_DA_CREDENCIAL = 16

#: O unico papel desta fase — D5. `operador` e `avaliador` estao declarados na
#: superficie e sem rota: o NON-GOAL e "tres papeis de facilitacao".
PAPEL_DO_CONSOLE = "facilitador"

WALLBOARD = "wallboard"
PLATEIA = "plateia"

#: A pagina crua da peca 4. **Descartavel por decisao**, e a P4-3 registra o
#: destino: a peca 6 a substitui pelo bundle e esta rota passa a servir aquele.
PAGINA_DA_SALA = "sala.html"


class ConfiguracaoError(Exception):
    """O processo nao sobe. Alto, e no boot — nunca no meio do exercicio."""


def credencial_do_console(ambiente: Mapping[str, str] | None = None) -> str:
    """A credencial do facilitador. **Recusa alta, sem default.**

    Um default aqui seria vulnerabilidade intencional com outro nome: o console
    dispara inject e rebobina o exercicio, e `CLAUDE.md` nao admite isso sob
    nenhuma justificativa.
    """
    valor = (ambiente if ambiente is not None else os.environ).get(
        VARIAVEL_DA_CREDENCIAL, ""
    )
    if len(valor) < MINIMO_DA_CREDENCIAL:
        raise ConfiguracaoError(
            f"{VARIAVEL_DA_CREDENCIAL} ausente ou com menos de "
            f"{MINIMO_DA_CREDENCIAL} caracteres. O console opera o exercicio: "
            "disparo nao tem desfazer e rollback descarta estado. Gere um valor "
            "local — `python -c \"import secrets; print(secrets.token_urlsafe(24))\"`"
        )
    return valor


@dataclass
class Exercicio:
    """O que o processo entrega as rotas. Montado uma vez, no boot."""

    engine: InjectEngine
    cache: SimulationStateCache
    declarations: Declarations
    #: As flags do adapter como DADO — o core nao conhece `domains/`.
    specs: Mapping[str, Mapping]
    #: `inject_id -> texto_para_plateia`, e so isso. D6.
    textos: Mapping[str, str]
    credencial: str
    segredo: str

    @property
    def store(self):
        return self.engine._store  # noqa: SLF001 — o engine e quem o possui

    def estado(self):
        return current(self.store, self.declarations, self.cache)

    def frame_wallboard(self) -> bytes:
        return projecoes.wallboard(self.estado(), self.specs)

    def frame_plateia(self) -> bytes:
        return projecoes.plateia(self.store.read_all(), self.textos)


class Autenticacao:
    """Middleware ASGI: `http` e `websocket` com o mesmo codigo.

    Falha fechada — caminho fora da lista de publicos exige `Authorization:
    Bearer <token>` valido, com o papel do console.
    """

    def __init__(self, app: ASGIApp, superficie: Superficie) -> None:
        self.app = app
        self.superficie = superficie

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        caminho = scope.get("path", "")
        if self.superficie.e_publica(caminho):
            await self.app(scope, receive, send)
            return

        exercicio: Exercicio | None = scope["app"].state.exercicio
        if exercicio is None or not self._autorizado(scope, exercicio):
            await self._nega(scope, send)
            return
        await self.app(scope, receive, send)

    def _autorizado(self, scope: Scope, exercicio: Exercicio) -> bool:
        bruto = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
        if not bruto.lower().startswith("bearer "):
            return False
        try:
            claims = tokens.verify(bruto[7:], secret=exercicio.segredo)
        except tokens.TokenInvalid:
            return False
        return claims.role == PAPEL_DO_CONSOLE

    async def _nega(self, scope: Scope, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b'{"detail":"nao autenticado"}'})


app = FastAPI(
    title="range-api",
    # As tres rotas que o framework acrescenta sozinho, DESLIGADAS. Mesmo
    # argumento da peca 5 da Fase 3: `/openapi.json` respondia 200 sem token e
    # descrevia a API inteira. Aqui seria pior — esta e a API que opera o
    # exercicio.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _exercicio(request: Request) -> Exercicio:
    exercicio: Exercicio | None = request.app.state.exercicio
    if exercicio is None:
        raise HTTPException(status_code=503, detail="exercicio nao montado")
    return exercicio


def _json(conteudo: bytes) -> Response:
    """Os bytes da projecao, VERBATIM — e o motivo NAO e o que eu escrevi antes.

    A primeira redacao dizia que `JSONResponse` quebraria a igualdade byte a
    byte. **Medido: nao quebra.** O `JSONResponse` do FastAPI usa
    `separators=(",", ":")` e `ensure_ascii=False`, que sao as mesmas opcoes do
    serializador da peca 2 — e como aquele ja emite as chaves ORDENADAS, um
    `loads`/`dumps` devolve os mesmos bytes. Plantado, zero testes vermelhos.

    Isso nao enfraquece a decisao; muda o argumento dela, e para melhor:

    - a igualdade e verdadeira **pela forma canonica**, e nao por esta linha.
      `sort_keys` na producao e o que faz duas serializacoes concordarem;
    - o que esta linha acrescenta e nao depender de as opcoes do framework
      COINCIDIREM com as nossas. Elas coincidem hoje. Se uma subida de versao
      mudar `ensure_ascii`, os bytes divergem — e ai o teste fica vermelho, o que
      tambem foi medido.

    Ver `tests/test_range_api.py`, onde as quatro formas de divergencia estao
    plantadas e contadas.
    """
    return Response(content=conteudo, media_type="application/json")


def _publica(request: Request) -> None:
    request.app.state.hub.publicar()


# ---------------------------------------------------------------------------
# SESSAO
# ---------------------------------------------------------------------------
@app.post("/session")
async def abrir_sessao(corpo: dict, request: Request) -> dict:
    """Troca a credencial do ambiente por um token de `facilitador`.

    O que esta rota NAO faz e o que a Fase 3 recusou em `POST /auth/token`:
    assinar o papel pedido no corpo. O papel e constante aqui.
    """
    exercicio = _exercicio(request)
    if not hmac.compare_digest(str(corpo.get("credencial", "")), exercicio.credencial):
        raise HTTPException(status_code=401, detail="credencial invalida")
    return {
        "token": tokens.issue(
            "console", PAPEL_DO_CONSOLE, secret=exercicio.segredo
        )
    }


# ---------------------------------------------------------------------------
# CONSOLE — leitura
# ---------------------------------------------------------------------------
@app.get("/injects")
async def listar_injects(request: Request) -> dict:
    exercicio = _exercicio(request)
    disparados = {
        e.correlation.inject_id
        for e in exercicio.store.read_all()
        if e.event_type == projecoes.INJECT_FIRED
    }
    return {
        "injects": [
            {
                "id": inject.id,
                "t_relative": inject.t_relative,
                "titulo": inject.titulo_operacional,
                "disparado": inject.id in disparados,
            }
            for inject in exercicio.engine.pack.injects
        ]
    }


@app.get("/timeline")
async def ler_timeline(request: Request) -> Response:
    return _json(projecoes.timeline(_exercicio(request).store.read_all()))


# ---------------------------------------------------------------------------
# CONSOLE — os comandos. Cada um GRAVA e PUBLICA.
# ---------------------------------------------------------------------------
@app.post("/exercise/start")
async def iniciar(request: Request) -> dict:
    exercicio = _exercicio(request)
    try:
        evento = exercicio.engine.start()
    except EngineError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    _publica(request)
    return {"event_id": evento.event_id}


@app.post("/exercise/pause")
async def pausar(request: Request) -> dict:
    exercicio = _exercicio(request)
    evento = exercicio.engine.pause()
    _publica(request)
    return {"event_id": evento.event_id}


@app.post("/exercise/resume")
async def retomar(request: Request) -> dict:
    exercicio = _exercicio(request)
    evento = exercicio.engine.resume()
    _publica(request)
    return {"event_id": evento.event_id}


@app.post("/injects/{inject_id}/fire", status_code=201)
async def disparar(inject_id: str, request: Request) -> dict:
    exercicio = _exercicio(request)
    try:
        evento = exercicio.engine.fire(inject_id)
    except EngineError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    _publica(request)
    return {"event_id": evento.event_id, "inject_id": inject_id}


@app.post("/exercise/rollback")
async def rebobinar(corpo: dict, request: Request) -> dict:
    exercicio = _exercicio(request)
    try:
        evento = exercicio.engine.rollback(
            to_event_id=str(corpo["to_event_id"]), reason=str(corpo["reason"])
        )
    except EngineError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    _publica(request)
    # A EPOCH DA RESPOSTA E A NOVA, E A DO EVENTO E A ABANDONADA — as duas estao
    # certas, e a diferenca e de `09` §3: o `rollback_performed` e desenhado no
    # FIM da epoch que acabou, porque foi ali que ele foi ordenado. O console
    # precisa saber em que epoch o exercicio esta AGORA, e ela e uma leitura do
    # fluxo, nao um campo do evento.
    #
    # O teste desta rota afirmava `evento.simulation_epoch == 1` e reprovou com
    # `0 != 1`. O teste estava errado; a linha ficou.
    return {
        "event_id": evento.event_id,
        "simulation_epoch": current_epoch(exercicio.store.read_all()),
    }


# ---------------------------------------------------------------------------
# SALA — sem autenticacao, por `05` §8. As duas unicas.
# ---------------------------------------------------------------------------
@app.get("/wallboard/state")
async def estado_do_wallboard(request: Request) -> Response:
    return _json(_exercicio(request).frame_wallboard())


@app.get("/plateia/state")
async def estado_da_plateia(request: Request) -> Response:
    return _json(_exercicio(request).frame_plateia())


@app.websocket("/ws/wallboard")
async def canal_do_wallboard(websocket: WebSocket) -> None:
    await _serve_canal(websocket, WALLBOARD)


@app.websocket("/ws/plateia")
async def canal_da_plateia(websocket: WebSocket) -> None:
    await _serve_canal(websocket, PLATEIA)


async def _serve_canal(websocket: WebSocket, projecao: str) -> None:
    """O ESTADO CORRENTE PRIMEIRO, e so depois as mudancas.

    E o item 3 da DoD virando propriedade do protocolo: quem conecta agora
    recebe tudo, sem historico e sem pedir. Um canal que so mandasse mudancas
    deixaria o navegador recem-recarregado olhando uma tela vazia ate o proximo
    inject — que pode nao vir.
    """
    hub: Hub = websocket.app.state.hub
    await websocket.accept()
    fila = hub.inscrever(projecao)
    try:
        await websocket.send_bytes(hub.frame(projecao))
        while True:
            await websocket.send_bytes(await fila.get())
    except WebSocketDisconnect:
        pass
    finally:
        hub.cancelar(projecao, fila)


@app.get("/sala", response_class=HTMLResponse)
async def pagina_da_sala() -> HTMLResponse:
    """A pagina crua da peca 4 — **descartavel, e com destino registrado**.

    Ela existe para que a cadeia inteira seja VISTA antes de as telas existirem,
    e a Fase 4 e o marco que existe para ser visto. A peca 6 a substitui pelo
    bundle de `range-core/web/`, e esta rota passa a servir aquele — ver a P4-3.
    """
    caminho = Path(next(iter(__import__("range_core").__path__))) / "web" / PAGINA_DA_SALA
    return HTMLResponse(caminho.read_text(encoding="utf-8"))


def montar(exercicio: Exercicio | None) -> FastAPI:
    """Liga o exercicio a aplicacao. Chamado pelo processo e pela suite.

    `None` e explicito e responde 503: um processo que esquecesse o wiring teria
    uma API que autentica e nao opera, em vez de uma que opera pela metade.
    """
    superficie = Superficie.carregar()
    app.state.exercicio = exercicio
    app.state.hub = Hub(
        {
            WALLBOARD: (lambda: exercicio.frame_wallboard()) if exercicio else bytes,
            PLATEIA: (lambda: exercicio.frame_plateia()) if exercicio else bytes,
        }
    )
    if not any(m.cls is Autenticacao for m in app.user_middleware):
        app.add_middleware(Autenticacao, superficie=superficie)
    return app
