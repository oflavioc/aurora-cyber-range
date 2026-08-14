# 07 — FASES DE IMPLEMENTAÇÃO

Ordenadas para **reduzir risco**, não por afinidade temática. O vertical slice vem cedo, deliberadamente.

---

## Visão geral

| Fase | Conteúdo | Checkpoint |
|---|---|---|
| 1 | Contratos (flags, eventos, cenário, ground truth, objetivos) + esqueleto | ⏸ |
| 2 | exercise-clock + event store com envelope e epoch + projeção + engine mínimo | ⏸ |
| 3 | academus-api mínimo (auth, 3 entidades, degradação por flag) | seguir |
| 4 | gm-console mínimo + wallboard mínimo + participant-view | ⏸ **VERTICAL SLICE** |
| 5 | Modelo de dados completo + seed + trilha de auditoria com hash | ⏸ |
| 6 | Objetivos + rubricas versionadas + métricas pareadas + calibração + declarações | ⏸ |
| 7 | Pack completo `ransomware-universidade` + branching + range-cli | ⏸ |
| 8 | academus-web completo + dashboards por persona + continuidade | seguir |
| 9 | projeção de fatos: evidence-simulator + telemetry-forwarder unificados | seguir |
| 10 | Assimetria de informação + AAR completo | ⏸ |
| 11 | federated-identity + mec-gateway + ecossistema externo + stub prontus | seguir |
| 12 | Observabilidade + `fraude-academica-express` + documentação | ⏸ |

Nas fases ⏸, parar e apresentar antes de prosseguir.

---

## Template obrigatório por fase

Cada fase se rege por:

```
ENTRY CRITERIA     o que precisa estar pronto antes
OUTPUTS            artefatos produzidos
ACCEPTANCE TESTS   referência a 06_ACCEPTANCE_TESTS.md
DEMO SCRIPT        sequência exata a executar para demonstrar
NON-GOALS          o que explicitamente NÃO fazer nesta fase
DEFINITION OF DONE checklist binária
```

---

## Fase 1 — Contratos e esqueleto

**ENTRY** — nenhum.

**OUTPUTS** — árvore de diretórios; `contracts/` com `state_flags.schema.yaml`, `events.schema.yaml` (catálogo fechado), `scenario.schema.v2.yaml`, `ground_truth.schema.yaml`, `objectives.schema.yaml`, `evidence.schema.yaml`; `domains/academus/flags.yaml` inicial; geradores de constantes Python e TypeScript para flags **e** event types; os **seis** verificadores de `tools/` invocados pelo CI (`01_ARCHITECTURE.md` §2), incluindo `codegen.py` com modo `--check` estritamente read-only; docker-compose; Alembic inicializado.

**NON-GOALS** — nenhuma lógica de negócio, nenhuma tela, nenhum seed.

**DEMO** — `range-cli scenario validate` recusa pack com flag inexistente; import de `domains/` dentro do core falha no CI.

**DONE quando:**
- [ ] Os seis contratos existem e validam exemplos positivos e negativos
- [ ] Constantes tipadas geradas em Python e TypeScript para flags e event types
- [ ] Teste de fronteira core/adapter passa (por AST)
- [ ] `event_type` fora do catálogo é rejeitado
- [ ] Os seis verificadores de `tools/` liberam árvore limpa e cada um falha contra a violação plantada por `scripts/phase0_negative_tests.py`
- [ ] `codegen.py --check` detecta constantes fora de sincronia e não escreve nenhum arquivo
- [ ] `docker compose up` sobe Postgres e Redis
- [ ] `RANDOM_SEED` lido de `.env`

---

## Fase 2 — Clock, eventos, estado, engine mínimo

**ENTRY** — Fase 1 completa.

**OUTPUTS** — exercise-clock com pausa e multiplicador; event store append-only com envelope universal e `truth_layer`; `simulation_epoch`; projeção de simulação; rollback com taxonomia de motivo; inject-engine capaz de carregar pack com 3 injects e aplicar effects.

**NON-GOALS** — branching, objetivos, métricas, telemetria, UI.

**DEMO** — via CLI: carregar pack, disparar A01, ler projeção, rollback, ler projeção restaurada.

**DONE quando:**
- [ ] Todo evento carrega `exercise_time`, `wall_time` e `clock_multiplier`
- [ ] PAUSAR congela o clock e bloqueia disparo agendado
- [ ] Aplicar A01 duas vezes produz projeção idêntica
- [ ] Rollback grava `rollback_performed`, incrementa `simulation_epoch` e reconstrói a projeção sem apagar eventos
- [ ] Evento de `participant_action` da epoch anterior permanece legível e marcado
- [ ] `reason: technical_failure` desconta o intervalo do cálculo de métricas
- [ ] Reconstrução completa da projeção a partir do store roda em < 3 s
- [ ] Flag não declarada impede boot do engine com mensagem clara

---

## Fase 3 — API mínima

**ENTRY** — Fase 2 completa.

**OUTPUTS** — academus-api com JWT, RBAC, três entidades (Aluno, Turma, Nota), e degradação real por flag em pelo menos três endpoints.

**NON-GOALS** — modelo completo, seed em escala, auditoria com hash.

**DONE quando:**
- [ ] `academus.enrollment_offline: true` faz o endpoint de matrícula retornar 503
- [ ] `academus.grades_readonly: true` bloqueia POST de nota com mensagem de negócio
- [ ] RBAC nega acesso cruzado entre perfis
- [ ] Nenhuma string solta de flag no código-fonte (verificado por lint)

---

## Fase 4 — VERTICAL SLICE ⏸

