# Fase 5 — Dados e auditoria ⏸

**Status: CONCLUÍDA — as seis peças, os seis itens da DoD com prova, e PASS na
auditoria de checkpoint, com os dois MEDIUM corrigidos na mesma rodada.** O
fechamento item a item está na §7; o inventário de pendências por destinatário na
§8; as quatro lições na §9; a auditoria e as correções na §10. A branch nasceu em
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
| **3** ✅ | trilha `audit_trail`: role `INSERT`-only, `REVOKE`, trigger, hash encadeado, `GET /audit/verify-chain`, e a escrita da trilha na rota de nota | **P3-6**, **P4-5**, e é o gatilho declarado da **P4-2** |
| **4** ✅ | seed em escala determinístico, com os seis conjuntos da Linha B nos volumes de `02` §6.1 | — |
| **5** ✅ | `GM_NOTES.md`, a query de referência e o mecanismo do gabarito | **D10** inteira |
| **6** ✅ | fechamento: DoD com prova item a item, a varredura do E1, o registro e a auditoria | **P5-1** |

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

### D12 — a sequência da trilha é atribuída pela aplicação, como a do event store — `DECIDIDA`

A Fase 2 recusou `BIGSERIAL` no event store com um argumento próprio: sequência
de banco **consome número em transação que faz rollback**, e o buraco resultante
seria alarme falso — *"detecção que grita sem defeito é detecção que se aprende a
ignorar"*.

A trilha tem a mesma pergunta e **podia** ter resposta diferente, porque `REVOKE`
e trigger mudam o modelo de ameaça. Examinei nessa direção e a resposta é a
mesma — mas o argumento que a sustenta aqui é outro, e é mais forte:

**1. A cadeia já obriga a serializar, então `BIGSERIAL` não economizaria nada.**
`previous_hash` é o `row_hash` da linha imediatamente anterior: para escrever,
é preciso ler a última linha sob trava. A sequência atribuída pela aplicação sai
de graça dessa trava que já existe. Com `BIGSERIAL` haveria trava **e** buraco.

**2. Com `REVOKE DELETE`, buraco deixa de ter explicação legítima.** No event
store, um buraco podia ser transação abortada; aqui, se a sequência é da
aplicação e a role não pode apagar, buraco significa *alguém passou por fora da
role*. A contiguidade sai de "ruído tolerado" para **sinal**, e é exatamente o
inverso do que se esperaria de "o REVOKE já cuida disso".

**3. `BIGSERIAL` exigiria `USAGE` na sequência para a role restrita.** Uma
permissão a mais numa role cujo propósito é ter o mínimo, para um valor que a
aplicação já sabe calcular.

### D13 — `REVOKE` e trigger, conferidos na fonte, e o que eles NÃO protegem — `DECIDIDA`

Conferido antes de escrever, e não de memória. `02` §4 obriga seis coisas, e a
Fase 2 recusou antecipar as três primeiras dizendo, no cabeçalho da própria
`integrity.py`, que são **Fase 5**:

| `02` §4 | O que a peça 3 entrega |
|---|---|
| 1. tabela dedicada `audit_trail`, separada das operacionais | migration `0004` |
| 2. role `academus_app` com `INSERT` apenas; `REVOKE UPDATE, DELETE, TRUNCATE` | role criada na migration, com `GRANT INSERT, SELECT` e `REVOKE` explícito |
| 3. trigger `BEFORE UPDATE OR DELETE` que levanta exceção incondicionalmente | `fn_audit_trail_imutavel()` |
| 4. `prev_hash` e `row_hash = SHA256(prev_hash \|\| payload canônico)` | primitiva do core, D3 |
| 5. `GET /audit/verify-chain` reportando a primeira quebra | D14 |
| 6. migration controlada | `0004`, versionada |

**O que os dois NÃO protegem, e isso precisa estar dito para ninguém ler
`REVOKE` como garantia total:**

`REVOKE` não alcança quem não passa pela role — superusuário e **dono da
tabela**. O dono pode re-conceder privilégio a si mesmo, e pode
`ALTER TABLE ... DISABLE TRIGGER`; um superusuário pode ainda
`SET session_replication_role = replica` e o trigger não dispara. Nenhuma das
duas coisas é defeito da implementação: é o que privilégio de dono significa.

**A relação entre os dois mecanismos, que é o que fecha a leitura errada:**

| | Cobre | Não cobre |
|---|---|---|
| `REVOKE` + trigger | **prevenção** no caminho normal — a aplicação e quem tem a credencial dela | quem tem privilégio de dono ou de superusuário |
| cadeia de hash | **detecção** de quem reescreveu e **não recomputou** a cadeia — acidente, migração malfeita, edição manual, restauração de backup | truncamento da cauda; e adversário com privilégio **e** o código, que recomputa tudo |

Os dois últimos limites já estavam declarados em `integrity.py` desde a Fase 2, e
**continuam valendo aqui** — são repetidos na trilha em vez de herdados em
silêncio. `REVOKE` sem cadeia deixaria o caminho privilegiado sem nenhuma
testemunha; cadeia sem `REVOKE` deixaria o caminho normal sem impedimento. É por
isso que `02` §4 exige os dois, e não um.

**Uma consequência de ambiente que é do operador, e está dita porque a DoD
depende dela.** `06` T7 exige que *"a role da aplicação não possua `UPDATE`,
`DELETE` ou `TRUNCATE`"*. Hoje a `academus-api` conecta com a **mesma role que
roda as migrations** — a `POSTGRES_USER` do compose, que na imagem oficial é
superusuário. Com uma role só, `REVOKE` não tem efeito nenhum sobre o caminho da
aplicação.

O que a peça 3 faz: cria a role `academus_app` sem `LOGIN`, com `INSERT`+`SELECT`
e `REVOKE` explícito, e **a escrita da trilha faz `SET LOCAL ROLE academus_app`
dentro da própria transação**. Isso torna a restrição operante no caminho da
aplicação sem exigir credencial nova, e o teste de T7 prova a ausência do
privilégio assumindo a role. O que **não** faz: impedir que quem conecta faça
`RESET ROLE`. A separação definitiva é uma segunda credencial no `.env` para a
`academus-api`, e ela é do operador — está registrada como pendência, não como
feito.

### D14 — `GET /audit/verify-chain` entra na superfície antes de existir — `DECIDIDA`

Disciplina da Fase 3, e ela vale aqui: a rota é declarada em
`domains/academus/api_surface.yaml` no mesmo commit em que nasce, e a terceira
direção do `check_api_surface.py` cobra a promoção de `planejada` para
`implementada`.

