#!/usr/bin/env python3
"""O item 4 da DoD e o par de T5, atravessando `docker restart`. Peca 7.

O QUE A PECA 3 PROVOU, E O QUE FALTAVA
---------------------------------------
A peca 3 provou a DERIVACAO — os cinco valores a partir do fluxo — e provou que
ela sobrevive a uma fronteira de processo real, com Postgres no meio. E a §4.4
recusou chamar aquilo de container, com todas as letras:

    | funcao pura   | a derivacao                          | peca 3 |
    | processo novo | a ida e volta pelo banco             | peca 3 |
    | container     | imagem, entrypoint, rede e volume    | peca 7 |

**Este script e a terceira linha.** O item 4 diz *"reinicio do CONTAINER do
engine"*, e chamar processo de container seria trocar a condicao por um proxy —
que e como a P3-2 venceu sem que a condicao dela tivesse ocorrido.

A ASSERCAO QUE UM TESTE EM PROCESSO NAO CONSEGUE PRODUZIR
-----------------------------------------------------------
`docker inspect --format {{.State.StartedAt}}` **antes e depois**. Se alguem
trocar o `docker restart` por um reinicio de processo — ou por nada —, o carimbo
nao muda e este script reprova. Sem essa linha, o par de T5 abaixo passaria
tambem num processo, e a diferenca entre peca 3 e peca 7 evaporaria sem que
ninguem visse.

O PAR DE T5, E COMO ELE E OBSERVADO DE FORA
--------------------------------------------
T5 exige os DOIS casos: *"reinicio com o exercicio pausado o restaura pausado;
reinicio depois da retomada o restaura correndo"*. Nenhuma rota expoe o clock —
e nao deve expor: o que a sala precisa e a projecao. Entao o clock e observado
pelo unico lugar onde ele se manifesta, que e o **carimbo do proximo evento**:

    pausado    disparar depois do reinicio carimba o MESMO `exercise_time`
               (o clock esta congelado, `01` §3)
    correndo   disparar depois do reinicio carimba um `exercise_time` MAIOR,
               e maior inclusive pelo tempo em que o container esteve FORA DO AR
               (`01` §3: na falha do range, o clock de exercicio continua
               correndo; quem desconta e a projecao de metricas)

Os dois juntos matam as tres implementacoes erradas plausiveis: subir sempre
pausado passa no primeiro e falha no segundo; subir sempre correndo faz o
inverso; e subir com T0 = agora derruba os dois, porque o `exercise_time`
voltaria para perto de zero.

USO
    docker compose up -d
    python scripts/prova_reinicio_de_container.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from contracts.generated.events import EXERCISE_PAUSED

RANGE = os.environ.get("AURORA_DEMO_RANGE_URL", "http://127.0.0.1:8000")
CONTAINER = os.environ.get("AURORA_RANGE_CONTAINER", "aurora-range-api")

#: O inject do `pack_minimo` (D13) que carimba o primeiro caso. So UM e
#: preciso: o segundo caso e carimbado por um `exercise_paused`, que nao gasta
#: inject nenhum e pode ser emitido quantas vezes for.
INJECT_PAUSADO = "A02"

#: Quanto o container fica fora do ar, no segundo caso. Precisa ser maior que a
#: resolucao de `exercise_time` (segundos) para que "o clock correu enquanto ele
#: esteve fora" seja uma afirmacao com numero, e nao arredondamento.
SEGUNDOS_FORA_DO_AR = 3

ESPERA_MAXIMA = 90


class ProvaError(Exception):
    """A prova para. Alto."""


def _pede(caminho: str, *, metodo: str = "GET", corpo=None, token: str | None = None):
    dados = None if corpo is None else json.dumps(corpo).encode()
    pedido = urllib.request.Request(RANGE + caminho, data=dados, method=metodo)
    if dados is not None:
        pedido.add_header("Content-Type", "application/json")
    if token:
        pedido.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


def _docker(*argumentos: str) -> str:
    resultado = subprocess.run(
        ["docker", *argumentos], capture_output=True, text=True, check=False
    )
    if resultado.returncode != 0:
        raise ProvaError(f"`docker {' '.join(argumentos)}` falhou: {resultado.stderr}")
    return resultado.stdout.strip()


def _iniciado_em() -> str:
    return _docker("inspect", "--format", "{{.State.StartedAt}}", CONTAINER)


def _espera_saudavel() -> None:
    """Ate o healthcheck do compose dizer `healthy` — e nao um `sleep` fixo.

    Um `sleep` calibrado na maquina de quem escreve vira teste instavel na
    maquina de quem roda. O healthcheck ja pergunta a coisa certa: a projecao
    responde, o que exige Postgres, Redis e o fold.
    """
    limite = time.monotonic() + ESPERA_MAXIMA
    while time.monotonic() < limite:
        estado = _docker("inspect", "--format", "{{.State.Health.Status}}", CONTAINER)
        if estado == "healthy":
            return
        time.sleep(1)
    raise ProvaError(f"{CONTAINER} nao ficou saudavel em {ESPERA_MAXIMA}s")


def _segundos(marca: str) -> int:
    """`T+HH:MM:SS` -> segundos. `09` §1.1 fixa a forma."""
    corpo = marca.removeprefix("T+")
    horas, minutos, segundos = (int(p) for p in corpo.split(":"))
    return horas * 3600 + minutos * 60 + segundos


def _carimbo(token: str, *, tipo: str | None = None, inject: str | None = None) -> int:
    """O `exercise_time` do ULTIMO evento que casa, em segundos.

    O CARIMBO E LIDO DA TIMELINE, e nao inventado aqui: e o proprio evento que
    o engine gravou, com o clock que o boot restaurou. E a unica manifestacao
    observavel do clock — nenhuma rota o expoe, e nao deve expor: o que a sala
    precisa e a projecao.
    """
    _, corpo = _pede("/timeline", token=token)
    entradas = [
        e
        for e in json.loads(corpo)["entradas"]
        if (tipo is None or e["tipo"] == tipo)
        and (inject is None or e.get("inject_id") == inject)
    ]
    if not entradas:
        raise ProvaError(f"nenhum evento na timeline para tipo={tipo} inject={inject}")
    return _segundos(entradas[-1]["exercise_time"])


def _dispara(inject: str, token: str) -> int:
    codigo, corpo = _pede(f"/injects/{inject}/fire", metodo="POST", corpo={}, token=token)
    if codigo != 201:
        raise ProvaError(f"disparo de {inject} respondeu {codigo}: {corpo!r}")
    return _carimbo(token, inject=inject)


def _comando(caminho: str, token: str) -> None:
    codigo, corpo = _pede(caminho, metodo="POST", corpo={}, token=token)
    if codigo != 200:
        raise ProvaError(f"POST {caminho} respondeu {codigo}: {corpo!r}")


def _reinicia(rotulo: str) -> None:
    antes = _iniciado_em()
    _docker("restart", "--timeout", "10", CONTAINER)
    _espera_saudavel()
    depois = _iniciado_em()
    if antes == depois:
        raise ProvaError(
            f"{CONTAINER} nao foi reiniciado de verdade: `StartedAt` nao mudou "
            f"({antes}). Esta e a linha que impede a prova de passar com um "
            "reinicio de PROCESSO — ver o cabecalho."
        )
    print(f"  {rotulo:.<28} StartedAt {antes[11:19]} -> {depois[11:19]}")


def main() -> int:
    credencial = os.environ.get("AURORA_GM_PASSWORD", "")
    if not credencial:
        raise ProvaError("AURORA_GM_PASSWORD ausente.")

    print("\nO reinicio de CONTAINER — item 4 da DoD, e o par de T5\n")

    codigo, corpo = _pede("/session", metodo="POST", corpo={"credencial": credencial})
    if codigo != 200:
        raise ProvaError(f"POST /session respondeu {codigo}: {corpo!r}")
    token = json.loads(corpo)["token"]

    # O exercicio precisa estar em curso: o que se restaura e um exercicio, e um
    # store sem `exercise_started` nao tem T0 para restaurar.
    _, corpo = _pede("/timeline", token=token)
    if not json.loads(corpo)["entradas"]:
        codigo, corpo = _pede("/exercise/start", metodo="POST", corpo={}, token=token)
        if codigo != 200:
            raise ProvaError(f"POST /exercise/start respondeu {codigo}: {corpo!r}")
    print("  exercicio em curso")

    # ------------------------------------------------------------------------
    # CASO 1 — PAUSADO restaura PAUSADO.
    # ------------------------------------------------------------------------
    _comando("/exercise/pause", token)
    congelado = _carimbo(token, tipo=EXERCISE_PAUSED)
    print(f"  exercicio PAUSADO em T+{congelado}s")

    _reinicia("reiniciado pausado")
    time.sleep(SEGUNDOS_FORA_DO_AR)

    depois_do_reinicio = _dispara(INJECT_PAUSADO, token)
    if depois_do_reinicio != congelado:
        raise ProvaError(
            f"o clock ANDOU com o exercicio pausado: {congelado}s -> "
            f"{depois_do_reinicio}s. Reinicio com o exercicio pausado tem de "
            "restaurar PAUSADO — T5, primeiro caso."
        )
    print(
        f"  clock congelado.............. T+{depois_do_reinicio}s, "
        f"o mesmo de antes do reinicio"
    )

    # ------------------------------------------------------------------------
    # CASO 2 — RETOMADO restaura CORRENDO, e o tempo fora do ar CONTOU.
    #
    # O EVENTO QUE CARIMBA E OUTRO `exercise_paused`, e nao um terceiro inject.
    # A primeira versao deste script lia `entradas[-1]` depois da retomada — e o
    # ultimo evento era o proprio `exercise_resumed`, carimbado ANTES do
    # reinicio, com o tempo congelado. Ele acusava "o clock nao andou" com o
    # servidor correto: eu media um evento que nao podia ter andado. Achado
    # rodando, e a licao e a de sempre — o instrumento tem de observar DEPOIS do
    # que ele julga.
    # ------------------------------------------------------------------------
    _comando("/exercise/resume", token)
    print("  exercicio RETOMADO")

    marca = time.monotonic()
    _reinicia("reiniciado correndo")
    time.sleep(SEGUNDOS_FORA_DO_AR)
    fora_do_ar = time.monotonic() - marca

    _comando("/exercise/pause", token)
    andou = _carimbo(token, tipo=EXERCISE_PAUSED)

    if andou <= congelado:
        raise ProvaError(
            f"o clock NAO andou depois da retomada: {congelado}s -> {andou}s. "
            "Reinicio depois da retomada tem de restaurar CORRENDO — T5, "
            "segundo caso."
        )
    if andou < congelado + int(fora_do_ar) - 2:
        raise ProvaError(
            f"o clock andou menos que o tempo fora do ar: {andou - congelado}s "
            f"contra {fora_do_ar:.0f}s. `01` §3 diz que na falha do range o "
            "clock de exercicio CONTINUA CORRENDO — restaurar congelado no "
            "ultimo evento inventaria uma pausa que ninguem declarou."
        )
    print(
        f"  clock correu................. T+{congelado}s -> T+{andou}s, "
        f"com {fora_do_ar:.0f}s fora do ar"
    )

    print("\n  os dois casos de T5, atravessando `docker restart`.\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvaError as erro:
        print(f"\nPROVA INTERROMPIDA: {erro}\n", file=sys.stderr)
        raise SystemExit(1) from erro
