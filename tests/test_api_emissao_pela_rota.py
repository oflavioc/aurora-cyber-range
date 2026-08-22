"""A ROTA emite — item 1 da DoD da Fase 6, provado pela rota e não ao lado dela.

B2 DA AUDITORIA DA FASE 6
--------------------------
`tests/test_api_emissao.py` provava duas coisas úteis e **nenhuma delas era a
emissão**: a guarda de boot, e a fidelidade entre a assinatura do emissor e os
`payload_fields` do hook. O teste do payload chamava `registrar_consulta`
**diretamente**, sem tocar `GET /audit/grade-changes`.

**Medido: apagar o corpo da rota deixava a suíte inteira verde.** O item 1 da DoD
— *"consultar a trilha com filtro de período emite `audit_query_performed`"* —
não tinha prova de emissão. Aqueles dois testes ficam: fidelidade de assinatura é
outra propriedade, e é útil. O que faltava é isto.

O QUE ESTA SUÍTE AFIRMA, E SOBRE O QUÊ
----------------------------------------
Ela exercita a **rota real** por `TestClient`, com o **emissor real** ligado a um
`InMemoryEventStore`, e afirma sobre o **evento que foi para o store** — não sobre
espião e não sobre assinatura. Espião prova que alguém chamou alguém; o evento
prova o que o exercício vai ler.

SEM BANCO, E ISSO NÃO É ATALHO
-------------------------------
O repositório é um duplo com um método. O que está sob teste é a
**instrumentação** — a rota chamar o emissor com os campos certos, e o emissor
gravar o evento certo —, e não a consulta SQL, que precisa de Postgres e é
exercitada onde a stack existe.

Um teste que exigisse banco para provar emissão mediria as duas coisas e falharia
por qualquer uma; e, na prática, **pularia** — que é como o item 1 ficaria sem
prova de novo, agora por ausência de serviço em vez de por ausência de teste.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from datetime import datetime

from contracts.generated.events import AUDIT_QUERY_PERFORMED
from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.emissor import CAMADA, PRODUTOR, Emissor
from domains.academus.api.surface import carregar
from fastapi.testclient import TestClient
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

#: O papel que `domains/academus/api_surface.yaml` autoriza na rota. Lido de lá
#: em vez de escrito aqui seria melhor; escrito aqui, um papel errado dá 403 e o
#: teste falha ALTO — que é o modo de falha aceitável para esta constante.
PAPEL = "secretaria"

PERIODO = {
    "period_start": "2026-03-01T00:00:00",
    "period_end": "2026-03-31T00:00:00",
}


@dataclass
class RepositorioFalso:
    """Um método, o que a rota chama. Sem banco — ver o cabeçalho.

    `linhas` é dado do caso: é ele que decide `result_count`, e é por isso que o
    duplo devolve uma lista configurável em vez de uma fixa. Fixa faria o teste
    do `result_count` medir a constante do duplo.
    """

    linhas: list = field(default_factory=list)
    chamadas: list = field(default_factory=list)

    def alteracoes_de_nota(self, inicio, fim, agrupar):
        self.chamadas.append((inicio, fim, agrupar))
        return list(self.linhas)


class _ComRota(unittest.TestCase):
    def monta(self, linhas=(), com_emissor: bool = True):
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.repositorio = RepositorioFalso(linhas=list(linhas))
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        emissor = Emissor(store=self.store) if com_emissor else None
        self.cliente = TestClient(
            montar(self.autenticacao, self.repositorio, None, emissor)
        )
        return self.cliente

    def cabecalho(self, sub: str = "S-1"):
        return {"Authorization": f"Bearer {self.autenticacao.emitir_token(sub, PAPEL)}"}

    def consulta(self, **extras):
        return self.cliente.get(
            "/audit/grade-changes", params={**PERIODO, **extras}, headers=self.cabecalho()
        )

    def emitidos(self):
        return [
            e for e in self.store.read_all() if e.event_type == AUDIT_QUERY_PERFORMED
        ]


class AGuardaDeBootSobreASuperficieREAL(_ComRota):
    """B1 da sexta auditoria — o ramo negativo que existia e nunca foi chamado.

    `monta(com_emissor=False)` estava escrito desde a peça 3 e **nenhuma chamada
    da suíte o usava**. Ele constrói o `Superficie` de verdade, por `carregar()`,
    e passa por `montar` — o mesmo caminho da produção. Rodá-lo uma vez teria
    pegado o `AttributeError` na primeira execução; em vez disso, 49 testes
    quebraram no worktree da auditoria, todos com o mesmo traceback.

    **A lição não é o tipo, é a forma do teste.** A guarda era provada em
    `test_api_emissao.py` contra dicionários escritos à mão, que têm `.get`; a
    produção entrega um `dataclass` com `slots`, que não tem. O teste mais verde
    da peça 3 era o que provava menos.
    """

    def test_sem_emissor_a_rota_que_declara_emite_RECUSA_o_boot(self):
        with self.assertRaises(RuntimeError) as capturado:
            self.monta(com_emissor=False)
        mensagem = str(capturado.exception)
        self.assertIn("GET /audit/grade-changes", mensagem)
        self.assertIn("emissor", mensagem)

    def test_com_emissor_o_boot_passa(self):
        """O positivo do mesmo eixo, sobre o mesmo objeto.

        Sem ele, uma guarda que recusasse SEMPRE passaria no teste acima.
        """
        self.assertIsNotNone(self.monta(com_emissor=True))


class AConsultaEmiteOEvento(_ComRota):
    """Item 1 da DoD, pela rota — e a afirmação é sobre o EVENTO."""

    def test_a_rota_responde_e_o_evento_vai_para_o_store(self):
        self.monta(linhas=[{"id": 1}, {"id": 2}])
        resposta = self.consulta()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(self.emitidos()), 1)

    def test_o_envelope_do_evento_e_o_declarado(self):
        """`09` §1.1 e §4.1: a camada e o produtor não são escolha do handler."""
        self.monta()
        self.consulta()
        [evento] = self.emitidos()

        self.assertEqual(evento.event_type, AUDIT_QUERY_PERFORMED)
        self.assertEqual(evento.truth_layer, CAMADA)
        self.assertEqual(evento.producer, PRODUTOR)

    def test_o_actor_id_e_o_sub_do_TOKEN_e_nao_um_parametro(self):
        """Quem consultou vem do escopo autenticado, e não do corpo do pedido.

        Se viesse do pedido, a trilha registraria quem o cliente **disse** ser —
        e a segunda camada de `00` §3 passaria a depender da terceira.
        """
        self.monta()
        self.cliente.get(
            "/audit/grade-changes", params=PERIODO, headers=self.cabecalho("S-77")
        )
        [evento] = self.emitidos()

        self.assertEqual(evento.actor_id, "S-77")

    def test_o_payload_carrega_os_quatro_campos_do_hook(self):
        self.monta(linhas=[{"id": 1}, {"id": 2}, {"id": 3}])
        self.consulta(group_by="user")
        [evento] = self.emitidos()

        self.assertEqual(
            set(evento.payload),
            {"period_start", "period_end", "group_by", "result_count"},
        )

    def test_o_result_count_e_o_TAMANHO_DO_QUE_A_CONSULTA_DEVOLVEU(self):
        """Não é constante, e não é o total do banco: é o que a equipe viu.

        `03` §1.2 apoia a evidência `auto` do OBJ-03 nisto. Um `result_count`
        fixo — ou lido de outro lugar — faria o AAR afirmar que a equipe viu o
        que ela não viu.
        """
        self.monta(linhas=[{"id": n} for n in range(7)])
        resposta = self.consulta()
        [evento] = self.emitidos()

        self.assertEqual(evento.payload["result_count"], 7)
        self.assertEqual(resposta.json()["total"], 7)

    def test_o_periodo_emitido_e_o_periodo_PEDIDO(self):
        self.monta()
        self.consulta()
        [evento] = self.emitidos()

        self.assertEqual(evento.payload["period_start"], PERIODO["period_start"])
        self.assertEqual(evento.payload["period_end"], PERIODO["period_end"])

    def test_group_by_ausente_viaja_como_nulo_e_nao_some(self):
        """Campo declarado pelo hook não pode faltar por ausência de parâmetro.

        Sumindo, o payload deixaria de ter os quatro campos e o `observability_
        hooks.yaml` descreveria um evento que não é o emitido.
        """
        self.monta()
        self.consulta()
        [evento] = self.emitidos()

        self.assertIn("group_by", evento.payload)
        self.assertIsNone(evento.payload["group_by"])

    def test_a_rota_de_fato_consultou_o_repositorio(self):
        """O evento é da CONSULTA. Emitir sem consultar seria registrar um ato
        que não houve — e o teste do `result_count` sozinho não distingue os
        dois, porque zero linhas também é resposta."""
        self.monta()
        self.consulta(group_by="user")

        [(inicio, fim, agrupar)] = self.repositorio.chamadas
        self.assertEqual(inicio, datetime.fromisoformat(PERIODO["period_start"]))
        self.assertEqual(fim, datetime.fromisoformat(PERIODO["period_end"]))
        self.assertTrue(agrupar)


class ONaoEmitido(_ComRota):
    """As direções em que o evento NÃO pode aparecer."""

    def test_periodo_invalido_e_recusado_ANTES_de_consultar_e_sem_emitir(self):
        self.monta()
        resposta = self.cliente.get(
            "/audit/grade-changes",
            params={"period_start": "2026-03-31T00:00:00",
                    "period_end": "2026-03-01T00:00:00"},
            headers=self.cabecalho(),
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(self.emitidos(), [])
        self.assertEqual(self.repositorio.chamadas, [])

    def test_periodo_malformado_tambem_nao_emite(self):
        self.monta()
        resposta = self.cliente.get(
            "/audit/grade-changes",
            params={"period_start": "ontem", "period_end": "hoje"},
            headers=self.cabecalho(),
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(self.emitidos(), [])

    def test_sem_token_nao_consulta_e_nao_emite(self):
        self.monta()
        resposta = self.cliente.get("/audit/grade-changes", params=PERIODO)

        self.assertIn(resposta.status_code, (401, 403))
        self.assertEqual(self.emitidos(), [])

    def test_consulta_vazia_EMITE_com_result_count_zero(self):
        """Não achar nada é resultado, e o AAR precisa saber que se procurou.

        É o oposto do caso acima: ali o ato não aconteceu; aqui aconteceu e não
        encontrou. Tratar os dois igual apagaria a diferença entre *"não olhou"*
        e *"olhou e não havia"* — que é a mesma distinção que a lacuna de
        cobertura de `03` §5.4 faz.
        """
        self.monta(linhas=[])
        self.consulta()
        [evento] = self.emitidos()

        self.assertEqual(evento.payload["result_count"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
