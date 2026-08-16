"""O JWT: o segredo que assina, e o que o token recusa.

O QUE ESTA SUITE PROVA QUE NAO E OBVIO
---------------------------------------
- O segredo segue a disciplina do `RANDOM_SEED` — ambiente primeiro, `.env`
  como fonte local, recusa alta e NENHUM valor padrao.
- O placeholder de `.env.example` e recusado. O teste LE o arquivo, entao os
  dois nao tem como divergir: repor um texto naquela linha deixa isto vermelho.
- `alg: none` e recusado. E o modo de falha que motivou usar `PyJWT` em vez de
  vinte linhas de `hmac`, e uma decisao motivada por um risco que ninguem
  exercita e uma decisao sem prova.
- O papel de EXERCICIO nao vira token — a metade da D2 que nenhum verificador
  de import pega.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import jwt as pyjwt

from domains.academus.api.auth import Autenticacao, PapelDesconhecido
from domains.academus.api.surface import carregar
from range_core.api.tokens import (
    ALGORITMO,
    JWT_SECRET,
    SecretUnavailable,
    TokenInvalid,
    issue,
    jwt_secret,
    verify,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Sintetico e com folga sobre o minimo. Nunca reutilizado fora da suite.
SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
OUTRO_SEGREDO = "outro-segredo-de-teste-com-mais-de-32-caracteres"

AGORA = 1_755_000_000.0


class Segredo(unittest.TestCase):
    def test_le_do_ambiente(self):
        self.assertEqual(jwt_secret({JWT_SECRET: SEGREDO}), SEGREDO)

    def test_ambiente_vence_o_dotenv(self):
        """Mesma ordem de `random_seed`, e pelo mesmo motivo operacional."""
        arquivo = REPO_ROOT / ".env.example"
        self.assertEqual(
            jwt_secret({JWT_SECRET: SEGREDO}, dotenv_path=arquivo), SEGREDO
        )

    def test_ausencia_levanta_sem_valor_padrao(self):
        with self.assertRaises(SecretUnavailable) as capturado:
            jwt_secret({})
        self.assertIn("Nao ha valor padrao", str(capturado.exception))

    def test_vazio_e_ausencia_sao_o_mesmo_caso(self):
        with self.assertRaises(SecretUnavailable):
            jwt_secret({JWT_SECRET: "   "})

    def test_curto_e_recusado(self):
        with self.assertRaises(SecretUnavailable) as capturado:
            jwt_secret({JWT_SECRET: "curto"})
        self.assertIn("minimo", str(capturado.exception))

    def test_o_placeholder_do_env_example_E_RECUSADO(self):
        """LE O ARQUIVO, e por isso os dois nao divergem.

        O placeholder e vazio de proposito: senha de banco copiada do exemplo
        falha no `connect`, e segredo de JWT copiado do exemplo FUNCIONA — com
        uma chave versionada neste repositorio. Se alguem repuser um texto ali,
        este teste fica vermelho antes de o servico subir com ele.
        """
        arquivo = REPO_ROOT / ".env.example"
        with self.assertRaises(SecretUnavailable):
            jwt_secret({}, dotenv_path=arquivo)


class Token(unittest.TestCase):
    def test_ida_e_volta(self):
        token = issue("A-1001", "aluno", secret=SEGREDO, now=AGORA)
        claims = verify(token, secret=SEGREDO, now=AGORA)
        self.assertEqual((claims.sub, claims.role), ("A-1001", "aluno"))

    def test_outra_chave_e_recusada(self):
        token = issue("A-1001", "aluno", secret=SEGREDO, now=AGORA)
        with self.assertRaises(TokenInvalid):
            verify(token, secret=OUTRO_SEGREDO, now=AGORA)

    def test_expirado_e_recusado(self):
        token = issue("A-1001", "aluno", secret=SEGREDO, valido_por=60, now=AGORA)
        verify(token, secret=SEGREDO, now=AGORA + 59)
        with self.assertRaises(TokenInvalid):
            verify(token, secret=SEGREDO, now=AGORA + 61)

    def test_alg_none_e_recusado(self):
        """O modo de falha que decidiu a dependencia, exercitado.

        Um verificador que lesse o `alg` do proprio token e confiasse nele
        aceitaria isto. A lista de algoritmos e do VERIFICADOR.
        """
        forjado = pyjwt.encode(
            {"sub": "A-1001", "role": "secretaria", "exp": int(AGORA) + 3600},
            key="",
            algorithm="none",
        )
        with self.assertRaises(TokenInvalid):
            verify(forjado, secret=SEGREDO, now=AGORA)

    def test_token_sem_exp_e_recusado(self):
        """Credencial eterna assinada corretamente ainda e credencial eterna."""
        sem_exp = pyjwt.encode(
            {"sub": "A-1001", "role": "aluno"}, SEGREDO, algorithm=ALGORITMO
        )
        with self.assertRaises(TokenInvalid):
            verify(sem_exp, secret=SEGREDO, now=AGORA)

    def test_adulterado_e_recusado(self):
        token = issue("A-1001", "aluno", secret=SEGREDO, now=AGORA)
        cabecalho, corpo, assinatura = token.split(".")
        with self.assertRaises(TokenInvalid):
            verify(f"{cabecalho}.{corpo}x.{assinatura}", secret=SEGREDO, now=AGORA)

    def test_lixo_e_recusado(self):
        with self.assertRaises(TokenInvalid):
            verify("nao-e-um-token", secret=SEGREDO, now=AGORA)


class VocabularioDePapel(unittest.TestCase):
    """A D2 como comportamento, e nao como combinado."""

    def setUp(self) -> None:
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)

    def test_papel_de_dominio_vira_token(self):
        for papel in ("aluno", "professor", "secretaria", "financeiro"):
            with self.subTest(papel=papel):
                token = self.autenticacao.emitir_token("U-1", papel, now=AGORA)
                self.assertEqual(verify(token, secret=SEGREDO, now=AGORA).role, papel)

    def test_papel_de_EXERCICIO_nao_vira_token(self):
        for papel in ("facilitador", "operador", "avaliador"):
            with self.subTest(papel=papel):
                with self.assertRaises(PapelDesconhecido):
                    self.autenticacao.emitir_token("U-1", papel, now=AGORA)

    def test_papel_inventado_tambem_nao(self):
        """A guarda nao e uma lista de proibidos — e a lista de permitidos.

        Recusar so `facilitador`, `operador` e `avaliador` seria blocklist, e
        `reitor` passaria. O que existe e `papeis_de_dominio`, e o resto cai.
        """
        with self.assertRaises(PapelDesconhecido):
            self.autenticacao.emitir_token("U-1", "reitor", now=AGORA)

    def test_o_core_nao_conhece_papel_nenhum(self):
        """`issue` assina o que mandarem — e e isso que mantem a D2 no adapter.

        Se o core recusasse `facilitador`, ele conheceria desenho de exercicio;
        se recusasse `reitor`, conheceria dominio. Ele nao julga, e o unico
        lugar do produto que julga e `Autenticacao.emitir_token`.
        """
        token = issue("U-1", "qualquer-coisa", secret=SEGREDO, now=AGORA)
        self.assertEqual(verify(token, secret=SEGREDO, now=AGORA).role, "qualquer-coisa")


class ClaimsDeclaradas(unittest.TestCase):
    def test_o_token_carrega_exatamente_o_declarado(self):
        """A mesma igualdade que o gate cobra por AST, agora em execucao.

        Duas provas do mesmo fato por caminhos diferentes: o gate le o codigo
        sem executa-lo, isto executa sem ler. Um erro que enganasse os dois
        precisaria ser o mesmo erro nas duas formas.
        """
        declaradas = set(carregar().claims)
        token = issue("A-1001", "aluno", secret=SEGREDO, now=AGORA)
        assinadas = set(
            pyjwt.decode(
                token,
                SEGREDO,
                algorithms=[ALGORITMO],
                # A expiracao nao e o que este teste afirma, e `AGORA` e um
                # instante fixo: conferi-la aqui faria o teste depender do
                # relogio da maquina para provar um fato sobre NOMES de claim.
                options={"verify_exp": False},
            )
        )
        self.assertEqual(assinadas, declaradas)


if __name__ == "__main__":
    unittest.main()
