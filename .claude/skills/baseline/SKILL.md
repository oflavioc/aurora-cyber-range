---
name: baseline
description: Valida rapidamente a integridade do baseline (pins × HEAD, boundary) e orienta o que fazer em divergência. Use antes de começar trabalho e sempre que o state-eval acusar divergência.
---

# Baseline

```bash
bash .claude/verify/run.sh --stage=baseline   # pins × blobs de HEAD
bash .claude/verify/run.sh --stage=boundary   # protegidos coerentes
python tools/codegen.py --check               # gerados byte-idênticos (já existia)
```

## Leitura dos resultados

- **Tudo verde** → o repositório é ele mesmo; trabalhe.
- **baseline FAIL "pin diverge"** → alguém alterou arquivo pinado sem repin.
  Mudança sua e legítima → `python .claude/verify/gen_pins.py` + commit próprio
  com motivo (R8). Não é sua → **não toque**: reporte ao usuário com o diff.
- **baseline FAIL "sem pin"** → arquivo novo rastreado; regenerar o registry no
  mesmo PR que o introduziu.
- **boundary FAIL** → protegido divergiu SEM rito: isso é incidente, não tarefa.
  Parar e reportar ao usuário com a classe e o rito exigido.
- **codegen --check FAIL** → decidir a direção ANTES de agir: o catálogo mudou
  de propósito (regenerar + repin) ou o gerado foi editado à mão (reverter).

## Âncoras

- Classe `generated` do boundary: `contracts/generated/events.py` / `.ts`.
- `docs/spec/` não entra aqui: a integridade dela é do gate `spec_freeze`.
- Hash medido só vale sobre blob/árvore LF (R2 §2).
