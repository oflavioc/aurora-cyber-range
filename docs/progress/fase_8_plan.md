# Plano — fase-8-web-completo

> Fase 2 (SDD) · dono: tech-lead · desenho técnico dos quatro itens de DoD da
> Fase 8 (`07_IMPLEMENTATION_PHASES.md` §Fase 8). Complementa
> `docs/progress/fase_8.md` (o registro de fase, que carrega a pauta herdada).
> **Este arquivo é desenho, não implementação e não toca `docs/spec/`.**

## 0. DoD e onde cada peça vive

| # | Item de DoD | Peso backend (INV-7) | Web (fino) |
|---|---|---|---|
| 1 | Modo "Prova em andamento" perde sessões conforme `lms_session_drop_rate` | domínio: cadência "por minuto" sobre a queda determinística | tela pinta o frame TOTAL de sessões |
| 2 | Console de investigação emite os marcadores automáticos | domínio: endpoint de auditoria com filtros, já emite `audit_query_performed` | console pinta resultado + filtros |
| 3 | Cada persona vê apenas sua camada `reported` | core: projeção `reported` por persona + rota de leitura | painel por persona pinta o frame |
| 4 | As sete ações de continuidade aplicam efeito mecânico e custo | domínio: tabela ação→efeito; core: endpoint + fold aplica `state_effect` | botões de ação nos painéis |

Regra transversal: **o peso é backend**. Toda derivação é do servidor; o frame
é estado TOTAL, nunca delta; o cliente pinta o payload (INV-7). Banner
"AMBIENTE SIMULADO — DADOS FICTÍCIOS" em toda tela nova (INV-10,
`check_banner_de_simulacao.py`, fonte e bundle).

## Desenho

### Item 1 — Modo "Prova em andamento" (cadência + tela)

- **Estado atual:** `domains/academus/api/degradacao.py` já faz a queda
  proporcional determinística e **sem estado** (`fracao_do_sujeito`, `cai`,
  `Degradador.aplica`). A rota degradada `GET /classes/{class_id}/gradebook`
  (503 proporcional) existe em `domains/academus/api_surface.yaml:279-296`.
- **Falta (P4-6, dono declarado = esta fase, `degradacao.py:72-77`):** a cadência
  *"por minuto"* do `effect_ui`. `degradacao.py` derruba quem cai o exercício
  inteiro; a cadência exige **tempo de exercício como entrada** — o estado que a
  P3-10 tirou de `degradacao.py` de propósito.
- **Módulo novo (dono do estado da cadência):** `domains/academus/api/prova_andamento.py`
  — camada sobre `fracao_do_sujeito`, função pura de `(sujeitos, taxa,
  minuto_de_exercício)`. Propriedades a preservar (as mesmas de `degradacao.py`):
  determinística por `derive_seed` (nunca `hash()`), estável no reinício e no
  rollback, monótona na taxa **e agora monótona no tempo** (minuto N ⊇ minuto
  N-1). Tempo de exercício é **insumo declarado** (relógio de exercício), não
  relógio de parede — R7 §6.
- **Rota nova (domínio):** `GET /exam/session-status` em `academus/api_surface.yaml`,
  devolve o frame TOTAL das sessões (cada sessão com estado `alive`/`dropped`
  no minuto corrente) — INV-7. `flags: [academus.lms_session_drop_rate]`.
- **Tela nova (web fino):** `range-core/web/exam-mode/` (cronômetro, autosave,
  monitoramento de sessões) que pinta o frame. Banner obrigatório.

### Item 2 — Console de investigação (filtros + tela)

- **Estado atual:** `GET /audit/grade-changes` já emite `audit_query_performed`
  (`academus/api_surface.yaml:400-404`, `emissor.py:77-118 registrar_consulta`);
  a projeção `auto`/`observed` existe (`range-core/objectives/projecao.py:61-215`)
  e o hook está em `academus/observability_hooks.yaml:45-48`. **O marcador `auto`
  já é emitido na consulta.**
- **Falta:** os cinco filtros de `02` §7:124 — período, usuário, IP, janela,
  autorização — no endpoint, e o console (UI).
- **Módulo (domínio):** estender o handler da rota de auditoria para aceitar os
  cinco filtros e **carregá-los no payload de `audit_query_performed`** (o
  marcador é o próprio efeito da consulta; P6-7 vigia rota que declara `emite`
  sem chamar emissor — esta chama). Sem novo `event_type` (INV-5).
