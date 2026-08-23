# Fase 6 — Objetivos, rubricas, métricas

**Status: AUDITADA — PASS na décima rodada, contra `c3051dc5`, sem BLOCKER e sem
HIGH.** 735 testes, `OK`, **0 skip, 0 xfail, 0 falha**, com a stack no ar; os
quatro invariantes verdes, 21 verificadores em `rc=0`, 88 negativos de contrato e
112 provas de invariante do hook executados, as duas provas de container e a
prova do seed conferidas contra este SHA, e `git diff docs/spec/` contra a base
**vazio**. As sete peças estão na tabela da §1; a DoD item a item, no relatório
`audit_20260823T155304Z.md`; as pendências, na §6; as três últimas rodadas, nas
§7 e §8. A âncora é `b794ce23`, regravada no sétimo rebase.

> **ESTA LINHA ENVELHECEU TRÊS VEZES, e as três em arquivos diferentes de quem a
> tornou falsa.** A primeira redação dizia `NÃO INICIADA` e sobreviveu a **cinco
> peças**; a segunda dizia `EM ANDAMENTO — peças 1 a 5 fechadas, peças 6 e 7
> abertas, sem auditoria de checkpoint` e sobreviveu às **sete peças e às dez
> rodadas de auditoria**, com a tabela da §1 dois parágrafos abaixo já dizendo o
> contrário.
>
> **O que separa esta classe das outras que este registro caça:**
> `check_readme_atual.py` **lê esta linha** — ela é a fonte do predicado
> `ultima-fase-concluida`. Não é prosa que envelhece ao lado de um verificador;
> é **entrada de verificador mantida à mão**, e o predicado não tem como reprovar
> a própria entrada que o alimenta. `NÃO INICIADA` passou porque respondia *"não"*
> à pergunta *"a fase fechou?"*, que continuava verdadeira sobre o fechamento e
> era falsa sobre o início; `EM ANDAMENTO` passou pela mesma porta, e por dez
> auditorias, porque a resposta que o predicado extrai dela permaneceu correta o
> tempo todo em que o resto da frase apodrecia.
>
> **Registrado como candidato a mecanismo, e a decisão fica para depois do
> merge.** A forma óbvia — cruzar a linha de status com fatos da árvore que já
> são computados (a tabela de peças do próprio documento, a existência de
> relatório de auditoria para a fase, o veredito do último) — é a mesma do
> `check_readme_atual.py`, aplicada a ele próprio. O que ela custa e o que ela
> deixa passar não foram medidos, e medir dentro do PR de fechamento seria a
> quinta ocorrência da classe da §7.7: escopo crescendo dentro de uma correção.

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

#### A regra irmã, e ela nasceu da terceira ocorrência — B1 da quinta auditoria

**Criar precondição de boot exige varrer quem sobe a stack, no mesmo commit.**

A da §3.4 é sobre **afirmação**: quem diz um número tem de ser encontrado. Esta é
sobre **execução**: quem executa a coisa tem de ser encontrado. A forma do erro é
a mesma — criar de um lado e não varrer o outro —, e por isso as duas moram
juntas; o que muda é o conjunto a varrer, e ele não sai do mesmo `grep`.

**As três ocorrências desta fase, em ordem:** o sétimo contrato com o CI ainda
afirmando seis; o venv da auditoria que mudou de casa e deixou um sítio para
trás; e agora o pacote completo — a fase tornou o pack **pré-requisito de boot**
(`criar()` faz `exige(AURORA_PACK)`, e o compose o monta por volume), atualizou o
CI, e **não atualizou o gravador das provas de container**, que é por P4-10 o
único caminho pelo qual os itens 1 e 4 da DoD da Fase 4 deixam de ser NÃO
VERIFICADO. A falha é determinística: `/pack` vazio, containers mortos na
largada, provas em `rc=125`, em toda rodada futura.

**A varredura, feita agora, e o que ela achou além do gravador.** O universo é
"quem sobe stack ou boota a API", e ele tem **sete** lugares:

| Lugar | Estado |
|---|---|
| `.github/workflows/invariants.yml` | ✅ materializa no passo anterior ao `up` — era o único |
| `scripts/grava_provas_de_container.py` | ❌ **o B1** — corrigido neste commit |
| `README.md` §Quick start | ❌ **achado novo** — é o caminho que uma pessoa nova executa primeiro, e ela subiria `/pack` vazio |
| `scripts/demo_fase4.py`, `mede_cache_frio.py`, `prova_reinicio_de_container.py` | ❌ **três achados** — não sobem a stack, mas o bloco `USO` de cada um manda subir, e a instrução estava incompleta |
| `scripts/sobe_sala.py` | ✅ já importa `materializa` |
| `scripts/demo_fase2.py` | ✅ idem, e o helper declara que essa materialização está em caminho de gate |
| lançador + `docker-compose.audit.yml` | **não se aplica**, e está declarado: a stack efêmera da auditoria tem só Postgres e Redis, sem API e sem `AURORA_PACK` |

**Quatro dos sete estavam errados, e só um era executável.** A distinção importa
para não inflar o achado: o gravador *falha*; os outros três *ensinam a falhar*.
Os dois custam a mesma tarde de quem os segue.

**O que NÃO virou verificador, e por quê.** Um gate que cruzasse "quem chama
`docker compose up`" com "quem materializa o pack" é escrevível, e não o escrevi:
o universo tem sete elementos, três dos quais são prosa de cabeçalho, e o
predicado teria de decidir por texto se um bloco `USO` "conta" como caminho de
execução. Seria a forma que este projeto já recusou uma vez — verificador que
casa prosa e passa a ser desligado. O que fecha esta classe é a varredura no
commit que cria a precondição, e ela agora é regra escrita, ao lado da irmã.

### 3.5 Prova negativa das unidades

Verificador tem `_probes.py`; **computador tem violação plantada na
implementação**, fora da árvore, e o número de testes vermelhos é a medida:

| Unidade | Violações plantadas | Reprovadas | Natureza da prova |
|---|---|---|---|
| `check_insumo_de_metrica` | 6, mais o positivo do consumidor que só anota | 6 | **reexecutável** — `check_insumo_de_metrica_probes.py`, versionado, e executado pelo auditor na décima rodada |
| `metrics/epoch.py` | 2 — união virando soma, `rehearsal` sem descarte | 2 | **ATESTAÇÃO DO AUTOR** |
| `metrics/verificacao.py` | 4 — linhagem, T0 ingênuo, `rehearsal`, desconto | 4 | **ATESTAÇÃO DO AUTOR** |
| `metrics/declaracao.py` | 5 — `TTID` no primeiro, `TTID` sem predicado, última declaração, qualquer inject, reinício de epoch | 5 | **ATESTAÇÃO DO AUTOR** |
| derivação das nove siglas | 5, plantadas **na tabela**, em cópia da spec | 5 | **ATESTAÇÃO DO AUTOR** |

