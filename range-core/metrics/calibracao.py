"""O escore de calibracao da Linha B — Brier no escopo revisado, e os tres sinais.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §5 (5.1 a 5.4); `02_DOMAIN_ACADEMUS.md` §6.2;
`00_MASTER_SPEC.md` §3 (consequencia normativa 4) e §3.2;
`06_ACCEPTANCE_TESTS.md` T11.

O CRITERIO NAO E RECALL
------------------------
`02` §6.2: *"o criterio NAO e encontrar 40 de 40. E a relacao entre confianca
declarada e forca real da evidencia."* Por isso nao ha contagem de acertos aqui —
o escore compara `confidence` com `defensibility`, e o sinal comportamental le a
combinacao das duas.

PROJECAO IRMA, E NAO UM TERCEIRO COMPUTADOR DE METRICA
-------------------------------------------------------
`00` §3.2 poe os dois computadores de metrica dentro da projecao `metrics` e
declara `calibration` como **projecao irma**, que produz o instante verificador
de `TTIV`. Este modulo e ela.

Ele nao recebe `InsumoDeDeclaracao` nem `InsumoDeVerificacao`: recebe **dados**, e
por isso e funcao pura. O que o liga a particao e `TTIV` — o computador do lado
da verificacao chama daqui o instante do limiar, com os escalares que o insumo
dele carrega.

O QUE ELE RECEBE, E POR QUE O ESCOPO E ENTRADA E NAO DERIVACAO
----------------------------------------------------------------
`03` §5.1 manda a equipe declarar `review_scope` — **periodo, populacao,
criterio** — antes de submeter, e §5.3 usa a declaracao para separar erro de
julgamento de lacuna de cobertura.

**Resolver essa prosa num conjunto de `case_id` nao e computavel aqui.** Medido:
`line_b_case` em `contracts/ground_truth.schema.yaml` tem `case_id`,
`defensibility`, `set` e `supporting_evidence` — e **nenhum atributo de data ou
de populacao**. Os atributos que o escopo filtra vivem nas linhas da trilha de
auditoria, no banco semeado, e nao no gabarito.

Entao o conjunto chega como **dado**, resolvido por quem tem os casos. Quem o
resolve, e onde, e a **P6-5** no registro da fase. Deriva-lo aqui por inferencia
seria inventar um filtro que nenhum documento fixa, e o Brier passaria a medir a
inferencia junto com a equipe.

OS TRES SINAIS NAO SE COMPENSAM
--------------------------------
`03` §5.4 e taxativo, e `06` T11 repete: *"o AAR trata os dois sinais
separadamente e nao os compensa entre si"*. Por isso a saida traz **tres listas**,
e nao um numero liquido: somar overconfidence com underconfidence produziria zero
para a equipe que errou dos dois lados, que e a leitura oposta da verdadeira.

*"Para a Linha B, overconfidence e pedagogicamente mais interessante que falso
negativo"* — e a ordem em que os sinais aparecem aqui segue a da tabela de §5.4,
que abre por ele.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from contracts.generated.events import ASSESSMENT_SUBMITTED

from range_core.events.envelope import Event

#: As chaves da submissao — `03` §5.1, e o contrato e
#: `contracts/assessment.schema.yaml`.
CASO = "case_id"
CONFIANCA = "confidence"

#: Os conjuntos do gabarito — `line_b_case.set` em
#: `contracts/ground_truth.schema.yaml`. So o primeiro produz lacuna de
#: cobertura: `03` §5.4 diz *"indevido comprovado fora do escopo revisado"*, e
#: nao "caso qualquer".
CONJUNTO_INDEVIDO = "indevido_comprovado"

#: Os limiares dos sinais — `03` §5.4, verbatim. Inteiros porque `confidence` e
#: inteiro no contrato, e a comparacao com `defensibility` acontece depois da
#: divisao por 100.
CONFIANCA_ALTA = 80
CONFIANCA_BAIXA = 30
DEFENSIBILIDADE_BAIXA = 0.2
DEFENSIBILIDADE_TOTAL = 1.0

#: `03` §5.3 — *"caso dentro do escopo e nao avaliado conta como confidence = 0"*.
#: Nao e "fica de fora": nao olhar um caso e uma resposta, e ela pontua.
CONFIANCA_DE_NAO_AVALIADO = 0

#: Os limites do contrato — `assessment.schema.yaml`, `confidence: integer 0..100`.
CONFIANCA_MINIMA = 0
CONFIANCA_MAXIMA = 100


class SubmissaoForaDoContrato(Exception):
    """`assessment_submitted` cujo payload o contrato proibe. **Recusa alta.**

    A P6-11, decidida pelo operador depois do fechamento da Fase 6. O que ela
    substituiu: `_por_caso` ignorava payload malformado e deixava `confidence`
    fora de faixa passar inteiro. Medido nesta arvore, antes do conserto:

    ======  =============  ===========  ==================================
    valor   defensibility  brier        sinal comportamental
    ======  =============  ===========  ==================================
    900     1.0            **64.0**     nenhum
    900     0.0            81.0         **overconfidence FALSO**
    -1      1.0            1.0201       **underconfidence FALSO**
    100.5   1.0            1.0          **underconfidence FALSO**, "nao avaliado"
    "90"    1.0            1.0          **underconfidence FALSO**, "nao avaliado"
    True    1.0            0.9801       **underconfidence FALSO** (entrou como 1)
    ======  =============  ===========  ==================================

    **POR QUE NAO E "IGNORAR E NOMEAR", como `Calibracao.nao_avaliados`.** Aquela
    lista nomeia ausencia COM significado pedagogico: o AAR distingue *"avaliou com
    confianca zero"* de *"nao avaliou"*, e isso e informacao sobre a equipe.
    `confidence: 900` nao e informacao sobre nada — e dado que o contrato proibe
    entrando por caminho que nao valida. Trata-lo como sinal inventaria semantica
    para lixo, e criaria uma terceira categoria que nenhuma secao define.

    **A GRAVIDADE E DE `03` §5.4, e nao do Brier.** Os sinais tem bordas exatas —
    `>= 80` sobre `<= 0.2`, `<= 30` sobre `= 1.0`. Fora de faixa nao so desloca o
    escore: **cai do lado errado de uma borda e produz sinal comportamental
    FALSO**, e a tabela acima mede as duas direcoes. `03` §5.4 le overconfidence
    como *"falsa acusacao — anular nota de formando inocente"*: um dado corrompido
    viraria **acusacao pedagogica contra a equipe**.

    **CLAMPAR E PIOR, e por isso nao foi escolhido.** `900 -> 100` produz
    overconfidence **plausivel e indistinguivel da real** — o defeito deixaria de
    ter qualquer sintoma, que e a forma exata que `00` §3.2 nomeia.

    **O QUE ELA COBRE, DITO COM PRECISAO:** os dois campos que este modulo LE, e
    nao o payload inteiro. `classification`, `evidence` e `justificativa` sao do
    contrato e nao sao lidos aqui; recusar por eles faria o computador validar o
    que nao consome, e isso e da rota. A regra e uma so — *o computador nao
    inventa semantica para o que le e nao consegue interpretar* —, e por isso
    `case_id` invalido tambem recusa, com `caso is None`.

    **ULTIMA LINHA, E NAO A PRIMEIRA.** A defesa real e a rota validar contra o
    contrato antes de gravar: aqui a submissao ja e evento, e o event store e
    append-only. Ver a P7-1 no registro da Fase 7.
    """

    def __init__(self, campo: str, caso: str | None, valor: object) -> None:
        #: `campo` e uma das duas chaves ja exportadas — `CASO` ou `CONFIANCA`.
        #: Sao elas que o modulo le, e nao ha terceira.
        super().__init__(
            f"`{campo}` fora do contrato em `assessment_submitted`: {valor!r}"
            + (f" (caso {caso})" if caso is not None else " (submissao sem `case_id`)")
            + ". `assessment.schema.yaml` fixa `case_id` no padrao `GC-<numero>` e "
            "`confidence` em inteiro 0..100. A recusa e alta de proposito: ver a "
            "P6-11 e o docstring desta excecao."
        )
        self.campo = campo
        self.caso = caso
        self.valor = valor


@dataclass(frozen=True)
class CasoDeGabarito:
    """Um caso da Linha B, como `03` §5.2 o descreve.

    `conjunto` NAO e derivavel de `defensibilidade`, e por isso e campo. A tabela
    de §5.2 associa 1.0 ao indevido comprovado, mas `defensibility` e um numero
    livre em [0,1] no contrato: um pack que escrevesse 0.7 tornaria a derivacao
    silenciosamente errada, e a lacuna de cobertura passaria a apontar para o
    caso errado.
    """

    defensibilidade: float
    conjunto: str


@dataclass(frozen=True)
class Sinal:
    """Uma sinalizacao comportamental de `03` §5.4, com o caso que a produziu."""

    caso: str
    confianca: int
    defensibilidade: float


@dataclass(frozen=True)
class Calibracao:
    """O escore e os sinais, SEPARADOS — `03` §5.4 proibe compensar.

    `brier` e `None` quando nenhum caso esta no escopo: nao ha media de conjunto
    vazio, e devolver `0.0` seria o melhor escore possivel para a equipe que nao
    declarou escopo nenhum — exatamente ao contrario.
    """

    brier: float | None
    casos_no_escore: tuple[str, ...] = ()
    overconfidence: tuple[Sinal, ...] = ()
    underconfidence: tuple[Sinal, ...] = ()
    lacunas_de_cobertura: tuple[str, ...] = ()

    #: Casos do escopo que a equipe nao avaliou. Entram no Brier como
    #: `confidence = 0`, e ficam nomeados porque o AAR precisa distinguir
    #: "avaliou com confianca zero" de "nao avaliou".
    nao_avaliados: tuple[str, ...] = field(default=())


def brier(
    submissoes: Sequence[Event],
    *,
    defensibilidade: Mapping[str, float],
    escopo: frozenset[str],
) -> float | None:
    """A media dos quadrados de `03` §5.3, sobre o escopo revisado.

    SEPARADO de `escore` porque tem DOIS consumidores: o escore completo, que o
    reporta ao lado dos sinais, e o computador de `TTIV`, que o recalcula a cada
    submissao para achar o instante em que ele cruza o limiar de calibracao
    (`03` §3.3). Escrita duas vezes, a formula divergiria — a classe D4.

    Ele pede `defensibilidade` e nao `CasoDeGabarito`: o Brier nao usa o
    `conjunto`, e quem o exige e a lacuna de cobertura. Pedir o que nao se usa
    faria o consumidor de `TTIV` carregar dado que ele nao tem — o insumo de
    `00` §3.2 traz a defensibilidade por caso, e nao o conjunto.

    `None` quando nao ha caso no escopo: nao ha media de conjunto vazio, e `0.0`
    seria o MELHOR escore possivel para quem nao declarou escopo nenhum.
    """
    declaradas = _por_caso(submissoes)
    quadrados = [
        (declaradas.get(caso, CONFIANCA_DE_NAO_AVALIADO) / 100 - defensibilidade[caso])
        ** 2
        for caso in sorted(escopo)
        if caso in defensibilidade
    ]
    return (sum(quadrados) / len(quadrados)) if quadrados else None


def escore(
    submissoes: Sequence[Event],
    *,
    gabarito: Mapping[str, CasoDeGabarito],
    escopo: frozenset[str],
) -> Calibracao:
    """O Brier sobre o escopo revisado, mais os tres sinais de `03` §5.4.

    `submissoes` sao os `assessment_submitted` do fluxo. Eventos de outro tipo
    sao ignorados em vez de recusados: o chamador entrega o insumo do lado dele,
    e recortar por tipo aqui e o mesmo recorte que os computadores de metrica
    fazem — no consumidor, e nao numa consulta compartilhada.

    A ULTIMA submissao de cada caso e a que vale. Reavaliar um caso e revisar o
    juizo, e `03` §5 mede o juizo com que a equipe FICOU — ao contrario das
    metricas de `03` §3, onde a PRIMEIRA declaracao marca o instante porque o que
    se mede la e o tempo ate declarar.
    """
    declaradas = _por_caso(submissoes)

    no_escore: list[str] = []
    nao_avaliados: list[str] = []
    overconfidence: list[Sinal] = []
    underconfidence: list[Sinal] = []

    for caso in sorted(escopo):
        alvo = gabarito.get(caso)
        if alvo is None:
            # Caso no escopo declarado e ausente do gabarito. Nao entra no Brier:
            # nao ha `defensibility` contra a qual comparar, e inventar uma
            # produziria nota a partir de nada.
            continue

        confianca = declaradas.get(caso, CONFIANCA_DE_NAO_AVALIADO)
        if caso not in declaradas:
            nao_avaliados.append(caso)

        no_escore.append(caso)

        sinal = Sinal(
            caso=caso, confianca=confianca, defensibilidade=alvo.defensibilidade
        )
        if confianca >= CONFIANCA_ALTA and alvo.defensibilidade <= DEFENSIBILIDADE_BAIXA:
            overconfidence.append(sinal)
        if confianca <= CONFIANCA_BAIXA and alvo.defensibilidade == DEFENSIBILIDADE_TOTAL:
            underconfidence.append(sinal)

    return Calibracao(
        brier=brier(
            submissoes,
            defensibilidade={c: a.defensibilidade for c, a in gabarito.items()},
            escopo=escopo,
        ),
        casos_no_escore=tuple(no_escore),
        overconfidence=tuple(overconfidence),
        underconfidence=tuple(underconfidence),
        lacunas_de_cobertura=_lacunas(gabarito, escopo),
        nao_avaliados=tuple(nao_avaliados),
    )


def _por_caso(submissoes: Sequence[Event]) -> dict[str, int]:
    """`case_id -> confidence` da ULTIMA submissao de cada caso, na ordem do fluxo.

    **RECUSA payload que o contrato proibe** — `SubmissaoForaDoContrato`, e o
    argumento inteiro esta la. A versao anterior ignorava, e o docstring dela dizia
    que um evento malformado *"o contrato ja recusa na entrada"*. A P6-11 mediu que
    nao recusa: o event store nao valida payload, e isso vale para todo evento.

    A guarda mora AQUI, e nao em `escore`, porque os dois consumidores passam por
    ela: o escore completo e o `brier` que o computador de `TTIV` (`03` §3.3)
    recalcula a cada prefixo. Em `escore`, o caminho de `TTIV` seguiria cru.
    """
    correntes: dict[str, int] = {}
    for evento in submissoes:
        if evento.event_type != ASSESSMENT_SUBMITTED:
            continue
        caso = evento.payload.get(CASO)
        confianca = evento.payload.get(CONFIANCA)
        if not isinstance(caso, str):
            raise SubmissaoForaDoContrato(CASO, None, caso)
        if not _confianca_conforme(confianca):
            raise SubmissaoForaDoContrato(CONFIANCA, caso, confianca)
        correntes[caso] = confianca
    return correntes


def _confianca_conforme(valor: object) -> bool:
    """`integer 0..100`, como `assessment.schema.yaml` a escreve.

    `bool` sai explicitamente: `isinstance(True, int)` e verdadeiro em Python e
    JSON nao tem essa ponte. Sem esta linha, `True` entraria valendo `1` — numero
    plausivel, e por isso pior que um erro.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        return False
    return CONFIANCA_MINIMA <= valor <= CONFIANCA_MAXIMA


def _lacunas(
    gabarito: Mapping[str, CasoDeGabarito], escopo: frozenset[str]
) -> tuple[str, ...]:
    """Indevido comprovado FORA do escopo revisado — `03` §5.4, terceira linha.

    *"Investigacao nao chegou la."* E reportado em separado e **nao** como falso
    negativo: a equipe nao errou o julgamento do caso, ela nao o julgou. Somar as
    duas coisas diria que quem olhou e errou e quem nao olhou cometeram a mesma
    falha.
    """
    return tuple(
        sorted(
            caso
            for caso, alvo in gabarito.items()
            if alvo.conjunto == CONJUNTO_INDEVIDO and caso not in escopo
        )
    )
