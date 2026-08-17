"""Alembic — ambiente de migracao.

A URL do banco vem de DATABASE_URL no ambiente, nunca de arquivo versionado:
credencial em arquivo versionado violaria 05_SECURITY_REQUIREMENTS.md secao 6.

`target_metadata` FICA None, E A RAZAO MUDOU — Fase 4, peca 5
--------------------------------------------------------------
A frase anterior dizia *"os modelos chegam na Fase 5; apontar para metadata
inexistente agora produziria autogenerate vazio que pareceria funcionar"*. Era
verdadeira quando escrita e deixou de ser: `domains/academus/models/registros.py`
tem os quatro modelos declarativos desde a P3-5, e eles chegaram na Fase 4.

O valor continua `None`, agora por um motivo diferente e mais forte: a metadata
existente cobre **quatro** das cinco tabelas. `event_store` e do core, tem
migration propria e e lida por `psycopg` cru, sem modelo declarativo — e um
`autogenerate` contra metadata parcial nao acusaria a ausencia: ele proporia
`DROP TABLE event_store`, porque e assim que ele le "tabela no banco e nao na
metadata".

As migrations deste projeto sao escritas a mao, e essa e a decisao. Ligar
`target_metadata` a `Base.metadata` do adapter poria o esquema do event store
sob a metadata de um domain — a direcao que o invariante 1 existe para nao
deixar acontecer — para ganhar um gerador que ninguem usa.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_url = os.environ.get("DATABASE_URL")
if _url:
    config.set_main_option("sqlalchemy.url", _url)

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
