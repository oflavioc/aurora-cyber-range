#!/usr/bin/env python3
"""Probes externos: cada verificador da Fase 0 deve falhar contra uma violacao plantada."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: readonly_bash.py vive em duas copias: a versionada (fonte) e a instalada em
#: ~/.claude/hooks/, que e a que o Claude Code realmente executa. Os probes
#: rodam contra a FONTE, e `hook_copies_in_sync` cobre a diferenca entre as duas.
READONLY_HOOK_SOURCE = ROOT / "user-scope" / "hooks" / "readonly_bash.py"
READONLY_HOOK_INSTALLED = Path.home() / ".claude" / "hooks" / "readonly_bash.py"


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


# --------------------------------------------------------------------------
# Probes do hook readonly_bash.py — NAS DUAS DIRECOES.
#
# So testar bloqueio produz um guarda que bloqueia tudo e passa no teste. Foi
# assim que quatro rodadas seguidas renderam falso bloqueio sem nenhum teste
# reprovar: o harness cobria "nega escrita" e nunca "libera leitura".
# --------------------------------------------------------------------------

#: Os cinco modos de falso bloqueio da familia P23, todos leitura legitima.
LEITURA_LEGITIMA = [
    ("(a) redirecao de stderr para /dev/null", "git rev-parse main 2>/dev/null"),
    ("(b) pipeline com filtro de texto", "git ls-files | sort"),
    ("(c) alternancia dentro de aspas", r'grep -n "fase 0\|phase 0"'),
    ("(d) laco de shell", 'for f in $(git ls-files); do cat "$f"; done'),
    (
        "(e) smoke test do PHASE_0_CHECKLIST (payload citado)",
        "printf '%s\\n' '{\"tool_input\":{\"command\":\"rm -rf range-core\"}}'"
        " | python ~/.claude/hooks/readonly_bash.py",
    ),
    ("verificador com prefixo de ambiente seguro",
     "PYTHONDONTWRITEBYTECODE=1 python tools/check_core_boundary.py"),
    ("harness negativo (este arquivo)", "python scripts/phase0_negative_tests.py"),
]

#: Escrita deliberada: a protecao nao pode ter sido afrouxada pela tokenizacao.
ESCRITA_DELIBERADA = [
    ("remocao real", "rm -rf range-core"),
    ("git que altera estado", "git commit -m x"),
    ("redirecionamento para arquivo", "git log > out.txt"),
    ("escrita via tee", "git ls-files | tee out.txt"),
    ("instalacao de pacote", "pip install requests"),
    ("acesso de rede", "curl https://example.com"),
    ("execucao arbitraria via python -c", "python -c 'import os'"),
    ("edicao in-place", "sed -i s/a/b/ file"),
    ("escrita no corpo de um laco", "for f in a; do rm $f; done"),
    ("execucao dentro de substituicao de comando", "git ls-files `rm -rf x`"),
    ("env como trampolim de execucao", "env rm -rf x"),
    ("flag destrutiva de git branch", "git branch -D main"),
    ("find com acao de escrita", "find . -delete"),

    # --- B1 (BLOCKER, setima auditoria) -----------------------------------
    # A reescrita por tokens abriu tres caminhos de escrita que a versao em
    # regex fechava. Os 13 probes acima cobriam redirecionamento SO na forma
    # `>`: o harness declarava provar que a protecao nao afrouxou, passava
    # verde, e tres afrouxamentos estavam presentes. Probe que so cobre a forma
    # que voce lembrou nao prova ausencia das formas que voce esqueceu.
    ("redirecionamento na forma >&", "ls >& out.txt"),
    ("redirecionamento na forma &>", "ls &> out.txt"),
    ("redirecionamento na forma &>>", "ls &>> out.txt"),
    ("redirecionamento na forma >|", "ls >| out.txt"),
    ("redirecionamento na forma <>", "ls <> out.txt"),
    ("escrita por flag: sort -o", "git ls-files | sort -o out.txt"),
    ("escrita por flag: find -fprint0", "find . -fprint0 out.txt"),

    # Travessia: os alvos alcancam o worktree PRINCIPAL a partir do worktree de
    # auditoria — CLAUDE.md e os proprios verificadores de tools/.
    ("travessia via >&", "ls >& ../../CLAUDE.md"),
    ("travessia via sort -o", "git ls-files | sort -o ../../CLAUDE.md"),
    ("travessia via find -fprint0", "find . -fprint0 ../../tools/codegen.py"),

    # H1: allowlistar um script e allowlistar o que ele FAZ. log_audit.py grava
    # incondicionalmente no worktree principal via persist().
    ("script de hook que grava sem condicao", "python .claude/hooks/log_audit.py"),

    # --- B1, superficie completa ------------------------------------------
    # Os tres vetores do auditor eram parte de uma familia maior: TODO comando
    # da allowlist que aceita flag de saida escreve. Nenhum deles precisa de
    # redirecionamento nem de comando fora da allowlist.
    ("escrita por flag: pytest --junitxml", "pytest --junitxml=../../CLAUDE.md"),
    ("escrita por flag: python -m pytest --junitxml",
     "python -m pytest --junitxml=../../CLAUDE.md"),
    ("escrita por flag: ruff --output-file", "ruff check --output-file ../../CLAUDE.md ."),
    ("escrita por flag: mypy --junit-xml", "mypy --junit-xml ../../CLAUDE.md ."),
    ("escrita por flag: eslint -o", "eslint -o ../../CLAUDE.md ."),
    # --noEmit presente satisfazia a checagem antiga, que ignorava o resto da
    # linha: classificar em vez de identificar, outra vez.
    ("escrita por flag: tsc --outFile", "tsc --noEmit --outFile ../../CLAUDE.md"),
    ("escrita por flag: sort --output= (forma longa)",
     "git ls-files | sort --output=../../CLAUDE.md"),
    # Escrita POSICIONAL: nenhuma flag envolvida, entao allowlist de flags
    # sozinha nao cobriria. `uniq entrada saida` grava em saida.
    ("escrita posicional: uniq", "uniq entrada.txt ../../CLAUDE.md"),
]


def _run_readonly_hook(command: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(READONLY_HOOK_SOURCE)],
        cwd=ROOT, input=payload, text=True, capture_output=True,
    )


def expect_hook_allows(label: str, command: str) -> None:
    result = _run_readonly_hook(command)
    if result.returncode != 0:
        _reject(
            f"readonly_bash.py {label}",
            f"BLOQUEOU leitura legitima (rc={result.returncode}). "
            f"Comando: {command}",
            (result.stdout or "") + (result.stderr or ""),
        )
    print(f"OK: readonly_bash.py liberou leitura legitima - {label}")


def expect_hook_blocks(label: str, command: str) -> None:
    result = _run_readonly_hook(command)
    saida = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 2:
        _reject(
            f"readonly_bash.py {label}",
            f"NAO bloqueou escrita deliberada (rc={result.returncode}, esperado 2). "
            f"Comando: {command}",
            saida,
        )
    if not saida.strip():
        _reject(f"readonly_bash.py {label}", "bloqueou sem explicar o motivo", saida)
    print(f"OK: readonly_bash.py bloqueou escrita deliberada - {label}")


def hook_copies_in_sync() -> None:
    """A copia instalada e a que roda. Divergencia silenciosa e o pior caso."""
    if not READONLY_HOOK_INSTALLED.exists():
        print(
            "AVISO: ~/.claude/hooks/readonly_bash.py ausente — checagem de drift "
            "pulada (esperado em CI, onde nao ha escopo de usuario)."
        )
        return
    fonte = READONLY_HOOK_SOURCE.read_text(encoding="utf-8").splitlines()
    instalada = READONLY_HOOK_INSTALLED.read_text(encoding="utf-8").splitlines()
    if fonte != instalada:
        _reject(
            "readonly_bash.py",
            "fonte versionada e copia instalada DIVERGEM. "
            f"Copie {READONLY_HOOK_SOURCE.relative_to(ROOT).as_posix()} "
            "para ~/.claude/hooks/",
            "",
        )
    print("OK: fonte versionada e copia instalada de readonly_bash.py identicas")


def main() -> int:
    with temporary_file("range-core/_phase0_probe_bad.py", "from domains.academus import X\n"):
        expect_fail("check_core_boundary.py", [sys.executable, "tools/check_core_boundary.py"],
                    "range-core/_phase0_probe_bad.py")

    # Montado por concatenacao de proposito: .claude/hooks/check_architecture.py
    # recusa literal de flag em codigo, e este arquivo e codigo. A montagem
    # evita o falso positivo do hook sem afrouxa-lo.
    probe_flag = "academus." + "phase0_probe_flag"

    flags = """flags:\n  - name: academus.phase0_probe_flag\n    type: boolean\n    default: false\n"""

    # Catalogo minimo no formato de 09_EVENT_MODEL.md secao 4.1, agrupado por
    # truth_layer. Ate aqui nenhum probe plantava contracts/events.schema.yaml,
    # entao load_declared_event_types() devolvia sempre {} e METADE do
    # invariante 2 — o ramo de event_type — nunca foi exercitada. O bloco de
    # artefatos de evento do codegen tambem nunca era alcancado.
    eventos = (
        "event_types:\n"
        "  ground_truth:\n"
        "    - fact_materialized\n"
        "  participant_action:\n"
        "    - containment_declared\n"
    )
    probe_event_type = "containment_declared"
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

    # O invariante 2 tem DOIS ramos: literal de flag e literal de event_type.
    # So o de flag tinha probe.
    with temporary_file("contracts/events.schema.yaml", eventos), temporary_file(
        "domains/academus/api/handler.py",
        "EVENT = " + repr(probe_event_type) + "\n",
    ):
        expect_fail("check_contract_literals.py (event_type)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/api/handler.py")

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
        expect_fail("codegen.py --check (artefato ausente)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "domains/_phase0_codegen_probe/flags.yaml")

    # Ausencia e divergencia sao ramos DIFERENTES do verificador, e T2 de
    # 06_ACCEPTANCE_TESTS.md fala de constantes DESSINCRONIZADAS — que e o ramo
    # de divergencia. Ele nao era exercitado por probe nenhum.
    #
    # Os dois artefatos sao plantados, e ambos divergentes: com .py e .ts
    # presentes, o ramo de ausencia nao pode disparar, entao a deteccao so pode
    # vir da comparacao de conteudo.
    with temporary_file("domains/_phase0_divergent_probe/flags.yaml", flags), temporary_file(
        "domains/_phase0_divergent_probe/generated/flags.py",
        "# artefato fora de sincronia com o contrato\n",
    ), temporary_file(
        "domains/_phase0_divergent_probe/generated/flags.ts",
        "// artefato fora de sincronia com o contrato\n",
    ):
        expect_fail("codegen.py --check (artefato divergente)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "domains/_phase0_divergent_probe/generated/flags.py")

    # O codegen tem dois blocos de contrato: flags por adapter e o catalogo de
    # eventos. O bloco de eventos nunca era alcancado, porque nenhum probe
    # plantava contracts/events.schema.yaml. O ramo de divergencia de conteudo e
    # o mesmo codigo ja exercitado pelo probe de flags acima; aqui o que se
    # prova e que o catalogo de eventos gera expectativa de artefato.
    with temporary_file("contracts/events.schema.yaml", eventos):
        expect_fail("codegen.py --check (artefatos de evento)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "contracts/events.schema.yaml")

    for label, comando in LEITURA_LEGITIMA:
        expect_hook_allows(label, comando)
    for label, comando in ESCRITA_DELIBERADA:
        expect_hook_blocks(label, comando)
    hook_copies_in_sync()

    print(
        "Todos os seis verificadores falharam contra probes independentes, e "
        f"readonly_bash.py passou nos {len(LEITURA_LEGITIMA)} probes de leitura "
        f"legitima e nos {len(ESCRITA_DELIBERADA)} de escrita deliberada."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
