# Fase 4 — VERTICAL SLICE ⏸

**Status: EM PLANEJAMENTO.** Nenhuma peça aberta. A branch nasceu em
`6efca2e` — a âncora está gravada em `docs/process/phase_anchors.tsv`, e ela é o
primeiro item do procedimento novo, não formalidade.

**Um status só**, e ele é o do documento inteiro. Foi o L2 da segunda auditoria
da Fase 3: um registro com dois cabeçalhos de estado não tem estado.

**Esta é a primeira fase auditada antes de existir em `main`.** As Fases 2 e 3
foram mergeadas peça a peça e auditadas depois — o H1 da quarta rodada da Fase 3
é história irreparável, e não defeito a corrigir naquele commit. O que impede a
repetição já está construído: `scripts/check_audit_base.py` com os oito eixos, a
âncora, e o procedimento de `docs/process/WORKFLOW.md`. **Esta fase é a primeira
em que esse aparato é exercido para valer.**

---

## 0. Por que este registro começa antes da fase

Mesma razão das Fases 2 e 3: o plano decide coisas antes de existir código, e
**conversa não é fonte versionada**. As decisões abaixo estão marcadas
`DECIDIDA` ou `PROPOSTA` — as `PROPOSTA` aguardam o operador, e nenhuma linha de
código nasce antes disso.

A Fase 3 provou o custo do contrário duas vezes: a P2-6 atravessou três camadas
porque cada uma tratou a anterior como fonte, e a D3 daquele registro afirmou
uma exigência de `05` §8 que a fonte não continha. **Afirmação sobre a spec aqui
é citação, e foi relida no momento de escrever** — cada seção abaixo nomeia
documento e §.

---

## 1. O que a fase entrega, conferido na fonte

`07` Fase 4 — **A fase mais importante do projeto. Prova a arquitetura ponta a
ponta antes de qualquer expansão.**

**OUTPUTS** — gm-console mínimo (autenticado, lista de injects, botão de
disparo, rollback); wallboard mínimo (dois painéis gerados por taxonomia +
índice de saúde); participant-view.

**NON-GOALS** — três papéis de facilitação, social feed, dashboards por persona,
BARS, AAR.

**DEMO SCRIPT** — a sequência exata: `GM clica A01 → engine grava evento e muda
projeção → API degrada matrícula → wallboard reage em < 1 s → participant-view
exibe texto_para_plateia → GM clica ROLLBACK → estado restaurado, evento
registrado`.

**DoD — seis itens**, e nenhum deles é atestação:

| | Item |
|---|---|
| 1 | a sequência do DEMO roda ponta a ponta sem intervenção manual |
| 2 | wallboard atualiza em < 1 s via WebSocket |
| 3 | refresh do browser no wallboard e no participant-view recupera o estado corrente |
| 4 | reinício do container do engine restaura o exercício a partir do event store |
| 5 | rollback aparece anotado na timeline |
| 6 | índice de saúde institucional é calculado a partir dos `severity_weight` ativos |

**Critérios:** **T5** é o da fase, e traz uma exigência que a DoD não enuncia —
*"reinício com o exercício pausado o restaura pausado; reinício depois da
retomada o restaura correndo. **Os dois casos**"*. **T6** diz "Fases 4–5", e a
§2 abaixo decide qual metade é desta. **T15** vale em todas as fases, e esta
acrescenta duas superfícies sem autenticação e um ecossistema de build novo.

**`05_SECURITY_REQUIREMENTS.md` é leitura obrigatória aqui**, e por três frentes
ao mesmo tempo: §8 (nenhum serviço exposto sem autenticação — **exceto wallboard
e participant-view**, que são exatamente duas das três telas desta fase), §6
(bind em `127.0.0.1`, nenhuma porta publicada no compose de produção) e T15
(nenhuma dependência não pinada — o `npm` entra aqui).

**`01_ARCHITECTURE.md`** dá o resto: §4 as cinco camadas de estado, §4.2 o que
rollback e reset fazem, §5.3 o que a taxonomia habilita (painel por convenção,
índice de saúde), §6 os serviços (wallboard sem login, participant-view só com
`texto_para_plateia`, gm-console com os quatro comandos) e §7 o desempenho.

---

