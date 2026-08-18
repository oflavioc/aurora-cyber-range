# Fase 5 — Dados e auditoria ⏸

**Status: EM ANDAMENTO — peças 1 e 2 de 6 fechadas.** A branch nasceu em
`fd34c44` e a âncora está gravada em `docs/process/phase_anchors.tsv`. As dez
decisões da §3 estão marcadas, e nenhuma linha de código nasceu contra decisão
pendente — as duas do operador (D9 e D10) foram respondidas antes da peça 2.

**Um status só**, e ele é o do documento inteiro — L2 da segunda auditoria da
Fase 3.

---

## 0. Por que este registro começa antes da fase

Mesma razão das Fases 2, 3 e 4: o plano decide coisas antes de existir código, e
**conversa não é fonte versionada**. As decisões da §3 estão marcadas
`DECIDIDA`, `PROPOSTA` ou `OPERADOR`; as duas últimas aguardam, e nenhuma linha
de código nasce contra elas.

**Afirmação sobre a spec aqui é citação, e foi relida no momento de escrever.**
Cada seção nomeia documento e §. A D3 da Fase 3 afirmou uma exigência de `05` §8
que a fonte não continha, e foi assim que se descobriu que o custo de citar de
memória não é a citação errada — é a decisão que se apoia nela.

---

## 1. O que a fase entrega, conferido na fonte

`07` Fase 5 — **OUTPUTS:** modelo completo, `CalendarioAcademico`,
`AutorizacaoRetificacao`, seed em escala com bulk insert, trilha append-only com
hash encadeado, `GM_NOTES.md` do pack.

**DoD — seis itens:**

1. Seed completo em < 5 min
2. Mesmo `RANDOM_SEED` produz dataset byte-idêntico em duas execuções
3. `UPDATE` e `DELETE` em `audit_trail` falham por trigger **e** por permissão de role
4. `GET /audit/verify-chain` detecta adulteração induzida em teste
5. Os seis conjuntos da Linha B existem nos volumes especificados
6. `GM_NOTES.md` contém a query de referência que separa indevidos de ambíguos

**Critérios de aceitação que julgam esta fase:** `06` T7 (auditoria imutável),
T8 (determinismo e gabarito), **T6** (isolamento de papel — *"Fases 4–5"*, e a
fase que acrescenta endpoint e personas é esta), T15 (segurança transversal, em
todas as fases).

### 1.1 Esta fase não tem NON-GOALS declarados, e a fronteira é derivada

O template obrigatório de `07` fixa seis blocos por fase — ENTRY, OUTPUTS,
ACCEPTANCE, DEMO, NON-GOALS, DoD. A entrada da Fase 5 traz **dois**: OUTPUTS e
DONE. Não há ENTRY, não há DEMO e não há NON-GOALS.

Isso não é defeito a consertar aqui — as Fases 3, 6, 8 e seguintes têm a mesma
forma, e reescrever `07` para completá-las seria `spec-change` sobre uma
convenção de redação, não sobre norma. **O que não pode ficar é a fronteira por
inferência silenciosa**, então ela está declarada aqui, derivada das fases
vizinhas e não de gosto:

| Fora desta fase | Onde está, na fonte |
|---|---|
| objetivos, rubricas, métricas pareadas, calibração, declarações | `07` Fase 6 |
| emissão de `audit_query_performed` na consulta à trilha | `07` Fase 6, item 1 da DoD |
| pack completo, branching, `range-cli`, linter de `GM_NOTES` × `ground_truth` | `07` Fase 7 |
| console de investigação, dashboards por persona, ações de continuidade | `07` Fase 8; `02` §7 e §9 |
| projeção de evidência, telemetria CEF, `precursor_events.jsonl` | `07` Fase 9; `08` |
| assimetria de informação e AAR | `07` Fase 10 |

**Uma correção de destinatário, e ela importa para o formato da trilha.**
`fase_3.md` §"o que sai daqui" escreveu que `audit_query_performed` foi *"movida
para a Fase 8"*, e o comentário de `domains/academus/api/app.py` repete a frase.
**`07` Fase 6 tem o item de DoD literal** — *"Consultar a trilha com filtro de
período emite `audit_query_performed`"* —, e o auditor da terceira rodada da Fase
4 já havia registrado a leitura certa (`audit_20260816T220943Z.md`). Documento
normativo prevalece sobre registro de fase: **é Fase 6**. A consequência prática
é desta fase — a trilha nasce com caminho de consulta por período, para que a
Fase 6 só precise acrescentar a emissão, e não reabrir o esquema.

---

## 2. O plano — as peças, e a ordem entre elas

Uma peça = uma volta = superfície declarada antes da implementação e checagem
escrita junto. A ordem abaixo não é temática: ela é a ordem em que cada peça
produz o insumo da seguinte.

| Peça | O que entrega | Fecha |
|---|---|---|
| **1** ✅ | registro seção → verificador de `05`, com as cinco direções e prova negativa pareada; e a §8.5 virando regra em `WORKFLOW.md` | **P4-12** |
| **2** ✅ | modelo completo, `CalendarioAcademico`, `AutorizacaoRetificacao`, `access_delegations` (migration, sem dado) | abriu a **P5-2** |
| **3** | trilha `audit_trail`: role `INSERT`-only, `REVOKE`, trigger, hash encadeado, `GET /audit/verify-chain`, e a escrita da trilha na rota de nota | **P3-6**, **P4-5**, e é o gatilho declarado da **P4-2** |
| **4** | seed em escala determinístico, com os seis conjuntos da Linha B nos volumes de `02` §6.1 | — |
| **5** | `GM_NOTES.md` e a query de referência | depende da **D10** |
| **6** | fechamento: DoD com prova item a item, registro, auditoria de checkpoint | — |

**A trilha vem antes do seed, e a ordem não é preferência.** Os seis conjuntos
da Linha B *são registros de alteração de nota* — `02` §6.1 os descreve por
janela, autorização, conta, IP e horário, que são campos de `02` §4.1. Semear a
Linha B sem trilha exigiria semeá-la duas vezes, ou semear numa tabela
provisória que a peça seguinte migraria. **A peça 1 vem antes de tudo** porque a
P4-12 existe justamente para que a fase não descubra no checkpoint qual seção de
`05` governa o que ela já construiu — foi o custo da §4 na Fase 4.

---

## 3. As decisões

Marcadas `DECIDIDA` (com o motivo, e implementável), `PROPOSTA` (recomendação
minha, o operador pode vetar) ou `OPERADOR` (não é minha, e a peça que depende
dela não começa antes da resposta).

