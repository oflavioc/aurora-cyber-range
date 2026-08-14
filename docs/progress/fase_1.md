# Fase 1 — Contratos e esqueleto

Conforme `07_IMPLEMENTATION_PHASES.md` §229: resumo técnico, estrutura, endpoints, migrations, variáveis de ambiente, DoD item a item, pendências e próxima fase.

---

## 1. Resumo técnico

Os **seis contratos** de `contracts/`, o `flags.yaml` dos dois adapters, a geração de constantes tipadas para Python e TypeScript, a árvore de diretórios, `docker-compose` com Postgres e Redis, e Alembic inicializado.

**Nenhuma lógica de negócio, nenhuma tela, nenhum seed** — os NON-GOALS da fase.

### 1.1 Dois conflitos internos da spec, resolvidos antes de escrever contrato

Encontrados ao desenhar `events.schema.yaml`. Nenhum podia ser resolvido por inferência — `CLAUDE.md` proíbe, e o primeiro toca o MASTER_SPEC. Foram para `spec-change` próprio, sem código junto, mergeado antes desta implementação.

**`facilitation` não era um `truth_layer`.** `00` §3 e `09` §2 diziam "exatamente um destes valores" e listavam **quatro**; `09` §4.1 agrupava o catálogo em **cinco**. Qual seria o `truth_layer` de `inject_fired`, sendo o campo obrigatório em todo evento?

Resolvido como **cinco valores, quatro verdades**: as quatro camadas afirmam algo sobre o *incidente*, `facilitation` afirma algo sobre a *máquina de exercício*. Ortogonal ao modelo, não uma quinta camada dele.

**`separate_incident_declared` era usado e não existia no catálogo.** `03` §1.1 e `09` §6 o usam como evidência `auto` do OBJ-03. O catálogo é registro fechado com CI que falha em `event_type` não registrado — um `objectives.yaml` escrito conforme o **exemplo normativo do `03`** seria recusado pelo linter.

### 1.2 Sistema de tipos das flags — decisão da fase

`01` §5.2 exemplifica só `boolean`, mas o inject de `04` §5 atribui `academus.lms_session_drop_rate: 0.4`, e essa flag está em `required_flags` do manifesto.

Declarado: **`boolean | number | enum`**, com `enum` exigindo `values` e `number` aceitando `min`/`max`.

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
contracts/                       os seis schemas + generated/{events.py,events.ts}
alembic/                         env.py, script.py.mako, versions/
docker-compose.yml  .env.example  alembic.ini
```

`generated/` co-localizado com a fonte canônica **não é escolha desta fase** — `codegen.py` da Fase 0 já o fixa, e o motivo está registrado lá: artefato com nome de adapter dentro do core exigiria exceção no `check_core_boundary.py`, e invariante com exceção é invariante morto.

## 3. Endpoints, migrations e variáveis de ambiente

**Endpoints: nenhum.** A API chega na Fase 3.

**Migrations: nenhuma.** Alembic está **inicializado** — `env.py`, `script.py.mako`, `versions/` vazio — que é o que a DoD pede. `target_metadata` fica `None` de propósito: os modelos chegam na Fase 5, e apontar para metadata inexistente produziria autogenerate vazio que pareceria funcionar.

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

---

## 5. Definition of Done — status

| # | Item | Status |
|---|---|---|
| 1 | Os seis contratos existem e validam exemplos positivos e negativos | ✅ cada contrato traz `example_valid` e `examples_invalid` com o motivo nomeado |
| 2 | Constantes tipadas geradas em Python e TypeScript para flags e event types | ✅ 32 event types, 14 flags, seis artefatos |
| 3 | Teste de fronteira core/adapter passa (por AST) | ✅ e falha contra import plantado |
| 4 | `event_type` fora do catálogo é rejeitado | ✅ catálogo fechado; literal fora do gerador reprova |
| 5 | Os seis verificadores liberam árvore limpa e falham contra violação plantada | ✅ tabela §4 |
| 6 | `codegen.py --check` detecta dessincronia e não escreve | ✅ provado nos dois sentidos |
| 7 | `docker compose up` sobe Postgres e Redis | ⏳ **não verificado por execução** — ver §6 |
| 8 | `RANDOM_SEED` lido de `.env` | ⚠️ **parcial** — declarado em `.env.example`; nenhum código o lê ainda |

**A fase não está concluída.** Dois itens não passam, e `CLAUDE.md` diz que uma fase só está concluída quando **todos** passam.

---

## 6. Pendências

### P1-1 — `docker compose up` não foi executado

O compose está escrito com versões pinadas, bind em `127.0.0.1` e healthcheck nos dois serviços. **Não foi subido.** Não afirmo que sobe: é a mesma distinção entre declaração e evidência que a Fase 0 passou dezenove rodadas aprendendo.

Precisa de execução do operador, e a saída de `docker compose ps` entra aqui como evidência.

### P1-2 — `RANDOM_SEED` declarado, não consumido

`.env.example` o declara. **Nenhum código o lê**, porque nesta fase não há código que precise dele — o seed alimenta geração de dados (Fase 5) e projeção de evidência (Fase 9).

Marcar ✅ agora seria marcar item de DoD sem evidência executável. Fica ⚠️ até existir consumidor, e o teste real é `00` §8: mesmo seed, dataset byte-idêntico em duas execuções.

### P1-3 — `evidence.schema.yaml` valida um artefato que ainda não é produzido

Ele valida o `MANIFEST.json` de `08` §7, e `range-cli evidence build` chega na Fase 9. O contrato existe porque a DoD da Fase 1 o exige; a validação real só será exercitada lá.

### P1-4 — `observability_hooks.yaml` tem dois hooks, não o conjunto

Os dois de `09` §6, que são exemplo normativo. Os demais chegam com a API na Fase 3 — declarar hook para rota inexistente seria contrato sem implementação.

### Herdadas da Fase 0, ainda abertas

**P25** — actions do CI em tag major mutável, adiada por decisão do operador para esta fase. **P36 M1** — a contagem de pendências do `fase_0.md` não fecha. **P37** — `docs/process/` fora do conjunto `CODE` do `spec_freeze`; a decisão registrada foi resolver *depois do início da Fase 1*, que é agora. **Item 4 da DoD da Fase 0** — o eixo de leitura ainda é lista, não propriedade.

---

## 7. Próxima fase

**Fase 2 — Clock, eventos, estado, engine mínimo.** ENTRY exige Fase 1 completa, então **P1-1 e P1-2 precisam fechar antes**.

O que a Fase 2 herda daqui: o envelope com `truth_layer` de cinco valores, o catálogo fechado de 32 tipos, as 14 flags com tipo declarado, e a taxonomia de motivo de rollback — que a Fase 2 vai usar para congelar o relógio de métricas em `technical_failure`.
