"""Prova negativa do motor: a porta do item 1 fica vermelha com defeito plantado.

R3 §5. O motor e uma funcao curta que orquestra tres decisoes, e as tres sao do
tipo que um gate distraido concede: *"filtrei os fatos certos"*, *"pus o
banner"*, *"recusei a invencao"*. Cada mutacao ataca uma.

AS NOVE MUTACOES
=================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **a recusa vira aviso** | sai o `raise EntidadeInventada` | a porta do item 1 |
| **o gerador recebe TODOS os fatos** | some o filtro por cobertura | fato invisivel nao projeta |
| **o banner some** | o conteudo passa a ser so o corpo | `05` §4, primeira linha |
| **a fonte ausente passa** | sai o `raise GeradorAusente` | falha fechada |
| **a guarda de veredito nao encontra nada** | `_ocorre` devolve `False` | `00` §3, B1 da 2a auditoria |
| **o NOME do campo sai da busca** | so os valores ficam guardados | `05` §6, o campo vazio que afirma |
| **a recusa de host inventado vira aviso** | `hosts_inventados` devolve `[]` | item 1, M2 da 2a auditoria |
| **a normalizacao de rotulo some** | `_` deixa de virar `-` | o falso POSITIVO do mesmo gate |
| **o manifesto declara todos os fatos** | `projects_facts` vira o elenco inteiro | cobertura de `08` §7 |

A QUINTA E A SEXTA SAO A CAMADA, E NAO A SEGURANCA
===================================================
`credential_state` valia `compromised` no fato real, e tres fontes o
escreviam. Nao e IOC, nao e dado real, nenhum verificador de `05` reclamaria —
e mesmo assim arruina o exercicio, porque a segunda linha do `vpn.log` entrega
a conclusao que o proprio fato manda correlacionar. Um gate contra isso nao
tem como ser derivado de norma de seguranca: ele vem de `00` §3, e e por isso
que a particao mora no contrato e nao numa lista no motor.

A OITAVA E O DEFEITO ESPELHADO, e ela existe porque gate que atrapalha morre.
Se a normalizacao `_` -> `-` sumir, `svc_academus` nunca casa `svc-academus` e
o oraculo passa a acusar a unica derivacao CORRETA. Falso positivo nao e um
gate mais rigoroso — e um gate que sera desligado (R10 §2).

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
ELENCO = REPO_ROOT / "range-core" / "evidence" / "elenco.py"
PROJECAO = REPO_ROOT / "range-core" / "evidence" / "projecao.py"
MANIFESTO = REPO_ROOT / "range-core" / "evidence" / "manifesto.py"
TESTES = REPO_ROOT / "tests" / "test_evidence_projecao.py"

#: `elenco` ANTES de `projecao` — ordem de dependencia: `projecao.py` importa as
#: funcoes do elenco no topo e guarda as ORIGINAIS.
MUTAVEIS = (
    ("elenco", "range_core.evidence.elenco", ELENCO),
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

#: A PORTA DO B1. Mutar `_ocorre` para `False` desliga a guarda inteira sem
#: mudar mais nada — e a forma mais limpa de perguntar "o que este gate custa?".
OCORRE = '    return re.search(rf"(?<![\\w.-]){re.escape(agulha)}(?![\\w.-])", conteudo) is not None'

#: O NOME DO CAMPO saindo da busca. Mais fina que a acima: os VALORES continuam
#: guardados, e o que se perde e so a chave escrita no registro JSONL.
NOME_DO_CAMPO = "        agulhas.append((campo, campo))"

#: A PORTA DO M2 — a segunda forma fechada do oraculo.
RECUSA_DE_HOST = "        hosts = hosts_inventados(conteudo, elenco)"

#: A NORMALIZACAO de rotulo de host. Sem ela, `svc_academus` nunca casa
#: `svc-academus` e a derivacao legitima passa a ser acusada — o falso POSITIVO,
#: que e o outro jeito de um gate deixar de servir.
ROTULOS = '        return frozenset(v.replace("_", "-").lower() for v in self.todos)'

#: A PORTA DO B1 DA 3a AUDITORIA — a fonte que entrega a resposta.
RECUSA_DE_RESPOSTA = "        classe = _entrega_a_resposta(da_fonte, casos)"

#: O JULGAMENTO POR ESPECIE. Trocar o subconjunto por igualdade sobre a fonte
#: INTEIRA e o defeito espelhado: `exfiltration` na mesma fonte passaria a
#: diluir `grade_change_retroactive`, e o vazamento voltaria com cara de
#: populacao mista.
POR_CLASSE = "        if set(ids) <= casos:"

#: O BANNER DO MANIFESTO — L2 da 3a auditoria.
BANNER_DO_MANIFESTO = '        "_banner": banner,'

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
    # AS QUATRO DA SEGUNDA AUDITORIA. As duas primeiras sao o B1 — a guarda que
    # impede o veredito do gabarito de ir para o fio —, e as duas ultimas sao o
    # M2, o oraculo de hostname.
    "a guarda de veredito nunca encontra nada": (
        [("projecao", OCORRE, "    return False")],
        {
            "test_gerador_que_escreve_o_VEREDITO_do_gabarito_e_recusado",
            "test_gerador_que_escreve_a_CLASSE_do_fato_e_recusado",
            "test_gerador_que_carimba_o_FACT_ID_e_recusado",
            "test_a_CHAVE_do_campo_de_gabarito_tambem_e_recusada",
            "test_a_guarda_alcanca_valor_COM_ESPACO_dentro_de_mapa",
        },
    ),
    "o NOME do campo de gabarito sai da busca": (
        [("projecao", NOME_DO_CAMPO, "        pass")],
        {"test_a_CHAVE_do_campo_de_gabarito_tambem_e_recusada"},
    ),
    "a recusa de host inventado vira aviso": (
        [("projecao", RECUSA_DE_HOST, "        hosts = []")],
        {"test_gerador_que_INVENTA_host_e_recusado"},
    ),
    # O FALSO POSITIVO, que e o defeito espelhado. Um gate que recusa o unico
    # jeito CORRETO de derivar o host seria abandonado na primeira vez que
    # atrapalhasse — e gate abandonado nao guarda nada (R10 §2).
    "a normalizacao de rotulo de host some": (
        [("elenco", ROTULOS, "        return frozenset(self.todos)")],
        {"test_o_host_DERIVADO_do_elenco_passa"},
    ),
    "a fonte que entrega a resposta passa em silencio": (
        [("projecao", RECUSA_DE_RESPOSTA, "        classe = None")],
        {"test_a_fonte_que_projeta_SO_CASO_e_recusada"},
    ),
    # O DEFEITO ESPELHADO da mesma guarda: julgar a fonte inteira em vez da
    # especie. Ele nao produz falso positivo — produz falso NEGATIVO, porque
    # qualquer fato de outra especie na mesma fonte passa a diluir o vazamento.
    "a guarda de resposta julga a fonte inteira, e nao a especie": (
        [
            (
                "projecao",
                POR_CLASSE,
                "        if set(ids) <= casos and len(por_classe) == 1:",
            )
        ],
        {"test_a_fonte_que_projeta_SO_CASO_e_recusada"},
    ),
    "o manifesto nasce sem banner": (
        [("manifesto", BANNER_DO_MANIFESTO, '        "_banner": "",')],
        {
            "test_o_manifesto_CARREGA_o_banner",
            # ACUSA TAMBEM, e nao esta sobrando: `_banner` e `required` com
            # `minLength: 1` no contrato, entao banner vazio e manifesto
            # INVALIDO — a regra morde nas duas camadas.
            "test_o_manifesto_VALIDA_contra_o_contrato_real",
        },
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
