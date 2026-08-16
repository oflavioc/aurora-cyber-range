"""De onde os contratos chegam ao loader — e por que eles chegam como DADO.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §2 (layout) e §5.4 (pack validado contra as flags do
adapter no boot); `04_SCENARIO_SCHEMA.md` §1 e §4.

O QUE ESTE MODULO E, E O QUE ELE NAO E
--------------------------------------
E o unico lugar do nucleo que toca disco para ler `contracts/`. Tudo o que vem
depois — `pack_loader`, `contract_rules` — recebe documento ja parseado e nao
sabe de onde veio.

A separacao nao e estetica. `load_pack` recebe os contratos como argumento, e e
o que torna a validacao testavel contra contrato sintetico: um teste que precise
de um `$defs` que a arvore nao tem monta o seu, em vez de plantar defeito na
arvore real e restaurar depois.

POR QUE O NUCLEO PODE LER `contracts/`, e onde isso encosta num limite
----------------------------------------------------------------------
O invariante 1 proibe o core de importar `domains/`. `contracts/` e a fonte
canonica compartilhada, agnostica de dominio, e o core ja depende dela desde o
fold, que importa `contracts.generated.events` para nao ter literal de
`event_type`.

O limite esta declarado na §2.1 do registro da Fase 2:
`tools/check_core_boundary.py` **nao olha** para `contracts/` — ele tem opiniao
apenas sobre `domains`. Este modulo e o segundo caminho do core para `contracts/`
e o PRIMEIRO que nao e constante gerada, que e exatamente a condicao que aquele
limite declarou como gatilho para virar pendencia. Ver o registro da fase.

**As flags do adapter NAO entram aqui**, e a assimetria e o ponto: contrato e do
nucleo, flag e do dominio. Quem carrega o adapter entrega as flags como dado —
`AdapterFlags` —, do mesmo jeito que `Declarations` recebe os defaults.

POR QUE PyYAML, E NAO `tools/_common.py::parse_yaml`
-----------------------------------------------------
Duas razoes, e a segunda sozinha ja decidiria.

1. O nucleo nao importa de `tools/`. Aquele diretorio e dos seis verificadores
   stdlib do CI, e a dependencia na direcao contraria inverteria o gate.

2. `parse_yaml` e deliberadamente estrito: le o SUBCONJUNTO em que nossos
   contratos sao escritos, por regra nossa. Pack e escrito por humano —
   `scenario-designer` — e a spec ja aceitou esse argumento uma vez, quando
   `scripts/check_spec_examples.py` trouxe PyYAML para ler `docs/spec/`.

Passam a existir DOIS parsers lendo os mesmos seis contratos, e isso e risco
real de divergencia. Por isso `tests/test_pack_loader.py::DoisParsers` afirma
que os dois produzem a MESMA arvore para os seis — o que tambem fecha, por
consequencia, o limite que `fase_1.md` §7.4 declarou sem verificar:
`parse_yaml` nunca tinha sido comparado com parser conforme.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from referencing import Registry, Resource

import contracts as _contracts_package


class ContractSourceError(Exception):
    """Os contratos nao puderam ser lidos. Nada depois disso teria significado."""


def contracts_dir() -> Path:
    """O diretorio `contracts/`, resolvido pelo PACOTE e nao por caminho relativo.

    Caminho relativo a este arquivo funcionaria na arvore e quebraria no
    container da Fase 4, que e exatamente a assimetria que a §3.2 do registro
    desta fase mediu: `contracts` so resolve pela arvore quando o CWD e a raiz
    do repositorio.

    `__path__` cobre o pacote de namespace e a instalacao editavel — a entrada
    do finder editavel nao e diretorio, e por isso a escolha e pela primeira que
    E diretorio, em vez de pela primeira.
    """
    for entrada in _contracts_package.__path__:
        caminho = Path(entrada)
        if caminho.is_dir():
            return caminho
    raise ContractSourceError(
        "pacote `contracts` sem diretorio resolvivel: "
        f"__path__={list(_contracts_package.__path__)!r}"
    )


def parse_document(caminho: Path) -> dict:
    """Um documento YAML, ou `ContractSourceError` nomeando o arquivo.

    `yaml.safe_load` nunca constroi objeto arbitrario — nao ha `!!python/object`
    aqui, e isso importa porque pack e conteudo de terceiro do ponto de vista do
    engine (`05_SECURITY_REQUIREMENTS.md` §1).
    """
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractSourceError(f"{caminho}: nao pode ser lido — {exc}") from exc
    try:
        documento = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        raise ContractSourceError(f"{caminho}: YAML invalido — {exc}") from exc
    if documento is None:
        return {}
    if not isinstance(documento, dict):
        raise ContractSourceError(
            f"{caminho}: documento de topo e {type(documento).__name__}, esperado mapeamento"
        )
    return documento


def read_contracts(raiz: Path | None = None) -> dict[str, dict]:
    """Os contratos, indexados por `x-aurora-contract`.

    A chave e a etiqueta que o proprio contrato declara, e nao o nome do
    arquivo: e ela que `contract_rules.build_registries` consulta, e nome de
    arquivo e caminho, nao identidade.
    """
    raiz = contracts_dir() if raiz is None else raiz
    caminhos = sorted(raiz.glob("*.yaml"))
    if not caminhos:
        raise ContractSourceError(f"nenhum contrato em {raiz}")

    por_nome: dict[str, dict] = {}
    for caminho in caminhos:
        schema = parse_document(caminho)
        por_nome[schema.get("x-aurora-contract") or caminho.stem] = schema
    return por_nome


def documents_by_id(contratos: dict[str, dict]) -> dict[str, dict]:
    """`$id` -> schema. E o que resolve `$ref` entre documentos."""
    return {s["$id"]: s for s in contratos.values() if "$id" in s}


def registry_for(contratos: dict[str, dict]) -> Registry:
    """O `Registry` de `referencing` com os contratos como recursos.

    Ordenado por `$id` para a construcao ser determinista — Registry nao depende
    de ordem, mas construcao reproduzivel e barata e evita perseguir fantasma
    depois.
    """
    return Registry().with_resources(
        [(id_, Resource.from_contents(s)) for id_, s in sorted(documents_by_id(contratos).items())]
    )


def rollback_reasons(contratos: dict[str, dict]) -> frozenset[str]:
    """A taxonomia de motivo de rollback, LIDA do contrato.

    `09_EVENT_MODEL.md` §3.1 fecha o conjunto e da a cada motivo um efeito
    definido; `contracts/events.schema.yaml` o declara em `$defs/rollback_reason`.

    Ler dali, em vez de repetir os quatro nomes no engine, e a mesma regra que
    tirou os literais de `event_type` do core: rotulo com erro de digitacao nunca
    dispara, e um motivo invalido produziria rollback que a Fase 6 ignora em
    silencio.
    """
    eventos = contratos.get("events") or {}
    enum = ((eventos.get("$defs") or {}).get("rollback_reason") or {}).get("enum")
    if not enum:
        raise ContractSourceError(
            "contracts/events.schema.yaml sem `$defs/rollback_reason`: "
            "sem a taxonomia, o engine aceitaria qualquer motivo"
        )
    return frozenset(enum)
