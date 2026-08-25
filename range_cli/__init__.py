"""`range-cli` — a superficie de linha de comando de `04_SCENARIO_SCHEMA.md` §8.

POR QUE UM PACOTE DE TOPO, E NAO `range-core/cli/`
==================================================
**O invariante 1 decide, e nao o gosto.** `range-core/` nao importa nada de
`domains/`, e `tools/check_core_boundary.py` o impoe por AST. O produtor de pack
precisa chamar o GERADOR do dominio — hoje
`domains.academus.seed.gabarito.gerar` —, e gerador e codigo, nao dado: nao ha
como recebe-lo por caminho de arquivo como a `academus-api` recebe as flags.

Entao o CLI e RAIZ DE COMPOSICAO, no mesmo sentido que
`range-core/api/processo.py`: ele conhece os dois lados e os liga. A diferenca e
que aquele consegue ficar dentro do core porque so precisa de DADO do dominio, e
este precisa de codigo. Por isso ele mora fora.

`01_ARCHITECTURE.md` §2 nao nomeia lugar para o CLI — a arvore dele lista
`range-core/`, `domains/`, `scenarios/`, `contracts/`, `tools/` e `docs/`, e o
CLI nao aparece em nenhum. A escolha e desta peca, e o argumento e o de cima.

UM SUBCOMANDO, E OS OUTROS CINCO NAO EXISTEM
=============================================
`04` §8 enumera sete. Este pacote entrega **um**: `scenario materialize`.

`validate`, `lint`, `dryrun` e `migrate` sao das pecas 4 e 5; `evidence build` e
`evidence verify` sao da Fase 9. Criar casca vazia para eles agora seria
superficie que PARECE existir — e o `07` ja registra, na Fase 1, que roteiro que
promete peca de fase futura nao e roteiro. Um `range-cli scenario lint` que
saisse zero sem conferir nada seria pior que a ausencia dele: a ausencia grita.
"""
