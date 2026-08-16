"""A `academus-api`. Duas rotas de leitura, e o RBAC que nega as outras.

O QUE ESTA PECA IMPLEMENTA, E O QUE ELA NAO TOCA
-------------------------------------------------
Implementa `GET /alunos/{aluno_id}` e `GET /turmas/{turma_id}` — as duas rotas
que o `api_surface.yaml` declarou com `flags: []` e `degradacao: nenhuma`, e o
comentario que as declarou ja dizia por que elas existem: *"o RBAC precisa de
rota que NEGUE"*.

**Nenhuma flag e lida aqui.** A degradacao por flag e a D4, e a peca 5 e o lugar
dela; decidi-la de passagem numa rota seria decidi-la por acidente. A garantia
nao e disciplina: `scripts/check_api_surface.py` reprova se um modulo de `api/`
importar `range_core.state` enquanto nenhuma rota implementada declarar flag.

`POST /auth/token` CONTINUA `planejada`, e o motivo esta na declaracao
--------------------------------------------------------------------
Emitir token exige autenticar um usuario, e usuario nao e entidade da Fase 3 —
`07` nomeia Aluno, Turma e Nota, e poe seed em escala nos NON-GOALS. Um endpoint
de login que assinasse o papel pedido no corpo seria vulnerabilidade
intencional, que `CLAUDE.md` proibe sem excecao.

Entao o JWT desta fase e emitido por `Autenticacao.emitir_token`, exercitado
pela suite com token de verdade sobre o stack ASGI de verdade, e o login chega
na Fase 5 com as personas do seed.

NAO HA SERVIDOR AQUI
--------------------
`app` e um objeto ASGI. Subi-lo com `uvicorn` em `AURORA_BIND_HOST`/`PORT` e da
Fase 4, que e a fase do DEMO e do container — pinar um runner que nada executa
seria dependencia sem consumidor.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from domains.academus.api.auth import Autenticacao, autoriza
from domains.academus.models.registros import ALUNOS, TURMAS, como_json

app = FastAPI(
    title="academus-api",
    # A DEPENDENCIA E GLOBAL, e essa e a decisao: rota nova nasce protegida, e
    # esquecer de proteger deixa de ser possivel. O contrario — cada rota
    # declarando a sua guarda — faz da protecao um item de checklist, e checklist
    # e o que a rota esquecida nao esta.
    dependencies=[Depends(autoriza)],
)


@app.get("/alunos/{aluno_id}")
async def ler_aluno(aluno_id: str) -> dict:
    """404 aqui e para quem TEM direito de saber que o aluno nao existe.

    Quem nao tem ja foi negado por `autoriza`, antes desta funcao comecar — e
    por isso a negacao nao pode variar com a existencia do registro.
    """
    registro = ALUNOS.get(aluno_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="aluno nao encontrado")
    return como_json(registro)


@app.get("/turmas/{turma_id}")
async def ler_turma(turma_id: str) -> dict:
    registro = TURMAS.get(turma_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return como_json(registro)


def montar(autenticacao: Autenticacao) -> FastAPI:
    """Liga a autenticacao a aplicacao. Chamado pelo processo, e pela suite.

    Injetar em vez de ler o ambiente no import: modulo que le `os.environ` no
    topo torna a aplicacao impossivel de montar duas vezes com segredos
    diferentes, e e o que faria o teste precisar mexer no ambiente do processo.
    """
    app.state.autenticacao = autenticacao
    return app
