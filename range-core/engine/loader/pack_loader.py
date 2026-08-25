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
from dados_sinteticos import achados_no_valor
from range_core.engine.citacoes import (
    CitacaoInvalida,
    confere_citacoes_de_fato,
    confere_fact_check_against,
    fatos_declarados,
    fatos_por_id,
)
from range_core.engine.migrations import MIGRACOES, ha_migracao
from range_core.rubrics.library import load_library
from range_core.engine.loader.contract_source import (
    ContractSourceError,
    documents_by_id,
    parse_document_com_texto,
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
    #: `t_relative` declarado antes do inject anterior DA MESMA LINHA.
    #: `04` §8 lista *"t_relative fora de ordem"* entre as checagens do
    #: `range-cli scenario lint`, e ate a peca 3 da Fase 7 nada a executava.
    T_RELATIVE_OUT_OF_ORDER = "t_relative_out_of_order"
    #: `fact_check_against` cujo ponteiro nao resolve — fato ausente, ou campo
    #: ausente do fato que existe. Declarada em `x-aurora-linter-rules` desde a
    #: Fase 1 e sem mecanismo ate a peca 3 da Fase 7.
    FACT_CHECK_UNRESOLVED = "fact_check_unresolved"
    #: IOC operacional no `ground_truth.yaml` — IP ou dominio roteavel, CPF que
    #: passa no digito verificador. `05_SECURITY_REQUIREMENTS.md` §5.2 e §3, e a
    #: **P7-7**, cujo gatilho declarado era esta peca.
    IOC_OPERACIONAL = "ioc_operacional"


class PackError(Exception):
    """O pack nao carrega, e o engine nao sobe.

    Recusa alta e deliberada, pelo mesmo motivo do `PackMismatch` do fold: um
    pack meio validado produz exercicio plausivel e errado, e a divergencia
    aparece no AAR, fases adiante.

    `arquivo` E `caminho` SAO OPCIONAIS, E SAO O QUE O LINTER LOCALIZA. Quem os
    tem, os declara; quem nao os tem — recusa sobre o diretorio, sobre a versao —
    os deixa em `None`, e o linter reporta a recusa sem `linha:coluna` em vez de
    inventar uma. `06` T12 exige posicao para as recusas que a nomeiam, e nao
    para todas: recusa de pack sem `manifest.yaml` nao tem linha nenhuma onde
    caber.

    Eles NAO entram na mensagem. A mensagem e prosa em portugues e vai ser
    reescrita; estes sao dados, e e sobre dado que o relatorio se monta — a mesma
    razao pela qual `site` existe desde a Fase 2.
    """

    def __init__(
        self,
        site: str,
        message: str,
        *,
        arquivo: str | None = None,
        caminho: str | None = None,
    ) -> None:
        super().__init__(f"[{site}] {message}")
        self.site = site
        #: A mensagem SEM o prefixo de sitio. O linter ja imprime o sitio no
        #: cabecalho do achado, e reimprimi-lo dentro do corpo dobraria a
        #: etiqueta em toda linha do relatorio.
        self.mensagem = message
        self.arquivo = arquivo
        self.caminho = caminho


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

    OS PASSOS 3 A 5 SAO UMA LISTA, E ELA TEM DOIS CONSUMIDORES — `_passos`. Este
    aqui os roda em ordem e para no primeiro que levantar; `varre_pack` roda a
    mesma lista colhendo todos. Duas listas seriam o gate aceitando pack que o
    boot recusa, com outro nome — a classe que a §1.4 do checkpoint fechou em
    `contract_rules`.
    """
    raiz, documentos, _ = _abre(pack_dir, contracts)
    manifest = documentos["manifest.yaml"]
    content_hash = content_hash_v1(documentos)

    for passo in _passos(raiz, documentos, contracts, adapter_flags):
        passo()

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


def _abre(
    pack_dir: Path | str, contracts: Mapping[str, Mapping]
) -> tuple[Path, dict[str, Mapping], dict[str, str]]:
    """Os tres passos ANTERIORES a qualquer regra: diretorio, presenca, leitura.

    ELES NAO ENTRAM EM `_passos`, e a exclusao e de especie. Um passo da lista
    julga o CONTEUDO do pack e pode ser colhido ao lado dos outros; estes tres
    decidem se ha pack. Sem `manifest.yaml` nao se sabe nem o que se esta lendo,
    e um linter que "colhesse" essa recusa junto de outras estaria relatando
    achados sobre documentos que nao leu.

    Por isso `varre_pack` os deixa subir: a recusa e a mesma do boot, e a
    resposta a ela e a mesma — arrume o pacote e rode de novo.
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
                arquivo=arquivo,
            )

    documentos, textos = _read_documents(raiz, scope_from_contract(scenario))
    return raiz, documentos, textos


