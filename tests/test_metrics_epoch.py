"""Epoch como calculo do consumidor — `06` T10, os dois criterios por nome.

O que esta suite prova:

1. o desconto usa a **uniao** dos intervalos, **nunca a soma** — e os casos
   sobrepostos sao escritos de forma que uma implementacao que somasse passasse
   a reprovar, em vez de so nao ser exercitada;
2. **nenhum evento de epoch com `reason: rehearsal` entra em calculo** — nem a
   escrituracao, nem os eventos do lado, nem o intervalo de um
   `technical_failure` que tenha caido dentro da epoch descartada;
3. o desconto e **calculo sobre insumo presente**, e nao numero que aparece por
   ausencia de insumo: o teste da montagem afirma que a escrituracao CHEGA
   inteira aos dois lados antes de qualquer conta.

A ORDEM TOTAL E `exercise_timestamp`, e os casos sao escritos nela. `06` T3
percorre os outros tres relogios e descarta cada um; aqui isso aparece como o
fato de os extremos serem `datetime` absolutos que nao rebobinam entre epochs.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from contracts.generated.events import (
    CONTAINMENT_DECLARED,
    EXERCISE_STARTED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.exercise_clock import ExerciseClock
from range_core.events.envelope import Correlation, Event
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.metrics.epoch import (
    MOTIVO_ENSAIO,
    MOTIVO_FALHA_TECNICA,
    Congelamento,
    JanelaInvertida,
    congelamentos,
    decorrido,
    epochs_descartadas,
    instante,
    no_calculo,
    uniao,
)
from range_core.metrics.insumo import monta

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

DIA = "2026-08-20"


def em(hora: str) -> datetime:
    """`"09:30"` -> instante do dia do exercicio. Legibilidade dos casos."""
    return datetime.fromisoformat(f"{DIA}T{hora}:00")


def janela(inicio: str, fim: str) -> Congelamento:
    return Congelamento(inicio=em(inicio), fim=em(fim))


def evento(tipo: str, *, epoch: int = 0, hora: str = "09:00", **payload: object) -> Event:
    """Evento montado a mao, para os casos das funcoes puras.

    Sem store de proposito: `uniao` e `decorrido` nao dependem de append nenhum,
    e faze-las passar por um store acoplaria o teste da regra ao teste do
    carimbo.
    """
    return Event(
        event_id=f"{tipo}-{epoch}-{hora}",
        event_type=tipo,
        truth_layer="facilitation",
        producer="teste",
        exercise_time="T+00:00",
        exercise_timestamp=f"{DIA}T{hora}:00",
        wall_timestamp=f"{DIA}T{hora}:00",
        clock_multiplier=1.0,
        simulation_epoch=epoch,
        correlation=Correlation(),
        payload=payload,
    )


def rollback(
    motivo: str, *, epoch: int, hora: str = "09:00", congela: tuple[str, str] | None = None
) -> Event:
    carga: dict[str, object] = {
        "to_event_id": "01J9F00000000000000000000A",
        "reason": motivo,
        "by_user": "fac",
        "role": "facilitador",
    }
    if congela is not None:
        carga["frozen_interval"] = {
            "start": f"{DIA}T{congela[0]}:00",
            "end": f"{DIA}T{congela[1]}:00",
        }
    return evento(ROLLBACK_PERFORMED, epoch=epoch, hora=hora, **carga)


class UniaoNuncaSoma(unittest.TestCase):
    """`06` T10: *"o desconto usa a uniao dos intervalos, nunca a soma"*.

    Os casos sobrepostos sao escritos com a SOMA calculada ao lado e afirmada
    diferente. Sem essa segunda afirmacao, uma implementacao que somasse
    continuaria passando nos casos disjuntos — onde soma e uniao coincidem — e o
    criterio de T10 nunca teria sido exercitado.
    """

    def test_sobrepostos_contam_o_trecho_comum_uma_vez(self):
        intervalos = [janela("09:10", "09:40"), janela("09:30", "10:00")]
        fundidos = uniao(intervalos)

        self.assertEqual(fundidos, (janela("09:10", "10:00"),))
        self.assertEqual(sum((c.duracao for c in fundidos), timedelta()),
                         timedelta(minutes=50))

        somadas = sum((c.duracao for c in intervalos), timedelta())
        self.assertEqual(somadas, timedelta(minutes=60))
        self.assertLess(
            sum((c.duracao for c in fundidos), timedelta()),
            somadas,
            "a uniao tem de ser MENOR que a soma aqui; se forem iguais, o "
            "trecho comum foi contado duas vezes",
        )

    def test_um_intervalo_contido_no_outro_nao_acrescenta_nada(self):
        """O caso extremo da sobreposicao, e o que mais engana: a soma DOBRA."""
        externo, interno = janela("09:00", "10:00"), janela("09:20", "09:30")
        fundidos = uniao([externo, interno])

        self.assertEqual(fundidos, (externo,))
        self.assertLess(
            sum((c.duracao for c in fundidos), timedelta()),
            externo.duracao + interno.duracao,
        )

    def test_adjacentes_exatos_fundem(self):
        """`fim == inicio` do seguinte e um unico trecho de relogio parado."""
        self.assertEqual(
            uniao([janela("09:00", "09:20"), janela("09:20", "09:35")]),
            (janela("09:00", "09:35"),),
        )

    def test_disjuntos_permanecem_dois(self):
        """O controle positivo: sem sobreposicao, uniao e soma coincidem.

        Ele existe para a suite nao passar por uma `uniao` que funda tudo num
        intervalo so — que reprovaria os casos acima por acidente e produziria
        desconto maior que o real.
        """
        dois = [janela("09:00", "09:10"), janela("09:30", "09:40")]
        self.assertEqual(uniao(dois), tuple(dois))

    def test_a_ordem_de_entrada_nao_muda_o_resultado(self):
        fora_de_ordem = [janela("09:30", "10:00"), janela("09:10", "09:40")]
        self.assertEqual(uniao(fora_de_ordem), (janela("09:10", "10:00"),))

    def test_sem_intervalo_nenhum_a_uniao_e_vazia(self):
        self.assertEqual(uniao([]), ())


class DescontoRecortaAJanela(unittest.TestCase):
    """O congelamento so desconta a parte que cai DENTRO da metrica."""

    def test_congelamento_inteiro_dentro_da_janela(self):
        self.assertEqual(
            decorrido(em("09:00"), em("10:00"), [janela("09:20", "09:35")]),
            timedelta(minutes=45),
        )

    def test_congelamento_que_comeca_antes_do_start_so_desconta_o_que_cai_dentro(self):
        """Descontar inteiro subtrairia tempo que a metrica nunca contou."""
        self.assertEqual(
            decorrido(em("09:30"), em("10:00"), [janela("09:00", "09:40")]),
            timedelta(minutes=20),
        )

    def test_congelamento_inteiramente_fora_nao_desconta(self):
        self.assertEqual(
            decorrido(em("09:00"), em("09:30"), [janela("10:00", "10:20")]),
            timedelta(minutes=30),
        )

    def test_sem_congelamento_o_decorrido_e_a_distancia(self):
        self.assertEqual(
            decorrido(em("09:00"), em("09:47"), []), timedelta(minutes=47)
        )

    def test_janela_invertida_levanta_em_vez_de_devolver_negativo(self):
        """`exercise_timestamp` nao rebobina: invertida e start e stop trocados."""
        with self.assertRaises(JanelaInvertida):
            decorrido(em("10:00"), em("09:00"), [])


class EnsaioDescartaAEpoch(unittest.TestCase):
    """`09` §3.1: *"nenhum evento da epoch entra em calculo"*.

    Nao e desconto de tempo — e exclusao de evento. As duas regras nao se
    reduzem uma a outra, e por isso tem casos separados.
    """

    def test_a_epoch_descartada_e_a_do_proprio_rollback(self):
        """O store carimba ANTES do append, entao o evento fecha a epoch dele."""
        escrituracao = (rollback(MOTIVO_ENSAIO, epoch=1, hora="09:30"),)
        self.assertEqual(epochs_descartadas(escrituracao), frozenset({1}))

    def test_rollback_de_outro_motivo_nao_descarta_nada(self):
        for motivo in (MOTIVO_FALHA_TECNICA, "facilitation", "adjudication"):
            with self.subTest(motivo=motivo):
                congela = ("09:10", "09:20") if motivo == MOTIVO_FALHA_TECNICA else None
                escrituracao = (rollback(motivo, epoch=1, congela=congela),)
                self.assertEqual(epochs_descartadas(escrituracao), frozenset())

    def test_evento_do_lado_na_epoch_descartada_nao_entra_em_calculo(self):
        """Vale para os eventos do LADO, e nao so para a escrituracao.

        E a razao de a escrituracao ir aos dois lados: sem ela, o computador da
        declaracao nao teria como saber que a epoch dele foi descartada.
        """
        descartadas = frozenset({1})
        eventos = (
            evento(CONTAINMENT_DECLARED, epoch=1, hora="09:20"),
            evento(CONTAINMENT_DECLARED, epoch=2, hora="09:50"),
        )
        sobreviventes = no_calculo(eventos, descartadas)

        self.assertEqual(len(sobreviventes), 1)
        self.assertEqual(sobreviventes[0].simulation_epoch, 2)

    def test_congelamento_registrado_em_epoch_descartada_nao_conta(self):
        """O cruzamento das duas regras, e ele e o caso que engana.

        Um `technical_failure` dentro de uma epoch que um `rehearsal` posterior
        descartou e evento daquela epoch. `09` §3.1 nao abre excecao por especie
        de evento, entao o intervalo dele nao desconta nada.
        """
        escrituracao = (
            rollback(MOTIVO_FALHA_TECNICA, epoch=1, hora="09:20",
                     congela=("09:05", "09:15")),
            rollback(MOTIVO_ENSAIO, epoch=1, hora="09:40"),
        )
        self.assertEqual(congelamentos(escrituracao), ())

    def test_congelamento_de_epoch_viva_continua_contando(self):
        """O controle do caso acima: sem ele, `congelamentos` podia devolver
        vazio sempre e passar."""
        escrituracao = (
            rollback(MOTIVO_FALHA_TECNICA, epoch=2, hora="09:20",
                     congela=("09:05", "09:15")),
            rollback(MOTIVO_ENSAIO, epoch=1, hora="09:40"),
        )
        self.assertEqual(congelamentos(escrituracao), (janela("09:05", "09:15"),))


class CongelamentosSaemUnidosDaEscrituracao(unittest.TestCase):
    """A uniao acontece UMA vez, no ponto que os dois computadores chamam."""

    def test_dois_technical_failure_sobrepostos_saem_como_um(self):
        escrituracao = (
            rollback(MOTIVO_FALHA_TECNICA, epoch=0, hora="09:45",
                     congela=("09:10", "09:40")),
            rollback(MOTIVO_FALHA_TECNICA, epoch=1, hora="10:05",
                     congela=("09:30", "10:00")),
        )
        self.assertEqual(congelamentos(escrituracao), (janela("09:10", "10:00"),))

    def test_o_desconto_sobre_eles_e_a_uniao_e_nao_a_soma(self):
        """A propriedade de T10 ponta a ponta, da escrituracao ao numero."""
        escrituracao = (
            rollback(MOTIVO_FALHA_TECNICA, epoch=0, hora="09:45",
                     congela=("09:10", "09:40")),
            rollback(MOTIVO_FALHA_TECNICA, epoch=1, hora="10:05",
                     congela=("09:30", "10:00")),
        )
        liquido = decorrido(em("09:00"), em("10:30"), congelamentos(escrituracao))

        self.assertEqual(liquido, timedelta(minutes=40))
        self.assertNotEqual(
            liquido,
            timedelta(minutes=30),
            "30 min e o que a SOMA das duracoes produziria — o trecho comum "
            "descontado duas vezes. T10 proibe por nome.",
        )

    def test_evento_de_epoch_que_nao_e_rollback_nao_vira_congelamento(self):
        escrituracao = (evento(EXERCISE_STARTED, epoch=0),)
        self.assertEqual(congelamentos(escrituracao), ())


class OInsumoChegaInteiroEODescontoECalculo(unittest.TestCase):
    """`00` §3.2: o numero certo nao pode aparecer por AUSENCIA de insumo.

    O teste afirma a presenca ANTES da conta. Se o montador recortasse a
    escrituracao, `insumo.epoch` viria vazio, `congelamentos` devolveria `()` e o
    desconto seria zero — resultado que, num teste que so olhasse o numero,
    ficaria indistinguivel de "nao houve congelamento".
    """

    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        self.store = InMemoryEventStore(
            ExerciseClock(datetime(2026, 8, 20, 9, 0, 0), now=lambda: float(next(parede)))
        )
        self.store.append(
            EventDraft(
                event_type=EXERCISE_STARTED,
                truth_layer="facilitation",
                producer="teste",
                correlation=Correlation(),
                payload={},
            )
        )
        self.ancora = self.store.read_all()[0]
        self.store.append(
            EventDraft(
                event_type=ROLLBACK_PERFORMED,
                truth_layer="facilitation",
                producer="teste",
                correlation=Correlation(),
                payload={
                    "to_event_id": self.ancora.event_id,
                    "reason": MOTIVO_FALHA_TECNICA,
                    "by_user": "fac",
                    "role": "facilitador",
                    "frozen_interval": {
                        "start": f"{DIA}T09:05:00",
                        "end": f"{DIA}T09:25:00",
                    },
                },
            )
        )

    def _insumos(self):
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        lados = dict(registro["x-aurora-registry"]["metric_side"])
        return monta(
            self.store.read_all(),
            lados,
            limiar_de_calibracao=0.15,
            defensibilidade={},
        )

    def test_a_escrituracao_chega_aos_dois_lados_antes_da_conta(self):
        declaracao, verificacao = self._insumos()
        for lado, insumo in (("declaracao", declaracao), ("verificacao", verificacao)):
            with self.subTest(lado=lado):
                tipos = {e.event_type for e in insumo.epoch}
                self.assertIn(ROLLBACK_PERFORMED, tipos)

    def test_o_desconto_sai_do_insumo_dos_dois_lados_e_e_o_mesmo(self):
        declaracao, verificacao = self._insumos()
        esperado = (janela("09:05", "09:25"),)

        self.assertEqual(congelamentos(declaracao.epoch), esperado)
        self.assertEqual(congelamentos(verificacao.epoch), esperado)

    def test_o_instante_de_um_evento_e_o_exercise_timestamp(self):
        """Um so lugar converte, e e onde a escolha de `06` T3 fica visivel."""
        self.assertEqual(
            instante(self.ancora),
            datetime.fromisoformat(self.ancora.exercise_timestamp),
        )


class MotivosConferemComOContrato(unittest.TestCase):
    """As constantes deste modulo contra o enum real de `rollback_reason`.

    Motivo novo no contrato sem decisao no modulo cairia em nenhum dos dois
    ramos e sumiria — nem desconto nem descarte, sem nada acusar. Este teste
    transforma isso em reprovacao.
    """

    def enum(self) -> list[str]:
        registro = parse_yaml(REPO_ROOT / "contracts" / "events.schema.yaml")
        return list(registro["$defs"]["rollback_reason"]["enum"])

    def test_os_dois_motivos_com_efeito_estao_no_enum(self):
        motivos = self.enum()
        self.assertIn(MOTIVO_FALHA_TECNICA, motivos)
        self.assertIn(MOTIVO_ENSAIO, motivos)

    def test_o_enum_nao_cresceu_sem_decisao_neste_modulo(self):
        """Os outros dois — `facilitation` e `adjudication` — nao produzem
        desconto nem descarte por `09` §3.1, e a ausencia deles aqui e decidida.
        """
        self.assertEqual(
            set(self.enum()),
            {MOTIVO_FALHA_TECNICA, MOTIVO_ENSAIO, "facilitation", "adjudication"},
            "o enum de `rollback_reason` mudou. Motivo novo precisa de decisao "
            "explicita em `range-core/metrics/epoch.py`: desconta, descarta, ou "
            "nem um nem outro — e por que.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
