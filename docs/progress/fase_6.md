# Fase 6 — Objetivos, rubricas, métricas

**Status: EM ANDAMENTO** — peças 1 a 5 fechadas em código, peças 6 e 7 abertas,
sem auditoria de checkpoint. A linha de status está aqui porque
`check_readme_atual.py` decide *"a fase fechou?"* por ela, e registro sem status
é registro que o verificador não consegue ler. `EM ANDAMENTO` não é uma das
formas que aquele predicado conta como conclusão — `CONCLUÍDA` e `AUDITADA —
PASS` são —, e é isso que se quer: a fase não fechou.

> **A redação anterior desta linha dizia `NÃO INICIADA`**, e sobreviveu a cinco
> peças. É exatamente a classe que o `check_progress_consistency.py` e o
> `check_readme_atual.py` existem para caçar — documento que sobrevive à mudança
> e a contradiz —, e ela passou porque os dois predicados perguntam *"a fase
> fechou?"*, e `NÃO INICIADA` responde *"não"*, que continuava sendo verdade
> sobre o fechamento enquanto era falso sobre o início. Corrigida na peça 5, com
> a distinção registrada: **não fechou** e **não começou** não são a mesma
> afirmação, e nenhum verificador olhava a segunda.

**Por que este registro nasceu antes da fase.** Duas pendências vieram do
`spec-change` `particao-das-metricas-pareadas`, que é anterior à fase, e
pendência sem lugar é pendência que ninguém encontra.

Registrá-las no `fase_5.md` seria pior: aquele registro está fechado e auditado,
e acrescentar linha a um documento encerrado é reescrever história de uma fase
que já passou. Elas não são achados da Fase 5; são consequências declaradas de
uma mudança de norma feita entre as duas.

## 1. Plano da fase — sete peças

| # | Peça | Estado |
|---|---|---|
| 1 | Biblioteca BARS: nove competências versionadas, contrato, integridade referencial | **fechada** |
| 2 | Motor de objetivos: binding evento→objetivo na projeção, `objective_evidence` | **fechada** |
| 3 | `audit_query_performed` e as ações de declaração nos endpoints | **fechada** — blocos A e B |
| 4 | Predicados de verificação e o motor que os avalia | **fechada** |
| 5 | Métricas: os dois computadores, o insumo tipado, epoch como cálculo | **fechada** — §3 |
| 6 | Calibração: Brier no escopo revisado, sinais, `TTIV` por limiar | **fechada** — §4 |
| 7 | Divergência entre avaliadores e a janela de asseguração prematura | **fechada** — §5 |

**Dependências que não são de conveniência.** A peça 4 vem antes da 5 porque os
computadores de métrica consomem `verification_predicate_satisfied`.

**O rebase já aconteceu**, antes da peça 3, e é o único: a `main` passou a
carregar toda a base normativa desta fase — os `spec-change`
`impacto-observavel-definido`, `acoes-de-declaracao-o-criterio`,
`superficie-de-participante` e `isencao-de-bootstrap-de-token` —, e não há
`spec-change` pendente. A âncora foi regravada junto, que é o que `WORKFLOW.md`
exige e o que o predicado de auditoria não deriva sozinho.

**A janela de asseguração prematura é da projeção `aar_timeline`, não da
`metrics`.** A janela cruza declaração com verificação, e por `00` §3.2 só o AAR
tem as duas metades. A Fase 10 renderiza a partir dela; a prova da DoD é teste
nomeado sobre a saída da `aar_timeline`.

### A peça 3 fecha em dois blocos declarados

**A fronteira é decisão de processo, e está aqui para que a auditoria não leia o
bloco A como incompleto nem o B como escopo crescido.**

| Bloco | Conteúdo |
|---|---|
| **A** | superfície de participante e seu perfil, emissor próprio com claims por superfície, as sete credenciais de ambiente (D5), `GET /audit/grade-changes`, a guarda de boot do emissor, e os hooks das ações normativas |
| **B** | as nove rotas de declaração com RBAC pela coluna *Quem* de `03` §3.4, e o predicado de completude da contrassinatura com os quatro negativos como testes |

**Por que dividida.** A peça 3 acumulou cinco `spec-change` — a nona ação, a
superfície, a autenticação, a isenção de bootstrap, e o predicado de impacto
observável antes deles. O corpo que sobrou não cabe numa sequência contínua sem
que a qualidade caia perto do fim, e a queda cairia exatamente sobre a
contrassinatura, que é a parte com quatro negativos a provar.

**O bloco A declara as nove rotas como `planejada`.** Não é adiamento
escondido: `scripts/check_api_surface.py` reprova rota `planejada` que já exista
no código, então a promoção no bloco B é cobrada pelo mesmo verificador. É o
mecanismo funcionando como desenhado — a obrigação escrita antes do código.

### As três decisões que a peça 3 tomou

**Superfície — saída B, terceira superfície no núcleo.** As três consideradas:
(A) o núcleo cresce com uma chave `personas`; (B) superfície irmã, com perfil
próprio; (C) as rotas no adapter, com a persona como dado.

Escolhida a **B**, por três razões. (1) A opção A tornaria `irreversibilidade` e
`confirmacao` campos presentes-às-vezes no perfil de facilitação — a doença que
a P4-2 acabou de curar do outro lado. (2) Persona é vocabulário de exercício
**por verificador**: `check_api_surface.py` a recusa no perfil de domínio, logo
RBAC por persona só é imponível no núcleo, e a opção C exigiria desfazer essa
guarda. (3) `SUPERFICIES` cresce por registro, que é o mecanismo desenhado.

E a razão dura da **colocação**, que não é organizacional: a varredura de rotas é
`rglob` sobre a `raiz_api` de cada superfície. Aninhada em `api/participante/`, a
superfície nova ficaria **dentro da árvore que o perfil do núcleo varre**, e as
rotas de declaração seriam julgadas pelo perfil errado — por
`camadas_de_emissao: [facilitation]` e por `irreversibilidade`. Irmã é a única
forma com árvores disjuntas.

**Autenticação — emissão própria, claims por superfície.** O modelo já era esse:
`token.claims` vive no `api_surface.yaml` de cada superfície. O que muda é o
verificador comparar **cada emissor contra a superfície dele** — movimento irmão
do `camadas_de_emissao`. A alternativa, uma claim `persona` opcional no
`_payload` único, realizaria por desenho o risco que o próprio docstring daquela
função guarda: literal único, claim para as duas vocações.

Credenciais de **ambiente**, disciplina D5: sete, uma por persona, sem default,
recusa alta. Sem `spec-change` para atribuição.

**A semântica do `actor_id`, dita como decisão e não como garantia.** `actor_id`
identifica **credencial, não humano**. A condição (4) da contrassinatura —
`actor_id` distintos — pega **reuso de credencial**, e não dualidade humana:
dualidade é controle **físico** da facilitação, na distribuição das sete
credenciais. Credencial pessoal futura dá dentes à condição (4) **sem tocar a
spec**, porque a condição já está escrita na forma certa. O limite fica
declarado em vez de parecer garantia.

### Reivindicação pendente para a peça 6

`scripts/check_spec_examples.py` guarda em `IGNORADOS` dois blocos de
`assessment_submitted` — `02_DOMAIN_ACADEMUS.md` §6.2 e `03_EXERCISE_DESIGN.md`
§5.1 —, os dois com o motivo *"artefato de runtime da Fase 6, sem contrato"*.

**O motivo caduca quando a peça 6 trouxer o contrato de assessment**, e caduco é
o mesmo que ausente: ninguém reabre um `IGNORADOS` para conferir se a condição
ainda se sustenta. A peça 6 dá aos dois o tratamento que a rubrica recebeu na
peça 1 — contrato que os **reivindica**, e a entrada sai da lista.

Registrado aqui porque a peça 1 já mostrou que a checagem existe e funciona: foi
ela que pegou o probe de `check_spec_examples_probes.py` ancorado no bloco que
deixou de ser ignorado.

### A lacuna que a peça 3 achou, e o `spec-change` que a fechou

T9 exige que todo `event_type` de `observability_hooks.yaml` seja emitido pela
ação correspondente. `separate_incident_declared` é evidência `auto` do OBJ-03
no exemplo **normativo** de `03` §1.1 e de `09` §6 — e `03` §3.4, a tabela que
`07` chama de requisito funcional, não tinha ação que o emitisse.

**Sem ação, OBJ-03 nunca é satisfeito, e o item de T9 seria insatisfazível por
construção.** Fechado pelo `spec-change` `acoes-de-declaracao-o-criterio`, que
acrescenta a linha e — mais importante — o **critério de pertencimento** que a
tabela nunca teve.

É a segunda vez que este mesmo evento cai de um registro fechado: da primeira,
do catálogo de `09` §4.1, corrigido pelo `spec-change`
`facilitation-e-separate-incident`. Os dois registros tinham enumeração e não
critério.

