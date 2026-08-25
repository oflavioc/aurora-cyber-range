# R1 — Invariantes de produto (PROPOSTA — PENDENTE DE RATIFICAÇÃO DO PROPRIETÁRIO)

> **STATUS: nenhuma linha desta tabela foi ratificada.** Este rascunho foi
> derivado do README, do CLAUDE.md e do `invariants.yml` existente durante a
> adoção da Estrutura Agêntica (ver `docs/ADOCAO_ESTRUTURA_AGENTICA.md`).
> Só o proprietário ratifica; até lá, a autoridade normativa segue sendo
> exclusivamente `docs/spec/` — esta página não cria norma nova, apenas dá às
> normas existentes o formato "invariante → gate" auditado pelo
> `compliance-audit.sh` (seção `invariantes`, mapa em
> `.claude/verify/invariants.json`).

Severidade: **bloqueante**. Dono: `product-owner` (papel a instanciar na Onda 2;
hoje, o proprietário). **A regra-mãe: invariante sem gate é prosa.**

| # | Invariante (proposta) | Gate executável (existente ou candidato) |
|---|---|---|
| INV-1 | **Nenhum ataque é executado.** Sem exploit, malware, ransomware funcional, criptografia real de arquivo, movimentação lateral, payload, backdoor ou vulnerabilidade intencional; todo efeito de incidente é flag de estado | `tools/check_security_constraints.py` + `tools/check_synthetic_data.py` (job `seguranca` do CI) — **existente** |
| INV-2 | **O event store é append-only.** Ações, consultas, submissões, declarações e avaliações nunca são apagadas nem alteradas | `scripts/check_store_read_surface.py` (superfície de leitura) — **parcial**; candidato: teste de aceitação T-append-only dedicado |
| INV-3 | **Rollback atua só sobre estado de simulação, gera evento explícito e novo `simulation_epoch`** — nunca apaga história | testes da Fase 4 (par 503/201 em volta do rollback) — **candidato a gate nomeado** no registro canônico |
| INV-4 | **O motor não conhece o domínio**: `range-core/` não importa nada de `domains/` | `tools/check_core_boundary.py` + `scripts/check_core_contract_imports.py` (CI `arquitetura`) — **existente** |
| INV-5 | **O domínio não conhece o inject**: nenhuma string literal de flag fora dos geradores; nenhum `event_type` fora do catálogo | `tools/check_contract_literals.py` + `tools/codegen.py --check` — **existente** |
| INV-6 | **Nenhum evento emitido carrega `objective_ids`** — o binding evento→objetivo é da projeção | `tools/check_event_envelope.py` — **existente** |
| INV-7 | **As telas refletem estado real**: toda derivação é do servidor; o cliente pinta o payload e o frame é estado TOTAL, nunca delta | `scripts/check_web_sem_derivacao.py` — **existente** (a metade "frame total" é candidata a gate próprio) |
| INV-8 | **Declaração nunca altera ground truth** (as quatro verdades); métrica de verificação nunca vem só de declaração | `scripts/check_insumo_de_metrica.py` (§3.2) — **parcial**; complementos nas Fases 6/10 |
| INV-9 | **O gabarito fica fora do repositório público**: `ground_truth.yaml` e `GM_NOTES.md` nunca versionados; identificador concreto nunca escrito à mão | `scripts/check_gabarito_fora_do_git.py` — **existente** |
| INV-10 | **Banner de ambiente simulado em toda tela e artefato** | `scripts/check_banner_de_simulacao.py` (fonte e bundle) — **existente** |

## Régua de mudança da superfície congelada

A superfície congelada do aurora é **`docs/spec/`** e o rito JÁ EXISTE e já é
mecânico: PR separado `spec-change:` com aprovação humana, aplicado pelo gate
`spec_freeze` do CI. Esta R1 **não** o substitui — apenas o reconhece como a
"porta pesada" do projeto. Não há "porta leve" proposta: spec só muda por
spec-change.

## Como ratificar

Para cada linha: o proprietário confirma (a linha fica), reformula (edita) ou
rejeita (sai). Gates "candidatos" viram tarefa com dono quando a linha for
confirmada. Depois da ratificação, remover o aviso de PROPOSTA no topo e
atualizar `.claude/verify/invariants.json`.
