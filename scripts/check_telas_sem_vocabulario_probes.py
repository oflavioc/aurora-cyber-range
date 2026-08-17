#!/usr/bin/env python3
"""Prova negativa de `check_telas_sem_vocabulario.py`.

Um verificador que nunca reprovou contra um vazamento plantado prova que a
arvore esta limpa, e nao que ele enxerga. As onze direcoes abaixo sao as duas
metades: o que ele TEM de pegar, e o que ele NAO pode bloquear — porque
`docs/process/WORKFLOW.md` classifica bloqueio indevido como defeito, e um gate
que reprovasse `A` dentro de um bundle minificado seria abandonado no primeiro
dia.

O VOCABULARIO PLANTADO E SINTETICO, e isso nao e detalhe de estilo: a primeira
versao deste arquivo usava o nome de uma flag de verdade, e **o hook a recusou —
invariante 2, literal de flag no codigo**. Estava certo. O que o probe exercita e
o MECANISMO de casamento, que recebe o vocabulario por parametro; usar um nome
real nao acrescentaria nada e poria no repositorio exatamente a string que o
invariante 2 existe para manter fora dele. Terceira vez nesta fase que o hook
aponta para o desenho certo.

Stdlib pura. Roda no job `arquitetura`.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_telas_sem_vocabulario as alvo  # noqa: E402

#: Sintetico, e com forma que nao e de flag — ver o cabecalho.
NOME_DE_FLAG = "NOME-DE-FLAG-PLANTADO-PELO-PROBE"
TEXTO_DE_PLATEIA = "O portal plantado pelo probe esta indisponivel"
TITULO = "Inject plantado 01"
ID_CURTO = "A01"

FALHAS: list[str] = []


def confere(descricao: str, condicao: bool) -> None:
    print(("OK: " if condicao else "FALHOU: ") + descricao)
    if not condicao:
        FALHAS.append(descricao)


def _com_arquivo(conteudo: str, nome: str, vocabulario: set[str]) -> list[str]:
    with tempfile.TemporaryDirectory() as bruto:
        raiz = Path(bruto)
        caminho = raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        return alvo.verifica([caminho], vocabulario, raiz)


def main() -> int:
    # ------------------------------------------------------------------ pega
    confere(
        "reprovou nome de flag na FONTE",
        _com_arquivo(
            f'const f = "{NOME_DE_FLAG}";', "wallboard-shell/main.tsx", {NOME_DE_FLAG}
        ),
    )
    confere(
        "reprovou texto de plateia no BUNDLE",
        _com_arquivo(
            f'<html><script>const t="{TEXTO_DE_PLATEIA}"</script></html>',
            "dist/wallboard-shell/index.html",
            {TEXTO_DE_PLATEIA},
        ),
    )
    confere(
        "reprovou titulo operacional, que e identidade de cenario",
        _com_arquivo(f'x("{TITULO}")', "gm-console/main.tsx", {TITULO}),
    )
    confere(
        "reprovou id de inject ENTRE ASPAS, no bundle",
        _com_arquivo(f'const i = "{ID_CURTO}";', "dist/gm-console/index.html", {ID_CURTO}),
    )
    confere(
        "reprovou id de inject entre crases",
        _com_arquivo(f"const i = `{ID_CURTO}`;", "gm-console/main.tsx", {ID_CURTO}),
    )
    confere(
        "reprovou vazamento no CSS, que tambem vai ao navegador",
        _com_arquivo(
            f'.x::after {{ content: "{TEXTO_DE_PLATEIA}"; }}',
            "src/estilo.css",
            {TEXTO_DE_PLATEIA},
        ),
    )

    # ------------------------------------------- nao bloqueia o que nao deve
    confere(
        "NAO bloqueou id curto SEM aspas — o limite declarado",
        not _com_arquivo(f"var {ID_CURTO}x = 1;", "dist/gm-console/index.html", {ID_CURTO}),
    )
    confere(
        "NAO bloqueou termo de 1 caractere (o `linha: A` do fixture)",
        not _com_arquivo(
            "const A = 1; const b = 'A';", "wallboard-shell/main.tsx", {"A"}
        ),
    )
    confere(
        "NAO bloqueou arquivo de cliente sem vocabulario nenhum",
        not _com_arquivo("export const x = 1;", "src/canal.ts", {NOME_DE_FLAG}),
    )

    # ------------------------------------------------------- anti-vacuidade
    with tempfile.TemporaryDirectory() as bruto:
        vazio = Path(bruto)
        original_web, original_bundle = alvo.WEB, alvo.BUNDLE
        original_flags = alvo.nomes_de_flag
        original_cenario = alvo.vocabulario_de_cenario
        try:
            alvo.WEB = vazio
            alvo.BUNDLE = vazio / "dist"
            confere("recusou (rc=2) diretorio de cliente VAZIO", alvo.main([]) == 2)

            alvo.WEB = original_web
            alvo.nomes_de_flag = lambda _raiz: set()
            alvo.vocabulario_de_cenario = lambda _raiz: set()
            confere("recusou (rc=2) vocabulario VAZIO", alvo.main([]) == 2)

            alvo.nomes_de_flag = original_flags
            alvo.vocabulario_de_cenario = original_cenario
            alvo.BUNDLE = vazio / "dist"
            confere(
                "recusou (rc=2) `--exige-bundle` sem bundle construido",
                alvo.main(["--exige-bundle"]) == 2,
            )
        finally:
            alvo.WEB, alvo.BUNDLE = original_web, original_bundle
            alvo.nomes_de_flag = original_flags
            alvo.vocabulario_de_cenario = original_cenario

    # ----------------------------------------------------------- arvore real
    confere("a arvore real passa (rc=0)", alvo.main([]) == 0)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} direcoes falharam.", file=sys.stderr)
        return 1
    print(
        "check_telas_sem_vocabulario.py pega nome de flag, texto e id de inject "
        "na fonte E no bundle, e nao bloqueia id curto sem aspas nem termo de um "
        "caractere."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
