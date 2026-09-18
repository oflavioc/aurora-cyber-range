# Fase 8 — Web completo

**Status: AUDITADA — PASS** — branch `fase-8-web-completo`, base `c38f890` (a
`main` pós-fechamento da Fase 7). O `checkpoint-auditor` emitiu **PASS** na 4ª
rodada (contexto fresco, worktree fixado no commit `02804c3`, base = PORTA;
laudo em `docs/progress/audit_20260918T192553Z.md`): os quatro itens de DoD
provados com oráculo independente, suíte 949/949 com zero pulos, todos os
verificadores rc=0, as três provas do lançador conferindo contra a árvore. A
linha de status existe porque `check_readme_atual.py` decide *"a fase fechou?"*
por ela; o veredito do auditor a moveu para AUDITADA — PASS.

**Por que este registro nasce antes da fase.** Vinte e cinco pendências
não-fechadas migram da Fase 7 para cá, e pendência sem lugar é pendência que
ninguém encontra. `check_progress_consistency` cobra que toda pendência
não-fechada da fase N apareça na tabela-resumo da fase N+1 — e cobra seção de
detalhe para cada linha. Este arquivo é esse destino, e nasce com a pauta
inteira herdada antes da primeira linha de implementação. É a mesma razão pela
qual o `fase_7.md` nasceu antes da Fase 7.

## 1. Plano da fase

A Fase 8 é **academus-web completo, dashboards por persona e continuidade** —
`07_IMPLEMENTATION_PHASES.md` §"Fase 8". Os quatro itens de DoD:

| # | Item de DoD | Fonte |
|---|---|---|
| 1 | Modo "Prova em andamento" perde sessões conforme `lms_session_drop_rate` | `07` §Fase 8 |
| 2 | Console de investigação emite os marcadores automáticos | `07` §Fase 8 |
| 3 | Cada persona vê apenas sua camada `reported` | `07` §Fase 8; `06` T14 (persona não vaza ground truth) |
| 4 | As sete ações de continuidade aplicam efeito mecânico e custo | `07` §Fase 8; `03` §continuidade |

**ENTRY** — Fase 7 selada (o pack completo, o `range-cli` e o branching
existem; as telas mínimas da Fase 4 — gm-console, wallboard, participant-view —
são a base sobre a qual o web completo cresce).

