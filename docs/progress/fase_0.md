# Fase 0 — Specification Freeze

Registro de progresso conforme `docs/spec/07_IMPLEMENTATION_PHASES.md` §Registro de progresso.

A Fase 0 não aparece na tabela de visão geral do `07`: ela é regida por `docs/process/PHASE_0_CHECKLIST.md`, deliberadamente fora da especificação normativa. O registro de progresso vale para ela mesmo assim.

---

## 0. A Fase 0 FALHOU na primeira auditoria de checkpoint

**Veredito: FAIL.** 1 BLOCKER, 4 HIGH, 3 MEDIUM, 2 LOW.

O commit `1073743` — que entregava os seis verificadores e cujo registro original afirmava que o teste negativo passava — **não** passou no gate. Isto fica registrado em primeiro lugar, e não em rodapé, porque é o dado mais útil deste arquivo: o mecanismo de defesa mordeu a primeira coisa que examinou, e mordeu o trabalho de quem escreveu o próprio mecanismo.

Os seis verificadores saíam `0` em árvore limpa e `1` contra cada probe. Isso era verdade e era insuficiente: **os probes não tocavam as fronteiras que importavam.** Um verificador cego combinado a um probe plantado dentro da região que ele enxerga produz um teste verde que não prova nada. Foi exatamente o achado do BLOCKER.

### Findings e destino

| ID | Severidade | Resumo | Destino |
|---|---|---|---|
| B1 | BLOCKER | `objective_ids` não era verificado em `range-core/engine/`, `/clock/`, `/state/`, `/telemetry/`, `/evidence/`, `/rubrics/` | corrigido em `22bc144` |
| H1 | HIGH | `check_contract_literals.py` ignorava TypeScript; o gate real não cobria o front-end | corrigido em `8e5dedb` |
| H2 | HIGH | `expect_fail()` aceitava qualquer `rc != 0`; crash de ferramenta contava como detecção | corrigido em `3a8477d` |
| H3 | HIGH | `check_synthetic_data.py` não verificava identificador (CPF) | corrigido em `9f786ec` |
| H4 | HIGH | Allowlist do auditor não liberava o harness negativo nem os hooks | corrigido em `aec88a8` |
| M1 | MEDIUM | O CI nunca executava o harness negativo | corrigido em `35f2eb8` |
| M2 | MEDIUM | Probe do `codegen` nunca exercita o ramo de divergência | **pendência aberta** — §6 P6 |
| M3 | MEDIUM | Isenções de caminho casam qualquer segmento, em qualquer profundidade | **pendência aberta** — §6 P7 |
| L1 | LOW | Separador de segmentos do hook do auditor quebra comando de leitura legítimo | **pendência aberta** — §6 P8 |
| L2 | LOW | `check_security_constraints.py` não varre os próprios hooks | **pendência aberta** — §6 P9 |

Ordem de correção determinada pela auditoria: H4 primeiro e isolado, porque enquanto ele existisse o auditor era **estruturalmente incapaz** de executar a prova central e auditava por inferência de leitura de código. Toda auditoria anterior a `aec88a8` foi inferência.

### Segunda auditoria: PASS, sem blocker

Executada sobre o commit corrigido. **Foi a primeira auditoria capaz de executar o harness em vez de inferir por leitura**, porque H4 já estava corrigido.

Veredito PASS, com três correções exigidas antes do `finalize` e três pendências mantidas abertas:

| ID | Severidade | Resumo | Destino |
|---|---|---|---|
| M1 | MEDIUM | O registro afirmava capacidade de rastreabilidade que o próprio HEAD desabilitou | **pendência aberta** — §6 P11; texto do §7 O4 corrigido |
| M3 | MEDIUM | Isenções de caminho casavam qualquer segmento, em qualquer profundidade | corrigido em `76e04c9` |
| M2 | MEDIUM | `RULE_DIVERGENT` do `codegen` nunca falhou contra violação plantada | corrigido em `8b129d2` |
| L3 | LOW | Docstring de `_common.py` contradizia o contrato estabelecido pelo H2 | corrigido em `6ed9993` |
| L1 | LOW | Separador de segmentos do hook do auditor quebra comando de leitura legítimo | **pendência aberta** — §6 P8 |
| L2 | LOW | `check_security_constraints.py` não varre os próprios hooks | **pendência aberta** — §6 P9 |

O L3 merece nota porque é a categoria mais traiçoeira: o cabeçalho de `_common.py` ainda instruía *"qualquer valor diferente de zero conta como detecção"*, exatamente o defeito que o H2 corrigira três commits antes. Documentação interna que sobrevive à correção e orienta a próxima pessoa a reintroduzi-la.

O M3 confirma o risco antecipado no próprio registro da primeira auditoria: ao trocar a varredura por negação padrão (B1), a isenção de caminho virou a **única** fronteira do invariante 4, e ela casava segmento em qualquer profundidade. `domains/<adapter>/api/metrics/emit.py` ficava isento por ter um `metrics` no meio do caminho. É a fronteira que a Fase 1 herda quando `range-core/` e `domains/` passarem a existir de fato.

Além dessas, uma regressão **minha** foi encontrada e corrigida entre as duas auditorias, em `c8c2be3` — ver §7 O4.

### Terceira auditoria: PASS, dois HIGH

PASS sem blocker, mas com dois HIGH — e por `docs/process/WORKFLOW.md` §Ciclo por fase, HIGH fecha antes do `finalize`.

| ID | Severidade | Resumo | Destino |
|---|---|---|---|
| H2 | HIGH | `finalize_phase0.sh` declarava "FASE 0 CONCLUÍDA" e criava `spec-v1.0` sem executar os itens 10 e 11 da DoD | corrigido em `6567b2b` |
| H1 | HIGH | Ramo de `event_type` do invariante 2 e bloco de artefatos de evento do `codegen` sem probe algum | corrigido em `154cb00` |
| M1 | MEDIUM | `spec_freeze` define "código" como só três diretórios; `tools/`, `scripts/`, `.claude/` e `.github/` ficam fora | corrigido em `012ce3a` — §6 P12 |
| M2 | MEDIUM | Deny de secrets cobre `Read` e `Edit`, mas não `Write` | **pendência aberta** — §6 P13 |
| M3 | MEDIUM | `check_event_envelope.py` só varre `.py`; camada web fora do invariante 4, sem declaração | **pendência aberta** — §6 P14 |
| L1 | LOW | `tools/README.md` e `README_FIRST.md` ainda instruem que os seis verificadores não existem | **pendência aberta** — §6 P15 |
| L2 | LOW | Hook do auditor bloqueia mais comandos de leitura legítimos que o descrito em P8 | **pendência aberta** — §6 P16 |
| L3 | LOW | `.env.example` não existe, embora dois documentos o tratem como presente | **pendência aberta** — §6 P17 |

O H2 é o achado mais grave das três rodadas em termos de consequência, ainda que classificado HIGH e não BLOCKER: a tag `spec-v1.0` nasceria de um mecanismo — `spec_freeze` — **nunca demonstrado**, e é a partir dela que a especificação vira imutável.

### Quarta auditoria: PASS, sem BLOCKER e sem HIGH

Primeira rodada sem achado bloqueante nem HIGH. Quatro MEDIUM e cinco LOW.

| ID | Severidade | Resumo | Destino |
|---|---|---|---|
| M2 | MEDIUM | O procedimento do item 10 da DoD não exercitava a regra que afirmava provar | corrigido em `7302bd1` |
| M1 | MEDIUM | Conjunto `CODE` do `spec_freeze` omite `user-scope/` — correção do P12 incompleta | corrigido em `ee7731d` — §6 P18 |
| M3 | MEDIUM | Deny de secrets ainda não cobre `Write` | **pendência aberta** — §6 P19 (reconfirma P13) |
| M4 | MEDIUM | `check_event_envelope.py` só varre `.py`, limitação não declarada no arquivo | **pendência aberta** — §6 P20 (reconfirma P14) |
| L1 | LOW | `tools/README.md` e `README_FIRST.md` ainda dizem que os seis não existem | **pendência aberta** — §6 P21 (reconfirma P15) |
| L2 | LOW | `README_FIRST.md` e `PHASE_0_CHECKLIST.md` descrevem o `finalize` anterior ao H2 | **pendência aberta** — §6 P22 |
| L3 | LOW | Hook do auditor segue bloqueando leitura legítima, com modo novo | **pendência aberta** — §6 P23 (reconfirma P8 e P16) |
| L4 | LOW | `check_security_constraints.py` não varre `.claude/hooks/` nem `user-scope/hooks/` | **pendência aberta** — §6 P24 (reconfirma e amplia P9) |
| L5 | LOW | Actions do CI presas a tag major mutável | **pendência aberta** — §6 P25 |

**Dois desses achados são falhas minhas das rodadas anteriores, e ficam nomeadas como tais:**

