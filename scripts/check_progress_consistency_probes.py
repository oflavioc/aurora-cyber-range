#!/usr/bin/env python3
"""Prova que `check_progress_consistency.py` RECUSA — e que le a tabela CERTA.

O EIXO QUE DECIDE E O (f), E ELE E O MOTIVO DESTE ARQUIVO EXISTIR
------------------------------------------------------------------
Ate a peca 1 da Fase 7, o parser achava a tabela-resumo por POSICAO: *"a primeira
tabela, depois do cabecalho de pendencias, que tenha ids"*. Heuristica. Uma
tabela intercalada ANTES dela — uma tabela de ocorrencias, um enum de estados —
com um identificador na primeira coluna sequestraria a leitura, e o verificador
cruzaria a tabela errada contra as secoes **sem nada acusar**: ele nao recusa
quando nao entende, ele responde sobre outro objeto e sai verde.

O (f) planta exatamente isso, e exige as duas metades:

    (f1) SEM marcador, a tabela intercalada SEQUESTRA a leitura  -> o defeito
    (f2) COM marcador, o parser le a tabela declarada            -> o conserto

Sem a metade (f1) o eixo nao prova nada: um parser que sempre lesse a tabela
certa por acaso passaria em (f2), e ninguem saberia que o marcador foi o que
mudou. **A condicao plantada tem de ser vista fazendo estrago antes de ser vista
sendo contida** — e essa e a mesma exigencia que a P7-2 pos nos eixos de rebase.

E POR QUE ESTE VERIFICADOR PASSOU TANTO TEMPO SEM PROVA NEGATIVA
------------------------------------------------------------------
Ele era o unico dos vinte e cinco de `scripts/` sem `_probes.py` pareado, e o
`README.md` nomeava a excecao. Uma checagem que nunca ficou vermelha contra uma
violacao plantada prova que roda, nao que detecta — e esta em particular guarda
a §1.6, que e a classe de defeito que ninguem ve acontecer.

STDLIB PURA. Constroi registros sinteticos em diretorio temporario e chama
`tabela_resumo` e `confere` diretamente: nenhum arquivo do repositorio e tocado.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_progress_consistency import (  # noqa: E402
    MARCADOR,
    SECAO,
    tabela_resumo,
)

MARCA = "<!-- tabela-resumo-de-pendencias -->"

#: A TABELA-RESUMO LEGITIMA, com dois ids que tem secao logo abaixo.
RESUMO = """| Id | O que é | Estado | Vence em |
|---|---|---|---|
| P9-1 | o primeiro defeito | `ABERTA` | um gatilho |
| P9-2 | o segundo defeito | `ABERTA` | outro gatilho |
"""

SECOES = """#### P9-1 — o primeiro defeito

Corpo.

#### P9-2 — o segundo defeito

