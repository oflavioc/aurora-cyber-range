"""A emissão das nove declarações — e o predicado de completude da contrassinatura.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3.4, incluindo o bloco *"A contrassinatura da integridade
— o predicado de completude"*; `09_EVENT_MODEL.md` §1 e §2.1.

DECLARAÇÃO NÃO É VERDADE, E É POR ISSO QUE ELA SÓ GRAVA EVENTO
----------------------------------------------------------------
`09` §2.1: `containment_declared` registra que a equipe **afirma** ter contido, e
**nunca** altera ground truth. Este módulo não toca estado de simulação, não move
flag e não escreve business state — ele grava evento, e nada mais. Se declaração
alterasse o mundo, declarar cedo melhoraria a métrica mesmo com a contenção
errada, que é o incentivo perverso que `00` §3 existe para impedir.

Não há import de `range_core.state` aqui, e a ausência é o mecanismo: o handler
não tem estado de simulação ao alcance, do mesmo modo que o handler do adapter
não tem flag.

A CONTRASSINATURA — TRÊS RECUSAS DE EMISSÃO
--------------------------------------------
`03` §3.4 nomeia quatro negativos. **Três são de emissão e vivem aqui**:
antecedente ausente, autocontrassinatura, e antecedente já completado.

O quarto — *"declaração isolada não marca `TTID`"* — **não é de emissão**: ela é
gravada, fica registrada, e a ausência de contrassinatura é achado do AAR. Quem
o executa é o computador de métrica, que é a peça 5; está registrado como
cláusula herdada em `docs/progress/fase_6.md`, com endereço.

POR QUE A LEITURA DO FLUXO E NÃO UM ÍNDICE
-------------------------------------------
O predicado precisa saber o que já foi declarado, e a fonte é o próprio store —
leitura total, sem filtro, como `01` §4.1 exige de todo caminho compartilhado.
Um índice paralelo de "declarações pendentes" seria estado fora do event store,
e `00` §5.5 apoia tudo em o registro reconstruir o exercício.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from contracts.generated.events import INTEGRITY_VALIDATION_DECLARED
from range_core.declarations.contrassinatura import (
    ABERTURA_INVALIDA,
    CADEIA_DE_TRES,
    JA_COMPLETADO,
    MESMA_CREDENCIAL,
    ORDEM_INVALIDA,
    PERSONA_QUE_CONTRASSINA,
    PERSONA_QUE_DECLARA_INTEGRIDADE,
    SEM_ANTECEDENTE,
    antecedente_de,
    violacao,
)
from range_core.events.envelope import Correlation, Event
from range_core.events.store import EventDraft, EventStore

#: `09` §2 — o que a equipe faz, vê ou declara.
CAMADA = "participant_action"

#: `09` §1.1 — quem produziu.
PRODUTOR = "participant-api"

#: AS MENSAGENS DE RECUSA, uma por condição de `03` §3.4.
#:
#: O predicado é compartilhado com o computador de `TTID`; o texto é desta
#: superfície, porque é aqui que alguém tem uma requisição na mão e precisa saber
#: o que corrigir. `06` T2 fixa a forma: nomear o quê e o porquê.
RECUSAS = {
    ABERTURA_INVALIDA: lambda persona, _antecedente: (
        f"persona {persona!r} nao abre a validacao de integridade.\n"
        f"    `03` §3.4: {PERSONA_QUE_DECLARA_INTEGRIDADE!r} declara e "
        f"{PERSONA_QUE_CONTRASSINA!r} contrassina, em ordem FIXA. A "
        "competencia nao e simetrica."
    ),
    SEM_ANTECEDENTE: lambda _persona, _antecedente: (
        "contrassinatura sem antecedente: `causation_id` nao aponta para uma "
        "declaracao de integridade anterior.\n"
        "    `causation_id` que nao aponta para uma delas nao grava."
    ),
    CADEIA_DE_TRES: lambda _persona, _antecedente: (
        "o antecedente ja e uma contrassinatura.\n"
        "    O par tem duas maos, e nao tres."
    ),
    ORDEM_INVALIDA: lambda persona, antecedente: (
        f"ordem invalida: {antecedente.persona!r} -> {persona!r}.\n"
        f"    `03` §3.4 fixa {PERSONA_QUE_DECLARA_INTEGRIDADE!r} -> "
        f"{PERSONA_QUE_CONTRASSINA!r}."
    ),
    MESMA_CREDENCIAL: lambda _persona, _antecedente: (
        "autocontrassinatura: a mesma credencial assinou as duas maos.\n"
        "    `actor_id` identifica credencial. Dualidade humana e "
        "controle fisico da facilitacao, na distribuicao das sete."
    ),
    JA_COMPLETADO: lambda _persona, _antecedente: (
        "o antecedente ja foi completado.\n"
        "    O par tem duas maos e um fechamento. Sem esta recusa, duas "
        "contrassinaturas sobre a mesma declaracao satisfariam as quatro "
        "condicoes e o computador de TTID escolheria sozinho qual marca."
    ),
}


class EmissaoRecusada(Exception):
    """A declaração não pode ser gravada. Três causas, todas de `03` §3.4."""


@dataclass(frozen=True)
class Emissor:
    """A porta de emissão da superfície de participante."""

    store: EventStore

    def declarar(
        self,
        event_type: str,
        *,
        persona: str,
        actor_id: str,
        justificativa: str,
        causation_id: str | None = None,
        payload: dict | None = None,
    ) -> Event:
        """Grava a declaração. `03` §3.4: autor, papel, epoch e justificativa livre.

        As marcas temporais e a `simulation_epoch` são carimbadas pelo store, não
        aqui — `EventDraft` não tem campo para elas (D1).

        A justificativa é **obrigatória e livre**: `03` §3.4 a exige de cada uma,
        e é ela que o AAR cita quando o delta entre declaração e verificação vira
        achado. Vazia, a declaração não grava.
        """
        if not justificativa.strip():
            raise EmissaoRecusada(
                "declaracao sem justificativa.\n"
                "    `03` §3.4 exige justificativa livre em cada uma: e ela que o "
                "AAR cita quando o delta vira achado."
            )

        if event_type == INTEGRITY_VALIDATION_DECLARED:
            self._confere_contrassinatura(persona, actor_id, causation_id)

        corpo = dict(payload or {})
        corpo["justificativa"] = justificativa
        return self.store.append(
            EventDraft(
                event_type=event_type,
                truth_layer=CAMADA,
                producer=PRODUTOR,
                correlation=Correlation(causation_id=causation_id),
                actor_id=actor_id,
                persona=persona,
                payload=corpo,
            )
        )

    # -- o predicado de completude, `03` §3.4 -------------------------------

    def _integridades(self) -> Sequence[Event]:
        """Toda `integrity_validation_declared` do fluxo, em ordem de gravação.

        Leitura **total** do store, sem filtro — `01` §4.1. O recorte por tipo é
        aqui, no consumidor, e não numa consulta que outras projeções herdariam.
        """
        return [
            e
            for e in self.store.read_all()
            if e.event_type == INTEGRITY_VALIDATION_DECLARED
        ]

    def _confere_contrassinatura(
        self, persona: str, actor_id: str, causation_id: str | None
    ) -> None:
        """As três recusas de emissão de `03` §3.4.

        O primeiro ato — sem `causation_id` — é da Pró-Reitoria, e só dela: a
        ordem é fixa porque a competência não é simétrica. TI abrindo o par
        declararia integridade de dado acadêmico, que não é competência dela.
        """
        # O PREDICADO É COMPARTILHADO, E AS MENSAGENS SÃO DAQUI.
        #
        # As quatro condições vivem em `range-core/declarations/contrassinatura.py`
        # porque têm DOIS consumidores: esta recusa de emissão e o computador de
        # `TTID`, que `03` §3.4 manda aplicar o mesmo predicado para escolher qual
        # evento marca. Escritas nos dois lugares seriam a classe D4, e a
        # divergência apareceria como `TTID` marcado num par que esta função
        # recusou — ou ausente num par que ela gravou.
        #
        # O que fica aqui é a MENSAGEM, e é o que a separação preserva: `06` T2
        # exige que a recusa nomeie o motivo, e um predicado booleano obrigaria
        # esta função a redescobri-lo.
        anteriores = self._integridades()
        condicao = violacao(
            persona=persona,
            actor_id=actor_id,
            causation_id=causation_id,
            anteriores=anteriores,
        )
        if condicao is None:
            return

        antecedente = (
            antecedente_de(causation_id, anteriores)
            if causation_id is not None
            else None
        )
        raise EmissaoRecusada(RECUSAS[condicao](persona, antecedente))