> **AS DEZESSEIS DAS QUATRO ÚLTIMAS LINHAS SÃO ATESTAÇÃO DO AUTOR, E NÃO PROVA
> REEXECUTÁVEL.** A violação foi plantada na implementação, o vermelho foi
> observado, e a árvore foi restaurada — nada ficou versionado que alguém possa
> rodar. Medido pelo auditor na décima rodada (L3): não há
> `test_metrics_*_probes.py`, e `grep -rln "mutation_harness" tests/` devolve
> cinco arquivos, **nenhum** de métrica.
>
> **A marca existe porque a §7.3.1 se aplica ao registro tanto quanto ao código.**
> Uma afirmação de prova negativa que ninguém pode reexecutar tem a forma de
> prova e o peso de declaração — e a auditoria seguinte a lê como prova, que é
> exatamente o que a §7.3.1 nomeia. Sem esta marca, a Fase 7 herdaria dezesseis
> negativos que não existem como artefato.
>
> **Por que é registro e não conserto:** a classe de defeito que o harness
> pegaria está coberta **estruturalmente** por `check_insumo_de_metrica`, que
> rodou com seis negativos e o controle positivo. O que falta é o artefato que
> torna a afirmação reexecutável, e ele é a **P6-13**.

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
| P6-7 | rota nova pode declarar `emite` e não chamar emissor nenhum | **VENCIDA na metade que mordeu** — B2 da sexta auditoria, e o verificador da fábrica |
| P6-8 | justificativa ausente devolve `409`, e `409` é reservado a recusa de estado | **condição** — ver abaixo |
| P6-9 | a cópia instalada do hook do auditor não é sincronizada por ninguém | **condição** — ver abaixo |
| P6-10 | hook declarado sem emissor, e nenhum verificador cruza hooks com emissores | **VENCIDA E RESOLVIDA** — decisão do operador, e o verificador existe |
| P6-11 | payload cru alimenta o Brier: `confidence: 900` produz escore 64,0 | **decisão** — ver abaixo |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção: `sub == persona`, e `actor_id` vira função da persona | **decisão** — do proprietário, depois do merge; ver abaixo |
| P6-13 | dezesseis violações plantadas declaradas na §3.5 são atestação do autor, e não prova reexecutável | **condição** — o artefato que as torne reexecutáveis; ver abaixo |
| P5-2 | a trilha declara a categoria "declarações do exercício" e ela não tem produtor — **herdada**, com esta fase como destinatário | **MIGRADA para a Fase 7**, com gatilho corrigido — ver abaixo |

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

##### VENCIDA NA METADE QUE MORDEU — e a pergunta cara não era a que faltava

**O B2 da sexta auditoria decidiu a pendência mostrando que ela estava mirando o
lugar errado.** Tudo acima discute *"o handler chama o emissor?"* — a pergunta
que exige análise de fluxo. O defeito real foi mais simples e mais grave: a
fábrica de produção da `academus-api` montava **sem emissor nenhum**. Não havia
handler a analisar, porque não havia emissor na aplicação.

`GET /audit/grade-changes` respondia `200` em produção e não gravava nada — o
item 1 da DoD desta fase, falso no único caminho que o container executa.

**A forma da correção é a segunda do mapa acima** — convenção estrutural imposta
por verificador —, e ela ficou mais barata do que o mapa previa, porque a
convenção não recai sobre as rotas: recai sobre **a fábrica**, que é uma por
serviço. `scripts/check_fabrica_liga_emissor.py` pergunta *"a função que o
`uvicorn --factory` chama constrói o produtor que a superfície deste serviço
promete?"*, e isso é um `ast.Call` dentro de um `FunctionDef`.

**A primeira versão do verificador estava errada, e a árvore não.** Ela exigia
`emissor=` de toda fábrica e reprovou o `range-api`, que emite pelo
`InjectEngine` — a convenção de um adapter imposta ao núcleo. O produtor passou a
ser declarado **por serviço**, e a lição fica: verificador que generaliza a
convenção de um caso reprova o que está certo, e é assim que um gate vira ruído
que alguém desliga.

**O `participant-api` entrou como estado declarado**, e não como buraco: ele tem
`montar` e não tem fábrica — não há serviço dele no `docker-compose.yml`. A
entrada com produtor `None` faz a checagem **reprovar no dia em que uma fábrica
nascer ali**, que é exatamente quando a decisão de quem grava precisa acontecer.

**O que continua aberto, dito e não escondido:** a metade original — *"este
handler, executado, emite?"*. O verificador imprime essa fronteira na própria
saída. Hoje quem a cobre é `tests/test_api_emissao_pela_rota.py`, que exercita a
rota real por `TestClient` e afirma sobre o evento no store.

**Vence, agora, em:** a próxima rota que declare `emite` **em um serviço cuja
fábrica já constrói o produtor** — aí a pergunta que sobra é a do fluxo, e ela
volta a ser decisão do proprietário entre as duas formas do mapa acima.

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

##### VENCIDA — a segunda leitura, e o verificador que o agravante exigia

**Decisão do operador: o hook sai.** `vpn_access_revoked` foi removido de
`domains/academus/observability_hooks.yaml`, e volta no commit que trouxer o
`federated-identity-simulator`. T9 volta a ser satisfazível sem exceção, e o
arquivo descreve só o que existe.

**O que a decisão custou, e é pouco:** nada do que este arquivo guardava se
perde. O `event_type` continua no catálogo de `contracts/events.schema.yaml`, com
`effect_class` e `metric_side` — é de lá que a Fase 11 lê o contrato do evento. O
que saiu foi a **afirmação de que a instrumentação existe**, e ela era falsa.

**O argumento da primeira leitura não se aplicava aqui, e essa é a distinção que
faltava na tabela acima.** *"Destinatário declarado é melhor que ausência"* vale
para `check_secoes_de_seguranca.py` porque o objeto lá é uma **seção de
requisito**: ela existe quer haja mecanismo ou não, e declarar quem a trará é a
única alternativa ao silêncio. Um hook não é isso — ele é a **declaração de que
uma ação instrumentada existe**. Declarar um que não existe não é registrar
dívida: é afirmar um fato falso sobre a árvore.

**O agravante era independente da escolha, e virou mecanismo.**
`scripts/check_hooks_com_emissor.py` cruza cada `observability_hooks.yaml` com as
emissões reais de `domains/`, por AST, em quatro direções:

| Direção | O que fecha |
|---|---|
| declarado × emitido | o critério de T9, literal — foi ela que reprovou a árvore antes da remoção |
| emitido × declarado | o arquivo descreve o que o adapter faz, e não uma lista de desejos |
| `producer` | o hook nomeia quem grava, e não outro serviço |
| `payload_fields` | as chaves do payload literal, para todo hook — antes existia só para `audit_query_performed`, num teste à mão |

**A forma escolhida foi a primeira do mapa acima — cruzar por AST — e não a
segunda.** O mapa dizia que ela *"esbarra na mesma dificuldade da P6-7: achar
quem chama o emissor é análise de fluxo"*. Medido ao escrever: a dificuldade é
real para **quem chama**, e não para **quem constrói**. `EventDraft(event_type=
<CONSTANTE>)` é decidível por varredura, e é o que separa *"hook sem emissor em
lugar nenhum"* — o defeito do B1 — de *"emissor que nenhuma rota alcança"*, que
continua sendo a P6-7 e está impresso na saída do próprio verificador.

**O limite declarado, então:** um `Emissor` com método que ninguém chama passa
aqui. A checagem vê a construção do evento, não o fluxo que a alcança.

**O que a prova negativa cobre:** as quatro direções, mais a **vacuidade** —
`domains/` sem `observability_hooks.yaml` nenhum tem de **reprovar**, porque
"nada a conferir" virando "ok" é o modo de falha desta checagem, e é o erro que
os dois predicados de base aposentados cometeram. Sete defeitos plantados, sete
reprovados, com o adapter coerente e a árvore real passando.

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

#### P6-12 — a condição (4) da contrassinatura não pode disparar em produção

**M1 da décima auditoria, e o mérito é meu, não do achado.** A decisão está
escrita na §1 desta fase: *"`actor_id` identifica **credencial, não humano**. A
condição (4) — `actor_id` distintos — pega **reuso de credencial**, e não
dualidade humana"*. O limite ficou declarado em
`range-core/participant/api/tokens.py:34-38` em vez de parecer garantia, e a
frase que fecha o parágrafo dizia que credencial pessoal futura daria dentes à
condição (4) **sem tocar a spec**.

**A medição mostra que a condição não pega nem o que eu escrevi que ela pegaria.**
`range-core/participant/api/app.py:101` emite `tokens.issue(persona, persona,
...)` — `sub` recebe o próprio valor de `persona` —, e `_declara` propaga
`actor_id = claims.sub`. Com isso `actor_id` é **função de `persona`**: satisfeita
a condição (2), que exige personas distintas, a (4) passa a ser satisfeita por
construção. A comparação `antecedente.actor_id == actor_id`
(`range-core/declarations/contrassinatura.py:106`) não tem como disparar em
produção — nem para dualidade humana, nem para reuso de credencial, que era a
metade que eu afirmei estar coberta. `tests/test_participant_emissao_pela_rota.py:134`
afirma `evento.actor_id == persona`, e é a confirmação por execução.

