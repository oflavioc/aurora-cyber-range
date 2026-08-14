#!/usr/bin/env python3
"""Utilitarios compartilhados dos verificadores da Fase 0.

Restricoes desta fase (docs/process/PHASE_0_CHECKLIST.md, secao "Interfaces
obrigatorias"):

1. somente stdlib;
2. nenhuma funcao aqui escreve em disco;
3. saida deterministica (varreduras e relatorios sempre ordenados);
4. mensagens em ASCII, para nao depender do codepage do console no Windows.

Codigos de saida usados pelos verificadores:

    0  arvore valida
    1  violacao encontrada
    2  erro de ferramenta ou de contrato malformado

Os tres codigos sao distintos de proposito, e scripts/phase0_negative_tests.py
exige EXATAMENTE 1 para contar como deteccao. Um verificador que sai 2 quebrou
ao ser executado — nao enxergou a violacao — e tratar isso como deteccao faria
o teste negativo provar o oposto do que promete.

Nao relaxe esta distincao: reportar violacao com 2, ou erro de ferramenta com
1, derruba a garantia do teste negativo sem que nada fique vermelho.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_ERROR = 2

#: Diretorios que nenhuma varredura deve percorrer.
PRUNED_DIRS = frozenset(
    {
        ".git",
        ".aurora-worktrees",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
    }
)

#: Nome do diretorio de artefatos gerados, co-localizado com a fonte canonica.
GENERATED_DIR = "generated"


class Violation(NamedTuple):
    """Uma violacao localizada. `line` é 0 quando nao ha linha aplicavel."""

    path: str
    line: int
    rule: str
    detail: str


class ContractError(Exception):
    """Contrato ausente, malformado ou em forma nao reconhecida."""


# ---------------------------------------------------------------------------
# Caminhos e varredura
# ---------------------------------------------------------------------------


def rel(path: Path) -> str:
    """Caminho relativo a raiz, sempre com barra normal, para saida estavel."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_pruned(path: Path, root: Path) -> bool:
    return any(part in PRUNED_DIRS for part in path.relative_to(root).parts)


def iter_files(
    root: Path,
    subdirs: Iterable[str],
    suffixes: Iterable[str],
    exclude_parts: Iterable[str] = (),
) -> Iterator[Path]:
    """Percorre `subdirs` sob `root`, em ordem deterministica.

    Subdiretorio inexistente e ignorado em silencio: na Fase 0 a arvore ainda
    nao tem range-core/, domains/, contracts/ nem scenarios/.
    """
    wanted = {s.lower() for s in suffixes}
    blocked = set(exclude_parts)
    for subdir in sorted(subdirs):
        base = root / subdir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in wanted:
                continue
            if _is_pruned(path, root):
                continue
            if blocked and any(part in blocked for part in path.relative_to(root).parts):
                continue
            yield path


#: Sufixos de front-end. 01_ARCHITECTURE.md secao 2 coloca range-core/web/ e
#: domains/<adapter>/web/ em TypeScript, e secao 5.4 exige constantes geradas
#: para Python E TypeScript.
WEB_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts")


