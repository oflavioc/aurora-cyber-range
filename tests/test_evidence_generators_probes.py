"""Prova negativa das fontes reais: o que cada afirmacao da peca 3 custa.

R3 §5. As afirmacoes desta peca sao de tres naturezas, e cada uma tem um jeito
proprio de passar sem ser verdade:

    o gabarito DECLARA a fonte        — some o fato, e a fonte nao existe
    o gerador nao INVENTA             — um literal no texto, onde o oraculo de
                                        endereco nao olha
    o arquivo nao VAZA gabarito       — um campo a mais no registro

AS CINCO MUTACOES
==================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **a guarda de IOC volta ao conteudo inteiro** | `_achados_no_texto` -> `achados_no_valor` | item 5 |
| **o sufixo do link vira TLD roteavel** | `.example` -> um TLD real | `05` §2 |
| **o fato de phishing some** | a Linha A volta a tres fatos | `08` §3, `email.eml` |
| **o vendor do CEF vira literal** | sai a leitura do contrato | `05` §5.1, P1-13 |
| **`fact_id` entra no registro JSONL** | um campo a mais | `05` §6 |

A PRIMEIRA E A QUE ESTA PECA APRENDEU DOENDO
=============================================
`dados_sinteticos.achados_no_valor` opera sobre UM VALOR DE CAMPO: texto com
espaco no meio ele descarta e devolve lista vazia. A primeira versao da guarda
do motor o chamava sobre o **conteudo inteiro do arquivo**, e passava
vacuamente — `"visite https://<host roteavel>/login"` nao produzia achado
nenhum. A guarda parecia proteger e nao protegia.

Esta mutacao restaura o defeito exato. Ela existe porque a correcao (tokenizar
antes de julgar) e invisivel no verde: sem ela, nada distinguiria a guarda que
funciona da que nao funciona.

A QUINTA E A QUE UM REVISOR NAO VE
===================================
Acrescentar `fact_id` ao registro JSONL parece melhoria — rastreabilidade,
correlacao, depuracao. E e **gabarito indo para o participante** (`05` §6). O
arquivo continua valido, o parser continua lendo, e o exercicio fica arruinado
sem que nada quebre. E a razao de a amarracao fato -> fonte ser por CONTEUDO.

OS CONJUNTOS SAO MEDIDOS, NAO PREVISTOS.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECAO = REPO_ROOT / "range-core" / "evidence" / "projecao.py"
EMAIL = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "email.py"
CEF = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "cef.py"
JSONL = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "jsonl.py"
LINHA_A = REPO_ROOT / "domains" / "academus" / "seed" / "linha_a.py"
TESTES = REPO_ROOT / "tests" / "test_evidence_generators.py"

IDENTITY = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "identity_audit.py"
DATABASE = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "database_audit.py"
#: A CADEIA EM ORDEM DE DEPENDENCIA — e os dois ultimos entram SEM mutacao
#: propria, so para serem recarregados depois de `jsonl`.
#:
#: Medido: mutar `jsonl.py` ou `cef.py` sozinhos nao derrubava NADA. Duas causas
#: empilhadas, e as duas sao de INSTRUMENTO:
#:
#: 1. `identity_audit` e `database_audit` fazem `from ...jsonl import linhas` no
#:    topo, e guardam a funcao ORIGINAL. Recarrega-los depois de `jsonl` resolve
#:    — e a ordem de dependencia que o cabecalho do harness descreve, e a mesma
#:    razao pela qual `test_queda_de_sessao_probes.py` poe `app.py` na lista sem
#:    muta-lo;
#: 2. o `__init__` do pacote resolvia os submodulos por ATRIBUTO. Ele **nao pode
#:    entrar nesta lista**: o harness carrega o arquivo como modulo avulso, sem
#:    `__path__`, e `from <pacote> import cef` ali dentro falha. A saida foi do
#:    outro lado — `geradores()` passou a resolver por `import_module`, que
#:    consulta `sys.modules`. Ver o cabecalho do pacote.
#:
#: **Falha de instrumento lida como ausencia de deteccao** — a terceira
#: ocorrencia desta familia nesta fase, depois do `from ... import` da peca 1 e
#: do `achados_no_valor` sobre texto livre desta peca.
MUTAVEIS = (
    ("projecao", "range_core.evidence.projecao", PROJECAO),
    ("linha_a", "domains.academus.seed.linha_a", LINHA_A),
    ("email", "domains.academus.evidence_generators.email", EMAIL),
    ("cef", "domains.academus.evidence_generators.cef", CEF),
    ("jsonl", "domains.academus.evidence_generators.jsonl", JSONL),
    ("identity_audit", "domains.academus.evidence_generators.identity_audit", IDENTITY),
    ("database_audit", "domains.academus.evidence_generators.database_audit", DATABASE),
)

GUARDA_DE_IOC = "        achados = _achados_no_texto(conteudo)"

#: A linha ACOMPANHOU a peca 4: o phishing passou a projetar tambem em
#: `precursor` (duas fontes para o mesmo fato, o modelo de `08` §1). O harness
#: exige casamento EXATO e uma vez so — e por isso que um alvo desatualizado
#: quebra alto aqui em vez de plantar outra coisa em silencio.
PHISHING = '            "projections": ["email", "precursor"],'

REGISTRO = "        registro = {c: fato[c] for c in campos if c in fato}"

MUTACOES = {
    "a guarda de IOC volta a julgar o conteudo inteiro": (
        [("projecao", GUARDA_DE_IOC, "        achados = achados_no_valor(conteudo)")],
        {"test_o_motor_RECUSA_gerador_que_escreve_dominio_roteavel"},
    ),
    # FINA DE PROPOSITO, e a escolha tem historia. A primeira versao mutava o
    # SUFIXO para um TLD roteavel — e derrubava 20 dos 27 testes, porque a
    # guarda de IOC e falha fechada: um dominio roteavel em UMA fonte impede a
    # projecao INTEIRA. Isso e o comportamento certo do motor e a mutacao
    # errada: ela media a falha fechada, nao a derivacao.
    #
    # Esta mutacao mantem o sufixo reservado e troca so o HOST por um literal.
    # Nenhuma guarda dispara — nao e IP, e o sufixo e permitido —, e o que
    # sobra e exatamente a pergunta: o host do link deriva do elenco?
    #
    # Ela expos uma fraqueza REAL do gate: a primeira versao do caso so
    # verificava que o ator aparecia em algum lugar do `.eml`, e ele aparece no
    # `From:` de qualquer jeito. O caso foi reescrito para julgar o HOST da URL.
    "o host do link e escrito a mao": (
        [
            (
                "email",
                '                    f"Acesse: https://{host}/recadastro",',
                '                    "Acesse: https://portal-seguro.example/recadastro",',
            )
        ],
        {"test_o_dominio_do_link_DERIVA_de_entidade_do_elenco"},
    ),
    # MUTACAO GROSSA, E DECLARADA COMO TAL: sem a projecao, `email.eml` nao
    # existe, entao TODA a classe que o le cai junto. Nao da para torna-la mais
    # fina — e essa a consequencia real de um fato deixar de projetar, e e
    # exatamente o que `08` §2 chama de invisivel ao time azul.
    #
    # `test_a_tabela_cobre_TUDO_o_que_o_gabarito_declara` NAO acusa, e esta
    # certo: se o gabarito deixa de declarar `email`, a tabela continua
    # cobrindo tudo o que ele declara. Aquele teste julga a conjuncao, nao a
    # presenca da fonte.
    "o fato de phishing perde a projecao em email": (
        [("linha_a", PHISHING, '            "projections": [],')],
        {
            "test_a_linha_A_tem_fato_de_PHISHING_projetado_em_email",
            "test_tem_os_cabecalhos_de_RFC_5322",
            "test_NAO_tem_anexo",
            "test_NAO_e_multipart",
            "test_o_link_aponta_para_SUFIXO_RESERVADO_a_documentacao",
            "test_o_dominio_do_link_DERIVA_de_entidade_do_elenco",
        },
    ),
    "o vendor do CEF vira literal no modulo": (
        [
            (
                "cef",
                "                    _escapar(vendor),",
                '                    "AuroraSec",',
            )
        ],
        {"test_o_vendor_e_o_product_vem_do_CONTRATO"},
    ),
    "o fact_id entra no registro JSONL": (
        [
            (
                "jsonl",
                REGISTRO,
                "        registro = {c: fato[c] for c in campos if c in fato}\n"
                '        registro["fact_id"] = fato.get("fact_id")',
            )
        ],
        {"test_NENHUMA_fonte_carrega_o_fact_id"},
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
