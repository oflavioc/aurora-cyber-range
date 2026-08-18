"""trilha de auditoria: tabela dedicada, role INSERT-only, REVOKE, trigger e cadeia

Revision ID: 0004_trilha_de_auditoria
Revises: 0003_modelo_completo
Create Date: 2026-08-17

`02` §4 — "Append-only e imutavel" EXIGE IMPLEMENTACAO
-------------------------------------------------------
*"PostgreSQL nao garante nada por si."* Os seis obrigatorios da secao, e o que
esta migration entrega de cada um:

  1. tabela dedicada `audit_trail`, separada das operacionais    -> aqui
  2. role `academus_app` com INSERT apenas; REVOKE UPDATE/DELETE/TRUNCATE -> aqui
  3. trigger BEFORE UPDATE OR DELETE que levanta excecao         -> aqui
  4. prev_hash e row_hash = SHA256(prev_hash || payload canonico) -> colunas aqui,
     calculo em `domains/academus/audit/trilha.py` com a primitiva do core
  5. GET /audit/verify-chain, primeira quebra                    -> a rota
  6. migration controlada                                        -> esta

O QUE `REVOKE` E TRIGGER NAO PROTEGEM — e isto precisa estar aqui, e nao so no
registro, porque e aqui que alguem le "REVOKE" e conclui "imutavel"
--------------------------------------------------------------------------------
`REVOKE` nao alcanca quem nao passa pela role: **superusuario e DONO da tabela**.
O dono re-concede privilegio a si mesmo e pode `ALTER TABLE ... DISABLE TRIGGER`;
um superusuario pode ainda `SET session_replication_role = replica`, e o trigger
nao dispara. Nada disso e defeito da implementacao — e o que privilegio de dono
significa.

A divisao entre os dois mecanismos:

  REVOKE + trigger  PREVENCAO no caminho normal — a aplicacao, e quem tem a
                    credencial dela. Nao cobre dono nem superusuario.
  cadeia de hash    DETECCAO de quem reescreveu e NAO recomputou a cadeia:
                    acidente, migracao malfeita, edicao manual, restauracao de
                    backup. Nao cobre truncamento da cauda, nem adversario com
                    privilegio E o codigo.

`REVOKE` sem cadeia deixa o caminho privilegiado sem testemunha; cadeia sem
`REVOKE` deixa o caminho normal sem impedimento. `02` §4 exige os dois.

A SEQUENCIA E DA APLICACAO, E NAO `BIGSERIAL` — D12
----------------------------------------------------
Mesma escolha do event store, por um argumento que aqui e mais forte:

  1. a cadeia JA obriga a serializar — `previous_hash` e o `row_hash` da linha
     imediatamente anterior, entao escrever exige ler a ultima sob trava. A
     sequencia da aplicacao sai de graca dessa trava; `BIGSERIAL` teria trava
     **e** buraco;
  2. com `REVOKE DELETE`, buraco deixa de ter explicacao legitima — e a
     contiguidade passa de ruido tolerado a SINAL;
  3. `BIGSERIAL` exigiria `USAGE` na sequencia para a role restrita: uma
     permissao a mais numa role cujo proposito e ter o minimo.

OS CAMPOS SAO OS DE `02` §4.1, e `event_id` NAO E UM DELES
-----------------------------------------------------------
A trilha nao e o event store. `01` §4 poe as duas em camadas diferentes — trilha
de auditoria e artefato de NEGOCIO, investigavel pela equipe azul; event store e
a maquina de exercicio. Misturar as duas poria `truth_layer` numa tabela de
dominio, e o adapter passaria a conhecer o modelo das quatro verdades.

`payload` guarda o que a categoria exige, e o `category` diz qual e. As cinco de
`02` §4.1: alteracao de nota, emissao de diploma, banco de questoes, pesquisa
academica e declaracoes do exercicio. **A quinta nao tem produtor ate a Fase 6** —
e a P5-2, declarada com destinatario em vez de esquecida.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_trilha_de_auditoria"
down_revision = "0003_modelo_completo"
branch_labels = None
depends_on = None

#: A ROLE DA APLICACAO. `02` §4 a nomeia literalmente.
ROLE = "academus_app"


def upgrade() -> None:
    op.create_table(
        "audit_trail",
        # SEM `autoincrement`: a sequencia e atribuida pela aplicacao (D12).
        sa.Column("sequence", sa.BigInteger(), primary_key=True, autoincrement=False),
        # A CATEGORIA de `02` §4.1. Texto e nao enum: enum no Postgres exige
        # migration para acrescentar valor, e a quinta categoria ganha produtor
        # na Fase 6 — o custo cairia la, sem motivo.
        sa.Column("category", sa.Text(), nullable=False),
        # QUEM, DE ONDE, COM O QUE. `02` §4.1 exige usuario, IP e user-agent para
        # alteracao de nota, e os tres sao o que separa os conjuntos da Linha B:
        # conta docente unica, IP de laboratorio compartilhado.
        # SEM FK, E A ASSIMETRIA COM A P4-5 E DELIBERADA.
        #
        # A P4-5 pos FK no OBJETO — `grades.student_id` — porque trilha que
        # registra aluno inexistente e a camada 2 mentindo sobre a camada 1, e ali
        # a rota confere antes de escrever.
        #
        # O ATOR e outra coisa: ele vem do `sub` de um token ASSINADO, e a trilha
        # registra quem agiu COMO SE APRESENTOU. Com FK, um token valido para uma
        # conta ausente de `users` faria a escrita da trilha falhar — e, como a
        # trilha e a mesma transacao do fato (D4), a operacao de negocio inteira
        # cairia. Trilha que RECUSA REGISTRAR por integridade referencial e pior
        # que trilha que registra ator desconhecido: a primeira nao deixa rastro
        # nenhum, e e justamente o caso em que o rastro importa mais.
        #
        # O cruzamento com `users` que a Linha B precisa — "conta docente unica"
        # de `02` §6.1 — e feito por VALOR na consulta, e nao por constraint.
        sa.Column("actor_user_id", sa.Text(), nullable=False),
        sa.Column("source_ip", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        # TIMESTAMP DUPLO — `02` §4.1. `occurred_at` e o relogio de parede do
        # fato; `recorded_at` e quando a linha entrou. Iguais no caminho normal,
        # e diferentes em carga retroativa — que e exatamente o que o exercicio
        # investiga.
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        # O OBJETO. Generico de proposito: `grade`, `diploma`, `exam_question`,
        # `research_project`. Duas colunas em vez de uma FK por categoria —
        # cinco FKs opcionais deixariam quatro nulas em toda linha.
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Text(), nullable=False),
        # O QUE MUDOU, e o resto do que `02` §4.1 pede por categoria — nota
        # anterior, nova nota, semestre, disciplina.
        sa.Column("payload", sa.JSON(), nullable=False),
        # A JANELA — `02` §2: "toda alteracao de nota calcula `within_window`
        # contra ela NO MOMENTO DA GRAVACAO". Calculado e gravado, e nao
        # derivado na leitura: o calendario pode ser corrigido depois, e a
        # trilha tem de dizer o que valia quando o fato ocorreu.
        sa.Column("within_window", sa.Boolean(), nullable=True),
        # NULO QUANDO NAO HOUVER — `02` §4.1, literal. E o campo que separa
        # "fora da janela" de "fraude": sem ele, o exercicio vira busca por
        # `WHERE within_window = false` (`02` §3).
        sa.Column(
            "authorization_id",
            sa.Text(),
            sa.ForeignKey(
                "rectification_authorizations.authorization_id",
                name="fk_audit_authorization",
            ),
            nullable=True,
        ),
        sa.Column("previous_hash", sa.Text(), nullable=False),
        sa.Column("row_hash", sa.Text(), nullable=False, unique=True),
        sa.CheckConstraint("sequence >= 1", name="ck_audit_sequencia_positiva"),
    )
    # A CONSULTA DA FASE 6 e por PERIODO — `07` Fase 6, item 1 da DoD. O indice
    # nasce aqui para que aquela fase acrescente a emissao do evento e nao
    # precise reabrir o esquema. `01` §7 proibe varredura em rota de exercicio.
    op.create_index("ix_audit_occurred_at", "audit_trail", ["occurred_at"])
    op.create_index("ix_audit_actor", "audit_trail", ["actor_user_id", "occurred_at"])

    # -- A P4-5 FECHA AQUI, e o gatilho declarado dela era este commit --------
    #
    # `grades.student_id` nasceu sem FK na 0002, e a ausencia foi NOMEADA: a rota
    # nao conferia se o aluno existia, entao FK ali teria trocado 201 por erro de
    # integridade — mudanca de comportamento entrando por efeito colateral de
    # migration. A pendencia datou o vencimento para "o commit em que a trilha
    # nascer", e o motivo e este arquivo: a trilha registra O ALUNO da alteracao,
    # e trilha que registra aluno inexistente e a camada 2 produzindo evidencia
    # plausivel e falsa sobre a camada 1.
    #
    # A FK VEM ACOMPANHADA, e nao sozinha: `repositorio.lancar_nota` passou a
    # conferir o aluno e a responder 404, como ja respondia para turma. E o mesmo
    # criterio pelo qual as outras tres FKs existem desde a 0002 — "a FK
    # documenta no esquema o que a rota ja faz".
    op.create_foreign_key(
        "fk_grades_student", "grades", "students", ["student_id"], ["student_id"]
    )

    # -- 2. a role, e o REVOKE ------------------------------------------------
    #
    # SEM `LOGIN` e sem senha. A separacao definitiva — credencial propria para a
    # `academus-api` — exige variavel no `.env`, e isso e do operador. O que esta
    # role torna possivel HOJE e `SET LOCAL ROLE`: a escrita da trilha assume a
    # role dentro da transacao, e a restricao passa a valer no caminho da
    # aplicacao sem credencial nova. O limite — `RESET ROLE` esta a um comando —
    # esta declarado na D13 e na pendencia.
    #
    # `IF NOT EXISTS` nao existe para `CREATE ROLE` em todas as versoes: o `DO`
    # confere antes. Role e objeto de CLUSTER, e nao de base — duas bases do
    # mesmo cluster compartilham esta.
    #
    # QUEM RODA A MIGRATION PRECISA DE `CREATEROLE` — ou a role precisa JA
    # EXISTIR. Medido: com uma role de migration sem esse atributo, o
    # `CREATE ROLE` falha com "Only roles with the CREATEROLE attribute may
    # create roles", e a mensagem nao diz o que fazer. A saida esta no proprio
    # erro: um DBA cria a role uma vez, e a partir dai o `IF NOT EXISTS` a
    # encontra e a migration roda com privilegio minimo.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
                BEGIN
                    CREATE ROLE {ROLE} NOLOGIN;
                EXCEPTION WHEN insufficient_privilege THEN
                    RAISE EXCEPTION
                        'a 0004 precisa criar a role `{ROLE}` (02_DOMAIN_ACADEMUS '
                        'secao 4 item 2) e quem roda esta migration nao tem '
                        'CREATEROLE. Duas saidas: rodar a migration com uma role '
                        'que tenha CREATEROLE, ou criar a role UMA VEZ como '
                        'superusuario — CREATE ROLE {ROLE} NOLOGIN; — e repetir. '
                        'A migration nao segue sem ela: trilha sem role restrita '
                        'e append-only so no nome.';
                END;
            END IF;
        END $$
        """
    )
    # QUEM CONECTA PRECISA SER MEMBRO para poder `SET ROLE`. `CURRENT_USER`
    # porque a migration nao sabe o nome da role de conexao — e nao deve saber:
    # ele vem do ambiente.
    op.execute(f"GRANT {ROLE} TO CURRENT_USER")

    # PUBLIC primeiro: sem isto, um privilegio herdado de `PUBLIC` sobreviveria
    # ao REVOKE nominal e a role restrita teria mais do que se declarou.
    op.execute("REVOKE ALL ON TABLE audit_trail FROM PUBLIC")
    op.execute(f"REVOKE ALL ON TABLE audit_trail FROM {ROLE}")
    # INSERT para escrever, SELECT para o `previous_hash` e para a verificacao.
    # `02` §4 diz "INSERT apenas" sobre ESCRITA — sem SELECT, a propria cadeia
    # seria inescrevivel: nao ha como encadear sem ler a linha anterior.
    op.execute(f"GRANT INSERT, SELECT ON TABLE audit_trail TO {ROLE}")
    # EXPLICITO, e redundante de proposito: `REVOKE ALL` acima ja tirou os tres.
    # Escrever os nomes que `02` §4 escreve faz o diff dizer o que a spec exige,
    # e faz o verificador da §7 ter o que casar.
    op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_trail FROM {ROLE}")

    # -- 3. o trigger, incondicional -----------------------------------------
    #
    # `02` §4: "trigger BEFORE UPDATE OR DELETE que levanta excecao
    # INCONDICIONALMENTE". Sem `IF`, sem excecao para role administrativa, sem
    # janela de manutencao — condicao aqui e a porta pela qual a imutabilidade
    # deixa de valer, e quem tem privilegio para precisar dela tem privilegio
    # para desligar o trigger, que ao menos deixa rastro no esquema.
    op.execute(
        """
        CREATE FUNCTION fn_audit_trail_imutavel() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_trail e append-only: % recusado. 02_DOMAIN_ACADEMUS secao 4 '
                'e 05_SECURITY_REQUIREMENTS secao 7. Correcao entra como LINHA '
                'NOVA, nunca como reescrita — a cadeia de hash existe para que '
                'reescrita seja visivel.',
                TG_OP;
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_audit_trail_imutavel
        BEFORE UPDATE OR DELETE ON audit_trail
        FOR EACH ROW EXECUTE FUNCTION fn_audit_trail_imutavel()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_audit_trail_imutavel ON audit_trail")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_trail_imutavel()")
    op.execute(f"REVOKE ALL ON TABLE audit_trail FROM {ROLE}")
    op.drop_constraint("fk_grades_student", "grades", type_="foreignkey")
    op.drop_index("ix_audit_actor", table_name="audit_trail")
    op.drop_index("ix_audit_occurred_at", table_name="audit_trail")
    op.drop_table("audit_trail")
    # A ROLE NAO E APAGADA, e a assimetria e deliberada: ela e objeto de cluster
    # e pode ter privilegio em outra base. `DROP ROLE` num downgrade derrubaria
    # algo que esta migration nao criou sozinha.
