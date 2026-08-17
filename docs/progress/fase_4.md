# Fase 4 — VERTICAL SLICE ⏸

**Status: EM CURSO — as sete peças fechadas; falta a auditoria de checkpoint.**
A branch nasceu em `6efca2e` e foi **rebaseada sobre `486df18`** quando o
`spec-change` da P4-9 entrou em `main` — a âncora está gravada em
`docs/process/phase_anchors.tsv` e foi **regravada no mesmo passo**, que é o item
3 do procedimento de `WORKFLOW.md` §"`spec-change` primeiro". Não é formalidade:
sem regravar, `check_audit_base.py` recusa a rodada com *"a ancora ficou
desatualizada"* — e recusa com razão, porque o ponto de bifurcação mudou de
verdade.

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

### D0 — o aparato primeiro: a peça 0 é P3-4 e P3-8 — **APROVADA, e implementada**

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

> **Aprovada, com três condições do operador, e as três estão na peça:**
> a linha da rede fica **escrita** em `WORKFLOW.md` (§"Onde passa a linha da
> rede"), senão a próxima pessoa que precisar de rede lê o venv como precedente;
> a instalação **falha alto** — auditoria contra o núcleo da árvore principal
> porque o `pip` falhou em silêncio é pior que auditoria que não roda; e o teste
> dos três pacotes é provado **reprovando**, com divergência plantada, e não só
> passando. Ver a §4.1.

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

#### E há um padrão de onde essas afirmações moram: **docstring**

A observação é do operador, e conferi na fonte em vez de concordar: **`Fase 4`
aparece 13 vezes no código**, em 10 arquivos, e **todas** em docstring ou
comentário — nenhuma em contrato, em YAML declarativo ou em teste que a exerça.

```text
range-core/engine/inject_engine.py      3     range-core/state/cache.py           1
range-core/state/simulation_state.py    2     range-core/engine/loader/*.py       2
tools/check_event_envelope.py           1     domains/academus/api/{app,surface}  2
tests/{test_api_tokens,test_inject_engine}.py 2
```

**Por que a docstring, e não outro lugar:** é o único sítio onde escrever *"isto
é da fase seguinte"* não custa nada. Contrato exigiria campo, teste exigiria
asserção, o registro tem `check_progress_consistency.py` cruzando tabela com
seção — a docstring não tem gate nenhum, e é por isso que a afirmação vai parar
lá. Não é desleixo: é o caminho de menor resistência funcionando.

**A regra que sai disso é barata e entra no procedimento da fase:** ao abrir a
Fase *n*, `grep -rn "Fase <n>"` no código é **a lista das promessas que vencem
agora**. Cada citação é uma de duas coisas — um item que esta fase entrega, ou
uma frase que esta fase torna falsa —, e as duas exigem leitura no começo, não
no fim. As 13 desta fase estão lidas: doze descrevem entregas das peças 3 a 7 e
seguem verdadeiras; a décima terceira é a de `exercise_reset`, que a D7 corrige.

Não vira verificador. Um gate que cruzasse citação com fase teria de decidir o
que uma frase em português afirma, e o custo de errar é falso bloqueio em
comentário — que é caro e inútil. Vira **leitura de entrada de fase**, que é
onde ela cabe.

### D8 — P3-5: as três tabelas em Postgres, e o que **não** é seed — **DECIDIDA**

`01` §4 põe Business State em Postgres e o declara *"não reversível por rollback;
só por reset total"* — **falso a partir do momento em que existe um container que
reinicia**, e esse momento é esta fase. Fase que torna uma linha normativa falsa
é onde a linha se conserta.

Escopo: as três tabelas e a migration. **Sem seed** — `07` Fase 5 é dona do
*"seed em escala com bulk insert"* e do determinismo por `RANDOM_SEED` (T8).

> **"As três tabelas" estava errado, e são quatro — corrigido na peça 5.** O
> número veio das três entidades que `07` Fase 3 nomeia, e a P3-5 nomeia
> **quatro** dicionários de módulo: `MATRICULAS` é um deles.
>
> **A autoria do erro é das duas partes, e isso está escrito porque a omissão
> tem leitura própria.** Eu escrevi "as três tabelas" contando a lista de
> entidades; o operador ratificou a decisão sem conferir contra a P3-5. Nenhum
> dos dois abriu a pendência que a decisão dizia fechar. Registrar só um lado
> deixaria a leitura de que foi descuido de quem escreveu — e o defeito não é de
> redação: é de **procedimento**, e um procedimento que só uma parte executa não
> tem revisão.
>
> É a mesma classe do L1 daquela auditoria: *número afirmado diz de que conjunto
> é, e é contado na fonte dele no momento em que se escreve*. Aqui a fonte era a
> pendência, e não a lista de entidades — e a regra que sai disso é barata:
> **decisão que declara fechar uma pendência é conferida contra o texto dela, e
> não contra a memória de qual era o escopo.**

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

### D12 — o reinício é provado no **container** — **APROVADA**

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

> **Aprovada, e com a exigência de fechar as duas pontas no mesmo commit:** CI e
> stack efêmera da auditoria. Se só o CI ganhar o serviço, a correção existe onde
> ninguém julga e falta onde alguém julga — e o teste **pula** na auditoria, que
> é o que a P2-19 atacou.

#### D12 revisada na peça 7 — a segunda ponta deixou de existir, e por isso não é exceção

**A exigência acima comprava uma proteção precisa: que o teste de container não
`pule` na auditoria.** Ela pressupunha a forma que a decisão tinha em mente — um
`unittest` que, sem stack, se marca como pulado, e pulo silencioso é lido como
verde.

**A peça 7 escolheu outra forma, e a escolha removeu a condição em vez de
atendê-la.** O reinício de container e o DEMO são **passos de CI**, na forma que
a Fase 2 fixou para o DEMO: um `run:` que falha reprova o job. **Passo de CI não
pula.** A proteção que a exigência comprava não tem o que proteger neste formato.

**E a exigência, aplicada assim mesmo, custaria sem entregar.** Acrescentar as
duas APIs ao `docker-compose.audit.yml` faria o lançador construir a imagem —
Node mais `pip install` — **a cada rodada de auditoria**, e **não daria ao
auditor a capacidade de rodar as provas**: `docker` está fora da allowlist pelo
mesmo argumento da P2-19, que recusou pôr rede na mão do julgador.

**O que o auditor verifica por leitura, e é o que sustenta a revisão:** que os
passos existem no workflow; que nenhum deles tem `continue-on-error`, `|| true`
ou `if: always()`; e que `Dockerfile` e compose dizem o que os scripts supõem. O
que ele **não** verifica é a execução — e isso vale igualmente para o
`demo_fase2.py` desde a Fase 2, com o mesmo estatuto.

**Isto é revisão da decisão, e não exceção a ela.** A diferença importa: uma
exceção deixaria a regra valendo e abriria um caso; a revisão diz que a regra
mudou de escopo — **a segunda ponta é exigida quando a prova puder pular**, e não
quando ela for passo de CI. Escrever isto como exceção ensinaria que a D12 se
contorna quando dá trabalho, que é o oposto do que aconteceu.

> **Ratificada pelo operador**, com o argumento aceito nestes termos: *"passo de
> CI não pula, então a proteção que a D12 comprava não existe nesse formato, e o
> custo seria real sem dar capacidade ao auditor"*.

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

### D15 — a corrida da árvore compartilhada ganha impedimento, e não convenção — **APROVADA, e implementada**

A corrida de `WORKFLOW.md` §"Árvore de trabalho compartilhada" ocorreu **três
vezes**, e as três foram pegas por alguém lembrar de conferir. Detecção por
memória não é detecção — é a mesma distinção entre regra e propriedade que a §1.6
da Fase 1 estabelece, e que já motivou mecanizar o guarda de branch uma vez.

**Por que o guarda de branch não alcança.** Ele é `pre-commit`: olha para onde o
commit vai cair. A corrida acontece **antes de existir commit** — `HEAD` se move
durante uma *leitura*, e o dano se torna durável na **escrita** que vem depois
dela, com base numa árvore que já não é aquela. Entre a leitura e o commit há uma
janela inteira que hoje não tem nada.

**A proposta move a guarda da hora do commit para a hora da escrita**, que é o
primeiro instante em que o dano é observável e ainda reversível. São três pernas,
e a segunda é a que teria pego a terceira ocorrência.

| | Quando | O que faz | Severidade |
|---|---|---|---|
| **1** | `SessionStart` | grava `<branch>` e `<sha>` num sentinela da sessão, em `.git/` | — |
| **2** | `PreToolUse` de `Write`/`Edit` | se `HEAD` está na branch **default**, **recusa** | bloqueio |
| **3** | `PreToolUse` de `Write`/`Edit` | se a branch **mudou** desde o sentinela, **recusa**, nomeando as duas | bloqueio |

**A perna 2 é a que fecha a terceira ocorrência, e ela não é a perna 3.** Naquele
caso a árvore **já estava** em `main` quando a sessão começou: um sentinela que
só comparasse "mudou desde o início" teria gravado `main` como âncora e não
diria nada. A perna 2 não compara com nada — ela afirma uma propriedade do
projeto: *`CLAUDE.md` diz uma fase = uma branch, então escrita de trabalho nunca
nasce na default.* É o `pre-commit` existente, adiantado da hora do commit para a
hora da primeira escrita, e nesse ponto ele custa **um arquivo** em vez de uma
sessão inteira.

**A perna 3 exige re-ancoragem explícita**, e é isso que a torna mecanismo: depois
de uma troca de branch legítima, alguém roda o comando que atualiza o sentinela.
Enquanto não rodar, as escritas continuam recusadas. Sem esse passo explícito, a
guarda viraria um aviso que se aprende a ignorar.

**Mudança de SHA na mesma branch NÃO bloqueia, e a assimetria é deliberada.**
Commit do operador na mesma branch é normal; `pull` reescrevendo arquivo sob uma
leitura é a segunda ocorrência registrada — e essa metade **já tem cobertura**: o
próprio harness recusa `Edit` de arquivo que mudou em disco desde o `Read`, e ele
recusou duas vezes durante a peça 5. Acrescentar bloqueio por SHA seria ruído
sobre uma propriedade que já existe. Onde não se sabe, **bloqueia**; onde se sabe
que é normal, não.

**O que ela não faz, e está dito porque não faz:**

- **Não previne a corrida** — detecta antes de a escrita se tornar durável. A
  leitura já feita continua velha, e a mensagem diz para reler. Nenhum mecanismo
  alcança a leitura que já aconteceu.
- **Não alcança o lado do operador.** Ele edita por fora do harness, e hook de
  ferramenta não vê isso.
- **É guarda local, não gate**, com o mesmo estatuto do guarda de branch: quem
  clonar sem `bootstrap.sh` não a tem, e escrita por outro caminho a contorna. A
  proteção real de `main` continua sendo a branch protection.

**Duas alternativas recusadas, e o motivo de cada uma.** *Worktree separado para
o agente* — já recusado em `WORKFLOW.md`, porque `start_checkpoint_audit.sh` fixa
um caminho e a confiança de workspace do Claude Code é por caminho; nada mudou
nisso. *`git checkout` automático de volta* — um agente que move `HEAD` para
consertar corrida de `HEAD` é um agente que move `HEAD`: piora o problema
compartilhado e pode atropelar uma troca deliberada do operador.

**Custo:** um `git symbolic-ref` por `Write`/`Edit`, na casa de milissegundos.

**Onde mora:** `user-scope/hooks/sentinela_de_branch.py`, instalado por
`bootstrap.sh` em `~/.claude/hooks/` e ligado em `~/.claude/settings.json` por
merge idempotente.

**Fora da árvore, e o argumento ficou mais forte ao implementar.** A proposta
dizia "como o guarda de branch"; ao escrever, o motivo se mostrou uma variante
direta do que tira o auditor daqui: **um guarda que mora na árvore que ele guarda
desaparece com ela.** Em `.claude/hooks/`, um `checkout` para um commit anterior
a D15 levaria junto o hook **e** a configuração dele — exatamente na situação
para a qual ele existe. `check_architecture.py` pode morar lá porque ele julga o
*conteúdo* do que se escreve; este julga *onde* se escreve, e a resposta depende
de o guarda existir depois de `HEAD` se mover.

**O custo disso, e o que o paga:** hook de escopo de usuário vale para toda a
máquina, e recusar escrita em `main` seria errado na maioria dos projetos. Ele se
auto-escopa por `docs/spec/00_MASTER_SPEC.md` na raiz do repositório e sai calado
fora daqui — e há probe para essa direção.

**Falha aberta na infraestrutura, fechada na propriedade.** Entrada ilegível,
`git` ausente, alvo fora de repositório, `HEAD` destacado, projeto que não é este:
**sai 0**, porque são os casos em que o hook não sabe — e um hook global que
derrubasse a sessão por não saber seria pior que o problema. As duas condições que
ele conhece saem **2**. A lista de "sai 0" é explícita em vez de ser o `except` do
fim, porque `WORKFLOW.md` classifica bloqueio indevido como defeito.

**A re-ancoragem exige o nome digitado**, e a mensagem de recusa **não** traz o
comando pronto para colar — o nome aparece no diagnóstico, e quem re-ancora o
compõe. `scripts/reancorar_sessao.py` recusa nome que não bate com `HEAD` e recusa
a branch default, que é o que mantém a perna 2 incondicional.

**Dez direções em `scripts/phase0_negative_tests.py`**, e as seis últimas são os
limites: as três pernas; re-ancoragem legítima libera; re-ancoragem com nome
errado recusa; re-ancoragem para a default recusa; escrita fora da árvore não
bloqueia; repositório que não é o AURORA não bloqueia; `HEAD` destacado não
bloqueia; e a cópia instalada é idêntica à fonte.

**A allowlist do auditor foi decidida no mesmo commit, e a decisão é "nada novo
entra"** — que é diferente de não ter decidido, e é a lição do B1 da Fase 2.
`phase0_negative_tests` já estava na lista e é ele que prova as três pernas;
`reancorar_sessao` fica **fora** porque escreve, e dar ao julgador uma operação de
escrita é a separação de papéis que o auditor não ter `Write` existe para manter.
Os três motivos estão escritos dentro do `readonly_bash.py`.

### D16 — o telão mostra saúde, área e as três piores — **DECIDIDA**

**O número que decidiu, e ele foi calculado antes de escrever tela.** Regra de
legibilidade confortável — altura de caixa alta ≥ distância/200 — dá, a 10 m,
~50 mm. Numa tela de 55" 1080p isso é fonte de ~113 px: **7 a 8 linhas na tela
inteira, ~34 caracteres por linha**. Numa de 75", ~10 linhas e ~46 caracteres.

**O payload de hoje está 2 a 4× acima disso.** Medido em `flags.yaml`: 13 flags,
**7 painéis, 13 itens**, cada um rotulado pelo `effect_ui` — mediana **59
caracteres**, máximo 80. No tamanho de telão cada rótulo quebra em duas linhas:
~26 linhas contra um orçamento de 8. **Não é problema de CSS** — nenhuma escolha
de fonte resolve 26 linhas em 8.

**E `07` já dizia "dois painéis"**, não sete. A peça 6 renderiza uma **seleção**,
e a parte que não é óbvia é que a seleção tem de ser **por convenção**: uma lista
de dois nomes de grupo no código quebraria a promessa de `01` §5.3 (*"adicionar
flag não exige tocar no wallboard"*) e reprovaria o probe da peça 2, que planta
uma flag num grupo inexistente e exige o painel novo.

O telão carrega três coisas, e nada mais:

| | O que é | Por quê |
|---|---|---|
| **índice de saúde** | um número, dominante | três dígitos a 113 px é a única coisa sem disputa de espaço |
| **painéis como blocos** | grupo, ativos/total, cor por `category` | responde *onde*, e é `01` §5.3 — derivado, não listado |
| **os N piores ativos** | `effect_ui` dos de maior `severity_weight` | responde *o quê*, limitado por construção |

**A ordenação por severidade é o que reconcilia as duas fontes.** Ela é
convenção derivada do próprio `flags.yaml`, então flag nova entra na disputa sem
ninguém tocar no cliente — e o corte em N mantém o "wallboard mínimo" de `07` sem
uma lista fixa em lugar nenhum.

**A alternativa recusada foi "só os ativos, texto completo".** Ela distingue
exatamente o que quebrou, e não tem limite superior: no pico do exercício estoura
o orçamento, e no início mostra tela vazia — que a sala lê como wallboard
quebrado, e não como exercício ainda calmo. O índice resolve os dois extremos
porque **sempre** tem valor.

**O que o telão deixa de distinguir, dito:** o texto integral de tudo o que está
degradado. Quem precisa disso é o facilitador, e ele tem o gm-console autenticado.
A plateia recebe a narrativa pela `/plateia`, que `01` §6 já separa para isso.

### D17 — o corte de telão é propriedade do PAYLOAD, e não do CSS — **DECIDIDA**

`wallboard()` passa a emitir o que cabe no telão — blocos, destaques e a
contagem do resto —, em vez de emitir tudo e deixar o cliente escolher.

**Isso converte metade do limite da §2.2 em teste.** O orçamento vira propriedade
de servidor: *"nunca mais de N destaques, qualquer que seja o estado"*, com o pior
caso — todas as flags ativas — exercido. O que sobra como limite declarado é a
pergunta genuinamente física, e ela deve continuar sem teste: **113 px lê a 10 m
naquela sala?**

É a D2 aplicada onde ela mais rende: cada pedaço de lógica que descesse para o
cliente subiria para o limite declarado, e o limite declarado é o único lugar
onde defeito não fica vermelho.

**Consequência de segurança, e ela é ganho:** o payload público deixa de carregar
o `effect_ui` de tudo e passa a carregar o de três. A varredura de `06` T6
continua a mesma, sobre uma superfície menor.

### D18 — as duas superfícies são independentes; a montagem da sala fica para a peça 7 — **DECIDIDA**

Não está decidido se wallboard e `/plateia` ocupam uma tela ou duas, e a peça 6
**não supõe**: cada rota é legível sozinha, com o orçamento inteiro.

**O custo é uma decisão adiada, e ela tem lugar** — a peça 7, onde container e
deploy aparecem. Se for uma tela só, o orçamento se parte ao meio e o telão fica
praticamente sem texto de item; a D16 já é a opção que sobrevive a isso, porque
o índice e os blocos não dependem do espaço que o texto ocupa.

**O que não pode acontecer é a peça 6 escolher por omissão** — entregar uma rota
que só faça sentido dentro da outra, e descobrir na peça 7 que a sala tem dois
projetores. Duas rotas independentes é a decisão que não fecha porta nenhuma.

### D19 — a casca do console é pública; o dado atrás dela não é — **DECIDIDA na peça 6, e depois com fonte normativa**

> **O texto abaixo é o da peça 6, e a primeira frase dele deixou de ser
> verdadeira — de propósito.** `05` §8 isentava **duas** superfícies quando esta
> decisão foi escrita, e hoje isenta **três**: o `spec-change` de `486df18`
> acrescentou a casca estática do `gm-console` e a rota que troca credencial por
> token. O parágrafo fica como está porque é a §1.6 — ele descreve o commit em
> que foi escrito, e reescrevê-lo apagaria justamente o fato de que a decisão
> viveu um tempo sem fonte. **Foi o M1 da primeira auditoria**, e o que o fechou
> está na P4-9.

`05` §8 isenta de autenticação **wallboard e participant-view**, e `GET /console`
é uma terceira rota pública. **A decisão está aqui, e não numa linha de YAML**,
porque `CLAUDE.md` diz que `05` não admite flexibilização *silenciosa* — e o
oposto de silenciosa é esta seção.

**O fato mecânico:** nenhum navegador envia `Authorization` numa navegação. A
casca de um console de browser é necessariamente alcançável sem token, e é por
isso que `POST /session` **já é pública desde a peça 4** — a superfície já
aceitou um ponto de entrada sem credencial para o mesmo console.

**O que `05` §8 protege é serviço exposto, e o serviço é o dado.** O que esta
rota entrega é HTML, CSS e JavaScript: nenhum inject, nenhum
`texto_para_plateia`, nenhuma credencial. Injects, timeline e os quatro comandos
continuam exigindo token pelo middleware, que **falha fechado** — caminho que
ninguém declarou público exige token, e há teste para `/rota-que-nao-existe`
respondendo 401.

**As três metades são teste, e não argumento:**

| | Onde |
|---|---|
| as duas telas públicas não conhecem o console | `tests/test_telas.py`, na fonte, e `prova_do_build.sh`, no artefato |
| **nenhuma tela carrega nome de flag, id de inject ou texto de cenário — fonte e bundle** | `scripts/check_telas_sem_vocabulario.py`, nos dois jobs |
| toda rota que o console chama responde 401 sem token | `tests/test_range_api.py`, desde a peça 4 |

> **A linha do meio não existia quando esta decisão foi escrita, e a tabela dizia
> que existia.** A versão original tinha duas linhas, e a primeira afirmava *"a
> casca não carrega dado de exercício"* com `tests/test_telas.py` como prova. **O
> que aquele teste prova é a direção inversa** — que as telas públicas não
> mencionam o console. Ninguém olhava para vocabulário de exercício dentro do
> cliente.
>
> **Achado por uma pergunta do operador**, e a pergunta é a certa: casca pública
> que vaza vocabulário é o canal lateral que o `403 × 404` da peça 1 da Fase 3
> fechou — não é o dado que vaza, é a **existência** dele. Medido antes de
> corrigir:
>
> | | Estado antes |
> |---|---|
> | nome de flag em fonte `.ts`/`.tsx` | **coberto** — invariante 2, `check_contract_literals.py` |
> | nome de flag no **bundle** `.html` | **coberto por nada** — `.html` não está em `WEB_SUFFIXES` |
> | id de inject, título, texto de plateia | **coberto por nada, em lugar nenhum** |
>
> A correção é a §4.7 — *"O verificador que a pergunta do operador exigiu"*.
> Registrar isto aqui, e não só lá, é a §1.6: a afirmação errada morava **nesta
> tabela**, e é aqui que alguém a leria como fonte.

**As alternativas, e por que nenhuma serve.** *Autenticar `GET /console`* torna a
tela inalcançável por navegação — não é mais seguro, é inoperante. *Não servir o
console pelo `range-api`* só muda o processo que entrega o mesmo arquivo, e
acrescenta um serviço à peça 7 para não responder a pergunta. *Emitir o token por
linha de comando e colar no console* já foi recusado na D5, e pelo motivo que
continua valendo: o item 1 da DoD é literalmente *"sem intervenção manual"*.

### D20 — a sala tem **dois** destinos, e a participant-view não é telão — **DECIDIDA na peça 7**

A D18 adiou a montagem física para cá, com destino. Ela vence agora, e a resposta
mudou de forma ao ser escrita: **a pergunta "uma tela ou duas?" tinha uma
premissa errada**, e a premissa era que a participant-view é uma tela de sala.

`01` §6 a chama de **participant-view**, e o nome é a resposta: é a projeção *do
participante*, e o lugar natural dela é o dispositivo de cada um. O wallboard é
que é o telão — *"sem login, alto contraste, legível a 10 m"*.

| Superfície | Onde | Por quê |
|---|---|---|
| `wallboard-shell` | **o telão da sala**, um por sala | o orçamento de 10 m foi calculado para ele inteiro (D16) |
| `participant-view` | **o dispositivo do participante**, e opcionalmente um segundo telão | é projeção por pessoa; `01` §6 dá a ela a narrativa, e não o estado |
| `gm-console` | a máquina do facilitador | autenticado, e é o único que opera |

**A decisão não custa nada porque as rotas já são independentes** — foi
exatamente isso que a D18 protegeu ao recusar escolher por omissão. Se a sala
tiver dois projetores, `/plateia` ocupa o segundo com o orçamento inteiro; se
tiver um, o telão fica com o wallboard e a narrativa vai para os dispositivos.
Nenhum dos dois casos exige tocar em código.

**O que fica declarado como limite:** se alguém decidir pôr as duas numa tela só,
o orçamento de texto se parte ao meio — e a D16 já é a opção que sobrevive a
isso, porque o índice e os blocos não dependem do espaço que o texto ocupa.

### D21 — o bind é `0.0.0.0` dentro do container, e a fronteira de `05` §6 é o host — **DECIDIDA na peça 7**

`05` §6 diz *"Bind em `127.0.0.1`"* e *"nenhuma porta publicada diretamente no
compose de produção"*. Um container que fizesse bind em `127.0.0.1` **dentro do
próprio namespace de rede** seria inalcançável — nem pelo container vizinho —, e
a leitura literal produziria uma stack que não sobe.

**A fronteira que a linha protege é a do host**, e ela é observável em dois
lugares que ficam lado a lado:

| | |
|---|---|
| default da **imagem** | `AURORA_BIND_HOST=127.0.0.1` — **fechado** |
| quem abre | o `docker-compose.yml`, com `0.0.0.0`, na linha imediatamente acima da que publica a porta |
| o que a porta faz | `127.0.0.1:8000:8000` — loopback do host, e mais lugar nenhum |

**O default fechado é a metade que importa:** quem rodar a imagem sem o compose
não expõe nada por acidente, e abrir exige escrever `0.0.0.0` ao lado de onde a
publicação aparece. É a mesma disciplina do `papeis: []` da Fase 3 — o
desconhecido não é público.

**O compose de produção é outro arquivo, e ele não existe ainda.** Este é o de
desenvolvimento, e publica no loopback porque alguém precisa abrir o telão. A
segunda metade de `05` §6 — *"nenhuma porta publicada no compose de produção"* —
vence quando existir deploy, e não é desta fase.

### D22 — a P3-2 fecha com número, e o número diz onde ela volta — **DECIDIDA na peça 7**

A D11 fixou a ordem: **medir, depois escolher**. Medido com a stack no ar,
`scripts/mede_cache_frio.py`:

| Configuração | 20 leituras simultâneas, cache frio | Reconstruções |
|---|---|---|
| **1 worker** (o do compose) | 20 conexões | **1** |
| **4 workers** | 20 conexões | **4** |

**A pendência não ocorre como escrita, e a razão não é single-flight.** A rota é
`async def` com corpo **síncrono**: a corrotina roda até o fim sem ceder o laço,
então o segundo leitor só começa depois que o primeiro já gravou o cache. Não há
voo concorrente para unificar.

**E o segundo número é o que redata a pendência com precisão:** o custo é
limitado pelo número de **workers**, e não pelo de leitores. Com 4 workers são 4
reconstruções — uma por laço de eventos —, e a 150 mil eventos cada uma custa os
2,874 s da §3.8 da Fase 2.

**Decisão: nenhum single-flight agora.** Mecanismo sem consumidor custou caro
duas vezes nesta linhagem, e a medição diz que o consumidor não existe: o deploy
desta fase tem um worker. O que sobra é a **P4-8**, com a condição escrita e o
limite medido — e ela carrega junto a face maior do mesmo fato, que é o laço
bloqueado.

---

## 4. Ordem das peças

| | Peça | Por que nesta posição |
|---|---|---|
| 0 | **aparato**: P3-4 e P3-8 ✅ | as duas vencem antes deste checkpoint, e as duas mudam o que o auditor consegue medir |
| 1 | **superfície do range-api** declarada + o verificador generalizado (D4, D6) ✅ | antes de existir rota, como na Fase 3 |
| 2 | **projeções de sala**: painéis por taxonomia, índice de saúde, timeline, frame total (D2, D3, D14) ✅ | funções puras, testadas sem servidor |
| 3 | **reconstrução do exercício** a partir do store: T0, acumulado, multiplicador, origem de epoch, pausa ✅ | é o item 4 da DoD e T5, e não depende de HTTP |
| 4 | **o range-api**: HTTP + WebSocket + autenticação do gm-console (D5) ✅ | a latência do item 2 é medida aqui |
| 5 | **`academus-api` sobre Postgres**: P3-5, P3-10, P3-11, P4-1 (D8, D9, D10) ✅ | o adapter deixa de perder estado no reinício |
| 6 | **as três telas** (D1, D2, D16, D17, D19) + build no CI ✅ | o cliente é o último porque não tem lógica |
| 7 | **containers, DEMO ponta a ponta, reinício de container** (D12) + medição da P3-2 (D11) ✅ | é onde a fase inteira vira uma sequência só |

**A peça 0 vem antes por medida, e não por hierarquia:** sem ela a auditoria
desta fase mediria com o aparato que ela conserta, e a procedência do núcleo
executado seria suposição — que é o item 2 do que a primeira auditoria da Fase 3
não conseguiu verificar.

**Uma volta por peça**, com a checagem escrita no mesmo commit que o mecanismo —
e o caminho que se vai entregar **rodado antes de entregar**, que é a segunda
metade da lição da §7.3.1 e a única que não depende de atenção.

---

## 4.1 A peça 0 — o aparato, e o que ele mediu

Duas pendências, e as duas mudam **o que o auditor consegue medir**. Nenhuma
linha de produto nesta peça.

### A P3-4 reproduzida, e ela era pior do que a pendência dizia

A pendência media três pacotes e apontava um. **Rodando o teste novo dentro do
worktree de auditoria, com o python do ambiente**, saíram **sete** falhas:

```text
range_core, range_core.events, range_core.events.envelope, ...
  -> C:\Projetos\aurora-cyber-range\range-core\...   (ARVORE PRINCIPAL)
contracts e montado a partir de 2 diretorios:
  [.../.aurora-worktrees/audit/contracts, .../aurora-cyber-range/contracts]
```

A segunda linha é o achado que eu não tinha previsto: `contracts` não vinha de
uma árvore **nem** da outra — vinha **das duas ao mesmo tempo**. Pacote de
namespace se compõe, e o `sys.path` do worktree mais o caminho da instalação
editável montam um pacote só com módulos de dois commits. É a "procedência
misturada" da pendência na forma mais literal possível, e um teste que só
perguntasse "veio daqui?" responderia *sim* para a metade contida.

Por isso a asserção da quimera é separada, e por isso ela conta **diretórios
distintos**: medido, o `contracts` de uma árvore sadia aparece **duas vezes** em
`__path__` — uma pelo `sys.path`, outra resolvida pelo gancho do instalador —,
e contar entradas acusaria a árvore certa.

### A primeira formulação reprovou na primeira execução, e a correção mudou o objeto

O teste afirmava sobre `__path__`. A instalação editável de PEP 660 injeta ali
uma entrada **sintética** — `__editable__.aurora_cyber_range-0.1.0.finder.__path_hook__` —
que não é diretório e nunca estará sob raiz nenhuma. A regra reprovaria toda
árvore com instalação editável, que são todas.

A saída **não** foi ignorar entrada inexistente: é justamente pelo gancho que a
outra árvore continua alcançável. Foi trocar o objeto da asserção — **de onde
veio o código que rodou**, e não onde o importador poderia ter procurado. A
varredura é sobre `sys.modules`, e num `discover` ela cobre tudo o que a suite
inteira importou, porque unittest importa todos os módulos de teste antes de
rodar qualquer um.

**O limite ficou declarado:** módulo que exista **só** na outra árvore continua
alcançável pelo gancho, e este teste não o veria enquanto ninguém o importasse.

### O venv, medido nos dois sentidos

| | Resultado |
|---|---|
| worktree, python do ambiente | **7 falhas** — o núcleo vinha da árvore principal |
| worktree, python do venv do lançador | **OK**, e a suite inteira roda: **228 testes** a partir do worktree |
| custo | **20 s**, com o cache do pip quente |
| árvore auditada suja depois da instalação? | **não** — `git status --short` no worktree, vazio |

**A falha alta foi exercitada, e não só escrita:** com o `WT` apontando para um
diretório sem `constraints.txt`, o bloco sai com `rc=1`, imprime as últimas
linhas do `pip.log` e diz por que para. Era condição do operador, e é o caso que
importa — auditoria que segue contra o núcleo errado porque o `pip` falhou em
silêncio produz veredito sobre outro commit.

### E o caminho que eu ia entregar estava quebrado — pego rodando

A primeira versão do lançador fazia `pip install -e "$WT[test]"`. O pip **recusa**
essa forma: *"is not a valid editable requirement"*. Nenhuma leitura pegaria —
a linha está correta em intenção, em aspas e em variável. Corrigida para
`(cd "$WT" && pip install -e ".[test]" -c constraints.txt)`, num subshell para
não mexer no diretório de quem chama.

É a §7.3.1 da Fase 3 aplicada de novo, e desta vez a lição funcionou como
antídoto em vez de como diagnóstico: **rodar o caminho que se vai entregar não
depende de atenção.**

### A P3-8, e por que ela não é "isentar `>` citado"

A pendência avisava que isentar citação desfaria a ordem que a oitava auditoria
da Fase 0 impôs. **A regra implementada não isenta citação: ela implementa a
semântica de aspas que o bash dá a `>`.** Dentro de aspas — simples ou duplas —
`>` não redireciona nada, e a regra anterior estava lendo outro shell.

É o mesmo conserto da 16ª auditoria, na direção oposta: lá,
`_substituicao_ou_subshell` deixou de usar máscara única porque `$(` **executa**
dentro de aspas duplas. A regra que sai das duas é uma: cada construto é
decidido com a semântica que o bash lhe dá.

**O que sustenta a segurança não é a máscara.** Para um `>` citado virar
redirecionamento, algum comando precisa reinterpretar a string como shell —
`sh -c`, `bash -c`, `eval`, `xargs`, `python -c`. Nenhum está na allowlist, e
isso é propriedade de whitelist: comando novo nasce bloqueado. Sete probes novos
afirmam os cinco, mais as duas quedas para o texto cru (aspas escapadas e aspas
não fechadas).

**O path de URL saiu por DUAS condições que valem juntas**, e nenhuma basta
sozinha — que é o desenho:

| | |
|---|---|
| só inexistência | `pytest --basetemp=/c/outra/arvore` **cria** o diretório |
| só leitor puro | `cat /c/Projetos/...` lê a árvore principal, e ler fora mede outra árvore |

`tree` e `sort` ficam **fora** da isenção com a forma de escrita nomeada
(`tree -o`, `sort -o`), e há probe para cada um. `git` também fica fora, e o
custo disso está declarado como falso bloqueio residual: path de URL em
argumento de `git log -S` segue bloqueado, e a leitura continua obtenível por
`grep`.

**E o teste de existência tinha um defeito de plataforma que só a medição
mostra:** no Git Bash o caminho absoluto é `/c/Projetos/...`, e
`os.path.exists` do Python de Windows resolve isso contra a raiz da unidade
corrente — diria *"não existe"* exatamente para o caminho real da árvore
principal, que é o alvo que a contenção mais precisa negar. As duas grafias são
testadas, e há probe para cada uma.

### Medido, velho contra novo

| | |
|---|---|
| comandos que passaram de `rc=2` para `rc=0` | **7** — as três setas, a ordem `autoriza -> degrada`, e três formas de path de URL |
| controles que **seguem** em `rc=2` | `git log > out.txt`, `sh -c "echo x > out.txt"`, `ls <fora>` |
| leituras legítimas liberadas pelo harness | **56**, eram 47 |
| eixos de bloqueio novos | **15** — 7 de reinterpretação de shell, 6 de alvo existente fora (3 formas × 2 grafias), 2 de comando que escreve com alvo inexistente |
| falsos bloqueios declarados | **8**, eram 10 — três fechados, um novo declarado |
| suite | **228 testes**, eram 223 |

A cópia instalada em `~/.claude/hooks/` foi sincronizada, e o harness confere as
duas — a divergência apareceu como **FAIL** antes da sincronia, que é o
mecanismo funcionando.

---

## 4.2 A peça 1 — a superfície do `range-api`, antes de existir rota

`range-core/api_surface.yaml`: **13 rotas declaradas, zero implementadas**, e o
verificador já roda. É a forma da peça 2 da Fase 3, e ela funcionou lá pelo
motivo que continua valendo — o que se declara antes do código não é a lista, é
a **obrigação**.

O verificador é **o mesmo**, generalizado: `scripts/check_api_surface.py` passou
de 36 para **66 eixos de prova negativa**.

### A generalização, e o que ela deixa de provar

A pergunta do operador é a certa: *um verificador parametrizado que aceite
qualquer par vira mais frouxo que dois específicos.* Vira — se o par for
argumento. **A generalização aqui é sobre as superfícies, e não sobre as
regras**, e a diferença é exatamente essa.

Não existe "papéis permitidos" e "papéis recusados" como parâmetro de chamada.
Existe **uma âncora** — `PAPEIS_DE_EXERCICIO`, os três de `03` §7 — e cada
perfil se relaciona com ela de um jeito **fixo**:

| Perfil | Relação com a âncora | O que reprova |
|---|---|---|
| `nucleo` | **igualdade**, nas duas direções | papel de domínio na lista; âncora encolhida |
| `dominio` | **disjunção** | papel de exercício na lista (o buraco da peça 2) |

Encolher a âncora reprova, e isso importa mais do que parece: era por ela que a
disjunção do outro lado se sustentava. Sem esse eixo, tirar `facilitador` da
lista do núcleo afrouxaria a guarda do adapter **sem tocar no adapter**.

**As três coisas que a generalização deixa de provar, e nenhuma é hipótese:**

**1. Família só roda onde o perfil a reivindica — e isso tem data.** Antes havia
uma superfície, e toda regra rodava nela. Agora, quando a `academus-api` passar
a emitir evento — Fase 5 pela trilha, Fase 8 pela instrumentação —, a família
`eventos` **não roda lá**, e "não declarar `emite`" é legítimo no perfil de
domínio. **Não é buraco novo** (o verificador nunca olhou emissão em código),
e é pior que isso: agora ele *parece* cobrir eventos. É a §7.3 da Fase 3 — a
verificação que parece existir — entrando pela porta da generalização.
Mitigação parcial, e ela é real: `emite` é campo **proibido** no perfil de
domínio, então declará-lo lá reprova alto. O que ninguém pega é emitir **sem**
declarar.

**2. A classificação é declaração minha, e superfície no perfil errado seria
verificada pelas regras erradas.** Duas metades fecham quase tudo: a tabela é
conferida **nas duas direções** contra o disco — superfície nova sem perfil
reprova, e não degrada para um perfil padrão —, e **perfil trocado é
barulhento**, porque os vocabulários de chave são disjuntos: com os perfis
invertidos, `flags` vira campo desconhecido e `efeito` vira campo obrigatório
ausente. Isso é *consequência* de como as chaves foram escolhidas, e não regra
escrita — então há eixo afirmando que cada perfil tem vocabulário exclusivo. Sem
ele, dois perfis que viessem a se sobrepor fariam a troca voltar a ser
silenciosa, e o probe de hoje continuaria verde porque olha os arquivos de hoje.

**3. Nada sobre o payload.** A igualdade byte a byte entre frame e snapshot está
**declarada e não medida**. A prova vem com o produtor, na peça 2 — e a rota só
passa a `implementada` junto dela.

**O que ela ganhou, e não tinha:** whitelist de chaves por perfil, nas duas
direções. Campo desconhecido reprova, e **campo obrigatório ausente também** — a
direção que importa, porque regra que só roda quando o campo existe se desliga
apagando o campo. Foi a forma da `degradacao` como prosa na Fase 3: declarada,
lida por ninguém, até a peça 5.

### D3 na declaração: a sala e quem reconecta veem o mesmo

O frame do WebSocket e o snapshot HTTP têm de ser o mesmo payload para o mesmo
estado. Antes de existir código, o que dá para afirmar é a declaração — e ela já
pega o caso que ninguém veria depois:

| Eixo | Por quê |
|---|---|
| canal e snapshot com **projeções diferentes** | duas serializações do mesmo fato divergem |
| canal e snapshot com **visibilidades diferentes** | a assimetria entra pela porta da **autorização**: canal público com snapshot autenticado, e cada um está certo sozinho |
| canal **sem** snapshot | "refresh recupera o estado corrente" não teria de onde acontecer |
| **um** canal e **um** snapshot por projeção | dois produtores do mesmo payload é a divergência esperando |
| projeção usada e não declarada; declarada e não usada | as duas direções, como sempre |

E o canal é rota como qualquer outra: a varredura por AST passou a enxergar
`@app.websocket(...)`. **Sem isso, um canal implementado ficaria invisível ao
eixo mais forte da checagem** — "implementada e não declarada" —, e o buraco
teria o tamanho da única superfície com WebSocket. Há probe.

### As rotas operam o exercício, e a superfície diz o que não tem volta

`01` §4.2 dá ao console quatro comandos com semânticas muito diferentes, e um
botão que dispara inject por engano não tem desfazer. O vocabulário é fechado:

| `efeito` | O que é | Exige |
|---|---|---|
| `nenhum` | não move o exercício | `emite` **proibido** |
| `reversivel` | existe comando inverso | `inverso`, e **mútuo** |
| `irreversivel` | não tem volta | `confirmacao: true` |
| `destrutivo` | irreversível **e** descarta o estado corrente | `confirmacao: true` |

**`destrutivo` não quer dizer que apaga história**, e a linha está no próprio
YAML porque a leitura errada inverteria a garantia central do event store:
`00` §5.5 e `01` §4.2 são explícitos — rollback não remove evento nenhum,
incrementa epoch. O que ele descarta é a projeção corrente.

Três eixos que valem nomeados:

- **inverso de uma seta só reprova.** Se A declara B como inverso, B tem de
  declarar A. Uma seta só faria "reversível" virar rótulo — e é o rótulo que a
  interface vai ler para decidir se pede confirmação.
- **confirmação onde não há o que confirmar também reprova.** Confirmar o que
  tem volta treina o operador a clicar "sim", e é assim que a confirmação do que
  **não** tem volta deixa de ser lida.
- **rota que move o exercício não pode ser pública.** `05` §8 isenta de
  autenticação apenas wallboard e participant-view, que *olham* o exercício.

### A quarta porta do nome de evento

`emite` é conferido contra `contracts/events.schema.yaml`: é a quarta porta pela
qual um `event_type` entra no sistema — depois do código, do pack e da spec —, e
as outras três já tinham guarda. **E a camada junto:** comando de console emite
`facilitation`, e não outra coisa. Emitir `participant_action` por aqui
misturaria máquina de exercício com fato do incidente, que é a confusão que
`00` §3 existe para impedir.

O extrator do catálogo tem probe próprio, pelo motivo de sempre: um catálogo
lido como `{}` deixaria os eixos de camada verdes **pelo caminho errado** —
acusariam "não está no catálogo", que é outro eixo.

---

## 4.3 A peça 2 — as projeções de sala, e a igualdade medida

`range-core/api/projecoes.py`: quatro funções puras — `wallboard`, `plateia`,
`timeline` e o serializador. **Nenhuma delas conhece HTTP**, e é por isso que a
peça inteira é testável sem servidor.

### A igualdade byte a byte deixou de ser declarada

Os cinco eixos da peça 1 provam que canal e snapshot existem **em par**. Nenhum
deles prova que os dois **produzem o mesmo** — e essa era a metade que faltava.

**A decisão que a torna verificável: as projeções devolvem `bytes`.** Devolver
`dict` deixaria cada rota serializar, e o mesmo fato escrito duas vezes diverge:
o `JSONResponse` do FastAPI não ordena chaves nem usa os separadores de um
`json.dumps` escrito à mão, e **nenhum teste que compare estruturas acusaria**.
Com `bytes`, o snapshot e o frame não têm por onde discordar — é a forma da peça
3 da Fase 3 outra vez: em vez de detectar a divergência, retirar o material com
que ela se escreve.

O serializador é um só, e cada opção fecha um caminho: `sort_keys=True`
(ordenação), `separators=(",", ":")` (estilo), `ensure_ascii=False` +
`.encode("utf-8")` (fronteira de byte, e acento em UTF-8).

**Os três caminhos de divergência, e o que fecha cada um:**

| Caminho | Fechado por | Como fica vermelho |
|---|---|---|
| ordenação de chave | `sort_keys` | dois dicionários de mesma chave em ordens diferentes |
| **carimbo de geração** | ausência do material | teste por **AST**: o módulo não importa `time`, `datetime`, `random`, `secrets` nem `uuid` |
| **tipo que muda no transporte** | — | o estado que atravessou o **Redis de verdade** contra o que saiu do fold |

O segundo é afirmado por estrutura de propósito. Provar por comportamento
exigiria montar duas vezes em instantes diferentes e concluir por **ausência de
diferença** — a asserção de ausência que passa também quando nada é observável,
que é o H1 da segunda auditoria da Fase 3.

**O terceiro é o que mede, e ele discrimina — plantado e medido:**

```text
$ # com {k: bool(v) ...} plantado na serializacao do RedisProjectionCache
FAIL: test_o_estado_que_passou_pelo_redis_produz_os_MESMOS_bytes
  b'{"indice_de_saude":15,...}' != b'{"indice_de_saude":0,...}'
```

**15 contra 0.** A taxa de queda de 0,4 volta do Redis como `True`, vira peso
cheio, e o telão mostraria saúde **zero** enquanto quem reconecta veria **15** —
para o mesmo estado. É exatamente o L1 da terceira auditoria da Fase 3, agora
com a consequência visível em vez de latente. Revertido, 20/20.

### O sinal do índice de saúde, fixado pelo par

A D14 inventa a fórmula, então o teste fixa o sinal. **"Ativa" é `valor ≠
default`**, e o par que prova são duas flags de **mesmo peso e defaults
opostos**: as duas têm de piorar o índice na mesma magnitude.

**Medido:** com `esta_ativa` trocado para `valor is True`, **seis testes ficam
vermelhos** — inclusive `test_sem_nada_fora_do_default_a_saude_e_plena`, porque
a flag de default `true` passaria a contar como ativa **em repouso**. Revertido,
20/20.

E há o caso real, contra `flags.yaml` e não contra fixture:
`academus.federated_session_active` é a única flag de default `true` do adapter
— **conferido no teste**, não lembrado —, e revogá-la tem de **baixar** o
índice. Com o sinal invertido, revogar acesso melhoraria o telão.

> **O hook recusou a primeira versão deste teste**, e recusou com razão: eu
> escrevi o nome da flag como literal. Nome de flag em código é o erro de
> digitação que o invariante 2 existe para pegar, e a constante gerada existe
> para isso. Segunda vez nesta fase que o hook aponta para o desenho certo.

### Os painéis são derivados, e o probe planta onde não há painel

`01` §5.3 promete que *"adicionar flag não exige tocar no wallboard"*. A flag
plantada cai num `wallboard_group` que **não existe** — e a categoria dela
também não está no conjunto de partida. Plantar num grupo existente provaria
menos: o item apareceria por herdar um painel que já estava lá, e uma lista fixa
de grupos passaria no teste.

**Medido:** agrupando por `category` em vez de `wallboard_group` — o erro
plausível —, o teste fica vermelho. Revertido, 20/20.

**Uma nota sobre a categoria, medida e não suposta:** os **sete** valores de
`category` de `01` §5.2 estão todos em uso em `flags.yaml`, então não existe
"categoria sem painel" para plantar no conjunto real. O probe usa fixture, onde
o conjunto de partida tem duas categorias e a plantada é a terceira.

### O que a sala não pode ver

`06` T6 é teste de **payload**, e as duas superfícies desta peça são as que
`05` §8 deixa sem autenticação — não há token entre elas e a rede.

- **O wallboard não carrega nome de flag.** `academus.enrollment_offline` é
  vocabulário de mecanismo; o que vai ao painel é o `effect_ui`, que
  `flags.yaml` escreve em linguagem de negócio desde a Fase 1. Varredura
  recursiva sobre o payload inteiro.
- **A plateia recebe um campo, e a garantia é do tipo.** `plateia` recebe
  `Mapping[str, str]` — `inject_id → texto_para_plateia` — e não o inject.
  `linha`, `descricao_facilitador`, `objectives` e `decision_point` **não estão
  ao alcance**: vazar exigiria mudar o chamador. É a D6, e é por isso que
  `pack_loader.Inject` continua sem esses campos — há teste afirmando isso.

`LoadedPack` ganhou `textos_para_plateia`, e só isso. A narrativa do
facilitador não entra ainda, e a ausência é a §7.3 aplicada: a checagem que a
guarda só pode ser escrita quando existir o consumidor, e ele é o gm-console da
peça 4.

### A whitelist do core disparou, e foi o mecanismo funcionando

`check_core_contract_imports.py` reprovou o import novo de
`contracts.generated.events`. Era exatamente o desenho — *"o custo de acrescentar
é uma conversa, e é esse o ponto"* —, e o argumento que o admitiu é o mesmo dos
outros três: a timeline rotula por `event_type` e a plateia acha o inject
corrente pelo `inject_fired`; literal de catálogo dentro do core violaria o
invariante 2. **É leitura, e não emissão** — o módulo não chama `append` e não
tem store ao alcance.

**248 testes, zero pulos com Redis no ar** (eram 228).

---

## 4.4 A peça 3 — a reconstrução do exercício, e o par de cada um dos cinco

`range-core/clock/restauracao.py`: `derivar` responde **cada** pergunta
separadamente, e `restaurar` monta o clock. **Duas funções e não uma**, e o
motivo é o teste: um teste que só olhasse o clock mediria os cinco por
consequência, e um erro de T0 e um erro de acumulado produzem o mesmo
`exercise_timestamp`.

| Valor | De onde vem |
|---|---|
| **T0** | `exercise_timestamp` do `exercise_started` — no instante do start o decorrido é zero, então aquela marca **é** o T0 |
| **acumulado** | `exercise_timestamp` do último evento, mais o trecho desde o `wall_timestamp` dele |
| **multiplicador** | `clock_multiplier` do último evento. `09` §1.1 o grava em cada evento *"para reconstrução"*, e esta é a reconstrução |
| **origem de epoch** | `decorrido(evento) − rótulo(evento)`, de qualquer evento da epoch corrente |
| **pausa** | `paused_in`, sobre o par `exercise_paused`/`exercise_resumed` |

### O reinício não congela o exercício, e isso é da spec

Enquanto o processo esteve fora do ar, o tempo de exercício **correu**. Não é
escolha: `01` §3 fixa que, na falha do range, *"o clock de exercício continua
correndo; apenas a projeção de métricas desconta o intervalo"* — e o desconto é
o `rollback_performed` com `reason: technical_failure`, que grava os extremos
desde a Fase 2.

Restaurar congelado no último evento inventaria uma pausa que ninguém declarou, e
o exercício andaria mais devagar que a sala. **O que congela é a pausa**, e ela é
explícita.

### O par de cada um — e o par é o arquivo inteiro

*Reinício pausado restaura pausado* passa com um engine que sobe **sempre
pausado**. Cada um dos outros quatro tem a sua forma de passar sem restaurar
nada, e por isso cada valor é medido com **dois fluxos que só diferem nele**.

**Medido, uma mutação por vez:**

| Mutação plantada | Testes vermelhos |
|---|---|
| T0 fixo no código | **8** |
| acumulado nasce em zero | **6** |
| **multiplicador sempre 1x** | **4** — inclusive `test_um_exercicio_em_5x_NAO_restaura_em_1x` |
| origem de epoch sempre zero | **4** |
| sobe sempre pausado | **4** — inclusive o par de T5 numa asserção só |

O multiplicador é o que o operador nomeou como mais fácil de enganar, e por isso
ele tem **duas** formas independentes de ser observado: o campo derivado, e a
conversão do tempo fora do ar. Um `derivar` que lesse o fluxo para o campo e
usasse 1x na conta passaria na primeira e falharia na segunda.

### O que é provado no container, e o que não é

**Nenhum dos cinco, nesta peça.** A resposta direta, porque a pergunta é a
certa: chamar processo de container seria trocar a condição por um proxy, que é
o que a P3-2 custou a esta linhagem.

| Nível | O que prova | Onde |
|---|---|---|
| função pura | a derivação: os cinco valores a partir de um fluxo | **peça 3** |
| **processo novo** | os cinco atravessando o **Postgres** e uma fronteira de processo real — outro interpretador, nada compartilhado além da tabela | **peça 3** |
| **container** | o *wiring*: imagem, entrypoint, caminho de configuração, rede e volume | **peça 7** |

**O item 4 da DoD continua aberto**, e é isso que esta linha registra. O que a
peça 3 fecha é a **lógica**; o que o container acrescenta não é aritmética, é a
montagem — e é a montagem que a DoD nomeia.

O teste de processo novo não é decoração: ele prova que os cinco sobrevivem à ida
e volta pelo banco. `subprocess`, `python tests/_restaura_em_outro_processo.py`,
e a asserção contra os cinco valores esperados.

### `paused_in` lê os dois eventos — conferido na fonte

A P2-13 existiu porque `exercise_paused` sem nada depois é o mesmo fluxo para
*"ainda pausado"* e para *"retomado, e nada aconteceu desde então"*. Conferido no
código e fixado em teste: `paused_in` desliga a pausa em `exercise_resumed`,
`exercise_started` e `exercise_reset`, e o teste percorre `pausado → retomado →
pausado` exigindo veredito diferente em cada passo. Um `paused_in` que só olhasse
`exercise_paused` devolveria `True` nos três.

E a heurística que pareceria salvar o caso — *evento posterior implica retomada* —
tem teste próprio afirmando que é **falsa**: `01` §3 bloqueia o disparo agendado
na pausa e §6 mantém o manual, então um `inject_fired` depois da pausa é
compatível com o exercício ainda parado.

**`paused_in` mudou de casa**, de `inject_engine` para `clock/restauracao`: quem
restaura precisa dela antes de existir engine, e duas cópias divergiriam na
primeira correção. Uma implementação, dois chamadores — a §1.4 do checkpoint da
Fase 2.

### Duas coisas que a suíte achou, e a segunda é defeito de verdade

**1. O harness de mutação acusou a mudança de casa.** `fonte_mutada` exige que a
linha alvo case **exatamente uma vez**, e casou zero: *"a linha alvo mudou de
forma, e a prova negativa deixou de plantar o que diz plantar"*. É a guarda
funcionando — prova negativa que deixa de plantar é prova que passa sem provar.

**2. O harness vazava módulo mutado para o resto do processo.** O registro em
`sys.modules` ficava **fora** do `try/finally`: com um mutável registrado e o
seguinte levantando — que é exatamente o caso acima —, os já registrados nunca
eram restaurados. **Toda a suíte seguinte rodava contra código mutado**, com as
falhas aparecendo longe da causa.

Quem achou foi o `test_procedencia_dos_pacotes` da **peça 0**, que é literalmente
a pergunta *"de onde veio o módulo que executou?"*: ele acusou `pack_loader`
vindo de um arquivo temporário. A P3-4 fechava a divergência entre **árvores**;
esta é a mesma pergunta dentro de **um processo só** — e o teste escrito para uma
pegou a outra.

**Medido depois da correção:** com a âncora quebrada de propósito, o único teste
vermelho é o do próprio harness. O vazamento não acontece mais.

### Duas docstrings da Fase 2 ficaram falsas aqui, e foram corrigidas aqui

`inject_engine` afirmava que *"T0, o acumulado, o multiplicador e a origem da
epoch continuam sendo estado do clock que um processo novo não recupera"*. Era
verdade quando escrita, e esta peça é quem a torna falsa. É a §1.6 da Fase 1 — e
é a nota da D7 valendo na prática: as duas afirmações estavam em **docstring**, o
único sítio onde datar uma promessa não custa nada.

**267 testes, zero pulos com a stack efêmera no ar** (eram 248).

---

## 4.5 A peça 4 — o `range-api`, e a primeira vez que dá para ver

`range-core/api/app.py`, `hub.py`, `superficie.py`: **18 rotas implementadas**,
todas declaradas antes na peça 1. O verificador cobrou a promoção de `planejada`
para `implementada` no mesmo commit, que era o desenho.

### A igualdade mudou de objeto — e a medição derrubou uma frase minha

Até a peça 2 a igualdade era sobre a **função**. Aqui é sobre as **duas rotas**,
e o que se compara é **o que trafega**: `response.content` de um lado,
`receive_bytes()` do outro.

Eu escrevi que o defeito que isso pega é trocar `Response(content=...)` por
`JSONResponse`. **Plantei, e não pega — zero testes vermelhos.** O
`JSONResponse` do FastAPI usa `separators=(",", ":")` e `ensure_ascii=False`, que
são as mesmas opções do serializador da peça 2, e como aquele já emite as chaves
**ordenadas**, um `loads`/`dumps` devolve os mesmos bytes.

**Isso não é buraco — é a forma canônica da peça 2 funcionando**, e muda o
argumento para melhor: a igualdade é verdadeira **pela forma canônica**, e não
pela linha que escolhe `Response`. O que a linha acrescenta é não depender de as
opções do framework coincidirem com as nossas.

**As cinco formas, plantadas e contadas:**

| Divergência plantada | Vermelhos |
|---|---|
| `JSONResponse` (re-serializa com as mesmas opções) | **0** — e está certo |
| re-serialização com separadores padrão | 2 |
| re-serialização com `ensure_ascii` (acento vira escape) | 2 |
| chaves em ordem invertida | 2 |
| **canal mandando texto em vez de bytes** | 4 |

A frase errada está corrigida nos dois lugares onde seria lida — o docstring de
`_json` e o do arquivo de teste. **O teste afirma a propriedade, e não o
mecanismo**: quando o mecanismo muda e a propriedade se mantém, verde é a
resposta certa.

### "< 1 s" sem cronômetro

Número de relógio oscila com a máquina. A forma é a do `EXPLAIN` sem `Seq Scan`
do `_head()`: afirmar a propriedade que produz o desempenho. Aqui são duas, e as
duas são contáveis:

1. **Não há espera.** O frame é produzido na mesma chamada que gravou o evento —
   sem polling, sem intervalo, sem tarefa de fundo. Afirmado por AST: os módulos
   do caminho do frame não importam `time`, `threading` nem `sched`.
2. **Um frame por evento, e não um por cliente.** Com três telas conectadas, um
   disparo custa **uma** reconstrução. Contado por um store instrumentado — que
   não é duplo, é a mesma classe com um contador.

**O limite, com número:** o custo de um frame é o de uma reconstrução, porque a
cabeça do fluxo mudou. A §3.8 da Fase 2 mediu **2,874 s em 150 mil eventos** —
então o orçamento de 1 s vale enquanto o volume couber nele. Fold incremental
seria a saída e **não é desta fase**: exigiria uma porta que aceita estado
pronto, que é o que a peça 3 da Fase 3 tirou do desenho.

**Observado, e como observação e não como critério:** num servidor uvicorn real,
**2 ms** do `POST /injects/A01/fire` até os dois frames chegarem a dois clientes
WebSocket. Máquina do operador, Windows 11, Python 3.12.

### Toda rota que move o exercício publica — e isso é verificado

Esquecer o `publicar` numa rota nova produz o pior defeito desta fase: **o
exercício anda e a sala não vê**. Nenhum teste de comportamento cobre a rota que
ainda não existe — mas a **declaração** já diz quais movem o exercício, e por AST
dá para exigir que todas publiquem. É a coluna `efeito` da peça 1 ganhando o
segundo consumidor.

### Autenticação por middleware, e não por dependência

A `academus-api` usa dependência global e lá basta. Aqui não: **o WebSocket não
passa pelo sistema de dependências do FastAPI da mesma forma**, e uma guarda que
não cobre o canal deixaria de fora justamente a rota que empurra o estado da
simulação. O middleware ASGI vê `http` e `websocket` com o mesmo código.

Falha fechada: a lista é de **isentos**, e caminho que ninguém declarou público
exige token — mesmo argumento do `papeis: []` da Fase 3. Há teste para
`/rota-que-nao-existe` respondendo 401. E `/docs`, `/redoc` e `/openapi.json`
desligados, pela lição da peça 5 da Fase 3 — aqui seria pior, porque esta é a
API que opera o exercício.

**Limite declarado:** canal autenticado não existe. Os dois canais são públicos
por `05` §8, e o navegador não envia `Authorization` no handshake — resolver
exigiria token em query string ou subprotocolo, e nenhum tem consumidor aqui.

### Um teste meu estava errado, e o engine não

A primeira versão do teste de rollback rebobinava para o **próprio**
`inject_fired` e exigia que o wallboard mudasse. Não muda, e está certo: o corte
é **naquele** evento, então o efeito dele sobrevive — `09` §3 desenha a epoch
nova começando depois da âncora, e o registro da Fase 2 diz o mesmo em prosa.

Para a sala ver a projeção voltar, o corte tem de ser anterior ao disparo. O
teste corrigido rebobina para o `exercise_started` e afirma que a projeção volta
a ser **byte a byte** a de antes do disparo.

E a rota responde a epoch **nova**, enquanto o evento carrega a **abandonada** —
as duas certas, e a diferença é de `09` §3. A linha está comentada onde alguém
vai estranhar.

### A página crua — e por que ela não é dívida real

Pedido do operador, fora do plano, e aceito. `range-core/web/sala.html`: HTML
cru, sem build, sem dependência, consumindo os dois canais.

**O que a torna descartável de verdade não é a intenção — são três decisões:**

| | |
|---|---|
| **ela não opera o exercício** | não dispara, não rebobina, não pede token. Há teste varrendo o corpo por `/injects/`, `/exercise/`, `/session` e `Authorization` |
| **ela consome só o que já existe** | os dois canais públicos. Não há endpoint que exista *para* ela |
| **a rota fica, o conteúdo muda** | `GET /sala` está na superfície; a peça 6 troca o arquivo pelo bundle e a rota continua |

Se ela criasse endpoint próprio, ou lesse token, ou tivesse estado local, seria
dívida — porque a peça 6 teria de desfazer alguma coisa. Como ela é uma função
do frame total, jogar fora é apagar um arquivo.

**O que ela paga:** `uvicorn` e `websockets` entram como dependência pinada
(T15), e entram nesta peça de qualquer forma — o container da peça 7 precisa dos
dois, e `websockets` **não** é fecho automático: sem ela o uvicorn recusa o
upgrade com *"Unsupported upgrade request"*, e o canal é o item 2 da DoD.

**Visto rodando, num servidor de verdade e com cliente WebSocket de verdade:**

```text
antes do disparo ..... saude 100
depois do disparo .... saude 90
ativos ............... fracao de sessoes derrubadas, portal de matricula em 503
plateia .............. "O portal de matricula esta indisponivel. A fila..."
observado ............ 2 ms do POST ate os dois frames
```

Registrada como **P4-3**, com destino.

**286 testes, zero pulos com a stack efêmera no ar** (eram 267).

---

## 4.6 A peça 5 — a `academus-api` sobre Postgres, e as quatro pendências

`alembic/versions/0002_business_state.py`, `domains/academus/models/registros.py`,
`domains/academus/api/repositorio.py`, `degradacao.py`, `app.py` e
`domains/academus/seed/demonstracao.py`. **Quatro pendências fechadas na mesma
volta** — P3-5, P3-10, P3-11 e P4-1 —, e elas vieram juntas porque tocam o mesmo
arquivo: separá-las seriam quatro edições do `repositorio.py` e quatro passagens
pelos mesmos testes.

**320 testes, zero pulos com a stack efêmera no ar** (eram 286).

### O que a peça 5 recebeu pronto, e o que a medição corrigiu

As decisões abaixo estavam tomadas antes da peça — D8, D9, D10 e a leitura de
idioma da P4-1 —, e a implementação **mudou duas delas**. As duas mudanças estão
nomeadas onde ocorrem, e nenhuma foi silenciosa.

### A P3-5: quatro tabelas, e a D8 dizia três

**A D8 escreveu "as três tabelas"** lendo as três entidades que `07` Fase 3
nomeia — Aluno, Turma, Nota. **A pendência nomeia quatro dicionários de módulo**,
e `MATRICULAS` é um deles. Deixá-lo em memória fecharia três quartos da pendência
e manteria o defeito no caminho do item 1 da DoD, que é justamente
`POST /enrollment`. São `students`, `classes`, `grades` e `enrollments`.

**O par atravessa PROCESSO, e essa era a exigência.** Reabrir a sessão do
SQLAlchemy no mesmo processo não discrimina: os dicionários de módulo
sobreviveriam a isso e o teste passaria com a implementação errada. O pai escreve
pela rota HTTP de verdade; `tests/_le_business_state_em_outro_processo.py` lê num
interpretador novo, com a tabela como única coisa compartilhada. É a forma que a
peça 3 fixou para o event store, aplicada à camada de baixo de `01` §4.

**Medido, uma mutação por vez** (`tests/test_business_state_probes.py`):

| Mutação plantada | Testes vermelhos |
|---|---|
| a nota volta para um dicionário de módulo | **2** — o de processo novo, e o do diário |
| a matrícula é escrita e **não commitada** | **1** — o de processo novo da matrícula |

A segunda existe porque ela é a vizinha invisível da primeira: dentro do processo
as duas produzem 201 e um objeto válido. Só quem está fora vê a diferença.

**O repositório devolve `dict`, e não instância de modelo.** Objeto ORM fora da
sessão levanta `DetachedInstanceError` no primeiro atributo, e a saída usual —
`expire_on_commit=False` mais confiar em que os atributos já foram carregados —
põe corrida entre o handler e o ciclo de vida da sessão. Serializar **dentro** da
sessão a elimina, e preserva a forma do handler: ele continua escrevendo
`if registro is None` e mais nada.

**Uma sessão por chamada pública, e não por requisição.** Sessão por requisição
traria transação atravessando `autoriza`, `degrada` e o handler — e a degradação
por `latencia` seguraria uma conexão aberta por 2,5 s **por requisição
degradada**, numa rota que o exercício existe para martelar. É o pool acabando
durante a sala.

**Os seis registros entram por caminho nomeado como tal**, `seed/demonstracao.py`,
e não pela migration — migration que insere dado de demonstração afirma que
aquelas linhas fazem parte do esquema. `enrollments` nasce **vazia** de propósito:
o caminho feliz do item 1 é a matrícula acontecendo, e uma tabela pré-carregada
tornaria "matriculou" indistinguível de "já estava lá".

**O que estes testes passaram a custar, dito:** `test_api_rbac.py` e
`test_api_degradacao.py` rodavam sem stack nenhuma e agora **pulam** sem
`AURORA_TEST_DATABASE_URL`. É piora local e nenhuma piora onde se julga — CI e o
lançador da auditoria sobem Postgres e rodam `alembic upgrade head`. A
alternativa, um repositório em memória ao lado do de Postgres só para a suíte,
seria o duplo que testa a si mesmo, e reintroduziria **como duplo** exatamente o
dicionário de módulo que a P3-5 removeu.

### A P3-10: a cota saiu, e as três propriedades foram medidas com mutação

A função é `h(RANDOM_SEED, rota, flag, sujeito) < taxa`, sobre `derive_seed` —
que já existe e já é SHA-256. Uma segunda derivação ao lado seria a classe D4.

**Medido, uma mutação por vez** (`tests/test_queda_de_sessao_probes.py`):

| Mutação plantada | Testes vermelhos |
|---|---|
| **o acumulador da Fase 3 volta** | **4** — monótona, rollback, ordem, e o reinício |
| **`hash()` no lugar de `derive_seed`** | **1** — e é o do subprocesso |
| **o sujeito sai da derivação** | **4** — a fração, o reinício, a ordem, e o par flag/rota |

**Três coisas apareceram só rodando, e duas delas eu não previa.**

**1. `test_a_FRACAO_observada_segue_a_taxa` não acusa o acumulador, e está
certo.** A cota dava `floor(n·taxa)` recusas exatas — a fração era a declarada. O
que ela não dava era o mesmo **conjunto**. Uma suíte que só contasse quantos caem
teria aprovado a implementação que a P3-10 existe para remover, e é por isso que
todas as asserções deste conjunto são sobre conjuntos.

**2. O acumulador derruba o teste de reinício, e eu não previa.** Ele é estado de
módulo, então o que uma classe deixa nele atravessa para a seguinte: o pai
calcula com o contador sujo e o filho, num processo novo, com ele zerado. É
"estável no reinício" sendo violada pelo mecanismo mais literal possível.

**3. A mutação do `hash()` derruba exatamente um teste — o do subprocesso.** Se
derrubasse mais, o subprocesso seria redundante. `hash()` de string é salgado por
`PYTHONHASHSEED` e é **estável dentro de um processo**: a suíte inteira ficaria
verde, e o defeito apareceria como *"o conjunto de participantes fora do ar mudou
depois do reinício do container"* — no dia do exercício.

**O rollback é medido com rollback de verdade**, e não com um `set` reescrevendo
a taxa: `ROLLBACK_PERFORMED` no store real, ancorado num evento real, com o fold
recalculando as flags. Sessenta sujeitos passam pelo HTTP, e o par que impede o
teste de passar sozinho está lá: `antes < depois` estrito antes de rebobinar —
sem ele, uma API que nunca degrada "devolveria" o conjunto vazio perfeitamente.

**Dois limites, e o segundo abre pendência.**

`floor(n·taxa)` exato deixa de valer: o que passa a valer é a fração sobre o
conjunto de **sujeitos**, granulada pelo tamanho do conjunto — com poucos
participantes, do mesmo jeito que uma moeda em três lançamentos não dá metade.

E **a citação da D9 estava incompleta**. Ela cita `flags.yaml` como *"fração de
sessões de prova em andamento derrubadas"*; o texto real termina em **"por
minuto"**. Esta função não implementa cadência: quem cai, cai o exercício
inteiro. Implementá-la exigiria tempo como entrada, que é exatamente o estado que
a P3-10 tirou daqui — e o consumidor que dá sentido à cadência é o Modo "Prova em
andamento" de `07` Fase 8. Virou a **P4-6**, com dono, em vez de ficar como
divergência entre o que a flag promete e o que a rota faz.

### A P3-11: a guarda de boot, com o par e com uma segunda condição

Flag citada em `api_surface.yaml` e ausente do estado corrente **recusa o boot**,
com mensagem nomeando a flag e o arquivo — a forma que `06` T2 exige do loader do
engine. A guarda roda em `montar`, e só quando há degradador: sem ele nenhuma
flag é lida, então não há no-op a impedir.

**O par que discrimina está no mesmo arquivo:** a superfície real, contra o
`flags.yaml` real, **sobe**. Uma guarda que sempre recusasse passaria em metade do
teste — e o teste usa os dois arquivos de verdade, não uma fixture que os imite.

**E há uma segunda condição, que não é a primeira dita de outro jeito:** rota
**pública** que declara `proporcional` também recusa o boot. A flag existe, está
declarada, e ainda assim a queda nunca aconteceria — o sujeito vem do `sub` do
token, e rota pública não tem token. Em tempo de requisição isso apareceria como
"ninguém cai", indistinguível de taxa zero; só o boot pode decidir. O par dela
está junto: `ligada` em rota pública **não** recusa, porque não precisa de
sujeito — a regra "pública não degrada" seria mais forte que o problema.

### A P4-1: os cinco caminhos, e `/plateia` como exceção com fonte

```text
/alunos/{aluno_id}          ->  /students/{student_id}
/turmas/{turma_id}          ->  /classes/{class_id}
/turmas/{turma_id}/diario   ->  /classes/{class_id}/gradebook
/turmas/{turma_id}/notas    ->  /classes/{class_id}/grades
/matricula                  ->  /enrollment
```

Os campos do corpo acompanharam — `aluno_id → student_id`, `turma_id → class_id`,
`valor → value` —, e as tabelas e colunas nascem em inglês pelo mesmo argumento.

**O que continua em português, e não é sobra:** os **valores** de papel
(`aluno`, `professor`, `secretaria`, `financeiro`) são vocabulário de persona,
que `03` §6 e §7 escrevem assim; e as `mensagem` de degradação, que são o texto
que o participante lê — interface está na lista do português.

**O limite, declarado para não parecer inconsistência restante:** nomes de
**módulo e de função interna** continuam em português — `registros`,
`repositorio`, `degradacao`, `superficie`, `restauracao`. Mudá-los é edição em
todo módulo do projeto, nenhum item de DoD os cobre, e a P4-1 é sobre **endpoint**,
que é o que atravessa o fio. O que mudou de idioma foi o que cruza a fronteira: o
caminho, a tabela, a coluna e as classes que mapeiam tabela.

**E a nota do núcleo mudou de força, e a diferença importa.**
`range-core/api_surface.yaml` dizia *"`domains/academus/api_surface.yaml` diverge
disto e não é tocado por esta peça"*. Agora não diverge: `/plateia` deixou de ser
"a exceção entre inconsistências" e passou a ser **a única exceção do projeto**,
com fonte normativa em `01` §6. Exceção com fonte se defende; inconsistência
restante ensina que a convenção é opcional, e a próxima rota nasce em português.

### Três afirmações de fase que esta peça tornou falsas — e corrigiu

A regra da D7 aplicada na entrada da peça, e não no fim:

| Onde | O que dizia | Por que era falsa |
|---|---|---|
| `models/registros.py` | *"tabela, SQLAlchemy e migration: **Fase 5**"* | a migration é desta peça |
| `alembic/env.py` | *"os modelos chegam na Fase 5"* | chegaram agora |
| `api/app.py` | *"cinco rotas... `/matricula`, `/turmas`"* | os caminhos mudaram |

O caso do `env.py` é o mais interessante dos três, porque **o valor não mudou e a
razão sim**. `target_metadata` continua `None`, agora porque a metadata existente
cobre **quatro** das cinco tabelas: `event_store` é do core, é lida por `psycopg`
cru e não tem modelo declarativo — e `autogenerate` contra metadata parcial não
acusaria a ausência, ele proporia `DROP TABLE event_store`. Ligar
`target_metadata` ao `Base` do adapter poria o esquema do event store sob a
metadata de um domain, que é a direção que o invariante 1 existe para impedir,
para ganhar um gerador que ninguém usa.

### Um defeito de INSTRUMENTO, pego pela própria prova negativa

Na primeira execução, as **três** mutações da P3-10 derrubavam
`test_montar_com_flag_ausente_RECUSA` — e nenhuma delas tem relação com a guarda
de boot.

A causa: o módulo mutado define uma classe `FlagNaoDeclarada` **nova**. `app.py`,
já importado, seguia levantando a original, e o `assertRaises` do teste — que
resolve pelo módulo mutado — não a reconhecia. **Falha do instrumento lida como
detecção**, que é a única coisa que uma prova negativa não pode ter.

Corrigido recarregando `app.py` junto, sem mutação, pela ordem de dependência que
o harness já oferece. É o mesmo eixo do vazamento que a peça 3 achou no harness —
*"de onde veio o módulo que executou?"* —, desta vez do lado da identidade de
classe em vez do lado da procedência de arquivo.

### O que esta peça NÃO liga, e tem data

**Nenhum processo monta a `academus-api` ainda.** `engine_do_ambiente` existe e
tem consumidor — a suíte e o leitor de processo novo —, mas quem sobe o adapter
com `uvicorn`, `DATABASE_URL` e `RANDOM_SEED` do ambiente é o **container da peça
7**. Dizer isso aqui é a §7.2 aplicada: mecanismo sem consumidor custou caro duas
vezes nesta linhagem, e o consumidor deste tem data e nome.

---

## 4.6.1 As decisões que a peça 5 recebeu prontas, com a fonte conferida

**Escrito antes da peça, e mantido como escrito.** É registro do que estava
decidido quando ela abriu, e não pauta: o que a implementação mudou está na §4.6,
nomeado onde muda — as quatro tabelas em vez de três, e a citação incompleta de
`flags.yaml` que virou a P4-6.

**Nomes de tabela e de identificador: inglês. Nomes de entidade na prosa:
português — e não é contradição.** `02` §1 lista *"Aluno, Professor, Curso,
Disciplina, Turma…"*, e isso é a nomeação **conceitual** do domínio, em texto
narrativo. `CLAUDE.md` §Idioma põe **identificadores, tabelas, colunas e
endpoints** em inglês. Os dois valem, e não sobre a mesma coisa.

A exceção real é outra e continua sendo uma só: **`/plateia`**, que `01` §6
escreve como caminho literal. Documento normativo prevalece sobre a convenção, e
ela já está declarada no `api_surface.yaml` do núcleo.

**Consequência para a peça 5:** as tabelas e colunas novas nascem em inglês — não
há por que criá-las em português e renomeá-las depois —, as classes de
`registros.py` acompanham, e os **valores de papel** (`aluno`, `professor`,
`secretaria`, `financeiro`) **ficam em português**: são vocabulário de persona,
que `03` §6 e §7 escrevem assim, e não identificador.

**O par da P3-5 tem de atravessar PROCESSO.** Reabrir a sessão do SQLAlchemy no
mesmo processo **não discrimina**: os dicionários de módulo de hoje —
`ALUNOS`, `NOTAS`, `MATRICULAS` — sobreviveriam a isso e o teste passaria com a
implementação errada. A forma é a de `tests/_restaura_em_outro_processo.py`: o
pai escreve, um **interpretador novo** lê. E a mutação que prova: com a escrita
voltando para dicionário de módulo, o filho não encontra a nota.

### A medição que a peça 5 recebe pronta — e ela abre uma pendência

A pergunta do operador sobre a P3-11 era a certa: *flag declarada no adapter e
ausente da superfície é no-op na outra direção?* **É — e foi medido:**

```text
flags que declaram `academus-api` em `consumers`:  12
flags consumidas por alguma rota declarada:         4
sem rota nenhuma:                                   8
```

As oito são `anpd_notification_window_open`, `enrollment_service_state`,
`federated_session_active`, `grade_integrity_suspect`, `research_data_exposed`,
`student_data_exposed`, `transcript_issuance_blocked` e `vpn_mfa_enforced`.

**A direção simétrica não é "flag sem rota" em geral** — flag consumida só pelo
wallboard ou pelo `academus-web` é normal. É **flag que declara a `academus-api`
como consumidora e que nenhuma rota consome**: a declaração afirma um consumo que
não existe.

**E ela não pode virar gate agora**, porque reprovaria a árvore por um motivo
legítimo: a API é deliberadamente mínima (`07` Fase 3 põe *"modelo completo"* nos
NON-GOALS), e as oito têm consumidor previsto na Fase 8. Virou a **P4-4**, com a
forma sugerida — a mesma de `domains/flags_pendentes.yaml`, que a peça 1 da Fase
3 criou para exatamente este tipo de promessa datada.

**O que a peça 5 implementa da P3-11 é a direção decidível hoje:** flag citada em
`api_surface.yaml` e ausente do estado corrente **recusa o boot**, com a mensagem
nomeando a flag e o arquivo — a forma que `06` T2 já exige do loader do engine.

### A P3-10, e a propriedade que o rollback pode quebrar sem ninguém ver

A decisão da D9 é **eliminar** o acumulador, e as três propriedades precisam de
medição, não de argumento:

| Propriedade | Como fica vermelha |
|---|---|
| estável no reinício | mesma sessão, processo novo, mesmo conjunto de recusas |
| **estável no rollback** | a taxa volta ao valor anterior e **exatamente as mesmas sessões** voltam a cair — é a que um acumulador quebra em silêncio, porque a flag reverte e a memória não |
| monótona na taxa | subir a taxa só **acrescenta** sessões; nunca troca o conjunto |

---

## 4.7 A peça 6 — o telão, o corte que virou payload, e as três telas

**Fechada.** A peça atravessou três sessões — a metade de servidor, a guarda do
cliente, e o cliente —, e esta seção registra as três porque conversa não é fonte
versionada.

### O que fechou

`range-core/api/projecoes.py`: `wallboard()` deixou de emitir tudo e passou a
emitir **índice + blocos + os N piores + a contagem do resto** — as D16 e D17,
com o número calculado antes de existir tela.

**Medido no payload real, com as 13 flags ativas:** 7 blocos, **3 destaques, 10
omitidos, 1.019 bytes**. Antes eram 13 itens de `effect_ui`, que no tamanho de
telão são ~26 linhas contra um orçamento de 7 a 8.

**Oito testes novos, e cinco deles são pares:**

| O que fica vermelho | Sem ele |
|---|---|
| nunca mais de 3 destaques, **com tudo ativo** | o orçamento estoura no pico, que é quando o telão importa |
| **e nunca menos de 3, com tudo ativo** | respeitar orçamento devolvendo vazio também "passa" |
| `destaques + omitidos == ativos` | o corte não se anuncia, e a sala lê "três problemas" onde há treze |
| a ordem é **severidade × intensidade** | uma flag grave e quase inativa empurra do telão uma menos grave e no máximo |
| sem nada ativo, o telão **ainda diz alguma coisa** | é o argumento contra "só os ativos": tela vazia lida como wallboard quebrado |
| os blocos não carregam texto de item | o orçamento estoura pela porta que a contagem de destaques não olha |
| no máximo 3 `effect_ui` no payload público | a consequência de segurança da D17, medida em vez de afirmada |
| o bloco pega a cor do **pior** ativo | a 10 m a cor é lida antes do texto, e o painel contaria a coisa errada |

**`paineis()` não foi tocado.** Ele é a derivação por convenção que o probe da
peça 2 guarda — flag plantada num grupo inexistente exige painel novo —, e
`blocos()` deriva *dele*, e não de `specs` outra vez. Duas implementações da
mesma promessa de `01` §5.3 divergiriam na primeira correção.

**Dois consumidores acompanharam no mesmo commit**, e os dois são a §1.6:
`web/sala.html`, que continua sendo a P4-3 e continua descartável; e
`test_range_api.py`, cujo teste de latência lia `painel["itens"]` — a pergunta
dele não mudou, a evidência sim.

> **`web/sala.html` não existe mais** — a metade de cliente desta mesma peça o
> substituiu pelo bundle, e a P4-3 fechou. O parágrafo acima fica como está
> porque descreve o commit em que foi escrito; o que ele afirmava era verdadeiro
> então, e é a §1.6 que manda dizer isto aqui em vez de reescrever.

### A guarda do cliente nasceu antes do cliente

`scripts/check_web_sem_derivacao.py`, na forma da peça 1: o que se declara antes
do código não é a lista, é a **obrigação**. A próxima sessão não consegue
escrever um cliente que deriva sem que isto reprove.

**O risco que ela fecha é preciso, e nenhum teste de payload o alcança:** um
`.sort()` no TypeScript troca *quais três* aparecem no telão, e o teste de
orçamento continua **verde** — ele mede o payload, e o payload continua certo. A
propriedade passa a viver no cliente, que é o único lugar onde defeito não fica
vermelho.

Três regras, e a segunda se sobrepõe à primeira de propósito: métodos de
seleção, ordenação e agregação proibidos; as coleções do payload consumidas **só
por `.map(`**; `.length` em comparação proibido — é assim que um orçamento se
reimplementa no cliente.

**E ela não nasce vacua.** `web/sala.html` já é cliente e já é varrido. Um
verificador que passasse por não ter o que olhar seria a §7.3, e há **probe
exigindo reprovação** com o diretório vazio e com o diretório ausente.

> **A anti-vacuidade deixou de depender do `sala.html`**: com ele apagado, quem
> o verificador varre são as três telas — **12 arquivos**. O probe do diretório
> vazio continua sendo o que garante isso, e não a existência de um arquivo em
> particular.

**A prova negativa achou dois defeitos, e os dois eram meus:**

| O que | Por que só a execução separa |
|---|---|
| a regra 2 estava **frouxa no código** e certa no enunciado | ela reusava a whitelist inteira, e `forEach` passava sobre coleção do payload — a regra 2 virava a regra 1 escrita de novo |
| `_exibe` estourava fora da raiz | `relative_to` levanta, e o probe da vacuidade aponta `WEB` para um temporário: **falha de instrumento no caminho de REPROVAÇÃO**, que só aparece quando o verificador está certo |

Dezesseis direções, e metade delas é o outro lado: `map`, `join`, o agregado
renderizado a partir do **número** do servidor, `.length` sem comparação. Gate de
cliente que bloqueasse `map` seria abandonado na primeira tela — e bloqueio
indevido também é defeito.

**Entrou na allowlist do auditor no mesmo commit** (B1), com a prova negativa ao
lado, e no job `arquitetura`, que não instala nada. O harness passou de 56 para
**58** leituras legítimas.

### O toolchain entrou por container, e a decisão não foi contorno de ambiente

`node` e `npm` **não existem no host**, e a sessão anterior parou aqui de
propósito: escrever um build React/Vite/Tailwind que não se consegue executar
entrega código que nunca rodou — a classe que custou o `pip install -e
"$WT[test]"` da peça 0.

**A decisão do operador foi Node em container pinado por digest, e o argumento
dele é mais forte que "não dá para instalar":** instalar no host resolveria
**uma** máquina. O CI continuaria com a versão que o runner trouxesse, e
passariam a existir duas versões possíveis do toolchain sem nada garantindo que
são a mesma. O container põe o toolchain sob a T15 como qualquer outra
dependência, e o `package-lock.json` fixa o fecho transitivo do mesmo jeito que
`constraints.txt`.

**E a igualdade entre CI e host não precisou de verificador, porque não há duas
declarações.** A imagem é declarada **uma vez**, no serviço `web-build` do
`docker-compose.yml`, e o CI roda o próprio compose:

```yaml
- name: as tres telas compilam, e o gate do build reprova
  run: docker compose --profile build run --rm web-build
```

`check_pinned_images.py` continua cobrando o eixo 1 — digest, e não tag — sobre
essa linha. O eixo 2, a igualdade entre arquivos, **não tem par para comparar
aqui, e isso é construção e não esquecimento**: é a forma da peça 2 outra vez —
em vez de detectar a divergência, retirar o material com que ela se escreve.

**Um custo mecânico apareceu e está pago:** o compose interpola o arquivo
**inteiro** antes de escolher o serviço, e `POSTGRES_PASSWORD` é declarada com
`:?` — sem default, porque `05` §8 proíbe senha trivial reutilizável. Sem a
variável, **qualquer** comando de compose aborta, inclusive um que só roda o
`web-build`. O job passa um valor efêmero que não chega a serviço nenhum, e o
comentário no workflow diz por quê.

### As três telas, e o que o arquivo único retira

| Tela | Rota | O que consome |
|---|---|---|
| `wallboard-shell` | `GET /sala` | `/ws/wallboard` |
| `participant-view` | `GET /plateia` | `/ws/plateia` |
| `gm-console` | `GET /console` | `/session`, `/injects`, `/timeline`, os comandos, e o `/ws/wallboard` **público** |

**Cada tela é UM arquivo** — `vite-plugin-singlefile` inlina JS e CSS dentro do
HTML —, e o que isso retira não é peso: é **a rota de asset estático**. Servir
`dist/assets/*` seria superfície de path traversal num processo cujas outras
rotas disparam inject e rebobinam exercício. Sem assets, cada tela é uma rota
declarada em `api_surface.yaml` e mais nada. Medido: **156, 154 e 159 kB**.

**O console não ganhou projeção própria de estado.** Ele lê o mesmo
`/ws/wallboard` que o telão: duas projeções do mesmo fato divergem, e a que
diverge em silêncio é sempre a que ninguém está olhando — a D4 da Fase 3, que
esta fase já aplicou duas vezes.

**A confirmação está onde a superfície pede, e só onde ela pede.** START, FIRE e
ROLLBACK confirmam porque a declaração diz `confirmacao: true`; PAUSAR e
CONTINUAR não, porque são `reversivel`. É o segundo consumidor da coluna
`efeito` da peça 1, e o primeiro que a sala vê.

### A guarda do cliente, exercida contra o cliente de verdade

Ela nasceu na sessão anterior, antes de existir tela. **Plantado um `.sort()` na
lista de destaques do wallboard, as duas regras dispararam** — a de método
proibido e a de coleção do payload, que se sobrepõem de propósito:

```text
range-core/web/wallboard-shell/main.tsx:96
    `.sort(` seleciona, ordena ou agrega - e o cliente PINTA.
range-core/web/wallboard-shell/main.tsx:96
    `destaques.sort(` - as colecoes do payload so sao consumidas por `.map(`.
```

Revertido, **12 arquivos varridos e verde**. O verificador deixou de depender do
`sala.html` para não ser vácuo: agora ele olha o cliente que a fase entrega.

### O gate do build, MEDIDO — e ele roda em toda execução, não uma vez

O risco era específico de frontend e está confirmado: **`vite build` não checa
tipos**. Ele transpila com esbuild e sai **0** com o TypeScript quebrado.

**Medido, com um erro de tipo plantado em código que entra no bundle:**

| Comando | TypeScript quebrado | Saída |
|---|---|---|
| `vite build` sozinho | sim | **0** — o risco, reproduzido |
| `tsc --noEmit && vite build` | sim | **≠ 0** — o gate reprova |
| `tsc --noEmit && vite build` | não | **0** — e não reprova sempre |

A terceira linha não é formalidade: um gate que reprovasse tudo passaria na
segunda e seria inútil.

**E a medição não ficou numa mensagem de commit.** `range-core/web/prova_do_build.sh`
é o comando do serviço `web-build`: ele planta, mede as três saídas, desplanta,
confere a restauração contra a cópia intacta e só então constrói. **Roda no CI e
na máquina de quem desenvolve, em toda execução** — porque "medi uma vez" é
exatamente a atestação que o DEMO da Fase 1 foi.

Duas direções de falha de instrumento estão escritas: se `vite build` passar a
**reprovar** o erro plantado, o script para e diz que a premissa mudou, em vez de
seguir verde por um motivo diferente do que ele acredita.

**E ele achou um defeito meu no caminho da limpeza:** a conferência da
restauração era `cmp -s "$ALVO" "$ALVO"` — um arquivo comparado consigo mesmo, e
portanto verdadeira sempre. **Verificação vácua no caminho de limpeza é a que
ninguém vê falhar**: ela só importaria no dia em que a restauração não
acontecesse, que é o dia em que a fonte plantada ficaria na árvore. Corrigida
para comparar contra uma cópia intacta.

Depois do build, o mesmo script varre o artefato **construído**: nenhum
`<script src>` — se o bundle deixasse de ser inlinado, `GET /sala` serviria um
HTML pedindo assets por uma rota que não existe, e a tela abriria em branco na
sala sem nenhum teste de payload ver — e nenhum `/injects/`, `/exercise/`,
`/session` ou `Authorization` nas duas telas públicas.

### O `event_id` da timeline, e por que ele é desta peça

`POST /exercise/rollback` exige `to_event_id`, e a timeline não o carregava. Sem
o campo, o console pediria ao facilitador que **digitasse um ULID** — no comando
que descarta o estado corrente. A entrada passou a levá-lo, e a timeline é
autenticada (`facilitador`, `03` §7): quem a lê já pode disparar e rebobinar,
então não há o que esconder ali.

### O que a suíte prova sem `npm`, e o que só o CI prova

`dist/` é artefato de build e está no `.gitignore` — não existe num clone limpo
nem no worktree da auditoria. Exigir o bundle na suíte faria a suíte depender do
`npm`, e a saída usual — **pular** quando o artefato falta — é pulo silencioso
lido como verde, que é o que a P2-19 atacou.

Então a divisão é explícita, e cada nível prova o que só ele pode:

| Nível | O que prova | Onde |
|---|---|---|
| **fonte** | as telas públicas não conhecem o console; cada uma consome o seu canal | `tests/test_telas.py`, sem `npm` |
| **rota** | cada caminho serve **a sua** tela, com conteúdos distintos; tela ausente **recusa alto** e diz como construir | `tests/test_telas.py`, com o diretório apontado |
| **artefato** | as três compilam; o bundle é arquivo único; as públicas não carregam vocabulário de console | `prova_do_build.sh`, no CI |
| **gate** | `tsc --noEmit` reprova o que `vite build` deixa passar | `prova_do_build.sh`, no CI |
| **caminho** | o bundle real é servido por `GET /sala` com o CWD **fora** da raiz | passo `pacotes importaveis`, no CI |

A varredura de fonte tem o **par que a impede de passar procurando errado**: os
mesmos termos proibidos nas telas públicas são **exigidos** no `gm-console`. Um
erro de digitação em `VOCABULARIO_DO_CONSOLE` deixaria a primeira metade verde
para sempre.

**`_tela` não degrada.** Bundle ausente responde **503** com o comando que o
constrói, e não a página crua: servir "alguma coisa" é como um telão mostra por
meses a tela que o projeto já decidiu jogar fora, sem nada acusar.

### O verificador que a pergunta do operador exigiu

**A pergunta:** *"o teste do lado negativo varre o HTML da casca por nome de
flag, nome de inject e qualquer texto de cenário?"*

**Não varria. E a tabela da D19 dizia que sim** — a afirmação está corrigida lá,
com o estado medido antes de consertar. O buraco tinha três camadas, e só a
primeira estava fechada: nome de flag em fonte `.ts`/`.tsx` já é o invariante 2;
no **bundle** `.html`, nada, porque `.html` não está em `WEB_SUFFIXES`; e id de
inject, `titulo_operacional`, `descricao_facilitador` e `texto_para_plateia`, em
lugar nenhum do cliente.

`scripts/check_telas_sem_vocabulario.py` fecha as três. **O vocabulário sai das
fontes reais** — `domains/*/flags.yaml` e **todo diretório com `injects.yaml`**,
por descoberta e não por lista: o pack real é entregável da Fase 7 (D13), e uma
lista escrita hoje não o incluiria — e ninguém descobriria, porque a varredura
continuaria verde.

**Três classes de termo, e a segunda existe porque bloqueio indevido também é
defeito:**

| Tamanho | Como se procura | Por quê |
|---|---|---|
| ≥ 6 caracteres | substring direto | específico o bastante |
| 2 a 5 | **só entre aspas** | `A01` solto casaria com hash de asset dentro de 156 kB de JS minificado |
| 1 | **ignorado, e a contagem é impressa** | `linha: A` do fixture: vazar "A" não conta nada a ninguém |

**O limite, declarado:** id curto montado por concatenação escapa da segunda
classe — o mesmo limite de varredura léxica que `01` §2 admite. E o que sustenta
a propriedade não é a varredura: é não haver pack ao alcance do build.

**Doze direções de prova negativa**, e as três que valem nomeadas são as do outro
lado: id curto **sem** aspas não bloqueia, termo de um caractere não entra, e o
vocabulário vazio **recusa** com `rc=2` em vez de imprimir "nenhum problema".

**O hook recusou a primeira versão do probe** — invariante 2, literal de flag no
código —, e recusou com razão: o probe exercita o **mecanismo de casamento**, que
recebe o vocabulário por parâmetro. Usar um nome real não acrescentaria nada e
poria no repositório exatamente a string que o invariante existe para manter
fora. **Terceira vez nesta fase** que o hook aponta para o desenho certo.

Entrou na allowlist do auditor no mesmo commit, com a prova negativa ao lado — o
harness passou de **58 para 60** leituras legítimas —, e roda nos dois jobs: em
`arquitetura` sobre a fonte, e em `contratos` **depois do build** com
`--exige-bundle`, que recusa se as três telas não estiverem construídas. Sem essa
guarda o passo varreria a fonte outra vez e diria que varreu o bundle.

**Medido na árvore real:** 16 arquivos de cliente varridos (**3 do bundle**), 45
termos, 4 procurados só entre aspas, 1 ignorado por ter um caractere.

### Visto rodando, contra o servidor de verdade

```text
/sala      200   156.285 bytes        saude antes ....... 100
/plateia   200   154.418 bytes        saude depois ......  90
/console   200   159.563 bytes        destaques 2, omitidos 0
plateia .... "O portal de matricula esta indisponivel. A fila..."
timeline ... exercise_started / inject disparado, com event_id
rollback ... 200, simulation_epoch 1, e a saude volta a 100
```

O `rollback` foi disparado com **o payload exato que o console monta** —
`to_event_id` da entrada da timeline, `reason: facilitation`.

### Os limites desta peça, declarados

- **Renderização e legibilidade a 10 m continuam sem teste**, como a §2.2 fixou:
  não há driver de browser nesta fase, e a D17 já encolheu esse limite ao levar o
  corte para o payload. O que resta é a pergunta física.
- **A `participant-view` não tem os dois cronômetros** de `01` §6. Nenhum dos
  dois está no payload, e inventá-los no cliente seria pior que não tê-los: um
  relógio que o servidor não conhece mostra à plateia um prazo que o exercício
  não está contando.
- **O console entrega o que os OUTPUTS da fase pedem** — *"gm-console mínimo
  (autenticado, lista de injects, botão de disparo, rollback)"* — e não a lista
  inteira de `01` §6. Seletor de pack, disparo agendado, RESET (D7), registro e
  AAR são de outras fases, e três papéis é NON-GOAL declarado.
- **O token vive na memória da aba.** Recarregar pede a credencial de novo, e
  isso é o comportamento desejado: persistir trocaria um incômodo de facilitador
  por uma credencial de exercício esquecida no navegador da sala.
- **Três avisos de `npm audit`, todos em dependência de desenvolvimento.** O
  fecho de produção — o que vai ao bundle — tem **zero**, medido com
  `npm audit --omit=dev`. É a **P4-7**.

**335 testes, zero pulos com a stack no ar** (eram 328).

---

## 4.8 Uma nota de processo: `HEAD` se moveu entre dois turnos

Entre o fim da peça 4 e a abertura da peça 5, a árvore estava em `main`, e não na
branch da fase. **Nada se perdeu** — a branch seguia intacta em `a3e5043`, com os
sete commits —, mas a árvore de trabalho mostrava o conteúdo da Fase 3.

É a corrida que `WORKFLOW.md` §"Árvore de trabalho compartilhada" descreve, e a
terceira ocorrência registrada. **O guarda de branch não a alcança**: ele olha
para onde o commit vai cair, e aqui `HEAD` se moveu durante uma leitura.

**Esta ocorrência é o que motivou a D15, e ela está implementada.** A perna que
fecha **este** caso é a que recusa escrita com `HEAD` na branch default, e não a
que compara com o início da sessão: aqui a árvore **já estava** em `main` quando
a sessão abriu, e um sentinela de "mudou desde o início" teria gravado `main`
como âncora e ficado calado. `WORKFLOW.md` §"O sentinela de branch" tem a forma
final; a §3 D15 tem o porquê de cada decisão.

**O que a pegou foi a convenção, e não um mecanismo:** *"na dúvida, verificar
`git branch --show-current` e `git status` antes de agir"*. Sem isso, a peça 5
teria sido escrita sobre a Fase 3 — importando módulos que não existem lá —, e o
`pre-commit` só a barraria no fim, depois do trabalho inteiro.

---

## 4.9 A peça 7 — os containers, e a fase virando uma sequência só

`Dockerfile`, `.dockerignore`, os três serviços novos do `docker-compose.yml`,
`range-core/api/processo.py`, `domains/academus/api/processo.py`,
`scripts/demo_fase4.py`, `scripts/prova_reinicio_de_container.py` e
`scripts/mede_cache_frio.py`.

### Uma imagem, dois processos, e o domínio por configuração

`range-api` e `academus-api` são **o mesmo código com raízes de composição
diferentes**. Duas imagens seriam duas instalações do mesmo `pyproject.toml`, com
a chance de divergirem em versão — que é o que `constraints.txt` existe para
impedir nem entre commits.

**A raiz de composição do núcleo não importa `domains/`, e isso decidiu a forma
do processo.** O invariante 1 vale para `range-core/api/processo.py` como para
qualquer módulo do core, então o pack e as flags do adapter chegam como
**caminho**, por `AURORA_PACK` e `AURORA_FLAGS`, e são lidos como dado.

Não é contorno do invariante — é o mesmo desenho de
`contract_rules.build_registries`, que deixou de ler `domains/*/flags.yaml` do
disco justamente para receber as flags de quem monta o processo. **A consequência
é que a mesma imagem serve outro adapter sem uma linha de core mudar**, e é essa
consequência que mostra que a regra não estava sendo contornada.

**O clock nasce do fluxo.** No boot, o processo lê o store antes de existir
engine: havendo eventos, o clock é `restaurar(...)` — os cinco valores da peça 3.
Um processo que subisse com T0 do momento do boot faria o exercício recomeçar a
cada reinício, com a sala inteira olhando.

### O item 4, atravessando `docker restart` — e a linha que impede o proxy

A §4.4 declarou a divisão em três níveis e recusou chamar de container o teste de
processo novo. **Esta é a terceira linha**, e ela roda contra o container de
verdade:

```text
exercicio PAUSADO em T+3902s
reiniciado pausado.......... StartedAt 16:36:41 -> 16:37:48
clock congelado............. T+3902s, o mesmo de antes do reinicio
exercicio RETOMADO
reiniciado correndo......... StartedAt 16:37:48 -> 16:37:57
clock correu................ T+3902s -> T+3911s, com 9s fora do ar
```

**A asserção que um teste em processo não consegue produzir é o `StartedAt`.**
`docker inspect --format {{.State.StartedAt}}` antes e depois: se alguém trocar o
`docker restart` por um reinício de processo — ou por nada —, o carimbo não muda e
a prova reprova. Sem essa linha, o par de T5 passaria também num processo, e a
diferença entre peça 3 e peça 7 evaporaria sem ninguém ver.

**O clock é observado pelo carimbo do próximo evento**, porque nenhuma rota expõe
o clock — e não deve expor: o que a sala precisa é a projeção. Os dois casos
juntos matam as três implementações erradas plausíveis: subir sempre pausado
passa no primeiro e falha no segundo; subir sempre correndo faz o inverso; e
subir com T0 = agora derruba os dois, porque o `exercise_time` voltaria para
perto de zero.

**E o segundo caso prova `01` §3 de quebra:** o clock andou **9 s**, que é o tempo
em que o container esteve fora do ar. Restaurar congelado no último evento
inventaria uma pausa que ninguém declarou.

### O DEMO, contra dois containers

A sequência de `07`, inteira, sem intervenção manual:

```text
fixture de demonstracao..... seis registros
telao antes................. saude 100
matricula antes............. 201
exercicio iniciado.......... T0 gravado
telao reagiu................ saude 90, 2 destaques, 47 ms
plateia..................... "O portal de matricula esta indisponivel. A f..."
matricula degradada......... 503
rollback.................... saude 100, epoch 1
matricula restaurada........ 201 — a mesma requisicao que deu 503
timeline.................... 3 entradas, rollback anotado, disparo preservado
```

**O que ele prova além do `demo_fase2.py`** é a montagem: aquele monta objetos em
memória num processo só; este fala HTTP e WebSocket com **dois containers**,
através de Postgres e Redis de verdade. E prova uma coisa que nenhum teste em
processo alcança: **a `academus-api` degrada por causa de um evento que o
`range-api` gravou** — dois containers, duas raízes de composição, um event
store.

**A asserção que discrimina é o par em volta do rollback.** A mesma requisição —
mesmo aluno, mesma turma — dá **503** depois do disparo e **201** depois do
rollback. Uma API que nunca degradasse passaria na segunda; uma que degradasse
sempre passaria na primeira. Só as duas juntas dizem que o estado voltou.

**Os 47 ms são de relógio de parede e atravessam dois containers** — entre 47 e
62 ms em execuções sucessivas. A prova de protocolo — não há espera no caminho do
frame — continua sendo a da peça 4, por AST. Este número é a ponta a ponta, e o
orçamento do item 2 é 1 s.

### Dois defeitos meus, os dois achados rodando

| O que | Por que só a execução separa |
|---|---|
| o DEMO lia **um** canal depois do `start` | toda rota que move o exercício publica nas **duas** projeções. O frame de `exercise_started` ficava na fila da plateia, e o `recv` seguinte pegava esse — com texto vazio. O DEMO acusava *"a plateia não recebeu texto_para_plateia"* com o servidor inteiramente correto |
| a prova de reinício lia `entradas[-1]` depois da retomada | o último evento era o próprio `exercise_resumed`, carimbado **antes** do reinício. Ela acusava *"o clock não andou"* medindo um evento que não podia ter andado — o instrumento tem de observar **depois** do que ele julga |

**As duas mensagens apontavam para o lugar errado**, e é isso que as torna caras:
um instrumento que erra apontando para o servidor faz procurar defeito onde não
há.

### A P3-2, medida nos dois sentidos

A D22 tem a decisão; o número está aqui porque foi ele que a produziu:

```text
1 worker    20 leituras simultaneas, cache frio -> 1 reconstrucao
4 workers   20 leituras simultaneas, cache frio -> 4 reconstrucoes
```

**A pendência é limitada pelo número de workers, e não pelo de leitores** — uma
reconstrução por laço de eventos. Com um worker ela não ocorre, e não por
single-flight: a rota é `async def` com corpo síncrono, e a corrotina roda até o
fim sem ceder o laço.

**E quase escrevi uma segunda conclusão errada.** Medi também o tempo — 20
leituras em 1,5× o tempo de uma — e ia registrar isso como prova de serialização.
**Não é:** a razão mistura conexão e transporte, que correm em paralelo, com o
corpo do handler, que não corre. Com este pack o fold custa microssegundos, e a
parte serializada é invisível no relógio. **Quem prova a serialização é a
contagem de reconstruções, e não o cronômetro** — o número do tempo ficou no
script dizendo de onde vem o tempo, com essa ressalva escrita ao lado.

### O gate de imagem ganhou uma segunda forma sintática

`FROM`. O `Dockerfile` é o quarto arquivo de `check_pinned_images.py`, e a razão é
a P3-1 exata com outra sintaxe: o estágio de Node da imagem poderia apontar para
um digest **diferente** do que o `web-build` usa, e o build do container e o da
máquina de quem desenvolve deixariam de ser o mesmo.

**O eixo 3 ganhou uma isenção, e ela é de uma pergunta e não de um arquivo.**
*"Esta imagem é um serviço que alguém consegue subir localmente?"* não se aplica a
imagem-base de build: `python:3.12.7-slim` existe só no `Dockerfile`. Exigir que
ele aparecesse no compose obrigaria a inventar um serviço que ninguém roda — ou a
escrever a linha num comentário para enganar a varredura. **O eixo 2 continua
valendo para ele**, e é o que importa: `node` está nos dois arquivos e os dois
digests têm de ser iguais.

**A primeira versão da isenção pulava o laço inteiro e levava o eixo 2 junto** —
isto é, desligava exatamente a razão de o `Dockerfile` estar na lista. Quem
mostrou foi o probe da isenção, e por isso ele existe.

**E o probe do `FROM` achou outro comportamento antes de eu escrever a afirmação
errada sobre ele:** `# FROM ...` comentado **é capturado**, porque a varredura
tira o `#` antes de olhar a marca — como já fazia com `image:`. O comportamento
fica: ela é conservadora na direção que importa, e pode cobrar digest de uma
linha comentada, mas não perde uma declaração de verdade. **A consequência para
quem escreve `Dockerfile` ficou dita no probe:** comentário em prosa não começa
com `FROM`. São **12 eixos**, eram 8.

### O que fica fora do alcance do auditor, e a decisão está aqui

Os três scripts desta peça — DEMO, prova de reinício e medição — **não entram na
allowlist do auditor**, e isso é decisão, não esquecimento (a lição do B1 da Fase
2 é que "nada novo entra" também precisa ser decidido).

Os três exigem **docker e uma stack no ar**, e a P2-19 recusou pôr rede na
allowlist do julgador. Rodá-los sem stack produziria *connection refused* — um
**FAIL falso**, que é pior que não rodar.

> **A D12 foi REVISADA por causa disto, e a revisão mora com ela** — §3, D12,
> *"a segunda ponta deixou de existir"*. O resumo: a exigência de pôr o serviço
> na stack da auditoria comprava uma proteção precisa — que o teste **não pule**
> —, e passo de CI não pula. A regra mudou de escopo em vez de ganhar um caso
> excepcional, e o operador ratificou nesses termos.
>
> **O que o auditor verifica por leitura**, e é o que sustenta a revisão: que os
> passos existem no workflow, que nenhum deles tem `continue-on-error`, `|| true`
> ou `if: always()`, e que o `Dockerfile` e o compose dizem o que os scripts
> supõem.

### O gate da superfície pegou a raiz de composição do adapter

`check_api_surface.py` reprovou `domains/academus/api/processo.py` por importar
`range_core.state` — *"e só `degradacao.py` pode"*. **Estava certo, e a regra é a
que importa:** estado ao alcance do handler é um `if flag:` esperando para
acontecer, e a exceção existe para o módulo que **aplica** a degradação, não para
quem por acaso monta o processo.

A construção do cache virou `degradacao.cache_do_ambiente`, e `processo.py`
voltou a não ter `range_core.state` ao alcance. **Quarta vez nesta fase que um
gate aponta para o desenho certo** — e a primeira em que o apontamento vem do
verificador de superfície, e não do hook.

### O CI rodou antes da auditoria, e achou um defeito na primeira volta

**Exigência do operador, e ela estava certa:** *"'verifiquei localmente' é a
forma de atestação que esta fase recusou em todos os outros lugares"*. Os quatro
passos novos nunca tinham rodado num runner, e o **item 4 da DoD depende deles**.

**O workflow não dispara em push de branch** — `on: push: branches: [main]` e
`pull_request` —, então exercitar o CI exigiu abrir o PR **em draft**. Ele não
merge e não move a âncora; a ordem de `WORKFLOW.md`, com a auditoria antes do
PR de merge, continua valendo.

**Primeira volta, vermelha, e no passo previsto:**

```text
SecretUnavailable: AURORA_JWT_SECRET tem 28 caracteres, e o minimo e 32.
Chave curta e quebrada offline a partir de um unico token capturado.
```

**O valor que usei na minha máquina tinha 39 caracteres; o que escrevi no
workflow tinha 28.** A stack subia aqui e não lá — a atestação exata que a
exigência do operador existia para pegar, e ela apareceu na primeira execução
real. **A guarda de boot estava certa e o CI estava certo**: o defeito era meu,
e o mecanismo funcionou como desenhado — recusa alta, no boot, com a mensagem
nomeando o motivo.

**E a primeira volta também mostrou um buraco de diagnóstico.** O runner é
descartável: `container aurora-range-api exited (1)` foi tudo o que sobrou, e o
traceback foi embora com a máquina. Um passo `if: failure()` passou a despejar
`docker compose ps --all` e os logs — **e `failure()` não é `always()`**: ele só
roda quando alguma coisa já falhou, e não pode transformar vermelho em verde. Ele
fica no **fim** do job, porque passo que falha pula os seguintes e no meio ele
cobriria só o passo anterior.

**Segunda volta, os quatro jobs verdes, e os números agora são do runner:**

```text
as tres telas construidas, o gate provado reprovando
telao reagiu................ saude 90, 2 destaques, 64 ms
matricula degradada......... 503
rollback.................... saude 100, epoch 1
matricula restaurada........ 201 — a mesma requisicao que deu 503
timeline.................... 3 entradas, rollback anotado, disparo preservado
reiniciado pausado.......... StartedAt 18:56:37 -> 18:56:44
clock congelado............. T+4s, o mesmo de antes do reinicio
reiniciado correndo......... StartedAt 18:56:44 -> 18:56:54
clock correu................ T+4s -> T+14s, com 10s fora do ar
20 leituras simultaneas .... 1 reconstrucao
```

**O que isso muda para a auditoria:** o item 4 da DoD deixa de depender de uma
execução na máquina de quem implementou.

> **A frase que estava aqui era uma atestação, e foi o L1 da primeira
> auditoria.** Ela dizia que os quatro contexts estavam *"verdes sobre o commit
> que vai ser auditado"* — e foi escrita **dentro** do commit que ela descrevia,
> sobre um resultado de CI que só podia ser de um commit **anterior**. Era a
> única evidência oferecida para o item 4, e afirmava o futuro.
>
> **O que se pode afirmar, datado:** a execução verde citada acima é a do commit
> `32057377` — anterior a este —, e os números do DEMO, do reinício e da medição
> saem dela. Cada commit posterior tem a sua própria execução, e nenhuma frase
> aqui pode falar por ela: quem responde é o CI do commit que está sendo
> auditado, e ele é consultável.

### Limites declarados desta peça

- **O compose de produção não existe.** Este é o de desenvolvimento e publica no
  loopback do host; a segunda metade de `05` §6 vence quando existir deploy.
- **O cliente é construído duas vezes no CI** — uma pelo `web-build`, para o gate
  e a prova negativa, e outra dentro da imagem. São perguntas diferentes, e a
  duplicação é deliberada.
- **`--workers 1`, e agora isso é uma escolha com número atrás** (D22): subir o
  número traz a P4-8 junto.
- **O DEMO exige um exercício que ainda não começou.** `exercise_started` já no
  store faz `engine.start()` recusar — correto, e não defeito. Ele para com a
  mensagem que diz o que fazer.

---

## 4.10 A primeira auditoria de checkpoint — FAIL, e o que ela achou

**FAIL correto.** As correções abaixo são de mecanismo, e não das linhas que o
sintoma pedia.

### B1 — `05` §4 não tinha verificador, e a fase entregou três telas sem banner

`05` §4 exige `AMBIENTE SIMULADO — DADOS FICTÍCIOS` *"em toda tela e no rodapé de
todo artefato gerado"*. **As três telas não o tinham.**

**E o achado não é uma linha esquecida:** `05` §4 **não aparece uma vez** nas
2.774 linhas deste registro, e **nenhum verificador cobria a seção** —
`check_security_constraints.py` declara escopo §1, `check_synthetic_data.py`
cobre §3. A seção inteira estava fora de todo mecanismo, e por isso a ausência
atravessou sete peças.

**O auditor tem razão no ponto 4:** presença de banner é propriedade do **DOM**,
não de renderização. Ela caiu no limite declarado da §2.2 — *"renderização,
contraste e legibilidade a 10 m"* — **por acidente**, e não por decisão: qualquer
varredura a lê sem navegador. O que continua sem teste é se ele é legível a 10 m.

`scripts/check_banner_de_simulacao.py` tem a forma das duas irmãs, e três eixos:

| Eixo | Por quê |
|---|---|
| o texto é **extraído de `05` §4**, e não copiado | texto normativo com segunda fonte diverge, e a que diverge em silêncio é a que ninguém olha — classe P3-1 |
| cada tela renderiza o componente, na **fonte** | `05` §4 diz TODA tela, sem exceção para tela pequena |
| cada **bundle** carrega o texto | a fonte pode tê-lo e o artefato servido não — e é o artefato que vai ao navegador |

**A §4 inteira está mapeada, e não só a parte que esta fase produz.** O registro
de classes é conferido nas duas direções: classe coberta sem alvo no disco
reprova, porque varredura vazia passa por não ter o que olhar.

| Classe | Estado |
|---|---|
| **telas** | coberta aqui — as três de `01` §2, fonte e bundle |
| evidência | **Fase 8** — `08_EVIDENCE_SIMULATOR.md`; §4 pede comentário na primeira linha, no formato do próprio arquivo |
| exportação | **Fase 8** — `academus-web`: histórico, diploma, PDF |
| relatório/AAR | **Fase 9** — `range-core/aar/` |

**O custo no telão está declarado:** o banner ocupa **uma** das 7 a 8 linhas do
orçamento da D16. Não é negociável — a spec não abre exceção para tela pequena.

**Dez direções de prova negativa, e duas acharam defeito meu no instrumento:** o
`relative_to` estourando fora da raiz — **terceira vez nesta linhagem**, porque
escrevi o verificador sem reusar o `rel()` que já existia —, e um
`spec: Path = SPEC` como default de função, avaliado uma vez na definição, que
tornava o probe de anti-vacuidade **incapaz de provocar a recusa que ele exigia**.

### H1 — três implementações da mesma propriedade, e o resultado líquido

A sincronia entre fonte versionada e cópia instalada tinha **três** implementações
em `phase0_negative_tests.py`: uma comparava `splitlines()`, duas comparavam
`read_bytes()`. **Duas implementações da mesma propriedade divergindo é a classe
P3-1**, e o líquido era pior que vermelho: **vermelha para quem desenvolve**
(bytes contra CRLF que o `core.autocrlf` do checkout produz, e que o autor não
escreveu) e **cega para quem julga** (no CI as três caíam no ramo de aviso e não
verificavam nada).

**Uma implementação**, comparando por linha — o que se afirma é que o código
instalado é o mesmo programa, e o fim de linha é decidido pelo checkout.

**O fim de linha do `pre-commit` é relevante, e por isso ganhou asserção
própria** em vez de continuar escondido dentro da comparação de bytes: ele é
`#!/bin/sh`, e um CR no shebang o torna inexecutável. **A asserção nova reprovou
na primeira execução:** o arquivo estava com CRLF na árvore, e `bootstrap.sh` o
copia assim — o guarda de branch deste clone estava a um `checkout` de parar de
guardar sem dizer nada. `.gitattributes` passou a forçar `eol=lf` em
`user-scope/hooks/**`.

**E o pulo virou contagem.** O relatório dizia *"Hooks exercitados: fonte
versionada, cópia instalada"* mesmo quando **nenhuma** cópia fora conferida.
Agora ele imprime `Copias instaladas: N conferidas, M AUSENTES` — no CI, onde não
há escopo de usuário, a ausência aparece como ausência.

### O que fica pendente para o operador

**M1 e o `spec-change`** — a lista de exceção de `05` §8 é fechada pelo
preâmbulo, e ampliá-la por decisão de fase é o caminho que o `spec-change`
existe para carregar. Ver a **P4-9**.

> **Resolvido: o `spec-change` foi mergeado em `486df18`**, a branch foi
> rebaseada sobre ele e a âncora regravada no mesmo passo. `05` §8 agora isenta a
> casca estática do `gm-console` e a rota que troca credencial por token.

**Itens 1 e 4 da DoD ficaram NÃO VERIFICADO por ausência de Docker no auditor**,
que é o padrão da P2-19. A proposta está na **P4-10**, e ela **não foi
implementada** — a decisão é do operador.

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

Quatro fechadas na peça 5. As **recebidas da Fase 3** estão marcadas com o
prefixo `P3-`; as abertas nesta fase, com `P4-`.

| Id | O que é | Vence em |
|---|---|---|
| P3-2 | ~~cache frio sem single-flight: leituras concorrentes reconstroem N vezes~~ | ✅ **FECHADA** na peça 7, com número (D22) |
| P3-4 | ~~no worktree de auditoria, `range_core` vem da árvore principal~~ | ✅ **FECHADA** na peça 0 |
| P3-5 | ~~business state em dicionários de módulo~~ | ✅ **FECHADA** na peça 5 (D8) |
| P3-8 | ~~dois falsos bloqueios do hook do auditor~~ | ✅ **FECHADA** na peça 0 |
| P3-10 | ~~`Cota` é estado mutável fora das cinco camadas de `01` §4~~ | ✅ **FECHADA** na peça 5 (D9) |
| P3-11 | ~~flag declarada e ausente do estado vira no-op silencioso~~ | ✅ **FECHADA** na peça 5 (D10) |
| P4-1 | ~~os caminhos da `academus-api` estão em português~~ | ✅ **FECHADA** na peça 5 |
| P4-2 | a família `eventos` não roda no perfil de domínio, e emitir sem declarar não tem guarda em lugar nenhum | **Fase 5** — ver abaixo |
| P4-3 | ~~a página crua de `/sala` é provisória e a peça 6 a substitui~~ | ✅ **FECHADA** na peça 6 |
| P4-4 | oito flags declaram `academus-api` como consumidora e nenhuma rota as consome | **Fase 8** — ver abaixo |
| P4-5 | `grades.student_id` não tem FK nem validação: nota de aluno inexistente é aceita | **Fase 5** — ver abaixo |
| P4-6 | o `effect_ui` da flag de queda de sessão diz "por minuto", e a função não tem cadência | **Fase 8** — ver abaixo |
| P4-7 | três avisos de `npm audit` no toolchain do cliente, todos em dependência de desenvolvimento | **condição** — ver abaixo |
| P4-8 | o caminho de leitura é síncrono dentro do laço de eventos: serializa hoje, e bloqueia em volume | **condição** — ver abaixo |
| P4-9 | ~~a casca pública do console amplia a lista fechada de `05` §8, e isso exige `spec-change`~~ | ✅ **FECHADA** pelo `spec-change` mergeado em `486df18` |
| P4-10 | itens 1 e 4 da DoD ficam NÃO VERIFICADO por ausência de Docker no auditor | **decisão do operador** — proposta abaixo |

A **P2-6** — a ligação declarativa de `participant_action` a flag — continua
datada para a **Fase 8**, e não é desta. A premissa original dela era falsa e o
registro da Fase 3 §2 tem a correção.

#### P3-2 — cache frio sem single-flight

Duas leituras concorrentes num cache frio reconstroem duas vezes, e cada
reconstrução custa o que a §3.8 da Fase 2 mediu — 2,874 s em 150 mil eventos.

**A condição que a pendência descreve ocorre nesta fase**, e desta vez pelo nome
e não por proxy: o primeiro processo que serve requisições concorrentes é o
container da peça 7. Ver a **D11** — a ordem é medir, depois escolher.

> **✅ FECHADA na peça 7, com número — e o número corrigiu a pergunta.** Medido
> com a stack no ar: **20 leituras simultâneas sobre cache frio produzem 1
> reconstrução** com o worker único do compose, e **4** com quatro workers. A
> pendência não ocorre como escrita, e a razão não é single-flight: a rota é
> `async def` com corpo síncrono, e a corrotina roda até o fim sem ceder o laço —
> não há voo concorrente para unificar.
>
> **O custo é limitado pelo número de workers, e não pelo de leitores.** É por
> isso que a pendência fecha em vez de ser redatada: a pergunta que ela fazia
> está respondida com medição, e o que sobra é outro fato — o caminho de leitura
> síncrono —, que tem nome próprio na **P4-8**. Ver a **D22** e a §4.9.

#### P3-4 — no worktree de auditoria, o core vem da árvore principal

`domains` e `contracts` resolvem pelo worktree; `range_core` resolve pela
**árvore principal**, porque a instalação editável grava caminho absoluto e
`range-core` tem hífen — não é importável pela árvore.

**Esta é a fase em que a pendência sai de latente**, e pelo motivo que a nota
corrigida dela previu: com auditoria antes do merge, a árvore principal e o
worktree ficam em commits diferentes de verdade, e um commit na principal
*durante* a auditoria trocaria o núcleo sob os testes do auditor sem sinal
nenhum.

> **✅ FECHADA na peça 0**, com as duas metades — o teste que fica vermelho e o
> venv que o faz passar —, e **reproduzida antes de corrigida**: sete falhas
> dentro do worktree, incluindo um `contracts` montado a partir das **duas**
> árvores ao mesmo tempo, que a pendência não previa. Ver a §4.1.

#### P3-5 — business state em dicionários de módulo

As três entidades e `Matricula` são `dataclass` em memória. `02` §7 diz
*"academus-api — FastAPI + **SQLAlchemy**"* e `01` §4 põe Business State em
Postgres, com a linha *"não reversível por rollback; só por reset total"*.

**A linha passa a ser falsa nesta fase**, porque é a primeira em que existe um
container que reinicia — e reinício não é reset total. Ver a **D8**.

> **✅ FECHADA na peça 5**, com **quatro** tabelas e não três — a D8 lia as três
> entidades de `07`, e a pendência nomeia quatro dicionários de módulo. O par
> atravessa **processo**, e a mutação que prova está medida: com a escrita
> voltando para dicionário de módulo, dois testes ficam vermelhos; com a
> matrícula escrita e não commitada, um. Ver a §4.6.

#### P3-8 — dois falsos bloqueios do hook do auditor

`->` dentro de string citada lido como redirecionamento, e *path* de URL lido
como caminho absoluto fora do worktree. Os dois matam comandos que o auditor
precisa para **medir**, e `WORKFLOW.md` classifica bloqueio indevido como
defeito — foi a lição do H4 da primeira auditoria da Fase 0.

**Vencimento declarado na Fase 3: antes do checkpoint desta fase.** É a peça 0.

> **✅ FECHADA na peça 0**, e a forma final difere da que a pendência previa em
> uma das duas metades. A da seta **não** é sobre alvo: é a semântica de aspas
> que o bash dá a `>`, que é a mesma correção da 16ª auditoria da Fase 0 na
> direção oposta. A do path de URL é sobre alvo, como previsto, e precisou de
> **duas** condições — não existir em disco **e** o comando do segmento não ter
> forma de escrever. Sete comandos passaram de bloqueado a liberado, medidos
> contra a versão anterior, com quinze eixos de bloqueio novos ao lado. §4.1.

#### P3-10 — `Cota` é estado mutável fora das cinco camadas

O acumulador de `proporcional` vive na instância do `Degradador`, é chaveado por
`(rota, flag)` e não deriva de nenhum evento. Reinício zera a cota; rollback
devolve a flag e não devolve o acumulador.

Ver a **D9**: a decisão é **eliminar** o estado, e não realocá-lo — e a forma
nova é mais fiel ao que `flags.yaml` declara sobre a flag.

> **✅ FECHADA na peça 5.** As três propriedades foram medidas com mutação
> plantada, e a medição corrigiu duas expectativas minhas: a fração observada
> **não** acusa o acumulador — a cota dava a fração certa e o conjunto errado —, e
> o acumulador **derruba** o teste de reinício, porque estado de módulo atravessa
> classes de teste. A frase *"mais fiel ao que `flags.yaml` declara"* ficou pela
> metade: o `effect_ui` termina em "por minuto", e a função não tem cadência. É a
> **P4-6**. Ver a §4.6.

#### P3-11 — flag declarada e ausente do estado vira no-op silencioso

`estado.flags.get(entrada.flag)` devolve `None` para flag que o estado corrente
não tem, e aí `ligada` não dispara e `proporcional` lê `0.0`. A rota não degrada,
e nada avisa. O gate protege o repositório; não protege o exercício em curso.

Ver a **D10**: a guarda de boot só tem sentido onde há boot, e o boot é desta
fase.

> **✅ FECHADA na peça 5**, com o par que discrimina e com **uma segunda
> condição** que a D10 não previa: rota **pública** que declara `proporcional`
> também recusa o boot, porque o sujeito vem do `sub` do token e rota pública não
> tem token — a queda nunca aconteceria, e em tempo de requisição isso seria
> indistinguível de taxa zero. Ver a §4.6.

---

#### P4-1 — os caminhos da `academus-api` estão em português

**Achado escrevendo a superfície do núcleo**, ao decidir o idioma dela.
`CLAUDE.md` §Idioma põe **endpoints** na lista do inglês, junto de
identificadores, tabelas, colunas, logs e nomes de flag e de evento. As cinco
rotas da Fase 3 são `/alunos/{aluno_id}`, `/turmas/{turma_id}`,
`/turmas/{turma_id}/diario`, `/turmas/{turma_id}/notas` e `/matricula`.

**Não é ambiguidade da regra, e conferi antes de registrar:** a mesma seção põe
em português a interface, os dados sintéticos, os cenários, as rubricas e a
documentação. Caminho de rota não é nenhum dos cinco.

**E a spec tem uma exceção própria, que não cobre essas cinco:** `01` §6 escreve
o caminho da participant-view como `/plateia`, literalmente. Documento normativo
prevalece sobre a convenção do `CLAUDE.md`, então a superfície do núcleo usa
inglês em tudo **menos** ali — e a exceção está dita no YAML, em vez de parecer
descuido.

**Por que não corrijo agora.** Renomear rota é mudança de produto, não de
aparato: toca `app.py`, `api_surface.yaml`, os testes de RBAC e de degradação, e
a Fase 3 está mergeada e auditada com esses nomes. Fazer isso dentro da peça 1
misturaria a correção com a superfície nova, e a peça deixaria de ter uma volta.

**Vencimento: a peça 5**, que é quando a `academus-api` é reaberta para a P3-5 —
o `repositorio.py` inteiro muda de forma ali, e os testes já vão ser tocados.
Renomear junto é uma edição; renomear à parte é duas.

> **✅ FECHADA na peça 5.** As cinco rotas e os campos de corpo em inglês, e as
> tabelas nascendo assim. `/plateia` deixou de ser "a exceção entre
> inconsistências" e passou a ser **a única exceção do projeto**, com fonte
> normativa — a nota do `range-core/api_surface.yaml` foi reescrita para dizer
> isso. O limite ficou declarado: nomes de **módulo e de função interna** seguem
> em português, e a razão está na §4.6.

#### P4-2 — a família `eventos` não roda no perfil de domínio

**Aberta na peça 1, e ela é a §7.3 com nome:** o verificador passou a conferir
`emite` contra o catálogo e contra a camada, e isso vale **só para o perfil do
núcleo**. Lido rápido, ele *parece* cobrir eventos.

**As duas metades, e a segunda é a que não tem dono:**

| | Estado |
|---|---|
| declarar `emite` na superfície de domínio | **reprova alto** — o campo é proibido no perfil, e há eixo |
| **emitir sem declarar** | **sem guarda em lugar nenhum** |

A segunda metade não é regressão da peça 1 — o verificador nunca olhou emissão em
código, em superfície nenhuma. O que a peça 1 mudou foi a aparência: antes não
havia família de eventos, e agora há uma que não alcança o adapter.

**O que falta é uma varredura por AST do lado do código**, e ela não existe para
nenhum dos dois perfis: hoje nada cruza *"quem chama `store.append`"* com
*"quem declarou `emite`"*. `tools/check_event_envelope.py` guarda outra coisa —
que nenhum evento emitido carregue `objective_ids`.

**Vencimento: Fase 5**, e o gatilho é a **condição**, não o marco — a §7.2 desta
linhagem existe por isso. A condição é *o primeiro emissor fora do
`inject-engine`*, e ele é da Fase 5: `06` T7 e a DoD daquela fase põem a trilha
de auditoria com hash na `academus-api`, e a P3-6 já registra que
`POST .../notas` vai encontrar a rota antes da trilha. O primeiro `append` do
adapter é lá.

**A `academus-api` não emite nada hoje, e a frase que eu ia escrever aqui era
falsa.** Eu ia registrar que *"nenhum módulo de `api/` importa o store"*.
**Importa:** `degradacao.py` importa `EventStore`, e é o único — conferido com o
próprio extrator do verificador, e não de memória. O que ele faz com o store é
**ler**: `current(store, declarations, cache)` chama `head()` e `read_all()`.

A afirmação verdadeira é mais estreita e é a que vale: **nenhum módulo de `api/`
chama `append`**. Enquanto isso for verdade, a metade sem guarda não tem sujeito
— e é ela que a Fase 5 recebe, no commit em que o primeiro `append` do adapter
nascer.

#### P4-3 — a página crua de `/sala`

**Pedido do operador, fora do plano, e aceito com o argumento dele:** a Fase 4 é
o marco que existe para ser visto, e ver cedo tem valor próprio.
`range-core/web/sala.html` prova a cadeia inteira — disparo, evento, projeção,
canal, navegador — três peças antes do fim.

**Ela não é dívida real, e isso é consequência de três decisões, não de
intenção:** não opera o exercício (não dispara, não rebobina, não pede token, e
há teste varrendo o corpo); consome só os dois canais que já existem, sem
endpoint próprio; e ocupa uma rota que **fica** — a peça 6 troca o arquivo pelo
bundle e `GET /sala` continua servindo.

**O que fecha a pendência:** a peça 6 substitui o arquivo pelo bundle de
`range-core/web/` — React 18 + Vite + Tailwind, que `00` §8 fixa —, atualiza a
entrada de `package-data` do `pyproject.toml` e apaga este HTML. Nada mais
precisa ser desfeito.

**O risco de ela virar permanente é real e tem antídoto barato:** ela não
implementa o que `01` §6 exige do wallboard — alto contraste, legível a 10 m,
painéis por convenção com codificação visual por `category`. Enquanto isso não
existir, o item de OUTPUTS da fase não está entregue, e é a DoD que cobra.

> **✅ FECHADA na peça 6, e o custo de desfazer foi o que a pendência previa:
> apagar um arquivo.** `GET /sala` continua e passou a servir o bundle do
> `wallboard-shell`; `web/sala.html` saiu; a entrada de `package-data` do
> `pyproject.toml` aponta para `web/dist/*/index.html`. Nenhum endpoint precisou
> ser removido, porque ela nunca teve endpoint próprio — as três decisões que a
> tornavam descartável eram, de fato, o que a tornava descartável.
>
> **A consequência da entrada nova tem dono e está escrita:** as telas são
> artefato de build, então **a imagem da peça 7 constrói o cliente antes do
> `pip install`**. Sem isso a instalação leva os `.py` e deixa as telas para
> trás — e `GET /sala` responde 503 no telão da sala, que é exatamente o que o
> 503 de `_tela` existe para dizer em voz alta. Ver a §4.7.

#### P4-4 — flag que declara consumidor que não a consome

**Medido ao responder a pergunta da P3-11 sobre a direção simétrica:** doze flags
declaram `academus-api` em `consumers`, quatro são consumidas por alguma rota, e
**oito não são consumidas por nenhuma**.

**A assimetria é real e é o espelho da P3-11.** Aquela pega *"a rota consome uma
flag que o estado não tem"*; esta seria *"a flag afirma um consumo que a rota não
faz"*. Nenhuma das duas é pega hoje pelo mesmo mecanismo: `check_api_surface`
confere rota → flag, e nada confere flag → rota.

**Por que não vira gate agora:** reprovaria a árvore por um motivo legítimo. A
`academus-api` é deliberadamente mínima — `07` Fase 3 põe *"modelo completo"* nos
NON-GOALS —, e as oito têm consumidor previsto: `05`/`02` §9 põem as sete ações
de continuidade e o `academus-web` completo na **Fase 8**, cujo item de DoD é
*"as sete ações de continuidade aplicam efeito mecânico e custo"*.

**A forma sugerida já existe no repositório:** `domains/flags_pendentes.yaml`, que
a peça 1 da Fase 3 criou para flags citadas na spec sem serviço que as traga,
com **quem a trará** por entrada e cobrança nas duas direções — entrada que
sobrou reprova, entrada que a fonte deixou de citar também. A mesma forma
aplicada a `consumers` fecharia esta.

**Vencimento: Fase 8**, e o gatilho é a condição, não o marco — *o primeiro
commit em que a `academus-api` passa a consumir flag de continuidade*.

#### P4-5 — nota lançada para aluno inexistente é aceita

**Aberta escrevendo a migration da P3-5**, ao decidir onde ficavam as chaves
estrangeiras. Três das quatro estão onde a rota **já garante** a relação:
`grades.class_id`, `enrollments.student_id` e `enrollments.class_id` — os três
caminhos falham antes de escrever quando o alvo não existe, então a FK documenta
no esquema o que o código já faz, sem mudar comportamento nenhum.

**`grades.student_id` não tem FK, e a assimetria é deliberada.** A rota não
confere se o aluno existe: `repositorio.lancar_nota` passa pela **turma** e mais
nada. Pôr FK ali faria `POST /classes/{class_id}/grades` com `student_id`
inventado passar de **201** a erro de integridade — mudança de comportamento de
uma rota que a Fase 3 entregou e auditou, entrando por efeito colateral de
migration. Esta peça não faz isso.

**A ausência é medida, e não só escrita:**
`test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje` afirma o comportamento atual.
Isso serve a duas coisas: a pendência deixa de depender de alguém lembrar, e o
dia em que ela for fechada tem um teste **vermelho** anunciando a mudança, em vez
de um verde silencioso.

**Vencimento: Fase 5**, e o gatilho é a condição: *o commit em que a trilha de
`02` §4.1 nascer*. Ela registra o aluno da alteração de nota — `06` T7 e a DoD
daquela fase —, e trilha que registra um aluno inexistente é pior que a ausência
de FK: ela produz evidência plausível e falsa, que é a camada 2 mentindo sobre a
camada 1.

#### P4-6 — o `effect_ui` promete cadência, e a função não tem

**Aberta implementando a P3-10, ao reler a fonte que a D9 cita.** A D9 justifica
a função determinista citando `flags.yaml` como *"fração de **sessões** de prova
em andamento derrubadas"*. O texto real do `effect_ui` de
`academus.lms_session_drop_rate` termina em **"por minuto"** — a citação da
decisão estava incompleta, e a diferença não é de estilo: "fração de sessões" é
um corte estável, "por minuto" é uma taxa que acumula no tempo.

**A função implementa a primeira metade.** Quem cai, cai o exercício inteiro;
não há um punhado novo a cada minuto. Implementar a cadência exigiria **tempo
como entrada**, que é exatamente o estado que a P3-10 acabou de tirar daqui — e o
resultado seria uma terceira variante do mesmo defeito: memória fora das cinco
camadas de `01` §4, agora com relógio junto.

**Nem o texto nem a função estão errados sozinhos.** O que não pode ficar é a
divergência sem dono: o facilitador lê o `effect_ui` para prever o efeito, e um
texto que promete cadência sobre uma flag que não a tem é a mesma classe de
defeito que `05`/`02` §9 produzem quando a spec promete serviço que não existe.

**Vencimento: Fase 8**, e o gatilho é a condição, não o marco — *o primeiro
consumidor com semântica de sessão*. `07` Fase 8 tem o item de DoD *"Modo 'Prova
em andamento' perde sessões conforme `lms_session_drop_rate`"*, e é lá que existe
uma sessão de prova com duração, com cronômetro e com autosave — os três
ingredientes que "por minuto" pressupõe. **A resolução pode ser nas duas
direções**, e é decisão daquela fase: implementar a cadência onde há sessão, ou
corrigir o `effect_ui` para o que a flag de fato faz.

#### P4-7 — três avisos no toolchain do cliente, todos de desenvolvimento

**Medido ao gerar o `package-lock.json`**, e registrado com o número dos dois
lados porque só um deles importa:

```text
npm audit              3 avisos (1 moderado, 2 altos)
npm audit --omit=dev   0
```

**Os avisos não alcançam o que vai à sala.** Um é do servidor de desenvolvimento
do `esbuild` (GHSA-67mh-4wv8-2f99) — e este projeto **não roda `vite dev`**: o
único comando é `vite build`, dentro de um container que sai ao terminar. Os
outros são do `postcss`, sobre CSS controlado pelo atacante; a entrada de CSS
aqui é o próprio Tailwind da árvore.

**Por que não corrigir agora.** O `npm audit fix` exige `--force`, que sobe
*major* de `vite` — trocar a versão do toolchain que acabou de ser pinada, por
avisos que não tocam o fecho de produção, é a mudança que se faz olhando, e não
de passagem. Pinar existe para que atualizar seja **mudança explícita de commit**,
e essa é a regra que `00` §8 fixa.

**Vencimento: condição, e não marco** — *a primeira das duas que ocorrer*: o
primeiro consumidor de `vite dev` (que põe o servidor de desenvolvimento em uso e
torna o aviso do `esbuild` sujeito), ou a primeira subida deliberada do toolchain
do cliente, que `07` Fase 8 traz junto com o `academus-web` completo.

---

#### P4-8 — o caminho de leitura é síncrono dentro do laço de eventos

**Aberta medindo a P3-2**, e ela é o que sobrou depois que a medição respondeu a
pergunta original. `GET /wallboard/state` é `async def` com corpo **síncrono**: a
corrotina roda até o fim sem ceder o laço de eventos.

O fato tem **duas faces**, e a primeira é benigna hoje:

| | |
|---|---|
| **serializa** | é por isso que 20 leituras simultâneas sobre cache frio produzem **1** reconstrução, e não 20 — o que fecha a P3-2 |
| **bloqueia** | a mesma síncrona segura o laço inteiro durante a reconstrução: a 150 mil eventos são **2,874 s** (§3.8 da Fase 2) em que nenhuma outra rota responde, **inclusive os dois canais de WebSocket** |

**A segunda face é a que importa e ainda não foi medida em volume.** Ela é
raciocinada a partir do código e do número da Fase 2, e está dita assim de
propósito: um telão que congela por quase três segundos durante o pico do
exercício é exatamente o defeito que o item 2 da DoD existe para impedir, e o
teste de protocolo da peça 4 não o alcança — ele prova que **não há espera** no
caminho do frame, e não que o laço está livre para entregá-lo.

**A saída não é single-flight.** Com um worker não há voo concorrente; com N
workers, single-flight dentro do processo não resolve nada entre processos. As
saídas reais são outras duas, e a escolha é da fase que tiver o consumidor:
tirar a reconstrução do laço (executor separado), ou tornar o fold incremental —
que a §4.5 já registrou como **não sendo desta fase**, porque exigiria uma porta
que aceita estado pronto, e é justamente o que a peça 3 da Fase 3 removeu.

**Vencimento: condição, e não marco** — *a primeira das duas que ocorrer*: um
deploy com mais de um worker (a P3-2 volta, limitada por eles), ou o primeiro
volume de eventos em que a reconstrução passe de uma fração do orçamento de 1 s.
`scripts/mede_cache_frio.py` e `scripts/bench_reconstruction.py` são os dois
instrumentos, e os dois já existem.

#### P4-9 — a D19 amplia uma lista fechada, e o caminho é `spec-change`

**M1 da primeira auditoria, e o auditor está certo no ponto processual.** O
argumento da D19 continua valendo — nenhum navegador envia `Authorization` numa
navegação, e a casca não carrega dado —, e **não é isso que está em questão**: a
lista de exceção de `05` §8 é **fechada pelo preâmbulo**, e ampliá-la por decisão
de fase é exatamente o que `spec-change` existe para carregar.

**Aberto como PR próprio**, com o argumento já escrito e sem código junto, na
ordem que `WORKFLOW.md` §"`spec-change` primeiro" fixa: ele é mergeado antes, a
branch da fase é rebaseada, e **a âncora é regravada no mesmo commit do rebase**.

**Enquanto ele não for aprovado**, `GET /console` é uma superfície pública que a
spec não isenta. A alternativa — não servir a casca pelo `range-api` — está
descrita na D19 e recusada com motivo.

> **✅ FECHADA pelo `spec-change` mergeado em `486df18`.** `05` §8 passou de uma
> exceção a uma **lista de duas**, e a segunda é a da casca: *"o HTML, CSS e
> JavaScript que o navegador carrega **antes de existir token**, e o endpoint de
> autenticação em si"*, com a linha que separa casca de serviço — *"nenhum dado
> de exercício trafega por ela"*.
>
> **A ordem de `WORKFLOW.md` foi cumprida inteira, e o terceiro passo é o que
> costuma faltar:** o `spec-change` foi PR próprio, sem código junto, mergeado
> primeiro; a branch da fase foi rebaseada sobre a `main` que já o contém; e **a
> âncora foi regravada de `6efca2e` para `486df18` no mesmo passo**. Sem o
> terceiro, `check_audit_base.py` recusaria esta rodada — o rebase move o ponto
> de bifurcação de verdade, e o predicado lê isso como âncora desatualizada.
>
> **O que a D19 sustentava por argumento passou a ter fonte.** O argumento não
> mudou e não precisava mudar; o que mudou é quem o carrega: era decisão de fase
> sobre uma lista que o preâmbulo de `05` fecha, e agora é a própria `05`. Era
> exatamente isso que o auditor apontou no M1, e ele estava certo no ponto
> processual.

#### P4-10 — itens 1 e 4 NÃO VERIFICADO: a proposta, e ela não está implementada

O auditor não pôde executar o DEMO nem a prova de reinício: os dois exigem Docker
e uma stack no ar, e `docker` está fora da allowlist pelo argumento da P2-19 —
**rede na mão do julgador é superfície permanente para resolver um problema de
uma vez**. O resultado é que os dois itens de DoD mais caros da fase chegam ao
veredito como NÃO VERIFICADO.

**É o mesmo padrão que a P2-19 resolveu uma vez**, e a forma da solução de lá é a
que esta proposta copia: **o que exige rede acontece no LANÇADOR, antes da
sessão, e o resultado chega pronto.**

| Opção | O que faz | Custo | Risco |
|---|---|---|---|
| **A — o lançador sobe a stack e roda as provas**, gravando a saída num arquivo que o auditor LÊ | o auditor julga uma execução real, feita na máquina do operador, sobre o commit auditado | ~3 min por rodada (build da imagem) | o auditor passa a **confiar num arquivo**: ele não viu rodar. É atestação com procedência melhor, mas ainda atestação |
| **B — `docker compose` e `docker inspect` entram na allowlist do auditor**, sem `run` arbitrário | o auditor executa as provas | zero | põe **rede e execução de container** na mão do julgador — o que a P2-19 recusou explicitamente |
| **C — nada muda**; os dois itens ficam NÃO VERIFICADO, sustentados pelo CI | honesto e barato | zero | o veredito da fase mais importante do projeto não cobre dois itens de DoD |

**Minha recomendação é a A, com uma condição que a torna diferente de
atestação:** o arquivo que o lançador grava carrega o **SHA do commit** e a saída
íntegra dos scripts, e o auditor **reprova** se o SHA não for o do worktree que
ele está julgando. Isso não faz o auditor ver a execução, mas amarra a evidência
ao objeto — que é a diferença entre "alguém rodou" e "rodou nisto".

**Não implementei.** A P2-19 é decisão de arquitetura de auditoria, e a lição do
B1 da Fase 2 é que "nada novo entra" também precisa ser decidido — por quem
decide.

---

## 7. Próxima fase

`07` Fase 5 — **Dados e auditoria ⏸**. ENTRY: Fase 4 completa.
