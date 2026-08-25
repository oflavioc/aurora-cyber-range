#!/usr/bin/env python3
"""Stage 0 do pipeline — env-doctor (Onda 0 da Estrutura Agêntica).

Valida a toolchain ANTES de qualquer suíte, com relatório explícito.
Mata a classe de falha "SKIP silencioso por ambiente ausente": ambiente
incompleto é reportado aqui, com nome, nunca descoberto no meio de uma suíte —
e nunca mascarado por um exit 0.

A toolchain DO PRODUTO é declarada em .claude/verify/toolchain.json:
  { "require": [ {"cmd": "node", "min": "22.0.0"}, ... ],
    "optional": [ {"cmd": "docker", "nota": "suítes de integração"} ] }
`require` ausente = FAIL; `optional` ausente = WARN nomeado.
Sempre validados: python >= 3.10 e git.
"""
import json, re, shutil, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILS, WARNS = [], []
def ok(msg):   print("[OK]  ", msg)
def warn(msg): WARNS.append(msg); print("[WARN]", msg)
def fail(msg): FAILS.append(msg); print("[FAIL]", msg)

def vtuple(s):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", s or "")
    return tuple(int(x or 0) for x in m.groups()) if m else None

# python (sempre)
if sys.version_info >= (3, 10):
    ok(f"python {sys.version.split()[0]}")
else:
    fail(f"python {sys.version.split()[0]} < 3.10")

# git (sempre)
if shutil.which("git"):
    autocrlf = subprocess.run(["git", "config", "--get", "core.autocrlf"],
                              capture_output=True, text=True).stdout.strip()
    ok("git presente")
    if autocrlf == "true":
        warn("core.autocrlf=true — inócuo com o .gitattributes (eol=lf), mas registrado")
else:
    fail("git ausente do PATH")

# toolchain declarada do produto
try:
    tc = json.load(open(".claude/verify/toolchain.json", encoding="utf-8"))
except Exception:
    tc = {}
    warn("toolchain.json ausente/ilegível — só python+git validados; declare a toolchain do produto")

def checa(entry, obrigatorio):
    cmd = entry.get("cmd")
    if not cmd:
        return
    path = shutil.which(cmd)
    if not path:
        msg = f"{cmd} ausente do PATH" + (f" ({entry['nota']})" if entry.get("nota") else "")
        (fail if obrigatorio else warn)(msg)
        return
    ver = subprocess.run([path] + entry.get("version_args", ["--version"]),
                         capture_output=True, text=True).stdout.strip().splitlines()
    ver = ver[0] if ver else ""
    minimo = entry.get("min")
    if minimo and vtuple(ver) and vtuple(ver) < vtuple(minimo):
        (fail if obrigatorio else warn)(f"{cmd} {ver} < mínimo {minimo}")
    else:
        ok(f"{cmd} {ver}" if ver else f"{cmd} presente")

for e in tc.get("require", []):
    checa(e, True)
for e in tc.get("optional", []):
    checa(e, False)

# stdout UTF-8
enc = getattr(sys.stdout, "encoding", "") or ""
if "utf" in enc.lower():
    ok(f"stdout {enc}")
else:
    warn(f"stdout {enc or 'desconhecido'} — scripts do projeto reconfiguram para UTF-8")

print("----")
print(f"env-doctor: {len(FAILS)} FAIL · {len(WARNS)} WARN")
sys.exit(1 if FAILS else 0)
