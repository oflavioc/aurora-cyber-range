# 04 — SCHEMA DE CENÁRIO (v2)

---

## 1. Estrutura do pacote

```
scenarios/academus/ransomware-universidade/
  manifest.yaml
  ground_truth.yaml        ← MÁQUINA: fatos, predicados, defensibilidade, branches
  GM_NOTES.md              ← HUMANO: narrativa para o facilitador
  objectives.yaml
  information_distribution.yaml
  injects.yaml
  branches.yaml
  evidence/                ← gerado por projeção
  media/
```

**`ground_truth.yaml` é autoritativo.** `GM_NOTES.md` explica ao facilitador o que está no ground truth e **não pode conter fato ausente dele** — o linter compara e recusa divergência. Idealmente parte do GM_NOTES é gerada a partir do ground truth, para eliminar drift.

## 2. Manifesto

```yaml
schema_version: 2
pack_id: ransomware-universidade
title: "Ransomware na véspera da matrícula"
domain: academus
min_engine_version: "1.0"
duration_minutes: 240
audience: executivo
lines: [A, B, ruido]
personas: [reitoria, pro_reitoria, ti, dpo, juridico, pesquisa, comunicacao]
required_flags: [academus.enrollment_offline, academus.lms_session_drop_rate]
required_rubrics: [incident_triage.v2, crisis_communication.v2, integrity_assurance.v1]
evidence_sources: [email, vpn, identity_audit, database_audit]
branch_policy:
  max_branch_points_per_line: 1
  max_paths_per_branch: 2
calibration:
  threshold: 0.15          # Brier máximo para considerar integridade validada (TTIV)
```

`required_rubrics` inclui a **versão**. Rubrica ausente ou em versão diferente impede a carga.

> **`branch_policy` teve um terceiro campo, `reconvergence_required: true`, e ele saiu neste `spec-change`.** Era booleano exigido sem efeito possível: a §6.2 recusa branch sem `reconverge_at` **incondicionalmente** — e o DoD 5 da Fase 7 repete a forma incondicional —, então `false` era aceito e mentia. A tensão foi medida na abertura da peça 4 de branching, quando "aplicar a `branch_policy`" exigiria dar semântica a um campo que não pode ter nenhuma. Decisão do proprietário (2026-08-25): **reconvergência é sempre obrigatória** — branch sem reconvergência torna não-limitado um exercício de `duration_minutes` fixa, contra o princípio de cenário ensaiável e determinístico da §6.1. A política fica com os dois contadores, que são o que a §6.2 sempre definiu como "aplicada": excesso de pontos ou de caminhos.

## 3. Ground truth

```yaml
facts:
  - fact_id: GT-A-014
    fact_class: initial_access
    actor: svc_academus
    action: vpn_login
    source_ip: 198.51.100.42
    exercise_time: "T-17d 02:14"
    projections: [vpn, identity_audit, cef]

verification_predicates:
  containment:
    all:
      - event: vpn_access_revoked
      - event: identity_scope_disabled
        payload: { principal: svc_academus }
      - absence_of: { fact_class: exfiltration, since: self }
  service_restoration:
    all:
      - flag_false: academus.enrollment_offline
      - flag_false: academus.lms_degraded

line_b_cases:
  - case_id: GC-029
    defensibility: 1.0
    set: indevido_comprovado
    supporting_evidence: [DBA-28391, DBA-28402]
  - case_id: GC-041
    defensibility: 0.5
    set: ambiguo
  - case_id: GC-077
    defensibility: 0.0
    set: legitimo_aparencia_suspeita
```

Sem `verification_predicates`, o pack não carrega — TTCV e TTRV seriam incomputáveis.

`since: self` é definido em `03_EXERCISE_DESIGN.md` §3.1.

## 4. Política de versionamento

