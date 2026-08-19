# Processo de trabalho — AURORA CYBER RANGE

## Fase 0 — Specification Freeze

Só documentação normativa, schemas, agentes, hooks, CI e tooling de governança. Nenhuma aplicação.

A ordem é deliberadamente rígida:

```text
bootstrap.sh
    ↓
seis verificadores + testes negativos
    ↓
commit/push
    ↓
CI verde
    ↓
branch protection confirmada
    ↓
spec-v1.0
```

`bootstrap.sh` **não** commita, não faz push e não cria tag. `finalize_phase0.sh` só cria a tag depois que CI e branch protection forem comprovados.

A partir de `spec-v1.0`, a especificação é imutável durante a implementação. Alteração exige branch `spec-change/<slug>` e PR próprio com título `spec-change:`, sem código junto e com aprovação humana.

## Ciclo por fase

```text
git checkout -b fase-<n>-<slug>
git rev-parse HEAD                      # a ÂNCORA: onde a fase começa
# escrever a linha `<n><TAB><sha><TAB><descrição>` em docs/process/phase_anchors.tsv
claude --permission-mode default
# implementar e testar
git add -A
git commit -m "fase-<n>: checkpoint candidate"
bash scripts/start_checkpoint_audit.sh <n>
# corrigir BLOCKER/HIGH, criar novo commit e reauditar
gh pr create --title "fase-<n>: <descrição>"
gh pr merge --rebase                    # REBASE. Nunca --squash. Ver abaixo
```

O auditor não corrige. Ele reporta e emite PASS/FAIL. Qualquer BLOCKER é FAIL.

### A âncora, e por que sem ela a auditoria recusa

`scripts/check_audit_base.py` responde *"a auditoria desta fase ainda é porta?"*, e
a propriedade é: **nada do trabalho da fase pode já estar na branch default**. Isso
exige saber onde a fase começou, e esse ponto **não é derivável do grafo** —
`git merge-base` é exatamente o valor que se corrompe quando parte da fase já foi
mergeada. A âncora é a única entrada que o predicado não infere.

**Âncora ausente recusa a auditoria.** Não há degradação para "ok": não saber onde
a fase começou é o caso em que não se pode afirmar que ela não foi mergeada. Os
dois predicados anteriores degradaram para "ok" quando não sabiam — o primeiro
entregando base vazia, o segundo perguntando só se o candidato estava contido na
base — e cada um custou uma auditoria que parecia gate e não era.

**Rebase move a âncora**, e isso é verdade e não inconveniência: o ponto de
bifurcação muda mesmo. Regrave a linha no mesmo commit do rebase; o verificador
recusa com essa leitura impressa entre as duas possíveis.

### `spec-change` primeiro, fase depois — e a âncora se move junto

`CLAUDE.md` proíbe alterar spec e código no mesmo PR, e o gate `spec_freeze`
reprova quem tentar. O que faltava escrito é **a ordem**, e ela não é óbvia
quando o `spec-change` nasce *durante* a fase — que é o caso normal, porque é
implementando que se descobre que a spec está errada.

Foi o H1 da terceira auditoria da Fase 3: o commit `02383e4`
(`spec-change: quem traz o consumidor da ligacao e a Fase 8`) ficou **dentro** do
intervalo da fase, entre a peça 1 e a peça 2. O diff da fase passou a carregar
`docs/spec/` junto com código, e o `spec_freeze` reprovaria o PR.

**O procedimento, na ordem:**

```text
# 1. o spec-change vira PR PRÓPRIO e é mergeado primeiro
git checkout -b spec-change/<slug> <origin/main>
gh pr create --title "spec-change: <descrição>"
gh pr merge --rebase                    # aprovação humana antes disto

# 2. a branch da fase é rebaseada sobre a main que já contém o spec-change
git checkout fase-<n>-<slug>
git fetch origin main
git rebase origin/main

# 3. a ÂNCORA MUDOU — o ponto de bifurcação é outro. Regrave-a
git merge-base origin/main HEAD          # <- o novo START
# atualize a linha da fase em docs/process/phase_anchors.tsv, no mesmo commit

# 4. só agora o checkpoint
bash scripts/start_checkpoint_audit.sh <n>
```

O passo 3 não é burocracia: sem ele `check_audit_base.py` recusa a auditoria
seguinte com *"a âncora ficou desatualizada"*, que é o comportamento certo — o
rebase moveu o começo da fase de verdade.

**Este furo é um clique do operador, e não condição do repositório** — a mesma
natureza do squash. Por isso mora aqui, no procedimento, e não só na pendência
que o descobriu.

### O prefixo `spec-change:` é lido por DOIS verificadores, e eles não são o mesmo

Custou duas ocorrências para ficar escrito, e a segunda aconteceu **no PR
seguinte ao que a ensinou** — o que já basta para tirar a regra de mensagem de
commit e trazê-la para cá. Ela protege `spec-change`, e `spec-change` acontece
no meio de fase.

