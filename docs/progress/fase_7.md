# Fase 7 — Pack completo, branching e `range-cli`

**Status: EM ANDAMENTO** — peça 1 aberta em `422a105`. A
linha de status está aqui porque `check_readme_atual.py` decide *"a fase
fechou?"* por ela, e registro de fase **sem** linha de status reprova o
verificador em vez de degradar para "ok" — é a guarda `_status_da_proxima`, que
existe para que uma terceira forma de rótulo não faça fonte e documento
concordarem sobre um fato falso.

**Por que este registro nasceu antes da fase.** Uma pendência migrou para cá no
fechamento da Fase 6, e pendência sem lugar é pendência que ninguém encontra.
Registrá-la no `fase_6.md` e só ali seria pior: aquele registro fecha auditado, e
quem abrir a Fase 7 não tem por que ler o inventário da anterior para descobrir o
que herdou. É a mesma razão pela qual o `fase_6.md` nasceu antes da Fase 6, e
está escrita lá.

> **A linha de status acima é entrada de verificador mantida à mão**, e ela
> envelheceu três vezes no registro da Fase 6 — `NÃO INICIADA` sobrevivendo a
> cinco peças, `EM ANDAMENTO` sobrevivendo a sete peças e dez auditorias. A
> observação está registrada como candidata a mecanismo no `fase_6.md`, §1. Quem
> começar esta fase deve atualizar esta linha **na peça 1**, e não no fechamento.

## 1. Plano da fase — sete peças

Os nove critérios DONE de `07_IMPLEMENTATION_PHASES.md` §"Fase 7" se agrupam em
quatro blocos de entrega. Somam-se três mecanismos: dois decididos na §7 desta
fase e um que nasceu da quinta ocorrência da classe que a §7.1 mede.

| Peça | O que entrega | Origem |
|---|---|---|
| 1 | verificador de transcrição de pauta entre registros de fase | quinta ocorrência da classe da §7.1, medida no rebase que abriu esta fase |
| 2 | pack: schema v1 migra automaticamente, v0 recusado com instrução; fato do `GM_NOTES.md` ausente do `ground_truth.yaml` recusado | DONE 7 e 8 |
| 3 | gramática de `exercise_time` | P6-3, pré-condição desta peça — o gatilho declarado é o primeiro pack que precise |
| 4 | `range-cli scenario lint`: inject sem objetivo e sem `noise: true`, `event_type` inexistente em condição com posição no arquivo, condição por juízo do facilitador | DONE 1, 2 e 3 |
| 5 | branching: `branch_policy` do manifesto aplicada, branch sem `reconverge_at` recusado, `dryrun` percorre todos os caminhos | DONE 4, 5 e 6 |
| 6 | as duas allowlists, com esqueleto comum | P7-4 e P7-5 |
| 7 | volume: reconstrução completa da projeção do `ransomware-universidade` de 4 h em < 3 s | DONE 9 |

**A peça 1 vem primeiro porque é degrau 1** na taxonomia da §7.1 — a exigência
deixa de ser afirmada em cada registro de fase e passa a ser derivada deles. É o
único degrau que faz a classe deixar de existir em vez de ficar visível.

**A peça 7 depende da P7-3.** O critério dos 3 s é prova de desempenho, e prova
de desempenho depende do pack materializado — que é exatamente o que a árvore não
cobre. A P7-3 vence na implementação da saída (b) da P7-2, e essa implementação é
conserto pontual contra `main`, fora desta branch.

**A CLI não é peça própria.** Ela é a superfície das peças 2, 4 e 5: o primeiro
critério DONE já a nomeia (`range-cli scenario lint`), e o resto se expõe por ela.

**O verde de `check_progress_consistency.py` é condição de fechamento.** Ele
reprova hoje por P7-4 e P7-5, cujas seções são o desenho das duas allowlists e
nascem na peça 6. Até lá o vermelho é esperado e tem causa nomeada — gate que fica
vermelho por motivo conhecido a fase inteira é gate que se aprende a ignorar, e é
assim que ele deixa de pegar o dia em que ficar vermelho por outro motivo.

## 6. Pendências

Prefixo `P7-` para as que nascerem aqui. A tabela abaixo começa com o que foi
**herdado**, e o prefixo herdado é preservado de propósito: renumerar apagaria a
cadeia que liga a pendência ao registro em que ela nasceu.

O corpo herdado desta tabela foi escrito no **encerramento da Fase 6**, depois do
merge do PR #53 — e por isso ele chega aqui como resumo com ponteiro, e não como
cópia. O argumento inteiro de cada item está no `docs/progress/fase_6.md`, que
fechou **AUDITADA**; repeti-lo aqui criaria duas fontes para o mesmo fato, que é
a §1.6 que aquele registro passou a fase inteira nomeando.

**`Estado` é enum FECHADO a partir desta fase**, com estes seis valores e nenhum
outro. Registros anteriores à Fase 7 ficam fora do escopo, como o
`phase_anchors.tsv` já fez com as Fases 0 a 2 — reescrever registro fechado para
caber em vocabulário novo é o que a §1.6 mede.

| Valor | O que afirma |
|---|---|
| `ABERTA` | o gatilho não chegou |
| `LATENTE` | o gatilho chegou e o defeito **não** apareceu |
| `DECIDIDA` | a decisão foi tomada, a implementação está pendente |
| `VENCIDA` | o gatilho chegou **e** o defeito apareceu |
| `RESOLVIDA` | fechada, com o conserto no repositório |
| `ENTREGA` | é trabalho desta fase, e não pendência a carregar |

**Por que estado e gatilho deixam de dividir célula.** Até aqui a coluna
`Vence em` carregava os dois — *"**condição** — a primeira ação de participante
que…"* —, e qualquer verificador que quisesse perguntar *"quantas pendências
seguem abertas?"* teria de **parsear prosa**. Prosa parseada é mecanismo que erra
em silêncio: ele não recusa quando não entende, ele classifica errado e segue
verde. Separadas, a pergunta de estado é uma comparação de string contra seis
valores, e a de gatilho continua sendo texto para humano — que é o que ela é.

**O `LATENTE` nasceu de um caso real, e não da simetria do enum.** A primeira
redação tinha cinco valores, e a P6-6 não coube em nenhum: o gatilho dela chegou
no trabalho da P7-2 e o defeito não apareceu. Forçá-la a `ABERTA` apagaria a
informação de que o gatilho já passou uma vez sem custo — que é evidência sobre a
forma 3 daquela pendência, e o único dado empírico que ela tem.

<!-- tabela-resumo-de-pendencias -->

