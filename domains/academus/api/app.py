"""A `academus-api` — cinco rotas, e nenhuma delas sabe o que e uma flag.

O QUE OS HANDLERS DESTE ARQUIVO NAO TEM
----------------------------------------
Nao ha `if flag` aqui, e nao por disciplina: **nao ha flag ao alcance**. A
degradacao e uma dependencia global que le a declaracao da rota, e o handler nao
recebe estado de simulacao, nao importa constante de flag e nao tem por onde
saber que foi degradado — do mesmo jeito que ele nao sabe por que alguem foi
negado.

Nao ha regra de escopo aqui tambem. `repositorio.aluno(id, escopo)` devolve
`None` tanto para ausente quanto para fora de escopo, entao o unico `if` que o
handler escreve e `if registro is None` — e ele nao consegue distinguir os dois
casos nem se quisesse. A indistinguibilidade da peca 4 vale sem ninguem se
lembrar dela.

AS DUAS DEPENDENCIAS GLOBAIS, E A ORDEM ENTRE ELAS
---------------------------------------------------
`autoriza` primeiro, `degrada` depois. Invertida, a ordem entregaria o estado da
simulacao a quem nem token tem: um 503 de matricula responderia "a flag esta
ligada" para qualquer um na rede.

O ITEM 1 E O ITEM 2 DA DoD SAO ROTAS DESTE ARQUIVO
----------------------------------------------------
`POST /matricula` com `academus.enrollment_offline` e `POST
/turmas/{turma_id}/notas` com `academus.grades_readonly`. O terceiro endpoint
degradado, que `07` exige, e `GET /turmas/{turma_id}/diario` — o unico com flag
`number`, e por isso o unico em que o TIPO da flag muda a forma do efeito.

O QUE ESTA API NAO FAZ, e tem data
-----------------------------------
Nao emite evento. `audit_query_performed` e de classe `observation` e a §2 deste
registro ja o moveu para a **Fase 8**; a trilha de auditoria com hash e `06` T7,
**Fase 5**. Uma rota que emitisse evento aqui anteciparia as duas.

Nao ha servidor: `app` e um objeto ASGI, e subi-lo com `uvicorn` em
`AURORA_BIND_HOST`/`PORT` e da Fase 4.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from domains.academus.api import repositorio
from domains.academus.api.auth import Autenticacao, autoriza, escopo_do_pedido
from domains.academus.api.degradacao import Degradador, degrada
from domains.academus.api.repositorio import Escopo
from domains.academus.models.registros import como_json

app = FastAPI(
    title="academus-api",
    # AS TRES ROTAS QUE O FASTAPI ACRESCENTA SOZINHO, DESLIGADAS. Achado nesta
    # peca, e o defeito era da peca 4: `/openapi.json` respondia **200 sem
    # token**, com 3.870 bytes descrevendo a API inteira.
    #
    # A dependencia global nao as cobria, e nao por descuido de configuracao:
    # elas entram por `add_route`, que e Starlette puro e nao passa pelo sistema
    # de dependencias do FastAPI. A "falha fechada" da peca 4 valia para rota
    # declarada e nao valia para rota que o framework declara por voce.
    #
    # `05` §8 exige que nenhum servico fique exposto sem autenticacao, e a lista
    # completa de rotas e superficie: num exercicio sobre assimetria, ela conta
    # a quem ainda nao entrou o que existe para ser encontrado. Nao ha uso da
    # documentacao interativa dentro do exercicio; quem desenvolve a le no
    # `api_surface.yaml`, que e a declaracao de verdade.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # AS DUAS SAO GLOBAIS, e essa e a decisao: rota nova nasce protegida E
    # sujeita a declaracao de degradacao. O contrario — cada rota declarando as
    # suas guardas — faz das duas um item de checklist, e checklist e o que a
    # rota esquecida nao esta.
    dependencies=[Depends(autoriza), Depends(degrada)],
)


@app.get("/alunos/{aluno_id}")
async def ler_aluno(aluno_id: str, escopo: Escopo = Depends(escopo_do_pedido)) -> dict:
    """404 aqui cobre dois casos que o handler nao distingue, e nao deve.

    Aluno inexistente e aluno alheio chegam como `None`. Quem tem direito de
    saber que o aluno nao existe recebe a mesma coisa que quem nao tem direito
    de ver aquele aluno — e e assim que a regra de escopo nao vira oraculo.
    """
    registro = repositorio.aluno(aluno_id, escopo)
    if registro is None:
        raise HTTPException(status_code=404, detail="aluno nao encontrado")
    return como_json(registro)


@app.get("/turmas/{turma_id}")
async def ler_turma(turma_id: str, escopo: Escopo = Depends(escopo_do_pedido)) -> dict:
    registro = repositorio.turma(turma_id, escopo)
    if registro is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return como_json(registro)


@app.get("/turmas/{turma_id}/diario")
async def ler_diario(turma_id: str, escopo: Escopo = Depends(escopo_do_pedido)) -> dict:
    notas = repositorio.diario(turma_id, escopo)
    if notas is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return {"turma_id": turma_id, "notas": [como_json(n) for n in notas]}


@app.post("/turmas/{turma_id}/notas", status_code=201)
async def lancar_nota(
    turma_id: str,
    corpo: dict,
    escopo: Escopo = Depends(escopo_do_pedido),
) -> dict:
    registro = repositorio.lancar_nota(
        turma_id, str(corpo["aluno_id"]), float(corpo["valor"]), escopo
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return como_json(registro)


@app.post("/matricula", status_code=201)
async def matricular(corpo: dict, escopo: Escopo = Depends(escopo_do_pedido)) -> dict:
    registro = repositorio.matricular(
        str(corpo["aluno_id"]), str(corpo["turma_id"]), escopo
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="matricula nao pode ser efetuada")
    return como_json(registro)


def montar(autenticacao: Autenticacao, degradador: Degradador | None = None) -> FastAPI:
    """Liga autenticacao e degradacao a aplicacao. Chamado pelo processo e pela suite.

    `degradador` opcional, e o default e explicito: **sem ele nada degrada**. Nao
    e conveniencia — e o que impede que esquecer o wiring produza degradacao
    silenciosa ou, pior, excecao no meio de um exercicio. Quem monta o processo
    entrega o event store, as declaracoes do pack e o cache; quem nao entrega
    tem uma API que so autentica.
    """
    app.state.autenticacao = autenticacao
    app.state.degradador = degradador
    return app
