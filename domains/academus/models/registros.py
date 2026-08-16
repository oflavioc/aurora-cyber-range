"""Aluno, Turma e Nota — as tres entidades de `07` Fase 3.

O CORTE, DECLARADO — porque "modelo completo" e NON-GOAL da fase
-----------------------------------------------------------------
`07` Fase 3 pede tres entidades e poe **modelo completo** e **seed em escala**
nos NON-GOALS. Sem o corte escrito, a peca cresce ate parecer a Fase 7 — entao
ele esta aqui, com motivo por linha.

**O que entra**

| | Por que |
|---|---|
| `Aluno`, `Turma`, `Nota` | sao as tres que `07` nomeia |
| `Turma.professor_id` | a regra de escopo `titular` da P3-3 precisa de um dono, e dono que nao existe no dado nao e verificavel |
| `Matricula` | o item 1 da DoD e `POST /matricula`, e rota que degrada precisa de um caminho feliz para a degradacao ser *diferenca* |
| dicionarios em memoria | ver abaixo |

**O que fica de fora, e onde vence**

| | Onde |
|---|---|
| tabela, `SQLAlchemy` e migration | **Fase 5** — `07` da a ela o seed e o dataset. Modelar agora seria modelar duas vezes, e a segunda apagaria a primeira |
| volume de `02` §6 (28 mil alunos) | **Fase 5**, derivado do `RANDOM_SEED`. Aqui sao seis registros literais, que sao fixture de rota e nao dataset |
| regra de negocio de nota — faixa, media, recuperacao, recalculo | nenhum item de DoD desta fase a exige, e inventa-la agora e vocabulario antes do modulo (D6) |
| Historico, Diploma, Bolsa, Contrato, e o papel `financeiro` | `02` §2 os lista, `07` Fase 3 nao. Papel declarado sem rota nao e buraco: e a superficie dizendo o que ainda nao existe |
| paginacao, filtro, busca | nao ha volume que as justifique nesta fase |
| trilha de auditoria e evento emitido pela API | **Fase 5** (`07` T7) e **Fase 8** — a §2 deste registro ja mediu que a Fase 3 nao emite `state_effect` |

**Em memoria, e nao em banco.** O event store e o Postgres da Fase 2; estes
registros nao sao estado de simulacao nem evento — sao o dado de negocio que a
Fase 5 vai semear. Um esquema provisorio criaria migration que a Fase 5 teria de
desfazer, e migration desfeita e historico que mente.

DADOS SINTETICOS
----------------
`05` §3. Nomes inventados, matriculas fora de qualquer padrao real, e nenhum
identificador que colida com pessoa existente.
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
    #: O DONO. E o que a regra `titular` compara com o `sub` do token, e sem ele
    #: a P3-3 seria uma declaracao sem nada em que se apoiar.
    professor_id: str


@dataclass(frozen=True, slots=True)
class Nota:
    aluno_id: str
    turma_id: str
    valor: float


@dataclass(frozen=True, slots=True)
class Matricula:
    aluno_id: str
    turma_id: str


ALUNOS: dict[str, Aluno] = {
    "A-1001": Aluno("A-1001", "Marina Alves Bueno", "Engenharia de Producao"),
    "A-1002": Aluno("A-1002", "Rafael Setubal Nunes", "Ciencia da Computacao"),
}

TURMAS: dict[str, Turma] = {
    "T-2001": Turma("T-2001", "Estruturas de Dados", "2026.2", "P-3001"),
    "T-2002": Turma("T-2002", "Calculo Numerico", "2026.2", "P-3002"),
}

NOTAS: list[Nota] = [
    Nota("A-1001", "T-2001", 8.5),
    Nota("A-1002", "T-2001", 7.0),
]

#: Escrito pelo `POST /matricula`. Lista, e nao dicionario, porque a chave seria
#: o par — e inventar chave composta e comecar o esquema que o corte adiou.
MATRICULAS: list[Matricula] = []


def como_json(registro) -> dict:
    """Serializacao rasa. `asdict` num dataclass sem aninhamento."""
    return asdict(registro)
