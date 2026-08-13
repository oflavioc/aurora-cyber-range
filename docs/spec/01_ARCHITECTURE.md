# 01 — ARQUITETURA

---

## 1. Camadas

| Camada | Conteúdo | Reutilizável |
|---|---|---|
| **range-core** | exercise-clock, event store, state projection, inject-engine, flag registry, telemetry-forwarder, evidence-simulator, gm-console, participant-view, wallboard-shell, AAR, rubrics library | Sim |
| **domain adapter** | entidades de negócio, telas, painéis do wallboard, flags, eventos de telemetria, geradores de evidência | Não |

Adapters: `academus` (implementar completo), `prontus` (stub + interface apenas).

## 2. Layout de repositório

```
range-core/
  clock/              exercise-clock, dual timestamp
  events/             event store append-only, envelope único, catálogo
  state/              flag registry, projection, snapshot, rollback
  engine/
    loader/           carga e validação de pack
    migrations/       migrações de schema_version
    branching/        avaliação de condições e ramificação
  objectives/         binding evento→objetivo, scoring, calibração (Brier)
  rubrics/            biblioteca BARS versionada (incident_triage.v2 etc.)
  metrics/            pares declaração × verificação + TTA, TTT, TTCM
  telemetry/          CEF/syslog forwarder
  evidence/           projeção de fatos → fontes de evidência e CEF
  aar/                geração do After-Action Report
  api/
  web/
    gm-console/
    participant-view/
    wallboard-shell/
domains/
  academus/
    models/ api/ web/ seed/ panels/
    flags.yaml
    telemetry_events.yaml
    evidence_generators/
    observability_hooks.yaml     pontos de coleta de evidência automática
  prontus/
    STUB.md  flags.yaml
scenarios/
  academus/
    ransomware-universidade/
    fraude-academica-express/
contracts/
  state_flags.schema.yaml
  scenario.schema.v2.yaml
  objectives.schema.yaml
  evidence.schema.yaml
  events.schema.yaml            catálogo fechado de event_type
  ground_truth.schema.yaml
tools/                          verificadores de invariante executados no CI
  check_core_boundary.py
  check_contract_literals.py
  check_event_envelope.py
  check_security_constraints.py
  check_synthetic_data.py
  codegen.py                    gera constantes; --check compara sem escrever
docs/
  spec/  progress/
```

**Verificadores de CI obrigatórios.** São **seis**, todos em `tools/`, todos por AST ou leitura de contrato — nunca por grep. Regex fica no hook de feedback rápido; o CI precisa enxergar import dinâmico, alias e outros casos que regex perde.

| Verificador | Invariante que guarda |
|---|---|
| `check_core_boundary.py` | `range-core/` não importa nada de `domains/` |
| `check_contract_literals.py` | nenhum literal de flag ou de `event_type` fora dos geradores |
| `check_event_envelope.py` | nenhum evento emitido carrega `objective_ids` |
| `check_security_constraints.py` | restrições funcionais de `05_SECURITY_REQUIREMENTS.md` §1 |
| `check_synthetic_data.py` | IPs, domínios e identificadores dentro das faixas sintéticas |
| `codegen.py --check` | constantes Python e TypeScript sincronizadas com os contratos |

`codegen.py --check` compara **em memória** os artefatos gerados com os que estão em disco e sai com código diferente de `0` em divergência. **Nunca escreve.** Justamente por isso, `git diff --exit-code` depois dele é vacuoso e não prova nada — a verificação é o próprio código de saída.

---

## 3. Relógios

Três marcas temporais, nunca uma só.

```json
{
  "exercise_time": "T+00:47:12",
  "exercise_timestamp": "2026-08-13T09:47:12",
  "wall_timestamp": "2026-08-13T10:32:16-03:00",
  "clock_multiplier": 5
}
```

Telemetria carrega adicionalmente `ingest_time`, distinto de `event_time`.

**exercise-clock**: T0 definido pelo facilitador; PAUSAR congela e impede disparo agendado; multiplicador 1x / 5x / 20x para ensaio; `clock_multiplier` gravado em cada evento para reconstrução.

**Congelamento por falha do range**: rollback com `reason: technical_failure` congela o relógio de métricas entre o inject falho e a retomada (`09_EVENT_MODEL.md` §3.1). O clock de exercício continua correndo; apenas a projeção de métricas desconta o intervalo.

---

## 4. Estado — cinco camadas

Rollback das flags **não é** rollback do exercício.

| Camada | O que é | Reversível | Persistência |
|---|---|---|---|
| **Simulation State** | flags do contrato | **Sim** — projeção reconstruída | Redis (projeção) + event store |
| **Business State** | notas, matrículas, submissões, documentos | Não por rollback; só por reset total | Postgres |
| **Participant Actions** | decisões, declarações, consultas, avaliações de caso | **Nunca** | Event store |
| **Facilitation Audit** | disparos, rollbacks, motivo, papel | **Nunca** | Event store |
| **Telemetry State** | projeções emitidas, cursor de replay | Não apaga; reemissão é novo evento | Log + event store |

### 4.1 Event store e projeções

Envelope único, catálogo fechado, `truth_layer` obrigatório — ver `09_EVENT_MODEL.md`.

