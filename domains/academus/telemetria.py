"""O catalogo de telemetria do ACADEMUS — `02` §10, do lado do adapter.

POR QUE ESTE MODULO EXISTE, E NAO UM ATALHO NO NUCLEO
======================================================
`range_core.telemetry.catalogo.carregar` recebe um CAMINHO. Quem sabe onde mora
o `telemetry_events.yaml` do ACADEMUS e o ACADEMUS.

A primeira versao punha um `do_academus()` dentro do nucleo, por conveniencia de
composicao — e o hook `check_architecture` **bloqueou a escrita**: invariante 1,
`range-core/` nao importa de `domains/`. O atalho nao mudou de forma, mudou de
lado. Fica registrado porque a conveniencia era plausivel, e e assim que uma
fronteira vaza.

O PADRAO E O MESMO DA TABELA DE GERADORES: o adapter monta, o nucleo consome.
"""

from __future__ import annotations

from pathlib import Path

from range_core.telemetry.catalogo import ARQUIVO, Catalogo, carregar

__all__ = ["CAMINHO", "catalogo"]

#: Ao lado deste modulo, como `flags.yaml` e `observability_hooks.yaml`.
CAMINHO = Path(__file__).resolve().parent / ARQUIVO


def catalogo(contratos: dict[str, dict]) -> Catalogo:
    """O catalogo do ACADEMUS, conferido contra o contrato na carga."""
    return carregar(CAMINHO, contratos=contratos)
