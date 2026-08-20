#!/usr/bin/env python3
"""Prova negativa de `00` §3.2: a checagem do insumo reprova contra violacao plantada.

Mesma doutrina de `check_store_read_surface_probes.py` e do harness da Fase 0 —
checagem que nunca reprovou prova que a arvore passa, nao que ela enxerga.

A VIOLACAO E PLANTADA EM COPIA, NUNCA NA ARVORE
-----------------------------------------------
Cada caso escreve uma copia mutada do modulo em diretorio temporario e aponta a
checagem para ela, pelo caminho opcional de CLI. Plantar no arquivo real e
restaurar depois e fragil pelo motivo obvio: falha no meio deixa a arvore suja, e
o resultado passa a mentir sobre o que foi verificado.

OS CASOS COBREM AS TRES EXIGENCIAS QUE A CHECAGEM AFIRMA
---------------------------------------------------------
A (1) pelo alias que resolve para o fluxo total e pela base trocada; a (2) pelo
campo que entra e pelo que some; a (3) pelas duas colocacoes que um segundo
montador teria — outra funcao no mesmo modulo, e outro arquivo da arvore.

O CASO DO SEGUNDO ARQUIVO E O QUE MAIS IMPORTA, e por isso ele monta uma ARVORE
inteira: e a forma em que o defeito aparece de verdade. Ninguem escreve um
segundo montador ao lado do primeiro, onde a regra esta escrita; escreve-se longe
dela, num modulo de computador, com o construtor parecendo conversao inocente.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_insumo_de_metrica import MODULO, main  # noqa: E402

#: `nome -> (trecho original, trecho plantado)`. Cada um casa exatamente uma vez.
CASOS: dict[str, tuple[str, str]] = {
    # (1) — o alias que a §3.2 bane por nome: resolve para o fluxo total, e o
    # fluxo inteiro o satisfaz.
    "tipo proprio vira alias de Sequence[Event]": (
        'EventosDeDeclaracao = NewType("EventosDeDeclaracao", tuple)',
        "EventosDeDeclaracao = Sequence[Event]",
    ),
    # (1) — a mesma exigencia pelo outro lado: continua sendo `NewType`, mas o
    # nome interno mente, e a mensagem de erro de tipo nomearia outra coisa.
    "NewType com nome interno diferente do da variavel": (
        'EventosDeVerificacao = NewType("EventosDeVerificacao", tuple)',
        'EventosDeVerificacao = NewType("EventosDeDeclaracao", tuple)',
    ),
    # (2) — o campo que da ao consumidor por onde buscar mais do que lhe foi
    # dado. E a forma exata do que a §3.2 bane: o store como objeto.
    "insumo ganha campo com o event store": (
        "    eventos: EventosDeDeclaracao\n    epoch: EscrituracaoDeEpoch",
        "    eventos: EventosDeDeclaracao\n    epoch: EscrituracaoDeEpoch\n"
        "    store: InMemoryEventStore",
    ),
    # (2) — a direcao inversa: escalar declarado que some. Sem o limiar, o
    # verificador de `TTIV` volta a consultar o pack.
    "escalar declarado some do insumo de verificacao": (
        "    limiar_de_calibracao: float\n",
        "",
    ),
    # (3) — segundo montador NO MESMO MODULO, fora de `monta`.
    "construtor invocado em outra funcao do modulo": (
        "def monta(",
        "def monta_o_lado_da_declaracao(fluxo, lados):\n"
        '    """Segundo montador com nome de conveniencia."""\n'
        "    return EventosDeDeclaracao(tuple(fluxo))\n"
        "\n"
        "\n"
        "def monta(",
    ),
}

#: (3) — O CASO QUE IMPORTA: o construtor invocado em OUTRO ARQUIVO da arvore.
#:
#: Nao ha por que plantar isto no modulo do insumo: quem escreve o segundo
#: montador nao o escreve ao lado da regra. Escreve-o num modulo de computador,
#: onde `EventosDeDeclaracao(fluxo)` passa por conversao inocente — e o
#: computador que o recebesse leria os dois lados do par com o tipo certo na
#: assinatura, que e o defeito da §3.2 na forma em que ele e invisivel.
COMPUTADOR_COM_MONTADOR = (
    "from range_core.metrics.insumo import EventosDeDeclaracao\n"
    "\n"
    "\n"
    "def computa_ttcd(fluxo):\n"
    '    """Monta o proprio insumo a partir do fluxo total — compila e roda."""\n'
    "    eventos = EventosDeDeclaracao(tuple(fluxo))\n"
    "    return len(eventos)\n"
)

#: O POSITIVO DO MESMO EIXO, e ele existe para a checagem nao passar por ser
#: cega a imports. Consumidor que IMPORTA o tipo para anotar — e nao o constroi —
#: e a forma normal e tem de PASSAR. Sem este caso, uma checagem que reprovasse
#: todo import passaria nos negativos e quebraria o primeiro computador de
#: verdade.
CONSUMIDOR_QUE_SO_ANOTA = (
    "from range_core.metrics.insumo import InsumoDeDeclaracao\n"
    "\n"
    "\n"
    "def computa_ttcd(insumo: InsumoDeDeclaracao) -> int:\n"
    '    """Recebe o insumo montado. Nao constroi tipo nenhum."""\n'
    "    return len(insumo.eventos)\n"
)


def _arvore_plantada(temporario: Path, vizinho: str) -> Path:
    """Copia o modulo real para `<raiz>/metrics/insumo.py` e poe um vizinho ao lado.

    A raiz varrida pela checagem acompanha o alvo — `alvo.parent.parent` —, entao
    esta e a arvore inteira que ela enxerga. Nada e escrito em `range-core/`.
    """
    raiz = temporario / "range-core-plantado"
    (raiz / "metrics").mkdir(parents=True)
    (raiz / "metrics" / "insumo.py").write_text(
        MODULO.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (raiz / "metrics" / "computador.py").write_text(vizinho, encoding="utf-8")
    return raiz / "metrics" / "insumo.py"


def probes_de_arvore() -> list[str]:
    """Os dois eixos que exigem um SEGUNDO arquivo: o negativo e o positivo."""
    falhas: list[str] = []

    with tempfile.TemporaryDirectory() as temporario:
        alvo = _arvore_plantada(Path(temporario) / "negativo", COMPUTADOR_COM_MONTADOR)
        if main([str(alvo)]) == 0:
            falhas.append("construtor invocado em OUTRO ARQUIVO da arvore: PASSOU")
        else:
            print("  reprovou como devia: construtor invocado em outro arquivo da arvore")

    with tempfile.TemporaryDirectory() as temporario:
        alvo = _arvore_plantada(Path(temporario) / "positivo", CONSUMIDOR_QUE_SO_ANOTA)
        if main([str(alvo)]) != 0:
            falhas.append(
                "consumidor que so IMPORTA e anota foi reprovado. A checagem "
                "confunde import com construcao, e o primeiro computador de "
                "verdade nao compilaria sob ela."
            )
        else:
            print("  passou como devia: consumidor que importa o tipo e nao o constroi")

    return falhas


def main_probes() -> int:
    original = MODULO.read_text(encoding="utf-8")
    falhas: list[str] = []

    with tempfile.TemporaryDirectory() as temporario:
        for nome, (alvo, plantado) in CASOS.items():
            ocorrencias = original.count(alvo)
            if ocorrencias != 1:
                falhas.append(
                    f"{nome}: o trecho alvo casou {ocorrencias} vezes, e precisa "
                    "casar uma. A fonte mudou de forma e o probe deixou de plantar "
                    "o que diz."
                )
                continue

            raiz = Path(temporario) / nome.replace(" ", "_") / "metrics"
            raiz.mkdir(parents=True)
            copia = raiz / "insumo.py"
            copia.write_text(original.replace(alvo, plantado), encoding="utf-8")

            if main([str(copia)]) == 0:
                falhas.append(f"{nome}: violacao plantada e a checagem PASSOU")
            else:
                print(f"  reprovou como devia: {nome}")

    falhas.extend(probes_de_arvore())

    if main([]) != 0:
        falhas.append("a arvore limpa reprova — a checagem esta quebrada, nao a arvore")

    if falhas:
        for falha in falhas:
            print(f"PROVA NEGATIVA FALHOU: {falha}", file=sys.stderr)
        return 1

    print(
        f"{len(CASOS) + 1} violacoes plantadas, {len(CASOS) + 1} reprovadas; "
        "o consumidor que so anota passa, e a arvore limpa passa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
