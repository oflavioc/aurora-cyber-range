#!/usr/bin/env python3
"""Probes externos: cada verificador da Fase 0 deve falhar contra uma violacao plantada."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


@contextmanager
def temporary_file(relative: str, content: str):
    path = ROOT / relative
    backup = None
    existed = path.exists()
    if existed:
        backup = path.read_bytes()

    created_dirs: list[Path] = []
    parent = path.parent
    missing: list[Path] = []
    while parent != ROOT and not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir()
        created_dirs.append(directory)

    path.write_text(content, encoding="utf-8")
    try:
        yield path
    finally:
        if existed:
            path.write_bytes(backup or b"")
        else:
            path.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass


def _reject(label: str, motivo: str, saida: str) -> None:
    print(f"FAIL: {label} {motivo}")
    if saida.strip():
        print(saida.strip())
    raise SystemExit(1)


def expect_fail(label: str, command: list[str], planted: str) -> None:
    """Exige DETECCAO, nao apenas saida diferente de zero.

    Aceitar qualquer rc != 0 torna crash de ferramenta (rc=2, contrato
    malformado, arquivo ilegivel) indistinguivel de deteccao (rc=1). Um
    verificador que quebra ao ser executado passaria no teste negativo sem
    nunca ter enxergado a violacao.

    Por isso sao tres exigencias: rc exatamente 1, saida nao vazia, e mencao
    explicita ao arquivo plantado.
    """
    result = run(*command)
    saida = (result.stdout or "") + (result.stderr or "")

    if result.returncode == 0:
        _reject(label, "nao detectou a violacao plantada", saida)

    if result.returncode != 1:
        _reject(
            label,
            f"saiu com rc={result.returncode}, esperado 1. "
            "rc diferente de 1 indica erro de ferramenta, nao deteccao",
            saida,
        )

    if planted not in saida.replace("\\", "/"):
        _reject(
            label,
            f"saiu com rc=1 mas nao citou o arquivo plantado '{planted}'. "
            "Deteccao sem localizacao nao permite intervir",
            saida,
        )

    print(f"OK: {label} detectou violacao em {planted} (rc=1)")


def main() -> int:
    with temporary_file("range-core/_phase0_probe_bad.py", "from domains.academus import X\n"):
        expect_fail("check_core_boundary.py", [sys.executable, "tools/check_core_boundary.py"],
                    "range-core/_phase0_probe_bad.py")

    # Montado por concatenacao de proposito: .claude/hooks/check_architecture.py
    # recusa literal de flag em codigo, e este arquivo e codigo. A montagem
    # evita o falso positivo do hook sem afrouxa-lo.
    probe_flag = "academus." + "phase0_probe_flag"

    flags = """flags:\n  - name: academus.phase0_probe_flag\n    type: boolean\n    default: false\n"""
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/_phase0_probe_literal.py", "FLAG = 'academus.phase0_probe_flag'\n"
    ):
        expect_fail("check_contract_literals.py", [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/_phase0_probe_literal.py")

    # TypeScript e gate real, nao so hook: 01_ARCHITECTURE.md secao 5.4 exige
    # constante gerada para Python E TypeScript, e o layout da secao 2 coloca
    # o front-end de core e adapter em .ts/.tsx.
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/web/_phase0_probe_literal.tsx",
        "export const FLAG = " + '"' + probe_flag + '";\n',
    ):
        expect_fail("check_contract_literals.py (TypeScript)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/web/_phase0_probe_literal.tsx")

    # Plantado em range-core/engine/, NAO em um diretorio "api"/"events": a
    # versao anterior do verificador so varria esses dois segmentos e o probe
    # antigo passava sem nunca tocar a fronteira real. 01_ARCHITECTURE.md
    # secao 6 declara o inject-engine como emissor de eventos de effect.
    with temporary_file(
        "range-core/engine/_phase0_probe_event.py",
        "event = {'event_type': 'PROBE', 'objective_ids': ['OBJ-X']}\n",
    ):
        expect_fail("check_event_envelope.py", [sys.executable, "tools/check_event_envelope.py"],
                    "range-core/engine/_phase0_probe_event.py")

    # Isencao de projecao e ANCORADA. Este caminho tem um segmento "metrics" no
    # meio, mas e caminho de emissao de adapter: so range-core/metrics/ e
    # projecao. Isencao casando segmento em qualquer profundidade anulava o
    # invariante 4 justamente onde ele passou a ser a unica fronteira.
    with temporary_file(
        "domains/academus/api/metrics/emit.py",
        "event = {'event_type': 'PROBE', 'objective_ids': ['OBJ-X']}\n",
    ):
        expect_fail("check_event_envelope.py (isencao ancorada)",
                    [sys.executable, "tools/check_event_envelope.py"],
                    "domains/academus/api/metrics/emit.py")

    # Mesma correcao no invariante 2: um segmento "contracts" no meio do
    # caminho nao autoriza literal de flag.
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/api/contracts/handler.py",
        "FLAG = " + repr(probe_flag) + "\n",
    ):
        expect_fail("check_contract_literals.py (isencao ancorada)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/api/contracts/handler.py")

    with temporary_file("range-core/_phase0_probe_security.py", "value = eval('1 + 1')\n"):
        expect_fail("check_security_constraints.py", [sys.executable, "tools/check_security_constraints.py"],
                    "range-core/_phase0_probe_security.py")

    with temporary_file(
        "scenarios/_phase0_probe/fixture.jsonl",
        '{"src":"8.8.8.8","domain":"google.com"}\n',
    ):
        expect_fail("check_synthetic_data.py", [sys.executable, "tools/check_synthetic_data.py"],
                    "scenarios/_phase0_probe/fixture.jsonl")

    # 123.456.789-09 e o CPF de exemplo canonico: sequencia crescente com os
    # digitos verificadores corretos. Nao e numero plausivelmente emitido, e
    # serve exatamente para provar que CPF VALIDO e recusado em dado sintetico
    # (05_SECURITY_REQUIREMENTS secao 3).
    with temporary_file(
        "scenarios/_phase0_probe_cpf/alunos.jsonl",
        '{"nome":"Fulano de Tal","cpf":"123.456.789-09"}\n',
    ):
        expect_fail("check_synthetic_data.py (identificador)",
                    [sys.executable, "tools/check_synthetic_data.py"],
                    "scenarios/_phase0_probe_cpf/alunos.jsonl")

    # codegen --check deve detectar contrato novo sem artefato gerado correspondente.
    with temporary_file("domains/_phase0_codegen_probe/flags.yaml", flags):
        expect_fail("codegen.py --check", [sys.executable, "tools/codegen.py", "--check"],
                    "domains/_phase0_codegen_probe/flags.yaml")

    print("Todos os seis verificadores falharam contra probes independentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
