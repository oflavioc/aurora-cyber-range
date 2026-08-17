"""business state em Postgres: students, classes, grades, enrollments

Revision ID: 0002_business_state
Revises: 0001_event_store
Create Date: 2026-08-16

A P3-5. Ate aqui o business state eram QUATRO DICIONARIOS DE MODULO —
`ALUNOS`, `TURMAS`, `NOTAS`, `MATRICULAS` —, e `01` §4 poe Business State em
Postgres com a linha *"nao reversivel por rollback; so por reset total"*. Essa
linha e falsa enquanto o dado mora em memoria: reinicio nao e reset total, e
reiniciava tudo do mesmo jeito.

QUATRO TABELAS, E A D8 DIZIA TRES
----------------------------------
A D8 escreveu *"as tres tabelas"* lendo as tres entidades que `07` Fase 3
nomeia — Aluno, Turma, Nota. A pendencia P3-5 nomeia **quatro** dicionarios de
modulo, e `MATRICULAS` e um deles: deixa-lo em memoria fecharia tres quartos da
pendencia e manteria o defeito no caminho do item 1 da DoD, que e justamente
`POST /enrollment`.

O QUE ESTA MIGRATION NAO FAZ, e cada ausencia tem motivo
---------------------------------------------------------
**Nao insere dado.** Os seis registros de demonstracao entram por
`domains/academus/seed/demonstracao.py`, que se chama assim para nao ser
confundido com o seed em escala da Fase 5 (`06` T8). Migration que insere dado
de demonstracao e historico que mente: ela afirma que aquelas linhas fazem parte
do esquema.

**Nao ha `REVOKE`, role `INSERT`-only nem trigger.** Isso e `02` §4 e `05` §7,
entregue na Fase 5, e vale para a `audit_trail` — que nao e nenhuma destas
quatro.

**Nao ha unicidade em `enrollments`.** Hoje `POST /enrollment` duas vezes grava
duas linhas, e uma chave composta faria a segunda virar erro. Isso e regra de
negocio — "matricula duplicada e recusada" —, e `registros.py` ja declarava
regra de nota fora do escopo da fase pelo mesmo argumento. Migration nao e o
lugar de decidir comportamento de rota.

**A chave substituta de `grades` e `enrollments` pode ter buracos, e aqui isso
nao importa.** O event store recusou `BIGSERIAL` porque buraco na sequencia dele
seria alarme falso — a sequencia E a contagem, e a cadeia de hash a usa. Nota e
matricula nao tem cadeia, nao tem contagem que dependa de contiguidade, e nada
le a chave delas: e identidade de linha, e nada mais.

AS CHAVES ESTRANGEIRAS ESTAO ONDE A ROTA JA GARANTE A RELACAO
---------------------------------------------------------------
`grades.class_id`, `enrollments.student_id` e `enrollments.class_id` tem FK
porque os tres caminhos ja falham antes de escrever quando o alvo nao existe:
`lancar_nota` passa pela turma, `matricular` passa pelo aluno e confere a turma.
A FK ali nao muda comportamento nenhum — ela documenta no esquema o que o codigo
ja faz.

`grades.student_id` **nao tem FK**, e a assimetria e deliberada: a rota nao
confere se o aluno existe. Por FK ali, `POST /classes/{class_id}/grades` com
`student_id` inventado passaria de 201 a erro de integridade — mudanca de
comportamento de uma rota que a Fase 3 entregou e auditou, entrando por efeito
colateral de migration. A ausencia esta nomeada e virou a **P4-5**, com destino
na Fase 5, que e dona da trilha de `02` §4.1 — e a trilha de alteracao de nota
registra o aluno.

IDIOMA — P4-1
-------------
Tabelas e colunas em ingles, `CLAUDE.md` §Idioma. Os valores de papel
(`aluno`, `professor`, `secretaria`, `financeiro`) continuam em portugues: sao
vocabulario de persona, que `03` §6 e §7 escrevem assim, e nao identificador.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_business_state"
down_revision = "0001_event_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("student_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        # `program` e nao `course`: o valor e o curso de graduacao do aluno, e
        # `Curso` e entidade propria em `02` §1 — usar `course` para um campo de
        # texto livre colidiria com a tabela que a Fase 5 vai criar.
        sa.Column("program", sa.Text(), nullable=False),
    )

    op.create_table(
        "classes",
        sa.Column("class_id", sa.Text(), primary_key=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("semester", sa.Text(), nullable=False),
        # O DONO. E o que a regra `titular` compara com o `sub` do token (P3-3).
        # Sem FK para uma tabela de professores porque ela nao existe: `07` Fase 3
        # nomeia tres entidades, e Professor nao e uma delas.
        sa.Column("professor_id", sa.Text(), nullable=False),
    )

    op.create_table(
        "grades",
        sa.Column("grade_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Text(), nullable=False),
        sa.Column(
            "class_id",
            sa.Text(),
            sa.ForeignKey("classes.class_id", name="fk_grades_class"),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
    )
    # A leitura do diario e `WHERE class_id = ...`, e ela e rota de exercicio.
    # `01` §7 proibe varredura em rota de tempo real; sem indice, `grades` seria
    # varrida inteira a cada leitura de diario.
    op.create_index("ix_grades_class_id", "grades", ["class_id"])

    op.create_table(
        "enrollments",
        sa.Column("enrollment_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.student_id", name="fk_enrollments_student"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Text(),
            sa.ForeignKey("classes.class_id", name="fk_enrollments_class"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # ORDEM INVERSA DA CRIACAO, por causa das FKs: derrubar `classes` antes de
    # `grades` deixaria a referencia pendurada e o Postgres recusaria.
    op.drop_table("enrollments")
    op.drop_index("ix_grades_class_id", table_name="grades")
    op.drop_table("grades")
    op.drop_table("classes")
    op.drop_table("students")
