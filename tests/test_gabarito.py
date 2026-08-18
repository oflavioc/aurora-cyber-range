"""`06` T8 — o gabarito, provado sobre artefato que o CI PRODUZ.

A FORMA DA PROVA, e por que ela nao e atestacao — a D10.3
-----------------------------------------------------------
`scenarios/` fica fora do Git, entao o `GM_NOTES.md` e o `ground_truth.yaml` do
exercicio nao existem no repositorio. *"Existe na minha maquina"* seria
atestacao, e o item 6 da DoD nao pode ser provado assim.

**O CI nao confere o artefato: ele o PRODUZ e o julga.** Versionado esta o
gerador, a query de referencia e o template de prosa; o artefato nasce aqui, de
um seed de teste, e e sobre ele que os criterios rodam.

O QUE ISTO NAO PROVA, e o limite e o mesmo do cabecalho do verificador: o
artefato gerado com o `RANDOM_SEED` de **producao** — o que vai para a sala —
nunca e visto por CI nenhum. Nao precisa ser: a propriedade provada e do
GERADOR, e ela independe do valor do seed.

O PAR QUE FECHA "O SEED DE TESTE E QUE FAZ DAR CERTO"
------------------------------------------------------
Duas execucoes com seeds DIFERENTES: os seis volumes tem de sair iguais, e os
`case_id` **distintos**. Isso separa propriedade do gerador de coincidencia de um
seed — e e o mesmo par que discrimina do teste de determinismo, aplicado ao
gabarito.

E ELE DESCOBRE O QUE E ESCRITO A MAO, em vez de confiar na declaracao: o que
sobrevive aos dois seeds com forma de identificador esta, por construcao, no
template. `test_nenhum_identificador_sobrevive_aos_dois_seeds` e essa descoberta.
"""

from __future__ import annotations

import unittest

import yaml
from sqlalchemy import text

from domains.academus.seed import carga, dataset, gabarito, linha_b

from _academus_banco import TABELAS, engine, exige_banco

SEED = 20260818
OUTRO_SEED = 424242
PACK = "linha-b-academus"


def _semeado(seed: int):
    """Devolve `(motor, conta_alvo)`. A conta e GABARITO e sai do seed."""
    motor = engine()
    with motor.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY"))
    dados = dataset.gerar(dataset.ESCALA_REDUZIDA, seed=seed)
    carga.carregar(motor, dados)
    return motor, dados.conta_alvo


