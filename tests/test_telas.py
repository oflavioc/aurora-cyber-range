"""As tres telas — a fronteira entre o que e publico e o que exige token.

POR QUE ESTE ARQUIVO NAO OLHA O BUNDLE
---------------------------------------
As telas sao artefato de build, e `range-core/web/dist/` esta no `.gitignore`.
Uma suite que exigisse o bundle construido dependeria do `npm` — e a saida usual
para isso, pular quando o artefato falta, e **pulo silencioso lido como verde**,
que e exatamente o que a P2-19 atacou.

Entao a divisao de trabalho e explicita, e cada nivel prova o que so ele pode:

    fonte           esta suite, sem `npm`: a fronteira publico/console
    artefato        `range-core/web/prova_do_build.sh`, no passo de CI
    gate do build   a prova negativa do proprio `tsc --noEmit`, no mesmo script

O QUE SE VARRE, E POR QUE A FONTE BASTA
----------------------------------------
`06` T6 e teste de PAYLOAD, e o payload continua sendo varrido em
`tests/test_projecoes.py`. O que se varre AQUI e outra coisa: **as duas telas
publicas nao podem conhecer o console**. Uma tela sem token com botao de disparo
poria o console na rede — e o bundle e uma transformacao determinista da fonte,
entao a propriedade que vale na fonte vale nele. A metade que a transformacao
poderia quebrar esta coberta no `prova_do_build.sh`, sobre o HTML construido.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from range_core.api import app as modulo_da_api

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "range-core" / "web"

#: O que uma tela PUBLICA nao pode mencionar. Sao os caminhos do console e o
#: cabecalho que os abre.
VOCABULARIO_DO_CONSOLE = ("/injects/", "/exercise/", "/session", "Authorization")

#: `src/` e compartilhado pelas tres telas, entao ele entra na varredura das
#: publicas: codigo de console em `src/` chegaria ao bundle do wallboard.
PUBLICAS = ("wallboard-shell", "participant-view", "src")

EXTENSOES = (".ts", ".tsx", ".html", ".css")


def _fontes(diretorio: Path) -> list[Path]:
    return sorted(
        caminho
        for caminho in diretorio.rglob("*")
        if caminho.is_file()
        and caminho.suffix in EXTENSOES
        and "node_modules" not in caminho.parts
        and "dist" not in caminho.parts
    )


class FronteiraDasTelasPublicas(unittest.TestCase):
    """As duas superficies que `05` §8 deixa sem autenticacao."""

    def test_as_telas_publicas_NAO_conhecem_o_console(self) -> None:
        for pasta in PUBLICAS:
            arquivos = _fontes(WEB / pasta)
            # ANTI-VACUIDADE: varredura sobre conjunto vazio passa sem olhar
            # nada, e foi assim que o probe do proprio verificador do cliente
            # achou o buraco na peca 6.
            self.assertTrue(arquivos, f"nenhuma fonte em range-core/web/{pasta}")
            for caminho in arquivos:
                texto = caminho.read_text(encoding="utf-8")
                for proibido in VOCABULARIO_DO_CONSOLE:
                    with self.subTest(arquivo=caminho.name, termo=proibido):
                        self.assertNotIn(
                            proibido,
                            texto,
                            "tela publica alcanca o console: uma tela sem token "
                            "com botao de disparo poria o console na rede",
                        )

    def test_o_CONSOLE_conhece_o_console_e_a_varredura_discrimina(self) -> None:
        """O par. Sem ele, a varredura de cima passaria por procurar errado.

        Se `VOCABULARIO_DO_CONSOLE` tivesse um termo com erro de digitacao, o
        teste acima ficaria verde para sempre. Este exige que os MESMOS termos
        apareçam onde eles tem de aparecer.
        """
        texto = "".join(
            caminho.read_text(encoding="utf-8") for caminho in _fontes(WEB / "gm-console")
        )
        for esperado in VOCABULARIO_DO_CONSOLE:
            with self.subTest(termo=esperado):
                self.assertIn(esperado, texto)

    def test_cada_tela_publica_consome_o_SEU_canal(self) -> None:
        """Tela que nao consome canal nenhum tambem passaria na varredura."""
        for pasta, canal in (
            ("wallboard-shell", "/ws/wallboard"),
            ("participant-view", "/ws/plateia"),
        ):
            texto = "".join(
                caminho.read_text(encoding="utf-8") for caminho in _fontes(WEB / pasta)
            )
            with self.subTest(tela=pasta):
                self.assertIn(canal, texto)


class RotasDasTelas(unittest.TestCase):
    """`GET /sala`, `GET /plateia` e `GET /console` — o mapeamento e a ausencia."""

    def setUp(self) -> None:
        self.cliente = TestClient(modulo_da_api.montar(None))

    def test_cada_rota_serve_A_SUA_tela(self) -> None:
        """Conteudos DISTINTOS: um mapeamento trocado passaria com todos iguais."""
        with tempfile.TemporaryDirectory() as bruto:
            raiz = Path(bruto)
            for tela in (
                modulo_da_api.TELA_DO_TELAO,
                modulo_da_api.TELA_DA_PLATEIA,
                modulo_da_api.TELA_DO_CONSOLE,
            ):
                (raiz / tela).mkdir(parents=True)
                (raiz / tela / "index.html").write_text(
                    f"<!doctype html><title>{tela}</title>", encoding="utf-8"
                )

            with mock.patch.object(modulo_da_api, "diretorio_das_telas", lambda: raiz):
                for caminho, tela in (
                    ("/sala", modulo_da_api.TELA_DO_TELAO),
                    ("/plateia", modulo_da_api.TELA_DA_PLATEIA),
                    ("/console", modulo_da_api.TELA_DO_CONSOLE),
                ):
                    with self.subTest(rota=caminho):
                        resposta = self.cliente.get(caminho)
                        self.assertEqual(resposta.status_code, 200)
                        self.assertIn(tela, resposta.text)

    def test_tela_nao_construida_RECUSA_alto_e_diz_como_construir(self) -> None:
        """Sem degradacao para outra coisa.

        Servir "alguma coisa" quando o bundle falta e como um telao mostra por
        meses a tela que o projeto ja decidiu jogar fora, sem nada acusar.
        """
        with tempfile.TemporaryDirectory() as bruto:
            with mock.patch.object(
                modulo_da_api, "diretorio_das_telas", lambda: Path(bruto)
            ):
                resposta = self.cliente.get("/sala")
            self.assertEqual(resposta.status_code, 503)
            self.assertIn(modulo_da_api.COMO_CONSTRUIR, resposta.json()["detail"])


class GateDoBuild(unittest.TestCase):
    """O build so e gate se `tsc --noEmit` rodar ANTES de `vite build`.

    `vite build` transpila com esbuild e **sai 0 com o TypeScript quebrado** —
    medido em `prova_do_build.sh`, que planta um erro de tipo e exige as duas
    saidas. O que esta classe guarda e mais barato e complementar: que a cadeia
    CI -> compose -> script continue ligada, e que ninguem simplifique o script
    de build para so `vite build` numa quarta-feira qualquer.
    """

    def test_o_script_de_build_comeca_por_tsc(self) -> None:
        manifesto = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
        self.assertTrue(
            manifesto["scripts"]["build"].startswith("tsc --noEmit &&"),
            "`vite build` sozinho sai 0 com o TypeScript quebrado: o passo de CI "
            "ficaria verde sobre um cliente que nao compila",
        )

    def test_o_CI_roda_o_build_pelo_compose_pinado(self) -> None:
        workflow = (RAIZ / ".github" / "workflows" / "invariants.yml").read_text(
            encoding="utf-8"
        )
        compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("--profile build run --rm web-build", workflow)
        self.assertIn("web-build:", compose)
        self.assertIn("prova_do_build.sh", compose)
        # O toolchain sob T15, como qualquer outra dependencia. A igualdade
        # entre CI e maquina do operador nao precisa de verificador aqui porque
        # nao ha DUAS declaracoes: o CI roda o proprio compose.
        self.assertIn("image: node:", compose)
        self.assertIn("@sha256:", compose.split("image: node:")[1].split("\n")[0])


if __name__ == "__main__":
    unittest.main()
