# R3 — TDD como estrutura

Severidade: **bloqueante** (hook `guard-tdd`, instalado na Onda 3; até lá,
disciplina do orquestrador com o stage `tdd` previsto).

TDD aqui não é pedido ao implementador — é separação estrutural de poderes:

1. **Fase diferente** — o gate nasce na Spec (Fase 1), antes do Plano.
2. **Autor diferente** — `qa-engineer` escreve o gate; os engenheiros
   (`ui-engineer`/`core-engineer`/`build-engineer`/`data-engineer`) implementam.
   O implementador **nunca** escreve o próprio critério de aceite; o QA
   **nunca** implementa a correção.
3. **O gate viaja no prompt de delegação** — o implementador o recebe pronto.
4. **Prova de red registrada** — o QA executa o gate ANTES da implementação e o
   FAIL é **commitado** (red não commitado é red inauditável). O planning-state
   registra `red.status: proven` com a referência do commit.
5. **Mutante obrigatório** — gate novo só é aceito matando um mutante escrito
   para ele. Campanha re-executada quando módulo ou gate muda (Onda 3: trigger
   por path).

## Tipagem de tarefa (válvula 1)

O `tech-lead` tipa cada tarefa no `tasks.md`; a escolha é auditável:

| Tipo | Exige red provado? |
|---|---|
| `feature`, `fix` | **Sim** |
| `refactor`, `doc`, `chore` | Não |

## Waiver (válvula 2)

`tdd_waiver: {motivo, data}` no planning-state deixa passar — e o
`compliance-audit` (seção `waivers`) **lista todos** a cada execução. Waiver é
rastro, não obstáculo. Waiver frequente = tipagem errada; a conversa acontece
sobre o dado.

## Ciclo

```
PO refina → TL desenha → QA escreve gate + prova RED (commit)
  → implementador (gate no prompt) → GREEN
  → QA revalida: green + mutante morto + regressão congelada intacta
  → PO aceita intenção
```
