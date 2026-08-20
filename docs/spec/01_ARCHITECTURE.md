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

**Exceção delimitada: TypeScript.** A stdlib de Python não traz analisador de TypeScript, e o CI não pode depender da aplicação que julga. Onde o alvo for `.ts`/`.tsx`/`.js`/`.jsx`, a varredura pode ser **léxica**, desde que seja declaradamente **conservadora** — admitindo falso positivo e nunca falso negativo — e que o limite esteja declarado no próprio verificador. A proibição continua valendo integralmente para Python, onde há AST. Esta exceção vale enquanto não houver analisador de TypeScript disponível sem depender da aplicação que o CI julga. Se essa condição deixar de valer, a exceção cai e os verificadores passam a exigir AST também para TypeScript.

O motivo da proibição original é preservado: regex é vedada porque **perde** casos. Varredura sobre-inclusiva não tem essa falha, e o custo que ela impõe — um falso positivo exige justificativa humana — recai sobre quem escreve o código, não sobre a garantia.

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

**A pausa tem começo e fim registrados.** PAUSAR grava `exercise_paused` e CONTINUAR grava `exercise_resumed` (`09_EVENT_MODEL.md` §4.1). O intervalo pausado é a distância entre os `wall_timestamp` dos dois eventos — **em tempo de parede, e não de exercício**, porque as duas marcas de exercício congelam na pausa e mediriam zero. É o espelho da escolha de `06_ACCEPTANCE_TESTS.md` T3, que usa `exercise_timestamp` justamente por ele excluir a pausa.

**Disparo manual continua permitido com o exercício pausado**; o que a pausa bloqueia é o disparo **agendado**. São dois comandos distintos em §6, e só o segundo aparece na frase do PAUSAR.

> As duas frases acima entraram no `spec-change` `exercise-resumed`. A primeira acompanha o evento novo. A segunda **já era implicação** de §3 dizer "agendado" e de §6 listar os dois disparos como coisas distintas, e passa a ser enunciada porque a justificativa do evento novo se apoia nela: é justamente por o disparo manual ser permitido que um evento posterior ao `exercise_paused` **não** prova que houve retomada. Exigência apoiada em propriedade não enunciada é a classe de defeito que o `spec-change` anterior consertou em três lugares.

**`exercise_timestamp` é marca do exercise-clock, não do relógio de parede.** Congela com o PAUSAR, junto de `exercise_time`, e avança na cadência do `clock_multiplier`. Os dois se separam no **rollback**: `exercise_time` é o rótulo `T+` e rebobina até o ponto de corte; `exercise_timestamp` **não rebobina**, e é o que torna ordenáveis entre si eventos de epochs distintas (`09_EVENT_MODEL.md` §1.1). O exemplo acima é de epoch única, onde os dois coincidem por construção — `T0 + exercise_time` —; a partir do primeiro rollback separam-se **pela quantidade de tempo de exercício que o rollback descartou**, e é essa separação que dá ao envelope duas marcas de exercício em vez de uma.

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

**A leitura do store é total.** `read_all` devolve todo evento gravado, sempre. **Nenhum caminho de leitura compartilhado filtra por epoch, por abandono ou por ponto de corte de rollback.** A exclusão dos eventos de epoch abandonada posteriores ao corte vive **no fold de `simulation_state`**, e em lugar nenhum mais — nunca no store, nunca em uma consulta que as outras projeções herdem.

O motivo é que **quatro das cinco projeções leem a epoch abandonada legitimamente**, cada uma pelo motivo declarado em `09_EVENT_MODEL.md` §3.1: `rehearsal` descarta a epoch do cálculo, `technical_failure` desconta o intervalo, `facilitation` e `adjudication` preservam a epoch anterior — e `aar_timeline` a renderiza com anotação de rollback. Só `simulation_state` é reconstruída, e é a única que o diagrama acima marca.

Um filtro no caminho de leitura compartilhado faria as outras quatro herdarem uma perda que nenhuma delas escolheu, **e nada falharia**: a projeção nasceria já cega, com a cegueira parecendo decisão de quem a escreveu. Como as quatro só existem a partir da Fase 6, o defeito ficaria latente por três fases, verde.

### 4.2 Rollback incrementa epoch

`rollback_performed` grava `to_inject_id`, `by_user`, `role`, `reason` e incrementa `simulation_epoch`. **Nada é removido.** Eventos da epoch anterior permanecem, marcados, e o AAR os renderiza como linha temporal rebobinada.

Motivos e sua semântica métrica: `09_EVENT_MODEL.md` §3.1.

**RESET TOTAL** grava `exercise_reset`, restaura defaults do contrato e o snapshot de business state do start. É recomeço, não correção.

**PAUSAR grava `exercise_paused` e CONTINUAR grava `exercise_resumed`** — ver §3. Os quatro comandos de execução do console (§6) passam a ter, cada um, evento no catálogo: sem isso, o estado de pausa não é reconstruível a partir do store, e o reinício exigido pela Fase 4 não teria como saber se o exercício estava parado.

