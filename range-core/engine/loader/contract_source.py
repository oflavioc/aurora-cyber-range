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

Passam a existir DOIS parsers lendo os mesmos contratos, e isso e risco
real de divergencia. Por isso `tests/test_pack_loader.py::DoisParsers` afirma
que os dois produzem a MESMA arvore para todos eles — o que tambem fecha, por
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


def parse_document_com_texto(caminho: Path) -> tuple[dict, str]:
    """O documento E o texto de que ele saiu, de UMA leitura so.

    O TEXTO SOBE JUNTO PORQUE O LINTER PRECISA DELE, e precisa dele SEM reler.
    `range-cli scenario lint` resolve `linha:coluna` compondo a arvore de nos do
    YAML (`engine/loader/posicao.py`), e a exigencia de T12 e sobre LOCALIZAR:
    posicao calculada sobre uma segunda leitura aponta para o arquivo que esta
    no disco agora, e nao para o que foi validado. Entre as duas leituras cabe
    uma edicao, e o relatorio passaria a mentir com a mesma confianca com que
    acerta.

    Devolver o texto em vez de expor um `compose` aqui mantem este modulo com um
    trabalho so — ler e parsear —, e deixa a arvore de nos com quem a consome.

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
        return {}, texto
    if not isinstance(documento, dict):
        raise ContractSourceError(
            f"{caminho}: documento de topo e {type(documento).__name__}, esperado mapeamento"
        )
    return documento, texto


def parse_document(caminho: Path) -> dict:
    """Só o documento — para quem não tem o que fazer com o texto.

    Uma implementacao, dois chamadores: quem so precisa do documento nao paga
    por uma leitura propria, e as duas formas nao podem divergir porque uma
    delega a outra.
    """
    return parse_document_com_texto(caminho)[0]


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


def fact_id_pattern(contratos: dict[str, dict]) -> str:
    """A forma de `fact_id`, LIDA do contrato.

    `contracts/ground_truth.schema.yaml` §`$defs/fact_id_pattern`, que o PR #59
    criou justamente para que as quatro referencias que resolvem `fact_id` — o
    campo, `materializes_facts`, `projects_facts` e `fact_check_against` — nao
    tivessem cada uma a sua copia.

    O LINTER DE CITACAO A CONSOME COMO DADO, e nao a reescreve: ele e o quinto
    lugar a falar dessa forma, e o primeiro que NAO e um campo de contrato.
    Escreve-la la seria a copia que o #59 acabou de eliminar, ressuscitada num
    modulo que ninguem pensaria em cruzar com o schema.
    """
    ground_truth = contratos.get("ground_truth") or {}
    padrao = ((ground_truth.get("$defs") or {}).get("fact_id_pattern") or {}).get(
        "pattern"
    )
    if not padrao:
        raise ContractSourceError(
            "contracts/ground_truth.schema.yaml sem "
            "`$defs/fact_id_pattern.pattern`: sem ele o linter de citacao teria "
            "de reescrever a forma, e citacao e declaracao passariam a poder "
            "divergir — que e o que ele existe para impedir"
        )
    return padrao


def formas_do_destino(contratos: dict[str, dict]) -> tuple[str, str]:
    """`(forma de domain, forma de pack_id)`, LIDAS do contrato.

    `04_SCENARIO_SCHEMA.md` §8.1 (b) manda o destino do pack ser
    `scenarios/<domain>/<pack_id>/`, e diz que *"os dois segmentos tem forma
    declarada em `contracts/scenario.schema.v2.yaml`"*. Sao as mesmas duas
    formas que o manifesto usa — e a igualdade nao e coincidencia: o diretorio
    em que o pack mora e o `pack_id` que ele declara.

    MESMA FORMA DE `rollback_reasons` e `since_qualifiers`: recebe os contratos
    ja parseados, faz a busca, nao toca disco. `engine/destino.py` as recebe por
    parametro em vez de as reescrever, pela regra de `04` §4.1 — duas copias de
    um padrao divergem, e foi por isso que `case_id` deixou de ter duas no #59.
    """
    scenario = contratos.get("scenario") or {}
    propriedades = scenario.get("properties") or {}
    formas = []
    for campo in ("domain", "pack_id"):
        padrao = (propriedades.get(campo) or {}).get("pattern")
        if not padrao:
            raise ContractSourceError(
                f"contracts/scenario.schema.v2.yaml sem `properties.{campo}.pattern`: "
                "sem ele o produtor de pack teria de reescrever a forma do "
                "segmento, e `04` §8.1 a declara como sendo a do contrato"
            )
        formas.append(padrao)
    return formas[0], formas[1]


def since_qualifiers(contratos: dict[str, dict]) -> frozenset[str]:
    """Os qualificadores de instante de `absence_of`, LIDOS do contrato.

    `03_EXERCISE_DESIGN.md` §3.1 fixa `self` como a UNICA forma de v1;
    `contracts/ground_truth.schema.yaml` a declara em `$defs/since_qualifier`
    desde o PR #59, que trocou `type: string` livre por `enum`.

    MESMA FORMA DE `rollback_reasons`, e o paralelo e o argumento: recebe os
    contratos JA PARSEADOS, faz a busca, e nao toca disco. Quem le disco e
    `read_contracts`, uma vez, na raiz de composicao — `04` §4.1.

    O QUE ESTA FUNCAO DESFAZ. `SINCE_SELF = "self"` estava definido DUAS vezes,
    em `engine/loader/pack_loader.py` e em `engine/verificacao.py`, sem import
    entre elas e sem verificador cruzando. As duas concordavam por COINCIDENCIA
    — os dois comentarios citavam a mesma fonte, e a unica guarda era lembrar.
    Mudar uma e esquecer a outra faria carga e avaliacao discordarem sobre o
    mesmo campo: um pack recusado no boot que o avaliador aceitaria, ou o
    inverso. E a classe D4.

    CONJUNTO, E NAO VALOR UNICO, pelo mesmo motivo de `rollback_reasons` e com um
    gatilho ja datado: a P6-3 traz a gramatica de `exercise_time`, e com ela uma
    segunda forma de `since` passa a ser definivel. Devolver a string faria a
    assinatura mudar no dia em que o enum ganhasse o segundo valor; devolver o
    conjunto faz o valor novo atravessar sem tocar em codigo nenhum.
    """
    ground_truth = contratos.get("ground_truth") or {}
    enum = ((ground_truth.get("$defs") or {}).get("since_qualifier") or {}).get("enum")
    if not enum:
        raise ContractSourceError(
            "contracts/ground_truth.schema.yaml sem `$defs/since_qualifier`: "
            "sem ele, a guarda de carga e o avaliador voltariam a ter cada um o "
            "seu literal, que e o defeito que esta funcao existe para desfazer"
        )
    return frozenset(enum)
