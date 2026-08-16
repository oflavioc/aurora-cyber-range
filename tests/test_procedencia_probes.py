"""A prova de que `test_procedencia_dos_pacotes` REPROVA — P3-4.

POR QUE ELE PRECISA DE PROBE, E NAO SO DE PASSAR
-------------------------------------------------
O teste da procedencia afirma uma ausencia: *nenhum* dos tres pacotes vem de
fora. Asserção de ausencia passa por dois motivos — porque a ausencia e
verdadeira, ou porque ela nunca poderia ser observada. Foi o H1 da segunda
auditoria da Fase 3: `dormidas == []` era verdadeiro e vazio, e o registro
anunciava a cobertura que nao existia.

Aqui a diferenca e concreta: se `_raizes_de` devolvesse `[]` para os tres, o
teste passaria verde para sempre. A divergencia PLANTADA e o que separa os dois
casos.

COMO A DIVERGENCIA E PLANTADA
------------------------------
Um pacote isca num diretorio temporario, e `PYTHONPATH` apontando para ele. A
ordem do `sys.path` faz o resto: `PYTHONPATH` vem ANTES do que a instalacao
editavel acrescenta, entao a isca vence o caminho instalado — que e exatamente
a forma da P3-4, com os papeis trocados.

O subprocesso roda com o CWD **no diretorio temporario**, e nao na raiz: com o
CWD na arvore, `domains` e `contracts` resolveriam por ela e a isca nunca seria
alcancada. O teste sob prova nao se importa — ele deriva a raiz do `__file__`,
e nao do CWD.

QUATRO EIXOS, E O CONTROLE
---------------------------
Tres iscas de pacote COMUM, uma por nome, porque os tres chegam ao `sys.path`
por mecanismos diferentes. Uma isca de NAMESPACE para `contracts`, que e o caso
da quimera — o pacote montado a partir de duas raizes ao mesmo tempo, em que a
metade contida passaria no primeiro teste.

E o controle: **sem isca, o mesmo subprocesso passa**. Sem ele, um teste que
reprovasse sempre — por erro de invocacao, por exemplo — daria os quatro eixos
verdes sem provar nada.

`tempfile` fica FORA da arvore, e isso e declarado em `docs/process/WORKFLOW.md`:
nada escrito na arvore sobrevive ao worktree, nada escrito fora dela sobrevive
ao processo.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SOB_PROVA = RAIZ / "tests" / "test_procedencia_dos_pacotes.py"


def _executa(isca: Path | None) -> subprocess.CompletedProcess[str]:
    """Roda o teste sob prova num subprocesso, com o CWD fora da arvore."""
    ambiente = dict(os.environ)
    ambiente.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as temporario:
        if isca is not None:
            ambiente["PYTHONPATH"] = str(isca)
        return subprocess.run(
            [sys.executable, str(SOB_PROVA)],
            cwd=temporario,
            env=ambiente,
            capture_output=True,
            text=True,
        )


class ProcedenciaReprova(unittest.TestCase):
    def test_o_controle_passa_sem_isca(self) -> None:
        """A metade que impede as outras de serem verdadeiras por vacuidade."""
        resultado = _executa(None)
        self.assertEqual(
            resultado.returncode, 0,
            "o teste da procedencia reprovou SEM divergencia plantada — os eixos "
            "abaixo ficariam verdes provando outra coisa.\n"
            + resultado.stdout + resultado.stderr,
        )

    def test_pacote_vindo_de_fora_da_arvore_REPROVA(self) -> None:
        for nome in ("range_core", "contracts", "domains"):
            with self.subTest(pacote=nome), tempfile.TemporaryDirectory() as base:
                isca = Path(base)
                (isca / nome).mkdir()
                (isca / nome / "__init__.py").write_text("", encoding="utf-8")
                resultado = _executa(isca)
                saida = resultado.stdout + resultado.stderr
                self.assertNotEqual(
                    resultado.returncode, 0,
                    f"{nome} veio de {isca} e o teste da procedencia PASSOU.\n" + saida,
                )
                self.assertIn(
                    nome, saida,
                    "reprovou sem nomear o pacote de procedencia errada: a mensagem "
                    "e o que faz a reprovacao acionavel",
                )

    def test_namespace_montado_de_DUAS_raizes_REPROVA(self) -> None:
        """A quimera: `contracts` daqui E de fora, ao mesmo tempo.

        Sem `__init__.py` a isca e uma PORCAO de namespace, e o Python compoe as
        duas em um pacote so. A metade contida continuaria passando no teste de
        raiz unica — e e por isso que aquele teste tem uma segunda asserção.
        """
        with tempfile.TemporaryDirectory() as base:
            isca = Path(base)
            (isca / "contracts").mkdir()
            resultado = _executa(isca)
            saida = resultado.stdout + resultado.stderr
            self.assertNotEqual(
                resultado.returncode, 0,
                "namespace montado a partir de duas raizes PASSOU: metade do pacote "
                "vinha de fora da arvore e nada acusou.\n" + saida,
            )
            # O NOME DO DIRETORIO ISCA, e nao uma frase da mensagem: reprovar
            # sem dizer DE ONDE veio a outra metade deixa o proximo leitor com o
            # mesmo trabalho que o teste existe para poupar.
            self.assertIn(isca.name, saida)


if __name__ == "__main__":
    unittest.main()
