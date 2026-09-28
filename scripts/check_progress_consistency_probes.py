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
    confere_gatilhos,
    confere_pauta,
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


# --------------------------------------------------------------------------
# A PAUTA HERDADA — todo item nao-fechado da fase N aparece na tabela da N+1.
#
# O defeito real esta morto pelos dois rebases desta fase: `e571091` abriu a
# branch da Fase 7 sem cinco pendencias da Fase 6, e nenhum gate viu. Os eixos
# abaixo o reconstroem sinteticamente, e o (h) tem as duas metades pela mesma
# razao do (f): ver a omissao SER PEGA nao prova nada se o caso verde tambem
# reprovar, e ver o verde passar nao prova nada se a omissao passar junto.
# --------------------------------------------------------------------------
def _registro(
    itens: list[tuple[str, str]],
    *,
    com_estado: bool = True,
    concluida: bool = False,
) -> list[str]:
    """Um registro de fase sintetico, com tabela-resumo declarada e secoes.

    `concluida` planta a LINHA DE STATUS de fechamento que `esta_concluida` le —
    e o que o eixo_l precisa para distinguir uma fase que fechou de uma aberta.
    """
    cabeca = ["# Fase sintética", ""]
    if concluida:
        cabeca += ["**Status: AUDITADA — PASS (2ª rodada).**", ""]
    cabeca += ["## 6. Pendências", "", MARCA, ""]
    if com_estado:
        cabeca += ["| Id | O que é | Estado | Vence em |", "|---|---|---|---|"]
        # `vencimento` por item quando ele vem na tupla de tres — o eixo (m)
        # precisa escrever "Fase N" no VENCIMENTO, e nao um gatilho genérico.
        cabeca += [
            f"| {t[0]} | o defeito | `{t[1]}` | {t[2] if len(t) > 2 else 'um gatilho'} |"
            for t in itens
        ]
    else:
        cabeca += ["| Id | O que é | Vence em |", "|---|---|---|"]
        cabeca += [
            f"| {t[0]} | o defeito | {t[2] if len(t) > 2 else 'um gatilho'} |"
            for t in itens
        ]
    corpo = [""]
    for t in itens:
        corpo += [f"#### {t[0]} — o defeito", "", "Corpo.", ""]
    return "\n".join(cabeca + corpo).splitlines()


def eixo_h() -> bool:
    """A OMISSAO, nas duas metades — e este eixo e a entrega da peca 1."""
    aberta_omitida = {
        6: _registro([("P8-1", "ABERTA"), ("P8-2", "RESOLVIDA")]),
        7: _registro([("P8-2", "RESOLVIDA")]),
    }
    falhas, _ = confere_pauta(aberta_omitida)

    # (h1) A OMISSAO E PEGA.
    if len(falhas) != 1 or "P8-1" not in falhas[0]:
        print(f"FALHOU: [h1] a omissao de `P8-1` NAO foi pega: {falhas}")
        return False
    if "P8-2" in falhas[0]:
        print("FALHOU: [h1] cobrou `P8-2`, que esta RESOLVIDA e nao migra.")
        return False

    # (h2) O CASO VERDE PASSA. Sem esta metade, um verificador que reprovasse
    # todo par passaria em (h1) sem distinguir nada.
    transcrita = {
        6: _registro([("P8-1", "ABERTA"), ("P8-2", "RESOLVIDA")]),
        7: _registro([("P8-1", "ABERTA")]),
    }
    falhas_verde, _ = confere_pauta(transcrita)
    if falhas_verde:
        print(f"FALHOU: [h2] o par COMPLETO foi reprovado: {falhas_verde}")
        return False

    print(
        "OK: [h - pauta herdada] a omissao de `P8-1` foi pega, `P8-2` RESOLVIDA "
        "nao foi cobrada, e o par completo passou."
    )
    return True


def eixo_i() -> bool:
    """Os quatro estados nao-fechados sao cobrados; `ENTREGA` nao."""
    nao_fechados = [("P8-1", "ABERTA"), ("P8-2", "LATENTE"),
                    ("P8-3", "DECIDIDA"), ("P8-4", "VENCIDA")]
    falhas, _ = confere_pauta({
        6: _registro(nao_fechados + [("P8-5", "ENTREGA")]),
        7: _registro([("P8-9", "ABERTA")]),
    })
    cobrados = {i for i, _ in nao_fechados if any(f"`{i}`" in f for f in falhas)}
    if cobrados != {i for i, _ in nao_fechados}:
        print(f"FALHOU: [i] nem todo estado nao-fechado foi cobrado: {cobrados}")
        return False
    if any("P8-5" in f for f in falhas):
        print("FALHOU: [i] `ENTREGA` foi cobrada, e ela e trabalho da propria fase.")
        return False
    print("OK: [i - estados] os quatro nao-fechados sao cobrados, `ENTREGA` nao.")
    return True


