# Fase 5 — Dados e auditoria ⏸

**Status: CONCLUÍDA — PASS na quinta rodada, contra `027f07e7`, sem BLOCKER e sem
HIGH.** 402 testes contra Postgres real, `OK` **sem nenhum `skipped`**; os quatro
invariantes verdes e os seis verificadores da fase com prova negativa executada.
O fechamento item a item está na §7; o inventário por destinatário na §8; as
lições na §9 — **sete nomeadas no fechamento**, sobre as quatro registradas
durante a fase; as cinco rodadas de auditoria na §10, na §11 e na §12. A
branch nasceu em `fd34c44` e a âncora está gravada em
`docs/process/phase_anchors.tsv`. As dezesseis decisões da §3 estão marcadas, e
nenhuma linha de código nasceu contra decisão pendente — as três do operador (D9,
D10 e D16) foram respondidas antes da peça que dependia de cada uma.

**Esta §7 não foi redigida pelo auditor, e a recusa dele é parte do fechamento.**
A instrução de escrevê-la chegou à janela errada, e ele parou: se quem emite o
veredito redige o artefato que a próxima auditoria trata como evidência, o
documento desfaz a separação que a Forma B (§11.3) acabou de estabelecer no
mecanismo. O que é dele está na §12.5 — a releitura conferindo se esta seção
corresponde ao que ele verificou.

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
| **6** ✅ | fechamento: DoD com prova item a item, a varredura do E1, o inventário por destinatário, as sete lições e as cinco rodadas de auditoria | **P5-1** |

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

### D9 — `POST /auth/token` nasce nesta fase — `DECIDIDA (operador) E NÃO EXECUTADA`

> **A rota NÃO nasceu, e a decisão ficou registrada como se tivesse nascido.**
> Achado ao responder o L1 da segunda auditoria: `api_surface.yaml` ainda traz
> `/auth/token` como `planejada`, e `app.py` não a tem. A decisão foi tomada
> antes da peça 2 e se perdeu entre as peças — não havia item de DoD que a
> cobrasse, e por isso nada ficou vermelho.
>
> **Isso é exatamente a classe que este registro existe para não deixar
> acontecer**: decisão marcada `DECIDIDA` num documento versionado, sem
> mecanismo que a cobre. A superfície tinha a terceira direção — ela cobra a
> promoção quando a rota nasce, e não a rota quando a decisão a promete.
>
> Vira a **P5-5**, com destinatário e gatilho. O texto abaixo é o da decisão,
> preservado.

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

### D16 — o mecanismo contra a reincidência da allowlist — `DECIDIDA` (operador)

**Implementada depois das três decisões do operador; o resultado está na §10.5.**
A forma abaixo é a que foi apresentada antes de qualquer código.

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

#### As três decisões, respondidas

1. **`*.sh` fica fora — por classe declarada, e não por omissão do universo.** A
   exclusão é estrutural: o lançador abre a sessão do auditor.
2. **Regex**, com a quarta direção cobrindo a fragilidade que ele assume: leitura
   parcial reprova igual a leitura vazia, cruzada contra o matcher real.
3. **P4-11 vale, e a ocorrência ficou contada** — é a terceira. Ver a §10.5.

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

A escala é a de `02` §5 — 28.000 alunos · 1.200 professores · 60 cursos · 8
semestres —, e o que ela produz é da ordem de 3,5 milhões de linhas, com as
notas, as matrículas e os históricos respondendo por 1,12 M cada. **O que a
medição afere são duas coisas**, e elas não são a mesma: o tempo do caminho
`gerar → COPY`, que é o que a DoD chama de seed, e a igualdade dos SHA-256 por
tabela entre duas rodadas do mesmo `RANDOM_SEED`.

**O número não está escrito aqui, e a ausência é o mecanismo.** Ele vive no
artefato assinado que o lançador grava sobre o commit auditado, e sai de
`scripts/check_prova_do_seed.py`, que só o imprime depois de conferir o SHA.
Máquina, data e stack continuam **ao lado do número** — a exigência de forma de
`06` T3 —, e continuam lá porque é lá que o número está. O porquê da mudança
está na §11: número de desempenho no registro envelhece em silêncio, e este
envelheceu três vezes.

**O par de digests é o que confirma escopo**, e ele também sai do verificador:
`students` não muda quando a correção é da trilha, e `audit_trail` muda. É essa
leitura que vale, e não o valor.

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

A medição foi **refeita** depois do embaralhamento, e os dois itens continuaram
passando: o tempo dentro do orçamento, e as vinte tabelas com SHA-256 igual nas
duas rodadas. Os números são os do artefato do commit, e não os deste parágrafo —
a §11 diz por quê.

**O que a releitura mostrou é o par, e não os valores:** o digest de `students`
não mudou e o de `audit_trail` mudou. Isso confirma o escopo do embaralhamento —
ele reordena a trilha e não toca o resto —, e é uma afirmação que sobrevive à
troca dos números, porque é sobre a **relação** entre os dois.

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
| P5-5 | a senha de seed de `05` §8 vale por vacuidade, e a D9 não foi executada | **condição** — ver abaixo |
| P5-6 | o gabarito é produzido e julgado em memória, e nada o escreve em `scenarios/` | **Fase 7** — ver abaixo |

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

### 10.6 A segunda rodada — FAIL, e o B1 é o achado da fase

**FAIL correto**, com um BLOCKER, um HIGH, um MEDIUM e dois LOW. Todos fechados
nesta rodada, menos os dois que ficam declarados.

#### B1 — o quarto vazamento da mesma família, e o pior deles

`object_id` trazia `g-ind-`, `g-amb-`, `g-sus-`, `g-mnt-`, `g-del-` e `g-nrm-`:
**o prefixo nomeava o conjunto**, na coluna que o participante lê.

**É pior que o terceiro**, e o terceiro tinha o argumento escrito no código:
aquele exigia ler o repositório e contar linhas; este **basta olhar a coluna**.

**A lacuna não era o prefixo, era a direção.** A bateria anti-vazamento inteira
apontava para o `GM_NOTES` e para o repositório — três verificadores, dezenas de
asserções —, e **nenhum teste perguntava se a linha da trilha se denuncia**. A
pergunta nova é essa, e ela é a correção real.

**Corrigido na ordem: asserção, vermelho medido, e só então o gerador.**

```text
FAIL  test_a_LINHA_DA_TRILHA_nao_diz_a_que_conjunto_pertence
      1 != 6 : os `object_id` tem 6 prefixos distintos
      (['g-amb','g-del','g-ind','g-mnt','g-nrm','g-sus'])

FAIL  test_o_PAR_DE_VALORES_nao_identifica_o_conjunto
      `ambiguos_legitimos` tem UM par de valores para 11 linhas ({(5.0, 6.5)})

FAIL  test_a_VARIACAO_de_nota_nao_separa_os_conjuntos
      a faixa de `indevidos_comprovados` (3.0..3.0) nao cruza a de nenhum outro
```

**As duas instâncias, e a segunda é a que passa por qualquer teste de string.**
Cada conjunto tinha um par de valores **fixo** — ambíguos sempre 5,0 → 6,5,
suspeitos 5,5 → 7,0, ruído 7,0 → 7,0. Um `GROUP BY previous_value, new_value`
devolvia o gabarito inteiro, e **nenhuma varredura de identificador vê isso,
porque não há string**.

E há uma terceira forma, que escrevi ao ver as duas: o **delta**. Pares distintos
ainda deixariam a faixa denunciar — se os indevidos sempre somassem 3,0 e mais
ninguém, `new - previous` seria o gabarito sozinho. O teste exige que a faixa de
cada conjunto **cruze** a de outro.

**O conserto:** `object_id` passa a ser atribuído **depois do embaralhamento**, em
ordem de trilha, sem prefixo de conjunto; e os pares de valores passam a ser
sorteados do fluxo semeado, com faixas que se cruzam. `02` §6.1 exige dos
indevidos apenas que **sempre elevem** — e elevar não os distingue, porque quase
todos elevam.

#### H1 — o verificador declarava cobrir o que não via

O comentário do `check_gabarito_fora_do_git.py` nomeava `g-ind-000`; o fonte tem
`f"g-ind-{i:03d}"`, e o sufixo vem de placeholder. As quinze sondas passavam
porque **nenhuma plantava identificador construído por f-string**.

**Isso é mais grave que o B1 como classe**, e o auditor está certo: ausência não
dá falsa garantia; declaração falsa dá.

Corrigido com as sondas primeiro. O sufixo passou a aceitar interpolação, e o
fecho virou lookahead — com `\b`, a forma interpolada continuava passando mesmo
depois de o sufixo aceitá-la, porque entre `}` e `"` não há fronteira de palavra.

**E o verificador corrigido achou a QUINTA instância do B1**, que nenhum humano
tinha visto: `AUT-AMB-`, `AUT-SUS-`, `PR-AMB-`, `PR-SUS-`, `PR-DEL-` — o infixo
nomeava o conjunto em `rectification_authorizations`, que é tabela que o
participante lê. Números de processo passaram a ser sequenciais e comuns aos três
conjuntos.

**A distinção que a correção exigiu**, e ela é o que impede a regra de reprovar o
gerador inteiro: interpolação só conta onde há **infixo de conjunto**.
`f"A-{i:06d}"` gera os 28 mil alunos e não aponta caso nenhum; `f"AUT-AMB-{i}"`
diz que aquela autorização é de ambíguo tão alto quanto `AUT-AMB-000`.

#### M1 — escalado, e a resposta é que o item é desta fase

`06` T8 está rotulado **Fase 5** e exige *"divergência é RECUSADA pelo linter"*.
Eu tinha comparação de conjuntos num teste, e remeti à Fase 7 no registro. **O
auditor está certo: ou `06` está errado e é `spec-change`, ou o item é da fase e
não foi entregue.** É o segundo.

