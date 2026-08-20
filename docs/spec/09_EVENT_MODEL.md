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

`event_id`, `event_type`, `truth_layer`, `producer`, `exercise_time`, `exercise_timestamp`, `wall_timestamp`, `clock_multiplier`, `simulation_epoch`.

**As três marcas temporais são obrigatórias**, conforme `01_ARCHITECTURE.md` §3, e `clock_multiplier` com elas, conforme `00_MASTER_SPEC.md` §5.6.

Esta lista omitia `exercise_timestamp` e `clock_multiplier`, e a omissão tinha custo. Sem `exercise_timestamp`, evento de `simulation_epoch` 2 e evento de epoch 0 não são ordenáveis entre si na linha do exercício — só dentro da própria epoch. Sem `clock_multiplier`, a timeline do AAR não é reconstruível quando o multiplicador mudou no meio, porque o mesmo intervalo de relógio de parede corresponde a durações diferentes de exercício.

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

**O avaliador de predicados e a epoch.** A satisfação **pertence à epoch em que foi emitida** — o `simulation_epoch` do próprio `verification_predicate_satisfied`. Depois de um rollback, o avaliador **reavalia sobre a linhagem corrente** (`01_ARCHITECTURE.md` §4.1); se ela satisfaz, emite **na epoch nova**. A emissão continua sendo por transição: o que mudou não foi o gatilho, foi o mundo sobre o qual ele é lido.

**O efeito é o mesmo nos quatro motivos, e isso é informação e não omissão.** O avaliador sempre reavalia sobre a corrente; o que difere entre eles é o que o **consumidor de métrica** faz com as epochs, e isso já está nas colunas acima. Uma coluna a mais nesta tabela teria quatro células iguais — e regra que não decide caso nenhum é pior que regra ausente, porque parece proteger.

**Os três negativos, nomeados porque são testes:**

- **predicado meio-revertido não existe.** As folhas `event` e as folhas de flag leem **o mesmo mundo** — a linhagem corrente. Sem esta seção, as primeiras liam o fluxo cru e as segundas o estado reconstruído, e um rollback deixava o predicado satisfeito pela metade;
- **satisfação de epoch abandonada não conta na corrente.** O evento continua no store, legível e marcado (`01_ARCHITECTURE.md` §4.1), e o AAR o renderiza; o que ele não faz é sustentar `TTCV` da epoch nova;
- **rollback atravessando o ato dessatisfaz na corrente.** Revogação de VPN desfeita pelo corte deixa de valer para a contenção, e a contenção volta a ser não verificada — que é o que o facilitador quis dizer ao rebobinar.

---

## 4. Catálogo de eventos

`contracts/events.schema.yaml` é registro fechado. Mesmo padrão do contrato de flags: constantes geradas para Python e TypeScript, e CI que falha com `event_type` não registrado.

Motivo: um `event_type` com erro de digitação nunca dispara. O marcador de evidência silenciosamente não é coletado, o objetivo nunca é satisfeito, a branch nunca ramifica — e ninguém percebe até o exercício ao vivo. É a falha mais cara possível.

### 4.0 `effect_class` — o que o evento é, não quem o produziu

`truth_layer` responde **quem afirma**. `effect_class` responde **que espécie de coisa o evento é**. São ortogonais, e confundi-los reabre pela porta do contrato a distinção que §2.1 fecha pela porta da semântica.

| Valor | Significado |
|---|---|
| `state_effect` | Altera o estado do mundo simulado. Ocorreu, independente do que alguém creia ou declare |
| `declaration` | Afirma crença, juízo ou classificação. **Nunca** altera ground truth |
| `observation` | Registra que alguém acessou ou viu algo. Sem efeito no mundo e sem afirmação sobre ele |
| `machine` | Ato da máquina de exercício ou escrituração do motor. Não é ato de participante |

`vpn_access_revoked` e `containment_declared` são ambos `participant_action`. O primeiro é `state_effect` — o acesso caiu, e teria caído mesmo que ninguém declarasse coisa alguma. O segundo é `declaration` — a equipe afirma ter contido, e a afirmação não muda o mundo.

