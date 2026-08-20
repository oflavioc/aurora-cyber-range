"""A `participant-api` — a superfície pela qual a persona declara.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §6; `03_EXERCISE_DESIGN.md` §3.4 e §6;
`05_SECURITY_REQUIREMENTS.md` §8. A superfície declarada é
`range-core/participant/api_surface.yaml`.

POR QUE UMA APLICAÇÃO SEPARADA DA DO CONSOLE
---------------------------------------------
As duas superfícies são irmãs e não aninhadas, e a razão é mecânica antes de ser
organizacional: `scripts/check_api_surface.py` varre as rotas de cada superfície
por `rglob` sobre o `api/` **irmão do próprio `api_surface.yaml`**. Aninhada sob
`range-core/api/`, esta aplicação seria varrida pelo perfil do console — e as
declarações de participante seriam julgadas por `camadas_de_emissao:
[facilitation]` e pelas famílias `irreversibilidade` e `canais`, que são de
comando de facilitação.

O QUE ESTE MÓDULO ENTREGA
--------------------------
A sessão — a troca de credencial por token, que é o que `05` §8 isenta de
autenticação, pela classe *"as rotas que trocam credencial por token"* e não
mais por uma instância no singular — e as **nove declarações** de `03` §3.4, com
RBAC por persona.

O predicado de completude da contrassinatura não está aqui: ele é do emissor,
porque é regra de EMISSÃO e não de rota. Ver `emissor.py`.

O QUE ESTA ROTA NÃO FAZ
------------------------
Assinar a persona pedida no corpo. É o mesmo que a Fase 3 recusou em `POST
/auth/token` e que o console recusa em `POST /session`: quem apresenta a
credencial de uma persona recebe o token **daquela** persona, e de nenhuma
outra. A persona não é escolha do cliente; é consequência da credencial.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request

from contracts.generated.events import (
    ASSESSMENT_SUBMITTED,
    CLASSIFICATION_DECLARED,
    COMMUNICATION_SUBMITTED,
    CONTAINMENT_DECLARED,
    INCIDENT_DECLARED,
    INTEGRITY_VALIDATION_DECLARED,
    REGULATORY_NOTICE_SUBMITTED,
    SEPARATE_INCIDENT_DECLARED,
    SERVICE_RESTORATION_DECLARED,
)
from range_core.participant.api import tokens
from range_core.participant.api.emissor import EmissaoRecusada, Emissor

app = FastAPI(
    title="AURORA — participant-api",
    description="AMBIENTE SIMULADO — DADOS FICTÍCIOS",
)


@dataclass(frozen=True)
class Sessao:
    """O que a aplicação precisa para emitir. Injetado por `montar`."""

    credenciais: tokens.Credenciais
    segredo: str
    #: `(METODO, caminho) -> personas declaradas`. Vem da SUPERFÍCIE, e não de
    #: uma tabela escrita aqui: duas listas sobre a mesma fronteira divergiriam,
    #: e a que diverge em silêncio é sempre a que ninguém está olhando. É o mesmo
    #: desenho do `autoriza` do adapter.
    personas_por_rota: dict[tuple[str, str], frozenset[str]] = field(
        default_factory=dict
    )
    emissor: Emissor | None = None


def _sessao(request: Request) -> Sessao:
    sessao = getattr(request.app.state, "sessao", None)
    if sessao is None:
        # Falha fechada: sem wiring não há emissão. Um default silencioso aqui
        # seria credencial em memória, que é o que a P3-5 removeu do adapter.
        raise HTTPException(status_code=503, detail="sessao nao configurada")
    return sessao


@app.post("/participant/session")
async def abrir_sessao(corpo: dict, request: Request) -> dict:
    """Troca a credencial de ambiente de uma persona pelo token dela.

    A persona vem no corpo **para ser conferida**, e não para ser assinada: o
    que decide o token é a credencial casar com a daquela persona. Persona
    inexistente e credencial errada devolvem o **mesmo** 401, sem distinguir —
    distinguir diria a quem tenta qual metade acertou.
    """
    sessao = _sessao(request)
    persona = str(corpo.get("persona", ""))
    if not sessao.credenciais.confere(persona, str(corpo.get("credencial", ""))):
        raise HTTPException(status_code=401, detail="credencial invalida")
    return {"token": tokens.issue(persona, persona, secret=sessao.segredo)}



# ---------------------------------------------------------------------------
# RBAC POR PERSONA — a tabela é a SUPERFÍCIE, e não uma segunda lista aqui
# ---------------------------------------------------------------------------


def _persona_autorizada(request: Request, rota: str) -> tuple[str, str]:
    """Devolve `(persona, actor_id)` do token, ou recusa.

    As personas admitidas vêm de `personas_por_rota`, montado da superfície —
    que é a mesma tabela que `check_api_surface.py` confere contra a coluna
    `Quem` de `03` §3.4. Escrever a lista aqui criaria duas fontes sobre a mesma
    fronteira, e a que diverge em silêncio é sempre a que ninguém olha.

    **403, e não 404.** A pergunta *"esta persona pode usar esta rota?"* se
    decide sem consultar recurso nenhum — é a distinção que o repositório do
    adapter já registra: 404 é para *"este recurso é seu?"*, que é indistinguível
    de não existir.
    """
    sessao = _sessao(request)
    cabecalho = request.headers.get("authorization", "")
    if not cabecalho.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="token ausente")
    try:
        claims = tokens.verify(cabecalho[7:], secret=sessao.segredo)
    except tokens.TokenInvalid:
        raise HTTPException(status_code=401, detail="token invalido")

    admitidas = sessao.personas_por_rota.get(("POST", rota), frozenset())
    if claims.persona not in admitidas:
        raise HTTPException(status_code=403, detail="persona sem acesso a esta acao")
    return claims.persona, claims.sub


async def _declara(
    request: Request, corpo: dict, rota: str, event_type: str
) -> dict:
    """O corpo comum das nove: autoriza, emite, devolve o `event_id`.

    **Uma função, nove rotas.** As nove diferem no caminho, nas personas e no
    `event_type` — tudo declarado. Escrever nove corpos iguais seria a classe D4
    com outro nome, e o que divergiria primeiro é a justificativa obrigatória.

    O `event_id` volta ao cliente porque a contrassinatura precisa dele: é o
    `causation_id` que a segunda mão envia.
    """
    persona, actor_id = _persona_autorizada(request, rota)
    sessao = _sessao(request)
    if sessao.emissor is None:
        raise HTTPException(status_code=503, detail="emissor nao configurado")
    try:
        evento = sessao.emissor.declarar(
            event_type,
            persona=persona,
            actor_id=actor_id,
            justificativa=str(corpo.get("justificativa", "")),
            causation_id=corpo.get("causation_id"),
            payload={k: v for k, v in corpo.items()
                     if k not in {"justificativa", "causation_id"}},
        )
    except EmissaoRecusada as recusa:
        # 409: o pedido é bem formado e o ESTADO o recusa — contrassinatura sem
        # antecedente, fora de ordem, ou sobre par já fechado.
        raise HTTPException(status_code=409, detail=str(recusa))
    return {"event_id": evento.event_id}


@app.post("/participant/incident", status_code=201)
async def declarar_incidente(corpo: dict, request: Request) -> dict:
    """Qualquer persona — `03` §3.4. Reconhecer que HÁ incidente é percepção."""
    return await _declara(request, corpo, "/participant/incident", INCIDENT_DECLARED)


@app.post("/participant/incident/separate", status_code=201)
async def declarar_incidente_separado(corpo: dict, request: Request) -> dict:
    """TI. Afirmar que são DOIS é conclusão sobre evidência — o objeto do OBJ-03."""
    return await _declara(
        request, corpo, "/participant/incident/separate", SEPARATE_INCIDENT_DECLARED
    )


@app.post("/participant/classification", status_code=201)
async def declarar_classificacao(corpo: dict, request: Request) -> dict:
    """TI. O stop de `TTT` — severidade e escopo declarados."""
    return await _declara(
        request, corpo, "/participant/classification", CLASSIFICATION_DECLARED
    )


@app.post("/participant/containment", status_code=201)
async def declarar_contencao(corpo: dict, request: Request) -> dict:
    """TI. O `TTCD` do par — e o delta para `TTCV` é o achado (`03` §3.2)."""
    return await _declara(
        request, corpo, "/participant/containment", CONTAINMENT_DECLARED
    )


@app.post("/participant/service-restoration", status_code=201)
async def declarar_restauracao(corpo: dict, request: Request) -> dict:
    """TI. O `TTRD` do par."""
    return await _declara(
        request, corpo, "/participant/service-restoration", SERVICE_RESTORATION_DECLARED
    )


@app.post("/participant/integrity-validation", status_code=201)
async def declarar_integridade(corpo: dict, request: Request) -> dict:
    """A ÚNICA de duas mãos. Pró-Reitoria declara, TI contrassina com `causation_id`.

    As duas personas invocam esta mesma rota: o que distingue o primeiro ato do
    segundo é o `causation_id`, e não o caminho. O predicado de completude e as
    três recusas de emissão estão em `emissor.py`.
    """
    return await _declara(
        request,
        corpo,
        "/participant/integrity-validation",
        INTEGRITY_VALIDATION_DECLARED,
    )


@app.post("/participant/communication", status_code=201)
async def submeter_comunicacao(corpo: dict, request: Request) -> dict:
    """Comunicação. O stop de `TTCM` — a submissão CONSTITUI a resposta."""
    return await _declara(
        request, corpo, "/participant/communication", COMMUNICATION_SUBMITTED
    )


@app.post("/participant/regulatory-notice", status_code=201)
async def submeter_notificacao(corpo: dict, request: Request) -> dict:
    """DPO. Também stop de `TTCM`, por OBJ-09."""
    return await _declara(
        request, corpo, "/participant/regulatory-notice", REGULATORY_NOTICE_SUBMITTED
    )


@app.post("/participant/assessment", status_code=201)
async def submeter_avaliacao(corpo: dict, request: Request) -> dict:
    """TI e Pró-Reitoria. O insumo do limiar de `TTIV` (`03` §3.3 e §5)."""
    return await _declara(
        request, corpo, "/participant/assessment", ASSESSMENT_SUBMITTED
    )


def montar(
    superficie: dict,
    *,
    segredo: str,
    emissor: Emissor | None = None,
) -> FastAPI:
    """Liga as credenciais de ambiente. Chamado pelo processo e pela suíte.

    `personas` chega como **dado**, da superfície — não é reescrito aqui. Duas
    listas sobre a mesma fronteira divergiriam, e a que diverge em silêncio é
    sempre a que ninguém está olhando.

    A recusa por credencial ausente sobe de `credenciais_do_ambiente` e **não é
    capturada**: persona declarada e sem credencial é exercício que descobre o
    defeito no meio da sala, e `05` §8 com D5 manda recusar alto.
    """
    personas = list(superficie.get("personas") or [])
    por_rota = {
        (str(r["method"]).upper(), r["path"]): frozenset(r.get("papeis") or [])
        for r in (superficie.get("rotas") or [])
        if r.get("papeis")
    }
    app.state.sessao = Sessao(
        tokens.credenciais_do_ambiente(personas), segredo, por_rota, emissor
    )
    return app
