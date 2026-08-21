#!/usr/bin/env python3
"""Executa os exemplos positivos e negativos dos contratos de `contracts/`.

Item 1 da DoD da Fase 1: *"os contratos existem e VALIDAM exemplos
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

# AS REGRAS `x-aurora-*` VIVEM NO NUCLEO, e este script passou a CHAMA-LAS.
#
# Decisao §1.4 do checkpoint da Fase 2: o loader de pack e o segundo consumidor
# delas, e duas implementacoes da mesma regra produziriam o gate divergindo do
# loader de producao — cada um aceitando um pack que o outro recusa.
#
# Este import e a razao de este script nao ser um dos seis verificadores: ele ja
# dependia de `jsonschema`, e agora depende tambem da aplicacao. Roda no job
# `contratos`, que instala; os seis de `tools/` seguem stdlib puro.
from range_core.engine.loader.contract_rules import (  # noqa: E402
    AuroraChecker,
    ContractRuleError,
    build_registries,
)
from range_core.rubrics.library import (  # noqa: E402
    RUBRICS_DIR,
    RubricLibraryError,
    load_library,
)

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
        # As flags do adapter sao lidas AQUI e passadas como dado: o nucleo
        # nao vai buscar arquivo em `domains/`.
        flags_do_adapter = {}
        for caminho_flags in sorted((REPO_ROOT / "domains").glob("*/flags.yaml")):
            for flag in (parse_yaml(caminho_flags) or {}).get("flags") or []:
                flags_do_adapter[flag["name"]] = flag
        # A biblioteca de rubricas e do CORE (00 secao 5.8), e nao de dominio:
        # le-la aqui nao atravessa a fronteira que as flags atravessariam. Vem
        # da arvore real, e nao dos exemplos, pelo mesmo motivo que
        # `event_catalog`: e a fonte canonica, no mesmo commit.
        biblioteca = load_library()
        registros = build_registries(contratos, flags_do_adapter, biblioteca)
    except (ContractError, ContractRuleError, RubricLibraryError) as exc:
        print(f"\nFALHAS: 1\n\n  {exc}\n", file=sys.stderr)
        return 1

    falhas = []
    positivos = negativos = instancias = 0

    # -----------------------------------------------------------------------
    # INSTANCIAS REAIS — `domains/<adapter>/flags.yaml`.
    #
    # 01 secao 5.2 diz, literalmente, "domains/<adapter>/flags.yaml, VALIDADO
    # CONTRA contracts/state_flags.schema.yaml". Ninguem o validava: este script
    # abria o arquivo so para colher nomes e tipos para o registro.
    #
    # Era o unico artefato real desta fase governado por contrato, e o unico sem
    # validacao — `category: disponibilidade` ali sairia rc=0 nos quatro jobs. E
    # ele e entrada do codegen e do `x-aurora-effects-match-flag-types`, entao o
    # erro se propagaria para as constantes e para a checagem de effects.
    # H1 da terceira auditoria.
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # DUAS COPIAS DA MESMA NORMA, CRUZADAS.
    #
    # `evidence.schema.yaml` guarda as faixas sinteticas de 05 secao 3, e
    # `tools/check_synthetic_data.py` guarda as suas proprias — e e ele quem de
    # fato varre os arquivos de dado. As duas divergiram DUAS VEZES enquanto o
    # comentario do contrato afirmava alinhamento (M2 da segunda auditoria, L3
    # da quinta).
    #
    # "Alinhado com X" e afirmacao sobre OUTRO arquivo. Ou existe algo que a
    # verifica, ou ela envelhece sozinha — que foi exatamente o que aconteceu.
    # Aqui ela passa a ser verificada.
    # -----------------------------------------------------------------------
    ev = contratos.get("evidence")
    if ev is not None:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import check_synthetic_data as csd  # noqa: E402

        declarados = {
            s.lstrip(".")
            for s in (ev.get("x-aurora-security-constraints") or {}).get(
                "allowed_domain_suffixes"
            ) or []
        }
        aplicados = set(csd.RESERVED_TLDS) | set(csd.RESERVED_DOMAINS)
        if declarados != aplicados:
            falhas.append(
                "contracts/evidence.schema.yaml x tools/check_synthetic_data.py: "
                "faixas de dominio divergentes.\n"
                f"    so no contrato: {sorted(declarados - aplicados) or 'nenhum'}\n"
                f"    so no verificador: {sorted(aplicados - declarados) or 'nenhum'}"
            )

    flags_schema = contratos.get("state_flags")
    if flags_schema is not None:
        validador_flags = Draft202012Validator(flags_schema, registry=registry)
        arquivos = sorted((REPO_ROOT / "domains").glob("*/flags.yaml"))
        if not arquivos:
            falhas.append("domains/*/flags.yaml: nenhum encontrado")
        for caminho in arquivos:
            instancias += 1
            erros = sorted(validador_flags.iter_errors(parse_yaml(caminho) or {}), key=str)
            for e in erros:
                falhas.append(
                    f"{rel(caminho)}: nao valida contra state_flags.schema.yaml\n"
                    f"    {e.json_path}: {e.message}"
                )

    # INSTANCIAS REAIS — `range-core/rubrics/*.yaml`.
    #
    # Mesmo argumento que ja traz `domains/*/flags.yaml` para ca: contrato
    # validado so contra as proprias fixtures prova consistencia interna e nao
    # prova fidelidade. A biblioteca e o artefato que o pack referencia, e se
    # ela nao valida, `required_rubrics` casa um id cujo conteudo o contrato
    # recusaria.
    #
    # `load_library` ja rodou acima e passaria por identidade e niveis; o que
    # falta e a FORMA, que e do contrato. As duas camadas, uma vez cada.
    rubricas_schema = contratos.get("rubrics")
    if rubricas_schema is not None:
        validador_rubricas = Draft202012Validator(rubricas_schema, registry=registry)
        arquivos = sorted(RUBRICS_DIR.glob("*.yaml"))
        if not arquivos:
            falhas.append("range-core/rubrics/*.yaml: nenhuma rubrica encontrada")
        for caminho in arquivos:
            instancias += 1
            erros = sorted(
                validador_rubricas.iter_errors(parse_yaml(caminho) or {}), key=str
            )
            for e in erros:
                falhas.append(
                    f"{rel(caminho)}: nao valida contra rubrics.schema.yaml\n"
                    f"    {e.json_path}: {e.message}"
                )

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
                elif len(viola) > 1:
                    # UMA violacao, nao uma regra violada. Agrupar por NOME DE
                    # REGRA deixava passar a fixture com dois `next` pendurados,
                    # que viola `pack_injects` duas vezes: ela nomeia um defeito
                    # e carrega dois, e continuaria sendo recusada se o defeito
                    # nomeado fosse corrigido. Mesmo criterio do lado do schema,
                    # onde o sitio de defeito ja incluia a propriedade ausente.
                    detalhe = "; ".join(d for _, d in viola)
                    falhas.append(
                        f"{rotulo}\n    viola `{declarado}` {len(viola)} vezes, "
                        f"esperado 1: {detalhe}"
                    )
            else:
                falhas.append(f"{rotulo}\n    `rejected_by: {declarado}` desconhecido")

    print(f"Contratos: {len(caminhos)}")
    print(f"Exemplos positivos executados: {positivos}")
    print(f"Exemplos negativos executados: {negativos}")
    print(f"Instancias reais validadas: {instancias}")

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
