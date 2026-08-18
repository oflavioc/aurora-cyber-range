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

O MODELO COMPLETO — a peca 2 da Fase 5
----------------------------------------
`07` Fase 5 poe *"modelo completo"* nos OUTPUTS, e completo e medido contra
`02` §1, que e a unica lista que a spec da. Dezoito das vinte entidades viram
tabela; `Incidente` e `Declaracao` NAO, porque `01` §4 poe Participant Actions no
event store com reversibilidade "nunca" — elas chegam como projecao na Fase 6.
`access_delegations` fecha a lacuna de §1 em relacao a §6.1, que exige "registro
formal de delegacao" sem lista-lo entre as entidades.

O raciocinio inteiro, com o que ficou de fora e contra qual fase vizinha, esta em
`alembic/versions/0003_modelo_completo.py` e na §4.2 do registro da fase.

`program` E `subject` MUDARAM DE FONTE, E NAO DE CHAVE
-------------------------------------------------------
As duas eram texto livre. Agora `Student` referencia `Course` e `Class`
referencia `Subject`, e o nome vem por relacao — mas **a resposta continua
trazendo `program` e `subject` com o mesmo valor**, porque `CAMPOS_PUBLICOS` le
atributo e nao coluna. E deliberado: renomear a chave seria mudanca de
comportamento de rota que a Fase 3 entregou e auditou, entrando por efeito
colateral de esquema — exatamente o que a P4-5 recusou pelo outro lado.

