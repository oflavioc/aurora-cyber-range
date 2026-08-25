"""O avaliador de predicados de verificação — e a linhagem como lógica dele.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3.1 — *"o motor avalia continuamente e emite
`verification_predicate_satisfied` no instante em que a condição passa a valer"*;
`09_EVENT_MODEL.md` §3.1, parágrafo do avaliador; `01_ARCHITECTURE.md` §4.1.

DUAS CAMADAS, E A SEPARAÇÃO É O PONTO
--------------------------------------
`avalia(no, mundo)` é **puro**: recebe a árvore e o mundo, devolve `bool`. Não
sabe o que é epoch, não lê store e não emite.

`avaliar_e_emitir(...)` **monta o mundo** — e é aí que a consciência de linhagem
vive. `00_MASTER_SPEC.md` §3.2 exige exatamente essa forma para o desconto por
união: *"o número certo aparecendo por ausência de insumo em vez de por cálculo"*
é o defeito, e ele vale igual aqui. Por isso a montagem é lógica escrita e
testada, e não um argumento que chega pronto de algum lugar.

O PREDICADO MEIO-REVERTIDO NÃO EXISTE, E É POR CONSTRUÇÃO
-----------------------------------------------------------
As folhas `event` e as folhas de flag leem **o mesmo mundo**: a linhagem
corrente. Antes de `01` §4.1 generalizar de instância para classe, as primeiras
liam o fluxo cru e as segundas o estado reconstruído — e um rollback deixava o
predicado satisfeito pela metade, com contenção "verificada" por ato que o
facilitador desfez.

Aqui não há como escrever isso: `Mundo` é montado de uma linhagem só, e as duas
famílias de folha o consultam.

A EMISSÃO É POR TRANSIÇÃO, E QUEM DECIDE A SUPRESSÃO NÃO É ESTE MÓDULO
------------------------------------------------------------------------
`09` §3.1: *"a satisfação pertence à epoch em que foi emitida… o avaliador
reavalia sobre a linhagem corrente e, se ela satisfaz, emite na epoch nova"*.

Uma satisfação anterior só suprime a emissão se ela **sustentar a métrica da
epoch corrente**, e essa pergunta tem uma resposta só, em
`range-core/events/veredito.py`, consumida também pelo computador de `TTCV`.

**A versão anterior desta seção dizia "se ela estiver na linhagem corrente", e
era o B1 da nona auditoria escrito por extenso.** Os dois critérios divergem
quando o corte não alcança o veredito: `linhagem.py` abandona só `ancora < j <
indice`, então um rollback ancorado em ou depois do
`verification_predicate_satisfied` o deixava vivo na linhagem e em epoch antiga —
este módulo não reemitia, o computador descartava por epoch, e `TTCV` sumia pelo
resto do exercício sem nada falhar. O mundo continua sendo lido da linhagem; o
que mudou foi a pergunta sobre o veredito, que agora é de epoch e é uma só.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from contracts.generated.events import (
    EXERCISE_STARTED,
    FACT_MATERIALIZED,
    ROLLBACK_PERFORMED,
    VERIFICATION_PREDICATE_SATISFIED,
)
from range_core.events.envelope import Correlation, Event, FlagValue
from range_core.events.epoch import current_epoch
from range_core.events.linhagem import eventos_da_linhagem_corrente
from range_core.events.store import EventDraft, EventStore
from range_core.events.veredito import NOME_DO_PREDICADO, veredito_da_epoch_corrente

#: `09` §4.1 — o veredito é da máquina, sobre o mundo. Nunca `participant_action`.
CAMADA = "ground_truth"

#: `09` §1.1 — quem produziu.
PRODUTOR = "inject-engine"

# `NOME_DO_PREDICADO` é importado, e não redeclarado: ele passou a ter dono único
# em `range-core/events/veredito.py` — B1 da nona auditoria. Sem essa chave, dois
# predicados satisfeitos produziriam eventos indistinguíveis, e `TTCV` e `TTRV`
# leriam o mesmo instante. O nome continua legível daqui porque `test_aar_timeline`
# e `test_laco_de_verificacao` o importam do emissor, que é onde ele é escrito.


#: A CONSTANTE SAIU DAQUI, e a ausência é o conserto — `04` §4.1.
#:
#: Era `SINCE_SELF = "self"`, escrito neste arquivo **e** em
#: `engine/loader/pack_loader.py`. As duas cópias concordavam por coincidência:
#: nenhum import entre elas, nenhum verificador cruzando, e os dois comentários
#: citando a mesma seção como se isso bastasse. Mudar uma e esquecer a outra
#: faria a carga recusar um pack que o avaliador aceitaria, ou o inverso.
#:
#: E ESTA ERA A CÓPIA MAIS PERIGOSA DAS DUAS, não a menos: o docstring de
#: `avalia` declara esta guarda como SEGUNDA LINHA, para *"predicado que veio
#: por outro caminho"*. Copia que só dispara depois de as outras falharem é
#: copia que envelhece sem ninguém olhando.
#:
#: O valor agora chega em `Mundo.since_qualifiers`, derivado de
#: `contracts/ground_truth.schema.yaml` §`$defs/since_qualifier` por
#: `contract_source.since_qualifiers`, lido uma vez na raiz de composição.


class SemGramaticaTemporal(Exception):
    """A pergunta é legítima e a resposta exigiria gramática que não existe.

    **Não é `PredicadoMalformado`**, e a distinção importa: o predicado está bem
    escrito, e é o motor que não sabe situar um fato no tempo. `fact.exercise_time`
    é `'T-17d 02:14'` no exemplo normativo e `minLength: 1` no contrato — não há
    gramática, e o `_T_RELATIVE` do loader (`HH:MM`) não representa dia negativo.

    **Recusa alta, pelo mesmo argumento das folhas `before`/`after`:** as duas
    respostas plausíveis são piores que recusar. Falso faria a contenção nunca
    verificar sem explicação; verdadeiro a faria verificar com vazamento em
    curso. A pendência é a **P6-3**, que passou a cobrir as três folhas: uma
    gramática de `exercise_time` decide `since`, `before` e `after` de uma vez, e
    duas gramáticas divergentes para o mesmo campo seriam pior que nenhuma.

    **Ela é inalcançável na árvore de hoje, e isso é medido, não suposto:** nada
    emite `fact_materialized` — o tipo é lido aqui e a única escrita no
    repositório é à mão, num teste. Quem escrever o produtor bate nela na
    primeira execução, que é onde a decisão da gramática precisa acontecer.
    """


@dataclass(frozen=True)
class InstanteDeReferencia:
    """O instante a partir do qual `since: self` exige ausência — `03` §3.1.

    Carrega os três relógios do envelope, e não um só, porque **qual deles a
    comparação usa é a decisão normativa da P6-3** — `exercise_time`,
    `exercise_timestamp` ou marca de parede dão resultados diferentes depois de
    um rollback. Guardar um só aqui seria tomar a decisão por omissão.

    `origem` diz QUAL evento o fixou. Sem ele, "epoch 0" e "depois do corte"
    ficam indistinguíveis na mensagem de recusa, e é justamente essa distinção
    que a §3.1 normatiza.
    """

    event_id: str
    exercise_time: str
    exercise_timestamp: str
    simulation_epoch: int
    origem: str


def instante_de_referencia(
    correntes: Sequence[Event],
) -> InstanteDeReferencia | None:
    """Onde a avaliação passou a acontecer NA LINHAGEM CORRENTE — `03` §3.1.

    Recebe os eventos **já filtrados pela linhagem**, como `mundo_corrente`, e
    pelo mesmo motivo: a filtragem é passo anterior e explícito em
    `avaliar_e_emitir`, para que ela seja legível como cálculo e não como recorte
    de quem monta. Filtrar de novo aqui seria a segunda reconstrução que o
    docstring de `avaliar_e_emitir` proíbe.

    **O `rollback_performed` corrente vence o `exercise_started`**, e é a norma:
    *"depois de um rollback, o instante de referência é o da reavaliação na epoch
    nova"*. Um `since: self` congelado no primeiro instante de avaliação
    sobreviveria ao corte, e o predicado meio-revertido voltaria por esta porta.
    O corte abandonado não aparece — ele não está na linhagem.

    Devolve `None` antes do `exercise_started`: não há "a partir de quando", e
    inventar um faria `since: self` responder sobre um exercício que não começou.
    """
    for evento in reversed(list(correntes)):
        if evento.event_type == ROLLBACK_PERFORMED:
            return _referencia(evento)
    for evento in correntes:
        if evento.event_type == EXERCISE_STARTED:
            return _referencia(evento)
    return None


def _referencia(evento: Event) -> InstanteDeReferencia:
    return InstanteDeReferencia(
        event_id=evento.event_id,
        exercise_time=evento.exercise_time,
        exercise_timestamp=evento.exercise_timestamp,
        simulation_epoch=evento.simulation_epoch,
        origem=evento.event_type,
    )


class PredicadoMalformado(Exception):
    """Nó que não é nenhuma das nove formas de `ground_truth.schema.yaml`.

    Recusa **alta**: o contrato já garante a forma, então chegar aqui significa
    que o pack passou por outro caminho. Avaliar um nó desconhecido como falso
    seria pior que recusar — a contenção nunca verificaria, e ninguém saberia por
    quê.
    """


@dataclass(frozen=True)
class Mundo:
    """O mundo corrente, montado de UMA linhagem.

    `tipos` e `fatos` vêm dos eventos sobreviventes; `flags`, do fold sobre os
    mesmos eventos. É a unidade que torna o predicado meio-revertido
    inexprimível.
    """

    tipos: frozenset[str]
    fatos: frozenset[str]
    flags: Mapping[str, FlagValue]
    referencia: InstanteDeReferencia | None = None
    #: OS QUALIFICADORES DE `since`, VINDOS DO CONTRATO — `04` §4.1.
    #:
    #: Chega como DADO, e não como constante deste módulo. Até aqui era
    #: `SINCE_SELF = "self"` escrito neste arquivo **e** em
    #: `engine/loader/pack_loader.py`, sem import entre os dois: as duas cópias
    #: concordavam por coincidência, e mudar uma sem a outra faria carga e
    #: avaliação discordarem sobre o mesmo campo. A origem única é
    #: `contract_source.since_qualifiers`, lida uma vez na raiz de composição.
    #:
    #: `kw_only` porque ele é OBRIGATÓRIO e entra depois de um campo com
    #: default. Sem isso a única saída seria dar-lhe um default — e default aqui
    #: seria a segunda origem voltando pela porta dos fundos.
    since_qualifiers: frozenset[str] = field(kw_only=True)


def avalia(no: Mapping, mundo: Mundo) -> bool:
    """A árvore de `ground_truth.schema.yaml` §predicate, sobre um mundo dado.

    **Puro.** Quem decide o que é o mundo é o chamador — e essa foi a decisão do
    `spec-change` `linhagem-corrente-e-o-avaliador`.

    `before` e `after` não são avaliados aqui e **não são silenciosamente
    falsos**: eles comparam contra o relógio de exercício, que não é parte do
    mundo desta função. Chegam como `PredicadoMalformado` até existir consumidor
    que os traga — recusa alta é o que impede um predicado temporal de passar por
    "não satisfeito" e a contenção nunca verificar sem explicação.

    `absence_of.since` É LIDO, e as três saídas são explícitas
    ---------------------------------------------------------
    Era o H1 da quarta auditoria: o campo estava no contrato, no exemplo
    normativo de `03` §3.1, e **sumia aqui** — `alvo["fact_class"]` descartava o
    resto do nó. A ausência passava a valer sobre a linhagem inteira, e o
    predicado que a própria spec escreve ficava insatisfazível no pack que ela
    ilustra: nada falhava, a métrica só deixava de marcar.

    | Forma | O que acontece |
    |---|---|
    | sem `since` | ausência TOTAL, e continua legítima (`03` §3.1) |
    | `since: self`, classe fora do mundo | **satisfaz** — é o caso normativo |
    | `since: self`, classe no mundo | `SemGramaticaTemporal` — ver a exceção |
    | outro valor | `PredicadoMalformado` — a guarda de carga é a primeira linha |
    """
    if "all" in no:
        return all(avalia(filho, mundo) for filho in no["all"])
    if "any" in no:
        return any(avalia(filho, mundo) for filho in no["any"])
    if "not" in no:
        return not avalia(no["not"], mundo)
    if "event" in no:
        return no["event"] in mundo.tipos
    if "flag_true" in no:
        return bool(mundo.flags.get(no["flag_true"]))
    if "flag_false" in no:
        return not bool(mundo.flags.get(no["flag_false"]))
    if "absence_of" in no:
        alvo = no["absence_of"]
        if isinstance(alvo, str):
            # Forma curta: nomeia só a classe, e não carrega qualificador.
            # Ausência TOTAL, legítima fora da contenção (`03` §3.1).
            return alvo not in mundo.fatos
        classe = alvo["fact_class"]
        since = alvo.get("since")
        if since is None:
            return classe not in mundo.fatos
        if since not in mundo.since_qualifiers:
            raise PredicadoMalformado(
                f"`absence_of.since` com valor nao definido: {since!r}.\n"
                f"    O contrato declara {sorted(mundo.since_qualifiers)!r} em "
                "`ground_truth.schema.yaml` §`$defs/since_qualifier`, e `03` §3.1 "
                "e quem os define. A guarda de carga recusa este pack antes do "
                "boot; chegar aqui significa que o predicado veio por outro "
                "caminho, e avaliar um qualificador que ninguem definiu seria "
                "inventar semantica."
            )
        if mundo.referencia is None:
            raise SemGramaticaTemporal(
                f"`absence_of` com `since: {since}` sem instante de "
                "referencia: nao ha `exercise_started` na linhagem corrente.\n"
                "    A ausencia e exigida A PARTIR do instante em que o predicado "
                "passou a ser avaliado, e antes do inicio esse instante nao "
                "existe. Responder aqui seria afirmar sobre um exercicio que nao "
                "comecou."
            )
        if classe in mundo.fatos:
            raise SemGramaticaTemporal(
                f"`absence_of` com `since: {since}` sobre a classe "
                f"{classe!r}, que ESTA na linhagem corrente.\n"
                f"    Instante de referencia: evento {mundo.referencia.event_id} "
                f"({mundo.referencia.origem}), `exercise_time` "
                f"{mundo.referencia.exercise_time!r}, epoch "
                f"{mundo.referencia.simulation_epoch}.\n"
                "    Situar o fato em relacao a ele exige comparar contra "
                "`fact.exercise_time`, que hoje e string sem gramatica "
                "(`ground_truth.schema.yaml`: `minLength: 1`; o exemplo "
                "normativo traz `'T-17d 02:14'`). Recusa alta: responder FALSO "
                "faria a contencao nunca verificar, e VERDADEIRO a faria "
                "verificar com vazamento em curso. Pendencia P6-3 em "
                "`docs/progress/fase_6.md` — a mesma das folhas `before` e "
                "`after`, e uma gramatica so decide as tres."
            )
        return True
    raise PredicadoMalformado(
        f"no de predicado nao reconhecido: {sorted(no)}.\n"
        "    As nove formas estao em `contracts/ground_truth.schema.yaml`. "
        "`before` e `after` comparam contra o relogio de exercicio, que nao e "
        "parte do mundo desta funcao, e por isso recusam alto em vez de "
        "devolverem falso — falso silencioso faria a contencao nunca verificar."
    )


def mundo_corrente(
    eventos: Sequence[Event],
    flags: Mapping[str, FlagValue],
    *,
    since_qualifiers: frozenset[str],
) -> Mundo:
    """Monta o mundo a partir dos eventos **já filtrados pela linhagem**.

    Recebe os eventos correntes, e não o fluxo total: a filtragem é passo
    anterior e explícito em `avaliar_e_emitir`, para que ela seja legível como
    cálculo e não como recorte de quem monta.

    `since_qualifiers` ATRAVESSA, e não é lido aqui: `04` §4.1 põe a leitura do
    contrato na raiz de composição, e este módulo é caminho quente — ele roda a
    cada gravação.
    """
    fatos = {
        str(e.payload.get("fact_class"))
        for e in eventos
        if e.event_type == FACT_MATERIALIZED and e.payload.get("fact_class")
    }
    return Mundo(
        tipos=frozenset(e.event_type for e in eventos),
        fatos=frozenset(fatos),
        flags=MappingProxyType(dict(flags)),
        referencia=instante_de_referencia(eventos),
        since_qualifiers=since_qualifiers,
    )


def avaliar_e_emitir(
    store: EventStore,
    predicados: Mapping[str, Mapping],
    flags: Mapping[str, FlagValue],
    *,
    since_qualifiers: frozenset[str],
) -> list[Event]:
    """Avalia os predicados do pack sobre a linhagem corrente, e emite as transições.

    Devolve os eventos emitidos — vazio quando nada passou a valer, que é o caso
    comum de uma avaliação contínua.

    A leitura do store é **total** (`01` §4.1), e o estreitamento acontece aqui,
    depois dela: `eventos_da_linhagem_corrente` é a definição única, a mesma que
    o fold consome.

    `flags` chega como **dado**, do fold, e não é recalculado aqui — duas
    reconstruções do mesmo estado divergiriam, e a divergência apareceria como
    predicado meio-revertido, que é o que este módulo existe para tornar
    impossível.
    """
    fluxo = store.read_all()
    correntes = eventos_da_linhagem_corrente(fluxo)
    mundo = mundo_corrente(correntes, flags, since_qualifiers=since_qualifiers)
    corrente = current_epoch(fluxo)

    emitidos: list[Event] = []
    for nome, arvore in sorted(predicados.items()):
        if not isinstance(arvore, Mapping):
            # `service_restoration` admite `{not_applicable: "motivo"}` — D5 da
            # Fase 1. Não é predicado, e não se avalia: AAR imprime "TTRV nao
            # aplicavel" em vez de nulo ou de um zero que parece medição.
            continue
        if "not_applicable" in arvore:
            continue
        if not avalia(arvore, mundo):
            continue
        if veredito_da_epoch_corrente(correntes, nome, corrente) is not None:
            continue
        emitidos.append(
            store.append(
                EventDraft(
                    event_type=VERIFICATION_PREDICATE_SATISFIED,
                    truth_layer=CAMADA,
                    producer=PRODUTOR,
                    correlation=Correlation(),
                    payload={NOME_DO_PREDICADO: nome},
                )
            )
        )
    return emitidos


# ---------------------------------------------------------------------------
# O LAÇO CONTÍNUO — `03` §3.1, *"o motor avalia continuamente"*.
#
# A peça 4 entregou o avaliador e declarou a fronteira: quem o chama a cada
# evento é a peça 5, porque **é o consumidor que decide a cadência**, e os
# computadores de métrica são o consumidor.
#
# POR QUE É UM OBJETO, E NÃO UMA CHAMADA DENTRO DO ENGINE
# --------------------------------------------------------
# As folhas de `containment` no exemplo normativo de `03` §3.1 são
# `vpn_access_revoked` e `identity_scope_disabled` — **ações com efeito no mundo
# simulado**, que `03` §3.1 separa por nome das afirmações sobre ele.
#
# MEDIDO NA ÁRVORE: nada as emite ainda. A superfície das três ações de `01` §4.4
# é de outra fase, e o `Emissor` das nove declarações não pode movê-las — por
# `09` §4.0, folha de predicado exige `state_effect` **e**
# `metric_side: verification`, e nenhuma das nove satisfaz a conjunção.
#
# Então hoje o único chamador é o engine. O laço é objeto, e não um método
# privado dele, para que a superfície que vier receba **este mesmo** objeto: dois
# laços leriam o mesmo store e dariam a mesma resposta, mas nada garantiria que
# carregam o mesmo pack.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LacoDeVerificacao:
    """Avalia os predicados do pack sobre a linhagem corrente, a cada gravação.

    `flags` NÃO é parâmetro: ele é derivado do fold aqui dentro, a cada chamada.
    Isso não contradiz o docstring de `avaliar_e_emitir` — o que aquele proíbe é
    o avaliador RECALCULAR o estado por conta própria; aqui o estado vem do
    `project`, que é o fold, e é a mesma reconstrução que toda projeção usa.

    Recebê-lo pronto seria pior: o chamador teria de lembrar de reconstruí-lo
    depois de gravar, e um chamador distraído avaliaria o mundo de antes do
    próprio evento que acabou de emitir.
    """

    store: EventStore
    predicados: Mapping[str, Mapping]
    declarations: object
    #: Do contrato, por `contract_source.since_qualifiers`, lido UMA vez na raiz
    #: de composição — `04` §4.1. É este campo que faz a guarda do avaliador
    #: deixar de ter literal próprio e passar a concordar com a de carga por
    #: construção, e não por lembrança.
    since_qualifiers: frozenset[str]

    def avaliar(self) -> list[Event]:
        """Devolve os vereditos emitidos — vazio no caso comum.

        Sem predicado, não há o que avaliar, e a saída antecipada evita um fold
        por gravação num pack que não os declara. Pack real sempre os tem —
        `ground_truth.schema.yaml` os exige —, mas o engine é montado em teste e
        em demo com packs mínimos.
        """
        if not self.predicados:
            return []
        from range_core.state.simulation_state import project

        flags = project(self.store.read_all(), self.declarations).flags
        return avaliar_e_emitir(
            self.store,
            self.predicados,
            flags,
            since_qualifiers=self.since_qualifiers,
        )
