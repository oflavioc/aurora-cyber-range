# Fase 1 — Contratos e esqueleto

Conforme `07_IMPLEMENTATION_PHASES.md` §229: resumo técnico, estrutura, endpoints, migrations, variáveis de ambiente, DoD item a item, pendências e próxima fase.

---

## 1. Resumo técnico

Os **seis contratos** de `contracts/` — JSON Schema 2020-12, decisão D4 —, o `flags.yaml` dos dois adapters, a geração de constantes tipadas para Python e TypeScript, a árvore de diretórios, `docker-compose` com Postgres e Redis pinados por digest, Alembic inicializado, o primeiro `pyproject.toml` do projeto, e o executor de exemplos dos contratos com o seu próprio teste negativo.

**Nenhuma lógica de negócio, nenhuma tela, nenhum seed** — os NON-GOALS da fase.

### 1.1 Dois conflitos internos da spec, resolvidos antes de escrever contrato

Encontrados ao desenhar `events.schema.yaml`. Nenhum podia ser resolvido por inferência — `CLAUDE.md` proíbe, e o primeiro toca o MASTER_SPEC. Foram para `spec-change` próprio, sem código junto, mergeado antes desta implementação.

**`facilitation` não era um `truth_layer`.** `00` §3 e `09` §2 diziam "exatamente um destes valores" e listavam **quatro**; `09` §4.1 agrupava o catálogo em **cinco**. Qual seria o `truth_layer` de `inject_fired`, sendo o campo obrigatório em todo evento?

Resolvido como **cinco valores, quatro verdades**: as quatro camadas afirmam algo sobre o *incidente*, `facilitation` afirma algo sobre a *máquina de exercício*. Ortogonal ao modelo, não uma quinta camada dele.

**`separate_incident_declared` era usado e não existia no catálogo.** `03` §1.1 e `09` §6 o usam como evidência `auto` do OBJ-03. O catálogo é registro fechado com CI que falha em `event_type` não registrado — um `objectives.yaml` escrito conforme o **exemplo normativo do `03`** seria recusado pelo linter.

### 1.2 O checkpoint ⏸ aconteceu, e foi cumprido na forma e não no fundo

A Fase 1 é ⏸. O `KICKOFF_PROMPT` manda parar e apresentar quatro coisas antes de qualquer código: árvore, `contracts/` completo, catálogo com `truth_layer`, e **as três decisões de modelagem mais arriscadas com recomendação**.

**A apresentação ocorreu e foi aprovada.** As quatro coisas foram submetidas antes do primeiro arquivo, com a frase *"Aguardo. Não escrevo nada até você decidir os três"*, e a resposta foi *"Aprovado. Pode seguir com as recomendações elaboradas"*.

**O defeito está no item 4, e é meu.** Das três decisões apresentadas, **duas não eram decisões de modelagem**: D1 (`facilitation` como `truth_layer`) e D2 (`separate_incident_declared` fora do catálogo) eram **escalações de contradição interna da spec** — coisas que `CLAUDE.md` me proíbe de resolver por inferência e que eu tinha obrigação de submeter de qualquer forma. Só D3, o sistema de tipos das flags, era decisão minha.

**Consequência concreta:** as decisões genuinamente arriscadas deste commit — as que custam caro para desfazer nas fases seguintes — **nunca foram submetidas**, porque duas escalações ocuparam o lugar delas. O checkpoint foi satisfeito como procedimento e falhou como salvaguarda.

É a mesma classe que a Fase 0 registrou repetidamente: cumprir a forma do mecanismo e perder a propriedade que ele deveria garantir. Aqui não houve execução sem submissão — houve **submissão do que não estava em risco**.

Ver §6, pendência **P1-5**, para as decisões que faltavam — quatro, submetidas e decididas depois, uma a uma.

### 1.3 O item 1 da DoD esteve ✅ por conter exemplos, quando a DoD pede validá-los

**É o defeito mais instrutivo desta fase, e está em destaque por decisão do operador.**

A tabela de DoD desta fase marcou ✅ o item *"os seis contratos existem e validam exemplos positivos e negativos"*, com a justificativa: *"cada contrato traz `example_valid` e `examples_invalid` com o motivo nomeado"*.

**A DoD não diz que os contratos contêm exemplos. Diz que os validam.** Nada, em momento algum, executou um único desses exemplos. O ✅ afirmava uma propriedade a partir da presença do mecanismo que deveria produzi-la.

#### É a mesma classe do B1 da primeira auditoria da Fase 0

Aquele B1 foi: `objective_ids` **não era verificado** em `range-core/engine/`, `/clock/`, `/state/`, `/telemetry/`, `/evidence/` e `/rubrics/`. O verificador existia, rodava, saía zero e o CI ficava verde — sobre seis diretórios que ele não varria. Mecanismo presente, propriedade ausente, e o verde afirmando a propriedade.

Aqui: exemplos presentes, validação ausente, e o ✅ afirmando a validação.

#### O agravante

Este defeito apareceu num documento que **eu escrevi depois** das dezenove rodadas da Fase 0 — rodadas cujo conteúdo era, repetidamente, esta exata lição. O `state_flags.schema.yaml` chegou a escrever, ao lado dos próprios exemplos negativos, que *"contrato sem exemplo negativo não prova que recusa nada — é a mesma lição do harness da Fase 0"*. A lição estava escrita, correta, no arquivo, e mesmo assim o item foi marcado por presença.

**Saber enunciar a regra não é o mesmo que aplicá-la a si.** É o mesmo padrão do defeito de checkpoint da §1.2: forma cumprida, propriedade perdida.

#### O que fechou

`scripts/check_contract_examples.py` executa os exemplos nas duas camadas, e `scripts/check_contract_examples_probes.py` prova que o executor reprova contra defeito plantado. **As contagens ficam na saída dos próprios scripts, não repetidas aqui** — número em prosa envelhece sozinho, e envelheceu: ver L2 da terceira auditoria em P1-19. O item 1 só voltou a ✅ depois disso — e a execução, quando chegou, encontrou **oito defeitos** nos exemplos que estavam ali marcados como suficientes. Ver P1-6.

**Consequência adotada:** item de DoD cuja evidência seja a existência de um artefato, e não a execução dele, é ⚠️ até que algo o execute.

### 1.4 Sistema de tipos das flags — decisão apresentada e aprovada

`01` §5.2 exemplifica só `boolean`, mas o inject de `04` §5 atribui `academus.lms_session_drop_rate: 0.4`, e essa flag está em `required_flags` do manifesto.

Declarado: **`boolean | number | enum`**, com `enum` exigindo `values` e `number` aceitando `min`/`max`. **A decisão D7 endureceu esta última**: `min` passou a ser obrigatório e `max` obrigatório ou `unbounded` explícito — ver P1-5.

**`string` livre não entra, por decisão.** É o tipo que o codegen não consegue tipar de forma útil em TypeScript, que o wallboard não sabe renderizar por convenção (`01` §5.3), e que permitiria valor nunca declarado. `enum` cobre estado ordinal — *normal / degraded / offline / restoring* — sem abrir essa porta.

`04` §4 proíbe alterar semântica de campo dentro da mesma `schema_version`, então errar aqui custaria migração.

---

## 2. Estrutura de diretórios

```
range-core/                      esqueleto: clock, events, state, engine/{loader,
                                 migrations,branching}, objectives, rubrics, metrics,
                                 telemetry, evidence, aar, api, web/{gm-console,
                                 participant-view,wallboard-shell}
domains/
  academus/                      flags.yaml (12 flags), observability_hooks.yaml,
                                 generated/{flags.py,flags.ts}, models/ api/ web/
                                 seed/ panels/ evidence_generators/
  prontus/                       STUB.md, flags.yaml (2 flags), generated/
scenarios/academus/              vazio nesta fase
contracts/                       os seis schemas + README.md (subconjunto YAML e
                                 extensoes x-aurora-*) + generated/{events.py,events.ts}
scripts/                         phase0_negative_tests.py, check_contract_examples.py,
                                 check_contract_examples_probes.py, audit_report.py
alembic/                         env.py, script.py.mako, versions/
docker-compose.yml  .env.example  alembic.ini  pyproject.toml
```

O executor de exemplos mora em `scripts/` e não em `tools/` porque `01_ARCHITECTURE.md` §2 declara que os verificadores de invariante **são seis**; um sétimo arquivo em `tools/` contradiria a spec, e ele não é verificador de invariante — é executor de fixture de contrato.

