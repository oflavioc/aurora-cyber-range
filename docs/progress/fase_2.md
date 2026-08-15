# Fase 2 — Clock, eventos, estado, engine mínimo

**Status: EM CURSO.** Checkpoint ⏸ submetido e decidido em 15/08/2026. Nenhum
código de fase escrito ainda.

---

## 0. Por que este registro começa antes da fase

`07` §233 manda gravar o registro **ao concluir** a fase. Este começou no
primeiro dia, e é deliberado.

O checkpoint ⏸ desta fase decidiu sete coisas que não têm artefato ainda:
duas escalações de spec, duas perguntas de arquitetura, três decisões de
modelagem, um resíduo e um invariante de verificação. Nenhuma delas está em
código, em contrato ou em teste — só na conversa que as produziu. Conversa não é
fonte versionada.

A §1.5 da Fase 1 diz: **ler a fonte, não lembrar dela.** Um checkpoint que só
existe em memória de sessão não tem fonte a ler. Este arquivo é a fonte.

Seções 2 a 4 estão reservadas e se preenchem conforme a fase produz. Uma seção
vazia aqui é honesta; uma decisão perdida não seria.

---

## 1. Checkpoint ⏸ — o que foi submetido e o que foi decidido

Submetido antes de qualquer código, conforme `CLAUDE.md` e a marca ⏸ de `07`.
Sete blocos. Todos decididos.

### 1.1 E1 — o NON-GOAL "métricas" contradiz um item da própria DoD

**Escalação, não decisão minha.** `07` Fase 2 diz:

- **NON-GOALS** — *"branching, objetivos, **métricas**, telemetria, UI"*
- **DoD item 7** — *"`reason: technical_failure` desconta o intervalo do
  **cálculo de métricas**"*

A fase declara métrica fora de escopo e exige, na checklist binária, que uma
métrica seja calculada com desconto de intervalo. Os dois não podem valer.

**Decisão: resolver do lado do NON-GOAL.** A Fase 2 **registra o intervalo a
descontar**; a Fase 6 **calcula**. É a leitura que preserva as duas fases:
`07` Fase 6 é a que entrega métricas pareadas, e antecipar cálculo para cá
duplicaria motor de métrica em duas fases — a classe que a D4 da Fase 1 desfez.

O `rollback_performed` de motivo `technical_failure` grava o intervalo congelado
no evento. Quem consome é a Fase 6.

**Vai por spec-change.** Não é interpretação: é reescrita do item 7 da DoD.

### 1.2 E2 — `wall_time` × `wall_timestamp`

**Escalação de digitação, verificada na fonte:**

| Fonte | Campo |
|---|---|
| `09` §1.1, linha 40 | `wall_timestamp` |
| `contracts/events.schema.yaml`, `required` | `wall_timestamp` |
| `07` Fase 2, DoD item 1 | **`wall_time`** |

O envelope não tem campo `wall_time`. O item da DoD, lido ao pé da letra, é
insatisfazível — a mesma forma da P1-18: checagem impossível por construção.

**Decisão: corrigir `07` para `wall_timestamp`.** Vai no mesmo spec-change de E1.

### 1.3 Sync × async no `range-core`

**Decisão: síncrono no núcleo.**

O núcleo é um fold determinista sobre um fluxo de eventos. Não há I/O
concorrente a esconder dentro dele, e `async` no fold contamina toda assinatura
de projeção com `await` sem comprar paralelismo real. A concorrência que existe
é de borda — HTTP, WebSocket — e vive nos adapters.

**Drivers: `psycopg[binary]` 3 e `redis-py`.** `psycopg` 3 traz as duas faces no
mesmo pacote, então a borda async da Fase 3 não exige um segundo driver ao lado
com um segundo dialeto de SQL. Foi por isso que a escolha não podia vir antes do
modelo de concorrência: `psycopg2` teria forçado `asyncpg` na Fase 3 e
`04` §4 proíbe mudar semântica dentro da mesma `schema_version`.

**Fecha a P1-11.**

### 1.4 Onde vive a execução das regras `x-aurora-*`

**Decisão: núcleo dono, script chamador.**

As regras viram módulo do `range-core`. `scripts/check_contract_examples.py`
deixa de ser implementação de referência e passa a **chamar** o módulo. O loader
de pack da Fase 2 chama o mesmo módulo.

Uma implementação, dois chamadores. Duas implementações da mesma regra é
exatamente a classe que a D4 da Fase 1 desfez, e aqui ela reapareceria com
roupa diferente: o verificador de CI divergindo do loader de produção, cada um
aceitando um pack que o outro recusa.

