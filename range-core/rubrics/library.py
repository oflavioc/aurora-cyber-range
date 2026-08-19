"""A biblioteca de rubricas BARS do core — carga, identidade e as cinco âncoras.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` secao 2; `00_MASTER_SPEC.md` secao 5.8. Contrato de
forma: `contracts/rubrics.schema.yaml`.

O QUE ESTE MODULO VERIFICA, E POR QUE NAO E O CONTRATO QUE VERIFICA
--------------------------------------------------------------------
O contrato alcanca forma: competencia no conjunto fechado, versao com o `v`,
escala `0-4`, cinco entradas em `anchors`, valores de texto nao vazio. Duas
coisas ficam fora do alcance dele, e as duas estao aqui:

1. **Nome do arquivo x conteudo.** O identificador que `required_rubrics` cita
   e o nome do arquivo, e nao ha campo `id` — ele seria segunda copia e
   divergiria em silencio. Entao a identidade e verificada: o stem tem de ser
   `<competency>.<version>` do proprio conteudo. Sem isto, renomear o arquivo
   troca o id que o pack casa sem que o conteudo mude, e a rubrica errada
   pontua a competencia certa.

2. **As chaves de `anchors` sao exatamente 0..4.** `03` secao 2.3 pede cinco
   ancoras, e a escala e `0-4`: sao os niveis, nao cinco chaves quaisquer. JSON
   Schema nao alcanca isso porque as chaves sao INTEIROS — o bloco normativo de
   `03` secao 2.2 escreve `0:` sem aspas, e `properties`/`required`/
   `propertyNames` so casam nome de propriedade string. `{5,6,7,8,9}` passa no
   contrato e e recusado aqui.

Sem a (2), uma rubrica com ancoras `1..5` carregaria, e o avaliador que
pontuasse `0` receberia "nivel inexistente" no meio do exercicio.

POR QUE `Path` COMO PARAMETRO
------------------------------
A raiz e argumento com default, e nao constante lida no import: o teste planta
biblioteca com defeito num diretorio temporario e chama a mesma funcao que a
producao chama. Verificador que so roda contra a arvore boa nunca prova que
reprova.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from range_core.engine.loader.contract_source import parse_document

#: Os cinco niveis da escala `0-4` de `03` secao 2.2. Conjunto, e nao contagem:
#: cinco chaves quaisquer nao sao os cinco niveis.
NIVEIS = frozenset(range(5))

#: `range-core/rubrics/`. O `.yaml` deste diretorio E a biblioteca.
RUBRICS_DIR = Path(__file__).resolve().parent


class RubricLibraryError(Exception):
    """Biblioteca malformada. Distinto de `pack cita rubrica inexistente`.

    Aqui o defeito e do CORE: um arquivo da biblioteca contradiz o proprio nome
    ou nao tem os cinco niveis. Nenhuma carga de pack teria significado depois
    disso, porque a rubrica que pontuaria a competencia esta quebrada.
    """


@dataclass(frozen=True)
class Rubric:
    """Uma rubrica versionada. `rubric_id` e o que `required_rubrics` cita."""

    rubric_id: str
    competency: str
    version: str
    scale: str
    anchors: Mapping[int, str]

    def anchor(self, nivel: int) -> str:
        """A ancora textual de um nivel. `KeyError` e impossivel apos a carga."""
        return self.anchors[nivel]


def _rubric_de(caminho: Path) -> Rubric:
    documento = parse_document(caminho)

    competency = documento.get("competency")
    version = documento.get("version")
    anchors = documento.get("anchors")

    if not isinstance(competency, str) or not isinstance(version, str):
        raise RubricLibraryError(
            f"{caminho.name}: sem `competency` ou sem `version`.\n"
            "    O contrato os exige; se este arquivo chegou aqui, o job "
            "`contratos` nao o validou como instancia real."
        )

    esperado = f"{competency}.{version}"
    if caminho.stem != esperado:
        raise RubricLibraryError(
            f"{caminho.name}: o conteudo diz `{esperado}` e o arquivo diz "
            f"`{caminho.stem}`.\n"
            "    O nome do arquivo E o identificador que `required_rubrics` "
            "cita. Divergindo, o pack casa um id cujo conteudo e outro."
        )

    if not isinstance(anchors, dict):
        raise RubricLibraryError(f"{caminho.name}: `anchors` nao e mapeamento.")

    chaves = set(anchors)
    if chaves != NIVEIS:
        faltando = sorted(NIVEIS - chaves)
        sobrando = sorted(k for k in chaves if k not in NIVEIS)
        partes = []
        if faltando:
            partes.append(f"niveis ausentes: {faltando}")
        if sobrando:
            partes.append(f"chaves fora da escala 0-4: {sobrando}")
        raise RubricLibraryError(
            f"{caminho.name}: {'; '.join(partes)}.\n"
            "    A escala e `0-4` e as ancoras sao os niveis dela — cinco "
            "chaves quaisquer nao sao os cinco niveis. Avaliador que pontuar "
            "um nivel sem ancora recebe o erro no meio do exercicio."
        )

    return Rubric(
        rubric_id=esperado,
        competency=competency,
        version=version,
        scale=documento.get("scale", ""),
        anchors=MappingProxyType({int(k): v for k, v in anchors.items()}),
    )


def load_library(raiz: Path | None = None) -> dict[str, Rubric]:
    """`rubric_id -> Rubric` para todo `.yaml` da raiz, em ordem de id.

    BIBLIOTECA VAZIA REPROVA, e isso e recusa e nao permissao. Raiz sem `.yaml`
    resolveria `required_rubrics` contra conjunto vazio e recusaria TODO pack,
    com a mensagem errada — "rubrica ausente" em vez de "biblioteca ausente".
    E o mesmo argumento que `build_pack_registries` faz para documento faltando,
    com a conclusao oposta porque aqui a raiz e do core e nao do pack: pack sem
    `objectives.yaml` e cenario possivel; core sem rubrica nenhuma, nao.
    """
    raiz = RUBRICS_DIR if raiz is None else raiz
    caminhos = sorted(raiz.glob("*.yaml"))
    if not caminhos:
        raise RubricLibraryError(
            f"{raiz}: nenhuma rubrica.\n"
            "    A biblioteca e do core (`00` §5.8) e nao pode estar vazia: "
            "vazia, todo pack seria recusado por 'rubrica ausente', que e a "
            "mensagem errada para o defeito certo."
        )
    return {r.rubric_id: r for r in (_rubric_de(c) for c in caminhos)}
