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

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from domains.academus.api.surface import PROPRIO, TITULAR
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
        self, class_id: str, student_id: str, value: float, escopo: Escopo
    ) -> dict | None:
        with Session(self._engine) as sessao:
            if self._turma(sessao, class_id, escopo) is None:
                return None
            registro = Grade(student_id=student_id, class_id=class_id, value=value)
            sessao.add(registro)
            sessao.commit()
            # DENTRO da sessao e DEPOIS do commit: `expire_on_commit` e o default,
            # entao o proximo atributo recarrega do banco. E o que se quer — a
            # resposta descreve o que ficou gravado, e nao o que se pediu.
            return como_json(registro)

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
