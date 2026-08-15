"""O event store: o carimbo, a epoch, e o par store -> fold.

O QUE ESTA SOB TESTE
--------------------
A regra de carimbo (D1 do checkpoint, §1.5 do registro) e a atribuicao de epoch,
que sao BACKEND-INDEPENDENTES: vivem no `append` concreto de `EventStore`, e
todo backend as herda. `InMemoryEventStore` e o veiculo, nao o objeto.

O RELOGIO E UM DUPLO, E ISSO E O DESENHO
----------------------------------------
`append` carimba a partir de `ExerciseClockPort`, que e uma porta com um metodo.
O clock real — pausa, multiplicador, T0 — e outra peca; o store nao precisa dela
para ser testavel, e e por isso que a porta existe.
"""

from __future__ import annotations

import unittest
from dataclasses import fields

from contracts.generated.events import (
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.clock.port import Marks
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    TO_EVENT_ID,
    Declarations,
    project,
)
from range_core.events.envelope import Correlation

FLAG = "fixture.written_flag"
FLAG_DEFAULTS = {FLAG: False}


class RelogioFixo:
    """Duplo do `exercise-clock`. Devolve marcas escolhidas pelo teste."""

    def __init__(self) -> None:
        self.marcas = Marks(
            exercise_time="T+00:10:00",
            exercise_timestamp="2026-08-13T09:10:00",
            wall_timestamp="2026-08-13T09:10:00-03:00",
            clock_multiplier=1.0,
        )

    def marks(self) -> Marks:
        return self.marcas


def draft(event_type: str, *, inject_id: str | None = None, payload: dict | None = None):
    return EventDraft(
        event_type=event_type,
        truth_layer="facilitation",
        producer="inject-engine",
        correlation=Correlation(inject_id=inject_id),
        payload=payload or {},
    )


def declarations() -> Declarations:
    return Declarations(
        pack_id="p",
        schema_version=2,
        content_hash="sha256:0000",
        canonicalization="v1",
        flag_defaults=dict(FLAG_DEFAULTS),
        inject_effects={"A01": {FLAG: True}},
        option_effects={},
    )


def started_draft():
    return draft(
        EXERCISE_STARTED,
        payload={
            PACK_ID: "p",
            PACK_SCHEMA_VERSION: 2,
            PACK_CONTENT_HASH: "sha256:0000",
            PACK_CANONICALIZATION: "v1",
        },
    )


class Carimbo(unittest.TestCase):
    def test_o_produtor_nao_tem_onde_escrever_tempo(self):
        """D1 no tipo, e nao na disciplina.

        `EventDraft` nao tem campo para as marcas, para a epoch nem para o id.
        Produtor que quisesse carimbar o proprio tempo nao teria onde.
        """
        campos = {f.name for f in fields(EventDraft)}
        proibidos = {
            "event_id",
            "exercise_time",
            "exercise_timestamp",
            "wall_timestamp",
            "clock_multiplier",
            "simulation_epoch",
        }
        self.assertEqual(campos & proibidos, set())

    def test_append_carimba_as_quatro_marcas_do_clock(self):
        relogio = RelogioFixo()
        store = InMemoryEventStore(relogio)
        evento = store.append(started_draft())

        self.assertEqual(evento.exercise_time, relogio.marcas.exercise_time)
        self.assertEqual(evento.exercise_timestamp, relogio.marcas.exercise_timestamp)
        self.assertEqual(evento.wall_timestamp, relogio.marcas.wall_timestamp)
        self.assertEqual(evento.clock_multiplier, relogio.marcas.clock_multiplier)

    def test_append_atribui_id_e_ids_nao_se_repetem(self):
        store = InMemoryEventStore(RelogioFixo())
        ids = {store.append(started_draft()).event_id for _ in range(50)}
        self.assertEqual(len(ids), 50)
        for identificador in ids:
            self.assertEqual(len(identificador), 26)

    def test_epoch_atribuida_e_a_contagem_de_rollbacks(self):
        """O store ATRIBUI pelo calculo compartilhado; o fold CONFERE com o seu."""
        store = InMemoryEventStore(RelogioFixo())
        primeiro = store.append(started_draft())
        self.assertEqual(primeiro.simulation_epoch, 0)

        store.append(draft(ROLLBACK_PERFORMED, payload={TO_EVENT_ID: primeiro.event_id}))
        depois = store.append(draft(INJECT_FIRED, inject_id="A01"))
        self.assertEqual(depois.simulation_epoch, 1)

    def test_o_rollback_carrega_a_epoch_que_encerra(self):
        """A leitura do diagrama de `09` §3, e a que o fold aceita.

        `_verify_epochs` admite as DUAS leituras para o proprio
        `rollback_performed`. Este teste fixa qual delas o store produz, para que
        a escolha seja visivel em vez de acidental.
        """
        store = InMemoryEventStore(RelogioFixo())
        primeiro = store.append(started_draft())
        rollback = store.append(
            draft(ROLLBACK_PERFORMED, payload={TO_EVENT_ID: primeiro.event_id})
        )
        self.assertEqual(rollback.simulation_epoch, 0)


