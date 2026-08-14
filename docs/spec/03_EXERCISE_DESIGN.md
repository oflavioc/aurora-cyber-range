# 03 — DESENHO DE EXERCÍCIO

O que o exercício pretende **medir**. Precedência sobre decisões de UX quando houver conflito.

---

## 1. Objetivos de aprendizagem

### 1.1 Contrato

```yaml
objectives:
  OBJ-03:
    title: "Reconhecer incidentes concorrentes"
    competency: incident_triage
    rubric: incident_triage.v2          # versão da rubrica no core
    expected_behavior:
      - "manter hipóteses concorrentes explicitamente registradas"
      - "não atribuir alteração de notas ao ransomware sem evidência correlacional"
    evidence:
      auto:
        - audit_query_performed
        - separate_incident_declared
      observed:
        - id: articulated_competing_hypotheses
          prompt_to_evaluator: "A equipe verbalizou mais de uma hipótese antes de convergir?"
    scoring:
      excellent: "<= 25 min e hipótese separada declarada"
      adequate:  "<= 45 min, mesmo sem declaração formal"
      poor:      "atribui Linha B à Linha A sem investigação"
    metric_binding: TTT
    debrief_questions:
      - "Em que momento decidiram que era um único incidente? O que sustentava isso?"
```

**Divisão de responsabilidade:** o core responde por **como pontuar** a competência (rubrica versionada). O pack responde por **onde ela se manifesta** (quais evidências, neste domínio).

### 1.2 Evidência: apenas duas classes

`auto` — emitida pela aplicação instrumentada, com produtor identificável. Declarada em `observability_hooks.yaml` (`09_EVENT_MODEL.md` §6).

`observed` — marcada por avaliador, sempre com pergunta explícita e âncora BARS. Nunca "dê uma nota".

**Não existe classe `derived`.** Inferências são calculadas pelo AAR a partir de eventos `auto`. Ou o sistema observou, ou uma pessoa observou — a ontologia permanece binária e a proveniência, rastreável.

### 1.3 Objetivos do pack `ransomware-universidade`

| ID | Título | Competência | Métrica |
|---|---|---|---|
| OBJ-01 | Classificar severidade e escalar para crise | `escalation` | TTA |
| OBJ-02 | Coordenar TI × Reitoria × Jurídico × DPO × Comunicação | `cross_functional_coordination` | — |
| OBJ-03 | Reconhecer incidentes concorrentes | `incident_triage` | TTT |
| OBJ-04 | Resistir a viés de confirmação | `analytical_rigor` | calibração |
| OBJ-05 | Decidir sobre continuidade do AVA e das provas | `business_continuity` | TTCD/TTCV |
| OBJ-06 | Decidir sobre suspensão da matrícula com trade-off explícito | `risk_decision` | TTCD |
| OBJ-07 | Validar integridade antes de liberar restauração | `integrity_assurance` | TTID/TTIV |
| OBJ-08 | Comunicar sob incerteza sem afirmar número não verificado | `crisis_communication` | TTCM |
| OBJ-09 | Cumprir obrigação regulatória no prazo | `regulatory_compliance` | TTCM |
| OBJ-10 | Distinguir recuperação técnica de recuperação de confiança no dado | `integrity_assurance` | TTIV − TTRV |

**OBJ-10 é o objetivo-âncora.** Toda a estrutura de métricas pareadas existe para torná-lo mensurável.

---

## 2. Rubricas BARS

### 2.1 Localização e versionamento

`range-core/rubrics/<competency>.<version>.yaml`. **Versionada.** O pack referencia `incident_triage.v2`; o AAR grava a versão usada.

**Comparabilidade entre exercícios vale apenas dentro da mesma versão de rubrica.** Comparar pontuação de `v1` com `v2` exige mapeamento declarado, ou o AAR recusa a comparação. Sem essa regra, revisar uma âncora invalida silenciosamente todo o histórico.

### 2.2 Formato

