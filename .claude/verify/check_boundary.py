#!/usr/bin/env python3
"""Stage boundary — coerência do manifesto de proteção (Onda 1, R6).

Valida que:
  1. boundary.json existe e todo path listado existe em HEAD;
  2. todo path protegido está no registry de pins (coerência entre manifestos);
  3. os blobs de HEAD das classes protegidas batem com os pins — divergência
     aqui nomeia o RITO violado, não só o hash.

O bloqueio em tempo de edição é do hook guard-boundary.sh; este stage é a
rede de segurança pós-fato (pega o que entrou por fora do harness).
"""
import hashlib, json, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    b = json.load(open(".claude/verify/boundary.json", encoding="utf-8"))
    pins = json.load(open(".claude/verify/pins.json", encoding="utf-8"))["files"]
except FileNotFoundError as e:
    print(f"[FAIL] manifesto ausente: {e.filename}")
    sys.exit(1)

classes = b.get("classes", {})
if not any(spec.get("paths") for spec in classes.values()):
    print("boundary: nenhum path protegido declarado ainda (kit recém-instanciado) — OK")
    sys.exit(0)

fails = 0
for classe, spec in classes.items():
    for p in spec["paths"]:
        r = subprocess.run(["git", "show", f"HEAD:{p}"], capture_output=True)
        if r.returncode != 0:
            print(f"[FAIL] {classe}: path protegido ausente de HEAD: {p}")
            fails += 1
            continue
        if p == ".claude/verify/pins.json":
            continue  # o registry não se auto-pina (por desenho)
        if p not in pins:
            print(f"[FAIL] {classe}: protegido sem pin no registry: {p}")
            fails += 1
            continue
        got = hashlib.sha256(r.stdout).hexdigest()
        if got != pins[p]:
            print(f"[FAIL] {classe}: {p} divergiu do pin SEM repin no registry.")
            print(f"       Rito exigido: {spec['rito']}")
            fails += 1

total = sum(len(s["paths"]) for s in classes.values())
print("----")
print(f"boundary: {total - fails}/{total} paths protegidos coerentes")
sys.exit(1 if fails else 0)
