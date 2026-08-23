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
