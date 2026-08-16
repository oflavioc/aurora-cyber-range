# 00 — MASTER SPEC
## Aurora Cyber Range — Autoridade Normativa

Precedência sobre todos os demais documentos. Conflito entre dois documentos não-master deve ser escalado, nunca resolvido por inferência.

---

## 1. O que é

Motor reutilizável de exercícios de crise cibernética, com domínios acopláveis. Primeiro domínio: acadêmico (ACADEMUS — Universidade Aurora, 28.000 alunos, 1.200 professores, 5 campi). Segundo domínio (PRONTUS, hospitalar) existe como stub, para provar a fronteira arquitetural.

Usos: TTX executivo, cyber range defensivo, exercício de Blue Team, continuidade de negócios, simulação LGPD, sala de crise.

## 2. O que não é

Não é laboratório ofensivo. Não executa ataques, não hospeda malware, não contém vulnerabilidade explorável. Todos os efeitos de incidente são simulações de estado. Ver `05_SECURITY_REQUIREMENTS.md`.

---

## 3. Modelo das quatro verdades (estrutura normativa)

Este é o modelo central do sistema. Confundir duas destas camadas invalida o AAR.

```
        GROUND TRUTH
   o que de fato ocorreu
             │
             ↓
     OBSERVABLE EVIDENCE
  o que pode ser descoberto
             │
             ↓
  PARTICIPANT BELIEF / DECLARATION
  o que a equipe crê e declara
             │
             ↓
     EVALUATOR ASSESSMENT
   o que o avaliador julgou
```

**Consequência normativa 1 — declaração não é verdade.** `containment_declared` registra que a equipe *afirma* ter contido. Nunca altera o ground truth. Caso contrário, declarar cedo melhora a métrica mesmo com contenção errada.

**Consequência normativa 2 — toda métrica de resposta é pareada.** Uma para a declaração, outra para a verificação objetiva. O delta entre elas é o achado.

**Consequência normativa 3 — assimetria de informação é desenho.** Personas diferentes recebem projeções diferentes do ground truth, com defasagem e confiança distintas.

**Consequência normativa 4 — calibração importa mais que recall.** Avalia-se a relação entre confiança declarada e força real da evidência, não a contagem de acertos.

### 3.1 `facilitation` — quinto valor de `truth_layer`, não quinta verdade

As quatro camadas acima são verdades **sobre o incidente**. Os eventos da máquina de exercício — disparo de inject, rollback, seleção de branch, start/pause/resume/reset — não são nenhuma delas: não afirmam o que ocorreu no incidente, o que é descobrível, o que a equipe declarou nem o que o avaliador julgou. Afirmam o que o **facilitador** fez com a simulação.

`truth_layer` admite, por isso, **cinco valores**: os quatro acima mais `facilitation`. O modelo das quatro verdades permanece com quatro camadas — `facilitation` é ortogonal a ele, e é a razão de ser um valor à parte em vez de ser espremido em um dos quatro.

Mapear `inject_fired` para `ground_truth` misturaria máquina de exercício com fato do incidente, que é exatamente a confusão que este modelo existe para impedir. `01_ARCHITECTURE.md` §4 já reconhece "Facilitation Audit" como camada de estado própria, com reversibilidade **nunca**, igual a `participant_action`.

Eventos `facilitation` entram no AAR como linha de operação do exercício, nunca como evidência de desempenho da equipe.

## 4. Cadeia pedagógica

```
                    LEARNING OBJECTIVE
                            │
            ┌───────────────┴───────────────┐
            ↓                               ↓
     GROUND TRUTH (fatos)           EXPECTED BEHAVIOR
            │                               │
            ↓ projeções                     │
     OBSERVABLE EVIDENCE                    │
            │                               │
            ↓ distribuição                  │
         INJECT ──────────────→ PARTICIPANT │
                                     │      │
                                     ↓      │
                          DECLARATION / DECISION
                                     │      │
                        ┌────────────┴──────┴─────┐
                        ↓                         ↓
                  CONSEQUENCE                  SCORE
                   (branch)                (BARS + calibração)
                        │                         │
                        └────────────┬────────────┘
                                     ↓
                                    AAR
```

Inject sem objetivo associado é ruído deliberado ou erro de autoria. O linter recusa inject sem `objectives` ou sem `noise: true` explícito.

---

## 5. Princípios inegociáveis

**5.1 Fronteira core / domain.** `range-core/` não importa nada de `domains/`. Teste de CI por AST. Se o core precisar conhecer o domínio, corrija a abstração, não o teste.

**5.2 Efeitos declarativos.** Injects declaram estado desejado, nunca executam ação imperativa. É o que torna rollback e idempotência possíveis.

**5.3 Uma realidade, múltiplas projeções.** Toda evidência — log, telemetria CEF, trilha de auditoria, precursor events — é **projeção de fato canônico** declarado em `ground_truth.yaml`. Nunca gerada independentemente. Ver `08_EVIDENCE_SIMULATOR.md`.

**5.4 Um envelope de evento.** Injects, evidências, declarações, avaliações e rollbacks compartilham a mesma estrutura, com `truth_layer` obrigatório. Ver `09_EVENT_MODEL.md`.

