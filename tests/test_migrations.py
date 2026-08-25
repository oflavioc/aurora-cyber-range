"""O registro de migracoes, e o ramo que ele governa e que ainda nao dispara.

POR QUE ESTE MODULO EXISTE
---------------------------
`range-core/engine/migrations/` entrega um REGISTRO vazio e a forma da consulta.
Um teste que so afirmasse `MIGRACOES == {}` seria tautologia — ele repetiria a
linha do modulo e nao provaria nada sobre o mecanismo.

O que ele prova e outra coisa: que `_instrucao_de_versao` DECIDE PELO REGISTRO,
e nao pela aritmetica das versoes. A diferenca importa porque a conta plausivel
— *"se a versao declarada e `max(SUPPORTED) - 1`, ha migracao"* — daria a
resposta certa hoje por acaso e a errada no dia em que a v1 existir sem
migrador, ou em que houver um salto de duas versoes.

E ELE COBRE O RAMO QUE NUNCA DISPARA NA ARVORE DE HOJE. `MIGRACOES` esta vazio,
entao a metade da mensagem que diz *"HA CAMINHO DE MIGRACAO"* e inalcancavel em
producao. Codigo inalcancavel dentro do mecanismo que a fase entrega e
exatamente o que a Fase 0 existe para nao deixar passar — a P2 daquele registro
diz isso com todas as letras sobre o modo de escrita do `codegen`.

Aqui ele e alcancado por REGISTRO INJETADO: o teste declara uma migracao que
nao existe no disco e afirma que a mensagem muda. Nenhum migrador e escrito, e
nenhum e simulado — o que se exercita e a decisao, que e a parte que existe.
"""

from __future__ import annotations

import unittest
from types import MappingProxyType

from range_core.engine import migrations
from range_core.engine.loader import pack_loader


class ORegistroEstaVazioEIssoEADeclaracao(unittest.TestCase):
    """A ausencia e a entrega — ver o cabecalho de `engine/migrations`."""

    def test_nao_ha_migracao_declarada(self) -> None:
        self.assertEqual({}, dict(migrations.MIGRACOES))

    def test_ha_migracao_responde_nao_para_qualquer_versao(self) -> None:
        for versao in (0, 1, 2, 3, 99):
            self.assertFalse(migrations.ha_migracao(versao))

    def test_o_registro_nao_aceita_escrita_em_runtime(self) -> None:
        """Migracao registrada fora do diff e migracao que nenhuma revisao viu."""
        with self.assertRaises(TypeError):
            migrations.MIGRACOES[1] = "v1_to_v2"  # type: ignore[index]


class ADecisaoVEmDoREGISTRO(unittest.TestCase):
    """O eixo que discrimina registro de aritmetica."""

    def _mensagem(self, versao: int) -> str:
        from pathlib import Path

        return pack_loader._instrucao_de_versao(Path("/pack"), versao)

    def test_sem_registro_a_mensagem_diz_que_NAO_HA_migrador(self) -> None:
        """A v1 e `max(SUPPORTED) - 1` e mesmo assim nao tem caminho.

        Se a decisao fosse pela conta, esta seria a mensagem errada — e e a
        certa: nunca houve contrato v1, entao nao ha o que aplicar.
        """
        self.assertIn("NAO HA MIGRADOR", self._mensagem(1))

    def test_com_registro_injetado_a_mensagem_MUDA(self) -> None:
        """O ramo inalcancavel em producao, alcancado aqui.

        Declara-se uma migracao que nao existe no disco: o que se exercita e a
        DECISAO. Se ela viesse da aritmetica, injetar o registro nao mudaria
        nada e este teste falharia — que e o ponto dele.
        """
        original_map = pack_loader.MIGRACOES
        original_fn = pack_loader.ha_migracao
        try:
            pack_loader.MIGRACOES = MappingProxyType({1: "v1_to_v2"})
            pack_loader.ha_migracao = lambda de: de in pack_loader.MIGRACOES
            mensagem = self._mensagem(1)
        finally:
            pack_loader.MIGRACOES = original_map
            pack_loader.ha_migracao = original_fn

        self.assertIn("HA CAMINHO DE MIGRACAO", mensagem)
        self.assertIn("v1_to_v2.py", mensagem)
        self.assertNotIn("NAO HA MIGRADOR", mensagem)

    def test_a_arvore_volta_ao_estado_anterior(self) -> None:
        """O `finally` acima e afirmado, e nao suposto.

        Teste que altera modulo e nao prova a restauracao contamina a ordem de
        execucao da suite — e ordem de teste que importa e defeito que aparece
        longe da causa.
        """
        self.assertEqual({}, dict(pack_loader.MIGRACOES))
        self.assertIs(pack_loader.ha_migracao, migrations.ha_migracao)


if __name__ == "__main__":
    unittest.main()
