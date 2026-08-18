"""Os seis registros do DEMO. **Fixture de demonstracao — nao e seed.**

A DISTINCAO PRECISA SER DITA, porque ela vai parecer arbitraria
-----------------------------------------------------------------
`07` Fase 5 e dona do *"seed em escala com bulk insert"* e do determinismo por
`RANDOM_SEED` (`06` T8): 28 mil alunos, 8 semestres, distribuicao plausivel,
`COPY`/`executemany`, alvo de < 5 min, e byte-identico entre duas execucoes.

Isto nao e nada disso. Sao **seis linhas literais** para que o DEMO SCRIPT da
Fase 4 tenha o que matricular e o que lancar: sem aluno e sem turma, `POST
/enrollment` responde 404 e a degradacao do item 1 da DoD nao teria caminho
feliz do qual ser *diferenca*.

O nome do modulo e `demonstracao` e nao `seed` por isso, e a D8 exige que estas
linhas entrem **por caminho explicitamente nomeado como tal, e nao pela
migration** — migration que insere dado de demonstracao e historico que mente:
ela afirma que aquelas linhas fazem parte do esquema.

IDEMPOTENTE, e o motivo e operacional
---------------------------------------
O container da peca 7 sobe mais de uma vez sobre o mesmo volume, e a suite
carrega isto em todo `setUp`. Uma carga que duplicasse a cada chamada faria a
segunda execucao do DEMO ter dois de cada, e o `enrollments` sem unicidade nao
reclamaria. `merge` resolve pela chave primaria.

`enrollments` E `grades` NAO SAO CARREGADOS AQUI
--------------------------------------------------
`grades` tem duas linhas porque o diario precisa ter o que mostrar antes de
alguem lancar. `enrollments` comeca **vazia**, e isso e a forma do teste: o
caminho feliz do item 1 e a matricula acontecendo, e uma tabela pre-carregada
tornaria "matriculou" indistinguivel de "ja estava la".

DADOS SINTETICOS — `05` §3
---------------------------
Nomes inventados, matriculas fora de qualquer padrao real, nenhum identificador
que colida com pessoa existente. `tools/check_synthetic_data.py` varre as faixas.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from domains.academus.models.registros import (
    AcademicCalendar,
    Class,
    Course,
    Grade,
    Professor,
    Student,
    Subject,
)

#: O SEMESTRE DA FIXTURE, com as onze datas de `02` §2.
#:
#: Ele entra porque a 0003 ligou `classes.semester` ao calendario: sem esta
#: linha, carregar a fixture viola FK. As datas sao coerentes entre si — aulas
#: dentro do semestre, lancamento depois das aulas, retificacao depois do
#: lancamento — porque `within_window` sera calculado contra elas na peca 3, e
#: uma janela incoerente aqui produziria teste verde sobre semantica errada.
#:
#: ISTO E FIXTURE, E NAO SEED. As oito semestres coerentes de `02` §2 sao da peca
#: 4, com `RANDOM_SEED`. Aqui e uma linha, literal, para o DEMO ter turma.
SEMESTRE = "2026.2"
CALENDARIO = dict(
    semester=SEMESTRE,
    classes_start=date(2026, 8, 3),
    classes_end=date(2026, 12, 12),
    grade_entry_start=date(2026, 12, 14),
    grade_entry_end=date(2026, 12, 22),
    rectification_start=date(2027, 2, 1),
    rectification_end=date(2027, 2, 15),
    enrollment_start=date(2026, 7, 13),
    enrollment_end=date(2026, 7, 31),
    graduation_date=date(2027, 3, 20),
    admission_exam_start=date(2026, 11, 7),
    admission_exam_end=date(2026, 11, 8),
)

#: CURSO E DISCIPLINAS. Os nomes sao os que `program` e `subject` ja devolviam —
#: a resposta das rotas nao muda, e e isso que o par de `test_modelo_completo.py`
#: fixa. Trocar o texto aqui mudaria a resposta sem tocar em rota nenhuma.
CURSOS = (
    ("C-9001", "Engenharia de Producao"),
    ("C-9002", "Ciencia da Computacao"),
)
DISCIPLINAS = (
    ("D-8001", "Estruturas de Dados", "C-9002"),
    ("D-8002", "Calculo Numerico", "C-9001"),
)

#: OS TITULARES. A 0003 ligou `classes.professor_id` a `professors`, e os dois
#: identificadores sao os mesmos que a fixture da Fase 3 ja usava — `P-3001` e o
#: titular de `T-2001`, e a suite de RBAC depende disso.
PROFESSORES = (
    ("P-3001", "Helena Braga Portilho"),
    ("P-3002", "Otavio Rezende Mancini"),
)

#: OS LITERAIS SAO TUPLAS, e nao instancias de modelo no nivel do modulo.
#:
#: Instancia ORM guardada em constante e objeto com estado de sessao: a primeira
#: carga a deixa em um estado, a segunda a encontra nele, e o defeito aparece na
#: segunda chamada — que e exatamente a que o container faz. Tupla nao tem
#: estado, e cada carga constroi o seu.
#:
#: `A-1001` e o aluno que a suite usa como `proprio`; `P-3001` e o titular de
#: `T-2001`. Os identificadores sao os MESMOS da fixture em memoria da Fase 3 —
#: mudar o dado junto com a persistencia faria o par "antes e depois" comparar
#: duas coisas ao mesmo tempo.
#: `program` VIROU `course_id` na 0003, e o valor que a rota devolve continua
#: sendo o nome do curso — `C-9001` chama-se "Engenharia de Producao". A resposta
#: de `GET /students/A-1001` e byte a byte a mesma da Fase 4.
ALUNOS = (
    ("A-1001", "Marina Alves Bueno", "C-9001"),
    ("A-1002", "Rafael Setubal Nunes", "C-9002"),
)

#: `subject` virou `subject_id` pela mesma razao, e `D-8001` chama-se
#: "Estruturas de Dados".
TURMAS = (
    ("T-2001", "D-8001", SEMESTRE, "P-3001"),
    ("T-2002", "D-8002", SEMESTRE, "P-3002"),
)

#: SEM chave substituta nos literais: `grade_id` e `autoincrement`, e fixar o
#: valor aqui reservaria dois numeros que o `POST` seguinte tentaria reusar — a
#: sequencia do Postgres nao anda quando a aplicacao escreve a chave.
NOTAS = (
    ("A-1001", "T-2001", 8.5),
    ("A-1002", "T-2001", 7.0),
)


def carregar(engine: Engine) -> None:
    """Grava a fixture. Idempotente por chave primaria.

    A ORDEM E A DAS CHAVES ESTRANGEIRAS, e ela cresceu com a 0003: calendario e
    curso antes de disciplina e aluno, professor antes de turma. Sem isso o
    `flush` viola FK — e violaria com mensagem sobre a linha errada, que e o tipo
    de erro que se lê como "o banco esta quebrado".

    As notas sao inseridas **so quando a turma ainda nao tem nenhuma**, porque
    elas nao tem chave natural: um `merge` por `grade_id` sintetizado inventaria
    identidade, e inserir sempre duplicaria a cada boot.
    """
    with Session(engine) as sessao:
        sessao.merge(AcademicCalendar(**CALENDARIO))
        for course_id, name in CURSOS:
            sessao.merge(Course(course_id=course_id, name=name))
        for subject_id, name, course_id in DISCIPLINAS:
            sessao.merge(
                Subject(subject_id=subject_id, name=name, course_id=course_id)
            )
        for professor_id, name in PROFESSORES:
            sessao.merge(Professor(professor_id=professor_id, name=name))
        sessao.flush()

        for student_id, name, course_id in ALUNOS:
            sessao.merge(
                Student(student_id=student_id, name=name, course_id=course_id)
            )
        for class_id, subject_id, semester, professor_id in TURMAS:
            sessao.merge(
                Class(
                    class_id=class_id,
                    subject_id=subject_id,
                    semester=semester,
                    professor_id=professor_id,
                )
            )
        sessao.flush()

        com_nota = set(sessao.scalars(select(Grade.class_id).distinct()))
        for student_id, class_id, value in NOTAS:
            if class_id in com_nota:
                continue
            sessao.add(Grade(student_id=student_id, class_id=class_id, value=value))

        sessao.commit()
