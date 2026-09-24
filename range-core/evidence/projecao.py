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
               ->  RECUSA se a saida expressar campo que so o gabarito sabe
               ->  RECUSA se a saida trouxer entidade que o ground truth nao fixou
               ->  RECUSA se a saida trouxer dado que nao e sintetico

Sao as RECUSAS que fazem a diferenca. `08` §1 afirma que *"contradicao entre
fontes torna-se estruturalmente impossivel"*, e essa frase so e verdadeira se
houver quem a imponha: sem elas, seria uma intencao sobre como escrever
geradores. A peca 1 deu o oraculo (`elenco.py`); aqui ele vira **porta**.

E A PRIMEIRA DAS TRES E A QUE GUARDA A CAMADA. `00` §3 separa ground truth de
evidencia observavel, e a separacao nao sobrevive a boa vontade: tres geradores
escreviam `credential_state` — o veredito do gabarito sobre a credencial — e o
unico que NAO o escrevia dizia em comentario que nao o escrevia de proposito.
Uma norma que depende de cada autor lembrar dela ja esta quebrada; foi o B1 da
segunda auditoria. Ver `VereditoDoGabarito`.

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
from range_core.evidence.elenco import (
    cobertura_de,
    elenco_de,
    enderecos_no,
    hosts_inventados,
    tokens_no,
)

