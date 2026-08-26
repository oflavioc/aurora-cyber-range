"""`range-cli scenario dryrun` — o verbo, do parser a saida (`06` T12, item 6).

O CORPO DA TRAVESSIA E DE `branching.percorre`, e a suite dele e
`tests/test_branching.py` — aqui se prova o que o VERBO acrescenta: a ordem
(lint primeiro, travessia depois), os codigos de saida, e o destino do texto.
Mesma divisao da suite do lint: `04` §8 poe os verbos de leitura no CI, e um
codigo de saida errado quebraria o job sem nenhuma regra ter falhado.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from range_cli import cli
from test_range_cli_lint import BRANCHES_LIMPO, INJECTS_LIMPO, _BaseDeLint, escreve_pack


class ASaidaDoDryrun(_BaseDeLint):
    def _roda(self, pack_dir: Path) -> tuple[int, str, str]:
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            codigo = cli.main(["scenario", "dryrun", str(pack_dir)])
        return codigo, saida.getvalue(), erro.getvalue()

    def test_pack_limpo_sai_zero_e_lista_todos_os_caminhos(self):
        codigo, saida, _ = self._roda(escreve_pack())
        self.assertEqual(codigo, cli.LIMPO)
        self.assertIn("todos percorridos", saida)
        self.assertIn("A01 -> A02 -> A03", saida)
        self.assertIn("A01 -> A03", saida)
        self.assertIn("(default)", saida)

    def test_pack_com_achado_de_lint_e_recusado_antes_da_travessia(self):
        """A travessia sobre pack com achados nao afirma nada — o verbo para
        no lint, e o relatorio e o MESMO do `lint`, para consertar uma vez."""
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_LIMPO.replace(
                    "    objectives: [OBJ-01]\n", "", 1
                )
            }
        )
        codigo, _, erro = self._roda(pack)
        self.assertEqual(codigo, cli.RECUSADO)
        self.assertIn("dryrun recusado", erro)
        self.assertIn("achado", erro)

    def test_pack_que_linta_limpo_e_nao_anda_e_recusado_pela_travessia(self):
        """O que o verbo ACRESCENTA: a branch bem-formada que nenhuma camada
        anterior ve — aqui, reconvergencia antes do `next` do braco default."""
        pack = escreve_pack(
            **{
                "branches.yaml": BRANCHES_LIMPO.replace(
                    "reconverge_at: A03", "reconverge_at: A02"
                )
            }
        )
        codigo, _, erro = self._roda(pack)
        self.assertEqual(codigo, cli.RECUSADO)
        self.assertIn("branch_walk_impossible", erro)

    def test_pack_sem_branches_sai_zero_e_diz_que_nao_ha_caminho(self):
        """`branches.yaml` e opcional (`x-aurora-registry.package_files`) — a
        ausencia nao e defeito, e um dryrun silencioso pareceria travado."""
        codigo, saida, _ = self._roda(escreve_pack(**{"branches.yaml": None}))
        self.assertEqual(codigo, cli.LIMPO)
        self.assertIn("nenhum caminho a percorrer", saida)
