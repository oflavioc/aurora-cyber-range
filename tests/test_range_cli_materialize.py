"""`range-cli scenario materialize` — o produtor do pack, e o que ele recusa.

O QUE ESTA SUITE PROVA
=======================
A **P5-6** fechando: o par `ground_truth.yaml` + `GM_NOTES.md` deixa de existir
so em memoria e passa a ter produtor em disco.

E as tres propriedades que `04` §8.1 e §8.2 exigem de quem escreve gabarito:
forma dos segmentos, recusa de destino versionado, e parametros explicitos.

DUAS METADES, E A SEGUNDA EXIGE BANCO
--------------------------------------
As recusas — forma invalida, destino rastreado, dominio sem gerador — acontecem
**antes** de qualquer geracao, entao nao precisam de Postgres e rodam em toda
maquina. Sao elas que carregam as garantias de `05` §6.

O determinismo e a escrita de verdade precisam do dataset semeado, e por isso
pulam sem `AURORA_TEST_DATABASE_URL`. O `skip` diz como rodar, para que pulo
silencioso nao seja confundido com verde.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

from range_cli import cli  # noqa: E402
from range_core.engine import destino as destino_de_pack  # noqa: E402
from range_core.engine.loader import contract_source  # noqa: E402

from _academus_banco import TABELAS, engine, exige_banco  # noqa: E402

CONTRATOS = contract_source.read_contracts()
FORMA_DOMAIN, FORMA_PACK_ID = contract_source.formas_do_destino(CONTRATOS)

def _MOTOR_PROIBIDO():
    """A fabrica que NAO pode ser chamada — ela e a assercao de ORDEM.

    Todas as recusas acontecem antes da conexao. Se alguma delas passar a rodar
    depois, esta fabrica dispara e o teste diz exatamente isso, em vez de o
    defeito so aparecer quando alguem rodar o executavel sem banco no ar —
    que foi como ele apareceu da primeira vez.
    """
    raise AssertionError(
        "a conexao foi aberta ANTES da recusa: as guardas de `04` §8.1 tem de "
        "rodar sem banco, ou um `domain` fora de forma passa a exigir Postgres"
    )


SEED = 20260825
DOMINIO = "academus"
PACK = "linha-b-academus"


class AsRecusasVemANTESDeQualquerEscrita(unittest.TestCase):
    """Nenhuma delas precisa de banco — e e isso que as torna a garantia.

    Se elas dependessem da geracao, a recusa aconteceria DEPOIS de o gabarito
    existir em memoria, e a janela entre gerar e recusar seria onde o defeito
    mora. Elas rodam antes, e por isso rodam sem stack nenhuma.
    """

    def _materializa(self, domain: str, pack_id: str, raiz: Path):
        return cli.materialize(
            domain, pack_id, raiz=raiz, abre_motor=_MOTOR_PROIBIDO, seed=SEED, conta_alvo="x"
        )

    def test_domain_fora_de_forma_recusa(self) -> None:
        """`^[a-z][a-z0-9_]*$` — a forma vem do contrato, nao deste teste."""
        with self.assertRaises(destino_de_pack.DestinoInvalido) as capturado:
            self._materializa("Academus", PACK, Path("/tmp"))
        self.assertIn("domain", str(capturado.exception))

    def test_pack_id_fora_de_forma_recusa(self) -> None:
        with self.assertRaises(destino_de_pack.DestinoInvalido) as capturado:
            self._materializa(DOMINIO, "Linha_B", Path("/tmp"))
        self.assertIn("pack_id", str(capturado.exception))

    def test_travessia_de_diretorio_nao_e_expressavel(self) -> None:
        """A forma do contrato ja exclui separador e ponto.

        Sem esta perna, `..` como `domain` sairia de `scenarios/` por `Path` sem
        que nada acusasse — e o destino do gabarito e o lugar em que sair da
        arvore custa mais.
        """
        for veneno in ("..", "a/b", ".hidden"):
            with self.assertRaises(destino_de_pack.DestinoInvalido):
                self._materializa(veneno, PACK, Path("/tmp"))

    def test_destino_VERSIONADO_recusa(self) -> None:
        """`04` §8.1 (c) — a guarda de `05` §6, no caminho que escreve.

        NUM REPOSITORIO DESCARTAVEL, e a escolha e o que torna o teste honesto:
        neste repositorio `scenarios/` esta no `.gitignore`, entao NADA sob o
        destino e rastreado — um teste aqui provaria a ausencia de rastreamento
        e nao a guarda. O repo sintetico tem o destino de fato versionado, e e
        contra ele que a recusa significa alguma coisa.

        E ele prova, de quebra, que a pergunta e ao `git` e nao ao `.gitignore`:
        nao ha `.gitignore` nenhum no repo sintetico.
        """
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            alvo = raiz / "scenarios" / DOMINIO / PACK
            alvo.mkdir(parents=True)
            (alvo / "ja-existe.txt").write_text("rastreado", encoding="utf-8")
            for comando in (
                ["git", "init", "-q"],
                ["git", "add", "-A"],
            ):
                resultado = subprocess.run(comando, cwd=raiz, capture_output=True)
                self.assertEqual(resultado.returncode, 0, resultado.stderr)

            with self.assertRaises(destino_de_pack.DestinoInvalido) as capturado:
                cli.materialize(
                    DOMINIO, PACK, raiz=raiz, abre_motor=_MOTOR_PROIBIDO, seed=SEED, conta_alvo="x"
                )
        mensagem = str(capturado.exception)
        self.assertIn("VERSIONADO", mensagem)
        self.assertIn("05_SECURITY_REQUIREMENTS", mensagem)

    def test_destino_NAO_versionado_passa_da_guarda(self) -> None:
        """O positivo, sem o qual a recusa acima passaria por recusar tudo.

        Ele para no gerador — `motor=None` nao chega a ser usado porque o
        dominio sintetico nao tem gabarito —, e isso basta: o que se afirma e
        que a guarda de destino NAO disparou.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cli.ComandoRecusado):
                self._materializa("prontus", PACK, Path(tmp))

    def test_dominio_sem_gerador_recusa_nomeando_o_que_falta(self) -> None:
        """`prontus` e stub declarado: sem Linha B, sem gabarito a materializar."""
        with self.assertRaises(cli.ComandoRecusado) as capturado:
            self._materializa("prontus", PACK, Path("/tmp") / "fora-do-repo")
        self.assertIn("gerador de gabarito", str(capturado.exception))