`generated/` co-localizado com a fonte canônica **não é escolha desta fase** — `codegen.py` da Fase 0 já o fixa, e o motivo está registrado lá: artefato com nome de adapter dentro do core exigiria exceção no `check_core_boundary.py`, e invariante com exceção é invariante morto.

## 3. Endpoints, migrations e variáveis de ambiente

**Endpoints: nenhum.** A API chega na Fase 3.

**Migrations: nenhuma.** Alembic está **inicializado** — `env.py`, `script.py.mako`, `versions/` vazio — que é o que a DoD pede. `target_metadata` fica `None` de propósito: os modelos chegam na Fase 5, e apontar para metadata inexistente produziria autogenerate vazio que pareceria funcionar. **Inicializado em arquivo, nunca executado**: a biblioteca não está instalada — ver P1-9.

**Variáveis** — `.env.example` versionado, `.env` no `.gitignore` (`05` §6):

| Variável | Papel |
|---|---|
| `RANDOM_SEED` | determinismo (`00` §8) |
| `POSTGRES_DB` / `USER` / `PASSWORD`, `DATABASE_URL` | business state |
| `REDIS_URL` | projeção de simulation state |
| `AURORA_JWT_SECRET` | assinatura de token |
| `AURORA_BIND_HOST` / `PORT` | bind em `127.0.0.1` (`05` §6) |
| `SYSLOG_HOST` / `PORT` / `PROTOCOL` | destino laboratorial configurável |

`POSTGRES_PASSWORD` **não tem default** no compose: ausente, ele falha em vez de subir com valor previsível. `05` §8 proíbe senha trivial reutilizável.

---

## 4. Verificação executada

**Os seis verificadores liberam a árvore limpa**, e — o que importa mais — cada invariante foi provado por **violação plantada**, agora com contrato real para verificar. Na Fase 0 eles rodavam contra uma árvore onde `range-core/`, `domains/` e `contracts/` nem existiam.

| Violação plantada | Verificador | rc |
|---|---|---|
| `from domains.academus.models import Aluno` em `range-core/state/` | `check_core_boundary` | 1 |
| literal `"academus.enrollment_offline"` fora do gerador | `check_contract_literals` | 1 |
| literal `"separate_incident_declared"` fora do gerador | `check_contract_literals` | 1 |
| `objective_ids` no envelope emitido | `check_event_envelope` | 1 |
| artefato gerado corrompido | `codegen.py --check` | 1 |

Árvore limpa depois de todos os probes.

**`codegen.py` ganhou o modo `--write`** — era a pendência **P2** do `fase_0.md`, adiada de propósito: modo de escrita sem contrato real para consumir e sem probe que o exercite seria código não verificado dentro do próprio mecanismo de verificação.

`--check` continua sendo o único modo que o CI invoca, e continua estritamente read-only. Verificado nos dois sentidos: gera, `--check` passa; corrompe um artefato, `--check` sai `1`; regenera, volta a `0`. `--write` rodado duas vezes seguidas não reescreve o que já está em sincronia.

**Os contratos são legíveis pelo parser da Fase 0** — subconjunto YAML estrito, sem âncoras, aliases, merge keys ou escalares multilinha. Um parser tolerante seria pior que grep: faria o verificador passar por ter lido o contrato errado, em silêncio.

### 4.1 O que passou a ser executado nesta fase

Onze verificações, todas verdes na árvore limpa:

| Verificação | O que prova | Dependência |
|---|---|---|
| os seis verificadores de `tools/` | os quatro invariantes arquiteturais | stdlib |
| `scripts/phase0_negative_tests.py` | que os seis **reprovam** — **27** leituras, 36 escritas, 112 provas | stdlib |
| `scripts/check_contract_examples.py` | 9 exemplos positivos validam; **61** negativos são recusados **pela camada que cada um declara**, cada um por **um só** defeito; `effect_class` cobre o catálogo exatamente | `jsonschema` |
| `scripts/check_contract_examples_probes.py` | que o executor **reprova** contra defeito plantado, em cada eixo de fixture mentirosa e de instância real inválida | `jsonschema` |
| `scripts/check_spec_examples.py` | que **todo exemplo normativo da spec é aceito** pelo contrato que o governa, e que nenhum bloco fica sem dono | `jsonschema`, `pyyaml` |
| `scripts/check_spec_examples_probes.py` | que esse verificador **reprova** quando o contrato regride, quando um bloco perde dono e quando uma âncora envelhece | `jsonschema`, `pyyaml` |

As duas últimas rodam no job `contratos`, separado, **o único que instala dependência** — ver P1-6 e P1-10.

**O executor não aceita "falhou, logo está provado".** Para `rejected_by: schema` o schema precisa recusar; para `rejected_by: x-aurora-*` o schema precisa **aceitar** — senão a fixture não isola a regra que diz provar — e a regra nomeada precisa ser a única a disparar. Foi essa exigência que revelou três fixtures violando duas regras cada.

---

## 5. Definition of Done — status

| # | Item | Status |
|---|---|---|
| 1 | Os seis contratos existem e validam exemplos positivos e negativos | ✅ **executados** — positivos validam, negativos são recusados pela camada que cada um declara e por um só defeito, instâncias reais validadas, e o executor reprova contra defeito plantado em cada eixo. Contagens na saída do script. Ver §1.3, P1-6 e P1-19 |
| 2 | Constantes tipadas geradas em Python e TypeScript para flags e event types | ✅ 32 event types, 12 flags, seis artefatos |
| 3 | Teste de fronteira core/adapter passa (por AST) | ✅ e falha contra import plantado |
| 4 | `event_type` fora do catálogo é rejeitado | ✅ catálogo fechado; literal fora do gerador reprova |
| 5 | Os seis verificadores liberam árvore limpa e falham contra violação plantada | ✅ tabela §4 |
| 6 | `codegen.py --check` detecta dessincronia e não escreve | ✅ provado nos dois sentidos |
| 7 | `docker compose up` sobe Postgres e Redis | ✅ **verificado por execução** em 14/08/2026 — ver P1-1 |
| ~~8~~ | ~~`RANDOM_SEED` lido de `.env`~~ | ➡️ **migrado para a Fase 2** pelo spec-change `effect-class-marcas-temporais-e-seed`. Ver P1-2 e P1-17 |

**A DoD da Fase 1 passa a ter sete itens, e os sete passam** — condicionado ao merge do spec-change `effect-class-marcas-temporais-e-seed`, que é quem move o item 8 para a Fase 2. Enquanto ele não mergear, o item 8 continua formalmente nesta lista e a fase continua aberta.

**Por que o item 8 migrou, e não foi fechado por atestação.** Eu havia proposto escrever um `range-core/config.py` mínimo para o item poder fechar. O operador recusou:

> *"Você marcou o item honestamente como ⚠️ e agora propõe escrever código para poder marcá-lo ✅. Isso é fechar item de DoD criando o consumidor, não é evidência."*

Depois, com o auditor apontando o mesmo item como BLOCKER nas duas rodadas, a decisão foi migrá-lo por spec-change, e o raciocínio registrado pelo operador é o que importa aqui:

> *"Os itens 9-13 da Fase 0 eram inverificáveis por qualquer auditor — CI, branch protection, coisas fora do worktree. Este é perfeitamente verificável, só não está feito. Atestação para item verificável é declarar fato que não ocorreu."*

O item não sumiu: virou item da Fase 2, com o texto endurecido para **"lido de `.env` por código do `range-core`, não por atestação"**. O teste real continua sendo `00` §8 — mesmo seed, dataset byte-idêntico em duas execuções.

O item 2 dizia **14 flags**. São **12**, conforme `domains/academus/generated/flags.py`, e a §2 deste mesmo documento já dizia 12 — o registro se contradizia. Corrigido.

---

## 6. Pendências

