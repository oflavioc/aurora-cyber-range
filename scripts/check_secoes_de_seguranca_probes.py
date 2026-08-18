#!/usr/bin/env python3
"""Prova que `check_secoes_de_seguranca.py` REPROVA contra registro plantado.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina da
Fase 0, repetida por todo `*_probes.py` deste repositorio.

POR QUE OS PROBES INJETAM O ESTADO INTEIRO
-------------------------------------------
Os defeitos que esta checagem pega sao sobre coisas que **nao existem na arvore**:
uma secao nova em `05`, uma entrada para secao removida, um verificador que passou
a citar uma secao que o registro diz estar esperando fase futura. Plantar cada um
exigiria editar a spec — que e proibido fora de `spec-change` — ou escrever um
verificador falso no disco. `verifica()` recebe os cinco conjuntos por parametro
justamente para nao precisar de nenhum dos dois.

O RISCO DESSA ESCOLHA, e o que o fecha: estado injetado nao exercita a LEITURA —
o parser de secoes de `05`, o de fases de `07` e o regex de citacao. Por isso ha
tres probes de leitura sobre os arquivos REAIS, e o mais importante deles e o da
citacao: se o regex parasse de casar, todo mecanismo declarado passaria a nao
citar a secao e a checagem reprovaria alto, em vez de aprovar em silencio. Esta
provado nas duas direcoes — casa o que deve e nao casa o que nao deve.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_secoes_de_seguranca import (  # noqa: E402
    FASES,
    MECANISMOS,
    SPEC,
    Entrada,
    citacoes,
    fases_de_07,
    main,
    secoes_da_spec,
    verifica,
)

SECOES = secoes_da_spec(SPEC.read_text(encoding="utf-8"))
FASES_DE_07 = fases_de_07(FASES.read_text(encoding="utf-8"))

#: O estado real, reconstruido para servir de base aos probes: cada mecanismo
#: declarado cita a sua secao, e o universo e exatamente o declarado.
CITADO_POR = {
    caminho: {numero}
    for numero, entrada in MECANISMOS.items()
    for caminho in entrada.mecanismos
}
VERSIONADOS = set(CITADO_POR) | {"scripts/check_novo.py"}
UNIVERSO = {c for c in CITADO_POR if c.startswith(("tools/", "scripts/"))}


def _base() -> tuple:
    """Os cinco conjuntos no estado que a arvore de fato tem."""
    return (
        dict(SECOES),
        dict(MECANISMOS),
        {k: set(v) for k, v in CITADO_POR.items()},
        set(VERSIONADOS),
        set(UNIVERSO),
        set(FASES_DE_07),
    )


def probe_secao_nova_sem_entrada() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    secoes[9] = "Retencao de dados de exercicio"
    return (secoes, registro, citado, vers, univ, fases), "nao tem entrada em"


def probe_entrada_para_secao_removida() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    del secoes[7]
    return (secoes, registro, citado, vers, univ, fases), "a spec nao tem essa secao"


def probe_titulo_divergente() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    secoes[6] = "Deploy e operacao"
    return (secoes, registro, citado, vers, univ, fases), "precisa ser RELIDA"


def probe_mecanismo_que_nao_cita() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    citado["tools/check_security_constraints.py"] = set()
    return (secoes, registro, citado, vers, univ, fases), "NAO cita a secao"


def probe_mecanismo_nao_versionado() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    vers.discard("tools/check_synthetic_data.py")
    return (secoes, registro, citado, vers, univ, fases), "nao esta versionado"


def probe_promocao_que_faltou() -> tuple:
    """O EIXO QUE ESTA FASE VAI EXERCER DE VERDADE, nas pecas 3 e 5.

    Um verificador novo passa a citar `05` §7 e a entrada continua dizendo
    "Fase 5, sem mecanismo". E a terceira direcao de `api_surface.yaml`: assim
    que o mecanismo nasce, a entrada tem de ser promovida no mesmo commit.
    """
    secoes, registro, citado, vers, univ, fases = _base()
    citado["scripts/check_novo.py"] = {7}
    univ.add("scripts/check_novo.py")
    return (secoes, registro, citado, vers, univ, fases), "e a promocao que esta faltando"


def probe_citacao_nao_declarada() -> tuple:
    """A mesma direcao (d) sobre secao JA coberta: mecanismo novo nao declarado."""
    secoes, registro, citado, vers, univ, fases = _base()
    citado["scripts/check_novo.py"] = {1}
    univ.add("scripts/check_novo.py")
    return (
        (secoes, registro, citado, vers, univ, fases),
        "nao esta declarado como mecanismo",
    )


def probe_sem_mecanismo_e_sem_destinatario() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    registro[6] = Entrada(
        titulo=SECOES[6], mecanismos=(), destinatario=None, nota="—"
    )
    return (
        (secoes, registro, citado, vers, univ, fases),
        "nao tem mecanismo nem destinatario",
    )


def probe_destinatario_para_fase_inexistente() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    registro[7] = Entrada(
        titulo=SECOES[7],
        mecanismos=(),
        destinatario=(99, "quando der"),
        nota="—",
    )
    return (
        (secoes, registro, citado, vers, univ, fases),
        "`07` nao declara essa fase",
    )


def probe_destinatario_sem_motivo() -> tuple:
    secoes, registro, citado, vers, univ, fases = _base()
    registro[7] = Entrada(
        titulo=SECOES[7], mecanismos=(), destinatario=(5, "   "), nota="—"
    )
    return (
        (secoes, registro, citado, vers, univ, fases),
        "destinatario sem motivo",
    )


def probe_controle_verde() -> tuple:
    """O estado real nao pode acusar nada. Sem este, os outros nao provam eixo."""
    return _base(), None  # `None` = este probe passa, e nao reprova


PROBES = [
    ("secao nova em `05` sem entrada no registro", probe_secao_nova_sem_entrada),
    ("entrada para secao que a spec removeu", probe_entrada_para_secao_removida),
    ("titulo que divergiu do da spec", probe_titulo_divergente),
    ("mecanismo declarado que nao cita a secao", probe_mecanismo_que_nao_cita),
    ("mecanismo declarado que nao esta versionado", probe_mecanismo_nao_versionado),
    ("verificador novo cita secao que espera fase futura", probe_promocao_que_faltou),
    ("verificador novo cita secao coberta, sem declaracao", probe_citacao_nao_declarada),
    ("entrada sem mecanismo e sem destinatario", probe_sem_mecanismo_e_sem_destinatario),
    ("destinatario para fase que `07` nao tem", probe_destinatario_para_fase_inexistente),
    ("destinatario sem motivo", probe_destinatario_sem_motivo),
    ("controle: o estado real da arvore", probe_controle_verde),
]


def roda(rotulo: str, monta) -> bool:
    argumentos, esperado = monta()
    problemas = verifica(*argumentos)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': estado plantado e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou, mas nao pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com estado plantado - {rotulo}")
    return True


def probe_leitura_das_secoes() -> bool:
    """A leitura real de `05`: oito secoes, e a §7 entre elas."""
    if len(SECOES) != 8 or SECOES.get(7) != "Integridade da trilha de auditoria":
        print(f"FALHA: a leitura de `05` devolveu {sorted(SECOES)} — a forma mudou")
        return False
    print("OK: le as oito secoes de `05` da propria spec")
    return True


def probe_leitura_das_fases() -> bool:
    if not {1, 5, 12} <= FASES_DE_07:
        print(f"FALHA: a leitura de `07` devolveu {sorted(FASES_DE_07)}")
        return False
    print("OK: le os numeros de fase da tabela de `07`")
    return True


def probe_regex_de_citacao() -> bool:
    """As DUAS direcoes do regex, e a segunda e a que evita falso positivo.

    Se ele parasse de casar, todo mecanismo declarado viraria "nao cita a secao"
    e a checagem reprovaria alto — falha fechada. Se casasse demais, o registro
    exigiria declaracao por citacao de OUTRO documento, e ai o custo seria ruido
    ate alguem aprender a ignorar a checagem.
    """
    casos_positivos = [
        ("05_SECURITY_REQUIREMENTS.md secao 1", {1}),
        ("`05` §4", {4}),
        ("05 secao 5.1: vendor/product", {5}),
        ("05_SECURITY_REQUIREMENTS §6", {6}),
        ("`05_SECURITY_REQUIREMENTS.md` §7, entregue na", {7}),
    ]
    casos_negativos = [
        "02_DOMAIN_ACADEMUS.md §4",
        "`01` §7 proibe varredura",
        "o ano de 2005 secao 3 do relatorio",
        "05_SECURITY_REQUIREMENTS.md sem numero nenhum",
    ]
    for texto, esperado in casos_positivos:
        if citacoes(texto) != esperado:
            print(f"FALHA: {texto!r} devia citar {esperado}, deu {citacoes(texto)}")
            return False
    for texto in casos_negativos:
        if citacoes(texto):
            print(f"FALHA: {texto!r} nao devia casar, e casou {citacoes(texto)}")
            return False
    print("OK: o regex de citacao casa as cinco formas reais e recusa as quatro falsas")
    return True


def arvore_limpa() -> bool:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return False
    return True


def main_probes() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda(rotulo, monta) for rotulo, monta in PROBES]
    resultados.append(probe_leitura_das_secoes())
    resultados.append(probe_leitura_das_fases())
    resultados.append(probe_regex_de_citacao())
    print()
    if all(resultados):
        print(
            f"check_secoes_de_seguranca.py reprova nos {len(resultados)} eixos: as "
            "cinco direcoes com estado plantado, o controle verde, e as tres "
            "leituras reais — secoes de `05`, fases de `07` e o regex de citacao "
            "nas duas direcoes."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
