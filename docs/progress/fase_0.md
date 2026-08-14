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

### Sexta auditoria: PASS, sem BLOCKER e sem HIGH

**Veredito PASS.** 0 BLOCKER, 0 HIGH, 3 MEDIUM, 6 LOW.

Rodada pedida para conferir o conjunto `CODE` contra o critério refinado — "ser mecanismo que aplica a spec" —, já que as três instâncias anteriores da linhagem tinham sido encontradas sob a formulação antiga, uma de cada vez.

| ID | Severidade | Resumo | Destino |
|---|---|---|---|
| M1 | MEDIUM | `.gitignore` fora do conjunto `CODE` — quarta instância da linhagem | corrigido em `b2fb8c2` — §6 P27 |
| M2 | MEDIUM | Deny de secrets sem `Write` | aberta, 3ª rodada — §6 P19 |
| M3 | MEDIUM | `check_event_envelope.py` só varre `.py` | aberta, 3ª rodada — §6 P20 |
| L1 | LOW | `tools/README.md` e `README_FIRST.md` desatualizados | aberta, 3ª rodada — §6 P21 |
| L2 | LOW | `README_FIRST.md` e `PHASE_0_CHECKLIST.md` descrevem o `finalize` anterior ao H2 | aberta, 2ª rodada — §6 P22 |
| L3 | LOW | Hook do auditor bloqueia leitura legítima — **modo novo, ver abaixo** | aberta, 4ª rodada — §6 P23 |
| L4 | LOW | `check_security_constraints.py` não varre os hooks | aberta, 3ª rodada — §6 P24 |
| L5 | LOW | Actions do CI presas a tag major mutável | aberta, 2ª rodada — §6 P25 |
| L6 | LOW | `.env.example` inexistente, tratado como presente | aberta, 2ª rodada — §6 P17 |

**A varredura da linhagem fechou.** Com `.gitignore` incluído, tudo que resta versionado fora do conjunto `CODE` e fora de `docs/spec/` é documentação descritiva: `CHANGELOG_V3.md`, `README_FIRST.md`, `docs/process/` e `docs/progress/`. A linhagem levou quatro rodadas — P12, P18, P26, P27 — e a quarta instância só apareceu depois de o critério ser corrigido, que é exatamente o argumento que motivou esta auditoria.

**O achado mais notável não é um finding, é o modo novo do L3.** O smoke test canônico prescrito em `PHASE_0_CHECKLIST.md:71-73` — o que valida o item 4 da DoD — **é bloqueado pelo próprio hook que ele testa**, porque `DENIED_ANYWHERE` casa `rm -rf` dentro do payload JSON entre aspas. Reproduzido: `rc=2`, com a mensagem "comando de escrita".

O auditor está estruturalmente impedido de executar o teste canônico do item 4. É a mesma classe do **H4** da primeira auditoria, que foi classificado HIGH justamente por impedir o auditor de rodar a prova central — e sobreviveu quatro rodadas depois dele por estar em uma família tratada como LOW.

### Dois itens de DoD apurados por execução nesta rodada

**Item 5 deixa de ser parcial.** As duas metades foram exercitadas: `Write` em `range-core/nope.py` bloqueado com `exit=2`, e `scenario_bash.py` distinguindo `git log --oneline` (`exit=2`) de `range-cli scenario validate` (`exit=0`). O registro marcava a allowlist de Bash como não exercitada desde o primeiro `fase_0.md`; está exercitada e funciona.

**Item 4 permanece parcial**, agora com cinco modos documentados no L3/P23, incluindo o bloqueio do próprio smoke test canônico.

**Dois desses findings acusam este próprio registro de imprecisão, e ambos procedem:**

- o **M1** contesta a classificação "formalmente conforme" que o §7 O2 dava ao commit inicial misturar `docs/spec/` e `tools/`. O texto normativo do `CLAUDE.md` diz *código*, não "range-core, domains e contracts". O O2 foi corrigido;
- o **L1** mostra que a afirmação de fechamento do P10 — *"verificado que nenhum outro ponto do repositório repete a instrução"* — era mais larga do que a verificação feita, que cobriu apenas a instrução de código de saída. O status do P10 foi corrigido para dizer o que de fato foi verificado.

### O que mudou no harness, e por quem

`scripts/phase0_negative_tests.py` foi alterado em B1, H2, H1 e H3. Isso contraria o princípio registrado em §6 P1 — *o implementador não mexe no teste que o julga*. A distinção que autoriza estas mudanças: **foram determinadas pela auditoria**, não escolhidas por quem estava sendo avaliado. P1 continua não corrigida justamente porque nasceu de julgamento meu, não de finding.

Probes passaram de 6 para 8, e a exigência deixou de ser "saiu diferente de zero" e passou a ser "saiu `1` e citou o arquivo plantado".

### Sétima auditoria: FAIL, 1 BLOCKER — a correção do P23 abriu escrita deliberada

Executada sobre `42a4779`. **Veredito FAIL**, 1 BLOCKER, 2 HIGH, 4 MEDIUM, 7 LOW. Relatório integral em `docs/progress/audit_20260814T020307Z.md` — **o primeiro relatório de auditoria a entrar no repositório**; as seis rodadas anteriores viveram no scroll da sessão e foram transcritas à mão.

O **B1** é regressão introduzida pelo commit sob auditoria: a reescrita tokenizada do `readonly_bash.py` liberou `>&` com alvo não-numérico, `sort -o` e `find -fprint0`, todos com travessia `../../` alcançando o worktree principal. O **H1**, comando da allowlist gravando no worktree principal. O **H2**, o harness declarando cobertura que não tinha.

Registrado em §6 **P32**.

### Oitava auditoria: FAIL — o limite do desenho, não mais uma via

Executada sobre `470ced8`. **Veredito FAIL**, 5 MEDIUM, 7 LOW.

**Duas capturas, uma rodada — corrigido após o M4 da nona auditoria.** Esta seção citava apenas `audit_20260814T030754Z.md`, e `audit_20260814T032039Z.md` entrava no repositório sem menção. Os dois arquivos têm o **mesmo** `session_id` (`ab69a491`) e o mesmo `head_sha` (`470ced8`): são duas capturas da mesma rodada, com conteúdos diferentes — 131 e 161 linhas. O de 161 linhas é o mais completo e é a fonte a usar; o de 131 fica versionado porque apagá-lo seria reescrever história de auditoria, e a duplicidade em si é evidência do modo de falha da captura.

**Ambas foram recuperadas com `audit_report.py --recover`, nenhuma foi automática.** A mensagem do commit `30f80c2` diz "capturado automaticamente" e está errada: as três últimas linhas de `audit_log.jsonl` — as duas desta rodada e a da nona — trazem todas `"recovered": true`. **P11 continua aberta neste commit**, e a afirmação em contrário era exatamente a classe de defeito do P33.

O achado que encerra o assunto não é um finding numerado: o auditor somou **três vias novas** ao `readonly_bash.py` tokenizado — `\r`, `$(...)` entre aspas duplas e crase entre aspas duplas — e observou que a das aspas é **estrutural**, porque `_blank_quoted` apaga o conteúdo citado antes de procurar crase, enquanto o bash expande as duas coisas dentro de aspas duplas. Cinco instâncias em três rodadas.

E declarou o que muda o método: **enquanto "o bash executaria isto?" for respondida por um parser reimplementado, a completude não é demonstrável — só refutável, uma via por rodada.** Avisou que passaria a gerar construções em vez de rodar os probes do repositório, o que é a postura correta para um auditor.

Consequência: o P23 foi **revertido** e voltou a ser pendência aberta. Ver §6 P23, reaberto.

### Nona auditoria: FAIL, 1 BLOCKER, 3 HIGH, 4 MEDIUM, 6 LOW

Executada sobre `30f80c2`. Relatório em `docs/progress/audit_20260814T034719Z.md`.

O auditor cumpriu o que anunciara na oitava: **avaliou gerando construções, não rodando a lista de probes do repositório**. Encontrou os 10 buracos que o harness declarava e classificou-os como **B1 BLOCKER**, com o argumento de que os alvos aceitam travessia `../../` e a escrita alcança o worktree principal — e registrou honestamente que essa travessia estava **assumida, não medida** por ele.

**A travessia foi medida antes de decidir a gravidade**, em sandbox com alvos sentinela, sem tocar o repositório. Resultado: **2 formas contidas, 8 atravessam**, duas delas provadas por execução real. O B1 **procede**, e foi fechado neste commit por duas regras de contenção (§6 P32).

| Finding | Destino |
|---|---|
| B1 — hook não bloqueia escrita que alcança o worktree principal | **fechado** — `..` e `git branch -D` negados; buracos de 10 para 2 |
| H1 — P32 marcada FECHADA descrevendo desenho que a reversão desfez | **fechado** — curinga de hooks fechado no código, registro corrigido |
| H2 — evidência do item 4 subdeclarada no quadro da DoD | **fechado** — célula agora traz os quatro números do harness deste commit |
| H3 — item 15 ✅ com leitura de duas rodadas atrás | **fechado** — tabela das nove rodadas, item 15 ⛔ |
| M1 — `log_audit.py` removido mas ainda nos Entregáveis | **fechado** — removido; `audit_report.py` acrescentado |
| M2 — §5 e "Estado do repositório" se contradizem | **fechado** — arbitrado a favor da §5, parágrafo congelado corrigido |
| M3 — referência a P30 onde cabia P34 | **fechado** |
| M4 — duas capturas da mesma sessão, uma citada | **fechado** — as duas registradas; "capturado automaticamente" corrigido para `--recover` |
| L1–L6 | abertas — ver §6 |

### Décima quarta auditoria: FAIL, 2 BLOCKER — enumerar sigilo era o mesmo erro de enumerar grafia

Executada sobre `ab5fcd4`. Relatório em `docs/progress/audit_20260814T144610Z.md`.

**B1 — `<(...)`, substituição de processo.** A regra da 13ª enumerava **duas grafias**, `$(` e crase. `<(` não é nenhuma das duas. Medido, `rc=0`:

```text
cat <(python -c "print(1)")        diff <(git log) <(git log)
```

E o auditor mediu a consequência, não supôs: `os.access(W_OK)` verdadeiro sobre `tools/codegen.py` do worktree **principal** e sobre `~/.claude/hooks/readonly_bash.py`, a cópia instalada do hook que o contém.

**A verificação posterior encontrou mais duas** que o relatório não citou: `>(...)` e **subshell puro `(cmd)`**, sem sigilo nenhum.

**B2 — e este é o achado que importa.** O docstring do quarto eixo definia a propriedade **pela grafia**: *"o conteúdo de `$(...)` ou de crase EXECUTA"*. Definir eixo por grafia é o mesmo erro que a 10ª puniu no eixo do alvo, cometido de novo um nível acima. A lista continuava sendo memória de quem a escreveu.

**Correção: a enumeração de sigilos foi trocada por uma propriedade.** Toda substituição e todo subshell do bash exigem **parêntese não citado** — `$(cmd)`, `<(cmd)`, `>(cmd)`, `(cmd)`, `$((...))`. O hook passa a negar parêntese fora de aspas, e só isso. Parêntese **dentro** de aspas continua liberado, porque `--format='%(refname)'` e `grep -n "foo(bar)"` são leitura legítima e comuns em auditoria.

E aqui a queda de segurança é **para o lado fechado**, ao contrário da queda em `_segmentos`: parse duvidoso bloqueia, porque não enxergar um parêntese libera execução, enquanto não enxergar um separador só bloqueia mais.

**H1 — a regra de flags dizia ser escopada por comando e não era.** `grep -o` e `rg -o` são `--only-matching`, leitura pura, e eram bloqueados. O comentário afirmava *"a superfície é FECHADA POR COMANDO"* enquanto a regex não mencionava comando nenhum: casava `-o` em qualquer posição de qualquer comando.

