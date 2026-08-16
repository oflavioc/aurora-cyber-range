# Fase 3 — API mínima

**Status: EM CURSO.** Aberta em 16/08/2026, com a Fase 2 concluída — nove de nove
itens e auditoria PASS.

**Status: FECHADA para auditoria.** Cinco peças entregues, **quatro de quatro**
itens da DoD com prova executável (§5.1), e as três pendências de aparato que
venciam neste checkpoint fechadas.

**211 testes — zero pulos com a stack efêmera no ar**, 27 verificações no CI, 183
arquivos classificados pelo gate.

Aberta em 16/08/2026; fechada em 17/08/2026.

---

## 0. Por que este registro começa antes da fase

Mesma razão da §0 do registro da Fase 2: o plano da fase decidiu seis coisas
antes de existir código, e **conversa não é fonte versionada**. A Fase 2 provou o
custo de deixar decisão viver só no diálogo — e provou de novo, pelo avesso, com
a P2-6: uma afirmação registrada sem conferência atravessou três camadas.

---

## 1. O que a fase entrega, conferido na fonte

`07` Fase 3 — `academus-api` com JWT, RBAC, três entidades (Aluno, Turma, Nota) e
degradação real por flag em pelo menos três endpoints.

**NON-GOALS:** modelo completo, seed em escala, auditoria com hash.

**Critérios:** só **T2**, que é "Fases 1–3". Três dos quatro bullets dele já estão
mecanizados desde a Fase 1 — literais, `codegen --check`, `event_type` fora do
catálogo. O primeiro — *"flag não declarada impede boot, com mensagem nomeando
flag e arquivo esperado"* — fechou na Fase 2, no loader de pack.

**`05_SECURITY_REQUIREMENTS.md` é leitura obrigatória aqui**, e não por
formalidade: a fase traz autenticação. §8 exige que nenhum serviço fique exposto
sem autenticação — exceto wallboard e participant-view —, e que senha de seed
venha do `RANDOM_SEED`, nunca de valor trivial. §6 fixa bind em `127.0.0.1`.

---

## 2. A P2-6 não vence aqui, e a premissa dela era falsa

A pendência dizia que o serviço consumidor nascia na Fase 3. **Não nasce.**

| | Fonte |
|---|---|
| `academus-api` | Fase 3 ✅ |
| `federated-identity-simulator`, que produz `vpn_access_revoked` | **Fase 11** — `07`, tabela de fases; `09` §6 dá o `producer` |
| os cinco `state_effect` de `participant_action` | nenhum é entregável da Fase 3 |

A Fase 3 emite `audit_query_performed`, de classe `observation`. **Movida para a
Fase 8**, que é a primeira com item de DoD que obriga a ligação — *"as sete ações
de continuidade aplicam efeito mecânico e custo"*, e `continuity_action_taken` é
um dos cinco.

A frase errada que eu havia escrito em `01` §4.4 está corrigida em `spec-change`
próprio — **submetido e ainda aberto** quando esta linha foi escrita. O registro da causa está na P2-6 do `fase_2.md`: **três camadas, cada
uma confiando na anterior.**

---

## 3. As decisões da fase, tomadas antes do código

### D0 — a DoD citava uma flag que o adapter não tinha — **FECHADA**

`academus.grades_readonly`, no item 2. Não é spec-change: `01` §5.2 dá ao adapter
a declaração das suas flags, e `07` Fase 1 entregou o arquivo como *"inicial"*.
Declarada em `domains/academus/flags.yaml`, com `category: integrity` — `02` §9
nomeia o congelamento de lançamento de notas como ação de continuidade cujo
efeito é *"impede propagação de adulteração"*. O que ela protege é o dado, não o
serviço.

**A checagem que a encontrou é a peça 1, e ela achou seis divergências, não uma.**
Ver a §4.

### D1 — a API lê a flag do Redis, não do fold — **DECIDIDA, não implementada**

`01` §4 é explícito: *"Simulation State — flags do contrato — Redis (projeção) +
event store"*.

**E a medição da Fase 2 fecha o argumento sem suposição:** reconstruir do zero
custa **2,874 s em 150 mil eventos** (§3.8 do `fase_2.md`), com 64% em consulta e
hidratação. Por request é inviável, e o número está medido, não estimado.

**Duas propriedades acompanham a decisão, e são propriedades — não cuidados:**

1. **Cache frio e divergência têm comportamento definido.** O Redis é projeção
   **descartável e reconstruível**: perdê-lo não pode produzir resposta errada,
   só resposta mais cara. A API que encontra o cache vazio reconstrói do store; a
   que encontra divergência entre Redis e store trata o **store como
   autoridade**, porque é ele que `01` §4.1 declara reconstruível do zero.
2. **Quem escreve no Redis não é um segundo caminho de escrita de estado.** O
   fold continua sendo a única autoridade: o Redis recebe **o resultado do
   fold**, e nada mais escreve nele. Uma rota que escrevesse flag direto no Redis
   produziria estado invisível ao rollback — exatamente o que a §4.4 deixou de
   afirmar quando a P2-9 foi corrigida.

**Como isso vira propriedade e não disciplina:** a escrita no Redis fica atrás de
uma superfície que só aceita `SimulationState`, e a checagem que a guarda é a da
peça 3. Sem isso, "só o fold escreve" é frase, e frase envelhece.

### D2 — dois conjuntos de papéis, e eles não se encontram

`03` §7 tem `facilitador`, `operador` e `avaliador` — papéis **do exercício**. A
API precisa de papéis **do domínio**: aluno, professor, secretaria, financeiro.

**Misturá-los põe desenho de exercício dentro do adapter**, que é a fronteira do
invariante 1 vazando por onde o verificador não olha — ele varre import, não
vocabulário. O papel de exercício não entra no token do domínio.

### D3 — o que o JWT carrega

Decorre da D2: `sub`, papel **de domínio**, expiração. `persona` de exercício
**não entra**. `AURORA_JWT_SECRET` já existe no `.env.example`.

