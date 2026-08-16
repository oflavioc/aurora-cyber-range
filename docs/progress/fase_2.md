# Fase 2 — Clock, eventos, estado, engine mínimo

**Status: CONCLUÍDA** em 16/08/2026. **Nove de nove** itens da Definition of Done
(§4), auditoria de checkpoint **PASS** contra `8c293e5` — zero BLOCKER, zero
HIGH, zero MEDIUM —, e os três LOW dispostos: dois corrigidos, um convertido em
pendência com destino.

Três `spec-change` nasceram nesta fase e estão em `main`: `a3aded5` (as
escalações do checkpoint ⏸), `c160522` (`exercise_resumed`) e `f52e924` (a
realocação do item 8). O registro final está na **§7**.

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
| P23 (falso bloqueio de hook) | Limite declarado | **Ganhou ocorrência em código.** Ver abaixo |
| P36 | Limite declarado | Sem mudança |

Os quatro limites declarados de `fase_1.md` §7.4 continuam limites, não
pendências — em especial: `check_contract_examples.py` é laço fechado, e
`tools/_common.py::parse_yaml` nunca foi comparado com parser conforme.

**A P23 ganhou ocorrência de tipo novo, e ela vale registro.** Até aqui os dez
falsos bloqueios afirmados eram de **leitura**, no hook do auditor. O primeiro
módulo desta fase produziu o primeiro em **código**: `.claude/hooks/check_architecture.py`
recusou a escrita de `range-core/state/simulation_state.py` porque a docstring
do tipo `Event` **citava o nome do campo proibido pelo invariante 4** — em prosa,
explicando que o campo não existe ali.

Regex não distingue menção de emissão, e essa é exatamente a troca declarada do
hook: falso positivo sim, falso negativo não. **Não é defeito e não se mexe
nela.** O gate real continua sendo `tools/check_event_envelope.py`, por AST, que
não confunde string constante com emissão.

O texto foi reescrito nomeando a seção da spec em vez do campo. Custo: uma
reescrita. É o preço correto do lado conservador.

### 2.1 Limite novo — `check_core_boundary.py` não olha para `contracts/`

O primeiro módulo desta fase importa `contracts.generated.events`, para não ter
literal de `event_type` no core. O import é legítimo: o invariante 1 proíbe
`domains/`, e o catálogo de eventos é agnóstico de domínio.

**Mas ele passa porque o verificador não olha, e isso não é o mesmo que ele
aprovar o caso.** `tools/check_core_boundary.py` detecta, por AST, só o que
aponta para `domains` — import direto, com alias, relativo que escape, e
dinâmico via `import_module`/`__import__`. Sobre `contracts` ele não tem opinião
nenhuma.

**A consequência, dita:** a próxima coisa importada de `contracts/` para dentro
do core não encontra guarda. Hoje só há um artefato lá que é código — o catálogo
gerado —, então a superfície é pequena. Quando deixar de ser, a ausência de
opinião passa a valer mais que a permissão.

Fica como **limite declarado**, não pendência: não é trabalho adiado, é
propriedade que o mecanismo não tem. Vira pendência no dia em que o core
importar de `contracts/` algo que não seja constante gerada.

> **O gatilho disparou, e dentro da mesma fase.** `contract_source.py` importa o
> **pacote** `contracts` para resolver o diretório e ler os `.yaml` em tempo de
> execução. Virou a **P2-15**, e ela está **fechada** —
> `scripts/check_core_contract_imports.py`. Esta seção fica como está: ela é o
> registro de quando a propriedade não existia, e a previsão dela se cumpriu
> literalmente.

---

## 3. Estrutura, migrations e variáveis de ambiente

### 3.1 Empacotamento — a Fase 1 declarou que não havia o que empacotar

`pyproject.toml` tinha `packages = []`, com a nota de que **`range-core` tem
hífen e não é pacote importável por nome** e de que a árvore daquela fase era
esqueleto. A Fase 2 tem o que empacotar, e a decisão é registrada aqui porque é
**distribuição**, não detalhe de arquivo.

**Mapeamento, não renomeação:**

```toml
[tool.setuptools.package-dir]
range_core = "range-core"
```

`package-dir` separa as duas coisas que estavam confundidas — o **caminho no
disco**, que `01` §2 normatiza como `range-core/` e que
`tools/check_core_boundary.py` varre por esse nome, e o **nome de import**, que
precisa ser identificador Python válido. Renomear o diretório para `range_core/`
contradiria o layout que a spec fixa, exigindo `spec-change` para agradar ao
empacotador, e moveria o alvo do verificador do invariante 1.

A lista de pacotes é **explícita**, e não `packages.find`: com `package-dir`
mapeando um nome a um diretório, a descoberta automática enxergaria `state`,
`clock` e `engine` como pacotes de topo, fora de `range_core`.

### 3.2 `contracts` no conjunto empacotado, e o limite que isso encontra

O fold importa `contracts.generated.events` — literal de `event_type` dentro de
`range-core/` violaria o invariante 2, e `check_contract_literals.py` isenta
`contracts/` justamente por ser onde o artefato legítimo vive.

**Sem a entrada no `pyproject`, o import só funcionava com o CWD na raiz do
repositório.** Verificado de fora dela: `ModuleNotFoundError`. Passaria em todo
teste local e quebraria no container da Fase 4.

Não fere o invariante 1 — ele proíbe o core de importar `domains/`, e o catálogo
de eventos é agnóstico de domínio. Os nomes de **flag**, que são de domínio,
continuam chegando como dado em `Declarations`, nunca por import.

> **Esta entrada vive na zona que o `check_core_boundary.py` não varre**, e o
> limite está descrito na **§2.1**: o verificador só tem opinião sobre
> `domains`, e sobre `contracts` ele não olha. A decisão de empacotar `contracts`
> e o limite de não haver guarda sobre esse caminho são a mesma coisa vista de
> dois lados — lidas separadas, a decisão parece coberta.

### 3.4 O event store, e as quatro decisões que ele carregou

**O envelope mudou de camada.** `Event` e `Correlation` nasceram em
`state/simulation_state.py`, porque o fold foi o primeiro a precisar deles.
Estava invertido, e apareceu ao escrever o `append`: `simulation_state` é UMA das
cinco projeções **sobre** eventos, e uma projeção definindo o envelope faria
`events/` depender de `state/`. Movido para `range-core/events/envelope.py` no
momento mais barato — um arquivo, com o fold e os testes como únicos consumidores.

**O cálculo da epoch é compartilhado; a conferência, não.**
`range_core.events.epoch.current_epoch` é usado pelo store, que carimba, e pela
projeção, que devolve. Escrever a regra duas vezes é a classe da D4. Mas
`_verify_epochs` **não** chama o compartilhado: se chamasse, o fold conferiria o
número contra o mesmo código que o produziu, e a conferência viraria tautologia.
Compartilha-se o cálculo; a segunda opinião continua sendo segunda.

**`event_id` não sai do `RANDOM_SEED`.** As cinco ocorrências em `docs/spec/` —
`00` §8, `02` §6, `05` §8, `06` T8 e `07` Fase 5 — amarram o seed a dataset
sintético, Linha B, evidências e senhas de seed. Nenhuma o liga a identidade de
evento, e a propriedade que sairia disso ninguém pediu: ids reproduzíveis entre
execuções distintas são colisão esperando acontecer. ULID de `secrets`,
implementado na stdlib para não trazer dependência que T15 obrigaria a pinar.

**A porta do relógio existe para o store não ficar bloqueado nem inventar o
clock.** `append` carimba a partir do `exercise-clock`, que é outra peça. A
`ExerciseClockPort` é o limite do que o store sabe sobre tempo: recebe as quatro
marcas prontas, numa leitura só — ler em chamadas separadas abriria janela para
o clock avançar, ou ser pausado, entre elas.

**O que a peça NÃO entrega:** `InMemoryEventStore` perde tudo ao morrer, e `06`
T3 exige que "reinício do processo restaura a projeção corrente sem
intervenção". O backend persistente é a próxima peça, e carrega uma decisão de
dependência — `psycopg[binary]` 3, já escolhido na §1.3 — com fecho transitivo a
pinar por T15, mais serviço de Postgres no job de CI.

### 3.5 O backend persistente, e por que ele não traz o mecanismo da Fase 5

**Antecipar a garantia, não o mecanismo.** `02` §4 e `05` §7 exigem role
`INSERT`-only, `REVOKE UPDATE/DELETE` e trigger — isso é **Fase 5**, e
antecipá-lo seria dois lugares definindo a mesma coisa, com o segundo a
divergir.

Mas append-only não podia ser, até lá, disciplina do código Python: quem tem a
connection string reescreve história e **nada acusaria**. O que esta fase entrega
é **detecção** — `sequence` contígua e encadeamento por hash, verificados a cada
leitura. E detecção não vira redundância depois do `REVOKE`, porque `REVOKE` não
protege contra quem tem privilégio: migração, restauração de backup e acesso
administrativo continuam existindo.

**A sequência é atribuída pela aplicação, e não por `BIGSERIAL`.** Sequência de
banco consome número em transação que faz rollback, e o buraco resultante seria
alarme falso — detecção que grita sem defeito é detecção que se aprende a
ignorar.

**Os metadados de integridade ficam na TABELA, não no envelope.** `sequence`,
`previous_hash` e `row_hash` são propriedade de armazenamento; o envelope é o de
`09` §1.1, e acrescentar campo a ele exigiria mudar o contrato.

**Os dois limites, declarados e um deles com teste próprio.** Truncamento da
cauda não é detectável — apagar as últimas linhas deixa cadeia íntegra e
sequência contígua, e pegar isso exigiria âncora externa, que a Fase 2 não
inventa. E reescrita completa por quem tem o código também não: quem recomputa a
cadeia inteira produz store íntegro e falso. `test_truncar_a_cauda_NAO_e_detectado`
existe para o limite ser **verificado** em vez de herdado como crença: se um dia
a detecção passar a pegá-lo, o teste fica vermelho e alguém atualiza a
declaração.

**Duas variáveis de ambiente, de propósito.** A migration lê `DATABASE_URL`; os
testes leem `AURORA_TEST_DATABASE_URL`. Os testes **truncam** a tabela, e apontá-los
para a primeira faria um `unittest` distraído apagar o banco de desenvolvimento
de quem tivesse o `.env` carregado. Ausente a segunda, eles pulam — e o `skip`
diz como rodar, para pulo silencioso não ser lido como verde.

**A checagem da P2-2 ganhou alcance ao existir a segunda implementação.** Ela
olhava só a classe em `store.py`; uma subclasse em outro arquivo podia
acrescentar `read_since` e passar. Apareceu ao escrever `PostgresEventStore`, que
é quando esse buraco aparece — a primeira implementação não tem com que divergir.

### 3.6 Dois escritores contra a mesma tabela

`sequence` e `previous_hash` são escolhidos pela **aplicação** a partir da última
linha — ler-e-escrever. Dois processos podiam, em tese, ler o mesmo topo e
produzir sequência repetida ou dois elos no mesmo `previous_hash`: a cadeia
**bifurca**, e a verificação passaria a acusar sem que ninguém tivesse
adulterado nada.

`_persist` toma `LOCK TABLE … IN EXCLUSIVE MODE` antes de ler o topo. O
`EXCLUSIVE` permite leitura concorrente e bloqueia escrita, que é a forma exata
do problema.

**E "o lock resolve" era suposição até ser testada.** Quatro threads, cinco
appends cada: sequência contígua 1–20, nenhum erro, cadeia íntegra. E a variante
**sem** o lock, rodada como prova descartável, produziu `UniqueViolation`, 7
linhas de 20 e sequência com buracos — então o teste pega a ausência em vez de
passar por acaso.

Isso também confirmou a **segunda linha de defesa**, que era afirmação de
docstring: `sequence` é chave primária e `row_hash` é único, então mesmo sem o
lock a colisão vira erro de integridade em vez de cadeia bifurcada em silêncio.

**Uma correção de estrutura veio junto.** `CadeiaAcusaReescrita` herdava de
`StoreEmPostgres` para reusar o `setUp`, e com isso os quatro casos da base
**rodavam duas vezes** — a contagem subia sem que nada a mais fosse provado. Os
"12 pulados" da rodada anterior eram 8 distintos e 4 repetidos. Base sem teste
próprio resolve.

### 3.7 O `exercise-clock`

**O tempo de parede entra por injeção.** `now` é parâmetro do construtor, com
`time.time` de default. Não é cerimônia de testabilidade: um clock que lê o
relógio do processo exige `sleep` e tolerância no teste, e teste com tolerância
sobre relógio ou é lento ou é intermitente — e intermitente é pior que ausente,
porque ensina a reexecutar até passar. Com a fonte controlada, *"durante o
PAUSAR o `exercise_time` não avança e o `wall_timestamp` avança"* é igualdade, e
não aproximação. Nenhum teste do clock dorme.

**Multiplicador é conjunto fechado — 1x, 5x, 20x — e não faixa.** `01` §3 os
enumera. Valor livre tornaria a timeline do AAR irreconstruível por combinação
que ninguém testou, apesar de `09` §1.1 gravar o multiplicador em cada evento
justamente para reconstruí-la.

**Trocar de multiplicador fecha o acumulado com o antigo.** Sem isso, passar de
1x para 20x no meio multiplicaria **retroativamente** o tempo já decorrido.

**Pausa dupla e retomada sem pausa são recusadas.** Não são idempotentes por
desenho: pausa dupla costuma ser dois facilitadores agindo sobre o mesmo
exercício, e silenciar isso esconde o conflito em vez de resolvê-lo.

**`start_new_epoch` rebobina o rótulo e não o timestamp** — a separação que o
`a3aded5` normatizou, agora com teste. O clock não sabe o que é rollback; quem
chama é quem sabe.

**O item 3 fecha pela metade, e a outra metade não é dele.** "PAUSAR congela o
clock" está fechado; "bloqueia disparo agendado" é do inject-engine. O clock
oferece `is_paused` e não agenda nada: quem decide não disparar é quem dispara.

### 3.8 A medição do item 8

`scripts/bench_reconstruction.py`, contra Postgres em container efêmero.

| | |
|---|---|
| **Data** | 15/08/2026 |
| **Máquina** | Windows 11 (10.0.26200), Python 3.12.10 |
| **Stack** | PostgreSQL 16.4 (`alpine`, digest pinado) · psycopg 3.2.12 · migration `0001_event_store` |

O contexto está junto do número porque o número **vale contra essa stack**.
Daqui a três fases, "2,874 s em 150 mil" sozinho é a §1.6 esperando acontecer —
e medição é o tipo de coisa que ninguém repete antes de citar. O bench passou a
imprimir data, máquina e stack junto do resultado, para que a próxima execução
não dependa de alguém lembrar de anotar.

**Não roda no CI**: tempo em runner compartilhado
varia com o vizinho, e gate que falha por vizinho ensina a reexecutar até passar
— o mesmo argumento que tirou o `sleep` dos testes do clock.

**Duas formas, porque o custo não é linear no número de eventos.** A máscara é
laço por intervalo abandonado: `R` rollbacks com intervalos longos custam
diferente de `N` eventos sem rollback. A forma **patológica** — 100 rollbacks
todos ancorados no `exercise_started`, cada um marcando o prefixo inteiro, que é
`O(R × N)` — é alcançável: é o facilitador rebobinando repetidamente para o
início.

| Forma | Eventos | `read_all` | `project` | Total |
|---|---:|---:|---:|---:|
| realista | 50 000 | 0,817 s | 0,029 s | **0,846 s** |
| patológica | 50 000 | 0,790 s | 0,068 s | **0,859 s** |
| realista | 100 000 | 1,641 s | 0,050 s | **1,691 s** |
| patológica | 100 000 | 2,001 s | 0,188 s | **2,189 s** |
| realista | 150 000 | 2,776 s | 0,098 s | **2,874 s** |
| realista | 200 000 | 4,165 s | 0,139 s | **4,304 s** |

