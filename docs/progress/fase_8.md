# Fase 8 — Web completo

**Status: EM ANDAMENTO** — branch `fase-8-web-completo` aberta de `04bbb46`, a
`main` com a Fase 7 selada (PR #69). A linha de status existe porque
`check_readme_atual.py` decide *"a fase fechou?"* por ela; enquanto a fase
corre, ela diz EM ANDAMENTO, e só o veredito do auditor a move.

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
| P8-1 | Onda 2 da Estrutura Agêntica: instanciar os oito papéis e desenhar a reconciliação fase↔demanda — a decisão de abertura que a adoção agendou para cá | `DECIDIDA` | apresentação ao proprietário na abertura; ver abaixo |
| P1-7 | o id do inject pode vazar a linha; falta o mecanismo que impeça o próximo pack de decidir pelo vazamento | `ABERTA` | esta fase, junto do destino do pack (P7-9); detalhe em `fase_7.md` §"P1-7" |
| P4-8 | leitura síncrona no laço de eventos serializa e bloqueia em volume | `ABERTA` | medição de volume; detalhe em `fase_4.md`/`fase_7.md` §"P4-8" |
| P5-2 | a categoria "declarações do exercício" da trilha não tem produtor | `ABERTA` | a primeira ação de participante que altere estado de domínio — **material desta fase** (item 4, continuidade); detalhe em `fase_5.md` §"P5-2" |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores de `line_b_case.set` | `ABERTA` | reformulação na abertura; o schema v3 é o veículo quando houver delta real; detalhe em `fase_5.md`/`fase_7.md` §"P5-4" |
| P6-2 | `observable_impact` (start de `TTA`) não existe em contrato | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; detalhe em `fase_6.md` §"P6-2" |
| P6-3 | `before`/`after`/`since` dependem de uma gramática de `exercise_time` que não existe | `ABERTA` | os três gatilhos herdados da Fase 6, intactos; detalhe em `fase_6.md` §"P6-3" |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança | `ABERTA` | esta fase — `03` §5.3 a consome para separar erro de julgamento de lacuna de cobertura; detalhe em `fase_6.md`/`fase_7.md` §"P6-5" |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e não `Bash` | `LATENTE` | a primeira sessão que trabalhe em duas branches, ou esta fase; detalhe em `fase_6.md` §"P6-6" |
| P6-7 | rota que declara `emite` e não chama emissor nenhum | `ABERTA` | a próxima rota `emite` cuja fábrica já constrói o produtor — **material desta fase** (o web emite); detalhe em `fase_6.md` §"P6-7" |
| P6-8 | justificativa ausente devolve `409`, reservado a recusa de estado | `DECIDIDA` | a medição dos consumidores, ou a Fase 10; detalhe em `fase_6.md` §"P6-8" |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção (`sub == persona`) | `ABERTA` | a palavra do proprietário entre as saídas (a) e (b) — **toca persona, material desta fase**; detalhe em `fase_6.md` §"P6-12" |
| P6-13 | dezesseis violações plantadas da §3.5 da Fase 6 são atestação, não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável; detalhe em `fase_6.md` §"P6-13" |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual linha esta fase entrega; detalhe em `fase_7.md` §"P7-1" |
| P7-4 | consumo de `event_type` por selecionador sem allowlist declarada | `ABERTA` | **Fase 12** — degrau 1.5; detalhe em `fase_7.md` §"P7-4" |
| P7-5 | chamadores de cada emissor não varridos quando o contrato do emissor muda | `ABERTA` | **Fase 12** — degrau 2; detalhe em `fase_7.md` §"P7-5" |
| P7-10 | ~~o gerador de gabarito só produz Linha B — a Linha A não é materializada~~ | `RESOLVIDA` | nasce `domains/academus/seed/linha_a.py`: sintetiza o incidente (initial_access, privilege_escalation, exfiltration) do seed, e os `verification_predicates` do pack passam a ser os do incidente (VPN revogada + escopo desabilitado + ausência de exfiltração), não mais a contenção da Linha B; ver abaixo |
| P7-11 | condição temporal de branch (`before`/`after`) carrega e nunca ramifica | `ABERTA` | o gatilho da P6-3 (a gramática temporal nascer); detalhe em `fase_7.md` §"P7-11" |
| P7-12 | a superfície do hook do auditor acumulou cinco achados M/L sem rastro | `ABERTA` | a próxima edição da allowlist do auditor, ou esta fase; detalhe em `fase_7.md` §"P7-12" |
| P7-13 | o harness não planta violação onde a correção entrou | `ABERTA` | **Onda 3 da Estrutura Agêntica** (TDD endurecido); detalhe em `fase_7.md` §"P7-13" |
| P7-14 | seis afirmações de registro/teste sem disposição (varredura P7-6) | `ABERTA` | a varredura de fechamento desta fase (regra (b) da P7-6); detalhe em `fase_7.md` §"P7-14" |
| P7-15 | o extremo inclusivo contra a redação-alvo de `03` §3.2 | `ABERTA` | PR spec-change na abertura; o `spec-guardian` mede antes; detalhe em `fase_7.md` §"P7-15" |
| P7-16 | `PHASE_0_CHECKLIST.md` afirma demonstração que foi atestação | `ABERTA` | PR spec-change de uma linha na abertura; detalhe em `fase_7.md` §"P7-16" |
| P7-17 | ~~o destino da P2-17 (start do `frozen_interval`) passou em silêncio~~ | `RESOLVIDA` | medido: o start vem da âncora (`inject_engine.py:579`, fixado por teste) e chega intacto ao desconto; decisão (a) aceitar a âncora — é conformidade com a fixture normativa do contrato, e o sinal é o que `09` §3.1 quer; (b) spec-change fica como destino se um cenário fizer a largura importar; ver abaixo |
| P7-19 | ~~`check_progress_consistency` isenta `ENTREGA` de migrar, mesmo não entregue~~ | `RESOLVIDA` | `esta_concluida` lê a linha de Status de fechamento e `confere_pauta` reprova `ENTREGA` numa fase concluída; eixo_l prova nas três pernas; ver abaixo |
| P7-20 | `04` §8 declara `validate`/`migrate` que não existem | `ABERTA` | PR de alinhamento do `04` §8 na abertura; detalhe em `fase_7.md` §"P7-20" |

#### P8-1 — Onda 2: os oito papéis e a reconciliação fase↔demanda

**Nasce com a fase**, e é a decisão de abertura que a adoção da Estrutura
Agêntica agendou para cá (`docs/ADOCAO_ESTRUTURA_AGENTICA.md` §0.4). A Onda 2
traz os oito papéis de agente (PO, TL, UI, core, build, data, QA, doc) e a
máquina SDD de sete fases governando também o roadmap — e a primeira tarefa é
**reconciliar** duas contagens de "fase": a fase-marco do roadmap do Aurora
(âncora + auditoria de checkpoint) e a fase-demanda da máquina SDD do kit. É
`DECIDIDA` porque o gatilho chegou (a abertura); a forma da reconciliação é do
proprietário. Vence quando ele decidir o modelo e os oito papéis forem
instanciados sobre os agentes existentes (`scenario-designer`, `spec-guardian`,
`checkpoint-auditor`).

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

#### P7-15 — o extremo inclusivo × `03` §3.2

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-15". PR spec-change na abertura;
o `spec-guardian` mede o drift antes.

#### P7-16 — o checklist afirma demonstração que foi atestação

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-16". PR spec-change de uma linha
na abertura.

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
lá, não se justifica. Apresentado ao proprietário no fechamento desta fase.

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

#### P7-20 — `validate`/`migrate` declarados e inexistentes

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-20". PR de alinhamento do `04`
§8 na abertura.
