"""O catalogo de telemetria do adapter — `02` §10, lido e conferido.

AUTORIDADE
----------
`02_DOMAIN_ACADEMUS.md` §10 (os doze eventos e os campos CEF),
`08_EVIDENCE_SIMULATOR.md` §2, e o item 4 da DoD da Fase 9.

O QUE ESTE MODULO FAZ, E O QUE ELE NAO SABE
============================================
Ele carrega o `telemetry_events.yaml` de um adapter e responde **uma** pergunta:

    assinatura_de(fact_class) -> a assinatura de telemetria, ou None

O que ele NAO sabe e QUAL adapter: o caminho chega por parametro, e nao ha
atalho por dominio aqui. O nucleo sabe carregar e conferir; **qual fato do mundo
academico vira qual sinal de SIEM e conhecimento do adapter**, e quem monta o
caminho e `domains/<adapter>/telemetria.py`.

> A primeira versao deste modulo tinha um `do_academus()` que importava
> `domains`, e o hook `check_architecture` o **bloqueou na escrita** —
> invariante 1. O atalho existia por conveniencia de composicao e nao pertencia
> aqui; ele foi para o lado do adapter, que e quem sabe onde mora o proprio
> arquivo. Fica registrado porque a conveniencia era plausivel: e exatamente
> assim que uma fronteira vaza.

A CONFERENCIA CONTRA O CONTRATO E NA CARGA, E NAO DEPOIS
=========================================================
`contracts/events.schema.yaml` §`$defs/telemetry_signature` fecha as doze
assinaturas. Uma assinatura fora dali e `event_type` com erro de digitacao com
outro nome: **nunca dispara**, o sinal nao chega ao SIEM do exercicio, e ninguem
percebe ate a sala. E a falha que `09` §4 chama de "a mais cara possivel", e por
isso a recusa e no momento da carga.

`None` E RESPOSTA VALIDA, E NAO ERRO
=====================================
Fato que nao gera telemetria e caso **normal**: `08` §2 poe o limite de deteccao
no gabarito, e nem todo fato chega ao SIEM. Levantar aqui obrigaria o chamador a
tratar o caso comum como excecao, e o forwarder passaria a decidir o que e
telemetria — decisao que e do catalogo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ARQUIVO",
    "CatalogoInvalido",
    "Entrada",
    "Catalogo",
    "assinaturas_do_contrato",
    "carregar",
]

#: O nome do arquivo, em todo adapter. `02` §10 o fixa.
ARQUIVO = "telemetry_events.yaml"


class CatalogoInvalido(Exception):
    """O catalogo do adapter nao casa o contrato."""


@dataclass(frozen=True)
class Entrada:
    signature: str
    severity: int
    outcome: str | None
    fact_class: str | None


@dataclass(frozen=True)
class Catalogo:
    """O catalogo de um adapter. Imutavel: e um fato sobre o documento."""

    entradas: tuple[Entrada, ...]

    def assinaturas(self) -> tuple[str, ...]:
        return tuple(e.signature for e in self.entradas)

    def assinatura_de(self, fact_class: str) -> str | None:
        """A assinatura que este `fact_class` dispara, ou `None`."""
        entrada = self.entrada_de(fact_class)
        return entrada.signature if entrada else None

    def entrada_de(self, fact_class: str) -> Entrada | None:
        for entrada in self.entradas:
            if entrada.fact_class == fact_class:
                return entrada
        return None


def assinaturas_do_contrato(contratos: dict[str, dict]) -> tuple[str, ...]:
    """As doze assinaturas de `02` §10, LIDAS do contrato.

    Mesma forma de `contract_source.rollback_reasons`: recebe os contratos ja
    parseados, busca, nao toca disco. Reescrever a lista aqui seria a copia que
    esta fase passou inteira evitando.
    """
    eventos = contratos.get("events") or {}
    enum = ((eventos.get("$defs") or {}).get("telemetry_signature") or {}).get("enum")
    if not enum:
        raise CatalogoInvalido(
            "contracts/events.schema.yaml sem `$defs/telemetry_signature`: "
            "sem o conjunto fechado, o catalogo do adapter aceitaria qualquer "
            "assinatura e o sinal nao chegaria ao SIEM do exercicio"
        )
    return tuple(enum)


def carregar(caminho: Path, *, contratos: dict[str, dict]) -> Catalogo:
    """Le o `telemetry_events.yaml` de um adapter e o confere contra o contrato."""
    import yaml

    if not caminho.exists():
        raise CatalogoInvalido(
            f"{caminho} ausente: `02` §10 declara os eventos de telemetria do "
            f"adapter, e sem o catalogo nenhum fato vira sinal"
        )

    documento = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    eventos = documento.get("events")
    if not isinstance(eventos, Sequence) or not eventos:
        raise CatalogoInvalido(f"{caminho} sem `events`: catalogo vazio nao emite nada")

    permitidas = set(assinaturas_do_contrato(contratos))
    entradas: list[Entrada] = []
    vistas: set[str] = set()

    for bruto in eventos:
        if not isinstance(bruto, Mapping):
            raise CatalogoInvalido(f"{caminho}: entrada que nao e mapa — {bruto!r}")
        assinatura = bruto.get("signature")
        if assinatura not in permitidas:
            raise CatalogoInvalido(
                f"{caminho}: assinatura fora do catalogo do contrato — "
                f"{assinatura!r}. As doze de `02` §10 estao em "
                f"`events.schema.yaml` §`$defs/telemetry_signature`"
            )
        if assinatura in vistas:
            raise CatalogoInvalido(
                f"{caminho}: assinatura declarada duas vezes — {assinatura!r}. "
                f"A segunda seria inalcancavel, e um `fact_class` novo iria "
                f"para a primeira sem que ninguem visse"
            )
        vistas.add(assinatura)
        entradas.append(
            Entrada(
                signature=assinatura,
                severity=int(bruto.get("severity", 0)),
                outcome=bruto.get("outcome"),
                fact_class=bruto.get("fact_class"),
            )
        )

    return Catalogo(tuple(entradas))