| | |
|---|---|
| **papel exigido** | `secretaria`. Não há papel de auditor no domínio, e criar um seria pôr papel de **exercício** dentro do adapter — o buraco que a peça 2 da Fase 3 fechou e que `06` T6 cobra |
| **efeito** | **nenhum sobre o exercício**. A rota lê e conta; não escreve, não muda flag, não emite evento |
| **reversível** | não se aplica — não há o que reverter numa leitura |
| **flags** | `[]`. Degradar a verificação de integridade seria o range mentindo sobre a própria trilha |

**`efeito` e `inverso` não vão no YAML, e a ausência é do perfil.**
`check_api_surface.py` tem dois perfis, e os campos `efeito`, `emite`, `inverso` e
`confirmacao` são do perfil do **núcleo** — no perfil de domínio eles são
**proibidos**, porque `emite` ali anteciparia a instrumentação (é a P4-2). Então a
resposta às três perguntas está aqui e no comentário da rota, e o YAML declara o
que o perfil dele conhece: `papeis`, `escopo`, `flags`, `degradacao`, `status`.

**Ela é a primeira rota que lê a trilha, e é `05` §7 que a governa** — integridade
da trilha. Por isso a resposta dela carrega a **posição exata da quebra** (`06`
T7 exige), e nada além: sem despejo de linhas, sem payload de auditoria, sem
conteúdo que `06` T6 varre.

### D15 — o verificador da §7 entra ANTES da promoção, e o vermelho vai para o registro — `DECIDIDA`

A direção (d) do `check_secoes_de_seguranca.py` é gate **só se reprovar de
verdade**. Promover a entrada da §7 no mesmo gesto que cria o verificador
deixaria a direção (d) como prosa: ela nunca teria ficado vermelha, e ninguém
saberia se funciona.

Ordem: `scripts/check_trilha_de_auditoria.py` nasce citando `05` §7 → a checagem
de seções **reprova**, porque a entrada ainda diz "sem mecanismo — Fase 5" → a
saída vermelha é copiada para o registro → **só então** a entrada é promovida.
Vale igual para a §6 na peça 5.

### D16 — o mecanismo contra a reincidência da allowlist — `PROPOSTA`

**Não implementada. A forma está aqui para ser vista antes.**

**O problema, medido e não suposto:** a regra *"script novo que precise ser
executado pelo auditor entra na allowlist por nome, no commit que o cria"* está
escrita **dentro do `readonly_bash.py`**, e o próprio arquivo documenta duas
violações anteriores — H3 da Fase 1, M5 da quarta auditoria da Fase 3. Esta é a
terceira. Três correções, nenhuma impediu a seguinte.

#### A forma

`scripts/check_allowlist_do_auditor.py`, no job `arquitetura`, cruzando **todo
`scripts/*.py` versionado** com os padrões de `ALLOWED`:

| | |
|---|---|
| (a) | script versionado em `scripts/` **ausente** da allowlist e **sem entrada** no registro de exclusão → **reprova** |
| (b) | entrada da allowlist nomeando script que **não existe** → reprova (allowlist que envelheceu afirmando ferramenta que sumiu) |
| (c) | exclusão declarada para script que **está** na allowlist → reprova (a declaração sobra e mente sobre o que acontece) |
| (d) | zero padrões extraídos de `ALLOWED` → reprova (a forma do arquivo mudou, e as outras três passariam por vacuidade) |

**O universo é `scripts/*.py`, e não `check_*.py`.** Restringir aos verificadores
deixaria de fora exatamente os dois que a discussão nomeia — `bench_reconstruction`
e `prova_seed_completo` —, e a pergunta que o mecanismo existe para responder é
sobre **todo script que o auditor poderia precisar rodar**.

#### O registro de exclusão, com motivo por entrada

É a forma do `DESCRITIVO` de `check_gate_coverage.py`: **tudo classificado, e a
terceira classe é declaração explícita.** As entradas que já existem por decisão,
com o motivo que já está escrito no hook:

```text
bench_reconstruction    Postgres, escreve centenas de milhares de linhas, minutos
prova_seed_completo     idem, mais `AURORA_SEED_DATABASE_URL`, e o item pede
                        NÚMERO DE MÁQUINA — reexecutar não confirma
grava_provas_de_container   sobe container: rede e execução na mão do julgador
reancorar_sessao        ESCREVE o sentinela em `.git/`
sobe_sala, demo_fase4, audit_report, …   uma linha cada, com o motivo
```

**O custo de acrescentar é uma frase de motivo**, e é ele que separa *"decidimos
que fica de fora"* de *"ninguém olhou"* — que é a distinção inteira.

#### Três coisas que a proposta precisa que você decida

1. **O universo cobre `scripts/*.sh`?** `start_checkpoint_audit.sh` é o lançador,
   e o auditor nunca o roda. Incluí-lo custa uma entrada; excluí-lo por extensão
   é uma regra a mais para lembrar.
2. **A extração de `ALLOWED` lê o hook por regex ou por AST?** O hook mora em
   `user-scope/hooks/` e é versionado; ler por AST é mais estável, e o padrão é
   uma f-string concatenada — o que torna o AST menos direto do que parece.
3. **P4-11 vale aqui**, e é preciso dizê-lo: este verificador **mora na árvore
   que audita** e lê o hook que constrange o auditor. A direção é aditiva
   (verificador novo, read-only), então a pendência não dispara — mas ele passa a
   ser mais um mecanismo cuja propriedade depende de a árvore auditada não o
   enfraquecer.

**O que a proposta NÃO resolve:** o item 1 da DoD continua sustentado pelo CI. A
exclusão de `prova_seed_completo` é decisão, e o mecanismo só a torna **visível e
cobrada** — ele não a desfaz. Ver a §10.4.

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

### 4.3 Peça 3 — a trilha, e a direção (d) exercida pela primeira vez

**Entregue:** migration `0004`, `domains/academus/audit/trilha.py`,
`GET /audit/verify-chain`, o verificador de `05` §7 com treze eixos de prova
negativa, e dezoito testes de T7 contra Postgres real.

#### A direção (d) reprovou antes da promoção — medido, e na ordem

Você repetiu a exigência porque se a promoção viesse antes o gate nunca teria
reprovado. Veio depois, e a saída é esta:

```text
P4-12 - secao de 05_SECURITY_REQUIREMENTS com mecanismo ou destinatario

  scripts/check_trilha_de_auditoria.py cita `05` §7 e nao esta declarado como
  mecanismo dela. A entrada diz que a secao espera a Fase 5, e ja ha verificador
  citando-a: e a promocao que esta faltando. [...]

rc=1
```

**E ela não reprovou na primeira tentativa, o que revelou um limite.** Com o
verificador recém-escrito e ainda **não versionado**, a checagem passou verde: o
universo vem de `git ls-files`, e arquivo fora do índice é invisível. Um
`git add -N` depois, reprovou.