class OsParametrosSaoEXPLICITOS(unittest.TestCase):
    """`04` §8.2 — nada e derivado de contexto."""

    def test_domain_e_pack_id_sao_posicionais_obrigatorios(self) -> None:
        """Opcao com default seria derivacao de contexto com outro nome."""
        with self.assertRaises(SystemExit):
            cli._parser().parse_args(["scenario", "materialize"])

    def test_seed_e_conta_alvo_sao_obrigatorios(self) -> None:
        with self.assertRaises(SystemExit):
            cli._parser().parse_args(["scenario", "materialize", DOMINIO, PACK])

    def test_o_comando_completo_parseia(self) -> None:
        args = cli._parser().parse_args(
            ["scenario", "materialize", DOMINIO, PACK, "--seed", "1", "--conta-alvo", "u"]
        )
        self.assertEqual((args.grupo, args.verbo), ("scenario", "materialize"))
        self.assertEqual((args.domain, args.pack_id), (DOMINIO, PACK))

    def test_main_RECUSA_sem_abrir_conexao_e_sem_DATABASE_URL(self) -> None:
        """A REPRODUCAO EXATA DO DEFEITO QUE A PRIMEIRA EXECUCAO ACHOU.

        `main` montava o motor ANTES de chamar `materialize`, entao um `domain`
        fora de forma estourava em `engine_do_ambiente` — que ate exigia um
        argumento que ninguem passava. Os testes de unidade nao viam: eles
        chamam `materialize` direto e pulam o `main`.

        Aqui o comando inteiro roda, sem `DATABASE_URL` no ambiente, e tem de
        sair `2` pela recusa de FORMA — nao por falta de banco.
        """
        import io
        import os
        from contextlib import redirect_stderr

        anterior = os.environ.pop("DATABASE_URL", None)
        if anterior is not None:
            self.addCleanup(os.environ.__setitem__, "DATABASE_URL", anterior)

        erro = io.StringIO()
        with redirect_stderr(erro):
            codigo = cli.main(
                ["scenario", "materialize", "Academus", PACK, "--seed", "1",
                 "--conta-alvo", "u"]
            )
        self.assertEqual(codigo, 2)
        self.assertIn("RECUSADO", erro.getvalue())
        self.assertIn("domain", erro.getvalue())
        # E a recusa NAO e sobre banco: se fosse, a ordem teria voltado a ser a
        # errada e este teste passaria pelo motivo errado.
        self.assertNotIn("DATABASE_URL", erro.getvalue())

    def test_os_outros_subcomandos_de_04_secao_8_NAO_existem(self) -> None:
        """Casca vazia seria superficie que PARECE existir.

        `migrate` nao tem entrega enquanto nao houver transicao real a migrar
        (ver `engine/migrations/__init__.py`); `evidence` e da Fase 9. Um verbo
        que saisse zero sem conferir nada seria pior que a ausencia dele — a
        ausencia grita.

        **`dryrun` SAIU DESTA LISTA na peca 4**, pelo mesmo movimento que tirou
        `lint` na peca 3 — a classe da §1.6 do registro da Fase 1: a lista se
        reescreve, nao ganha ressalva. O teste dele e
        `tests/test_range_cli_dryrun.py`, e a perna de presenca esta abaixo.

        `lint` **existe** desde a peca 3, e o teste dele e
        `tests/test_range_cli_lint.py`. `validate` **nao existe e nao vai
        existir como verbo separado nesta fase**: `04` §8 divide as checagens
        entre os dois, e `lint` roda a lista inteira de `_passos` — a de
        `validate` inclusive. Um `validate` seria um `lint` com menos checagens,
        e nenhum criterio de DoD o cobra.
        """
        for verbo in ("validate", "migrate"):
            with self.assertRaises(SystemExit):
                cli._parser().parse_args(["scenario", verbo, "x"])
        with self.assertRaises(SystemExit):
            cli._parser().parse_args(["evidence", "build", "x"])

    def test_dryrun_existe_e_recebe_o_caminho_do_pacote(self) -> None:
        """A perna de presenca do `dryrun` — mesma razao da de `lint` abaixo."""
        args = cli._parser().parse_args(["scenario", "dryrun", "algum/pacote"])
        self.assertEqual((args.grupo, args.verbo), ("scenario", "dryrun"))

    def test_lint_existe_e_recebe_o_caminho_do_pacote(self) -> None:
        """A outra metade: a lista acima so prova ausencia se `lint` estiver fora.

        Sem esta perna, remover `lint` do parser por engano deixaria a suite
        verde — o teste de ausencia passaria com mais um verbo, que e o mesmo
        defeito de discriminante que `PackSite` existe para nao ter.
        """
        args = cli._parser().parse_args(["scenario", "lint", "algum/pacote"])
        self.assertEqual((args.grupo, args.verbo), ("scenario", "lint"))
        self.assertEqual(args.path, "algum/pacote")
        # `--flags` e opcional: o default sai do `domain` do manifesto.
        self.assertIsNone(args.flags)


