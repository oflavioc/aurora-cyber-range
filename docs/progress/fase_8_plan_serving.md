# Plano — fase-8: dois gaps de integração ("web completo" servível)

> Fase 2/3 (SDD) · dono: tech-lead · **desenho, não implementação; não toca
> `docs/spec/` nem `contracts/`.** Complementa `fase_8_plan.md` (os 4 itens de
> DoD, T801–T821). Aqui: os DOIS gaps de integração que faltam para as telas da
> Wave 5 serem *servíveis* e para a continuidade funcionar no app real.
> Numeração continua de T821 → **T822+** (ids permanentes, R3/R9).

## Por que estes dois gaps existem

As Waves 1–6 de `fase_8_plan.md` entregam **payload + tela**, mas param antes da
**integração de deploy**:

- As 3 telas novas (`exam-mode`, `investigation-console`, `persona-panel`)
  existem em `range-core/web/` e passam nos gates web, mas **nenhuma rota as
  serve** — só `/sala`, `/plateia`, `/console` (as 3 antigas) são servidas por
  `range-core/api/app.py`.
- `range_core.participant.api.app.montar(..., acoes_de_continuidade=None)` é
  chamado **só por teste** (`tests/test_continuidade.py`,
  `test_participant_emissao_pela_rota.py`, `test_reported_isolation.py`).
  **Nenhuma raiz de composição de produção** injeta `CONTINUIDADE` + emissor
  real, e **não há serviço `participant-api` no `docker-compose.yml`**.

---

## GAP 1 — servir as 3 telas novas

### Fatos de fronteira (lidos, não supostos)

- `range-core/api/app.py:403-464` serve as 3 telas antigas por `_tela(nome)` +
  `diretorio_das_telas()` (resolve `range_core/web/dist/` pelo `__path__`) + 503
  alto quando o bundle falta. **Todos os 6 bundles moram em
  `range-core/web/dist/`** (um `dist/<nome>/index.html` por tela), servidos por
  `vite-plugin-singlefile` — não há rota de asset estático.
- `05` §8: só `wallboard`/`participant-view` são projeções **sem auth**; a
  **casca** do gm-console e as rotas troca-credencial→token são as exceções;
  o resto exige token. A casca de um console de browser é **necessariamente
  pública** (navegação não envia `Authorization`) — o que ela serve é HTML/CSS/JS
  sem dado de exercício; as rotas que ela CHAMA é que exigem token
  (`app.py:451-464`, `test_telas.py::pagina_do_console`).
- As 3 telas novas são **autenticadas** (não são as 2 projeções §8):
  - `persona-panel` → `participant-api` (core, token de persona, D1).
  - `exam-mode`, `investigation-console` → `academus-api` (papéis academus).
- `academus-api` autentica por **dependência global** `autoriza`
  (`domains/academus/api/auth.py:141`), que lê `declarada.publica` da superfície;
  rota servida e não-declarada → 403. `participant-api` autentica
  **por handler** (`_persona_autorizada`), então rota sem chamada a ele é pública.

### Decisão de topologia: **co-locar cada casca com a SUA data-API** (menor superfície)

Cada casca é servida pelo **mesmo serviço cuja data ela consome** — que é o
desenho que as 3 telas atuais já seguem (casca e `/…/state` no mesmo `range-api`,
mesma origem):

| Tela nova | Servida por | Rota (pública, casca) | Data-API que ela chama (com token) |
|---|---|---|---|
| `persona-panel` | **participant-api** | `GET /persona` | `/participant/view`, `/participant/continuity`, `/participant/session` |
| `exam-mode` | **academus-api** | `GET /exame` | rotas academus (papel) |
| `investigation-console` | **academus-api** | `GET /investigacao` | `GET /audit/grade-changes` + filtros |

`range-api` fica **inalterado** (`/sala`, `/plateia`, `/console`).

**Por que co-locar, e não "`range-api` serve tudo".** Se o `range-api` (`:8000`)
servisse `exam-mode`, a casca chamaria `academus-api` (`:8001`) —
**cross-origin**, exigindo middleware **CORS**, que é superfície nova
sensível a `05` §8 (fail-closed). Co-locar mantém **mesma origem** e **reusa o
helper de serving que já existe** — nenhuma linha de CORS. É a opção de **menor
superfície nova coerente com §8**.

**O bundle mora em `range-core/web/dist/` e todos os serviços o alcançam:**
`diretorio_das_telas()` resolve pelo `range_core.__path__`, então qualquer
processo que importe `range_core` acha o `dist/`. `academus-api` importar um
helper de `range_core` é a **direção esperada** (domínio→core; INV-4 só proíbe
core→domínio — o próprio `processo.py:45-70` já importa `range_core` fartamente).