### D1 — o registro de seções de `05` mora no verificador, não em YAML — `DECIDIDA`

A P4-12 pede **declaração**, não mecanismo: das oito seções de `05`, cinco são
nomeadas por algum verificador (§1, §3, §4, §6, §8) e três não são (§2, §5, §7),
e nada diz se a ausência é decisão.

A forma tem dois precedentes no repositório, e eles diferem: o `DESCRITIVO` de
`scripts/check_gate_coverage.py` é um dicionário **dentro** do verificador, com
motivo por entrada; `domains/flags_pendentes.yaml` é YAML, com **quem trará** por
entrada. Escolho a primeira, e o motivo é a direção (c) abaixo: a entrada precisa
nomear um módulo Python e o verificador precisa **abrir esse módulo e conferir
que ele de fato cita a seção**. Com o registro em YAML, o nome do módulo vira
string a resolver, e a checagem ganha um passo de indireção sem ganhar nada.

`scripts/check_secoes_de_seguranca.py`, com `_probes.py` pareado, nas quatro
direções:

| | |
|---|---|
| (a) | seção de `05` sem entrada no registro → **reprova** |
| (b) | entrada para seção que `05` não tem mais → **reprova** |
| (c) | entrada que nomeia verificador cujo fonte **não cita a seção** → **reprova** |
| (d) | entrada que diz "fase futura" para seção que **já tem** verificador → **reprova** |

A (d) é a terceira direção de `api_surface.yaml` aplicada aqui: é ela que impede
`planejada` de virar esconderijo.

**O que ele NÃO é**, e a pendência é explícita: não é um gate que exija
verificador para toda seção. Três das oito têm consumidor em fase futura, e
cobrar mecanismo antes do artefato é o erro que a §7.3 da Fase 3 nomeia.

### D2 — a §7 sai desta fase com verificador de verdade, e não só com declaração — `DECIDIDA`

`05` §7 é *"Integridade da trilha de auditoria"*, e ela é a seção cujo artefato
**esta fase produz**. Deixá-la no registro como "Fase 5, planejada" enquanto a
trilha nasce no mesmo commit seria escrever a declaração e não cumpri-la.

**A promoção da entrada é medida NA ORDEM, e não afirmada.** A direção (d) do
`check_secoes_de_seguranca.py` só é gate se ela de fato reprovar; promover a
entrada no mesmo gesto que cria o verificador deixaria a direção (d) como prosa —
ela nunca teria ficado vermelha, e ninguém saberia se ela funciona. Então a ordem
é: o verificador da §7 entra **primeiro**, com a entrada ainda dizendo *"sem
mecanismo — Fase 5"*; a saída vermelha vai para o registro; **só então** a entrada
é promovida. Vale igual para a §6 na peça 5 (D10.2).

O que o verificador confere é estrutura, e a propriedade em execução fica com os
testes de T7 contra Postgres real — que é a mesma divisão de
`test_event_store_postgres.py`: a migration declara `REVOKE UPDATE, DELETE,
TRUNCATE` e o trigger `BEFORE UPDATE OR DELETE`; `GET /audit/verify-chain` está
na superfície como `implementada`; e a role da aplicação não recebe privilégio de
escrita destrutiva em `audit_trail` em migration nenhuma.

**§2 e §5 ficam declaradas com destinatário**, que é o que a pendência cobra:
§2 (evidências sintéticas) → Fase 9, com `08`; §5 (fornecedores e atores de
ameaça) → Fase 7, com o pack. Nenhuma das duas ganha mecanismo agora.

**E a §6 é a que precisa ser medida em vez de herdada.** A P4-12 a conta entre as
cinco "nomeadas", e a citação que sustenta essa contagem é um **comentário do
workflow** — `.gitignore` como executor de `05` §6 —, não um verificador que a
nomeie no fonte. A cláusula de §6 que **esta fase toca** é outra: *"`GM_NOTES.md`
e `ground_truth.yaml` excluídos do build servido aos participantes"*, e ela só
tem sujeito a partir do commit em que esses arquivos existirem. A direção (c) da
D1 é quem decide isso, e ela decide medindo: se nenhum módulo cita §6, a entrada
dela não pode dizer "coberta".

Isso é a §4 da Fase 4 outra vez, com um dígito diferente — **"nomeada" é mais
grosso que "coberta"**, e a diferença aparece exatamente na cláusula que a fase
nova estreia.

### D3 — a cadeia de hash da trilha reusa a primitiva do core — `DECIDIDA`

`range-core/events/integrity.py` já encadeia por SHA-256 sobre forma canônica
mais `previous_hash`, e o cabeçalho dele **já diz que a trilha de `02` §4 e `05`
§7 é da Fase 5 e que antecipá-la ali seria duplicação**. Duas implementações de
encadeamento de hash no mesmo repositório é a classe de defeito que a Fase 1
pagou para desfazer.

O que se reusa é a **primitiva** — forma canônica + hash anterior → `row_hash`,
mais a verificação de contiguidade —, extraída para função genérica sobre
`dict`. O que **não** atravessa a fronteira: a tabela, o trigger, a role, os
campos de `02` §4.1 e a semântica do que é uma linha de trilha. Isso é adapter, e
o invariante 1 continua valendo na direção que ele guarda — `domains/` importa
`range-core/`, nunca o contrário.

Os dois limites que `integrity.py` declara — truncamento de cauda e reescrita
completa por quem tem o código — **continuam valendo aqui e são repetidos na
trilha**, porque `REVOKE` não protege contra quem tem privilégio.

### D4 — a linha de trilha é escrita na mesma transação da nota — `DECIDIDA`

`02` §4.3 do `01` diz que business state não reverte porque reverter *"gera
estado impossível — evento na trilha de auditoria sem correspondente no banco"*.
A recíproca é desta peça: nota gravada sem linha de trilha é o mesmo estado
impossível pelo outro lado, e é exatamente o que a P3-6 registra hoje.

Então a escrita é **uma transação só**: ou as duas linhas existem, ou nenhuma.
Trilha como efeito colateral best-effort depois do commit produz, na primeira
falha, uma nota sem registro — e a sala descobre isso no exercício, investigando.

**A concorrência tem custo e será medida na peça, não afirmada aqui.** O
encadeamento exige que dois `INSERT` simultâneos não leiam o mesmo
`previous_hash`; as saídas conhecidas são `SELECT ... FOR UPDATE` sobre a última
linha, `pg_advisory_xact_lock` por trilha, ou serialização por constraint de
unicidade em `sequence` com retry. A escolha sai com número, como a P3-2 saiu.