## 2. Evidência da DoD, por item

O que a auditoria precisa achar sem reconstruir a cadeia por leitura.

### T9 — *"AAR grava a versão de rubrica usada; comparação entre versões distintas é recusada sem mapeamento declarado"*

A letra diz **AAR**, e o AAR é da Fase 10. A cadeia tem **duas metades**, e as
duas estão nomeadas aqui para que a rastreabilidade não dependa de alguém
deduzi-la:

| Metade | Onde | O que faz | Prova |
|---|---|---|---|
| **grava e computa** | `range-core/objectives/projecao.py` — Fase 6, peça 2 | `EvidenciaDeObjetivo.rubric` carrega `<competency>.<version>`; `comparavel()` recusa entre versões | `tests/test_objectives_projecao.py::ComparacaoEntreVersoesDeRubrica` — as três: mesma versão compara, versões diferentes não, e a versão fica gravada |
| **renderiza** | AAR — Fase 10 | imprime a versão usada por objetivo e a recusa de comparação | T14, na fase que entrega o AAR |

**A recusa mora na projeção, e não no renderizador**, porque a versão usada é
dado desta projeção. Na outra colocação, todo consumidor que comparasse duas
rodadas precisaria lembrar da regra — e `WORKFLOW.md` registra que detecção por
memória não é detecção.

**O que ainda não existe, dito:** não há mecanismo de *mapeamento declarado*
entre versões. `comparavel()` não o consulta porque ele não existe; quando
existir, entra ali, e o nome da função é onde procurar. Enquanto não existir, a
recusa é total, que é o lado seguro da frase de `03` §2.1.

É a mesma forma da colocação da janela de asseguração prematura (§1): Fase 6
computa, Fase 10 renderiza.


### Fronteira declarada — o avaliador e o laço contínuo

A peça 4 entrega o **avaliador**: `avalia(no, mundo)` puro, e
`avaliar_e_emitir(store, predicados, flags)` montando o mundo sobre a linhagem
corrente e emitindo as transições.

**O laço contínuo não é dela.** Quem chama o avaliador a cada evento é o
`inject-engine`, e essa ligação é da **peça 5** — é lá que os computadores de
métrica passam a consumir o veredito, e é o consumidor que decide a cadência.

Está escrito aqui pela mesma razão dos dois blocos da peça 3: a auditoria lê a
fronteira declarada, e não a deduz do relato. Sem esta linha, o avaliador seria
lido como entrega incompleta, e a ligação na peça 5 como escopo crescido.

**`flags` chega ao avaliador como dado, do fold**, e não é recalculado por ele:
duas reconstruções do mesmo estado divergiriam, e a divergência apareceria
exatamente como predicado meio-revertido — que é o que a peça 4 tornou
inexprimível.

### Cláusula herdada pela peça 5 — o quarto negativo da contrassinatura

`03_EXERCISE_DESIGN.md` §3.4 nomeia quatro negativos do predicado de completude.
**Três são de emissão** e estão provados no bloco B da peça 3, com violação
plantada em `tests/test_participant_contrassinatura.py`: antecedente ausente,
autocontrassinatura, e antecedente já completado — mais a cadeia de três, que é
a condição (3).

**O quarto é do consumidor, e não da emissão:** *"declaração isolada não marca
`TTID`"*. A declaração é **gravada** e fica registrada; a ausência de
contrassinatura é achado do AAR, e não erro de quem declarou. Quem executa a
cláusula é o **computador de métrica**, que é a peça 5.

Testá-la no bloco B exigiria inventar o consumidor, que é a forma de um teste
passar por motivo errado. O que o bloco B prova é o **positivo** que a sustenta —
`test_declaracao_isolada_grava_e_fica_sem_sucessor`: a declaração existe no
fluxo e não tem sucessor. Sem isso, a cláusula herdada não teria sobre o que
operar.

**Endereço na peça 5:** o computador do lado da declaração, ao selecionar o
instante de `TTID`, aplica o predicado de `03` §3.4 e marca **o evento que
completa**. Declaração sem sucessor não produz `TTID`, e a janela sem
contrassinatura vai para a `aar_timeline`, junto da janela de asseguração
prematura — as duas são leitura do AAR e da mesma natureza.

## 3. A peça 5 — as métricas

Oito unidades, cada uma commitada e empurrada em verde. O que segue é o que a
auditoria precisa achar sem reconstruir a cadeia por leitura.

### 3.1 O que foi entregue, por unidade

| # | Unidade | O que fecha |
|---|---|---|
| 1 | payload de `inject_fired` | **P6-2**, ramo (b): `observable_impact` derivado na carga, carimbado no disparo |
| 2 | `metrics/insumo.py` | a partição de `00` §3.2 — tipos próprios, ponto único de montagem, escalares no insumo |
| 3 | `scripts/check_insumo_de_metrica.py` | a exigência **(3)** de §3.2, que era leitura e virou gate |
| 4 | `metrics/epoch.py` | epoch como cálculo do consumidor: união, `rehearsal`, e os outros dois motivos |
| 5 | `metrics/verificacao.py` | `TTCV` e `TTRV` |
| 6 | `metrics/declaracao.py` + `declarations/contrassinatura.py` | as seis siglas deste lado, e a cláusula herdada do `TTID` |
| 7 | `tests/test_derivacao_das_nove_siglas.py` | a derivação de `03` §3.0 contra o critério de `00` §3.2 |
| 8 | `LacoDeVerificacao` no `inject-engine` | o laço contínuo de `03` §3.1 — a fronteira que a peça 4 declarou |

### 3.2 As decisões que a peça 5 tomou

**A exigência (3) de `00` §3.2 não tinha mecanismo, e o docstring a afirmava.**
A §3.2 lista quatro exigências de verificação. A (4) já estava em
`contract_rules.py`; a (1) e a (2) são propriedades do módulo. A **(3)** —
*"o construtor aparece só ali"* — exige checagem de superfície, e não existia:
medido, nada em `scripts/` ou `tools/` citava os três tipos.

A primeira redação do módulo a descrevia no presente. **Afirmação de mecanismo
ausente é a classe da D19** — a casca do console que "tinha teste de vazamento"
quando o que havia era a direção inversa. O verificador nasceu na unidade
seguinte, e o docstring nomeou a ausência enquanto ela durou.

**`Medida` é tipo compartilhado pelos dois lados, e isso não fura a partição.**
`00` §3.2 particiona **insumo**, não resultado: um tipo de saída não carrega
evento nenhum. E o AAR recebe as duas metades de cada par para computar o delta
— dois formatos o fariam reconciliar antes de subtrair, e é ali que um
`desde_t0` de um lado viraria um `decorrido` do outro.

**O predicado de contrassinatura virou módulo, e o emissor foi refatorado.**
`03` §3.4 manda o **consumidor** aplicá-lo. Escrito duas vezes seria D4, e a
divergência apareceria como `TTID` marcado num par que a emissão recusou. O que
ficou no emissor é a **mensagem**, porque `06` T2 exige que a recusa nomeie o
motivo e um predicado booleano o obrigaria a redescobri-lo.

**`09` §3.1 tem quatro linhas, e só duas tinham mecanismo.** `06` T10 nomeia
`technical_failure` e `rehearsal`. `facilitation` e `adjudication` são norma viva
— *"métricas recomputadas a partir da nova epoch"* — e estavam sem código.

A assimetria da quarta é o achado: **`technical_failure` não descarta epoch
nenhuma.** A linha diz *"relógio congelado"* e *"a equipe não é penalizada por
bug do ambiente"*, e descartar as declarações anteriores penalizaria exatamente
por isso — obrigaria a redeclarar. Só o tempo é descontado.

**T0 não é a marca do `exercise_started`.** O evento é gravado alguns instantes
depois do zero, e usar a marca dele embutiria a latência de emissão em toda
métrica do exercício, sem nada acusar. `01` §4.4 dá a identidade que o recupera:
`exercise_timestamp == T0 + exercise_time`. Foi o teste de T0 que pegou.

### 3.3 Fronteiras declaradas — o que a peça 5 **não** entregou

**`TTIV` é da peça 6.** É a única das nove siglas sem computador, e o plano da
fase a nomeia por extenso na peça 6. Os escalares dela — `limiar_de_calibracao`
e `defensibilidade` — **já chegam no insumo**, porque `00` §3.2 exige que cheguem
como dado e não por consulta ao pack.

A fronteira é **cobrada e não declarada**:
`test_a_unica_sigla_sem_computador_e_ttiv_e_ela_e_da_peca_6` reprova no dia em
que ela for cruzada.

**`not_applicable` não é distinguido de "não verificado".** Daqui os dois são
ausência de veredito, e a distinção exige o pack — o banido de `00` §3.2. Não se
inventou campo de insumo para ela: enumerar vocabulário antes de o consumidor
existir é prever o módulo, que é a razão pela qual `check_store_read_surface.py`
esperou a API existir. Quem imprime *"TTRV não aplicável"* é o AAR.

