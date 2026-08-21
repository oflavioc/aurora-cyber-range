"""A projecao `aar_timeline` — as janelas dos pares, e a divergencia entre avaliadores.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §2.4 (divergencia) e §3.2 (o delta e o achado);
`00_MASTER_SPEC.md` §3.2; `01_ARCHITECTURE.md` §4.1.

POR QUE A JANELA MORA AQUI, E NAO NUM COMPUTADOR DE METRICA
------------------------------------------------------------
A janela de asseguracao prematura **cruza declaracao com verificacao**: ela vai
de `TTCD` a `TTCV`. Nenhum dos dois computadores pode calcula-la, porque nenhum
dos dois tem as duas metades — e essa e a particao inteira de `00` §3.2.

*"`aar_timeline` e o escopo que recebe as duas metades de cada par e computa os
deltas."* Este modulo e ele. A colocacao nao e organizacao: e a consequencia
direta da regra que impede `TTCD` de ser computado a partir de `TTCV`.

**Fase 6 computa, Fase 10 renderiza.** A prova de que a divisao existe e o teste
nomeado sobre a saida daqui — sem ele, "o AAR faz isso" seria afirmacao sobre uma
fase que ainda nao chegou, que e a forma de um requisito morrer sem nada ficar
vermelho.

ELE RECEBE O FLUXO, E ISSO NAO FURA A PARTICAO
-----------------------------------------------
`00` §3.2 particiona o insumo **dos computadores de metrica**. A `aar_timeline`
nao e um deles: ela e a projecao que junta o que eles produziram. Ler o fluxo e o
que `01` §4.1 espera de toda projecao — a leitura do store e total, e o
estreitamento e de quem estreita.

O que ela **nao** faz e recomputar metrica. As `Medida` chegam prontas, dos dois
computadores, com o decorrido ja descontado; refaze-las aqui seria a terceira
implementacao do desconto por uniao.

AS TRES JANELAS, E AS DUAS PRIMEIRAS SAO O MESMO DELTA COM SINAIS OPOSTOS
--------------------------------------------------------------------------
`03` §3.2 escreve os dois sentidos:

- **declaracao < verificacao** — *asseguracao prematura*. A janela e o tempo em
  que a instituicao operou **acreditando estar contida sem estar**, e o AAR lista
  os eventos de `ground_truth` ocorridos dentro dela como **evidencias
  incompativeis com a declaracao**;
- **declaracao > verificacao** — *lacuna de consciencia situacional*. A equipe
  estava contida e nao sabia; manteve degradacao desnecessaria.

A terceira e de outra natureza e vem da peca 3: a **declaracao de integridade sem
contrassinatura**. `03` §3.4 diz que ela e gravada e que a ausencia do segundo ato
e **achado do AAR, e nao erro de emissao** — entao ela chega aqui, ao lado das
outras duas, que e o endereco que o registro da fase ja lhe deu.

`03` §3.2 ESCREVE CONTENCAO, E ESTE MODULO APLICA AOS TRES PARES
-----------------------------------------------------------------
A redacao-alvo da §3.2 e sobre contencao, e o exemplo tambem. Mas a secao se
chama *"o delta e o achado, nos dois sentidos"*, e `03` §3 define **tres** pares —
a forma e identica nos tres, e o delta e o achado em todos.

Restringir a contencao exigiria uma razao, e nao ha: integridade declarada antes
de verificavel e exatamente a mesma leitura, sobre a coisa que `02` §6.2 diz custar
mais caro. A generalizacao esta escrita aqui para ser lida como decisao, e nao
deduzida da ausencia de restricao.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from contracts.generated.events import (
    BARS_SCORE_SUBMITTED,
    INTEGRITY_VALIDATION_DECLARED,
)

from range_core.declarations.contrassinatura import completa
from range_core.events.envelope import Event
from range_core.metrics.epoch import instante
from range_core.metrics.medida import Medida

#: A CAMADA das evidencias incompativeis — `03` §3.2 diz *"os `ground_truth`
#: eventos ocorridos dentro dessa janela"*, e nao "os eventos".
#:
#: A distincao e o ponto: o que torna a declaracao prematura e o MUNDO ter
#: continuado a se mover, e nao a equipe ter continuado a agir. Listar acao de
#: participante aqui misturaria a primeira camada de `00` §3 com a terceira.
CAMADA_DE_GROUND_TRUTH = "ground_truth"

#: As chaves do payload de `bars_score_submitted` — `events.schema.yaml`,
#: `bars_score_payload`.
COMPETENCIA = "competency"
NOTA = "score"

#: `03` §2.4 — *"divergencia >= 2 pontos na mesma competencia gera alerta"*.
#: Na escala `0-4` da rubrica, dois pontos sao metade da amplitude: e a distancia
#: a partir da qual dois avaliadores nao estao mais lendo a mesma ancora.
DIVERGENCIA_QUE_ALERTA = 2

#: Os tres pares de `03` §3 — declaracao, verificacao. A ordem e a da tabela.
PARES: tuple[tuple[str, str], ...] = (
    ("TTCD", "TTCV"),
    ("TTRD", "TTRV"),
    ("TTID", "TTIV"),
)

ASSEGURACAO_PREMATURA = "asseguracao_prematura"
LACUNA_DE_CONSCIENCIA = "lacuna_de_consciencia_situacional"
SEM_CONTRASSINATURA = "sem_contrassinatura"


@dataclass(frozen=True)
class Janela:
    """Um trecho do exercicio que o AAR imprime como achado.

    `fim is None` e janela ABERTA, e hoje so a de contrassinatura a produz: o
    segundo ato nunca veio, entao nao ha instante que a feche. Fecha-la no fim do
    exercicio inventaria um fato — a declaracao nao passou a estar contrassinada
    quando o exercicio acabou.
    """

    tipo: str
    par: tuple[str, str] | None
    inicio: datetime
    fim: datetime | None
    incompativeis: tuple[Event, ...] = ()

    @property
    def aberta(self) -> bool:
        return self.fim is None


@dataclass(frozen=True)
class AlertaDeDivergencia:
    """`03` §2.4 — *"nao resolve automaticamente; sinaliza para o debriefing"*.

    Por isso o alerta carrega os dois extremos e QUEM os deu, e nao uma nota
    consolidada: consolidar seria resolver, e a §2.4 diz explicitamente que o
    mecanismo nao resolve.
    """

    competencia: str
    menor: int
    maior: int
    avaliadores: tuple[str, ...]

    @property
    def distancia(self) -> int:
        return self.maior - self.menor


@dataclass(frozen=True)
class Timeline:
    """O que a Fase 6 computa e a Fase 10 renderiza."""

    janelas: tuple[Janela, ...] = ()
    divergencias: tuple[AlertaDeDivergencia, ...] = ()


def compoe(
    fluxo: Sequence[Event],
    *,
    declaracao: Sequence[Medida],
    verificacao: Sequence[Medida],
) -> Timeline:
    """A timeline do AAR: as janelas dos tres pares, mais a divergencia.

    As `Medida` chegam PRONTAS dos dois computadores — este e o unico escopo que
    recebe as duas metades, e e por isso que o delta e computado aqui.
    """
    por_sigla = {m.sigla: m for m in declaracao} | {m.sigla: m for m in verificacao}

    janelas = [
        janela
        for par in PARES
        if (janela := _janela_do_par(fluxo, par, por_sigla)) is not None
    ]
    janelas.extend(_janelas_sem_contrassinatura(fluxo))

    return Timeline(
        janelas=tuple(sorted(janelas, key=lambda j: (j.inicio, j.tipo))),
        divergencias=_divergencias(fluxo),
    )


def _janela_do_par(
    fluxo: Sequence[Event],
    par: tuple[str, str],
    por_sigla: dict[str, Medida],
) -> Janela | None:
    """O delta entre as duas metades, nos dois sentidos de `03` §3.2.

    **Falta qualquer uma das duas e nao ha janela.** Nao e o mesmo que janela de
    tamanho zero: sem a declaracao nao houve asseguracao nenhuma, e sem o veredito
    nao se sabe se ela era prematura. Uma janela vazia aqui apareceria no AAR como
    achado onde nao ha nem medicao.

    Delta ZERO tambem nao produz janela: declarar no mesmo instante em que o
    predicado passa a valer nao e nem prematuro nem lacuna, e `03` §3.2 so nomeia
    os dois sentidos.
    """
    sigla_declaracao, sigla_verificacao = par
    declarada = por_sigla.get(sigla_declaracao)
    verificada = por_sigla.get(sigla_verificacao)
    if declarada is None or verificada is None:
        return None
    if not declarada.marcada or not verificada.marcada:
        return None

    if declarada.fim < verificada.fim:
        tipo, inicio, fim = ASSEGURACAO_PREMATURA, declarada.fim, verificada.fim
    elif declarada.fim > verificada.fim:
        tipo, inicio, fim = LACUNA_DE_CONSCIENCIA, verificada.fim, declarada.fim
    else:
        return None

    return Janela(
        tipo=tipo,
        par=par,
        inicio=inicio,
        fim=fim,
        incompativeis=_incompativeis(fluxo, inicio, fim, tipo),
    )


def _incompativeis(
    fluxo: Sequence[Event], inicio: datetime, fim: datetime, tipo: str
) -> tuple[Event, ...]:
    """Os eventos de `ground_truth` DENTRO da janela — `03` §3.2.

    So na ASSEGURACAO PREMATURA. Na lacuna de consciencia a equipe estava contida
    e nao sabia: os eventos do intervalo nao contradizem declaracao nenhuma,
    porque nao havia declaracao ainda. Chama-los de incompativeis inverteria o
    achado — a §3.2 da a essa janela outra leitura, *"manteve degradacao
    desnecessaria"*, e ela e sobre custo e nao sobre contradicao.

    Os extremos entram: `inicio` e o instante da declaracao e `fim` o do veredito,
    e evento gravado no mesmo segundo da declaracao ja e posterior a ela na ordem
    do fluxo. Recorta-los abriria buraco de um segundo em cada ponta.
    """
    if tipo != ASSEGURACAO_PREMATURA:
        return ()
    return tuple(
        evento
        for evento in fluxo
        if evento.truth_layer == CAMADA_DE_GROUND_TRUTH
        and inicio <= instante(evento) <= fim
    )


def _janelas_sem_contrassinatura(fluxo: Sequence[Event]) -> list[Janela]:
    """Declaracao de integridade que abriu o par e ninguem completou — `03` §3.4.

    A clausula herdada, do lado do AAR. A declaracao **fica registrada**, e a
    ausencia de contrassinatura e achado daqui — nao erro de emissao, e nao
    ausencia de metrica: `TTID` ja nao marcou, no computador da declaracao, e o
    que sobra e a janela.

    O predicado e o MESMO de `range-core/declarations/contrassinatura.py`, que o
    emissor e o computador de `TTID` tambem usam. Tres consumidores, uma
    implementacao.
    """
    integridades = sorted(
        (e for e in fluxo if e.event_type == INTEGRITY_VALIDATION_DECLARED),
        key=instante,
    )
    completadas = {
        evento.correlation.causation_id
        for posicao, evento in enumerate(integridades)
        if completa(evento, integridades[:posicao])
    }
    return [
        Janela(
            tipo=SEM_CONTRASSINATURA,
            par=None,
            inicio=instante(evento),
            fim=None,
        )
        for evento in integridades
        if evento.correlation.causation_id is None
        and evento.event_id not in completadas
    ]


def _divergencias(fluxo: Sequence[Event]) -> tuple[AlertaDeDivergencia, ...]:
    """`03` §2.4 — divergencia `>= 2` pontos na mesma competencia.

    A DISTANCIA E ENTRE OS EXTREMOS, e nao entre pares consecutivos: com tres
    avaliadores dando 0, 1 e 2, nenhum par consecutivo alcanca dois pontos e o
    conjunto alcanca. A §2.4 fala da divergencia NA COMPETENCIA, e ela e a
    amplitude.

    A ULTIMA nota de cada avaliador vale, como no escore de calibracao: revisar a
    nota e revisar o juizo, e o AAR sinaliza o juizo com que o avaliador ficou.
    """
    notas: dict[str, dict[str, int]] = {}
    for evento in fluxo:
        if evento.event_type != BARS_SCORE_SUBMITTED:
            continue
        competencia = evento.payload.get(COMPETENCIA)
        nota = evento.payload.get(NOTA)
        if not isinstance(competencia, str) or not isinstance(nota, int):
            continue
        if evento.actor_id is None:
            continue
        notas.setdefault(competencia, {})[evento.actor_id] = nota

    alertas = []
    for competencia, por_avaliador in sorted(notas.items()):
        if len(por_avaliador) < 2:
            continue
        valores = por_avaliador.values()
        menor, maior = min(valores), max(valores)
        if maior - menor < DIVERGENCIA_QUE_ALERTA:
            continue
        alertas.append(
            AlertaDeDivergencia(
                competencia=competencia,
                menor=menor,
                maior=maior,
                avaliadores=tuple(sorted(por_avaliador)),
            )
        )
    return tuple(alertas)
