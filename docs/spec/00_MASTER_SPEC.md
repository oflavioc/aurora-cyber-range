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

**Consequência normativa 2 — métrica pareada é a que mede conclusão de ação datável por fora.** Uma métrica marca o instante de uma declaração; quando essa declaração afirma conclusão de ação de resposta da equipe, e o instante da conclusão é decidido fora da declaração, esse instante é a outra metade do par, e o delta entre as duas é o achado. §3.2 fixa o critério que decide quais são, o insumo que cada uma recebe, e o que isso proíbe.

**Consequência normativa 3 — assimetria de informação é desenho.** Personas diferentes recebem projeções diferentes do ground truth, com defasagem e confiança distintas.

**Consequência normativa 4 — calibração importa mais que recall.** Avalia-se a relação entre confiança declarada e força real da evidência, não a contagem de acertos.

### 3.1 `facilitation` — quinto valor de `truth_layer`, não quinta verdade

As quatro camadas acima são verdades **sobre o incidente**. Os eventos da máquina de exercício — disparo de inject, rollback, seleção de branch, start/pause/resume/reset — não são nenhuma delas: não afirmam o que ocorreu no incidente, o que é descobrível, o que a equipe declarou nem o que o avaliador julgou. Afirmam o que o **facilitador** fez com a simulação.

`truth_layer` admite, por isso, **cinco valores**: os quatro acima mais `facilitation`. O modelo das quatro verdades permanece com quatro camadas — `facilitation` é ortogonal a ele, e é a razão de ser um valor à parte em vez de ser espremido em um dos quatro.

Mapear `inject_fired` para `ground_truth` misturaria máquina de exercício com fato do incidente, que é exatamente a confusão que este modelo existe para impedir. `01_ARCHITECTURE.md` §4 já reconhece "Facilitation Audit" como camada de estado própria, com reversibilidade **nunca**, igual a `participant_action`.

Eventos `facilitation` entram no AAR como linha de operação do exercício, nunca como evidência de desempenho da equipe.

### 3.2 Partição das métricas — o critério, o insumo, e o que fica fora do alcance

A redação anterior da consequência normativa 2 dizia *"toda métrica de resposta é pareada"*, e **`métrica de resposta` não estava definida em lugar nenhum**: o termo ocorria duas vezes na spec inteira, e as duas eram a própria norma. Norma cuja classe de aplicação ninguém sabe enumerar não decide caso nenhum — decide quem implementa, na hora de implementar.

#### O critério

Toda métrica marca um instante. Uma métrica é **pareada** quando as três condições valem ao mesmo tempo:

1. a declaração que ela marca afirma **conclusão de ação de resposta da equipe** — não atributo do incidente;
2. o instante em que essa conclusão passou a valer é **decidido fora da declaração**;
3. esse instante **não coincide** com extremo que a própria métrica já marca.

Falhando qualquer uma, a métrica é **simples**. A conjunção é o critério. A tabela de `03_EXERCISE_DESIGN.md` §3.0 é o **resultado** de aplicá-la às nove siglas de v1, nunca a sua fonte: sigla nova se classifica pela conjunção, não por acréscimo de linha. Enumerar de novo aqui reproduziria, um nível acima, o defeito que esta seção corrige.

#### O que cada cláusula decide, e o que ela não decide

A **(1)** separa *"contivemos"* de *"a severidade é alta"*. Atributo do incidente tem acurácia, e acurácia é calibração — confiança contra defensibilidade, `03_EXERCISE_DESIGN.md` §5 —, não distância entre dois instantes. A **(2)** separa a conclusão que alguém de fora pode datar daquela que o próprio ato constitui. A **(3)** impede par degenerado, em que a segunda metade duplicaria um extremo que a métrica já marca.

**Em v1, (1) decide `TTT` e `TTA`, (2) decide `TTCM`, e (3) não decide sozinha nenhum caso** — acompanha (1) em `TTA`. Está registrada como guarda de sigla futura, e não como cláusula que hoje segura alguma coisa. Dizer o contrário daria à conjunção uma solidez que ela ainda não tem.

#### Quem decide o instante não precisa ser o mundo

O par exige verificador independente da declaração; não exige que ele seja predicado de estado do mundo. `TTID/TTIV` é instância disso e não exceção: integridade validada não é estado do mundo, e ainda assim a conclusão tem instante decidido fora da declaração — aquele em que o conjunto de `assessment_submitted` cruza o limiar de calibração medido contra a defensibilidade do gabarito. Par mantido, verificador diferente (`03_EXERCISE_DESIGN.md` §3.3).

#### O insumo — cada computador recebe apenas o seu lado

**O computador de cada métrica recebe apenas os eventos do lado dela, mais a escrituração de epoch e os escalares do seu insumo tipado. O único escopo que tem as duas metades de um par é o AAR.**

Isso fecha dois defeitos com uma regra só. Métrica simples computada a partir do veredito de verificação é um deles; `TTCD` computado a partir de `TTCV` é o mesmo defeito pelo outro lado, e nenhuma regra anterior o alcançava — `09_EVENT_MODEL.md` §4.0 guardava apenas o sentido oposto, o predicado referenciando declaração.

