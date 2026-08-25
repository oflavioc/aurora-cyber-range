# Spec — <NNN-slug>

> Fase 1 · donos: product-owner + tech-lead · referencia o refinement.md, não o repete.

## Objetivo

Uma frase. Link: [refinement.md](refinement.md).

## Critérios de aceite → gates

Todo critério é um gate executável, definido AQUI (antes do plano — R3 §1).

| # | Critério | Gate (id · arquivo · asserção) | Mutante previsto |
|---|---|---|---|

## Comportamento especificado

Por superfície: entrada → saída esperada, incluindo os casos de borda do
refinamento. Estados especiais do domínio tratados explicitamente quando tocados.

## Contratos

API/payload/estado novo: shape, owner do estado (R9 §5), consumidores.

## Cross-check (obrigatório)

- [ ] Invariantes R1 — nenhuma violada
- [ ] design-decisions.md — nenhum conflito
- [ ] Specs validadas anteriores — nenhuma contradição
- [ ] Boundary (R6) — toca protegido? Se sim: rito nomeado e autorização PARADA aqui

## Fora de escopo

Herdado do refinamento + o que a spec exclui.
