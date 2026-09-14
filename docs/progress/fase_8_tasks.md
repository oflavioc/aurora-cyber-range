# Tarefas — fase-8-web-completo

> Fase 3 (SDD) · dono: tech-lead · ids `[TNNN]` permanentes; a última wave é
> sempre validação. Consome `docs/progress/fase_8_plan.md`.
>
> Tipos (R3): `feature`/`fix` exigem **RED provado e commitado**;
> `refactor`/`doc`/`chore` não. **Um módulo por delegação** — dois donos nunca
> no mesmo arquivo na mesma wave. `[P]` = paralelizável na wave (delegações na
> mesma mensagem, arquivos disjuntos).
>
> Papéis (Onda 2): `core-engineer` = `range-core/`; `data-engineer` =
> `domains/academus/` (adapter, flags, projeções de domínio); `ui-engineer` =
> `range-core/web/`; `build-engineer` = contratos, codegen, superfícies, pins;
> `qa-engineer` = gates. Enquanto os papéis não são instanciados, o orquestrador
> veste cada chapéu declarando qual.

## Wave 1 — Contratos e registros (contrato antes do consumidor)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T801 | 1 | build-engineer | feature | | Fechar o `$def` de `continuity_action_taken` em `contracts/events.schema.yaml` (enum das 7 ações + `effects:[{flag,value}]` + `cost`/`tradeoff`); **regerar** `contracts/generated/events.{py,ts}` por `tools/codegen.py`; `codegen.py --check` verde | `codegen.py --check`, `check_event_envelope.py` (INV-6: sem `objective_ids`) |
| T802 | 1 | data-engineer | feature | [P] | Declarar as flags novas de efeito de continuidade em `domains/academus/flags.yaml` (as que D3 aprovar) + regerar `domains/academus/generated/flags.py` | `check_spec_flags.py`, gerador de constantes |
| T803 | 1 | build-engineer | chore | [P] | Declarar as rotas novas nas superfícies: `GET /exam/session-status` e filtros da rota de auditoria em `academus/api_surface.yaml`; `GET /participant/view` e `POST /participant/continuity` em `participant/api_surface.yaml` (status `planejada`) | `check_api_surface.py` (igualdade nas duas direções) |
| T804 | 1 | build-engineer | chore | | Regenerar `.claude/verify/pins.json` (`gen_pins.py`) se algum arquivo pinado mudou em T801–T803 — commit próprio, motivo na mensagem (R8) | stage `baseline` |

## Wave 2 — Gates + RED (autor ≠ implementador; RED commitado)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T805 | 2 | qa-engineer | feature | [P] | Gate item 1: cadência cresce com o minuto de exercício conforme a taxa; determinística (dois minutos iguais → mesmo conjunto), estável no reinício/rollback, monótona no tempo e na taxa; frame TOTAL. Positivo+negativo+adversarial+regressão+mutante. RED commitado | `test_prova_andamento` (novo, namespace Fase 8) |
| T806 | 2 | qa-engineer | feature | [P] | Gate item 2: consulta filtrada (período/usuário/IP/janela/autorização) emite `audit_query_performed` com os filtros e **seta o marcador `auto`** na projeção de objetivos. RED commitado | `test_console_investigacao` |
| T807 | 2 | qa-engineer | feature | [P] | Gate item 3: leitura por persona devolve só a camada `reported`; **nunca** um fato de ground truth (cláusula de isolamento `06` T14); persona não alcança a fatia de outra. RED commitado | `test_reported_isolation` |
| T808 | 2 | qa-engineer | feature | [P] | Gate item 4: cada uma das 7 ações emite `continuity_action_taken` (payload fechado), o fold aplica o efeito de flag e o custo viaja; negativo: ação fora do enum e payload fora do `$def` recusados; **regressão**: projeção `auto/observed` do item 2 intacta. RED commitado | `test_continuidade` |
| T809 | 2 | qa-engineer | chore | | Registrar as 4 suítes novas em `expected_suites.json` com a contagem (R10 §3); nomear o não-executado sem Postgres (R10 §2) | stage `suites` |

