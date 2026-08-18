#!/usr/bin/env python3
"""Prova que `check_allowlist_do_auditor.py` REPROVA contra ausencia plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

O EIXO QUE JUSTIFICA A CHECAGEM E O PRIMEIRO — script novo fora da allowlist e
sem declaracao. Ele ja ocorreu QUATRO vezes na historia deste repositorio, a
ultima delas na propria rodada que corrigia a terceira.

O EIXO QUE A ESCOLHA POR REGEX EXIGE E O ULTIMO. A extracao dos nomes e textual,
e regex sobre codigo pode deixar de casar quando o formato muda e passar verde.
Os dois probes de divergencia cobrem os dois modos: leitura vazia e leitura
PARCIAL — extrair tres nomes de vinte tem de reprovar igual a extrair zero, e foi
exatamente o que aconteceu duas vezes ao escrever o verificador.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_allowlist_do_auditor import (  # noqa: E402
    FORA,
    HOOK,
    main,
    nomes_da_allowlist,
    verifica,
)

SCRIPTS = ["check_um", "check_dois", "prova_alguma_coisa"]
LIDOS = {"check_um", "check_dois"}
LIBERADOS = {"check_um", "check_dois"}
DECLARADOS = {"prova_alguma_coisa": "exige stack no ar"}

PROBES = [
    (
        "script novo fora da allowlist e sem declaracao — a ocorrencia que ja "
        "aconteceu quatro vezes",
        (SCRIPTS + ["check_novo"], LIDOS, LIBERADOS, DECLARADOS),
        "nao esta na allowlist do auditor e nao esta declarado fora",
    ),
    (
        "declaracao para script que nao existe mais",
        (SCRIPTS, LIDOS, LIBERADOS, DECLARADOS | {"check_sumiu": "motivo qualquer"}),
        "e esse script nao existe",
    ),
    (
        "declarado fora E liberado pelo matcher — a declaracao sobrando",
        (SCRIPTS, LIDOS | {"prova_alguma_coisa"}, LIBERADOS | {"prova_alguma_coisa"},
         DECLARADOS),
        "esta declarado FORA da allowlist e o matcher o libera",
    ),
    (
        "a leitura textual devolveu ZERO — o formato do hook mudou",
        (SCRIPTS, set(), LIBERADOS, DECLARADOS),
        "devolveu ZERO nomes",
    ),
    (
        "a leitura textual devolveu PARCIAL — tres de vinte passa igual a zero",
        (SCRIPTS, {"check_um"}, LIBERADOS, DECLARADOS),
        "DIVERGE do matcher real",
    ),
    (
        "a leitura textual encontrou nome que o matcher NAO libera",
        (SCRIPTS, LIDOS | {"check_fantasma"}, LIBERADOS, DECLARADOS),
        "DIVERGE do matcher real",
    ),
    (
        "controle: universo coerente",
        (SCRIPTS, LIDOS, LIBERADOS, DECLARADOS),
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
        print(f"FALHA: probe '{rotulo}': ausencia plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com ausencia plantada - {rotulo}")
    return True


def probe_leitura_do_hook_real() -> bool:
    """A leitura textual sobre o hook DE VERDADE, e nao sobre conjunto injetado.

    Os probes acima injetam estado; este exercita o regex contra o arquivo real.
    Sem ele, uma mudanca de formato no hook so apareceria na direcao (d) do
    verificador — que e o lugar certo, mas depois de o gate ja ter reprovado.
    """
    lidos = nomes_da_allowlist(HOOK.read_text(encoding="utf-8"))
    if len(lidos) < 30 or "phase0_negative_tests" not in lidos or "demo_fase2" not in lidos:
        print(f"FALHA: a leitura do hook real devolveu {len(lidos)} nomes: {sorted(lidos)[:8]}")
        return False
    print(f"OK: le {len(lidos)} nomes do hook real, do primeiro ao ultimo do grupo")
    return True


def probe_registro_tem_motivo() -> bool:
    """Entrada sem motivo e a mesma coisa que ausencia de entrada."""
    vazias = [nome for nome, motivo in FORA.items() if len(motivo.strip()) < 40]
    if vazias:
        print(f"FALHA: entradas sem motivo escrito: {vazias}")
        return False
    print(f"OK: as {len(FORA)} exclusoes declaradas tem motivo escrito")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1
    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_leitura_do_hook_real())
    resultados.append(probe_registro_tem_motivo())
    print()
    if all(resultados):
        print(
            f"check_allowlist_do_auditor.py reprova nos {len(resultados)} eixos: "
            "script sem declaracao, declaracao orfa, declaracao sobrando, leitura "
            "vazia, leitura PARCIAL, nome fantasma, o controle verde, a leitura do "
            "hook real e o motivo por entrada."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