| # | Assunto | Status |
|---|---|---|
| P1-1 | `docker compose up` | ✅ fechada, verificada por execução |
| P1-5 | As quatro decisões de modelagem | ✅ fechadas, decididas pelo operador |
| P1-6 | Execução dos exemplos dos contratos | ✅ fechada |
| P1-8 | Pinagem por digest | ✅ fechada |
| P1-9 | Alembic executável | ✅ fechada, confirmada por execução |
| P1-10 | `contratos` é o quarto context obrigatório | ✅ documentado — reposição do check é a P1-18 |
| P1-12 | `simulation_epoch` com piso inventado contra critério normativo | ✅ fechada — achado pelo auditor |
| P1-13 | Achados da auditoria, rodadas 1 e 2 | ✅ BLOCKER/HIGH/MEDIUM/LOW corrigidos, salvo os abaixo |
| P1-14 | Predicado satisfeito por declaracao (M3) | ⚠️ **aberta, aguarda decisão de modelagem** |
| P1-15 | `exercise_timestamp`: `01` §3 x `09` §1.1 | ⚠️ **escalação aberta, dois não-master** |
| P1-16 | Falha de processo: relatório registrado sem ser tratado | ✅ registrada, regra adotada |
| P1-17 | Spec-change aplicado: `effect_class`, marcas temporais, item 8 | ✅ spec commitada, código implementado |
| P1-18 | `contratos` exigido antes de existir em `main` travou o spec-change | ⚠️ **aberta** — check removido; volta após o merge do PR de código |
| P1-19 | Terceira auditoria: contrato divergia da spec em 4 campos | ✅ corrigidos, com a camada que faltava |
| P1-20 | `information_distribution.yaml` sem contrato | ⚠️ aberta, resolve na Fase 10 |
| P1-2 | `RANDOM_SEED` declarado, não consumido | ⚠️ aberta por decisão — item 8 da DoD |
| P1-3 | `evidence.schema.yaml` valida artefato ainda não produzido | ⚠️ aberta, resolve na Fase 9 |
| P1-4 | `observability_hooks.yaml` tem dois hooks | ⚠️ aberta, resolve na Fase 3 |
| P1-7 | Id de inject pode vazar a linha | ⚠️ aberta, apontada para a Fase 3 |
| P1-11 | Sem driver de banco nem cliente Redis | ⚠️ aberta, resolve na Fase 2 |

---

### Fechadas

#### P1-1 — `docker compose up`: FECHADA, verificada por execução

Subido pelo operador na máquina nova e verificado em 14/08/2026. Não é só "os contêineres existem" — a integração foi exercitada:

| Verificação | Resultado |
|---|---|
| `docker compose ps` | `aurora-postgres` e `aurora-redis` **Up (healthy)**, healthcheck dos dois passando |
| Postgres: conexão + autenticação + query | `PostgreSQL 16.4 on x86_64-pc-linux-musl` |
| Postgres: encoding e timezone | `UTF8`, `UTC` |
| Redis: `PING` | `PONG` |
| Redis: roundtrip `SET`/`GET`/`DEL` | `OK` / `ok` / `1` |
| Alcançável do host | `127.0.0.1:5432` e `127.0.0.1:6379` aceitam conexão |
| **Não** alcançável fora do loopback | `::1` recusa conexão nos dois; `PORTS` publica só em `127.0.0.1` (`05` §6) |
| Redis sem persistência, como declarado | `save` vazio, `appendonly no` — a projeção volta do event store (`01` §4) |
| Volume | `aurora_pgdata` existe |

As credenciais nunca foram lidas: os comandos usam `$POSTGRES_USER`/`$POSTGRES_DB` de dentro do contêiner. `.env` permanece fora do alcance, conforme `CLAUDE.md`.

#### P1-5 — As quatro decisões de modelagem: FECHADAS

**Status: DECIDIDAS pelo operador em 14/08/2026**, uma a uma, apresentadas por custo de reversão. As quatro estão implementadas neste commit. Nenhuma tocou `docs/spec/`.

#### D4 — Contratos como JSON Schema 2020-12, não vocabulário próprio — **decidido: B, agora**

Os seis contratos eram YAML descritivo com chaves inventadas por mim. Das 65 ocorrências de vocabulário, **62 eram JSON Schema com outros nomes**; só 3 — integridade referencial entre arquivos — não têm equivalente pronto. E o vocabulário já havia divergido de si mesmo com um commit de idade: `must_exist_in_event_catalog` e `event_must_exist_in_catalog`, mesmo conceito, dois nomes, nada que pegasse isso porque não havia gramática.

**Correção de escopo que derrubou o argumento que eu tinha usado para manter.** Registrei aqui que "a Fase 0 exige apenas stdlib". `docs/process/PHASE_0_CHECKLIST.md:44` diz *"usar apenas stdlib Python **na Fase 0**, para o CI não depender da aplicação ainda"* — é restrição dos verificadores de CI, não da aplicação. `alembic/env.py:15-16` importa `alembic` e `sqlalchemy`. Apliquei uma restrição de escopo do CI a uma decisão de escopo da aplicação.

O que mudou:

- os seis contratos são JSON Schema 2020-12 autorados em YAML, com os comentários preservados — eles são a maior parte do valor destes arquivos;
- as regras de referência cruzada viram um conjunto **fechado e nomeado** de anotações `x-aurora-*`, documentado em `contracts/README.md`. É o único código de validação escrito à mão que sobra, agora com fronteira explícita em vez de difusa;
- `tools/_common.py::load_declared_event_types` passa a ler o catálogo dos `$defs` prefixados `event_type_`. Os `enum` que o validador usa são os mesmos que geram as constantes — não existe segunda cópia da lista;
- `scripts/phase0_negative_tests.py` planta o catálogo no formato novo. Os dois probes do catálogo continuam falhando contra violação plantada.

**Ganho estrutural, além do previsto.** Regras que eram prosa viraram schema executável: `event_type` pertencer à camada declarada (nada verificava — `containment_declared` com `truth_layer: ground_truth` passava), objetivo obrigatório salvo `noise: true`, e condição de branch e predicado de verificação como árvores **fechadas** — condição que dependa de juízo deixou de ser expressável, em vez de ficar proibida por comentário. E `additionalProperties: false` tornou anexo em evidência e classe `derived` inexpressáveis.

**Defeito dormente encontrado na conversão.** `tools/_common.py::_parse_scalar` devolve o texto cru entre aspas, sem processar escapes. Os padrões antigos usavam aspas duplas com dois backslashes antes do ponto, o que num parser YAML real vira um backslash e neste vira dois — regex errada. Ninguém consumia esses padrões, então estava dormente, e a Fase 2 os entregaria a um validador de verdade. Todo regex passou a aspas simples, onde os dois parsers concordam. Regra de autoria registrada em `contracts/README.md`.

#### D5 — `service_restoration` aceita predicado ou `not_applicable` — **decidido: C**

A spec declara a obrigatoriedade sobre a **seção**, nunca sobre cada chave (`03` §3.1, `04` §84); as duas aparecem no exemplo porque o pack do exemplo tem as duas. Exigir ambas impediria a carga de `fraude-academica-express`, que `04` §9 manda entregar.

A chave continua **obrigatória** — omitir continua sendo falha de carga. O que muda é que inaplicável deixou de ser indistinguível de esquecido: `not_applicable: "<motivo>"`, com motivo não vazio. O AAR passa a poder imprimir "TTRV não aplicável" em vez de nulo ou de um zero que parece medição.

Segundo exemplo positivo acrescentado ao contrato, com a forma que `fraude-academica-express` pode ter.

#### D6 — Identificadores sem teto inventado — **decidido: afrouxar**

`^GT-[A-Z]-[0-9]{3}$` era invenção minha, com teto de 999 fatos por linha e linha de um caractere. Agora `^GT-[A-Z0-9]+-[0-9]+$`, e a verificação real passou para onde ela existe: **unicidade** (`x-aurora-unique`) e **resolução** das três referências (`materializes_facts`, `projects_facts`, `fact_check_against`). O ponto continua proibido no padrão, e agora por motivo declarado: `04` §7 usa o id dentro de `facts.GT-A-020.records_affected`.

- `case_id` ganhou padrão (`^GC-[0-9]+$`): não tinha nenhum enquanto `fact_id` tinha um estrito.
- `inject_id` passou a `^[A-Z]+[0-9]+$`, com **prefixo sem semântica de linha** — ver P1-7.
- `objective_id` **mantém** `^OBJ-[0-9]{2}$` e o teto de 99, por decisão registrada: a spec só exibe OBJ-01 a OBJ-10 e nenhum pack se aproxima. Era o único da classe cujo teto não bloqueava entregável.

#### D7 — `number` exige domínio declarado — **decidido: exigir com escape explícito**

`state_flags.schema.yaml` declarava `min`/`max` opcionais para `number` **contra a justificativa escrita ao lado**, no mesmo bloco. Agora `min` é sempre obrigatório e `max` é obrigatório ou `unbounded` explícito — mesma forma da D5: ausência e esquecimento deixam de ser indistinguíveis. As 12 flags atuais já declaravam faixa onde precisavam; custo de migração: zero.

#### A quarta do registro anterior, absorvida

Os exemplos moram dentro dos contratos. Com a D4=B isso deixou de ser decisão: `examples` é palavra-chave padrão e a contraparte negativa é `x-aurora-invalid-examples`.

