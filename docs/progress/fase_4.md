# Fase 4 — VERTICAL SLICE ⏸

**Status: EM CURSO — peças 0 a 4 de 7 fechadas.** A branch nasceu em `6efca2e` — a
âncora está gravada em `docs/process/phase_anchors.tsv`, e ela é o primeiro item
do procedimento novo, não formalidade.

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
| 0 | **aparato**: P3-4 e P3-8 ✅ | as duas vencem antes deste checkpoint, e as duas mudam o que o auditor consegue medir |
| 1 | **superfície do range-api** declarada + o verificador generalizado (D4, D6) ✅ | antes de existir rota, como na Fase 3 |
| 2 | **projeções de sala**: painéis por taxonomia, índice de saúde, timeline, frame total (D2, D3, D14) ✅ | funções puras, testadas sem servidor |
| 3 | **reconstrução do exercício** a partir do store: T0, acumulado, multiplicador, origem de epoch, pausa ✅ | é o item 4 da DoD e T5, e não depende de HTTP |
| 4 | **o range-api**: HTTP + WebSocket + autenticação do gm-console (D5) ✅ | a latência do item 2 é medida aqui |
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

## 4.6 A peça 5 — o que ela recebe pronto, e o que já foi medido

**Não aberta.** A sessão que fechou as peças 0 a 4 parou aqui por contexto, e
esta seção existe para que a próxima não redescubra nada. É a mesma razão da §0:
conversa não é fonte versionada.

### O que a peça 5 fecha

Quatro pendências: **P3-5** (business state em Postgres), **P3-10** (a `Cota`),
**P3-11** (guarda de boot do adapter) e **P4-1** (idioma dos caminhos).

### As decisões já tomadas, com a fonte conferida

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

## 4.7 Uma nota de processo: `HEAD` se moveu entre dois turnos

Entre o fim da peça 4 e a abertura da peça 5, a árvore estava em `main`, e não na
branch da fase. **Nada se perdeu** — a branch seguia intacta em `a3e5043`, com os
sete commits —, mas a árvore de trabalho mostrava o conteúdo da Fase 3.

É a corrida que `WORKFLOW.md` §"Árvore de trabalho compartilhada" descreve, e a
terceira ocorrência registrada. **O guarda de branch não a alcança**: ele olha
para onde o commit vai cair, e aqui `HEAD` se moveu durante uma leitura.

**O que a pegou foi a convenção, e não um mecanismo:** *"na dúvida, verificar
`git branch --show-current` e `git status` antes de agir"*. Sem isso, a peça 5
teria sido escrita sobre a Fase 3 — importando módulos que não existem lá —, e o
`pre-commit` só a barraria no fim, depois do trabalho inteiro.

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
| P3-4 | ~~no worktree de auditoria, `range_core` vem da árvore principal~~ | ✅ **FECHADA** na peça 0 |
| P3-5 | business state em dicionários de módulo | **peça 5** (D8) |
| P3-8 | ~~dois falsos bloqueios do hook do auditor~~ | ✅ **FECHADA** na peça 0 |
| P3-10 | `Cota` é estado mutável fora das cinco camadas de `01` §4 | **peça 5** (D9) |
| P3-11 | flag declarada e ausente do estado vira no-op silencioso | **peça 5** (D10) |
| P4-1 | os caminhos da `academus-api` estão em português, e `CLAUDE.md` põe endpoints em inglês | **peça 5** — ver abaixo |
| P4-2 | a família `eventos` não roda no perfil de domínio, e emitir sem declarar não tem guarda em lugar nenhum | **Fase 5** — ver abaixo |
| P4-3 | a página crua de `/sala` é provisória e a peça 6 a substitui | **peça 6** — ver abaixo |
| P4-4 | oito flags declaram `academus-api` como consumidora e nenhuma rota as consome | **Fase 8** — ver abaixo |

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

#### P3-11 — flag declarada e ausente do estado vira no-op silencioso

`estado.flags.get(entrada.flag)` devolve `None` para flag que o estado corrente
não tem, e aí `ligada` não dispara e `proporcional` lê `0.0`. A rota não degrada,
e nada avisa. O gate protege o repositório; não protege o exercício em curso.

Ver a **D10**: a guarda de boot só tem sentido onde há boot, e o boot é desta
fase.

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

---

## 7. Próxima fase

`07` Fase 5 — **Dados e auditoria ⏸**. ENTRY: Fase 4 completa.
