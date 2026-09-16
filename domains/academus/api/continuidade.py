"""A tabela das sete acoes de continuidade academica — DADO puro, para injecao.

O QUE ESTE MODULO E, E O QUE ELE NAO E
--------------------------------------
E a metade de DOMINIO da acao de continuidade: *quais* flags cada acao move e
com que custo. Os nomes de flag sao `academus.*` — conhecimento do adapter, nao
do nucleo. Vive aqui, e entra no nucleo por INJECAO na raiz de composicao
(`montar(..., acoes_de_continuidade=CONTINUIDADE)`, T814), do mesmo jeito que
`personas_por_rota` e a `Sessao` ja entram da superficie. Assim o nucleo aplica
o efeito sem nunca importar `domains/` — o INV-4 e o ponto central da Fase 8.

O que este modulo **nao** faz, e por desenho (R9 §1): nao importa nucleo, nao
emite evento, nao le arquivo, nao executa nada no import. E uma tabela literal.

A FORMA, FIXADA PELO GATE T808 (`tests/test_continuidade.py`)
------------------------------------------------------------
`CONTINUIDADE: Mapping[action_id, tuple[Sequence[tuple[flag, value]], cost]]`:

- `action_id` — a chave. O CONJUNTO das sete e EXATAMENTE o enum fechado do
  `$def continuity_action_taken_payload` de `contracts/events.schema.yaml`
  (fechado na Wave 1, T801). O gate cobra a igualdade contra esse enum, que e o
  oracle independente: acao a mais ou a menos aqui reprova.
- `effects` — a sequencia de `(flag, value)`. Os nomes de flag sao as CONSTANTES
  geradas de `domains/academus/generated/flags.py` (T802), nunca literais
  (INV-5, `check_contract_literals.py`). `value` e o valor-alvo da flag.
- `cost` — o texto do "Custo" da tabela de `02_DOMAIN_ACADEMUS.md` §9:150-156,
  em PT-BR. Viaja no payload (D2); o gate exige que seja nao-vazio.

O default de cada flag no cenario e o OPOSTO do efeito, para que a mudanca seja
observavel — mas isso e estado do pack e do fold (T814), nao desta tabela.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domains.academus.generated.flags import (
    ACADEMUS_ACADEMIC_RECOVERY_ACTIVE,
    ACADEMUS_ENROLLMENT_DEADLINE_EXTENDED,
    ACADEMUS_EXAM_POSTPONED,
    ACADEMUS_GRADES_READONLY,
    ACADEMUS_MANUAL_ENROLLMENT_ACTIVE,
    ACADEMUS_OFFLINE_EXAM_MODE,
    ACADEMUS_TRANSCRIPT_ISSUANCE_BLOCKED,
)

#: Um efeito: o nome de uma flag e o valor-alvo. O nome vem sempre da constante
#: gerada; o valor e booleano nesta tabela (o `$def` admite tambem numero).
Efeito = tuple[str, bool]

#: A entrada de uma acao: a sequencia de efeitos e o texto do custo.
Acao = tuple[Sequence[Efeito], str]

#: A tabela. Chave = `action_id` (enum fechado do contrato). Injetada em
#: `montar()`; o endpoint deriva `effects`+`cost` dela e o fold aplica o efeito
#: lendo o PAYLOAD — nenhum nome de flag de dominio chega ao nucleo por import.
CONTINUIDADE: Mapping[str, Acao] = {
    "offline_exam": (
        [(ACADEMUS_OFFLINE_EXAM_MODE, True)],
        "Logística, atraso, risco de integridade",
    ),
    "freeze_grade_posting": (
        [(ACADEMUS_GRADES_READONLY, True)],
        "Trava o calendário",
    ),
    "manual_enrollment": (
        [(ACADEMUS_MANUAL_ENROLLMENT_ACTIVE, True)],
        "Capacidade limitada, fila física",
    ),
    "enrollment_deadline_extension": (
        [(ACADEMUS_ENROLLMENT_DEADLINE_EXTENDED, True)],
        "Impacto em calendário e repasse",
    ),
    "exam_postponement": (
        [(ACADEMUS_EXAM_POSTPONED, True)],
        "Conflito com colação",
    ),
    "emergency_document_issuance": (
        [(ACADEMUS_TRANSCRIPT_ISSUANCE_BLOCKED, False)],
        "Risco de emitir sobre dado não validado",
    ),
    "academic_recovery": (
        [(ACADEMUS_ACADEMIC_RECOVERY_ACTIVE, True)],
        "Custo docente",
    ),
}
