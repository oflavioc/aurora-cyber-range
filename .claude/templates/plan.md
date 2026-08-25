# Plano — <NNN-slug>

> Fase 2 · dono: tech-lead · consome a spec aprovada.

## Desenho

Camada e superfície escolhidas; por quê. Módulos tocados/criados (um dono por
módulo). Para cada dado novo: **owner do estado** (R9 §5).

## Contratos e registros

- APIs públicas: entradas novas/alteradas no manifesto de contratos do produto.
- Pontos de extensão: nenhum monkey-patch; extensão via API de registro (R9 §4).
- Ordem de composição/injeção no builder, se relevante.
- Pins: arquivos pinados que mudarão (repin no mesmo PR — R8).

## Boundary

Classe tocada mais alta: nenhuma | produto | generated (via builder) | frozen
(PAROU — rito da R1).

## Checklist R9 (módulo novo)

- [ ] escopo próprio + instalação única · [ ] uma API registrada · [ ] namespace por prefixo
- [ ] sem superfície insegura proibida · [ ] ≤600 linhas ou justificativa · [ ] helper único de invariante

## Waves

| Wave | Tarefas (resumo) | Depende de |
|---|---|---|

## Riscos e rollback

O que pode quebrar, como se detecta (gate), como se reverte.

## Protótipo

Questão que só código responde → branch `prototype/<nome>`; aprendizado
registrado aqui; o protótipo nunca vira produção.
