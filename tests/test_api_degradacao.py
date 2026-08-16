"""Degradacao por flag — itens 1 e 2 da DoD da Fase 3, e a D4 executando.

O QUE ESTA SUITE PROVA, e o que ela recusa provar
--------------------------------------------------
- **Item 1:** `enrollment_offline` ligada faz `POST /matricula` responder **503**.
- **Item 2:** `grades_readonly` ligada bloqueia `POST` de nota **com mensagem de
  negocio** — 409, e o texto diz ao professor o que fazer.
- **O terceiro endpoint** que `07` exige: `GET /turmas/{turma_id}/diario`, com a
  unica flag `number` da fase.
- **A degradacao e observavel sem se explicar.** Varredura sobre a resposta
  inteira — corpo e cabecalhos —, na forma que `06` T6 fixa para isolamento de
  papel: nenhum nome de flag, nenhum vocabulario de mecanismo.
- **Sem flag ligada, nada muda.** E a metade que impede a primeira de virar
  superstição: uma API que recusasse sempre passaria em metade destes testes.

SEM DUPLO, PELA TERCEIRA VEZ
-----------------------------
O estado vem de `InMemoryEventStore` + `InMemoryProjectionCache` + o fold de
verdade, atraves de `current` — a porta da peca 3, sem atalho. As flags vem de
`domains/academus/flags.yaml`, lidas pelo `AdapterFlags` do loader, e os nomes
vem das CONSTANTES GERADAS: literal de flag em teste tambem e literal, e o hook
recusou a primeira versao deste arquivo por isso, com razao.

A UNICA COSTURA E O TEMPO, e ela ja existia no projeto: `Degradador.dormir` e
parametro pelo mesmo motivo que `now` e parametro no relogio e no token. Esperar
2,5 s de verdade para afirmar que a latencia declarada foi aplicada seria pagar
o tempo do exercicio dentro da suite.
"""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from contracts.generated.events import EXERCISE_STARTED, INJECT_FIRED
from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.degradacao import Degradador, LeituraDeEstado
from domains.academus.api.surface import carregar
from domains.academus.generated.flags import (
    ACADEMUS_ENROLLMENT_OFFLINE,
    ACADEMUS_GRADES_READONLY,
    ACADEMUS_LMS_DEGRADED,
    ACADEMUS_LMS_SESSION_DROP_RATE,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.loader.pack_loader import AdapterFlags
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.state.cache import InMemoryProjectionCache
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    Declarations,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAGS_YAML = REPO_ROOT / "domains" / "academus" / "flags.yaml"

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

#: O professor de `T-2001` em `registros.py`. A regra `titular` compara com isto.
TITULAR = "P-3001"

#: PALAVRAS QUE NENHUMA RESPOSTA DEGRADADA PODE CONTER. A mesma familia da lista
#: da checagem, aqui aplicada ao que sai pelo fio em vez de ao que esta
#: declarado. O prefixo do namespace de flag entra: basta ele para a sala
#: perceber que esta lendo o mecanismo.
MECANISMO = ("flag", "simulac", "exercicio", "inject", "aurora", "range")


def _declaracoes() -> Declarations:
    """As flags do adapter, lidas do arquivo. Nao ha lista repetida aqui."""
    flags = AdapterFlags.from_document(
        yaml.safe_load(FLAGS_YAML.read_text(encoding="utf-8")),
        source=str(FLAGS_YAML),
    )
    return Declarations(
        pack_id="pack-de-teste",
        schema_version=2,
        content_hash="0" * 64,
        canonicalization="v1",
        flag_defaults=flags.defaults,
        inject_effects={
            "MATRICULA_FORA": {ACADEMUS_ENROLLMENT_OFFLINE: True},
            "NOTAS_CONGELADAS": {ACADEMUS_GRADES_READONLY: True},
            "AVA_LENTO": {ACADEMUS_LMS_DEGRADED: True},
            "SESSOES_CAINDO": {ACADEMUS_LMS_SESSION_DROP_RATE: 0.5},
            "TODAS_AS_SESSOES": {ACADEMUS_LMS_SESSION_DROP_RATE: 1.0},
        },
        option_effects={},
    )


def _relogio() -> ExerciseClock:
    parede = iter(range(1_000_000, 1_100_000))
    return ExerciseClock(datetime(2026, 8, 17, 9, 0, 0), now=lambda: float(next(parede)))


class Cenario:
    """O aparato: store real, cache real, fold real, e o relogio de sempre."""

    def __init__(self) -> None:
        self.declaracoes = _declaracoes()
        self.store = InMemoryEventStore(_relogio())
        self.store.append(
            EventDraft(
                event_type=EXERCISE_STARTED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste"),
                payload={
                    PACK_ID: "pack-de-teste",
                    PACK_SCHEMA_VERSION: 2,
                    PACK_CONTENT_HASH: "0" * 64,
                    PACK_CANONICALIZATION: "v1",
                },
            )
        )
        self.dormidas: list[float] = []
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)

        async def dormir(segundos: float) -> None:
            self.dormidas.append(segundos)

        self.degradador = Degradador(
            leitura=LeituraDeEstado(
                store=self.store,
                declarations=self.declaracoes,
                cache=InMemoryProjectionCache(),
            ),
            dormir=dormir,
        )
        self.cliente = TestClient(montar(self.autenticacao, self.degradador))

    def dispara(self, inject_id: str) -> None:
        """Um `inject_fired` de verdade. O efeito vem do fold, nao de um `set`."""
        self.store.append(
            EventDraft(
                event_type=INJECT_FIRED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste", inject_id=inject_id),
            )
        )

    def cabecalho(self, papel: str, sub: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, papel)}"}