| Id | O que é | Estado | Vence em |
|---|---|---|---|
| P5-2 | a trilha do Academus declara a categoria "declarações do exercício" e ela não tem produtor | `ABERTA` | a primeira ação de participante que altere estado de domínio; ver abaixo |
| P6-2 | `observable_impact` não existe em contrato nenhum, e é o *start* de `TTA` — herdada da Fase 6, §"P6-2" | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; ver abaixo |
| P6-3 | `before`, `after` e a comparação de `since` dependem de uma gramática de `exercise_time` que não existe — herdada da Fase 6, §"P6-3" | `ENTREGA` | peça 3 desta fase. Três gatilhos herdados: o primeiro pack que precise, a implementação do suporte temporal, e o primeiro produtor de `fact_materialized`, que bate em `SemGramaticaTemporal` por desenho deliberado; ver abaixo |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança, resolvida no fechamento do escore | `ENTREGA` | mudança de contrato agendada para esta fase; ver abaixo |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e **não** `Bash` — herdada da Fase 6, §"P6-6" | `LATENTE` | a primeira sessão que trabalhe em duas branches, ou a Fase 8, o que vier primeiro — o literal ocorreu no trabalho da P7-2 sem que o defeito aparecesse; ver abaixo |
| P6-7 | rota que declara `emite` e não chama emissor nenhum — a metade do fluxo continua aberta; herdada da Fase 6, §"P6-7" | `ABERTA` | a próxima rota que declare `emite` em serviço cuja fábrica já constrói o produtor, ou a Fase 8, o que vier primeiro; ver abaixo |
| P6-8 | justificativa ausente devolve `409`, e `409` é reservado a recusa de estado — herdada da Fase 6, §"P6-8" | `DECIDIDA` | a medição dos consumidores, ou a Fase 10, o que vier primeiro; ver abaixo |
| P6-9 | a cópia instalada do hook do auditor não é sincronizada por ninguém — herdada da Fase 6, §"P6-9" | `VENCIDA` | qualquer edição da fonte do hook — ocorreu três vezes, a última no PR #56; ver abaixo |
| P6-11 | payload cru alimenta o Brier: `confidence: 900` produz escore 64,0 | `RESOLVIDA` | venceu na L1 da terceira auditoria da Fase 6; conserto no PR #54; ver abaixo |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção: `sub == persona`, e `actor_id` vira função da persona | `ABERTA` | a palavra do proprietário entre as saídas (a) e (b); ver abaixo |
| P6-13 | dezesseis violações plantadas declaradas na §3.5 da Fase 6 são atestação do autor, e não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável, ou a primeira vez que alguém precise da cobertura que a tabela declara; ver abaixo |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual das três linhas esta fase entrega; ver abaixo |
| P7-2 | todo fechamento de fase por rebase-merge invalida as provas amarradas ao SHA — é estrutural do rito | `RESOLVIDA` | implementada no PR #56, pela saída (b): a prova nomeia a árvore; ver abaixo |
| P7-3 | a prova amarrada à árvore não cobre o pack materializado, que está no `.gitignore` desde a Fase 5 | `ABERTA` | a peça 7 desta fase — o critério dos 3 s exige o pack materializado. A janela barata era a implementação da saída (b), e passou no PR #56; ver abaixo |
| P7-4 | todo consumo de `event_type` por selecionador sem allowlist declarada — a mesma pergunta com duas respostas | `ENTREGA` | peça 6 desta fase — allowlist por tipo, degrau 1.5; ver §7.2 |
| P7-5 | os chamadores de cada emissor não são varridos quando o contrato do emissor muda | `ENTREGA` | peça 6 desta fase — allowlist de chamadores por emissor, degrau 2; ver §7.1 |

#### P5-2 — a categoria de trilha sem produtor, migrada da Fase 6 com gatilho corrigido

**Nasceu na Fase 5** (`docs/progress/fase_5.md`, §8), na peça que criou a trilha
`audit_trail`. `02` §4.1 lista **cinco** categorias que a trilha registra:
alteração de nota, emissão de diploma, banco de questões, pesquisa acadêmica e
**declarações do exercício — todas as ações de `declare_*`** (`03` §3.1). A peça
2 daquela fase criou `diplomas`, `exam_questions` e `research_projects`
justamente para que as quatro primeiras não nascessem sem sujeito. A quinta não
podia ganhar objeto ali: as ações `declare_*` são eventos `declaration` do
catálogo (`09` §4.1), e `01` §4 as põe no event store com reversibilidade
"nunca".

**Destinatário original: Fase 6. Gatilho original: o commit em que a primeira
ação `declare_*` nascer.**

**O gatilho disparou na Fase 6 e não venceu a pendência**, porque a suposição
embaixo dele estava errada. As nove ações nasceram (peça 3, bloco B), e
`DECLARACAO_DE_EXERCICIO` continua sem produtor — o gatilho assumia que a
declaração passaria pela **trilha do adapter**, e a peça 3 decidiu o contrário,
com três razões registradas e um verificador que as impõe: declaração é ato de
participante, mora no núcleo com RBAC por persona (`01` §6), e `audit_trail` é
mecanismo de **domínio**, sobre as entidades do Academus. As nove declaram no
event store, que é outro caminho.

**Por que não foi fechada.** A categoria continua declarada em `02` §4.1 e
continua sem produtor. Uma constante que nada escreve é *"o `event_type` que
nunca dispara"*, que `09` §4 chama de a falha mais cara possível: ninguém
descobre que ela não funciona porque ninguém a exercita. Fechar por "a fase
destinatária passou" apagaria a pergunta em vez de respondê-la.

**Por que o gatilho antigo não podia ficar.** Gatilho que já disparou e não
venceu é pior que ausência de gatilho: ele treina a próxima leitura a ignorá-lo.

**GATILHO NOVO: a primeira ação de participante que altere estado de domínio** —
aí a trilha do Academus tem o que registrar, e a categoria ganha o sujeito que
lhe falta. É a Fase 7 quem traz o pack completo `ransomware-universidade`, que é
de onde essas ações vêm.

**O que o gatilho novo corrige, dito com precisão.** O antigo perguntava *"a ação
nasceu?"*; o novo pergunta *"a ação toca a coisa que a trilha vigia?"*. A
condição que faltava não era temporal — era de **objeto**.

**A alternativa que NÃO se deve escolher**, e ela é a mesma que a Fase 5 já
recusou uma vez: omitir a categoria e acrescentá-la quando houver produtor. Isso
trocaria uma promessa declarada por uma lacuna silenciosa — a trilha passaria a
ter quatro categorias e nada diria que a quinta é da spec.

**Estado do código:** `domains/academus/audit/trilha.py` mantém
`DECLARACAO_DE_EXERCICIO` em `CATEGORIAS`, com o comentário apontando para esta
pendência e para este gatilho. O comentário anterior dizia *"nada a escreve até a
Fase 6"* e foi corrigido no commit de fechamento da Fase 6 — ele era a §1.6
inscrita no código: uma afirmação verdadeira quando nasceu, falsa quando outra
decisão a contradisse, e que nenhum verificador alcança porque é prosa em
comentário.

#### P6-2 — o *start* de `TTA` sem origem em contrato, e o ramo (b) já decidido

**Herdada já DECIDIDA** (`docs/progress/fase_6.md`, §"P6-2"). `03` §3 define o
*start* de `TTA` como *"primeiro inject com impacto observável"*, e `00` §3.2
exige que a escolha entre injects seja **cálculo do consumidor** sobre atributos
que viajam no payload de `inject_fired` — nunca recorte do montador do insumo. O
atributo não existia: nem no schema de cenário, nem no de eventos, e
`inject_fired` não emitia payload nenhum. Sem origem, `TTA` não é computável, e a
norma fica apontando para mecanismo inexistente.

**Decisão: ramo (b) — derivação pelo motor**, com o predicado virando norma pelo
`spec-change` `impacto-observavel-definido`, que define impacto observável em `03`
§3. O ramo (a) — campo `observable_impact` declarado pelo autor do cenário — foi
recusado por mexer no schema de **pack**, que tem regime de versão próprio.

**O predicado ditado não sobreviveu à verificação, e isso está preservado na
fonte:** a primeira redação exigia `effects` produzindo evento de
`truth_layer: observable_evidence`, e `effects` **não emite evento nenhum**. O
aprovado tem três pernas — `effects`, `materializes_facts` com fato que tenha
`projections`, e `evidence_release` — e a exclusão decidida recai sobre `reveals`,
que alimenta crença do participante e não o mundo.