**Os dois predicados, sobre a mesma convenção:**

| Quem lê | O que lê | O que acontece se estiver errado |
|---|---|---|
| `spec_freeze` (CI) | o **título do PR** | PR que toca `docs/spec/` sem o prefixo é reprovado |
| `check_readme_atual.py` | os **subjects de `git log spec-v1.0..HEAD`** | o contador do README diverge da árvore e o job `contratos` reprova |

São verificadores diferentes, com entradas diferentes, e **os dois mordem**.
Satisfazer um não diz nada sobre o outro.

**A regra operacional.** O prefixo `spec-change:` pertence a **duas** coisas: ao
commit normativo e ao título do PR. Commit auxiliar dentro do mesmo PR — o que
atualiza o contador do README, o que corrige uma âncora de probe, o que
conserta um typo — usa `docs:` ou `fix:`.

O motivo é aritmético e não estético: um segundo commit com o prefixo entra na
própria conta, e o número que ele acabou de corrigir sobe de novo. Foi
exatamente isso no primeiro dos dois casos.

**A regra de ordem, que é a que faltou no segundo.** Em branch que carregue
mudança normativa, `check_readme_atual.py` roda **depois de todo commit**, antes
do push.

**A propriedade que obriga a ordem, e ela é do verificador e não da lista.** A
entrada dele inclui o próprio commit candidato: lê `git log`, e não a árvore de
trabalho. Rodá-lo antes de commitar devolve verde sobre um estado que não é o
que vai ao CI, e o verde é sincero — o commit ainda não existia.

**Verificador com essa propriedade roda depois do commit.** Hoje
`check_readme_atual.py` é o único caso; qualquer verificador futuro que leia o
log herda esta regra sem precisar que alguém volte aqui para acrescentá-lo.

A redação anterior deste parágrafo dizia *"é o único verificador cuja entrada
inclui o commit candidato"* e *"todos os outros podem ser conferidos com a
árvore suja"* — duas afirmações universais sobre o conjunto de hoje, dentro do
documento que ensina a não inscrever contagem. Enunciar a propriedade, com a
instância datada e o herdeiro declarado, é o que não envelhece.

### Rebase, nunca squash, no merge de branch de fase

**Regra:** o merge de uma branch de fase é `--rebase` (ou fast-forward). **`--squash`
é proibido.**

O motivo é mecânico, e não estético. O predicado da base tem duas metades:
topologia contra a âncora, e conteúdo por identidade de patch. O squash é o único
caminho que escapa das duas ao mesmo tempo — ele reescreve N patches num só, então
os patch-ids individuais deixam de casar; a âncora continua sendo o merge-base
porque a identidade mudou; e se a branch andar depois do squash, o diff não é
vazio. As duas metades passam, e o conteúdo da fase está em `main`.

Isto está declarado em `scripts/check_audit_base.py` como furo conhecido — **furo
declarado vale mais que gate que mente**. E a regra mora aqui, e não só na
pendência que a descobriu, porque **quem clica é o operador, e a pendência não
está aberta na hora do clique**.

Rebase e fast-forward preservam identidade de patch: com eles, o mesmo predicado
que deixa o squash passar pega tudo o mais.

## Por que o auditor formal usa launcher de worktree

O objetivo é garantir simultaneamente:

- contexto fresco;
- filesystem descartável para efeitos colaterais de testes;
- commit auditado imutável durante a revisão;
- comparação reproduzível contra `main`.

O launcher cria um worktree **explicitamente a partir do `HEAD` candidato** e então inicia `claude --agent checkpoint-auditor` nele. Isso evita depender do worktree automático do frontmatter, cujo ponto de partida pode ser a branch default e não a branch candidata.

O agente não recebe ferramentas `Write`/`Edit`. Bash passa por allowlist textual — e o lançador concede `--allowedTools Bash` à sessão do auditor, **de propósito**, para que a allowlist do hook seja de fato quem decide. Essa combinação preserva a **separação de papéis**: o auditor não corrige por acidente porque não tem com que escrever, e não deixa de medir porque não tem quem aprove.

> **A frase anterior descrevia metade do mecanismo, e a metade errada.** Ela dizia apenas *"Bash passa por allowlist textual"*. Passava por allowlist textual **e** pela camada de permissão da sessão — e era a segunda que decidia: `.claude/settings.json` não tem entrada `permissions.allow` para `Bash`, então cada comando exigia aprovação humana. Nas duas primeiras auditorias da Fase 3 isso não apareceu porque o operador estava na janela clicando; na terceira, a sessão rodou sem terminal e **onze tentativas em seis formas de comando foram todas negadas** — nenhuma pelo hook. O auditor emitiu FAIL por não conseguir executar nada, e estava certo.
>
> Um mecanismo cuja propriedade central depende de alguém lembrar de clicar não é mecanismo. A concessão vive no **lançador**, versionada, e não em `settings.json`: ela vale para a sessão do auditor e para mais nada. A restrição inteira continua sendo o `readonly_bash.py` — allowlist por segmento, `DENIED_ANYWHERE` contra o comando cru, alvo resolvido contra o worktree —, com a superfície enumerada em `scripts/phase0_negative_tests.py`. Ela não contém adversário, e isso é declarado, não omitido: o hook decide por casamento textual, não por análise sintática de shell, e sua superfície é enumerada em `scripts/phase0_negative_tests.py` nas duas direções — escrita conhecida e não bloqueada, e leitura legítima bloqueada por engano (`PHASE_0_CHECKLIST.md` §Definition of Done, item 4, condições c e e).

