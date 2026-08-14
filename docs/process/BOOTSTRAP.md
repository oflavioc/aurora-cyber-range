# Bootstrap da implementação

Este documento é o roteiro de **partida da implementação**: como preparar o ambiente e entregar a Fase 0. Não é a apresentação do projeto — essa é o [`README.md`](../../README.md) na raiz.

*(Chamava-se `README_FIRST.md` na raiz. Renomeado para não conviver com o `README.md` de apresentação, que é outra coisa: um é bootstrap de implementação, o outro é o que alguém lê ao abrir o repositório.)*

Extraia este bundle **na raiz** de `C:\Projetos\aurora-cyber-range`.

## Passo a passo

1. Copie a especificação revisada para `docs/spec/` — os 10 arquivos (`00`–`09` + `KICKOFF_PROMPT.md`).
2. `bash bootstrap.sh` no Git Bash. Ele valida o ambiente e instala o auditor em escopo de usuário. **Não commita, não faz push, não cria tag.**
3. Abra o Claude Code com `claude --permission-mode default` e aceite o diálogo de confiança do workspace na primeira vez. Sem isso, os hooks de projeto em `.claude/settings.json` não valem.
4. Entregue a Fase 0: implementar os **seis** verificadores em `tools/`. Nada além disso.
5. Rode as verificações de `docs/process/PHASE_0_CHECKLIST.md`, incluindo `python scripts/phase0_negative_tests.py`.
6. Só quando tudo passar: `bash finalize_phase0.sh`. Ele commita, publica, espera o CI e aplica branch protection — e **para antes da tag**, imprimindo os comandos dos dois PRs descartáveis dos itens 10 e 11 da DoD. A tag `spec-v1.0` só sai numa segunda invocação explícita, `bash finalize_phase0.sh --dod-10-11-verificados`, que é a afirmação do operador de que executou os dois PRs e viu o `spec_freeze` reprovar nos dois.
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
