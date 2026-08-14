#!/usr/bin/env python3
"""Executa os exemplos positivos e negativos dos contratos de `contracts/`.

Item 1 da DoD da Fase 1: *"os seis contratos existem e VALIDAM exemplos
positivos e negativos"*. Conter exemplo nao e validar exemplo — o item esteve
marcado como cumprido por presenca, que e a mesma classe do B1 da primeira
auditoria da Fase 0: o mecanismo existia, a propriedade nao.

DUAS CAMADAS, E A DISTINCAO ENTRE ELAS E O PONTO
------------------------------------------------
1. JSON Schema 2020-12, via `jsonschema`.
2. As anotacoes `x-aurora-*`, que expressam integridade referencial entre
   arquivos — coisa que nenhuma linguagem de schema expressa.

Um `event_type` com erro de digitacao e uma string perfeitamente valida para o
JSON Schema; quem o recusa e a camada 2. Um executor que rodasse so a camada 1
marcaria essa fixture como aprovada sem ter verificado nada.

Por isso cada exemplo negativo declara `rejected_by`, e este script exige que a
recusa venha DE LA:

  rejected_by: schema          -> o schema precisa recusar.
  rejected_by: x-aurora-<...>  -> o schema precisa ACEITAR (senao a fixture nao
                                  isola a regra que diz provar) e a regra
                                  nomeada precisa disparar.

NAO E UM DOS SEIS VERIFICADORES DE INVARIANTE. `01_ARCHITECTURE.md` secao 2
declara que sao seis, todos em `tools/`, todos stdlib. Este mora em `scripts/`,
depende de `jsonschema` e roda em job de CI separado, justamente para que o gate
que a Fase 0 construiu nao ganhe dependencia.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# O mesmo parser que o CI usa para ler os contratos. Usar outro validaria uma
# arvore diferente da que os verificadores enxergam.
from _common import ContractError, parse_yaml, rel  # noqa: E402

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover
    print(
        "ERRO: `jsonschema` nao esta instalado.\n"
        "      pip install -e .   (ver pyproject.toml, pendencia P1-6)",
        file=sys.stderr,
    )
    raise SystemExit(2)


CONTRACTS = REPO_ROOT / "contracts"

#: Chaves de topo que carregam exemplos, e nao fazem parte do schema validado.
EXAMPLE_KEYS = ("examples", "x-aurora-document-examples", "x-aurora-invalid-examples")


# ---------------------------------------------------------------------------
# Registros consultados pelas anotacoes `x-aurora-ref`
# ---------------------------------------------------------------------------


def _walk_defs(schema: dict, prefix: str) -> list:
    defs = schema.get("$defs") or {}
    return sorted(k for k in defs if k.startswith(prefix))


def build_registries(contracts: dict) -> dict:
    """Monta os registros contra os quais `x-aurora-ref` resolve.

    `event_catalog` e `adapter_flags` vem das fontes canonicas reais. Os
    registros `pack_*` vem dos EXEMPLOS POSITIVOS dos proprios contratos: os
    exemplos formam um mini-pacote sintetico, e e contra ele que as referencias
    cruzadas de fixture resolvem. Nenhum pacote de cenario existe antes da
    Fase 7, e inventar um so para o teste seria dado nao versionado guiando
    verificacao.
    """
    eventos = contracts["events"]
    catalogo = set()
    for chave in _walk_defs(eventos, "event_type_"):
        catalogo.update(eventos["$defs"][chave]["enum"])

    # `effect_class` — 09 secao 4.0. A tabela e uma SEGUNDA lista dos mesmos 32
    # tipos, entao a cobertura exata e verificada aqui: sem isso ela divergiria
    # do catalogo em silencio, que e a classe de defeito que o proprio
    # `effect_class` existe para fechar.
    registro = (eventos.get("x-aurora-registry") or {})
    classes = registro.get("effect_class") or {}
    validos = set(registro.get("effect_class_values") or [])
    faltando = sorted(catalogo - set(classes))
    sobrando = sorted(set(classes) - catalogo)
    fora = sorted({v for v in classes.values() if v not in validos})
    if faltando or sobrando or fora:
        partes = []
        if faltando:
            partes.append(f"sem effect_class: {faltando}")
        if sobrando:
            partes.append(f"effect_class para tipo fora do catalogo: {sobrando}")
        if fora:
            partes.append(f"valor de effect_class fora do conjunto: {fora}")
        raise ContractError("contracts/events.schema.yaml: " + "; ".join(partes))

    state_effect = {n for n, c in classes.items() if c == "state_effect"}

    flags = {}
    for caminho in sorted((REPO_ROOT / "domains").glob("*/flags.yaml")):
        dados = parse_yaml(caminho) or {}
        for flag in dados.get("flags") or []:
            flags[flag["name"]] = flag

    fatos = set()
    for exemplo in contracts["ground_truth"].get("examples") or []:
        for fato in exemplo.get("facts") or []:
            fatos.add(fato["fact_id"])

    objetivos = set()
    for exemplo in contracts["objectives"].get("examples") or []:
        objetivos.update((exemplo.get("objectives") or {}).keys())

    injects = set()
    opcoes = set()
    for doc in contracts["scenario"].get("x-aurora-document-examples") or []:
        for inject in (doc.get("instance") or {}).get("injects") or []:
            injects.add(inject["id"])
            ponto = inject.get("decision_point") or {}
            for opcao in ponto.get("options") or []:
                opcoes.add(opcao["id"])

    return {
        "event_catalog": catalogo,
        "event_catalog_state_effect": state_effect,
        "adapter_flags": set(flags),
        "pack_facts": fatos,
        "pack_objectives": objetivos,
        "pack_injects": injects,
        "pack_decision_options": opcoes,
        "_flag_specs": flags,
    }


# ---------------------------------------------------------------------------
# Camada 2 — caminhada schema x instancia para colher as anotacoes
# ---------------------------------------------------------------------------


class AuroraChecker:
    """Aplica as anotacoes `x-aurora-*` percorrendo schema e instancia juntos.

    A caminhada acompanha os dois porque a anotacao vive no schema e o valor a
    verificar vive na instancia. Em `oneOf`/`anyOf` desce apenas pelos ramos que
    a instancia de fato satisfaz — descer por todos produziria violacao vinda de
    um ramo que nao e o da instancia.
    """

    def __init__(self, registries: dict, docs: dict):
        self.reg = registries
        self.docs = docs  # $id -> schema
        self.violations: list[tuple[str, str]] = []
        self._unique: dict[str, dict] = {}

    # -- localizacao no schema ----------------------------------------------
    #
    # A caminhada carrega (doc_id, ponteiro) em vez do no solto. E o que
    # permite validar um ramo por `{"$ref": doc_id + ponteiro}`, com o registry
    # resolvendo os `#/$defs/...` internos contra o DOCUMENTO certo. Validar o
    # no resolvido isoladamente quebra toda recursao — foi assim que a checagem
    # de `predicate` deixou de disparar em silencio.

    def _no(self, doc_id: str, ponteiro: str):
        no = self.docs.get(doc_id, {})
        for parte in [p for p in ponteiro.split("/") if p]:
            parte = parte.replace("~1", "/").replace("~0", "~")
            if isinstance(no, dict):
                no = no.get(parte, {})
            elif isinstance(no, list) and parte.isdigit() and int(parte) < len(no):
                # `oneOf/0`, `allOf/2`: segmento de indice. Sem isto a
                # caminhada morre em todo combinador, em silencio — e silencio
                # aqui significa anotacao que nunca dispara.
                no = no[int(parte)]
            else:
                no = {}
        return no

    def _split_ref(self, ref: str, doc_id: str) -> tuple[str, str]:
        if ref.startswith("#"):
            return doc_id, ref[1:]
        base, _, ponteiro = ref.partition("#")
        return base, ponteiro

    def _valida(self, doc_id: str, ponteiro: str, instancia) -> bool:
        try:
            alvo = {"$ref": f"{doc_id}#{ponteiro}"} if ponteiro else {"$ref": doc_id}
            return Draft202012Validator(alvo, registry=self._registry).is_valid(instancia)
        except Exception:
            return False

    # -- caminhada -----------------------------------------------------------

    def check(self, doc_id: str, ponteiro: str | None, instancia, registry) -> list:
        self.violations = []
        self._unique = {}
        self._registry = registry
        self._walk(doc_id, (ponteiro or "").lstrip("#"), instancia, "$")
        return self.violations

    def _walk(self, doc_id: str, ponteiro: str, instancia, ipath: str) -> None:
        schema = self._no(doc_id, ponteiro)
        if not isinstance(schema, dict):
            return

        if "$ref" in schema:
            novo_id, novo_ptr = self._split_ref(schema["$ref"], doc_id)
            self._walk(novo_id, novo_ptr, instancia, ipath)
            # As demais chaves de um no com $ref continuam valendo em 2020-12.

        self._apply(schema, instancia, f"{doc_id}#{ponteiro}", ipath)

        for i, _ in enumerate(schema.get("allOf") or []):
            self._walk(doc_id, f"{ponteiro}/allOf/{i}", instancia, ipath)

        for chave in ("oneOf", "anyOf"):
            for i, _ in enumerate(schema.get(chave) or []):
                sub = f"{ponteiro}/{chave}/{i}"
                if self._valida(doc_id, sub, instancia):
                    self._walk(doc_id, sub, instancia, ipath)

        if "if" in schema:
            ramo = "then" if self._valida(doc_id, f"{ponteiro}/if", instancia) else "else"
            if ramo in schema:
                self._walk(doc_id, f"{ponteiro}/{ramo}", instancia, ipath)

        if isinstance(instancia, dict):
            props = schema.get("properties") or {}
            for chave, valor in instancia.items():
                if chave in props:
                    self._walk(
                        doc_id, f"{ponteiro}/properties/{_esc(chave)}", valor,
                        f"{ipath}.{chave}",
                    )
                elif isinstance(schema.get("additionalProperties"), dict):
                    self._walk(
                        doc_id, f"{ponteiro}/additionalProperties", valor,
                        f"{ipath}.{chave}",
                    )
            if isinstance(schema.get("propertyNames"), dict):
                for chave in instancia:
                    self._apply(
                        schema["propertyNames"], chave,
                        f"{doc_id}#{ponteiro}/propertyNames",
                        f"{ipath}.<chave:{chave}>",
                    )

        if isinstance(instancia, list) and isinstance(schema.get("items"), dict):
            for i, item in enumerate(instancia):
                self._walk(doc_id, f"{ponteiro}/items", item, f"{ipath}[{i}]")

    # -- as anotacoes --------------------------------------------------------

    def _apply(self, schema: dict, valor, spath: str, ipath: str) -> None:
        registro = schema.get("x-aurora-ref")
        if registro and isinstance(valor, str):
            conhecidos = self.reg.get(registro)
            if conhecidos is None:
                self.violations.append(
                    (f"x-aurora-ref:{registro}", f"{ipath}: registro desconhecido")
                )
            elif valor not in conhecidos:
                self.violations.append(
                    (
                        f"x-aurora-ref:{registro}",
                        f"{ipath}: '{valor}' nao existe em {registro}",
                    )
                )

        if schema.get("x-aurora-unique") and isinstance(valor, str):
            visto = self._unique.setdefault(spath, {})
            if valor in visto:
                self.violations.append(
                    ("x-aurora-unique", f"{ipath}: '{valor}' duplicado (ja em {visto[valor]})")
                )
            else:
                visto[valor] = ipath

        if schema.get("x-aurora-effects-match-flag-types") and isinstance(valor, dict):
            for nome, atribuido in valor.items():
                spec = self.reg["_flag_specs"].get(nome)
                if spec is None:
                    continue  # ausencia e problema do x-aurora-ref, nao deste
                erro = _tipo_incompativel(spec, atribuido)
                if erro:
                    self.violations.append(
                        (
                            "x-aurora-effects-match-flag-types",
                            f"{ipath}.{nome}: {erro}",
                        )
                    )


#: "'x' is a required property" — a propriedade que falta, para distinguir dois
#: campos obrigatorios ausentes como DOIS defeitos, e nao um.
_FALTA = re.compile(r"^'(?P<prop>[^']+)' is a required property$")


def sitios_de_defeito(erros) -> set:
    """Agrupa erros de schema por SITIO DE DEFEITO.

    Um defeito costuma produzir mais de um erro: `event_type` fora do catalogo
    falha no `anyOf` do campo e no `enum` da camada ao mesmo tempo. Contar erros
    puniria a fixture correta. Contar SITIOS nao: os dois erros apontam para o
    mesmo caminho de instancia.

    Para `required` o sitio inclui a propriedade ausente, senao dois campos
    obrigatorios faltando no mesmo objeto contariam como um. Foi assim que
    `clock_multiplier` — exigido por 00 secao 5.6 e ausente do `required` ate o
    H2 da segunda auditoria — pode ser acrescentado sem que nenhuma das sete
    fixtures do envelope reprovasse: cada uma passou a carregar DOIS defeitos e
    continuou sendo recusada.
    """
    sitios = set()
    for e in erros:
        prop = None
        if e.validator == "required":
            m = _FALTA.match(e.message)
            prop = m.group("prop") if m else e.message
        sitios.add((tuple(str(p) for p in e.absolute_path), prop))
    return sitios


def _esc(chave: str) -> str:
    """Escapa `~` e `/` num segmento de JSON Pointer (RFC 6901)."""
    return chave.replace("~", "~0").replace("/", "~1")


def _tipo_incompativel(spec: dict, valor) -> str | None:
    tipo = spec.get("type")
    if tipo == "boolean":
        return None if isinstance(valor, bool) else f"flag booleana recebeu {type(valor).__name__}"
    if tipo == "number":
        # bool e subclasse de int em Python; sem esta ordem, `true` passaria
        # por numero.
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return f"flag numerica recebeu {type(valor).__name__}"
        minimo, maximo = spec.get("min"), spec.get("max")
        if minimo is not None and valor < minimo:
            return f"{valor} abaixo do minimo {minimo}"
        if isinstance(maximo, (int, float)) and valor > maximo:
            return f"{valor} acima do maximo {maximo}"
        return None
    if tipo == "enum":
        valores = spec.get("values") or []
        if not isinstance(valor, str) or valor not in valores:
            return f"'{valor}' fora de {valores}"
    return None


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # Diretorio alternativo de contratos: usado por
    # scripts/check_contract_examples_probes.py para rodar contra copias com
    # defeito plantado. Um executor que so roda contra a arvore boa nunca prova
    # que reprova.
    raiz = Path(argv[0]).resolve() if argv else CONTRACTS
    caminhos = sorted(raiz.glob("*.yaml"))
    if not caminhos:
        print(f"ERRO: nenhum contrato em {raiz}", file=sys.stderr)
        return 2

    contratos, por_id = {}, {}
    for caminho in caminhos:
        schema = parse_yaml(caminho)
        nome = schema.get("x-aurora-contract") or caminho.stem
        contratos[nome] = schema
        if "$id" in schema:
            por_id[schema["$id"]] = schema

    registry = Registry().with_resources(
        [(id_, Resource.from_contents(s)) for id_, s in sorted(por_id.items())]
    )
    # Erro de contrato — cobertura de `effect_class`, por exemplo — sai com a
    # mesma mensagem limpa e o mesmo rc=1 de uma fixture reprovada. Traceback
    # daria rc=1 tambem, mas `expect_fail` exige mensagem que localize o
    # problema: deteccao sem localizacao nao permite intervir.
    try:
        registros = build_registries(contratos)
    except ContractError as exc:
        print(f"\nFALHAS: 1\n\n  {exc}\n", file=sys.stderr)
        return 1

    falhas = []
    positivos = negativos = 0

    for caminho in caminhos:
        schema = parse_yaml(caminho)
        fonte = rel(caminho)
        nome = schema.get("x-aurora-contract") or caminho.stem
        base = schema.get("$id", "")
        checker = AuroraChecker(registros, por_id)

        def validador_para(ponteiro: str | None):
            alvo = {"$ref": f"{base}{ponteiro}"} if ponteiro else schema
            return Draft202012Validator(alvo, registry=registry)

        # -- positivos -------------------------------------------------------
        casos = [(None, ex) for ex in (schema.get("examples") or [])]
        for doc in schema.get("x-aurora-document-examples") or []:
            casos.append((doc.get("pointer"), doc.get("instance")))

        for i, (ponteiro, instancia) in enumerate(casos):
            positivos += 1
            erros = sorted(validador_para(ponteiro).iter_errors(instancia), key=str)
            if erros:
                falhas.append(
                    f"{fonte}: exemplo POSITIVO #{i} deveria validar e nao valida\n"
                    f"    {erros[0].json_path}: {erros[0].message}"
                )
                continue
            viola = checker.check(base, ponteiro, instancia, registry)
            if viola:
                regra, detalhe = viola[0]
                falhas.append(
                    f"{fonte}: exemplo POSITIVO #{i} viola {regra}\n    {detalhe}"
                )

        # -- negativos -------------------------------------------------------
        for i, caso in enumerate(schema.get("x-aurora-invalid-examples") or []):
            negativos += 1
            motivo = caso.get("reason", "<sem reason>")
            declarado = caso.get("rejected_by")
            instancia = caso.get("instance")
            ponteiro = caso.get("pointer")
            rotulo = f"{fonte}: exemplo NEGATIVO #{i} ({motivo})"

            if declarado is None:
                falhas.append(f"{rotulo}\n    sem `rejected_by`: nao declara quem recusa")
                continue

            recusa_schema = not validador_para(ponteiro).is_valid(instancia)
            viola = (
                []
                if recusa_schema
                else checker.check(base, ponteiro, instancia, registry)
            )
            regras = {r for r, _ in viola}

            if declarado == "schema":
                if not recusa_schema:
                    extra = f"; quem recusou foi {sorted(regras)}" if regras else ""
                    falhas.append(
                        f"{rotulo}\n    declara `rejected_by: schema` "
                        f"mas o schema ACEITA a instancia{extra}"
                    )
                else:
                    # UM defeito por fixture, tambem do lado do schema. A regra
                    # de isolamento existia so para as fixtures x-aurora; sem
                    # ela aqui, uma instancia com dois defeitos e recusada e
                    # passa, provando qualquer um dos dois — ou nenhum, se o que
                    # ela nomeia for removido do contrato.
                    sitios = sitios_de_defeito(validador_para(ponteiro).iter_errors(instancia))
                    if len(sitios) > 1:
                        detalhe = ", ".join(
                            f"{'/'.join(c) or '<raiz>'}{f' [{p} ausente]' if p else ''}"
                            for c, p in sorted(sitios, key=lambda s: (s[0], s[1] or ""))
                        )
                        falhas.append(
                            f"{rotulo}\n    recusada por {len(sitios)} defeitos distintos, "
                            f"esperado 1: {detalhe}"
                        )
            elif declarado.startswith("x-aurora"):
                if recusa_schema:
                    falhas.append(
                        f"{rotulo}\n    declara `rejected_by: {declarado}` mas o SCHEMA "
                        f"ja recusa: a fixture nao isola a regra que diz provar"
                    )
                elif declarado not in regras:
                    falhas.append(
                        f"{rotulo}\n    declara `rejected_by: {declarado}` e essa regra "
                        f"NAO disparou (dispararam: {sorted(regras) or 'nenhuma'})"
                    )
                elif regras != {declarado}:
                    # Uma instancia que viola mais de uma regra nao isola a que
                    # diz provar: ela passaria mesmo se a regra declarada fosse
                    # removida do executor.
                    falhas.append(
                        f"{rotulo}\n    declara `rejected_by: {declarado}` mas viola "
                        f"tambem {sorted(regras - {declarado})}: a fixture nao isola "
                        f"um defeito"
                    )
            else:
                falhas.append(f"{rotulo}\n    `rejected_by: {declarado}` desconhecido")

    print(f"Contratos: {len(caminhos)}")
    print(f"Exemplos positivos executados: {positivos}")
    print(f"Exemplos negativos executados: {negativos}")

    if falhas:
        print(f"\nFALHAS: {len(falhas)}\n", file=sys.stderr)
        for f in falhas:
            print(f"  {f}\n", file=sys.stderr)
        return 1

    print("\nTodos os exemplos positivos validam.")
    print("Todos os exemplos negativos sao recusados, cada um pela camada que declara.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