**Duas correções de forma que a execução tornaria visíveis:**

1. **Instâncias negativas eram parciais.** O exemplo de "event_type fora do catálogo" tinha dois campos, e falharia por faltar `event_id` e `producer` — não pelo motivo que nomeia. Executáveis, provariam a coisa errada. Cada instância negativa passou a ser completa com **um** defeito.
2. **Nem todo exemplo negativo é recusado pelo schema.** `event_type` com erro de digitação é uma string perfeitamente válida para o JSON Schema; quem o recusa é a resolução de referência. Cada exemplo passou a declarar `rejected_by`, e o que nenhuma camada recusa saiu dos exemplos negativos: "capability_gap nomeando produto" (`produto_xyz_edr` casa com o padrão) e "source_ip fora da faixa" (guardado por `tools/check_synthetic_data.py`) viraram `x-aurora-linter-rules`. Exemplo negativo que nada recusa é fixture que passa sem provar nada.

Também corrigido: o exemplo negativo "formato fora do conjunto v1" usava `format: syslog_text`, que **é** do conjunto v1 — não era inválido. Agora usa `pcap`.

#### P1-6 — Execução dos exemplos dos contratos: FECHADA

Era o item 1 da DoD, e ele não fechava sozinho. Ver §1.3 para o defeito que esta pendência corrige.

**O que entrou:**

- **`pyproject.toml`** — o primeiro manifesto de dependência do projeto, com `jsonschema`, `alembic` e `sqlalchemy`. Aprovado pelo operador. Até aqui o repositório não declarava dependência nenhuma, e `alembic/env.py` importava duas bibliotecas que ninguém tinha instalado.
- **Job `contratos` no CI**, separado. **É o único que instala dependência.** Os jobs `arquitetura` e `seguranca` continuam stdlib puro, sem `pip install`: o gate que a Fase 0 construiu em dezenove rodadas não ganha dependência, porque um gate que depende da aplicação que ele julga deixa de ser gate. Foi a propriedade que o operador exigiu preservar, e ela está preservada.
- **`scripts/check_contract_examples.py`** — executa as duas camadas. Mora em `scripts/` e não em `tools/` porque `01_ARCHITECTURE.md` §2 declara que os verificadores de invariante **são seis**; um sétimo arquivo em `tools/` contradiria a spec.
- **`scripts/check_contract_examples_probes.py`** — prova que o executor reprova.

**A correspondência com `rejected_by` é o que impede a fixture mentirosa.** O executor não aceita "falhou, logo está provado": para `rejected_by: schema` o schema precisa recusar; para `rejected_by: x-aurora-*` o schema precisa **aceitar** — senão a fixture não isola a regra que diz provar — e a regra nomeada precisa ser a **única** a disparar.

**Resultado no fechamento desta pendência** — os números cresceram depois, e ficam registrados aqui como o estado daquele momento: 9 exemplos positivos, 53 negativos, 6 contratos. E o executor reprovava nos seis eixos de fixture mentirosa de então: positivo que não valida, positivo que viola regra `x-aurora`, `rejected_by: schema` que o schema aceita, regra declarada que não dispara, fixture que o schema já recusa, e fixture sem `rejected_by`.

**A execução encontrou oito defeitos nos exemplos que já estavam marcados como suficientes:**

| # | Defeito | Como só a execução o revelaria |
|---|---|---|
| 1 | `_no()` do próprio executor não tratava índice de array em JSON Pointer | `oneOf/0` devolvia vazio, a caminhada morria em todo combinador **em silêncio**, e nenhuma anotação dentro de predicado ou branch jamais dispararia |
| 2 | Escolha de ramo `oneOf` validava o nó resolvido isolado | os `$ref` internos deixavam de resolver contra o documento; toda recursão quebrada |
| 3 | `evidence` positivo projetava `GT-A-019`, que nenhum exemplo declarava | referência cruzada que o próprio contrato manda recusar |
| 4 | `evidence` positivo projetava `GT-B-003`, idem | idem |
| 5 | `scenario` positivo usava `OBJ-01`/`OBJ-08`, não declarados | idem |
| 6 | `scenario` positivo ramificava para `A08`/`A12`, injects que o exemplo irmão não declarava | branch apontando para inject inexistente — a própria falha que o contrato diz recusar |
| 7 | três fixtures negativas violavam **duas** regras, não uma | passariam mesmo se a regra que dizem provar fosse removida do executor |
| 8 | os exemplos dos seis contratos não formavam um pacote coerente | só aparece quando algo resolve as referências entre eles |

Os dois primeiros são meus, no executor, e são os mais graves: um verificador que morre em silêncio é pior que verificador ausente, porque produz verde.

#### P1-8 — Pinagem por digest: FECHADA

O cabeçalho do `docker-compose.yml` afirmava, citando `00` §8, que *"tags de imagem incluem o digest"*. **Não incluíam.** Tag pinada em patch é bem mais forte que `16`, mas continua mutável — a mesma tag pode ser republicada com outro conteúdo, e "pinado" em `00` §8 significa conteúdo imutável, não rótulo estável.

Pinado por decisão do operador:

```
postgres:16.4-alpine@sha256:5660c2cbfea50c7a9127d17dc4e48543eedd3d7a41a595a2dfa572471e37e64c
redis:7.4.1-alpine@sha256:c1e88455c85225310bbea54816e9c3f4b5295815e6dbf80c34d40afc6df28275
```

**Consequência de política, registrada porque foi aceita junto:** atualizar imagem passa a ser **mudança explícita de commit**. `docker compose pull` não traz versão nova sozinho; subir de patch exige editar o digest e isso aparece em diff e em revisão. É o que "pinado" quer dizer.

Verificado depois da pinagem: contêineres recriados, `--wait` retorna **Healthy** nos dois, e a integração continua respondendo (`select 1` → `1`, `PING` → `PONG`).

#### P1-9 — Alembic executável: FECHADA, confirmada por execução

Antes: `import alembic` resolvia para `C:\Projetos\aurora-cyber-range\alembic` — o diretório do próprio repositório, como namespace package — e `sqlalchemy` não importava. A biblioteca nunca esteve instalada.

Confirmado por execução, não presumido:

| Verificação | Antes | Depois |
|---|---|---|
| `import alembic` resolve para | o diretório do repo | `site-packages/alembic/__init__.py` |
| `import sqlalchemy` | `ModuleNotFoundError` | 2.0.52 |
| CLI executa | não | `python -m alembic.config --help` lista os subcomandos |
| Lê `alembic.ini` e lista `heads` | não | sim, vazio — correto, não há migration |

O job `contratos` do CI passou a exercitar isso, para não regredir em silêncio.

**`DeprecationWarning` corrigido.** O Alembic avisava `No path_separator found in configuration` e caía no split legado por espaço, vírgula e **dois-pontos** — que em caminho do Windows, onde `C:` tem dois-pontos, é exatamente o split indesejado. `alembic.ini` trocou `version_path_separator` pelo `path_separator = os`, que substitui aquele e vale também para `prepend_sys_path`.

Verificado com `python -W error::DeprecationWarning -m alembic.config heads`, que transforma o aviso em erro: sai `0`. Warning que fica é warning que ninguém lê depois.

---

#### P1-10 — `contratos` é o quarto context obrigatório: RESOLVIDA

`docs/process/WORKFLOW.md` passou a listar **quatro** required status checks — `arquitetura`, `spec_freeze`, `seguranca` e `contratos` — com a razão de cada um e a dependência de cada um.

**Ser job separado e ser context obrigatório são coisas independentes.** `contratos` é separado porque é o único que instala do `pyproject.toml`; exigi-lo na branch protection não faz `arquitetura` instalar nada. O isolamento do gate stdlib continua intacto **e** o executor de fixtures bloqueia merge.

**Ordem de aplicação:** o GitHub só aceita exigir um check que já apareceu em algum run, então a configuração é aplicada **depois do merge deste PR**. Não é pendência de decisão — é sequência.

##### O erro que esta pendência registrou antes de ser corrigida

A primeira redação declarava as duas restrições **incompatíveis** e escolhia preservar o isolamento do gate, aceitando um checker que não bloqueia. O raciocínio estava correto — mover o executor para dentro de `arquitetura` de fato obrigaria aquele job a instalar dependência, e isso de fato destruiria a propriedade — mas respondia a uma pergunta que ninguém tinha feito. Tornar `contratos` obrigatório **nunca exigiu** movê-lo para `arquitetura`.