> **Correção, feita na peça 4.** A redação anterior dizia que *"`05` §8 exige que
> segredo e senha de seed venham do `RANDOM_SEED`"*. É falso, e é a §1.5 outra
> vez: eu lembrei a seção em vez de lê-la. `05` §8 fala de **senha de seed** —
> credencial de persona sintética dentro do exercício —, e não do segredo de
> assinatura.
>
> A diferença não é de redação. `RANDOM_SEED` é **reproduzível por desenho**:
> está versionado em `.env.example` e `06` T8 exige que duas execuções com o
> mesmo valor produzam dataset idêntico. Uma chave HS256 derivada dele seria
> conhecida por qualquer um com acesso ao repositório — e a frase estava escrita
> como premissa de uma decisão que ainda não tinha sido implementada.
>
> O que a peça 4 aplica é a **disciplina** do `RANDOM_SEED`, e não o valor:
> ambiente primeiro, sem default, recusa alta, lido por código do núcleo.

### D4 — degradação declarativa, não `if` por rota

`if flag:` espalhado é a forma que não sobrevive ao `check_contract_literals` e é
o oposto do que a Fase 2 fez com `effects`. A degradação é **declarada na rota** e
verificável por AST.

**O que isso torna possível:** os itens 1 e 2 da DoD deixam de ser dois casos de
teste e passam a ser uma propriedade sobre a superfície inteira — *"toda rota que
declara degradação por flag consulta o registry, e nenhuma consulta flag que não
declarou"*.

### D5 — a superfície da API declarada antes da implementação

Rotas, papel exigido e flags consumidas, declarados **antes** de existir rota, com
a checagem que os fixa escrita no mesmo commit. Mesma forma de
`check_store_read_surface.py`: whitelist, não blocklist — rota nova reprova até
ser declarada, e o custo é uma conversa.

---

## 4. A peça 1, e o que ela achou

`scripts/check_spec_flags.py` cruza **flag citada em `docs/spec/`** com **flag
declarada em `domains/<adapter>/flags.yaml`**.

**O buraco que ela fecha:** `01` §5.4 diz que nenhum serviço lê ou escreve flag
não declarada, e o loader recusa boot com flag desconhecida — as duas garantias
valem para o código e para o pack, e **a spec não passava por nenhuma**.
`check_spec_examples.py` valida blocos YAML; a DoD é markdown.

É a mesma família do que a Fase 2 anotou sobre o catálogo de eventos: *a tabela
de `09` §4.1 é markdown, e o CI não a cruza com o contrato*.

**Primeira execução: seis divergências**, e cinco eram invisíveis:

| Flag | Onde | Disposição |
|---|---|---|
| `academus.grades_readonly` | `07` Fase 3, item 2 da DoD | **declarada** — é da minha fase |
| três flags do `federated-identity-simulator` | `02` §7 | pendentes de fase |
| duas flags do `mec-gateway` | `02` §7 | pendentes de fase |

### A terceira classe, e por que ela não é uma lista de exceção comum

As cinco são de serviços da **Fase 11**. Declará-las agora **não seria
inofensivo**: entrariam nas constantes geradas e virariam painel no wallboard, que
`01` §5.3 renderiza **por convenção** a partir de `wallboard_group` — a sala veria
indicador de serviço que não existe. É a mesma disciplina que a Fase 2 aplicou ao
`RANDOM_SEED`: não inventar consumidor para justificar declaração.

`domains/flags_pendentes.yaml` registra cada uma com **quem a trará**, e a
checagem cobra as duas direções do envelhecimento: entrada já declarada reprova
(sobrou), entrada que a spec deixou de citar também (mente). Sem isso ela vira o
que toda lista de exceção vira.

### O hook achou um defeito de desenho, pela segunda vez nesta linhagem

A primeira versão da lista morava **dentro do `.py`**. O hook de arquitetura a
recusou: `<adapter>.<nome>` não declarado dentro de código é a assinatura exata do
erro de digitação que `tools/check_contract_literals.py` existe para recusar — e
ele recusaria.

**Estava certo, e o motivo é melhor que o que ele checa:** uma checagem cujo
trabalho é *nomear flags não declaradas* não pode escrevê-las em código. Nome de
flag em lista de exceção é **dado sobre flags**, não código. Foi para YAML.

É a mesma forma do achado do `RANDOM_SEED` na Fase 2, quando o hook recusou
escopos com aparência de flag: o bloqueio apontava para ambiguidade real.

### Seis eixos de prova negativa

Citada sem declaração; pendente que sobrou; pendente que a spec não cita; dois
casos verdes de controle; e **a varredura sobre documento de spec plantado em
diretório temporário** — o eixo que o conjunto injetado não cobre, e que exercita
a leitura de `docs/spec/` sem tocar em `docs/spec/`.

### E as duas entradas na allowlist do auditor, no mesmo commit

A regra que o B1 da Fase 2 cobrou, escrita dentro do próprio `readonly_bash.py`.
`phase0_negative_tests.py` foi de 38 para **40** leituras legítimas, com prova nas
duas direções.

---

## 4.1 A peça 2 — a superfície declarada antes de existir rota

`domains/academus/api_surface.yaml` e `scripts/check_api_surface.py`. **Seis rotas
declaradas, zero implementadas**, e a checagem já roda.

### O que foi declarado antes do código não é a lista — é a obrigação

**Lista escrita antes do código subestima, sempre.** Se a garantia fosse *"o que
está declarado é o que existe"*, ela valeria só para o que alguém lembrou de
prever, e a rota esquecida seria justamente a que ninguém declarou.

Por isso a checagem cobra **igualdade nas duas direções**, e a que importa é a
inversa:

| Eixo | Reprova quando |
|---|---|
| **rota implementada e ausente da declaração** | é a direção sem a qual a lista vira documentação com sintaxe de verificador |
| rota `implementada` ausente do código | a declaração envelheceu |
| rota `planejada` que **já existe** no código | impede `planejada` de virar esconderijo permanente |

O terceiro eixo é o que fecha o buraco óbvio dos dois estados: sem ele, bastaria
declarar tudo como planejado para a checagem nunca cobrar nada.

### Três coisas a mais que a superfície carrega

- **Papel de exercício é recusado por nome.** `facilitador`, `operador` e
  `avaliador` são de `03` §7 e não podem aparecer na superfície de domínio — se
  aparecerem, o adapter passou a conhecer desenho de exercício, que é a fronteira
  do invariante 1 vazando por onde o verificador **não olha**: ele varre import,
  não vocabulário.
- **Flag de rota é conferida contra o adapter.** É a terceira porta pela qual um
  nome de flag entra no sistema — depois do pack (loader, Fase 2) e da spec
  (peça 1) —, e agora as três têm a mesma guarda.
