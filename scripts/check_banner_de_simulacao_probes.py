#!/usr/bin/env python3
"""Prova negativa de `check_banner_de_simulacao.py`.

O verificador nasceu de um BLOCKER: `05` §4 exige o banner em toda tela, a Fase 4
entregou tres sem ele, e **nenhum verificador cobria a secao**. Um verificador
novo que nunca reprovou prova que a arvore esta limpa, e nao que ele enxerga —
que e exatamente como a §4 atravessou sete pecas.

A direcao 3 e a que vale mais: **a fonte pode ter o banner e o BUNDLE nao**. O
bundle e o que chega ao navegador, e uma checagem que so olhasse `.tsx` diria
"coberto" sobre um telao sem banner.

Stdlib pura. Roda no job `arquitetura`.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_banner_de_simulacao as alvo  # noqa: E402

BANNER = "AMBIENTE SIMULADO — DADOS FICTÍCIOS"

FALHAS: list[str] = []


def confere(descricao: str, condicao: bool) -> None:
    print(("OK: " if condicao else "FALHOU: ") + descricao)
    if not condicao:
        FALHAS.append(descricao)


def _arquivo(raiz: Path, nome: str, conteudo: str) -> Path:
    caminho = raiz / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def main() -> int:
    with tempfile.TemporaryDirectory() as bruto:
        raiz = Path(bruto)
        componente = _arquivo(raiz, "banner.tsx", f'export const T = "{BANNER}";')
        tela_ok = _arquivo(raiz, "telas/main.tsx", "<BannerDeSimulacao />")
        tela_sem = _arquivo(raiz, "telas/sem.tsx", "<div>telao</div>")
        bundle_ok = _arquivo(raiz, "dist/index.html", f"<html>{BANNER}</html>")
        bundle_sem = _arquivo(raiz, "dist/sem.html", "<html>telao</html>")

        confere(
            "reprovou componente SEM o texto normativo",
            bool(
                alvo.verifica(
                    BANNER,
                    _arquivo(raiz, "outro.tsx", 'export const T = "AMBIENTE DE TESTE";'),
                    [tela_ok],
                    [],
                )
            ),
        )
        confere(
            "reprovou tela que NAO renderiza o componente",
            bool(alvo.verifica(BANNER, componente, [tela_sem], [])),
        )
        confere(
            "reprovou BUNDLE sem o banner, com a fonte correta — a direcao que vale",
            bool(alvo.verifica(BANNER, componente, [tela_ok], [bundle_sem])),
        )
        confere(
            "reprovou componente ausente do disco",
            bool(alvo.verifica(BANNER, raiz / "nao-existe.tsx", [tela_ok], [])),
        )
        confere(
            "reprovou bundle ausente quando ele e exigido",
            bool(alvo.verifica(BANNER, componente, [tela_ok], [raiz / "dist/nao-existe.html"])),
        )
        confere(
            "NAO reprovou a combinacao correta",
            not alvo.verifica(BANNER, componente, [tela_ok], [bundle_ok]),
        )

        # ANTI-VACUIDADE: banner vazio faria todos os eixos passarem, porque
        # `"" in qualquer_texto` e sempre verdadeiro.
        confere(
            "com banner VAZIO, a combinacao errada passaria — por isso o rc=2",
            not alvo.verifica("", componente, [tela_ok], [bundle_sem]),
        )

        spec_sem_bloco = _arquivo(raiz, "05.md", "## 4. Banner obrigatorio\n\nsem bloco\n")
        confere(
            "extracao devolve vazio quando a §4 muda de forma",
            alvo.texto_normativo(spec_sem_bloco) == "",
        )

        original = alvo.SPEC
        try:
            alvo.SPEC = spec_sem_bloco
            confere("recusou (rc=2) quando o texto normativo nao pode ser extraido",
                    alvo.main([]) == 2)
        finally:
            alvo.SPEC = original

    confere(
        "o texto extraido da spec real nao e vazio",
        alvo.texto_normativo() != "",
    )
    confere("a arvore real passa (rc=0)", alvo.main([]) == 0)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} direcoes falharam.", file=sys.stderr)
        return 1
    print(
        "check_banner_de_simulacao.py reprova fonte sem o texto, tela sem o "
        "componente e BUNDLE sem o banner, e recusa quando a §4 deixa de ser "
        "legivel — que e o caso em que tudo passaria."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
