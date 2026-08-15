#!/usr/bin/env python3
"""Prova negativa da P2-2: a checagem reprova contra violacao plantada.

Mesma doutrina de `scripts/check_contract_examples_probes.py` e do harness da
Fase 0 — checagem que nunca reprovou prova que a arvore passa, nao que ela
enxerga.

A VIOLACAO E PLANTADA EM COPIA, NUNCA NA ARVORE
-----------------------------------------------
Cada caso escreve uma copia mutada do store em diretorio temporario e aponta a
checagem para ela, pelo caminho opcional de CLI. Plantar no arquivo real e
restaurar depois e fragil pelo motivo obvio: falha no meio deixa a arvore suja,
e o resultado passa a mentir sobre o que foi verificado.

OS QUATRO CASOS COBREM AS DUAS ASSERCOES
----------------------------------------
Os dois primeiros atacam "leitura sem parametro"; os dois ultimos, o whitelist
da superficie — que e a metade que segura o futuro, porque pega o metodo que
ninguem previu.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_store_read_surface import STORE_PATH, main  # noqa: E402

#: `nome -> (trecho original, trecho plantado)`. Cada um casa exatamente uma vez.
CASOS: dict[str, tuple[str, str]] = {
    "read_all com parametro posicional": (
        "def read_all(self) -> Sequence[Event]:",
        "def read_all(self, since: str | None = None) -> Sequence[Event]:",
    ),
    "read_all com **kwargs": (
        "def read_all(self) -> Sequence[Event]:",
        "def read_all(self, **kwargs) -> Sequence[Event]:",
    ),
    "metodo publico de leitura nao declarado": (
        "    def read_all(self) -> Sequence[Event]:",
        "    def read_since(self, cursor: str) -> Sequence[Event]:\n"
        '        """Leitura parcial — exatamente o que a §4.1 proibe."""\n'
        "        raise NotImplementedError\n\n"
        "    def read_all(self) -> Sequence[Event]:",
    ),
    "metodo declarado desaparece da classe": (
        "    def append(self, draft: EventDraft) -> Event:",
        "    def _append(self, draft: EventDraft) -> Event:",
    ),
}


def main_probes() -> int:
    original = STORE_PATH.read_text(encoding="utf-8")
    falhas: list[str] = []

    with tempfile.TemporaryDirectory() as temporario:
        for nome, (alvo, plantado) in CASOS.items():
            ocorrencias = original.count(alvo)
            if ocorrencias != 1:
                falhas.append(
                    f"{nome}: o trecho alvo casou {ocorrencias} vezes, e precisa casar "
                    "uma. A fonte mudou de forma e o probe deixou de plantar o que diz."
                )
                continue

            copia = Path(temporario) / "store_mutado.py"
            copia.write_text(original.replace(alvo, plantado), encoding="utf-8")

            if main([str(copia)]) == 0:
                falhas.append(f"{nome}: violacao plantada e a checagem PASSOU")
            else:
                print(f"  reprovou como devia: {nome}")

    if main([]) != 0:
        falhas.append("a arvore limpa reprova — a checagem esta quebrada, nao a arvore")

    if falhas:
        for falha in falhas:
            print(f"PROVA NEGATIVA FALHOU: {falha}", file=sys.stderr)
        return 1

    print(f"{len(CASOS)} violacoes plantadas, {len(CASOS)} reprovadas; arvore limpa passa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
