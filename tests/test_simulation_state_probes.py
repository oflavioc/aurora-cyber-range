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
    # A LINHAGEM MUDOU DE CASA DE NOVO, e o harness quebrou alto outra vez — que
    # e o comportamento que o paragrafo acima ja registrava. O corpo da mascara
    # saiu do fold para `range_core.events.linhagem` no spec-change
    # `linhagem-corrente-e-o-avaliador`, porque a spec passou a exigir UMA
    # definicao para o fold e para o avaliador de predicados.
    #
    # As tres mutacoes de ancora e a do limite do intervalo apontam para ca. O
    # que ficou no fold e o TRADUTOR de sitio, e mutar o tradutor prova outra
    # coisa — por isso elas mudaram de alvo em vez de o alvo mudar de nome.
    (
        "linhagem",
        "range_core.events.linhagem",
        REPO_ROOT / "range-core" / "events" / "linhagem.py",
    ),
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
        [("linhagem", "for j in range(anchor + 1, index):", "for j in range(anchor + 2, index):")],
        {
            "test_rollback_devolve_a_flag_escrita_ao_default",
            "test_rollback_atravessa_escrita_de_participant_action",
        },
    ),
    "raise de ancora posterior ao rollback removido": (
        [("linhagem", "if anchor > index:", "if anchor > index and False:")],
        {"test_cada_sitio_recusa_pelo_proprio_motivo"},
    ),
    "raise de ancora ja abandonada removido": (
        [("linhagem", "if not surviving[anchor]:", "if not surviving[anchor] and False:")],
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
    # M1 DA TERCEIRA AUDITORIA — a consequencia normativa 1 de `00` §3.
    #
    # *"Declaracao do participante nunca altera ground truth."* Antes desta
    # entrada, acrescentar um ramo de declaracao ao `_writes_of` deixava a suite
    # INTEIRA verde: nenhum teste afirmava a ausencia de escrita, so a
    # sobrevivencia do evento no fluxo. A regra que sustenta o modelo das quatro
    # verdades caia sem nada acusar.
    #
    # O ramo plantado e o mais inocente possivel — devolve a PRIMEIRA flag dos
    # defaults com `True`. Se ate ele derruba o teste, ramo nenhum passa.
    #
    # A mutacao tem DUAS substituicoes porque o modulo nao importa
    # `CONTAINMENT_DECLARED`: plantar so o ramo daria `NameError`, e erro de
    # carga nao e o mesmo que teste vermelho — o harness distingue os dois.
    "declaracao passa a escrever flag no fold": (
        [
            (
                "fold",
                "    DECISION_MADE,\n",
                "    CONTAINMENT_DECLARED,\n    DECISION_MADE,\n",
            ),
            (
                "fold",
                "    if event.event_type == DECISION_MADE:",
                "    if event.event_type == CONTAINMENT_DECLARED:\n"
                "        return {k: True for k in list(declarations.flag_defaults)[:1]}\n"
                "\n"
                "    if event.event_type == DECISION_MADE:",
            ),
        ],
        {"test_declaracao_NUNCA_move_flag"},
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
    # O ALVO MUDOU DE FORMA junto com a casa da linhagem: o `raise` com o sitio
    # literal virou uma ENTRADA DO MAPA de traducao. O eixo e o mesmo — trocar um
    # discriminante e ser acusado —, e o alvo novo prova algo a mais: que o mapa
    # discrimina, que e o risco que ele proprio introduziu.
    "discriminante trocado num sitio so": (
        [
            (
                "fold",
                "    ANCORA_DESCONHECIDA: Site.ANCHOR_UNKNOWN,\n",
                "    ANCORA_DESCONHECIDA: Site.ANCHOR_MISSING,\n",
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