### D5 — P4-5 fecha com o par rota + FK, e não com a FK sozinha — `DECIDIDA`

A pendência é `grades.student_id` sem FK: nota de aluno inexistente é aceita com
**201**. A FK sozinha trocaria isso por erro de integridade — mudança de
comportamento entrando por efeito colateral de migration, que é o que a Fase 4
recusou fazer.

O par é: a rota **confere o aluno** e responde 404 como já responde para turma
inexistente, e **aí** a FK documenta no esquema o que o código passou a fazer —
que é o critério pelo qual as outras três FKs já existem. `test_P4_5_nota_de_
aluno_INEXISTENTE_e_aceita_hoje` fica **vermelho** no commit da mudança, que é
o anúncio que a Fase 4 deixou armado.

O gatilho declarado da pendência é *"o commit em que a trilha nascer"*, e é a
peça 3: trilha que registra aluno inexistente é a camada 2 produzindo evidência
plausível e falsa sobre a camada 1.

### D6 — determinismo byte-idêntico exige que o seed não leia relógio — `DECIDIDA`

O item 2 da DoD é *"mesmo `RANDOM_SEED` produz dataset byte-idêntico em duas
execuções"*. Uma única chamada a `now()` no caminho do seed o torna
insatisfazível, e o defeito aparece como diferença de um campo em milhões de
linhas.

Então: **toda data do dataset deriva do `CalendarioAcademico`**, que por sua vez
deriva de uma data de referência declarada — não do relógio. `range_core.
determinism.seeded_random` já dá fluxo por escopo, e cada gerador pede o seu, de
modo que acrescentar um gerador não desloca o que os outros produzem.

A prova é comparação de **dump canônico**: `COPY ... TO` com `ORDER BY` de chave
por tabela, SHA-256 por tabela, duas execuções sobre banco recém-migrado. Sem
`ORDER BY` explícito o Postgres não promete ordem, e o teste ficaria
intermitentemente vermelho por um motivo que não é o dele.

### D7 — o `< 5 min` é medido com máquina, data e stack declaradas — `DECIDIDA`

Mesma forma que `06` T3 fixou para a curva de reconstrução, e pelo mesmo motivo:
número de desempenho sem o contexto em que foi obtido envelhece sem que ninguém
perceba. `01` §7 manda seed por `COPY`/`executemany`, nunca ORM linha a linha, e
`02` §5 põe o volume em milhões de registros de nota.

### D8 — a suíte de dados roda contra Postgres real, e não contra duplo — `DECIDIDA`

T7 exige que `UPDATE` e `DELETE` falhem **por trigger e por permissão de role**,
e T8 exige dataset byte-idêntico. Nenhuma das duas propriedades existe fora do
Postgres: trigger, `REVOKE` e `COPY` são do banco, e um duplo em memória
provaria a implementação do duplo. O repositório já tem o caminho —
`tests/_academus_banco.py`, `test_business_state_postgres.py` e o job de
containers do CI.

### D9 — `POST /auth/token` nasce nesta fase — `DECIDIDA` (operador)

`domains/academus/api_surface.yaml` traz a rota como `planejada` com o motivo
escrito: *"o que falta é a porta de entrada, e ela chega na Fase 5 com as
personas do seed"*. Esta é a fase das personas, e `05` §8 exige que senha de seed
seja **derivada do `RANDOM_SEED` e impressa apenas no log de seed local** — hoje
essa cláusula não tem consumidor nenhum.

**Não é item de DoD desta fase, e isso fica registrado em vez de dissolvido:**
é **escopo herdado da superfície**, e não escopo cobrado pela DoD. A distinção
importa no fechamento — a §7 não pode listar esta rota entre os itens provados,
porque nenhum item a pede.

**O motivo do operador é o que decide, e ele é mais forte que o meu:** a cláusula
de `05` §8 sobre senha derivada do `RANDOM_SEED` **está sem consumidor desde que
foi escrita**, e *cláusula normativa sem consumidor é a forma de coisa que
envelhece sem ninguém notar*. É a mesma família da P4-12, um nível abaixo: lá é a
seção sem verificador, aqui é a cláusula sem quem a exerça. A diferença é que
esta tem fase que pode exercê-la agora.

Os dois argumentos que já estavam de pé continuam: a terceira direção da checagem
de superfície cobraria a promoção numa fase que não declarou a rota, e T6 —
*"Fases 4–5"* — fica mais forte com token emitido pelo caminho real do que com
token assinado no teste.

### D10 — onde vivem `GM_NOTES.md` e `ground_truth.yaml` — `DECIDIDA` (operador): `scenarios/` fora do Git

**Esta é a decisão que `CLAUDE.md` reserva ao operador com todas as letras**, e
ela vence aqui: *"a decisão vence no commit em que o primeiro `ground_truth.yaml`
for escrito, e não antes"*. O item 6 da DoD e `06` T8 exigem `GM_NOTES.md` com a
query de referência **e** que todo fato citado nele exista em
`ground_truth.yaml`; a mesma `CLAUDE.md` proíbe versionar os dois neste
repositório, que é público.

Os dois não se contradizem — o que falta é dizer **onde** o artefato mora. As
opções que `CLAUDE.md` enumera, com a consequência de cada uma para a DoD:

| Opção | O que a DoD passa a exigir | Custo |
|---|---|---|
| **repositório privado separado** | a verificação de T8 sai do CI deste repo, e o item 6 passa a ser provado lá | dois repositórios, e a prova da fase mora fora dela |
| **submódulo privado** | CI deste repo pode conferir quando o submódulo está disponível, e **degrada quando não está** | degradação para "ok por não saber" é a classe que esta linhagem já pagou três vezes |
| **`scenarios/` fora do Git** | o artefato é reconstruído localmente do seed; o CI confere o **gerador** e a query, nunca o gabarito | a prova é do mecanismo que produz o gabarito, não do gabarito |

**Minha recomendação é a terceira, com uma distinção que ela torna possível:** o
que é gabarito não é a query nem a descrição dos seis conjuntos — `02` §6.1
publica os dois, e a spec é pública. Gabarito é **quais casos concretos**, e eles
saem do `RANDOM_SEED`, que mora em `.env` e não é versionado. Então versionar o
**gerador** do `GM_NOTES.md` e a query de referência mantém a fronteira pública
demonstrável — que é o que `CLAUDE.md` chama de "exemplo sanitizado" — enquanto
o arquivo com os 22 `case_id` nasce só na máquina de quem tem o `.env`.

