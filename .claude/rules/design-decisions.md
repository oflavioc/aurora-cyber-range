# R13 — Decisões de projeto que não são defeitos

**Não reportar como achado, não "corrigir de passagem".** Reapresentar decisão
confirmada como defeito gera ruído e desgasta a confiança nos achados reais.

## Confirmadas (com a fonte da confirmação)

Semeadas na adoção da Estrutura Agêntica a partir de registros existentes —
cada linha aponta a fonte; nenhuma é nova:

| Tema | Decisão |
|---|---|
| **`scenarios/` fora do Git** | Decidido pelo operador na peça 5 da Fase 5. Gabarito é *quais casos* (saem do `RANDOM_SEED`); descrição não é gabarito. `check_gabarito_fora_do_git.py` executa. Fonte: CLAUDE.md §Ground truth |
| **`checkpoint-auditor` fora do repositório** | Deliberado: auditor definido pelo commit que audita pode ser enfraquecido por esse commit. Fonte: CLAUDE.md §Fluxo por fase, WORKFLOW.md |
| **Job `contratos` roda testes de código** | Nome desatualizado de propósito: job novo = context novo, e context exigido antes de existir em `main` trava PRs (P1-18). Condição de saída registrada em `docs/progress/fase_2.md` §3.3 |
| **`docker-compose.yml` é DESCRITIVO no gate spec_freeze** | Composição local parametrizada por ambiente; os digests têm guarda própria (`check_pinned_images.py`). Fonte: comentário do `invariants.yml` |
| **Jobs `arquitetura`/`seguranca` sem `pip install`** | Gate que depende da aplicação que julga deixa de ser gate. Fonte: WORKFLOW.md / comentário do `invariants.yml` |
| **Probes-only no CI para predicados do lançador/worktree** | `check_audit_base`, `check_provas_de_container`, `check_prova_do_seed` julgam perguntas do lançador, não do PR — no CI rodam só os testes negativos. Fonte: comentários do `invariants.yml` |
| **`--squash` proibido** | Escapa do predicado que decide se a auditoria ainda é porta. Fonte: WORKFLOW.md |

## Candidatas — observadas na adoção, pendentes de confirmação do operador

- `AGENTS.md` é uma cópia envelhecida do CLAUDE.md (cita `~/.Codex/agents/` e
  a versão antiga da seção de ground truth, anterior à decisão da Fase 5).
  Intencional (snapshot para outro harness) ou drift a corrigir?
- `.claude/settings.local.json` versiona allowlist com URLs de banco locais
  (credencial declaradamente descartável). Intencional?

Confirmada qualquer uma como intencional → sobe para a tabela com a fonte.
