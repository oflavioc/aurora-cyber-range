# 09 — MODELO DE EVENTOS

Com o modelo das quatro verdades, praticamente tudo relevante é evento. Este documento define o envelope único, o catálogo e as regras de emissão.

---

## 1. Envelope universal

**Um envelope só.** Injects, marcadores de evidência, declarações, rollbacks, avaliações, submissões de mídia e decisões usam a mesma estrutura. Não existe estrutura paralela para evidência.

```json
{
  "event_id": "01J9F...",
  "event_type": "audit_query_performed",
  "truth_layer": "participant_action",
  "producer": "academus-api",
  "actor_id": "user-123",
  "persona": "ti",
  "object": { "type": "audit_trail", "filter": "period+user" },

  "exercise_time": "T+01:12:04",
  "exercise_timestamp": "2026-08-13T10:12:04",
  "wall_timestamp": "2026-08-13T11:47:31-03:00",
  "clock_multiplier": 1,
  "simulation_epoch": 1,

  "correlation": {
    "scenario_id": "ransomware-universidade",
    "inject_id": "B04",
    "causation_id": "01J9E...",
    "fact_id": null
  },

  "payload": {}
}
```

### 1.1 Campos obrigatórios

`event_id`, `event_type`, `truth_layer`, `producer`, `exercise_time`, `wall_timestamp`, `simulation_epoch`.

`actor_id` e `persona` são obrigatórios quando `truth_layer` for `participant_action` ou `evaluator_assessment`.

### 1.2 O que NÃO vai no envelope

**`objective_ids` não é emitido.** A ligação evento → objetivo ocorre na projeção, via `observability_hooks.yaml`.

Motivo: se a `academus-api` precisar saber que uma consulta satisfaz OBJ-03, o domínio passa a conhecer o desenho de exercício e a fronteira core/adapter vaza. Efeito colateral positivo: permite reavaliar um exercício antigo contra objetivos revisados.

---

## 2. As quatro verdades

`truth_layer` é campo obrigatório e assume exatamente um destes valores. Confundi-los é o erro que invalida o AAR.

| Camada | Significado | Quem produz | Reversível |
|---|---|---|---|
| `ground_truth` | O que de fato ocorreu no incidente simulado | motor, a partir de `ground_truth.yaml` | não |
| `observable_evidence` | O que o ambiente permite descobrir | projeções de fato, aplicação | não |
| `participant_action` | O que a equipe fez, viu ou **declarou** | aplicação instrumentada | nunca |
| `evaluator_assessment` | O que o avaliador julgou | gm-console | nunca |
| `facilitation` | O que o facilitador fez com a **simulação** | gm-console, inject-engine | nunca |

**São cinco valores, e quatro verdades.** `facilitation` não é uma quinta camada do modelo de `00_MASTER_SPEC.md` §3 — é ortogonal a ele. Os quatro primeiros afirmam algo sobre o incidente; `facilitation` afirma algo sobre a máquina de exercício. Ver `00_MASTER_SPEC.md` §3.1 para a razão de ser valor à parte em vez de ser mapeado em um dos quatro.

A tabela desta seção listava quatro valores enquanto o catálogo da §4.1 agrupava em cinco. Era divergência interna deste documento, resolvida no `spec-change` `facilitation-e-separate-incident`.

### 2.1 Declaração não é verdade

`containment_declared` é `participant_action`. **Nunca** altera `ground_truth`.

Se declaração alterasse o estado do mundo, declarar contenção cedo melhoraria a métrica mesmo com a contenção errada — incentivo perverso que destrói a validade da medição.

O motor avalia contenção real por predicado próprio (`03_EXERCISE_DESIGN.md` §3.2).

---

## 3. Simulation epoch

Rollback não apaga. Incrementa epoch.

```
epoch 0
  A01
  A02
  incident_declared          ← permanece no store
  A03
  rollback_performed → A02

epoch 1
  A03 (novamente)
  decisão diferente
```

Todo evento carrega `simulation_epoch`. O AAR sabe quais eventos ocorreram em linha temporal posteriormente rebobinada, sem perdê-los.

### 3.1 Motivo do rollback e semântica métrica

Rótulo sem consequência não serve. Cada motivo tem efeito definido:

