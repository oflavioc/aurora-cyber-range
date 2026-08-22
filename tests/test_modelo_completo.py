"""O modelo completo de `02` §1, e a prova de que nenhuma resposta de rota mudou.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
---------------------------------------
A peca 2 da Fase 5 faz as quatro tabelas da Fase 4 **crescerem**: `students`
troca `program` por `course_id`, `classes` troca `subject` por `subject_id`, e as
duas ganham chaves estrangeiras que nao existiam. Cada uma dessas mudancas pode
trocar a resposta de uma rota que a Fase 3 entregou e a Fase 4 auditou — que e
exatamente o que a D5 recusou fazer com `grades.student_id`.

**O par que anuncia.** `test_a_resposta_das_quatro_rotas_nao_mudou` fixa os
conjuntos de chaves que a Fase 4 devolvia. Se alguem acrescentar coluna a
`CAMPOS_PUBLICOS`, renomear `program` ou trocar a fonte de `subject` sem manter a
chave, este teste fica **vermelho** — e a mudanca de comportamento passa a ser
anunciada em vez de descoberta. E a mesma forma do
`test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje`, que a Fase 4 deixou armado
para o dia em que a P4-5 fechasse.

POR QUE A METADATA E CRUZADA COM O BANCO, E NAO CONFERIDA SOZINHA
------------------------------------------------------------------
Modelo declarativo e migration sao **duas descricoes do mesmo esquema**, e duas
copias divergem — foi o diagnostico que criou `check_pinned_images.py` para os
digests e `check_contract_examples.py` para as faixas sinteticas. Aqui a
conferencia e contra o banco de verdade, depois de `alembic upgrade head`: a
metadata que o codigo usa tem de descrever as tabelas que a migration criou.

Um teste que so olhasse a metadata provaria que o Python concorda com o Python.

EXIGE POSTGRES, e o pulo diz como rodar — `tests/_academus_banco.py`.
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.repositorio import Escopo, Repositorio
from domains.academus.api.surface import carregar
from domains.academus.models.registros import (
    AcademicCalendar,
    Base,
    Course,
    Student,
    como_json,
)
from domains.academus.seed import demonstracao

from _academus_app import emissor_de_teste
from _academus_banco import TABELAS, banco_limpo, exige_banco

SEGREDO = "segredo-de-teste-do-modelo-completo"

#: AS DEZENOVE TABELAS. Dezoito entidades de `02` §1 — menos `Incidente` e
#: `Declaracao`, que `01` §4 poe no event store — mais `access_delegations`, que
#: fecha a lacuna de §1 em relacao a §6.1.
#:
#: A LISTA E LITERAL, e nao derivada da metadata: derivada, ela concordaria com
#: qualquer coisa que o modelo dissesse, inclusive com uma tabela removida por
#: engano. Escrita, ela e uma afirmacao sobre o que a fase entregou.
TABELAS_ESPERADAS = {
    "academic_calendar",
    "academic_transcripts",
    "access_delegations",
    "attendance_records",
    "classes",
    "courses",
    "diplomas",
    "enrollments",
    "exam_questions",
    "financing_contracts",
    "grades",
    "hpc_jobs",
    "professors",
    "rectification_authorizations",
    "research_projects",
    "scholarships",
    "students",
    "subjects",
    "users",
}

#: O QUE CADA ROTA DA FASE 3 DEVOLVIA, e continua devolvendo. Copiado da resposta
#: real da Fase 4, e nao de `CAMPOS_PUBLICOS` — cruzar a whitelist consigo mesma
#: nao prova nada.
#: A TRILHA — no banco, fora da metadata. Ver os dois testes que a cruzam.
TRILHA = "audit_trail"

RESPOSTAS_DA_FASE_4 = {
    "aluno": {"student_id", "name", "program"},
    "turma": {"class_id", "subject", "semester", "professor_id"},
    "nota": {"student_id", "class_id", "value"},
    "matricula": {"student_id", "class_id"},
}


@exige_banco
class ModeloCompleto(unittest.TestCase):
    """As dezenove tabelas existem no banco, e a metadata as descreve."""

    def setUp(self) -> None:
        self.motor = banco_limpo()

    def test_as_dezenove_tabelas_existem_no_banco(self) -> None:
        no_banco = set(inspect(self.motor).get_table_names())
        faltando = TABELAS_ESPERADAS - no_banco
        self.assertEqual(
            set(), faltando, f"a migration nao criou: {sorted(faltando)}"
        )

    def test_a_metadata_descreve_as_mesmas_tabelas(self) -> None:
        """Modelo e migration sao duas descricoes do mesmo esquema.

        `event_store` fica de fora dos dois lados: ela e do core, tem migration
        propria e e lida por `psycopg` cru — o cabecalho de `Base` diz por que
        um modelo declarativo para ela poria o esquema do core sob a metadata de
        um adapter.

        `audit_trail` FICA DE FORA DA METADATA PELO MESMO MOTIVO, e a ausencia e
        mecanismo: ela e `INSERT`-only por `02` §4, e um modelo declarativo poria
        `session.merge()` ao alcance de quem a tocasse — um `UPDATE` que o
        trigger recusaria em producao, descoberto tarde. O acesso e por SQL cru
        em `domains/academus/audit/trilha.py`. `check_trilha_de_auditoria.py`
        reprova se alguem lhe der modelo.
        """
        self.assertEqual(TABELAS_ESPERADAS, set(Base.metadata.tables))
        self.assertNotIn(TRILHA, Base.metadata.tables)

    def test_a_trilha_existe_no_banco_mesmo_sem_modelo(self) -> None:
        """O par do teste acima: sem modelo, mas com tabela.

        Sem esta metade, "nao esta na metadata" seria satisfeito por uma trilha
        que nao existe em lugar nenhum.
        """
        self.assertIn(TRILHA, inspect(self.motor).get_table_names())

    def test_o_truncate_da_suite_cobre_toda_tabela_do_modelo_E_A_TRILHA(self) -> None:
        """Tabela fora de `TABELAS` sobreviveria ao `banco_limpo()`.

        E o dado de um teste entrando no proximo — a classe de defeito mais cara
        de diagnosticar numa suite, porque ela aparece como teste que passa
        sozinho e falha em conjunto.

        `audit_trail` ENTRA no truncate e NAO na metadata, e a assimetria e
        deliberada — ver o teste da metadata logo acima.
        """
        self.assertEqual(TABELAS_ESPERADAS | {TRILHA}, set(TABELAS))

    def test_a_janela_de_retificacao_existe_e_e_posterior_ao_lancamento(self) -> None:
        """`02` §2 e §4.1: `within_window` sera calculado contra estas datas.

        A coerencia entre elas nao e detalhe de fixture. A peca 3 vai comparar a
        data da alteracao com esta janela, e uma janela que comecasse antes do
        lancamento de notas tornaria "fora da janela" verdadeiro para o mundo
        normal — a Linha B inteira nasceria indistinguivel.
        """
        with Session(self.motor) as sessao:
            semestre = sessao.get(AcademicCalendar, demonstracao.SEMESTRE)
            self.assertIsNotNone(semestre)
            self.assertLess(semestre.classes_end, semestre.grade_entry_start)
            self.assertLess(semestre.grade_entry_end, semestre.rectification_start)
            self.assertLess(semestre.rectification_start, semestre.rectification_end)


@exige_banco
class RespostaNaoMudou(unittest.TestCase):
    """O PAR QUE ANUNCIA. Fica vermelho se alguma das quatro respostas mudar."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.repositorio = Repositorio(self.motor)

    def test_a_resposta_das_quatro_rotas_nao_mudou(self) -> None:
        aluno = self.repositorio.aluno("A-1001", Escopo(sub="A-1001", regra=None))
        turma = self.repositorio.turma("T-2001", Escopo(sub="P-3001", regra=None))
        diario = self.repositorio.diario("T-2001", Escopo(sub="P-3001", regra=None))
        matricula = self.repositorio.matricular(
            "A-1002", "T-2002", Escopo(sub="A-1002", regra=None)
        )

        self.assertEqual(RESPOSTAS_DA_FASE_4["aluno"], set(aluno))
        self.assertEqual(RESPOSTAS_DA_FASE_4["turma"], set(turma))
        self.assertEqual(RESPOSTAS_DA_FASE_4["nota"], set(diario[0]))
        self.assertEqual(RESPOSTAS_DA_FASE_4["matricula"], set(matricula))

    def test_program_e_subject_mudaram_de_fonte_e_nao_de_valor(self) -> None:
        """A ligacao nova devolve o MESMO texto que a coluna livre devolvia.

        Este e o teste que separa "a chave sobreviveu" de "o valor sobreviveu".
        Uma implementacao que devolvesse o `course_id` sob a chave `program`
        passaria no teste de chaves e quebraria a tela.
        """
        aluno = self.repositorio.aluno("A-1001", Escopo(sub="A-1001", regra=None))
        turma = self.repositorio.turma("T-2001", Escopo(sub="P-3001", regra=None))
        self.assertEqual("Engenharia de Producao", aluno["program"])
        self.assertEqual("Estruturas de Dados", turma["subject"])

    def test_coluna_nova_nao_vaza_para_a_resposta(self) -> None:
        """`status` e `entry_semester` existem na linha e NAO na resposta.

        A whitelist e o mecanismo, e este teste e o que a torna propriedade em
        vez de intencao: com `CAMPOS_PUBLICOS` serializando por reflexao, as duas
        apareceriam sozinhas — que e o defeito que a D6 da Fase 4 fechou para o
        wallboard e que aqui vale para o business state.
        """
        with Session(self.motor) as sessao:
            linha = sessao.get(Student, "A-1001")
            self.assertEqual("ativo", linha.status)

        aluno = self.repositorio.aluno("A-1001", Escopo(sub="A-1001", regra=None))
        self.assertNotIn("status", aluno)
        self.assertNotIn("entry_semester", aluno)
        self.assertNotIn("course_id", aluno)