- **Em YAML, e não em Python**, pelo mesmo motivo da lista de pendentes: nome de
  flag dentro de `.py` é literal que `check_contract_literals` recusa.

### O limite, verificado em vez de declarado

A varredura é por **AST**, e rota registrada em tempo de execução —
`add_api_route` com caminho calculado — **não é vista**. A alternativa seria
importar a aplicação dentro do verificador, e um gate que importa o que julga
deixa de ser gate.

`probe_do_limite_declarado` afirma o limite: planta uma rota dinâmica e exige que
a varredura **não** a encontre. Fica vermelho no dia em que deixar de valer —
mesma forma de `test_truncar_a_cauda_NAO_e_detectado`.

### Dez eixos de prova negativa

Os três de estado, os dois de papel, o de flag, um caso verde de controle, **a
varredura sobre módulo plantado** — sem ele, `rotas_implementadas` poderia
devolver conjunto vazio sempre e todos os outros continuariam verdes, porque
nenhum deles a chama — e o limite acima.

---

## 4.2 A peça 3 — a projeção materializada, e quem tem direito de escrevê-la

`range-core/state/cache.py`, `StreamHead` no store, e
`scripts/check_fold_authority.py`.

### Cache frio — a API nunca responde a partir de defaults

**Defaults não são fallback.** São o resultado correto de foldar um fluxo
**vazio**, e só isso. Com `exercise_started` no store, responder defaults
inverteria uma flag de default `true` — o caso que motivou o estado **total** do
fold na Fase 2.

Então cache frio não tem resposta rápida: tem **reconstrução**. O custo é de
partida, pago uma vez, e o que o cache elimina depois é o **fold**, não a
consulta de cabeça.

As duas metades estão em teste, e a segunda impede a primeira de virar
superstição: `test_cache_frio_NAO_responde_com_defaults` e
`test_defaults_NAO_sao_fallback_mas_sao_a_resposta_do_fluxo_vazio`.

### Divergência — quem detecta, e quando

**A cada leitura, e pela `StreamHead`** — quantos eventos há e qual é o último.
É comparação da **identidade da entrada**, não do estado: uma consulta de índice,
não um fold.

O argumento contra as duas alternativas é o mesmo número: comparar o estado a
cada request seria refazer os 2,874 s que o cache existe para evitar; não
comparar nada faria de *"o store é autoridade"* uma frase. **O cache poupa o
fold, não a consulta.**

`StreamHead` tem **dois** campos, e não um: só a contagem confundiria fluxos de
mesmo tamanho — o store restaurado de backup —, e só o último `event_id`
confundiria o fluxo truncado, que é o limite que
`test_truncar_a_cauda_NAO_e_detectado` declara e que **continua declarado**.

**A ordem em `current` é parte da garantia:** a cabeça é lida **antes** da
projeção. Lida depois, uma escrita que caísse no meio compararia a projeção nova
com a cabeça velha e concluiria que vale. Há teste que observa a ordem.

### `head()` reprovou na checagem da P2-2, e isso foi o mecanismo funcionando

Método público novo no store → `check_store_read_surface` recusou até ser
declarado. **Era exatamente o desenho:** *"o custo é uma conversa, e a conversa é
o ponto"*.

O argumento que o admitiu: a garantia de `01` §4.1 é sobre **caminho de leitura
de evento**, e `head` não devolve evento — devolve a identidade da entrada. Não
há o que filtrar num par de valores, e ele continua sem parâmetro. Um
`read_since(head)` continuaria reprovando.

### A porta não aceita estado — e é por isso que a autoridade é propriedade

`SimulationStateCache.refresh` recebe **o fluxo e as declarações**, e folda
dentro. Não há método que aceite um `SimulationState` pronto.

A alternativa óbvia — `write(state)` com verificação de procedência — **não
funciona**: `SimulationState` é um dataclass, e qualquer um constrói um. A
procedência não está no valor; está em **quem calcula**. Então a porta calcula.

`check_fold_authority.py` fecha a outra metade, com igualdade nas duas direções:
`SimulationState` é construído em **dois sítios declarados** — o fold, que
calcula, e a desserialização do Redis, que **não** calcula (sem `Declarations`,
sem fluxo, sem regra: `json.loads` e dois campos) — e nenhum método público da
porta aceita estado pronto.

### Os probes acharam três defeitos, e um deles era da própria checagem

| | O que era |
|---|---|
| 1 | `main()` chamado sem argumento — a checagem rodava **sempre contra o core real**, inclusive quando o probe passava árvore plantada. Os quatro probes reprovaram na primeira execução |
| 2 | renomear a classe da porta fazia a checagem devolver *"nenhum método aceita estado"* — **verdadeiro por vacuidade**. Mesma classe do eixo de varredura da peça 2 |
| 3 | eu inventei um digest de imagem Redis para o CI. O compose já tinha o valor pinado, e era só ler |

O terceiro não foi achado por probe, e sim por `grep` — e é o mais barato de
cometer: digest inventado ou não existe, e o job quebra, ou existe e aponta para
outra coisa. Virou a **P3-1**.

### Sem duplo, por decisão

A Fase 2 fechou com **zero mocks**, e a auditoria PASS registrou isso. Um duplo
de Redis seria a primeira dublagem da árvore, e testaria a si mesmo.

`InMemoryProjectionCache` **não é duplo**: é o segundo backend da mesma porta,
como `InMemoryEventStore` é do store — serve ao processo único e é exercitado
como implementação de verdade.

Para o Redis, a forma é a do Postgres, que a auditoria já aprovou:
`AURORA_TEST_REDIS_URL` própria — os testes **escrevem e apagam** a chave —,
`skip` que imprime o comando, e **serviço no CI**, com o mesmo digest do compose.

---

## 4.3 A peça 4 — JWT, RBAC, e onde a negação mora

### A separação dos dois conjuntos de papéis virou guarda, e é a mesma da peça 2

A peça 2 já recusava papel de exercício **na rota**. O JWT é a outra porta, e
nenhum verificador de import enxerga um claim: um token com `persona:
facilitador` não importa nada de lugar nenhum.

**Estendida, e não uma segunda checagem.** Duas listas sobre a mesma fronteira
divergem, e a que diverge em silêncio é sempre a que ninguém está olhando — é a
D4 do catálogo de classes.

O que a extensão acrescentou:

| Eixo | Reprova quando |
|---|---|
| papel de exercício **dentro de `papeis_de_dominio`** | era o buraco da peça 2: o papel na rota reprovava, e a lista de origem passava |
| `token.claims` × as chaves que o código assina | nas duas direções, por AST sobre `_payload` |
| a função que monta o payload sumiu | renomear devolvia *"as claims batem"* — **verdadeiro por vacuidade** |
| claim com vocabulário de exercício | `persona`, e os três papéis de `03` §7 |

**O que fecha o mecanismo é `emitir_token` ler `papeis_de_dominio` em tempo de
execução.** Junto com a checagem que recusa papel de exercício naquela lista,
`emitir_token(sub, "facilitador")` deixa de ser proibido e passa a ser
**inexprimível**: para o token existir, o papel precisaria estar na lista; para
estar na lista, precisaria passar pelo gate que o recusa por nome.

E é whitelist, não blocklist: `reitor` também cai. Recusar só os três seria
proteger contra o erro que já tem nome.

### 403 × 404 — a pergunta estava no lugar errado, e a spec já tinha opinião

`06` T6 fixa **403** para acesso a endpoint fora do papel. É o único lugar da
spec com opinião sobre isso, e é sobre papéis de exercício.

Mas o canal de inferência que preocupa num exercício sobre assimetria **não está
no número**: está em a resposta **variar com a existência do recurso**. 403
confirma que o recurso existe *se e somente se* a negação o consultou — e um 404
emitido depois de procurar vaza pelo tempo, com o número "certo".

Então a propriedade é **indistinguibilidade**, e ela é estrutural: `autoriza` é
dependência global e recebe `Request` e mais nada — **não há repositório ao
alcance dela**. A negação não tem como depender do que ela não pode ler.

`test_a_negacao_NAO_distingue_recurso_existente_de_inexistente` compara as duas
respostas, status e corpo. Fechada essa porta, o código de status fica livre para
seguir T6, e escolher 404 aqui criaria **duas políticas de negação no mesmo
produto** — cuja diferença seria, ela própria, informação inferível.

| | Quando |
|---|---|
| **401** | sem token, ou token que não verifica. Com `WWW-Authenticate` |
| **403** | token válido, papel que a rota não admite |
| **404** | só para quem **tem** direito de saber que o recurso não existe |

### O segredo: a disciplina do `RANDOM_SEED`, e um placeholder que virou vazio

Ambiente primeiro, `.env` como fonte local, sem default, recusa alta, lido por
código do núcleo. Mínimo de 32 caracteres — chave curta é quebrada offline a
partir de **um** token capturado, sem tocar no serviço.

**O placeholder de `.env.example` passou a ser vazio**, e é o único daquele
arquivo que é. A diferença com `POSTGRES_PASSWORD` é de comportamento: senha de
banco copiada do exemplo falha no `connect`, alto e na hora; **segredo de JWT
copiado do exemplo funciona** — o serviço sobe assinando com uma chave versionada
neste repositório. Um segredo errado que se anuncia é menos perigoso que um que
se comporta.

Vazio, *"copiei o exemplo"* e *"não configurei"* viram o mesmo caso, e a recusa
que já existe cobre os dois. **O teste lê o `.env.example`** e afirma que o valor
de lá é recusado: repor um texto naquela linha deixa a suíte vermelha.

Varri o arquivo antes de escalar. Os outros dois valores sensíveis —
`POSTGRES_PASSWORD` e o `DATABASE_URL` que o embute — continuam com texto, e a
assimetria acima é o motivo, escrito onde ele será lido.

### A degradação não entrou aqui, e isso é verificado

As duas rotas implementadas são as que a peça 2 declarou com `flags: []`, e o
comentário que as declarou já dizia por quê: *"o RBAC precisa de rota que
NEGUE"*.

A garantia não é disciplina: **enquanto nenhuma rota implementada declarar flag,
nenhum módulo de `api/` pode importar `range_core.state`**. A regra sai de cena
sozinha no dia em que a peça 5 implementar a primeira rota com flag — é a
fronteira entre duas peças escrita como verificação, não como intenção.

### `POST /auth/token` continua `planejada`, por decisão

Emitir token exige **autenticar um usuário**, e usuário não é entidade da Fase 3:
`07` nomeia Aluno, Turma e Nota e põe "seed em escala" nos NON-GOALS. Um endpoint
que assinasse o papel pedido no corpo seria **vulnerabilidade intencional**, que
`CLAUDE.md` proíbe sem exceção.

O JWT da fase existe e é exercitado: `emitir_token` assina, e a suíte bate nas
rotas com token de verdade sobre o stack ASGI de verdade. O que falta é a porta
de entrada, e a terceira direção da checagem cobra a promoção no dia em que a
rota nascer.

### Sem duplo, de novo — e uma depreciação vista rodando

`TestClient` fala ASGI com a aplicação real. Um cliente escrito à mão seria o
duplo que testa a si mesmo, e a Fase 2 fechou com zero mocks por decisão
registrada.

`httpx2`, e não `httpx`: o `starlette` 1.6 emite `StarletteDeprecationWarning`
pedindo o primeiro — **observado ao rodar a suíte, não lido em changelog**. Pinar
o caminho já depreciado seria escolher, sabendo, o que quebra na próxima subida.
Ele fica em `[project.optional-dependencies].test`, fora de `dependencies`:
declarar dependência de teste como de execução é afirmar que ela é necessária
para rodar.

### A P3-1 fechada — o meu digest inventado, agora pego por mecanismo

`scripts/check_pinned_images.py`, sete eixos de prova negativa, com o defeito
real em primeiro lugar. Três asserções: toda imagem pinada por digest; digest
idêntico nos dois arquivos; imagem do CI existe no compose — porque o compose é a
stack e o CI existe para espelhá-la, e serviço só do CI é digest **sem par com
que ser comparado**, que foi como o meu entrou.

O sétimo eixo é o que a peça 3 ensinou duas vezes: compose ausente sai com `rc=2`
em vez de imprimir *"0 imagens, todas pinadas"*.

---

## 4.4 A peça 5 — as três entidades, e a degradação que não se explica

### A forma declarativa: o que a flag faz com a rota

Até a peça 4, `degradacao` era **prosa** no `api_surface.yaml` — e prosa não
executa. A peça 5 é quem a torna dado, na mesma família dos `effects` do pack:

