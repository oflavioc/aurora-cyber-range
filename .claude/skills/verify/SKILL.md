---
name: verify
description: Roda o pipeline de verificação e o compliance-audit, e roteia cada falha para o dono certo com a correção certa. Use depois de qualquer alteração e antes de considerar trabalho pronto.
---

# Verificar o repositório

```bash
bash .claude/verify/run.sh                # pipeline mínimo (grava .last_green)
bash .claude/verify/compliance-audit.sh  # a configuração agêntica está íntegra?

# Os gates DO PRODUTO seguem sendo os de sempre — o pipeline acima não os
# substitui, complementa:
python -m unittest discover -s tests     # a suíte (sem stack, parte pula NOMEANDO)
python tools/check_core_boundary.py      # e demais verificadores de tools/ e scripts/
```

## Roteamento de falha — stage → correção certa → saída PROIBIDA

| Stage | Correção certa | Nunca |
|---|---|---|
| env-doctor | instalar/declarar a dependência em `toolchain.json` | mascarar com SKIP |
| baseline | mudança legítima → `gen_pins.py` no mesmo PR; ilegítima → reverter | editar pins.json à mão |
| boundary | seguir o RITO nomeado na mensagem (generated → `tools/codegen.py`) | contornar o hook |
| state | corrigir o planning-state para refletir o real | editar para "ficar verde" sem refletir o real |
| tdd | provar/commitar o red; completar o rastro | registrar red retroativo falso |
| compliance | corrigir a configuração apontada | remover a seção que acusa |
| verificadores de `tools/`/`scripts/` (CI) | diagnóstico de causa (R2 §3); a correção nunca enfraquece o verificador — e todo verificador mantém seu `_probes.py` | **enfraquecer o gate para passar** |

Falha que é decisão documentada (design-decisions/known-issues) → vira
registro, não correção. Falha nova sem dono claro → achado com id (padrão
P/B/M do projeto), nunca conserto "de passagem".
