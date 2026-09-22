"""`identity_audit.jsonl` — a projecao da trilha de identidade. `08` §3.

O QUE ESTA FONTE CARREGA
========================
`08` §3: *"conta de servico, criacao de sessao, escalada"*. E a fonte que liga o
acesso inicial a escalacao de privilegio — os dois fatos da Linha A que a
declaram —, e e nela que o time azul ve a **mesma conta** aparecendo nas duas
etapas.

E E ISSO QUE TORNA A CONSISTENCIA VERIFICAVEL. `06` T13 exige que as projecoes
de um fato apresentem *"usuario, IP e timestamp mutuamente consistentes"*; como
as duas saem do mesmo fato canonico, a consistencia nao e conferida depois — ela
e propriedade da construcao (`08` §1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domains.academus.evidence_generators.jsonl import linhas

__all__ = ["gerar", "CAMPOS"]

#: Os campos do fato que esta fonte carrega, na ordem em que sao escritos.
#:
#: `records_affected` fica FORA, e a exclusao e o desenho da fonte: volume de
#: registro e pergunta do banco, e `database_audit` e quem a responde. Uma fonte
#: que carregasse tudo faria as outras tres redundantes, e `08` §1 perderia o
#: que a torna util — fontes diferentes mostram ANGULOS diferentes do mesmo
#: fato, e o exercicio e correlaciona-las.
CAMPOS = (
    "exercise_time",
    "actor",
    "action",
    "source_ip",
    "dest",
    "credential_state",
    "mfa",
)


def gerar(fatos: Sequence[Mapping]) -> str:
    return linhas(fatos, CAMPOS)