**O que fica errado não é o mecanismo — é o que a norma promete.** `03` §3.4
escreve a condição (4) com a justificativa *"um mesmo operador com duas
credenciais satisfaria as personas e assinaria sozinho"*. **A spec é o que alguém
lê**, e ela promete uma barreira que o sistema não tem. O limite declarado no
docstring de `tokens.py` e neste registro não alcança quem lê a norma.

**As duas saídas:**

| Saída | O que ela faz | O que custa |
|---|---|---|
| **(a) a norma passa a dizer o que o mecanismo faz** | `03` §3.4 declara que a (4) é condição **estrutural** — ela existe escrita na forma certa e ganha dentes quando houver identidade de credencial —, e a justificativa deixa de prometer a barreira | `spec-change`, em PR próprio e antes de qualquer código. E aceita, por escrito, que hoje a autocontrassinatura por posse dupla não é barrada |
| **(b) `sub` passa a ser identidade de credencial** | a (4) volta a morder no caso que ela nomeia: emissão com `sub` derivado da credencial usada, e não da persona pedida | mexe na emissão de token da superfície de participante e nas sete credenciais de ambiente. É código, e o candidato auditado é `c3051dc` |

**Vence em:** a sua palavra, **depois do merge**. Nenhum item da DoD da Fase 6
cobra credencial por humano, e nem `01` §6 nem `05` §8 a exigem — por isso é
pendência e não conserto. É pauta da Fase 7.

#### P6-13 — dezesseis violações plantadas que ninguém pode reexecutar

**L3 da décima auditoria.** A tabela da §3.5 declara violações plantadas em
`metrics/epoch.py` (2), `metrics/verificacao.py` (4), `metrics/declaracao.py` (5)
e na derivação das nove siglas (5) — **dezesseis** —, todas "fora da árvore": a
violação foi plantada, o vermelho foi observado, a árvore foi restaurada. Não há
`test_metrics_*_probes.py`, e `mutation_harness` não aparece em arquivo de
métrica nenhum.

**A marca já está na §3.5, e ela é o conserto desta pendência no que ele tem de
imediato:** as quatro linhas passam a dizer **ATESTAÇÃO DO AUTOR**, e a primeira
linha da mesma tabela — `check_insumo_de_metrica`, com `_probes.py` versionado e
executado pelo auditor — passa a dizer **reexecutável**. A distinção existir na
própria tabela é o que impede a leitura errada.

**Por que marcar importa mais do que parece.** Afirmação de prova negativa que
ninguém pode reexecutar tem a **forma** de prova e o **peso** de declaração. É a
§7.3.1 aplicada ao registro da fase, e não ao código: a auditoria seguinte lê o
registro como fonte, e dezesseis negativos declarados sem artefato entram como
cobertura que não existe. O auditor da décima rodada disse a frase exata —
*"a afirmação é atestação: eu não consigo reexecutá-la"* — e a listou entre o que
**não conseguiu verificar**.

**Por que é registro e não conserto:** a classe de defeito que o harness pegaria
está coberta estruturalmente por `check_insumo_de_metrica` — seis negativos e o
controle positivo, executados —, e nenhum item da DoD depende dos dezesseis. `06`
T10 exige teste negativo próprio de **verificador**, e os verificadores têm.

**Vence em:** o artefato que torne a afirmação reexecutável — um
`test_metrics_*_probes.py` na forma dos que já existem, ou o `mutation_harness`
alcançando os computadores de métrica —, **ou** a primeira vez que alguém precise
da cobertura que a tabela declara. Enquanto não vier, a marca é o que mantém a
declaração honesta.

#### P5-2 — a categoria de trilha sem produtor, e o gatilho que disparou apontando para o lugar errado

**Herdada da Fase 5, com esta fase como destinatário nomeado.** `02` §4.1 lista
cinco categorias que a trilha de auditoria registra, e a quinta é *"declarações
do exercício — todas as ações de `declare_*`"* (`03` §3.1). As quatro primeiras
ganharam objeto na Fase 5; a quinta ficou declarada com destinatário, e o
gatilho escrito lá foi **o commit em que a primeira ação `declare_*` nascer**.

**O gatilho disparou nesta fase, e a suposição embaixo dele estava errada.** As
nove ações nasceram na peça 3, bloco B. `DECLARACAO_DE_EXERCICIO`
(`domains/academus/audit/trilha.py`) continua sem quem a escreva — e não por
esquecimento: o gatilho assumia que a declaração passaria pela **trilha do
adapter**, e a peça 3 decidiu o contrário. Declaração é ato de **participante**,
mora no núcleo com RBAC por persona (`01` §6), e a trilha `audit_trail` é
mecanismo de **domínio**, sobre as entidades do Academus. As nove declaram no
event store, que é outro caminho — e a decisão que as pôs lá é a mesma que a §1
registra com três razões e um verificador que a impõe.

**Por que não fecha, e por que não fica.** Fechar apagaria pergunta legítima: a
categoria continua declarada em `02` §4.1, continua sem produtor, e uma
constante que nada escreve é exatamente *"o `event_type` que nunca dispara"* que
`09` §4 chama de a falha mais cara possível. Mas manter o gatilho original é
pior que não ter gatilho nenhum: ele **já disparou**, e um gatilho disparado que
não vence é um alarme que a próxima leitura aprende a ignorar.

**MIGRADA para a Fase 7, com gatilho novo:** *a primeira ação de participante que
altere estado de domínio* — porque é aí que a trilha do adapter passa a ter o que
registrar, e é a Fase 7 quem traz o pack completo que produz essas ações. O
gatilho antigo perguntava *"a ação nasceu?"*; o novo pergunta *"a ação toca a
coisa que a trilha vigia?"*, que é a condição que faltava.

Registrada no destino em `docs/progress/fase_7.md`. O comentário de
`trilha.py` — que dizia *"nada a escreve até a Fase 6"* — foi corrigido no mesmo
commit: era §1.6 inscrito no código, e apontava para uma fase que fechou sem
escrevê-la.

---

## 7. A sétima auditoria — o M1 primeiro, e o mapa do B1

### 7.1 M1 — a conformidade de envelope cobre os três produtores

**A classe veio antes do conserto, e é essa ordem que é o achado.** O M1 registrou
escopo, e não defeito: `ConformeAoContrato` provava o que dizia, e a docstring
dela reivindicava ser *"a única camada que impede o engine de emitir um envelope
que o contrato recusa"* — verdadeira sobre o engine, e o commit da fase
acrescentou **dois produtores** sem estendê-la.

Medido no commit auditado: `grep -rn "iter_errors" tests/*.py` devolvia três
linhas, todas em `tests/test_inject_engine.py`.

**O mecanismo é um só**, em `tests/conformidade_de_envelope.py`: `envelope()`
monta o documento e `ValidacaoDeEnvelope` afirma sobre ele. Copiar a classe três
vezes seria a D4 com outro nome, e pior no caso concreto — o produtor **novo** é
justamente o que nasceria com a cópia velha, e o defeito que ela não vê é o
defeito que ele tem.

Os três herdeiros, todos com a classe chamada `ConformeAoContrato`:

| Produtor | Arquivo | Resultado |
|---|---|---|
| `inject-engine` | `tests/test_inject_engine.py` | verde, 7 `event_type` |
| `academus-api` | `tests/test_api_emissao_pela_rota.py` | **VERMELHO** — o B1 |
| `participant-api` | `tests/test_participant_emissao_pela_rota.py` | verde, as nove |

**O vermelho, medido, e a mensagem é a do contrato:**

```
FAIL: test_o_envelope_emitido_pela_rota_valida_contra_o_contrato
      (ConformeAoContrato) (event_type='audit_query_performed')
AssertionError: [<ValidationError: "'persona' is a required property">] != []
  : audit_query_performed (academus-api): 'persona' is a required property
```

Suíte inteira: **714 testes, 1 falha, 140 skips** (os `skipIf` de Postgres — os
serviços não estavam no ar nesta execução). A falha é uma, e é o B1.

