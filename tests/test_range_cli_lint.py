"""`range-cli scenario lint` — os itens 1, 2 e 3 da DoD da Fase 7, com posicao.

O QUE ESTA SUITE PROVA
=======================
Os tres criterios DONE da peca 3, mais o quarto que `06` T12 acrescenta com a
mesma exigencia de posicao:

    DoD 1   inject sem `objectives` e sem `noise: true` e recusado
    DoD 2   `event_type` inexistente em condicao de branch, COM POSICAO NO ARQUIVO
    DoD 3   condicao dependente de juizo do facilitador e recusada
    T12     opcao com `capability_gap` citando objetivo inexistente, COM POSICAO

E as duas regras que `x-aurora-linter-rules` declarava sem mecanismo nenhum ate
esta peca: `t_relative` fora de ordem e `fact_check_against` que nao resolve.

AS TRES PRIMEIRAS JA RECUSAVAM ANTES DESTA PECA, e a suite diz isso de proposito
-------------------------------------------------------------------------------
Elas recusavam na CARGA, pelo contrato — `if/else` em `#/$defs/inject`,
`x-aurora-ref: event_catalog`, `oneOf` fechado. O que a peca acrescenta e a
SUPERFICIE, a POSICAO e a COLHEITA. Um teste que so afirmasse "e recusado"
passaria identico antes e depois, e nao provaria a entrega — por isso cada caso
cobra tambem `arquivo:linha:coluna`, e ha um caso que cobra os quatro defeitos
numa execucao so.

A POSICAO E CONFERIDA CONTRA O TEXTO, e nao contra numero escrito a mao
-----------------------------------------------------------------------
`assertEqual(posicao.linha, 14)` envelhece na primeira linha inserida na
fixture, e envelhece em SILENCIO se o numero por acaso continuar casando outra
coisa. Aqui o esperado e DERIVADO: o teste localiza a ancora no proprio texto da
fixture e compara. Se a fixture mudar, o esperado muda junto.

FIXTURE ESCRITA, NUNCA A ARVORE MUTADA
---------------------------------------
Cada pack nasce em diretorio temporario. Mesma disciplina de
`tests/test_pack_loader.py`, e pelo mesmo motivo.
"""

from __future__ import annotations

import io
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from contracts.generated.events import VPN_ACCESS_REVOKED
from domains.academus.generated.flags import ACADEMUS_ENROLLMENT_OFFLINE
from range_cli import cli, lint as lint_de_cenario
from range_core.engine.loader import contract_source
from range_core.engine.loader.pack_loader import PackError, PackSite
from range_core.engine.loader.posicao import MapaDePosicoes

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRATOS = contract_source.read_contracts()
FLAGS = lint_de_cenario.carrega_flags(
    REPO_ROOT / "domains" / "academus" / "flags.yaml"
)

#: O erro de digitacao, DERIVADO da constante do catalogo — um `c` a menos.
#:
#: Escrever o nome errado a mao seria literal de `event_type` no fonte, que e o
#: invariante 3 e o que `tools/check_contract_literals.py` recusa. E derivar tem
#: valor proprio: a fixture continua sendo "o nome certo, com um caractere
#: trocado" mesmo que o nome certo mude.
EVENTO_COM_ERRO_DE_DIGITACAO = VPN_ACCESS_REVOKED.replace("access", "acess")

MANIFESTO = f"""\
schema_version: 2
pack_id: pack-da-suite-de-lint
title: "Pack de fixture da suite de lint"
domain: academus
min_engine_version: "1.0"
duration_minutes: 60
personas: [ti]
required_flags: [{ACADEMUS_ENROLLMENT_OFFLINE}]
required_rubrics: [incident_triage.v2]
"""

OBJETIVOS = """\
objectives:
  OBJ-01:
    title: "Reconhecer indisponibilidade como possível incidente"
    competency: incident_triage
    rubric: incident_triage.v2
    expected_behavior:
      - 'tratar a queda do portal como hipótese aberta'
    evidence:
      auto:
        - incident_declared
      observed:
        - id: articulou_hipotese_de_seguranca
          prompt_to_evaluator: "A equipe tratou a queda como hipótese de segurança?"
"""

