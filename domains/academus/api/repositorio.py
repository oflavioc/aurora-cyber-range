"""A busca dos registros — e a unica porta por onde a regra de escopo passa.

A P3-3 RESOLVIDA: UM CAMPO, DUAS REGRAS, E ELA MORA AQUI
---------------------------------------------------------
A pendencia perguntava se o escopo de objeto era um campo ou tres. Com as tres
entidades da para ver: **e um campo**. Todos os casos sao *"um campo do recurso
e igual ao `sub` do token"*, e o que muda entre eles e QUAL campo — o que e
valor, e nao dimensao.

    `proprio`  — o recurso E o sujeito       (`Aluno.aluno_id == sub`)
    `titular`  — o recurso PERTENCE ao sujeito (`Turma.professor_id == sub`)

Papel fora do mapa nao tem restricao de objeto: a `secretaria` ve qualquer
aluno e qualquer turma, e isso e desenho, nao esquecimento.

POR QUE A REGRA MORA NA BUSCA, E NAO DEPOIS DELA
-------------------------------------------------
A peca 4 fechou o vazamento de existencia numa dependencia global que **nao tem
repositorio ao alcance**. A regra de objeto nao pode ser assim: decidir se a
turma e sua exige ler a turma.

Entao a saida nao e negar depois de achar — e fazer **"nao e sua" e "nao
existe" virarem o mesmo caminho de codigo**. `turma(id, escopo)` devolve `None`
nos dois casos, e o handler, que so sabe tratar `None`, responde 404 sem nunca
aprender a diferenca.

A propriedade da peca 4 continua valendo, e continua valendo pelo mesmo motivo:
**a resposta nunca varia com a existencia de um recurso que quem pergunta nao
pode ver.** As duas consequencias sao diferentes porque as perguntas sao
diferentes, e nao porque ha duas politicas:

- *"este papel pode usar esta rota?"* — 403, decidido sem consultar nada.
- *"este recurso e seu?"* — indistinguivel de *"nao existe"*, entao 404.

Um 403 aqui diria "existe, e nao e sua", que e exatamente o que a regra de
escopo existe para nao dizer.
"""

from __future__ import annotations

from dataclasses import dataclass

from domains.academus.api.surface import PROPRIO, TITULAR
from domains.academus.models.registros import (
    ALUNOS,
    MATRICULAS,
    NOTAS,
    TURMAS,
    Aluno,
    Matricula,
    Nota,
    Turma,
)


@dataclass(frozen=True, slots=True)
class Escopo:
    """O sujeito e a regra que vale para ele NESTA rota.

    `regra` vem da declaracao, resolvida por `autoriza` — o handler nunca a
    escolhe, e por isso nao tem como escolher errado.
    """

    sub: str
    regra: str | None


def aluno(aluno_id: str, escopo: Escopo) -> Aluno | None:
    registro = ALUNOS.get(aluno_id)
    if registro is None:
        return None
    if escopo.regra == PROPRIO and registro.aluno_id != escopo.sub:
        return None
    return registro


def turma(turma_id: str, escopo: Escopo) -> Turma | None:
    registro = TURMAS.get(turma_id)
    if registro is None:
        return None
    if escopo.regra == TITULAR and registro.professor_id != escopo.sub:
        return None
    return registro


def diario(turma_id: str, escopo: Escopo) -> list[Nota] | None:
    """As notas de uma turma. **Passa pela turma**, e o escopo vem de la.

    Nota nao tem regra propria, e nao e omissao: ela e alcancada atraves da
    turma, entao quem nao ve a turma nao ve o diario dela. Uma segunda regra
    aqui seria a mesma regra escrita duas vezes — a classe D4.
    """
    if turma(turma_id, escopo) is None:
        return None
    return [n for n in NOTAS if n.turma_id == turma_id]


def lancar_nota(turma_id: str, aluno_id: str, valor: float, escopo: Escopo) -> Nota | None:
    if turma(turma_id, escopo) is None:
        return None
    registro = Nota(aluno_id=aluno_id, turma_id=turma_id, valor=valor)
    NOTAS.append(registro)
    return registro


def matricular(aluno_id: str, turma_id: str, escopo: Escopo) -> Matricula | None:
    """Matricula. O escopo vale sobre o ALUNO — a turma e livre.

    Um aluno matricula a si mesmo em qualquer turma; a `secretaria` matricula
    qualquer um. Nao ha regra sobre a turma porque nao ha dono a comparar: o
    `titular` dela e o professor, e professor nao matricula.
    """
    if aluno(aluno_id, escopo) is None or turma_id not in TURMAS:
        return None
    registro = Matricula(aluno_id=aluno_id, turma_id=turma_id)
    MATRICULAS.append(registro)
    return registro
