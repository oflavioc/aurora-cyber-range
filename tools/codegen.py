#!/usr/bin/env python3
"""Constantes tipadas geradas a partir dos contratos — modo de verificacao.

01_ARCHITECTURE.md secao 5.4 e 06_ACCEPTANCE_TESTS.md T2.

Dois modos. `--check` e o unico que o CI invoca, e e estritamente read-only.
`--write` gera, e chegou na Fase 1 junto com os contratos que consome — era a
pendencia P2 do fase_0.md, adiada de proposito: modo de escrita sem contrato
real para consumir e sem probe que o exercite seria codigo nao verificado
dentro do proprio mecanismo de verificacao.

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
WRITE_FLAG = "--write"

HEADER_PY = "# Gerado por tools/codegen.py. Nao editar a mao."
HEADER_TS = "// Gerado por tools/codegen.py. Nao editar a mao."

RULE_MISSING = "CODEGEN - artefato gerado ausente"
RULE_DIVERGENT = "CODEGEN - artefato gerado divergente do contrato"

USAGE = (
    "uso: python tools/codegen.py --check | --write\n"
    "  --check  compara os artefatos gerados com os contratos, sem escrever.\n"
    "  --write  regenera os artefatos a partir dos contratos.\n"
    "\n"
    "O CI invoca apenas --check, que e estritamente read-only. Um\n"
    "`git diff --exit-code` depois dele e vacuoso: nada e escrito, a arvore\n"
    "esta sempre limpa, e a prova e o proprio codigo de saida."
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
    """Constantes Python ANOTADAS COM `Final`.

    07_IMPLEMENTATION_PHASES.md linha 55 pede constantes TIPADAS em Python e
    TypeScript. Os artefatos TS ja usavam `export const` e `as const`, que dao
    tipo literal e imutabilidade; os de Python eram atribuicao de modulo sem
    anotacao, inferida como `str` mutavel. `Final` fecha a diferenca e faz um
    type checker recusar reatribuicao. Foi o L2 da segunda auditoria da Fase 1.
    """
    lines = [
        HEADER_PY,
        f"# Fonte canonica: {source}",
        "",
        "from typing import Final",
        "",
    ]
    for identifier, name in pairs:
        lines.append(f'{identifier}: Final[str] = "{name}"')
    lines.append("")
    if pairs:
        lines.append(f"{collection}: Final[tuple[str, ...]] = (")
        for identifier, _ in pairs:
            lines.append(f"    {identifier},")
        lines.append(")")
    else:
        lines.append(f"{collection}: Final[tuple[str, ...]] = ()")
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


def write() -> int:
    """Geracao efetiva. Chega na Fase 1, junto com os contratos que consome.

    Era a pendencia P2 do fase_0.md, adiada de proposito: modo de escrita sem
    contrato real para consumir e sem probe que o exercite seria codigo nao
    verificado dentro do proprio mecanismo de verificacao.

    `--check` continua sendo o unico modo que o CI invoca, e continua
    estritamente read-only. Este modo e do desenvolvedor, e o probe do harness
    exercita os dois: gera, confere que `--check` passa, corrompe um artefato e
    confere que `--check` reprova.
    """
    try:
        expected = _expected_artifacts()
    except ContractError as exc:
        return fail(str(exc))

    escritos = 0
    for path in sorted(expected, key=lambda p: p.as_posix()):
        content, _ = expected[path]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            atual = path.read_text(encoding="utf-8") if path.is_file() else None
            # So escreve o que mudou: rodar duas vezes seguidas nao deve alterar
            # mtime a toa, e a saida diz o que de fato foi tocado.
            if atual is not None and _normalise(atual) == _normalise(content):
                continue
            path.write_text(content, encoding="utf-8", newline="\n")
        except OSError as exc:
            return fail(f"{rel(path)}: nao foi possivel escrever ({exc})")
        print(f"gerado: {rel(path)}")
        escritos += 1

    if escritos == 0:
        print("nada a gerar: artefatos ja em sincronia com os contratos.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in (CHECK_FLAG, WRITE_FLAG):
        print(USAGE, file=sys.stderr)
        return 2
    return check() if argv[0] == CHECK_FLAG else write()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
