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
**Continua sem emitir evento**, e a trilha de auditoria da peca 3 nao mudou isso:
ela e tabela de dominio com cadeia propria (`02` §4), e nao o event store. O
primeiro `append` do adapter chega com `audit_query_performed`, que e **Fase 6** —
`07` Fase 6 tem o item de DoD literal *"consultar a trilha com filtro de periodo
emite `audit_query_performed`"*. O registro da Fase 3 e uma versao anterior deste
cabecalho diziam **Fase 8**, e a leitura certa e a de `07`.

E por isso a **P4-2** nao vence aqui: o gatilho dela e o primeiro `append` fora do
`inject-engine`, e nenhum modulo de `api/` chama `append`. Ela foi redatada para
a Fase 6 com o gatilho intacto.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request

from domains.academus.api.auth import Autenticacao, autoriza, escopo_do_pedido
from domains.academus.api.degradacao import (
    Degradador,
    confere_flags_declaradas,
    degrada,
)
from domains.academus.api.emissor import Emissor
from domains.academus.api.repositorio import Contexto, Escopo, Repositorio

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


def contexto_do_pedido(request: Request) -> Contexto:
    """Usuario, IP, user-agent e instante — `02` §4.1, e so a requisicao os tem.

    `request.client` e `None` quando nao ha peer — ASGI sem transporte, que e o
    caso de alguns clientes de teste. O fallback e explicito e nomeado em vez de
    string vazia: IP ausente numa trilha de auditoria e informacao, e uma cadeia
    string vazia se leria como "veio de lugar nenhum" sem dizer por que.
    """
    return Contexto(
        source_ip=request.client.host if request.client else "sem-peer",
        user_agent=request.headers.get("user-agent"),
        occurred_at=datetime.now(timezone.utc),
    )


@app.post("/classes/{class_id}/grades", status_code=201)
async def lancar_nota(
    class_id: str,
    corpo: dict,
    escopo: Escopo = Depends(escopo_do_pedido),
    repositorio: Repositorio = Depends(repositorio_do_pedido),
    contexto: Contexto = Depends(contexto_do_pedido),
) -> dict:
    """A P3-6: a nota e a linha de trilha entram na MESMA transacao.

    O 404 cobre agora TRES casos que o handler continua sem distinguir — turma
    inexistente, turma alheia e **aluno inexistente**, que e a P4-5. A mensagem
    fica generica pelo motivo de sempre: dizer qual dos tres ocorreu e responder
    a uma pergunta que quem lanca nota nao fez.
    """
    registro = repositorio.lancar_nota(
        class_id, str(corpo["student_id"]), float(corpo["value"]), escopo, contexto
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="turma ou aluno nao encontrado")
    return registro