**Não é defeito a corrigir, é escopo a declarar** — arquivo não versionado não
roda no CI de ninguém, e tratá-lo como mecanismo faria o registro afirmar
cobertura que não existe em lugar nenhum. O que muda é o procedimento, e ele está
escrito no cabeçalho do verificador: quem escreve verificador novo o adiciona ao
índice antes de rodar a checagem. No commit isso é automático; no CI a árvore já
está commitada.

**Só depois disso a entrada foi promovida.** `05` §7 sai desta fase com mecanismo
de verdade, e a §6 continua sendo a única sem — com destinatário na peça 5.

#### O que o verificador da §7 prova, e o que ele não prova

Ele confere que o **mecanismo continua declarado**: tabela dedicada, os três
verbos revogados **por nome**, trigger incondicional, colunas de cadeia, rota
implementada, e a ausência de modelo ORM. Que ele **funciona** é o que os testes
de T7 provam contra Postgres real.

A divisão não é arbitrária: apagar o `REVOKE` de uma migration futura **não
derruba teste nenhum** que rode sobre base já migrada — a tabela mantém as
permissões de ontem —, e o defeito viajaria até alguém recriar a base.

**Um probe mediu uma frouxidão minha e ela foi corrigida.** A migration tem
`REVOKE ALL` **e** o `REVOKE UPDATE, DELETE, TRUNCATE` explícito; o verificador
aceitava `ALL` como suficiente, então apagar a linha explícita não acusava nada.
`ALL` revoga os três de fato e **não diz quais** — nomeados, o diff fala a língua
da spec e a remoção de um deles fica visível em revisão. O verificador passou a
exigir os três por nome, e há probe para cada metade.

#### T7, os três critérios, e por que são quatro testes

| Critério | Prova |
|---|---|
| `UPDATE` e `DELETE` falham **por trigger** | duas tentativas, e a exceção carrega `append-only` |
| a role **não possui** `UPDATE`/`DELETE`/`TRUNCATE` | `has_table_privilege` — pergunta ao **catálogo**, não ao comportamento: mesmo com o trigger desligado, a role continuaria sem o privilégio |
| — | e o **par**: a role **possui** `INSERT` e `SELECT`. Sem ele, uma role sem privilégio nenhum passaria nos três `assertFalse` e a trilha seria inescrevível |
| adulteração induzida reporta a **posição** | quatro adulterações: campo, `payload` (a nota trocada), linha removida do meio, e o **truncamento da cauda que NÃO é detectado** |

**O último é o limite declarado sendo exercido, e não apenas escrito.**
`integrity.py` diz desde a Fase 2 que apagar as últimas N linhas deixa cadeia
íntegra e sequência contígua. O teste afirma isso: se ficar vermelho um dia,
alguém resolveu o problema e o registro precisa parar de dizer que ele existe.

A adulteração é feita **desabilitando o trigger** — que é exatamente o limite que
a D13 declara. É o ponto: a cadeia enxerga o que a prevenção não impediu.

#### A P4-5 e a P3-6 fechadas, e os dois vermelhos que as anunciaram

Medido na suíte, antes de eu tocar em qualquer um dos dois:

```text
FAIL: test_P4_5_nota_de_aluno_INEXISTENTE_e_aceita_hoje
FAIL: test_grades_student_id_continua_sem_FK
```

**Os dois ao mesmo tempo são o que distingue "a P4-5 fechou" de "alguém pôs uma
FK".** O primeiro é comportamento de rota, o segundo é esquema; a D5 exigiu o
par, e o par é o que ficou vermelho. Os dois foram reescritos para afirmar o
estado novo, com o nome antigo citado no corpo — quem ler daqui a três fases
encontra o que eles diziam antes.

A **P3-6** fecha com a nota e a linha de trilha na mesma transação, e a linha
carrega os dez campos que `02` §4.1 exige. Há teste para cada um, e um a mais
para o `within_window`: a fixture põe a janela de retificação em fevereiro de
2027, o teste roda hoje, e `False` é a resposta certa — um `True` diria que a
comparação não está olhando a janela que a Linha B inteira depende.

#### A P4-2 não venceu, e agora está medido

O gatilho é *o primeiro `append` fora do `inject-engine`*. Medido nesta peça, e
não assumido:

```text
grep de `.append(` em domains/**.py  →  nenhuma chamada a store.append
EventStore importado em domains/     →  degradacao.py (lê), processo.py (monta)
```

A trilha **não é o event store** — é tabela de domínio com cadeia própria. A
condição não ocorreu, e a pendência segue na Fase 6 com o gatilho intacto, como
redatado. O comentário de `app.py` que dizia "Fase 8" foi corrigido para Fase 6,
com a fonte.

#### Dois achados operacionais, e o segundo é do operador

**A migration exige `CREATEROLE`.** Medido ao aplicá-la com uma role de migration
sem esse atributo: `CREATE ROLE academus_app` falha com uma mensagem que não diz o
que fazer. A migration passou a capturar `insufficient_privilege` e a explicar as
duas saídas — rodar com role que tenha `CREATEROLE`, ou criar a role **uma vez**
como superusuário, e a partir daí o `IF NOT EXISTS` a encontra.

**A role da aplicação e a role das migrations são a mesma, e isso limita o que
`REVOKE` significa hoje** — é a **P5-3**, aberta abaixo.

### 4.4 Peça 4 — o seed em escala, e os seis conjuntos como produto

**Entregue:** `domains/academus/seed/{dataset,carga,linha_b}.py`,
`scripts/prova_seed_completo.py`, e onze testes — determinismo nas duas direções
e a partição dos seis conjuntos.

#### Os dois itens da DoD, medidos em escala completa

```text
maquina  Windows-11-10.0.26200-SP0        python 3.12.10       data 2026-08-18
escala   28.000 alunos · 1.200 professores · 60 cursos · 8 semestres
linhas   3.543.783        (1,12 M notas · 1,12 M matriculas · 1,12 M historicos)

  rodada 1   gerar 1,57 s   COPY 148,76 s   dump 4,41 s   seed 150,32 s
  rodada 2   gerar 2,01 s   COPY 157,37 s   dump 4,61 s   seed 159,39 s

  item 1  seed completo em < 5 min:  PASSA — 159,4 s de 300 s
  item 2  dataset byte-identico:     PASSA — 20 tabelas, SHA-256 por tabela

  audit_trail  c48adb205c44cf03810010836105b4efb423abbbb68fa54cf12ccb830906bc84
  students     b154960b58f49eb6cdf655dd397020beb4243663be906ae7247dc2985a09eaed
```

Máquina, data e stack ao lado do número — a exigência de forma que `06` T3 fixou
para a curva da Fase 2, e que vale igual aqui. **Os dois SHAs estão impressos e
não só comparados:** quem tiver o mesmo seed os reproduz sem confiar nesta saída.

#### As duas direções do determinismo

`test_o_mesmo_seed_produz_o_mesmo_dump` é a metade óbvia. **A que discrimina é a
outra:** seeds diferentes têm de produzir SHAs diferentes em `students`, `users`,
`grades` e `audit_trail`. Sem ela, um gerador que ignorasse o `RANDOM_SEED`
passaria no primeiro teste — "duas execuções iguais" é verdade trivial para quem
sempre produz a mesma coisa.

E há uma terceira afirmação, na direção oposta: **`academic_calendar` NÃO muda**
com outro seed. Ele deriva de `ANO_BASE`, e um calendário sorteado poria a janela
de retificação em data aleatória — `within_window` deixaria de ser comparável
entre execuções, e a Linha B inteira depende dessa comparação.

**O terceiro teste olha o fonte, e não o resultado:** duas execuções no mesmo
segundo passariam na igualdade mesmo com `now()` no caminho, e o defeito só
apareceria na virada do dia. Ele é **por AST**, e a razão foi medida: a primeira
versão procurava a string `datetime.now(` e reprovou contra o próprio docstring
do gerador, que cita a chamada para dizer que ela não existe. É a mesma razão
pela qual `06` T1 exige a fronteira core/adapter verificada por AST, *"não por
grep"*.

#### Os seis conjuntos são o produto, e "distinguível" virou uma partição

Seis consultas que devolvessem as contagens certas ainda poderiam se sobrepor —
uma linha contada em dois conjuntos, outra em nenhum. O que os testes provam é
mais forte:

| | |
|---|---|
| **contagem** | 22 · 11 · 34 · 60 · 18 · N — os números de `02` §6.1 |
| **disjunção** | nenhuma linha aparece em dois conjuntos |
| **cobertura** | a união é a trilha inteira: 3.145 = 22+11+34+60+18+3.000 |

Sem as duas últimas, dois conjuntos indistinguíveis passariam — o exercício teria
cinco, e ninguém descobriria até a sala.

**A ligação que faz os ambíguos serem ambíguos.** `02` §6.1 pede *"aprovador que
também aparece nos indevidos"*, e os indevidos não têm autorização nenhuma — a
ligação só pode ser pela **conta**: o aprovador das 11 autorizações é a mesma
conta docente que assina os 22. Sem isso, os 11 seriam apenas "fora da janela com
autorização", indistinguíveis dos 34.

**E há um teste das assinaturas, não só das contagens:** um gerador que
produzisse 22 linhas sem as seis características de `02` §6.1 passaria na
contagem e daria à sala um conjunto que não se parece com o que o `GM_NOTES`
descreve. O teste confere as seis — IP de laboratório, 22h–02h, sempre elevando,
sem autorização, fora da janela, conta única — e que os alunos afetados são no
máximo oito, que é o "mesmo grupo".

**As consultas moram em `domains/academus/seed/linha_b.py` e não no teste**,
porque são o produto: `02` §6.3 manda o `GM_NOTES.md` trazer a query de
referência, e escrita dentro do teste ela seria inacessível ao gerador da peça 5
— ou escrita duas vezes, que é a classe que este projeto já pagou.

#### Dois defeitos meus, e o segundo mudou o desenho

**A carga assumia a role restrita para o banco inteiro**, e a primeira execução
respondeu `permission denied for table academic_calendar`. **O erro estava
certo:** `academus_app` tem `INSERT`+`SELECT` em `audit_trail` e nada nas outras
dezenove — que é exatamente o que `02` §4 item 2 pede. Uma role que pudesse
semear o banco inteiro não seria a role da trilha. Agora ela é assumida só em
volta do `COPY` da trilha, com `RESET ROLE` logo depois — porque `SET LOCAL` vale
até o fim da **transação**, e hoje `audit_trail` é a última do dicionário: sem o
reset, a dependência de ordem reapareceria no dia em que alguém reordenasse.

**E o hook pegou uma colisão de convenção do core.** `seeded_random("academus.
alunos")` — a forma que `range_core.determinism` documentava desde a Fase 2 — é
**inexprimível dentro de `domains/`**: o invariante 2 recusa toda string
`(academus|prontus|core).algo`, porque é a forma de um nome de flag. Esta peça foi
o primeiro consumidor real do seed por escopo, e o bloqueio veio na primeira
escrita. O separador passou a ser `:`, e o core documenta `academus:alunos`.
Trocar o separador muda os sub-seeds derivados, e isso é inofensivo: não havia
consumidor antes.

#### O limite da P5-3 saiu da pendência e virou teste

Você pediu que ele ficasse onde quem lê o item da DoD encontre, na forma do
truncamento da cauda. São duas coisas:

- **`OQueT7NaoProva`**, em `tests/test_trilha_de_auditoria.py`: afirma que a role
  **que conecta** ainda possui `UPDATE` sobre `audit_trail`, e que `RESET ROLE`
  a traz de volta. Os dois ficam **vermelhos** no dia em que a segunda credencial
  existir — e a mensagem de falha diz que isso é a P5-3 fechando;
- o **cabeçalho do arquivo** passa a dizer o limite, porque é ali que alguém lê
  "T7 passa": o segundo critério é sobre `academus_app`, e a `academus-api` não
  conecta como ela.

**Sobre o gatilho caber como item de DoD:** ele não cabe sem `spec-change`.
`07` não declara fase de deploy — a lista de fases vai de contratos a
observabilidade, e nenhuma delas produz o deploy que `05` §6 governa. Acrescentar
item de DoD é editar `07`, que é spec, e isso é PR próprio com aprovação humana.
O que fiz sem spec-change foi pôr o gatilho **na entrada da §6 do registro de
seções** — que é CODE, e que a **peça 5 obrigatoriamente toca** para promover
aquela seção. Assim ele é lido na hora em que alguém está mexendo em deploy e
exclusão de gabarito, que é o momento certo. Se você quiser o item em `07`
também, é `spec-change` e eu abro.

---

### 4.5 Peça 5 — o gabarito, e três vazamentos que os testes acharam

**Entregue:** a entrada de `scenarios/` no `.gitignore` com o motivo,
`scripts/check_gabarito_fora_do_git.py` com dez eixos de prova negativa,
`domains/academus/seed/{gabarito.py,GM_NOTES.template.md}`, e onze testes que
**produzem** os dois artefatos e os julgam.

#### O que é gerado e o que é escrito à mão — a sua pergunta

| | |
|---|---|
| **escrito à mão**, versionado | a prosa do template — por que cada conjunto existe, por que os 34 parecem suspeitos, como conduzir. E a query de referência. **Nada disso é gabarito**: é reafirmação de `02` §6.1 e §6.2, e a spec é pública |
| **gerado**, fora do Git | todo fato concreto — `case_id`, a conta comprometida, o grupo de alunos, os números de processo, as datas, os volumes |

**Você estava certo que a metade escrita à mão é onde o gabarito vaza sem a
checagem ver.** O linter de T8 não pega: ele confere que todo fato do `GM_NOTES`
existe no `ground_truth.yaml`, e um caso escrito à mão **existe** lá. Então há
duas guardas, e a segunda é derivada em vez de declarada:

- **estática** — o verificador recusa token com forma de identificador de
  gabarito dentro do template **e dos módulos versionados do gerador**;
- **dinâmica** — renderizar com dois seeds e exigir que nenhum identificador que
  aponte para linha sobreviva aos dois. O que sobrevive está no template por
  construção: o teste **descobre** o que é escrito à mão em vez de confiar na
  declaração acima.

#### Três vazamentos, e os três foram achados por teste

**1. A conta comprometida era constante no repositório público.**
`linha_b.py` nasceu com `CONTA_DOS_INDEVIDOS` apontando para um identificador
literal. Quem lesse o repositório sabia metade do gabarito, e o `.env` não
protegia nada. A conta passou a ser **sorteada** e a chegar como parâmetro.

**2. As identidades da Linha B eram posicionais.** `professores[0]`,
`alunos[:8]` — a conta comprometida e o grupo alvo eram os mesmos com qualquer
seed. Foi `test_os_fatos_sao_DISTINTOS_entre_os_dois_seeds` que achou, **e ele só
existe porque você pediu a direção inversa da prova na peça 4**. Todas as
identidades passaram a sair de `sample`/`choice` do fluxo semeado.

**3. A ordem da trilha revelava os conjuntos — o mais silencioso dos três.** Os
conjuntos eram gravados em bloco: as 22 primeiras linhas de `audit_trail` eram
sempre os indevidos, as 11 seguintes os ambíguos. **O participante investiga a
trilha**, então o gabarito estava legível no artefato que ele abre — sem `.env`,
sem repositório, só contando linhas. Achado por
`test_o_MAPEAMENTO_caso_para_fato_muda_com_o_seed`. O gerador passou a
**embaralhar** a ordem com o fluxo semeado, e o determinismo continua.

**Os três têm a mesma forma:** o gabarito não estava no arquivo que a decisão
protegia. Estava no gerador, na posição e na ordem — lugares que "não versionar
`scenarios/`" não alcança.

#### A forma da prova (D10.3), e o limite nos dois lugares

O CI **produz** os dois artefatos de um seed de teste e os julga: o `GM_NOTES`
contém a query, **a query executada** devolve os 22 e nenhum ambíguo (conter o
texto sem executá-lo provaria interpolação de string), todo fato citado existe no
`ground_truth`, e o `ground_truth` gerado **valida contra o contrato do próprio
projeto**.

Duas execuções com seeds diferentes: os seis volumes iguais e os números de
`02` §6.1, e o mapeamento caso → conteúdo distinto.

**O limite está no cabeçalho do verificador e no cabeçalho do arquivo de teste**,
que são os dois lugares onde alguém pergunta "o que exatamente isto provou?": o
artefato gerado com o `RANDOM_SEED` de **produção** nunca é visto por CI nenhum,
e não precisa ser — a propriedade provada é do gerador. E há um limite que
nenhuma checagem alcança, dito em vez de suposto: nada impede alguém de publicar
o artefato renderizado fora do Git, por e-mail ou captura de tela. Isso é
disciplina de operação, não propriedade de repositório.

#### A medição em escala completa, refeita depois do embaralhamento

```text
  item 1  seed completo em < 5 min: PASSA — 144,3 s de 300 s
  item 2  dataset byte-identico:    PASSA — 20 tabelas, SHA-256 por tabela

  audit_trail  56a85082ddf6e1ef7764cfae491aba5f281c4965c3b33814a6b08ed5e28ee26f
  students     b154960b58f49eb6cdf655dd397020beb4243663be906ae7247dc2985a09eaed
```

**O SHA de `students` não mudou e o de `audit_trail` mudou**, e o par confirma o
escopo do embaralhamento: ele reordena a trilha e não toca o resto.

#### A quarta vez que o texto que explica a regra reprovou contra ela

Aconteceu três vezes nesta fase e uma quarta aqui: o teste de relógio reprovou
contra o docstring que cita `now()`; a guarda de placeholder reprovou contra a
instrução que cita as chaves duplas; o verificador de gabarito reprovou contra o
comentário que citava a conta como exemplo do que não fazer. **A correção nunca é
afrouxar a regra** — é a checagem olhar a estrutura (AST, forma do placeholder)
ou o texto deixar de conter a instância. Comparação por texto pega o texto que
fala sobre ela.

#### Uma decisão de contrato que virou pendência

`contracts/ground_truth.schema.yaml` fecha `line_b_case.set` em **três** valores,
e `02` §6.1 tem **seis** conjuntos. Ruído de manutenção e credenciais
compartilhadas ficam no dataset e **fora de `line_b_cases`**: rotulá-los
`legitimo_aparencia_suspeita` faria o gabarito afirmar algo falso, e alargar o
enum seria mudar semântica dentro da mesma `schema_version`, que `04` §4 proíbe.
É a **P5-4**, com destinatário na Fase 7.

---

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
| P5-1 | ~~docstring de `scripts/sobe_sala.py` manda rodar um script que não existe~~ | ✅ **FECHADA** no commit de fechamento |
| P5-2 | a trilha declara a categoria "declarações do exercício" e ela não tem produtor | **Fase 6** — ver abaixo |
| P5-3 | a role da aplicação e a das migrations são a mesma, e `REVOKE` não alcança quem conecta | **operador** — ver abaixo |
| P5-4 | os seis conjuntos de `02` §6.1 não cabem nos três valores do enum do contrato | **Fase 7** — ver abaixo |

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


#### P5-3 — a role da aplicação e a das migrations são a mesma

**Aberta implementando a D13, e ela é o que separa o mecanismo do efeito dele.**

`06` T7 exige que *"a role da aplicação não possua `UPDATE`, `DELETE` ou
`TRUNCATE`"*. A `academus_app` da `0004` não possui nenhum dos três, e há teste
perguntando ao catálogo do Postgres. **Mas a `academus-api` não conecta como
`academus_app`:** ela conecta com a `POSTGRES_USER` do compose, que é a mesma
role que roda as migrations e que, na imagem oficial, é **superusuária**.

Com uma role só, `REVOKE` não tem efeito sobre o caminho da aplicação — e ler a
DoD como "está feito" seria a leitura errada que a D13 existe para impedir.

**O que a peça 3 fez, e é mais que nada:** a escrita da trilha faz
`SET LOCAL ROLE academus_app` **dentro da transação**. A restrição passa a valer
no caminho que escreve, sem credencial nova, e `SET LOCAL` volta sozinho no fim
da transação — sem ele, a conexão voltaria ao pool com a role trocada, e o
defeito apareceria numa rota sem relação com trilha.

**O que ela não faz:** impedir `RESET ROLE`. Quem conecta continua podendo. Isso
é disciplina, não impedimento — a distinção da §1.6 da Fase 1.

**A separação definitiva é do operador**, e é por isso que a pendência é sua e
não minha: exige uma **segunda credencial** para a `academus-api` — role com
`LOGIN`, senha no `.env`, `DATABASE_URL` própria no compose. Não posso escrever o
`.env`, e uma senha em arquivo versionado seria pior que o problema.

**Gatilho: o primeiro deploy destinado a exercício com participante real.** Até
lá, o que existe é uma stack de desenvolvimento onde a distinção não muda risco
nenhum. A partir dali muda: `05` §6 põe o deploy atrás de túnel, e a role da
aplicação passa a ser alcançável por quem estiver dentro dele.

**O que eu preparei para essa hora:** a role já existe, os `GRANT`/`REVOKE` já
estão certos, e o código já assume a role. O que falta é a credencial — uma
variável, e não uma refatoração.

#### P5-4 — o enum do contrato tem três valores e `02` §6.1 tem seis conjuntos

**Aberta gerando o `ground_truth.yaml`, ao mapear os conjuntos para o contrato.**

`contracts/ground_truth.schema.yaml` fecha `line_b_case.set` em
`indevido_comprovado`, `ambiguo` e `legitimo_aparencia_suspeita`. `02` §6.1 nomeia
**seis** conjuntos, e `02` §6.2 dá `defensibility` 0.0 a *"legítimo (inclusive os
de aparência suspeita, **manutenção e delegação**)"* — o que implica que os seis
são casos.