class ItensDaDoD(unittest.TestCase):
    def setUp(self) -> None:
        self.c = Cenario()
        self.secretaria = self.c.cabecalho("secretaria", "S-1")
        self.professor = self.c.cabecalho("professor", TITULAR)

    def _matricula(self):
        return self.c.cliente.post(
            "/matricula",
            json={"aluno_id": "A-1001", "turma_id": "T-2001"},
            headers=self.secretaria,
        )

    def _nota(self):
        return self.c.cliente.post(
            "/turmas/T-2001/notas",
            json={"aluno_id": "A-1001", "valor": 9.0},
            headers=self.professor,
        )

    def test_item_1_matricula_responde_503_com_a_flag_ligada(self):
        self.assertEqual(self._matricula().status_code, 201)

        self.c.dispara("MATRICULA_FORA")

        self.assertEqual(self._matricula().status_code, 503)

    def test_item_2_nota_bloqueada_COM_MENSAGEM_DE_NEGOCIO(self):
        """409 e nao 403 seco: o item pede que a recusa EXPLIQUE.

        Quem recebe e um professor no meio de um lancamento. "Acesso negado" o
        manda abrir chamado; a mensagem daqui o manda falar com a coordenacao.
        """
        self.assertEqual(self._nota().status_code, 201)

        self.c.dispara("NOTAS_CONGELADAS")

        recusada = self._nota()
        self.assertEqual(recusada.status_code, 409)
        self.assertIn("coordenacao", recusada.json()["detail"].lower())

    def test_a_leitura_de_nota_segue_disponivel_com_a_flag_ligada(self):
        """O `effect_ui` da flag diz "leitura e historico seguem disponiveis".

        Degradacao que derruba o servico inteiro nao e a declarada, e a diferenca
        e o que faz o exercicio ser sobre integridade e nao sobre queda.
        """
        self.c.dispara("NOTAS_CONGELADAS")
        diario = self.c.cliente.get("/turmas/T-2001/diario", headers=self.professor)
        self.assertEqual(diario.status_code, 200)

    def test_o_terceiro_endpoint_fica_lento_e_depois_derruba(self):
        """A ordem declarada e a ordem vivida: lento primeiro, queda depois."""
        self.c.dispara("AVA_LENTO")
        lento = self.c.cliente.get("/turmas/T-2001/diario", headers=self.professor)
        self.assertEqual(lento.status_code, 200)
        self.assertEqual(self.c.dormidas, [2.5])

        self.c.dispara("TODAS_AS_SESSOES")
        derrubada = self.c.cliente.get("/turmas/T-2001/diario", headers=self.professor)
        self.assertEqual(derrubada.status_code, 503)
        self.assertEqual(self.c.dormidas, [2.5, 2.5])


class SemFlagNadaMuda(unittest.TestCase):
    """A metade que impede a outra de virar superstição."""

    def setUp(self) -> None:
        self.c = Cenario()
        self.professor = self.c.cabecalho("professor", TITULAR)

    def test_nenhuma_rota_degrada_com_o_fluxo_no_estado_inicial(self):
        secretaria = self.c.cabecalho("secretaria", "S-1")
        respostas = [
            self.c.cliente.post(
                "/matricula",
                json={"aluno_id": "A-1001", "turma_id": "T-2001"},
                headers=secretaria,
            ),
            self.c.cliente.post(
                "/turmas/T-2001/notas",
                json={"aluno_id": "A-1001", "valor": 9.0},
                headers=self.professor,
            ),
            self.c.cliente.get("/turmas/T-2001/diario", headers=self.professor),
        ]
        self.assertEqual([r.status_code for r in respostas], [201, 201, 200])
        self.assertEqual(self.c.dormidas, [])

    def test_a_API_SEM_DEGRADADOR_nao_degrada_nem_explode(self):
        """`montar` sem degradador e uma API que so autentica, e isso e explicito.

        Esquecer o wiring nao pode produzir excecao no meio de um exercicio, e
        tambem nao pode produzir degradacao silenciosa.
        """
        cliente = TestClient(montar(self.c.autenticacao, None))
        self.c.dispara("MATRICULA_FORA")
        resposta = cliente.post(
            "/matricula",
            json={"aluno_id": "A-1001", "turma_id": "T-2001"},
            headers=self.c.cabecalho("secretaria", "S-1"),
        )
        self.assertEqual(resposta.status_code, 201)