@app.get("/audit/grade-changes")
async def alteracoes_de_nota(
    request: Request,
    period_start: str,
    period_end: str,
    group_by: str | None = None,
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    """Item 1 da DoD da Fase 6 — consultar a trilha com filtro de periodo EMITE.

    O PRIMEIRO `append` do adapter, e o gatilho declarado da P4-2. A guarda que
    a pendencia pedia entrou antes desta rota: `check_api_surface.py` exige
    `emite` de toda rota com `efeito` diferente de `nenhum`, e confere a camada
    contra o perfil.

    O EVENTO E DA CONSULTA, E NAO DO RESULTADO. `audit_query_performed` e
    `effect_class: observation` (`09` §4.0): registra que alguem CONSULTOU, sem
    afirmar nada sobre o que encontrou. `result_count` viaja no payload porque
    `observability_hooks.yaml` o declara — e ele e o tamanho do que a equipe viu,
    que e o que evidencia OBJ-03, e nao um juizo sobre os casos.

    A EMISSAO E DEPOIS DA LEITURA, e falha de emissao NAO derruba a resposta:
    a consulta ja aconteceu, e negar o resultado por causa do registro trocaria
    um defeito de instrumentacao por um defeito de exercicio. O que nao pode
    acontecer e a rota existir SEM emissor, e disso cuida a guarda de boot.
    """
    try:
        inicio = datetime.fromisoformat(period_start)
        fim = datetime.fromisoformat(period_end)
    except ValueError:
        raise HTTPException(status_code=422, detail="periodo em formato invalido")
    if fim <= inicio:
        raise HTTPException(status_code=422, detail="periodo vazio ou invertido")

    agrupar = group_by == "user"
    linhas = repositorio.alteracoes_de_nota(inicio, fim, agrupar)

    emissor = getattr(request.app.state, "emissor", None)
    if emissor is not None:
        emissor.registrar_consulta(
            period_start=period_start,
            period_end=period_end,
            group_by=group_by,
            result_count=len(linhas),
            escopo=escopo_do_pedido(request),
        )
    return {"linhas": linhas, "total": len(linhas)}


@app.get("/audit/verify-chain")
async def verificar_trilha(
    repositorio: Repositorio = Depends(repositorio_do_pedido),
) -> dict:
    """`02` §4 item 5 e `06` T7 — percorre a trilha e reporta a PRIMEIRA quebra.

    A RESPOSTA CARREGA A POSICAO E NADA ALEM. `06` T7 exige a posicao exata; `06`
    T6 varre o corpo de qualquer resposta procurando o que nao pode estar la, e
    despejar linhas de trilha aqui poria conteudo de investigacao numa rota que
    existe para responder uma pergunta de integridade.
    """
    resultado = repositorio.verificar_trilha()
    return {
        "linhas": resultado.linhas,
        "integra": resultado.integra,
        # `None` quando integra, e o campo EXISTE nos dois casos: resposta que
        # muda de forma conforme o resultado obriga o cliente a descobrir a forma
        # antes de ler o valor.
        "quebra": (
            None
            if resultado.quebra is None
            else {
                "sequence": resultado.quebra.sequence,
                "motivo": resultado.quebra.motivo,
            }
        ),
    }


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


def confere_emissor_declarado(superficie, emissor) -> None:
    """Rota que declara `emite` exige emissor ligado. Recusa ALTA no boot.

    A guarda e a mesma forma de `confere_flags_declaradas`, e pelo mesmo motivo:
    a superficie declara que a rota GRAVA EVENTO, e sem emissor ela responderia
    normalmente sem gravar nada. O exercicio inteiro se apoia em o registro
    reconstruir o que houve (`00` §5.5) — uma rota instrumentada em silencio e
    pior que uma rota nao instrumentada, porque a ausencia nao aparece.

    Nao ha degradacao para "emite quando puder": ou o emissor esta ligado, ou o
    boot para com a lista das rotas que ficariam mudas.

    ELA LE O `Superficie`, E NAO UM DICIONARIO — B1 da sexta auditoria. A versao
    anterior fazia `superficie.get("rotas")` sobre o objeto que `montar` lhe
    passa, que e um `dataclass` com `slots`: `AttributeError` em todo boot sem
    emissor, e em 49 testes. Ela havia sido escrita contra o YAML CRU e provada
    contra dicionarios escritos a mao — a forma que a producao nunca produz.

    A irma `confere_flags_declaradas` sempre leu `superficie.rotas.values()`. As
    duas guardas do mesmo boot liam formas diferentes do mesmo objeto.
    """
    if emissor is not None:
        return
    mudas = [
        f"{r.method} {r.path}"
        for r in superficie.rotas.values()
        if r.emite and r.status == "implementada"
    ]
    if mudas:
        raise RuntimeError(
            "rotas declaram `emite` e nao ha emissor ligado: " + ", ".join(mudas)
            + ".\n    `montar(..., emissor=...)`. Rota instrumentada em silencio "
            "e pior que rota nao instrumentada: a ausencia nao aparece."
        )


def montar(
    autenticacao: Autenticacao,
    repositorio: Repositorio,
    degradador: Degradador | None = None,
    emissor: Emissor | None = None,
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
    app.state.emissor = emissor
    confere_emissor_declarado(autenticacao.superficie, emissor)
    if degradador is not None:
        confere_flags_declaradas(
            autenticacao.superficie, degradador.leitura.declarations
        )
    return app