```yaml
degradacao:
  - flag: academus.lms_degraded
    condicao: ligada
    efeito: latencia
    segundos: 2.5
  - flag: academus.lms_session_drop_rate
    condicao: proporcional
    efeito: recusa
    status: 503
    mensagem: 'Sua sessao foi encerrada. Faca login novamente para continuar.'
```

**A checagem que reprova rota que degrada fora dela não procura `if flag`** — e
essa é a decisão. Procurar o `if` seria a checagem óbvia e a fraca: bastaria
escrevê-lo de outro jeito. O que está afirmado é mais forte:

| | O handler |
|---|---|
| `range_core.state` | só `degradacao.py` importa. Estado ao alcance do handler é `if flag:` esperando para acontecer |
| constantes de flag geradas | **nenhum** módulo de `api/` importa. O nome chega como dado da declaração, como `flag_defaults` chega ao core |

O handler não tem `if flag` porque **não tem flag ao alcance**. É a forma da
peça 3 outra vez, e da peça 4: em vez de detectar o defeito, retirar o material
com que ele se escreve.

Mais seis eixos sobre a estrutura: vocabulário fechado de `condicao` e `efeito`;
`flags` e `degradacao` como conjuntos iguais nas duas direções; `recusa` sem
status de erro ou sem mensagem; `latencia` de zero segundos — degradação que não
se observa.

**E a `condicao` conferida contra o TIPO da flag em `flags.yaml`.** É o defeito
que eu teria cometido sem a checagem: `ligada` sobre `lms_session_drop_rate`, que
é `number` de 0 a 1, degradaria com `0.0` — o mundo normal — e o efeito ficaria
ligado o exercício inteiro, sem ninguém entender por quê.

### A degradação é observável sem ser explicada — e `flags.yaml` já sabia disso

A sala precisa **ver** o sistema cair, não ler um aviso dizendo que ele foi
derrubado. Uma resposta com "flag ativa" no corpo transforma exercício em
demonstração e destrói a assimetria que `00` §5 chama de desenho.

**A fonte já tinha a resposta, e eu não precisei inventá-la:** `flags.yaml`
declara `effect_ui` em linguagem de negócio desde a Fase 1 — *"Lançamento e
alteração de nota recusados; leitura e histórico seguem disponíveis"*. As
mensagens da degradação são a mesma língua, dirigidas ao participante.

Duas guardas, e elas olham coisas diferentes:

| | Onde |
|---|---|
| a checagem recusa mensagem que nomeie **a flag** ou vocabulário de mecanismo | no declarado |
| o teste varre a **resposta inteira** — corpo e cabeçalhos | no que sai pelo fio |

A segunda é a forma que `06` T6 fixa para isolamento de papel, aplicada a outro
assunto: teste de payload, não de intenção.

E há a metade que impede a primeira de virar superstição: **sem flag ligada,
nada muda** — as três rotas respondem 201, 201 e 200, e nenhuma latência é
aplicada. Uma API que recusasse sempre passaria em metade dos testes desta suíte.

### Um defeito da peça 4, achado aqui: `/openapi.json` respondia 200 sem token

A "falha fechada" da peça 4 valia para rota declarada e **não valia para rota que
o framework declara por você**. `/docs`, `/redoc` e `/openapi.json` entram por
`add_route`, que é Starlette puro e não passa pelo sistema de dependências — a
dependência global não as cobria.

Medido, não suposto: **200, 3.870 bytes** descrevendo a API inteira, sem token.
`05` §8 exige que nenhum serviço fique exposto sem autenticação, e num exercício
sobre assimetria a lista de rotas conta a quem ainda não entrou o que existe para
ser encontrado. As três estão desligadas, e há teste.

### A P3-3 respondida: **um campo**, e a resposta veio das três entidades

A pendência perguntava se o escopo de objeto era um campo ou três. Com Aluno,
Turma e Nota dá para ver: **é um campo**, porque todos os casos são *"um campo do
recurso é igual ao `sub`"*, e o que muda é **qual** campo — o que é valor, não
dimensão.

```yaml
escopo:
  professor: titular
```

`proprio` — o recurso **é** o sujeito. `titular` — o recurso **pertence** a ele.
Papel fora do mapa não tem restrição, e a `secretaria` está fora por desenho.

**A regra mora dentro da busca, e é isso que preserva a peça 4.** A negação de
papel é decidida sem consultar nada; a de objeto não pode ser — decidir se a
turma é sua exige lê-la. Então a saída não é negar depois de achar: é fazer
*"não é sua"* e *"não existe"* virarem **o mesmo caminho de código**.
`repositorio.turma(id, escopo)` devolve `None` nos dois casos, e o handler, que
só sabe tratar `None`, responde 404 sem nunca aprender a diferença.

A política continua sendo **uma**: a resposta nunca varia com a existência de um
recurso que quem pergunta não pode ver. 403 e 404 são consequências dela em
perguntas diferentes — *"este papel pode usar esta rota?"* e *"este recurso é
seu?"*. Um 403 aqui diria "existe, e não é sua".

E a escrita passa pelo mesmo lugar: o aluno não matricula o colega. Sem isso a
regra protegeria a consulta e deixaria a ação aberta, que é a metade que costuma
ser esquecida porque ninguém consulta para testar.

### O corte das três entidades, declarado

`07` põe **modelo completo** e **seed em escala** nos NON-GOALS, e sem o corte
escrito a peça cresce até parecer a Fase 7. Ele está no cabeçalho de
`registros.py`, com motivo por linha. Em resumo:

**Entra** — Aluno, Turma, Nota, mais `Turma.professor_id` (a regra `titular`
precisa de um dono, e dono que não existe no dado não é verificável) e
`Matricula` (rota que degrada precisa de caminho feliz, senão a degradação não é
*diferença*). Seis registros literais, em memória.

**Fica de fora** — tabela, SQLAlchemy e migration (**Fase 5**, que é quem tem o
seed: modelar agora seria modelar duas vezes, e migration desfeita é histórico
que mente); os volumes de `02` §6; regra de negócio de nota; Histórico, Diploma,
Bolsa e o papel `financeiro` — que continua declarado sem rota, e isso é a
superfície dizendo o que ainda não existe; paginação e busca; **e evento emitido
pela API**, que é Fase 5 (`06` T7) e Fase 8.

### A regra da peça 4 não se calou sozinha — ela foi substituída

A cerca da peça 4 dizia *"enquanto nenhuma rota implementada declarar flag,
`api/` não lê estado"*. Ela se calaria **hoje**, no commit em que a peça 5
declarou a primeira flag — e uma regra que evapora no dia em que o assunto dela
começa a existir não é uma regra.

