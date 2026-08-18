#!/usr/bin/env python3
"""Prova que `check_prova_do_seed.py` REPROVA — e a direcao (a) e a que importa.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

POR QUE OS PROBES INJETAM O DOCUMENTO
---------------------------------------
O defeito central e a AUSENCIA do arquivo, e plantar ausencia exigiria apagar a
evidencia de quem esta rodando. `avalia()` recebe o documento, o `HEAD` e o
estado de versionamento por parametro para que nenhum probe toque o disco.

A DIRECAO QUE MAIS IMPORTA E A PRIMEIRA: um verificador que degradasse para "ok"
por nao achar o arquivo trocaria um NAO VERIFICADO por um verde — e e exatamente
o que os dois predicados de base aposentados da Fase 3 faziam, cada um a sua
maneira.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_prova_do_seed import EVIDENCIA, avalia, main  # noqa: E402

SHA = "a" * 40
OUTRO = "b" * 40

VALIDO = {
    "commit": SHA,
    "maquina": "Windows-11",
    "python": "3.12.10",
    "data": "2026-08-18T12:00:00+00:00",
    "seed": 20260818,
    "linhas": 3_543_783,
    "orcamento_s": 300.0,
    "segundos": [150.3, 159.4],
    "item_1_seed_em_menos_de_5_min": True,
    "item_2_byte_identico": True,
    "digests": {"audit_trail": "c" * 64, "students": "d" * 64},
}

PROBES = [
    (
        "(a) o arquivo NAO EXISTE — e isto nao pode degradar para ok",
        (None, SHA, False),
        "nao existe ou nao e JSON legivel",
    ),
    (
        "(b) a prova e de OUTRO commit",
        (VALIDO | {"commit": OUTRO}, SHA, False),
        "Ela mede OUTRO commit",
    ),
    (
        "(b) o checkout nao resolve HEAD",
        (VALIDO, None, False),
        "nao resolve um HEAD de git",
    ),
    (
        "(c) o arquivo esta VERSIONADO — a amarracao viraria circular",
        (VALIDO, SHA, True),
        "esta VERSIONADO",
    ),
    (
        "(d) falta a maquina — `06` T3 exige o contexto ao lado do numero",
        ({k: v for k, v in VALIDO.items() if k != "maquina"}, SHA, False),
        "nao traz `maquina`",
    ),
    (
        "(d) falta a contagem de linhas",
        (VALIDO | {"linhas": 0}, SHA, False),
        "nao traz `linhas`",
    ),
    (
        "(e) a prova gravada diz que o item 1 FALHOU",
        (VALIDO | {"item_1_seed_em_menos_de_5_min": False}, SHA, False),
        "NAO passou",
    ),
    (
        "(e) e que o item 2 falhou",
        (VALIDO | {"item_2_byte_identico": False}, SHA, False),
        "NAO passou",
    ),
    (
        "controle: prova valida do commit corrente",
        (VALIDO, SHA, False),
        None,
    ),
]


def roda(rotulo: str, argumentos: tuple, esperado: str | None) -> bool:
    problemas = avalia(*argumentos)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': condicao plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com condicao plantada - {rotulo}")
    return True


def main_probes() -> int:
    resultados = [roda(*p) for p in PROBES]
    # O ESTADO REAL DESTE CHECKOUT e informativo, e nao um eixo: a evidencia so
    # existe na maquina que mediu, e o CI nunca a tem — pelo mesmo motivo do
    # `check_provas_de_container`, que tambem so roda os probes no CI.
    print(f"\n  neste checkout: `{EVIDENCIA}` "
          f"{'existe' if (REPO_ROOT / EVIDENCIA).exists() else 'NAO existe'}, "
          f"e `main()` retorna {main([])}")
    if all(resultados):
        print(
            f"\ncheck_prova_do_seed.py reprova nos {len(resultados)} eixos: "
            "ausencia, commit divergente, HEAD irresolvivel, arquivo versionado, "
            "contexto incompleto em duas formas, os dois itens falhos, e o "
            "controle verde."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
