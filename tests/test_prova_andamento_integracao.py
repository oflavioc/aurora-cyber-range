"""Item 1 da DoD da Fase 8, pelo eixo que faltava: a cláusula "CONFORME A FLAG".

B3 DA SÉTIMA AUDITORIA — O QUE ESTE GATE COBRE, E O QUE O ANTERIOR NÃO COBRIA
----------------------------------------------------------------------------
`tests/test_prova_andamento.py` prova a função pura `frame(seed, rota, flag,
sujeitos, taxa, minuto)` com a `taxa` **passada como argumento** — `ROTA`/`FLAG`
ali são só sal de hash. Nada naquele arquivo prova a CADEIA que faz o Modo
"Prova em andamento" derrubar sessão de verdade:

    processo.py:137-145   descobre `flag_da_prova` varrendo a superfície pela
                          entrada `proporcional`;
    ProvaEmAndamento      (degradacao.py:230-245) LÊ essa flag do ESTADO corrente
                          e chama a derivação;
    GET /exam/session-status  (app.py:166-203) monta o frame do estado do app.

O MODO DE FALHA QUE ISTO FECHA é silencioso: se a descoberta devolver `None`,
`montar(prova=None)`, e o handler cai no ramo all-ALIVE (`app.py:200`) — a suíte
de propriedades fica verde e a sala nunca vê ninguém cair. Este gate liga a
flag ao efeito observável pela ROTA REAL, com estado REAL (store + cache + fold),
como as suítes de serviço fazem (`tests/test_api_degradacao.py`).

O PAR QUE DÁ PODER À ASSERÇÃO
-----------------------------
`test_sem_prova_a_rota_responde_tudo_vivo_mesmo_com_a_flag_cheia` monta a MESMA
rota SEM `ProvaEmAndamento` e prova que, com a flag em 1.0, o frame sai inteiro
vivo. É exatamente o ramo all-ALIVE que mascara a wiring quebrada — e é ele que
torna `..._derruba_TODAS_as_sessoes` capaz de ficar vermelho: sem o par, "todas
vivas" passaria por acidente.

DADO SINTÉTICO (R11 §4)
-----------------------
Alunos e matrículas sintéticos, no curso `C-9001` da fixture de demonstração.
Nenhum identificador real; nada aqui é IOC.
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
from domains.academus.api.degradacao import (
    PROPORCIONAL,
    LeituraDeEstado,
    ProvaEmAndamento,
)
from domains.academus.api.prova_andamento import ALIVE, DROPPED
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
from sqlalchemy.orm import Session

from domains.academus.models.registros import Enrollment, Student

from _academus_app import emissor_de_teste
from _academus_banco import banco_limpo, exige_banco

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAGS_YAML = REPO_ROOT / "domains" / "academus" / "flags.yaml"

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
PERSONA = "ti"

#: FIXO E PASSADO, como em `test_api_degradacao` — um seed lido do ambiente
#: mudaria de resultado com o `.env` de quem roda.
SEED = 20260914

#: A turma da fixture; `P-3001` é o titular, mas esta rota não tem escopo de
#: objeto, então a `secretaria` consulta qualquer turma.
TURMA = "T-2001"
CURSO_DA_FIXTURE = "C-9001"

#: SESSÕES SUFICIENTES PARA HAVER FRAÇÃO. Com poucas, "algumas caem" é granulado
#: pelo tamanho — mesma lição de `test_queda_de_sessao`. Quarenta matrículas
#: fazem a taxa intermediária partir o conjunto com folga.
QUANTAS_SESSOES = 40

#: O minuto de EXERCÍCIO das asserções de queda. >= 1 para o corte cumulativo
#: sair de zero; a cadência em si é de `test_prova_andamento.py`.
MINUTO = 5


def _declaracoes() -> Declarations:
    """As flags do adapter, lidas do arquivo, com os injects que movem a taxa."""
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
            "METADE_CAINDO": {ACADEMUS_LMS_SESSION_DROP_RATE: 0.5},
            "TODAS_CAINDO": {ACADEMUS_LMS_SESSION_DROP_RATE: 1.0},
        },
        option_effects={},
    )


def _relogio() -> ExerciseClock:
    parede = iter(range(1_000_000, 1_100_000))
    return ExerciseClock(datetime(2026, 9, 14, 9, 0, 0), now=lambda: float(next(parede)))


def _flag_da_prova_descoberta(superficie) -> str | None:
    """Espelha EXATAMENTE `processo.py:137-145` — a descoberta que o boot faz.

    Está aqui como oráculo da própria descoberta: se a entrada `proporcional`
    sumir da superfície, `montar(prova=None)` e o Modo nunca derruba. Um teste
    fixa que, sobre a superfície REAL, ela devolve a flag esperada.
    """
    return next(
        (
            entrada.flag
            for rota in superficie.rotas.values()
            for entrada in rota.degradacao
            if entrada.condicao == PROPORCIONAL
        ),
        None,
    )


def _matricula_sinteticos(engine, quantas: int) -> list[str]:
    """Cria `quantas` alunos sintéticos e os matricula em `TURMA`.

    A fixture de demonstração deixa `enrollments` VAZIA de propósito; sem sessão,
    o frame seria trivialmente vazio e nada se provaria. Os ids são sintéticos
    (`05` §3) e o curso é o `C-9001` que a fixture já criou.
    """
    ids = [f"A-9{n:04d}" for n in range(quantas)]
    with Session(engine) as sessao:
        for aluno in ids:
            sessao.add(
                Student(student_id=aluno, name=f"Aluno Sintetico {aluno}", course_id=CURSO_DA_FIXTURE)
            )
        sessao.flush()
        for aluno in ids:
            sessao.add(Enrollment(student_id=aluno, class_id=TURMA))
        sessao.commit()
    return ids


class Cenario:
    """Store real, cache real, fold real — a taxa vem do fold, não de um `set`."""

    def __init__(self, quantas_sessoes: int = QUANTAS_SESSOES) -> None:
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
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.leitura = LeituraDeEstado(
            store=self.store,
            declarations=self.declaracoes,
            cache=InMemoryProjectionCache(),
        )
        self.flag_da_prova = _flag_da_prova_descoberta(self.autenticacao.superficie)

        engine = banco_limpo()
        self.sessoes = _matricula_sinteticos(engine, quantas_sessoes)
        from domains.academus.api.repositorio import Repositorio

        self.repositorio = Repositorio(engine)

    def prova(self) -> ProvaEmAndamento:
        """Construída como `processo.criar` a constrói: mesma leitura, mesmo seed,
        flag DESCOBERTA da superfície."""
        return ProvaEmAndamento(
            leitura=self.leitura, seed=SEED, flag=self.flag_da_prova
        )

    def cliente(self, com_prova: bool = True) -> TestClient:
        return TestClient(
            montar(
                self.autenticacao,
                self.repositorio,
                None,
                emissor_de_teste(),
                prova=self.prova() if com_prova else None,
            )
        )

    def dispara(self, inject_id: str) -> None:
        self.store.append(
            EventDraft(
                event_type=INJECT_FIRED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste", inject_id=inject_id),
            )
        )

    def cabecalho(self) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {self.autenticacao.emitir_token('S-1', 'secretaria', PERSONA)}"
            )
        }

    def sessoes_no_frame(self, cliente: TestClient, minuto: int = MINUTO) -> dict[str, str]:
        resposta = cliente.get(
            "/exam/session-status",
            params={"class_id": TURMA, "exercise_minute": minuto},
            headers=self.cabecalho(),
        )
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["sessions"]


@exige_banco
class ADescobertaDaFlag(unittest.TestCase):
    """A descoberta que o boot faz — sem ela, `prova=None` e o Modo é inerte."""

    def test_a_superficie_real_expoe_a_flag_da_prova_como_proporcional(self):
        superficie = carregar()
        self.assertEqual(
            _flag_da_prova_descoberta(superficie),
            ACADEMUS_LMS_SESSION_DROP_RATE,
            "a descoberta de `processo.py` não acha a flag na superfície: "
            "`montar(prova=None)` e o Modo nunca derruba ninguém",
        )


@exige_banco
class OModoDerrubaConformeAFlag(unittest.TestCase):
    """A cláusula "conforme a flag", provada pela ROTA com estado real."""

    def setUp(self) -> None:
        self.c = Cenario()
        self.cliente = self.c.cliente(com_prova=True)

    def test_com_a_flag_em_zero_ninguem_cai(self):
        """Estado inicial: `lms_session_drop_rate` = 0 (default). Frame todo vivo."""
        frame = self.c.sessoes_no_frame(self.cliente)

        self.assertEqual(set(frame), set(self.c.sessoes), "o frame não é total")
        self.assertEqual(set(frame.values()), {ALIVE}, "alguém caiu com a flag em zero")

    def test_com_a_flag_CHEIA_todas_as_sessoes_caem(self):
        """`TODAS_CAINDO` põe a taxa em 1.0 — no minuto 5, o frame inteiro cai.

        Se a wiring estivesse quebrada (`prova=None`, ou a flag não lida do
        estado), o handler cairia no ramo all-ALIVE e este teste ficaria
        vermelho. É a prova de que a flag chega ao efeito.
        """
        self.c.dispara("TODAS_CAINDO")
        frame = self.c.sessoes_no_frame(self.cliente)

        self.assertEqual(set(frame.values()), {DROPPED}, "a flag cheia não derrubou todas")

    def test_a_flag_e_LIDA_DO_ESTADO_mudar_o_valor_muda_o_frame(self):
        """A taxa NÃO é argumento: ela sai do estado corrente. Disparar o inject
        que a move muda o frame da MESMA rota, com a MESMA `ProvaEmAndamento`."""
        antes = self.c.sessoes_no_frame(self.cliente)
        self.assertEqual(set(antes.values()), {ALIVE})

        self.c.dispara("TODAS_CAINDO")
        depois = self.c.sessoes_no_frame(self.cliente)

        self.assertNotEqual(
            antes,
            depois,
            "mudar a flag no estado não mudou o frame: a rota não lê o estado",
        )
        self.assertEqual(set(depois.values()), {DROPPED})

    def test_taxa_intermediaria_derruba_ALGUMAS_e_poupa_ALGUMAS(self):
        """`METADE_CAINDO` (0.5): há caídas e há sobreviventes — nem tudo, nem nada.

        O par que separa "derruba sempre" de "nunca derruba": as duas metades
        precisam existir no mesmo frame."""
        self.c.dispara("METADE_CAINDO")
        frame = self.c.sessoes_no_frame(self.cliente)

        caidas = sum(1 for e in frame.values() if e == DROPPED)
        self.assertTrue(
            0 < caidas < len(frame),
            f"taxa 0,5 não partiu {len(frame)} sessões: caíram {caidas}",
        )

    def test_no_minuto_zero_ninguem_cai_mesmo_com_a_flag_cheia(self):
        """O minuto de exercício é honrado ponta a ponta: corte 0 no minuto 0."""
        self.c.dispara("TODAS_CAINDO")
        frame = self.c.sessoes_no_frame(self.cliente, minuto=0)

        self.assertEqual(set(frame.values()), {ALIVE}, "caiu alguém no minuto 0")


@exige_banco
class ORamoAllAliveMascara(unittest.TestCase):
    """O par negativo: SEM `ProvaEmAndamento`, a rota responde tudo vivo — mesmo
    com a flag cheia. É o modo de falha silencioso que a auditoria nomeou, e é o
    que dá poder discriminante ao teste de queda acima."""

    def setUp(self) -> None:
        self.c = Cenario()

    def test_sem_prova_a_rota_responde_tudo_vivo_mesmo_com_a_flag_cheia(self):
        cliente = self.c.cliente(com_prova=False)
        self.c.dispara("TODAS_CAINDO")
        frame = self.c.sessoes_no_frame(cliente)

        self.assertEqual(
            set(frame.values()),
            {ALIVE},
            "sem ProvaEmAndamento a rota deveria responder all-ALIVE — é este ramo "
            "que uma wiring quebrada usaria para mascarar a queda",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
