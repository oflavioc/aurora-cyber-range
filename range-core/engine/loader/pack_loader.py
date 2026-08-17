"""Carga e validacao de pack — o boot, e os sitios em que ele recusa.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §2 (`engine/loader/` — "carga e validacao de pack"), §5.4
("pack e validado contra as flags do seu adapter no boot; flag desconhecida
impede subida do engine") e §6; `04_SCENARIO_SCHEMA.md` §1, §2, §4 e §5;
`06_ACCEPTANCE_TESTS.md` T2; `07_IMPLEMENTATION_PHASES.md` Fase 2, item 9 da
DoD.

O QUE ESTE MODULO ENTREGA
-------------------------
Item 9 da DoD: **flag nao declarada impede boot do engine com mensagem clara**.
T2 e mais especifico que o item, e e ele que define "clara": a mensagem nomeia
**a flag e o arquivo esperado**. Por isso `AdapterFlags` carrega `source` — o
nucleo nao inventa o caminho de `domains/`, ele repete o que quem carregou o
adapter declarou.

DUAS CAMADAS, A MESMA DE SEMPRE
-------------------------------
1. JSON Schema 2020-12 sobre os documentos que `x-aurora-documents` mapeia.
2. As regras `x-aurora-*`, por `contract_rules` — o MESMO modulo que o gate de
   CI executa. E a §1.4 do checkpoint em funcionamento: uma implementacao, dois
   chamadores. Duas implementacoes produziriam o gate aceitando pack que o
   loader recusa, e vice-versa.

O QUE ESTA FASE VALIDA, E O QUE ELA DELIBERADAMENTE NAO VALIDA
---------------------------------------------------------------
`x-aurora-documents` mapeia TRES arquivos — `manifest.yaml`, `injects.yaml` e
`branches.yaml` —, e sao esses os que passam pela camada 1.

`objectives.yaml` e `ground_truth.yaml` tem contratos PROPRIOS e sao das Fases 6
e 7. Aqui eles sao LIDOS, e apenas para os registros contra os quais
`x-aurora-ref` resolve: sem `pack_objectives`, um inject que cite objetivo
inexistente passaria — e essa e a falha que `04` §6.2 chama de mais cara
possivel. Ler para registro nao e validar, e a distincao esta dita porque a
confusao entre as duas e o que faria alguem marcar a Fase 6 como adiantada.

**Nao verificados aqui, e cada um tem fase com item de DoD proprio:**
`verification_predicates` obrigatorios (Fase 6, T10), rubrica ausente ou em
versao divergente (Fase 6, T9), politica de branch e reconvergencia (Fase 7,
T12), migracao de `schema_version` N-1 (Fase 7).

POR QUE A RECUSA TEM SITIO, e nao so mensagem
----------------------------------------------
Mesmo argumento de `Site` no fold: o teste precisa afirmar QUAL recusa ocorreu.
Sem discriminante, um teste que planta flag inexistente e recebe a recusa de
manifesto ausente passa e nao prova nada. A mensagem e prosa em portugues e vai
ser reescrita; o codigo nao.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from range_core.engine.loader.canonical import (
    CANONICALIZATION_V1,
    content_hash_v1,
    scope_from_contract,
)
from range_core.engine.loader.contract_rules import AuroraChecker, build_pack_registries
from range_core.engine.loader.contract_source import (
    ContractSourceError,
    documents_by_id,
    parse_document,
    registry_for,
)
from range_core.events.envelope import FlagValue
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    Declarations,
)

#: `04` §4 manda o engine declarar as duas. `SUPPORTED_SCHEMA_VERSIONS` deveria
#: ser `[N, N-1]`, e aqui e so `[N]`: **nao existe contrato v1 neste
#: repositorio**, e suportar uma versao cujo contrato nao existe exigiria a
#: migracao em memoria, que e item de DoD da Fase 7 ("pack em schema v1 migra
#: automaticamente; v0 e recusado com instrucao"). Declarar suporte que nao ha
#: seria pior que declarar o suporte real.
ENGINE_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSIONS: tuple[int, ...] = (2,)

#: `t_relative` e `HH:MM` — `04` §5 (`"00:47"`), §6 (`before: "01:30"`) e os
#: exemplos de `03` §7 (`"T+01:10"`). O CONTRATO o deixa como string de forma
#: livre, de proposito: fechar formato em schema seria a classe D6. Mas o engine
#: precisa AGENDAR, e agendar exige interpretar — entao a interpretacao vive
#: aqui, estrita, e recusa alto o que nao reconhece. Recusar e o oposto de
#: inventar: um `t_relative` em outro formato para o boot em vez de virar
#: agendamento silenciosamente errado.
_T_RELATIVE = re.compile(r"^(?P<horas>\d{1,3}):(?P<minutos>[0-5]\d)$")

#: A regra que responde pelo item 9. Vem do nome do registro em
#: `contract_rules`, e nao de casamento de prosa.
_REGRA_FLAG_DESCONHECIDA = "x-aurora-ref:adapter_flags"


class PackSite:
    """Os sitios de recusa do loader, nomeados. Ver o cabecalho do modulo."""

    PACK_DIR_MISSING = "pack_dir_missing"
    REQUIRED_FILE_MISSING = "required_file_missing"
    DOCUMENT_UNREADABLE = "document_unreadable"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    ENGINE_TOO_OLD = "engine_too_old"
    DOCUMENT_INVALID = "document_invalid"
    UNDECLARED_FLAG = "undeclared_flag"
    RULE_VIOLATION = "rule_violation"
    T_RELATIVE_MALFORMED = "t_relative_malformed"


class PackError(Exception):
    """O pack nao carrega, e o engine nao sobe.

    Recusa alta e deliberada, pelo mesmo motivo do `PackMismatch` do fold: um
    pack meio validado produz exercicio plausivel e errado, e a divergencia
    aparece no AAR, fases adiante.
    """

    def __init__(self, site: str, message: str) -> None:
        super().__init__(f"[{site}] {message}")
        self.site = site


@dataclass(frozen=True, slots=True)
class AdapterFlags:
    """As flags do adapter, como DADO — e de onde elas vieram.

    `source` nao e enfeite de mensagem: T2 exige que a recusa nomeie **a flag e
    o arquivo esperado**, e o nucleo nao pode nomear `domains/<adapter>/flags.yaml`
    sem conhecer `domains/`. Quem carrega o adapter sabe o caminho e o entrega
    junto dos dados.

    `from_document` recebe o documento JA PARSEADO. Ler o arquivo aqui seria o
    acoplamento que o invariante 1 existe para evitar entrando por outra porta —
    exatamente o que a §1.4 do checkpoint tirou de `build_registries`.
    """

    source: str
    specs: Mapping[str, Mapping]

    @classmethod
    def from_document(cls, document: Mapping, *, source: str) -> AdapterFlags:
        """Do formato de `contracts/state_flags.schema.yaml`: `{flags: [...]}`."""
        return cls(
            source=source,
            specs={flag["name"]: flag for flag in (document or {}).get("flags") or []},
        )

    @property
    def defaults(self) -> Mapping[str, FlagValue]:
        """`nome -> default`. `default` e `required` no contrato de flags."""
        return {nome: spec["default"] for nome, spec in self.specs.items()}


@dataclass(frozen=True, slots=True)
class DecisionOption:
    id: str
    label: str
    effects: Mapping[str, FlagValue]


@dataclass(frozen=True, slots=True)
class DecisionPoint:
    id: str
    question: str
    options: tuple[DecisionOption, ...]
    timer_minutes: int | None


@dataclass(frozen=True, slots=True)
class Inject:
    """Um inject, na forma de que o engine precisa — nao o documento inteiro.

    `titulo`, `descricao_facilitador`, `texto_para_plateia` e `linha` continuam
    no manifesto lido e NAO sobem para ca: `03` §5.2 exige que o operador nao
    enxergue a linha, e o caminho mais curto para vazar e o engine carregar o
    campo sem precisar dele. Quem os exibe e a UI, por rota com papel — Fase 4.
    """

    id: str
    t_relative: str
    t_relative_seconds: int
    titulo_operacional: str
    effects: Mapping[str, FlagValue]
    decision_point: DecisionPoint | None
    noise: bool


@dataclass(frozen=True, slots=True)
class LoadedPack:
    """O pack carregado, com o pino que o `exercise_started` vai gravar."""

    pack_id: str
    schema_version: int
    content_hash: str
    canonicalization: str
    source: str
    manifest: Mapping
    injects: tuple[Inject, ...]
    declarations: Declarations

    #: `inject_id -> texto_para_plateia`, e SO isso — D6 da Fase 4.
    #:
    #: `Inject` continua sem os campos de narrativa, e o comentario de la diz por
    #: que: o caminho mais curto para vazar e o engine carregar o campo sem
    #: precisar dele. A participant-view precisa de UM campo, entao ela recebe um
    #: mapa de strings — `linha`, `descricao_facilitador`, `objectives` e
    #: `decision_point` nao ficam ao alcance de quem projeta.
    #:
    #: A narrativa do FACILITADOR — `titulo`, `descricao_facilitador` — nao entra
    #: aqui por enquanto, e a ausencia e a §7.3 aplicada: a checagem que a
    #: guarda so pode ser escrita quando existir o consumidor, e ele e o
    #: gm-console da peca 4.
    textos_para_plateia: Mapping[str, str] = field(default_factory=dict)

    def by_id(self, inject_id: str) -> Inject | None:
        for inject in self.injects:
            if inject.id == inject_id:
                return inject
        return None

    def pin_payload(self) -> dict:
        """As quatro chaves que o fold confere em todo `exercise_started`.

        As chaves vem de `simulation_state`, por constante: quem exige e o
        consumidor, e escrever o nome aqui de novo faria as duas pontas
        divergirem no dia em que uma delas mudasse.
        """
        return {
            PACK_ID: self.pack_id,
            PACK_SCHEMA_VERSION: self.schema_version,
            PACK_CONTENT_HASH: self.content_hash,
            PACK_CANONICALIZATION: self.canonicalization,
        }


def load_pack(
    pack_dir: Path | str,
    *,
    contracts: Mapping[str, Mapping],
    adapter_flags: AdapterFlags,
) -> LoadedPack:
    """Carrega, valida e devolve o pack. Levanta `PackError` em qualquer recusa.

    A ORDEM DOS PASSOS E PARTE DA GARANTIA:

    1. **Presenca** — `manifest.yaml`, que o contrato declara `required`. Sem ele
       nao se sabe nem o que se esta lendo.
    2. **Leitura** — todo documento de maquina presente, parseado. E aqui que o
       `content_hash` e calculado, sobre o que foi lido.
    3. **Versao** — `schema_version` suportada e `min_engine_version` alcancada.
       Antes da validacao de schema, de proposito: um pack v1 falharia no
       `const: 2` com mensagem sobre um campo, quando o que ele precisa e da
       instrucao de migracao.
    4. **Schema** — os documentos que `x-aurora-documents` mapeia.
    5. **Regras `x-aurora-*`** — incluindo a que responde pelo item 9.
    6. **Modelo** — injects e `Declarations`, ja sobre documento validado.

    Nada e devolvido pela metade: ou o pack carrega inteiro, ou o engine nao
    sobe.
    """
    raiz = Path(pack_dir)
    if not raiz.is_dir():
        raise PackError(PackSite.PACK_DIR_MISSING, f"{raiz}: nao e um diretorio de pack")

    scenario = contracts["scenario"]
    obrigatorios = (
        (scenario.get("x-aurora-registry") or {}).get("package_files") or {}
    ).get("required") or []

    for arquivo in obrigatorios:
        if not (raiz / arquivo).is_file():
            raise PackError(
                PackSite.REQUIRED_FILE_MISSING,
                f"{raiz}: falta `{arquivo}`, que "
                "`contracts/scenario.schema.v2.yaml` declara obrigatorio em "
                "`x-aurora-registry.package_files.required`",
            )

    documentos = _read_documents(raiz, scope_from_contract(scenario))
    manifest = documentos["manifest.yaml"]
    content_hash = content_hash_v1(documentos)

    _verify_schema_version(raiz, manifest)
    _verify_schema(documentos, scenario, contracts)
    _verify_engine_version(raiz, manifest)
    _verify_rules(documentos, scenario, contracts, adapter_flags)

    injects = _build_injects(documentos.get("injects.yaml") or {})

    return LoadedPack(
        pack_id=manifest["pack_id"],
        schema_version=manifest["schema_version"],
        content_hash=content_hash,
        canonicalization=CANONICALIZATION_V1,
        source=str(raiz),
        manifest=manifest,
        injects=injects,
        textos_para_plateia={
            str(bruto["id"]): str(bruto.get("texto_para_plateia") or "")
            for bruto in (documentos.get("injects.yaml") or {}).get("injects") or []
        },
        declarations=Declarations(
            pack_id=manifest["pack_id"],
            schema_version=manifest["schema_version"],
            content_hash=content_hash,
            canonicalization=CANONICALIZATION_V1,
            flag_defaults=adapter_flags.defaults,
            inject_effects={inject.id: inject.effects for inject in injects},
            option_effects={
                (inject.id, opcao.id): opcao.effects
                for inject in injects
                if inject.decision_point is not None
                for opcao in inject.decision_point.options
            },
        ),
    )


def _read_documents(raiz: Path, escopo: tuple[str, ...]) -> dict[str, Mapping]:
    """Os documentos de maquina PRESENTES, `caminho POSIX -> documento`.

    Ausencia nao e erro aqui: o pacote apenas-manifesto e forma legitima
    (`04` §9, e o `x-aurora-registry` do contrato separa `required` de
    `required_for_complete_pack` por causa dela). Quem cobra presenca e o passo
    anterior, contra a lista do contrato.
    """
    documentos: dict[str, Mapping] = {}
    for arquivo in escopo:
        caminho = raiz / arquivo
        if not caminho.is_file():
            continue
        try:
            documentos[arquivo] = parse_document(caminho)
        except ContractSourceError as exc:
            raise PackError(PackSite.DOCUMENT_UNREADABLE, str(exc)) from exc
    return documentos


def _verify_schema_version(raiz: Path, manifest: Mapping) -> None:
    """`schema_version` — `04` §4. ANTES da validacao de schema, de proposito.

    O contrato declara `const: 2`, entao um pack v1 falharia na camada 1 com uma
    mensagem sobre um campo. O que ele precisa e da INSTRUCAO DE MIGRACAO, e ela
    so pode vir de quem sabe o que "v1" significa.
    """
    versao = manifest.get("schema_version")
    if versao not in SUPPORTED_SCHEMA_VERSIONS:
        raise PackError(
            PackSite.UNSUPPORTED_SCHEMA_VERSION,
            f"{raiz}/manifest.yaml: `schema_version: {versao!r}`, e este engine "
            f"suporta {list(SUPPORTED_SCHEMA_VERSIONS)}. A migracao automatica de "
            "N-1 e entregavel da Fase 7 (`07_IMPLEMENTATION_PHASES.md`), e ate la "
            "nao ha caminho de carga para outra versao.",
        )


def _verify_engine_version(raiz: Path, manifest: Mapping) -> None:
    """`min_engine_version` — `04` §4. DEPOIS da validacao de schema.

    Ao contrario da versao de schema, esta comparacao precisa do campo BEM
    FORMADO: `"abc"` daria `ValueError` cru, e erro de ferramenta lido como
    recusa de pack e pior que recusa nenhuma. O contrato ja garante o formato
    `^[0-9]+\\.[0-9]+$`, entao rodar depois dele torna a garantia disponivel em
    vez de suposta.
    """
    exigida = manifest.get("min_engine_version")
    if exigida is not None and _version_tuple(exigida) > _version_tuple(ENGINE_VERSION):
        raise PackError(
            PackSite.ENGINE_TOO_OLD,
            f"{raiz}/manifest.yaml: exige engine {exigida}, e este e "
            f"{ENGINE_VERSION}. Carregar mesmo assim rodaria um pack que conta "
            "com recurso que este engine nao tem.",
        )


def _version_tuple(versao: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in str(versao).split("."))


def _verify_schema(
    documentos: Mapping[str, Mapping],
    scenario: Mapping,
    contracts: Mapping[str, Mapping],
) -> None:
    """Camada 1, sobre os documentos que `x-aurora-documents` mapeia.

    O mapa vem do CONTRATO, e nao de lista aqui: acrescentar um documento ao
    pacote passa a ser mudanca de contrato, e o loader o valida sem que ninguem
    tenha de lembrar de o acrescentar em dois lugares.
    """
    registry = registry_for(dict(contracts))
    base = scenario.get("$id", "")

    for arquivo, ponteiro in sorted((scenario.get("x-aurora-documents") or {}).items()):
        if arquivo not in documentos:
            continue
        alvo = {"$ref": f"{base}{ponteiro}"} if ponteiro not in (None, "#") else {"$ref": base}
        erros = sorted(
            Draft202012Validator(alvo, registry=registry).iter_errors(documentos[arquivo]),
            key=str,
        )
        if erros:
            detalhe = "\n".join(f"    {e.json_path}: {e.message}" for e in erros[:5])
            raise PackError(
                PackSite.DOCUMENT_INVALID,
                f"`{arquivo}` nao valida contra "
                f"`contracts/scenario.schema.v2.yaml{ponteiro}` "
                f"({len(erros)} erro(s)):\n{detalhe}",
            )


def _verify_rules(
    documentos: Mapping[str, Mapping],
    scenario: Mapping,
    contracts: Mapping[str, Mapping],
    adapter_flags: AdapterFlags,
) -> None:
    """Camada 2 — as regras `x-aurora-*`, pelo modulo que o gate de CI usa.

    ITEM 9 DA DoD MORA AQUI, e nao numa checagem propria de flag. Uma segunda
    implementacao de "a flag existe?" divergiria da primeira, e o gate passaria
    a aceitar pack que o boot recusa. O que este passo acrescenta e a
    CLASSIFICACAO: a violacao de `adapter_flags` sai com sitio proprio e com o
    arquivo esperado na mensagem, que e o que T2 exige alem do nome da flag.
    """
    registros = build_pack_registries(
        dict(contracts),
        dict(adapter_flags.specs),
        injects_document=documentos.get("injects.yaml"),
        objectives_document=documentos.get("objectives.yaml"),
        ground_truth_document=documentos.get("ground_truth.yaml"),
    )
    registry = registry_for(dict(contracts))
    docs_por_id = documents_by_id(dict(contracts))
    base = scenario.get("$id", "")

    for arquivo, ponteiro in sorted((scenario.get("x-aurora-documents") or {}).items()):
        if arquivo not in documentos:
            continue
        checker = AuroraChecker(registros, docs_por_id)
        violacoes = checker.check(base, ponteiro, documentos[arquivo], registry)
        if not violacoes:
            continue

        flags = [detalhe for regra, detalhe in violacoes if regra == _REGRA_FLAG_DESCONHECIDA]
        corpo = "\n".join(f"    {regra}: {detalhe}" for regra, detalhe in violacoes)
        if flags:
            raise PackError(
                PackSite.UNDECLARED_FLAG,
                f"`{arquivo}` cita flag que o adapter nao declara:\n{corpo}\n"
                f"    declare a flag em `{adapter_flags.source}` — o arquivo que "
                "`01_ARCHITECTURE.md` §5.2 normatiza como a declaracao do adapter — "
                "ou corrija o pack. Nenhum servico le ou escreve flag nao declarada "
                "(§5.4), e o engine nao sobe com o pack neste estado.",
            )
        raise PackError(
            PackSite.RULE_VIOLATION,
            f"`{arquivo}` viola regra de integridade referencial:\n{corpo}",
        )


def _build_injects(injects_document: Mapping) -> tuple[Inject, ...]:
    """O modelo de inject, ja sobre documento validado pelas duas camadas.

    `effects` ausente vira mapeamento VAZIO, e a entrada existe mesmo assim: o
    fold levanta `INJECT_NOT_IN_PACK` para inject que nao esta em
    `inject_effects`, e um inject sem effects e legitimo — inject de revelacao ou
    de midia nao move flag.
    """
    injects: list[Inject] = []
    for bruto in injects_document.get("injects") or []:
        ponto = bruto.get("decision_point")
        injects.append(
            Inject(
                id=bruto["id"],
                t_relative=bruto["t_relative"],
                t_relative_seconds=t_relative_seconds(bruto["t_relative"], bruto["id"]),
                titulo_operacional=bruto["titulo_operacional"],
                effects=dict(bruto.get("effects") or {}),
                decision_point=(
                    None
                    if ponto is None
                    else DecisionPoint(
                        id=ponto["id"],
                        question=ponto["question"],
                        options=tuple(
                            DecisionOption(
                                id=opcao["id"],
                                label=opcao["label"],
                                effects=dict(opcao.get("effects") or {}),
                            )
                            for opcao in ponto["options"]
                        ),
                        timer_minutes=ponto.get("timer_minutes"),
                    )
                ),
                noise=bool(bruto.get("noise", False)),
            )
        )
    return tuple(injects)


def t_relative_seconds(valor: str, inject_id: str) -> int:
    """`HH:MM` -> segundos de exercicio desde o inicio da linha do exercicio.

    Comparado contra `exercise_time`, que e o rotulo `T+` e REBOBINA ate o ponto
    de corte no rollback (`01` §3). E o que faz o agendamento voltar a valer
    depois de um rollback sem que o engine guarde memoria disso.
    """
    casado = _T_RELATIVE.match(str(valor))
    if casado is None:
        raise PackError(
            PackSite.T_RELATIVE_MALFORMED,
            f"inject {inject_id}: `t_relative: {valor!r}` nao e `HH:MM`. "
            "O contrato deixa o campo como string livre de proposito, mas agendar "
            "exige interpretar — e interpretar por adivinhacao produziria disparo "
            "na hora errada em vez de erro.",
        )
    return int(casado.group("horas")) * 3600 + int(casado.group("minutos")) * 60
