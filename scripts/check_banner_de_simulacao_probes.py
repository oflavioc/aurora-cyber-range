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

        # OS DOIS EIXOS DA FASE 9, injetados em TODOS os casos.
        #
        # Sem injetar, os `None` resolveriam para o contrato e o `evidence/`
        # REAIS — os casos antigos passariam a depender da arvore, e um probe
        # que le a arvore que ele existe para julgar deixa de isolar o eixo que
        # mede. A mesma razao pela qual `texto_normativo` resolve o global na
        # CHAMADA e nao no `def`.
        contrato_ok = _arquivo(
            raiz, "contrato.yaml", f"x-aurora-security-constraints:\n  banner_text: '{BANNER}'\n"
        )
        evidencia_ok = raiz / "evidence"
        _arquivo(raiz, "evidence/vpn.log", f"# {BANNER}\nT-9d user=svc\n")
        # O MANIFESTO DA FIXTURE VALIDA GANHOU O BANNER — B1 da 4a auditoria.
        # Ele nascera sem, e passava porque o verificador o ISENTAVA por nome de
        # arquivo. Sem a isencao, uma fixture "valida" sem banner faria o eixo da
        # combinacao correta reprovar — e o probe acusou na primeira execucao,
        # que e o comportamento certo dele.
        _arquivo(
            raiz,
            "evidence/MANIFEST.json",
            '{"_banner": "%s", "sources": []}\n' % BANNER,
        )

        def verifica(banner, fonte, telas, bundles, contrato=None, evidencia=None):
            """Os dois eixos novos com fixture valida, salvo quando o caso os ataca."""
            return alvo.verifica(
                banner,
                fonte,
                telas,
                bundles,
                contrato_ok if contrato is None else contrato,
                evidencia_ok if evidencia is None else evidencia,
            )

        confere(
            "reprovou componente SEM o texto normativo",
            bool(
                verifica(
                    BANNER,
                    _arquivo(raiz, "outro.tsx", 'export const T = "AMBIENTE DE TESTE";'),
                    [tela_ok],
                    [],
                )
            ),
        )
        confere(
            "reprovou tela que NAO renderiza o componente",
            bool(verifica(BANNER, componente, [tela_sem], [])),
        )
        confere(
            "reprovou BUNDLE sem o banner, com a fonte correta — a direcao que vale",
            bool(verifica(BANNER, componente, [tela_ok], [bundle_sem])),
        )
        confere(
            "reprovou componente ausente do disco",
            bool(verifica(BANNER, raiz / "nao-existe.tsx", [tela_ok], [])),
        )
        confere(
            "reprovou bundle ausente quando ele e exigido",
            bool(verifica(BANNER, componente, [tela_ok], [raiz / "dist/nao-existe.html"])),
        )
        confere(
            "NAO reprovou a combinacao correta",
            not verifica(BANNER, componente, [tela_ok], [bundle_ok]),
        )

        # ANTI-VACUIDADE: banner vazio faz os eixos de SUBSTRING passarem,
        # porque `"" in qualquer_texto` e sempre verdadeiro — e e por isso que o
        # `main` sai com rc=2 quando nao consegue extrair o texto, em vez de
        # seguir verificando.
        #
        # O EIXO DO CONTRATO NAO E VACUO, e a diferenca e de operador: ele
        # compara por IGUALDADE (`do_contrato != banner`), entao banner vazio
        # contra contrato preenchido ACUSA. Para medir a vacuidade que sobra, o
        # caso zera os dois lados — senao mediria o eixo novo, que nao e o
        # assunto aqui.
        contrato_vazio = _arquivo(
            raiz, "contrato_zero.yaml", "x-aurora-security-constraints:\n  banner_text: ''\n"
        )
        # O EIXO DO MANIFESTO TAMBEM NAO E VACUO, pela mesma razao do contrato e
        # com a mesma consequencia para este caso: ele compara `_banner` por
        # IGUALDADE, entao banner vazio contra manifesto preenchido ACUSA.
        #
        # Zerar os dois lados e o que mantem este caso medindo o que ele diz
        # medir — a vacuidade que sobra nos eixos de SUBSTRING. Sem isto ele
        # passaria a medir o eixo do manifesto, que nao e o assunto aqui. B1 da
        # 4a auditoria: o manifesto deixou de ser isento.
        evidencia_zero = raiz / "evidence_zero"
        _arquivo(raiz, "evidence_zero/vpn.log", "# \nT-9d user=svc\n")
        _arquivo(raiz, "evidence_zero/MANIFEST.json", '{"_banner": ""}\n')
        confere(
            "com banner VAZIO, os eixos de substring passariam — por isso o rc=2",
            not verifica(
                "",
                componente,
                [tela_ok],
                [bundle_sem],
                contrato=contrato_vazio,
                evidencia=evidencia_zero,
            ),
        )
        confere(
            "o eixo do CONTRATO nao e vacuo: banner vazio contra contrato cheio acusa",
            bool(verifica("", componente, [tela_ok], [bundle_ok])),
        )

        # ------------------------------------------------------------------
        # O QUARTO EIXO — `05` §4 x contrato de evidencia. H2 da Fase 9.
        # ------------------------------------------------------------------
        confere(
            "reprovou contrato cujo `banner_text` DIVERGE de `05` §4",
            bool(
                verifica(
                    BANNER,
                    componente,
                    [tela_ok],
                    [bundle_ok],
                    contrato=_arquivo(
                        raiz,
                        "contrato_divergente.yaml",
                        "x-aurora-security-constraints:\n  banner_text: 'AMBIENTE DE TESTE'\n",
                    ),
                )
            ),
        )
        confere(
            "reprovou contrato SEM `banner_text` — o motor ficaria sem texto",
            bool(
                verifica(
                    BANNER,
                    componente,
                    [tela_ok],
                    [bundle_ok],
                    contrato=_arquivo(raiz, "contrato_vazio.yaml", "x-aurora: {}\n"),
                )
            ),
        )
        confere(
            "reprovou contrato ausente do disco",
            bool(
                verifica(
                    BANNER, componente, [tela_ok], [bundle_ok],
                    contrato=raiz / "nao-existe.yaml",
                )
            ),
        )
        confere(
            "extracao do contrato devolve None quando a chave some",
            alvo.texto_do_contrato(_arquivo(raiz, "c2.yaml", "outra: coisa\n")) is None,
        )

        # ------------------------------------------------------------------
        # O QUINTO EIXO — a classe `evidencia`, agora COBERTA. M1 da Fase 9.
        # ------------------------------------------------------------------
        sem_banner = raiz / "evidence_ruim"
        _arquivo(raiz, "evidence_ruim/vpn.log", "T-9d user=svc\n")
        confere(
            "reprovou arquivo de evidencia SEM banner",
            bool(verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=sem_banner)),
        )

        rodape = raiz / "evidence_rodape"
        _arquivo(raiz, "evidence_rodape/vpn.log", f"T-9d user=svc\n# {BANNER}\n")
        confere(
            "reprovou banner no RODAPE — a posicao e o requisito",
            bool(verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=rodape)),
        )

        # A ANTI-VACUIDADE DESTE EIXO, e ela e a que importa: cobertura
        # declarada sem objeto e skip silencioso, que a R10 §2 chama de FAIL.
        confere(
            "reprovou diretorio de evidencia AUSENTE — cobertura sem objeto",
            bool(
                verifica(
                    BANNER, componente, [tela_ok], [bundle_ok],
                    evidencia=raiz / "evidence_inexistente",
                )
            ),
        )
        # ------------------------------------------------------------------
        # O MANIFESTO DEIXOU DE SER ISENTO — B1 da 4a auditoria.
        #
        # O caso anterior aqui dizia "reprovou diretorio SO com MANIFEST — o
        # indice nao e artefato", e ele codificava a isencao: com
        # `SEM_BANNER = {"MANIFEST.json"}`, um diretorio so com manifesto nao
        # tinha candidato nenhum e reprovava por ANTI-VACUIDADE, nao por banner.
        #
        # Hoje o manifesto E candidato, e os tres casos abaixo separam o que
        # aquele nao distinguia: sem a chave, com a chave em lugar errado, e
        # formato que o verificador nao sabe julgar.
        # ------------------------------------------------------------------
        so_manifesto = raiz / "evidence_manifesto_sem_banner"
        _arquivo(raiz, "evidence_manifesto_sem_banner/MANIFEST.json", '{"sources": []}\n')
        confere(
            "reprovou MANIFEST.json SEM `_banner` — o defeito exato do B1",
            bool(
                verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=so_manifesto)
            ),
        )

        chave_tardia = raiz / "evidence_manifesto_chave_tardia"
        _arquivo(
            raiz,
            "evidence_manifesto_chave_tardia/MANIFEST.json",
            '{"sources": [], "_banner": "%s"}\n' % BANNER,
        )
        confere(
            "reprovou `_banner` que NAO e a primeira chave — a posicao e o requisito",
            bool(
                verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=chave_tardia)
            ),
        )

        formato_novo = raiz / "evidence_formato_novo"
        _arquivo(raiz, "evidence_formato_novo/relatorio.pdf", "%PDF-1.4\n")
        confere(
            "reprovou formato SEM forma de banner declarada — nao saber julgar "
            "nao e aprovar",
            bool(
                verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=formato_novo)
            ),
        )

        manifesto_ok = raiz / "evidence_manifesto_ok"
        _arquivo(
            raiz,
            "evidence_manifesto_ok/MANIFEST.json",
            '{"_banner": "%s", "sources": []}\n' % BANNER,
        )
        confere(
            "APROVOU o manifesto com `_banner` na primeira chave — sem este par "
            "os tres acima passariam num verificador que recusa tudo",
            not verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=manifesto_ok),
        )

        vazio = raiz / "evidence_vazio"
        vazio.mkdir()
        confere(
            "reprovou diretorio de evidencia VAZIO — cobertura sem objeto",
            bool(verifica(BANNER, componente, [tela_ok], [bundle_ok], evidencia=vazio)),
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
