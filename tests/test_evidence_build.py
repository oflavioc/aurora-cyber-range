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
        "campos_do_fato": contract_source.campos_do_fato(CONTRATOS),
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

    def test_a_edicao_simples_e_reportada_PELO_HASH(self):
        """`06` T13 nomeia o mecanismo: *"edicao manual e detectada **por hash**
        no `MANIFEST.json`"*.

        E a distincao importa para quem le o achado. Ha DUAS conferencias
        empilhadas — o `sha256` do manifesto e a reprojecao — e elas respondem
        perguntas diferentes: o hash diz *"o arquivo nao e o que foi escrito"*, e
        a reprojecao diz *"o arquivo nao e o que o gabarito projeta"*. Sem este
        caso, remover a comparacao de hash deixaria a reprojecao pegar a edicao
        e reporta-la com a mensagem ERRADA — medido pela prova negativa.
        """
        alvo = self._arquivo("vpn.log")
        alvo.write_text("editado", encoding="utf-8", newline="")
        achados = self._conferir()
        do_arquivo = [a for a in achados if "vpn.log" in a]
        self.assertTrue(do_arquivo, achados)
        self.assertIn("sha256", do_arquivo[0])

    def test_manifesto_E_arquivo_alterados_JUNTOS_sao_distinguidos(self):
        """A defesa em profundidade sendo verificada — e o caso que mostra que a
        reprojecao nao e redundante com o hash.

        Quem edita o arquivo E atualiza o `sha256` do manifesto passa pela
        primeira conferencia. So a reprojecao o pega, porque ela nao pergunta
        *"bate com o que foi escrito?"* e sim *"bate com o que o gabarito
        projeta?"* — e a mensagem diz isso, em vez de acusar edicao manual.
        """
        import hashlib

        alvo = self._arquivo("vpn.log")
        forjado = "conluio"
        alvo.write_text(forjado, encoding="utf-8", newline="")
        manifesto = json.loads(self._arquivo(build.MANIFESTO).read_text(encoding="utf-8"))
        for source in manifesto["sources"]:
            if source["file"] == "vpn.log":
                source["sha256"] = hashlib.sha256(forjado.encode("utf-8")).hexdigest()
        self._arquivo(build.MANIFESTO).write_text(
            json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="",
        )
        achados = [a for a in self._conferir() if "vpn.log" in a]
        self.assertTrue(achados)
        self.assertIn("juntos", achados[0])

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

    def test_o_BUILD_declara_a_cobertura_por_fato(self):
        """`06` T13: *"para cada `fact_id`, todas as projecoes declaradas
        existem"*, do lado do PRODUTOR.

        Este caso julga `self.manifesto`, que e a saida do `construir` — e por
        isso ele nao substitui o de baixo. Foi exatamente a confusao que o H2 da
        segunda auditoria nomeou: ele se chamava
        `test_a_conferencia_e_DIRIGIDA_POR_FATO` e **nunca chamava `conferir`**.
        """
        declarados = {
            f for s in self.manifesto["sources"] for f in s["projects_facts"]
        }
        com_projecao = {
            f["fact_id"] for f in linha_a.facts(SEED) if f.get("projections")
        }
        self.assertEqual(declarados, com_projecao)

    def _adultera_o_manifesto(self, muda):
        """Reescreve o `MANIFEST.json` com `muda` aplicada a cada `source`.

        **Sem tocar em arquivo nenhum de evidencia** — e esse o ponto: o
        `sha256`, o `ground_truth_hash` e a reprojecao continuam todos batendo.
        O que muda e so a amarracao por fato, que e o que o manifesto existe
        para carregar.
        """
        import json

        caminho = self._arquivo(build.MANIFESTO)
        documento = json.loads(caminho.read_text(encoding="utf-8"))
        for source in documento["sources"]:
            muda(source)
        caminho.write_text(
            json.dumps(documento, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="",
        )

    def test_a_CONFERENCIA_pega_projects_facts_adulterado(self):
        """**H2 da segunda auditoria, o defeito verbatim.**

        `conferir` comparava so os NOMES DE ARQUIVO. `projects_facts` era
        escrito no build, validado pelo schema quanto a FORMA, e nunca mais
        lido: um manifesto com a cobertura por fato trocada e os arquivos
        intactos passava por todos os degraus — schema, `ground_truth_hash`,
        conjunto de arquivos, `sha256` e reprojecao.

        E e justamente a amarracao que nao tem outro guardiao: o `fact_id` NAO
        esta nas fontes (`05` §6 — ele entregaria o gabarito na primeira linha),
        entao o manifesto e o unico lugar onde ele aparece.
        """
        self._adultera_o_manifesto(lambda s: s.__setitem__("projects_facts", ["GT-A-999"]))
        achados = self._conferir()
        self.assertTrue(any("GT-A-999" in a for a in achados), achados)

    def test_a_CONFERENCIA_pega_format_adulterado(self):
        """A outra metade do mesmo degrau. Um manifesto que mente sobre o
        formato manda o facilitador abrir o arquivo com o parser errado, e o
        registro que liga fonte a formato e `x-aurora-registry.source_formats`
        — nao o que estiver escrito no manifesto."""
        self._adultera_o_manifesto(lambda s: s.__setitem__("format", "jsonl"))
        achados = self._conferir()
        self.assertTrue(any("formato" in a for a in achados), achados)

    def test_o_par_positivo_manifesto_INTACTO_nao_gera_achado(self):
        """Sem ele, um `conferir` que reclamasse de tudo passaria nos dois
        casos acima."""
        self.assertEqual(self._conferir(), [])

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


class OsVerbosDoCLI(unittest.TestCase):
    """`range-cli evidence build` e `evidence verify` — `04` §8."""

    def setUp(self):
        import yaml

        self.tmp = Path(tempfile.mkdtemp(prefix="aurora-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.pack = self.tmp / PACK
        self.pack.mkdir(parents=True)
        (self.pack / "ground_truth.yaml").write_text(
            yaml.safe_dump({"facts": linha_a.facts(SEED)}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
            newline="",
        )

    def _cli(self, *argv):
        """Roda o CLI com a saida capturada, e devolve `(rc, stdout, stderr)`."""
        import contextlib
        import io

        from range_cli.cli import main

        saida, erro = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            rc = main(list(argv))
        return rc, saida.getvalue(), erro.getvalue()

    def test_build_escreve_e_sai_limpo(self):
        rc, saida, _ = self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        self.assertEqual(rc, 0, saida)
        self.assertTrue((self.pack / "evidence" / "MANIFEST.json").exists())

    def test_verify_de_pacote_integro_sai_limpo(self):
        self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        rc, saida, _ = self._cli("evidence", "verify", str(self.pack))
        self.assertEqual(rc, 0, saida)

    # -- M3 da segunda auditoria: o modo de entrega ---------------------------

    def _com_injects(self, *liberadas):
        import yaml

        (self.pack / "injects.yaml").write_text(
            yaml.safe_dump(
                {
                    "injects": [
                        {
                            "id": "A07",
                            "evidence_release": [
                                {"source": f, "window": "T-9d → T-8d"}
                                for f in liberadas
                            ],
                        }
                    ]
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
            newline="",
        )

    def _modos(self):
        return {
            s["file"]: s["delivery_mode"]
            for s in json.loads(
                (self.pack / "evidence" / build.MANIFESTO).read_text(encoding="utf-8")
            )["sources"]
        }

    def test_fonte_liberada_por_inject_NAO_sai_pre_posicionada(self):
        """**M3 da segunda auditoria.** `montar` sempre soube receber `entrega`,
        e o CLI nunca a passava: todo manifesto saia `pre_positioned`, inclusive
        o de um pack cujos injects liberam fonte no meio do exercicio.

        O manifesto e o que o facilitador le para saber o que existe e desde
        quando (`08` §7). Dizer `pre_positioned` para uma fonte de
        `evidence_release` afirma disponibilidade desde o start — e e falso.
        """
        self._com_injects("vpn")
        rc, _, erro = self._cli(
            "evidence", "build", str(self.pack), "--seed", str(SEED)
        )
        self.assertEqual(rc, 0, erro)
        modos = self._modos()
        self.assertEqual(modos["vpn.log"], "released_by_inject")

    def test_a_fonte_NAO_liberada_continua_pre_posicionada(self):
        """O par negativo, e ele e o que impede a correcao de virar o oposto do
        defeito: sem ele, um CLI que marcasse TUDO como liberado passaria no
        caso acima."""
        self._com_injects("vpn")
        self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        modos = self._modos()
        self.assertTrue(len(modos) > 1, modos)
        for arquivo, modo in modos.items():
            if arquivo != "vpn.log":
                self.assertEqual(modo, "pre_positioned", arquivo)

    def test_pack_SEM_injects_continua_tudo_pre_posicionado(self):
        """`08` §5 — pre-posicionado e o unico modo que nao depende de decisao
        de cenario, e por isso e o default. Pack sem `injects.yaml` nao e erro:
        e o caso do pacote projetado fora de exercicio."""
        self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        self.assertEqual(set(self._modos().values()), {"pre_positioned"})

    def test_inject_que_libera_fonte_QUE_O_GABARITO_NAO_PROJETA_e_recusado(self):
        """A promessa que so falha na sala.

        `evidence_release` e escrito no roteiro de facilitacao e `projections`
        no gabarito — autores e momentos diferentes. Um inject que libera uma
        fonte sem fato promete ao participante um arquivo que nao existe.
        """
        self._com_injects("database_audit", "firewall")
        rc, _, erro = self._cli(
            "evidence", "build", str(self.pack), "--seed", str(SEED)
        )
        self.assertEqual(rc, 2)
        self.assertIn("firewall", erro)

    def test_verify_de_pacote_ADULTERADO_recusa(self):
        """O codigo de saida e `2`, o mesmo de `lint` e `materialize`: `04` §8
        poe esses verbos no CI, e um sinalizando recusa com `1` e outro com `2`
        faria o job depender de qual deles falhou."""
        self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        alvo = self.pack / "evidence" / "vpn.log"
        alvo.write_text("adulterado", encoding="utf-8", newline="")
        rc, _, erro = self._cli("evidence", "verify", str(self.pack))
        self.assertEqual(rc, 2)
        self.assertIn("vpn.log", erro)

    def test_verify_NAO_escreve_no_pacote(self):
        """`04` §8.1 (a) — `evidence verify` e da classe que so le, e as
        allowlists de quem opera o repositorio dependem disso."""
        self._cli("evidence", "build", str(self.pack), "--seed", str(SEED))
        antes = {
            p: (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(self.pack.rglob("*"))
        }
        self._cli("evidence", "verify", str(self.pack))
        depois = {
            p: (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(self.pack.rglob("*"))
        }
        self.assertEqual(antes, depois)

    def test_build_sem_ground_truth_recusa_dizendo_o_que_falta(self):
        """Falha fechada com instrucao: a evidencia e projecao do gabarito
        (`00` §5.3), entao sem ele nao ha o que projetar."""
        (self.pack / "ground_truth.yaml").unlink()
        rc, _, erro = self._cli(
            "evidence", "build", str(self.pack), "--seed", str(SEED)
        )
        self.assertEqual(rc, 2)
        self.assertIn("materialize", erro)

    def test_build_recusa_quando_o_motor_recusa(self):
        """A recusa do motor chega INTEIRA ao operador, com o nome da excecao —
        `GeradorAusente`, `EntidadeInventada`, `IOCEncontrado` nomeiam normas
        diferentes, e uma mensagem generica mandaria procurar."""
        import yaml

        forjado = {
            "facts": [
                {
                    "fact_id": "GT-A-777",
                    "fact_class": "x",
                    "exercise_time": "T+0",
                    "projections": ["firewall"],
                }
            ]
        }
        (self.pack / "ground_truth.yaml").write_text(
            yaml.safe_dump(forjado, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
            newline="",
        )
        rc, _, erro = self._cli(
            "evidence", "build", str(self.pack), "--seed", str(SEED)
        )
        self.assertEqual(rc, 2)
        self.assertIn("firewall", erro)


class OEvidenceVersionadoSobreviveAoCheckout(unittest.TestCase):
    """**M1 da segunda auditoria** — o pacote versionado e o seu fim de linha.

    `tests/fixtures/pack_exemplo/evidence/` nasceu versionado nesta fase para
    dar objeto ao `evidence verify` no CI. O `MANIFEST.json` declara o `sha256`
    do conteudo **em bytes**, como o gerador o escreveu: UTF-8 com LF.

    Num checkout com `core.autocrlf=true` — o da maquina do operador, e o do
    worktree que a auditoria cria — sem atributo os arquivos chegam com CRLF, e
    o `evidence verify` sai com rc=2 dizendo *"edicao manual, ou build de outro
    gabarito"*. **Acusa uma edicao que nao houve**, e manda procurar pelo lado
    errado. O CI, em Linux, passava.

    E a R2 §2 do outro lado: la a licao era medir identidade sobre blob de HEAD;
    aqui nao ha blob a que recorrer, porque em pack real (`scenarios/`, fora do
    Git desde a Fase 5) nao existe blob nenhum e o verificador le o disco. A
    disciplina tem de estar no checkout.
    """

    #: O diretorio VERSIONADO. Nao ha outro hoje, e o teste descobre os arquivos
    #: em vez de lista-los: arquivo novo entra na guarda sozinho.
    EVIDENCIA = Path(__file__).resolve().parent / "fixtures" / "pack_exemplo" / "evidence"

    def _arquivos(self):
        return sorted(p for p in self.EVIDENCIA.iterdir() if p.is_file())

    def test_ha_o_que_conferir(self):
        """Anti-vacuidade: diretorio vazio faria os dois casos abaixo passarem
        sem olhar nada — a mesma armadilha que o quinto eixo do verificador de
        banner fechou na primeira auditoria."""
        self.assertTrue(self._arquivos())

    def test_nenhum_arquivo_chegou_com_CARRIAGE_RETURN(self):
        """O sintoma, medido no disco. Este caso e VERDE no CI e vermelho na
        maquina onde o defeito existe — e por isso ele nao basta sozinho."""
        for caminho in self._arquivos():
            self.assertNotIn(
                b"\r", caminho.read_bytes(), f"{caminho.name} veio com CRLF"
            )

    def test_o_gitattributes_DECLARA_eol_lf_para_cada_um(self):
        """A causa, e ela e independente de plataforma — entao o CI a cobra.

        O caso acima so fica vermelho em quem ja sofreu o defeito; este fica
        vermelho em qualquer lugar onde a declaracao falte, que e o momento util.
        """
        import subprocess

        resultado = subprocess.run(
            ["git", "check-attr", "eol", "--", *[str(p) for p in self._arquivos()]],
            capture_output=True,
            text=True,
            cwd=str(self.EVIDENCIA.parent.parent.parent.parent),
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        linhas = [l for l in resultado.stdout.splitlines() if l.strip()]
        self.assertEqual(len(linhas), len(self._arquivos()))
        for linha in linhas:
            self.assertTrue(
                linha.endswith(": eol: lf"),
                f"sem `eol=lf` no .gitattributes: {linha}",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
