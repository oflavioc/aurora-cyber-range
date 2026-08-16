# Processo de trabalho — AURORA CYBER RANGE

## Fase 0 — Specification Freeze

Só documentação normativa, schemas, agentes, hooks, CI e tooling de governança. Nenhuma aplicação.

A ordem é deliberadamente rígida:

```text
bootstrap.sh
    ↓
seis verificadores + testes negativos
    ↓
commit/push
    ↓
CI verde
    ↓
branch protection confirmada
    ↓
spec-v1.0
```

`bootstrap.sh` **não** commita, não faz push e não cria tag. `finalize_phase0.sh` só cria a tag depois que CI e branch protection forem comprovados.

A partir de `spec-v1.0`, a especificação é imutável durante a implementação. Alteração exige branch `spec-change/<slug>` e PR próprio com título `spec-change:`, sem código junto e com aprovação humana.

## Ciclo por fase

```text
git checkout -b fase-<n>-<slug>
git rev-parse HEAD                      # a ÂNCORA: onde a fase começa
# escrever a linha `<n><TAB><sha><TAB><descrição>` em docs/process/phase_anchors.tsv
claude --permission-mode default
# implementar e testar
git add -A
git commit -m "fase-<n>: checkpoint candidate"
bash scripts/start_checkpoint_audit.sh <n>
# corrigir BLOCKER/HIGH, criar novo commit e reauditar
gh pr create --title "fase-<n>: <descrição>"
gh pr merge --rebase                    # REBASE. Nunca --squash. Ver abaixo
```

O auditor não corrige. Ele reporta e emite PASS/FAIL. Qualquer BLOCKER é FAIL.

### A âncora, e por que sem ela a auditoria recusa

`scripts/check_audit_base.py` responde *"a auditoria desta fase ainda é porta?"*, e
a propriedade é: **nada do trabalho da fase pode já estar na branch default**. Isso
exige saber onde a fase começou, e esse ponto **não é derivável do grafo** —
`git merge-base` é exatamente o valor que se corrompe quando parte da fase já foi
mergeada. A âncora é a única entrada que o predicado não infere.

**Âncora ausente recusa a auditoria.** Não há degradação para "ok": não saber onde
a fase começou é o caso em que não se pode afirmar que ela não foi mergeada. Os
dois predicados anteriores degradaram para "ok" quando não sabiam — o primeiro
entregando base vazia, o segundo perguntando só se o candidato estava contido na
base — e cada um custou uma auditoria que parecia gate e não era.

**Rebase move a âncora**, e isso é verdade e não inconveniência: o ponto de
bifurcação muda mesmo. Regrave a linha no mesmo commit do rebase; o verificador
recusa com essa leitura impressa entre as duas possíveis.

### Rebase, nunca squash, no merge de branch de fase

**Regra:** o merge de uma branch de fase é `--rebase` (ou fast-forward). **`--squash`
é proibido.**

O motivo é mecânico, e não estético. O predicado da base tem duas metades:
topologia contra a âncora, e conteúdo por identidade de patch. O squash é o único
caminho que escapa das duas ao mesmo tempo — ele reescreve N patches num só, então
os patch-ids individuais deixam de casar; a âncora continua sendo o merge-base
porque a identidade mudou; e se a branch andar depois do squash, o diff não é
vazio. As duas metades passam, e o conteúdo da fase está em `main`.

Isto está declarado em `scripts/check_audit_base.py` como furo conhecido — **furo
declarado vale mais que gate que mente**. E a regra mora aqui, e não só na
pendência que a descobriu, porque **quem clica é o operador, e a pendência não
está aberta na hora do clique**.

Rebase e fast-forward preservam identidade de patch: com eles, o mesmo predicado
que deixa o squash passar pega tudo o mais.

## Por que o auditor formal usa launcher de worktree

O objetivo é garantir simultaneamente:

- contexto fresco;
- filesystem descartável para efeitos colaterais de testes;
- commit auditado imutável durante a revisão;
- comparação reproduzível contra `main`.

O launcher cria um worktree **explicitamente a partir do `HEAD` candidato** e então inicia `claude --agent checkpoint-auditor` nele. Isso evita depender do worktree automático do frontmatter, cujo ponto de partida pode ser a branch default e não a branch candidata.

O agente não recebe ferramentas `Write`/`Edit`. Bash passa por allowlist textual. Essa combinação preserva a **separação de papéis** — impede que o auditor corrija por acidente em vez de reportar. Ela não contém adversário, e isso é declarado, não omitido: o hook decide por casamento textual, não por análise sintática de shell, e sua superfície é enumerada em `scripts/phase0_negative_tests.py` nas duas direções — escrita conhecida e não bloqueada, e leitura legítima bloqueada por engano (`PHASE_0_CHECKLIST.md` §Definition of Done, item 4, condições c e e).

