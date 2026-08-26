#!/usr/bin/env python3
"""Stage baseline — registry de pins × blobs de HEAD (Onda 0).

Verifica três coisas, sempre contra BLOBS (à prova de CRLF/plataforma):
  1. todo pin do registry bate com o blob de HEAD;
  2. nenhum arquivo pinado sumiu de HEAD;
  3. nenhum arquivo rastreado "pinável" (fora das exclusões) está SEM pin —
     arquivo novo exige regenerar o registry no mesmo PR (gen_pins.py).

Lição de origem: o manifesto manual anterior nunca era regenerado, vivia
vermelho e por isso ninguém o rodava — gate que falha pelo motivo errado vira
gate morto.
"""
import hashlib, json, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SELF = ".claude/verify/pins.json"

try:
    reg = json.load(open(SELF, encoding="utf-8"))
except FileNotFoundError:
    print("[FAIL] pins.json ausente — rode: python .claude/verify/gen_pins.py")
    sys.exit(1)

pins = reg["files"]
_excl = [e.split(" (")[0] for e in reg["_meta"]["exclusoes"]]  # anotação entre parênteses é doc, não padrão
excl_prefixes = tuple(e[:-2] for e in _excl if e.endswith("**"))
excl_suffixes = tuple(e[1:] for e in _excl if e.startswith("*."))
# caminho exato: padrão sem curinga — o mesmo trio de formas do gen_pins.py
excl_exatas = {e for e in _excl if "*" not in e}

tracked = [f for f in subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.splitlines() if f]

bad, missing, unpinned = [], [], []
for path, want in pins.items():
    r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True)
    if r.returncode != 0:
        missing.append(path)
        continue
    got = hashlib.sha256(r.stdout).hexdigest()
    if got != want:
        bad.append((path, want[:12], got[:12]))

for f in tracked:
    if f == SELF or f in excl_exatas or (excl_prefixes and f.startswith(excl_prefixes)) or (excl_suffixes and f.endswith(excl_suffixes)):
        continue
    if f not in pins:
        unpinned.append(f)

for p, w, g in bad:
    print(f"[FAIL] pin diverge: {p} (registry {w}… ≠ HEAD {g}…)")
for p in missing:
    print(f"[FAIL] pinado mas ausente de HEAD: {p}")
for p in unpinned:
    print(f"[FAIL] rastreado sem pin (regenere o registry no mesmo PR): {p}")

total = len(pins)
okn = total - len(bad) - len(missing)
print("----")
print(f"baseline: {okn}/{total} pins conferem · {len(bad)} divergentes · "
      f"{len(missing)} ausentes · {len(unpinned)} sem pin")
sys.exit(1 if (bad or missing or unpinned) else 0)