**A fase mais importante do projeto.** Prova a arquitetura ponta a ponta antes de qualquer expansão.

**ENTRY** — Fase 3 completa.

**OUTPUTS** — gm-console mínimo (autenticado, lista de injects, botão de disparo, rollback); wallboard mínimo (dois painéis gerados por taxonomia + índice de saúde); participant-view.

**NON-GOALS** — três papéis de facilitação, social feed, dashboards por persona, BARS, AAR.

**DEMO SCRIPT — executar exatamente esta sequência:**

```
GM clica inject A01
      ↓
engine grava evento e muda projeção
      ↓
API degrada endpoint de matrícula
      ↓
wallboard reage em < 1 s
      ↓
participant-view exibe texto_para_plateia
      ↓
GM clica ROLLBACK
      ↓
estado restaurado; evento de rollback registrado
```

**DONE quando:**
- [ ] A sequência acima roda ponta a ponta sem intervenção manual
- [ ] Wallboard atualiza em < 1 s via WebSocket
- [ ] Refresh do browser no wallboard e no participant-view recupera o estado corrente
- [ ] Reinício do container do engine restaura o exercício a partir do event store
- [ ] Rollback aparece anotado na timeline
- [ ] Índice de saúde institucional é calculado a partir dos `severity_weight` ativos

**Se qualquer item acima falhar, não avance.** É mais barato corrigir aqui do que na Fase 10.

---

## Fase 5 — Dados e auditoria

**OUTPUTS** — modelo completo, `CalendarioAcademico`, `AutorizacaoRetificacao`, seed em escala com bulk insert, trilha append-only com hash encadeado, `GM_NOTES.md` do pack.

**DONE quando:**
- [ ] Seed completo em < 5 min
- [ ] Mesmo `RANDOM_SEED` produz dataset byte-idêntico em duas execuções
- [ ] `UPDATE` e `DELETE` em `audit_trail` falham por trigger e por permissão de role
- [ ] `GET /audit/verify-chain` detecta adulteração induzida em teste
- [ ] Os seis conjuntos da Linha B existem nos volumes especificados
- [ ] `GM_NOTES.md` contém a query de referência que separa indevidos de ambíguos

---

## Fase 6 — Objetivos, rubricas, métricas

**OUTPUTS** — motor de objetivos com binding evento→objetivo na projeção; `observability_hooks.yaml`; biblioteca BARS versionada com 9 competências; métricas pareadas e predicados de verificação; escore de calibração; ações de declaração nos endpoints.

**DONE quando:**
- [ ] Consultar a trilha com filtro de período emite `audit_query_performed`
- [ ] Cada par declaração × verificação é disparável e testado
- [ ] Declaração não altera nenhum valor de ground truth
- [ ] Declaração prematura produz lista de eventos incompatíveis no AAR
- [ ] Pack sem `verification_predicates` não carrega
- [ ] `TTIV` computado por limiar de calibração, não por predicado de mundo
- [ ] Brier calculado só dentro do escopo revisado; lacuna de cobertura em separado
- [ ] Rubrica ausente ou em versão divergente impede carga do pack
- [ ] Divergência ≥ 2 pontos entre avaliadores gera alerta

---

## Fase 7 — Pack completo e branching

**DONE quando:**
- [ ] `range-cli scenario lint` recusa inject sem objetivo e sem `noise: true`
- [ ] `event_type` inexistente em condição de branch é recusado, com posição no arquivo
- [ ] Condição dependente de juízo do facilitador é recusada
- [ ] `branch_policy` do manifesto é aplicada
- [ ] Branch sem `reconverge_at` é recusado
- [ ] `dryrun` percorre todos os caminhos
- [ ] Pack em schema v1 migra automaticamente; v0 é recusado com instrução
- [ ] Fato citado no `GM_NOTES.md` e ausente do `ground_truth.yaml` é recusado

---

## Fase 8 — Web completo

**DONE quando:**
- [ ] Modo "Prova em andamento" perde sessões conforme `lms_session_drop_rate`
- [ ] Console de investigação emite os marcadores automáticos
- [ ] Cada persona vê apenas sua camada `reported`
- [ ] As sete ações de continuidade aplicam efeito mecânico e custo

---

## Fase 9 — Evidência e telemetria

**DONE quando:**
- [ ] Toda fonte é projeção de `fact_id`; nenhum gerador inventa entidade
- [ ] `range-cli evidence verify` valida consistência fato → projeções, dirigido por fato
- [ ] `precursor_events.jsonl` é reproduzível a partir do ground truth; edição manual detectada por hash
- [ ] Telemetria CEF é projeção, não emissão independente
- [ ] Nenhum arquivo contém anexo, binário, IOC real ou domínio roteável
- [ ] Replay respeita o clock de exercício

---

## Fase 10 — Assimetria e AAR ⏸

**DONE quando:**
- [ ] Personas recebem conteúdo divergente conforme `information_distribution.yaml`
- [ ] AAR compara número comunicado com ground truth e marca divergência
- [ ] AAR renderiza epochs separadas com motivo de rollback
- [ ] AAR tem as doze seções de `03_EXERCISE_DESIGN.md` §9
- [ ] Notas do facilitador aparecem rotuladas como qualitativas, separadas das métricas

---

## Fases 11 e 12

Serviços externos, segundo pack, observabilidade e documentação. Nenhum deles bloqueia um exercício real.

---

## Registro de progresso

Ao concluir cada fase, gravar `docs/progress/fase_<n>.md` com: resumo técnico, estrutura de diretórios, endpoints criados, migrations, variáveis de ambiente, itens de DoD com status, pendências e próxima fase.