`gabarito.conferir` levanta `GabaritoDivergente` e **roda dentro de `gerar`**: um
artefato divergente não chega a existir. Se rodasse depois, existiria um arquivo
inválido no disco entre a escrita e a conferência — e é nessa janela que alguém o
copia. Há teste por AST provando que a chamada está lá, e as duas direções:
fato órfão recusa, e `GM_NOTES` sem citação nenhuma **também** recusa, porque
passaria por vacuidade.

#### L1 — e a D9 estava marcada `DECIDIDA` sem ter sido executada

`05` §8 pede senha derivada do `RANDOM_SEED`; o seed grava `None`. **Conferi se a
rota nasceu, como o operador pediu: não nasceu.** `/auth/token` continua
`planejada`, e `app.py` não a tem — então a propriedade vale por vacuidade.

**O achado é maior que a vacuidade.** A D9 decidiu que a rota nasceria nesta fase
e ela não nasceu, e a decisão ficou no registro como se tivesse. É a classe que
este registro existe para não deixar acontecer: decisão marcada `DECIDIDA` num
documento versionado, **sem mecanismo que a cobre**. A terceira direção da
superfície cobra a promoção quando a rota nasce — não a rota quando a decisão a
promete.

Virou a **P5-5**, com as duas metades numa pendência só: a vacuidade acaba no
commit em que a rota nascer, e é aí que `05` §8 passa a ser violado.

#### L2 — fragilidade declarada

Fica como está, e o motivo está na §9.1: é a mesma família das seis ocorrências.


---

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

#### P5-6 — o gabarito existe como valor de retorno, e não como arquivo

**Aberta pelo L3 da quinta auditoria, e aceita como está.**

`07` Fase 5 lista `GM_NOTES.md` do pack nos OUTPUTS. `gabarito.gerar()` devolve o
artefato **em memória**, o linter roda dentro dele, e o teste produz o texto e o
julga — inclusive **executando** a query de referência contra o banco. O item 6
da DoD tem prova executável por esse caminho, e é por isso que isto é LOW e não
lacuna de entrega.

**O que falta é o produtor em disco:** nenhum comando escreve o par
`ground_truth.yaml` + `GM_NOTES.md` em `scenarios/`. Quem for facilitar um
exercício hoje tem o gerador e não tem o arquivo.

**Por que não se resolve aqui.** O `range-cli` é `00` §7 e `07` Fase 7 — escrever
um comando de pack nesta fase seria superfície de outra fase nascendo fora dela,
que é exatamente o corte declarado na §1.1. E a D10 já decidiu que o artefato
**nasce por comando** em vez de ser versionado: o produtor é a metade que falta
daquela decisão, não uma correção dela.

**Destinatário: Fase 7. Gatilho: o commit em que `range-cli` ganhar o subcomando
que escreve o pack** — é ali que "devolve em memória" deixa de ser suficiente,
porque o comando existe justamente para pôr o arquivo no disco.

> A numeração é `P5-6` e não `P5-5`: a P5-5 já estava ocupada pela senha de seed,
> aberta pelo L1 da segunda rodada. O item é o do L3 da quinta, com o
> destinatário e o gatilho aceitos.

**O que ela vai encontrar pronto:** o gerador, o linter que recusa divergência
dentro de `gerar`, o template de prosa e a query de referência — versionados, como
a D10 decidiu. Falta a chamada e o caminho de escrita.

---

## 7. O fechamento — a DoD com prova, item a item

`CLAUDE.md` diz que uma fase só fecha quando **todos** os itens da Definition of
Done passam. O quadro abaixo é o de `07` Fase 5 com a prova de cada um — não a
afirmação de que passou.

| # | Item de `07` Fase 5 | Prova |
|---|---|---|
| 1 | Seed completo em < 5 min | `scripts/check_prova_do_seed.py`, que **só imprime o número depois de conferir o SHA** — a medição é feita pelo lançador, no worktree do commit auditado, e o verificador recusa prova ausente ou de outro commit. O número não está aqui de propósito: ver §11 |
| 2 | Mesmo `RANDOM_SEED` produz dataset byte-idêntico | o mesmo artefato e o mesmo verificador: SHA-256 por tabela, igual nas duas rodadas da medição. E as duas direções na suíte: mesmo seed → mesmo dump; seeds diferentes → dumps diferentes |
| 3 | `UPDATE` e `DELETE` em `audit_trail` falham por trigger **e** por permissão de role | `tests/test_trilha_de_auditoria.py::TrilhaEhAppendOnly` — **quatro** testes: trigger recusando os dois verbos, `has_table_privilege` negando os três à role, e o par que impede o terceiro de virar superstição (a role **possui** `INSERT` e `SELECT`). **Limite: a role que a aplicação CONECTA não é essa** — M1 da quinta rodada, é a P5-3, e o que ele não prova está na §7.1 |
| 4 | `GET /audit/verify-chain` detecta adulteração induzida | `CadeiaDetectaAdulteracao` — campo alterado, `payload` alterado (a nota trocada), linha removida do meio, cada um reportando a **posição exata**; e a rota pelo stack ASGI, com papel, 401 e 403. **Limite: truncamento da cauda NÃO é detectado** — declarado, e **afirmado por teste** (`test_truncamento_da_cauda_NAO_e_detectado`), que é a técnica da §9.12 |
| 5 | Os seis conjuntos da Linha B nos volumes especificados | `SeisConjuntosDaLinhaB` — 22 · 11 · 34 · 60 · 18 · N, **disjuntos** e cuja **união é a trilha inteira**, aferidos contra `02` §6.1 e não contra o gerador (M2). Mais as seis características, e não só as contagens. **Limite: a partição é exercida em `ESCALA_REDUZIDA`** — os cinco conjuntos plantados não escalam, e o que muda com a escala é só o volume de fundo (L2 da quinta rodada, mantido) |
| 6 | `GM_NOTES.md` contém a query de referência que separa indevidos de ambíguos | `tests/test_gabarito.py` — o CI **produz** o artefato e o julga: o texto está lá, e a query **executada** devolve os 22 e nenhum dos 11. **Limite: o artefato existe em memória e nada o escreve em `scenarios/`** — L3 da quinta rodada, é a **P5-6**, com destinatário Fase 7 |

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
| `06` **T7** — auditoria imutável | os três critérios cobertos. Os critérios 1 e 2 — trigger e role — pelos **quatro** testes de `TrilhaEhAppendOnly`; o critério 3, a posição exata, por `CadeiaDetectaAdulteracao`. O limite da role declarado acima |
| `06` **T8** — determinismo e gabarito | os quatro critérios: dataset idêntico, os seis conjuntos, a query devolvendo exatamente os 22, e todo fato do `GM_NOTES` existindo no `ground_truth` |
| `06` **T6** — isolamento de papel (Fases 4–5) | a rota nova exige `secretaria`; 403 para aluno, 401 sem token. **A varredura recursiva de payload continua sendo a da Fase 4** — a rota de verificação devolve três campos e nenhum deles é conteúdo de trilha |
| `06` **T15** — segurança transversal | `Faker` pinado com fecho conferido; IPs só de RFC 5737; nenhum serviço novo exposto. **Esta linha é afirmação minha, e não do relatório** — ver abaixo |

**A conferência independente é a da quinta rodada**, e ela é de outra sessão e
outro worktree: os seis itens PASS, os **três critérios de T7** e os **quatro de
T8** cobertos, nenhum teste classificado como não provando o requisito, e as três
armadilhas típicas procuradas uma a uma. O relatório é
`docs/progress/audit_20260818T181506Z.md`; o que ele **não** conseguiu verificar
está lá, na seção própria, e não foi reescrito aqui.

**E a conferência para aí — a linha de T15 não tem corroboração no relatório.** Ele
não menciona T15 em ponto nenhum: nem `Faker`, nem RFC 5737, nem serviço exposto.
As três afirmações são minhas, conferidas na árvore (`constraints.txt`,
`dataset.py`, o compose), e ficam marcadas porque ler a tabela inteira como
auditada seria ler além do que foi auditado. **T6 está na mesma condição parcial**:
o relatório registra a rota nova com `papeis: [secretaria]` e 403/401 provados, e
não a varredura recursiva de payload, que continua sendo a da Fase 4.

### 7.3 Os dois verificadores por SHA reprovam no commit de fechamento — e isso é esperado

**O commit que grava este fechamento move o `HEAD`**, e os dois verificadores que
amarram evidência ao commit — `check_prova_do_seed.py` e
`check_provas_de_container.py` — reprovam por divergência de SHA: a prova gravada
é de outro commit.

Na árvore principal os dois **já estavam vermelhos antes deste commit**, pelo
mesmo motivo e não por outro: a prova do seed foi gravada sobre `c119718`, e a de
container declara `1d2f6395` — que não é ancestral nem de `c119718` nem do `HEAD`,
porque o rebase da P4-9 reescreveu aquela linha. **Anterior no tempo, e fora da
história alcançável** — e para o verificador tanto faz, porque o predicado é
igualdade de SHA e não ancestralidade. A medição que sustenta o candidato
`027f07e` nasceu **dentro do worktree de auditoria**, que é onde a Forma B a
executa. Não há nada a corrigir aqui: a árvore de quem edita não é a árvore que
julga.

**Não quebra nada, e a razão é de desenho:** no CI rodam **apenas os probes** dos
dois, porque o runner não tem — nem deve ter — o artefato que o operador escreve
na máquina que mede. E na próxima auditoria a Forma B mede dentro do worktree, de
modo que o artefato nasce sobre o commit que está sendo julgado.

**O que alguém vai ver, e qual estado é.** Quem rodar o lançador ou os dois
verificadores sobre o commit de fechamento verá dois vermelhos. O estado é
`TRANSPORTADA`, e não `AUSENTE`: **o artefato existe** — o que diverge é o SHA. Os
dois são direções separadas do verificador, (a) *arquivo não existe* e (b) *SHA
diverge*, e o briefing do auditor os distingue justamente para que ninguém deduza
qual foi.