**A classe teria pego o B1 na primeira rodada**, e o argumento não é retórico: o
teste que hoje cita `09` §1.1 na docstring
(`test_o_envelope_do_evento_e_o_declarado`) afirma sobre `event_type`,
`truth_layer` e `producer` — e **nenhum dos três é o que a §1.1 acrescenta**.
Verificar campo a campo à mão sempre verifica os campos de que alguém se lembrou;
o contrato não esquece, porque a regra está escrita nele.

**O mecanismo tem prova negativa própria** — `tests/test_conformidade_de_envelope.py`,
três recusas e dois controles positivos. Uma camada de conformidade falha em
silêncio da pior forma possível: não fica vermelha quando quebra, fica verde
validando nada. Os eixos são envelope inválido, **lista vazia** (a rota que
respondia sem gravar deixaria a validação passar por vacuidade — foi o B2 da
sexta rodada) e **`event_type` esperado e ausente** (conforme por emitir menos
não é conforme).

### 7.2 O B1 tem um conflito de spec embaixo, e ele não é meu para resolver

**O que a auditoria achou é verdadeiro, e é menor do que o que está embaixo.** O
adapter não tem de onde tirar `persona` — mas a razão não é esquecimento de
superfície. É que **dois documentos não-master dizem coisas incompatíveis**, e
`CLAUDE.md` manda parar e perguntar em vez de resolver por inferência.

**O lado que diz que o adapter emite `persona`:**

- `09_EVENT_MODEL.md` §1 — o exemplo normativo do envelope universal **é este
  evento**: `"event_type": "audit_query_performed"`, `"producer":
  "academus-api"`, `"persona": "ti"`;
- `09` §1.1 — *"`actor_id` e `persona` são obrigatórios quando `truth_layer` for
  `participant_action`"*;
- `09` §4.1 — `audit_query_performed` é `participant_action`;
- `03_EXERCISE_DESIGN.md` §3.4 — *"a consulta de auditoria que emite
  `audit_query_performed` é **rota da `academus-api`**"*;
- `contracts/events.schema.yaml` — o exemplo **positivo** (`:835`) e quatro
  negativos (`:967`, `:982`, `:1002`, `:1019`) carregam todos
  `producer: academus-api` **e** `persona: ti`. São validados por
  `check_contract_examples.py`, que passa: **o contrato já afirma o que o código
  não faz.**

**O lado que diz que ele não pode:**

- `01_ARCHITECTURE.md` §6 — *"A persona **vê pelo domínio** e declara pelo
  núcleo. (...) A separação não é organizacional: **`domains/` não pode conhecer
  persona**, e o verificador de superfície já a recusa como vocabulário de token
  no perfil de domínio. Uma rota de declaração no adapter exigiria desfazer essa
  guarda."*
- `scripts/check_api_surface.py:142` executa a frase:
  `VOCABULARIO_DE_EXERCICIO = PAPEIS_DE_EXERCICIO | {"persona"}`, aplicado ao
  `PERFIL_DOMINIO` como `vocabulario_proibido_em_claim`.

**A dobradiça, e ela é uma frase.** A proibição de `01` §6 é enunciada sem
qualificação — *"`domains/` não pode conhecer persona"* —, mas o **exemplo** que
a acompanha é *"uma rota de **declaração** no adapter"*. A consulta de auditoria
não é declaração: `03` §3.4 a classifica como **ato de observação**, família
distinta na mesma seção. Ler a frase pelo enunciado proíbe; lê-la pelo exemplo
não alcança este caso. **Não decido qual leitura vale.**

### 7.3 As três saídas, com o custo medido de cada uma

#### (a) A `academus-api` recebe `persona` no token

| | |
|---|---|
| **Norma** | **Desfaz a guarda que `01` §6 nomeia** — literalmente a frase *"exigiria desfazer essa guarda"*. Não toca `09`, não toca `03`, não toca o contrato: é a única das três em que o exemplo positivo do contrato **já descreve o resultado** |
| **Superfície** | `domains/academus/api_surface.yaml` `token.claims: [sub, role, exp]` ganha `persona`; `range-core/api/tokens.py::_payload` ganha a chave (conferido por AST nas duas direções); `check_api_surface.py:142` perde `persona` do vocabulário proibido do perfil de domínio |
| **Código** | `auth.py::emitir_token` e `autoriza`, `Escopo`, `emissor.py` — um argumento a mais em cada |
| **O custo que não está no diff** | **a fonte do valor não existe.** `POST /auth/token` é `planejada`; `emitir_token` **não tem chamador de produção** — medido: só a suíte e `scripts/demo_fase4.py:139`, que assina o token ele mesmo *"porque `/auth/token` não existe"*. E não há binding persona ↔ conta do Academus em lugar nenhum: `grep -rl persona domains/ alembic/` devolve o `api_surface.yaml`, `models/registros.py` e comentários de migration — nenhum deles é a tabela |

#### (b) `audit_query_performed` deixa de ser `participant_action`

| | |
|---|---|
| **Norma** | spec-change em **três** documentos: `09` §4.1 (a linha do catálogo), `09` §1 (o exemplo normativo do envelope **é este evento**), `09` §2 (`participant_action` é *"o que a equipe fez, **viu** ou declarou"* — consulta é o *viu*, e mudar a camada exige dizer por que ver deixou de ser ação de participante) |
| **Contagem fechada** | `03` §3.4 fecha a conta — *"`participant_action` tem dezessete `event_type`. Nove estão nesta tabela (...) Nove mais três mais dois mais três fecham os dezessete"* — e `01` §4.4 repete o dezessete. Tirar um quebra a conta de um registro que tem **parágrafo dedicado** a não haver terceira ocorrência de perda silenciosa |
| **Contrato** | `event_type_participant_action` (`:389`), `metric_side` (`:740`), `effect_class` (`:759`) e **os cinco exemplos**, todos `truth_layer: participant_action`; mais `objectives.schema.yaml:255` e `:351` |
| **Para onde** | `observable_evidence` é *"o que o ambiente permite descobrir"*. A consulta feita pela equipe virando *"o que o ambiente revela"* apaga a distinção entre **ter procurado** e **a evidência ter sido liberada** — a mesma que `test_consulta_vazia_EMITE_com_result_count_zero` protege (*"não olhou"* × *"olhou e não havia"*) e que `03` §1.2 usa para separar `auto` de `observed` |

#### (c) A consulta migra para a `participant-api`

| | |
|---|---|
| **Norma** | o **maior**: contradiz `03` §3.4 literalmente (*"é rota da `academus-api`"*), `09` §1 e `09` §6 pelo `producer` dos exemplos, e a metade *"a persona **vê pelo domínio**"* de `01` §6 — a consulta é o ver |
| **Mecânica** | a rota lê a trilha do Academus (`repositorio.alteracoes_de_nota`, Postgres do domínio). Movê-la faz `range-core/` consultar banco de domínio: não é o invariante 1, que é sobre import, mas é a mesma fronteira por outra porta |
| **Efeito colateral medido** | `domains/academus/observability_hooks.yaml` fica **sem hook nenhum**, e `check_hooks_com_emissor.py` passa a rodar com `total_hooks = 0` — verde por vacuidade. A guarda de vacuidade dele é sobre o **arquivo** existir, não sobre haver hook |
| **Dependência** | **arrasta o H2 junto**: a `participant-api` não tem onde declarar hook, porque `09` §6 escopa o arquivo em `domains/<adapter>/` |

#### (d) Uma quarta forma apareceu na medição — e ela é minha, não uma das três

O adapter **não** aprende persona: entrega `sub`, e quem carimba é o núcleo — um
resolvedor, ou o próprio `append`, que já carimba `event_id` e as três marcas
por D1. Preserva `01` §6 ao pé da letra e satisfaz `09` §1.1 sem tocar spec
nenhuma.

**O custo real é o mesmo buraco de (a)**: o binding persona ↔ conta de domínio
não existe. Além disso põe identidade dentro do store — que passa a precisar de
uma fonte de identidade — e faz `persona` deixar de ser **declarada pelo
produtor**, o que muda o sentido de `09` §1.1 sem mudar o texto dela. Registrada
para não sumir; não é recomendação.

