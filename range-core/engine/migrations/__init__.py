"""Migracoes de `schema_version` de pack — o registro, e o que ele NAO tem.

AUTORIDADE
----------
`04_SCENARIO_SCHEMA.md` §4, a politica de versionamento inteira:

    - Engine declara `ENGINE_VERSION` e `SUPPORTED_SCHEMA_VERSIONS = [N, N-1]`
    - Pack em N-1 carrega com migracao em memoria e aviso no boot
    - Pack anterior a N-1 e recusado com instrucao de migracao
    - Migracoes em `range-core/engine/migrations/v<n>_to_v<n+1>.py`, cada uma
      com teste
    - Nunca alterar semantica de campo dentro da mesma `schema_version`

O ESTADO DESTE MODULO, DITO ANTES DE QUALQUER COISA
=====================================================
**`MIGRACOES` esta VAZIO, e o mecanismo que o consulta NUNCA correu contra uma
transicao real.** Nao ha `v1_to_v2.py`. Nao ha migrador nenhum.

Isso nao e lacuna esquecida nem trabalho pela metade: e o estado correto, e o
paragrafo abaixo e a razao.

POR QUE NAO HA MIGRADOR — MEDIDO, E NAO SUPOSTO
================================================
**Nenhum contrato anterior ao v2 jamais existiu neste repositorio.** Medido com

    git log --all --diff-filter=A --name-only -- 'contracts/scenario.schema*'

que devolve **um** arquivo: `contracts/scenario.schema.v2.yaml`, acrescentado em
`31ddcfa` ("fase-1: contratos, esqueleto e geracao de constantes"). Os quinze
commits que tocaram o caminho tocaram esse mesmo arquivo. Nao ha `v0`, nao ha
`v1`, e nunca houve.

Entao um `v1_to_v2.py` seria escrito contra uma versao que ninguem definiu, e o
unico corpo possivel para ele seria a IDENTIDADE — receber o documento e
devolve-lo igual. **Um migrador identidade e pior que migrador nenhum**: ele faz
o item de DoD passar, faz o teste dele passar, e nao transforma nada. O gate
ficaria verde sobre um mecanismo que nunca foi exercido, e a primeira transicao
de verdade encontraria o caminho "provado" e errado.

E a mesma classe que `00` §3.2 nomeia — o numero certo aparecendo por ausencia
de insumo em vez de por calculo.

O QUE FALTOU PARA HAVER UM DELTA NESTA FASE, e as duas tentativas estao medidas
--------------------------------------------------------------------------------
A Fase 7 chegou perto de produzir um `v2 -> v3` por dois caminhos, e nenhum dos
dois chegou la:

1. **A P5-4** — os seis conjuntos de `02` §6.1 contra os tres valores de
   `line_b_case.set`. E o candidato mais proximo, e a medicao da peca 2 mostrou
   que ele **excede o que cabe num delta de schema**: promover ruido de
   manutencao e credenciais compartilhadas a caso muda a `fact_class` dos fatos
   que os sustentam, e com ela o predicado de contencao — que decide TTCV e
   TTRV. Nao e expansao de enum; e mudanca de semantica de verificacao. Saiu
   desta fase por isso.

2. **O aperto de `since`** (spec-change #58 e PR #59) — `type: string` livre
   virou `enum: [self]`. Parece delta e nao e: `03` §3.1 ja fixava `self` como a
   unica forma de v1 desde o `spec-change` #49, e a guarda de carga ja recusava
   o resto. O contrato deixou de ser MAIS PERMISSIVO que a norma; nenhum pack
   valido de ontem deixou de ser valido hoje. Transformacao nenhuma, logo
   migracao nenhuma.

QUANDO O PRIMEIRO MIGRADOR REAL NASCE
--------------------------------------
No commit em que existir um delta que mude a forma de um pack que ja era valido
— e a **P5-4** e o candidato mais proximo, agendada para fora desta fase. Ali o
`v2_to_v3.py` tera corpo, tera teste, e `SUPPORTED_SCHEMA_VERSIONS` passara a
`(3, 2)`.

Ate la `SUPPORTED_SCHEMA_VERSIONS` fica em `(2,)`, e a assimetria com a norma —
que pede `[N, N-1]` — e DELIBERADA e nao descuido: declarar suporte a uma versao
cujo contrato nunca existiu seria a afirmacao falsa que o `pack_loader` ja
recusava fazer desde a Fase 2.

O QUE ESTE MODULO ENTREGA, ENTAO
=================================
O **registro** e a **forma da consulta**. `pack_loader._verify_schema_version` o
consulta para decidir QUAL das duas mensagens de recusa emitir — a de "existe
caminho de migracao" ou a de "nao existe" —, e e o registro que torna essa
pergunta um dado em vez de um `try: import` que falha por motivo errado.

Acrescentar uma migracao passa a ser: escrever `v<n>_to_v<n+1>.py` com teste, e
declara-la aqui. Uma linha, e ela fica no diff.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

#: `schema_version` de ORIGEM -> nome do modulo que a migra para a seguinte.
#:
#: VAZIO, e a ausencia e a entrega — ver o cabecalho. O tipo e `Mapping` e o
#: valor e `MappingProxyType` para que ninguem o preencha em runtime: uma
#: migracao registrada fora do diff seria migracao que nenhuma revisao viu.
MIGRACOES: Mapping[int, str] = MappingProxyType({})


def ha_migracao(de: int) -> bool:
    """Existe migrador declarado para a `schema_version` de origem?

    A pergunta e de DADO e nao de import: `try: import v1_to_v2` diria "nao" com
    a mesma cara para modulo ausente e para modulo com erro de sintaxe, e as
    duas coisas exigem respostas diferentes de quem carrega o pack.
    """
    return de in MIGRACOES
