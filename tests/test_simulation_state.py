"""Propriedades do fold `simulation_state`, e as onze recusas.

POR QUE `unittest` E NAO `pytest`
---------------------------------
`pytest` nao esta no `pyproject.toml` nem instalado, e acrescenta-lo e
dependencia nova com fecho transitivo pinado em `constraints.txt` — T15,
"nenhuma dependencia nao pinada". A stdlib faz o que estes testes precisam, e
mantem a disciplina que os verificadores ja tem.

POR QUE AS FLAGS AQUI SAO SINTETICAS
------------------------------------
O fold e do `range-core`, que e agnostico de dominio. Nomear
`academus.enrollment_offline` num teste dele acoplaria o core a um adapter pelo
teste, que e a fronteira do invariante 1 vazando por onde o verificador nao
olha — `tools/check_contract_literals.py` varre `range-core/` e `domains/`, nao
`tests/`.

A primeira versao destes testes usava as flags reais, e o hook de arquitetura a
recusou. Estava certo por um motivo melhor do que o que ele checa.

O caso que motiva a P5 continua sendo real e esta citado: no `academus` ha flag
com `default: true`, e ler ausencia como `False` a inverteria. O teste reproduz
a FORMA — flag de default `True` que nenhum effect toca — sem importar o nome.

O QUE ESTES TESTES PROVAM, E O QUE DELIBERADAMENTE NAO FAZEM
------------------------------------------------------------
As propriedades correm sobre fluxos GERADOS com N rollbacks intercalados, e nao
sobre um caso fixo. Um caso fixo prova que aquele caso passa; a propriedade
prova a afirmacao.

As igualdades sao afirmadas sobre `dict(state.flags)` e `state.simulation_epoch`
EXPLICITAMENTE, e nao pelo `__eq__` gerado do dataclass. Comparar
`SimulationState` inteiro provaria que o dataclass funciona, que nao e o que
esta sob teste.

As onze recusas afirmam o `site`, e nao a mensagem. Sem discriminante, um teste
que planta ancora fora do fluxo e recebe a excecao de ancora ausente passa e nao
prova nada — seriam onze testes provando a mesma coisa uma vez.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from contracts.generated.events import (
    CLASSIFICATION_DECLARED,
    CONTAINMENT_DECLARED,
    DECISION_MADE,
    EXERCISE_PAUSED,
    EXERCISE_STARTED,
    INCIDENT_DECLARED,
    INJECT_FIRED,
    INTEGRITY_VALIDATION_DECLARED,
    ROLLBACK_PERFORMED,
    SEPARATE_INCIDENT_DECLARED,
    SERVICE_RESTORATION_DECLARED,
)
from range_core.events.envelope import Correlation, Event
from range_core.state.simulation_state import (
    OPTION_ID,
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    TO_EVENT_ID,
    Declarations,
    MalformedStream,
    PackMismatch,
    Site,
    project,
)

#: Flag que um effect escreve. Default `False`.
FLAG_WRITTEN = "fixture.written_flag"

#: Flag que NENHUM effect toca, com default `True`. E a forma da flag real de
#: identidade do `academus`, e o que a P5 protege: se o estado deixasse de ser
#: total, ela leria como ausente, e ausencia tratada como `False` inverteria o
#: mundo simulado.
FLAG_UNTOUCHED = "fixture.untouched_flag"

FLAG_DEFAULTS = {FLAG_WRITTEN: False, FLAG_UNTOUCHED: True}

PACK_ID_VALUE = "ransomware-universidade"
SCHEMA_VERSION_VALUE = 2
CONTENT_HASH_VALUE = "sha256:0000"
CANONICALIZATION_VALUE = "v1"


def declarations(**overrides) -> Declarations:
    base = dict(
        pack_id=PACK_ID_VALUE,
        schema_version=SCHEMA_VERSION_VALUE,
        content_hash=CONTENT_HASH_VALUE,
        canonicalization=CANONICALIZATION_VALUE,
        flag_defaults=dict(FLAG_DEFAULTS),
        inject_effects={"A01": {FLAG_WRITTEN: True}},
        option_effects={("A09", "suspend"): {FLAG_WRITTEN: True}},
    )
    base.update(overrides)
    return Declarations(**base)


def event(
    event_id: str,
    event_type: str,
    *,
    epoch: int = 0,
    payload: dict | None = None,
    inject_id: str | None = None,
    truth_layer: str = "facilitation",
) -> Event:
    return Event(
        event_id=event_id,
        event_type=event_type,
        truth_layer=truth_layer,
        producer="inject-engine",
        exercise_time="T+00:00:00",
        exercise_timestamp="2026-08-13T09:00:00",
        wall_timestamp="2026-08-13T09:00:00-03:00",
        clock_multiplier=1.0,
        simulation_epoch=epoch,
        correlation=Correlation(inject_id=inject_id),
        payload=payload or {},
    )


def started(**payload_overrides) -> Event:
    payload = {
        PACK_ID: PACK_ID_VALUE,
        PACK_SCHEMA_VERSION: SCHEMA_VERSION_VALUE,
        PACK_CONTENT_HASH: CONTENT_HASH_VALUE,
        PACK_CANONICALIZATION: CANONICALIZATION_VALUE,
    }
    payload.update(payload_overrides)
    return event("e0", EXERCISE_STARTED, payload=payload)


def stream(rollbacks: int, injects_per_segment: int = 2) -> list[Event]:
    """Fluxo valido com `rollbacks` cortes intercalados.

    Cada segmento dispara injects e termina num `rollback_performed` ancorado no
    rollback ANTERIOR — que sobrevive, porque a faixa abandonada e aberta nos
    dois extremos. Assim os cortes encadeiam sem que nenhum ancore em evento ja
    abandonado, que e recusa propria.

    A epoch de cada evento e o numero de rollbacks gravados antes dele; o
    proprio `rollback_performed` carrega a epoch que ENCERRA, que e a leitura do
    diagrama de `09` §3.
    """
    events = [started()]
    anchor = "e0"
    serial = 1
    for r in range(rollbacks):
        for _ in range(injects_per_segment):
            events.append(event(f"e{serial}", INJECT_FIRED, epoch=r, inject_id="A01"))
            serial += 1
        rollback_id = f"e{serial}"
        serial += 1
        events.append(
            event(rollback_id, ROLLBACK_PERFORMED, epoch=r, payload={TO_EVENT_ID: anchor})
        )
        anchor = rollback_id
    return events


class Propriedades(unittest.TestCase):
    """Fluxos gerados, nao casos fixos."""

    def test_p1_fold_e_determinista(self):
        """Duas execucoes sobre as MESMAS entradas dao o mesmo resultado."""
        for n in range(0, 5):
            with self.subTest(rollbacks=n):
                events, decl = stream(n), declarations()
                primeiro, segundo = project(events, decl), project(events, decl)
                self.assertEqual(dict(primeiro.flags), dict(segundo.flags))
                self.assertEqual(primeiro.simulation_epoch, segundo.simulation_epoch)

    def test_p2_fold_nao_depende_de_identidade_de_objeto(self):
        """`fold(events) == fold(copy(events))`.

        A copia sao INSTANCIAS NOVAS de `Event` com os mesmos valores, e nao a
        mesma lista: copiar a lista provaria apenas que a lista nao e mutada.
        """
        for n in range(0, 5):
            with self.subTest(rollbacks=n):
                events = stream(n)
                copia = [replace(e, payload=dict(e.payload)) for e in events]
                self.assertIsNot(events[0], copia[0])
                original = project(events, declarations())
                clonado = project(copia, declarations())
                self.assertEqual(dict(original.flags), dict(clonado.flags))
                self.assertEqual(original.simulation_epoch, clonado.simulation_epoch)

    def test_p3_reaplicar_o_mesmo_inject_nao_muda_o_estado(self):
        """Item 4 da DoD da Fase 2, como propriedade.

        Vale porque `effects` declara estado FINAL, nunca delta — nao porque o
        fold detecte repeticao. Por isso o teste varia o NUMERO de repeticoes:
        se houvesse guarda de idempotencia, uma contagem alta a exporia.
        """
        uma_vez = project(
            [started(), event("e1", INJECT_FIRED, inject_id="A01")], declarations()
        )
        for repeticoes in (2, 3, 7):
            with self.subTest(repeticoes=repeticoes):
                events = [started()] + [
                    event(f"e{i}", INJECT_FIRED, inject_id="A01")
                    for i in range(1, repeticoes + 1)
                ]
                self.assertEqual(
                    dict(project(events, declarations()).flags), dict(uma_vez.flags)
                )

    def test_p4_epoch_nunca_decresce(self):
        """Sobre PREFIXOS de fluxos gerados, e nao sobre um caso fixo.

        Todo prefixo de um fluxo valido tambem e valido: contem o
        `exercise_started`, e a ancora de um rollback e sempre anterior a ele.
        """
        for n in range(0, 5):
            with self.subTest(rollbacks=n):
                events = stream(n)
                anterior = -1
                for corte in range(1, len(events) + 1):
                    epoch = project(events[:corte], declarations()).simulation_epoch
                    self.assertGreaterEqual(epoch, anterior)
                    anterior = epoch
                self.assertEqual(anterior, n)

    def test_p5_flag_nunca_escrita_permanece_no_default(self):
        """A propriedade central do modulo, e a que impede a regressao cara.

        `FLAG_UNTOUCHED` tem default `True` e nenhum effect a toca. Depois de
        QUALQUER sequencia de rollbacks ela continua `True`.
        """
        for n in range(0, 5):
            for injects in (0, 1, 3):
                with self.subTest(rollbacks=n, injects=injects):
                    state = project(stream(n, injects), declarations())
                    self.assertIn(FLAG_UNTOUCHED, state.flags)
                    self.assertIs(state.flags[FLAG_UNTOUCHED], True)

    def test_p6_pack_divergente_do_pino_e_recusado(self):
        """O pino conferido dentro de `project`, exercido.

        Sem este teste a quarta leitura — effects resolvidos contra o pack em
        vez de gravados — dependeria de uma recusa que ninguem nunca disparou.
        """
        events = stream(2)
        for campo, valor in (
            ("content_hash", "sha256:ffff"),
            ("pack_id", "outro-pack"),
            ("schema_version", 1),
            ("canonicalization", "v2"),
        ):
            with self.subTest(divergente=campo):
                with self.assertRaises(PackMismatch):
                    project(events, declarations(**{campo: valor}))

    def test_rollback_devolve_a_flag_escrita_ao_default(self):
        """Item 5 da DoD: reconstroi sem apagar."""
        events = [
            started(),
            event("e1", INJECT_FIRED, inject_id="A01"),
            event("e2", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        ]
        antes = project(events[:2], declarations())
        depois = project(events, declarations())
        self.assertIs(antes.flags[FLAG_WRITTEN], True)
        self.assertIs(depois.flags[FLAG_WRITTEN], False)
        self.assertEqual(depois.simulation_epoch, 1)
        self.assertEqual(len(events), 3, "o fold nao remove evento do fluxo")

    def test_declaracao_NUNCA_move_flag(self):
        """M1 da terceira auditoria — a consequencia normativa 1 de `00` §3.

        *"Declaracao do participante nunca altera ground truth."* O fluxo abaixo
        traz as SEIS declaracoes que movem metrica, e o estado tem de sair
        identico ao dos defaults.

        NAO E REDUNDANTE com o teste abaixo. Aquele afirma que a declaracao
        SOBREVIVE no fluxo apos rollback; este afirma que ela NAO ESCREVE, e a
        diferenca aparece quando alguem acrescenta um ramo ao `_writes_of`:
        aquele continua verde, este fica vermelho.

        A prova de que ele fica vermelho esta em
        `tests/test_simulation_state_probes.py`, com o ramo plantado.
        """
        declaracoes = [
            CONTAINMENT_DECLARED,
            INCIDENT_DECLARED,
            CLASSIFICATION_DECLARED,
            SERVICE_RESTORATION_DECLARED,
            INTEGRITY_VALIDATION_DECLARED,
            SEPARATE_INCIDENT_DECLARED,
        ]
        events = [started()] + [
            event(f"e{n}", tipo, truth_layer="participant_action")
            for n, tipo in enumerate(declaracoes, start=1)
        ]

        estado = project(events, declarations())
        padrao = project([started()], declarations())

        # A COMPARACAO CONTRA O PADRAO E A UNICA ASSERCAO, e e deliberado. A
        # primeira versao acrescentava `flags[FLAG_WRITTEN] is False`, e com ela
        # este teste passava a acusar TAMBEM a mutacao "estado deixa de ser
        # total" — que e outra propriedade, com teste proprio. O harness
        # reprovou por conjunto divergente, que e o que ele existe para fazer:
        # teste que pega tudo nao localiza nada.
        self.assertEqual(dict(estado.flags), dict(padrao.flags))

    def test_participant_action_abandonada_permanece_no_fluxo(self):
        """D2 do checkpoint, na metade verificavel aqui.

        A acao permanece no fluxo — as outras quatro projecoes a leem — e nao
        move estado nesta.
        """
        events = [
            started(),
            event("e1", INCIDENT_DECLARED, truth_layer="participant_action"),
            event("e2", INJECT_FIRED, inject_id="A01"),
            event("e3", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        ]
        state = project(events, declarations())
        self.assertIs(state.flags[FLAG_WRITTEN], False)
        self.assertIn("e1", [e.event_id for e in events])

    def test_rollback_atravessa_escrita_de_participant_action(self):
        """A metade da §4.4 do `01` que o fold consegue exprimir hoje.

        `decision_made` e `participant_action` (`09` §4.1), e os `effects` da
        opcao escolhida movem flag — "quem muta o estado sao os effects, nao o
        evento". Um rollback que atravessa a decisao devolve a flag ao valor
        anterior, E O EVENTO CONTINUA NO FLUXO: e a §4.4 dizendo que o
        participante pode ver o mundo simulado contradizer a propria acao.

        O QUE ESTE TESTE **NAO** COBRE, e precisa ficar dito
        ---------------------------------------------------
        A §4.4 fala de `participant_action` com `effect_class: state_effect` —
        `vpn_access_revoked` e os outros quatro. `decision_made` e
        `declaration`, nao `state_effect`.

        A classe que a §4.4 nomeia NAO E EXPRIMIVEL neste fold: nenhum
        `event_type` carrega efeito de flag, e nao ha forma declarativa de
        ligar um `event_type` de `participant_action` a uma flag — e a P2-6 do
        registro da fase. Enquanto ela nao for decidida, a §4.4 descreve
        mudanca de estado sem caminho reconstruivel, e este teste cobre a
        propriedade dela apenas na classe `declaration`.
        """
        antes_do_corte = [
            started(),
            event("e1", DECISION_MADE, truth_layer="participant_action",
                  inject_id="A09", payload={OPTION_ID: "suspend"}),
        ]
        com_rollback = antes_do_corte + [
            event("e2", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        ]

        self.assertIs(project(antes_do_corte, declarations()).flags[FLAG_WRITTEN], True)

        depois = project(com_rollback, declarations())
        self.assertIs(depois.flags[FLAG_WRITTEN], False)
        self.assertEqual(depois.simulation_epoch, 1)
        self.assertIn(
            "e1",
            [e.event_id for e in com_rollback],
            "a acao do participante permanece no fluxo: reverte a flag, nao o registro",
        )

    def test_evento_sem_escrita_no_intervalo_abandonado_nao_muda_o_resultado(self):
        """O limite declarado da mascara, exercido.

        A mascara e posicional e alcanca eventos que nao pertencem a linha
        abandonada — um `exercise_paused` gravado entre a decisao e o registro.
        Inofensivo AQUI porque evento sem escrita nao contribui, e este teste
        sustenta a afirmacao em vez de so declara-la.
        """
        com_pausa = [
            started(),
            event("e1", INJECT_FIRED, inject_id="A01"),
            event("e2", EXERCISE_PAUSED),
            event("e3", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        ]
        sem_pausa = [
            started(),
            event("e1", INJECT_FIRED, inject_id="A01"),
            event("e3", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        ]
        self.assertEqual(
            dict(project(com_pausa, declarations()).flags),
            dict(project(sem_pausa, declarations()).flags),
        )


# ---------------------------------------------------------------------------
# AS ONZE RECUSAS.
#
# Tabela em vez de onze metodos escritos a mao, por um motivo que ja custou duas
# contagens erradas nesta fase: com a tabela, "todo sitio tem teste" e uma
# igualdade de conjuntos verificada por maquina, e nao uma contagem minha.
# ---------------------------------------------------------------------------
RECUSAS: dict[str, list[Event]] = {
    Site.NO_EXERCISE_STARTED: [event("e1", INJECT_FIRED, inject_id="A01")],
    Site.ROLLBACK_EPOCH_MISMATCH: [
        started(),
        event("e1", ROLLBACK_PERFORMED, epoch=7, payload={TO_EVENT_ID: "e0"}),
    ],
    Site.EVENT_EPOCH_MISMATCH: [
        started(),
        event("e1", INJECT_FIRED, epoch=3, inject_id="A01"),
    ],
    Site.ANCHOR_MISSING: [started(), event("e1", ROLLBACK_PERFORMED)],
    Site.ANCHOR_UNKNOWN: [
        started(),
        event("e1", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "inexistente"}),
    ],
    Site.ANCHOR_AFTER_ROLLBACK: [
        started(),
        event("e1", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e2"}),
        event("e2", INJECT_FIRED, epoch=1, inject_id="A01"),
    ],
    # O segundo rollback ancora dentro da faixa que o primeiro abandonou.
    #
    # A ancora e `e2`, e nao `e1`, DE PROPOSITO: `e1` fica exatamente sobre o
    # limite inferior do intervalo abandonado, e uma fixture sentada no limite
    # confunde dois defeitos num sinal so. Com `e2`, mover o limite quebra a
    # exclusao sem quebrar esta recusa, e a prova negativa consegue atribuir
    # cada mutacao ao teste que de fato a detecta.
    Site.ANCHOR_ABANDONED: [
        started(),
        event("e1", INJECT_FIRED, inject_id="A01"),
        event("e2", INJECT_FIRED, inject_id="A01"),
        event("e3", ROLLBACK_PERFORMED, payload={TO_EVENT_ID: "e0"}),
        event("e4", ROLLBACK_PERFORMED, epoch=1, payload={TO_EVENT_ID: "e2"}),
    ],
    Site.INJECT_WITHOUT_ID: [started(), event("e1", INJECT_FIRED)],
    Site.INJECT_NOT_IN_PACK: [started(), event("e1", INJECT_FIRED, inject_id="A99")],
    Site.DECISION_WITHOUT_OPTION: [started(), event("e1", DECISION_MADE, inject_id="A09")],
    Site.DECISION_NOT_IN_PACK: [
        started(),
        event("e1", DECISION_MADE, inject_id="A09", payload={OPTION_ID: "inexistente"}),
    ],
}


class Recusas(unittest.TestCase):
    """Uma por sitio, e cada uma afirma O SEU."""

    def test_cada_sitio_recusa_pelo_proprio_motivo(self):
        for site, events in RECUSAS.items():
            with self.subTest(site=site):
                with self.assertRaises(MalformedStream) as capturado:
                    project(events, declarations())
                self.assertEqual(
                    capturado.exception.site,
                    site,
                    "recusou, mas por outro sitio: o caso plantado nao exercita "
                    "o que este teste afirma exercitar",
                )

    def test_todo_sitio_declarado_tem_caso(self):
        """A contagem que me escapou duas vezes, agora verificada por maquina.

        Eu disse "sete sitios", depois "nove", e sao ONZE. Contar a mao foi o
        defeito; esta igualdade e a correcao. Sitio novo no fold sem caso aqui
        fica vermelho.
        """
        declarados = {
            valor
            for nome, valor in vars(Site).items()
            if not nome.startswith("_") and isinstance(valor, str)
        }
        self.assertEqual(declarados, set(RECUSAS))


if __name__ == "__main__":
    unittest.main()
