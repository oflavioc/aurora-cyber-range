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


def para_o_store(store, *, scenario_id: str, clock=None) -> Callable[[dict], object]:
    """O `emissor` que `Replay` chama — escreve no event store de verdade.

    `store` e um event store (o `append` de `09` §2); `scenario_id` vai na
    correlacao, como em todo evento do exercicio; `clock` produz o
    `ingest_time`.

    DEVOLVE UMA FUNCAO, e nao uma classe: `Replay.emissor` e
    `Callable[[dict], object]`, e o unico estado que existiria numa classe aqui
    — o conjunto do que ja saiu — ja e do `Replay`. Duas autoridades sobre "o
    que ja foi emitido" seria a duplicata que o item 6 (3) existe para impedir.

    `ingest_time` E DAQUI, E NAO DE `programar` — H1 da terceira auditoria
    -------------------------------------------------------------------------
    `00` §5.6 e `01` §3 pedem duas marcas para telemetria, e a divisao entre
    elas e a mesma divisao entre projecao e gravacao:

        `event_time`   quando o fato aconteceu. E funcao do GABARITO, entao sai
                       de `programar`, e o `cef.log` o escreve no prefixo syslog
        `ingest_time`  quando o SIEM recebeu. So existe no ato de gravar, e por
                       isso nao pode vir da projecao: o mesmo payload projetado
                       gravado duas vezes tem dois `ingest_time`

    E E ELA QUE TORNA A DISTINCAO VERIFICAVEL NO EVENTO. Num exercicio as duas
    ficam muito distantes — o acesso inicial e de `T-17d 02:14` e o sinal esta
    no SIEM desde o start (telemetria pre-posicionada, `08` §5).

    O INSTANTE E O DO EXERCICIO, e nao o de parede: `01` §3 congela o
    exercise-clock no PAUSAR, e um `ingest_time` de parede diria que o SIEM
    recebeu sinal durante uma sala parada.

    E ELE SAI DE `marks()`, que e a autoridade unica do rotulo: a mesma leitura
    que o store carimba no envelope. Formatar o rotulo aqui seria a segunda
    definicao de `T+HH:MM:SS`.

    > **A COINCIDENCIA, DITA:** neste motor `ingest_time` cai no mesmo instante
    > que o `exercise_time` do envelope, porque o `append` E a ingestao — nao ha
    > atraso de coletor simulado. O que `01` §3 exige e a distincao entre
    > ingestao e `event_time`, e essa e real e grande. Se um dia houver atraso
    > de coletor, e este campo que passa a diferir do envelope, e nao o
    > contrario.

    `clock` AUSENTE OMITE A MARCA, e a tolerancia tem limite declarado: o campo
    e opcional no contrato, entao um emissor montado sem clock (teste, dublê)
    continua produzindo payload valido. Quem compoe a producao e
    `InjectEngine`, que sempre o tem.
    """
    from range_core.events.envelope import Correlation
    from range_core.events.store import EventDraft

    def emitir(payload: dict):
        if clock is not None:
            payload = dict(payload, ingest_time=clock.marks().exercise_time)
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
