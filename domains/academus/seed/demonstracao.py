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

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from domains.academus.models.registros import Class, Grade, Student

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
ALUNOS = (
    ("A-1001", "Marina Alves Bueno", "Engenharia de Producao"),
    ("A-1002", "Rafael Setubal Nunes", "Ciencia da Computacao"),
)

TURMAS = (
    ("T-2001", "Estruturas de Dados", "2026.2", "P-3001"),
    ("T-2002", "Calculo Numerico", "2026.2", "P-3002"),
)

#: SEM chave substituta nos literais: `grade_id` e `autoincrement`, e fixar o
#: valor aqui reservaria dois numeros que o `POST` seguinte tentaria reusar — a
#: sequencia do Postgres nao anda quando a aplicacao escreve a chave.
NOTAS = (
    ("A-1001", "T-2001", 8.5),
    ("A-1002", "T-2001", 7.0),
)


def carregar(engine: Engine) -> None:
    """Grava os seis registros. Idempotente por chave primaria.

    As notas sao inseridas **so quando a turma ainda nao tem nenhuma**, porque
    elas nao tem chave natural: um `merge` por `grade_id` sintetizado inventaria
    identidade, e inserir sempre duplicaria a cada boot.
    """
    with Session(engine) as sessao:
        for student_id, name, program in ALUNOS:
            sessao.merge(Student(student_id=student_id, name=name, program=program))
        for class_id, subject, semester, professor_id in TURMAS:
            sessao.merge(
                Class(
                    class_id=class_id,
                    subject=subject,
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
