"""Prova negativa do fold: os testes ficam vermelhos contra violacao plantada.

O MECANISMO SAIU DAQUI, E O QUE ELE PROVA NAO MUDOU
----------------------------------------------------
O harness — carregar fonte mutada, rodar a suite, colher quem acusou — vivia
neste arquivo e foi extraido para `tests/mutation_harness.py` ao fechar a
**P2-14**: o engine e o loader precisavam do mesmo mecanismo, e copiar as ~120
linhas seria a classe D4 com outro nome.

**A extracao foi conferida pelo que ela mede.** As oito mutacoes abaixo foram
rodadas antes e depois, e os conjuntos vermelhos comparados um a um: os oito
identicos. Suite verde depois de uma extracao nao prova nada sobre uma prova
negativa — o que prova e o conjunto que cada mutacao derruba continuar sendo o
mesmo.

O QUE FICOU AQUI, e por que
---------------------------
A TABELA DE MUTACOES. Ela e conhecimento sobre ESTE modulo — quais linhas do
fold, quando alteradas, devem derrubar quais testes —, e nao mecanismo. Mecanismo
se compartilha; a tabela nao tem o que compartilhar.

Ver `tests/mutation_harness.py` para a doutrina, o motivo de a mutacao ser por
sitio e nao por amputacao, e por que o carregamento usa `importlib` em vez de
execucao dinamica.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from mutation_harness import REPO_ROOT, Substituicao, caso_de_prova_negativa

TESTS_PATH = Path(__file__).resolve().parent / "test_simulation_state.py"

#: OS MODULOS MUTAVEIS, em ordem de dependencia.
#:
#: Sao dois porque a regra da epoch e COMPARTILHADA entre o fold e o store —
#: `range_core.events.epoch` — e mutar so o fold deixaria de alcanca-la. A
#: primeira versao desta prova mutava um arquivo so, e quebrou alto no dia em
#: que o calculo mudou de casa: a guarda de "casar exatamente uma vez" acusou em
#: vez de plantar nada em silencio, que e o comportamento desejado.
MUTAVEIS = (
    ("epoch", "range_core.events.epoch", REPO_ROOT / "range-core" / "events" / "epoch.py"),
    (
        "fold",
        "range_core.state.simulation_state",
        REPO_ROOT / "range-core" / "state" / "simulation_state.py",
    ),
)


# ---------------------------------------------------------------------------
# AS MUTACOES. Cada uma: o que se planta, e QUEM exatamente deve acusar.
# ---------------------------------------------------------------------------
MUTACOES: dict[str, tuple[list[Substituicao], set[str]]] = {
    "limite do intervalo abandonado movido em um": (
        [("fold", "for j in range(anchor + 1, index):", "for j in range(anchor + 2, index):")],
        {
            "test_rollback_devolve_a_flag_escrita_ao_default",
            "test_rollback_atravessa_escrita_de_participant_action",
        },
    ),
    "raise de ancora posterior ao rollback removido": (
        [("fold", "if anchor > index:", "if anchor > index and False:")],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "raise de ancora ja abandonada removido": (
        [("fold", "if not surviving[anchor]:", "if not surviving[anchor] and False:")],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "conferencia de epoch de evento desligada": (
        [
            (
                "fold",
                "if event.simulation_epoch != rollbacks:",
                "if event.simulation_epoch != rollbacks and False:",
            )
        ],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "pino do pack desligado": (
        [("fold", "if atual != esperado:", "if atual != esperado and False:")],
        {"test_p6_pack_divergente_do_pino_e_recusado"},
    ),
    "estado deixa de ser total: nao semeia com os defaults": (
        [
            (
                "fold",
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
                "fold",
                "                Site.ANCHOR_UNKNOWN,\n",
                "                Site.ANCHOR_MISSING,\n",
            )
        ],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "epoch corrente sempre zero": (
        [
            (
                "epoch",
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


ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTS_PATH, MUTACOES)


if __name__ == "__main__":
    unittest.main()