## 2. O que é verificável, e o que fica declarado como limite

**Até aqui tudo era verificável por teste. Esta fase tem coisas que só a sala
vê**, e a decisão de onde fica a linha é do plano — não de quando o teste ficar
difícil de escrever.

O critério é um só: **verificável é o que falha vermelho sem um humano olhando.**
O resto é limite, e limite se declara com nome, não se omite.

### 2.1 Verificável — e como

| O que | Como fica vermelho |
|---|---|
| **o estado corrente chega a quem conecta agora** (item 3) | conexão nova, sem histórico nenhum, recebe o estado completo. É propriedade do **protocolo**, não disciplina do cliente — ver a D4 |
| **< 1 s** (item 2) | do `append` do `inject_fired` até o frame no cliente conectado, medido no protocolo, com o par que discrimina: sem disparo, nenhum frame |
| **o índice de saúde** (item 6) | função pura sobre os `severity_weight` e o estado; o par: nenhuma flag fora do default dá 100, e ligar a de peso 10 baixa mais que ligar a de peso 6 |
| **os painéis por taxonomia** (`01` §5.3) | flag nova em `flags.yaml` aparece no painel **sem tocar em código** — probe que planta uma flag e exige o painel novo |
| **o reinício** (item 4, T5) | o par: pausado restaura pausado, retomado restaura correndo. E no **container**, não no processo — ver a D12 |
| **o rollback na timeline** (item 5) | payload da timeline com a anotação e a epoch; o par: sem rollback, sem anotação |
| **a sequência inteira** (item 1) | o DEMO como passo de CI, na forma que a Fase 2 fixou — roteiro que ninguém executa apodrece igual a comentário que ninguém lê |
| **vazamento para a sala** (T6, a metade desta fase) | varredura recursiva de chaves sobre o payload público, corpo e cabeçalhos |

### 2.2 Declarado como limite

- **Renderização, contraste e legibilidade a 10 m** (`01` §6). Não há como
  afirmar isso sem navegador, e **não haverá driver de browser nesta fase**:
  seria uma dependência de teste maior que o que ela julga, e o que ela julgaria
  é justamente a parte que a D3 tira do cliente. O limite fica pequeno **porque**
  a derivação é do servidor — é a D3 que o encolhe, não a boa vontade.
- **"Sem intervenção manual" é provado no protocolo.** A sequência do DEMO é
  executada por processo, ponta a ponta. O que o navegador acrescenta é a
  pintura, e a pintura é o limite acima.
- **Rede isolada do exercício** (`05` §8, para wallboard e participant-view).
  Verificável é o bind em `127.0.0.1` e a ausência de porta publicada; que a
  rede da sala esteja isolada é propriedade de **deploy**, e o teste não a
  alcança.
- **A metade de T6 que é do `operador`** — *"resposta de endpoint autenticado
  como `operador` não contém `linha`, `descricao_facilitador`…"* — fica para a
  Fase 5. O NON-GOAL desta fase é *"três papéis de facilitação"*, e um critério
  sem sujeito é o defeito que este projeto já corrigiu três vezes na spec:
  cobrar de uma fase a verificação de artefato que ela não produz. **A metade que
  é desta fase é a das duas superfícies públicas**, e ela é a mais exposta das
  duas — wallboard e participant-view não têm token nenhum entre elas e a rede.

---

## 3. As decisões, tomadas antes do código

### D0 — o aparato primeiro: a peça 0 é P3-4 e P3-8 — **PROPOSTA**

As duas vencem **antes deste checkpoint**, e as duas mudam o que o auditor
consegue medir. Fazê-las depois seria auditar a fase inteira com o aparato que
elas consertam.

**P3-8** (dois falsos bloqueios do hook) é de escopo conhecido e não precisa de
aprovação: `WORKFLOW.md` já classifica bloqueio indevido como defeito.

**A P3-4 precisa, e é por isso que esta decisão é PROPOSTA.** A pendência ficou
sem teste **de propósito**: *"ele reprovaria toda auditoria feita em worktree, e
mudar o critério de reprovação do auditor no PR que ele vai auditar é decisão do
operador, não minha"*.

A forma proposta tem duas metades, e a segunda é a que exige a decisão:

