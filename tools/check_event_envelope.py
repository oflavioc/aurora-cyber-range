#!/usr/bin/env python3
"""INVARIANTE 4 — nenhum evento emitido carrega objective_ids.

09_EVENT_MODEL.md secao 1.2 e 06_ACCEPTANCE_TESTS.md T1.

O binding evento -> objetivo ocorre na projecao, via observability_hooks.yaml.
Se a aplicacao souber que uma acao satisfaz um objetivo, o dominio passa a
conhecer o desenho de exercicio e a fronteira core/adapter vaza.

A varredura e por NEGACAO: todo range-core/ e todo domains/ sao caminho de
emissao, exceto as camadas de projecao e pontuacao, unico lugar onde o binding
e legitimo.

A versao anterior usava allowlist de segmentos ("events", "api") e por isso
nao enxergava range-core/engine/, /clock/, /state/, /telemetry/, /evidence/
nem /rubrics/ — sendo que 01_ARCHITECTURE.md secao 6 declara o inject-engine
como emissor de eventos de effect. Allowlist de diretorio falha em silencio a
cada diretorio novo; negacao por padrao falha para o lado seguro.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    REPO_ROOT,
    ContractError,
    Violation,
    fail,
    WEB_SUFFIXES,
    iter_files,
    parse_python,
    rel,
    report,
)

FORBIDDEN_FIELD = "objective_ids"

SCANNED_DIRS = ("range-core", "domains")
PYTHON_SUFFIXES = (".py",)

#: UNICOS caminhos onde o binding evento->objetivo e legitimo: as camadas de
#: projecao do core, de 09_EVENT_MODEL.md secao 5, no layout de
#: 01_ARCHITECTURE.md secao 2.
#:
#: ANCORADOS a partir da raiz, de proposito. Casar o segmento em qualquer
#: profundidade isentava domains/<adapter>/api/metrics/ — caminho de emissao de
#: adapter — porque tinha um segmento "metrics" no meio. Depois que a varredura
#: passou a ser por negacao, esta lista virou a UNICA fronteira do invariante 4:
#: isencao larga aqui e o mesmo que nao ter verificacao.
#:
#: Acrescentar prefixo aqui AFROUXA o invariante e exige justificativa contra
#: 09_EVENT_MODEL.md secao 1.2.
PROJECTION_PREFIXES = (
    ("range-core", "objectives"),
    ("range-core", "aar"),
    ("range-core", "metrics"),
    ("range-core", "calibration"),
)

RULE = "INVARIANTE 4 - objective_ids no caminho de emissao"
ADVICE = "O binding evento->objetivo ocorre na projecao, via observability_hooks.yaml."


def _is_emission_path(path: Path) -> bool:
    """Emissao por padrao; projecao so nos prefixos ancorados declarados acima."""
    parts = path.resolve().relative_to(REPO_ROOT).parts
    return not any(parts[: len(prefix)] == prefix for prefix in PROJECTION_PREFIXES)


def _hits(tree: ast.Module):
    """Localiza objective_ids como chave, keyword, atributo ou identificador."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == FORBIDDEN_FIELD:
            yield node.lineno, "chave ou literal"
        elif isinstance(node, ast.keyword) and node.arg == FORBIDDEN_FIELD:
            yield getattr(node.value, "lineno", 0), "argumento nomeado"
        elif isinstance(node, ast.Attribute) and node.attr == FORBIDDEN_FIELD:
            yield node.lineno, "acesso a atributo"
        elif isinstance(node, ast.Name) and node.id == FORBIDDEN_FIELD:
            yield node.lineno, "identificador"
        elif isinstance(node, ast.arg) and node.arg == FORBIDDEN_FIELD:
            yield node.lineno, "parametro"


#: `objective_ids` como TOKEN, nao como string literal. Em TS/TSX o campo
#: aparece como chave nua — `{ objective_ids: [...] }` —, que
#: `iter_web_string_literals` nao enxerga porque nao e literal de string.
_TOKEN_WEB = re.compile(rf"\b{FORBIDDEN_FIELD}\b")


def _hits_web(path: Path):
    """Ocorrencias do campo proibido em arquivo TS/TSX/JS.

    LEXICAL, nao AST: a stdlib nao traz analisador de TypeScript, e a mesma
    limitacao ja esta documentada em check_contract_literals.py. Deliberadamente
    CONSERVADOR — qualquer ocorrencia do token em caminho de emissao e violacao,
    inclusive em comentario. O campo e proibido no envelope inteiro (09 secao
    1.2); nao ha uso legitimo dele aqui que valha um falso negativo.

    Sem esta varredura, o invariante 4 saia rc=0 sobre todo o front-end: os
    outros dois verificadores de codigo ja cobriam WEB_SUFFIXES e este nao —
    verificador que sai zero sobre territorio que nao varre, a mesma classe do
    B1 da primeira auditoria da Fase 0. Latente enquanto nao ha `.ts` na arvore,
    real na Fase 4. Foi o M1 da primeira e da segunda auditoria da Fase 1.
    """
    try:
        texto = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"{rel(path)}: nao foi possivel ler ({exc})") from exc
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if _TOKEN_WEB.search(linha):
            yield numero, "campo em codigo web"


def main() -> int:
    violations: list[Violation] = []
    try:
        for path in iter_files(REPO_ROOT, SCANNED_DIRS, WEB_SUFFIXES):
            if not _is_emission_path(path):
                continue
            source = rel(path)
            for line, kind in _hits_web(path):
                violations.append(
                    Violation(
                        source,
                        line,
                        RULE,
                        f"'{FORBIDDEN_FIELD}' presente como {kind}. {ADVICE}",
                    )
                )

        for path in iter_files(REPO_ROOT, SCANNED_DIRS, PYTHON_SUFFIXES):
            if not _is_emission_path(path):
                continue
            tree = parse_python(path)
            source = rel(path)
            seen: set[tuple[int, str]] = set()
            for line, kind in _hits(tree):
                if (line, kind) in seen:
                    continue
                seen.add((line, kind))
                violations.append(
                    Violation(
                        source,
                        line,
                        RULE,
                        f"'{FORBIDDEN_FIELD}' presente como {kind}. {ADVICE}",
                    )
                )
    except ContractError as exc:
        return fail(str(exc))

    return report(RULE, violations)


if __name__ == "__main__":
    sys.exit(main())