**O laço não alcança ações de participante, e a ausência é estrutural.** Medido:
`vpn_access_revoked` e `identity_scope_disabled` — as folhas de `containment` no
exemplo normativo de `03` §3.1 — **não são emitidos por nada na árvore**. A
superfície das três ações com efeito no mundo (`01` §4.4) é de outra fase.

E o `Emissor` das nove declarações não pode movê-las: por `09` §4.0, folha de
predicado exige `state_effect` **e** `metric_side: verification`, e nenhuma das
nove satisfaz a conjunção. A ligação seria no-op **por construção**, e há teste
calculando a conjunção sobre o catálogo real — com o controle que impede o caso
vazio de passar.

> Uma versão anterior deste commit ligava o laço ao `Emissor`, com um comentário
> que afirmava que aquela superfície emitia as folhas. Era falso, e a medição o
> desfez. Fica registrado porque é a mesma disciplina que o resto da fase aplica
> à spec: medir antes de afirmar.

**O delta entre as duas metades é do `aar_timeline`.** Os computadores marcam
instantes e entregam o decorrido desde T0 já descontado. `00` §3.2 põe o delta
no AAR por nome, e é a mesma colocação da janela de asseguração prematura.

### 3.4 A contagem inscrita, e a regra que sai daqui

**Criar instância de um conjunto contado exige varrer quem afirma a contagem, no
mesmo commit.**

A peça 1 criou o **sétimo** contrato — `rubrics.schema.yaml` — e não varreu. O
passo de CI que prova o `package-data` afirmava `len(read_contracts()) == 6`, e
mais dez lugares em prosa diziam *"os seis contratos"*. O passo teria ficado
vermelho no PR da fase, trinta commits depois de a causa entrar.

**A leitura errada seria *"a branch não foi empurrada"*.** `push` não roda CI sem
PR, e o número teria envelhecido do mesmo jeito num repositório que rodasse CI a
cada push. O que falhou foi a varredura — e ela **já era ritual desta fase**: a
contagem de `spec-change` foi corrigida por commit próprio quatro vezes, e o
mesmo cuidado não atravessou para o conjunto de contratos.

**A correção removeu o número, não o atualizou.** Trocar 6 por 7 marcaria a
quarta ocorrência da mesma classe nesta fase e prepararia a quinta. O CI passa a
afirmar a propriedade **derivada do diretório** — todo `.yaml` de `contracts/`
vira um contrato lido, nenhum órfão e nenhum faltante —, usando o mesmo
`contracts_dir()` que o loader usa, sem segunda implementação. A afirmação de
não-vazio preserva a prova do `package-data`: sem ela, `0 == 0` passaria.

E a pergunta desceu para a suíte, em `tests/test_cobertura_dos_contratos.py`. As
duas provas não se substituem: o passo de CI roda em `/tmp` e prova **resolução
fora da raiz**; o teste roda na suíte e prova **cobertura**, em segundos e para
quem está editando.

Os outros dois *"seis"* da árvore **não** foram tocados, e a distinção é o
trabalho: os **seis verificadores de invariante** de `tools/` seguem sendo seis, e
os **seis conjuntos da Linha B** de `02` §6.1 seguem sendo seis. Contagem que
envelheceu e contagem que vale têm a mesma forma no `grep`.

### 3.5 Prova negativa das unidades

Verificador tem `_probes.py`; **computador tem violação plantada na
implementação**, fora da árvore, e o número de testes vermelhos é a medida:

| Unidade | Violações plantadas | Reprovadas |
|---|---|---|
| `check_insumo_de_metrica` | 6, mais o positivo do consumidor que só anota | 6 |
| `metrics/epoch.py` | 2 — união virando soma, `rehearsal` sem descarte | 2 |
| `metrics/verificacao.py` | 4 — linhagem, T0 ingênuo, `rehearsal`, desconto | 4 |
| `metrics/declaracao.py` | 5 — `TTID` no primeiro, `TTID` sem predicado, última declaração, qualquer inject, reinício de epoch | 5 |
| derivação das nove siglas | 5, plantadas **na tabela**, em cópia da spec | 5 |

## 4. A peça 6 — a calibração

Três unidades, mais o `spec-change` que a P6-1 exigiu.

| # | Unidade | O que fecha |
|---|---|---|
| 1 | `contracts/assessment.schema.yaml` | a **reivindicação** que a peça 1 anotou: os dois blocos de `assessment_submitted` saem de `IGNORADOS` |
| 2 | `range-core/metrics/calibracao.py` | Brier no escopo revisado, os três sinais de `03` §5.4, e a lacuna de cobertura |
| 3 | `TTIV` em `metrics/verificacao.py` | `03` §3.3 — a metade cujo verificador não é o mundo. Com ela, as **nove** siglas têm computador |
| — | `spec-change` #47 | a P6-1, resolvida: a acurácia da classificação é rubrica, não calibração |

### 4.1 As decisões que a peça 6 tomou

**Duas normas incidem sobre `assessment_submitted`, e o contrato compõe as duas.**
`03` §5.1 dá à submissão cinco campos; `03` §3.4 a põe entre as nove ações de
declaração e exige de cada uma *"justificativa livre"*. Um contrato fechado só
sobre os cinco campos **recusaria o evento que a rota de produção emite** — e nada
acusaria, porque o event store não valida payload.

Não é redundância a resolver: `rationale` é o raciocínio **sobre o caso**,
`justificativa` é a exigência da §3.4 sobre o **ato de declarar**.

**A composição exigiu medir o `unevaluatedProperties`.** Fechá-lo dentro do `$def`
base não funciona: a palavra fecha no escopo do subschema e não enxerga o que o
pai avaliou. O `$def` base fica **aberto** e o fechamento mora em cada uso —
`assessment_documento` para a submissão como a spec a escreve,
`assessment_submitted_payload` para o evento gravado.

**O Brier tem dois consumidores, e por isso foi extraído.** O escore completo o
reporta ao lado dos sinais; o computador de `TTIV` o recalcula a cada submissão
para achar o instante em que ele cruza o limiar. Escrito duas vezes, divergiria.

**Os sinais não se compensam, e por isso são três listas.** Um número líquido
daria **zero** para a equipe que errou dos dois lados — a leitura exatamente
oposta da verdadeira, e o que `03` §5.4 proíbe por nome.

### 4.2 Fronteiras e limites declarados

**A lacuna de cobertura não entra no Brier**, e o conjunto — não a
defensibilidade — é quem a decide: um pack com `defensibility: 0.7` num indevido
continua produzindo lacuna, porque derivar o conjunto do número apontaria para o
caso errado.

**A borda de `TTIV` é `<=` sobre float, e o limite está dito.** `04` §2 chama o
valor de *"Brier máximo"*, e máximo inclui o valor. Igualdade exata na borda
depende de representabilidade binária — o teste usa `0.25`, que é exato. Um
epsilon trocaria um arbítrio conhecido por outro escondido.

**`review_scope` chega resolvido, e quem o resolve é a P6-5.**

### 4.3 O teste de fronteira que não reprovou ao ser cruzado

A peça 5 escreveu `test_a_unica_sigla_sem_computador_e_ttiv_e_ela_e_da_peca_6`
para reprovar quando `TTIV` ganhasse computador. **A fronteira foi cruzada na peça
6 e ele passou** — estava ancorado em `SIGLA_POR_PREDICADO`, e `TTIV` entrou fora
daquele mapa porque não é predicado.

**A lição:** teste de fronteira ancorado em detalhe de implementação mede o
detalhe, e não a propriedade. Reescrito para **rodar os dois computadores** e
comparar o conjunto de siglas produzidas com as nove da tabela, nas duas direções
— sem lista intermediária para envelhecer.

### 4.4 Prova negativa das unidades

| Unidade | Violações plantadas | Reprovadas |
|---|---|---|
| `metrics/calibracao.py` | 6 — limiares, faixa de defensibilidade, não avaliado, conjunto da lacuna, Brier virando soma | 6 |
| `metrics/verificacao.py` (com `TTIV`) | 5 — linhagem, T0, desconto, limiar estrito, `TTIV` na última | 5 |

**A prova achou um buraco na própria suíte:** encolher `DEFENSIBILIDADE_BAIXA` de
0.2 para 0.0 passava em tudo, porque todos os casos de overconfidence usavam
`defensibility = 0.0` e a borda que `03` §5.4 escreve nunca era exercitada. Dois
casos novos a fecham — 0.2 sinaliza, 0.21 não.

## 5. A peça 7 — a `aar_timeline`

`range-core/aar/` era esqueleto vazio desde a Fase 1. A peça 7 o preenche com a
projeção que `01` §4.1 lista há cinco fases e ninguém tinha escrito.

