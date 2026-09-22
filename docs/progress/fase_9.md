# Fase 9 — Evidência e telemetria

**Status: ABERTA** — branch `claude/fase-9-evidence-telemetry-c49cf4`, âncora
`c77120c` (a `origin/main` pós-fechamento da Fase 8). A linha de status existe
porque `check_readme_atual.py` decide *"a fase fechou?"* por ela; ela só muda
com o veredito do `checkpoint-auditor`.

**Por que este registro nasce antes da fase.** Vinte e seis pendências
não-fechadas migram para cá, e pendência sem lugar é pendência que ninguém
encontra. `check_progress_consistency` cobra que toda pendência não-fechada da
fase N apareça na tabela-resumo da fase N+1 — e cobra seção de detalhe para cada
linha. Este arquivo é esse destino, e nasce com a pauta inteira herdada antes da
primeira linha de implementação. É a mesma razão pela qual o `fase_8.md` nasceu
antes da Fase 8.

## 1. Plano da fase

A Fase 9 é **evidência e telemetria** — `07_IMPLEMENTATION_PHASES.md` §"Fase 9".
O que a define é o princípio de `00_MASTER_SPEC.md` §5.3 e `08` §1: **uma
realidade, múltiplas projeções**. Não há gerador por fonte; há um fato canônico
em `ground_truth.yaml` e projeções determinísticas dele. É isso que torna
contradição entre fontes *estruturalmente impossível*, em vez de apenas
improvável — e é por isso que o evidence-simulator e o telemetry-forwarder
ficam sob **um contrato só** (`08` §2).

Os sete itens de DoD:

| # | Item de DoD | Fonte |
|---|---|---|
| 1 | Toda fonte é projeção de `fact_id`; nenhum gerador inventa entidade | `07` §Fase 9; `08` §2 |
| 2 | `range-cli evidence verify` valida consistência fato → projeções, dirigido por fato | `07` §Fase 9; `06` T13 |
| 3 | `precursor_events.jsonl` é reproduzível a partir do ground truth; edição manual detectada por hash | `07` §Fase 9; `08` §2; `06` T13 |
| 4 | Telemetria CEF é projeção, não emissão independente | `07` §Fase 9; `08` §2 |
| 5 | Nenhum arquivo contém anexo, binário, IOC real ou domínio roteável | `07` §Fase 9; `05` §2 e §3; `06` T13 |
| 6 | Replay respeita o clock de exercício | `07` §Fase 9 |
| 7 | A reconstrução da projeção **continua em < 3 s** com `telemetry_emitted` no volume de um exercício de 4 h | `07` §Fase 9; `06` T13 |

Os critérios de `06` T13 acrescentam duas exigências que não têm item próprio na
DoD e que são cobradas do mesmo trabalho: **fato sem `projections` não aparece em
nenhuma fonte** (o limite de detecção deliberado de `08` §2) e **banner de
ambiente simulado na primeira linha de cada arquivo** (`05` §4).

**ENTRY** — Fase 8 selada e mergeada em `origin/main` (`c77120c`). O contrato do
manifesto já existe e está completo: `contracts/evidence.schema.yaml` valida o
`MANIFEST.json` de `08` §7, com exemplo positivo e nove negativos, e declara em
comentário que *"quem consome, hoje: o evidence-simulator da Fase 9, que ainda
não existe"*. Esta fase é quem o exercita pela primeira vez — é a **P1-3**.

