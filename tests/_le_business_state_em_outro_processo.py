#!/usr/bin/env python3
"""Le o business state — NUM PROCESSO NOVO. **Nao e teste**, dai o `_`.

`unittest discover` procura `test*.py`, entao este arquivo nao e coletado. Quem
o executa e `tests/test_business_state_postgres.py`, por `subprocess`.

POR QUE UM PROCESSO DE VERDADE, e por que reabrir a sessao nao serviria
------------------------------------------------------------------------
A P3-5 e sobre o business state morar em **dicionario de modulo**. Reabrir a
sessao do SQLAlchemy no mesmo processo **nao discrimina**: `ALUNOS`, `NOTAS` e
`MATRICULAS` sobreviveriam a isso sem esforco — sao objetos do interpretador
vivo —, e o teste passaria com a implementacao errada. A pergunta so tem
resposta com um interpretador **novo**, em que a UNICA coisa compartilhada com
quem escreveu e a tabela do Postgres.

E a mesma forma de `tests/_restaura_em_outro_processo.py`, que a peca 3 usou
para o event store, aplicada a outra camada de `01` §4.

O QUE ELE AINDA NAO E: um container. A divisao entre o que o processo prova e o
que so o container prova esta em `docs/progress/fase_4.md` §4.4.

USO
    python tests/_le_business_state_em_outro_processo.py <class_id> <student_id>
"""

from __future__ import annotations

import json
import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.academus.api.repositorio import engine_do_ambiente
from domains.academus.models.registros import Enrollment, Grade, Student


def main() -> int:
    class_id, student_id = sys.argv[1], sys.argv[2]
    engine = engine_do_ambiente(os.environ["AURORA_TEST_DATABASE_URL"])

    with Session(engine) as sessao:
        notas = sessao.scalars(
            select(Grade).where(Grade.class_id == class_id).order_by(Grade.grade_id)
        ).all()
        matriculas = sessao.scalars(
            select(Enrollment).where(Enrollment.student_id == student_id)
        ).all()
        alunos = sessao.scalars(select(Student).order_by(Student.student_id)).all()

        print(
            json.dumps(
                {
                    "notas": [[n.student_id, n.value] for n in notas],
                    "matriculas": [[m.student_id, m.class_id] for m in matriculas],
                    "alunos": [a.student_id for a in alunos],
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