def _passos(
    raiz: Path,
    documentos: Mapping[str, Mapping],
    contracts: Mapping[str, Mapping],
    adapter_flags: AdapterFlags,
):
    """A lista de recusas, na ordem. UM dono, dois consumidores.

    A ORDEM E PARTE DA GARANTIA, e o docstring de `load_pack` a enuncia. O que
    esta lista acrescenta e que ela deixa de estar escrita dentro de um dos dois
    consumidores: enquanto `load_pack` era o unico, a ordem era o corpo dele, e
    o linter teria de a repetir para relatar as mesmas recusas.

    Cada elemento e um `callable` sem argumento que levanta `PackError` ou nao
    faz nada. Quem consome decide o que fazer com o levantamento — parar, no
    boot; colher, no linter.

    GRANULARIDADE POR DOCUMENTO nas duas camadas de contrato. Para o boot e
    indiferente, porque ele para na primeira; para o linter e o que faz um
    `injects.yaml` defeituoso nao esconder o `branches.yaml` ao lado.
    """
    scenario = contracts["scenario"]
    manifest = documentos.get("manifest.yaml") or {}
    ground_truth = documentos.get("ground_truth.yaml")
    base = scenario.get("$id", "")
    mapa = sorted((scenario.get("x-aurora-documents") or {}).items())

    yield lambda: _verify_completude(raiz, documentos, scenario)
    yield lambda: _verify_schema_version(raiz, manifest)

    registry = registry_for(dict(contracts))
    for arquivo, ponteiro in mapa:
        if arquivo not in documentos:
            continue
        alvo, origem = _alvo_de_schema(ponteiro, base)
        yield (
            lambda arquivo=arquivo, alvo=alvo, origem=origem: _verify_schema_documento(
                arquivo, documentos[arquivo], alvo, origem, registry
            )
        )

    yield lambda: _verify_engine_version(raiz, manifest)

    # Os registros e o mapa de `$id` sao os mesmos para todo documento, e sao
    # montados uma vez — a leitura da biblioteca de rubricas nao se paga quatro
    # vezes por carga.
    registros = _registros_do_pack(documentos, contracts, adapter_flags)
    docs_por_id = documents_by_id(dict(contracts))
    for arquivo, ponteiro in mapa:
        if arquivo not in documentos:
            continue
        yield (
            lambda arquivo=arquivo, ponteiro=ponteiro: _verify_rules_documento(
                arquivo,
                documentos[arquivo],
                ponteiro,
                base=base,
                registros=registros,
                docs_por_id=docs_por_id,
                registry=registry,
                adapter_flags=adapter_flags,
            )
        )

    # DEPOIS da camada 1, e a ordem e a mesma razao de `_verify_engine_version`:
    # `t_relative` malformado e `media_event` sem forma sao recusa do contrato, e
    # rodar depois dele torna a garantia de forma disponivel em vez de suposta.
    yield lambda: confere_ordem_de_t_relative(documentos.get("injects.yaml"))
    yield lambda: confere_fact_check_do_pack(documentos)

    # `05` §5.2 e a P7-7. ANTES das guardas de predicado: um pack com IOC real e
    # defeito de outra especie — as outras recusas desta lista custam retrabalho
    # de autoria, esta custa `05` §1 violado num artefato que roda na sala.
    yield lambda: confere_ausencia_de_ioc(ground_truth)

    yield lambda: confere_folhas_temporais(ground_truth)
    # O QUALIFICADOR SAI DO CONTRATO, e `load_pack` ja recebe `contracts` — a
    # origem estava ao alcance sem encanamento novo. `04` §4.1.
    yield lambda: confere_qualificador_since(
        ground_truth, qualificadores=since_qualifiers(dict(contracts))
    )
    yield lambda: confere_citacoes_do_pack(raiz, documentos, contracts)


