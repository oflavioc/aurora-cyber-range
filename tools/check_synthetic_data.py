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
import ipaddress
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

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
# Regras de excecao — constantes nomeadas, deliberadamente
# ---------------------------------------------------------------------------
#
# Uma regra de excecao enterrada no meio do codigo nao e auditavel. Todas as
# listas abaixo sao declaradas aqui, no topo, e cada uma cita a norma que a
# justifica. A primeira delas vai precisar crescer conforme novos tipos de
# artefato entrarem nos packs de cenario.

#: Ultimo rotulo que indica NOME DE ARQUIVO, nao dominio. Sem esta lista,
#: "relatorio.pdf" seria acusado de dominio nao reservado.
#: CRESCE conforme novos formatos de artefato aparecem nos packs.
NON_DOMAIN_TRAILING_LABELS = frozenset(
    {
        "bak", "cef", "conf", "csv", "eml", "env", "gz", "htm", "html", "ics",
        "ini", "jpeg", "jpg", "js", "json", "jsonl", "log", "md", "mjs", "pdf",
        "png", "py", "sh", "sql", "svg", "toml", "ts", "tsx", "txt", "webp",
        "xml", "yaml", "yml", "zip",
    }
)

#: TLDs reservados a documentacao, teste e uso local. RFC 2606 e RFC 6761.
RESERVED_TLDS = frozenset({"example", "invalid", "test", "localhost", "local"})

#: Dominios de segundo nivel reservados a documentacao. RFC 2606 secao 3.
RESERVED_DOMAINS = frozenset({"example.com", "example.net", "example.org"})

#: Faixas de documentacao. RFC 5737 (IPv4) e RFC 3849 (IPv6). Declaradas
#: explicitamente para nao depender da classificacao de is_private, que varia
#: entre versoes do modulo ipaddress.
DOCUMENTATION_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "2001:db8::/32",
    )
)

#: Diretorios de dado sintetico. Contratos (flags.yaml, schemas) ficam de
#: fora: nome de flag tem a mesma forma de hostname e seria falso positivo.
DATA_SUFFIXES = (".json", ".jsonl", ".yaml", ".yml", ".csv")

MAX_HOSTNAME_LENGTH = 253
MAX_LABEL_LENGTH = 63

#: CPF: 11 digitos nus, ou 14 caracteres no formato NNN.NNN.NNN-NN. Apenas
#: essas duas formas canonicas sao tratadas como candidato, para nao classificar
#: qualquer numero longo como identificador.
CPF_DIGITS = 11
CPF_FORMATTED_LENGTH = 14
CPF_DOT_POSITIONS = (3, 7)
CPF_DASH_POSITION = 11

RULE_IP = "DADO SINTETICO - endereco IP fora das faixas permitidas"
RULE_DOMAIN = "DADO SINTETICO - dominio fora das faixas reservadas"
RULE_IDENTIFIER = "DADO SINTETICO - CPF passa na validacao de digito verificador"


def _scanned_subdirs(root: Path) -> list[str]:
    subdirs = ["scenarios"]
    for adapter in adapter_names(root):
        subdirs.append(f"domains/{adapter}/seed")
        subdirs.append(f"domains/{adapter}/evidence_generators")
    return subdirs


# ---------------------------------------------------------------------------
# Classificacao de valores
# ---------------------------------------------------------------------------


def _ip_is_allowed(address: ipaddress._BaseAddress) -> bool:
    if any(address in network for network in DOCUMENTATION_NETWORKS):
        return True
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_unspecified
        or address.is_reserved
    )


def _cpf_candidate(value: str) -> str | None:
    """Digitos do CPF quando o valor esta numa das duas formas canonicas."""
    text = value.strip()
    if len(text) == CPF_DIGITS and text.isdigit():
        return text
    if len(text) == CPF_FORMATTED_LENGTH:
        if all(text[position] == "." for position in CPF_DOT_POSITIONS) and (
            text[CPF_DASH_POSITION] == "-"
        ):
            digits = text.replace(".", "").replace("-", "")
            if digits.isdigit():
                return digits
    return None


def _cpf_check_digits_valid(digits: str) -> bool:
    """Validacao oficial de CPF. Sequencia de digito repetido nunca e valida."""
    if len(digits) != CPF_DIGITS or len(set(digits)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(digits[i]) * (size + 1 - i) for i in range(size))
        expected = (total * 10) % 11
        if expected == 10:
            expected = 0
        if expected != int(digits[size]):
            return False
    return True


def _as_ip(value: str):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _hostname_candidates(value: str):
    """Extrai hostnames de um valor: URL, e-mail ou hostname nu."""
    text = value.strip()
    if not text:
        return
    if "://" in text:
        host = urlsplit(text).hostname
        if host:
            yield host
        return
    if "@" in text:
        _, _, tail = text.rpartition("@")
        if tail:
            yield tail.strip()
        return
    if " " in text or "/" in text:
        return
    yield text


def _is_hostname_shaped(host: str) -> bool:
    if len(host) > MAX_HOSTNAME_LENGTH:
        return False
    labels = host.rstrip(".").split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > MAX_LABEL_LENGTH:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not label.replace("-", "").isalnum():
            return False
        if not label.isascii():
            return False
    tail = labels[-1].lower()
    if not tail.isalpha() or len(tail) < 2:
        return False
    if tail in NON_DOMAIN_TRAILING_LABELS:
        return False
    return True


def _hostname_is_allowed(host: str) -> bool:
    labels = host.rstrip(".").lower().split(".")
    if labels[-1] in RESERVED_TLDS:
        return True
    return ".".join(labels[-2:]) in RESERVED_DOMAINS


def _check_string(value: str, source: str, exempt: frozenset[str], violations: list[Violation]):
    if value in exempt:
        return

    cpf = _cpf_candidate(value)
    if cpf is not None:
        if _cpf_check_digits_valid(cpf):
            violations.append(
                Violation(
                    source,
                    0,
                    RULE_IDENTIFIER,
                    f"'{value}' e um CPF valido. 05_SECURITY_REQUIREMENTS secao 3 "
                    "exige que CPF sintetico FALHE a validacao de digito "
                    "verificador; caso contrario e indistinguivel de dado real.",
                )
            )
        return

    address = _as_ip(value)
    if address is not None:
        if not _ip_is_allowed(address):
            violations.append(
                Violation(
                    source,
                    0,
                    RULE_IP,
                    f"'{value}' nao esta em faixa privada nem de documentacao "
                    "(RFC 1918, RFC 5737, RFC 3849).",
                )
            )
        return

    for host in _hostname_candidates(value):
        if host in exempt:
            continue
        candidate = _as_ip(host)
        if candidate is not None:
            if not _ip_is_allowed(candidate):
                violations.append(
                    Violation(
                        source,
                        0,
                        RULE_IP,
                        f"'{host}' nao esta em faixa privada nem de documentacao.",
                    )
                )
            continue
        if _is_hostname_shaped(host) and not _hostname_is_allowed(host):
            violations.append(
                Violation(
                    source,
                    0,
                    RULE_DOMAIN,
                    f"'{host}' nao esta em faixa reservada a documentacao "
                    "(RFC 2606, RFC 6761).",
                )
            )


def _walk(value, source: str, exempt: frozenset[str], violations: list[Violation]) -> None:
    if isinstance(value, str):
        _check_string(value, source, exempt, violations)
    elif isinstance(value, dict):
        for item in value.values():
            _walk(item, source, exempt, violations)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, source, exempt, violations)


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