**O que é comum às quatro, e é o achado real:** nenhuma delas é barata porque
todas esbarram no mesmo artefato ausente — **não existe, em lugar nenhum da
árvore, a ligação entre uma persona de exercício e uma conta do domínio.** A
pergunta que decide o B1 não é *"qual campo"*; é **de quem é essa ligação, e onde
ela mora**.

### 7.4 H2 — a cegueira do verificador de hooks, e onde ela toca o B1

`check_hooks_com_emissor.py` varre `domains/*/observability_hooks.yaml` e o `.py`
do adapter irmão. A `participant-api` é núcleo — `09` §6 escopa o arquivo em
`domains/<adapter>/` —, então as **nove rotas de declaração** de `03` §3.4 são
estruturalmente invisíveis a T9. Cobertura hoje: **um `event_type` em trinta e
três**. E `separate_incident_declared`, que `09` §6 e `03` §1.1 usam como
evidência `auto` do OBJ-03 no exemplo normativo, não está declarado em hook
nenhum — verificado: `grep -rn separate_incident_declared domains/` não devolve
nada.

| Saída | Custo |
|---|---|
| **α — hook por PRODUTOR, e não por diretório de adapter** | spec-change de uma frase em `09` §6, mais uma segunda raiz no verificador — **declarada**, como o `SERVICOS` de `check_fabrica_liga_emissor.py`, e não descoberta por varredura. Leva T9 de 1/33 para 10/33 e dá endereço ao `separate_incident_declared` que a Fase 7 vai precisar |
| **β — as nove não são evidência `auto`** | contradiz `03` §1.2 (*"`auto` — emitida pela aplicação instrumentada (...) **Declarada em `observability_hooks.yaml`**"*) e o exemplo normativo de `09` §6. O OBJ-03 do pack da Fase 7 perde a evidência |
| **γ — mover as nove para um adapter** | contradiz `01` §6 frontalmente: *"elas vivem no core, com RBAC por persona, e não na `academus-api`"* |

**A intuição de que a mesma decisão resolve as duas está meio certa, e a metade
que falta importa.** O H2 precisa de **α em todos os mundos** — as nove
declarações existem e são `auto` independentemente do que se decida sobre a
consulta de auditoria. O acoplamento é de mão única: **(c) depende de α**, porque
o hook da consulta precisaria de onde morar; (a), (b) e (d) resolvem o B1 sem
tocar o H2, e o H2 continua aberto do mesmo jeito.

**Vence em:** a sua palavra. O M1 está no lugar e mede; o conserto do B1 não
começa antes disso.

### 7.5 A decisão, o `spec-change` e o conserto

**Decidido pelo proprietário: (a).** O conflito de §7.2 foi arbitrado pela fonte,
e não havia contradição real — o parágrafo de `01` §6 é inteiro sobre
**declaração**, e a proibição é qualificada pelo contexto. Consulta de auditoria
é **ato de observação**, família que `03` §3.4 separa e que não declara nada.

O `spec-change` #52 escreveu a qualificação que só existia no contexto, em dois
sítios — `01` §6 e `09` §6, este último com o α do H2 — e foi mergeado antes de
qualquer código, em PR próprio. A branch foi rebaseada sobre ele e a âncora
regravada no mesmo commit.

#### A forma do conserto, e a decisão que ela obrigou

A decisão era *"persona no token do adapter"*, e ela tem uma bifurcação dentro:
**qual `_payload`**. Medido: `range-core/api/tokens.py::_payload` serve **dois**
chamadores — este adapter e o **gm-console** (`range-core/api/app.py:259`).
Acrescentar `persona` ali poria a claim no token de **facilitação**, que é
exatamente o risco que o docstring daquela função guarda.

**O adapter ganhou emissor próprio** — `domains/academus/api/tokens.py` —, que é
o mesmo movimento que `range-core/participant/api/tokens.py` fez na peça 3, pelo
mesmo motivo: *uma função única assinando duas vocações*. Compartilha-se a
decisão criptográfica (`ALGORITMO`, `TokenInvalid`); não se compartilha o
`_payload`, que é quem carrega a vocação.

**`persona` ao lado de `role`, e não no lugar dele** — a diferença para a
superfície de participante, e ela é do desenho. Lá a persona **é** a autorização.
Aqui os dois coexistem porque respondem a perguntas distintas, e `01` §6 fixa a
assimetria: **papel de domínio autoriza a rota, persona identifica quem agiu.**

#### A guarda mudou de eixo, e é isso que a impede de ser afrouxamento

| | antes | agora |
|---|---|---|
| `persona` como **claim** | proibida (`VOCABULARIO_DE_EXERCICIO`) | **permitida** — é o que `09` §1 exibe como normativo |
| `persona` como **papel de rota** | não conferida | **proibida** (`PAPEIS_PROIBIDOS_NO_DOMINIO`) |

Sem a segunda metade a mudança seria afrouxamento puro: `papeis_de_dominio`
aceitaria `ti`, `emitir_token` assinaria papel de persona, e uma rota do adapter
passaria a autorizar por desenho de exercício. O caso
`test_a_PERSONA_nao_vira_papel_pela_porta_do_argumento` é o que prova que a
guarda mudou de lugar em vez de sumir.

#### Três camadas, e nenhuma sozinha basta

1. `tokens.verify` **exige** `persona` — token sem ela é token de outra
   superfície, e o `require` a recusa;
2. `Emissor.registrar_consulta` **levanta** `SemPersona` em vez de gravar. Falhar
   é caro e visível; gravar sem persona é barato e invisível — nada falha, o
   store não valida, e o defeito aparece no consumidor de outra fase com o
   exercício já gravado. É a assimetria que `09` §4 chama de a falha mais cara;
3. `ConformeAoContrato` mede o envelope contra o contrato — **o M1**, que é quem
   pegou o defeito.

`Escopo.persona` é opcional **no tipo** e obrigatória **no caminho real**: o
default existe para o duplo que só exercita escopo de objeto, e a camada (2) é o
que impede o `None` de virar envelope.

#### As medições

| | antes | depois |
|---|---|---|
| `ConformeAoContrato` no adapter | `'persona' is a required property` | verde |
| suíte | 714 testes, **1 falha** | **716 testes, OK** |
| claims assinadas na superfície de domínio | 3 | 4 |
| `check_hooks_com_emissor` | 1 hook, 1 produtor | **10 hooks, 2 produtores, 10 emissões** |
| cobertura de T9 | 1/33 | **10/33** |
| prova negativa dos hooks | 7 plantados | **11 plantados**, nas duas formas de produtor |

#### O H2, e o que a segunda raiz obrigou a descobrir

`09` §6 passou a declarar a instrumentação **por produtor**, e
`range-core/participant/observability_hooks.yaml` nasceu com as nove.

**O verificador não podia simplesmente ganhar um `glob` a mais.** O emissor da
`participant-api` constrói `EventDraft(event_type=event_type)` — uma **variável**,
porque uma função serve as nove rotas e quem escolhe o tipo é o handler.
Procurar `EventDraft` ali acharia **zero** e reprovaria as nove estando elas
corretas: exatamente o defeito que `check_fabrica_liga_emissor.py` cometeu na
primeira versão e registrou.

A tabela `PRODUTORES` declara, por produtor, **qual chamada carrega o tipo** —
`EventDraft` no adapter, `_declara` no núcleo — e o tipo passou a ser procurado
também entre os **posicionais**, com exigência de unicidade. `_produtor_da_raiz`
alcança o `PRODUTOR` do módulo irmão, sem o qual a direção (c) ficaria muda no
núcleo. E a **vacuidade passou a ser conferida por raiz**: no total, uma raiz
declarada sem arquivo seria coberta pela outra, e a instrumentação de um serviço
inteiro sumiria sem nada acusar.

**Os hooks das nove não declaram `payload_fields`, e o motivo está escrito no
arquivo** — não é esquecimento. Nenhum contrato o exige; o que ele compra é
cruzamento com a **assinatura** do emissor, que é prova fraca ao lado da prova de
emissão que `tests/test_participant_emissao_pela_rota.py` já dá pela rota real; o
corpo das nove é dinâmico por desenho (`03` §3.4 exige justificativa livre mais
campos por ação), e enumerá-lo seria lista que envelhece a cada ação nova; e
trocar o emissor por nove dicionários literais para o gate enxergar seria moldar
o código à checagem — a classe D4 com outro nome.