## Wave 3 — Backend independente (um módulo por delegação, [P] disjuntos)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T810 | 3 | data-engineer | feature | [P] | `domains/academus/api/prova_andamento.py`: cadência "por minuto" sobre `fracao_do_sujeito` (P4-6). Função pura de `(sujeitos, taxa, minuto)`, `derive_seed`, monótona no tempo. Handler de `GET /exam/session-status` (frame TOTAL) + promover a rota na superfície | T805 |
| T811 | 3 | data-engineer | feature | [P] | `domains/academus/api/continuidade.py`: tabela `action_id → [(constante_de_flag, valor)] + custo` usando `domains/academus/generated/flags.py` (sem literais). Exporta dado puro para injeção; **não** emite nem importa núcleo | T808, T801, T802 |
| T812 | 3 | data-engineer | feature | [P] | Filtros (período/usuário/IP/janela/autorização) no handler da rota de auditoria; carregar no payload de `audit_query_performed` via `registrar_consulta` (P6-7: chama o emissor) | T806 |
| T813 | 3 | core-engineer | feature | [P] | `range-core/participant/reported.py`: projeção da camada `reported` por persona (frame TOTAL, nunca ground truth) + `GET /participant/view` persona-vinculada; promover rota na superfície | T807 |

## Wave 4 — Backend dependente (item 4: núcleo consome a tabela por injeção)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T814 | 4 | core-engineer | feature | | `POST /participant/continuity` na `participant-api`: autoriza persona, valida `action_id` contra a **tabela injetada em `montar()`**, emite `continuity_action_taken`. Fold aplica `state_effect` genericamente lendo `effects[].flag/value` do payload — sem import de `domains/` (INV-4) | T808, T811, T801 |

## Wave 5 — Web fino (INV-7: cliente pinta o payload; INV-10: banner)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T815 | 5 | ui-engineer | feature | [P] | `range-core/web/exam-mode/`: cronômetro, autosave, monitoramento; pinta o frame de `/exam/session-status`. Banner | `test_prova_andamento` (parte web) + `check_banner_de_simulacao.py` |
| T816 | 5 | ui-engineer | feature | [P] | `range-core/web/investigation-console/`: os 5 filtros; pinta o resultado; dispara a consulta que emite o marcador. Banner | `test_console_investigacao` + `check_banner_de_simulacao.py` |
| T817 | 5 | ui-engineer | feature | [P] | `range-core/web/persona-panel/`: **um** módulo parametrizado pela persona; pinta o frame `reported` de `/participant/view`. Banner | `test_reported_isolation` + `check_banner_de_simulacao.py` |
| T818 | 5 | ui-engineer | feature | | Botões das 7 ações de continuidade no `persona-panel`; chamam `/participant/continuity` e pintam o custo/tradeoff devolvido. Banner | `test_continuidade` (parte web) |

## Wave 6 — Validação (sempre a última)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate associado |
|---|---|---|---|---|---|---|
| T819 | 6 | qa-engineer | chore | | Green das 4 suítes + mutante morto por cada gate + regressão congelada intacta (inclui projeção `auto/observed`); `check_web_sem_derivacao.py`, `check_banner_de_simulacao.py` (fonte e bundle) verdes | stages `suites`, `arquitetura`, `seguranca` |
| T820 | 6 | qa-engineer | doc | | Mapa DoD→prova: item 1↦T805, item 2↦T806, item 3↦T807, item 4↦T808 — os quatro nomeados no registro de fase (`06` pula T12→T13; a Fase 8 nomeia suas suítes no namespace da fase) | `check_progress_consistency` |
| T821 | 6 | product-owner | chore | | Aceite de intenção dos 4 itens de DoD; disposição das pendências herdadas materiais desta fase (P4-6, P5-2, P6-7 e as que a §6 lista) | DoD `07` §Fase 8 |

## Notas de dependência

- **Contrato antes do consumidor:** T801 (payload) e T803 (superfícies) antes de
  qualquer implementação que os consuma.
- **Flags antes da tabela:** T802 antes de T811.
- **Tabela antes do endpoint:** T811 antes de T814 (injeção).
- **Endpoint antes da tela:** T810→T815, T812→T816, T813→T817, T814→T818.
- **Gate antes da implementação:** cada gate de Wave 2 viaja no prompt da
  implementação correspondente (R3 §3).
