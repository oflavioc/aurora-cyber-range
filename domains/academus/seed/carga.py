"""A carga por `COPY`, e o dump canonico que prova o determinismo.

`01` §7 — *"seed via `COPY`/`executemany`, nunca ORM linha a linha. Alvo:
dataset completo em < 5 min"*. `02` §5 repete o alvo.

POR QUE `COPY` E NAO `executemany`
-----------------------------------
`01` §7 admite os dois. `COPY` foi o escolhido, e a razao e medivel: ele envia o
lote como fluxo, sem um round-trip de protocolo por linha nem plano de `INSERT`
por lote. Em milhoes de linhas a diferenca nao e de estilo.

O DUMP CANONICO — a outra metade da D6
----------------------------------------
`06` T8 exige dataset BYTE-IDENTICO entre duas execucoes. Provar isso exige uma
forma canonica do banco, e ela tem duas exigencias que nao sao obvias:

1. **`ORDER BY` explicito por tabela.** Sem ele o Postgres nao promete ordem
   nenhuma, e duas execucoes identicas produziriam dumps diferentes — o teste
   ficaria intermitentemente vermelho por um motivo que nao e o dele.

2. **A chave substituta NAO entra no hash de `grades`, `enrollments`,
   `academic_transcripts` e `attendance_records`.** Ela e identidade de linha
   atribuida pelo `BIGSERIAL`, e o que se quer provar e que o CONTEUDO e o mesmo.
   Num banco recem-migrado os numeros coincidem; num banco reusado, nao — e a
   propriedade que T8 cobra nao muda por causa disso.

   `audit_trail` e a excecao, e ela e deliberada: ali a `sequence` E conteudo,
   porque a cadeia de hash a inclui no material hasheado.
"""

from __future__ import annotations

import hashlib
import io

from sqlalchemy import Engine, text

from domains.academus.audit.trilha import ROLE_DA_APLICACAO
from domains.academus.seed.dataset import Dataset
from range_core.events.integrity import canonical_json

#: AS COLUNAS DE CADA TABELA, na ordem em que `dataset.gerar` as produz.
#:
#: Escrita, e nao derivada da metadata: derivada, ela concordaria com qualquer
#: coisa que o modelo dissesse — inclusive com uma coluna trocada de posicao, que
#: e o defeito que poria nome de aluno na coluna de curso sem nada acusar.
COLUNAS: dict[str, tuple[str, ...]] = {
    "academic_calendar": (
        "semester", "classes_start", "classes_end", "grade_entry_start",
        "grade_entry_end", "rectification_start", "rectification_end",
        "enrollment_start", "enrollment_end", "graduation_date",
        "admission_exam_start", "admission_exam_end",
    ),
    "users": ("user_id", "username", "display_name", "role", "password_hash", "active"),
    "courses": ("course_id", "name", "degree_level", "campus"),
    "professors": ("professor_id", "name", "user_id", "department"),
    "subjects": ("subject_id", "name", "course_id", "credits"),
    "students": ("student_id", "name", "course_id", "status", "entry_semester"),
    "classes": ("class_id", "subject_id", "semester", "professor_id"),
    "enrollments": ("student_id", "class_id", "status"),
    "grades": ("student_id", "class_id", "value"),
    "academic_transcripts": (
        "student_id", "subject_id", "semester", "final_grade", "result"
    ),
    "attendance_records": ("class_id", "student_id", "session_date", "present"),
    "diplomas": (
        "diploma_id", "student_id", "course_id", "campus", "issued_on",
        "issued_by_user_id",
    ),
    "scholarships": (
        "scholarship_id", "student_id", "kind", "percentage", "start_semester",
        "end_semester",
    ),
    "financing_contracts": (
        "contract_id", "student_id", "kind", "monthly_amount", "status", "signed_on"
    ),
    "exam_questions": (
        "question_id", "knowledge_area", "exam_year", "difficulty", "statement"
    ),
    "research_projects": (
        "project_id", "title", "principal_investigator_user_id", "funding_agency",
        "start_on", "end_on",
    ),
    "hpc_jobs": (
        "job_id", "project_id", "submitted_by_user_id", "submitted_at",
        "cpu_hours", "status",
    ),
    "rectification_authorizations": (
        "authorization_id", "requester_user_id", "approver_user_id",
        "justification", "process_number", "authorized_on",
    ),
    "access_delegations": (
        "delegation_id", "delegating_user_id", "delegate_user_id",
        "process_number", "valid_from", "valid_until", "reason",
    ),
    "audit_trail": (
        "sequence", "category", "actor_user_id", "source_ip", "user_agent",
        "occurred_at", "recorded_at", "object_type", "object_id", "payload",
        "within_window", "authorization_id", "previous_hash", "row_hash",
    ),
}

