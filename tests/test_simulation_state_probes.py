"""Prova negativa do fold: os testes ficam vermelhos contra violacao plantada.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Verificador que nunca falhou contra violacao plantada nao e verificador — e a
doutrina que a Fase 0 fixou em `scripts/phase0_negative_tests.py` e que os
executores de exemplo repetem em `*_probes.py`. Vale para o fold: uma suite que
nunca ficou vermelha prova que roda, nao que detecta.

MUTACAO POR SITIO, E NAO POR AMPUTACAO
--------------------------------------
A primeira tentativa desta prova substituia FUNCOES INTEIRAS — trocar
`_surviving_writes_mask` por "tudo sobrevive" derrubava, junto, quatro testes de
recusa, porque a validacao de ancora mora dentro dela. Aquilo mede reacao a
amputacao, nao deteccao da violacao, e versionar assim versionaria a confusao.

Aqui cada mutacao e cirurgica: mover um limite de intervalo, remover um `raise`,
trocar um discriminante, zerar um retorno. E cada uma declara o CONJUNTO EXATO
de testes que deve ficar vermelho — nem mais, nem menos. Mutacao que derruba
mais do que devia e mutacao grossa; que derruba menos denuncia teste que nao
prova o que diz.

POR QUE `importlib` E NAO EXECUCAO DINAMICA
-------------------------------------------
`05_SECURITY_REQUIREMENTS.md` §1 proibe execucao dinamica de codigo, e
`tools/check_security_constraints.py` recusa os tres builtins que a fazem —
avaliacao de expressao, execucao de codigo montado e compilacao em tempo de
execucao. A primeira versao desta prova usava dois deles sobre a fonte mutada e
foi barrada pelo hook. Corretamente, e a regra nao se contorna.

A fonte mutada e escrita em arquivo temporario e carregada por
`importlib.util.spec_from_file_location`, que e como qualquer ferramenta de
teste carrega modulo por caminho. Nao ha codigo montado em tempo de execucao: ha
um ARQUIVO, com o mesmo estatuto de qualquer outro modulo importado.

A mutacao e por texto sobre a fonte, e nao por monkeypatch, porque patch
substitui simbolo enquanto o defeito que se quer plantar e o que um humano
cometeria editando a linha. Cada substituicao exige casar EXATAMENTE UMA VEZ: se
a linha alvo mudar de forma, a prova quebra alto em vez de plantar outra coisa
em silencio.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FOLD_PATH = REPO_ROOT / "range-core" / "state" / "simulation_state.py"
TESTS_PATH = Path(__file__).resolve().parent / "test_simulation_state.py"
FOLD_MODULE = "range_core.state.simulation_state"


def _carrega(nome: str, caminho: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:  # pragma: no cover - caminho fixo
        raise AssertionError(f"nao foi possivel carregar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    # REGISTRAR ANTES DE EXECUTAR nao e cerimonia: `dataclass` resolve
    # anotacoes por `sys.modules[cls.__module__]` enquanto processa a classe, e
    # sem a entrada o modulo mutado quebra em `AttributeError` na primeira
    # dataclass — falha do instrumento, que a prova leria como deteccao.
    sys.modules[nome] = modulo
    try:
        spec.loader.exec_module(modulo)
    except BaseException:
        del sys.modules[nome]
        raise
    return modulo


def _fonte_mutada(substituicoes: list[tuple[str, str]]) -> str:
    source = FOLD_PATH.read_text(encoding="utf-8")
    for alvo, troca in substituicoes:
        ocorrencias = source.count(alvo)
        if ocorrencias != 1:
            raise AssertionError(
                f"a mutacao precisa casar exatamente uma vez, casou {ocorrencias}: "
                f"{alvo!r}. A linha alvo mudou de forma, e a prova negativa "
                "deixou de plantar o que diz plantar."
            )
        source = source.replace(alvo, troca)
    return source


def _vermelhos(substituicoes: list[tuple[str, str]]) -> set[str]:
    """Nomes de METODO que falham contra o fold mutado.

    O parametro de `subTest` e descartado: o que se afirma e QUAL teste acusa,
    e nao quantos subcasos dele.
    """
    with tempfile.TemporaryDirectory() as temporario:
        alvo = Path(temporario) / "fold_mutado.py"
        alvo.write_text(_fonte_mutada(substituicoes), encoding="utf-8")
        fold = _carrega("fold_mutado", alvo)

        # A copia da suite e carregada com o fold mutado no lugar do real, para
        # o `from ... import ...` dela resolver para o mutado. O modulo
        # compartilhado e restaurado em seguida: recarregar o que o runner esta
        # executando seria mexer na propria suite em curso.
        anterior = sys.modules.get(FOLD_MODULE)
        sys.modules[FOLD_MODULE] = fold
        try:
            suite_modulo = _carrega("testes_contra_fold_mutado", TESTS_PATH)
        finally:
            if anterior is not None:
                sys.modules[FOLD_MODULE] = anterior
            else:  # pragma: no cover - o fold sempre esta importado aqui
                del sys.modules[FOLD_MODULE]

        suite = unittest.defaultTestLoader.loadTestsFromModule(suite_modulo)
        resultado = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)

    nomes = set()
    for caso, _ in list(resultado.failures) + list(resultado.errors):
        nomes.add(caso.id().split(" ")[0].rsplit(".", 1)[-1])
    return nomes


# ---------------------------------------------------------------------------
# AS MUTACOES. Cada uma: o que se planta, e QUEM exatamente deve acusar.
# ---------------------------------------------------------------------------
MUTACOES: dict[str, tuple[list[tuple[str, str]], set[str]]] = {
    "limite do intervalo abandonado movido em um": (
        [("for j in range(anchor + 1, index):", "for j in range(anchor + 2, index):")],
        {
            "test_rollback_devolve_a_flag_escrita_ao_default",
            "test_rollback_atravessa_escrita_de_participant_action",
        },
    ),
    "raise de ancora posterior ao rollback removido": (
        [("if anchor > index:", "if anchor > index and False:")],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "raise de ancora ja abandonada removido": (
        [("if not surviving[anchor]:", "if not surviving[anchor] and False:")],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "conferencia de epoch de evento desligada": (
        [
            (
                "if event.simulation_epoch != rollbacks:",
                "if event.simulation_epoch != rollbacks and False:",
            )
        ],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "pino do pack desligado": (
        [("if atual != esperado:", "if atual != esperado and False:")],
        {"test_p6_pack_divergente_do_pino_e_recusado"},
    ),
    "estado deixa de ser total: nao semeia com os defaults": (
        [
            (
                "flags: dict[str, FlagValue] = dict(declarations.flag_defaults)",
                "flags: dict[str, FlagValue] = {}",
            )
        ],
        {
            "test_p5_flag_nunca_escrita_permanece_no_default",
            "test_rollback_devolve_a_flag_escrita_ao_default",
            "test_rollback_atravessa_escrita_de_participant_action",
            "test_participant_action_abandonada_permanece_no_fluxo",
        },
    ),
    "discriminante trocado num sitio so": (
        [
            (
                "                Site.ANCHOR_UNKNOWN,\n",
                "                Site.ANCHOR_MISSING,\n",
            )
        ],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "epoch corrente sempre zero": (
        [
            (
                "return sum(1 for event in events if event.event_type == ROLLBACK_PERFORMED)",
                "return 0",
            )
        ],
        {
            "test_p4_epoch_nunca_decresce",
            "test_rollback_devolve_a_flag_escrita_ao_default",
            "test_rollback_atravessa_escrita_de_participant_action",
        },
    ),
}


class ProvaNegativa(unittest.TestCase):
    def test_a_suite_esta_verde_sem_mutacao(self):
        """Ancora da prova: sem violacao plantada, nada acusa.

        Sem esta ancora, uma suite quebrada por outro motivo faria TODAS as
        mutacoes "detectarem", e a prova negativa passaria afirmando o contrario
        do que ha.
        """
        self.assertEqual(_vermelhos([]), set())

    def test_cada_mutacao_e_detectada_pelos_testes_certos(self):
        for descricao, (substituicoes, esperados) in MUTACOES.items():
            with self.subTest(mutacao=descricao):
                obtidos = _vermelhos(substituicoes)
                self.assertNotEqual(
                    obtidos, set(), "mutacao plantada e nenhum teste acusou"
                )
                self.assertEqual(
                    obtidos,
                    esperados,
                    "o conjunto que acusou nao e o declarado: mutacao grossa "
                    "demais, ou teste que nao prova o que diz",
                )


if __name__ == "__main__":
    unittest.main()
