"""A superficie do `range-api`, lida em TEMPO DE EXECUCAO.

E a mesma decisao que `domains/academus/api/surface.py` tomou na peca 4 da Fase
3: a declaracao que o gate confere e a MESMA que o processo obedece. Duas listas
— uma para o verificador, outra no codigo — divergem, e a que diverge em
silencio e sempre a que ninguem esta olhando.

O QUE O PROCESSO PRECISA DAQUI
-------------------------------
Uma coisa so: **quais caminhos sao publicos**. `05` §8 isenta de autenticacao
apenas wallboard e participant-view, e a lista de isentos nao pode viver como
`if` espalhado — ela e dado da declaracao.

CASAMENTO EXATO, E NAO POR PADRAO. Todos os caminhos publicos declarados sao
literais; nenhum tem parametro. Se um dia um deles tiver, este modulo recusa a
carga em vez de casar por prefixo — casar por prefixo faria `/wallboard/state`
liberar `/wallboard/state/secreto`, e a falha seria de abertura.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

#: O YAML e DADO DE EXECUCAO, e por isso entra em `package-data`. Resolver por
#: `Path(__file__).parent.parent` funciona na arvore e na instalacao editavel, e
#: quebraria no container — o mesmo erro que a peca 4 da Fase 3 quase cometeu.
#: `__path__` do pacote e o que atravessa os tres casos.
def _caminho() -> Path:
    import range_core  # noqa: PLC0415 — resolve o pacote, e nao o arquivo

    return Path(next(iter(range_core.__path__))) / "api_surface.yaml"


class SuperficieError(Exception):
    """A declaracao nao pode ser obedecida como esta."""


class Superficie:
    """As rotas declaradas, na forma de que o processo precisa."""

    def __init__(self, documento: Mapping) -> None:
        self._rotas = list(documento.get("rotas") or [])
        self._publicas: set[str] = set()
        for rota in self._rotas:
            if not rota.get("publica"):
                continue
            caminho = str(rota.get("path", ""))
            if "{" in caminho:
                raise SuperficieError(
                    f"rota publica {caminho!r} tem parametro. O casamento aqui e "
                    "EXATO de proposito: casar por padrao faria uma rota aberta "
                    "cobrir caminhos que ninguem declarou, e a falha seria de "
                    "abertura"
                )
            self._publicas.add(caminho)

    @classmethod
    def carregar(cls) -> Superficie:
        return cls(yaml.safe_load(_caminho().read_text(encoding="utf-8")) or {})

    def e_publica(self, caminho: str) -> bool:
        """**Falha fechada:** caminho que nao esta na lista exige token."""
        return caminho in self._publicas

    @property
    def publicas(self) -> frozenset[str]:
        return frozenset(self._publicas)