**O ponto de quebra é medido, não extrapolado: ~150 mil eventos.**

**E as duas metades não são as que se esperava.** Em 150 mil:

| | Tempo | Fatia |
|---|---:|---:|
| consulta + hidratação | 1,836 s | 64% |
| verificação da cadeia | 0,941 s | 33% |
| `project` — o fold | 0,098 s | **3%** |

Se o orçamento apertar, a decisão é sobre o **caminho de leitura**, e não sobre
a recomputação do fold. Hidratação primeiro, cadeia depois. Isso desarma a
P2-10: a estratégia do fold pode ser construída em cima sem reserva.

**O envelope, declarado porque é suposição.** O critério fala de "exercício de
4 h", não de contagem de eventos, e não existe pack para produzir um exercício
real. O que está medido é a curva volume → tempo.

> **Isto virou a realocação do item 8**, decidida pelo operador em 16/08/2026 e
> submetida em `spec-change/item-8-volume-de-4h`. Aceitar o envelope medido
> fecharia o item com evidência de outra coisa: a curva prova que o motor aguenta
> 150 mil eventos, **não** que 4 h cabem abaixo disso — e ninguém sabe o segundo
> número. Chamar a primeira de prova do segundo é atestação com um passo
> intermediário, que é o que o E1 recusou.
>
> O item da Fase 2 passa a cobrar **a curva**, que é o que esta fase pode provar
> e que a §3.8 já entrega com data, máquina e stack. O critério original — < 3 s
> para exercício de 4 h — vai **intacto** para a Fase 7, que é onde nasce o pack
> de 4 h (`04` §9), e ganha uma segunda metade na Fase 9, que é onde nasce a
> telemetria. Os detalhes e a varredura estão na §3.12.

**O que reabre:** a **Fase 9**, com `telemetry_emitted`. É a única fonte com
ordem de grandeza diferente das demais — injects são dezenas, ações de
participante são centenas, e telemetria é a que pode chegar às centenas de
milhares sozinha.

**Achado lateral, e ele virou a P2-11:** `append` abre uma conexão por chamada.
A medição usou escrita em lote de propósito, para não contar custo de escrita
como se fosse de reconstrução.

### 3.3 O job `contratos` roda teste de código, e o nome não diz isso

Os testes do `range-core` entraram como passo do job **`contratos`**, que é
`required status check`. O nome dele deixou de descrever o escopo.

**É deliberado, e o motivo é a P1-18:** job novo é context novo, e context
exigido antes de existir em `main` trava todo PR que não o produza. O encaixe em
job existente não cria context, e o `contratos` já instala a aplicação, que os
testes exigem.

**Por que isto está aqui e não só no YAML.** `contratos` é o nome que aparece na
branch protection e na página do PR, e quem lê "contratos verde" lê *contratos*.
O comentário mora no arquivo que ninguém abre enquanto revisa um PR.

**Condição de saída:** renomear quando houver **outro** motivo para tocar na
branch protection — a renomeação sozinha não justifica o risco que ela cria.

**Dois passos, e o segundo existe por uma assimetria medida.** A suíte roda na
raiz do repositório, e ali `contracts` resolve pela **árvore** mesmo sem
instalação — verificado com `python -S`. `range_core` não resolve, porque o
hífen o impede. Então o import de `range_core` na suíte já prova a instalação, e
o de `contracts` **não prova nada** — justamente a entrada que existe para o CWD
que não é a raiz. O segundo passo importa os dois de fora da raiz, e é o que
fecha isso.

**Ganhou uma terceira asserção na peça do loader**, e por motivo próprio: o
loader passou a **ler os `.yaml` de `contracts/` em tempo de execução**, e isso
não é o mesmo que importar o módulo gerado. Sem `package-data` no `pyproject`, a
instalação levaria `contracts/generated/*.py` e deixaria os contratos para trás —
árvore e instalação editável continuariam verdes, e o container da Fase 4 subiria
sem os contratos. É a mesma assimetria que o `package-dir` já pagou uma vez.

### 3.9 O loader e o inject-engine

A peça que a §6.2 previu, com as decisões que ela deixou em aberto agora
tomadas. Fecha o **item 9**, a **metade restante do item 3** e o **DEMO** da
fase.

**Onde mora o pack mínimo: decidido pelo operador — `tests/fixtures/pack_minimo/`.**
A §6.2 registrou inclinação e não decisão, e a decisão veio de fora. A forma de
`04` §1 é respeitada dentro do fixture: `manifest.yaml`, `injects.yaml` e
`objectives.yaml` com os mesmos nomes e a mesma estrutura do pacote real. O que
muda é o endereço, não o formato — um fixture com forma própria exercitaria um
loader que nenhum pack usa.

**Três injects, e os três existem por um caminho de mecanismo:** A01 tem
`effects` e nenhuma decisão; A02 tem `decision_point`, que é o único caminho por
onde `option_effects` chega à projeção; R01 é `noise: true`, que é o ramo `else`
do `if/else` do contrato — e é ele que faz a caminhada das regras descer por um
`if`, que é exatamente o código que a P2-12 estreitou.

**`objectives.yaml` num pack "mínimo" não é excesso.** Sem ele,
`x-aurora-ref: pack_objectives` resolveria contra conjunto vazio e o pack seria
recusado — corretamente. A alternativa era três injects todos de ruído, que não
exercitaria referência entre arquivos, que é a única coisa que a camada
`x-aurora-*` existe para verificar. O loader **lê** o arquivo para o registro e
**não o valida**: o contrato dele é da Fase 6, e ler para registro não é validar.

#### O escopo da canonicalização é derivado do contrato, e não da versão do loader

**A formulação anterior envelheceu, e o critério dela foi preservado.** A regra
v1 nasceu em docstring de `simulation_state.py` como *"escopo são os arquivos que
o LOADER PARSEIA"*, com o critério *"se o loader lê, pode mudar a resolução; se
não lê, não pode"*.

O critério está certo. A formulação deixou de estar no dia em que existiu um
segundo loader: o da Fase 2 não lê `branches.yaml` — branching é entregável da
Fase 7 —, e o da Fase 7 vai ler. **Escopo definido pela versão do loader faria o
mesmo pack ter hash diferente em duas fases**, e todo exercício desta fase
deixaria de reconstruir na próxima sem que ninguém tivesse tocado no pack.

O escopo v1 passa a ser: as entradas de `x-aurora-registry.package_files`
terminadas em `.yaml`, e apenas as presentes. `branches.yaml` entra desde já
porque **pode** mudar resolução. `GM_NOTES.md`, `evidence/` e `media/` ficam de
fora pelos motivos que já estavam escritos.

É a §1.6 outra vez, e desta vez pega antes de custar: a afirmação era verdadeira
quando foi escrita, e a decisão que a derrubou foi tomada no mesmo ciclo.

**Limite declarado:** arquivo `.yaml` presente no pack e ausente de
`package_files` não entra no hash. Pela regra isso é correto — documento que
loader nenhum lê não muda resolução —, mas significa que o escopo depende de o
contrato listar o que existe.

#### PyYAML no núcleo, e os dois parsers que agora leem os mesmos seis contratos

O loader lê com `yaml.safe_load`, e não com `tools/_common.py::parse_yaml`. Duas
razões, e a segunda decidiria sozinha: o núcleo não importa de `tools/`, que é
onde vivem os seis verificadores stdlib; e `parse_yaml` é deliberadamente
estrito, lê o **subconjunto** em que nossos contratos são escritos por regra
nossa, e pack é escrito por humano. A spec já aceitou esse argumento uma vez,
quando `check_spec_examples.py` trouxe PyYAML para ler `docs/spec/`.

**Passam a existir dois parsers sobre os mesmos seis arquivos, e isso é risco
real.** `tests/test_pack_loader.py::DoisParsers` afirma que os dois produzem a
mesma árvore para os seis. E isso **fecha, por consequência, um limite que
`fase_1.md` §7.4 declarou sem verificar**: `parse_yaml` nunca tinha sido
comparado com parser conforme.

#### `t_relative` é `HH:MM`, e a interpretação vive no engine porque o contrato a recusa

O contrato deixa o campo como string de forma livre, de propósito: fechar
formato em schema seria a classe D6. Mas **agendar exige interpretar**. A forma
foi lida na fonte, não escolhida: `04` §5 traz `"00:47"` num exercício de 240
min, `04` §6 traz `before: "01:30"` e `03` §7 traz `"T+01:10"` — são minutos, não
segundos.

O loader converte no boot e **recusa alto** o que não casa. Recusar é o oposto de
inventar: um `t_relative` em outro formato derruba o boot em vez de virar
agendamento silenciosamente errado, que é a falha que não aparece até o
exercício ao vivo.

#### A janela de agendamento não é memória, e o corte é o que a torna correta

`due_injects` é **consulta**. Um inject está em atraso quando

```text
corte < t_relative <= posição corrente
```

e não há `inject_fired` dele na epoch corrente.

**A posição é o rótulo `T+`**, que rebobina até o ponto de corte no rollback
(`01` §3). É isso que faz o agendamento voltar a valer depois de um rollback sem
o engine guardar nada: a posição está no relógio, e o que já disparou está no
store. Memória do que foi aplicado seria estado fora do fold — a mesma coisa que
a D3 recusou para a idempotência, com outro nome.

**O corte é a posição da âncora do último `rollback_performed`**, ou `-1` se não
houve nenhum. Sem ele, o rollback faria os injects **anteriores** ao corte
dispararem de novo, e `09` §3 é explícito ao desenhar só `A03 (novamente)` na
epoch 1.

**Limite declarado:** inject com `t_relative` anterior ao corte é tratado como
resolvido, tenha disparado ou não. É a leitura conservadora — o corte declara que
tudo até ali está assentado —, e a alternativa faria o engine ressuscitar inject
que o facilitador pulou de propósito.

#### O rollback: a ordem é gravar antes de rebobinar, e a origem é uma subtração

O `rollback_performed` é gravado **antes** de o clock rebobinar. Gravado depois,
ele carregaria o `exercise_time` do ponto de corte e pareceria ter acontecido lá
— e `09` §3 o desenha no fim da epoch abandonada, que é quando ele foi ordenado.

**A rebobinagem levou uma correção de leitura no caminho, e ela vale registro.**
A primeira formulação calculou a origem da nova epoch a partir de
`exercise_timestamp`, raciocinando que ele é absoluto. Está errado para rollbacks
**encadeados**: `exercise_timestamp` é decorrido desde T0 e nunca rebobina, então
a partir da segunda epoch ele deixa de ser a posição de cenário. Quem carrega a
posição é o **rótulo `T+`**, justamente por rebobinar.

A conta certa é `decorrido agora − posição da âncora`, e ela compõe sozinha:
como a posição da âncora já está no referencial rebobinado, a origem nova
acumula tudo o que foi descartado. O que sobra entre `exercise_timestamp` e o
rótulo passa a ser exatamente **quanto o rollback descartou**, que é o que
`01` §3 exige — e `test_encadeados_compoem_e_o_rotulo_rebobina_de_novo` prova o
caso que derrubou a primeira versão.

#### `technical_failure` é recusado, e a recusa é o que impede o item 7 de passar por fechado

O engine aceita os quatro motivos que a taxonomia declara — lida de
`contracts/events.schema.yaml`, nunca repetida no código — e **recusa**
`technical_failure`. `09` §3.1 dá a esse motivo, e só a ele, o efeito *"relógio
de métricas congelado"*, e `06` T3 exige que os extremos do intervalo sejam
gravados **no evento**. O campo de payload é a **P2-4** e não existe.

Emitir sem ele gravaria um rollback que a Fase 6 lê como se não houvesse
congelamento nenhum: o registro existiria e o requisito sumiria, que é a forma
exata do E1. A recusa deixa o item 7 **visível**.

**E a guarda não pode ficar órfã.** A constante do motivo é conferida contra a
taxonomia na construção do engine: se um `spec-change` renomear o valor, o engine
recusa subir, em vez de a guarda passar a apontar para um nome que ninguém usa.

#### Duas coisas que o engine não pôde fazer, e nenhuma delas é omissão

**`resume` não emite evento.** O catálogo de `09` §4.1 é registro fechado e não
tem `exercise_resumed`. O store guarda o início da pausa e não guarda o fim.
Inventar `event_type` violaria o invariante 3 e reaproveitar `exercise_paused`
gravaria dois eventos idênticos com significados opostos. Virou a **P2-13**.

**`SUPPORTED_SCHEMA_VERSIONS` é `[2]`, e `04` §4 pede `[N, N-1]`.** Não existe
contrato v1 neste repositório: suportar N-1 exige a migração em memória, que é
item de DoD da Fase 7. Declarar suporte que não há seria pior que declarar o
suporte real, e o pack em v1 é recusado com a instrução em vez de com uma
mensagem sobre `const: 2`.

#### O DEMO virou passo de CI (continua abaixo, na §3.10, o item 2)

`scripts/demo_fase2.py` roda a sequência do `07`: carregar pack, disparar A01,
ler projeção, rollback, ler projeção restaurada — mais o PAUSAR atravessando o
`t_relative` de um inject sem disparar nada.

**Não é `range-cli`**, que é entregável da Fase 7. É a mesma saída que o `07`
já registrou para o DEMO da Fase 1: roteiro que exige peça de fase futura não é
roteiro desta fase.

**Roda no CI**, e isso é o ponto: até aqui "o demo roda" era atestação. Ele prova
o que os testes não provam — a **montagem**: contratos lidos do disco, flags do
adapter entregues como dado, pack, clock, store e engine ligados na ordem em que
um chamador real os liga.

### 3.13 A primeira auditoria da fase, e o que ela cobrou

**FAIL em 16/08/2026**, contra `b304c19`. Um BLOCKER, um HIGH, dois LOW.
Relatório em `docs/progress/audit_20260816T071854Z.md`.

#### B1 — a fase criou a primeira suíte real e não estendeu o julgador

A allowlist do auditor admitia `pytest`; a suíte da Fase 2 é **`unittest`**, por
decisão registrada. O auditor não executou **nenhum** teste da fase — nem os
quatro verificadores novos, nem o DEMO, nem o harness de mutação — e voltou a
avaliar por leitura de código. **Sete dos nove itens da DoD ficaram NÃO
VERIFICADO.**

**A regra violada está escrita dentro do arquivo que ela governa:** *"script novo
que precise ser executado pelo auditor entra aqui por nome, no commit que o
cria"*. `git diff origin/main...HEAD -- user-scope/` devolvia **zero arquivos**.

**É reincidência nomeada**: o H3 da segunda auditoria da Fase 1 é o mesmo defeito,
e o próprio hook o cita ao justificar as entradas de então. E o agravante é de
autoria: esta fase passou três voltas argumentando que prova por construção não
basta, e entregou uma suíte que o julgador não conseguia rodar.

**Fechado com seis entradas, cada uma com motivo escrito e prova nas duas
direções** — `phase0_negative_tests.py` passou de 30 para **36** leituras
legítimas e de 36 para **40** escritas bloqueadas:

| Entrada | Por quê |
|---|---|
| `python -m unittest discover -s tests` | a suíte, na **forma exata** do CI |
| `check_store_read_surface` + probes | P2-2 — sem executar, o auditor lê a lista de métodos e infere |
| `check_core_contract_imports` + probes | P2-15, idem |
| `demo_fase2` | o DEMO SCRIPT que `07` exige; roda em memória, sem banco |

**Forma exata, e não família** — três probes provam que `python -m unittest
<módulo>`, `discover -s .` e argumento extra continuam **bloqueados**. Módulo
arbitrário por nome é execução arbitrária com outro nome, e `discover -s <dir>`
livre alcança qualquer diretório.

