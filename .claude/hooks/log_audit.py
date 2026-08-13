#!/usr/bin/env python3
"""SubagentStop — registro de auditoria quando o auditor roda como SUBAGENTE.

ATENCAO, PARA QUEM LER ISTO DEPOIS: este hook NAO e o mecanismo de captura da
auditoria de checkpoint. Ele esta inalcancavel pelo fluxo documentado.

`scripts/start_checkpoint_audit.sh` invoca o auditor com `claude --agent
checkpoint-auditor`, ou seja, como agente de TOPO. `SubagentStop` so dispara
para subagente despachado pela ferramenta Agent DENTRO de uma sessao. Por este
caminho o evento nunca ocorre, para nenhum valor de `agent_type` — e foi por
isso que nenhum `docs/progress/audit_*.md` jamais foi gravado, apesar de cinco
rodadas de auditoria terem acontecido.

A captura real vive no launcher, via `scripts/audit_report.py`.

Este arquivo permanece registrado em `.claude/settings.json` por um motivo
unico e estreito: SE algum dia o `checkpoint-auditor` for despachado como
subagente (pela ferramenta Agent, a partir de uma sessao ja aberta), o registro
daquela execucao nao se perde. Fora dessa hipotese ele nao roda. Nao trate a
presenca deste hook como evidencia de que a auditoria esta sendo capturada;
quem captura e o launcher.

Cuidados preservados da versao anterior:

1. o auditor roda em worktree descartavel (.aurora-worktrees/audit, recriado a
   cada execucao). Gravar relativo ao cwd perde o registro junto com o worktree;
2. o hook nunca derruba a sessao nem bloqueia o Stop: qualquer falha sai 0;
3. relatorio so e gravado quando o agente se identifica. Sem identificacao,
   registra-se a ocorrencia e NADA mais — inventar veredito a partir do texto
   final de um subagente qualquer e pior que nao registrar nenhum, e ja
   aconteceu: o arquivo fabricado sujava a arvore e bloqueava o proprio launcher
   na verificacao de tree limpo.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# scripts/ do MESMO checkout: em worktree de auditoria, .claude/hooks/ e
# scripts/ vem do commit auditado, entao o modulo compartilhado esta ao lado.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_report import (  # noqa: E402
    MAX_REPORT_CHARS,
    detect_verdict,
    last_agent_text,
    main_worktree_root,
    persist,
)

EXPECTED_AGENT = "checkpoint-auditor"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    try:
        cwd = Path(data.get("cwd") or ".").resolve()
    except Exception:
        cwd = Path(".").resolve()

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    agent_type = (data.get("agent_type") or "").strip()
    is_auditor = agent_type == EXPECTED_AGENT

    report = ""
    if is_auditor:
        transcript = data.get("transcript_path")
        if transcript:
            report = last_agent_text(Path(transcript))[:MAX_REPORT_CHARS]

    record = {
        "ts": now.isoformat(),
        "phase": None,
        "head_sha": None,
        "session_id": data.get("session_id"),
        "mode": "subagent",
        "launcher_exit": None,
        "verdict": detect_verdict(report) if report else "sem_relatorio",
        "report_path": None,
        "capture_error": None if report else "subagente nao identificado como auditor",
        "source": "subagent_stop_hook",
        "cwd": str(cwd),
        # Sem isto, um subagente qualquer viraria "auditoria" no historico.
        "identified_as_auditor": is_auditor,
        # Chaves recebidas, para diagnosticar campo ausente sem adivinhacao.
        "payload_keys": sorted(k for k in data.keys() if k != "transcript_path"),
    }

    try:
        persist(main_worktree_root(cwd), record, report, stamp)
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
