"""Projeção `simulation_state` — o fold que o rollback reconstrói.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §4, §4.1 e §4.4; `09_EVENT_MODEL.md` §1.1, §3, §3.1 e §5;
`00_MASTER_SPEC.md` §5.2 e §5.5.

POR QUE A ASSINATURA E ESTA
---------------------------
Esta e UMA das cinco projecoes, e a UNICA que o rollback reconstroi
(`01` §4.1). As outras quatro leem a epoch abandonada legitimamente, cada uma
pelo motivo declarado em `09` §3.1.

Tres propriedades estao codificadas no tipo, e nao na prosa:

1. **A projecao nao consulta o store.** `project` recebe o fluxo. Nao ha
   parametro por onde um store entre, entao "a projecao filtrou no caminho de
   leitura" deixa de ser detectavel e passa a ser inexprimivel.

2. **A exclusao vive AQUI, e em lugar nenhum mais.** Modulo por projecao, sem
   `project` generico compartilhado. Um fold generico faria da heranca proibida
   por `01` §4.1 o caminho de menor esforco — prosa proibindo o que a estrutura
   convida e o defeito latente que aquela secao descreve.

3. **O estado e total.** `SimulationState` traz TODA flag declarada, com o
   default de quem nunca foi escrita. Estado parcial obrigaria cada consumidor a
   mesclar defaults, e obrigacao repetida falha em silencio: com
   `academus.federated_session_active` em `default: true`, ler ausencia como
   `False` inverte a flag, e ausencia e o caso comum.

DESVIO CONSCIENTE, registrado em vez de omitido
-----------------------------------------------
A §1.9 do checkpoint desta fase escreveu `project(events) -> State`, com UM
argumento. Aqui sao dois.

O motivo nao e conveniencia: sob a forma de um argumento, `project` devolveria
escritas de flag e a mescla com os defaults aconteceria fora — e ai existiria
estado que nao passou pelo fold, enquanto `01` §4.1 diz que a exclusao de epoch
vive NO FOLD de `simulation_state`. A garantia cobriria metade do caminho.

Entre a letra da §1.9 e a propriedade da §4.1, prevalece a propriedade — que e o
que a §1.9 existe para proteger.

`Declarations` e categoria, nao par de argumentos avulsos. Com dois avulsos, o
terceiro entra sem discussao; com a categoria declarada, uma entrada que seja
ESTADO nao cabe nela sem alguem notar.

POR QUE `Sequence` E NAO `Iterable`
-----------------------------------
O rollback e retroativo: quando o fold ve `incident_declared` na epoch 0, o
`rollback_performed` que a abandona ainda nao chegou. Ha uma formulacao de uma
passada — historico de escritas por flag, com o corte virando filtro — mas ela
esta AFIRMADA e NAO DEMONSTRADA. `Sequence` ate a demonstracao: afrouxar depois
nao custa nada, apertar depois de haver codigo em cima custa.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from range_core.events.epoch import current_epoch
from range_core.events.envelope import (
    Correlation,
    Event,
    FlagValue,
)

from contracts.generated.events import (
    DECISION_MADE,
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)

# CHAVES DE PAYLOAD que este fold exige. Estao aqui como constantes, e nao como
# literais espalhados, porque viram SCHEMA DE PAYLOAD por `event_type` no mesmo
# PR — e a P2-4 ja abre `contracts/events.schema.yaml` para isso.
#
# Ate la sao contrato de facto: o fold as exige, e quem emitir sem elas encontra
# recusa alta, nunca leitura silenciosa de ausencia.
PACK_ID = "pack_id"
PACK_SCHEMA_VERSION = "pack_schema_version"
PACK_CONTENT_HASH = "pack_content_hash"
PACK_CANONICALIZATION = "pack_canonicalization"

#: Ancora do corte, em `rollback_performed`: `event_id` do ULTIMO evento que
#: sobrevive. Ver o passo 2 de `project` para por que nao e `to_inject_id`.
TO_EVENT_ID = "to_event_id"

#: Opcao escolhida, em `decision_made`. O inject vem de `correlation.inject_id`.
OPTION_ID = "option_id"

@dataclass(frozen=True, slots=True)
class Declarations:
    """As entradas declarativas do fold — tudo o que NAO vem do store.

    Sao declarativas no sentido de `00` §5.2: declaram estado desejado, nunca
    acao imperativa. E o que torna rollback e idempotencia possiveis.

    POR QUE OS EFFECTS SAO RESOLVIDOS, E NAO GRAVADOS
    -------------------------------------------------
    O catalogo de `09` §4.1 e registro FECHADO — **33 tipos**, contados na
    fonte ao escrever esta linha —, e nenhum deles carrega efeito de flag. O fold resolve os effects contra o pack: o fluxo diz
    QUAL inject disparou e QUAL opcao foi escolhida, e o pack diz o que cada um
    declara.

    A alternativa seria um `event_type` de efeito, que exigiria spec-change e
    custaria o principio: um evento gravando flag registra o RESULTADO da
    resolucao, e resultado gravado e o comeco de estado procedural — contra
    `00` §5.2.

    Reconstrucao continua honesta porque `01` §4.1 e `09` §5 exigem projecao
    "reconstruivel DO ZERO", nao "a partir do store". As tres ocorrencias de "a
    partir do store" em `docs/spec/` sao requisito de desempenho (`01` §7,
    `07` Fase 2 item 8) e de reinicio (`07` Fase 4) — e o contraste delas e
    store CONTRA MEMORIA, nao store contra store+pack.

    O PACK E FIXADO PELO STORE, e isso e condicao e nao melhoria
    -----------------------------------------------------------
    O pack e arquivo mutavel; o store nao e. Mesmo store com pack editado
    reconstruiria um mundo diferente, em silencio, e a divergencia apareceria no
    AAR — fases adiante. Por isso `exercise_started` carrega `pack_id`,
    `schema_version` e `content_hash`, e `project` RECUSA reconstruir contra
    pack de hash diferente. O store nao contem o pack; fixa-o.

    Precedente do mecanismo no proprio projeto: T13 usa hash no `MANIFEST.json`
    para detectar edicao manual de artefato gerado.

    DURANTE A EXECUCAO o pack e lido UMA VEZ, no boot, para este valor imutavel.
    Editar o arquivo no meio do exercicio nao e "nao detectado": e SEM EFEITO,
    porque nada o rele. A janela que sobra e o reinicio do engine que a Fase 4
    exige, e ali o pack relido e conferido contra o hash fixado no store.
    """

    pack_id: str
    schema_version: int

    #: SHA-256 da forma canonica do pack, pela regra que `canonicalization`
    #: nomeia.
    content_hash: str

    #: Etiqueta da regra de canonicalizacao — `"v1"` e a primeira. Existe para a
    #: regra poder mudar sem que o mesmo nome passe a significar outra coisa.
    #:
    #: v1: escopo sao os arquivos que o LOADER PARSEIA — se o loader le, pode
    #: mudar a resolucao; se nao le, nao pode. Ficam de fora `evidence/`
    #: (gerado, fora do Git, reconstruido de ground truth + seed), `media/`
    #: (nao parseado) e `GM_NOTES.md` (narrativa; nao alcanca resolucao). Cada
    #: arquivo e PARSEADO e reserializado em JSON determinista — UTF-8, chaves
    #: ordenadas, sem espaco insignificante —, as entradas sao concatenadas em
    #: ordem de caminho POSIX com o caminho como prefixo, e o SHA-256 corre
    #: sobre o resultado. Reserializar em vez de hashear bytes evita recusa por
    #: comentario ou espaco, que seria recusa sem divergencia real.
    canonicalization: str

    #: Toda flag declarada no adapter, com seu default. Vem do contrato do
    #: adapter, carregado no boot. O core NAO importa `domains/` (invariante 1),
    #: e `domains/<adapter>/generated/flags.py` traz so os NOMES, sem defaults —
    #: por isso os defaults chegam como dado, e nao por import.
    flag_defaults: Mapping[str, FlagValue]

    #: `inject_id` -> effects declarados. `04` §5.
    inject_effects: Mapping[str, Mapping[str, FlagValue]]

    #: `(inject_id, option_id)` -> effects da opcao de `decision_point`.
    #: `04` §5. Sem isto, o efeito de uma decisao nao chegaria a projecao
    #: nenhuma: os effects de opcao nao vivem em inject.
    option_effects: Mapping[tuple[str, str], Mapping[str, FlagValue]]


@dataclass(frozen=True, slots=True)
class SimulationState:
    """Estado de simulacao — TOTAL, nunca parcial.

    `flags` traz toda flag de `Declarations.flag_defaults`, escrita ou nao. Nao
    ha `get` com fallback, porque nao ha ausencia.
    """

    flags: Mapping[str, FlagValue]
    simulation_epoch: int


class Site:
    """Os ONZE sitios de recusa de `MalformedStream`, nomeados.

    Existem para o teste poder afirmar QUAL recusa ocorreu, e nao apenas que
    houve recusa. Sem discriminante, um teste que planta ancora fora do fluxo e
    recebe a excecao de ancora ausente passa e nao prova nada — seriam onze
    testes provando a mesma coisa uma vez.

    Discriminante no TIPO, e nao casamento de mensagem: a mensagem e prosa em
    portugues e vai ser reescrita; o codigo nao. Teste acoplado a prosa quebra
    quando a prosa melhora, que ensina a nao melhorar a prosa.
    """

    NO_EXERCISE_STARTED = "no_exercise_started"
    ROLLBACK_EPOCH_MISMATCH = "rollback_epoch_mismatch"
    EVENT_EPOCH_MISMATCH = "event_epoch_mismatch"
    ANCHOR_MISSING = "anchor_missing"
    ANCHOR_UNKNOWN = "anchor_unknown"
    ANCHOR_AFTER_ROLLBACK = "anchor_after_rollback"
    ANCHOR_ABANDONED = "anchor_abandoned"
    INJECT_WITHOUT_ID = "inject_without_id"
    INJECT_NOT_IN_PACK = "inject_not_in_pack"
    DECISION_WITHOUT_OPTION = "decision_without_option"
    DECISION_NOT_IN_PACK = "decision_not_in_pack"


class MalformedStream(Exception):
    """O fluxo nao permite reconstruir estado, e seguir seria pior que parar.

    Ausencia que o fold precisa — `exercise_started` num fluxo nao vazio, ancora
    de corte, id de opcao, inject que o pack nao declara — nao e tratada por
    omissao. Ignorar um rollback deixaria `simulation_state` exibindo um mundo
    que o rollback removeu, sem nada acusando; e um inject sem effects
    resolviveis produziria estado plausivel e errado.

    `site` diz QUAL das onze recusas ocorreu. Ver `Site`.
    """

    def __init__(self, site: str, message: str) -> None:
        super().__init__(f"[{site}] {message}")
        self.site = site


class PackMismatch(Exception):
    """O pack em `Declarations` nao e o que o store fixou.

    Recusa alta e deliberada: reconstruir contra outro pack produziria estado
    plausivel e errado, que e a falha que este pino existe para impedir.

    A mensagem nomeia `pack_id`, hash esperado, hash recebido e a etiqueta de
    canonicalizacao — sem isso a recusa nao e operavel. Ate a Fase 10 o pack
    como era e recuperado do Git pelo hash esperado; dali em diante, de
    armazenamento enderecado por conteudo, para o AAR de exercicio passado abrir
    sem arvore de trabalho.
    """


def project(events: Sequence[Event], declarations: Declarations) -> SimulationState:
    """Reconstroi `simulation_state` do zero, a partir do fluxo e das declaracoes.

    Determinista e pura: sem relogio, sem I/O, sem store. Mesmo par de entradas,
    mesmo resultado — que e o que torna o item 4 da DoD desta fase ("aplicar A01
    duas vezes produz projecao identica") uma propriedade e nao um teste.

    A IDEMPOTENCIA NAO VEM DE GUARDA. Vem de `effects` declarar ESTADO FINAL de
    flag, nunca delta (D3 do checkpoint, §1.7): aplicar A01 duas vezes escreve o
    mesmo valor. Guarda — "ja apliquei este inject, pulo" — exigiria o fold
    lembrar o que aplicou, e essa memoria seria estado fora do fold, que o
    rollback teria de reconstruir tambem.

    O QUE O FOLD FAZ, em ordem — e a ORDEM E A PARTE QUE IMPORTA:

    1. **Confere o pino.** Compara `pack_id`, `schema_version`, `content_hash` e
       a etiqueta de canonicalizacao de todo `exercise_started` do fluxo com
       `declarations`. Divergiu, levanta `PackMismatch`. A conferencia vive AQUI
       porque as duas metades sao argumentos desta funcao — nenhum chamador pode
       pula-la.

    2. **Filtra: marca o que sobrevive aos cortes.** Cada `rollback_performed`
       abandona os eventos ENTRE a sua ancora e ele proprio — inclusive
       `participant_action`. Eles permanecem no store, legiveis e marcados
       (item 6 da DoD), e permanecem ativos nas OUTRAS QUATRO projecoes.

       O CORTE E ANCORADO POR `event_id`, e nao por `to_inject_id`.
       `to_inject_id` e o rotulo legivel que `01` §4.2 exige, e localiza-lo
       exigiria varrer `inject_fired` — dependencia de uma projecao de estado
       num evento de `facilitation` que nada na spec autoriza. Ler
       `rollback_performed` nao cria essa divida: le-lo e ACARRETADO por
       `01` §4.1 mais §4.2.

    3. **Semeia com os defaults.** `declarations.flag_defaults` inteiro, e e
       este passo que torna o estado TOTAL.

    4. **Recomputa: reaplica as escritas sobreviventes**, na ordem do fluxo.

    POR QUE FILTRAR ANTES DE APLICAR, e nao "aplicar e depois excluir"
    -----------------------------------------------------------------
    Aplicar tudo e excluir depois so daria o mesmo resultado se toda escrita
    fosse absoluta e independente do estado anterior. **Ela e** — mas depender
    disso na ORDEM dos passos transformaria uma propriedade do contrato em
    premissa escondida do algoritmo. Filtrando antes, o resultado nao depende
    dela: o que sobrou e reaplicado do zero sobre os defaults, e nao ha nada a
    desfazer.

    E o mesmo motivo pelo qual rollbacks ENCADEADOS compoem sem caso especial —
    rollback dentro de epoch que ja era produto de rollback so marca mais
    posicoes como abandonadas, e a recomputacao nao sabe a diferenca.

    A PREMISSA, dita porque e premissa
    ----------------------------------
    **Todo `effect` e escrita ABSOLUTA de estado final**, nunca relativa. Nao ha
    incremento, alternancia nem derivacao de outra flag.

    Isso e garantido por contrato, e nao suposto: `effects` e objeto cujas
    chaves sao flags declaradas (`x-aurora-ref: adapter_flags`) e cujos valores
    respeitam o tipo declarado da flag (`x-aurora-effects-match-flag-types`) —
    literal do tipo, sem forma de expressao. Normativamente e `00` §5.2:
    "declaram estado desejado, nunca executam acao imperativa".

    Se o contrato um dia admitir effect relativo, ESTE FOLD MUDA: a
    recomputacao continua correta, mas a resolucao de uma escrita passaria a
    depender do estado no momento dela, e o passo 4 deixaria de ser reaplicacao
    de valores para virar reexecucao ordenada.

    Levanta `PackMismatch` se o pino nao bater, e `MalformedStream` se o fluxo
    nao permitir reconstruir.
    """
    _verify_pack_pin(events, declarations)
    _verify_epochs(events)
    surviving = _surviving_writes_mask(events)

    flags: dict[str, FlagValue] = dict(declarations.flag_defaults)
    for index, event in enumerate(events):
        if not surviving[index]:
            continue
        flags.update(_writes_of(event, declarations))

    return SimulationState(
        flags=MappingProxyType(flags),
        simulation_epoch=current_epoch(events),
    )


def _verify_pack_pin(events: Sequence[Event], declarations: Declarations) -> None:
    """Confere o pino do pack contra todo `exercise_started` do fluxo.

    TODO `exercise_started`, e nao "o primeiro", de proposito: `exercise_reset`
    e recomeco (`01` §4.2) e pode produzir um segundo. Conferir todos cobre os
    dois casos sem precisar decidir aqui a semantica do reset.

    Fluxo vazio nao tem o que conferir — exercicio que nao comecou reconstroi
    para os defaults. Fluxo NAO vazio sem `exercise_started` e malformado: sem
    ele o pino nao existe, e reconstruir sem pino e exatamente o silencio que o
    pino existe para impedir.
    """
    if not events:
        return

    pinned = 0
    for event in events:
        if event.event_type != EXERCISE_STARTED:
            continue
        pinned += 1
        payload = event.payload
        atual = (
            payload.get(PACK_ID),
            payload.get(PACK_SCHEMA_VERSION),
            payload.get(PACK_CONTENT_HASH),
            payload.get(PACK_CANONICALIZATION),
        )
        esperado = (
            declarations.pack_id,
            declarations.schema_version,
            declarations.content_hash,
            declarations.canonicalization,
        )
        if atual != esperado:
            raise PackMismatch(
                f"pack fixado pelo store nao e o carregado: "
                f"store={atual!r} carregado={esperado!r} "
                f"(evento {event.event_id}). "
                f"Recupere o pack de hash {atual[2]!r} antes de reconstruir."
            )

    if pinned == 0:
        raise MalformedStream(
            Site.NO_EXERCISE_STARTED,
            f"fluxo com {len(events)} eventos e nenhum {EXERCISE_STARTED}: "
            "sem ele nao ha pino de pack, e reconstruir sem pino produziria "
            "estado plausivel e nao verificavel"
        )


def _surviving_writes_mask(events: Sequence[Event]) -> list[bool]:
    """Marca de quais posicoes as ESCRITAS entram neste fold.

    NAO E VEREDITO DE QUE O EVENTO NAO ACONTECEU, e a distincao nao e verbal.
    O evento permanece no store, legivel e marcado, e permanece ativo nas outras
    quatro projecoes (`01` §4.1, e a D2 do checkpoint). Esta mascara e local a
    `simulation_state` e nao se exporta — exporta-la seria a heranca que
    `01` §4.1 proibe.

    O ALCANCE E POSICIONAL, e o limite disso esta dito
    --------------------------------------------------
    Um `rollback_performed` na posicao `i`, ancorado na posicao `a`, marca
    `a < j < i`. Nada garante que TODO evento nesse intervalo pertenca a linha
    abandonada: um `exercise_paused`, por exemplo, pode ser gravado entre o
    facilitador decidir rebobinar e o rollback ser registrado. `09` §3 desenha o
    intervalo com injects e uma declaracao, e nao diz o que mais cabe nele nem
    proibe nada — entao NAO ha invariante de engine a invocar aqui, e inventar
    um seria normatizar por conveniencia de implementacao.

    O alcance largo e inofensivo NESTE fold, e so nele, por uma razao que vale
    escrever: evento que nao declara escrita nao contribui de um jeito nem de
    outro. `exercise_paused` marcado ou desmarcado produz o mesmo estado. E todo
    evento que DECLARA escrita e esta antes do registro do rollback pertence a
    linha abandonada por construcao — foi gravado antes de ela ser encerrada.

    Se algum dia uma projecao precisar de "este evento foi abandonado" como
    veredito geral, ela nao reusa isto: o criterio dela e outro, e o motivo
    declarado dela em `09` §3.1 tambem.

    Encadeados compoem sem caso especial — marcar de novo o que ja estava
    marcado nao muda nada. O que NAO e aceito e ancorar num evento ja
    abandonado: isso descreveria um corte para dentro de uma linha temporal que
    deixou de existir, e resolver por conta propria seria inventar semantica.
    """
    position_of: dict[str, int] = {}
    for index, event in enumerate(events):
        position_of[event.event_id] = index

    surviving = [True] * len(events)

    for index, event in enumerate(events):
        if event.event_type != ROLLBACK_PERFORMED:
            continue

        anchor_id = event.payload.get(TO_EVENT_ID)
        if not isinstance(anchor_id, str):
            raise MalformedStream(
                Site.ANCHOR_MISSING,
                f"{ROLLBACK_PERFORMED} {event.event_id} sem {TO_EVENT_ID!r} no "
                "payload: o corte nao tem ancora, e ignorar o rollback deixaria "
                "o estado exibindo um mundo que ele removeu"
            )

        anchor = position_of.get(anchor_id)
        if anchor is None:
            raise MalformedStream(
                Site.ANCHOR_UNKNOWN,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "que nao esta no fluxo"
            )
        if anchor > index:
            raise MalformedStream(
                Site.ANCHOR_AFTER_ROLLBACK,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "posterior a ele: rollback so anda para tras"
            )
        if not surviving[anchor]:
            raise MalformedStream(
                Site.ANCHOR_ABANDONED,
                f"{ROLLBACK_PERFORMED} {event.event_id} ancora em {anchor_id!r}, "
                "que ja foi abandonado por rollback anterior"
            )

        for j in range(anchor + 1, index):
            surviving[j] = False

    return surviving


def _writes_of(event: Event, declarations: Declarations) -> Mapping[str, FlagValue]:
    """Resolve as escritas de flag que um evento declara, contra o pack.

    Nenhum `event_type` do catalogo carrega efeito de flag — ver `Declarations`.
    O fluxo diz QUAL inject disparou e QUAL opcao foi escolhida; o pack diz o
    que cada um declara.

    Evento que nao dispara effects resolve para nada, e isso e o caso comum:
    declaracao, observacao e escrituracao do motor nao movem flag.
    """
    if event.event_type == INJECT_FIRED:
        inject_id = event.correlation.inject_id
        if inject_id is None:
            raise MalformedStream(
                Site.INJECT_WITHOUT_ID,
                f"{INJECT_FIRED} {event.event_id} sem inject_id em correlation: "
                "nao ha como resolver os effects dele contra o pack"
            )
        effects = declarations.inject_effects.get(inject_id)
        if effects is None:
            raise MalformedStream(
                Site.INJECT_NOT_IN_PACK,
                f"{INJECT_FIRED} {event.event_id} cita o inject {inject_id!r}, "
                "que o pack fixado nao declara"
            )
        return effects

    if event.event_type == DECISION_MADE:
        inject_id = event.correlation.inject_id
        option_id = event.payload.get(OPTION_ID)
        if inject_id is None or not isinstance(option_id, str):
            raise MalformedStream(
                Site.DECISION_WITHOUT_OPTION,
                f"{DECISION_MADE} {event.event_id} sem inject_id em correlation "
                f"ou sem {OPTION_ID!r} no payload: a opcao escolhida nao e "
                "identificavel, e sem ela os effects dela nao existem"
            )
        effects = declarations.option_effects.get((inject_id, option_id))
        if effects is None:
            raise MalformedStream(
                Site.DECISION_NOT_IN_PACK,
                f"{DECISION_MADE} {event.event_id} cita a opcao "
                f"{(inject_id, option_id)!r}, que o pack fixado nao declara"
            )
        return effects

    return {}


def _verify_epochs(events: Sequence[Event]) -> None:
    """Confere o `simulation_epoch` do envelope contra a contagem de rollbacks.

    POR QUE CONFERIR, JA QUE `current_epoch` CONTA
    -----------------------------------------------
    Contornar a ambiguidade de `01` §4.2 contra `09` §3 foi decisao consciente.
    NAO conferir o campo que a expressa seria outra coisa: o fold leria um
    envelope que discorda dele e seguiria em silencio, que e a classe de falha
    que este modulo inteiro combate.

    O QUE E CONFERIDO, e o que fica de fora de proposito
    ----------------------------------------------------
    A epoch comeca em ZERO (`06` T3, e o piso do contrato) e cada
    `rollback_performed` a incrementa em um. Entao a epoch de um evento e o
    numero de rollbacks gravados ANTES dele.

    A unica excecao e o proprio `rollback_performed`, que aceita as DUAS
    leituras — a epoch que ele encerra ou a que ele abre. E exatamente a
    ambiguidade entre `01` §4.2 ("incrementa") e o diagrama de `09` §3, que o
    desenha dentro da epoch encerrada. Aceitar as duas ali, e so ali, confere
    tudo o mais sem resolver por inferencia o que a spec nao resolveu.
    """
    rollbacks = 0
    for event in events:
        if event.event_type == ROLLBACK_PERFORMED:
            if event.simulation_epoch not in (rollbacks, rollbacks + 1):
                raise MalformedStream(
                    Site.ROLLBACK_EPOCH_MISMATCH,
                    f"{ROLLBACK_PERFORMED} {event.event_id} com "
                    f"simulation_epoch={event.simulation_epoch}: esperado "
                    f"{rollbacks} (epoch encerrada) ou {rollbacks + 1} "
                    "(epoch aberta), pelas duas leituras que a spec admite"
                )
            rollbacks += 1
            continue

        if event.simulation_epoch != rollbacks:
            raise MalformedStream(
                Site.EVENT_EPOCH_MISMATCH,
                f"evento {event.event_id} com "
                f"simulation_epoch={event.simulation_epoch} apos {rollbacks} "
                f"rollback(s): esperado {rollbacks}. O envelope discorda do "
                "fluxo, e seguir escolheria um dos dois em silencio"
            )


# `_current_epoch` saiu daqui: o calculo agora e `range_core.events.epoch`,
# compartilhado com o store, que carimba a mesma epoch no append. Duas
# implementacoes da mesma regra e a classe que a D4 da Fase 1 desfez.
#
# `_verify_epochs` NAO chama o compartilhado, e nao e esquecimento: se chamasse,
# o fold conferiria o numero contra o mesmo codigo que o produziu, e a
# conferencia viraria tautologia. Compartilha-se o calculo; a segunda opiniao
# continua sendo segunda.
