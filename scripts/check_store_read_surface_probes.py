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


#: SUBCLASSE INDIRETA — o eixo que faltava, e o argumento de ele existir.
#:
#: A checagem casava `bases` por nome contra `EventStore` e parava ai: uma classe
#: `class X(InMemoryEventStore)` nao casava e podia acrescentar `read_since`
#: publico sem reprovar. Era o L2 da auditoria de 16/08/2026.
#:
#: E o MESMO buraco que o eixo de subclasse ja tinha fechado um nivel acima —
#: antes dele, so a classe base era conferida. Fechar um nivel de cada vez e o
#: que faz o buraco voltar com outro nome; por isso a checagem passou a usar
#: fecho TRANSITIVO, e por isso este probe herda em DOIS saltos.
DESCENDENTE_INDIRETO = (
    "from range_core.events.store import InMemoryEventStore\n"
    "\n"
    "\n"
    "class StoreEspiao(InMemoryEventStore):\n"
    '    """Dois saltos de heranca: EventStore -> InMemoryEventStore -> aqui."""\n'
    "\n"
    "    def read_since(self, cursor: str):\n"
    '        """Leitura parcial — exatamente o que a 01 secao 4.1 proibe."""\n'
    "        raise NotImplementedError\n"
)


def probe_de_subclasse_indireta() -> list[str]:
    """Monta uma ARVORE de core em diretorio temporario, e nao um arquivo so.

    Os demais probes plantam num arquivo e passam o caminho dele. Este precisa de
    DOIS arquivos — o store e o descendente —, porque a violacao so existe na
    relacao entre eles. Nada e escrito em `range-core/`.
    """
    falhas: list[str] = []
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario) / "range-core-plantado"
        (raiz / "events").mkdir(parents=True)
        (raiz / "events" / "store.py").write_text(
            STORE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (raiz / "events" / "espiao.py").write_text(DESCENDENTE_INDIRETO, encoding="utf-8")

        if main([str(raiz / "events" / "store.py")]) == 0:
            falhas.append("subclasse INDIRETA com metodo de leitura nao declarado: PASSOU")
        else:
            print("  reprovou como devia: subclasse indireta (dois saltos de heranca)")
    return falhas


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

    falhas.extend(probe_de_subclasse_indireta())

    if main([]) != 0:
        falhas.append("a arvore limpa reprova — a checagem esta quebrada, nao a arvore")

    if falhas:
        for falha in falhas:
            print(f"PROVA NEGATIVA FALHOU: {falha}", file=sys.stderr)
        return 1

    print(f"{len(CASOS) + 1} violacoes plantadas, {len(CASOS) + 1} reprovadas; "
          "arvore limpa passa. O eixo a mais e a subclasse indireta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