- o **M1** mostra que minha correção do P12 foi **incompleta**. Ampliei o conjunto `CODE` para `tools/`, `scripts/`, `.claude/`, `.github/` e os `.sh` de raiz, mas deixei `user-scope/` de fora — e é justamente lá que vive a fonte versionada do `checkpoint-auditor` e do seu hook, copiada para `~/.claude/` pelo `bootstrap.sh`. Pelo próprio critério que usei ("ser executável / mecanismo que aplica a spec"), `user-scope/` deveria ter entrado na mesma correção;
- o **L2** é instância **nova** da categoria que o P10 e o P15 nomeiam — documentação que sobrevive à correção e a contradiz — **criada pela minha correção do H2**. Mudei o fluxo do `finalize_phase0.sh` para parar antes da tag, corrigi o `fase_0.md`, e não toquei no `README_FIRST.md:12` nem no `PHASE_0_CHECKLIST.md:104`, que seguem descrevendo o script anterior.

O L2 é o achado mais instrutivo da rodada: a categoria estava nomeada, registrada duas vezes, e mesmo assim reincidi na correção seguinte. Corrigir código e deixar a documentação para trás não é distração pontual — é padrão, e nesta fase já apareceu quatro vezes (P10, P15, P17, P22).

### Quinta auditoria: apenas um achado transmitido

Da quinta rodada chegou a este registro exatamente **um** achado — o M1, sobre `CLAUDE.md` estar fora do conjunto `CODE` — corrigido em `32bdc05` e registrado em §6 P26. **Veredito, contagem e demais achados não foram transmitidos**, e isso fica declarado em vez de suposto.

A causa é **P11**: sem persistência do relatório, cada rodada chega por transcrição manual, e o que não for transcrito não existe para este registro. O mesmo mecanismo produziu a terceira confusão de IDs entre rodadas desta fase — o achado foi inicialmente classificado como decisão do operador, porque chegou sem identificação de rodada e o M1 conhecido até então era o da quarta auditoria.

**Dois desses findings acusam este próprio registro de imprecisão, e ambos procedem:**

- o **M1** contesta a classificação "formalmente conforme" que o §7 O2 dava ao commit inicial misturar `docs/spec/` e `tools/`. O texto normativo do `CLAUDE.md` diz *código*, não "range-core, domains e contracts". O O2 foi corrigido;
- o **L1** mostra que a afirmação de fechamento do P10 — *"verificado que nenhum outro ponto do repositório repete a instrução"* — era mais larga do que a verificação feita, que cobriu apenas a instrução de código de saída. O status do P10 foi corrigido para dizer o que de fato foi verificado.

### O que mudou no harness, e por quem

`scripts/phase0_negative_tests.py` foi alterado em B1, H2, H1 e H3. Isso contraria o princípio registrado em §6 P1 — *o implementador não mexe no teste que o julga*. A distinção que autoriza estas mudanças: **foram determinadas pela auditoria**, não escolhidas por quem estava sendo avaliado. P1 continua não corrigida justamente porque nasceu de julgamento meu, não de finding.

Probes passaram de 6 para 8, e a exigência deixou de ser "saiu diferente de zero" e passou a ser "saiu `1` e citou o arquivo plantado".

---

## 1. Resumo técnico

Implementados os **seis verificadores de invariante** em `tools/`, invocados por `.github/workflows/invariants.yml`. Nenhum código de aplicação.

Todos seguem o contrato de `PHASE_0_CHECKLIST.md` §Interfaces obrigatórias: saída `0` em árvore válida, diferente de `0` em violação, impressão de caminho e motivo, **apenas stdlib**, nenhuma escrita em disco, determinismo.

| Verificador | Invariante | Técnica |
|---|---|---|
| `check_core_boundary.py` | `range-core/` não importa de `domains/` | AST: `Import`, `ImportFrom` (inclusive relativo resolvido), `importlib.import_module` e `__import__` com literal |
| `check_contract_literals.py` | nenhum literal de flag ou `event_type` fora dos geradores | leitura dos contratos + AST sobre `ast.Constant` |
| `check_event_envelope.py` | nenhum evento emitido carrega `objective_ids` | AST no caminho de emissão, excluindo camadas de projeção |
| `check_security_constraints.py` | restrições funcionais de `05_SECURITY_REQUIREMENTS.md` §1 | AST sobre `ast.Call` |
| `check_synthetic_data.py` | IPs e domínios em faixas sintéticas | parse estruturado (json/jsonl/csv/YAML) + `ipaddress` |
| `codegen.py --check` | constantes Python/TypeScript sincronizadas | geração em memória e comparação com o disco |

`tools/_common.py` concentra parser YAML de subconjunto estrito, varredura determinística, leitura de contrato e relatório.

### Duas decisões de implementação

**Detecção por chamada, não por texto, em `check_security_constraints.py`.** `.claude/hooks/check_architecture.py` e `scripts/phase0_negative_tests.py` contêm `eval(` e `shell=True` dentro de *strings*. A AST os enxerga como `Constant`, nunca como `Call` — zero falso positivo. Grep marcaria os dois arquivos. É o argumento concreto para a exigência de AST em `01_ARCHITECTURE.md` §2.

**`sys.dont_write_bytecode = True` nos seis pontos de entrada.** O import de `_common` criava `tools/__pycache__`, o que viola o requisito 5 ("não modificar arquivos quando executados em modo de verificação"). O diretório está no `.gitignore`, mas o requisito é sobre escrita, não sobre rastreamento — e o worktree do `checkpoint-auditor` espera árvore intacta.

### Parser YAML próprio

A regra "apenas stdlib na Fase 0" exclui PyYAML, e a leitura de `flags.yaml` é necessária a dois verificadores. O parser cobre um subconjunto pequeno — mapeamentos e sequências em bloco, sequências em fluxo, escalares, comentários, documento único — e **recusa com erro explícito** ancoras, aliases, merge keys, escalares multilinha, mapeamentos em fluxo, tabulação na indentação e múltiplos documentos.

Um parser tolerante seria pior que grep: faria o verificador passar por ter lido o contrato errado, em silêncio.

---

## 2. Estrutura de diretórios

```
tools/
  README.md                      inventário da fase (entregue com o bundle)
  _common.py                     parser YAML, varredura, contratos, relatório
  check_core_boundary.py
  check_contract_literals.py
  check_event_envelope.py
  check_security_constraints.py
  check_synthetic_data.py
  codegen.py                     apenas --check nesta fase
docs/progress/
  fase_0.md                      este arquivo
```

Nenhum outro diretório foi criado. `range-core/`, `domains/`, `contracts/` e `scenarios/` continuam inexistentes — são OUTPUTS da Fase 1. Os seis verificadores tratam a ausência desses diretórios como árvore válida.

### Contrato de artefatos gerados

`codegen.py --check` espera os artefatos **co-localizados com a fonte canônica**:

```
domains/<adapter>/flags.yaml   ->  domains/<adapter>/generated/flags.py
                                   domains/<adapter>/generated/flags.ts
contracts/events.schema.yaml   ->  contracts/generated/events.py
                                   contracts/generated/events.ts
```

Co-localizado, e não sob `range-core/`, porque um artefato com nome de adapter dentro do core exigiria exceção no próprio `check_core_boundary.py`. **Invariante com exceção é invariante morto.** Com este layout, implementar o adapter `prontus` não toca `range-core/` em lugar nenhum.

Este layout é contrato herdado pela Fase 1.

---

## 3. Endpoints, migrations e variáveis de ambiente

**Nenhum, nos três casos** — e isso é conformidade, não lacuna.

`PHASE_0_CHECKLIST.md` abre proibindo código de aplicação, `docker-compose` e migration na Fase 0. Não há serviço, não há banco, não há Alembic. `RANDOM_SEED` em `.env` é DoD da **Fase 1**, não desta.

---

## 4. Verificação executada

> Um verificador que nunca falhou contra uma violação plantada não é um verificador; é um script que sai com zero.

**Esta seção descreve o estado APÓS as correções da primeira auditoria.** A versão anterior deste registro afirmava, com razão, que o harness passava — e o harness passava sem tocar as fronteiras que importavam. Passar no teste negativo é condição necessária, nunca suficiente; a qualidade do probe é parte do que precisa ser auditado.

**Teste negativo obrigatório** — `python scripts/phase0_negative_tests.py` passa com **13 probes**, sete a mais que a entrega original:

| Probe | Onde é plantado | Fronteira que exercita |
|---|---|---|
| `check_core_boundary.py` | `range-core/_phase0_probe_bad.py` | import direto de `domains/` |
| `check_contract_literals.py` | `domains/academus/_phase0_probe_literal.py` | literal de flag em Python |
| `check_contract_literals.py` (TypeScript) | `domains/academus/web/_phase0_probe_literal.tsx` | literal de flag em TS — **novo, H1** |
| `check_event_envelope.py` | `range-core/engine/_phase0_probe_event.py` | **replantado, B1** — antes em `domains/academus/api/` |
| `check_event_envelope.py` (isenção ancorada) | `domains/academus/api/metrics/emit.py` | segmento `metrics` fora do core — **novo, M3** |
| `check_contract_literals.py` (isenção ancorada) | `domains/academus/api/contracts/handler.py` | segmento `contracts` fora da raiz — **novo, M3** |
| `check_contract_literals.py` (event_type) | `contracts/events.schema.yaml` + `domains/academus/api/handler.py` | literal de `event_type` — **novo, H1 da 3ª auditoria** |
| `check_security_constraints.py` | `range-core/_phase0_probe_security.py` | execução dinâmica |
| `check_synthetic_data.py` | `scenarios/_phase0_probe/fixture.jsonl` | IP roteável e domínio real |
| `check_synthetic_data.py` (identificador) | `scenarios/_phase0_probe_cpf/alunos.jsonl` | CPF válido — **novo, H3** |
| `codegen.py --check` (ausente) | `domains/_phase0_codegen_probe/flags.yaml` | artefato gerado ausente |
| `codegen.py --check` (divergente) | `domains/_phase0_divergent_probe/generated/flags.py` e `.ts` | conteúdo fora de sincronia — **novo, M2** |
| `codegen.py --check` (artefatos de evento) | `contracts/events.schema.yaml` | bloco de eventos do codegen — **novo, H1 da 3ª auditoria** |

