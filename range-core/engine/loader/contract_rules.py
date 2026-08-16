"""As regras `x-aurora-*` — implementacao unica, dois chamadores.

AUTORIDADE
----------
`contracts/README.md`, secao "Extensoes `x-aurora-*`"; decisao §1.4 do
checkpoint da Fase 2.

POR QUE ESTE MODULO EXISTE
--------------------------
Estas regras expressam integridade referencial ENTRE arquivos — coisa que
nenhuma linguagem de schema expressa. Um `event_type` com erro de digitacao e
string perfeitamente valida para o JSON Schema; quem o recusa e esta camada.

Ate a Fase 2 elas viviam dentro de `scripts/check_contract_examples.py`, o
executor de fixtures do CI. O loader de pack seria o SEGUNDO a precisar delas, e
reimplementa-las produziria o verificador de CI divergindo do loader de
producao — cada um aceitando um pack que o outro recusa. E a classe que a D4 da
Fase 1 desfez, reaparecendo com outra roupa.

**Uma implementacao, dois chamadores.** `scripts/check_contract_examples.py`
deixou de ser implementacao de referencia e passou a chamar. O loader chama o
mesmo.

O MOVIMENTO VEIO SOZINHO, ANTES DO LOADER
------------------------------------------
Tirar estas linhas de dentro de um gate ativo e ligar um consumidor novo sao
duas mudancas; feitas juntas, dariam um sinal so, e um vermelho nao diria qual
delas quebrou. O gate continua verde depois do movimento, provando que o modulo
faz o que as linhas faziam — e so entao o loader consome.

O QUE MUDOU NA TRAVESSIA, e por que
-----------------------------------
`build_registries` lia `domains/*/flags.yaml` do disco. Aqui as flags do adapter
chegam como DADO. Nao seria violacao do invariante 1, que e sobre import — mas
seria o acoplamento que ele existe para evitar entrando por outra porta, e o
`Declarations` do fold ja tinha resolvido isso do jeito certo.

`ContractError`, de `tools/_common`, virou `ContractRuleError` local: o nucleo
nao importa de `tools/`, que e onde vivem os verificadores stdlib do CI.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator


class ContractRuleError(Exception):
    """Contrato malformado o bastante para as regras nao poderem correr.

    Distinto de "fixture reprovada": aqui o problema e do CONTRATO, e nenhuma
    verificacao subsequente teria significado.
    """


# ---------------------------------------------------------------------------
# Registros consultados pelas anotacoes `x-aurora-ref`
# ---------------------------------------------------------------------------


def _walk_defs(schema: dict, prefix: str) -> list:
    defs = schema.get("$defs") or {}
    return sorted(k for k in defs if k.startswith(prefix))


def build_registries(contracts: dict, adapter_flags: dict) -> dict:
    """Monta os registros contra os quais `x-aurora-ref` resolve.

    `adapter_flags` chega como DADO — `nome -> spec` —, e nao por leitura de
    `domains/*/flags.yaml`. O nucleo nao vai buscar arquivo de dominio: quem
    carrega o adapter o entrega, do mesmo jeito que `Declarations` recebe os
    defaults. Nao seria violacao do invariante 1, que e sobre IMPORT, mas seria
    o acoplamento que ele existe para evitar, entrando por outra porta.

    `event_catalog` vem da fonte canonica real. Os
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
        raise ContractRuleError("contracts/events.schema.yaml: " + "; ".join(partes))

    state_effect = {n for n, c in classes.items() if c == "state_effect"}

    flags = dict(adapter_flags)

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
