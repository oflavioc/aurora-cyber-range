"""Prova negativa do loader — o boot, o pino e a forma canonica.

O QUE ESTA PROVA MIRA
---------------------
As recusas do loader ja discriminam por **sitio**, e a suite as afirma uma a uma.
O que estava sem prova era, de novo, o lado POSITIVO: que ele leia certo o que
aceita.

Um loader que recusa tudo o que deve recusar e ainda assim converte `t_relative`
errado, ou hasheia um escopo diferente do declarado, passa em todos os testes de
recusa — e o defeito aparece no agendamento ou na reconstrucao, fases adiante.

**DUAS mutacoes daqui nao derrubavam nada, e as duas viraram teste.**

O prefixo de caminho na forma canonica existe, segundo `canonical.py`, para que
mover conteudo de um arquivo para outro nao produza o mesmo hash — e a afirmacao
vivia so na prosa. `sort_keys=True` existe para que reordenar chaves nao mude o
hash — idem.

**E o primeiro teste que escrevi para o prefixo tambem nao derrubava a mutacao.**
Ele trocava DOIS documentos de lugar, e isso muda o hash mesmo sem prefixo,
porque a ordem de concatenacao e por caminho e os corpos trocam de posicao. O
caso que isola o prefixo e um documento so, sob dois nomes. Os dois testes finais
sao `test_o_MESMO_documento_sob_outro_nome_muda_o_hash` e
`test_a_ORDEM_das_chaves_no_arquivo_nao_muda_o_hash`.

Ver `tests/mutation_harness.py` para a doutrina e o mecanismo.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from mutation_harness import REPO_ROOT, Substituicao, caso_de_prova_negativa

TESTS_PATH = Path(__file__).resolve().parent / "test_pack_loader.py"

LOADER = REPO_ROOT / "range-core" / "engine" / "loader"

#: EM ORDEM DE DEPENDENCIA: `pack_loader` importa de `canonical`.
MUTAVEIS = (
    ("canonical", "range_core.engine.loader.canonical", LOADER / "canonical.py"),
    ("loader", "range_core.engine.loader.pack_loader", LOADER / "pack_loader.py"),
)


MUTACOES: dict[str, tuple[list[Substituicao], set[str]]] = {
    # -----------------------------------------------------------------------
    # `t_relative` — o campo que o contrato deixa livre e o engine precisa
    # interpretar. Erro aqui nao falha: agenda na hora errada.
    # -----------------------------------------------------------------------
    "t_relative conta os minutos como segundos": (
        [
            (
                "loader",
                'return int(casado.group("horas")) * 3600 + int(casado.group("minutos")) * 60',
                'return int(casado.group("horas")) * 3600 + int(casado.group("minutos"))',
            )
        ],
        {"test_t_relative_vira_segundos"},
    ),
    # -----------------------------------------------------------------------
    # A FORMA CANONICA — as duas propriedades que o pino depende.
    # -----------------------------------------------------------------------
    "a forma canonica perde o prefixo de caminho": (
        [
            (
                "canonical",
                'digest.update(f"{caminho}\\n{corpo}\\n".encode("utf-8"))',
                'digest.update(f"{corpo}\\n".encode("utf-8"))',
            )
        ],
        {"test_o_MESMO_documento_sob_outro_nome_muda_o_hash"},
    ),
    "o escopo da forma canonica deixa de filtrar por `.yaml`": (
        [
            (
                "canonical",
                'arquivos.update(entrada for entrada in grupo if entrada.endswith(".yaml"))',
                "arquivos.update(grupo)",
            )
        ],
        {"test_GM_NOTES_fica_fora_do_hash"},
    ),
    "a serializacao canonica deixa de ordenar as chaves": (
        [("canonical", "            sort_keys=True,", "            sort_keys=False,")],
        {"test_a_ORDEM_das_chaves_no_arquivo_nao_muda_o_hash"},
    ),
    # -----------------------------------------------------------------------
    # O ESTADO TOTAL — `01` secao 5.4, e a razao de `SimulationState` nao ter
    # ausencia. Defaults vazios produzem projecao parcial, que e plausivel.
    # -----------------------------------------------------------------------
    "os defaults do adapter chegam vazios ao fold": (
        [
            (
                "loader",
                'return {nome: spec["default"] for nome, spec in self.specs.items()}',
                "return {}",
            )
        ],
        {"test_flag_defaults_traz_o_adapter_inteiro"},
    ),
    # -----------------------------------------------------------------------
    # ITEM 9 — o sitio proprio da flag nao declarada. Sem discriminante, a
    # mensagem que T2 exige poderia sair para qualquer violacao.
    # -----------------------------------------------------------------------
    "a flag nao declarada perde o sitio proprio": (
        [
            (
                "loader",
                "        if flags:\n",
                "        if False:\n",
            )
        ],
        {
            "test_impede_o_boot",
            "test_a_mensagem_nomeia_a_flag",
            "test_a_mensagem_nomeia_o_arquivo_esperado",
            "test_vale_para_required_flags_do_manifesto",
            "test_vale_para_effects_de_opcao_de_decisao",
        },
    ),
    # -----------------------------------------------------------------------
    # INJECT SEM EFFECTS PRECISA DE ENTRADA, e nao de ausencia: o fold levanta
    # `INJECT_NOT_IN_PACK` para inject fora do mapeamento, e o de ruido seria o
    # primeiro a derrubar a projecao ao ser disparado.
    # -----------------------------------------------------------------------
    "inject sem effects fica de fora do mapeamento": (
        [
            (
                "loader",
                "            inject_effects={inject.id: inject.effects for inject in injects},",
                "            inject_effects={i.id: i.effects for i in injects if i.effects},",
            )
        ],
        {"test_todo_inject_tem_entrada_em_inject_effects"},
    ),
}


ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTS_PATH, MUTACOES)


if __name__ == "__main__":
    unittest.main()
