"""`precursor_events.jsonl` — o sinal fraco, gerado. `08` §2.

A FRASE QUE ESTE MODULO TORNA VERDADEIRA
=========================================
`08` §2: *"`precursor_events.jsonl` deixa de ser artefato autoral: e **gerado**
como projecao."*

O risco do artefato autoral nao e ele nascer errado — e ele ser **editado
depois**, ficando incoerente com as outras fontes sem que nada acuse. Gerado, ele
e funcao do ground truth; e com o `sha256` no `MANIFEST.json`, a edicao passa a
ser detectavel (item 3 da DoD).

O QUE E UM PRECURSOR, E POR QUE ELE NAO ATRIBUI ATOR
=====================================================
Precursor e o que **antecede** o incidente e so vira significativo depois — a
entrega do phishing, antes de qualquer login. `08` §2 poe a dificuldade em
`discoverability`, que e do gabarito e nao da evidencia.

**Por isso este arquivo NAO carrega `actor`.** Atribuicao e exatamente o que o
time azul tem de construir correlacionando as outras fontes: o `identity_audit`
traz a conta, o `vpn.log` traz o acesso, e e o participante quem liga o sinal
anterior aos dois. Um `actor` aqui entregaria a correlacao pronta e apagaria o
trabalho que o exercicio existe para medir.

**O que ele carrega e o instante, o que foi observado e de onde.** Sao os campos
com que um sinal de rede chega antes de alguem saber de quem ele e.

O LIMITE, DECLARADO: quais fatos sao precursores e decisao do GABARITO, via
`projections`, e nao deste modulo. Ele projeta o que lhe derem. Se um pack
declarar um fato tardio como precursor, o arquivo o trara — e isso e autoria de
cenario, nao defeito de gerador.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domains.academus.evidence_generators.jsonl import linhas

__all__ = ["gerar", "CAMPOS"]

#: SEM `actor` e SEM `credential_state` — ver o cabecalho. Os dois sao
#: atribuicao, e atribuicao e o achado, nao o insumo.
CAMPOS = (
    "exercise_time",
    "action",
    "source_ip",
    "dest",
)


def gerar(fatos: Sequence[Mapping]) -> str:
    return linhas(fatos, CAMPOS)
