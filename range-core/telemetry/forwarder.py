"""O telemetry-forwarder: projecao em evento, e replay no clock de exercicio.

AUTORIDADE
----------
`08_EVIDENCE_SIMULATOR.md` §2, `09_EVENT_MODEL.md` §4.1, `01_ARCHITECTURE.md`
§3, e os itens 4 e 6 da DoD da Fase 9.

ITEM 4 — UM CONTRATO SO
========================
`08` §2: *"a telemetria CEF e projecao, nao emissao independente. Isso unifica
evidence-simulator e telemetry-forwarder sob um contrato so."*

`programar` deriva os eventos **dos mesmos fatos** que o `cef.log` — e a
unificacao nao e de estrutura, e de VALOR: o `src` do evento e o `src` da linha
do arquivo porque os dois saem de `source_ip` do mesmo fato. Duas
implementacoes coerentes hoje nao provam nada sobre amanha.

`telemetry_emitted` e `machine` e `metric_side: none` (`09` §4.1 e `00` §3.2):
ele e escrituracao do motor e **nenhum computador de metrica o le**. Isso e o
que permite emiti-lo em volume sem mexer em metrica nenhuma.

ITEM 6 — RESPEITAR O CLOCK SAO TRES PROPRIEDADES
=================================================
1. **so vence o que ja venceu em tempo de EXERCICIO.** O forwarder le
   `elapsed_seconds()`, nunca o relogio de parede;
2. **durante a pausa, nada novo vence** — consequencia da (1), porque `01` §3
   congela o exercise-clock no PAUSAR. Um forwarder preso ao relogio de parede
   continuaria despejando telemetria numa sala parada;
3. **nao reemite.** Duplicata no event store e SINAL para a reconstrucao: ela
   nao sabe distinguir telemetria repetida de telemetria de verdade, e o item 7
   mede reconstrucao sobre esse volume.

O ESTADO DO REPLAY E O CONJUNTO DO QUE JA SAIU, e ele e do objeto e nao do
clock: rebobinar o relogio nao "desemite" nada, porque `09` §3 e explicito —
rollback nao apaga. O que a nova epoch faz e ser outra linhagem, e um replay
novo comeca com o conjunto vazio.

O LIMITE DO AGENDAMENTO, DECLARADO
===================================
`programar` poe todo evento em `em_segundos=0` — telemetria **pre-posicionada**
(`08` §5), ja no SIEM quando o exercicio comeca. Os fatos da Linha A sao do
PASSADO do incidente (`T-17d 02:14`), e converter esse rotulo em segundos de
exercicio e a gramatica temporal que **nao existe** (P6-3).

O mecanismo ja aceita qualquer instante — `Programado.em_segundos` e parametro,
e `Replay` o respeita. O que falta e a conversao, e ela chega com a P6-3.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from range_core.telemetry.catalogo import Catalogo

__all__ = ["Programado", "Replay", "programar", "erros_de_payload"]

#: `campo do fato -> chave CEF`, e sao os de `02` §10.
#:
#: `cnt` recebe `records_affected` porque e o contador do formato; `cs1`-`cs4`
#: ficam FORA deste mapa de proposito: `02` §10 os reserva para contexto do
#: DOMINIO (campus, curso, semestre, disciplina), e o fato nao os tem. Preenche-los
#: com outra coisa seria usar o campo reservado para o que couber.
CAMPO_PARA_CEF = (
    ("source_ip", "src"),
    ("dest", "dst"),
    ("actor", "suser"),
    ("records_affected", "cnt"),
)


@dataclass(frozen=True)
class Programado:
    """Um evento de telemetria pronto, com o instante em que ele vence."""

    fact_id: str
    fact_class: str
    em_segundos: int
    payload: dict


def programar(
    fatos: Sequence[Mapping], *, catalogo: Catalogo
) -> tuple[Programado, ...]:
    """Os eventos de telemetria que estes fatos produzem.

    **Na ordem do documento**, que e a ordem do incidente — a mesma que o motor
    de projecao usa, e pela mesma razao (`projecao.py`: ordenar por
    `exercise_time` exige a gramatica da P6-3).

    Fato cujo `fact_class` o catalogo nao mapeia **nao vira telemetria**, e isso
    e caso normal: `08` §2 poe o limite de deteccao no gabarito.
    """
    programados: list[Programado] = []

    for fato in fatos:
        fact_class = fato.get("fact_class")
        if not isinstance(fact_class, str):
            continue
        entrada = catalogo.entrada_de(fact_class)
        if entrada is None:
            continue

        payload: dict = {
            "signature": entrada.signature,
            "severity": entrada.severity,
        }
        # `event_time` — A PRIMEIRA DAS DUAS MARCAS DE `00` §5.6, e ela e da
        # PROJECAO: quando o fato aconteceu no mundo simulado. A outra,
        # `ingest_time`, e de quem grava, porque so existe no ato de gravar —
        # ver `telemetry/emissao.py`.
        #
        # H1 DA TERCEIRA AUDITORIA. Sem ela, o evento nao carregava o instante
        # que `discoverability.requires` manda correlacionar, e o
        # `additionalProperties: false` do contrato impedia acrescenta-lo.
        instante = fato.get("exercise_time")
        if isinstance(instante, str) and instante:
            payload["event_time"] = instante
        if entrada.outcome:
            payload["outcome"] = entrada.outcome
        for campo, chave in CAMPO_PARA_CEF:
            if campo in fato:
                payload[chave] = fato[campo]

        # `fact_id` NAO entra no payload — `05` §6, e o contrato o torna
        # inexpressavel (`additionalProperties: false`). Ele viaja aqui fora,
        # no `Programado`, para o emissor correlacionar sem publicar.
        programados.append(
            Programado(
                fact_id=str(fato.get("fact_id", "")),
                fact_class=fact_class,
                em_segundos=0,
                payload=payload,
            )
        )

    return tuple(programados)


def erros_de_payload(payload: Mapping, contratos: dict[str, dict]) -> list[str]:
    """Os erros do payload contra `$defs/telemetry_emitted_payload`.

    Lista, e nao excecao, pela mesma razao de `manifesto.erros_de_schema`: quem
    chama decide o que fazer.
    """
    from jsonschema import Draft202012Validator

    from range_core.engine.loader.contract_source import registry_for

    eventos = contratos.get("events") or {}
    if not (eventos.get("$defs") or {}).get("telemetry_emitted_payload"):
        return ["contracts/events.schema.yaml sem `$defs/telemetry_emitted_payload`"]

    # O ALVO E UM `$ref` PARA O `$defs`, E NAO O SUB-SCHEMA SOLTO.
    #
    # Medido: passando o sub-schema direto, o `$ref: '#/$defs/telemetry_signature'`
    # que ha dentro dele resolve contra o PROPRIO sub-schema — `#` e a raiz do
    # documento validador — e `jsonschema` levanta `PointerToNowhere`. O enum das
    # doze assinaturas deixaria de ser conferido, e um payload com assinatura
    # inventada passaria se o erro fosse silenciado em vez de estourar.
    #
    # Com o `$ref` pelo `$id`, o registry resolve os dois niveis no documento
    # inteiro, que e como o loader de pack ja valida os seus.
    alvo = {
        "$ref": f"{eventos['$id']}#/$defs/telemetry_emitted_payload",
    }

    erros = sorted(
        Draft202012Validator(alvo, registry=registry_for(contratos)).iter_errors(payload),
        key=str,
    )
    return [f"{e.json_path}: {e.message}" for e in erros]


@dataclass
class Replay:
    """Emite cada evento programado UMA vez, quando ele vence no exercicio.

    `clock` precisa de `elapsed_seconds()` — e so isso. A dependencia estreita e
    deliberada: o forwarder nao pausa, nao retoma e nao rebobina; ele **le** o
    tempo de exercicio, e quem o move e o gm-console. Um forwarder que soubesse
    pausar teria duas autoridades sobre o mesmo relogio.
    """

    programados: Sequence[Programado]
    clock: object
    emissor: Callable[[dict], object]
    _emitidos: set[int] = field(default_factory=set, init=False, repr=False)

    def tick(self) -> int:
        """Emite os que venceram e ainda nao sairam. Devolve quantos sairam.

        A ORDEM E A DO VENCIMENTO, com a do documento desempatando: o event
        store e append-only e a ordem de chegada e a ordem da timeline do AAR.
        Emitir fora de ordem faria o SIEM do exercicio mostrar a escalada antes
        do acesso inicial.
        """
        decorrido = self.clock.elapsed_seconds()
        saiu = 0

        for indice, programado in sorted(
            enumerate(self.programados), key=lambda par: (par[1].em_segundos, par[0])
        ):
            if indice in self._emitidos or programado.em_segundos > decorrido:
                continue
            self.emissor(programado.payload)
            self._emitidos.add(indice)
            saiu += 1

        return saiu