**A leitura disciplinada da spec desta fase** (CLAUDE.md §"Disciplina de
leitura"), a fazer no início da implementação: `00_MASTER_SPEC.md`,
`09_EVENT_MODEL.md`, `07` §Fase 8, os critérios de aceite correspondentes em
`06`, e `05_SECURITY_REQUIREMENTS.md` — a fase toca apresentação a
participante, personas e ações que mudam estado, então a fronteira de
`05` §6 (nada de ground truth em superfície de participante) é central.

## 2. A abertura, e o que ela carrega

A adoção da Estrutura Agêntica decidiu que **a Onda 2 entra na abertura da
Fase 8** (ver `docs/ADOCAO_ESTRUTURA_AGENTICA.md` §0.4): os oito papéis de
agente e o desenho da reconciliação fase↔demanda. Essa é a primeira decisão da
fase, e é do proprietário — ela reconfigura como todo trabalho daqui em diante
é governado. Está registrada como P8-1 e apresentada ao proprietário; a
implementação segue a decisão.

Além dela, dez pendências da Fase 7 declararam gatilho "abertura da Fase 8" —
os spec-changes de alinhamento (P7-15, P7-16, P7-20), os mecanismos (P7-17,
P7-19) e a ampliação do gerador para a Linha A (P7-10, `DECIDIDA`). Cada uma
tem linha na §6.

## 3. Itens de DoD — status e evidência

A §7 de fechamento (resumo técnico, estrutura, endpoints, migrações, variáveis
de ambiente, próxima fase) é redigida por quem implementou **após** o veredito
do auditor. Esta seção é o insumo do auditor: cada item de DoD com status e a
prova executável que o sustenta. Contagens medidas com Postgres/Redis no ar
(a suíte completa passa a 949).

| # | Item de DoD | Status | Evidência executável |
|---|---|---|---|
| 1 | Modo "Prova em andamento" perde sessões conforme `lms_session_drop_rate` | **VERDE** | `domains/academus/api/prova_andamento.py` (modelo de sobrevivência cumulativo, determinístico por `derive_seed`) provado por `tests/test_prova_andamento.py` (15, puro); a cláusula **conforme a flag** provada ponta-a-ponta por `tests/test_prova_andamento_integracao.py` (7, serviço): `GET /exam/session-status` derruba sessões conforme `academus.lms_session_drop_rate` LIDA do estado, e com a flag 0 ninguém cai |
| 2 | Console de investigação emite os marcadores automáticos | **VERDE** | os cinco filtros (período/usuário/IP/janela/autorização, `filter_window` booleano) são **aplicados à consulta SQL** (`repositorio.alteracoes_de_nota`, filtro→coluna por `_FILTRO_PARA_COLUNA`) e o marcador `auto` (`audit_query_performed`) é emitido. O oráculo do SQL real é `tests/test_console_consulta_servico.py` (13, `@exige_banco`): semeia o próprio conjunto na `audit_trail` real e afere que cada filtro recorta o subconjunto certo e que `result_count` é a contagem **filtrada** — não uma cópia do mapa de produção. `tests/test_console_investigacao.py` (16, sem serviço) prova o marcador `auto` pela projeção e o encaminhamento do handler |
| 3 | Cada persona vê apenas sua camada `reported` | **VERDE** | `range-core/participant/reported.py::project` (conjunção camada-reportável **E** `persona==P`, whitelist) provado na projeção pura **e pela rota real** `GET /participant/view` sobre o payload da API — `tests/test_reported_isolation.py` (10): nunca vaza ground truth, persona não alcança a fatia de outra, 401 sem token |
| 4 | As sete ações de continuidade aplicam efeito mecânico e custo | **VERDE** | `domains/academus/continuidade.py` (as 7 do enum fechado) + fold genérico lendo `payload["effects"]` (INV-4: tabela injetada em `montar()`); `tests/test_continuidade.py` (20): cada ação emite `continuity_action_taken`, o fold aplica a flag, o custo viaja, negativos (422/403/401) presentes |

As quatro telas web (`exam-mode`, `investigation-console`, `persona-panel` + botões de continuidade) pintam o frame TOTAL do servidor (INV-7), com banner (INV-10, gate estendido às seis telas) e sem derivação no cliente. O serving por rota e a raiz de composição de produção estão desenhados em `fase_8_plan_serving.md` e **não** são exigidos pela DoD desta fase (o auditor confirmou itens 3/4 sem eles).

## 6. Pendências

Prefixo `P8-` para as que nascerem aqui. A tabela abaixo começa com o que foi
**herdado** da Fase 7, e o prefixo herdado é preservado: renumerar apagaria a
cadeia que liga a pendência ao registro em que ela nasceu.

As **seções de detalhe** das herdadas são resumo com ponteiro, e não cópia: o
argumento inteiro de cada uma vive no `docs/progress/fase_N.md` de origem, que
fechou (ou fecha) auditado. Repeti-lo aqui criaria duas fontes para o mesmo
fato — a §1.6 que os registros perseguem. O que fica aqui é o id, o estado, e
a relevância para ESTA fase.

**`Estado` é o enum fechado da Fase 7**: `ABERTA` · `LATENTE` · `DECIDIDA` ·
`VENCIDA` · `RESOLVIDA` · `ENTREGA`.

<!-- tabela-resumo-de-pendencias -->

| Pendência | Assunto | Estado | Vence em |
|---|---|---|---|
| P8-1 | ~~Onda 2 da Estrutura Agêntica: instanciar os oito papéis e desenhar a reconciliação fase↔demanda — a decisão de abertura que a adoção agendou para cá~~ | `RESOLVIDA` | aceite de abertura do proprietário no chat em 2026-09-14; os oito papéis estão instalados e em uso (tech-lead produziu o desenho da Fase 8); reconciliação "marco por fora, SDD por dentro" registrada na adoção; ver abaixo |
| P8-2 | o banner (`05` §4) na classe `exportacao` — histórico, diploma, PDF gerados pelo academus-web — não tem fase de destino: os artefatos ainda não existem, e o gate `check_banner_de_simulacao.py` os defere | `ABERTA` | a fase que construir os artefatos de exportação do academus-web (não previstos na DoD da Fase 8 nem em item da Fase 9); ver abaixo |
| P8-3 | a entrada `pytest` na allowlist do auditor (`readonly_bash.py`) tem o prefixo do venv (H2) mas `pytest` não é dependência do projeto — a regra admite um comando que não existe em interpretador nenhum | `ABERTA` | a fase que adotar `pytest` (se alguma) ou a decisão de remover a entrada; a suíte do projeto é `unittest`; ver abaixo |
| P8-4 | cinco das sete superfícies do academus-web (`02` §7: Portal do Aluno, do Professor, Secretaria, Financeiro, AVA) não têm fase de destino — a Fase 8 entregou só Prova em andamento e Console de investigação | `ABERTA` | a fase que construir o restante do academus-web (não previstas na DoD da Fase 8: `07` §Fase 8 tem quatro itens e nenhum as cobra); ver abaixo |
| P8-5 | as três telas que a fase construiu (`exam-mode`, `investigation-console`, `persona-panel`) não têm rota que as sirva, e a `participant-api` — que sustenta os itens 3 e 4 — não tem raiz de composição de produção nem serviço no `docker-compose.yml` | `ABERTA` | a fase de serving/deploy do web (desenho pronto em `fase_8_plan_serving.md`, T822–T831); não exigido pela DoD da Fase 8 (comportamento provado sem serving), mas a entrega fica inalcançável sem ele; ver abaixo |
| P8-6 | as sete `action_id` do enum fechado do contrato estão copiadas à mão em `persona-panel/tipos.ts` sem gate que cruze com o contrato — o lado Python tem oráculo (`test_continuidade`), o TypeScript não | `ABERTA` | a Onda 3 (TDD endurecido) ou a geração de constantes TS a partir do contrato (como `events.ts`/`flags.ts` já fazem); ver abaixo |
| P8-7 | o "cronômetro" do Modo Prova em andamento recebe `exercise_minute` como insumo do chamador; a cadência da queda não acompanha o relógio de exercício do servidor (PAUSAR não congela) | `ABERTA` | a fase que ligar `ProvaEmAndamento` ao relógio autoritativo do `PostgresEventStore` já injetado; a cláusula "conforme a flag" da DoD está provada, o cronômetro é refinamento; ver abaixo |
| P1-7 | o id do inject pode vazar a linha; falta o mecanismo que impeça o próximo pack de decidir pelo vazamento | `ABERTA` | **redatada no fechamento da Fase 8**: o gatilho "esta fase, junto do destino do pack (P7-9)" passou sem vencer — a Fase 8 expôs injects ao participante mas não construiu o mecanismo, e o destino do pack (P7-9) segue aberto. Novo vencimento: a fase que decidir o destino do pack (P7-9) ou o primeiro pack novo; detalhe em `fase_7.md` §"P1-7" |
| P4-8 | leitura síncrona no laço de eventos serializa e bloqueia em volume | `ABERTA` | medição de volume; detalhe em `fase_4.md`/`fase_7.md` §"P4-8" |
| P5-2 | ~~a categoria "declarações do exercício" da trilha não tem produtor~~ | `RESOLVIDA` | **venceu na Fase 8**: as sete ações de continuidade (item 4) são a primeira ação de participante que altera estado de domínio, com produtor — `POST /participant/continuity` emite `continuity_action_taken` e o fold aplica o efeito; detalhe em `fase_5.md` §"P5-2" |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores de `line_b_case.set` | `ABERTA` | reformulação na abertura; o schema v3 é o veículo quando houver delta real; detalhe em `fase_5.md`/`fase_7.md` §"P5-4" |
| P6-2 | `observable_impact` (start de `TTA`) não existe em contrato | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; detalhe em `fase_6.md` §"P6-2" |
| P6-3 | `before`/`after`/`since` dependem de uma gramática de `exercise_time` que não existe | `ABERTA` | os três gatilhos herdados da Fase 6, intactos; detalhe em `fase_6.md` §"P6-3" |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança | `ABERTA` | **redatada no fechamento da Fase 8**: o gatilho "esta fase" passou sem vencer — não foi material da DoD da Fase 8. Novo vencimento: a fase que consumir `03` §5.3 (separar erro de julgamento de lacuna de cobertura), candidata a Fase 10 (AAR/calibração); detalhe em `fase_6.md`/`fase_7.md` §"P6-5" |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e não `Bash` | `LATENTE` | **redatada no fechamento da Fase 8**: o "ou esta fase" sai; permanece `LATENTE` com o gatilho real — a primeira sessão que trabalhe em duas branches simultâneas; detalhe em `fase_6.md` §"P6-6" |
| P6-7 | ~~rota que declara `emite` e não chama emissor nenhum~~ | `RESOLVIDA` | **venceu na Fase 8**: as rotas novas que declaram `emite` chamam o emissor de fato — `POST /participant/continuity` (`emitir_continuidade`) e `GET /audit/grade-changes` (`registrar_consulta`) —, e o padrão é gateado por `check_fabrica_liga_emissor`/`check_hooks_com_emissor`; detalhe em `fase_6.md` §"P6-7" |
| P6-8 | justificativa ausente devolve `409`, reservado a recusa de estado | `DECIDIDA` | a medição dos consumidores, ou a Fase 10; detalhe em `fase_6.md` §"P6-8" |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção (`sub == persona`) | `ABERTA` | **redatada no fechamento da Fase 8**: o gatilho "material desta fase" passou — a Fase 8 tocou persona (item 3, leitura `reported`) mas não a contrassinatura. Novo vencimento: a palavra do proprietário entre as saídas (a) e (b); detalhe em `fase_6.md` §"P6-12" |
| P6-13 | dezesseis violações plantadas da §3.5 da Fase 6 são atestação, não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável; detalhe em `fase_6.md` §"P6-13" |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual linha esta fase entrega; detalhe em `fase_7.md` §"P7-1" |
| P7-4 | consumo de `event_type` por selecionador sem allowlist declarada | `ABERTA` | **Fase 12** — degrau 1.5; detalhe em `fase_7.md` §"P7-4" |
| P7-5 | chamadores de cada emissor não varridos quando o contrato do emissor muda | `ABERTA` | **Fase 12** — degrau 2; detalhe em `fase_7.md` §"P7-5" |
| P7-10 | ~~o gerador de gabarito só produz Linha B — a Linha A não é materializada~~ | `RESOLVIDA` | nasce `domains/academus/seed/linha_a.py`: sintetiza o incidente (initial_access, privilege_escalation, exfiltration) do seed, e os `verification_predicates` do pack passam a ser os do incidente (VPN revogada + escopo desabilitado + ausência de exfiltração), não mais a contenção da Linha B; ver abaixo |
| P7-11 | condição temporal de branch (`before`/`after`) carrega e nunca ramifica | `ABERTA` | o gatilho da P6-3 (a gramática temporal nascer); detalhe em `fase_7.md` §"P7-11" |
| P7-12 | a superfície do hook do auditor acumulou cinco achados M/L sem rastro | `ABERTA` | **redatada no fechamento da Fase 8**: o gatilho "a próxima edição da allowlist" DISPAROU — a allowlist foi editada nesta fase (H2, `c2df575`); o resíduo específico (entrada `pytest` inerte) está em **P8-3**. Novo vencimento da linha-mãe: a próxima edição da allowlist do auditor; detalhe em `fase_7.md` §"P7-12" |
| P7-13 | o harness não planta violação onde a correção entrou | `ABERTA` | **Onda 3 da Estrutura Agêntica** (TDD endurecido); detalhe em `fase_7.md` §"P7-13" |
| P7-14 | seis afirmações de registro/teste sem disposição (varredura P7-6) | `ABERTA` | a varredura de fechamento desta fase (regra (b) da P7-6); detalhe em `fase_7.md` §"P7-14" |
| P7-15 | ~~o extremo inclusivo contra a redação-alvo de `03` §3.2~~ | `RESOLVIDA` | fechada em `c38f890` (fix-finding P7-15), que é a **base** desta branch — o PR já estava em `main` antes do primeiro commit da fase; `fase_7.md:1249` registra RESOLVIDA |
| P7-16 | ~~`PHASE_0_CHECKLIST.md` afirma demonstração que foi atestação~~ | `RESOLVIDA` | fechada em `8b3462e` (spec-change, base da branch): `PHASE_0_CHECKLIST.md` já diz "fechados por atestação (P34), não por demonstração" |
| P7-17 | ~~o destino da P2-17 (start do `frozen_interval`) passou em silêncio~~ | `RESOLVIDA` | medido: o start vem da âncora (`inject_engine.py:579`, fixado por teste) e chega intacto ao desconto; decisão (a) aceitar a âncora — é conformidade com a fixture normativa do contrato, e o sinal é o que `09` §3.1 quer; (b) spec-change fica como destino se um cenário fizer a largura importar; ver abaixo |
| P7-19 | ~~`check_progress_consistency` isenta `ENTREGA` de migrar, mesmo não entregue~~ | `RESOLVIDA` | `esta_concluida` lê a linha de Status de fechamento e `confere_pauta` reprova `ENTREGA` numa fase concluída; eixo_l prova nas três pernas; ver abaixo |
| P7-20 | ~~`04` §8 declara `validate`/`migrate` que não existem~~ | `RESOLVIDA` | fechada em `8b3462e` (spec-change, base da branch): `04` §8 já removeu `validate`/`migrate` como verbos próprios, com a nota da P7-20 |

#### P8-1 — Onda 2: os oito papéis e a reconciliação fase↔demanda — RESOLVIDA

**Nasce com a fase**, e é a decisão de abertura que a adoção da Estrutura
Agêntica agendou para cá (`docs/ADOCAO_ESTRUTURA_AGENTICA.md` §0.4). A Onda 2
traz os oito papéis de agente (PO, TL, UI, core, build, data, QA, doc) e a
máquina SDD de sete fases governando também o roadmap — e a primeira tarefa é
**reconciliar** duas contagens de "fase": a fase-marco do roadmap do Aurora
(âncora + auditoria de checkpoint) e a fase-demanda da máquina SDD do kit.

**RESOLVIDA no aceite de abertura (2026-09-14).** O proprietário aceitou a
abertura no chat ("vai com as recomendações"). Os oito papéis estão instalados
em `.claude/agents/` e já em uso — o `tech-lead` produziu o desenho técnico
desta fase (`fase_8_plan.md`, `fase_8_tasks.md`). A reconciliação é **"marco
por fora, SDD por dentro"**: o roadmap governa os marcos (âncora +
`checkpoint-auditor`); a máquina SDD de sete fases governa as demandas fora do
roadmap. Os agentes pré-existentes (`scenario-designer`, `spec-guardian`,
`checkpoint-auditor`) permanecem e não foram substituídos.