```yaml
competency: crisis_communication
version: v2
scale: 0-4
anchors:
  0: "Nenhuma resposta emitida dentro do exercício."
  1: "Resposta fora do prazo, ou internamente contraditória."
  2: "Resposta no prazo, mas sem distinguir fato confirmado de incerteza."
  3: "Comunica fatos confirmados, incertezas declaradas, ações em curso e
      horário do próximo update."
  4: "Além do nível 3, mantém consistência verificável entre canais e
      corrige publicamente informação anterior quando novo fato a contradiz."
```

### 2.3 Competências v1

`incident_triage`, `escalation`, `cross_functional_coordination`, `analytical_rigor`, `business_continuity`, `risk_decision`, `integrity_assurance`, `crisis_communication`, `regulatory_compliance`. Cinco âncoras cada, redigidas em comportamento observável — nunca em adjetivo.

### 2.4 Calibração entre avaliadores

Divergência ≥ 2 pontos na mesma competência gera alerta no AAR. Não resolve automaticamente; sinaliza para o debriefing.

---

## 3. Métricas pareadas

MTTD e MTTR são ambíguos demais. Substituídos por pares **declaração × verificação**.

| Par | Declaração (participante) | Verificação (ground truth) |
|---|---|---|
| Contenção | **TTCD** — `containment_declared` | **TTCV** — predicado de contenção satisfeito |
| Restauração | **TTRD** — `service_restoration_declared` | **TTRV** — predicado de restauração satisfeito |
| Integridade | **TTID** — `integrity_validation_declared` | **TTIV** — ver §3.3 |

Métricas simples, sem par:

| Sigla | Start | Stop |
|---|---|---|
| **TTA** | primeiro inject com impacto observável | `incident_declared` |
| **TTT** | `incident_declared` | `classification_declared` com severidade e escopo |
| **TTCM** | inject com `requires_response` | submissão correspondente |

### 3.1 Predicados de verificação

TTCV e TTRV só são computáveis se o `ground_truth.yaml` declarar **o que é** contenção e restauração neste incidente:

```yaml
verification_predicates:
  containment:
    all:
      - event: vpn_access_revoked
      - event: identity_scope_disabled
        payload: { principal: svc_academus }
      - absence_of:
          fact_class: exfiltration
          since: self
  service_restoration:
    all:
      - flag_false: academus.enrollment_offline
      - flag_false: academus.lms_degraded
```

O motor avalia continuamente e emite `verification_predicate_satisfied` no instante em que a condição passa a valer. Sem esta seção, o pack não carrega.

### 3.2 O delta é o achado, nos dois sentidos

- **TTCD < TTCV** — asseguração prematura. A janela é o tempo em que a instituição operou acreditando estar contida sem estar. O AAR lista os `ground_truth` eventos ocorridos dentro dessa janela como **evidências incompatíveis com a declaração**.
- **TTCD > TTCV** — lacuna de consciência situacional. A equipe estava contida e não sabia; manteve degradação desnecessária.

Redação-alvo no AAR: *"Contenção declarada em T+31. Evento incompatível com contenção em T+38. Contenção verificável apenas em T+52."*

Isso mede qualidade da decisão, não velocidade.

### 3.3 TTIV não é simétrico

Contenção e restauração são **estados do mundo** — o ground truth sabe se valem. Integridade validada não é: é propriedade da **qualidade da avaliação da equipe**.

`TTIV` = instante em que o conjunto de `assessment_submitted` atinge o limiar de calibração definido no pack (`calibration.threshold`), medido contra a defensibilidade do gabarito (§5).

Forçar simetria aqui produziria um número inexplicável no debriefing.

### 3.4 Ações de declaração são requisito funcional

| Ação | Quem | Evento |
|---|---|---|
| Declarar incidente | qualquer persona | `incident_declared` |
| Declarar classificação | TI | `classification_declared` |
| Declarar contenção | TI | `containment_declared` |
| Declarar restauração por serviço | TI | `service_restoration_declared` |
| Declarar integridade validada | Pró-Reitoria + contrassinatura TI | `integrity_validation_declared` |
| Submeter posicionamento | Comunicação | `communication_submitted` |
| Submeter notificação regulatória | DPO | `regulatory_notice_submitted` |
| Submeter avaliação de caso | TI / Pró-Reitoria | `assessment_submitted` |

Cada uma grava evento com autor, papel, ambos os relógios, epoch e justificativa livre.