**Raciocínio correto sobre a pergunta errada, e o custo teria sido concreto:** um gate que roda, reporta e não bloqueia — exatamente o buraco que o comentário do step `teste negativo dos seis verificadores` existe para descrever. Eu teria sacrificado a metade que importa (bloquear) para proteger uma metade que nunca esteve ameaçada (o isolamento), e teria registrado isso como restrição aceita — o que faz um defeito parar de ser procurado.

É uma variante das §1.2 e §1.3, e a mais difícil de pegar sozinho: ali a forma foi cumprida no lugar da propriedade; aqui uma propriedade real foi defendida contra um conflito inexistente. As duas produzem o mesmo resultado — mecanismo presente, garantia ausente — e esta ainda vem acompanhada de uma justificativa que parece rigor.

**Regra adotada:** antes de registrar duas restrições como incompatíveis, escrever qual pergunta cada uma responde. Se as perguntas forem diferentes, não há conflito a aceitar.

#### P1-12 — `simulation_epoch` tinha piso inventado contra critério normativo: FECHADA

O contrato declarava `simulation_epoch: minimum: 1`. **Invenção minha, e desta vez contra texto normativo explícito.**

`09_EVENT_MODEL.md` §3 desenha `epoch 0` antes do primeiro rollback e `epoch 1` depois dele. E `06_ACCEPTANCE_TESTS.md` T3 exige que *"evento de `participant_action` gravado na **epoch 0** continua legível após rollback, marcado com sua epoch"*.

**Consequência se tivesse passado:** o contrato recusaria todo evento da primeira linha temporal — inclusive o evento que o teste de aceitação T3 obriga a existir. Um contrato tornando insatisfazível um critério de aceitação da fase seguinte.

Pior: o exemplo negativo `'simulation_epoch zero: epoch comeca em 1'` era uma fixture **executável** afirmando como defeito aquilo que a spec exige como válido. A execução dos exemplos, que fechou o item 1 da DoD, não pega isso — o executor prova que a fixture é recusada pela camada que ela declara, não que a regra por trás dela esteja certa. **Fixture executável prova consistência interna, não fidelidade à spec.** Para isso serve o auditor.

Corrigido: `minimum: 0`, e a fixture passou a testar epoch **negativo**, que é o que de fato não existe.

Uma segunda invenção da mesma classe foi encontrada na varredura que este achado motivou: `max_paths_per_branch: minimum: 2`. `04` §2 exibe o valor `2` num exemplo e nunca declara piso; quem desliga ramificação já o faz por `max_branch_points_per_line: 0`. Relaxado para `1`.

##### Como apareceu

Pelo `checkpoint-auditor`, em contexto fresco, nos primeiros segundos da sessão — antes mesmo de eu ter conseguido rodá-la direito. O launch foi feito por engano dentro de um pipe em background, onde o modo interativo não funciona, e encerrado; a captura registrou `indeterminado` em vez de inventar veredito, e o fragmento preservado continha a observação. Verifiquei contra a spec antes de aceitá-la — o achado procede por `09` §3 e `06` T3, não por autoridade de quem o disse.

**É a defesa que as fixtures não dão.** Sete das oito coisas que a execução dos exemplos encontrou eram incoerências internas; esta é divergência da spec, e nenhum executor de fixture a encontraria, porque ele valida o contrato contra si mesmo. Ver `docs/progress/audit_20260814T223850Z.md`, anotado como launch abortado.

#### P1-13 — Achados da auditoria: duas rodadas, ambas FAIL

Duas auditorias formais rodaram, em contexto fresco e worktree preso ao commit candidato.

| Rodada | Commit | Veredito | Relatório |
|---|---|---|---|
| 1 | `59580e6` | FAIL — 2 BLOCKER, 1 HIGH, 1 MEDIUM, 1 LOW | `audit_20260814T224156Z.md` |
| 2 | `4a7b092` | FAIL — 2 BLOCKER, 3 HIGH, 4 MEDIUM, 3 LOW | `audit_20260814T230744Z.md` |

**A rodada 2 encontrou mais, não menos.** Motivo declarado no próprio relatório: na rodada 1 o auditor **não conseguiu executar nada** — toda tentativa foi recusada pela camada de permissão. Na rodada 2 ele executou os seis verificadores e o harness, e o que ganhou em execução gastou em profundidade de leitura. Três achados da rodada 1 reapareceram na 2 **porque eu não os corrigi nem os registrei entre as rodadas** — H1, M1 e L1. Isso é falha de processo minha: `docs/process/WORKFLOW.md:36` define o ciclo como *"corrigir BLOCKER/HIGH, criar novo commit e reauditar"*, e eu commitei o relatório sem tratar os findings.

##### Corrigidos neste commit

**B2 (rodada 2) — dependências não pinadas.** `pyproject.toml` usava `>=` em três pacotes, contra `00` §8 e `06` T15, **no mesmo commit** em que `docker-compose.yml` pinava imagens por digest e explicava por que tag mutável não é pinagem. A mesma regra aplicada de forma inconsistente a dois artefatos do mesmo commit. Agora: versões exatas, `referencing` declarado explicitamente (era importado direto e vinha por transitividade), e `constraints.txt` fixando o **fecho transitivo** — o CI instala com `-c constraints.txt`. O argumento não é formal: `referencing` é quem resolve os `$ref` entre os contratos, e uma versão nova dele mudaria o resultado do único gate do item 1 da DoD sem nada aparecer em diff.

**H1 (rodadas 1 e 2) — `correlation` ausente do envelope.** O envelope normativo de `09` §1 tem `correlation: {scenario_id, inject_id, causation_id, fact_id}`, e o contrato declarava só `fact_id`, **no topo**, com o comentário citando "09 seção 1" — a seção onde o campo está dentro de `correlation`. Li a seção errado. Corrigido: `correlation` fechado com os quatro campos, mais `object` e `payload`, que também faltavam. `inject_id` e `scenario_id` não levam `x-aurora-ref`: resolvem contra o pacote carregado em execução, não contra o mini-pacote de fixture, e amarrá-los ali seria inventar acoplamento.

**H2 (rodada 2) — evento sem `clock_multiplier` era válido.** `00` §5.6 é taxativo: *"Todo evento carrega `exercise_time` e `wall_timestamp`, mais `clock_multiplier`"*. A lista de `09` §1.1 o omite, e eu segui a lista. `CLAUDE.md` resolve sem escalação: em conflito, o MASTER_SPEC prevalece. É a mesma classe do P1-12 na direção oposta — lá o contrato recusava o que a spec exige, aqui aceitava o que ela proíbe.

**H3 (rodada 2) — o auditor não podia executar a prova central da fase.** O commit criou dois executores em `scripts/`, criou o job que os invoca e os declarou quarto required check, mas não estendeu a allowlist do `readonly_bash.py`. Resultado: o item 1 da DoD — o item que esta fase reabriu justamente por ter sido marcado ✅ por presença — voltava a repousar em relato do implementador. Corrigido por **nome explícito em alternação**, nunca curinga sob `scripts/`: curinga pré-autorizaria o auditor a executar qualquer script que um commit futuro acrescentasse, e o equivalente sob `.claude/hooks/` foi o H1 da sétima auditoria da Fase 0. As duas formas entraram em `LEITURA_LEGITIMA`, para que o bloqueio, se voltar, reprove o harness em vez de aparecer só no relatório do próximo auditor. **27 leituras legítimas**, contra 24.

**M1 (rodadas 1 e 2) — `check_event_envelope.py` só varria Python.** Os outros dois verificadores de código já cobriam `WEB_SUFFIXES`; este saía rc=0 sobre todo o front-end. Verificador que sai zero sobre território que não varre é a mesma classe do B1 da primeira auditoria da Fase 0. Corrigido com varredura lexical de `.ts/.tsx/.js`, deliberadamente conservadora — chave nua `{ objective_ids: [...] }` não é literal de string e escaparia de `iter_web_string_literals`. Com probe próprio: ramo de verificador sem violação plantada é o defeito que ele corrige.

**M2 (rodada 2) — duas cópias das faixas sintéticas, já divergentes.** `evidence.schema.yaml` afirmava que `tools/check_synthetic_data.py` consumia o registro. **Não consome** — o verificador tem constantes próprias, e as listas já tinham divergido: faltavam aqui `2001:db8::/32` (RFC 3849, citada nominalmente por `05` §3) e `example.net`. Afirmação corrigida e listas alinhadas. Unificar as duas fontes fica para a Fase 9, que é quem constrói o gerador.

