"""`06` T7 — auditoria imutavel, contra Postgres real.

Os tres criterios de T7, e cada um exige o banco de verdade:

    UPDATE e DELETE em `audit_trail` falham POR TRIGGER
    a role da aplicacao NAO POSSUI UPDATE, DELETE ou TRUNCATE
    adulteracao induzida faz `GET /audit/verify-chain` reportar a POSICAO EXATA

**Sao dois mecanismos e dois testes, e nao um.** O trigger recusa a todos; o
`REVOKE` recusa a role. Um teste so — "tentei alterar e falhou" — nao diria qual
dos dois recusou, e a diferenca importa: o trigger cai se alguem o desabilitar, e
o `REVOKE` cai se alguem regrantear. Provar os dois separadamente e o que torna
cada um verificavel sozinho.

E O TERCEIRO EXIGE ADULTERAR DE VERDADE
-----------------------------------------
A adulteracao e feita com a role de teste (dona da tabela), desabilitando o
trigger — que e exatamente o que a D13 declara como o limite do mecanismo: dono
passa. O ponto do teste e que a CADEIA acusa mesmo quando a prevencao nao
impediu, e com a posicao. Sem desabilitar o trigger nao ha como produzir uma
trilha adulterada para verificar — e um teste que so verificasse cadeia integra
provaria que a funcao roda, nao que ela detecta.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.repositorio import Contexto, Escopo, Repositorio
from domains.academus.api.surface import carregar
from domains.academus.audit import trilha

from _academus_banco import banco_limpo, exige_banco

SEGREDO = "segredo-de-teste-da-trilha-com-mais-de-32-caracteres"


def _contexto() -> Contexto:
    return Contexto(
        source_ip="198.51.100.7",  # RFC 5737 — `05` §3
        user_agent="Mozilla/5.0 (teste)",
        occurred_at=datetime.now(timezone.utc),
    )


@exige_banco
class TrilhaEhAppendOnly(unittest.TestCase):
    """T7, criterios 1 e 2 — trigger e role, provados separadamente."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.repositorio = Repositorio(self.motor)
        self.repositorio.lancar_nota(
            "T-2001", "A-1001", 9.0, Escopo(sub="P-3001", regra=None), _contexto()
        )

    def test_UPDATE_falha_por_trigger(self) -> None:
        with Session(self.motor) as sessao:
            with self.assertRaises(Exception) as capturado:
                sessao.execute(text("UPDATE audit_trail SET source_ip = '203.0.113.9'"))
                sessao.commit()
        self.assertIn("append-only", str(capturado.exception))

    def test_DELETE_falha_por_trigger(self) -> None:
        with Session(self.motor) as sessao:
            with self.assertRaises(Exception) as capturado:
                sessao.execute(text("DELETE FROM audit_trail"))
                sessao.commit()
        self.assertIn("append-only", str(capturado.exception))

    def test_a_role_da_aplicacao_nao_possui_UPDATE_DELETE_nem_TRUNCATE(self) -> None:
        """T7, criterio 2 — e este NAO e o trigger.

        `has_table_privilege` pergunta ao catalogo do Postgres, e nao ao
        comportamento: mesmo com o trigger desabilitado, a role continuaria sem o
        privilegio. E o que separa este teste do de cima.
        """
        with Session(self.motor) as sessao:
            for verbo in ("UPDATE", "DELETE", "TRUNCATE"):
                tem = sessao.execute(
                    text(
                        "SELECT has_table_privilege('academus_app', 'audit_trail', :v)"
                    ),
                    {"v": verbo},
                ).scalar()
                self.assertFalse(
                    tem, f"a role `academus_app` tem {verbo} sobre `audit_trail`"
                )

    def test_a_role_da_aplicacao_possui_INSERT_e_SELECT(self) -> None:
        """O par que impede o teste de cima de virar superticao.

        Uma role sem privilegio NENHUM passaria nos tres `assertFalse` acima e
        seria inutil: a trilha nao poderia ser escrita. `SELECT` entra porque a
        cadeia le a linha anterior para encadear.
        """
        with Session(self.motor) as sessao:
            for verbo in ("INSERT", "SELECT"):
                tem = sessao.execute(
                    text(
                        "SELECT has_table_privilege('academus_app', 'audit_trail', :v)"
                    ),
                    {"v": verbo},
                ).scalar()
                self.assertTrue(tem, f"a role nao pode {verbo}, e a trilha nao escreve")


