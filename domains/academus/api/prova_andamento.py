"""Modo "Prova em andamento" — a queda de sessao por MINUTO de exercicio.

A CADENCIA QUE A P4-6 DEIXOU SEM DONO, FECHADA AQUI
----------------------------------------------------
`degradacao.py:72-77` registrou a divergencia: `fracao_do_sujeito`/`cai` derrubam
quem cai o exercicio INTEIRO, de uma vez — o `effect_ui` da flag
`academus.lms_session_drop_rate` termina em *"por minuto"*, que aquela funcao nao
implementa, porque implementar a cadencia exige TEMPO DE EXERCICIO como entrada, o
estado que a P3-10 tirou de `degradacao.py` de proposito. O consumidor que da
sentido a cadencia e o Modo "Prova em andamento" de `07` Fase 8, e ele mora aqui.

Este modulo NAO DUPLICA A DERIVACAO. A posicao fixa de cada sessao continua sendo
`fracao_do_sujeito` (existente, testada, determinista por `derive_seed` — nunca
`hash()`, que muda entre processos). A cadencia so move, ao longo do tempo, o
CORTE que decide onde a fila de sessoes e cortada — e por isso as propriedades da
D9 sobrevivem e uma nova se soma:

    sem estado            funcao pura de (seed, rota, flag, sujeitos, taxa, minuto)
    estavel no reinicio   `derive_seed` (SHA-256), o mesmo conjunto a cada boot
    estavel no rollback   a taxa volta, e EXATAMENTE as mesmas sessoes voltam
    monotona na taxa      subir a taxa so acrescenta; nunca troca o conjunto
    monotona no tempo      o corte cresce com o minuto => o conjunto so acrescenta

O MODELO DE SOBREVIVENCIA CUMULATIVO
-------------------------------------
`taxa` e a fracao de sessoes AINDA VIVAS que cai a cada minuto de exercicio.
Cumulativamente, a fracao derrubada ate o minuto `m` e

    corte(taxa, m) = 1 - (1 - taxa) ** m       para 0 < taxa < 1, m >= 1

com os limites `corte = 0` no minuto 0 (o exercicio comeca sem ninguem fora do
ar) e `corte = 1` a partir do minuto 1 quando `taxa = 1` (apagao total). Uma
sessao esta derrubada no minuto `m` sse a sua posicao fixa cai abaixo do corte:

    fracao_do_sujeito(seed, rota, flag, sujeito) < corte(taxa, m)

A monotonia no tempo cai por construcao: o corte cresce com `m`, e o corte e um
`<` sobre uma posicao FIXA — nada move uma sessao de dentro para fora quando o
minuto avanca, entao quem caiu nao ressuscita. E a diferenca que a sala LE: uma
implementacao que re-sorteasse a cada minuto daria a fracao certa e trocaria quem
esta fora do ar, e o painel piorando com participantes voltando se leria como
recuperacao espontanea.

O FRAME E ESTADO TOTAL — INV-7
-------------------------------
`frame` descreve TODAS as sessoes, cada uma `alive` ou `dropped`, e nunca um
delta do que caiu neste minuto. O servidor deriva; o cliente pinta o payload. Os
`dropped` do frame sao, por construcao, exatamente `derrubadas(...)`.
"""

from __future__ import annotations

from collections.abc import Iterable

from domains.academus.api.degradacao import fracao_do_sujeito

#: O vocabulario FECHADO do frame. Duas palavras e nada mais: valor fora delas
#: seria estado que a tela nao sabe pintar, pelo mesmo motivo que o catalogo de
#: `event_type` e fechado.
ALIVE = "alive"
DROPPED = "dropped"


def corte_cumulativo(taxa: float, minuto: int) -> float:
    """Fracao cumulativa derrubada ate `minuto` — o modelo de sobrevivencia.

    Monotona no minuto e na taxa por construcao; `0.0` no minuto 0 ou taxa nao
    positiva; teto `1.0` em taxa cheia a partir do minuto 1. Fora desses limites
    e `1 - (1 - taxa) ** minuto`.
    """
    if minuto <= 0:
        return 0.0
    if taxa <= 0.0:
        return 0.0
    if taxa >= 1.0:
        return 1.0
    return 1.0 - (1.0 - taxa) ** minuto


def derrubadas(
    seed: int,
    rota: str,
    flag: str,
    sujeitos: Iterable[str],
    taxa: float,
    minuto: int,
) -> set[str]:
    """O conjunto de sessoes derrubadas ate `minuto`, para esta taxa.

    Reusa `fracao_do_sujeito` como base determinista: a cadencia so decide onde a
    fila e cortada. Funcao pura — sem estado, sem relogio de parede, sem `hash()`.
    """
    corte = corte_cumulativo(taxa, minuto)
    return {s for s in sujeitos if fracao_do_sujeito(seed, rota, flag, s) < corte}


def frame(
    seed: int,
    rota: str,
    flag: str,
    sujeitos: Iterable[str],
    taxa: float,
    minuto: int,
) -> dict[str, str]:
    """O frame TOTAL: TODA sessao presente, `alive` ou `dropped` — INV-7.

    Coerente com `derrubadas` por construcao: os `dropped` do frame sao
    exatamente o conjunto derrubado. E estado total, nunca delta.
    """
    caidos = derrubadas(seed, rota, flag, sujeitos, taxa, minuto)
    return {sujeito: (DROPPED if sujeito in caidos else ALIVE) for sujeito in sujeitos}
