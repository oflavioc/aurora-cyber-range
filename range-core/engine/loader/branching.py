"""A travessia do grafo de branches — um dono, dois consumidores.

O QUE ESTE MODULO FECHA
========================
Os itens 4 e 6 da DoD da Fase 7 (`07_IMPLEMENTATION_PHASES.md`) e a metade
"indicado" da regra do `option` (`x-aurora-linter-rules`,
`option_existe_no_decision_point_indicado`, parcial desde a peca 3):

    4. `branch_policy` do manifesto e aplicada — excesso de pontos de
       ramificacao por linha ou de caminhos por ponto e recusado
    6. `dryrun` percorre todos os caminhos — e recusa o que nao consegue
       percorrer (`06` T12: *"sem erro"*)

POR QUE UM MODULO, E NAO DUAS FUNCOES ONDE CADA CONSUMIDOR MORA
================================================================
E o motivo registrado em `x-aurora-linter-rules -> branch_policy_aplicada`
desde a peca 3: *"a politica so pode ser aplicada por quem conta pontos de
ramificacao por linha e caminhos por ponto, e isso e a mesma travessia que o
`dryrun` percorre. Separar as duas duplicaria a caminhada do grafo"*. A
estrutura de pontos (`pontos_de_ramificacao`) e uma; quem conta (`_passos`
do loader, via `confere_branch_policy`) e quem anda (`range-cli scenario
dryrun`, via `percorre`) sao os dois chamadores.

A SEMANTICA E DECLARADA, NAO INFERIDA
======================================
`04` §6 da o exemplo normativo e `04` §2 da as duas contagens; o resto e
decisao desta peca, registrada em `docs/progress/fase_7.md` §5.2 ANTES do
codigo. As que moldam este arquivo:

- **linha de um ponto** = campo `line` da branch; ausente, a `linha` do
  inject de `at_inject`. Grupo `None` e legitimo, como nos injects.
- **caminho de um braco** = `at_inject` -> `next` -> injects comuns da linha
  na janela entre `next` e `reconverge_at` (excluidos os `next` dos bracos
  irmaos, que sao a divergencia) -> `reconverge_at`. `next` IGUAL a
  `reconverge_at` e legal — o braco vai direto a reconvergencia, e a fixture
  limpa da suite de lint fixa isso desde a peca 3.
- **a travessia recusa o que nao percorre**: `next` que nao vem depois de
  `at_inject` no relogio; `reconverge_at` antes de `next`; `next` ou
  `reconverge_at` fora da linha do ponto. Sao recusas do `dryrun`, nao do
  lint — pack que linta limpo e nao ensaia e o que o verbo existe para pegar
  antes da sala (`04` §8: *"dryrun e pre-requisito de ensaio"*).

O IMPORT DE `pack_loader` E DE MAO UNICA
=========================================
`PackError`, `PackSite` e `t_relative_seconds` moram la; este modulo os
importa no topo. O `pack_loader` consome este modulo por import TARDIO,
dentro de `_passos` — a outra direcao no topo seria ciclo, e a forma tardia
ja e precedente decidido em `range_cli/cli.py`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from range_core.engine.loader.pack_loader import (
    PackError,
    PackSite,
    t_relative_seconds,
)

#: O arquivo sobre o qual toda recusa deste modulo se localiza.
BRANCHES = "branches.yaml"


@dataclass(frozen=True, slots=True)
class Braco:
    """Um item de `evaluate` — um caminho possivel do ponto."""

    id: str | None
    next: str | None
    default: bool
    #: JSON path do braco em `branches.yaml`, para o linter localizar.
    caminho: str


@dataclass(frozen=True, slots=True)
class Ponto:
    """Uma branch de `branches.yaml`, com a linha ja resolvida."""

    id: str | None
    line: object
    at_inject: str | None
    reconverge_at: str | None
    bracos: tuple[Braco, ...]
    caminho: str


@dataclass(frozen=True, slots=True)
class Caminho:
    """Um caminho percorrido: o ponto, o braco, e a sequencia de injects."""

    ponto: Ponto
    braco: Braco
    sequencia: tuple[str, ...]


def _linha_por_inject(injects_document: Mapping | None) -> dict[str, object]:
    linhas: dict[str, object] = {}
    for bruto in (injects_document or {}).get("injects") or []:
        if isinstance(bruto, Mapping) and isinstance(bruto.get("id"), str):
            linhas[bruto["id"]] = bruto.get("linha")
    return linhas


def pontos_de_ramificacao(
    injects_document: Mapping | None, branches_document: Mapping | None
) -> list[Ponto]:
    """As branches do pack, como estrutura — a base dos dois consumidores.

    DEFENSIVO POR DESENHO: campo ausente vira `None` em vez de levantar. A
    forma e recusa da camada 1, que roda ANTES de qualquer chamador deste
    modulo na lista de `_passos`; aqui a pergunta e outra, e uma branch
    malformada nao pode esconder a contagem das bem-formadas no relatorio do
    linter, que colhe um achado por passo.
    """
    linhas = _linha_por_inject(injects_document)
    pontos: list[Ponto] = []
    for indice, bruto in enumerate((branches_document or {}).get("branches") or []):
        if not isinstance(bruto, Mapping):
            continue
        caminho = f"$.branches[{indice}]"
        bracos = tuple(
            Braco(
                id=braco.get("id") if isinstance(braco.get("id"), str) else None,
                next=braco.get("next") if isinstance(braco.get("next"), str) else None,
                default=braco.get("default") is True,
                caminho=f"{caminho}.evaluate[{j}]",
            )
            for j, braco in enumerate(bruto.get("evaluate") or [])
            if isinstance(braco, Mapping)
        )
        at_inject = bruto.get("at_inject")
        at_inject = at_inject if isinstance(at_inject, str) else None
        reconverge = bruto.get("reconverge_at")
        reconverge = reconverge if isinstance(reconverge, str) else None
        line = bruto.get("line")
        if line is None and at_inject is not None:
            line = linhas.get(at_inject)
        pontos.append(
            Ponto(
                id=bruto.get("id") if isinstance(bruto.get("id"), str) else None,
                line=line,
                at_inject=at_inject,
                reconverge_at=reconverge,
                bracos=bracos,
                caminho=caminho,
            )
        )
    return pontos


def _rotulo_de_linha(line: object) -> str:
    return f"linha {line!r}" if line is not None else "branches sem linha resolvida"


def confere_branch_policy(
    manifest_document: Mapping | None,
    injects_document: Mapping | None,
    branches_document: Mapping | None,
) -> None:
    """*"`branch_policy` do manifesto e aplicada"* — `04` §2, §6.2 e `06` T12.

    MANIFESTO SEM `branch_policy` NAO CONTA NADA. O campo e opcional no
    contrato, e politica ausente e ausencia de limite declarado — inventar um
    default seria a classe D6, piso que a fonte nao declara.

    NA CARGA TAMBEM, e nao so no linter — este `confere_*` entra em `_passos`,
    que os dois consumidores rodam. Regra que o `lint` recusasse e o boot
    aceitasse produziria pack reprovado pelo CI e carregado pelo engine.

    A PRIMEIRA VIOLACAO GANHA, como em `confere_ordem_de_t_relative`: um
    achado por passo e o contrato da colheita, e o primeiro excesso — na ordem
    do arquivo — e o lugar certo para apontar, porque e o ponto em que o
    limite declarado foi ultrapassado.
    """
    politica = (manifest_document or {}).get("branch_policy")
    if not isinstance(politica, Mapping):
        return

    pontos = pontos_de_ramificacao(injects_document, branches_document)

    max_pontos = politica.get("max_branch_points_per_line")
    if isinstance(max_pontos, int) and not isinstance(max_pontos, bool):
        contagem: dict[object, int] = {}
        for ponto in pontos:
            contagem[ponto.line] = contagem.get(ponto.line, 0) + 1
            if contagem[ponto.line] > max_pontos:
                raise PackError(
                    PackSite.BRANCH_POLICY_EXCEEDED,
                    f"branch {ponto.id!r}: e o ponto de ramificacao numero "
                    f"{contagem[ponto.line]} da {_rotulo_de_linha(ponto.line)}, e o "
                    "manifesto declara `branch_policy.max_branch_points_per_line: "
                    f"{max_pontos}`.\n"
                    "    A politica e do MANIFESTO e a contagem e por linha — a "
                    "linha de um ponto e o campo `line` da branch, ou a `linha` "
                    "do inject de `at_inject` quando ele falta. Ou a branch sai, "
                    "ou o limite declarado sobe.",
                    arquivo=BRANCHES,
                    caminho=ponto.caminho,
                )

    max_caminhos = politica.get("max_paths_per_branch")
    if isinstance(max_caminhos, int) and not isinstance(max_caminhos, bool):
        for ponto in pontos:
            if len(ponto.bracos) > max_caminhos:
                raise PackError(
                    PackSite.BRANCH_POLICY_EXCEEDED,
                    f"branch {ponto.id!r}: `evaluate` tem {len(ponto.bracos)} "
                    "caminhos, e o manifesto declara "
                    f"`branch_policy.max_paths_per_branch: {max_caminhos}`.\n"
                    "    Cada braco de `evaluate` e um caminho que o exercicio "
                    "pode tomar e que o `dryrun` percorre — o limite existe para "
                    "o numero de caminhos do ensaio nao crescer alem do que o "
                    "manifesto prometeu.",
                    arquivo=BRANCHES,
                    caminho=f"{ponto.caminho}.evaluate",
                )


def _decision_points(injects_document: Mapping | None) -> dict[str, set[str]]:
    """`{decision_point.id: {option.id, ...}}` do `injects.yaml`."""
    pontos: dict[str, set[str]] = {}
    for inject in (injects_document or {}).get("injects") or []:
        if not isinstance(inject, Mapping):
            continue
        ponto = inject.get("decision_point")
        if not isinstance(ponto, Mapping) or not isinstance(ponto.get("id"), str):
            continue
        opcoes = {
            opcao["id"]
            for opcao in ponto.get("options") or []
            if isinstance(opcao, Mapping) and isinstance(opcao.get("id"), str)
        }
        pontos[ponto["id"]] = opcoes
    return pontos


def confere_option_no_decision_point(
    injects_document: Mapping | None, branches_document: Mapping | None
) -> None:
    """*"todo `option` referenciado deve existir no `decision_point` INDICADO"*.

    A METADE QUE FALTAVA DESDE A PECA 3, e o registro do contrato a declarava
    por escrito: o `x-aurora-ref: pack_decision_options` prova existencia
    GLOBAL, a folha `option` nao carrega o `decision`, e as duas viajam em
    folhas IRMAS da mesma conjuncao — casa-las exige interpretar a arvore de
    `when`, que e o que este passo faz.

    O PAR E LIDO NA CONJUNCAO DIRETA: `decision` e `option` irmaos do mesmo
    `all` — a forma do vocabulario de `04` §6.1 (*"`decision` + `option`"*).
    `option` cujo `decision` irmao nao existe no pack e recusado pela MESMA
    regra: nao ha "indicado" onde existir. Folha `option` sem irmao
    `decision` segue coberta so pela existencia global, e isso esta declarado
    no registro do contrato — `any`/`not` nao pareiam, porque disjuncao e
    negacao nao indicam nada.

    Com MAIS DE UM `decision` irmao, o `option` e aceito se pertence a
    QUALQUER um deles: a conjuncao afirma as duas decisoes tomadas, e a folha
    nao diz de qual das duas o option e — recusar o que pertence a uma delas
    seria recusar pack legitimo por limitacao da leitura.
    """
    pontos = _decision_points(injects_document)
    for indice, bruto in enumerate((branches_document or {}).get("branches") or []):
        if not isinstance(bruto, Mapping):
            continue
        for j, braco in enumerate(bruto.get("evaluate") or []):
            if isinstance(braco, Mapping) and isinstance(braco.get("when"), Mapping):
                _confere_condicao(
                    braco["when"],
                    f"$.branches[{indice}].evaluate[{j}].when",
                    pontos,
                )


def _confere_condicao(
    condicao: Mapping, caminho: str, pontos: dict[str, set[str]]
) -> None:
    filhos = condicao.get("all")
    if isinstance(filhos, list):
        decisoes = [
            (i, filho["decision"])
            for i, filho in enumerate(filhos)
            if isinstance(filho, Mapping) and isinstance(filho.get("decision"), str)
        ]
        if decisoes:
            desconhecidas = [(i, d) for i, d in decisoes if d not in pontos]
            permitidas: set[str] = set()
            for _, d in decisoes:
                permitidas |= pontos.get(d, set())
            for i, filho in enumerate(filhos):
                if not isinstance(filho, Mapping):
                    continue
                opcao = filho.get("option")
                if not isinstance(opcao, str):
                    continue
                if desconhecidas:
                    indice_d, dp = desconhecidas[0]
                    raise PackError(
                        PackSite.OPTION_FORA_DO_DECISION_POINT,
                        f"a condicao pareia `option: {opcao}` com `decision: "
                        f"{dp}`, e nenhum inject do pack tem `decision_point` "
                        f"com id {dp!r}.\n"
                        "    Nao ha decision_point INDICADO onde o option possa "
                        "existir — e a mesma classe do event_type inexistente: o "
                        "erro de digitacao nao falha em lugar nenhum, a condicao "
                        "simplesmente nunca casa, e ninguem percebe ate o "
                        "exercicio ao vivo.",
                        arquivo=BRANCHES,
                        caminho=f"{caminho}.all[{indice_d}].decision",
                    )
                if opcao not in permitidas:
                    indicados = sorted(d for _, d in decisoes)
                    rotulo = (
                        f"o decision_point indicado ({indicados[0]!r})"
                        if len(indicados) == 1
                        else f"nenhum dos decision_points indicados ({indicados})"
                    )
                    raise PackError(
                        PackSite.OPTION_FORA_DO_DECISION_POINT,
                        f"`option: {opcao}` nao existe em {rotulo} — as opcoes "
                        "dele sao "
                        f"{sorted(permitidas) if permitidas else 'nenhuma'}.\n"
                        "    A existencia GLOBAL o `x-aurora-ref` ja prova; o que "
                        "esta recusado aqui e a metade \"indicado\" de `04` "
                        "§6.2: a folha `decision` irma diz QUAL ponto de decisao "
                        "a condicao le, e o option precisa ser dele.",
                        arquivo=BRANCHES,
                        caminho=f"{caminho}.all[{i}].option",
                    )
        for i, filho in enumerate(filhos):
            if isinstance(filho, Mapping):
                _confere_condicao(filho, f"{caminho}.all[{i}]", pontos)

    alternativas = condicao.get("any")
    if isinstance(alternativas, list):
        for i, filho in enumerate(alternativas):
            if isinstance(filho, Mapping):
                _confere_condicao(filho, f"{caminho}.any[{i}]", pontos)

    negada = condicao.get("not")
    if isinstance(negada, Mapping):
        _confere_condicao(negada, f"{caminho}.not", pontos)


def percorre(
    injects_document: Mapping | None, branches_document: Mapping | None
) -> list[Caminho]:
    """Todos os caminhos de branch, percorridos — o corpo do `dryrun`.

    PRESSUPOE PACK LIMPO. O verbo roda o lint antes e para nos achados; aqui
    os ids ja resolvem (camada 2) e os `t_relative` ja tem forma (passo
    proprio). O que ESTE passo recusa e o que nenhuma camada anterior ve: a
    branch bem-formada cujo caminho nao e percorrivel no relogio ou na linha.

    A ORDEM DENTRO DA JANELA E A DO ENGINE — `(t_relative_seconds, id)`, a
    mesma de `inject_engine` —, porque o caminho impresso e o ensaio do que o
    exercicio faria, e nao uma ordenacao nova.
    """
    tempos: dict[str, int] = {}
    linhas: dict[str, object] = {}
    for bruto in (injects_document or {}).get("injects") or []:
        if not isinstance(bruto, Mapping) or not isinstance(bruto.get("id"), str):
            continue
        identificador = bruto["id"]
        linhas[identificador] = bruto.get("linha")
        valor = bruto.get("t_relative")
        if valor is not None:
            tempos[identificador] = t_relative_seconds(valor, identificador)

    caminhos: list[Caminho] = []
    for ponto in pontos_de_ramificacao(injects_document, branches_document):
        if ponto.at_inject is None or ponto.reconverge_at is None:
            continue  # forma e recusa da camada 1, antes deste chamador
        for nome, inject_id in (
            ("at_inject", ponto.at_inject),
            ("reconverge_at", ponto.reconverge_at),
        ):
            if inject_id not in tempos:
                raise PackError(
                    PackSite.BRANCH_WALK_IMPOSSIBLE,
                    f"branch {ponto.id!r}: `{nome}: {inject_id}` nao resolve para "
                    "um inject com `t_relative` — nao ha onde ancorar a "
                    "travessia.",
                    arquivo=BRANCHES,
                    caminho=f"{ponto.caminho}.{nome}",
                )
        t_at = tempos[ponto.at_inject]
        t_rec = tempos[ponto.reconverge_at]
        for braco in ponto.bracos:
            if braco.next is None:
                continue  # `next` e `required` do braco — camada 1
            rotulo = braco.id or braco.caminho
            if braco.next not in tempos:
                raise PackError(
                    PackSite.BRANCH_WALK_IMPOSSIBLE,
                    f"branch {ponto.id!r}, braco {rotulo!r}: `next: {braco.next}` "
                    "nao resolve para um inject com `t_relative`.",
                    arquivo=BRANCHES,
                    caminho=f"{braco.caminho}.next",
                )
            t_next = tempos[braco.next]
            if linhas.get(braco.next) != ponto.line or linhas.get(
                ponto.reconverge_at
            ) != ponto.line:
                fora = (
                    braco.next
                    if linhas.get(braco.next) != ponto.line
                    else ponto.reconverge_at
                )
                raise PackError(
                    PackSite.BRANCH_WALK_IMPOSSIBLE,
                    f"branch {ponto.id!r}, braco {rotulo!r}: {fora!r} esta na "
                    f"linha {linhas.get(fora)!r}, e o ponto e da "
                    f"{_rotulo_de_linha(ponto.line)}.\n"
                    "    O caminho de um braco e a janela da LINHA DO PONTO "
                    "entre a divergencia e a reconvergencia (registro §5.2 da "
                    "fase); um `next` de outra linha nao tem janela onde "
                    "correr.",
                    arquivo=BRANCHES,
                    caminho=f"{braco.caminho}.next",
                )
            if t_next <= t_at:
                raise PackError(
                    PackSite.BRANCH_WALK_IMPOSSIBLE,
                    f"branch {ponto.id!r}, braco {rotulo!r}: `next: {braco.next}` "
                    f"dispara em {_hhmm(t_next)}, que nao vem DEPOIS do "
                    f"`at_inject: {ponto.at_inject}` ({_hhmm(t_at)}).\n"
                    "    A divergencia acontece no ponto; um caminho que comeca "
                    "antes dele nao e percorrivel no relogio do exercicio.",
                    arquivo=BRANCHES,
                    caminho=f"{braco.caminho}.next",
                )
            if t_rec < t_next:
                raise PackError(
                    PackSite.BRANCH_WALK_IMPOSSIBLE,
                    f"branch {ponto.id!r}, braco {rotulo!r}: `reconverge_at: "
                    f"{ponto.reconverge_at}` ({_hhmm(t_rec)}) vem ANTES de "
                    f"`next: {braco.next}` ({_hhmm(t_next)}) — o caminho "
                    "diverge e nao tem onde reconvergir.",
                    arquivo=BRANCHES,
                    caminho=f"{ponto.caminho}.reconverge_at",
                )
            irmaos = {
                outro.next
                for outro in ponto.bracos
                if outro is not braco and outro.next is not None
            } - {ponto.reconverge_at}
            janela = sorted(
                (
                    identificador
                    for identificador, t in tempos.items()
                    if linhas.get(identificador) == ponto.line
                    and (t, identificador) > (t_next, braco.next)
                    and (t, identificador) < (t_rec, ponto.reconverge_at)
                    and identificador not in irmaos
                ),
                key=lambda identificador: (tempos[identificador], identificador),
            )
            if braco.next == ponto.reconverge_at:
                sequencia = (ponto.at_inject, ponto.reconverge_at)
            else:
                sequencia = (
                    ponto.at_inject,
                    braco.next,
                    *janela,
                    ponto.reconverge_at,
                )
            caminhos.append(Caminho(ponto=ponto, braco=braco, sequencia=sequencia))
    return caminhos


def _hhmm(segundos: int) -> str:
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}"
