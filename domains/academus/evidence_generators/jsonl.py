"""O serializador JSONL compartilhado — um registro por fato, uma linha cada.

POR QUE UM HELPER, E NAO DUAS COPIAS
=====================================
`identity_audit` e `database_audit` sao as duas fontes JSONL de `08` §3, e o que
difere entre elas e **quais campos do fato cada uma carrega**, nunca como o
registro se escreve. R9 §8 — helper unico por semantica: duas copias do
serializador divergiriam na primeira mudanca de forma (ordem de chave,
`ensure_ascii`, separador), e a divergencia apareceria como *"as duas fontes
discordam sobre o mesmo fato"*, que e exatamente o que `08` §1 existe para
impedir.

A ORDEM DAS CHAVES E A DA DECLARACAO, e isso e determinismo (R7 §6): o registro
vira `sha256` no manifesto, e ordem de chave instavel mudaria o hash sem que
nada no fato tivesse mudado.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

__all__ = ["linhas"]


def linhas(fatos: Sequence[Mapping], campos: Sequence[str]) -> str:
    """Um registro JSON por fato, com os campos declarados que o fato tiver.

    **Campo ausente no fato nao vira chave nula.** `04` §3 exige apenas
    `fact_id`, `fact_class` e `exercise_time`; os demais sao opcionais, e um
    `null` no registro afirmaria que o valor foi medido e e vazio — que e
    diferente de nao ter sido registrado. O time azul le a diferenca.

    E `fact_id` NUNCA entra: `05` §6 — o arquivo vai para o participante, e o
    identificador de gabarito ali entrega o gabarito. A amarracao fato -> fonte
    e por conteudo, no elenco (peca 1 da Fase 9).
    """
    registros = []
    for fato in fatos:
        registro = {c: fato[c] for c in campos if c in fato}
        registros.append(json.dumps(registro, ensure_ascii=False, sort_keys=False))
    return "\n".join(registros)
