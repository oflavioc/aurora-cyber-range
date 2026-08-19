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

#### A coluna `Métrica` é descritiva, e não é o valor de `metric_binding`

A coluna acima diz **o que evidencia** cada objetivo, em linguagem de leitura humana: por isso admite par (`TTCD/TTCV`), expressão (`TTIV − TTRV`), mecanismo de avaliação (`calibração`) e ausência (`—`).

**`metric_binding` é escalar**, como §1.1 o exibe, e aponta **a métrica de disparo** — aquela cujo instante o motor marca a partir dos eventos do objetivo. Nunca o par, nunca a expressão.

- **Pares** não precisam ser declarados: §3 já define quais são, e o AAR os monta a partir da métrica declarada. OBJ-05 vincula `TTCD`; TTCV vem do predicado de verificação do pack, não do objetivo.
- **Deltas são computação do AAR**, não binding. **OBJ-10 vincula `TTIV`**, e a diferença para TTRV é a leitura que §9 item 3 manda pôr em destaque. Registrado aqui em vez de deixado ao leitor: sem isso, quem lê esta tabela conclui que o campo precisa carregar a expressão, e essa conclusão exigiria mudar a forma de um campo dentro da mesma `schema_version` — o que `04_SCENARIO_SCHEMA.md` §4 proíbe.
- **`calibração` não é métrica** e não entra em `metric_binding`. É o mecanismo de avaliação de §5, e OBJ-04 simplesmente omite o campo, que é opcional.

O conjunto de valores admissíveis é o das siglas de §3 — `TTA`, `TTT`, `TTCM`, `TTCD`, `TTCV`, `TTRD`, `TTRV`, `TTID`, `TTIV` —, todas em inglês, como `00_MASTER_SPEC.md` §8 exige de identificador.

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

As tabelas desta seção são o **resultado de aplicar o critério de `00_MASTER_SPEC.md` §3.2** às nove siglas de v1. Não são a definição da partição e não podem ser lidas como lista de isenções: o critério classifica, a tabela registra o que ele classificou, e §3.0 mostra a conta. Sigla nova entra pela derivação, não por acréscimo de linha.

| Par | Declaração (participante) | Verificação (ground truth) |
|---|---|---|
| Contenção | **TTCD** — `containment_declared` | **TTCV** — predicado de contenção satisfeito |
| Restauração | **TTRD** — `service_restoration_declared` | **TTRV** — predicado de restauração satisfeito |
| Integridade | **TTID** — `integrity_validation_declared` | **TTIV** — ver §3.3 |

Métricas **simples** — classificadas em §3.0, com a cláusula que decidiu cada uma:

| Sigla | Start | Stop | Cláusula que a mantém simples |
|---|---|---|---|
| **TTA** | primeiro inject com impacto observável | `incident_declared` | (1) e (3) — atributo do mundo, e o instante já é o start |
| **TTT** | `incident_declared` | `classification_declared` com severidade e escopo | (1) — atributo do incidente; acurácia é calibração (§3.0) |
| **TTCM** | inject com `requires_response` | submissão correspondente | (2) — a submissão constitui a resposta |

**Impacto observável, definido.** O *start* de `TTA` é *"o primeiro inject com impacto observável"*, e a expressão precisa de predicado: sem ele, qual inject abre a medição vira decisão de quem implementa, e `TTA` deixa de ser comparável entre exercícios. `00_MASTER_SPEC.md` §3.2 exige que a seleção de start seja cálculo do consumidor sobre o payload de `inject_fired`, e não recorte do montador — sem definição, o consumidor calcularia com um critério que nenhum documento fixa.

**Um inject tem impacto observável quando declara ao menos um de:**

1. **`effects`** — mutação de flag. Toda flag tem superfície **por construção do contrato**: `contracts/state_flags.schema.yaml` exige `effect_ui`, `wallboard_group` e `consumers` em toda declaração, e é o que torna esta perna estrutural em vez de costume — não existe flag que se mova sem lugar onde a mudança apareça.
2. **`materializes_facts`** com fato que tenha **`projections`** — o fato passa a existir *e* a aparecer em pelo menos uma fonte de evidência.
3. **`evidence_release`** — uma fonte é liberada para consulta.

**É derivado, não declarado.** O predicado se avalia sobre o que o pack já escreve, na carga. Um campo novo no inject — `observable_impact: true` — seria segunda fonte para o mesmo fato, divergiria do conteúdo em silêncio, e poria em mãos de autoria a decisão de quando a métrica começa a correr.

**O que fica de fora, pelo modelo das quatro verdades.** Inject cuja única declaração é **`reveals`** não tem impacto observável. `reveals` alimenta **crença do participante** — a terceira camada de `00_MASTER_SPEC.md` §3 —, e não o mundo nem a evidência descobrível. `TTA` mede a distância entre a primeira camada e a terceira: o mundo muda, e a equipe leva um tempo até declarar que mudou. Sala **informada** não é sala que **detectou**, e contar o inject narrativo como start mediria o tempo de reagir a um aviso — outra coisa, com lugar próprio em `TTCM`, para o que exige resposta.

Pela mesma razão, **fato sem `projections` não conta**: `08_EVIDENCE_SIMULATOR.md` §2 o declara invisível ao time azul de propósito, para ensinar limite de detecção. Fato que ninguém pode descobrir não move a segunda camada, e abrir `TTA` nele mediria latência contra um relógio que a equipe não tinha como ver começar.

### 3.0 Derivação das nove siglas

