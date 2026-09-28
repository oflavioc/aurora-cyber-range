"""O banner de ambiente simulado, por formato de fio — `05` §4.

AUTORIDADE
----------
`05_SECURITY_REQUIREMENTS.md` §4: banner *"em toda tela e no rodape de todo
artefato gerado"*, e — nos arquivos de evidencia — *"como comentario na primeira
linha, no formato do proprio arquivo"*. `06_ACCEPTANCE_TESTS.md` T13 o cobra
como criterio proprio.

O TEXTO VEM DO CONTRATO, E ISSO NAO E PREFERENCIA
==================================================
`contracts/evidence.schema.yaml` declara `banner_text` em
`x-aurora-security-constraints`, e este modulo o recebe por parametro — lido de
la por `contract_source.restricoes_de_evidencia`. Escrever a string aqui seria a
**P1-13 por outra porta**: aquela pendencia e exatamente duas copias da mesma
norma de seguranca, uma no contrato e outra num modulo, que ja divergiram duas
vezes sem ninguem notar. Uma terceira copia nao melhoraria a situacao.

A FORMA DO COMENTARIO E POR FORMATO, E CADA UMA E DECISAO
==========================================================
`05` §4 diz *"no formato do proprio arquivo"*, e os quatro formatos de fio de
`08` §3 nao tem a mesma nocao de comentario:

    syslog_text   `#` — convencao universal de log em texto
    cef_syslog    `#` — o mesmo; CEF viaja sobre syslog
    jsonl         REGISTRO JSON, e nao comentario
    rfc5322       CABECALHO `X-`, e nao comentario

**JSONL e a decisao que precisa de razao.** JSON nao tem comentario, e um `#` na
primeira linha quebraria todo parser que o time azul apontasse para o arquivo —
`jq`, um script de ingestao, o proprio SIEM de treinamento. Um arquivo de
evidencia que nao abre e pior que um sem banner, e a regra de `05` §4 e
*"no formato do proprio arquivo"*, que aqui significa: um registro a mais, com
chave reservada. O parser le, o humano ve, e nada quebra.

**RFC 5322 e a segunda.** `.eml` nao tem comentario de linha; tem comentario
entre parenteses dentro de campo estruturado, que nenhum leitor de e-mail
mostra. O idiomatico e um cabecalho proprio, e cabecalho `X-` e exatamente o
mecanismo que o formato reserva para isso.

FALHA FECHADA PARA FORMATO DESCONHECIDO
========================================
Formato sem forma de banner declarada e **recusado**, e nao tratado com um
default. As fontes pos-MVP de `08` §4 entram por spec-change, e cada uma tera de
decidir a sua forma; um default silencioso produziria arquivo sem banner no dia
em que a primeira delas chegasse — que e a falha que `05` §4 nao admite.
"""

from __future__ import annotations

import json

__all__ = ["FormatoSemBanner", "texto", "linha", "tem_banner"]

#: A chave reservada do banner em JSONL. Prefixada com `_` pela convencao que
#: separa metadado de campo de dado — um registro de evidencia nunca tem `_`
#: no inicio da chave.
CHAVE_JSONL = "_banner"

#: O cabecalho do banner em RFC 5322. `X-` e o espaco que o formato reserva para
#: cabecalho nao padronizado.
CABECALHO_RFC5322 = "X-Aurora-Simulacao"


class FormatoSemBanner(Exception):
    """Formato de fio sem forma de banner declarada.

    Nao ha default, e a ausencia dele e o ponto — ver o cabecalho.
    """


def texto(contratos: dict[str, dict]) -> str:
    """O texto do banner, lido do contrato.

    Atalho sobre `contract_source.restricoes_de_evidencia` para quem so precisa
    do banner: a leitura continua sendo uma so, e nenhum chamador escreve a
    string.
    """
    from range_core.engine.loader.contract_source import (
        ContractSourceError,
        restricoes_de_evidencia,
    )

    valor = restricoes_de_evidencia(contratos).get("banner_text")
    if not valor:
        raise ContractSourceError(
            "contracts/evidence.schema.yaml sem "
            "`x-aurora-security-constraints.banner_text`: sem ele o motor "
            "teria de reescrever o texto que `05` §4 fixa"
        )
    return valor


def linha(formato: str, texto_do_banner: str) -> str:
    """A primeira linha do arquivo, no formato dele.

    Sem `\\n` no fim: quem monta o arquivo junta as linhas, e devolver o
    separador aqui faria a juncao depender de quem chamou primeiro.
    """
    if formato in ("syslog_text", "cef_syslog"):
        return f"# {texto_do_banner}"
    if formato == "jsonl":
        # `ensure_ascii=False` PRESERVA o travessao e o acento de
        # "DADOS FICTICIOS" — escapa-los produziria um banner que o humano le
        # como `—`, e o requisito e que ele AVISE. O arquivo e UTF-8 por
        # decisao do gerador (R7 §2), entao nao ha o que escapar.
        return json.dumps({CHAVE_JSONL: texto_do_banner}, ensure_ascii=False)
    if formato == "rfc5322":
        return f"{CABECALHO_RFC5322}: {texto_do_banner}"
    raise FormatoSemBanner(
        f"formato de fio sem forma de banner declarada: {formato!r}. "
        f"`05` §4 exige banner na primeira linha de todo arquivo de evidencia, "
        f"e nao ha default — a forma de cada formato novo e decisao, nao "
        f"consequencia"
    )


def tem_banner(conteudo: str, formato: str, texto_do_banner: str) -> bool:
    """O conteudo abre com o banner do formato?

    **Na PRIMEIRA linha, e a posicao e o requisito.** `05` §4 e explicito, e a
    razao e de uso: banner no rodape nao avisa quem abre o arquivo e le as
    primeiras linhas, que e o que alguem faz com um log de 40 mil registros.

    Comparacao pela linha INTEIRA, e nao por `in`: `in` aceitaria o banner no
    meio de uma linha de dado, e uma linha de dado que por acaso contivesse o
    texto passaria a valer como banner.
    """
    primeira = conteudo.split("\n", 1)[0]
    try:
        return primeira == linha(formato, texto_do_banner)
    except FormatoSemBanner:
        return False