**Por que não fechou na Fase 6.** O payload de `inject_fired`, o emissor e o teste
de emissão nasceram lá, que é o que cabia num PR de código. O que falta é o outro
lado: nada consome `TTA` ainda.

**Vence em:** o commit em que o consumidor de `TTA` for desenhado — é ele que
força a escolha, e antes dele ela seria tomada sem o caso de uso à vista.

#### P6-3 — a gramática de `exercise_time`, e as três folhas que dependem dela

**Herdada como `condição`** (`docs/progress/fase_6.md`, §"P6-3") **e promovida a
pré-condição da peça 3 nesta fase**, por decisão do proprietário. As duas coisas
convivem e nenhuma substitui a outra: a Fase 6 declarou os gatilhos; esta fase
declarou que o primeiro deles dispara aqui.

`contracts/ground_truth.schema.yaml` admite `predicate_before` e
`predicate_after`, e o avaliador **não os implementa** — eles comparam contra o
relógio de exercício, que não é parte do mundo que ele monta. `since` entrou na
mesma pendência, e não abriu uma própria: as três folhas comparam contra o mesmo
campo, e duas gramáticas para `exercise_time` divergiriam em predicado que
verifica num caminho e não no outro.

**O que a Fase 6 implementou, e por isso a ausência é contida e não silenciosa:**
o instante de referência derivado da linhagem corrente; `confere_folhas_temporais`
recusando o pack **na carga**, nomeando folha e motivo enquanto ainda dá para
consertar; e a segunda linha no avaliador, que levanta `SemGramaticaTemporal` em
vez de responder — as duas respostas plausíveis são piores, porque falso faz a
contenção nunca verificar e verdadeiro a faz verificar com vazamento em curso.

**Por que não fechou.** Falta a gramática, e o adiamento é legítimo por medição e
não por conveniência: **não existe produtor de `fact_materialized`**, então
`Mundo.fatos` é vazio em produção e nenhum comportamento de hoje depende da
escolha. O que se adia é a comparação, não a semântica — essa está em `03` §3.1
desde o `spec-change` #49.

**O que a decisão precisa escolher:** contra o que o predicado temporal compara —
`exercise_time`, `exercise_timestamp` ou marca de parede. As três dão resultados
diferentes depois de um rollback, e por isso é escolha normativa e não improviso
de implementação.

**Vence em:** três gatilhos, e o primeiro dispara nesta fase — o primeiro pack que
precise de folha temporal, a implementação do suporte temporal, ou o primeiro
produtor de `fact_materialized`, que baterá em `SemGramaticaTemporal` na primeira
execução. É deliberado que bata: a decisão precisa acontecer ali.

#### P6-5 — `review_scope` carrega a lista, e é entrega desta fase

**Herdada já DECIDIDA** (`docs/progress/fase_6.md`, §6). Não é pergunta aberta: é
trabalho agendado. `03` §5.1 manda a equipe declarar escopo revisado — *"período,
população, critério"* —, e §5.3 usa a declaração para separar **erro de
julgamento** de **lacuna de cobertura**. O escore precisa, para isso, do conjunto
de `case_id` dentro do escopo, e ele não é derivável do gabarito:
`line_b_case` não tem atributo de data nem de população.

**Decisão do operador, na peça 7 da Fase 6 — opção 3 de três:** `review_scope`
passa a carregar a lista de `case_id`, resolvida no **fechamento** do escore.
As duas rejeitadas, com o custo preservado no registro da Fase 6: a
`academus-api` resolveria com o conjunto atravessando do adapter para o núcleo
**por dado**, que é a travessia que o invariante 1 não vê; o gerador do seed
resolveria na geração, e escopo declarado em runtime não tem como ser resolvido
por quem já terminou de rodar.

**Por que caiu aqui:** é mudança de contrato, e por isso não coube na Fase 6.

**O que já está pronto para ela.** `escopo_revisado` é escalar do
`InsumoDeVerificacao`, declarado em `CAMPOS_DECLARADOS` de
`check_insumo_de_metrica.py`, e `escore()` já o recebe como dado. Esta fase muda
**de onde ele vem** — não a forma como chega ao consumidor, que `00` §3.2 fixou.

#### P6-6 — o sentinela de branch não enxerga escrita por `Bash`

**Herdada como `condição` não decidida** (`docs/progress/fase_6.md`, §"P6-6"). A
D15 existe para pegar a corrida em que a branch muda no meio da sessão e o
trabalho pensado sobre uma árvore é gravado noutra. Ela funciona pelos canais que
intercepta — o hook é declarado com o matcher `Edit|Write|NotebookEdit`, e `Bash`
**não está nele**. Não é que o sentinela avalie e libere: ele **nunca é invocado**
para escrita feita por `Bash`. O mesmo vale para o hook de invariantes do projeto,
declarado com `Edit|Write`. É achado de **configuração**, verificável na linha do
`settings.json`, e não de simulação.

**O custo, medido no que dava para medir:** na sessão de fechamento da Fase 6,
**não menos que 25** chamadas de `Bash` escreveram em arquivo rastreado. O número
exato **não é reconstruível da árvore**, e essa é a parte afiada do achado — o
canal não deixa rastro que o repositório saiba auditar, e os dois canais
interceptados deixam.

**Por que não foi corrigido.** Alargar um guarda dentro do PR que conserta outro é
o acoplamento que este repositório recusa desde a regra de `spec-change` separado.
E a correção não é uma linha: o hook decide por `file_path`, e **não há
`file_path` num `sed -i`**. Decidir por texto de comando é a pergunta que
`readonly_bash.py` já responde com allowlist, e replicá-la seria a segunda
implementação da mesma pergunta.

**As três formas, para quando a decisão vier:** `Bash` no matcher com detecção por
texto de comando; guarda no `PostToolUse` comparando a branch antes e depois — que
pega a corrida em vez de preveni-la, com o dano já gravado; ou disciplina
declarada, escrita em arquivo rastreado passando por `Write`/`Edit` e `Bash`
ficando para comando. A terceira é a mais barata e **admite que o guarda não
guarda** — e disciplina é o que falhou nas quatro reincidências da D16.

**Uma superfície a mais, achada nesta fase.** O gatilho literal — a primeira
sessão em duas branches — ocorreu no trabalho da P7-2, com três branches e duas
re-ancoragens. O defeito **não** ocorreu: toda escrita em arquivo rastreado passou
por `Edit`/`Write`, e o sentinela recusou as duas trocas e exigiu re-ancoragem com
o nome digitado. Isso é a forma 3 — disciplina declarada — sendo cumprida, e é
evidência a favor dela, não contra.

**Mas `git stash` e `git stash pop` mudam arquivo rastreado por um caminho que o
matcher também não vê**, e não são escrita de conteúdo. Se o sentinela existe para
pegar trabalho pensado sobre uma árvore e gravado noutra, `stash` é esse risco por
uma porta que nenhuma das três formas mapeou. A decisão entre elas passa a ter
esse caso.

**A pendência NÃO está vencida.** No vocabulário deste registro, vencer é o
gatilho chegar e o defeito aparecer — foi o caso da P6-9. Aqui o gatilho chegou e
o defeito não apareceu.

**Vence em:** a primeira sessão que trabalhe em duas branches, **ou** a Fase 8,
quando o paralelismo começar e várias branches viverem ao mesmo tempo — o que vier
primeiro. É **decisão do proprietário**: as três têm custos de natureza diferente.