### 4.3 Por que business state não reverte

Se um participante alterou nota, revogou VPN ou emitiu documento, isso aconteceu. Reverter gera estado impossível — evento na trilha de auditoria sem correspondente no banco — e destrói o artefato investigativo central.

### 4.4 `participant_action` com `effect_class: state_effect`

**Cinco dos dezessete `event_type` de `participant_action` do catálogo são `effect_class: state_effect`** (`09_EVENT_MODEL.md` §4.0 e §4.1): `communication_submitted`, `regulatory_notice_submitted`, `continuity_action_taken`, `vpn_access_revoked` e `identity_scope_disabled`. Todos podem mover flag. Quando um rollback atravessa uma dessas ações, **a flag reverte e o efeito de domínio não.**

**A exposição é estrutural, não de borda.** A ligação entre a ação e a flag **não é escolha de autoria de cenário**: `effects` existe em `inject` e em `option` de `decision_point` (`04_SCENARIO_SCHEMA.md` §5), e nenhuma das duas alcança um `event_type` de `participant_action`. Nenhum pack pode ligá-la, e nenhum pack pode desligá-la — vale para todo exercício que rode o adapter.

**A ligação ainda não existe, e é isso que esta seção descreve: uma exposição que se materializa quando ela existir.** O que quer que venha a ligá-los produz estado de simulação, e estado de simulação vem do fold — §4.1: *toda projeção é reconstruível do zero*, e o que não passa pelo fold não sobrevive à reconstrução. A forma dessa ligação é decidida na fase que traz o serviço que a consome.

O caso concreto: `vpn_access_revoked` é produzido por `POST /identity/revoke` (`domains/academus/observability_hooks.yaml`), e o cenário que esta seção descreve é o de esse evento mover `academus.federated_session_active`, cujo default é `true`. O defensor revoga o acesso e a flag cai; um rollback anterior à revogação a devolve a `true` em `simulation_state`, enquanto o registro da revogação segue vivo — no store e nas outras quatro projeções — e o que o domínio escreveu, que é Business State, não volta por §4.3.

> **As duas frases do mecanismo foram corrigidas no `spec-change` `quatro-marcas-e-quem-escreve-flag`; era a P2-9.** Elas diziam que *"a ligação é feita pelo **serviço** que atende a rota"* e que *"o serviço que atende a rota **escreve** `academus.federated_session_active`"*.
>
> **Eram verdadeiras quando escritas, e deixaram de ser por decisão do mesmo ciclo.** A Fase 2 decidiu que os `effects` são resolvidos contra o pack pelo fold, e não gravados no store — o que torna `simulation_state` reconstruível do zero, como a §4.1 exige. Sob essa leitura, **serviço nenhum escreve flag**: estado que não vem do fold não sobrevive à reconstrução, e um serviço que escrevesse direto produziria estado invisível ao rollback.
>
> **Não houve momento em que alguém errou.** A primeira decisão estava certa contra o que se sabia; a segunda foi tomada depois, e derrubou a primeira sem que se visse. É a classe que o registro da Fase 1 chama de §1.6 — a afirmação que envelhece depois de correta —, e ela foi pega **aqui** em vez de três fases adiante.
>
> **A tese da seção não dependia de quem escreve, e por isso sobrevive inteira:** o rollback reverte a flag e não reverte o efeito de domínio; a exposição é estrutural; o resíduo é maior nos dois `event_type` de efeito externo; e o participante pode ver o mundo contradizer a própria ação. O que morreu foi a frase do **caminho**.
>
> **O que fica em aberto é a forma da ligação, e ela não é decidida aqui.** Desenhá-la antes de existir o serviço que a consome seria inventar vocabulário para prever o módulo. O primeiro consumidor é a **Fase 8**, cujo item de DoD *"as sete ações de continuidade aplicam efeito mecânico e custo"* obriga a ligação — `continuity_action_taken` é um dos cinco `state_effect`. O caso concreto usado acima chega depois: o `federated-identity-simulator` que produz `vpn_access_revoked` é da **Fase 11**.
>
> **A frase anterior dizia que a Fase 3 traz os dois, e estava errada na metade que importava.** A `academus-api` é da Fase 3; o `federated-identity-simulator` é da Fase 11, como a tabela de fases de `07_IMPLEMENTATION_PHASES.md` sempre disse — e nenhum dos cinco `event_type` de `participant_action` com `effect_class: state_effect` é entregável da Fase 3, que emite `audit_query_performed`, de classe `observation`.
>
> **A afirmação atravessou três camadas sem que ninguém a conferisse na fonte**: nasceu numa pendência do registro da Fase 2, foi repetida aqui pelo `spec-change` que corrigiu a frase do mecanismo, e foi repetida de novo na instrução que abriu a Fase 3. Cada camada confiou na anterior. É a §1.5 da Fase 1 — *ler a fonte, não lembrar dela* — na forma que não parece §1.5 em nenhum ponto isolado, porque em cada um deles havia uma fonte aparente.

