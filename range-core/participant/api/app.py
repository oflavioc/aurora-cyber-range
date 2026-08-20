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

O QUE ESTE MÓDULO ENTREGA NO BLOCO A, E O QUE FICA PARA O B
------------------------------------------------------------
Bloco A: a sessão — a troca de credencial por token, que é o que `05` §8 isenta
de autenticação, agora pela classe *"as rotas que trocam credencial por token"*
e não mais por uma instância no singular.

Bloco B: as nove declarações de `03` §3.4, com RBAC por persona e com o
predicado de completude da contrassinatura. Elas estão declaradas `planejada` na
superfície, e `check_api_surface.py` **reprova rota planejada que já exista no
código** — a promoção é cobrada pelo mesmo verificador que cobraria o
esquecimento.

O QUE ESTA ROTA NÃO FAZ
------------------------
Assinar a persona pedida no corpo. É o mesmo que a Fase 3 recusou em `POST
/auth/token` e que o console recusa em `POST /session`: quem apresenta a
credencial de uma persona recebe o token **daquela** persona, e de nenhuma
outra. A persona não é escolha do cliente; é consequência da credencial.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request

from range_core.participant.api import tokens

app = FastAPI(
    title="AURORA — participant-api",
    description="AMBIENTE SIMULADO — DADOS FICTÍCIOS",
)


@dataclass(frozen=True)
class Sessao:
    """O que a aplicação precisa para emitir. Injetado por `montar`."""

    credenciais: tokens.Credenciais
    segredo: str


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


def montar(personas: list[str], *, segredo: str) -> FastAPI:
    """Liga as credenciais de ambiente. Chamado pelo processo e pela suíte.

    `personas` chega como **dado**, da superfície — não é reescrito aqui. Duas
    listas sobre a mesma fronteira divergiriam, e a que diverge em silêncio é
    sempre a que ninguém está olhando.

    A recusa por credencial ausente sobe de `credenciais_do_ambiente` e **não é
    capturada**: persona declarada e sem credencial é exercício que descobre o
    defeito no meio da sala, e `05` §8 com D5 manda recusar alto.
    """
    app.state.sessao = Sessao(tokens.credenciais_do_ambiente(personas), segredo)
    return app
