#!/usr/bin/env python3
"""Prova que `check_contract_examples.py` REPROVA contra defeito plantado.

Um executor de fixtures que so roda contra a arvore boa prova que ela passa, nao
que ele pega alguma coisa. E a mesma distincao que `phase0_negative_tests.py`
aplica aos seis verificadores de invariante, e o motivo pelo qual a Fase 0 levou
dezenove rodadas: **o mecanismo existir nao e a propriedade valer.**

Cada probe copia `contracts/` para um diretorio temporario, planta UM defeito por
substituicao de texto, e exige rc=1 com a mensagem do eixo correspondente.

Os seis eixos, um por forma de mentira que uma fixture pode contar:

  1. exemplo positivo que nao valida
  2. exemplo positivo que viola regra x-aurora
  3. fixture `rejected_by: schema` que o schema na verdade aceita
  4. fixture x-aurora cuja regra declarada nao dispara
  5. fixture x-aurora que o schema ja recusa — nao isola a regra que diz provar
  6. fixture negativa sem `rejected_by`

Nao escreve em `contracts/`. Rodado no mesmo job de CI que o executor.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "contracts"
EXECUTOR = REPO_ROOT / "scripts" / "check_contract_examples.py"


#: (rotulo, arquivo, texto original, texto plantado, trecho esperado no stderr)
PROBES = [
    (
        "exemplo positivo que nao valida",
        "state_flags.schema.yaml",
        "        category: performance\n        domain_area: academic\n"
        "        severity_weight: 5",
        "        category: disponibilidade\n        domain_area: academic\n"
        "        severity_weight: 5",
        "exemplo POSITIVO",
    ),
    (
        "exemplo positivo que viola regra x-aurora",
        "ground_truth.schema.yaml",
        "          - flag_false: academus.enrollment_offline",
        "          - flag_false: academus.flag_inventada",
        "x-aurora-ref:adapter_flags",
    ),
    (
        "fixture `rejected_by: schema` que o schema aceita",
        "state_flags.schema.yaml",
        "        - name: enrollment_offline",
        "        - name: academus.enrollment_offline",
        "o schema ACEITA a instancia",
    ),
    (
        "fixture x-aurora cuja regra declarada nao dispara",
        "ground_truth.schema.yaml",
        "            - event: vpn_acess_revoked",
        "            - event: vpn_access_revoked",
        "NAO disparou",
    ),
    (
        "fixture x-aurora que o schema ja recusa: nao isola a regra",
        "ground_truth.schema.yaml",
        "    rejected_by: 'x-aurora-unique'\n    instance:\n      facts:\n"
        "        - fact_id: GT-A-001",
        "    rejected_by: 'x-aurora-unique'\n    instance:\n      facts:\n"
        "        - fact_id: gt-minusculo",
        "ja recusa",
    ),
    (
        "fixture de schema com dois defeitos: nao isola nenhum",
        "events.schema.yaml",
        "  - reason: 'truth_layer fora dos cinco valores'\n"
        "    rejected_by: schema\n"
        "    instance:\n"
        "      event_id: '01J9F000000000000000000002'",
        "  - reason: 'truth_layer fora dos cinco valores'\n"
        "    rejected_by: schema\n"
        "    instance:\n"
        "      event_id: ''",
        "defeitos distintos, esperado 1",
    ),
    (
        "effect_class sem cobrir o catalogo inteiro",
        "events.schema.yaml",
        "    containment_declared: declaration\n",
        "",
        "sem effect_class",
    ),
    (
        "effect_class com valor fora do conjunto declarado",
        "events.schema.yaml",
        "    vpn_access_revoked: state_effect\n",
        "    vpn_access_revoked: efeito_colateral\n",
        "valor de effect_class fora do conjunto",
    ),
    (
        "fixture negativa sem `rejected_by`",
        "objectives.schema.yaml",
        "  - reason: 'classe derived nao existe: a ontologia de evidencia e binaria'\n"
        "    rejected_by: schema",
        "  - reason: 'classe derived nao existe: a ontologia de evidencia e binaria'",
        "sem `rejected_by`",
    ),
]


def arvore_limpa() -> bool:
    r = subprocess.run(
        [sys.executable, str(EXECUTOR)], capture_output=True, text=True, cwd=REPO_ROOT
    )
    if r.returncode != 0:
        print("FALHA: a arvore limpa ja reprova; probes nao provariam nada")
        print(r.stdout + r.stderr)
        return False
    print("OK: arvore limpa passa (rc=0)")
    return True


def roda_probe(rotulo, arquivo, antes, depois, esperado) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "contracts"
        shutil.copytree(CONTRACTS, destino)
        alvo = destino / arquivo
        texto = alvo.read_text(encoding="utf-8")

        if texto.count(antes) != 1:
            print(
                f"FALHA: probe '{rotulo}' nao ancorou — o trecho aparece "
                f"{texto.count(antes)}x em {arquivo}, esperado 1"
            )
            return False

        alvo.write_text(texto.replace(antes, depois), encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(EXECUTOR), str(destino)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        saida = r.stdout + r.stderr

        if r.returncode != 1:
            print(
                f"FALHA: probe '{rotulo}' saiu com rc={r.returncode}, esperado 1. "
                f"rc diferente de 1 indica erro de ferramenta, nao deteccao"
            )
            return False
        if esperado not in saida:
            print(
                f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado "
                f"({esperado!r} ausente da saida)"
            )
            return False

    print(f"OK: reprovou com defeito plantado - {rotulo}")
    return True


def main() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda_probe(*p) for p in PROBES]
    print()
    if all(resultados):
        print(
            f"check_contract_examples.py reprova nos {len(PROBES)} eixos de defeito "
            f"de fixture."
        )
        return 0
    print(f"{resultados.count(False)} de {len(PROBES)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