**Decisões de abertura da Fase 8 ratificadas no mesmo aceite** (detalhe em
`fase_8_plan.md`; a forma concreta de D2/D3 na sua §"Decisões da abertura"):

- **D1 — leitura do item 3 é autenticada e vinculada ao token da persona**
  (`GET /participant/view` devolve a camada `reported` da própria persona;
  isolação real, A não pede a visão de B). A superfície de participante passa a
  modelar rotas de **leitura**, não só emissores.
- **D2 — payload fechado de `continuity_action_taken`**: `action_id` (enum das
  7), `effects:[{flag,value}]`, `cost` (o tradeoff de `02` §9). Evolução de
  contrato derivada de `02` §9 — **não** `spec-change`.
- **D3 — cinco flags novas de continuidade** em `domains/academus/flags.yaml`
  (`offline_exam_mode`, `manual_enrollment_active`, `enrollment_deadline_extended`,
  `exam_postponed`, `academic_recovery_active`); as outras duas ações reusam
  `grades_readonly` e `transcript_issuance_blocked`. `check_spec_flags.py` não
  exige que flag declarada seja citada na spec (só reprova citada-e-não-declarada),
  então não há spec-change.
- **Fronteira do item 3**: a Fase 8 entrega só a **isolação** de leitura; o
  conteúdo divergente de `information_distribution.yaml` (`03` §4) é assimetria
  da **Fase 10**.

