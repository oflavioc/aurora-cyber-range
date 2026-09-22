"""`database_audit.jsonl` — a projecao da trilha do banco. `08` §3.

O QUE ESTA FONTE CARREGA, E POR QUE SAO AS DUAS LINHAS
=======================================================
`08` §3: *"leitura em massa (Linha A) e alteracoes de nota com IP e sessao
(Linha B)"*. E a **unica fonte que atravessa as duas linhas do exercicio**, e
isso nao e acaso: as duas deixam rastro na mesma trilha de banco, e separa-las
em arquivos distintos entregaria de graca a distincao que o participante precisa
descobrir — que ha dois incidentes, nao um (o OBJ-03, *"reconhecer incidentes
concorrentes"*).

**A Linha B so chega aqui desde a peca 3 da Fase 9.** Ate entao os fatos
`grade_change_retroactive` nao declaravam `projections`, e fato sem
`projections` e invisivel ao time azul por desenho (`08` §2) — entao a cobertura
passava e a linha de integridade simplesmente nao existia em arquivo nenhum.
Medido na peca 1, §2.3 do registro da fase.

`records_affected` E O QUE DISCRIMINA AS DUAS
==============================================
A leitura em massa traz milhares; cada alteracao de nota traz **um**. E o campo
que o time azul usa para separar os dois padroes sem que nada no arquivo lhe
diga qual e qual — leitura de evidencia, nao rotulo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domains.academus.evidence_generators.jsonl import linhas

__all__ = ["gerar", "CAMPOS"]

#: `dest` carrega o objeto tocado — o host na Linha A, a matricula do aluno na
#: Linha B. O mesmo campo com significados distintos e o que o fato declara, e a
#: fonte o espelha em vez de reinterpretar: reinterpretar seria a projecao
#: afirmando algo que o ground truth nao disse.
CAMPOS = (
    "exercise_time",
    "actor",
    "action",
    "source_ip",
    "dest",
    "records_affected",
)


def gerar(fatos: Sequence[Mapping]) -> str:
    return linhas(fatos, CAMPOS)