```
EVENT STORE (append-only, imutável)
    │
    ├──→ simulation_state      ← ROLLBACK reconstrói esta
    ├──→ objective_evidence
    ├──→ metrics
    ├──→ calibration
    └──→ aar_timeline
```

Nenhuma projeção escreve no store. Toda projeção é reconstruível do zero.

### 4.2 Rollback incrementa epoch

`rollback_performed` grava `to_inject_id`, `by_user`, `role`, `reason` e incrementa `simulation_epoch`. **Nada é removido.** Eventos da epoch anterior permanecem, marcados, e o AAR os renderiza como linha temporal rebobinada.

Motivos e sua semântica métrica: `09_EVENT_MODEL.md` §3.1.

**RESET TOTAL** grava `exercise_reset`, restaura defaults do contrato e o snapshot de business state do start. É recomeço, não correção.

### 4.3 Por que business state não reverte

Se um participante alterou nota, revogou VPN ou emitiu documento, isso aconteceu. Reverter gera estado impossível — evento na trilha de auditoria sem correspondente no banco — e destrói o artefato investigativo central.

---

## 5. Contrato de flags

### 5.1 Namespacing

`core.*` para o motor, `<adapter>.*` para domínios. Evita colisão quando dois domínios coexistirem.

### 5.2 Declaração

`domains/<adapter>/flags.yaml`, validado contra `contracts/state_flags.schema.yaml`:

```yaml
flags:
  - name: academus.enrollment_offline
    type: boolean
    default: false
    category: availability        # availability | integrity | confidentiality |
                                  # identity | performance | narrative | regulatory
    domain_area: academic         # academic | financial | research |
                                  # identity | infrastructure | communication
    severity_weight: 8            # 0–10, alimenta o índice de saúde institucional
    wallboard_group: "Matrícula"
    consumers: [academus-api, academus-web, wallboard]
    effect_ui: "Portal de matrícula retorna 503 com página de manutenção"
    reversible: true

  - name: academus.grade_integrity_suspect
    type: boolean
    default: false
    category: integrity
    domain_area: academic
    severity_weight: 10
    wallboard_group: "Integridade Acadêmica"
    consumers: [academus-api, academus-web, wallboard]
    effect_ui: "Banner de notas sob verificação; histórico marcado como provisório"
    reversible: true
```

### 5.3 O que a taxonomia habilita

- **Wallboard gerado por convenção** — painéis derivados de `wallboard_group`; adicionar flag não exige tocar no wallboard
- **Codificação visual por `category`** — cor e ícone definidos no core
- **Índice de saúde institucional** — número único no telão, a partir dos `severity_weight` ativos
- **AAR segmentado** — impacto de disponibilidade separado de integridade e confidencialidade. No cenário acadêmico essa distinção é o aprendizado principal: o sistema volta, mas a confiança no dado não

### 5.4 Regras

- Nenhum serviço lê ou escreve flag não declarada
- Constantes tipadas geradas para Python e TypeScript. **Proibido string solta de flag no código**
- CI falha com flag não declarada
- Pack é validado contra as flags do seu adapter no boot; flag desconhecida impede subida do engine
- Aplicar o mesmo inject duas vezes produz projeção idêntica (idempotência)

---

## 6. Serviços do core

**inject-engine** — carrega pack, avalia branches, emite eventos de effect, alimenta projeção.

**wallboard-shell** — sem login, WebSocket, alto contraste, legível a 10 m. Renderiza por convenção a partir da taxonomia. Painéis específicos vêm do adapter. **Papel: narrativa, para a plateia.**

**participant-view** (`/plateia`) — projeção separada. Apenas `texto_para_plateia` do inject corrente, cronômetro de decisão, cronômetro de deadline de mídia.

**gm-console** — três papéis (`03_EXERCISE_DESIGN.md` §6), seletor de pack, disparo manual e agendado, PAUSAR / CONTINUAR / ROLLBACK / RESET, estado de flags, registro, geração de AAR.

**telemetry-forwarder** — CEF via Syslog UDP/TCP para destino laboratorial configurável. **A telemetria é projeção de fato canônico**, não emissão independente; `precursor_events.jsonl` é gerado, não autoral (`08_EVIDENCE_SIMULATOR.md`). Modo Live e modo Replay. Campos `src`, `dst`, `suser`, `severity`, `outcome`, `cnt`, `cs1`–`cs4`.

**evidence-simulator** — ver `08_EVIDENCE_SIMULATOR.md`.

**Observabilidade** — Prometheus (requests, erros, autenticações, sessões AVA, fila de matrícula) e Grafana com dashboard *Operações* e dashboard *Exercício*. **Papel: evidência, para o time azul.** Distinto do wallboard. Não construir o mesmo painel duas vezes.

---

## 7. Desempenho

- Contadores do wallboard mantidos em Redis, atualizados por evento
- **Proibido `COUNT(*)` sobre tabelas de nota ou matrícula em rota de tempo real**
- Seed via `COPY` / `executemany`, nunca ORM linha a linha. Alvo: dataset completo em < 5 min
- Reconstrução de projeção a partir do event store deve completar em < 3 s para exercício de 4 h
