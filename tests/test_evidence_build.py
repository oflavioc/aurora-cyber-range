"""`evidence build` e `evidence verify` — itens 2 e 3 da DoD da Fase 9.

O QUE ESTA SUITE FECHA
======================
`07` §Fase 9, item 2: *"`range-cli evidence verify` valida consistencia fato →
projecoes, dirigido por fato"*. Item 3: *"`precursor_events.jsonl` e reproduzivel
a partir do ground truth; edicao manual detectada por hash"*.

Os dois sao o mesmo mecanismo visto de dois angulos, e e isso que os torna
baratos: **a projecao e funcao pura de (ground truth, geradores)**, entao
conferir e reprojetar em memoria e comparar com o disco. Nao ha regra de
validacao escrita a mao — o oraculo e o proprio produtor, rodado de novo.

E ISSO ALCANCA O QUE O ELENCO NAO ALCANCA. A peca 1 declarou o limite: o
oraculo de `elenco.py` afirma ausencia de invencao para ENDERECO, que tem forma
fechada; um ator inventado que nao colidisse com nada passaria. A reprojecao o
pega — o byte diverge, qualquer que seja a natureza da diferenca.

A EDICAO MANUAL E O CASO QUE `08` §2 NOMEIA
============================================
*"`precursor_events.jsonl` deixa de ser artefato autoral: e gerado como
projecao."* O risco do artefato autoral nao e ele nascer errado — e ele ser
**editado depois**, ficando incoerente com as outras fontes sem que nada acuse.
O `sha256` por arquivo no `MANIFEST.json` e o que torna isso detectavel, e o
`ground_truth_hash` fecha o outro lado: ground truth editado sem rebuild.

`verify` NAO ESCREVE, E ISSO E CONTRATO
========================================
`04` §8.1 (a): as allowlists de quem opera o repositorio liberam os subcomandos
que so LEEM — e `evidence verify` e nomeado la. Um verbo de conferencia que
escrevesse (ainda que "so para comparar") sairia dessa classe sem que a
allowlist percebesse. R7 §3 diz o mesmo para todo stage: verificacao nunca
escreve na arvore.
"""

from __future__ import annotations

import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from range_core.engine.loader import contract_source

banner = importlib.import_module("range_core.evidence.banner")
build = importlib.import_module("range_core.evidence.build")
geradores_mod = importlib.import_module("domains.academus.evidence_generators")
linha_a = importlib.import_module("domains.academus.seed.linha_a")

CONTRATOS = contract_source.read_contracts()
SEED = 424242
PACK = "ransomware-universidade"

#: O `ground_truth.yaml` do pack, em bytes — e sobre BYTES que o hash e feito.
#: `hash_do_ground_truth` recebe bytes de proposito: o que se quer detectar e a
#: edicao do ARQUIVO, e hash da estrutura parseada seria insensivel a comentario
#: (onde o autor escreve o que o gabarito significa) e a reordenacao de chave.
def _ground_truth_bytes():
    import yaml

    documento = {"facts": linha_a.facts(SEED)}
    return yaml.safe_dump(documento, allow_unicode=True, sort_keys=False).encode("utf-8")


def _contexto():
    return {
        "geradores": geradores_mod.geradores(CONTRATOS),
        "formatos": contract_source.formatos_por_fonte(CONTRATOS),
        "banner": banner.texto(CONTRATOS),
    }