**Decidido: `scenarios/` fora do Git.** A distinção que separa o que é público do
que é gabarito é o que decide, e ela vale a repetição porque é ela que sustenta
as três exigências abaixo: **gabarito não é a query nem a descrição dos
conjuntos** — `02` §6.1 publica as duas, e a spec é pública. **Gabarito é quais
casos**, e eles saem do `RANDOM_SEED`, que mora no `.env`. Versionar o gerador e
a query mantém a fronteira demonstrável em vez de declarada.

#### D10.1 — o `.gitignore` carrega o motivo, e não só a linha

*Quem abre o `.gitignore` não lê o `fase_5.md`.* A entrada de `scenarios/` vai
com o motivo escrito ali: por que o diretório inteiro sai, o que a exclusão
protege, e a linha que separa o que continua versionado — gerador, query e
template — do que nunca entra. Uma entrada muda de `scenarios/` seria, daqui a
duas fases, indistinguível de artefato de build ignorado por conveniência.

Isso é a mesma disciplina do `DESCRITIVO` de `check_gate_coverage.py`: o custo de
acrescentar uma linha é uma frase de motivo, e é ela que separa *"decidimos que
fica de fora"* de *"ninguém olhou"*.

#### D10.2 — o mecanismo, porque `.gitignore` é convenção e `git add -f` a atravessa

`.gitignore` não impede nada: ele muda o padrão. `git add -f` versiona o arquivo
sem que nada acuse, e um `git add -A` num diretório que alguém designorou
localmente faz o mesmo sem intenção nenhuma.

`scripts/check_gabarito_fora_do_git.py`, na peça 5, com as duas direções:

| | |
|---|---|
| caminho versionado cujo nome seja `ground_truth.yaml` ou `GM_NOTES.md`, em qualquer lugar da árvore | **reprova**, e nomeia o caminho |
| `.gitignore` sem a entrada de `scenarios/`, ou com ela sem motivo | **reprova** — a linha que executa a decisão não pode sumir em silêncio |

A fonte é `git ls-files`, e não o disco: o que importa é o que está **versionado**,
e o arquivo existir localmente é justamente o caso normal de quem tem o `.env`.
`contracts/ground_truth.schema.yaml` não colide — é o *schema*, com outro nome, e
a checagem casa nome de arquivo inteiro e não prefixo.

**E este verificador é o que promove a §6 no registro da peça 1.** Ele cita `05`
§6, e a direção (d) do `check_secoes_de_seguranca.py` **reprova** enquanto a
entrada da §6 continuar dizendo "sem mecanismo — Fase 5". A promoção não depende
de alguém lembrar: o commit que traz o mecanismo fica vermelho até o registro
acompanhar.

#### D10.3 — como o item 6 da DoD e o T8 são satisfeitos sem o artefato no repositório

A pergunta é justa e a resposta não pode ser *"existe na minha máquina"*, que é
atestação. **O CI não confere o artefato: ele o produz e o julga.**

O que é **versionado**: o gerador, a **query de referência** (SQL, escrito à mão e
não gerado) e o template do `GM_NOTES.md`. O que **nunca** é versionado: os dois
artefatos renderizados, que vivem em `scenarios/` e são reconstruíveis com o seed.

O job roda, do zero, sobre banco recém-migrado:

```text
RANDOM_SEED=<seed de teste>  →  seed do dataset  →  gerador
                                                     ├── ground_truth.yaml
                                                     └── GM_NOTES.md
```

e então afirma, sobre os artefatos que ele mesmo acabou de produzir:

1. **item 6 da DoD** — o `GM_NOTES.md` gerado contém a query de referência, e a
   query **executada** devolve os 22 indevidos e nenhum dos 11 ambíguos. Conter o
   texto sem executá-lo provaria interpolação de string;
2. **T8, terceiro critério** — a query retorna **exatamente** os 22 comprovados, e
   os 22 `case_id` batem com os marcados `set: indevido_comprovado` no
   `ground_truth.yaml` daquela mesma execução;
3. **T8, quarto critério** — todo fato citado no `GM_NOTES.md` existe no
   `ground_truth.yaml`. É o linter que `07` Fase 7 cobra por DoD; aqui ele já tem
   sujeito, e o que a Fase 7 acrescenta é a recusa no `range-cli`.

**O que fecha o buraco de "o seed de teste é que faz dar certo": duas execuções
com seeds DIFERENTES.** Os seis volumes de `02` §6.1 — 22, 11, 34, ~60, 18 e os
milhares — têm de sair iguais nas duas, com `case_id` diferentes. Isso separa
*"propriedade do gerador"* de *"coincidência de um seed"*, e é o mesmo par que
discrimina que o teste de PAUSAR precisou na Fase 4: um caso sozinho passa com um
gerador que só sabe fazer aquele.

**O que fica de fora da prova, e está dito:** o `GM_NOTES.md` do exercício real,
gerado com o `RANDOM_SEED` de produção, nunca é visto pelo CI. E não precisa ser —
a propriedade provada é do **gerador**, e ela é independente do valor do seed.
Afirmar mais do que isso seria a atestação que a pergunta recusa.

**E esse limite não pode morar só aqui.** Quem lê o item 6 da DoD no fechamento
não abre a decisão que o produziu — é a mesma distância que fez a §8.5 precisar
sair do registro para o `WORKFLOW.md`. Então o limite é escrito nos **dois**
lugares em que alguém tropeça nele: no cabeçalho do verificador que prova o item
(é ele que o leitor abre quando pergunta *"o que exatamente isto provou?"*), e na
linha do item 6 na §7 do fechamento, junto da prova — não como nota de rodapé do
registro da decisão.

### D11 — a §8.5 da Fase 4 vira regra de processo — `DECIDIDA` (instrução do operador)

*"O auditor é a única camada onde o teste roda sem que ninguém tenha interesse no
resultado."* Isso está hoje em `fase_4.md` §8.5, que é **registro descritivo** —
diz o que aconteceu, não o que deve acontecer. Lição registrada não constrange a
fase seguinte; a Fase 4 seguiu a regra contra o custo aparente de uma rodada
extra porque alguém se lembrou, e **detecção por memória não é detecção** é o
diagnóstico que este repositório já usou duas vezes para mecanizar coisa.

A regra entra em `docs/process/WORKFLOW.md` §"Ordem de defesa", na peça 1, com as
duas metades que a §8.5 separa:

- o auditor tem **três** papéis, e o terceiro é execução — o teste rodado por
  quem não o escreveu, em ambiente que quem implementou não configurou. Verde de
  CI é evidência real, e é evidência produzida pelo pipeline de quem implementou;
