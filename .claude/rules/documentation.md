# R12 — Documentação

Severidade: **processo**; itens marcados são auditados por máquina.

## Idioma e nomes

Já é norma do aurora (CLAUDE.md §Idioma) e permanece: **inglês** para
identificadores, tabelas, colunas, endpoints, logs, nomes de flag e de evento;
**PT-BR** para interface, dados sintéticos, cenários, rubricas, documentação e
commits.

## Templates obrigatórios (novo — demandas da máquina SDD)

Artefatos de demanda usam `.claude/templates/`: `refinement.md`, `spec.md`,
`plan.md`, `tasks.md`. Os registros de FASE do roadmap seguem o formato
existente de `docs/progress/` — não mudam.

## Glossário — `CONTEXT.md` (a criar na Onda 2)

Vocabulário canônico do domínio, na raiz, mantido no refinamento de cada
demanda. Formato por termo: definição em 1–2 frases + sinônimos a evitar.
Candidatos óbvios do aurora: ground truth, evidência observável, declaração,
avaliação, inject, epoch, fold, projeção, pack, âncora, peça.

## Achados e backlog

Achados ganham **id permanente** (o aurora já faz: P6-9, B1, M2 — manter o
padrão; números citados nunca renumeram). Cada achado cita a cadeia
arquivo:linha→efeito. Refutado fica riscado com a razão (R2 §5). Decisão
confirmada vai para [`design-decisions.md`](design-decisions.md).

## ADRs

Decisão **difícil de reverter** + **surpreendente sem contexto** + **fruto de
trade-off real** → `docs/adr/NNNN-slug.md` (template em
`.claude/templates/adr.md`). Faltando qualquer um dos três, não é ADR — vira
comentário no lugar onde a decisão mora (o aurora pratica isso extensamente em
`invariants.yml`; ADR é para a decisão que nenhum arquivo único abriga).

## O que é gerado e não se edita à mão

| Arquivo | Gerado por |
|---|---|
| `contracts/generated/events.py` / `events.ts` | `tools/codegen.py` |
| `.claude/verify/pins.json` | `gen_pins.py` |
| `range-core/web/dist/` (não versionado) | build das telas (compose `web-build`) |

Alterar a lógica no gerador, nunca a saída.