**O que a peça 5 fez, e por quê:** ruído de manutenção e credenciais
compartilhadas ficam no **dataset** e fora de `line_b_cases`. As duas
alternativas foram recusadas com motivo:

| Alternativa | Por que não |
|---|---|
| rotulá-los `legitimo_aparencia_suspeita` | o gabarito afirmaria algo falso — que eles *parecem* suspeitos à primeira vista —, e a calibração da Fase 6 os trataria como os 34, misturando dois erros que `02` §6.2 manda separar |
| alargar o enum | é mudar semântica dentro da mesma `schema_version`, e `04` §4 proíbe |

**A consequência, dita em vez de escondida:** uma equipe que classifique uma
linha de manutenção como suspeita não tem caso no gabarito contra o qual ser
pontuada. Hoje isso não custa nada — a calibração é da Fase 6 e o pack é da Fase
7 —, e passa a custar quando o Brier for calculado.

**Destinatário: Fase 7**, que é a dona do pack e do `ground_truth.yaml` completo.
**Gatilho: o commit em que o primeiro `assessment` for pontuado contra o
gabarito** — que é quando "caso sem entrada" deixa de ser assimetria de modelo e
vira lacuna de pontuação. A saída provável é uma `schema_version` nova, e ela é
decisão daquela fase e não desta.

