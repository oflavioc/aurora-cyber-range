# Mapa de integração — Estrutura Agêntica no aurora

> Branch `chore/estrutura-agentica`, 2026-08-25. Kit de origem:
> `C:\Projetos\estrutura-agentica-kit` (destilado do QuickScan phase5).
> Princípio da integração: **onde o aurora já tem mecanismo equivalente ou
> melhor, o mecanismo existente prevalece** — nada foi sobrescrito.

## 0. Decisões do proprietário — 2026-08-25

Tomadas em sessão, no chat, após apresentação das colisões:

1. **A Estrutura Agêntica é a estrutura permanente de desenvolvimento do
   projeto inteiro daqui em diante** — não um complemento pontual. Todo
   trabalho da Fase 8 em diante nasce dentro dela.
2. **A Fase 7 fecha pelo processo atual** (peças 4 e 5, auditoria de
   checkpoint e P7-6 sob as regras que regeram as peças 1–3) — a auditoria
   não muda de chão no meio da fase. A instanciação corre em paralelo, nesta
   branch própria.
3. **Trunk + âncoras prevalece sobre o gitflow do kit** — confirmada a
   adaptação da R14 que documenta o fluxo real (fase = branch = PR rebase em
   `main`, âncora obrigatória, squash proibido). O predicado
   `check_audit_base` permanece válido sem mudança.
4. **Primeira instalação: Ondas 0–1.** A Onda 2 (8 papéis + SDD governando
   também o roadmap) entra **na abertura da Fase 8** — o desenho da
   reconciliação fase↔demanda é a primeira tarefa dessa abertura. A Onda 3
   segue aguardando a dor (primeira regressão que red-first teria evitado).

## 1. Adotado limpo (instalado nesta branch — Ondas 0/1 do BOOTSTRAP)

| Peça | Onde | Nota |
|---|---|---|
| Regras R2, R3, R10, R8 (evidência, TDD estrutural, gates, pins) | `.claude/rules/` | Como no kit — não colidem com nada existente |
| Regras R5, R6, R7, R9, R11, R12, R13 | `.claude/rules/` | **Adaptadas**: tabela de agentes aponta os existentes; boundary reconhece o spec_freeze; determinismo reconhece o `.gitattributes` parcial; modularidade traduzida para Python; design-decisions **semeada com decisões já registradas do aurora** (fontes citadas) |
| R4 (SDD, 7 fases) + skills `new-demand`/`fix-finding`/`spec-validate` | `.claude/rules/sdd.md`, `.claude/skills/` | **Escopo restrito**: governa demanda FORA do roadmap; as fases 1–12 seguem o processo próprio (âncora + auditoria de checkpoint), que tem precedência declarada no texto |
| R14 (git flow) | `.claude/rules/git-flow.md` | **Documenta o fluxo do aurora** (fase-N, rebase, squash proibido, spec-change) — o modelo develop/feature do kit NÃO foi adotado |
| Templates de demanda + ADR + planning-state.schema | `.claude/templates/` | Como no kit |
| Verify skeleton: `run.sh`, `compliance-audit.sh`, checks de baseline/boundary/state/tdd, `env_doctor`, `pipeline.yaml` mínimo | `.claude/verify/` | Pipeline LOCAL e opcional; não substitui `tools/`+`scripts/`+CI — complementa. `toolchain.json` exige docker (node fica fora de propósito: build das telas é do compose) |
| Pins semeados do HEAD | `.claude/verify/pins.json` | Exclusões: `docs/progress/**`, `phase_anchors.tsv`, project-memory, zips. Gerado em commit próprio |
| Hooks guard-boundary, guard-tdd (desativado: `produto.globs` vazio), guard-data, state-eval, post-turn-verify | `.claude/hooks/` + `settings.json` | Registrados ao lado do `check_architecture.py` existente, que permanece. Reversível: remover a entrada em settings.json |
| `boundary.json` | `.claude/verify/` | `generated` = `contracts/generated/*` (rito: codegen); `frozen` VAZIA de propósito (ver §3); deny espelhado em settings.json |
| R1 rascunho + `invariants.json` | `.claude/rules/product-invariants.md` | **PROPOSTA PENDENTE DE RATIFICAÇÃO** — ver §4 |

## 2. O aurora já tem equivalente ou melhor (kit NÃO instalado nesses pontos)