Cada probe exige agora `rc == 1` **e** menção ao arquivo plantado. `rc = 2` (crash de ferramenta) é rejeitado explicitamente.

**Prova de regressão do B1** — o verificador anterior sai `0` contra o probe replantado em `range-core/engine/`, e o corrigido sai `1`. Sem o replante, a correção de cobertura ficaria sem prova.

**Árvore limpa** — os seis saem `0`, sem escrita e sem resíduo.

**Determinismo** — execuções repetidas produzem saída byte-idêntica.

**Casos fora da cobertura do harness** — verificados, todos corretos:

| Caso | Esperado | Resultado |
|---|---|---|
| `import domains.academus as d` (alias) | violação | detectado |
| `importlib.import_module('domains.academus')` | violação | detectado |
| `import hashlib`, `cryptography`, `jwt` | **permitido** | não acusado |
| `objective_ids` em `engine/`, `clock/`, `state/`, `telemetry/`, `evidence/`, `rubrics/`, `events/` | violação | detectados (B1) |
| `objective_ids` em `objectives/`, `aar/`, `metrics/` | **permitido** | não acusados |
| `objective_ids` em `domains/*/api/` | violação | detectado |
| literal de flag em `.tsx`, `.ts`, template literal | violação | detectados (H1) |
| literal de flag em comentário de linha e de bloco TS | **permitido** | não acusados |
| CPF válido, formatado e nu | violação | detectados (H3) |
| CPF com verificador errado, CPF de dígito repetido, telefone e matrícula de 11 dígitos | **permitido** | não acusados |
| `192.0.2.10`, `10.1.2.3`, `2001:db8::1`, `example.com`, `relatorio.final.pdf` | **permitido** | não acusado |
| `www.microsoft.com` em URL; `1.1.1.1` em CSV | violação | detectados |
| artefato gerado presente porém divergente | violação | detectado |
| literal de flag dentro de `generated/` | **permitido** | não acusado |
| literal de flag fora de `generated/` | violação | detectado |
| flag com erro de digitação, não declarada | violação | detectado |

O último caso merece nota: além de casar literais contra o contrato, `check_contract_literals.py` acusa string com forma `<adapter>.<nome>` que **não** está declarada em nenhum `flags.yaml`. É o erro de digitação que viraria flag desconhecida em runtime e que a detecção por conjunto declarado, sozinha, deixaria passar.

**Smoke tests de hooks** — todos conforme `PHASE_0_CHECKLIST.md`:

| Hook | Cenário | Esperado | Obtido |
|---|---|---|---|
| `check_architecture.py` | import de `domains/` em `range-core/` | 2 | 2 |
| `check_architecture.py` | edição de `docs/spec/` fora de branch `spec-change/` | 2 | 2 |
| `readonly_bash.py` | escrita deliberada (`rm -rf`) | 2 | 2 |
| `readonly_bash.py` | `python tools/check_core_boundary.py` | 0 | 0 |
| `scenario_scope.py` | Write fora de `scenarios/` | 2 | 2 |

---

## 5. Definition of Done — status

Referência: `docs/process/PHASE_0_CHECKLIST.md` §Definition of Done.

| # | Item | Status |
|---|---|---|
| 1 | Os seis verificadores liberam árvore limpa | ✅ |
| 2 | Os seis detectam as violações externas de `phase0_negative_tests.py` | ✅ após B1, H1, H2 e H3. Estava marcado ✅ antes da auditoria com probes que não tocavam as fronteiras |
| 3 | Hook bloqueia import de `domains/`, edição de `docs/spec/` e literal de flag | ✅ cobertura de `objective_ids` no hook ampliada em B1 |
| 4 | Hook do auditor bloqueia escrita e libera verificadores de leitura | ⚠️ parcial — H4 corrigido (harness e hooks liberados), mas comandos de leitura legítimos seguem bloqueados: `\|` entre aspas (§6 P8), `merge-base`, `2>&1`, `for-each-ref`, `sort` (§6 P16) |
| 5 | Hook do `scenario-designer` bloqueia Write/Edit fora de `scenarios/` e Bash fora da allowlist | ⚠️ parcial — escopo de Write/Edit verificado; allowlist de Bash (`scenario_bash.py`) **não** exercitada |
| 6 | `ground_truth.yaml` e `GM_NOTES.md` **não** estão no `.gitignore` | ✅ aparecem apenas em comentário que documenta o versionamento deliberado |
| 7 | `.env`/secrets negados em `.claude/settings.json` | ⚠️ parcial — `Read` e `Edit` de `.env`, `.env.*` e `secrets/**` negados; **`Write` não** (§6 P13). Leitura, que é o risco principal, está coberta; criação e sobrescrita não |
| 8 | Auto Mode desabilitado para este projeto | ✅ `defaultMode: default`, `disableAutoMode: disable` |
| 9 | Primeiro push de `main` deixa `arquitetura` e `seguranca` verdes | ⛔ commit inicial existe; **sem push**, sem evidência de CI |
| 10 | PR descartável confirma que `spec_freeze` falha com spec e código juntos | ⛔ bloqueado por 9 |
| 11 | PR descartável confirma título `spec-change:` para alteração só de spec | ⛔ bloqueado por 9 |
| 12 | Branch protection em `main` exige `arquitetura`, `spec_freeze`, `seguranca` | ⛔ bloqueado por 9 |
| 13 | `spec-v1.0` criada depois de CI e branch protection | ⛔ nenhuma tag existe |
| 14 | `/doctor` sem apontamentos relevantes | ✅ executado nesta sessão, sem achados |

**Quem executa o quê, corrigido após o H2 da terceira auditoria.** `bash finalize_phase0.sh` executa os itens **9, 12 e 13** — push, espera de CI, branch protection e tag. Os itens **10 e 11 são manuais**: exigem PR descartável comprovando que `spec_freeze` reprova spec+código no mesmo PR e que alteração só de spec exige título `spec-change:`.

O script parava de declarar "FASE 0 CONCLUÍDA" e criar `spec-v1.0` sem que 10 e 11 tivessem sido executados. Agora ele para antes da tag, imprime os comandos exatos dos dois PRs descartáveis, e só cria a tag numa segunda invocação explícita: `bash finalize_phase0.sh --dod-10-11-verificados`. A flag é a afirmação do operador de que executou os dois PRs e viu `spec_freeze` reprovar nos dois.

**A Fase 0 não está concluída enquanto os itens 9 a 13 não passarem.**

**Item 15, não listado no checklist mas exigido por `docs/process/WORKFLOW.md`: auditoria de checkpoint com veredito PASS.** Status ✅ **com ressalva** — quatro auditorias: FAIL; PASS com três correções; PASS com dois HIGH; e **PASS sem BLOCKER e sem HIGH** (§0). Por `WORKFLOW.md` §Ciclo por fase, o critério de bloqueio é BLOCKER e HIGH, e a quarta rodada não tem nenhum dos dois. O único MEDIUM que a auditoria pediu para fechar antes dos itens 10 e 11 está corrigido (`7302bd1`).

A ressalva: sete pendências da quarta rodada seguem abertas (§6 P19–P25). A oitava, **P18**, tocava o próprio `spec_freeze` que os itens 10 e 11 vão demonstrar, e por isso foi corrigida em `ee7731d` antes deles.

### Estado do repositório neste registro

`main`, working tree limpo, remoto `origin` configurado, **sem push**, sem tag.

| Commit | Conteúdo |
|---|---|
| `1073743` | entrega original dos seis verificadores — **reprovada na auditoria** |
| `aec88a8` | [H4] allowlist do auditor libera a prova central e os smoke tests |
| `22bc144` | [B1] `objective_ids` por negação padrão; probe replantado; hook corrigido |
| `3a8477d` | [H2] `expect_fail` exige `rc == 1` e citação do arquivo plantado |
| `35f2eb8` | [M1] CI executa o harness negativo |
| `817e434` | `log_audit.py` persiste veredito e relatório da auditoria |
| `8e5dedb` | [H1] `check_contract_literals` cobre TypeScript |
| `9f786ec` | [H3] `check_synthetic_data` verifica identificador (CPF) |
| `132ff75` | registro da reprovação na primeira auditoria |
| `c8c2be3` | regressão do `817e434`: hook gravava subagente qualquer como auditoria |
| `76e04c9` | [M3] isenção de caminho ancorada, nos dois verificadores |
| `8b129d2` | [M2] probe para o ramo de divergência do `codegen --check` |
| `6ed9993` | [L3] docstring de `_common.py` alinhada ao contrato do H2 |

