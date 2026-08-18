"""modelo completo de `02` §1: as dezoito entidades, mais o registro de delegacao

Revision ID: 0003_modelo_completo
Revises: 0002_business_state
Create Date: 2026-08-17

"MODELO COMPLETO" E MEDIDO CONTRA `02` §1, E NAO CONTRA O QUE O EXERCICIO USA
------------------------------------------------------------------------------
`07` Fase 5 poe *"modelo completo"* nos OUTPUTS sem dizer completo em relacao a
que. `02` §1 e a unica lista que a spec da, e e normativa: vinte entidades. Duas
delas NAO viram tabela, e a razao e normativa tambem — nao e corte por tamanho:

  Incidente e Declaracao  ->  `01` §4 poe Participant Actions no EVENT STORE,
                              reversibilidade "nunca". `incident_declared`,
                              `separate_incident_declared` e as acoes `declare_*`
                              de `03` §3.1 sao `event_type` do catalogo
                              (`09` §4.1). Tabela em Postgres para qualquer das
                              duas seria segunda casa do mesmo fato, e trocaria
                              "nunca reverte" por "so por reset total" sem que
                              nada acusasse. Chegam como PROJECAO, na Fase 6.

Dezoito tabelas, entao — quatro ja existem desde a 0002 e crescem aqui.

`access_delegations` FECHA LACUNA INTERNA DA SPEC, E NAO ESTENDE O MODELO
--------------------------------------------------------------------------
`02` §6.1 exige o conjunto *"Credenciais compartilhadas — 18: monitor/assistente
usando conta do professor **com registro formal de delegacao**"*. A spec pede a
coisa e nao a lista em §1: **a §1 esta incompleta em relacao a §6.1**, e esta
tabela fecha a lacuna em vez de acrescentar entidade nova.

Sem ela o conjunto e indistinguivel dos indevidos comprovados, e a Linha B perde
um dos seis que o item 5 da DoD cobra.

**Tabela, e nao campo na linha da trilha.** A delegacao existe ANTES e
INDEPENDENTEMENTE da alteracao de nota: como campo, ela viraria propriedade do
evento, repetida a cada alteracao e sem validade consultavel. O console de
investigacao da Fase 8 pergunta *"havia delegacao valida naquela data?"*, que e
consulta a fato.

E NAO E `spec-change`, pelo contraste que a propria spec oferece: `09` §4 declara
o catalogo de eventos *"registro fechado"* com todas as letras, e `02` §1 nao faz
declaracao equivalente. O projeto exige `spec-change` onde a spec FECHA.

O QUE ESTA MIGRATION NAO MUDA: NENHUMA RESPOSTA DE ROTA
--------------------------------------------------------
Esta e a propriedade que a D5 recusou entregar por efeito colateral de esquema, e
aqui ela vale por TRES razoes estruturais, e nao por conferencia:

1. **As duas unicas rotas que ESCREVEM** sao `POST /enrollment` e
   `POST /classes/{class_id}/grades`. Nenhuma FK nova cai sobre elas:
   `enrollments` ja tinha as duas FKs desde a 0002 e a rota ja confere as duas;
   `grades.student_id` continua SEM FK — e a D5, e o par rota+404+FK e da peca 3.
   Nao ha rota que escreva em `students` ou `classes`, entao FK nova ali nao tem
   como trocar 201 por erro de integridade.

2. **Coluna nova nao vaza para resposta**: `CAMPOS_PUBLICOS` e whitelist, e o que
   nao esta la nao sai. `status` e `entry_semester` nascem invisiveis.

3. **`program` e `subject` mudam de FONTE e nao de CHAVE.** As duas eram texto
   livre e passam a vir de `courses.name` e `subjects.name` por relacao; a
   resposta continua trazendo `program` e `subject` com o mesmo valor. O par que
   anuncia esta em `tests/test_modelo_completo.py`: ele fixa os conjuntos de
   chaves das quatro respostas da Fase 3, e fica VERMELHO se alguma mudar.

ELA RECUSA SOBRE TABELA COM DADO, E ESCREVER O BACKFILL E QUE MOSTROU POR QUE
------------------------------------------------------------------------------
A primeira versao desta migration fazia backfill: `students.program` viraria um
curso por valor distinto ja gravado, com o proprio texto como nome — honesto, e
sem informacao nova. **Duas das tres ligacoes nao sao deriveis, e isso so aparece
ao escrever a terceira:**

  classes.professor_id -> professors   `professors.name` NAO ESTA em lugar nenhum;
                                       `classes` guarda so o identificador
  classes.semester     -> academic_calendar   as ONZE DATAS do semestre — inicio
                                       e fim de aulas, janela de lancamento,
                                       **janela de retificacao**, matricula,
                                       colacao, vestibular — nao existem no dado
                                       antigo, e sao exatamente o que `02` §2 diz
                                       que torna a Linha B detectavel

Backfill que inventa nome de professor ou janela de retificacao produz dado
plausivel e falso — e `within_window` calculado contra uma janela inventada e a
camada 2 mentindo sobre a camada 1, que e o mesmo argumento da P4-5.

**Entao a migration RECUSA quando `students` ou `classes` tem linha**, com a
instrucao no proprio erro. Uma regra em vez de tres backfills desiguais, e ela e
verdadeira: **nao existe dado de producao neste projeto**. O que ha em `students`
e `classes` e a fixture de demonstracao de seis linhas, que `demonstracao.py`
recarrega, e o dataset de verdade e o da peca 4.

LIMITE DECLARADO, com a condicao que o encerra: isto vale enquanto nao houver
exercicio com dado de participante gravado. No primeiro que houver, migration
tera de MIGRAR, e recusar deixa de ser aceitavel. `courses.campus` continua
nullable pelo motivo vizinho — o campus nao esta no dado antigo, e o seed da peca
4 e quem escreve os cinco de `02`.

O QUE CONTINUA FORA, e contra qual fase vizinha
-------------------------------------------------
Ecossistema externo de `02` §8 e os dois simuladores de §7 -> Fase 11.
Telemetria de `02` §10 -> Fase 9. Modo "Prova em andamento", console de
investigacao e acoes de continuidade de §9 -> Fase 8. `audit_trail` e de `02` §4
e nasce na peca 3, com role, trigger e cadeia de hash. Regra de negocio sobre o
dado — nota valida, matricula unica, pre-requisito — nao e modelo, e continua
fora pelo mesmo argumento da 0002: migration nao e o lugar de decidir
comportamento de rota.

IDIOMA — tabelas e colunas em ingles (`CLAUDE.md` §Idioma). Os VALORES de papel e
de situacao (`aluno`, `ativo`, `matriculado`, `aprovado`) seguem em portugues:
sao vocabulario de persona e de negocio, que `03` §6 e §7 escrevem assim, e nao
identificador.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_modelo_completo"
down_revision = "0002_business_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- A RECUSA, ANTES DE QUALQUER DDL -------------------------------------
    #
    # Ver o cabecalho: nome de professor e as onze datas do semestre nao existem
    # no dado antigo, e inventa-los produziria `within_window` calculado contra
    # janela que ninguem declarou. Recusa alta, e nunca meia-migracao.
    op.execute(
        """
        DO $$
        DECLARE
            alunos integer;
            turmas integer;
        BEGIN
            SELECT count(*) INTO alunos FROM students;
            SELECT count(*) INTO turmas FROM classes;
            IF alunos > 0 OR turmas > 0 THEN
                RAISE EXCEPTION
                    'a 0003 recusa: % aluno(s) e % turma(s) gravados. Esta '
                    'migration liga `classes` a `professors` e a '
                    '`academic_calendar`, e nem o nome do professor nem as onze '
                    'datas do semestre existem no dado antigo — backfill aqui '
                    'inventaria a janela de retificacao. O que ha nessas tabelas '
                    'e a fixture de demonstracao, que se recarrega: '
                    'TRUNCATE enrollments, grades, classes, students RESTART '
                    'IDENTITY; depois `alembic upgrade head` e '
                    '`demonstracao.carregar(engine)`.',
                    alunos, turmas;
            END IF;
        END $$
        """
    )

    # -- CalendarioAcademico: `02` §2, e sem ela a Linha B nao e detectavel -----
    #
    # A CHAVE E O PROPRIO SEMESTRE (`2026.2`), e isso e o que mantem
    # `classes.semester` intacta: a coluna que ja existe ganha FK sem mudar de
    # tipo, de valor nem de nome. Chave substituta aqui obrigaria a reescrever a
    # coluna da resposta, que e exatamente o que esta peca nao faz.
    op.create_table(
        "academic_calendar",
        sa.Column("semester", sa.Text(), primary_key=True),
        sa.Column("classes_start", sa.Date(), nullable=False),
        sa.Column("classes_end", sa.Date(), nullable=False),
        sa.Column("grade_entry_start", sa.Date(), nullable=False),
        sa.Column("grade_entry_end", sa.Date(), nullable=False),
        # A JANELA DE RETIFICACAO. `02` §2 a nomeia em negrito, e ela e o que
        # `within_window` compara no momento da gravacao (`02` §4.1).
        sa.Column("rectification_start", sa.Date(), nullable=False),
        sa.Column("rectification_end", sa.Date(), nullable=False),
        sa.Column("enrollment_start", sa.Date(), nullable=False),
        sa.Column("enrollment_end", sa.Date(), nullable=False),
        sa.Column("graduation_date", sa.Date(), nullable=False),
        sa.Column("admission_exam_start", sa.Date(), nullable=False),
        sa.Column("admission_exam_end", sa.Date(), nullable=False),
    )

    # -- Usuario: `02` §1, e o sujeito de tudo que a trilha registra -----------
    #
    # `password_hash`, nunca senha. `05` §8: senha de seed e derivada do
    # `RANDOM_SEED` e impressa apenas no log de seed local.
    #
    # `role` admite `servico` alem dos quatro papeis de dominio de
    # `api_surface.yaml`: `svc_migration` de `02` §6.1 e conta de servico, e
    # conta de servico nao faz login. A lista fechada que `emitir_token` le
    # continua sendo a do YAML, e este valor nao entra la.
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "courses",
        sa.Column("course_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("degree_level", sa.Text(), nullable=True),
        # NULLABLE por causa do backfill — ver o cabecalho. Inventar campus aqui
        # seria migration afirmando fato que ninguem declarou.
        sa.Column("campus", sa.Text(), nullable=True),
    )

    op.create_table(
        "professors",
        sa.Column("professor_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        # A CONTA DOCENTE. `02` §6.1 abre os indevidos comprovados com "conta
        # docente unica": sem esta ligacao, "quem alterou" e "de quem e a conta"
        # sao dois textos que ninguem consegue cruzar.
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_professors_user"),
            nullable=True,
        ),
        sa.Column("department", sa.Text(), nullable=True),
    )

    op.create_table(
        "subjects",
        sa.Column("subject_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "course_id",
            sa.Text(),
            sa.ForeignKey("courses.course_id", name="fk_subjects_course"),
            nullable=False,
        ),
        sa.Column("credits", sa.Integer(), nullable=True),
    )

    # -- AutorizacaoRetificacao: `02` §3 --------------------------------------
    #
    # Os CINCO campos que a secao nomeia, e nada alem: solicitante, coordenador
    # aprovador, justificativa, numero de processo, data. A ligacao com a
    # alteracao de nota e feita pela TRILHA (`authorization_id` em `02` §4.1),
    # que nasce na peca 3 — poe-la aqui seria a trilha antes da trilha.
    #
    # Sem esta entidade, "fora da janela = fraude" e o exercicio vira busca por
    # `WHERE within_window = false`. E o que `02` §3 diz com todas as letras.
    op.create_table(
        "rectification_authorizations",
        sa.Column("authorization_id", sa.Text(), primary_key=True),
        sa.Column(
            "requester_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_rectauth_requester"),
            nullable=False,
        ),
        sa.Column(
            "approver_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_rectauth_approver"),
            nullable=False,
        ),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("process_number", sa.Text(), nullable=False, unique=True),
        sa.Column("authorized_on", sa.Date(), nullable=False),
    )

    # -- access_delegations: a lacuna de `02` §1 em relacao a §6.1 -------------
    op.create_table(
        "access_delegations",
        sa.Column("delegation_id", sa.Text(), primary_key=True),
        # QUEM EMPRESTA e QUEM USA. Os dois sao conta: o conjunto de `02` §6.1 e
        # "monitor usando a conta do professor", e o que a trilha vai registrar
        # e a conta do professor.
        sa.Column(
            "delegating_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_delegation_delegating"),
            nullable=False,
        ),
        sa.Column(
            "delegate_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_delegation_delegate"),
            nullable=False,
        ),
        # O "REGISTRO FORMAL" DE `02` §6.1. Sem numero de processo e sem
        # validade, a delegacao seria indistinguivel de afirmacao retroativa —
        # e o conjunto inteiro existe para ser distinguivel dos indevidos.
        sa.Column("process_number", sa.Text(), nullable=False, unique=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )
    # A CONSULTA DA FASE 8 e "havia delegacao valida naquela data, para esta
    # conta?". Sem indice, ela varre a tabela — `01` §7 proibe varredura em rota
    # de tempo real, e o console de investigacao e rota de exercicio.
    op.create_index(
        "ix_delegations_delegating",
        "access_delegations",
        ["delegating_user_id", "valid_from", "valid_until"],
    )

    # -- as quatro da 0002 crescem --------------------------------------------
    #
    # `students.program` (texto livre) -> `students.course_id`. A resposta
    # continua trazendo `program`: o modelo o expoe por relacao. Ver o cabecalho.
    op.add_column(
        "students",
        sa.Column(
            "course_id",
            sa.Text(),
            sa.ForeignKey("courses.course_id", name="fk_students_course"),
            nullable=False,
        ),
    )
    op.drop_column("students", "program")

    # `status` e `entry_semester` NASCEM INVISIVEIS: nao estao em
    # `CAMPOS_PUBLICOS`, entao nenhuma resposta muda por eles existirem. `02` §5
    # pede distribuicao plausivel de evasao, e evasao e situacao do aluno.
    op.add_column(
        "students",
        sa.Column("status", sa.Text(), nullable=False, server_default="ativo"),
    )
    op.add_column(
        "students",
        sa.Column(
            "entry_semester",
            sa.Text(),
            sa.ForeignKey("academic_calendar.semester", name="fk_students_entry"),
            nullable=True,
        ),
    )

    # `classes.subject` (texto livre) -> `classes.subject_id`, mesma forma.
    op.add_column(
        "classes",
        sa.Column(
            "subject_id",
            sa.Text(),
            sa.ForeignKey("subjects.subject_id", name="fk_classes_subject"),
            nullable=False,
        ),
    )
    op.drop_column("classes", "subject")

    # `semester` NAO MUDA — mesma coluna, mesmo tipo, mesmo valor. Ganha FK
    # porque agora existe a tabela que a 0002 nao tinha. Nenhuma rota escreve em
    # `classes`, entao a FK nao tem como trocar 201 por erro de integridade.
    op.create_foreign_key(
        "fk_classes_semester",
        "classes",
        "academic_calendar",
        ["semester"],
        ["semester"],
    )
    # `professor_id` idem: a 0002 o deixou sem FK porque `professors` nao existia,
    # e disse isso no comentario. Existe agora.
    op.create_foreign_key(
        "fk_classes_professor", "classes", "professors", ["professor_id"], ["professor_id"]
    )

    op.add_column(
        "enrollments",
        sa.Column("status", sa.Text(), nullable=False, server_default="matriculado"),
    )

    # -- as demais entidades de `02` §1 ---------------------------------------
    #
    # DIARIO NAO VIRA TABELA. `02` §7 o descreve como "diario, frequencia,
    # lancamento de notas": as notas ja sao `grades`, e o que ele tem e nenhuma
    # outra entidade guarda e a FREQUENCIA. Uma tabela `class_journals` com
    # cabecalho por turma guardaria uma linha por turma sem nenhum campo que a
    # turma ja nao tenha — e a classe D4 (mesma regra escrita duas vezes), agora
    # em esquema em vez de em codigo. `Diario` fica sendo a VISAO turma -> notas
    # + frequencia, que e como `GET /classes/{class_id}/gradebook` ja o trata.
    op.create_table(
        "attendance_records",
        sa.Column("attendance_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "class_id",
            sa.Text(),
            sa.ForeignKey("classes.class_id", name="fk_attendance_class"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_attendance_student"),
            nullable=False,
        ),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("present", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_attendance_class", "attendance_records", ["class_id", "session_date"]
    )

    # HistoricoEscolar. O CR NAO E COLUNA: `02` §5 pede distribuicao plausivel de
    # CR, e CR e derivado destas linhas. Guarda-lo seria o mesmo fato em dois
    # lugares, com o segundo envelhecendo na primeira retificacao — que e
    # exatamente o evento que este exercicio investiga.
    op.create_table(
        "academic_transcripts",
        sa.Column("transcript_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_transcript_student"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Text(),
            sa.ForeignKey("subjects.subject_id", name="fk_transcript_subject"),
            nullable=False,
        ),
        sa.Column(
            "semester",
            sa.Text(),
            sa.ForeignKey("academic_calendar.semester", name="fk_transcript_semester"),
            nullable=False,
        ),
        sa.Column("final_grade", sa.Float(), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
    )
    op.create_index("ix_transcript_student", "academic_transcripts", ["student_id"])

    # Diploma. `02` §4.1 poe "emissao de diploma" entre o que a trilha registra:
    # usuario, horario, campus, curso, aluno. Sem esta tabela, aquela categoria
    # da trilha nasce sem objeto.
    op.create_table(
        "diplomas",
        sa.Column("diploma_id", sa.Text(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_diploma_student"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Text(),
            sa.ForeignKey("courses.course_id", name="fk_diploma_course"),
            nullable=False,
        ),
        sa.Column("campus", sa.Text(), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column(
            "issued_by_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_diploma_issuer"),
            nullable=False,
        ),
    )

    op.create_table(
        "scholarships",
        sa.Column("scholarship_id", sa.Text(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_scholarship_student"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("percentage", sa.Integer(), nullable=False),
        sa.Column("start_semester", sa.Text(), nullable=False),
        sa.Column("end_semester", sa.Text(), nullable=True),
    )

    op.create_table(
        "financing_contracts",
        sa.Column("contract_id", sa.Text(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_contract_student"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("monthly_amount", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("signed_on", sa.Date(), nullable=False),
    )

    # QuestaoVestibular. `02` §4.1: a trilha registra acesso, pesquisa,
    # exportacao e impressao do banco de questoes.
    #
    # SEM ENUNCIADO REAL. O campo guarda texto sintetico curto; `05` §3 vale para
    # tudo que o seed escreve, e banco de questoes com conteudo verossimil de
    # prova real seria dado que ninguem declarou sintetico.
    op.create_table(
        "exam_questions",
        sa.Column("question_id", sa.Text(), primary_key=True),
        sa.Column("knowledge_area", sa.Text(), nullable=False),
        sa.Column("exam_year", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_projects",
        sa.Column("project_id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "principal_investigator_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_project_pi"),
            nullable=False,
        ),
        sa.Column("funding_agency", sa.Text(), nullable=True),
        sa.Column("start_on", sa.Date(), nullable=False),
        sa.Column("end_on", sa.Date(), nullable=True),
    )

    op.create_table(
        "hpc_jobs",
        sa.Column("job_id", sa.Text(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Text(),
            sa.ForeignKey("research_projects.project_id", name="fk_job_project"),
            nullable=False,
        ),
        sa.Column(
            "submitted_by_user_id",
            sa.Text(),
            sa.ForeignKey("users.user_id", name="fk_job_user"),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_hours", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    # ORDEM INVERSA DA CRIACAO, por causa das FKs — o mesmo cuidado da 0002.
    op.drop_table("hpc_jobs")
    op.drop_table("research_projects")
    op.drop_table("exam_questions")
    op.drop_table("financing_contracts")
    op.drop_table("scholarships")
    op.drop_table("diplomas")
    op.drop_index("ix_transcript_student", table_name="academic_transcripts")
    op.drop_table("academic_transcripts")
    op.drop_index("ix_attendance_class", table_name="attendance_records")
    op.drop_table("attendance_records")

    op.drop_column("enrollments", "status")

    # A VOLTA DE `classes.subject` E `students.program` RESTAURA O TEXTO, e nao a
    # coluna vazia: sem isto, descer a migration deixaria a aplicacao da 0002 com
    # `NOT NULL` sem valor, e o downgrade seria irreversivel na pratica.
    op.add_column("classes", sa.Column("subject", sa.Text(), nullable=True))
    op.execute(
        "UPDATE classes SET subject = subjects.name "
        "FROM subjects WHERE classes.subject_id = subjects.subject_id"
    )
    op.alter_column("classes", "subject", nullable=False)
    op.drop_constraint("fk_classes_professor", "classes", type_="foreignkey")
    op.drop_constraint("fk_classes_semester", "classes", type_="foreignkey")
    op.drop_constraint("fk_classes_subject", "classes", type_="foreignkey")
    op.drop_column("classes", "subject_id")

    op.drop_column("students", "entry_semester")
    op.drop_column("students", "status")
    op.add_column("students", sa.Column("program", sa.Text(), nullable=True))
    op.execute(
        "UPDATE students SET program = courses.name "
        "FROM courses WHERE students.course_id = courses.course_id"
    )
    op.alter_column("students", "program", nullable=False)
    op.drop_constraint("fk_students_course", "students", type_="foreignkey")
    op.drop_column("students", "course_id")

    op.drop_index("ix_delegations_delegating", table_name="access_delegations")
    op.drop_table("access_delegations")
    op.drop_table("rectification_authorizations")
    op.drop_table("subjects")
    op.drop_table("professors")
    op.drop_table("courses")
    op.drop_table("users")
    op.drop_table("academic_calendar")
