#!/usr/bin/env python3
"""INVARIANTE 2 — nenhuma string literal de flag ou de event_type no codigo.

00_MASTER_SPEC.md secao 5.1, 01_ARCHITECTURE.md secao 5.4 e 09_EVENT_MODEL.md
secao 4.

O verificador le os contratos canonicos e so entao varre o codigo por AST.
Essa ordem importa: a autoridade sobre o que e uma flag e o contrato, nao um
padrao textual. Um literal so e violacao porque o contrato o declara.

Duas deteccoes complementares:

1. literal exatamente igual a um nome declarado em domains/<adapter>/flags.yaml
   ou no catalogo contracts/events.schema.yaml;
2. literal com forma de flag de um adapter existente (`<adapter>.<nome>`) que
   NAO esta declarado — erro de digitacao que a deteccao 1 nao pegaria e que
   em runtime viraria flag desconhecida.

A lista de adapters vem de domains/<adapter>/, nao de uma constante embutida.

Python e TypeScript sao varridos. 01_ARCHITECTURE.md secao 5.4 exige constante
gerada para as DUAS linguagens, e o layout da secao 2 coloca range-core/web/ e
domains/<adapter>/web/ em TypeScript: cobrir so Python deixaria literal de flag
em TSX passar pelo gate real do CI, mesmo com o hook rapido acusando.

Python usa AST. TypeScript usa varredura lexica, porque a stdlib nao traz
analisador de TypeScript — ver iter_web_string_literals em _common.py, onde o
limite esta declarado.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    parse_yaml,
    GENERATED_DIR,
    REPO_ROOT,
    WEB_SUFFIXES,
    ContractError,
    Violation,
    adapter_names,
    fail,
    iter_files,
    iter_web_string_literals,
    load_declared_event_types,
    load_declared_flags,
    parse_python,
    rel,
    report,
)

#: Onde literais de flag e de event_type sao legitimos, ANCORADO a partir da
#: raiz: contracts/ guarda as fontes canonicas, domains/<adapter>/generated/ e
#: contracts/generated/ guardam os artefatos, tools/codegen.py os produz.
#:
#: Casar o segmento em qualquer profundidade autorizava
#: domains/<adapter>/api/contracts/handler.py a conter literal de flag, so por
#: ter um segmento "contracts" no meio do caminho. Isencao e a excecao ao
#: invariante 2: larga demais, ela o anula.
AUTHORIZED_FILES = frozenset({"tools/codegen.py"})
CONTRACTS_ROOT = "contracts"
DOMAINS_ROOT = "domains"

#: `tests` ENTROU na quarta auditoria da Fase 3 (M4), e entrou tarde. O item 4 da
#: DoD da Fase 3 diz *"nenhuma string solta de flag no codigo-fonte, verificado
#: por lint"*, e `06` T2 nao restringe diretorio — mas a varredura excluia
#: justamente `tests/`, que e onde esta fase escreveu nome de flag. O que barrou a
#: primeira versao de `tests/test_api_degradacao.py` foi o hook
#: `check_architecture.py`, que se declara NAO-GATE no proprio cabecalho: o item
#: estava provado por um mecanismo cujo escopo excluia o unico diretorio em que a
#: fase correu o risco. Classe "verificacao que parece existir", 7.3 do registro.
#:
#: `scripts` FICA DE FORA, e e decisao declarada, nao esquecimento: os
#: `*_probes.py` plantam literal de flag DE PROPOSITO — a violacao plantada e o
#: que prova que o verificador reprova. Varre-los seria reprovar a propria prova
#: negativa. O dia em que `scripts/` tiver codigo de producao, esta linha muda.
SCANNED_DIRS = ("range-core", "domains", "tests")
PYTHON_SUFFIXES = (".py",)

RULE_DECLARED = "INVARIANTE 2 - literal de contrato no codigo"
RULE_UNDECLARED = "INVARIANTE 2 - literal com forma de flag nao declarada"
#: Invariante 3: event_type fora do catalogo, em YAML de instrumentacao.
RULE_HOOK_EVENT = "INVARIANTE 3 - event_type de hook fora do catalogo"


def _is_authorized(path: Path) -> bool:
    relative = path.resolve().relative_to(REPO_ROOT)
    if relative.as_posix() in AUTHORIZED_FILES:
        return True
    parts = relative.parts
    # contracts/... (inclui contracts/generated/)
    if parts[:1] == (CONTRACTS_ROOT,):
        return True
    # domains/<adapter>/generated/...
    return len(parts) > 3 and parts[0] == DOMAINS_ROOT and parts[2] == GENERATED_DIR


def _string_constants(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node


def _looks_like_flag(value: str, adapters: frozenset[str]) -> bool:
    head, separator, tail = value.partition(".")
    if not separator or head not in adapters:
        return False
    if not tail:
        return False
    return all(part.replace("_", "").isalnum() for part in tail.split(".") if part)


def _judge(
    value: str,
    source: str,
    line: int,
    declared_flags: dict[str, str],
    declared_events: dict[str, str],
    adapters: frozenset[str],
    violations: list[Violation],
) -> None:
    if value in declared_flags:
        violations.append(
            Violation(
                source,
                line,
                RULE_DECLARED,
                f"literal '{value}' declarado em {declared_flags[value]}. "
                "Use a constante gerada.",
            )
        )
    elif value in declared_events:
        violations.append(
            Violation(
                source,
                line,
                RULE_DECLARED,
                f"event_type '{value}' declarado em {declared_events[value]}. "
                "Use a constante gerada.",
            )
        )
    elif _looks_like_flag(value, adapters):
        violations.append(
            Violation(
                source,
                line,
                RULE_UNDECLARED,
                f"literal '{value}' tem forma de flag de um adapter existente "
                "mas nao esta declarado em nenhum flags.yaml.",
            )
        )


def main() -> int:
    violations: list[Violation] = []
    try:
        declared_flags = load_declared_flags(REPO_ROOT)
        declared_events = load_declared_event_types(REPO_ROOT)
        adapters = frozenset(adapter_names(REPO_ROOT))

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            if _is_authorized(path):
                continue
            source = rel(path)
            for node in _string_constants(parse_python(path)):
                _judge(
                    node.value, source, node.lineno,
                    declared_flags, declared_events, adapters, violations,
                )

        # ---------------------------------------------------------------
        # observability_hooks.yaml — 09_EVENT_MODEL.md secao 6.
        #
        # Este arquivo CARREGA event_type e nao era varrido por ninguem: a
        # varredura de codigo cobre .py e WEB_SUFFIXES, nunca .yaml, e nenhum
        # contrato de `contracts/` o valida.
        # `audit_query_perfomed` aqui saia rc=0 em todos os gates.
        #
        # E exatamente a falha que 09 secao 4 chama de "a mais cara possivel":
        # o event_type com erro de digitacao nunca dispara, a evidencia `auto`
        # do objetivo nunca e coletada, e ninguem percebe ate o exercicio ao
        # vivo. O invariante 3 diz "nenhum event_type fora do catalogo" sem
        # restringir a linguagem do arquivo. M4 da segunda auditoria da Fase 1.
        # ---------------------------------------------------------------
        for path in sorted((REPO_ROOT / "domains").glob("*/observability_hooks.yaml")):
            dados = parse_yaml(path) or {}
            source = rel(path)
            for posicao, hook in enumerate(dados.get("hooks") or [], start=1):
                if not isinstance(hook, dict):
                    continue
                nome = hook.get("event_type")
                if isinstance(nome, str) and nome and nome not in declared_events:
                    violations.append(
                        Violation(
                            source,
                            posicao,
                            RULE_HOOK_EVENT,
                            f"hook {posicao}: event_type '{nome}' nao esta no catalogo "
                            f"de contracts/events.schema.yaml.",
                        )
                    )

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, WEB_SUFFIXES):
            if _is_authorized(path):
                continue
            source = rel(path)
            for line, value in iter_web_string_literals(path):
                _judge(
                    value, source, line,
                    declared_flags, declared_events, adapters, violations,
                )
    except ContractError as exc:
        return fail(str(exc))

    return report("INVARIANTE 2 - literais de contrato", violations)


if __name__ == "__main__":
    sys.exit(main())
