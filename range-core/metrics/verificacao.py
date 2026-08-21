"""O computador do lado da VERIFICACAO — `TTCV` e `TTRV`.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §3 (tabela dos pares) e §3.1; `09_EVENT_MODEL.md` §3.1;
`00_MASTER_SPEC.md` §3.2; `06_ACCEPTANCE_TESTS.md` T10.

O QUE ELE RECEBE, E O QUE ELE NAO TEM
--------------------------------------
`InsumoDeVerificacao`, e nada alem. Sem store, sem pack e sem fluxo total: nao ha
por onde buscar mais do que lhe foi dado. Em particular **ele nao alcanca
`containment_declared`** — o que fecha, pelo lado que nenhuma regra anterior
alcancava, o defeito de `TTCD` computado a partir de `TTCV` (`00` §3.2).

O QUE ELE MARCA
---------------
Dois instantes, um por predicado de `03` §3.1, que sao os dois que o contrato
admite — `verification_predicates` tem `additionalProperties: false` e exige
`containment` e `service_restoration`.

**Ele marca INSTANTE, e nao delta de par.** O delta entre as duas metades e do
`aar_timeline`: `00` §3.2 o diz por nome, e e a mesma colocacao da janela de
asseguracao prematura. O que este modulo entrega junto do instante e o
**decorrido desde T0, ja descontado** — sem ele, o AAR teria de refazer o
desconto para cada metade, e duas implementacoes da mesma regra divergem.

SO A LINHAGEM CORRENTE SUSTENTA A METRICA
------------------------------------------
`09` §3.1: *"satisfacao de epoch abandonada nao conta na corrente"*. O evento
continua no store, legivel e marcado — `01` §4.1 —, e o AAR o renderiza; o que
ele nao faz e sustentar `TTCV` da epoch nova. Por isso o veredito e selecionado
por `simulation_epoch == corrente`, e nao por "o primeiro que aparecer".

O avaliador da peca 4 reemite na epoch nova quando a linhagem corrente ainda
satisfaz, e nao reemite dentro da mesma epoch — a emissao e por transicao. Entao
ha no maximo um veredito por (predicado, epoch), e a selecao e determinada.

`TTIV` NAO ESTA AQUI, E A FRONTEIRA E DO PLANO DA FASE
-------------------------------------------------------
`TTIV` e a terceira metade de verificacao, e ela e da **peca 6** — o plano da
fase a nomeia por extenso: *"Calibracao: Brier no escopo revisado, sinais, `TTIV`
por limiar"*. Ela nao e predicado de estado do mundo (`03` §3.3): o instante e
aquele em que o conjunto de `assessment_submitted` cruza o limiar de calibracao
medido contra a defensibilidade, e o mecanismo do limiar nasce com o escore.

Os escalares dela JA CHEGAM no insumo — `limiar_de_calibracao` e
`defensibilidade` —, e isso e deliberado: `00` §3.2 exige que eles cheguem como
dado e nao por consulta ao pack, e a peca 6 encontra o caminho pronto. Escrito
aqui para que a auditoria leia a fronteira em vez de deduzi-la da ausencia.

`not_applicable` — O QUE ESTE MODULO NAO DISTINGUE, E POR QUE
---------------------------------------------------------------
`service_restoration` aceita `not_applicable` com motivo (D5 da Fase 1,
`ground_truth.schema.yaml`), e o avaliador nao o avalia nem emite. Daqui, isso e
indistinguivel de *"ainda nao verificado"*: os dois sao ausencia de veredito.

**A distincao exige o pack, e o pack e o banido de `00` §3.2.** Ela nao e
inventada aqui por um argumento que este repositorio ja escreveu: enumerar o
vocabulario antes de o consumidor existir e prever o modulo, e a proxima palavra
nao estaria na lista — e a razao pela qual `check_store_read_surface.py` esperou
a API existir. Quem imprime *"TTRV nao aplicavel"* e o AAR, que tem o pack; o que
ele recebe daqui e `NAO_VERIFICADA`, que e verdade sobre o insumo deste lado.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from contracts.generated.events import VERIFICATION_PREDICATE_SATISFIED

from range_core.events.epoch import current_epoch
from range_core.metrics.epoch import (
    Congelamento,
    congelamentos,
    decorrido,
    epochs_descartadas,
    instante,
    marco_zero,
    no_calculo,
)
from range_core.metrics.insumo import InsumoDeVerificacao
from range_core.metrics.medida import Medida, nao_marcada

#: A chave do payload de `verification_predicate_satisfied`. O valor e o nome do
#: predicado em `ground_truth.yaml`, e o emissor e
#: `range-core/engine/verificacao.py` — que declara a mesma constante pelo mesmo
#: motivo. `tests/test_metrics_verificacao.py` cruza as duas.
NOME_DO_PREDICADO = "predicate"

#: OS DOIS PREDICADOS, e sao os dois que o contrato admite:
#: `verification_predicates` exige `containment` e `service_restoration` e fecha
#: com `additionalProperties: false`. A cobertura e cruzada com o contrato em
#: teste — predicado novo no schema sem sigla aqui reprova, em vez de existir sem
#: metrica que o leia.
PREDICADO_CONTENCAO = "containment"
PREDICADO_RESTAURACAO = "service_restoration"

SIGLA_POR_PREDICADO: dict[str, str] = {
    PREDICADO_CONTENCAO: "TTCV",
    PREDICADO_RESTAURACAO: "TTRV",
}


#: A FORMA DO RESULTADO E COMPARTILHADA com o computador da declaracao —
#: `range-core/metrics/medida.py` diz por que. A particao de `00` §3.2 e sobre
#: INSUMO: um tipo de saida comum nao abre caminho para um lado ler o outro,
#: porque ele nao carrega evento nenhum.
#:
#: `inicio` e T0 nas metricas deste lado: `03` §3 nao lhes da coluna de start, e
#: a redacao-alvo do AAR em §3.2 as imprime em `T+`.


def computa(insumo: InsumoDeVerificacao) -> tuple[Medida, ...]:
    """As metricas do lado da verificacao, na ordem de `03` §3.

    Todo o consumo de epoch acontece AQUI, em codigo visivel: a epoch corrente, o
    descarte de `rehearsal` e a uniao dos congelamentos saem da escrituracao que
    o insumo trouxe. `00` §3.2 exige essa colocacao — recortados na montagem, o
    numero certo apareceria por ausencia de insumo em vez de por calculo.
    """
    descartadas = epochs_descartadas(insumo.epoch)
    corrente = current_epoch(insumo.epoch)
    congelados = congelamentos(insumo.epoch)
    t_zero = marco_zero(insumo.epoch)
    eventos = no_calculo(insumo.eventos, descartadas)

    return tuple(
        _medida(sigla, _veredito(eventos, nome, corrente), t_zero, congelados)
        for nome, sigla in SIGLA_POR_PREDICADO.items()
    )


def _veredito(eventos, nome: str, corrente: int):
    """O `verification_predicate_satisfied` do predicado, NA EPOCH CORRENTE.

    O `min` por instante e defensivo e nao decisorio: o avaliador emite por
    transicao e nao empilha veredito dentro da mesma epoch, entao ha no maximo
    um. Se um dia houver dois, marcar o PRIMEIRO e a leitura de `03` §3.1 —
    *"o instante em que a condicao passa a valer"* —, e nao a ultima reemissao.
    """
    candidatos = [
        e
        for e in eventos
        if e.event_type == VERIFICATION_PREDICATE_SATISFIED
        and e.payload.get(NOME_DO_PREDICADO) == nome
        and e.simulation_epoch == corrente
    ]
    return min(candidatos, key=instante, default=None)


def _medida(
    sigla: str, veredito, t_zero: datetime, congelados: tuple[Congelamento, ...]
) -> Medida:
    if veredito is None:
        return nao_marcada(sigla)
    marcado = instante(veredito)
    return Medida(
        sigla=sigla,
        inicio=t_zero,
        fim=marcado,
        decorrido=decorrido(t_zero, marcado, congelados),
    )
