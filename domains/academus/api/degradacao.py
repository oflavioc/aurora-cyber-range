"""A degradacao por flag — declarada na rota, executada aqui, e em lugar nenhum mais.

A D4, DECIDIDA DE VERDADE
-------------------------
A Fase 2 recusou `if` espalhado e pos o efeito na declaracao do pack. Aqui a
declaracao ja tinha casa desde a peca 2 — `api_surface.yaml` diz QUAL flag cada
rota consulta —, e o que faltava era **o que a flag faz com a rota**. Isso agora
e dado: `condicao`, `efeito`, `status`, `mensagem`, `segundos`.

**Nenhum handler contem `if flag`.** A degradacao e uma dependencia GLOBAL, como
`autoriza`: ela roda antes da path operation, le a declaracao da rota que o
FastAPI casou, e levanta ou dorme. O handler nao recebe estado de simulacao,
nao importa flag nenhuma e nao tem por onde saber que foi degradado — do mesmo
jeito que ele nao tem por onde saber por que alguem foi negado.

E a forma da peca 3 outra vez: em vez de detectar `if flag:` no handler, o
handler **nao tem** flag ao alcance. `scripts/check_api_surface.py` fecha a
outra metade — este e o unico modulo de `api/` autorizado a importar
`range_core.state`, e nenhum modulo de `api/` pode importar as constantes de
flag geradas, porque o nome da flag chega como DADO da declaracao.

A MENSAGEM E DE NEGOCIO, E ISSO E REQUISITO E NAO ESTILO
---------------------------------------------------------
O exercicio inteiro depende de a sala **ver** o sistema cair, e nao de ler um
aviso dizendo que ele foi derrubado. Uma resposta com "flag ativa" no corpo
transforma exercicio em demonstracao, e destroi a assimetria que `00` §5 chama
de desenho.

`flags.yaml` ja escrevia a apresentacao em linguagem de negocio, no campo
`effect_ui` — *"Lancamento e alteracao de nota recusados; leitura e historico
seguem disponiveis"*. As mensagens daqui sao a mesma lingua, dirigidas ao
participante. A checagem recusa mensagem que nomeie flag ou mecanismo, e
`tests/test_api_degradacao.py` varre a **resposta inteira**, corpo e cabecalhos,
na forma que `06` T6 fixa para isolamento de papel.

`proporcional` E COTA DETERMINISTA, E NAO SORTEIO
---------------------------------------------------
`academus.lms_session_drop_rate` e `number` de 0 a 1 — *"fracao de sessoes
derrubadas"*. A implementacao obvia seria sortear a cada request, e ela esta
errada por um motivo que `range-core/determinism.py` ja documenta: um fluxo
consumido por request e **dependente de ordem**, e duas execucoes do mesmo
exercicio com o mesmo `RANDOM_SEED` divergiriam por qualquer diferenca no
trafego. `seeded_random` foi escrito com escopo justamente para que ordem
deixasse de ser variavel; um consumidor por request seria o primeiro a
reintroduzi-la.

A cota acumulada da exatamente `floor(n * taxa)` recusas em `n` requisicoes,
distribuidas por igual, sem sorteio nenhum. Reproduzivel, e o facilitador
consegue prever o efeito — o que num exercicio e virtude, nao limitacao.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from range_core.events.store import EventStore
from range_core.state.cache import SimulationStateCache, current
from range_core.state.simulation_state import Declarations, SimulationState

from domains.academus.api.surface import Degradacao, RotaDeclarada

#: As duas condicoes e os dois efeitos. Vocabulario FECHADO — a checagem recusa
#: qualquer outra palavra, pelo mesmo motivo que o catalogo de `event_type` e
#: fechado: valor novo que ninguem implementou vira degradacao que nao acontece.
LIGADA = "ligada"
PROPORCIONAL = "proporcional"
RECUSA = "recusa"
LATENCIA = "latencia"

CONDICOES = frozenset({LIGADA, PROPORCIONAL})
EFEITOS = frozenset({RECUSA, LATENCIA})


@dataclass(frozen=True, slots=True)
class LeituraDeEstado:
    """O estado de simulacao, pela porta da peca 3. **O unico caminho.**

    `current` le a cabeca do fluxo ANTES da projecao e reconstroi quando o cache
    nao vale — nada disso e reimplementado aqui, e e por isso que este objeto e
    tao pequeno: ele e um wiring, nao uma politica.
    """

    store: EventStore
    declarations: Declarations
    cache: SimulationStateCache

    def estado(self) -> SimulationState:
        return current(self.store, self.declarations, self.cache)


@dataclass
class Cota:
    """A cota acumulada de `proporcional`, por (rota, flag).

    Mutavel de proposito: e a unica coisa com memoria nesta borda, e a memoria e
    o que faz `floor(n * taxa)` sair exato em vez de aproximado.
    """

    acumulado: dict[tuple[str, str], float] = field(default_factory=dict)

    def vence(self, chave: tuple[str, str], taxa: float) -> bool:
        if taxa <= 0:
            return False
        total = self.acumulado.get(chave, 0.0) + taxa
        if total >= 1.0:
            self.acumulado[chave] = total - 1.0
            return True
        self.acumulado[chave] = total
        return False


@dataclass
class Degradador:
    """Aplica a degradacao declarada. Montado uma vez, no boot.

    `dormir` e parametro pela mesma razao que `now` e parametro no relogio e no
    token: o teste precisa afirmar que a latencia DECLARADA foi aplicada, e
    esperar 2,5 s de verdade para descobrir isso seria pagar o tempo do
    exercicio dentro da suite. Nao e duplo de biblioteca — e a costura de tempo
    que este projeto ja usa em dois lugares.
    """

    leitura: LeituraDeEstado
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep
    cota: Cota = field(default_factory=Cota)

    def _dispara(self, entrada: Degradacao, estado: SimulationState, rota: str) -> bool:
        valor = estado.flags.get(entrada.flag)
        if entrada.condicao == LIGADA:
            return valor is True
        return self.cota.vence((rota, entrada.flag), float(valor or 0.0))

    async def aplica(self, rota: RotaDeclarada) -> None:
        """Percorre as entradas NA ORDEM DECLARADA e para na primeira recusa.

        A ordem importa e e a da declaracao: no diario, a latencia vem antes da
        queda de sessao, e e assim que o participante vive — o sistema fica
        lento, e depois derruba. Inverter faria a recusa acontecer sem espera, e
        a sala leria "fora do ar" em vez de "degradado".
        """
        if not rota.degradacao:
            return

        estado = self.leitura.estado()
        for entrada in rota.degradacao:
            if not self._dispara(entrada, estado, rota.path):
                continue
            if entrada.efeito == LATENCIA:
                await self.dormir(entrada.segundos)
            else:
                raise HTTPException(status_code=entrada.status, detail=entrada.mensagem)


async def degrada(request: Request) -> None:
    """Dependencia global. Roda DEPOIS de `autoriza`, e a ordem e deliberada.

    Degradar antes de autenticar entregaria o estado da simulacao a quem nem
    token tem: um 503 de matricula responderia "a flag esta ligada" para
    qualquer um na rede. As dependencias globais rodam na ordem declarada, e a
    aplicacao as declara nessa.
    """
    degradador: Degradador | None = getattr(request.app.state, "degradador", None)
    if degradador is None:
        return

    rota = request.scope.get("route")
    declarada = (
        None
        if rota is None
        else request.app.state.autenticacao.superficie.rota(
            request.method, getattr(rota, "path", "")
        )
    )
    if declarada is not None:
        await degradador.aplica(declarada)