**E o par que não pode ser confundido é `TRANSPORTADA` × `REPROVOU`.** O vermelho
diz *"a medição desta rodada não aconteceu, e divergência de SHA é o caso normal
aqui"* — **não** *"a medição rodou e um item falhou"*, que é a direção (e) e é
defeito de fase. `prova_seed_completo.py` grava o artefato **mesmo quando a
medição falha**, então o código de saída não separa os dois; o que separa é o SHA
gravado dentro dele. É a §11.4 inteira, e ela existe porque quem só olhasse o `rc`
chamaria de transporte uma medição reprovada.

Está escrito aqui porque a alternativa seria alguém redescobrir o vermelho sem o
contexto e concluir que a fase regrediu depois do PASS.

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
| **Fase 7** | P5-6 | o gabarito não tem produtor em disco | o commit em que `range-cli` ganhar o subcomando que escreve o pack |
| **operador, sem fase** | P5-3 | `REVOKE` não alcança a role que conecta | o primeiro deploy destinado a exercício com participante real |
| **condição, sem fase** | P5-5 | senha de seed de `05` §8 vale por vacuidade | o primeiro commit que implemente `POST /auth/token` |
| **condição, sem fase** | P4-7, P4-8, P4-11 | herdadas da Fase 4, sem mudança | inalterados |
| **Fase 8** | P4-4, P4-6, P2-6 | herdadas, sem mudança | inalterados |

**As duas da Fase 7 vão juntas e não são a mesma.** A P5-6 é o **produtor** — o
comando que escreve o par no disco; a P5-4 é o **modelo** — os seis conjuntos que
não cabem nos três valores do enum. Quem fechar a primeira sem olhar a segunda
escreve um `ground_truth.yaml` que omite dois conjuntos sem que nada acuse, porque
o schema não tem como recusar o que não sabe nomear.

**Duas das seis abertas aqui ficaram sem fase, e ficaram de propósito.** A P5-3
não tem fase porque `07` não declara fase de deploy; a P5-5 não tem fase porque a
D9 decidiu uma e ela não foi executada — e inventar outra repetiria o defeito que
o L1 da segunda rodada achou. Pôr fase numa pendência cuja condição não pertence a
fase nenhuma é como ela morre calada: chega o marco, ninguém viu a condição, e a
linha é riscada por vencimento.

**A P4-2 foi redatada e não empurrada**, e a diferença está medida: o gatilho
continua sendo *o primeiro `append`*, e a Fase 5 provou que ele não aconteceu
aqui — a trilha de `02` §4 é tabela de domínio com cadeia própria, e não o event
store. Se a Fase 6 também não o produzir, ela desce de novo.

**A P5-3 é a única do operador**, e é a única que não é minha para fechar: ela
exige uma segunda credencial, e credencial não se escreve em arquivo versionado.
O gatilho não cabe como item de DoD sem `spec-change` — `07` não declara fase de
deploy. Ele viaja na entrada da §6 do registro de seções, que é CODE e que quem
mexer em deploy e em exclusão de gabarito tem de tocar. A P5-5, a outra sem fase,
viaja de outro jeito: pela terceira direção da superfície, que cobra a promoção da
rota no commit em que ela nascer.

---

## 9. O que a fase aprendeu sobre o próprio método

**Sete lições são as que o fechamento nomeia** — quatro do operador, três
acrescentadas pelo auditor. Elas não estão em ordem numérica: as seções foram
escritas na volta em que cada uma apareceu, e renumerá-las quebraria as citações
que outras fases já fazem.

| A lição | Onde | Quem a nomeou |
|---|---|---|
| a família dos **sete vetores** e a propriedade que a fechou — partição declarada | **§9.2**, com a distinção entre *corrigido* e *inexprimível* na **§9.7** | operador |
| a **correção herdando o defeito** da coisa corrigida, minutos depois de a classe ser nomeada | **§9.6** | operador |
| o **gate que nasceu inalcançável**, e a pergunta que virou critério de admissão | **§9.8** | operador |
| o **laço da medição**, fechado tirando o número do registro e pondo a medição no lançamento | **§9.9** | operador |
| **regra escrita × regra virada predicado** — a mesma violada quatro vezes, a quarta corrigindo a terceira | **§9.10** | auditor |
| **auditabilidade como produto**, e não subproduto — a comparação com a Fase 2 | **§9.11** | auditor |
| o **limite exercido** em vez de escrito, com nome próprio: a técnica é autoextinguível | **§9.12** | auditor |

**E quatro ficam registradas de onde nasceram**, porque são as instâncias que as
sete generalizam: **§9.1** (o texto que explica a regra reprova contra ela, seis
vezes), **§9.3** (escalar sem varrer), **§9.4** (a direção inversa da prova) e
**§9.5** (o teste não nasceu certo, e o que o descobriu foi plantar).

**As três do auditor entraram porque ele viu o que eu não podia ver.** A §9.10 e a
§9.11 são sobre o julgador — quem constrói o mecanismo julga mal se ele próprio
alcança o julgador; e a §9.12 nomeia uma técnica que eu usei quatro vezes sem
perceber que era uma. Nenhuma das três foi redigida por ele: o que ele fez foi
nomeá-las, e a distinção é a mesma da §12.5.

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


### 9.5 O teste não nasceu certo, e o que o descobriu foi plantar — não reler

O teste de propriedade que substituiu as asserções por vetor **passou verde na
primeira execução**. Quatro vetores históricos foram plantados para medir, e **só
dois reprovavam**.

| Vetor plantado | Reprovava? | O que faltava |
|---|---|---|
| `user_agent` próprio do ruído | sim | — |
| hora do ruído fixa em 03h | **não** | a varredura isentava a coluna **inteira**, sem olhar o campo `conjuntos` |
| alunos de janela estreita | **não** | exclusividade e intercalação não pegam concentração; e depois, o limiar |
| infixo no `object_id` | **não** (ver §9.7) | a mutação não é escrevível |

**Sem plantar, o verde de primeira teria fechado a fase.** E verde de primeira num
teste escrito para uma classe que já produziu sete instâncias era o resultado
menos provável — foi o que não me ocorreu enquanto eu o lia e achava correto.

**As três correções que a medição exigiu** não são refinamentos: cada uma fechava
um buraco pelo qual um vazamento real passava. E a última — comparar entre seeds
com limiar de independência — só apareceu porque a anterior produziu **falso
positivo** contra `minuto`, cuja sobreposição entre dois seeds é *menor* que o
acaso prediz. Um teste que reprova o que não é defeito é abandonado na terceira
vez que alguém o vê vermelho.

### 9.6 A correção herdou o defeito da coisa corrigida — e no mesmo turno

O H1 da segunda auditoria apontou: `assertNotEqual` sobre união é satisfeito por
**um** elemento. Escrevi o teste de propriedade para corrigir isso — e **usei
`assertNotEqual` sobre conjuntos dentro dele**.

Segunda vez na mesma volta, com a classe nomeada, escrita e fresca. É a §7.3.1 na
forma mais dura que esta linhagem produziu: **a correção reproduzindo o defeito
da coisa que ela corrige**, minutos depois de o defeito ter sido explicado.

**O que pegou foi medir, e não lembrar.** Eu tinha acabado de escrever o
parágrafo sobre a fraqueza do `assertNotEqual`; isso não impediu nada. O que
impediu foi plantar o vetor e ver o teste passar quando ele devia falhar.

A conclusão não é "prestar mais atenção" — é a mesma da §1.6 da Fase 1, com um
alvo novo: **a disciplina não segura nem quem acabou de escrever a regra**, e
por isso a medição por mutação deixa de ser recomendável e passa a ser o passo
que fecha um teste de classe. Um teste escrito contra uma classe conhecida nasce
sem prova, e prova aqui é mutação que ele tem de pegar.

### 9.7 Corrigido e inexprimível não são o mesmo estado

Seis dos sete vazamentos foram **corrigidos**: o código mudou, e o teste que os
pega existe. Um deles ficou em outro estado, e a distinção vale registro porque
ela é o que a reestruturação comprou.

**O vetor de identificador é hoje inexprimível.** `object_id` é atribuído
**depois** do embaralhamento, num ponto onde o conjunto já não está em escopo:
não há variável a consultar. Tentei escrever a mutação que o reintroduziria e não
consegui — não porque seja difícil, mas porque exigiria **mover código de lugar**,
e mover código de lugar aparece no diff como reestruturação, não como ajuste.

| Estado | O que impede o retorno | O que o retorno parece no diff |
|---|---|---|
| **corrigido** | um teste que fica vermelho | uma linha alterada, e o teste acusa |
| **inexprimível** | não há de onde tirar o dado | uma função mudando de forma |

**A diferença é o custo de reintroduzir.** Um vetor corrigido volta com um
descuido e é pego por um teste; um vetor inexprimível volta só com uma decisão de
estrutura, que passa por revisão de PR com outra cara. É a distinção entre regra
e impedimento da §1.6 — e é o argumento a favor de reestruturar em vez de
corrigir, quando a classe já mostrou que tem N+1 instâncias.

**Não vale para os outros seis**, e isso está dito para não virar promessa
grande: a hora, o IP, o aluno e o valor continuam sendo decididos com o conjunto
em escopo, porque `02` §6.1 exige que sejam. O que os segura é a lista declarada
mais a varredura por coluna — mecanismo, e não impossibilidade.

### 9.2 Sete vetores da mesma família, e o que a fechou não foi o sétimo conserto

**Esta é a lição central da fase, e ela tem duas metades**: por que a contagem
chegou a sete, e por que parar de consertar vetor foi o que terminou.

A D10 decidiu *"`scenarios/` fica fora do Git"*, e a decisão está certa. Ela
protege **o arquivo**. O gabarito vazou por sete caminhos que ela não nomeia, e
**nenhum dos sete foi achado por leitura** — cada um veio de teste, de verificador
ou de auditoria:

