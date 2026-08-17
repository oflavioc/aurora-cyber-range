"""As projecoes de sala — e a igualdade byte a byte, MEDIDA.

O QUE ESTE ARQUIVO PROVA, NA ORDEM DE IMPORTANCIA
--------------------------------------------------
1. **O mesmo estado produz os mesmos bytes**, inclusive quando o estado chega
   por caminhos diferentes. E a propriedade central da peca: o frame do
   WebSocket e o snapshot HTTP tem de ser o mesmo payload, e a superficie
   declarada so prova que os dois EXISTEM em par — nenhum eixo declarativo prova
   que eles PRODUZEM o mesmo.
2. **O sinal do indice de saude**, com uma flag de default `true` e uma de
   default `false`. Se o sinal inverter, o indice MELHORA quando o defensor
   revoga acesso.
3. **Os paineis sao derivados**, com flag plantada num grupo que nao existe.
4. **A sala nao ve o que nao pode**, por varredura recursiva — `06` T6 e teste de
   payload, e nao de interface.

POR QUE A IGUALDADE PRECISA DE MAIS DE UMA CHAMADA IGUAL
---------------------------------------------------------
Chamar a mesma funcao duas vezes com o mesmo objeto prova pouco. Os tres
caminhos por onde a divergencia entra de verdade sao:

- **ordenacao de chave** — duas serializacoes do mesmo dicionario;
- **carimbo de geracao** — o mesmo estado montado em instantes diferentes;
- **tipo que muda no transporte** — o estado que passou pelo Redis contra o que
  saiu do fold. Foi o L1 da terceira auditoria da Fase 3: uma flag `number` que
  voltava `bool` da serializacao. Aquilo produziria dois payloads diferentes
  para o mesmo estado, e a sala e quem reconecta veriam coisas diferentes.

O terceiro so e observavel com Redis de verdade, e por isso ele pula sem o
servico — com o comando impresso, na forma que a P2-19 fixou.
"""

from __future__ import annotations

import ast
import json
import os
import unittest
from datetime import datetime
from pathlib import Path