`finalize_phase0.sh` **não** foi executado.

---

## 6. Pendências

### P1 — `phase0_negative_tests.py` deixa diretórios vazios no Windows (não corrigido de propósito)

**Sintoma.** Após executar o harness, `range-core/`, `domains/` e `scenarios/` às vezes permanecem vazios na árvore.

**Causa.** O helper `temporary_file` remove os diretórios que criou com `rmdir` dentro de `try/except OSError: pass`. No Windows, o `rmdir` de um diretório recém-esvaziado falha de forma intermitente — handle transitório sobre o arquivo apagado — e o `except` engole o erro em silêncio.

**Reprodução.** Observado 1 vez em cerca de 8 execuções. Com o `rmdir` instrumentado, nunca reproduziu: a instrumentação adiciona latência suficiente para o handle ser liberado. É corrida, não defeito lógico.

**Impacto.** Cosmético. Diretório vazio não é rastreado pelo Git, então `git status` permanece limpo, e os seis verificadores continuam saindo `0` com esses diretórios presentes e vazios — verificado explicitamente.

**Por que não foi corrigido.** `scripts/phase0_negative_tests.py` é o harness que **testa** os verificadores desta fase. O implementador dos verificadores não altera o teste que os julga. Uma correção feita por quem está sendo avaliado é indistinguível, para um auditor, de um enfraquecimento do teste — e é exatamente a classe de mudança que a Fase 0 existe para impedir.

**Encaminhamento.** Correção pertence a um PR próprio, de escopo `scripts/`, sem alteração em `tools/` no mesmo commit. A correção provável é reintentar o `rmdir` ou registrar a falha em vez de silenciá-la.

### P2 — `codegen.py` sem modo de escrita

`--check` é o único modo implementado. Invocar sem a flag sai `rc=2` com mensagem apontando a Fase 1.

**Justificativa.** `PHASE_0_CHECKLIST.md` §Interfaces obrigatórias autoriza explicitamente: "a geração efetiva poderá usar outro modo/flag em fase posterior". Nenhum probe do harness exercita escrita, e código não exercitado dentro do próprio mecanismo de verificação é precisamente o que a Fase 0 existe para não deixar passar.

**Encaminhamento.** Fase 1, junto com os contratos que a geração consome.

### P3 — Cobertura de TypeScript em `check_core_boundary.py` não é exercitada

A stdlib não traz analisador de TypeScript. A cobertura de `.ts`/`.tsx`/`.js` usa extração de declaração de import, não AST, e é deliberadamente conservadora.

**Justificativa.** `01_ARCHITECTURE.md` §2 prevê front-end sob `range-core/web/`, e `.claude/hooks/check_architecture.py` já cobre import relativo em TS. Omitir a verificação deixaria o buraco aberto; incluí-la sem probe deixa código não exercitado. Optei por incluir com a limitação declarada no docstring do próprio arquivo.

**Escopo reduzido pelo H1.** A correção do H1 (`8e5dedb`) adicionou probe TypeScript, mas para `check_contract_literals.py` — literal de flag em `.tsx`. A cobertura TS de **`check_core_boundary.py`**, que é import de `domains/` a partir de `range-core/web/`, continua sem probe. São mecanismos distintos: um é varredura léxica de literais de string, o outro é extração de declaração de import.

**Encaminhamento.** Quando a Fase 4 criar `range-core/web/`, o harness precisa de probe de import TypeScript. Até lá esta cobertura específica é não verificada.

### P4 — Formatos sem gramática declarada ficam fora de `check_synthetic_data.py`

Cobertos: `.json`, `.jsonl`, `.yaml`, `.yml`, `.csv`. Descobertos: `.log`, `.eml`, `.txt`, CEF.

**Justificativa.** A verificação é estrutural: o arquivo é analisado e os **valores** são percorridos, sem varredura textual do bruto. Formato sem gramática declarada não permite isso, e cair para varredura textual reintroduziria exatamente o grep que a spec recusa.

**Impacto.** `08_EVIDENCE_SIMULATOR.md` prevê evidência em formatos livres. Enquanto não houver verificação correspondente, `05_SECURITY_REQUIREMENTS.md` §3 depende de revisão humana nesses arquivos.

**Encaminhamento.** Fase 9. A verificação precisa ser desenhada **junto** com o formato de evidência, não depois.

### P5 — Registro de progresso da Fase 0 — resolvido

Este documento. Registrado aqui porque a ausência foi levantada como pendência antes de ser resolvida, e o histórico da fase deve mostrar isso em vez de apenas o estado final.

---

As quatro pendências seguintes vêm da primeira auditoria de checkpoint (§0). O texto é o do finding, **integral**, não resumo: pendência resumida perde a evidência e deixa de ser rastreável até a correção.

### P6 — [M2] O probe do codegen exercita apenas a ausência de artefato, nunca a divergência

```text
[M2] O probe do codegen exercita apenas a ausência de artefato, nunca a divergência
  Arquivo: scripts/phase0_negative_tests.py:87-89; tools/codegen.py:60,189-198
  Requisito violado: 06_ACCEPTANCE_TESTS.md T2 ("Constantes Python e TypeScript
  DESSINCRONIZADAS → --check sai com código ≠ 0")
  Evidência: o probe planta domains/_phase0_codegen_probe/flags.yaml sem
  generated/, acionando só RULE_MISSING (linha 176-183). O ramo RULE_DIVERGENT
  (linha 189-198) — que é o que de fato detecta constante fora de sincronia com
  o contrato — não é exercitado por nenhum probe. Nenhum probe planta um
  artefato .py/.ts com conteúdo divergente.
```

**Status: FECHADA em `8b129d2`**, na segunda auditoria. O probe planta `flags.yaml` **e** os dois artefatos gerados, ambos divergentes: com `.py` e `.ts` presentes, o ramo de ausência não pode disparar, então a detecção só pode vir da comparação de conteúdo. Verificado que a saída cita "divergente" e não "ausente".

### P7 — [M3] Isenções de caminho casam qualquer segmento, em qualquer profundidade

```text
[M3] Isenções de caminho casam qualquer segmento, em qualquer profundidade
  Arquivo: tools/check_event_envelope.py:41,53; tools/check_contract_literals.py:48,58-62
  Requisito violado: 01_ARCHITECTURE.md §2 ("Invariante com exceção é invariante
  morto", ecoado em tools/codegen.py:27-29)
  Evidência: _is_emission_path() retorna False se QUALQUER parte do caminho
  estiver em {"objectives","aar","metrics","calibration"}; logo
  domains/academus/api/metrics/emit.py — caminho de emissão de adapter — fica
  isento. Do mesmo modo, _is_authorized() isenta qualquer arquivo com um segmento
  contracts ou generated, então domains/academus/api/contracts/handler.py pode
  conter literal de flag sem violação.
```

**Status: FECHADA em `76e04c9`**, na segunda auditoria. Projeção passou a ser reconhecida por prefixo ancorado na raiz (`range-core/objectives|aar|metrics|calibration`), e autorização de literal por `contracts/...` ou `domains/<adapter>/generated/...`. Dois probes novos provam a correção; verificado também que as camadas de projeção legítimas do core seguem isentas e os artefatos gerados seguem autorizados.

O encaminhamento antecipado neste registro — ancorar em prefixo — foi o adotado.

### P8 — [L1] O separador de segmentos do hook do auditor quebra comandos de leitura legítimos

```text
[L1] O separador de segmentos do hook do auditor quebra comandos de leitura legítimos
  Arquivo: user-scope/hooks/readonly_bash.py:54
  Requisito violado: PHASE_0_CHECKLIST.md §DoD item 4 ("libera testes/verificadores
  de leitura")
  Evidência: re.split(r"\|\||&&|;|\|", cmd) não tem consciência de aspas.
  Observado: git ls-files | grep -E "^(range-core|domains|contracts|scenarios)/"
  foi bloqueado com "Segmento: domains", porque o | DENTRO DA REGEX ENTRE ASPAS
  foi tratado como pipe de shell.
```

**Status.** Aberta por instrução. Falha para o lado seguro — bloqueia o legítimo, não libera o proibido — mas degrada a capacidade do auditor exatamente como o H4 fazia, e H4 foi tratado como HIGH por esse motivo. Por causa desta pendência, o item 4 da DoD (§5) permanece **parcial** mesmo após a correção do H4.

**Reconfirmada na quarta auditoria** — ver §6 P23.

### P9 — [L2] `check_security_constraints.py` não varre os próprios hooks nem o workflow