| # | Caminho | O que vazava | Quem achou |
|---|---|---|---|
| 1 | **o gerador** | a conta comprometida era constante num módulo versionado | teste da peça 5 |
| 2 | **a posição** | identidades por índice: mesma conta e mesmo grupo com qualquer seed | *seeds diferentes → SHAs diferentes*, pedido pelo operador |
| 3 | **a ordem** | conjuntos gravados em bloco — as 22 primeiras linhas da trilha eram sempre os indevidos | o mapeamento caso → conteúdo mudando com o seed |
| 4 | **a própria linha** | prefixo de conjunto em `object_id`, e par de valores fixo por conjunto | B1 da segunda rodada |
| 5 | **a tabela vizinha** | infixo de conjunto no número de processo, em `rectification_authorizations` | o verificador **depois** de o H1 corrigi-lo |
| 6 | **a janela de índice** | `student_id`, justificativa e aprovador saindo de faixas disjuntas por conjunto | B1 da terceira rodada |
| 7 | **a conta do ator** | `actor_user_id` de ambíguos e suspeitos disjunto do dos normais | a varredura corrigida, e **nenhuma auditoria o viu** |

E três entradas saíram **antes** de virar instância numerada — `lote` no payload,
`user_agent` e a hora fixa do ruído —, achadas por aplicar uma pergunta a cada
campo, e não por rodar teste nenhum.

**O que os sete têm em comum, e o que isso invalidava.** O gabarito estava legível
no **artefato que o participante investiga** — sem `.env`, sem repositório e sem
`RANDOM_SEED`. A bateria anti-vazamento inteira apontava para o repositório: três
verificadores, dezenas de asserções. A lacuna nunca foi nenhum dos sete; era a
**direção** que ninguém tinha testado. Uma fronteira declarada sobre *onde o
arquivo mora* não diz nada sobre *o que o conteúdo revela*, e as duas perguntas
não se respondem uma à outra.

**A causa é estrutural, e é por isso que a contagem não parava.** O gerador
construía **por conjunto**: um laço por conjunto, e todo atributo escrito de
dentro dele. O conjunto era a **primeira** coisa decidida — então todo atributo
era função dele, vazar era o caso normal e *não* vazar era o acidente. A lista do
que um laço fixa não é enumerável por inspeção. Consertar o vetor N deixava N+1
existindo, e foi o que aconteceu cinco vezes seguidas.

**A propriedade que fechou a classe** não é "nada depende do conjunto" — isso
destruiria a Linha B, porque `02` §6.1 **exige** a correlação; sem ela os indevidos
deixam de ser indevidos. É esta:

> a partição dos atributos é **declarada**, e tudo que não está na lista é sorteado
> por um caminho que não conhece o conjunto.

**Não é o pool que fecha — é o pool mais a lista.** O pool torna a independência
possível; é a **lista** que torna a fronteira verificável em vez de intencional, e
que faz **coluna nova entrar sozinha** na varredura em vez de precisar de asserção
nova. A pergunta que classifica cada entrada — *a spec exige a propriedade ou o
valor?* — achou três vazamentos antes de qualquer teste rodar, e a varredura
corrigida achou o sétimo.

**A mudança de forma é o ponto.** Antes: N asserções contra N vetores conhecidos,
e o N+1 sempre existia. Depois: uma propriedade sobre **toda coluna que o dataset
escreve**, com a lista declarada do que pode correlacionar. Seis dos sete ficaram
**corrigidos**; um ficou **inexprimível**, e a distinção entre os dois estados —
que é o que a reestruturação comprou — está na §9.7.

**A generalização, para a Fase 6 e as seguintes:** quando uma classe de defeito
chega à terceira instância, o conserto da terceira é a resposta errada. O que
termina é achar a propriedade que tornava a classe possível e trocar as asserções
por ela — e o sinal de que se achou a propriedade certa é que a instância N+1
deixa de ser expressável, e não que ela deixou de aparecer.

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

### 9.8 Mecanismo admitido sem caminho de exercício — a pergunta que virou critério

`check_prova_do_seed.py` foi escrito, testado por nove eixos de prova negativa,
documentado no registro e **admitido na allowlist do auditor**. Ele nascia
**inalcançável**: o artefato que ele lê é gravado na raiz da árvore de quem mede,
o worktree de auditoria é criado do zero a partir do commit, e o lançador
transportava apenas as provas de container. O gate reprovaria em **toda auditoria
futura** — desta fase e das próximas — por ausência de um arquivo que nunca
chegava ali. Foi H1 da quarta rodada, e o BLOCKER da mesma rodada era a
consequência: os itens 1 e 2 da DoD sem prova nenhuma no checkout.

**O que torna isto uma lição e não um esquecimento é o gêmeo.**
`check_provas_de_container.py` funciona porque recebeu o transporte **no mesmo
commit que o criou**. A forma completa era conhecida, estava escrita ao lado, e
mesmo assim entrou a metade. É o mesmo movimento das sete instâncias da §9.2:
**olhar o artefato novo e não a cadeia que o faz existir**.

É a §7.3 do registro da Fase 3 — *"checagem só é exercida quando existe
consumidor, e até lá ela parece pronta"* — um andar acima: lá, o teste que parece
existir; aqui, o **mecanismo** admitido, allowlistado e documentado, sem o caminho
pelo qual é exercido.

**O antídoto não é lembrar. É a pergunta, e ela vale para toda admissão futura de
mecanismo — allowlist, CI, hook, gate de PR:**

> **Por qual caminho ele é exercido no ambiente em que vai julgar, e quem constrói
> esse caminho?**

Duas metades, e a segunda é a que faltou: *"o operador roda"* não é resposta se
nada no lançador o roda. **A resposta certa nomeia um commit**, e é o commit que
cria o mecanismo — não um posterior.

**E a pergunta foi aplicada a si mesma antes de a correção entrar**: a cadeia da
Forma B foi rodada inteira — stack efêmera, banco descartável, `alembic upgrade
head`, as duas rodadas de medição — antes de o commit existir. O que ficou não
exercido está dito na §11.6, com o motivo de por que a primeira reauditoria o
exerce por construção.

### 9.9 O laço da medição: o registro que envelhece a prova que ele cita

O artefato de medição carrega o SHA do checkout, e o verificador reprova quando
ele diverge. Daí sai um laço que não estava no desenho:

```text
medir  ->  registrar o número  ->  commitar  ->  a medição fica de outro commit
   ^                                                            |
   +------------------------------------------------------------+
```

**Ele se exerceu duas vezes na volta que o criou**, e a saída que enxerguei foi
procedimental: *medir por último, com o código congelado, e não commitar nada
depois*. A volta seguinte caiu nele de novo — e o M1 da quarta rodada foi
exatamente isto: o quadro de DoD, que é a linha mais lida do registro, citando um
número que não era de medição nenhuma do candidato.

**A disciplina falhou porque disciplina é o que a §9.6 já registrou não segurar** —
não segura nem quem acabou de escrever a regra. Três voltas confirmaram.

**A saída foi tirar as duas responsabilidades de quem escreve o documento**, e são
duas e não uma:

| | O que saiu de onde |
|---|---|
| **Forma A** | o **número** sai do registro. Nenhuma linha carrega valor de medição; o registro diz *onde* a prova está e o que ela prova |
| **Forma B** | a **medição** sai da disciplina e entra no lançador, que a executa sobre o commit já congelado, dentro do worktree |

**A A sozinha não bastava** — ela deixa "medir por último" como disciplina. A B
sozinha também não: o número voltaria a ser transcrito e a envelhecer. É a junção
que fecha o laço, e o detalhe da implementação está na §11.

**A generalização:** todo número de desempenho é uma afirmação sobre um commit. Se
ele mora num documento que o commit seguinte não atualiza, ele **envelhece em
silêncio** — e a forma de não envelhecer não é atualizá-lo com cuidado, é o
documento não o conter. `06` T3 continua satisfeito por leitura literal: ele exige
máquina, data e stack **ao lado do número**, e os três estão onde o número está.

### 9.10 A regra que virou predicado é a que segurou — e a que ficou escrita foi violada quatro vezes

*"Script novo que precise ser executado pelo auditor entra aqui por nome, no
commit que o cria."* A frase está escrita **dentro do arquivo que ela governa**.
Foi violada **quatro vezes**:

| # | Cometida em | Como se soube |
|---|---|---|
| 1 | Fase 2 | B1 da auditoria — a fase criou a primeira suíte real e não estendeu o julgador; ele não executou **nada**, e sete de nove itens da DoD ficaram NÃO VERIFICADO |
| 2 | Fase 4 | `check_readme_atual.py` e sua prova negativa ficaram fora, e **ninguém notou por uma fase inteira** — só o verificador da D16 os viu, já na Fase 5 |
| 3 | Fase 5, peças 1, 3 e 5 | M1 da primeira auditoria — os três verificadores novos da fase nasceram fora da allowlist. A terceira reincidência da mesma regra |
| 4 | Fase 5, na rodada que corrigia a terceira | `check_volumes_da_linha_b.py`, criado **para corrigir o M1**, nasceu fora da allowlist. Achado pelo verificador da D16 na primeira execução, junto com a segunda ocorrência |

**A quarta é a que fecha o argumento.** Ela foi cometida enquanto se corrigia a
terceira, por quem tinha acabado de escrever sobre ela. É a **§9.6 em outro
subsistema** — a correção herdando o defeito da coisa corrigida —, e a segunda vez
na mesma fase que essa forma aparece. Se restava dúvida de que a regra escrita não
segurava, ela acaba aqui.

**O que a fechou foi a D16: a regra virou predicado.**
`check_allowlist_do_auditor.py` cruza `git ls-files scripts/` com a allowlist real
do hook, e **importa o matcher em vez de reimplementá-lo** — divergência entre "o
matcher libera" e "a leitura encontrou" reprova *por divergência*, antes de
qualquer conclusão sobre classificação. Ele disparou **duas vezes enquanto era
escrito**, e achou as quatro entradas na primeira execução real. Resultado: 50
scripts, 40 na allowlist, 10 declarados fora **com motivo** — porque universo que
exclui por não incluir é a mesma forma de "coberto por nada" que já custou duas
auditorias.

