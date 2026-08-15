"""O store em Postgres: persistencia, reinicio, e a cadeia que acusa reescrita.

VARIAVEL PROPRIA, E NAO `DATABASE_URL`
--------------------------------------
Estes testes ESCREVEM e LIMPAM a tabela. Apontar para `DATABASE_URL` faria um
`python -m unittest` distraido apagar o banco de desenvolvimento de quem
estivesse com o `.env` carregado.

`AURORA_TEST_DATABASE_URL` e explicita: quem a define esta dizendo que aquele
banco e descartavel. Ausente, os testes PULAM — e o `skip` diz como rodar, para
que pulo silencioso nao seja confundido com verde.

O QUE SE PROVA AQUI, e que o store em memoria nao consegue provar
------------------------------------------------------------------
O criterio de reinicio da `06` T3: uma instancia nova, sobre o mesmo banco,
reconstroi a projecao corrente. E a deteccao de reescrita, que so existe porque
ha uma tabela para reescrever.
"""

from __future__ import annotations

import os
import unittest

from contracts.generated.events import EXERCISE_STARTED, INJECT_FIRED, ROLLBACK_PERFORMED
from range_core.events.integrity import ChainBroken
from range_core.events.postgres_store import TABLE, PostgresEventStore, normalize_dsn
from range_core.state.simulation_state import project

from test_event_store import (  # reaproveita o duplo de relogio e os drafts
    FLAG,
    RelogioFixo,
    declarations,
    draft,
    started_draft,
)

DSN_ENV = "AURORA_TEST_DATABASE_URL"
_URL = os.environ.get(DSN_ENV)

RAZAO = (
    f"{DSN_ENV} nao definida. Estes testes escrevem e limpam a tabela, entao "
    "exigem banco declarado descartavel. Para rodar:\n"
    f"    {DSN_ENV}=postgresql+psycopg://user:senha@127.0.0.1:5432/base \\\n"
    "        python -m unittest discover -s tests"
)


@unittest.skipIf(_URL is None, RAZAO)
class _BaseComBanco(unittest.TestCase):
    """`setUp` e utilitarios. SEM teste proprio, de proposito.

    A primeira versao usava heranca entre classes de teste para reusar o
    `setUp`, e com isso os quatro casos da base RODAVAM DUAS VEZES — a contagem
    subia sem que nada a mais fosse provado. Base sem teste resolve: cada
    subclasse contribui so o que e dela.
    """

    def setUp(self) -> None:
        import psycopg

        self.dsn = normalize_dsn(_URL)
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(f"TRUNCATE {TABLE}")
        self.store = PostgresEventStore(RelogioFixo(), _URL)

    def _executa(self, sql: str, *params) -> None:
        import psycopg

        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, params)


@unittest.skipIf(_URL is None, RAZAO)
class StoreEmPostgres(_BaseComBanco):
    def test_grava_e_le_na_ordem_de_append(self):
        primeiro = self.store.append(started_draft())
        segundo = self.store.append(draft(INJECT_FIRED, inject_id="A01"))
        self.assertEqual(
            [e.event_id for e in self.store.read_all()],
            [primeiro.event_id, segundo.event_id],
        )

    def test_instancia_nova_sobre_o_mesmo_banco_restaura_a_projecao(self):
        """`06` T3 — reinicio do processo restaura sem intervencao.

        Instancia nova e o que um processo reiniciado tem: nenhum estado em
        memoria, so o banco.
        """
        self.store.append(started_draft())
        self.store.append(draft(INJECT_FIRED, inject_id="A01"))

        renascido = PostgresEventStore(RelogioFixo(), _URL)
        estado = project(renascido.read_all(), declarations())
        self.assertIs(estado.flags[FLAG], True)

    def test_rollback_persistido_reconstroi_sem_apagar(self):
        inicio = self.store.append(started_draft())
        self.store.append(draft(INJECT_FIRED, inject_id="A01"))
        self.store.append(draft(ROLLBACK_PERFORMED, payload={"to_event_id": inicio.event_id}))

        renascido = PostgresEventStore(RelogioFixo(), _URL)
        estado = project(renascido.read_all(), declarations())
        self.assertIs(estado.flags[FLAG], False)
        self.assertEqual(estado.simulation_epoch, 1)
        self.assertEqual(len(renascido.read_all()), 3, "nada foi removido")

    def test_sequencia_e_contigua_e_comeca_em_um(self):
        import psycopg

        for _ in range(4):
            self.store.append(started_draft())
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT sequence FROM {TABLE} ORDER BY sequence")
            self.assertEqual([linha[0] for linha in cur.fetchall()], [1, 2, 3, 4])


