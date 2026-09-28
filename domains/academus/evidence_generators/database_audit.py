"""`database_audit.jsonl` — a projecao da trilha do banco. `08` §3.

O QUE ESTA FONTE CARREGA, E POR QUE SAO AS DUAS LINHAS
=======================================================
`08` §3: *"leitura em massa (Linha A) e alteracoes de nota com IP e sessao
(Linha B)"*. E a **unica fonte que atravessa as duas linhas do exercicio**, e
isso nao e acaso: as duas deixam rastro na mesma trilha de banco, e separa-las
em arquivos distintos entregaria de graca a distincao que o participante precisa
descobrir — que ha dois incidentes, nao um (o OBJ-03, *"reconhecer incidentes
concorrentes"*).

A LINHA B LEVOU TRES RODADAS DE AUDITORIA PARA FICAR CERTA
===========================================================
    peca 3       os fatos da Linha B ganham `projections: [database_audit]`
    B1 da 3a     a projecao SAI: o gabarito so tem fato para os CASOS, e o
                 arquivo de 67 linhas entregava quais eram caso
    H1 da 4a     a projecao VOLTA, agora com a populacao inteira — 3.145
                 linhas de trilha, das quais 67 sao caso

A saida do B1 que eu escolhi — *"uma fonte que projete da TRILHA"* — apontava
para fora da spec: `00` §5.3 e categorico, *"toda evidencia e projecao de fato
canonico declarado em `ground_truth.yaml`"*. A saida certa estava na propria
mensagem da guarda de cobertura: **projetar a populacao inteira da especie**. E
ela nao e concessao, e o artefato CERTO — a trilha que o time azul tria sao as
3.145 linhas, nao as 67 que alguem ja separou.

E A ORDEM DO ARQUIVO E POR INSTANTE, e nao por conjunto: `gabarito.gerar` ordena
os fatos da Linha B antes de montar o documento, porque o motor preserva a ordem
do documento e a POSICAO no arquivo entregaria a particao por defensibilidade sem
que nenhum campo vazasse.

`records_affected` E O QUE DISCRIMINA AS DUAS
==============================================
A leitura em massa traz milhares; cada alteracao de nota traz **um**. E o campo
que o time azul usa para separar os dois padroes sem que nada no arquivo lhe
diga qual e qual — leitura de evidencia, nao rotulo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domains.academus.evidence_generators.jsonl import linhas

__all__ = ["gerar", "CAMPOS"]

#: `dest` carrega o objeto tocado — o host na Linha A, a matricula do aluno na
#: Linha B. O mesmo campo com significados distintos e o que o fato declara, e a
#: fonte o espelha em vez de reinterpretar: reinterpretar seria a projecao
#: afirmando algo que o ground truth nao disse.
CAMPOS = (
    "exercise_time",
    "actor",
    "action",
    "source_ip",
    "dest",
    "records_affected",
)


def gerar(fatos: Sequence[Mapping]) -> str:
    return linhas(fatos, CAMPOS)
