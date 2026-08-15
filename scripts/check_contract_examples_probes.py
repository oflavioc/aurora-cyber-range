#!/usr/bin/env python3
"""Prova que `check_contract_examples.py` REPROVA contra defeito plantado.

Um executor de fixtures que so roda contra a arvore boa prova que ela passa, nao
que ele pega alguma coisa. E a mesma distincao que `phase0_negative_tests.py`
aplica aos seis verificadores de invariante, e o motivo pelo qual a Fase 0 levou
dezenove rodadas: **o mecanismo existir nao e a propriedade valer.**

DOIS TIPOS DE PROBE, e a contagem esta em PROBES e PROBES_INSTANCIA — nunca
repetida em prosa. A versao anterior deste docstring dizia "os seis eixos" e
enumerava seis enquanto o codigo ja executava nove: documentacao que sobrevive a
mudanca e a contradiz, a linhagem P10/P15/P22 que este repositorio nomeia. Foi o
L2 da terceira auditoria, e a licao e nao escrever numero que o codigo ja sabe.

FIXTURE MENTIROSA — copia `contracts/` para diretorio temporario e planta UM
defeito por substituicao de texto. Cobre as formas de um exemplo afirmar o que
nao prova: positivo que nao valida, positivo que viola regra x-aurora, negativo
que o schema aceita, regra declarada que nao dispara, fixture que o schema ja
recusa, fixture com dois defeitos, duas violacoes da mesma regra, `effect_class`
incompleto ou com valor invalido, e negativa sem `rejected_by`.

INSTANCIA REAL INVALIDA — planta em `domains/<adapter>/flags.yaml` e restaura.
Cobre o eixo que a auditoria mostrou aberto: o executor validar exemplos e nao
validar o artefato real que o contrato governa.

Cada probe exige rc=1 e a mensagem do eixo correspondente. Rodado no mesmo job
de CI que o executor.
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
        "fixture x-aurora com duas violacoes da MESMA regra",
        "scenario.schema.v2.yaml",
        "          reconverge_at: Z99\n"
        "          evaluate:\n"
        "            - id: z\n"
        "              default: true\n"
        "              next: A09B\n",
        "          reconverge_at: Z99\n"
        "          evaluate:\n"
        "            - id: z\n"
        "              default: true\n"
        "              next: Y88\n",
        "vezes, esperado 1",
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
        "faixas sinteticas divergindo entre contrato e verificador",
        "evidence.schema.yaml",
        "    - .localhost\n    - .local",
        "    - .localhost",
        "faixas de dominio divergentes",
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


#: Probes de INSTANCIA REAL. Diferentes dos demais: nao ha copia de contrato,
#: porque o alvo e `domains/<adapter>/flags.yaml`, que o executor le sempre da
#: raiz do repositorio. Estes plantam no lugar e restauram no fim — escrita
#: instrumental do proprio teste, a mesma excecao delimitada que
#: `scripts/phase0_negative_tests.py` ja faz.
FLAG_VALIDA = (
    "flags:\n"
    "  - name: academus.probe_flag\n"
    "    type: boolean\n"
    "    default: false\n"
    "    category: availability\n"
    "    domain_area: academic\n"
    "    severity_weight: 5\n"
    "    wallboard_group: 'Probe'\n"
    "    consumers: [academus-api]\n"
    "    effect_ui: 'Probe'\n"
    "    reversible: true\n"
)

PROBES_INSTANCIA = [
    (
        "flags.yaml com category fora do conjunto fechado",
        FLAG_VALIDA.replace("category: availability", "category: disponibilidade"),
        "nao valida contra state_flags.schema.yaml",
    ),
    (
        "flags.yaml com flag numerica sem dominio declarado (D7)",
        FLAG_VALIDA.replace(
            "    type: boolean\n    default: false\n",
            "    type: number\n    default: 0\n",
        ),
        "nao valida contra state_flags.schema.yaml",
    ),
]


def roda_probe_instancia(rotulo, conteudo, esperado) -> bool:
    alvo = REPO_ROOT / "domains" / "academus" / "flags.yaml"
    original = alvo.read_bytes()
    try:
        alvo.write_text(conteudo, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(EXECUTOR)], capture_output=True, text=True, cwd=REPO_ROOT
        )
        saida = r.stdout + r.stderr
        if r.returncode != 1:
            print(f"FALHA: probe '{rotulo}' saiu com rc={r.returncode}, esperado 1")
            return False
        if esperado not in saida:
            print(f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado")
            return False
    finally:
        alvo.write_bytes(original)
    print(f"OK: reprovou com defeito plantado - {rotulo}")
    return True


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
    resultados += [roda_probe_instancia(*p) for p in PROBES_INSTANCIA]
    print()
    if all(resultados):
        print(
            f"check_contract_examples.py reprova nos {len(PROBES) + len(PROBES_INSTANCIA)} "
            f"eixos: {len(PROBES)} de fixture mentirosa, {len(PROBES_INSTANCIA)} de "
            f"instancia real invalida."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