**Consequência de gate:** `check_contract_examples.py` deixa de ser stdlib pura
e passa a importar do núcleo. Ele já roda no job `contratos`, que tem
dependências de aplicação desde a P1-6 — os outros verificadores seguem stdlib.

### 1.5 D1 — as três marcas temporais são carimbadas na ingestão

**Decisão minha.** `exercise_time`, `exercise_timestamp`, `wall_timestamp` e
`clock_multiplier` são preenchidos pelo **event store, no append**, a partir do
`exercise-clock` — nunca pelo produtor do evento.

Produtor que carimba o próprio tempo produz fluxo não-monotônico: dois adapters
com relógios diferentes gravam eventos cuja ordem no store contradiz a ordem em
`exercise_time`, e o fold passa a depender de qual chegou primeiro. Como o
`clock_multiplier` e a pausa vivem no clock e não no produtor, um produtor que
carimbe durante uma pausa carimba um tempo que não existiu.

**Risco assumido:** evento cujo tempo de origem é anterior ao append — telemetria
com atraso — perde a distância. Fica declarado; se a Fase 9 precisar, o campo de
origem entra no `correlation`, não nas marcas do envelope.

### 1.6 D2 — o que a projeção reconstruída inclui (forma revisada)

**A decisão mais cara de errar da fase.** A primeira formulação estava errada, e
a revisão veio de três perguntas.

**Decisão, na forma final:**

> A projeção **`simulation_state`** reconstruída após rollback **exclui** os
> eventos da epoch abandonada posteriores ao ponto de corte, **inclusive
> `participant_action`**.
>
> As outras quatro projeções — `objective_evidence`, `metrics`, `calibration`,
> `aar_timeline` — **continuam a enxergar** esses eventos, cada uma tratando o
> abandono pelo motivo declarado em `09` §3.1.
>
> **A exclusão vive no fold de `simulation_state`, e em lugar nenhum mais.**
> Nunca no store, nunca numa consulta que as outras herdem.

**Conferido na fonte, não lembrado:** `01` §4.1 e `09` §5 mostram as cinco
projeções com `← ROLLBACK reconstrói esta` apontando **só** para
`simulation_state`. E `09` §3 traz literalmente o caso disputado:

```
epoch 0
  A01
  A02
  incident_declared          ← permanece no store
  A03
  rollback_performed → A02
```

**As três perguntas, e as respostas:**

**1. Ação de participante da epoch abandonada, posterior ao corte: entra na
projeção reconstruída?**
Não entra em `simulation_state`. Entra nas outras quatro.

**2. Se não entra, como isso não viola "nunca reversível"?**
Porque *"nunca reversível"* qualifica o **registro** e a **camada**, não a
projeção de estado de simulação. O evento permanece no store, legível e marcado
— é o item 6 da DoD desta fase — e permanece **ativo em quatro das cinco
projeções**. O que o rollback desfaz é o efeito sobre flags, que é Simulation
State, a única camada que `01` §4 declara reversível.

**3. Se entra, como o fold reconcilia uma ação que pressupõe estado que o
rollback desfez?**
Não se coloca para `simulation_state`, que é a única com estado mutável a
contradizer. As outras quatro são **acumulações** ordenadas por
`(epoch, exercise_time)`: não há o que reconciliar porque não há estado a
sobrescrever.

### 1.7 D3 — `effects` de inject é declarativo, e a idempotência vem disso

**Decisão minha.** `effects` declara **estado final de flag**, nunca delta.
Aplicar A01 duas vezes produz projeção idêntica porque a segunda aplicação
escreve o mesmo valor, não porque o engine detecta repetição e ignora.

Idempotência por guarda — *"já apliquei este inject, pulo"* — exige o engine
lembrar o que aplicou, e essa memória é estado fora do fold. Rollback teria de
reconstruí-la também, e ela seria a primeira coisa a divergir. Declarativo não
tem memória a reconstruir.

É item 4 da DoD desta fase e a razão de rollback ser possível.

### 1.8 O resíduo — `participant_action` com `effect_class: state_effect`

A D2 deixa um resíduo que **não é defeito e precisa ser norma**, não só nota de
registro.

Quando uma `participant_action` tem `effect_class: state_effect`, ela move flag.
Se o rollback a atravessa, **a flag reverte e o efeito de domínio não**.

O exemplo, com fontes conferidas: `vpn_access_revoked` é
`effect_class: state_effect` em `contracts/events.schema.yaml` e é produzido por
`federated-identity-simulator` em `POST /identity/revoke`
(`domains/academus/observability_hooks.yaml`). Um pack pode ligá-lo a
`academus.federated_session_active`. Um defensor revoga o acesso; o rollback
atravessa o evento; a flag volta a `true` em `simulation_state`, enquanto o
registro da revogação segue vivo nas outras quatro projeções e o que o domínio
escreveu — Business State, não reversível por `01` §4 — não volta.

