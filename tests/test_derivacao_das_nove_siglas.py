"""`06` T10 — a derivacao das nove siglas contra o criterio de `00` §3.2.

O CRITERIO CLASSIFICA; A TABELA REGISTRA O QUE ELE CLASSIFICOU
---------------------------------------------------------------
`03` §3 diz por extenso que as tabelas da secao *"sao o resultado de aplicar o
criterio de `00_MASTER_SPEC.md` §3.2 as nove siglas de v1. Nao sao a definicao da
particao e nao podem ser lidas como lista de isencoes"*. T10 fecha:
**divergencia reprova esta tabela, nunca o criterio.**

POR QUE ISTO NAO E TAUTOLOGIA
------------------------------
Reescrever em Python a resposta de cada sigla e depois compara-la com a tabela
compararia a tabela consigo mesma — o defeito que `check_volumes_da_linha_b`
existe para nao repetir, e que o M2 da Fase 5 pegou.

O que se faz aqui e outra coisa: a §3.0 **publica as tres respostas**, uma por
coluna, e a §3.2 do `00` publica a **conjuncao**. Este teste aplica a conjuncao
as colunas e exige que o resultado seja o da ultima coluna. As entradas sao da
spec; a operacao e da spec; o que se verifica e que a tabela e consistente com o
proprio criterio que ela afirma aplicar.

Editar `Resultado` sem editar as colunas reprova. Editar uma coluna sem editar o
resultado reprova. Foi assim que `separate_incident_declared` caiu de dois
registros fechados: os dois tinham enumeracao e nenhum tinha criterio.

A TERCEIRA DIRECAO — A TABELA CONTRA O CODIGO
----------------------------------------------
As nove siglas da tabela sao cruzadas com as que os computadores de fato
produzem. Sem isso, sigla nova entraria na spec sem metrica que a leia — ou o
codigo pararia de emitir uma sem que a tabela notasse.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "spec" / "03_EXERCISE_DESIGN.md"

#: As tres respostas que uma celula de condicao pode carregar.
SIM = "sim"
NAO = "nao"
NAO_ALCANCADA = "nao_se_alcanca"
NAO_CLASSIFICA = "nao_se_classifica"

PAREADA = "pareada"
SIMPLES = "simples"
METADE = "metade_de_verificacao"


def _condicao(celula: str) -> str:
    """A resposta de uma celula de condicao, ignorando a justificativa.

    A justificativa vem depois de um travessao e e prosa; o que decide sao as
    primeiras palavras. `nao se classifica` e conferido ANTES de `nao`, porque o
    segundo e prefixo do primeiro e a ordem inversa classificaria as tres
    metades de verificacao como respostas negativas.
    """
    limpa = celula.replace("*", "").strip().lower()
    if "nao se classifica" in limpa:
        return NAO_CLASSIFICA
    if "nao se alcanca" in limpa:
        return NAO_ALCANCADA
    if limpa == "—" or limpa == "-":
        return NAO_CLASSIFICA
    if limpa.startswith("sim"):
        return SIM
    if limpa.startswith("nao"):
        return NAO
    raise AssertionError(
        f"celula de condicao nao reconhecida: {celula!r}. A forma da tabela de "
        "`03` §3.0 mudou, e este teste precisa acompanhar — nao passar por cima."
    )


def _resultado(celula: str) -> str:
    limpa = celula.replace("*", "").strip().lower()
    if limpa.startswith("pareada"):
        return PAREADA
    if limpa.startswith("simples"):
        return SIMPLES
    if limpa.startswith("metade de verificacao"):
        return METADE
    raise AssertionError(
        f"celula de resultado nao reconhecida: {celula!r}. A forma da tabela de "
        "`03` §3.0 mudou."
    )


def _sem_acento(texto: str) -> str:
    for de, para in (
        ("ã", "a"), ("á", "a"), ("â", "a"), ("é", "e"), ("ê", "e"),
        ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c"),
    ):
        texto = texto.replace(de, para).replace(de.upper(), para.upper())
    return texto


def tabela() -> list[dict]:
    """As linhas da tabela de derivacao de `03` §3.0, lidas do documento.

    A extracao ancora no cabecalho da secao e para na proxima. Ancorar no
    documento inteiro pegaria as OUTRAS tabelas de `03` §3 — a dos pares e a das
    simples —, que tem colunas diferentes e reprovariam por forma.
    """
    texto = SPEC.read_text(encoding="utf-8")
    inicio = texto.index("### 3.0 Derivação das nove siglas")
    fim = texto.index("####", inicio)
    bloco = texto[inicio:fim]

    linhas = []
    for linha in bloco.splitlines():
        if not linha.startswith("| **"):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) != 6:
            raise AssertionError(
                f"linha da tabela com {len(celulas)} colunas, e a tabela tem 6: "
                f"{linha!r}"
            )
        sigla = celulas[0].replace("*", "").strip()
        linhas.append(
            {
                "sigla": sigla,
                "instante": celulas[1],
                "condicoes": [_condicao(_sem_acento(c)) for c in celulas[2:5]],
                "resultado": _resultado(_sem_acento(celulas[5])),
            }
        )
    return linhas


class AConjuncaoReproduzATabela(unittest.TestCase):
    """`00` §3.2: *"a conjuncao e o criterio"* — as tres ao mesmo tempo."""

    def setUp(self) -> None:
        self.linhas = tabela()

    def test_a_tabela_tem_as_nove_siglas(self):
        self.assertEqual(len(self.linhas), 9)
        self.assertEqual(
            {l["sigla"] for l in self.linhas},
            {"TTCD", "TTRD", "TTID", "TTA", "TTT", "TTCM", "TTCV", "TTRV", "TTIV"},
        )

    def test_pareada_exatamente_quando_as_tres_sao_sim(self):
        """O criterio, literal. Falhando qualquer uma, a metrica e simples."""
        for linha in self.linhas:
            if linha["resultado"] == METADE:
                continue
            with self.subTest(sigla=linha["sigla"]):
                todas_sim = all(c == SIM for c in linha["condicoes"])
                esperado = PAREADA if todas_sim else SIMPLES
                self.assertEqual(
                    linha["resultado"],
                    esperado,
                    f"{linha['sigla']}: as colunas dizem {linha['condicoes']} e o "
                    f"resultado diz {linha['resultado']}. A conjuncao de `00` §3.2 "
                    f"produz {esperado}. Divergencia reprova A TABELA, nunca o "
                    "criterio — `06` T10.",
                )

    def test_nao_se_alcanca_so_aparece_depois_de_um_nao(self):
        """A conjuncao curto-circuita, e a tabela tem de refletir isso.

        `(nao se alcanca)` sem um `nao` antes seria coluna nao respondida
        parecendo coluna dispensada — e a dispensa e o que permite ler a linha
        sem verificar a condicao.
        """
        for linha in self.linhas:
            if linha["resultado"] == METADE:
                continue
            with self.subTest(sigla=linha["sigla"]):
                ja_falhou = False
                for posicao, condicao in enumerate(linha["condicoes"], start=1):
                    if condicao == NAO_ALCANCADA:
                        self.assertTrue(
                            ja_falhou,
                            f"{linha['sigla']}: a condicao ({posicao}) diz "
                            "'(nao se alcanca)' sem que nenhuma anterior tenha "
                            "falhado. A conjuncao so dispensa o resto depois de "
                            "um `nao`.",
                        )
                    if condicao == NAO:
                        ja_falhou = True

    def test_as_metades_de_verificacao_nao_se_classificam_pelo_criterio(self):
        """Elas nao sao declaracao: o criterio nao tem o que julgar nelas."""
        for linha in self.linhas:
            if linha["resultado"] != METADE:
                continue
            with self.subTest(sigla=linha["sigla"]):
                self.assertEqual(
                    linha["condicoes"], [NAO_CLASSIFICA] * 3,
                    f"{linha['sigla']} e metade de verificacao e tem coluna de "
                    "condicao respondida. Ou ela se classifica, ou nao — as duas "
                    "leituras nao cabem na mesma linha.",
                )

    def test_toda_metade_de_verificacao_aponta_para_uma_pareada(self):
        """*"metade de verificacao de X"* — e X precisa ser pareada de fato."""
        pareadas = {l["sigla"] for l in self.linhas if l["resultado"] == PAREADA}
        texto = SPEC.read_text(encoding="utf-8")
        inicio = texto.index("### 3.0 Derivação das nove siglas")
        bloco = texto[inicio : texto.index("####", inicio)]

        for linha in bloco.splitlines():
            casado = re.search(r"metade de verificação de `(\w+)`", linha)
            if casado is None:
                continue
            with self.subTest(linha=linha[:20]):
                self.assertIn(casado.group(1), pareadas)

    def test_toda_pareada_declara_a_metade_que_a_completa(self):
        """`**pareada** → `TTCV`` — o par tem de nomear a outra metade."""
        siglas = {l["sigla"] for l in self.linhas}
        texto = SPEC.read_text(encoding="utf-8")
        inicio = texto.index("### 3.0 Derivação das nove siglas")
        bloco = texto[inicio : texto.index("####", inicio)]

        apontadas = set(re.findall(r"\*\*pareada\*\* → `(\w+)`", bloco))
        self.assertEqual(len(apontadas), 3)
        self.assertTrue(apontadas <= siglas)


class ATabelaContraOCodigo(unittest.TestCase):
    """As siglas da spec cruzadas com as que os computadores produzem.

    Sem esta direcao, sigla nova entraria na tabela sem metrica que a leia, e
    ninguem saberia ate o AAR imprimir uma linha vazia.
    """

    def setUp(self) -> None:
        self.siglas_da_spec = {l["sigla"] for l in tabela()}

    def test_as_siglas_do_computador_da_declaracao_estao_na_tabela(self):
        from range_core.metrics.declaracao import computa  # noqa: F401

        producidas = {"TTCD", "TTRD", "TTID", "TTA", "TTT", "TTCM"}
        self.assertTrue(producidas <= self.siglas_da_spec)

    def test_as_siglas_do_computador_da_verificacao_estao_na_tabela(self):
        from range_core.metrics.verificacao import SIGLA_POR_PREDICADO

        self.assertTrue(set(SIGLA_POR_PREDICADO.values()) <= self.siglas_da_spec)

    def test_a_unica_sigla_sem_computador_e_ttiv_e_ela_e_da_peca_6(self):
        """A fronteira do plano da fase, cobrada em vez de declarada.

        `TTIV` e a unica das nove sem computador nesta peca, e o plano da Fase 6
        a poe na peca 6 — *"Calibracao: Brier no escopo revisado, sinais, `TTIV`
        por limiar"*. Quando a peca 6 fechar, este teste reprova, e e assim que
        se descobre que a fronteira foi cruzada.
        """
        from range_core.metrics.verificacao import SIGLA_POR_PREDICADO

        com_computador = {"TTCD", "TTRD", "TTID", "TTA", "TTT", "TTCM"} | set(
            SIGLA_POR_PREDICADO.values()
        )
        self.assertEqual(
            self.siglas_da_spec - com_computador,
            {"TTIV"},
            "a lista de siglas sem computador mudou. Se `TTIV` ganhou o dele na "
            "peca 6, atualize este teste; se outra sigla ficou sem, ha metrica "
            "na spec que ninguem calcula.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
