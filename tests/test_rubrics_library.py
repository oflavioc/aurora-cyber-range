"""A biblioteca de rubricas BARS — identidade, níveis e o que o contrato não alcança.

`contracts/rubrics.schema.yaml` verifica FORMA, e o job `contratos` a valida
contra os nove arquivos reais. O que este teste cobre é o que o schema **não
pode** cobrir, e por isso vive em `range_core/rubrics/library.py`:

1. o nome do arquivo é o identificador, e o conteúdo tem de concordar com ele;
2. as chaves de `anchors` são exatamente os cinco níveis `0..4` — inalcançável
   por JSON Schema porque as chaves são inteiros, e `properties`/`required`/
   `propertyNames` só casam nome de propriedade string.

Cada teste planta a biblioteca inteira num diretório temporário e chama a MESMA
função que a produção chama. Verificador que só roda contra a árvore boa nunca
prova que reprova.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from range_core.rubrics.library import (
    NIVEIS,
    RUBRICS_DIR,
    RubricLibraryError,
    load_library,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: As nove competências de `03` §2.3, com a versão que a spec fixa para três
#: delas em `04` §2 — `incident_triage.v2`, `crisis_communication.v2` e
#: `integrity_assurance.v1`. As demais em v1.
ESPERADAS = {
    "analytical_rigor.v1",
    "business_continuity.v1",
    "crisis_communication.v2",
    "cross_functional_coordination.v1",
    "escalation.v1",
    "incident_triage.v2",
    "integrity_assurance.v1",
    "regulatory_compliance.v1",
    "risk_decision.v1",
}


class BibliotecaReal(unittest.TestCase):
    """A árvore em execução. Sem isto, nenhuma recusa abaixo significa nada."""

    def test_as_nove_competencias_carregam(self):
        biblioteca = load_library()
        self.assertEqual(set(biblioteca), ESPERADAS)

    def test_toda_rubrica_tem_os_cinco_niveis_com_texto(self):
        for rubric_id, rubrica in sorted(load_library().items()):
            with self.subTest(rubrica=rubric_id):
                self.assertEqual(set(rubrica.anchors), set(NIVEIS))
                for nivel in sorted(NIVEIS):
                    self.assertTrue(rubrica.anchor(nivel).strip())

    def test_as_tres_que_o_manifesto_normativo_cita_existem(self):
        """`04` §2 fixa `[incident_triage.v2, crisis_communication.v2,
        integrity_assurance.v1]`. Se a biblioteca não as tiver, o manifesto
        normativo da spec descreve um pack que não carrega."""
        biblioteca = load_library()
        for rubric_id in (
            "incident_triage.v2",
            "crisis_communication.v2",
            "integrity_assurance.v1",
        ):
            with self.subTest(rubrica=rubric_id):
                self.assertIn(rubric_id, biblioteca)

    def test_a_escala_e_a_mesma_em_todas(self):
        """Comparabilidade entre competências depende disso — `03` §2.2."""
        escalas = {r.scale for r in load_library().values()}
        self.assertEqual(escalas, {"0-4"})


class _ComCopia(unittest.TestCase):
    """Base: copia a biblioteca para diretório temporário e planta um defeito."""

    def copia(self) -> Path:
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        destino = Path(temporario.name) / "rubrics"
        destino.mkdir()
        for caminho in sorted(RUBRICS_DIR.glob("*.yaml")):
            shutil.copy2(caminho, destino / caminho.name)
        return destino

    def recusa(self, destino: Path, trecho: str) -> RubricLibraryError:
        with self.assertRaises(RubricLibraryError) as capturado:
            load_library(destino)
        self.assertIn(trecho, str(capturado.exception))
        return capturado.exception


class IdentidadeEntreNomeEConteudo(_ComCopia):
    """O nome do arquivo é o id que `required_rubrics` cita — `00` §5.8."""

    def test_arquivo_renomeado_reprova(self):
        """Renomear troca o id sem mudar o conteúdo.

        Sem esta guarda, `incident_triage.v2.yaml` copiado para
        `escalation.v1.yaml` faria o pack casar `escalation.v1` e pontuar
        escalação com as âncoras de triagem — nada acusaria, e o AAR sairia com
        a competência errada medida.
        """
        destino = self.copia()
        (destino / "incident_triage.v2.yaml").rename(destino / "escalation.v2.yaml")
        self.recusa(destino, "o arquivo diz")

    def test_versao_do_conteudo_divergindo_do_nome_reprova(self):
        destino = self.copia()
        caminho = destino / "escalation.v1.yaml"
        caminho.write_text(
            caminho.read_text(encoding="utf-8").replace("version: v1", "version: v3"),
            encoding="utf-8",
        )
        self.recusa(destino, "o arquivo diz")


class OsCincoNiveis(_ComCopia):
    """O que o JSON Schema não alcança, porque as chaves são inteiros."""

    def test_cinco_ancoras_fora_da_escala_reprovam(self):
        """`{1..5}` tem cardinalidade cinco e passa no contrato.

        É exatamente o caso que motiva esta camada: o avaliador que pontuasse
        `0` receberia "nível inexistente" no meio do exercício.
        """
        destino = self.copia()
        caminho = destino / "risk_decision.v1.yaml"
        texto = caminho.read_text(encoding="utf-8")
        for antes, depois in ((" 4:", " 5:"), (" 3:", " 4:"), (" 2:", " 3:"),
                              (" 1:", " 2:"), (" 0:", " 1:")):
            texto = texto.replace(antes, depois, 1)
        caminho.write_text(texto, encoding="utf-8")
        self.recusa(destino, "chaves fora da escala 0-4")

    def test_nivel_ausente_reprova(self):
        destino = self.copia()
        caminho = destino / "escalation.v1.yaml"
        linhas = [
            linha
            for linha in caminho.read_text(encoding="utf-8").splitlines()
            if not linha.lstrip().startswith("4:")
        ]
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        self.recusa(destino, "niveis ausentes")


class BibliotecaVazia(_ComCopia):
    def test_raiz_sem_rubrica_reprova_por_biblioteca_e_nao_por_pack(self):
        """A mensagem importa tanto quanto a recusa.

        Biblioteca vazia resolveria `required_rubrics` contra conjunto vazio e
        recusaria todo pack por "rubrica ausente" — a mensagem errada para o
        defeito certo, e o operador iria procurar o erro no pack.
        """
        destino = self.copia()
        for caminho in destino.glob("*.yaml"):
            caminho.unlink()
        self.recusa(destino, "nenhuma rubrica")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