**Consequência normativa.** A folha `event` de um predicado de verificação só pode referenciar `event_type` que satisfaça **as duas** condições, ambas atributos declarados do catálogo: `effect_class: state_effect` **e** `metric_side: verification` (`00_MASTER_SPEC.md` §3.2) — ver também `03_EXERCISE_DESIGN.md` §3.1. Sem essa restrição, um pack pode declarar `containment: {all: [{event: containment_declared}]}`, e nele TTCD e TTCV passam a medir o mesmo instante. A consequência normativa 2 de `00_MASTER_SPEC.md` §3 — métrica pareada mede conclusão de ação datável por fora, e o delta é o achado — seria anulada por autoria de cenário, sem que nada falhe.

`verification_predicate_satisfied` é `machine` por um motivo que não admite exceção: se fosse `state_effect`, um predicado poderia referenciar o evento que o próprio predicado emite ao ser satisfeito.

**Nenhuma das duas condições basta sozinha, e cada uma barra o que a outra deixa passar.**

Só `effect_class` — a regra anterior a `00_MASTER_SPEC.md` §3.2 — admite `communication_submitted` e `regulatory_notice_submitted`, que são `state_effect` porque o **ato** tem efeito externo (§4.1). Eles são o *stop* de `TTCM`, métrica do lado da declaração: admiti-los como folha põe o mesmo `event_type` nos dois lados e destrói a disjunção que §3.2 exige.

Só `metric_side` admite `verification_predicate_satisfied`, que é `verification` por papel e `machine` por classe — e recairia exatamente na autorreferência que o parágrafo acima proíbe sem exceção. Por isso a regra é conjunção, e não escolha entre os dois atributos.

Em v1 a conjunção deixa **cinco** tipos referenciáveis: `fact_materialized`, `attack_stage_reached`, `continuity_action_taken`, `vpn_access_revoked` e `identity_scope_disabled`. Os predicados de exemplo de `03_EXERCISE_DESIGN.md` §3.1 e de `04_SCENARIO_SCHEMA.md` §3 continuam válidos, e a leitura *"contido = nenhum estágio novo alcançado"* que §4.1 justifica continua exprimível.

**A porta que fica fechada, e o portão que a abre.** Predicado sobre evento de comunicação — *"contido = regulador notificado"*, *"restaurado = público informado"* — passa a ser recusado, e a recusa **não é arbitrária**: §4.1 classifica esses dois eventos pelo **ato**, e é o ato que tem efeito externo; o **conteúdo** continua tratado como afirmação em `04_SCENARIO_SCHEMA.md` §7, que compara o número comunicado com o ground truth. Um predicado sobre eles mediria o ato — *"houve notificação"* — quando o que importa à contenção é o conteúdo, que já tem mecanismo próprio.

Se um cenário futuro precisar dessa referência, o caminho é **spec-change** que reabra o escopo com o mérito examinado, e não `metric_side` remendado num pack. Quem escrever o primeiro pack na Fase 7 encontra aqui a razão da recusa e o caminho de contestá-la.

### 4.1 Catálogo v1