**Desenho declarado e mecanismo implementado divergiam — dentro do commit que se propunha a atacar os falsos bloqueios por causa.** É a mesma classe que este registro cobrou de si mesmo três vezes, e desta vez a divergência estava no comentário que eu escrevi para justificar a regra. Corrigido: o comando dono da flag precisa aparecer antes dela, no mesmo segmento.

**M1** é a célula do item 7 descrevendo o deny anterior à correção do próprio commit — quinta instância da linhagem P10/P15/P17/P22. Corrigida abaixo.

**Resultado medido: 17 leituras legítimas liberadas (eram 13), 4 falsos bloqueios, 0 escritas não bloqueadas.**

**O padrão dos eixos ganhou um andar.** Não é que exista um quinto eixo: é que o **quarto foi definido por enumeração** e a enumeração vazou. A lição que fica escrita no harness é a regra de admissão de eixo — **um eixo se define pela propriedade que o gera, nunca pelas grafias lembradas** —, e ela agora vale para os quatro.

### P23 — a metade "libera leitura" do item 4, atacada por causa e não por caso

**Cinco rodadas, onze falsos bloqueios declarados, nenhuma rodada dedicada a eles.** Sempre LOW, sempre "falha para o lado seguro". Mas cada falso bloqueio **empurra a auditoria de medição para inferência de leitura de código** — a degradação que fez o H4 da primeira rodada ser HIGH, e a razão pela qual várias rodadas registraram "não consegui verificar" onde deveriam ter medido.

Atacados por **causa**, em quatro grupos, não um a um:

| Causa | Casos | Correção |
|---|---|---|
| `2>/dev/null` casava a regra de redirecionamento | 3 | `/dev/null`, `&1` e `&2` isentos — descarte e duplicação de descritor não persistem nada |
| segundo segmento do pipe sem allowlist | 1 | filtros de leitura entram: `sort`, `cut`, `tr`, `nl`, `rev`, `comm`, `join`, `column`, `fold`, `basename`, `dirname` |
| `git tag` negado inteiro | 2 | forma de **leitura** é fechada: `git tag` só, ou `--list`/`-l`. `git tag v9.9.9` e `-d` seguem bloqueados |
| **separador dentro de aspas** | 1 + a família P8/P16 inteira | máscara de citação |
| âncora `$` do harness e dos hooks recusava sufixo | 2 | admite só `2>/dev/null`; a âncora continua fechando o resto |

**Resultado medido: 13 leituras legítimas liberadas (eram 5), 4 falsos bloqueios (eram 11), 0 escritas não bloqueadas.**

**A máscara de citação é a correção estrutural, e é a que a oitava auditoria havia reprovado.** O `|` de `grep -n "a\|b"` nunca foi pipe: é conteúdo citado. A tentativa anterior falhou porque apagava o conteúdo citado **antes** de procurar substituição, e o bash expande `$()` dentro de aspas duplas.

**Aqui a ordem é a inversa, e é isso que a torna segura:** `DENIED_ANYWHERE` roda contra o comando **cru** — inclusive `$(...)` e crase, negados desde a 13ª —, e a máscara serve **apenas** para delimitar segmentos. Nada que aconteça na máscara pode liberar escrita que a negação pegaria.

**E ela cai para o lado seguro quando o parse pode divergir do bash.** Aspas escapadas ou não fechadas devolvem `confiavel=False`, e o hook volta ao texto cru, que acha **mais** separadores. Isso é probado nas duas direções em `MASCARA_ADVERSARIAL` — cinco probes adversariais da própria correção, porque ignorar separador citado é a direção *fail-open* e afirmar que ela é segura sem medir seria a classe de defeito que a 11ª e a 13ª puniram.

**Os quatro que ficam são decisão, não pendência:**

- **laço de shell** e **`$(...)`** são estrutura de controle e execução. Liberar o laço é liberar o corpo dele; liberar substituição foi o B1 da 13ª;
- **o smoke test canônico** cita `rm -rf` dentro do payload JSON. Isentá-lo exigiria `DENIED_ANYWHERE` consciente de aspas — a direção fail-open, exatamente o que a oitava reprovou. Roda de uma sessão comum;
- **leitura fora do worktree** é o custo deliberado da contenção.

**`allowlist_e_a_revisada()` provou o valor no primeiro uso real.** Ao acrescentar os filtros, ele reprovou com doze nomes não revisados e me obrigou a examinar cada um. **`uniq` foi rejeitado na revisão**: escreve por **posicional** — `uniq entrada saida` —, mesma família do `find -fprint0`, sem flag para negar. `sort -u` cobre o uso. O desenho da sétima auditoria já o removera pelo mesmo motivo, e sem o probe ele teria voltado silenciosamente. **É a primeira vez nesta fase que um mecanismo impediu a reintrodução de um defeito conhecido em vez de a auditoria seguinte encontrá-lo.**

### P17 nunca fechou por um motivo mecânico: o deny é mais largo que a norma e torna `.env.example` incriável

**Descoberto ao tentar criar o arquivo, 2026-08-14.** A ferramenta recusou: *"File is in a directory that is denied by your permission settings."*

**A regra e a norma não batem:**

| | Caminhos |
|---|---|
| `CLAUDE.md` §Secrets | `.env`, `.env.local`, `.env.*.local`, `secrets/` — e diz explicitamente: ***"`.env.example` é permitido e deve conter apenas placeholders"*** |
| `.claude/settings.json:9-10` | `.env`, **`.env.*`**, `secrets/**` |

`.env.*` casa `.env.example`. **O mecanismo proíbe o que o texto normativo permite** — e não por engano de digitação: `.env.*` é mais largo que a enumeração da norma, que fala em `.env.*.local`.

**Consequência medida:** a P17 está aberta desde a terceira auditoria, foi reconfirmada em **cinco** rodadas e classificada LOW em todas. Nenhuma delas diagnosticou a causa. O arquivo não faltava por esquecimento — **nenhum agente jamais poderia tê-lo criado**, e o achado se repetia porque a correção era impossível pelo caminho que os agentes têm.

**Resolvido por decisão do operador, 2026-08-14, com a autorização explícita de "se for necessário relaxar alguma regra para fins de produtividade, podemos — a prioridade é funcionalidade".**

O deny foi **alinhado ao texto normativo**, não afrouxado além dele: `.env`, `.env.local`, `.env.*.local`, `secrets/**` — exatamente a enumeração de `CLAUDE.md` §Secrets. `.env.example` foi criado com placeholders. **P17 fechada após cinco reconfirmações.**

**Consequência que fica declarada, não escondida:** `.env.production` e `.env.staging` deixam de ser negados, porque a norma não os lista. No mundo real esses arquivos têm segredo. Se o projeto quiser cobri-los, o lugar de dizer isso é `CLAUDE.md` — e aí o mecanismo segue a norma, em vez de a norma ser inferida do mecanismo. **Registrado como pendência de norma, não de código.**

**O trade-off que existia antes da decisão:**

- **alinhar à norma** (`.env`, `.env.local`, `.env.*.local`) devolve a capacidade de criar e ler o exemplo, mas deixa `.env.production` e `.env.staging` fora do deny — a norma não os lista, e no mundo real eles têm segredo;
- **manter `.env.*`** preserva a proteção larga, e aí o `.env.example` é artefato **humano**: criado uma vez à mão, versionado, nunca editado por agente. Custo: agente também não consegue **ler** o exemplo para saber que variáveis existem.

A segunda opção é defensável como postura, mas então `CLAUDE.md` deveria dizer que o exemplo é criado pelo operador, e a P17 deveria estar marcada como "aguardando ação humana" em vez de reaparecer como LOW a cada rodada. **É a lacuna entre norma e mecanismo que precisa fechar, não o arquivo.**

**A classe é a mesma de duas outras desta fase.** `Write(...)` inerte no deny e o deny de secrets contornável por `cat` vieram de supor comportamento de plataforma sem exercitá-lo. Esta vem do inverso — a plataforma faz **mais** do que a norma manda —, e a lição é a mesma: **regra de mecanismo e texto normativo divergem em silêncio até alguém exercitar a fronteira.**

### Décima terceira auditoria: FAIL, 1 BLOCKER, 1 HIGH — o quarto eixo, e uma regressão por reversão que ninguém rastreou

Executada sobre `1a4aa9e`. Relatório em `docs/progress/audit_20260814T054640Z.md`, **capturado automaticamente** — primeira rodada em que o artefato entra no repositório sem intervenção.

**B1 — substituição de comando.** `$(...)` e crase **executam sem sair do segmento**, então a validação por primeira palavra nunca os enxerga. Medido, `rc=0` em todos:

```text
echo $(python -c "print(1)")        which $(python -c "print(1)")
echo `python -c "print(1)"`         printf %s $(python -c "print(1)")
```

O auditor foi além da decisão do hook e mediu a consequência: o processo resultante tinha `os.access(..., W_OK) == True` sobre `tools/codegen.py` do worktree principal. **O auditor podia reescrever os verificadores que audita.** Nenhuma das regras de contenção alcançava, porque dentro do `$()` o alvo é absoluto e não há flag.

**E esta via já tinha sido encontrada.** A oitava auditoria a achou no desenho tokenizado; a reversão do P23 a reintroduziu **sem entrá-la na lista de defeitos declarados**. É a primeira regressão-por-reversão registrada nesta fase, e o mecanismo que deveria pegá-la — a lista de defeitos afirmados — falhou porque ninguém migrou o achado ao reverter. Um defeito conhecido que sai do harness vira defeito esquecido; foi exatamente o que a condição 4(e) do item 4 reformulado diz, aplicado a si mesmo.

**H1 — o probe de substituição não exercitava substituição.** A entrada era `("execucao dentro de substituicao de comando", "git ls-files \`rm -rf x\`")`, e bloqueava pela regra do token `rm`: **medido, dá `rc=2` idêntico sem a crase**. Nada nele dependia da substituição.

É a **terceira** instância da mesma armadilha — antes dela o `env rm -rf x` e, antes, a grafia única de alvo. E a segunda que eu deixei no arquivo **enquanto documentava o defeito idêntico duas linhas acima**. A regra que faltava está agora escrita no código: **a carga de um probe de eixo não pode conter token denylistado**, senão o probe passa pela regra do token e não pelo eixo.

**Quarto eixo, e o padrão dos eixos se confirma:**

| Rodada | Eixo | O que o harness não variava |
|---|---|---|
| 10ª | alvo | uma grafia só (`../../`) |
| 11ª | comando | conjunto fixo, lembrado |
| 12ª | composição | segmento único, sempre |
| 13ª | **substituição** | nenhum probe real; o que havia era rótulo |

**M2/P24 fechado, e custou zero.** `check_security_constraints.py` não varria `.claude/hooks/` nem `user-scope/hooks/` — na Fase 0, praticamente todo o código executável do repositório, incluindo o arquivo que decide o que o auditor pode rodar. Aberta desde a quarta auditoria, na terceira reconfirmação. **Medido antes de incluir: a árvore sai `rc=0`.** Cinco rodadas de LOW/MEDIUM para uma mudança de uma linha sem custo — o que é um argumento contra deixar pendência barata envelhecer.

**M1** é a tabela de rodadas desatualizada; ver a nota na própria tabela. **L1** é o `.env.example`, e virou achado próprio (abaixo).

### Décima segunda auditoria: FAIL, 2 BLOCKER — o terceiro eixo, que nenhum probe tocava

Executada sobre `218bb77`, worktree íntegro, execução real do começo ao fim.

**B1 — `\n`, `\r` e `&` não estavam no separador de segmentos.** `re.split(r"\|\||&&|;|\|", cmd)` cobria quatro separadores; o bash honra sete. E a omissão era **total**, não parcial: como cada segmento é validado isoladamente, bastava a **primeira palavra** ser allowlistada para todo o resto passar sem validação nenhuma.

Medido, com `rc=0` em todos:

```text
pytest --version\npython -c "open('<qualquer caminho>','w')"
pytest --version\rpython -c "..."
pytest --version & python -c "..."
```

