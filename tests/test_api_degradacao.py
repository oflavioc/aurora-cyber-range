"""Degradacao por flag — itens 1 e 2 da DoD da Fase 3, e a D4 executando.

O QUE ESTA SUITE PROVA, e o que ela recusa provar
--------------------------------------------------
- **Item 1:** `enrollment_offline` ligada faz `POST /enrollment` responder **503**.
- **Item 2:** `grades_readonly` ligada bloqueia `POST` de nota **com mensagem de
  negocio** — 409, e o texto diz ao professor o que fazer.
- **O terceiro endpoint** que `07` exige: `GET /classes/{class_id}/gradebook`, com a
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

O QUE A PECA 5 DA FASE 4 MUDOU AQUI
-------------------------------------
**Banco.** O business state saiu dos dicionarios de modulo (P3-5), entao este
arquivo PULA sem `AURORA_TEST_DATABASE_URL` — ver `tests/_academus_banco.py`.

**Caminhos em ingles** (P4-1), e os campos do corpo junto.

**`proporcional` deixou de ter memoria** (P3-10). A classe `Proporcional` abaixo
mudou de objeto: ela afirmava `floor(n*taxa)` recusas em `n` REQUISICOES, com a
sequencia exata `[200, 503, 200, 503, ...]` de um acumulador rampeando. Agora a
fracao e sobre o conjunto de **sujeitos**, e a mesma sessao recebe sempre a
mesma resposta — as tres propriedades da D9 estao em
`tests/test_queda_de_sessao.py`, onde ha sujeitos suficientes para medi-las.
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
from domains.academus.api.degradacao import Degradador, LeituraDeEstado, cai
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

from _academus_app import emissor_de_teste
from _academus_banco import exige_banco, repositorio_limpo

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAGS_YAML = REPO_ROOT / "domains" / "academus" / "flags.yaml"

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

#: O token de dominio passou a carregar `persona` — B1 da setima auditoria.
#: Nada NESTE arquivo depende dela: degradacao e decidida por FLAG, e nao por
#: quem pede. A constante existe para o argumento obrigatorio ser explicito.
PERSONA = "ti"

#: O `RANDOM_SEED` da suite, FIXO E PASSADO, e nao lido do ambiente. `00` §8 o
#: exige fixo; aqui ele e argumento porque um teste que dependesse da variavel de
#: ambiente mudaria de resultado com o `.env` de quem roda — que e o oposto do
#: que a P3-10 acabou de comprar.
SEED = 20260816

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
            seed=SEED,
            dormir=dormir,
        )
        self.repositorio = repositorio_limpo()
        self.cliente = TestClient(
            montar(
                self.autenticacao,
                self.repositorio,
                self.degradador,
                emissor_de_teste(),
            )
        )

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
        return {
            "Authorization": (
                f"Bearer {self.autenticacao.emitir_token(sub, papel, PERSONA)}"
            )
        }


@exige_banco
class ItensDaDoD(unittest.TestCase):
    def setUp(self) -> None:
        self.c = Cenario()
        self.secretaria = self.c.cabecalho("secretaria", "S-1")
        self.professor = self.c.cabecalho("professor", TITULAR)

    def _matricula(self):
        return self.c.cliente.post(
            "/enrollment",
            json={"student_id": "A-1001", "class_id": "T-2001"},
            headers=self.secretaria,
        )

    def _nota(self):
        return self.c.cliente.post(
            "/classes/T-2001/grades",
            json={"student_id": "A-1001", "value": 9.0},
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
        diario = self.c.cliente.get("/classes/T-2001/gradebook", headers=self.professor)
        self.assertEqual(diario.status_code, 200)

    def test_o_terceiro_endpoint_fica_lento_e_depois_derruba(self):
        """A ordem declarada e a ordem vivida: lento primeiro, queda depois."""
        self.c.dispara("AVA_LENTO")
        lento = self.c.cliente.get("/classes/T-2001/gradebook", headers=self.professor)
        self.assertEqual(lento.status_code, 200)
        self.assertEqual(self.c.dormidas, [2.5])

        self.c.dispara("TODAS_AS_SESSOES")
        derrubada = self.c.cliente.get("/classes/T-2001/gradebook", headers=self.professor)
        self.assertEqual(derrubada.status_code, 503)
        self.assertEqual(self.c.dormidas, [2.5, 2.5])


@exige_banco
class SemFlagNadaMuda(unittest.TestCase):
    """A metade que impede a outra de virar superstição."""

    def setUp(self) -> None:
        self.c = Cenario()
        self.professor = self.c.cabecalho("professor", TITULAR)

    def test_nenhuma_rota_degrada_com_o_fluxo_no_estado_inicial(self):
        secretaria = self.c.cabecalho("secretaria", "S-1")
        respostas = [
            self.c.cliente.post(
                "/enrollment",
                json={"student_id": "A-1001", "class_id": "T-2001"},
                headers=secretaria,
            ),
            self.c.cliente.post(
                "/classes/T-2001/grades",
                json={"student_id": "A-1001", "value": 9.0},
                headers=self.professor,
            ),
            self.c.cliente.get("/classes/T-2001/gradebook", headers=self.professor),
        ]
        self.assertEqual([r.status_code for r in respostas], [201, 201, 200])
        self.assertEqual(self.c.dormidas, [])

    def test_a_API_SEM_DEGRADADOR_nao_degrada_nem_explode(self):
        """`montar` sem degradador e uma API que so autentica, e isso e explicito.

        Esquecer o wiring nao pode produzir excecao no meio de um exercicio, e
        tambem nao pode produzir degradacao silenciosa.
        """
        cliente = TestClient(
            montar(self.c.autenticacao, self.c.repositorio, None, emissor_de_teste())
        )
        self.c.dispara("MATRICULA_FORA")
        resposta = cliente.post(
            "/enrollment",
            json={"student_id": "A-1001", "class_id": "T-2001"},
            headers=self.c.cabecalho("secretaria", "S-1"),
        )
        self.assertEqual(resposta.status_code, 201)


@exige_banco
class Proporcional(unittest.TestCase):
    """A unica flag `number` da fase, e o unico efeito que nao e liga-desliga."""

    def setUp(self) -> None:
        self.c = Cenario()
        self.professor = self.c.cabecalho("professor", TITULAR)

    ROTA = "/classes/{class_id}/gradebook"

    def _tenta(self, vezes: int, sub: str = TITULAR, papel: str = "professor") -> list[int]:
        cabecalho = self.c.cabecalho(papel, sub)
        return [
            self.c.cliente.get("/classes/T-2001/gradebook", headers=cabecalho).status_code
            for _ in range(vezes)
        ]

    def _partidos(self, taxa: float) -> tuple[str, str]:
        """Um sujeito que cai e um que nao cai, NESTA taxa. Calculados, nao fixados.

        O par vem da propria funcao pura, e isso e deliberado: o que este arquivo
        prova e o **wiring** — que a rota consulta a flag certa, com o caminho
        certo e com o `sub` do token —, e nao a distribuicao, que
        `test_queda_de_sessao.py` mede sobre sujeitos suficientes.

        Fixar dois identificadores literais aqui seria escrever o digest de
        SHA-256 no teste: verde enquanto ninguem mexe, e vermelho por um motivo
        ilegivel no dia em que a derivacao mudar de forma legitimamente.
        """
        cai_, nao_cai = None, None
        for n in range(200):
            sub = f"S-{n}"
            if cai(SEED, self.ROTA, ACADEMUS_LMS_SESSION_DROP_RATE, sub, taxa):
                cai_ = cai_ or sub
            else:
                nao_cai = nao_cai or sub
            if cai_ and nao_cai:
                return cai_, nao_cai
        raise AssertionError(f"taxa {taxa} nao partiu 200 sujeitos — a funcao nao discrimina")

    def test_taxa_zero_nunca_derruba(self):
        """O default da flag e `0`. Uma condicao `ligada` aqui derrubaria SEMPRE."""
        self.assertEqual(set(self._tenta(6)), {200})

    def test_a_MESMA_sessao_recebe_sempre_a_mesma_resposta(self):
        """A P3-10 em uma assercao: nao ha memoria, entao nao ha intermitencia.

        Era isto que a cota acumulada NAO dava. Com ela, `taxa 0,5` produzia
        `[200, 503, 200, 503, ...]` para o mesmo participante — a sessao dele
        caia, voltava, caia de novo. `flags.yaml` fala em *"fracao de sessoes
        derrubadas"*, e derrubar a mesma sessao alternadamente nao e isso: e um
        servico piscando, que na sala se le como instabilidade e nao como queda.

        Seis requisicoes, uma resposta so. O valor dela nao esta fixado aqui de
        proposito — qual sujeito cai e o objeto dos dois testes seguintes.
        """
        self.c.dispara("SESSOES_CAINDO")
        self.assertEqual(len(set(self._tenta(6))), 1)

    def test_quem_cai_e_decidido_pelo_SUJEITO_do_token(self):
        """O par que discrimina, na mesma rota e com a mesma taxa.

        Um degradador que ignorasse o sujeito daria a mesma resposta aos dois, e
        e por isso que sao dois: a assercao de que alguem cai passaria sozinha
        com "derruba sempre", e a de que alguem nao cai passaria sozinha com
        "nunca derruba".
        """
        self.c.dispara("SESSOES_CAINDO")
        derrubado, poupado = self._partidos(0.5)

        self.assertEqual(
            self._tenta(1, sub=derrubado, papel="secretaria"), [503]
        )
        self.assertEqual(
            self._tenta(1, sub=poupado, papel="secretaria"), [200]
        )

    def test_taxa_um_derruba_sempre(self):
        self.c.dispara("TODAS_AS_SESSOES")
        self.assertEqual(set(self._tenta(4)), {503})
        # E TAMBEM QUEM ERA POUPADO EM 0,5: a monotonicidade chegando ate a rota,
        # e nao so ate a funcao. Sem esta linha, um degradador que caisse por
        # sujeito mas trocasse o conjunto ao subir a taxa passaria.
        _, poupado_em_meio = self._partidos(0.5)
        self.assertEqual(self._tenta(1, sub=poupado_em_meio, papel="secretaria"), [503])


@exige_banco
class AutorizaAntesDeDegradar(unittest.TestCase):
    """M2 da auditoria da Fase 3 — a ordem que era argumento e nao era teste.

    `app.py` declara `dependencies=[Depends(autoriza), Depends(degrada)]` e o
    comentario ao lado diz por que: *"degradar antes de autenticar entregaria o
    estado da simulacao a quem nem token tem"*. A propriedade valia, e repousava
    **inteiramente** na ordem de resolucao de dependencias do FastAPI — que
    nenhum teste e nenhum verificador fixava.

    Era a classe que a §7.3 do registro desta fase nomeia: verificacao que
    parece existir. O argumento estava escrito; a prova, nao.

    UM 503 SEM TOKEN E VAZAMENTO DE ESTADO, e nao apenas ordem trocada: ele
    responde *"a flag esta ligada"* para qualquer um na rede, e `00` §3 chama
    assimetria de informacao de desenho.
    """

    def setUp(self) -> None:
        self.c = Cenario()
        self.c.dispara("MATRICULA_FORA")
        self.c.dispara("NOTAS_CONGELADAS")
        self.c.dispara("TODAS_AS_SESSOES")

    def _sem_token(self, metodo: str, caminho: str):
        chamada = getattr(self.c.cliente, metodo)
        if metodo == "post":
            return chamada(caminho, json={"student_id": "A-1001", "class_id": "T-2001", "value": 9.0})
        return chamada(caminho)

    def test_sem_token_as_tres_rotas_degradadas_respondem_401_e_nao_503(self):
        """As TRES, com as flags ligadas. Uma so nao discriminaria a ordem."""
        rotas = [
            ("post", "/enrollment"),
            ("post", "/classes/T-2001/grades"),
            ("get", "/classes/T-2001/gradebook"),
        ]
        for metodo, caminho in rotas:
            with self.subTest(rota=f"{metodo.upper()} {caminho}"):
                resposta = self._sem_token(metodo, caminho)
                self.assertEqual(
                    resposta.status_code,
                    401,
                    "degradou antes de autenticar: a resposta conta o estado da "
                    "simulacao a quem nao tem token",
                )
                self.assertEqual(resposta.headers.get("WWW-Authenticate"), "Bearer")

    def test_sem_token_nao_paga_a_latencia_declarada(self):
        """A latencia tambem e observavel, e tambem nao pode chegar sem token.

        Sem esta assercao, um `degrada` que rodasse antes e aplicasse SO a
        latencia — recusando depois com 401 — passaria no teste acima e ainda
        entregaria pela cronometragem que a flag do AVA esta ligada.

        A FLAG PRECISA ESTAR LIGADA, E A PRIMEIRA VERSAO DESTE TESTE NAO LIGAVA.
        O `setUp` da classe dispara `MATRICULA_FORA`, `NOTAS_CONGELADAS` e
        `TODAS_AS_SESSOES`; o unico inject que liga `academus.lms_degraded` e
        `AVA_LENTO`, e ele nao estava aqui. Com a flag em `false`, a entrada de
        `latencia` do diario nao dispara em ordem NENHUMA — `dormidas` era `[]`
        com `autoriza` antes ou depois, com token ou sem token, e a assercao nao
        discriminava nada. Foi o H1 da auditoria de `5b219a7`.

        POR ISSO O PAR, e nao a metade: a MESMA rota, com a MESMA flag ligada,
        paga 2,5 s com token e zero sem token. A primeira metade e o que torna a
        segunda capaz de ficar vermelha.
        """
        self.c.dispara("AVA_LENTO")

        com_token = self.c.cliente.get(
            "/classes/T-2001/gradebook", headers=self.c.cabecalho("professor", TITULAR)
        )
        self.assertEqual(com_token.status_code, 503)
        self.assertEqual(
            self.c.dormidas,
            [2.5],
            "a latencia declarada nao chegou nem COM token: o teste voltou a nao "
            "discriminar ordem nenhuma",
        )

        self.c.dormidas.clear()
        resposta = self._sem_token("get", "/classes/T-2001/gradebook")
        # A ESPERA ANTES DO STATUS, de proposito: e a assercao que so este teste
        # faz. Com a ordem invertida o status tambem sai errado, e o teste acima
        # ja o cobre nas tres rotas — deixar o status primeiro faria o canal de
        # temporizacao nunca ser a linha que fica vermelha.
        self.assertEqual(
            self.c.dormidas,
            [],
            "degradou antes de autenticar: a espera entrega pela cronometragem "
            "que a flag do AVA esta ligada, a quem nao tem token",
        )
        self.assertEqual(resposta.status_code, 401)

    def test_com_token_as_mesmas_rotas_degradam(self):
        """O par que discrimina: uma API que so devolvesse 401 passaria acima."""
        secretaria = self.c.cabecalho("secretaria", "S-1")
        professor = self.c.cabecalho("professor", TITULAR)

        self.assertEqual(
            self.c.cliente.post(
                "/enrollment",
                json={"student_id": "A-1001", "class_id": "T-2001"},
                headers=secretaria,
            ).status_code,
            503,
        )
        self.assertEqual(
            self.c.cliente.post(
                "/classes/T-2001/grades",
                json={"student_id": "A-1001", "value": 9.0},
                headers=professor,
            ).status_code,
            409,
        )
        self.assertEqual(
            self.c.cliente.get("/classes/T-2001/gradebook", headers=professor).status_code,
            503,
        )

    def test_a_ordem_declarada_na_aplicacao_e_autoriza_depois_degrada(self):
        """E a metade estrutural, sobre o objeto que o FastAPI vai resolver.

        O teste de comportamento acima prova a propriedade hoje; este nomeia a
        causa, para que uma inversao apareca como "a ordem mudou" em vez de como
        tres 503 inexplicados.
        """
        from domains.academus.api.app import app
        from domains.academus.api.auth import autoriza
        from domains.academus.api.degradacao import degrada

        chamadas = [d.dependency for d in app.router.dependencies]
        self.assertEqual(chamadas, [autoriza, degrada])


@exige_banco
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
                "/enrollment",
                json={"student_id": "A-1001", "class_id": "T-2001"},
                headers=self.c.cabecalho("secretaria", "S-1"),
            )
        )

    def test_a_recusa_de_nota_nao_se_explica(self):
        self.c.dispara("NOTAS_CONGELADAS")
        self._varre(
            self.c.cliente.post(
                "/classes/T-2001/grades",
                json={"student_id": "A-1001", "value": 9.0},
                headers=self.c.cabecalho("professor", TITULAR),
            )
        )

    def test_a_queda_de_sessao_nao_se_explica(self):
        self.c.dispara("TODAS_AS_SESSOES")
        self._varre(
            self.c.cliente.get(
                "/classes/T-2001/gradebook", headers=self.c.cabecalho("professor", TITULAR)
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
