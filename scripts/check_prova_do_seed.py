#!/usr/bin/env python3
"""M2 — a prova do seed completo e DESTE commit, e ela existe.

O QUE ESTA CHECAGEM FECHA
--------------------------
Os itens 1 e 2 da DoD da Fase 5 sao NUMEROS DE MAQUINA: `< 5 min` e "dataset
byte-identico". O auditor nao pode reexecutar — o script exige Postgres, escreve
3,5 milhoes de linhas duas vezes e leva minutos, e reexecuta-lo em outra maquina
produziria OUTRO numero, que nao confirma o primeiro. A exclusao dele da
allowlist e decisao registrada, pelo mesmo criterio do `bench_reconstruction`.

**O que faltava nao era o auditor rodar: era a gravacao existir.** Ate aqui o
numero vivia so no registro da fase, e o registro trazia DOIS — 159,4 s e
144,3 s, de antes e depois do embaralhamento — sem nada dizendo a qual commit
cada um pertencia. Numero de desempenho sem commit fica ambiguo assim que a
arvore anda uma vez, e ela andou.

E A MESMA FORMA DO `check_provas_de_container.py`, e pelo mesmo argumento da
P4-10: o que exige rede e volume acontece FORA da sessao do julgador, e o
resultado chega pronto — amarrado ao objeto por SHA. Isso nao faz o auditor ver a
execucao; amarra a evidencia ao commit, que e a diferenca entre "alguem rodou" e
"rodou nisto".

AS CINCO DIRECOES, e a primeira e a que nao pode degradar
-----------------------------------------------------------
    (a) o arquivo NAO EXISTE                                    -> REPROVA
    (b) o `commit` gravado diverge do `HEAD` deste checkout      -> REPROVA
    (c) o arquivo esta VERSIONADO                                -> REPROVA
    (d) falta maquina, data, python ou o numero de linhas        -> REPROVA
    (e) a prova gravada diz que um dos dois itens FALHOU         -> REPROVA

A **(a)** e a que este verificador existe para nao degradar: "nao ha prova" e
exatamente o caso em que nao se pode afirmar o item. Os dois predicados de base
aposentados da Fase 3 degradaram para "ok" quando nao sabiam, e cada um custou
uma auditoria que parecia gate.

A **(c)** e o espelho: o arquivo carrega o SHA do commit que ele mede, e **um
commit nao contem o proprio SHA**. Versiona-lo tornaria a amarracao circular.

A **(d)** e `06` T3 virando predicado: numero de desempenho sem maquina, data e
stack envelhece sem que ninguem perceba.

Stdlib pura. NAO roda no job `arquitetura` — ver o rodape.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCIA = ".aurora-prova-do-seed.json"

RULE = "M2 - a prova do seed completo e deste commit"

#: `06` T3: maquina, data e stack AO LADO do numero, e nao em outro lugar.
CONTEXTO = ("maquina", "python", "data", "seed", "linhas")
ITENS = ("item_1_seed_em_menos_de_5_min", "item_2_byte_identico")


def _head(raiz: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", str(raiz), "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        capture_output=True, text=True, check=False,
    )
    sha = r.stdout.strip()
    return sha if len(sha) == 40 else None


def _versionado(raiz: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(raiz), "ls-files", "--error-unmatch", EVIDENCIA],
        capture_output=True, text=True, check=False,
    )
    return r.returncode == 0


def avalia(doc: dict | None, head: str | None, versionado: bool) -> list[str]:
    """As cinco direcoes. Por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    if versionado:
        problemas.append(
            f"`{EVIDENCIA}` esta VERSIONADO. Ele carrega o SHA do commit que "
            "mede, e um commit nao contem o proprio SHA — versiona-lo torna a "
            "amarracao circular e a evidencia deixa de dizer alguma coisa."
        )

    if doc is None:
        problemas.append(
            f"`{EVIDENCIA}` nao existe ou nao e JSON legivel. Os itens 1 e 2 da "
            "DoD ficam sem prova, e ISTO NAO DEGRADA PARA OK: nao ter a medicao e "
            "o caso em que nao se pode afirmar o item.\n"
            "    Rode, na maquina que vai medir:\n"
            "      AURORA_SEED_DATABASE_URL=... RANDOM_SEED=... \\\n"
            "          python scripts/prova_seed_completo.py"
        )
        return problemas

    if head is None:
        problemas.append(
            "este checkout nao resolve um HEAD de git: sem o SHA nao ha contra o "
            "que amarrar a evidencia."
        )
    elif doc.get("commit") != head:
        problemas.append(
            f"a prova foi gravada sobre `{doc.get('commit')}` e este checkout e "
            f"`{head}`. Ela mede OUTRO commit — e o numero de um commit nao "
            "afirma nada sobre este. Rode de novo sobre o candidato."
        )

    for campo in CONTEXTO:
        if not doc.get(campo):
            problemas.append(
                f"a prova nao traz `{campo}`. `06` T3 exige maquina, data e stack "
                "ao lado do numero: sem o contexto, o numero envelhece sem que "
                "ninguem perceba."
            )

    for item in ITENS:
        if doc.get(item) is not True:
            problemas.append(
                f"a prova gravada diz que `{item}` NAO passou "
                f"({doc.get(item)!r}). O arquivo e escrito mesmo quando a medicao "
                "falha, de proposito: e assim que 'falhou' se distingue de "
                "'ninguem rodou'."
            )

    return problemas


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    caminho = REPO_ROOT / EVIDENCIA
    try:
        doc = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = None

    problemas = avalia(doc, _head(REPO_ROOT), _versionado(REPO_ROOT))

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    # A SAIDA INTEGRA, e nao "ok": aprovar em silencio trocaria um NAO VERIFICADO
    # por "confie na minha checagem" — a mesma exigencia que a P4-10 fez ao (c).
    print(f"{RULE}: prova de `{doc['commit'][:12]}`, e este checkout e o mesmo.")
    print(f"  maquina  {doc['maquina']}  ·  python {doc['python']}")
    print(f"  data     {doc['data']}  ·  seed {doc['seed']}")
    print(f"  linhas   {doc['linhas']:,}")
    print(
        f"  item 1   {doc['segundos'][0]:.1f} s e {doc['segundos'][1]:.1f} s, "
        f"orcamento {doc['orcamento_s']:.0f} s"
    )
    print(f"  item 2   {len(doc['digests'])} tabelas com SHA-256 igual nas duas")
    print(f"  audit_trail  {doc['digests']['audit_trail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
