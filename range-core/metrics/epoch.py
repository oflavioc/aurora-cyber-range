"""Epoch como CALCULO do consumidor — o desconto por uniao e o descarte de `rehearsal`.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §3.2, bloco *"Epoch e computacao do consumidor, nunca recorte
na montagem"*; `09_EVENT_MODEL.md` §3.1; `03_EXERCISE_DESIGN.md` §3.5;
`06_ACCEPTANCE_TESTS.md` T10.

POR QUE ISTO E UM MODULO, E NAO UM RECORTE NO MONTADOR
------------------------------------------------------
`range-core/metrics/insumo.py` entrega a escrituracao de epoch INTEIRA aos dois
lados, de proposito. O desconto mora aqui porque a §3.2 exige que ele seja
*"codigo do consumidor, visivel e testado"*, e diz o que se perde na outra
colocacao: recortada na montagem, a regra passa a ser propriedade do montador, o
numero certo aparece por **ausencia de insumo** em vez de por calculo, e evento
perdido por defeito fica indistinguivel de evento corretamente descontado.

E modulo compartilhado pelos dois computadores, e nao codigo repetido em cada um,
pelo motivo da D4: duas implementacoes da mesma regra divergem em silencio.
Compartilhar o calculo nao o tira do consumidor — ele continua sendo chamado
pelo computador, sobre insumo que o computador recebeu.

AS DUAS REGRAS, E ELAS SAO DIFERENTES
--------------------------------------
`09` §3.1 da a cada `reason` um efeito proprio, e so dois deles chegam ate aqui:

- **`technical_failure`** congela o relogio entre o inject falho e a retomada. O
  intervalo e **descontado**, e a equipe nao e penalizada por bug do ambiente.
- **`rehearsal`** descarta a epoch: *"nenhum evento da epoch entra em calculo"*.
  Nao e desconto de tempo — e exclusao de evento, e por isso as duas regras nao
  se reduzem uma a outra.

`facilitation` e `adjudication` nao produzem desconto nem descarte: as metricas
sao recomputadas a partir da nova epoch, com nota, e a nota e do AAR.

UNIAO, NUNCA SOMA — E E POR ISSO QUE O REGISTRO E POR EXTREMOS
---------------------------------------------------------------
Dois congelamentos que se sobrepoem contam o trecho comum **duas vezes** se as
duracoes forem somadas, e a duracao ja somada nao guarda com que detectar isso.
`06` T3 fixa o registro por extremos exatamente para tornar a uniao possivel, e
T10 exige a uniao por nome.

O RELOGIO E `exercise_timestamp`, E OS OUTROS TRES FORAM DESCARTADOS
---------------------------------------------------------------------
`06` T3 percorre os quatro e explica cada recusa. `wall_timestamp` nao, porque o
PAUSAR o avanca sem avancar o exercicio; `exercise_time` nao, porque rebobina no
rollback — os dois extremos de um congelamento caem em epochs diferentes **por
construcao**, e a uniao e operacao de ordem total entre extremos de rollbacks
distintos; duracao nao, pelo paragrafo acima.

**A PAUSA NAO PRECISA DE DESCONTO, e a ausencia e consequencia e nao esquecimento:**
`exercise_timestamp` nao avanca durante o pausar. Descontar a pausa aqui a
contaria duas vezes. E o mesmo fato que descarta `wall_timestamp`, visto do outro
lado.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from contracts.generated.events import EXERCISE_STARTED, ROLLBACK_PERFORMED

from range_core.clock.exercise_clock import label_seconds
from range_core.events.envelope import Event
from range_core.events.epoch import current_epoch
from range_core.metrics.insumo import EscrituracaoDeEpoch

#: Os dois `reason` que produzem efeito de metrica. O enum completo vive em
#: `contracts/events.schema.yaml` (`$defs/rollback_reason`), e
#: `tests/test_metrics_epoch.py` cruza estas constantes com ele — motivo novo no
#: contrato sem decisao aqui reprova, em vez de cair em nenhum dos dois ramos e
#: sumir.
MOTIVO_FALHA_TECNICA = "technical_failure"
MOTIVO_ENSAIO = "rehearsal"
MOTIVO_FACILITACAO = "facilitation"
MOTIVO_ADJUDICACAO = "adjudication"

#: OS MOTIVOS QUE REINICIAM A CONTAGEM DE EVENTOS. `09` §3.1 diz das duas linhas
#: a mesma coisa com palavras diferentes — *"metricas recomputadas a partir da
#: nova epoch, com nota"* e *"metricas da nova epoch, com registro do motivo da
#: anulacao"*. As epochs ate a do rollback saem do calculo; a nota e o registro
#: sao do AAR.
MOTIVOS_QUE_REINICIAM = frozenset({MOTIVO_FACILITACAO, MOTIVO_ADJUDICACAO})


class JanelaInvertida(ValueError):
    """Fim antes do inicio. Nao e caso de dominio, e defeito de quem chamou.

    `exercise_timestamp` nao rebobina — e a razao de ele existir —, entao uma
    janela invertida so nasce de start e stop trocados no computador. Devolver
    zero ou um negativo esconderia isso dentro de um numero que o AAR imprime.
    """


class SemMarcoZero(ValueError):
    """Nao ha `exercise_started` no fluxo, e T0 nao pode ser derivado.

    Levanta em vez de devolver `None`: T0 ausente faria todo decorrido virar
    nulo, e o AAR imprimiria ausencia de medicao onde houve medicao — a
    degradacao silenciosa que a P2-19 recusou.

    **O gatilho mudou com a P6-4.** Ele era o ensaio descartado, e deixou de ser:
    T0 e atributo do exercicio e sobrevive ao descarte de qualquer epoch. O que
    resta e o caso honesto — metrica computada sobre fluxo em que o exercicio
    nunca comecou.
    """


@dataclass(frozen=True)
class Congelamento:
    """Um intervalo de relogio congelado, pelos extremos.

    Em `datetime`, e nao na string do envelope: a uniao compara e ordena, e
    comparacao de string so coincide com comparacao de instante enquanto o
    formato for exatamente o mesmo em todo produtor.
    """

    inicio: datetime
    fim: datetime

    @property
    def duracao(self) -> timedelta:
        return self.fim - self.inicio


def epochs_descartadas(escrituracao: EscrituracaoDeEpoch) -> frozenset[int]:
    """As epochs que um rollback `rehearsal` descartou.

    **A epoch descartada e a do proprio `rollback_performed`**, e nao a seguinte:
    o store carimba a epoch ANTES do append — `current_epoch` conta os rollbacks
    ja gravados —, entao o evento de rollback carrega a epoch que ele encerra.
    E o que `09` §3 desenha, com o evento dentro da epoch que fecha.
    """
    return frozenset(
        evento.simulation_epoch
        for evento in escrituracao
        if evento.event_type == ROLLBACK_PERFORMED
        and evento.payload.get("reason") == MOTIVO_ENSAIO
    )


def no_calculo(
    eventos: Sequence[Event], descartadas: frozenset[int]
) -> tuple[Event, ...]:
    """Os eventos que entram em calculo — os de epoch descartada ficam de fora.

    Vale para os eventos do LADO, e nao so para a escrituracao: `09` §3.1 diz
    *"nenhum evento da epoch entra em calculo"*, sem restringir a especie. E a
    razao de a escrituracao ir aos dois lados — sem ela, o computador da
    declaracao nao teria como saber que a epoch dele foi descartada, e o
    montador teria de recortar por ele.
    """
    return tuple(e for e in eventos if e.simulation_epoch not in descartadas)


def epochs_em_calculo(escrituracao: EscrituracaoDeEpoch) -> frozenset[int]:
    """As epochs cujos eventos contam para as metricas — os QUATRO motivos.

    `09` §3.1 da a cada `reason` um efeito proprio sobre as metricas, e os quatro
    sao diferentes. Implementar so os dois que `06` T10 nomeia deixaria os outros
    dois sem mecanismo, e eles sao norma viva:

    - `rehearsal` — *"nenhum evento da epoch entra em calculo"*: a epoch sai;
    - `facilitation` e `adjudication` — *"metricas recomputadas a partir da nova
      epoch"*: tudo ate a epoch do rollback sai;
    - `technical_failure` — a linha NAO manda descartar epoch nenhuma. Ela diz
      *"relogio congelado"* e *"a equipe nao e penalizada por bug do ambiente"*, e
      descartar as declaracoes anteriores penalizaria exatamente por isso: a
      equipe teria de redeclarar o que ja declarara. So o TEMPO e descontado.

    A assimetria entre os tres primeiros e o quarto e a informacao que a linha
    *"o que difere entre eles e o que o consumidor de metrica faz com as epochs"*
    carrega — e este e o consumidor.
    """
    corrente = current_epoch(escrituracao)
    descartadas = epochs_descartadas(escrituracao)

    piso = 0
    for evento in escrituracao:
        if (
            evento.event_type == ROLLBACK_PERFORMED
            and evento.payload.get("reason") in MOTIVOS_QUE_REINICIAM
        ):
            piso = max(piso, evento.simulation_epoch + 1)

    return frozenset(
        n for n in range(corrente + 1) if n >= piso and n not in descartadas
    )


def apenas(eventos: Sequence[Event], epochs: frozenset[int]) -> tuple[Event, ...]:
    """Os eventos cujas epochs contam. O par de `epochs_em_calculo`.

    Separado de `no_calculo` de proposito: aquele responde *"esta epoch foi
    descartada?"*, e este *"esta epoch conta?"*. Sao perguntas diferentes desde
    que `facilitation` entrou, e uma funcao so com dois sentidos e onde o
    proximo leitor erra.
    """
    return tuple(e for e in eventos if e.simulation_epoch in epochs)


def congelamentos(escrituracao: EscrituracaoDeEpoch) -> tuple[Congelamento, ...]:
    """Os intervalos descontados, de **dois** motivos, ja unidos e em ordem.

    A uniao acontece aqui, uma vez, e nao em cada chamador: dois chamadores que
    a fizessem por conta propria seriam duas implementacoes da mesma regra. E e
    por ela que os dois motivos entram na MESMA tabela em vez de num caminho
    paralelo — sobrepostos, o trecho comum e contado uma vez.

    `technical_failure` — o congelamento registrado por extremos no payload.
    Intervalo registrado em epoch descartada NAO entra por aqui: ele ja esta
    dentro do intervalo do ensaio, e a uniao o absorveria de qualquer forma.

    `rehearsal` — **P6-4**. O ensaio descartado consumiu tempo de exercicio, e
    esse tempo esta embutido no `exercise_timestamp` de tudo o que veio depois:
    o relogio nao rebobina no rollback, so o rotulo `T+` rebobina. Como T0
    sobrevive ao descarte, sem este desconto o ensaio inteiro entraria em toda
    metrica medida desde T0.

    E o multiplicador e a razao de o desconto ser POR EXTREMOS DE
    `exercise_timestamp` e nao por tempo de parede: um ensaio de dez minutos a
    20x consome duzentos minutos de exercicio, e sao os duzentos que precisam
    sair. Medidos nos dois extremos, saem exatos, sem que o multiplicador
    apareca na conta.
    """
    descartadas = epochs_descartadas(escrituracao)
    brutos = [
        _intervalo(evento)
        for evento in no_calculo(escrituracao, descartadas)
        if evento.event_type == ROLLBACK_PERFORMED
        and evento.payload.get("reason") == MOTIVO_FALHA_TECNICA
    ]
    brutos.extend(_intervalos_de_ensaio(escrituracao, descartadas))
    return uniao(brutos)


def _intervalos_de_ensaio(
    escrituracao: EscrituracaoDeEpoch, descartadas: frozenset[int]
) -> list[Congelamento]:
    """Um intervalo por epoch descartada por `rehearsal` — P6-4.

    A epoch descartada vai do inicio dela ate o rollback que a fecha:

    - **fim** e o `exercise_timestamp` do proprio rollback de `rehearsal`, que
      carrega a epoch que encerra;
    - **inicio** e o `exercise_timestamp` do rollback que fechou a epoch
      ANTERIOR — ou **T0**, para a epoch 0, que nao tem anterior.

    Os dois extremos saem da escrituracao e de T0, e nao de campo novo no
    payload: `frozen_interval` e do `technical_failure`, onde o facilitador
    registra o trecho em que o range esteve quebrado. Aqui o trecho e a epoch
    inteira, e ela ja esta descrita pelos rollbacks que a delimitam — pedir ao
    facilitador que o repita seria segunda fonte para o mesmo fato.
    """
    if not descartadas:
        return []

    fecha: dict[int, datetime] = {}
    abre: dict[int, datetime] = {}
    for evento in escrituracao:
        if evento.event_type != ROLLBACK_PERFORMED:
            continue
        # O rollback carrega a epoch que ENCERRA, entao ele abre a seguinte.
        abre[evento.simulation_epoch + 1] = instante(evento)
        if evento.payload.get("reason") == MOTIVO_ENSAIO:
            fecha[evento.simulation_epoch] = instante(evento)

    intervalos: list[Congelamento] = []
    for epoch in sorted(descartadas):
        fim = fecha.get(epoch)
        inicio = abre.get(epoch) if epoch > 0 else marco_zero(escrituracao)
        if fim is None or inicio is None or fim <= inicio:
            continue
        intervalos.append(Congelamento(inicio=inicio, fim=fim))
    return intervalos


def uniao(intervalos: Iterable[Congelamento]) -> tuple[Congelamento, ...]:
    """Funde os que se tocam ou se sobrepoem. NUNCA soma duracoes.

    Adjacencia exata funde junto — `fim == inicio` do seguinte —, e nao e
    detalhe: dois congelamentos encostados descrevem um unico trecho de relogio
    parado, e mante-los separados nao muda a medida mas faz a saida descrever
    mal o que houve.
    """
    ordenados = sorted(intervalos, key=lambda c: (c.inicio, c.fim))
    fundidos: list[Congelamento] = []
    for atual in ordenados:
        if fundidos and atual.inicio <= fundidos[-1].fim:
            anterior = fundidos[-1]
            if atual.fim > anterior.fim:
                fundidos[-1] = Congelamento(anterior.inicio, atual.fim)
            continue
        fundidos.append(atual)
    return tuple(fundidos)


def decorrido(
    inicio: datetime, fim: datetime, congelados: Sequence[Congelamento]
) -> timedelta:
    """A distancia entre dois instantes, **menos** o relogio congelado no meio.

    Os congelamentos sao RECORTADOS a janela antes de descontar. Um que comece
    antes do start ou termine depois do stop so desconta a parte que cai dentro
    — descontar inteiro subtrairia tempo que a metrica nunca contou, e produziria
    numero menor que o real sem nada acusar.

    Espera `congelados` **ja unidos** (`congelamentos` devolve assim). Sobre
    intervalos crus com sobreposicao, o resultado seria a soma — que e o defeito
    que T10 proibe por nome.
    """
    if fim < inicio:
        raise JanelaInvertida(
            f"janela de metrica invertida: stop {fim.isoformat()} antes do start "
            f"{inicio.isoformat()}. `exercise_timestamp` nao rebobina, entao isto "
            "e start e stop trocados no computador, e nao rollback."
        )

    congelado = timedelta()
    for intervalo in congelados:
        recorte_inicio = max(intervalo.inicio, inicio)
        recorte_fim = min(intervalo.fim, fim)
        if recorte_fim > recorte_inicio:
            congelado += recorte_fim - recorte_inicio
    return (fim - inicio) - congelado


def instante(evento: Event) -> datetime:
    """O instante de um evento na ordem total do exercicio.

    Um so lugar converte, e os computadores nao repetem `fromisoformat`: e o
    ponto onde a escolha de `exercise_timestamp` — e a recusa dos outros tres
    relogios de `06` T3 — fica visivel em vez de espalhada.
    """
    return datetime.fromisoformat(evento.exercise_timestamp)


def _intervalo(evento: Event) -> Congelamento:
    """O `frozen_interval` de um `rollback_performed`, em `datetime`.

    A ausencia do campo NAO e tratada com default: o contrato o exige quando
    `reason` e `technical_failure` (`events.schema.yaml`, o `if/then` do
    `rollback_payload`), e um `KeyError` aqui aponta para o contrato violado. Um
    `.get` com fallback transformaria contrato quebrado em desconto zero — e o
    desconto sumiria sem nada acusar, que e o buraco que aquele `if/then` existe
    para fechar.
    """
    bruto = evento.payload["frozen_interval"]
    return Congelamento(
        inicio=datetime.fromisoformat(bruto["start"]),
        fim=datetime.fromisoformat(bruto["end"]),
    )


def marco_zero(escrituracao: EscrituracaoDeEpoch) -> datetime:
    """T0 — o zero do relogio de exercicio, RECUPERADO do `exercise_started`.

    **NAO e o `exercise_timestamp` do evento.** `01` §3 poe T0 na mao do
    facilitador, e o evento e gravado alguns instantes depois; usar a marca dele
    como zero embutiria a latencia de emissao em toda metrica do exercicio, sem
    nada acusar. Medido: foi o que a primeira versao desta funcao fazia, e o
    teste de T0 a pegou.

    `01` §4.4 da a identidade que o recupera exatamente —
    `exercise_timestamp == T0 + exercise_time` —, entao T0 e a marca MENOS o
    rotulo. Quem le o rotulo e `label_seconds`, do proprio relogio: o formato
    `T+HH:MM:SS` tem um dono so, e uma segunda leitura aqui seria a classe D4.

    POR QUE A IDENTIDADE SE SUSTENTA AQUI, MEDIDO NO RELOGIO
    ---------------------------------------------------------
    `marks()` calcula `exercise_time = _label(elapsed - epoch_started_at)` e
    `exercise_timestamp = T0 + elapsed`. A identidade so vale onde
    `epoch_started_at == 0`, que e a **epoch 0** — e o `exercise_started` que
    abre o exercicio e anterior a qualquer rollback, entao vive nela.

    O truncamento tambem fecha: `_label` trunca ao segundo e o `isoformat` do
    timestamp usa `timespec="seconds"`. Os dois truncam o MESMO `elapsed` ao
    mesmo segundo, e a subtracao devolve T0 exato.

    T0 NAO PERTENCE A EPOCH NENHUMA — P6-4
    ---------------------------------------
    **Decisao do proprietario.** T0 e atributo do EXERCICIO: `01` §3 o poe na mao
    do facilitador, e o `exercise_started` **registra o ato, nao e a fonte dele**.
    Por isso a busca varre a escrituracao inteira e nao filtra por epoch
    descartada — o descarte de `09` §3.1 tira EVENTOS do calculo, e T0 nao e um
    evento: e o zero contra o qual os eventos sao medidos.

    As duas alternativas caem por merito, e ficam escritas para nao voltarem:

    - **T0 do `exercise_started` da epoch nova** encolheria `TTA`, `TTT` e `TTCM`
      pelo tempo do ensaio, silenciosamente — as tres tem start proprio, e o
      start deslocaria junto;
    - **T0 do evento descartado, com o evento em calculo** contradiz `09` §3.1 na
      letra: *"nenhum evento da epoch entra em calculo"*.

    O tempo que o ensaio consumiu **nao fica dentro das metricas**: ele sai pelo
    desconto por uniao, em `congelamentos`, que e o mecanismo que ja existia.

    A RECUSA CONTINUA, e so a origem mudou: exercicio sem `exercise_started`
    nenhum nao produz metrica.
    """
    for evento in escrituracao:
        if evento.event_type == EXERCISE_STARTED:
            return instante(evento) - timedelta(
                seconds=label_seconds(evento.exercise_time)
            )
    raise SemMarcoZero(
        "nenhum `exercise_started` no fluxo: T0 nao pode ser derivado, e "
        "exercicio sem T0 nao produz metrica.\n"
        "    Isto NAO acontece mais por descarte de epoch — T0 e atributo do "
        "exercicio e sobrevive a `rehearsal` (P6-4). Acontece quando a metrica e "
        "computada sobre um fluxo em que o exercicio nunca comecou."
    )