**Bloqueio indevido também é defeito.** Um auditor que não consegue rodar a prova central audita por inferência de leitura de código, e continua emitindo veredito enquanto isso — foi a lição do H4 da primeira auditoria da Fase 0. Por isso o item 4(e) trata falso bloqueio novo como finding, e não como inconveniência.

### `--headless` existe, tem código, e NUNCA rodou — limite declarado

`start_checkpoint_audit.sh` aceita `--headless`, que troca a sessão interativa por
`claude -p`. **O caminho existe, está escrito, e não tem uma única execução
registrada.** Contado em `docs/progress/audit_log.jsonl`, não lembrado: das 71
linhas, **26 são `interactive`**, 3 são `subagent`, 42 são anteriores ao campo —
e **nenhuma é `headless`**.

**Caminho que existe e nunca rodou é atestação esperando acontecer.** Ele *parece*
uma capacidade: alguém lê a flag, lê o `--help` do script, e conclui que a
auditoria roda sem janela. Ninguém viu. É a mesma forma que este projeto já
recusou no DEMO da Fase 1 — roteiro que ninguém executa apodrece igual a
comentário que ninguém lê — e no `pip install -e "$WT[test]"` da Fase 4, que
estava correto em intenção, em aspas e em variável, e o pip recusava.

**Se um dia for preciso, a primeira execução não pode ser numa rodada que decide
fase.** Estrear o modo no checkpoint que fecha uma fase troca duas variáveis ao
mesmo tempo: um FAIL passa a ter duas leituras — a fase, ou o modo — e nenhuma
das duas é separável depois. A primeira execução tem de ser sobre um commit cujo
veredito já se conhece.

**E há uma segunda razão, que é do lado da árvore compartilhada.** Em interativa,
quem implementou entrega o terminal e **para**. Em headless, o processo que pediu
a auditoria **continua vivo enquanto o auditor mede** — e a corrida da
§"Árvore de trabalho compartilhada" volta a existir exatamente na janela em que
ninguém está olhando. O worktree está fixado em `HEAD_SHA` e o venv da P3-4 fecha
a procedência dos pacotes, então o auditor não mediria outro commit; o que se
perde é mais simples e não tem mecanismo: `HEAD` da árvore principal se movendo
sob uma auditoria em curso.

Enquanto isso não for exercido, **a convenção é a de sempre: o operador lança, e
o agente fica parado até o relatório sair.**

### Onde passa a linha da rede: o lançador tem, o auditor não

**A regra:** tudo o que exige rede acontece **antes da sessão**, no lançador, na
máquina do operador. A sessão do auditor roda sem rede, e `curl`, `wget`, `nc`,
`ssh`, `pip install` e `npm install` estão em `DENIED_ANYWHERE` — não por
esquecimento de allowlist, mas porque **preparar o ambiente e emitir o veredito
são papéis diferentes**, e é a mesma separação que faz o auditor não ter `Write`.

A linha já tinha sido traçada uma vez, e a decisão está registrada: a P2-19
considerou dar ao auditor o `gh` para ele consultar o CI, e **recusou** — poria
rede na allowlist do julgador, superfície permanente para resolver um problema
de uma vez. A saída foi o lançador subir a stack efêmera.

**O que o lançador faz com rede, hoje:**

| | Por quê |
|---|---|
| `git fetch origin main` | a base de comparação é `origin/main` atualizado, e não `main` local — P2-16 |
| `docker compose up` da stack efêmera | sem ela, doze testes pulam e o pulo é lido como verde — P2-19 |
| `pip install -e <worktree>` num venv próprio | sem ele, `range_core` resolve pela árvore principal — P3-4, abaixo |
| **as provas de container do commit auditado** | o DEMO ponta a ponta e o reinício de container exigem Docker, e o auditor não o tem — P4-10, abaixo |
| **a medição do seed completo do commit auditado** | ela escreve 3,5 milhões de linhas duas vezes e leva minutos, e medi-la *antes* do commit invalida a própria prova — Fase 5 §11, abaixo |

**O critério de severidade é um só, e ele decide as quatro:** *falha ALTO o que
faria o veredito **falar de outra coisa**; falha BAIXO o que faria o veredito
**dizer menos**.* A primeira é um veredito errado com cara de certo; a segunda é
um veredito incompleto que se declara incompleto.

Contadas no código, e não lembradas — **uma** aborta e **quatro** seguem:

