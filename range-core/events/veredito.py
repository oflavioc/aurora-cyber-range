"""O veredito que sustenta a metrica da epoch corrente — UMA pergunta, uma funcao.

AUTORIDADE
----------
`09_EVENT_MODEL.md` §3.1, bloco *"O avaliador de predicados e a epoch"*: *"A
satisfacao pertence a epoch em que foi emitida... Depois de um rollback, o
avaliador reavalia sobre a linhagem corrente; se ela satisfaz, emite na epoch
nova"*. Tambem `06_ACCEPTANCE_TESTS.md` T10 e `00_MASTER_SPEC.md` §3.2.

POR QUE ISTO EXISTE — B1 DA NONA AUDITORIA
-------------------------------------------
Dois modulos faziam a mesma pergunta com criterios diferentes:

- `range-core/engine/verificacao.py` decidia se SUPRIME a emissao, e perguntava
  *"ha veredito deste predicado na linhagem corrente?"* — sem olhar epoch;
- `range-core/metrics/verificacao.py` decide qual veredito MARCA `TTCV`/`TTRV`, e
  perguntava *"ha veredito deste predicado na epoch corrente?"*.

Os dois conjuntos coincidem quase sempre, e divergem exatamente onde o corte NAO
alcanca o veredito. `range-core/events/linhagem.py` abandona so `ancora < j <
indice_do_rollback`, entao um rollback ancorado EM ou DEPOIS do
`verification_predicate_satisfied` o deixa vivo na linhagem e em epoch antiga: o
avaliador nao reemitia, o computador descartava, e a metade de verificacao do par
sumia pelo resto do exercicio. Nada falhava — e `03` §3.0 chama isso de *"o modo
mais caro de errar: a metrica nao falha, ela deixa de marcar"*.

**A correcao nao foi alinhar os dois filtros por coincidencia.** E uma funcao so,
respondendo *"este predicado ja tem veredito que sustenta a metrica da epoch
corrente?"*, consumida pelos dois lados — a mesma forma que `epochs_em_calculo`
tomou depois do H1 da terceira auditoria.

O CRITERIO E A EPOCH, E A LINHAGEM NAO ENTRA — E POR QUE ISSO E CORRETO
------------------------------------------------------------------------
`09` §3.1 poe a satisfacao COMO PERTENCENTE a epoch em que foi emitida. Veredito
de epoch anterior nao sustenta a metrica da corrente **mesmo sobrevivendo ao
corte** — e e justamente isso que o avaliador precisa saber para reemitir.

A linhagem nao e um segundo filtro porque ela e implicada:

    simulation_epoch == corrente  ==>  esta na linhagem corrente

`current_epoch` conta os `rollback_performed` gravados, e o store carimba a epoch
ANTES do append; logo, evento de epoch corrente e posterior ao ultimo rollback do
fluxo. `escritas_sobreviventes` so abandona posicoes ESTRITAMENTE anteriores ao
rollback que as corta, entao nada o alcanca. A reciproca e falsa, e a diferenca
entre as duas era o B1.

Sem a implicacao, esta funcao seria inconsumivel pelo lado da metrica: o
computador recebe apenas os eventos do lado `verification` (`00` §3.2), e nao tem
o fluxo total de que `escritas_sobreviventes` precisa para derivar posicoes.
`tests/test_verificacao.py::AImplicacaoQueSustentaAFuncaoUnica` a afirma sobre
rollbacks encadeados, para que ela seja premissa medida e nao raciocinio deste
docstring — e afirma tambem que a RECIPROCA e falsa, que e o que produziu o B1.

O QUE ELA DEVOLVE, E POR QUE NAO E UM `bool`
---------------------------------------------
O avaliador quer saber SE existe; o computador quer o INSTANTE. Duas funcoes —
uma predicado, uma seletora — seriam de novo duas implementacoes da mesma busca,
que e a classe D4 que este modulo fecha. Devolve o evento, e quem so precisa da
existencia compara com `None`.
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.generated.events import VERIFICATION_PREDICATE_SATISFIED
from range_core.events.envelope import Event

#: A chave do payload de `verification_predicate_satisfied` — o valor e o nome do
#: predicado em `ground_truth.yaml`.
#:
#: MORA AQUI, e nao no emissor, porque esta funcao precisa dela e o emissor nao
#: pode ser importado pelo computador de metrica. Ela era declarada nos DOIS
#: modulos, com um teste cruzando as duas copias; agora ha uma copia, e o teste
#: afirma que nenhum dos dois redeclara o literal.
NOME_DO_PREDICADO = "predicate"


def veredito_da_epoch_corrente(
    eventos: Sequence[Event], nome: str, corrente: int
) -> Event | None:
    """O `verification_predicate_satisfied` deste predicado NA EPOCH CORRENTE.

    `eventos` pode ser o fluxo total, a linhagem corrente ou so o lado
    `verification` ja recortado por `apenas()`: o filtro de epoch da a mesma
    resposta nos tres, pela implicacao do cabecalho. E o que permite que o
    avaliador e o computador chamem a MESMA funcao com os insumos que cada um
    tem.

    O PRIMEIRO na ordem do fluxo, e a escolha e defensiva e nao decisoria: o
    avaliador emite por transicao e nao empilha veredito dentro da mesma epoch,
    entao ha no maximo um. Se um dia houver dois, marcar o primeiro e a leitura
    de `03` §3.1 — *"o instante em que a condicao passa a valer"* —, e nao a
    ultima reemissao.

    A ordem e a DO FLUXO, e nao `min` por `exercise_timestamp` convertido: `01`
    §4.2 da a ordem do fluxo como a ordem total do exercicio, e ela ja era o
    desempate do `min` anterior. Converter relogio aqui exigiria importar
    `range_core.metrics.epoch.instante`, e a direcao da dependencia e o motivo de
    esta funcao viver em `range-core/events/`.
    """
    for evento in eventos:
        if (
            evento.event_type == VERIFICATION_PREDICATE_SATISFIED
            and evento.payload.get(NOME_DO_PREDICADO) == nome
            and evento.simulation_epoch == corrente
        ):
            return evento
    return None