class Leitura(unittest.TestCase):
    def test_read_all_devolve_tudo_na_ordem_de_append(self):
        store = InMemoryEventStore(RelogioFixo())
        gravados = [store.append(started_draft())]
        gravados.append(store.append(draft(INJECT_FIRED, inject_id="A01")))

        self.assertEqual(
            [e.event_id for e in store.read_all()],
            [e.event_id for e in gravados],
        )

    def test_o_que_read_all_devolve_nao_muta_o_store(self):
        """Append-only que o chamador consegue alterar nao e append-only."""
        store = InMemoryEventStore(RelogioFixo())
        store.append(started_draft())
        lido = store.read_all()
        with self.assertRaises(AttributeError):
            lido.append(started_draft())  # type: ignore[attr-defined]
        self.assertEqual(len(store.read_all()), 1)


class StoreMaisFold(unittest.TestCase):
    """As duas pecas juntas: o que o store produz, o fold consome."""

    def test_gravar_inject_e_projetar_move_a_flag(self):
        store = InMemoryEventStore(RelogioFixo())
        store.append(started_draft())
        store.append(draft(INJECT_FIRED, inject_id="A01"))

        estado = project(store.read_all(), declarations())
        self.assertIs(estado.flags[FLAG], True)
        self.assertEqual(estado.simulation_epoch, 0)

    def test_rollback_gravado_reconstroi_sem_apagar(self):
        """Item 5 da DoD, agora com o evento GRAVADO em vez de construido a mao.

        A metade que faltava ao fold sozinho: quem grava o `rollback_performed`
        e o store.
        """
        store = InMemoryEventStore(RelogioFixo())
        inicio = store.append(started_draft())
        store.append(draft(INJECT_FIRED, inject_id="A01"))
        store.append(draft(ROLLBACK_PERFORMED, payload={TO_EVENT_ID: inicio.event_id}))

        estado = project(store.read_all(), declarations())
        self.assertIs(estado.flags[FLAG], False)
        self.assertEqual(estado.simulation_epoch, 1)
        self.assertEqual(len(store.read_all()), 3, "nada foi removido do store")



class Integridade(unittest.TestCase):
    """A cadeia, sem banco.

    O encadeamento e a peca com consequencia de seguranca, e ela nao pode
    depender de haver Postgres para ser exercitada: sem esta classe, um CI sem
    servico de banco pularia justamente o que mais importa e ficaria verde.
    """

    def _linhas(self, quantos: int):
        from range_core.events.integrity import FIRST_SEQUENCE, GENESIS_HASH, row_hash

        store = InMemoryEventStore(RelogioFixo())
        eventos = [store.append(started_draft()) for _ in range(quantos)]
        linhas, anterior, sequencia = [], GENESIS_HASH, FIRST_SEQUENCE
        for evento in eventos:
            atual = row_hash(evento, anterior)
            linhas.append((sequencia, anterior, atual, evento))
            anterior, sequencia = atual, sequencia + 1
        return linhas

    def test_cadeia_integra_passa(self):
        from range_core.events.integrity import verify_chain

        verify_chain(self._linhas(5))

    def test_campo_alterado_quebra(self):
        from dataclasses import replace

        from range_core.events.integrity import ChainBroken, verify_chain

        linhas = self._linhas(3)
        seq, anterior, gravado, evento = linhas[1]
        linhas[1] = (seq, anterior, gravado, replace(evento, producer="outro"))
        with self.assertRaises(ChainBroken):
            verify_chain(linhas)

    def test_buraco_na_sequencia_quebra(self):
        from range_core.events.integrity import ChainBroken, verify_chain

        linhas = self._linhas(3)
        with self.assertRaises(ChainBroken):
            verify_chain([linhas[0], linhas[2]])

    def test_hash_anterior_que_nao_encadeia_quebra(self):
        from range_core.events.integrity import ChainBroken, GENESIS_HASH, verify_chain

        linhas = self._linhas(3)
        seq, _, gravado, evento = linhas[1]
        linhas[1] = (seq, GENESIS_HASH, gravado, evento)
        with self.assertRaises(ChainBroken):
            verify_chain(linhas)

if __name__ == "__main__":
    unittest.main()