def varre_pack(
    pack_dir: Path | str,
    *,
    contracts: Mapping[str, Mapping],
    adapter_flags: AdapterFlags,
) -> tuple[list[PackError], dict[str, str]]:
    """TODAS as recusas do pack, e o texto de cada documento lido.

    O SEGUNDO CONSUMIDOR DE `_passos` — `range-cli scenario lint`. A diferenca
    com `load_pack` e uma so: aquele para na primeira recusa, este colhe a lista
    inteira.

    POR QUE COLHER, e nao chamar `load_pack` e traduzir o levantamento
    ------------------------------------------------------------------
    `04` §8 da nomes e listas de checagem DISTINTOS a `validate` e a `lint`, e a
    diferenca util entre os dois e exatamente esta. Um linter que relata um
    defeito por execucao manda o autor consertar e rodar de novo para descobrir
    o proximo — e o pack de 4 h da `04` §9 tem seis documentos. Nesse regime o
    verbo `lint` nao acrescentaria nada a `validate`, e a spec nao teria por que
    ter os dois.

    OS TEXTOS SOBEM JUNTO porque e sobre eles que a posicao se resolve, e eles
    vem da MESMA leitura que produziu os documentos validados. Ver
    `contract_source.parse_document_com_texto`.

    O QUE NAO E COLHIDO: as recusas de `_abre` — diretorio, presenca de
    `manifest.yaml`, documento ilegivel. Elas sobem, e o docstring de `_abre` diz
    por que.
    """
    raiz, documentos, textos = _abre(pack_dir, contracts)
    achados: list[PackError] = []
    for passo in _passos(raiz, documentos, contracts, adapter_flags):
        try:
            passo()
        except PackError as erro:
            achados.append(erro)
    return achados, textos


def _read_documents(
    raiz: Path, escopo: tuple[str, ...]
) -> tuple[dict[str, Mapping], dict[str, str]]:
    """Os documentos de maquina PRESENTES, e o texto de cada um.

    Ausencia nao e erro aqui: o pacote apenas-manifesto e forma legitima
    (`04` §9, e o `x-aurora-registry` do contrato separa `required` de
    `required_for_complete_pack` por causa dela). Quem cobra presenca e o passo
    anterior, contra a lista do contrato.

    O TEXTO VEM DA MESMA LEITURA que produziu o documento — `parse_document_com_texto`
    —, e nao de uma segunda. O linter resolve `linha:coluna` sobre ele, e a razao
    de nao reler esta no docstring daquela funcao.
    """
    documentos: dict[str, Mapping] = {}
    textos: dict[str, str] = {}
    for arquivo in escopo:
        caminho = raiz / arquivo
        if not caminho.is_file():
            continue
        try:
            documentos[arquivo], textos[arquivo] = parse_document_com_texto(caminho)
        except ContractSourceError as exc:
            raise PackError(
                PackSite.DOCUMENT_UNREADABLE, str(exc), arquivo=arquivo
            ) from exc
    return documentos, textos


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


def _alvo_de_schema(ponteiro: str | None, base: str) -> tuple[dict, str]:
    """`(o que validar contra, como se chama)` para um documento do pacote.

    PONTEIRO RELATIVO resolve no contrato de cenario; URI ABSOLUTA resolve em
    outro — `ground_truth.yaml` e `objectives.yaml` tem contrato proprio, e e por
    isso que o mapa carrega `$ref` e nao so ponteiro (B1 da Fase 6).
    """
    if ponteiro and "://" in ponteiro:
        return {"$ref": ponteiro}, ponteiro
    if ponteiro in (None, "#"):
        return {"$ref": base}, f"contracts/scenario.schema.v2.yaml{ponteiro or ''}"
    return (
        {"$ref": f"{base}{ponteiro}"},
        f"contracts/scenario.schema.v2.yaml{ponteiro}",
    )


