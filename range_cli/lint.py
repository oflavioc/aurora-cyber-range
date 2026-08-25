"""`range-cli scenario lint <path>` — as recusas do pack, TODAS, e onde elas estao.

O QUE ELE FECHA
===============
Os itens 1, 2 e 3 da DoD da Fase 7 (`07_IMPLEMENTATION_PHASES.md`):

    1. `range-cli scenario lint` recusa inject sem objetivo e sem `noise: true`
    2. `event_type` inexistente em condicao de branch e recusado, COM POSICAO NO ARQUIVO
    3. condicao dependente de juizo do facilitador e recusada

E os criterios correspondentes de `06_ACCEPTANCE_TESTS.md` T12, que acrescentam
um quarto com a mesma exigencia de posicao: opcao com `capability_gap`
referenciando objetivo inexistente.

O QUE JA EXISTIA, E QUAL E O DELTA — a medicao que abriu a peca
================================================================
As tres recusas dos itens 1 a 3 **ja ocorriam** antes deste modulo, na CARGA:

    item 1   `if/else` em `#/$defs/inject` do contrato de cenario — camada 1
    item 2   `x-aurora-ref: event_catalog` em `branch_event.event` — camada 2
    item 3   `branch_condition` com `oneOf` fechado e `additionalProperties: false`

O delta desta peca nao e a recusa — e (a) a SUPERFICIE, porque `range-cli` so
tinha `materialize`; (b) a POSICAO NO ARQUIVO, que o criterio cobra duas vezes e
que nada produzia; e (c) relatar TODAS as recusas em vez de parar na primeira.

POR QUE O LINTER NAO REIMPLEMENTA NENHUMA REGRA
================================================
Ele e o TERCEIRO chamador de `contract_rules` — depois do executor de fixtures do
CI e do loader de pack —, e chega la por `pack_loader.varre_pack`, que roda a
MESMA lista de passos que o boot. Uma segunda implementacao produziria o linter
aceitando pack que o boot recusa, e vice-versa: e a classe que a §1.4 do
checkpoint da Fase 2 fechou, e que `contract_rules` existe para nao deixar
voltar.

`confere_citacoes_do_pack` ja previa este chamador por escrito — *"o verbo do CLI
chamara ESTA funcao — uma implementacao, dois chamadores"*. Ele chama.

O RELATORIO E APRESENTACAO, E POR ISSO MORA AQUI
=================================================
`posicao.py` resolve caminho -> `linha:coluna` e e do nucleo, porque e sobre o
documento. Como isso vira texto na tela e decisao de CLI, e um nucleo que
formatasse relatorio teria adquirido opiniao sobre terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, PackError, varre_pack
from range_core.engine.loader.posicao import MapaDePosicoes, Posicao

#: `01_ARCHITECTURE.md` §5.2 normatiza `domains/<adapter>/flags.yaml` como a
#: declaracao de flags do adapter, e `pack_loader` ja repete esse caminho na
#: mensagem que T2 exige. Deriva-lo aqui e ler a norma, e nao inventar convencao.
FLAGS_DO_ADAPTER = "domains/{domain}/flags.yaml"


class LintRecusado(Exception):
    """O linter nao pode correr. Distinto de "o pack tem achados"."""


@dataclass(frozen=True, slots=True)
class Achado:
    """Uma recusa, com onde ela esta. `posicao` e `None` quando nao ha onde.

    Recusa sem posicao e legitima e nao e defeito do resolvedor: pack COMPLETO
    sem `objectives.yaml` nao tem linha nenhuma onde caber — o defeito e a
    ausencia de um arquivo, e apontar para uma linha do que existe seria apontar
    para o lugar errado com aparencia de certeza.
    """

    erro: PackError
    posicao: Posicao | None

    @property
    def onde(self) -> str:
        arquivo = self.erro.arquivo or ""
        if self.posicao is None:
            return arquivo or "<pack>"
        return f"{arquivo}:{self.posicao}"


def localiza(achados: list[PackError], textos: dict[str, str]) -> list[Achado]:
    """Cada recusa, com a posicao resolvida sobre o texto de que ela saiu.

    UM MAPA POR ARQUIVO, montado sob demanda: o pack de 4 h tem seis documentos
    e um pack limpo nao monta mapa nenhum — compor a arvore de nos de todos eles
    para depois nao usar nenhuma seria pagar o caso raro no caso comum.
    """
    mapas: dict[str, MapaDePosicoes] = {}
    localizados: list[Achado] = []
    for erro in achados:
        posicao = None
        arquivo, caminho = erro.arquivo, erro.caminho
        if arquivo and caminho and arquivo in textos:
            if arquivo not in mapas:
                mapas[arquivo] = MapaDePosicoes.do_texto(textos[arquivo])
            posicao = mapas[arquivo].de(caminho)
        localizados.append(Achado(erro=erro, posicao=posicao))
    return localizados


def lint(
    pack_dir: Path | str,
    *,
    contracts,
    adapter_flags: AdapterFlags,
) -> list[Achado]:
    """Os achados do pack, localizados. Lista vazia significa pack limpo."""
    achados, textos = varre_pack(
        pack_dir, contracts=contracts, adapter_flags=adapter_flags
    )
    return localiza(achados, textos)


def flags_do_pack(pack_dir: Path, raiz: Path) -> AdapterFlags:
    """As flags do adapter que o MANIFESTO declara — e nao as do contexto.

    A DIFERENCA PARA `04` §8.2 E DE ESPECIE, e ela precisa ser dita porque a
    forma se parece. Aquela secao proibe `materialize` de DERIVAR `domain` de
    adapter em uso, de variavel de ambiente ou de diretorio corrente — e a razao
    e que ele ESCREVE, e destino de escrita de gabarito nao se descobre por
    contexto.

    Aqui o `domain` nao e derivado de contexto nenhum: ele e CAMPO DECLARADO do
    `manifest.yaml` que o operador apontou, e `contracts/scenario.schema.v2.yaml`
    o exige em `required`. Ler um campo do arquivo que se pediu para conferir e o
    oposto de descobrir o alvo sozinho.

    O caminho vem de `01_ARCHITECTURE.md` §5.2, que normatiza
    `domains/<adapter>/flags.yaml`. `--flags` continua existindo para o adapter
    que nao more ali.
    """
    manifesto = pack_dir / "manifest.yaml"
    if not manifesto.is_file():
        raise LintRecusado(
            f"{pack_dir}: falta `manifest.yaml`. Sem ele nao se sabe nem que "
            "dominio o pack declara, e as flags contra as quais conferir sao as "
            "DAQUELE adapter."
        )
    try:
        documento = contract_source.parse_document(manifesto)
    except contract_source.ContractSourceError as erro:
        raise LintRecusado(str(erro)) from erro

    domain = documento.get("domain")
    if not isinstance(domain, str) or not domain:
        raise LintRecusado(
            f"{manifesto}: sem `domain`. O contrato o exige em `required`, e sem "
            "ele nao ha adapter cujas flags conferir. Rode de novo com `--flags` "
            "se o manifesto ainda estiver sendo escrito."
        )
    return carrega_flags(raiz / FLAGS_DO_ADAPTER.format(domain=domain))


def carrega_flags(caminho: Path) -> AdapterFlags:
    """`flags.yaml` -> `AdapterFlags`, com o `source` que T2 exige na mensagem.

    O nucleo NAO le este arquivo — `AdapterFlags.from_document` recebe o
    documento ja parseado de proposito, e o cabecalho de `contract_rules` diz por
    que: ir buscar arquivo de `domains/` seria o acoplamento que o invariante 1
    existe para evitar, entrando por outra porta. Quem le e este modulo, que e
    de TOPO.
    """
    if not caminho.is_file():
        raise LintRecusado(
            f"{caminho}: nao existe. `01_ARCHITECTURE.md` §5.2 normatiza "
            "`domains/<adapter>/flags.yaml` como a declaracao de flags do "
            "adapter; se o deste pack mora em outro lugar, aponte-o com `--flags`."
        )
    try:
        documento = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as erro:
        raise LintRecusado(f"{caminho}: nao pode ser lido — {erro}") from erro
    return AdapterFlags.from_document(documento or {}, source=caminho.as_posix())


def relatorio(achados: list[Achado]) -> list[str]:
    """As linhas do relatorio, na ordem em que os passos as produziram.

    A ORDEM E A DOS PASSOS, e nao a do arquivo. Ela e a ordem em que a recusa
    ocorre no boot — completude, versao, schema, regras, predicados, citacoes —,
    e e a ordem em que consertar: um `injects.yaml` que nao valida contra o
    contrato torna incerto o que a camada 2 diria sobre ele. Reordenar por linha
    daria ao autor uma lista bonita e a sugestao errada de por onde comecar.

    A POSICAO INEXATA SE DECLARA. `~` antes do `linha:coluna` diz que aquela e a
    posicao do ancestral, e a linha seguinte nomeia ate onde o caminho resolveu.
    Sem a marca, um apontamento aproximado teria a mesma cara de um exato.
    """
    linhas: list[str] = []
    for achado in achados:
        erro = achado.erro
        marca = "" if achado.posicao is None or achado.posicao.exata else "~"
        linhas.append(f"{marca}{achado.onde}: [{erro.site}]")
        linhas.extend(f"  {linha}" for linha in erro.mensagem.splitlines())
        if achado.posicao is not None and not achado.posicao.exata:
            linhas.append(
                f"  (posicao aproximada: o caminho resolveu ate "
                f"`{achado.posicao.caminho_resolvido}`, e `{erro.caminho}` "
                "nao existe no documento como ele foi lido)"
            )
    return linhas