**`bench_reconstruction.py` ficou de fora, e a ausência é decisão.** Ele exige
Postgres, **escreve** centenas de milhares de linhas e demora minutos. O item 8,
na forma nova, não pede reprodução: pede a curva com máquina, data e stack
declaradas — que o script gera **por código**, o que é conferível por leitura. O
relatório marcou o item 8 PASS pela forma e declarou não ter reproduzido a
medição, o que é a leitura certa. Admiti-lo daria ao auditor uma operação de
escrita longa para confirmar o que a forma já garante. Há probe fixando a
ausência: readmiti-lo passa a exigir decisão explícita.

#### H1 — falso positivo, e virou a P2-16

Ver a **P2-16**. O cálculo do próprio gate desmonta o achado, e a condição que o
produziu — o worktree resolvendo `main` para o ref local — vira pendência de
mecanismo com destino.

#### L1 e L2 — os dois procedem, e o L1 é o mais instrutivo

**L1:** a docstring de `rollback` dizia `technical_failure` **é RECUSADO**, quatro
linhas acima do código que o aceita. E o cabeçalho do mesmo módulo estava correto,
no pretérito — **corrigi a afirmação geral e deixei a específica, no mesmo arquivo
e na mesma edição.** A §1.6 não avisa que já foi aplicada uma vez ali.

**L2:** o cabeçalho de `bench_reconstruction.py` citava a forma **revogada** do
item 8. A tabela de DoD e a §3.12 fazem a distinção; só o script ficou para trás.

#### Os itens 5 e 6, e o limite que virou teste

A observação do relatório é justa e mais estreita do que ficou: *"grava"* e
*"incrementa"* têm cobertura em memória, e a tabela já as cita. O que depende
**exclusivamente** de Postgres é *"sobrevive ao reinício"* — e num ambiente sem
`AURORA_TEST_DATABASE_URL` a suíte fica verde com essa metade não exercitada.

Não é corrigível sem inventar um segundo backend persistente só para o teste, que
seria uma terceira implementação do store. **É declarável — e agora é verificado**:
`test_event_store.LimiteDoStoreEmMemoria.test_o_store_em_memoria_NAO_sobrevive_ao_reinicio`,
na forma de `test_truncar_a_cauda_NAO_e_detectado`. Se alguém der persistência ao
store em memória, o teste fica vermelho e a dependência dos itens 5 e 6 em relação
ao CI passa a ser revisada — em vez de envelhecer escrita em prosa.

### 3.14 A segunda auditoria — PASS, e o que ela cobrou depois

**PASS em 16/08/2026**, contra `8c293e5`. Zero BLOCKER, zero HIGH, zero MEDIUM,
três LOW. Relatório em `docs/progress/audit_20260816T075242Z.md`.

**A diferença entre as duas rodadas é o que o B1 fechou:** desta vez o auditor
executou. `Ran 155 tests ... OK (skipped=9)`, mais os seis verificadores, os
quatro `*_probes.py`, o harness negativo e o DEMO. A primeira rodada julgou por
leitura sete dos nove itens; esta julgou por execução tudo o que não depende de
Postgres.

**O achado mais forte não é um finding.** A seção *"testes que não provam o
requisito"* voltou vazia, com o que ele procurou declarado: mock (zero na
árvore), `skip` sem justificativa, teste que passa pelo motivo errado, limite
herdado como crença, recusa sem discriminante. Os dois testes que passavam por
acidente esta fase achou sozinha e transformou em mutação permanente — e é isso
que a seção registra.

#### Os três LOW, e o que cada um virou

| | O que era | Disposição |
|---|---|---|
| **L1** | `simulation_state.py` dizia *"registro FECHADO de 32 tipos"*; o catálogo tem 33 | **corrigido** — e é o §1.6 pela terceira vez no mesmo tipo de lugar: número de catálogo em prosa dentro de código. A própria fase acrescentou o `exercise_resumed` e não voltou aqui |
| **L2** | a whitelist da superfície do store só enxergava subclasse **direta** | **corrigido**, com eixo novo no probe |
| **L3** | o `start` do intervalo congelado vem da âncora, não do inject falho | **P2-17** — não é defeito a corrigir aqui |

#### L2 — o buraco tinha a forma do buraco anterior

`_subclasses_fora_da_linha` casava `bases` por nome contra `EventStore`. Uma
classe `class X(InMemoryEventStore)` não casava e podia acrescentar `read_since`
público sem reprovar.

**E o eixo de subclasse já tinha sido acrescentado depois, por ter sido buraco uma
vez** — antes dele, só a classe base era conferida. Fechar **um nível de cada
vez** é o que faz o buraco voltar com outro nome. A checagem passou a usar **fecho
transitivo**, que não tem "próximo nível".

O probe herda em **dois saltos** e monta uma árvore de core em diretório
temporário — dois arquivos, porque a violação só existe na relação entre eles, e
nada é escrito em `range-core/`. Para isso a raiz do core passou a acompanhar o
alvo do CLI, o que antes tornava o eixo inexercitável sem sujar a árvore.
**Conferido que discrimina:** revertido o fecho para filho direto, o probe novo
reprova; restaurado, passa. Cinco eixos.

#### Três pendências do aparato, e nenhuma é da fase

O relatório levantou duas coisas que **não são findings** e que o registro
absorve como pendência de mecanismo, junto da **P2-16**: o harness de mutação
escreve em `tempfile` fora do worktree, contra a suposição de contenção do hook
(**P2-18**), e o auditor não tem como confirmar que o CI está verde no commit que
audita (**P2-19**) — o que deixa metade de dois itens da DoD verificada por
leitura e configuração, não por execução.

**As três são do aparato de auditoria**, e é por isso que estão registradas como
tal: nenhuma delas se conserta mexendo no código da fase, e todas se repetem no
próximo checkpoint se ninguém as fechar.

#### O que o auditor declarou sobre auditar sob as regras desta fase

Ele registrou, no item 4, que `8c293e5` altera o hook que restringe o Bash dele —
e examinou a mudança linha a linha antes de operar sob ela: estritamente aditiva,
forma exata ancorada, cinco scripts por nome explícito, nenhuma negação
afrouxada.

**Registrar isso é a conduta certa e vale nomear**, porque a alternativa — não
mencionar — é indistinguível de não ter notado. É a mesma razão de esta fase ter
declarado, no commit que estendeu a allowlist, que estava ampliando o próprio
julgador.

### 3.12 A realocação do item 8, e o que a varredura achou

Decidida pelo operador em 16/08/2026: **realocação com destino**, não aceitação
do envelope. `spec-change/item-8-volume-de-4h`.

#### A varredura, com os critérios

| | Padrão | |
|---|---|---|
| **P1** | `< ?3 ?s\|3 segundos\|tres segundos` | o limite pelo número |
| **P2** | `\b4 ?h\b\|quatro horas\|240` | o volume |
| **P3** | `reconstru` | a exigência sem nenhum dos dois |

**Três sítios — e eles não diziam a mesma coisa, que é o achado que só a
varredura dá:**

| Sítio | Volume citado? |
|---|---|
| `01` §7 — *"< 3 s **para exercício de 4 h**"* | sim |
| `06` T3 — *"**para exercício de 4 h** roda em < 3 s"* | sim |
| `07` Fase 2, item 8 — *"a partir do store roda em < 3 s"* | **não** |

**A redação do item omitia o volume**, e sem ele qualquer medição o satisfaz — o
que explica, retroativamente, por que a §3.8 precisou declarar o envelope à mão.

#### A classe: o item que a própria letra já dava por cumprido

Isto é a forma do **E2**, e vale como classe e não como detalhe desta realocação.

O E2 foi *"o item 1 dizia `wall_time`, e o envelope não tem esse campo"* —
insatisfazível por construção. Este é o mesmo defeito **na direção oposta**:

| | O item diz | O critério que o julga diz | Efeito |
|---|---|---|---|
| **E2** | `wall_time` | `wall_timestamp` | impossível de cumprir; a implementação certa o deixa por marcar |
| **item 8** | "< 3 s" | "< 3 s **para exercício de 4 h**" | **cumprido por qualquer medição** |

**A direção oposta é a pior das duas.** O item insatisfazível trava e alguém
investiga; o item cumprido pela própria letra passa, e passa **verde**. O item 8
esteve tecnicamente cumprido desde a primeira medição — 0,846 s em 50 mil eventos
satisfaz *"reconstrução completa da projeção a partir do store roda em < 3 s"*
ao pé da letra.

**O que segurou não foi mecanismo, foi desconfiança** — a §3.8 declarou o
envelope à mão porque quem mediu percebeu que o número não respondia à pergunta.
Isso não é propriedade: é sorte com disciplina. Se a §3.8 tivesse sido escrita
por quem só lesse o `07`, o item teria fechado.

**A regra que ela ensina:** item de DoD e critério de aceitação são **duas
redações da mesma exigência**, e divergência entre elas não é redundância inútil
— é o único lugar onde este defeito aparece antes de custar. Ler os dois lado a
lado, e não um deles, é o que a varredura fez.

**Onde ela morde de novo:** qualquer item que declare um limite sem declarar
**sobre o quê**. `< 1 s` do wallboard na Fase 4, `< 5 min` do seed na Fase 5 —
ambos com o mesmo formato, e nenhum dos dois foi conferido contra o critério que
o julga. Não é escopo desta fase; fica dito.

**`01` §7 não foi tocado, e a ausência é decisão:** ele enuncia a norma de
desempenho, que é permanente e não ligada a fase. O que se realocou foi **quem a
verifica** — mesma forma da correção do item 7.

#### O destino, conferido na fonte

`04` §9: o pack completo de 4 h é o `ransomware-universidade`, entregável da
**Fase 7**. O outro pack — `fraude-academica-express` — é de 90 min e é da Fase
12. A distinção que o operador pediu para conferir — *"onde nasce o pack"* versus
*"onde nasce um pack de 4 h"* — existia, e as duas respostas coincidem.

#### Os dois destinos, criados e não prometidos

Mergeado em 16/08/2026. O critério original — **< 3 s, para exercício de 4 h** —
existe agora em quatro lugares, dois de DoD e dois de aceitação:

| Fase | Item de DoD (`07`) | Critério (`06`) | O que ela mede |
|---|---|---|---|
| **7** | reconstrução do exercício de 4 h do `ransomware-universidade` em < 3 s | **T12** | o volume que o **pack** produz |
| **9** | a reconstrução continua em < 3 s com `telemetry_emitted` no volume de 4 h | **T13** | o volume que o **range** produz |

**Nenhum dos dois é promessa em prosa**: os quatro são checklist binária ou
critério de aceitação, que é a diferença que o E1 estabeleceu — requisito
realocado sem fase obrigada a cumpri-lo não é mover, é apagar com passo
intermediário.

`01` §7 continua enunciando a norma, sem alteração.

#### O insumo é dois, e por isso o item virou dois

`telemetry_emitted` é `event_type` do catálogo e vai para o event store como
qualquer outro: **entra na leitura total que a reconstrução percorre**. E é a
única fonte com ordem de grandeza diferente — injects são dezenas, ações de
participante são centenas, telemetria pode chegar às centenas de milhares
sozinha. A própria §3.8 já registrava a Fase 9 como quem reabre o item.

Então o exercício de 4 h da Fase 7 **não é** o da Fase 9: lá se mede o volume que
o **pack** produz, aqui o que o **range** produz. Com item só na Fase 7, o
critério seria verificado e passaria a ser falso na Fase 9 sem nada ficar
vermelho.

**É a única parte que foi além da instrução recebida, e está dita como tal.** A
instrução pedia um destino; a regra que a acompanhava — *"a fase que decide é a
que tem o insumo"* — aplicada a um insumo que a varredura mostrou ser dois, dá
dois itens. Mesma divisão que o `spec-change` anterior deu ao `rehearsal`, e
removível sem tocar no resto.

### 3.11 A metade de contrato do `exercise_resumed`, e o item 7

Depois do merge do `spec-change`. Duas coisas caminharam juntas porque a segunda
dependia do mesmo arquivo: `contracts/events.schema.yaml`.

**O `exercise_resumed`, nas quatro camadas:** enum de
`event_type_facilitation`, entrada em `x-aurora-registry.effect_class` (`machine`),
constantes geradas em Python e TypeScript, e emissão em `InjectEngine.resume`.

**`paused_in(events)` é função pura sobre o fluxo**, na mesma forma do fold —
quem restaura confere sem montar engine. `exercise_started` e `exercise_reset`
também devolvem o estado a *correndo*: `01` §4.2 chama o reset de recomeço, e
exercício que recomeça não herda a pausa do anterior.

**`restore_pause_state` restaura o estado de pausa, e SÓ ele.** T0, o acumulado,
o multiplicador e a origem da epoch continuam por restaurar — item de DoD da
**Fase 4**. A metade que está aqui é a que **não era possível** antes do evento:
as outras três são deriváveis do envelope hoje.

#### O par de `06` T5, e o teste que passava pelo motivo errado

O critério novo pede os dois casos, e a razão é que **um teste que só verifique o
primeiro passa com um engine que sobe sempre pausado**. Os dois estão em
`test_inject_engine.ReinicioRestauraPausa`.

**Um terceiro teste meu passava pelo motivo errado, e a mutação o pegou.** Ele
dizia *"o bloqueio de disparo agendado sobrevive ao reinício"* e afirmava
`due_injects() == ()`. Mas o clock reiniciado nasce em `T+00:00:00` — nenhum
inject vence nele, pausado ou não. A asserção teria continuado verde com o
bloqueio removido.

Trocado por `test_a_posicao_do_exercicio_NAO_e_restaurada`, que afirma **o
limite**: o reinício restaura a pausa e não a posição. Mesma forma de
`test_truncar_a_cauda_NAO_e_detectado` no store — se um dia a posição passar a
ser restaurada, o teste fica vermelho e alguém atualiza a declaração, em vez de o
limite envelhecer escrito em prosa.

**As duas mutações conferidas:** `restore_pause_state` que lê e não aplica
derruba dois testes; `paused_in` que ignora o `exercise_resumed` derruba outros
dois. Nenhuma delas passa despercebida.

#### O item 7 veio junto, e não por conveniência de arquivo

`$defs/frozen_interval` fecha a **P2-4**, e o argumento está lá. O que vale
registrar aqui é a ordem: o campo só podia ser escrito depois de existir o
consumidor que diz quais chaves ele exige — foi o que a P2-4 dizia desde o
início, e é por isso que ela não foi antecipada para o `spec-change`.

**O `technical_failure` deixou de recusar.** A recusa existia para o item 7 não
passar por fechado enquanto o campo não existia; com o campo, ela vira o
contrário — o que sobra é o engine derivar os extremos e gravá-los.

### 3.10 O `RANDOM_SEED`, e por que ele não ganhou consumidor nesta fase

Item 2 da DoD: *"lido de `.env` **por código do `range-core`**, não por
atestação"*. **O contraste do item não é entre variável de ambiente e arquivo —
é entre código e afirmação.** Até aqui o seed existia em `.env.example` e em
cinco lugares da spec, e nada no repositório o lia.

`range-core/determinism.py`. Módulo na raiz do core, e não dentro de um
consumidor: o seed atravessa `evidence/` (Fase 9), o seed de dataset (que é de
adapter, Fase 5) e a geração de senha de `05` §8 — guardá-lo dentro de um dos
três faria os outros dois importarem de um lugar que não os descreve. Módulo na
raiz não acrescenta diretório, então não contradiz o layout que `01` §2 fixa.

**Esta fase não consome o seed, e isso está dito em vez de disfarçado.**
`event_id` sai de `secrets` (§3.4), e nenhuma peça da Fase 2 sorteia nada.
Inventar um consumidor para justificar o item seria pior que a atestação que ele
proíbe. O que está entregue é o caminho de leitura existindo e **verificado**,
com os consumidores datados.