1. **O teste** — `range_core`, `contracts` e `domains` resolvem sob a **mesma
   raiz** que a árvore em execução. Sem parâmetro, sem git: compara o
   `__file__` dos três com a raiz derivada do próprio arquivo de teste.
2. **O lançador passa a criar um venv dentro do worktree** e a instalar
   `-e "$WT[test]" -c constraints.txt` nele, com o `PATH` à frente. Sem isso o
   teste fica vermelho em **toda** auditoria — porque hoje `range_core` de fato
   vem da árvore principal, e `range-core` tem hífen: não há CWD que resolva.

**A alternativa recusada foi pular o teste em worktree.** É exatamente
*degradar para "ok" quando não se sabe* — a classe que custou três predicados a
esta linhagem.

**O custo, dito:** o lançador passa a precisar de rede uma vez por auditoria (o
`pip install`). É o **lançador**, na máquina do operador, e não o auditor — a
decisão da P2-19 de não pôr rede na allowlist do julgador continua intacta.

### D1 — as três telas em React 18 + Vite + Tailwind, sob `range-core/web/` — **DECIDIDA**

`00` §8 fixa a stack e `01` §2 põe `range-core/web/gm-console/`,
`participant-view/` e `wallboard-shell/` no layout. `tools/check_contract_literals.py`
já varre `.ts`/`.tsx` por varredura léxica, com o limite declarado — a exceção
de `01` §2. **Escolher outra coisa exigiria `spec-change`**, e não há defeito na
spec a corrigir aqui.

**Todo o ecossistema de node fica dentro de `range-core/web/`** — `package.json`,
lockfile, configuração. Nada novo na raiz: arquivo novo no topo nasce invisível
ao `spec_freeze`, e foi a P37.

**O build entra no job `contratos`, e não em job novo.** Job novo é context novo,
e context exigido antes de existir em `main` trava todo PR que não o produza —
foi a P1-18. O nome do job já não descreve o escopo desde a Fase 2, e a condição
de saída está registrada lá.

**Sem test runner de JavaScript**, e o motivo é a D3: não há lógica no cliente
para testar. O que o CI prova é que ele **compila**.

### D2 — toda derivação é do servidor; o cliente é renderizador — **DECIDIDA**

Painéis, índice de saúde, timeline, o texto que a plateia lê: **calculados em
Python, verificados em Python**. O TS recebe pronto e pinta.

Não é gosto de arquitetura: é o que faz a §2.2 acima ter três linhas em vez de
"a UI não é testada". Cada pedaço de lógica que descesse para o cliente subiria
para o limite declarado — e o limite declarado é o único lugar onde defeito não
fica vermelho.

### D3 — o frame é estado **total**, nunca delta — **DECIDIDA**

O item 3 da DoD (*"refresh recupera o estado corrente"*) vira propriedade do
protocolo: **não há o que acumular**. Um cliente que quisesse divergir do
servidor não teria por onde — a mesma forma da porta da peça 3 da Fase 3, que
não aceita `SimulationState` pronto.

**E o snapshot HTTP e o frame do WebSocket são o mesmo payload, da mesma
função.** Duas serializações do mesmo fato divergem, e a que diverge em silêncio
é sempre a que ninguém está olhando — é a D4 da Fase 3, e a checagem que a
sustenta é a mesma família.

**O custo, medido antes de decidir:** o estado de simulação são ~15 flags. Frame
total a cada evento é ordens de grandeza abaixo de qualquer orçamento desta
fase. Se um dia não for, o número dirá — e não a intuição.

### D4 — a superfície do range-api declarada antes da rota, e o verificador é o **mesmo** — **DECIDIDA**

A Fase 3 pagou por essa forma e ela funcionou: `api_surface.yaml` +
`check_api_surface.py`, com igualdade nas duas direções e o terceiro eixo que
impede `planejada` de virar esconderijo.

**Um segundo verificador seria a D4 da Fase 3 outra vez** — duas listas sobre a
mesma fronteira divergem. O verificador é **generalizado** para duas
declarações; o vocabulário de papéis é que muda de lado:

| | `domains/academus/api_surface.yaml` | a declaração do core |
|---|---|---|
| papel de exercício | **recusado** | é o vocabulário legítimo |
| papel de domínio | é o vocabulário legítimo | **recusado** |