```text
[L2] check_security_constraints.py não varre os próprios hooks nem o workflow
  Arquivo: tools/check_security_constraints.py:36
  Requisito violado: 05_SECURITY_REQUIREMENTS.md §1
  Evidência: SCANNED_DIRS = ("range-core", "domains", "tools", "scripts").
  .claude/hooks/*.py — que executa subprocess.run (check_architecture.py:98) e
  roda em toda chamada de Edit/Write — não é verificado por nenhum dos seis.
```

**Status.** Aberta, **reconfirmada na segunda auditoria**. O código de governança é o menos vigiado do repositório, e é o que roda com mais frequência. Ao incluir `.claude/hooks/` no escopo será preciso decidir o que fazer com o `subprocess.run` legítimo de `check_architecture.py` e do `log_audit.py` — nenhum usa shell, então a regra atual não os acusaria, mas isso precisa ser verificado e não presumido.

A regressão O4 (§7) reforça o argumento: o defeito nasceu em `.claude/hooks/log_audit.py`, e nenhum dos seis verificadores olhava para lá.

**Reconfirmada e ampliada na quarta auditoria** para `user-scope/hooks/` — ver §6 P24.

### P10 — [L3] Docstring de `_common.py` contradizia o contrato do H2 — resolvida

```text
[L3] a docstring de tools/_common.py:18-19 ainda diz "qualquer valor diferente
  de zero conta como deteccao", contradizendo o contrato que o H2 estabeleceu
  (rc == 1 exatamente). Documentação interna que instrui precisamente o erro
  corrigido.
```

**Status: FECHADA em `6ed9993`, com ressalva.** Registrada mesmo resolvida porque nomeia uma categoria de defeito que vai reaparecer: correção de código que deixa para trás a documentação que a contradiz. O texto antigo sobreviveria à correção e orientaria a próxima pessoa a desfazê-la.

**Ressalva, após o L1 da terceira auditoria.** O status dizia *"verificado que nenhum outro ponto do repositório repete a instrução"*. A verificação feita cobriu apenas a instrução de **código de saída** (`grep` por "diferente de zero"), não a categoria inteira. A terceira auditoria encontrou outro caso da mesma categoria — `tools/README.md` e `README_FIRST.md` ainda instruindo que os seis verificadores não existem — registrado em §6 P15. A afirmação larga foi substituída por esta, que diz o que de fato foi medido.
### P11 — [M1, segunda auditoria] O registro afirmava capacidade que o próprio HEAD desabilitou

```text
M1 (segunda auditoria): o registro de progresso afirma capacidade que o próprio
HEAD desabilitou. O §7 O4 do fase_0.md diz que o relatório vai para
docs/progress/audit_<timestamp>.md e o veredito para o audit_log.jsonl. Mas o
c8c2be3 passou a exigir agent_type == "checkpoint-auditor", e o agent_type chega
vazio — o próprio O5 registra isso. Consequência: o mecanismo de rastreabilidade
está inerte e o registro afirma o contrário. Nem esta auditoria nem a anterior
foram persistidas por ele.
```

**Status.** Aberta. O texto do §7 O4 foi corrigido para descrever o estado real e medido; **o mecanismo continua inerte**. As duas coisas são separadas de propósito: o finding era sobre o registro mentir, e essa parte está resolvida. Fazer a captura funcionar é trabalho que ninguém pediu ainda e que não deve ser inventado dentro de uma correção de texto.

**Por que não basta remover a exigência de `agent_type`.** Ela foi introduzida em `c8c2be3` justamente porque, sem ela, o hook gravava a mensagem final de qualquer subagente como auditoria, com veredito fabricado. Afrouxar volta a fabricar. O problema real é anterior: o launcher invoca o auditor como agente **de topo** (`claude --agent`), não como subagente, então `SubagentStop` provavelmente nunca dispara para ele — o hook está no evento errado.

**Encaminhamento provável.** Capturar no `launcher`, que é quem sabe que está executando uma auditoria e já grava `phase`, `head_sha` e `launcher_exit`, em vez de depender de um hook que precisa adivinhar quem chamou. Isso implica também decidir o destino de `docs/progress/audit_log.jsonl`, hoje em `.gitignore:26` — um registro de auditoria que não entra no repositório não é registro. Enquanto isso não existir, o veredito precisa ser colado manualmente, como foi nas três primeiras rodadas.

---

As seis pendências seguintes vêm da **terceira auditoria**. IDs novos, para não colidir com P1–P11; a coluna de origem em §0 dá a correspondência com os IDs daquela rodada.

### P12 — [M1, terceira auditoria] `spec_freeze` define "código" como apenas três diretórios

```text
[M1] O job spec_freeze define "código" como apenas range-core/ domains/ contracts/; tools/, scripts/, .claude/ e .github/ ficam fora
Arquivo: .github/workflows/invariants.yml:60
Requisito violado: CLAUDE.md §A especificação é imutável ("Alterar spec e código
no mesmo PR é proibido"); WORKFLOW.md:25 ("PR próprio com título spec-change:,
sem código junto")
Evidência: CODE=$(git diff --name-only "$BASE_SHA" HEAD -- range-core/ domains/
contracts/ | wc -l). Um PR que altere docs/spec/00_MASTER_SPEC.md e
tools/check_core_boundary.py produz CODE=0 e passa no gate. Nem CLAUDE.md nem
WORKFLOW.md restringem "código" a três diretórios; tools/ é justamente onde vivem
os verificadores que a spec normatiza (01_ARCHITECTURE.md §2). Está parcialmente
reconhecido em fase_0.md:404 (O4→O2), classificado ali como "formalmente
conforme" — leitura que a auditoria não sustenta: o texto normativo diz "código",
não "range-core, domains e contracts".
```

**Status: FECHADA em `012ce3a`.** Corrigida **antes** dos itens 10 e 11 da DoD, de propósito: são eles que demonstram o `spec_freeze`, e a tag `spec-v1.0` congela a especificação confiando nesse gate. Demonstrar um gate estreito não é demonstrar o gate que a spec descreve.

O critério adotado é **ser mecanismo que aplica a spec**, não "tudo que não é `docs/spec/`". A formulação original dizia "ser executável", o que nunca foi literalmente verdade — o conjunto sempre incluiu markdown de governança de agente, que não executa nada e define comportamento.

| Entra no conjunto `CODE` | Por quê | Quando entrou |
|---|---|---|
| `range-core/`, `domains/`, `contracts/` | conjunto original | — |
| `tools/` | os verificadores que a spec normatiza (`01_ARCHITECTURE.md` §2) | `012ce3a` |
| `scripts/` | harness negativo e launcher de auditoria | `012ce3a` |
| `.claude/` | hooks e definições de agente de projeto | `012ce3a` |
| `.github/` | CI | `012ce3a` |
| `bootstrap.sh`, `finalize_phase0.sh` | executáveis de raiz, via `:(glob)*.sh` | `012ce3a` |
| `user-scope/` | fonte versionada do auditor e do seu hook | `ee7731d` (§6 P18) |
| `CLAUDE.md` | instrução permanente: autoridade, invariantes, restrições inegociáveis | `32bdc05` (§6 P26) |

`docs/process/`, `README_FIRST.md` e `CHANGELOG_V3.md` **não** entram: são documentação descritiva, e o próprio PR de `spec-change` costuma precisar tocá-los. Verificado que nenhum caminho sob `docs/` casa com o conjunto `CODE`.

**Consequência aceita da entrada do `CLAUDE.md`.** Ele espelha partes da spec — cita `docs/spec/` sete vezes e repete os invariantes arquiteturais e as quatro camadas de verdade. Uma mudança normativa passa a exigir **dois PRs**: o `spec-change:` e o que atualiza o `CLAUDE.md`, com o segundo temporariamente defasado em relação ao primeiro. É o mesmo custo já aceito para `tools/`, pelo mesmo motivo: separar a mudança da regra da mudança do mecanismo que a aplica.

Esta última entrada corrige o **M1 da quinta auditoria** — ver §6 P26.

O `:(glob)` é necessário: sem o magic glob, `*.sh` casaria em qualquer profundidade, e não apenas na raiz.

**Observação retroativa — o commit inicial desta fase passaria a ser reprovado.** `1073743` tocou `docs/spec/` (11 arquivos) e, simultaneamente, `tools/` (8), `scripts/` (2), `.claude/` (7), `.github/` (1) e dois `.sh` de raiz — `CODE=20`. Sob a regra nova, um PR com esse conteúdo é reprovado.

Isso **não é problema**, e fica registrado porque confunde quem ler o histórico depois: `spec_freeze` roda apenas em `pull_request`, e a Fase 0 nasce direto em `main`, por desenho. O commit inicial nunca passou por PR e nunca passará. A regra vale da tag `spec-v1.0` em diante, quando toda mudança já entra por PR — que é exatamente o regime que ela existe para proteger.

### P13 — [M2, terceira auditoria] Deny de secrets cobre `Read` e `Edit`, mas não `Write`

