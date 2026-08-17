"""Prova negativa da P3-10: as tres propriedades ficam vermelhas com mutacao plantada.

A D9 lista quatro propriedades, e tres delas sao afirmacoes que um teste
distraido concede de graca. Aqui cada uma tem uma mutacao que a quebra **sem
quebrar as outras** — e o conjunto vermelho de cada uma esta declarado.

AS TRES MUTACOES, E A PROPRIEDADE QUE CADA UMA ATACA
------------------------------------------------------
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **o acumulador volta** | a `Cota` da Fase 3, reescrita dentro de `cai` | estavel no rollback, e monotona |
| **`hash()` no lugar de `derive_seed`** | a armadilha que `determinism.py` documenta | estavel no reinicio |
| **o sujeito sai da derivacao** | so rota e flag decidem | a fracao, e o par que discrimina |

A SEGUNDA E A QUE JUSTIFICA UM SUBPROCESSO NA SUITE
-----------------------------------------------------
`hash()` de string e salgado por `PYTHONHASHSEED` e e **estavel dentro de um
processo**. Uma suite inteira escrita no mesmo interpretador ficaria verde com
ela, e o defeito apareceria como *"o conjunto de participantes fora do ar mudou
depois do reinicio do container"* — no dia do exercicio.

Se essa mutacao derrubasse mais de um teste, o subprocesso seria redundante. Ela
derruba exatamente um, e e por isso que ele existe.

O CONJUNTO VERMELHO E MEDIDO, E TRES COISAS APARECERAM SO RODANDO
-------------------------------------------------------------------
**1. `test_a_FRACAO_observada_segue_a_taxa` nao acusa o acumulador**, e esta
certo: a cota dava `floor(n*taxa)` recusas exatas, entao a fracao era a
declarada. O que ela nao dava era o mesmo CONJUNTO. Uma suite que so contasse
quantos caem teria aprovado a implementacao que a P3-10 existe para remover — e
essa e a razao de as assercoes deste conjunto serem sobre conjuntos.

**2. `test_os_extremos_sao_exatos` tambem nao acusa**, e tambem esta certo: com
taxa 1 o acumulador vence sempre, e com taxa 0 ele nao vence nunca. Os extremos
sao justamente onde as duas implementacoes coincidem.

**3. O acumulador derruba `test_ESTAVEL_NO_REINICIO`, e eu nao previa.** Ele e
estado de MODULO, entao o que a classe anterior deixou nele atravessa para a
seguinte: o pai calcula com o contador sujo e o filho, num processo novo,
calcula com ele zerado. E a propriedade "estavel no reinicio" sendo violada pelo
mecanismo mais literal possivel — e foi a execucao que mostrou, nao o
raciocinio.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

from _academus_banco import exige_banco

REPO_ROOT = Path(__file__).resolve().parent.parent
DEGRADACAO = REPO_ROOT / "domains" / "academus" / "api" / "degradacao.py"
TESTES = REPO_ROOT / "tests" / "test_queda_de_sessao.py"

APP = REPO_ROOT / "domains" / "academus" / "api" / "app.py"

#: `app.py` ENTRA SEM MUTACAO, e a razao e um defeito de INSTRUMENTO que a
#: primeira execucao mostrou: as tres mutacoes derrubavam
#: `test_montar_com_flag_ausente_RECUSA`, e nenhuma delas tem nada a ver com a
#: guarda de boot.
#:
#: O modulo mutado define uma classe `FlagNaoDeclarada` NOVA. `app.py`, ja
#: importado, seguia levantando a ORIGINAL, e o `assertRaises` do teste — que
#: resolve pelo modulo mutado — nao a reconhecia. Falha do instrumento lida como
#: deteccao, que e exatamente o que uma prova negativa nao pode ter.
#:
#: Recarregar `app.py` junto faz o `import` dele resolver para o modulo mutado, e
#: as duas pontas voltam a falar da mesma classe. E a ordem de dependencia que o
#: cabecalho do harness descreve, usada para o que ela existe.
MUTAVEIS = (
    ("degradacao", "domains.academus.api.degradacao", DEGRADACAO),
    ("app", "domains.academus.api.app", APP),
)

CORTE = "    return fracao_do_sujeito(seed, rota, flag, sujeito) < taxa"
DERIVACAO = 'return derive_seed(seed, f"{rota}|{flag}|{sujeito}") / ESPACO'

ACUMULADOR = (
    "    chave = (rota, flag)\n"
    "    total = _ACUMULADO.get(chave, 0.0) + taxa\n"
    "    if total >= 1.0:\n"
    "        _ACUMULADO[chave] = total - 1.0\n"
    "        return True\n"
    "    _ACUMULADO[chave] = total\n"
    "    return False"
)

MUTACOES = {
    "o acumulador da Fase 3 volta": (
        [
            ("degradacao", "ESPACO = 2**64", "ESPACO = 2**64\n\n_ACUMULADO: dict = {}"),
            ("degradacao", CORTE, ACUMULADOR),
        ],
        {
            "test_MONOTONA_subir_a_taxa_so_acrescenta",
            "test_ESTAVEL_NO_REINICIO_processo_novo_produz_o_mesmo_conjunto",
            "test_rebobinar_devolve_EXATAMENTE_as_mesmas_sessoes",
            "test_a_ordem_das_requisicoes_nao_muda_quem_cai",
        },
    ),
    "hash() no lugar de derive_seed": (
        [
            (
                "degradacao",
                DERIVACAO,
                'return (hash(f"{seed}|{rota}|{flag}|{sujeito}") % ESPACO) / ESPACO',
            )
        ],
        {"test_ESTAVEL_NO_REINICIO_processo_novo_produz_o_mesmo_conjunto"},
    ),
    "o sujeito sai da derivacao": (
        [("degradacao", DERIVACAO, 'return derive_seed(seed, f"{rota}|{flag}") / ESPACO')],
        {
            "test_a_FRACAO_observada_segue_a_taxa",
            "test_ESTAVEL_NO_REINICIO_processo_novo_produz_o_mesmo_conjunto",
            "test_flags_e_rotas_diferentes_nao_derrubam_o_MESMO_conjunto",
            "test_a_ordem_das_requisicoes_nao_muda_quem_cai",
        },
    ),
}

ProvaNegativa = exige_banco(caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES))


if __name__ == "__main__":
    import unittest

    unittest.main()