#### P8-2 — o banner na classe `exportacao` sem fase de destino

**Nasceu na 2ª auditoria da Fase 8 (M1).** Ao estender `check_banner_de_simulacao.py`
para cobrir as três telas academus-web (item de INV-10), a classe `exportacao`
de `05` §4 — o banner no **rodapé de artefato gerado** (histórico, diploma, PDF,
exportação) — ficou deferida com dono "Fase 8/9", que não a cobre: `07` §Fase 9
não tem item para esses artefatos, e eles ainda não existem no disco. O banner
em TELA está gateado (as seis telas); o banner em ARTEFATO GERADO é classe
distinta (`05` §4: *"no rodapé de todo artefato gerado"*), e só pode ser gateado
quando o artefato existir.

**Vence em:** a fase que construir os artefatos de exportação do academus-web
(histórico/diploma/PDF servidos ao participante) — não previstos na DoD da Fase 8
nem em item da Fase 9. Até lá, o registro bidirecional de `check_banner_de_simulacao.py`
mantém a classe deferida e reprova se um alvo aparecer no disco sem o banner. A
pendência existe para que o requisito não morra em silêncio (a forma que `05` §4
e a própria auditoria nomeiam).

#### P8-4 — cinco superfícies do academus-web sem fase de destino

**Nasceu na 3ª auditoria da Fase 8 (M4, órfão da 2ª).** `02` §7 enumera sete
superfícies do academus-web: Portal do Aluno, Portal do Professor, Secretaria,
Financeiro, AVA simplificado, Modo "Prova em andamento" e Console de
investigação. A Fase 8 entrega as duas últimas (mais o `persona-panel`). **Não é
falha de DoD** — `07` §Fase 8 tem quatro itens e nenhum cobra as outras cinco —,
mas a fase intitulada "Web completo" fecha sem que nenhuma pendência diga quem
constrói Portal do Aluno, Portal do Professor, Secretaria, Financeiro e AVA.

