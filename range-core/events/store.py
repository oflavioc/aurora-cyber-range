"""Event store append-only — a superficie, antes da implementacao.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4, §4.1 e §4.2; `09_EVENT_MODEL.md` §1.1 e §3;
`00_MASTER_SPEC.md` §5.5.

O QUE ESTA SUPERFICIE EXISTE PARA TORNAR INEXPRIMIVEL
-----------------------------------------------------
`01` §4.1 diz: **a leitura do store e total.** `read_all` devolve todo evento
gravado, sempre, e nenhum caminho de leitura compartilhado filtra por epoch, por
abandono ou por ponto de corte de rollback.

O fold ja nao consegue consultar o store — `project` recebe o fluxo e nao tem
parametro por onde um store entre. Falta a outra metade: **o store nao pode
oferecer o filtro**. As duas juntas fecham a garantia; sozinha, cada uma deixa
uma porta.

A forma escolhida nao e uma lista de parametros proibidos. E a AUSENCIA DE
PARAMETRO: `read_all()` nao aceita nada. Enumerar vocabulario proibido —
`since`, `after`, `epoch`, `cursor` — seria adivinhar as palavras que alguem
usaria, e a proxima palavra nao estaria na lista. Sem parametro, nao ha o que
nomear.

`scripts/check_store_read_surface.py` verifica isso por AST, e verifica pela
SUPERFICIE INTEIRA em vez de por nome: o conjunto de metodos publicos precisa ser
exatamente o declarado ali. Metodo publico novo reprova ate alguem atualizar a
lista — que e o ponto, porque forca a conversa em vez de deixar um filtro entrar.

PAGINACAO FICA DE FORA; STREAMING E OUTRA DECISAO
--------------------------------------------------
As duas nao sao a mesma coisa, e so uma abre a porta que a §4.1 fecha.

**Paginacao esta fora da superficie publica.** Qualquer parametro que diga ONDE
COMECAR e um lugar onde alguem escreve "comeca depois do corte", e o filtro entra
pela frente com nome de otimizacao.

**Streaming — devolver iterador em vez de sequencia — nao abre porta nenhuma**:
muda so quando o custo de memoria e pago, e nao permite dizer o que fica de fora.
Fica disponivel se a medicao exigir.

QUEM MATERIALIZA, E A SUPOSICAO QUE ISSO CARREGA
------------------------------------------------
`project` recebe `Sequence`. Se `read_all` devolvesse iterador, alguem
materializaria entre o store e o fold — e "alguem" e o chamador, que e onde a
materializacao pode ser esquecida.

**Decisao: `read_all` devolve `Sequence`.** O store materializa, a simetria com
`project` fica intacta, e nao ha passo que se possa pular.

**A suposicao, declarada porque e suposicao:** um exercicio de 4 h cabe em
memoria com folga. Ela **nao foi medida** — e a P2-10, que vence dentro desta
fase, assim que houver fluxo desse tamanho.

**O que a reabre:** a medicao da P2-10 mostrar que nao cabe com folga, ou o
envelope de volume mudar — a Fase 9 acrescenta `telemetry_emitted`, que e a
unica fonte com ordem de grandeza diferente das demais. Se reabrir, a saida e
`read_all` devolvendo iterador e o CHAMADOR materializando, com a materializacao
num unico lugar nomeado, nunca espalhada.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from range_core.clock.port import ExerciseClockPort
from range_core.events.envelope import Correlation, Event
from range_core.events.epoch import current_epoch
from range_core.events.ids import new_event_id


@dataclass(frozen=True, slots=True)
class StreamHead:
    """Quantos eventos ha, e qual e o ultimo. A identidade do fim do fluxo.

    DOIS CAMPOS, e nao um. So a contagem confundiria fluxos de mesmo tamanho —
    e um deles e o caso real: reconstrucao de um store restaurado de backup com
    o mesmo numero de linhas e conteudo diferente. So o ultimo `event_id`
    confundiria o fluxo que perdeu eventos no meio e manteve a cauda, que e o
    truncamento que `test_truncar_a_cauda_NAO_e_detectado` declara como limite.

    Os dois juntos nao fecham o buraco do truncamento — nada aqui fecha, e o
    limite continua declarado la —, mas fecham o de tamanho igual, que e o caso
    que o cache encontra em operacao normal.
    """

    count: int
    last_event_id: str | None


@dataclass(frozen=True, slots=True)
class EventDraft:
    """O que um PRODUTOR submete. Nao e o envelope.

    Faltam aqui, de proposito, as quatro marcas temporais, o `simulation_epoch`
    e o `event_id`: quem os carimba e o store, no append, a partir do
    `exercise-clock` — D1 do checkpoint desta fase, §1.5 do registro.

    Produtor que carimba o proprio tempo produz fluxo nao-monotonico, e carimba
    tempo que nao existiu se o fizer durante uma pausa. Aqui isso deixa de ser
    disciplina: **nao ha campo onde escrever**.
    """

    event_type: str
    truth_layer: str
    producer: str
    correlation: Correlation
    payload: Mapping[str, object] = field(default_factory=dict)
    actor_id: str | None = None
    persona: str | None = None


class EventStore(ABC):
    """A superficie. DOIS metodos publicos, e a lista e fechada.

    Fechada nao por convencao: `scripts/check_store_read_surface.py` compara o
    conjunto de metodos publicos com o que ele declara, e reprova o terceiro.

    A TENTACAO FUTURA, dita agora porque e previsivel
    -------------------------------------------------
    Foi o desenho MINIMO que tornou a verificacao forte, e nao o contrario. Com
    `read_all()` sem parametro, a checagem pode afirmar "nenhum parametro" em vez
    de listar palavras proibidas — e nenhuma lista prevê a palavra seguinte.

    A tentacao futura e acrescentar um metodo "so de leitura", inofensivo em si,
    sem perceber que ele **derruba a assercao**: a partir dele a garantia deixa
    de ser estrutural e volta a depender de alguem ter listado o parametro certo.
    Por isso a checagem reprova metodo publico novo ate ser declarada — o custo e
    uma conversa, e a conversa e o ponto.

    OS DOIS METODOS SAO CONCRETOS; O QUE OS BACKENDS IMPLEMENTAM E OUTRA COISA
    ---------------------------------------------------------------------------
    `append` carimba e `read_all` devolve; a persistencia fica em `_persist` e
    `_stored`, que sao privados. Assim a regra de carimbo — D1, e a epoch
    corrente — e escrita UMA VEZ e vale para todo backend, em vez de ser
    reimplementada por cada um e divergir no terceiro.
    """

    def __init__(self, clock: ExerciseClockPort) -> None:
        self._clock = clock

    def append(self, draft: EventDraft) -> Event:
        """Grava e devolve o evento carimbado. Append-only: nunca sobrescreve.

        O STORE CARIMBA, O PRODUTOR NAO — D1 do checkpoint, §1.5 do registro.
        `event_id`, as quatro marcas e o `simulation_epoch` sao atribuidos aqui,
        e `EventDraft` nao tem campo para nenhum deles.

        As quatro marcas vem de UMA leitura do clock (`Marks`), e nao de quatro:
        ler em chamadas separadas abriria janela para o clock avancar — ou ser
        pausado — entre elas.

        A epoch vem de `range_core.events.epoch.current_epoch`, o mesmo calculo
        que a projecao usa. O store ATRIBUI e o fold CONFERE, com contagem
        propria; se os dois usassem o mesmo caminho a conferencia nao valeria
        nada.

        `01` §4.2 e `00` §5.5: nada e removido, nunca. Rollback e um evento como
        outro qualquer, e o que ele faz com a linha temporal e assunto do fold.
        """
        marks = self._clock.marks()
        event = Event(
            event_id=new_event_id(),
            event_type=draft.event_type,
            truth_layer=draft.truth_layer,
            producer=draft.producer,
            exercise_time=marks.exercise_time,
            exercise_timestamp=marks.exercise_timestamp,
            wall_timestamp=marks.wall_timestamp,
            clock_multiplier=marks.clock_multiplier,
            simulation_epoch=current_epoch(self._stored()),
            correlation=draft.correlation,
            payload=dict(draft.payload),
            actor_id=draft.actor_id,
            persona=draft.persona,
        )
        self._persist(event)
        return event

    def read_all(self) -> Sequence[Event]:
        """Todo evento gravado, na ordem de append. SEM PARAMETRO.

        A ausencia de parametro e a garantia de `01` §4.1, e nao um simplismo
        que se corrige depois: e o que impede o caminho de leitura compartilhado
        de filtrar por epoch, abandono ou corte.

        Devolve `Sequence`, e nao iterador: `project` recebe `Sequence`, e
        empurrar a materializacao para o chamador a poe onde ela pode ser
        esquecida. A suposicao de que um exercicio de 4 h cabe em memoria esta
        declarada no cabecalho deste modulo, com o que a reabre — e a P2-10.

        A ordem de append e a ordem do exercicio por construcao: o store carimba
        no append, a partir de um clock que nao retrocede. Por isso o fold nao
        reordena.
        """
        return self._stored()

    def head(self) -> StreamHead:
        """A IDENTIDADE DO FIM DO FLUXO, em O(1). Nao devolve evento nenhum.

        POR QUE ISTO NAO ABRE A PORTA QUE `read_all` FECHA
        --------------------------------------------------
        `01` §4.1 proibe caminho de leitura compartilhado que FILTRE por epoch,
        abandono ou ponto de corte. Este metodo nao devolve eventos — devolve
        quantos ha e qual e o ultimo. Nao ha o que filtrar num par de valores, e
        nao ha parametro por onde um filtro entre: a garantia da §4.1 continua
        estrutural, e nao passa a depender de disciplina.

        POR QUE ELE EXISTE
        ------------------
        A projecao materializada (`01` §4: *"Simulation State — Redis (projecao)
        + event store"*) precisa saber SE ainda vale. Comparar o estado inteiro
        seria refazer o fold, que e o que o cache existe para evitar — 2,874 s em
        150 mil eventos, medido na §3.8 do registro da Fase 2.
        
        Comparar a CABECA e outra coisa: e a identidade da ENTRADA do fold, e
        custa uma consulta de indice. O que o cache poupa e o fold, nao a
        consulta.

        `read_all` continua sem parametro, e esta continua sendo a superficie
        inteira — agora com tres metodos, declarados em
        `scripts/check_store_read_surface.py`.
        """
        return self._head()

    @abstractmethod
    def _head(self) -> StreamHead:
        """A cabeca, em O(1). Backend-especifico — e o `O(1)` e o requisito.

        A implementacao ingenua seria `len(self._stored())`, que em Postgres
        carrega o fluxo inteiro e verifica a cadeia: exatamente o custo que o
        cache existe para evitar, pago para descobrir se o cache serve.
        """

    @abstractmethod
    def _persist(self, event: Event) -> None:
        """Grava um evento ja carimbado. Backend-especifico."""

    @abstractmethod
    def _stored(self) -> Sequence[Event]:
        """Todo evento gravado, na ordem de append. Backend-especifico."""


class InMemoryEventStore(EventStore):
    """Store em memoria. NAO satisfaz o criterio de reinicio da T3.

    Existe para exercitar o carimbo, a epoch e o par store -> fold sem depender
    de banco, e para ser o duplo dos testes de quem consumir o store.

    `06` T3 exige que "reinicio do processo restaura a projecao corrente sem
    intervencao", e isto perde tudo ao morrer. O backend persistente e a proxima
    peca, e a decisao de dependencia que ela carrega esta marcada no registro da
    fase.
    """

    def __init__(self, clock: ExerciseClockPort) -> None:
        super().__init__(clock)
        self._events: list[Event] = []

    def _persist(self, event: Event) -> None:
        self._events.append(event)

    def _stored(self) -> Sequence[Event]:
        # Copia: devolver a lista viva deixaria um leitor mutar o store por
        # acidente, e append-only que o chamador consegue alterar nao e
        # append-only.
        return tuple(self._events)

    def _head(self) -> StreamHead:
        return StreamHead(
            count=len(self._events),
            last_event_id=self._events[-1].event_id if self._events else None,
        )
