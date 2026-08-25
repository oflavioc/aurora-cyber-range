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

**O QUE A FASE 6 FECHOU AQUI**, e esta linha foi reescrita porque a anterior
descrevia como pendente o que a propria fase entregou — M2 da auditoria:

- **rubrica ausente ou em versao divergente** (T9): `x-aurora-ref: rubric_library`
  em `scenario.schema.v2.yaml`, resolvido em `_verify_rules`, com dois testes;
- **`verification_predicates` obrigatorios** (T10): `ground_truth.yaml` entrou em
  `x-aurora-documents` e passa a ser validado contra o contrato dele, e
  `required_for_complete_pack` virou codigo em `_verify_completude` — B1 da mesma
  auditoria.

**Nao verificados aqui**, e cada um tem fase com item de DoD proprio: politica de
branch e reconvergencia (Fase 7, T12), migracao de `schema_version` N-1 (Fase 7).

> A redacao anterior dizia que os dois primeiros nao eram verificados aqui, e
> ficou FALSA dentro do modulo que a fase alterou — a metade da rubrica havia
> sido implementada nesta mesma fase. E a classe da §1.6 do registro da Fase 1:
> afirmacao que nasce verdadeira e envelhece com a entrega. O modo de corrigir e
> este — reescrever a lista com o que ha, e nao acrescentar uma ressalva.

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
from range_core.engine.citacoes import (
    CitacaoInvalida,
    confere_citacoes_de_fato,
    fatos_declarados,
)
from range_core.engine.migrations import MIGRACOES, ha_migracao
from range_core.rubrics.library import load_library
from range_core.engine.loader.contract_source import (
    ContractSourceError,
    documents_by_id,
    parse_document,
    fact_id_pattern,
    registry_for,
    since_qualifiers,
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
#: ser `[N, N-1]`, e aqui e so `[N]` — e a assimetria e DECIDIDA, nao pendente.
#:
#: **Nenhum contrato anterior ao v2 jamais existiu neste repositorio.** Medido
#: com `git log --all --diff-filter=A --name-only -- 'contracts/scenario.schema*'`,
#: que devolve um arquivo so: `scenario.schema.v2.yaml`, em `31ddcfa`. Entao
#: `[N, N-1]` aqui seria `[2, 1]`, e a v1 nao tem contrato, nao tem migrador e
#: nunca teve pack. Declarar suporte a ela seria a afirmacao falsa que este
#: modulo recusa fazer desde a Fase 2.
#:
#: O comentario anterior dizia que a migracao de N-1 *"e item de DoD da Fase
#: 7"*, como se a fase fosse resolver a assimetria. A Fase 7 **e esta**, e a
#: peca 2 mediu que nao ha delta a migrar: a P5-4 excede o que cabe num schema e
#: saiu da fase, e o aperto de `since` foi alinhamento com norma que ja existia,
#: nao transformacao. O porque inteiro esta em `engine/migrations/__init__.py`.
#:
#: `(3, 2)` no dia em que houver `v2_to_v3.py` com corpo e teste. Nao antes.
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
    #: Folha temporal declarada num predicado de verificacao. A gramatica do
    #: contrato a admite (`ground_truth.schema.yaml` §predicate_before/after) e o
    #: avaliador ainda nao a implementa — ver `docs/progress/fase_6.md`, P6-3.
    TEMPORAL_LEAF_UNSUPPORTED = "temporal_leaf_unsupported"
    #: Pack COMPLETO ao qual falta um dos documentos que
    #: `x-aurora-registry.package_files.required_for_complete_pack` exige. B1 da
    #: auditoria da Fase 6: aquele registro era citado em docstring e nao lido
    #: por codigo nenhum.
    INCOMPLETE_PACK = "incomplete_pack"
    #: `absence_of.since` com valor que `03` §3.1 nao define — `self` e a unica
    #: forma de v1. H1 da quarta auditoria da Fase 6.
    SINCE_UNDEFINED_VALUE = "since_undefined_value"
    #: Predicado de CONTENCAO com `absence_of` sem `since` — a forma que a §3.1
    #: exige, e sem a qual o pack cai no defeito que o `spec-change` #49 corrigiu.
    CONTAINMENT_ABSENCE_WITHOUT_SINCE = "containment_absence_without_since"
    #: Fato citado e ausente de `facts`, ou citado em forma que o contrato nao
    #: casa — item 8 da DoD da Fase 7 e `06` T8. Cobre os tres lados que citam:
    #: `GM_NOTES.md`, `materializes_facts` e `projects_facts`.
    CITACAO_DE_FATO_INVALIDA = "citacao_de_fato_invalida"


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
    #: DERIVADO NA CARGA — `03` §3, "Impacto observável, definido". Marca o
    #: *start* de `TTA`, e é derivado em vez de declarado porque um campo no
    #: pack seria segunda fonte para o mesmo fato e poria em mãos de autoria a
    #: decisão de quando a métrica começa a correr.
    observable_impact: bool
    #: `media_event.requires_response` do pack — `04` §7. O *start* de `TTCM`.
    #: Este VEM declarado: quem sabe se um inject exige resposta é quem o
    #: escreveu, e o campo já existia antes desta fase.
    requires_response: bool


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

    #: `verification_predicates` do `ground_truth.yaml` — `03` §3.1.
    #:
    #: ELES SAO GABARITO, e a colocacao aqui e decidida e nao acidental. Quem os
    #: le sabe o que E contencao neste incidente, que e metade do que a equipe
    #: tem de descobrir.
    #:
    #: Entram no pack porque o LACO CONTINUO precisa deles: `03` §3.1 exige que o
    #: motor avalie continuamente, e o motor recebe o pack. A alternativa — um
    #: segundo carregamento do `ground_truth.yaml` no chamador — poria a leitura
    #: do gabarito em dois lugares, e o segundo nasceria sem as guardas do
    #: primeiro (`confere_folhas_temporais`, integridade referencial).
    #:
    #: A FRONTEIRA QUE ISSO NAO CRUZA: nenhuma rota serializa o pack. `/injects`
    #: monta um dicionario com quatro campos por inject, e a participant-view
    #: recebe `textos_para_plateia`, que e um mapa de strings. `05` §6 continua
    #: valendo, e `check_api_surface.py` continua sendo quem o cobra por rota.
    verification_predicates: Mapping[str, Mapping] = field(default_factory=dict)

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
    _verify_completude(raiz, documentos, scenario)
    manifest = documentos["manifest.yaml"]
    content_hash = content_hash_v1(documentos)

    _verify_schema_version(raiz, manifest)
    _verify_schema(documentos, scenario, contracts)
    _verify_engine_version(raiz, manifest)
    _verify_rules(documentos, scenario, contracts, adapter_flags)
    confere_folhas_temporais(documentos.get("ground_truth.yaml"))
    # O QUALIFICADOR SAI DO CONTRATO, e `load_pack` ja recebe `contracts` — a
    # origem estava ao alcance sem encanamento novo. `04` §4.1.
    confere_qualificador_since(
        documentos.get("ground_truth.yaml"),
        qualificadores=since_qualifiers(dict(contracts)),
    )
    confere_citacoes_do_pack(raiz, documentos, contracts)

    injects = _build_injects(
        documentos.get("injects.yaml") or {}, documentos.get("ground_truth.yaml")
    )

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
        verification_predicates=(documentos.get("ground_truth.yaml") or {}).get(
            "verification_predicates"
        )
        or {},
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

    A MENSAGEM ANTERIOR NAO DAVA INSTRUCAO, e o criterio da DoD e "recusado COM
    INSTRUCAO". Ela dizia *"a migracao automatica de N-1 e entregavel da Fase 7,
    e ate la nao ha caminho de carga"* — informacao de ROADMAP, nao de conserto:
    quem lia ficava sabendo de que fase o mecanismo era, e nao o que fazer com o
    pack na mao. E ela envelheceu duas vezes de uma so vez, porque a Fase 7 e
    esta, e o "ate la" passou a apontar para o presente. E a §1.6 no codigo.

    A DE AGORA RESPONDE TRES PERGUNTAS, na ordem em que quem foi recusado as faz:
    o que este pack declara, o que este engine aceita, e o que fazer agora.
    """
    versao = manifest.get("schema_version")
    if versao in SUPPORTED_SCHEMA_VERSIONS:
        return
    raise PackError(
        PackSite.UNSUPPORTED_SCHEMA_VERSION,
        _instrucao_de_versao(raiz, versao),
    )


def _instrucao_de_versao(raiz: Path, versao: object) -> str:
    """As tres perguntas, e a terceira depende de haver migrador declarado.

    O RAMO E LIDO DO REGISTRO, e nao inferido da aritmetica das versoes: uma
    conta como `versao == max(SUPPORTED) - 1` afirmaria que existe caminho de
    migracao so porque a distancia e de um, e e exatamente essa afirmacao que
    hoje seria falsa. Quem sabe se ha migrador e `migrations.MIGRACOES`.
    """
    suportadas = sorted(SUPPORTED_SCHEMA_VERSIONS)
    alvo = max(SUPPORTED_SCHEMA_VERSIONS)

    linhas = [
        f"{raiz}/manifest.yaml: `schema_version: {versao!r}`, e este engine "
        f"aceita {suportadas}.",
    ]

    if isinstance(versao, int) and ha_migracao(versao):
        linhas.append(
            f"    HA CAMINHO DE MIGRACAO de {versao} para {alvo}, em "
            f"`range-core/engine/migrations/{MIGRACOES[versao]}.py` — se voce "
            "esta lendo isto, ele existe e nao foi aplicado, o que e defeito do "
            "loader e nao do pack. Abra uma issue com esta mensagem."
        )
        return "\n".join(linhas)

    linhas.append(
        f"    NAO HA MIGRADOR declarado para {versao!r}: "
        "`range-core/engine/migrations/MIGRACOES` esta vazio, e o cabecalho "
        "daquele modulo diz por que — nenhum contrato anterior ao v2 jamais "
        "existiu neste repositorio, entao nao ha transicao que alguem pudesse "
        "ter escrito."
    )
    linhas.append(
        f"    O QUE FAZER: leve o pack para `schema_version: {alvo}` a mao. A "
        f"forma exigida esta em `contracts/scenario.schema.v{alvo}.yaml` — que "
        "e o contrato que o loader aplica no passo seguinte a este — e o "
        "manifesto normativo esta em `04_SCENARIO_SCHEMA.md` §2. Rode o loader "
        "de novo: a recusa seguinte, se houver, ja nomeia o campo."
    )
    linhas.append(
        f"    SE {versao!r} FOR UMA VERSAO FUTURA, o conserto e o inverso — este "
        "engine e velho demais para o pack, e atualiza-lo e o caminho. "
        "`04` §4 fixa `SUPPORTED_SCHEMA_VERSIONS = [N, N-1]`; aqui ele e "
        f"{suportadas} porque N-1 nunca existiu, e declarar suporte a uma versao "
        "sem contrato seria pior que declarar o suporte real."
    )
    return "\n".join(linhas)


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


def _verify_completude(
    raiz: Path, documentos: Mapping[str, Mapping], scenario: Mapping
) -> None:
    """`required_for_complete_pack` deixa de ser prosa — B1 da Fase 6.

    O registro existia no contrato desde a terceira auditoria e era citado em
    DOIS docstrings; nenhum codigo o lia. Um pack completo sem `ground_truth.yaml`
    carregava limpo, e `TTCV`/`TTRV` ficavam incomputaveis em runtime — que e o
    que `03` §3.1 diz que o pack nao pode ter.

    O QUE ESTE PASSO **NAO** FAZ, E E A RESSALVA QUE O DESENHO EXIGE
    ----------------------------------------------------------------
    Ele **nao** torna `ground_truth.yaml` obrigatorio para todo pack. `04` §9
    manda entregar `vazamento-lgpd` e `pesquisa-comprometida` como *"apenas
    manifesto, sem injects"*, e eles existem justamente para provar que o loader
    lida com pacote incompleto. Endurecer aqui reintroduziria o M1 da terceira
    auditoria, que foi quem separou as duas formas.

    O CRITERIO E DERIVADO, E NAO UMA QUARTA LISTA
    ----------------------------------------------
    Pack **completo** e o que traz **pelo menos um** dos documentos de
    `required_for_complete_pack`; nele, **todos** sao exigidos. Pack
    **apenas-manifesto** nao traz nenhum, e continua carregando.

    A derivacao evita a lista nova que teria de ser mantida em acordo com a
    existente — e listas paralelas divergem, que e a classe que este mesmo
    registro ja custou uma auditoria para fechar.

    O MEIO-TERMO E O QUE ELE PEGA: pack com `injects.yaml` e sem
    `ground_truth.yaml` nao e apenas-manifesto nem completo. Antes deste passo
    ele carregava como se fosse legitimo.
    """
    exigidos = (
        (scenario.get("x-aurora-registry") or {}).get("package_files") or {}
    ).get("required_for_complete_pack") or []

    presentes = [arquivo for arquivo in exigidos if arquivo in documentos]
    if not presentes:
        return

    faltando = [arquivo for arquivo in exigidos if arquivo not in documentos]
    if not faltando:
        return

    linhas = [
        f"{raiz}: pack COMPLETO sem {', '.join(repr(a) for a in faltando)}.",
        f"    Ele traz {', '.join(repr(a) for a in presentes)}, entao nao e "
        "pacote apenas-manifesto — e `contracts/scenario.schema.v2.yaml` exige "
        "os tres em "
        "`x-aurora-registry.package_files.required_for_complete_pack`.",
        "    Pacote APENAS-MANIFESTO continua sendo forma legitima (`04` §9): "
        "ele nao traz NENHUM dos tres.",
    ]
    raise PackError(PackSite.INCOMPLETE_PACK, "\n".join(linhas))


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
        # PONTEIRO RELATIVO resolve neste contrato; URI ABSOLUTA resolve em
        # outro — `ground_truth.yaml` e `objectives.yaml` tem contrato proprio, e
        # e por isso que o mapa carrega `$ref` e nao so ponteiro (B1 da Fase 6).
        if ponteiro and "://" in ponteiro:
            alvo = {"$ref": ponteiro}
            origem = ponteiro
        elif ponteiro in (None, "#"):
            alvo = {"$ref": base}
            origem = f"contracts/scenario.schema.v2.yaml{ponteiro or ''}"
        else:
            alvo = {"$ref": f"{base}{ponteiro}"}
            origem = f"contracts/scenario.schema.v2.yaml{ponteiro}"
        erros = sorted(
            Draft202012Validator(alvo, registry=registry).iter_errors(documentos[arquivo]),
            key=str,
        )
        if erros:
            detalhe = "\n".join(f"    {e.json_path}: {e.message}" for e in erros[:5])
            raise PackError(
                PackSite.DOCUMENT_INVALID,
                f"`{arquivo}` nao valida contra `{origem}` "
                f"({len(erros)} erro(s)):\n{detalhe}",
            )


#: As duas folhas que a gramatica admite e o avaliador ainda nao implementa.
FOLHAS_TEMPORAIS = ("before", "after")


def _folhas_temporais(no, caminho: str = "") -> list[str]:
    """Caminhos das folhas temporais na arvore, em ordem de leitura."""
    achadas: list[str] = []
    if isinstance(no, Mapping):
        for chave, valor in no.items():
            aqui = f"{caminho}.{chave}" if caminho else str(chave)
            if chave in FOLHAS_TEMPORAIS:
                achadas.append(aqui)
            else:
                achadas.extend(_folhas_temporais(valor, aqui))
    elif isinstance(no, (list, tuple)):
        for indice, filho in enumerate(no):
            achadas.extend(_folhas_temporais(filho, f"{caminho}[{indice}]"))
    return achadas


def confere_folhas_temporais(ground_truth: Mapping | None) -> None:
    """Recusa NA CARGA o pack que declare folha temporal — P6-3.

    A GRAMATICA AS ADMITE, E O AVALIADOR NAO AS IMPLEMENTA. Sem esta guarda, o
    pack carrega limpo e detona **na avaliacao**, no meio do exercicio: o
    avaliador levanta `PredicadoMalformado` no instante em que a contencao
    deveria ser conferida, que e o pior momento possivel para descobrir uma
    ausencia de implementacao.

    A recusa muda de INSTANTE, e nao de existencia — e o padrao da guarda de
    boot do emissor: falhar quando ainda da para consertar o pack, e nao quando
    a sala esta cheia. `PredicadoMalformado` permanece no avaliador como segunda
    linha de defesa, para o caso de um predicado chegar por outro caminho.

    A mensagem nomeia A FOLHA e O MOTIVO, e nao so o fato: `06` T2 fixa essa
    forma para a flag nao declarada, e a razao e a mesma — deteccao sem
    localizacao nao permite intervir.
    """
    predicados = (ground_truth or {}).get("verification_predicates") or {}
    achadas: list[str] = []
    for nome, arvore in sorted(predicados.items()):
        achadas.extend(f"{nome}.{c}" for c in _folhas_temporais(arvore))
    if achadas:
        raise PackError(
            PackSite.TEMPORAL_LEAF_UNSUPPORTED,
            "predicado com folha temporal: " + ", ".join(achadas) + ".\n"
            "    `before` e `after` estao na gramatica de "
            "`contracts/ground_truth.schema.yaml` e o avaliador ainda NAO os "
            "implementa — eles comparam contra o relogio de exercicio, que nao e "
            "parte do mundo que ele monta. Recusar aqui e recusar enquanto da "
            "para consertar o pack; sem isto, a falha chega na avaliacao, no "
            "meio do exercicio. Pendencia P6-3 em `docs/progress/fase_6.md`."
        )


#: A CONSTANTE SAIU DAQUI — `04` §4.1. Era `SINCE_SELF = "self"`, e a mesma
#: linha existia em `engine/verificacao.py`, sem import entre as duas. O valor
#: agora vem do contrato, por `contract_source.since_qualifiers`, e `load_pack`
#: o passa adiante: ele ja recebe `contracts`, entao a origem estava ao alcance
#: sem encanamento novo.
#:
#: `PREDICADO_QUE_EXIGE_SINCE` FICA, e a diferenca e de especie: qual predicado
#: exige o qualificador e norma de `03` §3.1 sobre a CHAVE, e nao vocabulario
#: que o contrato declare. Deriva-lo seria inventar um registro para um fato que
#: nao esta em contrato nenhum.

#: O predicado cuja forma normativa EXIGE o qualificador. A exigencia e da §3.1,
#: e e da chave: `service_restoration` nao afirma o presente, e ausencia total ali
#: continua legitima.
PREDICADO_QUE_EXIGE_SINCE = "containment"


def _folhas_absence_of(no, caminho: str = "") -> list[tuple[str, object]]:
    """`(caminho, alvo)` de cada folha `absence_of` da arvore, em ordem de leitura."""
    achadas: list[tuple[str, object]] = []
    if isinstance(no, Mapping):
        for chave, valor in no.items():
            aqui = f"{caminho}.{chave}" if caminho else str(chave)
            if chave == "absence_of":
                achadas.append((aqui, valor))
            else:
                achadas.extend(_folhas_absence_of(valor, aqui))
    elif isinstance(no, (list, tuple)):
        for indice, filho in enumerate(no):
            achadas.extend(_folhas_absence_of(filho, f"{caminho}[{indice}]"))
    return achadas


def confere_qualificador_since(
    ground_truth: Mapping | None, *, qualificadores: frozenset[str]
) -> None:
    """Recusa NA CARGA as duas formas que `03` §3.1 nao admite — H1 da 4a auditoria.

    AS DUAS PERNAS SAO DEFEITOS PERMANENTES, e nao ausencia de implementacao
    ------------------------------------------------------------------------
    E o que separa esta guarda da `confere_folhas_temporais`: aquela recusa o que
    o avaliador ainda nao faz, e morre quando ele fizer. Estas duas continuam
    valendo depois de qualquer implementacao.

    1. **VALOR NAO DEFINIDO.** `self` e a unica forma de v1. Avaliar
       `since: exercise_start` exigiria semantica que ninguem declarou, e a
       forma plausivel de "resolver" — ignorar o valor — e exatamente o defeito
       que o `spec-change` #49 corrigiu.

    2. **CONTENCAO COM `absence_of` SEM `since`.** A §3.1 exige o campo no
       predicado de contencao, e a razao esta escrita la: sem a exigencia, um
       pack escreve contencao sem `since`, cai no defeito original — ausencia
       TOTAL, insatisfazivel em todo cenario que materialize o fato antes da
       resposta — e a correcao da spec **nao o alcanca**. A forma curta em
       string entra aqui: ela nao carrega qualificador, e sem esta direcao seria
       o desvio por escrita.

    A ORDEM DE PRECEDENCIA e deliberada: valor nao definido primeiro. Um pack com
    os dois defeitos tem um problema de VALOR, e nomear a chave faltando antes
    mandaria o autor acrescentar um campo que ele ja escreveu errado.

    NAO HA PERNA PARA `self`: o avaliador o implementa. Recusar a forma normativa
    faria o cenario canonico da propria spec deixar de carregar, que e pior que o
    defeito que a recusa corrigiria — e foi correcao de rota do proprietario.

    `qualificadores` CHEGA COMO DADO — `04` §4.1. Ele sai de
    `contracts/ground_truth.schema.yaml` §`$defs/since_qualifier` por
    `contract_source.since_qualifiers`, e nao de constante deste modulo. Ate o
    primeiro bloco da peca 2 da Fase 7 a linha `SINCE_SELF = "self"` existia
    aqui **e** em `engine/verificacao.py`, e a concordancia entre as duas era
    coincidencia mantida a mao.
    """
    predicados = (ground_truth or {}).get("verification_predicates") or {}
    valor_nao_definido: list[str] = []
    contencao_sem_since: list[str] = []

    for nome, arvore in sorted(predicados.items()):
        for caminho, alvo in _folhas_absence_of(arvore):
            onde = f"{nome}.{caminho}"
            if isinstance(alvo, Mapping) and "since" in alvo:
                if alvo["since"] not in qualificadores:
                    valor_nao_definido.append(f"{onde} (since: {alvo['since']!r})")
            elif nome == PREDICADO_QUE_EXIGE_SINCE:
                contencao_sem_since.append(onde)

    if valor_nao_definido:
        raise PackError(
            PackSite.SINCE_UNDEFINED_VALUE,
            "`absence_of.since` com valor nao definido: "
            + ", ".join(valor_nao_definido)
            + ".\n"
            f"    O contrato declara {sorted(qualificadores)!r} em "
            "`ground_truth.schema.yaml` §`$defs/since_qualifier`, e "
            "`03_EXERCISE_DESIGN.md` §3.1 e quem os define. Qualquer outro valor "
            "e recusado na carga enquanto nao houver semantica declarada para "
            "ele. Recusar aqui e recusar enquanto da para consertar o pack; "
            "avaliar seria inventar."
        )

    if contencao_sem_since:
        raise PackError(
            PackSite.CONTAINMENT_ABSENCE_WITHOUT_SINCE,
            "predicado de contencao com `absence_of` sem qualificador: "
            + ", ".join(contencao_sem_since)
            + ".\n"
            f"    `03_EXERCISE_DESIGN.md` §3.1 exige `since` — o contrato "
            f"declara {sorted(qualificadores)!r} — na "
            "folha `absence_of` do predicado de CONTENCAO. Sem ele a ausencia "
            "vale sobre a linhagem inteira — o predicado passa a afirmar que o "
            "fato NUNCA ocorreu, e nenhum cenario que materialize exfiltracao "
            "antes da resposta consegue satisfazer contencao. A metrica nao "
            "falha: ela deixa de marcar, que e o modo mais caro de errar.\n"
            "    A forma curta em string tambem cai aqui: ela nao carrega "
            "qualificador. Fora da contencao, ausencia total continua legitima."
        )


#: O documento de prosa do facilitador. NAO esta em `x-aurora-documents` — ele
#: nao e documento de maquina, e `scope_from_contract` o exclui por nao terminar
#: em `.yaml`. E lido AQUI, e so para o linter.
GM_NOTES = "GM_NOTES.md"


def confere_citacoes_do_pack(
    raiz: Path,
    documentos: Mapping[str, Mapping],
    contracts: Mapping[str, Mapping],
) -> None:
    """Item 8 da DoD e `06` T8 — os TRES lados que citam fato, contra `facts`.

    NA CARGA, e nao so no `range-cli scenario lint`. A mesma razao de
    `confere_folhas_temporais`: recusar enquanto ainda da para consertar o pack,
    e nao quando a sala esta cheia. O verbo do CLI (peca 4) chamara ESTA funcao —
    uma implementacao, dois chamadores, que e a §1.4 do checkpoint.

    TRES LADOS CITAM FATO, E ESTA FUNCAO COBRE **UM**. A medicao e o que decide,
    e ela foi feita antes de escrever:

        materializes_facts  JA COBERTO, por DOIS mecanismos — `$ref` para
                            `fact_id_pattern` (a forma, PR #59) e
                            `x-aurora-ref: pack_facts` (a existencia, desde a
                            Fase 2). Medido: plantar `GT-FANTASMA-999` ali
                            recusa com sitio `rule_violation`, ANTES desta
                            funcao rodar.
        projects_facts      JA COBERTO pelo mesmo par, em
                            `evidence.schema.yaml`. Nao ha MANIFEST na arvore —
                            `evidence build` e da Fase 9 —, mas o mecanismo que
                            o julgara ja existe e nao e este.
        GM_NOTES.md         **NAO COBERTO POR NADA**, e e o que sobra para ca.

    **POR QUE SO O `GM_NOTES` VEM PARA CA, e nao os tres.** Acrescentar os dois
    primeiros seria a TERCEIRA implementacao de *"este fato existe?"* — e o
    modulo de citacoes existe justamente para que essa pergunta tenha uma
    resposta so. A D4 nao deixa de ser D4 por estar dentro do mecanismo que a
    persegue.

    **E o `GM_NOTES` nao e alcancavel pelos outros dois por razao ESTRUTURAL**,
    e nao por esquecimento: `$ref` e `x-aurora-ref` operam sobre documento de
    maquina, e ele e PROSA. `scope_from_contract` o exclui por nao terminar em
    `.yaml`, e nenhuma regra do contrato tem como varrer markdown. E a unica das
    tres portas que nao tinha guarda, e e o que o item 8 da DoD nomeia.

    A FUNCAO DO NUCLEO CONTINUA GERAL, com as tres fontes: quem a chamar com um
    MANIFEST na Fase 9 nao precisa de codigo novo, e o `range-cli scenario lint`
    da peca 4 chamara ESTA — uma implementacao, dois chamadores.

    `GM_NOTES.md` AUSENTE NAO E ERRO: ele e `optional` em
    `x-aurora-registry.package_files`, e o pacote apenas-manifesto (`04` §9) nao
    o tem.
    """
    ground_truth = documentos.get("ground_truth.yaml")
    if ground_truth is None:
        # Sem ground truth nao ha contra o que conferir. Pacote apenas-manifesto
        # cai aqui, e `_verify_completude` ja separou essa forma da defeituosa.
        return

    fontes: dict[str, object] = {}

    caminho_do_gm = raiz / GM_NOTES
    if caminho_do_gm.is_file():
        try:
            fontes[GM_NOTES] = caminho_do_gm.read_text(encoding="utf-8")
        except OSError as exc:
            raise PackError(
                PackSite.DOCUMENT_UNREADABLE, f"{caminho_do_gm}: nao pode ser lido — {exc}"
            ) from exc

    # `materializes_facts` NAO ENTRA AQUI — ver o docstring. Ele ja e conferido
    # duas vezes antes desta linha: pela forma, no `_verify_schema`, e pela
    # existencia, no `_verify_rules`. Uma terceira conferencia nao acrescentaria
    # garantia e acrescentaria uma copia da pergunta.

    if not fontes:
        return

    try:
        confere_citacoes_de_fato(
            declarados=fatos_declarados(ground_truth),
            fontes=fontes,
            forma=fact_id_pattern(dict(contracts)),
        )
    except CitacaoInvalida as erro:
        raise PackError(PackSite.CITACAO_DE_FATO_INVALIDA, str(erro)) from erro


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
        # A biblioteca de rubricas e do core (00 secao 5.8) e vem da arvore em
        # execucao — nao e dado de dominio nem de pack. E ela que executa
        # *"rubrica ausente ou em versao diferente impede a carga"* (04 secao 2),
        # pelo mesmo `x-aurora-ref` com que a flag desconhecida impede o boot.
        load_library(),
        manifest_document=documentos.get("manifest.yaml"),
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


def _fatos_com_projecao(ground_truth: Mapping | None) -> frozenset[str]:
    """`fact_id` dos fatos que aparecem em ALGUMA fonte de evidência.

    Fato sem `projections` é invisível ao time azul **de propósito** — `08` §2 o
    usa para ensinar limite de detecção. Ele não move a camada de evidência
    observável, e por isso não conta para impacto observável: abrir `TTA` nele
    mediria latência contra um relógio que a equipe não tinha como ver começar.
    """
    return frozenset(
        fato["fact_id"]
        for fato in (ground_truth or {}).get("facts") or []
        if fato.get("projections")
    )


def _tem_impacto_observavel(bruto: Mapping, fatos_com_projecao: frozenset[str]) -> bool:
    """O predicado de `03` §3 — três pernas, e a exclusão decidida.

    **Derivado, e não declarado.** O `spec-change` `impacto-observavel-definido`
    fixou as três: `effects`, `materializes_facts` com fato que tenha
    `projections`, e `evidence_release`.

    A perna de `effects` é **estrutural e não costume**: `state_flags.schema.yaml`
    exige `effect_ui`, `wallboard_group` e `consumers` em toda flag, então não
    existe flag que se mova sem lugar onde a mudança apareça.

    **`reveals` fica de fora, e a exclusão é decidida.** Ele alimenta crença do
    participante — a terceira camada de `00` §3 —, e não o mundo nem a evidência
    descobrível. `TTA` mede a distância da primeira camada à terceira: sala
    **informada** não é sala que **detectou**.
    """
    if bruto.get("effects"):
        return True
    if bruto.get("evidence_release"):
        return True
    return any(
        fato in fatos_com_projecao for fato in (bruto.get("materializes_facts") or [])
    )


def _build_injects(
    injects_document: Mapping, ground_truth: Mapping | None = None
) -> tuple[Inject, ...]:
    """O modelo de inject, ja sobre documento validado pelas duas camadas.

    `effects` ausente vira mapeamento VAZIO, e a entrada existe mesmo assim: o
    fold levanta `INJECT_NOT_IN_PACK` para inject que nao esta em
    `inject_effects`, e um inject sem effects e legitimo — inject de revelacao ou
    de midia nao move flag.
    """
    fatos_com_projecao = _fatos_com_projecao(ground_truth)
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
                observable_impact=_tem_impacto_observavel(bruto, fatos_com_projecao),
                requires_response=bool(
                    (bruto.get("media_event") or {}).get("requires_response")
                ),
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
