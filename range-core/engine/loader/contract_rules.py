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
from referencing.exceptions import Unresolvable


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


def _injects_and_options(documento: dict) -> tuple[set, set]:
    """`(ids de inject, ids de opcao)` de um documento no formato `injects.yaml`.

    Serve aos DOIS chamadores — o executor de fixtures, que passa a instancia de
    um exemplo, e o loader, que passa o `injects.yaml` do pack. Sao a mesma forma
    de documento, e le-la duas vezes seria a D4 dentro do modulo que existe para
    desfazer a D4.
    """
    injects, opcoes = set(), set()
    for inject in (documento or {}).get("injects") or []:
        injects.add(inject["id"])
        ponto = inject.get("decision_point") or {}
        for opcao in ponto.get("options") or []:
            opcoes.add(opcao["id"])
    return injects, opcoes


def _base_registries(contracts: dict, adapter_flags: dict) -> dict:
    """A metade que NAO depende de pacote: catalogo de eventos e flags do adapter.

    Existe porque os dois chamadores divergem so na outra metade. O executor de
    fixtures resolve `pack_*` contra os exemplos dos contratos; o loader, contra
    o pack de verdade. O catalogo e as flags sao os mesmos nos dois, e escreve-los
    duas vezes seria a divergencia que a §1.4 do checkpoint fechou.
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

    return {
        "event_catalog": catalogo,
        "event_catalog_state_effect": state_effect,
        "adapter_flags": set(flags),
        "_flag_specs": flags,
    }


def build_registries(contracts: dict, adapter_flags: dict) -> dict:
    """Monta os registros contra os quais `x-aurora-ref` resolve, PARA AS FIXTURES.

    `adapter_flags` chega como DADO — `nome -> spec` —, e nao por leitura de
    `domains/*/flags.yaml`. O nucleo nao vai buscar arquivo de dominio: quem
    carrega o adapter o entrega, do mesmo jeito que `Declarations` recebe os
    defaults. Nao seria violacao do invariante 1, que e sobre IMPORT, mas seria
    o acoplamento que ele existe para evitar, entrando por outra porta.

    `event_catalog` vem da fonte canonica real. Os
    registros `pack_*` vem dos EXEMPLOS POSITIVOS dos proprios contratos: os
    exemplos formam um mini-pacote sintetico, e e contra ele que as referencias
    cruzadas de fixture resolvem.

    A frase seguinte era *"nenhum pacote de cenario existe antes da Fase 7, e
    inventar um so para o teste seria dado nao versionado guiando verificacao"*.
    Ela envelheceu no commit em que o loader nasceu: existe pack — o fixture
    minimo da Fase 2 —, e o loader resolve contra ELE, por
    `build_pack_registries`. O argumento continua valendo para as FIXTURES DOS
    CONTRATOS, que sao o que esta funcao serve: elas nao podem depender de um
    pacote que vive fora de `contracts/`, senao o gate do CI passaria a julgar
    contrato contra dado de outra arvore.
    """
    registros = _base_registries(contracts, adapter_flags)

    fatos = set()
    for exemplo in contracts["ground_truth"].get("examples") or []:
        for fato in exemplo.get("facts") or []:
            fatos.add(fato["fact_id"])

    objetivos = set()
    for exemplo in contracts["objectives"].get("examples") or []:
        objetivos.update((exemplo.get("objectives") or {}).keys())

    injects, opcoes = set(), set()
    for doc in contracts["scenario"].get("x-aurora-document-examples") or []:
        do_exemplo, opcoes_do_exemplo = _injects_and_options(doc.get("instance") or {})
        injects |= do_exemplo
        opcoes |= opcoes_do_exemplo

    registros.update(
        {
            "pack_facts": fatos,
            "pack_objectives": objetivos,
            "pack_injects": injects,
            "pack_decision_options": opcoes,
        }
    )
    return registros


def build_pack_registries(
    contracts: dict,
    adapter_flags: dict,
    *,
    injects_document: dict | None = None,
    objectives_document: dict | None = None,
    ground_truth_document: dict | None = None,
) -> dict:
    """Os mesmos registros, resolvendo `pack_*` contra UM PACK de verdade.

    E a diferenca inteira entre o executor de fixtures e o loader: as regras sao
    as mesmas, os documentos e que sao outros. Uma implementacao, dois
    chamadores — §1.4 do checkpoint —, e aqui isso fica visivel: o que diverge
    esta nos argumentos, nao no codigo da regra.

    DOCUMENTO AUSENTE VIRA REGISTRO VAZIO, e isso e recusa e nao permissao.
    Pack sem `objectives.yaml` resolve `pack_objectives` contra conjunto vazio,
    entao um inject que cite objetivo e RECUSADO — que e o comportamento certo:
    o objetivo citado de fato nao existe. A alternativa, pular a regra quando o
    arquivo falta, deixaria passar exatamente o erro de digitacao que a
    `04_SCENARIO_SCHEMA.md` §6.2 chama de falha mais cara possivel.
    """
    registros = _base_registries(contracts, adapter_flags)

    injects, opcoes = _injects_and_options(injects_document or {})

    fatos = set()
    for fato in (ground_truth_document or {}).get("facts") or []:
        fatos.add(fato["fact_id"])

    registros.update(
        {
            "pack_facts": fatos,
            "pack_objectives": set(((objectives_document or {}).get("objectives") or {}).keys()),
            "pack_injects": injects,
            "pack_decision_options": opcoes,
        }
    )
    return registros


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
        """A instancia satisfaz o ramo apontado? Usado para decidir a descida.

        O QUE E TOLERADO, E SO ISSO — P2-12
        ------------------------------------
        `Unresolvable` cobre a familia de falhas de resolucao de `$ref`:
        documento ausente do registry, ponteiro para lugar nenhum, ancora
        invalida. Nelas a resposta honesta e "este ramo nao se aplica", e a
        descida para. O defeito nao passa em silencio: a camada 1 valida a
        MESMA instancia contra o MESMO `$ref` e levanta alto, porque nao captura
        nada.

        `jsonschema` embrulha o erro de `referencing` em
        `_WrappedReferencingError`, que **herda de `Unresolvable`** — conferido
        na versao pinada, e nao suposto. Se um dia deixar de herdar, o teste
        `test_contract_rules.RefIrresolvivel` fica vermelho em vez de a
        tolerancia sumir sem aviso.

        O QUE DEIXOU DE SER TOLERADO, e por que isto e uma pendencia e nao um
        detalhe
        --------------------------------------------------------------------
        Era `except Exception: return False`. Erro de PROGRAMACAO — nome
        inexistente, assinatura trocada, tipo errado — virava `False`, e `False`
        aqui significa "o ramo nao se aplica". A regra deixava de ser aplicada e
        o sintoma aparecia tres camadas adiante, como *"a regra declarada nao
        disparou"*, apontando para as fixtures em vez de para a causa.

        Nao e hipotese: foi o unico defeito do movimento da §1.4 do checkpoint —
        o modulo novo nao importava `Draft202012Validator`, o `NameError` foi
        engolido, e quatro fixtures negativas reprovaram pelo motivo errado.

        Erro de programacao agora SOBE. Um loader que recusa pack por regra que
        silenciosamente nao correu recusa — ou aceita — o pack errado, e nada
        acusa.
        """
        alvo = {"$ref": f"{doc_id}#{ponteiro}"} if ponteiro else {"$ref": doc_id}
        try:
            return Draft202012Validator(alvo, registry=self._registry).is_valid(instancia)
        except Unresolvable:
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