**Vence em:** a fase que construir o restante do academus-web (candidata: a fase
de conteúdo/experiência de participante, a decidir pelo proprietário no
planejamento pós-Fase-8). A pendência existe para que as cinco não sumam do
radar por não estarem em item de DoD.

#### P8-3 — a entrada `pytest` da allowlist do auditor admite comando inexistente

**Nasceu na 3ª auditoria da Fase 8 (M2, órfão da 2ª).** O H2 da 1ª auditoria
pediu o `{PREFIXO_DO_VENV}` na entrada `pytest` de `user-scope/hooks/readonly_bash.py`
(4ª ocorrência da classe "forma admitida, interpretador inalcançável"), e ele foi
acrescentado. Mas `pytest` **não é dependência do projeto** — a suíte é `unittest`
(decisão registrada no próprio `readonly_bash.py`), e o venv do lançador não tem o
módulo. A regra agora admite `pytest`/`python -m pytest` com o prefixo certo, mas
nenhum interpretador deste worktree o executa: a correção do H2 destravou um
comando que não existe.

**Por que fica ABERTA e não é revertida agora:** a entrada é inócua (allowlist
que não casa comando algum não faz mal) e coerente com as irmãs; removê-la
reabriria a inconsistência que o H2 nomeou. **Vence em:** a fase que adotar
`pytest` como dependência (aí a entrada passa a valer), **ou** a decisão do
proprietário de removê-la por ser vestigial. Registrada para não ser "correção
que destrava o impossível" sem rastro.

#### P8-5 — as telas construídas sem rota, e a `participant-api` sem processo

**Nasceu na 4ª auditoria da Fase 8 (H1).** A fase construiu três telas
(`exam-mode`, `investigation-console`, `persona-panel`) e o `range-api` serve só
`/sala`, `/plateia`, `/console` — nenhuma rota serve as novas. E a
`participant-api`, que sustenta os itens 3 (leitura `reported`) e 4
(continuidade) da DoD, tem `montar(...)` chamado **só por teste**: não há
`processo.py` de produção que injete `CONTINUIDADE` + emissor real, nem serviço
`participant-api` no `docker-compose.yml`.

**Não é falha de DoD** — `07` §Fase 8 tem quatro itens comportamentais, nenhum
pede serving, e o auditor confirmou itens 3/4 sem ele. Mas a fase "Web completo"
fecha com entrega inalcançável sem registro de quem a alcança. O desenho já
existe em `fase_8_plan_serving.md` (T822–T831: co-locar cada casca com sua
data-API; factory em `domains/academus/api/participante_processo.py`; serviço no
compose). **Vence em:** a fase de serving/deploy do web (a decidir pelo
proprietário no planejamento pós-Fase-8, candidata à Fase 9 ou a uma fase de
deploy). Registrada para que a entrega inalcançável não atravesse para a Fase 9
sem dono.

#### P8-6 — o enum das sete ações copiado à mão no cliente, sem gate

**Nasceu na 4ª auditoria da Fase 8 (M5).** As sete `action_id` do enum FECHADO do
contrato (`events.schema.yaml`, `continuity_action_taken_payload`) estão escritas
à mão em `range-core/web/persona-panel/tipos.ts` (`ACOES_DE_CONTINUIDADE`), sem
nenhum gate que cruze as duas listas. O lado Python tem oráculo independente
(`test_continuidade.py::test_a_tabela_cobre_exatamente_as_sete_do_contrato` lê o
enum do YAML e exige igualdade); o cliente não. Acrescentar uma oitava ação ao
contrato, ou renomear uma das sete, deixa o painel com um botão que devolve 422
e nada fica vermelho. INV-3/INV-5 não o alcançam porque `action_id` não é flag
nem `event_type`. **Vence em:** a Onda 3 (TDD endurecido) ou a geração de
constantes TS a partir do contrato (o mesmo mecanismo que já produz `events.ts`
e `flags.ts`, R12); ver `L2` da mesma auditoria — `CAMPO_DA_CONSULTA` do teste
de dublê é da mesma família (cópia à mão), coberta pelo oráculo de serviço.

#### P8-7 — o cronômetro da prova em andamento não acompanha o relógio de exercício

**Nasceu na 4ª auditoria da Fase 8 (M6).** `ProvaEmAndamento.frame(...)` recebe
`exercise_minute` como insumo do chamador (query param obrigatório de
`GET /exam/session-status`), e a tela pinta esse eco como "cronômetro". Mas o
processo já tem o relógio autoritativo à mão (`processo.py` injeta o
`PostgresEventStore` com clock no mesmo `LeituraDeEstado`). Consequência: PAUSAR
não congela a queda (o chamador escolhe o minuto), e é possível pedir minuto 0 e
receber o frame inteiro `alive` com a flag cheia.

