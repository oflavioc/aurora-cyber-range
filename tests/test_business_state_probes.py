"""Prova negativa da P3-5: a suite fica vermelha com o estado de volta em memoria.

Suite que nunca ficou vermelha prova que roda, e nao que detecta — a doutrina
que a Fase 0 fixou e que o `tests/mutation_harness.py` aplica desde a Fase 2.

AS DUAS MUTACOES, E POR QUE SAO ESTAS DUAS
--------------------------------------------
A pendencia fala de business state em **dicionario de modulo**, e e essa a
primeira. A segunda e o vizinho dela e passaria despercebida por qualquer teste
que rodasse na mesma sessao: escrever no banco e **nao commitar**. As duas
produzem o mesmo sintoma para quem esta dentro do processo — o objeto existe, a
resposta e 201 — e sintomas opostos para quem esta fora.

E por isso que as duas so sao pegas por um INTERPRETADOR NOVO, e por isso que o
teste central deste conjunto e um `subprocess`.

O CONJUNTO VERMELHO E MEDIDO, E NAO PREVISTO
----------------------------------------------
Cada mutacao declara o conjunto EXATO de testes que deve acusar. Conjunto maior
significa mutacao grossa; menor denuncia teste que nao prova o que diz. Os
valores abaixo foram obtidos rodando, e nao raciocinando — inclusive o que
surpreende: a mutacao do dicionario **nao** derruba `test_P4_5...` nem
`test_a_resposta_nao_carrega_a_chave_substituta`, porque os dois olham o que a
rota DEVOLVE, e a rota devolve certo. Eles medem outra coisa, e esta certo que
nao acusem.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

from _academus_banco import exige_banco

REPO_ROOT = Path(__file__).resolve().parent.parent
REPOSITORIO = REPO_ROOT / "domains" / "academus" / "api" / "repositorio.py"
TESTES = REPO_ROOT / "tests" / "test_business_state_postgres.py"

MUTAVEIS = (("repositorio", "domains.academus.api.repositorio", REPOSITORIO),)

#: A ancora do acumulador em memoria. `class Repositorio:` ocorre uma vez, e a
#: guarda de `fonte_mutada` reprova alto se isso deixar de ser verdade.
CABECA = "class Repositorio:"

MUTACOES = {
    "a nota volta para um dicionario de modulo": (
        [
            (
                "repositorio",
                CABECA,
                "_NOTAS_EM_MEMORIA: list = []\n\n\n" + CABECA,
            ),
            (
                "repositorio",
                "            registro = Grade(student_id=student_id, class_id=class_id, value=value)\n"
                "            sessao.add(registro)",
                "            registro = Grade(student_id=student_id, class_id=class_id, value=value)\n"
                "            _NOTAS_EM_MEMORIA.append(registro)",
            ),
        ],
        {
            "test_a_nota_lancada_pela_rota_e_lida_por_OUTRO_PROCESSO",
            "test_o_diario_sai_em_ordem_estavel",
        },
    ),
    "a matricula e escrita e NAO commitada": (
        [
            (
                "repositorio",
                "            registro = Enrollment(student_id=student_id, class_id=class_id)\n"
                "            sessao.add(registro)\n"
                "            sessao.commit()",
                "            registro = Enrollment(student_id=student_id, class_id=class_id)\n"
                "            sessao.add(registro)\n"
                "            sessao.flush()",
            )
        ],
        {"test_a_matricula_feita_pela_rota_e_lida_por_OUTRO_PROCESSO"},
    ),
}

ProvaNegativa = exige_banco(caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES))


if __name__ == "__main__":
    import unittest

    unittest.main()