@exige_banco
class FronteirasDoEsquema(unittest.TestCase):
    """O que a peca 2 deliberadamente NAO mudou."""

    def setUp(self) -> None:
        self.motor = banco_limpo()

    def test_grades_student_id_GANHOU_FK_na_peca_3(self) -> None:
        """A P4-5 fechada, do lado do esquema — e este teste anunciou.

        Ate a peca 2 ele dizia `..._continua_sem_FK` e afirmava a ausencia. Ficou
        **vermelho** na peca 3, junto do
        `test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje`, e os dois vermelhos
        ao mesmo tempo sao o que distingue "a P4-5 fechou" de "alguem pos uma FK".

        A FK sozinha teria sido mudanca de comportamento por efeito colateral de
        migration. Ela veio com o 404 na rota, que e o par que a D5 exigiu.
        """
        fks = inspect(self.motor).get_foreign_keys("grades")
        colunas = {coluna for fk in fks for coluna in fk["constrained_columns"]}
        self.assertIn("student_id", colunas)

    def test_classes_ganhou_as_tres_FKs_que_a_0002_nao_tinha(self) -> None:
        fks = inspect(self.motor).get_foreign_keys("classes")
        referenciadas = {fk["referred_table"] for fk in fks}
        self.assertEqual(
            {"subjects", "academic_calendar", "professors"}, referenciadas
        )

    def test_nenhuma_entidade_nova_e_serializavel_pela_API(self) -> None:
        """"Modelo completo" nao e "superficie completa".

        `como_json` recusa tipo ausente de `CAMPOS_PUBLICOS`, e as quinze
        entidades da peca 2 estao ausentes por decisao: nenhuma rota as serve. O
        dia em que uma precisar sair pela API, alguem escreve a linha — e nao
        descobre que ela ja saia.
        """
        with Session(self.motor) as sessao:
            curso = sessao.get(Course, "C-9001")
            with self.assertRaises(TypeError):
                como_json(curso)