GROUND_TRUTH = f"""\
facts:
  - fact_id: GT-A-020
    fact_class: exfiltration
    actor: svc_academus
    action: bulk_export
    exercise_time: "T-9d 02:14"
    records_affected: 1200
    projections: [vpn]
verification_predicates:
  containment:
    all:
      - event: {VPN_ACCESS_REVOKED}
      - absence_of:
          fact_class: exfiltration
          since: self
  service_restoration:
    all:
      - flag_false: {ACADEMUS_ENROLLMENT_OFFLINE}
"""

INJECTS_LIMPO = f"""\
injects:
  - id: A01
    linha: A
    t_relative: "00:10"
    titulo_operacional: "Comunicado 01"
    objectives: [OBJ-01]
    effects:
      {ACADEMUS_ENROLLMENT_OFFLINE}: true
  - id: A02
    linha: A
    t_relative: "00:20"
    titulo_operacional: "Comunicado 02"
    objectives: [OBJ-01]
  - id: A03
    linha: A
    t_relative: "00:30"
    titulo_operacional: "Comunicado 03"
    objectives: [OBJ-01]
"""

BRANCHES_LIMPO = f"""\
branches:
  - id: BR-A-CONTAINMENT
    line: A
    at_inject: A01
    evaluate:
      - id: contained_early
        when:
          all:
            - event: {VPN_ACCESS_REVOKED}
        next: A02
      - id: not_contained
        default: true
        next: A03
    reconverge_at: A03
"""

#: Os `TemporaryDirectory` vivos, esvaziados no `tearDown` da base.
_TEMPORARIOS: list[tempfile.TemporaryDirectory] = []


def escreve_pack(**arquivos: str | None) -> Path:
    """Um pack em diretorio temporario. Os defaults formam um pack LIMPO.

    Passar `nome=None` REMOVE o arquivo — e assim que a suite exercita o pacote
    apenas-manifesto de `04` §9 sem precisar de uma segunda fabrica.
    """
    padrao: dict[str, str | None] = {
        "manifest.yaml": MANIFESTO,
        "objectives.yaml": OBJETIVOS,
        "ground_truth.yaml": GROUND_TRUTH,
        "injects.yaml": INJECTS_LIMPO,
        "branches.yaml": BRANCHES_LIMPO,
    }
    padrao.update(arquivos)
    temporario = tempfile.TemporaryDirectory()
    _TEMPORARIOS.append(temporario)
    destino = Path(temporario.name) / "pack"
    destino.mkdir(parents=True)
    for nome, conteudo in padrao.items():
        if conteudo is not None:
            (destino / nome).write_text(conteudo, encoding="utf-8", newline="\n")
    return destino


class _BaseDeLint(unittest.TestCase):
    """Roda o linter, e oferece as duas assercoes que toda entrega desta peca usa."""

    def tearDown(self) -> None:
        while _TEMPORARIOS:
            _TEMPORARIOS.pop().cleanup()

    def lint(self, pack_dir: Path) -> list[lint_de_cenario.Achado]:
        return lint_de_cenario.lint(
            pack_dir, contracts=CONTRATOS, adapter_flags=FLAGS
        )

    def um_achado(self, pack_dir: Path, site: str) -> lint_de_cenario.Achado:
        """O UNICO achado, e ele e do sitio esperado.

        A unicidade e parte da assercao. Sem ela, uma fixture que plantasse dois
        defeitos passaria provando o errado — e a colheita do linter torna esse
        engano facil, justamente porque ele nao para no primeiro.
        """
        achados = self.lint(pack_dir)
        self.assertEqual(
            [a.erro.site for a in achados],
            [site],
            f"esperado exatamente um achado de {site!r}",
        )
        return achados[0]

    def assertPosicaoNaAncora(
        self, achado: lint_de_cenario.Achado, fonte: str, ancora: str
    ) -> None:
        """A posicao aponta para a ancora, DERIVADA do texto da fixture."""
        self.assertIsNotNone(achado.posicao, "o achado saiu sem posicao")
        self.assertTrue(
            achado.posicao.exata,
            f"posicao aproximada: resolveu ate {achado.posicao.caminho_resolvido!r}",
        )
        candidatas = [
            i + 1 for i, linha in enumerate(fonte.splitlines()) if ancora in linha
        ]
        self.assertEqual(
            len(candidatas), 1, f"a ancora {ancora!r} nao aparece exatamente uma vez"
        )
        self.assertEqual(achado.posicao.linha, candidatas[0])