**A conclusão conjunta desta fase, e ela é a lição:** das correções que esta fase
produziu, **as que seguraram foram exatamente as que viraram predicado** — a
partição declarada com varredura por coluna, o linter que **recusa** dentro de
`gerar`, os volumes lidos da spec em vez das constantes, a allowlist cruzada com o
matcher, a medição amarrada por SHA. As que ficaram como texto — a frase dentro do
hook, "medir por último", "prestar atenção ao `assertNotEqual`" — foram
reincididas, **inclusive por quem as tinha acabado de escrever**.

Regra escrita é documentação do que se pretendia. **Só o predicado é mecanismo**, e
a diferença entre os dois é medida em reincidências.

### 9.11 Auditabilidade é produto da fase, e não subproduto dela

**A comparação é com a Fase 2, e ela é dura.** Lá, a fase criou a primeira suíte
real do projeto e não estendeu o julgador por uma linha: o auditor **não executou
nada**, voltou a julgar por leitura de código, e **sete dos nove itens da DoD
ficaram NÃO VERIFICADO**. O veredito foi FAIL por uma omissão de uma linha — e o
que se perdeu não foi o veredito, foi a evidência: nenhum daqueles sete itens ficou
provado, apenas plausível.

Nesta fase o julgador executou. O relatório da quinta rodada registra 402 testes
contra Postgres real com `OK` e **zero pulos**, os quatro invariantes verdes com
`phase0_negative_tests.py` provando que os seis verificadores ainda reprovam contra
violação plantada, e os seis verificadores novos da fase com **prova negativa
executada**. Nenhum item de DoD ficou NÃO VERIFICADO.

**Isso não foi consequência de a fase ser boa — foi construído, e custou:**

| O que foi construído | Contra qual falha |
|---|---|
| a **allowlist como predicado** (D16) | o auditor sem o comando que a fase criou — a §9.10 |
| a **prova de container** amarrada por SHA (P4-10) | o que exige rede e volume não caber na sessão do julgador |
| a **medição do seed no lançador** (Forma B) | o gate que nasce inalcançável — a §9.8 |
| os **quatro estados** do briefing (`MEDIDA`, `REPROVOU`, `TRANSPORTADA`, `AUSENTE`) | o auditor deduzindo qual foi, que já custou uma rodada na Fase 3 |
| o **verificador da §7 de `05`** entrando antes da promoção | seção normativa coberta por nada |

**A inversão é o ponto.** Enquanto auditabilidade é subproduto, ela é o que sobra
depois de a fase estar pronta — e o que sobra é leitura de código, que produz
"parece certo" e não "está provado". Quando é produto, ela aparece no plano da
fase, tem commit, tem prova negativa, e **falha antes** de a auditoria começar.

**O critério prático, para a Fase 6:** um mecanismo novo só está pronto quando o
julgador consegue exercê-lo no ambiente em que vai julgar — o que é a pergunta da
§9.8 outra vez, agora como definição de pronto e não como antídoto.

### 9.12 O limite exercido — uma técnica com nome próprio, e ela se autoextingue

**Esta técnica está diluída dentro da P5-3 e da §7.1, e a fase inteira a usou
quatro vezes sem nomeá-la.** O nome importa porque sem ele ela não é reusável.

**A forma:** quando um mecanismo tem um limite conhecido, escreve-se um teste que
**afirma o limite** — não que o mecanismo funciona, mas que a lacuna ainda está
lá. Ele fica **verde enquanto o limite existe**, e **vermelho no dia em que
alguém o fechar**, com mensagem de falha dizendo qual pendência acabou de vencer.

| Onde | O que o teste afirma | Fica vermelho quando |
|---|---|---|
| `test_a_role_QUE_CONECTA_ainda_possui_UPDATE_na_trilha` | a role de conexão **ainda tem** `UPDATE` sobre a trilha | a segunda credencial existir — a P5-3 fechando |
| `test_a_role_que_conecta_pode_voltar_de_SET_ROLE` | `RESET ROLE` desfaz o `SET LOCAL ROLE` da escrita | idem |
| `test_truncamento_da_cauda_NAO_e_detectado` | a cadeia não detecta remoção do fim | a âncora de cauda existir |
| a partição em `ESCALA_REDUZIDA` | o limite declarado ao lado do item 5 | a partição for exercida em escala completa |

**Por que é melhor que escrever o limite.** Limite escrito envelhece calado: ele
continua no documento depois de fechado, e passa a ser afirmação falsa — que é
exatamente a classe do E1 e da P5-1, e o que a §9.3 registra sobre a terceira
ocorrência. Limite **exercido** não pode envelhecer: no instante em que deixa de
ser verdade, a suíte fica vermelha e alguém tem de olhar.

**A propriedade que ela tem e nenhuma outra tem: é autoextinguível.** O teste
existe para deixar de existir. Ele não é dívida acumulando — é dívida com alarme,
e o alarme dispara **do lado certo**, no commit que resolve, e não no commit que
esquece.

**O que ela não faz, e está dito porque não faz:** não fecha o limite. A P5-3
continua aberta e é do operador; o truncamento de cauda continua não detectado. A
técnica troca *"o limite está escrito em algum lugar"* por *"o limite tem
mecanismo que acusa quando muda"* — que é a mesma distinção entre regra e
predicado da §9.10, aplicada ao que ainda **não** foi construído.

**Quando usá-la:** sempre que um item de DoD passar com limite conhecido. O par
"o item passa" + "e isto é o que ele não prova" só é honesto se a segunda metade
tiver mecanismo — do contrário ela é ressalva, e ressalva é o que a leitura de
amanhã ignora.

---

## 10. A auditoria de checkpoint — cinco rodadas, e o PASS é o da quinta

**Cinco rodadas, três FAIL entre dois PASS**, e a sequência importa mais que o
veredito final: o PASS da primeira era um PASS que não tinha visto o gabarito
vazando pela coluna que o participante lê.

| # | Commit | Veredito | O achado que a definiu | Onde |
|---|---|---|---|---|
| 1 | `7e4c897` | PASS | M1 allowlist (a terceira reincidência) e M2 guarda em vez de conferência | §10.1–§10.5 |
| 2 | `719d84a` | **FAIL** | B1 — prefixo de conjunto em `object_id`; H1 — o verificador declarava cobrir o que não via | §10.6 |
| 3 | `46c0347` | **FAIL** | B1 — o sexto vetor, e a decisão de parar de consertar vetor | §10.7, §10.8 |
| 4 | `c119718` | **FAIL** | B1 + H1 — os itens 1 e 2 sem medição, e o gate nascido inalcançável | §11 |
| 5 | `027f07e` | **PASS** | sem BLOCKER e sem HIGH; um MEDIUM e três LOW, todos declarados | §12 |

**O PASS da primeira rodada é o dado mais útil da tabela.** Ele foi emitido sobre
uma árvore em que o gabarito de dezenas de casos era legível na trilha, e o achado
não veio de mais leitura: veio de a auditoria seguinte perguntar numa direção que
nenhuma das anteriores tinha perguntado. Auditoria é amostra, e um PASS diz que
*aquelas* perguntas foram respondidas.

As três primeiras rodadas e as correções de cada uma estão abaixo; a quarta produziu
a §11 inteira, e a quinta está na §12.

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
com contexto no próprio registro. Declarado, e não omitido — como a Fase 4 fez com
a opção C que recusou.

> **Superado em parte, e a leitura desta seção mudou duas vezes depois.** A
> exclusão de `prova_seed_completo.py` da allowlist continua válida, e pelas três
> razões acima. O que caiu foi a segunda metade do "sustentado por": *"a medição
> registrada com contexto no registro"* virou o M2 da terceira rodada (número sem
> dono) e o B1 da quarta (item de DoD sem prova amarrada ao commit). A resposta
> está na §10.8 — o artefato assinado — e na §11: a medição não é lida no
> documento nem executada pelo auditor; ela é feita **pelo lançador**, fora da
> sessão dele, e chega amarrada por SHA. A exclusão da allowlist não era o
> problema; a ausência do caminho era.

### 10.5 A D16 implementada — e ela achou a quarta ocorrência na primeira execução

As três decisões do operador, e o que cada uma produziu.

**`*.sh` fica fora por classe declarada, e não por omissão do universo.** Há um
único — `start_checkpoint_audit.sh` —, e a exclusão é **estrutural**: ele abre a
sessão do auditor, então rodá-lo de dentro dela seria recursão. A classe está
escrita no verificador com o motivo, porque *universo que exclui por não incluir
é a mesma forma de "coberto por nada" que a §4 e a §6 de `05` tiveram* — e as
duas custaram uma auditoria cada.

**Regex, com a quarta direção cobrindo a fragilidade que ele assume.** A leitura
textual é cruzada com o **matcher real**: `ALLOWED` é importado do próprio hook, e
para cada script compara-se "o matcher libera?" com "a leitura encontrou?".
Divergência reprova **por divergência**, antes de qualquer conclusão sobre
classificação — a forma do `check_gate_coverage.py`, que confere o próprio
casamento contra o `git ls-files`.

**E ela disparou duas vezes enquanto o verificador era escrito**, que é o melhor
argumento a favor dela: primeiro com quatro nomes só no matcher (a primeira
entrada abre o grupo com `(?:`, e o regex não casava), depois com um (a última
fecha com `)`). Leitura parcial reprova igual a leitura vazia, e há probe para
cada uma.

#### O que a primeira execução achou

```text
`scripts/check_readme_atual.py` nao esta na allowlist e nao esta declarado fora
`scripts/check_readme_atual_probes.py`  idem
`scripts/check_volumes_da_linha_b.py`   idem
`scripts/check_volumes_da_linha_b_probes.py`  idem
```

**`check_volumes_da_linha_b` foi criado nesta mesma rodada, corrigindo o M1.** É
a **quarta** ocorrência da regra, cometida enquanto se corrigia a terceira, por
quem tinha acabado de escrever sobre ela. Se houvesse dúvida de que a regra
escrita não segurava, ela acaba aqui.