**Consequência, dita: o participante pode ver o mundo contradizer a própria
ação. Isso é desenho, não defeito.** Rollback atua sobre estado de simulação; o
que o participante fez continua tendo acontecido.

É material de briefing de facilitador, **mas primeiro precisa ser norma** — vai
para `01` §4 no spec-change.

### 1.9 A regra da exclusão precisa de verificação, não só de disciplina

A D2 termina em *"a exclusão vive no fold e em lugar nenhum mais"*. Isso é
disciplina, e disciplina sozinha tem modo de falha silencioso com **três fases
de atraso**: quem escrever `metrics` na Fase 6 herda um caminho de leitura que
já perdeu eventos, e nada falha.

**A premissa original da verificação estava errada, e a correção importa.** Foi
pedida verificação de que *"nenhuma projeção além de `simulation_state` filtra
por epoch abandonada"*. Essa propriedade **não existe**:

- `09` §3.1 — `rehearsal` faz a epoch inteira **não entrar em cálculo**: `metrics`
  lê abandono.
- `09` §5 — `aar_timeline` renderiza *"epochs e anotação de rollback"*: lê abandono.
- `objective_evidence` e `calibration` alimentam escore, e escore é cálculo.

Quatro das cinco leem abandono **legitimamente**, cada uma pelo motivo declarado.

**O invariante correto:**

> **O store devolve todo evento, sempre. A exclusão vive no fold, nunca no
> caminho de leitura compartilhado.**

Assim cada projeção decide sozinha o que fazer com a epoch abandonada, e nenhuma
herda perda que não escolheu.

**As quatro camadas, todas aprovadas:**

| | Camada | Quando |
|---|---|---|
| **(a)** | **Linha normativa em `01` §4.1** — `read_all` é total; nenhum caminho de leitura compartilhado filtra por epoch, abandono ou ponto de corte | **spec-change, agora** |
| **(b)** | **Teste de propriedade** sobre store + fold | **dentro da Fase 2** |
| **(c)** | **AST sobre a superfície de leitura do store** | **Fase 2, depois de a API existir** — P2-2 |
| **(d)** | **Propriedade entre projeções** | **Fase 6** — P2-1 |

**(b), a camada principal.** Um teste afirma as duas metades ao mesmo tempo:

> Dado um fluxo com N eventos e R rollbacks, com `participant_action` depois de
> cada corte:
> `len(read_all()) == N + R` **e** `simulation_state(read_all())` difere do
> estado sem rollback.

A primeira metade prova que **nada se perdeu**; a segunda, que **a exclusão
aconteceu**. Rollback escondendo no store reprova a primeira; rollback marcando
sem excluir reprova a segunda. Não há como passar nas duas com a implementação
errada.

**Acima das quatro, e é o item mais valioso: a assinatura.** Projeção recebe o
fluxo — `project(events: Iterable[Event]) -> State` — e **não consulta o store**.
A implementação ruim deixa de ser detectável e passa a ser **inexprimível**, o
que é sempre superior a teste. Custa zero agora porque nada existe ainda.

**(c) foi adiado por motivo, não por preguiça.** Escrever a lista de parâmetros
proibidos antes de a API existir é inventar vocabulário para prever o módulo —
a classe da D6, já paga nesta fase com o `simulation_epoch: minimum: 1`.

### 1.10 A classe nova: tratar um conjunto de cinco como se fosse um

Duas formulações erradas apareceram neste checkpoint, com autores diferentes, e
são **uma instância só da mesma classe**:

| Formulação | Erro |
|---|---|
| *"a ação não entra **na projeção**"* | Singular. Existem cinco; a ação não entra em **uma** |
| *"a ação vira **arquivo morto**"* | Subestima. Ela segue **ativa em quatro das cinco** |

A classe: **o artigo definido no singular apagou a cardinalidade.** Nenhuma das
duas frases é falsa sobre `simulation_state` — as duas são falsas sobre o
conjunto, e nenhuma revisão de redação pega isso, porque a frase lê bem.

É parenta da §1.5 da Fase 1 — *"li outra coisa, e nunca errado"* — com uma
diferença: ali o defeito era ler a fonte errada; aqui a fonte estava certa e a
**cardinalidade** se perdeu na travessia para a prosa.

**A regra que ela ensina: afirmação sobre projeção nomeia qual, ou diz "as
cinco".** Nunca "a projeção".

Se a segunda formulação tivesse passado, o teste de (b) teria sido escrito para
provar que a ação some — e teria travado a Fase 6 por três fases, verde.

---