class OPackLimpoNaoTemAchado(_BaseDeLint):
    """Sem isto, nenhuma recusa abaixo significa coisa alguma."""

    def test_pack_completo_e_valido_sai_sem_achados(self):
        self.assertEqual(self.lint(escreve_pack()), [])

    def test_pacote_apenas_manifesto_passa(self):
        """`04` §9 — forma legitima, e nao pacote defeituoso.

        Os dois packs de roadmap (`vazamento-lgpd`, `pesquisa-comprometida`)
        existem justamente para provar que o loader lida com pacote incompleto.
        Um linter que os recusasse reprovaria dois entregaveis normativos.
        """
        pack = escreve_pack(
            **{
                "injects.yaml": None,
                "branches.yaml": None,
                "objectives.yaml": None,
                "ground_truth.yaml": None,
            }
        )
        self.assertEqual(self.lint(pack), [])


class OsQuatroCriteriosComPosicao(_BaseDeLint):
    """DoD 1, 2, 3 e o quarto de `06` T12 — cada um com `linha:coluna`."""

    def test_dod_1_inject_sem_objetivo_e_sem_noise(self):
        fonte = textwrap.dedent(
            """\
            injects:
              - id: A01
                linha: A
                t_relative: "00:10"
                titulo_operacional: "Comunicado sem objetivo e sem noise"
            """
        )
        achado = self.um_achado(
            escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None}),
            PackSite.DOCUMENT_INVALID,
        )
        self.assertEqual(achado.erro.arquivo, "injects.yaml")
        self.assertIn("objectives", achado.erro.mensagem)
        self.assertPosicaoNaAncora(achado, fonte, "- id: A01")

    def test_dod_1_noise_true_dispensa_objectives(self):
        """A outra metade: `00` §4 chama a ambiguidade de ruido ou erro de autoria.

        Sem esta perna, uma regra que exigisse `objectives` de TODO inject
        passaria no teste acima e recusaria o inject de ruido — que e forma
        legitima, e e o que discrimina as duas.
        """
        fonte = textwrap.dedent(
            """\
            injects:
              - id: R01
                t_relative: "00:10"
                titulo_operacional: "Comunicado de ruido"
                noise: true
            """
        )
        self.assertEqual(
            self.lint(escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None})),
            [],
        )

    def test_dod_2_event_type_inexistente_em_condicao_de_branch(self):
        fonte = BRANCHES_LIMPO.replace(
            VPN_ACCESS_REVOKED, EVENTO_COM_ERRO_DE_DIGITACAO, 1
        )
        achado = self.um_achado(
            escreve_pack(**{"branches.yaml": fonte}), PackSite.RULE_VIOLATION
        )
        self.assertEqual(achado.erro.arquivo, "branches.yaml")
        self.assertIn("event_catalog", achado.erro.mensagem)
        self.assertIn(EVENTO_COM_ERRO_DE_DIGITACAO, achado.erro.mensagem)
        self.assertEqual(
            achado.erro.caminho, "$.branches[0].evaluate[0].when.all[0].event"
        )
        self.assertPosicaoNaAncora(
            achado, fonte, f"event: {EVENTO_COM_ERRO_DE_DIGITACAO}"
        )

    def test_dod_2_a_coluna_aponta_para_o_VALOR_e_nao_para_a_chave(self):
        """Localizar e o ponto do criterio, e a chave nao e o defeito.

        `04` §6.2 diz que o erro de digitacao faz a branch nao ramificar. Quem
        conserta precisa do cursor em cima do NOME ERRADO, e nao no `event:`,
        que esta certo.
        """
        fonte = BRANCHES_LIMPO.replace(
            VPN_ACCESS_REVOKED, EVENTO_COM_ERRO_DE_DIGITACAO, 1
        )
        achado = self.um_achado(
            escreve_pack(**{"branches.yaml": fonte}), PackSite.RULE_VIOLATION
        )
        linha = fonte.splitlines()[achado.posicao.linha - 1]
        self.assertEqual(
            linha[achado.posicao.coluna - 1 :], EVENTO_COM_ERRO_DE_DIGITACAO
        )

    def test_dod_3_condicao_que_depende_de_juizo_do_facilitador(self):
        fonte = textwrap.dedent(
            """\
            branches:
              - id: BR-A-JUIZO
                line: A
                at_inject: A01
                evaluate:
                  - id: bem_conduzido
                    when:
                      facilitator_thinks_response_was_good: true
                    next: A02
                  - id: sem_juizo
                    default: true
                    next: A03
                reconverge_at: A03
            """
        )
        achado = self.um_achado(
            escreve_pack(**{"branches.yaml": fonte}), PackSite.DOCUMENT_INVALID
        )
        self.assertEqual(achado.erro.arquivo, "branches.yaml")
        self.assertPosicaoNaAncora(
            achado, fonte, "facilitator_thinks_response_was_good"
        )

    def test_t12_capability_gap_citando_objetivo_inexistente(self):
        fonte = textwrap.dedent(
            f"""\
            injects:
              - id: A01
                linha: A
                t_relative: "00:10"
                titulo_operacional: "Comunicado 01"
                objectives: [OBJ-01]
                decision_point:
                  id: DP-A01
                  question: "Suspender a matrícula online?"
                  options:
                    - id: no_federated_revocation
                      label: "Não temos como revogar a sessão federada"
                      effects:
                        {ACADEMUS_ENROLLMENT_OFFLINE}: true
                      tradeoff: "Exposição persiste; a equipe registra a lacuna"
                      capability_gap:
                        control_function: federated_session_revocation
                        objectives_affected: [OBJ-99]
              - id: A02
                linha: A
                t_relative: "00:20"
                titulo_operacional: "Comunicado 02"
                objectives: [OBJ-01]
              - id: A03
                linha: A
                t_relative: "00:30"
                titulo_operacional: "Comunicado 03"
                objectives: [OBJ-01]
            """
        )
        achado = self.um_achado(
            escreve_pack(**{"injects.yaml": fonte}), PackSite.RULE_VIOLATION
        )
        self.assertIn("pack_objectives", achado.erro.mensagem)
        self.assertEqual(
            achado.erro.caminho,
            "$.injects[0].decision_point.options[0].capability_gap"
            ".objectives_affected[0]",
        )
        self.assertPosicaoNaAncora(achado, fonte, "OBJ-99")