Alvos que passaram: `CLAUDE.md`, `tools/`, `docs/spec/00_MASTER_SPEC.md` e **a cópia instalada do próprio hook**. Nem a regra de `..` nem a de flags de saída alcançavam — o alvo é absoluto e não há flag. O auditor provou a escrita ponta a ponta com sentinela em `%TEMP%`, deliberadamente fora do repositório.

**B2 — o eixo que faltava.** As 33 provas de escrita e as 32 de grafia de alvo eram **todas de segmento único**. O eixo do **alvo** estava coberto desde a 10ª; o eixo do **comando** passou a estar na 11ª com `allowlist_e_a_revisada()`; o eixo da **composição** — como comandos são encadeados — não era exercitado por probe nenhum. O harness imprimia "0 escritas não bloqueadas" com o B1 aberto, e a célula da DoD citava esse número como evidência.

Correção: **`SEPARADORES_DE_COMANDO`**, sete separadores, cada um testado como prefixo legítimo (`git status`) seguido de carga de escrita. O prefixo legítimo é o ponto — sem ele o probe passaria pela regra do próprio comando de escrita e não pela composição, que foi exatamente o defeito do probe `env rm -rf x` punido na 11ª.

**Três eixos, três rodadas, e o padrão fica visível.** Alvo, comando, composição. Cada rodada expôs um eixo que o harness não variava, e em cada uma a lista estava "completa" segundo quem a escreveu. Não há razão para supor que três são todos — mas os três agora são asseridos, e um eixo asserido não regride em silêncio.

**M2 — o deny de secrets era escopado por ferramenta.** `.claude/settings.json` nega `Read`/`Edit` de `.env` e `secrets/`, e essas regras valem para as **ferramentas de arquivo** do Claude Code. `cat .env`, `head .env.local`, `grep -r x secrets/` e `stat .env` passavam pelo Bash — medidos com `rc=0`. `CLAUDE.md` §Secrets diz *"nunca leia"*, sem restringir a ferramenta. Fechado no hook.

Latente nesta fase, porque nenhum desses arquivos existe. **Exposição real na Fase 1**, cujo DoD põe `RANDOM_SEED` em `.env` — e é a segunda vez que a distinção "regra de ferramenta ≠ regra de caminho" aparece nesta fase, depois do `Write(...)` inerte. As duas vêm de supor comportamento de plataforma sem exercitá-lo.

**M1 procede, e é sobre o registro do P11 abaixo.** O auditor mediu o `audit_log.jsonl`: zero linhas com `manual_recovery`, zero com `"recovered": false`. O mecanismo `--via launcher-trap` existe no código, mas **entrou no commit seguinte à captura que fechou o P11** — então nenhum artefato do repositório sustenta a afirmação. A seção abaixo é **atestação do operador**, e agora está rotulada como tal, no mesmo padrão dos itens 9 a 13. A prova por artefato vem na próxima captura.

**H1** é `docs/process/` fora do conjunto `CODE` — registrado como P36 na branch `spec-change/dod-item-4-limite-declarado`, adiado por decisão do operador. Terceira rodada consecutiva a levantá-lo por auditor independente.

**P35 não cobre esta rodada**, e o auditor apontou sozinho pela segunda vez: B1 é omissão de três separadores de uma lista, corrigível em uma linha, não a propriedade universal indecidível. Condição 3.

### P11 FECHADO por evidência versionada — a prova por artefato chegou

**A captura da 12ª rodada gravou, no `audit_log.jsonl` versionado:**

```json
{"head_sha": "218bb77206888b4002681d270a0aecac68b30afa", "verdict": "FAIL",
 "recovered": true, "manual_recovery": false, "capture_via": "launcher-trap",
 "report_path": "docs/progress/audit_20260814T053247Z.md"}
```

**`manual_recovery: false` e `capture_via: launcher-trap`** — o operador digitou `/exit` e o relatório de 15 KB entrou no repositório sem nenhum comando manual. É a primeira captura a passar pelo código que distingue os dois caminhos, e ela distinguiu.

**O P11 deixa de ser atestação e passa a ser a segunda camada de verdade: evidência observável, versionada, verificável por quem não estava na sessão.** Foi o que o M1 da 12ª auditoria exigiu, e a exigência estava certa — a rodada anterior tinha o comportamento, não tinha o artefato.

**Treze rodadas para fechar, e o desenho da correção é a lição.** A pendência não foi resolvida por fazer a captura funcionar; ela já funcionava na 11ª rodada. Foi resolvida por tornar o resultado **distinguível no registro** — enquanto `recovered: true` significava as duas coisas, funcionar e não funcionar produziam o mesmo artefato, e nenhuma quantidade de execuções bem-sucedidas teria fechado a pendência. Vale para além do P11: **um mecanismo que não deixa rastro distinguível não é verificável, por mais que funcione.** É a mesma razão por que os itens 9 a 13 seguem em atestação.

**O que fecha junto.** As cinco confusões de ID desta fase — §0 e §6 P26, P32 — tinham todas a mesma raiz: sem relatório persistido, cada rodada chegava por transcrição manual, e o que não fosse transcrito não existia para este arquivo. A partir daqui, cada rodada deixa relatório versionado com `head_sha`, `session_id` e veredito.

### Como o P11 estava registrado até aqui — atestação, e por quê

**2026-08-14, primeira vez em onze rodadas.** O operador digitou `/exit` na sessão do auditor e o launcher imprimiu, sozinho:

```text
Relatorio capturado: docs/progress/audit_20260814T051115Z.md
Veredito detectado: FAIL
```

18 KB, com `head_sha` e `session_id` corretos. **Nenhum comando manual.** As onze rodadas anteriores dependeram de transcrição ou de `--recover` digitado à mão, e é dessa pendência que saíram as **cinco** confusões de ID desta fase.

**Camada de verdade, rotulada após o M1 da 12ª auditoria — e resolvida na captura seguinte.** O parágrafo acima era **declaração do operador**, terceira camada. O auditor mediu as 51 linhas do `audit_log.jsonl`: **zero** com `manual_recovery`, **zero** com `"recovered": false`. A correção que distingue captura automática de recuperação manual entrou no commit **seguinte** ao da captura que fechou o P11, então nenhum artefato sustentava a afirmação — e o M1 estava certo em exigir o rótulo.

**A captura seguinte forneceu o artefato** (ver a seção acima): `manual_recovery: false`, `capture_via: launcher-trap`. A pendência foi de declaração a evidência em uma rodada, e o caminho — rotular honestamente em vez de defender a afirmação — é o que tornou a diferença visível.

**Uma ressalva medida, e ela vira correção.** O log gravou `"recovered": true` mesmo nesta captura automática, porque o launcher chama `audit_report.py --recover` **no próprio trap de saída** (`start_checkpoint_audit.sh:88`) — o mesmo caminho de código da recuperação manual. Ou seja: **o campo que deveria provar o P11 não distinguia os dois casos**, e teria mantido a pendência ambígua para sempre. Foi essa exata ambiguidade que produziu a contradição apontada pelo M4 da nona auditoria entre a mensagem do commit ("capturado automaticamente") e o log (`recovered: true`) — os dois estavam certos, e o campo é que era cego.

Corrigido: o launcher passa `--via launcher-trap`, e o log ganha `manual_recovery`, verdadeiro **só** quando o operador teve de recuperar à mão. `recovered` fica como está, para não reescrever a leitura das linhas antigas.

### `Write(...)` no deny de secrets não existe — P13/P19 eram premissa falsa, e o H2 da décima auditoria estava errado

Ao encerrar a sessão, o próprio Claude Code respondeu:

```text
Permission deny rule (.claude/settings.json): Write(.env) is not matched by file
permission checks — only Edit(path) rules are. Use Edit(.env) instead
(Edit rules cover all file-editing tools).
```

**`Edit(.env)` já cobre a ferramenta `Write`.** Nunca houve lacuna. A pendência nasceu como **P13** na terceira auditoria, foi reconfirmada como **P19** na quarta, reapareceu em três rodadas seguintes, foi listada como HIGH pela décima, e o item 7 da DoD ficou marcado ⚠️ parcial durante seis rodadas — tudo sobre um buraco que não existia.

**Eu implementei o H2 sem verificar a premissa**, e as três regras `Write(...)` que acrescentei eram inertes: não negavam nada e passaram a emitir aviso a cada sessão. Removidas. O item 7 é **PASS desde sempre**, e o que faltava não era regra, era conferir o comportamento da ferramenta antes de acreditar no finding.

**A lição é a mesma das seis correções do §6 P32, e mais dura, porque desta vez a fonte de verdade estava disponível o tempo todo.** Seis auditorias adversariais concordaram entre si sobre uma propriedade da plataforma que nenhuma delas mediu — e a plataforma respondeu na primeira vez que alguém a exercitou. Um finding repetido por muitas rodadas ganha aparência de fato verificado; concordância entre auditores não é medição. **Auditor também é terceira camada de verdade quando fala do que não executou.**

### Décima primeira auditoria: FAIL, 2 BLOCKER — a tese refutada dentro do próprio arquivo

Executada sobre `8b4d627`, com worktree íntegro do começo ao fim e execução real. Foi a rodada mais bem instrumentada da fase: o auditor rodou os seis verificadores, o harness completo e os smoke tests, e mediu por execução, não por leitura.

**B1 — três vias, todas confirmadas, mais duas que a verificação posterior somou.** O commit anterior declarava a tese *"o que se verifica por texto não é contenção, é ausência de capacidade"*, e a tese foi refutada **no próprio arquivo que a implementava**: `find` saiu da allowlist, e ficaram lá `env` e `git`, ambos com capacidade de escrita.

| Via | Medido |
|---|---|
| `env python -c "open('x','w')"` | `rc=0` — **execução arbitrária**; `env` estava allowlistado sem nenhuma restrição sobre o que invoca. O probe `python -c` bloqueava; bastava prefixar com `env` |
| `git diff --output=…` | `rc=0` — e `git show`/`git log` também, que a auditoria não citou e a verificação encontrou |
| `git branch -m/-M/-f/-c` | `rc=0` — negar só `-d/-D` era enumerar um quinto de uma família que muta o ref store compartilhado |

A justificativa que eu escrevera — *"a superfície é fechada por comando, são as flags de saída que essas **cinco** ferramentas documentam"* — esquecia a sexta família allowlistada, `git`, que é a maior de todas. `env` é pior que qualquer flag: é execução arbitrária, e permitia sobrescrever o próprio hook instalado do auditor.

**B2 — um probe que passava pelo motivo errado.** A entrada rotulada *"env como trampolim de execucao"* usava `env rm -rf x` e passava pela regra do token `rm`; **nada nela exercitava `env`**. Um probe que carrega o nome da propriedade que não mede é pior que nenhum probe: ele ocupa o lugar dela na lista. E a matriz de 32 provas variava a grafia do **alvo** mantendo fixo o conjunto de **comandos** — o mesmo erro do B2 anterior, num eixo diferente. `BURACOS_CONHECIDOS` vazia foi apresentada como resultado, e estava vazia por as formas não terem sido procuradas.

**Correção, e desta vez ela troca a pergunta em vez de estender a lista.**

- `env` **removido**. Não custa nada: `SAFE_ENV_PREFIX` já aceita `VAR=valor` antes do comando, então `PYTHONDONTWRITEBYTECODE=1 pytest` segue passando.
- `git branch` **removido** dos subcomandos. `for-each-ref` lista ramos e não muta.
- `--output` **negado**, cobrindo `git diff`/`log`/`show`.
- Os probes de defeito e buraco conhecido passam a rodar contra a **cópia instalada** (M1) — antes só `expect_hook_allows`/`expect_hook_blocks` o faziam.
- **`allowlist_e_a_revisada()`** — o probe estrutural que faltava.