**Ambiente vence `.env`, e `dotenv_path` é parâmetro.** Em container as
variáveis chegam pelo ambiente; `.env` é o caso local. E o núcleo não sai
procurando `.env` a partir do CWD — seria a mesma armadilha que a §3.2 mediu com
`contracts`: funciona na raiz do repositório e falha no container, com a falha
aparecendo longe da causa.

**Nenhum teste toca o `.env` real.** `CLAUDE.md` o nega, e o arquivo pode não
existir na máquina que roda a suíte — um teste que dependesse dele seria
intermitente por construção.

#### Mesmo seed não basta, e o código passou a refletir isso

`08` §1: *"geradores independentes divergem semanticamente à primeira mudança de
código **ou de ordem de geração**"*.

Um `random.Random` compartilhado tem exatamente esse defeito: dois geradores
consumindo do mesmo fluxo ficam acoplados pela ordem, e acrescentar um gerador
desloca tudo o que vem depois. `06` T8 exige dataset byte-idêntico entre duas
execuções — com fluxo único, ele passa hoje e falha na Fase 5 por um defeito
plantado aqui, meses antes, em lugar nenhum que a investigação olharia.

`seeded_random(escopo)` deriva um fluxo por escopo, e a ordem entre eles deixa de
ser variável. **A derivação não usa `hash()`**: `hash()` de string é salgado por
`PYTHONHASHSEED` e muda entre processos — daria dataset diferente a cada execução
a partir do mesmo seed, que é o oposto exato de T8 e uma falha que só apareceria
em execução separada. SHA-256 aqui é derivação determinista, não segurança.

#### O hook achou uma ambiguidade de desenho, e desta vez não era falso positivo

A primeira versão dos testes usava `academus.alunos` como escopo, e
`.claude/hooks/check_architecture.py` recusou a escrita: literal com forma de
flag.

**Estava certo, e por um motivo melhor que o que ele checa.** `<adapter>.<nome>`
é a forma que `01` §5.1 normatiza para flag, e `tools/check_contract_literals.py`
recusa literal com essa forma que não esteja declarado — justamente porque é a
assinatura de um erro de digitação de flag. Um escopo de seed que se parece com
flag é ambiguidade de **desenho**, não inconveniência de ferramenta.

Os escopos passaram a ser `dataset/alunos`, `evidence/vpn`. É a terceira
ocorrência da P23 em código nesta fase, e a primeira em que o bloqueio apontava
para algo que valia mudar — as outras duas custaram uma reescrita de prosa cada.

---

## 4. Itens da Definition of Done

Da `07` Fase 2, **na forma que os três `spec-change` desta fase deixaram**: E1 e
E2 no `a3aded5`, o item 8 no `item-8-volume-de-4h`. O `exercise-resumed` não
tocou esta lista — ele criou evento, não item.

> **Esta abertura dizia *"nenhum item iniciado"* e descrevia uma coluna
> *"o que mudou"* que a tabela não tem.** As duas eram verdadeiras quando foram
> escritas, no primeiro dia da fase, e sobreviveram a nove itens fechados. É a
> §1.6 dentro do documento que a nomeia — e apareceu ao reler a tabela para o
> checkpoint, que é tarde: quem a lesse antes teria lido "nenhum item iniciado"
> embaixo de nove ✅.

**A quarta coluna nomeia a fonte, e é ela que o checkpoint confere.** Atestação
sem fonte é o que esta fase registrou como caro; a tabela existe para que
"passa" e "aqui está a prova" sejam a mesma frase.

| | Item | Status | Verificado contra o quê |
|---|---|---|---|
| 1 | As quatro marcas em todo evento | ✅ | `test_event_store.Carimbo.test_append_carimba_as_quatro_marcas_do_clock` — as quatro vêm de **uma** leitura. `…test_o_produtor_nao_tem_onde_escrever_tempo` — `EventDraft` não tem os seis campos que o store atribui |
| 2 | `RANDOM_SEED` lido por código do `range-core` | ✅ | `range-core/determinism.py`, com `tests/test_determinism.py`. As duas fontes — ambiente e arquivo no formato `.env` — e as três recusas: ausente, vazio, não-inteiro. Continua valendo que **não** é aqui que ele é consumido: `event_id` usa `secrets`, e os consumidores têm data. Ver a §3.10 |
| 3 | PAUSAR congela o clock e bloqueia disparo agendado | ✅ | **Congela**: `test_exercise_clock.Pausar.test_durante_a_pausa_o_exercicio_congela_e_a_parede_avanca` e `…test_as_duas_marcas_de_exercicio_congelam_JUNTAS`, que é a norma que o `a3aded5` acrescentou ao `01` §3. **Bloqueia disparo agendado**: `test_inject_engine.PausaBloqueiaAgendado`, e a **construção** é a prova — o tempo passa do `t_relative` ANTES da pausa, `…test_o_atraso_existe_antes_da_pausa` afirma que o inject está em atraso naquele instante, e `…test_a_posicao_nao_muda_ao_pausar` fecha a outra causa possível. Sobra `is_paused` como única diferença |
| 4 | Aplicar A01 duas vezes produz projeção idêntica | ✅ | `test_simulation_state.Propriedades.test_p3_reaplicar_o_mesmo_inject_nao_muda_o_estado`, com 2, 3 e 7 repetições. Prova negativa: a mutação *"defaults removidos"* e a *"limite do intervalo movido"* o derrubam, em `test_simulation_state_probes` |
| 5 | Rollback grava, incrementa epoch, reconstrói sem apagar | ✅ | Três metades, três fontes. **Grava**: `test_event_store_postgres.StoreEmPostgres.test_rollback_persistido_reconstroi_sem_apagar`. **Incrementa**: `test_event_store.Carimbo.test_epoch_atribuida_e_a_contagem_de_rollbacks`. **Sem apagar**: o mesmo teste de Postgres afirma 3 linhas na tabela depois do rollback |
| 6 | `participant_action` da epoch anterior legível e marcada | ✅ | **Legível**: `test_simulation_state.Propriedades.test_participant_action_abandonada_permanece_no_fluxo` e `…test_rollback_atravessa_escrita_de_participant_action`. **Marcada**: `simulation_epoch` é coluna `NOT NULL` e é conferido por `_verify_epochs`, cuja ausência é pega pela mutação *"conferência de epoch desligada"*. **Sobrevive ao reinício**: `…test_instancia_nova_sobre_o_mesmo_banco_restaura_a_projecao` |
| 7 | `technical_failure` **registra** os extremos, em `exercise_timestamp` | ✅ | `$defs/frozen_interval` no contrato, com quatro fixtures negativas. `test_inject_engine.Rollback.test_technical_failure_registra_os_extremos_do_intervalo` prova o registro; `…test_os_outros_motivos_NAO_carregam_intervalo` prova que é só deste motivo; `…test_congelamento_contido_numa_pausa_registra_ZERO` prova o caso que `06` T3 nomeia — e é ele que fica vermelho se alguém trocar o campo por `wall_timestamp` |
| 8 | Curva **volume → tempo** medida, com ponto de quebra e máquina, data e stack declaradas | ✅ | §3.8: 50 mil a 200 mil eventos, nas formas realista e patológica, com o ponto de quebra em ~150 mil (2,874 s) e o estouro em 200 mil (4,304 s). Data, máquina e stack impressos pelo próprio `scripts/bench_reconstruction.py`, e não anotados à mão. **A forma do item é a do `spec-change` `item-8-volume-de-4h`**, mergeado em 16/08/2026; o critério de 4 h passou a ser cobrado da Fase 7 (T12) e da Fase 9 (T13) |
| 9 | Flag não declarada impede boot com mensagem clara | ✅ | `test_pack_loader.FlagNaoDeclarada`, em quatro asserções separadas porque `06` T2 exige **duas** metades: `…test_impede_o_boot` (recusa, com sítio próprio), `…test_a_mensagem_nomeia_a_flag`, `…test_a_mensagem_nomeia_o_arquivo_esperado` e `…test_vale_para_required_flags_do_manifesto`. `…test_objetivo_inexistente_e_violacao_de_regra_e_nao_de_flag` discrimina o sítio — sem ele, `UNDECLARED_FLAG` poderia estar sendo devolvido para qualquer violação |

**Nove de nove.** Cada ✅ nomeia a fonte que o prova — atestação sem fonte é o
que esta fase já registrou como caro, e é o que o checkpoint vai conferir linha a
linha.

**O item 8 fecha na forma nova, e a distinção importa:** o que a Fase 2 prova é a
curva, não o critério de 4 h. O critério não foi enfraquecido — foi para as fases
que têm o insumo, com item de DoD e critério de aceitação próprios em cada uma.
Ver a §3.12.

Os itens 4, 5 e 6 ganharam uma **segunda** fonte na peça do engine, e não é
redundância: eles estavam provados no fold, que é onde a propriedade vive, e
passam a estar provados **pela porta por onde um facilitador de fato os
executa** — `test_inject_engine.Idempotencia`, `…Rollback.test_grava_incrementa_epoch_e_nao_apaga`
e `…Rollback.test_a_decisao_da_epoch_abandonada_continua_legivel_e_marcada`.

O item 7 é o único cujo cumprimento depende de contrato que ainda não existe: o
campo de payload que carrega os extremos é a **P2-4**.

---

## 5. Pendências

| Id | O que é | Vencimento |
|---|---|---|
| P2-1 | Propriedade entre projeções: abandono lido só pelo motivo declarado | **Fase 6** |
| P2-2 | ~~AST sobre a superfície de leitura do store~~ | **FECHADA** — `scripts/check_store_read_surface.py` |
| P2-3 | ~~Spec-change com os itens do checkpoint~~ | **FECHADA** em 15/08/2026, `a3aded5` |
| P2-4 | ~~Campo de payload dos extremos do intervalo congelado~~ | **FECHADA** — `$defs/frozen_interval` |
| P2-5 | `00` §5.6 enumera duas das quatro marcas temporais | Antes da Fase 3, junto da P37 |
| P2-6 | Sem forma declarativa de ligar `participant_action` a flag; a `01` §4.4 depende dela | **Fase 8** — movida em 16/08/2026, premissa original falsa |
| P2-9 | A frase do mecanismo na `01` §4.4 envelheceu — `spec-change` | Sem prazo amarrado à Fase 3 |
| P2-10 | ~~Medir o item 8 antes de construir em cima do fold~~ | **FECHADA** — medida em 15/08/2026, §3.8 |
| P2-11 | `append` abre uma conexão por chamada | **Fase 9**, com o item 8 e pela mesma causa |
| P2-12 | ~~`AuroraChecker._valida` engole exceção e devolve `False`~~ | **FECHADA** — `tests/test_contract_rules.py` |
| P2-13 | ~~O store não responde "o exercício está pausado agora?"~~ | **FECHADA** — `exercise_resumed`, nas duas metades |
| P2-14 | ~~O engine não tem prova negativa por mutação, como o fold tem~~ | **FECHADA** — `tests/mutation_harness.py` + dois `*_probes.py` |
| P2-15 | ~~Nada guarda o que o core importa de `contracts/`~~ | **FECHADA** — `scripts/check_core_contract_imports.py` |
| P2-16 | O worktree de auditoria resolve `main` para o ref LOCAL, que pode estar atrás | **Antes do próximo checkpoint** — Fase 3 |
| P2-17 | O `start` do intervalo congelado vem da âncora, não do inject falho | **Fase 6**, com o cálculo do desconto |
| P2-18 | O harness de mutação escreve fora do worktree de auditoria | **Antes do próximo checkpoint** — Fase 3 |
| P2-19 | O auditor não confirma que o CI está verde no commit que audita | **Fase 3**, junto da P2-16 |
| P2-7 | Exemplo de `09` §1.1 com `simulation_epoch: 1` e aritmética de epoch única | Sem prazo — candidato, não defeito |
| P2-8 | Retenção do pack por conteúdo, para reconstruir exercício passado | **Fase 10**, com item de DoD próprio |

#### P2-1 — propriedade entre projeções

**O que falta.** Verificar que `metrics`, `objective_evidence`, `calibration` e
`aar_timeline` leem epoch abandonada **apenas pelo motivo declarado** em
`09` §3.1, e não por herança do caminho de leitura.

**Por que não agora.** A propriedade é *entre* projeções e hoje existem zero. A
Fase 2 cria a primeira. O teste só é escrevível quando existir a segunda.

**Vencimento: Fase 6**, quando `metrics` e `objective_evidence` nascem.

**O que segura até lá:** as camadas (a) e (b) da §1.9, mais a assinatura que
impede a projeção de consultar o store.

#### P2-2 — superfície de leitura do store — **FECHADA**

`scripts/check_store_read_surface.py`, com prova negativa em
`scripts/check_store_read_surface_probes.py`. Job `arquitetura`.

**A forma mudou por causa do adiamento, e é o argumento de tê-lo feito.** A
pendência dizia "verificar que as funções públicas de leitura não aceitam
parâmetro de filtragem por epoch, abandono ou ponto de corte" — uma lista de
vocabulário proibido. Escrevê-la antes da API seria a D6: `since`, `after`,
`cursor`, e a próxima palavra não estaria na lista.

Com a superfície desenhada, a afirmação forte passou a ser possível: `read_all()`
**não tem parâmetro nenhum**. Não há palavra a proibir porque não há onde
escrever palavra. E a checagem afirma a **superfície inteira** — o conjunto de
métodos públicos precisa ser exatamente o declarado —, que é whitelist e não
blocklist: `read_since(cursor)` reprova por ser novo, sem que ninguém tenha
previsto a palavra.

**Foi o desenho mínimo que tornou a verificação forte, e não o contrário.** A
tentação futura é acrescentar um método "só de leitura", inofensivo em si, sem
perceber que ele derruba a asserção — está dito na docstring de `EventStore`.

Quatro violações plantadas, quatro reprovadas, em cópia temporária e nunca na
árvore.

#### P2-3 — spec-change — **FECHADA**

Mergeada em 15/08/2026 como `a3aded5`, PR #21, quatro checks verdes.

**Foi aberta com quatro itens e fechou com nove.** Os quatro decididos: E1
(§1.1), E2 (§1.2), o resíduo em `01` §4 (§1.8) e a linha normativa em `01` §4.1
(§1.9 camada a). Os cinco que se juntaram a eles **não foram escopo novo** — são
a mesma exigência nos outros lugares onde ela vivia, e cada um teria deixado a
spec pior se ficasse de fora:

| | O que era | Por que não dava para deixar |
|---|---|---|
| `06` T3 | trazia a exigência do item 7 **com as mesmas palavras**, etiquetada Fase 2 | Corrigir só o `07` criaria conflito entre dois não-master no PR que existe para resolver um |
| `06` T10 + DoD Fase 6 | o cálculo não tinha destino | Sem eles o E1 não moveria o requisito: **apagaria** |
| `06` T14 + DoD Fase 10 | `rehearsal` era **duas** exigências tratadas como uma | `09` §3.1 lhe dá dois efeitos, e eles são de fases diferentes |
| `06` T4 | listava três das quatro marcas | É o critério que **julga** o item que o E2 corrige |
| `01` §3 | a semântica de `exercise_timestamp` não estava enunciada | T3 passou a exigir os extremos nesse campo; exigência apoiada em propriedade não enunciada é a classe que o PR conserta |

**A lição de método, que é o que sobrevive.** Escalar contra um documento sem
varrer onde mais a exigência vive é meia correção, e a metade que fica produz
contradição nova. A varredura que achou as cinco foi `git grep` contra
`origin/main` com **dois** padrões: o nome do motivo (`technical_failure`) e um
que pega o enunciado sem o nome (`congel|desconta|intervalo`). O segundo é o que
encontrou `03` §3.5, que nenhuma auditoria reportou — e foi ele que deu apoio
documental à Fase 6 como casa do cálculo, via o mapa de `00` §7, em vez de só
coerência.

