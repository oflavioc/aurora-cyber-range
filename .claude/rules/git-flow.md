# R14 — Git flow

Severidade: **processo**. Esta regra DOCUMENTA o fluxo que o aurora já pratica
(`docs/process/WORKFLOW.md` é a fonte; em divergência, ele prevalece) — o kit
da Estrutura Agêntica traz um modelo develop/feature que NÃO foi adotado aqui.

## Modelo do aurora (vigente)

| Branch | Papel |
|---|---|
| `main` | Integração. Recebe código exclusivamente por PR com **merge rebase** (`gh pr merge --rebase`); `--squash` é **proibido** — escapa do predicado da auditoria (WORKFLOW.md) |
| `fase-<n>-<slug>` | **Uma por fase do roadmap.** Nasce de `main`; a âncora vai em `docs/process/phase_anchors.tsv` (sem ela a auditoria recusa); fecha por PR após auditoria de checkpoint |
| `spec-change/<slug>` | Mudança de `docs/spec/` — PR separado, título `spec-change:`, aprovação humana antes de qualquer código. Spec e código no mesmo PR é bloqueado pelo gate `spec_freeze` |
| `feature/NNN-slug` | **(novo, Onda 2)** Uma por demanda fora do roadmap conduzida pela skill `new-demand`; nasce de `main` atualizada, volta por PR com rebase; `NNN-slug` casa com `specs/NNN-slug/` |

## Regras de commit e merge

- Commits pequenos e narrados (padrão vigente: `fase-7 peca N (i/n): ...`);
  **proibido squash**.
- O commit RED do TDD entra no histórico e é referenciado no PR (R3).
- Alterou arquivo pinado → `gen_pins.py` **no mesmo PR**, pins em commit
  próprio com motivo (R8).
- Merge de PR é **do operador**. Push de branch de trabalho e abertura de PR
  são livres.
- Auditoria de checkpoint antes do PR de fase:
  `bash scripts/start_checkpoint_audit.sh <n>` — inalterado.

## Worktrees

Branch isola o histórico, não o disco. Duas conversas simultâneas → uma
worktree por demanda (`git worktree add ../aurora-NNN feature/NNN-slug`).
A auditoria de checkpoint já usa worktree fixado no commit candidato — mesmo
princípio.

## Autonomia

| Ação | Autonomia |
|---|---|
| Criar branch, worktree, push de branch de trabalho, abrir PR | **Livre** |
| Merge de PR em `main` | **Do operador** |
| Editar `docs/spec/` | **Nunca junto com código** — rito spec-change |
| Commit direto em `main` | **Não** |