class OLinterColheEOBootPara(_BaseDeLint):
    """A diferenca entre `lint` e `load_pack`, e ela e a razao de o verbo existir.

    `04` §8 da nomes e listas de checagem distintos a `validate` e a `lint`. Um
    linter que relatasse um defeito por execucao mandaria o autor consertar e
    rodar de novo — seis vezes, num pack de seis documentos. Nesse regime `lint`
    nao acrescentaria nada a `validate`, e a spec nao teria por que ter os dois.
    """

    def test_os_quatro_defeitos_saem_numa_execucao_so(self):
        injects = textwrap.dedent(
            f"""\
            injects:
              - id: A01
                linha: A
                t_relative: "00:10"
                titulo_operacional: "Sem objetivo e sem noise"
              - id: A02
                linha: A
                t_relative: "00:20"
                titulo_operacional: "Comunicado 02"
                objectives: [OBJ-01]
                decision_point:
                  id: DP-A01
                  question: "Suspender a matrícula online?"
                  options:
                    - id: no_federated_revocation
                      label: "Não temos como revogar a sessão federada"
                      effects:
                        {ACADEMUS_ENROLLMENT_OFFLINE}: true
                      tradeoff: "Exposição persiste"
                      capability_gap:
                        control_function: federated_session_revocation
                        objectives_affected: [OBJ-99]
              - id: A03
                linha: A
                t_relative: "00:30"
                titulo_operacional: "Comunicado 03"
                objectives: [OBJ-01]
            """
        )
        branches = textwrap.dedent(
            f"""\
            branches:
              - id: BR-A-CONTAINMENT
                line: A
                at_inject: A01
                evaluate:
                  - id: contained_early
                    when:
                      all:
                        - event: {EVENTO_COM_ERRO_DE_DIGITACAO}
                    next: A02
                  - id: bem_conduzido
                    when:
                      facilitator_thinks_response_was_good: true
                    next: A03
                  - id: not_contained
                    default: true
                    next: A03
                reconverge_at: A03
            """
        )
        achados = self.lint(
            escreve_pack(**{"injects.yaml": injects, "branches.yaml": branches})
        )
        self.assertEqual(
            sorted((a.erro.arquivo, a.erro.site) for a in achados),
            [
                ("branches.yaml", PackSite.DOCUMENT_INVALID),
                ("branches.yaml", PackSite.RULE_VIOLATION),
                ("injects.yaml", PackSite.DOCUMENT_INVALID),
                ("injects.yaml", PackSite.RULE_VIOLATION),
            ],
        )
        # E TODOS SE LOCALIZAM. Colher sem posicao seria metade da entrega.
        self.assertTrue(all(a.posicao is not None and a.posicao.exata for a in achados))

    def test_um_documento_defeituoso_nao_esconde_o_irmao(self):
        """A granularidade POR DOCUMENTO das duas camadas — `_passos`.

        Antes desta peca, `_verify_schema` levantava no PRIMEIRO documento que
        falhasse, e `branches.yaml` vem antes de `injects.yaml` na ordem do mapa.
        Um pack com defeito nos dois so mostrava um.
        """
        injects = INJECTS_LIMPO.replace("    objectives: [OBJ-01]\n", "", 1)
        branches = BRANCHES_LIMPO.replace("    reconverge_at: A03\n", "")
        achados = self.lint(
            escreve_pack(**{"injects.yaml": injects, "branches.yaml": branches})
        )
        self.assertEqual(
            sorted(a.erro.arquivo for a in achados),
            ["branches.yaml", "injects.yaml"],
        )


