"""*"Este valor é dado sintético?"* — uma implementação, dois chamadores.

AUTORIDADE
----------
`05_SECURITY_REQUIREMENTS.md` §3 (faixas de IP, domínio e identificador) e §5.2
(nenhum IOC operacional quando o cenário usa ator de ameaça real).
`06_ACCEPTANCE_TESTS.md` T15.

POR QUE ESTE PACOTE EXISTE, E POR QUE ELE É DE TOPO
----------------------------------------------------
`tools/check_synthetic_data.py` responde essa pergunta desde a Fase 0, e varre a
**árvore versionada**. `scenarios/` está fora do Git desde a decisão da peça 5 da
Fase 5 — então o **pack**, que é justamente onde o gabarito e o ator de ameaça
moram, nunca passou por ele.

A P7-7 cobra o verificador do `threat_actor` declarado, e a exigência de `05`
§5.2 que é mecanizável é *"nenhum IOC operacional"* — sem hash de amostra real,
sem IP ou domínio de infraestrutura real. Essa é **a mesma pergunta** que o
verificador da Fase 0 já responde, sobre um artefato que ele não alcança.

Reimplementá-la no linter seria a D4 com outro nome: duas respostas para a mesma
pergunta, divergindo no dia em que uma das faixas mudasse — e a divergência aqui
não falha alto, ela deixa passar. É a mesma razão que tirou as regras
`x-aurora-*` de dentro de um gate e as pôs em `range-core/engine/loader/contract_rules.py`.

**DE TOPO, e stdlib puro, porque os dois chamadores vivem em mundos diferentes:**

| Chamador | Como ele roda |
|---|---|
| `tools/check_synthetic_data.py` | `python tools/x.py` no job `arquitetura`, que **não instala nada** — stdlib pura desde a Fase 0, *"o CI da Fase 0 não pode depender da aplicação"* |
| `range_cli/lint.py` | pacote instalado, importado por nome |

Pôr o predicado em `tools/` deixaria o `range-cli` instalado sem ele — `tools`
não está em `packages` do `pyproject.toml`, e o import resolveria só com o CWD na
raiz. É literalmente a assimetria que aquele arquivo declara ter pago três vezes.
Pôr em `range-core/` faria `tools/` importar a aplicação, que é o que a pureza do
job existe para impedir. Sobra o topo.

O QUE ESTE MÓDULO **NÃO** FAZ
------------------------------
Não lê arquivo, não conhece caminho, não sabe o que é um pack. Ele classifica
**valores**. Quem varre é o chamador: um percorre a árvore versionada por
diretório, o outro percorre o documento do pack. A varredura é onde os dois
legitimamente diferem — o predicado, não.

E ele não decide o que fazer com a violação: devolve `Achado`, e cada chamador o
embrulha no vocabulário dele (`Violation` no verificador, `PackError` no linter).
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# Regras de excecao — constantes nomeadas, deliberadamente.
#
# Uma regra de excecao enterrada no meio do codigo nao e auditavel. Todas as
# listas abaixo sao declaradas aqui, no topo, e cada uma cita a norma que a
# justifica. Elas vieram INTEIRAS de `tools/check_synthetic_data.py`, sem
# alteracao de valor: o movimento e de lugar, e nao de semantica, e e por isso
# que a suite daquele verificador continua sendo a prova dele.
# ---------------------------------------------------------------------------

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

#: TLDs reservados a documentacao, teste e uso local. RFC 2606 e RFC 6761 para
#: `example`, `invalid`, `test` e `localhost`; RFC 6762 (mDNS) para `local`.
#:
#: A citacao anterior nomeava so 2606 e 6761, que nao cobrem `local` — L3 da
#: quinta auditoria. Esta lista e espelhada em
#: contracts/evidence.schema.yaml::allowed_domain_suffixes, e as duas divergiam
#: enquanto o comentario de la afirmava alinhamento.
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


@dataclass(frozen=True, slots=True)
class Achado:
    """Uma violacao de dado sintetico, sem opiniao sobre onde ela apareceu.

    `regra` e uma das tres constantes `RULE_*`; `valor` e o texto acusado;
    `detalhe` e a prosa que nomeia a norma. O chamador acrescenta a localizacao,
    que so ele conhece — arquivo e linha no verificador, caminho de instancia no
    linter de pack.
    """

    regra: str
    valor: str
    detalhe: str


# ---------------------------------------------------------------------------
# Classificacao de valores
# ---------------------------------------------------------------------------


def ip_permitido(address) -> bool:
    if any(address in network for network in DOCUMENTATION_NETWORKS):
        return True
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_unspecified
        or address.is_reserved
    )


def cpf_candidato(value: str) -> str | None:
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


def cpf_digitos_validos(digits: str) -> bool:
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


def como_ip(value: str):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def hostnames_candidatos(value: str):
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


def tem_forma_de_hostname(host: str) -> bool:
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


def hostname_permitido(host: str) -> bool:
    labels = host.rstrip(".").lower().split(".")
    if labels[-1] in RESERVED_TLDS:
        return True
    return ".".join(labels[-2:]) in RESERVED_DOMAINS


def achados_no_valor(value: str, *, isentos: frozenset[str] = frozenset()) -> list[Achado]:
    """Os achados de UM valor de texto. Lista vazia significa valor limpo.

    `isentos` e a lista de excecao do chamador — nomes de flag e de `event_type`,
    no verificador da arvore, que tem forma de hostname e seriam falso positivo.
    """
    achados: list[Achado] = []
    if value in isentos:
        return achados

    cpf = cpf_candidato(value)
    if cpf is not None:
        if cpf_digitos_validos(cpf):
            achados.append(
                Achado(
                    RULE_IDENTIFIER,
                    value,
                    f"'{value}' e um CPF valido. 05_SECURITY_REQUIREMENTS secao 3 "
                    "exige que CPF sintetico FALHE a validacao de digito "
                    "verificador; caso contrario e indistinguivel de dado real.",
                )
            )
        return achados

    address = como_ip(value)
    if address is not None:
        if not ip_permitido(address):
            achados.append(
                Achado(
                    RULE_IP,
                    value,
                    f"'{value}' nao esta em faixa privada nem de documentacao "
                    "(RFC 1918, RFC 5737, RFC 3849).",
                )
            )
        return achados

    for host in hostnames_candidatos(value):
        if host in isentos:
            continue
        candidate = como_ip(host)
        if candidate is not None:
            if not ip_permitido(candidate):
                achados.append(
                    Achado(
                        RULE_IP,
                        host,
                        f"'{host}' nao esta em faixa privada nem de documentacao.",
                    )
                )
            continue
        if tem_forma_de_hostname(host) and not hostname_permitido(host):
            achados.append(
                Achado(
                    RULE_DOMAIN,
                    host,
                    f"'{host}' nao esta em faixa reservada a documentacao "
                    "(RFC 2606, RFC 6761).",
                )
            )
    return achados


def achados_na_arvore(value, *, isentos: frozenset[str] = frozenset()) -> list[Achado]:
    """Os achados de uma estrutura inteira — mapeamento, sequencia ou escalar.

    Percorre VALORES, e nao chaves: nome de campo nao e dado sintetico. E a
    mesma travessia que `tools/check_synthetic_data.py` fazia em `_walk`.
    """
    achados: list[Achado] = []
    if isinstance(value, str):
        achados.extend(achados_no_valor(value, isentos=isentos))
    elif isinstance(value, dict):
        for item in value.values():
            achados.extend(achados_na_arvore(item, isentos=isentos))
    elif isinstance(value, (list, tuple)):
        for item in value:
            achados.extend(achados_na_arvore(item, isentos=isentos))
    return achados