| Etapa | Falha | Consequência declarada |
|---|---|---|
| `pip install -e <worktree>` | **ALTO** — `exit 1` | sem o venv, os testes rodam contra o núcleo da árvore principal: o veredito seria **sobre outro commit** |
| `git fetch origin main` | segue, com aviso | a base pode estar desatualizada; o SHA dela vai no prompt e o auditor sabe contra o que compara |
| `docker compose up` da stack efêmera | segue, `SERVICOS=AUSENTES` | os testes de serviço **pulam**, e o prompt diz isso ao auditor para que o pulo não seja lido como verde |
| as provas de container | segue, com aviso | os itens 1 e 4 da Fase 4 voltam a **NÃO VERIFICADO** |
| a medição do seed completo | segue, com aviso e log | os itens 1 e 2 da Fase 5 caem para o que houver de transportado, e o verificador recusa se o SHA divergir |

> **A frase que estava aqui dizia *"falha de rede no lançador falha ALTO — nenhum
> dos três degrada para 'segue sem'"*, e ela era falsa quando escrita.** A stack
> efêmera degrada para `AUSENTES` desde a própria P2-19 que a criou, e o `git
> fetch` sempre avisou e seguiu. A frase descrevia o caso da P3-4 e generalizava
> para os outros dois sem contá-los — e a versão seguinte, ao acrescentar a
> quarta linha, propagou o erro como *"três dos quatro"*.
>
> É a §1.6 e o L1 da terceira auditoria da Fase 3 na mesma linha: **número
> afirmado diz de que conjunto é, e é contado na fonte dele no momento em que se
> escreve.** O que estava certo o tempo todo era o critério; o que faltava era
> tê-lo aplicado às quatro etapas em vez de a uma.

### Falha que degrada precisa dizer POR QUÊ — e as três degradam

**Degradar é decisão; degradar em silêncio é defeito.** As três linhas que seguem
acima entregam ao auditor um veredito que diz menos — e ele só é honesto se o
operador puder saber *por quê* a rodada mediu menos.

Foi a rodada de **17/08/2026**: a stack subiu, `alembic upgrade head` falhou, e
**73 dos 335 testes pularam** — 22% da suíte, na rodada que decidia a Fase 4. As
duas etapas mandavam a saída para `/dev/null`, e o ramo de falha chamava
`derruba_stack` logo depois: **a causa morria duas vezes**, no descarte e na
remoção dos containers que a explicariam. Sobrou a frase *"migration falhou"*.

**E ela não foi reproduzível com o que sobrou** — a stack foi subida e a migration
rodada duas vezes depois, das duas árvores, `rc=0` nas duas. É esse fato que
justifica o mecanismo em vez de precaução: sem a saída daquele momento não há como
distinguir corrida de porta, bind transitório e defeito de verdade, e **cada
hipótese custa uma rodada de auditoria inteira**.

É a mesma lição que a peça 7 da Fase 4 já aprendeu no CI — *"falha de container
sem log é falha que só se diagnostica por adivinhação"* —, com o preço maior: lá
custava um job vermelho que se reroda; aqui custa uma rodada degradada que **ainda
assim emite veredito**.

`diagnostica_stack` grava em `.aurora-worktrees/stack.log`, fora do worktree pelo
mesmo motivo do `pip.log`, e tem duas propriedades que não são a mesma:

1. **imprime ANTES de `derruba_stack`** — invertida a ordem, `ps` e `logs` medem
   containers que já não existem, e a causa morre pelo caminho que o mecanismo
   existe para fechar;
2. **aparece quando o lançador SEGUE**, e não só quando aborta — as três etapas
   que degradam seguem por desenho, então esse é o único caminho em que ela
   aparece.

**A primeira execução do bloco corrigiu a própria correção:** medido, o arquivo
tinha 205 linhas com a causa na 133, e o `tail` na tela mostrava boot de Postgres.
Diagnóstico que existe e não chega a quem lê é a mesma perda com mais passos. A
causa passou a ir para a tela **antes** de `ps` e `logs` serem anexados.

### As provas de container, e por que elas não são atestação — P4-10

Itens 1 e 4 da DoD da Fase 4 — o DEMO ponta a ponta e o reinício do **container**
do engine. Os dois exigem Docker e uma stack no ar, e `docker` está fora da
allowlist pelo argumento desta mesma seção. Na primeira auditoria daquela fase os
dois chegaram ao veredito como NÃO VERIFICADO.

O lançador sobe a stack **a partir do worktree auditado**, roda as duas provas e
grava a saída íntegra num arquivo. O auditor **lê** — e é aqui que a coisa
deixaria de valer, se parasse aqui.

**O que a separa de atestação é o SHA.** O arquivo carrega o commit, e
`scripts/check_provas_de_container.py` — que está na allowlist —, **reprova** se
ele não for o do checkout que se julga. E **reprova também quando o arquivo não
existe**: não há degradação para "ok por não saber", que é o erro que os dois
predicados de base aposentados cometeram.