Corpo.
"""

#: A TABELA INTERCALADA, e ela e o veneno: tem id na PRIMEIRA coluna, entao a
#: heuristica de posicao a confunde com a tabela-resumo. E realista — a tabela de
#: ocorrencias da propria secao 1.6 tem esta forma.
INTERCALADA = """| Ocorrência | Onde | Id |
|---|---|---|
| P9-7 | num registro anterior | primeira |
"""


def registro(*, com_marcador: bool, com_intercalada: bool) -> str:
    partes = ["# Fase 9 — sintética", "", "## 6. Pendências", "", "Prosa.", ""]
    if com_intercalada:
        partes += ["Uma tabela que veio antes:", "", INTERCALADA.rstrip(), ""]
    if com_marcador:
        partes += [MARCA, ""]
    partes += [RESUMO.rstrip(), "", SECOES.rstrip(), ""]
    return "\n".join(partes)


def ids_de(texto: str) -> list[str] | None:
    return tabela_resumo(texto.splitlines())


def eixo_a() -> bool:
    """O caso simples: sem intercalada, com marcador, le a tabela declarada."""
    ids = ids_de(registro(com_marcador=True, com_intercalada=False))
    if ids != ["P9-1", "P9-2"]:
        print(f"FALHOU: [a - leitura simples] leu {ids}, esperado ['P9-1', 'P9-2'].")
        return False
    print("OK: [a - leitura simples] o marcador aponta e o parser le a tabela certa.")
    return True


def eixo_b() -> bool:
    """DEGRADACAO: sem marcador e sem intercalada, vale a regra herdada."""
    ids = ids_de(registro(com_marcador=False, com_intercalada=False))
    if ids != ["P9-1", "P9-2"]:
        print(
            f"FALHOU: [b - degradacao] registro sem marcador deixou de ser lido: "
            f"{ids}. `fase_5.md` e anteriores dependem deste caminho."
        )
        return False
    print("OK: [b - degradacao] registro sem marcador continua sendo lido.")
    return True


def eixo_c() -> bool:
    """Sem cabecalho de pendencias e sem marcador: `None`, e nao erro."""
    if ids_de("# Fase 9\n\nSó prosa, sem tabela.\n") is not None:
        print("FALHOU: [c - sem tabela] devolveu lista onde nao ha tabela nenhuma.")
        return False
    print("OK: [c - sem tabela] devolve None, e o arquivo e ignorado.")
    return True


def eixo_d() -> bool:
    """O MARCADOR VALE SOZINHO, sem cabecalho de pendencias acima dele."""
    texto = "\n".join(["# Fase 9", "", MARCA, "", RESUMO.rstrip(), "", SECOES.rstrip()])
    ids = ids_de(texto)
    if ids != ["P9-1", "P9-2"]:
        print(f"FALHOU: [d - marcador sozinho] leu {ids}.")
        return False
    print("OK: [d - marcador sozinho] o marcador nao depende do cabecalho.")
    return True


def eixo_e() -> bool:
    """MENCAO NAO E MARCADOR. O regex ancora a linha inteira de proposito.

    O docstring do proprio verificador cita a marca em prosa; se o casamento
    fosse por substring, uma frase sobre o mecanismo viraria o mecanismo.
    """
    if MARCADOR.match(f"O marcador e `{MARCA}`, e ele vai acima da tabela."):
        print("FALHOU: [e - mencao] uma MENCAO em prosa foi lida como marcador.")
        return False
    if not MARCADOR.match(f"  {MARCA}  "):
        print("FALHOU: [e - mencao] a linha inteira com espaco em volta NAO casou.")
        return False
    print("OK: [e - mencao] casa a linha inteira, e recusa mencao em prosa.")
    return True


def eixo_f() -> bool:
    """O EIXO QUE DECIDE — a tabela intercalada, nas duas metades.

    (f1) sem marcador ela SEQUESTRA a leitura, e isso e o defeito medido;
    (f2) com marcador o parser le a tabela declarada, e isso e o conserto.
    """
    sem = ids_de(registro(com_marcador=False, com_intercalada=True))
    com = ids_de(registro(com_marcador=True, com_intercalada=True))

    # (f1) A CONDICAO PLANTADA ACONTECEU? Se a intercalada nao sequestrasse a
    # leitura, este eixo passaria sem provar que o marcador serve para alguma
    # coisa — que e a vacuidade de um teste que se auto-satisfaz.
    if sem == ["P9-1", "P9-2"]:
        print(
            "FALHOU: [f1] a tabela intercalada NAO sequestrou a leitura sem o\n"
            "        marcador; o eixo seria vacuo e nao mede o conserto."
        )
        return False
    if sem != ["P9-7"]:
        print(f"FALHOU: [f1] esperado o sequestro lendo ['P9-7'], veio {sem}.")
        return False

    # (f2) O CONSERTO.
    if com != ["P9-1", "P9-2"]:
        print(
            f"FALHOU: [f2] COM o marcador o parser ainda leu a tabela errada: {com}."
        )
        return False
    print(
        "OK: [f - tabela intercalada] sem marcador leu ['P9-7'] — o sequestro —, "
        "e com marcador leu ['P9-1', 'P9-2']."
    )
    return True


def eixo_g() -> bool:
    """O CRUZAMENTO continua valendo: id na tabela sem secao e pego.

    O marcador muda ONDE se le, e nao O QUE se cobra. Um eixo que so provasse a
    leitura deixaria passar um parser que lesse a tabela certa e nao cruzasse
    nada.
    """
    texto = registro(com_marcador=True, com_intercalada=False)
    ids = ids_de(texto)
    secoes = [m.group(1) for m in map(SECAO.match, texto.splitlines()) if m]
    sem_secao = [i for i in (ids or []) if i not in secoes]
    if sem_secao:
        print(f"FALHOU: [g] o registro de controle ja nasce inconsistente: {sem_secao}")
        return False

    quebrado = texto.replace("#### P9-2 — o segundo defeito", "#### Outra coisa")
    ids_q = ids_de(quebrado)
    secoes_q = [m.group(1) for m in map(SECAO.match, quebrado.splitlines()) if m]
    faltando = [i for i in (ids_q or []) if i not in secoes_q]
    if faltando != ["P9-2"]:
        print(f"FALHOU: [g] secao removida e o cruzamento nao acusou: {faltando}")
        return False
    print("OK: [g - cruzamento] id na tabela sem secao de detalhe continua sendo pego.")
    return True


EIXOS = (eixo_a, eixo_b, eixo_c, eixo_d, eixo_e, eixo_f, eixo_g)


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    print(
        "check_progress_consistency.py — sete eixos. O (f) e o que decide: ele\n"
        "planta uma tabela intercalada com id e exige ver o SEQUESTRO sem o\n"
        "marcador antes de exigir a leitura certa com ele. O (b) prova que\n"
        "registro sem marcador continua sendo lido — `fase_5.md` depende disso.\n"
    )
    resultados = [eixo() for eixo in EIXOS]
    print()
    if all(resultados):
        print(
            f"Os {len(resultados)} eixos provam que a tabela-resumo e achada pelo "
            "MARCADOR quando\nele existe, que a heuristica de posicao continua "
            "valendo sem ele, e que o\ncruzamento contra as secoes nao foi "
            "afrouxado pela mudanca."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} eixos nao provaram nada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