class OESCRITOR_E_DETERMINISTA(unittest.TestCase):
    """Mesmos insumos, mesmos BYTES — a metade do invariante que e DESTE modulo.

    A DECOMPOSICAO E DELIBERADA, e cada metade e provada por quem a possui:

        o GERADOR e determinista   `tests/test_gabarito.py::DoisSeedsDiferentes`
                                   — mesmo seed, mesmo conteudo; seeds
                                   diferentes, `case_id` distintos
        o ESCRITOR e determinista  aqui — mesmo `Gabarito`, mesmos bytes

    Provar so a ponta a ponta deixaria a segunda metade sem sujeito proprio: um
    escritor que carimbasse hora seria pego, mas a suite inteira passaria a
    exigir Postgres para provar uma propriedade de `yaml.safe_dump`. E sem
    Postgres — que e o caso de quem clona — o invariante ficaria sem prova
    nenhuma.

    O GERADOR E SUBSTITUIDO POR UM QUE DEVOLVE SEMPRE O MESMO: assim o unico
    lugar de onde variacao pode vir e a escrita, que e o que esta sob teste.
    """

    #: Um `Gabarito` FIXO. As chaves fora de ordem alfabetica sao de proposito:
    #: sem `sort_keys=True` na serializacao, a ordem de insercao vazaria para o
    #: arquivo, e dois dicionarios com a mesma informacao produziriam bytes
    #: diferentes conforme a ordem em que foram montados.
    GROUND_TRUTH_FIXO = {
        "verification_predicates": {
            "containment": {"absence_of": {"fact_class": "x", "since": "self"}},
            "service_restoration": {"not_applicable": "fora do escopo"},
        },
        "facts": [{"fact_id": "GT-T-001", "fact_class": "x", "exercise_time": "T+0"}],
        "line_b_cases": [],
    }
    GM_NOTES_FIXO = "# GM_NOTES de teste\n\nGT-T-001 — acentuação preservada.\n"

    def setUp(self) -> None:
        from types import SimpleNamespace

        gabarito = SimpleNamespace(
            ground_truth=self.GROUND_TRUTH_FIXO, gm_notes=self.GM_NOTES_FIXO
        )
        gerador = SimpleNamespace(gerar=lambda motor, **kwargs: gabarito)
        original = cli._gerador_do_dominio
        cli._gerador_do_dominio = lambda domain: gerador
        self.addCleanup(setattr, cli, "_gerador_do_dominio", original)

    def _bytes_de_uma_materializacao(self) -> dict[str, bytes]:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            alvo = cli.materialize(
                DOMINIO, PACK, raiz=Path(tmp), abre_motor=lambda: None,
                seed=SEED, conta_alvo="u"
            )
            return {
                nome: (alvo / nome).read_bytes()
                for nome in (cli.GROUND_TRUTH, cli.GM_NOTES)
            }

    def test_DUAS_materializacoes_produzem_os_MESMOS_BYTES(self) -> None:
        """Byte a byte, e nao "estrutura equivalente".

        E o arquivo que a P7-3 precisaria hashear, e hash nao compara estrutura.
        Timestamp, ordem de `dict` vazando para o YAML, uuid de execucao — cada
        um deles quebra este teste, que e o ponto dele.
        """
        primeiro = self._bytes_de_uma_materializacao()
        segundo = self._bytes_de_uma_materializacao()
        for nome in (cli.GROUND_TRUTH, cli.GM_NOTES):
            self.assertEqual(primeiro[nome], segundo[nome], f"{nome} nao e determinista")

    def test_a_ordem_das_chaves_NAO_depende_da_ordem_de_insercao(self) -> None:
        """A perna que pega a regressao mais provavel: perder `sort_keys`.

        Sem ela, o teste acima passaria mesmo sem `sort_keys` — os dois
        dicionarios seriam o MESMO objeto, montado uma vez. Aqui os dois trazem
        a mesma informacao em ordem de insercao trocada, e so uma serializacao
        ordenada os faz coincidir.
        """
        import yaml

        direto = yaml.safe_dump(
            self.GROUND_TRUTH_FIXO, sort_keys=True, allow_unicode=True,
            default_flow_style=False,
        )
        invertido = yaml.safe_dump(
            dict(reversed(list(self.GROUND_TRUTH_FIXO.items()))),
            sort_keys=True, allow_unicode=True, default_flow_style=False,
        )
        self.assertEqual(direto, invertido)
        self.assertEqual(
            direto.encode("utf-8"),
            self._bytes_de_uma_materializacao()[cli.GROUND_TRUTH],
        )

    def test_o_GM_NOTES_preserva_acentuacao_e_termina_em_LF(self) -> None:
        """`newline="\\n"` explicito: no Windows o default reescreveria para CRLF.

        Dois sistemas produzindo bytes diferentes para o mesmo gabarito e
        exatamente o nao-determinismo que este bloco existe para excluir — e ele
        nao apareceria em maquina nenhuma que rodasse a suite sozinha.
        """
        escrito = self._bytes_de_uma_materializacao()[cli.GM_NOTES]
        self.assertEqual(escrito, self.GM_NOTES_FIXO.encode("utf-8"))
        self.assertNotIn(b"\r\n", escrito)