**M4 (rodada 2) — `observability_hooks.yaml` sem nenhuma camada que o valide.** O arquivo carrega `event_type` e não era varrido por gate nenhum: os seis contratos não o cobrem e a varredura de código nunca alcança `.yaml`. Um `audit_query_perfomed` ali saía rc=0 em todos os gates — exatamente a falha que `09` §4 chama de *"a mais cara possível"*. O invariante 3 diz "nenhum `event_type` fora do catálogo" sem restringir a linguagem do arquivo, então a verificação entrou em `check_contract_literals.py`, com probe.

**L1 (rodadas 1 e 2) — `objective_ids` proibido só na raiz.** `payload` e `object` passaram a recusá-lo explicitamente, com fixture. Continua valendo o registro do auditor: quem de fato aplica o invariante é o AST, em qualquer profundidade.

**L2 (rodada 2) — constantes Python não tipadas.** A DoD pede constantes **tipadas** em Python e TypeScript; os artefatos TS usavam `export const` e `as const`, os de Python eram atribuição sem anotação. Agora `Final[str]` e `Final[tuple[str, ...]]`.

##### O buraco que os findings revelaram no meu próprio executor

Ao acrescentar `clock_multiplier` a `required`, **nenhuma das sete fixtures do envelope reprovou** — e todas deveriam ter reprovado, porque nenhuma o declarava. A causa: a regra de isolamento que eu exigia das fixtures `x-aurora` eu **não exigia das de schema**. Para `rejected_by: schema` eu aceitava qualquer recusa.

Consequência: uma fixture com dois defeitos é recusada e passa, provando qualquer um dos dois — ou **nenhum**, se o defeito que ela nomeia for removido do contrato. É a mesma classe que o executor existe para impedir, dentro do executor.

Corrigido com agrupamento por **sítio de defeito**: erros são agrupados por caminho de instância, e erros de `required` incluem a propriedade ausente — senão dois campos obrigatórios faltando no mesmo objeto contariam como um. Um defeito que produz vários erros (um `event_type` inválido falha no `anyOf` do campo e no `enum` da camada) continua contando como um sítio.

A regra reprovou quatro fixtures que estavam passando, e as quatro foram separadas em uma-por-defeito. **Sétimo eixo de probe** acrescentado, para a regra nova não ser mecanismo sem prova. Os exemplos negativos passaram de 53 para **59**.

##### Abertos, por decisão ou por escopo

**B1 das duas rodadas — item 8 da DoD.** Ver P1-2. O auditor registra que a marcação honesta e a recusa em escrever consumidor artificial estão corretas, e conclui que mesmo assim a fase não fecha: *"as saídas limpas são implementar o consumidor real ou mover o item por `spec-change`; nenhuma delas é 'auditor aceita'"*. Decisão do operador.

**M3 da rodada 2 — predicado de verificação satisfeito por declaração.** `verification_predicates.containment: {all: [{event: containment_declared}]}` valida em todas as camadas. O `x-aurora-ref` resolve contra o catálogo inteiro, que inclui os `*_declared` de `participant_action`, e é exatamente a declaração que o modelo das quatro verdades separa da verificação: TTCD e TTCV colapsariam no mesmo instante e o delta — que `03` §3.2 chama de "o achado" — deixaria de existir sem nada falhar.

O auditor registra com precisão o que **não** é o achado: `vpn_access_revoked` e `identity_scope_disabled` também são `participant_action` e são legítimos no exemplo normativo de `03` §3.1 — são **ações com efeito no mundo**, não afirmações sobre ele. A distinção que falta ao contrato é essa, e ela não existe no catálogo hoje. Fechá-la exige classificar os 32 tipos em ação-com-efeito e declaração, que é decisão de modelagem, não correção. **Aguarda decisão.**

**L3 da rodada 2 — `exercise_timestamp` opcional.** `01` §3 diz "três marcas temporais, nunca uma só"; `09` §1.1 não o lista entre os obrigatórios. **Os dois são documentos não-master**, e `CLAUDE.md` §"Autoridade" manda *parar e perguntar* nesse caso, não resolver por inferência. Diferente do H2, onde o MASTER_SPEC decidia. **Escalação aberta.**

**P25 herdada, reforçada.** O auditor observa que `actions/checkout@v4` e `actions/setup-python@v5` são a mesma classe do B2 e já estão declarados na P25.

#### P1-16 — Falha de processo: registrei a auditoria e segui sem tratá-la

**Entrada própria, e não nota dentro da correção, porque o defeito é do processo e não do artefato.**

Depois da rodada 1, eu commitei o relatório e segui. `docs/process/WORKFLOW.md:36` define o ciclo como **corrigir BLOCKER/HIGH, novo commit candidato, reauditar**. Registrar não é tratar.

Consequência medida: **três achados reapareceram na rodada 2** — H1 (`correlation` ausente), M1 (`check_event_envelope` sem TypeScript) e L1 (`objective_ids` só na raiz). O auditor gastou uma rodada reencontrando o que já estava escrito no próprio repositório, e o relatório da rodada 2 registra isso explicitamente: *"não foi nem corrigido nem registrado como pendência"*.

O agravante: o H1 era achado de **leitura da spec**, não de execução. Estava correto e completo no relatório da rodada 1, com arquivo e linha. Passei por cima dele duas vezes — uma ao escrever o contrato, outra ao ler o relatório que o apontava.

**Por que aconteceu.** Tratei o relatório como artefato a versionar em vez de trabalho a fazer. O commit `4a7b092` — *"fase-1: relatorio da primeira auditoria"* — é exatamente isso: preservou a evidência e não agiu sobre ela. É a mesma família das §1.2 e §1.3: cumprir a forma do mecanismo — a auditoria rodou, o relatório está versionado — e perder a propriedade que ele deveria garantir, que é o defeito deixar de existir.

**Regra adotada:** commit que registra relatório de auditoria não fecha o ciclo. O ciclo fecha quando cada BLOCKER e HIGH está corrigido ou explicitamente registrado como pendência aberta com decisão pendente. Findings MEDIUM e LOW não corrigidos entram em pendência nomeada — os três que reapareceram não estavam em lugar nenhum de §6.

#### P1-17 — Spec-change aplicado: `effect_class`, três marcas temporais e a migração do item 8

Branch `spec-change/effect-class-marcas-temporais-e-seed`, commit `96296e1`, **saindo de `main`** para que o diff contenha apenas `docs/spec/`. As três decisões foram apresentadas como diff antes de qualquer edição e aprovadas uma a uma.

**O que a spec passou a dizer:**

- `09` §4.0 — `effect_class` com quatro valores, ortogonal a `truth_layer`, e a regra derivada: a folha `event` de um predicado de verificação só pode referenciar `state_effect`.
- `09` §4.1 — os 32 tipos classificados, em tabela, com os seis casos de decisão registrados no próprio documento.
- `09` §1.1 — `exercise_timestamp` e `clock_multiplier` entram nos obrigatórios.
- `03` §3.1 — a restrição do predicado, com o custo de não tê-la.
- `07` — item 8 sai da Fase 1 e entra na Fase 2 como *"lido de `.env` por código do `range-core`, não por atestação"*.

**O que este commit de código implementa:**

- `x-aurora-registry.effect_class` nos 32 tipos de `events.schema.yaml`, com os comentários de decisão junto dos casos ambíguos;
- `x-aurora-ref: event_catalog_state_effect` na folha `event` do predicado, e **apenas** nela — o branching mantém acesso ao catálogo inteiro, porque ramificar sobre o que a equipe **declarou** é desenho legítimo de cenário; o que não pode é **verificar** contra declaração;
- `exercise_timestamp` obrigatório, propagado às 11 instâncias de envelope;
- fixture negativa `containment: {all: [{event: containment_declared}]}` — o achado da rodada 2, agora recusado por regra e provado por fixture.

**`decision_made` foi corrigido na revisão do PR de spec-change**, de `state_effect` para `declaration`. Meu argumento era que a opção carrega `effects` que mutam flags — mas quem muta o estado são os `effects`, não o evento. `decision_made` registra que a equipe **escolheu**, e escolher é afirmação, do mesmo tipo que `containment_declared`. Classifiquei pelo que a escolha *causa* em vez de pelo que o evento *é*, que é exatamente a confusão que `effect_class` existe para desfazer.

O teste que decidiu: como `state_effect`, `containment: {all: [{event: decision_made}]}` seria satisfeito **no instante do clique, antes de qualquer efeito existir** — o buraco da P1-14 sobrevivendo dentro do campo criado para fechá-lo. A refutação já estava na minha própria nota, que dizia que o uso real em branching passa pelas folhas `decision` e `option`: se passa, nada dependia de ela ser `state_effect`. Escrevi o contra-argumento ao lado da classificação e não o apliquei.