**Por que esse último é a mudança que importa.** Onze rodadas repetiram o mesmo padrão: o harness prova as formas que quem escreveu lembrou, e a rodada seguinte encontra uma que ele não lembrou. *"Lembrei de todos os comandos?"* **não é decidível**. *"A allowlist é o conjunto que foi revisado?"* **é**. O probe afirma o conjunto: acrescentar comando à allowlist reprova o harness até que ele entre em `COMANDOS_REVISADOS`, o que força a revisão de capacidade de escrita a acontecer **no momento da mudança**, não na auditoria seguinte. Foi assim que `env` sobreviveu onze rodadas — nunca houve um momento em que alguém tivesse de justificá-lo.

Ele mordeu na primeira execução, acusando três nomes; eram subcomandos que a extração confundia com comandos, e a extração foi corrigida. Um probe que não acusa nada ao nascer não prova que a lista está limpa.

**H1, H3 e M2 são erros meus de registro, e todos da mesma família.** A célula do item 4 na tabela §5 continuava dizendo *"32 bloqueadas, 2 não bloqueadas"* depois de o commit anterior levar as não bloqueadas a zero — reabrindo, no commit seguinte, exatamente o H2 que a nona auditoria fechara. E a narrativa da décima rodada adiava um achado *"para o P36"*, que **não existe nesta branch**: é a numeração da branch de `spec-change`, e aqui a série vai até P35. Referência pendurada criada pela minha própria renumeração — a quinta confusão de IDs da fase.

**O limite, dito pelo auditor e aceito aqui.** *"Provei que três vias existem; não provei que são as únicas. Enquanto a pergunta 'o bash executaria isto?' for respondida por casamento textual, a completude não é demonstrável — só refutável, e refutei mais três."* É a mesma conclusão da oitava rodada, agora com o corolário prático: **a resposta não é fechar a próxima via, é reduzir a superfície e tornar o conjunto asserido.**

**P35 não cobre esta rodada, e o auditor apontou isso sem que ninguém pedisse.** Pela condição 3 da própria decisão, qualquer BLOCKER de outra natureza reprova como sempre — e B2 em particular não é sobre a definição do item 4, é sobre o oráculo afirmar propriedade que não tem. **O merge não procede com esta rodada.**

### Décima auditoria: FAIL, 2 BLOCKER — a correção do B1 repetiu o erro que ela fechava

Executada sobre `2065d244`. Relatório em `docs/progress/audit_20260814T044412Z.md`. **Rodada comprometida por minha culpa, e mesmo assim a mais útil da fase.**

**O que eu quebrei.** Lancei o launcher em segundo plano, sem terminal. A sessão do auditor subiu, mas a camada de permissão recusou **toda** execução — o auditor não conseguiu rodar um único comando. Depois, ao "limpar" o que eu julgava um lançamento travado, **removi o worktree com a sessão viva dentro**. É o M1 do relatório. Onze dos catorze itens da DoD saíram NÃO VERIFICADO, e por isso **esta rodada não vale como gate**. O relatório sobreviveu porque `audit_report.py` grava estado antes da sessão — a função que o P11 existe para prover, exercida pelo acidente que ela previa.

**B1 — e ele procede, medido.** A correção de contenção do commit anterior negava `..` e **deixava caminho absoluto, `~` e `$HOME` abertos**. Sete das oito formas declaradas fechadas reabriam trocando a grafia do mesmo alvo. Medido aqui, todas com `rc=0`:

```text
find . -fprint0 /c/Projetos/aurora-cyber-range/tools/codegen.py
pytest --junitxml=/c/Projetos/aurora-cyber-range/CLAUDE.md
find /c/Projetos/aurora-cyber-range -delete
find . -fprint0 ~/.claude/hooks/readonly_bash.py
python -m pytest --junitxml=$HOME/.claude/hooks/readonly_bash.py
```

A última **sobrescreve o hook instalado do próprio auditor** — precisamente o comprometimento que a colocação em escopo de usuário existe para impedir (`WORKFLOW.md` §Por que o auditor não mora no repositório).

**B2** — o harness provava as oito com o literal `../../` e nenhum probe usava alvo absoluto: ficava verde certificando uma contenção que não existia. E declarava `find . -delete` como "contida" enquanto a mesma allowlist aprovava `find /c/Projetos/... -delete`, violando o critério de admissão que o próprio arquivo fixava.

**A lição, e ela é sobre mim.** Eu escrevi que "o invariante não é a flag, é o alvo" e então **policiei uma grafia do alvo**. Um alvo tem infinitas grafias; policiá-lo por texto é sempre refutável, que é literalmente o argumento que matou o item 4 antigo. Repeti a classe de erro dentro da correção que deveria encerrá-la, e o registro anterior chegou a dizer "duas regras, não oito" como se fosse profundidade.

**O que se verifica por texto não é contenção, é ausência de capacidade.** Correção:

| | Antes | Agora |
|---|---|---|
| `find` na allowlist | sim — escreve por ação e por flag, alvo posicional arbitrário | **removido**; `git ls-files`, `rg` e `ls` cobrem a leitura |
| flags de saída de `pytest`/`ruff`/`mypy`/`eslint`/`tsc` | liberadas | **negadas**, enumeradas por comando |
| probes de travessia | 8, todos com `../../` | 8 formas **× 4 grafias** = 32 provas de invariante |
| probes contra a cópia instalada | nenhum — só a fonte versionada | **as duas**, quando a cópia existe (H4) |
| escritas não bloqueadas | 2, declaradas "contidas" | **0** |

A enumeração de flags é defensável onde a de alvos não era: a superfície é **fechada por comando** — são as flags de saída que essas cinco ferramentas documentam —, enquanto a de alvos é aberta. Flag nova é finding pelo item 4(d), não defeito aceito.

**H2 fechado: `Write` entrou no deny de secrets.** Era P13, reconfirmada como P19 e reaberta em três rodadas desde então. Seis rodadas aberta, fechada em uma linha.

**H3 é o `docs/process/` fora do conjunto `CODE`, acontecendo ao vivo.** *(A versão anterior deste parágrafo adiava o achado "para o P36", que não existe nesta branch — a série aqui vai até P35, e P36 é a numeração da branch `spec-change/dod-item-4-limite-declarado`, onde a pendência de fato está registrada. Referência pendurada, apontada pelo H3 da 11ª auditoria.)* O auditor apontou que `2065d244` alterou `PHASE_0_CHECKLIST.md` — o documento que define a DoD — no mesmo commit que ela julga, fora de qualquer gate, porque `docs/process/` não está no conjunto `CODE` do `spec_freeze`. É a pendência adiada para depois da Fase 1, **encontrada por um auditor independente que não sabia que ela estava registrada**. Isso eleva a prioridade dela: deixa de ser observação minha e passa a ser achado externo reproduzido.

**O que a rodada custou e o que ensinou sobre o método.** Uma auditoria sem execução, com o worktree destruído no meio, ainda assim encontrou dois BLOCKER reais por leitura de regex — e o segundo deles é sobre o oráculo que deveria ter pego o primeiro. Vale registrar o que o próprio auditor escreveu: *"nada nesta auditoria é prova de execução; B1 e B2 derivam de leitura de regex e da allowlist, não de comando executado."* Ele declarou o limite e acertou mesmo assim. A medição posterior confirmou.

**O que a nona rodada provou sobre o método.** O auditor gerou construções em vez de confiar na lista, e a lista estava certa quanto ao *quê* e errada quanto ao *tanto faz*: dizia "10 buracos" e tratava todos como equivalentes. A distinção que faltava — **contido no worktree × alcança o worktree principal** — não estava em lugar nenhum, e é ela que separa defeito aceitável de finding. Entrou no critério de admissão do harness e na condição (c) do item 4 reformulado.

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
| 4 | Hook do auditor bloqueia escrita e libera verificadores de leitura | ⚠️ **as duas direções tratadas; a definição é que segue insatisfazível.** **Escrita:** 33 formas bloqueadas, mais 32 provas de invariante de alvo, 7 de composição e 8 de substituição — e o eixo da substituição passou a ser verificado por **propriedade** (parêntese fora de aspas), não por lista de sigilos. **0 não bloqueadas**. **Leitura:** 17 liberadas e **4 falsos bloqueios**, os quatro por decisão registrada (§6 P23). O item só passa quando a reformulação do `spec-change` entrar |
| 5 | Hook do `scenario-designer` bloqueia Write/Edit fora de `scenarios/` e Bash fora da allowlist | ✅ **as duas metades exercitadas**, com a evidência corrigida na oitava auditoria: `Write` em `range-core/nope.py` → `exit=2`; `scenario_bash.py` devolve `exit=2` para `git log --oneline` e `exit=0` para `range-cli scenario validate scenarios/academus/pack`. **`range-cli scenario validate` sem argumento também dá `exit=2`** — a evidência anterior afirmava `exit=0` para essa forma, o que nunca foi verdade (§6 P33) |
| 6 | `ground_truth.yaml` e `GM_NOTES.md` **não** estão no `.gitignore` | ✅ aparecem apenas em comentário que documenta o versionamento deliberado |
| 7 | `.env`/secrets negados em `.claude/settings.json` | ✅ **PASS** — `Read`/`Edit` de `.env`, `.env.local`, `.env.*.local` e `secrets/**`, exatamente a enumeração de `CLAUDE.md` §Secrets, e **`Edit` cobre a ferramenta `Write`** por desenho do Claude Code. Somado a isso, o hook do auditor nega leitura de secret por caminho de shell (`cat .env`), que o deny por ferramenta não alcança. *(Esta célula dizia `.env.*` — o deny anterior à correção da P17, feita no mesmo intervalo de candidatura: era o M1 da 14ª auditoria, quinta instância da linhagem P10/P15/P17/P22.)* |
| 8 | Auto Mode desabilitado para este projeto | ✅ `defaultMode: default`, `disableAutoMode: disable` |
| 9 | Primeiro push de `main` deixa `arquitetura` e `seguranca` verdes | ✅ **por ATESTAÇÃO DO OPERADOR** — não verificado por auditoria (§6 P34) |
| 10 | PR descartável confirma que `spec_freeze` falha com spec e código juntos | ✅ **por ATESTAÇÃO DO OPERADOR** — reprovou pela mensagem esperada (§6 P34) |
| 11 | PR descartável confirma título `spec-change:` para alteração só de spec | ✅ **por ATESTAÇÃO DO OPERADOR** — reprovou pela mensagem esperada (§6 P34) |
| 12 | Branch protection em `main` exige `arquitetura`, `spec_freeze`, `seguranca` | ✅ **por ATESTAÇÃO DO OPERADOR** — aplicada com `enforce_admins: true` (§6 P34) |
| 13 | `spec-v1.0` criada depois de CI e branch protection | ✅ **por ATESTAÇÃO DO OPERADOR** — tag publicada (§6 P34) |
| 14 | `/doctor` sem apontamentos relevantes | ✅ executado nesta sessão, sem achados |

**Quem executa o quê, corrigido após o H2 da terceira auditoria.** `bash finalize_phase0.sh` executa os itens **9, 12 e 13** — push, espera de CI, branch protection e tag. Os itens **10 e 11 são manuais**: exigem PR descartável comprovando que `spec_freeze` reprova spec+código no mesmo PR e que alteração só de spec exige título `spec-change:`.

O script parava de declarar "FASE 0 CONCLUÍDA" e criar `spec-v1.0` sem que 10 e 11 tivessem sido executados. Agora ele para antes da tag, imprime os comandos exatos dos dois PRs descartáveis, e só cria a tag numa segunda invocação explícita: `bash finalize_phase0.sh --dod-10-11-verificados`. A flag é a afirmação do operador de que executou os dois PRs e viu `spec_freeze` reprovar nos dois.

