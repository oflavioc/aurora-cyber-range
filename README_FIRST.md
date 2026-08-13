# Comece por aqui

Extraia este bundle **na raiz** de `C:\Projetos\aurora-cyber-range`.

## Passo a passo

1. Copie a especificação revisada para `docs/spec/` — os 10 arquivos (`00`–`09` + `KICKOFF_PROMPT.md`).
2. `bash bootstrap.sh` no Git Bash. Ele valida o ambiente e instala o auditor em escopo de usuário. **Não commita, não faz push, não cria tag.**
3. Abra o Claude Code com `claude --permission-mode default` e aceite o diálogo de confiança do workspace na primeira vez. Sem isso, os hooks de projeto em `.claude/settings.json` não valem.
4. Entregue a Fase 0: implementar os **seis** verificadores em `tools/`. Nada além disso.
5. Rode as verificações de `docs/process/PHASE_0_CHECKLIST.md`, incluindo `python scripts/phase0_negative_tests.py`.
6. Só quando tudo passar: `bash finalize_phase0.sh`. É o único script que commita, publica, espera o CI, aplica branch protection e — por último — cria `spec-v1.0`.
7. Rode `/doctor` no Claude Code depois do primeiro commit.

## O que fica fora do repositório, e por quê

O `checkpoint-auditor` e seu hook `readonly_bash.py` são instalados em `~/.claude/`, não versionados aqui.

Hooks de frontmatter de subagente de **projeto** só rodam depois que você aceita o diálogo de confiança da pasta que contém o arquivo do agente. O worktree de auditoria é outra pasta; sem aceitar, o Claude Code pula os hooks silenciosamente e registra só no debug log — o auditor ficaria com Bash irrestrito exatamente na operação em que deveria estar mais contido.

E há a razão mais forte: um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit.

O `spec-guardian` e o `scenario-designer` continuam versionados no projeto, porque atuam dentro dele e devem evoluir junto com as regras que aplicam.

## Ordem de defesa

| Camada | Velocidade | Alcance | Limite |
|---|---|---|---|
| Hooks | segundos | dentro da sessão do Claude Code | não pega commit feito fora dela |
| CI | minutos | todo push e PR | não pega teste que passa sem provar o requisito |
| `checkpoint-auditor` | ~10 min | requisito × implementação | não é determinístico |

Nenhuma substitui as outras.

## Comandos do dia a dia

```bash
# implementar uma fase
git checkout -b fase-1-contratos
claude --permission-mode default

# auditar (após commit candidato, working tree limpo)
bash scripts/start_checkpoint_audit.sh 1

# abrir o PR
gh pr create --title "fase-1: contratos e esqueleto"
```
