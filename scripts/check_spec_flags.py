#!/usr/bin/env python3
"""Toda flag citada em `docs/spec/` existe no adapter, ou tem fase declarada.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
`01_ARCHITECTURE.md` §5.4: *"nenhum servico le ou escreve flag nao declarada"*, e
o loader de pack recusa boot com flag desconhecida desde a Fase 2. As duas
garantias valem para o CODIGO e para o PACK.

**A spec nao passava por nenhuma delas.** `07_IMPLEMENTATION_PHASES.md` cobra, no
item 2 da DoD da Fase 3, que uma flag de leitura-apenas de notas bloqueie o POST
— e essa flag NAO EXISTE em `domains/academus/flags.yaml`. Item de DoD
insatisfazivel por construcao, da familia do E2 da Fase 2, e invisivel porque
`scripts/check_spec_examples.py` valida BLOCOS YAML e a DoD e markdown.

Mesma familia do que o registro da Fase 2 anotou sobre o catalogo de eventos: a
tabela de `09` §4.1 e markdown, e o CI nao a cruza com o contrato. A lista de
lugares onde a spec afirma algo que nenhuma maquina le e o que esta checagem
comeca a fechar.

**Primeira execucao: seis divergencias**, e so uma era conhecida.

AS TRES CLASSES, E A TERCEIRA E O PONTO
----------------------------------------
- **declarada** — existe em `domains/<adapter>/flags.yaml`. Nada a fazer.
- **citada e nao declarada** — reprova. E o defeito.
- **citada para servico que ainda nao existe** — passa, se estiver em
  `domains/flags_pendentes.yaml` com a fase que a trara.

A terceira classe existe porque `02_DOMAIN_ACADEMUS.md` §7 descreve o
`federated-identity-simulator` e o `mec-gateway` junto dos injects de cada um, e
os dois sao entregaveis da Fase 11. Declarar aquelas flags agora nao seria
inofensivo: elas virariam painel no wallboard, que `01` §5.3 renderiza POR
CONVENCAO a partir de `wallboard_group`, e a sala veria indicador de servico que
nao existe.

A LISTA ENVELHECE NAS DUAS DIRECOES, e a checagem cobra as duas: entrada ja
declarada reprova (sobrou), entrada que a spec deixou de citar tambem (mente).
Sem isso ela vira o que toda lista de excecao vira — permissao permanente que
ninguem rele.

O QUE ELA NAO FAZ
-----------------
Nao exige que toda flag DECLARADA seja citada na spec: a maioria nao e, e nao
deve ser. A direcao que importa e a que produz item de DoD impossivel.

Stdlib pura, com o parser estrito de `tools/` — o mesmo que os seis verificadores
usam. Roda no job `arquitetura`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

SPEC_DIR = REPO_ROOT / "docs" / "spec"
DOMAINS = REPO_ROOT / "domains"

#: A LISTA DE PENDENTES VEM DE ARQUIVO DE DADO, e nao daqui.
#:
#: Escrever `<adapter>.<nome>` de flag NAO DECLARADA dentro de um `.py` e a
#: assinatura exata do erro de digitacao que `tools/check_contract_literals.py`
#: recusa — e ele recusaria esta lista. O hook de arquitetura barrou a primeira
#: versao por isso, e estava certo: nome de flag em lista de excecao e DADO sobre
#: flags, nao codigo.
PENDENTES_PATH = DOMAINS / "flags_pendentes.yaml"

RULE = "flags citadas na spec x declaradas no adapter"


def adapters() -> list[str]:
    """Os adapters vem do disco, e nao de constante embutida.

    Mesma escolha de `tools/check_contract_literals.py`: a autoridade sobre o que
    e um adapter e `domains/`, e adapter novo passa a ser varrido sem que ninguem
    se lembre de acrescenta-lo aqui.
    """
    return sorted(p.parent.name for p in DOMAINS.glob("*/flags.yaml"))


def declaradas() -> set[str]:
    nomes: set[str] = set()
    for caminho in sorted(DOMAINS.glob("*/flags.yaml")):
        for flag in (parse_yaml(caminho) or {}).get("flags") or []:
            nomes.add(flag["name"])
    return nomes


def pendentes(caminho: Path | None = None) -> dict[str, str]:
    """`flag -> quem a trara`, do arquivo de dado."""
    caminho = PENDENTES_PATH if caminho is None else caminho
    if not caminho.is_file():
        return {}
    documento = parse_yaml(caminho) or {}
    return {
        entrada["name"]: entrada.get("quem_traz", "<sem dono declarado>")
        for entrada in documento.get("pendentes") or []
    }


def citadas(spec_dir: Path, nomes_de_adapter: list[str]) -> dict[str, list[str]]:
    """`flag -> onde foi citada`, varrendo `docs/spec/`.

    O padrao e o mesmo de `check_contract_literals.py`: `<adapter>.<nome>` com
    adapter existente. Sobre-inclusivo de proposito — pega a citacao em prosa, em
    tabela e em bloco de exemplo, e a DoD e prosa.
    """
    if not nomes_de_adapter:
        return {}
    padrao = re.compile(r"\b(?:" + "|".join(nomes_de_adapter) + r")\.[a-z_][a-z0-9_]*")
    achadas: dict[str, list[str]] = {}
    for doc in sorted(spec_dir.glob("*.md")):
        for numero, linha in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for nome in padrao.findall(linha):
                achadas.setdefault(nome, []).append(f"{doc.name}:{numero}")
    return achadas


def verifica(
    achadas: dict[str, list[str]],
    ja_declaradas: set[str],
    lista_pendente: dict[str, str],
) -> list[str]:
    """As tres asserções.

    Recebe tudo por parametro para a prova negativa poder injetar cenarios que
    nao existem na arvore — sem plantar flag em `domains/` nem editar a spec.
    """
    problemas: list[str] = []

    for nome in sorted(achadas):
        if nome in ja_declaradas or nome in lista_pendente:
            continue
        problemas.append(
            f"{nome}: citada em {', '.join(achadas[nome])} e NAO declarada.\n"
            "    `01` §5.4 diz que nenhum servico le ou escreve flag nao "
            "declarada, e o loader recusa boot com flag desconhecida. Flag que so "
            "existe na spec produz item de DoD insatisfazivel por construcao — a "
            "familia do E2 da Fase 2.\n"
            "    Declare-a em `domains/<adapter>/flags.yaml`, ou registre-a em "
            "`domains/flags_pendentes.yaml` com a fase que a trara."
        )

    for nome, dono in sorted(lista_pendente.items()):
        if nome in ja_declaradas:
            problemas.append(
                f"{nome}: pendente por «{dono}» e JA declarada no adapter. "
                "A entrada sobrou — remova-a de `flags_pendentes.yaml`.\n"
                "    Lista de excecao que sobra e permissao que ninguem pediu."
            )
        elif nome not in achadas:
            problemas.append(
                f"{nome}: pendente por «{dono}» e nao e citada em `docs/spec/` "
                "por documento nenhum.\n"
                "    A lista afirma sobre a spec algo que a spec nao diz."
            )

    return problemas


def main(argv: list[str] | None = None) -> int:
    nomes_de_adapter = adapters()
    if not nomes_de_adapter:
        print(f"{RULE}: nenhum adapter com `flags.yaml` em {DOMAINS}", file=sys.stderr)
        return 2

    achadas = citadas(SPEC_DIR, nomes_de_adapter)
    lista_pendente = pendentes()
    problemas = verifica(achadas, declaradas(), lista_pendente)

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(achadas)} flags citadas em `docs/spec/` — "
        f"{len(achadas) - len(lista_pendente)} declaradas no adapter e "
        f"{len(lista_pendente)} pendentes, cada uma com a fase que a trara."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
