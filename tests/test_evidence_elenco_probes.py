"""Prova negativa do item 1: o gate do elenco fica vermelho com defeito plantado.

R3 §5 — gate novo so e aceito matando um mutante escrito para ele. Uma suite que
nunca ficou vermelha prova que roda, nao que detecta, e o item 1 e especialmente
exposto a isso: `elenco_de` e `cobertura_de` sao funcoes curtas sobre um dicio-
nario, e uma suite distraida sobre elas passa concedendo tudo.

AS QUATRO MUTACOES, E A PROPRIEDADE QUE CADA UMA ATACA
=======================================================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **o elenco aceita tudo** | `contem` devolve `True` sempre | a afirmacao de PRESENCA |
| **o rotulo entra no lugar do destino** | `action` no lugar de `dest` | entidade nao e rotulo de especie |
| **a cobertura declara o enum inteiro** | toda fonte do contrato, com conjunto vazio | fonte sem fato nao existe |
| **a regex de endereco perde a fronteira** | sai o `(?![\\w.])` | endereco nao e sequencia de numeros |

A PRIMEIRA E A QUE UM GATE DISTRAIDO CONCEDE
=============================================
`contem` sempre `True` e exatamente o oraculo que nao morde: com ele, toda
projecao passa, inclusive a que inventa ator. Se nenhum teste acusasse, o item 1
estaria sendo afirmado por uma funcao que nao decide nada — e e essa a forma de
defeito que a Fase 7 mediu como a mais cara, porque nada fica vermelho.

A QUARTA E A UNICA QUE EXIGE CASO ADVERSARIAL
==============================================
Sem a fronteira da direita, `1.2.3.4.5` doa `1.2.3.4`. Nenhum caso POSITIVO a
pega: os enderecos legitimos continuam sendo achados, e a suite ficaria verde
inteira. Quem a mata e `test_NAO_confunde_versao_nem_sequencia_de_numeros_com_
endereco`, que existe so para isso — e a razao de um gate nascer com caso
adversarial e nao so com positivo e negativo (R10 §nascimento).

A SUITE ALVO PRECISA RESOLVER O MODULO POR `sys.modules`
=========================================================
`tests/test_evidence_elenco.py` obtem o modulo por `importlib.import_module`, e
isso e **condicao de funcionamento desta prova**, nao estilo. O harness planta a
mutacao substituindo a entrada de `sys.modules`; um `from range_core.evidence
import elenco as mod` ligaria `mod` ao ATRIBUTO do pacote, que o harness nao
toca.

**Medido, e o sintoma e traicoeiro:** rodada sozinha, esta prova passava — o
atributo do pacote ainda nao existia, e o `from` caia no `sys.modules` mutado
por acaso. Rodada junto da arvore inteira, os quatro mutantes "sobreviviam",
porque a suite alvo ja tinha sido importada e o atributo ja apontava para o
original. Falha de INSTRUMENTO lida como ausencia de deteccao — o espelho exato
do que o cabecalho de `test_queda_de_sessao_probes.py` descreve, e a razao de
uma prova negativa ter de ser conferida na suite COMPLETA e nao so isolada.

OS CONJUNTOS SAO MEDIDOS, E NAO PREVISTOS
==========================================
A primeira redacao deste arquivo PREVIU um conjunto, e a execucao o desmentiu.
Fica registrado porque o erro e instrutivo, e porque "medido, nao previsto" so
significa alguma coisa quando a previsao errada aparece:

**1. `test_fato_invisivel_ENTRA_no_elenco` NAO acusa a mutacao do rotulo** — eu
previa que sim. O fato invisivel da fixture declara `dest: host-sem-log`, entao
trocar `dest` por `action` de fato o tira do elenco; mas aquele teste so afirma
sobre `atores` e `enderecos`, e nunca olha `destinos`. **A medicao revelou uma
propriedade do TESTE, e nao do modulo:** o caso do fato invisivel nao cobre
destino. Nao e defeito — o assunto dele e `projections` —, mas agora esta dito.

**2. A mutacao da cobertura NAO derruba `test_fato_SEM_projections_nao_aparece_
em_fonte_nenhuma`**, e esta certo: declarar toda fonte com conjunto VAZIO nao
poe `GT-A-099` em lugar nenhum. O teste continua verde porque a propriedade que
ele julga continua valendo — e e assim que se descobre que duas asserções
proximas julgam coisas diferentes de verdade.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
ELENCO = REPO_ROOT / "range-core" / "evidence" / "elenco.py"
TESTES = REPO_ROOT / "tests" / "test_evidence_elenco.py"

MUTAVEIS = (("elenco", "range_core.evidence.elenco", ELENCO),)

CONTEM = "        return valor in self.todos"

MAPA = '    baldes = {"actor": atores, "dest": destinos, CAMPO_DE_ENDERECO: enderecos}'

RETORNO_DA_COBERTURA = (
    "    return {fonte: frozenset(fatos) for fonte, fatos in por_fonte.items()}"
)

ENUM_INTEIRO = (
    "    todas = ('vpn', 'identity_audit', 'database_audit', 'email', 'cef', 'precursor')\n"
    "    for fonte in todas:\n"
    "        por_fonte.setdefault(fonte, set())\n"
    "    return {fonte: frozenset(fatos) for fonte, fatos in por_fonte.items()}"
)

MUTACOES = {
    "o elenco aceita tudo": (
        [("elenco", CONTEM, "        return True")],
        {"test_o_elenco_responde_por_ator_e_destino_pela_PRESENCA"},
    ),
    "o rotulo de especie entra no lugar do destino": (
        [
            ("elenco", 'CAMPOS_DE_ENTIDADE = ("actor", "dest", "source_ip")',
             'CAMPOS_DE_ENTIDADE = ("actor", "action", "source_ip")'),
            ("elenco", MAPA,
             '    baldes = {"actor": atores, "action": destinos, CAMPO_DE_ENDERECO: enderecos}'),
        ],
        {
            "test_reune_ator_destino_e_endereco_de_todos_os_fatos",
            "test_o_elenco_NAO_carrega_escalar_nem_rotulo",
            "test_o_elenco_responde_por_ator_e_destino_pela_PRESENCA",
        },
    ),
    "a cobertura declara o enum inteiro do contrato": (
        [("elenco", RETORNO_DA_COBERTURA, ENUM_INTEIRO)],
        {
            "test_cada_fonte_recebe_exatamente_os_fatos_que_a_declaram",
            "test_projections_VAZIA_e_tratada_como_ausente",
            "test_a_cobertura_nao_inventa_fonte",
        },
    ),
    "a regex de endereco perde a fronteira da direita": (
        [
            (
                "elenco",
                r'_IPV4 = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w.])")',
                r'_IPV4 = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}")',
            )
        ],
        {"test_NAO_confunde_versao_nem_sequencia_de_numeros_com_endereco"},
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