**Bloqueio indevido também é defeito.** Um auditor que não consegue rodar a prova central audita por inferência de leitura de código, e continua emitindo veredito enquanto isso — foi a lição do H4 da primeira auditoria da Fase 0. Por isso o item 4(e) trata falso bloqueio novo como finding, e não como inconveniência.

A integridade do repositório repousa em branch protection com `enforce_admins`, no job `spec_freeze` e nos seis verificadores — nenhum deles alcançável pelo hook do auditor. Qualquer sujeira incidental de teste **dentro da árvore** morre com o worktree temporário.

> **A exceção, declarada — P2-18.** A frase acima prometia contenção total, e a promessa era meio verdadeira. `tests/mutation_harness.py` e os `*_probes.py` escrevem a fonte mutada em `tempfile.TemporaryDirectory()`, que fica **fora do worktree**: o diretório é autolimpante e o alvo não é escolhido por quem roda, mas ele não morre com o worktree — morre com o processo.
>
> Não é escrita deliberada do auditor, e o hook não a intercepta: acontece dentro de um `python -m unittest` já autorizado. **`tempfile` é o mecanismo certo** — plantar mutação dentro da árvore auditada a deixaria suja durante a execução, que é pior —, e o que estava errado era a frase.
>
> **Contenção real, então, são duas afirmações e não uma:** nada escrito *na árvore* sobrevive ao worktree, e nada escrito *fora dela* sobrevive ao processo. A segunda é mais fraca, e está dita porque é mais fraca.
>
> **A stack efêmera da auditoria é da mesma família.** Desde o fechamento da P2-19, o lançador sobe Postgres e Redis descartáveis e exporta `AURORA_TEST_DATABASE_URL`/`AURORA_TEST_REDIS_URL` — os testes **escrevem** neles. Portas próprias, sem volume, e `docker compose down` ao final: é escrita real, fora do repositório, com tempo de vida da auditoria. Apontar para o compose do projeto truncaria o banco de desenvolvimento.

## Scenario designer

O `scenario-designer` possui uma competência diferente da engenharia de aplicação e pode editar apenas `scenarios/`.

A restrição é técnica, não apenas textual:

- `scenario_scope.py`: bloqueia Write/Edit fora de `scenarios/`;
- `scenario_bash.py`: permite apenas `range-cli scenario validate|lint|dryrun`, `git diff -- scenarios/...` e `git status --short`.

`ground_truth.yaml` e `GM_NOTES.md` são versionados no repositório privado. Eles nunca chegam a imagem, API, bundle ou export de participante.

## Paralelismo — não antes da Fase 8

Fases 1 a 7 são estritamente sequenciais: contratos → engine → API → vertical slice → objetivos → pacote. Worktree paralelo nessa etapa tende a fragmentar justamente os contratos que precisam permanecer coerentes.

A partir da Fase 8, três frentes podem ser separadas:

| Worktree | Escopo |
|---|---|
| `wt-web` | academus-web completo e dashboards por persona |
| `wt-evidence` | projeção de fatos e telemetry-forwarder |
| `wt-external` | federated-identity, mec-gateway, stub prontus |

Cada frente deve tocar diretórios claramente definidos e reconvergir antes da Fase 10.

## Por que o auditor não mora no repositório

Duas razões, e a segunda importa mais:

1. **Mecânica.** Hooks de frontmatter de subagente de *projeto* só rodam depois que você aceita o diálogo de confiança da pasta que contém o arquivo do agente. O worktree de auditoria é outra pasta; sem essa aceitação o Claude Code pula os hooks silenciosamente e registra apenas no debug log. O `readonly_bash.py` simplesmente não rodaria.

2. **Integridade.** Um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit. Definição em `~/.claude/agents/` fica fora do alcance do código sob revisão.

O `scenario-designer` e o `spec-guardian` continuam no projeto, porque escrevem ou leem dentro dele e são versionados junto com as regras que aplicam.

## Revisão adversarial de segunda camada

O `checkpoint-auditor` oferece o ganho principal: contexto fresco, spec + diff + saída real de teste, sem raciocínio da implementação.

Um segundo fornecedor/modelo pode ser usado nos checkpoints ⏸ para reduzir viés específico de modelo, mas é camada adicional. Não substitui o auditor nem o CI.

## Ordem de defesa

1. **Hook** — feedback em segundos dentro da sessão; pega violações óbvias.
2. **CI** — gate real por AST/contrato; pega violações feitas dentro ou fora do Claude Code.
3. **Auditor** — verifica se o teste realmente prova o requisito e se a semântica da implementação corresponde à spec.

Nenhuma camada substitui outra.

## Auto Mode e secrets

