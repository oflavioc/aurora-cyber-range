# Fase 9 — Evidência e telemetria

**Status: ABERTA** — branch `claude/fase-9-evidence-telemetry-c49cf4`, âncora
`c77120c` (a `origin/main` pós-fechamento da Fase 8). A linha de status existe
porque `check_readme_atual.py` decide *"a fase fechou?"* por ela; ela só muda
com o veredito do `checkpoint-auditor`.

**Por que este registro nasce antes da fase.** Vinte e seis pendências
não-fechadas migram para cá, e pendência sem lugar é pendência que ninguém
encontra. `check_progress_consistency` cobra que toda pendência não-fechada da
fase N apareça na tabela-resumo da fase N+1 — e cobra seção de detalhe para cada
linha. Este arquivo é esse destino, e nasce com a pauta inteira herdada antes da
primeira linha de implementação. É a mesma razão pela qual o `fase_8.md` nasceu
antes da Fase 8.

## 1. Plano da fase

A Fase 9 é **evidência e telemetria** — `07_IMPLEMENTATION_PHASES.md` §"Fase 9".
O que a define é o princípio de `00_MASTER_SPEC.md` §5.3 e `08` §1: **uma
realidade, múltiplas projeções**. Não há gerador por fonte; há um fato canônico
em `ground_truth.yaml` e projeções determinísticas dele. É isso que torna
contradição entre fontes *estruturalmente impossível*, em vez de apenas
improvável — e é por isso que o evidence-simulator e o telemetry-forwarder
ficam sob **um contrato só** (`08` §2).

Os sete itens de DoD:

| # | Item de DoD | Fonte |
|---|---|---|
| 1 | Toda fonte é projeção de `fact_id`; nenhum gerador inventa entidade | `07` §Fase 9; `08` §2 |
| 2 | `range-cli evidence verify` valida consistência fato → projeções, dirigido por fato | `07` §Fase 9; `06` T13 |
| 3 | `precursor_events.jsonl` é reproduzível a partir do ground truth; edição manual detectada por hash | `07` §Fase 9; `08` §2; `06` T13 |
| 4 | Telemetria CEF é projeção, não emissão independente | `07` §Fase 9; `08` §2 |
| 5 | Nenhum arquivo contém anexo, binário, IOC real ou domínio roteável | `07` §Fase 9; `05` §2 e §3; `06` T13 |
| 6 | Replay respeita o clock de exercício | `07` §Fase 9 |
| 7 | A reconstrução da projeção **continua em < 3 s** com `telemetry_emitted` no volume de um exercício de 4 h | `07` §Fase 9; `06` T13 |

Os critérios de `06` T13 acrescentam duas exigências que não têm item próprio na
DoD e que são cobradas do mesmo trabalho: **fato sem `projections` não aparece em
nenhuma fonte** (o limite de detecção deliberado de `08` §2) e **banner de
ambiente simulado na primeira linha de cada arquivo** (`05` §4).

**ENTRY** — Fase 8 selada e mergeada em `origin/main` (`c77120c`). O contrato do
manifesto já existe e está completo: `contracts/evidence.schema.yaml` valida o
`MANIFEST.json` de `08` §7, com exemplo positivo e nove negativos, e declara em
comentário que *"quem consome, hoje: o evidence-simulator da Fase 9, que ainda
não existe"*. Esta fase é quem o exercita pela primeira vez — é a **P1-3**.