- **Tela nova (web fino):** `range-core/web/investigation-console/` com os cinco
  filtros; pinta o resultado. Banner obrigatório.

### Item 3 — Camada `reported` por persona (isolação de leitura)

- **Recomendação de fronteira de fase (confirmada na leitura, a ratificar pelo
  proprietário):** a **Fase 8 entrega a ISOLAÇÃO de leitura** — projeção da
  camada `reported` filtrada por persona, sem vazar ground truth (cláusula de
  isolamento de `06` T14; `03` §6:395 "cada persona vê apenas sua camada
  `reported`"). O **conteúdo divergente** de `information_distribution.yaml`
  (subestimativa deliberada, `03` §4) é assimetria da **Fase 10** — T14 está
  rotulado Fase 10. Desenhamos só o lado Fase 8.
- **Estado atual:** o RBAC por persona existe na `participant-api`
  (`range-core/participant/api/app.py:110-135 _persona_autorizada`, 403), mas a
  superfície só **escreve** (nove declarações). A camada `reported` é emitida
  via `truth_layer=reported` (`emissor.py`, constante `CAMADA`). As sete personas
  são vocabulário fechado (`participant/api_surface.yaml:71-78`, `03` §6).
- **Módulo novo (core, dono da projeção):** `range-core/participant/reported.py`
  — projeção que, dada a persona, devolve o frame TOTAL da **camada `reported`
  daquela persona**, provando exclusão de ground truth (nunca lê
  `ground_truth.yaml`, nunca projeta as quatro-verdades acima de `reported`).
  Estado canônico é o event store; a projeção **nunca é fonte** (R9 §5,
  `check_fold_authority.py`).
- **Rota nova (leitura):** `GET /participant/view` — persona-vinculada pelo token
  (ver decisão D1 abaixo). Emite nada; `efeito: nenhum`.
- **Tela nova (web fino):** `range-core/web/persona-panel/` — **um** módulo
  parametrizado pela persona (não sete módulos; R9 §7 — uma responsabilidade),
  pinta o frame `reported` e expõe os botões de declaração já existentes por
  persona. Banner obrigatório.

### Item 4 — Sete ações de continuidade (efeito mecânico + custo)

- **Estado atual:** só existe o `event_type` `continuity_action_taken`
  (`events.schema.yaml:403`, `metric_side: verification`, `effect_class:
  state_effect`), o binding OBJ-10 (`objectives.schema.yaml:306`,
  `auto:[continuity_action_taken]`) e a rubrica
  `range-core/rubrics/business_continuity.v1.yaml`. O **payload é ABERTO**. As
  sete ações com efeito/custo estão em `02` §9:148-156. **P5-2** (categoria de
  ação que altera estado de domínio, sem produtor) e **P6-7** vencem aqui.

- **Resolução do INV-4 (o ponto central desta fase).** `range-core/` não importa
  nada de `domains/`. A ação de continuidade tem duas metades com donos
  diferentes:
  1. **Quais flags cada ação move** é conhecimento de DOMÍNIO (os *nomes* de
     flag são `academus.*`). Vive em `domains/academus/api/continuidade.py`, uma
     **tabela de dados** que mapeia `action_id → [(constante_de_flag, valor)] +
     custo`, usando as **constantes geradas** (`domains/academus/generated/flags.py`),
     nunca literais (INV-5, `check_contract_literals.py`).
  2. **Autorizar por persona, emitir e aplicar o efeito** é do NÚCLEO. A
     `participant-api` já autoriza por persona e assina token de persona.
  - **A ponte que não fura o INV-4:** a tabela de domínio entra no núcleo por
     **injeção na raiz de composição** (`montar()`), exatamente como
     `personas_por_rota` e `Sessao` já entram da superfície
     (`app.py:63-135`). O endpoint de continuidade recebe a tabela como **dado
     injetado**; nunca a importa. O núcleo valida que o `action_id` está na
     tabela, monta o payload a partir dela, autoriza a persona, emite
     `continuity_action_taken` (`participant_action` / `state_effect`).
  - **O fold aplica o `state_effect` genericamente:** lê `effects[].flag` /
     `effects[].value` do payload e escreve no registry de flags (o núcleo tem
     o registry; os nomes vêm do payload — dado, não import). Nenhum nome de
     flag de domínio aparece em código do núcleo.
- **Contrato:** fechar o payload de `continuity_action_taken` como `$def` em
  `contracts/events.schema.yaml` (enum das sete ações + `effects: [{flag,value}]`
  + `cost`/`tradeoff`). É **evolução de contrato derivada de `02` §9, não
  `spec-change`** de `docs/spec/`. Ver D2/D3 (decisões do proprietário).
- **Flags novas:** parte dos sete efeitos já tem flag (congelamento de
  lançamento → `academus.grades_readonly`; emissão emergencial de documentos →
  `academus.transcript_issuance_blocked`). Outros (prova offline, matrícula
  manual, extensão de prazo, adiamento de prova, recuperação acadêmica) **não
  têm flag** em `domains/academus/flags.yaml` — ver D3.
- **Tela (web fino):** botões de ação nos `persona-panel` (mesma tela do item 3),
  chamando o endpoint de continuidade; pintam o custo/tradeoff devolvido.
- **Cruzamento com o item 2:** `continuity_action_taken` também é evento
  `auto`-vinculado (OBJ-10) lido pela projeção `auto/observed`. **Fechar o
  payload não pode quebrar essa projeção** — regressão obrigatória no gate.

## Decisões da abertura (ratificadas pelo proprietário em 2026-09-14)

O proprietário aceitou a abertura no chat ("vai com as recomendações"). As
decisões D1–D3 e a fronteira do item 3 estão ratificadas; a forma concreta:

- **D1 — leitura autenticada por persona.** `GET /participant/view` devolve a
  camada `reported` da própria persona, vinculada ao token. A superfície de
  participante passa a modelar rotas de leitura.
- **D2 — payload fechado de `continuity_action_taken`:** `action_id` (enum das
  7 ações), `effects: [{flag, value}]`, `cost` (string — o tradeoff de `02` §9).
  O cliente envia só `action_id`; o servidor deriva `effects`+`cost` da tabela
  de domínio injetada (INV-7). Evolução de contrato, **não** `spec-change`.
- **D3 — as 7 ações → `action_id`, efeito e custo** (a tabela de
  `domains/academus/api/continuidade.py`, com as constantes geradas):

  | Ação (`02` §9) | `action_id` | Efeito (flag → valor) | Flag |
  |---|---|---|---|
  | Prova offline | `offline_exam` | `academus.offline_exam_mode → true` | **nova** |
  | Congelamento de notas | `freeze_grade_posting` | `academus.grades_readonly → true` | existe |
  | Matrícula manual | `manual_enrollment` | `academus.manual_enrollment_active → true` | **nova** |
  | Extensão de prazo | `enrollment_deadline_extension` | `academus.enrollment_deadline_extended → true` | **nova** |
  | Adiamento de prova | `exam_postponement` | `academus.exam_postponed → true` | **nova** |
  | Emissão emergencial | `emergency_document_issuance` | `academus.transcript_issuance_blocked → false` | existe |
  | Recuperação acadêmica | `academic_recovery` | `academus.academic_recovery_active → true` | **nova** |

  Cinco flags novas; duas ações reusam flags existentes. O `cost` de cada ação
  é o texto da coluna "Custo" de `02` §9:150-156.
- **Fronteira do item 3:** Fase 8 = isolação de leitura da camada `reported`;
  conteúdo divergente de `information_distribution.yaml` = Fase 10.
- **Bloqueador descartado:** `check_spec_flags.py` **não** exige que flag
  declarada seja citada na spec (docstring, "O QUE ELA NÃO FAZ") — só reprova
  citada-e-não-declarada. Declarar as 5 flags novas não é `spec-change`.

## Contratos e registros

- **API pública nova (superfícies, conferidas nas duas direções — R9 §2):**
  - `academus/api_surface.yaml`: `GET /exam/session-status` (item 1);
    filtros na rota de auditoria (item 2).
  - `participant/api_surface.yaml`: `GET /participant/view` (item 3, rota de
    **leitura** — hoje a superfície só modela emissores; ver D1);
    `POST /participant/continuity` (item 4).
- **Contrato de evento:** `$def` fechado de `continuity_action_taken` em
  `contracts/events.schema.yaml` → **regerar** `contracts/generated/events.py` e
  `events.ts` por `tools/codegen.py` (classe `generated` do boundary — só via
  codegen; `codegen.py --check` prova identidade no CI). **Nunca editar a saída.**
- **Ponto de extensão (R9 §4, sem monkey-patch):** a tabela ação→efeito de
  domínio é registrada por **injeção em `montar()`** — ponto de composição
  explícito, aprovado aqui. O núcleo não conhece a tabela em tempo de import.
- **Flags:** novas entradas em `domains/academus/flags.yaml` → regerar
  `domains/academus/generated/flags.py` pelo mesmo gerador de constantes (D3).
- **Pins (R8):** `events.schema.yaml`, `generated/events.*`, `flags.py` e as
  superfícies são candidatos a pin — se pinados, **regenerar `pins.json` no
  mesmo PR** (`gen_pins.py`), em commit próprio com motivo.

## Boundary

Classe tocada mais alta: **generated (via builder)** — `contracts/generated/events.*`
só por `tools/codegen.py`; `domains/academus/generated/flags.py` só pelo gerador
de constantes. **`frozen` (`docs/spec/`) NÃO é tocada** — nenhum item exige
`spec-change` (conclusão: os quatro derivam de spec já publicada). Se a
ratificação de D2/D3 revelar que a forma exige `docs/spec/`, o plano **PARA** no
item 4 e nomeia o rito `spec-change:` (PR próprio, aprovação humana) antes da
implementação — R6 §3/§5.

## Checklist R9 (módulos novos)

- [x] escopo próprio + sem efeito de import — `prova_andamento.py`,
  `continuidade.py`, `reported.py` são funções puras / tabelas; nada executa no
  import.
- [x] uma API registrada — cada rota nova declarada na superfície e conferida
  nas duas direções (`check_api_surface.py`).
- [x] namespace por prefixo — flags e eventos de domínio seguem `academus.*`.
- [x] sem superfície insegura proibida — sem SQL por concatenação, sem `eval`,
  subprocess com lista, caminho entre aspas.
- [x] ≤600 linhas por módulo — cada um é focado; `prova_andamento.py` reusa
  `degradacao.py` em vez de duplicar.
- [x] helper único de invariante — a derivação determinística continua em
  `derive_seed`; a distinção da cadência mora só em `prova_andamento.py`.

## Waves

| Wave | Tarefas (resumo) | Depende de |
|---|---|---|
| 1 | Contratos e registros: `$def` de `continuity_action_taken` + codegen; flags novas + regen; rotas novas nas duas superfícies | decisões D1–D3 do proprietário |
| 2 | Gates escritos + RED commitado (4 itens de DoD) | Wave 1 (contratos/superfícies para referenciar) |
| 3 | Backend independente: `prova_andamento` (item 1), tabela `continuidade` (item 4), filtros de auditoria (item 2), projeção+rota `reported` (item 3) | Wave 1, Wave 2 (gate no prompt) |
| 4 | Backend dependente: endpoint de continuidade + fold `state_effect` + injeção em `montar()` (item 4) | Wave 3 (tabela `continuidade`), Wave 1 (contrato+flags) |
| 5 | Web fino: `exam-mode`, `investigation-console`, `persona-panel`, botões de continuidade | Waves 3/4 (endpoints que cada tela consome) |
| 6 | Validação: green + mutantes + regressão congelada + mapeamento DoD + banner/bundle + aceite do PO | Waves 3–5 |

## Riscos e rollback

- **INV-4 furado no item 4** se o núcleo importar a tabela de domínio → detecção:
  `check_core_boundary.py` + `check_core_contract_imports.py` (CI `arquitetura`).
  Reversão: a tabela volta a ser dado injetado em `montar()`.
- **Literal de flag** no núcleo ou na tabela → `check_contract_literals.py`.
  Mitigação: tabela usa constantes geradas.
- **Regressão da projeção `auto/observed`** ao fechar o payload (item 4 cruza o
  item 2) → regressão congelada obrigatória no gate do item 4.
- **Vazamento de ground truth** no item 3 → gate de isolação (persona nunca
  recebe fato de ground truth) + `05` §6; a projeção nunca lê `ground_truth.yaml`.
- **SKIP silencioso** de gate sem Postgres → o gate nomeia o não-executado
  (R10 §2); `expected_suites.json` tolera só o intervalo declarado.
- **Cadência com relógio de parede** (item 1) → viraria artefato não
  determinístico (R7 §6); tempo é insumo de exercício declarado, provado por
  teste de determinismo em dois "minutos" iguais.

## Protótipo

Nenhum previsto. As quatro peças têm precedente no repositório (degradação,
emissor, projeção, injeção em `montar`); não há pergunta que só código responda.
Se a cadência "por minuto" (item 1) revelar ambiguidade na granularidade do
conjunto de sujeitos, abrir `prototype/prova-cadencia` descartável e trazer o
aprendizado para cá — o protótipo nunca vira produção.
