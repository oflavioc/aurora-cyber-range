"""O predicado de completude da contrassinatura — as quatro condições de `03` §3.4.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3.4, bloco *"A contrassinatura da integridade — o
predicado de completude"*.

POR QUE ELE MORA AQUI, E NÃO NO EMISSOR
----------------------------------------
Ele tem **dois** consumidores, e a spec nomeia os dois:

- a **emissão** recusa a contrassinatura inválida na hora de gravar (§3.4, os três
  negativos de emissão);
- o **computador de `TTID`** aplica o mesmo predicado para escolher qual dos dois
  eventos marca o instante — *"`TTID` marca o evento que completa, e não o
  primeiro. O cálculo é do consumidor sobre o insumo do lado da declaração"*.

Escrito nos dois lugares, seria a classe D4: duas implementações da mesma norma,
divergindo em silêncio. E a divergência aqui é cara de um jeito específico —
apareceria como `TTID` marcado num par que a emissão considerou inválido, ou
ausente num par que ela gravou.

A FORMA É "QUAL CONDIÇÃO FALHOU", E NÃO UM BOOLEANO
----------------------------------------------------
Um `bool` obrigaria o emissor a redescobrir o motivo para escrever a recusa, e
`06` T2 fixa que detecção sem localização não permite intervir. Devolver a
condição violada dá ao emissor a mensagem certa e ao computador o que ele
precisa — que é apenas *"violou alguma?"*.

`actor_id` É CREDENCIAL, E NÃO HUMANO
--------------------------------------
A condição (4) pega **reuso de credencial**, e não dualidade humana. Dualidade é
controle **físico** da facilitação, na distribuição das sete credenciais de
ambiente. O limite fica declarado em vez de parecer garantia — `docs/progress/fase_6.md`.
"""

from __future__ import annotations

from collections.abc import Sequence

from range_core.events.envelope import Event

#: A ordem FIXA de `03` §3.4: Pró-Reitoria declara, TI contrassina. A competência
#: não é simétrica — validar integridade de dado acadêmico é juízo da
#: Pró-Reitoria, e a contrassinatura de TI é a corroboração técnica.
PERSONA_QUE_DECLARA_INTEGRIDADE = "pro_reitoria"
PERSONA_QUE_CONTRASSINA = "ti"

#: AS CONDIÇÕES, pelo número que `03` §3.4 lhes dá. A (2) tem duas metades porque
#: a primeira não cobre a segunda: um operador com duas credenciais satisfaria as
#: personas e assinaria sozinho.
SEM_ANTECEDENTE = "1_sem_antecedente"
ORDEM_INVALIDA = "2a_ordem_invalida"
MESMA_CREDENCIAL = "2b_mesma_credencial"
CADEIA_DE_TRES = "3_antecedente_ja_e_contrassinatura"
JA_COMPLETADO = "4_antecedente_ja_completado"

#: A persona errada ABRINDO o par. Não é uma das quatro condições — elas julgam a
#: contrassinatura —, e sim a outra metade da ordem fixa: TI abrindo declararia
#: integridade de dado acadêmico, que não é competência dela.
ABERTURA_INVALIDA = "0_abertura_por_persona_errada"


def antecedente_de(causation_id: str, anteriores: Sequence[Event]) -> Event | None:
    """A declaração de integridade que `causation_id` aponta, se houver."""
    return next((e for e in anteriores if e.event_id == causation_id), None)


def violacao(
    *,
    persona: str | None,
    actor_id: str | None,
    causation_id: str | None,
    anteriores: Sequence[Event],
) -> str | None:
    """A primeira condição violada, ou `None` se o ato é válido.

    `anteriores` são as `integrity_validation_declared` **anteriores a este ato**,
    em ordem de gravação. Passar o fluxo inteiro faria a condição (4) enxergar
    contrassinaturas futuras, e um par válido viraria inválido pelo que veio
    depois dele.
    """
    if causation_id is None:
        # ABERTURA: o primeiro ato é da Pró-Reitoria, e só dela.
        if persona != PERSONA_QUE_DECLARA_INTEGRIDADE:
            return ABERTURA_INVALIDA
        return None

    antecedente = antecedente_de(causation_id, anteriores)
    if antecedente is None:
        return SEM_ANTECEDENTE

    # (3) antes de (2), e a ordem importa para a mensagem: um antecedente que já
    # é contrassinatura tem persona `ti`, e julgá-lo por (2) diria "ordem
    # inválida" sobre uma cadeia de três — diagnóstico que aponta para o lugar
    # errado.
    if antecedente.correlation.causation_id is not None:
        return CADEIA_DE_TRES

    if (
        antecedente.persona != PERSONA_QUE_DECLARA_INTEGRIDADE
        or persona != PERSONA_QUE_CONTRASSINA
    ):
        return ORDEM_INVALIDA

    if antecedente.actor_id == actor_id:
        return MESMA_CREDENCIAL

    if any(e.correlation.causation_id == causation_id for e in anteriores):
        return JA_COMPLETADO

    return None


def completa(evento: Event, anteriores: Sequence[Event]) -> bool:
    """Este evento é o que COMPLETA a contrassinatura?

    Falso para a declaração isolada, e é a cláusula que `03` §3.4 nomeia como
    negativo: *"declaração isolada não marca `TTID`"*. Ela fica registrada — o
    evento existe no fluxo —, e a ausência de contrassinatura é achado do AAR, e
    não erro de quem declarou.
    """
    if evento.correlation.causation_id is None:
        return False
    return (
        violacao(
            persona=evento.persona,
            actor_id=evento.actor_id,
            causation_id=evento.correlation.causation_id,
            anteriores=anteriores,
        )
        is None
    )