class OrdemDeTRelative(_BaseDeLint):
    """A regra que `x-aurora-linter-rules` declarava e ninguem executava."""

    def test_fora_de_ordem_na_MESMA_linha_recusa(self):
        fonte = INJECTS_LIMPO.replace('t_relative: "00:30"', 't_relative: "00:05"')
        achado = self.um_achado(
            escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None}),
            PackSite.T_RELATIVE_OUT_OF_ORDER,
        )
        self.assertIn("A03", achado.erro.mensagem)
        self.assertEqual(achado.erro.caminho, "$.injects[2].t_relative")
        self.assertPosicaoNaAncora(achado, fonte, 't_relative: "00:05"')

    def test_linhas_DIFERENTES_nao_se_ordenam_entre_si(self):
        """A perna que a medicao exigiu, e sem ela a regra reprova a fonte.

        `04` §9 poe Linhas A, B e ruido em paralelo no mesmo exercicio, e o
        exemplo positivo de `injects_document` no proprio contrato declara a
        linha A ate `01:40` e o inject de ruido em `00:52`. Sob ordem GLOBAL
        aquela fixture seria recusada — regra escrita contra a fonte, que e a
        classe do B4 da terceira auditoria.
        """
        # SEM `dedent`: o fragmento e concatenado a um documento ja indentado, e
        # dedent tiraria os dois espacos que fazem dele um item da sequencia.
        fonte = INJECTS_LIMPO + (
            '  - id: R01\n'
            '    t_relative: "00:05"\n'
            '    titulo_operacional: "Comunicado de ruido"\n'
            "    noise: true\n"
        )
        self.assertEqual(
            self.lint(escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None})),
            [],
        )


