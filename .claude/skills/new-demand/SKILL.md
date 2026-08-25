---
name: new-demand
description: Conduz uma demanda nova da ideia à validação em 7 fases com aprovação explícita do usuário entre cada uma (Refinamento → Spec → Plano → Tarefas → Red → Implementação → Validação). Use quando o pedido cria comportamento novo — módulo, superfície, contrato, gate de feature.
---

# Demanda nova

O gate está em `.claude/rules/sdd.md`; a orquestração em `orchestration.md`; o
TDD em `tdd.md`. Esta skill é o procedimento. **Nenhuma fase começa sem a
anterior aprovada pelo usuário** ("ok", "sim", "prossiga", "aprovado" — no chat).

## Antes de tudo

1. Estado limpo: `bash .claude/verify/run.sh --light` verde; senão, tratar primeiro.
2. **Branch**: `git checkout main && git pull && git checkout -b feature/NNN-slug`
   (próximo NNN livre; worktree se houver outra conversa ativa — R14).
3. Criar `specs/NNN-slug/` e o planning-state
   (`.claude/project-memory/planning-state/<slug>.json`, schema em
   `.claude/templates/planning-state.schema.json`), `phase: "refinement"`.
4. Atualizar o planning-state a **cada** mudança de fase/status — é ele que o
   `state-eval` injeta e o stage `state` valida.

## Fase 0 — Refinamento → `refinement.md`

Delegar ao `product-owner` (template `refinement.md`): enquadramento, desafio,
casos de borda, vocabulário no `CONTEXT.md`. Raia técnica que o PO apontar em
DEPENDÊNCIAS → orquestrador consulta o especialista e devolve o destilado ao PO.
Sem limite de rodadas. **Gate**: usuário aprova o entendimento.

## Fase 1 — Spec → `spec.md`

PO + `tech-lead` (template): formaliza o refinamento, referencia sem repetir.
**Critérios de aceite viram GATES definidos aqui** — id, arquivo, asserção e o
mutante previsto. Cross-check contra invariantes, `design-decisions.md` e specs
validadas; conflito → parar e escalar. **Gate**: aprovação do usuário.

## Fase 2 — Plano → `plan.md`

`tech-lead` (template): camadas, owner do estado, contratos/pontos de extensão,
boundary (rito nomeado se tocar protegido), waves. **Gate**: aprovação do usuário.

## Fase 3 — Tarefas → `tasks.md`

`tech-lead`: `[TNNN]`, wave, dono, tipo, `[P]`. **Gate**: aprovação do usuário.

## Fase 4 — Red

`qa-engineer`: escreve os gates da spec, **executa e registra o FAIL, commita o
red** (mensagem: `test(NNN): red — <gate>`); escreve os mutantes. Planning-state
`red.status: proven` + ref do commit. **Gate**: red provado (tarefas
feature/fix; demais tipos pulam com o tipo registrado).

## Fase 5 — Implementação

Por wave, na ordem; `[P]` em delegações paralelas na mesma mensagem. Cada
delegação: **um módulo**, com o gate e a spec REFERENCIADOS por caminho no
prompt. Falha de um agente não derruba os pares; máx. 3 tentativas → escalar.
Registrar `implement.waves_done`/`pending` após cada wave.

## Fase 6 — Validação

1. `qa-engineer`: green + mutante morto + pipeline completo verde (contagens
   canônicas) + `spec-validate` (score; <100% → classificar e iterar, máx. 2).
2. `product-owner`: aceite de intenção contra o `refinement.md`.
3. Push + **PR feature → main** (`gh pr create --base main`; merge por rebase,
   `--squash` proibido — R14); merge é do usuário. Planning-state `done` só
   com PR aberto e CI verde.