### 5.1 Por que a janela mora aqui, e não num computador

A janela de asseguração prematura **cruza declaração com verificação**: vai de
`TTCD` a `TTCV`. **Nenhum dos dois computadores pode calculá-la**, porque nenhum
tem as duas metades — e isso é a partição inteira de `00` §3.2, não uma escolha
de organização.

*"`aar_timeline` é o escopo que recebe as duas metades de cada par e computa os
deltas."* A colocação é consequência direta da regra que impede `TTCD` de ser
computado a partir de `TTCV`.

**A prova de que a Fase 6 computa e a Fase 10 renderiza** é
`test_a_janela_NAO_sai_de_computador_de_metrica_nenhum`: ele afirma que o
veredito não chega ao insumo da declaração, que a declaração não chega ao da
verificação, **e** que a janela sai mesmo assim. Sem ele, *"o AAR faz isso"*
seria afirmação sobre uma fase que ainda não chegou.

**Ler o fluxo não fura a partição.** `00` §3.2 particiona o insumo **dos
computadores de métrica**; a `aar_timeline` não é um deles. As `Medida` chegam
prontas, com o decorrido já descontado — refazê-las aqui seria a terceira
implementação do desconto por união.

### 5.2 As três janelas, e o que cada uma carrega

| Janela | Condição | Carrega incompatíveis? |
|---|---|---|
| **asseguração prematura** | declaração **<** verificação | **sim** — os `ground_truth` dentro dela |
| **lacuna de consciência situacional** | declaração **>** verificação | **não** |
| **sem contrassinatura** | integridade declarada e nunca completada | não — e fica **aberta** |

**A lacuna não carrega incompatíveis, e isso é decisão com argumento.** A equipe
estava contida e não sabia: os eventos do intervalo não contradizem declaração
nenhuma, porque não havia declaração ainda. Chamá-los de incompatíveis inverteria
o achado — §3.2 dá a essa janela outra leitura, *"manteve degradação
desnecessária"*, e ela é sobre **custo**, não sobre contradição.

**Só `ground_truth` entra na lista.** §3.2 diz *"os `ground_truth` eventos"*, e
não *"os eventos"*. O que torna a declaração prematura é o **mundo** ter
continuado a se mover; listar ação de participante misturaria a primeira camada
de `00` §3 com a terceira.

**A janela sem contrassinatura fica ABERTA.** `fim = None`, porque o segundo ato
nunca veio. Fechá-la no fim do exercício inventaria um fato — a declaração não
passou a estar contrassinada quando o exercício acabou.

**O predicado de contrassinatura tem agora TRÊS consumidores** — o emissor, o
computador de `TTID` e esta projeção — e **uma** implementação. Foi o que a peça 6
já tinha exigido ao extraí-lo.

### 5.3 A generalização aos três pares, declarada

`03` §3.2 escreve **contenção**, e o exemplo também. Este módulo aplica aos
**três** pares, e a razão está escrita no cabeçalho em vez de deduzida da ausência
de restrição: a seção se chama *"o delta é o achado, nos dois sentidos"*, `03` §3
define três pares, e a forma é idêntica nos três. Restringir a contenção exigiria
uma razão, e não há — integridade declarada antes de verificável é a mesma
leitura, sobre a coisa que `02` §6.2 diz custar mais caro.

### 5.4 A divergência não resolve, e a distância é entre extremos

`03` §2.4: *"não resolve automaticamente; sinaliza para o debriefing"*. Por isso o
alerta carrega os **dois extremos e quem os deu**, e não uma nota consolidada —
consolidar seria resolver.

**A distância é a amplitude, e não a diferença entre consecutivos.** Três
avaliadores em 0, 1 e 2: nenhum par consecutivo alcança dois pontos, e o conjunto
alcança. A §2.4 fala da divergência **na competência**.

O payload de `bars_score_submitted` nasceu aqui, pela regra de sempre — o
consumidor nasce e o contrato com ele. **`competency` não é enumerado nele**: a
lista das nove vive em `rubrics.schema.yaml`, e uma terceira cópia (a §2.3 e o
contrato já são duas) divergiria em silêncio. O cruzamento é por teste.

### 5.5 Prova negativa

| Violação plantada | Vermelhos |
|---|---|
| limiar de divergência sobe para 3 | 2 |
| incompatíveis deixam de filtrar por `ground_truth` | 1 |
| a lacuna passa a carregar incompatíveis | 1 |
| a janela sem contrassinatura confia na emissão | 1 |

## 6. Pendências

Abertas antes da fase, no `spec-change` `particao-das-metricas-pareadas`.
Prefixo `P6-`.

| Id | O que é | Vence em |
|---|---|---|
| P6-1 | `classification_declared` não é caso calibrável, e `03` §3.0 aponta a acurácia da classificação para a calibração | **VENCIDA E RESOLVIDA** — `spec-change` #47 |
| P6-2 | `observable_impact` não existe em contrato nenhum, e é o *start* de `TTA` | **Fase 6** — ver abaixo |
| P6-3 | `before`, `after` e a comparação de `since` dependem de uma gramática de `exercise_time` que não existe | **condição** — ver abaixo |
| P6-4 | ensaio descartado leva embora o `exercise_started`, e T0 fica sem origem | **fechada** — decidida pelo operador, ver abaixo |
| P6-5 | `review_scope` é prosa, e nada resolve a prosa num conjunto de `case_id` | **DECIDIDA** — entrega na Fase 7 |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e **não** `Bash` | **condição** — ver abaixo |
| P6-7 | rota nova pode declarar `emite` e não chamar emissor nenhum | **condição** — ver abaixo |
| P6-8 | justificativa ausente devolve `409`, e `409` é reservado a recusa de estado | **condição** — ver abaixo |
| P6-9 | a cópia instalada do hook do auditor não é sincronizada por ninguém | **condição** — ver abaixo |
| P6-10 | hook declarado sem emissor, e nenhum verificador cruza hooks com emissores | **condição** — ver abaixo |
| P6-11 | payload cru alimenta o Brier: `confidence: 900` produz escore 64,0 | **decisão** — ver abaixo |

#### P6-1 — a calibração não cobre a classificação, e a §3.0 aponta para ela

`03_EXERCISE_DESIGN.md` §3.0 defende que `TTT` não tem par com dois argumentos.
O primeiro é suficiente sozinho: o verificador seria parametrizado pelo conteúdo
da declaração, e severidade declarada errada para mais produz instante
inexistente e métrica indefinida.

O segundo é de **categoria**: a acurácia de um atributo declarado é matéria de
calibração, não de distância entre instantes. Ele classifica corretamente e
**não afirma cobertura** — a §5 escora o Brier sobre os casos de Linha B
(`assessment_submitted`), e `classification_declared` não é um deles. O texto da
§3.0 diz isso com todas as letras, de propósito.

**A pendência é a decisão que ficou de fora:** estender a §5 para admitir a
classificação como caso calibrável, ou deixar a acurácia da classificação com a
rubrica `incident_triage` (§2.3) e parar de mencionar calibração ali.

Decidido pelo operador que a **§5 não cresce neste spec-change**. Fica para
quando o escore de calibração for implementado — é ali que se descobre se o
mecanismo comporta um caso que não vem de `line_b_cases`.

**Vence em:** o commit em que o escore de calibração da Fase 6 pontuar o primeiro
`assessment_submitted` contra o gabarito.

##### VENCIDA E RESOLVIDA na peça 6 — a medição, e o caminho escolhido

O escore existe (`range-core/metrics/calibracao.py`), e com ele a pergunta que a
pendência guardava deixou de ser especulativa: **o mecanismo comporta um caso que
não vem de `line_b_cases`?**

**Medido: não comporta, e faltam três coisas — não uma.**

| O que o Brier de §5.3 exige | O que `classification_declared` tem |
|---|---|
| um **conjunto** de casos, para haver média | **uma** classificação por exercício — média de um elemento é o erro quadrático, e §5.3 chama o escore de *"comparável entre exercícios e entre equipes"* |
| `confidence` 0–100 no ato | `03` §3 descreve o ato como *"severidade e escopo"*; **não há campo de confiança** |
| `defensibility` no gabarito | `line_b_case` é a única entrada com `defensibility`, e ela é keyed por `case_id` `^GC-[0-9]+$` |

Estender a §5 para admiti-la exigiria, portanto, **duas alterações de contrato** —
um campo de confiança em `classification_declared` e uma entrada de
defensibilidade fora de `line_b_cases` — além do texto da §5. Não é acréscimo de
linha.

**RESOLVIDA pelo operador: remover a menção**, e deixar a acurácia da
classificação com a rubrica `incident_triage` (§2.3). Executado no `spec-change`
`acuracia-da-classificacao-e-rubrica` — PR #47, mergeado por rebase com os quatro
checks verdes.