class FactCheckAgainst(_BaseDeLint):
    """A quarta citacao de fato — a que nao tinha dono ate esta peca."""

    def _com_media(self, valor: str) -> str:
        # SEM `dedent`, pelo mesmo motivo do fragmento de ruido acima.
        return INJECTS_LIMPO + (
            "  - id: A04\n"
            "    linha: A\n"
            '    t_relative: "00:40"\n'
            '    titulo_operacional: "Coletiva"\n'
            "    objectives: [OBJ-01]\n"
            "    media_event:\n"
            "      type: press_call\n"
            "      deadline_minutes: 20\n"
            "      requires_response: true\n"
            f"      fact_check_against: {valor}\n"
        )

    def test_ponteiro_que_resolve_passa(self):
        fonte = self._com_media("facts.GT-A-020.records_affected")
        self.assertEqual(
            self.lint(escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None})),
            [],
        )

    def test_fato_inexistente_recusa(self):
        fonte = self._com_media("facts.GT-A-999.records_affected")
        achado = self.um_achado(
            escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None}),
            PackSite.FACT_CHECK_UNRESOLVED,
        )
        self.assertIn("GT-A-999", achado.erro.mensagem)
        self.assertIn("nao declara", achado.erro.mensagem)
        self.assertPosicaoNaAncora(achado, fonte, "fact_check_against:")

    def test_campo_inexistente_num_fato_que_EXISTE_tem_OUTRA_mensagem(self):
        """As duas metades sao defeitos diferentes e mandam procurar em lugares
        diferentes: fato errado e erro de citacao, campo errado e erro de
        projecao. Fundi-las mandaria metade dos casos ao arquivo errado.
        """
        fonte = self._com_media("facts.GT-A-020.campo_que_nao_existe")
        achado = self.um_achado(
            escreve_pack(**{"injects.yaml": fonte, "branches.yaml": None}),
            PackSite.FACT_CHECK_UNRESOLVED,
        )
        self.assertIn("existe, e nao tem o campo", achado.erro.mensagem)
        self.assertIn("records_affected", achado.erro.mensagem)


