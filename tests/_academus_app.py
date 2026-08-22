"""O emissor que a guarda de boot exige — B1 e B2 da sexta auditoria da Fase 6.

POR QUE ESTE MODULO EXISTE
--------------------------
`domains/academus/api_surface.yaml` declara `emite: audit_query_performed` para
`GET /audit/grade-changes`, que e rota IMPLEMENTADA. A guarda de `montar` recusa
o boot quando a superficie declara `emite` e nao ha emissor ligado — `00` §5.5,
*"rota instrumentada em silencio e pior que rota nao instrumentada"*.

Ate a sexta auditoria a guarda NAO RECUSAVA: ela lia o `Superficie` como se fosse
um `dict`, quebrava com `AttributeError`, e o defeito ficou escondido atras dos
140 testes que pulavam por falta de Postgres. Com a guarda consertada, todo teste
que monta a `academus-api` a partir da superficie REAL precisa de emissor — e
isso nao e imposto pelo teste, e a producao aparecendo nele.

POR QUE UM `Emissor` DE VERDADE, E NAO UM DUPLO
-----------------------------------------------
O que a guarda pergunta e "ha emissor ligado?", e qualquer objeto responderia. O
`Emissor` real sobre um `InMemoryEventStore` custa o mesmo e mantem a montagem
identica a de producao: se a assinatura do emissor mudar, estes testes veem.

Quem AFIRMA sobre emissao e `tests/test_api_emissao_pela_rota.py`. Aqui o emissor
e infraestrutura de montagem, e o store e descartado.
"""

from __future__ import annotations

from datetime import datetime

from domains.academus.api.emissor import Emissor
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore


def emissor_de_teste() -> Emissor:
    """Um emissor sobre store em memoria, com relogio determinista.

    O relogio nao e `now` de parede: `InMemoryEventStore` carimba no `append`, e
    um teste que gravasse com o relogio da maquina teria carimbo diferente a cada
    execucao. Nenhum caso desta familia le o carimbo, e o determinismo e barato.
    """
    parede = iter(range(1_000_000, 1_100_000))
    return Emissor(
        store=InMemoryEventStore(
            ExerciseClock(
                datetime(2026, 8, 22, 9, 0, 0), now=lambda: float(next(parede))
            )
        )
    )
