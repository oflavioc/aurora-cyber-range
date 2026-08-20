# Fase 6 — Objetivos, rubricas, métricas

**Status: NÃO INICIADA** — sem branch, sem implementação e sem auditoria. Este
registro existe apenas para abrigar as duas pendências abertas antes da fase,
no `spec-change` `particao-das-metricas-pareadas`. A linha de status está aqui
porque `check_readme_atual.py` decide *"a fase fechou?"* por ela, e registro sem
status é registro que o verificador não consegue ler.

**Registro em aberto.** A fase ainda não começou: não há branch, não há
implementação e não há auditoria. Este arquivo existe antes dela por um motivo
só — duas pendências nasceram no `spec-change` `particao-das-metricas-pareadas`,
que é anterior à fase, e pendência sem lugar é pendência que ninguém encontra.

Registrá-las no `fase_5.md` seria pior: aquele registro está fechado e auditado,
e acrescentar linha a um documento encerrado é reescrever história de uma fase
que já passou. Elas não são achados da Fase 5; são consequências declaradas de
uma mudança de norma feita entre as duas.

O resto deste registro — decisões, seções de implementação, DoD com prova — é
escrito pela fase, quando ela existir.

## 1. Plano da fase — sete peças

| # | Peça | Estado |
|---|---|---|
| 1 | Biblioteca BARS: nove competências versionadas, contrato, integridade referencial | **fechada** |
| 2 | Motor de objetivos: binding evento→objetivo na projeção, `objective_evidence` | |
| 3 | `audit_query_performed` e as ações de declaração nos endpoints | |
| 4 | Predicados de verificação e o motor que os avalia | **antes da 5** |
| 5 | Métricas: os dois computadores, o insumo tipado, epoch como cálculo | **depois da 4** |
| 6 | Calibração: Brier no escopo revisado, sinais, `TTIV` por limiar | |
| 7 | Divergência entre avaliadores e a janela de asseguração prematura | |

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

## 6. Pendências

Abertas antes da fase, no `spec-change` `particao-das-metricas-pareadas`.
Prefixo `P6-`.

| Id | O que é | Vence em |
|---|---|---|
| P6-1 | `classification_declared` não é caso calibrável, e `03` §3.0 aponta a acurácia da classificação para a calibração | **Fase 6** — ver abaixo |
| P6-2 | `observable_impact` não existe em contrato nenhum, e é o *start* de `TTA` | **Fase 6** — ver abaixo |
| P6-3 | `before` e `after` são declaráveis na gramática de predicado e o avaliador não os implementa | **condição** — ver abaixo |

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

#### P6-3 — folhas temporais declaráveis e não implementadas

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