A conjunção de `00_MASTER_SPEC.md` §3.2, aplicada sigla a sigla. Esta tabela é o que `06_ACCEPTANCE_TESTS.md` T10 confere contra o critério; divergência reprova esta tabela, nunca o critério.

| Sigla | Instante que marca | (1) conclusão de ação de resposta? | (2) instante decidido fora da declaração? | (3) não coincide com extremo próprio? | Resultado |
|---|---|---|---|---|---|
| **TTCD** | `containment_declared` | **sim** — acesso revogado, escopo desabilitado são ações da equipe | **sim** — `verification_predicates.containment` sobre `state_effect` | sim | **pareada** → `TTCV` |
| **TTRD** | `service_restoration_declared` | **sim** — restabelecer serviço é ação da equipe | **sim** — `verification_predicates.service_restoration` | sim | **pareada** → `TTRV` |
| **TTID** | `integrity_validation_declared` | **sim** — validar integridade é ação da equipe | **sim** — limiar de calibração contra defensibilidade (§3.3) | sim | **pareada** → `TTIV` |
| **TTA** | `incident_declared` | **não** — *"há incidente"* é atributo do mundo, não conclusão de ação | (não se alcança) | **não** — o instante em que passou a valer **é o start** da própria métrica | **simples** |
| **TTT** | `classification_declared` | **não** — severidade e escopo são atributos do incidente | (não se alcança) | (não se alcança) | **simples** — ver abaixo |
| **TTCM** | submissão correspondente ao inject `requires_response` | **sim** — responder é ação da equipe | **não** — a submissão **constitui** a resposta; nada fora dela decide que houve resposta | (não se alcança) | **simples** |
| **TTCV** | predicado de contenção satisfeito | — não se classifica pelo critério | — | — | metade de verificação de `TTCD` |
| **TTRV** | predicado de restauração satisfeito | — não se classifica pelo critério | — | — | metade de verificação de `TTRD` |
| **TTIV** | limiar de calibração atingido | — não se classifica pelo critério | — | — | metade de verificação de `TTID`; verificador não é o mundo (§3.3) |

**`TTA` falha por duas razões independentes**, e as duas estão na tabela porque a segunda sobrevive a quem leia `incident_declared` como conclusão de um reconhecimento: mesmo assim o instante em que *"há incidente"* passou a valer é o inject que o materializa, que é o start. `TTA` **já é** o delta entre mundo e declaração.

#### Por que `TTT` não tem par, e não é omissão

Parear `TTT` exigiria predicado de verificação para a classificação, e ele seria **parametrizado pelo conteúdo da declaração**: o instante a marcar seria aquele em que o incidente atingiu *a severidade declarada*. Declarada errada para mais, esse instante **não existe** — o mundo nunca chega lá —, e a métrica fica indefinida: some do AAR sem dizer que sumiu. Métrica que não dispara é pior que métrica ausente, porque a ausência ao menos se vê.

**É esse o argumento, e ele basta.** Verificador que depende do que a declaração diz não verifica a declaração.

A acurácia de um atributo declarado é, por categoria, matéria de **calibração** — relação entre confiança declarada e força da evidência, §5 — e não distância entre dois instantes. Isso classifica; **não afirma que a §5, como está, cobre `classification_declared`**: ela escora o Brier sobre os casos de Linha B, e a classificação não é um deles. Estender a §5 é decisão própria, registrada como **P6-1**, e esta seção não depende dela.

`TTT` mede o tempo até haver classificação, e só.

### 3.1 Predicados de verificação

TTCV e TTRV só são computáveis se o `ground_truth.yaml` declarar **o que é** contenção e restauração neste incidente.

**A folha `event` de um predicado só pode referenciar `event_type` com `effect_class: state_effect`** (`09_EVENT_MODEL.md` §4.0).

Sem essa restrição, `containment: {all: [{event: containment_declared}]}` é um pack perfeitamente válido — e nele TTCD e TTCV passam a medir o mesmo instante. O delta que a §3.2 chama de "o achado" deixa de existir, e **nada falha**: a métrica continua sendo calculada, só que mede a si mesma. A consequência normativa 2 de `00_MASTER_SPEC.md` §3 seria anulada por autoria de cenário, não por defeito de código.

A distinção não é de camada. `vpn_access_revoked` e `identity_scope_disabled` são `participant_action`, como `containment_declared`, e são legítimos aqui: são **ações com efeito no mundo simulado**, não afirmações sobre ele.

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

### 3.3 TTIV é o par cujo verificador não é o mundo

Contenção e restauração são **estados do mundo** — o ground truth sabe se valem. Integridade validada não é: é propriedade da **qualidade da avaliação da equipe**.

Isso **não a tira do par**, e a redação anterior sugeria o contrário ao chamá-la de assimétrica. Pelo critério de `00_MASTER_SPEC.md` §3.2, o par exige conclusão de ação da equipe com instante decidido fora da declaração — e as duas coisas valem: validar integridade é ação da equipe, e o instante é aquele em que o conjunto de `assessment_submitted` atinge `calibration.threshold`, medido contra a defensibilidade do gabarito (§5). O que muda é **quem decide o instante**, não se há par.

`TTIV` = esse instante. Forçar o verificador a ser predicado de estado do mundo produziria um número inexplicável no debriefing — e essa é a assimetria real: de verificador, não de estrutura.

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

**`facilitador`** — timeline integral, linhas, ground truth, GM_NOTES, consequências, PAUSAR / CONTINUAR / ROLLBACK / RESET, AAR.

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
