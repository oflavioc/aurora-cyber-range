"""Todo `.yaml` de dado de execucao entra na instalacao — B3 da sexta auditoria.

O QUE ESTA SUITE PROVA
----------------------
Que cada `.yaml` sob as arvores EMBARCADAS — `range-core/` e `domains/` — esta
coberto por uma entrada de `[tool.setuptools.package-data]`, e que o pacote que o
contem esta em `packages`. As duas metades, porque falham diferente: pacote
ausente some inteiro; `package-data` ausente leva os `.py` e deixa o dado para
tras.

POR QUE ELA EXISTE, E O QUE CUSTOU NAO EXISTIR
-----------------------------------------------
`range_core = ["*.yaml"]` cobre a RAIZ de `range-core/`, e nao os subpacotes:
globs de `package-data` sao relativos ao diretorio de cada pacote. As nove
rubricas de `range-core/rubrics/` — a peca 1 desta fase — ficaram de fora da
imagem, e o container morria no boot com `RubricLibraryError: nenhuma rubrica`.

Custou uma rodada de auditoria inteira, e o sintoma chegou a tres passos da
causa: `container range-api exited (1)`.

POR QUE TESTE E NAO VERIFICADOR
--------------------------------
A pergunta e sobre DOIS ARQUIVOS DA ARVORE — `pyproject.toml` e o que existe em
disco — e nao exige a aplicacao instalada. Roda em segundos, para quem esta
editando, e e onde um `.yaml` novo aparece.

E ELA NAO SUBSTITUI O CONTAINER, e isso esta dito: com instalacao EDITAVEL o
`.pth` poe a raiz no `sys.path`, entao NADA que rode na arvore prova
empacotamento. O que esta suite prova e que a DECLARACAO cobre o que existe; que
a declaracao funciona, so o container prova — e e por isso que os dois existem.

O UNIVERSO E DECLARADO, E NAO INFERIDO
---------------------------------------
`NAO_EMBARCADOS` lista o que fica de fora com motivo. Sem essa lista, a suite
teria de adivinhar a intencao de cada arquivo — e adivinhar significa passar por
omissao no dia em que alguem acrescentar um `.yaml` que ninguem le.
"""

from __future__ import annotations

import fnmatch
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: O que NAO entra na instalacao, com motivo. Caminho relativo a raiz, POSIX.
NAO_EMBARCADOS: dict[str, str] = {
    "domains/flags_pendentes.yaml": (
        "registro de flags citadas na spec e ainda sem adapter. E lido por "
        "`scripts/check_spec_flags.py`, que roda no CI sobre a arvore — nunca "
        "em execucao."
    ),
    "domains/prontus/flags.yaml": (
        "o `prontus` e STUB DECLARADO: duas flags e um documento, sem modelo, "
        "tela nem cenario. Ele existe para a fronteira arquitetural ser "
        "verificavel, e nao ha servico que o carregue."
    ),
}


def _pyproject() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as arquivo:
        return tomllib.load(arquivo)


def _diretorio_do_pacote(pacote: str, package_dir: dict[str, str]) -> Path:
    """`range_core.rubrics` -> `range-core/rubrics`, pelo mapa de `package-dir`."""
    partes = pacote.split(".")
    raiz = package_dir.get(partes[0], partes[0])
    return REPO_ROOT.joinpath(raiz, *partes[1:])


class TodoYamlEmbarcavelEstaDeclarado(unittest.TestCase):
    """As duas metades: o pacote em `packages`, e o arquivo em `package-data`."""

    def setUp(self) -> None:
        config = _pyproject()["tool"]["setuptools"]
        self.packages: list[str] = config["packages"]
        self.package_dir: dict[str, str] = config.get("package-dir", {})
        self.package_data: dict[str, list[str]] = config.get("package-data", {})
        self.diretorios = {
            _diretorio_do_pacote(p, self.package_dir).resolve(): p
            for p in self.packages
        }

    def _yamls(self) -> list[Path]:
        achados: list[Path] = []
        for raiz in ("range-core", "domains"):
            achados.extend(sorted((REPO_ROOT / raiz).rglob("*.yaml")))
        return achados

    def test_todo_yaml_esta_coberto_ou_declarado_fora(self):
        descobertos: list[str] = []
        for caminho in self._yamls():
            relativo = caminho.relative_to(REPO_ROOT).as_posix()
            if relativo in NAO_EMBARCADOS:
                continue

            pacote = self.diretorios.get(caminho.parent.resolve())
            self.assertIsNotNone(
                pacote,
                f"{relativo}: o diretorio que o contem nao e um pacote declarado "
                "em `packages`. Na instalacao ele nao existe — declare o pacote, "
                "ou registre o arquivo em NAO_EMBARCADOS com o motivo.",
            )

            globs = self.package_data.get(pacote) or []
            if not any(fnmatch.fnmatch(caminho.name, g) for g in globs):
                descobertos.append(f"{relativo} (pacote `{pacote}`)")

        self.assertEqual(
            descobertos,
            [],
            "`.yaml` sem entrada em `[tool.setuptools.package-data]`: a "
            "instalacao leva os `.py` e deixa o dado para tras, e o sintoma so "
            "aparece no container — foi o B3 da sexta auditoria, com as nove "
            "rubricas de `range_core.rubrics`.",
        )

    def test_a_biblioteca_de_rubricas_esta_coberta(self):
        """O caso do B3, nomeado — controle contra a checagem generica passar vazia."""
        globs = self.package_data.get("range_core.rubrics") or []
        self.assertTrue(
            any(fnmatch.fnmatch("incident_triage.v2.yaml", g) for g in globs),
            "`range_core.rubrics` sem `*.yaml` em `package-data`: `load_library()` "
            "levanta `RubricLibraryError: nenhuma rubrica` no boot do container, e "
            "todo pack passa a ser recusado por 'rubrica ausente' — a mensagem "
            "errada para o defeito certo.",
        )

    def test_a_varredura_NAO_e_vazia(self):
        """Sem isto, um `rglob` que deixasse de achar arquivos passaria por vacuidade.

        E o mesmo eixo que a prova negativa de `check_hooks_com_emissor` cobre: a
        checagem que nao tem o que conferir nao pode sair verde.
        """
        self.assertGreaterEqual(len(self._yamls()), 10)

    def test_NAO_EMBARCADOS_descreve_o_que_existe(self):
        """Entrada que sobra e lista envelhecida — e lista envelhecida mente."""
        sumidos = [
            relativo
            for relativo in NAO_EMBARCADOS
            if not (REPO_ROOT / relativo).is_file()
        ]
        self.assertEqual(sumidos, [], "entradas de NAO_EMBARCADOS sem arquivo")


if __name__ == "__main__":
    unittest.main()
