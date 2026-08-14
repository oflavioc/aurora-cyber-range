# Fase 0 — Specification Freeze

Nenhum código de aplicação, `docker-compose` ou migration. Scripts de suporte, hooks, CI e verificadores são permitidos porque são parte do mecanismo de governança da Fase 0.

## Entregáveis

- [ ] `docs/spec/` com 00–09 + `KICKOFF_PROMPT.md`
- [ ] `CLAUDE.md` na raiz
- [ ] `.claude/agents/` com `spec-guardian` e `scenario-designer`
- [ ] `.claude/hooks/` com `check_architecture.py`, `scenario_scope.py`, `scenario_bash.py`
- [ ] `scripts/audit_report.py` — captura do relatório de auditoria, invocada pelo launcher
- [ ] `~/.claude/agents/checkpoint-auditor.md` e `~/.claude/hooks/readonly_bash.py` instalados pelo `bootstrap.sh` (escopo de usuário, fora do repositório)
- [ ] `.claude/settings.json` com hooks, Manual/default e deny de secrets
- [ ] `.github/workflows/invariants.yml`
- [ ] `tools/` com os **seis** verificadores invocados pelo CI
- [ ] `scripts/phase0_negative_tests.py`
- [ ] `scripts/start_checkpoint_audit.sh`
- [ ] `.gitignore`
- [ ] `bootstrap.sh` e `finalize_phase0.sh`
- [ ] `docs/process/WORKFLOW.md`

## Os seis verificadores de `tools/`

O bundle não os implementa deliberadamente. Eles são a primeira tarefa real do Claude Code na Fase 0.

| Script | O que verifica | Como |
|---|---|---|
| `check_core_boundary.py` | `range-core/` não importa de `domains/` | AST: `Import`, `ImportFrom`, `importlib.import_module`, `__import__` com literal |
| `check_contract_literals.py` | Nenhum literal de flag ou `event_type` fora dos pontos autorizados | AST + leitura dos contratos/catálogos; não depender só de regex |
| `check_event_envelope.py` | `objective_ids` ausente do caminho de emissão | AST + caminho/semântica de emissão |
| `check_security_constraints.py` | Restrições funcionais de `05_SECURITY_REQUIREMENTS` §1 | AST/heurística de comportamento proibido: `eval`, `exec`, `shell=True`, execução arbitrária, criptografia funcional de arquivos como efeito de ataque. **Não proibir import de biblioteca criptográfica por si só** |
| `check_synthetic_data.py` | IPs/domínios/identificadores fora das faixas sintéticas permitidas | análise de seed, evidência e fixtures; ranges de documentação/exemplo |
| `codegen.py --check` | Constantes Python/TypeScript sincronizadas com contratos | compara fonte canônica e artefatos gerados; em `--check`, nunca reescreve |

**AST no CI; regex apenas no hook de feedback rápido.** O CI precisa enxergar import dinâmico/alias e outros casos que regex pode perder.

## Interfaces obrigatórias

Todos os verificadores devem:

1. retornar `0` para árvore válida;
2. retornar valor diferente de `0` para violação;
3. imprimir caminho e motivo da violação;
4. usar apenas stdlib Python na Fase 0, para o CI não depender da aplicação ainda;
5. não modificar arquivos quando executados em modo de verificação;
6. ser determinísticos.

`codegen.py --check` deve ser estritamente read-only. A geração efetiva poderá usar outro modo/flag em fase posterior.

## Teste negativo obrigatório

Rode:

```bash
python scripts/phase0_negative_tests.py
```

Esse harness planta violações temporárias **fora dos verificadores** e exige que cada um falhe. Ele testa os seis, inclusive `codegen.py --check`, e limpa os probes ao terminar.

O princípio é obrigatório:

> Um verificador que nunca falhou contra uma violação plantada não é um verificador; é um script que sai com zero.

## Smoke tests de hooks

```bash
# Hook arquitetural deve bloquear
printf '%s\n' '{"cwd":"'"$(pwd)"'","tool_input":{"file_path":"range-core/x.py","content":"from domains.academus import Y"}}' \
  | python .claude/hooks/check_architecture.py
echo "exit=$?"  # espera 2

# Auditor não pode executar escrita deliberada
printf '%s\n' '{"tool_input":{"command":"rm -rf range-core"}}' \
  | python ~/.claude/hooks/readonly_bash.py
echo "exit=$?"  # espera 2

# Scenario designer não pode escrever fora de scenarios/
printf '%s\n' '{"cwd":"'"$(pwd)"'","tool_input":{"file_path":"range-core/nope.py","content":"x=1"}}' \
  | python .claude/hooks/scenario_scope.py
echo "exit=$?"  # espera 2
```

## Ordem correta de fechamento

Nunca tagueie antes de provar o CI.

```text
bootstrap
  ↓
implementar 6 verificadores
  ↓
testes positivos + negativos
  ↓
commit da Fase 0
  ↓
push main
  ↓
CI verde
  ↓
branch protection confirmada
  ↓
spec-v1.0
```

Use `bash finalize_phase0.sh` para executar essa ordem. Se branch protection falhar, a Fase 0 permanece incompleta e a tag não é criada.

## Definition of Done

- [ ] Os seis verificadores liberam árvore limpa
- [ ] Os seis detectam as violações externas de `scripts/phase0_negative_tests.py`
- [ ] Hook bloqueia import de `domains/` em `range-core/`, edição de `docs/spec/` e literal de flag
- [ ] Hook do auditor bloqueia escrita deliberada e libera testes/verificadores de leitura
- [ ] Hook do scenario-designer bloqueia Write/Edit fora de `scenarios/` e Bash fora da allowlist
- [ ] `ground_truth.yaml` e `GM_NOTES.md` **não** estão no `.gitignore`
- [ ] `.env`/secrets estão negados em `.claude/settings.json`
- [ ] Auto Mode está desabilitado para este projeto
- [ ] Primeiro push de `main` deixa `arquitetura` e `seguranca` verdes; `spec_freeze` é PR-only
- [ ] PR descartável confirma: `spec_freeze` falha se spec e código mudam juntos
- [ ] PR descartável confirma: alteração só de spec exige título `spec-change:`
- [ ] Branch protection em `main` exige `arquitetura`, `spec_freeze`, `seguranca`
- [ ] `spec-v1.0` criada **depois** de CI + branch protection
- [ ] `/doctor` sem apontamentos relevantes

## Auditoria das fases seguintes

O checkpoint formal não usa worktree automático do frontmatter. Depois de criar o commit candidato:

```bash
bash scripts/start_checkpoint_audit.sh <fase>
```

O launcher cria worktree temporário fixado exatamente no `HEAD` candidato e inicia um contexto fresco com `checkpoint-auditor`.