A fronteira é a mesma, lida nos dois sentidos — e é ela que o invariante 1 não
alcança, porque varre import e não vocabulário.

### D5 — o gm-console autentica **um** papel — **DECIDIDA**

`facilitador`, e só. O NON-GOAL da fase é *"três papéis de facilitação"*.
`operador` e `avaliador` entram na declaração como `planejada`, e o terceiro
eixo do verificador cobra a promoção no dia em que a rota nascer — a promessa
fica no mecanismo, não em prosa.

**A credencial vem do ambiente, sem default, com recusa alta**, na disciplina
que a peça 4 da Fase 3 fixou para o segredo de JWT — e com o mesmo placeholder
**vazio** no `.env.example`, pela mesma assimetria: senha copiada do exemplo
**funciona**, e um segredo errado que se anuncia é menos perigoso que um que se
comporta. Comparação por `compare_digest`.

**A alternativa recusada** era emitir o token por linha de comando e colá-lo no
console. Ela evita guardar credencial, e é pior aqui: o item 1 da DoD é
literalmente *"sem intervenção manual"*.

**O que continua proibido é o que a Fase 3 recusou:** endpoint que assine o papel
pedido no corpo. Isso é vulnerabilidade intencional, e `CLAUDE.md` não a admite.

### D6 — a narrativa é carregada **por superfície**, e o engine continua sem ela — **DECIDIDA**

`pack_loader.Inject` **não carrega** `titulo`, `descricao_facilitador`,
`texto_para_plateia` nem `linha`, e o comentário lá diz por quê — *"o caminho
mais curto para vazar é o engine carregar o campo sem precisar dele. Quem os
exibe é a UI, por rota com papel — Fase 4"*. **Esta é a fase, e a decisão é
manter a separação em vez de desfazê-la.**

A narrativa passa a ser lida por um caminho **próprio**, e cada superfície
declara os campos que carrega — whitelist. Vazar deixa de ser esquecer um
filtro e passa a ser escrever um caminho novo.

O teste é o de `06` T6: varredura recursiva de chaves sobre o payload
serializado, corpo e cabeçalhos. **Por superfície**, porque as listas são
diferentes: `texto_para_plateia` é proibido no wallboard e é *o conteúdo* da
participant-view.

### D7 — `exercise_reset` fica de fora, e a docstring que o datava aqui é corrigida — **DECIDIDA**

`07` OUTPUTS pede *disparo* e *rollback*. `01` §4.2 diz que RESET *"restaura os
defaults do contrato **e o snapshot de business state do start**"* — e snapshot
de business state exige o dataset, que é Fase 5.

`range-core/engine/inject_engine.py` diz, em docstring, *"`exercise_reset` é
Fase 4"*. **Era verdadeira quando escrita e deixou de ser**: é a §1.6 da Fase 1,
e a correção da frase entra nesta fase junto com a decisão — não fica para quem
chegar depois e a ler como fonte.

`paused_in` já trata `EXERCISE_RESET` no fluxo, e isso continua: ler um evento
que ainda não é emitido não antecipa nada.

### D8 — P3-5: as três tabelas em Postgres, e o que **não** é seed — **DECIDIDA**

`01` §4 põe Business State em Postgres e o declara *"não reversível por rollback;
só por reset total"* — **falso a partir do momento em que existe um container que
reinicia**, e esse momento é esta fase. Fase que torna uma linha normativa falsa
é onde a linha se conserta.

Escopo: as três tabelas e a migration. **Sem seed** — `07` Fase 5 é dona do
*"seed em escala com bulk insert"* e do determinismo por `RANDOM_SEED` (T8).

**Os seis registros do DEMO não são seed, e a distinção precisa ser dita**
porque ela vai parecer arbitrária: seed é dataset em escala, determinista e
verificável por T8; seis linhas para que a matrícula tenha o que matricular são
**fixture de demonstração**. Elas entram por um caminho explicitamente nomeado
como tal, e não pela migration — migration que insere dado de demonstração é
histórico que mente.

### D9 — P3-10: a cota **sai**, não muda de lugar — **DECIDIDA**