`tools/check_contract_literals.py` ganhou a mesma segunda raiz, e ela é
**necessária por outro eixo**: lá se pergunta se o tipo está no **catálogo**, e um
`event_type` com erro de digitação no arquivo novo nunca dispararia. Verificado
plantando `containment_declaredd` — rc=1, com a mensagem do invariante 3 — e
restaurando.

#### Dois probes que a mudança obrigou a mexer, e um defeito achado no caminho

`check_api_surface_probes.py` plantava `persona` no token de domínio e exigia
recusa — **o probe codificava a leitura isolada de `01` §6** que o `spec-change`
corrigiu. O caso passou a plantar papel de **facilitação**, que continua proibido
nas duas superfícies, e a guarda que `persona` deixou vazia ganhou probe próprio:
`probe_da_persona_como_papel_de_dominio`. Sem esse par, a peça seria afrouxamento
com aparência de precisão.

**E `check_readme_atual_probes.py` estava quebrado antes desta peça.** A âncora
era o literal `**684 testes**`, e a rodada que levou o README a 707 não a
acompanhou: o probe morria no próprio `_com` com *"o probe não ancorou"*. O modo
de falha era o **certo** — ele grita em vez de passar calado —, e o CI o executa
(`invariants.yml:694`), mas nenhuma auditoria o listou.

O conserto tira o número de lá: a âncora passa a ser **derivada** do README por
expressão. O que o caso planta é a troca por um número errado, e o número certo é
o que estiver escrito. Se a **forma** da afirmação mudar — e não o número —, o
`AssertionError` volta, e aí ele significa o que sempre quis significar.

#### O que esta peça NÃO fechou, dito

- **H1 (P6-11)** e **L1** seguem registrados e não foram tocados: eram decisão
  registrada de não tocar nesta unidade.
- **A metade aberta da P6-7** — *"este handler, executado, emite?"* — continua
  aberta, e o verificador imprime a fronteira na própria saída.
- **As duas provas pesadas** — containers e seed — estão amarradas ao SHA do
  candidato e são regravadas **pelo lançador**, contra o worktree da auditoria.
  Enquanto o candidato não existe elas reprovam por divergência de SHA, que é o
  comportamento certo e não um defeito da árvore (`docs/process/WORKFLOW.md`,
  P4-10 e a medição do seed).

### 7.6 B1 da oitava auditoria — o chamador de produção ficou para trás

**FAIL justificado, e confirmado na fonte.** A peça anterior pôs `persona` no
token de domínio, atualizou os testes daquela superfície e **não atualizou
`scripts/demo_fase4.py`**, que continuava assinando com
`range_core.api.tokens.issue` — `{sub, role, exp}` — e mandando o token para a
`academus-api`, cujo `EXIGIDAS` passara a pedir quatro claims. Resultado: 401 na
**primeira** matrícula do DEMO, com a stack inteiramente correta. Os 716 testes
ficaram verdes exercitando o caminho novo; o único artefato que exercita a
montagem real ficou no antigo.

#### A varredura, antes de qualquer linha

O laudo nomeava um consumidor. O universo é *"quem produz uma credencial, e para
qual superfície ela vai"*, e ele tem **oito** lugares:

| Lugar | O que faz | Estado |
|---|---|---|
| `range-core/api/app.py:259` | assina com o emissor do núcleo, para a superfície do **console** | ✅ é o par certo — e é o **único** chamador legítimo daquele `issue` |
| `range-core/participant/api/app.py:101` | assina com o emissor de **participante**, para a superfície de participante | ✅ |
| `domains/academus/api/auth.py:130` | assina com o emissor do **adapter**, para a `academus-api` | ✅ |
| `scripts/demo_fase4.py:139,170` | assinava com o emissor do **núcleo** e mandava para a `academus-api` | ❌ **o B1 — corrigido aqui** |
| `scripts/sobe_sala.py:53` | importa `jwt_secret`, **não assina nada**, e sobe só o `range-api` | ✅ **não é a mesma classe** |
| `scripts/prova_reinicio_de_container.py:94` | manda `Bearer`, mas o token vem de `POST /session` do `range-api` — a rota, não o emissor | ✅ |
| `range-core/web/gm-console/main.tsx:53,65` | idem: token do console, obtido pela rota | ✅ |
| `domains/academus/api/processo.py:62`, `range-core/api/processo.py:61` | leem `jwt_secret` no boot e o entregam pronto | ✅ não emitem |

**`sobe_sala.py` não tem o defeito, e a distinção é o trabalho.** Ele importa do
mesmo módulo, e é por isso que ele aparece na varredura — mas o que ele importa é
o **segredo**, não o emissor, e o que ele monta é o `range-api`, que verifica com
o `verify` do núcleo. Consumidor do módulo e assinante para a superfície de
domínio são conjuntos diferentes, e `grep` por módulo devolve a união dos dois.

**O achado que a varredura acrescenta é negativo, e vale registrá-lo:** fora de
`range-core/api/app.py`, **nenhum lugar do produto precisa de
`range_core.api.tokens.issue`**. Quem quer token de console pede à rota que
existe para emiti-lo. Isso não é acaso — é a propriedade que o degrau 2 do mapa
abaixo transforma em verificador.

#### O conserto

`demo_fase4.py` passa a usar `autenticacao_do_ambiente().emitir_token(sub, papel,
PERSONA)` — o caminho que a produção usa e que os testes desta superfície já
usavam. Não é só trocar de emissor: `emitir_token` é o único lugar do produto que
julga `role` contra `papeis_de_dominio`, então o script deixa de poder assinar um
papel que a superfície não declara. `EXIGIDAS` **não** foi relaxada, e não há
default para `persona`: é a decisão do `spec-change` #52, e afrouxá-la para
acomodar um chamador seria inverter a regra de que o código é que está errado.

**A persona é `ti`, e a escolha tem razão.** `aluno` é papel de domínio e não está
no vocabulário das sete de `03` §6; entre as duas do `pack_minimo`
(`personas: [ti, reitoria]`) a escolha é a mesma que `09` §1 usa no envelope
normativo com `producer: academus-api`, e a mesma que os testes escolheram.

### 7.7 A quarta ocorrência da classe, e o mapa para transformá-la em mecanismo

**As quatro, nesta fase:** o sétimo contrato com o CI ainda afirmando seis; o venv
da auditoria ausente da branch; a precondição de boot do pack sem varrer o
gravador; e agora o contrato do token sem varrer o chamador de produção.

**Duas regras já estão escritas** (§3.4 e a irmã), pela mesma mão, duas seções
acima — e a classe reincidiu assim mesmo. **O modo de falha não é ignorar a
regra: é não reconhecer que *esta* mudança é uma instância dela.** A regra cobra
uma varredura *depois* de uma classificação, e é a classificação que falha. Um
mecanismo não pede classificação nenhuma: ele dispara sobre o artefato.

#### Por que hoje só a prova de container pega

Estaticamente, `demo_fase4.py` importar `range_core.api.tokens` é **legal** —
`range-core/api/app.py` faz o mesmo e precisa fazer. A ilegalidade só existe
**em relação ao destino da requisição**, e o destino é `ACADEMUS`: uma constante
de módulo com default de ambiente, isto é, uma **string resolvida em runtime**.

Nenhum grafo de import, nenhuma igualdade AST × YAML e nenhum catálogo liga
*"assinou com o emissor A"* a *"mandou para a superfície B"*, porque essa ligação
é **dado, e não estrutura** — e todo verificador desta árvore trabalha sobre
estrutura. O único instrumento que observa o caminho do dado é o que o executa.

Vale a comparação com o M1 da mesma peça, que **pegou** o defeito irmão no
envelope: `ConformeAoContrato` mede o **objeto produzido**, e por isso não
precisa saber quantos chamadores existem. O token também tem objeto — mas o
objeto só existe em runtime e a validade dele depende do destino. Por isso a
verificação acontece dentro do sistema em execução, e chega como 401.

