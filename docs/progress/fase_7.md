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

## 1. Plano da fase — cinco peças

> **REDUZIDA de sete para cinco, por decisão do proprietário.** As peças 3
> (gramática de `exercise_time`) e 6 (as duas allowlists) saíram, reagendadas com
> gatilho declarado. O critério de corte, dito com todas as letras: **o que
> quebra durante exercício ao vivo com cliente** — e as duas não passam nele. A
> §1.1 traz a razão medida de cada uma.
>
> **A numeração antiga fica entre parênteses nas linhas movidas**, e não é
> enfeite: os registros de fechamento das peças 1 e 2 e todos os commits desta
> branch citam "peça 4", "peça 6" e "peça 7" com o sentido antigo. Renumerar sem
> deixar rastro apagaria a ligação entre a pauta e o registro em que ela nasceu —
> é a mesma razão pela qual a §6 preserva o prefixo herdado das pendências.

Os nove critérios DONE de `07_IMPLEMENTATION_PHASES.md` §"Fase 7" se agrupam em
quatro blocos de entrega.

| Peça | O que entrega | Origem |
|---|---|---|
| 1 | verificador de transcrição de pauta entre registros de fase | quinta ocorrência da classe da §7.1, medida no rebase que abriu esta fase — **FECHADA** |
| 2 | pack: esqueleto de migração e recusa por versão, o produtor `range-cli scenario materialize`, o linter de citação de fato | DONE 7 e 8 — **FECHADA** |
| 3 *(era 4)* | `range-cli scenario lint`: inject sem objetivo e sem `noise: true`, `event_type` inexistente em condição com posição no arquivo, condição por juízo do facilitador | DONE 1, 2 e 3 — **FECHADA**, e ela também fechou a P7-7 |
| 4 *(era 5)* | branching: `branch_policy` do manifesto aplicada, branch sem `reconverge_at` recusado, `dryrun` percorre todos os caminhos | DONE 4, 5 e 6 |
| 5 *(era 7)* | volume: reconstrução completa da projeção do `ransomware-universidade` de 4 h em < 3 s | DONE 9 |

**A peça 1 vem primeiro porque é degrau 1** na taxonomia da §7.1 — a exigência
deixa de ser afirmada em cada registro de fase e passa a ser derivada deles. É o
único degrau que faz a classe deixar de existir em vez de ficar visível.

### 1.1 As duas peças que saíram, e por que cada uma passa no corte

O critério é **o que quebra durante exercício ao vivo com cliente**. As duas têm
valor real; nenhuma das duas quebra na sala.

#### A peça 3 antiga — a gramática de `exercise_time`

**Nada quebra ao vivo por ela não existir, e isso é medição da Fase 6, não
suposição.** Não existe produtor de `fact_materialized`: `Mundo.fatos` é vazio em
produção, e **nenhum comportamento de hoje depende da escolha** que a P6-3 cobra.

**A ausência é CONTIDA, e não silenciosa** — é o que separa este adiamento de uma
lacuna. Duas guardas a delimitam, e as duas foram entregues na Fase 6:

| Guarda | O que ela faz |
|---|---|
| `confere_folhas_temporais` | recusa o pack **na carga**, nomeando a folha e o motivo, enquanto ainda dá para consertar |
| `SemGramaticaTemporal` no avaliador | **levanta** em vez de responder. As duas respostas plausíveis são piores: falso faz a contenção nunca verificar, verdadeiro a faz verificar com vazamento em curso |

**O que quebraria ao vivo é um pack que use `before`/`after` — e a carga recusa
esse pack.** O defeito não chega à sala: ele chega ao boot, que é onde a §3.1 da
Fase 6 decidiu pô-lo.

**E os três gatilhos da P6-3 foram medidos um a um no fechamento da peça 2**
(§3.8), justamente para que esta decisão não fosse tomada no escuro: **nenhum
disparou**. O produtor de pack escreve `exercise_time` como campo de `facts`, e
declarar um fato no pack não é produzir o fato — `FACT_MATERIALIZED` tem dois
usos em produção, o import e uma leitura, e nenhum `append`.

#### A peça 6 antiga — as duas allowlists

**Elas são mecanismo contra a classe da §7.1, e o valor é real — mas INTERNO.**
Uma exigência afirmada num lugar cujos sítios não são varridos quando ela muda
custa rodadas de auditoria e retrabalho. Não custa nada na frente do cliente: o
exercício roda igual.

**E o escopo é maior do que a §1 supunha quando as adotou.** A peça 2 mediu
(§3.5) que a classe tem **três variantes distintas**, cada uma escapando por um
caminho diferente:

| Variante | O mecanismo que a alcança |
|---|---|
| predicado estreito | allowlist de chamadores por emissor — a P7-5, degrau 2 |
| defeito sem sujeito | **derivação**, e não varredura — degrau 1, faz a classe deixar de existir |
| cobertura que não alcança o ponto de entrada | **execução** — degrau 3, e a §7.1 já registra que ali *"o que sobra é a prova de container"* |

Adotar "as duas allowlists" como uma peça supunha um mecanismo para uma classe.
São três mecanismos para três variantes, e um deles exige prova de container —
que o proprietário já decidiu **não** tornar gate obrigatório (§7.1).

**O CUSTO, dito sem suavizar.** A §7.1 registra que **duas regras escritas não
seguraram a classe**, e que ela reincidiu **cinco vezes na Fase 6** — hoje dez,
com as ocorrências que esta fase acrescentou. O parágrafo que fecha aquele mapa
diz que o modo de falha *"não é ignorar a regra, é não reconhecer que esta
mudança é uma instância dela"*, e que mecanismo não pede classificação: dispara
sobre o artefato.

**Adiar é aceitar que a próxima ocorrência custe uma rodada.** Não há leitura
otimista disponível: a classe reincidiu dez vezes, e nada no adiamento a torna
menos provável. **Foi decisão informada**, com o número na mesa.

> **~~A peça 7 depende da P7-3.~~ SUPERADO na peça 2.** A afirmação era: *"o
> critério dos 3 s é prova de desempenho, e prova de desempenho depende do pack
> materializado — que é exatamente o que a árvore não cobre. A P7-3 vence na
> implementação da saída (b) da P7-2, e essa implementação é conserto pontual
> contra `main`, fora desta branch."*
>
> **A dependência deixou de existir**, e não por decisão: a peça 2 entregou o
> produtor de pack, e com ele o determinismo passou a ser propriedade **provada**
> do artefato. Um pack cujos bytes são função dos insumos não precisa da árvore
> para ser comparado — ele é reproduzível por comando. A P7-3 fecha na §3.5, e a
> peça 7 passa a depender só do pack existir, o que ela já pode fazer nascer.
>
> A previsão de *onde* a P7-3 venceria também estava errada: ela dizia "na
> implementação da saída (b) da P7-2", e o PR #56 passou sem tocá-la — está
> registrado no detalhe dela como *"a janela barata passou"*. Quem a fechou foi
> o produtor, três peças depois e por outro caminho.

**A CLI não é peça própria.** Ela é a superfície das peças 2, 4 e 5: o primeiro
critério DONE já a nomeia (`range-cli scenario lint`), e o resto se expõe por ela.

**O verde de `check_progress_consistency.py` é condição de fechamento, e ele está
VERDE desde a redução de escopo.**

> **A causa do vermelho mudou, e a redação anterior caducou junto.** Ela dizia:
> *"ele reprova hoje por P7-4 e P7-5, cujas seções são o desenho das duas
> allowlists e nascem na peça 6. Até lá o vermelho é esperado e tem causa
> nomeada."*
>
> **Aquela causa deixou de existir quando a peça 6 saiu da fase.** As duas
> pendências continuam na tabela — agora `ABERTA`, com destinatário Fase 12 —, e
> a peça que escreveria as seções delas não existe mais. Mantido o texto antigo,
> o vermelho passaria a durar **o resto da fase inteira sem peça que o
> consertasse**.
>
> **E é exatamente o modo de falha que o próprio parágrafo avisava:** *"gate que
> fica vermelho por motivo conhecido a fase inteira é gate que se aprende a
> ignorar, e é assim que ele deixa de pegar o dia em que ficar vermelho por outro
> motivo."* A redução de escopo transformaria o aviso em profecia.
>
> **Por isso as duas seções de detalhe foram escritas agora**, e não adiadas com
> a peça: elas não descrevem o mecanismo que ninguém vai construir nesta fase —
> descrevem a **pendência**, que é o que a §6 cobra. O material existia: os dois
> mapas da §7 e as três variantes que a peça 2 mediu.

Gate que fica vermelho por motivo conhecido a fase inteira é gate que se aprende
a ignorar. A saída não é declarar melhor o vermelho: é não tê-lo.

## 2. A peça 1 — a pauta herdada deixa de depender de quem transcreve

Seis unidades, cada uma commitada em verde. O que segue é o que a auditoria
precisa achar sem reconstruir a cadeia por leitura.

**O que a peça fecha, em uma frase:** a pergunta *"a pauta da fase anterior
chegou inteira aqui?"* era respondida por leitura, e passou a ser respondida por
predicado.

### 2.1 O que foi entregue, por unidade

| # | Unidade | O que fecha |
|---|---|---|
| 1 | coluna `Estado` na tabela da §6, com enum fechado de seis valores (`422a105`) | estado e gatilho deixam de dividir célula. A pergunta *"quantas seguem abertas?"* vira comparação contra seis strings, e não prosa parseada |
| 2 | a linha de status do registro (`2f2272e`) | ela acompanha a peça, e não o fechamento — o rótulo envelheceu três vezes na Fase 6 |
| 3 | `<!-- tabela-resumo-de-pendencias -->` e `_localiza` (`01a4e05`) | o parser deixa de achar a tabela-resumo por **posição**, e passa a lê-la onde o registro a declara |
| 4 | a mesma coluna na `fase_6.md` (`b4fd284`) | o vocabulário vale nos **dois** lados do par, que é o que torna o cruzamento possível |
| 5 | o quarto predicado de `check_progress_consistency.py` (`d29022b`) | **todo item não-fechado da fase N aparece na tabela da fase N+1** |
| 6 | `check_progress_consistency_probes.py`, 11 eixos (`01a4e05`, `d29022b`) | a prova negativa que faltava — era o único dos vinte e cinco de `scripts/` sem ela, e o `README.md` nomeava a exceção |

**O predicado, com o vocabulário que ele usa.** `ABERTA`, `LATENTE`, `DECIDIDA` e
`VENCIDA` migram; `RESOLVIDA` está fechada e não migra; `ENTREGA` é trabalho da
própria fase, cobrado pela DoD dela. Estado fora do enum **reprova**: ele não é
classificável como fechado nem como aberto, e escolher um dos dois em silêncio
degradaria exatamente onde a pergunta é.

**A direção é de N para N+1**, e ela é escolhida: é a que pega **omissão**. A
inversa — *"todo item da N+1 veio de algum lugar"* — pegaria invenção, que não é
o defeito que aconteceu.

**As duas degradações se anunciam.** Fase seguinte que não existe, e registro cuja
tabela-resumo não declara coluna de estado — `fase_1.md` até `fase_5.md`, anteriores
ao vocabulário — são **PULADOS com a razão impressa**. Par não conferido que não se
anuncia é indistinguível de par conferido e verde, e essa confusão é a classe que
o verificador inteiro persegue. Hoje são sete pulos e um par conferido.

### 2.2 A medição que vale — o verificador achou o que cinco leituras não