O acumulador de `proporcional` vive na instância do `Degradador`, fora das cinco
camadas de `01` §4, e a P3-10 mostra as duas consequências: reinício zera a cota,
e rollback devolve a flag sem devolver o acumulador.

**A saída óbvia — persistir o acumulador — é a errada**, e por duas razões que se
somam. Business State é *"notas, matrículas, submissões, documentos"*; um
contador de recusas não é isso. E derivá-lo do event store exigiria um evento por
requisição, que é Fase 5 (trilha) e Fase 8 (instrumentação).

**A forma nova elimina o estado em vez de realocá-lo**, e é mais fiel ao que a
flag declara. `flags.yaml` diz *"fração de **sessões** de prova em andamento
derrubadas"* — e a cota por requisição derruba a **mesma sessão** de forma
intermitente, que não é o que está escrito.

A decisão é uma função determinista, sem memória: a sessão cai quando
`h(RANDOM_SEED, sujeito, rota) < taxa`. Quatro propriedades, e as três últimas
são o que a pendência cobrava:

| | |
|---|---|
| **sem estado** | não há o que ficar fora das cinco camadas |
| **estável no reinício** | o mesmo exercício, o mesmo conjunto de sessões |
| **estável no rollback** | a taxa volta ao valor anterior e **exatamente as mesmas sessões** voltam a cair |
| **monótona na taxa** | subir a taxa só **acrescenta** sessões; nunca troca o conjunto |

**O limite, declarado:** `floor(n·taxa)` exato deixa de valer. O que passa a
valer é a fração sobre o conjunto de sessões, que é o que a flag diz. E o
sujeito vem do `sub` do token — requisição sem token não chega ao degradador,
porque `autoriza` roda antes, e isso já tem teste desde o M2 da Fase 3.

### D10 — P3-11: guarda de boot do adapter — **DECIDIDA**

Flag citada em `api_surface.yaml` e ausente do estado corrente devolve `None`, e
a rota **não degrada, sem nada avisar**. O CI cobre; o runtime não.

