#!/usr/bin/env python3
"""Prova que `check_regras_do_linter.py` REPROVA contra defeito plantado.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina da
Fase 0, repetida por todo `*_probes.py` deste repositorio.

POR QUE OS PROBES INJETAM AS REGRAS EM VEZ DE EDITAR O CONTRATO
----------------------------------------------------------------
Os defeitos aqui sao estados que a arvore nao tem — entrada sem dono, `sitio`
apontando para constante que nao existe, `id` duplicado. Planta-los de verdade
exigiria escrever no `contracts/scenario.schema.v2.yaml` e desfazer depois, e
verificador que suja a arvore para se provar e o que a P2-15 recusou.

`verifica()` recebe as regras e o conjunto de sitios por parametro exatamente
para isso.

O RISCO DESSA ESCOLHA, e o que o fecha: lista injetada nao exercita a LEITURA.
Os dois ultimos probes cobrem esse eixo — um confere que `regras_do_contrato()`
le o registro REAL e que ele nao esta vazio, o outro que `sitios_declarados()`
extrai os sitios do `pack_loader.py` REAL e encontra os que o registro cita.
Sem eles, um `x-aurora-linter-rules` renomeado no contrato deixaria a suite
verde com `verifica([])` nunca sendo chamado com nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_regras_do_linter import (  # noqa: E402
    LOADER,
    regras_do_contrato,
    sitios_declarados,
    verifica,
)

#: Sitios SINTETICOS. Nao usam nome de sitio real de proposito: o que os probes
#: exercitam e a LOGICA, e ela nao conhece nenhum sitio em particular.
SITIOS = {"sitio_de_fixture", "outro_sitio_de_fixture"}


def _regra(**campos) -> dict:
    """Uma entrada valida, com os campos pedidos sobrescritos.

    A base e valida de proposito: cada probe planta UM defeito, e um probe que
    partisse de entrada ja quebrada reprovaria pelo motivo errado.
    """
    base = {
        "id": "regra_de_fixture",
        "rule": "o enunciado da regra de fixture",
        "mecanismo": "algum/modulo.py, alguma_funcao",
        "sitio": "sitio_de_fixture",
    }
    base.update(campos)
    return {chave: valor for chave, valor in base.items() if valor is not None}


#: `(rotulo, regras, trecho esperado na reprovacao)`
PROBES = [
    (
        "registro vazio: o gate passaria a nao julgar nada",
        [],
        "esta vazio ou ausente",
    ),
    (
        "a forma ANTIGA do registro — sequencia de strings sem dono",
        ["t_relative fora de ordem e recusado"],
        "e nao um mapeamento",
    ),
    (
        "entrada sem `id`",
        [_regra(id=None)],
        "sem `id`",
    ),
    (
        "entrada sem `rule`: o enunciado que um humano le",
        [_regra(rule=None)],
        "sem `rule`",
    ),
    (
        "entrada sem mecanismo E sem destinatario — a prosa sem dono",
        [_regra(mecanismo=None, sitio=None)],
        "sem `mecanismo` e sem `destinatario`",
    ),
    (
        "adiamento sem motivo: a excecao que vira permissao permanente",
        [_regra(mecanismo=None, sitio=None, destinatario="Fase 12")],
        "e nao tem `motivo`",
    ),
    (
        "`sitio` apontando para constante que `PackSite` nao declara",
        [_regra(sitio="sitio_que_foi_renomeado")],
        "nao existe em `PackSite`",
    ),
    (
        "`id` duplicado: uma das duas entradas fica invisivel a quem a cita",
        [_regra(), _regra()],
        "duplicado",
    ),
]


def main() -> int:
    falhas: list[str] = []

    for rotulo, regras, esperado in PROBES:
        problemas = verifica(regras, SITIOS)
        if not problemas:
            falhas.append(f"{rotulo}: NAO reprovou")
            continue
        corpo = "\n".join(problemas)
        if esperado not in corpo:
            falhas.append(
                f"{rotulo}: reprovou, e a mensagem nao traz {esperado!r}.\n"
                f"    Reprovar pelo motivo errado e passar pelo motivo errado."
                f"\n    Mensagem: {corpo[:200]}"
            )

    # CONTROLE POSITIVO. Sem ele, um `verifica()` que reprovasse TUDO passaria
    # nos oito probes acima e o verificador viraria gate sempre vermelho.
    if problemas := verifica([_regra()], SITIOS):
        falhas.append(
            "controle positivo: entrada valida foi REPROVADA — "
            f"{problemas}"
        )

    # -- o eixo que a injecao nao alcanca: a leitura da arvore real -----------

    reais = regras_do_contrato()
    if not reais:
        falhas.append(
            "`regras_do_contrato()` devolveu vazio sobre o contrato REAL. O "
            "registro sumiu, foi renomeado, ou o parser deixou de o alcancar — e "
            "nos tres casos o verificador passaria a julgar nada."
        )

    sitios_reais = sitios_declarados(LOADER)
    if not sitios_reais:
        falhas.append(
            "`sitios_declarados()` nao achou `PackSite` no `pack_loader.py` REAL. "
            "Sem os sitios, a perna que cobra `sitio` aceitaria qualquer nome."
        )
    else:
        citados = {
            str(regra.get("sitio")).strip()
            for regra in reais
            if isinstance(regra, dict) and regra.get("sitio")
        }
        if orfaos := sorted(citados - sitios_reais):
            falhas.append(
                f"o registro REAL cita sitio que o `PackSite` REAL nao declara: "
                f"{orfaos}. Este probe e a prova de que a extracao por AST casa "
                "com o que o contrato escreve — se ela quebrasse, `verifica()` "
                "reprovaria a arvore limpa e alguem removeria a perna."
            )

    if falhas:
        print("PROVA NEGATIVA REPROVADA\n", file=sys.stderr)
        for falha in falhas:
            print(f"  {falha}\n", file=sys.stderr)
        return 1

    print(
        f"{len(PROBES)} defeitos plantados, {len(PROBES)} detectados; "
        f"controle positivo verde; registro real com {len(reais)} regras e "
        f"{len(sitios_reais)} sitios lidos da arvore."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
