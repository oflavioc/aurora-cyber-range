"""O linter de fato citado — item 8 da DoD, `06` T8, `00` §5.10.

*"Fato citado no `GM_NOTES.md` e ausente do `ground_truth.yaml` e recusado."*

TRES LADOS CITAM FATO, E ESTA SUITE COBRE OS QUE TEM SUJEITO
==============================================================
    GM_NOTES.md          prosa — o criterio que a DoD nomeia
    materializes_facts   inject que materializa fato (`04` §5)
    projects_facts       fonte de evidencia que projeta fato (`08` §7)

**A FRONTEIRA, DECLARADA E NAO SUPOSTA.** Medido nesta arvore:

    scenarios/                            VAZIO — nao ha pack de producao em
                                          disco. O produtor existe desde a peca
                                          2, e materializar exige o banco
                                          semeado.
    tests/fixtures/pack_minimo/injects.yaml   NAO tem `materializes_facts`.
    MANIFEST.json                         nao existe em lugar nenhum;
                                          `evidence build` e da Fase 9.

Entao **nenhum dos tres tem artefato de PRODUCAO hoje**. A terceira perna —
`projects_facts` — esta escrita no linter e **sem sujeito**: ela roda contra
dado montado aqui, e nao contra MANIFEST nenhum. Isso esta dito em vez de
escondido, e e a diferenca entre cobertura e aparencia de cobertura.

O QUE HA DE REAL, E POR QUE ELE VALE
=====================================
`tests/fixtures/pack_completo.materializa()` escreve um pacote COMPLETO em disco
e o loader o carrega inteiro. Nao e arvore montada a mao num dicionario de
teste: e diretorio, com `ground_truth.yaml` gerado em runtime, que atravessa
`load_pack` pelos mesmos seis passos que o boot usa.

E o linter roda **na carga**, e nao so quando alguem o chama — entao as recusas
abaixo sao as do BOOT, com o sitio `PackSite.CITACAO_DE_FATO_INVALIDA`.

**E a licao do PR #57 aplicada:** la, quatro testes corretos julgavam arvores
montadas a mao, e o gerador de producao — que escrevia `since: containment_declared`
— nunca passava por nenhum deles. Uma guarda que so ve o duplo prova o duplo.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "fixtures"))

from range_core.engine.citacoes import (  # noqa: E402
    CitacaoInvalida,
    citacoes_de_fato,
    confere_citacoes_de_fato,
)
from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import (  # noqa: E402
    AdapterFlags,
    PackError,
    PackSite,
    load_pack,
)

from pack_completo import materializa  # noqa: E402

CONTRATOS = contract_source.read_contracts()
FORMA = contract_source.fact_id_pattern(CONTRATOS)

FLAGS_DO_ADAPTER = Path("domains") / "academus" / "flags.yaml"
FLAGS = AdapterFlags.from_document(
    yaml.safe_load((REPO_ROOT / FLAGS_DO_ADAPTER).read_text(encoding="utf-8")),
    source=FLAGS_DO_ADAPTER.as_posix(),
)

#: O pacote COMPLETO, materializado em temporario — artefato de verdade.
PACK = materializa()

#: O fato que o `ground_truth.yaml` daquele pacote declara.
FATO_DECLARADO = "GT-FIXTURE-001"


class AFormaVemDoContrato(unittest.TestCase):
    """Nao ha regex literal no linter — `04` §4.1."""

    def test_a_forma_e_a_de_fact_id_pattern(self) -> None:
        self.assertEqual(FORMA, "^GT-[A-Z0-9]+-[0-9]+$")

    def test_contrato_sem_o_def_recusa_alto(self) -> None:
        with self.assertRaises(contract_source.ContractSourceError) as capturado:
            contract_source.fact_id_pattern({"ground_truth": {"$defs": {}}})
        self.assertIn("fact_id_pattern", str(capturado.exception))


class AsDuasRedes(unittest.TestCase):
    """A rede 2 e o que impede o predicado estreito — e ela e o eixo."""

    def test_bem_formado_e_reconhecido_no_meio_da_prosa(self) -> None:
        bem, quase = citacoes_de_fato(
            f"O acesso inicial ({FATO_DECLARADO}) precede tudo.", forma=FORMA
        )
        self.assertEqual({FATO_DECLARADO}, bem)
        self.assertEqual(set(), quase)

    def test_as_TRES_formas_nao_casadas_sao_pegas_pela_rede_2(self) -> None:
        """`gt-a-031`, `GT-A-31` e `GTA031` — as tres do enunciado.

        `GT-A-31` CASA a forma: `A` e `[A-Z0-9]+` e `31` e `[0-9]+`. Entao ela
        cai na rede 1 e e pega por NAO EXISTIR, e nao por forma. As outras duas
        nao casam, e so a rede 2 as ve — sem ela, um `gt-a-031` no `GM_NOTES`
        seria invisivel ao linter feito para pega-lo.
        """
        bem, quase = citacoes_de_fato("gt-a-031 e GTA031 no meio do texto", forma=FORMA)
        self.assertEqual(set(), bem)
        self.assertEqual({"gt-a-031", "GTA031"}, quase)

        bem, quase = citacoes_de_fato("GT-A-31", forma=FORMA)
        self.assertEqual({"GT-A-31"}, bem, "GT-A-31 casa a forma — cai na rede 1")
        self.assertEqual(set(), quase)

    def test_bem_formado_NAO_aparece_tambem_como_quase(self) -> None:
        """Sem a subtracao, todo pack integro seria recusado pela rede 2."""
        _, quase = citacoes_de_fato(FATO_DECLARADO, forma=FORMA)
        self.assertEqual(set(), quase)

    def test_texto_sem_citacao_nenhuma_nao_dispara(self) -> None:
        bem, quase = citacoes_de_fato("prosa sem identificador algum", forma=FORMA)
        self.assertEqual((set(), set()), (bem, quase))


class OsTresLadosSaoConferidos(unittest.TestCase):
    """A funcao do nucleo, contra os tres nomes de fonte.

    `projects_facts` roda contra dado montado aqui — **nao ha MANIFEST na
    arvore**, e a suite declara isso no cabecalho em vez de simular cobertura.
    """

    def _confere(self, fontes) -> None:
        confere_citacoes_de_fato(
            declarados={FATO_DECLARADO}, fontes=fontes, forma=FORMA
        )

    def test_os_tres_passam_com_fato_declarado(self) -> None:
        self._confere(
            {
                "GM_NOTES.md": f"o fato {FATO_DECLARADO} abre a linha",
                "materializes_facts": [FATO_DECLARADO],
                "projects_facts": [FATO_DECLARADO],
            }
        )

    def test_cada_um_dos_tres_RECUSA_fato_ausente(self) -> None:
        for nome, conteudo in (
            ("GM_NOTES.md", "o fato GT-FANTASMA-999 explica tudo"),
            ("materializes_facts", ["GT-FANTASMA-999"]),
            ("projects_facts", ["GT-FANTASMA-999"]),
        ):
            with self.subTest(fonte=nome):
                with self.assertRaises(CitacaoInvalida) as capturado:
                    self._confere({nome: conteudo})
                mensagem = str(capturado.exception)
                self.assertIn(nome, mensagem, "a recusa tem de dizer ONDE")
                self.assertIn("GT-FANTASMA-999", mensagem)

    def test_cada_um_dos_tres_RECUSA_forma_nao_casada(self) -> None:
        for nome, conteudo in (
            ("GM_NOTES.md", "ver gt-fixture-001 na tabela"),
            ("materializes_facts", ["GTFIXTURE001"]),
            ("projects_facts", ["gt_fixture_001"]),
        ):
            with self.subTest(fonte=nome):
                with self.assertRaises(CitacaoInvalida) as capturado:
                    self._confere({nome: conteudo})
                self.assertIn("nao casa o contrato", str(capturado.exception))

    def test_a_recusa_nomeia_a_fonte_e_nao_o_agregado(self) -> None:
        """Uniao de fontes esconderia qual dos tres esta quebrado."""
        with self.assertRaises(CitacaoInvalida) as capturado:
            self._confere(
                {
                    "GM_NOTES.md": f"tudo certo com {FATO_DECLARADO}",
                    "materializes_facts": ["GT-FANTASMA-999"],
                }
            )
        self.assertIn("materializes_facts", str(capturado.exception))


class ContraOPackMATERIALIZADO(unittest.TestCase):
    """PASSO A — contra artefato de verdade, e nao contra arvore montada a mao.

    O pacote e escrito em disco por `pack_completo.materializa()` e carregado
    por `load_pack` pelos mesmos seis passos do boot. As recusas abaixo sao as
    do BOOT.

    **NAO e o pack de producao**, e a diferenca esta declarada no cabecalho
    desta suite: `scenarios/` esta vazio, e materializar o de producao exige o
    banco semeado. A licao do PR #57 fica valendo — esta cobertura e melhor que
    dicionario de teste e pior que artefato de producao.
    """

    def _copia(self) -> Path:
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        destino = Path(temporario.name) / "pack"
        shutil.copytree(PACK, destino)
        return destino

    def _carrega(self, diretorio: Path):
        return load_pack(diretorio, contracts=CONTRATOS, adapter_flags=FLAGS)

    def test_CONTROLE_POSITIVO_o_pack_integro_carrega(self) -> None:
        """Sem ele, uma recusa que negasse todo pack satisfaria os negativos."""
        pack = self._carrega(self._copia())
        self.assertEqual(pack.schema_version, 2)

    def test_pack_SEM_GM_NOTES_carrega(self) -> None:
        """`GM_NOTES.md` e `optional` — pacote apenas-manifesto nao o tem."""
        destino = self._copia()
        self.assertFalse((destino / "GM_NOTES.md").exists())
        self._carrega(destino)

    def test_GM_NOTES_com_fato_AUSENTE_recusa_o_pack_NA_CARGA(self) -> None:
        """O criterio do item 8 da DoD, sobre o artefato em disco."""
        destino = self._copia()
        (destino / "GM_NOTES.md").write_text(
            "# GM_NOTES\n\nO fato GT-FANTASMA-999 abre a linha A.\n", encoding="utf-8"
        )
        with self.assertRaises(PackError) as capturado:
            self._carrega(destino)
        self.assertEqual(capturado.exception.site, PackSite.CITACAO_DE_FATO_INVALIDA)
        self.assertIn("GT-FANTASMA-999", str(capturado.exception))
        self.assertIn("GM_NOTES.md", str(capturado.exception))

    def test_GM_NOTES_com_fato_em_FORMA_NAO_CASADA_recusa(self) -> None:
        """A perna que prova que o predicado nao e estreito.

        `gt-fixture-001` aponta para um fato que EXISTE — mas na forma errada,
        e nessa forma ele nunca resolveria. Um linter que so procurasse
        identificadores bem formados nao o veria, e o autor acharia que citou.
        """
        destino = self._copia()
        (destino / "GM_NOTES.md").write_text(
            "# GM_NOTES\n\nVer gt-fixture-001 na tabela.\n", encoding="utf-8"
        )
        with self.assertRaises(PackError) as capturado:
            self._carrega(destino)
        self.assertEqual(capturado.exception.site, PackSite.CITACAO_DE_FATO_INVALIDA)
        self.assertIn("nao casa o contrato", str(capturado.exception))

    def test_GM_NOTES_com_fato_DECLARADO_carrega(self) -> None:
        """O outro controle positivo: citar direito nao recusa."""
        destino = self._copia()
        (destino / "GM_NOTES.md").write_text(
            f"# GM_NOTES\n\nO fato {FATO_DECLARADO} abre a linha A.\n", encoding="utf-8"
        )
        self._carrega(destino)

    def _com_materializes_facts(self, valor: list[str]) -> Path:
        destino = self._copia()
        caminho = destino / "injects.yaml"
        documento = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        documento["injects"][0]["materializes_facts"] = valor
        caminho.write_text(yaml.safe_dump(documento, sort_keys=False), encoding="utf-8")
        return destino

    def test_materializes_facts_com_fato_DECLARADO_carrega(self) -> None:
        self._carrega(self._com_materializes_facts([FATO_DECLARADO]))


class OsOutrosDoisLadosJaTinhamGUARDA(unittest.TestCase):
    """A MEDICAO QUE MUDOU O DESENHO, e ela esta aqui para nao ser esquecida.

    O linter foi pedido para cobrir TRES lados. Medido antes de escrever: dois
    deles ja tinham guarda, e melhor — `$ref` para a forma (PR #59) e
    `x-aurora-ref: pack_facts` para a existencia (desde a Fase 2). Acrescenta-los
    ao linter seria a TERCEIRA implementacao de *"este fato existe?"*, dentro do
    modulo que existe para essa pergunta ter uma resposta so.

    Entao `confere_citacoes_do_pack` alimenta **so** o `GM_NOTES.md` — a unica
    das tres portas sem guarda, e por razao ESTRUTURAL: `$ref` e `x-aurora-ref`
    operam sobre documento de maquina, e prosa nao e documento de maquina.

    ESTA CLASSE AFIRMA A COBERTURA ALHEIA. Sem ela, a decisao de nao cobrir
    ficaria como prosa num docstring — e no dia em que alguem tirasse o
    `x-aurora-ref` de `materializes_facts`, o lado ficaria descoberto e o
    comentario continuaria dizendo que estava coberto. E a §1.6.
    """

    def _copia(self) -> Path:
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        destino = Path(temporario.name) / "pack"
        shutil.copytree(PACK, destino)
        return destino

    def _com_materializes_facts(self, valor: list[str]) -> Path:
        destino = self._copia()
        caminho = destino / "injects.yaml"
        documento = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        documento["injects"][0]["materializes_facts"] = valor
        caminho.write_text(yaml.safe_dump(documento, sort_keys=False), encoding="utf-8")
        return destino

    def _recusa(self, destino: Path) -> PackError:
        with self.assertRaises(PackError) as capturado:
            load_pack(destino, contracts=CONTRATOS, adapter_flags=FLAGS)
        return capturado.exception

    def test_materializes_facts_com_fato_AUSENTE_e_recusado_por_x_aurora_ref(self) -> None:
        """`rule_violation`, e nao o sitio do linter — e esse e o ponto.

        O fato inexistente e pego pela integridade referencial que a Fase 2 ja
        entregou, ANTES de o linter rodar. Se este teste passar a devolver
        `citacao_de_fato_invalida`, alguem tirou o `x-aurora-ref` e o linter
        virou a unica guarda — o que muda o desenho e tem de ser deliberado.
        """
        erro = self._recusa(self._com_materializes_facts(["GT-FANTASMA-999"]))
        self.assertEqual(erro.site, PackSite.RULE_VIOLATION)
        self.assertIn("pack_facts", str(erro))

    def test_materializes_facts_em_FORMA_NAO_CASADA_e_recusado_pelo_schema(self) -> None:
        """`document_invalid` — o `$ref` do PR #59, na camada 1.

        `gt-fixture-001` nao casa `^GT-[A-Z0-9]+-[0-9]+$`, e a recusa acontece na
        validacao de schema. Antes do #59 o campo era `type: string` livre e isto
        passaria — a fixture negativa daquele PR cobre o contrato; esta cobre o
        artefato em disco.
        """
        erro = self._recusa(self._com_materializes_facts(["gt-fixture-001"]))
        self.assertEqual(erro.site, PackSite.DOCUMENT_INVALID)

    def test_projects_facts_tem_o_MESMO_par_no_contrato_de_evidencia(self) -> None:
        """A terceira porta, conferida no CONTRATO por nao haver artefato.

        Nao ha `MANIFEST.json` na arvore — `evidence build` e da Fase 9 —, entao
        nao ha o que carregar. O que da para afirmar hoje e que o mecanismo que
        o julgara existe e e o mesmo par: forma por `$ref`, existencia por
        `x-aurora-ref`. Afirmar mais que isso seria atestacao.
        """
        evidencia = CONTRATOS["evidence"]
        fonte = evidencia["$defs"]["source"]["properties"]["projects_facts"]["items"]
        self.assertIn("fact_id_pattern", str(fonte.get("allOf")))
        self.assertEqual("pack_facts", fonte.get("x-aurora-ref"))


if __name__ == "__main__":
    unittest.main()