**Três auditorias do `spec-guardian`, uma por mudança de escopo** — quatro
itens, seis, nove. A segunda achou dois BLOCKERs reais, e os dois teriam
mergeado: `06` T3 contradizendo o `07` já corrigido, e a cláusula de forma
apontando para `exercise_time`, que rebobina.

#### P2-4 — campo de payload dos extremos do intervalo congelado — **FECHADA**

`$defs/frozen_interval` e `$defs/rollback_payload` em
`contracts/events.schema.yaml`, com um exemplo positivo e **quatro** fixtures
negativas. Fecha o **item 7** da DoD.

**O nome e o tipo, que eram o que estava aberto:** `frozen_interval`, objeto com
`start` e `end`, ambos strings na forma de `exercise_timestamp` — e **sem
`pattern`**, porque o `exercise_timestamp` do envelope também não tem. Inventar
aqui um formato que o campo de origem não exige seria cobrar da cópia mais que do
original.

**Fechado por `additionalProperties: false`**, ao contrário do `payload`
genérico: a lista de chaves é conhecida e pequena, e chave nova sem contrato é
erro de digitação que em runtime vira campo que ninguém lê.

**Os extremos são derivados, não recebidos.** `start` é o `exercise_timestamp`
da âncora; `end` é o de agora. Extremo passado por parâmetro é extremo que o
chamador pode errar — e errar aqui **não falha**: produz número plausível que só
vira métrica errada na Fase 6, que é exatamente o que `06` T3 descreve sobre as
três formas erradas.

**O caso zero sai de graça, e é normativo.** `06` T3: *"um congelamento
inteiramente contido numa pausa registra ZERO"*. Sai sozinho, porque
`exercise_timestamp` não avança durante o PAUSAR — não há caso especial no engine
para produzi-lo, e há teste que o afirma.

**Duas fixtures onde a primeira tentativa foi uma.** A negativa de *"duração em
vez de extremos"* carregava **três** defeitos — chave fora do contrato, `start`
ausente e `end` ausente — e o executor a reprovou pela regra do um-defeito-por-
fixture. Separadas, cada uma prova metade da forma: que os dois extremos são
exigidos, e que duração não entra ao lado deles.

**O resíduo, declarado: este é o primeiro schema de payload por `event_type`, e
por enquanto o único.** O `payload` dos outros 32 tipos continua aberto. Fechar
todos agora seria escrever 32 contratos sem consumidor — e cada um nasce quando o
seu nasce. Este nasceu porque tem dois: o fold exige `to_event_id`, e o item 7
exige o intervalo. **Não vira pendência**: é regra declarada no próprio contrato,
com gatilho — o consumidor.

---

O texto abaixo é o registro de quando a pendência estava aberta.

**O que faltava.** `contracts/events.schema.yaml` deixa `payload` aberto
(`type: object`, sem schema por `event_type`), declarando que os schemas chegam
nesta fase. O item 7 da DoD pressupõe um campo concreto, e ele não existe — nem
no `x-aurora-registry`, nem no exemplo de `rollback_performed` de `01` §4.2, que
lista só `to_inject_id`, `by_user`, `role` e `reason`.

**A forma já está decidida e não é pendência:** extremos, nunca duração; em
`exercise_timestamp`, nunca em `exercise_time` nem em `wall_timestamp`. Está
normatizada em `06` T3 pelo `a3aded5`. Aberto é só o nome e o tipo do campo.

**Por que não veio no spec-change.** Contrato é código, e `CLAUDE.md` proíbe
spec e código no mesmo PR.

**Vencimento: dentro da Fase 2**, no PR de código, junto dos schemas de payload
por `event_type`.

**A lista de chaves saiu do fold, e é por isso que ela está aqui.** Escrever o
corpo de `project` obrigou a nomear as chaves que ele exige, e elas viraram
constantes em `range-core/state/simulation_state.py`. São **contrato de facto
hoje**: o fold recusa sem elas, e nada as valida.

| Chave | Em que evento | Para quê |
|---|---|---|
| `pack_id`, `pack_schema_version`, `pack_content_hash`, `pack_canonicalization` | `exercise_started` | o pino do pack |
| `to_event_id` | `rollback_performed` | âncora do corte, ao lado do `to_inject_id` que `01` §4.2 exige |
| `option_id` | `decision_made` | resolver os effects da opção; o inject vem de `correlation.inject_id` |

Anotado aqui porque o schema não pode ser escrito por quem não sabe quais chaves
o consumidor exige — seria contrato desenhado sem o seu único cliente.

#### P2-5 — `00` §5.6 enumera duas das quatro marcas

`00_MASTER_SPEC.md` §5.6 se chama "Dois relógios, sempre" e enumera
`exercise_time` e `wall_timestamp` mais `clock_multiplier`, omitindo
`exercise_timestamp` — que `01` §3 exige, `09` §1.1 lista como obrigatória e o
`required` do contrato cobra.

**Conferido que não é contradição, e o argumento importa:** o texto não diz
"apenas" nem "somente", então é afirmação existencial e não enumeração fechada.
E `00` conta **relógios**, que são dois, enquanto `01` conta **marcas**, que são
três — o exercise-clock produz duas. O `a3aded5` reforça essa leitura ao
declarar `exercise_timestamp` marca do exercise-clock, em vez de um terceiro
relógio.

**Por isso é cosmética, e por isso não foi escalação.** O MASTER não afirma nada
sobre `exercise_timestamp`, e silêncio não é contradição.

**Vencimento: antes da Fase 3**, junto da P37.

#### P2-6 — sem forma declarativa de ligar `participant_action` a flag

`effects` existe em `inject` e em `option` de `decision_point` (`04` §5). Não há
como ligar um `event_type` de `participant_action` — os cinco `state_effect` —
a uma flag.

**A §4.4 do `01` depende desta pendência**, e a dependência só apareceu ao
tentar escrever o teste dela. Sob a quarta leitura, serviço nenhum escreve flag:
o fold resolve effects contra o pack. Sem ligação declarativa,
`vpn_access_revoked` não move flag nenhuma, e a §4.4 descreve mudança de estado
sem caminho reconstruível — o que contraria `01` §4.1, porque estado que não vem
do fold não sobrevive à reconstrução do zero.

**Por que não decidir agora.** Desenhar a ligação antes de a API existir é
inventar vocabulário para prever o módulo — classe da D6, já paga nesta fase. E
`vpn_access_revoked` é produzido por serviço que nasce na Fase 3: o valor de
esperar é o consumidor nascer junto do contrato.

**O que segura até lá:** `tests/test_simulation_state.py` prova a tese da §4.4
na classe `declaration`, com `decision_made` — a flag reverte e o evento
permanece no fluxo. Falta a classe `state_effect`, e o teste diz isso na própria
docstring.

**Vencimento: Fase 8** — movido em 16/08/2026, e o motivo é que **a premissa
original era falsa**.

> Esta pendência dizia: *"`vpn_access_revoked` é produzido por serviço que nasce
> na **Fase 3**: o valor de esperar é o consumidor nascer junto do contrato"*.
> Conferido em `07`: o `federated-identity-simulator` é da **Fase 11**, e
> **nenhum** dos cinco `state_effect` de `participant_action` é entregável da
> Fase 3 — que emite `audit_query_performed`, de classe `observation`.
>
> **A afirmação atravessou três camadas sem ninguém conferir na fonte:** nasceu
> aqui, foi repetida em `01` §4.4 pelo `spec-change` da P2-9, e foi repetida na
> instrução que abriu a Fase 3. Cada camada confiou na anterior — a §1.5 na forma
> que não parece §1.5 em nenhum ponto isolado, porque em cada um havia uma fonte
> aparente.
>
> **O destino certo é a Fase 8**, pela mesma regra que realocou o item 8: a fase
> que decide é a que tem o insumo. O item de DoD dela — *"as sete ações de
> continuidade aplicam efeito mecânico e custo"* — **obriga** a ligação, porque
> `continuity_action_taken` é um dos cinco. A Fase 11 é o caso concreto que
> `01` §4.4 usa, e chega três fases depois do primeiro consumidor.
>
> A frase errada em `01` §4.4 foi corrigida em `spec-change`
> `quem-traz-o-consumidor-da-ligacao`.

#### P2-9 — a frase do mecanismo na `01` §4.4 envelheceu

**É a §1.6 acontecendo dentro da spec, produzida por duas decisões deste mesmo
ciclo.** A §4.4 diz *"o serviço que atende a rota escreve
`academus.federated_session_active`"*. Era verdadeiro quando foi escrito, no
spec-change `a3aded5`. A **quarta leitura** — effects resolvidos contra o pack,
decidida depois, no desenho do fold — derrubou a frase: serviço nenhum escreve
flag.

Não houve momento em que alguém errou. A primeira decisão estava certa contra o
que se sabia; a segunda foi aprovada sem que se visse que derrubava a primeira.
É a classe que a §1.6 da Fase 1 nomeia — a afirmação que envelhece depois de
correta —, aqui com as duas decisões nomeadas, em vez de descoberta três fases
adiante.

**O que morreu é só a frase do caminho.** A tese da §4.4 continua inteira, e
nada nela dependia de quem escreve a flag:

- rollback reverte a flag e não reverte o efeito de domínio;
- a exposição é estrutural, e não escolha de autoria de cenário;
- o resíduo é maior nos dois `event_type` de efeito externo;
- o participante pode ver o mundo simulado contradizer a própria ação, e isso é
  desenho, não defeito.

**Não é a mesma pendência que a P2-6, e por isso são duas.** A Fase 3 entrega a
ligação declarativa; corrigir a frase é `spec-change`, e continua necessário
depois de a ligação existir — a frase descreveria o mecanismo errado de todo
jeito.

**Sem prazo amarrado à Fase 3:** pode ir antes, sozinha, ou junto do
spec-change que a ligação declarativa vier a exigir.

#### P2-10 — medição do item 8 — **FECHADA**

Medida em 15/08/2026, antes de qualquer coisa ser construída em cima do fold,
que era a ordem que a pendência fixava. Números, formas e envelope na **§3.8**.

**O resultado desarma a preocupação que abriu a pendência.** Ela existia porque
o fold recomputa do zero e a máscara é O(n) por rollback: se a medição obrigasse
a trocar a estratégia, mexeria numa decisão com seis propriedades e oito
mutações apoiadas nela. **O fold é 3% do orçamento.** A estratégia de
recomputação não é o risco, e pode ser construída em cima sem reserva.

#### P2-11 — `append` abre uma conexão por chamada

`PostgresEventStore._persist` faz `psycopg.connect` a cada evento. Custa
milissegundos por append, e a Fase 2 grava **a ritmo de facilitador** — dezenas
de eventos por hora —, então não é problema agora.

**Mas "agora" é datado, e a data tem nome.** A Fase 9 traz `telemetry_emitted`,
que é justamente a fonte que a §3.8 nomeia como quem reabre o item 8 — e
telemetria **não grava a ritmo de facilitador**. Leitura e escrita reabrem
juntas, pela mesma causa: volume.

**Por que isto não pode ficar só como observação no bench.** Quem chegar na
Fase 9 seguindo a §3.8 encontra o problema de **leitura** documentado com número
e curva, e não encontra o de **escrita** — que estará no mesmo caminho, pela
mesma razão, e sem aviso.

**Vencimento: Fase 9**, junto da reavaliação do item 8. A saída provável é
conexão reusada ou pool, mas medir antes de escolher — pela mesma ordem que a
P2-10 fixou e que se mostrou certa: o risco que se supunha não era o que estava
lá.

#### P2-12 — `except Exception` que transformava erro de programação em "regra não disparou" — **FECHADA**

Fechada **antes** de o loader consumir o módulo, que era a ordem que a pendência
fixava. `AuroraChecker._valida` capturava `Exception` e devolvia `False`, e
`False` ali significa *"este ramo não se aplica"* — então todo erro de
programação saía como regra que não disparou, três camadas adiante, apontando
para as fixtures em vez de para a causa.

Estreitado para `referencing.exceptions.Unresolvable`, que é a família que o
bloco de fato pretende tolerar. `jsonschema` embrulha a falha de resolução em
`_WrappedReferencingError`, que **herda** de `Unresolvable` — conferido na versão
pinada, não suposto, e afirmado em teste para a herança não mudar em silêncio.

**A prova negativa é versionada e tem duas metades**, em
`tests/test_contract_rules.py`:

| Classe | O que afirma |
|---|---|
| `ErroDeProgramacaoSobe` | o defeito histórico — o nome que o módulo não importava — **estoura**. Conferido contra o código antigo: com `except Exception` os dois casos ficam vermelhos. São dois porque só `NameError` deixaria passar uma captura estreitada para `except NameError`, que resolve o caso conhecido e nenhum outro |
| `RefIrresolvivel` | a tolerância que sobrou é **percorrida**, e a caminhada continua. Captura que nunca capturou é prosa com sintaxe de código, que é o mesmo defeito do outro lado |
| `Sintoma` | liga a causa ao sintoma: com `_valida` devolvendo `False`, a instância que o baseline reprova não produz violação nenhuma |

Sem a terceira, as duas primeiras provariam que o código faz o que faz, e não que
o que ele fazia antes era defeito.

**Tolerar ali não esconde nada**, e isso também está afirmado: a camada 1 valida
a mesma instância contra o mesmo `$ref` e levanta alto, porque não captura nada.

#### P2-13 — o store não responde "o exercício está pausado agora?"

**A primeira redação desta pendência estava mais forte do que a fonte
sustenta, e a correção é a pendência.** Ela dizia *"a duração de uma pausa não é
reconstruível a partir do fluxo"*. Falso: é reconstruível, e foi medido. O que
não é reconstruível é outra coisa, mais estreita e mais séria.

##### Conferido na fonte: o catálogo não tem como expressar retomada

`contracts/events.schema.yaml`, `$defs/event_type_facilitation` — enumeração
completa, seis valores:

```yaml
inject_fired, rollback_performed, branch_selected,
exercise_started, exercise_paused, exercise_reset
```

`09` §4.1 traz os mesmos seis, e o documento declara o catálogo **registro
fechado**. Não há `exercise_resumed` nem equivalente.

**A assimetria também está na spec, e não só no contrato.** `01` §6 dá ao
gm-console *"PAUSAR / CONTINUAR / ROLLBACK / RESET"* — quatro ações —, e o
catálogo tem evento para três delas. `03` §6 lista o papel `facilitador` com
*"PAUSAR / ROLLBACK / RESET"*, e nem cita CONTINUAR. Nenhum documento justifica a
ausência; ela tem a forma de omissão, não de desenho.

##### O que É reconstruível, e a conta está medida

Entre o `exercise_paused` e o evento seguinte:

```text
pausa em tempo de parede = Δwall − Δexercise / clock_multiplier
```

Medido com um caso de 5 min correndo, 10 min pausado e 2 min correndo: Δwall
720 s, Δexercise 120 s, multiplicador 1 → **600 s**, que é o valor real.

Funciona porque `exercise_timestamp` congela na pausa e `wall_timestamp` não —
`01` §3 e `06` T4. **Duas condições:** existir um evento posterior, e o
`clock_multiplier` ser o mesmo nos dois extremos (o envelope grava o valor por
evento, então uma troca no meio do intervalo é invisível na ordem).

##### O que NÃO é reconstruível, e é isso que importa

**Se o exercício está pausado neste momento.** Dois estados distintos produzem
exatamente o mesmo fluxo:

| Fluxo | Realidade |
|---|---|
| `exercise_paused`, nada depois | ainda pausado |
| `exercise_paused`, nada depois | retomado, e nada aconteceu desde então |