`check_readme_atual` estava fora **desde a Fase 4**, e ninguém havia notado.

Os quatro entraram, mais o próprio `check_allowlist_do_auditor` e sua prova
negativa. **50 scripts: 40 na allowlist, 10 declarados fora com motivo.**

#### A P4-11 e a terceira ocorrência — a contagem é o ponto

<!-- O título não começa com o identificador de propósito: a seção de detalhe da
     P4-11 vive em `fase_4.md`, e `check_progress_consistency.py` leria um
     `#### P4-11 —` aqui como detalhe de pendência desta fase, cobrando linha na
     tabela-resumo. Ele reprovou exatamente assim, e está certo: nota SOBRE uma
     pendência herdada não é a pendência. -->

Este é o **terceiro mecanismo que mora na árvore que audita e lê o que constrange
o auditor** — depois do próprio `readonly_bash.py` e do
`check_provas_de_container.py`. A direção é **aditiva** (verificador novo,
somente leitura, com prova negativa ao lado), então a P4-11 **não dispara**: o
gatilho dela é *alteração de `readonly_bash.py` em direção que não seja
estritamente aditiva*.

**Mas a contagem importa, e é por isso que ela está registrada.** Pendência com
condição de vencimento — e não com marco — parece inativa quando está apenas
esperando a direção errada. Três ocorrências sem disparo é exatamente o padrão
que faz alguém concluir que a pendência morreu. Ela não morreu: está esperando
a primeira remoção de regra, o primeiro afrouxamento de `_alvo_nao_contido`, ou o
primeiro comando com forma de escrita admitido.


#### P5-5 — a senha de seed vale por vacuidade, e a D9 não foi executada

**Aberta pelo L1 da segunda auditoria, e ela tem duas metades que se sustentam
uma na outra.**

`05` §8: *"Senhas de seed nunca são valores triviais reutilizáveis; são geradas a
partir do `RANDOM_SEED` e impressas apenas no log de seed local."* O seed grava
`password_hash = None` em todos os usuários.

**Hoje a propriedade vale por vacuidade**, e conferi em vez de supor: não há rota
que troque credencial por token — `POST /auth/token` continua `planejada` na
superfície, e `app.py` não a implementa. Sem porta de entrada, não há senha a
proteger, e "nunca trivial" é verdade sobre um conjunto vazio.

**A vacuidade acaba no commit em que a rota nascer**, e é por isso que as duas
metades são uma pendência só: a D9 decidiu que ela nasceria nesta fase e ela não
nasceu. Se tivesse nascido, `05` §8 estaria sendo violado agora.

**Destinatário: a fase que implementar `POST /auth/token`.** A D9 a punha aqui;
como não foi executada, ela volta a ser escopo herdado da superfície, e a
`api_surface.yaml` continua cobrando a promoção no commit em que a rota existir.

**Gatilho: o primeiro commit que implemente a rota.** No mesmo commit, três
coisas: a senha derivada do `RANDOM_SEED` por `seeded_random`, o hash gravado em
`users.password_hash`, e a impressão **apenas no log de seed local** — que é a
metade de `05` §8 que um `print` distraído viola sem que nada acuse.

**O que já está pronto para essa hora:** a coluna existe, o seed já cria os
usuários com papel, e `range_core.determinism.seeded_random` já dá o fluxo por
escopo. O que falta é a rota e três linhas no gerador.

---

### 10.7 A terceira rodada — a propriedade, e não o sétimo vetor

**FAIL, e o operador estava certo em parar de corrigir vetor.** O sexto vazamento
— `student_id` por janela de índice disjunta — veio por um caminho que nenhuma
das cinco correções alcançava.

#### A propriedade que permitia, e onde discordei

O gerador construía **por conjunto**: um laço por conjunto, e todo atributo
escrito de dentro dele. O conjunto era a **primeira** coisa decidida, então todo
atributo era função dele — vazar era o caso normal, e não vazar era o acidente. A
lista do que um laço fixa não é enumerável por inspeção: por isso corrigir vetor
nunca terminava.

**Onde discordei, e o operador aceitou:** "nada depende do conjunto" destruiria a
Linha B. `02` §6.1 **exige** a correlação — sem ela os indevidos deixam de ser
indevidos. A propriedade que fecha é outra:

> a partição dos atributos é **declarada**, e tudo que não está na lista é
> sorteado por um caminho que não conhece o conjunto.

**Não é o pool que fecha a classe — é o pool mais a lista**, porque é a lista que
torna a fronteira verificável em vez de intencional.

#### A pergunta aplicada a cada entrada, e três vetores achados antes do teste

*A spec exige a propriedade ou o valor?* Aplicada às nove entradas, ela achou
três vazamentos **antes de qualquer teste rodar**:

| | |
|---|---|
| `lote` no payload | só o ruído tinha a chave — classificador perfeito. `02` §6.1 marca o ruído pelo **usuário**. Saiu |
| `user_agent` | `batch/1.0` só no ruído. `02` §4.1 exige registrá-lo, não o faz discriminante. Foi para o pool |
| hora do ruído | fixa em 03h. A faixa noturna é dos indevidos e dos suspeitos; o ruído não tem faixa normativa. Foi para o pool |

E a entrada do grupo de alunos ficou nos termos que o operador exigiu: **o
discriminante é a concentração, não a identidade**.

#### O teste, e a medição por mutação achou o sétimo

A varredura é por coluna, contra a lista, e **coluna nova entra sozinha**. Mas
ela não nasceu certa — quatro mutações históricas foram plantadas para medir, e
só duas reprovavam:

| Correção que a mutação exigiu | O que faltava |
|---|---|
| a varredura respeitar `conjuntos` | isentava a coluna **inteira**; a hora do ruído passava porque `hora` está na lista para outros dois conjuntos |
| separar coluna categórica de coluna de identidade | exclusividade de timestamp é verdade trivial, e reprovava contra o que não é vazamento |
| comparar entre seeds com **limiar de independência** | `assertNotEqual` sobre conjuntos é satisfeito por um elemento — **o mesmo defeito que o H1 apontou, reproduzido por mim**; e limiar fixo reprovava `minuto`, cuja sobreposição é menor que o acaso prediz |

**E a varredura corrigida achou o sétimo vetor, que nenhuma auditoria viu:**
`actor_user_id` das contas de ambíguos e suspeitos era **disjunto** das contas
dos normais — a conta separava "normal" de "ambíguo ou suspeito", e a lista não
licencia `actor_user_id` para nenhum dos três. As contas não normativas passaram
a sair de um pool comum.

#### O que mudou de forma, e é isso que fecha a classe

Antes: N asserções contra N vetores conhecidos, e o N+1 sempre existia.
Agora: uma propriedade sobre **toda coluna que o dataset escreve**, com a lista
declarada do que pode correlacionar. O vetor de identificador é hoje
**estruturalmente inexprimível** — `object_id` é atribuído depois do
embaralhamento, num ponto onde o conjunto já não está em escopo.

---

### 10.8 M2 — o artefato assinado, e o que ele torna não-ambíguo

**Os dois números do registro eram o sintoma.** A §4.4 e a §4.5 traziam valores
diferentes para a mesma medição — de antes e depois do embaralhamento —, e nada
nos dois dizia a qual commit cada um pertencia. Número de desempenho sem commit
fica ambíguo assim que a árvore anda uma vez, e ela andou seis. Os valores saíram
das duas seções pela Forma A, e o que sobrou aqui é o diagnóstico: **citá-los de
volta para explicar o defeito seria a §9.1 outra vez** — o texto que explica a
regra contendo a instância que a regra proíbe.

**A forma é a do `check_provas_de_container.py`, e o argumento é o da P4-10:** o
que exige rede e volume acontece **fora** da sessão do julgador, e o resultado
chega pronto — amarrado ao objeto por SHA. Isso não faz o auditor ver a execução;
amarra a evidência ao commit, que é a diferença entre "alguém rodou" e "rodou
nisto".

`prova_seed_completo.py` passou a gravar `.aurora-prova-do-seed.json` com o SHA
do checkout, máquina, data, stack, o número de linhas, os dois tempos e os
digests. **O arquivo é sempre escrito, inclusive quando a medição falha** — é
assim que "falhou" se distingue de "ninguém rodou".

`check_prova_do_seed.py` reprova em cinco direções, e a primeira é a que não pode
degradar:

| | |
|---|---|
| (a) | o arquivo **não existe** → reprova. Não ter a medição é o caso em que não se pode afirmar o item |
| (b) | o `commit` gravado diverge do `HEAD` → reprova |
| (c) | o arquivo está **versionado** → reprova: ele carrega o SHA do commit que mede, e um commit não contém o próprio SHA |
| (d) | falta máquina, data, python ou linhas → reprova. É `06` T3 virando predicado |
| (e) | a prova gravada diz que um dos itens **falhou** → reprova |

Nove eixos de prova negativa. No CI **só os probes** rodam, pelo mesmo motivo do
verificador das provas de container: o runner não tem — nem deve ter — o arquivo
que o operador escreve na máquina que mede.

**A exclusão do `prova_seed_completo.py` da allowlist continua válida**, e não
mudou: o que faltava não era o auditor rodar, era a gravação existir. O
verificador entra na allowlist; o script medido, não.

#### A medição assinada, e o número que agora tem dono

O que o verificador imprime, depois de conferir o SHA, tem esta forma — e é o
conteúdo, e não os valores, que importa aqui:

```text
commit   <o do candidato, e o verificador confere antes de imprimir>
maquina  <platform.platform()>
python   <versao>                  data     <data UTC da medicao>
seed     <RANDOM_SEED>             linhas   <total gerado>

item 1   <t1> s e <t2> s, de um orcamento de 300 s        PASSA
item 2   20 tabelas com SHA-256 igual nas duas rodadas    PASSA

audit_trail  <digest>
students     <digest>
```

