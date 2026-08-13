# v3 — correções da auditoria do v2

## BLOCKER

**B1 — auditor perdia o hook em cada worktree.**
`start_checkpoint_audit.sh` criava um caminho novo por execução. Como hooks de frontmatter de subagente de **projeto** só rodam depois do diálogo de confiança da pasta, cada worktree era não-confiado e o `readonly_bash.py` era pulado silenciosamente — o auditor ficava com Bash irrestrito exatamente na operação em que deveria estar mais contido.

Corrigido em duas frentes:
- `checkpoint-auditor.md` e `readonly_bash.py` movidos para `user-scope/`, instalados pelo `bootstrap.sh` em `~/.claude/`. Definições de escopo de usuário rodam seus hooks sem a etapa de confiança.
- Worktree passou a usar caminho **fixo** (`.aurora-worktrees/audit`), recriado a cada execução. Preserva a confiança de workspace para os hooks de projeto em `.claude/settings.json`, que também dependem dela.

Razão adicional, mais forte que a mecânica: um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit.

## HIGH

**H1 — `codegen.py --check` + `git diff --exit-code` era vacuoso.**
Se `--check` não escreve, o `git diff` está sempre limpo e a etapa não verifica nada. O contrato agora é explícito: `--check` compara em memória e sai diferente de zero em divergência. A etapa `git diff` foi removida.

**H2 — deny de `.env` só cobria a raiz.**
Em project settings, `/path` ancora em `<project root>/path`. Um `.env` em `domains/academus/` passava. Trocado para nome simples (`Read(.env)`, `Read(.env.*)`, `Read(secrets/**)`), que segue semântica gitignore e casa em qualquer profundidade.

## MEDIUM

**M1 —** `push` restrito a `main`. Antes, cada PR gerava dois runs no mesmo SHA e o `spec_freeze` aparecia skipped no run de push.

**M2 —** `finalize_phase0.sh` passou a alinhar os métodos de merge do repositório (`--enable-merge-commit=false`), sem o que `required_linear_history: true` trava o botão de merge.

**M3 —** `finalize_phase0.sh` detecta proteção já aplicada e falha com mensagem explícita em vez de morrer no push. Depois da Fase 0, mudanças vão por PR.

## LOW

**L1 —** `.gitignore` alinhado com `08_EVIDENCE_SIMULATOR.md`: ignora `scenarios/**/evidence/` inteiro. Evidência é projeção determinista de `ground_truth.yaml` + `RANDOM_SEED` e se reconstrói com `range-cli evidence build`.

## Validado nesta versão

Sintaxe de todos os hooks, scripts e configs. Frontmatter dos três agentes. 18 smoke tests funcionais, incluindo: import legítimo de `cryptography` **não** bloqueado, traversal `scenarios/../range-core/` bloqueado, encadeamento `&& rm -rf /` bloqueado, e auditor impedido de commitar ou redirecionar saída.