---

## 7. O fechamento — a DoD com prova, item a item

`CLAUDE.md` diz que uma fase só fecha quando **todos** os itens da Definition of
Done passam. O quadro abaixo é o de `07` Fase 5 com a prova de cada um — não a
afirmação de que passou.

| # | Item de `07` Fase 5 | Prova |
|---|---|---|
| 1 | Seed completo em < 5 min | `scripts/prova_seed_completo.py` — **144,3 s de 300 s**, 3.543.783 linhas, Windows-11-10.0.26200-SP0 · python 3.12.10 · 18/08/2026 |
| 2 | Mesmo `RANDOM_SEED` produz dataset byte-idêntico | o mesmo script: **20 tabelas com SHA-256 igual** em duas rodadas. E as duas direções na suíte: mesmo seed → mesmo dump; seeds diferentes → dumps diferentes |
| 3 | `UPDATE` e `DELETE` em `audit_trail` falham por trigger **e** por permissão de role | `tests/test_trilha_de_auditoria.py::TrilhaEhAppendOnly` — **quatro** testes: trigger recusando os dois verbos, `has_table_privilege` negando os três à role, e o par que impede o terceiro de virar superstição (a role **possui** `INSERT` e `SELECT`) |
| 4 | `GET /audit/verify-chain` detecta adulteração induzida | `CadeiaDetectaAdulteracao` — campo alterado, `payload` alterado (a nota trocada), linha removida do meio, cada um reportando a **posição exata**; e a rota pelo stack ASGI, com papel, 401 e 403 |
| 5 | Os seis conjuntos da Linha B nos volumes especificados | `SeisConjuntosDaLinhaB` — 22 · 11 · 34 · 60 · 18 · N, **disjuntos** e cuja **união é a trilha inteira**, aferidos contra `02` §6.1 e não contra o gerador (M2). Mais as seis características, e não só as contagens. **Limite: a partição é exercida em `ESCALA_REDUZIDA`** — os cinco conjuntos plantados não escalam, e o que muda com a escala é só o volume de fundo (L1) |
| 6 | `GM_NOTES.md` contém a query de referência que separa indevidos de ambíguos | `tests/test_gabarito.py` — o CI **produz** o artefato e o julga: o texto está lá, e a query **executada** devolve os 22 e nenhum dos 11 |

### 7.1 O que o item 3 NÃO prova — e isto está na linha dele de propósito

**T7 prova a propriedade da role `academus_app`, e não a da aplicação.** A
`academus-api` não conecta como ela: conecta com a `POSTGRES_USER`, que roda as
migrations, é dona da tabela e, na imagem oficial, é superusuária. Enquanto for
assim, `REVOKE` não alcança o caminho da aplicação, e **`RESET ROLE` está a um
comando de distância** do `SET LOCAL ROLE` que a escrita da trilha assume.

Quem lê "o item 3 passa" e conclui que a aplicação não pode alterar a trilha
conclui algo falso. **O que segura ali é o trigger** — que recusa a todos,
inclusive ao dono — **e a cadeia**, que torna visível a reescrita de quem
desabilitar o trigger.

O limite é **exercido e não só escrito**: `OQueT7NaoProva` afirma que a role que
conecta ainda possui `UPDATE` e que `RESET ROLE` a traz de volta. Os dois ficam
vermelhos no dia em que a segunda credencial existir, e a mensagem de falha diz
que isso é a **P5-3** fechando. É a mesma forma do
`test_truncamento_da_cauda_NAO_e_detectado`.