```text
[M2] O deny de secrets cobre Read e Edit, mas não Write
Arquivo: .claude/settings.json:6-13
Requisito violado: PHASE_0_CHECKLIST.md §DoD item 7 (".env/secrets estão negados
em .claude/settings.json"); CLAUDE.md §Secrets ("Nunca leia, edite ou versione
.env … secrets/")
Evidência: a lista deny contém exatamente Read(.env), Edit(.env), Read(.env.*),
Edit(.env.*), Read(secrets/**), Edit(secrets/**). Não há nenhuma entrada
Write(...). Que Edit e Write são ferramentas distintas nesta configuração está
estabelecido no próprio arquivo: settings.json:18 usa "matcher": "Edit|Write". O
CHANGELOG_V3.md:19-20 documenta a correção H2 apenas sobre ancoragem de caminho,
sem tocar na cobertura de ferramenta. A leitura de .env — o risco principal —
está negada; a criação/sobrescrita não.
```

**Status.** Aberta. Rebaixa o item 7 da DoD (§5) de ✅ para ⚠️ parcial: o item pede secrets negados, e a negação é parcial por ferramenta.

**Reconfirmada na quarta auditoria** — ver §6 P19.

### P14 — [M3, terceira auditoria] `check_event_envelope.py` só varre `.py`, sem declarar a limitação

```text
[M3] check_event_envelope.py só varre .py; a camada web de core e adapter fica fora do invariante 4, sem declaração da limitação
Arquivo: tools/check_event_envelope.py:43 (PYTHON_SUFFIXES = (".py",)) e :92
Requisito violado: 06_ACCEPTANCE_TESTS.md T1 ("Nenhum evento emitido pelo core ou
pelo adapter carrega objective_ids. Verificado por tools/check_event_envelope.py");
01_ARCHITECTURE.md §2 (range-core/web/gm-console|participant-view|wallboard-shell
e domains/<adapter>/web/)
Evidência: o verificador irmão do mesmo commit varre TS explicitamente
(check_contract_literals.py:160, usando WEB_SUFFIXES de _common.py:119), e o
check_core_boundary.py:191 também. Só check_event_envelope.py não varre — e seu
docstring (linhas 1-19) não menciona a limitação, ao contrário de
check_core_boundary.py:10-13, cuja limitação de TS está declarada e registrada
como pendência P3 (fase_0.md:275-283). O hook rápido
.claude/hooks/check_architecture.py:133 cobre .ts/.tsx para objective_ids; o gate
real do CI, não. Lacuna silenciosa é exatamente o que o B1 da primeira auditoria
condenou.
```

**Status.** Aberta. O achado é duplo — falta a cobertura **e** falta a declaração. A segunda metade é a mais grave, porque é o padrão que o B1 condenou: dos três verificadores que poderiam varrer TS, dois varrem e um não, sem que nada no arquivo diga isso.

**Reconfirmada na quarta auditoria** — ver §6 P20.

### P15 — [L1, terceira auditoria] `tools/README.md` e `README_FIRST.md` contradizem o estado real

```text
[L1] tools/README.md e README_FIRST.md ainda instruem que os seis verificadores não existem
Arquivo: tools/README.md:3 ("Este diretório é deliberadamente entregue sem os seis
verificadores finais. A primeira tarefa real do Claude Code é implementar…");
README_FIRST.md:10 ("Entregue a Fase 0: implementar os seis verificadores em tools/")
Requisito violado: mesma categoria nomeada por L3/P10 em fase_0.md:368-377
("correção de código que deixa para trás a documentação que a contradiz"), cujo
status diz "Verificado que nenhum outro ponto do repositório repete a instrução"
Evidência: os seis existem, rodam e saem 0 (medido). fase_0.md:98 inclusive
descreve tools/README.md como "inventário da fase". O texto em disco é do bundle
pré-implementação. A afirmação de fechamento do P10 é, portanto, imprecisa: outro
ponto do repositório contradiz o estado real.
```

**Status.** Aberta. A ressalva ao P10 já foi aplicada (§6 P10). Os dois arquivos continuam com o texto pré-implementação.

**Reconfirmada na quarta auditoria** — ver §6 P21.

### P16 — [L2, terceira auditoria] Hook do auditor bloqueia mais leitura legítima que o descrito em P8

```text
[L2] O hook do auditor bloqueia comandos de leitura legítimos além do caso descrito em P8
Arquivo: user-scope/hooks/readonly_bash.py:41 e :44
Requisito violado: PHASE_0_CHECKLIST.md §DoD item 4 ("libera testes/verificadores
de leitura")
Evidência: observado nesta sessão, dois modos novos, distintos do caso de aspas
registrado em P8 (fase_0.md:338-351):
(a) git merge-base HEAD main foi bloqueado como "git que altera estado" —
\bgit\s+(…|merge|…)\b casa dentro de merge-base porque - é fronteira de palavra;
(b) git rev-parse HEAD main 2>&1 foi bloqueado como "redirecionamento de saída
para arquivo" — >\s*\S casa >&1.
Também git for-each-ref e sort caem fora da allowlist. Falha para o lado seguro,
mas degrada a capacidade do auditor — o mesmo argumento que fez o H4 ser HIGH. P8
descreve só o caso do | entre aspas.
```

**Status.** Aberta, e **agrupa-se ao P8**: são a mesma família de defeito — casamento textual sem consciência de sintaxe de shell. P8 descreve o `|` entre aspas; P16 acrescenta `merge-base` casando como `merge`, `2>&1` casando como redirecionamento, e `for-each-ref`/`sort` fora da allowlist. Juntos são a razão de o item 4 da DoD (§5) seguir parcial.

**Reconfirmada na quarta auditoria, com modo novo** (`->` entre aspas) — ver §6 P23.

### P17 — [L3, terceira auditoria] `.env.example` não existe, mas dois documentos o tratam como presente

```text
[L3] .env.example não existe, embora dois documentos o tratem como presente
Arquivo: ausente da árvore (git ls-files não o lista); docs/process/WORKFLOW.md:108
(".env.example continua disponível e deve conter apenas placeholders")
Requisito violado: 05_SECURITY_REQUIREMENTS.md §6 (".env.example versionado; .env
no .gitignore")
Evidência: .gitignore:2-5 cobre .env e variantes; o .env.example correspondente
não está versionado. A Fase 0 não tem aplicação e RANDOM_SEED é DoD da Fase 1, o
que torna a lacuna defensável no tempo — mas o texto do WORKFLOW.md afirma
disponibilidade que não existe.
```

**Status.** Aberta. A própria auditoria reconhece a lacuna como defensável no tempo — a Fase 0 não tem aplicação e `RANDOM_SEED` é DoD da Fase 1. O defeito imediato é o texto do `WORKFLOW.md` afirmar disponibilidade inexistente, terceira ocorrência da categoria do P10/P15 nesta rodada.

---

As oito pendências seguintes vêm da **quarta auditoria**. IDs a partir de P18, sem colisão com P1–P17. Cinco delas reconfirmam pendências anteriores: o texto novo fica aqui, e a pendência original recebe ponteiro.

### P18 — [M1, quarta auditoria] Conjunto `CODE` do `spec_freeze` omite `user-scope/`

```text
[M1] O conjunto CODE do spec_freeze omite user-scope/ — correção do P12 incompleta
Arquivo: .github/workflows/invariants.yml:76-78
Requisito violado: CLAUDE.md §A especificação é imutável durante a implementação
("Alterar spec e código no mesmo PR é proibido"); docs/process/WORKFLOW.md:25
Evidência: medido. git ls-files -- range-core/ domains/ contracts/ tools/ scripts/
.claude/ .github/ ':(glob)*.sh' retorna 20 arquivos e não inclui
user-scope/agents/checkpoint-auditor.md nem user-scope/hooks/readonly_bash.py, que
são tracked (git ls-files -- user-scope/ lista os dois). Um PR que altere
docs/spec/00_MASTER_SPEC.md e user-scope/hooks/readonly_bash.py produz CODE=0 e
passa no gate.
Por que é MEDIUM: bootstrap.sh:40-41 copia esses dois arquivos para ~/.claude/;
eles são a fonte canônica do auditor e do seu hook. É exatamente o critério "ser
executável / mecanismo que aplica a própria spec" que o P12 usou para incluir
.claude/ e .github/. O argumento de integridade do WORKFLOW.md §"Por que o auditor
não mora no repositório" protege a cópia instalada, não a fonte versionada — que
continua enfraquecível no mesmo PR que altera a spec. Mesma categoria do M1 da
terceira auditoria, classificado MEDIUM.
```

**Correção incompleta minha**, não defeito herdado: o P12 foi fechado por mim uma rodada antes, com o critério então formulado como "ser executável", e `user-scope/` satisfaz esse critério tanto quanto `.claude/`. (A formulação foi depois refinada para "ser mecanismo que aplica a spec" — ver a tabela em §6 P12 —, o que só reforça a inclusão.)

**Status: FECHADA em `ee7731d`.** `user-scope/` entrou no conjunto `CODE`. Corrigida antes dos itens 10 e 11 pelo mesmo argumento que levou o P12 a ser corrigido antes: são eles que demonstram o `spec_freeze`, e a tag `spec-v1.0` congela a especificação confiando nesse gate.