| Kit | Equivalente do aurora | Veredito |
|---|---|---|
| Boundary `frozen` para a spec | Gate `spec_freeze` + PR `spec-change:` com aprovação humana | O do aurora é mais forte (bloqueia no CI, nas duas direções de conjunto) — mantido como única autoridade |
| Mutante obrigatório (R3 §5) | Prova negativa pareada (`*_probes.py`, 26/26) | Mesmo princípio, mecanismo local melhor integrado; a R3 instalada vale para gates NOVOS de demanda, e o `_probes.py` é a forma aceita de mutante |
| Auditoria de configuração (`compliance-audit.sh`) | `check_gate_coverage.py`, `check_allowlist_do_auditor.py` etc. | Complementares: o do aurora audita o CI e o auditor; o do kit audita hooks/deny/invariantes/waivers — instalados ambos |
| Auditoria de fase (Fase 6 da SDD: QA+PO) | `checkpoint-auditor` externo com worktree | Para fases do roadmap, o do aurora prevalece; a validação da SDD vale só para demandas |
| `expected_suites.json` com contagens | README com contador de testes + `check_readme_atual.py` | O do aurora já confere prosa×árvore no CI. `expected_suites.json` instalado VAZIO; preencher é decisão do operador (§3) |
| 8 agentes do kit | `scenario-designer`, `spec-guardian`, `checkpoint-auditor` | Onda 2 NÃO instalada — os agentes existentes permanecem; os 8 papéis entram na abertura da Fase 8 (decisão §0.4) |

## 3. Conflitos e decisões que só o proprietário pode tomar

1. ~~**Ratificar as 10 invariantes da R1**~~ **DECIDIDO (2026-08-25)**: as
   10 confirmadas sem reformulação ("Confirmo as 10"). Os gates candidatos
   viraram as tarefas da §5.
2. **`.gitattributes` global (`* text=auto eol=lf`)** — o kit manda; o aurora
   cobre só `*.sh` e `user-scope/hooks/**`. Estender exige commit de
   renormalização da árvore e conferência dos verificadores que hasheiam
   conteúdo. Enquanto não decidido, pins medem blobs de HEAD (imune a CRLF).
3. **Disciplina de repin (R8) no dia a dia** — com pins semeados, alterar
   arquivo pinado exige `gen_pins.py` no mesmo PR para o stage `baseline`
   ficar verde. Se o custo parecer alto no ritmo atual, ajustar
   `_meta.exclusoes` (o gerador preserva) ou adiar o stage.
4. **Pipeline mínimo no CI** — hoje `run.sh` é local/opcional (e roda no hook
   Stop, em modo leve). Entrar como job de CI é decisão de branch protection
   (context novo — a lição P1-18 do próprio aurora se aplica).
5. **AGENTS.md desatualizado** — cópia envelhecida do CLAUDE.md (cita
   `~/.Codex/agents/` e a versão pré-decisão da seção de gabarito).
   Sincronizar, gerar de fonte única ou aposentar? Não tocado nesta branch.
6. ~~**Onda 2 e Onda 3** — gatilhos~~ **DECIDIDO (§0.4)**: Onda 2 na
   abertura da Fase 8; Onda 3 segue aguardando a dor (primeira regressão que
   red-first teria evitado).
7. **O kit vira repositório publicado?** — `C:\Projetos\estrutura-agentica-kit`
   é hoje um repo git local sem remote.
8. ~~**Base desta branch**~~ **RESOLVIDO (consequência de §0.2)**: rebase
   `--onto origin/main` executado em 2026-08-25 — a branch carrega só os
   commits de estrutura, com repin em commit próprio. O PR desta branch é
   independente da fase-7 e pode mergear antes ou depois dela.

## 4. Ratificação da R1 — registro

O proprietário confirmou as 10 linhas em 2026-08-25, no chat, sem
reformulação. O aviso de PROPOSTA saiu da R1, `invariants.json` está com
`status: ratificada`, e o `compliance-audit.sh` (seção `invariantes`) cobra
gate existente para cada linha — invariante sem gate é prosa.

## 5. Tarefas abertas pela ratificação (gatilho: abertura da Fase 8)

| Tarefa | O que falta | Dono |
|---|---|---|
| T-INV-2 | Teste de aceitação append-only dedicado (hoje só a superfície de leitura é conferida por `check_store_read_surface.py`) | `qa-engineer` (Onda 2); até lá, o proprietário |
| T-INV-3 | O par 503/201 em volta do rollback vira gate nomeado no registro canônico (hoje é teste da Fase 4 sem nome de gate) | idem |
| T-INV-7 | A metade "frame é estado TOTAL, nunca delta" ganha gate próprio (hoje `check_web_sem_derivacao.py` cobre só a derivação) | idem |