A guarda tem a forma que `06` T2 já exige do engine — *"flag não declarada
impede boot, com mensagem nomeando flag e arquivo esperado"* — aplicada ao
adapter, no ponto em que ele é montado. É `01` §5.4 (*"nenhum serviço lê ou
escreve flag não declarada"*) deixando de ser verdade só no repositório.

O par que discrimina vem junto: uma guarda que sempre recusasse passaria em
metade do teste.

### D11 — P3-2: **medir antes de escolher** — **DECIDIDA**

A pendência foi redatada na Fase 3 por ter sido datada por *proxy* — "quando o
FastAPI chegar" — em vez de pela condição que ela descreve. **A condição é o
primeiro processo que serve requisições concorrentes, e ele é desta fase.**

A ordem é a que a P2-10 fixou e que já se mostrou certa: **medir** quantas
reconstruções ocorrem com N leituras simultâneas sobre cache frio, e só então
decidir se há single-flight e onde. Mecanismo sem consumidor custou caro duas
vezes nesta linhagem.

**Se a medição mostrar que não morde, a pendência fecha com número** — e não com
opinião.

### D12 — o reinício é provado no **container** — **PROPOSTA**

O item 4 da DoD diz *"reinício do **container** do engine"*. Provar no processo e
declarar o container como limite seria trocar a condição por um proxy — que é
exatamente como a P3-2 venceu sem que a condição dela ocorresse (§7.2 da Fase 3).

O que isso implica, e é por isso que é PROPOSTA:

1. o CI constrói a imagem e reinicia o serviço — custo de minutos por PR;
2. **a stack efêmera da auditoria ganha o mesmo serviço**, senão o teste de
   container **pula** na auditoria, e pulo silencioso lido como verde é
   exatamente o que a P2-19 atacou. `WORKFLOW.md` já diz que a stack do worktree
   *"faz parte do que se audita"*.

O teste cobre os dois níveis — processo e container — e o par de T5 em cada um:
pausado restaura pausado, retomado restaura correndo.

### D13 — o pack do DEMO é o `pack_minimo` do fixture — **DECIDIDA**

`A01` já tem `academus.enrollment_offline: true` e `texto_para_plateia`, que é
exatamente o que o roteiro pede. O pack real é entregável da **Fase 7**, e
escrever um aqui anteciparia fase — o mesmo argumento que a Fase 2 usou para não
escrever `range-cli`.

### D14 — o índice de saúde: a fórmula é inventada aqui, então é declarada aqui — **DECIDIDA**

`01` §5.3 pede *"número único no telão, a partir dos `severity_weight` ativos"* e
**não dá a fórmula**. Inventá-la sem declarar seria a pior das duas coisas:
número no telão que ninguém sabe reproduzir.

Duas definições, e a primeira é a que quase se erra:

- **"Ativa" é `valor ≠ default`, e não `valor verdadeiro`.**
  `academus.federated_session_active` tem default `true`: quando ela **cai**, as
  sessões federadas foram revogadas, e o telão tem de piorar. Ler "ativa" como
  "verdadeira" inverteria o sinal justamente na flag de identidade.
- **Flag `number` contribui em proporção**, normalizada pelos `min`/`max` do
  contrato; `boolean` e `enum` contribuem com o peso cheio quando saem do
  default.

O índice é `100` menos a fração do peso total que está ativa, e as três
propriedades vão para teste: nenhuma flag fora do default dá **100**; peso maior
baixa mais; e o número é reprodutível a partir de `flags.yaml` mais o estado —
sem nada guardado em lugar nenhum.

---

## 4. Ordem das peças

| | Peça | Por que nesta posição |
|---|---|---|
| 0 | **aparato**: P3-4 e P3-8 | as duas vencem antes deste checkpoint, e as duas mudam o que o auditor consegue medir |
| 1 | **superfície do range-api** declarada + o verificador generalizado (D4, D6) | antes de existir rota, como na Fase 3 |
| 2 | **projeções de sala**: painéis por taxonomia, índice de saúde, timeline, frame total (D2, D3, D14) | funções puras, testadas sem servidor |
| 3 | **reconstrução do exercício** a partir do store: T0, acumulado, multiplicador, origem de epoch, pausa | é o item 4 da DoD e T5, e não depende de HTTP |
| 4 | **o range-api**: HTTP + WebSocket + autenticação do gm-console (D5) | a latência do item 2 é medida aqui |
| 5 | **`academus-api` sobre Postgres**: P3-5, P3-10, P3-11 (D8, D9, D10) | o adapter deixa de perder estado no reinício |
| 6 | **as três telas** (D1, D2) + build no CI | o cliente é o último porque não tem lógica |
| 7 | **containers, DEMO ponta a ponta, reinício de container** (D12) + medição da P3-2 (D11) | é onde a fase inteira vira uma sequência só |

**A peça 0 vem antes por medida, e não por hierarquia:** sem ela a auditoria
desta fase mediria com o aparato que ela conserta, e a procedência do núcleo
executado seria suposição — que é o item 2 do que a primeira auditoria da Fase 3
não conseguiu verificar.

**Uma volta por peça**, com a checagem escrita no mesmo commit que o mecanismo —
e o caminho que se vai entregar **rodado antes de entregar**, que é a segunda
metade da lição da §7.3.1 e a única que não depende de atenção.

---

## 5. O procedimento desta fase, e o que muda

**A auditoria vem antes do merge.** É a primeira vez, e as consequências são
três:

1. **A árvore principal e o worktree ficam em SHAs diferentes de verdade** — a
   P3-4 deixa de ser latente. É a D0.
2. **Um `spec-change` que apareça no meio vira PR próprio e é mergeado primeiro**,
   a branch é rebaseada, e **a âncora é regravada no mesmo commit do rebase**.
   `WORKFLOW.md` §"`spec-change` primeiro" fixa a ordem; foi o H1 da terceira
   rodada da Fase 3.
3. **`gh pr merge --rebase`.** `--squash` é o único caminho que escapa das duas
   metades do predicado ao mesmo tempo, e o furo está declarado em
   `check_audit_base.py` e em `WORKFLOW.md`.

---

## 6. Pendências

Nenhuma aberta nesta fase ainda. As seis abaixo são **recebidas da Fase 3**, com
a peça que as vence.

| Id | O que é | Vence em |
|---|---|---|
| P3-2 | cache frio sem single-flight: leituras concorrentes reconstroem N vezes | **peça 7** — medir antes de escolher (D11) |
| P3-4 | no worktree de auditoria, `range_core` vem da árvore principal | **peça 0** (D0) |
| P3-5 | business state em dicionários de módulo | **peça 5** (D8) |
| P3-8 | dois falsos bloqueios do hook do auditor | **peça 0** |
| P3-10 | `Cota` é estado mutável fora das cinco camadas de `01` §4 | **peça 5** (D9) |
| P3-11 | flag declarada e ausente do estado vira no-op silencioso | **peça 5** (D10) |

A **P2-6** — a ligação declarativa de `participant_action` a flag — continua
datada para a **Fase 8**, e não é desta. A premissa original dela era falsa e o
registro da Fase 3 §2 tem a correção.

#### P3-2 — cache frio sem single-flight

Duas leituras concorrentes num cache frio reconstroem duas vezes, e cada
reconstrução custa o que a §3.8 da Fase 2 mediu — 2,874 s em 150 mil eventos.

**A condição que a pendência descreve ocorre nesta fase**, e desta vez pelo nome
e não por proxy: o primeiro processo que serve requisições concorrentes é o
container da peça 7. Ver a **D11** — a ordem é medir, depois escolher.

#### P3-4 — no worktree de auditoria, o core vem da árvore principal

`domains` e `contracts` resolvem pelo worktree; `range_core` resolve pela
**árvore principal**, porque a instalação editável grava caminho absoluto e
`range-core` tem hífen — não é importável pela árvore.

**Esta é a fase em que a pendência sai de latente**, e pelo motivo que a nota
corrigida dela previu: com auditoria antes do merge, a árvore principal e o
worktree ficam em commits diferentes de verdade, e um commit na principal
*durante* a auditoria trocaria o núcleo sob os testes do auditor sem sinal
nenhum. Ver a **D0**, que é PROPOSTA justamente porque muda o critério de
reprovação do auditor no PR que ele vai auditar.

#### P3-5 — business state em dicionários de módulo

As três entidades e `Matricula` são `dataclass` em memória. `02` §7 diz
*"academus-api — FastAPI + **SQLAlchemy**"* e `01` §4 põe Business State em
Postgres, com a linha *"não reversível por rollback; só por reset total"*.

**A linha passa a ser falsa nesta fase**, porque é a primeira em que existe um
container que reinicia — e reinício não é reset total. Ver a **D8**.

#### P3-8 — dois falsos bloqueios do hook do auditor

`->` dentro de string citada lido como redirecionamento, e *path* de URL lido
como caminho absoluto fora do worktree. Os dois matam comandos que o auditor
precisa para **medir**, e `WORKFLOW.md` classifica bloqueio indevido como
defeito — foi a lição do H4 da primeira auditoria da Fase 0.

**Vencimento declarado na Fase 3: antes do checkpoint desta fase.** É a peça 0.
A correção troca grafia por decisão sobre o **alvo** — não há caminho gravável em
`-> degrada`, e `/turmas/{turma_id}/diario` não existe como caminho —, e os eixos
de `scripts/phase0_negative_tests.py` crescem **nas duas direções**: escrita
conhecida que continua bloqueada, e estes dois comandos que passam a rodar.

#### P3-10 — `Cota` é estado mutável fora das cinco camadas

O acumulador de `proporcional` vive na instância do `Degradador`, é chaveado por
`(rota, flag)` e não deriva de nenhum evento. Reinício zera a cota; rollback
devolve a flag e não devolve o acumulador.

Ver a **D9**: a decisão é **eliminar** o estado, e não realocá-lo — e a forma
nova é mais fiel ao que `flags.yaml` declara sobre a flag.

#### P3-11 — flag declarada e ausente do estado vira no-op silencioso

`estado.flags.get(entrada.flag)` devolve `None` para flag que o estado corrente
não tem, e aí `ligada` não dispara e `proporcional` lê `0.0`. A rota não degrada,
e nada avisa. O gate protege o repositório; não protege o exercício em curso.

Ver a **D10**: a guarda de boot só tem sentido onde há boot, e o boot é desta
fase.

---

## 7. Próxima fase

`07` Fase 5 — **Dados e auditoria ⏸**. ENTRY: Fase 4 completa.