Medido: o conjunto `CODE` passa de **20 para 22** arquivos — `user-scope/agents/checkpoint-auditor.md` e `user-scope/hooks/readonly_bash.py`. Verificado que `docs/spec/` e `docs/process/` seguem fora, e que o cenário do finding, spec + `user-scope/hooks/` no mesmo PR, passa a disparar a regra de spec+código.

**O que a omissão revelava.** O argumento de integridade de `docs/process/WORKFLOW.md` §"Por que o auditor não mora no repositório" protege a **cópia instalada** em `~/.claude/`, fora do alcance do commit sob revisão. Ele não diz nada sobre a fonte versionada — que continua no repositório, e continuava fora do gate. O mesmo PR que alterava a spec podia enfraquecer o auditor que deveria auditá-la.

### P19 — [M3, quarta auditoria] Deny de secrets ainda não cobre `Write` — reconfirma P13

```text
[M3] Deny de secrets ainda não cobre Write — pendência P13, reconfirmada
Arquivo: .claude/settings.json:6-13
Requisito violado: PHASE_0_CHECKLIST.md §DoD item 7; CLAUDE.md §Secrets
Evidência: a lista deny contém exatamente Read(.env), Edit(.env), Read(.env.*),
Edit(.env.*), Read(secrets/**), Edit(secrets/**). Nenhuma entrada Write(...). Que
Edit e Write são ferramentas distintas nesta configuração está no próprio arquivo:
settings.json:18 usa "matcher": "Edit|Write".
```

**Status.** Aberta. Mesmo defeito de **P13**; segunda auditoria consecutiva a levantá-lo. Mantém o item 7 da DoD (§5) em parcial.

### P20 — [M4, quarta auditoria] `check_event_envelope.py` só varre `.py` — reconfirma P14

```text
[M4] check_event_envelope.py só varre .py, e a limitação continua não declarada no arquivo — pendência P14, reconfirmada
Arquivo: tools/check_event_envelope.py:43 (PYTHON_SUFFIXES = (".py",)) e :92
Requisito violado: 06_ACCEPTANCE_TESTS.md T1; 01_ARCHITECTURE.md §2
Evidência: os dois verificadores irmãos varrem TS — check_contract_literals.py:160
usa WEB_SUFFIXES, e check_core_boundary.py declara sua limitação de TS no docstring
(linhas 10-13). O docstring de check_event_envelope.py (linhas 1-19) não menciona a
restrição a .py. A lacuna está registrada em fase_0.md P14, mas continua invisível
para quem lê apenas o verificador.
```

**Status.** Aberta. Mesmo defeito de **P14**. A auditoria reforça o ponto que o P14 já fazia: registrar a lacuna no `fase_0.md` não a torna visível para quem abre o verificador — a declaração precisa estar no arquivo.

### P21 — [L1, quarta auditoria] `tools/README.md` e `README_FIRST.md` desatualizados — reconfirma P15

```text
[L1] tools/README.md e README_FIRST.md ainda instruem que os seis verificadores não existem — pendência P15, reconfirmada
Arquivo: tools/README.md:3; README_FIRST.md:10
Requisito violado: categoria nomeada por L3/P10 em fase_0.md
Evidência: os seis existem e saem 0 (medido nesta sessão). tools/README.md:1 ainda
se intitula "verificadores a implementar".
```

**Status.** Aberta. Mesmo defeito de **P15**.

### P22 — [L2, quarta auditoria] `README_FIRST.md` e `PHASE_0_CHECKLIST.md` descrevem o `finalize` anterior ao H2

```text
[L2] NOVO — README_FIRST.md:12 e PHASE_0_CHECKLIST.md:104 descrevem um finalize_phase0.sh que a correção do H2 eliminou
Arquivo: README_FIRST.md:12; docs/process/PHASE_0_CHECKLIST.md:104
Requisito violado: mesma categoria de P10/P15 (documentação que sobrevive à
correção e a contradiz)
Evidência: README_FIRST.md:12 diz que finalize_phase0.sh "é o único script que
commita, publica, espera o CI, aplica branch protection e — por último — cria
spec-v1.0", e PHASE_0_CHECKLIST.md:104 diz "Use bash finalize_phase0.sh para
executar essa ordem". Após 6567b2b, a primeira invocação para antes da tag
(finalize_phase0.sh:178-233) e a tag só sai com --dod-10-11-verificados. Nenhum dos
dois textos menciona a segunda invocação. É instância nova da categoria, criada
pelo próprio delta que esta auditoria foi chamada a examinar.
```

**Status.** Aberta. **Criada pela minha correção do H2** em `6567b2b`. Mudei o fluxo do script, atualizei o `fase_0.md` e não toquei nos dois textos que descrevem o script para o operador — que são justamente os que ele lê primeiro.

Quarta ocorrência da categoria nesta fase, depois de P10, P15 e P17. As três anteriores eram herdadas do bundle inicial; esta eu produzi, com a categoria já nomeada e registrada duas vezes. Isso a torna a mais informativa das oito.

### P23 — [L3, quarta auditoria] Hook do auditor segue bloqueando leitura legítima — reconfirma P8 e P16

```text
[L3] O hook do auditor continua bloqueando leitura legítima — pendências P8/P16, reconfirmadas por reprodução direta
Arquivo: user-scope/hooks/readonly_bash.py:41,44,54
Requisito violado: PHASE_0_CHECKLIST.md §DoD item 4 ("libera testes/verificadores de
leitura")
Evidência: quatro bloqueios observados nesta sessão, todos de comandos de leitura:
(a) git ... 2>/dev/null → "redirecionamento de saida para arquivo";
(b) printf "%s -> " → o -> dentro de string entre aspas casou como redirecionamento;
(c) for t in ...; do e python --version → fora da allowlist;
(d) grep -E '^(range-core|domains|...)' → o | dentro da regex entre aspas foi tratado
como pipe, bloqueado com "Segmento: domains".
O caso (b) é modo novo, não descrito em P8 nem em P16. Falha para o lado seguro, mas
obrigou a reescrever comandos de auditoria — a mesma degradação de capacidade que fez
o H4 ser HIGH.
```

**Status.** Aberta. Terceira rodada consecutiva a levantar a mesma família — **P8**, **P16** e agora esta. O caso (b) é modo novo: `->` dentro de string casando como redirecionamento.

Os três juntos deixam claro que o defeito não é uma lista de casos, e sim a abordagem: `readonly_bash.py` faz casamento textual sem consciência de sintaxe de shell. Corrigir caso a caso vai continuar produzindo achados; o encaminhamento provável é tokenizar o comando antes de decidir.

### P24 — [L4, quarta auditoria] `check_security_constraints.py` não varre os hooks — reconfirma e amplia P9

```text
[L4] check_security_constraints.py não varre .claude/hooks/ nem user-scope/hooks/ — pendência P9, reconfirmada e ampliada
Arquivo: tools/check_security_constraints.py:36 (SCANNED_DIRS = ("range-core",
"domains", "tools", "scripts"))
Requisito violado: 05_SECURITY_REQUIREMENTS.md §1
Evidência: .claude/hooks/log_audit.py:47 e check_architecture.py executam
subprocess.run, e user-scope/hooks/readonly_bash.py roda em toda chamada de Bash do
auditor. Nenhum dos seis verificadores olha para esses caminhos. P9 cita só
.claude/hooks/; user-scope/hooks/ é ampliação.
```

**Status.** Aberta. Amplia **P9** para `user-scope/hooks/`.

Conversava diretamente com o P18: `user-scope/` estava fora do conjunto `CODE` do `spec_freeze` **e** fora do escopo do verificador de segurança — o diretório menos vigiado do repositório, contendo o hook que restringe o auditor. Com o P18 fechado em `ee7731d`, resta a segunda metade: `user-scope/hooks/` e `.claude/hooks/` seguem fora de `SCANNED_DIRS`.

### P25 — [L5, quarta auditoria] Actions do CI presas a tag major mutável

```text
[L5] Actions do CI presas a tag major mutável
Arquivo: .github/workflows/invariants.yml:12,13,50,93,94
Requisito violado: 00_MASTER_SPEC.md §8 ("Todas as versões pinadas");
06_ACCEPTANCE_TESTS.md T15 ("Nenhuma dependência não pinada")
Evidência: actions/checkout@v4 e actions/setup-python@v5 são tags móveis, não SHAs.
python-version: "3.12" está corretamente pinado.
```

**Status.** Aberta, **deliberadamente adiada para a Fase 1**. Mexer no `invariants.yml` na véspera de executar os PRs descartáveis que testam esse mesmo workflow adiciona risco sem necessidade: se algo quebrar, quebra exatamente na demonstração dos itens 10 e 11. A decisão de adiar é do operador e está registrada aqui para não parecer esquecimento.

---

### P26 — [M1, quinta auditoria] `CLAUDE.md` fora do conjunto `CODE` do `spec_freeze`

Houve uma **quinta auditoria**. Dela chegou até este registro exatamente um achado, o M1: `CLAUDE.md` deveria entrar no conjunto `CODE` do `spec_freeze`. O texto verbatim do finding **não foi transmitido**, e o veredito e os demais achados da rodada também não — o que fica declarado aqui em vez de suposto, e é consequência direta de **P11**, que mantém a captura de relatório inerte.