E a heurística que salvaria o caso — *"evento depois do `exercise_paused` implica
retomada"* — **não vale**, e não por acidente: `01` §3 bloqueia o disparo
**agendado** durante a pausa, e `01` §6 mantém o disparo **manual**, que esta
fase implementou. Verificado: um `inject_fired` manual durante a pausa produz
evento posterior com o exercício ainda pausado.

##### Onde isso cobra, e por que não é a Fase 10

Não é o AAR — a timeline renderiza pausas com a derivação acima. **É a Fase 4**,
cujo item de DoD diz *"reinício do container do engine restaura o exercício a
partir do event store"*, e `06` T3 acrescenta *"reinício do processo restaura a
projeção corrente sem intervenção"*.

Um engine que reinicia lê o store e não sabe se deve subir pausado. **Ele vai
acertar ou errar sem ter como saber qual** — e o erro é operacionalmente caro nos
dois sentidos: subir correndo um exercício que o facilitador pausou dispara
inject agendado numa sala parada; subir pausado um exercício em curso congela a
sala sem que ninguém tenha pedido.

**Também não encosta no item 3 nem no item 8, e vale dizer:** o item 3 é sobre o
clock vivo e o agendador, que não leem o store; e o fold de `simulation_state`
ignora `exercise_paused` inteiramente — a reconstrução do item 8 não depende
disto em nada.

##### As três saídas, e por que duas são piores que a pendência

| | Saída | Custo |
|---|---|---|
| **(a)** | `exercise_resumed` no catálogo | **`spec-change`** — `09` §4.1 é normativo e o registro é fechado. Acrescentar sem ele violaria o invariante 3, que é o gate por AST |
| **(b)** | discriminante no payload de `exercise_paused` | Sem `spec-change`, porque o payload é aberto. **Mas faz o catálogo mentir:** o tipo passaria a significar "o estado de pausa mudou", e todo consumidor que filtra por `exercise_paused` — AAR, métricas — contaria retomada como pausa. É a semântica de uma entrada de registro fechado mudando sem que o registro mude |
| **(c)** | aceitar, e restaurar o estado de pausa de outra fonte | Contradiz o item da Fase 4 na letra: *"a partir do event store"*. E abriria estado de exercício fora do store, que é o que `01` §4.1 fecha |

**A decisão é do operador**, e não minha: é o **segundo `spec-change` desta
fase**, e o argumento está acima em vez de a consequência aparecer depois. O
primeiro (`a3aded5`) corrigiu itens insatisfazíveis por construção; este tem a
mesma forma — um item de DoD da Fase 4 que o catálogo atual não permite
satisfazer —, mas descoberto **duas fases antes** de a fase que o cobra existir.

##### Decidida em 16/08/2026: saída (a)

Branch `spec-change/exercise-resumed`, a partir de `origin/main`. **Cinco sítios
em `docs/spec/`**, e a varredura que os achou está na §5.1 abaixo.

**O que o evento carrega ficou decidido no próprio `spec-change`, e não depois:
nada além do envelope.** A duração da pausa é a distância entre os
`wall_timestamp` dos dois eventos — extremos, nunca duração, que é a forma que
`06` T3 já fixou. Em `wall_timestamp` e não em `exercise_timestamp` porque as
duas marcas de exercício congelam na pausa e mediriam zero: espelho exato de T3,
que escolheu `exercise_timestamp` justamente por ele **excluir** a pausa.

**Isso desarma a preocupação que abriu a decisão.** Trocar o multiplicador
durante a pausa **é permitido** — conferido no clock — e quebra a derivação por
subtração: numa pausa de 660 s com troca no meio, `Δwall − Δexercise/mult`
devolve 420 s pelo multiplicador do extremo esquerdo. Com o evento, a conta
some. O evento não existe para carregar a duração; existe para que não haja
conta — e é por isso que a norma **não depende de campo que o contrato ainda não
tem**, que era o risco de repetir a P2-4.

**A metade de contrato fechou em 16/08/2026, depois do merge do `spec-change`**:
enum de `event_type_facilitation`, entrada em `x-aurora-registry.effect_class`,
constantes geradas em Python e TypeScript, emissão em `InjectEngine.resume`,
`paused_in`, `restore_pause_state` e os testes. **A divergência entre os dois
catálogos durou um merge**, e enquanto durou esteve escrita aqui — que era o
ponto, porque o CI não a cruza: a tabela de `09` §4.1 é markdown e nenhum
verificador a lê.

**A P2-13 está fechada.** Ver a §3.11.

##### 5.1 A varredura, com os critérios

Quatro padrões, porque escalar contra um documento sem varrer onde mais a
exigência vive é meia correção — a lição do E1, que custou nove alterações:

| | Padrão | O que ele pega que os outros não pegam |
|---|---|---|
| **P1** | `pausar\|continuar\|retomar\|retomad` | o comando pelo nome, em prosa |
| **P2** | `exercise_*\|inject_fired\|rollback_performed` | o `event_type`, sem a palavra |
| **P3** | `rein[íi]cio\|reiniciar\|restaura` | a exigência sem nenhum dos dois nomes |
| **P4** | `start/pause\|disparo de inject\|máquina de exerc` | **enumerações dos atos** |

**O P4 foi o que pagou.** Ele achou `00` §3.1 — no MASTER —, que enumera
*"disparo de inject, rollback, seleção de branch, start/pause/reset"*. Nenhum dos
outros três a encontraria: ela não usa PAUSAR, não cita `event_type` e não fala
de reinício. Era a enumeração que ficaria obsoleta em silêncio, no documento de
maior autoridade.

**Dois sítios conferidos e deliberadamente não alterados**, porque não alterar
também é decisão:

- `01` §4, tabela de camadas — *"Facilitation Audit: disparos, rollbacks, motivo,
  papel"* é ilustrativo e já não citava `exercise_paused`. Não fica obsoleto por
  esta mudança.
- `03` §7, última linha — *"todo disparo e rollback registram autor, papel,
  motivo e epoch"*. Estender para pausa e retomada criaria norma sobre campo de
  payload que o contrato não tem: a P2-4 outra vez, com outro nome.

##### O erro de leitura que quase entrou no commit, e como ele foi pego

A primeira mensagem do commit afirmava que `main` local carregava um commit
**não empurrado** que tocaria `bootstrap.sh`, `scripts/` e `user-scope/`, e que a
branch saía de `origin/main` por isso.

**Era falso.** `main` local está **dois commits atrás** de `origin/main`, e nada
só nele. A afirmação nasceu de ler a saída de dois comandos como se fosse de um:
`git log origin/main..main` não imprimiu nada, e a linha seguinte — cabeçalho do
`git show` que veio depois — foi lida como resultado dele.

Pego pelo `git reflog show origin/main`, que mostrou `origin/main` já em
`a3aded5` nas duas leituras: **não houve corrida com o operador**, houve leitura
errada. A mensagem foi corrigida antes do push.

**A decisão de sair de `origin/main` continua certa, por outro motivo e mais
forte:** `main` local não tem o `a3aded5`, que é o `spec-change` anterior. Sair
dele teria produzido as edições contra o texto antigo, e o diff do PR reverteria
aquele PR junto.

**A classe é a mesma da §6.1** — número lembrado de outro conjunto —, aqui como
**linha atribuída ao comando errado**. Regra que ela ensina: comando cuja saída
decide alguma coisa roda sozinho, ou com separador entre as saídas.

**Vencimento: antes da Fase 4.** Não bloqueia a Fase 2: nenhum item desta fase
depende dele, e o engine já não emite nada em `resume`.

#### P2-14 — prova negativa por mutação do engine e do loader — **FECHADA**

`tests/mutation_harness.py` extraído, com `test_inject_engine_probes.py` (nove
mutações) e `test_pack_loader_probes.py` (sete). **Dezesseis mutações novas, mais
as oito do fold.**

**A extração foi conferida pelo que ela mede, e não por a suíte continuar
verde.** As oito mutações do fold foram rodadas antes e depois, com os conjuntos
vermelhos capturados e comparados um a um: **9 de 9 idênticos**, contando a
âncora sem mutação. Suíte verde depois de uma extração não prova nada sobre uma
prova negativa — o que prova é o conjunto que cada mutação derruba continuar
sendo o mesmo.

##### As mutações miram o comportamento POSITIVO, e o motivo

As recusas já discriminavam por **sítio**. O que a construção não garantia era o
outro lado: que o engine **faça** o que deve. Afirmação positiva passa por
acidente com muito mais facilidade que recusa — só um caminho precisa dar certo,
e há vários jeitos de ele dar certo pelo motivo errado.

**Três testes meus passavam por acidente, e as mutações acharam os três.**

| O que o teste dizia | Por que passava errado |
|---|---|
| *"o bloqueio de agendado sobrevive ao reinício"* | o clock reiniciado nasce em `T+00:00:00`, então **nada** vence nele, com bloqueio ou sem |
| *"a opção escolhida move a flag"* | afirmava só que o estado **mudou** — a opção errada também muda |
| *"o prefixo de caminho na forma canônica"* | trocava **dois** documentos de lugar, e isso muda o hash mesmo sem prefixo |

##### E duas propriedades não tinham teste nenhum

As mutações não derrubaram nada, que é o achado mais valioso que uma prova
negativa produz:

- **`inject_effects` mapeando todos os injects para o primeiro** passava pela
  suíte inteira. Ninguém afirmava o que um inject faz ao estado, só que o estado
  mudou — e reaplicar os effects de A01 não muda nada, então **a idempotência da
  D3 escondia o defeito em vez de expô-lo**. Virou
  `test_o_disparo_aplica_os_effects_DAQUELE_inject`, com o valor esperado vindo
  do pack.
- **`sort_keys=True` na forma canônica** não tinha prova: o teste existente
  comparava dois hashes vindos do **mesmo texto YAML**, onde a ordem de inserção
  já era igual e `sort_keys` não tinha o que fazer.

##### Uma mutação foi descartada, e a razão fica registrada

*"A janela nunca deixa nada vencer"* derruba **vinte e dois** testes: quase todo
`setUp` dispara para chegar ao estado que vai examinar. É mutação grossa pela
definição do próprio harness — mede reação a amputação, não detecção — e o
conjunto declarado precisaria ser refeito a cada teste novo.

**A propriedade não fica descoberta** (um engine que não dispara é visto por
vinte e dois testes de uma vez); o que ela não tem, e não pode ter dada a
estrutura da suíte, é um **discriminante**. Dito em vez de fingido, e no lugar
dela entrou uma cirúrgica sobre a mesma função: a **ordem** de disparo.

##### O custo previsto se confirmou

A pendência dizia: *"a forma certa não é copiar o harness — seriam ~120 linhas
duplicadas, que é a classe D4 —, e sim extrair para um módulo compartilhado. Isso
toca um arquivo já auditado, e misturá-lo com a peça nova daria um sinal só."* Foi
o que se fez, e o commit da extração não tem outro conteúdo.

---

O texto abaixo é o registro de quando a pendência estava aberta.

O fold tinha `tests/test_simulation_state_probes.py`: cada mutação cirúrgica
declara o conjunto exato de testes que deve ficar vermelho. O engine e o loader
não têm equivalente.

**O que segura até lá.** As recusas afirmam **sítio**, e não mensagem, então um
teste que planta um defeito e recebe outra recusa reprova. E a prova do item 3 é
**por construção**: o inject está em atraso no instante da pausa
(`test_o_atraso_existe_antes_da_pausa`) e a pausa não muda a posição
(`test_a_posicao_nao_muda_ao_pausar`), então não sobra outra causa para o
resultado vazio além da consulta a `is_paused`.

**Por que ainda assim é pendência.** Prova por construção depende de a construção
continuar valendo, e nada a verifica. A doutrina desta linhagem é que mecanismo
que nunca ficou vermelho prova que roda, não que detecta.

**Custo declarado:** a forma certa não é copiar o harness — seriam ~120 linhas
duplicadas, que é a classe D4 —, e sim extrair o carregador de fonte mutada para
um módulo compartilhado e fazer os dois probes o usarem. Isso toca um arquivo já
auditado, e misturá-lo com a peça nova daria um sinal só.

**Vencimento: Fase 2, no PR da fase.**

#### P2-15 — o que o core importa de `contracts/` — **FECHADA**

`scripts/check_core_contract_imports.py`, com prova negativa em
`scripts/check_core_contract_imports_probes.py`. Job `arquitetura`.

**O gatilho da §2.1 disparou, conferido:** ela dizia *"vira pendência no dia em
que o core importar de `contracts/` algo que não seja constante gerada"*.
`range-core/engine/loader/contract_source.py:62` faz `import contracts` — o
**pacote**, e não o módulo de constantes — para resolver o diretório pelo
`__path__` e ler os seis `.yaml` em tempo de execução. Os outros três imports do
core continuam sendo `contracts.generated.events`.

**Prazo corrigido para esta fase, e o argumento é do operador:** a guarda está
ausente **agora**, e a superfície que ela cobre acabou de crescer. Adiar para a
Fase 3 deixaria a fase que criou a exposição fechar sem ela.

**Whitelist, não blocklist** — a forma que a P2-2 mostrou ser a certa. Não há
lista de coisas proibidas em `contracts/`, porque a próxima não estaria nela. Há
a lista do que o core de fato importa, **com o motivo de cada entrada**, e a
checagem afirma a igualdade nas duas direções: arquivo que importa e não está
declarado reprova, e entrada declarada cujo arquivo não importa mais também.

A segunda direção é a que impede a lista de envelhecer virando permissão ampla —
**declaração que sobra é permissão que ninguém pediu**, e é o modo de falha de
toda whitelist.

**Seis eixos de prova negativa**, cinco de import plantado — direto, com alias,
dinâmico via `import_module`, relativo que escapa, e arquivo declarado importando
além do declarado — e um de declaração órfã.

**O probe achou um acoplamento na checagem, e ele valia.** A resolução do import
relativo estava ancorada na raiz **deste** repositório; contra a cópia temporária
do probe ela falhava em silêncio, e o probe passava com `rc=0` — lendo "não
detectou" como "não há violação". A raiz virou parâmetro. É o argumento inteiro
de exigir prova negativa: o eixo que ela não provaria era exatamente o que estava
quebrado.

**O limite, declarado:** a checagem vê **import**, não leitura de arquivo. Um
módulo do core que abrisse `contracts/events.schema.yaml` por caminho literal
passaria. Hoje isso não existe — `contract_source` resolve pelo `__path__`, que é
um import —, e a forma de manter assim é esta lista continuar sendo o único
caminho de entrada.

#### P2-16 — o auditor lê `main` local, e `main` local envelhece

**Aberta pela auditoria de 16/08/2026**, como consequência de um achado que era
falso positivo — e o falso positivo é o defeito, não o achado.

**O H1 dizia** que a branch da fase altera `docs/spec/` e código no mesmo diff
contra `main`, e que o PR seria imergível pelo próprio gate. **Não procede**, e o
cálculo do próprio `spec_freeze` é a prova:

| Base | SPEC | CODE | Resultado |
|---|---|---|---|
| `origin/main` — **a base real do PR** | 0 | 26 | passa |
| `main` local | 6 | 27 | reprova |

`origin/main` contém os três `spec-change` (conferido por `merge-base
--is-ancestor`); o `main` local está três commits atrás. O job roda contra
`github.event.pull_request.base.sha`, que é o primeiro.

**O auditor declarou o próprio limite** — *"estado real de `main`: refs remotos
não consultados; concluí a partir de `git log main..HEAD`"* —, e a allowlist dele
já permite `rev-parse` e `for-each-ref`. A informação estava alcançável e não foi
buscada.

