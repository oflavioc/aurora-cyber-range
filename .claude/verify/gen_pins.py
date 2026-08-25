#!/usr/bin/env python3
"""Gera/atualiza o registry único de pins (Onda 0 — R8 da Estrutura Agêntica).

Fonte ÚNICA de identidade dos artefatos versionados: os hashes saem daqui,
nunca de literais espalhados. Os hashes são computados dos BLOBS de HEAD —
à prova de CRLF e de plataforma, por construção.

Uso:
  python .claude/verify/gen_pins.py            # grava .claude/verify/pins.json
  python .claude/verify/gen_pins.py --stdout   # imprime sem gravar

Exclusões e pins declarativos: se .claude/verify/pins.json já existe, as
exclusões vêm de _meta.exclusoes e os declarativos de `declared` (preservados
na regeneração). Na primeira geração valem os DEFAULTS abaixo — ajuste-os ao
projeto (docs de alta rotatividade, evidência binária, estado de processo).
"""
import hashlib, json, subprocess, sys
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SELF = ".claude/verify/pins.json"
DEFAULT_EXCLUSOES = [
    ".claude/project-memory/** (estado de processo — muda por fase; validado pelo stage state, não por pin)",
    "*.zip",
    SELF,
]

def head_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

def tracked():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f]

def blob(path):
    r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"blob ausente em HEAD: {path}")
    return r.stdout

def load_prev():
    try:
        return json.load(open(SELF, encoding="utf-8"))
    except Exception:
        return {}

def build():
    prev = load_prev()
    exclusoes = prev.get("_meta", {}).get("exclusoes", DEFAULT_EXCLUSOES)
    declared = prev.get("declared", {})
    _excl = [e.split(" (")[0] for e in exclusoes]  # anotação entre parênteses é doc, não padrão
    excl_prefixes = tuple(e[:-2] for e in _excl if e.endswith("**"))
    excl_suffixes = tuple(e[1:] for e in _excl if e.startswith("*."))
    files = {}
    for f in sorted(tracked()):
        if f == SELF or (excl_prefixes and f.startswith(excl_prefixes)) or (excl_suffixes and f.endswith(excl_suffixes)):
            continue
        files[f] = hashlib.sha256(blob(f)).hexdigest()
    return {
        "_meta": {
            "descricao": "Registry único de pins — fonte de identidade dos artefatos (R8). "
                         "Hashes = SHA-256 dos blobs de HEAD. Alterar arquivo pinado exige "
                         "regenerar este registry no MESMO PR, com motivo no commit.",
            "gerado_de_head": head_sha(),
            "gerado_em": str(date.today()),
            "exclusoes": exclusoes,
        },
        "declared": declared,
        "files": files,
    }

if __name__ == "__main__":
    # gen_pins lê blobs de HEAD: rodar com mudanças pendentes em arquivos
    # pináveis gera pins do estado ANTERIOR (erro já cometido em produção no
    # projeto de origem, duas vezes). Pré-condição mecânica:
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    pendentes = [l for l in dirty.splitlines()
                 if l[3:].strip() and not l[3:].startswith((SELF,))]
    if pendentes and "--force" not in sys.argv:
        print("[FAIL] gen_pins exige árvore limpa (HEAD é a fonte dos blobs). Pendências:")
        for l in pendentes[:5]:
            print("   ", l)
        print("Commite o conteúdo PRIMEIRO; pins vêm em commit próprio na sequência.")
        sys.exit(1)
    reg = build()
    text = json.dumps(reg, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
    else:
        with open(SELF, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"pins.json: {len(reg['files'])} arquivos pinados de HEAD {reg['_meta']['gerado_de_head'][:12]}")