**O digest de `students` é o mesmo desde a peça 4 e o de `audit_trail` mudou a
cada correção da Linha B** — e o par continua sendo a confirmação de escopo que
ele era: as sete correções tocaram a trilha e não o resto. É a única afirmação
desta seção que não depende de qual rodada produziu o artefato.

**A autoridade não é este texto — é o artefato.** Escrever o número aqui
reintroduziria, com outra forma, a ambiguidade que o M2 fecha: o registro é
histórico e não acompanha o candidato. Quem quiser o número deste commit roda o
verificador.

**E o mecanismo se exerceu duas vezes antes de eu entender o que ele exige.** A
medição foi gravada sobre `9042d9f`; o commit seguinte a invalidou, e o
verificador reprovou com *"a prova foi gravada sobre X e este checkout é Y"*.
Refiz sobre o novo candidato — e o commit que registrava o número invalidou a
prova de novo. **É um laço**, e a saída que eu enxerguei ali foi procedimental:
medir por último, depois de o código congelar, e não commitar nada depois. A §11
registra por que essa saída não bastou, e o que entrou no lugar dela.

---
## 11. A medição sai do registro e entra no lançador — Formas A e B

**As duas foram decididas pelo operador e implementadas juntas**, e é a junção
que fecha. Elas atacam o mesmo laço por lados diferentes: a **A** tira do registro
o número que envelhece, a **B** tira da disciplina a responsabilidade de medir na
hora certa.

### 11.1 O laço, medido antes de ser desenhado

O artefato do M2 carrega o SHA do checkout, e `check_prova_do_seed.py` reprova
quando ele diverge. A consequência não estava no desenho:

```text
medir  ->  registrar o número  ->  commitar  ->  a medição fica de outro commit
   ^                                                            |
   +------------------------------------------------------------+
```

**Ele se exerceu duas vezes na volta que o criou**, e a saída que eu enxerguei era
procedimental: medir por último, com o código congelado, e não commitar nada
depois. Está registrado na §10.8 — e a volta seguinte caiu nele de novo.

### 11.2 Forma A — nenhuma linha do registro carrega número de medição

| Onde | O que passou a dizer |
|---|---|
| quadro da DoD, itens 1 e 2 | *provado por `check_prova_do_seed.py`, que só imprime depois de conferir o SHA* |
| §4.4 e §4.5 | a narrativa sem os tempos e sem os digests: o que se mediu, por quê, e o que o **par** de digests confirma |
| §10.8 | o quadro vira **forma** — os campos, com o lugar do valor marcado |
| §10.8, o diagnóstico | os dois números que ele citava saíram: recitá-los para explicar a regra é a §9.1 |

**`06` T3 continua satisfeito**, e a leitura é literal: ele exige máquina, data e
stack **ao lado do número**. O número está no artefato, e é lá que os três estão.
O que o registro perde é *"quanto levou nesta máquina"* — e a perda não é real,
porque esse número nunca foi autoritativo: envelheceu em três rodadas e produziu
o M1 da terceira auditoria.

### 11.3 Forma B — o lançador mede, sobre o commit já congelado

**A A sozinha não bastava**, e o argumento é desta fase contra ela mesma: ela
deixa *"medir por último"* como **disciplina**, e a §9.6 registra que a disciplina
não segura nem quem acabou de escrever a regra — a correção herdou o defeito da
coisa corrigida, no mesmo turno. Três voltas confirmaram.

**O precedente é a P4-10, inteiro.** É a razão pela qual o gêmeo — as provas de
container — funciona: o que exige rede, volume e minutos acontece no lançador,
fora da sessão do julgador, e o resultado chega pronto e amarrado por SHA. A
medição do seed passou a ser a quinta etapa dessa lista.

O que ela precisa e o gêmeo não, com o motivo de cada uma:

| | Por quê |
|---|---|
| **banco descartável próprio** (`aurora_seed`, no servidor efêmero) | `prova_seed_completo.py` **TRUNCA vinte tabelas duas vezes**. Apontá-lo para `aurora_audit` destruiria, na mesma sessão, o banco em que a suíte do auditor vai rodar |
| **recriado a cada rodada** | mesmo motivo do venv da P3-4: banco reaproveitado carrega o esquema do commit anterior |
| **`CREATEROLE`** | a `0004` cria `academus_app`. `aurora_audit` é a `POSTGRES_USER` da imagem, então é superusuária do cluster. A role é objeto de **cluster**: se a migration do banco da stack já a criou, esta só faz o `GRANT` |
| **depois do `git worktree add`, e contra o worktree** | são três coisas e não uma: a migration aplicada é a do commit auditado, o código medido é o do commit auditado, e `prova_seed_completo.py` grava o artefato na raiz da árvore **de onde ele foi executado**, com o SHA que `git -C` resolve ali |
| **`RANDOM_SEED` fixo no lançador** | o mesmo argumento do `SEED` do `grava_provas_de_container.py`: seed que mudasse por rodada tornaria a medição incomparável com a anterior. Não é credencial |
| **falha BAIXO, e diz por quê** | sem a medição os itens 1 e 2 voltam a NÃO VERIFICADO, que é honesto. O log fica em `.aurora-worktrees/seed.log`, e a causa vai para a tela — a decisão do `diagnostica_stack` |

**O custo está aceito pelo operador:** ~5 min por rodada, somados aos ~3 das
provas de container.

### 11.4 O transporte fica, e vira o caminho degradado — a decisão que faltava

A §11.3 anterior deixou explícito que **manter ou remover o transporte era decisão
desta sessão, com o motivo escrito**. Ele fica, e muda de papel:

- com a **B**, o artefato **nasce dentro do worktree** e sobrescreve o que a cópia
  tiver posto ali. O transporte deixa de ser o caminho normal;
- ele continua sendo o que sobra **quando não há Docker nesta máquina** — a
  medição de quem mediu fora ainda vale, e quem a aceita ou recusa é o
  verificador, pelo SHA, exatamente como antes. Removê-lo trocaria um veredito
  parcial por nenhum na única situação em que ele ainda serve;
- **ele vem antes da medição, e não depois.** Invertida a ordem, uma cópia velha
  sobrescreveria a medição recém-feita deste commit — o defeito que a B existe
  para fechar, entrando pela porta do fallback.

**E o briefing do auditor distingue quatro estados, não dois** — deixar que ele
deduza qual foi é a forma que já custou uma rodada na Fase 3, quando o veredito da
guarda de base ia para o `stderr` e morria ali:

| Estado | O que ele diz ao auditor |
|---|---|
| `MEDIDA` | vínculo estrutural: o artefato nasceu aqui, sobre este commit |
| `REPROVOU` | a medição **aconteceu** e um dos dois itens falhou. É defeito da fase, e **não** ausência de ambiente |
| `TRANSPORTADA` | a medição desta rodada não aconteceu; divergência de SHA é o caso **normal**, não anomalia |
| `AUSENTE` | não há prova nenhuma, e os itens 1 e 2 são NÃO VERIFICADO |

**A segunda linha é a que quase não existiu.** `prova_seed_completo.py` grava o
artefato **mesmo quando a medição falha** — é assim que "falhou" se distingue de
"ninguém rodou" —, então um lançador que só olhasse o `rc` chamaria de
`TRANSPORTADA` um arquivo que é a medição reprovada **deste** commit. O auditor
leria "divergência de SHA é normal" onde o fato é item de DoD vermelho. A
separação é pelo SHA gravado no artefato, e não pelo código de saída.

### 11.5 A lição da volta — mecanismo sem caminho de exercício

`check_prova_do_seed.py` entrou na allowlist do auditor **como se funcionasse**.
Ele nascia inalcançável: o artefato era gravado na raiz da árvore de quem mede, o
worktree de auditoria é criado do zero a partir do commit, e o lançador
transportava apenas as provas de container. **O gate reprovaria em toda auditoria
futura** — desta fase e das próximas —, por ausência de um arquivo que nunca
chegava ali.

**É a §7.3 do registro da Fase 3 aplicada a mecanismo em vez de a teste** —
*"checagem só é exercida quando existe consumidor, e até lá ela parece pronta"*.
Aquela seção nomeia a
verificação que *parece* existir; esta é a mesma forma um andar acima — o
mecanismo admitido, allowlistado, documentado, e sem o caminho pelo qual é
exercido.

**E o que a torna dura é o gêmeo.** `check_provas_de_container.py` funciona
porque recebeu o transporte no mesmo commit que o criou. A forma completa era
conhecida, estava escrita ao lado, e mesmo assim eu admiti a metade — pelo mesmo
motivo que as sete instâncias de vazamento: **olhar o artefato novo e não a
cadeia que o faz existir**.

O antídoto não é lembrar. É a pergunta que a próxima admissão de mecanismo tem de
responder antes de entrar em qualquer lista: **por qual caminho ele é exercido no
ambiente em que vai julgar, e quem constrói esse caminho?**

### 11.6 A B foi exercida antes de entrar — e é a §11.5 aplicada a si mesma

**O achado que fechou esta volta foi um mecanismo admitido sem caminho de
exercício.** Entregar a correção dele sem exercer o caminho novo repetiria a forma
com um andar a mais, e este projeto já registrou sete instâncias de olhar o
artefato novo em vez da cadeia que o faz existir.

Então a cadeia foi rodada inteira, na máquina do operador, nesta ordem: subir a
stack efêmera, criar o banco descartável, `alembic upgrade head` nele — as quatro
revisões, incluindo o `CREATE ROLE` que exige `CREATEROLE` — e a medição completa
com as duas rodadas. **Ela saiu `rc=0`, e os dois itens passaram.**

**E há uma confirmação que não era esperada e vale mais que o `rc`:** os dois
digests saíram **idênticos** aos das medições anteriores com o mesmo
`RANDOM_SEED`. Isso prova a decisão do seed fixo no lançador pelo lado que
importa — ele reproduz o mesmo dataset, e não apenas *um* dataset determinista.

