#!/usr/bin/env python3
"""Sobe a stack do commit auditado, roda as duas provas, grava a saida. P4-10.

QUEM EXECUTA ISTO E O LANCADOR, NA MAQUINA DO OPERADOR
--------------------------------------------------------
E a mesma linha que a P2-19 tracou e que a P3-4 seguiu: **o que exige rede
acontece antes da sessao, no lancador, e o resultado chega pronto.** Preparar o
ambiente e emitir o veredito sao papeis diferentes.

Por isso este script **NAO entra na allowlist do auditor**, e a ausencia e
decisao e nao esquecimento — a licao do B1 da Fase 2 e que "nada novo entra"
tambem precisa ser decidido. Ele constroi imagem, sobe container e derruba
stack: admiti-lo daria ao julgador exatamente a rede e a execucao de container
que a P2-19 recusou. O que o auditor recebe e o arquivo, e quem o julga e
`scripts/check_provas_de_container.py`, que le e nao executa.

A STACK E EFEMERA, E ISOLADA DA DE DESENVOLVIMENTO EM TRES EIXOS
------------------------------------------------------------------
O `docker-compose.yml` do projeto e o objeto da auditoria — e ele que a peca 7
entrega —, entao a prova roda contra **ele**, e nao contra uma copia. O que muda
sao tres coisas que nao podem colidir com a stack de quem desenvolve:

    projeto        `aurora-provas`, por `-p`
    nomes          `AURORA_STACK_PREFIX`, senao `container_name` e global e
                   colide mesmo com projeto diferente
    portas         proprias, e diferentes TAMBEM das da stack efemera da
                   auditoria (15432/16379), que fica no ar durante a sessao
    volume         `AURORA_PGDATA_VOLUME`, senao a prova escreveria no
                   `aurora_pgdata` de desenvolvimento — que e exatamente o que
                   o `docker-compose.audit.yml` existe para nao fazer

O volume morre no `down -v`. Sem isso, a segunda rodada encontraria o event
store da primeira e `engine.start()` recusaria — o DEMO exige um exercicio que
ainda nao comecou, e isso esta no cabecalho dele.

O ARQUIVO E SEMPRE ESCRITO, INCLUSIVE QUANDO TUDO FALHA
--------------------------------------------------------
Falha da stack vira `rc != 0` gravado, com a saida do `docker compose` junto. O
verificador reprova lendo isso, e o auditor ve **por que**.

O que nao pode acontecer e o arquivo nao existir por uma falha silenciosa e o
auditor ler ausencia como "ainda nao rodou" — por isso o `finally` grava mesmo
quando o processo esta saindo por excecao.

E POR QUE ELE NAO ABORTA A AUDITORIA
--------------------------------------
O venv da P3-4 falha ALTO porque sem ele o auditor mede outro nucleo — o
veredito sairia sobre outro commit. Aqui nao: sem as provas, os itens 1 e 4
voltam a ser NAO VERIFICADO, que e a opcao C da P4-10 e e honesto. Derrubar a
auditoria inteira por falta de Docker seria trocar um veredito parcial por
nenhum.

USO (o lancador chama assim, e ninguem mais precisa chamar)
    python scripts/grava_provas_de_container.py --worktree <caminho> \\
        --python <interpretador do venv da auditoria>
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_provas_de_container import EVIDENCIA, ESQUEMA, PROVAS  # noqa: E402

#: PROJETO, PREFIXO E VOLUME PROPRIOS. `container_name` e global no daemon: sem
#: prefixo, `-p` nao basta e o `docker compose up` colide com a stack de
#: desenvolvimento pelo NOME, mesmo estando em outro projeto.
PROJETO = "aurora-provas"
PREFIXO = "aurora-provas"
VOLUME = "aurora_provas_pgdata"

#: PORTAS PROPRIAS, e diferentes das duas outras stacks que podem estar no ar:
#: a de desenvolvimento (5432/6379/8000/8001) e a efemera da auditoria
#: (15432/16379), que sobe ANTES desta e fica ate o fim da sessao.
#:
#: Numeros baixos de proposito: as faixas de exclusao do Windows sao DINAMICAS e
#: vivem perto do intervalo efemero — 56379 ja custou um `bind: uma tentativa de
#: acesso a um soquete de uma maneira proibida pelas permissoes`, achado rodando
#: e registrado no cabecalho do `docker-compose.audit.yml`.
PORTAS = {
    "AURORA_PG_PORT": "15433",
    "AURORA_REDIS_PORT": "16380",
    "AURORA_RANGE_PORT": "18000",
    "AURORA_ACADEMUS_PORT": "18001",
}

#: O `RANDOM_SEED` e FIXO, e os dois segredos NAO SAO. A assimetria e de
#: natureza: a seed governa determinismo — `05` §8 e T8 —, e uma seed que mudasse
#: a cada rodada faria a queda de sessao da P3-10 sortear outro conjunto e a
#: prova deixar de ser comparavel entre rodadas. Os outros dois sao credenciais,
#: e `05` §8 proibe valor trivial REUTILIZAVEL: estes nascem por rodada, vivem
#: dentro de containers que morrem no `down`, e nao servem para mais nada.
SEED = "20260817"

TEMPO_LIMITE_STACK = 600
TEMPO_LIMITE_PROVA = 600


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(worktree: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


def _ambiente(senha_pg: str, credencial: str, segredo: str) -> dict[str, str]:
    env = dict(os.environ)
    # O OUTRO LADO DA MESMA DECODIFICACAO. As provas sao Python e escrevem
    # acento — `"O portal de matricula esta indisponivel"` vem do pack. Num pipe,
    # o Python do Windows escreve na codepage do locale, e o leitor aqui decodifica
    # UTF-8: os dois combinados produziriam mojibake numa evidencia que existe
    # para ser LIDA. Fixar dos dois lados e a unica forma de nao depender do
    # locale de quem roda a auditoria.
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(PORTAS)
    env.update(
        {
            "AURORA_STACK_PREFIX": PREFIXO,
            "AURORA_PGDATA_VOLUME": VOLUME,
            "POSTGRES_PASSWORD": senha_pg,
            "AURORA_GM_PASSWORD": credencial,
            "AURORA_JWT_SECRET": segredo,
            "RANDOM_SEED": SEED,
        }
    )
    return env


def _executa(
    comando: list[str], *, cwd: Path, env: dict[str, str], limite: int
) -> tuple[int, str]:
    """Roda e captura tudo — stdout e stderr no mesmo fio, que e a ordem real.

    Separa-los produziria uma evidencia em que a mensagem de erro nao fica ao
    lado da linha que a causou, e quem le e um auditor que nao viu rodar.

    A CODIFICACAO E EXPLICITA, E FOI ACHADA RODANDO. `text=True` sozinho decodifica
    pela codepage do locale — `cp1252` nesta maquina —, e a saida do `docker
    compose` tem bytes que ela nao mapeia. O que acontece entao e pior que uma
    excecao: no Windows a captura roda em THREAD LEITORA, a excecao morre la, e
    `subprocess.run` devolve **saida vazia com o rc do processo**. Uma prova
    verde com evidencia vazia, e nada acusando.

    `errors="replace"` fecha o que sobra: byte indecodificavel vira `\\ufffd` e o
    resto da saida chega. Perder um caractere e melhor que perder a evidencia.
    """
    try:
        r = subprocess.run(
            comando,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limite,
            check=False,
        )
    except FileNotFoundError as erro:
        return 127, f"{' '.join(comando)}: {erro}"
    except subprocess.TimeoutExpired:
        return 124, f"{' '.join(comando)}: excedeu {limite}s e foi interrompido."
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _compose(worktree: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "-p",
        PROJETO,
        "-f",
        str(worktree / "docker-compose.yml"),
    ]


def grava(worktree: Path, interpretador: str, saida: Path) -> int:
    commit = _sha(worktree)
    senha_pg = secrets.token_urlsafe(24)
    credencial = secrets.token_urlsafe(24)
    segredo = secrets.token_urlsafe(48)
    env = _ambiente(senha_pg, credencial, segredo)

    doc: dict = {
        "esquema": ESQUEMA,
        "commit": commit,
        "quando": _agora(),
        "gerado_por": "scripts/grava_provas_de_container.py",
        "stack": {"rc": None, "saida": ""},
        "provas": [],
    }

    try:
        inicio = time.monotonic()
        rc, texto = _executa(
            [*_compose(worktree), "up", "-d", "--build", "--wait",
             "range-api", "academus-api"],
            cwd=worktree,
            env=env,
            limite=TEMPO_LIMITE_STACK,
        )
        doc["stack"] = {
            "rc": rc,
            "segundos": round(time.monotonic() - inicio, 1),
            "saida": texto,
        }

        # A URL do banco e a do HOST, e nao a do compose: as provas rodam FORA
        # dos containers, e `postgres:5432` so resolve dentro da rede deles.
        base = {
            "DATABASE_URL": (
                f"postgresql+psycopg://aurora:{senha_pg}"
                f"@127.0.0.1:{PORTAS['AURORA_PG_PORT']}/aurora"
            ),
            "AURORA_GM_PASSWORD": credencial,
            "AURORA_JWT_SECRET": segredo,
            "RANDOM_SEED": SEED,
            "AURORA_DEMO_RANGE_URL": f"http://127.0.0.1:{PORTAS['AURORA_RANGE_PORT']}",
            "AURORA_DEMO_ACADEMUS_URL": (
                f"http://127.0.0.1:{PORTAS['AURORA_ACADEMUS_PORT']}"
            ),
            "AURORA_RANGE_CONTAINER": f"{PREFIXO}-range-api",
        }

        for prova in PROVAS:
            comando = [
                interpretador if parte == "python" else parte for parte in prova.comando
            ]
            if rc != 0:
                # A stack nao subiu. A prova e gravada assim mesmo, com rc
                # proprio: entrada AUSENTE e reservada para arquivo truncado, e
                # confundir as duas faria o auditor ler "nao gravou" onde o fato
                # e "nao teve contra o que rodar".
                doc["provas"].append(
                    {
                        "id": prova.id,
                        "item": prova.item,
                        "comando": comando,
                        "rc": 125,
                        "saida": (
                            "NAO EXECUTADA: a stack de containers nao subiu "
                            f"(docker compose up saiu {rc}). A saida dela esta em "
                            "`stack`."
                        ),
                    }
                )
                continue

            inicio = time.monotonic()
            prc, ptexto = _executa(
                comando, cwd=worktree, env={**env, **base}, limite=TEMPO_LIMITE_PROVA
            )
            doc["provas"].append(
                {
                    "id": prova.id,
                    "item": prova.item,
                    "comando": comando,
                    "rc": prc,
                    "segundos": round(time.monotonic() - inicio, 1),
                    "saida": ptexto,
                }
            )
    finally:
        # `-v` REMOVE O VOLUME, e e o que torna a stack efemera de verdade: sem
        # ele a rodada seguinte encontraria o `exercise_started` desta, e
        # `engine.start()` recusaria — o DEMO exige um exercicio que ainda nao
        # comecou.
        _executa(
            [*_compose(worktree), "down", "-v", "--remove-orphans"],
            cwd=worktree,
            env=env,
            limite=180,
        )
        # ESCRITO NO `finally`. Se o processo estiver saindo por excecao, a
        # ausencia do arquivo seria lida pelo auditor como "ainda nao rodou" —
        # e o verificador reprovaria pelo eixo errado, sem dizer o que houve.
        saida.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    reprovadas = [p for p in doc["provas"] if p.get("rc") != 0]
    for p in reprovadas:
        print(f"  prova `{p['id']}` reprovou (rc={p['rc']})", file=sys.stderr)
    return 1 if reprovadas else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Grava as provas de container do commit.")
    p.add_argument("--worktree", required=True, help="o checkout auditado")
    p.add_argument(
        "--python",
        default=sys.executable,
        help="interpretador que roda as provas — o do venv da auditoria",
    )
    p.add_argument("--saida", help=f"onde gravar (padrao: <worktree>/{EVIDENCIA})")
    a = p.parse_args(argv)

    worktree = Path(a.worktree).resolve()
    saida = Path(a.saida) if a.saida else worktree / EVIDENCIA
    return grava(worktree, a.python, saida)


if __name__ == "__main__":
    raise SystemExit(main())