Fixture própria acrescentada, e não é redundante com a de `containment_declared`: ela fixa **esta** classificação. Reclassificar `decision_made` no futuro deixaria a outra passando e nada acusaria. Distribuição final: 12 `declaration`, 9 `machine`, 7 `state_effect`, 4 `observation`.

**Cobertura de `effect_class` é verificada, não presumida.** A tabela é uma **segunda lista** dos mesmos 32 tipos, e segunda lista é o que diverge em silêncio — foi assim que `must_exist_in_event_catalog` ganhou dois nomes na D4. O executor exige cobertura exata nos três sentidos: todo tipo do catálogo classificado, nenhuma classe órfã, nenhum valor fora do conjunto declarado. **Dois eixos novos de probe** provam que ele reprova nos dois primeiros. Eixos: 9. Exemplos negativos: 60.

#### P1-19 — Terceira auditoria: o achado foi sobre o meu mecanismo, não sobre um campo

FAIL, e o relatório está em `docs/progress/audit_20260815T012753Z.md`. Foi a primeira rodada em que o auditor **executou** a prova central da fase — o H3 anterior fechou a allowlist.

**O achado central não é finding nenhum. É a seção "TESTES QUE NÃO PROVAM O REQUISITO":**

> A suíte encontrou **zero** dos cinco defeitos de fidelidade.

B1, B2, B3, M1 e M2 saíram todos da leitura dos contratos contra a spec, campo a campo. `check_contract_examples.py` valida cada contrato contra fixtures que vivem **dentro do próprio contrato**, escritas pelo mesmo autor no mesmo commit — laço fechado, que prova consistência interna e não tem como provar fidelidade. E os nove eixos de probe **todos pressupunham que a fixture certa existe**: fechavam o eixo *"o executor enxerga?"* e deixavam aberto o eixo *"o autor olhou?"*.

##### Os quatro BLOCKERs, e a causa única

Não li a spec errado nesses campos: **não li a spec nesses campos.** Montei o inventário a partir do meu próprio contrato anterior, e a reescrita da D4 foi tradução fiel da fonte errada.

| | O que estava errado | De onde veio |
|---|---|---|
| **B1** `evidence_release` | `array of string`; a spec traz `{source, window}` em **dois** documentos | O contrato antigo o listava só como NOME em `optional_fields`, sem forma. Inventei uma sem abrir a spec |
| **B2** `reveals` | objeto único; a spec traz sequência | O erro **já estava** no contrato antigo. A reescrita o traduziu com fidelidade em vez de encontrá-lo |
| **B3** `note_to_facilitator` | ausente do braço de branch | Omissão herdada — mas **inócua** antes, porque nada fechava o vocabulário |
| **B4** `inject_id` | `^[A-Z]+[0-9]+$` recusa `A09B`/`A09C` do exemplo normativo | Padrão inventado por mim, mesma família da D6 |

**B4 não é da auditoria: saiu da releitura campo a campo que o operador mandou fazer antes de corrigir**, exatamente porque três lacunas da mesma causa sugeriam uma quarta. A varredura completa dos quatro blocos (`04` §5, `04` §6, `08` §2, `08` §5) achou essa e mais nenhuma — `04` §7 e `08` §2 batem campo a campo.

**Um agravante estrutural que vale isolar:** `additionalProperties: false` é decisão certa e **amplifica** esse defeito. Fechar um vocabulário transcrito incompletamente converte cada lacuna de transcrição em regra que quebra pacote. Foi o que aconteceu no B3: a omissão era inofensiva no contrato permissivo e virou recusa de pack legítimo no contrato fechado.

##### Correções, cada uma com exemplo positivo usando o **valor literal** da spec

Por exigência do operador, e a razão é boa: *"se a fixture é `A09B` e o padrão aceitar `A09B`, a correção está provada contra a fonte"* — não contra a minha leitura dela, que é o que falhou nos quatro.

`evidence_release`, `reveals`, o par `A09B`/`A09C` e o `note_to_facilitator` foram transcritos tal e qual de `04` §5 e §6. O exemplo de branches é agora transcrição literal do bloco normativo inteiro, id por id.

##### H1 — o único artefato real da fase não era validado

`01` §5.2 diz, literalmente, *"`domains/<adapter>/flags.yaml`, **validado contra** `contracts/state_flags.schema.yaml`"*. Ninguém o validava: o executor abria o arquivo só para colher nomes e tipos. Um `category: disponibilidade` ali sairia rc=0 nos quatro jobs — e o arquivo é entrada do `codegen` e da checagem de `effects`.

Fechado, com **dois eixos novos de probe** que plantam `flags.yaml` inválido e restauram. Instâncias reais validadas passam a aparecer na saída.

##### O buraco que apareceu de novo dentro do meu executor

Ao corrigir o B4, as fixtures continuaram apontando `next: A09`, que **deixou de existir** no mini-pacote — e passaram. Minha regra de isolamento agrupava por **nome de regra**, então duas violações da mesma regra passavam: a fixture nomeava um defeito e carregava dois, e seguiria sendo recusada se o defeito nomeado fosse corrigido.

Corrigido para exigir **uma violação**, não uma regra violada — o mesmo critério que o lado do schema já usava com o sítio de defeito. Eixo de probe próprio.

É a terceira vez nesta fase que a regra de isolamento encontra um defeito no ato de ser endurecida. O padrão vale registrar: **toda vez que exijo mais do mecanismo, ele acha o que passava.**

##### Os MEDIUM e LOW

**M1** — `package_files.required` exigia `ground_truth.yaml`, `objectives.yaml` e `injects.yaml`, o que recusaria os dois pacotes "apenas manifesto" que `04` §9 manda entregar. Separado em `required` e `required_for_complete_pack`.

**M2** — `calibracao` saiu do enum: identificador em português contra `00` §8, derivado de prosa de coluna. A ambiguidade maior — a tabela de `03` §1.3 pedir par e delta de um campo escalar — era **contradição interna ao `03`** e foi resolvida por spec-change, não aqui.

**M3** — `pack_decision_options` era registro estruturalmente vazio: nenhum inject de exemplo tinha `decision_point`, então a folha `option` do branching não podia disparar contra nada. Regra que passava por ser inalcançável. Exemplo acrescentado com os ids literais de `04` §5.

**L1** — varredura léxica de TypeScript: desvio literal de `01` §2 em **dois** verificadores, um deles desde a Fase 0. Resolvido por spec-change delimitando a exceção, não por silêncio.

**L2** — documentação contradizendo a execução: o README dizia "seis eixos" com nove no código, e o `fase_1.md` dizia 60 num lugar e 61 em outro. **As contagens saíram da prosa** e ficam na saída dos scripts — número em prosa envelhece sozinho, e envelheceu.

**L3** — `window` passou a ser obrigatória em **toda** fonte, e não só em `released_by_inject`: `08` §7 a lista por arquivo. O condicional que a exigia só naquele modo virou no-op e foi removido — regra que não pode falhar é ruído que se confunde com garantia.


### Abertas

#### P1-2 — `RANDOM_SEED` declarado, não consumido

`.env.example` o declara. **Nenhum código o lê**, porque nesta fase não há código que precise dele — o seed alimenta geração de dados (Fase 5) e projeção de evidência (Fase 9).

Marcar ✅ agora seria marcar item de DoD sem evidência executável. Fica ⚠️ até existir consumidor, e o teste real é `00` §8: mesmo seed, dataset byte-idêntico em duas execuções.

#### P1-3 — `evidence.schema.yaml` valida um artefato que ainda não é produzido

Ele valida o `MANIFEST.json` de `08` §7, e `range-cli evidence build` chega na Fase 9. O contrato existe porque a DoD da Fase 1 o exige; a validação real só será exercitada lá.

#### P1-4 — `observability_hooks.yaml` tem dois hooks, não o conjunto

Os dois de `09` §6, que são exemplo normativo. Os demais chegam com a API na Fase 3 — declarar hook para rota inexistente seria contrato sem implementação.

#### P1-7 — O id do inject pode vazar a linha, e isso aponta para a Fase 3

O padrão antigo `^[A-Z][0-9]{2}$` sugeria — pelo exemplo `id: A07` / `linha: A` de `04` §5 — que a letra acompanha a linha. Duas consequências:

1. `ransomware-universidade` tem Linhas A + B + **ruído** (`04` §9), e `ruido` não é uma letra: o inject de ruído não teria id possível;
2. se a letra codifica a linha, **o id vaza a linha**. `03` §5.2 exige que o operador não enxergue que existe Linha B, sob pena de destruir o efeito de triagem sob viés — e o operador vê a fila.

O contrato agora declara o prefixo **sem semântica de linha**. O que ele não resolve é o payload: **se a API da Fase 3 entregar o id do inject ao operador, e os packs continuarem nomeando por linha por hábito, o vazamento volta pela porta dos dados.** Fica apontado para a Fase 3, onde o payload por persona é decidido.

#### P1-14 — Predicado de verificação pode ser satisfeito por declaração

`verification_predicates.containment: {all: [{event: containment_declared}]}` valida em todas as camadas: o `x-aurora-ref` resolve contra o catálogo inteiro, que inclui os `*_declared` de `participant_action`.

TTCD e TTCV colapsariam no mesmo instante, e o delta — que `03` §3.2 chama de "o achado" — deixaria de existir sem nada falhar. É a confusão entre camadas 3 e 4 que `00` §3 existe para impedir, passando pelo contrato que deveria guardá-la.

**Não é "proibir `participant_action` no predicado".** `vpn_access_revoked` e `identity_scope_disabled` são dessa camada e são legítimos no exemplo normativo de `03` §3.1: são **ações com efeito no mundo simulado**, não afirmações sobre ele. A distinção que falta é essa, e ela não existe no catálogo — fechá-la exige classificar os 32 tipos. Decisão de modelagem. Ver P1-13.

#### P1-15 — `exercise_timestamp`: conflito entre dois documentos não-master

`01` §3 diz "três marcas temporais, nunca uma só" e lista `exercise_timestamp`; `09` §1.1 não o inclui entre os campos obrigatórios. O contrato o declara opcional, seguindo `09`.

Os dois são não-master, e `CLAUDE.md` §"Autoridade" manda **parar e perguntar** nesse caso — não resolver por inferência. Diferente do H2, onde `00` §5.6 decidia por ser MASTER. **Escalação, não pendência de implementação.** Ver P1-13.

#### P1-18 — `contratos` como required check travou o merge do spec-change: impasse circular

**Não foi exceção ao gate. Foi impasse de configuração, e o gate nunca chegou a ser afrouxado no que importa.**

Para mergear o PR #12 — o spec-change — foi preciso **remover `contratos` dos required status checks**. A causa é circular:

- `contratos` é o job que executa os exemplos dos contratos, e ele **só existe na branch de código**, que ainda não mergeou;
- o PR #12 sai de `main`, onde o job não existe. Ele reporta três checks, nunca quatro;
- a branch protection exigia os quatro. O quarto ficava **esperado e ausente**, não falhando.

Consequência medida, com a saída literal do operador:

```
$ gh pr merge 12 --rebase --delete-branch
X ... the base branch policy prohibits the merge.

$ gh pr merge 12 --rebase --delete-branch --admin
GraphQL: Required status check "contratos" is expected. (mergePullRequest)
```

**Nem `--admin` passa**, e isso é o ponto: privilégio administrativo contorna check que *falha*, não check que *não existe*. Com `enforce_admins: true`, o PR ficaria bloqueado indefinidamente.

##### A regra que isso ensina

**Um status check só pode ser exigido depois de ter aparecido num run em `main`.** Antes disso, exigi-lo não fortalece nada — trava todo PR que não o produza, inclusive os que não têm como produzi-lo.

A P1-10 já dizia "aplicar depois do merge", mas dizia isso pela metade: registrava que o GitHub *não aceita* exigir um check inédito, e não registrava que exigir um check que existe **em outra branch** trava tudo. As duas metades são a mesma regra vista de lados opostos, e faltava a que custou o ciclo.

##### O que NÃO foi afrouxado

A remoção foi de **um** context, o único impossível de satisfazer naquele PR. `arquitetura`, `spec_freeze` e `seguranca` continuaram exigidos e passaram — inclusive o `spec_freeze`, que é justamente quem prova que aquele PR tocava `docs/spec/` sem tocar código. O gate que a Fase 0 construiu julgou o spec-change por inteiro.

##### Estado e ordem de reposição

`contratos` está **fora** dos required checks agora. Ele volta **depois do merge do PR de código**, que é o commit que leva o job para `main`. A partir daí todo PR contra `main` passa a produzi-lo, e a exigência passa a ser satisfazível — o que a P1-10 sempre quis dizer.

Enquanto não voltar, vale o que a P1-10 já registrava: o job roda e reporta, mas um PR com fixture quebrada pode ser mergeado com ele vermelho.

#### P1-20 — `information_distribution.yaml` é arquivo de pack sem contrato

`04` §1 o lista entre os arquivos do pacote e `03` §4 traz o bloco normativo, mas nenhum dos seis contratos o cobre — e `01` §2 fixa o conjunto em seis. Apareceu ao montar a lista de ignorados do verificador de exemplos da spec: é um bloco normativo que nenhum contrato reivindica.

Mesma classe do M4 da segunda auditoria (`observability_hooks.yaml`), e com a mesma consequência: um campo com erro de digitação ali sai rc=0 em todos os gates. Não bloqueia a Fase 1 — o arquivo não consta dos OUTPUTS —, e a assimetria de informação que ele governa chega na Fase 10.

Fica registrado com o motivo escrito na própria lista de ignorados, para não virar omissão silenciosa.

#### P1-11 — Nenhum driver de banco nem cliente Redis declarado

O `docker compose` sobe e responde, e a aplicação **ainda não consegue falar com nenhum dos dois**: `psycopg2` e `psycopg` não estão instalados, e nenhum cliente Redis está declarado. `alembic current`, que conecta de fato, não roda.

Não bloqueia a Fase 1 — a DoD pede Alembic *inicializado* e `docker compose up` *subindo os serviços*, e as duas coisas estão verificadas. Bloqueia a Fase 2, que projeta `simulation_state` em Redis, e a Fase 5, que escreve o modelo.

Não acrescentei ao `pyproject.toml` porque a aprovação do operador foi para três pacotes nomeados, e a escolha atravessa fases. Fica para a Fase 2, que é quem consome — e não é escolha isolada de pacote:

**`psycopg` 3 e `psycopg2` têm implicações diferentes para async, e a decisão deve ser tomada junto com a de sync vs async do `range-core`.** `psycopg2` é síncrono e só; com SQLAlchemy async exige `asyncpg` ou equivalente ao lado. `psycopg` 3 tem as duas faces no mesmo pacote, e um único driver serve os dois modos. Escolher o driver antes de decidir o modelo de concorrência do core é decidir o segundo por acidente do primeiro — e `04` §4 proíbe alterar semântica dentro da mesma `schema_version`, o que torna caro descobrir isso depois.

O mesmo vale para o cliente Redis: `redis-py` cobre sync e async, mas a escolha só faz sentido depois que o core declarar qual dos dois ele é.

### Herdadas da Fase 0, ainda abertas

**P25** — actions do CI em tag major mutável, adiada por decisão do operador para esta fase. **P36 M1** — a contagem de pendências do `fase_0.md` não fecha. **P37** — `docs/process/` fora do conjunto `CODE` do `spec_freeze`; a decisão registrada foi resolver *depois do início da Fase 1*, que é agora. **Item 4 da DoD da Fase 0** — o eixo de leitura ainda é lista, não propriedade.

---

## 7. Próxima fase

**Fase 2 — Clock, eventos, estado, engine mínimo.** ENTRY exige Fase 1 completa. Falta **P1-2** (item 8 da DoD), que fica aberta por decisão registrada em §5.

Uma ação de operador fica pendente fora do repositório, e não é decisão: acrescentar `contratos` aos required status checks, **depois do merge deste PR** — o GitHub só aceita exigir check que já apareceu em algum run (P1-10).

O que a Fase 2 herda daqui: o envelope com `truth_layer` de cinco valores, o catálogo fechado de 32 tipos, as 12 flags com tipo e domínio declarados, a taxonomia de motivo de rollback — que a Fase 2 vai usar para congelar o relógio de métricas em `technical_failure` — e os seis contratos em JSON Schema, com o conjunto `x-aurora-*` que o **loader de pack da Fase 2 é quem passa a executar** sobre packs reais, e não só sobre os exemplos.

Três coisas nascem lá, e estão registradas aqui para não se perderem: o `config.py` que lê `RANDOM_SEED` (P1-2), o driver de banco e o cliente Redis (P1-11), e o payload por persona que decide se o id do inject chega ao operador (P1-7).