**Não toca a cláusula da DoD** — o item 1 cobra "perde sessões **conforme
`lms_session_drop_rate`**", e isso está provado ponta a ponta contra a flag lida
do estado. O defeito é do cronômetro, não do "conforme a flag". **Vence em:** a
fase que ligar `ProvaEmAndamento` ao relógio de exercício do servidor (derivar o
minuto do `exercise-clock`, não recebê-lo por parâmetro), respeitando que PAUSAR
congela (`01` §3).

#### P1-7 — id de inject pode vazar a linha

Herdada da Fase 1, carregada pela 7. O pack de 4 h decidiu por ids neutros
`IN*`; falta o mecanismo que impeça o próximo pack de escolher o vazamento.
Detalhe e história em `fase_7.md` §"P1-7". Nesta fase o web expõe injects a
participante, então a superfície de vazamento é material aqui.

#### P4-8 — leitura síncrona no laço de eventos

Herdada da Fase 4. Serializa hoje e bloqueia em volume. Detalhe em `fase_7.md`
§"P4-8"; o gatilho de medição pode chegar com o volume de telemetria da Fase 9.

#### P5-2 — a categoria "declarações do exercício" sem produtor

Herdada da Fase 5. Detalhe em `fase_5.md` §"P5-2". Vence na primeira ação de
participante que altere estado de domínio — e as sete ações de continuidade
(item 4 desta fase) são candidatas diretas.

#### P5-4 — os seis conjuntos não cabem nos três valores de `set`