@exige_banco
class OArtefatoEhProduzidoEJulgado(unittest.TestCase):
    """Item 6 da DoD e T8 — sobre o artefato que este teste acabou de gerar."""

    @classmethod
    def setUpClass(cls) -> None:
        motor, conta_alvo = _semeado(SEED)
        cls.gabarito = gabarito.gerar(
            motor, pack=PACK, seed=SEED, conta_alvo=conta_alvo
        )
        cls.motor = motor
        cls.conta_alvo = conta_alvo

    def test_o_GM_NOTES_contem_a_query_de_referencia(self) -> None:
        """Item 6 da DoD, primeira metade: o texto esta la."""
        self.assertIn(linha_b.INDEVIDOS.strip(), self.gabarito.gm_notes)
        self.assertIn(linha_b.AMBIGUOS.strip(), self.gabarito.gm_notes)

    def test_a_query_do_GM_NOTES_EXECUTADA_devolve_os_22_e_nenhum_ambiguo(self) -> None:
        """Item 6, segunda metade — e e ela que separa prova de interpolacao.

        Conter o texto sem executa-lo provaria que alguem colou uma string. O que
        `02` §6.3 chama de "a query que SEPARA indevidos de ambiguos" so e
        verdade se, rodando, ela devolver um conjunto e nao o outro.
        """
        with self.motor.begin() as conexao:
            indevidos = {
                l[0] for l in conexao.execute(text(linha_b.INDEVIDOS), linha_b.parametros(self.conta_alvo))
            }
            ambiguos = {
                l[0] for l in conexao.execute(text(linha_b.AMBIGUOS), linha_b.parametros(self.conta_alvo))
            }
        self.assertEqual(dataset.INDEVIDOS, len(indevidos))
        self.assertEqual(set(), indevidos & ambiguos)

    def test_todo_fato_citado_no_GM_NOTES_existe_no_ground_truth(self) -> None:
        """T8, quarto criterio — o linter que `02` §6.3 exige.

        A extracao e por FORMA do identificador, e nao por posicao: o facilitador
        pode citar um caso em qualquer frase, e um linter que so olhasse a tabela
        deixaria passar a citacao solta.
        """
        citados = gabarito.fatos_citados(self.gabarito.gm_notes)
        declarados = {c["case_id"] for c in self.gabarito.ground_truth["line_b_cases"]}
        declarados |= {f["fact_id"] for f in self.gabarito.ground_truth["facts"]}
        orfaos = citados - declarados
        self.assertEqual(
            set(),
            orfaos,
            f"o `GM_NOTES` cita {sorted(orfaos)[:5]} e o `ground_truth` nao os tem. "
            "`02` §6.3: nao pode conter fato ausente do ground truth",
        )
        # E O PAR: a citacao nao pode ser vazia, senao o linter passa por vacuidade.
        self.assertGreaterEqual(len(citados), dataset.INDEVIDOS)

    def test_o_ground_truth_gerado_valida_contra_o_contrato(self) -> None:
        """Artefato que o proprio contrato do projeto recusaria nao e artefato."""
        import json
        from pathlib import Path

        import jsonschema

        esquema = yaml.safe_load(
            Path("contracts/ground_truth.schema.yaml").read_text(encoding="utf-8")
        )
        jsonschema.validate(
            json.loads(json.dumps(self.gabarito.ground_truth, default=str)), esquema
        )

    def test_a_defensibilidade_e_a_de_02_secao_6_2(self) -> None:
        por_conjunto = {}
        for caso in self.gabarito.ground_truth["line_b_cases"]:
            por_conjunto.setdefault(caso["set"], set()).add(caso["defensibility"])
        self.assertEqual({"indevido_comprovado": {1.0}, "ambiguo": {0.5},
                          "legitimo_aparencia_suspeita": {0.0}}, por_conjunto)


