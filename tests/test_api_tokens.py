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

import os
import unittest
from pathlib import Path

import jwt as pyjwt

from domains.academus.api.auth import (
    Autenticacao,
    PapelDesconhecido,
    autenticacao_do_ambiente,
)
from domains.academus.api import tokens as dominio
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

#: A persona que o token de dominio passou a carregar — B1 da setima auditoria.
#: `09` §1.1 a exige em `participant_action`, e `01` §6 (spec-change #52) a
#: autoriza no adapter DESDE QUE ela nao autorize rota: papel autoriza, persona
#: identifica. `emitir_token` NAO julga o valor — julgar poria o vocabulario de
#: `03` §6 dentro do dominio —, e por isso nao ha teste de persona invalida aqui.
PERSONA = "ti"

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
                token = self.autenticacao.emitir_token(
                    "U-1", papel, PERSONA, now=AGORA
                )
                claims = dominio.verify(token, secret=SEGREDO, now=AGORA)
                self.assertEqual(claims.role, papel)
                self.assertEqual(claims.persona, PERSONA)

    def test_papel_de_EXERCICIO_nao_vira_token(self):
        for papel in ("facilitador", "operador", "avaliador"):
            with self.subTest(papel=papel):
                with self.assertRaises(PapelDesconhecido):
                    self.autenticacao.emitir_token("U-1", papel, PERSONA, now=AGORA)

    def test_a_PERSONA_nao_vira_papel_pela_porta_do_argumento(self):
        """`emitir_token("U-1", "ti", ...)` recusa, e a recusa e a topologia.

        `01` §6, na forma do spec-change #52: *"o que autoriza uma rota do
        adapter e papel de dominio, nunca persona"*. Como o adapter passou a
        aceitar `persona` no token, o eixo em que a guarda vale mudou de lugar —
        e este caso e o que prova que ela mudou de lugar em vez de sumir.

        A guarda e a mesma de sempre: `papeis_de_dominio` e lista de PERMITIDOS,
        e `ti` nao esta la. `scripts/check_api_surface.py` fecha a outra ponta
        recusando persona DENTRO daquela lista.
        """
        for persona in ("ti", "dpo", "pro_reitoria"):
            with self.subTest(persona=persona):
                with self.assertRaises(PapelDesconhecido):
                    self.autenticacao.emitir_token("U-1", persona, persona, now=AGORA)

    def test_papel_inventado_tambem_nao(self):
        """A guarda nao e uma lista de proibidos — e a lista de permitidos.

        Recusar so `facilitador`, `operador` e `avaliador` seria blocklist, e
        `reitor` passaria. O que existe e `papeis_de_dominio`, e o resto cai.
        """
        with self.assertRaises(PapelDesconhecido):
            self.autenticacao.emitir_token("U-1", "reitor", PERSONA, now=AGORA)

    def test_o_core_nao_conhece_papel_nenhum(self):
        """`issue` assina o que mandarem — e e isso que mantem a D2 no adapter.

        Se o core recusasse `facilitador`, ele conheceria desenho de exercicio;
        se recusasse `reitor`, conheceria dominio. Ele nao julga, e o unico
        lugar do produto que julga e `Autenticacao.emitir_token`.
        """
        token = issue("U-1", "qualquer-coisa", secret=SEGREDO, now=AGORA)
        self.assertEqual(verify(token, secret=SEGREDO, now=AGORA).role, "qualquer-coisa")


class BootDoAdapter(unittest.TestCase):
    """L3 da auditoria da Fase 3 — a funcao existia e ninguem a exercia.

    `autenticacao_do_ambiente` e o ponto onde o adapter monta a autenticacao a
    partir do ambiente, e a varredura do auditor achou **nenhum chamador e
    nenhum teste**. A recusa alta estava provada em `jwt_secret`, um nivel
    abaixo; que o BOOT DO ADAPTER a propaga, nao estava.

    A alternativa era apagar a funcao — ou tem consumidor e ganha prova, ou nao
    existe. Ela fica porque o consumidor tem data: a Fase 4 e quem monta o
    processo, e `01` §4 poe a `academus-api` em container ali. O que muda e que
    ela deixa de ser codigo nao exercido.

    O AMBIENTE E MANIPULADO E RESTAURADO, sem duplo: `jwt_secret` le `os.environ`
    por padrao, e injetar um dicionario aqui testaria o parametro em vez do
    caminho de boot — que e exatamente o que ja esta testado acima.
    """

    def setUp(self) -> None:
        self.anterior = os.environ.get(JWT_SECRET)
        self.addCleanup(self._restaura)

    def _restaura(self) -> None:
        if self.anterior is None:
            os.environ.pop(JWT_SECRET, None)
        else:
            os.environ[JWT_SECRET] = self.anterior

    def test_com_segredo_no_ambiente_o_adapter_monta(self):
        os.environ[JWT_SECRET] = SEGREDO
        autenticacao = autenticacao_do_ambiente()

        self.assertEqual(autenticacao.segredo, SEGREDO)
        self.assertIn("aluno", autenticacao.superficie.papeis_de_dominio)

        token = autenticacao.emitir_token("A-1001", "aluno", PERSONA, now=AGORA)
        self.assertEqual(
            dominio.verify(token, secret=SEGREDO, now=AGORA).sub, "A-1001"
        )

    def test_SEM_segredo_o_boot_do_adapter_RECUSA(self):
        """A recusa alta chega ate aqui, e nao para em `jwt_secret`.

        Um adapter que capturasse a excecao e subisse com segredo vazio passaria
        no teste de `jwt_secret` e falharia neste.
        """
        os.environ.pop(JWT_SECRET, None)
        with self.assertRaises(SecretUnavailable):
            autenticacao_do_ambiente()


class ClaimsDeclaradas(unittest.TestCase):
    def test_o_token_carrega_exatamente_o_declarado(self):
        """A mesma igualdade que o gate cobra por AST, agora em execucao.

        Duas provas do mesmo fato por caminhos diferentes: o gate le o codigo
        sem executa-lo, isto executa sem ler. Um erro que enganasse os dois
        precisaria ser o mesmo erro nas duas formas.

        O EMISSOR AQUI E O DO DOMINIO, e a troca e o B1 da setima auditoria: as
        claims declaradas em `domains/academus/api_surface.yaml` sao as DESTA
        superficie, e o `_payload` que tem de bater com elas e o de
        `domains/academus/api/tokens.py`. O do console assina `{sub, role, exp}`
        e serve outra vocacao — `range-core/api/app.py:259`.
        """
        declaradas = set(carregar().claims)
        token = dominio.issue("A-1001", "aluno", PERSONA, secret=SEGREDO, now=AGORA)
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
