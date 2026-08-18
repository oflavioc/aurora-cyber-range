# AURORA CYBER RANGE — Instruções permanentes

## Autoridade

`docs/spec/00_MASTER_SPEC.md` é a autoridade normativa deste projeto.

Em conflito entre documentos, o MASTER_SPEC prevalece. Em conflito entre dois documentos não-master, **pare e pergunte** — não resolva por inferência.

## Disciplina de leitura

**Nunca carregue toda a especificação de uma vez.** Antes de cada fase, leia exatamente:

1. `docs/spec/00_MASTER_SPEC.md`
2. `docs/spec/09_EVENT_MODEL.md`
3. O documento da fase, conforme `docs/spec/07_IMPLEMENTATION_PHASES.md`
4. Os critérios daquela fase em `docs/spec/06_ACCEPTANCE_TESTS.md`

Leia `05_SECURITY_REQUIREMENTS.md` sempre que a fase tocar execução, dados, evidências, telemetria, autenticação ou deploy.

## A especificação é imutável durante a implementação

Se o código não bate com a spec, **o código está errado**. Nunca edite `docs/spec/` para acomodar uma implementação.

Se a spec estiver de fato errada, pare, explique, crie uma branch `spec-change/<slug>` e abra um PR separado com título iniciado por `spec-change:` — com aprovação humana antes de qualquer código. Alterar spec e código no mesmo PR é proibido.

## Restrições inegociáveis

`docs/spec/05_SECURITY_REQUIREMENTS.md` não admite flexibilização silenciosa.

Nenhum exploit, malware, ransomware funcional, criptografia real de arquivo como efeito de ataque, movimentação lateral, payload ofensivo, backdoor ou vulnerabilidade intencional. Todos os efeitos de incidente são simulados por estado.

**Criptografia legítima da aplicação não é proibida.** JWT, hashing, TLS e mecanismos equivalentes podem usar bibliotecas criptográficas quando forem necessários à segurança normal da aplicação. A proibição é de comportamento ofensivo/efeito de ataque funcional, não de imports de crypto.

## Invariantes arquiteturais

Estas quatro regras têm hook e teste de CI:

1. `range-core/` **não importa nada** de `domains/`
2. Nenhuma string literal de nome de flag fora dos geradores de constante
3. Nenhum `event_type` fora do catálogo em `contracts/events.schema.yaml`
4. Nenhum evento emitido carrega `objective_ids` — o binding evento→objetivo é feito na projeção

Hook = feedback rápido. CI = gate real. Auditor = valida se o teste realmente prova o requisito.

## Quatro camadas de verdade

Nunca confunda:

1. `ground truth`
2. evidência observável
3. crença/declaração do participante
4. avaliação do avaliador

Declaração do participante nunca altera ground truth. Métrica de verificação nunca é calculada apenas a partir de declaração.

## Rollback

Rollback atua apenas sobre **estado de simulação**. Ações de participante, consultas, submissões, declarações, comunicação, auditoria e avaliações permanecem append-only.

Todo rollback gera evento explícito e novo `simulation_epoch`. Nunca apague história para "voltar no tempo".

## Fluxo por fase

Uma fase = um branch = um PR.

```text
git checkout -b fase-<n>-<slug>
# gravar a âncora em docs/process/phase_anchors.tsv — sem ela a auditoria recusa
# implementar
# rodar testes de aceitação
# criar commit candidato
bash scripts/start_checkpoint_audit.sh <n>
# corrigir BLOCKERs e HIGHs
# novo commit candidato e nova auditoria
gh pr create
gh pr merge --rebase        # REBASE. `--squash` é proibido — WORKFLOW.md
```

A auditoria formal usa contexto fresco e um worktree fixado no commit candidato.

A âncora é o commit em que a branch da fase nasceu, e ela existe porque o
predicado que decide se a auditoria ainda é **porta** — e não laudo — não
consegue derivar esse ponto do grafo. Âncora ausente **recusa**; `--squash`
escapa do predicado e por isso é proibido. Os dois estão em
`docs/process/WORKFLOW.md`.

O `checkpoint-auditor` vive em `~/.claude/agents/`, **fora deste repositório**. Isso é deliberado: hooks de frontmatter de subagente de projeto só rodam depois do diálogo de confiança da pasta — o que falharia no worktree de auditoria — e um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit.

Nas fases marcadas ⏸ em `07_IMPLEMENTATION_PHASES.md`, pare e apresente antes de prosseguir.

Uma fase só está concluída quando **todos** os itens da Definition of Done passam. Item inviável → pare e explique, não contorne.

## Paralelismo

Não paralelize implementação antes da Fase 8. Fases 1–7 compartilham contratos e são sequenciais. A partir da Fase 8, siga `docs/process/WORKFLOW.md`.

## Scenario designer

O `scenario-designer` pode ler o repositório, mas só pode escrever em `scenarios/`. Hooks específicos aplicam essa restrição; não tente contorná-los.

## Ground truth e GM notes

**Este repositório é público.** A versão anterior desta seção dizia "repositório privado" e instruía a mover os artefatos de gabarito *antes* de uma publicação futura. A publicação já ocorreu, e a instrução ficou apontando para uma condição que não existe mais.

`ground_truth.yaml` e `GM_NOTES.md` são fontes de facilitação e de máquina: quem os lê antes do exercício tem o gabarito. Em repositório público, versioná-los entrega o gabarito junto com o motor.

Enquanto o destino definitivo não estiver decidido, vale a regra restritiva:

- **Não versione `ground_truth.yaml` nem `GM_NOTES.md` aqui.** Hoje nenhum existe — `scenarios/` está vazio, e o primeiro pack é entregável da Fase 7.
- Eles seguem excluídos de imagens, bundles, APIs e exports destinados a participantes. Isso é `05_SECURITY_REQUIREMENTS.md` §6 e não depende da visibilidade do repositório.
- Exemplo de pack **sanitizado** — sem gabarito e sem notas de GM — é permitido, e é o que torna a fronteira pública demonstrável em vez de apenas declarada.

**Pendência aberta, e ela é do operador:** onde vivem os artefatos privados quando o primeiro pack existir — repositório privado separado, submódulo, ou `scenarios/` fora do Git. A decisão vence no commit em que o primeiro `ground_truth.yaml` for escrito, e não antes.

## Secrets

Nunca leia, edite ou versione `.env`, `.env.local`, `.env.*.local` ou `secrets/`. O projeto aplica deny rules para esses caminhos. `.env.example` é permitido e deve conter apenas placeholders.

## Modo de permissão

Este projeto desabilita Auto Mode em `.claude/settings.json`. Use `default`/Manual para implementação e Plan quando quiser apenas análise.

## Idioma

Inglês: identificadores, tabelas, colunas, endpoints, logs, nomes de flag e de evento.

Português do Brasil: interface, dados sintéticos, cenários, rubricas, documentação, commits.

## Nunca commitar

`.env`, credenciais, tokens, chaves privadas, dumps de banco ou qualquer arquivo com dado real/não sintético.

Evidência gerada em `scenarios/**/evidence/` também fica fora do Git: é projeção determinista de `ground_truth.yaml` + `RANDOM_SEED` e se reconstrói com `range-cli evidence build`.
