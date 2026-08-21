"""A cobertura de `contracts/` é derivada do diretório, e nunca de um número.

POR QUE ESTE MÓDULO EXISTE
---------------------------
O passo de CI que prova o `package-data` afirmava `len(read_contracts()) == 6`.
A peça 1 da Fase 6 criou o **sétimo** contrato — `rubrics.schema.yaml` — e não
varreu quem afirmava a contagem. O passo teria ficado vermelho no PR da fase,
trinta commits depois de a causa entrar.

**A lição não é "a branch não foi empurrada"** — `push` não roda CI sem PR, e o
número teria envelhecido do mesmo jeito num repositório com CI a cada push. A
lição é a que ficou escrita em `docs/progress/fase_6.md`: **criar instância de um
conjunto contado exige varrer quem afirma a contagem, no mesmo commit.**

O QUE ELE ACRESCENTA AO PASSO DE CI
------------------------------------
O passo de CI roda com `working-directory: /tmp`, e é isso que ele prova: que
`contracts` resolve pelo `__path__` do pacote e não pelo CWD. Ele **não roda na
suíte**, então a divergência só apareceria no runner.

Este módulo faz a mesma pergunta de dentro da suíte, onde ela é respondida em
segundos e por quem está editando. As duas provas não se substituem: uma é sobre
**resolução fora da raiz**, a outra é sobre **cobertura**.

NENHUM NÚMERO AQUI TAMBÉM
--------------------------
A comparação é sempre `contratos lidos` × `arquivos no diretório`. Escrever
`assertEqual(len(...), 7)` reproduziria o defeito com outro número, e a próxima
peça que criar um contrato o encontraria vermelho sem saber por quê.
"""

from __future__ import annotations

import unittest

from range_core.engine.loader import contract_source


class TodoArquivoDeContratoEUmContratoLido(unittest.TestCase):
    def setUp(self) -> None:
        self.lidos = contract_source.read_contracts()
        self.arquivos = sorted(
            caminho.name for caminho in contract_source.contracts_dir().glob("*.yaml")
        )

    def test_o_diretorio_nao_esta_vazio(self):
        """Sem isto, `0 == 0` passaria e o `package-data` ficaria sem prova."""
        self.assertTrue(self.arquivos)

    def test_nenhum_arquivo_fica_orfao_e_nenhum_contrato_sobra(self):
        """A igualdade nas duas direções, e não só uma contagem que bate.

        Arquivo que o loader não lê é contrato que nenhum gate valida — foi
        assim que `observability_hooks.yaml` atravessou a Fase 1 sem varredura.
        Contrato lido sem arquivo seria estado inventado pelo loader.
        """
        self.assertEqual(
            len(self.lidos),
            len(self.arquivos),
            f"contratos lidos: {sorted(self.lidos)}; arquivos: {self.arquivos}. "
            "A cobertura é derivada do diretório — se um arquivo novo não vira "
            "contrato, o loader precisa saber lê-lo.",
        )

    def test_cada_contrato_lido_tem_arquivo_de_mesmo_prefixo(self):
        """A ligação nome→arquivo, para a contagem não bater por acidente.

        Dois arquivos e dois contratos com nomes trocados dariam o mesmo número
        e descreveriam outra árvore.
        """
        prefixos = {nome.split(".")[0] for nome in self.arquivos}
        self.assertEqual(set(self.lidos), prefixos)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
