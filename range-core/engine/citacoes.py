"""Quem cita `fact_id`, e contra o que — o linter de fato citado.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §5.10 (*"`GM_NOTES.md` e narrativa para o facilitador e nao
pode conter fato ausente do ground truth"*), `02_DOMAIN_ACADEMUS.md` §6.3,
`04_SCENARIO_SCHEMA.md` §1 e §8, `06_ACCEPTANCE_TESTS.md` T8 e o item 8 da DoD
da Fase 7.

TRES LADOS CITAM FATO, E O LINTER COBRE OS TRES
================================================
    GM_NOTES.md          prosa do facilitador — o criterio que a DoD nomeia
    materializes_facts   o inject que faz o fato passar a existir (`04` §5)
    projects_facts       a fonte de evidencia que o projeta (`08` §7)

**Fechar so o primeiro seria fechar uma porta de tres.** E a classe que a §7.1
do registro da Fase 7 mede — uma exigencia afirmada num lugar, e os sitios que a
satisfazem nao varridos —, e ela reincidiu cinco vezes na Fase 6.

Os dois ultimos ganharam `pattern` por `$ref` no PR #59, e ate ali eram string
livre. Mas `pattern` responde *"tem forma de `fact_id`?"*, e nao *"existe em
`facts`?"* — a segunda e relacao entre documentos, e e o que este modulo faz.

AS DUAS REDES, E A SEGUNDA E A QUE IMPEDE O PREDICADO ESTREITO
===============================================================
Um linter que so procurasse identificadores BEM FORMADOS teria um buraco
silencioso: `gt-a-031` e `GTA031` nao casam a forma, entao ele nao os veria — e
o autor que os escreveu acha que citou um fato. O erro de digitacao passaria
exatamente pela peneira feita para pega-lo.

    rede 1  BEM FORMADO   casa a forma do contrato -> tem de existir em `facts`
    rede 2  QUASE         parece tentativa de citar fato e NAO casa a forma
                          -> RECUSA, porque ou e erro de digitacao, ou e uma
                             forma que este linter nao sabe conferir

A rede 2 e deliberadamente sobre-inclusiva: ela admite falso positivo — que
custa a alguem renomear uma palavra — e nunca falso negativo, que custa um fato
citado e inexistente chegando a sala. E a mesma direcao que `01` §2 autoriza
para a varredura lexica de TypeScript, e pelo mesmo motivo.

A FORMA VEM DO CONTRATO, COMO DADO
===================================
`contracts/ground_truth.schema.yaml` §`$defs/fact_id_pattern` desde o PR #59, e
ela chega aqui por parametro pela regra de `04` §4.1. Reescreve-la aqui seria a
terceira copia de um padrao que o #59 acabou de unificar — e este modulo existe
justamente para que citacao e declaracao nao divirjam.

O QUE ESTE MODULO NAO FAZ
==========================
**Nao confere `case_id`.** `GC-` e caso da Linha B, e a pergunta dele e outra: o
caso confere contra o DATASET semeado, e nao contra o ground truth. Ela mora em
`domains/academus/seed/gabarito.py`, que e quem conhece o dataset — subir uma
pergunta de dominio para o nucleo seria o acoplamento que o invariante 1
proibe, entrando pela porta de uma funcao util.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


class CitacaoInvalida(Exception):
    """Alguem cita fato que o ground truth nao tem, ou nao sabe citar.

    RECUSA ALTA, e e o verbo que `06` T8 usa: *"divergencia e RECUSADA pelo
    linter"*. Comparacao que relata e nao recusa satisfaz a leitura da norma e
    nao satisfaz a norma — o artefato divergente continua existindo.
    """


def _rede_bem_formada(forma: str) -> re.Pattern[str]:
    """A forma do contrato, ancorada em PALAVRA em vez de em string.

    O padrao do contrato e `^...$` porque la ele valida um campo inteiro. Aqui
    ele varre prosa, e `^$` nunca casaria no meio de uma frase. A conversao e
    mecanica — tira as ancoras de string, poe as de palavra — e nao reescreve a
    forma: o miolo continua sendo exatamente o do contrato.
    """
    miolo = forma.removeprefix("^").removesuffix("$")
    return re.compile(rf"\b{miolo}\b")


#: A rede 2, e ela NAO vem do contrato — de proposito.
#:
#: O contrato descreve o que e VALIDO. Esta rede descreve o que PARECE tentativa
#: de citar um fato, e o contrato nao tem como declarar isso: ele nao fala a
#: linguagem dos erros. Ela e escrita aqui, larga, e o cabecalho diz por que.
#:
#: Casa `GT` com ou sem separador, em qualquer caixa, seguido de algo com
#: digito: `gt-a-031`, `GTA031`, `GT_A_031`, `Gt-a-31`.
_QUASE = re.compile(r"\bg\s*t[-_ ]?[a-z0-9]*[-_ ]?[a-z]*\d+\b", re.IGNORECASE)


def citacoes_de_fato(texto: str, *, forma: str) -> tuple[set[str], set[str]]:
    """`(bem formadas, quase formadas)` no texto dado.

    A segunda EXCLUI a primeira: um identificador bem formado nao e "quase". Sem
    essa subtracao toda citacao correta apareceria nas duas listas, e a recusa
    da rede 2 reprovaria o pack integro.
    """
    bem_formadas = set(_rede_bem_formada(forma).findall(texto))
    quase = {
        achado
        for achado in _QUASE.findall(texto)
        if achado not in bem_formadas
    }
    return bem_formadas, quase


def _texto_da_fonte(valor) -> str:
    """Prosa ou lista de identificadores — os dois viram texto varrivel.

    `GM_NOTES.md` e string; `materializes_facts` e `projects_facts` sao listas.
    Uni-las com espaco basta: as duas redes casam por palavra, e nenhum
    identificador tem espaco dentro.
    """
    if isinstance(valor, str):
        return valor
    if isinstance(valor, Iterable):
        return " ".join(str(item) for item in valor)
    return str(valor)


def confere_citacoes_de_fato(
    *,
    declarados: Iterable[str],
    fontes: Mapping[str, object],
    forma: str,
) -> None:
    """O linter. Levanta `CitacaoInvalida` na primeira fonte divergente.

    `fontes` e `nome legivel -> conteudo`, e o nome entra na mensagem: recusa
    que nao diz ONDE nao permite intervir, que e a forma que `06` T2 fixa.

    AS DUAS DIRECOES SAO CONFERIDAS POR FONTE, e nao no agregado: um
    `GM_NOTES.md` correto nao compensa um `materializes_facts` errado, e reportar
    o conjunto uniao esconderia qual dos tres esta quebrado.

    **Nao ha perna contra vacuidade aqui**, e a ausencia e decidida: um
    `injects.yaml` sem `materializes_facts` e legitimo — inject de midia nao
    materializa fato nenhum. Quem exige que o `GM_NOTES` cite ALGUM fato e o
    dominio, porque a exigencia e sobre o GABARITO e nao sobre pack em geral.
    """
    conhecidos = set(declarados)

    for nome, conteudo in sorted(fontes.items()):
        bem_formadas, quase = citacoes_de_fato(_texto_da_fonte(conteudo), forma=forma)

        if orfaos := sorted(bem_formadas - conhecidos):
            raise CitacaoInvalida(
                f"`{nome}` cita fato que o `ground_truth.yaml` nao declara: "
                f"{orfaos[:5]}.\n"
                "    `00_MASTER_SPEC.md` §5.10: a narrativa EXPLICA o ground "
                "truth, e nao inventa. Fato citado e inexistente invalida o "
                "gabarito inteiro, porque o motor le um e o facilitador conduz "
                "pelo outro.\n"
                f"    Declarados em `facts`: {sorted(conhecidos)[:5]}"
                f"{' ...' if len(conhecidos) > 5 else ''}"
            )

        if malformadas := sorted(quase):
            raise CitacaoInvalida(
                f"`{nome}` cita fato em forma que nao casa o contrato: "
                f"{malformadas[:5]}.\n"
                f"    A forma e `{forma}`, de "
                "`ground_truth.schema.yaml` §`$defs/fact_id_pattern`. Um "
                "identificador que nao casa NUNCA resolve contra `facts` — o "
                "autor acha que citou um fato, e nao citou.\n"
                "    Esta recusa e sobre-inclusiva de proposito: ela admite "
                "falso positivo, que custa renomear uma palavra, e nunca falso "
                "negativo, que custa um fato inexistente chegando a sala."
            )


def fatos_declarados(ground_truth: Mapping | None) -> set[str]:
    """Os `fact_id` que o ground truth declara — o conjunto contra o qual se confere."""
    return {
        str(fato["fact_id"])
        for fato in (ground_truth or {}).get("facts") or []
        if fato.get("fact_id")
    }