**A condição é forte por mecânica, e não por confiança: um commit não pode conter
o próprio SHA.** A forma óbvia de forjar — versionar o arquivo junto com o
código — não tem como carregar o hash do commit que a contém.

**O que continua verdade, e está impresso na saída do próprio verificador:** o
auditor não viu rodar. A procedência é melhor que a de uma frase de registro — há
SHA, há saída íntegra, e o texto é o dos próprios scripts —, e continua sendo
leitura.

**Quem grava fica FORA da allowlist**, e a exclusão é a mesma separação de papéis
que faz o auditor não ter `Write`: `grava_provas_de_container.py` constrói
imagem, sobe container e derruba stack. Admiti-lo poria rede **e** execução de
container na mão do julgador, que é o que a P2-19 recusou. A exclusão é provada
em `scripts/phase0_negative_tests.py`, e não apenas escrita no comentário da
allowlist.

**Para quem vier depois:** precisar de rede não é argumento para acrescentá-la à
allowlist do auditor. É argumento para fazer a coisa no lançador, antes da
sessão, e entregar o resultado pronto — como as linhas acima.

### A medição do seed, e por que ela é a única que acontece DEPOIS do commit

Itens 1 e 2 da DoD da Fase 5 — o seed completo em menos de cinco minutos, e o
dataset byte-idêntico com o mesmo `RANDOM_SEED`. A forma é a da P4-10, e a
diferença é o **momento**, que aqui não é detalhe:

> a prova carrega o SHA do checkout, e o verificador reprova quando ele diverge.
> Medir → registrar o número → commitar **invalida a própria medição**.

A saída procedimental existe e é óbvia — *medir por último, com o código
congelado, e não commitar nada depois*. Ela foi escrita no registro da Fase 5 e
**a volta seguinte caiu no laço de novo**, escrita por quem tinha acabado de
descrevê-lo. É a mesma distinção entre regra e propriedade que já motivou
mecanizar o guarda de branch e o sentinela: instrução é regra; lançador é
impedimento.

Por isso o lançador **mede**, depois do `git worktree add` e contra o worktree. O
que a distingue das provas de container, e o motivo de cada coisa:

| | |
|---|---|
| **banco descartável próprio** | o script **TRUNCA vinte tabelas duas vezes**. Apontá-lo para o banco da stack efêmera destruiria, na mesma sessão, aquele em que a suíte do auditor vai rodar. Ele nasce e morre no mesmo servidor efêmero, que não tem volume |
| **recriado a cada rodada** | mesmo motivo do venv: banco reaproveitado carrega o esquema do commit anterior |
| **`CREATEROLE`** | a migration `0004` cria a role da aplicação, e a `POSTGRES_USER` da imagem é superusuária do cluster. A role é objeto de cluster: se o outro banco já a criou, esta execução só faz o `GRANT` |
| **`RANDOM_SEED` fixo no lançador** | seed que mudasse por rodada tornaria a medição incomparável com a anterior — o mesmo argumento do `SEED` do gravador de container. Não é credencial |

**O transporte continua existindo, e é o caminho degradado.** O lançador copia
`.aurora-prova-do-seed.json` da árvore principal **antes** de medir, e a medição
o sobrescreve quando acontece. Sem Docker, o que sobra é a medição de quem mediu
fora — e quem a aceita ou recusa é o verificador, pelo SHA. Invertida a ordem, a
cópia velha sobrescreveria a medição recém-feita, que é o defeito entrando pela
porta do fallback.

**O briefing distingue os dois casos**, e não deixa o auditor deduzir: `MEDIDA
PELO LANCADOR` é vínculo estrutural; `TRANSPORTADA` avisa que divergência de SHA
é o caso normal daquela rodada, e não anomalia.

### O venv da auditoria, e o que ele fecha — P3-4

Medido no worktree da Fase 3, com o CWD dentro dele: `domains` e `contracts`
resolviam pelo worktree, e **`range_core` resolvia pela árvore principal**. A
instalação editável grava caminho absoluto, e `range-core/` tem hífen — não é
importável pela árvore, então não há CWD que corrija. O auditor executava o
adapter e os testes do commit candidato **contra o núcleo de outro commit**.

Até a Fase 3 isso não mordia por construção: a auditoria rodava depois do merge,
e os dois lados coincidiam. **A Fase 4 é a primeira auditada antes do merge** —
os dois SHAs são diferentes de verdade.

São duas metades, e nenhuma serve sozinha:

- `tests/test_procedencia_dos_pacotes.py` afirma que todo módulo importado dos
  três pacotes veio da árvore em execução — é a que fica **vermelha**;
- o venv em `.aurora-worktrees/venv`, criado pelo lançador com a árvore auditada
  instalada, é a que a faz **passar**.

O venv fica **fora** do worktree, porque o worktree é o objeto da auditoria e um
diretório de dependências dentro dele apareceria em toda listagem que o auditor
fizesse. E é **recriado a cada rodada**: venv reaproveitado carrega as
dependências do commit anterior, que é a mesma classe de defeito entrando pela
porta das dependências em vez da do código.

