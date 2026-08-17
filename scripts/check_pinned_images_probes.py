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

WORKFLOW = ".github/workflows/invariants.yml"

UM = "a" * 64
OUTRO = "b" * 64

#: `(rotulo, compose, workflow, trecho esperado)`
PROBES = [
    (
        "digest DIFERENTE nos dois arquivos — o defeito que aconteceu",
        {"redis:7.4.1-alpine": UM},
        {"redis:7.4.1-alpine": OUTRO},
        "tem digests DIFERENTES",
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
        "TERCEIRO arquivo divergindo do compose",
        {"redis:7.4.1-alpine": UM},
        {"redis:7.4.1-alpine": UM, "postgres:16.4-alpine": OUTRO},
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
    problemas = verifica(compose, [(WORKFLOW, workflow)])

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


def probe_do_dockerfile() -> bool:
    """A varredura enxerga `FROM`, tira o ` AS <estagio>` e casa com o compose.

    A peca 7 acrescentou uma SEGUNDA FORMA SINTATICA de declarar imagem. Sem
    este probe, um erro no corte do sufixo faria `node:...@sha256:X AS cliente`
    virar uma chave que nunca casa com a do compose — e o eixo 2, que e o unico
    motivo de o `Dockerfile` estar na lista, ficaria verde sem nunca comparar
    nada.
    """
    conteudo = (
        f"FROM node:22.11.0-alpine@sha256:{UM} AS cliente\n"
        "RUN npm ci\n"
        f"FROM python:3.12.7-slim@sha256:{OUTRO}\n"
        "ENV FROM_NAO_E_MARCA=1\n"
    )
    with tempfile.TemporaryDirectory() as temporario:
        alvo = Path(temporario) / "Dockerfile"
        alvo.write_text(conteudo, encoding="utf-8")
        achadas = imagens(alvo)

    esperadas = {"node:22.11.0-alpine": UM, "python:3.12.7-slim": OUTRO}
    if achadas != esperadas:
        print(f"FALHA: a varredura de FROM devolveu {achadas}, esperado {esperadas}")
        return False
    print("OK: a varredura enxerga `FROM` e descarta o estagio - arquivo plantado")
    return True


def probe_do_from_comentado() -> bool:
    """`# FROM ...` E CAPTURADO, e isso e conservador de PROPOSITO.

    **Achado por este probe, e nao por leitura.** A primeira versao do fixture
    acima trazia um comentario comecando por `# FROM` como prosa, e a varredura
    o leu como imagem — porque ela tira o `#` antes de olhar a marca, exatamente
    como ja fazia com `image:`.

    O comportamento fica, e a razao e a que o cabecalho do verificador declara:
    a varredura e conservadora na direcao que importa. Ela pode cobrar digest de
    uma linha comentada — e o custo disso e uma justificativa humana —, e o que
    ela nao faz e PERDER uma declaracao de verdade, que seria o falso negativo.
    Um `FROM` comentado costuma ser um estagio desativado, e um estagio
    desativado sem digest volta sem digest.

    **A consequencia para quem escreve `Dockerfile` fica dita aqui:** comentario
    em prosa nao comeca com `FROM`. E o mesmo contrato que o `docker-compose.yml`
    ja tinha para `image:`.
    """
    conteudo = f"# FROM debian:bookworm@sha256:{UM}\nFROM scratch\n"
    with tempfile.TemporaryDirectory() as temporario:
        alvo = Path(temporario) / "Dockerfile"
        alvo.write_text(conteudo, encoding="utf-8")
        achadas = imagens(alvo)

    if achadas.get("debian:bookworm") != UM:
        print(f"FALHA: `# FROM` comentado deixou de ser capturado: {achadas}")
        return False
    if achadas.get("scratch") != "":
        print(f"FALHA: `FROM scratch` sem digest devia entrar sem digest: {achadas}")
        return False
    print("OK: `# FROM` comentado e capturado - conservador, e declarado")
    return True


def probe_da_divergencia_no_dockerfile() -> bool:
    """Digest de Node diferente entre o compose e o `Dockerfile` REPROVA.

    E a P3-1 com `FROM` no lugar de `image:`: o container construiria o cliente
    com um toolchain e a maquina de quem desenvolve com outro, e os dois diriam
    "node 22.11.0-alpine".
    """
    problemas = verifica(
        {"node:22.11.0-alpine": UM},
        [("Dockerfile", {"node:22.11.0-alpine": OUTRO})],
    )
    if not any("digests DIFERENTES" in p for p in problemas):
        print(f"FALHA: divergencia no Dockerfile nao foi acusada: {problemas}")
        return False
    print("OK: reprovou digest divergente entre compose e Dockerfile")
    return True


def probe_da_isencao_do_eixo_3() -> bool:
    """Imagem-base que so existe no `Dockerfile` NAO reprova — e a isencao.

    E a metade que impede a de cima de virar "bloqueia tudo": `python:3.12.7-slim`
    nunca sobe como servico, e exigir que ele aparecesse no compose obrigaria a
    inventar um servico que ninguem roda. **A isencao e do eixo 3 e so dele** —
    a versao anterior desta funcao pulava o laco inteiro e levava o eixo 2
    junto, e foi este probe que mostrou.
    """
    problemas = verifica(
        {"node:22.11.0-alpine": UM},
        [("Dockerfile", {"node:22.11.0-alpine": UM, "python:3.12.7-slim": OUTRO})],
    )
    if problemas:
        print(f"FALHA: a imagem-base do Dockerfile foi acusada: {problemas}")
        return False
    print("OK: nao acusou imagem-base ausente do compose - a isencao do eixo 3")
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
    resultados.append(probe_do_dockerfile())
    resultados.append(probe_do_from_comentado())
    resultados.append(probe_da_divergencia_no_dockerfile())
    resultados.append(probe_da_isencao_do_eixo_3())
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