Foi trocada pela whitelist permanente — só `degradacao.py` lê estado —, e há
probe afirmando que a troca está viva na árvore real: **exatamente um módulo lê
estado, e é o motor**. Se um dia o conjunto ficar vazio, a whitelist passaria a
ser verdadeira por vacuidade, e o probe fica vermelho antes disso virar silêncio.

---

## 5. Ordem das peças

| | Peça | Estado |
|---|---|---|
| 1 | checagem de flags citadas na spec + `grades_readonly` no adapter | ✅ |
| 2 | superfície da API declarada + a checagem que a fixa (D5) | ✅ |
| 3 | leitura de flag pela API (D1) — a porta e a autoridade do fold, antes do FastAPI | ✅ |
| 4 | JWT + RBAC (D2, D3), com os dois conjuntos de papéis separados | ✅ |
| 5 | as três entidades e a degradação declarativa (D4) — itens 1 e 2 da DoD | ✅ |

**A peça 1 é a única que paga antes de existir código dependendo dela**, e foi por
isso que veio primeiro: ela achou um item de DoD insatisfazível **antes** de
alguém tentar implementá-lo.

---

## 5.1 A Definition of Done, item por item, com a prova

`07_IMPLEMENTATION_PHASES.md` Fase 3. **Quatro itens, quatro provas executáveis** —
nenhuma linha desta tabela é atestação minha.

| | Item | Prova |
|---|---|---|
| 1 | `academus.enrollment_offline: true` faz o endpoint de matrícula retornar 503 | `tests/test_api_degradacao.py::ItensDaDoD::test_item_1_matricula_responde_503_com_a_flag_ligada` — 201 antes do inject, 503 depois, com o efeito vindo do **fold** sobre um `inject_fired` real |
| 2 | `academus.grades_readonly: true` bloqueia POST de nota com mensagem de negócio | `::test_item_2_nota_bloqueada_COM_MENSAGEM_DE_NEGOCIO` — 409 e o texto manda falar com a coordenação. E `::test_a_leitura_de_nota_segue_disponivel_com_a_flag_ligada`, porque o `effect_ui` da flag diz que a leitura segue |
| 3 | RBAC nega acesso cruzado entre perfis | `tests/test_api_rbac.py::RBAC::test_ACESSO_CRUZADO_e_negado_nas_duas_direcoes` — professor não lê aluno, aluno não lê turma, **e** professor lê a turma dele. O par é o que discrimina: negar tudo passaria em dois terços |
| 4 | Nenhuma string solta de flag no código-fonte, verificado por lint | `python tools/check_contract_literals.py`, no job `arquitetura`. Exercido nesta fase: o hook **recusou** a primeira versão de `tests/test_api_degradacao.py`, que escrevia os quatro nomes de flag como literal |

**O item 4 não é herdado de fase anterior.** Ele estava mecanizado desde a Fase 1,
mas a Fase 3 é a primeira que escreve código consumindo flag por nome — e a
verificação reprovou de verdade, contra código meu, antes de existir commit.

**O que a fase entrega além da DoD**, porque `07` pede nos OUTPUTS: JWT (`06` T2 e
`05` §8), três entidades, e degradação real em **três** endpoints — a DoD nomeia
dois, e `07` exige pelo menos três.

**Critérios de aceitação:** só **T2**, "Fases 1–3". Os quatro bullets passam, e os
três primeiros já passavam desde a Fase 1.

---

## 6. Pendências

| Id | O que é | Vencimento |
|---|---|---|
| P3-1 | ~~O digest de imagem é pinado em dois lugares e nada cruza os dois~~ | ✅ **FECHADA** na peça 4 |
| P3-2 | Cache frio sem single-flight: leituras concorrentes reconstroem N vezes | **Fase 4** — redatada, ver abaixo |
| P3-3 | ~~O RBAC é de papel, e aluno lê aluno: falta a regra de objeto~~ | ✅ **FECHADA** na peça 5 |
| P3-4 | No worktree de auditoria, `range_core` vem da árvore PRINCIPAL e `domains` do worktree | **Antes do próximo checkpoint** — Fase 4 |

#### P3-1 — o digest de imagem é pinado em dois lugares

`docker-compose.yml` e `.github/workflows/invariants.yml` pinam as mesmas duas
imagens por digest, e **nada cruza os dois**.

**Não é hipótese:** ao acrescentar o serviço de Redis ao CI eu escrevi um digest
**inventado**, diferente do que o compose já tinha. Peguei por `grep`, não por
mecanismo — e digest inventado ou não existe, e o job quebra com erro de imagem,
ou existe e aponta para outra coisa.

**O que está em jogo é mais que o erro de digitação:** dois digests diferentes
para o mesmo papel são **dois ambientes**, e o CI deixa de julgar o que o
desenvolvedor roda. É a mesma classe do `check_spec_flags` — duas listas do mesmo
fato, sem ninguém cruzando.

**A forma é conhecida e barata:** uma checagem que extrai `image: <nome>@sha256:`
dos dois arquivos e exige igualdade por nome de imagem, com prova negativa.
Vencimento dentro desta fase.

> **Fechada na peça 4** por `scripts/check_pinned_images.py` — §4.3. Três
> asserções e sete eixos de prova negativa, com o digest divergente em primeiro
> lugar. A terceira asserção não estava prevista aqui e é a que fecha a origem:
> imagem que só o CI conhece reprova, porque digest sem par no compose é
> exatamente o que o meu era.

#### P3-2 — cache frio sem single-flight

Duas leituras concorrentes num cache frio reconstroem **duas vezes**, e cada
reconstrução custa o que a §3.8 da Fase 2 mediu.

**Hoje não é problema, e a data em que passa a ser tem nome:** o engine é
síncrono e de processo único, e a Fase 3 é a primeira a trazer concorrência de
verdade — a API. Enquanto não houver duas leituras simultâneas, não há o que
proteger.

**Por que não construir agora.** Um lock sem concorrência é mecanismo sem
consumidor, e a Fase 2 registrou o custo disso duas vezes. A saída provável é
single-flight na borda que a API introduzir, e **medir antes de escolher** — pela
ordem que a P2-10 fixou e que se mostrou certa.

**Vencimento: Fase 3, junto do FastAPI.**

