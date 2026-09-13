#!/usr/bin/env python3
"""Grava a prova do exercicio de 4 h — lint, travessia e medida, amarrados.

O GRAVADOR do par cujo verificador e `check_prova_do_exercicio_4h.py` — a
resposta ao H2 da 2ª auditoria da Fase 7, na classe da P4-10 e do par do seed:
o que exige ambiente (Postgres, o pack em disco) roda AQUI, fora da sessao do
julgador, e o resultado chega amarrado por hash — a arvore do codigo que mediu
e os sete arquivos do pack medido.

TRES MEDICOES, UMA GRAVACAO:

    lint      — `range_cli.lint.lint`, a MESMA lista de passos do boot;
    travessia — `branching.percorre`, todos os caminhos (item 6 da DoD);
    medida    — `medida_do_exercicio_4h.mede`, o numero do item 9 com
                maquina/data/stack por codigo.

O ARQUIVO E ESCRITO MESMO QUANDO ALGO FALHA, como nos dois pares irmaos: e
assim que "falhou" se distingue de "ninguem rodou". O verificador reprova
prova de falha pela direcao (e).

USO:
    AURORA_TEST_DATABASE_URL=... python scripts/prova_do_exercicio_4h.py \\
        scenarios/academus/ransomware-universidade

O banco de medicao e TRUNCADO — nunca o banco semeado do exercicio.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_prova_do_exercicio_4h import ESQUEMA, EVIDENCIA  # noqa: E402
from medida_do_exercicio_4h import mede  # noqa: E402

from range_cli import lint as lint_de_cenario  # noqa: E402
from range_core.engine.loader import branching, contract_source, pack_loader  # noqa: E402

#: Os sete arquivos do pack completo — a segunda perna da amarracao.
ARQUIVOS_DO_PACK = (
    "manifest.yaml",
    "injects.yaml",
    "branches.yaml",
    "objectives.yaml",
    "information_distribution.yaml",
    "ground_truth.yaml",
    "GM_NOTES.md",
)


def _arvore(raiz: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(raiz), "rev-parse", "--verify", "HEAD^{tree}"],
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if len(argumentos) != 1:
        print(__doc__.split("USO:")[1].strip(), file=sys.stderr)
        return 2
    url = os.environ.get("AURORA_TEST_DATABASE_URL")
    if not url:
        print("AURORA_TEST_DATABASE_URL nao definida.", file=sys.stderr)
        return 1

    pack_dir = Path(argumentos[0])
    doc: dict = {
        "esquema": ESQUEMA,
        "tree": _arvore(REPO_ROOT),
        "pack_dir": pack_dir.as_posix(),
        "gerado_por": "scripts/prova_do_exercicio_4h.py",
        "arquivos": {
            nome: hashlib.sha256((pack_dir / nome).read_bytes()).hexdigest()
            for nome in ARQUIVOS_DO_PACK
            if (pack_dir / nome).is_file()
        },
    }

    contracts = contract_source.read_contracts()
    flags = lint_de_cenario.flags_do_pack(pack_dir, Path.cwd())

    achados = lint_de_cenario.lint(pack_dir, contracts=contracts, adapter_flags=flags)
    doc["lint_sem_achados"] = not achados
    doc["lint_achados"] = [a.erro.site for a in achados]

    if achados:
        doc["item_6_dryrun_todos_os_caminhos"] = False
        doc["item_9_reconstrucao_em_menos_de_3_s"] = False
    else:
        documentos = pack_loader.le_documentos(pack_dir, contracts)
        try:
            caminhos = branching.percorre(
                documentos.get("injects.yaml"), documentos.get("branches.yaml")
            )
            doc["item_6_dryrun_todos_os_caminhos"] = True
            doc["caminhos"] = len(caminhos)
            doc["pontos"] = len({c.ponto.id for c in caminhos})
        except pack_loader.PackError as erro:
            doc["item_6_dryrun_todos_os_caminhos"] = False
            doc["travessia_recusou"] = f"[{erro.site}] {erro.mensagem.splitlines()[0]}"

        medicao = mede(pack_dir, url)
        doc.update(medicao)
        doc["item_9_reconstrucao_em_menos_de_3_s"] = medicao["passa"]

    destino = REPO_ROOT / EVIDENCIA
    destino.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    tudo = all(
        doc.get(item) is True
        for item in (
            "lint_sem_achados",
            "item_6_dryrun_todos_os_caminhos",
            "item_9_reconstrucao_em_menos_de_3_s",
        )
    )
    print(
        f"prova gravada em {EVIDENCIA} — arvore {doc['tree'][:12]}, "
        f"{len(doc['arquivos'])} arquivos do pack, "
        f"{'TUDO PASSOU' if tudo else 'COM FALHA (gravada mesmo assim)'}"
    )
    return 0 if tudo else 1


if __name__ == "__main__":
    raise SystemExit(main())