**Os itens 9 a 13 estão fechados por ATESTAÇÃO DO OPERADOR, não por verificação.** A distinção é deliberada e não é formalidade: nenhum auditor de checkpoint pode verificá-los com as ferramentas atuais — `gh` não está na allowlist do auditor e execução de CI não é observável de dentro de um worktree. O que está registrado é a declaração do operador de que executou `finalize_phase0.sh`, de que os dois PRs descartáveis reprovaram pela mensagem esperada, e de que a branch protection foi aplicada. Ver §6 P34 para a constatação estrutural e a decisão pendente. *(Dizia §6 P30, que é uma linha da revisão de referências cruzadas sobre `02_DOMAIN_ACADEMUS.md:126`. Corrigido após o M3 da nona auditoria — e notável porque P28–P31 são precisamente o achado "referência aponta para a seção errada".)*

Isto é a terceira camada das quatro (`declaração`), não a segunda (`evidência observável`). Registrar atestação como se fosse verificação seria exatamente o que o `CLAUDE.md` proíbe em "Quatro camadas de verdade".

**Item 15, não listado no checklist mas exigido por `docs/process/WORKFLOW.md`: auditoria de checkpoint com veredito PASS.** Status ⛔ **NÃO satisfeito.**

**Corrigido após o H3 da nona auditoria.** Este parágrafo dizia ✅ com ressalva, apoiado em "quatro auditorias: FAIL; PASS; PASS; PASS sem BLOCKER e sem HIGH". Era uma leitura congelada em `470ced8`, duas rodadas atrás. O estado real:

| Rodada | Veredito |
|---|---|
| 1ª | FAIL |
| 2ª | PASS, com três correções |
| 3ª | PASS, com dois HIGH |
| 4ª | PASS, sem BLOCKER e sem HIGH |
| 5ª | não transmitido (P11) |
| 6ª | PASS, 0 BLOCKER, 0 HIGH |
| **7ª** | **FAIL**, 1 BLOCKER |
| **8ª** | **FAIL** |
| **9ª** | **FAIL**, 1 BLOCKER |
| **10ª** | **FAIL**, 2 BLOCKER — rodada comprometida por mim (worktree destruído no meio) |
| **11ª** | **FAIL**, 2 BLOCKER |
| **12ª** | **FAIL**, 2 BLOCKER |
| **13ª** | **FAIL**, 1 BLOCKER, 1 HIGH |

**Esta tabela ficou desatualizada em três rodadas** — foi o M1 da 13ª auditoria, e é a **terceira** instância da mesma classe: o H3 da 9ª puniu "item 15 ✅ com leitura de duas rodadas atrás", eu corrigi, e o defeito voltou com leitura de três rodadas atrás. O status ⛔ do item 15 seguiu correto o tempo todo, o que limitou o dano; o que subdeclarava era a **contagem de reprovações**.

A causa é estrutural, não descuido: a tabela é mantida à mão enquanto `docs/progress/audit_log.jsonl` já tem a mesma informação por artefato, com `head_sha` e veredito. Enquanto as duas fontes existirem em paralelo, elas vão divergir de novo. **Fica registrado como o próximo candidato a mecanizar** — a tabela deveria ser derivada do log, não digitada.

`docs/progress/audit_log.jsonl` confirma `"verdict": "FAIL"` nas três últimas linhas. Marcar ✅ deixava quem consultasse só a tabela concluir que o checkpoint passou — que é a classe de defeito do próprio P33, no item vizinho.

**O item 15 só volta a ser avaliável na rodada que este commit vai disparar.** Ele fecha o B1 e os quatro HIGH/MEDIUM de registro; o veredito dessa rodada é que decide, e será registrado aqui como o auditor emitir, não como previsto.

A ressalva anterior continua: sete pendências da quarta rodada seguem abertas (§6 P19–P25). A oitava, **P18**, tocava o próprio `spec_freeze` que os itens 10 e 11 demonstraram, e por isso foi corrigida em `ee7731d` antes deles.

### Estado do repositório neste registro

**Corrigido após o M2 da nona auditoria.** Este parágrafo dizia "**sem push**, sem tag" enquanto a §5 acima marcava os itens 9 a 13 como fechados por atestação — push feito, CI verde, branch protection aplicada e `spec-v1.0` publicada. As duas afirmações não podiam ser verdadeiras ao mesmo tempo, e o auditor registrou que não conseguia arbitrar de dentro do worktree.

**Arbitrado aqui: a §5 está certa e este parágrafo estava desatualizado.** Ele descrevia o estado anterior ao `finalize_phase0.sh` e nunca foi atualizado quando o script rodou. Estado corrente: `main` com push, `origin` configurado, branch protection aplicada com `enforce_admins`, tag `spec-v1.0` publicada — **tudo por atestação do operador**, terceira camada de verdade, exatamente como a §5 declara. Nenhuma auditoria verificou nada disso, e §6 P34 registra por que não pode.

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

`finalize_phase0.sh` **foi executado**, por atestação do operador (§5, itens 9 a 13). A frase anterior — "não foi executado" — era a segunda metade da contradição apontada pelo M2 da nona auditoria, e vinha do mesmo parágrafo congelado.

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

**Status: FECHADA** no commit que introduz `scripts/audit_report.py`. Cinco rodadas foram transcritas à mão antes disso, com três confusões de ID.

O diagnóstico do encaminhamento estava certo e foi confirmado: `SubagentStop` **nunca** dispara para o auditor, e não por causa do `agent_type`. O launcher invoca `claude --agent checkpoint-auditor`, que é sessão **de topo**; `SubagentStop` só dispara para subagente despachado pela ferramenta Agent dentro de uma sessão. O evento não ocorre por aquele caminho para nenhum valor de `agent_type`. A exigência introduzida em `c8c2be3` não era o obstáculo — era o gancho errado.

**Como a saída de uma sessão interativa é capturada.** Não por pipe. O Claude Code entra em modo não-interativo quando o stdout não é um TTY (`claude --help`: "via `-p`, or when stdout is not a TTY, e.g. piped or redirected output"). Canalizar a saída para capturá-la destruiria exatamente a interatividade que a auditoria existe para ter — e o que sairia seria fluxo de repaint de TUI, não documento. Captura por PTY (`script`) foi descartada pela mesma razão, mais a ausência da ferramenta no Git Bash do Windows.

O launcher passou a **pré-atribuir** o identificador da sessão (`--session-id`) e a ler o transcript daquela sessão depois que ela termina. A sessão continua 100% interativa. O identificador deixa de ser descoberto por heurística ("arquivo mais recente do diretório") — origem das três confusões de ID — e passa a ser imposto por quem lança. O transcript é localizado pelo **nome do arquivo** (`<session-id>.jsonl`), não pela regra de sanitização do diretório de projeto, que é convenção interna.

**Limite conhecido, com mitigação explícita.** O formato do transcript JSONL é interno do Claude Code, sem contrato público. Se mudar, a extração degrada. A mitigação é a falha ser **visível**: registro com `verdict: "sem_relatorio"` e o motivo, saída diferente de zero (código 3, distinto da falha da própria sessão), **e aviso impresso em bloco** dizendo que o veredito precisa ser transcrito à mão. Código de saída no fim de script longo passa despercebido; a mensagem não.

**Modo headless (`--headless`)** existe para CI, usando `-p`. Não é o padrão, e a decisão é deliberada: a auditoria é o momento em que o operador mais quer acompanhar e intervir — foi assim que uma sessão travada foi pega na quinta rodada e que uma reclassificação de ID foi decidida no meio de uma rodada. Headless troca isso por conveniência de captura, e a captura é o problema menor. O launcher **imprime o modo** em que está rodando, para não haver ambiguidade sobre por que a sessão não abriu.

**Destino resolvido.** `.gitignore:26` removido. `docs/progress/audit_log.jsonl` e `docs/progress/audit_*.md` passam a ser versionados: cada linha é a única prova de uma rodada que já aconteceu, não artefato reconstruível. Não exige `spec-change` — a spec só fala de `docs/progress/fase_<n>.md` (`07_IMPLEMENTATION_PHASES.md:229`) e nada diz sobre o registro de auditoria.

**Decisão sobre o hook `SubagentStop`.** Mantido em `.claude/settings.json`, **com comentário explícito** (`$comment_SubagentStop`) dizendo que não é o mecanismo de captura e que só vale se o auditor um dia for despachado como subagente. Removê-lo faria essa hipótese perder registro; mantê-lo mudo faria alguém supor, daqui a seis meses, que a auditoria está sendo capturada por ele. O mesmo aviso abre a docstring de `.claude/hooks/log_audit.py`. O hook passou a importar `last_agent_text`, `detect_verdict`, `main_worktree_root` e `persist` de `scripts/audit_report.py` em vez de duplicá-las, e preservou a guarda de identificação: sem `agent_type == "checkpoint-auditor"`, registra a ocorrência e nada mais.

**REABERTA na sétima auditoria: a captura não funcionou, e a decisão sobre o hook estava errada.**

A sétima rodada correu inteira e **nenhum `audit_*.md` foi gravado**. Verificado: não há uma única linha com `source: "launcher"` no `audit_log.jsonl`. Se `audit_report.py` tivesse executado e falhado, teria gravado linha com `capture_error` — logo ele **nunca executou**.

**A causa.** A sessão terminou por fechamento da janela do auditor, no X. Isso mata o processo do launcher sem executar `trap` nenhuma. A captura era código sequencial **depois** da sessão, e código depois da sessão só roda se o processo sobreviver a ela. O teste que a validou rodava `audit_report.py` isoladamente, nunca o launcher inteiro com uma sessão real no meio — a diferença entre os dois é exatamente onde o defeito morava.

**A correção inverte a prioridade.** `trap EXIT INT TERM` foi acrescentada e cobre saída normal, `/exit` e Ctrl+C — mas **não cobre o caminho que de fato ocorreu**, e que é o mais provável de repetir. O que resolve é o estado gravado **antes** da sessão: `--begin` grava `docs/progress/.last_audit_session` com `session_id`, fase, `head_sha` e modo, e `python scripts/audit_report.py --recover` captura depois, a qualquer momento em que o transcript ainda exista. Uma captura perdida deixa de ser transcrição manual e vira um comando.

O banner do launcher passou a avisar **antes** da sessão, em bloco destacado, que fechar a janela perde a captura automática, com o comando de recuperação ao lado. Aviso no lugar certo vale mais que mecanismo que não cobre o caso mais provável — e no fim de script longo o scroll come a mensagem.

O `.last_audit_session` entrou no `.gitignore`: arquivo de estado versionado sujaria a árvore e bloquearia a verificação de tree limpo do próprio launcher.

**O hook `SubagentStop` foi REMOVIDO de vez**, junto com `.claude/hooks/log_audit.py`. Mantê-lo foi decisão minha na primeira passagem, e este é o segundo argumento novo contra ela: além de inalcançável por desenho do launcher, ele **escreveu no `audit_log.jsonl` durante a sétima auditoria** — arquivo que o próprio P11 acabara de tornar versionado —, sujando a árvore e bloqueando a auditoria seguinte na verificação de tree limpo. É a mesma armadilha que a docstring dele já descrevia, reintroduzida em forma nova pela decisão de versionar o log. Mecanismo que só produz efeito colateral não é mecanismo.

Se um dia o `checkpoint-auditor` for despachado como **subagente** (pela ferramenta Agent, a partir de uma sessão já aberta), reintroduzir é trivial: um bloco `SubagentStop` com matcher `^checkpoint-auditor$` chamando um script que use `last_agent_text`, `detect_verdict` e `persist` de `scripts/audit_report.py`, que continuam existindo. O que **não** deve ser reintroduzido é a escrita no arquivo versionado sem condição.

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

**Reconfirmada na sexta auditoria (L6): segunda rodada.**

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

**Status.** Aberta. Mesmo defeito de **P13**; segunda auditoria consecutiva a levantá-lo. Mantém o item 7 da DoD (§5) em parcial. **Reconfirmada na sexta auditoria (M2): terceira rodada.**

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

