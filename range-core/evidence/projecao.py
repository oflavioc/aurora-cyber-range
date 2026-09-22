"""O motor de projecao — uma realidade, multiplas projecoes.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §5.3, `08_EVIDENCE_SIMULATOR.md` §1 e §2,
`06_ACCEPTANCE_TESTS.md` T13, e os itens 1 e 5 da DoD da Fase 9.

O QUE ESTE MODULO E
===================
A espinha que transforma ground truth em fontes de evidencia:

    cobertura  ->  UM gerador por fonte, com APENAS os fatos daquela fonte
               ->  banner na primeira linha
               ->  RECUSA se a saida trouxer entidade que o ground truth nao fixou

E o terceiro passo que faz a diferenca. `08` §1 afirma que *"contradicao entre
fontes torna-se estruturalmente impossivel"*, e essa frase so e verdadeira se
houver quem a imponha: sem a recusa, ela seria uma intencao sobre como escrever
geradores. A peca 1 deu o oraculo (`elenco.py`); aqui ele vira **porta**.

O MOTOR NAO CONHECE FORMATO DE FIO
===================================
Quem escreve `vpn.log` de verdade e `domains/<adapter>/evidence_generators/`.
O contrato do gerador e mínimo, e deliberadamente:

    gerador(fatos: Sequence[Mapping]) -> str      # o CORPO, sem banner

Ele recebe os fatos ja filtrados e ordenados, e devolve texto. Nao recebe o
ground truth inteiro, nao recebe o elenco, e nao escreve arquivo — as tres
ausencias sao o mesmo desenho do insumo tipado de `00` §3.2: **nao ter por onde
buscar mais do que lhe foi dado**. Um gerador que recebesse o ground truth
poderia projetar o fato invisivel, e a regra de `08` §2 passaria a depender de
ele se lembrar de nao fazer isso.

O BANNER NAO E RESPONSABILIDADE DO GERADOR, pela mesma razao: `05` §4 vale para
todo arquivo, e deixar cada gerador o escrever faria a norma depender de seis
lembrancas em vez de uma.

A ORDEM DOS FATOS E A DO DOCUMENTO, E ISSO TEM LIMITE DECLARADO
================================================================
Dentro de cada fonte, os fatos chegam ao gerador **na ordem em que o ground
truth os lista** — que `domains/academus/seed/gabarito.py` fixa como *"a ordem
do incidente"*, e que e a ordem que um log deve refletir.

**O limite:** se quem escreve o ground truth listar fora de ordem cronologica, a
projecao sai fora de ordem, e nada aqui acusa. Ordenar por `exercise_time`
exigiria compara-los, e comparar `T-9d` com `T-17d` exige a gramatica temporal
que **nao existe** — e a P6-3. Ordenar lexicograficamente seria pior que nao
ordenar: produziria ordem errada com cara de ordenada.

A JANELA SAI DA MESMA ORDEM, e herda o mesmo limite.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from dados_sinteticos import achados_no_valor
from range_core.evidence import banner as _banner
from range_core.evidence.elenco import cobertura_de, elenco_de, enderecos_no

__all__ = [
    "FonteProjetada",
    "GeradorAusente",
    "FonteSemFormato",
    "EntidadeInventada",
    "IOCEncontrado",
    "projetar",
    "nome_do_arquivo",
]

#: `fonte -> nome do arquivo`, quando a regra geral nao vale.
#:
#: A regra geral e `<fonte><extensao do formato>`, e ela acerta as quatro fontes
#: que `08` §3 nomeia literalmente: `email.eml`, `vpn.log`,
#: `identity_audit.jsonl`, `database_audit.jsonl`.
#:
#: `precursor` e a excecao, e ela e da spec: `08` §2 e `06` T13 chamam o arquivo
#: de **`precursor_events.jsonl`**, nao de `precursor.jsonl`. Derivar o nome
#: produziria um arquivo que o criterio de aceitacao nao encontra.
NOMES_PROPRIOS = {"precursor": "precursor_events.jsonl"}

#: Extensao por formato de fio. `cef_syslog` usa `.log` porque CEF viaja sobre
#: syslog e e um log de texto — `08` §3 nao nomeia o arquivo dele, entao a regra
#: geral decide, e a decisao fica aqui em vez de virar surpresa no disco.
EXTENSAO = {
    "rfc5322": ".eml",
    "syslog_text": ".log",
    "jsonl": ".jsonl",
    "cef_syslog": ".log",
}

Gerador = Callable[[Sequence[Mapping]], str]

#: Um token de conteudo: tudo que nao e espaco nem pontuacao de delimitacao.
#:
#: **POR QUE TOKENIZAR, E ESTE E O PONTO QUE UMA PRIMEIRA VERSAO ERROU.**
#: `dados_sinteticos.achados_no_valor` opera sobre UM VALOR DE CAMPO — e o que
#: `hostnames_candidatos` assume: ou o valor e uma URL, ou um e-mail, ou um
#: hostname nu. Texto com espaco no meio ele descarta e devolve **lista vazia**.
#:
#: Aplicado ao conteudo INTEIRO de um arquivo de log, o predicado passava
#: vacuamente: `"visite https://<host roteavel>/login"` nao produzia achado
#: nenhum. A guarda parecia proteger e nao protegia — medido na peca 3.
#:
#: A TOKENIZACAO E DO MOTOR; O JULGAMENTO CONTINUA SENDO DO PREDICADO UNICO.
#: A alternativa — ensinar `dados_sinteticos` a ler texto livre — mudaria a
#: semantica de um modulo que o CI e o loader ja consomem, para servir a um
#: chamador so. Compor e mais barato e nao move a fonte da resposta (R9 §8).
#:
#: `=` E SEPARADOR, e isto foi medido na correcao do M1 da auditoria: log de fio
#: e `chave=valor`, e sem cortar no `=` o token vira `url=https://<host>/x` —
#: `urlsplit` nao reconhece `url=https` como esquema, `hostnames_candidatos`
#: devolve nada, e o IOC passa. O caso original desta guarda usava
#: `"visite https://..."`, com espaco, e por isso o defeito nao aparecia: a
#: forma que um GERADOR de log realmente escreve e a outra.
_TOKEN = re.compile(r"[^\s\"'<>()\[\],;=]+")


def _achados_no_texto(conteudo: str) -> list:
    """Os achados de `dados_sinteticos`, token a token — ver `_TOKEN`."""
    achados = []
    for token in _TOKEN.findall(conteudo):
        achados.extend(achados_no_valor(token))
    return achados


class GeradorAusente(Exception):
    """A cobertura pede uma fonte para a qual nao ha gerador."""


class FonteSemFormato(Exception):
    """A fonte nao esta no registro de formatos do contrato."""


class EntidadeInventada(Exception):
    """A saida do gerador traz entidade que o ground truth nao fixou — item 1."""


class IOCEncontrado(Exception):
    """A saida do gerador traz dado nao sintetico — item 5, `05` §2 e §3.

    **Quem decide e `dados_sinteticos`**, o mesmo predicado que o loader de pack
    e o CI usam. Um detector proprio aqui seria a terceira resposta para *"este
    valor e sintetico?"* — a P1-13 por mais uma porta, divergindo na primeira
    faixa nova. `05` §2 nao admite excecao, e a guarda fica no PRODUTOR: o
    arquivo nao chega a existir, em vez de existir e ser reprovado depois.
    """


@dataclass(frozen=True)
class FonteProjetada:
    """Uma fonte pronta para virar arquivo. Imutavel: e o resultado de uma
    projecao determinista, e nada depois dela deve reescrever o conteudo."""

    fonte: str
    formato: str
    conteudo: str
    projects_facts: tuple[str, ...]
    janela: str

    @property
    def nome_do_arquivo(self) -> str:
        return nome_do_arquivo(self.fonte, self.formato)


def nome_do_arquivo(fonte: str, formato: str) -> str:
    """`<fonte><extensao>`, com as excecoes que a spec nomeia."""
    if fonte in NOMES_PROPRIOS:
        return NOMES_PROPRIOS[fonte]
    extensao = EXTENSAO.get(formato)
    if extensao is None:
        raise FonteSemFormato(
            f"formato de fio sem extensao declarada: {formato!r} (fonte {fonte!r}). "
            f"Formato novo entra por spec-change, e o nome do arquivo dele e "
            f"decisao — nao consequencia"
        )
    return f"{fonte}{extensao}"


def _janela(fatos: Sequence[Mapping]) -> str:
    """Do primeiro ao ultimo fato, NA ORDEM DO DOCUMENTO — ver o cabecalho.

    `window` e obrigatoria em TODA fonte (L3 da terceira auditoria da Fase 1):
    sem ela o facilitador nao sabe o que o arquivo abrange, e isso vale igual
    para o pre-posicionado e para o liberado por inject.
    """
    primeiro = fatos[0].get("exercise_time", "?")
    ultimo = fatos[-1].get("exercise_time", "?")
    return f"{primeiro} → {ultimo}"


def projetar(
    ground_truth: Mapping,
    *,
    geradores: Mapping[str, Gerador],
    formatos: Mapping[str, str],
    banner: str,
) -> list[FonteProjetada]:
    """Projeta o ground truth nas fontes que ele declara.

    `formatos` vem de `contract_source.formatos_por_fonte` e `banner` de
    `contract_source.restricoes_de_evidencia` — os dois LIDOS do contrato, nunca
    reescritos aqui (a P1-13).

    A ordem das fontes e alfabetica, e a razao e determinismo: iteracao de
    dicionario e estavel em CPython mas nao e contrato de linguagem, e a saida
    deste motor alimenta hash no manifesto.
    """
    cobertura = cobertura_de(ground_truth)
    if not cobertura:
        return []

    elenco = elenco_de(ground_truth)
    ordem_do_documento = list(ground_truth.get("facts") or ())

    faltando = sorted(set(cobertura) - set(geradores))
    if faltando:
        raise GeradorAusente(
            f"a cobertura de projecao pede fonte sem gerador: {', '.join(faltando)}. "
            f"Sem ele a fonte nao viraria arquivo, e a cobertura de `08` §7 "
            f"passaria a declarar um arquivo que nao existe"
        )

    projetadas: list[FonteProjetada] = []

    for fonte in sorted(cobertura):
        formato = formatos.get(fonte)
        if formato is None:
            raise FonteSemFormato(
                f"fonte fora do registro do contrato: {fonte!r}. "
                f"`contracts/evidence.schema.yaml` §`x-aurora-registry.source_formats` "
                f"e o conjunto FECHADO de v1"
            )

        da_fonte = [f for f in ordem_do_documento if f.get("fact_id") in cobertura[fonte]]
        corpo = geradores[fonte](da_fonte)
        conteudo = _banner.linha(formato, banner) + "\n" + corpo

        inventadas = sorted(enderecos_no(conteudo) - elenco.enderecos)
        if inventadas:
            raise EntidadeInventada(
                f"a projecao de {fonte!r} traz endereco que o ground truth nao "
                f"fixou: {', '.join(inventadas)}. `08` §2 — a projecao consome o "
                f"elenco do ground truth, e nao inventa entidade"
            )

        # O item 5, com o predicado que o CI ja usa. Vem DEPOIS da guarda de
        # elenco porque as duas perguntas sao diferentes e a ordem importa para
        # a mensagem: endereco de documentacao fora do elenco e invencao (a
        # primeira), e endereco roteavel e IOC (esta) — reportar a segunda para
        # um caso da primeira mandaria o autor do gerador procurar a faixa
        # errada.
        achados = _achados_no_texto(conteudo)
        if achados:
            raise IOCEncontrado(
                f"a projecao de {fonte!r} traz dado que nao e sintetico: "
                f"{achados[:5]}. `05` §2 e §3 nao admitem excecao — sem IOC real, "
                f"sem dominio roteavel, IP so de faixa de documentacao ou privada"
            )

        projetadas.append(
            FonteProjetada(
                fonte=fonte,
                formato=formato,
                conteudo=conteudo,
                projects_facts=tuple(f["fact_id"] for f in da_fonte),
                janela=_janela(da_fonte),
            )
        )

    return projetadas
