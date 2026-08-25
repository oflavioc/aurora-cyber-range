"""O `range-api` como PROCESSO — o que o container executa. Peca 7.

AUTORIDADE
----------
`07_IMPLEMENTATION_PHASES.md` Fase 4, item 4 da DoD (*"reinicio do container do
engine restaura o exercicio a partir do event store"*); `06_ACCEPTANCE_TESTS.md`
T5 (*"os dois casos"*: pausado restaura pausado, retomado restaura correndo);
`01_ARCHITECTURE.md` §4 (as cinco camadas de estado) e §3 (o clock nao congela
enquanto o range esta fora do ar); `05_SECURITY_REQUIREMENTS.md` §6 e §8.

O QUE ESTE MODULO E: a RAIZ DE COMPOSICAO
------------------------------------------
Ate a peca 6, quem montava o exercicio eram `scripts/sobe_sala.py` (em memoria) e
a suite. Nenhum dos dois e o container. Este e — e a diferenca nao e aritmetica,
e a MONTAGEM: imagem, entrypoint, caminho de configuracao, rede e volume. A §4.4
declarou exatamente essa divisao ao recusar chamar de container o teste de
processo novo da peca 3.

O DOMINIO CHEGA POR CONFIGURACAO, E NAO POR IMPORT
---------------------------------------------------
O invariante 1 proibe o core de importar `domains/`, e este modulo mora no core.
Entao o pack e as flags do adapter chegam como CAMINHO, por variavel de
ambiente — `AURORA_PACK` e `AURORA_FLAGS` —, e sao lidos como **dado**.

Nao e contorno do invariante: e o mesmo desenho de `contract_rules.build_registries`,
que deixou de ler `domains/*/flags.yaml` do disco justamente para receber as
flags de quem monta o processo. Aqui quem monta e o compose, e a consequencia e
que a MESMA imagem serve outro adapter — `prontus` — sem uma linha de core mudar.
Se este modulo importasse `domains.academus`, o core teria um dominio preferido.

O CLOCK NASCE DO FLUXO, E NAO DO RELOGIO DE PAREDE
---------------------------------------------------
No boot, o processo LE o store antes de existir engine. Se ha eventos, o clock e
`restaurar(...)` — os cinco valores da peca 3 —, e nao um `ExerciseClock` novo.
Um processo que subisse com T0 do momento do boot faria o exercicio recomecar a
cada reinicio, com a sala inteira olhando.

**O reinicio nao congela o exercicio**, e isso e `01` §3: enquanto o processo
esteve fora do ar, o tempo de exercicio correu. O que congela e a pausa, e ela e
explicita — `paused_in` sobre o par `exercise_paused`/`exercise_resumed`.

RECUSA ALTA, E NO BOOT
-----------------------
Toda variavel obrigatoria e exigida aqui, sem default. Um processo que subisse
com metade da configuracao teria uma API que autentica e nao opera — e
descobrir isso no meio do exercicio e o pior momento possivel. E a mesma
disciplina de `credencial_do_console` e de `jwt_secret`.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import redis
import yaml
from fastapi import FastAPI

from range_core.api.app import Exercicio, credencial_do_console, montar
from range_core.api.tokens import jwt_secret
from range_core.clock.exercise_clock import ExerciseClock
from range_core.clock.restauracao import clock_do_store
from range_core.engine.inject_engine import Facilitator, InjectEngine
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.engine.verificacao import LacoDeVerificacao
from range_core.events.postgres_store import PostgresEventStore
from range_core.state.cache import RedisProjectionCache

#: O caminho do pack de exercicio. VOLUME, e nao conteudo de imagem: `01` §6 da
#: ao gm-console um seletor de pack, entao o pack e entrada de deploy — e uma
#: imagem que o carregasse dentro precisaria ser reconstruida para trocar de
#: cenario.
VARIAVEL_DO_PACK = "AURORA_PACK"

#: O `flags.yaml` do adapter, como DADO. Ver o cabecalho.
VARIAVEL_DAS_FLAGS = "AURORA_FLAGS"

VARIAVEL_DO_BANCO = "DATABASE_URL"
VARIAVEL_DO_REDIS = "REDIS_URL"

#: Quem opera o console. `03` §7 da ao facilitador a timeline integral e os
#: quatro comandos; `role="control"` e a camada de `09` §1.
FACILITADOR = Facilitator(user="facilitador", role="control")


class ConfiguracaoDoProcessoError(Exception):
    """O processo nao sobe. Alto, e no boot."""


def exige(nome: str, ambiente: dict[str, str] | None = None) -> str:
    valor = (ambiente if ambiente is not None else os.environ).get(nome, "")
    if not valor:
        raise ConfiguracaoDoProcessoError(
            f"{nome} ausente. O `range-api` opera o exercicio: subir com metade "
            "da configuracao produz uma API que autentica e nao opera, e o meio "
            "do exercicio e o pior momento para descobrir isso."
        )
    return valor


def criar() -> FastAPI:
    """A fabrica que o `uvicorn --factory` chama. Uma vez, no boot."""
    dsn = exige(VARIAVEL_DO_BANCO)
    caminho_do_pack = Path(exige(VARIAVEL_DO_PACK))
    caminho_das_flags = Path(exige(VARIAVEL_DAS_FLAGS))

    # DUAS CONSTRUCOES DO STORE, e a primeira so LE. O construtor exige clock
    # porque o store carimba no append; o clock, por sua vez, sai do fluxo que
    # so o store sabe ler. E a mesma ordem de `tests/_restaura_em_outro_processo.py`,
    # e o valor provisorio nao entra em nada — se entrasse, o teste de T0
    # passaria com qualquer coisa.
    provisorio = PostgresEventStore(ExerciseClock(datetime(1970, 1, 1)), dsn)
    clock = clock_do_store(provisorio)
    store = PostgresEventStore(clock, dsn)

    contratos = contract_source.read_contracts()
    flags = AdapterFlags.from_document(
        yaml.safe_load(caminho_das_flags.read_text(encoding="utf-8")),
        source=caminho_das_flags.as_posix(),
    )
    pack = load_pack(caminho_do_pack, contracts=contratos, adapter_flags=flags)

    # O LAÇO CONTÍNUO de `03` §3.1, montado UMA vez e compartilhado.
    #
    # É aqui que ele deixa de ser opcional: o engine e o emissor de participante
    # aceitam `None` porque teste e demo os montam sem pack de gabarito, e é esta
    # composição — a de produção — que garante que o laço existe. Um segundo laço
    # para a superfície de participante leria o mesmo store e daria a mesma
    # resposta, mas nada garantiria que os dois carregam o mesmo pack.
    laco = LacoDeVerificacao(
        store=store,
        predicados=pack.verification_predicates,
        declarations=pack.declarations,
        # DO CONTRATO, LIDO UMA VEZ AQUI — `04` §4.1. O avaliador tinha o seu
        # próprio `SINCE_SELF = "self"`, gêmeo do que existia no loader, e as
        # duas cópias concordavam por coincidência. É a mesma forma com que
        # `rollback_reasons` desce para o `InjectEngine`, três linhas abaixo.
        since_qualifiers=contract_source.since_qualifiers(contratos),
    )

    exercicio = Exercicio(
        engine=InjectEngine(
            pack=pack,
            clock=clock,
            store=store,
            facilitator=FACILITADOR,
            rollback_reasons=contract_source.rollback_reasons(contratos),
            laco=laco,
        ),
        cache=RedisProjectionCache(redis.from_url(exige(VARIAVEL_DO_REDIS))),
        declarations=pack.declarations,
        specs=flags.specs,
        textos=pack.textos_para_plateia,
        credencial=credencial_do_console(),
        segredo=jwt_secret(),
    )
    return montar(exercicio)
