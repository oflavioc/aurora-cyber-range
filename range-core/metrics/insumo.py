"""O insumo tipado por lado — onde a partição de `00` §3.2 vira código.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §3.2, blocos *"O insumo — cada computador recebe apenas o seu
lado"* e *"O que a assinatura verifica, e a costura que é fraca"*.

O QUE ESTE MÓDULO É
--------------------
O **único ponto de montagem** dos dois insumos. A norma exige três coisas, e as
três estão aqui:

1. **tipo próprio por lado**, distinto e recusado se resolver para
   `Sequence[Event]` — que não nega nada, porque o fluxo inteiro o satisfaz;
2. **um ponto de montagem por lado**, com o construtor aparecendo só nele;
3. **os escalares do lado no próprio insumo** — o limiar de calibração e a
   defensibilidade chegam ao verificador de `TTIV` por aqui, e não por consulta
   ao pack.

O QUE ESTE MÓDULO **NÃO** FAZ, E É O PONTO
--------------------------------------------
**Não recorta epoch.** A escrituração chega inteira, num campo próprio, aos dois
lados. O desconto por união e a exclusão de `rehearsal` são **cálculo do
consumidor**, e `00` §3.2 diz por quê: recortados aqui, a regra passaria a ser
propriedade do montador, o número certo apareceria por **ausência de insumo** em
vez de por cálculo, e evento perdido por defeito ficaria indistinguível de
evento corretamente descontado.

**Não seleciona start.** Qual inject é *"o primeiro com impacto observável"* é
cálculo do consumidor sobre o payload de `inject_fired`. Montador que já
entregasse "o inject certo" moveria a regra para fora do que o teste alcança.

A LEITURA DO STORE CONTINUA TOTAL
----------------------------------
`01` §4.1 vale sem alteração: o estreitamento acontece **depois** da leitura
total, na montagem, e estreita **um argumento de um consumidor**. O fluxo inteiro
continua existindo e é o que o AAR dobra — ler tudo e então estreitar preserva a
reconstrução; estreitar na leitura, não.

A COSTURA FRACA, DITA — E AINDA SEM O VERIFICADOR
--------------------------------------------------
`NewType` não é barreira de execução: construir o tipo estreito a partir do fluxo
total, fora daqui, compila. O que a norma exige em seu lugar é **checagem de
superfície** sobre onde o construtor aparece — whitelist, não blocklist —, e ela
é mais fraca que *"não tem flag ao alcance"* da D4, porque o veredito chega como
**dado**.

**Ela ainda não existe, e isto está escrito para que a ausência não seja lida
como presença.** Este módulo satisfaz as exigências (1), (2) e (4) de `00` §3.2 —
tipo próprio, o banido fora do insumo, e os lados vindos do `metric_side` com
cobertura e disjunção checadas em `range-core/engine/loader/contract_rules.py`.
A **(3)** é obrigação de verificador, e o verificador é a unidade seguinte da
peça 5. Enquanto ele não existir, *"um único ponto de montagem"* é propriedade
desta árvore por leitura, e não por gate — que é exatamente a distinção que a
§3.2 faz ao chamar a costura de fraca.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NewType

from range_core.events.envelope import Event

#: Os três lados que o catálogo declara em `metric_side` e que produzem insumo.
#: `none` não aparece: nenhum computador de métrica lê aqueles tipos.
LADO_DECLARACAO = "declaration"
LADO_VERIFICACAO = "verification"
LADO_EPOCH = "epoch"

#: OS TIPOS PRÓPRIOS. `Sequence[Event]` não nega nada — o fluxo inteiro o
#: satisfaz —, e uma assinatura que o aceitasse não afirmaria coisa alguma.
EventosDeDeclaracao = NewType("EventosDeDeclaracao", tuple)
EventosDeVerificacao = NewType("EventosDeVerificacao", tuple)
EscrituracaoDeEpoch = NewType("EscrituracaoDeEpoch", tuple)


@dataclass(frozen=True)
class InsumoDeDeclaracao:
    """O que o computador do lado da declaração recebe, e nada além.

    Sem store, sem pack e sem fluxo total: não há por onde buscar mais do que
    lhe foi dado. É a forma do `project` do fold, que não consulta porque não tem
    parâmetro por onde um store entre.
    """

    eventos: EventosDeDeclaracao
    epoch: EscrituracaoDeEpoch


@dataclass(frozen=True)
class InsumoDeVerificacao:
    """O lado da verificação, com os escalares que ele precisa.

    `limiar_de_calibracao` e `defensibilidade` chegam **como dado**, e não por
    consulta ao pack: `00` §3.2 proíbe ter *por onde buscar mais do que lhe foi
    dado*, e não ter o que lhe é necessário. Sem eles, o verificador de `TTIV`
    não teria como marcar o instante em que o conjunto de `assessment_submitted`
    cruza o limiar — que é o que `03` §3.3 define.
    """

    eventos: EventosDeVerificacao
    epoch: EscrituracaoDeEpoch
    limiar_de_calibracao: float
    defensibilidade: Mapping[str, float]


def _por_lado(fluxo: Sequence[Event], lados: Mapping[str, str], lado: str) -> tuple:
    """Os eventos do fluxo cujo `metric_side` declarado é `lado`.

    O recorte resolve contra o **atributo do catálogo**, e não contra
    `effect_class` nem contra prosa: `00` §3.2 mediu que nenhuma das duas classes
    serve de chave, e o mapa é a fonte.

    `event_type` fora do mapa **não** cai num lado por omissão: ele simplesmente
    não entra em insumo nenhum, e a cobertura total do catálogo é verificada em
    `range-core/engine/loader/contract_rules.py`. Um tipo novo sem `metric_side`
    reprova lá, e não vaza para cá.
    """
    return tuple(e for e in fluxo if lados.get(e.event_type) == lado)


def monta(
    fluxo: Sequence[Event],
    lados: Mapping[str, str],
    *,
    limiar_de_calibracao: float,
    defensibilidade: Mapping[str, float],
) -> tuple[InsumoDeDeclaracao, InsumoDeVerificacao]:
    """O ÚNICO ponto de montagem dos dois insumos.

    Um só, e não dois: os dois lados saem do mesmo fluxo e da mesma escrituração
    de epoch, e separá-los em duas funções abriria a possibilidade de montarem
    sobre leituras diferentes do store — que é a divergência silenciosa que o
    predicado meio-revertido já mostrou custar caro na peça 4.

    **A escrituração de epoch vai INTEIRA para os dois**, e não recortada. O que
    cada consumidor faz com ela é cálculo dele.
    """
    epoch = EscrituracaoDeEpoch(_por_lado(fluxo, lados, LADO_EPOCH))
    return (
        InsumoDeDeclaracao(
            eventos=EventosDeDeclaracao(_por_lado(fluxo, lados, LADO_DECLARACAO)),
            epoch=epoch,
        ),
        InsumoDeVerificacao(
            eventos=EventosDeVerificacao(_por_lado(fluxo, lados, LADO_VERIFICACAO)),
            epoch=epoch,
            limiar_de_calibracao=limiar_de_calibracao,
            defensibilidade=dict(defensibilidade),
        ),
    )
