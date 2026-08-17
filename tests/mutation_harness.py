"""O harness de prova negativa por mutacao — compartilhado, e por que ele existe.

O QUE E UMA PROVA NEGATIVA POR MUTACAO
---------------------------------------
Verificador que nunca falhou contra violacao plantada nao e verificador — a
doutrina que a Fase 0 fixou em `scripts/phase0_negative_tests.py`. Para SUITE de
teste vale igual: uma suite que nunca ficou vermelha prova que roda, nao que
detecta.

Este modulo planta um defeito na FONTE de um modulo, carrega a versao mutada no
lugar do original, roda a suite que julga aquele modulo, e devolve **quais
testes acusaram**. Quem chama declara, por mutacao, o conjunto exato esperado.

POR QUE COMPARTILHADO, E POR QUE A EXTRACAO VEIO SOZINHA NUM COMMIT
--------------------------------------------------------------------
Nasceu dentro de `tests/test_simulation_state_probes.py`, para o fold. O engine e
o loader precisam do mesmo mecanismo — e a **P2-14** era exatamente eles nao o
terem.

Copiar as ~120 linhas seria a classe D4 com outro nome: duas copias do que mede,
divergindo na terceira. Extrair toca um arquivo ja auditado, entao a extracao e o
unico conteudo do commit que a fez — misturar "o harness mudou de casa" com "ha
mutacoes novas" daria um sinal so, e um vermelho nao diria qual dos dois.

**A extracao foi conferida pelo que ela mede, e nao por a suite continuar
verde.** As oito mutacoes do fold foram rodadas ANTES e DEPOIS, e os conjuntos
vermelhos de cada uma comparados um a um. Conjunto diferente significaria a
extracao alterando o que se mede — que e o unico jeito de este tipo de mudanca
estragar alguma coisa sem ninguem notar.

MUTACAO POR SITIO, E NAO POR AMPUTACAO
--------------------------------------
A primeira versao desta prova substituia FUNCOES INTEIRAS. Trocar
`_surviving_writes_mask` por "tudo sobrevive" derrubava, junto, quatro testes de
recusa — porque a validacao de ancora mora dentro dela. Aquilo mede reacao a
amputacao, nao deteccao da violacao.

Aqui cada mutacao e cirurgica: mover um limite de intervalo, remover um `raise`,
trocar um discriminante, zerar um retorno. E cada uma declara o CONJUNTO EXATO de
testes que deve ficar vermelho — nem mais, nem menos. Mutacao que derruba mais do
que devia e mutacao grossa; que derruba menos denuncia teste que nao prova o que
diz.

POR QUE `importlib` E NAO EXECUCAO DINAMICA
-------------------------------------------
`05_SECURITY_REQUIREMENTS.md` §1 proibe execucao dinamica de codigo, e
`tools/check_security_constraints.py` recusa os tres builtins que a fazem. A
primeira versao usava dois deles sobre a fonte mutada e foi barrada pelo hook.
Corretamente, e a regra nao se contorna.

A fonte mutada e escrita em arquivo temporario e carregada por
`importlib.util.spec_from_file_location`, que e como qualquer ferramenta de teste
carrega modulo por caminho. Nao ha codigo montado em tempo de execucao: ha um
ARQUIVO, com o mesmo estatuto de qualquer outro modulo importado.

A mutacao e por TEXTO sobre a fonte, e nao por monkeypatch, porque patch
substitui simbolo enquanto o defeito que se quer plantar e o que um humano
cometeria editando a linha. Cada substituicao exige casar EXATAMENTE UMA VEZ: se
a linha alvo mudar de forma, a prova quebra alto em vez de plantar outra coisa em
silencio.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import types
import unittest
from collections.abc import Iterable, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: `(chave, modulo importavel, caminho da fonte)`.
Mutavel = tuple[str, str, Path]

#: `(chave do mutavel, texto original, texto plantado)`.
Substituicao = tuple[str, str, str]


def carrega_modulo(nome: str, caminho: Path) -> types.ModuleType:
    """Carrega um modulo por caminho, registrando ANTES de executar.

    Registrar antes nao e cerimonia: `dataclass` resolve anotacoes por
    `sys.modules[cls.__module__]` enquanto processa a classe, e sem a entrada o
    modulo mutado quebra em `AttributeError` na primeira dataclass — falha do
    instrumento, que a prova leria como deteccao.
    """
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:  # pragma: no cover - caminho fixo
        raise AssertionError(f"nao foi possivel carregar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    try:
        spec.loader.exec_module(modulo)
    except BaseException:
        del sys.modules[nome]
        raise
    return modulo


def fonte_mutada(caminho: Path, chave: str, substituicoes: Iterable[Substituicao]) -> str:
    """A fonte com as substituicoes daquele mutavel aplicadas.

    Casar exatamente uma vez e a guarda que impede a prova de plantar outra coisa
    quando a linha alvo muda de forma.
    """
    source = caminho.read_text(encoding="utf-8")
    for onde, alvo, troca in substituicoes:
        if onde != chave:
            continue
        ocorrencias = source.count(alvo)
        if ocorrencias != 1:
            raise AssertionError(
                f"a mutacao precisa casar exatamente uma vez, casou {ocorrencias}: "
                f"{alvo!r}. A linha alvo mudou de forma, e a prova negativa "
                "deixou de plantar o que diz plantar."
            )
        source = source.replace(alvo, troca)
    return source


def vermelhos(
    mutaveis: Sequence[Mutavel],
    tests_path: Path,
    substituicoes: Sequence[Substituicao],
) -> set[str]:
    """Nomes de METODO que falham com a mutacao plantada.

    Os mutaveis sao carregados EM ORDEM DE DEPENDENCIA e injetados em
    `sys.modules` sob o nome real, para que o import de um resolva para a versao
    mutada do outro. Sem isso, um modulo mutado importaria o original de outro e
    a mutacao ficaria pela metade.

    O parametro de `subTest` e descartado do nome: o que se afirma e QUAL teste
    acusa, e nao quantos subcasos dele.
    """
    anteriores: dict[str, types.ModuleType | None] = {}
    with tempfile.TemporaryDirectory() as temporario:
        try:
            # O REGISTRO ENTROU NO `try`, e a diferenca nao e de estilo.
            #
            # Ele ficava FORA: se um mutavel fosse registrado e o SEGUINTE
            # levantasse — o que `fonte_mutada` faz de proposito quando a linha
            # alvo muda de forma —, os ja registrados nunca eram restaurados. Os
            # modulos mutados sobreviviam em `sys.modules` pelo resto do
            # processo, e toda a suite seguinte rodava contra CODIGO MUTADO,
            # com as falhas aparecendo longe da causa.
            #
            # Achado pelo `test_procedencia_dos_pacotes` da peca 0 desta fase, que
            # e literalmente a pergunta "de onde veio o modulo que executou?" —
            # ele acusou `pack_loader` vindo de um arquivo temporario. A P3-4
            # fechava a divergencia entre ARVORES; esta e a mesma pergunta dentro
            # de um processo so.
            for chave, modulo, caminho in mutaveis:
                destino = Path(temporario) / f"{chave}_mutado.py"
                destino.write_text(
                    fonte_mutada(caminho, chave, substituicoes), encoding="utf-8"
                )
                anteriores[modulo] = sys.modules.get(modulo)
                sys.modules[modulo] = carrega_modulo(f"{chave}_mutado", destino)

            suite_modulo = carrega_modulo(f"suite_contra_{tests_path.stem}", tests_path)
            suite = unittest.defaultTestLoader.loadTestsFromModule(suite_modulo)
            resultado = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        finally:
            # Restaurar e obrigatorio: recarregar o que o runner esta executando
            # deixaria a suite em curso apontando para modulos mutados.
            for modulo, anterior in anteriores.items():
                if anterior is not None:
                    sys.modules[modulo] = anterior
                else:  # pragma: no cover - todos estao importados nos chamadores
                    sys.modules.pop(modulo, None)

    nomes = set()
    for caso, _ in list(resultado.failures) + list(resultado.errors):
        nomes.add(caso.id().split(" ")[0].rsplit(".", 1)[-1])
    return nomes


def caso_de_prova_negativa(
    mutaveis: Sequence[Mutavel],
    tests_path: Path,
    mutacoes: dict[str, tuple[list[Substituicao], set[str]]],
) -> type[unittest.TestCase]:
    """Monta o `TestCase` que roda a tabela de mutacoes de um chamador.

    Existe para os dois `*_probes.py` nao repetirem as duas asserções que
    importam — a ancora sem mutacao, e o conjunto exato por mutacao. Repetir
    essas duas seria repetir justamente a parte que define o que a prova
    significa.
    """

    class ProvaNegativa(unittest.TestCase):
        def test_a_suite_esta_verde_sem_mutacao(self):
            """Ancora da prova: sem violacao plantada, nada acusa.

            Sem esta ancora, uma suite quebrada por outro motivo faria TODAS as
            mutacoes "detectarem", e a prova negativa passaria afirmando o
            contrario do que ha.
            """
            self.assertEqual(vermelhos(mutaveis, tests_path, []), set())

        def test_cada_mutacao_e_detectada_pelos_testes_certos(self):
            for descricao, (substituicoes, esperados) in mutacoes.items():
                with self.subTest(mutacao=descricao):
                    obtidos = vermelhos(mutaveis, tests_path, substituicoes)
                    self.assertNotEqual(
                        obtidos, set(), "mutacao plantada e nenhum teste acusou"
                    )
                    self.assertEqual(
                        obtidos,
                        esperados,
                        "o conjunto que acusou nao e o declarado: mutacao grossa "
                        "demais, ou teste que nao prova o que diz",
                    )

    return ProvaNegativa