**O fundamento é de duplicação, e não de custo.** Estender a §5 criaria um
**segundo número sobre a mesma coisa** — rubrica e escore pontuando o mesmo
julgamento, sem regra de precedência entre eles. É a forma do argumento que já
mantém `TTT` sem par: duplicar mecanismo é pior que medir uma vez só. A correção
fica menor que o defeito.

**E a acurácia já tinha casa.** §1.3 põe `incident_triage` e `TTT` na **mesma
linha** do OBJ-03; o exemplo normativo de §1.1 traz `rubric: incident_triage.v2`
e `metric_binding: TTT` no mesmo objetivo. A §3.0 não criou endereço — apontou o
que a spec já tinha. E a calibração também já tem o dela na mesma tabela: é a
métrica do **OBJ-04**, não do OBJ-03.

**A medição acima fica preservada de propósito.** Ela é a evidência de por que a
outra opção caiu, e some se a pendência for apenas apagada — que é a forma pela
qual uma decisão vira folclore: o resultado sobrevive e o argumento não.

**A varredura achou TRÊS sítios, e não dois.** O terceiro estava em
`00_MASTER_SPEC.md` §3.2 — o documento de autoridade, e o que define a cláusula
(1) do critério de partição. Corrigir só `03` teria deixado a norma-mãe mandando
para a §5 enquanto a norma-filha mandava para a rubrica. É a mesma varredura que
faltou quando a peça 1 criou o sétimo contrato (§3.4).

**O que a peça 6 fez no código:** nada que antecipasse a decisão. `classification`
é campo do contrato de assessment e **é gravado**; o que ele não faz é pontuar.
Está dito no cabeçalho de `contracts/assessment.schema.yaml`.

#### P6-2 — o start de `TTA` não tem origem em contrato nenhum

`03_EXERCISE_DESIGN.md` §3 define o *start* de `TTA` como *"primeiro inject com
impacto observável"*, e `00_MASTER_SPEC.md` §3.2 exige que a escolha entre
injects seja **cálculo do consumidor** sobre atributos que viajam no payload de
`inject_fired` — nunca recorte do montador do insumo.

**O atributo não existe.** Medido na árvore: `requires_response`, que é o *start*
de `TTCM`, existe em `contracts/scenario.schema.v2.yaml` como campo de
`media_event`. Um marcador de impacto observável não existe nem no schema de
cenário nem no de eventos, e `inject_fired` hoje não emite payload nenhum —
`range-core/engine/inject_engine.py` chama `_append(INJECT_FIRED,
inject_id=inject.id)`, e `inject_id` é campo de **envelope**, não de payload.

Sem origem, `TTA` não é computável, e a norma fica apontando para mecanismo
inexistente — que é exatamente a classe de defeito que o `spec-change` que a
criou existe para corrigir.

**A bifurcação, para decisão:**

**(a) Campo no pack.** `inject` ganha `observable_impact: boolean` em
`contracts/scenario.schema.v2.yaml`, o autor do cenário o declara, e
`inject_fired` o repassa no payload.

- *A favor:* impacto observável é juízo de desenho de exercício, e quem sabe se
  um inject é visível para a sala é quem o escreveu.
- *Contra:* é uma terceira alteração de contrato, e mexe no schema de **pack**,
  que tem regime de versão próprio — `04_SCENARIO_SCHEMA.md` §4 e
  `SUPPORTED_SCHEMA_VERSIONS = [N, N-1]`. Campo novo não altera semântica de
  campo existente, então não força bump; mas pack em N-1 não o traz, e o
  comportamento na ausência precisa ser decidido junto.

**(b) Derivação do motor.** O motor deriva o marcador dos `effects` do inject —
inject que move flag tem impacto observável; inject que não move, não tem.

- *A favor:* não toca o schema de pack, e liga o marcador ao que a sala de fato
  vê, que é a flag mudando de estado.
- *Contra:* impacto observável passa a ser consequência de mecanismo, e não
  declaração de autoria; um inject de impacto puramente narrativo — imprensa
  ligando, sem flag — ficaria fora do *start* de `TTA` sem que ninguém tivesse
  decidido isso.

**DECIDIDA — ramo (b), com o predicado declarado na spec.** O `spec-change`
`impacto-observavel-definido` define impacto observável em `03` §3, e a
derivação passa a ser norma em vez de escolha de implementação.

**O predicado ditado não sobreviveu à verificação, e a correção está no PR.** A
primeira redação dizia *"inject cujos `effects` produzem ao menos um evento de
`truth_layer: observable_evidence`"*. Medido na árvore: `effects` é mutação de
flag e **não emite evento nenhum** — `01` §4.4 registra que os `effects` são
resolvidos contra o pack pelo fold e não gravados no store. Ao pé da letra o
predicado é vazio e `TTA` nunca começa; lido de forma frouxa, exclui o inject
que derruba o portal, que é o impacto mais observável que a sala tem.

O predicado aprovado tem três pernas — `effects`, `materializes_facts` com fato
que tenha `projections`, e `evidence_release` — e a exclusão decidida recai
sobre `reveals`, que alimenta crença do participante e não o mundo.

O payload de `inject_fired` nasce na branch da Fase 6, junto do emissor e do
teste de emissão, que são todos código e cabem no mesmo PR.

**Vence em:** o commit em que o consumidor de `TTA` for desenhado — é ele que
força a escolha, e antes dele a decisão seria tomada sem o caso de uso à vista.

#### P6-3 — uma gramática de `exercise_time`, e as três folhas que dependem dela

`contracts/ground_truth.schema.yaml` admite `predicate_before` e
`predicate_after` na gramática de predicado. O avaliador da peça 4 **não os
implementa**: eles comparam contra o relógio de exercício, que não é parte do
mundo que ele monta.

**A recusa mudou de instante, e não de existência.** `confere_folhas_temporais`
recusa o pack **na carga**, nomeando a folha e o motivo — enquanto ainda dá para
consertar o pack. Sem ela, o pack carregaria limpo e a falha chegaria **na
avaliação**, no instante em que a contenção deveria ser conferida, que é o pior
momento possível para descobrir uma ausência de implementação. É o padrão da
guarda de boot do emissor.

`PredicadoMalformado` permanece no avaliador como **segunda linha de defesa**,
para o caso de um predicado chegar por outro caminho.

**Vence em:** a implementação do suporte temporal, **ou** o primeiro pack que
precisar de uma folha temporal — o que vier primeiro. Se vier o pack, é
**decisão do proprietário** antes de qualquer improviso: o que o predicado
temporal compara — `exercise_time`, `exercise_timestamp` ou marca de parede — é
escolha normativa, e as três dão resultados diferentes depois de um rollback.

##### A TERCEIRA FOLHA — `since` entrou aqui, e não abriu pendência própria

**H1 da quarta auditoria**, e a leitura que decidiu foi do proprietário: o
instante do fato é o **declarado** (`fact.exercise_time`), e não o do evento
`fact_materialized`. O fato é o objeto do ground truth; o instante do evento é
quando o simulador contou — metadado de emissão. Fundar `since` no segundo faria
a semântica de contenção depender de **quando o produtor grava**, que é
implementação de outra fase decidindo norma desta.

**Por que uma pendência e não duas.** `since`, `before` e `after` comparam contra
o mesmo campo. Duas gramáticas para `exercise_time` — uma para o qualificador,
outra para as folhas — divergiriam, e a divergência apareceria como predicado que
verifica num caminho e não no outro. É a D4 da Fase 1 outra vez: uma decisão, três
folhas, uma gramática. Por isso o que seria a **P6-12 é esta seção**, e não uma
linha nova na tabela.

**O que trava, medido e não suposto:**

| | Medição |
|---|---|
| produtor de `fact_materialized` | **não existe**. O tipo está no catálogo, é lido em `verificacao.py` ao montar o mundo, e a única escrita no repositório é à mão, em `tests/test_aar_timeline.py` |
| o instante declarado | `fact.exercise_time` é `minLength: 1` no contrato, e o exemplo normativo traz `'T-17d 02:14'` — **não há gramática**, e o `_T_RELATIVE` do loader (`HH:MM`) não representa dia negativo |
| o mundo | `Mundo.fatos` carrega **classes**, não instantes. Situar um fato exige carregar o instante junto, o que só faz sentido depois da gramática |

**É a medição do produtor ausente que torna o adiamento legítimo**, e ela é o que
precisa sobreviver a esta seção: sem produtor, `Mundo.fatos` é vazio em produção,
e **nenhum comportamento de hoje depende da escolha**. O que se adia é a
comparação, não a semântica — a semântica está na `03` §3.1 desde o
`spec-change` #49.

**O que foi implementado agora**, e por que não esperou:

- **o instante de referência**, derivado da linhagem corrente —
  `instante_de_referencia`: o `rollback_performed` da corrente, ou o
  `exercise_started` na epoch 0. É a metade da §3.1 que **não** depende de
  gramática, e é ela que faz o predicado normativo carregar e satisfazer;