| `reason` | Efeito no AAR | Efeito nas métricas |
|---|---|---|
| `technical_failure` | Epoch anterior marcada como falha do range | **Relógio de métricas congelado** entre o inject falho e a retomada. A equipe não é penalizada por bug do ambiente |
| `rehearsal` | Epoch descartada do AAR | Nenhum evento da epoch entra em cálculo |
| `facilitation` | Epoch anterior preservada como contexto | Métricas recomputadas a partir da nova epoch, com nota |
| `adjudication` | Epoch anterior preservada e **sinalizada** | Métricas da nova epoch, com registro do motivo da anulação |

`adjudication` é o caso em que o facilitador anula uma decisão por uso de informação fora de banda. Precisa aparecer no debriefing.

---

## 4. Catálogo de eventos

`contracts/events.schema.yaml` é registro fechado. Mesmo padrão do contrato de flags: constantes geradas para Python e TypeScript, e CI que falha com `event_type` não registrado.

Motivo: um `event_type` com erro de digitação nunca dispara. O marcador de evidência silenciosamente não é coletado, o objetivo nunca é satisfeito, a branch nunca ramifica — e ninguém percebe até o exercício ao vivo. É a falha mais cara possível.

### 4.1 Catálogo v1

**ground_truth** — `fact_materialized`, `attack_stage_reached`, `verification_predicate_satisfied`

**observable_evidence** — `evidence_source_released`, `evidence_source_accessed`, `telemetry_emitted`

**participant_action** — `inject_viewed`, `audit_query_performed`, `evidence_source_opened`, `incident_declared`, `separate_incident_declared`, `classification_declared`, `containment_declared`, `service_restoration_declared`, `integrity_validation_declared`, `assessment_submitted`, `communication_submitted`, `regulatory_notice_submitted`, `continuity_action_taken`, `vpn_access_revoked`, `identity_scope_disabled`, `decision_made`, `capability_gap_declared`

> `separate_incident_declared` foi acrescentado no `spec-change` `facilitation-e-separate-incident`. Ele já era usado como evidência `auto` do OBJ-03 em `03_EXERCISE_DESIGN.md` §1.1 e na §6 deste documento, sem constar do catálogo — e o catálogo é **registro fechado**, com CI que falha em `event_type` não registrado. Um `objectives.yaml` escrito conforme o exemplo normativo do `03` seria recusado pelo linter.
>
> Declarar que são **dois** incidentes é ação distinta de declarar **um**: é o objeto do OBJ-03, "reconhecer incidentes concorrentes". Reaproveitar `incident_declared` apagaria a distinção que o objetivo mede. É exatamente a classe de falha que `04_SCENARIO_SCHEMA.md` §6.2 descreve — o `event_type` inexistente que nunca dispara e que ninguém percebe até o exercício ao vivo.

**evaluator_assessment** — `bars_score_submitted`, `observed_marker_set`, `qualitative_note_added`

**facilitation** — `inject_fired`, `rollback_performed`, `branch_selected`, `exercise_started`, `exercise_paused`, `exercise_reset`

---

## 5. Projeções

```
EVENT STORE (append-only, imutável)
    │
    ├──→ simulation_state      ← ROLLBACK reconstrói esta
    ├──→ objective_evidence    ← binding via observability_hooks
    ├──→ metrics               ← pareadas declaração × verificação
    ├──→ calibration           ← assessments × defensibility
    └──→ aar_timeline          ← com epochs e anotação de rollback
```

Nenhuma projeção escreve no store. Toda projeção é reconstruível do zero.

## 6. Instrumentação

`domains/<adapter>/observability_hooks.yaml` mapeia ação da aplicação a `event_type` do catálogo:

```yaml
hooks:
  - event_type: audit_query_performed
    trigger: "GET /audit/grade-changes com filtro de período e agrupamento por usuário"
    producer: academus-api
    payload_fields: [period_start, period_end, group_by, result_count]

  - event_type: vpn_access_revoked
    trigger: "POST /identity/revoke com escopo vpn"
    producer: federated-identity-simulator
    payload_fields: [scope, principal]
```

E `scenarios/<pack>/objectives.yaml` faz o binding:

```yaml
OBJ-03:
  competency: incident_triage
  rubric: incident_triage.v2
  evidence:
    auto: [audit_query_performed, separate_incident_declared]
    observed: [articulated_competing_hypotheses]
```

O core responde por **como pontuar** a competência. O pack responde por **onde ela se manifesta**.