@exige_banco
class CadeiaDetectaAdulteracao(unittest.TestCase):
    """T7, criterio 3 — a posicao exata da quebra."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.repositorio = Repositorio(self.motor)
        for valor in (7.0, 8.0, 9.0):
            self.repositorio.lancar_nota(
                "T-2001", "A-1001", valor, Escopo(sub="P-3001", regra=None), _contexto()
            )

    def _adultera(self, sql: str, **parametros) -> None:
        """Adultera com o trigger desligado — o limite que a D13 declara.

        Dono da tabela passa. E justamente por isso que a cadeia existe: ela
        continua vendo o que a prevencao nao impediu.
        """
        with self.motor.begin() as conexao:
            conexao.execute(text("ALTER TABLE audit_trail DISABLE TRIGGER USER"))
            conexao.execute(text(sql), parametros)
            conexao.execute(text("ALTER TABLE audit_trail ENABLE TRIGGER USER"))

    def test_a_trilha_intacta_e_integra(self) -> None:
        resultado = self.repositorio.verificar_trilha()
        self.assertTrue(resultado.integra)
        self.assertEqual(3, resultado.linhas)
        self.assertIsNone(resultado.quebra)

    def test_campo_alterado_e_detectado_na_posicao(self) -> None:
        self._adultera("UPDATE audit_trail SET source_ip = :ip WHERE sequence = 2",
                       ip="203.0.113.4")
        resultado = self.repositorio.verificar_trilha()
        self.assertFalse(resultado.integra)
        self.assertEqual(2, resultado.quebra.sequence)
        self.assertIn("hash gravado", resultado.quebra.motivo)

    def test_payload_alterado_e_detectado(self) -> None:
        """A NOTA trocada na trilha — a adulteracao que o exercicio investiga.

        E o caso do inject de `02` §4: alguem questiona se a propria trilha foi
        adulterada. Trocar o valor da nota registrada e a forma mais util de
        adulteracao, e a que o hash pega por conteudo.
        """
        self._adultera(
            "UPDATE audit_trail SET payload = jsonb_set(payload::jsonb, "
            "'{new_value}', '10.0')::json WHERE sequence = 1"
        )
        resultado = self.repositorio.verificar_trilha()
        self.assertFalse(resultado.integra)
        self.assertEqual(1, resultado.quebra.sequence)

    def test_linha_removida_do_meio_quebra_o_encadeamento(self) -> None:
        self._adultera("DELETE FROM audit_trail WHERE sequence = 2")
        resultado = self.repositorio.verificar_trilha()
        self.assertFalse(resultado.integra)
        # A SEQUENCIA acusa antes do hash: a linha 3 aparece onde se esperava a 2.
        self.assertEqual(3, resultado.quebra.sequence)
        self.assertIn("buraco ou reordenacao", resultado.quebra.motivo)

    def test_truncamento_da_cauda_NAO_e_detectado(self) -> None:
        """O LIMITE DECLARADO, exercido — e nao apenas escrito.

        `integrity.py` declara desde a Fase 2 que apagar as ultimas N linhas
        deixa cadeia integra e sequencia contigua. Este teste afirma o limite:
        se um dia ele ficar vermelho, alguem resolveu o problema e o registro
        precisa parar de dizer que ele existe.
        """
        self._adultera("DELETE FROM audit_trail WHERE sequence = 3")
        resultado = self.repositorio.verificar_trilha()
        self.assertTrue(resultado.integra, "o truncamento da cauda passou a ser visto")
        self.assertEqual(2, resultado.linhas)


@exige_banco
class NotaEhTrilhaNaMesmaTransacao(unittest.TestCase):
    """A P3-6: nota gravada sem linha de trilha e estado impossivel."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.repositorio = Repositorio(self.motor)

    def test_lancar_nota_grava_a_linha_de_trilha(self) -> None:
        antes = self.repositorio.verificar_trilha().linhas
        self.repositorio.lancar_nota(
            "T-2001", "A-1001", 8.0, Escopo(sub="P-3001", regra=None), _contexto()
        )
        self.assertEqual(antes + 1, self.repositorio.verificar_trilha().linhas)

    def test_a_linha_carrega_o_que_02_secao_4_1_exige(self) -> None:
        contexto = _contexto()
        self.repositorio.lancar_nota(
            "T-2001", "A-1001", 8.0, Escopo(sub="P-3001", regra=None), contexto
        )
        with Session(self.motor) as sessao:
            linha = sessao.execute(
                text("SELECT * FROM audit_trail ORDER BY sequence DESC LIMIT 1")
            ).one()

        self.assertEqual(trilha.ALTERACAO_DE_NOTA, linha.category)
        self.assertEqual("P-3001", linha.actor_user_id)      # usuario
        self.assertEqual(contexto.source_ip, linha.source_ip)  # IP
        self.assertEqual(contexto.user_agent, linha.user_agent)  # user-agent
        self.assertIsNotNone(linha.occurred_at)              # timestamp duplo
        self.assertIsNotNone(linha.recorded_at)
        self.assertEqual("2026.2", linha.payload["semester"])  # semestre
        self.assertEqual("D-8001", linha.payload["subject_id"])  # disciplina
        self.assertIsNone(linha.payload["previous_value"])   # nota anterior
        self.assertEqual(8.0, linha.payload["new_value"])    # nova nota
        self.assertIsNotNone(linha.within_window)            # within_window
        self.assertIsNone(linha.authorization_id)            # nulo quando nao houver

    def test_within_window_e_calculado_contra_a_janela_de_retificacao(self) -> None:
        """`02` §2: calculado NO MOMENTO DA GRAVACAO, contra o calendario.

        A fixture poe a janela de retificacao em fevereiro de 2027, e o teste
        roda hoje: `within_window` tem de ser `False`. Um `True` aqui diria que a
        comparacao nao esta olhando a janela certa — e a Linha B inteira depende
        de essa comparacao estar certa.
        """
        self.repositorio.lancar_nota(
            "T-2001", "A-1001", 8.0, Escopo(sub="P-3001", regra=None), _contexto()
        )
        with Session(self.motor) as sessao:
            dentro = sessao.execute(
                text("SELECT within_window FROM audit_trail ORDER BY sequence DESC LIMIT 1")
            ).scalar()
        self.assertFalse(dentro)

    def test_P4_5_nota_de_aluno_INEXISTENTE_passa_a_ser_recusada(self) -> None:
        """A P4-5 FECHADA, e este e o teste que a Fase 4 deixou armado ao contrario.

        `test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje` afirmava o
        comportamento antigo — 201 para aluno que nao existe. Ele fica vermelho
        neste commit, que era exatamente o anuncio combinado: a mudanca de
        comportamento chega anunciada por um teste, e nao por um verde silencioso.
        """
        registro = self.repositorio.lancar_nota(
            "T-2001", "A-NAO-EXISTE", 8.0, Escopo(sub="P-3001", regra=None), _contexto()
        )
        self.assertIsNone(registro)

    def test_aluno_inexistente_nao_deixa_nota_nem_trilha(self) -> None:
        """A recusa e ANTES da escrita, e nao um rollback depois dela.

        Se a nota fosse gravada e desfeita, a sequencia da trilha teria consumido
        um numero — e o buraco seria alarme falso, que e exatamente o que a D12
        recusou ao nao usar `BIGSERIAL`.
        """
        self.repositorio.lancar_nota(
            "T-2001", "A-NAO-EXISTE", 8.0, Escopo(sub="P-3001", regra=None), _contexto()
        )
        with Session(self.motor) as sessao:
            self.assertEqual(
                0, sessao.execute(text("SELECT count(*) FROM audit_trail")).scalar()
            )
            self.assertEqual(
                2, sessao.execute(text("SELECT count(*) FROM grades")).scalar()
            )