### 3.5 Congelamento por falha do range

Rollback com `reason: technical_failure` congela o relógio de métricas entre o inject falho e a retomada. A equipe não é penalizada por bug do ambiente. Ver `09_EVENT_MODEL.md` §3.1.

---

## 4. Ground truth, observável e reportado

```yaml
information_distribution:
  - persona: ti
    at: "T+00:20"
    content: "volume anômalo de leitura detectado; escopo desconhecido"
    confidence: low
  - persona: dpo
    at: "T+01:10"
    content: "estimativa preliminar de 4.000 registros"
    confidence: medium
    note: "subestimativa deliberada — ground truth é 12.480"
  - persona: comunicacao
    at: "T+01:25"
    content: "imprensa afirma 28.000 alunos vazados"
    confidence: none
    source: external
```

Ninguém tem a mesma informação ao mesmo tempo. Consequência avaliativa: como o motor conhece o ground truth, o AAR verifica **automaticamente** se a instituição comunicou número não verificado. Liga OBJ-04 e OBJ-08.

---

## 5. Calibração (Linha B)

### 5.1 Submissão

```yaml
assessment:
  case_id: GC-029
  classification: suspicious       # suspicious | legitimate | inconclusive
  confidence: 72                   # 0–100
  evidence: [DBA-28391, DBA-28402]
  rationale: "Alteração fora da janela, sem autorização, conta incompatível
              com a disciplina, horário fora de expediente."
```

Antes de submeter, a equipe declara **escopo revisado** (`review_scope`: período, população, critério). Isso separa erro de julgamento de lacuna de cobertura.

### 5.2 Gabarito

Cada caso em `ground_truth.yaml` carrega `defensibility ∈ [0,1]`:

| Conjunto | Defensibilidade | Comportamento esperado |
|---|---|---|
| Indevido comprovado | 1.0 | Alta confiança na irregularidade |
| Genuinamente ambíguo | 0.5 | Confiança baixa/moderada e escalonamento |
| Legítimo com aparência suspeita | 0.0 | Investigação sem falsa acusação |
| Ruído de manutenção / delegação | 0.0 | Descartado |

### 5.3 Escore

Brier sobre os casos dentro do escopo revisado:

```
brier = média( (confidence/100 − defensibility)² )
```

Menor é melhor. Comparável entre exercícios e entre equipes.

Caso dentro do escopo e não avaliado conta como `confidence = 0`. Caso **fora** do escopo revisado não entra no Brier — entra como **lacuna de cobertura**, reportada em separado.

### 5.4 Sinalizações comportamentais

| Sinal | Condição | Leitura |
|---|---|---|
| **Overconfidence** | `confidence ≥ 80` sobre `defensibility ≤ 0.2` | Falsa acusação. Anular nota de formando inocente |
| **Underconfidence** | `confidence ≤ 30` sobre `defensibility = 1.0` | Evidência forte, conclusão não alcançada |
| **Lacuna de cobertura** | indevido comprovado fora do escopo revisado | Investigação não chegou lá |

Para a Linha B, **overconfidence é pedagogicamente mais interessante que falso negativo**: o custo institucional de acusar indevidamente supera o de deixar um caso duvidoso em aberto. O AAR trata os dois sinais separadamente e não os compensa entre si.

---

## 6. Personas

| Persona | Painel | Declarações |
|---|---|---|
| Reitoria | índice de saúde institucional, imprensa | `incident_declared` |
| Pró-Reitoria Acadêmica | calendário, diplomas, colação, matrícula | `integrity_validation_declared`, `assessment_submitted` |
| TI | status de serviços, contenção, recuperação | todas as técnicas |
| DPO | titulares afetados, rascunho de notificação | `regulatory_notice_submitted` |
| Jurídico | exposição de responsabilidade | — |
| Pesquisa | projetos afetados, PI | — |
| Comunicação | fila de imprensa, posicionamento | `communication_submitted` |

Cada persona vê apenas sua camada `reported`.

---

## 7. Papéis de facilitação

**`facilitador`** — timeline integral, linhas, ground truth, GM_NOTES, consequências, PAUSAR / ROLLBACK / RESET, AAR.