#### P6-7 — a metade do fluxo, que sobrou quando a metade da fábrica fechou

**Herdada meio-fechada** (`docs/progress/fase_6.md`, §"P6-7"), e é a única da
tabela que chega assim. A pergunta original era *"rota nova pode declarar `emite`
em `api_surface.yaml` e não chamar emissor nenhum?"* — `check_api_surface.py`
confere que a rota **declara** `emite`, e não que ela **emite**.

**O que fechou na Fase 6, e não era a pergunta cara.** O B2 da sexta auditoria
decidiu a pendência mostrando que ela mirava o lugar errado: o defeito real não
era um handler que não chamasse o emissor, era a **fábrica de produção da
`academus-api` montando sem emissor nenhum**. Não havia handler a analisar,
porque não havia emissor na aplicação — `GET /audit/grade-changes` respondia
`200` em produção e não gravava nada. `scripts/check_fabrica_liga_emissor.py`
fechou isso, e ficou mais barato que o mapa previa porque a convenção recai sobre
**a fábrica, que é uma por serviço**, e não sobre cada rota.

**O que continua aberto:** *"este handler, executado, emite?"* — a pergunta de
fluxo. O verificador da fábrica imprime essa fronteira na própria saída, em vez
de deixá-la implícita. Hoje quem a cobre é `tests/test_api_emissao_pela_rota.py`,
que exercita a rota real por `TestClient` e afirma sobre o evento no store —
cobertura por teste, e não por propriedade.

**As duas formas seguem esperando decisão do proprietário**, e o custo de cada uma
está medido na fonte: **análise de fluxo** responde à pergunta certa sem convenção
nenhuma, e custa outra ordem de esforço — cadeia de chamadas entre módulos, com
alias, indireção e `getattr`, e um analisador incompleto volta a ser a fraqueza de
taxa de erro desconhecida que a Fase 6 já descartou; **convenção estrutural
imposta por verificador** transforma a pergunta difícil em decidível por AST
simples, e custa liberdade de desenho — rota que não entrar por um ponto de
emissão nomeado reprova mesmo estando correta.

**A vizinhança com a P7-5, e ela não é identidade.** A P7-5 pergunta *"quem chama
este emissor?"* e é o **degrau 2** da §7.1 — allowlist de chamadores, resolvida por
import. A P6-7 pergunta *"esta rota, executada, emite?"* e é o **degrau 3**, que é
execução. Não são a mesma pendência e não se fecham juntas. Mas quem implementar a
P7-5 na peça 6 esbarra nesta fronteira, porque as duas leem `api_surface.yaml` e
param em lugares diferentes — e é barato dizer isso agora.

**Por que ela chegou aqui só na peça 1.** Ela foi a **sexta ocorrência** da classe
da §7.1, e a mais cara de admitir: quatro leituras da pauta da Fase 6 passaram por
ela sem transcrevê-la, porque a célula da tabela de lá dizia *"VENCIDA na metade
que mordeu"* e "VENCIDA" lê-se como fechada. Quem a achou foi o verificador da
peça 1, na primeira execução sobre a árvore real — que é exatamente o argumento
de que transcrição manual não pode ser o mecanismo.

**Vence em:** a próxima rota que declare `emite` **em um serviço cuja fábrica já
constrói o produtor** — aí a pergunta que sobra é a do fluxo —, **ou** a Fase 8,
quando o paralelismo multiplicar quem escreve rota, o que vier primeiro.

#### P6-8 — justificativa ausente devolve `409`, e `409` é recusa de estado

**Herdada com o mérito decidido e a medição pendente**
(`docs/progress/fase_6.md`, §"P6-8"). `_declara` captura `EmissaoRecusada` e
responde **409** para todas as causas. O comentário da própria função reserva o
409 a *"o pedido é bem formado e o ESTADO o recusa"* e enumera **três**, todas de
contrassinatura: antecedente ausente, fora de ordem, e par já fechado.
**Justificativa ausente não é nenhuma delas** — é campo obrigatório faltando,
pedido malformado, e o código honesto seria **422**, que é o que as duas rotas de
período inválido já devolvem no adapter.

**Por que não foi corrigido.** Duas razões de escopo, e nenhuma de dúvida: mudar
status no meio de uma correção de auditoria é escopo crescendo; e **`409` é
superfície contratada** — quem consome a API pode depender dele, e
`api_surface.yaml` não declara status, então a dependência, se existir, é
invisível ao verificador.

**O que falta medir antes de mudar:** quem depende do status hoje. `gm-console` e
`participant-view` são os consumidores conhecidos; um `grep` por `409` na árvore
de cliente responde metade, e a outra metade é se algum teste o afirma. **O teste
afirma `409`, e isso é deliberado** — teste que descreve o que deveria ser, e não
o que é, não pega regressão. A discrepância está no docstring dele.

**Vence em:** a medição dos consumidores, **ou** a Fase 10, quando o AAR passar a
ler recusas — o que vier primeiro.

#### P6-11 — VENCIDA E RESOLVIDA: recusa alta, no computador, com exceção nomeada

**Herdada da Fase 6 como a única pendência que não esperava condição externa — o
mecanismo existia e o lugar estava escolhido; faltava a palavra sobre ignorar ×
recusar. Decisão do operador, depois do merge do PR #53: RECUSAR ALTO.**

Este conserto é **código puro**, em PR próprio contra `main` e **fora de qualquer
branch de fase**: a Fase 7 não abriu.

##### A medição, antes do conserto — e ela é mais larga que a L1 original

A L1 da terceira auditoria mediu `confidence: 900 → brier 64,0`. Refeita nesta
árvore antes de escrever uma linha, sobre um único caso no escopo:

| valor | `defensibility` | Brier | sinal comportamental |
|---|---|---|---|
| `900` | 1.0 | **64,0** | nenhum |
| `900` | 0.0 | 81,0 | **overconfidence FALSO** |
| `-1` | 1.0 | 1,0201 | **underconfidence FALSO** |
| `100.5` | 1.0 | 1,0 | **underconfidence FALSO**, e o caso vira *"não avaliado"* |
| `"90"` | 1.0 | 1,0 | **underconfidence FALSO**, e o caso vira *"não avaliado"* |
| `True` | 1.0 | 0,9801 | **underconfidence FALSO** — entrou valendo `1` |

**O que a medição acrescenta à L1:** o defeito não era só o deslocamento do
escore. Três dos payloads produzem **sinal comportamental falso**, e dois deles
fazem a equipe que *submeteu* constar como quem *não olhou*.

##### As quatro razões da decisão, na ordem em que o operador as deu

**1. Não é o caso de "ignorar e nomear", e a diferença é de significado.**
`Calibracao.nao_avaliados` nomeia ausência **com significado pedagógico**: o AAR
distingue *"avaliou com confiança zero"* de *"não avaliou"*, e isso é informação
sobre a equipe. `confidence: 900` não é informação sobre nada — é dado que o
contrato proíbe (`0..100`, inteiro) entrando por caminho que não valida.
Tratá-lo como sinal inventaria semântica para lixo, e criaria uma terceira
categoria que nenhuma seção define.

**2. A gravidade é de `03` §5.4, e não do Brier.** Os sinais têm bordas exatas —
`≥ 80` sobre `≤ 0.2`, `≤ 30` sobre `= 1.0`. Fora de faixa **cai do lado errado de
uma borda**, e a tabela acima mede as duas direções. E `03` §5.4 lê overconfidence
como *"falsa acusação — anular nota de formando inocente"*: um dado corrompido
viraria **acusação pedagógica contra a equipe**.

