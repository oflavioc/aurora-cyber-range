"""O elenco fixado pelo ground truth, e a cobertura de projecao — item 1.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §5.3 (*"toda evidencia e projecao de fato canonico"*),
`08_EVIDENCE_SIMULATOR.md` §1 e §2, `06_ACCEPTANCE_TESTS.md` T13, e o item 1
da DoD da Fase 9 (`07_IMPLEMENTATION_PHASES.md`).

O QUE ESTE MODULO RESPONDE
==========================
Tres perguntas, todas PURAS:

    elenco_de(ground_truth)    quais entidades as projecoes PODEM usar
    cobertura_de(ground_truth) fonte -> os `fact_id` que ela projeta
    enderecos_no(texto)        quais enderecos um texto CONTEM

As duas primeiras sao funcao do ground truth e de mais nada — **nem do seed**.
`06` T13 exige teste *"dirigido por fato, nao por seed"*, e um modulo que
recebesse seed nao teria como sustentar isso: a pergunta *"este fato projeta em
vpn?"* e respondida pelo documento, nunca pelo gerador.

POR QUE ISTO E CORE, E NAO DOMINIO
===================================
`fact_id`, `projections` e os campos de entidade sao forma do CONTRATO
(`contracts/ground_truth.schema.yaml`), nao do academico. Um segundo dominio
(PRONTUS) declara fato com a mesma forma. O que e do dominio e **como** cada
fonte se escreve — o formato de fio —, e isso mora em
`domains/<adapter>/evidence_generators/`. Invariante 1: nada aqui importa de
`domains/`.

A ASSIMETRIA DO ORACULO, DECLARADA
===================================
Para **endereco** a rede e solida: a forma e fechada, entao toda ocorrencia num
arquivo de evidencia ou esta no elenco, ou foi inventada — e `enderecos_no(t) -
elenco.enderecos` e a afirmacao de AUSENCIA que o item 1 cobra.

Para **ator** e **destino** nao ha forma assim. `svc_academus` e `vpn-gw-01` sao
reconheciveis a olho, mas uma rede lexica que os pegasse pegaria tambem palavra
comum do corpo do log, que e texto livre — a sobre-inclusao que `citacoes.py`
aceita de proposito para `fact_id` (onde o alvo tem forma) aqui viraria ruido.
Para eles, `contem()` sustenta a afirmacao de PRESENCA, que e a consistencia
mutua de `06` T13 (*"apresentam usuario, IP e timestamp mutuamente
consistentes"*).

**O que fica de fora das duas:** ator inventado que nao colide com nada. Ele e
alcancado pela reprojecao determinista do `evidence verify` (item 2), e nao por
este modulo. Dito aqui porque um limite nao declarado vira garantia suposta.

O `fact_id` NAO VAI PARA O REGISTRO PROJETADO
==============================================
Carimbar o `fact_id` em cada linha seria a amarracao obvia entre fato e
projecao, e ela esta proibida pelo que o sistema e: o arquivo vai para o time
azul, e `GT-A-014` num `vpn.log` entrega o gabarito na primeira linha (`05` §6).
A amarracao e por CONTEUDO — o elenco —, e essa restricao e a razao de este
modulo existir em vez de um campo a mais no registro.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = ["Elenco", "elenco_de", "cobertura_de", "enderecos_no"]

#: Os campos do fato que nomeiam ENTIDADE do mundo simulado.
#:
#: `contracts/ground_truth.schema.yaml` §`$defs/fact` declara a forma de cada
#: campo, mas nao rotula quais sao entidade — essa distincao e desta camada, e
#: por isso esta declarada aqui e nao derivada.
#:
#: O que fica DE FORA, e por que: `fact_class` e `action` sao rotulo de especie
#: (`initial_access`, `vpn_login`); `exercise_time` e instante;
#: `records_affected` e escalar; `credential_state` e `mfa` sao atributo. Se
#: qualquer um entrasse, o oraculo passaria a aceitar todo numero ou verbo que o
#: gerador escrevesse, e o item 1 deixaria de morder.
CAMPOS_DE_ENTIDADE = ("actor", "dest", "source_ip")

#: Dos tres, o que carrega ENDERECO — o unico com forma fechada, e por isso o
#: unico sobre o qual se afirma ausencia. Ver a assimetria, no cabecalho.
CAMPO_DE_ENDERECO = "source_ip"

#: IPv4 candidato. As fronteiras `(?<![\w.])` e `(?![\w.])` sao o que separa
#: endereco de sequencia de numeros, e cada uma paga um caso adversarial:
#: sem a da esquerda, `1.2.3.4.5` doaria `2.3.4.5`; sem a da direita, doaria
#: `1.2.3.4`. A validacao de faixa fica com `ipaddress` — `999.1.1.1` casa a
#: forma e NAO e endereco, e escrever a faixa na regex a tornaria ilegivel e
#: errada (o mesmo argumento que `ground_truth.schema.yaml` faz sobre CIDR).
_IPV4 = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w.])")

#: IPv6 candidato: dois a oito grupos hex separados por `:`, com ou sem
#: compressao. Deliberadamente SOLTA — quem decide e `ipaddress`, logo abaixo.
#: E por isso que `02:14:07` de um timestamp de syslog nao sobrevive: casa a
#: forma, e nao e endereco (tres grupos sem `::` nao formam IPv6).
_IPV6 = re.compile(r"(?<![\w:.])[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?![\w:])")


@dataclass(frozen=True)
class Elenco:
    """As entidades que o ground truth fixou. Imutavel: e um fato sobre o
    documento, e nada depois da leitura pode acrescentar ator ao mundo."""

    atores: frozenset[str]
    destinos: frozenset[str]
    enderecos: frozenset[str]

    @property
    def todos(self) -> frozenset[str]:
        return self.atores | self.destinos | self.enderecos

    def contem(self, valor: str) -> bool:
        """A afirmacao de PRESENCA — ver a assimetria, no cabecalho."""
        return valor in self.todos


def _facts(ground_truth: Mapping | None) -> Sequence[Mapping]:
    """Os fatos do documento, ou nada.

    Tolera ausencia porque quem chama pode estar conferindo um MANIFEST fora do
    pack — o mesmo caso que `evidence.schema.yaml` nomeia ao separar a forma do
    `fact_id` da resolucao contra `facts`.
    """
    if not ground_truth:
        return ()
    fatos = ground_truth.get("facts")
    return fatos if isinstance(fatos, Sequence) else ()


def elenco_de(ground_truth: Mapping | None) -> Elenco:
    """As entidades que as projecoes podem usar.

    **Todo fato entra, inclusive o que nao projeta.** O fato sem `projections` e
    invisivel ao time azul (`08` §2), mas as entidades dele sao do mundo e outro
    fato pode legitimamente cita-las — um ator que aparece no acesso inicial
    invisivel e de novo na exfiltracao visivel e o caso normal. Exclui-lo faria
    o oraculo recusar projecao correta, que e falso positivo de gate e custa
    mais caro que a cobertura a mais.
    """
    atores: set[str] = set()
    destinos: set[str] = set()
    enderecos: set[str] = set()

    #: UMA declaracao por campo, e o laco a consome. `CAMPOS_DE_ENTIDADE` fixa
    #: QUAIS campos sao entidade; este mapa, em qual balde cada um cai. Iterar
    #: sobre o mapa e nao sobre a constante deixaria a constante decorativa —
    #: declarada e nao consumida e, na pratica, uma segunda fonte que ninguem
    #: confere (R9 §8).
    baldes = {"actor": atores, "dest": destinos, CAMPO_DE_ENDERECO: enderecos}

    for fato in _facts(ground_truth):
        for campo in CAMPOS_DE_ENTIDADE:
            valor = fato.get(campo)
            if isinstance(valor, str) and valor:
                baldes[campo].add(valor)

    return Elenco(frozenset(atores), frozenset(destinos), frozenset(enderecos))


def cobertura_de(ground_truth: Mapping | None) -> dict[str, frozenset[str]]:
    """`fonte -> os `fact_id` que ela projeta`.

    **Fonte sem fato nao aparece.** O retorno nao e o enum do contrato com
    conjuntos vazios: fonte com zero fatos e arquivo que o `evidence build` nao
    tem por que escrever, e declara-la faria a cobertura afirmar existencia de
    um arquivo vazio. `06` T13 cobra o inverso — *"fato sem `projections` nao
    aparece em nenhuma fonte"* —, e as duas metades se encontram aqui.

    Lista vazia e ausencia dizem a mesma coisa: o fato nao projeta. O contrato
    torna o campo opcional para nao exigir a forma vazia, e quem escreve o
    ground truth pode usar qualquer uma das duas.
    """
    por_fonte: dict[str, set[str]] = {}

    for fato in _facts(ground_truth):
        fact_id = fato.get("fact_id")
        projections = fato.get("projections")
        if not isinstance(fact_id, str) or not isinstance(projections, Sequence):
            continue
        for fonte in projections:
            if isinstance(fonte, str) and fonte:
                por_fonte.setdefault(fonte, set()).add(fact_id)

    return {fonte: frozenset(fatos) for fonte, fatos in por_fonte.items()}


def enderecos_no(texto: str) -> set[str]:
    """Todo endereco IP literal do texto, na forma em que aparece.

    A forma em que APARECE, e nao a normalizada: o que se compara depois e com o
    elenco, que carrega o valor tal como o ground truth o escreveu. Normalizar
    aqui faria `2001:0db8::1` e `2001:db8::1` deixarem de ser distinguiveis de
    um lado so, e o gate passaria a aceitar uma reescrita que o gerador nao
    devia ter feito.
    """
    achados: set[str] = set()

    for padrao, tipo in ((_IPV4, ipaddress.IPv4Address), (_IPV6, ipaddress.IPv6Address)):
        for candidato in padrao.findall(texto):
            try:
                tipo(candidato)
            except ValueError:
                continue
            achados.add(candidato)

    return achados
