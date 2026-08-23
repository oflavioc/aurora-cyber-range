"""A conformidade do envelope contra o contrato — o mecanismo, para os TRÊS.

M1 DA SÉTIMA AUDITORIA DA FASE 6
---------------------------------
O achado foi de ESCOPO, e não de defeito: `ConformeAoContrato` provava o que
dizia, e a docstring dela afirmava ser *"a única camada que impede o engine de
emitir um envelope que o contrato recusa"* — verdadeira sobre o engine, e o
commit da fase acrescentou **dois produtores** sem estendê-la.

Medido no commit auditado: `grep -rn "iter_errors" tests/*.py` devolvia três
linhas, todas em `tests/test_inject_engine.py`. O evento do adapter e as nove
declarações da `participant-api` nunca eram validados contra
`contracts/events.schema.yaml`.

**É a ausência que deixou o B1 passar por seis rodadas.** `audit_query_performed`
é `participant_action` (`09` §4.1), a camada em que o contrato exige `persona`
(`09` §1.1 e `contracts/events.schema.yaml`), e o emissor do adapter não a
escreve. Nada na árvore perguntava.

POR QUE UM MÓDULO, E NÃO A CLASSE COPIADA TRÊS VEZES
-----------------------------------------------------
Copiada, ela é a classe D4 com outro nome: três validadores sobre o mesmo
contrato divergem, e o que diverge em silêncio é sempre o que ninguém está
olhando. Pior no caso concreto — o produtor NOVO é justamente o que nasceria com
a cópia velha, e o defeito que ela não vê é o defeito que ele tem.

Aqui há uma função que constrói o documento e um mixin que afirma sobre ele. Um
produtor novo herda o mixin; não há o que reescrever, e é isso que faz o custo de
estender ser menor que o de esquecer.

O QUE O MIXIN RECUSA ALÉM DO ENVELOPE INVÁLIDO
-----------------------------------------------
**Lista vazia REPROVA.** Uma suíte que valide zero evento fica verde afirmando
nada, e é a forma de falha que este projeto já pagou — a rota que respondia sem
gravar (B2 da sexta rodada) deixaria esta validação passar por vacuidade.

`esperados` fecha a outra direção: o conjunto de `event_type` que TEM de aparecer.
Sem ele, um produtor que parasse de emitir metade dos tipos continuaria conforme,
porque tudo o que ele emitisse continuaria válido.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator

from range_core.engine.loader import contract_source

#: Os contratos, lidos uma vez. Mesma fonte que o loader usa no boot — validar
#: contra uma cópia escrita à mão aqui mediria a cópia.
CONTRATOS = contract_source.read_contracts()


def validador() -> Draft202012Validator:
    """O validador do envelope, com o registry que resolve os `$ref`.

    O `registry_for` é o que faz `$ref` de payload atravessar para os outros
    contratos — sem ele, `assessment_submitted` validaria só o envelope e o
    payload passaria sem ser olhado.
    """
    return Draft202012Validator(
        CONTRATOS["events"], registry=contract_source.registry_for(CONTRATOS)
    )


def envelope(evento) -> dict:
    """O evento na forma de documento, como o contrato o descreve.

    Campos opcionais ausentes são OMITIDOS, e não enviados como `null`: o
    contrato tipa `actor_id` como string, e `None` seria recusado por um motivo
    que não tem nada a ver com o que se quer provar.

    **A omissão não esconde o B1**, e é a diferença que importa: `09` §1.1 torna
    `persona` OBRIGATÓRIO na camada de pessoa, então omiti-lo faz o contrato
    recusar por `required` — que é exatamente o defeito. O que a omissão evita é
    a recusa por TIPO, que apareceria também em evento correto de outra camada.
    """
    documento = {
        "event_id": evento.event_id,
        "event_type": evento.event_type,
        "truth_layer": evento.truth_layer,
        "producer": evento.producer,
        "exercise_time": evento.exercise_time,
        "exercise_timestamp": evento.exercise_timestamp,
        "wall_timestamp": evento.wall_timestamp,
        "clock_multiplier": evento.clock_multiplier,
        "simulation_epoch": evento.simulation_epoch,
        "correlation": {
            chave: valor
            for chave, valor in {
                "scenario_id": evento.correlation.scenario_id,
                "inject_id": evento.correlation.inject_id,
                "causation_id": evento.correlation.causation_id,
                "fact_id": evento.correlation.fact_id,
            }.items()
            if valor is not None
        },
        "payload": dict(evento.payload),
    }
    if evento.actor_id is not None:
        documento["actor_id"] = evento.actor_id
    if evento.persona is not None:
        documento["persona"] = evento.persona
    return documento


class ValidacaoDeEnvelope:
    """Mixin de `TestCase`. **O store não valida — decisão dele.**

    Sem esta camada, um produtor pode emitir por anos um envelope que o contrato
    recusa, e o primeiro a descobrir é o consumidor de outra fase — com o store
    append-only e o exercício já gravado.

    Herdar isto é o que um produtor novo precisa fazer. É de propósito que não há
    varredura automática de produtores: uma que descobrisse emissores sozinha
    passaria por vacuidade no dia em que a heurística deixasse de reconhecer o
    próximo — e o produtor invisível seria o não validado.
    """

    def assertConformeAoContrato(self, eventos, *, esperados=None) -> None:
        """Cada evento valida, a lista não é vazia, e os `esperados` apareceram.

        `esperados` é conjunto de `event_type`. Quando dado, exige que TODOS
        estejam presentes — a direção que impede um produtor de ficar conforme
        por emitir menos.
        """
        eventos = list(eventos)
        self.assertTrue(
            eventos,
            "nenhum evento para validar: a conformidade passaria por vacuidade, "
            "que e a forma de falha que este mixin existe para nao ter.",
        )

        if esperados is not None:
            faltando = sorted(set(esperados) - {e.event_type for e in eventos})
            self.assertEqual(
                faltando,
                [],
                f"`event_type` esperado e nao emitido: {faltando}. Validar so o "
                "que foi emitido deixa um produtor conforme por emitir menos.",
            )

        alvo = validador()
        for evento in eventos:
            with self.subTest(event_type=evento.event_type):
                erros = sorted(alvo.iter_errors(envelope(evento)), key=str)
                self.assertEqual(
                    erros,
                    [],
                    f"{evento.event_type} ({evento.producer}): "
                    f"{erros[0].message if erros else ''}",
                )
