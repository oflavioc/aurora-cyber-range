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
- [ ] `scripts/phase0_negative_tests.py` — probes dos seis verificadores (item 2) e probes de hook com as duas listas de defeito afirmado (item 4). Separação em `scripts/hook_guard_tests.py` é pendência registrada (§6 P38)
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

# Auditor: uma das formas de escrita enumeradas no harness
printf '%s\n' '{"tool_input":{"command":"rm -rf range-core"}}' \
  | python ~/.claude/hooks/readonly_bash.py
echo "exit=$?"  # espera 2

# Scenario designer não pode escrever fora de scenarios/
printf '%s\n' '{"cwd":"'"$(pwd)"'","tool_input":{"file_path":"range-core/nope.py","content":"x=1"}}' \
  | python .claude/hooks/scenario_scope.py
echo "exit=$?"  # espera 2
```

**Este bloco não prova o item 4.** Ele exercita um caso; a prova das cinco
condições — inclusive as duas listas de defeito afirmado, a de escrita não
bloqueada em 4(c) e a de falso bloqueio de leitura em 4(e) — é responsabilidade
de `scripts/phase0_negative_tests.py`. E o segundo probe **não é executável pelo
Bash do próprio auditor**: o `rm -rf` dentro do payload JSON casa como comando de
escrita e o hook bloqueia o teste que o testa (`docs/progress/fase_0.md` §6 P23).
Rode-o de uma sessão comum.

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

Use `bash finalize_phase0.sh` para executar essa ordem. Ele **para antes da tag** e imprime os comandos dos dois PRs descartáveis dos itens 10 e 11; a tag só sai numa segunda invocação explícita, `bash finalize_phase0.sh --dod-10-11-verificados`. Se branch protection falhar, a Fase 0 permanece incompleta e a tag não é criada.

## Definition of Done

- [ ] Os seis verificadores liberam árvore limpa
- [ ] Os seis detectam as violações externas de `scripts/phase0_negative_tests.py`
- [ ] Hook bloqueia import de `domains/` em `range-core/`, edição de `docs/spec/` e literal de flag
- [ ] **Item 4 — Separação de papéis do auditor**

  a) O agente `checkpoint-auditor` não declara `Write` nem `Edit` em suas `tools`.

  b) O hook `readonly_bash.py` bloqueia as formas de escrita enumeradas em
     `scripts/phase0_negative_tests.py`, e o harness prova cada uma nas duas
     direções.

  c) A superfície aberta é declarada: toda forma de escrita conhecida e não
     bloqueada está listada no harness como defeito afirmado, e o harness reprova
     se qualquer uma passar a ser bloqueada sem atualização da lista. Uma forma só
     pode ser declarada se **nenhuma grafia do seu alvo** escapar do worktree de
     auditoria — provado no harness contra as quatro grafias equivalentes:
     relativa, absoluta, `~` e variável de ambiente. Escrita que alcança o
     worktree principal é finding, não defeito aceito: ela derrota o propósito
     declarado do hook, que é impedir correção acidental, e não apenas conter
     adversário.

     > **Por que a prova é por grafia, e não por contenção.** Um alvo tem
     > infinitas grafias, então "esta escrita fica contida" não é demonstrável
     > por casamento textual — é a mesma indemonstrabilidade que motivou esta
     > reformulação, e ela reapareceu dentro da primeira tentativa de corrigi-la
     > (`docs/progress/fase_0.md` §6 P36, décima auditoria). O que se verifica é
     > **ausência de capacidade de escrita** no comando allowlistado: comando que
     > escreve por posição sai da allowlist, e flag de saída é negada por comando.
     > Declarar contenção sem essa prova é usar a disciplina de declaração para
     > legitimar exatamente o que ela existe para impedir.

  d) Nenhum comando de escrita **não declarado** passa: qualquer forma nova
     encontrada é finding, não defeito aceito.

  e) O hook libera os comandos de leitura e de execução de teste que o auditor
     precisa para medir em vez de inferir. Falsos bloqueios conhecidos estão
     listados em `scripts/phase0_negative_tests.py` como defeito afirmado, pela
     mesma disciplina de (c): defeito documentado que sai do harness vira defeito
     esquecido. Falso bloqueio novo é finding, pela mesma razão de (d) — degrada a
     capacidade de auditar.

  > **Separação de suítes é pendência registrada** (`docs/progress/fase_0.md`
  > §6 P38). Hoje `scripts/phase0_negative_tests.py` responde pelo item 2 *e* pelo
  > item 4, e um verde não distingue qual metade passou. A separação em
  > `scripts/hook_guard_tests.py` está decidida, e adiada para depois de o harness
  > de hook chegar a `main` — separar arquivo que ainda não chegou é ordem errada.

  **Limite declarado.** O hook decide por casamento textual, não por análise
  sintática de shell. Completude não é demonstrável neste desenho — apenas
  refutável, uma via por rodada, o que nove auditorias comprovaram. A proteção da
  integridade do repositório repousa em branch protection com `enforce_admins`, no
  job `spec_freeze` do CI e nos seis verificadores — nenhum deles alcançável pelo
  hook do auditor, e todos demonstrados funcionando nos itens 9 a 13.

  O propósito do hook é impedir que o auditor corrija por acidente em vez de
  reportar, preservando a separação de papéis. Não é conter adversário.

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