class SemIOCOperacional(_BaseDeLint):
    """`05` §5.2 e a **P7-7**, cujo gatilho declarado era esta peça.

    A PERGUNTA NÃO É REIMPLEMENTADA: `confere_ausencia_de_ioc` chama o predicado
    de `dados_sinteticos/`, o mesmo que `tools/check_synthetic_data.py` usa
    desde a Fase 0. O que faltava não era a resposta — era um **segundo
    chamador**: aquele verificador varre a árvore versionada, e `scenarios/`
    está fora do Git, então o pack nunca passava por ele.
    """

    #: Ator real e documentado, com fonte pública citável — a forma que `05`
    #: §5.2 EXIBE como legítima. O pack limpo tem de aceitá-la inteira.
    ATOR = (
        "threat_actor:\n"
        '  name: "Qilin"\n'
        "  aliases: [Agenda]\n"
        '  mitre_id: "S1242"\n'
        "  sources:\n"
        '    - "MITRE ATT&CK S1242"\n'
        "    - https://attack.mitre.org/software/S1242\n"
        '  note_to_facilitator: "Perfil público. Nenhum IOC reproduzido."\n'
    )

    def test_ator_real_com_fonte_citavel_passa(self):
        """A fonte é o ÚNICO lugar do gabarito onde nomear domínio real é o ponto.

        `05` §5.2 exige fonte pública citável; `attack.mitre.org` numa `sources`
        é **citação**, e o mesmo domínio num `source_ip` seria infraestrutura. A
        varredura não distingue as duas — por isso a isenção é de subárvore e é
        declarada, e é isto que a prova.
        """
        self.assertEqual(
            self.lint(escreve_pack(**{"ground_truth.yaml": GROUND_TRUTH + self.ATOR})),
            [],
        )

    def test_ip_roteavel_num_fato_recusa(self):
        fonte = GROUND_TRUTH.replace(
            'exercise_time: "T-9d 02:14"',
            'exercise_time: "T-9d 02:14"\n    source_ip: 45.83.220.11',
        )
        achado = self.um_achado(
            escreve_pack(**{"ground_truth.yaml": fonte}), PackSite.IOC_OPERACIONAL
        )
        self.assertIn("45.83.220.11", achado.erro.mensagem)
        self.assertEqual(achado.erro.caminho, "$.facts[0].source_ip")
        self.assertPosicaoNaAncora(achado, fonte, "source_ip:")

    def test_dominio_roteavel_FORA_de_sources_recusa(self):
        """A isenção é de `threat_actor.sources`, e de mais nada.

        Isentar por VALOR faria o mesmo domínio passar em qualquer lugar do
        documento, que é o oposto do que a §5.2 quer.
        """
        fonte = GROUND_TRUTH + self.ATOR.replace(
            "  aliases: [Agenda]\n", "  aliases: [attack.mitre.org]\n"
        )
        achado = self.um_achado(
            escreve_pack(**{"ground_truth.yaml": fonte}), PackSite.IOC_OPERACIONAL
        )
        self.assertEqual(achado.erro.caminho, "$.threat_actor.aliases[0]")

    def test_cpf_que_passa_no_digito_verificador_recusa(self):
        """`05` §3 — CPF sintético tem de FALHAR o dígito verificador."""
        # NO `actor`, e nao num campo inventado: `additionalProperties: false`
        # recusaria um `cpf:` na camada 1, e o achado sairia com dois sitios em
        # vez do que este caso quer provar. E um ator identificado por CPF e a
        # forma realista do vazamento.
        fonte = GROUND_TRUTH.replace(
            "    actor: svc_academus", "    actor: 529.982.247-25"
        )
        achado = self.um_achado(
            escreve_pack(**{"ground_truth.yaml": fonte}), PackSite.IOC_OPERACIONAL
        )
        self.assertIn("CPF", achado.erro.mensagem)

    def test_o_predicado_e_o_MESMO_do_verificador_da_arvore(self):
        """Uma implementação, três chamadores — e este teste é o que o prova.

        Sem esta perna, alguém reimplementaria as faixas no linter e as duas
        respostas divergiriam no dia em que uma delas mudasse. A divergência
        aqui **não falha alto**: ela deixa passar.
        """
        import dados_sinteticos
        from range_core.engine.loader import pack_loader

        self.assertIs(pack_loader.achados_no_valor, dados_sinteticos.achados_no_valor)

    def test_dominio_embutido_em_PROSA_escapa_e_isso_e_limite_declarado(self):
        """O limite medido, e ele é teste para não virar cobertura suposta.

        O predicado classifica VALORES: `hostnames_candidatos` desiste quando o
        texto tem espaço. Um domínio dentro de `note_to_facilitator` passa.

        **O teste afirma o limite, e não o comportamento desejado.** Ele fica
        vermelho no dia em que alguém estender a varredura para prosa — que é o
        aviso certo, porque essa extensão muda o comportamento de
        `tools/check_synthetic_data.py` sobre a árvore inteira.
        """
        fonte = GROUND_TRUTH + self.ATOR.replace(
            "Nenhum IOC reproduzido.", "C2 observado em evil-infra.net"
        )
        self.assertEqual(
            self.lint(escreve_pack(**{"ground_truth.yaml": fonte})), []
        )


class AsFlagsVemDoManifesto(_BaseDeLint):
    """`04` §8.2 proibe DERIVAR de contexto; ler campo declarado nao e derivar."""

    def test_o_domain_do_manifesto_resolve_o_flags_yaml_do_adapter(self):
        flags = lint_de_cenario.flags_do_pack(escreve_pack(), REPO_ROOT)
        self.assertTrue(flags.source.endswith("domains/academus/flags.yaml"))
        self.assertIn(ACADEMUS_ENROLLMENT_OFFLINE, flags.specs)

    def test_manifesto_sem_domain_recusa_em_vez_de_adivinhar(self):
        pack = escreve_pack(**{"manifest.yaml": MANIFESTO.replace("domain: academus\n", "")})
        with self.assertRaises(lint_de_cenario.LintRecusado) as capturado:
            lint_de_cenario.flags_do_pack(pack, REPO_ROOT)
        self.assertIn("domain", str(capturado.exception))

    def test_adapter_sem_flags_yaml_recusa_nomeando_o_caminho(self):
        """`prontus` NAO serve para este caso, e a razao e informacao.

        O stub dele TEM `flags.yaml` — `domains/prontus/flags.yaml` existe desde
        a Fase 1, e e o que prova a fronteira de `01` §2. Um adapter sem
        declaracao de flags nao existe na arvore, entao o caso e exercitado com
        um dominio que nao existe: e a mesma situacao do ponto de vista deste
        caminho, e nao depende de nenhum adapter continuar incompleto.
        """
        pack = escreve_pack(
            **{
                "manifest.yaml": MANIFESTO.replace(
                    "domain: academus", "domain: dominio_inexistente"
                )
            }
        )
        with self.assertRaises(lint_de_cenario.LintRecusado) as capturado:
            lint_de_cenario.flags_do_pack(pack, REPO_ROOT)
        self.assertIn("dominio_inexistente", str(capturado.exception))
        self.assertIn("--flags", str(capturado.exception))