**Status.** Aberta. Mesmo defeito de **P14**. A auditoria reforça o ponto que o P14 já fazia: registrar a lacuna no `fase_0.md` não a torna visível para quem abre o verificador — a declaração precisa estar no arquivo. **Reconfirmada na sexta auditoria (M3): terceira rodada.**

### P21 — [L1, quarta auditoria] `tools/README.md` e `README_FIRST.md` desatualizados — reconfirma P15

```text
[L1] tools/README.md e README_FIRST.md ainda instruem que os seis verificadores não existem — pendência P15, reconfirmada
Arquivo: tools/README.md:3; README_FIRST.md:10
Requisito violado: categoria nomeada por L3/P10 em fase_0.md
Evidência: os seis existem e saem 0 (medido nesta sessão). tools/README.md:1 ainda
se intitula "verificadores a implementar".
```

**Status.** Aberta. Mesmo defeito de **P15**. **Reconfirmada na sexta auditoria (L1): terceira rodada.**

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

**Reconfirmada na sexta auditoria (L2): segunda rodada.**

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

**Reconfirmada na sexta auditoria (L3): quarta rodada, com o quinto modo — e é o mais grave.**

O smoke test canônico prescrito em `docs/process/PHASE_0_CHECKLIST.md:71-73`, que valida o **item 4 da DoD**, é bloqueado pelo próprio hook que ele testa: `DENIED_ANYWHERE` casa `rm -rf` dentro do payload JSON entre aspas. Reproduzido, `rc=2`, mensagem "comando de escrita".

O auditor está estruturalmente impedido de executar o teste canônico do item 4 — a mesma classe do **H4** da primeira auditoria, que foi classificado HIGH exatamente por impedir o auditor de rodar a prova central. A diferença é que o H4 foi tratado como HIGH e fechado em uma rodada, enquanto este sobreviveu quatro rodadas por estar numa família tratada como LOW.

Os cinco modos conhecidos: `|` entre aspas (P8); `merge-base` casando como `merge` e `2>&1` como redirecionamento (P16); `->` entre aspas como redirecionamento (P23); e agora o payload JSON contendo `rm -rf`. Todos são a mesma causa — casamento textual sem tokenização — e nenhum é corrigível por acrescentar exceção sem reintroduzir o problema em outra forma.

**Status: FECHADA em `60a7fa7`.** Quatro rodadas de correção caso a caso não convergiram, exatamente como a linhagem previa. A causa foi trocada, não o sintoma: `shlex` tokeniza respeitando aspas, `punctuation_chars=True` transforma operador de shell em token próprio, e a decisão passou a olhar a **palavra de comando** de cada segmento. Conteúdo de argumento nunca mais é interpretado como comando.

> **Correção de referência, e o que ela ensina.** Este parágrafo citava `7a67305`. Aquele SHA existia no branch `fase-0-manutencao-p11-p23`, criado sobre a `main` anterior; o trabalho foi recriado sobre `edd9527` e o commit do P23 passou a ser `60a7fa7`. Ao apagar o branch antigo, `7a67305` deixou de pertencer a qualquer ref e virou referência morta dentro de um documento versionado.
>
> **Referência a SHA dentro de documento versionado é frágil sob rebase**, e a fragilidade é assimétrica: o documento é reescrito por quem edita, mas o SHA é reescrito por uma operação que ninguém associa a editar documento. A correção foi feita em commit próprio, e não emendando o commit de registro, justamente porque emendar recriaria os commits seguintes — incluindo o `60a7fa7` que este texto passa a citar. A correção invalidaria a própria referência que ela cria.
>
> **Daqui em diante, considerar citar por assunto do commit** (`fase-0 [P23]: readonly_bash.py decide por tokens`) em vez de hash. O assunto sobrevive a rebase, a cherry-pick e a recriação de branch; o hash não sobrevive a nenhum dos três.

Os cinco modos passam. O (e) foi verificado ponta a ponta: o smoke test de `PHASE_0_CHECKLIST.md:71-73` agora executa, e o hook segue devolvendo `exit=2` para `rm -rf` real — o auditor deixou de estar impedido de rodar o teste canônico do item que audita.

**A direção inversa não afrouxou, e três buracos fecharam.** A allowlist passou a ser positiva. Redirecionamento de saída só passa para `/dev/null`. A tokenização permitiu bloquear o que o regex não via: `env CMD` como trampolim de execução, `git branch -D`, e `find -exec/-delete`. Crase é negada; entrada que não tokeniza é negada (falha fechada).

**REABERTA na oitava auditoria, e a correção foi REVERTIDA.** O fechamento acima descreve o que foi feito e por quê; o que segue é por que não se sustentou.

**Cinco instâncias em três rodadas.** A sétima auditoria somou duas vias que a tokenização não cobria; a oitava somou três — `\r`, `$(...)` entre aspas duplas, e crase entre aspas duplas. A das aspas é **estrutural**, não descuido: `_blank_quoted` apaga o conteúdo citado **antes** de procurar crase, enquanto o bash **expande** substituição de comando e crase dentro de aspas duplas. A premissa da função está errada, não a sua implementação.

**O argumento que encerra o assunto**, e que vale além deste hook: enquanto *"o bash executaria isto?"* for respondida por um parser reimplementado em ~520 linhas, **a completude não é demonstrável — só refutável**, uma via por rodada. Nenhum conjunto de probes prova ausência de via; cada rodada só consegue exibir mais uma. O auditor avisou que passaria a **gerar construções** em vez de rodar os probes do repositório, e está certo em fazer isso: probe escrito por quem implementou herda os pontos cegos de quem implementou.

**A reversão, e a premissa que ela corrigiu.** O hook voltou à versão em casamento textual. A justificativa era "falso-positiva, irritante e fechada, em vez de silenciosa e aberta" — e a **medição derruba a segunda metade**: a versão antiga erra nas duas direções. Bloqueia 9 leituras legítimas **e** deixa 10 escritas passarem.

O que a versão antiga fecha é a família de **redirecionamento** — `>&`, `>|`, `<>` — porque `>\s*\S` casa todas por acidente, sem saber o que são. O que ela abre é a família de **escrita por flag** — `pytest --junitxml`, `ruff --output-file`, `mypy --junit-xml`, `eslint -o`, `tsc --outFile`, `find -fprint0`, `find -delete`, `git branch -D` — porque casamento textual não olha flag nenhuma.

A escolha real, então, não foi entre "fechada" e "aberta". Foi entre **duas superfícies abertas diferentes**, e a decisão de reverter é defensável por outro motivo: a superfície da versão antiga é **conhecida e estável**, enquanto a da versão tokenizada crescia a cada rodada sem previsão de convergir.

**O harness afirma as quatro combinações**, não as duas confortáveis: 5 leituras liberadas, 24 escritas bloqueadas, **9 falsos bloqueios conhecidos** e **10 buracos conhecidos**. As duas últimas listas são afirmadas como defeito: se o comportamento mudar, o harness reprova e manda migrar a linha para a lista certa. Defeito documentado que sai do harness vira defeito esquecido — e harness que só afirma o que acerta é exatamente o que o H2 puniu.

**O que fica para quem for refazer isto.** O caminho que não foi tentado é não reimplementar o parser: delegar a decisão ao próprio bash (`bash -n`, ou expansão controlada), ou reduzir a superfície a ponto de o parser ser desnecessário — por exemplo, não aceitar pipeline nem substituição de comando, e exigir um comando por chamada. Menos capacidade, mas capacidade **demonstrável**.

**O harness passou a cobrir as duas direções** — 7 probes de leitura legítima e 13 de escrita deliberada. Esta é a lição da linhagem, e vale além deste arquivo: o harness cobria "nega escrita" e nunca "libera leitura", e por isso quatro rodadas seguidas produziram falso bloqueio **sem nenhum teste reprovar**. Um guarda testado só contra o que deve bloquear converge para bloquear tudo. Um probe adicional compara a fonte versionada com a cópia instalada em `~/.claude/hooks/`, que é a que efetivamente roda: divergência silenciosa entre as duas é o pior caso. Ausente a cópia instalada (CI), avisa e segue.

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

**Status.** Aberta. Amplia **P9** para `user-scope/hooks/`. **Reconfirmada na sexta auditoria (L4): terceira rodada.**

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

**Status.** Aberta, **deliberadamente adiada para a Fase 1**. **Reconfirmada na sexta auditoria (L5): segunda rodada.** Mexer no `invariants.yml` na véspera de executar os PRs descartáveis que testam esse mesmo workflow adiciona risco sem necessidade: se algo quebrar, quebra exatamente na demonstração dos itens 10 e 11. A decisão de adiar é do operador e está registrada aqui para não parecer esquecimento.

---

### P26 — [M1, quinta auditoria] `CLAUDE.md` fora do conjunto `CODE` do `spec_freeze`

Houve uma **quinta auditoria**. Dela chegou até este registro exatamente um achado, o M1: `CLAUDE.md` deveria entrar no conjunto `CODE` do `spec_freeze`. O texto verbatim do finding **não foi transmitido**, e o veredito e os demais achados da rodada também não — o que fica declarado aqui em vez de suposto, e é consequência direta de **P11**, que mantém a captura de relatório inerte.

**Status: FECHADA em `32bdc05`.**

`CLAUDE.md` é a instrução permanente carregada em toda sessão: define autoridade normativa, os quatro invariantes arquiteturais e as restrições inegociáveis. Alterar a especificação e, no mesmo PR, o documento que diz como obedecê-la é exatamente o acoplamento que a regra existe para impedir.

**O que o achado expôs, além do próprio caminho.** Ao justificar a inclusão, ficou claro que o critério do conjunto `CODE` estava mal formulado. O comentário do workflow dizia "ser executável", e isso nunca foi literalmente verdade: desde `012ce3a` o conjunto já continha `.claude/agents/scenario-designer.md`, `.claude/agents/spec-guardian.md` e `user-scope/agents/checkpoint-auditor.md` — três markdowns que não executam nada e definem comportamento. O critério real sempre foi **ser mecanismo que aplica a spec**, e a formulação foi corrigida no workflow e na tabela do §6 P12.

**Erro de classificação, corrigido.** Este achado foi registrado inicialmente como decisão do operador, porque chegou sem identificação de rodada e o M1 conhecido até então era o da quarta auditoria, sobre `user-scope/`. É a terceira vez nesta fase que IDs se confundem entre rodadas — as duas anteriores estão em §0 —, e todas as três têm a mesma raiz: **P11**. Enquanto o relatório da auditoria não for persistido, cada rodada chega por transcrição manual, sem rodada nem veredito anexados.

---

### P27 — [M1, sexta auditoria] `.gitignore` fora do conjunto `CODE` — quarta instância da linhagem

```text
[M1] .gitignore está fora do conjunto CODE do spec_freeze — quarta instância da
linhagem P12/P18/P26
Arquivo: .github/workflows/invariants.yml:99-102
Requisito violado: CLAUDE.md §"A especificação é imutável durante a implementação"
("Alterar spec e código no mesmo PR é proibido"); docs/process/WORKFLOW.md:25;
05_SECURITY_REQUIREMENTS.md §6 (".env.example versionado; .env no .gitignore")
Evidência: medido. git ls-files retorna 39 arquivos versionados; git ls-files --
range-core/ domains/ contracts/ tools/ scripts/ .claude/ .github/ user-scope/
CLAUDE.md ':(glob)*.sh' retorna 23, e .gitignore não está entre eles. Os arquivos
versionados fora do conjunto CODE e fora de docs/spec/ são seis: .gitignore,
CHANGELOG_V3.md, README_FIRST.md, docs/process/PHASE_0_CHECKLIST.md,
docs/process/WORKFLOW.md, docs/progress/fase_0.md. Cinco são documentação
descritiva, e a exclusão deles está justificada em invariants.yml:71-72 e na
tabela de fase_0.md §6 P12. O .gitignore não é documentação e nunca foi
classificado em nenhuma das três rodadas da linhagem — não aparece na tabela do
P12, nem no P18, nem no P26.
Por que é MEDIUM: pelo critério vigente — "ser mecanismo que aplica a spec"
(invariants.yml:65) — o .gitignore é mecanismo, não descrição: é ele que executa
05_SECURITY_REQUIREMENTS.md §6 e §Nunca commitar do CLAUDE.md, e é o objeto
exclusivo do item 6 da DoD (ground_truth.yaml e GM_NOTES.md não podem estar
nele). Consequência concreta: um PR que altere
docs/spec/05_SECURITY_REQUIREMENTS.md e, no mesmo commit, remova .env do
.gitignore ou acrescente ground_truth.yaml a ele produz CODE=0 e passa no gate.
Mesma severidade das três instâncias anteriores, pela mesma razão estrutural.
```

