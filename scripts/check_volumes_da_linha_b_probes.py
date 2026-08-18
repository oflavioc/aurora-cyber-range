#!/usr/bin/env python3
"""Prova que `check_volumes_da_linha_b.py` REPROVA contra divergencia plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

O EIXO QUE JUSTIFICA A CHECAGEM E O TERCEIRO: a constante trocada. Ele e o modo
de falha que o teste anterior NAO pegava, porque comparava o gerador consigo
mesmo — trocar `INDEVIDOS = 22` por `20` mantinha tudo verde e fazia o dataset
deixar de cumprir `02` §6.1.

O QUARTO E O QUE IMPEDE A DEGRADACAO: com a tabela ilegivel, as outras direcoes
passariam por vacuidade. Nao saber e o caso em que nao se pode afirmar.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_volumes_da_linha_b import (  # noqa: E402
    GERADOR,
    SPEC,
    constantes,
    main,
    verifica,
    volumes_da_spec,
)

DA_SPEC = volumes_da_spec(SPEC.read_text(encoding="utf-8"))
DO_CODIGO = constantes(GERADOR.read_text(encoding="utf-8"))

PROBES = [
    (
        "a constante trocada — o modo de falha que o teste anterior nao pegava",
        (DA_SPEC, DO_CODIGO | {"INDEVIDOS": 20}),
        "`02` §6.1 diz 22 e `dataset.INDEVIDOS` diz 20",
    ),
    (
        "outra constante trocada, para o eixo nao depender de um numero",
        (DA_SPEC, DO_CODIGO | {"DELEGADAS": 17}),
        "`dataset.DELEGADAS` diz 17",
    ),
    (
        "a constante sumiu do gerador",
        (DA_SPEC, {k: v for k, v in DO_CODIGO.items() if k != "SUSPEITOS"}),
        "nao declara a constante `SUSPEITOS`",
    ),
    (
        "conjunto novo na spec sem par declarado",
        (DA_SPEC | {"Contas de servico": "9"}, DO_CODIGO),
        "o registro deste verificador nao o conhece",
    ),
    (
        "constante de volume que a spec nao pede",
        (DA_SPEC, DO_CODIGO | {"INVENTADOS": 5}),
        "sem linha na tabela de `02` §6.1",
    ),
    (
        "a tabela da spec ficou ilegivel — a degradacao que nao pode existir",
        ({}, DO_CODIGO),
        "passariam por VACUIDADE",
    ),
    (
        "controle: a spec e o gerador como estao",
        (DA_SPEC, DO_CODIGO),
        None,
    ),
]


def roda(rotulo: str, argumentos: tuple, esperado: str | None) -> bool:
    problemas = verifica(*argumentos)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': divergencia plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com divergencia plantada - {rotulo}")
    return True


def probe_leitura_da_spec() -> bool:
    """A leitura real de `02` §6.1: os seis conjuntos, com os cinco numeros."""
    esperado = {
        "Indevidos comprovados": "22",
        "Ambíguos legítimos": "11",
        "Legítimos suspeitos à primeira vista": "34",
        "Ruído de manutenção": "60",
        "Credenciais compartilhadas": "18",
        "Legítimos normais": "milhares",
    }
    if DA_SPEC != esperado:
        print(f"FALHA: a leitura de `02` §6.1 devolveu {DA_SPEC}")
        return False
    print("OK: le os seis conjuntos de `02` §6.1 da propria spec, com os volumes")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1
    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_leitura_da_spec())
    print()
    if all(resultados):
        print(
            f"check_volumes_da_linha_b.py reprova nos {len(resultados)} eixos: duas "
            "constantes trocadas, constante ausente, conjunto novo sem par, "
            "constante sem linha na spec, tabela ilegivel, o controle verde e a "
            "leitura real dos seis conjuntos."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