### 7.2 Os critérios de aceitação, e o que ficou fora

| Critério | Estado |
|---|---|
| `06` **T7** — auditoria imutável | os três critérios, com quatro testes; o limite da role declarado acima |
| `06` **T8** — determinismo e gabarito | os quatro critérios: dataset idêntico, os seis conjuntos, a query devolvendo exatamente os 22, e todo fato do `GM_NOTES` existindo no `ground_truth` |
| `06` **T6** — isolamento de papel (Fases 4–5) | a rota nova exige `secretaria`; 403 para aluno, 401 sem token. **A varredura recursiva de payload continua sendo a da Fase 4** — a rota de verificação devolve três campos e nenhum deles é conteúdo de trilha |
| `06` **T15** — segurança transversal | `Faker` pinado com fecho conferido; IPs só de RFC 5737; nenhum serviço novo exposto |

---

## 8. O inventário do fechamento — por destinatário

| Fechadas nesta fase | Onde |
|---|---|
| **P3-6** — nota gravada antes de a trilha existir | peça 3: nota e trilha na mesma transação, com os dez campos de `02` §4.1 |
| **P4-5** — `grades.student_id` aceita aluno inexistente | peça 3: o par rota 404 + FK, anunciado por **dois** testes vermelhos ao mesmo tempo |
| **P4-12** — três seções de `05` sem verificador e sem declaração | peça 1: registro com cinco direções; §7 promovida na peça 3 e §6 na peça 5. **As oito seções têm mecanismo** |
| **P5-1** — a docstring do `sobe_sala.py` | fechada no commit de fechamento, e a classe registrada |

**Abertas, e para quem elas vão:**

| Destinatário | Id | O que ela cobra | Gatilho |
|---|---|---|---|
| **Fase 6** | P4-2 | emitir evento sem declarar `emite` não tem guarda | *o primeiro `append` fora do `inject-engine`* — **medido nesta fase: não ocorreu**, nenhuma chamada em `domains/` |
| **Fase 6** | P5-2 | a categoria "declarações do exercício" não tem produtor | o commit em que a primeira ação `declare_*` nascer |
| **Fase 7** | P5-4 | seis conjuntos, três valores de enum | o commit em que o primeiro `assessment` for pontuado contra o gabarito |
| **operador, sem fase** | P5-3 | `REVOKE` não alcança a role que conecta | o primeiro deploy destinado a exercício com participante real |
| **condição, sem fase** | P4-7, P4-8, P4-11 | herdadas da Fase 4, sem mudança | inalterados |
| **Fase 8** | P4-4, P4-6, P2-6 | herdadas, sem mudança | inalterados |

**A P4-2 foi redatada e não empurrada**, e a diferença está medida: o gatilho
continua sendo *o primeiro `append`*, e a Fase 5 provou que ele não aconteceu
aqui — a trilha de `02` §4 é tabela de domínio com cadeia própria, e não o event
store. Se a Fase 6 também não o produzir, ela desce de novo.

**A P5-3 é a única sem fase, e é a única do operador.** O gatilho não cabe como
item de DoD sem `spec-change`: `07` não declara fase de deploy. Ele viaja na
entrada da §6 do registro de seções — que é CODE, e que quem mexer em deploy e em
exclusão de gabarito tem de tocar.

---

## 9. O que a fase aprendeu sobre o próprio método

### 9.1 O texto que explica a regra reprova contra ela — seis vezes, e é padrão

Não é coincidência. Aconteceu **seis vezes nesta fase**, em seis mecanismos
diferentes:

| # | A regra | O que ela reprovou |
|---|---|---|
| 1 | o teste que proíbe leitura de relógio no gerador | o **docstring** do gerador, que cita `datetime.now(` para dizer que ele não existe |
| 2 | a guarda de placeholder não substituído | a **instrução de edição** do template, que cita as chaves duplas |
| 3 | o verificador de gabarito, forma de identificador | o **comentário** que citava a conta como exemplo do que não fazer |
| 4 | o mesmo verificador, sobre os módulos | o comentário de `dataset.py` que citava a conta antiga |
| 5 | a direção (e), afirmação de que o gabarito é versionado | o **texto corrigido**: *"não é versionado"* contém *"é versionado"* |
| 6 | a mesma direção (e) | o **arquivo de prova**, que precisa plantar a afirmação para testá-la |

**A correção nunca foi afrouxar a regra.** Foram três formas, e as três são a
mesma ideia:

- **olhar a estrutura em vez do texto** — AST para a chamada de relógio, forma do
  placeholder em vez da abertura `{{`, negação filtrada por janela;
- **o texto deixar de conter a instância** — o comentário passou a dizer "a
  primeira da lista" em vez do identificador;
- **autoexclusão declarada** — o verificador e sua prova saem do próprio
  universo, com o motivo escrito, como `check_secoes_de_seguranca.py` já
  precisara.

**Por que isto merece seção e não linha.** Um verificador de texto tem uma
superfície que nenhum outro tem: **ele também é texto**, e o texto que o explica
vive perto dele. Toda vez que a regra é sobre conteúdo escrito, o material da
explicação é material da violação. A Fase 6 traz `observability_hooks.yaml`,
rubricas versionadas e binding evento→objetivo — três mecanismos que se explicam
citando o que proíbem. **Comece sabendo:** se a checagem é sobre texto, ela
precisa de estrutura ou de autoexclusão **antes** da primeira execução, e não
depois.

### 9.2 Uma decisão de fronteira protege o arquivo, e o conteúdo vaza por onde ela não nomeia

A D10 decidiu *"`scenarios/` fica fora do Git"*, e a decisão está certa. Ela
protege **o arquivo**. O gabarito vazou por **três caminhos que ela não nomeia**,
e os três foram achados por teste e não por leitura:

| Caminho | O que vazava |
|---|---|
| **o gerador** | a conta comprometida era constante num módulo versionado |
| **a posição** | as identidades eram por índice: mesma conta e mesmo grupo com qualquer seed |
| **a ordem** | os conjuntos gravados em bloco — as 22 primeiras linhas da trilha eram sempre os indevidos |

**O terceiro é o mais grave**, e é o que resume a lição: o gabarito estava
legível no **artefato que o participante investiga**, por contagem de linhas, sem
`.env` e sem repositório. Nenhuma regra sobre versionamento alcança isso.

**A generalização:** uma fronteira declarada sobre *onde o arquivo mora* não diz
nada sobre *o que o conteúdo revela*. As duas perguntas são diferentes, e a
segunda só tem resposta quando alguém a formula como propriedade verificável —
aqui, "nada que identifique um caso pode sobreviver a dois seeds". Foi essa
pergunta, e não a decisão, que achou os três.

### 9.3 Escalar sem varrer é a metade barata — e a varredura não impede a terceira vez

