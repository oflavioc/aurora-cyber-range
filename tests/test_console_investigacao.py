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


@dataclass
class RepositorioFalso:
    """Um método, o que a rota chama. Sem banco — a instrumentação é o que está
    sob teste, não a consulta SQL (ver `test_api_emissao_pela_rota` §cabeçalho).

    `linhas` é dado do caso: decide `result_count`. Fixa faria o teste medir a
    constante do duplo.
    """

    linhas: list = field(default_factory=list)
    chamadas: list = field(default_factory=list)

    def alteracoes_de_nota(self, inicio, fim, agrupar):
        self.chamadas.append((inicio, fim, agrupar))
        return list(self.linhas)


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