Herdada da Fase 5, mal formulada na origem (medido na Fase 7). Detalhe em
`fase_7.md` §"P5-4". Reformular na abertura; schema v3 é o veículo quando
houver delta real (a política de versionamento do #67 rege isso).

#### P6-2 — `observable_impact`, o start de `TTA`

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-2". Vence quando o
consumidor de `TTA` for desenhado.

#### P6-3 — a gramática temporal de `exercise_time`

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-3". Os três gatilhos seguem
intactos; a P7-11 depende deste.

#### P6-5 — `review_scope` com a lista de `case_id`

Herdada da Fase 6, decisão do operador sem veículo. Detalhe em `fase_7.md`
§"P6-5". `03` §5.3 a consome nesta fase para separar erro de julgamento de
lacuna de cobertura.

#### P6-6 — o sentinela não intercepta `Bash`

Herdada da Fase 6, `LATENTE`. Detalhe em `fase_6.md` §"P6-6". Vence na primeira
sessão em duas branches, ou nesta fase.

#### P6-7 — rota que declara `emite` sem chamar emissor

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-7". O web completo desta fase
adiciona rotas que emitem — a próxima que declare `emite` com fábrica pronta é
o gatilho.

#### P6-8 — `409` para justificativa ausente

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-8". Vence na medição
dos consumidores, ou na Fase 10.

#### P6-12 — a condição (4) da contrassinatura em produção

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-12". Toca persona (`sub ==
persona`), então é material desta fase; a saída é do proprietário.

#### P6-13 — as dezesseis violações plantadas como atestação

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-13". Vence quando a afirmação
precisar ser reexecutável.

#### P7-1 — a rota de submissão não valida o payload

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-1". Depende da decisão do
proprietário sobre qual das três linhas esta fase entrega.

#### P7-4 — consumo de `event_type` por selecionador sem allowlist

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-4".

#### P7-5 — chamadores de emissor não varridos

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-5".

#### P7-10 — o gerador só produz Linha B — RESOLVIDA

Herdada da Fase 7. Detalhe da origem em `fase_7.md` §"P7-10". A decisão do
proprietário (13/09) foi ampliar o mecanismo, não a spec.

**RESOLVIDA na abertura da Fase 8.** Nasce `domains/academus/seed/linha_a.py`,
o dono do gabarito do incidente. As decisões de desenho, na altitude do
registro da Fase 7 §5.2 (a spec fixa a forma; o conteúdo determinístico é
escolha do gerador, documentada e reversível):

- **Sintetizar do seed, não semear tabela de incidente.** A Linha B é lida do
  banco porque é dado acadêmico real; a Linha A (acesso por credencial de
  serviço, escalação, exfiltração) é o incidente sobreposto, não business
  state. Semear VPN/exfiltração no Postgres anteciparia o evidence-simulator
  (Fase 9) e furaria a fronteira de `01` §2. O incidente nasce do seed,
  determinístico, com prova negativa (dois seeds diferem).
- **A forma é a de `04` §3 e do exemplo de `ground_truth.schema.yaml`** —
  `initial_access`, `privilege_escalation`, `exfiltration`, com `source_ip` de
  faixa de documentação (RFC 5737), `credential_state`, `mfa`, `projections`,
  `discoverability`.
- **O ator é conta de serviço (`svc_academus`), não a `conta_alvo` da Linha B**:
  são dois vetores — a Linha B é adulteração de nota por conta docente, a
  Linha A é ransomware por credencial de serviço. Conflati-los faria as
  métricas medirem o mesmo ator.

**A correção de fundo**: `gabarito.predicados_de_verificacao` devolvia a
contenção da Linha B (`absence_of grade_change_retroactive`) e
`service_restoration: not_applicable` — o que a Fase 7 mediu como o defeito
(TTCV/TTRV incomputáveis, contenção medindo integridade). Agora os
`verification_predicates` do pack são os do incidente (VPN revogada + escopo
desabilitado + ausência de exfiltração; restauração pelas duas flags). Os casos
`GC-` da Linha B seguem sendo a linha de integridade (TTIV), outra pergunta.

Provado: `test_linha_a.py` (10 testes — determinismo nas duas direções, forma
de `04` §3, IP de documentação, predicados do incidente); pack rematerializado
contra o banco semeado, `lint` sem achados, `dryrun` percorre, `check_synthetic_data`
verde, parser estrito verde, invariantes 2 e 3 verdes (constantes geradas de
flag e event_type). Suíte 858 → 868.

#### P7-11 — condição temporal de branch nunca ramifica

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-11". Depende da P6-3.

#### P7-12 — a superfície do hook do auditor

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-12". Cinco achados M/L sobre
`readonly_bash.py`; vence na próxima edição da allowlist ou nesta fase.

#### P7-13 — o harness não planta onde a correção entrou

Herdada da Fase 7, gatilho **Onda 3**. Detalhe em `fase_7.md` §"P7-13".

#### P7-14 — seis afirmações sem disposição

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-14". A varredura de fechamento
desta fase dá disposição a cada uma (regra (b) da P7-6).

#### P7-15 — o extremo inclusivo × `03` §3.2 — RESOLVIDA

Herdada da Fase 7 e **fechada em `c38f890`** (fix-finding P7-15), que é a base
desta branch — o PR já estava em `main` antes do primeiro commit da fase.
`fase_7.md:1249` registra RESOLVIDA. A linha estava falsamente `ABERTA` na §6 até
o fechamento da Fase 8 (M1 da 4ª auditoria). Detalhe de origem em `fase_7.md`.

#### P7-16 — o checklist afirma demonstração que foi atestação — RESOLVIDA

Herdada da Fase 7 e **fechada em `8b3462e`** (spec-change, base da branch):
`PHASE_0_CHECKLIST.md` já diz "fechados por atestação (P34), não por
demonstração". Estava falsamente `ABERTA` até o fechamento (M1). Detalhe de
origem em `fase_7.md` §"P7-16".

#### P7-17 — o destino da P2-17 passou em silêncio — RESOLVIDA

Herdada da Fase 7. Detalhe da origem em `fase_7.md` §"P7-17" e na P2-17
(`fase_2.md`). O gatilho que a P2-17 declarou — "a Fase 6 decide se a largura a
mais importa" — passou sem menção, e a P7-17 existe para tirá-lo do silêncio.

**Medição (o que faltava).** O `start` do `frozen_interval` **ainda vem da
âncora**: `range-core/engine/inject_engine.py` `_frozen_interval` devolve
`start = ancora.exercise_timestamp` (linha 579), fixado pelo teste
`test_inject_engine.…test_technical_failure_registra_os_extremos_do_intervalo`
(`start == self.a01.exercise_timestamp`). Daí ele flui **sem transformação**
para o desconto da Fase 6: `metrics/epoch.py` `_intervalo` lê `start`/`end` do
payload, `congelamentos` os une, e `decorrido` os subtrai da janela da métrica.
A âncora chega intacta ao número.

**Decisão: aceitar a âncora como start — é conformidade com a spec, não
aproximação a corrigir.** A fixture normativa do próprio contrato
(`contracts/events.schema.yaml`, "ROLLBACK COM CONGELAMENTO") equaciona
`start = exercise_timestamp da âncora` com o que `06` T3 chama de *"do inject
falho até a retomada"*. As duas rotas de remediação que a P2-17 pôs:

- **(a) aceitar a âncora** — nenhum código muda; o invariante já é gate. **Escolhida.**
- **(b) exigir que o `rollback_performed` nomeie o inject falho** — campo novo de
  payload, e portanto `spec-change` mais contrato, com aprovação humana
  (`CLAUDE.md`). O contrato mostra por que (b) é caro e não trivial:
  `to_event_id`/`to_inject_id` nomeiam a **âncora**, não a falha; localizar a
  falha exigiria varrer `inject_fired`, "dependência de uma projeção de estado
  num evento de facilitação que nada na spec autoriza"
  (`events.schema.yaml:559-562`).

**Por que (a) é segura e não só barata.** A única divergência entre âncora e
inject falho aparece quando o facilitador rebobina para **antes** da falha — e
aí o intervalo gravado é mais largo, descontando tempo que correu normal. Mas o
sinal é o que `09` §3.1 **quer**: desconta a mais, nunca a menos — *"a equipe
não é penalizada por bug do ambiente"*. Superestimar o congelamento credita a
equipe; nunca a pune. E a spec não oferece campo para distinguir o caso, então
(a) é o teto do que se lê do envelope sem `spec-change`.

**Destino de (b), registrado para não voltar em silêncio:** é a saída *se e
quando* um cenário fizer a largura a mais importar — um `technical_failure`
cuja âncora fique muito antes da falha, com tempo de exercício legítimo no meio
que o crédito a mais distorça um TTCV a ponto de mudar a leitura do AAR. Até
lá, não se justifica. **Ratificada pelo proprietário no chat em 2026-09-14**
("Ratifico a decisão (a) da P7-17"): a rota (a) é a decisão de fechamento, e
(b) fica registrada como destino condicionado ao cenário que a exija.

#### P7-19 — `ENTREGA` não entregue sai sem destinatário — RESOLVIDA

Herdada da Fase 7. Detalhe da origem em `fase_7.md` §"P7-19". Foi o H3 da 2ª
auditoria da Fase 7: P1-7, P5-4 e P6-5 escaparam da migração porque `ENTREGA`
não migra e a Definition of Done que a cobra é humana, não um gate. Uma fase
que **fecha** com uma linha ainda `ENTREGA` a faz sumir — não foi entregue,
não migra, não está em checagem nenhuma.

**RESOLVIDA na abertura da Fase 8.** Em `check_progress_consistency.py`,
`esta_concluida` lê a linha de Status de fechamento (`CONCLUÍDA` /
`AUDITADA — PASS`), e `confere_pauta` reprova qualquer linha `ENTREGA` numa
fase assim, mandando marcar `RESOLVIDA` (entregue, não migra) ou reclassificar
para um estado que migra. A guarda casa o **Status**, não o estado: fase aberta
com `ENTREGA` continua legítima — é trabalho em andamento da própria fase.

A prova negativa é o `eixo_l` de `check_progress_consistency_probes.py`, nas
três pernas da disciplina do (f)/(h): a condição vista fazendo estrago (fase
fechada com `ENTREGA` reprova), contida (a mesma curada passa), e a guarda
presa no Status e não no estado (fase aberta com `ENTREGA` não reprova). Esse
verificador era o único dos de `scripts/` sem prova negativa de fechamento; o
eixo fecha essa lacuna.

#### P7-20 — `validate`/`migrate` declarados e inexistentes — RESOLVIDA

Herdada da Fase 7, e **fechada na base desta branch** (`8b3462e`, spec-change do
`04` §8, antes do primeiro commit da fase): `validate`/`migrate` já não são
verbos próprios, com a nota da P7-20. Detalhe de origem em `fase_7.md` §"P7-20".

---

## 7. Fechamento

> Redigida por quem implementou, **após** o veredito PASS do `checkpoint-auditor`
> (`docs/progress/audit_20260918T192553Z.md`), como manda o rito.

### Resumo técnico

A Fase 8 entregou os quatro itens de DoD de "Web completo", com o peso no
**backend** (INV-7: toda derivação no servidor, o cliente pinta o frame total) e
o web fino:

1. **Modo "Prova em andamento"** — `domains/academus/api/prova_andamento.py`
   deriva, por minuto de exercício, quais sessões caem conforme
   `academus.lms_session_drop_rate` (modelo de sobrevivência cumulativo
   `1-(1-taxa)^m` sobre `fracao_do_sujeito`, determinístico por `derive_seed`).
2. **Console de investigação** — os cinco filtros de `02` §7 (período, usuário,
   IP, janela, autorização) são aplicados à consulta SQL da trilha
   (`repositorio.alteracoes_de_nota`), e a consulta emite o marcador `auto`
   `audit_query_performed`. `filter_window` é booleano (coluna `within_window`).
3. **Camada `reported` por persona** — `range-core/participant/reported.py`
   projeta, por persona vinculada ao token (D1), só a camada reportável (nunca
   ground truth), servida em `GET /participant/view`.
4. **Sete ações de continuidade** — `domains/academus/continuidade.py` mapeia
   cada ação a efeito (flag) e custo; `POST /participant/continuity` emite
   `continuity_action_taken` e o fold do `simulation_state` aplica o efeito
   genericamente lendo `payload["effects"]` (INV-4: a tabela de domínio entra
   por injeção em `montar()`, nenhum nome de flag chega ao core por import).

**Status por item de DoD com evidência: §3.** Todos VERDE, provados com oráculo
independente, par negativo e asserção sobre payload de API ou estado
reconstruído (o auditor confirmou na tabela DoD do laudo).

### Estrutura de diretórios (novidades da fase)

- `domains/academus/api/prova_andamento.py` — cadência da queda de sessão.
- `domains/academus/continuidade.py` — tabela ação→efeito+custo (fora de `api/`
  por causa da guarda de imports).
- `range-core/participant/reported.py` — projeção da camada `reported`.
- `range-core/web/exam-mode/`, `range-core/web/investigation-console/`,
  `range-core/web/persona-panel/` — as três telas (index.html + main.tsx +
  tipos.ts), pintando o frame do servidor, com banner (INV-10).
- Contrato: `$def continuity_action_taken_payload` em
  `contracts/events.schema.yaml` + constantes regeneradas.

### Endpoints criados

- `GET /exam/session-status` (academus-api) — frame TOTAL das sessões da prova.
- filtros novos em `GET /audit/grade-changes` (academus-api).
- `GET /participant/view` (participant-api) — leitura da camada `reported`.
- `POST /participant/continuity` (participant-api) — as sete ações.

### Migrações

**Nenhuma.** As colunas que os filtros do console usam (`actor_user_id`,
`source_ip`, `within_window`, `authorization_id`) já existiam na `audit_trail`
(migração `0004`). As cinco flags novas de continuidade são declarativas
(`domains/academus/flags.yaml`), não tabela.

### Variáveis de ambiente

**Nenhuma nova.** Reusa `academus.lms_session_drop_rate` e as flags de
continuidade do registry, `RANDOM_SEED`, e as credenciais/DSN já existentes.

### Pendências

**§6.** A fase fecha com as pendências herdadas dispostas (P7-15/16/20 e P5-2/P6-7
RESOLVIDAS; os gatilhos "esta fase" de P1-7/P6-5/P6-6/P6-12/P7-12 redatados) e
sete pendências nativas P8-1…P8-7 — as P8-5/6/7 nascidas da 4ª auditoria
(serving/composição, enum TS sem gate, cronômetro por insumo), todas registradas
para não vazarem para a Fase 9 sem dono.

### Próxima fase

**Fase 9 — Evidência e telemetria** (`07` §Fase 9): evidence-simulator +
telemetry-forwarder unificados, projeção de fatos, e a reconstrução < 3 s com
`telemetry_emitted` no volume de 4 h. O operador abrirá a Fase 9 em sessão nova
(um chat por fase), retomando a pauta herdada da §6 desta fase.
