"""Item 2 da DoD — `RANDOM_SEED` lido por código do `range-core`.

O QUE O ITEM PEDE, E O QUE ESTA SUITE AFIRMA
---------------------------------------------
*"lido de `.env` **por código do `range-core`**, não por atestação."* Então o que
precisa ficar provado é o **caminho de leitura**, nas duas fontes possíveis, e a
recusa quando não há seed nenhum.

NENHUM TESTE TOCA O `.env` DE VERDADE
-------------------------------------
`CLAUDE.md` nega leitura de `.env`, e o arquivo pode simplesmente não existir na
máquina que roda a suíte. Os testes escrevem um arquivo **no formato** `.env` em
diretório temporário. Um teste que dependesse do `.env` real seria intermitente
por construção — passaria na máquina de quem o escreveu.

O AMBIENTE DO PROCESSO NÃO É MUTADO
-----------------------------------
`random_seed` recebe o mapeamento por parâmetro, com `os.environ` como default.
Isso é o que permite afirmar a leitura sem `os.environ[...] = ...` numa suíte que
roda junto de outras — mutar o ambiente do processo é efeito que sobrevive ao
teste que o causou.

OS ESCOPOS SÃO `caminho/assim`, E NÃO `adapter.assim`
------------------------------------------------------
A primeira versão desta suíte usava `academus.alunos` como escopo, e o hook de
arquitetura a recusou como literal de flag. **Estava certo, e não como falso
positivo:** `<adapter>.<nome>` é a forma de flag que `01` §5.1 normatiza, e
`tools/check_contract_literals.py` recusa literal com essa forma que não esteja
declarado — justamente porque é a assinatura de um erro de digitação de flag.

Um escopo de seed que se parece com flag é ambiguidade de desenho, não
inconveniência de ferramenta. A forma passou a ser `dataset/alunos`, que nenhuma
das duas leituras confunde.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from range_core.determinism import (
    RANDOM_SEED,
    SeedUnavailable,
    derive_seed,
    parse_dotenv,
    random_seed,
    read_dotenv,
    seeded_random,
)

#: Formato de `.env`, com as formas que o parser aceita e as que ele ignora. É o
#: subconjunto de `.env.example`, e não `dotenv` completo.
DOTENV = """
# comentário, ignorado
RANDOM_SEED=424242

POSTGRES_USER=aurora
AURORA_JWT_SECRET="com aspas"
linha sem igual
"""


class LeituraDoSeed(unittest.TestCase):
    def test_le_do_ambiente(self):
        self.assertEqual(random_seed({RANDOM_SEED: "424242"}), 424242)

    def test_le_do_arquivo_no_formato_dotenv(self):
        with tempfile.TemporaryDirectory() as temporario:
            caminho = Path(temporario) / ".env"
            caminho.write_text(DOTENV, encoding="utf-8")
            self.assertEqual(random_seed({}, dotenv_path=caminho), 424242)

    def test_o_ambiente_vence_o_arquivo(self):
        """Em container as variáveis chegam pelo ambiente; `.env` é local."""
        with tempfile.TemporaryDirectory() as temporario:
            caminho = Path(temporario) / ".env"
            caminho.write_text(DOTENV, encoding="utf-8")
            self.assertEqual(random_seed({RANDOM_SEED: "7"}, dotenv_path=caminho), 7)

    def test_sem_seed_recusa_e_nao_inventa_valor(self):
        """Seed inventado reproduz a si mesmo, e `05` §8 deriva senha dele."""
        with self.assertRaises(SeedUnavailable) as capturado:
            random_seed({})
        self.assertIn(RANDOM_SEED, str(capturado.exception))

    def test_arquivo_ausente_nao_e_seed_ausente_silencioso(self):
        with tempfile.TemporaryDirectory() as temporario:
            with self.assertRaises(SeedUnavailable) as capturado:
                random_seed({}, dotenv_path=Path(temporario) / "nao-existe")
        self.assertIn("nao-existe", str(capturado.exception))

    def test_valor_nao_inteiro_recusa(self):
        """`random.Random` aceitaria a string e produziria outro fluxo."""
        with self.assertRaises(SeedUnavailable):
            random_seed({RANDOM_SEED: "quarenta e dois"})

    def test_valor_vazio_recusa(self):
        with self.assertRaises(SeedUnavailable):
            random_seed({RANDOM_SEED: "  "})


class ParserDeDotenv(unittest.TestCase):
    def test_o_subconjunto_que_o_projeto_escreve(self):
        valores = parse_dotenv(DOTENV)
        self.assertEqual(valores[RANDOM_SEED], "424242")
        self.assertEqual(valores["AURORA_JWT_SECRET"], "com aspas")
        self.assertNotIn("linha sem igual", valores)
        self.assertNotIn("# comentário, ignorado", valores)

    def test_arquivo_ausente_devolve_vazio_em_vez_de_estourar(self):
        with tempfile.TemporaryDirectory() as temporario:
            self.assertEqual(read_dotenv(Path(temporario) / "nada"), {})

    def test_nao_faz_interpolacao_e_o_limite_esta_afirmado(self):
        """O limite é declarado no módulo; aqui ele fica VERIFICADO.

        Se alguém esticar o parser para interpolar, este teste fica vermelho — e
        a decisão registrada é outra: `python-dotenv` pinado, não parser maior.
        """
        self.assertEqual(parse_dotenv("A=1\nB=${A}\n")["B"], "${A}")


class FluxosDerivados(unittest.TestCase):
    """`08` §1: mesmo seed é necessário e não suficiente."""

    def test_escopos_distintos_nao_compartilham_fluxo(self):
        a = seeded_random("dataset/alunos", seed=424242)
        b = seeded_random("evidence/vpn", seed=424242)
        self.assertNotEqual(
            [a.random() for _ in range(5)], [b.random() for _ in range(5)]
        )

    def test_o_mesmo_escopo_reproduz_a_mesma_sequencia(self):
        primeira = [seeded_random("dataset/alunos", seed=424242).random() for _ in range(1)]
        segunda = [seeded_random("dataset/alunos", seed=424242).random() for _ in range(1)]
        self.assertEqual(primeira, segunda)

    def test_um_gerador_novo_nao_desloca_os_outros(self):
        """A propriedade que o fluxo único NÃO tem, e a razão de derivar.

        Com um `random.Random` compartilhado, acrescentar um consumidor no meio
        muda tudo o que vem depois dele — e `06` T8 falharia na Fase 5 por um
        defeito plantado em outro lugar, meses antes.
        """
        antes = [seeded_random("dataset/notas", seed=424242).random() for _ in range(3)]
        _intruso = [seeded_random("dataset/turmas", seed=424242).random() for _ in range(50)]
        depois = [seeded_random("dataset/notas", seed=424242).random() for _ in range(3)]
        self.assertEqual(antes, depois)

    def test_a_derivacao_e_estavel_entre_processos(self):
        """Valor **anotado**, e não recalculado — `hash()` de string muda a cada
        processo, e é exatamente isso que este teste existe para pegar.

        O número foi registrado de uma execução e vale como âncora. Recalculá-lo
        aqui pela mesma fórmula compararia a implementação com uma cópia dela
        mesma, e passaria mesmo se as duas mudassem juntas. Se a derivação
        trocar de algoritmo, este teste fica vermelho — que é o aviso de que todo
        dataset gerado antes deixou de ser reproduzível.
        """
        self.assertEqual(derive_seed(424242, "dataset/alunos"), 4782405114317613158)


if __name__ == "__main__":
    unittest.main()
