"""O mecanismo do M1 conferido contra si mesmo — os negativos e o controle.

POR QUE ESTE ARQUIVO EXISTE
----------------------------
`tests/conformidade_de_envelope.py` é a camada que impede os três produtores de
gravar um envelope que o contrato recusa. Uma camada assim **falha em silêncio da
pior forma possível**: ela não fica vermelha quando quebra — fica verde validando
nada, e o produtor segue emitindo.

É a mesma disciplina que o projeto aplica aos verificadores de `scripts/`: cada
um tem prova negativa, porque *"passou"* só significa alguma coisa quando existe
um caso que reprova.

OS TRÊS EIXOS, E O CONTROLE POSITIVO
-------------------------------------
1. **envelope inválido reprova** — o eixo para o qual a classe existe;
2. **lista vazia reprova** — a vacuidade. Sem isto, uma rota que parasse de
   emitir deixaria a conformidade verde, que é como o B2 da sexta rodada
   sobreviveu: a rota respondia e não gravava;
3. **`esperados` ausente reprova** — a outra direção da vacuidade: um produtor
   que emitisse metade dos tipos continuaria conforme, porque o que ele emitisse
   continuaria válido;
4. **controle positivo** — envelope correto passa. Sem ele, um mixin que
   reprovasse SEMPRE satisfaria os três acima.
"""

from __future__ import annotations

import unittest

from conformidade_de_envelope import ValidacaoDeEnvelope

from contracts.generated.events import AUDIT_QUERY_PERFORMED, EXERCISE_STARTED
from range_core.events.envelope import Correlation, Event


def _evento(**alteracoes) -> Event:
    """Um envelope completo de `09` §1.1, com o que o caso quiser trocar.

    Os valores são os de um evento real de facilitação; `truth_layer` e `persona`
    são o que cada caso move, porque é o par que a condicional de `09` §1.1
    governa.
    """
    campos = {
        "event_id": "01J9F00000000000000000000",
        "event_type": EXERCISE_STARTED,
        "truth_layer": "facilitation",
        "producer": "inject-engine",
        "exercise_time": "T+00:00:00",
        "exercise_timestamp": "2026-08-21T09:00:00",
        "wall_timestamp": "2026-08-21T09:00:00-03:00",
        "clock_multiplier": 1.0,
        "simulation_epoch": 0,
        "correlation": Correlation(),
        "payload": {},
    }
    campos.update(alteracoes)
    return Event(**campos)


def _alvo() -> unittest.TestCase:
    """Uma instância que carrega o mixin, para exercê-lo de fora de uma execução.

    O que se mede aqui é se a asserção **levanta**, e para isso ela precisa ser
    chamada de dentro de outro teste.

    A CLASSE NASCE DENTRO DA FUNÇÃO, e não no módulo: `TestCase` declarado no
    escopo do módulo é COLETADO pelo runner, e uma subclasse sem método `test*`
    entra na suíte pelo `runTest` — um caso que não afirma nada, que é
    exatamente o que a seção *"testes que não provam o requisito"* da auditoria
    cobra. Aqui ela não é atributo do módulo, então o loader não a enxerga.
    """

    class Alvo(ValidacaoDeEnvelope, unittest.TestCase):
        pass

    return Alvo()


class OMecanismoReprova(unittest.TestCase):
    """Os três eixos em que a validação tem de dizer não."""

    def setUp(self) -> None:
        self.alvo = _alvo()

    def test_envelope_de_participant_action_sem_persona_REPROVA(self):
        """O eixo para o qual a classe existe — e é a forma exata do B1.

        `09` §1.1: *"`actor_id` e `persona` são obrigatórios quando `truth_layer`
        for `participant_action` ou `evaluator_assessment`"*.
        """
        sem_persona = _evento(
            event_type=AUDIT_QUERY_PERFORMED,
            truth_layer="participant_action",
            producer="academus-api",
            actor_id="S-1",
        )
        with self.assertRaises(AssertionError) as capturado:
            self.alvo.assertConformeAoContrato([sem_persona])

        self.assertIn("persona", str(capturado.exception))

    def test_lista_vazia_REPROVA(self):
        """A vacuidade. Rota que para de gravar não pode deixar isto verde."""
        with self.assertRaises(AssertionError):
            self.alvo.assertConformeAoContrato([])

    def test_event_type_esperado_e_ausente_REPROVA(self):
        """A outra direção: conforme por emitir menos não é conforme."""
        with self.assertRaises(AssertionError) as capturado:
            self.alvo.assertConformeAoContrato(
                [_evento()], esperados={EXERCISE_STARTED, AUDIT_QUERY_PERFORMED}
            )

        self.assertIn(AUDIT_QUERY_PERFORMED, str(capturado.exception))


class OControlePositivo(unittest.TestCase):
    """Sem isto, um mixin que reprovasse SEMPRE passaria nos três acima."""

    def test_envelope_correto_passa(self):
        _alvo().assertConformeAoContrato(
            [_evento()], esperados={EXERCISE_STARTED}
        )

    def test_participant_action_COM_persona_passa(self):
        """O par do primeiro negativo, sobre o mesmo evento.

        É o que separa *"a validação exige `persona` na camada de pessoa"* de
        *"a validação recusa `audit_query_performed`"*.
        """
        _alvo().assertConformeAoContrato(
            [
                _evento(
                    event_type=AUDIT_QUERY_PERFORMED,
                    truth_layer="participant_action",
                    producer="academus-api",
                    actor_id="S-1",
                    persona="ti",
                )
            ]
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