**Por que isso vira pendência do mecanismo, e não nota de rodapé.** `WORKFLOW.md`
diz que *bloqueio indevido também é defeito*, e o item 4(e) da P23 trata falso
bloqueio novo como finding. Aqui o custo é maior que um bloqueio: um HIGH
inventado consome a rodada seguinte, e **todo checkpoint futuro cuja branch tenha
mergeado um `spec-change` reproduz o mesmo H1** — porque a branch sempre estará à
frente de um `main` local que ninguém atualizou.

**Destino, e são duas saídas possíveis:**

| | Onde | O que muda |
|---|---|---|
| **(a)** | `scripts/start_checkpoint_audit.sh` | o launcher faz `git fetch origin` e passa `origin/main` como base de comparação ao worktree |
| **(b)** | `user-scope/agents/checkpoint-auditor.md` | o auditor compara contra `origin/main`, e só cai para `main` se não houver remoto |

**(a) é a preferível**, e o argumento é o mesmo que tirou o auditor do
repositório: mecanismo que depende de o auditor lembrar de fazer a coisa certa
não é mecanismo. O launcher já fixa o commit candidato; fixar também a base é a
mesma natureza de decisão.

**Vencimento: antes do próximo checkpoint** — vale dizer, antes da Fase 3
fechar, porque é lá que ele volta a ser exercido.

#### P2-17 — o `start` do intervalo congelado vem da âncora, não do inject falho

**L3 da auditoria de PASS, e não é defeito a corrigir aqui** — é decisão real sem
fase obrigada a reconciliá-la, que é a forma da P2-8.

| | |
|---|---|
| **O que a norma pede** | `09` §3.1: *"relógio de métricas congelado **entre o inject falho e a retomada**"*; `06` T3 repete *"o intervalo vai do inject falho até a retomada"* |
| **O que o código entrega** | `_frozen_interval` devolve `start = ancora.exercise_timestamp` — a âncora é o **último evento que sobrevive** ao corte, e o inject falho é o primeiro **descartado** depois dela |
| **Por que a diferença existe** | a spec **não oferece campo** que identifique o inject falho no fluxo. Derivar da âncora é a única leitura disponível do envelope, e recebê-lo por parâmetro seria extremo que o chamador pode errar — errando sem falhar, que é o que `06` T3 descreve sobre as três formas erradas |

**Quando a diferença aparece:** quando o facilitador rebobina para um ponto
**anterior** ao inject falho — permitido, e não recusado por nada. Aí o intervalo
gravado é mais largo que o da norma, e a Fase 6 descontará tempo de exercício que
correu normalmente.

**A divergência é conservadora** — desconta a mais, nunca a menos —, e por isso
não é BLOCKER nem HIGH. Mas *"conservadora"* é uma propriedade da métrica, não
uma licença: um TTCV inflado por desconto excessivo é um número errado com sinal
conhecido.

**O que a Fase 6 tem de decidir**, que é o destino desta pendência: aceitar a
âncora como aproximação declarada, ou passar a exigir que o `rollback_performed`
de `technical_failure` nomeie o inject falho — o que é campo novo de payload e
portanto `spec-change` mais contrato. **Quem tem o insumo é a Fase 6**: é ela que
calcula o desconto e é ela que descobre se a largura a mais importa.

**Vencimento: Fase 6**, junto do item de DoD do desconto por união.

#### P2-18 — o harness de mutação escreve fora do worktree de auditoria

Levantado pelo próprio auditor, no item 5 do que ele não conseguiu verificar —
**não é finding e não é da fase**: é do aparato.

`tests/mutation_harness.py` usa `tempfile.TemporaryDirectory()` para escrever a
fonte mutada. O diretório é autolimpante e o alvo não é controlável por quem roda
— mas fica **fora do worktree de auditoria**, e o desenho do hook assume que
sujeira incidental de teste *"morre com o worktree temporário"*
(`WORKFLOW.md`).

**Não é escrita deliberada do auditor**, e o hook não a intercepta: ela acontece
dentro de um `python -m unittest` já autorizado. A suposição de contenção é que
fica meio verdadeira.

**Destino:** ou o harness passa a escrever dentro da árvore que está sendo
auditada — o que a torna suja durante a execução, e é pior —, ou o `WORKFLOW.md`
passa a declarar a exceção, que é o que a honestidade do registro pede. **A
segunda**, e por argumento: `tempfile` é o mecanismo certo, e o que está errado é
a frase que promete contenção total.

**Vencimento: antes do próximo checkpoint**, junto da P2-16 — as duas são do
mesmo aparato e cabem no mesmo PR.

#### P2-19 — o auditor não confirma que o CI está verde no commit que audita

Também do item 1 do relatório, e é o limite mais estrutural dos três.

Nove testes de Postgres **pulam** no worktree do auditor, e com eles: a
persistência, o critério de reinício de `06` T3, os três casos de detecção de
reescrita por cadeia de hash, a contiguidade de `sequence` e o caso de dois
escritores concorrentes. O CI cobre tudo isso — sobe Postgres 16.4 pinado por
digest, aplica `alembic upgrade head` e define `AURORA_TEST_DATABASE_URL` —, e o
auditor **leu o workflow e não pôde executá-lo**.

**A consequência é precisa:** metade de dois itens da DoD é verificada por
*leitura e configuração*, não por execução. O repositório declara essa
dependência em `test_event_store.LimiteDoStoreEmMemoria`, o que é o melhor que
esta fase podia fazer — mas o auditor continua emitindo veredito sem ver o gate
que sustenta a parte que ele não roda.

**Destino, e as duas saídas não são equivalentes:**

| | Saída | Custo |
|---|---|---|
| **(a)** | o launcher passa ao auditor a URL de um Postgres efêmero (o mesmo `docker compose` que o projeto já traz) | o auditor passa a executar os nove; exige Docker na máquina de quem audita |
| **(b)** | o auditor consulta o estado do CI para o commit auditado, por `gh run list --commit` | precisa de rede e de `gh` na allowlist — que é ampliar o julgador de novo, e por um caminho que fala com fora |

**Decidida pelo operador: (a).** O auditor sem rede é **propriedade**, não
limitação, e `gh` na allowlist abriria **superfície permanente** para resolver
**dúvida pontual**.

**A consequência é maior que a pendência, e fica dita aqui para ninguém
implementar só a metade que o título nomeia.** O Postgres efêmero não fecha
apenas *"o auditor não vê o CI"*: ele **faz os nove testes pularem de pular**. Com
`AURORA_TEST_DATABASE_URL` definida no worktree, o auditor passa a executar a
persistência, o critério de reinício de `06` T3, os três casos de detecção de
reescrita por cadeia de hash, a contiguidade de `sequence` e o caso de dois
escritores concorrentes — que é o **item 1** da lista de não-verificados do
relatório, e o que mantém metade dos itens 5 e 6 verificada por leitura.

Quem implementar (a) e parar em "o auditor sabe do CI" terá resolvido a menor das
duas coisas.

**Vencimento: Fase 3**, junto da P2-16.

#### P2-7 — o exemplo de `09` §1.1 e a aritmética de epoch única

`09` §1.1 traz `exercise_time: "T+01:12:04"` e
`exercise_timestamp: "2026-08-13T10:12:04"` com `simulation_epoch: 1`. Com
T0 = 09:00:00 os dois coincidem — isto é, um evento pós-rollback em que nada de
tempo de exercício foi descartado, o que só ocorre em rollback de rebobinagem
zero.

**Não é contradição e não foi escalado:** nenhum documento declara T0, e
qualquer par de valores define um por subtração. Sem proposição falsificável não
há conflito entre não-master a escalar.

**Não é verificável hoje:** `check_spec_examples.py` valida forma contra schema,
não relação aritmética entre `exercise_time`, `exercise_timestamp` e
`simulation_epoch`.

Levantado pelo `spec-guardian` na terceira auditoria, que recomendou escalação.
**A recomendação foi recusada com o argumento acima**, e o que mudou foi o texto
do `01` §3: `"depois do primeiro rollback deixam de coincidir"` virou
`"separam-se pela quantidade de tempo de exercício que o rollback descartou"` —
porque rollback de rebobinagem zero não separa nada, e a frase anterior afirmava
que sim.

**Sem prazo.** É candidato a exemplo mais claro em `09`, não defeito normativo.

#### P2-8 — retenção do pack por conteúdo

**A decisão já está tomada, e o que falta é a casa dela.** Os `effects` são
resolvidos contra o pack, não gravados no store (quarta leitura), e o pack é
fixado pelo `content_hash` que o `exercise_started` grava. Disso decorre que
reconstruir exercício passado exige **o pack como era**, e um pack legitimamente
corrigido entre execuções tornaria todo exercício anterior irreconstruível.

Regra decidida: **packs versionados por conteúdo, com o antigo retido.** Pack
imutável após o primeiro uso foi descartado — cenário é iterado entre execuções,
e a regra seria violada na primeira correção.

| | |
|---|---|
| **O que a Fase 2 entrega** | O **pino** e a **recusa**: `project` compara o hash do `exercise_started` com o de `Declarations` e levanta `PackMismatch`, com mensagem que nomeia `pack_id`, hash esperado, hash recebido e a etiqueta de canonicalização |
| **O que falta** | O **arquivo morto**: armazenamento endereçado por conteúdo, para o AAR de exercício passado abrir sem árvore de trabalho |
| **O que segura até lá** | O pack como era vem do **Git**, recuperado pelo hash que a mensagem de recusa nomeia. Serve para operador com o repositório à mão; não serve para o AAR abrir sozinho |

**Vencimento: Fase 10**, que é quando o AAR completo nasce — e **com item de DoD
próprio em `07`**, não só com esta pendência.

**Por que o destino é nomeado agora.** A decisão nasceu em docstring de
`range-core/state/simulation_state.py`, e docstring não é checklist binária.
Deixá-la só ali repetiria a forma do E1: requisito decidido, sem fase obrigada a
cumpri-lo, que não é mover — é apagar com passo intermediário. O item de DoD da
Fase 10 é spec-change, e é dele que esta pendência é a fila.

---

## 6. Os verificadores, nominalmente

Escrito porque a contagem oscilou em voz alta durante o spec-change — "nove",
depois "dez", contra os "seis" do `01` §2 — e três conjuntos diferentes estavam
sendo chamados pelo mesmo nome.

**Definição, e ela vale daqui em diante.** *Verificador* são os seis de `tools/`
que o `01` §2 normatiza, e nada mais. O que roda em `scripts/` é **checagem** ou
**probe**, e se chama assim — nunca "verificador".

> A primeira redação desta definição dizia "harness ou probe", e estava errada
> na própria tabela abaixo: `check_progress_consistency.py` é **checagem**, não
> harness nem probe. Corrigido aqui. O ponto da definição não muda — o que
> distingue não é o que o script faz, é `01` §2 nomear **seis** e nomear onde
> eles moram.
>
> **Consequência prática:** checagem nova de fase — como a da P2-2 — vai para
> `scripts/`, e não para `tools/`. Um sétimo arquivo em `tools/` contradiria a
> contagem que o `01` §2 fixa, e exigiria `spec-change` para acomodar decisão de
> implementação. Atestação de "todos os verificadores passam" que use
outro recorte é inconferível — foi exatamente o defeito que apareceu neste
spec-change, onde "verde" correu contra um conjunto que não existia em documento
nenhum.

**Os seis são exatamente seis.** `_common.py` é biblioteca compartilhada, não
verificador; `codegen.py` conta porque `--check` é verificação que não escreve.

| | Verificador | Job |
|---|---|---|
| 1 | `tools/check_core_boundary.py` | `arquitetura` |
| 2 | `tools/check_contract_literals.py` | `arquitetura` |
| 3 | `tools/check_event_envelope.py` | `arquitetura` |
| 4 | `tools/codegen.py --check` | `arquitetura` |
| 5 | `tools/check_security_constraints.py` | `seguranca` |
| 6 | `tools/check_synthetic_data.py` | `seguranca` |

**`scripts/` não são verificadores no sentido do `01` §2**, e o CI executa **onze**
deles — quatro checagens, um cruzamento de registro, cinco testes negativos e o
DEMO da fase:

> A frase dizia *"seis deles — dois checks, um cruzamento de registro e três
> testes negativos"* enquanto a tabela abaixo já listava **oito**. É a §6.1
> acontecendo dentro da seção que a §6.1 escreveu: o número foi lembrado de
> quando foi escrito, e a tabela cresceu ao lado dele. Corrigido aqui, e contado
> na fonte — a lista de passos de `.github/workflows/invariants.yml`.

| | Script | Job | O que é |
|---|---|---|---|
| 7 | `scripts/check_progress_consistency.py` | `arquitetura` | cruza tabela × seções deste tipo de registro |
| 8 | `scripts/phase0_negative_tests.py` | `arquitetura` | prova que os **seis** reprovam violação plantada |
| 9 | `scripts/check_contract_examples.py` | `contratos` | exemplos dos seis contratos |
| 10 | `scripts/check_contract_examples_probes.py` | `contratos` | prova que o 9 reprova |
| 11 | `scripts/check_spec_examples.py` | `contratos` | exemplos normativos da spec contra os contratos |
| 12 | `scripts/check_spec_examples_probes.py` | `contratos` | prova que o 11 reprova |
| 13 | `scripts/check_store_read_surface.py` | `arquitetura` | P2-2: a leitura do store não aceita filtro |
| 14 | `scripts/check_store_read_surface_probes.py` | `arquitetura` | prova que o 13 reprova |
| 15 | `scripts/demo_fase2.py` | `contratos` | o DEMO da fase, executado para não apodrecer |
| 16 | `scripts/check_core_contract_imports.py` | `arquitetura` | P2-15: o core importa de `contracts/` exatamente o declarado |
| 17 | `scripts/check_core_contract_imports_probes.py` | `arquitetura` | prova que o 16 reprova, em seis eixos |

Fora do CI: `scripts/audit_report.py` e `scripts/start_checkpoint_audit.sh` são
ferramenta de auditoria, não gate.

### 6.1 As contagens desta fase, e o que cada uma conta

**Três correções de contagem já aconteceram aqui, e as três são o mesmo defeito:
dois conjuntos com o mesmo número colado na cabeça.** "Nove verificadores" contra
os seis normativos; "sete sítios de recusa", depois "nove", e são onze; "doze
itens de DoD" contra os nove que a fase tem.

**É classe distinta da §1.5 da Fase 1, e o remédio é outro.** A §1.5 é *"li
outra coisa, e nunca errado"* — ler a fonte errada. Aqui a fonte certa nunca foi
lida: o número veio **lembrado de outro conjunto**, e nenhuma das três teria sido
pega por reler. Reler o `07` não corrige "doze" se o doze veio da contagem do
CI; só conferir contra **a fonte daquele conjunto** corrige.

A regra que ela ensina: **número afirmado diz de que conjunto é, e é contado na
fonte dele no momento em que se escreve.** A §1.5 mandaria reler, que é
exatamente o que não teria funcionado.

| Quantos | Do quê | Onde é a fonte |
|---|---|---|
| **9** | itens da Definition of Done da Fase 2 | `07_IMPLEMENTATION_PHASES.md`, seção Fase 2 |
| **6** | verificadores normativos, todos em `tools/` | `01_ARCHITECTURE.md` §2, e a tabela da §6 acima |
| **17** | invocações de `tools/` e `scripts/` que o CI executa | os 6 acima mais 11 de `scripts/` |
| **11** | sítios de recusa do fold | `Site`, em `range-core/state/simulation_state.py` |
| **4** | required status checks | `arquitetura`, `spec_freeze`, `seguranca`, `contratos` |

A confusão volta, e **custa mais quando aparece dentro de uma atestação** — foi o
que fez "todos os verificadores passam" correr verde contra um recorte que não
existia em documento nenhum.

**O número certo depende da pergunta, e é por isso que ele oscilava:**