def iter_web_string_literals(path: Path):
    """Literais de string de arquivo TS/JS, por varredura lexica.

    A stdlib nao traz analisador de TypeScript, entao isto e um lexer pequeno
    que acompanha estado de aspas e de comentario. Nao e grep — comentario e
    escape sao respeitados — mas tambem nao e AST, e a diferenca esta
    declarada aqui de proposito.

    Limite conhecido: literal de expressao regular (/.../) nao e reconhecido
    como tal, entao uma regex contendo aspas pode dessincronizar o estado. O
    efeito e falso NEGATIVO (um literal deixa de ser visto), nunca travamento,
    porque a comparacao final e contra o conjunto declarado no contrato.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"{rel(path)}: nao foi possivel ler ({exc})") from exc

    line = 1
    index = 0
    size = len(text)
    while index < size:
        char = text[index]

        if char == "\n":
            line += 1
            index += 1
            continue

        if char == "/" and index + 1 < size:
            following = text[index + 1]
            if following == "/":
                while index < size and text[index] != "\n":
                    index += 1
                continue
            if following == "*":
                index += 2
                while index + 1 < size and not (text[index] == "*" and text[index + 1] == "/"):
                    if text[index] == "\n":
                        line += 1
                    index += 1
                index += 2
                continue

        if char in "\"'`":
            quote = char
            opened_at = line
            index += 1
            buffer: list[str] = []
            while index < size:
                current = text[index]
                if current == "\\" and index + 1 < size:
                    buffer.append(text[index + 1])
                    index += 2
                    continue
                if current == quote:
                    index += 1
                    break
                if current == "\n":
                    line += 1
                buffer.append(current)
                index += 1
            yield opened_at, "".join(buffer)
            continue

        index += 1


def parse_python(path: Path) -> ast.Module:
    """Le e analisa um arquivo Python.

    Erro de sintaxe vira ContractError em vez de arquivo silenciosamente
    pulado: um verificador que ignora o que nao consegue analisar e um
    verificador contornavel.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"{rel(path)}: nao foi possivel ler ({exc})") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ContractError(
            f"{rel(path)}:{exc.lineno or 0}: nao foi possivel analisar por AST ({exc.msg})"
        ) from exc


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------


def report(title: str, violations: list[Violation]) -> int:
    if not violations:
        return EXIT_OK
    ordered = sorted(violations)
    print(f"{title}: {len(ordered)} violacao(oes)", file=sys.stdout)
    for item in ordered:
        where = f"{item.path}:{item.line}" if item.line else item.path
        print(f"  {where}", file=sys.stdout)
        print(f"    {item.rule}: {item.detail}", file=sys.stdout)
    return EXIT_VIOLATION


def fail(message: str) -> int:
    print(f"ERRO DE CONTRATO: {message}", file=sys.stderr)
    return EXIT_ERROR


# ---------------------------------------------------------------------------
# YAML: subconjunto estrito
# ---------------------------------------------------------------------------
#
# A Fase 0 proibe dependencia externa, entao nao ha PyYAML. Este parser cobre
# deliberadamente um subconjunto pequeno e RECUSA o que nao entende. Um parser
# tolerante seria pior que grep: faria o verificador passar por ter lido o
# contrato errado, em silencio.
#
# Suportado: mapeamentos e sequencias em bloco, sequencias em fluxo ([a, b]),
# escalares nus ou entre aspas, booleanos, nulos, inteiros e floats,
# comentarios e um unico documento.
#
# Recusado: ancoras, aliases, merge keys, escalares multilinha (| e >),
# mapeamentos em fluxo ({a: b}), tabulacao na indentacao e multiplos documentos.


class YamlError(ContractError):
    pass


def _strip_comment(text: str) -> str:
    out: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is not None:
            if quote == '"' and char == "\\" and index + 1 < len(text):
                out.append(char)
                out.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            out.append(char)
        elif char in "\"'":
            quote = char
            out.append(char)
        elif char == "#" and (not out or out[-1].isspace()):
            break
        else:
            out.append(char)
        index += 1
    return "".join(out).rstrip()


def _scan_lines(text: str, source: str) -> list[list]:
    lines: list[list] = []
    seen_document = False
    for number, raw in enumerate(text.splitlines(), start=1):
        leading = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise YamlError(f"{source}:{number}: tabulacao na indentacao nao e suportada")
        content = _strip_comment(raw)
        stripped = content.strip()
        if not stripped:
            continue
        if stripped == "---":
            if seen_document:
                raise YamlError(f"{source}:{number}: multiplos documentos nao suportados")
            seen_document = True
            continue
        if stripped == "..." or stripped.startswith(("&", "*", "<<")):
            raise YamlError(f"{source}:{number}: ancora, alias ou merge key nao suportado")
        indent = len(content) - len(content.lstrip())
        lines.append([indent, stripped, number])
    return lines