**A leitura disciplinada da spec desta fase** (CLAUDE.md §"Disciplina de
leitura"), feita na abertura: `00_MASTER_SPEC.md`, `09_EVENT_MODEL.md`,
`07` §Fase 9, `06` T13, `08_EVIDENCE_SIMULATOR.md` (o documento da fase, por
`00` §7) e `05_SECURITY_REQUIREMENTS.md` — a fase toca evidências, dados e
telemetria, então `05` §2 (evidências sintéticas), §3 (dados), §4 (banner) e
§5.1 (vendor/product fictício) são centrais e não admitem flexibilização.

## 2. A abertura, e o que ela carrega

### 2.1 O ambiente: o venv por worktree — não é defeito de árvore

A primeira execução da suíte nesta sessão deu **680 testes, 64 falhas e 61
erros**, sendo 65 do `tests/test_procedencia_dos_pacotes.py`. **Não era defeito
da árvore.** A instalação editável de PEP 660 é global e aponta para o checkout
principal; o finder vive em `sys.meta_path` e vence o `sys.path`, então
`range_core` (diretório com hífen, não importável pela árvore) resolvia pela
**árvore principal** enquanto `domains` e `contracts` resolviam pelo worktree —
dois commits no mesmo processo.

É exatamente a **P3-4**, e a metade que faz a prova passar já estava escrita em
`docs/process/WORKFLOW.md` §"O venv da auditoria": um venv próprio com a árvore
instalada. Criado em `.venv/` (já coberto pelo `.gitignore`), com
`pip install -e ".[test]" -c constraints.txt`, a suíte passa a **949 testes, OK,
163 pulos** — o número exato que o README declara para execução sem Postgres.

Fica registrado porque a R2 §3 é justamente isto: suíte vermelha exige
diagnóstico de **causa** antes de conclusão, e ambiente vem antes de código.

### 2.2 Três pendências que escaparam do mecanismo de migração

`check_progress_consistency` cobra a migração de pendência apenas entre fases
cuja tabela-resumo declara **coluna de estado** — as tabelas das fases 0 a 5 têm
três colunas, são anteriores ao vocabulário fechado da Fase 7, e o verificador as
**pula**, dizendo-o em voz alta. A consequência é que gatilho escrito lá não
chega a destino nenhum por máquina.

Três pendências com vencimento **explicitamente nesta fase** estavam nessa
situação e **não constavam da tabela-resumo da §6 da Fase 8**:

- **P1-3** — `evidence.schema.yaml` valida artefato ainda não produzido
  (`fase_1.md` §7.3: *"Fase 9"*);
- **P1-13** — duas cópias das faixas sintéticas, contrato × verificador
  (`fase_1.md`: *"unificar as duas fontes fica para a Fase 9, que é quem
  constrói o gerador"*; o próprio `contracts/evidence.schema.yaml:197` a nomeia);
- **P2-11** — `append` abre uma conexão por chamada (`fase_2.md`: *"Vencimento:
  Fase 9, junto da reavaliação do item 8"*).

As três entram na tabela abaixo com o prefixo de origem preservado. O **defeito
do mecanismo** que as deixou passar é a **P9-1**.

### 2.3 Duas lacunas do gabarito contra `08` §3 — e as duas fecham na peça 3

Medido na peça 1, lendo o gerador de gabarito. `domains/academus/seed/gabarito.py`
produz os fatos da Linha B (`grade_change_retroactive`, um por linha da trilha
semeada) com `fact_id`, `actor`, `source_ip`, `dest` e `records_affected` — e
**sem `projections`**. Só os três fatos da Linha A (`linha_a.py`) as declaram.

Pela regra de `08` §2, fato sem `projections` é **invisível ao time azul**. Mas
`08` §3 enumera as fontes v1 e diz, do `database_audit.jsonl`, que ele carrega
*"leitura em massa (Linha A) e alterações de nota com IP e sessão (Linha B)"*.
As duas leituras não cabem juntas: ou a Linha B projeta em `database_audit`, ou
a tabela de `08` §3 descreve um arquivo que não vai existir.

**Não é spec-change** — a spec está coerente, e é o gerador que está incompleto:
`08` §3 é autoridade sobre o que cada fonte carrega, e quem declara `projections`
é o gabarito, que é mecanismo. A correção é do gerador, e cai na peça que
constrói o `database_audit`.

Fica registrado aqui porque é exatamente a classe de defeito que `08` §1 existe
para impedir: a evidência que o time azul recebe deixaria de ter a linha de
integridade, e nada ficaria vermelho — a cobertura de projeção passaria, porque
fato sem `projections` **legitimamente** não projeta.

**A segunda lacuna apareceu ao escrever a peça 3, e é da mesma família.**
`08` §3 enumera `email.eml` com *"phishing de recadastramento — origem da
Linha A"*, e **nenhum fato declarava `projections: [email]`**: o gerador não
produzia o fato de phishing. Sem ele, o `.eml` seria conteúdo autoral em vez de
projeção — exatamente o que `08` §2 proíbe ao dizer que *"precursor_events.jsonl
deixa de ser artefato autoral: é gerado como projeção"*.

**As duas fecham na peça 3.** `linha_a.py` passa a sintetizar
`phishing_delivery` (determinístico por seed, antes do acesso inicial na ordem
do incidente), e `gabarito.py` declara `projections: [database_audit]` nos fatos
da Linha B. Nenhuma das duas é spec-change: `08` §3 é autoridade sobre o que
cada fonte carrega, e quem declara `projections` é o gabarito, que é mecanismo.

**E uma terceira, que o motor cobrou sozinho:** o gabarito já declarava `cef`
desde a P7-10, e o motor recusa por falha fechada a cobertura que pede fonte sem
gerador. Um pacote de geradores que parasse nas quatro de `08` §3 não projetaria
o próprio gabarito do projeto — então `cef` entrou aqui. É a metade-arquivo do
item 4; a outra (`telemetry_emitted` no event store) tem peça própria, e as duas
compartilham o gerador, que é o que `08` §2 quer dizer com *"um contrato só"*.

### 2.4 Prova negativa só vale conferida na suíte COMPLETA, e resolvida por `sys.modules`

**Três ocorrências da mesma família de defeito nesta fase, todas de instrumento
lido como ausência de detecção.** Registradas juntas porque a terceira só foi
reconhecida rápido por causa das duas primeiras.

1. **Peça 1 — `from pacote import submodulo`.** Os quatro mutantes morriam com o
   probe rodando sozinho e **sobreviviam** na suíte completa. O harness planta a
   mutação substituindo `sys.modules`; `from range_core.evidence import elenco
   as mod` liga ao **atributo do pacote**, que o harness não toca. Sozinho
   funcionava por acaso — o atributo ainda não existia.
2. **Peça 3 — o mesmo, com `linha_a` e com o `__init__` do pacote.** A mutação
   do fato de phishing não derrubava nada porque a suíte segurava
   `from domains.academus.seed import linha_a`; e as de `cef` e `jsonl` não
   derrubavam nada porque `geradores()` resolvia os submódulos por atributo.
   O `__init__` **não pode ser mutado**: o harness o carrega como módulo avulso,
   sem `__path__`. A saída foi do outro lado — `geradores()` passou a resolver
   por `import_module`.
3. **Peça 3 — `identity_audit` e `database_audit` segurando `jsonl`.** Import no
   topo guarda a função original; entram na lista de mutáveis **sem mutação
   própria**, só para serem recarregados depois. É a ordem de dependência que o
   cabeçalho do harness descreve e que `test_queda_de_sessao_probes.py` já usa.

A regra que fica: **prova negativa se confere na suíte completa, e tudo o que
ela muta resolve-se por `sys.modules`.** Isolada, ela pode estar medindo o acaso
da ordem de import.

### 2.5 A conferência empilha duas perguntas, e elas não são redundantes

Medido na peça 4, pela prova negativa. `conferir` compara o `sha256` do
manifesto **e** o conteúdo reprojetado, e a mutação que removia a primeira
comparação **não matava teste nenhum** — a segunda pegava a edição de qualquer
forma.

Não era gate frouxo: as duas perguntas são diferentes.

- **o `sha256`** pergunta *"o arquivo é o que foi escrito?"*;
- **a reprojeção** pergunta *"o arquivo é o que o gabarito projeta?"*.

Quem edita o arquivo **e** atualiza o hash no manifesto passa pela primeira, e só
a segunda o pega. E quem edita só o arquivo é pego pelas duas — mas com
**mensagens diferentes**, e `06` T13 nomeia o hash como o mecanismo da detecção
de edição manual. Sem a comparação de hash, a edição simples era reportada como
*"manifesto e arquivo foram alterados juntos"*, que é falso.

O gate ganhou dois casos por causa dessa medição: um que exige a mensagem do
hash, outro que exerce o conluio — e a mutação passou a morder. **A redundância
aparente era divisão de trabalho**, e o que faltava era um teste que a
distinguisse.

### 2.6 O hook defendeu a fronteira, e a conveniência era plausível

Medido na peça 5. A primeira versão de `range-core/telemetry/catalogo.py` trazia
um atalho `do_academus(contratos)` — conveniência de composição, para o chamador
não montar o caminho. O hook `check_architecture` **bloqueou a escrita**:
invariante 1, `range-core/` não importa de `domains/`.

O atalho não mudou de forma, mudou de lado: foi para
`domains/academus/telemetria.py`, que é quem sabe onde mora o próprio arquivo. O
núcleo carrega e confere; **qual fato do mundo acadêmico vira qual sinal de SIEM
é conhecimento do adapter**.

Fica registrado porque a conveniência era plausível e o defeito seria invisível
no verde — é exatamente assim que uma fronteira vaza. E é a diferença que a §1.6
do registro da Fase 1 estabelece: **instrução é regra; hook é impedimento**.

### 2.7 `achados_no_valor` julga VALOR, não texto — a guarda que não guardava

Medido na peça 3, e é a lição mais cara dela. O item 5 exige *"nenhum arquivo
contém anexo, binário, IOC real ou domínio roteável"*, e o predicado que
responde isso já existe em `dados_sinteticos` — reusá-lo em vez de escrever um
segundo é a lição da P1-13.

Mas `achados_no_valor` opera sobre **um valor de campo**: `hostnames_candidatos`
assume que o valor é uma URL, um e-mail ou um hostname nu, e **texto com espaço
no meio ele descarta**, devolvendo lista vazia. Chamado sobre o conteúdo inteiro
de um arquivo de log, ele passa vacuamente: `"visite https://<host roteável>/login"`
não produz achado nenhum.

A primeira versão da guarda do motor fazia exatamente isso — e a primeira versão
do teste que a julgava, também. **A guarda parecia proteger e não protegia, e o
teste concordava com ela.**

A correção é tokenizar antes de julgar, e a divisão de responsabilidade fica
declarada: **a tokenização é do motor; o julgamento continua sendo do predicado
único.** Ensinar `dados_sinteticos` a ler texto livre mudaria a semântica de um
módulo que o CI e o loader já consomem, para servir a um chamador só.

O teste usa `split()` puro e o motor usa uma regex que também corta pontuação —
**as duas tokenizações são diferentes de propósito**: um teste que reusasse a do
motor deixaria de ser oráculo independente e aprovaria um defeito na própria
tokenização. E a prova negativa restaura o defeito exato, porque sem ela nada
distinguiria a guarda que funciona da que não funciona.

## 3. Itens de DoD — status e evidência

A §7 de fechamento é redigida por quem implementou **após** o veredito do
auditor. Esta seção é o insumo do auditor: cada item de DoD com status e a prova
executável que o sustenta.

| # | Item de DoD | Status | Evidência executável |
|---|---|---|---|
| 1 | Toda fonte é projeção de `fact_id`; nenhum gerador inventa entidade | **VERDE** — as seis fontes que o gabarito declara são projeção de fato, o motor **recusa** o gerador que inventa, e `evidence build` as escreve em disco com o `MANIFEST.json` | Três camadas. (a) `range-core/evidence/elenco.py` responde as três perguntas puras — `elenco_de`, `cobertura_de` (fato sem `projections` fora) e `enderecos_no`; `tests/test_evidence_elenco.py` (18, **dirigido por fato e não por seed**, `06` T13) + probes (2), 4 mutantes. (b) `range-core/evidence/projecao.py` transforma o oráculo em **porta**: `EntidadeInventada` nomeia a fonte e o valor; `tests/test_evidence_projecao.py` (29) + probes (2), 5 mutantes. (c) `domains/academus/evidence_generators/` — os geradores reais das cinco fontes, provados contra o fato em `tests/test_evidence_generators.py` (27) + probes (2), 5 mutantes. **Nenhuma fonte carrega `fact_id`** (`05` §6), e o domínio do link do `.eml` **deriva** do elenco em vez de ser escrito à mão — a fresta do item 1 onde o oráculo de endereço não olha |
| 2 | `range-cli evidence verify` dirigido por fato | **VERDE** | `range-core/evidence/build.py::conferir` **reprojeta em memória** e compara com o disco — não há regra de validação escrita à mão, o oráculo é o próprio produtor rodado de novo. Confere, em ordem de dependência: manifesto presente e válido contra o contrato → `ground_truth_hash` → cobertura declarada × projetada → `sha256` por arquivo → conteúdo reprojetado → arquivo a mais. `range-cli evidence verify <path>` sai `0`/`2` e **não escreve** (`04` §8.1 (a), provado por `st_mtime_ns` antes/depois). `tests/test_evidence_build.py` (28) + probes (2) |
| 3 | `precursor_events.jsonl` reproduzível; edição manual detectada por hash | **VERDE** | `domains/academus/evidence_generators/precursor.py` — o phishing projeta em **duas** fontes (`email` e `precursor`), que é o modelo de `08` §1. O arquivo tem o nome que a spec usa, é reproduzível byte a byte, e a edição manual é detectada. **O precursor omite `actor` de propósito**: atribuição é o achado do exercício, não o insumo |
| 4 | Telemetria CEF é projeção, não emissão independente | **VERDE** | Duas metades, **um gerador só** — que é o que `08` §2 quer dizer com *"um contrato só"*. O arquivo `cef.log` (peça 3) e o `telemetry_emitted` saem dos **mesmos fatos**: `domains/academus/telemetry_events.yaml` (`02` §10, os doze eventos) mapeia `fact_class` → assinatura, e `range-core/telemetry/forwarder.py::programar` deriva o payload. **A prova é de valor, não de estrutura**: o `src` do evento e o do `cef.log` são comparados lado a lado, porque duas implementações coerentes hoje não provam nada sobre amanhã. O payload valida contra `$defs/telemetry_emitted_payload`, com `fact_id` **inexpressável** (`05` §6) |
| 5 | Nenhum anexo, binário, IOC real ou domínio roteável | **VERDE para as fontes que existem** | Duas metades. (a) **Banner** (`06` T13, critério próprio): `range-core/evidence/banner.py` produz e reconhece o banner na **primeira linha**, por formato de fio, com o texto **lido do contrato**; formato sem forma declarada é recusado. 8 casos, incluindo o negativo de posição (rodapé não conta). (b) **IOC**: `projetar()` levanta `IOCEncontrado` usando `dados_sinteticos` — **o mesmo predicado do CI e do loader**, não um segundo detector (P1-13). O `.eml` tem as três negativas de `05` §2 em casos separados: sem anexo, sem MIME multipart, link em sufixo reservado. **A guarda passava vacuamente na primeira versão** — ver §2.5, e o mutante que restaura o defeito |
| 6 | Replay respeita o clock de exercício | **VERDE** | `range-core/telemetry/forwarder.py::Replay` lê `elapsed_seconds()` — nunca o relógio de parede — e tem as três propriedades com caso próprio: só emite o que venceu em tempo de **exercício**, **nada novo vence durante a pausa** (`01` §3 congela o clock), e **não reemite** (duplicata no event store é sinal para a reconstrução). O forwarder **não sabe pausar**: ele lê o tempo, e quem o move é o gm-console — duas autoridades sobre o mesmo relógio seria o defeito. `tests/test_telemetry_forwarder.py` (20) + probes (2) |
| 7 | Reconstrução < 3 s com `telemetry_emitted` no volume de 4 h | *não iniciado* | — |

## 6. Pendências

Prefixo `P9-` para as que nascerem aqui. A tabela abaixo começa com o que foi
**herdado**, e o prefixo herdado é preservado: renumerar apagaria a cadeia que
liga a pendência ao registro em que ela nasceu.

As **seções de detalhe** das herdadas são resumo com ponteiro, e não cópia: o
argumento inteiro de cada uma vive no `docs/progress/fase_N.md` de origem.
Repeti-lo aqui criaria duas fontes para o mesmo fato. O que fica aqui é o id, o
estado, e a relevância para ESTA fase.

**`Estado` é o enum fechado da Fase 7**: `ABERTA` · `LATENTE` · `DECIDIDA` ·
`VENCIDA` · `RESOLVIDA` · `ENTREGA`.

<!-- tabela-resumo-de-pendencias -->

| Pendência | Assunto | Estado | Vence em |
|---|---|---|---|
| P9-1 | a migração de pendência só é conferida entre fases com coluna de estado — o gatilho escrito numa tabela de três colunas (fases 0–5) não chega a destino nenhum por máquina | `ABERTA` | esta fase, junto do fechamento — foi ela que expôs o defeito ao resgatar P1-3, P1-13 e P2-11; ver abaixo |
| P1-3 | ~~`evidence.schema.yaml` valida um artefato que ainda não é produzido~~ | `RESOLVIDA` | **venceu na peça 2**: `range-core/evidence/manifesto.py` produz o `MANIFEST.json` e `erros_de_schema` o valida contra o contrato real, com os `$ref` cruzados resolvidos pelo `Registry` do loader. Oito fases depois, o contrato tem consumidor; ver abaixo |
| P1-7 | o id do inject pode vazar a linha; falta o mecanismo que impeça o próximo pack de decidir pelo vazamento | `ABERTA` | a fase que decidir o destino do pack (P7-9) ou o primeiro pack novo; detalhe em `fase_7.md` §"P1-7" |
| P1-13 | duas cópias das faixas sintéticas — o contrato declara as faixas e `check_synthetic_data.py` declara as suas; divergiram duas vezes em silêncio | `ABERTA` | **esta fase** — é ela que constrói o gerador, e é aqui que o gerador seguiria o contrato enquanto o CI julga pela constante; detalhe em `fase_1.md` §"P1-13" |
| P2-11 | `append` abre uma conexão por chamada | `ABERTA` | **esta fase** — telemetria não grava a ritmo de facilitador; leitura e escrita reabrem juntas, pela mesma causa (volume); detalhe em `fase_2.md` §"P2-11" |
| P4-8 | leitura síncrona no laço de eventos serializa e bloqueia em volume | `ABERTA` | **esta fase** é o gatilho de medição declarado — o volume de `telemetry_emitted`; detalhe em `fase_4.md`/`fase_7.md` §"P4-8" |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores de `line_b_case.set` | `ABERTA` | o schema v3, quando houver delta real; detalhe em `fase_5.md`/`fase_7.md` §"P5-4" |
| P6-2 | `observable_impact` (start de `TTA`) não existe em contrato | `DECIDIDA` | o commit em que o consumidor de `TTA` for desenhado; detalhe em `fase_6.md` §"P6-2" |
| P6-3 | `before`/`after`/`since` dependem de uma gramática de `exercise_time` que não existe | `ABERTA` | os três gatilhos herdados da Fase 6, intactos; detalhe em `fase_6.md` §"P6-3" |
| P6-5 | `review_scope` passa a carregar a lista de `case_id` que o escopo alcança | `ABERTA` | a fase que consumir `03` §5.3, candidata a Fase 10 (AAR/calibração); detalhe em `fase_6.md`/`fase_7.md` §"P6-5" |
| P6-6 | o sentinela de branch intercepta `Write`/`Edit` e não `Bash` | `LATENTE` | a primeira sessão que trabalhe em duas branches simultâneas; detalhe em `fase_6.md` §"P6-6" |
| P6-8 | justificativa ausente devolve `409`, reservado a recusa de estado | `DECIDIDA` | a medição dos consumidores, ou a Fase 10; detalhe em `fase_6.md` §"P6-8" |
| P6-12 | a condição (4) da contrassinatura não pode disparar em produção (`sub == persona`) | `ABERTA` | a palavra do proprietário entre as saídas (a) e (b); detalhe em `fase_6.md` §"P6-12" |
| P6-13 | dezesseis violações plantadas da §3.5 da Fase 6 são atestação, não prova reexecutável | `ABERTA` | o artefato que torne a afirmação reexecutável; detalhe em `fase_6.md` §"P6-13" |
| P7-1 | a rota de submissão não valida o payload contra o contrato antes de gravar | `ABERTA` | decisão do proprietário sobre qual linha entrega; detalhe em `fase_7.md` §"P7-1" |
| P7-4 | consumo de `event_type` por selecionador sem allowlist declarada | `ABERTA` | **Fase 12** — degrau 1.5; detalhe em `fase_7.md` §"P7-4" |
| P7-5 | chamadores de cada emissor não varridos quando o contrato do emissor muda | `ABERTA` | **Fase 12** — degrau 2; detalhe em `fase_7.md` §"P7-5" |
| P7-11 | condição temporal de branch (`before`/`after`) carrega e nunca ramifica | `ABERTA` | o gatilho da P6-3 (a gramática temporal nascer); detalhe em `fase_7.md` §"P7-11" |
| P7-12 | a superfície do hook do auditor acumulou cinco achados M/L sem rastro | `ABERTA` | a próxima edição da allowlist do auditor; detalhe em `fase_7.md` §"P7-12" |
| P7-13 | o harness não planta violação onde a correção entrou | `ABERTA` | **Onda 3 da Estrutura Agêntica** (TDD endurecido); detalhe em `fase_7.md` §"P7-13" |
| P7-14 | seis afirmações de registro/teste sem disposição (varredura P7-6) | `ABERTA` | a varredura de fechamento desta fase; detalhe em `fase_7.md` §"P7-14" |
| P8-2 | o banner (`05` §4) na classe `exportacao` não tem fase de destino | `ABERTA` | a fase que construir os artefatos de exportação do academus-web; detalhe em `fase_8.md` §"P8-2" |
| P8-3 | a entrada `pytest` na allowlist do auditor admite comando que nenhum interpretador executa | `ABERTA` | a fase que adotar `pytest`, ou a decisão do proprietário de removê-la; detalhe em `fase_8.md` §"P8-3" |
| P8-4 | cinco das sete superfícies do academus-web (`02` §7) não têm fase de destino | `ABERTA` | a fase que construir o restante do academus-web; detalhe em `fase_8.md` §"P8-4" |
| P8-5 | as três telas da Fase 8 não têm rota que as sirva, e a `participant-api` não tem raiz de composição de produção | `ABERTA` | **redatada na abertura da Fase 9**: o proprietário decidiu no chat (2026-09-18) que ela NÃO entra nesta fase. Novo vencimento: a fase de serving/deploy do web; ver abaixo |
| P8-6 | as sete `action_id` do enum fechado estão copiadas à mão em `persona-panel/tipos.ts` sem gate | `ABERTA` | a Onda 3, ou a geração de constantes TS a partir do contrato; detalhe em `fase_8.md` §"P8-6" |
| P8-7 | o cronômetro do Modo Prova em andamento recebe `exercise_minute` do chamador e não acompanha o relógio de exercício | `ABERTA` | a fase que ligar `ProvaEmAndamento` ao relógio autoritativo — **o item 6 desta DoD (replay respeita o clock) é candidato direto**; detalhe em `fase_8.md` §"P8-7" |

#### P9-1 — a migração de pendência é cega às fases de tabela antiga

**Nasce com a fase.** `check_progress_consistency.py` confere o par de pauta
fase N → N+1 apenas quando a tabela-resumo da fase N declara **coluna de
estado**. As fases 0 a 5 têm tabela de três colunas, anteriores ao vocabulário
fechado da Fase 7, e o verificador as pula — declaradamente, imprimindo o motivo.

A cegueira não é defeito do verificador: sem estado não há como dizer o que
deveria migrar, e inventá-lo seria escrever história por inferência. O defeito é
a **consequência não registrada**: gatilho escrito numa dessas tabelas —
*"resolve na Fase 9"* — não tem quem o cobre, e a pendência só chega ao destino
se um humano a reencontrar. Foi o que aconteceu nesta abertura com P1-3, P1-13 e
P2-11: as três nomeiam esta fase, e nenhuma constava da tabela da Fase 8.

**Vence em:** esta fase, junto do fechamento. A saída provável é uma varredura
de gatilho por texto — *"toda linha de qualquer registro que nomeie uma fase
como vencimento aparece na tabela-resumo daquela fase"* —, que alcança as
tabelas antigas sem exigir que elas ganhem coluna de estado retroativa. A forma
exata é decisão do fechamento, e a pendência existe para que a varredura não
dependa de alguém lembrar.

#### P1-3 — o contrato do manifesto valida artefato ainda não produzido — RESOLVIDA

Herdada da Fase 1, resgatada nesta abertura (ver §2.2). `evidence.schema.yaml`
valida o `MANIFEST.json` de `08` §7, e o contrato existia desde a Fase 1 porque
a DoD daquela fase o exigia — sem nunca validar nada. O próprio arquivo o diz:
*"quem consome, hoje: o evidence-simulator da Fase 9, que ainda não existe"*.

**RESOLVIDA na peça 2.** `range-core/evidence/manifesto.py::montar` produz o
documento e `erros_de_schema` o valida contra aquele schema, com os `$ref`
resolvidos pelo mesmo `Registry` que o loader de pack usa. A validação é real e
está provada nas duas direções: o manifesto correto passa, e um com quatro
defeitos (formato fora do enum v1, hash curto, `sha256` inválido, `fact_id` fora
da forma) é recusado **com o caminho** de cada um. O par negativo não é adorno —
um validador que nunca recusa também devolve lista vazia.

Um caso é dedicado ao **`$ref` cruzado** (`projects_facts.items` →
`ground_truth.schema.json#/$defs/fact_id_pattern`), porque resolver aquilo exige
o `Registry` montado com os dois contratos: sem ele, um validador mal montado
ignoraria a cláusula em silêncio e os outros três defeitos manteriam o teste
verde.

Detalhe de origem em `fase_1.md` §"P1-3".

#### P1-7 — id de inject pode vazar a linha

Herdada da Fase 1, carregada pelas 7 e 8. O pack de 4 h decidiu por ids neutros
`IN*`; falta o mecanismo que impeça o próximo pack de escolher o vazamento.
Detalhe em `fase_7.md` §"P1-7".

#### P1-13 — duas cópias das faixas sintéticas, e o gerador no meio

Herdada da Fase 1 (M2 da 2ª rodada de auditoria), resgatada nesta abertura.
`contracts/evidence.schema.yaml` declara as faixas de IP, os sufixos de domínio
e o vendor/product em `x-aurora-security-constraints`;
`tools/check_synthetic_data.py` declara as suas em constantes próprias. As duas
listas já divergiram **duas vezes** em silêncio, e hoje
`scripts/check_contract_examples.py` cruza as duas e reprova em divergência — o
que fechou o sintoma, não a causa.

A causa é esta fase: **o gerador seguiria o contrato e o CI julgaria pela
constante**. Enquanto ninguém gerava evidência, a duplicação era inerte.
Detalhe em `fase_1.md` §"P1-13".

#### P2-11 — `append` abre uma conexão por chamada

Herdada da Fase 2, resgatada nesta abertura. `PostgresEventStore._persist` faz
`psycopg.connect` a cada evento; a Fase 2 gravava a ritmo de facilitador, e por
isso não mordia. **Telemetria não grava a ritmo de facilitador** — é a única
fonte com ordem de grandeza diferente (`07` §Fase 9), e é o insumo do item 7
desta DoD. Leitura (P4-8) e escrita (esta) reabrem juntas, pela mesma causa.
A saída provável é conexão reusada ou pool, **medindo antes de escolher**.
Detalhe em `fase_2.md` §"P2-11".

#### P4-8 — leitura síncrona no laço de eventos

Herdada da Fase 4. O gatilho declarado é medição de volume, e o volume chega
aqui: o item 7 da DoD mede a reconstrução com `telemetry_emitted`. Par natural
da P2-11. Detalhe em `fase_4.md`/`fase_7.md` §"P4-8".

#### P5-4 — os seis conjuntos não cabem nos três valores de `set`

Herdada da Fase 5, mal formulada na origem. Detalhe em `fase_7.md` §"P5-4".

#### P6-2 — `observable_impact`, o start de `TTA`

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-2".

#### P6-3 — a gramática temporal de `exercise_time`

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-3". A P7-11 depende desta.

#### P6-5 — `review_scope` com a lista de `case_id`

Herdada da Fase 6. Detalhe em `fase_6.md`/`fase_7.md` §"P6-5". Candidata à
Fase 10.

#### P6-6 — o sentinela não intercepta `Bash`

Herdada da Fase 6, `LATENTE`. Detalhe em `fase_6.md` §"P6-6".

#### P6-8 — `409` para justificativa ausente

Herdada da Fase 6, `DECIDIDA`. Detalhe em `fase_6.md` §"P6-8".

#### P6-12 — a condição (4) da contrassinatura em produção

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-12". A saída é do proprietário.

#### P6-13 — as dezesseis violações plantadas como atestação

Herdada da Fase 6. Detalhe em `fase_6.md` §"P6-13".

#### P7-1 — a rota de submissão não valida o payload

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-1".

#### P7-4 — consumo de `event_type` por selecionador sem allowlist

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-4".

#### P7-5 — chamadores de emissor não varridos

Herdada da Fase 7, gatilho **Fase 12**. Detalhe em `fase_7.md` §"P7-5".

#### P7-11 — condição temporal de branch nunca ramifica

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-11". Depende da P6-3.

#### P7-12 — a superfície do hook do auditor

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-12". Vence na próxima edição da
allowlist do auditor; o resíduo específico é a P8-3.

#### P7-13 — o harness não planta onde a correção entrou

Herdada da Fase 7, gatilho **Onda 3**. Detalhe em `fase_7.md` §"P7-13".

#### P7-14 — seis afirmações sem disposição

Herdada da Fase 7. Detalhe em `fase_7.md` §"P7-14". A varredura de fechamento
desta fase dá disposição a cada uma.

#### P8-2 — o banner na classe `exportacao` sem fase de destino

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-2". **Não vence aqui**, e a
distinção importa: a classe `evidencia` do mesmo gate — banner na primeira linha
de todo arquivo de evidência — **é** desta fase (`05` §4, `06` T13), e
`check_banner_de_simulacao.py` já a defere nominalmente para cá. A classe
`exportacao` é artefato do academus-web, que nenhum item desta DoD constrói.

#### P8-3 — a entrada `pytest` da allowlist admite comando inexistente

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-3". A suíte do projeto é
`unittest`.

#### P8-4 — cinco superfícies do academus-web sem fase de destino

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-4".

#### P8-5 — as telas sem rota, e a `participant-api` sem processo

Herdada da Fase 8, e a única herdada cujo destino **era decisão de abertura desta
fase**: o registro da Fase 8 a marca como *"candidata à Fase 9 ou a uma fase de
deploy"*. `07` §Fase 9 não tem item de serving — os sete itens são evidência,
telemetria e desempenho —, então trazê-la para cá seria ampliar o escopo da fase
por decisão do proprietário, e não cumprir a DoD.

**DECIDIDA pelo proprietário na abertura (2026-09-18): NÃO entra na Fase 9.**
Fica para a fase de serving/deploy do web. O desenho continua pronto e válido em
`fase_8_plan_serving.md` (T822–T831: co-locar cada casca com sua data-API;
factory em `domains/academus/api/participante_processo.py`; serviço no compose),
e a pendência segue `ABERTA` com esse destino. Detalhe de origem em `fase_8.md`
§"P8-5".

#### P8-6 — o enum das sete ações copiado à mão no cliente

Herdada da Fase 8. Detalhe em `fase_8.md` §"P8-6".

#### P8-7 — o cronômetro da prova não acompanha o relógio de exercício

Herdada da Fase 8, e material aqui: o **item 6 desta DoD** — *"replay respeita o
clock de exercício"* — é a exigência de que o tempo venha do relógio
autoritativo e não de parâmetro do chamador. É o mesmo princípio, e o
`ProvaEmAndamento` é o caso já medido dele. Detalhe em `fase_8.md` §"P8-7".

## 7. Fechamento

> A redigir por quem implementou, **após** o veredito do `checkpoint-auditor`,
> como manda o rito.