| `truth_layer` | `event_type` | `effect_class` |
|---|---|---|
| `ground_truth` | `fact_materialized` | `state_effect` |
| `ground_truth` | `attack_stage_reached` | `state_effect` |
| `ground_truth` | `verification_predicate_satisfied` | `machine` |
| `observable_evidence` | `evidence_source_released` | `machine` |
| `observable_evidence` | `evidence_source_accessed` | `observation` |
| `observable_evidence` | `telemetry_emitted` | `machine` |
| `participant_action` | `inject_viewed` | `observation` |
| `participant_action` | `audit_query_performed` | `observation` |
| `participant_action` | `evidence_source_opened` | `observation` |
| `participant_action` | `incident_declared` | `declaration` |
| `participant_action` | `separate_incident_declared` | `declaration` |
| `participant_action` | `classification_declared` | `declaration` |
| `participant_action` | `containment_declared` | `declaration` |
| `participant_action` | `service_restoration_declared` | `declaration` |
| `participant_action` | `integrity_validation_declared` | `declaration` |
| `participant_action` | `assessment_submitted` | `declaration` |
| `participant_action` | `communication_submitted` | `state_effect` |
| `participant_action` | `regulatory_notice_submitted` | `state_effect` |
| `participant_action` | `continuity_action_taken` | `state_effect` |
| `participant_action` | `vpn_access_revoked` | `state_effect` |
| `participant_action` | `identity_scope_disabled` | `state_effect` |
| `participant_action` | `decision_made` | `declaration` |
| `participant_action` | `capability_gap_declared` | `declaration` |
| `evaluator_assessment` | `bars_score_submitted` | `declaration` |
| `evaluator_assessment` | `observed_marker_set` | `declaration` |
| `evaluator_assessment` | `qualitative_note_added` | `declaration` |
| `facilitation` | `inject_fired` | `machine` |
| `facilitation` | `rollback_performed` | `machine` |
| `facilitation` | `branch_selected` | `machine` |
| `facilitation` | `exercise_started` | `machine` |
| `facilitation` | `exercise_paused` | `machine` |
| `facilitation` | `exercise_resumed` | `machine` |
| `facilitation` | `exercise_reset` | `machine` |

**Trinta e três tipos.** Vinte e sete são inequívocos; os cinco abaixo são decisão registrada, e o sexto é o `verification_predicate_satisfied` já justificado acima.

- **`communication_submitted` e `regulatory_notice_submitted` são `state_effect`.** O *conteúdo* de uma comunicação é afirmação; o *ato* de emiti-la tem efeito externo — o público soube, o regulador foi notificado, o prazo regulatório correu. A classificação segue o ato. O conteúdo continua tratado como afirmação em outro lugar: `04_SCENARIO_SCHEMA.md` §7 compara o número comunicado com o ground truth.
- **`decision_made` é `declaration`.** A opção escolhida carrega `effects` que mutam flags, mas **quem muta o estado são os `effects`, não o evento**: `decision_made` registra que a equipe *escolheu*, e escolher é afirmação, do mesmo tipo que `containment_declared`. Classificá-lo por `state_effect` abriria `containment: {all: [{event: decision_made}]}`, satisfeito no instante do clique, **antes de qualquer efeito existir** — o mesmo buraco que este campo fecha, com outro nome. Se um cenário precisar que uma decisão conte como contenção verificada, o caminho é o `effect` dela materializar um fato e o predicado referenciar esse fato, preservando a cadeia **decisão → efeito → estado observável**.
- **`fact_materialized` e `attack_stage_reached` são `state_effect`.** São mudança do mundo, ainda que produzidas pelo motor. Isso permite um predicado dizer *"contido = nenhum estágio novo alcançado"*, que é objetivamente observável — o critério que §3.1 do `03` exige.

