# Fase 2 — Clock, eventos, estado, engine mínimo

**Status: EM CURSO.** Checkpoint ⏸ submetido e decidido em 15/08/2026. O
spec-change que ele exigia está em `main` no commit `a3aded5` (PR #21).

**Código escrito até aqui:** a projeção `simulation_state`, o envelope, o
cálculo compartilhado de epoch, o `event_id`, a porta do relógio e o event store
com implementação em memória. Nenhum item da DoD fechado — ver a §4.

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
4 h", não de contagem de eventos, e não existe pack nem engine para produzir um
exercício real. O que está medido é a curva volume → tempo. O item 8 fecha
quando o volume de 4 h for conhecido e estiver abaixo de 150 mil.

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

---

## 4. Itens da Definition of Done

Da `07` Fase 2, **já com as correções de E1 e E2**, que entraram em `main` no
`a3aded5`. A coluna "o que mudou" existe porque três itens são mais exigentes
agora do que eram no texto que a fase encontrou. Nenhum item iniciado.

| | Item | Status | Verificado contra o quê |
|---|---|---|---|
| 1 | As quatro marcas em todo evento | ✅ | `test_event_store.Carimbo.test_append_carimba_as_quatro_marcas_do_clock` — as quatro vêm de **uma** leitura. `…test_o_produtor_nao_tem_onde_escrever_tempo` — `EventDraft` não tem os seis campos que o store atribui |
| 2 | `RANDOM_SEED` lido por código do `range-core` | ⬜ | Nada escrito. Decidido que **não** é aqui que ele é consumido — `event_id` usa `secrets` |
| 3 | PAUSAR congela o clock e bloqueia disparo agendado | ⬜ **metade** | **Congela**: fechada — `test_exercise_clock.Pausar.test_durante_a_pausa_o_exercicio_congela_e_a_parede_avanca` e `…test_as_duas_marcas_de_exercicio_congelam_JUNTAS`, que é a norma que o `a3aded5` acrescentou ao `01` §3. **Bloqueia disparo agendado**: aberta, e é do inject-engine — o clock oferece `is_paused` e não agenda nada |
| 4 | Aplicar A01 duas vezes produz projeção idêntica | ✅ | `test_simulation_state.Propriedades.test_p3_reaplicar_o_mesmo_inject_nao_muda_o_estado`, com 2, 3 e 7 repetições. Prova negativa: a mutação *"defaults removidos"* e a *"limite do intervalo movido"* o derrubam, em `test_simulation_state_probes` |
| 5 | Rollback grava, incrementa epoch, reconstrói sem apagar | ✅ | Três metades, três fontes. **Grava**: `test_event_store_postgres.StoreEmPostgres.test_rollback_persistido_reconstroi_sem_apagar`. **Incrementa**: `test_event_store.Carimbo.test_epoch_atribuida_e_a_contagem_de_rollbacks`. **Sem apagar**: o mesmo teste de Postgres afirma 3 linhas na tabela depois do rollback |
| 6 | `participant_action` da epoch anterior legível e marcada | ✅ | **Legível**: `test_simulation_state.Propriedades.test_participant_action_abandonada_permanece_no_fluxo` e `…test_rollback_atravessa_escrita_de_participant_action`. **Marcada**: `simulation_epoch` é coluna `NOT NULL` e é conferido por `_verify_epochs`, cuja ausência é pega pela mutação *"conferência de epoch desligada"*. **Sobrevive ao reinício**: `…test_instancia_nova_sobre_o_mesmo_banco_restaura_a_projecao` |
| 7 | `technical_failure` **registra** os extremos, em `exercise_timestamp` | ⬜ | Forma normatizada em `06` T3; o campo é a **P2-4** |
| 8 | Reconstrução completa em < 3 s | ⬜ **medido, não fechado** | Passa com folga até ~150 mil eventos (2,87 s) e estoura em 200 mil (4,30 s). Fecha quando o volume real de 4 h for conhecido — depende do pack e do engine, que não existem. Números e envelope na §3.8 |
| 9 | Flag não declarada impede boot com mensagem clara | ⬜ | Não há boot. O fold recusa inject e opção fora do pack, que é outra coisa |

**Quatro de nove fechados, e o item 3 pela metade**, com cada ✅ nomeando o teste que o prova — atestação sem fonte é
o que esta fase já registrou como caro. O que falta é clock, seed, loader com
validação de flags, o campo de payload do intervalo, e a medição do item 8.

O item 7 é o único cujo cumprimento depende de contrato que ainda não existe: o
campo de payload que carrega os extremos é a **P2-4**.

---

## 5. Pendências

| Id | O que é | Vencimento |
|---|---|---|
| P2-1 | Propriedade entre projeções: abandono lido só pelo motivo declarado | **Fase 6** |
| P2-2 | ~~AST sobre a superfície de leitura do store~~ | **FECHADA** — `scripts/check_store_read_surface.py` |
| P2-3 | ~~Spec-change com os itens do checkpoint~~ | **FECHADA** em 15/08/2026, `a3aded5` |
| P2-4 | Campo de payload dos extremos do intervalo congelado | **Fase 2**, no PR de código |
| P2-5 | `00` §5.6 enumera duas das quatro marcas temporais | Antes da Fase 3, junto da P37 |
| P2-6 | Sem forma declarativa de ligar `participant_action` a flag; a `01` §4.4 depende dela | **Fase 3** |
| P2-9 | A frase do mecanismo na `01` §4.4 envelheceu — `spec-change` | Sem prazo amarrado à Fase 3 |
| P2-10 | ~~Medir o item 8 antes de construir em cima do fold~~ | **FECHADA** — medida em 15/08/2026, §3.8 |
| P2-11 | `append` abre uma conexão por chamada | **Fase 9**, com o item 8 e pela mesma causa |
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

#### P2-4 — campo de payload dos extremos do intervalo congelado

**O que falta.** `contracts/events.schema.yaml` deixa `payload` aberto
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

**Vencimento: Fase 3.**

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

**`scripts/` não são verificadores no sentido do `01` §2**, e o CI executa seis
deles — dois checks, um cruzamento de registro e três testes negativos:

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
| **14** | invocações Python que o CI executa | os 6 acima mais 8 de `scripts/` |
| **11** | sítios de recusa do fold | `Site`, em `range-core/state/simulation_state.py` |
| **4** | required status checks | `arquitetura`, `spec_freeze`, `seguranca`, `contratos` |

A confusão volta, e **custa mais quando aparece dentro de uma atestação** — foi o
que fez "todos os verificadores passam" correr verde contra um recorte que não
existia em documento nenhum.

**O número certo depende da pergunta, e é por isso que ele oscilava:**

- *"Quantos verificadores a spec normatiza?"* — **seis**, e é o que o `01` §2 e o
  README dizem.
- *"Quantas invocações Python o CI roda?"* — **catorze**, mais `pip install` e
  `alembic --help` no job `contratos`. Eram doze até a checagem da P2-2 e a
  prova negativa dela entrarem.
- *"Quantas eu rodei localmente durante o spec-change?"* — **dez**. Não era
  nenhum dos dois conjuntos: faltavam os dois `*_probes.py`. Rodados depois, os
  dois passam, mas o registro fica: eu chamei de "verificadores" um recorte que
  não era nem o normativo nem o do CI.

O `spec_freeze` não aparece nas tabelas porque não roda script: é `git diff`
contra o conjunto `CODE` mais o prefixo do título, dentro do próprio workflow.

## 7. Próxima fase

`07` Fase 3 — API mínima. ENTRY: Fase 2 completa.

**P37 vence antes dela**, com prazo declarado em `fase_1.md` §7.2.