- Engine declara `ENGINE_VERSION` e `SUPPORTED_SCHEMA_VERSIONS = [N, N-1]`
- Pack em N-1 carrega com migração em memória e aviso no boot
- Pack anterior a N-1 é recusado com instrução de migração
- Migrações em `range-core/engine/migrations/v<n>_to_v<n+1>.py`, cada uma com teste
- **Nunca alterar semântica de campo dentro da mesma `schema_version`**

### 4.1 Forma declarada uma vez, e constante derivada de contrato entra no núcleo como dado

**Uma forma que dois contratos exigem é definida em `$defs` de um só, e referenciada por `$ref` a partir dos outros.** O contrato-fonte é aquele que **declara a entidade**, não o que a menciona: `fact_id` e `case_id` moram em `ground_truth.schema.yaml` porque é ele que declara `facts` e `line_b_cases`. Duas cópias da mesma forma são duas coisas que divergem, e a divergência entre contratos não falha alto — ela faz a junção deixar de casar, e o efeito aparece como dado ausente em vez de erro.

Quando a composição impedir o `$ref` — um padrão que embute outro, como `fact_check_against` — a cópia é **declarada no ponto**, com o que a mantém em acordo dito por escrito. Cópia declarada é dívida nomeada; cópia silenciosa é a mesma dívida sem ninguém para cobrá-la.

**A constante derivada de contrato entra no núcleo como DADO, por construtor, lida uma vez na raiz de composição.** Nenhum módulo de `range-core/` lê `contracts/` em caminho quente: quem lê é a fábrica que sobe o processo, e o valor viaja como argumento até quem o consome, que o valida na construção.

A forma já está em uso e é o precedente a seguir — a taxonomia de motivo de rollback:

| Passo | Onde |
|---|---|
| o contrato é lido, uma vez, no boot | `range-core/engine/loader/contract_source.py:151` (`rollback_reasons`), chamado de `range-core/api/processo.py:144`, dentro da fábrica que `uvicorn --factory` invoca |
| o valor entra no objeto de núcleo como dado | `range-core/engine/inject_engine.py:211` — `rollback_reasons: Collection[str]` |
| o receptor valida na construção e congela | `inject_engine.py:214-225` — taxonomia sem `technical_failure` derruba o **boot**, não o exercício |

O que isso compra é a ausência de uma segunda origem: a constante existe uma vez, no contrato, e nenhum módulo a repete. O que custa é um parâmetro obrigatório a mais em quem a consome — e é por isso que ela chega **validada na construção**, e não conferida a cada uso.

## 5. Inject

```yaml
- id: A07
  linha: A                          # visível apenas ao facilitador
  t_relative: "00:47"
  titulo: "Nota de resgate exibida no portal"
  titulo_operacional: "Inject 07"   # único rótulo visível ao operador
  descricao_facilitador: "..."
  texto_para_plateia: "..."
  objectives: [OBJ-01, OBJ-08]      # obrigatório, salvo noise: true
  effects:
    academus.lms_session_drop_rate: 0.4
    academus.enrollment_offline: true
  materializes_facts: [GT-A-031]    # fatos que passam a existir neste ponto
  evidence_release:
    - source: vpn
      window: "T-9d → T-8d"
  reveals:
    - persona: reitoria
      content: "possível vazamento de dados de alunos"
      confidence: low
  decision_point:
    id: DP-A03
    question: "Suspender a matrícula online?"
    objectives: [OBJ-06]
    timer_minutes: 15
    options:
      - id: suspend
        label: "Suspender imediatamente"
        effects: { academus.enrollment_offline: true }
        tradeoff: "Contém exposição; interrompe período letivo, gera fila física"
      - id: monitor
        label: "Manter no ar sob monitoramento"
        effects: { academus.lms_session_drop_rate: 0.6 }
        tradeoff: "Preserva calendário; amplia janela de exposição"
      - id: no_federated_revocation
        label: "Não temos como revogar a sessão federada no tempo do exercício"
        effects: { academus.lms_session_drop_rate: 0.6 }
        tradeoff: "Exposição persiste; a equipe registra a lacuna em vez de simular capacidade"
        capability_gap:                                  # opcional
          control_function: federated_session_revocation # função, nunca produto
          objectives_affected: [OBJ-05]
          metric_impacted: TTCV
```

