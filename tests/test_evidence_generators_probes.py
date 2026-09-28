"""Prova negativa das fontes reais: o que cada afirmacao da peca 3 custa.

R3 §5. As afirmacoes desta peca sao de tres naturezas, e cada uma tem um jeito
proprio de passar sem ser verdade:

    o gabarito DECLARA a fonte        — some o fato, e a fonte nao existe
    o gerador nao INVENTA             — um literal no texto, onde o oraculo de
                                        endereco nao olha
    o arquivo nao VAZA gabarito       — um campo a mais no registro

AS SEIS MUTACOES
=================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **a guarda de IOC volta ao conteudo inteiro** | `_achados_no_texto` -> `achados_no_valor` | item 5 |
| **a tokenizacao nao corta no `=`** | o separador do syslog some | item 5, M1 da 1a auditoria |
| **a tokenizacao nao corta no `\\|`** | o separador do CEF some | item 5, achado na correcao do H1 |
| **o host do link e escrito a mao** | um rotulo literal no `.eml` | item 1, M2 da 2a auditoria |
| **o fato de phishing some** | a Linha A volta a tres fatos | `08` §3, `email.eml` |
| **o vendor do CEF vira literal** | sai a leitura do contrato | `05` §5.1, P1-13 |
| **`fact_id` entra no registro JSONL** | um campo a mais | `05` §6, B1 da 2a auditoria |

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
ELENCO = REPO_ROOT / "range-core" / "evidence" / "elenco.py"
PROJECAO = REPO_ROOT / "range-core" / "evidence" / "projecao.py"
CEF_DE_FIO = REPO_ROOT / "range-core" / "telemetry" / "cef.py"
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
    # `elenco` ANTES de `projecao`, e a ordem e a da dependencia: `projecao.py`
    # faz `from range_core.evidence.elenco import ...` no topo e guarda as
    # funcoes ORIGINAIS. Recarrega-lo depois e o que faz a mutacao chegar.
    ("elenco", "range_core.evidence.elenco", ELENCO),
    ("projecao", "range_core.evidence.projecao", PROJECAO),
    ("cef_de_fio", "range_core.telemetry.cef", CEF_DE_FIO),
    ("linha_a", "domains.academus.seed.linha_a", LINHA_A),
    ("email", "domains.academus.evidence_generators.email", EMAIL),
    ("cef", "domains.academus.evidence_generators.cef", CEF),
    ("jsonl", "domains.academus.evidence_generators.jsonl", JSONL),
    ("identity_audit", "domains.academus.evidence_generators.identity_audit", IDENTITY),
    ("database_audit", "domains.academus.evidence_generators.database_audit", DATABASE),
)

GUARDA_DE_IOC = "        achados = _achados_no_texto(conteudo)"

#: TRIPLE-QUOTED, e nao aspas simples: a linha alvo tem `"` escapado E `'` cru,
#: e qualquer um dos dois delimitadores exigiria escape que muda os bytes — o
#: harness casa TEXTO, entao o alvo tem de ser byte a byte o que esta no
#: arquivo. A primeira tentativa errou aqui e o harness quebrou alto ("casou 0"),
#: que e o comportamento certo.
#:
#: O ALVO MUDOU DE ARQUIVO na correcao do M2: o tokenizador saiu de `projecao.py`
#: e virou `elenco.tokens_no`, porque o oraculo de hostname passou a precisar
#: dele — R9 §8, um helper por semantica.
TOKEN = r'''_TOKEN = re.compile(r"[^\s\"'<>()\[\],;=|]+")'''
TOKEN_SEM_IGUAL = r'''_TOKEN = re.compile(r"[^\s\"'<>()\[\],;|]+")'''
TOKEN_SEM_PIPE = r'''_TOKEN = re.compile(r"[^\s\"'<>()\[\],;=]+")'''

#: A linha ACOMPANHOU a peca 4: o phishing passou a projetar tambem em
#: `precursor` (duas fontes para o mesmo fato, o modelo de `08` §1). O harness
#: exige casamento EXATO e uma vez so — e por isso que um alvo desatualizado
#: quebra alto aqui em vez de plantar outra coisa em silencio.
PHISHING = '            "projections": ["email", "precursor"],'

REGISTRO = "        registro = {c: fato[c] for c in campos if c in fato}"

#: O `actor` saindo de `database_audit` — M2 da quarta auditoria. A fonte
#: carrega `actor` e `source_ip`, e ficava FORA da comparacao de consistencia
#: mutua de `06` T13: os dois unicos casos que a leem olham `records_affected` e
#: a CHAVE `exercise_time`. Um `CAMPOS` sem `actor` nao era alcancado.
CAMPOS_DO_DATABASE = (
    '    "exercise_time",\n    "actor",\n    "action",\n    "source_ip",\n'
    '    "dest",\n    "records_affected",\n)'
)

#: TODA A SUITE QUE LE ARQUIVO PROJETADO, e ela e o conjunto vermelho de duas
#: mutacoes desta tabela. A grossura nao e preguica de mutante — e a **falha
#: fechada do motor**, medida: desde a correcao do B1 e do M2, tanto o `fact_id`
#: num registro quanto um host escrito a mao sao recusa de `projetar`, e recusa
#: derruba a projecao INTEIRA, nao a fonte onde o defeito esta.
#:
#: E o comportamento certo. Um pacote escrito pela metade seria pior que nenhum:
#: o facilitador teria arquivos coerentes ao lado de arquivos que nao existem. O
#: custo e este conjunto; a alternativa seria um motor que escreve o que sabe
#: estar errado.
#:
#: Fica declarado UMA vez, e nao copiado nas duas mutacoes: duas listas de 28
#: nomes divergiriam na primeira suite nova, e a divergencia apareceria como
#: "mutante nao mata" numa delas so.
TUDO_QUE_PROJETA = {
    "test_NAO_e_multipart",
    "test_NAO_tem_anexo",
    "test_NENHUMA_fonte_carrega_o_fact_id",
    "test_a_assinatura_NAO_e_a_classe_do_fato",
    "test_a_severidade_e_do_TIPO_DE_SINAL_e_nao_do_caso",
    "test_duas_projecoes_do_mesmo_ground_truth_sao_IDENTICAS",
    "test_fato_projetado_em_cef_SEM_assinatura_e_recusado",
    "test_nenhum_gerador_inventa_ENDERECO_NEM_HOST",
    "test_nenhuma_fonte_tem_achado_de_dado_nao_sintetico",
    "test_o_cabecalho_tem_os_sete_campos_do_formato",
    "test_o_database_audit_traz_o_volume_da_leitura_em_massa",
    "test_o_dominio_do_link_DERIVA_de_entidade_do_elenco",
    "test_o_identity_audit_e_JSONL_valido_com_um_objeto_por_fato",
    "test_o_link_aponta_para_SUFIXO_RESERVADO_a_documentacao",
    "test_o_mesmo_fato_aparece_no_CEF_e_na_outra_fonte_dele",
    "test_o_motor_RECUSA_IOC_na_forma_CHAVE_VALOR_de_log",
    "test_o_motor_RECUSA_IOC_no_CABECALHO_CEF",
    "test_o_motor_RECUSA_gerador_que_escreve_dominio_roteavel",
    "test_o_par_positivo_os_geradores_reais_passam",
    "test_o_precursor_NAO_atribui_ator",
    "test_o_vendor_e_o_product_vem_do_CONTRATO",
    "test_o_vpn_log_traz_usuario_endereco_e_a_ausencia_de_MFA",
    "test_seeds_diferentes_produzem_projecoes_diferentes",
    "test_tem_os_cabecalhos_de_RFC_5322",
    "test_toda_fonte_declarada_virou_arquivo",
    "test_toda_omissao_declarada_ACONTECE",
    "test_todo_registro_JSONL_carrega_o_instante_do_fato",
    "test_um_fato_com_OUTRO_ator_muda_todas_as_projecoes",
    "test_usuario_IP_e_timestamp_CONCORDAM_entre_as_projecoes",
}

MUTACOES = {
    "a guarda de IOC volta a julgar o conteudo inteiro": (
        [("projecao", GUARDA_DE_IOC, "        achados = achados_no_valor(conteudo)")],
        {
            "test_o_motor_RECUSA_gerador_que_escreve_dominio_roteavel",
            "test_o_motor_RECUSA_IOC_na_forma_CHAVE_VALOR_de_log",
            "test_o_motor_RECUSA_IOC_no_CABECALHO_CEF",
        },
    ),
    # A TOKENIZACAO SEM `=`, que e o defeito que o M1 da auditoria descobriu de
    # lado. Com ela, o caso com espaco (`"visite https://..."`) continua VERDE e
    # so o de `chave=valor` acusa — que e exatamente por que o defeito
    # sobreviveu a peca 3: o unico caso existente era o que nao o alcanca.
    "a tokenizacao nao corta no `=`": (
        [("elenco", TOKEN, TOKEN_SEM_IGUAL)],
        {"test_o_motor_RECUSA_IOC_na_forma_CHAVE_VALOR_de_log"},
    ),
    # O SEGUNDO SEPARADOR, aprendido na correcao do H1. O cabecalho CEF e
    # `CEF:0|vendor|produto|versao|assinatura|NOME|severidade|`, e o `NOME` sai
    # de `action` — campo do fato. Sem cortar no `|`, o token vira o cabecalho
    # inteiro, nao tem forma de host, e um dominio roteavel escrito ali passa.
    #
    # Foi medido plantando o defeito: a familia de separadores nao se descobre
    # por inspecao, ela se descobre quando um formato novo chega.
    "a tokenizacao nao corta no `|`": (
        [("elenco", TOKEN, TOKEN_SEM_PIPE)],
        {"test_o_motor_RECUSA_IOC_no_CABECALHO_CEF"},
    ),
    # A MUTACAO QUE MUDOU DE VEREDITO TRES VEZES, e as viradas contam a historia
    # do gate melhor que qualquer comentario sobre ele:
    #
    # 1a  mutar o SUFIXO para um TLD roteavel derrubava 20 de 27 — a guarda de
    #     IOC e falha fechada. Media a falha fechada, nao a derivacao;
    # 2a  mantendo o sufixo reservado e trocando so o HOST por um literal,
    #     NENHUMA guarda disparava — nao e IP, e o sufixo e permitido. Sobrava
    #     um teste so, e ele teve de ser reescrito para julgar o host da URL em
    #     vez da presenca do ator no `From:`;
    # 3a  **hoje ela derruba tudo o que projeta**, e e o M2 da segunda
    #     auditoria: `intranet-ti.example` virou entidade inventada aos olhos do
    #     motor, porque hostname entrou na forma fechada do oraculo ao lado de
    #     endereco IP.
    #
    # O mesmo defeito plantado saiu de "quase nada o ve" para "o motor se recusa
    # a escrever o pacote". O conjunto grosso e a medida do reforco, e nao um
    # mutante mal escolhido.
    "o host do link e escrito a mao": (
        [
            (
                "email",
                '                    f"Acesse: https://{host}/recadastro",',
                '                    "Acesse: https://intranet-ti.example/recadastro",',
            )
        ],
        TUDO_QUE_PROJETA,
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
    "o database_audit para de carregar o ator": (
        [
            (
                "database_audit",
                CAMPOS_DO_DATABASE,
                '    "exercise_time",\n    "action",\n    "source_ip",\n'
                '    "dest",\n    "records_affected",\n)',
            )
        ],
        # ANTES DO M2 ESTE CONJUNTO ERA VAZIO — a mutacao nao matava nada, e a
        # medicao e o que provou o achado: a fonte carregava `actor` e nenhum
        # teste comparava. Hoje o caso de consistencia mutua a alcanca porque o
        # fato de teste projeta nela.
        {"test_usuario_IP_e_timestamp_CONCORDAM_entre_as_projecoes"},
    ),
    "o vendor do CEF vira literal no modulo": (
        [
            (
                "cef_de_fio",
                "            _escapar(vendor),",
                '            "AuroraSec",',
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
        # A MESMA VIRADA, pelo mesmo motivo. Ate o B1 da segunda auditoria, o
        # `fact_id` no registro era pego por UM teste de suite — e teste de
        # suite e a coisa mais facil de apagar junto com a regressao que ele
        # guarda. Hoje `fact_id` esta na classe `structural` da particao do
        # contrato, e a guarda de veredito recusa a projecao inteira: `05` §6
        # deixou de depender de alguem se lembrar.
        TUDO_QUE_PROJETA,
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
