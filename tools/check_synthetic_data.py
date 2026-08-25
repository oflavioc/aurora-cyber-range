#!/usr/bin/env python3
"""DADOS SINTETICOS — 05_SECURITY_REQUIREMENTS.md secao 3.

Tres categorias, conforme 06_ACCEPTANCE_TESTS.md T15 e
docs/process/PHASE_0_CHECKLIST.md: IPs, dominios e IDENTIFICADORES.

Nenhum IP roteavel de terceiro, nenhum dominio registrado real em dado de
cenario, seed ou gerador de evidencia. Enderecos ficam nas faixas privadas ou
de documentacao (RFC 1918, RFC 5737, RFC 3849); dominios ficam nas faixas
reservadas a documentacao e teste (RFC 2606, RFC 6761).

Identificador: CPF sintetico deve FALHAR a validacao de digito verificador
(05_SECURITY_REQUIREMENTS.md secao 3). CPF valido em dado de cenario e
indistinguivel de CPF real, e e a diferenca entre dado ficticio e dado
pessoal.

Este e o unico dos seis verificadores que nao opera sobre AST: o alvo e dado,
nao codigo. A leitura e estrutural mesmo assim — json, csv e o subconjunto
YAML sao analisados e os VALORES sao percorridos. Nao ha varredura textual do
arquivo bruto.

Limites conhecidos, declarados de proposito para que a lacuna seja rastreavel
em vez de silenciosa:

1. Arquivos sem gramatica declarada (.log, .eml, .txt, CEF) nao sao cobertos.
   Quando o evidence-simulator da Fase 9 passar a emiti-los, a verificacao
   correspondente precisa ser projetada junto com o formato.

2. Dos identificadores, apenas CPF e verificado — e o unico que
   05_SECURITY_REQUIREMENTS.md secao 3 nomeia. CNPJ, PIS/PASEP, titulo de
   eleitor, matricula institucional e RG (que nao tem digito verificador
   padronizado nacional) ficam de fora ate existir requisito que os nomeie.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    REPO_ROOT,
    ContractError,
    Violation,
    adapter_names,
    fail,
    iter_files,
    load_declared_event_types,
    load_declared_flags,
    parse_yaml,
    rel,
    report,
)

# ---------------------------------------------------------------------------
# O PREDICADO SAIU DAQUI — `dados_sinteticos/`, e o movimento e da peca 3 da
# Fase 7.
#
# As constantes de excecao e a classificacao de valor viviam neste arquivo desde
# a Fase 0, e ele varre a ARVORE VERSIONADA. `scenarios/` esta fora do Git desde
# a peca 5 da Fase 5 — entao o PACK, que e onde o gabarito e o ator de ameaca
# moram, nunca passou por aqui.
#
# A P7-7 cobra o verificador do `threat_actor` declarado, e a exigencia de `05`
# §5.2 que e mecanizavel — *"nenhum IOC operacional"* — E A MESMA PERGUNTA que
# este arquivo ja respondia, sobre um artefato que ele nao alcanca.
#
# Reimplementa-la no `range-cli scenario lint` seria a D4 com outro nome: duas
# respostas para a mesma pergunta, divergindo no dia em que uma das faixas
# mudasse. E a divergencia aqui NAO FALHA ALTO — ela deixa passar.
#
# O QUE FICOU NESTE ARQUIVO e a VARREDURA: quais diretorios, quais formatos,
# quais isencoes. E ai que os dois chamadores legitimamente diferem — um
# percorre a arvore por diretorio, o outro percorre o documento de um pack.
#
# `dados_sinteticos` e stdlib pura e de TOPO pelo mesmo motivo que este job nao
# instala nada. O `sys.path` abaixo o alcanca pela raiz derivada de `__file__`,
# entao ele resolve com ou sem instalacao.
# ---------------------------------------------------------------------------

sys.path.insert(0, str(REPO_ROOT))

from dados_sinteticos import (  # noqa: E402
    RULE_DOMAIN,
    RULE_IDENTIFIER,
    RULE_IP,
    achados_na_arvore,
)

#: Diretorios de dado sintetico. Contratos (flags.yaml, schemas) ficam de
#: fora: nome de flag tem a mesma forma de hostname e seria falso positivo.
DATA_SUFFIXES = (".json", ".jsonl", ".yaml", ".yml", ".csv")


def _scanned_subdirs(root: Path) -> list[str]:
    subdirs = ["scenarios"]
    for adapter in adapter_names(root):
        subdirs.append(f"domains/{adapter}/seed")
        subdirs.append(f"domains/{adapter}/evidence_generators")
    return subdirs


def _walk(value, source: str, exempt: frozenset[str], violations: list[Violation]) -> None:
    """A travessia, agora um EMBRULHO: o predicado e de `dados_sinteticos`.

    A `Violation` de `tools/_common` continua sendo o vocabulario deste
    verificador — o modulo compartilhado devolve `Achado`, sem opiniao sobre
    onde ele apareceu, e cada chamador acrescenta a localizacao que so ele
    conhece. Aqui e arquivo e linha; no linter de pack e o caminho de instancia.
    """
    for achado in achados_na_arvore(value, isentos=exempt):
        violations.append(Violation(source, 0, achado.regra, achado.detalhe))


# ---------------------------------------------------------------------------
# Leitura por formato
# ---------------------------------------------------------------------------


def _load(path: Path):
    suffix = path.suffix.lower()
    source = rel(path)
    if suffix in (".yaml", ".yml"):
        return [parse_yaml(path)]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"{source}: nao foi possivel ler ({exc})") from exc

    if suffix == ".json":
        try:
            return [json.loads(text)]
        except json.JSONDecodeError as exc:
            raise ContractError(f"{source}:{exc.lineno}: JSON invalido ({exc.msg})") from exc
    if suffix == ".jsonl":
        documents = []
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                documents.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ContractError(f"{source}:{number}: JSONL invalido ({exc.msg})") from exc
        return documents
    if suffix == ".csv":
        return [list(csv.reader(text.splitlines()))]
    return []


def main() -> int:
    violations: list[Violation] = []
    try:
        # Nome de flag e de event_type tem a mesma forma de hostname. Sao
        # termos de contrato, nao dado sintetico: isentos por leitura do
        # contrato, nao por lista embutida.
        exempt = frozenset(load_declared_flags(REPO_ROOT)) | frozenset(
            load_declared_event_types(REPO_ROOT)
        )

        for path in iter_files(REPO_ROOT, _scanned_subdirs(REPO_ROOT), DATA_SUFFIXES):
            source = rel(path)
            for document in _load(path):
                _walk(document, source, exempt, violations)
    except ContractError as exc:
        return fail(str(exc))

    return report("DADOS SINTETICOS - 05_SECURITY_REQUIREMENTS secao 3", violations)


if __name__ == "__main__":
    sys.exit(main())
