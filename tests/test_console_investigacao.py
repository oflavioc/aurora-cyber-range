"""Item 2 da DoD da Fase 8 — o Console de investigação emite os marcadores `auto`.

AUTORIDADE
----------
`02_DOMAIN_ACADEMUS.md` §7:124 — *"Console de investigação: consulta à trilha de
auditoria com filtros de período, usuário, IP, janela e autorização. É onde os
marcadores `auto` de evidência são emitidos."* — e `07_IMPLEMENTATION_PHASES.md`
§Fase 8, item 2 da DoD.

O GATE, E O QUE ELE MEDE (T806)
--------------------------------
Este é o RED do item 2, escrito ANTES da implementação (T812, data-engineer).
Ele prova, pela ROTA real (`GET /audit/grade-changes`) com o EMISSOR real ligado
a um `InMemoryEventStore` — o padrão de `tests/test_api_emissao_pela_rota.py`, e
pelo mesmo motivo: espião prova que alguém chamou alguém; o EVENTO prova o que o
exercício vai ler.

Hoje a consulta carrega **só o período**: `emissor.registrar_consulta` grava
`[period_start, period_end, group_by, result_count]` e nada mais
(`domains/academus/api/emissor.py`). Os quatro filtros do console — usuário, IP,
janela e autorização — **não existem** no handler nem no payload. Por isso este
gate falha, e essa é a prova de red (R3 §4).

OS CINCO FILTROS, COM NOME DE CAMPO FIXADO (o alvo da T812)
-----------------------------------------------------------
`02` §7:124 lista CINCO filtros; período já são dois campos. Os nomes de campo de
payload (identificadores → inglês, CLAUDE.md §Idioma) que este oráculo fixa:

    período      -> period_start, period_end   (JÁ EXISTEM, inalterados)
    usuário      -> filter_user
    IP           -> filter_ip
    janela       -> filter_window
    autorização  -> filter_authorization

Convenção herdada de `period_start`/`period_end`/`group_by`: **nome do parâmetro
de query == nome do campo de payload**, e **campo declarado nunca some por
ausência de parâmetro** — viaja `None`, como `group_by` já faz
(`test_api_emissao_pela_rota::test_group_by_ausente_viaja_como_nulo_e_nao_some`).
A T812 estende `payload_fields` do `observability_hooks.yaml` para os seis campos
de filtro; a fidelidade assinatura↔hook é gate de `tests/test_api_emissao.py` e
NÃO é medida aqui.

O MARCADOR `auto` É PROVADO PELA PROJEÇÃO, NUNCA PELO PAYLOAD
-------------------------------------------------------------
`range-core/objectives/projecao.py` liga `event_type` → objetivo (invariante 4,
`09` §1.2): o marcador `auto` está satisfeito quando o fluxo tem ao menos um
evento daquele tipo — a projeção **não lê payload**. Então "o console emite o
marcador `auto`" prova-se rodando `project` sobre o store depois da consulta e
verificando que `AUDIT_QUERY_PERFORMED` caiu em `auto_satisfeita`. O oráculo é
independente da implementação: um `Objetivo` mínimo montado por `objetivos_de`,
com `auto = [AUDIT_QUERY_PERFORMED]`, e um controle que prova que o marcador
está AUSENTE antes de qualquer consulta.

MATRIZ GATE ↔ MUTANTE (R3 §5; campanha re-executada no green, Fase 6 / T819)
-----------------------------------------------------------------------------
    M1  handler ignora os quatro filtros novos e grava só o período
        (== estado pré-T812)                     -> morto por
        `test_o_payload_carrega_os_cinco_filtros` e `..._com_o_valor_PEDIDO`.
        PROVADO AGORA: é exatamente o código atual, e o red o mata.
    M2  handler lê os filtros mas grava um subconjunto (dropa IP/janela)
        -> morto por `test_o_payload_carrega_os_cinco_filtros` (exige o conjunto
        COMPLETO, não superconjunto de subconjunto).
    M3  handler declara `emite` mas não chama o emissor — a classe P6-7
        -> morto por `test_a_consulta_filtrada_emite_um_evento` (exatamente um)
        e por `test_a_consulta_filtrada_seta_o_auto_de_OBJ03` (sem evento, sem
        marcador).
    M4  handler grava constante em vez do valor pedido
        -> morto por `test_cada_filtro_viaja_com_o_valor_PEDIDO`.
    M5  emissor estendido perde a recusa `SemPersona`
        -> morto por `test_sem_persona_o_emissor_recusa_e_nao_grava`.

MATRIZ DE APLICAÇÃO — B2 DA SÉTIMA AUDITORIA (o que M1–M5 não cobrem)
--------------------------------------------------------------------
M1–M5 medem a GRAVAÇÃO do payload; nenhuma media a APLICAÇÃO do filtro à
consulta. O gate anterior não podia: o `RepositorioFalso` tinha assinatura de
três parâmetros, e por isso era estruturalmente impossível notar que os quatro
filtros nunca chegavam ao SQL. Os mutantes de aplicação:

    M6  consulta que aceita os filtros e os descarta (aplica só o período)
        -> morto por `test_result_count_reflete_a_consulta_FILTRADA_e_nao_a_sem_filtro`
        e demonstrado em `MatrizDeAplicacaoDeFiltro::test_M6_...`.
    M7  handler que grava o filtro no payload mas chama a consulta com três
        posicionais (== estado ATUAL) -> morto por
        `test_os_quatro_filtros_chegam_ao_repositorio`. PROVADO AGORA: é o código
        atual, e o red o mata.

DADO SINTÉTICO (R11 §4)
-----------------------
Os valores de filtro são sintéticos e não roteáveis: `filter_ip` é RFC 1918
(`10.x`), `filter_user` é um id de sujeito fictício. Nada aqui é IOC operacional
nem dado real.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from datetime import datetime

from contracts.generated.events import AUDIT_QUERY_PERFORMED
from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.emissor import Emissor, SemPersona
from domains.academus.api.repositorio import Escopo
from domains.academus.api.surface import carregar
from fastapi.testclient import TestClient
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore
from range_core.objectives.projecao import objetivos_de, project

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

#: O papel que `domains/academus/api_surface.yaml` autoriza na rota; papel errado
#: dá 403 e o teste falha ALTO, que é o modo aceitável para esta constante.
PAPEL = "secretaria"

#: A persona do exemplo normativo de `09` §1 para este mesmo evento.
PERSONA = "ti"

PERIODO = {
    "period_start": "2026-03-01T00:00:00",
    "period_end": "2026-03-31T00:00:00",
}

#: OS QUATRO FILTROS NOVOS — o alvo preciso da T812. Nome de campo == nome de
#: parâmetro de query. Valores sintéticos (R11 §4).
FILTROS = {
    "filter_user": "U-142",
    "filter_ip": "10.0.0.7",
    "filter_window": "business_hours",
    "filter_authorization": "mfa",
}

#: O conjunto que a projeção não lê mas o hook descreve — os seis campos de
#: filtro que o payload do console deve carregar.
CAMPOS_DE_FILTRO = frozenset({"period_start", "period_end", *FILTROS})

#: OBJ-03 no formato de leitura da projeção, com o `event_type` do console como
#: única evidência `auto`. Oráculo independente da implementação do handler.
OBJETIVOS = objetivos_de(
    {
        "objectives": {
            "OBJ-03": {
                "title": "Reconhecer incidentes concorrentes",
                "competency": "incident_triage",
                "rubric": "incident_triage.v2",
                "evidence": {"auto": [AUDIT_QUERY_PERFORMED]},
            }
        }
    }
)


#: O MAPA FILTRO→COLUNA que o repositório real aplica na consulta (`02` §7:124).
#: O duplo o usa para FILTRAR de verdade; é aqui que o contrato da consulta fica
#: legível para o data-engineer (T812): cada filtro do console recorta a trilha
#: por uma coluna da linha de auditoria.
#:
#:     filter_user          -> actor_user_id
#:     filter_ip            -> source_ip
#:     filter_window        -> within_window
#:     filter_authorization -> authorization_id
CAMPO_DA_CONSULTA = {
    "filter_user": "actor_user_id",
    "filter_ip": "source_ip",
    "filter_window": "within_window",
    "filter_authorization": "authorization_id",
}


@dataclass
class RepositorioFalso:
    """A CONSULTA sob teste — não só a instrumentação. B2 da sétima auditoria.

    A versão anterior tinha assinatura de TRÊS parâmetros (`inicio, fim, agrupar`),
    e por isso era estruturalmente impossível notar que os quatro filtros do
    console NÃO chegavam à consulta: o handler os gravava no payload do evento e
    os deixava cair antes do SQL (`app.py` chamava `alteracoes_de_nota(inicio,
    fim, agrupar)`), e o `result_count` do evento descrevia a consulta SEM filtro
    — trilha afirmando um mundo que a consulta não produziu.

    Este duplo passa a ter a ASSINATURA COMPLETA que o repositório real deve
    expor, CAPTURA o que recebeu (`chamadas`) e APLICA os filtros às `linhas`.
    Ele DEFINE o contrato da T812:

        alteracoes_de_nota(inicio, fim, agrupar_por_usuario, *,
                           filter_user=None, filter_ip=None,
                           filter_window=None, filter_authorization=None)

    Os quatro filtros são keyword-only com default `None` de propósito: o handler
    atual, que chama com três posicionais, não quebra — ele apenas deixa os
    filtros em `None`, e é ISSO que os testes de aplicação flagram (o filtro
    pedido não chegou à consulta), em vez de um `TypeError` que confundiria "não
    encaminhou" com "assinatura errada".

    `linhas` é dado do caso: cada linha é um `dict` no formato da trilha, e o
    duplo a recorta pelos filtros recebidos, exatamente como o SQL fará.
    """

    linhas: list = field(default_factory=list)
    chamadas: list = field(default_factory=list)

    def alteracoes_de_nota(
        self,
        inicio,
        fim,
        agrupar_por_usuario,
        *,
        filter_user=None,
        filter_ip=None,
        filter_window=None,
        filter_authorization=None,
    ):
        pedidos = {
            "filter_user": filter_user,
            "filter_ip": filter_ip,
            "filter_window": filter_window,
            "filter_authorization": filter_authorization,
        }
        self.chamadas.append(
            {"inicio": inicio, "fim": fim, "agrupar_por_usuario": agrupar_por_usuario, **pedidos}
        )
        selecionadas = list(self.linhas)
        for filtro, valor in pedidos.items():
            if valor is None:
                continue
            coluna = CAMPO_DA_CONSULTA[filtro]
            selecionadas = [linha for linha in selecionadas if linha.get(coluna) == valor]
        return selecionadas


class _ComConsole(unittest.TestCase):
    def monta(self, linhas=()):
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(
                datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede))
            )
        )
        self.repositorio = RepositorioFalso(linhas=list(linhas))
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(
            montar(self.autenticacao, self.repositorio, None, Emissor(store=self.store))
        )
        return self.cliente

    def cabecalho(self, sub: str = "S-1", persona: str = PERSONA):
        return {
            "Authorization": (
                f"Bearer {self.autenticacao.emitir_token(sub, PAPEL, persona)}"
            )
        }

    def consulta_filtrada(self, **extras):
        """A consulta do console: período + os quatro filtros novos."""
        return self.cliente.get(
            "/audit/grade-changes",
            params={**PERIODO, **FILTROS, **extras},
            headers=self.cabecalho(),
        )

    def consulta_simples(self, **extras):
        """A forma atual — só período. Âncora da regressão."""
        return self.cliente.get(
            "/audit/grade-changes",
            params={**PERIODO, **extras},
            headers=self.cabecalho(),
        )

    def emitidos(self):
        return [
            e for e in self.store.read_all() if e.event_type == AUDIT_QUERY_PERFORMED
        ]

    def cobertura(self):
        """A projeção `objective_evidence` do OBJ-03 sobre o que foi ao store."""
        return project(self.store.read_all(), OBJETIVOS)["OBJ-03"]


class OConsoleEmiteComOsCincoFiltros(_ComConsole):
    """Positivo canônico — a consulta filtrada emite, e o payload carrega os cinco.

    Mata M1 (grava só período), M2 (grava subconjunto) e M4 (grava constante).
    """

    def test_a_consulta_filtrada_emite_um_evento(self):
        self.monta(linhas=[{"id": 1}, {"id": 2}])
        resposta = self.consulta_filtrada()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(self.emitidos()), 1)

    def test_o_payload_carrega_os_cinco_filtros(self):
        self.monta()
        self.consulta_filtrada()
        [evento] = self.emitidos()

        self.assertTrue(
            CAMPOS_DE_FILTRO.issubset(evento.payload),
            f"payload sem os campos de filtro: faltam "
            f"{CAMPOS_DE_FILTRO - set(evento.payload)}",
        )

    def test_cada_filtro_viaja_com_o_valor_PEDIDO(self):
        """Não é constante e não vem do token: é o que o console pediu.

        Um valor fixo — ou lido de outro lugar — faria a trilha registrar um
        filtro que não foi o aplicado.
        """
        self.monta()
        self.consulta_filtrada()
        [evento] = self.emitidos()

        for campo, valor in FILTROS.items():
            self.assertEqual(evento.payload.get(campo), valor, campo)
        self.assertEqual(evento.payload.get("period_start"), PERIODO["period_start"])
        self.assertEqual(evento.payload.get("period_end"), PERIODO["period_end"])

    def test_filtro_ausente_viaja_como_NULO_e_nao_some(self):
        """Campo declarado não pode faltar por ausência de parâmetro — o mesmo
        contrato de `group_by`. Sumindo, o hook descreveria um evento que não é
        o emitido."""
        self.monta()
        self.consulta_simples()  # nenhum dos quatro filtros novos
        [evento] = self.emitidos()

        for campo in FILTROS:
            self.assertIn(campo, evento.payload)
            self.assertIsNone(evento.payload[campo])


class OConsoleSetaOMarcadorAuto(_ComConsole):
    """Item 2, pelo eixo que o define: a projeção `auto` marca OBJ-03.

    Prova PELA PROJEÇÃO, nunca pelo payload (a projeção não lê payload). Mata M3
    (handler que não chama o emissor: sem evento, o marcador fica ausente).
    """

    def test_o_auto_esta_AUSENTE_antes_de_qualquer_consulta(self):
        """Controle — sem ele, um marcador satisfeito por construção passaria."""
        self.monta()
        cobertura = self.cobertura()

        self.assertIn(AUDIT_QUERY_PERFORMED, cobertura.auto_ausente)
        self.assertNotIn(AUDIT_QUERY_PERFORMED, cobertura.auto_satisfeita)

    def test_a_consulta_filtrada_seta_o_auto_de_OBJ03(self):
        self.monta(linhas=[{"id": 1}])
        self.consulta_filtrada()
        cobertura = self.cobertura()

        self.assertIn(AUDIT_QUERY_PERFORMED, cobertura.auto_satisfeita)
        self.assertNotIn(AUDIT_QUERY_PERFORMED, cobertura.auto_ausente)


class ARegressaoDoComportamentoAtual(_ComConsole):
    """A forma atual — só período — continua emitindo e marcando. Não quebrar o
    `audit_query_performed` que já existe (item 1 da Fase 6)."""

    def test_consulta_simples_ainda_responde_e_emite(self):
        self.monta(linhas=[{"id": n} for n in range(7)])
        resposta = self.consulta_simples()
        [evento] = self.emitidos()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(evento.payload["result_count"], 7)
        self.assertEqual(evento.payload["period_start"], PERIODO["period_start"])

    def test_consulta_simples_ainda_seta_o_auto(self):
        self.monta()
        self.consulta_simples()

        self.assertIn(AUDIT_QUERY_PERFORMED, self.cobertura().auto_satisfeita)


class OEventoQueNaoPodeAparecer(_ComConsole):
    """As direções em que o console NÃO pode emitir — nem parcial, nem sem sujeito."""

    def test_sem_token_a_consulta_filtrada_nao_emite_nem_marca(self):
        self.monta()
        resposta = self.cliente.get(
            "/audit/grade-changes", params={**PERIODO, **FILTROS}
        )

        self.assertIn(resposta.status_code, (401, 403))
        self.assertEqual(self.emitidos(), [])
        self.assertIn(AUDIT_QUERY_PERFORMED, self.cobertura().auto_ausente)

    def test_periodo_invertido_com_filtros_e_recusado_sem_emitir(self):
        """Filtro malformado não vira evento parcial silencioso: recusa ANTES de
        consultar, e nada vai ao store."""
        self.monta()
        resposta = self.cliente.get(
            "/audit/grade-changes",
            params={
                "period_start": "2026-03-31T00:00:00",
                "period_end": "2026-03-01T00:00:00",
                **FILTROS,
            },
            headers=self.cabecalho(),
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(self.emitidos(), [])
        self.assertEqual(self.repositorio.chamadas, [])

    def test_sem_persona_o_emissor_recusa_e_nao_grava(self):
        """A recusa ALTA `SemPersona` sobrevive à extensão do emissor (T812).

        Chama `registrar_consulta` com os quatro filtros novos e um `Escopo` sem
        persona: a assinatura estendida deve aceitá-los E manter a guarda. Nada
        pode ir ao store.
        """
        self.monta()
        emissor = Emissor(store=self.store)

        with self.assertRaises(SemPersona):
            emissor.registrar_consulta(
                period_start=PERIODO["period_start"],
                period_end=PERIODO["period_end"],
                group_by=None,
                result_count=0,
                escopo=Escopo(sub="S-1", regra=None, persona=None),
                **FILTROS,
            )
        self.assertEqual(self.emitidos(), [])


class OsFiltrosSaoAplicadosAConsulta(_ComConsole):
    """B2 — o eixo que o gate anterior não media: o filtro chega ao SQL, e o
    `result_count` do evento reflete a consulta FILTRADA, não a sem-filtro.

    Prova a APLICAÇÃO (o repositório recebe o filtro e recorta as linhas), e não
    só a GRAVAÇÃO (o payload carrega o filtro). O defeito atual — handler que
    encaminha os filtros só ao emissor — mata os dois testes desta classe.

    Mata M6 (repo/handler que ignora o filtro e aplica só o período).
    """

    def test_os_quatro_filtros_chegam_ao_repositorio(self):
        """A CONSULTA recebeu os quatro valores pedidos — não apenas o payload.

        Hoje o handler grava os filtros no evento e chama a consulta só com
        `(inicio, fim, agrupar)`: o duplo os captura como `None`, e esta asserção
        fica vermelha. Essa é a prova de red do B2 (R3 §4).
        """
        self.monta()
        self.consulta_filtrada()
        [chamada] = self.repositorio.chamadas

        for campo, valor in FILTROS.items():
            self.assertEqual(
                chamada[campo],
                valor,
                f"o filtro {campo!r} não chegou à consulta (chegou {chamada[campo]!r}): "
                "o handler o gravou no evento e o deixou cair antes do SQL",
            )

    def test_result_count_reflete_a_consulta_FILTRADA_e_nao_a_sem_filtro(self):
        """O `result_count` do evento é o tamanho da consulta COM filtro.

        Cinco linhas na trilha, três do usuário pedido. Uma consulta por
        `filter_user` deve devolver TRÊS, e é esse o número que a trilha registra.
        Hoje o filtro não chega ao SQL: a consulta devolve as cinco, e o evento
        carrega `filter_user` ao lado de um `result_count=5` — `effect_class:
        observation` afirmando o que não ocorreu. Vermelho até a T812.
        """
        self.monta(
            linhas=[
                {"actor_user_id": "U-142"},
                {"actor_user_id": "U-142"},
                {"actor_user_id": "U-142"},
                {"actor_user_id": "U-999"},
                {"actor_user_id": "U-999"},
            ]
        )
        # Só `filter_user` viaja — os outros três ficam ausentes, e o duplo não os
        # aplica: assim o número esperado depende de UM eixo, e o teste não mede a
        # interseção de quatro recortes.
        self.consulta_simples(filter_user="U-142")
        [evento] = self.emitidos()

        self.assertEqual(
            evento.payload["result_count"],
            3,
            "result_count veio da consulta SEM filtro: o evento afirma um tamanho "
            "que a consulta filtrada não produziu",
        )
        [chamada] = self.repositorio.chamadas
        self.assertEqual(chamada["filter_user"], "U-142")

    def test_a_consulta_filtrada_ainda_emite_e_marca_o_auto(self):
        """A aplicação não pode custar a emissão: com filtros aplicados, o evento
        continua sendo emitido e o `auto` de OBJ-03 continua sendo marcado."""
        self.monta(linhas=[{"actor_user_id": "U-142"}])
        self.consulta_filtrada()

        self.assertEqual(len(self.emitidos()), 1)
        self.assertIn(AUDIT_QUERY_PERFORMED, self.cobertura().auto_satisfeita)


class MatrizDeAplicacaoDeFiltro(unittest.TestCase):
    """M6/M7 — a APLICAÇÃO do filtro à consulta, o que M1–M5 (payload) não cobrem.

    Auto-contida: demonstra, sem depender do handler (que hoje nem encaminha os
    filtros), que a asserção central do gate — `result_count` == tamanho da
    consulta filtrada — MATA um repositório que ignora o filtro e aplica só o
    período. R3 §5 / R10 §Nascimento.
    """

    INICIO = datetime.fromisoformat(PERIODO["period_start"])
    FIM = datetime.fromisoformat(PERIODO["period_end"])
    LINHAS = [{"actor_user_id": "U-142"}] * 3 + [{"actor_user_id": "U-999"}] * 2

    def test_M6_repo_que_IGNORA_o_filtro_de_usuario_e_morto(self):
        """Mutante: consulta que devolve tudo do período, ignorando `filter_user`."""

        class RepoQueSoAplicaPeriodo:
            def __init__(self, linhas):
                self.linhas = linhas

            def alteracoes_de_nota(
                self,
                inicio,
                fim,
                agrupar_por_usuario,
                *,
                filter_user=None,
                filter_ip=None,
                filter_window=None,
                filter_authorization=None,
            ):
                # ERRO: aceita os filtros e os descarta — só o período conta.
                return list(self.linhas)

        oraculo = RepositorioFalso(linhas=list(self.LINHAS))
        mutante = RepoQueSoAplicaPeriodo(list(self.LINHAS))

        n_oraculo = len(
            oraculo.alteracoes_de_nota(self.INICIO, self.FIM, False, filter_user="U-142")
        )
        n_mutante = len(
            mutante.alteracoes_de_nota(self.INICIO, self.FIM, False, filter_user="U-142")
        )

        self.assertEqual(n_oraculo, 3, "o repositório-oráculo recorta pelo filtro")
        self.assertEqual(n_mutante, 5, "o mutante ignora o filtro e devolve tudo")
        # É esta desigualdade que `test_result_count_reflete_a_consulta_FILTRADA`
        # transforma em veredito: o número que a trilha registra separa os dois.
        self.assertNotEqual(
            n_oraculo,
            n_mutante,
            "sem a asserção de result_count-filtrado, o mutante passaria",
        )

    def test_M7_handler_que_nao_encaminha_o_filtro_e_morto(self):
        """Mutante: o handler grava o filtro no payload mas chama a consulta com
        três posicionais — o defeito ATUAL. O duplo o captura como `None`.

        Reproduz a chamada do handler de hoje e prova que o filtro não chega."""
        oraculo = RepositorioFalso(linhas=list(self.LINHAS))
        # A chamada exata do handler atual (app.py) — três posicionais, sem filtros.
        oraculo.alteracoes_de_nota(self.INICIO, self.FIM, False)
        [chamada] = oraculo.chamadas

        self.assertIsNone(
            chamada["filter_user"],
            "a chamada de três posicionais deixa o filtro em None — é assim que o "
            "gate detecta que o handler não encaminhou",
        )
        # O par: encaminhando, o mesmo duplo registra o valor pedido.
        oraculo.chamadas.clear()
        oraculo.alteracoes_de_nota(self.INICIO, self.FIM, False, filter_user="U-142")
        self.assertEqual(oraculo.chamadas[0]["filter_user"], "U-142")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