### 5.1 `capability_gap`

Campo **opcional** na opção. Quando presente, marca que a opção declara **ausência de capacidade**, não escolha de curso de ação. Ver `03_EXERCISE_DESIGN.md` §8.3.

| Campo | Conteúdo |
|---|---|
| `control_function` | Função de controle ausente, em inglês e snake_case. **Nunca nome de produto ou de fornecedor** (`05_SECURITY_REQUIREMENTS.md` §5.1) |
| `objectives_affected` | Objetivos de aprendizagem impactados pela ausência |
| `metric_impacted` | Sigla da métrica afetada, quando houver |

`effects` e `tradeoff` continuam obrigatórios: a lacuna tem consequência no mundo simulado e não é saída sem custo. Escolher esta opção emite `decision_made`, como qualquer outra, **e também** `capability_gap_declared` (`09_EVENT_MODEL.md` §4.1) — o primeiro preserva a uniformidade da trilha de decisões, o segundo carrega os campos acima para a projeção do AAR.

`control_function` é **vocabulário aberto** nesta versão do schema. Fechá-lo agora seria inventar taxonomia antes de haver dados: a consolidação em vocabulário controlado fica para quando existirem packs suficientes para revelar quais funções de fato se repetem.

## 6. Branching

```yaml
branches:
  - id: BR-A-CONTAINMENT
    line: A
    at_inject: A08
    evaluate:
      - id: contained_early
        when:
          all:
            - event: vpn_access_revoked
            - before: "01:30"
        next: A09B
        note_to_facilitator: "Alcance reduzido; dados já exfiltrados permanecem."
      - id: not_contained
        default: true
        next: A09C
    reconverge_at: A12
```

### 6.1 Condições só podem depender do objetivamente observável

**Permitido:** `event` (do catálogo), `decision` + `option`, `flag`, `before` / `after`, combinados por `all` / `any` / `not`.

**Proibido:** qualquer condição que dependa de juízo — `facilitator_thinks_response_was_good` e equivalentes. O cenário precisa permanecer ensaiável e determinístico.

### 6.2 Validação obrigatória do linter

- `branch_policy` do manifesto é aplicada: excesso de pontos de ramificação ou de caminhos é recusado
- Branch sem `reconverge_at` é recusado
- **Todo `event` referenciado em `when` deve existir no catálogo de eventos.** Um `event_type` com erro de digitação nunca dispara: a branch silenciosamente não ramifica e ninguém percebe até o exercício ao vivo. É a falha mais cara possível
- Todo `option` referenciado deve existir no `decision_point` indicado
- **Todo objetivo em `objectives_affected` de um `capability_gap` deve existir em `objectives.yaml`.** Mesma classe do `event_type` inexistente e pelo mesmo motivo: o erro de digitação não falha em lugar nenhum — a lacuna simplesmente não é atribuída a objetivo algum e some do AAR, e ninguém percebe até o exercício ao vivo

## 7. Eventos de mídia

```yaml
media_event:
  type: press_call        # press_call | investigative | viral_post | protest | union
  outlet: "Jornal Aurora"
  reporter: "Carla Mendes"
  deadline_minutes: 20
  requires_response: true
  objectives: [OBJ-08]
  fact_check_against: facts.GT-A-020.records_affected
```

`fact_check_against` permite ao AAR comparar automaticamente o número comunicado com o ground truth.

## 8. CLI

