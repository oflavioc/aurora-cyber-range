"""A busca dos registros — e a unica porta por onde a regra de escopo passa.

A P3-3 RESOLVIDA: UM CAMPO, DUAS REGRAS, E ELA MORA AQUI
---------------------------------------------------------
A pendencia perguntava se o escopo de objeto era um campo ou tres. Com as tres
entidades da para ver: **e um campo**. Todos os casos sao *"um campo do recurso
e igual ao `sub` do token"*, e o que muda entre eles e QUAL campo — o que e
valor, e nao dimensao.

    `proprio`  — o recurso E o sujeito         (`Student.student_id == sub`)
    `titular`  — o recurso PERTENCE ao sujeito (`Class.professor_id == sub`)

Papel fora do mapa nao tem restricao de objeto: a `secretaria` ve qualquer
aluno e qualquer turma, e isso e desenho, nao esquecimento.

POR QUE A REGRA MORA NA BUSCA, E NAO DEPOIS DELA
-------------------------------------------------
A peca 4 da Fase 3 fechou o vazamento de existencia numa dependencia global que
**nao tem repositorio ao alcance**. A regra de objeto nao pode ser assim:
decidir se a turma e sua exige ler a turma.

Entao a saida nao e negar depois de achar — e fazer **"nao e sua" e "nao
existe" virarem o mesmo caminho de codigo**. `turma(id, escopo)` devolve `None`
nos dois casos, e o handler, que so sabe tratar `None`, responde 404 sem nunca
aprender a diferenca.

A propriedade da peca 4 continua valendo, e continua valendo pelo mesmo motivo:
**a resposta nunca varia com a existencia de um recurso que quem pergunta nao
pode ver.** As duas consequencias sao diferentes porque as perguntas sao
diferentes, e nao porque ha duas politicas:

- *"este papel pode usar esta rota?"* — 403, decidido sem consultar nada.
- *"este recurso e seu?"* — indistinguivel de *"nao existe"*, entao 404.

Um 403 aqui diria "existe, e nao e sua", que e exatamente o que a regra de
escopo existe para nao dizer.

A P3-5: O ESTADO SAIU DO DICIONARIO DE MODULO
-----------------------------------------------
Ate a peca 4 desta fase, `ALUNOS`, `TURMAS`, `NOTAS` e `MATRICULAS` eram
dicionarios e listas de modulo. `01` §4 poe Business State em Postgres e o
declara *"nao reversivel por rollback; so por reset total"* — e reinicio nao e
reset total. `02` §7 fixa **SQLAlchemy**, e e ele.

**O repositorio devolve `dict`, e nao instancia de modelo.** Nao e preferencia
de estilo: objeto ORM fora da sessao levanta `DetachedInstanceError` no primeiro
atributo, e a saida usual — `expire_on_commit=False` mais confiar em que os
atributos ja foram carregados — poe uma condicao de corrida entre o handler e o
ciclo de vida da sessao. Serializar **dentro** da sessao a elimina: o que sai
daqui nao tem sessao para perder.

Isso tambem preserva a forma do handler: ele continua escrevendo `if registro is
None` e mais nada.

UMA SESSAO POR CHAMADA PUBLICA
--------------------------------
Cada metodo publico abre uma sessao e a fecha; os privados recebem a sessao
aberta. A alternativa — sessao por requisicao, injetada — traria transacao
atravessando `autoriza`, `degrada` e o handler, e a degradacao por `latencia`
seguraria uma conexao aberta por 2,5 s **por requisicao degradada**. Numa rota
que o exercicio existe para martelar, isso e o pool acabando durante a sala.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.orm import Session

from domains.academus.api.surface import PROPRIO, TITULAR
from domains.academus.audit import trilha
from domains.academus.models.registros import (
    Class,
    Enrollment,
    Grade,
    Student,
    como_json,
)
from range_core.events.postgres_store import normalize_dsn


@dataclass(frozen=True, slots=True)
class Escopo:
    """O sujeito e a regra que vale para ele NESTA rota.

    `regra` vem da declaracao, resolvida por `autoriza` — o handler nunca a
    escolhe, e por isso nao tem como escolher errado.
    """

    sub: str
    regra: str | None


@dataclass(frozen=True, slots=True)
class Contexto:
    """O que `02` §4.1 exige da REQUISICAO, e que so existe no ponto dela.

    Usuario, IP, user-agent e o instante. A P3-6 registrou exatamente isto:
    *"tres deles so podem ser preenchidos no ponto da requisicao. Quem chegar na
    Fase 5 pela via do banco nao vai encontra-los; encontra a rota."*

    `occurred_at` VEM DE FORA e nao de `now()` aqui: o instante do fato e do
    handler, e uma segunda leitura de relogio dentro do repositorio produziria
    dois tempos para o mesmo ato. O `recorded_at` da linha, esse sim, e o `now()`
    do banco — sao as duas marcas do timestamp duplo.
    """

    source_ip: str
    user_agent: str | None
    occurred_at: datetime


class Repositorio:
    """A borda de persistencia da `academus-api`. Montada uma vez, no boot."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # -- privados: recebem a sessao aberta e devolvem o objeto ORM ----------

    def _aluno(self, sessao: Session, student_id: str, escopo: Escopo) -> Student | None:
        registro = sessao.get(Student, student_id)
        if registro is None:
            return None
        if escopo.regra == PROPRIO and registro.student_id != escopo.sub:
            return None
        return registro

    def _turma(self, sessao: Session, class_id: str, escopo: Escopo) -> Class | None:
        registro = sessao.get(Class, class_id)
        if registro is None:
            return None
        if escopo.regra == TITULAR and registro.professor_id != escopo.sub:
            return None
        return registro

    # -- publicos: uma sessao cada, e `dict` na saida -----------------------

    def aluno(self, student_id: str, escopo: Escopo) -> dict | None:
        with Session(self._engine) as sessao:
            registro = self._aluno(sessao, student_id, escopo)
            return None if registro is None else como_json(registro)

    def turma(self, class_id: str, escopo: Escopo) -> dict | None:
        with Session(self._engine) as sessao:
            registro = self._turma(sessao, class_id, escopo)
            return None if registro is None else como_json(registro)

    def diario(self, class_id: str, escopo: Escopo) -> list[dict] | None:
        """As notas de uma turma. **Passa pela turma**, e o escopo vem de la.

        Nota nao tem regra propria, e nao e omissao: ela e alcancada atraves da
        turma, entao quem nao ve a turma nao ve o diario dela. Uma segunda regra
        aqui seria a mesma regra escrita duas vezes — a classe D4.
        """
        with Session(self._engine) as sessao:
            if self._turma(sessao, class_id, escopo) is None:
                return None
            # ORDENADA, e a ordem e a de insercao. Sem `ORDER BY`, o Postgres
            # nao promete ordem nenhuma, e o diario mudaria de forma entre duas
            # leituras identicas — que na sala e lido como "o sistema esta
            # baguncando as notas", e nao como ausencia de clausula.
            notas = sessao.scalars(
                select(Grade).where(Grade.class_id == class_id).order_by(Grade.grade_id)
            ).all()
            return [como_json(nota) for nota in notas]

    def lancar_nota(
        self,
        class_id: str,
        student_id: str,
        value: float,
        escopo: Escopo,
        contexto: Contexto,
    ) -> dict | None:
        """Lanca a nota E grava a trilha, na MESMA transacao — P3-6 e D4.

        `01` §4.3 diz que reverter business state geraria *"evento na trilha de
        auditoria sem correspondente no banco"*. A reciproca e esta: nota gravada
        sem linha de trilha e o mesmo estado impossivel pelo outro lado, e era o
        que a P3-6 registrava desde a Fase 3. Trilha como efeito colateral depois
        do `commit` produz, na primeira falha, nota sem registro.

        A P4-5 FECHA AQUI, e com o par que a pendencia previu: o aluno e
        conferido e a resposta e 404 — a mesma que a turma inexistente ja dava —,
        e so entao a FK da 0004 documenta no esquema o que esta linha passou a
        fazer. `test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje` fica vermelho
        neste commit, que era o anuncio armado na Fase 4.

        404 E NAO 400, e a escolha nao e cosmetica: `_aluno` com escopo devolve
        `None` tanto para ausente quanto para fora de escopo, e um 400 aqui
        contaria a diferenca. A indistinguibilidade da peca 4 da Fase 3 vale
        tambem para quem lanca nota.
        """
        with Session(self._engine) as sessao:
            turma = self._turma(sessao, class_id, escopo)
            if turma is None:
                return None
            # SEM ESCOPO na busca do aluno: quem lanca e o titular da turma, e o
            # aluno nao e "dele" em sentido nenhum. `Escopo(sub, None)` pergunta
            # so pela existencia.
            if self._aluno(sessao, student_id, Escopo(sub=escopo.sub, regra=None)) is None:
                return None

            registro = Grade(student_id=student_id, class_id=class_id, value=value)
            sessao.add(registro)
            sessao.flush()

            trilha.registrar(
                sessao,
                trilha.Registro(
                    category=trilha.ALTERACAO_DE_NOTA,
                    actor_user_id=escopo.sub,
                    source_ip=contexto.source_ip,
                    user_agent=contexto.user_agent,
                    object_type="grade",
                    object_id=str(registro.grade_id),
                    occurred_at=contexto.occurred_at,
                    # `02` §4.1: nota anterior, nova nota, semestre, disciplina.
                    # A anterior e `None` no lancamento — nao ha o que havia —, e
                    # `None` aqui diz "nao havia", enquanto omitir o campo diria
                    # "ninguem registrou". A Linha B depende dessa diferenca.
                    payload={
                        "previous_value": None,
                        "new_value": value,
                        "class_id": class_id,
                        "student_id": student_id,
                        "semester": turma.semester,
                        "subject_id": turma.subject_id,
                    },
                    within_window=trilha.dentro_da_janela(
                        sessao, turma.semester, contexto.occurred_at.date()
                    ),
                    # NULO NO LANCAMENTO: autorizacao de retificacao existe para
                    # alteracao fora da janela, e a Fase 8 e quem traz a rota que
                    # altera nota ja lancada. Aqui o campo e nulo com o sentido
                    # que `02` §4.1 lhe da — "nulo quando nao houver".
                    authorization_id=None,
                ),
            )
            sessao.commit()
            # DENTRO da sessao e DEPOIS do commit: `expire_on_commit` e o default,
            # entao o proximo atributo recarrega do banco. E o que se quer — a
            # resposta descreve o que ficou gravado, e nao o que se pediu.
            return como_json(registro)

    def verificar_trilha(self) -> trilha.Resultado:
        """`GET /audit/verify-chain`. Leitura, e nada alem — ver a D14.

        Sessao propria e somente leitura: a verificacao nao escreve, nao emite
        evento e nao muda flag. Se escrevesse — um marcador de "verificado em" —,
        verificar a trilha alteraria a trilha, e a cadeia passaria a depender de
        quantas vezes alguem perguntou.
        """
        with Session(self._engine) as sessao:
            return trilha.verificar(sessao)

    def alteracoes_de_nota(
        self, inicio: datetime, fim: datetime, agrupar_por_usuario: bool
    ) -> list[dict]:
        """`GET /audit/grade-changes` — a trilha filtrada por período.

        É a consulta que a Linha B exige: `02` §6 põe as alterações indevidas
        dentro de uma massa de alterações legítimas, e distinguir umas das outras
        é o trabalho analítico que OBJ-03 e OBJ-04 medem. Esta rota é a
        ferramenta, e não a resposta — ela devolve o que está na trilha, sem
        marcar nada como suspeito.

        **Leitura, e nada além.** Sessão própria, somente leitura, pelo mesmo
        argumento de `verificar_trilha`: se a consulta escrevesse, consultar a
        trilha alteraria a trilha.

        `agrupar_por_usuario` devolve contagem por ator em vez das linhas. Os
        dois modos existem porque o hook de `observability_hooks.yaml` declara
        `group_by` no payload: a consulta agrupada é a que evidencia OBJ-03 —
        *"reconhecer incidentes concorrentes"* começa por ver que um usuário
        concentra alterações fora de janela.
        """
        with Session(self._engine) as sessao:
            if agrupar_por_usuario:
                linhas = sessao.execute(
                    text(
                        "SELECT actor_user_id, COUNT(*) AS total "
                        "FROM audit_trail "
                        "WHERE category = :categoria "
                        "  AND occurred_at >= :inicio AND occurred_at < :fim "
                        "GROUP BY actor_user_id ORDER BY total DESC, actor_user_id"
                    ),
                    {
                        "categoria": trilha.ALTERACAO_DE_NOTA,
                        "inicio": inicio,
                        "fim": fim,
                    },
                ).all()
                return [
                    {"actor_user_id": linha[0], "total": int(linha[1])}
                    for linha in linhas
                ]

            linhas = sessao.execute(
                text(
                    "SELECT sequence, actor_user_id, occurred_at, object_id, "
                    "       within_window, authorization_id "
                    "FROM audit_trail "
                    "WHERE category = :categoria "
                    "  AND occurred_at >= :inicio AND occurred_at < :fim "
                    "ORDER BY sequence"
                ),
                {"categoria": trilha.ALTERACAO_DE_NOTA, "inicio": inicio, "fim": fim},
            ).all()
            return [
                {
                    "sequence": int(linha[0]),
                    "actor_user_id": linha[1],
                    "occurred_at": str(linha[2]),
                    "object_id": linha[3],
                    "within_window": linha[4],
                    "authorization_id": linha[5],
                }
                for linha in linhas
            ]

    def matricular(self, student_id: str, class_id: str, escopo: Escopo) -> dict | None:
        """Matricula. O escopo vale sobre o ALUNO — a turma e livre.

        Um aluno matricula a si mesmo em qualquer turma; a `secretaria`
        matricula qualquer um. Nao ha regra sobre a turma porque nao ha dono a
        comparar: o `titular` dela e o professor, e professor nao matricula.
        """
        with Session(self._engine) as sessao:
            if self._aluno(sessao, student_id, escopo) is None:
                return None
            if sessao.get(Class, class_id) is None:
                return None
            registro = Enrollment(student_id=student_id, class_id=class_id)
            sessao.add(registro)
            sessao.commit()
            return como_json(registro)