def eixo_j() -> bool:
    """ESTADO FORA DO ENUM REPROVA, e nao e ignorado em silencio."""
    falhas, _ = confere_pauta({
        6: _registro([("P8-1", "TALVEZ")]),
        7: _registro([("P8-9", "ABERTA")]),
    })
    if not any("fora do enum" in f and "TALVEZ" in f for f in falhas):
        print(f"FALHOU: [j] estado desconhecido nao reprovou: {falhas}")
        return False
    print("OK: [j - enum fechado] estado fora do vocabulario reprova, nomeando-o.")
    return True


def eixo_k() -> bool:
    """AS DUAS DEGRADACOES SAO PULO COM RAZAO, e nunca falha silenciosa."""
    # Sem a fase seguinte.
    falhas, pulos = confere_pauta({6: _registro([("P8-1", "ABERTA")])})
    if falhas:
        print(f"FALHOU: [k] reprovou por nao existir a fase seguinte: {falhas}")
        return False
    if not any("nao existe" in p for p in pulos):
        print(f"FALHOU: [k] pulou sem dizer que a fase seguinte nao existe: {pulos}")
        return False

    # Sem coluna de estado — `fase_5.md` e anteriores.
    falhas2, pulos2 = confere_pauta({
        6: _registro([("P8-1", "ABERTA")], com_estado=False),
        7: _registro([("P8-9", "ABERTA")]),
    })
    if falhas2:
        print(f"FALHOU: [k] reprovou tabela de tres colunas: {falhas2}")
        return False
    if not any("nao declara coluna de estado" in p for p in pulos2):
        print(f"FALHOU: [k] pulou sem dizer que falta a coluna: {pulos2}")
        return False

    print("OK: [k - degradacao] as duas rotas pulam com a razao dita, e nao reprovam.")
    return True


# --------------------------------------------------------------------------
# P7-19 — `ENTREGA` numa fase CONCLUIDA reprova.
#
# `ENTREGA` e trabalho da propria fase: nao migra, e a Definition of Done a
# cobra. Mas a DoD e humana, nao um gate — entao uma fase que FECHA com uma
# linha ainda `ENTREGA` a faz sumir: nao foi entregue, nao migra, nao esta em
# nenhuma checagem. Foi o H3 da 2a auditoria da Fase 7: P1-7, P5-4 e P6-5
# escaparam assim. Como o (f) e o (h), o eixo tem as metades — a condicao tem
# de ser vista fazendo estrago (fase fechada COM `ENTREGA` reprova) antes de ser
# vista contida (a mesma fechada, com a linha ja `RESOLVIDA`, passa) — e uma
# terceira perna que prende a guarda no Status, e nao no estado: fase ABERTA com
# `ENTREGA` e legitima e nao pode reprovar.
# --------------------------------------------------------------------------
def eixo_l() -> bool:
    """`ENTREGA` numa fase CONCLUIDA reprova; contida e aberta, nao."""
    def cobrada_por_conclusao(falhas: list[str], item: str) -> bool:
        return any(f"`{item}`" in f and "CONCLUIDA" in f for f in falhas)

    # (l1) A CONDICAO FAZENDO ESTRAGO: fase fechada com a linha ainda `ENTREGA`.
    fechada_com_entrega = {
        6: _registro([("P8-1", "ENTREGA"), ("P8-2", "RESOLVIDA")], concluida=True),
    }
    falhas, _ = confere_pauta(fechada_com_entrega)
    if not cobrada_por_conclusao(falhas, "P8-1"):
        print(f"FALHOU: [l1] `ENTREGA` numa fase CONCLUIDA nao foi pega: {falhas}")
        return False
    if cobrada_por_conclusao(falhas, "P8-2"):
        print("FALHOU: [l1] cobrou `P8-2`, que ja esta RESOLVIDA e fechou certo.")
        return False

    # (l2) A CONDICAO CONTIDA: a mesma fase fechada, a linha virou `RESOLVIDA`.
    # Sem esta metade, uma guarda que reprovasse toda fase concluida passaria em
    # (l1) sem provar que foi o `ENTREGA` que pesou.
    fechada_curada = {
        6: _registro([("P8-1", "RESOLVIDA"), ("P8-2", "RESOLVIDA")], concluida=True),
    }
    falhas_ok, _ = confere_pauta(fechada_curada)
    if falhas_ok:
        print(f"FALHOU: [l2] a fase fechada e curada foi reprovada: {falhas_ok}")
        return False

    # (l3) A GUARDA CASA O STATUS, NAO O ESTADO: fase ABERTA com `ENTREGA` e o
    # caso legitimo — trabalho em andamento da propria fase — e nao pode reprovar.
    aberta_com_entrega = {
        6: _registro([("P8-1", "ENTREGA")]),
        7: _registro([("P8-9", "ABERTA")]),
    }
    falhas_aberta, _ = confere_pauta(aberta_com_entrega)
    if any("CONCLUIDA" in f for f in falhas_aberta):
        print(f"FALHOU: [l3] `ENTREGA` numa fase ABERTA foi cobrada: {falhas_aberta}")
        return False

    print(
        "OK: [l - entrega no fechamento] `ENTREGA` numa fase CONCLUIDA reprova, "
        "curada nao, e numa fase aberta continua legitima."
    )
    return True


