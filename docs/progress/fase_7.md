# Fase 7 — Pack completo, branching e `range-cli`

**Status: NÃO INICIADA** — nenhuma peça, nenhum commit, nenhuma auditoria. A
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

## 6. Pendências

Prefixo `P7-` para as que nascerem aqui. A tabela abaixo começa com o que foi
**herdado**, e o prefixo herdado é preservado de propósito: renumerar apagaria a
cadeia que liga a pendência ao registro em que ela nasceu.

| Id | O que é | Vence em |
|---|---|---|
| P5-2 | a trilha do Academus declara a categoria "declarações do exercício" e ela não tem produtor | **condição** — a primeira ação de participante que altere estado de domínio; ver abaixo |
| P6-11 | payload cru alimenta o Brier: `confidence: 900` produz escore 64,0 | **VENCIDA E RESOLVIDA** — decisão do operador: recusa alta no computador; ver abaixo |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | **decisão** — nasceu da P6-11, e é a defesa que vem antes dela; ver abaixo |

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