- **rodada de checkpoint degradada não fecha fase.** Pulo declarado no relatório,
  com a correção ao alcance, é rodada a refazer — e o custo da rodada extra não
  entra na conta, porque foi ele que a Fase 4 pagou para poder fechar.

`docs/process/` é **CODE** para o gate `spec_freeze` (o workflow o classifica
assim, com exceção do `PHASE_0_CHECKLIST.md`), então esta edição viaja no PR da
fase sem tocar a spec — conferido antes de propor, e não assumido.

---

## 4. As peças

### 4.1 Peça 1 — o registro de seções de `05`, e a medição que corrigiu a pendência

**Entregue:** `scripts/check_secoes_de_seguranca.py` com `_probes.py` pareado,
dois passos no job `arquitetura`, e a §8.5 da Fase 4 virando regra em
`WORKFLOW.md` §"Ordem de defesa".

**A medição vem antes do mecanismo, e ela mudou o número.** A P4-12 conta cinco
seções de `05` nomeadas por algum verificador (§1, §3, §4, §6, §8) e três sem
ninguém (§2, §5, §7). Medido sobre `tools/*.py` e `scripts/check_*.py`:

```text
scripts/check_api_surface.py            -> 8
scripts/check_banner_de_simulacao.py    -> 4        (+ o _probes, 4)
scripts/check_contract_examples.py      -> 3
scripts/check_spec_examples.py          -> 3
scripts/check_telas_sem_vocabulario.py  -> 8
tools/check_security_constraints.py     -> 1
tools/check_synthetic_data.py           -> 3
```

**São quatro e quatro, e a §6 é a que cai.** Nenhum verificador a cita. O que
sustentava a contagem eram duas citações que não são escopo de verificador: um
comentário do `.github/workflows/invariants.yml` dizendo que o `.gitignore`
executa a seção, e um comentário de `contracts/ground_truth.schema.yaml`. Nenhum
dos dois fica vermelho quando a §6 é violada.

