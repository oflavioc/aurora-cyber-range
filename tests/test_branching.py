"""A peca 4 da Fase 7 — `branch_policy` aplicada, a metade "indicado", e a travessia.

O QUE ESTA SUITE PROVA
=======================
Os itens 4 e 6 da DoD (`07_IMPLEMENTATION_PHASES.md`) e a regra
`option_existe_no_decision_point_indicado` do registro do contrato:

    - `confere_branch_policy` conta pontos por linha e caminhos por ponto, e
      recusa o excesso COM POSICAO — e politica ausente nao conta nada;
    - `confere_option_no_decision_point` recusa o `option` que nao pertence ao
      `decision_point` que a folha `decision` IRMA indica — o caso que o
      `x-aurora-ref` global sempre deixou passar, e por isso ele e o teste de
      discriminante inteiro desta regra;
    - `percorre` produz a sequencia de cada caminho e recusa o que nao anda.

AS FIXTURAS VEM DA SUITE DO LINT, e a reutilizacao e deliberada: uma fabrica
de pack, muitos consumidores — escrever uma segunda aqui seria a D4 da Fase 1
dentro da suite que existe para provar a regra nova. `escreve_pack` monta o
pack LIMPO por default, e cada teste troca so o arquivo que a prova exige.

A semantica que cada assercao cobra esta declarada em
`docs/progress/fase_7.md` §5.2 — ANTES do codigo, para a revisao ser da
decisao e nao da arqueologia.
"""

from __future__ import annotations

import unittest

import yaml

from domains.academus.generated.flags import ACADEMUS_ENROLLMENT_OFFLINE
from range_core.engine.loader import branching
from range_core.engine.loader.pack_loader import PackSite
from test_range_cli_lint import (
    BRANCHES_LIMPO,
    INJECTS_LIMPO,
    MANIFESTO,
    _BaseDeLint,
    escreve_pack,
)

#: A politica do exemplo normativo de `04` §2 — a fixture limpa cabe nela.
POLITICA_DO_EXEMPLO = """\
branch_policy:
  max_branch_points_per_line: 1
  max_paths_per_branch: 2
"""

MANIFESTO_COM_POLITICA = MANIFESTO + POLITICA_DO_EXEMPLO

#: Dois pontos de ramificacao na MESMA linha A. Sob a politica do exemplo
#: (max 1 por linha), o SEGUNDO e o excesso — e a ancora da posicao e o id
#: dele.
BRANCHES_DOIS_PONTOS = """\
branches:
  - id: BR-PRIMEIRO
    line: A
    at_inject: A01
    evaluate:
      - id: unico
        default: true
        next: A02
    reconverge_at: A02
  - id: BR-SEGUNDO
    line: A
    at_inject: A02
    evaluate:
      - id: unico
        default: true
        next: A03
    reconverge_at: A03
"""

#: Um ponto com TRES caminhos. Sob `max_paths_per_branch: 2`, o `evaluate` e o
#: excesso.
BRANCHES_TRES_CAMINHOS = """\
branches:
  - id: BR-TRES-CAMINHOS
    line: A
    at_inject: A01
    evaluate:
      - id: primeiro
        default: true
        next: A02
      - id: segundo
        next: A02
      - id: terceiro
        next: A03
    reconverge_at: A03
"""

#: Injects com DOIS decision_points, para a metade "indicado" ter o que
#: distinguir: `suspend` pertence a DP-UM; `alpha` pertence a DP-DOIS.
INJECTS_COM_DECISOES = f"""\
injects:
  - id: A01
    linha: A
    t_relative: "00:10"
    titulo_operacional: "Comunicado 01"
    objectives: [OBJ-01]
    decision_point:
      id: DP-UM
      question: "Suspender a matrícula online?"
      options:
        - id: suspend
          label: "Suspender imediatamente"
          effects:
            {ACADEMUS_ENROLLMENT_OFFLINE}: true
          tradeoff: "Contém exposição; interrompe o período letivo"
        - id: monitor
          label: "Manter no ar sob monitoramento"
          effects: {{}}
          tradeoff: "Preserva calendário; amplia a janela de exposição"
  - id: A02
    linha: A
    t_relative: "00:20"
    titulo_operacional: "Comunicado 02"
    objectives: [OBJ-01]
    decision_point:
      id: DP-DOIS
      question: "Comunicar o corpo docente agora?"
      options:
        - id: alpha
          label: "Comunicar imediatamente"
          effects: {{}}
          tradeoff: "Transparência; abre espaço para ruído"
  - id: A03
    linha: A
    t_relative: "00:30"
    titulo_operacional: "Comunicado 03"
    objectives: [OBJ-01]
"""


def _branches_com_condicao(condicao_yaml: str) -> str:
    """Uma branch cuja condicao do primeiro braco e a do teste."""
    condicao = "\n".join(f"          {linha}" for linha in condicao_yaml.splitlines())
    return f"""\
branches:
  - id: BR-DA-CONDICAO
    line: A
    at_inject: A01
    evaluate:
      - id: condicionado
        when:
{condicao}
        next: A02
      - id: contrario
        default: true
        next: A03
    reconverge_at: A03
"""