A integridade do repositório repousa em branch protection com `enforce_admins`, no job `spec_freeze` e nos seis verificadores — nenhum deles alcançável pelo hook do auditor. Qualquer sujeira incidental de teste **dentro da árvore** morre com o worktree temporário.

> **A exceção, declarada — P2-18.** A frase acima prometia contenção total, e a promessa era meio verdadeira. `tests/mutation_harness.py` e os `*_probes.py` escrevem a fonte mutada em `tempfile.TemporaryDirectory()`, que fica **fora do worktree**: o diretório é autolimpante e o alvo não é escolhido por quem roda, mas ele não morre com o worktree — morre com o processo.
>
> Não é escrita deliberada do auditor, e o hook não a intercepta: acontece dentro de um `python -m unittest` já autorizado. **`tempfile` é o mecanismo certo** — plantar mutação dentro da árvore auditada a deixaria suja durante a execução, que é pior —, e o que estava errado era a frase.
>
> **Contenção real, então, são duas afirmações e não uma:** nada escrito *na árvore* sobrevive ao worktree, e nada escrito *fora dela* sobrevive ao processo. A segunda é mais fraca, e está dita porque é mais fraca.
>
> **A stack efêmera da auditoria é da mesma família.** Desde o fechamento da P2-19, o lançador sobe Postgres e Redis descartáveis e exporta `AURORA_TEST_DATABASE_URL`/`AURORA_TEST_REDIS_URL` — os testes **escrevem** neles. Portas próprias, sem volume, e `docker compose down` ao final: é escrita real, fora do repositório, com tempo de vida da auditoria. Apontar para o compose do projeto truncaria o banco de desenvolvimento.

## Scenario designer

O `scenario-designer` possui uma competência diferente da engenharia de aplicação e pode editar apenas `scenarios/`.

A restrição é técnica, não apenas textual:

- `scenario_scope.py`: bloqueia Write/Edit fora de `scenarios/`;
- `scenario_bash.py`: permite apenas `range-cli scenario validate|lint|dryrun`, `git diff -- scenarios/...` e `git status --short`.

`ground_truth.yaml` e `GM_NOTES.md` **não são versionados**. `scenarios/` está fora do Git desde a peça 5 da Fase 5 — este repositório é público, e os dois são o gabarito. O que fica versionado é o **gerador**, a **query de referência** e o **template de prosa**; os artefatos nascem de `RANDOM_SEED` na máquina de quem tem o `.env`. Eles nunca chegam a imagem, API, bundle ou export de participante, e `scripts/check_gabarito_fora_do_git.py` reprova o PR que os versionar.

## Paralelismo — não antes da Fase 8

Fases 1 a 7 são estritamente sequenciais: contratos → engine → API → vertical slice → objetivos → pacote. Worktree paralelo nessa etapa tende a fragmentar justamente os contratos que precisam permanecer coerentes.

A partir da Fase 8, três frentes podem ser separadas:

| Worktree | Escopo |
|---|---|
| `wt-web` | academus-web completo e dashboards por persona |
| `wt-evidence` | projeção de fatos e telemetry-forwarder |
| `wt-external` | federated-identity, mec-gateway, stub prontus |

Cada frente deve tocar diretórios claramente definidos e reconvergir antes da Fase 10.

## Por que o auditor não mora no repositório

Duas razões, e a segunda importa mais:

1. **Mecânica.** Hooks de frontmatter de subagente de *projeto* só rodam depois que você aceita o diálogo de confiança da pasta que contém o arquivo do agente. O worktree de auditoria é outra pasta; sem essa aceitação o Claude Code pula os hooks silenciosamente e registra apenas no debug log. O `readonly_bash.py` simplesmente não rodaria.

2. **Integridade.** Um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit. Definição em `~/.claude/agents/` fica fora do alcance do código sob revisão.

O `scenario-designer` e o `spec-guardian` continuam no projeto, porque escrevem ou leem dentro dele e são versionados junto com as regras que aplicam.

## Revisão adversarial de segunda camada

O `checkpoint-auditor` oferece o ganho principal: contexto fresco, spec + diff + saída real de teste, sem raciocínio da implementação.

Um segundo fornecedor/modelo pode ser usado nos checkpoints ⏸ para reduzir viés específico de modelo, mas é camada adicional. Não substitui o auditor nem o CI.

## Ordem de defesa

1. **Hook** — feedback em segundos dentro da sessão; pega violações óbvias.
2. **CI** — gate real por AST/contrato; pega violações feitas dentro ou fora do Claude Code.
3. **Auditor** — verifica se o teste realmente prova o requisito, se a semântica da implementação corresponde à spec, **e executa a suíte**.

Nenhuma camada substitui outra.

### O terceiro papel do auditor é execução, e ele não é redundância do CI

As três não são intensidades da mesma coisa: **o hook impede, o CI mede o que foi declarado, e o auditor é a única camada onde o teste roda sem que ninguém tenha interesse no resultado.**

