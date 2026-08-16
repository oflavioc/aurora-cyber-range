#!/usr/bin/env python3
"""Prova que `check_pinned_images.py` REPROVA contra digest plantado.

O PRIMEIRO PROBE E O DEFEITO REAL. Nao e um caso hipotetico: e exatamente o que
eu fiz na peca 3 — inventei um digest de Redis para o CI com o compose ja
pinando o valor certo ao lado. Ele foi pego por `grep`, e este arquivo existe
para que na proxima vez seja pego por mecanismo.

E o ultimo probe e o que os dois defeitos de vacuidade da peca 3 ensinaram a
escrever: a varredura precisa provar que ENXERGA, senao todos os outros probes
ficam verdes contra dicionarios injetados por eles mesmos.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_pinned_images import imagens, main, verifica  # noqa: E402

UM = "a" * 64
OUTRO = "b" * 64

#: `(rotulo, compose, workflow, trecho esperado)`
PROBES = [
    (
        "digest DIFERENTE nos dois arquivos — o defeito que aconteceu",
        {"redis:7.4.1-alpine": UM},
        {"redis:7.4.1-alpine": OUTRO},
        "digests DIFERENTES nos dois arquivos",
    ),
    (
        "imagem sem digest no compose",
        {"postgres:16.4-alpine": ""},
        {},
        "nao esta pinada por digest",
    ),
    (
        "imagem sem digest no workflow",
        {"redis:7.4.1-alpine": UM},
        {"redis:7.4.1-alpine": ""},
        "nao esta pinada por digest",
    ),
    (
        "servico que so o CI conhece",
        {"redis:7.4.1-alpine": UM},
        {"redis:7.4.1-alpine": UM, "mysql:8": OUTRO},
        "nao existe em docker-compose.yml",
    ),
    (
        "os dois arquivos em acordo: nada a acusar",
        {"redis:7.4.1-alpine": UM, "postgres:16.4-alpine": OUTRO},
        {"redis:7.4.1-alpine": UM},
        None,
    ),
]


def roda(rotulo, compose, workflow, esperado) -> bool:
    problemas = verifica(compose, workflow)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' nao acusou pelo eixo esperado: {problemas}")
        return False
    print(f"OK: reprovou com violacao plantada - {rotulo}")
    return True


def probe_da_varredura() -> bool:
    """A varredura enxerga `image:` com e sem digest, e ignora o resto.

    Sem isto, `imagens()` podendo devolver `{}` sempre deixaria TODOS os probes
    acima verdes — nenhum deles a chama. E a mesma forma do `probe_da_varredura`
    de `check_api_surface_probes.py`, e existe pelo mesmo motivo.
    """
    conteudo = (
        "services:\n"
        "  redis:\n"
        f"    image: redis:7.4.1-alpine@sha256:{UM}\n"
        "  banco:\n"
        "    image: 'postgres:16.4-alpine'\n"
        "  app:\n"
        "    build: .\n"
        "    environment:\n"
        "      IMAGEM_PREFERIDA: nao-e-uma-chave-image\n"
    )
    with tempfile.TemporaryDirectory() as temporario:
        alvo = Path(temporario) / "compose.yml"
        alvo.write_text(conteudo, encoding="utf-8")
        achadas = imagens(alvo)

    esperadas = {"redis:7.4.1-alpine": UM, "postgres:16.4-alpine": ""}
    if achadas != esperadas:
        print(f"FALHA: a varredura devolveu {achadas}, esperado {esperadas}")
        return False
    print("OK: a varredura enxerga `image:` com e sem digest - arquivo plantado")
    return True


def probe_do_arquivo_ausente() -> bool:
    """Compose que sumiu sai com rc=2, e nao com "0 imagens, tudo certo"."""
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(REPO_ROOT / "scripts")
            + "');\n"
            "import check_pinned_images as c;\n"
            "from pathlib import Path;\n"
            "c.COMPOSE = ('docker-compose.yml', Path('nao-existe.yml'));\n"
            "sys.exit(c.main())",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if resultado.returncode != 2:
        print(f"FALHA: compose ausente saiu com rc={resultado.returncode}, esperado 2")
        print(resultado.stdout + resultado.stderr)
        return False
    print("OK: arquivo ausente reprova em vez de passar vazio - anti-vacuidade")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1

    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_da_varredura())
    resultados.append(probe_do_arquivo_ausente())

    print()
    if all(resultados):
        print(
            f"check_pinned_images.py reprova nos {len(resultados)} eixos, com o "
            "digest divergente em primeiro lugar — que e o defeito que a peca 3 "
            "cometeu de verdade."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
