"""`SINCE_SELF` tem UMA origem — e as duas guardas seguem o contrato, nao um literal.

O DEFEITO QUE ESTE MODULO EXISTE PARA IMPEDIR
----------------------------------------------
`SINCE_SELF = "self"` esteve definido DUAS vezes:

    range-core/engine/loader/pack_loader.py   a guarda de CARGA
    range-core/engine/verificacao.py          o AVALIADOR, segunda linha

Sem import entre elas e sem verificador cruzando. As duas concordavam por
COINCIDENCIA — os dois comentarios citavam `03` §3.1, e a unica guarda era
lembrar de editar as duas. Mudar uma e esquecer a outra faz carga e avaliacao
discordarem sobre o mesmo campo: pack recusado no boot que o avaliador
aceitaria, ou o inverso. E a classe D4.

POR QUE A SEGUNDA COPIA ERA A MAIS PERIGOSA, e nao a menos
------------------------------------------------------------
O docstring de `avalia` declara a guarda do avaliador como SEGUNDA LINHA, para
*"predicado que veio por outro caminho"*. Uma copia na linha que existe
justamente para o caso nao previsto e a que pode envelhecer sem ninguem notar:
ela so dispara quando as duas primeiras ja falharam, e ai ninguem esta olhando.

O QUE ESTE TESTE AFIRMA, E POR QUE NAO BASTA AFIRMAR A CONCORDANCIA
--------------------------------------------------------------------
Um teste que so verificasse `pack_loader.SINCE_SELF == verificacao.SINCE_SELF`
passaria HOJE com as duas copias literais, e passaria amanha se alguem trocasse
as duas para o mesmo valor errado. Ele afirmaria a concordancia, que ja existe
por acaso, e nao a DERIVACAO, que e a propriedade.

Entao o teste monta um contrato SINTETICO cujo `$defs/since_qualifier` declara
outro vocabulario — `ancora` no lugar de `self` — e exige que as DUAS guardas o
sigam: aceitem `ancora` e recusem `self`. Codigo que tenha o literal embutido
falha, porque ele continua aceitando `self` e recusando `ancora`.

E a mesma forma que `tests/test_gabarito.py::DoisSeedsDiferentes` usa para
descobrir o que e escrito a mao: o que sobrevive a troca da fonte esta embutido,
por construcao.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import (  # noqa: E402
    PackError,
    PackSite,
    confere_qualificador_since,
)
from range_core.engine.verificacao import (  # noqa: E402
    Mundo,
    PredicadoMalformado,
    avalia,
)

#: O contrato REAL da arvore, lido uma vez — e a origem que a producao usa.
CONTRATOS = contract_source.read_contracts()

#: O VOCABULARIO SINTETICO. Nao e `self`, e e por isso que ele discrimina:
#: codigo que deriva do contrato o aceita, codigo com literal embutido nao.
OUTRO = "ancora"

CONTRATO_SINTETICO = {
    "ground_truth": {
        "$defs": {"since_qualifier": {"enum": [OUTRO]}},
    }
}


def _predicados(qualificador: str) -> dict:
    """Um `verification_predicates` de contencao com o `since` dado."""
    return {
        "verification_predicates": {
            "containment": {
                "absence_of": {"fact_class": "exfiltration", "since": qualificador}
            },
            "service_restoration": {"not_applicable": "fora do escopo do teste"},
        }
    }


class AOrigemEUmaSo(unittest.TestCase):
    """A funcao que le o contrato existe e devolve o que o contrato diz."""

    def test_o_qualificador_sai_do_contrato_da_arvore(self) -> None:
        self.assertEqual(frozenset({"self"}), contract_source.since_qualifiers(CONTRATOS))

    def test_contrato_sem_o_def_recusa_alto(self) -> None:
        """Ausencia nao vira default: default seria a segunda origem de volta."""
        with self.assertRaises(contract_source.ContractSourceError) as capturado:
            contract_source.since_qualifiers({"ground_truth": {"$defs": {}}})
        self.assertIn("since_qualifier", str(capturado.exception))


class AsDuasGuardasSeguemOContrato(unittest.TestCase):
    """O eixo que decide: troque a FONTE, e as duas guardas tem de acompanhar.

    Sem estes quatro, o modulo afirmaria a concordancia atual — que ja existe por
    coincidencia — em vez da derivacao.
    """

    def setUp(self) -> None:
        self.outro = contract_source.since_qualifiers(CONTRATO_SINTETICO)

    # --- a guarda de CARGA -------------------------------------------------

    def test_a_carga_ACEITA_o_qualificador_do_contrato_sintetico(self) -> None:
        self.assertIsNone(
            confere_qualificador_since(_predicados(OUTRO), qualificadores=self.outro)
        )

    def test_a_carga_RECUSA_self_quando_o_contrato_nao_o_declara(self) -> None:
        """Se `self` passar aqui, ele esta embutido no codigo e nao veio do contrato."""
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(_predicados("self"), qualificadores=self.outro)
        self.assertEqual(capturado.exception.site, PackSite.SINCE_UNDEFINED_VALUE)

    # --- o AVALIADOR -------------------------------------------------------

    def _mundo(self, qualificadores) -> Mundo:
        return Mundo(
            tipos=frozenset(),
            fatos=frozenset(),
            flags={},
            referencia=None,
            since_qualifiers=qualificadores,
        )

    def test_o_avaliador_ACEITA_o_qualificador_do_contrato_sintetico(self) -> None:
        """Aceitar = nao levantar `PredicadoMalformado`.

        `SemGramaticaTemporal` NAO conta como recusa do valor: ela e a P6-3, e
        significa que o valor foi RECONHECIDO e a comparacao e que falta. E
        justamente por chegar ate ela que se sabe que o qualificador passou.
        """
        from range_core.engine.verificacao import SemGramaticaTemporal

        no = {"absence_of": {"fact_class": "exfiltration", "since": OUTRO}}
        with self.assertRaises(SemGramaticaTemporal):
            avalia(no, self._mundo(self.outro))

    def test_o_avaliador_RECUSA_self_quando_o_contrato_nao_o_declara(self) -> None:
        """O espelho do teste da carga, e o que fecha a segunda copia."""
        no = {"absence_of": {"fact_class": "exfiltration", "since": "self"}}
        with self.assertRaises(PredicadoMalformado) as capturado:
            avalia(no, self._mundo(self.outro))
        self.assertIn("self", str(capturado.exception))


class ASegundaLinhaContinuaDeFato(unittest.TestCase):
    """Sobre o contrato REAL, as duas continuam concordando — controle positivo.

    Sem esta classe, as quatro acima passariam se alguem quebrasse as duas
    guardas de um jeito que so acertasse o contrato sintetico.
    """

    def setUp(self) -> None:
        self.reais = contract_source.since_qualifiers(CONTRATOS)

    def test_a_carga_aceita_a_forma_normativa(self) -> None:
        self.assertIsNone(
            confere_qualificador_since(_predicados("self"), qualificadores=self.reais)
        )

    def test_a_carga_recusa_o_que_a_norma_nao_define(self) -> None:
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(
                _predicados("exercise_start"), qualificadores=self.reais
            )
        self.assertEqual(capturado.exception.site, PackSite.SINCE_UNDEFINED_VALUE)

    def test_o_avaliador_recusa_o_que_a_norma_nao_define(self) -> None:
        no = {"absence_of": {"fact_class": "exfiltration", "since": "exercise_start"}}
        with self.assertRaises(PredicadoMalformado):
            avalia(
                no,
                Mundo(
                    tipos=frozenset(),
                    fatos=frozenset(),
                    flags={},
                    referencia=None,
                    since_qualifiers=self.reais,
                ),
            )


if __name__ == "__main__":
    unittest.main()