**Clampar é pior, e por isso não foi escolhido.** `900 → 100` produz
overconfidence **plausível e indistinguível da real** — o defeito perderia o
único sintoma que tinha. É a forma que `00` §3.2 nomeia: o número errado que
ninguém percebe.

**3. A forma é a exceção nomeada da fase** — `SemGramaticaTemporal`,
`LinhagemInvalida`, e agora `SubmissaoForaDoContrato`: recusa **nomeando o campo,
o caso e o valor**, em vez de responder. Os três chegam como atributos, e não
como texto de mensagem, pelo mesmo motivo dos quatro `motivo` de
`LinhagemInvalida`: quem trata não casa por prosa.

**4. A consequência, dita: isso torna o cálculo de calibração abortável em
exercício.** A guarda mora em `_por_caso`, que é o caminho dos **dois**
consumidores — o escore completo e o `brier` que `_instante_do_limiar`
(`03` §3.3) recalcula a cada prefixo para achar `TTIV`. Um único payload
corrompido derruba o cálculo inteiro, e não só aquele caso.

**É aceitável pelo mesmo argumento do `since`:** número errado que ninguém
percebe é pior que ausência ruidosa. Mas o que fecha a frase é o resto dela — **a
defesa real é a rota validar antes, e a recusa no computador é a última linha,
não a primeira.** Aqui a submissão já é evento, e o event store é append-only:
quando esta exceção dispara, o dado inválido já está gravado. Isso é a **P7-1**.

##### O que a guarda cobre, e a fronteira é declarada

Ela cobre **os dois campos que este módulo lê** — `case_id` e `confidence` —, e
não o payload inteiro. `classification`, `evidence` e `justificativa` são do
contrato e não são lidos aqui; recusar por eles faria o computador validar o que
não consome, e isso é da rota.

**Três casos foram além dos quatro plantados que o operador nomeou, e a razão é
que são a mesma regra e não uma segunda decisão** — *o computador não inventa
semântica para o que lê e não consegue interpretar*:

- **`confidence` ausente.** O contrato a exige, e a lista de
  `x-aurora-invalid-examples` a nomeia: *"sem ela não há Brier nem sinal
  comportamental"*. Ignorá-la fazia o caso virar *"não avaliado"* — afirmação
  falsa sobre uma equipe que submeteu, e a tabela mostra o sinal falso que ela
  produz.
- **`case_id` ausente ou fora de forma.** Mesma regra, e a exceção diz
  `caso is None` em vez de inventar um.
- **`True`.** `isinstance(True, int)` é verdadeiro em Python e JSON não tem essa
  ponte. Sem a linha que o exclui, `True` entraria valendo `1` — número
  plausível, e por isso pior que um erro.

Se a fronteira tiver de encolher para os quatro casos originais, é uma linha a
remover; ela está aqui declarada e não silenciosa.

##### A prova, e ela é reexecutável — não atestação

`tests/test_metrics_calibracao.py::ASubmissaoForaDoContratoERecusada`, **11
testes versionados**. É a lição da **P6-13** aplicada no mesmo mês em que ela foi
escrita: violação plantada fora da árvore vira atestação do autor, e o que se
versiona é o probe.

**O vermelho foi medido antes, e com a violação plantada de volta depois** — o
comportamento antigo (`continue` no lugar dos dois `raise`) recolocado, a suíte
rodada, a árvore restaurada:

```
Ran 11 tests   FAILED (failures=9)
```

**Nove reprovam, e os dois que passam são o controle positivo** — as quatro
bordas exatas `0`, `30`, `80` e `100`, que passam **antes e depois**. É essa
metade que prova que a guarda **discrimina por contrato** em vez de reprovar
tudo: sem ela, uma recusa que negasse toda submissão satisfaria os nove
negativos.

**Suíte inteira:** 746 testes, verdes. O contador do README acompanhou, na mesma
branch e em commit separado.

#### P6-12 — a condição (4) da contrassinatura não pode disparar em produção

**M1 da décima auditoria da Fase 6, e o mérito é do achado.**
`range-core/participant/api/app.py:101` emite `tokens.issue(persona, persona,
...)` — `sub` recebe o próprio valor de `persona` —, e `_declara` propaga
`actor_id = claims.sub`. Com isso `actor_id` é **função de `persona`**: satisfeita
a condição (2), que exige personas distintas, a (4) passa a ser satisfeita por
construção, e a comparação em
`range-core/declarations/contrassinatura.py:106` não tem como disparar. Nem para
dualidade humana, nem para **reuso de credencial**, que era a metade que a §1 da
Fase 6 afirmou estar coberta.

**O que fica errado não é o mecanismo — é o que a norma promete.** `03` §3.4
escreve a condição (4) com a justificativa *"um mesmo operador com duas
credenciais satisfaria as personas e assinaria sozinho"*. A spec é o que alguém
lê, e ela promete uma barreira que o sistema não tem.

| Saída | O que ela faz | O que custa |
|---|---|---|
| **(a) a norma passa a dizer o que o mecanismo faz** | `03` §3.4 declara a (4) como condição **estrutural** — escrita na forma certa, com dentes quando houver identidade de credencial | `spec-change`, em PR próprio e **antes de qualquer código**. E aceita, por escrito, que hoje a autocontrassinatura por posse dupla não é barrada |
| **(b) `sub` passa a ser identidade de credencial** | a (4) volta a morder no caso que ela nomeia | mexe na emissão de token da superfície de participante e nas sete credenciais de ambiente |

**Vence em:** a sua palavra. Nenhum item da DoD da Fase 6 cobrava credencial por
humano, e nem `01` §6 nem `05` §8 a exigem — por isso é pendência e não conserto.

#### P6-13 — dezesseis violações plantadas que ninguém pode reexecutar

**L3 da décima auditoria da Fase 6.** A tabela da §3.5 daquele registro declara
violações plantadas em `metrics/epoch.py` (2), `metrics/verificacao.py` (4),
`metrics/declaracao.py` (5) e na derivação das nove siglas (5) — **dezesseis** —,
todas "fora da árvore": a violação foi plantada, o vermelho foi observado, a
árvore foi restaurada. Não existe `test_metrics_*_probes.py`, e
`mutation_harness` não aparece em arquivo de métrica nenhum.

**A marca já está lá, e ela é o conserto no que ele tem de imediato:** as quatro
linhas dizem **ATESTAÇÃO DO AUTOR**, e a primeira linha da mesma tabela —
`check_insumo_de_metrica`, com `_probes.py` versionado e executado pelo auditor —
diz **reexecutável**. Afirmação de prova negativa que ninguém pode reexecutar tem
a **forma** de prova e o **peso** de declaração, e a auditoria seguinte lê o
registro como fonte.

**Vence em:** o artefato que torne a afirmação reexecutável — um
`test_metrics_*_probes.py` na forma dos que já existem, ou o `mutation_harness`
alcançando os computadores de métrica —, **ou** a primeira vez que alguém precise
da cobertura que a tabela declara. Enquanto não vier, a marca é o que mantém a
declaração honesta.

#### P7-1 — a rota de submissão não valida o payload contra o contrato

**Nasceu da P6-11**, e o operador pediu que fosse registrada com o mapa e **não**
implementada agora.

**O fato:** o event store não valida payload — e isso vale para todo evento, não
só para `assessment_submitted`. A rota que grava a submissão também não. A
consequência é a que a P6-11 mediu: `confidence: 900` chega ao computador porque
não há nada entre a submissão e o event store que confira o contrato que já
existe em `assessment.schema.yaml`.