@exige_banco
class OParESCRITO(unittest.TestCase):
    """A metade que precisa do dataset semeado."""

    @classmethod
    def setUpClass(cls) -> None:
        from sqlalchemy import text

        from domains.academus.seed import carga, dataset

        cls.motor = engine()
        with cls.motor.begin() as conexao:
            conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY"))
        dados = dataset.gerar(dataset.ESCALA_REDUZIDA, seed=SEED)
        carga.carregar(cls.motor, dados)
        cls.conta_alvo = dados.conta_alvo

    def _materializa_em(self, raiz: Path) -> Path:
        return cli.materialize(
            DOMINIO,
            PACK,
            raiz=raiz,
            abre_motor=lambda: self.motor,
            seed=SEED,
            conta_alvo=self.conta_alvo,
        )

    def test_os_dois_arquivos_nascem_no_caminho_de_00_secao_6(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            alvo = self._materializa_em(Path(tmp))
            self.assertEqual(alvo, Path(tmp) / "scenarios" / DOMINIO / PACK)
            self.assertTrue((alvo / cli.GROUND_TRUTH).is_file())
            self.assertTrue((alvo / cli.GM_NOTES).is_file())

    def test_o_ground_truth_ESCRITO_valida_contra_o_contrato(self) -> None:
        """Artefato que o proprio contrato recusaria nao e artefato.

        E a leitura do DISCO, e nao do valor em memoria: a serializacao pode
        perder o que a estrutura tinha, e e o arquivo que vai para a sala.
        """
        import json
        import tempfile

        import jsonschema
        import yaml

        with tempfile.TemporaryDirectory() as tmp:
            alvo = self._materializa_em(Path(tmp))
            escrito = yaml.safe_load((alvo / cli.GROUND_TRUTH).read_text("utf-8"))
        esquema = yaml.safe_load(
            (REPO_ROOT / "contracts" / "ground_truth.schema.yaml").read_text("utf-8")
        )
        jsonschema.validate(json.loads(json.dumps(escrito, default=str)), esquema)

    def test_DUAS_materializacoes_produzem_os_MESMOS_BYTES(self) -> None:
        """O INVARIANTE — mesmos insumos, mesmos bytes.

        Byte a byte, e nao "estrutura equivalente": e o arquivo que a P7-3
        precisaria hashear, e hash nao compara estrutura. Timestamp, ordem de
        `dict` que vaze para o YAML, uuid de execucao — qualquer um deles
        quebra este teste, que e o ponto dele.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            primeiro = self._materializa_em(Path(a))
            segundo = self._materializa_em(Path(b))
            for nome in (cli.GROUND_TRUTH, cli.GM_NOTES):
                self.assertEqual(
                    (primeiro / nome).read_bytes(),
                    (segundo / nome).read_bytes(),
                    f"{nome} nao e determinista",
                )


if __name__ == "__main__":
    unittest.main()