**5.5 Rollback incrementa epoch, não apaga.** Apenas a projeção de simulação é reconstruída. Ação de participante, avaliação e auditoria de facilitação são append-only permanentes.

**5.6 Dois relógios, sempre.** São dois relógios e **três marcas**: o exercise-clock produz `exercise_time` e `exercise_timestamp`, o relógio de parede produz `wall_timestamp`. Todo evento carrega as três, mais `clock_multiplier`. Telemetria carrega também `ingest_time`.

> A enumeração trazia `exercise_time` e `wall_timestamp`, omitindo `exercise_timestamp`. **Não era contradição** — o texto não dizia "apenas", e esta seção conta *relógios*, que são dois, enquanto `01_ARCHITECTURE.md` §3 conta *marcas*, que são três. Mas o MASTER é a autoridade que os demais citam, e uma lista incompleta aqui é lida como fechada: `09_EVENT_MODEL.md` §1.1 cita esta seção como fonte de `clock_multiplier`, e a Fase 2 gastou uma escalação (E2) exatamente sobre qual marca o envelope tem. Corrigido no `spec-change` `quatro-marcas-e-quem-escreve-flag`; era a P2-5.
>
> **Os dois relógios continuam dois, e é isso que o título afirma.** `exercise_timestamp` é marca do exercise-clock — congela no PAUSAR junto de `exercise_time` e avança na cadência do multiplicador (`01_ARCHITECTURE.md` §3) —, e não um terceiro relógio. O que se separa no rollback são as duas marcas do mesmo relógio, não relógios distintos.

**5.7 Evidência antes de julgamento.** Critério sem evidência observável associada — `auto` ou `observed` — não entra no AAR como métrica. Impressão de facilitador entra rotulada como nota qualitativa.

**5.8 Rubrica no core, manifestação no pack.** A âncora BARS é universal e versionada (`incident_triage.v2`). Quais evidências demonstram aquela competência é decisão do cenário.

**5.9 Trilha de auditoria é mecanismo.** Append-only exige role `INSERT`-only, `REVOKE UPDATE/DELETE`, trigger e hash encadeado. Ver `02_DOMAIN_ACADEMUS.md` §4.

**5.10 Gabarito é de máquina.** `ground_truth.yaml` é a fonte autoritativa, legível pelo motor. `GM_NOTES.md` é narrativa para o facilitador e **não pode conter fato ausente do ground truth**.

---

## 6. Glossário

| Termo | Definição |
|---|---|
| **Core** | `range-core/` — motor agnóstico de domínio |
| **Adapter** | `domains/<nome>/` — domínio de negócio acoplável |
| **Pack** | Pacote de cenário em `scenarios/<domain>/<pack_id>/` |
| **Fato** | Unidade de ground truth, com `fact_id`, projetada em evidências |
| **Projeção de evidência** | Renderização de um fato em formato de log ou telemetria |
| **Flag** | Variável de estado de simulação, namespaced, declarada em contrato |
| **Epoch** | Linha temporal de simulação; rollback incrementa |
| **Declaração** | Afirmação do participante; nunca altera ground truth |
| **Predicado de verificação** | Condição objetiva que define contenção, restauração ou integridade |
| **Defensibilidade** | Valor 0–1 no gabarito indicando quão sustentável é acusar um caso |
| **Vertical slice** | Fase 4 — caminho ponta a ponta mínimo funcionando |

---

## 7. Mapa de documentos

| Doc | Escopo | Fases |
|---|---|---|
| `00_MASTER_SPEC.md` | Autoridade, quatro verdades, princípios | Todas |
| `01_ARCHITECTURE.md` | Core/adapter, estado, relógios, flags, serviços, verificadores de CI | 1, 2, 4 |
| `02_DOMAIN_ACADEMUS.md` | Entidades, auditoria, dataset, Linha B, continuidade | 3, 5, 8 |
| `03_EXERCISE_DESIGN.md` | Objetivos, BARS, métricas pareadas, calibração, finalidade comercial, AAR | 6, 7, 10 |
| `04_SCENARIO_SCHEMA.md` | Schema v2, ground_truth, branch_policy, CLI | 2, 7 |
| `05_SECURITY_REQUIREMENTS.md` | Restrições inegociáveis, deploy | Todas |
| `06_ACCEPTANCE_TESTS.md` | Critérios de aceitação | Todas |
| `07_IMPLEMENTATION_PHASES.md` | Fases, DoD, demo script, non-goals | Todas |
| `08_EVIDENCE_SIMULATOR.md` | Projeções de fato para Blue Team | 9 |
| `09_EVENT_MODEL.md` | Envelope, catálogo, epochs, instrumentação | 2, 6 |

---

## 8. Stack e convenções

Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL 16 · Redis · React 18 · Vite · TailwindCSS · Recharts · WebSocket · Prometheus · Grafana · Docker Compose · Linux VPS. Todas as versões pinadas.

**Idioma** — inglês para identificadores, tabelas, endpoints, logs, nomes de flag e de evento; português do Brasil para interface, dados sintéticos, cenários, rubricas e documentação.

**Determinismo** — `RANDOM_SEED` fixo em `.env`. Necessário, mas não suficiente: a consistência entre evidências vem do modelo de projeção de fatos (§5.3), não do seed.
