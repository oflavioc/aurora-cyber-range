# Fase 0 — verificadores a implementar

Este diretório é deliberadamente entregue sem os seis verificadores finais. A primeira tarefa real do Claude Code é implementar, conforme `docs/process/PHASE_0_CHECKLIST.md`:

- `check_core_boundary.py`
- `check_contract_literals.py`
- `check_event_envelope.py`
- `check_security_constraints.py`
- `check_synthetic_data.py`
- `codegen.py` com modo `--check`

Não avance para código de aplicação antes de `python scripts/phase0_negative_tests.py` provar que cada verificador falha contra uma violação externa plantada.
