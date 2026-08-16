"""Prova negativa do engine — e ela mira o COMPORTAMENTO POSITIVO.

POR QUE ESTA PROVA E DIFERENTE DA DO FOLD
------------------------------------------
O engine ja tem uma forma de discriminacao que o fold tambem tem: as recusas
afirmam **sitio**, e nao mensagem, entao um teste que planta um defeito e recebe
outra recusa reprova. Isso cobre o lado negativo — o engine recusar o que deve.

**O que a construcao NAO garante e o outro lado:** que ele FACA o que deve. Um
inject que dispara quando vence, uma decisao que resolve a opcao escolhida e nao
outra, um bloqueio que e o bloqueio e nao uma coincidencia. Sao afirmacoes
positivas, e afirmacao positiva passa por acidente com muito mais facilidade que
recusa — porque so um caminho precisa dar certo, e ha varios jeitos de ele dar
certo pelo motivo errado.

**Ja aconteceu duas vezes nesta fase, e as duas estao aqui como mutacao:**

1. `test_o_bloqueio_de_disparo_agendado_sobrevive_ao_reinicio` afirmava
   `due_injects() == ()` depois do reinicio. O clock reiniciado nasce em
   `T+00:00:00`, entao **nenhum** inject vence nele, com bloqueio ou sem. A
   mutacao `pausa deixa de bloquear` mostra qual teste de fato prova o item 3.
2. `test_a_opcao_escolhida_move_a_flag_pela_projecao` afirmava so que o estado
   MUDOU. Trocar a opcao escolhida pela primeira do `decision_point` tambem
   muda o estado — a mutacao `resolucao pega sempre a primeira opcao` derrubava
   nada. O teste foi reescrito para exigir o valor da opcao, e so entao a
   mutacao passou a ser detectada.

O LOADER E MUTADO JUNTO, e nao em arquivo proprio
--------------------------------------------------
`inject_effects` e `option_effects` sao construidos pelo loader e consumidos pelo
fold atraves do engine. Um erro na construcao so aparece quando alguem dispara ou
decide — entao quem o detecta e a suite do engine, e e aqui que a mutacao dele
precisa estar. A do loader que a suite DELE detecta esta em
`test_pack_loader_probes.py`.

Ver `tests/mutation_harness.py` para a doutrina e o mecanismo.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from mutation_harness import REPO_ROOT, Substituicao, caso_de_prova_negativa

TESTS_PATH = Path(__file__).resolve().parent / "test_inject_engine.py"

#: EM ORDEM DE DEPENDENCIA: o engine importa `LoadedPack` do loader, e a suite
#: carrega o pack no import. Sem essa ordem, o engine mutado importaria o loader
#: original e a mutacao ficaria pela metade.
MUTAVEIS = (
    (
        "loader",
        "range_core.engine.loader.pack_loader",
        REPO_ROOT / "range-core" / "engine" / "loader" / "pack_loader.py",
    ),
    (
        "engine",
        "range_core.engine.inject_engine",
        REPO_ROOT / "range-core" / "engine" / "inject_engine.py",
    ),
)


MUTACOES: dict[str, tuple[list[Substituicao], set[str]]] = {
    # -----------------------------------------------------------------------
    # ITEM 3 — a mutacao que mostra QUAL teste prova o bloqueio.
    #
    # Derruba UM teste, e e o unico que constroi o caso onde o inject esta em
    # atraso no instante da pausa. Os demais passam com o bloqueio removido, e
    # isso nao e defeito deles: e a razao de aquele existir.
    # -----------------------------------------------------------------------
    "pausa deixa de bloquear o disparo agendado": (
        [
            (
                "engine",
                "        if self._clock.is_paused or not self._started():",
                "        if not self._started():",
            )
        ],
        {
            "test_pausado_nao_ha_disparo_agendado",
            "test_o_relogio_de_parede_correr_na_pausa_nao_solta_nada",
        },
    ),
    # -----------------------------------------------------------------------
    # A JANELA, pelos dois lados. Uma mutacao para "dispara antes da hora" e
    # outra para "nunca dispara": a primeira sozinha nao pegaria um engine
    # paralisado, e a segunda sozinha nao pegaria um afobado.
    # -----------------------------------------------------------------------
    "a janela ignora a posicao do relogio: tudo vence sempre": (
        [
            (
                "engine",
                "            if corte < inject.t_relative_seconds <= posicao",
                "            if corte < inject.t_relative_seconds",
            )
        ],
        {
            "test_nada_vence_antes_da_hora",
            "test_o_atraso_existe_antes_da_pausa",
            "test_retomado_o_mesmo_inject_volta_a_vencer",
            "test_a_sequencia_inteira",
            "test_o_inject_abandonado_volta_a_vencer_e_o_anterior_nao",
            "test_a_projecao_volta_ao_ponto_de_corte",
            "test_inject_de_ruido_dispara_e_nao_move_flag",
        },
    ),
    # A MUTACAO "nunca dispara nada" FOI TENTADA E DESCARTADA, e o motivo vale
    # mais que ela. Zerar a posicao derruba VINTE E DOIS testes: quase todo setUp
    # da suite dispara para chegar ao estado que vai examinar, e o efeito cascata
    # por toda parte. E mutacao grossa pela definicao do proprio harness — mede
    # reacao a amputacao, nao deteccao —, e o conjunto declarado ficaria refeito
    # a cada teste novo.
    #
    # A propriedade nao fica sem cobertura: um engine que nao dispara e visto por
    # vinte e dois testes de uma vez. O que ela nao tem, e nao pode ter dada a
    # estrutura da suite, e um DISCRIMINANTE. Fica dito em vez de fingido.
    #
    # No lugar dela, uma mutacao cirurgica sobre a mesma funcao: a ORDEM.
    "a ordem de disparo inverte": (
        [
            (
                "engine",
                "                self._pack.injects, key=lambda i: (i.t_relative_seconds, i.id)",
                "                self._pack.injects, key=lambda i: (-i.t_relative_seconds, i.id)",
            )
        ],
        {"test_vence_na_ordem_do_t_relative"},
    ),
    # -----------------------------------------------------------------------
    # O CORTE — sem ele, o rollback faz os injects ANTERIORES ao ponto de corte
    # dispararem de novo, e `09` secao 3 desenha so `A03 (novamente)`.
    # -----------------------------------------------------------------------
    "o corte do rollback e ignorado pela janela": (
        [("engine", "        corte = self._cut_position()", "        corte = -1")],
        {"test_o_inject_abandonado_volta_a_vencer_e_o_anterior_nao"},
    ),
    # -----------------------------------------------------------------------
    # A RESOLUCAO CONTRA O PACK — a mutacao que o teste antigo nao pegava.
    # -----------------------------------------------------------------------
    "resolucao pega sempre a primeira opcao do decision_point": (
        [
            (
                "loader",
                "                (inject.id, opcao.id): opcao.effects",
                "                (inject.id, opcao.id): inject.decision_point.options[0].effects",
            )
        ],
        {"test_a_opcao_escolhida_move_a_flag_pela_projecao"},
    ),
    "os effects de inject vao todos para o primeiro inject": (
        [
            (
                "loader",
                "            inject_effects={inject.id: inject.effects for inject in injects},",
                "            inject_effects={inject.id: injects[0].effects for inject in injects},",
            )
        ],
        {
            "test_o_disparo_aplica_os_effects_DAQUELE_inject",
            "test_o_inject_de_ruido_nao_escreve_flag_nenhuma",
        },
    ),
    # -----------------------------------------------------------------------
    # ITEM 7 — os extremos derivados. Trocar `start` pela marca de agora produz
    # intervalo de duracao zero SEMPRE, que e plausivel e errado.
    # -----------------------------------------------------------------------
    "o intervalo congelado comeca em agora, e nao na ancora": (
        [
            (
                "engine",
                "            INTERVAL_START: ancora.exercise_timestamp,",
                "            INTERVAL_START: self._clock.marks().exercise_timestamp,",
            )
        ],
        {"test_technical_failure_registra_os_extremos_do_intervalo"},
    ),
    # -----------------------------------------------------------------------
    # P2-13 — o estado de pausa lido do fluxo.
    # -----------------------------------------------------------------------
    "o reinicio le a pausa e nao a aplica": (
        [
            (
                "engine",
                "        if pausado and not self._clock.is_paused:",
                "        if False and not self._clock.is_paused:",
            )
        ],
        {"test_pausado_restaura_pausado", "test_a_posicao_do_exercicio_NAO_e_restaurada"},
    ),
    "a retomada nao devolve o estado a correndo": (
        [
            (
                "engine",
                "        elif evento.event_type in (EXERCISE_RESUMED, EXERCISE_STARTED, EXERCISE_RESET):",
                "        elif evento.event_type in (EXERCISE_STARTED, EXERCISE_RESET):",
            )
        ],
        {
            "test_depois_da_retomada_restaura_correndo",
            "test_o_fluxo_responde_sozinho_sem_engine",
        },
    ),
}


ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTS_PATH, MUTACOES)


if __name__ == "__main__":
    unittest.main()