**Por que ela é a defesa real, e a recusa no computador não é.** Quando
`SubmissaoForaDoContrato` dispara, o dado inválido **já está gravado**, e o event
store é append-only: não há como desfazê-lo, só interpretá-lo. A rota é o único
ponto em que a submissão inválida pode **não virar evento** — e é lá que o
participante recebe um `422` em vez de ver a calibração do exercício abortar.

**O mapa, com o que cada lugar cobre e o que deixa passar** — é a mesma tabela de
três linhas que a P6-11 trazia, relida agora que a terceira já foi construída:

| Onde | O que cobre | O que deixa passar |
|---|---|---|
| **na rota** ✅ | a submissão inválida nunca vira evento, e o participante recebe `422` em vez de um escore estranho no AAR | evento que entre por **outro** caminho — importação, reconstrução, produtor futuro. A garantia é da porta, e não da propriedade |
| **no event store**, para todo evento | seria a propriedade, e não a porta — nenhum caminho escaparia | é decisão de arquitetura bem maior que esta pendência, e toca todo produtor do catálogo. Não é o que a P6-11 decidiu |
| **no computador** | **já existe** — é a P6-11, resolvida | é a última linha: o dado já está gravado, e o custo da recusa é o cálculo inteiro |

**A recomendação, dita:** a primeira linha, e ela **não substitui** a terceira. As
duas cobrem coisas diferentes — a rota impede que o dado nasça, o computador
impede que um dado nascido por outro caminho seja interpretado. Trocar uma pela
outra reabriria exatamente a P6-11.

**Vence em:** decisão do proprietário sobre **qual das três linhas** desta fase
entrega, e a rota é candidata natural porque a Fase 7 mexe na superfície de
participante para o pack completo.

#### P7-2 — VENCIDA E RESOLVIDA: a prova passa a nomear a árvore, não o commit

**Nasceu do fechamento da Fase 6, e o caso concreto foi só o sintoma.** Depois do
merge do PR #53, dois verificadores passaram a reprovar na `main`:

```
check_prova_do_seed.py         rc=1
check_provas_de_container.py   rc=2
```

Os dois artefatos — `.aurora-prova-do-seed.json` e
`.aurora-provas-de-container.json` — foram gravados sobre
`c3051dc`, o candidato **pré-rebase** da Fase 6. O `gh pr merge --rebase`
reescreveu os SHAs, e a `main` virou `18befac`. Nenhum dos dois arquivos mudou;
o commit que eles nomeiam é que deixou de existir na default.

**A generalização, e é ela que faz disto pendência em vez de conserto:** isso
**não é acidente deste fechamento**. `WORKFLOW.md` fixa **rebase, nunca squash**,
e rebase reescreve SHA por definição. Então *todo* fechamento de fase invalida
*toda* prova amarrada ao commit, **sempre**. O conserto pontual — regravar —
resolve esta ocorrência e não toca a causa: o rito produz o defeito.

##### A medição que decide o mapa, e ela cabe em três linhas

O que o rebase preserva é a **árvore**. Medido nesta árvore, nos dois merges:

| Par | Tree |
|---|---|
| `c3051dc` (candidato auditado da Fase 6) e `dc0f036` (o par rebaseado na `main`) | `e2356091` — **iguais** |
| `c0f56f0` (tip da branch da Fase 6) e `18befac` (`main` pós-#53) | `ad2fdf6c` — **iguais** |
| `a9746c5` (tip da branch da P6-11) e `ecef8d9` (`main` pós-#54) | `466f9196` — **iguais** |

**Três merges, três pares, nenhuma diferença de árvore.** O SHA muda; o objeto
que a prova mediu, não. É a mesma igualdade de árvore que se usou para confirmar
que o #53 tinha levado tudo.

##### As três opções, com o custo de cada uma

**(a) Regravação como passo do rito de fechamento.**

| | |
|---|---|
| O que é | depois de `gh pr merge --rebase`, o rito ganha uma etapa: rodar os dois gravadores sobre a `main` resultante |
| Custo direto | **~8 min por fechamento** na máquina do operador — ~3 min das provas de container e ~5 min do seed, que é o custo já aceito na §11.3 da Fase 5 —, mais Docker no ar e um Postgres descartável |
| O que **não** cobre | é **regra, e não mecanismo** — degrau 1.5 da §7.7, na melhor leitura. A classe que a §7.7 mediu **quatro vezes** é exatamente esta: a regra existe, e o modo de falha é não reconhecer que esta mudança é uma instância dela. Uma quinta ocorrência aqui seria a mesma forma |
| Custo escondido | a janela entre o merge e a regravação continua vermelha, e ninguém a vê: o artefato é `.gitignore` e mora só na árvore de quem rodou |

**(b) A prova amarrada à ÁRVORE, e não ao commit.**

| | |
|---|---|
| O que é | o gravador escreve `git rev-parse HEAD^{tree}` no lugar do SHA do commit, e os dois verificadores comparam árvore com árvore |
| O que resolve | as três linhas da medição acima. A prova **atravessa o rebase**, porque ela passa a nomear o que de fato mediu: conteúdo, e não história |
| O argumento antiforja **sobrevive** | é o que o cabeçalho dos dois verificadores chama de mecânico: *"um commit não pode conter o próprio SHA"*. Vale igual para a árvore — o hash de árvore cobre o conteúdo dos arquivos, então **um arquivo versionado não pode conter o hash da árvore que o contém**. A condição (c), *evidência versionada reprova*, continua de pé pelo mesmo motivo e sem enfraquecer |
| O que ele **deixa passar**, e é o custo real | a árvore cobre **só o conteúdo rastreado**. As duas provas dependem de coisa que não está nela: `grava_provas_de_container.py` **materializa o pack antes do `up`**, e `scenarios/` inteiro está no `.gitignore` por decisão da Fase 5. Uma prova amarrada à árvore afirmaria estar em dia com o pack trocado embaixo dela |
| Segundo limite | dois commits com a mesma árvore ficam indistinguíveis. Para prova de **desempenho e comportamento** isso é o comportamento certo — mesmo conteúdo é o mesmo objeto —, mas deixa de distinguir *qual* commit produziu a medição, e o registro de fase cita SHA |
| Custo de implementação | dois gravadores, dois verificadores e os dois `_probes.py`. Não é grande, e é código |

**(c) Aceitar TRANSPORTADA na `main` como estado normal entre o merge e a próxima
regravação.**

| | |
|---|---|
| O que é | o verificador passa a admitir um terceiro estado, entre "em dia" e "envelhecida" |
| O custo que o proprietário nomeou | ninguém sabe distinguir *"transportada porque acabou de mergear"* de *"transportada porque ninguém regravou"* |
| **E há um custo maior embaixo dele.** | admitir o terceiro estado **sem** um predicado que o decida é fazer o verificador sair `ok` quando ele não sabe. É exatamente a degradação que esta linhagem **já aposentou duas vezes** — os dois predicados de base da Fase 3, e o cabeçalho de `check_prova_do_seed.py` escreve a direção (a) como *"a que não pode degradar"* |
| E o predicado que faltaria | para separar as duas leituras, alguma coisa precisa decidir se o commit gravado e o `HEAD` são **o mesmo objeto**. Identidade de patch ou igualdade de árvore são as únicas candidatas — e nesse ponto a **(c) vira a (b)**. A (c) sozinha é a degradação; a (c) com predicado é a (b) com outro nome |

##### Uma observação de forma, e ela muda como o conserto pontual acontece

Os dois artefatos estão no `.gitignore` — linhas 66 e 73 —, e a condição (c) dos
dois verificadores **reprova evidência versionada**. Então **regravar não é um
PR**: é operação sobre a árvore de trabalho de quem roda, e o resultado não
entra em commit nenhum. Isso também explica por que o vermelho não aparece para
todo mundo: um clone novo não tem prova nenhuma, e a checagem reprova por
ausência — que é o comportamento declarado, e é honesto.

Consequência prática que a ordem obriga: **a regravação tem de ser a última
coisa**, depois do último merge. Regravar antes de mergear este registro
produziria uma prova sobre um `HEAD` que o próprio merge desfaz — a P7-2
mordendo a mão de quem a escreve.

> **Superado pela decisão registrada no fim desta seção.** A restrição vale para
> a saída (a); a (b) a apaga, porque a árvore não muda no rebase-merge.

**DECIDIDA — saída (b): a prova amarrada à ÁRVORE.** Decisão do proprietário. Os
gravadores passam a escrever `git rev-parse HEAD^{tree}` no lugar do SHA do
commit, e os dois verificadores comparam árvore com árvore. A medição das três
linhas acima é o fundamento: três merges, três pares, nenhuma diferença de
árvore — o SHA muda, o objeto que a prova mediu não.

**Por que não a (a).** É regra, e não mecanismo — degrau 1.5 da §7.1, e a classe
que ela mede reincidiu quatro vezes. Some-se que a regravação não entra em commit
nenhum: uma regra manual cujo resultado não deixa rastro versionado não pode ser
auditada por ninguém além de quem a executou.

**Por que não a (c).** O próprio mapa a dissolve: o predicado que separaria
"transportada porque acabou de mergear" de "transportada porque ninguém regravou"
só pode ser identidade de patch ou igualdade de árvore, e nesse ponto a (c) vira
a (b). Sem predicado, é verificador saindo `ok` quando não sabe — a degradação
que esta linhagem já aposentou duas vezes.

**O que a (b) apaga, e não estava escrito.** A restrição "regravar tem de ser a
última coisa, depois do último merge" é restrição da (a): ela existe porque a
prova nomeia história, e história muda no merge. Com a prova nomeando árvore, a
ordem deixa de importar.

**O que a (b) NÃO cobre, e nasce como P7-3.** A árvore cobre só o conteúdo
rastreado, e `scenarios/` está no `.gitignore` por decisão da Fase 5. É buraco
que já existe hoje — o SHA tem a mesma cegueira —, e a (b) apenas o torna
nomeável.

**A advertência herdada do commit que corrigiu este mapa:** os dois artefatos
continuam no `.gitignore`, e a condição (c) reprova evidência versionada. Quem
escrever o rito precisa escrever junto que regravar não entra em commit.

**Onde o conserto mora:** código puro, em PR próprio contra `main` e fora de
qualquer branch de fase — o mesmo rito da P6-11. A Fase 7 não abriu.

**IMPLEMENTADA no PR #56**, conserto pontual contra `main`, fora desta branch, no
rito da P6-11. Os dois gravadores, os dois verificadores e os dois `_probes.py`
passaram a nomear `HEAD^{tree}`; o campo `commit` virou `tree`; o esquema do
artefato de container foi para `/2` e o do seed ganhou esquema. A prosa que
descrevia o mecanismo mudou junto — `WORKFLOW.md`, `.gitignore`,
`start_checkpoint_audit.sh`, `invariants.yml` e os comentários da allowlist do
auditor —, porque texto normativo que sobrevive à mudança que descreve é a §1.6
com outro nome.

**O merge é o próprio espécime:** `ddb5d59` virou `93847b4` no rebase-and-merge,
e a árvore não mudou. O rito que produzia o defeito foi exercido pela correção no
ato de entrar.

**Um teste nasceu inerte e foi pego antes de virar prova.** O probe do rebase
criava e reaplicava o commit no mesmo segundo; os dois objetos saíam
byte-idênticos e o git devolvia o mesmo SHA — o eixo passava sem exercer rebase
nenhum. `GIT_COMMITTER_DATE` fixa. Numa máquina mais lenta teria passado por
acaso.

#### P7-3 — a árvore não cobre o pack, e o pack é insumo da prova

**Nasceu da decisão da P7-2.** A saída (b) amarra a prova ao hash da árvore, e a
árvore cobre **só o conteúdo rastreado**. `grava_provas_de_container.py`
materializa o pack antes do `up`, e `scenarios/` inteiro está no `.gitignore` por
decisão da Fase 5. Uma prova amarrada à árvore afirmaria estar em dia com o pack
trocado por baixo dela.

**Não é defeito introduzido pela (b).** Prova amarrada ao SHA tem exatamente a
mesma cegueira: o commit também só cobre o rastreado. A (b) não cria o buraco —
ela o torna nomeável, porque passa a declarar o que de fato mede.

**Vence em:** a peça 7 desta fase — o critério dos 3 s exige o pack
materializado, e é ali que a prova afirmaria estar em dia com um pack que não
hasheia.

**A janela barata passou.** O gatilho anterior era a implementação da saída (b),
porque ali o gravador escolhia o que hasheia e acrescentar o pack custava quase
nada. O PR #56 passou sem isso. O defeito não nasceu ali — ele preexiste ao SHA e
à árvore —, mas o conserto deixou de ser de graça.

#### P6-9 — VENCIDA: a terceira divergência chegou antes do gatilho

**A terceira ocorrência aconteceu no PR #56.** Editar os comentários de
`user-scope/hooks/readonly_bash.py` fez `phase0_negative_tests.py` reprovar na
hora, pelo gate que exige que a fonte e a cópia em `~/.claude/hooks/` sejam
idênticas. A remediação foi a mesma das duas anteriores: copiar à mão.

**O gatilho declarado era a próxima auditoria de checkpoint, e não foi ele.** A
divergência nasce de qualquer edição da fonte, e edição da fonte acontece em
trabalho comum. Registrar o gatilho como "a auditoria" descrevia onde a
divergência **dói**, não onde ela **ocorre**.

**As três formas seguem mapeadas na Fase 6, §P6-9, e nenhuma foi escolhida.**
Decisão do proprietário.

---

## 7. Pauta de mecanismo herdada — DECIDIDA: os dois mapas viram entrega

Os dois itens abaixo **não** são pendências e não têm identificador: nenhum deles
afirma defeito aberto. São **mapas** — cada um mediu o custo de um mecanismo
possível e parou antes de implementá-lo, porque a escolha é do proprietário.
Ambos foram escritos com a mesma fórmula no fim: *"o mapa está aqui para ser
decidido, não executado"*.

> **Superado pela decisão registrada abaixo.** Valia enquanto os dois eram mapas.

Estão aqui, e não só no registro da Fase 6, porque mapa que vive no inventário de
uma fase encerrada é mapa que ninguém abre — é a mesma razão pela qual este
arquivo nasceu antes da fase, escrita no topo.

> **DECIDIDOS pelo proprietário nesta fase.** Os dois deixaram de ser mapas e
> viraram entrega, e por isso ganharam identificador: a §7.1 é a **P7-5**, a §7.2
> é a **P7-4**. A ressalva do parágrafo acima — que mapa não é pendência e não
> tem ID — valia enquanto nenhum dos dois afirmava trabalho a fazer.

### 7.1 Os três degraus da §7.7 — a classe que reincidiu quatro vezes

**A classe:** uma exigência é afirmada num lugar e os sítios que a satisfazem não
são varridos quando ela muda. Quatro ocorrências na Fase 6 — o sétimo contrato
com o CI ainda afirmando seis; o venv da auditoria ausente da branch; a
precondição de boot do pack sem varrer o gravador; o contrato do token sem varrer
o chamador de produção.

**Duas regras escritas não a impediram**, e o registro da Fase 6 diz por quê: o
modo de falha não é ignorar a regra, é **não reconhecer que esta mudança é uma
instância dela**. A regra cobra varredura depois de uma classificação, e é a
classificação que falha. Mecanismo não pede classificação: dispara sobre o
artefato.

| Degrau | O que é | Custo | O que deixa passar |
|---|---|---|---|
| **1 — desduplicar o fato** | onde a exigência puder ser **derivada** em vez de afirmada, a classe deixa de existir. Funcionou uma vez na Fase 6: o CI parou de dizer `== 6` e passou a derivar de `contracts_dir()` | quase zero | os fatos que **não** aceitam derivação — qual emissor serve qual superfície é decisão, não contagem |
| **1.5 — a regra ancorada no artefato** | um hook que dispare quando o commit toca `EXIGIDAS`, `_payload` ou `token.claims` de um `api_surface.yaml`, e **imprima a lista de chamadores daquele emissor** | baixo | não bloqueia — não tem como saber se a varredura aconteceu. Cobertura humana, e é honesto dizer que é isso |
| **2 — allowlist de chamadores por emissor** | AST pura, na forma do `check_core_boundary.py`: achar as chamadas, resolver o módulo importado, exigir que o arquivo esteja na lista daquele emissor. Os emissores são **três e fechados**, e metade da tabela já existe em `check_api_surface.py::PERFIS` | baixo, e **teria pego o B1 da §7.6** | é por arquivo: iria cega no dia em que um arquivo falasse com duas superfícies. O que fecha o buraco é o achado negativo da §7.6 — **nenhum cliente precisa do `issue` do núcleo** —, e é essa propriedade, não a lista, que faz o degrau valer |
| **3 — execução** | o que sobra, e sobra por natureza | a prova de container | nada; é o único instrumento onde não há objeto a medir |

**A recomendação registrada no fechamento**, com as palavras de lá: para o
**token**, não é verdade que só a prova de container cobre — o degrau 2 é
escrevível e barato. Para o **boot**, é verdade: precondição de boot é
procedimento, não objeto, e não há verificador sem casar prosa. Isso não é lacuna
a fechar depois — é o argumento de que **a prova de container tem de ser gate
obrigatório, e não opcional**.

**Sexta ocorrência, no PR #56, e a variante é nova.** O mapa do escopo procurou
quem faz *parse* do JSON da prova e concluiu que o lançador não lê o campo. Era
verdade e insuficiente: `start_checkpoint_audit.sh:652` fazia
`grep -q "\"$HEAD_SHA\""` dentro do artefato — leitura do valor sem parse nenhum.
Deixada como estava, ela nunca casaria, e toda medição reprovada seria briefada
ao auditor como "não mediu".

**A varredura aconteceu; o predicado é que era estreito.** Isso muda o desenho da
P7-5: allowlist de chamadores por emissor resolve import, e `grep` dentro de `.sh`
não é import. O degrau 2 não alcança esse caminho, e dizer isso agora é mais
barato que descobrir na peça 6.

**A forma geral, que é o que sai daqui:** a classe fecha quando a exigência é
conferida sobre o **objeto que ela governa**, e não sobre os caminhos que o
produzem.

**Fonte:** `docs/progress/fase_6.md`, §7.7.

**DECIDIDA — P7-5: adotado o degrau 2 para o token.** Allowlist de chamadores por
emissor, AST pura na forma de `check_core_boundary.py`. Os emissores são três e
fechados, e metade da tabela já existe em `check_api_surface.py::PERFIS`.

**A recomendação sobre o boot NÃO foi adotada, e a lacuna fica declarada.** Este
mapa conclui que a prova de container tem de ser gate obrigatório, porque
precondição de boot é procedimento e não objeto. O proprietário decidiu que não:
o custo por fechamento não se justifica. A consequência é que **o boot segue
coberto só por execução voluntária**, e isso é estado declarado, não lacuna
esquecida.

### 7.2 A allowlist por selecionador da §8.5 — "a mesma pergunta tem uma resposta"

**Nasceu de uma pergunta do proprietário** na nona auditoria da Fase 6: *há
mecanismo que cubra que todo consumo de epoch passe pela mesma função, ou a
resposta honesta é que só a matriz de testes cobre?*

**A medição mostrou que a formulação estava errada.** Nove módulos de
`range-core/` leem `.simulation_epoch`, e os nove são legítimos. Mas o B1 não foi
epoch **lida errado**: foi epoch **não lida** — o avaliador não tinha comparação
de epoch nenhuma. Um verificador que cobre *quem lê* não vê *quem deixou de ler*.
A propriedade quebrada era **"a mesma pergunta tem uma resposta"**, e epoch era
só o campo em que as duas divergiam.

**Nessa formulação há mecanismo, e ele é estrutural.** Medido por AST, contando
módulos que comparam `event_type` contra cada constante: `ROLLBACK_PERFORMED` tem
**8** selecionadores, `EXERCISE_STARTED` 5, `INJECT_FIRED` 4,
`INTEGRITY_VALIDATION_DECLARED` 3, `ASSESSMENT_SUBMITTED` 2, e os outros nove
tipos 1. Isso mata a regra ingênua — *"um dono por tipo"* — antes de ela ser
proposta: os oito consumidores de `ROLLBACK_PERFORMED` fazem perguntas
**diferentes** sobre o mesmo evento, e dono único ali seria uma função com oito
sentidos.

**O que sobra é a forma que já funciona nesta árvore:** allowlist por tipo,
declarada com o motivo — a mesma de `check_core_contract_imports.py`. Ela é
testável contra o próprio defeito que a originou: escrever
`_ja_satisfeito_na_corrente` faria `VERIFICATION_PREDICATE_SATISFIED` passar de um
para **dois** selecionadores, e a allowlist reprovaria até alguém escrever por
quê.

**O limite, na taxonomia da §7.1 acima: é degrau 1.5, não degrau 2.** Cobra
**declaração, não concordância** — dois consumidores declarados podem continuar
divergindo, e nenhum AST decide se duas buscas têm o mesmo propósito, porque
propósito não é estrutura. O que muda é **quando** a duplicação fica visível: no
commit que a cria, em vez de na nona auditoria. Para a divergência entre
duplicatas declaradas, o que cobre é a matriz de testes.

**Fonte:** `docs/progress/fase_6.md`, §8.5.

**DECIDIDA — P7-4: adotada a allowlist por tipo.** Degrau 1.5, com o limite
aceito como está: cobra declaração, não concordância. Ela nasce com o teste
contra o defeito que a originou — escrever `_ja_satisfeito_na_corrente` faria
`VERIFICATION_PREDICATE_SATISFIED` passar de um para dois selecionadores, e a
allowlist reprovaria.

**Forma comum com a P7-5, declarada aqui para que não divirjam:** as duas são
allowlist declarada com motivo, na linha de `check_core_contract_imports.py`. O
esqueleto é o mesmo; o que muda é o objeto governado — event_type por
selecionador aqui, chamador por emissor lá. Duas sintaxes de allowlist para a
mesma forma seria a D4 que os dois mecanismos existem para pegar.
