"""P2-12 — a captura larga de `AuroraChecker._valida`, e a prova de que fechou.

O QUE ESTA SOB TESTE, E POR QUE PRECISA DE TESTE PROPRIO
--------------------------------------------------------
`_valida` responde "a instancia satisfaz este ramo?", e a resposta decide a
DESCIDA da caminhada. `False` significa "nao se aplica": a caminhada nao entra,
e nenhuma anotacao `x-aurora-*` daquele ramo dispara.

Enquanto a captura era `except Exception: return False`, todo erro de
programacao dentro dela produzia exatamente esse `False` — e o sintoma aparecia
tres camadas adiante, como *"a regra declarada nao disparou"*, apontando para as
fixtures em vez de para a causa. Aconteceu: o modulo novo da §1.4 nao importava
`Draft202012Validator`, o `NameError` foi engolido, e quatro fixtures negativas
reprovaram pelo motivo errado.

O gate pegou o sintoma. **Nada provava a causa**, e e isso que este arquivo
fecha.

AS DUAS METADES, e nenhuma prova sozinha o que a pendencia pedia
----------------------------------------------------------------
1. **Erro de programacao SOBE.** Com um nome quebrado plantado, `check` estoura.
   E a prova negativa que a P2-12 exige, na forma que ela pede: plantar o nome
   inexistente e verificar que estoura em vez de devolver `False`.

2. **A tolerancia que sobrou e EXERCITADA.** `Unresolvable` continua tolerado, e
   ha teste que o percorre. Captura que nunca capturou e prosa com sintaxe de
   codigo — a mesma classe de "regra que nunca falhou contra violacao plantada
   nao e regra", do outro lado.

A metade 1 sem a 2 deixaria uma captura decorativa; a 2 sem a 1 nao provaria
nada sobre o defeito que a pendencia nomeia.

O SINTOMA TEM TESTE PROPRIO, e nao e redundante
------------------------------------------------
`Sintoma` reproduz o comportamento ANTIGO — `_valida` devolvendo `False` por
engolir — e afirma que dali sai *nenhuma violacao*. Sem ele, os testes acima
provariam que o codigo faz o que faz, e nao que o que ele fazia antes era
defeito. E a ligacao entre a causa e o sintoma que a P2-12 descreve.

POR QUE UM SCHEMA SINTETICO, E NAO OS CONTRATOS REAIS
------------------------------------------------------
O que esta sob teste e a MECANICA da caminhada, nao o conteudo de contrato
nenhum. Contra `contracts/`, estes testes passariam a depender de um `oneOf`
continuar existindo em algum lugar de um arquivo que muda por outros motivos —
e quebrariam por mudanca legitima, que e como se ensina a ignorar teste.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

from range_core.engine.loader import contract_rules
from range_core.engine.loader.contract_rules import AuroraChecker

DOC_ID = "https://aurora-cyber-range.local/tests/contract_rules.json"

#: Flag que o registro sintetico conhece. Nao ha nome de dominio aqui: o modulo
#: sob teste e do `range-core`, e nomear `academus.*` num teste dele acoplaria o
#: core a um adapter pela porta que o invariante 1 nao guarda.
FLAG_DECLARADA = "fixture.declarada"
FLAG_AUSENTE = "fixture.ausente"

REGISTROS = {"adapter_flags": {FLAG_DECLARADA}, "_flag_specs": {}}


def documento(primeiro_ramo: dict) -> dict:
    """Schema com um `oneOf` de dois ramos, e a regra no SEGUNDO.

    A forma importa: `_valida` so e chamado para decidir a descida em
    `oneOf`/`anyOf`/`if`. Sem combinador, a caminhada nunca o invoca e o teste
    passaria sem tocar no codigo que ele diz cobrir.

    O primeiro ramo e o parametro porque e nele que cada caso planta o seu
    defeito; o segundo e sempre o que a instancia satisfaz, e e o que carrega a
    anotacao. Assim "a caminhada continuou" e afirmavel: a violacao do segundo
    ramo so aparece se o primeiro nao tiver derrubado a travessia.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": DOC_ID,
        "type": "object",
        "properties": {
            "campo": {
                "oneOf": [
                    primeiro_ramo,
                    {"type": "string", "x-aurora-ref": "adapter_flags"},
                ]
            }
        },
    }


def registry_de(doc: dict) -> Registry:
    return Registry().with_resources([(DOC_ID, Resource.from_contents(doc))])


#: Instancia que viola `x-aurora-ref: adapter_flags` no segundo ramo.
INSTANCIA = {"campo": FLAG_AUSENTE}

#: Ramo que nao interfere: a instancia e string, entao este nunca e satisfeito.
RAMO_SAO = {"type": "integer"}

#: Ramo cujo `$ref` aponta para documento que o registry nao tem.
RAMO_DOC_AUSENTE = {"$ref": "https://aurora-cyber-range.local/tests/nao-existe.json"}