## 2. O que a Fase 2 herda

Inventário completo em `fase_1.md` §7. O que muda de estado aqui:

| | Estado na entrada | Efeito do checkpoint |
|---|---|---|
| P1-11 (sem driver de banco nem cliente Redis) | Aberta | **Fechada pela §1.3** — `psycopg[binary]` 3 e `redis-py` |
| P1-2 (`RANDOM_SEED` sem consumidor) | Aberta | Item 2 da DoD desta fase |
| P25 (actions em tag major mutável) | **Vencida na Fase 1** | Continua vencida |
| P37 (`docs/process/` fora do `CODE` do `spec_freeze`) | **Vencida na Fase 1** | Prazo declarado: **antes da Fase 3** |
| P23, P36 | Limites declarados | Sem mudança |

Os quatro limites declarados de `fase_1.md` §7.4 continuam limites, não
pendências — em especial: `check_contract_examples.py` é laço fechado, e
`tools/_common.py::parse_yaml` nunca foi comparado com parser conforme.

---

## 3. Estrutura, migrations e variáveis de ambiente

*Reservado.* Preenche conforme a fase produz.

---

## 4. Itens da Definition of Done

Da `07` Fase 2, com as correções de E1 e E2 aplicadas **se e quando o
spec-change entrar**. Nenhum item iniciado.

| | Item | Status |
|---|---|---|
| 1 | Três marcas temporais e `clock_multiplier` em todo evento | ⬜ |
| 2 | `RANDOM_SEED` lido por código do `range-core` | ⬜ |
| 3 | PAUSAR congela o clock e bloqueia disparo agendado | ⬜ |
| 4 | Aplicar A01 duas vezes produz projeção idêntica | ⬜ |
| 5 | Rollback grava evento, incrementa epoch, reconstrói sem apagar | ⬜ |
| 6 | `participant_action` da epoch anterior legível e marcada | ⬜ |
| 7 | `technical_failure` **registra** o intervalo a descontar (E1) | ⬜ |
| 8 | Reconstrução completa da projeção em < 3 s | ⬜ |
| 9 | Flag não declarada impede boot com mensagem clara | ⬜ |

---

## 5. Pendências

| Id | O que é | Vencimento |
|---|---|---|
| P2-1 | Propriedade entre projeções: abandono lido só pelo motivo declarado | **Fase 6** |
| P2-2 | AST sobre a superfície de leitura do store | **Fase 2**, após a API existir |
| P2-3 | E1, E2, o resíduo e a linha normativa pendentes de merge | Antes de qualquer código desta fase |

#### P2-1 — propriedade entre projeções

**O que falta.** Verificar que `metrics`, `objective_evidence`, `calibration` e
`aar_timeline` leem epoch abandonada **apenas pelo motivo declarado** em
`09` §3.1, e não por herança do caminho de leitura.

**Por que não agora.** A propriedade é *entre* projeções e hoje existem zero. A
Fase 2 cria a primeira. O teste só é escrevível quando existir a segunda.

**Vencimento: Fase 6**, quando `metrics` e `objective_evidence` nascem.

**O que segura até lá:** as camadas (a) e (b) da §1.9, mais a assinatura que
impede a projeção de consultar o store.

#### P2-2 — AST sobre a superfície de leitura do store

**O que falta.** Verificar que as funções públicas de leitura do event store não
aceitam parâmetro de filtragem por epoch, abandono ou ponto de corte.

**Por que não agora.** Escrever a lista antes de a API existir é enumerar
vocabulário para prever o módulo — classe da D6, já paga nesta fase.

**Vencimento: dentro da Fase 2**, depois que a API existir, para a enumeração
descrever o que há em vez de adivinhar. Vantagem sobre AST em consumidores: a
superfície é **um módulo**, não um conjunto aberto de chamadores.

**Se a enumeração se mostrar instável, vira limite declarado** — não passa em
silêncio.

#### P2-3 — spec-change pendente de merge

**O que falta.** Um spec-change com quatro itens: E1 (§1.1), E2 (§1.2), o
resíduo em `01` §4 (§1.8) e a linha normativa em `01` §4.1 (§1.9 camada a).

**Por que bloqueia.** `CLAUDE.md`: alterar spec e código no mesmo PR é proibido,
e a spec é imutável durante a implementação. Os itens 1 e 7 da DoD desta fase
dependem de E2 e E1; começar código antes do merge é implementar contra texto
que se sabe errado.

**Vencimento: antes de qualquer código da Fase 2.**

---

## 6. Próxima fase

`07` Fase 3 — API mínima. ENTRY: Fase 2 completa.

**P37 vence antes dela**, com prazo declarado em `fase_1.md` §7.2.
