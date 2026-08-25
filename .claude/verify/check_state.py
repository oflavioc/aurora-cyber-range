#!/usr/bin/env python3
"""Stage state — planning-state válido contra o schema (Onda 2).

Validação estrutural sem dependência externa (sem jsonschema lib): campos
obrigatórios, enums de fase/status, coerência slug↔arquivo↔spec_dir, e a regra
R3: tarefa em implement/validate/done de demanda sem waiver exige red.commit.
"""
import json, os, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = Path(".claude/project-memory/planning-state")
PHASES = ["refinement", "specify", "plan", "tasks", "red", "implement", "validate", "done"]
STATUS = {"pending", "in_progress", "awaiting_approval", "approved", "proven", "done"}

if not DIR.is_dir() or not list(DIR.glob("*.json")):
    print("state: nenhum planning-state (nenhuma demanda em curso) — OK")
    sys.exit(0)

fails = 0
def fail(f, msg):
    global fails
    fails += 1
    print(f"[FAIL] {f.name}: {msg}")

for f in sorted(DIR.glob("*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        fail(f, f"JSON inválido: {e}")
        continue
    for req in ("demanda", "phase", "spec_dir"):
        if req not in d:
            fail(f, f"campo obrigatório ausente: {req}")
    if d.get("phase") not in PHASES:
        fail(f, f"phase inválida: {d.get('phase')}")
    if d.get("demanda") and f.stem != d["demanda"]:
        fail(f, f"slug '{d['demanda']}' ≠ nome do arquivo")
    if d.get("spec_dir") and not os.path.isdir(d["spec_dir"]):
        fail(f, f"spec_dir inexistente: {d['spec_dir']}")
    for ph in PHASES[:-1]:
        st = (d.get(ph) or {}).get("status")
        if st is not None and st not in STATUS:
            fail(f, f"status inválido em {ph}: {st}")
    # R3: fases pós-red exigem red provado (com commit) ou waiver registrado
    if d.get("phase") in ("implement", "validate", "done") and "tdd_waiver" not in d:
        red = d.get("red") or {}
        if red.get("status") != "proven" or not red.get("commit"):
            fail(f, "fase pós-red sem red.status=proven+commit e sem tdd_waiver (R3)")
    if f.stat().st_size and d.get("phase") == "done" and not d.get("pr_url"):
        fail(f, "done sem pr_url (R4: done só com PR aberto)")

n = len(list(DIR.glob("*.json")))
print("----")
print(f"state: {n} demanda(s) · {fails} problema(s)")
sys.exit(1 if fails else 0)