class OQueNaoEColhido(_BaseDeLint):
    """As recusas de `_abre` sobem. Sem pack lido nao ha o que relatar."""

    def test_diretorio_inexistente_levanta_em_vez_de_virar_achado(self):
        with self.assertRaises(PackError) as capturado:
            self.lint(Path("nao/existe/em/lugar/nenhum"))
        self.assertEqual(capturado.exception.site, PackSite.PACK_DIR_MISSING)

    def test_pack_sem_manifesto_levanta(self):
        pack = escreve_pack(**{"manifest.yaml": None})
        with self.assertRaises(PackError) as capturado:
            self.lint(pack)
        self.assertEqual(capturado.exception.site, PackSite.REQUIRED_FILE_MISSING)


class ASaidaDoComando(_BaseDeLint):
    """Codigo de saida e destino do texto — `04` §8 poe `lint` no CI."""

    def _roda(self, pack_dir: Path) -> tuple[int, str, str]:
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            codigo = cli.main(["scenario", "lint", str(pack_dir)])
        return codigo, saida.getvalue(), erro.getvalue()

    def test_pack_limpo_sai_zero(self):
        codigo, saida, _ = self._roda(escreve_pack())
        self.assertEqual(codigo, cli.LIMPO)
        self.assertIn("sem achados", saida)

    def test_pack_com_achado_sai_dois_e_escreve_no_stderr(self):
        fonte = BRANCHES_LIMPO.replace(
            VPN_ACCESS_REVOKED, EVENTO_COM_ERRO_DE_DIGITACAO, 1
        )
        codigo, saida, erro = self._roda(escreve_pack(**{"branches.yaml": fonte}))
        self.assertEqual(codigo, cli.RECUSADO)
        self.assertEqual(saida, "")
        self.assertIn("branches.yaml:", erro)
        self.assertIn("1 achado.", erro)

    def test_o_codigo_de_recusa_e_o_MESMO_do_materialize(self):
        """Dois verbos sinalizando recusa com codigos diferentes fariam o job de
        CI depender de qual deles falhou."""
        self.assertEqual(cli.RECUSADO, 2)


class OMapaDePosicoes(unittest.TestCase):
    """O resolvedor, e o fallback que se declara em vez de mentir."""

    FONTE = 'injects:\n  - id: A01\n    t_relative: "00:10"\n'

    def test_resolve_caminho_exato(self):
        posicao = MapaDePosicoes.do_texto(self.FONTE).de("$.injects[0].t_relative")
        self.assertTrue(posicao.exata)
        linha = self.FONTE.splitlines()[posicao.linha - 1]
        # A coluna e DERIVADA da fonte, e nao escrita a mao.
        self.assertEqual(posicao.coluna - 1, linha.index('"00:10"'))

    def test_caminho_que_nao_existe_devolve_o_ANCESTRAL_e_se_declara(self):
        """Cair para o ancestral em silencio apontaria uma linha errada com a
        mesma confianca de uma certa, e a exigencia de T12 e sobre localizar.
        """
        posicao = MapaDePosicoes.do_texto(self.FONTE).de("$.injects[0].nao_existe")
        self.assertFalse(posicao.exata)
        self.assertEqual(posicao.caminho_resolvido, "$.injects[0]")

    def test_yaml_ilegivel_devolve_mapa_vazio_em_vez_de_levantar(self):
        """Quem recusa documento ilegivel e o passo de leitura, com sitio
        proprio. Um segundo levantamento aqui viraria rastro de pilha no meio do
        relatorio.
        """
        self.assertIsNone(MapaDePosicoes.do_texto("a: [1,\n  b: {").de("$.a"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