Verde de CI é evidência real, e é evidência produzida pelo pipeline de quem implementou — mesmo runner, mesma configuração, mesma suíte que o autor escolheu declarar. Na auditoria os mesmos testes são exercitados por **quem não os escreveu**, num ambiente que quem implementou não configurou. É por isso que a linha 3 diz "e executa a suíte" e não só "verifica".

### Rodada de checkpoint degradada não fecha fase

**Regra:** se a rodada de auditoria rodou com testes pulados, ela não é a rodada que fecha a fase. Corrija a causa do pulo, gere novo commit candidato e reaudite.

O custo da rodada extra **não entra na conta**. Ele é o que a Fase 4 pagou para poder fechar: a rodada degradada mediu 22% menos — 73 dos 335 testes pularam —, o risco material era baixo e estava medido (os mesmos 73 rodaram verdes no CI, sobre o mesmo SHA), e a rodada foi refeita assim mesmo. O motivo não era o risco: é que este projeto passou três fases recusando *"provavelmente está certo"* como fecho, e fechar a fase mais importante com a degradação declarada no relatório, **tendo a correção ao alcance**, seria a exceção que o resto do método não admitiu.

Isso estava em `docs/progress/fase_4.md` §8.5, que é registro **descritivo** — diz o que aconteceu, não o que deve acontecer. Lição registrada não constrange a fase seguinte: a Fase 4 seguiu a regra porque alguém se lembrou dela, e **detecção por memória não é detecção** é o diagnóstico que já motivou mecanizar coisa duas vezes neste repositório. Aqui ela é regra.

**O que ela não é:** não é gate — nenhum mecanismo lê o relatório e conta pulos. É regra de processo, e a distinção entre regra e impedimento é a da §1.6 do registro da Fase 1. O que a torna mais forte que a lição é o lugar: `WORKFLOW.md` é lido antes do checkpoint; o registro de uma fase encerrada, não.

## Auto Mode e secrets

O usuário pode ter Auto Mode configurado globalmente. Este projeto define `permissions.defaultMode = default` e `disableAutoMode = disable` em `.claude/settings.json`.

Também existem deny rules para `.env`, variantes locais e `secrets/`. `.env.example` continua disponível e deve conter apenas placeholders.

## GitHub / branch protection

`spec_freeze` roda apenas em `pull_request`. Isso é intencional: no primeiro push não existe `pull_request.base.sha`, nem título de PR.

A branch protection exige **quatro** contexts:

| Context | O que guarda | Dependência |
|---|---|---|
| `arquitetura` | os quatro invariantes arquiteturais, mais o teste negativo que prova que os seis verificadores reprovam | nenhuma — stdlib |
| `spec_freeze` | spec e código não mudam no mesmo PR; alteração em `docs/spec/` exige título `spec-change:` | nenhuma — `git` |
| `seguranca` | restrições funcionais de `05_SECURITY_REQUIREMENTS.md` e faixas de dado sintético | nenhuma — stdlib |
| `contratos` | os exemplos dos seis contratos, e o teste negativo que prova que o executor reprova | instala do `pyproject.toml` |

Eram três até a Fase 1. `contratos` é **job separado** porque é o único que instala dependência: os outros três rodam sem `pip install`, e um gate que depende da aplicação que ele julga deixa de ser gate.

**Job separado e context obrigatório são coisas independentes.** Acrescentar `contratos` à lista de required status checks não faz `arquitetura` instalar nada — o isolamento continua intacto. Confundir as duas coisas custaria um gate que roda, reporta e **não bloqueia merge**: um PR com fixture quebrada passaria com o job vermelho.

**Ordem de aplicação.** Um status check só pode ser exigido depois de ter aparecido em pelo menos um run. Logo, `contratos` entra na branch protection **depois do merge do PR que o cria**, não antes.

Se a API de branch protection não estiver disponível para o plano/permissão do repositório, a fase não deve ser declarada concluída até a proteção equivalente ser configurada e comprovada.

## Windows

Os hooks são Python para funcionar em Git Bash e PowerShell, desde que `python` esteja no PATH. Os scripts `.sh` devem ser executados em Git Bash.

Depois do primeiro commit e novamente após qualquer alteração em `.claude/`, rode `/doctor`.

---

## Árvore de trabalho compartilhada

Operador e agente trabalham no **mesmo clone**, e `HEAD` é estado global. Um `gh pr merge --delete-branch` apaga a branch local e troca `HEAD`; um `checkout` ou `pull` reescreve arquivos sob uma leitura em curso. Nenhum dos dois é erro isolado — é corrida.

**Aconteceu duas vezes em 15/08/2026:** um commit do agente foi parar em `main` local porque `HEAD` se moveu durante a operação, e um arquivo apareceu modificado e voltou ao normal segundos depois. **E uma terceira em 16/08/2026** — a árvore em `main` no início de um turno, mostrando o conteúdo da fase anterior. Foi ela que motivou o sentinela abaixo.

