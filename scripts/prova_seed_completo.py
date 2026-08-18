#!/usr/bin/env python3
"""Mede o seed COMPLETO: `< 5 min` e byte-identico. Itens 1 e 2 da DoD da Fase 5.

POR QUE ISTO E SCRIPT E NAO TESTE
----------------------------------
A suite prova a LOGICA em escala reduzida, em segundos. O que so o volume real
mede e o TEMPO — `01` §7 e `02` §5 poem o alvo em cinco minutos para o dataset
completo, e um teste de suite que semeasse 28 mil alunos duas vezes tornaria
`unittest discover` inviavel para todo o resto.

Mesma forma de `scripts/bench_reconstruction.py` e `scripts/mede_cache_frio.py`:
o numero sai daqui, com maquina, data e stack ao lado. `06` T3 fixou essa
exigencia de forma para a curva da Fase 2 — *"numero de desempenho sem o contexto
em que foi obtido envelhece sem que ninguem perceba"* — e ela vale igual aqui.

O QUE ELE MEDE, E NA ORDEM
---------------------------
    1. gerar    o dataset em memoria, a partir do `RANDOM_SEED`
    2. carregar por `COPY`, uma transacao
    3. dump     SHA-256 por tabela, `COPY ... TO` ordenado
    4. repetir  1-3 e comparar: os SHAs tem de bater EXATAMENTE

USO
    AURORA_SEED_DATABASE_URL=postgresql+psycopg://user:senha@host:5432/base \\
    RANDOM_SEED=20260818 python scripts/prova_seed_completo.py

VARIAVEL PROPRIA, e nao `DATABASE_URL`: este script **TRUNCA** as vinte tabelas,
duas vezes. Mesma disciplina de `AURORA_TEST_DATABASE_URL` — quem a define esta
dizendo que aquele banco e descartavel.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import text

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from domains.academus.api.repositorio import engine_do_ambiente  # noqa: E402
from domains.academus.seed import carga, dataset  # noqa: E402
from range_core.determinism import random_seed  # noqa: E402

DSN_ENV = "AURORA_SEED_DATABASE_URL"

#: O ARTEFATO ASSINADO — M2 da segunda auditoria, na forma do
#: `check_provas_de_container.py`.
#:
#: Ate aqui o numero vivia so no registro da fase, e o registro trazia DOIS —
#: 159,4 s e 144,3 s, de antes e depois do embaralhamento — sem nada dizendo a
#: qual commit cada um pertencia. Numero de desempenho sem commit e ambiguo assim
#: que a arvore anda uma vez.
#:
#: O arquivo carrega o SHA do checkout, e `check_prova_do_seed.py` reprova quando
#: ele diverge E quando o arquivo nao existe. Nao ha degradacao para "ok por nao
#: saber": nao ter a prova e o caso em que nao se pode afirmar o item 1.
EVIDENCIA = ".aurora-prova-do-seed.json"

#: A ordem inversa das FKs, como em `tests/_academus_banco.py`. Repetida aqui
#: porque `scripts/` nao importa de `tests/`: script de operador nao pode
#: depender da suite existir.
TABELAS = (
    "audit_trail", "hpc_jobs", "research_projects", "exam_questions",
    "financing_contracts", "scholarships", "diplomas", "academic_transcripts",
    "attendance_records", "enrollments", "grades", "classes", "students",
    "access_delegations", "rectification_authorizations", "subjects",
    "professors", "courses", "users", "academic_calendar",
)

ORCAMENTO_SEGUNDOS = 300.0


def _limpa(motor) -> None:
    with motor.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY"))


def _rodada(motor, seed: int) -> tuple[float, dict[str, str], int]:
    _limpa(motor)
    inicio = time.perf_counter()
    dados = dataset.gerar(dataset.ESCALA_COMPLETA, seed=seed)
    gerado = time.perf_counter()
    carga.carregar(motor, dados)
    carregado = time.perf_counter()
    digests = carga.dump_canonico(motor)
    fim = time.perf_counter()

    print(
        f"    gerar    {gerado - inicio:7.2f} s\n"
        f"    COPY     {carregado - gerado:7.2f} s\n"
        f"    dump     {fim - carregado:7.2f} s\n"
        f"    seed     {carregado - inicio:7.2f} s  <- o que a DoD mede"
    )
    return carregado - inicio, digests, dados.total()


def main() -> int:
    url = os.environ.get(DSN_ENV)
    if not url:
        print(
            f"{DSN_ENV} nao definida. Este script TRUNCA as vinte tabelas duas "
            "vezes, entao exige banco declarado descartavel. Ver o cabecalho.",
            file=sys.stderr,
        )
        return 2

    seed = random_seed()
    motor = engine_do_ambiente(url)

    print("PROVA DO SEED COMPLETO — itens 1 e 2 da DoD da Fase 5\n")
    print(f"  maquina  {platform.platform()}")
    print(f"  python   {platform.python_version()}")
    print(f"  data     {datetime.now(timezone.utc).date().isoformat()}")
    print(f"  seed     {seed}")
    print(f"  escala   {dataset.ESCALA_COMPLETA}\n")

    print("  rodada 1")
    tempo_1, digests_1, linhas = _rodada(motor, seed)
    print(f"\n  linhas geradas: {linhas:,}\n")
    print("  rodada 2 — mesmo seed")
    tempo_2, digests_2, _ = _rodada(motor, seed)

    identico = digests_1 == digests_2
    dentro = max(tempo_1, tempo_2) < ORCAMENTO_SEGUNDOS

    print("\n" + "=" * 68)
    print(
        f"  item 1  seed completo em < 5 min: "
        f"{'PASSA' if dentro else 'FALHA'} — "
        f"{max(tempo_1, tempo_2):.1f} s de {ORCAMENTO_SEGUNDOS:.0f} s"
    )
    print(
        f"  item 2  dataset byte-identico:    "
        f"{'PASSA' if identico else 'FALHA'} — "
        f"{len(digests_1)} tabelas, SHA-256 por tabela"
    )
    if not identico:
        divergentes = [t for t in digests_1 if digests_1[t] != digests_2.get(t)]
        print(f"          divergiram: {divergentes}")
    print("=" * 68)

    # O SHA DA TRILHA IMPRESSO, e nao so comparado: ele e o que um auditor pode
    # reproduzir a partir do mesmo seed sem confiar nesta saida.
    print(f"\n  audit_trail  {digests_1['audit_trail']}")
    print(f"  students     {digests_1['students']}")

    _grava(
        {
            "commit": _head(),
            "maquina": platform.platform(),
            "python": platform.python_version(),
            "data": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "linhas": linhas,
            "orcamento_s": ORCAMENTO_SEGUNDOS,
            "segundos": [round(tempo_1, 2), round(tempo_2, 2)],
            "item_1_seed_em_menos_de_5_min": dentro,
            "item_2_byte_identico": identico,
            "digests": digests_1,
        }
    )
    print(f"\n  evidencia gravada em {EVIDENCIA}")

    return 0 if (identico and dentro) else 1


def _head() -> str | None:
    r = subprocess.run(
        ["git", "-C", REPO_ROOT, "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        capture_output=True,
        text=True,
        check=False,
    )
    sha = r.stdout.strip()
    return sha if len(sha) == 40 else None


def _grava(doc: dict) -> None:
    """O arquivo e SEMPRE escrito, inclusive quando a prova falha.

    Mesma decisao do gravador de container: evidencia que so existe quando passa
    nao distingue "falhou" de "ninguem rodou" — e a segunda e exatamente o que o
    verificador precisa poder reprovar.
    """
    with open(os.path.join(REPO_ROOT, EVIDENCIA), "w", encoding="utf-8") as saida:
        saida.write(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