class Proporcional(unittest.TestCase):
    """A unica flag `number` da fase, e o unico efeito que nao e liga-desliga."""

    def setUp(self) -> None:
        self.c = Cenario()
        self.professor = self.c.cabecalho("professor", TITULAR)

    def _tenta(self, vezes: int) -> list[int]:
        return [
            self.c.cliente.get("/turmas/T-2001/diario", headers=self.professor).status_code
            for _ in range(vezes)
        ]

    def test_taxa_zero_nunca_derruba(self):
        """O default da flag e `0`. Uma condicao `ligada` aqui derrubaria SEMPRE."""
        self.assertEqual(set(self._tenta(6)), {200})

    def test_taxa_meia_derruba_exatamente_metade_e_sem_sorteio(self):
        """Cota deterministica: `floor(n * taxa)` recusas, distribuidas por igual.

        Um sorteio por request seria o primeiro consumidor do `RANDOM_SEED`
        dependente de ORDEM — e `range-core/determinism.py` foi escrito com
        escopo justamente para que ordem deixasse de ser variavel. Aqui o numero
        e exato, e o facilitador consegue prever o efeito.
        """
        self.c.dispara("SESSOES_CAINDO")
        codigos = self._tenta(6)
        self.assertEqual(codigos.count(503), 3)
        # A SEQUENCIA EXATA, e ela e observada e nao adivinhada: a primeira
        # versao deste teste afirmava `[503, 200, ...]` e ficou vermelha. O
        # acumulador comeca em zero, entao a taxa de 0,5 so vence na SEGUNDA
        # requisicao — o efeito entra rampeando, que e mais parecido com um
        # servico degradando do que com um interruptor.
        self.assertEqual(codigos, [200, 503, 200, 503, 200, 503])

    def test_taxa_um_derruba_sempre(self):
        self.c.dispara("TODAS_AS_SESSOES")
        self.assertEqual(set(self._tenta(4)), {503})


class NaoSeExplica(unittest.TestCase):
    """A degradacao e observavel SEM ser explicada. Varredura sobre a resposta."""

    def setUp(self) -> None:
        self.c = Cenario()

    def _varre(self, resposta) -> None:
        texto = (resposta.text + " " + str(dict(resposta.headers))).lower()
        for palavra in MECANISMO:
            self.assertNotIn(
                palavra,
                texto,
                f"a resposta degradada contem {palavra!r} — a sala leria o "
                "mecanismo em vez de ver o sistema cair",
            )

    def test_a_recusa_de_matricula_nao_se_explica(self):
        self.c.dispara("MATRICULA_FORA")
        self._varre(
            self.c.cliente.post(
                "/matricula",
                json={"aluno_id": "A-1001", "turma_id": "T-2001"},
                headers=self.c.cabecalho("secretaria", "S-1"),
            )
        )

    def test_a_recusa_de_nota_nao_se_explica(self):
        self.c.dispara("NOTAS_CONGELADAS")
        self._varre(
            self.c.cliente.post(
                "/turmas/T-2001/notas",
                json={"aluno_id": "A-1001", "valor": 9.0},
                headers=self.c.cabecalho("professor", TITULAR),
            )
        )

    def test_a_queda_de_sessao_nao_se_explica(self):
        self.c.dispara("TODAS_AS_SESSOES")
        self._varre(
            self.c.cliente.get(
                "/turmas/T-2001/diario", headers=self.c.cabecalho("professor", TITULAR)
            )
        )

    def test_as_rotas_de_documentacao_nao_existem(self):
        """Achado desta peca, e o defeito era da peca 4.

        `/openapi.json` respondia **200 sem token**, com a API inteira descrita.
        A dependencia global nao as cobria: elas entram por `add_route`, que e
        Starlette puro. Num exercicio sobre assimetria, a lista de rotas conta a
        quem ainda nao entrou o que existe para ser encontrado.
        """
        for caminho in ("/openapi.json", "/docs", "/redoc"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.c.cliente.get(caminho).status_code, 404)


if __name__ == "__main__":
    unittest.main()
