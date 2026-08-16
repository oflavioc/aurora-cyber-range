"""Os tres pacotes resolvem sob a raiz DESTA arvore — P3-4.

O QUE ESTE ARQUIVO AFIRMA, E POR QUE ELE E CURTO
------------------------------------------------
`range_core`, `contracts` e `domains` sao importados de dentro da arvore em que
esta suite esta rodando, e nao de outra. So isso.

A MEDICAO QUE O ORIGINOU, no worktree de auditoria da Fase 3:

    domains    -> worktree          (diretorio real, o CWD vence no sys.path)
    contracts  -> worktree          (idem)
    range_core -> ARVORE PRINCIPAL  (instalacao editavel, caminho ABSOLUTO)

`range-core/` tem hifen e nao e importavel pela arvore — e o argumento que o
proprio `pyproject.toml` escreve —, entao so resta o caminho instalado. O
auditor executava o adapter e os testes do commit candidato **contra o nucleo
de outro commit**, e a saida parecia normal: e a forma exata de uma propriedade
parecer verificada sem estar.

POR QUE SO AGORA
----------------
Ate a Fase 3 a auditoria rodava DEPOIS do merge, e a arvore principal estava no
mesmo commit do worktree — a divergencia existia e nao mordia. A Fase 4 e a
primeira auditada ANTES do merge: os dois SHAs sao diferentes de verdade.

A pendencia ficou sem teste de proposito, e a nota dela diz por que: escrito
antes, ele reprovaria toda auditoria feita em worktree, e mudar o criterio de
reprovacao do auditor no PR que ele vai auditar e decisao do operador. Foi
decidido, e a outra metade — o venv que faz esta prova passar — esta em
`scripts/start_checkpoint_audit.sh`.

A RAIZ VEM DO `__file__`, E NAO DO CWD
--------------------------------------
`Path(__file__).parents[1]` e a arvore a que ESTE ARQUIVO pertence. Derivar do
CWD responderia "de onde alguem chamou", que e a pergunta que ja tem resposta
errada disponivel; derivar do git responderia sobre repositorio, e o worktree e
o mesmo repositorio. A pergunta e sobre a ARVORE, e o arquivo sabe em qual esta.

A PERGUNTA E SOBRE O MODULO QUE EXECUTOU, E NAO SOBRE O `__path__`
------------------------------------------------------------------
A primeira versao deste arquivo afirmava sobre `__path__`, e **reprovou na
primeira execucao** — por um motivo que vale registrado, porque ele muda a
formulacao e nao so o codigo. A instalacao editavel de PEP 660 injeta em
`contracts.__path__` uma entrada SINTETICA:

    __editable__.aurora_cyber_range-0.1.0.finder.__path_hook__

Ela nao e diretorio, nao existe em disco e nunca vai estar "sob a raiz". Uma
regra sobre `__path__` reprovaria toda arvore com instalacao editavel — que sao
todas —, e a correcao obvia (ignorar entrada inexistente) seria pior: e
justamente por esse gancho que a arvore principal continuaria alcancavel.

Entao a asserção mudou de objeto: **todo modulo dos tres pacotes que este
processo importou tem `__file__` sob esta raiz**. E o fato que importa — de onde
veio o codigo que rodou —, e nao a lista de lugares onde o importador poderia
ter procurado.

E ela cresce sozinha com a suite: num `discover`, todos os modulos de teste sao
importados ANTES de qualquer teste rodar, entao o que este teste varre e tudo o
que a suite inteira tocou, e nao uma lista que alguem lembrou de manter.

LIMITE DECLARADO: um modulo que exista SO na outra arvore continua alcancavel
pelo gancho do instalador editavel, e este teste nao o veria enquanto ninguem o
importasse. O que ele garante e o que a P3-4 pede — que o codigo executado nesta
suite venha deste checkout —, e nao que a outra arvore esteja inalcancavel.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Os tres, e nao um. Cada um chega ao `sys.path` por um mecanismo diferente —
#: `range_core` por mapeamento de `package-dir`, `contracts` como pacote de
#: namespace, `domains` como pacote comum —, e a P3-4 mostrou que eles resolvem
#: de formas diferentes. Testar so o que quebrou seria testar a lembranca.
#:
#: O representante existe para que o arquivo prove alguma coisa quando rodado
#: SOZINHO: sem ele, `sys.modules` teria so o que o proprio teste importou.
REPRESENTANTES = {
    "range_core": "range_core.state.simulation_state",
    "contracts": "contracts.generated.events",
    "domains": "domains.academus.api.surface",
}


class ProcedenciaDosPacotes(unittest.TestCase):
    def test_todo_modulo_importado_dos_tres_pacotes_veio_desta_arvore(self) -> None:
        for pacote, representante in REPRESENTANTES.items():
            with self.subTest(pacote=pacote):
                try:
                    importlib.import_module(representante)
                except ImportError as erro:
                    self.fail(
                        f"{pacote}: {representante} nao pode ser importado ({erro}). "
                        "Pacote que sombreia o desta arvore sem trazer os modulos "
                        "dela e a P3-4 na forma mais barulhenta."
                    )

        for nome, modulo in sorted(sys.modules.items()):
            if nome.split(".")[0] not in REPRESENTANTES:
                continue
            arquivo = getattr(modulo, "__file__", None)
            if arquivo is None:  # namespace puro nao tem arquivo proprio
                continue
            with self.subTest(modulo=nome):
                self.assertTrue(
                    Path(arquivo).resolve().is_relative_to(RAIZ),
                    f"{nome} foi importado de {arquivo}, que esta FORA de {RAIZ}.\n"
                    "Esta suite estaria medindo o codigo de outra arvore — P3-4.\n"
                    "Num worktree de auditoria, o lancador cria o venv que instala "
                    "ESTE checkout; fora dele, `pip install -e .` na arvore em que "
                    "se trabalha.",
                )

    def test_nenhum_pacote_e_montado_a_partir_de_DUAS_arvores(self) -> None:
        """A quimera silenciosa: metade daqui, metade de outra arvore.

        `contracts` e pacote de NAMESPACE — sem `__init__.py` —, e namespace se
        compoe: dois diretorios de mesmo nome em raizes diferentes viram um
        pacote so, com os modulos de ambos. A asserção acima passaria para todo
        modulo que a suite tivesse importado da metade contida.

        Aqui a conta e sobre DIRETORIOS REAIS de `__path__`, e o gancho sintetico
        do instalador editavel fica de fora por nao ser diretorio — dito no
        cabecalho, porque e ele que mantem a outra arvore alcancavel.
        """
        for pacote in REPRESENTANTES:
            with self.subTest(pacote=pacote):
                modulo = importlib.import_module(pacote)
                # DISTINTOS, e nao a contagem de entradas: medido, o `contracts`
                # desta arvore aparece DUAS VEZES em `__path__` — uma pelo
                # `sys.path` e outra resolvida pelo gancho do instalador
                # editavel, que aponta para o mesmo diretorio real. Contar
                # entradas acusaria a arvore sadia; o que importa e de quantas
                # ARVORES o pacote vem.
                reais = sorted({
                    Path(caminho).resolve()
                    for caminho in getattr(modulo, "__path__", [])
                    if Path(caminho).is_dir()
                })
                self.assertEqual(
                    len(reais), 1,
                    f"{pacote} e montado a partir de {len(reais)} diretorios: {reais}.\n"
                    "Um pacote com duas origens executa codigo de duas arvores, e "
                    "nada na saida diz qual modulo veio de onde.",
                )


if __name__ == "__main__":  # o probe executa este arquivo diretamente
    unittest.main()