#: A ORDEM DE LEITURA do dump. `ORDER BY` explicito — ver o cabecalho.
ORDENACAO: dict[str, str] = {
    "academic_calendar": "semester",
    "users": "user_id",
    "courses": "course_id",
    "professors": "professor_id",
    "subjects": "subject_id",
    "students": "student_id",
    "classes": "class_id",
    "enrollments": "student_id, class_id",
    "grades": "student_id, class_id, value",
    "academic_transcripts": "student_id, subject_id, semester",
    "attendance_records": "class_id, student_id, session_date",
    "diplomas": "diploma_id",
    "scholarships": "scholarship_id",
    "financing_contracts": "contract_id",
    "exam_questions": "question_id",
    "research_projects": "project_id",
    "hpc_jobs": "job_id",
    "rectification_authorizations": "authorization_id",
    "access_delegations": "delegation_id",
    "audit_trail": "sequence",
}


def _texto(valor) -> str:
    """Serializa uma celula para o formato TEXT do `COPY`, com escape."""
    if valor is None:
        return r"\N"
    if isinstance(valor, bool):
        return "t" if valor else "f"
    if isinstance(valor, dict):
        valor = canonical_json(valor)
    else:
        valor = str(valor)
    return (
        valor.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def carregar(engine: Engine, dataset: Dataset) -> None:
    """Grava o dataset inteiro. Uma transacao, `COPY` por tabela, na ordem das FKs.

    UMA TRANSACAO SO, e a escolha e da propriedade que T8 cobra: um seed que
    falhasse no meio deixaria um banco meio populado, e a proxima execucao
    produziria um dataset diferente do da anterior — determinismo perdido por
    falha parcial, que e o caso em que ninguem procura.
    """
    bruto = engine.raw_connection()
    try:
        with bruto.cursor() as cursor:
            for tabela, linhas in dataset.tabelas.items():
                if not linhas:
                    continue
                colunas = ", ".join(COLUNAS[tabela])
                corpo = "".join(
                    "\t".join(_texto(celula) for celula in linha) + "\n"
                    for linha in linhas
                )
                # A ROLE RESTRITA VALE SO PARA A TRILHA, e a primeira versao
                # disto a assumia para a carga INTEIRA — com `permission denied`
                # em `academic_calendar` na primeira execucao. O erro estava
                # certo: `academus_app` tem `INSERT`+`SELECT` em `audit_trail` e
                # NADA nas outras dezenove, que e exatamente o que `02` §4 item 2
                # pede. Uma role que pudesse semear o banco inteiro nao seria a
                # role da trilha.
                #
                # `RESET ROLE` logo depois porque `SET LOCAL` vale ate o fim da
                # TRANSACAO, e nao do comando: sem ele, a role continuaria
                # assumida nas tabelas seguintes. Hoje `audit_trail` e a ultima
                # do dicionario e nada viria depois — e e exatamente esse tipo de
                # dependencia de ordem que reaparece no dia em que alguem
                # reordena e ninguem lembra por que a ordem importava.
                restrita = tabela == "audit_trail"
                if restrita:
                    cursor.execute(f"SET LOCAL ROLE {ROLE_DA_APLICACAO}")
                with cursor.copy(f"COPY {tabela} ({colunas}) FROM STDIN") as copia:
                    copia.write(corpo)
                if restrita:
                    cursor.execute("RESET ROLE")
        bruto.commit()
    finally:
        bruto.close()


def dump_canonico(engine: Engine) -> dict[str, str]:
    """SHA-256 por tabela, sobre o `COPY ... TO` ordenado. Ver o cabecalho."""
    #: A chave substituta sai do hash: ela e identidade de linha, e nao conteudo.
    #: `audit_trail` NAO esta aqui — ali a `sequence` e conteudo, porque a cadeia
    #: a inclui no material hasheado.
    sem_chave = {
        "grades": "grade_id",
        "enrollments": "enrollment_id",
        "academic_transcripts": "transcript_id",
        "attendance_records": "attendance_id",
    }

    digests: dict[str, str] = {}
    bruto = engine.raw_connection()
    try:
        with bruto.cursor() as cursor:
            for tabela, ordem in ORDENACAO.items():
                colunas = ", ".join(COLUNAS[tabela])
                assert tabela not in sem_chave or sem_chave[tabela] not in colunas
                consulta = f"SELECT {colunas} FROM {tabela} ORDER BY {ordem}"
                digest = hashlib.sha256()
                with cursor.copy(f"COPY ({consulta}) TO STDOUT") as copia:
                    for bloco in copia:
                        digest.update(bloco)
                digests[tabela] = digest.hexdigest()
    finally:
        bruto.close()
    return digests