**Os lados são papéis declarados por `event_type` no catálogo** (`contracts/events.schema.yaml`, registro `metric_side`), e não são derivados de `effect_class`. A derivação foi tentada e reprova nos dois sentidos: `verification_predicate_satisfied` é `machine`, como `inject_fired`, e só um dos dois é veredito; `assessment_submitted` é `declaration` e é o insumo do verificador de `TTIV`. Nenhuma das duas classes é chave de partição.

| Lado | Semântica do papel |
|---|---|
| `declaration` | o que a equipe afirma, e os disparos que fornecem os *starts* das métricas simples |
| `verification` | o que decide, por fora da declaração, o instante em que a conclusão passou a valer: o veredito de predicado, os eventos que uma folha de predicado pode referenciar, e o insumo do limiar de calibração |
| `epoch` | escrituração da máquina de exercício, entregue **aos dois lados** |
| `none` | nenhum computador de métrica lê |

A tabela descreve a **semântica**. A pertinência de cada `event_type` é o atributo do catálogo, e é sobre o atributo que a cobertura total e a **disjunção** são checadas — nunca sobre esta prosa, e nunca sobre o conteúdo dos predicados de um pack.

A referenciabilidade por folha de predicado é **estática do catálogo**: vale por atributo declarado, para todo pack, e não depende de quais predicados um pack em particular escreveu. Fosse dinâmica, o lado de um `event_type` mudaria com o cenário carregado, e a disjunção não seria checável fora de execução.

#### Por que isso não é filtro no caminho compartilhado

A superfície de leitura do event store **permanece total e sem parâmetro**: `01_ARCHITECTURE.md` §4.1 — *"a leitura do store é total; nenhum caminho de leitura compartilhado filtra por epoch, por abandono ou por ponto de corte"* —, executada por `scripts/check_store_read_surface.py`. Nada aqui a toca.

O motivo daquela regra é o desta: §4.1 registra que **quatro das cinco projeções leem a epoch abandonada legitimamente**, e que um filtro compartilhado as faria herdar uma perda que nenhuma escolheu, sem nada falhar.

O recorte desta seção é de outra espécie e em outro lugar: acontece **depois da leitura total**, na **montagem do insumo, no chamador**, com **um único ponto de montagem por lado**, e estreita **um argumento de um consumidor**. O fluxo total continua existindo, continua sendo o que o AAR dobra e o que a reconstrução refaz.

**Onde os computadores ficam, no diagrama de §4.1:** os dois lados vivem dentro da projeção `metrics`; `calibration` é projeção irmã e é ela que produz o instante verificador de `TTIV`; `aar_timeline` é o escopo que recebe as duas metades de cada par e computa os deltas. `objective_evidence` e `simulation_state` não são consumidores de métrica.

#### Epoch é computação do consumidor, nunca recorte na montagem

O desconto do intervalo de `technical_failure` — pela **união** dos intervalos, nunca pela soma — e a exclusão de epoch com `reason: rehearsal` **não são exclusões na montagem**. Os `event_type` de lado `epoch` chegam a **ambos** os computadores, com tipo próprio, e o desconto é **código do consumidor**, visível e testado.

A razão é de verificabilidade. Recortada na montagem, a regra *"nenhum evento de `rehearsal` entra em cálculo"* passa a ser propriedade do montador e não da métrica: o teste que a julga exercitaria o montador, o número certo apareceria por ausência de insumo em vez de por cálculo, e evento perdido por defeito ficaria indistinguível de evento corretamente descontado.

**A seleção de start segue a mesma regra.** Qual inject é *"o primeiro com impacto observável"* e qual carrega `requires_response` são atributos que viajam no **payload** de `inject_fired`; escolher entre eles é cálculo do consumidor. Montador que já entregasse "o inject certo" moveria a regra para fora do que o teste alcança, exatamente como no caso da epoch.

#### O que a assinatura verifica, e a costura que é fraca

`Sequence[Event]` **não nega nada**: o fluxo inteiro o satisfaz, e checagem que aceite essa anotação não afirma coisa alguma. A verificação exige:

1. o insumo de cada lado tem **tipo próprio**, recusado se resolver para `Sequence[Event]`, `Iterable[Event]`, `list[Event]` ou alias deles;
2. **o banido é o fluxo total, o event store e o pack como objeto.** O insumo tipado **carrega os escalares de que o lado precisa** — o limiar de calibração e a defensibilidade por caso chegam assim ao verificador de `TTIV`, e não por consulta ao pack. Proíbe-se ter *por onde buscar mais do que lhe foi dado*, não ter o que lhe é necessário;
3. cada tipo de insumo tem **um único ponto de montagem**, e o construtor do tipo aparece só ali;
4. os lados vêm do `metric_side` do catálogo, com cobertura total e disjunção checadas sobre o atributo.

**A (3) é a costura fraca, e está dita por ser fraca.** Tipo estreito não é barreira de execução: construí-lo a partir do fluxo total, fora do ponto de montagem, compila. O que impede é checagem de superfície sobre onde o construtor aparece — whitelist, não blocklist. Isso é mais fraco que *"não tem flag ao alcance"* da D4, e é mais fraco porque o veredito chega como **dado**, não como import.

Sem tudo isso a partição volta a ser decisão de implementação, e o defeito é invisível pelo motivo que `03_EXERCISE_DESIGN.md` §3.1 registra: a métrica continua sendo calculada. Nada falha.

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
