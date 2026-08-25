---
name: spec-validate
description: Compara uma spec aprovada com a implementação real e reporta o score de conformidade item a item. Somente leitura. Use na Fase 6 da new-demand ou para auditar demanda antiga.
---

# Validar spec contra a implementação

Somente leitura — validação é separada de correção. Executor: `qa-engineer`.

## Procedimento

1. Extrair da `spec.md` a lista numerada de exigências verificáveis (critérios
   de aceite, gates prometidos, contratos declarados).
2. Para cada item, conferir na implementação REAL (source + execução de gate),
   nunca no relatório de quem implementou (R2).
3. Classificar cada gap em UMA de três classes:
   - **spec-errada** — a exigência estava mal formulada; corrigir a spec exige
     aprovação do usuário;
   - **implementação-divergente** — existe mas diferente do especificado;
   - **faltando** — não implementado.
4. **Divergência pesa mais que ausência**: o que existe divergente engana o
   leitor da spec; o que falta é visível.
5. Score = itens conformes / total, com a lista completa anexa.

## Saída e limites

- Score 100% → segue para o aceite de intenção do PO.
- < 100% → classificar, devolver ao orquestrador para UMA iteração de correção;
  **máximo 2 iterações** — na terceira divergência, escalar ao usuário com o
  quadro completo.
- Gap classe spec-errada NUNCA se "resolve" afrouxando o gate (R10 §1).
- Specs validadas viram insumo do cross-check das demandas seguintes.