def eixo_m() -> bool:
    """A VARREDURA DE GATILHO — P9-1, e as tres pernas que a definem.

    O defeito que ela fecha: gatilho escrito numa fase de tabela ANTIGA (tres
    colunas, sem estado) nao tinha quem o cobrasse, porque `confere_pauta` pula
    essa fase inteira. Foi assim que P1-3, P1-13 e P2-11 prometeram a Fase 9 e
    nao constavam da tabela da Fase 8.
    """
    # (m1) A PROMESSA VIVA QUE NAO CHEGA E PEGA — e a fase de origem e de TRES
    # colunas, que e exatamente onde `confere_pauta` e cego.
    orfa = {
        2: _registro([("P2-11", "", "**Fase 9**")], com_estado=False),
        9: _registro([("P9-1", "ABERTA")]),
    }
    falhas = confere_gatilhos(orfa)
    if len(falhas) != 1 or "P2-11" not in falhas[0]:
        print(f"FALHOU: [m1] o gatilho orfao NAO foi pego: {falhas}")
        return False

    # (m2) O CASO VERDE PASSA. Sem esta perna, um verificador que reprovasse
    # todo gatilho passaria em (m1) sem distinguir nada.
    chegou = {
        2: _registro([("P2-11", "", "**Fase 9**")], com_estado=False),
        9: _registro([("P2-11", "ABERTA"), ("P9-1", "ABERTA")]),
    }
    if confere_gatilhos(chegou):
        print(f"FALHOU: [m2] o gatilho que CHEGOU foi reprovado: {confere_gatilhos(chegou)}")
        return False

    # (m3) DESTINO FECHADO NAO E COBRADO, e a razao e que a pergunta e
    # inconclusiva: ausencia na tabela de la pode ser RESOLUCAO. Cobrar aqui
    # transformaria 42 casos historicos em falha permanente, e a saida seria uma
    # lista de excecao que nunca encolhe.
    fechado = {
        2: _registro([("P2-11", "", "**Fase 9**")], com_estado=False),
        9: _registro([("P9-1", "ABERTA")], concluida=True),
    }
    if confere_gatilhos(fechado):
        print("FALHOU: [m3] cobrou gatilho de destino CONCLUIDO, que e inconclusivo.")
        return False

    print(
        "OK: [m - varredura de gatilho] a promessa viva que nao chega e pega "
        "mesmo em tabela de tres colunas, a que chega passa, e destino concluido "
        "nao e cobrado."
    )
    return True


EIXOS = (eixo_a, eixo_b, eixo_c, eixo_d, eixo_e, eixo_f, eixo_g,
         eixo_h, eixo_i, eixo_j, eixo_k, eixo_l, eixo_m)


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    print(
        "check_progress_consistency.py — doze eixos, em tres perguntas.\n"
        "\n"
        "  (a)-(g)  a tabela-resumo e achada e cruzada contra as secoes. O (f)\n"
        "           decide: planta uma tabela intercalada com id e exige ver o\n"
        "           SEQUESTRO sem o marcador antes da leitura certa com ele.\n"
        "  (h)-(k)  a pauta herdada migra. O (h) decide, e tem as duas metades:\n"
        "           a omissao e pega, E o par completo passa.\n"
        "  (l)      `ENTREGA` numa fase CONCLUIDA reprova — o H3 da 2a auditoria\n"
        "           da Fase 7 (P7-19). Tres pernas: estrago, contida, e a guarda\n"
        "           presa no Status e nao no estado.\n"
    )
    resultados = [eixo() for eixo in EIXOS]
    print()
    if all(resultados):
        print(
            f"Os {len(resultados)} eixos provam que a tabela-resumo e achada pelo "
            "MARCADOR quando ele\nexiste, que a heuristica de posicao continua "
            "valendo sem ele, que o cruzamento\ncontra as secoes nao foi "
            "afrouxado, que pendencia nao-fechada que nao migra\npara a fase "
            "seguinte e PEGA — sem que o par completo seja reprovado junto —, e "
            "que\n`ENTREGA` numa fase CONCLUIDA reprova sem cobrar a fase aberta."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} eixos nao provaram nada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
