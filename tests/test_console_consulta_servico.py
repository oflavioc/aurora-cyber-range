"""B2 + H1 da re-auditoria da Fase 8 — o ORÁCULO DE SERVIÇO que faltava.

AUTORIDADE
----------
`02_DOMAIN_ACADEMUS.md` §7:124 (Console de investigação, os cinco filtros) e §4
(a trilha, `within_window` calculado e gravado como Boolean —
`alembic/versions/0004_trilha_de_auditoria.py:130`, `sa.Boolean`).

POR QUE ESTE ARQUIVO EXISTE (B2 da re-auditoria)
------------------------------------------------
`tests/test_console_investigacao.py` e `tests/test_api_emissao_pela_rota.py`
provam o ENCAMINHAMENTO do handler contra um `RepositorioFalso` — um dublê que
reimplementa o filtro sobre `dict` e **copia** o mapa `_FILTRO_PARA_COLUNA`. Isso
mede o handler, e é útil, mas o SQL REAL de
`domains/academus/api/repositorio.py::alteracoes_de_nota` — os filtros que o
data-engineer adicionou — **nunca é exercitado**. Comparar duas cópias do mesmo
mapa não é oráculo independente (R10 §Nascimento: *"oracle independente da
implementação"*).

O oráculo deste arquivo é INDEPENDENTE: o conjunto de linhas que ELE semeia na
`audit_trail` real, com valores conhecidos e distintos por coluna. Ele chama o
`Repositorio` REAL sobre Postgres real e afirma que só as linhas que casam
voltam — a asserção não vem de `_FILTRO_PARA_COLUNA`, vem do que foi semeado.

H1 — `within_window` É BOOLEAN, E `filter_window` É `str` (o RED)
-----------------------------------------------------------------
`within_window` é coluna Boolean; `filter_window` chega ao SQL como `str`, sem
coerção nem validação (`app.py:252` e `repositorio.py:319` declaram `str | None`).
O que o experimento de red mostrou, e é o que fixa o contrato:

  * No REPOSITÓRIO, passar um `bool` (`filter_window=True/False`) já funciona —
    o psycopg adapta o booleano do Python. Esses testes são o ORÁCULO da
    aplicação correta do filtro (verde), não o red.
  * Na ROTA, o parâmetro só pode chegar como `str`. O Postgres coage por acaso
    as strings que SÃO literais booleanos (`'true'`, `'false'`), mas
    **`'business_hours'` — o valor exato que o gate de dublê usa em `FILTROS` —
    dá `invalid input syntax for type boolean` → 500 → nenhum evento emitido.**
    O gate antigo afirma 200 + evento + marcador `auto` para esse mesmo valor;
    sobre o SQL real isso é falso.

O contrato que este gate define e que o data-engineer implementa: `filter_window`
é BOOLEANO (`bool | None`). Como booleano, um valor não-booleano é recusado com
**422 ANTES de consultar** (a mesma disciplina de `test_periodo_invertido...`),
nunca um 500 vazado do driver. O `422 != 500` foi o RED do H1; hoje é verde
(`filter_window: bool | None` na rota, `ea8bf90`).

MATRIZ GATE ↔ MUTANTE (R3 §5) — sobre o SQL real, não sobre `dict`
------------------------------------------------------------------
    MS1  repositório que aceita os filtros e os DESCARTA (aplica só o período)
         -> morto por `test_filter_user_recorta_a_trilha` e demonstrado em
         `MatrizSobreOBancoReal::test_MS1_repo_que_ignora_o_filtro_e_morto`.
    MS2  repositório que TROCA a coluna de um filtro (filter_user -> source_ip)
         -> morto por `test_filter_user_recorta_a_trilha` e demonstrado em
         `MatrizSobreOBancoReal::test_MS2_repo_que_troca_a_coluna_e_morto`.
    MS3  handler/rota que trata `filter_window` como texto livre (estado ATUAL)
         -> morto por `test_filter_window_nao_booleano_e_recusado_sem_500`.
         PROVADO AGORA: é o código atual, e o red o mata.

DADO SINTÉTICO (R11 §4)
-----------------------
`source_ip` é RFC 1918 (`10.x`); `actor_user_id` e `authorization_id` são ids
fictícios. Nada aqui é IOC operacional nem dado real.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from contracts.generated.events import AUDIT_QUERY_PERFORMED
from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.emissor import Emissor
from domains.academus.api.repositorio import Repositorio
from domains.academus.api.surface import carregar
from domains.academus.audit import trilha
from domains.academus.models.registros import RectificationAuthorization, User
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.store import InMemoryEventStore

from _academus_banco import banco_limpo, exige_banco

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"

#: Papel que autoriza a rota; persona do exemplo normativo de `09` §1.
PAPEL = "secretaria"
PERSONA = "ti"

PERIODO = {
    "period_start": "2026-03-01T00:00:00",
    "period_end": "2026-03-31T00:00:00",
}

#: O INSTANTE das linhas semeadas — dentro do período consultado.
QUANDO = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)

#: O CONJUNTO SEMEADO — o oráculo. Cada linha tem valores conhecidos e distintos
#: por coluna, escolhidos para que cada filtro isolado recorte um subconjunto
#: DIFERENTE e a contagem esperada dependa de UM eixo:
#:
#:     seq  actor    source_ip   within_window  authorization_id
#:      1   U-142    10.0.0.7     True           AUTH-1
#:      2   U-999    10.0.0.8     True           AUTH-2
#:      3   U-142    10.0.0.9     False          None
#:      4   U-999    10.0.0.7     False          AUTH-1
#:
#: Donde, sobre o período inteiro:
#:     filter_user=U-142            -> {1, 3}
#:     filter_ip=10.0.0.7           -> {1, 4}
#:     filter_window=True           -> {1, 2}
#:     filter_window=False          -> {3, 4}
#:     filter_authorization=AUTH-1  -> {1, 4}
#:     user=U-142 E window=True     -> {1}
LINHAS = (
    # (sequence esperada, actor, ip, within_window, authorization_id)
    (1, "U-142", "10.0.0.7", True, "AUTH-1"),
    (2, "U-999", "10.0.0.8", True, "AUTH-2"),
    (3, "U-142", "10.0.0.9", False, None),
    (4, "U-999", "10.0.0.7", False, "AUTH-1"),
)


def _semear_dependencias(motor) -> None:
    """Usuários e autorizações que a FK de `audit_trail.authorization_id` exige.

    `banco_limpo()` trunca `users` e `rectification_authorizations`; a fixture de
    demonstração não as popula. Sem estas linhas, semear uma trilha com
    `authorization_id` não-nulo viola FK (`fk_audit_authorization`).
    """
    with Session(motor) as sessao:
        sessao.merge(User(user_id="U-142", username="u142", display_name="Sintetico A", role="secretaria"))
        sessao.merge(User(user_id="U-999", username="u999", display_name="Sintetico B", role="secretaria"))
        for aid, proc in (("AUTH-1", "PROC-0001"), ("AUTH-2", "PROC-0002")):
            sessao.merge(
                RectificationAuthorization(
                    authorization_id=aid,
                    requester_user_id="U-142",
                    approver_user_id="U-999",
                    justification="sintetica",
                    process_number=proc,
                    authorized_on=date(2026, 3, 1),
                )
            )
        sessao.commit()


def _semear_trilha(motor) -> None:
    """Grava o conjunto `LINHAS` pela porta REAL da trilha (`trilha.registrar`).

    Encadeia e atribui `sequence` como a produção — as sequências saem 1..4 na
    ordem de inserção, e é por isso que a identidade (não só a contagem) pode ser
    afirmada.
    """
    for _seq, actor, ip, within, auth in LINHAS:
        with Session(motor) as sessao:
            trilha.registrar(
                sessao,
                trilha.Registro(
                    category=trilha.ALTERACAO_DE_NOTA,
                    actor_user_id=actor,
                    source_ip=ip,
                    object_type="grade",
                    object_id="1",
                    occurred_at=QUANDO,
                    payload={"new_value": 9.0},
                    within_window=within,
                    authorization_id=auth,
                ),
            )
            sessao.commit()


@exige_banco
class ConsultaRealRecortaATrilha(unittest.TestCase):
    """B2 — o SQL real de `alteracoes_de_nota`, cada filtro sobre o oráculo semeado.

    O oráculo é `LINHAS`, não `_FILTRO_PARA_COLUNA`: cada asserção compara o que
    o SQL devolveu contra o subconjunto que ESTE arquivo semeou. Mata MS1 (repo
    que ignora o filtro) e MS2 (repo que troca a coluna).
    """

    def setUp(self) -> None:
        self.motor = banco_limpo()
        _semear_dependencias(self.motor)
        _semear_trilha(self.motor)
        self.repositorio = Repositorio(self.motor)
        self.inicio = datetime.fromisoformat(PERIODO["period_start"])
        self.fim = datetime.fromisoformat(PERIODO["period_end"])

    def _consulta(self, **filtros) -> list[dict]:
        return self.repositorio.alteracoes_de_nota(self.inicio, self.fim, False, **filtros)

    def _sequencias(self, linhas) -> set[int]:
        return {linha["sequence"] for linha in linhas}

    def test_sem_filtro_devolve_o_periodo_inteiro(self) -> None:
        """Controle — sem recorte, o oráculo inteiro volta. Sem ele, um filtro que
        zerasse tudo passaria por vacuidade."""
        self.assertEqual(self._sequencias(self._consulta()), {1, 2, 3, 4})

    def test_filter_user_recorta_a_trilha(self) -> None:
        self.assertEqual(self._sequencias(self._consulta(filter_user="U-142")), {1, 3})

    def test_filter_ip_recorta_a_trilha(self) -> None:
        self.assertEqual(self._sequencias(self._consulta(filter_ip="10.0.0.7")), {1, 4})

    def test_filter_authorization_recorta_a_trilha(self) -> None:
        self.assertEqual(
            self._sequencias(self._consulta(filter_authorization="AUTH-1")), {1, 4}
        )

    def test_filter_window_TRUE_e_booleano_recorta_dentro_da_janela(self) -> None:
        """`filter_window` é BOOLEANO. Passa `True` (não string) e recorta as
        linhas dentro da janela. O contrato do H1: `bool | None`."""
        self.assertEqual(self._sequencias(self._consulta(filter_window=True)), {1, 2})

    def test_filter_window_FALSE_recorta_fora_da_janela(self) -> None:
        self.assertEqual(self._sequencias(self._consulta(filter_window=False)), {3, 4})

    def test_filtros_combinados_intersectam(self) -> None:
        """Dois eixos ao mesmo tempo — a interseção, não a união. Prova que os
        fragmentos `WHERE` se somam com `AND`."""
        self.assertEqual(
            self._sequencias(self._consulta(filter_user="U-142", filter_window=True)),
            {1},
        )

    def test_agrupado_por_usuario_conta_o_recorte_filtrado(self) -> None:
        """O modo `agrupar_por_usuario` também aplica os filtros: `filter_window`
        True agrupa só {1: U-142, 2: U-999} = um por ator."""
        agrupado = self.repositorio.alteracoes_de_nota(
            self.inicio, self.fim, True, filter_window=True
        )
        por_ator = {linha["actor_user_id"]: linha["total"] for linha in agrupado}
        self.assertEqual(por_ator, {"U-142": 1, "U-999": 1})


@exige_banco
class OConsoleSobreOBancoReal(unittest.TestCase):
    """A junta rota→consulta→evento no caminho REAL — repositório sobre Postgres,
    emissor real sobre `InMemoryEventStore`.

    O `result_count` do evento `audit_query_performed` é a contagem da consulta
    FILTRADA — a asserção que o gate de dublê não podia fazer sobre o SQL real.
    """

    def setUp(self) -> None:
        self.motor = banco_limpo()
        _semear_dependencias(self.motor)
        _semear_trilha(self.motor)
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 21, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        # `raise_server_exceptions=False`: um 500 do driver vira RESPOSTA 500, e não
        # exceção propagada — é assim que o teste observa o H1 como a sala o veria.
        self.cliente = TestClient(
            montar(self.autenticacao, Repositorio(self.motor), None, Emissor(store=self.store)),
            raise_server_exceptions=False,
        )

    def _cabecalho(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.autenticacao.emitir_token('S-1', PAPEL, PERSONA)}"
        }

    def _consulta(self, **extras):
        return self.cliente.get(
            "/audit/grade-changes",
            params={**PERIODO, **extras},
            headers=self._cabecalho(),
        )

    def _eventos(self):
        return [e for e in self.store.read_all() if e.event_type == AUDIT_QUERY_PERFORMED]

    def test_result_count_do_evento_reflete_a_consulta_FILTRADA(self) -> None:
        """`filter_user=U-142` sobre o SQL real -> 2 linhas ({1, 3}), e é 2 o
        número que a trilha do evento registra — não 4 (o período inteiro)."""
        resposta = self._consulta(filter_user="U-142")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total"], 2)
        [evento] = self._eventos()
        self.assertEqual(evento.payload["result_count"], 2)

    def test_filter_window_booleano_true_filtra_e_emite(self) -> None:
        """A forma booleana canônica: `filter_window=true` -> {1, 2} = 2, e o
        evento é emitido com esse count."""
        resposta = self._consulta(filter_window="true")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total"], 2)
        [evento] = self._eventos()
        self.assertEqual(evento.payload["result_count"], 2)

    def test_filter_window_nao_booleano_e_recusado_sem_500(self) -> None:
        """H1 — O RED. `filter_window=business_hours` é o valor EXATO que o gate
        de dublê (`test_console_investigacao.py::FILTROS`) usa e afirma válido.

        Sobre o SQL real, `within_window = 'business_hours'` dá
        `invalid input syntax for type boolean` -> 500 -> nenhum evento. Como
        `filter_window` deve ser BOOLEANO (`bool | None`), um valor não-booleano
        é erro de REQUISIÇÃO: 422, recusado ANTES de consultar, e nada vai ao
        store — a mesma disciplina de período invertido.

        Foi o RED do H1 (commit `b8e3b56`): antes de o parâmetro ser tipado, a
        rota devolvia 500 (o driver vazava `invalid input syntax for type
        boolean`) e a asserção de 422 falhava. Ficou VERDE quando `filter_window`
        virou `bool | None` na rota (`ea8bf90`).
        """
        resposta = self._consulta(filter_window="business_hours")
        self.assertEqual(
            resposta.status_code,
            422,
            "filter_window nao-booleano deveria ser recusado como requisicao "
            f"invalida (422), mas veio {resposta.status_code}: o valor caiu no SQL "
            "contra uma coluna Boolean. filter_window precisa ser `bool | None`.",
        )
        self.assertEqual(
            self._eventos(),
            [],
            "um 500 do driver nao pode deixar rastro de consulta que nao ocorreu",
        )


@exige_banco
class MatrizSobreOBancoReal(unittest.TestCase):
    """MS1/MS2 — a discriminação do oráculo, demonstrada sobre o SQL real.

    Prova que a asserção central (`filter_user=U-142 -> {1, 3}`) MATA um
    repositório que ignora o filtro e um que troca a coluna. Subclasses do
    `Repositorio` real (R9 §4: extensão por herança, nunca monkey-patch), sobre o
    mesmo Postgres.
    """

    def setUp(self) -> None:
        self.motor = banco_limpo()
        _semear_dependencias(self.motor)
        _semear_trilha(self.motor)
        self.inicio = datetime.fromisoformat(PERIODO["period_start"])
        self.fim = datetime.fromisoformat(PERIODO["period_end"])

    def _seqs(self, linhas) -> set[int]:
        return {linha["sequence"] for linha in linhas}

    def test_MS1_repo_que_ignora_o_filtro_e_morto(self) -> None:
        class RepoQueIgnoraFiltros(Repositorio):
            def alteracoes_de_nota(self, inicio, fim, agrupar, **_filtros):
                # ERRO: aceita os filtros e chama o período puro, descartando-os.
                return super().alteracoes_de_nota(inicio, fim, agrupar)

        oraculo = Repositorio(self.motor)
        mutante = RepoQueIgnoraFiltros(self.motor)

        certo = self._seqs(oraculo.alteracoes_de_nota(self.inicio, self.fim, False, filter_user="U-142"))
        errado = self._seqs(mutante.alteracoes_de_nota(self.inicio, self.fim, False, filter_user="U-142"))

        self.assertEqual(certo, {1, 3})
        self.assertEqual(errado, {1, 2, 3, 4}, "o mutante ignora o filtro e devolve o período inteiro")
        self.assertNotEqual(certo, errado, "sem a asserção de recorte, o mutante passaria")

    def test_MS2_repo_que_troca_a_coluna_e_morto(self) -> None:
        class RepoQueTrocaColuna(Repositorio):
            # ERRO: filter_user passa a recortar por source_ip.
            _FILTRO_PARA_COLUNA = {
                **Repositorio._FILTRO_PARA_COLUNA,
                "filter_user": "source_ip",
            }

        oraculo = Repositorio(self.motor)
        mutante = RepoQueTrocaColuna(self.motor)

        certo = self._seqs(oraculo.alteracoes_de_nota(self.inicio, self.fim, False, filter_user="U-142"))
        # "U-142" não é IP nenhum -> o mutante devolve vazio, distinto do oráculo.
        errado = self._seqs(mutante.alteracoes_de_nota(self.inicio, self.fim, False, filter_user="U-142"))

        self.assertEqual(certo, {1, 3})
        self.assertEqual(errado, set(), "o mutante compara U-142 contra source_ip e não acha nada")
        self.assertNotEqual(certo, errado, "sem a asserção de coluna correta, o mutante passaria")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
