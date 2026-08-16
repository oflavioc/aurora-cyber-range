"""Aluno e Turma — o minimo que o RBAC precisa para NEGAR alguma coisa.

DELIBERADAMENTE POBRE, E COM DATA
----------------------------------
`07` Fase 3 pede tres entidades (Aluno, Turma, Nota) e a peca 5 e quem as
entrega junto da degradacao declarativa. O que existe aqui e o que o item 3 da
DoD — *"RBAC nega acesso cruzado entre perfis"* — precisa para ser verificavel:
negacao sem rota que a exerca nao e propriedade, e rota sem recurso nao e rota.

Modelar agora o que a peca 5 vai modelar de novo seria inventar vocabulario
antes de o modulo existir — a classe D6 do catalogo. Entao: dois dataclasses,
um dicionario, e nada de repositorio abstrato.

DADOS SINTETICOS
----------------
`05` §7. Nomes inventados, matriculas fora de qualquer padrao real. O seed em
escala e da Fase 5, derivado do `RANDOM_SEED`; estes quatro registros sao
literais porque sao fixture de rota, nao dataset.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Aluno:
    aluno_id: str
    nome: str
    curso: str


@dataclass(frozen=True, slots=True)
class Turma:
    turma_id: str
    disciplina: str
    semestre: str


ALUNOS: dict[str, Aluno] = {
    "A-1001": Aluno("A-1001", "Marina Alves Bueno", "Engenharia de Producao"),
    "A-1002": Aluno("A-1002", "Rafael Setubal Nunes", "Ciencia da Computacao"),
}

TURMAS: dict[str, Turma] = {
    "T-2001": Turma("T-2001", "Estruturas de Dados", "2026.2"),
    "T-2002": Turma("T-2002", "Calculo Numerico", "2026.2"),
}


def como_json(registro) -> dict:
    """Serializacao rasa. `asdict` num dataclass sem aninhamento."""
    return asdict(registro)
