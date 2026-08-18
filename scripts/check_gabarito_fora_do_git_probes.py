#!/usr/bin/env python3
"""Prova que `check_gabarito_fora_do_git.py` REPROVA contra gabarito plantado.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

POR QUE OS PROBES INJETAM A LISTA DE VERSIONADOS
--------------------------------------------------
O defeito central desta checagem e um arquivo que **nao existe na arvore** — e
que nao pode existir, porque plantar um `GM_NOTES.md` versionado para testar
seria versionar gabarito. `verifica()` recebe a lista, o `.gitignore` e o
template por parametro para que nenhum probe precise escrever nada.

O PROBE MAIS IMPORTANTE E O DO TEMPLATE, e nao o do arquivo versionado: o
arquivo versionado tem duas outras guardas (o `.gitignore` e a revisao do PR); o
identificador escrito a mao dentro do template nao tem nenhuma alem desta.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_gabarito_fora_do_git import (  # noqa: E402
    ENTRADA,
    GITIGNORE,
    MODULOS,
    SEED,
    TEMPLATE,
    main,
    verifica,
)

VERSIONADOS = ["README.md", "domains/academus/seed/dataset.py", "contracts/ground_truth.schema.yaml"]
IGNORE = GITIGNORE.read_text(encoding="utf-8")
MODELO = TEMPLATE.read_text(encoding="utf-8")


def _fontes(template: str | None = None) -> dict[str, str]:
    """As fontes reais, com o template opcionalmente trocado pelo plantado."""
    fontes = {TEMPLATE.name: MODELO if template is None else template}
    fontes.update({n: (SEED / n).read_text(encoding="utf-8") for n in MODULOS})
    return fontes


def _ignore_sem_entrada() -> str:
    return "\n".join(l for l in IGNORE.splitlines() if l.strip() != ENTRADA)


def _ignore_sem_motivo() -> str:
    """A entrada existe e o comentario acima dela some."""
    linhas = [l for l in IGNORE.splitlines() if not l.startswith("#")]
    return "\n".join(linhas)


PROBES = [
    (
        "`GM_NOTES.md` versionado num pack",
        (VERSIONADOS + ["scenarios/academus/ransomware/GM_NOTES.md"], IGNORE, _fontes()),
        "esta VERSIONADO",
    ),
    (
        "`ground_truth.yaml` versionado, e em outro diretorio",
        (VERSIONADOS + ["packs/linha-b/ground_truth.yaml"], IGNORE, _fontes()),
        "esta VERSIONADO",
    ),
    (
        "o schema do contrato NAO e confundido com o gabarito",
        (VERSIONADOS, IGNORE, _fontes()),
        None,  # `ground_truth.schema.yaml` esta na lista e tem de passar
    ),
    (
        "a entrada de `scenarios/` sumiu do `.gitignore`",
        (VERSIONADOS, _ignore_sem_entrada(), _fontes()),
        "nao tem a entrada",
    ),
    (
        "a entrada ficou sem motivo escrito",
        (VERSIONADOS, _ignore_sem_motivo(), _fontes()),
        "sem motivo escrito",
    ),
    (
        "case_id escrito a mao no template versionado",
        (VERSIONADOS, IGNORE, _fontes(MODELO + "\nO caso GC-0007 e o mais claro deles.\n")),
        "identificador concreto",
    ),
    (
        "a conta comprometida citada na prosa",
        (VERSIONADOS, IGNORE, _fontes(MODELO + "\nA conta e a U-P-0000, e ela assina todos.\n")),
        "identificador concreto",
    ),
    (
        "matricula do grupo alvo citada na prosa",
        (VERSIONADOS, IGNORE, _fontes(MODELO + "\nOs alunos sao A-000001 e A-000002.\n")),
        "identificador concreto",
    ),
    (
        "placeholder trocado por numero fixo",
        (VERSIONADOS, IGNORE, _fontes(MODELO.replace("{{N_INDEVIDOS}}", "22"))),
        "perdeu os placeholders",
    ),
    (
        "controle: a arvore real",
        (VERSIONADOS, IGNORE, _fontes()),
        None,
    ),
]


def roda(rotulo: str, argumentos: tuple, esperado: str | None) -> bool:
    problemas = verifica(*argumentos)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': gabarito plantado e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com gabarito plantado - {rotulo}")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1
    resultados = [roda(*p) for p in PROBES]
    print()
    if all(resultados):
        print(
            f"check_gabarito_fora_do_git.py reprova nos {len(resultados)} eixos: os "
            "dois nomes versionados, o `.gitignore` sem entrada e sem motivo, tres "
            "formas de identificador escrito a mao no template, o placeholder "
            "perdido, e os dois casos verdes de controle — inclusive o schema do "
            "contrato, que tem `ground_truth` no nome e continua versionado."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
