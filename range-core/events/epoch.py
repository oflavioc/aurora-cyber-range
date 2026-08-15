"""A epoch corrente — calculo COMPARTILHADO, conferencia nao.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4.2; `09_EVENT_MODEL.md` §3; `06_ACCEPTANCE_TESTS.md` T3.

POR QUE COMPARTILHAR ESTE CALCULO
---------------------------------
Dois lugares precisam da epoch corrente: o **store**, que a carimba no append, e
a projecao **`simulation_state`**, que a devolve no estado reconstruido. Escrever
"epoch = contagem de rollbacks" nos dois e a classe que a D4 da Fase 1 desfez —
duas implementacoes da mesma regra, divergindo em silencio.

POR QUE A CONFERENCIA NAO VEM JUNTO
-----------------------------------
`_verify_epochs`, no fold, permanece **verificacao independente** e nao chama
esta funcao. Se chamasse, o fold estaria conferindo o numero contra o mesmo
codigo que o produziu, e a conferencia viraria tautologia: qualquer erro na regra
apareceria dos dois lados e se cancelaria.

Compartilha-se o CALCULO; a conferencia continua sendo uma segunda opiniao, que
e o que ela precisa ser para valer alguma coisa.

A EPOCH COMECA EM ZERO
----------------------
`06` T3 exige que evento da epoch 0 continue legivel apos rollback, e `09` §3
desenha `epoch 0` antes do primeiro rollback. Contagem de rollbacks da isso de
graca: nenhum rollback, epoch zero.

E a contagem contorna uma ambiguidade que a spec nao resolve, em vez de resolve-la
por inferencia: `01` §4.2 diz que `rollback_performed` "incrementa
`simulation_epoch`", enquanto o diagrama de `09` §3 desenha o proprio evento
DENTRO da epoch que ele encerra. Contar nao depende de qual das duas leituras
esta certa.
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.generated.events import ROLLBACK_PERFORMED

from range_core.events.envelope import Event


def current_epoch(events: Sequence[Event]) -> int:
    """Quantos rollbacks o fluxo registra — que e a epoch corrente."""
    return sum(1 for event in events if event.event_type == ROLLBACK_PERFORMED)