**Status: FECHADA em `b2fb8c2`.** Conjunto `CODE` de 23 para 24 arquivos.

**Fecha a linhagem.** Com `.gitignore` incluído, tudo que resta versionado fora do conjunto `CODE` e fora de `docs/spec/` é documentação descritiva. A varredura pedida no §8 item 1, sob o critério refinado, está feita.

**O que a linhagem inteira ensina.** Quatro instâncias, quatro rodadas — P12 (`tools/`, `scripts/`, `.claude/`, `.github/`), P18 (`user-scope/`), P26 (`CLAUDE.md`), P27 (`.gitignore`). As três primeiras foram encontradas sob a formulação "ser executável", uma por rodada, cada uma parecendo a última. A quarta só apareceu depois de o critério ser reformulado para "ser mecanismo que aplica a spec" e de alguém varrer o conjunto **inteiro** contra ele, em vez de julgar caminho por caminho. Enumerar exceções uma a uma converge devagar; conferir o conjunto todo contra o critério converge de uma vez.

Uma discrepância menor de medição: o finding cita 39 arquivos versionados e a medição local devolve 40 — diferença de um commit de registro entre a auditoria e a correção. A lista dos seis arquivos fora do conjunto bate exatamente, que é a afirmação substantiva.

---

### P28 a P31 — [revisão de referências cruzadas, spec-change `ator-real-e-finalidade-comercial`] Quatro referências por número de seção apontam para a seção errada

**Status: ABERTAS. Não corrigidas de propósito.**

Encontradas ao varrer o repositório atrás de referências cruzadas por número de seção, antes de inserir a §8 nova no `03_EXERCISE_DESIGN.md`. A varredura era necessária porque inserir seção no meio de um documento desloca tudo depois dela — e ao conferir uma a uma, quatro já estavam erradas **antes** da inserção.

Nenhuma foi agravada pela mudança. Três das quatro apontam para `03_EXERCISE_DESIGN.md`, e nenhuma delas para a §8 — que era a única seção deslocada. É por isso que o spec-change quebrou exatamente uma referência (`07_IMPLEMENTATION_PHASES.md:216`, corrigida no mesmo PR) e não cinco.

Ficam fora daquele PR por decisão explícita do operador: são pré-existentes e misturá-las inflaria o diff de um `spec-change:`, que precisa permanecer auditável linha a linha. Viram PR próprio.

| ID | Local | Diz | Deveria dizer |
|---|---|---|---|
| **P28** | `01_ARCHITECTURE.md:207` | três papéis, `03_EXERCISE_DESIGN.md` §6 | **§7** — §6 é *Personas*; os três papéis de facilitação são §7 |
| **P29** | `02_DOMAIN_ACADEMUS.md:50` | ações `declare_*`, `03_EXERCISE_DESIGN.md` §3.1 | **§3.4** — §3.1 é *Predicados de verificação*; a tabela de ações de declaração é §3.4 |
| **P30** | `02_DOMAIN_ACADEMUS.md:126` | dashboards por persona, `03_EXERCISE_DESIGN.md` §5 | **§6** — §5 é *Calibração (Linha B)*; personas é §6 |
| **P31** | `09_EVENT_MODEL.md:69` | predicado próprio, `03_EXERCISE_DESIGN.md` §3.2 | **§3.1** — §3.1 define os predicados; §3.2 trata da leitura do delta |

**O que o conjunto sugere.** As quatro são do mesmo tipo: referência escrita por memória do conteúdo, não por conferência do número. P29 e P31 chegam a apontar para a subseção vizinha da correta. Nenhum verificador cobre isso hoje — `tools/` valida fronteira de import, literais de contrato, envelope de evento e dado sintético, e nenhum valida se `<doc> §<n>` existe e trata do que a frase afirma. É a mesma classe de falha silenciosa do `event_type` inexistente: não quebra nada, só manda o leitor para o lugar errado.

Uma verificação possível — resolver cada `NN_DOC.md §X.Y` contra os cabeçalhos do arquivo alvo e falhar quando a seção não existe — pegaria zero das quatro, porque todas apontam para seções que existem. Pegar essas exige comparar a frase com o conteúdo da seção, o que não é mecanizável barato. Registrado para não se perder, sem propor gate.

---

### P33 — [M4, oitava auditoria] O registro guardava evidência falsa para o item 5 da DoD

```text
[M4] O registro guarda evidencia falsa para o item 5 da DoD
Arquivo: docs/progress/fase_0.md:295
Evidencia: o registro afirma que scenario_bash.py distingue git log --oneline
(exit=2) de range-cli scenario validate (exit=0). Medido nesta rodada:
range-cli scenario validate -> exit=2; so range-cli scenario validate
scenarios/academus/pack -> exit=0.
```

**Status: FECHADA.** Medido de novo e confirmado: `range-cli scenario validate` sem argumento devolve `exit=2`; só com o caminho do pack devolve `exit=0`. A evidência do item 5 foi corrigida para o que foi medido, e não apenas registrada como pendência.

O item 5 **continua ✅**: as duas metades do hook seguem exercitadas, e o `exit=2` para a forma sem argumento é comportamento correto do hook, não defeito. O que estava errado era o texto da evidência.

Vale registrar por que sobreviveu duas rodadas: o **L2 da sétima auditoria** apontou isto, e o registro o marcou explicitamente como "a apurar" — o que é honesto, mas "a apurar" não apura. Uma afirmação errada marcada como não verificada continua sendo lida como evidência por quem passa os olhos na tabela do DoD.

### P34 — [constatação estrutural, oitava auditoria] Os itens 9 a 13 da DoD não são verificáveis por auditoria

**Status: ABERTA — decisão pendente do operador.**

Os itens 9 a 13 (push de `main` com CI verde, os dois PRs descartáveis do `spec_freeze`, branch protection, tag `spec-v1.0`) **não podem ser verificados por nenhum auditor de checkpoint com as ferramentas atuais**. Duas razões, ambas estruturais:

1. **`gh` não está na allowlist do auditor.** Sem ele não há como consultar estado de PR, de check run ou de branch protection.
2. **Execução de CI não é observável de dentro de um worktree.** O auditor lê um checkout fixado num commit; o que aconteceu no GitHub Actions não deixa rastro nesse checkout.

Por isso os cinco foram fechados por **atestação do operador**, e estão marcados como tal em §5 — não como verificados. É a terceira camada das quatro (`declaração`), não a segunda (`evidência observável`). Registrar atestação como verificação seria violar diretamente "Quatro camadas de verdade" do `CLAUDE.md`.

**Decisão pendente: liberar `gh` de leitura na allowlist do auditor.** Tornaria os itens 9 a 12 verificáveis por evidência em vez de declaração. Custo e risco a pesar antes de decidir:

- `gh` fala com a rede, e acesso de rede está hoje inteiramente negado ao auditor (`DENIED_ANYWHERE`);
- **não existe forma de expressar "só GET" numa regra de prefixo**: `gh api` cobre POST, DELETE e mutação GraphQL na mesma sintaxe. Uma allowlist de `gh` teria que ser por subcomando explícito (`gh pr view`, `gh run list`, `gh api` **nunca**), e cairia no mesmo problema de completude que derrubou o P23 — desta vez sobre a superfície de subcomandos do `gh`;
- o auditor passaria a depender de credencial do operador, o que muda o que uma auditoria comprometida pode fazer.

Enquanto a decisão não for tomada, **atestação é o mecanismo, e o registro diz isso em voz alta** em vez de simular verificação.

### P32 — [B1 BLOCKER, H1, H2, sétima auditoria] A reescrita por tokens abriu escrita deliberada

```text
[B1] readonly_bash.py libera tres caminhos de escrita que a versao anterior
bloqueava: `>&` com palavra nao-numerica (classificado como duplicacao de
descritor e liberado sem validar o alvo), `sort -o FILE`, `find -fprint0 FILE`.
Os alvos aceitam travessia ../../, entao a escrita alcanca o worktree
principal — incluindo CLAUDE.md e os verificadores de tools/.
[H1] python .claude/hooks/log_audit.py esta na allowlist e grava
incondicionalmente no worktree principal via persist().
[H2] Os 13 probes de escrita deliberada cobrem redirecionamento so na forma `>`.
O harness declara provar que a protecao nao afrouxou, passa verde, e tres
afrouxamentos estao presentes.
```

**Status: PARCIALMENTE REABERTA pela reversão do P23, e re-fechada em 2026-08-14 por outro caminho. Corrigido após o H1 da nona auditoria.**

Esta entrada dizia **"Status: FECHADA"** e descrevia um desenho — allowlist de flags com default-deny, `git tag` com `max_positional=0`, 32 probes — que **a reversão do P23 desfez**. O código voltou ao casamento textual e nada disso existia mais no arquivo, enquanto este texto seguia afirmando que sim. É a categoria que o próprio registro batizou em P10: **documentação que sobrevive à correção e orienta a próxima pessoa a desfazê-la.** A descrição abaixo fica preservada como o que o desenho tokenizado fazia, não como o que o hook faz hoje.

**O que de fato vale hoje**, medido neste commit:

| Afirmação do texto original | Estado real após a reversão | Estado após 2026-08-14 |
|---|---|---|
| hooks allowlistados por **nome explícito** | falso — voltara ao curinga `.claude/hooks/[A-Za-z0-9_.-]+\.py` | **verdadeiro** — nomes explícitos, `log_audit.py` fora |
| default-deny de flags | falso — não existe | continua não existindo; substituído por **contenção** (`..` negado) |
| `git tag` bloqueado com operando | falso — `git tag` está bloqueado até para listar (falso bloqueio afirmado) | idem, afirmado no harness |
| 32 probes | falso — 29 probes de hook + 19 afirmações | 32 escritas bloqueadas, 2 buracos, 11 falsos bloqueios |

**Por que o curinga foi fechado no código em vez de o registro ser rebaixado.** O H1 da sétima auditoria já mandara removê-lo, e o argumento continua inteiro: allowlistar um script é allowlistar o que ele faz, e o script está **no commit sob auditoria** — o mesmo argumento que mantém o `checkpoint-auditor` fora do repositório. Rebaixar o texto para "não fechado" deixaria o buraco aberto com a documentação correta; fechá-lo no código torna o texto verdadeiro. Fechado por nome explícito.

**O B1 da nona auditoria foi fechado neste mesmo commit, por contenção.** A medição mostrou que 8 das 10 formas declaradas escreviam fora do worktree de auditoria — provado por execução: `find . -fprint0 ../../tools/codegen.py` sobrescreveu arquivo no worktree principal, e `git branch -D` apagou ramo no ref store compartilhado. Foram fechadas negando `..` em qualquer posição e negando `git branch` com flag de deleção. **Duas regras, não oito**: o invariante não é a flag, é o alvo. A lista de buracos declarados caiu de 10 para 2, ambos contidos.

O texto abaixo é o registro do desenho tokenizado, preservado por valor histórico.

