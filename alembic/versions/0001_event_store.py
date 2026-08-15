"""event store append-only, com sequencia e encadeamento por hash

Revision ID: 0001_event_store
Revises:
Create Date: 2026-08-15

PRIMEIRA MIGRATION DO PROJETO. A Fase 1 deixou o Alembic executavel e sem
nenhuma revisao — P1-9. Esta e a tabela do event store.

AS MARCAS TEMPORAIS SAO `text`, E NAO `timestamptz`
---------------------------------------------------
O envelope de `09` §1.1 as declara como string, e `exercise_time` nem e
timestamp: e o rotulo `T+HH:MM:SS`. Converter na escrita e reconverter na leitura
produziria um valor diferente do que foi HASHEADO, e a cadeia quebraria por
formatacao — deteccao que grita sem defeito.

Guardar exatamente o que o contrato define, e exatamente o que foi assinado.

`correlation` E `payload` SAO `jsonb`
--------------------------------------
`payload` e aberto por contrato ate os schemas por `event_type` chegarem, e
`jsonb` guarda isso sem inventar colunas. A forma canonica que o hash cobre e
serializada pela aplicacao, entao a normalizacao que o `jsonb` faz na escrita
nao afeta a verificacao.

O QUE ESTA MIGRATION NAO FAZ, DE PROPOSITO
-------------------------------------------
Nao ha `REVOKE UPDATE/DELETE`, nem role `INSERT`-only, nem trigger de bloqueio.
Isso e `02_DOMAIN_ACADEMUS.md` §4 e `05_SECURITY_REQUIREMENTS.md` §7, entregue na
FASE 5, e antecipar seria duplicar mecanismo em dois lugares.

O que esta fase entrega e DETECCAO — `sequence` e o par de hashes —, que torna a
ausencia da prevencao visivel em vez de silenciosa, e que continua util depois do
`REVOKE`, porque `REVOKE` nao protege contra quem tem privilegio.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_event_store"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_store",
        # Atribuida pela APLICACAO, e nao `BIGSERIAL`: sequencia de banco consome
        # numero em transacao que faz rollback, e o buraco seria alarme falso.
        sa.Column("sequence", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("event_id", sa.Text(), nullable=False, unique=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("truth_layer", sa.Text(), nullable=False),
        sa.Column("producer", sa.Text(), nullable=False),
        sa.Column("exercise_time", sa.Text(), nullable=False),
        sa.Column("exercise_timestamp", sa.Text(), nullable=False),
        sa.Column("wall_timestamp", sa.Text(), nullable=False),
        sa.Column("clock_multiplier", sa.Float(), nullable=False),
        sa.Column("simulation_epoch", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=True),
        sa.Column("persona", sa.Text(), nullable=True),
        sa.Column("correlation", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.Text(), nullable=False),
        sa.Column("row_hash", sa.Text(), nullable=False, unique=True),
        # A epoch comeca em ZERO (`06` T3), e negativa nao existe: nao ha linha
        # temporal anterior a primeira. Mesmo piso do contrato.
        sa.CheckConstraint("simulation_epoch >= 0", name="ck_event_store_epoch_nao_negativa"),
        sa.CheckConstraint("sequence >= 1", name="ck_event_store_sequencia_positiva"),
    )


def downgrade() -> None:
    # `downgrade` existe porque Alembic o espera, e DERRUBA A TABELA INTEIRA.
    #
    # Nao ha como "desfazer" um event store parcialmente: `00_MASTER_SPEC.md`
    # §5.5 diz que nada e removido, e migration que apagasse linhas seria
    # exatamente a reescrita de historia que a cadeia de hash existe para
    # detectar. Ou a tabela existe inteira, ou nao existe.
    op.drop_table("event_store")