class BranchPolicyAplicada(_BaseDeLint):
    """Item 4 da DoD: *"`branch_policy` do manifesto e aplicada"* — `06` T12."""

    def test_a_fixture_limpa_cabe_na_politica_do_exemplo_normativo(self):
        pack = escreve_pack(**{"manifest.yaml": MANIFESTO_COM_POLITICA})
        self.assertEqual(self.lint(pack), [])

    def test_excesso_de_pontos_por_linha_e_recusado_no_segundo_ponto(self):
        pack = escreve_pack(
            **{
                "manifest.yaml": MANIFESTO_COM_POLITICA,
                "branches.yaml": BRANCHES_DOIS_PONTOS,
            }
        )
        achado = self.um_achado(pack, PackSite.BRANCH_POLICY_EXCEEDED)
        self.assertIn("max_branch_points_per_line", achado.erro.mensagem)
        self.assertIn("BR-SEGUNDO", achado.erro.mensagem)
        self.assertPosicaoNaAncora(achado, BRANCHES_DOIS_PONTOS, "BR-SEGUNDO")

    def test_excesso_de_caminhos_e_recusado_no_evaluate_do_ponto(self):
        pack = escreve_pack(
            **{
                "manifest.yaml": MANIFESTO_COM_POLITICA,
                "branches.yaml": BRANCHES_TRES_CAMINHOS,
            }
        )
        achado = self.um_achado(pack, PackSite.BRANCH_POLICY_EXCEEDED)
        self.assertIn("max_paths_per_branch", achado.erro.mensagem)
        # A posicao de `$.branches[0].evaluate` resolve para o VALOR — a lista,
        # que comeca no primeiro braco —, e nao para a linha da chave.
        self.assertPosicaoNaAncora(achado, BRANCHES_TRES_CAMINHOS, "id: primeiro")

    def test_sem_politica_no_manifesto_nada_e_contado(self):
        """Politica ausente e ausencia de limite DECLARADO — inventar default
        seria a classe D6, piso que a fonte nao declara."""
        pack = escreve_pack(**{"branches.yaml": BRANCHES_DOIS_PONTOS})
        self.assertEqual(self.lint(pack), [])

    def test_a_linha_do_ponto_cai_para_a_linha_do_at_inject(self):
        """Registro §5.2, decisao 1: sem `line` na branch, vale a `linha` do
        inject de `at_inject` — os dois pontos continuam sendo da linha A."""
        sem_line = BRANCHES_DOIS_PONTOS.replace("    line: A\n", "")
        pack = escreve_pack(
            **{
                "manifest.yaml": MANIFESTO_COM_POLITICA,
                "branches.yaml": sem_line,
            }
        )
        achado = self.um_achado(pack, PackSite.BRANCH_POLICY_EXCEEDED)
        self.assertIn("BR-SEGUNDO", achado.erro.mensagem)


class OptionNoDecisionPointIndicado(_BaseDeLint):
    """A metade "indicado" de `04` §6.2 — parcial no registro desde a peca 3."""

    def test_par_correto_nao_tem_achado(self):
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_COM_DECISOES,
                "branches.yaml": _branches_com_condicao(
                    "all:\n  - decision: DP-UM\n  - option: suspend"
                ),
            }
        )
        self.assertEqual(self.lint(pack), [])

    def test_option_de_OUTRO_decision_point_e_recusado_com_posicao(self):
        """O caso que o `x-aurora-ref` global sempre deixou passar: `suspend`
        existe no pack — so nao existe em DP-DOIS. E o discriminante inteiro
        da regra nova, e por isso `um_achado` importa: a existencia global NAO
        pode produzir um segundo achado aqui."""
        branches = _branches_com_condicao(
            "all:\n  - decision: DP-DOIS\n  - option: suspend"
        )
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_COM_DECISOES,
                "branches.yaml": branches,
            }
        )
        achado = self.um_achado(pack, PackSite.OPTION_FORA_DO_DECISION_POINT)
        self.assertIn("DP-DOIS", achado.erro.mensagem)
        self.assertPosicaoNaAncora(achado, branches, "option: suspend")

    def test_decision_point_indicado_inexistente_e_recusado_na_folha_decision(self):
        branches = _branches_com_condicao(
            "all:\n  - decision: DP-NOVENTA\n  - option: suspend"
        )
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_COM_DECISOES,
                "branches.yaml": branches,
            }
        )
        achado = self.um_achado(pack, PackSite.OPTION_FORA_DO_DECISION_POINT)
        self.assertIn("DP-NOVENTA", achado.erro.mensagem)
        self.assertPosicaoNaAncora(achado, branches, "decision: DP-NOVENTA")

    def test_option_sem_irmao_decision_segue_coberto_so_pela_existencia_global(self):
        """Registro §5.2, decisao 5: folha `option` sozinha nao indica ponto
        nenhum — recusa aqui seria inventar par que o autor nao escreveu."""
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_COM_DECISOES,
                "branches.yaml": _branches_com_condicao("all:\n  - option: alpha"),
            }
        )
        self.assertEqual(self.lint(pack), [])

    def test_o_par_e_encontrado_dentro_de_any_e_not(self):
        """A conjuncao pode morar fundo na arvore — a caminhada desce por
        `any` e `not` para achar os `all` internos."""
        branches = _branches_com_condicao(
            "any:\n"
            "  - not:\n"
            "      all:\n"
            "        - decision: DP-DOIS\n"
            "        - option: monitor"
        )
        pack = escreve_pack(
            **{
                "injects.yaml": INJECTS_COM_DECISOES,
                "branches.yaml": branches,
            }
        )
        achado = self.um_achado(pack, PackSite.OPTION_FORA_DO_DECISION_POINT)
        self.assertPosicaoNaAncora(achado, branches, "option: monitor")


