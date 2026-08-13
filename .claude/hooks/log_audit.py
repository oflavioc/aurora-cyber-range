#!/usr/bin/env python3
"""SubagentStop — persiste o RESULTADO da auditoria de checkpoint.

A versao anterior gravava apenas timestamp, agent_type e session_id. O
veredito PASS/FAIL e os findings morriam com a sessao, e a proxima pessoa a
abrir o repositorio nao tinha como saber que o gate mordeu. Uma auditoria
cujo resultado nao sobrevive nao e registro, e lembranca.

Dois cuidados que a versao anterior nao tinha:

1. O `checkpoint-auditor` roda em worktree descartavel
   (.aurora-worktrees/audit, recriado a cada execucao). Gravar relativo ao
   cwd perde o registro junto com o worktree — foi o que aconteceu. A raiz do
   worktree PRINCIPAL e resolvida por `git rev-parse --git-common-dir`.

2. Hook nunca derruba a sessao nem bloqueia o Stop: qualquer falha sai 0.

O relatorio completo vai para docs/progress/audit_<timestamp>.md e o
audit_log.jsonl passa a apontar para ele, com o veredito.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_REPORT_CHARS = 200_000


def main_worktree_root(start: Path) -> Path:
    """Raiz do worktree principal, mesmo quando invocado de um worktree."""
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--git-common-dir"],
            check=False,
            text=True,
            capture_output=True,
            timeout=5,
        )
        common = result.stdout.strip()
        if result.returncode == 0 and common:
            path = Path(common)
            if not path.is_absolute():
                path = (start / path).resolve()
            # <raiz principal>/.git -> <raiz principal>
            if path.name == ".git":
                return path.parent
            return path
    except Exception:
        pass
    return start


def last_agent_text(transcript: Path) -> str:
    """Ultimo bloco de texto emitido pelo subagente, do transcript JSONL."""
    chunks: list[str] = []
    try:
        with transcript.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                texts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                joined = "\n".join(t for t in texts if t.strip())
                if joined.strip():
                    chunks = [joined]
    except Exception:
        return ""
    return chunks[0] if chunks else ""


def detect_verdict(report: str) -> str:
    """Veredito por melhor esforco. 'indeterminado' quando ambiguo."""
    upper = report.upper()
    has_fail = "FAIL" in upper
    has_pass = "PASS" in upper
    if has_fail and not has_pass:
        return "FAIL"
    if has_pass and not has_fail:
        return "PASS"
    if has_fail and has_pass:
        # Relatorio que cita os dois: FAIL prevalece, porque qualquer BLOCKER
        # e FAIL (docs/process/WORKFLOW.md) e o custo de errar para o lado
        # otimista e declarar concluida uma fase que nao passou.
        return "FAIL"
    return "indeterminado"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    try:
        cwd = Path(data.get("cwd") or ".").resolve()
    except Exception:
        cwd = Path(".").resolve()

    root = main_worktree_root(cwd)
    progress = root / "docs" / "progress"

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    report = ""
    transcript = data.get("transcript_path")
    if transcript:
        report = last_agent_text(Path(transcript))[:MAX_REPORT_CHARS]

    record = {
        "ts": now.isoformat(),
        "agent_type": data.get("agent_type"),
        "session_id": data.get("session_id"),
        "cwd": str(cwd),
        "verdict": detect_verdict(report) if report else "sem_relatorio",
        "report_path": None,
        # Chaves recebidas, para diagnosticar campo ausente sem adivinhacao:
        # agent_type veio vazio nas auditorias da Fase 0.
        "payload_keys": sorted(k for k in data.keys() if k != "transcript_path"),
    }

    try:
        progress.mkdir(parents=True, exist_ok=True)
        if report:
            report_file = progress / f"audit_{stamp}.md"
            header = (
                f"# Auditoria de checkpoint — {now.isoformat()}\n\n"
                f"- session_id: `{data.get('session_id')}`\n"
                f"- veredito detectado: **{record['verdict']}**\n"
                f"- worktree auditado: `{cwd}`\n\n"
                "> Detectado por melhor esforco a partir do relatorio abaixo, "
                "que e a fonte autoritativa.\n\n---\n\n"
            )
            report_file.write_text(header + report + "\n", encoding="utf-8")
            record["report_path"] = report_file.relative_to(root).as_posix()

        with (progress / "audit_log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