@exige_banco
class DoisSeedsDiferentes(unittest.TestCase):
    """O par que fecha "o seed de teste e que faz dar certo"."""

    @classmethod
    def setUpClass(cls) -> None:
        motor, conta = _semeado(SEED)
        cls.primeiro = gabarito.gerar(motor, pack=PACK, seed=SEED, conta_alvo=conta)
        motor, conta = _semeado(OUTRO_SEED)
        cls.segundo = gabarito.gerar(
            motor, pack=PACK, seed=OUTRO_SEED, conta_alvo=conta
        )

    def _volumes(self, notas: str) -> list[str]:
        import re

        return re.findall(r"\| ([0-9]+) \|", notas)

    def test_os_seis_volumes_sao_os_mesmos_nos_dois(self) -> None:
        self.assertEqual(
            self._volumes(self.primeiro.gm_notes),
            self._volumes(self.segundo.gm_notes),
        )
        # E OS VOLUMES SAO OS DE `02` §6.1, e nao apenas iguais entre si.
        self.assertEqual(
            [
                str(dataset.INDEVIDOS), str(dataset.AMBIGUOS), str(dataset.SUSPEITOS),
                str(dataset.RUIDO), str(dataset.DELEGADAS),
                str(dataset.ESCALA_REDUZIDA.normais_na_trilha),
            ],
            self._volumes(self.primeiro.gm_notes),
        )

    def test_os_fatos_sao_DISTINTOS_entre_os_dois_seeds(self) -> None:
        """`case_id` pode coincidir — ele e ordinal. O FATO nao pode.

        `GC-0001` e o primeiro caso de qualquer execucao; o que identifica o caso
        de verdade e o `fact_id`, que sai da linha da trilha. Exigir `case_id`
        distinto seria exigir que o gerador numerasse por seed, o que nao torna
        nada mais seguro — e o que precisa diferir e o CONTEUDO.
        """
        atores_1 = {f["actor"] for f in self.primeiro.ground_truth["facts"]}
        atores_2 = {f["actor"] for f in self.segundo.ground_truth["facts"]}
        alvos_1 = {f["dest"] for f in self.primeiro.ground_truth["facts"]}
        alvos_2 = {f["dest"] for f in self.segundo.ground_truth["facts"]}
        self.assertNotEqual(
            (atores_1, alvos_1),
            (atores_2, alvos_2),
            "os dois seeds produziram o mesmo gabarito: o gerador esta ignorando "
            "o `RANDOM_SEED`, e a prova passaria por vacuidade",
        )

    def test_nenhum_identificador_QUE_APONTA_PARA_LINHA_sobrevive(self) -> None:
        """DESCOBRE o que e escrito a mao, em vez de confiar na declaracao.

        O que sobrevive aos dois seeds com forma de identificador esta, por
        construcao, no TEMPLATE — e template e versionado. Este teste e a metade
        dinamica da guarda que `check_gabarito_fora_do_git.py` faz estatica: la se
        procura a forma no arquivo, aqui se procura o que os dois artefatos tem em
        comum.

        O `case_id` E EXCLUIDO, e a exclusao custou uma volta. A primeira versao
        deste teste reprovou contra `GC-0001..GC-0067`, e a reprovacao estava
        errada: `GC-000n` e ROTULO ORDINAL — o n-esimo caso de qualquer execucao —,
        e por si so nao diz linha nenhuma. Ele nasce no gerador, e nao no
        template, entao a premissa "sobreviveu aos dois logo veio do template" nao
        vale para ele.

        O QUE CARREGA GABARITO E O MAPEAMENTO, e a segunda metade deste teste o
        exige diferente: `GC-0001 -> GT-LINHAB-<n>` e o que diz QUAL linha e o
        primeiro caso, e isso tem de mudar com o seed.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from check_gabarito_fora_do_git import IDENTIFICADORES

        def aponta_para_linha(texto: str) -> set[str]:
            return {
                i for i in IDENTIFICADORES.findall(texto) if not i.startswith("GC-")
            }

        comuns = aponta_para_linha(self.primeiro.gm_notes) & aponta_para_linha(
            self.segundo.gm_notes
        )
        self.assertEqual(
            set(),
            comuns,
            f"{sorted(comuns)[:5]} aparecem nos DOIS artefatos: identificador que "
            "nao muda com o seed veio do template versionado, e template e "
            "publico — e gabarito vazando pela metade escrita a mao",
        )

    def test_o_MAPEAMENTO_caso_para_fato_muda_com_o_seed(self) -> None:
        """A metade que o `case_id` ordinal nao cobre.

        `GC-0001` existe nos dois; o que ele APONTA nao pode ser o mesmo. Sem
        isto, um gerador que numerasse casos sobre linhas fixas passaria no teste
        acima — e o gabarito seria o mesmo com qualquer seed.

        E FOI ELE QUE ACHOU O TERCEIRO VAZAMENTO: o mapeamento era identico entre
        seeds porque o `fact_id` deriva da POSICAO na trilha, e os conjuntos eram
        gravados em bloco — as 22 primeiras linhas eram sempre os indevidos. Quem
        lesse o repositorio publico leria o gabarito na propria trilha, que e o
        artefato que o participante investiga. O gerador passou a EMBARALHAR a
        ordem, com o fluxo semeado.

        A comparacao e sobre o CONTEUDO do fato — ator e aluno —, e nao sobre o
        `fact_id`: identificador ordinal comparado com identificador ordinal
        acusaria "mudou" so porque a posicao mudou.
        """
        def mapa(g) -> dict:
            fatos = {f["fact_id"]: (f["actor"], f["dest"]) for f in g.ground_truth["facts"]}
            return {
                c["case_id"]: fatos[c["supporting_evidence"][0]]
                for c in g.ground_truth["line_b_cases"]
            }

        self.assertNotEqual(mapa(self.primeiro), mapa(self.segundo))


if __name__ == "__main__":
    unittest.main()