O usuário pode ter Auto Mode configurado globalmente. Este projeto define `permissions.defaultMode = default` e `disableAutoMode = disable` em `.claude/settings.json`.

Também existem deny rules para `.env`, variantes locais e `secrets/`. `.env.example` continua disponível e deve conter apenas placeholders.

## GitHub / branch protection

`spec_freeze` roda apenas em `pull_request`. Isso é intencional: no primeiro push não existe `pull_request.base.sha`, nem título de PR.

A branch protection exige **quatro** contexts:

| Context | O que guarda | Dependência |
|---|---|---|
| `arquitetura` | os quatro invariantes arquiteturais, mais o teste negativo que prova que os seis verificadores reprovam | nenhuma — stdlib |
| `spec_freeze` | spec e código não mudam no mesmo PR; alteração em `docs/spec/` exige título `spec-change:` | nenhuma — `git` |
| `seguranca` | restrições funcionais de `05_SECURITY_REQUIREMENTS.md` e faixas de dado sintético | nenhuma — stdlib |
| `contratos` | os exemplos dos seis contratos, e o teste negativo que prova que o executor reprova | instala do `pyproject.toml` |

Eram três até a Fase 1. `contratos` é **job separado** porque é o único que instala dependência: os outros três rodam sem `pip install`, e um gate que depende da aplicação que ele julga deixa de ser gate.

**Job separado e context obrigatório são coisas independentes.** Acrescentar `contratos` à lista de required status checks não faz `arquitetura` instalar nada — o isolamento continua intacto. Confundir as duas coisas custaria um gate que roda, reporta e **não bloqueia merge**: um PR com fixture quebrada passaria com o job vermelho.

**Ordem de aplicação.** Um status check só pode ser exigido depois de ter aparecido em pelo menos um run. Logo, `contratos` entra na branch protection **depois do merge do PR que o cria**, não antes.

Se a API de branch protection não estiver disponível para o plano/permissão do repositório, a fase não deve ser declarada concluída até a proteção equivalente ser configurada e comprovada.

## Windows

Os hooks são Python para funcionar em Git Bash e PowerShell, desde que `python` esteja no PATH. Os scripts `.sh` devem ser executados em Git Bash.

Depois do primeiro commit e novamente após qualquer alteração em `.claude/`, rode `/doctor`.

---

## Árvore de trabalho compartilhada

Operador e agente trabalham no **mesmo clone**, e `HEAD` é estado global. Um `gh pr merge --delete-branch` apaga a branch local e troca `HEAD`; um `checkout` ou `pull` reescreve arquivos sob uma leitura em curso. Nenhum dos dois é erro isolado — é corrida.

**Aconteceu duas vezes em 15/08/2026:** um commit do agente foi parar em `main` local porque `HEAD` se moveu durante a operação, e um arquivo apareceu modificado e voltou ao normal segundos depois.

### O guarda de branch

`user-scope/hooks/pre-commit` recusa commit direto na branch default. `bootstrap.sh` o instala em `.git/hooks/`, e o harness prova as três direções: bloqueia na default, libera em branch de trabalho, e **é contornado por `--no-verify`**.

**É guarda local, não gate.** Protege este clone, não o repositório: quem clonar sem rodar o `bootstrap.sh` não o tem, e o bypass existe por desenho — hook de cliente é contornável, e isso não é defeito a corrigir. A proteção real de `main` continua sendo a branch protection, com os quatro required status checks e `enforce_admins`.

**O que motivou mecanizar não foi o erro, foi a detecção.** `CLAUDE.md` já instruía a criar branch antes de commitar na default; a instrução existia e não segurou. E o caso só apareceu porque alguém leu `[main d9ec0de]` na saída do `git commit` — detecção por sorte não é detecção. É a mesma distinção entre regra e propriedade que a §1.6 do registro da Fase 1 estabelece: instrução é regra; hook é impedimento.

### A convenção de anúncio

**O hook não impede a corrida.** Ele olha para onde o commit vai cair; se `HEAD` se mover no meio de uma *leitura*, ele não vê nada. Mecanismo nenhum alcança essa parte, então ela é convenção:

- **O agente anuncia antes de commitar** quando o operador pode estar operando a árvore.
- **O operador avisa antes de `merge`, `checkout`, `pull` ou `switch`** enquanto o agente trabalha.
- **Na dúvida, verificar `git branch --show-current` e `git status` antes de agir** — os dois são baratos e não mutam nada.

Um worktree separado eliminaria a condição, e foi **descartado**: o `start_checkpoint_audit.sh` fixa um caminho em `.aurora-worktrees/` e a confiança de workspace do Claude Code é por caminho. Um segundo worktree permanente exigiria reescrever o fluxo de auditoria que a Fase 0 fixou em dezenove rodadas, e a corrida é rara o suficiente para conviver.
