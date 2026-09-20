"""Prova negativa do motor: a porta do item 1 fica vermelha com defeito plantado.

R3 §5. O motor e uma funcao curta que orquestra tres decisoes, e as tres sao do
tipo que um gate distraido concede: *"filtrei os fatos certos"*, *"pus o
banner"*, *"recusei a invencao"*. Cada mutacao ataca uma.

AS CINCO MUTACOES
==================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **a recusa vira aviso** | sai o `raise EntidadeInventada` | a porta do item 1 |
| **o gerador recebe TODOS os fatos** | some o filtro por cobertura | fato invisivel nao projeta |
| **o banner some** | o conteudo passa a ser so o corpo | `05` §4, primeira linha |
| **a fonte ausente passa** | sai o `raise GeradorAusente` | falha fechada |
| **o manifesto declara todos os fatos** | `projects_facts` vira o elenco inteiro | cobertura de `08` §7 |

A PRIMEIRA E A QUE DEFINE A PECA
=================================
Sem o `raise`, `projetar()` volta a ser o que a peca 1 ja era: um lugar que SABE
que houve invencao e deixa passar. `08` §1 afirma que contradicao entre fontes e
*estruturalmente impossivel* — e uma afirmacao dessas so e verdadeira enquanto
existir quem a imponha. A mutacao mede exatamente isso.

A QUINTA ATRAVESSA DOIS MODULOS, e e a unica assim
===================================================
`projects_facts` nasce em `projecao.py` e e copiado por `manifesto.py`. Mutar o
manifesto para declarar fatos que a fonte nao projeta e o defeito que `08` §7
existe para impedir — o manifesto e o que o `evidence verify` confere, entao um
manifesto generoso faz o verificador aprovar cobertura que nao existe.

OS CONJUNTOS SAO MEDIDOS, NAO PREVISTOS — e a segunda mutacao desmentiu TRES
previsoes de uma vez. Cada uma ensina algo sobre a suite:

**1. Os dois testes de invencao NAO acusam** o gerador recebendo todos os fatos,
e esta certo: o duble que inventa levanta `EntidadeInventada` de qualquer jeito,
com dois fatos ou com tres. A mutacao nao alcanca o caminho deles.

**2. `test_ground_truth_sem_fato_visivel_nao_projeta_nada` NAO acusa**, e a
razao e estrutural: com um ground truth so de fato invisivel, a cobertura e
vazia e `projetar()` devolve `[]` **antes** de chegar ao filtro. A guarda
`if not cobertura: return []` protege aquele caminho da mutacao — o que revela
que aquele teste julga a guarda, e nao o filtro.

**3. `test_os_fatos_chegam_em_ordem_ESTAVEL` acusa**, e eu nao previa. Ele fixa
a lista exata que o gerador recebe, entao qualquer coisa que mude o conjunto o
derruba — inclusive uma mutacao cujo assunto e outro. Deteccao legitima, e sinal
de que aquele teste e mais forte do que o nome sugere.

O IMPORT DA SUITE ALVO E POR `sys.modules`, que e a condicao de funcionamento
desta prova (§2.4 do registro da fase, e o cabecalho de
`test_evidence_elenco_probes.py`).
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECAO = REPO_ROOT / "range-core" / "evidence" / "projecao.py"
MANIFESTO = REPO_ROOT / "range-core" / "evidence" / "manifesto.py"
TESTES = REPO_ROOT / "tests" / "test_evidence_projecao.py"

MUTAVEIS = (
    ("projecao", "range_core.evidence.projecao", PROJECAO),
    ("manifesto", "range_core.evidence.manifesto", MANIFESTO),
)

RECUSA = """        inventadas = sorted(enderecos_no(conteudo) - elenco.enderecos)
        if inventadas:
            raise EntidadeInventada("""

RECUSA_MUTADA = """        inventadas = []
        if inventadas:
            raise EntidadeInventada("""

FILTRO = (
    "        da_fonte = [f for f in ordem_do_documento "
    "if f.get(\"fact_id\") in cobertura[fonte]]"
)

BANNER_NO_CONTEUDO = '        conteudo = _banner.linha(formato, banner) + "\\n" + corpo'

GUARDA_DE_GERADOR = """    faltando = sorted(set(cobertura) - set(geradores))
    if faltando:"""

PROJECTS_FACTS = '            "projects_facts": list(fonte.projects_facts),'

MUTACOES = {
    "a recusa de invencao vira aviso": (
        [("projecao", RECUSA, RECUSA_MUTADA)],
        {
            "test_gerador_que_INVENTA_endereco_e_recusado",
            "test_a_recusa_NOMEIA_a_fonte_CERTA",
        },
    ),
    "o gerador recebe TODOS os fatos do documento": (
        [("projecao", FILTRO, "        da_fonte = list(ordem_do_documento)")],
        {
            "test_cada_gerador_recebe_APENAS_os_fatos_da_sua_fonte",
            "test_fato_SEM_projections_nao_chega_a_gerador_nenhum",
            "test_cada_fonte_declara_os_fact_id_que_projeta",
            "test_o_manifesto_NAO_carrega_fato_que_nao_projeta",
            "test_os_fatos_chegam_em_ordem_ESTAVEL",
        },
    ),
    "o banner some do conteudo": (
        [("projecao", BANNER_NO_CONTEUDO, "        conteudo = corpo")],
        {"test_o_banner_e_a_primeira_linha_de_TODA_fonte"},
    ),
    "a fonte sem gerador passa em silencio": (
        [
            (
                "projecao",
                GUARDA_DE_GERADOR,
                "    faltando = []\n    if faltando:",
            )
        ],
        {"test_gerador_AUSENTE_para_fonte_da_cobertura_e_recusado_nomeando_a_fonte"},
    ),
    "o manifesto declara fato que a fonte nao projeta": (
        [
            (
                "manifesto",
                PROJECTS_FACTS,
                '            "projects_facts": sorted(\n'
                "                {f for s in fontes for f in s.projects_facts}\n"
                "            ),",
            )
        ],
        {"test_cada_fonte_declara_os_fact_id_que_projeta"},
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