**`operador`** — apenas fila de injects liberados, com `titulo_operacional` neutro, botão de disparo. **Não vê**: linha, `descricao_facilitador`, GM_NOTES, ground truth, timeline futura, consequências. Se enxergar que existe Linha B, o efeito de triagem sob viés é destruído. Teste é sobre payload de API, não sobre interface.

**`avaliador`** — read-only, formulário BARS com âncoras carregadas do core, marcação de evidências `observed`.

Todo disparo e rollback registram autor, papel, motivo e epoch.

---

## 8. Finalidade comercial e separação de camadas

O AURORA pode ser operado em contexto comercial — um fornecedor conduzindo o exercício para um cliente. Essa finalidade é legítima e muda o desenho do AAR, mas **não pode contaminar o cenário**.

### 8.1 O que nunca entra no exercício

Nome de fornecedor, nome de produto, arquitetura de referência de portfólio, ou qualquer conteúdo que sugira uma solução específica. Isso vale para injects, evidências, dashboards, wallboard e `decision_point`.

Motivo: um exercício em que a resposta "certa" aponta para um produto deixa de medir a capacidade da equipe e passa a medir se ela adivinhou o vendor. Destrói a validade da avaliação e o participante percebe.

### 8.2 O que entra no AAR

Lacuna de capacidade, nomeada por **função de controle**, nunca por produto.

Exemplo do que é permitido: *"A revogação de acesso da conta de serviço levou 41 minutos porque não havia mecanismo centralizado de revogação de sessão federada. TTCV foi 38 minutos maior que TTCD por essa razão."*

Exemplo do que é proibido: *"Recomenda-se a adoção de [produto] para reduzir esse tempo."*

A diferença é que a primeira é conclusão do exercício, mensurada; a segunda é conclusão comercial, e pertence à conversa que vem depois, conduzida por pessoas, fora do relatório.

### 8.3 Lacuna de capacidade como resposta registrável

Um `decision_point` pode ter, entre as opções, uma que declare ausência de capacidade — e essa declaração é dado, não desistência.

Quando uma equipe responde "não conseguimos fazer isso no tempo do exercício porque não temos o mecanismo", isso é o achado mais valioso da rodada. O AAR registra a lacuna, o objetivo de aprendizagem afetado e a métrica impactada.

Ver `04_SCENARIO_SCHEMA.md` §5 para o campo `capability_gap` na opção, e `09_EVENT_MODEL.md` §4.1 para o `event_type` correspondente.

### 8.4 Neutralidade do pacote

Um scenario pack não declara fornecedor. Se um facilitador quiser material de posicionamento, ele vive fora de `scenarios/`, não é carregado pelo engine e não aparece em nenhuma superfície do exercício.

---

## 9. After-Action Report

1. **Desempenho por objetivo** — evidências `auto` e `observed` distinguidas, classificação, rubrica e versão usadas
2. **Métricas pareadas** — TTCD/TTCV, TTRD/TTRV, TTID/TTIV com deltas e leitura; janelas de asseguração prematura com os eventos incompatíveis listados; TTA, TTT, TTCM
3. **`TTIV − TTRV` em destaque** — exposição não resolvida sinalizada quando restauração verificada ocorre sem integridade validada
4. **Calibração** — Brier, overconfidence, underconfidence, lacuna de cobertura, com casos nominais
5. **Rubricas BARS** — por competência e persona, com âncora textual atingida e divergência entre avaliadores
6. **Informação × verdade** — comunicação externa comparada ao ground truth
7. **Timeline por epoch** — rollbacks anotados com motivo; eventos de epoch rebobinada preservados e marcados
8. **Impacto por `category`** — disponibilidade, integridade, confidencialidade
9. **Facilitação** — quem disparou o quê, sob qual papel, com que motivo de rollback
10. **Perguntas de debriefing** — agregadas dos objetivos acionados
11. **Notas qualitativas** — rotuladas como impressão, separadas das métricas
12. **Lacunas de capacidade declaradas** — cada `capability_gap_declared` com a função de controle ausente, o objetivo de aprendizagem afetado e a métrica impactada, nomeadas por função e nunca por produto (§8.2)

Linha A, Linha B e ruído separados em todas as seções.