**A P6-7 nunca chegou a este registro, e sobreviveu a cinco passagens pela pauta
da Fase 6** — a transcrição de abertura, a reconstrução deliberada contra a fonte,
o commit que existia *para* achar omissões (`30cc1d5`, "as quatro pendências
herdadas ausentes da transcrição"), a escrita dos corpos herdados a partir da
fonte (`1331b2c`) e o mapeamento que precedeu esta peça. Cinco leituras, nenhuma
delas descuidada, e a mesma linha passando em todas.

**Quem a achou foi o predicado, na primeira execução sobre a árvore real:**

```
fase 6 -> 7: `P6-7` esta `VENCIDA` na fase 6 e NAO APARECE na tabela da fase 7.
```

**E o motivo é mecânico, não de atenção.** A célula da Fase 6 dizia *"**VENCIDA na
metade que mordeu**"*. Quem lê uma tabela lê a célula, e `VENCIDA` carrega o
sentido de encerrada; a ressalva que nega o rótulo está numa subordinada, e o
corpo que a explica — *"o que continua aberto, dito e não escondido"* — fica trinta
linhas abaixo. **Foi a separação entre estado e gatilho que tornou a omissão
classificável, e portanto cobrável**: com o estado num campo próprio, `VENCIDA`
virou um valor não-fechado, e não-fechado migra.

A peça pegou, na sua primeira execução, o defeito que ela existe para pegar. É a
única forma de evidência que este mecanismo podia produzir sobre si mesmo — e ela
custou a admissão de que a leitura humana já havia falhado cinco vezes no mesmo
ponto.

### 2.3 O sexto valor do enum, e por que ele não estava previsto

O enum foi especificado com **cinco** valores. A **P6-6** não coube em nenhum: o
gatilho literal dela — *a primeira sessão que trabalhe em duas branches* — ocorreu
no trabalho da P7-2, com três branches e duas re-ancoragens, e **o defeito não
apareceu**, porque toda escrita em arquivo rastreado passou por `Edit`/`Write`.
`ABERTA` afirma que o gatilho não chegou; `VENCIDA` afirma que o defeito apareceu.
As duas seriam falsas.

**A implementação parou antes de editar e trouxe as três saídas** — sexto valor,
redefinir `ABERTA`, ou afrouxar `VENCIDA` para "gatilho chegou" —, e o proprietário
escolheu a primeira. `LATENTE` carrega o que nenhum dos outros carrega: **o gatilho
já passou uma vez sem custo**, que é o único dado empírico existente sobre a forma 3
daquela pendência.

**Sem essa parada, o enum teria mentido sobre uma linha no mesmo commit que o
declarava fechado.** A P7-3 fez o mesmo por outro caminho: o gatilho dela nomeava
uma *janela de oportunidade* e não um defeito, a janela passou no PR #56, e ela
ficou `ABERTA` com gatilho reescrito em vez de forçada num rótulo errado.

### 2.4 O que fica aberto, e por que o gate segue vermelho

`check_progress_consistency.py` sai **rc=1**, e as duas causas estão nomeadas:
**P7-4** e **P7-5** estão na tabela e não têm seção de detalhe. As seções delas são
o desenho das duas allowlists, e nascem na **peça 6** junto com o mecanismo que
descrevem — escrevê-las antes de implementar seria adivinhar.

Isso está declarado na §1 de propósito. Gate que fica vermelho por motivo conhecido
a fase inteira é gate que se aprende a ignorar, e é assim que ele deixa de pegar o
dia em que ficar vermelho por outro motivo. **O verde dele é condição de
fechamento da fase.**

O par **6→7 passa**. Os pares 0→1 até 5→6 são pulados por falta de coluna de
estado, e 7→8 por não existir destino.

### 2.4.1 A cobertura do predicado, medida na varredura que abriu a peça 2

Os três fatos abaixo foram **medidos**, e não estimados: a varredura de abertura
da peça 2 rodou o gate e leu a faixa `fase_0.md` a `fase_5.md`. Eles ficam aqui, e
não só no relatório daquela varredura, porque declaração de cobertura que vive
fora do mecanismo é a §1.6 com outro nome.

**A faixa coberta hoje é um par de oito.** Seis são pulados por ausência de coluna
de estado nos registros 0 a 5, e o sétimo — 7→8 — por não existir
`docs/progress/fase_8.md`. O par conferido é 6→7. Isso não é defeito do predicado:
é o preço de um vocabulário que nasceu na Fase 7 e não se aplica retroativamente,
e a §6 declara essa fronteira. O que muda é que agora está **contado**.

**DEFEITO CONHECIDO, com conserto em commit próprio: o `fase_0.md` não tem
tabela-resumo, e o pulo 0→1 se anuncia com o motivo errado.** A §6 daquele
registro é prosa em subseções `### P<n> —`, sem tabela nenhuma; `_localiza` para
no primeiro `##` e devolve `None` antes de ver qualquer `|`. É por isso que o
contador diz `com tabela-resumo, conferidos: 7` de oito. Mas a mensagem do pulo é
**uma string só**, e ela afirma *"a tabela-resumo da fase 0 não declara coluna de
estado (tabela de três colunas)"* — descrição verdadeira para os registros 1 a 5 e
**falsa** para o 0. O pulo se anuncia, que é o que importa; anuncia-se com a causa
errada, que é o defeito. **Registrado aqui e não consertado agora**: mexer em
`scripts/` dentro do commit que registra a varredura é o acoplamento que este
repositório recusa desde a regra de `spec-change` separado.

**O mecanismo lê `fase_N.md` e nada mais, e isso é desenho.** Obrigação endereçada
a uma fase que mora em **registro executável** — o caso medido é
`scripts/check_secoes_de_seguranca.py:213`, entrada `5` com
`destinatario=(7, …)` — é **inalcançável** por ele. Não é buraco a tapar: o
predicado responde *"a pauta escrita chegou inteira?"*, e registro executável não é
pauta escrita. O que a fronteira exige é que ela seja dita, porque um verificador
que cobre uma superfície é lido como cobrindo todas.

**O vocabulário da varredura, declarado para que a próxima saiba o que ela não
procurou:** pack, `ground_truth.yaml`, `GM_NOTES.md`, `range-cli`,
`schema_version`, branching, materialização de cenário. **O quinto achado não veio
desse predicado** — veio por **rastro**, seguindo uma pendência já fechada
(a P4-12) até o mecanismo em que o conteúdo dela sobreviveu. É a **P7-7**, e o
modo como ela foi achada é a evidência de que o predicado por vocabulário não
alcança o que não está em registro de fase.

### 2.5 O que a peça 2 herda — quatro pendências, e não nenhuma

> **CORRIGIDA.** A redação anterior desta seção dizia *"**Nenhum bloqueio.** O pack
> começa limpo"*. A **varredura de abertura da peça 2** — a faixa `fase_0.md` a
> `fase_5.md`, 13.606 linhas, com o predicado ajustado por arquivo à forma de cada
> um — mediu **quatro pendências herdadas endereçadas a esta fase, e nenhuma delas
> estava na §6**. A afirmação era falsa quando foi escrita, e falsa por um motivo
> mecânico: o quarto predicado confere pares **consecutivos**, e o par 5→6 é pulado.
> Pendência endereçada a uma fase que **salta** a seguinte não é alcançada nem
> quando o par existe.

**O que a peça 2 herda, medido:**

| Id | Origem | Estado | O que ela obriga aqui |
|---|---|---|---|
| **P1-7** | `fase_1.md` §"P1-7" — caiu da cadeia no par 1→2 | `ENTREGA` | o pack é quem nomeia inject, e a convenção se decide ao escrevê-lo |
| **P4-8** | `fase_4.md` §"P4-8" | `ABERTA` | nada na peça 2; a segunda perna do gatilho é a medição da peça 7 |
| **P5-4** | `fase_5.md` §"P5-4" | `ENTREGA` | é **o delta do schema**, e portanto pré-condição do que a peça 2 desenha |
| **P5-6** | `fase_5.md` §"P5-6" | `ENTREGA` | o subcomando que escreve o pack em disco |

**As duas da Fase 5 fecham juntas, e a razão está na fonte.** `fase_5.md:1729-1733`
já escreveu o acoplamento: *"a P5-6 é o **produtor** … a P5-4 é o **modelo** … Quem
fechar a primeira sem olhar a segunda escreve um `ground_truth.yaml` que omite dois
conjuntos sem que nada acuse, porque o schema não tem como recusar o que não sabe
nomear."*

**O que continua verdadeiro da redação anterior:** a peça 2 herda **ferramenta** —
a pauta da §6 tem estado legível por máquina, e qualquer pendência que ela fechar
ou abrir passa a ser cobrada pelo predicado no fechamento da fase. E a peça 1 não
deixou bloqueio **de implementação**: o que ela deixou de fora foi a pauta, e é
isto que esta correção repõe.

**A P6-3 é pré-condição da peça 3, e não da 2** — a §1 já a registra assim. A peça 2
pode abrir sem a gramática de `exercise_time`; o que não pode é a peça 3 fechar sem
ela.

## 3. A peça 2 — o pack ganha produtor, e o schema ganha guarda

> **O título mudou no fechamento.** Ele dizia *"a varredura que precede o delta
> do schema"*, e era verdadeiro quando a peça abriu — o primeiro ato foi medir.
> Ficou falso no fim: **não houve delta de schema**, e o que a peça entregou foi
> outra coisa. Título que sobrevive à entrega que o contradiz é a §1.6, e ela é a
> classe que este registro persegue desde a Fase 1.

Quatro itens, cada um commitado em verde. O que segue é o que a auditoria precisa
achar sem reconstruir a cadeia por leitura.

**O que a peça fecha, em uma frase:** o gabarito existia como valor de retorno e
não como arquivo, e as guardas que o protegem existiam como disciplina — passou a
existir em disco, por comando, com o destino e a forma cobrados por mecanismo.

As §§3.1 e 3.2 são da varredura de abertura; as §§3.3 a 3.5, do que a
implementação decidiu e mediu; as §§3.6 a 3.9, o fechamento.

### 3.1 `information_distribution.yaml` fica FORA do pack desta peça, declarado

`04` §1 lista `information_distribution.yaml` entre os arquivos do pacote, e
**nenhum dos contratos o cobre** — é a **P1-20**, aberta na Fase 1 com destinatário
declarado **Fase 10** (`fase_1.md` §"P1-20": *"a assimetria de informação que ele
governa chega na Fase 10"*).

**Ela NÃO ganha linha na §6, e a ausência é decidida.** O critério da varredura
exige destinatário nesta fase ou gatilho que esta fase satisfaça; a P1-20 tem
destinatário Fase 10 e nenhuma condição que a Fase 7 dispare. Transcrevê-la aqui
seria inventar herança, que é o defeito simétrico ao que a §2.5 acabou de corrigir.

**Mas a adjacência é real e fica dita:** o pack completo que esta fase entrega
materializaria um documento de pack que **nenhum contrato reivindica**, e um campo
com erro de digitação ali sai `rc=0` em todos os gates. A decisão desta peça é
**não escrevê-lo** — o `ransomware-universidade` desta fase entrega os documentos
que têm contrato. Isso é limite declarado, não esquecimento, e é o que impede que a
Fase 10 receba um arquivo já em uso e sem forma acordada.

### 3.2 O interpretador do projeto é `py -3.12`, e isso é condição de leitura do gate

Medido nesta árvore:

| | |
|---|---|
| `py -3.12 -V` | **Python 3.12.10** — o interpretador do projeto |
| `python -V` (o do `PATH`) | **Python 3.14.7** — sem PyYAML instalado |

**Não existe venv neste repositório**: não há `.venv`, `venv` nem `pyvenv.cfg` na
árvore. Quem rodar um verificador com o `python` do `PATH` recebe vermelho **de
ambiente**, e vermelho de ambiente lido como vermelho de conteúdo é a pior forma de
falso positivo — ele treina quem o vê a desconfiar do gate em vez do commit. Todo
número desta fase sai de `py -3.12`.

### 3.3 As duas decisões de desenho que nenhuma norma decidia

As duas são desta peça, e ficam declaradas aqui porque a spec não as decide — o
que ela decide é o que elas não podem contradizer.

#### 3.3.1 `range_cli/` é pacote de TOPO, e o invariante 1 é quem decide

`01` §2 lista `range-core/`, `domains/`, `scenarios/`, `contracts/`, `tools/` e
`docs/`. **O CLI não aparece em nenhum.** Medido: `grep -n "range-cli\|cli/"` em
`01_ARCHITECTURE.md` devolve zero. `04` §8 fixa a *superfície* — nome do
executável, grupos, verbos — e não o lugar.

**A escolha não é de gosto: é o invariante 1.** O produtor chama
`domains.<x>.seed.gabarito`, e `tools/check_core_boundary.py` impõe por AST que
`range-core/` não importe nada de `domains/`. Um `range-core/cli/` reprovaria no
primeiro import.

**E a saída que a `academus-api` usa não serve aqui**, que é a parte medida. Em
`range-core/api/processo.py:119` o adapter entra como **dado**: as flags chegam
por caminho de arquivo, lidas com `yaml.safe_load`, e por isso o core nunca
importa o domínio. **Gerador é código.** `gabarito.gerar` é uma função com
comportamento; não há caminho de arquivo que a substitua, e injetá-la por
configuração seria import dinâmico com outro nome — a mesma travessia que o
invariante existe para tornar inexprimível, entrando pela porta que ele não
enxerga.

Então o CLI é **raiz de composição**, no mesmo sentido que `processo.py`, e a
diferença é exatamente essa: aquele consegue ficar dentro do core porque só
precisa de dado do domínio; este precisa de código, e por isso mora fora.

#### 3.3.2 A guarda de destino mora em `range-core/engine/destino.py`

A guarda que pergunta *"este destino é rastreado?"* nasceu em
`tests/fixtures/pack_completo.py`, porque a primeira que precisou dela foi uma
fixture. **Produção não importa de `tests/`**, e o produtor — que é a razão
inteira de ela existir — não a alcançava.

**Copiar seria a D4 dentro do mecanismo que existe para o gabarito não nascer no
lugar errado.** Duas cópias de uma guarda de segurança divergem, e a que diverge
em silêncio é a que ninguém está olhando. Ela mudou de casa, e a fixture passou a
usá-la — restou **uma** implementação e **uma** mensagem.

**Por que `engine/` e não o CLI:**

| | |
|---|---|
| a leitura do pack já mora em `engine/loader/` | esta é a outra metade da mesma pergunta, do lado da escrita |
| ela é agnóstica de domínio | não sabe o que é `academus`, e não precisa |
| não importa `domains/` nem `contracts/` | as duas formas de segmento chegam **por parâmetro**, pela regra de `04` §4.1 — `contract_source.formas_do_destino` as lê uma vez, na raiz de composição |
| **no CLI seria pior** | a fixture de teste passaria a depender do CLI para montar um pacote, e o CLI é superfície, não biblioteca |

### 3.4 Três achados de execução, e o terceiro é variante nova da classe da §7.1

#### 3.4.1 DÉCIMA OCORRÊNCIA: cobertura que não alcança o PONTO DE ENTRADA

**A variante é nova**, e é a que interessa à peça 6.

`materialize` recebia o motor **pronto**, e `main` o montava **antes** de chamá-la.
Consequência: `range-cli scenario materialize Academus x` tentava conectar no
banco **antes** de descobrir que `Academus` não casa a forma do contrato. Pior —
`engine_do_ambiente()` exige um argumento `url` que `main` não passava, então o
comando estourava com `TypeError` em vez de recusar.

**E isso contradizia o cabeçalho escrito no próprio arquivo**, que afirma *"a
ordem dos passos é a garantia: forma dos segmentos, destino não rastreado,
geração, escrita"*. A prosa dizia uma coisa e o `main` fazia outra, a dez linhas
de distância.

**Por que dezessete testes não viram:** eles chamam `materialize` **direto**, e
pulam o `main`. A cobertura alcançava a função e não o **ponto de entrada** — e o
ponto de entrada é onde a ordem de fato acontece.

**Quem achou foi rodar o executável de verdade.** Não o teste, não o gate, não a
leitura: `range-cli --help` e uma invocação com argumento inválido.

**Fechado por mecanismo, e não por lembrança.** `abre_motor` passou a ser
**fábrica**, chamada só depois das guardas — a ordem virou propriedade da
assinatura. E dois testes nasceram: `_MOTOR_PROIBIDO`, uma fábrica que **reprova
se for chamada**, e um que roda `main` inteiro sem `DATABASE_URL` e exige recusa
por **forma**, não por falta de banco.

#### 3.4.2 A perna de ordem de inserção não era redundante, e isso foi medido

O teste de determinismo tem duas pernas: duas materializações produzem os mesmos
bytes, e a ordem das chaves não depende da ordem de inserção. A segunda parecia
redundante.

**Não é, e a violação plantada mostrou por quê.** Com `sort_keys=False`:

| perna | resultado com a violação |
|---|---|
| duas materializações, mesmos bytes | **PASSOU** |
| ordem de inserção não vaza | **FALHOU** |

A comparação de bytes passou porque os dois dicionários eram **o mesmo objeto**,
montado uma vez: a ordem de inserção era idêntica nas duas execuções. Ela só
pegaria o defeito no dia em que dois gabaritos equivalentes fossem montados em
ordens diferentes — e aí o pack seria irreprodutível sem nada ter ficado
vermelho.

É a mesma forma do controle positivo da P6-11: sem a segunda perna, a primeira
prova menos do que parece provar.

#### 3.4.3 `check_readme_atual.py` recusa a contagem em vez de responder errado

`range_cli` entrou no `pyproject.toml` e a instalação editável não foi refeita.
O módulo só resolvia por CWD, e `tests/test_range_cli_materialize.py` deixava de
importar fora dele.

**O verificador não reportou um número quase certo.** Ele reportou:

```
a descoberta de testes acusou erro de carga: ['F']. A contagem nao vale
enquanto isso nao fechar — modulo que nao importa vira um caso de falha e
mantem o total parecido com o certo.
```

O total teria sido **767** em vez de 783: dezessete testes virando um
`_FailedTest`. Diferença de dezesseis num número que ninguém confere de cabeça —
e passaria.

**É a forma certa de guarda, e vale registrar como exemplo:** ela prefere **não
responder** a responder errado. É a mesma direção que `check_progress_consistency`
usa nos pulos, que `check_audit_base` usa na âncora ausente, e a oposta da que
esta linhagem aposentou duas vezes — o verificador que sai `ok` quando não sabe.

E pegou a assimetria de instalação **antes** de custar uma rodada: é a quarta vez
que o `pyproject.toml` a paga, e a primeira em que um verificador a viu.

#### 3.4.4 `git stash` apareceu duas vezes — dado para a P6-6, e não pendência nova

A **P6-6** registra que o sentinela de branch intercepta `Write`/`Edit` e **não**
`Bash`, e nomeia `git stash` como *"esse risco por uma porta que nenhuma das três
formas mapeou"*. Ela era, até aqui, uma observação sem instância.

**Passou a ter duas, as duas nesta sessão:**

| Onde | O que aconteceu |
|---|---|
| spec-change #58 | `git stash push -- contracts/` para separar as duas metades do trabalho, e `git stash pop` depois de trocar de branch. Funcionou, e o `pop` foi conferido |
| conserto da P6-9 | `git stash -u` antes de rodar o lançador — e ele **removeu o próprio conserto**, fazendo a medição rodar a versão antiga. O `grep` da saída voltou vazio, e por um instante pareceu que o conserto não funcionava |

**A segunda é a que interessa**, e ela é exatamente a forma que a P6-6 descreve:
trabalho pensado sobre uma árvore, executado contra outra. Nenhum hook viu —
`git stash` não é `Write` nem `Edit`, e o sentinela nunca foi invocado. O
prejuízo foi de minutos e a medição foi refeita corretamente; o que a torna
registrável é que **o modo de falha ocorreu**, e não que ele tenha custado caro.

**Isto NÃO abre pendência.** A P6-6 já existe, já nomeia `git stash` por nome, e
**vence na Fase 8** — quando o paralelismo começar e várias branches viverem ao
mesmo tempo. O que muda é que ela deixa de ser hipótese: quem for decidir entre
as três formas lá terá **duas ocorrências medidas** em vez de um risco
raciocinado, e a segunda mostra que o dano não precisa de duas branches — basta
uma árvore com trabalho não commitado.

### 3.5 As três variantes da classe da §7.1, medidas nesta peça

A §7.1 mede *"uma exigência é afirmada num lugar e os sítios que a satisfazem não
são varridos quando ela muda"*. **Esta peça produziu três variantes distintas**,
e as três são insumo do desenho da **P7-5** na peça 6 — porque cada uma escapa
por um caminho diferente, e uma allowlist de chamadores por emissor só alcança a
primeira.

| Variante | O caso desta peça | Por que escapa |
|---|---|---|
| **predicado estreito** | a varredura da §2.4.1 procurou quem faz *parse* do JSON da prova e concluiu que o lançador não lê o campo; `start_checkpoint_audit.sh:652` fazia `grep -q` dentro do artefato | a varredura **aconteceu**; o predicado é que não alcançava a forma. `grep` dentro de `.sh` não é import, e o degrau 2 resolve por import |
| **defeito sem sujeito** | `SINCE_SELF` em duas cópias, e o `since: containment_declared` do gerador | ninguém **afirmava** o defeito, então não havia o que varrer. O mecanismo não era varredura: era **derivação** — uma origem só, e a divergência deixa de ser expressável |
| **cobertura que não alcança o ponto de entrada** | §3.4.1 — dezessete testes sobre `materialize`, zero sobre `main` | a exigência estava escrita **no arquivo certo**, e a cobertura era **da função**. Nenhuma varredura de import a alcança: é execução, e a §7.1 já nomeia isso como o degrau 3 |

**O que isso diz à peça 6, e é a parte que ela precisa antes de desenhar:** a
allowlist de chamadores por emissor cobre a **primeira** variante e nada das
outras duas. A segunda se fecha por derivação — e derivação faz a classe deixar
de existir, que é o degrau 1. A terceira é execução, e a §7.1 já registra que
para ela *"o que sobra é a prova de container"*.

**A P7-5 não deve ser desenhada como se cobrisse as três.** Declarar isso agora é
mais barato que descobrir na peça 6 — é literalmente o argumento que a §7.1 usa
sobre a sexta ocorrência.

### 3.6 O que foi entregue, por item

| # | Item | O que fecha |
|---|---|---|
| 1 | esqueleto de migração e recusa por versão | `SUPPORTED_SCHEMA_VERSIONS = (2,)` com a assimetria **decidida** e não pendente; a recusa passa a **instruir** em quatro perguntas — o que o pack declara, o que o engine aceita, o que fazer, e o inverso se a versão for **futura**. A quarta perna não estava prevista e é defeito real: sem ela a mensagem mandaria rebaixar um pack `v9` |
| 2 | `SINCE_SELF` com uma origem só | as **duas** cópias eliminadas, 19 sítios (5 de produção, 14 de teste). O valor vem do contrato e desce por construtor até `Mundo`; os 38 sítios de `avalia(` não mudaram |
| 3 | `range-cli scenario materialize` | o produtor do par, com **determinismo provado em três pernas** e recusa de destino versionado perguntando ao `git` — não ao `.gitignore`, que `git add -f` atravessa |
| 4 | o linter de citação de fato | `GM_NOTES.md` com fato ausente ou em forma não casada recusa **na carga**, com sítio próprio |

**As duas medições que mais mudaram o trabalho** não estão na tabela porque não
são entrega, e sim o que a tornou possível: a varredura de abertura (§2.4.1),
que achou quatro pendências herdadas que ninguém havia transcrito, e a medição
do delta v3 (§3.5 do relatório de então), que mostrou que **não havia delta**.

### 3.7 O que a peça NÃO fechou, e cada ausência tem razão medida

**Nenhum dos três lados de citação tem artefato de PRODUÇÃO.** O que existe é o
pacote materializado por `pack_completo.materializa()`, carregado por `load_pack`
pelos seis passos do boot — **melhor que dicionário de teste, pior que artefato
de produção**. As três razões, medidas:

| Lado | Por que não há artefato |
|---|---|
| `GM_NOTES.md` | `scenarios/` está vazio. O produtor existe, e materializar exige o banco semeado; a senha está no `.env`, que é caminho negado |
| `materializes_facts` | `tests/fixtures/pack_minimo/injects.yaml` não traz o campo |
| `projects_facts` | não há `MANIFEST.json` na árvore; `evidence build` é da Fase 9 |

**A lição do PR #57 continua valendo e está declarada na suíte:** lá, quatro
testes corretos julgavam árvores montadas à mão, e o gerador de produção — que
escrevia `since: containment_declared` — nunca passava por nenhum deles.

---

**"v1 migra automaticamente" fica como esqueleto declarado, e a divergência com a
redação do DONE 7 é dita aqui de propósito.**

Medido com `git log --all --diff-filter=A --name-only -- 'contracts/scenario.schema*'`:
**nenhum contrato anterior ao v2 jamais existiu** neste repositório. O único
arquivo que o comando devolve é `scenario.schema.v2.yaml`, em `31ddcfa`. O
migrador existe como **registro** e nunca correu contra transição real.

**O item é satisfeito pela forma normativa, e não pela literal.** `06` T12 escreve
o critério em **N**: *"pack em `schema_version` N-1 carrega com migração e aviso;
anterior a N-1 é recusado com instrução"*. O DONE 7 de `07` o instancia como
*"pack em schema v1 migra automaticamente; v0 é recusado com instrução"* — e o
`v1` literal pressupõe uma versão que nunca existiu.

**Sem esta declaração, quem ler o critério no fechamento da fase encontra um item
que não confere** — e a saída errada seria escrever um `v1_to_v2.py` identidade
para fazer a linha passar. Migrador identidade faz o item de DoD passar, faz o
teste dele passar, e não transforma nada: o gate ficaria verde sobre mecanismo
nunca exercido, e a primeira transição de verdade encontraria o caminho
"provado" e errado.

---

**A P5-4 saiu da fase, e ela está MAL FORMULADA na origem.**

Ela nomeia **dois** conjuntos fora do enum — ruído de manutenção e credenciais
compartilhadas. Medido em `domains/academus/seed/gabarito.py`, o gerador percorre
**três**:

```python
for nome in ("ruido_de_manutencao", "credenciais_compartilhadas", "legitimos_normais"):
```

**`legitimos_normais` é o terceiro, e ele é diferente dos outros dois.** `02` §6.2
atribui `defensibility` a **cinco** famílias — 1.0 indevido, 0.5 ambíguo, 0.0
*"legítimo (inclusive os de aparência suspeita, manutenção e delegação)"* — e
**não menciona legítimos normais**. A spec, portanto, **não decide** se o sexto
conjunto é caso.

**A pergunta do sexto conjunto não está formulada em pendência nenhuma.** Não é
que a P5-4 a responda mal: ela não a faz. E ela não cabe na P5-4 sem reescrevê-la,
porque a P5-4 é sobre conjuntos que *têm* `defensibility` e não cabem no enum, e
este não tem. Fica registrado aqui, e quem retomar a P5-4 precisa decidir se abre
a segunda.

---

**A P1-7 foi medida e não fechou** — o produtor não nomeia inject nenhum. O
detalhe está na §6, com a medição; aqui fica só o ponteiro, porque fechar por
estar na lista da peça seria marcar como entregue uma decisão que ninguém tomou.

### 3.8 O que a peça 3 herda — e a fronteira da P6-3, medida

**A gramática de `exercise_time` é a peça 3**, e a **P6-3** segue `ENTREGA` com os
três gatilhos herdados intactos.

**A pergunta que a peça 2 tinha de responder antes de passar adiante:** o produtor
escreve `exercise_time` no `ground_truth.yaml` (`gabarito.py:182`, `quando.isoformat()`).
**Isso ativa algum dos três gatilhos?** Medido, e a resposta é **não** — nos três:

| Gatilho | Medição | Ativa? |
|---|---|---|
| o primeiro pack que precise de folha temporal | `confere_folhas_temporais` sobre o pack produzido **passa**: `predicados_de_verificacao()` tem só `absence_of` com `since: self`, e nenhum `before`/`after` | **não** |
| a implementação do suporte temporal | não foi feita nesta peça | **não** |
| o primeiro produtor de `fact_materialized` | `FACT_MATERIALIZED` tem **dois** usos em produção — o import em `verificacao.py:58` e uma **leitura** em `:333`. Nenhum `append` | **não** |

**A distinção que decide o terceiro, e ela é de espécie:** *declarar um fato no
pack não é produzir o fato*. O `exercise_time` que o produtor escreve é **campo de
`facts` no `ground_truth.yaml`** — dado de gabarito, camada 1. O produtor de
`fact_materialized` é o **motor em runtime**, emitindo evento quando o fato passa
a existir no mundo simulado. São camadas diferentes de `00` §3, e confundi-las
seria a mesma confusão de espécie que pôs um `event_type` no lugar de um
qualificador de instante e derrubou a carga do pack no PR #57.

**Consequência para a peça 3, dita para que ela não herde dúvida:** ela abre com
os três gatilhos **intactos**, e não com gatilho vencido. `Mundo.fatos` continua
vazio em produção — nada emite o evento —, e `SemGramaticaTemporal` continua
inalcançável na árvore. A escolha normativa que a P6-3 cobra (contra o que o
predicado temporal compara — `exercise_time`, `exercise_timestamp` ou marca de
parede) segue sem caso de uso à vista, e a peça 3 a toma por decisão e não por
pressão de defeito.

### 3.9 O custo, medido — e é fato sobre o método

| | |
|---|---|
| rodadas de medição antes de qualquer código | **cinco** |
| PRs próprios contra `main` | **três** — #57 (conserto do `since` do gerador), #58+#59 (spec-change e contratos), #60 (spec-change do caminho e do produtor) |
| rebases da branch, e âncoras regravadas | **cinco** de cada |

**O desenho da D2 mudou três vezes, e cada mudança veio de medição:**

| Desenho | O que o derrubou |
|---|---|
| **(a)** `v2 -> v3` com a P5-4 | a medição do delta: promover os dois conjuntos a caso muda a `fact_class` dos fatos que os sustentam, e com ela o predicado de contenção — que decide TTCV e TTRV. Não é expansão de enum; é mudança de semântica de verificação |
| **(a')** o aperto de `since` como delta | `03` §3.1 já fixava `self` desde o `spec-change` #49, e a guarda de carga já recusava o resto. Nenhum pack válido de ontem deixou de ser válido — alinhamento, não transformação |
| **(c)** sem delta disponível | o que sobrou, e o que a peça entregou: mecanismo construído e **declarado** como nunca tendo corrido contra transição real |

**Isto é registro sobre o método, e não queixa.** O desenho foi feito **por
descoberta**: cada uma das três formas parecia certa até a medição seguinte, e
nenhuma caiu por argumento — todas caíram por número. Três PRs contra `main` no
meio de uma peça não é sinal de peça mal planejada; é o preço de o repositório
recusar norma e mecanismo no mesmo PR, e a alternativa seria um PR que o
`spec_freeze` reprova.

**E funcionou porque a árvore tem registro denso.** Cada uma das três derrubadas
se apoiou em algo escrito antes por outra pessoa ou outra fase: a P5-4 tinha o
custo das duas alternativas medido no `fase_5.md`; o `since` tinha o `spec-change`
#49 explicando o que ele decidiu; a ausência de contrato v1 saiu de `git log`,
que é registro que ninguém escreveu de propósito. **Sem esse registro, as três
formas teriam sido decididas por plausibilidade** — e a (a) e a (a') são as duas
mais plausíveis.

## 4. A peça 3 — o linter ganha superfície, posição e colheita

**Os três critérios DONE desta peça já recusavam antes dela**, e a peça começa
dizendo isso porque é o que define o que ela de fato entregou.

| DONE | Quem já recusava | Prova negativa no contrato |
|---|---|---|
| 1 — inject sem `objectives` e sem `noise: true` | `if/else` em `#/$defs/inject`, camada 1 | existia |
| 2 — `event_type` inexistente em condição de branch | `x-aurora-ref: event_catalog`, camada 2 | **não existia** |
| 3 — condição por juízo do facilitador | `branch_condition` com `oneOf` fechado e `additionalProperties: false` | existia |

A ausência da fixture do DONE 2 foi medida na abertura: as únicas negativas de
`event_catalog` na árvore eram de `objectives.schema.yaml` e de
`ground_truth.schema.yaml`. **A regra que `04` §6.2 chama de "falha mais cara
possível" não tinha prova no contrato que a declara.** Ela tem agora, e o valor
plantado é `vpn_acess_revoked` — o nome certo com um `c` a menos, que é a forma
real do defeito. Fixture com `evento_que_nao_existe` provaria a regra contra um
caso que ninguém comete.

### 4.1 O que a peça entregou, e o delta é de três espécies

| # | Entrega | O que ela fecha |
|---|---|---|
| 1 | `range-cli scenario lint <path>` | a superfície: o CLI só tinha `materialize`. Terceiro chamador da mesma validação, por `varre_pack` |
| 2 | **posição no arquivo** | `branches.yaml:10:22`, o que `06` T12 cobra **duas vezes** e o que nada produzia |
| 3 | **colheita** | os passos viraram lista com dois consumidores: o boot para no primeiro, o linter colhe todos |
| 4 | `t_relative` fora de ordem | regra declarada em `x-aurora-linter-rules` desde a Fase 1, sem mecanismo |
| 5 | `fact_check_against` que não resolve | idem |
| 6 | `x-aurora-linter-rules` com leitor | `scripts/check_regras_do_linter.py` + probes |
| 7 | ausência de IOC no gabarito | a **P7-7**, cujo gatilho declarado era esta peça |

### 4.2 A posição, e por que ela não é o caminho de instância

As duas camadas de validação já produziam **caminho**: `jsonschema` devolve
`e.json_path`, a `AuroraChecker` devolve o `ipath` dela, e — conferido, não
suposto — **no mesmo dialeto**: `$` na raiz, `.chave`, `[i]`. É isso que permite
um resolvedor só servir às duas.

Caminho é posição no **documento**. `linha:coluna` é posição no **arquivo**, e é
a que o critério cobra, porque é a que o autor cola no editor. Quem lê
`$.branches[0].evaluate[0].when.all[0]` conta braços a mão; quem lê
`branches.yaml:10:22` abre no lugar.

**As duas leituras são dos mesmos bytes, e isso é a garantia.**
`parse_document_com_texto` devolve documento e texto de uma leitura só, e
`MapaDePosicoes` compõe a árvore de nós sobre aquele texto. Reler o arquivo
abriria janela entre as duas, e nela a posição passaria a apontar para um arquivo
que **não é o que foi validado** — erro pior que posição ausente, porque parece
certo.

**A coluna aponta para o VALOR, e não para a chave**, e há teste próprio para
isso: `04` §6.2 diz que o erro de digitação faz a branch não ramificar, e quem
conserta precisa do cursor sobre o nome errado, não sobre o `event:` que está
certo.

**O fallback se declara.** Caminho que não resolve exato devolve a posição do
ancestral mais profundo, com `exata=False` e o caminho até onde resolveu; o
relatório marca a linha com `~`. Cair para o ancestral em silêncio apontaria uma
linha errada com a mesma confiança de uma certa — e a exigência de T12 é sobre
**localizar**, então localização que mente é pior que a ausência dela.

### 4.3 A colheita, e por que ela não é escopo inventado

`04` §8 dá nomes e listas de checagem **distintos** a `validate` e a `lint`. Um
linter que relatasse um defeito por execução mandaria o autor consertar e rodar
de novo — seis vezes, num pack de seis documentos. Nesse regime o verbo `lint`
não acrescentaria nada ao `validate`, e a spec não teria por que ter os dois.

A colheita **não é uma segunda implementação**, e essa era a armadilha. Os passos
de recusa passaram a ser uma lista — `_passos` — com dois consumidores:

```
load_pack   roda em ordem e para no primeiro que levantar   (comportamento intacto)
varre_pack  roda a mesma lista colhendo todos               (o linter)
```

Duas listas seriam o gate aceitando pack que o boot recusa, com outro nome — a
classe que a §1.4 do checkpoint da Fase 2 fechou em `contract_rules`.

**A granularidade passou a ser por documento** nas duas camadas de contrato. Para
o boot é indiferente, porque ele para no primeiro; para o linter é o que faz um
`injects.yaml` defeituoso não esconder o `branches.yaml` ao lado.

**O que NÃO é colhido são as recusas de `_abre`** — diretório, `manifest.yaml`
ausente, documento ilegível. Elas sobem, e a razão é de espécie: um passo da lista
julga o **conteúdo** do pack; estes três decidem se **há** pack. Colhê-los seria
relatar achados sobre documentos que não foram lidos.

### 4.4 `t_relative` fora de ordem é POR LINHA, e a diferença foi medida

`04` §9 manda o `ransomware-universidade` ter *"Linhas A + B + ruído"*, e linhas
correm em paralelo no relógio do exercício. **Sob ordem global, o exemplo
positivo de `injects_document` do próprio contrato seria recusado**: ele declara
`00:47, 00:55, 01:10, 01:15, 01:40` na linha A e `00:52` no inject de ruído, que
não tem `linha`. Regra que reprova a fixture válida do contrato que a declara é
regra escrita contra a fonte — a classe do B4 da terceira auditoria.

**O que a regra NÃO é: garantia de disparo.** `inject_engine` ordena por
`(t_relative_seconds, id)` e dispararia certo de qualquer jeito. A recusa é sobre
**autoria** — um `01:50` digitado onde se queria `00:50` dispara na hora errada
sem nada falhar, e a ordem do arquivo é o único sinal que sobra.

**Na carga também, e não só no linter.** Regra que o `lint` recusasse e o boot
aceitasse produziria pack reprovado pelo CI e carregado pelo engine. Vale para as
três regras novas desta peça.

### 4.5 O registro do linter tinha zero leitores, e já havia envelhecido

`x-aurora-linter-rules` declarava sete validações a cargo do
`range-cli scenario lint`, e **nenhum código o lia**. É literalmente o M1 da
terceira auditoria — *"registro ignorado é prosa marcada como contrato"* —, no
mesmo arquivo em que aquele achado já custou o `_verify_completude` do B1 da
Fase 6, num registro vizinho.

**E ele já mentia.** A medição regra a regra, na abertura:

| Regra declarada | Estado medido |
|---|---|
| `branch_policy` aplicada | peça 4 |
| `option` existe no `decision_point` **indicado** | **parcial** — `x-aurora-ref: pack_decision_options` prova existência global, não a do DP irmão |
| `t_relative` fora de ordem | **sem implementação** |
| `control_function` não é produto | declaradamente não mecanizável |
| `GM_NOTES` com fato ausente | entregue na peça 2 |
| `fact_check_against` resolve | **sem implementação** |
| `required_rubrics` cobre objectives.yaml | **já mecanizada**, e a linha dizia o contrário |

Cada entrada passou a ter `id`, `rule`, e **ou** `mecanismo` **ou**
`destinatario` + `motivo`. O `sitio`, quando há, é conferido contra `PackSite`
por AST: sítio renomeado derruba o gate em vez de virar entrada morta.

**O limite é declarado, e é real:** a direção inversa não é coberta. Obrigação
que `04` §8 enuncie e que ninguém tenha transcrito para o registro continua
invisível — aquela lista é prosa corrida, e não há o que derivar dela. O
verificador julga se cada entrada **tem dono**, não se as entradas são todas as
que deveriam existir. Mesma forma do `check_gate_coverage.py`.

### 4.6 A P7-7 fechou, e medi-la mostrou que eram TRÊS exigências

A pendência cobrava *"o verificador do ator declarado"* como se fosse uma coisa.
`05` §5.2 tem três, com três destinos diferentes:

| Exigência | Destino |
|---|---|
| fonte pública citável | **meia** — o contrato exige `sources` não vazio; *"citável"* não é forma. `sources: [confia em mim]` casa o schema. Mesma classe do `control_function` |
| TTPs não excedem o público na fonte | **não mecanizável** — o julgamento é contra documento **externo**, e nenhum verificador daqui tem como lê-lo |
| nenhum IOC operacional | **mecanizada** |

Fundir as três numa entrada faria o mecanismo da terceira cobrir as duas
primeiras em silêncio. Elas são três entradas do registro, e as duas primeiras
declaram `destinatario: revisão humana`.

**A terceira não foi reimplementada, e é aí que está a decisão.** *"Este valor é
dado sintético?"* é a mesma pergunta que `tools/check_synthetic_data.py` responde
desde a Fase 0. O que faltava não era a resposta — era um **segundo chamador**:
aquele verificador varre a **árvore versionada**, e `scenarios/` está fora do Git
desde a peça 5 da Fase 5, então o pack nunca passou por ele.

O predicado saiu para `dados_sinteticos/`, pacote de topo e stdlib puro, com três
chamadores: o verificador da árvore, o linter de pack, e
`scripts/check_contract_examples.py` — que já comparava as faixas do contrato com
as aplicadas e **quebrou alto** no movimento, que é o comportamento certo.

**Por que de topo, e não em `tools/` nem em `range-core/`.** Os dois chamadores
principais vivem em mundos diferentes: `tools/` roda no job `arquitetura`, que
**não instala nada**; `range_cli` e `range-core` rodam instalados. Em `tools/`, o
`range-cli` instalado ficaria sem ele — `tools` não está em `packages` —, que é a
assimetria que o `pyproject.toml` declara ter pago três vezes. Em `range-core/`,
`tools/` passaria a importar a aplicação, que é o que a pureza daquele job existe
para impedir.

**E a assimetria cobrou na hora:** com o pacote novo em `packages` mas a
instalação editável desatualizada, `check_readme_atual.py` passou a contar 550
testes em vez de 835, com três falhas de carga. O número **parecia plausível** —
que é exatamente o modo de falha que o próprio verificador descreve na mensagem
dele. Fechou com `pip install -e .`.

**O limite da terceira, medido e com teste próprio: domínio embutido em PROSA
escapa.** O predicado classifica valores, e `hostnames_candidatos` desiste quando
o texto tem espaço — `note_to_facilitator: "C2 em evil-infra.net"` **passa**.

Não estender a varredura para prosa foi decisão, nesta ordem: mudar isso mudaria
o comportamento de `check_synthetic_data.py` sobre a **árvore inteira**, dentro de
uma peça que não pediu isso; e rede larga sobre prosa produz falso positivo em
volume, que é como um gate deixa de ser lido. **Há teste que afirma o limite**, e
ele fica vermelho no dia em que alguém o fechar — que é o aviso certo.

**`threat_actor.sources` é isento da varredura, e é o único.** A §5.2 **exige**
fonte pública citável ali, então `attack.mitre.org` numa `sources` é **citação**;
o mesmo domínio num `source_ip` seria **infraestrutura**. A varredura não
distingue as duas e não tem como. A isenção é de **subárvore**, e não de valor:
isentar por valor faria o mesmo domínio passar em qualquer lugar do documento.

### 4.7 Dois gates estavam VERMELHOS, e não por causa desta peça

Achados ao rodar a varredura de verificadores, e os dois mudam o quadro com que
esta peça abriu.

| Gate | Desde | Causa |
|---|---|---|
| **D16** — `check_allowlist_do_auditor.py` | `8751c77`, **peça 1** | `check_progress_consistency_probes.py` nasceu e não entrou na allowlist do auditor |
| **P37** — `check_gate_coverage.py` | **peça 2** | `range_cli/` nasceu como pacote de topo e nunca foi classificado para o `spec_freeze` |

**Os dois dispararam, e o vermelho não foi lido.** O P37 é o mais duro: a
mensagem dele é literalmente *"diretório novo no topo nasce invisível ao gate, e
nada avisa"*. Avisou.

**São a décima primeira e a décima segunda ocorrências da classe da §7.1, e são
uma variante que aquele mapa não tinha.** As dez anteriores são de exigência
afirmada e não varrida; estas duas são de **mecanismo que disparou e cujo sinal
ninguém leu**. O degrau 1 — derivação em vez de afirmação — não as alcança: a
derivação existia e funcionou. O que falha é a leitura.

O D16 tem agravante próprio: a allowlist do auditor **já tinha** a regra escrita,
e o comentário do `check_audit_base_probes` no mesmo arquivo registra a mesma
falha da quarta auditoria da Fase 3 — *"prova negativa que fica fora da allowlist
no commit que a cria"*. A regra estava escrita, ao lado, e não segurou.

Os dois foram consertados nesta peça. **A varredura de verificadores passou a ser
passo de fechamento de peça, e não de fechamento de fase** — foi ela que os achou,
e ela custa um comando.

### 4.8 O que a peça NÃO fechou

**`lint` não roda no CI, e `04` §8 diz que deveria.** Não há pack lintável na
árvore: `scenarios/` está fora do Git e `tests/fixtures/pack_minimo` é
deliberadamente incompleto — o linter o recusa, corretamente, por
`incomplete_pack`. Um step apontado para uma fixture que o linter não pode julgar
seria gate verde sobre ausência. Registrado como **P7-9**.

**A metade "no `decision_point` indicado"** da regra do `option` continua sem
mecanismo, e agora está declarada como parcial no registro do contrato, com
destinatário peça 4 — é lá que a árvore de `when` é interpretada.

**`range-core` passou a importar um pacote de topo que nenhuma guarda enxerga.**
`check_core_boundary.py` só opina sobre `domains/`; `check_core_contract_imports.py`
só sobre `contracts/`. É a P2-15 um nível acima, e virou **P7-8**.

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
| P1-7 | o id do inject pode vazar a linha, e o contrato só desacoplou o prefixo — herdada da Fase 1, §"P1-7"; caiu da cadeia no par 1→2 | `ENTREGA` | **NÃO fechou na peça 2** — o produtor escreve `ground_truth.yaml` e `GM_NOTES.md`, e nenhum dos dois nomeia inject. Medido; ver abaixo |
| P4-8 | o caminho de leitura é síncrono dentro do laço de eventos: serializa hoje, e bloqueia em volume — herdada da Fase 4, §"P4-8" | `ABERTA` | a segunda perna do gatilho é a medição da peça 7 desta fase; ver abaixo |
| P5-2 | a trilha do Academus declara a categoria "declarações do exercício" e ela não tem produtor | `ABERTA` | a primeira ação de participante que altere estado de domínio; ver abaixo |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores de `line_b_case.set` — herdada da Fase 5, §"P5-4" | `ENTREGA` | peça 2 desta fase — é o delta do schema v3; ver abaixo |
| P5-6 | ~~o gabarito é produzido e julgado em memória, e nada o escreve em `scenarios/`~~ — herdada da Fase 5, §"P5-6" | `RESOLVIDA` | o gatilho declarado ocorreu: `range-cli scenario materialize`, na peça 2. A outra metade fechou no PR #57; ver abaixo |
| P6-2 | `observable_impact` não existe em contrato nenhum, e é o *start* de `TTA` — herdada da Fase 6, §"P6-2" | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; ver abaixo |
| P6-3 | `before`, `after` e a comparação de `since` dependem de uma gramática de `exercise_time` que não existe — herdada da Fase 6, §"P6-3" | `ABERTA` | os TRÊS gatilhos herdados da Fase 6, intactos: o primeiro pack que precise, a implementação do suporte temporal, e o primeiro produtor de `fact_materialized`. Medidos um a um no fechamento da peça 2 — nenhum disparou; ver abaixo |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança, resolvida no fechamento do escore | `ENTREGA` | mudança de contrato agendada para esta fase; ver abaixo |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e **não** `Bash` — herdada da Fase 6, §"P6-6" | `LATENTE` | a primeira sessão que trabalhe em duas branches, ou a Fase 8, o que vier primeiro — o literal ocorreu no trabalho da P7-2 sem que o defeito aparecesse; ver abaixo |
| P6-7 | rota que declara `emite` e não chama emissor nenhum — a metade do fluxo continua aberta; herdada da Fase 6, §"P6-7" | `ABERTA` | a próxima rota que declare `emite` em serviço cuja fábrica já constrói o produtor, ou a Fase 8, o que vier primeiro; ver abaixo |
| P6-8 | justificativa ausente devolve `409`, e `409` é reservado a recusa de estado — herdada da Fase 6, §"P6-8" | `DECIDIDA` | a medição dos consumidores, ou a Fase 10, o que vier primeiro; ver abaixo |
| P6-9 | ~~a cópia instalada do hook do auditor não é sincronizada por ninguém~~ — herdada da Fase 6, §"P6-9" | `RESOLVIDA` | o lançador passou a sincronizar as três cópias antes de abrir a sessão — PR #61; ver abaixo |
| P6-11 | payload cru alimenta o Brier: `confidence: 900` produz escore 64,0 | `RESOLVIDA` | venceu na L1 da terceira auditoria da Fase 6; conserto no PR #54; ver abaixo |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção: `sub == persona`, e `actor_id` vira função da persona | `ABERTA` | a palavra do proprietário entre as saídas (a) e (b); ver abaixo |
| P6-13 | dezesseis violações plantadas declaradas na §3.5 da Fase 6 são atestação do autor, e não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável, ou a primeira vez que alguém precise da cobertura que a tabela declara; ver abaixo |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual das três linhas esta fase entrega; ver abaixo |
| P7-2 | todo fechamento de fase por rebase-merge invalida as provas amarradas ao SHA — é estrutural do rito | `RESOLVIDA` | implementada no PR #56, pela saída (b): a prova nomeia a árvore; ver abaixo |
| P7-3 | ~~a prova amarrada à árvore não cobre o pack materializado, que está no `.gitignore` desde a Fase 5~~ | `RESOLVIDA` | deixou de ser buraco e virou invariante na peça 2: o pack é determinista com prova negativa, e a escrita recusa destino versionado perguntando ao `git`; ver abaixo |
| P7-4 | todo consumo de `event_type` por selecionador sem allowlist declarada — a mesma pergunta com duas respostas | `ABERTA` | **Fase 12** — allowlist por tipo, degrau 1.5. O gatilho é a fase, e NÃO a próxima ocorrência; ver abaixo |
| P7-5 | os chamadores de cada emissor não são varridos quando o contrato do emissor muda | `ABERTA` | **Fase 12** — allowlist de chamadores por emissor, degrau 2. O gatilho é a fase, e NÃO a próxima ocorrência; ver abaixo |
| P7-6 | 44 `audit_*.md` de 14 a 23/ago/2026 nunca foram varridos por destinatário: achado de auditoria não promovido a pendência não está em `fase_N.md`, e nenhum predicado o alcança | `ABERTA` | fechamento desta fase; ver abaixo |
| P7-7 | ~~`05` §5.2 exige ator de ameaça com fonte pública citável declarada em `ground_truth.yaml`, e o verificador do ator declarado não existe~~ | `RESOLVIDA` | o gatilho declarado era a peça do lint, e ela chegou. Medi-la mostrou **três** exigências, não uma: a de IOC ganhou mecanismo, as duas outras ganharam `destinatario: revisão humana` com motivo; ver abaixo |
| P7-8 | `range-core/` importa `dados_sinteticos`, e nenhuma guarda enxerga import de pacote de topo que não seja `contracts/` — é a P2-15 um nível acima | `ABERTA` | o segundo pacote de topo que o core importar, ou a Fase 12; ver abaixo |
| P7-9 | `04` §8 diz que `lint` roda no CI, e não há pack lintável na árvore versionada | `ABERTA` | o primeiro pack lintável versionado, ou a Fase 12 com a documentação; ver abaixo |

#### P1-7 — o id do inject pode vazar a linha, e quem decide é quem escreve o pack

**Herdada da Fase 1** (`docs/progress/fase_1.md`, §"P1-7"), e ela **caiu da cadeia
no par 1→2**: o destinatário declarado era a Fase 3, e nem `fase_2.md` nem
`fase_3.md` a transcreveram. Busca por `P1-7` em `fase_2.md` … `fase_7.md` retorna
zero. Ficou cinco fases sem destino, e quem a achou foi a varredura de abertura
desta peça.

**O fato.** O padrão antigo `^[A-Z][0-9]{2}$` sugeria — pelo exemplo `id: A07` /
`linha: A` de `04` §5 — que a letra do id acompanha a linha. Duas consequências,
e a segunda é a que importa: se a letra codifica a linha, **o id vaza a linha**, e
`03` §5.2 exige que o operador não enxergue que existe Linha B, sob pena de
destruir o efeito de triagem sob viés. O operador vê a fila.

**O que a Fase 1 consertou, e o que ela não podia consertar.** O contrato passou a
declarar o prefixo **sem semântica de linha**, o que fecha a metade de schema. A
metade que sobrou está escrita na fonte: *"se a API da Fase 3 entregar o id do
inject ao operador, **e os packs continuarem nomeando por linha por hábito**, o
vazamento volta pela porta dos dados."*

**Por que ela é ENTREGA desta fase.** A primeira metade do gatilho já ocorreu — a
Fase 3 entregou a API e a Fase 4 a superfície. A segunda metade é sobre **os
packs**, e esta fase escreve o primeiro pack real (`04` §9). Não há como escrever
`injects.yaml` sem escolher a convenção de id, e escolher por hábito é exatamente
o que a pendência prevê.

**ELA NÃO FECHOU NA PEÇA 2, e a §2.5 previu que fecharia.** A previsão dizia *"o
pack é quem nomeia inject, e a convenção se decide ao escrevê-lo"* — e o que a
peça 2 entregou não escreve inject nenhum. Medido antes de mexer no estado:

| Medição | Resultado |
|---|---|
| arquivos que `materialize` escreve | **dois** — `ground_truth.yaml` e `GM_NOTES.md` (`range_cli/cli.py:56-57`) |
| chaves do `ground_truth` que o gerador produz | `facts`, `line_b_cases`, `verification_predicates` — nenhuma é inject |
| ocorrências de `inject` no gerador, no produtor e na guarda de destino | **zero** |

**A previsão errou o objeto, não o momento.** `injects.yaml` é conteúdo de
cenário, e conteúdo de cenário é do `scenario-designer` — que só pode escrever em
`scenarios/`, por hook. O produtor materializa o **gabarito**, que é projeção do
dataset semeado; ele não tem inject a nomear porque a Linha B não tem injects.

**Ela fica `ENTREGA` e o gatilho fica**, porque a fase ainda escreve o pack
completo `ransomware-universidade` — que tem Linhas A + B + ruído e, aí sim,
`injects.yaml`. **Fechá-la aqui por estar na lista da peça 2 seria marcar como
entregue uma decisão que ninguém tomou** — e é a classe que o registro da Fase 6
mede na §1.6: afirmação que nasce de expectativa e não de medição.

**A alternativa que NÃO se deve escolher:** confiar no contrato. Ele desacoplou o
padrão, e padrão permissivo não impede ninguém de escrever `A07` para a Linha A e
`B03` para a Linha B — que valida e vaza.

#### P4-8 — o caminho de leitura é síncrono, e a segunda perna do gatilho é a peça 7

**Herdada da Fase 4** (`docs/progress/fase_4.md`, §"P4-8"), reconfirmada sem
mudança na Fase 5 (`fase_5.md:1726`, *"herdadas da Fase 4, sem mudança —
inalterados"*) e **ausente de `fase_6.md` e desta §6 até agora**. Como a P1-7, ela
sobreviveu por estar num inventário que o predicado não lê.

**O fato.** `GET /wallboard/state` é `async def` com corpo **síncrono**: a corrotina
roda até o fim sem ceder o laço de eventos. Isso tem duas faces, e a primeira é
benigna — é ela que faz 20 leituras simultâneas sobre cache frio produzirem **uma**
reconstrução, e é assim que a P3-2 fechou. A segunda é que a mesma síncrona segura
o laço inteiro durante a reconstrução: a 150 mil eventos são **2,874 s** (§3.8 da
Fase 2) em que nenhuma outra rota responde, **inclusive os dois canais de
WebSocket**.

**O gatilho, literal:** *"a primeira das duas que ocorrer: um deploy com mais de um
worker, ou **o primeiro volume de eventos em que a reconstrução passe de uma fração
do orçamento de 1 s**"*.

**Por que ela chega a esta fase, e por que NÃO é entrega da peça 2.** A segunda
perna é **a medição do item 9 da DoD desta fase** — reconstrução completa da
projeção do exercício de 4 h do `ransomware-universidade`, cobrada em **< 3 s**. É
a peça 7 que produz esse número, e é ele que dispara ou libera o gatilho. Os dois
instrumentos que a pendência nomeia — `scripts/mede_cache_frio.py` e
`scripts/bench_reconstruction.py` — já existem, e por isso a medição não custa
desenho novo.

**O que a peça 7 tem de fazer com ela, dito agora para não ser decidido no aperto:**
o número dos 3 s não responde sozinho. `< 3 s` satisfaz a DoD **e** pode já ter
passado da fração de 1 s que este gatilho nomeia — as duas afirmações convivem, e
ler só a primeira fecharia a DoD deixando a pendência vencer em silêncio.

**Vence em:** a medição da peça 7, **ou** um deploy com mais de um worker, o que
vier primeiro. A saída não é single-flight — com um worker não há voo concorrente,
e com N workers single-flight dentro do processo não resolve nada entre processos.

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

#### P5-4 — seis conjuntos, três valores de enum: é o delta do schema

**Herdada da Fase 5** (`docs/progress/fase_5.md`, §"P5-4"), com destinatário
**Fase 7** declarado na fonte — *"que é a dona do pack e do `ground_truth.yaml`
completo"* — e ausente desta §6 até a varredura desta peça.

**O fato.** `contracts/ground_truth.schema.yaml` fecha `line_b_case.set` em três
valores: `indevido_comprovado`, `ambiguo` e `legitimo_aparencia_suspeita`. `02`
§6.1 nomeia **seis** conjuntos, e `02` §6.2 dá `defensibility` 0.0 a *"legítimo
(inclusive os de aparência suspeita, **manutenção e delegação**)"* — o que implica
que os seis são casos.

**O que a Fase 5 fez, e as duas alternativas que ela recusou com motivo.** Ruído de
manutenção e credenciais compartilhadas ficaram no **dataset** e fora de
`line_b_cases`. Rotulá-los `legitimo_aparencia_suspeita` faria o gabarito afirmar
algo falso — que eles *parecem* suspeitos à primeira vista —, e a calibração
trataria os dois como os 34, misturando dois erros que `02` §6.2 manda separar.
Alargar o enum é mudar semântica dentro da mesma `schema_version`, e `04` §4
proíbe.

**A consequência, medida e não suposta:** uma equipe que classifique uma linha de
manutenção como suspeita **não tem caso no gabarito contra o qual ser pontuada**.
Isso não custava nada enquanto o Brier não corria; custa a partir do momento em que
o pack existe.

**Por que ela é ENTREGA da peça 2.** A saída provável que a fonte já registra é
**`schema_version` nova** — e é exatamente isso que a peça 2 desenha. A P5-4 não é
vizinha do trabalho de migração: **ela é o conteúdo do delta**. Desenhar o caminho
v1→v2 e a recusa do v0 sem decidir o que muda em v3 seria construir a máquina de
migrar sem saber o que ela vai migrar.

**Vence em:** a peça 2, junto com a **P5-6**. Ver o acoplamento no detalhe dela.

#### P5-6 — RESOLVIDA: o produtor existe, e o gatilho declarado foi o commit dele

**Herdada da Fase 5** (`docs/progress/fase_5.md`, §"P5-6"), aberta pelo L3 da
quinta auditoria daquela fase e aceita como LOW, com destinatário **Fase 7**.
Também ausente desta §6 até a peça 2.

> **FECHADA na peça 2.** O gatilho declarado era *"o commit em que `range-cli`
> ganhar o subcomando que escreve o pack"*, e ele ocorreu:
> `range-cli scenario materialize <domain> <pack_id>`.
>
> **A pendência tinha duas metades, e a primeira já havia fechado.** O PR #57
> corrigiu o `since` do gerador — sem ele o pack produzido **não carregava**, e
> um produtor que gravasse artefato que o próprio loader recusa não fecharia
> pendência nenhuma. Esta peça fecha a outra: o comando que põe o par no disco.
>
> **O que ele entrega além do arquivo**, e é o que faz a P7-3 fechar junto: a
> escrita **recusa destino versionado** perguntando ao `git` — não ao
> `.gitignore`, que `git add -f` atravessa — e é **determinista**, com prova
> negativa em três pernas. O gabarito deixou de depender de disciplina para não
> nascer no lugar errado.
>
> **Uma decisão de forma, declarada:** o linter de `02` §6.3 **não** foi
> reimplementado no produtor. Ele já roda dentro de `gerar`, e o docstring de
> `GabaritoDivergente` diz por quê — *"se rodasse depois, existiria um artefato
> inválido no disco entre a escrita e a conferência, e é nessa janela que alguém
> o copia"*. Conferir de novo seria a segunda implementação da mesma pergunta.

**O fato.** `gabarito.gerar()` devolve o artefato **em memória**; o linter roda
dentro dele e o teste produz o texto e o julga — inclusive executando a query de
referência contra o banco. O item 6 da DoD da Fase 5 tem prova executável por esse
caminho, e é por isso que isto nunca foi lacuna de entrega. **O que falta é o
produtor em disco:** nenhum comando escreve o par `ground_truth.yaml` +
`GM_NOTES.md` em `scenarios/`. Quem for facilitar um exercício hoje tem o gerador e
não tem o arquivo.

**Gatilho declarado:** *"o commit em que `range-cli` ganhar o subcomando que
escreve o pack"* — e ele é desta peça, porque é a peça 2 que abre a superfície de
pack. A D10 da Fase 5 já decidiu que o artefato **nasce por comando** em vez de ser
versionado; este produtor é a metade que falta daquela decisão, e não uma correção
dela.

**O ACOPLAMENTO COM A P5-4, e é a razão de as duas fecharem juntas.** Está escrito
na fonte, `fase_5.md:1729-1733`, e é o parágrafo que esta peça precisa ter à vista
antes de escrever a primeira linha:

> *"As duas da Fase 7 vão juntas e não são a mesma. A P5-6 é o **produtor** — o
> comando que escreve o par no disco; a P5-4 é o **modelo** — os seis conjuntos que
> não cabem nos três valores do enum. Quem fechar a primeira sem olhar a segunda
> escreve um `ground_truth.yaml` que omite dois conjuntos sem que nada acuse,
> porque o schema não tem como recusar o que não sabe nomear."*

**A frase final é a que decide a ordem:** o schema não recusa o que não sabe
nomear. Um produtor escrito antes do delta grava um gabarito incompleto e **verde**
— e gabarito incompleto que passa em todos os gates é a forma de erro que este
repositório persegue desde a Fase 0.

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

**Vence em:** os três gatilhos herdados da Fase 6, **intactos** — o primeiro pack
que precise de folha temporal, a implementação do suporte temporal, ou o primeiro
produtor de `fact_materialized`, que baterá em `SemGramaticaTemporal` na primeira
execução. É deliberado que bata: a decisão precisa acontecer ali.

> **SAIU DA FASE 7 na redução de escopo, e volta a `ABERTA`.** Ela havia sido
> promovida a `ENTREGA` — *"peça 3 desta fase"* —, e a peça 3 antiga não existe
> mais. O critério de corte está na §1.1: **nada quebra ao vivo por esta
> gramática não existir**, porque a ausência é **contida** por duas guardas que a
> Fase 6 entregou, e o pack que a exigiria é recusado na carga.
>
> **O GATILHO NÃO FOI REESCRITO**, e isso é decisão e não descuido. Os três são
> os que a Fase 6 declarou, e o primeiro deles — *"o primeiro pack que precise"* —
> continua valendo tal como está. Inventar gatilho novo aqui repetiria o que a
> P5-2 documenta como o erro mais caro desta linhagem: gatilho que já disparou e
> não venceu **treina a próxima leitura a ignorá-lo**.
>
> **E os três foram medidos um a um no fechamento da peça 2** (§3.8), para que a
> saída da fase não fosse decidida no escuro: **nenhum disparou**. O produtor de
> pack escreve `exercise_time` como campo de `facts` no `ground_truth.yaml`, e
> declarar um fato no pack **não é produzir o fato** — `FACT_MATERIALIZED` tem
> dois usos em produção, o import e uma leitura, e nenhum `append`.

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

**A janela barata passou.** O gatilho anterior era a implementação da saída (b),
porque ali o gravador escolhia o que hasheia e acrescentar o pack custava quase
nada. O PR #56 passou sem isso. O defeito não nasceu ali — ele preexiste ao SHA e
à árvore —, mas o conserto deixou de ser de graça.

> **RESOLVIDA na peça 2, e por um caminho que nenhuma das previsões apontava.**
> A pendência dizia *"vence na peça 7 desta fase"*, e a §1 dizia que a peça 7
> **dependia** dela. As duas afirmações caíram, e a razão é a mesma.
>
> **O buraco era: a prova nomeia a árvore, e a árvore não cobre o pack.** A saída
> que se imaginava era hashear o pack junto — acrescentar conteúdo não rastreado
> ao que a prova mede.
>
> **A saída que apareceu é melhor, e ela dissolve o buraco em vez de tapá-lo:**
> o pack passou a ser **reproduzível por comando**. `range-cli scenario
> materialize` é determinista — mesmos insumos, mesmos bytes —, e o determinismo
> tem prova negativa em três pernas, com timestamp e `sort_keys=False` plantados
> e medidos.
>
> Um artefato que é **função dos insumos** não precisa ser hasheado junto da
> árvore para que a prova seja honesta: os insumos estão na árvore — o gerador, a
> query de referência, o template — e o `RANDOM_SEED` é declarado. A prova
> continua nomeando a árvore, e agora isso **basta**, porque o pack não é mais
> conteúdo independente: é saída de código versionado.
>
> **E a metade de segurança fechou junto:** a escrita recusa destino versionado
> perguntando ao `git`. O pack não mora no rastreado por **propriedade do único
> caminho que o escreve**, e não por convenção do `.gitignore` — que `git add -f`
> atravessa. Era essa a parte que fazia o buraco ser buraco: nada garantia onde o
> pack estava.
>
> **A consequência para a §1 está corrigida lá**: a peça 7 não depende mais desta
> pendência. Ela depende do pack existir, e a peça 2 entregou quem o faz nascer.

#### P7-4 — a mesma pergunta com duas respostas, e a allowlist por tipo

**Nasceu DECIDIDA na §7.2 desta fase**, e o mapa inteiro está lá — esta seção é a
pendência, e não a repetição do mapa.

**O fato.** Nada garante que dois módulos que perguntam a mesma coisa sobre um
`event_type` cheguem à mesma resposta. Medido por AST na §7.2:
`ROLLBACK_PERFORMED` tem **8** selecionadores, `EXERCISE_STARTED` 5,
`INJECT_FIRED` 4, `INTEGRITY_VALIDATION_DECLARED` 3, `ASSESSMENT_SUBMITTED` 2, e
os outros nove tipos 1.

**Isso mata a regra ingênua antes de ela ser proposta:** *"um dono por tipo"*
faria dos oito consumidores de `ROLLBACK_PERFORMED` uma função com oito sentidos
— eles fazem perguntas **diferentes** sobre o mesmo evento.

**A forma decidida é allowlist por tipo, declarada com o motivo** — a mesma de
`check_core_contract_imports.py`. Ela é testável contra o defeito que a originou:
escrever `_ja_satisfeito_na_corrente` faria `VERIFICATION_PREDICATE_SATISFIED`
passar de um para **dois** selecionadores, e a allowlist reprovaria até alguém
escrever por quê.

**O limite, aceito como está:** é **degrau 1.5**, e cobra **declaração, não
concordância**. Dois consumidores declarados podem continuar divergindo, e nenhum
AST decide se duas buscas têm o mesmo propósito, porque propósito não é
estrutura. O que muda é **quando** a duplicação fica visível: no commit que a
cria, em vez de na nona auditoria.

**SAIU DA FASE 7 na redução de escopo**, com a peça 6. A razão está na §1.1: o
valor é real e **interno** — nada disso quebra na frente do cliente.

**Vence em: a Fase 12** — observabilidade e documentação, que é onde disciplina
interna cabe.

**E o gatilho é a FASE, e não "a próxima ocorrência da classe".** A distinção é a
lição da **P6-9**, e ela custou três ocorrências: gatilho por ocorrência dispara
**quando o dano já aconteceu**. A P6-9 chegou à mesa `VENCIDA` porque o gatilho
dela descrevia onde a divergência *dói*, e não onde ela *ocorre* — e as três
remediações foram todas manuais, depois do fato. Datar por fase custa que a
pendência não "venza" quando a classe reincidir; o que se ganha é que ela não
dependa de alguém reconhecer a reincidência, que é exatamente a capacidade que a
§7.1 mediu como ausente dez vezes.

**Forma comum com a P7-5, preservada:** as duas são allowlist declarada com
motivo, na linha de `check_core_contract_imports.py`. O esqueleto é o mesmo; o
que muda é o objeto governado. Duas sintaxes de allowlist para a mesma forma
seria a D4 que os dois mecanismos existem para pegar — e quem as implementar na
Fase 12 deve fazê-las juntas por isso, e não por conveniência.

**Fonte:** §7.2 desta fase, e `docs/progress/fase_6.md` §8.5.

#### P7-5 — os chamadores de cada emissor, e o degrau 2

**Nasceu DECIDIDA na §7.1 desta fase**, e o mapa dos três degraus está lá.

**O fato.** Quando o contrato de um emissor muda — `EXIGIDAS`, `_payload`,
`token.claims` —, os sítios que o satisfazem não são varridos. A classe reincidiu
**quatro vezes na Fase 6**: o sétimo contrato com o CI ainda afirmando seis; o
venv da auditoria ausente da branch; a precondição de boot do pack sem varrer o
gravador; o contrato do token sem varrer o chamador de produção.

**Duas regras escritas não a impediram**, e o registro da Fase 6 diz por quê: o
modo de falha **não é ignorar a regra**, é **não reconhecer que esta mudança é
uma instância dela**. A regra cobra varredura depois de uma classificação, e é a
classificação que falha. Mecanismo não pede classificação: dispara sobre o
artefato.

**A forma decidida é o degrau 2** — AST pura, na forma do `check_core_boundary.py`:
achar as chamadas, resolver o módulo importado, exigir que o arquivo esteja na
lista daquele emissor. Os emissores são **três e fechados**, e metade da tabela já
existe em `check_api_surface.py::PERFIS`. **Teria pego o B1 da §7.6.**

**O limite, medido e não suposto:** é por arquivo, e iria cega no dia em que um
arquivo falasse com duas superfícies. O que fecha esse buraco é o achado negativo
da §7.6 — **nenhum cliente precisa do `issue` do núcleo** —, e é essa propriedade,
e não a lista, que faz o degrau valer.

**E a peça 2 mediu que ele cobre UMA das três variantes**, o que a §1 não sabia
quando adotou a pendência. A §3.5 nomeia as três: **predicado estreito** (que o
degrau 2 alcança), **defeito sem sujeito** (que se fecha por derivação, degrau 1,
e faz a classe deixar de existir) e **cobertura que não alcança o ponto de
entrada** (que é execução, degrau 3). A sexta ocorrência já havia mostrado o
limite por outro lado: `start_checkpoint_audit.sh:652` fazia `grep -q` dentro do
artefato, e **`grep` dentro de `.sh` não é import** — o degrau 2 não alcança esse
caminho.

**Quem a implementar na Fase 12 não deve desenhá-la como se cobrisse as três.**
Declarar isso agora é mais barato que descobrir lá, e é literalmente o argumento
que a §7.1 usa sobre a própria sexta ocorrência.

**SAIU DA FASE 7 na redução de escopo**, e **vence em: a Fase 12**, pelo mesmo
gatilho por fase da P7-4 — e pela mesma razão, que é a lição da P6-9.

**A vizinhança com a P6-7, e ela não é identidade.** A P6-7 pergunta *"esta rota,
executada, emite?"* e é o **degrau 3**. Não se fecham juntas. Mas quem
implementar esta esbarra naquela fronteira, porque as duas leem
`api_surface.yaml` e param em lugares diferentes.

**Fonte:** §7.1 desta fase, e `docs/progress/fase_6.md` §7.7.

#### P7-6 — 44 registros de auditoria que ninguém varreu por destinatário

**Nasceu da varredura de abertura da peça 2**, e nasceu do que ela **não** cobriu.

**O fato, contado na árvore:** `docs/progress/` tem **44** arquivos `audit_*.md`,
de `audit_20260814T020307Z.md` a `audit_20260823T155304Z.md` — 14 a 23 de agosto de
2026. Eles são versionados desde a decisão registrada no `fase_0.md` §"P11":
*"cada linha é a única prova de uma rodada que já aconteceu, não artefato
reconstruível"*.

**A lacuna.** Achado de auditoria que **não foi promovido a pendência** não aparece
em `fase_N.md` nenhum. O quarto predicado de `check_progress_consistency.py` lê
`fase_N.md` e nada mais — a §2.4.1 declara essa fronteira —, e a varredura desta
peça leu a mesma superfície. **Nenhum dos dois alcança os 44.** Um BLOCKER
corrigido no commit e nunca transcrito, um MEDIUM aceito com ressalva, um LOW cuja
ressalva envelheceu: os três têm a mesma forma, e a forma é invisível.

**Por que isto é pendência e não trabalho da peça 2.** Varrer 44 registros de
auditoria por destinatário é medição de outra ordem, e fazê-la dentro da peça que
desenha o schema é escopo crescendo — o mesmo argumento com que a P6-8 e a P6-7
não foram consertadas dentro da correção que as achou. E a medição precisa de um
predicado que ainda não existe: *"este achado virou pendência em algum
`fase_N.md`?"* exige casar achado com id, e achado de auditoria **não tem id
estável** entre rodadas.

**As duas formas, para quando a decisão vier.** **(a)** varredura única, manual,
com o resultado promovido a pendências — barata, e não impede a 45ª. **(b)** regra
no rito de auditoria: todo achado não corrigido no mesmo PR nasce com linha na §6
da fase corrente — mecanismo no produtor em vez de varredura no consumidor, e é a
direção que a §7.1 chama de degrau 1.

**Vence em:** o fechamento desta fase. É deliberado que caia ali e não depois: a
Fase 8 abre o paralelismo, e multiplicar quem escreve registro antes de saber o que
os 44 guardam é aumentar a dívida sem tê-la medido.

#### P7-7 — RESOLVIDA: eram TRÊS exigências, e só uma tinha mecanismo possível

**O gatilho declarado era *"a peça 4 desta fase, no lint"*** — na numeração
antiga, que é a peça 3 depois da redução da §1. Ele chegou, e a pendência fecha.

**Ela cobrava uma coisa e eram três.** A nota da entrada `5` de
`scripts/check_secoes_de_seguranca.py` já as nomeava — *"fonte citavel, TTP nao
excedida, IOC ausente"* —, e a pendência as tratava como um verificador só.
Medi-las mostrou três destinos diferentes; o detalhe está na §4.6, e aqui fica o
que a pendência precisava responder:

| Exigência | O que fechou |
|---|---|
| fonte pública citável | **meia**, e declarada assim. `sources` é `required` com `minItems: 1`; *"citável"* não é forma — `sources: [confia em mim]` casa o schema |
| TTP não excedida | **nenhum mecanismo é possível**: o julgamento é contra documento externo |
| IOC ausente | `confere_ausencia_de_ioc`, sítio `ioc_operacional`, na carga **e** no linter |

**Fundir as três teria sido o modo errado de fechar**: o mecanismo da terceira
passaria a cobrir as duas primeiras em silêncio, e a pendência ficaria marcada
como resolvida sobre cobertura que não existe. As três são entradas separadas do
`x-aurora-linter-rules`, e as duas primeiras dizem `destinatario: revisão
humana`.

**A entrada `5` do registro perdeu o `destinatario=(7, …)`**, que era o que a
pendência avisava: *"se a peça 4 fechar sem ela, a entrada continua dizendo
`destinatario=(7, …)` sobre uma fase que passou — e gatilho que já disparou e não
venceu é o defeito que a P5-2 documenta"*. Ele saiu.

**O que a pendência não previa, e apareceu ao fechá-la:** `tools/check_synthetic_data.py`
**já executava** a cláusula de IOC — as faixas da §3 são a forma dela — e não
constava do registro como mecanismo da §5. A direção inversa do
`check_secoes_de_seguranca.py` o pegou quando o movimento do predicado o fez
citar a seção. Registro que subestima a própria cobertura é a direção em que ele
mente sem que nada acuse.

**E o probe daquele verificador tinha um defeito latente**, exposto pelo primeiro
mecanismo declarado sob **duas** seções: a base sintética montava
`caminho -> {numero}` por compreensão de dicionário, e dicionário sobrescreve. O
controle verde reprovava por defeito da própria base. Corrigido para acumular.

#### P7-8 — o core importa pacote de topo, e nenhuma guarda enxerga isso

**Nasceu na peça 3**, e ela é a **P2-15 um nível acima** — literalmente a mesma
forma, com outro alvo.

A §2.1 do registro da Fase 2 declarou um limite: *"`tools/check_core_boundary.py`
detecta, por AST, só o que aponta para `domains`. Sobre `contracts` ele não tem
opinião nenhuma"*. O gatilho disparou na peça do loader, e a resposta foi o
`check_core_contract_imports.py` — whitelist do que o core importa de
`contracts/`, com motivo por entrada.

**O fato.** `range-core/engine/loader/pack_loader.py` passou a importar
`dados_sinteticos`, pacote de topo criado nesta peça. As duas guardas existentes
não o alcançam: uma só opina sobre `domains/`, a outra só sobre `contracts/`.
**O import é legítimo** — o pacote é stdlib puro, agnóstico de domínio, e a
alternativa era duplicar o predicado ou fazer `tools/` importar a aplicação. O
que falta é guarda: sem ela, o próximo import de topo não encontra nada, e a
ausência de opinião passa a valer mais que a permissão. É o argumento da P2-15,
palavra por palavra.

**A forma da saída, se alguém a tomar:** generalizar
`check_core_contract_imports.py` de *"o que o core importa de `contracts/`"* para
*"o que o core importa de fora de `range_core`"*, mantendo a whitelist com motivo
por entrada. O custo é que a lista cresce; o que se compra é que crescer passe a
ser uma conversa, que é o desenho que aquele arquivo já defende.

**Por que não fechou aqui.** Generalizar uma guarda de invariante é mudança de
mecanismo com prova negativa própria, e ela não pertence à peça do linter — seria
a terceira superfície nascendo numa peça que já entregou duas. E o defeito é de
**ausência de opinião**, não de violação: hoje há **um** import de topo no core
além de `contracts`, e ele está declarado aqui.

**Vence em:** o segundo pacote de topo que o core importar — momento em que a
lista deixa de ser uma linha e passa a ser lista de verdade —, ou a Fase 12, o
que vier primeiro.

#### P7-9 — `lint` não roda no CI, e a árvore não tem pack para lintar

**Nasceu na peça 3.** `04_SCENARIO_SCHEMA.md` §8 fecha com *"`validate`, `lint` e
`evidence verify` rodam no CI"*, e o `lint` desta peça **não** tem step.

**O fato, medido.** Não há pack lintável versionado. `scenarios/` está fora do
Git desde a peça 5 da Fase 5, e `tests/fixtures/pack_minimo` é **deliberadamente
incompleto** — o linter o recusa, corretamente, com sítio `incomplete_pack`,
porque ele traz `injects.yaml` e `objectives.yaml` sem `ground_truth.yaml`.

**Por que não foi resolvido com uma fixture nova.** Seria cumprir a letra: um
step apontado para um pack fabricado para passar prova que o **executável corre**,
e não que a árvore está limpa — a suíte já cobre o linter contra packs sintéticos
completos, incluindo os quatro critérios com posição. O que o step acrescentaria é
a variante *"cobertura que não alcança o ponto de entrada"* da §7.1, que a §1.1
registra como o degrau 3 e que o proprietário já decidiu **não** tornar gate
obrigatório.

**E há a fronteira de `04` §8.1 (a) a preservar:** as allowlists liberam os
subcomandos que só leem, e `lint` é um deles. Um step de CI não a toca — mas uma
fixture de pack "de verdade" na árvore versionada toca a decisão da Fase 5 sobre
onde pack mora, e essa decisão não é desta peça.

**O que a ausência custa hoje:** nada mede que o `range-cli` **instalado** corre.
A suíte chama `cli.main` em processo. É a mesma lacuna que a §3.4.1 desta fase
mediu como DÉCIMA OCORRÊNCIA — cobertura que não alcança o ponto de entrada — e
está nomeada aqui para não ser confundida com cobertura.

**Vence em:** o primeiro pack lintável versionado, ou a Fase 12, que é onde a
documentação e o segundo pack entram.

**O achado original fica abaixo, sem edição** — ele é sobre o MODO como a
pendência foi encontrada, e esse valor não caduca com o conserto.

##### Como ela foi achada, e por que isso valia um id

**Achada por RASTRO, e não pelo predicado da varredura** — e é isso que a torna
interessante. O vocabulário da varredura (§2.4.1) não a alcançaria: ela não está em
registro de fase nenhum. Ela apareceu seguindo a **P4-12**, que está **FECHADA**
(`fase_5.md:1713`), até o mecanismo em que o conteúdo dela sobreviveu.

**Onde ela mora:** `scripts/check_secoes_de_seguranca.py:213-228`, entrada `5` do
registro seção → verificador, com `destinatario=(7, …)`. É a **única** das oito
entradas que aponta para esta fase; as outras apontam para 9, para 12, e cinco não
apontam para lugar nenhum. O texto é da própria entrada:

> *"a §5.2 exige fonte publica citavel declarada em `ground_truth.yaml`, e o
> primeiro pack e da Fase 7. Sem pack nao ha ator declarado a conferir"*

E a nota da mesma entrada declara o que falta, com as três exigências nomeadas:

> *"**COBERTURA PARCIAL**: os dois contratos carregam a distincao da §5.1
> (fornecedor de produto sempre ficticio) e a forma do bloco `threat_actor` da
> §5.2. O que falta e verificador que confira o ator DECLARADO contra as exigencias
> da §5.2 — **fonte citavel, TTP nao excedida, IOC ausente**."*

**Por que ela é peça 4 e não peça 2.** A peça 2 faz o pack **existir**; conferir o
ator declarado é regra de **linter sobre pack existente**, que é o objeto da peça 4
(`range-cli scenario lint`). Escrevê-la na peça 2 seria a segunda superfície de
recusa nascendo fora do lugar onde as outras seis já vão morar.

**O que ela obriga da peça 2, mesmo não sendo dela:** o `ground_truth.yaml` que a
peça 2 desenhar precisa **admitir** o bloco `threat_actor` com fonte citável, ou a
peça 4 chegará a um schema que não tem onde pôr o que ela conferiria.

**O achado tem valor além de si, e ele está na §2.4.1:** obrigação endereçada a uma
fase que mora em registro executável é inalcançável pelo quarto predicado, **por
desenho**. Esta é a primeira instância medida dessa classe, e é por isso que ela
ganhou id em vez de virar nota de rodapé.

**Vence em:** a peça 4 desta fase, no lint. Se a peça 4 fechar sem ela, a entrada
`5` do registro continua dizendo `destinatario=(7, …)` sobre uma fase que passou —
e gatilho que já disparou e não venceu é o defeito que a P5-2 documenta.

#### P6-9 — RESOLVIDA: o lançador sincroniza, e a comparação passa a ter dois chamadores

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

> **RESOLVIDA no PR #61**, conserto puro contra `main` e fora desta branch — o
> mesmo rito da P6-11 e da P7-2.
>
> **A FORMA ESCOLHIDA É A PRIMEIRA: o lançador sincroniza.** As outras duas
> caem, e as razões são medidas:
>
> | Forma | Por que não |
> |---|---|
> | (2) o verificador acusa melhor | **não conserta.** `phase0_negative_tests.py` já acusava — pegou nas três ocorrências. O que faltava não era detecção: era o passo ficar **antes** de o lançador abrir a sessão |
> | (3) disciplina declarada | é o que falhou. Três ocorrências, três remediações manuais |
>
> **ERAM TRÊS PARES, E NÃO UM** — a medição que precedeu o conserto mudou o
> escopo dele: `readonly_bash.py`, `sentinela_de_branch.py` e
> `checkpoint-auditor.md`. Consertar o primeiro deixando os irmãos vivos seria a
> §9.6, que é a correção que fecha a instância e deixa a classe viva.
>
> **O QUARTO FICA FORA, e a exclusão é declarada em dois lugares no código.**
> `user-scope/hooks/pre-commit` → `.git/hooks/pre-commit` vai para **dentro** da
> árvore, é hook do **git** e não do agente, e é **o único par em que BYTES
> importam**: ele é `#!/bin/sh`, e um CR no shebang o torna inexecutável.
> `sem_carriage_return` o afirma por `read_bytes()`; sincronizá-lo por linha
> apagaria exatamente a diferença que importa nele.
>
> **O CUSTO ACEITO, e ele é estreito:** o lançador passa a **escrever fora da
> árvore**. Até aqui só tocava `.aurora-worktrees/`, o worktree e
> `docs/progress/`. As guardas vieram do `bootstrap.sh`, que é o único
> precedente de escrita em `~/` no repositório: destino **derivado** de
> `Path.home()` e nunca parametrizável, escrita **só quando diverge**, razão
> declarada no ponto, falha **alta** em qualquer erro — e **SMOKE TEST depois de
> escrever**. Não confiar que a cópia deu certo: exercitá-la. O `readonly_bash`
> tem de bloquear `rm -rf`; o sentinela tem de responder com rc 0 ou 2, que são
> os dois vereditos legítimos porque dependem da branch.
>
> **A comparação virou predicado, e a razão não foi estética.**
> `copia_em_sincronia` não servia: ela não devolve valor e, no ramo de
> divergência, chama `_reject`, que levanta `SystemExit(1)` — ela **aborta onde
> o lançador tem de reparar**. Duplicá-la seria a **quarta** implementação da
> mesma comparação, e o H1 da primeira auditoria da Fase 4 fechou as três
> anteriores. Então `divergem(fonte, instalada)` saiu dela, e os dois a chamam.
>
> A assimetria da ausência ficou **fora** do predicado: para o harness, cópia
> ausente é **esperada** (o CI não tem escopo de usuário); para o lançador,
> ausente significa **copiar**. Se ela entrasse ali, o predicado teria dois
> comportamentos conforme quem chama — que é como se fabrica a próxima
> divergência.
>
> ##### O VERMELHO 1, e ele é a prova de que a pendência era o que dizia ser
>
> Divergência plantada em `~/.claude/hooks/sentinela_de_branch.py`, lançador
> rodado **antes** do conserto:
>
> ```
> Preparing worktree (detached HEAD 44e641e)
> Criando o venv da auditoria e instalando a arvore auditada (P3-4)...
> Subindo a stack efemera da auditoria (Postgres + Redis)...
> Rodando as provas de container do commit auditado (P4-10)...
> Medindo o seed completo do commit auditado (~5 min; Forma B da Fase 5)...
> ```
>
> Ele atravessou a guarda de base, montou o worktree, criou o venv, instalou a
> árvore, subiu a stack, rodou as provas de container e entrou no seed — **com o
> hook instalado divergente**. `grep -i "hook|sincron|sentinela|.claude"` sobre a
> saída inteira: **zero**.
>
> **Não era só que ninguém sincronizava: ninguém sequer olhava**, no exato rito
> cujo produto depende de o hook ser o que a árvore declara.
>
> Depois do conserto, a mesma divergência:
>
> ```
> Sincronizando a copia instalada do escopo de usuario (P6-9)...
> Escopo de usuario SINCRONIZADO (1 de 3):
>   sentinela de branch: atualizada (divergia da fonte)
>   smoke test passou em cada copia escrita que e programa.
> Preparing worktree (detached HEAD 932996e)
> ```
>
> A etapa aparece **entre** a guarda de base e o worktree, e a posição é por
> ordem de custo: depois da guarda, que é a última coisa barata; antes do
> worktree, porque falhar depois de venv e stack desperdiçaria o trabalho caro.
>
> ##### Um achado de lado, e ele é da mesma classe que a pendência mede
>
> `scripts/check_allowlist_do_auditor.py` lê a **fonte versionada** — `HOOK`
> aponta para `user-scope/hooks/readonly_bash.py` — e **não declarava isso**.
>
> Ele responde *"a fonte declara este script?"* e **não** responde *"o auditor
> consegue de fato executá-lo?"*. A segunda depende da cópia instalada estar em
> dia, que era justamente o que ninguém garantia. Quem lesse o cabeçalho
> concluiria que "a allowlist está certa" significa "o auditor roda o script" —
> que é a segunda pergunta, e ele não a faz.
>
> **É a §7.3.1: verificador que não declara a própria fronteira é lido como
> cobrindo mais do que cobre.** Corrigido **por declaração**, sem tocar em
> comportamento — o mecanismo estava certo; o que faltava era ele dizer o que
> não fazia.

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