@unittest.skipIf(_URL is None, RAZAO)
class CadeiaAcusaReescrita(_BaseComBanco):
    """A garantia que a Fase 2 entrega no lugar do mecanismo da Fase 5.

    Nao ha `REVOKE` nem trigger ate a Fase 5 — quem tem a connection string
    reescreve. O que estes testes provam e que a reescrita **nao passa em
    silencio**.
    """

    def test_modificar_um_campo_quebra_a_cadeia(self):
        self.store.append(started_draft())
        self.store.append(draft(INJECT_FIRED, inject_id="A01"))

        self._executa(
            f"UPDATE {TABLE} SET producer = %s WHERE sequence = %s", "outro-produtor", 1
        )
        with self.assertRaises(ChainBroken) as capturado:
            self.store.read_all()
        self.assertIn("sequencia 1", str(capturado.exception))

    def test_remover_linha_do_meio_quebra_a_cadeia(self):
        for _ in range(3):
            self.store.append(started_draft())

        self._executa(f"DELETE FROM {TABLE} WHERE sequence = %s", 2)
        with self.assertRaises(ChainBroken):
            self.store.read_all()

    def test_trocar_o_payload_por_outro_valido_quebra_a_cadeia(self):
        """Reescrita que produz linha bem-formada continua sendo detectada.

        E o caso realista: nao um campo corrompido, mas um valor plausivel
        trocado por outro plausivel.
        """
        self.store.append(started_draft())
        self._executa(
            f"UPDATE {TABLE} SET payload = %s WHERE sequence = %s",
            '{"pack_id": "outro-pack"}',
            1,
        )
        with self.assertRaises(ChainBroken):
            self.store.read_all()

    def test_truncar_a_cauda_NAO_e_detectado(self):
        """O limite declarado, exercido em vez de so afirmado.

        Apagar as ultimas linhas deixa cadeia integra e sequencia contigua.
        Nenhum mecanismo interno a tabela pega isso — seria preciso ancora
        externa, que a Fase 2 nao inventa.

        O teste existe para que o limite seja VERIFICADO, e nao herdado como
        crenca: se um dia a deteccao passar a pegar truncamento, este teste fica
        vermelho e alguem atualiza a declaracao.
        """
        for _ in range(3):
            self.store.append(started_draft())

        self._executa(f"DELETE FROM {TABLE} WHERE sequence = %s", 3)
        self.assertEqual(len(self.store.read_all()), 2, "a cauda sumiu sem acusar")


@unittest.skipIf(_URL is None, RAZAO)
class DoisEscritoresConcorrentes(_BaseComBanco):
    """O caso que ninguem escreve por acidente.

    `sequence` e `previous_hash` sao escolhidos pela APLICACAO a partir da
    ultima linha — ler-e-escrever. Dois processos contra a mesma tabela podem,
    em tese, ler o mesmo topo e produzir duas linhas com a mesma sequencia, ou
    duas encadeadas no mesmo `previous_hash`: a cadeia BIFURCA, e a verificacao
    passaria a acusar sem que ninguem tenha adulterado nada.

    `_persist` toma `LOCK TABLE ... IN EXCLUSIVE MODE` antes de ler o topo,
    justamente por isso. Este teste existe porque "o lock resolve" e suposicao
    ate alguem tentar — e porque a alternativa seria confiar em que ninguem
    rodara dois escritores.

    O banco e a segunda linha de defesa, e nao a primeira: `sequence` e chave
    primaria e `row_hash` e unico, entao mesmo sem o lock a colisao viraria erro
    de integridade em vez de cadeia bifurcada em silencio.
    """

    def test_escritas_concorrentes_nao_bifurcam_a_cadeia(self):
        import threading

        import psycopg

        ESCRITORES, POR_ESCRITOR = 4, 5
        erros: list[BaseException] = []

        def escreve() -> None:
            try:
                store = PostgresEventStore(RelogioFixo(), _URL)
                for _ in range(POR_ESCRITOR):
                    store.append(started_draft())
            except BaseException as exc:  # pragma: no cover - so falha se houver corrida
                erros.append(exc)

        threads = [threading.Thread(target=escreve) for _ in range(ESCRITORES)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(erros, [], "append concorrente levantou")

        total = ESCRITORES * POR_ESCRITOR
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT sequence FROM {TABLE} ORDER BY sequence")
            sequencias = [linha[0] for linha in cur.fetchall()]

        self.assertEqual(
            sequencias,
            list(range(1, total + 1)),
            "sequencia com buraco ou repeticao: dois escritores leram o mesmo topo",
        )

        # A verificacao da cadeia e o teste de bifurcacao propriamente dito: se
        # duas linhas tivessem encadeado no mesmo `previous_hash`, o segundo elo
        # nao fecharia.
        eventos = PostgresEventStore(RelogioFixo(), _URL).read_all()
        self.assertEqual(len(eventos), total)
        self.assertEqual(len({e.event_id for e in eventos}), total)


if __name__ == "__main__":
    unittest.main()