**O que isto não prova, e está dito porque não prova:** a medição foi exercida a
partir da árvore principal, com o Postgres efêmero de pé, e **não de dentro de um
worktree de auditoria em curso**. O que resta não exercido é o acoplamento do
bloco ao resto do lançador — a ordem, o `VENV_BIN`, o `cd "$WT"` —, e é a primeira
reauditoria que o exerce. O limite é o mesmo do `--headless`: caminho que existe e
nunca rodou é atestação esperando acontecer, e a diferença aqui é que **a
reauditoria seguinte o roda por construção**, sem ninguém precisar lembrar.

---

## 12. A quinta rodada — PASS, e o que sai declarado

**PASS contra `027f07e7`, sem BLOCKER e sem HIGH**, com um MEDIUM e três LOW.
Relatório em `docs/progress/audit_20260818T181506Z.md`. A guarda de base saiu
**PORTA**: `HEAD` conferido, árvore limpa, âncora em
`docs/process/phase_anchors.tsv` idêntica à base informada.

### 12.1 O que o julgador executou, e por que a lista é o resultado

Isto é a §9.11 medida em vez de afirmada:

| O que rodou | Resultado |
|---|---|
| a suíte inteira, contra Postgres real | **402 testes, `OK`, nenhum `skipped`** |
| os quatro invariantes arquiteturais | verdes, com `phase0_negative_tests.py` provando que os seis verificadores ainda reprovam contra violação plantada |
| os seis verificadores novos da fase | todos com **prova negativa executada** e verde |
| as três armadilhas típicas de teste que não prova o requisito | procuradas uma a uma; **nenhuma encontrada** |

Nenhum item de DoD ficou NÃO VERIFICADO. **E os limites do próprio julgador estão
no relatório dele**, em seção própria — a medição do seed e as provas de container
não foram presenciadas, o número do item 1 é de máquina, a partição em escala
completa não foi executada, e o pack real com o `RANDOM_SEED` de produção não é
visto por CI nenhum. A amarração é o SHA, e não a palavra de quem mediu.

### 12.2 M1 — a role que conecta, e por que o MEDIUM não vira item de DoD

**O auditor registrou explicitamente que nenhum requisito é violado.** `02` §4
item 2 e `05` §7 exigem que `academus_app` exista `INSERT`-only com os três
`REVOKE`, e ela existe — conferido no catálogo do Postgres, não por comportamento.
O MEDIUM é **consequência operacional**, e é a **P5-3**, que já estava aberta com
destinatário operador e gatilho declarado.

O que segura hoje está dito na §7.1 e não se repete aqui: o trigger recusa a
todos, inclusive ao dono, e a cadeia torna visível a reescrita de quem o
desabilitar. E o limite é **exercido** — a técnica da §9.12 —, com dois testes que
ficam vermelhos no dia em que a segunda credencial existir.

### 12.3 Os três LOW — dois ficam declarados, um virou pendência

| | O que é | Destino |
|---|---|---|
| **L1** | a posição da quebra é extraída por *parsing* da mensagem de `ChainBroken`, que não carrega campo estruturado | **fica declarado, com a condição que o relatório dá e que não pode sumir aqui:** neste mesmo diff a mensagem do event store perdeu o trecho `evento {event_id}`, e **se um identificador iniciado por dígito precedesse a sequência, a posição reportada seria outra**. Os três casos de T7 têm teste verde hoje. A correção é dar campo estruturado à exceção do core — mexer em `range-core/` por conveniência de um domínio, e a fronteira do invariante 1 é o que impede que isso seja "de passagem" |
| **L2** | a partição da Linha B é exercida em `ESCALA_REDUZIDA` | **fica declarado**, e a linha do item 5 diz isso. O auditor conferiu que os pools de conta são disjuntos **por construção**, de modo que a propriedade não depende do volume de fundo — **e classificou o próprio argumento como estrutural, por leitura de `dataset.py:373-386`, e NÃO como medição.** As duas metades andam juntas: a segunda é dele, está na seção de limites do relatório, e sem ela isto viraria "o auditor verificou em escala" |
| **L3** | o gabarito não tem produtor em disco | virou **P5-6**, com destinatário Fase 7 e gatilho no commit do subcomando de pack |

**Os dois que ficam não viraram pendência de propósito.** Pendência é para o que
tem condição de vencimento e destinatário; limite conhecido de mecanismo que
funciona é declaração — e nos dois casos a declaração tem mecanismo, que é a §9.12
outra vez. Abrir pendência para tudo que é LOW transforma o inventário em lista
de desejos, e o efeito é que ninguém lê a parte que cobra.

### 12.4 A linha de status tem forma, e a primeira que escrevi era uma terceira

**Aconteceu escrevendo este fechamento, e vale registrar porque o mecanismo que
deveria pegar estava escrito para pegar exatamente isto.**

`check_readme_atual.py` decide *"a fase fechou?"* pela linha `**Status:` do
cabeçalho, e reconhece **duas** formas — `CONCLUÍDA` e `AUDITADA — PASS` —,
porque os registros usam duas. A primeira versão desta linha dizia
`**Status: FECHADA`. O verificador **não reclamou da forma**: ele apenas não viu a
Fase 5 fechar, continuou computando *"última fase concluída: 4"*, e o vermelho que
apareceu foi outro — a contagem de relatórios de auditoria no README.

**O docstring de `_status_da_proxima` prevê este caso literalmente** — *"se a Fase
5 fechar numa TERCEIRA forma, a fonte continuaria dizendo 4, o documento
continuaria dizendo 4, e os dois concordariam sobre um fato falso"* — e a guarda
que ele instalou cobre **linha ausente**, não **forma nova**. É a §9.8 outra vez,
em miniatura: a pergunta certa estava escrita ao lado do mecanismo, e o mecanismo
cobria a metade barata dela.

**Corrigido usando a forma reconhecida**, que é o certo — inventar vocabulário de
status é o defeito, não a vítima dele. **O que fica declarado:** a guarda continua
sem cobrir forma nova, e fechar o buraco é fazer o verificador reprovar linha de
status que não case com nenhuma das duas formas. É correção de uma linha, e é
**da fase que a fizer** — mexer no verificador dentro do commit de fechamento da
fase que ele julga é a forma que este registro passou cinco rodadas separando.

### 12.5 A releitura do auditor sobre a §7 — e as oito divergências que ela achou

**O auditor recusou redigir esta §7, e a recusa está certa.** Se quem emite o
veredito escreve o artefato que a próxima auditoria trata como evidência, o
documento desfaz no papel a separação que a Forma B acabou de estabelecer no
mecanismo — a medição saindo da sessão do julgador. Redigir é de quem implementou.

**Conferir é dele, e é auditoria.** Pedido: a §7 corresponde ao que a quinta
rodada de fato verificou? Saída em divergências — SUPERAFIRMAÇÃO, IMPRECISÃO,
OMISSÃO —, com a instrução explícita de apontar e **não** propor redação.

**O veredito da releitura: nenhuma SUPERAFIRMAÇÃO.** Toda prova citada existe e é
a que o relatório registra; nenhuma linha atribui cobertura que a auditoria não
sustente. Os números do quadro foram conferidos contra `02` §6.1, o quadro contra
`07` Fase 5 linha a linha, e os dois verificadores por SHA foram executados.

**Oito divergências, e o padrão delas é um só: a §7 afirmava de MENOS.** Sete das
oito eram limite que o relatório declara e a linha do registro não carregava — o
inverso do defeito que se procura num fechamento, e ainda assim defeito, porque
limite que só existe três seções adiante não acompanha a linha que alguém cita.

| O que estava errado | Corrigido para |
|---|---|
| **§7.3 — o par de estados errado**, e no parágrafo cujo propósito é impedir exatamente essa leitura: o estado no commit de fechamento é `TRANSPORTADA` (o artefato **existe**, o SHA diverge) e não `AUSENTE` (não há prova nenhuma) | o estado nomeado certo, e o par que não pode ser confundido dito como a §11.4 o diz: `TRANSPORTADA` × `REPROVOU` |
| item 3 do quadro sem marca de limite, enquanto o item 5 tinha | a marca na linha, apontando a §7.1 e a P5-3 |
| item 6 sem marca de limite | a marca na linha, apontando a P5-6 |
| item 4 sem o limite que o relatório nomeia para ele — truncamento de cauda | o limite na linha, com o teste que o afirma |
| §7.2 — *"T7: os três critérios, com quatro testes"*, quando os quatro cobrem dois dos três | a atribuição correta: critérios 1 e 2 por `TrilhaEhAppendOnly`, critério 3 por `CadeiaDetectaAdulteracao` |
| §7.2 — a linha de T15 lida como auditada, e o relatório não menciona T15 | marcada como afirmação minha, conferida na árvore; e T6 marcada como parcial pelo mesmo critério |
| §12.3 L2 — *"o auditor verificou independentemente"*, ficando com a metade boa | as duas metades: ele conferiu **por construção**, e classificou o próprio argumento como **estrutural e não medição** |
| §12.3 L1 — a condição da fragilidade omitida | a condição, do relatório: identificador iniciado por dígito precedendo a sequência mudaria a posição reportada |

E uma oitava, menor: a prova de container não é de um commit "anterior" na
história — `1d2f6395` **não é ancestral** do `HEAD`, porque o rebase da P4-9
reescreveu aquela linha. Para o verificador tanto faz, e é por isso que o
predicado é igualdade de SHA e não ancestralidade; para o registro, não tanto
faz.

**O que a releitura demonstra, e é por isso que ela fica registrada.** As oito
foram achadas **lendo o registro contra o relatório**, não relendo o código — e
sete delas eram do tipo que nenhum teste pega, porque o defeito é o documento
dizer menos do que a evidência sustenta. Um fechamento escrito por quem
implementou tende a esse erro: quem sabe onde o limite está escrito não sente
falta dele na linha. Este é o argumento a favor da divisão — **redigir de um lado,
conferir do outro** —, e ele não é sobre confiança, é sobre o que cada lado
consegue ver.
