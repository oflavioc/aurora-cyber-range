#!/usr/bin/env python3
"""Stage tdd — o regime red-first é auditável (Onda 3, R3).

Valida, para cada planning-state:
  1. red.status=proven ⇒ red.commit EXISTE no repositório (git cat-file);
  2. demanda done ⇒ validate.conformance presente;
  3. tdd_waiver ⇒ listado (rastro, nunca obstáculo — compliance também lista).
E para a matriz gate↔mutante (mutation-matrix.json, instalada na Onda 3):
  4. estrutura válida; toda entrada com harness/gate/última prova;
  5. dívidas declaradas listadas (visíveis, nunca implícitas).
Antes da Onda 3 a matriz pode não existir — isso é reportado com nome, não FAIL.
"""
import json, subprocess, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

fails = 0
def fail(msg):
    global fails
    fails += 1
    print("[FAIL]", msg)

DIR = Path(".claude/project-memory/planning-state")
states = sorted(DIR.glob("*.json")) if DIR.is_dir() else []
waivers = []
for f in states:
    d = json.load(open(f, encoding="utf-8"))
    red = d.get("red") or {}
    if red.get("status") == "proven":
        c = red.get("commit", "")
        r = subprocess.run(["git", "cat-file", "-e", c], capture_output=True)
        if r.returncode != 0:
            fail(f"{f.name}: red.commit '{c[:12]}' não existe no repositório")
        else:
            print(f"[OK]   {f.name}: red provado e commitado ({c[:12]}…)")
    if d.get("phase") == "done" and not (d.get("validate") or {}).get("conformance"):
        fail(f"{f.name}: done sem validate.conformance")
    if "tdd_waiver" in d:
        waivers.append(f"{f.name}: {d['tdd_waiver'].get('motivo','?')} ({d['tdd_waiver'].get('data','?')})")

for w in waivers:
    print(f"[WAIVER] {w}")
if not waivers:
    print("[OK]   waivers TDD: nenhum ativo")

try:
    mm = json.load(open(".claude/verify/mutation-matrix.json", encoding="utf-8"))
    bad = [p.get("mutante", "?") for p in mm["pares"]
           if not (p.get("harness") and p.get("gate") and (p.get("ultima_prova") or {}).get("resultado"))]
    if bad:
        fail("matriz: pares incompletos: " + ", ".join(bad))
    else:
        print(f"[OK]   matriz gate↔mutante: {len(mm['pares'])} pares completos")
    for d in mm.get("dividas_declaradas", []):
        print(f"[DÍVIDA] {d}")
except FileNotFoundError:
    print("[NOTA] mutation-matrix.json ausente — matriz gate↔mutante ainda não instalada (Onda 3)")

print("----")
print(f"tdd: {len(states)} demanda(s) · {len(waivers)} waiver(s) · {fails} problema(s)")
sys.exit(1 if fails else 0)
