"""A linhagem corrente — quais escritas sobrevivem ao corte, e uma definição só.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4.1, na redação do `spec-change`
`linhagem-corrente-e-o-avaliador`: *"a exclusão dos eventos de epoch abandonada
posteriores ao corte vive no escopo de quem reconstrói o mundo corrente"*, e
*"a linhagem corrente tem UMA definição, e ela é função pura nomeada"*.

POR QUE AQUI, E NÃO EXPORTADA DO FOLD — A DIREÇÃO DA DEPENDÊNCIA
------------------------------------------------------------------
São dois consumidores: o fold de `simulation_state`, que reconstrói as flags, e
o avaliador de predicados, que decide se contenção e restauração valem agora.

Expor a máscara **do fold** faria o avaliador importar de `range_core.state`
para reconstruir mundo — e ele não depende de projeção de flags: o que os dois
compartilham é a noção de **linhagem**, e não o fold. A dependência ficaria
invertida, com o consumidor mais novo pendurado no mais antigo por um detalhe
que não é de nenhum dos dois.

`range-core/events/` é a camada de onde os dois já dependem, e é onde
`current_epoch` mora — linhagem é da mesma família. Daqui, `state/` importa
descendo, e o avaliador também.

**Por isso o erro é local.** `MalformedStream` e os onze `Site` vivem em
`simulation_state`, e importá-los aqui inverteria a direção que este módulo
existe para respeitar. As quatro recusas de âncora sobem como
`LinhagemInvalida`, e quem tem vocabulário de sítio o traduz — o fold mantém os
onze intactos, e este módulo não passa a conhecê-los.

O ALCANCE É POSICIONAL, E O LIMITE MUDOU DE DONO
--------------------------------------------------
Um `rollback_performed` na posição `i`, ancorado em `a`, marca `a < j < i`. Nada
garante que **todo** evento nesse intervalo pertença à linha abandonada: um
`exercise_paused` pode ser gravado entre o facilitador decidir rebobinar e o
rollback ser registrado.

O alcance largo é inofensivo para quem lê **escrita**, e a razão é a mesma para
os dois consumidores: **evento que não declara escrita não contribui de um jeito
nem de outro**, e todo evento que declara escrita e está antes do registro do
rollback pertence à linha abandonada por construção — foi gravado antes de ela
ser encerrada.

O avaliador se enquadra por um motivo que precisa ser dito, e não herdado: as
folhas `event` de um predicado só podem referenciar `event_type` com
`effect_class: state_effect` **e** `metric_side: verification` (`09` §4.0). São
atos com efeito no mundo — a mesma classe de "declara escrita" —, então o
argumento acima os cobre.

**Não é veredito geral de "este evento foi abandonado".** Consumidor cujo
critério seja outro não reusa isto: o critério dele é outro, e o motivo dele em
`09` §3.1 também. A versão anterior desta função dizia que ela *"não se exporta —
exportá-la seria a herança que `01` §4.1 proíbe"*, e a frase era exata sob a
redação antiga daquela seção. O `spec-change` que generalizou de instância para
classe a substituiu por esta: o que se proíbe é herança **no caminho
compartilhado de leitura**, e não que dois consumidores do mundo corrente
compartilhem a definição de linhagem — ao contrário, agora a spec **exige** que
compartilhem.
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.generated.events import ROLLBACK_PERFORMED
from range_core.events.envelope import Event

#: A chave da âncora no payload de `rollback_performed` — `01` §4.2, e o
#: `$defs/rollback_payload` do contrato de eventos.
TO_EVENT_ID = "to_event_id"


class LinhagemInvalida(Exception):
    """Fluxo em que a linhagem não é derivável. `motivo` nomeia qual das quatro.

    Local de propósito: quem tem vocabulário de sítio traduz. Ver o cabeçalho.
    """

    def __init__(self, motivo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.motivo = motivo


#: Os quatro motivos, para quem traduz não casar por texto de mensagem.
ANCORA_AUSENTE = "ancora_ausente"
ANCORA_DESCONHECIDA = "ancora_desconhecida"
ANCORA_POSTERIOR = "ancora_posterior"
ANCORA_ABANDONADA = "ancora_abandonada"


def escritas_sobreviventes(events: Sequence[Event]) -> list[bool]:
    """`[bool]` por posição: a escrita daquele evento entra na linhagem corrente?

    Encadeados compõem sem caso especial — marcar de novo o que já estava marcado
    não muda nada. O que **não** é aceito é ancorar num evento já abandonado:
    isso descreveria um corte para dentro de uma linha temporal que deixou de
    existir, e resolver por conta própria seria inventar semântica.
    """
    position_of: dict[str, int] = {}
    for index, event in enumerate(events):
        position_of[event.event_id] = index

    surviving = [True] * len(events)

    for index, event in enumerate(events):
        if event.event_type != ROLLBACK_PERFORMED:
            continue

        anchor_id = event.payload.get(TO_EVENT_ID)
        if not isinstance(anchor_id, str):
            raise LinhagemInvalida(
                ANCORA_AUSENTE,
                f"{ROLLBACK_PERFORMED} {event.event_id} sem {TO_EVENT_ID!r} no "
                "payload: o corte nao tem ancora, e ignorar o rollback deixaria "
                "o estado exibindo um mundo que ele removeu",
            )

        anchor = position_of.get(anchor_id)
        if anchor is None:
            raise LinhagemInvalida(
                ANCORA_DESCONHECIDA,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "que nao esta no fluxo",
            )
        if anchor > index:
            raise LinhagemInvalida(
                ANCORA_POSTERIOR,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "posterior a ele: rollback so anda para tras",
            )
        if not surviving[anchor]:
            raise LinhagemInvalida(
                ANCORA_ABANDONADA,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "que ja foi abandonado por rollback anterior",
            )

        for j in range(anchor + 1, index):
            surviving[j] = False

    return surviving


def eventos_da_linhagem_corrente(events: Sequence[Event]) -> list[Event]:
    """Os eventos cuja escrita sobrevive ao corte, na ordem do fluxo.

    A forma que o **avaliador** consome: ele não precisa das posições, precisa do
    mundo. O fold usa a máscara porque compõe posição a posição com as
    declarações do pack.
    """
    sobreviventes = escritas_sobreviventes(events)
    return [e for e, vive in zip(events, sobreviventes) if vive]