@exige_banco
class RotasContinuamRespondendo(unittest.TestCase):
    """Ponta a ponta, pelo stack ASGI: o esquema novo nao quebrou a Fase 3."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(
            montar(self.autenticacao, Repositorio(self.motor), None, emissor_de_teste())
        )

    def _cabecalho(self, sub: str, papel: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, papel)}"}

    def test_GET_students_devolve_program_como_sempre(self) -> None:
        resposta = self.cliente.get(
            "/students/A-1001", headers=self._cabecalho("A-1001", "aluno")
        )
        self.assertEqual(200, resposta.status_code)
        self.assertEqual(
            {"student_id": "A-1001", "name": "Marina Alves Bueno",
             "program": "Engenharia de Producao"},
            resposta.json(),
        )

    def test_GET_classes_devolve_subject_como_sempre(self) -> None:
        resposta = self.cliente.get(
            "/classes/T-2001", headers=self._cabecalho("P-3001", "professor")
        )
        self.assertEqual(200, resposta.status_code)
        self.assertEqual(
            {"class_id": "T-2001", "subject": "Estruturas de Dados",
             "semester": "2026.2", "professor_id": "P-3001"},
            resposta.json(),
        )

    def test_POST_enrollment_continua_201(self) -> None:
        """A FK de `enrollments` nao mudou, e a rota ja conferia as duas pontas.

        E o caso que prova a razao 1 do cabecalho da 0003: as duas unicas rotas
        que escrevem nao receberam FK nova.
        """
        resposta = self.cliente.post(
            "/enrollment",
            json={"student_id": "A-1001", "class_id": "T-2002"},
            headers=self._cabecalho("A-1001", "aluno"),
        )
        self.assertEqual(201, resposta.status_code)


if __name__ == "__main__":
    unittest.main()