**O diagnóstico.** Tokenizar foi acerto para **parsear**: resolveu o `rm -rf` dentro de JSON entre aspas, que quatro rodadas de regex não resolveram. O erro foi usar a tokenização para **classificar** operadores com mais precisão, em vez de **identificá-los** com mais confiabilidade e bloquear todos. A versão em regex bloqueava `>&` por acidente, sem saber o que era: falso-positiva, irritante, **fechada**. A versão nova sabia que `>&` era duplicação de descritor, deu a ele um caminho próprio e pulou o alvo sem validar: falso-negativa. **Precisão de classificação virou justificativa para liberar.**

Agrava que o commit do P23 afirmava que "a tokenização permitiu bloquear o que o regex não via" e listava três buracos fechados. Estava certo sobre aqueles três e cego para os que abria no mesmo movimento.

**A superfície era maior que os três casos.** Sondagem posterior achou mais oito, todos escrita através de comandos que a allowlist já permitia, nenhum precisando de redirecionamento: `sort --output=`, `pytest --junitxml`, `python -m pytest --junitxml`, `ruff --output-file`, `mypy --junit-xml`, `eslint -o`, `tsc --outFile`, e `uniq entrada saida` — este último **escrita posicional, sem flag nenhuma**. O `tsc` é o mais didático: a checagem antiga confirmava a presença de `--noEmit` e ignorava o resto da linha. Classificar em vez de identificar, outra vez, em outro lugar.

**A correção, em dois princípios, os dois default-deny.**

1. **Todo token de redirecionamento bloqueia**, sem distinguir `>`, `>>`, `>&`, `&>`, `&>>`, `>|`, `<`, `<<`, `<&`, `<>`. Exceção apenas para duas sequências **exatas de token**: `2>/dev/null` e `2>&1`. Forma desconhecida é bloqueada, nunca liberada. `>/dev/null` sem fd ficou de fora de propósito — acrescentar exceção "óbvia" é como a família P8→P16→P23 nasceu. Token de pontuação que não decompõe em operador conhecido bloqueia **explicitamente**, e não por acidente de virar palavra de comando desconhecida: acidente não é garantia, e foi assim que `>&` passou.
2. **Allowlist de flags por comando**, com default-deny dentro do comando permitido. Cobre `--flag=valor` (partido no `=`), bundles de letra curta (`-no` não esconde mais o `-o`), flags que consomem valor, e limite de posicionais onde o comando escreve por posição. `find` e `uniq` saíram da allowlist: superfície grande demais para o valor: `git ls-files` e `rg` cobrem `find`, `sort -u` cobre `uniq`.

**Custo medido.** 40 comandos reais de auditoria — `git log --oneline -20`, `grep -n -A3 -B3`, `rg --type py`, `pytest -x --tb=short`, `mypy --strict`, `git ls-files | sort -u | head -20` — todos passam. O default-deny não engessou o auditor.

**H1 e o limite que fica declarado.** Allowlistar um script é allowlistar o que ele faz, e o script está **no commit sob auditoria**: o curinga `.claude/hooks/*.py` deixava o commit auditado definir o comportamento de um comando que o auditor está pré-autorizado a rodar — o mesmo argumento que mantém o `checkpoint-auditor` fora do repositório. Os hooks passaram a ser allowlistados por **nome explícito**, e só os guardas, que leem stdin e imprimem. `log_audit.py` saiu (e depois foi removido de vez, ver P11).

A classe **não** foi eliminada, e vale declarar em vez de fingir: `pytest` roda testes do commit auditado, `tools/check_*.py` é código do commit auditado. A propriedade é inerente à auditoria. **A linha que dá para segurar é: script cujo propósito é verificar, sim; script que escreve, não.**

**M2 — o registro do próprio P11 estava errado, e foi corrigido nesta rodada.** `detect_verdict` contava presença de "PASS"/"FAIL" no texto **inteiro** e, com os dois presentes, devolvia `FAIL`. O formato obrigatório do auditor tem `## VEREDITO: PASS | FAIL` como linha literal — logo **todo** relatório contém as duas palavras, e **todo PASS seria arquivado como FAIL**. O mecanismo que acabara de eliminar a transcrição manual registraria a primeira aprovação capturada automaticamente como reprovação, e corrigir depois significaria ter esse primeiro PASS gravado como reprovação no log versionado.

Não é correção caso a caso: é o registro do próprio P11. O veredito passou a sair da **linha de veredito** especificamente — início de linha, com ou sem `#` e sem ênfase, prosa no meio de parágrafo não casa. Sem linha, linha ambígua (o template não preenchido) ou linhas discordantes gravam `indeterminado` **com o motivo** no campo `verdict_reason`, nunca um palpite. Índice que chuta é pior que índice ausente; o relatório continua sendo a fonte autoritativa. Sete casos cobertos, incluindo o que motivou o achado: PASS que cita "FAIL" no corpo agora registra PASS.

**L3 — leitura pura de git que estava fora.** `cat-file`, `merge-base`, `for-each-ref` e `tag` entraram no conjunto de leitura. O `merge-base` é o que o auditor usa para comparar contra `main`: bloqueá-lo degradava a capacidade de auditar sem ganho de segurança, que é o argumento que fez o **H4** ser HIGH na primeira rodada.

`git tag` recebeu tratamento próprio, porque sem operando **lista** e com operando **cria**: `max_positional=0` resolve pelo lado seguro, e `-d`/`--delete` nem chegam lá — caem no default-deny de flags. Filtrar por padrão se faz com `git tag | grep`. Probes nas duas direções: os quatro subcomandos passam, `git tag v9.9.9` e `git tag -d` bloqueiam.

**Pendência aberta a verificar: L2.** O relatório da sétima auditoria afirma que `fase_0.md:295` registra, como evidência do DoD item 5, que `scenario_bash.py` devolve `exit=0` para `range-cli scenario validate`, e que a medição do auditor divergiu. **Não foi verificado** nesta rodada — fica registrado como pendência a apurar, não como fechado.

**Observação para quando o L5 for tratado.** `main()` devolver 0 quando o stdin não parseia como JSON é o mesmo *fail-open* já registrado como **O1** para o `check_architecture.py`. Guardrail que não consegue interpretar a entrada deve **negar**, não permitir. Os dois devem ser corrigidos juntos, em commit próprio.

**H2 e a lição sobre o harness.** Os 13 probes cobriam redirecionamento só na forma `>` — a forma que quem escreveu se lembrou. Probe que só cobre a forma lembrada não prova ausência das formas esquecidas, e o harness verde foi usado como evidência do que ele não media. São 32 probes agora, e a correção veio em **commit posterior ao dos probes**, de propósito: o harness foi commitado **vermelho**, reprovando contra o código da época, porque um probe que passa no momento em que é escrito não prova nada. Um commit em que o teste prova o buraco antes de fechá-lo é o oposto do que o H2 puniu.

---

### P35 — [decisão do operador, 2026-08-14] Ordem de merge, e o precedente de mergear com auditoria FAIL

**Status: DECIDIDA. Registro do precedente, não exceção casual.**

**A constatação que reordenou tudo.** A DoD julga `main`. Existe um `spec-change` pronto que reformula o item 4 da DoD — ele deixa de exigir uma propriedade universal sobre todos os comandos de shell possíveis e passa a exigir cinco condições verificáveis, com a superfície aberta declarada. Se esse PR entrasse primeiro, a auditoria desta manutenção julgaria contra uma DoD que `main` ainda não tem o código para satisfazer, e **o item 4 continuaria inaferível por ordem, não por mérito**. Depois de nove rodadas travadas por uma definição insatisfazível, travar mais uma por sequência de merge seria repetir o mesmo erro noutra forma.

**Ordem decidida:**

| | Passo | Contra qual DoD |
|---|---|---|
| a | fechar B1, H1, H2, H3 e M1–M4 nesta branch | — |
| b | auditoria desta branch | **DoD antiga** — o item 4 falha por definição insatisfazível, e isso é esperado |
| c | **mergear esta branch mesmo assim**, registrando o motivo | — |
| d | mergear o `spec-change` do item 4 | — |
| e | auditoria de confirmação contra `main` | **DoD nova, com o código presente** |

**O passo (c) é o incomum, e fica registrado com estas palavras: é a primeira vez neste projeto que algo entra em `main` com auditoria FAIL.**

**A justificativa é que o finding é sobre um requisito que já foi reconhecido como não obtenível e cuja correção está no PR seguinte.** O item 4 antigo — *"o hook bloqueia escrita deliberada"* — é uma afirmação universal sobre todos os comandos de shell possíveis, demonstrável apenas com um parser de shell completo. Nove rodadas o refutaram uma via por vez sem nunca poder confirmá-lo. Reprovar por ele em (b) não mede a qualidade desta manutenção; mede a definição, e a definição já foi julgada e substituída.

**O que isto não é.** Não é permissão para mergear com FAIL quando o finding for legítimo. As quatro condições que sustentam esta decisão, e que precisam valer **juntas** em qualquer repetição futura:

1. o requisito violado já foi **formalmente reconhecido como não obtenível**, com o registro do reconhecimento anterior ao merge;
2. a correção do requisito **já está escrita e em revisão**, não é intenção — é o PR do passo (d);
3. o FAIL é **exclusivamente** desse item; qualquer BLOCKER ou HIGH de outra natureza reprova como sempre;
4. o passo (e) existe e é obrigatório — a manutenção não fica sem auditoria válida, fica com a auditoria adiada para quando puder ser justa.

Sem as quatro juntas, o precedente não se aplica. Este parágrafo existe para que a próxima invocação desta decisão tenha de se comparar a ela, em vez de citá-la de memória.

**A condição 3 já mordeu, e é a prova de que não é decorativa.** A nona auditoria trouxe o **B1 BLOCKER** — o hook liberando escrita que alcança o worktree principal. Não é a definição insatisfazível: é defeito concreto e corrigível, e pela condição 3 ele **impediria** o merge. Por isso foi fechado neste commit, e não declarado. O precedente não foi usado para contornar o B1; foi o B1 que teve de morrer antes de o precedente poder valer.

**A ressalva do veredito.** Por `docs/process/WORKFLOW.md` §Ciclo por fase o critério de bloqueio é BLOCKER e HIGH, e por `checkpoint-auditor.md` §Regras apenas BLOCKER força FAIL. **Item de DoD falhando não determina o veredito por si.** Com B1 e os três HIGH fechados, o passo (b) pode sair **PASS com o item 4 marcado como falha declarada** em vez de FAIL. O registro do passo (c) deve descrever **o veredito que a auditoria de fato emitir**, não o previsto aqui. Se sair PASS, este precedente não chega a ser exercido — e continua registrado, porque a decisão de mergear apesar do finding foi tomada de qualquer modo.

**O teste do P11 no passo (b).** Esta branch traz `scripts/audit_report.py` e a captura pelo launcher, mas as três últimas linhas de `audit_log.jsonl` trazem todas `"recovered": true` — nenhuma captura automática funcionou até aqui. Se o relatório da próxima rodada sobreviver à sessão **sem `--recover`**, o P11 fecha de fato, pela primeira vez na fase. **O resultado fica registrado aqui explicitamente, seja qual for**: se sobreviver, P11 fecha com o commit que o provou; se não sobreviver, P11 continua aberta com o modo de falha descrito, e não com "tentou-se de novo".

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

1. **Sétima auditoria de checkpoint**, via `bash scripts/start_checkpoint_audit.sh 0`. A sexta fechou a linhagem do conjunto `CODE` (§6 P27), mas a correção que a fechou — `b2fb8c2` — não foi auditada, e ela toca o gate que os passos 3 e 4 vão exercitar.
2. Decidir o destino das pendências abertas (§6). São **dezenove**: quatro declaradas por mim durante a implementação (P1–P4) e quinze vindas das auditorias (P8, P9, P11, P13–P17, P19–P25). P5, P6, P7, P10, P12, P18, P26 e P27 estão fechadas.
   - **P23** merece decisão antes das demais: seu quinto modo impede o auditor de executar o smoke test canônico do item 4 da DoD. É a mesma classe do H4, que foi HIGH, e sobreviveu quatro rodadas por estar numa família tratada como LOW.
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
