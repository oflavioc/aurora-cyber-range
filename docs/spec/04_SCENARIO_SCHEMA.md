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
  reconvergence_required: true
calibration:
  threshold: 0.15          # Brier máximo para considerar integridade validada (TTIV)
```

`required_rubrics` inclui a **versão**. Rubrica ausente ou em versão diferente impede a carga.

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
range-cli evidence build <path>      # gera projeções a partir do ground truth
range-cli evidence verify <path>     # consistência fato → projeções
```

`validate`, `lint` e `evidence verify` rodam no CI. `dryrun` é pré-requisito de ensaio.

## 9. Pacotes a entregar

**Completo:** `ransomware-universidade` — 4 h, executiva, Linhas A + B + ruído, um ponto de ramificação por linha.

**Completo:** `fraude-academica-express` — 90 min, mista, Linha B expandida com os seis conjuntos de casos e avaliação por calibração.

**Apenas manifesto, sem injects:** `vazamento-lgpd`, `pesquisa-comprometida`. Validam que o loader lida com pacote incompleto e marcam roadmap. **Não escrever os injects destes dois.**