class ATravessia(unittest.TestCase):
    """`percorre` — o corpo do `dryrun`, direto na funcao (`06` T12)."""

    def _percorre(self, injects: str, branches: str) -> list[branching.Caminho]:
        return branching.percorre(
            yaml.safe_load(injects), yaml.safe_load(branches)
        )

    def test_a_fixture_limpa_produz_as_duas_sequencias(self):
        caminhos = self._percorre(INJECTS_LIMPO, BRANCHES_LIMPO)
        self.assertEqual(
            [caminho.sequencia for caminho in caminhos],
            [("A01", "A02", "A03"), ("A01", "A03")],
        )
        self.assertEqual(
            [caminho.braco.id for caminho in caminhos],
            ["contained_early", "not_contained"],
        )

    def test_a_janela_exclui_o_next_dos_bracos_irmaos(self):
        """Registro §5.2, decisao 3: os `next` irmaos SAO a divergencia — o
        caminho de um braco nao passa pelo inject que so existe no outro."""
        injects = INJECTS_LIMPO + (
            "  - id: A04\n"
            "    linha: A\n"
            '    t_relative: "00:40"\n'
            '    titulo_operacional: "Comunicado 04"\n'
            "    objectives: [OBJ-01]\n"
        )
        branches = """\
branches:
  - id: BR-DIVERGE
    line: A
    at_inject: A01
    evaluate:
      - id: pela_esquerda
        default: true
        next: A02
      - id: pela_direita
        next: A03
    reconverge_at: A04
"""
        caminhos = self._percorre(injects, branches)
        self.assertEqual(
            [caminho.sequencia for caminho in caminhos],
            [("A01", "A02", "A04"), ("A01", "A03", "A04")],
        )

    def _erro_de_travessia(self, injects: str, branches: str):
        with self.assertRaises(Exception) as contexto:
            self._percorre(injects, branches)
        erro = contexto.exception
        self.assertEqual(erro.site, PackSite.BRANCH_WALK_IMPOSSIBLE)
        return erro

    def test_next_que_nao_vem_depois_do_ponto_e_recusado(self):
        branches = BRANCHES_LIMPO.replace("at_inject: A01", "at_inject: A02")
        # `contained_early` continua com `next: A02` — igual ao ponto, e igual
        # nao e DEPOIS.
        erro = self._erro_de_travessia(INJECTS_LIMPO, branches)
        self.assertIn("nao vem DEPOIS", erro.mensagem)
        self.assertTrue(erro.caminho.endswith(".next"), erro.caminho)

    def test_reconvergencia_antes_do_next_e_recusada(self):
        branches = BRANCHES_LIMPO.replace("reconverge_at: A03", "reconverge_at: A02")
        # `not_contained` tem `next: A03`, e a reconvergencia declarada (A02)
        # vem antes dele no relogio.
        erro = self._erro_de_travessia(INJECTS_LIMPO, branches)
        self.assertIn("ANTES", erro.mensagem)
        self.assertTrue(erro.caminho.endswith(".reconverge_at"), erro.caminho)

    def test_next_fora_da_linha_do_ponto_e_recusado(self):
        injects = INJECTS_LIMPO.replace(
            "  - id: A02\n    linha: A", "  - id: A02\n    linha: B"
        )
        erro = self._erro_de_travessia(injects, BRANCHES_LIMPO)
        self.assertIn("linha", erro.mensagem)
        self.assertTrue(erro.caminho.endswith(".next"), erro.caminho)

    def test_next_igual_a_reconvergencia_e_caminho_direto(self):
        """A fixture limpa fixa isso desde a peca 3: o braco default vai
        direto a reconvergencia, e a sequencia e o par."""
        caminhos = self._percorre(INJECTS_LIMPO, BRANCHES_LIMPO)
        self.assertEqual(caminhos[1].sequencia, ("A01", "A03"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
