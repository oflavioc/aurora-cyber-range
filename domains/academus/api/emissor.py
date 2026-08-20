"""A porta de emissão do adapter — o primeiro `append` fora do inject-engine.

AUTORIDADE
----------
`09_EVENT_MODEL.md` §1 e §6; `07_IMPLEMENTATION_PHASES.md` Fase 6, item 1 da
DoD; `domains/academus/observability_hooks.yaml`.

ERA A P4-2, E ELA VENCEU AQUI
------------------------------
A pendência dizia: *"a família `eventos` não roda no perfil de domínio, e emitir
sem declarar `emite` não tem guarda em lugar nenhum"*, com o gatilho declarado
sendo **o primeiro `append` fora do inject-engine**. Este módulo é esse append —
e a guarda entrou **antes** dele, na parte 1 desta peça: `check_api_surface.py`
exige `emite` de toda rota cujo `efeito` não seja `nenhum`, e confere a camada
contra o perfil da superfície.

O PRODUTOR NÃO CARIMBA O TEMPO
-------------------------------
`EventDraft` não tem campo para as marcas temporais, para o `simulation_epoch`
nem para o `event_id`: quem os carimba é o store, a partir do exercise-clock —
D1 do checkpoint da Fase 2. Aqui isso não é disciplina, é ausência de campo.

NENHUM LITERAL DE `event_type`
-------------------------------
A constante vem de `contracts.generated.events`, como o invariante 2 exige. Um
`event_type` escrito à mão aqui seria a quarta porta pela qual um tipo com erro
de digitação entra no sistema — e `09` §4 chama isso de a falha mais cara
possível, porque o evento nunca dispara e ninguém percebe até o exercício.

O VÍNCULO COM OBJETIVO NÃO PASSA POR AQUI
------------------------------------------
`09` §1.2 proíbe o campo de vínculo no envelope, e o invariante 4 o guarda por
AST. Não há onde escrevê-lo: `EventDraft` não tem o campo. Quem faz o binding é
a projeção — `range-core/objectives/projecao.py`, da peça 2 —, e é isso que
permite reavaliar um exercício antigo contra objetivos revisados.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.generated.events import AUDIT_QUERY_PERFORMED
from domains.academus.api.repositorio import Escopo
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, EventStore

#: `09` §2 — a `academus-api` é aplicação instrumentada, e o que ela grava é o
#: que a equipe fez. Nunca `facilitation`, que é do console.
CAMADA = "participant_action"

#: `09` §1.1 — quem produziu. O nome do serviço, e não o do módulo.
PRODUTOR = "academus-api"


@dataclass(frozen=True)
class Emissor:
    """O `append` do adapter, com a superfície mínima que as rotas usam.

    **Um método por hook**, e não um `append` genérico exposto ao handler. A
    diferença é a mesma que separa a degradação declarativa de um `if flag` no
    handler: com `append` genérico, cada rota decidiria sozinha camada, produtor
    e forma do payload, e a declaração de `observability_hooks.yaml` viraria
    documentação. Aqui o hook tem uma função, e a função é o que a rota chama.
    """

    store: EventStore

    def registrar_consulta(
        self,
        *,
        period_start: str,
        period_end: str,
        group_by: str | None,
        result_count: int,
        escopo: Escopo,
    ) -> None:
        """`audit_query_performed` — o hook declarado desde o esqueleto da Fase 1.

        Os `payload_fields` são **exatamente** os quatro que
        `observability_hooks.yaml` declara: `period_start`, `period_end`,
        `group_by` e `result_count`. Acrescentar campo aqui sem declarar lá faria
        o hook descrever um evento que não é o emitido.
        """
        self.store.append(
            EventDraft(
                event_type=AUDIT_QUERY_PERFORMED,
                truth_layer=CAMADA,
                producer=PRODUTOR,
                correlation=Correlation(),
                actor_id=escopo.sub,
                payload={
                    "period_start": period_start,
                    "period_end": period_end,
                    "group_by": group_by,
                    "result_count": result_count,
                },
            )
        )
