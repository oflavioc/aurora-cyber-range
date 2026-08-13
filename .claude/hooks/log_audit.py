#!/usr/bin/env python3
"""SubagentStop — registra que uma auditoria de checkpoint ocorreu."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

log = Path("docs/progress/audit_log.jsonl")
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_type": data.get("agent_type"),
        "session_id": data.get("session_id"),
    }, ensure_ascii=False) + "\n")
sys.exit(0)
