"""inject-engine — quem chama o clock, o store e o fold, e quem nao dispara.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §3 (PAUSAR impede disparo agendado), §4.1 e §4.2
(rollback), §6 ("inject-engine — carrega pack, avalia branches, emite eventos de
effect, alimenta projecao"); `09_EVENT_MODEL.md` §1.1, §2, §3 e §3.1;
`07_IMPLEMENTATION_PHASES.md` Fase 2, item 3 da DoD e DEMO.

O QUE ESTE MODULO ENTREGA, E O QUE JA ESTAVA PRONTO
---------------------------------------------------
O store grava e carimba; o clock da as marcas e o `is_paused`; o fold projeta e
recusa o que nao fecha. **O engine e quem chama os tres.** Nada do que ele faz
com estado e dele: ele nao guarda flag, nao guarda "o que ja apliquei" e nao tem
projecao propria.

A METADE RESTANTE DO ITEM 3 MORA AQUI
--------------------------------------
*"PAUSAR congela o clock e bloqueia disparo agendado."* A primeira metade e do
clock e ja estava fechada. A segunda e desta peca, e a divisao nao e arbitraria:
o clock **nao agenda nada**, entao ele nao tem o que bloquear. Ele oferece
`is_paused`; quem decide nao disparar e quem dispara.

`01` §3 fala em disparo AGENDADO. Disparo MANUAL durante a pausa continua
permitido, e a distincao e da spec e nao minha: `01` §6 lista "disparo manual e
agendado" como duas coisas no gm-console, e so a segunda aparece na frase do
PAUSAR. Um facilitador que clica durante a pausa esta decidindo; um agendador
que dispara durante a pausa esta ignorando a pausa.

A JANELA DE AGENDAMENTO, e por que ela nao e memoria
-----------------------------------------------------
`due_injects` e CONSULTA, nunca lembranca. Um inject esta em atraso quando

    corte < t_relative <= posicao corrente

e nao existe `inject_fired` dele na epoch corrente.

**`posicao corrente` e o rotulo `T+`**, que rebobina ate o ponto de corte no
rollback (`01` §3). E o que faz o agendamento voltar a valer depois de um
rollback sem o engine guardar nada: a posicao esta no relogio, e o que ja
disparou esta no store.

**`corte` e a posicao da ancora do ultimo `rollback_performed`**, ou -1 se nao
houve nenhum. Sem ele, o rollback faria os injects ANTERIORES ao corte
dispararem de novo — e `09` §3 e explicito ao desenhar so `A03 (novamente)` na
epoch 1, com A01 e A02 preservados.

**O limite, declarado:** inject com `t_relative` anterior ao corte e tratado como
resolvido, tenha disparado ou nao. Um inject que nunca disparou e fica para tras
de um corte nao volta sozinho — volta por disparo manual. E a leitura
conservadora: o corte declara que tudo ate ali esta assentado, e adivinhar o
contrario faria o engine ressuscitar inject que o facilitador pulou de proposito.

Idempotencia NAO depende de nada disso. Ela vem de `effects` declarar estado
final (D3, §1.7 do registro): disparar A01 duas vezes escreve o mesmo valor.
A janela evita evento duplicado na timeline, que e outra coisa.

O QUE ESTA PECA NAO FAZ
------------------------
Branching (`branch_selected`) e Fase 7. `exercise_reset` e Fase 4. E `rollback`
com `reason: technical_failure` **recusa**, porque o campo de payload que carrega
os extremos do intervalo congelado nao existe — item 7 da DoD, pendencia P2-4.
Emitir o evento sem o intervalo seria gravar um rollback que a Fase 6 le como se
nao houvesse congelamento nenhum: registro que existe, requisito que some.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from contracts.generated.events import (
    DECISION_MADE,
    EXERCISE_PAUSED,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.exercise_clock import ExerciseClock, label_seconds
from range_core.engine.loader.pack_loader import LoadedPack
from range_core.events.envelope import Correlation, Event
from range_core.events.epoch import current_epoch
from range_core.events.store import EventDraft, EventStore
from range_core.state.simulation_state import (
    OPTION_ID,
    TO_EVENT_ID,
    SimulationState,
    project,
)

#: `09` §2 — `facilitation` afirma o que o facilitador fez com a SIMULACAO, e o
#: produtor e a maquina de exercicio. `01` §6 nomeia as duas pecas: o
#: inject-engine executa, o gm-console e por onde a decisao entra.
TRUTH_LAYER_FACILITATION = "facilitation"
TRUTH_LAYER_PARTICIPANT = "participant_action"
PRODUCER_ENGINE = "inject-engine"
PRODUCER_CONSOLE = "gm-console"

#: Chaves de payload de `rollback_performed`. `01` §4.2 lista as quatro; o
#: `to_event_id` que ancora o corte vem de `simulation_state`, que e quem o
#: exige. Viram schema de payload por `event_type` na **P2-4**, e ate la sao
#: contrato de facto — mesma situacao das chaves do fold, e pela mesma razao.
TO_INJECT_ID = "to_inject_id"
BY_USER = "by_user"
ROLE = "role"
REASON = "reason"

#: `09` §3.1 da a este motivo, e so a ele, o efeito *"relogio de metricas
#: congelado entre o inject falho e a retomada"*. E por isso que ele exige um
#: campo que os outros tres nao exigem. A constante e conferida no construtor
#: contra a taxonomia lida do contrato: se o nome mudar la, a guarda nao fica
#: orfa em silencio.
REASON_TECHNICAL_FAILURE = "technical_failure"

#: Corte "adiante de tudo": nenhum inject cai na janela. Usado so no fluxo que o
#: fold ja recusaria por ancora desconhecida, para o engine nao agendar por
#: adivinhacao enquanto isso.
_SEM_JANELA = 1 << 40


class EngineSite:
    """Os sitios de recusa do engine, nomeados — mesmo argumento do fold."""

    ALREADY_STARTED = "already_started"
    NOT_STARTED = "not_started"
    UNKNOWN_INJECT = "unknown_inject"
    UNKNOWN_DECISION_POINT = "unknown_decision_point"
    UNKNOWN_OPTION = "unknown_option"
    UNKNOWN_ANCHOR = "unknown_anchor"
    UNKNOWN_REASON = "unknown_reason"
    INTERVAL_NOT_RECORDABLE = "interval_not_recordable"


class EngineError(Exception):
    """Operacao que o engine recusa, alto.

    `site` diz QUAL recusa ocorreu, para o teste poder afirmar a recusa certa em
    vez de "houve excecao".
    """

    def __init__(self, site: str, message: str) -> None:
        super().__init__(f"[{site}] {message}")
        self.site = site


@dataclass(frozen=True, slots=True)
class Facilitator:
    """Quem opera. Vai para o payload dos eventos de `facilitation`.

    `01` §4.2 grava `by_user` e `role` no `rollback_performed`, e nao ha razao
    para o pause ser anonimo enquanto o rollback tem autor: pausa dupla e
    tipicamente dois facilitadores agindo sobre o mesmo exercicio, e o registro
    de quem pausou e o que permite ver isso depois.
    """

    user: str
    role: str


class InjectEngine:
    """Carrega pack, dispara inject, registra decisao, pausa e rebobina.

    POR QUE O CLOCK CONCRETO, E NAO A PORTA
    ----------------------------------------
    `ExerciseClockPort` e o LIMITE DO STORE — uma leitura, quatro marcas. O
    engine precisa de mais: `is_paused`, `elapsed_seconds`, `pause`, `resume` e
    `start_new_epoch`. Alargar a porta para caber o engine tiraria dela a
    propriedade que a justifica.

    Duplo de teste tambem nao e necessario aqui: o clock ja recebe o tempo de
    parede por injecao, entao um teste do engine controla o tempo com o clock
    de verdade — e testa o clock de verdade junto.
    """

    def __init__(
        self,
        *,
        pack: LoadedPack,
        clock: ExerciseClock,
        store: EventStore,
        facilitator: Facilitator,
        rollback_reasons: Collection[str],
    ) -> None:
        if REASON_TECHNICAL_FAILURE not in rollback_reasons:
            raise EngineError(
                EngineSite.UNKNOWN_REASON,
                f"a taxonomia recebida {sorted(rollback_reasons)!r} nao tem "
                f"{REASON_TECHNICAL_FAILURE!r}: a guarda do item 7 ficaria orfa, "
                "e um rollback de falha tecnica passaria sem o intervalo",
            )
        self._pack = pack
        self._clock = clock
        self._store = store
        self._facilitator = facilitator
        self._rollback_reasons = frozenset(rollback_reasons)

    # -- leitura -------------------------------------------------------------

    @property
    def pack(self) -> LoadedPack:
        return self._pack

    def state(self) -> SimulationState:
        """A projecao, reconstruida do zero a cada chamada.

        Sem cache, e e decisao: cache seria estado fora do fold, e o rollback
        teria de reconstrui-lo tambem. A §3.8 do registro mediu o custo — o fold
        e 3% do orcamento de reconstrucao —, entao nao ha o que otimizar aqui
        antes de haver problema medido.
        """
        return project(self._store.read_all(), self._pack.declarations)

    def position_seconds(self) -> int:
        """Posicao na linha do exercicio, em segundos — o rotulo `T+` lido."""
        return label_seconds(self._clock.marks().exercise_time)

    def due_injects(self) -> tuple[str, ...]:
        """Injects agendados em atraso. **Vazio enquanto pausado** — item 3.

        A pausa e conferida ANTES de qualquer leitura de posicao, para que a
        resposta durante a pausa nao dependa de nenhuma outra coisa estar certa.

        Antes do `exercise_started` nada e agendado: o relogio ate corre, mas o
        exercicio nao comecou. Sem esta guarda, `fire_due` antes do start
        levantaria `NOT_STARTED` por um caminho que o chamador nao pediu — a
        consulta diria "ha o que disparar" e a acao recusaria.
        """
        if self._clock.is_paused or not self._started():
            return ()

        posicao = self.position_seconds()
        corte = self._cut_position()
        ja_dispararam = self._fired_in_current_epoch()

        return tuple(
            inject.id
            for inject in sorted(
                self._pack.injects, key=lambda i: (i.t_relative_seconds, i.id)
            )
            if corte < inject.t_relative_seconds <= posicao
            and inject.id not in ja_dispararam
        )

    # -- transicoes ----------------------------------------------------------

    def start(self) -> Event:
        """`exercise_started`, com o pino do pack no payload.

        Recusa o segundo start: `01` §4.2 tem `exercise_reset` para recomecar, e
        ele e de outra fase. Dois `exercise_started` sem reset seria o mesmo
        exercicio afirmando dois inicios.
        """
        if any(e.event_type == EXERCISE_STARTED for e in self._store.read_all()):
            raise EngineError(
                EngineSite.ALREADY_STARTED,
                "o exercicio ja comecou. Recomecar e `exercise_reset`, que e "
                "entregavel de outra fase",
            )
        return self._append(
            EXERCISE_STARTED,
            payload=self._pack.pin_payload(),
        )

    def fire(self, inject_id: str) -> Event:
        """Disparo MANUAL de um inject. Permitido durante a pausa — ver o modulo.

        Nao grava effects: quem os resolve e o fold, contra o pack fixado. O
        evento diz QUAL inject disparou, e `04` §5 diz o que ele declara —
        `09` §4.1 nao tem tipo de evento que carregue efeito de flag, e
        acrescentar um seria gravar o RESULTADO da resolucao, que e o comeco de
        estado procedural (`00` §5.2).
        """
        inject = self._pack.by_id(inject_id)
        if inject is None:
            raise EngineError(
                EngineSite.UNKNOWN_INJECT,
                f"inject {inject_id!r} nao existe no pack {self._pack.pack_id!r}",
            )
        self._require_started(f"disparar {inject_id}")
        return self._append(INJECT_FIRED, inject_id=inject.id)

    def fire_due(self) -> tuple[Event, ...]:
        """Dispara o que `due_injects` reportar, na ordem do `t_relative`.

        E o disparo AGENDADO, e portanto o que a pausa bloqueia — a lista vem
        vazia e nada acontece, sem caso especial aqui.
        """
        return tuple(self.fire(inject_id) for inject_id in self.due_injects())

    def decide(self, inject_id: str, option_id: str, *, actor_id: str, persona: str) -> Event:
        """`decision_made` — `participant_action`, e `declaration` por classe.

        A opcao escolhida carrega `effects` que mutam flags, mas quem muta sao os
        effects e nao o evento (`09` §4.0): a equipe ESCOLHEU, e escolher e
        afirmacao. Por isso `actor_id` e `persona` sao obrigatorios aqui e nao
        nos eventos de facilitacao.

        `causation_id` aponta para o `inject_fired` que abriu a decisao, quando
        houver: e a cadeia decisao -> efeito que `09` §1 existe para preservar.
        """
        inject = self._pack.by_id(inject_id)
        if inject is None:
            raise EngineError(
                EngineSite.UNKNOWN_INJECT,
                f"inject {inject_id!r} nao existe no pack {self._pack.pack_id!r}",
            )
        if inject.decision_point is None:
            raise EngineError(
                EngineSite.UNKNOWN_DECISION_POINT,
                f"inject {inject_id!r} nao tem `decision_point`: nao ha decisao a registrar",
            )
        if option_id not in {opcao.id for opcao in inject.decision_point.options}:
            raise EngineError(
                EngineSite.UNKNOWN_OPTION,
                f"opcao {option_id!r} nao existe em {inject.decision_point.id!r} "
                f"(opcoes: {sorted(o.id for o in inject.decision_point.options)})",
            )
        self._require_started(f"registrar decisao em {inject_id}")

        return self._append(
            DECISION_MADE,
            inject_id=inject_id,
            payload={OPTION_ID: option_id},
            truth_layer=TRUTH_LAYER_PARTICIPANT,
            producer=PRODUCER_CONSOLE,
            actor_id=actor_id,
            persona=persona,
            causation_id=self._last_fired_event_id(inject_id),
        )

    def pause(self) -> Event:
        """PAUSAR — congela o clock e registra. A recusa da pausa dupla e do clock."""
        self._clock.pause()
        return self._append(EXERCISE_PAUSED, payload=self._who())

    def resume(self) -> None:
        """CONTINUAR — retoma o clock. **Nao emite evento, e isso e uma lacuna.**

        O catalogo de `09` §4.1 e registro FECHADO e nao tem `exercise_resumed`.
        Entao o store guarda o inicio da pausa e nao guarda o fim: a duracao de
        uma pausa nao e reconstruivel a partir do fluxo, e a timeline do AAR
        (Fase 10) mostra uma pausa que nunca termina.

        Nao e contornado aqui. Inventar `event_type` fora do catalogo violaria o
        invariante 3, e reaproveitar `exercise_paused` para os dois sentidos
        gravaria dois eventos identicos com significados opostos. Fica como
        pendencia, com `spec-change` proprio — ver o registro da fase.
        """
        self._clock.resume()

    def rollback(self, *, to_event_id: str, reason: str) -> Event:
        """`rollback_performed` — grava, incrementa epoch, rebobina o rotulo.

        A ORDEM E DELIBERADA: o evento e gravado ANTES de o clock rebobinar.
        Gravado depois, ele carregaria o `exercise_time` do ponto de corte e
        pareceria ter acontecido la — e `09` §3 o desenha no fim da epoch
        abandonada, que e quando ele de fato foi ordenado.

        A REBOBINAGEM, e por que ela e uma subtracao e nao um zero:
        `start_new_epoch` recebe a ORIGEM da nova epoch em segundos de exercicio
        desde T0. Para o rotulo voltar ao ponto de corte — `01` §3, *"rebobina
        ate o ponto de corte"* —, a origem e `decorrido agora menos a posicao da
        ancora`. Encadeados compoem sozinhos: a posicao da ancora ja esta no
        referencial rebobinado, entao a origem nova acumula o descartado.

        O que sobra e `exercise_timestamp`, que NAO rebobina: a distancia entre
        ele e o rotulo passa a ser exatamente quanto o rollback descartou, que e
        o que `01` §3 exige.

        `technical_failure` e RECUSADO — ver o cabecalho do modulo e a P2-4.
        """
        if reason not in self._rollback_reasons:
            raise EngineError(
                EngineSite.UNKNOWN_REASON,
                f"motivo {reason!r} fora da taxonomia de `09` §3.1 "
                f"({sorted(self._rollback_reasons)}). Rotulo sem consequencia nao "
                "serve: cada motivo tem efeito definido no AAR e nas metricas",
            )
        if reason == REASON_TECHNICAL_FAILURE:
            raise EngineError(
                EngineSite.INTERVAL_NOT_RECORDABLE,
                f"rollback com `reason: {REASON_TECHNICAL_FAILURE}` exige registrar "
                "no evento os extremos do intervalo congelado, em `exercise_timestamp` "
                "(item 7 da DoD da Fase 2, `06_ACCEPTANCE_TESTS.md` T3). O campo de "
                "payload que os carrega ainda nao existe no contrato — pendencia "
                "P2-4. Gravar sem ele produziria um rollback que a Fase 6 le como se "
                "nao houvesse congelamento, e o desconto sumiria sem nada acusar",
            )

        eventos = self._store.read_all()
        ancora = next((e for e in eventos if e.event_id == to_event_id), None)
        if ancora is None:
            raise EngineError(
                EngineSite.UNKNOWN_ANCHOR,
                f"nenhum evento com event_id {to_event_id!r} no store: o corte nao "
                "tem ancora",
            )

        evento = self._append(
            ROLLBACK_PERFORMED,
            inject_id=ancora.correlation.inject_id,
            payload={
                TO_EVENT_ID: to_event_id,
                TO_INJECT_ID: ancora.correlation.inject_id,
                REASON: reason,
                **self._who(),
            },
        )
        self._clock.start_new_epoch(
            self._clock.elapsed_seconds() - label_seconds(ancora.exercise_time)
        )
        return evento

    # -- internos ------------------------------------------------------------

    def _who(self) -> dict:
        return {BY_USER: self._facilitator.user, ROLE: self._facilitator.role}

    def _started(self) -> bool:
        return any(e.event_type == EXERCISE_STARTED for e in self._store.read_all())

    def _require_started(self, o_que: str) -> None:
        if not self._started():
            raise EngineError(
                EngineSite.NOT_STARTED,
                f"{o_que}: o exercicio nao comecou. Sem `exercise_started` nao ha "
                "pino de pack, e o fold recusa reconstruir um fluxo desses",
            )

    def _append(
        self,
        event_type: str,
        *,
        inject_id: str | None = None,
        payload: dict | None = None,
        truth_layer: str = TRUTH_LAYER_FACILITATION,
        producer: str = PRODUCER_ENGINE,
        actor_id: str | None = None,
        persona: str | None = None,
        causation_id: str | None = None,
    ) -> Event:
        """Ponto unico de emissao. As marcas e a epoch sao do store — D1."""
        return self._store.append(
            EventDraft(
                event_type=event_type,
                truth_layer=truth_layer,
                producer=producer,
                correlation=Correlation(
                    scenario_id=self._pack.pack_id,
                    inject_id=inject_id,
                    causation_id=causation_id,
                ),
                payload=payload or {},
                actor_id=actor_id,
                persona=persona,
            )
        )

    def _cut_position(self) -> int:
        """Posicao da ancora do ultimo rollback, ou -1 se nao houve nenhum.

        -1, e nao 0, para que um inject em `t_relative: "00:00"` seja disparavel
        na epoch 0 — a comparacao e estritamente maior.
        """
        eventos = self._store.read_all()
        ultimo = next(
            (e for e in reversed(list(eventos)) if e.event_type == ROLLBACK_PERFORMED),
            None,
        )
        if ultimo is None:
            return -1
        ancora_id = ultimo.payload.get(TO_EVENT_ID)
        ancora = next((e for e in eventos if e.event_id == ancora_id), None)
        if ancora is None:
            # Fluxo que o fold recusaria por `ANCHOR_UNKNOWN`. Aqui a resposta
            # conservadora e nao agendar nada, em vez de agendar contra um corte
            # que nao se sabe onde fica.
            return _SEM_JANELA
        return label_seconds(ancora.exercise_time)

    def _fired_in_current_epoch(self) -> set[str]:
        eventos: Sequence[Event] = self._store.read_all()
        epoch = current_epoch(eventos)
        return {
            e.correlation.inject_id
            for e in eventos
            if e.event_type == INJECT_FIRED
            and e.simulation_epoch == epoch
            and e.correlation.inject_id is not None
        }

    def _last_fired_event_id(self, inject_id: str) -> str | None:
        eventos = self._store.read_all()
        epoch = current_epoch(eventos)
        for evento in reversed(list(eventos)):
            if (
                evento.event_type == INJECT_FIRED
                and evento.simulation_epoch == epoch
                and evento.correlation.inject_id == inject_id
            ):
                return evento.event_id
        return None