def _split_flow(text: str, source: str, number: int) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in text:
        if quote is not None:
            if char == quote:
                quote = None
            current.append(char)
        elif char in "\"'":
            quote = char
            current.append(char)
        elif char == ",":
            parts.append("".join(current).strip())
            current = []
        elif char in "[]{}":
            raise YamlError(f"{source}:{number}: sequencia em fluxo aninhada nao suportada")
        else:
            current.append(char)
    if quote is not None:
        raise YamlError(f"{source}:{number}: aspas nao fechadas")
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_scalar(text: str, source: str, number: int):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _parse_value(text: str, source: str, number: int):
    if text.startswith(("|", ">")):
        raise YamlError(f"{source}:{number}: escalar multilinha nao suportado")
    if text.startswith("{"):
        raise YamlError(f"{source}:{number}: mapeamento em fluxo nao suportado")
    if text.startswith("["):
        if not text.endswith("]"):
            raise YamlError(f"{source}:{number}: sequencia em fluxo nao fechada")
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part, source, number) for part in _split_flow(inner, source, number)]
    return _parse_scalar(text, source, number)


def _split_key(text: str) -> tuple[str, str] | None:
    quote: str | None = None
    for index, char in enumerate(text):
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == ":":
            if index + 1 == len(text) or text[index + 1] == " ":
                return text[:index].strip(), text[index + 1 :].strip()
    return None


def _is_sequence_line(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _parse_block(lines: list[list], index: int, indent: int, source: str):
    if _is_sequence_line(lines[index][1]):
        return _parse_sequence(lines, index, indent, source)
    return _parse_mapping(lines, index, indent, source)


def _parse_sequence(lines: list[list], index: int, indent: int, source: str):
    items: list = []
    while index < len(lines) and lines[index][0] == indent and _is_sequence_line(lines[index][1]):
        number = lines[index][2]
        after = lines[index][1][1:]
        rest = after.strip()
        if not rest:
            index += 1
            if index < len(lines) and lines[index][0] > indent:
                value, index = _parse_block(lines, index, lines[index][0], source)
            else:
                value = None
            items.append(value)
            continue
        inner_indent = indent + 1 + (len(after) - len(after.lstrip()))
        lines[index] = [inner_indent, rest, number]
        if _split_key(rest) is not None:
            value, index = _parse_mapping(lines, index, inner_indent, source)
        else:
            value = _parse_value(rest, source, number)
            index += 1
        items.append(value)
    return items, index


def _parse_mapping(lines: list[list], index: int, indent: int, source: str):
    result: dict = {}
    while index < len(lines) and lines[index][0] == indent:
        content = lines[index][1]
        number = lines[index][2]
        if _is_sequence_line(content):
            break
        split = _split_key(content)
        if split is None:
            raise YamlError(f"{source}:{number}: linha nao e um par 'chave: valor'")
        raw_key, rest = split
        key = _parse_scalar(raw_key, source, number)
        if rest == "":
            index += 1
            if index < len(lines) and lines[index][0] > indent:
                value, index = _parse_block(lines, index, lines[index][0], source)
            elif (
                index < len(lines)
                and lines[index][0] == indent
                and _is_sequence_line(lines[index][1])
            ):
                value, index = _parse_sequence(lines, index, indent, source)
            else:
                value = None
        else:
            value = _parse_value(rest, source, number)
            index += 1
        if key in result:
            raise YamlError(f"{source}:{number}: chave duplicada '{key}'")
        result[key] = value
    return result, index


def parse_yaml(path: Path):
    """Analisa `path` como YAML do subconjunto suportado."""
    source = rel(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise YamlError(f"{source}: nao foi possivel ler ({exc})") from exc
    lines = _scan_lines(text, source)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0][0], source)
    if index != len(lines):
        raise YamlError(
            f"{source}:{lines[index][2]}: indentacao inconsistente ou conteudo inesperado"
        )
    return value