def _verify_schema_documento(
    arquivo: str, documento: Mapping, alvo: dict, origem: str, registry
) -> None:
    """Camada 1, sobre UM documento.

    POR DOCUMENTO, E NAO SOBRE A COLECAO, e a granularidade e o que o linter
    precisa: `load_pack` para na primeira recusa de qualquer jeito, e para ele a
    diferenca e nenhuma. Para `range-cli scenario lint`, um passo por documento e
    o que faz um `injects.yaml` defeituoso nao esconder o `branches.yaml` ao
    lado — que e a diferenca entre um linter e um boot que nao carrega.
    """
    erros = sorted(
        Draft202012Validator(alvo, registry=registry).iter_errors(documento), key=str
    )
    if not erros:
        return
    detalhe = "\n".join(f"    {e.json_path}: {e.message}" for e in erros[:5])
    raise PackError(
        PackSite.DOCUMENT_INVALID,
        f"`{arquivo}` nao valida contra `{origem}` ({len(erros)} erro(s)):\n{detalhe}",
        arquivo=arquivo,
        caminho=erros[0].json_path,
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


def confere_ordem_de_t_relative(injects_document: Mapping | None) -> None:
    """*"`t_relative` fora de ordem e recusado"* — `04` §8 e `x-aurora-linter-rules`.

    POR LINHA, E NAO PELA SEQUENCIA INTEIRA — e a diferenca foi MEDIDA, nao
    escolhida por gosto. `04` §9 manda o `ransomware-universidade` ter *"Linhas A
    + B + ruido"*, e linhas correm em paralelo no relogio do exercicio: exigir
    ordem global obrigaria o autor a intercalar as tres num arquivo so, o que
    troca um defeito de autoria por um custo de leitura em todo pack multilinha.

    A MEDICAO: o exemplo positivo de `injects_document` em
    `contracts/scenario.schema.v2.yaml` declara `00:47, 00:55, 01:10, 01:15,
    01:40` na linha A e `00:52` no inject de ruido, que nao tem `linha`. Sob
    ordem global ele seria RECUSADO — e ele e a fixture que o gate de exemplos
    usa como valida. Regra que reprova o exemplo positivo do proprio contrato e
    regra escrita contra a fonte, que e a classe do B4 da terceira auditoria.

    INJECT SEM `linha` FORMA GRUPO PROPRIO. O campo e opcional no contrato, e o
    inject de ruido do exemplo nao o tem — `03` §5.2 mantem a linha invisivel ao
    operador, entao ela e do facilitador e nem todo inject a declara.

    O QUE ISSO **NAO** E: garantia de disparo. `inject_engine` ordena por
    `(t_relative_seconds, id)` e dispararia certo de qualquer jeito. Esta recusa
    e sobre AUTORIA — um `01:50` digitado onde se queria `00:50` continua
    disparando, na hora errada, e o unico sinal e a ordem do arquivo.

    NA CARGA TAMBEM, e nao so no linter. Regra que o `lint` recusasse e o boot
    aceitasse produziria pack reprovado pelo CI e carregado pelo engine — a
    divergencia entre os dois chamadores que `contract_rules` existe para nao
    deixar voltar.
    """
    anterior: dict[object, tuple[str, int]] = {}
    for indice, bruto in enumerate((injects_document or {}).get("injects") or []):
        if not isinstance(bruto, Mapping):
            continue
        valor = bruto.get("t_relative")
        if valor is None:
            continue  # a ausencia e recusa da camada 1, com sitio proprio
        try:
            segundos = t_relative_seconds(valor, str(bruto.get("id")))
        except PackError:
            return  # forma malformada: quem recusa e o passo dela, e antes deste
        linha = bruto.get("linha")
        anterior_id, anterior_segundos = anterior.get(linha, (None, -1))
        if segundos < anterior_segundos:
            rotulo = f"linha {linha!r}" if linha is not None else "injects sem `linha`"
            raise PackError(
                PackSite.T_RELATIVE_OUT_OF_ORDER,
                f"inject {bruto.get('id')!r}: `t_relative: {valor!r}` vem depois "
                f"de {anterior_id!r} (`{anterior_segundos // 3600:02d}:"
                f"{anterior_segundos % 3600 // 60:02d}`) no arquivo, e ANTES dele "
                f"no relogio — os dois estao na mesma {rotulo}.\n"
                "    O engine ordena por `t_relative` e dispararia na ordem certa; "
                "o que esta recusado aqui e a AUTORIA. Um `01:50` digitado onde "
                "se queria `00:50` dispara na hora errada sem nada falhar, e a "
                "ordem do arquivo e o unico sinal que sobra.\n"
                "    A ordem e exigida DENTRO de cada linha, e nao entre linhas: "
                "`04_SCENARIO_SCHEMA.md` §9 poe Linhas A, B e ruido em paralelo "
                "no mesmo exercicio.",
                arquivo="injects.yaml",
                caminho=f"$.injects[{indice}].t_relative",
            )
        anterior[linha] = (bruto.get("id"), segundos)


def _citacoes_de_fact_check(injects_document: Mapping | None) -> dict[str, str]:
    """`caminho de instancia -> valor` de todo `fact_check_against` do pack.

    A CHAVE E O CAMINHO, e nao o id do inject, porque e ela que o linter localiza
    no arquivo. Ela entra na mensagem de `confere_fact_check_against` como o
    "onde", entao o autor le o mesmo endereco na prosa e no `linha:coluna`.
    """
    citacoes: dict[str, str] = {}
    for indice, bruto in enumerate((injects_document or {}).get("injects") or []):
        if not isinstance(bruto, Mapping):
            continue
        media = bruto.get("media_event")
        if isinstance(media, Mapping) and media.get("fact_check_against"):
            citacoes[f"$.injects[{indice}].media_event.fact_check_against"] = str(
                media["fact_check_against"]
            )
    return citacoes


def confere_fact_check_do_pack(
    documentos: Mapping[str, Mapping],
) -> None:
    """A quarta citacao de fato — `fact_check_against`, de `04` §7.

    AS OUTRAS TRES JA TINHAM DONO, e esta nao tinha: `materializes_facts` e
    `projects_facts` sao cobertas pelo par `$ref` + `x-aurora-ref`, e o
    `GM_NOTES.md` pelo linter de citacao da peca 2. Esta nao e alcancavel por
    `x-aurora-ref` por razao estrutural — o valor nao e um `fact_id`, e sim
    `facts.<fact_id>.<campo>`, e o registro resolve valores inteiros.

    SEM GROUND TRUTH NAO HA CONTRA O QUE CONFERIR, e a ausencia nao e erro aqui:
    pacote apenas-manifesto (`04` §9) nao o tem, e `_verify_completude` ja separou
    essa forma da defeituosa.
    """
    ground_truth = documentos.get("ground_truth.yaml")
    if ground_truth is None:
        return
    citacoes = _citacoes_de_fact_check(documentos.get("injects.yaml"))
    if not citacoes:
        return
    try:
        confere_fact_check_against(
            fatos=fatos_por_id(ground_truth), citacoes=citacoes
        )
    except CitacaoInvalida as erro:
        raise PackError(
            PackSite.FACT_CHECK_UNRESOLVED,
            str(erro),
            arquivo="injects.yaml",
            # O "onde" da mensagem E o caminho, por construcao de
            # `_citacoes_de_fact_check`. Reextrai-lo da prosa seria fazer o dado
            # atravessar a mensagem para voltar a ser dado.
            caminho=str(erro).split("`", 2)[1],
        ) from erro


#: O bloco de `05` §5.2 que EXIGE fonte publica citavel, e por isso e o unico
#: lugar do gabarito onde nomear um dominio real e o proposito, e nao o defeito.
#:
#: `attack.mitre.org` numa `sources` e CITACAO; o mesmo dominio num `source_ip`
#: ou numa projecao seria INFRAESTRUTURA. A varredura nao distingue as duas — e
#: nao tem como —, entao a distincao entra como caminho isento, declarado.
#:
#: A ISENCAO E DE SUBARVORE, e nao de valor: isentar por valor faria o mesmo
#: dominio passar em qualquer lugar do documento, que e exatamente o oposto do
#: que a §5.2 quer.
CAMINHO_ISENTO_DE_IOC = ("threat_actor", "sources")


def _valores_com_caminho(no, caminho: str = "$"):
    """`(caminho de instancia, valor)` de cada folha de texto, em ordem de leitura.

    O DIALETO E O MESMO das duas camadas de contrato — `$`, `.chave`, `[i]` —,
    e e por isso que o resolvedor de posicao do linter serve a esta recusa sem
    codigo novo.

    A subarvore de `CAMINHO_ISENTO_DE_IOC` nao e descida. Ver a constante.
    """
    if isinstance(no, Mapping):
        for chave, valor in no.items():
            if (str(chave),) == CAMINHO_ISENTO_DE_IOC[:1] and isinstance(valor, Mapping):
                for filho, subvalor in valor.items():
                    if str(filho) == CAMINHO_ISENTO_DE_IOC[1]:
                        continue
                    yield from _valores_com_caminho(
                        subvalor, f"{caminho}.{chave}.{filho}"
                    )
                continue
            yield from _valores_com_caminho(valor, f"{caminho}.{chave}")
    elif isinstance(no, (list, tuple)):
        for indice, filho in enumerate(no):
            yield from _valores_com_caminho(filho, f"{caminho}[{indice}]")
    elif isinstance(no, str):
        yield caminho, no


def confere_ausencia_de_ioc(ground_truth: Mapping | None) -> None:
    """Nenhum IOC operacional no gabarito — `05` §5.2, e a **P7-7**.

    A PERGUNTA NAO E REIMPLEMENTADA AQUI. Ela e a mesma que
    `tools/check_synthetic_data.py` responde desde a Fase 0, e as duas passaram a
    chamar `dados_sinteticos` — o pacote de topo que a peca 3 extraiu justamente
    para nao haver duas respostas. Duas divergiriam no dia em que uma das faixas
    mudasse, e a divergencia **nao falha alto**: ela deixa passar.

    POR QUE A PERGUNTA PRECISAVA DE UM SEGUNDO CHAMADOR
    ----------------------------------------------------
    Aquele verificador varre a **arvore versionada**, e `scenarios/` esta fora do
    Git desde a peca 5 da Fase 5. O pack — que e onde o gabarito e o ator de
    ameaca moram — nunca passou por ele. O proprio `ground_truth.schema.yaml`
    declara em `x-aurora-linter-rules` que `source_ip` fica *"guardado por
    tools/check_synthetic_data.py"*, e para pack essa frase era falsa.

    DAS TRES EXIGENCIAS DA §5.2, ESTA E A UNICA MECANIZAVEL, e as outras duas
    estao declaradas no registro do contrato de cenario com destinatario
    `revisao humana`:

        fonte publica citavel   meia — o contrato exige `sources` nao vazio, e
                                "citavel" nao e forma. Mesma classe do
                                `control_function` de `04` §5.1
        TTP nao excedida        julgamento contra documento EXTERNO
        IOC ausente             ESTA

    O ESCOPO E O DOCUMENTO INTEIRO, e nao so o bloco do ator. A §5.2 diz que
    *"as faixas de documentacao da §3 continuam obrigatorias em toda evidencia"*,
    e o `source_ip` de um `fact` e o caso mais provavel de vazamento — o ator
    real e escrito com cuidado, o IP de um fato e copiado de um relatorio.

    NA CARGA TAMBEM, e nao so no linter. Pack com IOC real nao pode subir: e a
    unica das regras desta peca cujo custo de passar nao e retrabalho de autoria,
    e sim `05` §1 violado num artefato que roda na frente de cliente.

    O LIMITE, DECLARADO PORQUE E REAL: **dominio embutido em PROSA escapa.**
    -------------------------------------------------------------------------
    O predicado classifica VALORES — `hostnames_candidatos` extrai host de URL,
    de e-mail ou de hostname nu, e desiste quando o texto tem espaco. Entao
    `note_to_facilitator: "C2 em evil-infra.net"` **passa**, e foi medido.

    A alternativa seria varrer prosa por padrao de dominio, e ela nao foi tomada
    por dois motivos, nesta ordem: `tools/check_synthetic_data.py` declara desde
    a Fase 0 que *"nao ha varredura textual do arquivo bruto"*, e mudar isso
    mudaria o comportamento do verificador sobre a **arvore inteira** — seeds e
    seus comentarios incluidos — dentro de uma peca que nao pediu isso; e a rede
    larga sobre prosa produz falso positivo em volume, que e como um gate deixa
    de ser lido.

    **O campo mais exposto e o `note_to_facilitator`**, que e prosa por
    definicao. Ali a garantia hoje e revisao humana, como nas outras duas
    exigencias da §5.2 — e esta linha existe para que isso seja lacuna nomeada, e
    nao cobertura suposta.
    """
    if ground_truth is None:
        return
    achados: list[str] = []
    for caminho, valor in _valores_com_caminho(ground_truth):
        for achado in achados_no_valor(valor):
            achados.append(f"{caminho}: {achado.detalhe}")
    if not achados:
        return
    raise PackError(
        PackSite.IOC_OPERACIONAL,
        "`ground_truth.yaml` traz dado que nao e sintetico:\n"
        + "\n".join(f"    {linha}" for linha in achados[:5])
        + (f"\n    ... e mais {len(achados) - 5}" if len(achados) > 5 else "")
        + "\n    `05_SECURITY_REQUIREMENTS.md` §5.2 admite ator de ameaca REAL e "
        "documentado, e proibe IOC operacional junto: sem hash de amostra, sem IP "
        "ou dominio de infraestrutura real, sem chave. A §3 fixa as faixas, e "
        "elas valem em toda evidencia.\n"
        "    `threat_actor.sources` e ISENTO desta varredura, e e o unico: a "
        "§5.2 EXIGE fonte publica citavel ali, entao nomear um dominio real "
        "naquele campo e o proposito e nao o defeito.",
        arquivo="ground_truth.yaml",
        caminho=achados[0].split(":", 1)[0],
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


def _registros_do_pack(
    documentos: Mapping[str, Mapping],
    contracts: Mapping[str, Mapping],
    adapter_flags: AdapterFlags,
) -> dict:
    """Os registros contra os quais `x-aurora-ref` resolve, montados UMA vez.

    Hoisted para fora do laco por documento: eles nao dependem do documento que
    esta sendo checado, e remonta-los por documento seria pagar a leitura da
    biblioteca de rubricas quatro vezes por carga.
    """
    return build_pack_registries(
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


def _verify_rules_documento(
    arquivo: str,
    documento: Mapping,
    ponteiro: str | None,
    *,
    base: str,
    registros: dict,
    docs_por_id: dict,
    registry,
    adapter_flags: AdapterFlags,
) -> None:
    """Camada 2 — as regras `x-aurora-*`, pelo modulo que o gate de CI usa.

    ITEM 9 DA DoD MORA AQUI, e nao numa checagem propria de flag. Uma segunda
    implementacao de "a flag existe?" divergiria da primeira, e o gate passaria
    a aceitar pack que o boot recusa. O que este passo acrescenta e a
    CLASSIFICACAO: a violacao de `adapter_flags` sai com sitio proprio e com o
    arquivo esperado na mensagem, que e o que T2 exige alem do nome da flag.

    O CAMINHO DA PRIMEIRA VIOLACAO SOBE NO ERRO, e e ele que o linter localiza.
    A `AuroraChecker` ja o produzia — `$.branches[0].evaluate[0].when.all[0].event`
    — e ele morria dentro da mensagem, que e prosa. `06` T12 cobra a posicao
    justamente da recusa que nasce aqui: o `event_type` inexistente em condicao
    de branch e uma violacao de `x-aurora-ref: event_catalog`.
    """
    checker = AuroraChecker(registros, docs_por_id)
    violacoes = checker.check(base, ponteiro, documento, registry)
    if not violacoes:
        return

    # `ipath` e a cabeca do detalhe, ate o primeiro `: `. A `AuroraChecker` o
    # monta assim nas tres anotacoes, e le-lo de volta e mais barato que mudar a
    # forma de retorno dela — que tem outro chamador, o gate de CI.
    caminho = violacoes[0][1].split(":", 1)[0].strip()

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
            arquivo=arquivo,
            caminho=caminho,
        )
    raise PackError(
        PackSite.RULE_VIOLATION,
        f"`{arquivo}` viola regra de integridade referencial:\n{corpo}",
        arquivo=arquivo,
        caminho=caminho,
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