from range_core.api import projecoes
from range_core.api.projecoes import (
    ATIVA,
    CATEGORIA,
    ENTRADAS,
    GRUPO,
    INTENSIDADE,
    ITENS,
    ROTULO,
    SAUDE_PLENA,
    TEXTO,
    indice_de_saude,
    paineis,
    plateia,
    serializa,
    timeline,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore
from range_core.state.cache import RedisProjectionCache
from range_core.state.simulation_state import SimulationState

REDIS_ENV = "AURORA_TEST_REDIS_URL"
_URL = os.environ.get(REDIS_ENV)

RAZAO = (
    f"{REDIS_ENV} nao definida. Este teste ESCREVE e APAGA a chave da projecao. "
    f"Para rodar:\n    docker compose up -d redis && {REDIS_ENV}="
    "redis://127.0.0.1:6379/1 python -m unittest discover -s tests"
)

#: Duas flags com o MESMO peso e defaults OPOSTOS. E o par que fixa o sinal: sem
#: a de default `true`, "ativa" poderia significar "verdadeira" e nada ficaria
#: vermelho. A forma e a do `academus.federated_session_active`.
LIGADA_POR_DEFAULT = "fixture.sessao_federada_ativa"
DESLIGADA_POR_DEFAULT = "fixture.matricula_fora_do_ar"

SPECS = {
    LIGADA_POR_DEFAULT: {
        "name": LIGADA_POR_DEFAULT,
        "type": "boolean",
        "default": True,
        "category": "identity",
        "severity_weight": 9,
        "wallboard_group": "Identidade",
        "effect_ui": "Sessoes federadas seguem validas",
    },
    DESLIGADA_POR_DEFAULT: {
        "name": DESLIGADA_POR_DEFAULT,
        "type": "boolean",
        "default": False,
        "category": "availability",
        "severity_weight": 9,
        "wallboard_group": "Matricula",
        "effect_ui": "Portal de matricula retorna pagina de manutencao",
    },
}

DEFAULTS = {nome: spec["default"] for nome, spec in SPECS.items()}


def _estado(**mudancas) -> SimulationState:
    flags = dict(DEFAULTS)
    flags.update(mudancas)
    return SimulationState(flags=flags, simulation_epoch=0)


class IgualdadeByteAByte(unittest.TestCase):
    """A propriedade central: o mesmo estado, os mesmos bytes."""

    def test_a_projecao_devolve_BYTES_e_nao_estrutura(self) -> None:
        """Devolver `dict` deixaria cada rota serializar — o mesmo fato, duas vezes.

        E a asserção que impede a divergencia de existir: com `bytes`, o snapshot
        e o frame nao tem por onde discordar; com `dict`, o `JSONResponse` do
        FastAPI e um `json.dumps` a mao ja discordam na ordenacao das chaves, e
        nenhum teste que compare ESTRUTURAS acusaria.
        """
        for rotulo, saida in (
            ("wallboard", projecoes.wallboard(_estado(), SPECS)),
            ("plateia", plateia([], {})),
            ("timeline", timeline([])),
        ):
            with self.subTest(projecao=rotulo):
                self.assertIsInstance(saida, bytes)

    def test_o_mesmo_estado_produz_os_MESMOS_bytes(self) -> None:
        estado = _estado(**{DESLIGADA_POR_DEFAULT: True})
        self.assertEqual(
            projecoes.wallboard(estado, SPECS),
            projecoes.wallboard(estado, SPECS),
        )

    def test_estados_DIFERENTES_produzem_bytes_diferentes(self) -> None:
        """A metade que impede a de cima de ser verdadeira por vacuidade.

        Uma projecao que devolvesse sempre `b'{}'` passaria em todas as
        asserções de igualdade deste arquivo.
        """
        self.assertNotEqual(
            projecoes.wallboard(_estado(), SPECS),
            projecoes.wallboard(_estado(**{DESLIGADA_POR_DEFAULT: True}), SPECS),
        )

    def test_a_ordem_de_insercao_das_chaves_NAO_muda_os_bytes(self) -> None:
        """`sort_keys` fecha o primeiro dos tres caminhos de divergencia."""
        self.assertEqual(
            serializa({"b": 1, "a": 2}),
            serializa({"a": 2, "b": 1}),
        )

    def test_nada_aqui_sabe_que_horas_sao(self) -> None:
        """O segundo caminho, fechado por ESTRUTURA e nao por observacao.

        Provar por comportamento exigiria montar duas vezes em instantes
        diferentes e concluir por ausencia de diferenca — a asserção de ausencia
        que passa tambem quando nada e observavel. Aqui a afirmacao e outra: o
        material com que o carimbo se escreve nao esta ao alcance do modulo.
        """
        fonte = Path(projecoes.__file__).read_text(encoding="utf-8")
        importados: set[str] = set()
        for node in ast.walk(ast.parse(fonte)):
            if isinstance(node, ast.Import):
                importados.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                importados.add((node.module or "").split(".")[0])

        for proibido in ("time", "datetime", "random", "secrets", "uuid"):
            with self.subTest(modulo=proibido):
                self.assertNotIn(
                    proibido, importados,
                    f"`projecoes` importa {proibido!r}: um carimbo de geracao faz "
                    "duas serializacoes do MESMO estado diferirem, e a sala e "
                    "quem reconecta passam a ver coisas diferentes.",
                )


@unittest.skipUnless(_URL, RAZAO)
class IgualdadeAtravesDoTransporte(unittest.TestCase):
    """O terceiro caminho: o estado que veio do Redis contra o que veio do fold.

    E o caminho REAL da Fase 4, e nao uma hipotese: o frame sai da projecao
    materializada e o snapshot pode sair de uma reconstrucao. Se o transporte
    mudar um tipo — `0.4` voltando `True`, que foi o L1 da terceira auditoria —,
    os dois payloads divergem para o mesmo estado.
    """

    CHAVE = "aurora:teste:projecoes"

    def setUp(self) -> None:
        import redis  # noqa: PLC0415 — dependencia da suite, nao do modulo

        self.cliente = redis.Redis.from_url(_URL)
        self.cliente.delete(self.CHAVE)
        self.addCleanup(self.cliente.delete, self.CHAVE)
        self.cache = RedisProjectionCache(self.cliente, chave=self.CHAVE)

    def test_o_estado_que_passou_pelo_redis_produz_os_MESMOS_bytes(self) -> None:
        from range_core.state.cache import CachedProjection  # noqa: PLC0415

        specs = dict(SPECS)
        specs["fixture.taxa_de_queda"] = {
            "name": "fixture.taxa_de_queda",
            "type": "number",
            "min": 0,
            "max": 1,
            "default": 0,
            "category": "performance",
            "severity_weight": 6,
            "wallboard_group": "AVA",
            "effect_ui": "Fracao de sessoes de prova derrubadas",
        }
        do_fold = SimulationState(
            flags={
                LIGADA_POR_DEFAULT: False,
                DESLIGADA_POR_DEFAULT: True,
                "fixture.taxa_de_queda": 0.4,
            },
            simulation_epoch=1,
        )

        clock = ExerciseClock(datetime(2026, 8, 16, 9, 0, 0))
        store = InMemoryEventStore(clock)
        # A serializacao do backend E o objeto do teste, entao ela e exercitada
        # diretamente. `refresh` folda, e foldar aqui produziria outro estado.
        self.cache._store(CachedProjection(state=do_fold, head=store.head()))  # noqa: SLF001
        do_redis = self.cache.read().state

        self.assertEqual(
            projecoes.wallboard(do_fold, specs),
            projecoes.wallboard(do_redis, specs),
            "o estado que atravessou o Redis produziu OUTROS bytes: a sala e quem "
            "reconecta veriam coisas diferentes para o mesmo estado",
        )


class IndiceDeSaude(unittest.TestCase):
    """D14 — a formula e inventada aqui, entao o sinal dela e fixado aqui."""

    def test_sem_nada_fora_do_default_a_saude_e_plena(self) -> None:
        self.assertEqual(indice_de_saude(_estado(), SPECS), SAUDE_PLENA)

    def test_as_DUAS_direcoes_de_default_pioram_o_indice_IGUALMENTE(self) -> None:
        """O caso que a D14 nomeia, e o unico que prova o sinal.

        `fixture.sessao_federada_ativa` tem default `true`: quando ela CAI, o
        defensor revogou acesso e a instituicao esta pior. Se "ativa" fosse lido
        como "verdadeira", esta flag contribuiria ao contrario — e o telao
        MELHORARIA no momento em que o acesso e revogado.

        Os dois pesos sao iguais de proposito: a asserção e sobre a direcao e a
        magnitude, e nao sobre qual flag pesa mais.
        """
        pleno = indice_de_saude(_estado(), SPECS)
        caiu = indice_de_saude(_estado(**{LIGADA_POR_DEFAULT: False}), SPECS)
        subiu = indice_de_saude(_estado(**{DESLIGADA_POR_DEFAULT: True}), SPECS)

        self.assertLess(caiu, pleno, "flag de default `true` que CAIU melhorou o indice")
        self.assertLess(subiu, pleno)
        self.assertEqual(
            caiu, subiu,
            "pesos iguais e defaults opostos deram contribuicoes diferentes: o "
            "sinal depende do valor, e nao da distancia ao default",
        )

    def test_peso_maior_baixa_mais(self) -> None:
        leve = dict(SPECS[DESLIGADA_POR_DEFAULT], severity_weight=2)
        pesado = dict(SPECS[DESLIGADA_POR_DEFAULT], severity_weight=10)
        base = {LIGADA_POR_DEFAULT: SPECS[LIGADA_POR_DEFAULT]}
        estado = _estado(**{DESLIGADA_POR_DEFAULT: True})

        self.assertGreater(
            indice_de_saude(estado, {**base, DESLIGADA_POR_DEFAULT: leve}),
            indice_de_saude(estado, {**base, DESLIGADA_POR_DEFAULT: pesado}),
        )

    def test_flag_number_contribui_em_PROPORCAO(self) -> None:
        specs = {
            "fixture.taxa": {
                "name": "fixture.taxa", "type": "number", "min": 0, "max": 1,
                "default": 0, "category": "performance", "severity_weight": 10,
                "wallboard_group": "AVA", "effect_ui": "Sessoes derrubadas",
            }
        }
        meio = indice_de_saude(
            SimulationState(flags={"fixture.taxa": 0.5}, simulation_epoch=0), specs
        )
        cheio = indice_de_saude(
            SimulationState(flags={"fixture.taxa": 1.0}, simulation_epoch=0), specs
        )
        self.assertEqual((meio, cheio), (50, 0))

    def test_o_caso_REAL_do_adapter(self) -> None:
        """A mesma propriedade contra `domains/academus/flags.yaml`, e nao fixture.

        A flag e nomeada pela CONSTANTE GERADA, e nao por literal: o hook recusou
        a primeira versao deste arquivo, e recusou com razao — nome de flag em
        codigo e o erro de digitacao que o invariante 2 existe para pegar.

        A asserção de que ela e a UNICA de default `true` no adapter e conferida
        aqui, e nao lembrada: se outra aparecer, este teste fica vermelho e o par
        de sinal ganha um segundo caso real em vez de envelhecer.
        """
        import yaml  # noqa: PLC0415

        from domains.academus.generated.flags import (  # noqa: PLC0415
            ACADEMUS_FEDERATED_SESSION_ACTIVE,
        )

        raiz = Path(__file__).resolve().parents[1]
        documento = yaml.safe_load(
            (raiz / "domains" / "academus" / "flags.yaml").read_text(encoding="utf-8")
        )
        specs = {f["name"]: f for f in documento["flags"]}
        ligadas = [n for n, s in specs.items() if s.get("default") is True]
        self.assertEqual(ligadas, [ACADEMUS_FEDERATED_SESSION_ACTIVE])

        defaults = {n: s["default"] for n, s in specs.items()}
        pleno = indice_de_saude(
            SimulationState(flags=defaults, simulation_epoch=0), specs
        )
        revogado = indice_de_saude(
            SimulationState(
                flags={**defaults, ACADEMUS_FEDERATED_SESSION_ACTIVE: False},
                simulation_epoch=0,
            ),
            specs,
        )
        self.assertEqual(pleno, SAUDE_PLENA)
        self.assertLess(
            revogado, pleno,
            "revogar a sessao federada MELHOROU o indice de saude institucional",
        )


class PaineisPorTaxonomia(unittest.TestCase):
    """`01` §5.3 — *"adicionar flag nao exige tocar no wallboard"*."""

    def test_flag_com_GRUPO_NOVO_cria_painel_novo(self) -> None:
        """A flag plantada cai num grupo que NAO existe, e e esse o ponto.

        Plantar num grupo existente provaria menos: o item apareceria por herdar
        um painel que ja estava la, e uma lista fixa de grupos passaria no teste.
        Aqui o painel so pode existir se tiver sido derivado.

        A categoria plantada tambem nao existe no conjunto de partida — a
        codificacao visual e por `category` (`01` §5.3), e um painel que herdasse
        a cor do vizinho passaria despercebido.
        """
        antes = paineis(_estado(), SPECS)
        self.assertNotIn("Biblioteca", [p[GRUPO] for p in antes])
        self.assertNotIn(
            "confidentiality", [i[CATEGORIA] for p in antes for i in p[ITENS]]
        )

        plantada = {
            "name": "fixture.acervo_exposto",
            "type": "boolean",
            "default": False,
            "category": "confidentiality",
            "severity_weight": 7,
            "wallboard_group": "Biblioteca",
            "effect_ui": "Acervo digital marcado como exposto",
        }
        depois = paineis(
            _estado(**{"fixture.acervo_exposto": True}),
            {**SPECS, "fixture.acervo_exposto": plantada},
        )

        novos = [p for p in depois if p[GRUPO] == "Biblioteca"]
        self.assertEqual(len(novos), 1, "o painel do grupo novo nao foi derivado")
        item = novos[0][ITENS][0]
        self.assertEqual(item[CATEGORIA], "confidentiality")
        self.assertEqual(item[ROTULO], "Acervo digital marcado como exposto")
        self.assertTrue(item[ATIVA])
        self.assertEqual(len(depois), len(antes) + 1)

    def test_flag_number_carrega_INTENSIDADE_e_boolean_nao(self) -> None:
        specs = {
            "fixture.taxa": {
                "name": "fixture.taxa", "type": "number", "min": 0, "max": 1,
                "default": 0, "category": "performance", "severity_weight": 6,
                "wallboard_group": "AVA", "effect_ui": "Sessoes derrubadas",
            },
            **SPECS,
        }
        montados = paineis(
            SimulationState(
                flags={**DEFAULTS, "fixture.taxa": 0.25}, simulation_epoch=0
            ),
            specs,
        )
        ava = next(p for p in montados if p[GRUPO] == "AVA")
        self.assertEqual(ava[ITENS][0][INTENSIDADE], 0.25)
        identidade = next(p for p in montados if p[GRUPO] == "Identidade")
        self.assertNotIn(INTENSIDADE, identidade[ITENS][0])


class OQueASalaNaoPodeVer(unittest.TestCase):
    """`06` T6, aplicado as duas superficies que `05` §8 deixa sem autenticacao."""

    def _folhas(self, documento) -> list:
        """Toda chave e todo valor do JSON, recursivamente."""
        achados: list = []
        if isinstance(documento, dict):
            for chave, valor in documento.items():
                achados.append(str(chave))
                achados.extend(self._folhas(valor))
        elif isinstance(documento, list):
            for item in documento:
                achados.extend(self._folhas(item))
        else:
            achados.append(str(documento))
        return achados

    def test_o_wallboard_NAO_carrega_nome_de_flag(self) -> None:
        """Nome de flag e vocabulario de mecanismo, e a sala le negocio.

        E a mesma regra que a peca 5 da Fase 3 aplicou a mensagem de degradacao:
        uma resposta que se explica transforma exercicio em demonstracao.
        """
        payload = json.loads(projecoes.wallboard(_estado(), SPECS))
        folhas = self._folhas(payload)
        for nome in SPECS:
            with self.subTest(flag=nome):
                self.assertNotIn(nome, folhas)

    def test_a_plateia_carrega_UM_campo(self) -> None:
        payload = json.loads(plateia([], {}))
        self.assertEqual(list(payload), [TEXTO])

    def test_a_plateia_NAO_tem_como_receber_o_resto_do_inject(self) -> None:
        """A garantia e do TIPO, e nao de um filtro.

        `plateia` recebe `Mapping[str, str]`. Nao ha `linha`,
        `descricao_facilitador`, `objectives` nem `decision_point` ao alcance —
        vazar exigiria mudar o CHAMADOR. E a D6, e e por isso que
        `pack_loader.Inject` continua sem esses campos.
        """
        from range_core.engine.loader.pack_loader import Inject  # noqa: PLC0415

        for proibido in ("linha", "descricao_facilitador", "texto_para_plateia", "titulo"):
            with self.subTest(campo=proibido):
                self.assertNotIn(proibido, Inject.__dataclass_fields__)


class Plateia(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ExerciseClock(datetime(2026, 8, 16, 9, 0, 0))
        self.store = InMemoryEventStore(self.clock)

    def _dispara(self, inject_id: str):
        from range_core.events.envelope import Correlation  # noqa: PLC0415
        from range_core.events.store import EventDraft  # noqa: PLC0415

        return self.store.append(
            EventDraft(
                event_type=projecoes.INJECT_FIRED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="p", inject_id=inject_id),
                payload={},
            )
        )

    def test_o_texto_e_o_do_ULTIMO_inject_disparado(self) -> None:
        self._dispara("A01")
        self._dispara("A02")
        payload = json.loads(
            plateia(self.store.read_all(), {"A01": "primeiro", "A02": "segundo"})
        )
        self.assertEqual(payload[TEXTO], "segundo")

    def test_sem_inject_disparado_o_texto_e_vazio(self) -> None:
        payload = json.loads(plateia(self.store.read_all(), {"A01": "primeiro"}))
        self.assertEqual(payload[TEXTO], "")


class Timeline(unittest.TestCase):
    """Item 5 da DoD — *"rollback aparece anotado na timeline"*."""

    def setUp(self) -> None:
        self.clock = ExerciseClock(datetime(2026, 8, 16, 9, 0, 0))
        self.store = InMemoryEventStore(self.clock)

    def _append(self, event_type: str, payload: dict, inject_id: str | None = None):
        from range_core.events.envelope import Correlation  # noqa: PLC0415
        from range_core.events.store import EventDraft  # noqa: PLC0415

        return self.store.append(
            EventDraft(
                event_type=event_type,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="p", inject_id=inject_id),
                payload=payload,
            )
        )

    def test_o_rollback_aparece_ANOTADO_com_motivo_e_ponto_de_corte(self) -> None:
        self._append(projecoes.INJECT_FIRED, {}, "A01")
        self._append(
            projecoes.ROLLBACK_PERFORMED,
            {"reason": "facilitation", "to_inject_id": "A01"},
            "A01",
        )
        entradas = json.loads(timeline(self.store.read_all()))[ENTRADAS]

        self.assertNotIn("rollback", entradas[0], "o disparo foi anotado como rollback")
        self.assertEqual(
            entradas[1]["rollback"], {"motivo": "facilitation", "para": "A01"}
        )
        self.assertEqual(entradas[1][ROTULO], "ROLLBACK")

    def test_a_epoch_de_cada_entrada_e_a_do_evento(self) -> None:
        """Sem ela o console nao tem como renderizar epochs separadas — `09` §3."""
        self._append(projecoes.INJECT_FIRED, {}, "A01")
        entradas = json.loads(timeline(self.store.read_all()))[ENTRADAS]
        self.assertEqual(entradas[0]["epoch"], 0)


if __name__ == "__main__":
    unittest.main()