**A P4-12 não fica maior por isso — ela fica mais barata**, e a diferença é o
momento. A seção que caiu é justamente aquela cuja cláusula esta fase estreia
(*"`GM_NOTES.md` e `ground_truth.yaml` excluídos do build servido aos
participantes"*), e ela já tem mecanismo datado e destinatário: a D10.2, na peça
5. Descobrir isso na peça 1 custa uma linha de registro; descobrir no checkpoint
custou uma rodada na Fase 4.

**"Nomeada" é mais grosso que "coberta", e o registro passou a distinguir os
dois.** Uma entrada pode declarar mecanismo, destinatário, ou **os dois** — que é
o estado real da §2 e da §5: o contrato já fecha parte da norma (anexo
inexprimível em `evidence.schema.yaml`, `threat_actor` em
`ground_truth.schema.yaml`) e o resto espera a fase que traz o artefato. Um
registro que só admitisse "coberta" ou "futura" obrigaria a mentir numa das duas.

**O universo não foi escolhido por esta checagem.** É o mesmo conjunto que
`check_readme_atual.py` conta e o README publica — `tools/*.py` e
`scripts/check_*.py`. Escolher um universo próprio seria escolher o que produz a
resposta desejada, e a resposta aqui foi contra a expectativa de quem escreveu a
pendência.

**As cinco direções**, e a (d) é a que trabalha nas peças seguintes:

| | |
|---|---|
| (a) | seção de `05` sem entrada → reprova |
| (b) | entrada para seção que a spec não tem, ou título que divergiu → reprova |
| (c) | mecanismo declarado que não existe, não é versionado ou não cita a seção → reprova |
| (d) | verificador do universo que cita a seção e não está declarado → reprova |
| (e) | entrada sem mecanismo e sem destinatário, ou destinatário para fase que `07` não tem → reprova |

A **(d)** é a terceira direção de `api_surface.yaml` aplicada aqui: quando a peça
3 trouxer o verificador da §7 e a peça 5 o da §6, a entrada que ainda disser "sem
mecanismo — Fase 5" fica **vermelha** e cobra a promoção no mesmo commit. A
promoção deixa de depender de alguém lembrar.

**A autoexclusão é necessária e está declarada:** o verificador cita as oito
seções por construção — ele *é* o registro. Sem excluí-lo do universo, a (d)
exigiria que cada entrada o declarasse como mecanismo de si mesma, e o registro
passaria a afirmar que executa `05`. Ele não executa: declara.

**Prova negativa: 14 eixos.** As cinco direções com estado plantado (seção nova
sem entrada, entrada órfã, título divergente, mecanismo que não cita, mecanismo
não versionado, promoção que faltou, citação não declarada, entrada vazia,
destinatário para fase inexistente, destinatário sem motivo), o controle verde
sobre o estado real, e **três leituras contra os arquivos reais** — as oito seções
de `05`, os números de fase de `07`, e o regex de citação nas duas direções: casa
as cinco formas que a árvore de fato usa (`05_SECURITY_REQUIREMENTS.md secao 1`,
`` `05` §4 ``, `05 secao 5.1`, `05_SECURITY_REQUIREMENTS §6`, `` `05_SECURITY_
REQUIREMENTS.md` §7 ``) e recusa as quatro falsas, incluindo `02` §4 e o ano
`2005`. Sem a segunda direção, um regex frouxo cobraria declaração por citação de
outro documento — ruído até alguém aprender a ignorar a checagem.

**A §8.4 aplicada antes de custar**, e não depois: a saída imprime `§` e títulos
acentuados, e num terminal `cp1252` isso é `UnicodeEncodeError` com rc=1 **sobre
árvore limpa**. `_tolera_terminal_estreito()` é o mesmo mecanismo de
`check_readme_atual.py` — perder um glifo é o custo; perder a saída inteira não se
compara.

**O que a peça tocou fora de si:** o README declara **17** verificadores em
`scripts/` e **16** com prova negativa (eram 16 e 15). O número não é enfeite —
`check_readme_atual.py` o cruza com a árvore, e a peça teria ficado vermelha nele.

### 4.2 Peça 2 — o corte de "modelo completo", declarado antes da migration

*"Modelo completo"* é a expressão mais elástica da DoD desta fase, e ela é
elástica porque não diz **completo em relação a quê**. Três leituras cabem na
frase, e elas produzem migrations diferentes:

| Leitura | O que ela produz | Por que não é ela |
|---|---|---|
| tudo que uma universidade tem | sem limite | não tem fonte; "completo" viraria juízo meu |
| as entidades que o exercício usa | ~8 tabelas | é a lista que **eu** escolheria, e a fase seguinte descobre a falta |
| **a lista de `02` §1** | 20 entidades | **é a única lista que a spec dá**, e é normativa |

**Adotada a terceira.** `02` §1 enumera vinte entidades, e é contra ela que
"completo" se mede. As duas exclusões abaixo têm fonte normativa própria — não
são corte por tamanho.

#### O que NÃO vira tabela, e contra qual documento

| Entidade | Fora porque | Chega em |
|---|---|---|
| **Incidente** | `01` §4 põe Participant Actions no **event store**, reversibilidade "nunca". `incident_declared` e `separate_incident_declared` são `event_type` do catálogo (`09` §4.1) | Fase 6, como **projeção** |
| **Declaracao** | idem — as ações `declare_*` de `03` §3.1 são eventos `declaration`, e `07` Fase 6 tem *"ações de declaração nos endpoints"* nos OUTPUTS | Fase 6, como **projeção** |

Uma tabela em Postgres para qualquer das duas seria **segunda casa do mesmo
fato**, e `09` §5 é explícito: nenhuma projeção escreve no store, e toda projeção
é reconstruível do zero. Business state não reverte (`01` §4.3); ação de
participante nunca reverte. Guardar declaração como business state trocaria a
segunda regra pela primeira sem que nada acusasse.

**Consequência que fica declarada:** `02` §4.1 manda a trilha registrar
*"Declarações do exercício — todas as ações de `declare_*`"*. A trilha desta fase
**suporta a categoria e não tem produtor** — o produtor é a Fase 6. Categoria sem
produtor declarada é diferente de categoria esquecida, e é a diferença que a
P4-12 acabou de mecanizar um nível acima.

**Dezoito tabelas, então.** As dezesseis restantes de `02` §1, mais
`CalendarioAcademico` e `AutorizacaoRetificacao` que a mesma lista já traz e que
`07` nomeia à parte por serem o que torna a Linha B detectável (`02` §2 e §3).

#### As quatro tabelas da Fase 4 não são substituídas — elas crescem

`students`, `classes`, `grades` e `enrollments` ganham colunas e chaves
estrangeiras. Isso tem três consequências que a migration precisa resolver, e
nenhuma delas é neutra:

| | O que muda | O cuidado |
|---|---|---|
| `classes.semester` | hoje é texto livre (`"2026.2"`); passa a referenciar `academic_calendar` | a linha do semestre precisa existir **antes**; a fixture de demonstração usa `2026.2` |
| `classes.professor_id` | hoje é texto sem FK, porque não havia tabela de professor; agora há | a regra `titular` da P3-3 não muda — a FK documenta o que a rota já compara |
| coluna nova `NOT NULL` | em tabela que já tem dado | ou default declarado, ou backfill na própria migration; `demonstracao.py` acompanha no mesmo commit |

**`grades.student_id` continua sem FK nesta peça, e isso é a D5 e não esquecimento.**
O par rota + FK é da peça 3, onde a trilha nasce; separar a FK do 404 faria a
mudança de comportamento entrar por migration, que é exatamente o que a Fase 4
recusou.

#### Uma entidade que `02` §1 não lista, e por isso está marcada

`02` §6.1 exige o conjunto **Credenciais compartilhadas — 18 casos**: *"Monitor/
assistente usando conta do professor **com registro formal de delegação**"*. Esse
registro não está entre as vinte entidades de §1, e **sem ele o conjunto é
indistinguível dos indevidos comprovados** — a Linha B perde um dos seis, e com
ele o item 5 da DoD.

Duas formas, e recomendo a primeira:

| Forma | A favor | Contra |
|---|---|---|
| **tabela `access_delegations`** | a delegação existe **antes e independentemente** da alteração de nota, e o console de investigação da Fase 8 precisa perguntar *"havia delegação válida naquela data?"* — que é consulta a fato, não a evento | acrescenta tabela que `02` §1 não nomeia |
| campo na linha da trilha | não acrescenta entidade | faria a delegação virar propriedade do evento: duas alterações sob a mesma delegação a repetiriam, e não haveria como perguntar por validade em data nenhuma |

**`02` §1 não se declara fechada** — diferente do catálogo de eventos, que `09`
§4 chama de *"registro fechado"* com todas as letras. Então acrescentar não
contradiz a spec. Mas é acréscimo ao modelo do domínio, e por isso está **dito
aqui em vez de aparecer na migration**: se você lê §1 como lista fechada, isto é
`spec-change` e não decisão de fase.

#### `Diário` não vira tabela própria, e a alternativa está dita

`Diário` é, em `02` §7, o que o Portal do Professor mostra: *"diário, frequência,
lançamento de notas"*. As notas já são `grades`; o que o diário tem e **nenhuma
outra entidade guarda** é a frequência. Então o que vira tabela é
`attendance_records`, e `Diário` permanece a **visão** turma → notas + frequência,
que é como a rota `GET /classes/{class_id}/gradebook` já o trata desde a Fase 3.

A alternativa — uma tabela `class_journals` com cabeçalho por turma — guardaria
uma linha por turma sem nenhum campo que a turma já não tenha. É a classe D4:
mesma regra escrita duas vezes.

#### O corte de VOLUME é outro, e é da peça 4

Tabela existir e tabela ter volume são coisas diferentes, e misturá-las é o que
faz "modelo completo" parecer "seed de tudo". Três faixas:

| Faixa | Entidades | Volume |
|---|---|---|
| **número na fonte** | Aluno, Professor, Curso, Semestre, Disciplina, Turma, Matrícula, Nota, e os seis conjuntos da Linha B | 28.000 · 1.200 · 60 · 8 · milhões de notas · 22/11/34/~60/18 — `02` §5 e §6.1 |
| **sem número, volume mínimo coerente** | HistóricoEscolar, Diploma, Bolsa, ContratoFinanciamento, QuestãoVestibular, ProjetoPesquisa, JobHPC, Usuário, `access_delegations` | o bastante para a trilha de `02` §4.1 ter objeto nas quatro categorias que ela declara, e para `02` §5 ter a distribuição plausível de CR, reprovação, evasão e bolsas |
| **vazia** | nenhuma | tabela criada e nunca semeada é modelo que parece pronto e não é |

**As quatro categorias de `02` §4.1 são o que decide a segunda faixa**, e não
gosto: a trilha registra alteração de nota, **emissão de diploma**, **banco de
questões** e **pesquisa acadêmica**. Sem `diplomas`, `exam_questions` e
`research_projects` com alguma linha, três das quatro categorias da trilha
nascem sem objeto — e uma trilha que declara categoria sem sujeito é a mesma
forma de promessa vazia que a P4-4 registra sobre flags.

#### O que a peça entregou, e a correção que escrever a migration produziu

**Dezenove tabelas**: as dezoito de `02` §1 menos `Incidente` e `Declaracao`,
mais `access_delegations`. Migration `0003_modelo_completo`, modelos, fixture
crescida e `tests/test_modelo_completo.py` com treze testes.

**A migration RECUSA sobre tabela com dado, e foi escrever o backfill que
mostrou por quê.** A primeira versão migrava: `students.program` viraria um curso
por valor distinto já gravado, com o próprio texto como nome — honesto, sem
informação nova. **Duas das três ligações não são deriváveis, e isso só aparece
ao escrever a terceira:**

| Ligação | O que falta no dado antigo |
|---|---|
| `classes.professor_id` → `professors` | o **nome** do professor não está em lugar nenhum; `classes` guarda só o identificador |
| `classes.semester` → `academic_calendar` | as **onze datas** do semestre — incluindo a janela de retificação, que é o que `02` §2 diz tornar a Linha B detectável |

Backfill que inventa nome de professor ou janela de retificação produz dado
plausível e falso, e `within_window` calculado contra janela inventada é a camada
2 mentindo sobre a camada 1 — o mesmo argumento da P4-5, um andar acima. Então
uma regra em vez de três backfills desiguais, e ela é verdadeira: **não existe
dado de produção neste projeto.** O que há em `students` e `classes` é a fixture
de seis linhas, que `demonstracao.py` recarrega.

**Medido, e não afirmado:** com um aluno gravado, a 0003 recusa com a instrução
no próprio erro, e **nenhuma tabela é criada** — a transação inteira aborta (6
tabelas antes, 6 depois). Com base limpa, aplica as 19 e o esquema confere.

**Limite declarado, com a condição que o encerra:** isto vale enquanto não houver
exercício com dado de participante gravado. No primeiro que houver, migration
terá de **migrar**, e recusar deixa de ser aceitável.

#### Nenhuma resposta de rota mudou, e a razão é estrutural

Você pediu a confirmação ou o par que anuncia. **São as duas coisas**, porque a
confirmação sozinha seria conferência minha:

| | Por que não muda |
|---|---|
| FK nova em `students` e `classes` | **nenhuma rota escreve nessas tabelas.** As duas únicas que escrevem são `POST /enrollment` e `POST /classes/{class_id}/grades`; `enrollments` já tinha as duas FKs desde a 0002 e a rota já conferia as duas pontas |
| `grades.student_id` | **continua sem FK** — é a D5, e o par rota + 404 + FK é da peça 3 |
| coluna nova (`status`, `entry_semester`) | `CAMPOS_PUBLICOS` é whitelist: o que não está lá não sai. Nasce invisível |
| `program` e `subject` | mudaram de **fonte** e não de **chave** — vêm de `courses.name` e `subjects.name` por relação, sob o mesmo nome e com o mesmo valor |

**O par que anuncia é `tests/test_modelo_completo.py`**, e ele tem três dentes:
`test_a_resposta_das_quatro_rotas_nao_mudou` fixa os conjuntos de chaves copiados
da resposta real da Fase 4 — não de `CAMPOS_PUBLICOS`, porque cruzar a whitelist
consigo mesma não prova nada; `test_program_e_subject_mudaram_de_fonte_e_nao_de_
valor` separa *"a chave sobreviveu"* de *"o valor sobreviveu"*, porque devolver
`C-9001` sob a chave `program` passaria no primeiro e quebraria a tela; e
`test_grades_student_id_continua_sem_FK` fica **vermelho no dia em que a peça 3
fechar a P4-5** — é o espelho, do lado do esquema, do
`test_P4_5_..._e_aceita_hoje`.

**348 testes, 86 exigindo Postgres**, contra Postgres real: base descartável,
migration aplicada, suíte inteira verde. Os quatro pulos restantes são de Redis e
já existiam.

#### `class_journals` recusada — a D4 em esquema, e não em código

A D4 da Fase 3 nomeou a classe *"mesma regra escrita duas vezes"* em código.
`class_journals` seria a mesma coisa **em esquema**: uma linha por turma sem
nenhum campo que a turma já não tenha, e um segundo lugar de onde ler a mesma
identidade. A frequência — que é o que o diário tem e nenhuma outra entidade
guarda — virou `attendance_records`, e `Diário` continua sendo a visão turma →
notas + frequência.

Vale registrar porque a classe é a mesma e o custo é diferente: em código, a
duplicação diverge na primeira edição; em esquema, ela diverge e **fica**, porque
migration para desfazer tabela já povoada é mais cara que a que a criou.

#### O que fica fora da fase inteira, e contra qual vizinha

| Fora | Onde |
|---|---|
| ecossistema externo de `02` §8 (`lms_vendor`, `payment_gateway`, …) | Fase 11 — `07` "serviços externos" |
| `federated-identity-simulator` e `mec-gateway` de `02` §7 | Fase 11 |
| telemetria do adapter de `02` §10 (`telemetry_events.yaml`) | Fase 9 |
| Modo "Prova em andamento", console de investigação, dashboards por persona | Fase 8 |
| ações de continuidade de `02` §9 | Fase 8 |
| regra de negócio sobre o dado (nota válida, matrícula única, pré-requisito) | **nenhuma fase pediu**, e a migration 0002 já recusou decidir comportamento de rota por esquema |

---

## 5. O que a Fase 5 recebe — as pendências datadas para cá

Quatro chegam com destinatário **Fase 5** no inventário da §6.1 da Fase 4, e
cada uma tem gatilho declarado por condição, não por marco.

| Id | O que ela cobra | Gatilho declarado | Onde vence |
|---|---|---|---|
| **P3-6** | `POST /classes/{class_id}/grades` grava nota antes de a trilha existir | a fase que a DoD e `06` T7 cobram | peça 3 |
| **P4-2** | emitir evento sem declarar `emite` não tem guarda em lugar nenhum | *o primeiro `append` fora do `inject-engine`* | **redatada para a Fase 6**, com o gatilho intacto — ver abaixo |
| **P4-5** | `grades.student_id` aceita aluno inexistente | *o commit em que a trilha de `02` §4.1 nascer* | peça 3, pela D5 |
| **P4-12** | três seções de `05` sem verificador e sem declaração de que é decisão | *o commit da trilha, que é quando a §7 sai de "plausivelmente futura"* | peça 1, **antes** do gatilho |

**A P4-2 não vence aqui, e foi redatada com o gatilho intacto.** O gatilho é o
primeiro `append` do adapter no **event store**, e a trilha de `02` §4 **não é o
event store**: é tabela dedicada, com hash próprio, role própria e trigger
próprio. O `append` do adapter chega com `audit_query_performed`, que é `07` Fase
6 (§1.1 acima corrige o destino que `fase_3.md` e o comentário de `app.py`
afirmam).

**Destinatário novo: Fase 6. Gatilho: o mesmo de sempre** — *o primeiro `append`
fora do `inject-engine`*. Nada na pendência mudou exceto a fase que a recebe, e é
essa a diferença entre redatar e enfraquecer: se a Fase 6 também não produzir o
`append`, ela desce de novo, e a condição continua sendo a condição.

**A confirmação é da peça 3 e sai medida**, com o mesmo extrator que a P4-2 usou
para descobrir que `degradacao.py` importa o store e só lê: se a peça fechar com
alguma chamada a `store.append` em `domains/`, a condição ocorreu **aqui** e a
pendência volta para esta fase, no commit em que isso for verdade. A medição é o
que decide; a redatação é a leitura de hoje.

As demais seguem como estão: **P4-4** e **P4-6** na Fase 8, **P2-6** na Fase 8, e
**P4-7**, **P4-8** e **P4-11** por condição, sem fase.

---

## 6. Pendências

Abertas nesta fase. Prefixo `P5-`.

| Id | O que é | Vence em |
|---|---|---|
| P5-1 | docstring de `scripts/sobe_sala.py` manda rodar um script que não existe | **condição** — ver abaixo |
| P5-2 | a trilha declara a categoria "declarações do exercício" e ela não tem produtor | **Fase 6** — ver abaixo |

#### P5-1 — caminho citado em docstring apontando para arquivo inexistente

**Achada lendo o repositório para planejar esta fase, e não corrigida de
passagem** — o valor dela está em ser a instância de uma classe, e corrigir a
linha apagaria a classe junto.

O bloco `USO` de `scripts/sobe_sala.py` diz:

```text
    AURORA_GM_PASSWORD=<credencial local> python scripts/sobe_sala.py
    # e, noutro terminal:
    python scripts/dispara.py A01        # ou o DEMO da peca 7
```

**`scripts/dispara.py` não existe, e nunca existiu** — conferido com
`git log --all --diff-filter=AD -- scripts/dispara.py`, que volta vazio, e não
por leitura do diretório. Não é arquivo removido cuja citação envelheceu: é
caminho que nasceu falso na docstring, ao lado de uma alternativa que é
verdadeira (`scripts/demo_fase4.py`).

**Por que isso não é cosmético.** `sobe_sala.py` existe para que a fase seja
VISTA enquanto é construída, e o bloco `USO` é a única instrução de como fazer
isso. Quem seguir a docstring recebe `No such file or directory` no segundo
terminal, com a sala no ar e sem meio de disparar — e a leitura natural do erro é
que a instalação está quebrada, não que a instrução está errada. É a classe da
§1.6 da Fase 1 com um agravante: as duas ocorrências que motivaram
`check_readme_atual.py` eram afirmações que **ficaram** falsas; esta **nasceu**
falsa e atravessou uma auditoria de checkpoint com PASS integral.

**Destinatário: esta fase**, e a correção tem duas direções possíveis — apontar
para `scripts/demo_fase4.py`, que existe e faz o que a linha promete, ou criar o
disparador de uma linha que a docstring descreve. A primeira é uma edição; a
segunda é superfície nova numa fase que não a pede.

**Gatilho: condição, e não marco** — *a primeira das duas que ocorrer*: a
primeira peça desta fase que precisar subir a sala para ver alguma coisa (e aí a
docstring é lida por quem a segue), ou o commit de fechamento, que é o último
momento em que ela ainda é desta fase.

**A forma que fecharia a classe, e ela não está decidida:** um verificador que
extraia caminhos citados em docstring e comentário de `scripts/` e `tools/` e os
cruze com `git ls-files` — mesma disciplina do `check_readme_atual.py`, que já
cruza `caminhos <- git ls-files` para README e BRIEFING. O risco é overmatch:
caminho citado como exemplo hipotético, caminho de artefato gerado que não é
versionado, caminho dentro de bloco de saída de comando. **Isso é decisão de
quando a pendência for fechada**, e registrá-la aqui é o que impede que a
correção da linha feche o assunto sem que ninguém tenha olhado para a classe.

#### P5-2 — categoria de trilha declarada sem produtor

**Aberta no corte da peça 2, e ela é a forma da P2-3:** requisito que existe e
não tem fase obrigada a cumpri-lo. Declarar não basta — sem destinatário, a
categoria fica lá e ninguém a cobra.

`02` §4.1 lista **cinco** categorias que a trilha registra: alteração de nota,
emissão de diploma, banco de questões, pesquisa acadêmica e **declarações do
exercício — todas as ações de `declare_*`** (`03` §3.1).

As quatro primeiras ganham objeto nesta fase: a peça 2 criou `diplomas`,
`exam_questions` e `research_projects` exatamente para que não nascessem sem
sujeito. **A quinta não pode ganhar**, e a razão é o corte que a própria peça 2
declara: as ações `declare_*` são eventos `declaration` do catálogo (`09` §4.1),
`01` §4 as põe no event store com reversibilidade "nunca", e `Declaracao` por
isso não virou tabela. O produtor delas é `07` Fase 6 — *"ações de declaração nos
endpoints"* nos OUTPUTS.

**O risco concreto, e ele não é teórico.** A trilha da peça 3 vai declarar as
cinco categorias. Quatro terão escrita exercitada por teste; a quinta será uma
constante que nada emite — e é assim que um `event_type` com erro de digitação
sobrevive até o exercício ao vivo, que `09` §4 chama de *"a falha mais cara
possível"*. Uma categoria que ninguém escreve nunca é exercitada, e ninguém
descobre que ela não funciona.

**Destinatário: Fase 6. Gatilho: o commit em que a primeira ação `declare_*`
nascer** — que é o que aquela fase entrega por OUTPUTS. O que ela precisa
encontrar aqui está dito para não ser redescoberto: a categoria já existe na
trilha, com nome, e o que falta é o chamador.

**A alternativa que NÃO se deve escolher:** omitir a categoria agora e
acrescentá-la na Fase 6. Isso trocaria uma promessa vazia declarada por uma
lacuna silenciosa — a trilha passaria a ter quatro categorias e nada diria que a
quinta é da spec. É a mesma escolha que a P4-4 registrou sobre flags que declaram
consumidor inexistente, e a resposta lá foi a mesma: declarar com destinatário.
