"""O resultado de um computador de métrica — a forma que o AAR recebe dos dois.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §3.2; `03_EXERCISE_DESIGN.md` §3 e §3.2.

POR QUE UM TIPO SÓ PARA OS DOIS LADOS
--------------------------------------
A partição de `00` §3.2 é sobre **insumo**, e não sobre resultado: o que ela
proíbe é um computador ter por onde ler o outro lado. Um tipo de saída
compartilhado não abre esse caminho — ele não carrega evento nenhum.

E o AAR é o escopo que recebe **as duas metades de cada par** e computa o delta
entre elas. Dois formatos de saída fariam esse escopo reconciliar antes de
subtrair, e a reconciliação é onde um `desde_t0` de um lado viraria um
`decorrido` do outro sem que nada acusasse.

`inicio` NÃO É SEMPRE T0, E É POR ISSO QUE ELE É CAMPO
-------------------------------------------------------
`03` §3 dá **start explícito** a `TTA`, `TTT` e `TTCM` — primeiro inject com
impacto observável, `incident_declared`, inject com `requires_response`. As
pareadas não têm coluna de start, e a redação-alvo do AAR em §3.2 as imprime em
`T+`, que é distância desde T0.

Guardar só a duração perderia a informação que o AAR precisa para escrever
*"Contenção declarada em T+31"* ao lado de *"Contenção verificável apenas em
T+52"*. Guardar só os instantes obrigaria o AAR a refazer o desconto — e duas
implementações da mesma regra divergem.

NÃO MARCADA NÃO É ZERO
-----------------------
`decorrido is None` diz que a métrica **não tem instante**: a declaração não
veio, o predicado não foi satisfeito, o par não foi completado. Zero pareceria
medição, e `03` §3.0 registra o custo disso — *"métrica que não dispara é pior
que métrica ausente, porque a ausência ao menos se vê"*.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Medida:
    """Uma sigla de `03` §3, com os dois extremos e o decorrido já descontado.

    `referencia` nomeia o objeto quando a sigla admite mais de uma ocorrência no
    mesmo exercício: `TTCM` é uma por inject com `requires_response`, e sem o
    `inject_id` o AAR teria uma lista de durações sem saber a que responde cada
    uma. As demais siglas ocorrem uma vez, e nelas ela é `None`.
    """

    sigla: str
    inicio: datetime | None
    fim: datetime | None
    decorrido: timedelta | None
    referencia: str | None = None

    @property
    def marcada(self) -> bool:
        """Houve instante a marcar? Falso não é zero — ver o cabeçalho."""
        return self.fim is not None


def nao_marcada(sigla: str, *, referencia: str | None = None) -> Medida:
    """A métrica que não disparou, escrita uma vez em vez de em cada ramo."""
    return Medida(
        sigla=sigla, inicio=None, fim=None, decorrido=None, referencia=referencia
    )
