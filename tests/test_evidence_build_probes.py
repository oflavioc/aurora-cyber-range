"""Prova negativa do build e do verify: a conferencia que nao confere.

R3 §5. `conferir` e a funcao mais perigosa desta fase, porque **o modo de falha
dela e silencioso e parece sucesso**: uma conferencia que nao confere devolve
lista vazia, imprime *"sem achados"* e sai com `0`. Nada distingue o pacote
integro do pacote que ninguem olhou.

AS CINCO MUTACOES
==================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **o hash do arquivo nao e comparado** | some a comparacao de `sha256` | item 3, edicao manual |
| **o hash do ground truth nao e comparado** | some a guarda de `generated_from` | ground truth editado sem rebuild |
| **arquivo a mais e ignorado** | some a varredura do diretorio | cobertura de `08` §7 |
| **a escrita usa a traducao do SO** | `newline=""` -> `newline=None` | R7 §2, LF |
| **o precursor ganha o ator** | `CAMPOS` do precursor ganha `actor` | `08` §2, sinal fraco |

A QUARTA SO MORDE FORA DO LINUX, E ISSO ESTA DITO
==================================================
`newline=None` traduz `\\n` para o separador do SO na escrita. No Linux nao ha
traducao, entao a mutacao e **inerte no CI** — e o caso que a mata
(`test_escreve_com_LF_e_nunca_CRLF`) so fica vermelho no Windows.

Nao e defeito da prova: e a R2 §2 outra vez, do lado do produtor. A licao de
origem foi 56 de 74 hashes "falhando" num checkout Windows por CRLF, e **aqui
nao ha blob de Git a que recorrer** — `scenarios/` esta fora do Git desde a Fase
5. O caso existe para a plataforma em que o defeito aparece, e o registro da
fase diz em qual ele foi medido.

A QUINTA E A QUE PARECE MELHORIA
=================================
Acrescentar `actor` ao `precursor_events.jsonl` da rastreabilidade, ajuda a
correlacao, e **entrega o achado**. Atribuicao e o que o time azul constroi
cruzando as outras fontes; num precursor ela nao e sinal fraco, e resposta. O
arquivo continua valido e o exercicio fica sem o exercicio.

O LIMITE DESTA PROVA, MEDIDO E DECLARADO
=========================================
**Os casos da classe `OsVerbosDoCLI` nao sao alcancados por mutacao em
`build.py`.** `range_cli/cli.py` faz `from range_core.evidence import build`, que
liga ao ATRIBUTO do pacote; o harness substitui `sys.modules`, e o atributo nao
acompanha. O CLI segue chamando o modulo ORIGINAL enquanto o resto da suite ve o
mutado.

**Nao e defeito do CLI**, e por isso nada foi mudado la: `from pacote import
submodulo` e a forma correta em producao, e torce-la para servir ao instrumento
seria deixar o teste ditar o desenho. E nao e defeito do gate: os casos do CLI
provam o que dizem, com o modulo real.

E o limite do INSTRUMENTO, e ele fica escrito porque uma prova negativa que
parece cobrir o CLI e nao cobre e pior que uma que declara nao cobrir. O que
cobre o CLI sao os proprios casos dele, rodados sem mutacao.

OS CONJUNTOS SAO MEDIDOS, NAO PREVISTOS.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD = REPO_ROOT / "range-core" / "evidence" / "build.py"
PRECURSOR = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "precursor.py"
JSONL = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "jsonl.py"
IDENTITY = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "identity_audit.py"
DATABASE = REPO_ROOT / "domains" / "academus" / "evidence_generators" / "database_audit.py"
TESTES = REPO_ROOT / "tests" / "test_evidence_build.py"

#: A cadeia em ordem de dependencia — a licao da peca 3. Os tres ultimos entram
#: sem mutacao propria, so para recarregar depois de `jsonl` e de `precursor`.
MUTAVEIS = (
    ("build", "range_core.evidence.build", BUILD),
    ("jsonl", "domains.academus.evidence_generators.jsonl", JSONL),
    ("precursor", "domains.academus.evidence_generators.precursor", PRECURSOR),
    ("identity_audit", "domains.academus.evidence_generators.identity_audit", IDENTITY),
    ("database_audit", "domains.academus.evidence_generators.database_audit", DATABASE),
)

COMPARA_HASH = """        if em_hash != source["sha256"]:"""

COMPARA_GT = """    if declarado != esperado:"""

VARRE_DIRETORIO = "    for caminho in sorted(destino.iterdir()):"

ESCRITA = '    alvo.write_text(conteudo, encoding="utf-8", newline="")'

CAMPOS_DO_PRECURSOR = '    "exercise_time",\n    "action",\n    "source_ip",\n    "dest",\n)'

MUTACOES = {
    # A MUTACAO QUE NAO MATAVA NINGUEM, E O QUE ELA REVELOU.
    #
    # Medido: com `if False`, os tres casos de edicao manual continuavam
    # VERDES. A causa nao era o gate frouxo — era a SEGUNDA conferencia
    # (`bruto != fonte.conteudo`) pegando a edicao e reportando-a com a
    # mensagem errada: "manifesto e arquivo foram alterados juntos", quando so
    # o arquivo tinha sido tocado.
    #
    # As duas conferencias nao sao redundantes: o hash pergunta "e o que foi
    # escrito?", a reprojecao pergunta "e o que o gabarito projeta?". Quem
    # edita o arquivo E atualiza o hash passa pela primeira e so a segunda o
    # pega. `06` T13 nomeia o HASH como o mecanismo da deteccao de edicao
    # manual, e a mensagem e o que o facilitador le.
    #
    # O gate ganhou dois casos por causa desta medicao — um que exige a
    # mensagem do hash, outro que exerce o conluio — e a mutacao passou a
    # morder.
    "o hash do arquivo nao e comparado": (
        [("build", COMPARA_HASH, "        if False:")],
        {"test_a_edicao_simples_e_reportada_PELO_HASH"},
    ),
    "o hash do ground truth nao e comparado": (
        [("build", COMPARA_GT, "    if False:")],
        {"test_GROUND_TRUTH_editado_sem_rebuild_e_detectado"},
    ),
    "arquivo a mais no diretorio e ignorado": (
        [("build", VARRE_DIRETORIO, "    for caminho in []:")],
        {"test_arquivo_A_MAIS_no_diretorio_e_detectado"},
    ),
    # GROSSA POR CONSEQUENCIA REAL, e o conjunto foi medido NO WINDOWS: o CRLF
    # muda os bytes de todo arquivo, entao o `sha256` do manifesto deixa de
    # bater no mesmo build que o escreveu, e o `verify` acusa tudo. Nao da para
    # torna-la fina — e essa a consequencia de perder o `newline=""`.
    "a escrita usa a traducao de fim de linha do SO": (
        [("build", ESCRITA, '    alvo.write_text(conteudo, encoding="utf-8")')],
        {
            "test_escreve_com_LF_e_nunca_CRLF",
            "test_o_sha256_do_manifesto_confere_com_o_BYTE_em_disco",
            "test_pacote_recem_construido_nao_tem_achado",
        },
    ),
    "o precursor passa a atribuir ator": (
        [
            (
                "precursor",
                CAMPOS_DO_PRECURSOR,
                '    "exercise_time",\n    "action",\n    "source_ip",\n'
                '    "dest",\n    "actor",\n)',
            )
        ],
        {"test_o_precursor_NAO_atribui_ator"},
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