**A leitura disciplinada da spec desta fase** (CLAUDE.md §"Disciplina de
leitura"), feita na abertura: `00_MASTER_SPEC.md`, `09_EVENT_MODEL.md`,
`07` §Fase 9, `06` T13, `08_EVIDENCE_SIMULATOR.md` (o documento da fase, por
`00` §7) e `05_SECURITY_REQUIREMENTS.md` — a fase toca evidências, dados e
telemetria, então `05` §2 (evidências sintéticas), §3 (dados), §4 (banner) e
§5.1 (vendor/product fictício) são centrais e não admitem flexibilização.

## 2. A abertura, e o que ela carrega

### 2.1 O ambiente: o venv por worktree — não é defeito de árvore

A primeira execução da suíte nesta sessão deu **680 testes, 64 falhas e 61
erros**, sendo 65 do `tests/test_procedencia_dos_pacotes.py`. **Não era defeito
da árvore.** A instalação editável de PEP 660 é global e aponta para o checkout
principal; o finder vive em `sys.meta_path` e vence o `sys.path`, então
`range_core` (diretório com hífen, não importável pela árvore) resolvia pela
**árvore principal** enquanto `domains` e `contracts` resolviam pelo worktree —
dois commits no mesmo processo.

É exatamente a **P3-4**, e a metade que faz a prova passar já estava escrita em
`docs/process/WORKFLOW.md` §"O venv da auditoria": um venv próprio com a árvore
instalada. Criado em `.venv/` (já coberto pelo `.gitignore`), com
`pip install -e ".[test]" -c constraints.txt`, a suíte passa a **949 testes, OK,
163 pulos** — o número exato que o README declara para execução sem Postgres.

Fica registrado porque a R2 §3 é justamente isto: suíte vermelha exige
diagnóstico de **causa** antes de conclusão, e ambiente vem antes de código.

### 2.2 Três pendências que escaparam do mecanismo de migração

`check_progress_consistency` cobra a migração de pendência apenas entre fases
cuja tabela-resumo declara **coluna de estado** — as tabelas das fases 0 a 5 têm
três colunas, são anteriores ao vocabulário fechado da Fase 7, e o verificador as
**pula**, dizendo-o em voz alta. A consequência é que gatilho escrito lá não
chega a destino nenhum por máquina.

Três pendências com vencimento **explicitamente nesta fase** estavam nessa
situação e **não constavam da tabela-resumo da §6 da Fase 8**:

- **P1-3** — `evidence.schema.yaml` valida artefato ainda não produzido
  (`fase_1.md` §7.3: *"Fase 9"*);
- **P1-13** — duas cópias das faixas sintéticas, contrato × verificador
  (`fase_1.md`: *"unificar as duas fontes fica para a Fase 9, que é quem
  constrói o gerador"*; o próprio `contracts/evidence.schema.yaml:197` a nomeia);
- **P2-11** — `append` abre uma conexão por chamada (`fase_2.md`: *"Vencimento:
  Fase 9, junto da reavaliação do item 8"*).

As três entram na tabela abaixo com o prefixo de origem preservado. O **defeito
do mecanismo** que as deixou passar é a **P9-1**.

### 2.3 Duas lacunas do gabarito contra `08` §3 — e as duas fecham na peça 3

Medido na peça 1, lendo o gerador de gabarito. `domains/academus/seed/gabarito.py`
produz os fatos da Linha B (`grade_change_retroactive`, um por linha da trilha
semeada) com `fact_id`, `actor`, `source_ip`, `dest` e `records_affected` — e
**sem `projections`**. Só os três fatos da Linha A (`linha_a.py`) as declaram.

Pela regra de `08` §2, fato sem `projections` é **invisível ao time azul**. Mas
`08` §3 enumera as fontes v1 e diz, do `database_audit.jsonl`, que ele carrega
*"leitura em massa (Linha A) e alterações de nota com IP e sessão (Linha B)"*.
As duas leituras não cabem juntas: ou a Linha B projeta em `database_audit`, ou
a tabela de `08` §3 descreve um arquivo que não vai existir.

**Não é spec-change** — a spec está coerente, e é o gerador que está incompleto:
`08` §3 é autoridade sobre o que cada fonte carrega, e quem declara `projections`
é o gabarito, que é mecanismo. A correção é do gerador, e cai na peça que
constrói o `database_audit`.

Fica registrado aqui porque é exatamente a classe de defeito que `08` §1 existe
para impedir: a evidência que o time azul recebe deixaria de ter a linha de
integridade, e nada ficaria vermelho — a cobertura de projeção passaria, porque
fato sem `projections` **legitimamente** não projeta.

**A segunda lacuna apareceu ao escrever a peça 3, e é da mesma família.**
`08` §3 enumera `email.eml` com *"phishing de recadastramento — origem da
Linha A"*, e **nenhum fato declarava `projections: [email]`**: o gerador não
produzia o fato de phishing. Sem ele, o `.eml` seria conteúdo autoral em vez de
projeção — exatamente o que `08` §2 proíbe ao dizer que *"precursor_events.jsonl
deixa de ser artefato autoral: é gerado como projeção"*.

**As duas fecham na peça 3.** `linha_a.py` passa a sintetizar
`phishing_delivery` (determinístico por seed, antes do acesso inicial na ordem
do incidente), e `gabarito.py` declara `projections: [database_audit]` nos fatos
da Linha B. Nenhuma das duas é spec-change: `08` §3 é autoridade sobre o que
cada fonte carrega, e quem declara `projections` é o gabarito, que é mecanismo.

**E uma terceira, que o motor cobrou sozinho:** o gabarito já declarava `cef`
desde a P7-10, e o motor recusa por falha fechada a cobertura que pede fonte sem
gerador. Um pacote de geradores que parasse nas quatro de `08` §3 não projetaria
o próprio gabarito do projeto — então `cef` entrou aqui. É a metade-arquivo do
item 4; a outra (`telemetry_emitted` no event store) tem peça própria, e as duas
compartilham o gerador, que é o que `08` §2 quer dizer com *"um contrato só"*.

### 2.4 Prova negativa só vale conferida na suíte COMPLETA, e resolvida por `sys.modules`

**Três ocorrências da mesma família de defeito nesta fase, todas de instrumento
lido como ausência de detecção.** Registradas juntas porque a terceira só foi
reconhecida rápido por causa das duas primeiras.

1. **Peça 1 — `from pacote import submodulo`.** Os quatro mutantes morriam com o
   probe rodando sozinho e **sobreviviam** na suíte completa. O harness planta a
   mutação substituindo `sys.modules`; `from range_core.evidence import elenco
   as mod` liga ao **atributo do pacote**, que o harness não toca. Sozinho
   funcionava por acaso — o atributo ainda não existia.
2. **Peça 3 — o mesmo, com `linha_a` e com o `__init__` do pacote.** A mutação
   do fato de phishing não derrubava nada porque a suíte segurava
   `from domains.academus.seed import linha_a`; e as de `cef` e `jsonl` não
   derrubavam nada porque `geradores()` resolvia os submódulos por atributo.
   O `__init__` **não pode ser mutado**: o harness o carrega como módulo avulso,
   sem `__path__`. A saída foi do outro lado — `geradores()` passou a resolver
   por `import_module`.
3. **Peça 3 — `identity_audit` e `database_audit` segurando `jsonl`.** Import no
   topo guarda a função original; entram na lista de mutáveis **sem mutação
   própria**, só para serem recarregados depois. É a ordem de dependência que o
   cabeçalho do harness descreve e que `test_queda_de_sessao_probes.py` já usa.

A regra que fica: **prova negativa se confere na suíte completa, e tudo o que
ela muta resolve-se por `sys.modules`.** Isolada, ela pode estar medindo o acaso
da ordem de import.

### 2.5 A conferência empilha duas perguntas, e elas não são redundantes

Medido na peça 4, pela prova negativa. `conferir` compara o `sha256` do
manifesto **e** o conteúdo reprojetado, e a mutação que removia a primeira
comparação **não matava teste nenhum** — a segunda pegava a edição de qualquer
forma.

Não era gate frouxo: as duas perguntas são diferentes.

- **o `sha256`** pergunta *"o arquivo é o que foi escrito?"*;
- **a reprojeção** pergunta *"o arquivo é o que o gabarito projeta?"*.

Quem edita o arquivo **e** atualiza o hash no manifesto passa pela primeira, e só
a segunda o pega. E quem edita só o arquivo é pego pelas duas — mas com
**mensagens diferentes**, e `06` T13 nomeia o hash como o mecanismo da detecção
de edição manual. Sem a comparação de hash, a edição simples era reportada como
*"manifesto e arquivo foram alterados juntos"*, que é falso.

O gate ganhou dois casos por causa dessa medição: um que exige a mensagem do
hash, outro que exerce o conluio — e a mutação passou a morder. **A redundância
aparente era divisão de trabalho**, e o que faltava era um teste que a
distinguisse.

### 2.6 O hook defendeu a fronteira, e a conveniência era plausível

Medido na peça 5. A primeira versão de `range-core/telemetry/catalogo.py` trazia
um atalho `do_academus(contratos)` — conveniência de composição, para o chamador
não montar o caminho. O hook `check_architecture` **bloqueou a escrita**:
invariante 1, `range-core/` não importa de `domains/`.

O atalho não mudou de forma, mudou de lado: foi para
`domains/academus/telemetria.py`, que é quem sabe onde mora o próprio arquivo. O
núcleo carrega e confere; **qual fato do mundo acadêmico vira qual sinal de SIEM
é conhecimento do adapter**.

Fica registrado porque a conveniência era plausível e o defeito seria invisível
no verde — é exatamente assim que uma fronteira vaza. E é a diferença que a §1.6
do registro da Fase 1 estabelece: **instrução é regra; hook é impedimento**.

### 2.7 `achados_no_valor` julga VALOR, não texto — a guarda que não guardava

Medido na peça 3, e é a lição mais cara dela. O item 5 exige *"nenhum arquivo
contém anexo, binário, IOC real ou domínio roteável"*, e o predicado que
responde isso já existe em `dados_sinteticos` — reusá-lo em vez de escrever um
segundo é a lição da P1-13.

Mas `achados_no_valor` opera sobre **um valor de campo**: `hostnames_candidatos`
assume que o valor é uma URL, um e-mail ou um hostname nu, e **texto com espaço
no meio ele descarta**, devolvendo lista vazia. Chamado sobre o conteúdo inteiro
de um arquivo de log, ele passa vacuamente: `"visite https://<host roteável>/login"`
não produz achado nenhum.

A primeira versão da guarda do motor fazia exatamente isso — e a primeira versão
do teste que a julgava, também. **A guarda parecia proteger e não protegia, e o
teste concordava com ela.**

A correção é tokenizar antes de julgar, e a divisão de responsabilidade fica
declarada: **a tokenização é do motor; o julgamento continua sendo do predicado
único.** Ensinar `dados_sinteticos` a ler texto livre mudaria a semântica de um
módulo que o CI e o loader já consomem, para servir a um chamador só.

O teste usa `split()` puro e o motor usa uma regex que também corta pontuação —
**as duas tokenizações são diferentes de propósito**: um teste que reusasse a do
motor deixaria de ser oráculo independente e aprovaria um defeito na própria
tokenização. E a prova negativa restaura o defeito exato, porque sem ela nada
distinguiria a guarda que funciona da que não funciona.

### 2.8 O volume do item 7, e a margem que eu declarei sem poder declarar

**Medido na peça 6, e é o item desta fase que precisou de três declarações
retiradas antes de fechar — duas na 1ª auditoria, uma na 2ª.**

> A frase original desta linha dizia *"o primeiro item de DoD desta fase que não
> fecha"* — verdadeira enquanto 833/min estourava, e **resíduo** depois de
> 400/min ser adotado: o item 7 fecha, e a §3 o marca VERDE. Duas afirmações
> opostas no mesmo documento, num registro que é o insumo declarado do auditor.
> Foi o M3 da 1ª auditoria.

> **E A TERCEIRA RETIRADA É A MAIS INSTRUTIVA — H3 da 2ª auditoria.**
>
> Esta seção afirmava *"folga ≥ 28%"* e *"cruzar os 3 s exigiria um desvio de
> 0,85 s a partir do pior caso observado"*. A prova gravada contra a árvore
> final deu **2,750 s**: a folga real era de 8%, o valor ficou 0,60 s acima do
> "pior caso" declarado, e caiu **dentro** da faixa que a tabela atribuía a
> 500/min — o volume que esta mesma seção rejeitou por *"não ter margem
> reprodutível"*.
>
> O critério `< 3 s` continuou passando. **O que não passou foi o argumento de
> método**, e ele é o que esta seção põe no centro: eu deduzi uma dispersão de
> cinco execuções e a tratei como limite. Cinco execuções não limitam nada —
> elas descrevem a máquina naquele intervalo, com aquela carga.
>
> A correção não é medir mais e declarar outra faixa. É **parar de declarar
> margem em prosa**: o que esta página pode afirmar com honestidade é o que foi
> observado e quando, nunca o que não será excedido.

`06` T13 cobra que a reconstrução *"continua em < 3 s"* com `telemetry_emitted`
no volume de um exercício de 4 h, e `07` §Fase 9 diz que telemetria *"pode
chegar às centenas de milhares sozinha"*. O harness da Fase 7 foi estendido com
a composição da Fase 9 — **sem tocar a da Fase 7**, porque as duas medem o mesmo
exercício e a comparabilidade é o que torna o "continua" uma afirmação.

A curva, no mesmo ambiente (Windows-11, Python 3.12.10, PostgreSQL 16.4,
psycopg 3.2.12, migração `0004`):

A tabela abaixo é **histórico de observações**, e não previsão. Cada linha diz o
que aquela execução mediu naquele dia, naquela máquina — nenhuma delas afirma o
que a próxima medirá.

| telemetria/min | eventos | observações | veredito das observações |
|---|---|---|---|
| 0 (composição da Fase 7) | 650 | 0,043 s | todas abaixo de 3 s |
| 200 | 48.650 | 1,026 s | todas abaixo de 3 s |
| **400 — o declarado** | **96.650** | 1,73 / 1,79 / 2,02 / 2,04 / 2,15 / **2,75** s | **todas abaixo de 3 s, em nove execuções** |
| 500 | 120.650 | 2,626 / 2,798 / **3,084** s | **uma acima, em três execuções** |
| 600 | 144.650 | 3,162 s | acima |
| 833 | 200.570 | 3,812 s | acima |

O **2,75 s** em negrito é a gravação que o H3 trouxe, e ele está na tabela pela
mesma razão pela qual achado refutado permanece riscado (R2 §5): tirá-lo faria
esta página voltar a descrever uma dispersão menor do que a observada.

> **O VALOR EXATO MORA NA PROVA, E NÃO NESTA PÁGINA — e a razão é um ciclo
> medido, não preferência de redação.**
>
> O H3 da auditoria pediu que o registro citasse o número da prova. Cumprir isso
> ao pé da letra abre um ciclo:
>
>     o registro cita o valor → commitar muda a árvore → a prova é regravada
>     contra a árvore nova → devolve outro número → o registro fica errado → ...
>
> Três regravações consecutivas deram **2,017 / 2,043 / 2,147 s**. Nenhum está
> errado: é a variância da máquina. O que está errado é amarrar prosa commitada
> a uma medição que só existe **depois** do commit — e a primeira tentativa de
> consertar isso com uma faixa fechada (1,73–2,05 s) foi ultrapassada pela
> regravação seguinte, o que prova o ponto.
>
> **A fonte única do valor é `check_prova_do_exercicio_4h.py`**, que o imprime e
> o confere contra a árvore. Esta página registra as observações e quando elas
> aconteceram; quem quer o número da gravação corrente roda o verificador. É a
> mesma regra que o resto do projeto aplica a contagem de suíte: o registro
> canônico é o dado, a prosa aponta para ele.

#### A folga é fina, e isso está declarado — não contornado

A tentativa seguinte de fechar o H3 foi **argumentar a margem a partir da
dispersão**: cinco execuções entre 1,73 s e 2,15 s, dispersão de ~0,42 s, logo
cruzar os 3 s exigiria o dobro dela. A gravação seguinte deu 2,75 s e derrubou o
argumento inteiro — a amostra não limitava a máquina, apenas a descrevia.

O que sobra, dito sem enfeite:

- **o critério passa**, e quem o afirma é o verificador, contra a árvore;
- **a dispersão observada é da mesma ordem que a folga**. Uma gravação futura
  acima de 3 s é possível, e não seria surpresa;
- **se acontecer, a saída não é diminuir o volume.** Isso seria mover a régua até
  caber, que é o que o resto desta seção recusa em dois lugares. A saída é a
  otimização já nomeada — atacar a reserialização da cadeia, o custo dominante
  decomposto logo abaixo.

Declarar o risco é mais barato que descobri-lo na próxima auditoria: foi
exatamente por não o declarar que esta seção precisou ser reescrita duas vezes.

**Ponto de quebra entre 120 mil e 144 mil eventos**, coerente com a curva da
Fase 2 (~150 mil, 2,874 s) — o mesmo motor, medido de novo com a fonte que a
Fase 2 nomeou como quem reabriria o item.

#### A linha de 500/min é a que importa, e ela é sobre método

O proprietário decidiu 500/min **com a curva à vista**, depois de a primeira
declaração (833/min, justificada pela cardinalidade de `AUTH_FAIL`/`AUTH_BRUTE`
num ambiente com as 29.200 contas de `02` §1) ter estourado. À época, 500/min
tinha **uma** medição: 2,626 s.

Repetida três vezes, ela deu 2,626 / 2,798 / 3,084 s — **cruza o orçamento numa
delas**. A variância entre execuções (~0,45 s) é maior que a folga.

**Critério de desempenho que falha em 1 de 3 execuções não é critério, é
sorteio.** E o agravante é estrutural: a prova é gravada **uma vez** e amarrada
por hash à árvore, então o veredito passaria a depender de qual execução foi
gravada — com o auditor podendo obter o oposto ao reexecutar. A decisão foi
levada de volta ao proprietário com esse dado, e 400/min foi escolhido porque
**nenhuma execução dele cruzou o orçamento**, enquanto 500/min cruzou na
terceira.

**Essa é toda a distinção, e ela é mais modesta do que a redação anterior
afirmava.** A versão que o H3 derrubou dizia *"folga de ao menos 28% em cinco
execuções"* — e nove execuções depois, a pior está a 8%. O que continua
verdadeiro é o comparativo: nas observações registradas, 400/min não mudou de
veredito e 500/min mudou. O que nunca foi verdadeiro é a margem como garantia.

#### A causa, decomposta

Com 200.570 eventos, medido isoladamente:

| etapa | custo |
|---|---|
| query + transporte, sem JSON | 0,13 s |
| desserialização JSONB → dict **pelo driver** | 1,19 s |
| construção de 200 mil `Event`/`Correlation` | ~0,5 s |
| `verify_chain` — reserialização canônica + SHA-256 | 1,19 s |
| `project` (o fold) | 0,11 s |

**O custo dominante é um ciclo desserializar → reserializar.** O `payload` e o
`correlation` vêm do banco como JSON, viram `dict`, e `canonical_form` os
transforma em JSON canônico outra vez para conferir o hash.

#### O que NÃO é saída

**Tornar a verificação de cadeia opcional.** `postgres_store._stored` já declara
por que: *"a verificação é incondicional, e não há como desligá-la — um
`verify=False` seria a porta que a próxima pressa usaria, e store adulterado que
responde produz projeção plausível e falsa"*. É `01` §4.1 e `05` §7. Desligá-la
para passar no orçamento seria enfraquecer o gate, que é o que a R10 §1 proíbe
em primeiro lugar.

**Escolher o volume que faz passar.** O número é declarado por mim; declarar
500/min em vez de 833/min faria o item ficar verde sem que nada no motor
mudasse. Isso é a mesma classe: mover a régua até o resultado caber.

#### A otimização que foi medida e NÃO adotada

`::text` + `json.loads` em vez da desserialização do driver é mais barato
**isoladamente**: 0,929 s contra 1,192 s sobre 200.570 eventos.

**Aplicada em `_stored`, o ganho não apareceu.** Com a troca, o `read_all`
completo mediu 2,980 s e 2,851 s; sem ela, 2,988 / 3,076 / 2,546 / 2,719 s. A
variância entre execuções é maior que o ganho, e o `json.loads` dentro do laço
que já constrói `Event` e `Correlation` dilui o que o benchmark isolado
mostrava.

**Revertida**, e o registro ficou em comentário no próprio `postgres_store.py`:
complexidade a mais numa superfície de `05` §7 sem benefício reprodutível é
custo, e quem voltar a este ponto começa sabendo que o gargalo **não** está por
onde o JSON passa.

O caminho com ganho suficiente é atacar a **reserialização da cadeia** (teto
~1,0 s) — mudança estrutural, não otimização local, e fora do escopo desta fase.

#### As duas pendências de volume, e só uma venceu

**A P4-8 venceu aqui, e com número.** Ela dizia *"leitura síncrona no laço de
eventos serializa e bloqueia em volume"*, com gatilho declarado em "medição de
volume". A medição existe, e é precisa: `read_all` é 97% do custo total, e
dentro dele o ciclo desserializar → reserializar domina.

**A P2-11 NÃO foi exercitada, e isso é limite e não descuido.** Ela é sobre
`append` abrir uma conexão por chamada — **escrita**. A carga do harness é em
lote, como a do bench, porque o que o critério mede é **reconstrução**. Ela
segue `ABERTA`, com o gatilho intacto, e a fase não pode alegar tê-la fechado.

### 2.9 A 1ª auditoria — FAIL, e o que ela achou

`docs/progress/audit_20260922T200341Z.md`, sobre `b4b5f50`. **Veredito FAIL**,
por um BLOCKER mecânico, mais 3 HIGH, 4 MEDIUM e 2 LOW.

**O B1 é processual e a causa é de disciplina, não de código.** A prova do
exercício de 4 h foi gravada contra a árvore de `3b3e9c2` e **dois commits
entraram depois** (a recusa nomeada do lançador e os pins dela) — que órfãos a
prova. `check_prova_do_exercicio_4h.py` reprovou com a leitura certa: *"o código
que mediu é OUTRO"*. O instrumento não falhou; **acusou**.

A regra que fica: **a prova de 4 h é o ÚLTIMO artefato antes do disparo.**
Gravá-la no meio e continuar commitando é o que a órfã, e nenhum gate pega isso
antes do auditor.

**E a nota de entrada do laudo é procedente.** O resumo que enviei declarava
`3b3e9c2` como candidato, e eu continuei commitando depois de escrevê-lo —
inclusive a correção que o proprietário pediu. Toda a evidência daquele resumo
era de outra árvore. R2 §4: mensagem de agente não é evidência.

#### O que cada achado produziu

| Achado | Disposição |
|---|---|
| **B1** — prova órfã | regravada contra a árvore candidata, como **último** passo |
| **H1** — `evidence verify` fora do CI | passo novo em `invariants.yml`, sobre o `evidence/` **versionado** do pack de exemplo — e isso o torna gate de **regressão do gerador**, não fumaça |
| **H2** — banner com duas fontes vivas | quarto eixo em `check_banner_de_simulacao.py`: `05` §4 × `banner_text` do contrato, com 4 direções de prova negativa |
| **H3** — três números para a mesma medição | a §2.8 e a §3 passam a citar **o número da prova** (a fonte única passa a ser o verificador), e a variância entre a linha exploratória e a prova fica registrada |
| **M1** — registros de adiamento mentindo | a classe `evidencia` vira **coberta e varrida**; a §2 de `check_secoes_de_seguranca` ganha mecanismo real; o dono de `relatorio` corrigido para Fase 10 |
| **M2** — payload de telemetria não ligado | binding por `event_type` no `allOf`, com dois exemplos negativos (`fact_id` e assinatura inventada) |
| **M3** — contradição na §2.8 | a frase resídua reescrita, com o motivo registrado |
| **M4** — P1-13 sem disposição | **RESOLVIDA**: o cruzamento das faixas de IP fecha a metade que faltava |
| **L1** — `verify` sem tratar recusas do motor | captura nomeada, como o `build` já tinha |
| **L2** — regras do linter sem dono | as quatro ganham `mecanismo` no contrato |
| **teste CEF por substring** | passa a comparar a **linha do próprio fato**, não o arquivo inteiro |

#### Dois defeitos que a correção do M1 descobriu

**A tokenização não cortava no `=`.** Log de fio é `chave=valor`, e o token
virava `url=https://<host>/x` — `urlsplit` não reconhece `url=https` como
esquema, e o IOC atravessava. O caso que existia usava `"visite https://..."`,
**com espaço**, e por isso o defeito sobreviveu à peça 3: o único teste era o que
não o alcança. Corrigido no motor e no verificador, com caso e mutante próprios.

**O `evidence/` versionado não era varrido.** `check_synthetic_data.py`
declarava, no próprio cabeçalho, que `.log`/`.eml` ficavam fora **e nomeava a
Fase 9 como quem fecharia** — e eu não fechei. Pior: ao versionar o `evidence/`
para o H1, criei arquivo de evidência na árvore que nenhum verificador olhava.
Fechado com `TEXT_SUFFIXES` + varredura token a token, com número de linha.

### 2.10 A 2ª auditoria — FAIL, e o achado que redefine a fase

`docs/progress/audit_20260923T191036Z.md`, sobre `36e139c`. **Veredito FAIL**,
por 1 BLOCKER, 4 HIGH, 4 MEDIUM e 2 LOW.

#### O B1 não é um defeito de implementação. É a fase inteira olhando para o lado errado

> *"A evidência entregue ao time azul carrega o veredito do gabarito:
> `credential=compromised`."*

Três fontes escreviam `credential_state` — `vpn.log`, `identity_audit.jsonl` e o
`cef.log` —, e o valor no fato real é `compromised`. **Nenhum concentrador de VPN
do mundo registra que uma credencial está comprometida**, porque isso é
atribuição, e atribuição é o achado que o exercício existe para medir. A segunda
linha do `vpn.log` entregava pronta a conclusão que o próprio fato manda
correlacionar (`discoverability.requires`: *"correlacionar horário fora de
expediente com ausência de MFA"*).

**O que torna este achado severo não é o campo. É que eu escrevi o argumento
certo e não o apliquei.** O cabeçalho de `vpn.py` recusava `suspicious=true`
dizendo que *"entregaria a resposta e misturaria as camadas de `00` §3"*. O de
`precursor.py` excluía `actor` **e `credential_state`** dizendo que *"atribuição
é o achado, não o insumo"*. Quatro geradores, dois com a doutrina escrita e três
violando-a — porque a doutrina estava em **comentário**, e comentário depende de
cada autor lembrar.

A fase passou seis peças construindo portas para "não inventar entidade" e "não
vazar IOC", e nenhuma para **"não afirmar ground truth"** — que é a primeira das
quatro verdades de `00` §3, a camada que o projeto inteiro existe para separar.

A correção é estrutural e não é uma lista de proibidos:
`contracts/evidence.schema.yaml` §`x-aurora-registry.fact_fields` **particiona**
os campos de `$defs/fact` em `projectable` / `ground_truth_only` / `structural`,
`projetar` recusa o que não for projetável (`VereditoDoGabarito`), e
`check_contract_examples.py` cruza a união das três com as `properties` do
contrato de ground truth — **campo novo no fato reprova até ser classificado**.
Lista de proibidos envelhece calada; partição conferida não.

#### O H1 e o B1 são o mesmo defeito, em duas camadas

`cef.py` tinha mapeamento próprio — `signature` = `fact_class`, severidade fixa
5, sem `outcome`, `credential_state` em `cs1` — enquanto `telemetry_emitted` saía
do catálogo de `02` §10. Para o **mesmo fato**, o arquivo dizia
`initial_access|…|5` e o evento dizia `SERVICE_ACCOUNT_ANOMALY`, severidade 7,
`outcome=success`.

`08` §2 diz que a telemetria CEF é projeção, *"e isso unifica evidence-simulator
e telemetry-forwarder sob um contrato só"*. Eu li isso como **disciplina de
escrita** — dois geradores coerentes — e escrevi na §3 que havia "um gerador só".
Não havia: havia dois caminhos de código em camadas diferentes, que já nasceram
divergentes.

"Um contrato só" é **um produtor só**. Hoje `cef.py` chama `programar` — o mesmo
que produz o evento — e renderiza o payload com `range_core.telemetry.cef.linha`.
O que o arquivo diz é o que o event store carrega, porque é o mesmo dicionário.

> **E o teste dependia da divergência para funcionar.** Ele localizava a linha
> CEF pela `fact_class` — só o gerador antigo punha a classe do fato no campo de
> assinatura. Um par que compara dois campos de sete e acha a linha pelo que
> difere não prova unificação nenhuma. Hoje a asserção é de igualdade **total**,
> nos dois sentidos.

#### O que cada achado produziu

| Achado | Disposição |
|---|---|
| **B1** — veredito do gabarito na evidência | partição declarada no contrato + `VereditoDoGabarito` no motor + verificador que cobra a cobertura da partição; `credential_state` sai das três fontes |
| **H1** — dois contratos para a mesma projeção | `range-core/telemetry/cef.py` renderiza o payload de `programar`; o gerador do adapter deixa de mapear; fato roteado para `cef` sem assinatura vira **recusa nomeada** |
| **H2** — `verify` não confere a cobertura por fato | `conferir` passa a comparar `projects_facts` e `format`; o teste que não chamava `conferir` foi partido em dois, com o nome de cada um dizendo o que ele julga |
| **H3** — margem declarada que a prova desmente | a §2.8 para de declarar margem: a tabela vira **histórico de observações**, e o risco residual fica escrito |
| **H4** — 1º critério de T13 sem teste | `AsProjecoesDoMesmoFatoSaoMUTUAMENTEConsistentes` — fato escrito **à mão**, cinco fontes, um parser por formato de fio, igualdade entre o que cada um extraiu |
| **M1** — `evidence/` versionado reprova em checkout Windows | `.gitattributes` com `eol=lf` para `**/evidence/*`, mais dois casos: um mede o sintoma (CR no disco) e outro a causa (o atributo declarado, que o CI cobra) |
| **M2** — "não inventa entidade" só guardava IP | hostname vira a **segunda forma fechada** do oráculo; os dois fallbacks inventados de `email.py` saem; as afirmações falsas sobre o alcance da reprojeção são corrigidas onde estavam escritas |
| **M3** — `delivery_mode` sempre `pre_positioned` | o CLI lê `evidence_release` dos injects; fonte liberada que o gabarito não projeta vira recusa |
| **M4** — nenhum produto emite `telemetry_emitted` | `range-core/telemetry/emissao.py` + `LoadedPack.telemetria` + `InjectEngine.tick_de_telemetria()`, composto em `processo.criar` por variável de ambiente **exigida** |
| **L1** — `phishing_delivery` → `AUTH_FAIL`/`failure` | o mapeamento sai: o gateway **não** barrou o phishing, e é por isso que há Linha A. Fato sem assinatura é o limite de detecção de `08` §2 |
| **L2** — README datando o fechamento de uma fase aberta | redação corrigida, contagem reconferida |

#### Três defeitos que a correção descobriu, e não estavam no laudo

**A tokenização não cortava no `|`.** O cabeçalho CEF é
`CEF:0|vendor|produto|versão|assinatura|NOME|severidade|`, e o `NOME` sai de
`action` — campo do fato. Sem cortar no `|`, o token vira o cabeçalho inteiro,
não tem forma de host, e um domínio roteável escrito ali **atravessa a guarda de
IOC**. É o mesmo defeito do `=` na 1ª auditoria, com outro separador: a família
não se descobre por inspeção, ela se descobre quando um formato de fio novo
chega. Os separadores agora estão declarados, com a data de cada um.

**A unificação do H1 deixou um gate sem dono.** Enquanto o arquivo e o evento
tinham caminhos próprios, compará-los guardava conteúdo. Desde que os dois saem
do mesmo `programar`, um campo que suma do payload some dos dois e a igualdade
continua verdadeira — **a mutação *"o `src` sai do payload"* parou de derrubar
qualquer teste**. Medido pelo harness, não previsto. Nasceu
`test_o_payload_carrega_os_campos_do_FATO`, com o mapa de `02` §10 escrito à mão
no teste.

**A prova negativa estava intermitente, e a causa era minha.** `cli.py` fazia
`from range_core.evidence import build`, que resolve pelo **atributo do pacote**;
o harness substitui `sys.modules`. O CLI rodava o módulo original enquanto o
resto da suíte rodava o mutado — e o conjunto vermelho declarado passou a
depender da **ordem** em que a suíte importou o pacote. É a quarta ocorrência
desta família na fase, e a terceira com a mesma correção (`import_module`).

### 2.11 A 3ª auditoria — FAIL, e os dois BLOCKERs são meus

`docs/progress/audit_20260924T172008Z.md`, sobre `9ba5973`. **Veredito FAIL**,
por 2 BLOCKERs, 1 HIGH, 2 MEDIUM e 2 LOW.

#### O B1 é o B1 da rodada anterior, por outro canal — e eu o introduzi corrigindo outra coisa

> *"`database_audit.jsonl` entrega o gabarito da Linha B: quais linhas são
> casos, e em que conjunto cada uma está."*

Na peça 3 eu acrescentei `projections: ["database_audit"]` aos fatos da Linha B,
citando `08` §3 (*"alterações de nota com IP e sessão"*). **A citação estava
certa e a conclusão estava errada**, e o motivo está três linhas acima do laço
que os cria: ele percorre `CONJUNTOS_DE_CASO`, que são **três dos seis**.

Os únicos fatos que a Linha B tem são os **casos**. Projetá-los produz um arquivo
com 67 linhas numa população de 3.145 — e quem o abre sabe quais são caso sem
analisar nenhuma. A defensibilidade vinha de brinde, na ordem: o gabarito agrupa
por conjunto e a projeção preserva a ordem do documento.

**É exatamente a mesma falha do B1 da 2ª rodada, um nível acima.** Lá o vazamento
era de CAMPO — `credential_state` dizendo a resposta dentro da linha. Aqui é de
CONJUNTO: nenhum campo vaza, e o arquivo inteiro é a resposta. A guarda que
construí para o primeiro não tinha como ver o segundo, porque ela olha conteúdo e
este defeito está na **cobertura**.

E o conserto não é projetar os seis conjuntos. Os outros três são 3.078 linhas de
trilha — dado acadêmico real, semeado, que `01` §2 põe em business state.
Transformá-las em `fact_id` faria o `ground_truth.yaml` virar cópia da tabela, e
`linha_a.py` já registra a fronteira: o incidente é sintetizado porque é overlay,
a Linha B é **lida** porque é dado. A metade Linha B de `08` §3 fica em aberto,
com mecanismo nomeado — **P9-4**.

A porta nova (`RespostaEntregue`) julga **por espécie de fato**, e a distinção é o
que a torna usável: um arquivo com 67 casos entre 3.145 linhas não revela nada;
um com 67 de 67 revela tudo. Uma guarda que olhasse a fonte inteira aceitaria a
diluição por uma classe que o time azul nem confunde com a outra — e esse é o
mutante espelhado que acompanha a porta.

#### O B2 é o preço de uma correção feita pela metade

O M4 da rodada anterior ligou `Replay` ao event store. Eu passei **todos** os
fatos a `programar`, e o `cef.log` continuou filtrado pela cobertura. Resultado:
o SIEM do exercício mostrava sinal de fato que **não tem linha no arquivo** — e
teria mostrado de fato sem `projections`, que `08` §2 define como invisível ao
time azul.

A afirmação que escrevi na §3 — *"um produtor só, o mesmo dicionário"* — era
verdadeira sobre o **formato** do payload e falsa sobre a **população**. Os dois
sentidos precisam valer, e agora o conjunto sai de `cobertura_de`, que é a mesma
função que o motor consulta. Dois filtros equivalentes divergiriam na primeira
regra nova; um filtro só não tem como.

> **E o teste escondia isso.** O `setUp` pré-filtrava os fatos por `cef` antes de
> `programar`, com um comentário dizendo que passar todos *"mediria uma
> composição que não existe"* — e era exatamente a composição que o loader fazia.
> O outro caso comparava com `len(self.pack.telemetria)`, que é a própria saída
> do produto: tautológico sobre **quais** fatos viram telemetria. A fixture do
> pacote completo ganhou os três casos (projeta em `cef`, projeta em outra fonte,
> não projeta) para que a suíte tivesse o que distinguir.

#### O que cada achado produziu

| Achado | Disposição |
|---|---|
| **B1** — a fonte entrega a resposta | `RespostaEntregue` julga por espécie, sobre a COBERTURA e antes do gerador; a projeção da Linha B sai; a metade `08` §3 vira **P9-4** |
| **B2** — telemetria de todos os fatos | o loader pede o conjunto a `cobertura_de`; a fixture ganha os três casos; dois mutantes |
| **H1** — `ingest_time` inexpressável | `event_time` e `ingest_time` entram no contrato de telemetria. A primeira é da **projeção** (sai de `programar`, e o `cef.log` a escreve no prefixo syslog); a segunda é de **quem grava**, porque só existe no ato de gravar |
| **M1** — filtro genérico no teste de T13 | `OMISSOES` nomeia a única ausência admitida, e um segundo caso cobra que ela **aconteça** — permissão pendurada é por onde a próxima entra |
| **M2** — resíduo do H3 | o argumento de margem sobrevivia em `medida_do_exercicio_4h.py`, que é **onde ele nasceu**; a correção da 2ª rodada só alcançou o registro |
| **L1** — `window` e `delivery_mode` sem conferência | os dois degraus entram em `conferir`, e o `verify` passa a receber a entrega declarada pelo pack |
| **L2** — `MANIFEST.json` sem banner | `_banner` vira `required` no contrato, primeira chave do documento, com exemplo negativo próprio |

#### O que a correção do H1 apertou sem querer

O carimbo do prefixo syslog do `cef.log` vinha **de fora** do payload, por
parâmetro. Com `event_time` dentro dele, o renderizador passou a lê-lo de lá — e
com isso a última coisa que o arquivo escrevia e o evento não tinha desapareceu.
A asserção de igualdade entre a linha e o payload cobre agora as três chaves de
cabeçalho e todas as extensões, nos dois sentidos.

## 3. Itens de DoD — status e evidência

A §7 de fechamento é redigida por quem implementou **após** o veredito do
auditor. Esta seção é o insumo do auditor: cada item de DoD com status e a prova
executável que o sustenta.

| # | Item de DoD | Status | Evidência executável |
|---|---|---|---|
| 1 | Toda fonte é projeção de `fact_id`; nenhum gerador inventa entidade | **VERDE** — as seis fontes que o gabarito declara são projeção de fato, o motor **recusa** o gerador que inventa, e `evidence build` as escreve em disco com o `MANIFEST.json` | Três camadas. (a) `range-core/evidence/elenco.py` responde as perguntas puras — `elenco_de`, `cobertura_de` (fato sem `projections` fora), `enderecos_no` e, desde o M2 da 2ª auditoria, `hostnames_no`/`hosts_inventados`; `tests/test_evidence_elenco.py` (23, **dirigido por fato e não por seed**, `06` T13) + probes (2). (b) `range-core/evidence/projecao.py` transforma o oráculo em **porta**, e são **duas** formas fechadas — endereço IP e hostname —, com `EntidadeInventada` nomeando a fonte e o valor; `tests/test_evidence_projecao.py` (38) + probes (2), 9 mutantes. (c) `domains/academus/evidence_generators/` — os geradores reais das seis fontes, provados contra o fato em `tests/test_evidence_generators.py` (35) + probes (2), 6 mutantes. **Nenhuma fonte carrega `fact_id`** (`05` §6), e o domínio do link do `.eml` **deriva** do elenco. **E A COBERTURA TAMBÉM É GUARDADA** desde o B1 da 3ª auditoria: `RespostaEntregue` recusa a fonte que projeta, dentro de uma espécie, apenas os fatos que `line_b_cases` cita como caso — o vazamento que nenhum campo revela e o arquivo inteiro entrega. **O LIMITE, DECLARADO:** ator nu escrito à mão, sem virar endereço nem hostname, continua fora do alcance — e a reprojeção do `verify` **não** o pega, porque roda o mesmo gerador. A versão anterior desta linha afirmava que pegava; era falsa por construção (M2) |
| 2 | `range-cli evidence verify` dirigido por fato | **VERDE** | `range-core/evidence/build.py::conferir` **reprojeta em memória** e compara com o disco — não há regra de validação escrita à mão, o oráculo é o próprio produtor rodado de novo. Confere, em ordem de dependência: manifesto presente e válido contra o contrato → `ground_truth_hash` → conjunto de arquivos declarado × projetado → `sha256` por arquivo → conteúdo reprojetado → **`projects_facts` e `format` de cada fonte** → arquivo a mais. Os dois últimos degraus entraram no H2 da 2ª auditoria, e são os que tornam a conferência **dirigida por fato**: o `fact_id` não está nas fontes (`05` §6), então o manifesto é o único lugar onde ele aparece — adulterá-lo não deixava rastro em arquivo nenhum. `range-cli evidence verify <path>` sai `0`/`2` e **não escreve** (`04` §8.1 (a), provado por `st_mtime_ns` antes/depois). `tests/test_evidence_build.py` (38) + probes (2) |
| 3 | `precursor_events.jsonl` reproduzível; edição manual detectada por hash | **VERDE** | `domains/academus/evidence_generators/precursor.py` — o phishing projeta em **duas** fontes (`email` e `precursor`), que é o modelo de `08` §1. O arquivo tem o nome que a spec usa, é reproduzível byte a byte, e a edição manual é detectada. **O precursor omite `actor` de propósito**: atribuição é o achado do exercício, não o insumo |
| 4 | Telemetria CEF é projeção, não emissão independente | **VERDE** | Duas metades, **um produtor só** — e a distinção custou o H1 da 2ª auditoria: a versão anterior tinha dois geradores coerentes, que já nasceram divergentes para o mesmo fato. Hoje `range-core/telemetry/forwarder.py::programar` monta o payload a partir de `domains/academus/telemetry_events.yaml` (`02` §10), e as duas saídas o **renderizam**: `range-core/telemetry/cef.py::linha` escreve o `cef.log`, `range-core/telemetry/emissao.py` grava `telemetry_emitted` no event store. **A prova é de igualdade total, nos dois sentidos**: todo campo do payload aparece na linha com o mesmo valor, e a linha não tem extensão que o payload não tenha. A segunda metade tem emissor de **produto** desde o M4, e o **mesmo conjunto** desde o B2 da 3ª auditoria: `LoadedPack.telemetria` pede a `cobertura_de` exatamente os fatos que o motor entrega ao gerador de CEF, e `InjectEngine.start()` os emite. Fato que projeta em outra fonte, ou em fonte nenhuma, não vira sinal no SIEM; o payload atravessa o envelope pelo mesmo validador de todo produtor, com `fact_id` **inexpressável** (`05` §6). `tests/test_telemetry_forwarder.py` (23) + probes (2) e `tests/test_inject_engine.py` (classe própria, 8 casos) |
| 5 | Nenhum anexo, binário, IOC real ou domínio roteável | **VERDE para as fontes que existem** | Três metades — a terceira entrou no B1 da 2ª auditoria, e é de OUTRA natureza: `credential_state` não é IOC nem dado real, e nenhum verificador de `05` reclamaria dele; ele arruína o exercício por confundir **camada** (`00` §3), e quem o guarda é `VereditoDoGabarito`. (a) **Banner** (`06` T13, critério próprio): `range-core/evidence/banner.py` produz e reconhece o banner na **primeira linha**, por formato de fio, com o texto **lido do contrato**; formato sem forma declarada é recusado. 8 casos, incluindo o negativo de posição (rodapé não conta). (b) **IOC**: `projetar()` levanta `IOCEncontrado` usando `dados_sinteticos` — **o mesmo predicado do CI e do loader**, não um segundo detector (P1-13). O `.eml` tem as três negativas de `05` §2 em casos separados: sem anexo, sem MIME multipart, link em sufixo reservado. **A guarda passava vacuamente na primeira versão** — ver §2.5, e o mutante que restaura o defeito |
| 6 | Replay respeita o clock de exercício | **VERDE** | `range-core/telemetry/forwarder.py::Replay` lê `elapsed_seconds()` — nunca o relógio de parede — e tem as três propriedades com caso próprio: só emite o que venceu em tempo de **exercício**, **nada novo vence durante a pausa** (`01` §3 congela o clock), e **não reemite** (duplicata no event store é sinal para a reconstrução). O forwarder **não sabe pausar**: ele lê o tempo, e quem o move é o gm-console — duas autoridades sobre o mesmo relógio seria o defeito. `tests/test_telemetry_forwarder.py` (23) + probes (3). **As duas marcas de `00` §5.6 estão no evento** desde o H1 da 3ª auditoria — `event_time` do fato e `ingest_time` da gravação, distintas e verificadas. **A integração com o store existe desde o M4 da 2ª auditoria**: o `start` do engine emite a telemetria pré-posicionada, e o `tick` seguinte devolve zero — a propriedade (3) provada contra o event store de verdade, e não contra dublê |
| 7 | Reconstrução < 3 s com `telemetry_emitted` no volume de 4 h | **VERDE**, com 96.650 eventos (96.000 `telemetry_emitted`, 400/min). **O número é o da prova gravada, e esta página não o repete**: a fonte única é `check_prova_do_exercicio_4h.py`, que o imprime e o confere contra a árvore. **A folga é fina e o risco está declarado** — a dispersão observada é da mesma ordem que ela, e a saída para uma gravação futura acima de 3 s é a otimização nomeada, nunca diminuir o volume. Ver §2.8, que perdeu duas redações por afirmar margem que a prova desmentiu | `scripts/medida_do_exercicio_4h.py --telemetria N` estende a composição da Fase 9 **sem tocar a da Fase 7** — as duas medem o mesmo exercício, e é a comparabilidade que torna o "continua" de T13 uma afirmação. A prova é gravada por `prova_do_exercicio_4h.py` e amarrada por hash à árvore e aos sete arquivos do pack; `check_prova_do_exercicio_4h.py` a cobra, com prova negativa própria para o item da Fase 9 (10 venenos, 7 direções). **O volume foi escolhido porque nenhuma execução dele cruzou o orçamento, enquanto 500/min cruzou na terceira — e é só isso que se pode afirmar. Ver §2.8** |

## 6. Pendências

Prefixo `P9-` para as que nascerem aqui. A tabela abaixo começa com o que foi
**herdado**, e o prefixo herdado é preservado: renumerar apagaria a cadeia que
liga a pendência ao registro em que ela nasceu.

As **seções de detalhe** das herdadas são resumo com ponteiro, e não cópia: o
argumento inteiro de cada uma vive no `docs/progress/fase_N.md` de origem.
Repeti-lo aqui criaria duas fontes para o mesmo fato. O que fica aqui é o id, o
estado, e a relevância para ESTA fase.

**`Estado` é o enum fechado da Fase 7**: `ABERTA` · `LATENTE` · `DECIDIDA` ·
`VENCIDA` · `RESOLVIDA` · `ENTREGA`.

<!-- tabela-resumo-de-pendencias -->

| Pendência | Assunto | Estado | Vence em |
|---|---|---|---|
| P9-1 | a migração de pendência só é conferida entre fases com coluna de estado — o gatilho escrito numa tabela de três colunas (fases 0–5) não chega a destino nenhum por máquina | `ABERTA` | esta fase, junto do fechamento — foi ela que expôs o defeito ao resgatar P1-3, P1-13 e P2-11; ver abaixo |
| P1-3 | ~~`evidence.schema.yaml` valida um artefato que ainda não é produzido~~ | `RESOLVIDA` | **venceu na peça 2**: `range-core/evidence/manifesto.py` produz o `MANIFEST.json` e `erros_de_schema` o valida contra o contrato real, com os `$ref` cruzados resolvidos pelo `Registry` do loader. Oito fases depois, o contrato tem consumidor; ver abaixo |
| P1-7 | o id do inject pode vazar a linha; falta o mecanismo que impeça o próximo pack de decidir pelo vazamento | `ABERTA` | a fase que decidir o destino do pack (P7-9) ou o primeiro pack novo; detalhe em `fase_7.md` §"P1-7" |
| P1-13 | ~~duas cópias das faixas sintéticas — o contrato declara as faixas e `check_synthetic_data.py` declara as suas; divergiram duas vezes em silêncio~~ | `RESOLVIDA` | **venceu nesta fase, nas duas metades**: o motor consome `dados_sinteticos` (fonte única do julgamento) e `check_contract_examples.py` passa a cruzar também as **faixas de IP**, que era a metade que faltava; ver abaixo |
| P2-11 | `append` abre uma conexão por chamada | `ABERTA` | **esta fase** — telemetria não grava a ritmo de facilitador; leitura e escrita reabrem juntas, pela mesma causa (volume); detalhe em `fase_2.md` §"P2-11" |
| P4-8 | leitura síncrona no laço de eventos serializa e bloqueia em volume | `DECIDIDA` | **o gatilho disparou e a medição existe** (§2.8): `read_all` é 97% do custo, e o ponto de quebra está em ~135 mil eventos. A decisão de fundo — atacar a reserialização da cadeia — é estrutural e fica para a fase que a couber; ver abaixo |
| P9-2 | o volume de telemetria do item 7 pressupõe **ruído de fundo** do ambiente simulado, e nenhum item de DoD o constrói | `ABERTA` | a fase que construir o produtor do ruído — o tráfego normal em que o time azul acha o sinal; ver abaixo |
| P9-3 | `08` §5 declara **três** modos de entrega e o contrato de cenário sabe expressar **dois**: `evidence_release_item` tem `source` e `window`, e nenhum campo de atraso — `on_request` é inalcançável por um pack | `ABERTA` | a fase que entregar o dashboard de TI de `08` §5 (*"o modo mais realista, e o que melhor exercita OBJ-02"*); ver abaixo |
| P9-4 | `08` §3 dá ao `database_audit.jsonl` duas metades — *"leitura em massa (Linha A) e **alterações de nota com IP e sessão (Linha B)**"* — e só a primeira é projetável: os únicos fatos que a Linha B tem são os **casos**, e projetá-los entrega a resposta (B1 da 3ª auditoria) | `ABERTA` | a fase que der ao motor de evidência uma fonte que projete da **trilha** (business state), e não de `facts`; ver abaixo |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores de `line_b_case.set` | `ABERTA` | o schema v3, quando houver delta real; detalhe em `fase_5.md`/`fase_7.md` §"P5-4" |
| P6-2 | `observable_impact` (start de `TTA`) não existe em contrato | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; detalhe em `fase_6.md` §"P6-2" |
| P6-3 | `before`/`after`/`since` dependem de uma gramática de `exercise_time` que não existe | `ABERTA` | os três gatilhos herdados da Fase 6, intactos; detalhe em `fase_6.md` §"P6-3" |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança | `ABERTA` | a fase que consumir `03` §5.3, candidata a Fase 10 (AAR/calibração); detalhe em `fase_6.md`/`fase_7.md` §"P6-5" |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e não `Bash` | `LATENTE` | a primeira sessão que trabalhe em duas branches simultâneas; detalhe em `fase_6.md` §"P6-6" |
| P6-8 | justificativa ausente devolve `409`, reservado a recusa de estado | `DECIDIDA` | a medição dos consumidores, ou a Fase 10; detalhe em `fase_6.md` §"P6-8" |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção (`sub == persona`) | `ABERTA` | a palavra do proprietário entre as saídas (a) e (b); detalhe em `fase_6.md` §"P6-12" |
| P6-13 | dezesseis violações plantadas da §3.5 da Fase 6 são atestação, não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável; detalhe em `fase_6.md` §"P6-13" |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual linha entrega; detalhe em `fase_7.md` §"P7-1" |
| P7-4 | consumo de `event_type` por selecionador sem allowlist declarada | `ABERTA` | **Fase 12** — degrau 1.5; detalhe em `fase_7.md` §"P7-4" |
| P7-5 | chamadores de cada emissor não varridos quando o contrato do emissor muda | `ABERTA` | **Fase 12** — degrau 2; detalhe em `fase_7.md` §"P7-5" |
| P7-11 | condição temporal de branch (`before`/`after`) carrega e nunca ramifica | `ABERTA` | o gatilho da P6-3 (a gramática temporal nascer); detalhe em `fase_7.md` §"P7-11" |
| P7-12 | a superfície do hook do auditor acumulou cinco achados M/L sem rastro | `ABERTA` | a próxima edição da allowlist do auditor; detalhe em `fase_7.md` §"P7-12" |
| P7-13 | o harness não planta violação onde a correção entrou | `ABERTA` | **Onda 3 da Estrutura Agêntica** (TDD endurecido); detalhe em `fase_7.md` §"P7-13" |
| P7-14 | seis afirmações de registro/teste sem disposição (varredura P7-6) | `ABERTA` | a varredura de fechamento desta fase; detalhe em `fase_7.md` §"P7-14" |
| P8-2 | o banner (`05` §4) na classe `exportacao` não tem fase de destino | `ABERTA` | a fase que construir os artefatos de exportação do academus-web; detalhe em `fase_8.md` §"P8-2" |
| P8-3 | a entrada `pytest` na allowlist do auditor admite comando que nenhum interpretador executa | `ABERTA` | a fase que adotar `pytest`, ou a decisão do proprietário de removê-la; detalhe em `fase_8.md` §"P8-3" |
| P8-4 | cinco das sete superfícies do academus-web (`02` §7) não têm fase de destino | `ABERTA` | a fase que construir o restante do academus-web; detalhe em `fase_8.md` §"P8-4" |
| P8-5 | as três telas da Fase 8 não têm rota que as sirva, e a `participant-api` não tem raiz de composição de produção | `ABERTA` | **redatada na abertura da Fase 9**: o proprietário decidiu no chat (2026-09-18) que ela NÃO entra nesta fase. Novo vencimento: a fase de serving/deploy do web; ver abaixo |
| P8-6 | as sete `action_id` do enum fechado estão copiadas à mão em `persona-panel/tipos.ts` sem gate | `ABERTA` | a Onda 3, ou a geração de constantes TS a partir do contrato; detalhe em `fase_8.md` §"P8-6" |
| P8-7 | o cronômetro do Modo Prova em andamento recebe `exercise_minute` do chamador e não acompanha o relógio de exercício | `ABERTA` | a fase que ligar `ProvaEmAndamento` ao relógio autoritativo — **o item 6 desta DoD (replay respeita o clock) é candidato direto**; detalhe em `fase_8.md` §"P8-7" |

#### P9-1 — a migração de pendência é cega às fases de tabela antiga

**Nasce com a fase.** `check_progress_consistency.py` confere o par de pauta
fase N → N+1 apenas quando a tabela-resumo da fase N declara **coluna de
estado**. As fases 0 a 5 têm tabela de três colunas, anteriores ao vocabulário
fechado da Fase 7, e o verificador as pula — declaradamente, imprimindo o motivo.

A cegueira não é defeito do verificador: sem estado não há como dizer o que
deveria migrar, e inventá-lo seria escrever história por inferência. O defeito é
a **consequência não registrada**: gatilho escrito numa dessas tabelas —
*"resolve na Fase 9"* — não tem quem o cobre, e a pendência só chega ao destino
se um humano a reencontrar. Foi o que aconteceu nesta abertura com P1-3, P1-13 e
P2-11: as três nomeiam esta fase, e nenhuma constava da tabela da Fase 8.

**Vence em:** esta fase, junto do fechamento. A saída provável é uma varredura
de gatilho por texto — *"toda linha de qualquer registro que nomeie uma fase
como vencimento aparece na tabela-resumo daquela fase"* —, que alcança as
tabelas antigas sem exigir que elas ganhem coluna de estado retroativa. A forma
exata é decisão do fechamento, e a pendência existe para que a varredura não
dependa de alguém lembrar.

#### P1-3 — o contrato do manifesto valida artefato ainda não produzido — RESOLVIDA

Herdada da Fase 1, resgatada nesta abertura (ver §2.2). `evidence.schema.yaml`
valida o `MANIFEST.json` de `08` §7, e o contrato existia desde a Fase 1 porque
a DoD daquela fase o exigia — sem nunca validar nada. O próprio arquivo o diz:
*"quem consome, hoje: o evidence-simulator da Fase 9, que ainda não existe"*.

**RESOLVIDA na peça 2.** `range-core/evidence/manifesto.py::montar` produz o
documento e `erros_de_schema` o valida contra aquele schema, com os `$ref`
resolvidos pelo mesmo `Registry` que o loader de pack usa. A validação é real e
está provada nas duas direções: o manifesto correto passa, e um com quatro
defeitos (formato fora do enum v1, hash curto, `sha256` inválido, `fact_id` fora
da forma) é recusado **com o caminho** de cada um. O par negativo não é adorno —
um validador que nunca recusa também devolve lista vazia.

Um caso é dedicado ao **`$ref` cruzado** (`projects_facts.items` →
`ground_truth.schema.json#/$defs/fact_id_pattern`), porque resolver aquilo exige
o `Registry` montado com os dois contratos: sem ele, um validador mal montado
ignoraria a cláusula em silêncio e os outros três defeitos manteriam o teste
verde.

Detalhe de origem em `fase_1.md` §"P1-3".

#### P1-7 — id de inject pode vazar a linha

Herdada da Fase 1, carregada pelas 7 e 8. O pack de 4 h decidiu por ids neutros
`IN*`; falta o mecanismo que impeça o próximo pack de escolher o vazamento.
Detalhe em `fase_7.md` §"P1-7".

#### P1-13 — duas cópias das faixas sintéticas — RESOLVIDA

Herdada da Fase 1 (M2 da 2ª rodada de auditoria), resgatada nesta abertura.
`contracts/evidence.schema.yaml` declara as faixas de IP, os sufixos de domínio
e o vendor/product em `x-aurora-security-constraints`; `dados_sinteticos`
declara os seus em constantes próprias. As duas listas já divergiram **duas
vezes** em silêncio.

**A causa era esta fase**: o gerador seguiria o contrato e o CI julgaria pela
constante. Enquanto ninguém gerava evidência, a duplicação era inerte.

**RESOLVIDA nas duas metades, e a segunda só fechou depois da auditoria (M4).**

1. **O julgamento tem fonte única.** O motor de projeção consome
   `dados_sinteticos` — o mesmo predicado do CI e do loader de pack —, com
   entrada própria na whitelist de imports do core. Não há segundo detector.
2. **As duas listas são cruzadas por máquina.** `check_contract_examples.py`
   já cruzava os sufixos de domínio desde a Fase 1; passa a cruzar também as
   **faixas de IP**, que era a metade aberta — o auditor mediu que sete faixas
   do contrato não eram conferidas contra nenhuma.

**O cruzamento de IP não é de conjunto, e a razão é substantiva.** As três
faixas privadas do contrato (RFC 1918) não aparecem em
`DOCUMENTATION_NETWORKS` porque `ip_permitido` as aceita por
`address.is_private`, que é **predicado e não lista**. Comparar conjuntos
exigiria duplicar a RFC 1918 numa das pontas — a cópia que a P1-13 existe para
não multiplicar. O que se cruza é o **veredito**: toda faixa declarada tem de
ser aceita pelo predicado, e um endereço roteável tem de ser recusado (a
anti-vacuidade, sem a qual um `ip_permitido` que aceitasse tudo passaria).

Detalhe de origem em `fase_1.md` §"P1-13".

#### P2-11 — `append` abre uma conexão por chamada

Herdada da Fase 2, resgatada nesta abertura. `PostgresEventStore._persist` faz
`psycopg.connect` a cada evento; a Fase 2 gravava a ritmo de facilitador, e por
isso não mordia. **Telemetria não grava a ritmo de facilitador** — é a única
fonte com ordem de grandeza diferente (`07` §Fase 9), e é o insumo do item 7
desta DoD. Leitura (P4-8) e escrita (esta) reabrem juntas, pela mesma causa.
A saída provável é conexão reusada ou pool, **medindo antes de escolher**.
Detalhe em `fase_2.md` §"P2-11".

> **O M4 da 2ª auditoria pôs o gatilho ao alcance, e não o disparou.** O
> `InjectEngine.start()` agora emite a telemetria pré-posicionada **um evento
> por vez**, por `append` — exatamente o padrão que esta pendência nomeia.
>
> Com três eventos no `ransomware-universidade`, isso é irrelevante. Com o
> produtor de ruído de fundo da P9-2, são três conexões por evento de ambiente,
> todas no start. **As duas pendências passam a ter o mesmo gatilho**, e quem
> abrir a P9-2 herda esta junto — dito aqui para que a segunda não seja
> descoberta durante a primeira.
>
> Continua `ABERTA` e **não exercitada**: a carga do harness do item 7 é em
> lote, porque o que o critério mede é reconstrução. Esta fase não pode alegar
> tê-la fechado nem tê-la medido.

#### P4-8 — leitura síncrona no laço de eventos — DECIDIDA

Herdada da Fase 4, com gatilho declarado em "medição de volume". **O gatilho
disparou nesta fase e a medição existe** — §2.8 traz a curva inteira, a
decomposição de custo e o ponto de quebra.

O número: com 200.570 eventos, `read_all` é **97% do custo total** (3,698 s de
3,812 s), e dentro dele o ciclo **desserializar → reserializar** domina — o
`payload` vem do banco como JSON, vira `dict`, e `canonical_form` o transforma
em JSON canônico outra vez para conferir o hash.

**Duas saídas foram examinadas e uma foi medida e descartada.** `::text` +
`json.loads` é mais barato isoladamente (0,929 s contra 1,192 s) e **não
entregou ganho no caminho real**: a variância entre execuções é maior. Revertida,
com o registro em comentário no `postgres_store.py`.

**O que fica DECIDIDO:** a saída com ganho suficiente é atacar a reserialização
da cadeia (teto ~1,0 s), e ela é mudança **estrutural** no event store —
superfície de `05` §7, onde a verificação incondicional é garantia e não
otimização pendente. Fora do escopo desta fase, e o vencimento é a fase que
couber esse trabalho. O que NÃO é saída está escrito na §2.8: tornar a
verificação de cadeia opcional.

Detalhe de origem em `fase_4.md`/`fase_7.md` §"P4-8".

#### P9-2 — o volume do item 7 pressupõe ruído que ninguém produz

**Nasce na peça 6.** O item 7 mede a reconstrução com 96 mil `telemetry_emitted`
em 4 h. Mas **a telemetria que o range projeta hoje sai dos fatos do gabarito** —
e são dezenas, não dezenas de milhares.

Chegar ao volume que `07` §Fase 9 nomeia (*"pode chegar às centenas de milhares
sozinha"*) pressupõe **ruído de fundo** do ambiente simulado: o tráfego normal
em que o time azul tem de achar o sinal. `08` §2 põe o limite de detecção no
gabarito, e `02` §10 declara doze espécies de evento — sete delas sem nenhum
`fact_class` que as dispare no `ransomware-universidade`, justamente porque são
o ambiente e não o incidente.

**Isso não é falha do item 7**, e a distinção importa: `06` T13 é critério de
**desempenho** — ele cobra que o motor aguente o volume, não que exista quem o
produza. A medição usa um fluxo sintético declarado, como o bench da Fase 2.

**Vence em:** a fase que construir o produtor do ruído de fundo. Até lá, o
exercício real tem telemetria na ordem de dezenas, e o time azul não tem em que
procurar — o que torna esta pendência material para a qualidade do exercício,
ainda que não para a DoD desta fase.

> **O M4 da 2ª auditoria mudou a natureza desta pendência, e para pior.** Até
> ele, o range não emitia `telemetry_emitted` nenhum: a lacuna entre "o que a
> medição supõe" e "o que o exercício produz" era total, e por isso abstrata.
>
> Agora o exercício **emite de verdade** — e emite exatamente o que esta
> pendência prevê: um evento por fato de gabarito que o catálogo mapeie. No
> `ransomware-universidade` isso são **três**. O número deixou de ser hipótese.
>
> A pendência segue `ABERTA` e com o mesmo dono. O que ela ganhou foi uma
> medida: a distância entre 3 e 96.000.

#### P9-3 — `on_request` é declarado pela spec e inexpressável por um pack

**Nasce na correção do M3 da 2ª auditoria.** O `evidence build` passou a ler
`evidence_release` dos injects e a marcar as fontes liberadas como
`released_by_inject`. Ao escrever isso, o terceiro modo ficou visível pela
ausência.

`08` §5 declara três: **pré-posicionado**, **liberado por inject** e **sob
requisição** — este último com *"atraso configurável simula dependência de
fornecedor"*, e a spec o chama de *"o modo mais realista e o que melhor exercita
OBJ-02"*. `contracts/evidence.schema.yaml` conhece os três no enum
`delivery_mode`, e `manifesto.montar` já aceita `atrasos` como parâmetro.

**O que falta é o lado do pack.** `$defs/evidence_release_item` tem `source` e
`window`, e nada mais: não há onde um autor de cenário escreva o atraso. Então
`on_request` é um valor que o manifesto pode carregar e que **nenhum pack pode
produzir** — o parâmetro existe e nunca chega ninguém por ele.

**Não é defeito desta fase**, e a distinção é a mesma da P9-2: o item 2 da DoD
cobra que o `verify` seja dirigido por fato, não que os três modos tenham
autoria. Mas é exatamente a forma de um requisito morrer em silêncio — o enum
fica completo, o código fica pronto, e o modo nunca é usado porque ninguém
percebe que não dá.

**Vence em:** a fase que entregar o dashboard de TI por onde o participante
solicita a fonte. Mudar `evidence_release_item` é mudança de contrato de
cenário, e entra com o consumidor — antes dele seria campo declarado sem quem o
leia, que é a P1-3 outra vez.

#### P9-4 — a metade Linha B de `08` §3 não é projetável de `facts`

**Nasce no B1 da 3ª auditoria da Fase 9, e ela é a pendência que o próprio
achado cria.**

`08` §3 diz que o `database_audit.jsonl` carrega *"leitura em massa (Linha A) e
alterações de nota com IP e sessão (Linha B)"*. A primeira metade é projeção de
um fato (`GT-A-031`, a exfiltração) e funciona. A segunda não tem como sair de
`facts`, e a razão é estrutural:

- o gabarito só cria fato para os **três conjuntos de caso** — 67 linhas;
- os outros três conjuntos são **3.078 linhas** de trilha: `ruido_de_manutencao`,
  `credenciais_compartilhadas` e `legitimos_normais`;
- projetar só os casos entrega a resposta (foi o B1);
- declarar as 3.145 como fato faria o `ground_truth.yaml` virar cópia da tabela
  de auditoria — e `01` §2 separa business state de overlay de incidente.

**O que falta é uma fonte que projete da TRILHA**, e o motor de evidência
deliberadamente não a alcança: o contrato do gerador é `gerar(fatos) -> str`, e
as três ausências (não recebe ground truth, não recebe elenco, não escreve
arquivo) são o desenho do insumo tipado de `00` §3.2. Dar business state a um
gerador desfaria isso.

**A linha B não fica sem evidência enquanto isso.** A trilha existe no banco e é
alcançável pelo console de investigação; o que não existe é o **arquivo**
pré-posicionado que `08` §3 nomeia. A distinção importa para o facilitador que
monta a sala, e é por isso que a pendência é material e não cosmética.

**Vence em:** a fase que decidir como uma fonte de evidência lê business state —
provavelmente a mesma que fechar a P9-2, porque o ruído de fundo tem a mesma
natureza: volume que não é gabarito.

#### P5-4 — os seis conjuntos não cabem nos três valores de `set`

Herdada da Fase 5, mal formulada na origem. Detalhe em `fase_7.md` §"P5-4".

#### P6-2 — `observable_impact`, o start de `TTA`

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-2".

#### P6-3 — a gramática temporal de `exercise_time`

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-3". A P7-11 depende desta.

#### P6-5 — `review_scope` com a lista de `case_id`

Herdada da Fase 6. Detalhe em `fase_6.md`/`fase_7.md` §"P6-5". Candidata à
Fase 10.

#### P6-6 — o sentinela não intercepta `Bash`

Herdada da Fase 6, `LATENTE`. Detalhe em `fase_6.md` §"P6-6".

#### P6-8 — `409` para justificativa ausente

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-8".

#### P6-12 — a condição (4) da contrassinatura em produção

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-12". A saída é do proprietário.

#### P6-13 — as dezesseis violações plantadas como atestação

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-13".

#### P7-1 — a rota de submissão não valida o payload

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-1".

#### P7-4 — consumo de `event_type` por selecionador sem allowlist

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-4".

#### P7-5 — chamadores de emissor não varridos

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-5".

#### P7-11 — condição temporal de branch nunca ramifica

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-11". Depende da P6-3.

#### P7-12 — a superfície do hook do auditor

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-12". Vence na próxima edição da
allowlist do auditor; o resíduo específico é a P8-3.

#### P7-13 — o harness não planta onde a correção entrou

Herdada da Fase 7, gatilho **Onda 3**. Detalhe em `fase_7.md` §"P7-13".

#### P7-14 — seis afirmações sem disposição

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-14". A varredura de fechamento
desta fase dá disposição a cada uma.

#### P8-2 — o banner na classe `exportacao` sem fase de destino

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-2". **Não vence aqui**, e a
distinção importa: a classe `evidencia` do mesmo gate — banner na primeira linha
de todo arquivo de evidência — **é** desta fase (`05` §4, `06` T13), e
`check_banner_de_simulacao.py` já a defere nominalmente para cá. A classe
`exportacao` é artefato do academus-web, que nenhum item desta DoD constrói.

#### P8-3 — a entrada `pytest` da allowlist admite comando inexistente

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-3". A suíte do projeto é
`unittest`.

#### P8-4 — cinco superfícies do academus-web sem fase de destino

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-4".

#### P8-5 — as telas sem rota, e a `participant-api` sem processo

Herdada da Fase 8, e a única herdada cujo destino **era decisão de abertura desta
fase**: o registro da Fase 8 a marca como *"candidata à Fase 9 ou a uma fase de
deploy"*. `07` §Fase 9 não tem item de serving — os sete itens são evidência,
telemetria e desempenho —, então trazê-la para cá seria ampliar o escopo da fase
por decisão do proprietário, e não cumprir a DoD.

**DECIDIDA pelo proprietário na abertura (2026-09-18): NÃO entra na Fase 9.**
Fica para a fase de serving/deploy do web. O desenho continua pronto e válido em
`fase_8_plan_serving.md` (T822–T831: co-locar cada casca com sua data-API;
factory em `domains/academus/api/participante_processo.py`; serviço no compose),
e a pendência segue `ABERTA` com esse destino. Detalhe de origem em `fase_8.md`
§"P8-5".

#### P8-6 — o enum das sete ações copiado à mão no cliente

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-6".

#### P8-7 — o cronômetro da prova não acompanha o relógio de exercício

Herdada da Fase 8, e material aqui: o **item 6 desta DoD** — *"replay respeita o
clock de exercício"* — é a exigência de que o tempo venha do relógio
autoritativo e não de parâmetro do chamador. É o mesmo princípio, e o
`ProvaEmAndamento` é o caso já medido dele. Detalhe em `fase_8.md` §"P8-7".

## 7. Fechamento

> A redigir por quem implementou, **após** o veredito do `checkpoint-auditor`,
> como manda o rito.
