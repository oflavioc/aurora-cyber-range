"""RBAC — o item 3 da DoD da Fase 3, sobre o stack ASGI de verdade.

*"RBAC nega acesso cruzado entre perfis."*

SEM DUPLO, PELA MESMA DECISAO DA PECA 3
----------------------------------------
`TestClient` fala ASGI com a aplicacao real: roteamento, dependencia global,
serializacao e codigo de status sao os de producao. Um cliente escrito a mao
seria o duplo que testa a si mesmo, e a Fase 2 fechou com zero mocks por decisao
registrada. `httpx` esta em `[project.optional-dependencies].test` justamente
para nao afirmar que ele e necessario para RODAR.

O TESTE MAIS IMPORTANTE DESTE ARQUIVO E O DE INDISTINGUIBILIDADE
------------------------------------------------------------------
403 confirma que o recurso existe **se e so se** a negacao o consultou. O canal
de inferencia que preocupa num exercicio sobre assimetria de informacao nao esta
no numero: esta em a resposta VARIAR com a existencia do recurso.

Aqui a negacao acontece numa dependencia global que recebe `Request` e mais
nada — nao ha repositorio ao alcance dela. Entao a propriedade e estrutural, e
`test_a_negacao_NAO_distingue_recurso_existente_de_inexistente` a afirma
comparando as duas respostas byte a byte.

Fechada essa porta, o codigo de status segue `06` T6, que fixa **403**.
"""

from __future__ import annotations

import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao, autoriza
from domains.academus.api.surface import carregar

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

ALUNO_QUE_EXISTE = "A-1001"
ALUNO_QUE_NAO_EXISTE = "A-9999"
TURMA_QUE_EXISTE = "T-2001"

#: O professor de `T-2001`, e o aluno que e ele mesmo. A peca 5 tornou o SUJEITO
#: relevante: ate a peca 4 qualquer `sub` servia, porque so o papel era julgado.
TITULAR = "P-3001"
OUTRO_PROFESSOR = "P-3002"