**Status: FECHADA em `32bdc05`.**

`CLAUDE.md` é a instrução permanente carregada em toda sessão: define autoridade normativa, os quatro invariantes arquiteturais e as restrições inegociáveis. Alterar a especificação e, no mesmo PR, o documento que diz como obedecê-la é exatamente o acoplamento que a regra existe para impedir.

**O que o achado expôs, além do próprio caminho.** Ao justificar a inclusão, ficou claro que o critério do conjunto `CODE` estava mal formulado. O comentário do workflow dizia "ser executável", e isso nunca foi literalmente verdade: desde `012ce3a` o conjunto já continha `.claude/agents/scenario-designer.md`, `.claude/agents/spec-guardian.md` e `user-scope/agents/checkpoint-auditor.md` — três markdowns que não executam nada e definem comportamento. O critério real sempre foi **ser mecanismo que aplica a spec**, e a formulação foi corrigida no workflow e na tabela do §6 P12.

**Erro de classificação, corrigido.** Este achado foi registrado inicialmente como decisão do operador, porque chegou sem identificação de rodada e o M1 conhecido até então era o da quarta auditoria, sobre `user-scope/`. É a terceira vez nesta fase que IDs se confundem entre rodadas — as duas anteriores estão em §0 —, e todas as três têm a mesma raiz: **P11**. Enquanto o relatório da auditoria não for persistido, cada rodada chega por transcrição manual, sem rodada nem veredito anexados.

---

## 7. Observações levantadas durante a fase

Nenhuma delas bloqueia a Fase 0. Ficam registradas porque foram descobertas aqui e se perderiam de outro modo.

**O1 — `check_architecture.py` falha aberto com stdin malformado.** `main()` encerra com `except Exception: return 0` quando o JSON de entrada não parseia, ou seja, libera a operação. Em contraste, `check_spec_edit` falha **fechado** quando a consulta ao git falha: sem branch, bloqueia. O Claude Code sempre envia JSON bem-formado, então não há exploração prática pelo modelo — é assimetria de projeto defensivo, não buraco ativo. Descoberto porque um teste manual com `echo` colapsou `\\` em `\` e produziu JSON inválido.

**O2 — o commit inicial mistura `docs/spec/` e `tools/`.** As edições de propagação em `docs/spec/` e os seis verificadores entraram no mesmo commit inicial. Isso **não** aciona o job `spec_freeze`: ele roda apenas em `pull_request`, e o conjunto que ele considera "código" é `range-core/`, `domains/` e `contracts/` — `tools/` não está nele.

**Correção após o M1 da terceira auditoria.** Uma versão anterior deste parágrafo classificava a situação como "formalmente conforme". Essa leitura não se sustenta: `CLAUDE.md` §A especificação é imutável e `docs/process/WORKFLOW.md:25` dizem **código**, sem restringir a três diretórios — e `tools/` é justamente onde vivem os verificadores que a spec normatiza. Era uma lacuna do `spec_freeze`, não conformidade formal.

**Estado atual.** A lacuna foi fechada em `012ce3a` (§6 P12): o conjunto `CODE` passou a incluir `tools/`, `scripts/`, `.claude/`, `.github/` e os `.sh` de raiz. Sob a regra corrigida, o commit inicial **seria reprovado** — o que não é problema, porque ele nasceu em `main` sem PR, e `spec_freeze` só roda em `pull_request`. Ver a observação retroativa em P12.

**O3 — o regime de `spec-change` ainda não estava em vigor.** Por `docs/process/WORKFLOW.md`, a especificação passa a ser imutável a partir da tag `spec-v1.0`. Como ela não existe, as edições em `docs/spec/` feitas nesta fase são parte do bundle inicial, não alteração de spec congelada.

**O4 — o resultado da auditoria não sobrevive à sessão. NÃO resolvido — ver §6 P11.** `log_audit.py` gravava apenas timestamp, `agent_type` e `session_id`. Duas tentativas de correção, nenhuma eficaz:

- `817e434` passou a ler o transcript e gravar o relatório em `docs/progress/audit_<timestamp>.md` no worktree principal, resolvido por `git rev-parse --git-common-dir`. Mas `SubagentStop` dispara para **qualquer** subagente, e o hook passou a gravar o texto final de qualquer um como se fosse auditoria, com veredito fabricado;
- `c8c2be3` corrigiu essa fabricação exigindo `agent_type == "checkpoint-auditor"`. Como `agent_type` chega **vazio** (O5), o ramo que grava o relatório nunca executa.

**Estado real, medido:** nenhum arquivo `docs/progress/audit_*.md` jamais foi gravado. Dos 15 registros do `audit_log.jsonl`, 14 vêm do hook e **zero** foram identificados como auditor. Nem a primeira auditoria nem a segunda foram persistidas por este mecanismo.

O único traço que sobrevive é a linha que o **próprio launcher** grava (`scripts/start_checkpoint_audit.sh:51`): há exatamente uma, com `phase=0`, `head_sha=c8c2be3` e `launcher_exit=0` — a segunda auditoria. E mesmo ela não entra no repositório, porque `docs/progress/audit_log.jsonl` está no `.gitignore:26`.

Uma versão anterior desta seção afirmava que o mecanismo funcionava. Essa afirmação foi o achado M1 da segunda auditoria e está corrigida aqui.

**O5 — `agent_type` chega vazio no payload de `SubagentStop`.** Os sete registros do `audit_log.jsonl` anteriores a `817e434` têm `agent_type` em branco, então não é possível distinguir, no histórico, quais execuções foram do `checkpoint-auditor`. O campo passou a registrar `payload_keys` para diagnosticar isso sem adivinhação na próxima auditoria.

---

## 8. Próxima fase

**A Fase 0 continua ABERTA.** Não avançar para a Fase 1.

Ordem para fechá-la:

1. **Sexta auditoria de checkpoint**, via `bash scripts/start_checkpoint_audit.sh 0`. O motivo não é formalidade: o critério do conjunto `CODE` foi refinado de "ser executável" para "ser mecanismo que aplica a spec" (§6 P26), e **o conjunto atual nunca foi conferido contra o critério novo**. Se houver uma quarta instância da linhagem P12 → P18 → P26, é o critério corrigido que a encontra. Três correções entraram depois da quarta rodada — `7302bd1`, `ee7731d` e `32bdc05` — e as duas últimas tocam o próprio gate que os passos 3 e 4 vão exercitar.
2. Decidir o destino das pendências abertas (§6). São **dezenove**: quatro declaradas por mim durante a implementação (P1–P4) e quinze vindas das auditorias (P8, P9, P11, P13–P17, P19–P25). P5, P6, P7, P10, P12, P18 e P26 estão fechadas.
   - **P11** ainda tem efeito sobre a próxima auditoria: enquanto o mecanismo de captura estiver inerte, o veredito precisa ser colado manualmente;
   - **P25** está deliberadamente adiada para a Fase 1 — mexer no `invariants.yml` na véspera de executar os PRs que testam esse mesmo workflow adiciona risco sem necessidade.
3. `bash finalize_phase0.sh` — vai até branch protection e **para antes da tag**, imprimindo os comandos dos itens 10 e 11 da DoD.
4. Executar os dois PRs descartáveis e confirmar que `spec_freeze` **reprova** nos dois.
5. Só então `bash finalize_phase0.sh --dod-10-11-verificados`, que cria e publica `spec-v1.0`. Nunca tagueie antes de provar o CI.

Depois disso, **Fase 1 — Contratos e esqueleto** (`07_IMPLEMENTATION_PHASES.md`), checkpoint ⏸. O kickoff da Fase 1 pede, antes de qualquer código: árvore de diretórios, `contracts/` completo, catálogo de eventos inicial com `truth_layer` de cada tipo, e as três decisões de modelagem mais arriscadas com recomendação. Aguardar aval humano antes de implementar.

A Fase 1 herda desta fase o contrato de caminho dos artefatos gerados (§2) e recebe P2 como trabalho seu.

---

## 9. O que esta fase ensinou

Registrado porque é o motivo de este arquivo existir, e porque some se ficar só nos commits.

**O gate mordeu.** A primeira coisa que o `checkpoint-auditor` examinou foi o mecanismo de verificação escrito para auditar todo o resto — e reprovou com um BLOCKER e quatro HIGH. A ordem de defesa de `docs/process/WORKFLOW.md` — hook, CI, auditor — funcionou na camada em que hook e CI são cegos: **verificar se o teste realmente prova o requisito.**

**Teste verde não é prova.** Os seis verificadores passavam no teste negativo antes da auditoria. O que faltava não era execução, era probe: `check_event_envelope.py` era cego para `range-core/engine/` e o probe estava plantado justamente na região que ele enxergava. Um teste cujo probe vive dentro da região coberta mede a si mesmo.

**H4 é a lição estrutural.** Enquanto a allowlist do auditor não permitiu executar o harness, toda auditoria foi inferência de leitura de código. Um mecanismo de auditoria que não consegue rodar a prova central não é auditoria independente — e isso não aparece no resultado, porque um auditor impedido continua emitindo veredito.