class ABase(unittest.TestCase):
    """Constroi num diretorio TEMPORARIO — a arvore nunca e tocada (R7 §3)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aurora-evidence-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.gt = _ground_truth_bytes()
        self.manifesto = build.construir(
            self.gt,
            destino=self.tmp,
            pack_id=PACK,
            random_seed=SEED,
            **_contexto(),
        )

    def _conferir(self):
        return build.conferir(
            self.tmp, self.gt, contratos=CONTRATOS, **_contexto()
        )

    def _arquivo(self, nome):
        return self.tmp / nome


class AConstrucaoEscreveOPacote(ABase):
    def test_escreve_um_arquivo_por_fonte_declarada(self):
        fontes = {s["file"] for s in self.manifesto["sources"]}
        for nome in fontes:
            self.assertTrue(self._arquivo(nome).exists(), nome)

    def test_escreve_o_MANIFEST_json(self):
        alvo = self._arquivo(build.MANIFESTO)
        self.assertTrue(alvo.exists())
        self.assertEqual(json.loads(alvo.read_text(encoding="utf-8")), self.manifesto)

    def test_o_manifesto_escrito_VALIDA_contra_o_contrato(self):
        manifesto_mod = importlib.import_module("range_core.evidence.manifesto")
        em_disco = json.loads(self._arquivo(build.MANIFESTO).read_text(encoding="utf-8"))
        self.assertEqual(manifesto_mod.erros_de_schema(em_disco, CONTRATOS), [])

    def test_todo_arquivo_abre_com_o_banner(self):
        texto = banner.texto(CONTRATOS)
        for source in self.manifesto["sources"]:
            conteudo = self._arquivo(source["file"]).read_text(encoding="utf-8")
            self.assertTrue(
                banner.tem_banner(conteudo, source["format"], texto), source["file"]
            )

    def test_escreve_com_LF_e_nunca_CRLF(self):
        """R7 §2 — o gerador escreve com `newline="\\n"` explicito.

        A licao de origem e a R2 §2: 56 de 74 hashes "falharam" num checkout
        Windows e era CRLF, nao divergencia. Aqui NAO HA blob de Git a que
        recorrer — `scenarios/` esta fora do Git desde a Fase 5 —, entao a
        disciplina tem de estar no produtor.
        """
        for source in self.manifesto["sources"]:
            bruto = self._arquivo(source["file"]).read_bytes()
            self.assertNotIn(b"\r\n", bruto, source["file"])

    def test_o_sha256_do_manifesto_confere_com_o_BYTE_em_disco(self):
        import hashlib

        for source in self.manifesto["sources"]:
            bruto = self._arquivo(source["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(bruto).hexdigest(), source["sha256"])

    def test_dois_builds_produzem_BYTES_identicos(self):
        outro = Path(tempfile.mkdtemp(prefix="aurora-evidence-2-"))
        self.addCleanup(shutil.rmtree, outro, ignore_errors=True)
        build.construir(
            self.gt, destino=outro, pack_id=PACK, random_seed=SEED, **_contexto()
        )
        for source in self.manifesto["sources"]:
            self.assertEqual(
                self._arquivo(source["file"]).read_bytes(),
                (outro / source["file"]).read_bytes(),
                source["file"],
            )


class AConferenciaEDirigidaPorFato(ABase):
    """Item 2."""

    def test_pacote_recem_construido_nao_tem_achado(self):
        self.assertEqual(self._conferir(), [])

    def test_arquivo_EDITADO_A_MAO_e_detectado_pelo_hash(self):
        """Item 3, e o caso que `08` §2 nomeia."""
        alvo = self._arquivo("vpn.log")
        alvo.write_text(
            alvo.read_text(encoding="utf-8") + "\nlinha acrescentada a mao",
            encoding="utf-8",
            newline="\n",
        )
        achados = self._conferir()
        self.assertTrue(achados)
        self.assertTrue(any("vpn.log" in a for a in achados), achados)

    def test_GROUND_TRUTH_editado_sem_rebuild_e_detectado(self):
        """O outro lado da amarracao: `generated_from.ground_truth_hash`."""
        achados = build.conferir(
            self.tmp, self.gt + b"\n# comentario novo\n", contratos=CONTRATOS, **_contexto()
        )
        self.assertTrue(any("ground_truth" in a for a in achados), achados)

    def test_arquivo_AUSENTE_e_detectado(self):
        self._arquivo("vpn.log").unlink()
        achados = self._conferir()
        self.assertTrue(any("vpn.log" in a for a in achados), achados)

    def test_arquivo_A_MAIS_no_diretorio_e_detectado(self):
        """Arquivo que o manifesto nao declara e conteudo autoral entrando pela
        porta dos fundos — e a cobertura de `08` §7 deixaria de descrever o que
        existe."""
        self._arquivo("anotacoes.txt").write_text("nota", encoding="utf-8", newline="\n")
        achados = self._conferir()
        self.assertTrue(any("anotacoes.txt" in a for a in achados), achados)

    def test_MANIFEST_ausente_e_detectado(self):
        self._arquivo(build.MANIFESTO).unlink()
        self.assertTrue(self._conferir())

    def test_a_conferencia_e_DIRIGIDA_POR_FATO(self):
        """`06` T13: *"para cada `fact_id`, todas as projecoes declaradas
        existem"*. O manifesto declara a cobertura; a conferencia a cruza com o
        ground truth, e nao com o que achou no disco."""
        declarados = {
            f for s in self.manifesto["sources"] for f in s["projects_facts"]
        }
        com_projecao = {
            f["fact_id"] for f in linha_a.facts(SEED) if f.get("projections")
        }
        self.assertEqual(declarados, com_projecao)

    def test_a_conferencia_NAO_ESCREVE_nada(self):
        """`04` §8.1 (a) e R7 §3 — `evidence verify` e da classe que so le."""
        antes = {p: p.stat().st_mtime_ns for p in sorted(self.tmp.rglob("*"))}
        self._conferir()
        depois = {p: p.stat().st_mtime_ns for p in sorted(self.tmp.rglob("*"))}
        self.assertEqual(antes, depois)


class OPrecursorEProjecao(ABase):
    """Item 3 — `precursor_events.jsonl` gerado, nunca autoral."""

    def test_o_arquivo_tem_o_nome_QUE_A_SPEC_USA(self):
        """`08` §2 e `06` T13 o chamam de `precursor_events.jsonl`, e nao de
        `precursor.jsonl`. Derivar o nome produziria um arquivo que o criterio
        de aceitacao nao encontra."""
        self.assertTrue(self._arquivo("precursor_events.jsonl").exists())

    def test_e_JSONL_valido(self):
        conteudo = self._arquivo("precursor_events.jsonl").read_text(encoding="utf-8")
        for linha in conteudo.splitlines():
            if linha.strip():
                json.loads(linha)

    def test_e_REPRODUZIVEL_a_partir_do_ground_truth(self):
        outro = Path(tempfile.mkdtemp(prefix="aurora-precursor-"))
        self.addCleanup(shutil.rmtree, outro, ignore_errors=True)
        build.construir(
            self.gt, destino=outro, pack_id=PACK, random_seed=SEED, **_contexto()
        )
        self.assertEqual(
            self._arquivo("precursor_events.jsonl").read_bytes(),
            (outro / "precursor_events.jsonl").read_bytes(),
        )

    def test_edicao_manual_do_precursor_e_detectada(self):
        alvo = self._arquivo("precursor_events.jsonl")
        alvo.write_text('{"forjado": true}\n', encoding="utf-8", newline="\n")
        achados = self._conferir()
        self.assertTrue(any("precursor_events.jsonl" in a for a in achados), achados)

    def test_o_precursor_NAO_atribui_ator(self):
        """Sinal fraco e o que faz dele precursor. Atribuicao e justamente o que
        o time azul tem de construir correlacionando as outras fontes — entrega-la
        aqui apagaria o exercicio, e `08` §2 poe a dificuldade em
        `discoverability`, que e do gabarito."""
        conteudo = self._arquivo("precursor_events.jsonl").read_text(encoding="utf-8")
        for linha in conteudo.splitlines():
            if linha.strip() and not linha.startswith("{\"_banner"):
                self.assertNotIn("actor", json.loads(linha))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
