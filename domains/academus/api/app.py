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
casos nem se quisesse. A indistinguibilidade da peca 4 da Fase 3 vale sem
ninguem se lembrar dela.

E nao ha SQL aqui. O repositorio devolve `dict` ja serializado, dentro da
sessao — o handler nao tem sessao para vazar nem objeto destacado para tropecar.

AS DUAS DEPENDENCIAS GLOBAIS, E A ORDEM ENTRE ELAS
---------------------------------------------------
`autoriza` primeiro, `degrada` depois. Invertida, a ordem entregaria o estado da
simulacao a quem nem token tem: um 503 de matricula responderia "a flag esta
ligada" para qualquer um na rede. E, desde a P3-10, a ordem tambem e o que torna
o **sujeito** disponivel a degradacao: quem cai e decidido pelo `sub` de um
token ja verificado.

OS CAMINHOS ESTAO EM INGLES — P4-1
------------------------------------
Eram `/alunos`, `/turmas`, `/turmas/{id}/diario`, `/turmas/{id}/notas` e
`/matricula`. `CLAUDE.md` §Idioma poe **endpoints** na lista do ingles, junto de
identificadores, tabelas, colunas, logs e nomes de flag e de evento, e a mesma
secao poe em portugues a interface, os dados sinteticos, os cenarios, as
rubricas e a documentacao — caminho de rota nao e nenhum dos cinco.

A renomeacao veio nesta peca e nao na peca 1 porque ela e **mudanca de
produto**: toca a superficie declarada, os handlers, os testes de RBAC e os de
degradacao. Fazer isso na peca 1 misturaria a correcao com a superficie nova, e
a peca deixaria de ter uma volta. Aqui o `repositorio.py` inteiro ja muda de
forma pela P3-5, e os mesmos testes ja vao ser tocados: renomear junto e uma
edicao; renomear a parte sao duas.

**A unica excecao do projeto e `/plateia`**, e ela e da SPEC — `01` §6 escreve o
caminho da participant-view assim, literalmente, e documento normativo prevalece
sobre a convencao. Ela vive na superficie do NUCLEO, e esta dita la. Depois
desta peca nao ha inconsistencia restante: ha uma excecao, com fonte.

O ITEM 1 E O ITEM 2 DA DoD DA FASE 3 SAO ROTAS DESTE ARQUIVO
--------------------------------------------------------------
`POST /enrollment` com `academus.enrollment_offline` e `POST
/classes/{class_id}/grades` com `academus.grades_readonly`. O terceiro endpoint
degradado, que `07` exige, e `GET /classes/{class_id}/gradebook` — o unico com
flag `number`, e por isso o unico em que o TIPO da flag muda a forma do efeito.

O QUE ESTA API NAO FAZ, e tem data
-----------------------------------
Nao emite evento. `audit_query_performed` e de classe `observation` e ja foi
movido para a **Fase 8**; a trilha de auditoria com hash e `06` T7, **Fase 5**.
Uma rota que emitisse evento aqui anteciparia as duas — e e a P4-2 que espera
esse commit, porque e nele que a metade sem guarda ganha sujeito.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from domains.academus.api.auth import Autenticacao, autoriza, escopo_do_pedido
from domains.academus.api.degradacao import (
    Degradador,
    confere_flags_declaradas,
    degrada,
)
from domains.academus.api.repositorio import Escopo, Repositorio

app = FastAPI(
    title="academus-api",
    # AS TRES ROTAS QUE O FASTAPI ACRESCENTA SOZINHO, DESLIGADAS. Achado na peca
    # 5 da Fase 3, e o defeito era da peca 4: `/openapi.json` respondia **200 sem
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


def repositorio_do_pedido(request: Request) -> Repositorio:
    """O repositorio montado no boot. Dependencia de handler.

    Vem do `app.state` e nao de variavel de modulo: variavel de modulo e
    exatamente o que a P3-5 acabou de tirar daqui, e ela voltaria pela porta do
    wiring. Quem monta o processo entrega o engine; quem nao entrega nao tem
    aplicacao — ver `montar`.
    """
    return request.app.state.repositorio


@app.get("/students/{student_id}")
async def ler_aluno(
    student_id: str,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    """404 aqui cobre dois casos que o handler nao distingue, e nao deve.

    Aluno inexistente e aluno alheio chegam como `None`. Quem tem direito de
    saber que o aluno nao existe recebe a mesma coisa que quem nao tem direito
    de ver aquele aluno — e e assim que a regra de escopo nao vira oraculo.
    """
    registro = repositorio.aluno(student_id, escopo)
    if registro is None:
        raise HTTPException(status_code=404, detail="aluno nao encontrado")
    return registro


@app.get("/classes/{class_id}")
async def ler_turma(
    class_id: str,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    registro = repositorio.turma(class_id, escopo)
    if registro is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return registro


@app.get("/classes/{class_id}/gradebook")
async def ler_diario(
    class_id: str,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    notas = repositorio.diario(class_id, escopo)
    if notas is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return {"class_id": class_id, "grades": notas}


@app.post("/classes/{class_id}/grades", status_code=201)
async def lancar_nota(
    class_id: str,
    corpo: dict,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    registro = repositorio.lancar_nota(
        class_id, str(corpo["student_id"]), float(corpo["value"]), escopo
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="turma nao encontrada")
    return registro


@app.post("/enrollment", status_code=201)
async def matricular(
    corpo: dict,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    registro = repositorio.matricular(
        str(corpo["student_id"]), str(corpo["class_id"]), escopo
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="matricula nao pode ser efetuada")
    return registro


def montar(
    autenticacao: Autenticacao,
    repositorio: Repositorio,
    degradador: Degradador | None = None,
) -> FastAPI:
    """Liga autenticacao, persistencia e degradacao. Chamado pelo processo e pela suite.

    `repositorio` e OBRIGATORIO e `degradador` e OPCIONAL, e a assimetria e
    deliberada. Sem repositorio nao ha aplicacao: toda rota implementada le ou
    escreve business state, e um default silencioso so poderia ser um duplo em
    memoria — que e o que a P3-5 acabou de remover. Sem degradador ha uma API
    que so autentica, e isso e util e explicito: esquecer o wiring nao pode
    produzir degradacao silenciosa nem excecao no meio de um exercicio.

    A GUARDA DE BOOT DA P3-11 RODA AQUI, e so quando ha degradador — sem ele
    nenhuma flag e lida, entao nao ha o que ficar no-op. Ela recusa alto: flag
    citada na superficie e ausente do estado corrente derrubaria a rota para um
    `None` silencioso, e `06` T2 exige que isso impeca o boot com mensagem
    nomeando flag e arquivo.
    """
    app.state.autenticacao = autenticacao
    app.state.repositorio = repositorio
    app.state.degradador = degradador
    if degradador is not None:
        confere_flags_declaradas(
            autenticacao.superficie, degradador.leitura.declarations
        )
    return app