> `exercise_resumed` foi acrescentado no `spec-change` `exercise-resumed`, e o que o justifica é uma **assimetria**, não uma necessidade de implementação.
>
> `01_ARCHITECTURE.md` §6 dá ao gm-console quatro comandos de execução — PAUSAR / CONTINUAR / ROLLBACK / RESET — e o catálogo tinha evento para três deles. Num sistema cuja premissa é que o registro reconstrói tudo (`00_MASTER_SPEC.md` §5.5, e a leitura total de `01_ARCHITECTURE.md` §4.1), **comando de facilitação sem rastro é exceção não declarada**. A ausência não estava justificada em documento nenhum: tinha a forma de omissão, e não de desenho.
>
> **A consequência era um estado não reconstruível, e ele é estreito e concreto.** Sem evento de retomada, `exercise_paused` sem nada depois é o mesmo fluxo para *"ainda pausado"* e para *"retomado, e nada aconteceu desde então"*. A heurística que salvaria o caso — evento posterior implica retomada — **não vale**: `01_ARCHITECTURE.md` §3 bloqueia o disparo **agendado** durante a pausa e §6 mantém o **manual**, então um `inject_fired` posterior é compatível com o exercício ainda parado.
>
> Quem cobra é a Fase 4, cujo item de DoD manda o reinício do engine restaurar o exercício **a partir do event store** (`07_IMPLEMENTATION_PHASES.md`): sem este evento, o engine que reinicia acerta ou erra o estado de pausa sem ter como saber qual — e o erro é caro nos dois sentidos, porque subir correndo dispara inject agendado numa sala parada, e subir pausado congela uma sala em curso.
>
> **A duração da pausa não vai no payload, e a razão é a mesma que decidiu T3 de `06_ACCEPTANCE_TESTS.md`: extremos, nunca duração.** Com os dois eventos no fluxo, o intervalo é a distância entre os `wall_timestamp` deles, e nenhum campo novo é necessário. Sem o evento, a única saída era derivar por subtração — `Δwall − Δexercise / clock_multiplier` —, e essa conta **quebra** quando o multiplicador muda dentro do intervalo, o que é permitido e não é raro: trocar de 1x para 5x antes de retomar é operação normal de ensaio. Medido: numa pausa real de 660 s com troca de multiplicador no meio, a subtração devolve 420 s pelo multiplicador do extremo esquerdo. O evento não existe para carregar a conta — existe para que não haja conta.
>
> **Em `wall_timestamp`, e não em `exercise_timestamp`**, que é o espelho exato da decisão de T3: lá o campo é `exercise_timestamp` porque ele **exclui** a pausa; aqui é `wall_timestamp` porque durante a pausa ele é o único que corre. Os dois eventos carregam o mesmo `exercise_timestamp` por construção, e o intervalo medido nele seria zero.

> `separate_incident_declared` foi acrescentado no `spec-change` `facilitation-e-separate-incident`. Ele já era usado como evidência `auto` do OBJ-03 em `03_EXERCISE_DESIGN.md` §1.1 e na §6 deste documento, sem constar do catálogo — e o catálogo é **registro fechado**, com CI que falha em `event_type` não registrado. Um `objectives.yaml` escrito conforme o exemplo normativo do `03` seria recusado pelo linter.
>
> Declarar que são **dois** incidentes é ação distinta de declarar **um**: é o objeto do OBJ-03, "reconhecer incidentes concorrentes". Reaproveitar `incident_declared` apagaria a distinção que o objetivo mede. É exatamente a classe de falha que `04_SCENARIO_SCHEMA.md` §6.2 descreve — o `event_type` inexistente que nunca dispara e que ninguém percebe até o exercício ao vivo.

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

E `scenarios/<pack>/objectives.yaml` faz o binding. **A forma normativa do arquivo é a de `03_EXERCISE_DESIGN.md` §1.1**; o bloco abaixo é uma instância completa dela, mostrada aqui pelo que interessa a esta seção — o `event_type` do hook aparecendo em `evidence.auto`:

```yaml
objectives:
  OBJ-03:
    title: "Reconhecer incidentes concorrentes"
    competency: incident_triage
    rubric: incident_triage.v2
    evidence:
      auto:
        - audit_query_performed
        - separate_incident_declared
      observed:
        - id: articulated_competing_hypotheses
          prompt_to_evaluator: "A equipe verbalizou mais de uma hipótese antes de convergir?"
```

> Esta seção exibia uma forma **abreviada e divergente** do mesmo arquivo: sem o invólucro `objectives`, sem `title`, e com `observed` como sequência de strings em vez de sequência de marcadores com `id` e `prompt_to_evaluator`. Omitir `title` é abreviação; trocar o tipo de `observed` é **outra forma**, e um `objectives.yaml` escrito conforme aquele bloco era recusado pelo contrato — a falha que a §4 chama de "a mais cara possível", pela mesma razão que motivou o `spec-change` do `separate_incident_declared`.
>
> Corrigido alinhando este bloco à forma de `03` §1.1, e não o contrário: `03` §1 é onde o contrato de objetivos é definido, e esta seção o consome. Os dois blocos passam a ser validados contra o mesmo schema por `scripts/check_spec_examples.py`, então divergirem de novo deixa de ser possível em silêncio — que era o que tornava a duplicação perigosa.

O core responde por **como pontuar** a competência. O pack responde por **onde ela se manifesta**.
