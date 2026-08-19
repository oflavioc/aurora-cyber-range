#!/usr/bin/env python3
"""Prova que `check_spec_examples.py` REPROVA contra defeito plantado.

O verificador de exemplos da spec passou de primeira. Verificador que nunca
falhou prova que a arvore esta boa, nao que ele enxerga — e este em particular
nasceu para fechar o buraco que a terceira auditoria nomeou, entao aceitar seu
verde sem prova seria repetir o defeito no mecanismo que o corrige.

Tres eixos, um por forma de o verificador mentir:

  1. o contrato regride e passa a recusar o exemplo NORMATIVO — o caso real dos
     quatro defeitos daquela auditoria;
  2. a declaracao some e o bloco fica sem dono — cobertura por omissao;
  3. a ancora nao existe mais na spec — declaracao que envelheceu.

Planta em COPIA de `contracts/`. A spec fica intocada: e ela que o verificador
trata como fonte.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "contracts"
SPEC = REPO_ROOT / "docs" / "spec"
VERIFICADOR = REPO_ROOT / "scripts" / "check_spec_examples.py"


#: (rotulo, arquivo, texto original, texto plantado, trecho esperado)
PROBES = [
    (
        "contrato regride e recusa o exemplo normativo",
        "scenario.schema.v2.yaml",
        "      evidence_release:\n"
        "        type: array\n"
        "        minItems: 1\n"
        "        items:\n"
        "          $ref: '#/$defs/evidence_release_item'\n",
        "      evidence_release:\n"
        "        type: array\n"
        "        minItems: 1\n"
        "        items:\n"
        "          type: string\n",
        "o exemplo NORMATIVO e recusado",
    ),
    (
        "bloco da spec sem contrato que o reivindique",
        "scenario.schema.v2.yaml",
        "  - doc: '04_SCENARIO_SCHEMA.md'\n"
        "    anchor: '5. Inject'\n"
        "    pointer: '#/$defs/inject'\n"
        "    form: sequence-item\n",
        "",
        "nenhum contrato reivindica",
    ),
    (
        # A ancora era `sections: [1, 2]`, e a secao 2 servia porque o bloco de
        # `03` §2.2 estava em IGNORADOS. Na peca 1 da Fase 6 ele saiu de la —
        # `contracts/rubrics.schema.yaml` passou a reivindica-lo —, e o probe
        # deixou de ter bloco ignorado sob a secao que planta. Repontado para a
        # secao 4, onde `information_distribution` segue ignorado (P1-20).
        #
        # E o eixo, e nao a secao, que este probe prova: contrato que se declara
        # autoridade sobre uma secao cujo bloco alguem ignorou tem de dizer por
        # que nao o reivindica.
        "ignorado sob secao reivindicada como autoridade, sem justificar por que",
        "objectives.schema.yaml",
        "  - doc: '03_EXERCISE_DESIGN.md'\n    sections: [1]\n",
        "  - doc: '03_EXERCISE_DESIGN.md'\n    sections: [1, 4]\n",
        "e o motivo nao diz por que o",
    ),
    (
        "reivindica bloco de secao sobre a qual nao declara autoridade",
        "scenario.schema.v2.yaml",
        "  - doc: '08_EVIDENCE_SIMULATOR.md'\n    sections: [5]\n",
        "",
        "sem declarar autoridade",
    ),
    (
        "declaracao apontando para ancora que nao existe mais",
        "events.schema.yaml",
        "    anchor: '1. Envelope universal'\n",
        "    anchor: '1. Envelope que foi renomeado'\n",
        "que nao existe em docs/spec/",
    ),
]


def arvore_limpa() -> bool:
    r = subprocess.run(
        [sys.executable, str(VERIFICADOR)], capture_output=True, text=True, cwd=REPO_ROOT
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
            [sys.executable, str(VERIFICADOR), str(destino)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        saida = r.stdout + r.stderr

        if r.returncode != 1:
            print(f"FALHA: probe '{rotulo}' saiu com rc={r.returncode}, esperado 1")
            print(saida)
            return False
        if esperado not in saida:
            print(f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado")
            print(saida)
            return False

    print(f"OK: reprovou com defeito plantado - {rotulo}")
    return True


#: Probes que plantam na SPEC, e nao no contrato. Sao as regras que dependem do
#: conteudo dos documentos: rotulo de cerca e entrada orfa em IGNORADOS.
PROBES_SPEC = [
    (
        "cerca sem rotulo carregando estrutura de dados",
        "09_EVENT_MODEL.md",
        "```yaml\nhooks:\n",
        "```\nhooks:\n",
        "parece carregar estrutura de dados",
    ),
    (
        "entrada de IGNORADOS que ficou orfa",
        "05_SECURITY_REQUIREMENTS.md",
        "## 3. Dados",
        "## 3. Dados renomeada",
        "que nao existe mais em docs/spec/",
    ),
]


def roda_probe_spec(rotulo, arquivo, antes, depois, esperado) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "spec"
        shutil.copytree(SPEC, destino)
        alvo = destino / arquivo
        texto = alvo.read_text(encoding="utf-8")
        if texto.count(antes) < 1:
            print(f"FALHA: probe '{rotulo}' nao ancorou em {arquivo}")
            return False
        alvo.write_text(texto.replace(antes, depois, 1), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(VERIFICADOR), str(CONTRACTS), str(destino)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        saida = r.stdout + r.stderr
        if r.returncode != 1:
            print(f"FALHA: probe '{rotulo}' saiu com rc={r.returncode}, esperado 1")
            return False
        if esperado not in saida:
            print(f"FALHA: probe '{rotulo}' reprovou, mas nao pelo eixo esperado")
            return False
    print(f"OK: reprovou com defeito plantado - {rotulo}")
    return True


def main() -> int:
    if not arvore_limpa():
        return 1
    resultados = [roda_probe(*p) for p in PROBES]
    resultados += [roda_probe_spec(*p) for p in PROBES_SPEC]
    print()
    if all(resultados):
        print(f"check_spec_examples.py reprova nos {len(PROBES) + len(PROBES_SPEC)} eixos: {len(PROBES)} de contrato, {len(PROBES_SPEC)} de spec.")
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
