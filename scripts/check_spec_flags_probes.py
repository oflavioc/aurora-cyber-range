#!/usr/bin/env python3
"""Prova que `check_spec_flags.py` REPROVA contra divergencia plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina da
Fase 0, repetida por todo `*_probes.py` deste repositorio.

POR QUE OS PROBES INJETAM OS TRES CONJUNTOS
--------------------------------------------
Os defeitos aqui sao sobre estados que nao existem na arvore: uma flag citada e
nao declarada, uma entrada de pendente que sobrou, outra que a spec deixou de
citar. Planta-los de verdade exigiria editar `docs/spec/` — que e o documento
imutavel durante a implementacao — e `domains/`, sujando a arvore para testar.

`verifica()` recebe os tres conjuntos por parametro exatamente para isso.

O RISCO DESSA ESCOLHA, e o que o fecha: conjunto injetado nao exercita a
VARREDURA. O sexto probe cobre esse eixo, plantando a citacao num diretorio de
spec temporario e conferindo que `citadas()` a encontra — sem tocar em
`docs/spec/`.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_spec_flags import (  # noqa: E402
    adapters,
    citadas,
    declaradas,
    main,
    pendentes,
    verifica,
)

#: Nomes de flag SINTETICOS. Nao usam prefixo de adapter existente de proposito:
#: `<adapter>.<nome>` nao declarado dentro de um `.py` e literal que
#: `tools/check_contract_literals.py` recusa — foi o que barrou a primeira versao
#: da lista de pendentes. O que os probes exercitam e a LOGICA, e ela nao olha o
#: prefixo.
CITADA = "fixture.flag_citada"
DECLARADA = "fixture.flag_declarada"

ONDE = ["07_IMPLEMENTATION_PHASES.md:1"]

#: `(rotulo, citadas, declaradas, pendentes, trecho esperado)`
PROBES = [
    (
        "flag citada na spec e nao declarada em lugar nenhum",
        {CITADA: ONDE},
        set(),
        {},
        "NAO declarada",
    ),
    (
        "entrada de pendente que ja foi declarada no adapter",
        {CITADA: ONDE},
        {CITADA},
        {CITADA: "alguem, Fase 11"},
        "A entrada sobrou",
    ),
    (
        "entrada de pendente que a spec deixou de citar",
        {},
        set(),
        {CITADA: "alguem, Fase 11"},
        "a spec nao diz",
    ),
    (
        "flag declarada e citada: nada a acusar",
        {DECLARADA: ONDE},
        {DECLARADA},
        {},
        None,
    ),
    (
        "flag declarada e NAO citada: nao e defeito, e a direcao que nao importa",
        {},
        {DECLARADA},
        {},
        None,
    ),
]


def roda(rotulo, achadas, ja_declaradas, lista_pendente, esperado) -> bool:
    problemas = verifica(achadas, ja_declaradas, lista_pendente)

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
        print(f"FALHA: probe '{rotulo}' acusou, mas nao pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com divergencia plantada - {rotulo}")
    return True


def probe_da_varredura() -> bool:
    """O eixo que o conjunto injetado nao cobre: a leitura de `docs/spec/`.

    Escreve um documento de spec SINTETICO em diretorio temporario e confere que
    a varredura acha a flag citada nele, com arquivo e linha. Nada e escrito em
    `docs/spec/`, que e imutavel durante a implementacao.
    """
    nomes = adapters()
    if not nomes:
        print("FALHA: nenhum adapter para montar o padrao de varredura")
        return False

    alvo = f"{nomes[0]}.flag_que_so_existe_no_probe"
    with tempfile.TemporaryDirectory() as temporario:
        spec = Path(temporario)
        (spec / "99_FALSO.md").write_text(
            f"- [ ] `{alvo}: true` bloqueia alguma coisa\n", encoding="utf-8"
        )
        achadas = citadas(spec, nomes)

    if alvo not in achadas:
        print(f"FALHA: a varredura nao achou {alvo} no documento plantado")
        return False
    if not achadas[alvo][0].startswith("99_FALSO.md:"):
        print(f"FALHA: a varredura achou {alvo} sem localizar arquivo e linha")
        return False

    print("OK: a varredura acha a citacao, com arquivo e linha - documento plantado")
    return True


def arvore_limpa() -> bool:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return False
    return True


def main_probes() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_da_varredura())

    # A arvore real precisa ter as tres classes representadas, senao os probes
    # medem logica sobre um caso que nao ocorre.
    if not pendentes():
        print("FALHA: nenhuma pendente declarada — a terceira classe esta vazia")
        resultados.append(False)
    if not (declaradas() & set(citadas(REPO_ROOT / "docs" / "spec", adapters()))):
        print("FALHA: nenhuma flag citada E declarada — a primeira classe esta vazia")
        resultados.append(False)

    print()
    if all(resultados):
        print(
            f"check_spec_flags.py reprova nos {len(PROBES) + 1} eixos: citada sem "
            "declaracao, pendente que sobrou, pendente que a spec nao cita, dois "
            "casos verdes de controle, e a varredura sobre documento plantado."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
