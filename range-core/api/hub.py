"""O empurrador de frames — UM frame por evento, e nao um por cliente.

AUTORIDADE
----------
`07_IMPLEMENTATION_PHASES.md` Fase 4, item 2 da DoD (*"wallboard atualiza em
< 1 s via WebSocket"*) e item 3 (*"refresh do browser recupera o estado
corrente"*); `01_ARCHITECTURE.md` §6.

O QUE "< 1 s" QUER DIZER AQUI, E POR QUE NAO E MILISSEGUNDO
-------------------------------------------------------------
Numero de relogio oscila com a maquina, e um teste que afirme `< 1 s` em
milissegundos ou e frouxo demais para pegar defeito ou intermitente. A forma que
este projeto ja usou para o mesmo problema foi o `EXPLAIN` sem `Seq Scan` do
`_head()`: **afirmar a propriedade que produz o desempenho, e nao o desempenho.**

Aqui a propriedade tem duas metades, e as duas sao contaveis:

1. **NAO HA ESPERA.** O frame e produzido na MESMA chamada que gravou o evento.
   Nao ha laco de polling, nao ha intervalo, nao ha tarefa de fundo — e por isso
   nao ha nada que possa ser configurado com um numero grande demais.
2. **UM FRAME POR EVENTO, E NAO UM POR CLIENTE.** `publicar` monta cada projecao
   UMA VEZ e entrega os mesmos bytes a todos os inscritos. Com dez telas na sala,
   o custo e o mesmo de uma — e o teste conta as leituras do store para provar
   isso, em vez de cronometrar.

**O LIMITE, DECLARADO E COM NUMERO.** O custo de um frame e o de uma
reconstrucao da projecao, porque a cabeca do fluxo mudou. A §3.8 do registro da
Fase 2 mediu: **2,874 s em 150 mil eventos**. Entao o orcamento de 1 s vale
enquanto o volume couber nele, e o DEMO desta fase roda com dezenas de eventos.
Fold incremental — partir do estado em cache e aplicar so o evento novo — seria
a saida, e ela NAO e desta fase: exigiria uma porta que aceita estado pronto, que
e exatamente o que a peca 3 da Fase 3 tirou do desenho.

A FILA E POR CLIENTE, E O QUE ELA GUARDA E O ULTIMO
-----------------------------------------------------
Cada inscrito tem uma fila de tamanho 1: chegando frame novo com o anterior
ainda nao entregue, o anterior e DESCARTADO. Nao ha o que perder — o frame e
estado TOTAL (D3), entao o mais novo contem tudo o que o antigo dizia. Guardar a
fila inteira faria uma tela lenta acumular historia que ninguem quer ver.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping


class Hub:
    """Inscricao por projecao, e um frame por evento.

    `produtores` chega por parametro — `nome -> () -> bytes` —, e o hub nao sabe
    o que e wallboard nem o que e plateia. Ele so sabe que ha projecoes, que elas
    produzem bytes e que quem esta inscrito recebe os mesmos bytes.
    """

    def __init__(self, produtores: Mapping[str, Callable[[], bytes]]) -> None:
        self._produtores = dict(produtores)
        self._filas: dict[str, list[asyncio.Queue[bytes]]] = {
            nome: [] for nome in produtores
        }

    def projecoes(self) -> frozenset[str]:
        return frozenset(self._produtores)

    def inscrever(self, projecao: str) -> asyncio.Queue[bytes]:
        fila: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
        self._filas[projecao].append(fila)
        return fila

    def cancelar(self, projecao: str, fila: asyncio.Queue[bytes]) -> None:
        if fila in self._filas[projecao]:
            self._filas[projecao].remove(fila)

    def inscritos(self, projecao: str) -> int:
        return len(self._filas[projecao])

    def frame(self, projecao: str) -> bytes:
        """O estado corrente daquela projecao. E o MESMO que o snapshot HTTP."""
        return self._produtores[projecao]()

    def publicar(self) -> None:
        """Monta cada projecao UMA VEZ e entrega a todos os inscritos.

        Sincrona de proposito: quem chama e o handler que acabou de gravar o
        evento, e o frame tem de sair antes de a resposta HTTP voltar. Async aqui
        criaria uma janela em que o disparo ja respondeu e a sala ainda nao viu.

        **So monta projecao que tem alguem ouvindo.** Sem inscrito, montar seria
        pagar uma reconstrucao para jogar fora.
        """
        for projecao, filas in self._filas.items():
            if not filas:
                continue
            bytes_do_frame = self.frame(projecao)
            for fila in filas:
                if fila.full():
                    # O anterior ainda nao foi entregue. Descartar e correto: o
                    # frame e estado TOTAL, entao o novo contem tudo o que o
                    # antigo dizia.
                    fila.get_nowait()
                fila.put_nowait(bytes_do_frame)
