#!/usr/bin/env python3
"""Toda regra de `x-aurora-linter-rules` tem mecanismo, ou tem destinatario.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
`contracts/scenario.schema.v2.yaml` declara em `x-aurora-linter-rules` as
validacoes que `04_SCENARIO_SCHEMA.md` §6.2 e §8 poem a cargo do
`range-cli scenario lint`. Ate a peca 3 da Fase 7 aquele registro era uma
**sequencia de sete strings que nenhum codigo lia**.

E ele ja tinha envelhecido, sem que nada acusasse: a ultima entrada descrevia
como obrigacao futura do linter — *"`required_rubrics` deve cobrir toda rubrica
citada em objectives.yaml"* — algo que `objectives.schema.yaml` mecanizou por
`x-aurora-ref: pack_required_rubrics`. Ninguem tinha por que cruzar as duas.

E LITERALMENTE A CLASSE DO M1 DA TERCEIRA AUDITORIA: *"registro ignorado e prosa
marcada como contrato"*. Aquele achado foi sobre `x-aurora-registry.package_files`,
e custou o `_verify_completude` do B1 da Fase 6 para fechar. Este e o mesmo
defeito, no mesmo arquivo, num registro vizinho.

O QUE ELA COBRA, POR ENTRADA
-----------------------------
- `id` presente, nao vazio e UNICO — e por ele que a entrada e citada;
- `rule` presente e nao vazio — o enunciado em prosa, para humano;
- `mecanismo` **ou** `destinatario`. Nunca nenhum dos dois: entrada sem um nem
  outro e exatamente a prosa sem dono que este verificador existe para acabar;
- `destinatario` presente exige `motivo`. Adiar sem dizer por que e a lista de
  excecao que vira permissao permanente — a mesma razao pela qual
  `check_spec_flags.py` cobra a fase de cada pendente;
- `sitio`, quando presente, **existe em `PackSite`**. E a perna que faz o
  registro nao poder virar entrada morta: renomear um sitio derruba o gate em vez
  de deixar a regra apontando para um mecanismo que nao existe mais.

O QUE ELA NAO FAZ, E O LIMITE E REAL
-------------------------------------
Nao cobra a direcao inversa: obrigacao que `04` §8 enuncie e que ninguem tenha
transcrito para o registro continua invisivel. A lista daquela secao e prosa
corrida, e nao ha o que derivar dela sem casar texto — que e o modo de checagem
que este repositorio ja recusou em `tools/check_core_boundary.py`, e pelo mesmo
motivo.

Ela julga se cada entrada TEM dono, e nao se as entradas sao todas as que
deveriam existir. Mesma forma de `check_gate_coverage.py`: *"nao julga se a
classificacao esta CERTA — julga se ela EXISTE"*.

`PackSite` E LIDO POR AST, e nao por import
--------------------------------------------
Importar `range_core` traria `jsonschema`, `yaml` e a biblioteca de rubricas para
dentro de um verificador do job `arquitetura`, que e stdlib pura por desenho
desde a Fase 0. O que se precisa daqui e da lista de nomes de sitio, e ela e
sintatica.

Stdlib pura, com o parser estrito de `tools/`. Roda no job `arquitetura`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

RULE = "P7 - toda regra de x-aurora-linter-rules tem mecanismo ou destinatario"

CONTRATO = REPO_ROOT / "contracts" / "scenario.schema.v2.yaml"
LOADER = REPO_ROOT / "range-core" / "engine" / "loader" / "pack_loader.py"

REGISTRO = "x-aurora-linter-rules"
CLASSE_DE_SITIO = "PackSite"


def sitios_declarados(fonte: Path) -> set[str]:
    """Os VALORES das constantes de `PackSite`, por AST.

    Os valores, e nao os nomes dos atributos: e o valor que viaja em
    `PackError.site`, e e ele que o registro cita. Casar pelo nome do atributo
    deixaria `T_RELATIVE_OUT_OF_ORDER = "outra_coisa"` passar.
    """
    arvore = ast.parse(fonte.read_text(encoding="utf-8"), filename=str(fonte))
    for no in ast.walk(arvore):
        if isinstance(no, ast.ClassDef) and no.name == CLASSE_DE_SITIO:
            return {
                filho.value.value
                for filho in no.body
                if isinstance(filho, ast.Assign)
                and isinstance(filho.value, ast.Constant)
                and isinstance(filho.value.value, str)
            }
    return set()


def verifica(regras: list, sitios: set[str]) -> list[str]:
    """Os problemas, um por linha. Lista vazia significa registro em dia."""
    problemas: list[str] = []
    vistos: dict[str, int] = {}

    if not regras:
        return [
            f"`{REGISTRO}` esta vazio ou ausente em "
            "`contracts/scenario.schema.v2.yaml`.\n"
            "    Ele e a lista das validacoes que `04` §6.2 e §8 poem a cargo do "
            "`range-cli scenario lint`. Vazio, este verificador passa a nao "
            "julgar nada e vira gate verde sobre ausencia."
        ]

    for posicao, entrada in enumerate(regras):
        onde = f"entrada {posicao}"
        if not isinstance(entrada, dict):
            problemas.append(
                f"{onde}: e {type(entrada).__name__}, e nao um mapeamento.\n"
                "    A forma antiga do registro era uma sequencia de strings, e "
                "era justamente ela que nao tinha como carregar dono. Ver o "
                "cabecalho do registro no contrato."
            )
            continue

        identificador = str(entrada.get("id") or "").strip()
        if not identificador:
            problemas.append(f"{onde}: sem `id`. E por ele que a entrada e citada.")
            continue
        onde = f"`{identificador}`"

        if identificador in vistos:
            problemas.append(
                f"{onde}: `id` duplicado — ja usado na entrada {vistos[identificador]}.\n"
                "    Duas entradas com o mesmo id fazem uma delas ser invisivel a "
                "quem a cita."
            )
            continue
        vistos[identificador] = posicao

        if not str(entrada.get("rule") or "").strip():
            problemas.append(
                f"{onde}: sem `rule`. O enunciado em prosa e o que um humano le "
                "para saber o que a regra exige."
            )

        mecanismo = str(entrada.get("mecanismo") or "").strip()
        destinatario = str(entrada.get("destinatario") or "").strip()
        motivo = str(entrada.get("motivo") or "").strip()

        if not mecanismo and not destinatario:
            problemas.append(
                f"{onde}: sem `mecanismo` e sem `destinatario`.\n"
                "    Regra declarada que ninguem executa e ninguem deve e "
                "exatamente a prosa marcada como contrato que este verificador "
                "existe para acabar. Ou aponte onde ela roda, ou declare quem a "
                "trara e por que ainda nao."
            )

        if destinatario and not motivo:
            problemas.append(
                f"{onde}: tem `destinatario` «{destinatario}» e nao tem `motivo`.\n"
                "    Adiamento sem razao escrita e a lista de excecao que vira "
                "permissao permanente. Quando ha tambem `mecanismo`, o `motivo` e "
                "quem diz que METADE da regra ainda falta."
            )

        sitio = str(entrada.get("sitio") or "").strip()
        if sitio and sitio not in sitios:
            problemas.append(
                f"{onde}: `sitio: {sitio!r}` nao existe em "
                f"`{CLASSE_DE_SITIO}` de `range-core/engine/loader/pack_loader.py`.\n"
                f"    Sitios declarados: {sorted(sitios)[:6]}"
                f"{' ...' if len(sitios) > 6 else ''}\n"
                "    Ou o sitio foi renomeado e o registro ficou para tras, ou a "
                "entrada aponta para um mecanismo que nunca existiu. Nos dois "
                "casos a regra deixou de ter dono sem que nada acusasse — que e "
                "o defeito que esta perna fecha."
            )

    return problemas


def regras_do_contrato(caminho: Path = CONTRATO) -> list:
    documento = parse_yaml(caminho)
    return documento.get(REGISTRO) or []


def main(argv: list[str] | None = None) -> int:
    if not CONTRATO.is_file():
        print(f"{RULE}: {CONTRATO} nao existe", file=sys.stderr)
        return 2
    if not LOADER.is_file():
        print(f"{RULE}: {LOADER} nao existe", file=sys.stderr)
        return 2

    regras = regras_do_contrato()
    sitios = sitios_declarados(LOADER)
    if not sitios:
        print(
            f"{RULE}: `{CLASSE_DE_SITIO}` nao foi encontrada em {LOADER}, ou nao "
            "declara sitio nenhum. Sem ela a perna do `sitio` passaria a aceitar "
            "qualquer nome.",
            file=sys.stderr,
        )
        return 2

    problemas = verifica(regras, sitios)
    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    com_mecanismo = sum(1 for r in regras if str(r.get("mecanismo") or "").strip())
    print(
        f"{RULE}: {len(regras)} regras declaradas — {com_mecanismo} com mecanismo "
        f"e {len(regras) - com_mecanismo} com destinatario e motivo."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