> **REDATADA PARA A FASE 4, e a premissa do prazo original estava errada.**
>
> Eu datei esta pendência por um *proxy* — "quando o FastAPI chegar" — em vez de
> pela condição que ela descreve: **quando houver duas leituras simultâneas**. O
> proxy chegou e a condição não: a peça 5 lê a projeção a cada request, mas não
> há servidor. `app` é um objeto ASGI, `uvicorn` não é dependência desta fase, e
> a suíte roda `TestClient`, que é sequencial. Concorrência aqui é literalmente
> impossível.
>
> É a mesma forma da P2-6, e é por isso que registro em vez de simplesmente
> mover: **um prazo apoiado em proxy vence sem que a condição ocorra**, e o
> risco é o oposto do que parece — não é atrasar, é *fechar* uma pendência
> porque a data passou.
>
> O gatilho correto tem nome: **o primeiro processo que serve requisições
> concorrentes**, que é o container da Fase 4. E a ordem da P2-10 continua
> valendo: medir antes de escolher o mecanismo.

#### P3-3 — o RBAC é de papel, e a regra de objeto ainda não existe

`GET /alunos/{aluno_id}` admite `aluno`, e **qualquer aluno lê qualquer aluno**.

**Não é buraco de escopo:** o item 3 da DoD é *"RBAC nega acesso cruzado entre
**perfis**"*, que é papel contra papel, e é o que a peça 4 entrega e prova. A
regra de objeto — o aluno vê a si mesmo — é uma **segunda regra**, sobre o `sub`
do token e não sobre o `role`.

**Por que não agora.** A forma declarativa dela precisa de vocabulário novo no
`api_surface.yaml` — algo como um escopo por rota —, e inventá-lo antes de haver
mais de um caso é a classe D6. A peça 5 traz a terceira entidade e as três rotas
degradadas, e é lá que se vê se o escopo é um campo ou três.

**O que já está pago:** comparar `sub` com o parâmetro do caminho não consulta
recurso nenhum, então a regra de objeto **não reabre** a questão de 403 × 404.

**Vencimento: Fase 3, peça 5.**

> **Fechada na peça 5** — §4.4. A resposta é **um campo**, com duas regras
> (`proprio` e `titular`), e ela veio das três entidades: todos os casos são "um
> campo do recurso é igual ao `sub`", e o que muda é qual campo.
>
> O que eu não tinha previsto ao abrir a pendência: a regra `titular` **exige ler
> o recurso**, o que reabriria a questão de 403 × 404 se a negação acontecesse
> depois da busca. Resolvido pondo a regra **dentro** da busca — "não é sua" e
> "não existe" devolvem `None` pelo mesmo caminho —, e a propriedade da peça 4
> continua valendo sem ninguém se lembrar dela.

---

## 6.1 Pendências herdadas

| Id | O que é | Vencimento |
|---|---|---|
| P2-5 | ~~`00` §5.6 enumerava duas das quatro marcas~~ | **FECHADA** — `spec-change` de 16/08 |
| P2-9 | ~~a frase do mecanismo em `01` §4.4~~ | **FECHADA** — mesmo `spec-change` |
| P37 | ~~`docs/process/` fora do `CODE`~~ | **FECHADA** — e era maior que a pendência |
| P2-16 | ~~o auditor lê `main` local, e `main` local envelhece~~ | ✅ **FECHADA** no fechamento desta fase |
| P2-18 | ~~o harness de mutação escreve fora do worktree~~ | ✅ **FECHADA** — a frase do `WORKFLOW.md` corrigida |
| P2-19 | ~~o auditor não executa o que depende de serviço~~ | ✅ **FECHADA** — stack efêmera no lançador |
| P2-6 | ligação declarativa de `participant_action` a flag | **Fase 8** |

### As três do aparato venciam NESTE checkpoint, e estão fechadas

A pergunta que este parágrafo responde é a que a P2-14 tornou obrigatória:
**alguma pendência vence nesta fase e está aberta?** Não. As três diziam *"antes
do próximo checkpoint"*, e o próximo checkpoint é este — então foram feitas
agora, no PR de fechamento, que é o mesmo PR que as pendências previam
(*"as duas são do mesmo aparato e cabem no mesmo PR"*).

**P2-16 — a base de comparação.** O lançador faz `git fetch origin main`, resolve
`origin/main` para um SHA e **passa esse SHA no prompt**, com a instrução de não
resolver `main` por conta própria. A formulação anterior — *"diff contra main"* —
era o próprio defeito: delegava a resolução ao auditor, dentro de um worktree
cujos refs locais podem estar atrás. Saída (a) da pendência, sem desvio.

**P2-18 — a promessa meio verdadeira.** `WORKFLOW.md` dizia que *"qualquer sujeira
incidental de teste morre com o worktree temporário"*. Não morre: `tempfile` fica
fora dele. A contenção real são **duas** afirmações — nada escrito na árvore
sobrevive ao worktree, nada escrito fora dela sobrevive ao processo —, e a
segunda está dita porque é mais fraca. Saída (b), que era a decidida.

**P2-19 — e ela deixou de ser doze pulos.** Saída (a): `docker-compose.audit.yml`
efêmero, sem volume, com portas próprias, subido pelo lançador, migration
aplicada, e as duas variáveis **exportadas** — não passadas na linha de comando,
porque o `readonly_bash` só admite três prefixos inline de propósito.

Medido, não suposto: com a stack no ar, **211 testes, zero pulos**. Sem ela eram
199 rodando e 12 pulando, e entre os doze estavam a persistência, o critério de
reinício de `06` T3 e a detecção de reescrita por cadeia de hash.

**Rodar o lançador achou dois defeitos que ler não acharia:**

| | O que era |
|---|---|
| 1 | sem `-p`, o `docker compose` deriva o nome do projeto do **diretório** — o mesmo do compose de desenvolvimento — e reconcilia os dois arquivos como uma stack só. A primeira execução **recriou o `aurora-redis` de desenvolvimento** e o removeu no `down`. Era o pior caso que as portas separadas tentavam evitar, entrando por outra porta |
| 2 | a porta 56379 caiu numa **faixa de exclusão do Windows**, e o `bind` falhou. As faixas são dinâmicas e vivem perto do intervalo efêmero, então número alto é escolha frágil. 15432 e 16379 |

O volume `aurora_pgdata` sobreviveu aos dois — conferido, não presumido.

