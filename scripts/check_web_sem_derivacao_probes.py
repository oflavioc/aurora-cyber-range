#!/usr/bin/env python3
"""Teste negativo de `check_web_sem_derivacao.py`.

Verificador que nunca reprovou contra violacao plantada nao e verificador — a
doutrina que a Fase 0 fixou em dezenove rodadas. Aqui cada uma das tres regras
tem um par: **o que ela pega** e **o que ela nao pode pegar**.

O SEGUNDO E O QUE FALTA NA MAIORIA DAS PROVAS NEGATIVAS. Uma regra que
reprovasse tudo passaria em toda linha da primeira coluna, e o cliente ficaria
impossivel de escrever — que e a outra forma de o gate estar errado.
`docs/process/WORKFLOW.md` classifica bloqueio indevido como defeito, e a
simetria esta aqui por isso.

A VACUIDADE TAMBEM E PROVADA. O verificador nasceu antes das tres telas, e a
armadilha dessa ordem e sair verde por nao ter o que olhar — a §7.3, a
verificacao que parece existir. Ha probe apontando o diretorio para um lugar
vazio e exigindo REPROVACAO.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_web_sem_derivacao as alvo  # noqa: E402

FALHAS: list[str] = []

FICTICIO = alvo.RAIZ / "range-core" / "web" / "probe.tsx"


def reprova(rotulo: str, fonte: str) -> None:
    problemas = alvo.varre(FICTICIO, fonte)
    if not problemas:
        FALHAS.append(f"NAO PEGOU: {rotulo}\n    {fonte.strip()}")
    else:
        print(f"OK: reprovou {rotulo}")


def libera(rotulo: str, fonte: str) -> None:
    problemas = alvo.varre(FICTICIO, fonte)
    if problemas:
        FALHAS.append(
            f"BLOQUEIO INDEVIDO: {rotulo}\n    {fonte.strip()}\n    "
            + problemas[0].replace("\n", "\n    ")
        )
    else:
        print(f"OK: liberou {rotulo}")


# -- regra 1: metodos de selecao, ordenacao e agregacao --------------------

reprova(
    "reordenar destaques",
    "const ordenados = estado.destaques.sort((a, b) => b.severidade - a.severidade);",
)
reprova(
    "expandir o agregado por filtro",
    "const visiveis = itens.filter((i) => i.ativa);",
)
reprova(
    "reimplementar o corte com slice",
    "const tres = lista.slice(0, 3);",
)
reprova(
    "recompor o indice por agregacao",
    "const saude = pesos.reduce((a, b) => a + b, 0);",
)
reprova("inverter a ordem", "linhas.reverse();")
reprova("escolher um item", "const pior = lista.find((i) => i.severidade === 10);")

# -- regra 2: as colecoes do payload so por `.map(` -------------------------

reprova(
    "colecao do payload consumida por metodo que nao e map",
    "estado.paineis.forEach(function (b) { pinta(b); });",
)
reprova(
    "timeline reordenada no console",
    "dados.entradas.sort(byTime);",
)

# -- regra 3: `.length` em comparacao --------------------------------------

reprova(
    "orcamento reimplementado por contagem",
    "if (estado.destaques.length > 3) { corta(); }",
)
reprova(
    "contagem comparada do outro lado",
    "if (3 < estado.destaques.length) { corta(); }",
)

# -- o outro lado: o que o renderizador PRECISA fazer ----------------------

libera(
    "pintar os destaques",
    'const linhas = estado.destaques.map((i) => "<li>" + i.rotulo + "</li>").join("");',
)
libera(
    "pintar os blocos com a contagem que o servidor mandou",
    'estado.paineis.map((b) => b.grupo + " " + b.ativos + "/" + b.total).join("");',
)
libera(
    "renderizar o agregado a partir do NUMERO do servidor",
    'if (estado.omitidos > 0) { linhas.push("+ " + estado.omitidos + " outros"); }',
)
libera(
    "usar length sem comparar",
    "const total = linhas.length;",
)
libera(
    "o indice, que chega pronto",
    "elemento.textContent = estado.indice_de_saude;",
)

# -- a vacuidade: diretorio sem cliente REPROVA ----------------------------

with tempfile.TemporaryDirectory() as vazio:
    original = alvo.WEB
    alvo.WEB = Path(vazio)
    try:
        if alvo.main() == 0:
            FALHAS.append(
                "NAO PEGOU: diretorio de cliente VAZIO passou verde.\n"
                "    Verificador que sai verde por nao ter o que olhar e a §7.3."
            )
        else:
            print("OK: reprovou diretorio de cliente vazio")
    finally:
        alvo.WEB = original

with tempfile.TemporaryDirectory() as fora:
    original = alvo.WEB
    alvo.WEB = Path(fora) / "nao-existe"
    try:
        if alvo.main() == 0:
            FALHAS.append("NAO PEGOU: diretorio de cliente AUSENTE passou verde.")
        else:
            print("OK: reprovou diretorio de cliente ausente")
    finally:
        alvo.WEB = original


if FALHAS:
    print("\n" + "\n\n".join(FALHAS), file=sys.stderr)
    raise SystemExit(1)

print(
    f"\ncheck_web_sem_derivacao.py reprova {len(alvo.PROIBIDOS)} metodos de "
    "selecao, ordenacao e agregacao, e libera o que o renderizador precisa."
)
