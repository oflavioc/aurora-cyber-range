"""A `academus-api` como PROCESSO — o que o container executa. Peca 7.

AUTORIDADE
----------
`02_DOMAIN_ACADEMUS.md` §7 (*"academus-api — FastAPI + SQLAlchemy"*);
`01_ARCHITECTURE.md` §4 (Business State em Postgres) e §5.4 (nenhum servico le
ou escreve flag nao declarada); `07_IMPLEMENTATION_PHASES.md` Fase 4, DEMO
SCRIPT (*"API degrada matricula"*).

O QUE A §4.6 DEIXOU MARCADO PARA CA
------------------------------------
*"Nenhum processo monta a `academus-api` ainda. `engine_do_ambiente` existe e tem
consumidor — a suite e o leitor de processo novo —, mas quem sobe o adapter com
`uvicorn`, `DATABASE_URL` e `RANDOM_SEED` do ambiente e o container da peca 7."*

**Esta e a peca 7, e este e o processo.** A frase datada da §4.6 fica verdadeira
por deixar de ser promessa.

AS DECLARACOES SAEM DO PACK, E NAO DE UMA LISTA AQUI
-----------------------------------------------------
O degradador le `simulation_state` pelo FOLD (`LeituraDeEstado`), e o fold precisa
das `Declarations` — que carregam `flag_defaults`, `inject_effects` e a
identidade do pack. Elas nao sao inventadas aqui: **este processo carrega o mesmo
pack que o `range-api` carrega, do mesmo volume**.

Duas listas de declaracao para o mesmo exercicio divergiriam na primeira
correcao, e a divergencia apareceria como *"a API degradou uma flag que o telao
nao mostra"* — a classe D4 da Fase 3, agora atravessando dois containers.

O ADAPTER IMPORTA O CORE, E ESSA DIRECAO E A ESPERADA
------------------------------------------------------
O invariante 1 proibe o CORE de importar `domains/`. Aqui a direcao e a inversa,
e e por isso que a raiz de composicao do adapter pode fazer o que
`range-core/api/processo.py` nao pode: nomear os dois lados.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI

from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.degradacao import (
    Degradador,
    LeituraDeEstado,
    cache_do_ambiente,
)
from domains.academus.api.emissor import Emissor
from domains.academus.api.repositorio import Repositorio, engine_do_ambiente
from domains.academus.api.surface import carregar as carregar_superficie
from range_core.api.processo import (
    VARIAVEL_DAS_FLAGS,
    VARIAVEL_DO_BANCO,
    VARIAVEL_DO_PACK,
    VARIAVEL_DO_REDIS,
    exige,
)
from range_core.api.tokens import jwt_secret
from range_core.clock.exercise_clock import ExerciseClock
from range_core.clock.restauracao import clock_do_store
from range_core.determinism import random_seed
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.events.postgres_store import PostgresEventStore


def criar() -> FastAPI:
    """A fabrica que o `uvicorn --factory` chama. Uma vez, no boot.

    A GUARDA DE BOOT DA P3-11 RODA DENTRO DE `montar`, e e por isso que ela
    protege o exercicio e nao so o repositorio: flag citada em
    `api_surface.yaml` e ausente do estado corrente **recusa o boot** aqui,
    com o container inteiro falhando ao subir, em vez de degradar em silencio
    durante a sala.
    """
    dsn = exige(VARIAVEL_DO_BANCO)
    caminho_das_flags = Path(exige(VARIAVEL_DAS_FLAGS))
    caminho_do_pack = Path(exige(VARIAVEL_DO_PACK))

    contratos = contract_source.read_contracts()
    flags = AdapterFlags.from_document(
        yaml.safe_load(caminho_das_flags.read_text(encoding="utf-8")),
        source=caminho_das_flags.as_posix(),
    )
    pack = load_pack(caminho_do_pack, contracts=contratos, adapter_flags=flags)

    # O ADAPTER PASSOU A ESCREVER, E O COMENTARIO ANTERIOR PREVIU ISTO.
    #
    # Ele dizia: *"so le… o valor fixo torna isso visivel: se algum dia este
    # processo passar a escrever, o carimbo de 1970 aparece no primeiro evento
    # em vez de passar despercebido."* A peca 3 desta fase o fez escrever
    # (`audit_query_performed`), e o dia chegou — B2 da sexta auditoria.
    #
    # DUAS CONSTRUCOES DO STORE, e a primeira so LE: o construtor exige clock
    # porque o store carimba no `append`, e o clock sai do fluxo que so o store
    # sabe ler. E a mesma ordem do `range-api`, e a MESMA funcao — `clock_do_store`
    # mudou de casa para `range_core.clock.restauracao` justamente para nao haver
    # duas reconstrucoes do mesmo estado.
    #
    # Sem isto, ligar o emissor teria carimbado os eventos do adapter com T0 de
    # 1970: `exercise_time` absurdo, e nenhum teste de rota pegaria — eles
    # afirmam sobre o payload, nao sobre o envelope.
    provisorio = PostgresEventStore(ExerciseClock(datetime(1970, 1, 1)), dsn)
    store = PostgresEventStore(clock_do_store(provisorio), dsn)

    return montar(
        autenticacao=Autenticacao(
            superficie=carregar_superficie(), segredo=jwt_secret()
        ),
        repositorio=Repositorio(engine_do_ambiente(dsn)),
        degradador=Degradador(
            leitura=LeituraDeEstado(
                store=store,
                declarations=pack.declarations,
                # A CONSTRUCAO VEM DE `degradacao`, e nao de `range_core.state`:
                # `check_api_surface.py` reprova qualquer modulo de `api/` que
                # importe estado, menos aquele. A primeira versao deste arquivo
                # importava direto e o gate reprovou — ver a nota la.
                cache=cache_do_ambiente(exige(VARIAVEL_DO_REDIS)),
            ),
            seed=random_seed(),
        ),
        # O EMISSOR, LIGADO — B2 da sexta auditoria. `api_surface.yaml` declara
        # `emite: audit_query_performed` para `GET /audit/grade-changes` desde a
        # peca 3, e esta fabrica montava sem ele: a unica rota instrumentada da
        # fase respondia normalmente e nao gravava nada, em producao.
        #
        # A guarda de `montar` existia para impedir exatamente isso e nao
        # impedia, porque lia o objeto errado (B1). As duas metades do mesmo
        # defeito: a declaracao sem wiring, e a guarda que nao alcancava a
        # declaracao.
        emissor=Emissor(store=store),
    )