#### P3-4 — no worktree de auditoria, o core vem da árvore principal

**Achado ao conferir a allowlist antes deste checkpoint, e medido:**

| Pacote | De onde resolve, com o CWD no worktree |
|---|---|
| `domains` | **worktree** |
| `contracts` | **worktree** |
| `range_core` | **árvore principal** |

A instalação editável grava caminhos **absolutos** para a árvore principal.
`domains` e `contracts` são diretórios reais e o CWD vence no `sys.path`;
`range-core` tem hífen e **não é importável pela árvore** — é justamente o
argumento que o `pyproject.toml` escreve —, então só resta o caminho instalado.

**A consequência é procedência misturada.** Se a árvore principal estiver num
commit diferente do worktree auditado, o auditor executa os testes e o adapter do
commit candidato **contra o núcleo de outro commit** — e o resultado parece
normal. É a forma exata de uma propriedade parecer verificada sem estar.

**Hoje não morde por construção:** o lançador exige árvore limpa e fixa o worktree
em `HEAD`, então os dois coincidem no instante do lançamento. **Morde se eu
commitar na árvore principal enquanto a auditoria roda** — que é exatamente o que
aconteceria numa rodada de correção paralela.

**Não é nova da Fase 3**, mas ficou pior nela: a peça 4 pôs `domains` no
`pyproject.toml`, e o adapter passou a importar o núcleo em todo request.

**Destino:** a forma provável é um teste que afirma que os três pacotes resolvem
sob a raiz da árvore em execução — o que transforma quimera silenciosa em linha
vermelha. Não o escrevi agora **de propósito**: ele reprovaria toda auditoria
feita em worktree, e mudar o critério de reprovação do auditor no PR que ele vai
auditar é decisão do operador, não minha.

**Vencimento: antes do próximo checkpoint — Fase 4.**

### O que confirmei na allowlist, na fonte e não por suposição

Rodei a cópia **instalada** do hook contra 21 comandos, incluindo os oito
verificadores que esta fase criou:

| | Resultado |
|---|---|
| os 4 verificadores da fase + as 4 provas negativas | **liberados** |
| `python -m unittest discover -s tests` | **liberado** |
| `python -m unittest tests.test_api_rbac` e afins | **bloqueados**, e é a forma exata declarada na Fase 2: família admitida deixaria passar `python -m unittest <qualquer coisa>` |
| `AURORA_TEST_REDIS_URL=... python -m unittest ...` | **bloqueado**, e é o desenho: esses testes **escrevem e apagam** a chave, e um hook que aceitasse `VAR=valor` inline deixaria o auditor apontar a suíte para qualquer lugar. É por isso que a P2-19 exporta em vez de passar inline |

**Nada que a Fase 3 criou está fora da allowlist.** Os dois bloqueios são
deliberados, já documentados, e o segundo é o que torna a solução da P2-19
possível sem afrouxar o hook.

---

## 7. O que a fase aprendeu sobre o próprio método

Três, como a Fase 2. As três são sobre **verificação que parece existir**, e é
por isso que elas valem mais que qualquer item de DoD: um item de DoD que falha
avisa, e uma verificação vazia não.

### 7.1 Afirmação sem conferência atravessa camadas, porque cada uma confia na anterior

A P2-6 dizia que o serviço consumidor nascia na Fase 3. Não nascia — é a Fase 11.
Eu escrevi a frase errada num `spec-change` que **foi mergeado**, e a instrução
seguinte veio construída sobre ela. **Três camadas**, cada uma tratando a
anterior como fonte.

E aconteceu de novo dentro desta fase, menor e mais rápido: a D3 do meu próprio
registro afirmava que `05` §8 exigia o segredo de JWT derivado do `RANDOM_SEED`.
Falso, e não inofensivo — derivar a chave de assinatura de um valor versionado
seria **publicá-la**. A frase durou de uma peça à outra porque ninguém a confere:
registro não tem gate.

**O que muda daqui em diante:** afirmação sobre a spec dentro de um registro é
citação, não paráfrase — e quando ela é premissa de uma decisão que ainda não foi
implementada, ela é relida no momento de implementar. Foi assim que esta caiu.

### 7.2 Prazo apoiado em proxy vence sem que a condição ocorra

Datei a P3-2 como *"Fase 3, com o FastAPI"*. O FastAPI chegou; a condição que a
pendência descreve — **duas leituras simultâneas** — não. Não há servidor, e a
suíte é sequencial.

O risco de um prazo por proxy não é atrasar. É **fechar**: a data passa, o proxy
está lá, e a pendência é dada por vencida sem nada ter sido resolvido. É a mesma
forma da P2-6, com o tempo no lugar do fato.

**O que muda:** o vencimento nomeia a **condição**, não o marco que se espera que
a traga. A P3-2 agora diz *"o primeiro processo que serve requisições
concorrentes"*.

### 7.3 Checagem só é exercida quando existe consumidor — e até lá ela parece pronta

A peça 2 recusava papel de exercício **na rota** e deixava passar o mesmo papel em
`papeis_de_dominio`, a lista de onde os papéis vêm. O buraco era invisível porque
**nada lia aquela lista**: sem consumidor, as duas metades da regra pareciam uma.

A peça 4 pôs `emitir_token` a lê-la em tempo de execução, e o buraco virou
caminho: um papel de exercício ali seria token de exercício emitido pelo adapter.

Duas repetições do mesmo padrão nesta fase confirmam que não foi acaso: `/openapi.json`
respondia 200 sem token — a "falha fechada" da peça 4 valia para rota declarada e
não para rota que o framework declara sozinho —, e `check_fold_authority` chamava
`main()` sem `sys.argv`, rodando sempre contra a árvore real.

**O que muda:** ao escrever uma checagem antes do consumidor, escrever também o
probe do **eixo que só existirá depois** — e, quando o consumidor chegar, reler a
checagem em vez de assumir que ela já cobria. Foi isso que a peça 4 fez com a
peça 2, e a peça 5 com a peça 4.

### O contraste que vale registrar

As três lições da Fase 2 eram sobre **ler a fonte**. As três desta são sobre
**verificação vazia** — regra que não é exercida, prazo que não é condição,
afirmação que não é conferida. A diferença é que a fase anterior construía o
mecanismo, e esta começou a depender dele.

---

## 8. Próxima fase

`07` Fase 4 — **VERTICAL SLICE ⏸**. ENTRY: Fase 3 completa.