- **a guarda de carga**, com as duas pernas que são defeito permanente: valor
  não definido, e contenção com `absence_of` sem `since` — a forma curta em
  string incluída, senão a exigência seria contornável por escrita;
- **a segunda linha no avaliador**: `since` desconhecido recusa alto, e a classe
  presente no mundo levanta `SemGramaticaTemporal` em vez de responder. As duas
  respostas plausíveis são piores — falso faz a contenção nunca verificar,
  verdadeiro a faz verificar com vazamento em curso.

**Não houve perna para `since: self` na guarda**, e essa foi correção de rota do
proprietário sobre o desenho que eu havia trazido. Recusar a forma normativa na
carga faria o `ransomware-universidade` — o cenário que a spec inteira ilustra —
**deixar de carregar**: pior que o defeito que corrigiria. O H1 fazia `TTCV` não
marcar num cenário; a guarda faria o cenário não existir.

**Vence em:** a gramática de `exercise_time`. Ela fecha as três folhas de uma
vez, e o gatilho continua sendo o que já estava escrito acima — o primeiro pack
que precise, ou a implementação do suporte temporal. Acrescenta-se um terceiro: o
primeiro produtor de `fact_materialized`, que baterá em `SemGramaticaTemporal` na
primeira execução. É deliberado que bata: a decisão precisa acontecer ali.

#### P6-4 — o ensaio descartado leva embora o `exercise_started`

As métricas pareadas medem desde **T0**, e T0 é recuperado do `exercise_started`
pela identidade de `01` §4.4 — `exercise_timestamp == T0 + exercise_time`.

`09` §3.1 dá a `rehearsal` o efeito *"nenhum evento da epoch entra em cálculo"*, e
o rollback de ensaio carrega a epoch que **encerra**. Um ensaio rodado na epoch 0
e descartado leva junto o `exercise_started`, que vive nela — e **não há segundo
`exercise_started`**, porque rollback não reabre exercício.

**É alcançável, e não teórico: é exatamente o caso de uso do motivo** — rodar um
aquecimento e jogá-lo fora. Sem T0, `desde_t0` some de todas as siglas.

**DECIDIDA pelo operador: T0 é atributo do exercício, não da epoch.** Ele
sobrevive ao descarte de qualquer epoch porque **não pertence a nenhuma**.

**Fundamento.** `01_ARCHITECTURE.md` §3 — *"T0 definido pelo facilitador"*. O
`exercise_started` **registra o ato, não é a fonte dele**. O descarte de `09`
§3.1 tira **eventos** do cálculo, e T0 não é um evento: é o zero contra o qual
os eventos são medidos.

**As duas alternativas caem por mérito**, e ficam escritas para não voltarem:

- **T0 do `exercise_started` da epoch nova** encolheria `TTA`, `TTT` e `TTCM`
  pelo tempo do ensaio, **silenciosamente** — as três têm start próprio, e o
  start deslocaria junto;
- **T0 do evento descartado, com o evento em cálculo** contradiz `09` §3.1 na
  letra: *"nenhum evento da epoch entra em cálculo"*.

#### A condição de contorno do multiplicador, e como ela foi tratada

Um ensaio a 5x ou 20x consome **tempo de exercício** que não é tempo do
exercício de verdade: dez minutos de parede a 20x são duzentos minutos de
`exercise_timestamp`. E o relógio **não rebobina** no rollback — só o rótulo
`T+` rebobina —, então esses duzentos minutos ficam embutidos em tudo o que vem
depois.

Com T0 preservado, sem tratamento eles entrariam em toda métrica medida desde
T0. **O tratamento é o mecanismo que já existia:** o intervalo da epoch
descartada entra no **desconto por união** de `range-core/metrics/epoch.py`, como
um motivo a mais na mesma tabela — nunca um caminho paralelo.

Os dois extremos saem da escrituração, e não de campo novo no payload: **fim** é
o `exercise_timestamp` do rollback de `rehearsal`, **início** é o do rollback que
fechou a epoch anterior — ou T0, para a epoch 0. `frozen_interval` continua sendo
do `technical_failure`, onde o facilitador registra o trecho em que o range
esteve quebrado; aqui o trecho é a epoch inteira, e ela já está descrita pelos
rollbacks que a delimitam.

**Por que a mesma tabela importa:** um `technical_failure` dentro do ensaio é
**absorvido pela união** em vez de descontado duas vezes. Em caminhos paralelos,
o trecho comum sairia duplicado — o defeito exato que T10 proíbe ao exigir união
em vez de soma. Há teste nomeado para isso.

**E o multiplicador não aparece na conta.** Medir por extremos de
`exercise_timestamp` já o incorpora, porque é ele que avança na cadência do
multiplicador. Medir por parede exigiria o `clock_multiplier` de cada trecho, e
um ensaio com troca de multiplicador no meio teria dois.

#### A identidade de `01` §4.4 recupera o zero — verificado antes de implementar

A exigência era parar e escalar se ela não recuperasse. **Ela recupera**, e o
motivo é mecânico: `marks()` calcula `exercise_time = _label(elapsed −
epoch_started_at)` e `exercise_timestamp = T0 + elapsed`. A identidade vale onde
`epoch_started_at == 0`, que é a **epoch 0** — e o `exercise_started` que abre o
exercício é anterior a qualquer rollback, logo vive nela.

O truncamento fecha junto: `_label` trunca ao segundo e o `isoformat` do
timestamp usa `timespec="seconds"`. Os dois truncam o **mesmo** `elapsed` ao
mesmo segundo, e a subtração devolve T0 exato. Não há `spec-change` a fazer.

**`marco_zero` continua levantando**, e só a origem mudou: exercício sem
`exercise_started` nenhum não produz métrica. O gatilho deixou de ser o ensaio
descartado e passou a ser o caso honesto — métrica computada sobre fluxo em que
o exercício nunca começou.

#### P6-5 — `review_scope` é prosa, e ninguém a resolve em casos

`03` §5.1 manda a equipe declarar **escopo revisado** — *"período, população,
critério"* — antes de submeter, e §5.3 usa a declaração para separar duas coisas
que o AAR precisa ver separadas: **erro de julgamento** (caso no escopo, avaliado
errado) e **lacuna de cobertura** (indevido comprovado fora do escopo).

O escore precisa, portanto, do **conjunto de `case_id` dentro do escopo**. Ele
não é derivável do que a Fase 6 tem à mão.

**Medido:** `line_b_case`, em `contracts/ground_truth.schema.yaml`, tem
`case_id`, `defensibility`, `set` e `supporting_evidence` — e **nenhum atributo
de data ou de população**. Os atributos que um período ou uma população filtram
vivem nas linhas da trilha de auditoria, no banco semeado, e não no gabarito.

**O que a peça 6 fez.** `escore()` recebe `escopo: frozenset[str]` como **dado**,
pelo mesmo argumento com que `00` §3.2 manda os escalares chegarem ao verificador
de `TTIV` em vez de por consulta ao pack. Derivá-lo aqui por inferência seria
inventar um filtro que nenhum documento fixa — e o Brier passaria a medir a
inferência junto com a equipe.

**O que não se decidiu, e não é equivalente:**

- **quem resolve** — a `academus-api`, que tem as linhas; o gerador do seed, que
  as plantou; ou o próprio `review_scope`, se ele passar a carregar a lista
  resolvida no ato da declaração;
- **quando** — na abertura do escopo (a lista congela e o AAR sabe o que a equipe
  disse que ia olhar) ou no fechamento do escore (a lista reflete o banco no
  instante do cálculo, e muda se o banco mudar).

As duas perguntas têm consequência de norma: a segunda decide se declarar escopo
largo e revisar pouco é distinguível de declarar escopo estreito.

**Vencia em:** o primeiro exercício que computasse Brier sobre um pack real, ou a
Fase 10. Foi decidida antes, com o mapa das três opções à vista.

##### DECIDIDA na peça 7 — `review_scope` carrega a lista, resolvida no fechamento

**Decisão do operador: opção 3.** `review_scope` passa a carregar a lista de
`case_id` que o escopo alcança, e ela é resolvida no **fechamento** do escore —
não na abertura. **Entrega na Fase 7**, porque é mudança de contrato.

**Por que o fechamento, e não a abertura.** É o fechamento que distingue **escopo
largo com revisão rasa** de **escopo estreito** — e essa distinção é precisamente
o que a calibração mede. Congelar na abertura tornaria a declaração inauditável
contra o que foi de fato revisado: a equipe declararia intenção, e o Brier
pontuaria a intenção.

**As duas opções rejeitadas, com o custo preservado** — elas são a evidência de
por que a terceira venceu, e somem se a pendência for apenas fechada:

| Opção | O que oferecia | Por que caiu |
|---|---|---|
| **`academus-api` resolve** | tem as linhas da trilha e já tem o console de investigação | o conjunto resolvido chegaria ao core **vindo do adapter**. O invariante 1 **varre import, e não vocabulário** — a Fase 4 registrou isso ao separar papel de exercício de papel de domínio, e precisou de `check_api_surface.py` para guardar o que o invariante não alcança. Aqui a travessia seria **por dado**, e nenhum invariante a veria |
| **Gerador do seed resolve** | plantou os casos e conhece os atributos | cai por **tempo**: ele resolve na geração, e o escopo é declarado em *runtime*. Escopo que a equipe escreve durante o exercício não teria como ser resolvido por quem já terminou de rodar |

**O que a Fase 6 deixa pronto para ela.** `escopo_revisado` já é escalar do
`InsumoDeVerificacao`, declarado em `CAMPOS_DECLARADOS` do
`check_insumo_de_metrica.py`, e `escore()` já o recebe como dado. A Fase 7 muda
**de onde ele vem** — não a forma como chega ao consumidor, que `00` §3.2 já
fixou.

#### P6-6 — o sentinela de branch não enxerga escrita por `Bash`

A D15 existe para pegar a corrida em que a branch muda no meio da sessão e o
trabalho pensado sobre uma árvore é gravado noutra. **Ela funcionou nesta
sessão** — recusou uma escrita minha quando criei a branch do `spec-change`,
exigiu re-ancoragem explícita, e a re-ancoragem não tem atalho de um clique.

**A medição, e ela é de configuração, não de simulação.** O hook é declarado em
`~/.claude/settings.json` assim:

```json
{ "PreToolUse": [ { "matcher": "Edit|Write|NotebookEdit", ... } ] }
```

`Bash` **não está no matcher**. Não é que o sentinela avalie e libere — ele
**nunca é invocado** para escrita feita por `Bash`. O mesmo vale para o hook de
invariantes do projeto (`.claude/hooks/check_architecture.py`), declarado em
`.claude/settings.json` com o matcher `Edit|Write`.

> **Tentei a medição mais forte e ela não foi fiel, então não a apresento como
> prova.** Disparei os cinco payloads contra o hook com a âncora posta em
> desacordo de propósito; **todos** passaram, inclusive `Write` — que na sessão
> real havia sido recusado. O motivo: o sentinela chaveia por `session_id`, e o
> subprocess não o forneceu. O que sustenta esta pendência é a linha de
> configuração acima, que é fato verificável.

**O custo, medido no que dá para medir.** Nesta sessão, **não menos que 25**
chamadas de `Bash` escreveram em arquivo rastreado — `sed -i` para os contadores
do README e do probe, e `python - <<PY` com `write_text` para módulos, contratos,
testes, o lançador e este próprio registro. O número exato **não é
reconstruível da árvore**, e essa é a parte mais afiada do achado: o canal não
deixa rastro que o repositório saiba auditar. Os dois canais interceptados
deixam.

**O que ele deixaria de pegar num caso ruim.** Exatamente o cenário da D15: a
branch muda — por `git checkout` do operador, por um rebase, por um `worktree` —
e a próxima edição por `sed -i` ou por heredoc grava na árvore errada, sem
recusa e sem aviso. O trabalho pensado sobre a fase entraria num `spec-change`,
ou o inverso, e o `spec_freeze` só o pegaria se por acaso os dois conjuntos
tivessem sido tocados.

**Não foi corrigido no PR #48, e a omissão é decisão.** Aquele PR conserta o
buraco do interpretador do auditor; alargar um guarda dentro do PR que conserta
outro é o acoplamento que este repositório recusa desde a regra de `spec-change`
separado. E a correção não é uma linha: `Bash` no matcher faria o hook opinar
sobre **todo** comando, e ele hoje decide por `file_path` — não há `file_path`
num `sed -i`. Decidir por texto de comando é o problema que
`readonly_bash.py` já resolve com allowlist, e replicá-lo aqui seria a segunda
implementação da mesma pergunta.

**As três formas, para quando a decisão vier:**

1. **`Bash` no matcher do sentinela**, com detecção de escrita por texto de
   comando — segunda implementação da pergunta que `readonly_bash.py` responde;
2. **guarda no `PostToolUse`**, comparando a branch antes e depois — pega a
   corrida em vez de preveni-la, e o dano já estaria gravado;
3. **disciplina declarada**: escrita em arquivo rastreado passa por `Write`/`Edit`,
   e `Bash` fica para comando. É a mais barata e é **disciplina**, que a §1.6 do
   registro da Fase 1 separa de impedimento — e disciplina foi o que falhou nas
   quatro reincidências da D16.

**Vence em:** a primeira sessão que trabalhe em duas branches, **ou** a Fase 8,
quando o paralelismo começar e várias branches viverem ao mesmo tempo — o que
vier primeiro. É **decisão do proprietário**: as três têm custos de natureza
diferente, e a terceira admite que o guarda não guarda.

#### P6-7 — rota que declara `emite` e não chama emissor nenhum

O B2 fechou o item 1 da DoD com **duas** provas fortes cobrindo **dez** rotas, e
isso só é possível por uma propriedade **estrutural**: as nove declarações passam
todas por `_declara`, e `GET /audit/grade-changes` chama o emissor no próprio
corpo. Mutar qualquer um dos dois pontos deixa a suíte vermelha — medido, cinco
mutações em cada.

**O que continua aberto é a classe, e não a instância.** Uma rota nova que declare
`emite` em `api_surface.yaml` e não passe por nenhum dos dois pontos nasce sem
prova de emissão, e nada acusa: `check_api_surface.py` confere que a rota
**declara** `emite`, e não que ela **emite**.

É a classe do achado original — verificação que parece existir —, agora com o
gatilho conhecido.

**A verificação por AST foi considerada e DESCARTADA**, com o motivo medido. O
critério fraco *"o handler, ou função no mesmo módulo, referencia o emissor"* erra
nos **dois** sentidos: referenciar não é chamar, e handler correto em outro módulo
reprovaria. Fraqueza declarada com taxa de erro desconhecida é pior que ausência
dita — e a medição que a matou foi a mesma que revelou a saída: um AST ingênuo
reprovaria as nove rotas **estando elas corretas**, porque o handler chama
`_declara` e não o emissor.

**As duas formas, com o custo de cada lado:**

| Forma | O que compra | O que custa |
|---|---|---|
| **Análise de fluxo** | responde à pergunta certa — *"esta rota, executada, emite?"* — sem convenção nenhuma | outra ordem de esforço: seguir cadeia de chamadas entre módulos, com alias, indireção e `getattr`. E um analisador incompleto volta a ser fraqueza com taxa de erro desconhecida, que é o que acabou de ser descartado |
| **Convenção estrutural imposta por verificador** | transforma a pergunta difícil em fácil: *"toda rota que declara `emite` passa por um ponto de emissão nomeado"* é decidível por AST simples | é convenção — obriga rota futura a entrar por um dos pontos, e a que não entrar reprova mesmo estando correta. O custo é de desenho, não de detecção |

A segunda é a forma que este repositório **já usa** em outros lugares: whitelist
de superfície em `check_store_read_surface.py`, ponto único de montagem em
`check_insumo_de_metrica.py`, ponto único de emissão no próprio `Emissor` — que
já existe justamente para o handler não decidir camada, produtor e payload.

**Vence em:** a próxima rota que declare `emite`, **ou** a Fase 8, quando o
paralelismo multiplicar quem escreve rota — o que vier primeiro. É **decisão do
proprietário**: a primeira compra exatidão e custa esforço; a segunda compra
verificabilidade e custa liberdade de desenho.

#### P6-8 — justificativa ausente devolve `409`

`_declara` captura `EmissaoRecusada` e responde **409** para todas as causas. O
comentário da própria função reserva o 409 a *"o pedido é bem formado e o ESTADO o
recusa"* e enumera **três**, todas de contrassinatura: antecedente ausente, fora
de ordem, e par já fechado.

**Justificativa ausente não é nenhuma delas.** É campo obrigatório faltando —
pedido malformado —, e o código honesto seria **422**, que é o que as duas rotas
de período inválido já devolvem no adapter.

**O mérito está decidido; o que falta é medição.** Não foi corrigido junto do B2
por duas razões, e as duas são de escopo e não de dúvida:

1. **Mudar status no meio de uma correção de auditoria é escopo crescendo** — a
   mesma razão pela qual o guarda do sentinela não foi alargado dentro do PR do
   venv;
2. **`409` é superfície contratada.** Quem consome a API pode depender dele, e
   `api_surface.yaml` não declara status — então a dependência, se existir, é
   invisível ao verificador.

**O que falta medir antes de mudar:** quem depende do status hoje. O `gm-console`
e a `participant-view` são os consumidores conhecidos; um `grep` por `409` na
árvore de cliente responde metade, e a outra metade é se algum teste o afirma.