@exige_banco
class RotaDeVerificacao(unittest.TestCase):
    """`GET /audit/verify-chain` pelo stack ASGI — papel, forma e conteudo."""

    def setUp(self) -> None:
        self.motor = banco_limpo()
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(montar(self.autenticacao, Repositorio(self.motor)))

    def _cabecalho(self, papel: str, sub: str = "U-1") -> dict[str, str]:
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, papel)}"}

    def test_secretaria_verifica(self) -> None:
        resposta = self.cliente.get(
            "/audit/verify-chain", headers=self._cabecalho("secretaria")
        )
        self.assertEqual(200, resposta.status_code)
        self.assertEqual(
            {"linhas": 0, "integra": True, "quebra": None}, resposta.json()
        )

    def test_aluno_nao_verifica(self) -> None:
        """RBAC: `06` T6 exige que papel sem direito receba 403, e nao 200 vazio."""
        resposta = self.cliente.get(
            "/audit/verify-chain", headers=self._cabecalho("aluno", sub="A-1001")
        )
        self.assertEqual(403, resposta.status_code)

    def test_sem_token_nao_verifica(self) -> None:
        """`05` §8: caminho nao declarado publico exige token por falha fechada."""
        self.assertEqual(401, self.cliente.get("/audit/verify-chain").status_code)

    def test_a_resposta_tem_a_mesma_FORMA_com_e_sem_quebra(self) -> None:
        """O campo `quebra` existe nos dois casos.

        Resposta que muda de forma conforme o resultado obriga quem lê a
        descobrir a forma antes de ler o valor — e o wallboard da Fase 8 lê isto.
        """
        with self.motor.begin() as conexao:
            conexao.execute(
                text(
                    "INSERT INTO audit_trail (sequence, category, actor_user_id,"
                    " source_ip, occurred_at, recorded_at, object_type, object_id,"
                    " payload, previous_hash, row_hash) VALUES (1, 'grade_change',"
                    " 'P-3001', '198.51.100.7', now(), now(), 'grade', '1',"
                    " '{}', '" + "0" * 64 + "', 'hash-invalido')"
                )
            )
        corpo = self.cliente.get(
            "/audit/verify-chain", headers=self._cabecalho("secretaria")
        ).json()
        self.assertEqual({"linhas", "integra", "quebra"}, set(corpo))
        self.assertFalse(corpo["integra"])
        self.assertEqual(1, corpo["quebra"]["sequence"])


if __name__ == "__main__":
    unittest.main()