#### Os três degraus, com o que cada um cobra e o que cada um deixa passar

**Degrau 1 — desduplicar o fato.** Onde a exigência puder ser *derivada* em vez de
*afirmada*, a classe deixa de existir. É o que funcionou uma vez nesta fase: o
CI parou de dizer `== 6` e passou a derivar de `contracts_dir()`. Custo quase
zero; cobertura total **para os fatos que aceitam derivação**. O fato do token
não aceita: qual emissor serve qual superfície é decisão, não contagem.

**Degrau 1.5 — a regra ancorada no artefato, e não na memória.** Um hook que
dispare quando o commit toca `EXIGIDAS`, `_payload` ou `token.claims` de um
`api_surface.yaml`, e **imprima a lista de chamadores daquele emissor**. Não
bloqueia — não tem como saber se a varredura aconteceu —, mas troca *"lembrar da
regra"* por *"a lista está na tela"*. Custo baixo. Cobertura humana, e é honesto
dizer que é isso.

**Degrau 2 — allowlist de chamadores por emissor.** Este teria pego o B1,
estaticamente, com a mesma forma do `check_core_boundary.py`. O conjunto de
emissores é **três e fechado**, e o de chamadores legítimos de cada um é pequeno
e fechado:

| Emissor | Quem pode chamá-lo |
|---|---|
| `range-core/api/tokens.py::issue` | `range-core/api/app.py` (a rota que troca credencial por token) e os testes dele |
| `range-core/participant/api/tokens.py::issue` | `range-core/participant/api/app.py` e os testes daquela superfície |
| `domains/academus/api/tokens.py::issue` | `domains/academus/api/auth.py::emitir_token` e os testes; quem fala com a `academus-api` chega por `emitir_token` |

A checagem é AST pura: achar as chamadas, resolver o módulo importado, exigir que
o arquivo esteja na lista daquele emissor. **Sem casar prosa, sem overmatch** — é
a objeção que desligou o verificador de precondição de boot na §3.4, e ela não se
aplica aqui. E metade da tabela **já existe**: `check_api_surface.py::PERFIS`
carrega `MODULO_DO_TOKEN` por superfície; o que falta é a terceira coluna.

**O limite dele, dito:** a allowlist é por arquivo, e vai cega no dia em que um
arquivo precisar falar com **duas** superfícies — ele estaria na lista dos dois
emissores e escolher o errado voltaria a passar. O que fecha esse buraco é o
achado negativo da §7.6: **nenhum cliente precisa do `issue` do núcleo**, porque
o token de console sai da rota. Com a lista do núcleo tendo exatamente um
elemento, o caso de dois emissores no mesmo arquivo deixa de ser exprimível — e é
essa propriedade, não a lista, que faz o degrau 2 valer.

**Degrau 3 — execução.** O que sobra. E sobra por natureza, não por preguiça:

| Contrato | Objeto medível fora de execução? | Mecanismo possível | Hoje |
|---|---|---|---|
| **envelope** | sim — o documento emitido | `ConformeAoContrato` sobre o produzido | ✅ existe, é o M1, e foi ele que pegou o defeito irmão |
| **token** | o objeto é de runtime, e a validade depende do **destino** | degrau 2: trocar o dado por estrutura, proibindo o import | ❌ não existe; quem pegou foi a prova de container |
| **boot** | **não** — é procedimento, não objeto | nenhum sem casar prosa (§3.4 mediu: sete sítios, três deles bloco `USO`) | ❌ e declarado assim desde a §3.4 |

**A resposta honesta, por linha:** para o **token**, *não* é verdade que só a
prova de container cobre — o degrau 2 é escrevível e barato, e é o que eu
recomendaria se a decisão fosse minha. Para o **boot**, é verdade: não há
verificador sem casar prosa, e a prova de container é o único instrumento. Isso
não é lacuna a fechar depois; é o argumento de que **a prova de container tem de
ser gate obrigatório, e não opcional** — ela é a única cobertura da terceira
linha, e um gate que se pode pular não cobre nada.

**A forma geral, que é o que sai daqui:** a classe fecha quando a exigência é
conferida sobre o **objeto que ela governa**, e não sobre os caminhos que o
produzem. Onde não há objeto — precondição de boot é procedimento —, não há o que
medir, e sobra a execução.

#### Uma quinta ocorrência começou nesta peça, e foi um mecanismo que a parou

Commitar o relatório da oitava auditoria levou `docs/progress/` de 41 para 42, e
o README continuava dizendo **41**. É a mesma classe — instância criada, quem
afirma a contagem não varrido —, e ela não chegou a existir como defeito porque
`check_readme_atual.py` **deriva o número da árvore** e reprovou na mesma sessão,
com o número certo na mensagem.

Não é anedota: é o degrau 1 medido em campo, e no eixo em que a regra escrita
falhou quatro vezes. O que separa este caso dos outros quatro não é cuidado — é
que aqui a afirmação tinha um objeto do qual derivar.

**Vence em:** a sua palavra. Nada do mapa foi implementado nesta peça; o conserto
é o da §7.6, e o mapa está aqui para ser decidido, não executado.

---

## 8. A nona auditoria — B1, e a terceira assimetria de epoch

### 8.1 O defeito, e por que ele só aparece numa combinação

Duas metades respondiam **a mesma pergunta** — *"este predicado já tem veredito
que sustenta a métrica da epoch corrente?"* — com critérios diferentes:

| Lado | O que perguntava | Onde |
|---|---|---|
| avaliador | há veredito deste predicado **na linhagem corrente**? | `_ja_satisfeito_na_corrente` |
| computador de `TTCV`/`TTRV` | há veredito deste predicado **na epoch corrente**? | `e.simulation_epoch == corrente` |

Os dois conjuntos coincidem quase sempre, porque `simulation_epoch == corrente`
**implica** estar na linhagem corrente. A recíproca é falsa, e é toda a distância
entre eles: `events/linhagem.py:138` abandona apenas `ancora < j < indice`, então
um rollback ancorado **em ou depois** do `verification_predicate_satisfied` o
deixa vivo na linhagem carregando a epoch antiga. O avaliador não reemitia — via
o veredito na linhagem —, e o computador o descartava — via a epoch errada.

E era **irrecuperável**: refazer a ação não produz transição, porque a flag já
está `True`. A metade de verificação do par sumia pelo resto do exercício, sem
nada falhar. É o modo de falha que `03` §3.0 nomeia: *"a métrica não falha, ela
deixa de marcar"*.

**O motivo normativo é o que torna o caso caro:** `technical_failure` é a única
linha de `09` §3.1 que **não** descarta epoch — *"a equipe não é penalizada por
bug do ambiente"* (`03` §3.5). Com ele, a epoch 0 continua em cálculo, atravessa
o `apenas()`, e a divergência decide sozinha. Com `facilitation`, o piso de
`epochs_em_calculo` já teria excluído a epoch antiga, e a resposta viria de outra
regra — que é por que a matriz da §8.4 usa `technical_failure` nas quatro células.

### 8.2 O vermelho veio antes do conserto, e isso não é cerimônia

O auditor derivou o B1 **por leitura** e disse isso na seção *"o que eu não
consegui verificar"*: o worktree dele não tem ferramenta de escrita. A primeira
coisa desta peça foi plantar a sequência de quatro passos com o `LacoDeVerificacao`
ligado, atravessando até a métrica, e **medir**:

```text
FAIL: test_o_veredito_e_reemitido_na_epoch_nova   AssertionError: 0 != 1
FAIL: test_ttcv_continua_marcada                  `TTCV` sumiu apos um rollback
                                                  que nem alcancou o veredito
FAIL: test_o_redisparo_nao_e_a_saida              False is not true
```

Os dois testes de **premissa** da mesma classe passaram desde o início — o corte
de fato não alcança o veredito, e a contenção de fato continua satisfeita na
linhagem corrente. Sem eles, o vermelho poderia estar medindo outro defeito.

### 8.3 O conserto foi a pergunta, e não o alinhamento dos filtros