- *"Quantos verificadores a spec normatiza?"* — **seis**, e é o que o `01` §2 e o
  README dizem.
- *"Quantas invocações de `tools/` e `scripts/` o CI roda?"* — **dezessete**, e o
  recorte precisa vir junto: fora dele o job `contratos` ainda roda
  `pip install`, `alembic --help`, `alembic upgrade head`, a suíte de
  `unittest` e dois `python -c`. Eram doze até a checagem da P2-2 e a prova
  negativa dela entrarem, catorze até o DEMO virar passo, e quinze até a P2-15
  trazer as duas dela.
- *"Quantas eu rodei localmente durante o spec-change?"* — **dez**. Não era
  nenhum dos dois conjuntos: faltavam os dois `*_probes.py`. Rodados depois, os
  dois passam, mas o registro fica: eu chamei de "verificadores" um recorte que
  não era nem o normativo nem o do CI.

O `spec_freeze` não aparece nas tabelas porque não roda script: é `git diff`
contra o conjunto `CODE` mais o prefixo do título, dentro do próprio workflow.

## 6.2 A peça do inject-engine com o loader — **ENTREGUE**

Escrito **antes** de a peça começar, e não depois: a sessão que a produziu se
esgotou aqui, e o que se sabe sobre ela não pode viver só na conversa. É a §0
deste registro outra vez.

> **Entregue em 15/08/2026.** O texto abaixo fica como estava — é o registro do
> que se sabia antes —, com duas marcas: a decisão que estava aberta foi tomada
> pelo operador, e o que a peça de fato produziu está na **§3.9**, que é onde as
> decisões novas moram.

### O que a peça fecha

| | |
|---|---|
| Item 9 da DoD | flag não declarada impede boot com mensagem clara |
| Metade restante do item 3 | "bloqueia disparo agendado" — é do engine, não do clock, que só oferece `is_paused` |
| DEMO da fase | carregar pack, disparar A01, ler projeção, rollback, ler projeção restaurada |

### A restrição que ordena o trabalho — §1.4 do checkpoint

**As regras `x-aurora-*` viram módulo do `range-core`, e o script de CI passa a
chamá-lo.** Hoje elas vivem em `scripts/check_contract_examples.py` —
`build_registries`, `AuroraChecker`, `_tipo_incompativel`, `_esc`, cerca de 290
linhas entre as linhas 69 e 360.

**FEITO em 15/08/2026**, e **antes** do loader, não junto: tirar 290 linhas de
dentro de um gate ativo e ligar um consumidor novo são duas mudanças, e feitas
juntas dariam um sinal só — um vermelho não diria qual delas quebrou. O módulo é
`range-core/engine/loader/contract_rules.py`, e o gate ficou verde depois do
movimento, provando que ele faz o que as linhas faziam.

**Duas coisas mudaram na travessia, as duas de propósito.** `build_registries`
lia `domains/*/flags.yaml` do disco; agora as flags chegam como **dado** — não
seria violação do invariante 1, que é sobre import, mas seria o acoplamento que
ele existe para evitar entrando por outra porta. E `ContractError`, de
`tools/_common`, virou `ContractRuleError` local: o núcleo não importa de
`tools/`.

**O movimento teve um defeito, e ele foi silencioso — ver a P2-12.**

**Consequência de gate, já prevista na §1.4:** `check_contract_examples.py`
deixa de ser stdlib pura e passa a importar do núcleo. Ele já roda no job
`contratos`, que tem dependência de aplicação desde a P1-6 — os outros
verificadores seguem stdlib. Depois do movimento, `check_contract_examples.py` e
`check_contract_examples_probes.py` precisam continuar verdes: são eles que
provam que o gate ainda enxerga.

### O que o loader valida, conferido no contrato

`x-aurora-documents` de `contracts/scenario.schema.v2.yaml` mapeia **três**
arquivos, e só três:

| Arquivo | Ponteiro |
|---|---|
| `manifest.yaml` | `#` |
| `injects.yaml` | `#/$defs/injects_document` |
| `branches.yaml` | `#/$defs/branches_document` |

`objectives.yaml`, `ground_truth.yaml` e os demais têm contratos próprios e são
das Fases 6, 7 e 9. **O loader da Fase 2 valida o que consome** — manifesto e
injects —, e `branches.yaml` é opcional aqui porque branching é NON-GOAL desta
fase e entregável da Fase 7.

### A decisão aberta: onde mora o pack mínimo

`scenarios/` **não existe** — o pack é entregável da Fase 7, e o diretório é
território do `scenario-designer`. A Fase 2 precisa de um pack de 3 injects.

| | A favor | Contra |
|---|---|---|
| `scenarios/academus/<pack>/` | é onde pack de verdade mora, e exercita o caminho real | um fixture da Fase 2 ali é confundido com cenário, e herda as obrigações de `ground_truth.yaml` e `GM_NOTES.md` que `CLAUDE.md` impõe a scenario pack |
| `tests/fixtures/pack_minimo/` | é fixture e se chama assim | não exercita o caminho de diretório real |

**Inclinação registrada, não decidida:** a segunda, com a forma de `04` §1
respeitada dentro do fixture. A decisão é do operador.

> **Decidida pelo operador em 15/08/2026: `tests/fixtures/pack_minimo/`**, com a
> forma de `04` §1 respeitada dentro do fixture. O que a decisão custa — o
> caminho de diretório real não é exercitado — está pago em parte pelo DEMO, que
> monta o pack contra o adapter real e roda no CI. Ver a §3.9.

### O que já está pronto para a peça

O store grava e lê; o clock dá as marcas e o `is_paused`; o fold projeta e
recusa o que não fecha. O engine é quem chama os três — e é o primeiro
consumidor das regras `x-aurora-*` sobre pack real, que é o que a §1.4 antecipou.

## 7. Registro final da fase

O que `07` §248 manda gravar ao concluir, mais duas coisas que ele não pede e que
esta fase pagou para aprender.

### 7.1 Resumo técnico

A Fase 2 entrega o **núcleo determinista**: um relógio, um registro append-only,
uma projeção e o motor que os chama. Nenhuma tela, nenhuma rota, nenhuma métrica.

| Peça | Onde | O que ela é |
|---|---|---|
| `exercise-clock` | `range-core/clock/` | T0, pausa, multiplicador fechado (1x/5x/20x), as **quatro marcas** de uma leitura só. Tempo de parede por injeção — nenhum teste dorme |
| event store | `range-core/events/` | append-only, envelope de `09` §1.1, carimbo no append (D1), duas implementações — memória e Postgres com `sequence` contígua e cadeia de hash |
| projeção `simulation_state` | `range-core/state/` | fold puro, `project(events, declarations)`, **onze sítios de recusa** nomeados. A exclusão de epoch abandonada vive aqui e em lugar nenhum mais |
| loader de pack | `range-core/engine/loader/` | duas camadas — JSON Schema e as regras `x-aurora-*`, **as mesmas do gate de CI** —, pino por `content_hash` canônico |
| inject-engine | `range-core/engine/inject_engine.py` | dispara, agenda, decide, pausa, rebobina. Não guarda estado: consulta o clock e o store |
| determinismo | `range-core/determinism.py` | `RANDOM_SEED` do ambiente ou de `.env`, com fluxos derivados por escopo |

**As quatro decisões que mais restringem o que vem depois:** o núcleo é
**síncrono** (§1.3); as marcas são carimbadas **pelo store** (§1.5); a exclusão de
rollback vive **só no fold** (§1.6); e `effects` é **estado final declarado**,
nunca delta (§1.7) — que é o que torna idempotência e rollback possíveis.

### 7.2 Estrutura de diretórios

```text
range-core/
  determinism.py            RANDOM_SEED e fluxos derivados por escopo
  clock/                    exercise_clock.py, port.py
  events/                   envelope, epoch, ids, integrity, store, postgres_store
  state/                    simulation_state.py — o fold
  engine/
    inject_engine.py        dispara, agenda, decide, pausa, rebobina
    loader/                 canonical, contract_rules, contract_source, pack_loader
    branching/ migrations/  vazios — Fase 7
  aar/ api/ evidence/ metrics/ objectives/ rubrics/ telemetry/   vazios
tests/                      12 arquivos — 11 suítes e o harness de mutação; 155 testes
  fixtures/pack_minimo/     manifest.yaml, injects.yaml, objectives.yaml
scripts/                    +6 nesta fase, dos quais 5 rodam no CI
alembic/versions/           0001_event_store.py
```

### 7.3 Endpoints criados

**Nenhum, e é NON-GOAL.** `07` Fase 2 exclui UI e API; a `academus-api` é da Fase
3. O que existe de superfície pública nesta fase são dois métodos de
`EventStore` — `append` e `read_all` — e a lista é **fechada por verificação**
(`scripts/check_store_read_surface.py`, cinco eixos de prova negativa).

### 7.4 Migrations

| Revisão | Arquivo | O que cria |
|---|---|---|
| `0001_event_store` | `alembic/versions/0001_event_store.py` | tabela do event store, com `simulation_epoch NOT NULL`, `sequence` como chave primária atribuída pela **aplicação** e `row_hash` único |

`sequence` não é `BIGSERIAL` de propósito: sequência de banco consome número em
transação que faz rollback, e o buraco resultante seria alarme falso — detecção
que grita sem defeito é detecção que se aprende a ignorar (§3.5).

### 7.5 Variáveis de ambiente

| Variável | Quem lê | Por quê |
|---|---|---|
| `DATABASE_URL` | a migration | o banco de desenvolvimento |
| `AURORA_TEST_DATABASE_URL` | os testes de Postgres | **duas variáveis de propósito**: os testes fazem `TRUNCATE`, e apontá-los para a primeira faria um `unittest` distraído apagar o banco de quem tivesse o `.env` carregado (§3.5) |
| `RANDOM_SEED` | `range-core/determinism.py` | item 2 da DoD. Sem valor padrão: seed inventado reproduz a si mesmo |

Ausente `AURORA_TEST_DATABASE_URL`, os nove testes de Postgres **pulam**, e o
`skip` imprime o comando para rodá-los — pulo silencioso lido como verde é o que
a **P2-19** ataca.

### 7.6 Pendências abertas, por quem as recebe

**Oito fechadas** — P2-2, P2-3, P2-4, P2-10, P2-12, P2-13, P2-14 e P2-15 —, e
**onze abertas**, contadas na tabela da §5 no momento de escrever esta linha.

> A primeira redação desta frase dizia *"seis fechadas"* e listava sete nomes. A
> §6.1 acontecendo dentro da seção que a descreve, três parágrafos acima de
> "número afirmado é contado na fonte dele". Pega por contar, não por reler.

Separadas por destinatário:

#### Fase 3 — quem começar lê isto primeiro

| Id | O que é |
|---|---|
| **P2-5** | `00` §5.6 enumera duas das quatro marcas — cosmético, `spec-change` |
| **P2-6** | ~~sem forma declarativa de ligar `participant_action` a flag~~ — **movida para a Fase 8** |
| **P2-9** | a frase do mecanismo em `01` §4.4 envelheceu — `spec-change` |
| **P37** | `docs/process/` fora do `CODE` do `spec_freeze` — herdada da Fase 1 |

**P2-5 e P2-9 cabem no mesmo `spec-change`**; a P37 é mecanismo e vai em PR
próprio. Nenhuma das quatro impede o início da Fase 3 — as duas de spec vencem
antes de ela **fechar**.

#### Fases posteriores

| Id | Destino | O que é |
|---|---|---|
| **P2-1** | Fase 6 | propriedade entre projeções: abandono lido só pelo motivo declarado |
| **P2-17** | Fase 6 | o `start` do intervalo congelado vem da âncora, não do inject falho |
| **P2-11** | Fase 9 | `append` abre uma conexão por chamada |
| **P2-8** | Fase 10 | retenção do pack por conteúdo, com item de DoD próprio |
| **P2-7** | sem prazo | o exemplo de `09` §1.1 e a aritmética de epoch única — candidato, não defeito |

#### Aparato de auditoria — não são da fase, e se repetem sem dono

| Id | O que é |
|---|---|
| **P2-16** | o worktree resolve `main` para o ref **local**, que envelhece — produziu um HIGH falso |
| **P2-18** | o harness de mutação escreve em `tempfile` fora do worktree, contra a suposição de contenção |
| **P2-19** | o auditor não confirma o CI no commit auditado — e o Postgres efêmero que a fecha **também faz os nove testes deixarem de pular** |

**As três cabem num PR só**, e vencem antes do próximo checkpoint: nenhuma delas
se conserta mexendo no código de fase alguma.

### 7.7 O que a fase aprendeu sobre o próprio método

Três lições, e **nenhuma está numa Definition of Done**. As três custaram caro.

**1. Escalar sem varrer é meia correção — a lição do E1.**
O E1 corrigiu um item do `07`, e a mesma exigência vivia em mais cinco lugares. A
varredura que os achou usou **dois** padrões: o nome do motivo, e um que pega o
enunciado **sem** o nome. O segundo é o que encontrou `03` §3.5, que nenhuma
auditoria tinha reportado.

Repetiu-se três vezes depois, e o padrão que paga é sempre o que **não** usa o
nome: no `exercise_resumed`, foi o das *enumerações de atos* que achou `00` §3.1
— no MASTER — enumerando "start/pause/reset"; no item 8, foi comparar os três
sítios lado a lado que revelou que **eles não diziam a mesma coisa**, e que a
redação do item já o dava por cumprido.

**2. Número lembrado de outro conjunto, e reler não pega — a §6.1.**
Três correções de contagem na mesma fase: "nove verificadores" contra seis, "sete
sítios de recusa" contra onze, "doze itens de DoD" contra nove. A §1.5 da Fase 1
manda **reler a fonte** — e reler não corrige nenhuma delas, porque o número não
veio de leitura errada: veio **lembrado de outro conjunto**.

A regra é outra: **número afirmado diz de que conjunto é, e é contado na fonte
dele no momento em que se escreve.** Custou de novo no L1 da auditoria PASS — "32
tipos" numa docstring, escrita antes de a própria fase acrescentar o trigésimo
terceiro.

**3. A fase que cria o mecanismo estende o julgador no mesmo commit — o B1.**
Esta fase criou a primeira suíte real do projeto, em `unittest`, e não
acrescentou uma linha à allowlist do auditor. O auditor não executou **nada** e
voltou a julgar por leitura: sete dos nove itens ficaram NÃO VERIFICADO, e o
veredito foi FAIL por uma omissão de uma linha.

**A regra já estava escrita dentro do arquivo que ela governa** — *"script novo
que precise ser executado pelo auditor entra aqui por nome, no commit que o
cria"* —, e é reincidência nomeada do H3 da segunda auditoria da Fase 1. Regra
escrita não segura; o que segura é o commit que a cumpre.

**O que as três têm em comum**, e é o que sobrevive: nenhuma é erro de raciocínio.
São **afirmações que envelhecem** — a correção que não varreu, o número que veio
de outro conjunto, o mecanismo que não acompanhou o que ele julga. É a §1.6 da
Fase 1 em três formas, e o remédio nunca é atenção: é fazer a afirmação depender
de algo que **falha alto** quando ela deixa de valer.

## 8. Próxima fase

`07` Fase 3 — API mínima. **ENTRY: Fase 2 completa** ✅

O que a Fase 3 herda em condição de uso: o fold, o store nas duas implementações,
o clock, o loader e o engine — com 155 testes, 17 verificações no CI e prova
negativa por mutação sobre os três módulos que decidem estado.

**O que ela precisa resolver cedo:** a **P2-6**. A `01` §4.4 descreve mudança de
estado sem caminho reconstruível enquanto não houver forma declarativa de ligar
`participant_action` a flag — e é na Fase 3 que nasce o serviço que a consome.