`CLAUDE.md` foi corrigida em `3dd9d18`: de "repositório privado" para "este
repositório é público". A mesma afirmação vivia em **mais três lugares**, e
ficou — `.gitignore`, `docs/process/WORKFLOW.md`, e duas vezes em
`.claude/agents/scenario-designer.md`, onde **instruía um subagente a versionar
o gabarito**.

É a classe do E1, e o custo dela aqui foi maior que o usual: a definição de
subagente não é documentação, é instrução executável por outro agente.

**A varredura acha a segunda ocorrência; não impede a terceira.** O critério
usado está escrito no registro e no verificador, e a direção (e) do
`check_gabarito_fora_do_git.py` passou a executá-lo: documento versionado que
**afirme** que o gabarito é versionado reprova, com allowlist declarada para
quem cita a frase antiga de propósito.

### 9.4 A direção inversa da prova é a que descobre

Três dos achados desta fase vieram de testes que ninguém teria escrito para
"provar que funciona":

- **seeds diferentes produzem SHAs diferentes** — pedido pelo operador na peça 4,
  e foi ele que achou o vazamento posicional;
- **o mapeamento caso → conteúdo muda com o seed** — achou o vazamento de ordem;
- **a role possui `INSERT` e `SELECT`** — o par que impede os três `assertFalse`
  de T7 de passarem com uma role sem privilégio nenhum.

A forma comum: **o teste que afirma o que NÃO pode ser igual**, ao lado do que
afirma o que deve ser. Sem ele, um mecanismo que ignora sua própria entrada passa
por vacuidade.

---

## 10. A auditoria de checkpoint — PASS, e as duas correções da rodada

**PASS na primeira rodada**, com dois MEDIUM e dois LOW. Os dois MEDIUM foram
corrigidos nesta rodada; os dois LOW ficam, e o motivo de cada um está abaixo.

### 10.1 M1 — a allowlist do auditor, e a terceira reincidência da mesma regra

Os três verificadores da fase — `check_secoes_de_seguranca`,
`check_trilha_de_auditoria`, `check_gabarito_fora_do_git` — nasceram fora da
allowlist do `readonly_bash.py`. A regra existe e está escrita **dentro do
próprio arquivo**: *"script novo que precise ser executado pelo auditor entra
aqui por nome, no commit que o cria"*.

**Corrigido: os três entram, com as três provas negativas**, e o critério de
admissão é o mesmo dos que já estavam lá — o auditor **não consegue responder por
leitura**. Ler oito seções contra 41 verificadores a olho, ou uma migration de
300 linhas procurando `REVOKE`, ou cinco arquivos procurando forma de
identificador, não é auditoria.

**Mas a correção não é o achado.** O arquivo documenta **duas** ocorrências
anteriores dentro dele mesmo — o H3 da Fase 1 e o M5 da quarta auditoria da Fase
3 — e esta é a terceira. **Três correções, e nenhuma impediu a seguinte.** A
regra está no lugar certo e depende de alguém lê-la no momento certo, que é a
definição de disciplina, e a §1.6 da Fase 1 separa disciplina de impedimento.

A proposta de mecanismo está na **D16**, e ela não está implementada.

### 10.2 M2 — a guarda em vez da conferência

O teste que julga os volumes da Linha B lia as **constantes do gerador** — quer
dizer, comparava o gerador consigo mesmo. Trocar `INDEVIDOS = 22` por `20`
manteria tudo verde, e o dataset deixaria de cumprir `02` §6.1 sem nada ficar
vermelho.

**A conferência à mão satisfaz e não segura.** O auditor conferiu os cinco
números e eles estavam certos; a rodada seguinte dependeria de alguém conferir de
novo.

**Fechado com a forma do `check_spec_flags.py`:**
`scripts/check_volumes_da_linha_b.py` lê a tabela de `02` §6.1 e cruza com as
constantes por AST, nas quatro direções — conjunto sem constante, constante sem
conjunto, número divergente, e **tabela ilegível**, que é a que impede as outras
três de passarem por vacuidade. Oito eixos de prova negativa.

**E é verificador, e não só teste, por um motivo mecânico:** os testes do seed
exigem Postgres e **pulam sem ele**. A pergunta *"o gerador ainda promete o que a
spec pede?"* tem de ser respondida sem banco.

**O nome do teste prometia o que não entregava** — `test_os_volumes_sao_os_de_02_
secao_6_1` lendo o gerador. É a classe da §7.3 da Fase 3, e a correção foi manter
o nome e **mudar a leitura**: ele passa a ler `02` §6.1 pelo mesmo parser. O
mesmo vale para o teste de volumes do `GM_NOTES`.

### 10.3 L1 e L2 — ficam, e por quê

**L1 — a partição dos seis conjuntos não é exercida em escala completa.** É
verdade e é limite declarado: os testes rodam em `ESCALA_REDUZIDA`, e o que muda
com a escala é apenas o volume de fundo — os cinco conjuntos plantados **não
escalam**, porque 22, 11, 34, 60 e 18 são números de `02` §6.1. A linha do item 5
no fechamento diz isso.

**L2 — os seis conjuntos e os três valores do enum.** É a **P5-4**, aberta na
peça 5 com destinatário na Fase 7 e gatilho declarado.

### 10.4 O item 1 da DoD, e por que ele fica sustentado pelo CI

`prova_seed_completo.py` ficou fora da allowlist, e a exclusão é **decisão pelo
mesmo critério de `bench_reconstruction`**, com um agravante próprio:

| | |
|---|---|
| exige Postgres, **escreve 3,5 M de linhas duas vezes**, ~5 min | admiti-lo daria ao julgador uma operação de escrita longa |
| exige `AURORA_SEED_DATABASE_URL` | `SAFE_ENV_PREFIX` não a admite, e alargá-lo para aceitar DSN poria connection string arbitrária na mão do auditor — superfície de rede pela porta do ambiente |
| o item pede um **número de máquina** | reexecutá-lo em outra máquina produz **outro número**, e não confirma o primeiro |

**O terceiro é o que decide, e ele não vale para a Fase 4.** Lá, a P4-10 escolheu
a opção A porque a propriedade era *comportamental* — a sequência do DEMO roda
ponta a ponta? —, e isso não se lê. Aqui a propriedade é um número relativo à
máquina, e é por isso que `06` T3 exige máquina, data e stack **ao lado dele**. O
que o auditor confere por leitura é o que importa: que os três são gerados **por
código**, e não digitados.

**Sustentado por:** o CI, que exercita o mesmo caminho de geração e carga em
escala reduzida com as duas direções do determinismo; mais a medição registrada
com contexto na §4.4 e na §4.5. Declarado, e não omitido — como a Fase 4 fez com
a opção C que recusou.

