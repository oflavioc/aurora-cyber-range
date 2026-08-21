"""O `range-api` — o que trafega, o que empurra, e o que nao entra sem token.

A IGUALDADE MUDOU DE OBJETO NESTA PECA
---------------------------------------
Na peca 2 ela era sobre a FUNCAO: a mesma projecao, os mesmos bytes. Aqui e
sobre as DUAS ROTAS — e e onde ela pode quebrar, porque o corpo HTTP e o frame
do WebSocket passam por caminhos de codificacao diferentes e nenhum teste de
funcao alcanca essa diferenca.

Entao o que se compara e **o que trafega**: `response.content` de um lado,
`receive_bytes()` do outro. Nao o que a projecao devolveu.

O QUE ELE PEGA, MEDIDO — E O QUE NAO PEGA, E POR QUE ISSO ESTA CERTO
----------------------------------------------------------------------
Cada forma de divergencia foi PLANTADA e contada:

    JSONResponse (re-serializa com as MESMAS opcoes)   0 vermelhos
    re-serializacao com separadores padrao             2
    re-serializacao com `ensure_ascii`                 2
    chaves em ordem invertida                          2
    canal mandando TEXTO em vez de bytes               4

**O primeiro nao e buraco: e a forma canonica da peca 2 funcionando.** O
`JSONResponse` do FastAPI usa `separators=(",", ":")` e `ensure_ascii=False`, e
o produtor ja emite as chaves ORDENADAS — entao um `loads`/`dumps` devolve os
mesmos bytes, e a propriedade continua verdadeira. O teste afirma a
PROPRIEDADE, e nao o mecanismo que a produz; quando o mecanismo muda e a
propriedade se mantem, verde e a resposta certa.

Eu havia escrito o contrario — que este era o defeito que o teste pegava — e a
medicao derrubou a frase. Ela esta corrigida aqui e em `_json`, no lugar onde
seria lida.

"< 1 s" SEM CRONOMETRO
-----------------------
Numero de relogio oscila com a maquina. A forma que este projeto ja usou para o
mesmo problema foi o `EXPLAIN` sem `Seq Scan` do `_head()`: afirmar a
propriedade que produz o desempenho.

Aqui sao duas, e as duas sao contaveis:

  1. o frame e produzido na MESMA chamada que gravou o evento — nao ha polling,
     nao ha intervalo, nao ha tarefa de fundo;
  2. **um frame por evento, e nao um por cliente** — com tres telas conectadas,
     um disparo custa UMA reconstrucao, e nao tres. Contado por um store
     instrumentado.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

import yaml
from starlette.testclient import TestClient

from range_core.api import app as modulo_da_api
from range_core.api.app import Exercicio, montar
from range_core.api.superficie import Superficie, SuperficieError
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.inject_engine import Facilitator, InjectEngine
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import AdapterFlags, load_pack
from range_core.events.store import InMemoryEventStore
from range_core.state.cache import InMemoryProjectionCache

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests" / "fixtures"))
from pack_completo import materializa  # noqa: E402

#: PACOTE COMPLETO materializado em temporario — B1 da Fase 6.
PACK = materializa()
CREDENCIAL = "credencial-de-teste-longa"
SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres!!"


class StoreContado(InMemoryEventStore):
    """O store de verdade, com um contador de LEITURAS TOTAIS.

    Nao e duplo: e a mesma classe, com um contador. O que se mede e quantas
    reconstrucoes um disparo custa — e a resposta tem de ser a mesma com uma tela
    ou com tres.
    """

    def __init__(self, clock) -> None:
        super().__init__(clock)
        self.leituras = 0

    def read_all(self):
        self.leituras += 1
        return super().read_all()


def _monta() -> tuple[TestClient, Exercicio, StoreContado]:
    contratos = contract_source.read_contracts()
    flags = AdapterFlags.from_document(
        yaml.safe_load(
            (RAIZ / "domains" / "academus" / "flags.yaml").read_text(encoding="utf-8")
        ),
        source="domains/academus/flags.yaml",
    )
    pack = load_pack(PACK, contracts=contratos, adapter_flags=flags)
    clock = ExerciseClock(datetime(2026, 8, 16, 9, 0, 0))
    store = StoreContado(clock)
    exercicio = Exercicio(
        engine=InjectEngine(
            pack=pack,
            clock=clock,
            store=store,
            facilitator=Facilitator(user="operador-de-teste", role="control"),
            rollback_reasons=contract_source.rollback_reasons(contratos),
        ),
        cache=InMemoryProjectionCache(),
        declarations=pack.declarations,
        specs=flags.specs,
        textos=pack.textos_para_plateia,
        credencial=CREDENCIAL,
        segredo=SEGREDO,
    )
    return TestClient(montar(exercicio)), exercicio, store


class BaseDaApi(unittest.TestCase):
    def setUp(self) -> None:
        self.cliente, self.exercicio, self.store = _monta()
        self.addCleanup(self.cliente.close)

    @property
    def cabecalho(self) -> dict:
        resposta = self.cliente.post("/session", json={"credencial": CREDENCIAL})
        self.assertEqual(resposta.status_code, 200)
        return {"Authorization": f"Bearer {resposta.json()['token']}"}

    def _comeca(self) -> None:
        self.assertEqual(
            self.cliente.post("/exercise/start", headers=self.cabecalho).status_code, 200
        )


class IgualdadeDoQueTrafega(BaseDaApi):
    """A propriedade central, agora sobre as duas ROTAS."""

    def test_o_frame_do_canal_e_o_corpo_do_snapshot_sao_os_MESMOS_bytes(self) -> None:
        self._comeca()
        self.cliente.post("/injects/A01/fire", headers=self.cabecalho)

        for canal, snapshot in (
            ("/ws/wallboard", "/wallboard/state"),
            ("/ws/plateia", "/plateia/state"),
        ):
            with self.subTest(projecao=canal):
                corpo = self.cliente.get(snapshot).content
                with self.cliente.websocket_connect(canal) as ws:
                    frame = ws.receive_bytes()
                self.assertEqual(
                    frame, corpo,
                    "o canal e o snapshot entregaram bytes diferentes para o mesmo "
                    "estado: quem esta na sala e quem acabou de dar refresh veriam "
                    "coisas diferentes, e cada um dos dois estaria certo sozinho",
                )

    def test_o_snapshot_nao_re_serializa_o_que_a_projecao_produziu(self) -> None:
        """A metade estrutural do de cima: o corpo E o que a projecao produziu.

        Nao "equivalente como estrutura" — IDENTICO. E o eixo que pega qualquer
        re-serializacao que mude a codificacao: separadores padrao, `ensure_ascii`
        e ordem de chave foram plantados, e os tres ficam vermelhos aqui.
        """
        self._comeca()
        self.assertEqual(
            self.cliente.get("/wallboard/state").content,
            self.exercicio.frame_wallboard(),
        )

    def test_conectar_agora_recebe_o_estado_CORRENTE(self) -> None:
        """Item 3 da DoD, como propriedade do protocolo.

        O canal manda o estado inteiro no `accept`, antes de qualquer mudanca —
        entao quem recarrega o navegador nao espera pelo proximo inject. O par que
        discrimina: o estado depois do disparo e DIFERENTE do de antes.
        """
        self._comeca()
        with self.cliente.websocket_connect("/ws/plateia") as ws:
            antes = ws.receive_bytes()
        self.cliente.post("/injects/A01/fire", headers=self.cabecalho)
        with self.cliente.websocket_connect("/ws/plateia") as ws:
            depois = ws.receive_bytes()

        self.assertEqual(json.loads(antes)["texto"], "")
        self.assertIn("matrícula", json.loads(depois)["texto"])
        self.assertNotEqual(antes, depois)


class Latencia(BaseDaApi):
    """`< 1 s` afirmado por propriedade, e nao por cronometro."""

    def test_o_frame_chega_na_MESMA_chamada_que_gravou_o_evento(self) -> None:
        """Sem espera: o disparo responde e o frame ja esta na fila.

        Um canal que dependesse de polling deixaria a fila vazia aqui, e o
        `receive_bytes` seguinte travaria ate o timeout.
        """
        self._comeca()
        with self.cliente.websocket_connect("/ws/wallboard") as ws:
            ws.receive_bytes()  # o estado corrente, na conexao
            self.cliente.post("/injects/A01/fire", headers=self.cabecalho)
            depois = json.loads(ws.receive_bytes())

        # O PAYLOAD MUDOU DE FORMA NA PECA 6 (D16/D17): o telao passou a carregar
        # blocos com contagem, e nao a lista de itens. A pergunta deste teste e a
        # mesma — "o frame ja traz a mudanca?" — e a evidencia dela agora e a
        # contagem de ativos, que e o que o bloco carrega.
        ativos = sum(bloco["ativos"] for bloco in depois["paineis"])
        self.assertTrue(ativos, "o frame chegou sem a mudanca que o disparo causou")
        self.assertTrue(
            depois["destaques"], "o frame chegou sem o item que o disparo ativou"
        )

    def test_UM_frame_por_evento_e_nao_um_por_cliente(self) -> None:
        """A metade contavel, e a que sustenta o orcamento com a sala cheia.

        Tres telas conectadas, um disparo: o custo tem de ser o de UMA
        reconstrucao. Um hub que montasse por inscrito multiplicaria por tres, e
        nenhum cronometro numa suite de dezenas de eventos acusaria isso.
        """
        self._comeca()
        with self.cliente.websocket_connect("/ws/wallboard") as um, \
             self.cliente.websocket_connect("/ws/wallboard") as dois, \
             self.cliente.websocket_connect("/ws/wallboard") as tres:
            for ws in (um, dois, tres):
                ws.receive_bytes()

            antes = self.store.leituras
            self.cliente.post("/injects/A01/fire", headers=self.cabecalho)
            for ws in (um, dois, tres):
                ws.receive_bytes()
            custo_com_tres = self.store.leituras - antes

        self.assertLessEqual(
            custo_com_tres, 2,
            f"tres telas custaram {custo_com_tres} leituras totais do store. O "
            "frame tem de ser montado UMA vez e entregue a todos.",
        )

    def test_nao_ha_espera_nem_tarefa_de_fundo_no_caminho_do_frame(self) -> None:
        """A metade estrutural: o material do polling nao esta ao alcance.

        Mesma forma do `test_nada_aqui_sabe_que_horas_sao` da peca 2 — provar por
        comportamento exigiria observar ausencia de atraso, que e a asserção que
        passa quando nada e observavel.
        """
        for modulo in (modulo_da_api, __import__("range_core.api.hub", fromlist=["x"])):
            fonte = Path(modulo.__file__).read_text(encoding="utf-8")
            importados: set[str] = set()
            for node in ast.walk(ast.parse(fonte)):
                if isinstance(node, ast.Import):
                    importados.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    importados.add((node.module or "").split(".")[0])
            with self.subTest(modulo=Path(modulo.__file__).name):
                self.assertNotIn("time", importados)
                self.assertNotIn("threading", importados)
                self.assertNotIn("sched", importados)


class TodaRotaQueMoveOExercicioPublica(unittest.TestCase):
    """A coluna `efeito` da peca 1, ganhando o segundo consumidor.

    Esquecer o `publicar` numa rota nova produz o pior defeito desta fase: o
    exercicio anda e a sala nao ve. Nao ha como um teste de comportamento cobrir
    a rota que ainda nao existe — mas a DECLARACAO ja diz quais movem o
    exercicio, e por AST da para exigir que todas publiquem.
    """

    def test_o_publicar_esta_em_toda_rota_de_efeito(self) -> None:
        documento = yaml.safe_load(
            (RAIZ / "range-core" / "api_surface.yaml").read_text(encoding="utf-8")
        )
        movem = {
            (r["method"].upper(), r["path"])
            for r in documento["rotas"]
            if r.get("efeito") != "nenhum" and r.get("status") == "implementada"
        }
        self.assertTrue(movem, "nenhuma rota implementada move o exercicio: vacuo")

        arvore = ast.parse(Path(modulo_da_api.__file__).read_text(encoding="utf-8"))
        publicam: set[tuple[str, str]] = set()
        for node in ast.walk(arvore):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            chamadas = {
                filho.func.id
                for filho in ast.walk(node)
                if isinstance(filho, ast.Call) and isinstance(filho.func, ast.Name)
            }
            if "_publica" not in chamadas:
                continue
            for decorador in node.decorator_list:
                if (
                    isinstance(decorador, ast.Call)
                    and isinstance(decorador.func, ast.Attribute)
                    and decorador.args
                    and isinstance(decorador.args[0], ast.Constant)
                ):
                    publicam.add(
                        (decorador.func.attr.upper(), decorador.args[0].value)
                    )

        self.assertEqual(
            movem - publicam, set(),
            "rota que move o exercicio e nao publica: o exercicio anda e a sala "
            "nao ve",
        )


class FalhaFechada(BaseDaApi):
    """`05` §8 — so wallboard e participant-view ficam sem autenticacao."""

    def test_o_console_sem_token_responde_401(self) -> None:
        for metodo, caminho in (
            ("get", "/injects"),
            ("get", "/timeline"),
            ("post", "/exercise/start"),
            ("post", "/injects/A01/fire"),
        ):
            with self.subTest(rota=caminho):
                resposta = getattr(self.cliente, metodo)(caminho)
                self.assertEqual(resposta.status_code, 401)
                self.assertIn("www-authenticate", {k.lower() for k in resposta.headers})

    def test_credencial_errada_nao_abre_sessao(self) -> None:
        self.assertEqual(
            self.cliente.post("/session", json={"credencial": "quase"}).status_code, 401
        )

    def test_as_rotas_da_sala_respondem_SEM_token(self) -> None:
        """A metade que impede a de cima de ser 'bloqueia tudo e passa no teste'."""
        for caminho in ("/wallboard/state", "/plateia/state"):
            with self.subTest(rota=caminho):
                self.assertEqual(self.cliente.get(caminho).status_code, 200)

    def test_as_tres_telas_passam_pelo_middleware_SEM_token(self) -> None:
        """As paginas sao publicas — e o que se afirma aqui e o MIDDLEWARE.

        `200` nao serve como asserção nesta suite: as telas sao artefato de
        build, e `dist/` nao existe numa arvore recem-clonada nem no worktree da
        auditoria. Exigir 200 aqui faria a suite depender do `npm`, e a saida
        usual — pular quando o bundle falta — e pulo silencioso lido como verde,
        que e o que a P2-19 atacou.

        Entao o que se mede e o que este teste existe para medir: sem token, a
        resposta NAO e 401. Que a tela existe de verdade e prova de outro nivel —
        `tests/test_telas.py` com o diretorio apontado, e o passo de build do CI.
        """
        for caminho in ("/sala", "/plateia", "/console"):
            with self.subTest(rota=caminho):
                self.assertNotEqual(self.cliente.get(caminho).status_code, 401)

    def test_rota_nao_declarada_publica_exige_token(self) -> None:
        """Falha fechada: o desconhecido nao e publico.

        Uma rota nova nasce protegida porque a lista e de ISENTOS, e nao de
        protegidos — o mesmo argumento do `papeis: []` da Fase 3.
        """
        self.assertEqual(self.cliente.get("/rota-que-nao-existe").status_code, 401)

    def test_a_documentacao_interativa_esta_desligada(self) -> None:
        for caminho in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(rota=caminho):
                self.assertIn(self.cliente.get(caminho).status_code, (401, 404))


class SuperficiePublica(unittest.TestCase):
    def test_rota_publica_com_parametro_e_RECUSADA(self) -> None:
        """Casar por padrao faria uma rota aberta cobrir o que ninguem declarou."""
        with self.assertRaises(SuperficieError):
            Superficie({"rotas": [{"path": "/w/{id}", "publica": True}]})

    def test_a_lista_de_publicas_e_a_declarada(self) -> None:
        publicas = Superficie.carregar().publicas
        self.assertEqual(
            publicas,
            {"/session", "/wallboard/state", "/plateia/state", "/ws/wallboard",
             "/ws/plateia", "/sala", "/plateia", "/console"},
        )


class Credencial(unittest.TestCase):
    def test_credencial_ausente_ou_curta_RECUSA_o_boot(self) -> None:
        for ambiente in ({}, {modulo_da_api.VARIAVEL_DA_CREDENCIAL: "curta"}):
            with self.subTest(ambiente=ambiente):
                with self.assertRaises(modulo_da_api.ConfiguracaoError):
                    modulo_da_api.credencial_do_console(ambiente)

    def test_credencial_longa_passa(self) -> None:
        self.assertEqual(
            modulo_da_api.credencial_do_console(
                {modulo_da_api.VARIAVEL_DA_CREDENCIAL: CREDENCIAL}
            ),
            CREDENCIAL,
        )

    def test_o_env_example_traz_o_placeholder_VAZIO(self) -> None:
        """Mesma assimetria do `AURORA_JWT_SECRET` da Fase 3.

        Credencial copiada de um arquivo versionado FUNCIONA, e o console dispara
        inject. Vazia, "copiei o exemplo" e "nao configurei" viram o mesmo caso, e
        a recusa alta cobre os dois.
        """
        linhas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
        alvo = [
            linha for linha in linhas
            if linha.startswith(f"{modulo_da_api.VARIAVEL_DA_CREDENCIAL}=")
        ]
        self.assertEqual(alvo, [f"{modulo_da_api.VARIAVEL_DA_CREDENCIAL}="])
        with self.assertRaises(modulo_da_api.ConfiguracaoError):
            modulo_da_api.credencial_do_console({modulo_da_api.VARIAVEL_DA_CREDENCIAL: ""})


class RollbackPelaRota(BaseDaApi):
    """A ponta do DEMO: rebobinar pelo console e ver a timeline anotada."""

    def test_o_rollback_devolve_a_projecao_e_anota_a_timeline(self) -> None:
        """O corte vai para ANTES do disparo, e a distincao custou uma execucao.

        A primeira versao rebobinava para o proprio `inject_fired` e afirmava que
        o wallboard mudava. Nao muda, e esta certo: o corte e NAQUELE evento,
        entao o efeito dele SOBREVIVE — `09` §3 desenha a epoch 1 comecando
        depois da ancora, e o registro da Fase 2 diz a mesma coisa em prosa
        (*"A01 nao volta: o disparo dele sobreviveu ao rollback"*).

        Para a sala ver a projecao voltar, o corte tem de ser anterior ao
        disparo. O teste estava errado; o engine, nao.
        """
        inicio = self.cliente.post("/exercise/start", headers=self.cabecalho)
        antes_do_disparo = self.cliente.get("/wallboard/state").content

        self.cliente.post("/injects/A01/fire", headers=self.cabecalho)
        depois_do_disparo = self.cliente.get("/wallboard/state").content
        self.assertNotEqual(antes_do_disparo, depois_do_disparo)

        resposta = self.cliente.post(
            "/exercise/rollback",
            json={"to_event_id": inicio.json()["event_id"], "reason": "facilitation"},
            headers=self.cabecalho,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["simulation_epoch"], 1)

        depois_do_rollback = self.cliente.get("/wallboard/state").content
        self.assertNotEqual(depois_do_disparo, depois_do_rollback)
        self.assertEqual(
            depois_do_rollback, antes_do_disparo,
            "a projecao restaurada nao e BYTE A BYTE a de antes do disparo",
        )

        timeline = json.loads(
            self.cliente.get("/timeline", headers=self.cabecalho).content
        )["entradas"]
        anotadas = [e for e in timeline if "rollback" in e]
        self.assertEqual(len(anotadas), 1)
        self.assertEqual(anotadas[0]["rollback"]["motivo"], "facilitation")


# A pagina crua de `/sala` foi substituida pelo bundle na peca 6 — a P4-3
# fechada —, e o teste que a varria mudou de casa junto com ela:
# `tests/test_telas.py` varre a FONTE das tres telas, que e o que existe sem
# `npm`, e o passo de build do CI varre o artefato construido.


if __name__ == "__main__":
    unittest.main()
