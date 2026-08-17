"""A P3-5: o business state atravessa PROCESSO, e nao so a sessao.

`01` §4 poe Business State em Postgres e o declara *"nao reversivel por
rollback; so por reset total"*. Enquanto o dado morava em dicionario de modulo,
essa linha era falsa por um motivo que nenhuma fase anterior podia mostrar:
**reinicio nao e reset total**, e ate a Fase 3 nao havia container que
reiniciasse. Esta e a fase que tem, entao e aqui que a linha se conserta.

O PAR TEM DE ATRAVESSAR PROCESSO — e essa e a decisao central deste arquivo
----------------------------------------------------------------------------
Reabrir a sessao do SQLAlchemy no mesmo processo **nao discrimina**. `ALUNOS`,
`TURMAS`, `NOTAS` e `MATRICULAS` eram objetos do interpretador vivo: eles
sobreviveriam a qualquer `Session()` nova, e um teste construido assim ficaria
verde com a implementacao errada — que e a definicao de verificacao que parece
existir.

O pai escreve pela rota HTTP de verdade; um **interpretador novo** le. A unica
coisa compartilhada entre os dois e a tabela.

`06` T3 ja exigia isso do event store — *"reinicio do processo restaura a
projecao corrente sem intervencao"* —, e a peca 3 desta fase construiu o
mecanismo em `tests/_restaura_em_outro_processo.py`. Aqui e a MESMA pergunta na
camada de baixo de `01` §4, e o aparato e reaproveitado em vez de reinventado.

A MUTACAO QUE PROVA, e ela esta em `test_queda_de_sessao.py`? Nao — esta aqui
-------------------------------------------------------------------------------
Com a escrita voltando para dicionario de modulo, o filho nao encontra a nota.
Isso e medido em `ProvaNegativa`, plantando a mutacao no repositorio pelo mesmo
harness que a peca 3 usou.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.repositorio import Escopo, Repositorio
from domains.academus.api.surface import carregar
from domains.academus.models.registros import Enrollment, Grade, Student

from _academus_banco import URL, banco_limpo, exige_banco

REPO_ROOT = Path(__file__).resolve().parent.parent
LEITOR = REPO_ROOT / "tests" / "_le_business_state_em_outro_processo.py"

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

TITULAR = "P-3001"
TURMA = "T-2001"
ALUNO = "A-1001"

#: SEM regra de escopo — e o escopo da `secretaria`, que ve tudo. Usado nos
#: testes que falam com o repositorio direto, onde nao ha token para resolve-lo.
IRRESTRITO = Escopo(sub="S-1", regra=None)


@exige_banco
class AtravessaProcesso(unittest.TestCase):
    """O par da P3-5: o pai escreve pela rota, o filho le num interpretador novo."""

    def setUp(self) -> None:
        self.engine = banco_limpo()
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(montar(self.autenticacao, Repositorio(self.engine)))

    def _cabecalho(self, papel: str, sub: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, papel)}"}

    def _outro_processo(self) -> dict:
        """`python tests/_le_...py` — interpretador novo, sem nada compartilhado.

        `check=True` porque falha do filho e falha do teste: um `returncode`
        ignorado transformaria "o processo novo nao subiu" em "nao encontrou a
        nota", que sao coisas diferentes e teriam a mesma cor.
        """
        saida = subprocess.run(
            [sys.executable, str(LEITOR), TURMA, ALUNO],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "AURORA_TEST_DATABASE_URL": str(URL)},
            cwd=str(REPO_ROOT),
        )
        return json.loads(saida.stdout)

    def test_a_nota_lancada_pela_rota_e_lida_por_OUTRO_PROCESSO(self):
        """O caso central. Com dicionario de modulo, o filho nao acha nada."""
        resposta = self.cliente.post(
            f"/classes/{TURMA}/grades",
            json={"student_id": ALUNO, "value": 9.75},
            headers=self._cabecalho("professor", TITULAR),
        )
        self.assertEqual(resposta.status_code, 201)

        lido = self._outro_processo()
        self.assertIn([ALUNO, 9.75], lido["notas"])

    def test_a_matricula_feita_pela_rota_e_lida_por_OUTRO_PROCESSO(self):
        """O item 1 da DoD da Fase 3 escreve aqui, e a escrita dele tem de durar."""
        resposta = self.cliente.post(
            "/enrollment",
            json={"student_id": ALUNO, "class_id": TURMA},
            headers=self._cabecalho("secretaria", "S-1"),
        )
        self.assertEqual(resposta.status_code, 201)

        self.assertIn([ALUNO, TURMA], self._outro_processo()["matriculas"])

    def test_o_PAR_que_discrimina_o_que_nao_foi_escrito_nao_aparece(self):
        """Sem esta metade, um leitor que devolvesse tudo o que existe passaria.

        O filho le a mesma turma logo depois de o banco ser limpo e recarregado:
        as duas notas da fixture de demonstracao estao la, e a nota de 9,75 do
        teste anterior NAO — porque ela nao foi lancada neste caso.
        """
        lido = self._outro_processo()
        self.assertEqual([valor for _, valor in lido["notas"]], [8.5, 7.0])
        self.assertEqual(lido["matriculas"], [])

    def test_a_fixture_de_demonstracao_e_o_que_o_DEMO_precisa_e_nada_mais(self):
        """Seis registros, e a distincao com o seed da Fase 5 e o ponto.

        `07` Fase 5 e dona do dataset em escala e do determinismo por
        `RANDOM_SEED` (`06` T8). Se esta contagem crescer sem que a Fase 5 tenha
        chegado, alguem comecou o seed dentro da Fase 4 — e a linha entre fixture
        de demonstracao e dataset e exatamente a que a D8 pediu para ser dita.
        """
        with Session(self.engine) as sessao:
            self.assertEqual(len(sessao.scalars(select(Student)).all()), 2)
            self.assertEqual(len(sessao.scalars(select(Grade)).all()), 2)
            self.assertEqual(len(sessao.scalars(select(Enrollment)).all()), 0)


@exige_banco
class NaoHaMaisDicionarioDeModulo(unittest.TestCase):
    """A metade estrutural: o material com que o defeito se escreve saiu.

    O teste de processo prova a propriedade HOJE. Este nomeia a causa, para que
    um retorno ao estado em memoria apareca como *"a variavel de modulo voltou"*
    em vez de como uma falha de processo filho, que e onde ninguem olha primeiro.

    E a mesma forma da peca 2: em vez de detectar a divergencia, retirar o
    material — o modelo de registros nao tem mais colecao nenhuma no topo.
    """

    def test_registros_nao_expoe_colecao_de_modulo(self):
        from domains.academus.models import registros

        colecoes = {
            nome: type(valor).__name__
            for nome, valor in vars(registros).items()
            if not nome.startswith("_") and isinstance(valor, (dict, list, set))
            and nome != "CAMPOS_PUBLICOS"
        }
        self.assertEqual(
            colecoes,
            {},
            "colecao de modulo em `registros.py`: e por ai que o business state "
            "volta a viver no interpretador e a morrer no reinicio (P3-5)",
        )

    def test_o_repositorio_exige_engine_e_nao_tem_default(self):
        """Sem engine nao ha repositorio, e sem repositorio nao ha aplicacao.

        `montar` recebe o repositorio como argumento OBRIGATORIO — a assimetria
        com `degradador`, que e opcional, esta explicada la. Um default aqui so
        poderia ser um duplo em memoria, que e o dicionario de modulo voltando
        pela porta do wiring.
        """
        with self.assertRaises(TypeError):
            Repositorio()  # type: ignore[call-arg]

        with self.assertRaises(TypeError):
            montar(Autenticacao(superficie=carregar(), segredo=SEGREDO))  # type: ignore[call-arg]


@exige_banco
class OQueOEsquemaGarante(unittest.TestCase):
    """As FKs estao onde a rota ja garante a relacao — e a P4-5 onde nao estao."""

    def setUp(self) -> None:
        self.repositorio = Repositorio(banco_limpo())

    def test_matricula_em_turma_inexistente_nao_grava(self):
        self.assertIsNone(self.repositorio.matricular(ALUNO, "T-9999", IRRESTRITO))

    def test_matricula_de_aluno_inexistente_nao_grava(self):
        self.assertIsNone(self.repositorio.matricular("A-9999", TURMA, IRRESTRITO))

    def test_nota_em_turma_inexistente_nao_grava(self):
        self.assertIsNone(self.repositorio.lancar_nota("T-9999", ALUNO, 9.0, IRRESTRITO))

    def test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje(self):
        """A ausencia, afirmada em vez de omitida.

        `grades.student_id` nao tem FK, e a rota nao confere o aluno: a nota
        grava. Este teste existe para que a P4-5 seja **medida** e nao apenas
        escrita — e para que o dia em que ela for fechada tenha um teste
        vermelho anunciando a mudanca de comportamento, em vez de um verde
        silencioso.

        Por que nao fechar agora: por FK ali, `POST /classes/{class_id}/grades`
        passaria de 201 a erro de integridade — mudanca de comportamento de uma
        rota que a Fase 3 entregou e auditou, entrando por efeito colateral de
        migration. Vence na Fase 5, dona da trilha de `02` §4.1, que registra o
        aluno da alteracao de nota.
        """
        gravada = self.repositorio.lancar_nota(TURMA, "A-9999", 9.0, IRRESTRITO)
        self.assertEqual(gravada, {"student_id": "A-9999", "class_id": TURMA, "value": 9.0})

    def test_a_resposta_nao_carrega_a_chave_substituta(self):
        """`grade_id` e identidade de linha, e nao dado de negocio.

        A whitelist de `CAMPOS_PUBLICOS` e o que garante isso — serializar por
        reflexao poria na resposta toda coluna nova por ela existir, que e a D6
        aplicada ao business state.
        """
        gravada = self.repositorio.lancar_nota(TURMA, ALUNO, 7.5, IRRESTRITO)
        self.assertNotIn("grade_id", gravada)

    def test_o_diario_sai_em_ordem_estavel(self):
        """Sem `ORDER BY` o Postgres nao promete ordem, e a sala leria bagunca."""
        for valor in (1.0, 2.0, 3.0):
            self.repositorio.lancar_nota(TURMA, ALUNO, valor, IRRESTRITO)

        duas_leituras = [
            [n["value"] for n in self.repositorio.diario(TURMA, IRRESTRITO)]
            for _ in range(2)
        ]
        self.assertEqual(duas_leituras[0], duas_leituras[1])
        self.assertEqual(duas_leituras[0][-3:], [1.0, 2.0, 3.0])


if __name__ == "__main__":
    unittest.main()
