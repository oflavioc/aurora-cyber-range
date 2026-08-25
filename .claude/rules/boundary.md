# R6 — Change boundary

Severidade: **bloqueante** (hook `guard-boundary` + stage `boundary` +
`permissions.deny`).

A boundary é **dado, não prosa**: `.claude/verify/boundary.json` declara as
classes de proteção e o rito que autoriza mudança em cada uma.

## Classes no aurora

| Classe | Conteúdo | Rito de mudança |
|---|---|---|
| `frozen` | *(vazia por decisão de adoção)* — a superfície congelada do aurora é `docs/spec/`, e ela JÁ tem mecanismo próprio e mais forte: gate `spec_freeze` do CI + PR `spec-change:` com aprovação humana. Duplicá-la aqui criaria segunda autoridade para o mesmo fato | rito spec-change (WORKFLOW.md) |
| `generated` | `contracts/generated/events.py`, `contracts/generated/events.ts` | só via `tools/codegen.py`; `codegen.py --check` prova identidade no CI |
| `legacy` | *(vazia)* | — |
| `registry` | `.claude/verify/pins.json` | só via `gen_pins.py`, no mesmo PR, com motivo no commit |

## Regras

1. Edição direta de path protegido é **negada pelo hook** com o rito nomeado.
2. `permissions.deny` espelha o boundary (Edit+Write) — o `compliance-audit`
   (seção `deny`) falha se divergirem.
3. **Expansão de boundary só por spec commitada ANTES do código** — nunca por
   autorização registrada só em prosa de relatório.
4. Quando uma fase do roadmap é fechada e auditada, seus módulos são candidatos
   ao freeze acumulativo — decisão do operador, fase a fase.
5. Correção que exigir arquivo protegido: **PARAR, explicar o rito, aguardar**
   a autorização do usuário no chat.