class RBAC(unittest.TestCase):
    def setUp(self) -> None:
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(montar(self.autenticacao))

    def _cabecalho(self, papel: str, sub: str = "U-1") -> dict[str, str]:
        token = self.autenticacao.emitir_token(sub, papel)
        return {"Authorization": f"Bearer {token}"}

    # -- o que o item 3 da DoD cobra ---------------------------------------

    def test_papel_declarado_le(self):
        for papel in ("aluno", "secretaria"):
            with self.subTest(papel=papel):
                resposta = self.cliente.get(
                    f"/alunos/{ALUNO_QUE_EXISTE}",
                    # O SUJEITO IMPORTA DESDE A PECA 5: um `aluno` so le a si
                    # mesmo, entao o `sub` dele e o proprio `aluno_id`. A
                    # `secretaria` nao tem regra de escopo e le qualquer um.
                    headers=self._cabecalho(
                        papel, ALUNO_QUE_EXISTE if papel == "aluno" else "S-1"
                    ),
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json()["aluno_id"], ALUNO_QUE_EXISTE)

    def test_ACESSO_CRUZADO_e_negado_nas_duas_direcoes(self):
        """Professor nao le aluno, e aluno nao le turma.

        As DUAS direcoes, e nao uma: um RBAC que negasse tudo passaria no
        primeiro caso, e e o par que discrimina — mesma forma do teste de
        reinicio pausado/correndo de `06` T5.
        """
        negado = self.cliente.get(
            f"/alunos/{ALUNO_QUE_EXISTE}", headers=self._cabecalho("professor")
        )
        self.assertEqual(negado.status_code, 403)

        tambem_negado = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}", headers=self._cabecalho("aluno")
        )
        self.assertEqual(tambem_negado.status_code, 403)

        permitido = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}", headers=self._cabecalho("professor", TITULAR)
        )
        self.assertEqual(permitido.status_code, 200)

    # -- 401 x 403 x 404 ---------------------------------------------------

    def test_sem_token_e_401_com_www_authenticate(self):
        resposta = self.cliente.get(f"/alunos/{ALUNO_QUE_EXISTE}")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.headers.get("WWW-Authenticate"), "Bearer")

    def test_token_de_outra_chave_e_401_e_nao_403(self):
        """Quem nao autenticou nao teve papel negado — ele nao tem papel."""
        outra = Autenticacao(superficie=carregar(), segredo="outro" * 10)
        alheio = outra.emitir_token("U-1", "secretaria")
        resposta = self.cliente.get(
            f"/alunos/{ALUNO_QUE_EXISTE}", headers={"Authorization": f"Bearer {alheio}"}
        )
        self.assertEqual(resposta.status_code, 401)

    def test_quem_TEM_direito_recebe_404_de_recurso_ausente(self):
        """404 e informacao, e vai para quem pode te-la."""
        resposta = self.cliente.get(
            f"/alunos/{ALUNO_QUE_NAO_EXISTE}", headers=self._cabecalho("secretaria")
        )
        self.assertEqual(resposta.status_code, 404)

    def test_a_negacao_NAO_distingue_recurso_existente_de_inexistente(self):
        """A propriedade que decide a pergunta de 403 x 404.

        Se a negacao consultasse o repositorio, `A-1001` e `A-9999` dariam
        respostas diferentes para o mesmo papel negado — e a diferenca seria um
        oraculo de enumeracao. Aqui as duas sao identicas, e sao identicas
        porque `autoriza` nao tem o repositorio ao alcance.
        """
        cabecalho = self._cabecalho("professor")
        existe = self.cliente.get(f"/alunos/{ALUNO_QUE_EXISTE}", headers=cabecalho)
        nao_existe = self.cliente.get(
            f"/alunos/{ALUNO_QUE_NAO_EXISTE}", headers=cabecalho
        )

        self.assertEqual(existe.status_code, nao_existe.status_code)
        self.assertEqual(existe.content, nao_existe.content)

    def test_o_corpo_da_negacao_nao_repete_o_recurso_pedido(self):
        """Mensagem que ecoa o id devolve pela resposta o que a negacao esconde."""
        resposta = self.cliente.get(
            f"/alunos/{ALUNO_QUE_EXISTE}", headers=self._cabecalho("professor")
        )
        self.assertNotIn(ALUNO_QUE_EXISTE, resposta.text)