# ---------------------------------------------------------------------------
# Contratos
# ---------------------------------------------------------------------------


def flag_contract_paths(root: Path) -> list[Path]:
    """`domains/<adapter>/flags.yaml`, em ordem deterministica."""
    base = root / "domains"
    if not base.is_dir():
        return []
    found = [p for p in base.glob("*/flags.yaml") if p.is_file()]
    return sorted(found, key=lambda p: p.as_posix())


def events_contract_path(root: Path) -> Path:
    return root / "contracts" / "events.schema.yaml"


def load_declared_flags(root: Path) -> dict[str, str]:
    """Mapeia nome de flag -> contrato que a declara."""
    declared: dict[str, str] = {}
    for path in flag_contract_paths(root):
        data = parse_yaml(path)
        source = rel(path)
        if not isinstance(data, dict) or "flags" not in data:
            raise ContractError(f"{source}: esperado mapeamento com a chave 'flags'")
        entries = data["flags"]
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise ContractError(f"{source}: 'flags' deve ser uma sequencia")
        for position, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or "name" not in entry:
                raise ContractError(f"{source}: item {position} de 'flags' sem chave 'name'")
            name = entry["name"]
            if not isinstance(name, str) or not name:
                raise ContractError(f"{source}: item {position} de 'flags' com 'name' invalido")
            declared[name] = source
    return declared


#: Prefixo dos `$defs` que carregam o catalogo, um por truth_layer.
EVENT_TYPE_DEF_PREFIX = "event_type_"


def load_declared_event_types(root: Path) -> dict[str, str]:
    """Mapeia event_type -> contrato que o declara.

    O contrato e JSON Schema (decisao D4 da Fase 1). O catalogo vive nos `$defs`
    prefixados `event_type_`, um por truth_layer, cada um um `enum` de strings.
    Ler o `enum` diretamente evita manter uma segunda copia da lista so para o
    codegen — a lista que o validador usa e a mesma que gera as constantes.

    O catalogo so existe a partir da Fase 1. Contrato ausente devolve conjunto
    vazio; presente em forma nao reconhecida levanta erro, em vez de devolver
    vazio e enfraquecer o verificador em silencio.
    """
    path = events_contract_path(root)
    if not path.is_file():
        return {}
    data = parse_yaml(path)
    source = rel(path)
    if not isinstance(data, dict):
        raise ContractError(f"{source}: esperado mapeamento no topo")

    defs = data.get("$defs")
    if not isinstance(defs, dict):
        raise ContractError(f"{source}: '$defs' ausente ou nao e mapeamento")

    layer_defs = sorted(k for k in defs if k.startswith(EVENT_TYPE_DEF_PREFIX))
    if not layer_defs:
        raise ContractError(
            f"{source}: nenhum '$defs/{EVENT_TYPE_DEF_PREFIX}<truth_layer>' encontrado"
        )

    names: dict[str, str] = {}
    for key in layer_defs:
        entry = defs[key]
        if not isinstance(entry, dict):
            raise ContractError(f"{source}: '$defs/{key}' deve ser um mapeamento")
        values = entry.get("enum")
        if not isinstance(values, list) or not values:
            raise ContractError(f"{source}: '$defs/{key}' sem 'enum' nao vazio")
        for value in values:
            if not isinstance(value, str) or not value:
                raise ContractError(f"{source}: '$defs/{key}' com entrada nao textual")
            if value in names:
                raise ContractError(f"{source}: event_type duplicado no catalogo: '{value}'")
            names[value] = source

    return names


def adapter_names(root: Path) -> list[str]:
    """Adapters declarados por `domains/<adapter>/`."""
    base = root / "domains"
    if not base.is_dir():
        return []
    return sorted(
        p.name for p in base.iterdir() if p.is_dir() and p.name not in PRUNED_DIRS
    )