### Helper único de serving (R9 §8: uma semântica, um dono)

A semântica "servir a casca ou **503 alto** com o comando de build" não pode
existir em três cópias. **Extrair** `diretorio_das_telas()`, `servir_tela(nome)
-> HTMLResponse`, `COMO_CONSTRUIR` e as constantes de nome de tela para um módulo
core dedicado — proposta: **`range_core/web_shell.py`** (top-level em
`range_core`, sem app FastAPI no import, sem rota; fora do escopo do scanner de
`api/` do `check_api_surface.py`). As 3 rotas atuais do `range-api` passam a
**delegar** a ele (refactor preservando comportamento; `test_telas::RotasDasTelas`
segue verde como regressão). `participant-api` e `academus-api` importam o mesmo
helper.

> **Módulo tocado que é PINADO + de fase fechada:** `range-core/api/app.py` e
> `range-core/participant/api/app.py` estão em `.claude/verify/pins.json` (Fase 4).
> Alterá-los exige **regenerar `pins.json` no mesmo PR** (R8, `gen_pins.py`,
> commit próprio). `boundary.json → frozen` está **vazio** hoje (a superfície
> congelada é `docs/spec/`), então **não há rito de boundary** para eles — mas se
> o operador tiver aplicado freeze acumulativo a módulos de Fase 4 (R6 §4/§5),
> **PARAR** e pedir autorização antes da Wave de implementação. Verificar antes.

### Extensão de `test_telas` sem enfraquecer "pública não conhece console"

`PUBLICAS = (wallboard-shell, participant-view, src)` **não muda**: as 3 telas
novas são **autenticadas**, não são as 2 projeções §8 — logo **não entram** em
`PUBLICAS`, e a regra "as 2 projeções e o `src/` compartilhado nunca alcançam a
console de facilitação" (`VOCABULARIO_DO_CONSOLE`) fica intacta. O que se
**acrescenta** (só reforça a fronteira):

1. `RotasDasTelas` análogas para **academus-api** (`/exame`→exam-mode,
   `/investigacao`→investigation-console) e **participant-api**
   (`/persona`→persona-panel): mapeamento rota→tela + **503-recusa** — cada uma
   montada com o `montar`/factory do SEU serviço, não o do `range-api`.
2. **Casca pública / dados autenticados** (análogo ao `pagina_do_console`): a
   casca responde **200 sem token**, e **toda rota de dado que ela chama exige
   token** (401/403 sem token) — prova que a casca pública não põe dado na rede.
3. **Varredura FACILITATION-only** nas 3 telas novas: nenhuma pode conter
   `/injects/` nem `/exercise/` (os comandos do gm-console). Não se reusa
   `VOCABULARIO_DO_CONSOLE` inteiro porque as telas novas **legitimamente** usam
   `Authorization` (token próprio) e `persona-panel` usa `/participant/session` —
   o subconjunto de facilitação é o que nenhuma tela não-facilitadora pode ter.

---

## GAP 2 — raiz de composição de produção do `participant-api`

### O problema, exato

`montar(superficie, *, segredo, emissor=None, acoes_de_continuidade=None)`
(`range-core/participant/api/app.py:358`) só é chamado por teste. Em produção,
algo precisa chamá-lo injetando `acoes_de_continuidade =
domains.academus.continuidade.CONTINUIDADE` (`domains/academus/continuidade.py:57`,
as 7 ações) e um `Emissor(store=…)` real — **sem que `range-core/` importe
`domains/`** (INV-4).

### Decisão: a factory vive em **`domains/academus/api/participante_processo.py`**

