"""Prova negativa do gabarito: as tres reversoes que o H1 da 5a auditoria nomeou.

R3 §5. Este arquivo existe por um motivo especifico e vale dize-lo: a Fase 9
levou tres rodadas de auditoria para a Linha B ficar certa, e na quarta ela
ficou certa **sem gate**. O laudo da quinta listou as tres reversoes que a
suite de 1139 testes nao veria, e este arquivo e a resposta a essa lista.

AS QUATRO MUTACOES
===================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **a ordem por instante some** | sai o `fatos.sort` | a POSICAO no arquivo entrega a particao |
| **o laco volta aos conjuntos de caso** | `linha_b.CONJUNTOS` -> `CONJUNTOS_DE_CASO` | `08` §3, e o B1 da 3a auditoria |
| **a projecao some** | sai `projections` do fato | `08` §3: a Linha B sai de toda fonte |
| **a especie volta a ser fixa** | `CLASSE_POR_JANELA[...]` -> literal | `00` §3, M1 da 5a auditoria |

A PRIMEIRA E A QUE DEFINE ESTE ARQUIVO
=======================================
`RespostaEntregue` julga PERTINENCIA por especie: ela pergunta *"nesta fonte,
dentro desta especie, tudo e caso?"*. Com a populacao inteira a resposta e nao, e
a guarda cala — corretamente. Mas ela **nao enxerga ordem**, e o gabarito agrupa
por conjunto: sem o `sort`, as 22 primeiras linhas do arquivo sao os indevidos
comprovados, as 11 seguintes os ambiguos, e a defensibilidade sai de graca na
posicao.

E a variante POR POSICAO do mesmo BLOCKER da 3a rodada. O codigo que a impede e
uma linha; o que faltava era a prova de que ela morde.

A SEGUNDA E A QUE A SUITE NAO PODIA VER
========================================
Voltar o laco a `CONJUNTOS_DE_CASO` reproduz o `cb8d123` — e a suite estava
VERDE naquele commit. Nada em `tests/` projetava o gabarito real, entao a unica
coisa que pegaria seria um `evidence build` sobre o pack, que a suite nao roda.

O MOTOR DE MENTIRA E O QUE TORNA ISTO POSSIVEL SEM BANCO. `gabarito.gerar` LE a
trilha, e as quatro propriedades sao funcao das LINHAS. A classe com banco
(`OArtefatoEhProduzidoEJulgado`) pula sem Postgres, e foi para dentro daquele
pulo que o H1 caiu.

OS CONJUNTOS SAO MEDIDOS, NAO PREVISTOS.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
GABARITO = REPO_ROOT / "domains" / "academus" / "seed" / "gabarito.py"
#: O ALVO E A SUITE SEM BANCO, e a escolha e limite de instrumento resolvido no
#: lugar certo. `test_gabarito.py` tem classe que exige Postgres e chama
#: `gabarito.gerar`, que renderiza o `GM_NOTES.md` de um template IRMAO — e o
#: harness carrega o modulo de um temporario, onde o template nao existe.
#:
#: Medido: com o alvo em `test_gabarito.py`, a ancora reprovava SO COM O BANCO NO
#: AR (1147 OK sem Postgres, 5 falhas com ele). Instrumento que muda de veredito
#: com o ambiente e pior que um que reprova sempre.
TESTES = REPO_ROOT / "tests" / "test_gabarito_linha_b.py"

MUTAVEIS = (("gabarito", "domains.academus.seed.gabarito", GABARITO),)

ORDENACAO = '    fatos.sort(key=lambda f: (f["exercise_time"], f["fact_id"]))'

LACO_DOS_SEIS = "    for nome in linha_b.CONJUNTOS:"

PROJECAO = '                    "projections": ["database_audit"],'

ESPECIE = '                    "fact_class": CLASSE_POR_JANELA[bool(na_janela)],'

MUTACOES = {
    "a ordem por instante some": (
        [("gabarito", ORDENACAO, "    pass")],
        {
            "test_os_fatos_saem_ORDENADOS_POR_INSTANTE",
            # A ANTI-VACUIDADE ACUSA JUNTO, e e por isso que ela existe: a
            # fixture embaralha os instantes, entao sem o `sort` a primeira
            # linha do arquivo volta a ser um indevido comprovado.
            "test_a_ordem_por_instante_MISTURA_os_conjuntos",
        },
    ),
    "o laco de fatos volta aos conjuntos de CASO": (
        [("gabarito", LACO_DOS_SEIS, "    for nome, _ in CONJUNTOS_DE_CASO:")],
        {
            "test_os_SEIS_conjuntos_viram_fato",
            # OS OUTROS TRES ACUSAM, e as tres deteccoes sao legitimas: sem os
            # conjuntos de nao-caso, todo fato passa a ser caso (o par), a
            # primeira linha volta a ser um indevido (a ordem), e nao sobra
            # nenhuma linha DENTRO da janela para a especie discriminar.
            "test_so_os_TRES_conjuntos_de_caso_viram_caso",
            "test_a_ordem_por_instante_MISTURA_os_conjuntos",
            "test_a_ESPECIE_sai_da_janela_de_retificacao",
        },
    ),
    "a projecao em database_audit some do fato": (
        [("gabarito", PROJECAO, "")],
        {"test_TODA_linha_declara_a_projecao_em_database_audit"},
    ),
    "a especie volta a ser fixa, ignorando a janela": (
        [("gabarito", ESPECIE, '                    "fact_class": "grade_change_retroactive",')],
        {"test_a_ESPECIE_sai_da_janela_de_retificacao"},
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
