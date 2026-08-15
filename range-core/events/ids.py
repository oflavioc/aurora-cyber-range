"""`event_id` — ULID de fonte NAO semeada, e o motivo de nao ser semeada.

POR QUE NAO SAI DO `RANDOM_SEED`
--------------------------------
O item 2 da DoD desta fase exige `RANDOM_SEED` lido por codigo do `range-core`,
e a tentacao e consumi-lo aqui, no primeiro ponto nao-determinista que a fase
produz. Seria errado, e a spec decide sozinha.

Conferido nas cinco ocorrencias em `docs/spec/`: `00` §8, `02` §6, `05` §8,
`06` T8 e `07` Fase 5 amarram o seed a **dataset sintetico, Linha B, evidencias
e senhas de seed** — "mesmo seed, mesmo dataset". Nenhuma o liga a identidade de
evento.

E a propriedade que sairia disso ninguem pediu: `event_id` reproduzivel entre
execucoes distintas e **colisao esperando acontecer** — dois exercicios com o
mesmo seed gerariam os mesmos ids, e o store deixaria de poder distinguir um
evento de outro entre execucoes.

O seed fica para quem gera dado sintetico. Aqui a fonte e `secrets`.

POR QUE ULID, E POR QUE SEM DEPENDENCIA
---------------------------------------
O exemplo de envelope de `09` §1 traz `01J9F...`, que e forma de ULID: 26
caracteres em base32 de Crockford, 48 bits de tempo em milissegundos e 80 bits
aleatorios. Ordenavel lexicograficamente pela metade temporal, o que ajuda a
leitura de um store append-only.

Implementado com a stdlib de proposito. Uma biblioteca traria dependencia nova,
que por T15 exige pinagem com fecho transitivo — custo desproporcional para
trinta linhas cuja especificacao e publica e estavel.

O TEMPO AQUI E DE PAREDE, E NAO DE EXERCICIO
--------------------------------------------
A metade temporal do id usa relogio de parede. Nao e marca de exercicio e nao
concorre com as quatro do envelope: e identidade, nao tempo do incidente. O
`exercise_time` do mesmo evento pode rebobinar num rollback; o id, nunca.
"""

from __future__ import annotations

import secrets
import time

#: Base32 de Crockford: sem I, L, O e U, para nao confundir com 1 e 0 na leitura
#: humana — e um id aparece em mensagem de recusa e em relatorio de AAR.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

_TIME_BITS = 48
_RANDOM_BITS = 80
_LENGTH = 26


def new_event_id() -> str:
    """Um ULID novo. Nao determinista, e e o desenho."""
    milliseconds = time.time_ns() // 1_000_000
    value = (milliseconds << _RANDOM_BITS) | secrets.randbits(_RANDOM_BITS)

    caracteres = []
    for _ in range(_LENGTH):
        value, resto = divmod(value, 32)
        caracteres.append(_ALPHABET[resto])
    return "".join(reversed(caracteres))
