"""A superficie declarada, lida em TEMPO DE EXECUCAO pelo proprio adapter.

POR QUE O CODIGO LE O MESMO ARQUIVO QUE O GATE CONFERE
-------------------------------------------------------
`api_surface.yaml` nasceu na peca 2 como declaracao conferida por
`scripts/check_api_surface.py`. A peca 4 faz dele tambem a FONTE do RBAC — e a
diferenca e grande.

Se cada rota carregasse o seu proprio `if papel not in (...)`, a checagem
continuaria verde enquanto o codigo exigisse um papel diferente do declarado: a
lista diria `[aluno, secretaria]` e o handler exigiria `professor`, e nada
cruzaria os dois. A declaracao viraria comentario com sintaxe de YAML.

Lendo daqui, **a divergencia deixa de ser possivel** em vez de passar a ser
detectavel. E a mesma forma que a peca 3 usou na porta do cache, e a mesma que a
D4 reserva para a degradacao: declarativo, nao espalhado.

RESOLUCAO DO CAMINHO PELO `__path__` DO PACOTE
-----------------------------------------------
Nao por `Path(__file__).parent.parent`. A §3.2 do registro da Fase 2 mediu essa
armadilha com `contracts/`: caminho relativo ao arquivo funciona na arvore e
falha na instalacao, e a falha aparece longe da causa — no container da Fase 4.
`domains.academus.__path__` cobre os dois casos, e o `pyproject.toml` ganhou a
entrada de `package-data` no mesmo commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

import domains.academus as _pacote

ARQUIVO = "api_surface.yaml"


@dataclass(frozen=True, slots=True)
class RotaDeclarada:
    """Uma linha de `rotas:`, ja normalizada.

    `papeis` VAZIO NAO SIGNIFICA "todo mundo" — significa ninguem. Rota publica
    e declarada com `publica: true`, e a checagem recusa as duas incoerencias
    (publica com papeis, e vazia sem publica).

    A alternativa — vazio querendo dizer aberto — inverte o sentido no caso mais
    perigoso: uma rota que PERDESSE seus papeis por edicao descuidada ficaria
    aberta em vez de fechada.
    """

    method: str
    path: str
    papeis: frozenset[str]
    publica: bool
    flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Superficie:
    papeis_de_dominio: frozenset[str]
    claims: tuple[str, ...]
    rotas: Mapping[tuple[str, str], RotaDeclarada]

    def rota(self, method: str, path: str) -> RotaDeclarada | None:
        return self.rotas.get((method.upper(), path))


def _caminho() -> Path:
    for entrada in _pacote.__path__:
        candidato = Path(entrada) / ARQUIVO
        if candidato.is_file():
            return candidato
    raise FileNotFoundError(
        f"{ARQUIVO} nao encontrado em __path__={list(_pacote.__path__)!r}. "
        "Na instalacao, ele vem por `package-data` do `pyproject.toml`."
    )


def carregar() -> Superficie:
    """Le e normaliza. Sem cache: quem monta a aplicacao chama uma vez."""
    documento = yaml.safe_load(_caminho().read_text(encoding="utf-8")) or {}

    rotas: dict[tuple[str, str], RotaDeclarada] = {}
    for bruta in documento.get("rotas") or []:
        rota = RotaDeclarada(
            method=str(bruta["method"]).upper(),
            path=str(bruta["path"]),
            papeis=frozenset(bruta.get("papeis") or []),
            publica=bool(bruta.get("publica", False)),
            flags=tuple(bruta.get("flags") or []),
        )
        rotas[(rota.method, rota.path)] = rota

    return Superficie(
        papeis_de_dominio=frozenset(documento.get("papeis_de_dominio") or []),
        claims=tuple((documento.get("token") or {}).get("claims") or []),
        rotas=rotas,
    )
