"""A camada `reported` por persona — a projecao de LEITURA da view de participante.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §6: *"cada persona ve apenas sua camada `reported`"*;
`06_ACCEPTANCE_TESTS.md` T14: *"endpoint de persona nao vaza ground truth"*;
`09_EVENT_MODEL.md` §2 — as quatro verdades (+ `facilitation`).

O QUE ESTA PECA E, E O QUE ELA NAO E
-------------------------------------
E uma PROJECAO, e projecao nunca e fonte (`01` §4.1). O estado canonico e o event
store; esta funcao le o fluxo que o store devolve por `read_all()` e nao consulta
mais nada — nao le `ground_truth.yaml`, nao toca flag, nao materializa estado.
Espelha o `project` do fold na forma: funcao PURA de uma `Sequence[Event]`.

`reported` NAO E UM VALOR DE `truth_layer`. As acoes de participante nascem com
`truth_layer: participant_action` (ver o `CAMADA` do emissor), e a evidencia
observavel com `observable_evidence`. `reported` e a VIEW derivada por persona —
o recorte que uma persona pode ver da sua fatia do exercicio.

A FRONTEIRA DE FASE, DECLARADA
------------------------------
A Fase 8 entrega SO a ISOLACAO: nunca as camadas acima de `reported`, por persona,
frame total. O CONTEUDO divergente de `information_distribution.yaml` — a
subestimativa deliberada e a assimetria de `03` §4 — e Fase 10, e nao esta aqui.

O caso `persona is None` (broadcast/compartilhado) fica em ABERTO de proposito: e
conteudo, portanto Fase 10. Esta funcao nao o pina em nenhuma direcao — um evento
sem `persona` simplesmente nao casa `event.persona == P`, e a Fase 10 decide o que
fazer com ele sem ter de desfazer nada daqui.

O PREDICADO — UMA CONJUNCAO DE DUAS PERNAS
-------------------------------------------
Um evento entra no frame `reported` da persona P sse, e so se, as DUAS valem:

  1. `truth_layer` E REPORTAVEL — pertence a {`observable_evidence`,
     `participant_action`}. As camadas ACIMA de `reported` — `ground_truth`,
     `evaluator_assessment`, `facilitation` — NUNCA entram (T14, `03` §6), mesmo
     que um evento delas venha marcado para P. Declaracao nao vira verdade, e o
     que a persona ve nao pode incluir o gabarito nem a avaliacao do avaliador.
  2. o evento e ENDERECADO a P — `event.persona == P`. A fatia de outra persona
     nao entra: isolamento D1, falha fechada.

Nenhuma perna basta sozinha. A filtragem por camada sem a de persona vazaria a
fatia alheia; a de persona sem a de camada vazaria o gabarito marcado para P.

FRAME TOTAL, NUNCA DELTA — INV-7
---------------------------------
Devolve TODOS os reportaveis de P, e nao so o ultimo: o cliente pinta o payload,
e o frame e estado total. Um delta faria a tela depender de ter visto os frames
anteriores, que e o acoplamento que INV-7 existe para impedir.
"""

from __future__ import annotations

from collections.abc import Sequence

from range_core.events.envelope import Event

#: As camadas REPORTAVEIS — `09` §2. Sao as duas abaixo da fronteira de `reported`:
#: o que a equipe FAZ (`participant_action`) e o que o ambiente REVELA
#: (`observable_evidence`). As tres de cima — `ground_truth`,
#: `evaluator_assessment`, `facilitation` — ficam de fora por construcao.
#:
#: Whitelist, e nao blocklist das tres de cima: camada nova no catalogo nao entra
#: na view ate alguem vir aqui e dizer que ela e reportavel. O custo e uma
#: conversa, e e esse o ponto — o inverso deixaria uma camada nova vazar por
#: omissao.
REPORTAVEIS = frozenset({"observable_evidence", "participant_action"})


def project(persona: str, eventos: Sequence[Event]) -> Sequence[Event]:
    """O frame `reported` TOTAL da persona `persona`, projetado do fluxo.

    Funcao PURA: mesma entrada, mesma saida; nao le store, nao le gabarito, nao
    escreve nada. A ordem de `eventos` e preservada — o store carimba na ordem do
    exercicio, e a view nao reordena.

    A CONJUNCAO das duas pernas do predicado (ver o cabecalho): reportavel E
    endereçado a `persona`. Devolve `tuple` — imutavel, como o `_stored` do store,
    para que nenhum leitor mute o frame por acidente.
    """
    return tuple(
        evento
        for evento in eventos
        if evento.truth_layer in REPORTAVEIS and evento.persona == persona
    )
