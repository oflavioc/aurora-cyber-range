"""O avaliador de predicados de verificação — e a linhagem como lógica dele.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3.1 — *"o motor avalia continuamente e emite
`verification_predicate_satisfied` no instante em que a condição passa a valer"*;
`09_EVENT_MODEL.md` §3.1, parágrafo do avaliador; `01_ARCHITECTURE.md` §4.1.

DUAS CAMADAS, E A SEPARAÇÃO É O PONTO
--------------------------------------
`avalia(no, mundo)` é **puro**: recebe a árvore e o mundo, devolve `bool`. Não
sabe o que é epoch, não lê store e não emite.

`avaliar_e_emitir(...)` **monta o mundo** — e é aí que a consciência de linhagem
vive. `00_MASTER_SPEC.md` §3.2 exige exatamente essa forma para o desconto por
união: *"o número certo aparecendo por ausência de insumo em vez de por cálculo"*
é o defeito, e ele vale igual aqui. Por isso a montagem é lógica escrita e
testada, e não um argumento que chega pronto de algum lugar.

O PREDICADO MEIO-REVERTIDO NÃO EXISTE, E É POR CONSTRUÇÃO
-----------------------------------------------------------
As folhas `event` e as folhas de flag leem **o mesmo mundo**: a linhagem
corrente. Antes de `01` §4.1 generalizar de instância para classe, as primeiras
liam o fluxo cru e as segundas o estado reconstruído — e um rollback deixava o
predicado satisfeito pela metade, com contenção "verificada" por ato que o
facilitador desfez.

Aqui não há como escrever isso: `Mundo` é montado de uma linhagem só, e as duas
famílias de folha o consultam.

A EMISSÃO É POR TRANSIÇÃO, E A TRANSIÇÃO É LIDA NA CORRENTE
-------------------------------------------------------------
`09` §3.1: *"a satisfação pertence à epoch em que foi emitida… o avaliador
reavalia sobre a linhagem corrente e, se ela satisfaz, emite na epoch nova"*.

Uma satisfação anterior só suprime a emissão se ela **estiver na linhagem
corrente**. Satisfação de epoch abandonada não está — o evento continua no
store, legível e marcado, e o AAR o renderiza —, então a reavaliação emite de
novo na epoch nova. O gatilho continua sendo transição; o que mudou foi o mundo
sobre o qual ele é lido.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from contracts.generated.events import (
    FACT_MATERIALIZED,
    VERIFICATION_PREDICATE_SATISFIED,
)
from range_core.events.envelope import Correlation, Event, FlagValue
from range_core.events.linhagem import eventos_da_linhagem_corrente
from range_core.events.store import EventDraft, EventStore

#: `09` §4.1 — o veredito é da máquina, sobre o mundo. Nunca `participant_action`.
CAMADA = "ground_truth"

#: `09` §1.1 — quem produziu.
PRODUTOR = "inject-engine"

#: A chave do payload que nomeia qual predicado passou a valer. Sem ela, dois
#: predicados satisfeitos produziriam eventos indistinguíveis, e `TTCV` e `TTRV`
#: leriam o mesmo instante.
NOME_DO_PREDICADO = "predicate"


class PredicadoMalformado(Exception):
    """Nó que não é nenhuma das nove formas de `ground_truth.schema.yaml`.

    Recusa **alta**: o contrato já garante a forma, então chegar aqui significa
    que o pack passou por outro caminho. Avaliar um nó desconhecido como falso
    seria pior que recusar — a contenção nunca verificaria, e ninguém saberia por
    quê.
    """


@dataclass(frozen=True)
class Mundo:
    """O mundo corrente, montado de UMA linhagem.

    `tipos` e `fatos` vêm dos eventos sobreviventes; `flags`, do fold sobre os
    mesmos eventos. É a unidade que torna o predicado meio-revertido
    inexprimível.
    """

    tipos: frozenset[str]
    fatos: frozenset[str]
    flags: Mapping[str, FlagValue]


def avalia(no: Mapping, mundo: Mundo) -> bool:
    """A árvore de `ground_truth.schema.yaml` §predicate, sobre um mundo dado.

    **Puro.** Quem decide o que é o mundo é o chamador — e essa foi a decisão do
    `spec-change` `linhagem-corrente-e-o-avaliador`.

    `before` e `after` não são avaliados aqui e **não são silenciosamente
    falsos**: eles comparam contra o relógio de exercício, que não é parte do
    mundo desta função. Chegam como `PredicadoMalformado` até existir consumidor
    que os traga — recusa alta é o que impede um predicado temporal de passar por
    "não satisfeito" e a contenção nunca verificar sem explicação.
    """
    if "all" in no:
        return all(avalia(filho, mundo) for filho in no["all"])
    if "any" in no:
        return any(avalia(filho, mundo) for filho in no["any"])
    if "not" in no:
        return not avalia(no["not"], mundo)
    if "event" in no:
        return no["event"] in mundo.tipos
    if "flag_true" in no:
        return bool(mundo.flags.get(no["flag_true"]))
    if "flag_false" in no:
        return not bool(mundo.flags.get(no["flag_false"]))
    if "absence_of" in no:
        alvo = no["absence_of"]
        classe = alvo if isinstance(alvo, str) else alvo["fact_class"]
        return classe not in mundo.fatos
    raise PredicadoMalformado(
        f"no de predicado nao reconhecido: {sorted(no)}.\n"
        "    As nove formas estao em `contracts/ground_truth.schema.yaml`. "
        "`before` e `after` comparam contra o relogio de exercicio, que nao e "
        "parte do mundo desta funcao, e por isso recusam alto em vez de "
        "devolverem falso — falso silencioso faria a contencao nunca verificar."
    )


def mundo_corrente(
    eventos: Sequence[Event], flags: Mapping[str, FlagValue]
) -> Mundo:
    """Monta o mundo a partir dos eventos **já filtrados pela linhagem**.

    Recebe os eventos correntes, e não o fluxo total: a filtragem é passo
    anterior e explícito em `avaliar_e_emitir`, para que ela seja legível como
    cálculo e não como recorte de quem monta.
    """
    fatos = {
        str(e.payload.get("fact_class"))
        for e in eventos
        if e.event_type == FACT_MATERIALIZED and e.payload.get("fact_class")
    }
    return Mundo(
        tipos=frozenset(e.event_type for e in eventos),
        fatos=frozenset(fatos),
        flags=MappingProxyType(dict(flags)),
    )


def _ja_satisfeito_na_corrente(eventos: Sequence[Event], nome: str) -> bool:
    """Há veredito deste predicado **na linhagem corrente**?

    É o que torna a emissão por transição, e é onde a norma de `09` §3.1 opera:
    satisfação de epoch abandonada **não** está na linhagem, então não suprime a
    emissão na epoch nova. O evento antigo continua no store — o que ele não faz
    é sustentar `TTCV` da corrente.
    """
    return any(
        e.event_type == VERIFICATION_PREDICATE_SATISFIED
        and e.payload.get(NOME_DO_PREDICADO) == nome
        for e in eventos
    )


def avaliar_e_emitir(
    store: EventStore,
    predicados: Mapping[str, Mapping],
    flags: Mapping[str, FlagValue],
) -> list[Event]:
    """Avalia os predicados do pack sobre a linhagem corrente, e emite as transições.

    Devolve os eventos emitidos — vazio quando nada passou a valer, que é o caso
    comum de uma avaliação contínua.

    A leitura do store é **total** (`01` §4.1), e o estreitamento acontece aqui,
    depois dela: `eventos_da_linhagem_corrente` é a definição única, a mesma que
    o fold consome.

    `flags` chega como **dado**, do fold, e não é recalculado aqui — duas
    reconstruções do mesmo estado divergiriam, e a divergência apareceria como
    predicado meio-revertido, que é o que este módulo existe para tornar
    impossível.
    """
    correntes = eventos_da_linhagem_corrente(store.read_all())
    mundo = mundo_corrente(correntes, flags)

    emitidos: list[Event] = []
    for nome, arvore in sorted(predicados.items()):
        if not isinstance(arvore, Mapping):
            # `service_restoration` admite `{not_applicable: "motivo"}` — D5 da
            # Fase 1. Não é predicado, e não se avalia: AAR imprime "TTRV nao
            # aplicavel" em vez de nulo ou de um zero que parece medição.
            continue
        if "not_applicable" in arvore:
            continue
        if not avalia(arvore, mundo):
            continue
        if _ja_satisfeito_na_corrente(correntes, nome):
            continue
        emitidos.append(
            store.append(
                EventDraft(
                    event_type=VERIFICATION_PREDICATE_SATISFIED,
                    truth_layer=CAMADA,
                    producer=PRODUTOR,
                    correlation=Correlation(),
                    payload={NOME_DO_PREDICADO: nome},
                )
            )
        )
    return emitidos


# ---------------------------------------------------------------------------
# O LAÇO CONTÍNUO — `03` §3.1, *"o motor avalia continuamente"*.
#
# A peça 4 entregou o avaliador e declarou a fronteira: quem o chama a cada
# evento é a peça 5, porque **é o consumidor que decide a cadência**, e os
# computadores de métrica são o consumidor.
#
# POR QUE É UM OBJETO, E NÃO UMA CHAMADA DENTRO DO ENGINE
# --------------------------------------------------------
# As folhas de `containment` no exemplo normativo de `03` §3.1 são
# `vpn_access_revoked` e `identity_scope_disabled` — **ações com efeito no mundo
# simulado**, que `03` §3.1 separa por nome das afirmações sobre ele.
#
# MEDIDO NA ÁRVORE: nada as emite ainda. A superfície das três ações de `01` §4.4
# é de outra fase, e o `Emissor` das nove declarações não pode movê-las — por
# `09` §4.0, folha de predicado exige `state_effect` **e**
# `metric_side: verification`, e nenhuma das nove satisfaz a conjunção.
#
# Então hoje o único chamador é o engine. O laço é objeto, e não um método
# privado dele, para que a superfície que vier receba **este mesmo** objeto: dois
# laços leriam o mesmo store e dariam a mesma resposta, mas nada garantiria que
# carregam o mesmo pack.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LacoDeVerificacao:
    """Avalia os predicados do pack sobre a linhagem corrente, a cada gravação.

    `flags` NÃO é parâmetro: ele é derivado do fold aqui dentro, a cada chamada.
    Isso não contradiz o docstring de `avaliar_e_emitir` — o que aquele proíbe é
    o avaliador RECALCULAR o estado por conta própria; aqui o estado vem do
    `project`, que é o fold, e é a mesma reconstrução que toda projeção usa.

    Recebê-lo pronto seria pior: o chamador teria de lembrar de reconstruí-lo
    depois de gravar, e um chamador distraído avaliaria o mundo de antes do
    próprio evento que acabou de emitir.
    """

    store: EventStore
    predicados: Mapping[str, Mapping]
    declarations: object

    def avaliar(self) -> list[Event]:
        """Devolve os vereditos emitidos — vazio no caso comum.

        Sem predicado, não há o que avaliar, e a saída antecipada evita um fold
        por gravação num pack que não os declara. Pack real sempre os tem —
        `ground_truth.schema.yaml` os exige —, mas o engine é montado em teste e
        em demo com packs mínimos.
        """
        if not self.predicados:
            return []
        from range_core.state.simulation_state import project

        flags = project(self.store.read_all(), self.declarations).flags
        return avaliar_e_emitir(self.store, self.predicados, flags)