**O teste afirma `409`**, e isso é deliberado: teste que descreve o que deveria
ser, e não o que é, não pega regressão. A discrepância está no docstring dele.

**Vence em:** a medição dos consumidores, **ou** a Fase 10, quando o AAR passar a
ler recusas — o que vier primeiro.

#### P6-9 — a cópia instalada do hook do auditor não é sincronizada por ninguém

**H1 da auditoria da Fase 6, e é a segunda ocorrência.** A primeira foi nesta
mesma sessão: `phase0_negative_tests.py` acusou divergência entre
`user-scope/hooks/readonly_bash.py` e a cópia em `~/.claude/hooks/`, e eu copiei
à mão.

**A consequência é real e não é cosmética.** Na auditoria, o hook instalado —
sem a entrada de `check_insumo_de_metrica` — **bloqueou** o verificador central
da peça 5, e o harness negativo saiu `rc=1`. O auditor não conseguiu executar o
mecanismo que fecha a exigência (3) de `00` §3.2.

**E o mecanismo que deveria acusar isso lê o lado errado.**
`check_allowlist_do_auditor.py` sai `RC=0` porque lê a **fonte versionada** —
ele responde *"a fonte declara o script?"*, e não *"o auditor consegue
executá-lo?"*. As duas perguntas pareciam a mesma até esta auditoria.

**O commit fez a parte dele**: a entrada está na fonte e o CI roda os dois
scripts. O defeito está **fora da árvore**, e é por isso que nenhum gate o
alcança — é a mesma classe da P6-6, o guarda que não cobre o canal por onde a
coisa acontece.

**As três formas, com o custo:**

| Forma | O que compra | O que custa |
|---|---|---|
| **O lançador sincroniza** | a auditoria nunca roda com hook velho, e o passo fica ao lado do que já monta venv e worktree | o lançador passa a **escrever em `~/.claude/`**, fora da árvore. Hoje ele só escreve em `.aurora-worktrees/` e no worktree; ampliar isso é dar-lhe alcance sobre a configuração do usuário |
| **O `phase0` falhar mais cedo** | o operador descobre antes de abrir a sessão, e não no meio dela | não conserta — apenas antecipa. E `phase0_negative_tests.py` **já acusa**: foi ele que pegou nas duas vezes. O que falta não é detecção, é o passo ficar **antes** do lançador abrir a janela |
| **O lançador RECUSAR quando divergem** | falha alta, sem escrever nada fora da árvore, e na forma que o repositório já usa para venv e âncora | exige ação manual do operador a cada mudança do hook — disciplina, que a §1.6 da Fase 1 separa de impedimento e que falhou nas quatro reincidências da D16 |

**A terceira é a que mais se parece com o resto do aparato** — o lançador já
recusa alto por âncora desatualizada, por árvore suja e por venv que não instala.
Mas ela deixa a sincronia como disciplina, e disciplina é o que falhou duas vezes
aqui.

**Não decidida.** As três têm custos de natureza diferente: a primeira amplia o
alcance de escrita do lançador, a segunda não conserta, e a terceira admite
depender de disciplina.

**Vence em:** a próxima auditoria de checkpoint — ela é a terceira oportunidade
para a mesma divergência, e as duas anteriores ocorreram.

#### P6-10 — hook declarado sem emissor, e o verificador que não existe

**M2 da terceira auditoria.** `domains/academus/observability_hooks.yaml` declara
`vpn_access_revoked` com `producer: federated-identity-simulator`, e esse
simulador é da **Fase 11**. `06` T9 exige que todo `event_type` do arquivo seja
emitido pela ação correspondente — e o critério é **da Fase 6**.

**A leitura, com o custo dos dois lados.** A pergunta é se hook declarado sem
emissor é pendência legítima até a fase do produtor, ou se ele não deveria estar
declarado ainda:

| Leitura | A favor | Contra |
|---|---|---|
| **Declarar com destinatário é legítimo** | é a mesma forma que `check_secoes_de_seguranca.py` já impõe a `05`: cada seção tem *mecanismo ou destinatário*, e destinatário declarado é melhor que ausência. O hook documenta o contrato do evento antes de o produtor existir, e a Fase 11 encontra a forma pronta | T9 não distingue *"declarado com destinatário"* de *"declarado"*. Enquanto não distinguir, o critério é **insatisfazível por construção** para este hook — a classe que a peça 3 já corrigiu com um `spec-change` quando `separate_incident_declared` não tinha ação |
| **Não declarar até haver produtor** | T9 volta a ser satisfazível sem exceção, e o arquivo descreve só o que existe | perde-se a declaração antecipada, e o contrato do evento nasce junto com o produtor — que é quando ninguém está olhando para o desenho. E `05` §6 mostra que ausência sem motivo é pior que presença com destinatário |

**A escolha tem consequência normativa**, e é por isso que não a tomo: se a
primeira vence, T9 precisa de `spec-change` para admitir o destinatário; se a
segunda, o hook sai do arquivo agora.

**O agravante, e ele é independente da escolha.** **Não existe verificador
cruzando os hooks com os emissores reais.** `check_contract_literals.py` confere
que o `event_type` do hook está no catálogo — e não que alguém o emite. O
`payload_fields` é cruzado com a assinatura do emissor **apenas para
`audit_query_performed`**, e por um teste escrito à mão.

Então hoje: hook com `event_type` válido e produtor inexistente **passa em todos
os gates**. É a mesma família da P6-7 — declaração conferida, emissão não.

**O mapa do verificador:**

| Forma | O que compra | O que custa |
|---|---|---|
| **Cruzar hook × emissor por AST** | responde *"alguém emite este tipo?"* | esbarra na mesma dificuldade da P6-7: o emissor é um método por hook, e achar quem o chama é análise de fluxo |
| **Cruzar hook × catálogo de produtores declarados** | barato e decidível: cada hook nomeia `producer`, e o repositório sabe quais produtores existem | não prova emissão — prova que o produtor existe. É guarda mais fraca, e a fraqueza tem de ficar dita |
| **Exigir `fase_destinataria` no hook sem produtor** | torna a dívida legível e cobrável, na forma do registro de seções de segurança | é declaração, não detecção: hook que minta sobre o destinatário passa |

**Vence em:** a decisão da leitura acima, **ou** a Fase 11, quando o produtor
chegar — o que vier primeiro.

#### P6-11 — payload cru alimenta o Brier

**L1 da terceira auditoria, e a medição é o argumento.** Medido nesta árvore:

```
confidence: 900  ->  brier = 64.0
```

Sessenta e quatro vezes o pior escore possível de uma entrada válida. `TTIV`
compara esse número com `calibration.threshold` — então um payload fora de faixa
**desloca o instante de `TTIV`**, ou o impede para sempre. É a forma que esta
fase existe para impedir: nada falha, a métrica continua sendo calculada.

**O contrato já bane.** `assessment.schema.yaml` fixa `confidence` em 0–100
inteiro. O que falta é aplicação: **o event store não valida payload**, e isso
vale para todo evento.

**A proposta, com o argumento — para decisão.** Três lugares, e eu recomendo o
terceiro:

| Onde | A favor | Contra |
|---|---|---|
| **Na rota** | mais cedo: a submissão inválida nunca vira evento, e o participante recebe `422` em vez de um escore estranho no AAR | não cobre evento que entre por outro caminho — importação, reconstrução, produtor futuro. E o store continua aceitando: a garantia vale para **esta** porta, não para a propriedade |
| **No insumo** (`monta`) | um ponto para os dois lados, e é onde a partição já vive | **contradiz `00` §3.2**: o montador não pode ter regra própria. *"O número certo aparecendo por ausência de insumo em vez de por cálculo"* é o defeito que a seção nomeia, e descartar submissão inválida ali é exatamente isso |
| **No computador** ✅ | é **cálculo do consumidor**, que é a forma que `00` §3.2 exige. `_por_caso` já ignora payload malformado — falta `confidence` fora de faixa ser malformado também. E a decisão fica **visível e testável**, em vez de embutida numa porta |

**O que a terceira ainda deixa aberto, dito:** ignorar silenciosamente uma
submissão fora de faixa a transforma em *"não avaliado"*, que pontua como
`confidence = 0`. Isso é uma **decisão**, não uma consequência — e a alternativa
é recusar alto, que faria um payload inválido derrubar o escore inteiro.

Minha leitura: **ignorar e nomear**, como `Calibracao.nao_avaliados` já faz —
o AAR precisa distinguir *"não avaliou"* de *"avaliou com payload inválido"*, e
uma terceira lista é mais barata que qualquer das outras opções.

**Vence em:** esta decisão. É a única pendência da fase que **não** espera
condição externa — o mecanismo existe e o lugar está escolhido; falta a sua
palavra sobre ignorar × recusar.