O módulo que injeta `CONTINUIDADE` **importa `domains/`** → **não pode** morar em
`range-core/`. O padrão já existe e resolve isto: `domains/academus/api/processo.py`
é a factory do `academus-api` e **nomeia os dois lados** ("O ADAPTER IMPORTA O
CORE, E ESSA DIRECAO E A ESPERADA", `processo.py:30-34`). A raiz do
`participant-api`, por simetria, é uma **nova factory irmã** em
`domains/academus/api/`:

```
criar() -> FastAPI:
    dsn   = exige(VARIAVEL_DO_BANCO)            # reusa range_core.api.processo.exige
    store = PostgresEventStore(clock_do_store(provisorio), dsn)   # mesma dupla-construção
    superficie = yaml.safe_load(participant/api_surface.yaml)      # montar recebe dict
    return range_core.participant.api.app.montar(
        superficie,
        segredo=jwt_secret(),
        emissor=range_core.participant.api.emissor.Emissor(store=store),
        acoes_de_continuidade=domains.academus.continuidade.CONTINUIDADE,   # a ponte INV-4
    )
```

**Por que não um módulo top-level fora de core e de domínio.** Seria uma
segunda convenção para o mesmo fato que `processo.py` já resolve; a factory do
`academus-api` mora em `domains/academus/api/`, e a do `participant-api` desta
implantação injeta uma tabela **de academus** — é wiring **por adapter**. Uma
implantação `prontus` teria `domains/prontus/api/participante_processo.py` com a
tabela dela, e **nenhuma linha de core muda** (mesmo argumento de
`processo.py:26-29`). Mantém INV-4 e o padrão de injeção existente
(`personas_por_rota`, `Sessao`, `emissor` já entram por `montar`).

**Serviço no compose.** Adicionar `participant-api` ao `docker-compose.yml`
(mesma imagem; `uvicorn domains.academus.api.participante_processo:criar
--factory`; porta loopback nova, ex. `8002`; `DATABASE_URL`, `AURORA_JWT_SECRET`
e as credenciais de persona por ambiente; `depends_on` migrations/postgres).
É o **mesmo serviço** que serve `GET /persona` (GAP 1).

### Gate: provar que a raiz **liga a tabela**

`tests/test_participante_processo.py` (namespace Fase 8): `criar()` (com env e
store stubados) prova `app.state.sessao.acoes_de_continuidade` **é** `CONTINUIDADE`
(chaves == enum das 7), `emissor is not None`, e **recusa alta** na ausência de
env obrigatória; e — análogo a `GateDoBuild` — que o serviço `participant-api` do
compose aponta para `…participante_processo:criar`. INV-4 seguro: o módulo está
em `domains/`, não em core (`check_core_boundary.py` /
`check_core_contract_imports.py` continuam verdes).

---

## Contratos, registros, boundary

- **`docs/spec/`: NÃO tocado.** **`contracts/`: NÃO tocado** — nenhum
  `event_type` novo, nenhum `$def`, nenhum codegen. `continuity_action_taken` e a
  assinatura de `montar(acoes_de_continuidade=…)` já vêm da Fase 8 (T801/T814).
- **Superfícies (não são spec/contracts):** rotas de casca em
  `participant/api_surface.yaml` (`GET /persona`, pública, `efeito: nenhum`, sem
  `papeis`) e `academus/api_surface.yaml` (`GET /exame`, `GET /investigacao`,
  `publica: true`). Conferidas nas duas direções por `check_api_surface.py`.
- **Pins (R8):** `range-core/api/app.py` e `range-core/participant/api/app.py`
  estão pinados; se alterados, **regen `pins.json` no mesmo PR**, commit próprio
  com motivo. A nova factory e o `web_shell.py` são candidatos a pin.
- **Boundary:** classe mais alta tocada = **`registry`** (`pins.json` via
  `gen_pins.py`). `frozen`/`generated` **não** tocadas.

## Waves (continuam após a Wave 6 de `fase_8_plan.md`)

| Wave | Tarefas | Depende de |
|---|---|---|
| 7 | Refactor do helper + superfícies + gates RED (GAP 1 e GAP 2) | Wave 5/6 (telas e endpoints existem) |
| 8 | Implementação: rotas de casca + factory (um módulo por delegação, `[P]`) | Wave 7 (helper, superfície, gate no prompt) |
| 9 | Compose + pins + validação | Wave 8 |

---

# Tarefas

> Tipos (R3): `feature`/`fix` exigem RED provado e commitado; `refactor`/`chore`
> não. Um módulo por delegação; `[P]` = paralelizável (arquivos disjuntos).
> Papéis como em `fase_8_tasks.md`.

## Wave 7 — refactor + superfícies + gates (contrato/gate antes do consumidor)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate |
|---|---|---|---|---|---|---|
| T822 | 7 | core-engineer | refactor | | Extrair `diretorio_das_telas`, `servir_tela(nome)->HTMLResponse`, `COMO_CONSTRUIR` e as constantes de nome de tela para `range_core/web_shell.py`; `range-api` (`/sala`,`/plateia`,`/console`) passa a delegar (comportamento idêntico). Toca `range-core/api/app.py` (PINADO) → regen `pins.json` no mesmo PR | `test_telas::RotasDasTelas` verde (regressão); `codegen`/`baseline` |
| T823 | 7 | build-engineer | chore | [P] | Declarar rotas de casca: `GET /persona` em `participant/api_surface.yaml` (pública, sem `papeis`, `efeito: nenhum`); `GET /exame`, `GET /investigacao` em `academus/api_surface.yaml` (`publica: true`) | `check_api_surface.py` (duas direções) |
| T824 | 7 | qa-engineer | feature | [P] | Gate GAP 1 em `tests/test_telas.py`: `RotasDasTelas` para academus-api e participant-api (rota→tela + 503-recusa); casca pública 200 sem token **e** rota de dado que ela chama exige token; varredura FACILITATION-only (`/injects/`,`/exercise/` ausentes nas 3 telas novas). `PUBLICAS` inalterado. RED commitado | `test_telas` (namespace Fase 8) |
| T828 | 7 | qa-engineer | feature | [P] | Gate GAP 2 `tests/test_participante_processo.py`: `criar()` liga `acoes_de_continuidade == CONTINUIDADE` (chaves == enum das 7) e `emissor is not None`; recusa alta sem env; serviço `participant-api` do compose aponta a `participante_processo:criar`. RED commitado | `test_participante_processo` |

## Wave 8 — implementação (um módulo por delegação, `[P]` disjuntos)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate |
|---|---|---|---|---|---|---|
| T825 | 8 | core-engineer | feature | [P] | `participant-api`: `GET /persona` → `servir_tela("persona-panel")`, pública (sem `_persona_autorizada`). Toca `range-core/participant/api/app.py` (PINADO) → regen pins | T824 (parte participant) |
| T826 | 8 | data-engineer | feature | [P] | `academus-api`: `GET /exame`→exam-mode, `GET /investigacao`→investigation-console via `range_core.web_shell` (domínio→core, INV-4 ok); ligar na app/`montar` do academus; casca pública pela superfície | T824 (parte academus) |
| T829 | 8 | data-engineer | feature | [P] | `domains/academus/api/participante_processo.py`: `criar()->FastAPI` — store (dupla-construção de clock), carrega `participant/api_surface.yaml` como dict, `Emissor(store)`, injeta `CONTINUIDADE`, chama `range_core.participant.api.app.montar(...)`. Importa `domains/` (permitido; não é core) | T828 |

## Wave 9 — compose + pins + validação (a última é validação)

| Id | Wave | Dono | Tipo | [P] | Descrição | Gate |
|---|---|---|---|---|---|---|
| T830 | 9 | build-engineer | chore | | Serviço `participant-api` no `docker-compose.yml` (imagem, `uvicorn …participante_processo:criar --factory`, porta loopback, env, `depends_on`); serve `/persona` (GAP 1) | `test_participante_processo` (parte compose) |
| T827 | 9 | build-engineer | chore | | Regen `.claude/verify/pins.json` (`gen_pins.py`) para os pinados alterados (T822/T825) e novos candidatos (`web_shell.py`, factory); commit próprio, motivo; registrar suítes novas em `expected_suites.json` (R10 §3), nomear não-executado sem Postgres (R10 §2) | stage `baseline`, `suites` |
| T831 | 9 | qa-engineer | chore | | Green dos gates novos + mutante por gate + regressão intacta (`test_telas` antigo, `test_continuidade`, `test_reported_isolation`); `check_core_boundary`/`check_core_contract_imports` (INV-4), `check_banner_de_simulacao` (as 3 telas servidas), `check_api_surface` verdes | stages `suites`, `arquitetura`, `seguranca`, `baseline` |

## Notas de dependência

- Gate antes da implementação: T824→(T825,T826), T828→T829 (o gate viaja no
  prompt — R3 §3).
- Helper antes do consumidor: T822 antes de T825/T826.
- Superfície antes do consumidor: T823 antes de T825/T826.
- Factory antes do compose: T829 antes de T830.
- Pins e validação por último: T827/T831 depois de todo código.

## Decisões que pedem confirmação do proprietário (nenhuma toca `docs/spec`/`contracts`)

1. **Topologia de serving** — co-locar cada casca com a sua data-API (Opção B,
   recomendada, sem CORS) vs `range-api` serve tudo + CORS (Opção A). Arquitetura,
   não spec.
2. **Local da factory** — `domains/academus/api/participante_processo.py`
   (recomendado, casa com `processo.py`) vs módulo top-level de composição.
3. **Módulos PINADOS de Fase 4** (`range-core/api/app.py`,
   `range-core/participant/api/app.py`): hoje `boundary.json → frozen` está vazio,
   então basta regen de pins (R8). **Se** houver freeze acumulativo de Fase 4
   (R6 §4/§5), editar é rito de boundary → **PARAR** e pedir autorização antes
   da Wave 8. Verificar antes de implementar.
</content>
</invoke>