class EscopoDeObjeto(unittest.TestCase):
    """P3-3 — a regra de objeto, e por que ela nao contradiz a peca 4.

    A peca 4 fixou 403 para negacao de PAPEL, decidida sem consultar recurso
    nenhum. Aqui a pergunta e outra — *"este recurso e seu?"* — e ela so pode ser
    respondida lendo o recurso.

    A saida nao e negar depois de achar: e fazer **"nao e sua" e "nao existe"
    virarem o mesmo caminho de codigo**. `repositorio.turma(id, escopo)` devolve
    `None` nos dois casos, e o handler, que so sabe tratar `None`, responde 404
    sem nunca aprender a diferenca.

    A politica continua sendo UMA: a resposta nunca varia com a existencia de um
    recurso que quem pergunta nao pode ver. 403 e 404 sao consequencias dela em
    perguntas diferentes.
    """

    def setUp(self) -> None:
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(montar(self.autenticacao))

    def _cabecalho(self, papel: str, sub: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, papel)}"}

    def test_proprio_o_aluno_le_a_si_mesmo_e_nao_ao_colega(self):
        meu = self.cliente.get(
            f"/alunos/{ALUNO_QUE_EXISTE}", headers=self._cabecalho("aluno", ALUNO_QUE_EXISTE)
        )
        self.assertEqual(meu.status_code, 200)

        alheio = self.cliente.get(
            "/alunos/A-1002", headers=self._cabecalho("aluno", ALUNO_QUE_EXISTE)
        )
        self.assertEqual(alheio.status_code, 404)

    def test_titular_o_professor_le_a_turma_dele_e_nao_a_do_colega(self):
        minha = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}", headers=self._cabecalho("professor", TITULAR)
        )
        self.assertEqual(minha.status_code, 200)

        alheia = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}",
            headers=self._cabecalho("professor", OUTRO_PROFESSOR),
        )
        self.assertEqual(alheia.status_code, 404)

    def test_papel_SEM_regra_de_escopo_ve_tudo(self):
        """A `secretaria` nao esta no mapa, e isso e desenho e nao esquecimento."""
        resposta = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}", headers=self._cabecalho("secretaria", "S-1")
        )
        self.assertEqual(resposta.status_code, 200)

    def test_recurso_ALHEIO_e_recurso_INEXISTENTE_sao_a_mesma_resposta(self):
        """A propriedade inteira da P3-3, num assert.

        Se fossem distinguiveis, um professor enumeraria as turmas da
        universidade pela diferenca entre "nao e sua" e "nao existe" — e saberia
        quais turmas existem sem poder ver nenhuma delas.
        """
        cabecalho = self._cabecalho("professor", OUTRO_PROFESSOR)
        alheia = self.cliente.get(f"/turmas/{TURMA_QUE_EXISTE}", headers=cabecalho)
        inexistente = self.cliente.get("/turmas/T-9999", headers=cabecalho)

        self.assertEqual(alheia.status_code, inexistente.status_code)
        self.assertEqual(alheia.content, inexistente.content)

    def test_o_diario_herda_o_escopo_da_turma(self):
        """Nota nao tem regra propria — ela e alcancada ATRAVES da turma.

        Uma segunda regra aqui seria a mesma regra escrita duas vezes, que e a
        classe D4. O teste afirma que a heranca acontece, em vez de confiar nela.
        """
        alheio = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}/diario",
            headers=self._cabecalho("professor", OUTRO_PROFESSOR),
        )
        self.assertEqual(alheio.status_code, 404)

        meu = self.cliente.get(
            f"/turmas/{TURMA_QUE_EXISTE}/diario",
            headers=self._cabecalho("professor", TITULAR),
        )
        self.assertEqual(meu.status_code, 200)

    def test_o_aluno_nao_matricula_o_colega(self):
        """A escrita tambem passa pelo escopo, e nao so a leitura.

        Sem isto, a regra protegeria a consulta e deixaria a acao aberta — que e
        a metade que costuma ser esquecida porque ninguem consulta para testar.
        """
        alheia = self.cliente.post(
            "/matricula",
            json={"aluno_id": "A-1002", "turma_id": TURMA_QUE_EXISTE},
            headers=self._cabecalho("aluno", ALUNO_QUE_EXISTE),
        )
        self.assertEqual(alheia.status_code, 404)

        minha = self.cliente.post(
            "/matricula",
            json={"aluno_id": ALUNO_QUE_EXISTE, "turma_id": TURMA_QUE_EXISTE},
            headers=self._cabecalho("aluno", ALUNO_QUE_EXISTE),
        )
        self.assertEqual(minha.status_code, 201)


class FalhaFechada(unittest.TestCase):
    """Rota que a superficie nao declara e negada em EXECUCAO, e nao so no CI.

    Sao dois mecanismos independentes: o gate protege o repositorio, e este
    protege o exercicio em curso. O gate reprova o commit; este nega o request
    de uma rota que chegou por outro caminho — registrada em tempo de execucao,
    montada por um router de terceiro, ou introduzida sem passar pelo CI.
    """

    def test_rota_nao_declarada_e_negada(self):
        aplicacao = FastAPI(dependencies=[Depends(autoriza)])

        @aplicacao.get("/rota-que-ninguem-declarou")
        async def oculta() -> dict:
            return {"vazou": True}

        aplicacao.state.autenticacao = Autenticacao(
            superficie=carregar(), segredo=SEGREDO
        )
        cliente = TestClient(aplicacao)

        token = aplicacao.state.autenticacao.emitir_token("U-1", "secretaria")
        resposta = cliente.get(
            "/rota-que-ninguem-declarou", headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertNotIn("vazou", resposta.text)


if __name__ == "__main__":
    unittest.main()