Alinhar os dois filtros por coincidência deixaria a classe D4 de pé: duas
implementações concordando hoje e livres para divergir amanhã. O que foi feito é
o que `epochs_em_calculo` virou depois do H1 da terceira auditoria — **uma função,
consumida pelos dois lados**:

`range-core/events/veredito.py::veredito_da_epoch_corrente`.

**Onde ela mora é consequência, e não conveniência.** Em `metrics/` o avaliador
importaria métrica; em `engine/` o computador importaria engine. `range-core/events/`
é a camada de que os dois já dependem — o argumento é literalmente o do cabeçalho
de `events/linhagem.py`, e a whitelist de `check_core_contract_imports.py` cobrou
o motivo por escrito antes de aceitar o módulo novo.

**O critério é a epoch, e a linhagem não é um segundo filtro.** Ela é implicada:
`current_epoch` conta os rollbacks gravados e o store carimba a epoch antes do
append, logo evento de epoch corrente é posterior ao último rollback, e
`escritas_sobreviventes` só abandona posições estritamente anteriores ao corte.
Sem essa implicação a função seria inconsumível pelo lado da métrica, que recebe
apenas os eventos do lado `verification` (`00` §3.2) e não tem o fluxo total de
que `escritas_sobreviventes` precisa. Por isso ela é **afirmada**, e não
postulada: `AImplicacaoQueSustentaAFuncaoUnica`, sobre rollbacks encadeados com
âncoras diferentes — inclusive a recíproca, que é falsa e é o que produziu o B1.

A chave do payload foi junto. Ela era declarada nos **dois** módulos, com um teste
cruzando as cópias; a função única precisa dela, e o teste que cruzava virou
tautologia. O que sobrou afirma o que ainda se pode afirmar: que nenhum dos dois
voltou a escrever o literal.

**Nenhum caso hoje verde mudou de comportamento**, e isso é medição e não análise:
735 testes, `OK`. A razão é a implicação — os dois critérios só divergem no ramo
do B1.

### 8.4 A matriz, e as duas violações plantadas

Os testes das duas metades **se evitavam**, e não por acaso: os do laço ancoravam
sempre na abertura (o que corta o veredito e faz os dois critérios concordarem por
construção), e os da métrica punham o rollback antes do veredito. Duas suítes, sem
se falar, escolheram a mesma metade da matriz — e o comentário de
`test_metrics_verificacao.py:227-231` chega a registrar o sintoma do B1 observado
e contornado pelo arranjo do teste.

`AMatrizDoCorteEDoPredicado` cobre as quatro:

| # | o corte alcança o veredito? | o predicado ainda vale? | reemite | `TTCV` |
|---|---|---|---|---|
| A | sim — âncora na abertura | não, o disparo caiu junto | não | não marcada |
| B | sim — âncora no disparo | sim, a flag sobreviveu | sim | marcada |
| C | **não** — âncora no veredito | sim | sim | marcada |
| D | **não** — âncora no desligamento | não, a opção desligou | não | não marcada |

**A célula C era o B1. A célula D é o par dela**, e existe para fechar a correção
pelo outro lado: nela o veredito de epoch 0 está **vivo na linhagem corrente**, e
`TTCV` mesmo assim não marca — porque o mundo corrente deixou de satisfazer a
contenção. Sem D, "consertar" removendo o filtro de epoch da métrica passaria na
suíte inteira, e `TTCV` marcaria contenção que o exercício já desfez.

As duas violações plantadas medem exatamente isso:

| Violação plantada | Quem reprova |
|---|---|
| o avaliador volta a suprimir por linhagem | **C** — e A, B e D seguem verdes: era a combinação que faltava |
| o filtro de epoch removido da função única | **D**, A e C |

A célula D é também o que mede a escolha de `technical_failure`: com a segunda
violação plantada, `test_metrics_verificacao.py` inteiro continuou verde, porque
os casos dele usam `facilitation` e ali `epochs_em_calculo` já responde antes.

### 8.5 A classe — e a pergunta do mecanismo, medida

**É a terceira assimetria de epoch desta fase:** `epochs_em_calculo` lido de um
lado só (H1 da terceira auditoria), o instante de referência de `since` (H1 da
quarta), e agora o veredito. A norma de `09` §3.1 vem sendo implementada **de um
lado por vez**.

A pergunta que o proprietário fez: *há mecanismo possível — algo que cobre que
todo consumo de epoch passe pela mesma função — ou a resposta honesta é que só a
matriz de testes cobre?*

**A formulação está errada, e a medição é o que mostra isso.** Nove módulos de
`range-core/` leem `.simulation_epoch`, e os nove são legítimos — o store carimba,
o fold confere, a projeção devolve, o desconto agrupa. Mas o B1 **não foi epoch
lida errado: foi epoch não lida**. O avaliador não tinha comparação de epoch
nenhuma, e é por isso que ele estava errado. Um verificador que cobre *quem lê*
não vê *quem deixou de ler* — ele teria olhado para os nove e passado.

A propriedade que estava quebrada não é *"todo consumo de epoch passa pela mesma
função"*. É **"a mesma pergunta tem uma resposta"**, que é a D4, e epoch é apenas
o campo em que as duas respostas divergiam.

**Nessa formulação há mecanismo, e ele é estrutural.** Medido nesta árvore, por
AST, contando quais módulos comparam `event_type` contra cada constante:

| Tipo | Módulos que o selecionam |
|---|---|
| `ROLLBACK_PERFORMED` | 8 |
| `EXERCISE_STARTED` | 5 |
| `INJECT_FIRED` | 4 |
| `INTEGRITY_VALIDATION_DECLARED` | 3 |
| `ASSESSMENT_SUBMITTED` | 2 |
| os outros nove tipos | 1 |

Isso mata a regra ingênua — *"um dono por tipo"* — antes de ela ser proposta:
`ROLLBACK_PERFORMED` tem oito consumidores e eles fazem **perguntas diferentes**
sobre o mesmo evento (achar o corte, contar a epoch, restaurar o relógio, agrupar
congelamentos). Dono único aqui seria uma função com oito sentidos.

O que sobra é a forma que já funciona nesta árvore: **allowlist por tipo,
declarada com o motivo** — a mesma de `check_core_contract_imports.py`. E ela é
testável contra este próprio defeito: escrever `_ja_satisfeito_na_corrente` faria
`VERIFICATION_PREDICATE_SATISFIED` passar de um para **dois** selecionadores, e a
allowlist reprovaria até alguém escrever por quê. Ter na mesma tela *"o avaliador
busca este evento para decidir se suprime a emissão"* e *"o computador busca este
evento para marcar TTCV"* é o ponto: a pergunta *"então são duas respostas para a
mesma pergunta?"* fica difícil de não fazer.

**E o limite, dito com a taxonomia da §7.7:** é degrau 1.5, não degrau 2. Ele
cobra **declaração, não concordância** — dois consumidores declarados podem
continuar divergindo, e nenhum AST decide se duas buscas têm o mesmo propósito,
porque propósito não é estrutura. O que ele muda é *quando* a duplicação fica
visível: no commit que a cria, em vez de na nona auditoria.

Vale registrar que o mecanismo **funcionou comigo nesta peça**, no eixo vizinho:
`check_core_contract_imports.py` reprovou `events/veredito.py` no primeiro `rc=1`
e só aceitou depois de eu escrever por que aquele módulo existe naquela camada. É
o mesmo formato, aplicado a outro fato.

**A resposta honesta, em duas linhas.** Para *"todo consumo de epoch pela mesma
função"*: não, e não é limitação de ferramenta — é que a propriedade não é essa.
Para *"a mesma pergunta tem uma resposta"*: sim, existe mecanismo, é barato, é AST
pura, e teria pego este B1 — mas cobre o **nascimento** da duplicação, não a
divergência entre duplicatas declaradas. Para **essa**, a matriz de testes é o que
cobre, e é por isso que ela tem as quatro células e não as duas que faltavam.

**Vence em:** a sua palavra. O verificador de allowlist por tipo **não foi
implementado** nesta peça — o conserto é o da §8.3, e o mapa está aqui para ser
decidido, não executado.
