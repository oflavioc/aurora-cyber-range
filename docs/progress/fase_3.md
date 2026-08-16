# Fase 3 — API mínima

**Status: EM CURSO.** Aberta em 16/08/2026, com a Fase 2 concluída — nove de nove
itens e auditoria PASS.

**Peça 1 entregue:** a checagem que cruza flag citada na spec com flag declarada
no adapter, e a flag que ela encontrou faltando.

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
**não entra**. `AURORA_JWT_SECRET` já existe no `.env.example`, e `05` §8 exige
que segredo e senha de seed venham do `RANDOM_SEED` — que a Fase 2 já lê por
código do núcleo.

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

## 5. Ordem das peças

| | Peça | Estado |
|---|---|---|
| 1 | checagem de flags citadas na spec + `grades_readonly` no adapter | ✅ |
| 2 | superfície da API declarada + a checagem que a fixa (D5) | ✅ |
| 3 | leitura de flag pela API (D1) — a porta, com o duplo, antes do FastAPI | |
| 4 | JWT + RBAC (D2, D3), com os dois conjuntos de papéis separados | |
| 5 | as três entidades e a degradação declarativa (D4) — itens 1 e 2 da DoD | |

**A peça 1 é a única que paga antes de existir código dependendo dela**, e foi por
isso que veio primeiro: ela achou um item de DoD insatisfazível **antes** de
alguém tentar implementá-lo.

---

## 6. Pendências herdadas

Esta fase **ainda não abriu pendência própria**. Quando abrir, esta seção passa a
se chamar `## Pendências`, com tabela — que é o que `check_progress_consistency.py`
cruza contra as seções de detalhe.

| Id | O que é | Vencimento |
|---|---|---|
| P2-5 | ~~`00` §5.6 enumerava duas das quatro marcas~~ | **FECHADA** — `spec-change` de 16/08 |
| P2-9 | ~~a frase do mecanismo em `01` §4.4~~ | **FECHADA** — mesmo `spec-change` |
| P37 | ~~`docs/process/` fora do `CODE`~~ | **FECHADA** — e era maior que a pendência |
| P2-6 | ligação declarativa de `participant_action` a flag | **Fase 8** |
| P2-16, P2-18, P2-19 | aparato de auditoria | antes do próximo checkpoint |

---

## 7. Próxima fase

`07` Fase 4 — **VERTICAL SLICE ⏸**. ENTRY: Fase 3 completa.
