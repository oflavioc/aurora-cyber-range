#!/usr/bin/env python3
"""Constantes tipadas geradas a partir dos contratos — modo de verificacao.

01_ARCHITECTURE.md secao 5.4 e 06_ACCEPTANCE_TESTS.md T2.

Na Fase 0 este script implementa APENAS `--check`. A geracao efetiva chega na
Fase 1, junto com os contratos que ela consome. Modo de escrita sem probe que
o exercite seria codigo nao verificado dentro do proprio mecanismo de
verificacao — exatamente o que a Fase 0 existe para nao deixar passar.

Contrato de `--check`, fixado apos a auditoria v2 (CHANGELOG_V3.md, H1):

    compara EM MEMORIA os artefatos gerados com os que estao em disco e sai
    com codigo diferente de zero em divergencia. NUNCA escreve.

Por isso um `git diff --exit-code` depois deste comando e vacuoso: como nada
e escrito, a arvore esta sempre limpa e a etapa nao verificaria nada. A prova
e o proprio codigo de saida.

Artefatos ficam co-localizados com a fonte canonica:

    domains/<adapter>/flags.yaml   ->  domains/<adapter>/generated/flags.py
                                       domains/<adapter>/generated/flags.ts
    contracts/events.schema.yaml   ->  contracts/generated/events.py
                                       contracts/generated/events.ts

Co-localizado, e nao sob range-core/, porque um artefato com nome de adapter
dentro do core exigiria excecao no check_core_boundary.py. Invariante com
excecao e invariante morto.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    GENERATED_DIR,
    REPO_ROOT,
    ContractError,
    Violation,
    fail,
    flag_contract_paths,
    events_contract_path,
    load_declared_event_types,
    load_declared_flags,
    parse_yaml,
    rel,
    report,
)

CHECK_FLAG = "--check"

HEADER_PY = "# Gerado por tools/codegen.py. Nao editar a mao."
HEADER_TS = "// Gerado por tools/codegen.py. Nao editar a mao."

RULE_MISSING = "CODEGEN - artefato gerado ausente"
RULE_DIVERGENT = "CODEGEN - artefato gerado divergente do contrato"

USAGE = (
    "uso: python tools/codegen.py --check\n"
    "  --check  compara os artefatos gerados com os contratos, sem escrever.\n"
    "\n"
    "A geracao efetiva chega na Fase 1, junto com os contratos que ela consome.\n"
    "Na Fase 0 este script e estritamente read-only."
)


def _identifier(name: str) -> str:
    out = []
    for char in name:
        out.append(char if char.isalnum() else "_")
    identifier = "".join(out).upper().strip("_")
    while "__" in identifier:
        identifier = identifier.replace("__", "_")
    if not identifier or identifier[0].isdigit():
        identifier = f"K_{identifier}"
    return identifier


def _bind(names: list[str], source: str) -> list[tuple[str, str]]:
    """Associa cada nome ao seu identificador, recusando colisao."""
    seen: dict[str, str] = {}
    pairs: list[tuple[str, str]] = []
    for name in sorted(names):
        identifier = _identifier(name)
        if identifier in seen:
            raise ContractError(
                f"{source}: '{name}' e '{seen[identifier]}' produzem o mesmo "
                f"identificador '{identifier}'"
            )
        seen[identifier] = name
        pairs.append((identifier, name))
    return pairs


def _render_python(pairs: list[tuple[str, str]], source: str, collection: str) -> str:
    lines = [HEADER_PY, f"# Fonte canonica: {source}", ""]
    for identifier, name in pairs:
        lines.append(f'{identifier} = "{name}"')
    lines.append("")
    if pairs:
        lines.append(f"{collection} = (")
        for identifier, _ in pairs:
            lines.append(f"    {identifier},")
        lines.append(")")
    else:
        lines.append(f"{collection} = ()")
    lines.append("")
    return "\n".join(lines)


def _render_typescript(pairs: list[tuple[str, str]], source: str, collection: str) -> str:
    lines = [HEADER_TS, f"// Fonte canonica: {source}", ""]
    for identifier, name in pairs:
        lines.append(f'export const {identifier} = "{name}";')
    lines.append("")
    if pairs:
        lines.append(f"export const {collection} = [")
        for identifier, _ in pairs:
            lines.append(f"  {identifier},")
        lines.append("] as const;")
    else:
        lines.append(f"export const {collection} = [] as const;")
    lines.append("")
    return "\n".join(lines)


def _expected_artifacts() -> dict[Path, tuple[str, str]]:
    """Mapeia artefato -> (conteudo canonico gerado em memoria, contrato de origem).

    O contrato de origem viaja junto porque a mensagem de violacao precisa
    citar QUEM exige o artefato, nao apenas qual arquivo falta. Sem isso,
    quem le a saida nao sabe onde intervir.
    """
    expected: dict[Path, tuple[str, str]] = {}

    for contract in flag_contract_paths(REPO_ROOT):
        data = parse_yaml(contract)
        source = rel(contract)
        if not isinstance(data, dict) or not isinstance(data.get("flags"), list):
            raise ContractError(f"{source}: esperado mapeamento com a chave 'flags'")
        names = []
        for position, entry in enumerate(data["flags"], start=1):
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise ContractError(f"{source}: item {position} de 'flags' sem 'name' valido")
            names.append(entry["name"])
        pairs = _bind(names, source)
        target = contract.parent / GENERATED_DIR
        expected[target / "flags.py"] = (_render_python(pairs, source, "ALL_FLAGS"), source)
        expected[target / "flags.ts"] = (_render_typescript(pairs, source, "ALL_FLAGS"), source)

    events_contract = events_contract_path(REPO_ROOT)
    if events_contract.is_file():
        source = rel(events_contract)
        pairs = _bind(list(load_declared_event_types(REPO_ROOT)), source)
        target = events_contract.parent / GENERATED_DIR
        expected[target / "events.py"] = (
            _render_python(pairs, source, "ALL_EVENT_TYPES"),
            source,
        )
        expected[target / "events.ts"] = (
            _render_typescript(pairs, source, "ALL_EVENT_TYPES"),
            source,
        )

    return expected


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def check() -> int:
    violations: list[Violation] = []
    try:
        expected = _expected_artifacts()
    except ContractError as exc:
        return fail(str(exc))

    for path in sorted(expected, key=lambda p: p.as_posix()):
        target = rel(path)
        content, source = expected[path]
        if not path.is_file():
            violations.append(
                Violation(
                    target,
                    0,
                    RULE_MISSING,
                    f"exigido por {source}, que declara nomes sem artefato "
                    "correspondente. Regenere as constantes.",
                )
            )
            continue
        try:
            current = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return fail(f"{target}: nao foi possivel ler ({exc})")
        if _normalise(current) != _normalise(content):
            violations.append(
                Violation(
                    target,
                    0,
                    RULE_DIVERGENT,
                    f"conteudo em disco difere do gerado a partir de {source}. "
                    "Regenere as constantes.",
                )
            )

    return report("CODEGEN - constantes fora de sincronia", violations)


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] != CHECK_FLAG:
        print(USAGE, file=sys.stderr)
        return 2
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