`tests/test_modelo_completo.py` fixa os quatro conjuntos de chaves e fica
VERMELHO se algum mudar. Coluna nova nao vaza sozinha: a whitelist e o que faz
disso propriedade em vez de cuidado.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Metadata das quatro tabelas de business state.

    NAO inclui `event_store`, e a ausencia e deliberada: aquela tabela e do
    core, tem migration propria e e lida por `psycopg` cru. Um modelo
    declarativo para ela poria o esquema do event store sob a metadata de um
    adapter, que e a direcao que o invariante 1 existe para nao deixar acontecer.
    """


class AcademicCalendar(Base):
    """`02` §2. Sem esta entidade a Linha B nao e detectavel.

    A CHAVE E O PROPRIO SEMESTRE, e e isso que manteve `classes.semester`
    intacta: a coluna da resposta nao mudou de tipo, de valor nem de nome — so
    ganhou FK. Chave substituta aqui teria obrigado a reescrever a resposta.

    A janela de retificacao e o que `within_window` compara no momento da
    gravacao (`02` §4.1), e e por isso que ela nao pode ser nula: janela ausente
    tornaria `within_window` indefinido, e a trilha registraria indefinicao como
    se fosse fato.
    """

    __tablename__ = "academic_calendar"

    semester: Mapped[str] = mapped_column(Text, primary_key=True)
    classes_start: Mapped[date] = mapped_column(Date, nullable=False)
    classes_end: Mapped[date] = mapped_column(Date, nullable=False)
    grade_entry_start: Mapped[date] = mapped_column(Date, nullable=False)
    grade_entry_end: Mapped[date] = mapped_column(Date, nullable=False)
    rectification_start: Mapped[date] = mapped_column(Date, nullable=False)
    rectification_end: Mapped[date] = mapped_column(Date, nullable=False)
    enrollment_start: Mapped[date] = mapped_column(Date, nullable=False)
    enrollment_end: Mapped[date] = mapped_column(Date, nullable=False)
    graduation_date: Mapped[date] = mapped_column(Date, nullable=False)
    admission_exam_start: Mapped[date] = mapped_column(Date, nullable=False)
    admission_exam_end: Mapped[date] = mapped_column(Date, nullable=False)


class User(Base):
    """`02` §1 Usuario — o sujeito de tudo que a trilha registra.

    `password_hash`, NUNCA senha: `05` §8 exige que a senha de seed venha do
    `RANDOM_SEED` e seja impressa apenas no log de seed local.

    `role` admite `servico` alem dos quatro papeis de dominio de
    `api_surface.yaml` — `svc_migration` de `02` §6.1 e conta de servico, e conta
    de servico nao faz login. A lista fechada que `emitir_token` le continua
    sendo a do YAML, e este valor nao entra la.
    """

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Course(Base):
    __tablename__ = "courses"

    course_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    degree_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: NULLABLE, e o motivo esta na 0003: o campus nao existe no dado antigo, e
    #: o seed da peca 4 e quem escreve os cinco de `02`.
    campus: Mapped[str | None] = mapped_column(Text, nullable=True)


class Professor(Base):
    __tablename__ = "professors"

    professor_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    #: A CONTA DOCENTE. `02` §6.1 abre os indevidos comprovados com "conta
    #: docente unica": sem esta ligacao, "quem alterou" e "de quem e a conta"
    #: sao dois textos que ninguem cruza.
    user_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_professors_user"), nullable=True
    )
    department: Mapped[str | None] = mapped_column(Text, nullable=True)


class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    course_id: Mapped[str] = mapped_column(
        Text, ForeignKey("courses.course_id", name="fk_subjects_course"), nullable=False
    )
    credits: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RectificationAuthorization(Base):
    """`02` §3 — a entidade que torna a Linha B realista.

    Sem ela, "fora da janela = fraude" e o exercicio vira busca por
    `WHERE within_window = false`. Os cinco campos sao os que a secao nomeia, e
    nada alem: a ligacao com a alteracao de nota e feita pela TRILHA
    (`authorization_id` em `02` §4.1), que nasce na peca 3.
    """

    __tablename__ = "rectification_authorizations"

    authorization_id: Mapped[str] = mapped_column(Text, primary_key=True)
    requester_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_rectauth_requester"), nullable=False
    )
    approver_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_rectauth_approver"), nullable=False
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    process_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    authorized_on: Mapped[date] = mapped_column(Date, nullable=False)


class AccessDelegation(Base):
    """A lacuna de `02` §1 em relacao a §6.1, e nao uma entidade nova.

    §6.1 exige o conjunto "Credenciais compartilhadas — 18: monitor/assistente
    usando conta do professor **com registro formal de delegacao**". A spec pede
    a coisa e nao a lista em §1.

    TABELA E NAO CAMPO NA TRILHA: a delegacao existe antes e independentemente da
    alteracao de nota. Como campo, ela viraria propriedade do evento — repetida a
    cada alteracao e sem validade consultavel —, e o console da Fase 8 pergunta
    "havia delegacao valida naquela data?", que e consulta a fato.
    """

    __tablename__ = "access_delegations"
    __table_args__ = (
        Index(
            "ix_delegations_delegating",
            "delegating_user_id",
            "valid_from",
            "valid_until",
        ),
    )

    delegation_id: Mapped[str] = mapped_column(Text, primary_key=True)
    delegating_user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", name="fk_delegation_delegating"),
        nullable=False,
    )
    delegate_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_delegation_delegate"), nullable=False
    )
    process_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    course_id: Mapped[str] = mapped_column(
        Text, ForeignKey("courses.course_id", name="fk_students_course"), nullable=False
    )
    #: NASCEM INVISIVEIS: nao estao em `CAMPOS_PUBLICOS`, entao nenhuma resposta
    #: muda por eles existirem. `02` §5 pede distribuicao plausivel de evasao, e
    #: evasao e situacao do aluno.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ativo")
    entry_semester: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("academic_calendar.semester", name="fk_students_entry"),
        nullable=True,
    )

    course: Mapped[Course] = relationship(lazy="joined")

    @property
    def program(self) -> str:
        """O nome do curso, sob a chave que a resposta sempre teve.

        A FONTE mudou — era texto livre na propria linha, agora vem de `courses`
        —, e a CHAVE nao. Renomear seria mudanca de comportamento de uma rota
        entregue e auditada, entrando por efeito colateral de esquema.

        `lazy="joined"` porque `como_json` roda dentro da sessao e a alternativa
        seria um SELECT por aluno lido — `01` §7 nao proibe isso nominalmente,
        mas o diario de uma turma cheia viraria N+1 numa rota de exercicio.
        """
        return self.course.name


class Class(Base):
    __tablename__ = "classes"

    class_id: Mapped[str] = mapped_column(Text, primary_key=True)
    subject_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("subjects.subject_id", name="fk_classes_subject"),
        nullable=False,
    )
    #: MESMA COLUNA DA 0002 — mesmo tipo, mesmo valor, mesmo nome. Ganhou FK
    #: porque agora existe a tabela; a resposta nao muda em nada.
    semester: Mapped[str] = mapped_column(
        Text,
        ForeignKey("academic_calendar.semester", name="fk_classes_semester"),
        nullable=False,
    )
    #: O DONO. E o que a regra `titular` compara com o `sub` do token (P3-3), e
    #: dono que nao existe no dado nao e verificavel. A 0002 o deixou sem FK
    #: porque `professors` nao existia; existe agora, e a FK nao muda a regra.
    professor_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("professors.professor_id", name="fk_classes_professor"),
        nullable=False,
    )

    subject_record: Mapped[Subject] = relationship(lazy="joined")

    @property
    def subject(self) -> str:
        """O nome da disciplina, sob a chave que a resposta sempre teve.

        Mesmo movimento de `Student.program`, e o atributo de relacao se chama
        `subject_record` justamente para nao colidir com a chave publica.
        """
        return self.subject_record.name


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
    #: Invisivel na resposta, como `Student.status`. A unicidade de matricula
    #: continua fora: e regra de negocio, e a 0002 ja recusou decidir
    #: comportamento de rota por esquema.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="matriculado")


class AttendanceRecord(Base):
    """A FREQUENCIA — e `Diario` nao vira tabela.

    `02` §7 descreve o diario como "diario, frequencia, lancamento de notas": as
    notas ja sao `grades`, e o que sobra e a frequencia. Uma tabela
    `class_journals` com cabecalho por turma guardaria uma linha por turma sem
    nenhum campo que a turma ja nao tenha — a classe D4 (mesma regra escrita duas
    vezes), agora em esquema em vez de em codigo.

    `Diario` fica sendo a VISAO turma -> notas + frequencia, que e como
    `GET /classes/{class_id}/gradebook` ja o trata desde a Fase 3.
    """

    __tablename__ = "attendance_records"
    __table_args__ = (Index("ix_attendance_class", "class_id", "session_date"),)

    attendance_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    class_id: Mapped[str] = mapped_column(
        Text, ForeignKey("classes.class_id", name="fk_attendance_class"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("students.student_id", name="fk_attendance_student"),
        nullable=False,
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AcademicTranscript(Base):
    """HistoricoEscolar. **O CR nao e coluna**, e a ausencia e desenho.

    `02` §5 pede distribuicao plausivel de CR, e CR e derivado destas linhas.
    Guarda-lo seria o mesmo fato em dois lugares, com o segundo envelhecendo na
    primeira retificacao — que e exatamente o evento que este exercicio
    investiga.
    """

    __tablename__ = "academic_transcripts"
    __table_args__ = (Index("ix_transcript_student", "student_id"),)

    transcript_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    student_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("students.student_id", name="fk_transcript_student"),
        nullable=False,
    )
    subject_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("subjects.subject_id", name="fk_transcript_subject"),
        nullable=False,
    )
    semester: Mapped[str] = mapped_column(
        Text,
        ForeignKey("academic_calendar.semester", name="fk_transcript_semester"),
        nullable=False,
    )
    final_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(Text, nullable=False)


class Diploma(Base):
    """`02` §4.1 poe "emissao de diploma" entre o que a trilha registra —
    usuario, horario, campus, curso, aluno. Sem esta tabela, aquela categoria da
    trilha nasce sem objeto."""

    __tablename__ = "diplomas"

    diploma_id: Mapped[str] = mapped_column(Text, primary_key=True)
    student_id: Mapped[str] = mapped_column(
        Text, ForeignKey("students.student_id", name="fk_diploma_student"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        Text, ForeignKey("courses.course_id", name="fk_diploma_course"), nullable=False
    )
    campus: Mapped[str] = mapped_column(Text, nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    issued_by_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_diploma_issuer"), nullable=False
    )


class Scholarship(Base):
    __tablename__ = "scholarships"

    scholarship_id: Mapped[str] = mapped_column(Text, primary_key=True)
    student_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("students.student_id", name="fk_scholarship_student"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    start_semester: Mapped[str] = mapped_column(Text, nullable=False)
    end_semester: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinancingContract(Base):
    __tablename__ = "financing_contracts"

    contract_id: Mapped[str] = mapped_column(Text, primary_key=True)
    student_id: Mapped[str] = mapped_column(
        Text, ForeignKey("students.student_id", name="fk_contract_student"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    monthly_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    signed_on: Mapped[date] = mapped_column(Date, nullable=False)


class ExamQuestion(Base):
    """QuestaoVestibular. `02` §4.1: a trilha registra acesso, pesquisa,
    exportacao e impressao do banco de questoes.

    SEM ENUNCIADO REAL — `statement` guarda texto sintetico curto. `05` §3 vale
    para tudo que o seed escreve, e banco de questoes com conteudo verossimil de
    prova real seria dado que ninguem declarou sintetico.
    """

    __tablename__ = "exam_questions"

    question_id: Mapped[str] = mapped_column(Text, primary_key=True)
    knowledge_area: Mapped[str] = mapped_column(Text, nullable=False)
    exam_year: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)


class ResearchProject(Base):
    __tablename__ = "research_projects"

    project_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    principal_investigator_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_project_pi"), nullable=False
    )
    funding_agency: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_on: Mapped[date] = mapped_column(Date, nullable=False)
    end_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class HpcJob(Base):
    __tablename__ = "hpc_jobs"

    job_id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("research_projects.project_id", name="fk_job_project"),
        nullable=False,
    )
    submitted_by_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", name="fk_job_user"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cpu_hours: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)


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
#:
#: AS QUINZE ENTIDADES DA PECA 2 NAO ESTAO AQUI, e a ausencia e o mecanismo.
#: Nenhuma rota as serve, e `como_json` RECUSA tipo ausente com `TypeError` em
#: vez de serializar por reflexao. E o que faz "modelo completo" nao significar
#: "superficie completa": tabela nova nao vira resposta por existir, e o dia em
#: que uma delas precisar sair pela API alguem tera de escrever a linha aqui.
#:
#: `program` e `subject` sao PROPRIEDADE e nao coluna desde a 0003 — a chave da
#: resposta nao mudou, a fonte dela mudou. `tests/test_modelo_completo.py` fixa
#: os quatro conjuntos e fica vermelho se algum mudar.
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
