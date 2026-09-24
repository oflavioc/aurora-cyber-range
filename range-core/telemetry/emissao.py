"""O emissor que liga o `Replay` ao event store — item 4, segunda metade.

AUTORIDADE
----------
`09_EVENT_MODEL.md` §4.1 (`telemetry_emitted`: `observable_evidence`,
`effect_class: machine`), `01_ARCHITECTURE.md` §4, `08_EVIDENCE_SIMULATOR.md`
§5, e o item 4 da DoD da Fase 9.

M4 DA SEGUNDA AUDITORIA — O QUE FALTAVA
========================================
`programar` produzia o payload, `Replay` decidia a hora, e **ninguem escrevia
nada**. `Replay.emissor` era um `Callable[[dict], object]` que em toda a arvore
recebia `list.append`: o unico lugar que punha `telemetry_emitted` num store era
`scripts/medida_do_exercicio_4h.py`, que monta o payload a mao.

O efeito nao era so "falta codigo". O item 7 mede a reconstrucao sobre um volume
de telemetria de 4 h, e esse volume **nao era produzido pelo range** — a medicao
media um exercicio que o produto nao gerava. E o binding de contrato por
`event_type`, escrito na primeira rodada, nao tinha emissor real que o
exercitasse.

O ENVELOPE E DAQUI; O PAYLOAD VEM PRONTO
=========================================
    truth_layer   `observable_evidence`  — `09` §4.1, a tabela e explicita
    producer      quem emitiu, por nome
    payload       o de `programar`, sem tocar

`actor_id` e `persona` ficam AUSENTES, e a ausencia e o que a camada significa:
telemetria nao e ato de participante. Preenche-los faria o computador de metrica
enxergar acao onde houve sinal de maquina — e `09` §4.1 marca
`metric_side: none` exatamente para que nenhum o leia.

O `fact_id` NAO ENTRA NO PAYLOAD, e agora ha duas guardas: `programar` o deixa
fora por construcao (ele viaja no `Programado`), e o contrato o torna
inexpressavel (`additionalProperties: false` sob o binding por `event_type`).
`05` §6 — o participante ve este evento no SIEM do exercicio.

O QUE ESTE MODULO NAO DECIDE
=============================
**Quando** emitir. Isso e do `Replay`, que le o clock de exercicio, e do
chamador, que o faz tocar. Aqui so se monta o rascunho e se chama `append`.
"""

from __future__ import annotations

from collections.abc import Callable

from contracts.generated.events import TELEMETRY_EMITTED

__all__ = ["PRODUTOR", "TRUTH_LAYER", "para_o_store"]

#: `09` §4.1 — a tabela poe `telemetry_emitted` em `observable_evidence`.
TRUTH_LAYER = "observable_evidence"

#: Quem assina. Nome proprio e nao `inject-engine`: o forwarder e outro emissor,
#: e o AAR distingue quem produziu o que.
PRODUTOR = "telemetry-forwarder"


def para_o_store(store, *, scenario_id: str) -> Callable[[dict], object]:
    """O `emissor` que `Replay` chama — escreve no event store de verdade.

    `store` e um event store (o `append` de `09` §2); `scenario_id` vai na
    correlacao, como em todo evento do exercicio.

    DEVOLVE UMA FUNCAO, e nao uma classe: `Replay.emissor` e
    `Callable[[dict], object]`, e o unico estado que existiria numa classe aqui
    — o conjunto do que ja saiu — ja e do `Replay`. Duas autoridades sobre "o
    que ja foi emitido" seria a duplicata que o item 6 (3) existe para impedir.
    """
    from range_core.events.envelope import Correlation
    from range_core.events.store import EventDraft

    def emitir(payload: dict):
        return store.append(
            EventDraft(
                event_type=TELEMETRY_EMITTED,
                truth_layer=TRUTH_LAYER,
                producer=PRODUTOR,
                correlation=Correlation(scenario_id=scenario_id),
                payload=payload,
            )
        )

    return emitir
