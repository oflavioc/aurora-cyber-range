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

UM CRITERIO DE EPOCH PARA OS DOIS LADOS — H1 DA TERCEIRA AUDITORIA
--------------------------------------------------------------------
`epochs_em_calculo` e o MESMO que o computador da declaracao consome, e a
unificacao foi decisao normativa: `09` §3.1 manda *"metricas recomputadas a
partir da nova epoch"* (`facilitation`) e *"metricas da nova epoch"*
(`adjudication`) **sem excecao por lado**.

Antes, este lado lia so o descarte de `rehearsal`. `assessment_submitted` de
epoch ANULADA continuava alimentando o Brier, e `TTIV` marcava em instante de
linha temporal rebobinada — nada falhava, e a metrica continuava sendo
calculada. Tres razoes fecharam a decisao:

1. `09` §3.1 poe `adjudication` como o facilitador ANULANDO decisao por
   informacao fora de banda, e exige que isso apareca no debriefing. `TTIV`
   marcando em instante rebobinado e o oposto;
2. a tabela nao tem excecao por lado, e tratar `assessment_submitted` como imune
   criaria uma que ela nao tem;
3. **por simetria**: `TTID` reinicia na anulacao. `TTIV` medindo de outra linha
   faria o delta do par — *o achado* de `03` §3.2 — comparar DUAS linhas
   temporais.

A EPOCH DO VEREDITO, QUE E OUTRA REGRA E CONTINUA
---------------------------------------------------
`09` §3.1 tambem diz *"satisfacao de epoch abandonada nao conta na corrente"*, e
isso vale para o VEREDITO especificamente: o avaliador reemite na epoch nova
quando a linhagem corrente ainda satisfaz, e nao reemite dentro da mesma epoch.
Por isso o veredito e selecionado por `simulation_epoch == corrente`.

**Este paragrafo declarava uma premissa que o emissor nao honrava — B1 da nona
auditoria.** A selecao aqui estava certa; o avaliador e que suprimia a reemissao
por um criterio proprio, de linhagem, e os dois divergiam quando o corte nao
alcancava o veredito. A selecao passou a ser
`range_core.events.veredito.veredito_da_epoch_corrente`, que e a MESMA funcao que
o avaliador consulta — a premissa deixou de ser declarada e passou a ser
compartilhada.

As duas regras convivem e nao se substituem. `epochs_em_calculo` nao estreita nada
no `technical_failure` — a linha dele nao manda descartar epoch —, e e ali que o
filtro de corrente segue sendo o unico a excluir veredito antigo.

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

from contracts.generated.events import ASSESSMENT_SUBMITTED

from range_core.events.epoch import current_epoch
from range_core.events.veredito import (
    NOME_DO_PREDICADO,
    veredito_da_epoch_corrente,
)
from range_core.metrics.calibracao import brier
from range_core.metrics.epoch import (
    Congelamento,
    apenas,
    congelamentos,
    decorrido,
    epochs_em_calculo,
    instante,
    marco_zero,
)
from range_core.metrics.insumo import InsumoDeVerificacao
from range_core.metrics.medida import Medida, nao_marcada

# `NOME_DO_PREDICADO` e importado de `range-core/events/veredito.py`, e nao
# redeclarado aqui. Ele era declarado nos DOIS modulos, com um teste cruzando as
# copias; a funcao unica do B1 precisa da chave, e a chave foi junto — uma copia,
# e o teste agora afirma que nenhum dos dois a redeclara.

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
    corrente = current_epoch(insumo.epoch)
    congelados = congelamentos(insumo.epoch)
    t_zero = marco_zero(insumo.epoch)
    eventos = apenas(insumo.eventos, epochs_em_calculo(insumo.epoch))

    por_predicado = tuple(
        _medida(
            sigla,
            veredito_da_epoch_corrente(eventos, nome, corrente),
            t_zero,
            congelados,
        )
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