def engine_do_ambiente(url: str) -> Engine:
    """Monta o engine a partir da URL do SQLAlchemy. Sem default, por desenho.

    `pool_pre_ping` porque o container da peca 7 sobrevive ao Postgres reiniciar
    e a conexao ociosa nao sabe disso: sem ele, a primeira requisicao depois do
    reinicio do banco morre com conexao fechada, o que na sala aparece como a
    aplicacao caindo sozinha.

    O DIALETO E O DO SQLAlchemy, e nao o DSN cru. O event store fala `psycopg`
    direto e por isso normaliza; aqui a conversao e a inversa, e ela existe para
    que **uma** variavel de ambiente sirva aos dois. Duas variaveis para o mesmo
    banco e a forma de elas divergirem — o cabecalho de `normalize_dsn` ja diz
    isso, e este e o outro lado.
    """
    return create_engine(_dialeto_sqlalchemy(url), pool_pre_ping=True)


def _dialeto_sqlalchemy(url: str) -> str:
    """`postgresql://...` -> `postgresql+psycopg://...`, e idempotente.

    Sem isto, uma URL em DSN cru faria o SQLAlchemy escolher o driver DEFAULT do
    dialeto — `psycopg2` —, que nao esta instalado nem pinado. O erro apareceria
    no boot do container como "modulo nao encontrado", longe da causa.
    """
    normalizada = normalize_dsn(url)
    return normalizada.replace("postgresql://", "postgresql+psycopg://", 1)
