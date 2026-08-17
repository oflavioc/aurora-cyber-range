#!/usr/bin/env python3
"""O DEMO da Fase 4, ponta a ponta, contra a stack de CONTAINERS. Peca 7.

O ROTEIRO E O DE `07_IMPLEMENTATION_PHASES.md`, e nao um parecido:

    GM clica A01 -> engine grava evento e muda projecao -> API degrada matricula
    -> wallboard reage em < 1 s -> participant-view exibe texto_para_plateia ->
    GM clica ROLLBACK -> estado restaurado, evento registrado

POR QUE ELE E UM PASSO DE CI, E NAO UM ROTEIRO ESCRITO
-------------------------------------------------------
Item 1 da DoD: *"a sequencia do DEMO roda ponta a ponta SEM INTERVENCAO
MANUAL"*. Roteiro que ninguem executa apodrece igual a comentario que ninguem le
— a Fase 1 pagou por um DEMO inexecutavel havia tempo sem que nada acusasse, e
o `demo_fase2.py` virou passo de CI por isso.

O QUE ESTE ACRESCENTA AO `demo_fase2.py`
-----------------------------------------
Aquele monta os objetos em memoria, num processo so. Este fala HTTP e WebSocket
com **dois containers**, atraves de Postgres e Redis de verdade: o que ele prova
alem da logica e a MONTAGEM — imagem, entrypoint, rede, volume — e a unica coisa
compartilhada entre os dois processos e a stack.

E por isso ele prova uma coisa que nenhum teste em processo alcanca: que a
`academus-api` DEGRADA por causa de um evento que o `range-api` gravou. Sao dois
containers, duas raizes de composicao, um event store.

A ASSERCAO QUE DISCRIMINA E O PAR EM VOLTA DO ROLLBACK
-------------------------------------------------------
`POST /enrollment` com o MESMO par aluno/turma e chamado duas vezes: depois do
disparo, tem de dar **503**; depois do rollback, tem de dar **201**. Mesma
requisicao, resultados opostos — uma API que nunca degradasse passaria na
segunda, e uma que degradasse sempre passaria na primeira. So as duas juntas
dizem que o estado voltou.

O DEMO EXIGE UM EXERCICIO QUE AINDA NAO COMECOU
------------------------------------------------
`exercise_started` ja no store significa que o exercicio esta em curso, e
`engine.start()` recusa. Isso e correto e nao e defeito: o DEMO e a PRIMEIRA
coisa que roda contra a stack. Ele para com a mensagem que diz o que fazer, em
vez de disfarcar.

USO
    docker compose up -d
    python scripts/demo_fase4.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from websockets.sync.client import connect  # noqa: E402

from domains.academus.api.repositorio import engine_do_ambiente  # noqa: E402
from domains.academus.seed.demonstracao import carregar  # noqa: E402
from range_core.api import tokens  # noqa: E402

RANGE = os.environ.get("AURORA_DEMO_RANGE_URL", "http://127.0.0.1:8000")
ACADEMUS = os.environ.get("AURORA_DEMO_ACADEMUS_URL", "http://127.0.0.1:8001")

#: O inject do DEMO. D13: o pack e o `pack_minimo` do fixture, e `A01` ja tem
#: `academus.enrollment_offline: true` e `texto_para_plateia` — que e
#: exatamente o que o roteiro pede.
INJECT = "A01"

#: O par que a matricula usa. `A-1002` e `T-2002` sao do seed de demonstracao, e
#: `enrollments` nasce VAZIA de proposito (D8): o caminho feliz e a matricula
#: ACONTECENDO, e uma tabela pre-carregada tornaria "matriculou" indistinguivel
#: de "ja estava la".
ALUNO = "A-1002"
TURMA = "T-2002"

#: Item 2 da DoD. O numero e de relogio de parede e atravessa dois containers —
#: a prova de PROTOCOLO (nao ha espera no caminho do frame) esta na suite, por
#: AST. Aqui o que se mede e a ponta a ponta.
ORCAMENTO_DO_FRAME = 1.0


class DemoError(Exception):
    """O DEMO para. Alto, e dizendo o que fazer."""


def _pede(url: str, *, metodo: str = "GET", corpo=None, token: str | None = None):
    dados = None if corpo is None else json.dumps(corpo).encode()
    pedido = urllib.request.Request(url, data=dados, method=metodo)
    if dados is not None:
        pedido.add_header("Content-Type", "application/json")
    if token:
        pedido.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


def _exige(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise DemoError(mensagem)


def _passo(rotulo: str, detalhe: str = "") -> None:
    print(f"  {rotulo:.<28} {detalhe}")


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    _exige(bool(dsn), "DATABASE_URL ausente: o DEMO precisa semear os seis registros.")
    segredo = os.environ.get("AURORA_JWT_SECRET", "")
    _exige(bool(segredo), "AURORA_JWT_SECRET ausente.")
    credencial = os.environ.get("AURORA_GM_PASSWORD", "")
    _exige(bool(credencial), "AURORA_GM_PASSWORD ausente.")

    print("\nDEMO da Fase 4 — a sequencia de `07`, contra a stack de containers\n")

    # -- 0. o dado de demonstracao. NAO e seed (D8): seis registros para que a
    #       matricula tenha o que matricular. O seed em escala e T8, da Fase 5.
    carregar(engine_do_ambiente(dsn))
    _passo("fixture de demonstracao", "seis registros")

    # O token de dominio e assinado AQUI, e nao pedido a uma rota: `/auth/token`
    # esta `planejada` na superficie do adapter, e a Fase 3 recusou de proposito
    # um endpoint que assina o papel pedido no corpo. Quem assina aqui e um
    # script de facilitacao com o segredo em maos — o mesmo estatuto do seed.
    token_do_aluno = tokens.issue(ALUNO, "aluno", secret=segredo)

    codigo, corpo = _pede(f"{RANGE}/session", metodo="POST", corpo={"credencial": credencial})
    _exige(codigo == 200, f"POST /session respondeu {codigo}: {corpo!r}")
    console = json.loads(corpo)["token"]
    _passo("sessao do facilitador", "token emitido")

    canal = RANGE.replace("http", "ws")
    # OS DOIS CANAIS SAO DO `range-api`. A `academus-api` nao tem canal: ela e
    # o sistema que o exercicio quebra, e nao uma projecao de sala.
    with connect(f"{canal}/ws/wallboard") as telao, connect(
        f"{canal}/ws/plateia"
    ) as plateia:
        # O ESTADO CORRENTE CHEGA SEM PEDIR — item 3 da DoD virando propriedade
        # do protocolo: quem conecta agora recebe o frame inteiro.
        antes = json.loads(telao.recv())
        plateia.recv()
        _exige(
            antes["indice_de_saude"] == 100,
            f"a sala nao comecou intacta: saude {antes['indice_de_saude']}. "
            "O DEMO exige um exercicio que ainda nao comecou — "
            "`docker compose down -v && docker compose up -d`.",
        )
        _passo("telao antes", f"saude {antes['indice_de_saude']}")

        # -- 1. a matricula funciona ANTES. Sem isto, "degradou" nao se
        #       distingue de "nunca funcionou".
        codigo, corpo = _pede(
            f"{ACADEMUS}/enrollment",
            metodo="POST",
            corpo={"student_id": "A-1001", "class_id": TURMA},
            token=tokens.issue("A-1001", "aluno", secret=segredo),
        )
        _exige(codigo == 201, f"matricula antes do inject respondeu {codigo}: {corpo!r}")
        _passo("matricula antes", "201")

        codigo, corpo = _pede(f"{RANGE}/exercise/start", metodo="POST", corpo={}, token=console)
        _exige(codigo == 200, f"POST /exercise/start respondeu {codigo}: {corpo!r}")
        # OS DOIS CANAIS SAO DRENADOS, e nao so o do telao. Toda rota que move o
        # exercicio publica nas DUAS projecoes — e a primeira versao deste script
        # lia so o telao aqui, deixando o frame de `exercise_started` na fila da
        # plateia. O `recv` seguinte pegava ESSE, com o texto vazio, e o DEMO
        # acusava "a plateia nao recebeu texto_para_plateia" com o servidor
        # inteiramente correto. Achado rodando, e a mensagem apontava para o
        # lugar errado — que e o custo de ler uma fila pela metade.
        telao.recv()
        plateia.recv()
        _passo("exercicio iniciado", "T0 gravado")

        # -- 2. O DISPARO, e o cronometro do item 2 da DoD.
        marca = time.monotonic()
        codigo, corpo = _pede(
            f"{RANGE}/injects/{INJECT}/fire", metodo="POST", corpo={}, token=console
        )
        _exige(codigo == 201, f"disparo respondeu {codigo}: {corpo!r}")

        depois = json.loads(telao.recv(timeout=ORCAMENTO_DO_FRAME))
        latencia = time.monotonic() - marca
        _exige(
            latencia < ORCAMENTO_DO_FRAME,
            f"o frame levou {latencia:.3f}s, acima do orcamento de {ORCAMENTO_DO_FRAME}s",
        )
        _exige(
            depois["indice_de_saude"] < antes["indice_de_saude"],
            f"o telao nao piorou: {antes['indice_de_saude']} -> {depois['indice_de_saude']}",
        )
        _passo(
            "telao reagiu",
            f"saude {depois['indice_de_saude']}, "
            f"{len(depois['destaques'])} destaques, {latencia * 1000:.0f} ms",
        )

        narrativa = json.loads(plateia.recv(timeout=ORCAMENTO_DO_FRAME))
        _exige(bool(narrativa["texto"]), "a plateia nao recebeu texto_para_plateia")
        _passo("plateia", f'"{narrativa["texto"][:44]}..."')

        # -- 3. A DEGRADACAO, no OUTRO container.
        codigo, corpo = _pede(
            f"{ACADEMUS}/enrollment",
            metodo="POST",
            corpo={"student_id": ALUNO, "class_id": TURMA},
            token=token_do_aluno,
        )
        _exige(
            codigo == 503,
            f"a matricula NAO degradou: {codigo}. O evento foi gravado pelo "
            "`range-api` e lido pela `academus-api` — se isto falha, os dois "
            "containers nao estao vendo o mesmo event store.",
        )
        _passo("matricula degradada", f"503 — {json.loads(corpo).get('detail', '')[:40]}")

        # -- 4. O ROLLBACK, ancorado no `exercise_started`.
        codigo, corpo = _pede(f"{RANGE}/timeline", token=console)
        _exige(codigo == 200, f"GET /timeline respondeu {codigo}")
        entradas = json.loads(corpo)["entradas"]
        alvo = entradas[0]["event_id"]

        codigo, corpo = _pede(
            f"{RANGE}/exercise/rollback",
            metodo="POST",
            corpo={"to_event_id": alvo, "reason": "facilitation"},
            token=console,
        )
        _exige(codigo == 200, f"rollback respondeu {codigo}: {corpo!r}")
        epoch = json.loads(corpo)["simulation_epoch"]

        restaurado = json.loads(telao.recv())
        _exige(
            restaurado["indice_de_saude"] == antes["indice_de_saude"],
            f"a projecao nao voltou: {restaurado['indice_de_saude']} != "
            f"{antes['indice_de_saude']}",
        )
        _passo("rollback", f"saude {restaurado['indice_de_saude']}, epoch {epoch}")

    # -- 5. o par que fecha: a MESMA requisicao que deu 503 agora da 201.
    codigo, corpo = _pede(
        f"{ACADEMUS}/enrollment",
        metodo="POST",
        corpo={"student_id": ALUNO, "class_id": TURMA},
        token=token_do_aluno,
    )
    _exige(
        codigo == 201,
        f"a matricula nao voltou depois do rollback: {codigo}: {corpo!r}",
    )
    _passo("matricula restaurada", "201 — a mesma requisicao que deu 503")

    # -- 6. e o evento continua registrado. `00` §5.5: rollback NAO apaga nada.
    codigo, corpo = _pede(f"{RANGE}/timeline", token=console)
    entradas = json.loads(corpo)["entradas"]
    anotadas = [e for e in entradas if "rollback" in e]
    disparos = [e for e in entradas if e.get("inject_id") == INJECT]
    _exige(len(anotadas) == 1, f"a timeline nao anotou o rollback: {entradas}")
    _exige(
        bool(disparos),
        "o disparo sumiu da timeline: rollback NAO apaga evento — `00` §5.5",
    )
    _passo("timeline", f"{len(entradas)} entradas, rollback anotado, disparo preservado")

    print("\n  a sequencia inteira, sem intervencao manual.\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DemoError as erro:
        print(f"\nDEMO INTERROMPIDO: {erro}\n", file=sys.stderr)
        raise SystemExit(1) from erro
