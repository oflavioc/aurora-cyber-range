"""Student, Class, Grade e Enrollment — o business state, agora em Postgres.

O QUE MUDOU AQUI, E POR QUE A FRASE ANTERIOR PRECISAVA CAIR
-------------------------------------------------------------
Este arquivo dizia, em prosa, *"em memoria, e nao em banco... um esquema
provisorio criaria migration que a Fase 5 teria de desfazer"*. Era verdade
quando escrita e deixou de ser: `01` §4 poe Business State em Postgres e o
declara *"nao reversivel por rollback; so por reset total"*, e essa linha e
falsa enquanto o dado mora em dicionario de modulo — **reinicio nao e reset
total**, e reiniciava tudo do mesmo jeito. A Fase 4 e a primeira em que existe
container que reinicia, entao e aqui que a linha se conserta. E a P3-5, e e a
§1.6 da Fase 1 outra vez.

O corte de escopo continua valendo, e nao foi desfeito: `07` Fase 3 poe **modelo
completo** e **seed em escala** nos NON-GOALS, e nada disso entra agora.
Historico, Diploma, Bolsa, Contrato, CalendarioAcademico e AutorizacaoRetificacao
seguem fora; regra de negocio de nota segue fora; volume segue fora — o dataset
de 28 mil alunos e `06` T8, Fase 5.

O QUE ENTRA, e por que quatro e nao tres
------------------------------------------
`07` Fase 3 nomeia tres entidades, e a D8 escreveu "as tres tabelas" lendo essa
lista. A P3-5 nomeia os dicionarios de modulo, e sao **quatro**: `ALUNOS`,
`TURMAS`, `NOTAS` e `MATRICULAS`. Deixar `MATRICULAS` em memoria fecharia tres
quartos da pendencia e manteria o defeito no caminho do item 1 da DoD, que e
`POST /enrollment`.

IDIOMA — P4-1, e onde exatamente passa a linha
------------------------------------------------
`CLAUDE.md` §Idioma poe **identificadores, tabelas, colunas e endpoints** em
ingles. As classes daqui MAPEIAM tabelas, entao acompanham: `Student`, `Class`,
`Grade`, `Enrollment`.

O que **nao** muda, e a distincao nao e conveniencia: os valores de papel
(`aluno`, `professor`, `secretaria`, `financeiro`) sao vocabulario de persona,
que `03` §6 e §7 escrevem em portugues, e nao identificador. E os nomes de
modulo e de funcao interna deste repositorio — `registros`, `repositorio`,
`degradacao`, `superficie` — continuam como estao: mudar isso e edicao em todo
modulo do projeto, nao tem item de DoD que a cobre, e a P4-1 e sobre **endpoint**,
que e o que atravessa o fio. O limite esta dito para nao parecer inconsistencia
restante.

`Class` E NOME DE CLASSE, e o desconforto e menor que a alternativa
--------------------------------------------------------------------
`Turma` em ingles e `class`, e a tabela se chama `classes`. Inventar
`CourseClass` ou `Section` poria no codigo um nome que o esquema nao tem, e a
divergencia entre os dois e exatamente o que a P4-1 existe para nao deixar
comecar. `class` e palavra reservada; `Class` nao e.

DADOS SINTETICOS
----------------
`05` §3. Os seis registros de demonstracao estao em
`domains/academus/seed/demonstracao.py`, fora daqui e fora da migration.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, ForeignKey, Index, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadata das quatro tabelas de business state.

    NAO inclui `event_store`, e a ausencia e deliberada: aquela tabela e do
    core, tem migration propria e e lida por `psycopg` cru. Um modelo
    declarativo para ela poria o esquema do event store sob a metadata de um
    adapter, que e a direcao que o invariante 1 existe para nao deixar acontecer.
    """


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    program: Mapped[str] = mapped_column(Text, nullable=False)


class Class(Base):
    __tablename__ = "classes"

    class_id: Mapped[str] = mapped_column(Text, primary_key=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    semester: Mapped[str] = mapped_column(Text, nullable=False)
    #: O DONO. E o que a regra `titular` compara com o `sub` do token (P3-3), e
    #: dono que nao existe no dado nao e verificavel.
    professor_id: Mapped[str] = mapped_column(Text, nullable=False)


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (Index("ix_grades_class_id", "class_id"),)

    grade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: SEM FK, e a ausencia esta nomeada — P4-5. A rota nao confere se o aluno
    #: existe, entao uma FK aqui mudaria 201 em erro de integridade: mudanca de
    #: comportamento de rota entrando por efeito colateral de esquema.
    student_id: Mapped[str] = mapped_column(Text, nullable=False)
    class_id: Mapped[str] = mapped_column(
        Text, ForeignKey("classes.class_id", name="fk_grades_class"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    student_id: Mapped[str] = mapped_column(
        Text, ForeignKey("students.student_id", name="fk_enrollments_student"), nullable=False
    )
    class_id: Mapped[str] = mapped_column(
        Text, ForeignKey("classes.class_id", name="fk_enrollments_class"), nullable=False
    )


#: O QUE CADA ENTIDADE MOSTRA NA RESPOSTA. Whitelist, e nao `asdict` do objeto.
#:
#: A versao anterior serializava o dataclass inteiro, e ali isso era seguro
#: porque o dataclass tinha exatamente os campos publicos. Com ORM deixa de ser:
#: um `__dict__` de instancia carrega `_sa_instance_state`, e uma coluna nova —
#: `internal_note`, `flagged_by` — entraria na resposta por existir. E a mesma
#: forma da D6, aplicada ao business state: vazar passa a exigir escrever o
#: campo aqui, em vez de esquecer de tira-lo.
#:
#: A CHAVE SUBSTITUTA FICA DE FORA das duas que a tem: `grade_id` e
#: `enrollment_id` sao identidade de linha, nao dado de negocio, e a resposta da
#: Fase 3 nao os tinha.
CAMPOS_PUBLICOS: dict[type, tuple[str, ...]] = {
    Student: ("student_id", "name", "program"),
    Class: ("class_id", "subject", "semester", "professor_id"),
    Grade: ("student_id", "class_id", "value"),
    Enrollment: ("student_id", "class_id"),
}


def como_json(registro) -> dict:
    """Serializacao rasa, pela whitelist. Chamada DENTRO da sessao.

    Fora da sessao um objeto destacado levanta `DetachedInstanceError` no
    primeiro atributo — e por isso o repositorio serializa antes de fechar a
    sessao, e devolve `dict`. Ver o cabecalho de `repositorio.py`.
    """
    campos = CAMPOS_PUBLICOS.get(type(registro))
    if campos is None:
        raise TypeError(
            f"{type(registro).__name__} nao esta em CAMPOS_PUBLICOS. Entidade nova "
            "declara o que mostra; serializar por reflexao poria campo novo na "
            "resposta por ele existir."
        )
    return {campo: getattr(registro, campo) for campo in campos}