```
range-cli scenario validate <path>   # schema, flags, personas, rubricas (com versão),
                                     # objetivos, verification_predicates
range-cli scenario migrate <path>
range-cli scenario lint <path>       # inject sem objetivo e sem noise, DP sem consequência,
                                     # t_relative fora de ordem, mídia sem deadline,
                                     # branch_policy, event_type inexistente,
                                     # GM_NOTES com fato ausente do ground truth
range-cli scenario dryrun <path>     # percorre todos os caminhos de branch sem UI
range-cli scenario materialize <domain> <pack_id>
                                     # escreve o par ground_truth.yaml + GM_NOTES.md
                                     # do pack; recusa destino versionado
range-cli evidence build <path>      # gera projeções a partir do ground truth
range-cli evidence verify <path>     # consistência fato → projeções
```

`validate`, `lint` e `evidence verify` rodam no CI. `dryrun` é pré-requisito de ensaio.

### 8.1 `materialize` escreve, e as três propriedades que decorrem disso

**`materialize` é o único subcomando que produz o gabarito.** `evidence build` **consome** o ground truth para dele derivar projeções; `materialize` é quem escreve o ground truth. Dois `build` para operações opostas seriam confusão de espécie, e o nome os separa.

Sem ele a superfície tem um buraco que só aparece na sala: quem for facilitar tem o gerador e não tem o arquivo.

**(a) Ele está do lado de ESCRITA da fronteira, e a fronteira já existe.** As allowlists que restringem quem opera o repositório liberam `validate`, `lint`, `dryrun` e `evidence verify` — os que só leem — e param aí. `materialize` e `evidence build` ficam fora delas pela mesma razão, e isso é propriedade a preservar, não omissão a corrigir: um subcomando que escreve não entra numa lista de leitura porque o nome dele começa igual.

**(b) O destino é `scenarios/<domain>/<pack_id>/`**, a forma que `00_MASTER_SPEC.md` §6 fixa no glossário. Os dois segmentos têm forma declarada em `contracts/scenario.schema.v2.yaml`: `domain` casa `^[a-z][a-z0-9_]*$` e `pack_id` casa `^[a-z][a-z0-9-]*$`. Caminho que não corresponda a essas formas é recusado antes de qualquer escrita.

**(c) `materialize` RECUSA destino versionado**, e a recusa é dele e não do `.gitignore`. `05_SECURITY_REQUIREMENTS.md` §6 põe `ground_truth.yaml` e `GM_NOTES.md` fora do repositório servido, e este repositório é público: quem os lê antes do exercício tem o gabarito. `.gitignore` é convenção, e `git add -f` a atravessa — a garantia tem de ser propriedade do **caminho que escreve**, porque ele é o único ponto por onde o artefato nasce. A decisão é do `git`, perguntando se o alvo é rastreado, e não de uma lista de caminhos proibidos: lista não prevê o caminho que ninguém previu.

### 8.2 `domain` e `pack_id` são parâmetros explícitos

**`materialize` recebe os dois como argumento, e não os deriva de nada.** Não de adapter em uso, não de variável de ambiente, não de diretório corrente, não de configuração implícita.

Derivar de contexto acoplaria o produtor ao domínio por um canal que nenhum verificador enxerga — e `01_ARCHITECTURE.md` §2 mantém `range-core/` sem conhecimento de `domains/` justamente para que esse acoplamento seja inexprimível, não apenas desencorajado. Um produtor que descobrisse o domínio "sozinho" reintroduziria a dependência por dado, que é a travessia que o invariante não vê.

O custo é um argumento a mais na linha de comando. O que se compra é que o destino da escrita seja legível no comando que a produziu — e escrita de gabarito é exatamente o lugar onde "onde isso foi parar?" não pode depender de reconstruir contexto.

## 9. Pacotes a entregar

**Completo:** `ransomware-universidade` — 4 h, executiva, Linhas A + B + ruído, um ponto de ramificação por linha.

**Completo:** `fraude-academica-express` — 90 min, mista, Linha B expandida com os seis conjuntos de casos e avaliação por calibração.

**Apenas manifesto, sem injects:** `vazamento-lgpd`, `pesquisa-comprometida`. Validam que o loader lida com pacote incompleto e marcam roadmap. **Não escrever os injects destes dois.**