__all__ = [
    "FonteProjetada",
    "GeradorAusente",
    "FonteSemFormato",
    "EntidadeInventada",
    "IOCEncontrado",
    "VereditoDoGabarito",
    "RespostaEntregue",
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

def _achados_no_texto(conteudo: str) -> list:
    """Os achados de `dados_sinteticos`, token a token.

    A TOKENIZACAO E DE `elenco.tokens_no`; O JULGAMENTO CONTINUA SENDO DO
    PREDICADO UNICO. A alternativa — ensinar `dados_sinteticos` a ler texto
    livre — mudaria a semantica de um modulo que o CI e o loader ja consomem,
    para servir a um chamador so. Compor e mais barato e nao move a fonte da
    resposta (R9 §8).
    """
    achados = []
    for token in tokens_no(conteudo):
        achados.extend(achados_no_valor(token))
    return achados


def _folhas(valor: object) -> list[str]:
    """Os valores ESCALARES de um campo do fato, como texto.

    Campo do fato e escalar ou mapa (`discoverability`) ou lista
    (`projections`). Descer ate a folha e o que faz a guarda alcancar
    `discoverability.requires`, que e a frase que literalmente diz ao
    facilitador o que ha para descobrir.

    `bool` fica de fora por ser `int` em Python e por nao existir campo booleano
    em `$defs/fact` — incluir produziria a busca pelos literais `True`/`False`,
    que casam palavra comum sem nomear nada.
    """
    if isinstance(valor, str):
        return [valor] if valor else []
    if isinstance(valor, bool):
        return []
    if isinstance(valor, (int, float)):
        return [str(valor)]
    if isinstance(valor, Mapping):
        return [f for v in valor.values() for f in _folhas(v)]
    if isinstance(valor, Sequence):
        return [f for v in valor for f in _folhas(v)]
    return []


def _ocorre(agulha: str, conteudo: str) -> bool:
    """A agulha aparece no conteudo como UNIDADE, e nao como pedaco de palavra.

    POR QUE FRONTEIRA E NAO TOKEN. A tokenizacao de `_TOKEN` serve ao predicado
    de IOC, que precisa de um candidato a host por vez; aqui o alvo e outro —
    `{"fact_class": "initial_access"}` produz o token `initial_access}`, com a
    chave colada, e a igualdade de token nao casaria. A fronteira `[\\w.-]` das
    duas pontas atravessa a pontuacao de QUALQUER formato de fio (`=` do
    syslog, `"` e `:` do JSON, `|` do CEF) sem casar `GT-A-0142` para `GT-A-014`.

    E ela e o que permite buscar valor com ESPACO — a frase de
    `discoverability.requires` — com a mesma regra, em vez de uma segunda.
    """
    return re.search(rf"(?<![\w.-]){re.escape(agulha)}(?![\w.-])", conteudo) is not None


class GeradorAusente(Exception):
    """A cobertura pede uma fonte para a qual nao ha gerador."""


class FonteSemFormato(Exception):
    """A fonte nao esta no registro de formatos do contrato."""


class EntidadeInventada(Exception):
    """A saida do gerador traz entidade que o ground truth nao fixou — item 1."""


class RespostaEntregue(Exception):
    """A fonte projeta EXATAMENTE os fatos que o gabarito cita como caso.

    B1 DA TERCEIRA AUDITORIA, e ele e o irmao gemeo do B1 da segunda por outro
    canal. La o vazamento era de CAMPO — `credential_state` dizendo a resposta
    dentro da linha. Aqui e de CONJUNTO: o `database_audit.jsonl` levava as 67
    linhas que `line_b_cases` cita como caso, e **so elas**, numa populacao de
    3.145 alteracoes de nota.

    O participante nao precisava ler campo nenhum. Bastava abrir o arquivo: se
    esta aqui, e caso. E como a ordem e a do documento e o gabarito agrupa por
    conjunto, a posicao ainda entregava a particao por defensibilidade.

    O QUE SE AFIRMA, E POR FACT_CLASS. A pergunta nao e *"a fonte tem caso?"* —
    tem, e deve ter. E *"dentro de uma especie de fato, a fonte tem SO casos?"*.
    Um arquivo com 67 casos entre 3.145 linhas nao revela nada; um com 67 de 67
    revela tudo. Por isso a comparacao e de igualdade dentro da classe, e nao de
    pertinencia: `exfiltration` na mesma fonte nao dilui `grade_change_retroactive`,
    porque o time azul nao confunde as duas populacoes.

    O LIMITE, DECLARADO: a guarda so morde onde o gabarito DECLARA casos. Um
    pack sem `line_b_cases` nao tem resposta escrita, e nao ha o que entregar.
    """


class VereditoDoGabarito(Exception):
    """A saida do gerador expressa campo que so o gabarito sabe — `00` §3.

    B1 DA SEGUNDA AUDITORIA, e o defeito que ele nomeia e de CAMADA, nao de
    seguranca: `vpn.log`, `identity_audit.jsonl` e o CEF saiam com
    `credential=compromised`. Nenhum concentrador de VPN do mundo registra que
    uma credencial esta comprometida — isso e ATRIBUICAO, e atribuicao e o que o
    time azul constroi. A segunda linha do arquivo entregava pronta a conclusao
    que o proprio fato manda correlacionar.

    **A guarda nao le uma lista escrita aqui.** Ela consome a particao de
    `contracts/evidence.schema.yaml` §`x-aurora-registry.fact_fields`, e o
    comentario de la explica por que a particao e de tres listas: uma lista de
    proibidos envelhece calada, porque campo novo no fato nasceria permitido.
    """


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


def _do_gabarito_no_fato(
    fato: Mapping, projetaveis: frozenset[str], fontes: frozenset[str]
) -> list[tuple[str, str]]:
    """`(campo, agulha)` do que este fato tem e que NAO pode ir para o fio.

    O CAMPO VIAJA JUNTO COM A AGULHA porque e ele que a recusa precisa nomear:
    quem le *"expressa 'compromised'"* procura uma string no gerador; quem le
    *"expressa `credential_state`"* sabe qual campo do fato nao devia estar
    sendo lido. Os dois na mensagem, e a mensagem aponta o conserto.

    O NOME entra junto com o valor porque a fonte JSONL escreve a chave: um
    registro com `"credential_state"` e `""` nao seria pego pelo valor, e a
    chave ja afirma que o campo foi registrado — que e o que o time azul le.

    A EXCLUSAO DECLARADA: valor que e NOME DE FONTE do registro do contrato nao
    entra. `projections` carrega exatamente esses nomes (`vpn`, `email`, `cef`),
    e eles sao vocabulario da camada de projecao, nao fato sobre o mundo —
    procura-los em texto livre acusaria a palavra "email" no corpo de um e-mail.
    O que `projections` de fato revela — em quais OUTRAS fontes o fato aparece —
    nao e expressavel dentro de um arquivo so.
    """
    agulhas: list[tuple[str, str]] = []
    for campo, valor in fato.items():
        if campo in projetaveis:
            continue
        agulhas.append((campo, campo))
        agulhas.extend((campo, f) for f in _folhas(valor) if f not in fontes)
    return agulhas


def _fatos_de_caso(ground_truth: Mapping) -> frozenset[str]:
    """Os `fact_id` que `line_b_cases` cita como evidencia de apoio.

    E a RESPOSTA escrita: quem tem esta lista sabe quais linhas da trilha sao
    caso e qual a defensibilidade de cada uma. `04` §3 a poe no ground truth
    justamente porque ela e gabarito, e `05` §6 a mantem fora de tudo que chega
    ao participante.
    """
    citados: set[str] = set()
    for caso in ground_truth.get("line_b_cases") or ():
        if isinstance(caso, Mapping):
            citados.update(
                f for f in (caso.get("supporting_evidence") or ()) if isinstance(f, str)
            )
    return frozenset(citados)


def _entrega_a_resposta(
    da_fonte: Sequence[Mapping], casos: frozenset[str]
) -> str | None:
    """A `fact_class` cuja populacao nesta fonte e so de caso, ou `None`.

    POR CLASSE, e a razao esta em `RespostaEntregue`: e dentro de uma especie de
    fato que o participante compara linhas. Misturar classes para diluir seria
    esconder o vazamento atras de uma populacao que ninguem confunde com a
    outra.
    """
    if not casos:
        return None

    por_classe: dict[str, list[str]] = {}
    for fato in da_fonte:
        classe, fact_id = fato.get("fact_class"), fato.get("fact_id")
        if isinstance(classe, str) and isinstance(fact_id, str):
            por_classe.setdefault(classe, []).append(fact_id)

    for classe, ids in por_classe.items():
        if set(ids) <= casos:
            return classe
    return None


def projetar(
    ground_truth: Mapping,
    *,
    geradores: Mapping[str, Gerador],
    formatos: Mapping[str, str],
    banner: str,
    campos_do_fato: Mapping[str, frozenset[str]],
) -> list[FonteProjetada]:
    """Projeta o ground truth nas fontes que ele declara.

    `formatos` vem de `contract_source.formatos_por_fonte`, `banner` de
    `contract_source.restricoes_de_evidencia` e `campos_do_fato` de
    `contract_source.campos_do_fato` — os tres LIDOS do contrato, nunca
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
    projetaveis = campos_do_fato["projectable"]
    nomes_de_fonte = frozenset(formatos)
    casos = _fatos_de_caso(ground_truth)

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

        # A RESPOSTA, ANTES DE QUALQUER BYTE SER GERADO — B1 da 3a auditoria.
        # Esta guarda nao olha conteudo: ela olha a COBERTURA, e por isso vem
        # antes do gerador. Uma fonte que projeta so caso ja esta errada na
        # declaracao do gabarito, e nao na escrita do arquivo — o conserto e
        # remover a projecao ou acrescentar a populacao, nunca mudar o gerador.
        classe = _entrega_a_resposta(da_fonte, casos)
        if classe is not None:
            raise RespostaEntregue(
                f"a fonte {fonte!r} projeta, da especie {classe!r}, APENAS fatos "
                f"que `line_b_cases` cita como caso. O arquivo entrega a "
                f"resposta: quem o abre sabe quais linhas sao caso sem analisar "
                f"nenhuma. `05` §6 — o gabarito fica fora do que chega ao "
                f"participante. Projete a populacao inteira daquela especie, ou "
                f"nao projete a especie"
            )

        corpo = geradores[fonte](da_fonte)
        conteudo = _banner.linha(formato, banner) + "\n" + corpo

        # O VEREDITO DO GABARITO — B1 da segunda auditoria. Vem PRIMEIRO das
        # tres guardas, e a ordem e a da gravidade: endereco inventado e fonte
        # incoerente, IOC e norma de seguranca, e isto aqui e o exercicio
        # perdendo o sentido — a evidencia passa a afirmar a resposta, e toda
        # medicao de deteccao sobre ela vira medicao de leitura de rotulo.
        for fato in da_fonte:
            for campo, agulha in _do_gabarito_no_fato(
                fato, projetaveis, nomes_de_fonte
            ):
                if _ocorre(agulha, conteudo):
                    raise VereditoDoGabarito(
                        f"a projecao de {fonte!r} expressa {agulha!r}, que e o "
                        f"campo de gabarito `{campo}` do fato "
                        f"{fato.get('fact_id')!r}. "
                        f"`00` §3 separa ground truth de evidencia observavel: "
                        f"so os campos de "
                        f"`x-aurora-registry.fact_fields.projectable` vao para "
                        f"o fio, porque so eles um sensor registraria"
                    )

        inventadas = sorted(enderecos_no(conteudo) - elenco.enderecos)
        if inventadas:
            raise EntidadeInventada(
                f"a projecao de {fonte!r} traz endereco que o ground truth nao "
                f"fixou: {', '.join(inventadas)}. `08` §2 — a projecao consome o "
                f"elenco do ground truth, e nao inventa entidade"
            )

        # A SEGUNDA FORMA FECHADA — M2 da segunda auditoria. Endereco e hostname
        # sao as duas entidades sobre as quais se pode afirmar AUSENCIA de
        # invencao; a mensagem separa as duas porque quem escreve o gerador
        # procura em lugares diferentes.
        hosts = hosts_inventados(conteudo, elenco)
        if hosts:
            raise EntidadeInventada(
                f"a projecao de {fonte!r} traz host cujo rotulo o ground truth "
                f"nao fixou: {', '.join(hosts)}. `08` §2 — o rotulo tem de vir "
                f"do elenco (o sufixo reservado de `05` §2 nao conta), e um "
                f"literal escrito no gerador se reproduz identico na "
                f"reprojecao, entao o `evidence verify` NAO o pegaria"
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
