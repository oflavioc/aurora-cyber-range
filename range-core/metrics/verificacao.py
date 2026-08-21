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

`TTIV` — A METADE CUJO VERIFICADOR NAO E O MUNDO
-------------------------------------------------
`TTCV` e `TTRV` saem de predicado de estado do mundo. `TTIV` nao: `03` §3.3 diz
que integridade validada e propriedade da **qualidade da avaliacao da equipe**, e
fixa o instante como *"aquele em que o conjunto de `assessment_submitted` atinge
`calibration.threshold`, medido contra a defensibilidade do gabarito"*.

**Isso nao a tira do par** — a §3.3 corrige explicitamente a redacao anterior que
a chamava de assimetrica. Pelo criterio de `00` §3.2 o par exige conclusao de
acao da equipe com instante decidido fora da declaracao, e as duas valem. O que
muda e QUEM decide o instante, e nao se ha par.

O BRIER VEM DE `metrics/calibracao.py`, e nao e reescrito aqui: `03` §3.3 aponta
para §5, e duas implementacoes da mesma formula divergiriam — a classe D4. Este
modulo faz o que so ele pode fazer: percorrer as submissoes na ordem do exercicio
e achar a PRIMEIRA em que o escore cruza o limiar.

Os tres escalares chegam pelo insumo — `limiar_de_calibracao`, `defensibilidade`
e `escopo_revisado` —, e `00` §3.2 exige exatamente essa forma: como dado, e nao
por consulta ao pack.

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

from contracts.generated.events import (
    ASSESSMENT_SUBMITTED,
    VERIFICATION_PREDICATE_SATISFIED,
)

from range_core.events.epoch import current_epoch
from range_core.metrics.calibracao import brier
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

#: A terceira metade de verificacao. NAO esta em `SIGLA_POR_PREDICADO` porque
#: nao e predicado: `03` §3.3 poe o verificador dela fora do mundo, e o teste que
#: cruza aquele mapa com `verification_predicates` reprovaria se ela entrasse.
SIGLA_DO_LIMIAR = "TTIV"


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

    por_predicado = tuple(
        _medida(sigla, _veredito(eventos, nome, corrente), t_zero, congelados)
        for nome, sigla in SIGLA_POR_PREDICADO.items()
    )
    return por_predicado + (
        _medida(
            SIGLA_DO_LIMIAR,
            _instante_do_limiar(
                eventos,
                defensibilidade=insumo.defensibilidade,
                escopo=insumo.escopo_revisado,
                limiar=insumo.limiar_de_calibracao,
            ),
            t_zero,
            congelados,
        ),
    )


def _instante_do_limiar(
    eventos,
    *,
    defensibilidade,
    escopo: frozenset[str],
    limiar: float,
):
    """A submissao em que o Brier passa a valer `<= limiar` — `03` §3.3.

    A PRIMEIRA, e nao a ultima: `03` §3 mede o tempo ATE a integridade estar
    validada, e a equipe que continua submetendo depois de cruzar o limiar nao
    move o instante em que ela cruzou.

    O escore e RECALCULADO a cada prefixo, e nao acumulado num contador: `03` §5.3
    conta caso do escopo nao avaliado como `confidence = 0`, entao o Brier CAI
    conforme a equipe avalia bem — e um acumulador teria de saber desfazer o
    "nao avaliado" de cada caso ao ve-lo chegar. Recalcular e O(n^2) sobre o
    numero de submissoes e exato; o exercicio tem dezenas, nao milhoes.

    Cruzar e `<=`, e nao `<`: `04` §2 chama o valor de *"Brier maximo para
    considerar integridade validada"*, e maximo inclui o proprio valor.
    """
    submissoes = sorted(
        (e for e in eventos if e.event_type == ASSESSMENT_SUBMITTED), key=instante
    )
    for quantas in range(1, len(submissoes) + 1):
        escore = brier(
            submissoes[:quantas], defensibilidade=defensibilidade, escopo=escopo
        )
        if escore is not None and escore <= limiar:
            return submissoes[quantas - 1]
    return None


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