**O resíduo não tem o mesmo tamanho nos cinco, e é maior nos dois de efeito externo.** `communication_submitted` e `regulatory_notice_submitted` são `state_effect` porque *o ato* produz efeito fora do exercício — `09_EVENT_MODEL.md` §4.1 diz que "o público soube, o regulador foi notificado, o prazo regulatório correu". Neles o rollback devolve a flag e não existe o que devolva o que já foi comunicado. `continuity_action_taken` fica entre os extremos: a ação tem custo já pago em Business State, que a §4.3 mantém. `vpn_access_revoked` e `identity_scope_disabled` são as duas de efeito interno, e mesmo nelas o que o domínio escreveu permanece. **Em nenhum dos cinco o rollback desfaz o ato — o que varia é só o tamanho do que sobra fora da flag.**

**O participante pode ver o mundo simulado contradizer a própria ação, e isso é desenho, não defeito.** Rollback atua sobre Simulation State, a única camada que a tabela da §4 declara reversível. O que ele fez continua tendo acontecido, continua registrado e continua sendo camada `append-only` permanente (`00_MASTER_SPEC.md` §5.5), com `nunca` na coluna Reversível da tabela da §4 — e a reversão da flag não contradiz nada disso.

**Consequência de facilitação, e ela carrega o peso todo.** Sendo estrutural, a exposição não tem mitigação de desenho: não há pack que a evite nem configuração que a desligue. O que resta é o anúncio, e ele tem dois destinatários distintos:

- **Antes do corte** — quem escolhe o ponto de rollback considera quais dessas ações o corte atravessa, e em especial se há alguma das duas de efeito externo entre elas. Rollback sobre elas não é operação neutra: tem custo de coerência, o custo cresce com o resíduo, e ele pertence à decisão de facilitação, não à surpresa da sala.
- **Depois do corte** — o atravessamento é dito à equipe, na retomada e no debriefing. Sem isso, a equipe lê como falha do range aquilo que é a regra do exercício, e o AAR ganha uma discussão sobre bug no lugar da discussão sobre o que a ação significou.

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

**participant-api** — a superfície pela qual a **persona declara**. As ações de `03_EXERCISE_DESIGN.md` §3.4 são atos do **exercício**, e não do domínio: quem as autoriza é a persona, que é vocabulário de desenho de exercício. Por isso elas vivem no core, com RBAC por persona, e não na `academus-api`.

**A persona vê pelo domínio e declara pelo núcleo.** Os painéis de `03_EXERCISE_DESIGN.md` §6 são telas do adapter — `domains/<adapter>/panels/` —, e é a tela do adapter que **chama** esta superfície. A separação não é organizacional: `domains/` não pode conhecer persona, e o verificador de superfície já a recusa como vocabulário de token no perfil de domínio. Uma rota de declaração no adapter exigiria desfazer essa guarda.

Distinta do `gm-console`, que é facilitação (§7 de `03`), e do `participant-view` (`/plateia`), que é **projeção de sala** e não recebe ato de participante (`05_SECURITY_REQUIREMENTS.md` §8).

**gm-console** — três papéis (`03_EXERCISE_DESIGN.md` §7), seletor de pack, disparo manual e agendado, PAUSAR / CONTINUAR / ROLLBACK / RESET, estado de flags, registro, geração de AAR.

> A referência dizia `§6`, que é **Personas**; os três papéis de facilitação são **§7**. A troca estava na linha que descreve o console, e é a própria confusão que a entrada acima existe para desfazer — corrigida no mesmo `spec-change`, porque publicar a distinção nova ao lado da troca antiga a enfraqueceria.

**telemetry-forwarder** — CEF via Syslog UDP/TCP para destino laboratorial configurável. **A telemetria é projeção de fato canônico**, não emissão independente; `precursor_events.jsonl` é gerado, não autoral (`08_EVIDENCE_SIMULATOR.md`). Modo Live e modo Replay. Campos `src`, `dst`, `suser`, `severity`, `outcome`, `cnt`, `cs1`–`cs4`.

**evidence-simulator** — ver `08_EVIDENCE_SIMULATOR.md`.

**Observabilidade** — Prometheus (requests, erros, autenticações, sessões AVA, fila de matrícula) e Grafana com dashboard *Operações* e dashboard *Exercício*. **Papel: evidência, para o time azul.** Distinto do wallboard. Não construir o mesmo painel duas vezes.

---

## 7. Desempenho

- Contadores do wallboard mantidos em Redis, atualizados por evento
- **Proibido `COUNT(*)` sobre tabelas de nota ou matrícula em rota de tempo real**
- Seed via `COPY` / `executemany`, nunca ORM linha a linha. Alvo: dataset completo em < 5 min
- Reconstrução de projeção a partir do event store deve completar em < 3 s para exercício de 4 h