#: Ramo cujo `$ref` aponta para ponteiro que nao existe no proprio documento.
RAMO_PONTEIRO_VAZIO = {"$ref": "#/$defs/inexistente"}


def viola(doc: dict) -> list:
    checker = AuroraChecker(REGISTROS, {DOC_ID: doc})
    return checker.check(DOC_ID, None, INSTANCIA, registry_de(doc))


class Baseline(unittest.TestCase):
    """Sem defeito plantado, a regra dispara. Sem isto, nada acima significa."""

    def test_a_regra_dispara_no_ramo_satisfeito(self):
        violacoes = viola(documento(RAMO_SAO))
        self.assertEqual([r for r, _ in violacoes], ["x-aurora-ref:adapter_flags"])


class ErroDeProgramacaoSobe(unittest.TestCase):
    """A prova negativa da P2-12, na forma que ela pede."""

    def test_nome_quebrado_estoura_em_vez_de_devolver_False(self):
        """Planta o defeito historico: o nome que o modulo nao importava.

        `NameError` e o erro exato do movimento da §1.4, e nao um representante
        escolhido por conveniencia — a captura antiga o transformava em
        "a regra nao disparou".
        """

        def nome_quebrado(*args, **kwargs):
            raise NameError("name 'Draft202012Validator' is not defined")

        doc = documento(RAMO_SAO)
        with mock.patch.object(contract_rules, "Draft202012Validator", nome_quebrado):
            with self.assertRaises(NameError):
                viola(doc)

    def test_erro_de_tipo_tambem_sobe(self):
        """Nao e o `NameError` que e especial: e a classe inteira.

        Um teste so com `NameError` deixaria passar uma captura estreitada para
        `except NameError`, que resolveria o caso conhecido e nenhum outro.
        """

        def assinatura_trocada(*args, **kwargs):
            raise TypeError("argumento inesperado")

        doc = documento(RAMO_SAO)
        with mock.patch.object(contract_rules, "Draft202012Validator", assinatura_trocada):
            with self.assertRaises(TypeError):
                viola(doc)


class Sintoma(unittest.TestCase):
    """O outro lado: engolir produz EXATAMENTE "a regra nao disparou".

    Reproduz o comportamento antigo sem restaura-lo — `_valida` sobrescrito para
    devolver `False`, que e o que a captura larga devolvia. A afirmacao e sobre a
    CONSEQUENCIA: nenhuma violacao reportada, com a mesma instancia que o
    `Baseline` reprova.
    """

    def test_valida_que_devolve_False_apaga_a_violacao(self):
        class Engolindo(AuroraChecker):
            def _valida(self, doc_id, ponteiro, instancia) -> bool:
                return False

        doc = documento(RAMO_SAO)
        checker = Engolindo(REGISTROS, {DOC_ID: doc})
        self.assertEqual(checker.check(DOC_ID, None, INSTANCIA, registry_de(doc)), [])


class RefIrresolvivel(unittest.TestCase):
    """A tolerancia que sobrou, exercitada — e a heranca em que ela se apoia.

    `jsonschema` embrulha a falha de resolucao de `referencing` em
    `_WrappedReferencingError`. A captura estreitada nomeia `Unresolvable`, e so
    funciona porque o embrulho herda dela. Isso e propriedade da versao pinada,
    nao garantia de API — entao esta afirmado aqui: se a heranca mudar, estes
    testes ficam vermelhos em vez de a tolerancia sumir em silencio.
    """

    def test_documento_ausente_e_tolerado_e_a_caminhada_continua(self):
        violacoes = viola(documento(RAMO_DOC_AUSENTE))
        self.assertEqual([r for r, _ in violacoes], ["x-aurora-ref:adapter_flags"])

    def test_ponteiro_para_lugar_nenhum_e_tolerado_e_a_caminhada_continua(self):
        violacoes = viola(documento(RAMO_PONTEIRO_VAZIO))
        self.assertEqual([r for r, _ in violacoes], ["x-aurora-ref:adapter_flags"])

    def test_o_embrulho_do_jsonschema_herda_de_Unresolvable(self):
        doc = documento(RAMO_DOC_AUSENTE)
        alvo = {"$ref": f"{DOC_ID}#/properties/campo/oneOf/0"}
        with self.assertRaises(Unresolvable):
            Draft202012Validator(alvo, registry=registry_de(doc)).is_valid(INSTANCIA)

    def test_o_defeito_nao_passa_em_silencio_na_camada_1(self):
        """Tolerar aqui nao esconde nada: a camada 1 ve o mesmo `$ref`.

        `check_contract_examples.py` valida a instancia contra o documento
        inteiro ANTES de chamar as regras, e ali nao ha captura nenhuma. Sem
        esta afirmacao, "tolerado" poderia significar "ignorado pelas duas
        camadas".
        """
        doc = documento(RAMO_DOC_AUSENTE)
        with self.assertRaises(Unresolvable):
            Draft202012Validator({"$ref": DOC_ID}, registry=registry_de(doc)).is_valid(
                INSTANCIA
            )


if __name__ == "__main__":
    unittest.main()
