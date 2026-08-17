"""O banco de business state para a suite. **Nao e teste** — daí o `_`.

`unittest discover` procura `test*.py`, entao este arquivo nao e coletado. Quem
o importa sao `test_api_rbac.py`, `test_api_degradacao.py`,
`test_business_state_postgres.py` e `test_queda_de_sessao.py`.

VARIAVEL PROPRIA, E NAO `DATABASE_URL`
--------------------------------------
Mesma disciplina de `test_event_store_postgres.py`, e pelo mesmo motivo: estes
testes **truncam** as quatro tabelas. Apontar para `DATABASE_URL` faria um
`python -m unittest` distraido apagar o business state de desenvolvimento de
quem estivesse com o `.env` carregado.

`AURORA_TEST_DATABASE_URL` e explicita: quem a define esta dizendo que aquele
banco e descartavel. Ausente, os testes PULAM — e o `skip` diz como rodar, para
que pulo silencioso nao seja confundido com verde.

O QUE MUDOU COM A P3-5, E O QUE ISSO CUSTA
--------------------------------------------
Ate a peca 4 desta fase, RBAC e degradacao rodavam **sem banco nenhum**: o
business state eram dicionarios de modulo. Com o estado em Postgres, os dois
arquivos passam a exigir a stack — e passam a PULAR onde ela nao existe.

Isso e piora local e melhora onde se julga: CI e o lancador da auditoria sobem
Postgres e rodam `alembic upgrade head`, entao nos dois lugares em que alguem
emite veredito a suite roda inteira. A alternativa — um repositorio em memoria
ao lado do de Postgres, so para a suite — seria o duplo que testa a si mesmo, e
reintroduziria como duplo exatamente o dicionario de modulo que a P3-5 removeu.

O TRUNCATE NAO TOCA `event_store`
-----------------------------------
As quatro tabelas de business state, e so elas. `event_store` tem cadeia de hash
e vida propria; quem a limpa e `test_event_store_postgres.py`, que sabe o que
esta fazendo com ela.
"""

from __future__ import annotations

import os
import unittest

from sqlalchemy import Engine, text

from domains.academus.api.repositorio import Repositorio, engine_do_ambiente
from domains.academus.seed import demonstracao

DSN_ENV = "AURORA_TEST_DATABASE_URL"
URL = os.environ.get(DSN_ENV)

RAZAO = (
    f"{DSN_ENV} nao definida. Estes testes truncam as tabelas de business state, "
    "entao exigem banco declarado descartavel, com `alembic upgrade head` "
    "aplicado. Para rodar:\n"
    f"    DATABASE_URL=postgresql+psycopg://user:senha@127.0.0.1:5432/base \\\n"
    "        python -m alembic upgrade head\n"
    f"    {DSN_ENV}=postgresql+psycopg://user:senha@127.0.0.1:5432/base \\\n"
    "        python -m unittest discover -s tests"
)

#: Decorador de classe. `@exige_banco` em vez de `@unittest.skipIf(...)` repetido
#: em quatro arquivos: a razao do pulo e uma so, e escrita quatro vezes ela
#: envelhece em tres.
exige_banco = unittest.skipIf(URL is None, RAZAO)

#: ORDEM INVERSA DAS FKs. `students` antes de `enrollments` deixaria a referencia
#: pendurada; `CASCADE` resolveria e esconderia a ordem errada, e a ordem errada
#: e informacao — ela diz que alguem mudou o esquema sem olhar as dependencias.
TABELAS = ("enrollments", "grades", "classes", "students")


def engine() -> Engine:
    """O engine do banco de teste. Chamada so depois de `exige_banco`."""
    return engine_do_ambiente(str(URL))


def banco_limpo() -> Engine:
    """Trunca as quatro tabelas e recarrega a fixture de demonstracao.

    `RESTART IDENTITY` zera as sequencias de `grades` e `enrollments`. Sem isso a
    chave substituta cresceria entre os testes — inofensivo hoje, e exatamente o
    tipo de valor que um teste futuro assumiria estavel sem dizer.
    """
    motor = engine()
    with motor.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY"))
    demonstracao.carregar(motor)
    return motor


def repositorio_limpo() -> Repositorio:
    return Repositorio(banco_limpo())