### O guarda de branch

`user-scope/hooks/pre-commit` recusa commit direto na branch default. `bootstrap.sh` o instala em `.git/hooks/`, e o harness prova as três direções: bloqueia na default, libera em branch de trabalho, e **é contornado por `--no-verify`**.

**É guarda local, não gate.** Protege este clone, não o repositório: quem clonar sem rodar o `bootstrap.sh` não o tem, e o bypass existe por desenho — hook de cliente é contornável, e isso não é defeito a corrigir. A proteção real de `main` continua sendo a branch protection, com os quatro required status checks e `enforce_admins`.

**O que motivou mecanizar não foi o erro, foi a detecção.** `CLAUDE.md` já instruía a criar branch antes de commitar na default; a instrução existia e não segurou. E o caso só apareceu porque alguém leu `[main d9ec0de]` na saída do `git commit` — detecção por sorte não é detecção. É a mesma distinção entre regra e propriedade que a §1.6 do registro da Fase 1 estabelece: instrução é regra; hook é impedimento.

### O sentinela de branch — a escrita, e não o commit

**Aconteceu uma terceira vez em 16/08/2026**, entre duas peças da Fase 4: a
árvore estava em `main` e mostrava o conteúdo da Fase 3. As três ocorrências
foram pegas por alguém lembrar de conferir, e **detecção por memória não é
detecção** — é a mesma distinção entre regra e propriedade que já motivou
mecanizar o guarda de branch uma vez.

`user-scope/hooks/sentinela_de_branch.py` é o `pre-commit` **adiantado até a
primeira escrita**. Entre a leitura e o commit havia uma janela inteira sem nada;
nesse ponto o erro custa **um arquivo**, e não a sessão.

| Perna | Quando | O que faz |
|---|---|---|
| 1 | `SessionStart` | grava o sentinela: sessão, branch e sha |
| 2 | `PreToolUse` de escrita, `HEAD` na branch **default** | **recusa**, e não há re-ancoragem |
| 3 | `PreToolUse` de escrita, branch **diferente** do sentinela | **recusa**, nomeando as duas |

**A perna 2 é a que decide, e ela não é a perna 3.** Na terceira ocorrência a
árvore *já estava* em `main` quando a sessão começou: um sentinela que só
comparasse "mudou desde o início" teria gravado `main` como âncora e ficado
calado. A perna 2 não compara com nada — ela afirma que trabalho não nasce na
default.

**A re-ancoragem é explícita e exige o nome digitado** —
`python scripts/reancorar_sessao.py <branch>` —, e a mensagem de recusa **não**
traz o comando pronto para colar. Uma saída de um clique vira o "sim" que se
aprende a dar, que é o mesmo argumento pelo qual `api_surface.yaml` proíbe
`confirmacao` em rota que tem volta. O script recusa nome que não bate com `HEAD`
e recusa a branch default.

**Mudança de sha na mesma branch não bloqueia.** Commit do operador é normal, e
`pull` sob leitura já tem cobertura: o harness do Claude Code recusa `Edit` de
arquivo alterado em disco desde o `Read`.

**Ele mora em `~/.claude/hooks/`, fora da árvore, e o motivo é a variante direta
do que tira o auditor daqui:** um guarda que mora na árvore que ele guarda
desaparece com ela — um `checkout` para um commit anterior levaria junto o hook e
a configuração dele, exatamente na situação para a qual ele existe. O custo é que
hook de escopo de usuário vale para toda a máquina, e por isso ele se auto-escopa
por `docs/spec/00_MASTER_SPEC.md` e sai calado fora deste projeto.

**Guarda local, não gate**, com o mesmo estatuto do `pre-commit`: escrita por
fora do harness não passa por ele, e a proteção real de `main` continua sendo a
branch protection. As dez direções — as três pernas e os limites declarados —
estão em `scripts/phase0_negative_tests.py`.

### A convenção de anúncio

**Nenhum dos dois hooks previne a corrida.** O `pre-commit` olha para onde o
commit vai cair; o sentinela detecta antes de a escrita virar durável, e manda
reler — mas a leitura que já aconteceu continua velha, e **isso** nenhum
mecanismo alcança. O lado do operador, que edita fora do harness, também não.
Então a parte de baixo continua sendo convenção:

- **O agente anuncia antes de commitar** quando o operador pode estar operando a árvore.
- **O operador avisa antes de `merge`, `checkout`, `pull` ou `switch`** enquanto o agente trabalha.
- **Na dúvida, verificar `git branch --show-current` e `git status` antes de agir** — os dois são baratos e não mutam nada.

Um worktree separado eliminaria a condição, e foi **descartado**: o `start_checkpoint_audit.sh` fixa um caminho em `.aurora-worktrees/` e a confiança de workspace do Claude Code é por caminho. Um segundo worktree permanente exigiria reescrever o fluxo de auditoria que a Fase 0 fixou em dezenove rodadas, e a corrida é rara o suficiente para conviver.
