"""Caminho de instancia -> posicao no arquivo. A metade que faltava ao linter.

AUTORIDADE
----------
`06_ACCEPTANCE_TESTS.md` T12 — *"`event_type` inexistente em condicao de branch
e recusado pelo linter, **com a posicao no arquivo**"*, e a mesma exigencia
repetida no criterio da opcao com `capability_gap`. `07_IMPLEMENTATION_PHASES.md`
Fase 7, item 2 da DoD, escreve *"com posicao no arquivo"*.

O QUE "POSICAO NO ARQUIVO" QUER DIZER, E POR QUE NAO E O CAMINHO DE INSTANCIA
-----------------------------------------------------------------------------
As duas camadas de validacao ja produzem CAMINHO: `jsonschema` devolve
`e.json_path` (`$.branches[0].evaluate[0].when.all[0].event`) e a `AuroraChecker`
devolve o `ipath` dela, **no mesmo dialeto** — `$` na raiz, `.chave` para
mapeamento, `[i]` para sequencia. Isso foi conferido, e nao suposto: e o que
permite que UM resolvedor sirva as duas.

Caminho e posicao no DOCUMENTO. `linha:coluna` e posicao no ARQUIVO, e e a que o
criterio cobra — porque e a que o autor do pack cola no editor. Quem le
`$.branches[0].evaluate[0].when.all[0]` tem de contar bracos a mao para achar o
`event` errado; quem le `branches.yaml:14:18` abre no lugar.

AS DUAS LEITURAS SAO DOS MESMOS BYTES, E ISSO E A GARANTIA
-----------------------------------------------------------
`yaml.safe_load` e `yaml.compose` correm sobre a MESMA string, entregue pelo
chamador. Reler o arquivo aqui abriria janela entre as duas leituras, e nela a
posicao passaria a apontar para um arquivo que nao e o que foi validado — erro
pior que posicao ausente, porque parece certo.

`compose` NAO CONSTROI OBJETO: ele para na arvore de nos. `05` §1 continua valendo
pelo mesmo motivo que faz `parse_document` usar `safe_load` — pack e conteudo de
terceiro do ponto de vista do engine.

O FALLBACK E DECLARADO, E NAO SILENCIOSO
-----------------------------------------
Caminho que nao resolve exato devolve a posicao do ANCESTRAL mais profundo que
resolve, e diz que foi isso que fez (`exata=False`). Cair para o ancestral em
silencio faria o linter apontar uma linha errada com a mesma confianca de uma
certa — e a exigencia de T12 e sobre localizar, entao localizacao que mente e
pior que a ausencia dela.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

#: Um segmento do dialeto de caminho: `.chave` ou `[indice]`.
#:
#: `<chave:NOME>` e a forma que a `AuroraChecker` emite para violacao colhida em
#: `propertyNames` — a chave de um `effects`, por exemplo. Ali o que viola e o
#: NOME da chave, e nao o valor dela, entao ele resolve para o no da chave.
_SEGMENTO = re.compile(r"\.<chave:(?P<chave>[^>]*)>|\.(?P<nome>[^.\[]+)|\[(?P<indice>\d+)\]")


@dataclass(frozen=True, slots=True)
class Posicao:
    """Onde, no arquivo. `linha` e `coluna` sao 1-based, como todo editor conta.

    `exata` diz se o caminho pedido resolveu inteiro. `False` significa que esta
    e a posicao do ancestral nomeado em `caminho_resolvido` — e quem exibe
    precisa dizer isso, sob pena de apontar uma linha com confianca que ela nao
    tem.
    """

    linha: int
    coluna: int
    exata: bool
    caminho_resolvido: str

    def __str__(self) -> str:
        return f"{self.linha}:{self.coluna}"


def _segmentos(caminho: str) -> list[tuple[str, str]]:
    """`$.a[0].b` -> `[("nome","a"), ("indice","0"), ("nome","b")]`.

    Caminho que nao comece em `$` e recusado devolvendo lista vazia — quem o
    produziu nao e nenhuma das duas camadas, e adivinhar a raiz seria inventar.
    """
    if not caminho.startswith("$"):
        return []
    partes: list[tuple[str, str]] = []
    posicao = 1
    while posicao < len(caminho):
        casado = _SEGMENTO.match(caminho, posicao)
        if casado is None:
            return partes
        if casado.group("chave") is not None:
            partes.append(("chave", casado.group("chave")))
        elif casado.group("nome") is not None:
            partes.append(("nome", casado.group("nome")))
        else:
            partes.append(("indice", casado.group("indice")))
        posicao = casado.end()
    return partes


class MapaDePosicoes:
    """A arvore de nos de UM documento, consultavel por caminho de instancia.

    Guarda a arvore em vez de um dicionario `caminho -> posicao` porque a
    consulta precisa poder PARAR no meio: o fallback devolve o ancestral, e um
    dicionario plano so responde sim ou nao.
    """

    def __init__(self, raiz) -> None:
        self._raiz = raiz

    @classmethod
    def do_texto(cls, texto: str) -> MapaDePosicoes:
        """Do MESMO texto que o chamador entregou ao `safe_load`.

        YAML invalido devolve mapa VAZIO em vez de levantar: quem recusa
        documento ilegivel e o passo de leitura, com sitio proprio
        (`PackSite.DOCUMENT_UNREADABLE`), e um segundo levantamento aqui
        transformaria o relatorio do linter em rastro de pilha.
        """
        try:
            return cls(yaml.compose(texto))
        except yaml.YAMLError:
            return cls(None)

    def de(self, caminho: str) -> Posicao | None:
        """A posicao daquele caminho, ou a do ancestral mais profundo, ou `None`.

        `None` so quando nem a raiz existe — documento vazio ou ilegivel.
        """
        no = self._raiz
        if no is None:
            return None

        resolvido = "$"
        melhor = no
        for especie, valor in _segmentos(caminho):
            proximo = _desce(no, especie, valor)
            if proximo is None:
                return _posicao(melhor, exata=False, caminho=resolvido)
            no = melhor = proximo
            resolvido += (
                f"[{valor}]"
                if especie == "indice"
                else f".<chave:{valor}>" if especie == "chave" else f".{valor}"
            )
        return _posicao(melhor, exata=resolvido == caminho, caminho=resolvido)


def _desce(no, especie: str, valor: str):
    """Um passo na arvore de nos. `None` quando o segmento nao existe."""
    if especie == "indice":
        if not isinstance(no, yaml.SequenceNode):
            return None
        indice = int(valor)
        return no.value[indice] if indice < len(no.value) else None

    if not isinstance(no, yaml.MappingNode):
        return None
    for chave, filho in no.value:
        if chave.value == valor:
            # `chave` para violacao de nome de chave, `filho` para as demais: o
            # que viola em `propertyNames` e o nome, e apontar para o valor
            # mandaria o autor consertar o lado certo do dois-pontos por engano.
            return chave if especie == "chave" else filho
    return None


def _posicao(no, *, exata: bool, caminho: str) -> Posicao:
    marca = no.start_mark
    return Posicao(
        linha=marca.line + 1,
        coluna=marca.column + 1,
        exata=exata,
        caminho_resolvido=caminho,
    )
