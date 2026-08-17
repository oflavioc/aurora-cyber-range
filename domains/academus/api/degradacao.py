"""A degradacao por flag — declarada na rota, executada aqui, e em lugar nenhum mais.

A D4, DECIDIDA DE VERDADE
-------------------------
A Fase 2 recusou `if` espalhado e pos o efeito na declaracao do pack. Aqui a
declaracao ja tinha casa desde a peca 2 da Fase 3 — `api_surface.yaml` diz QUAL
flag cada rota consulta —, e o que faltava era **o que a flag faz com a rota**.
Isso agora e dado: `condicao`, `efeito`, `status`, `mensagem`, `segundos`.

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
`effect_ui`. As mensagens daqui sao a mesma lingua, dirigidas ao participante. A
checagem recusa mensagem que nomeie flag ou mecanismo, e
`tests/test_api_degradacao.py` varre a **resposta inteira**, corpo e cabecalhos,
na forma que `06` T6 fixa para isolamento de papel.

`proporcional` — A P3-10: O ACUMULADOR SAIU, E NAO MUDOU DE LUGAR
------------------------------------------------------------------
Ate a peca 4 desta fase, `proporcional` era uma **cota acumulada** guardada na
instancia do `Degradador`, chaveada por `(rota, flag)`. Ela dava `floor(n*taxa)`
recusas exatas em `n` requisicoes, e essa exatidao era o argumento a favor dela.

O argumento contra e maior, e sao **duas consequencias que se somam**: o
acumulador e estado mutavel fora das cinco camadas de `01` §4 — reinicio o zera
—, e **rollback devolve a flag sem devolver a memoria**. A segunda e a que
ninguem veria: o facilitador rebobina, a taxa volta ao valor anterior, e o
conjunto de quem cai passa a ser outro. Nada fica vermelho; a sala so vive um
exercicio diferente do que o facilitador restaurou.

**Persistir o acumulador seria a saida errada.** Business State e *"notas,
matriculas, submissoes, documentos"* — um contador de recusas nao e isso —, e
deriva-lo do event store exigiria um evento por requisicao, que e Fase 5
(trilha) e Fase 8 (instrumentacao).

**A forma nova elimina o estado em vez de realoca-lo**, e e mais fiel ao que a
flag declara: `flags.yaml` fala em *"fracao de sessoes de prova em andamento
derrubadas"*, e cota por requisicao derruba a MESMA sessao de forma
intermitente, que nao e o que esta escrito. A funcao e determinista e sem
memoria — a sessao cai quando `h(RANDOM_SEED, rota, flag, sujeito) < taxa` — e
as quatro propriedades sao as da D9:

    sem estado             nao ha o que ficar fora das cinco camadas
    estavel no reinicio    o mesmo exercicio, o mesmo conjunto de sessoes
    estavel no rollback    a taxa volta, e EXATAMENTE as mesmas sessoes voltam
    monotona na taxa       subir a taxa so acrescenta; nunca troca o conjunto

**Dois limites, ditos porque sao limites.**

`floor(n·taxa)` exato deixa de valer. O que passa a valer e a fracao sobre o
conjunto de **sujeitos**, que e o que a flag diz — com poucos sujeitos, a fracao
observada e granulada pelo tamanho do conjunto, do mesmo jeito que uma moeda em
tres lancamentos nao da metade.

E o `effect_ui` da flag termina em *"por minuto"*, que esta funcao **nao
implementa**: quem cai, cai o exercicio inteiro, e nao um punhado novo a cada
minuto. Implementar a cadencia exigiria tempo como entrada, que e exatamente o
estado que a P3-10 tirou daqui. O consumidor que da sentido a cadencia e o Modo
"Prova em andamento" de `07` Fase 8, e a divergencia esta registrada na P4-6 em
vez de ficar sem dono.

A DERIVACAO NAO USA `hash()`, E O MOTIVO JA ESTAVA ESCRITO
------------------------------------------------------------
`range-core/determinism.py` documenta: `hash()` de string e salgado por
`PYTHONHASHSEED` e **muda entre processos**. Usa-lo aqui produziria um conjunto
de sessoes diferente a cada boot — a propriedade "estavel no reinicio" falharia
exatamente onde ela e cobrada, e so em execucao separada. Por isso a derivacao e
`derive_seed`, que ja existe e ja e SHA-256: uma segunda derivacao ao lado seria
a classe D4 outra vez.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request

from range_core.determinism import derive_seed
from range_core.events.store import EventStore
from range_core.state.cache import SimulationStateCache, current
from range_core.state.simulation_state import Declarations, SimulationState

from domains.academus.api.surface import Degradacao, RotaDeclarada, Superficie

#: As duas condicoes e os dois efeitos. Vocabulario FECHADO — a checagem recusa
#: qualquer outra palavra, pelo mesmo motivo que o catalogo de `event_type` e
#: fechado: valor novo que ninguem implementou vira degradacao que nao acontece.
LIGADA = "ligada"
PROPORCIONAL = "proporcional"
RECUSA = "recusa"
LATENCIA = "latencia"

CONDICOES = frozenset({LIGADA, PROPORCIONAL})
EFEITOS = frozenset({RECUSA, LATENCIA})

#: O espaco de `derive_seed`: ele devolve os 8 primeiros bytes do digest como
#: inteiro sem sinal. Dividir por ele leva a fracao para `[0, 1)`.
ESPACO = 2**64

#: O arquivo que declara as flags do adapter. Nomeado na mensagem da guarda de
#: boot, porque `06` T2 exige *"mensagem nomeando flag E ARQUIVO ESPERADO"* — e
#: quem le a recusa precisa saber onde escrever a declaracao que falta.
ARQUIVO_DE_FLAGS = "domains/academus/flags.yaml"


class FlagNaoDeclarada(Exception):
    """A P3-11. Flag citada na superficie e ausente do estado corrente.

    RECUSA ALTA, NO BOOT, e nao no meio do exercicio. `estado.flags.get(nome)`
    devolvia `None` para flag que as declaracoes nao trazem — e entao `ligada`
    nunca disparava e `proporcional` lia `0.0`. **A rota nao degradava, e nada
    avisava.** O gate do CI protege o repositorio; isto protege o exercicio em
    curso, que e outra coisa.

    A forma e a que `06` T2 ja exige do loader do engine, aplicada ao adapter no
    ponto em que ele e montado, e e `01` §5.4 — *"nenhum servico le ou escreve
    flag nao declarada"* — deixando de ser verdade so no repositorio.
    """


@dataclass(frozen=True, slots=True)
class LeituraDeEstado:
    """O estado de simulacao, pela porta da peca 3 da Fase 3. **O unico caminho.**

    `current` le a cabeca do fluxo ANTES da projecao e reconstroi quando o cache
    nao vale — nada disso e reimplementado aqui, e e por isso que este objeto e
    tao pequeno: ele e um wiring, nao uma politica.
    """

    store: EventStore
    declarations: Declarations
    cache: SimulationStateCache

    def estado(self) -> SimulationState:
        return current(self.store, self.declarations, self.cache)


def fracao_do_sujeito(seed: int, rota: str, flag: str, sujeito: str) -> float:
    """A posicao fixa de um sujeito em `[0, 1)`, para esta rota e esta flag.

    Pura, estavel entre processos e independente de ordem, volume e historico. E
    o que substitui o acumulador: em vez de lembrar quantas caíram, cada sujeito
    **ja tem** o seu lugar na fila, e a taxa so decide onde a fila e cortada.

    A flag entra na derivacao porque duas flags proporcionais sobre a mesma rota
    sao dois fenomenos: se compartilhassem o conjunto, ligar a segunda nao
    atingiria ninguem novo, e o facilitador leria isso como a flag nao
    funcionando.
    """
    return derive_seed(seed, f"{rota}|{flag}|{sujeito}") / ESPACO


def cai(seed: int, rota: str, flag: str, sujeito: str, taxa: float) -> bool:
    """`taxa` fracao dos sujeitos cai — sempre os mesmos, para a mesma taxa.

    MONOTONA POR CONSTRUCAO: o corte e `<`, entao subir a taxa so pode mover
    sujeitos de fora para dentro. Nao ha caminho pelo qual alguem que caia com
    0,4 pare de cair com 0,6 — que e a propriedade que um sorteio por requisicao
    nao tem, e que a cota acumulada tinha por acidente do acumulador.
    """
    if taxa <= 0:
        return False
    return fracao_do_sujeito(seed, rota, flag, sujeito) < taxa


def confere_flags_declaradas(superficie: Superficie, declarations: Declarations) -> None:
    """A guarda de boot da P3-11. Chamada por `montar`, e nao por rota.

    DUAS CONDICOES, e a segunda nao e a mesma coisa dita de outro jeito:

    1. **flag citada e nao declarada** — a rota nao degradaria, em silencio;
    2. **`proporcional` em rota publica** — nao haveria sujeito, e a queda de
       sessao nunca aconteceria. O sujeito vem do `sub` do token, e rota publica
       nao tem token. E o mesmo no-op da primeira, entrando pela outra porta.

    A segunda e decidivel aqui e so aqui: em tempo de requisicao ela apareceria
    como "ninguem cai", que e indistinguivel de taxa zero.
    """
    problemas: list[str] = []
    declaradas = set(declarations.flag_defaults)

    for rota in superficie.rotas.values():
        citadas = set(rota.flags) | {d.flag for d in rota.degradacao}
        for flag in sorted(citadas - declaradas):
            problemas.append(
                f"{rota.method} {rota.path}: cita a flag {flag!r}, que o estado "
                f"corrente nao declara.\n"
                f"    Declare-a em `{ARQUIVO_DE_FLAGS}`. Sem isso a rota le "
                "`None`, nao degrada, e nada avisa — `01` §5.4 diz que nenhum "
                "servico le flag nao declarada."
            )
        if rota.publica:
            for entrada in rota.degradacao:
                if entrada.condicao == PROPORCIONAL:
                    problemas.append(
                        f"{rota.method} {rota.path}: e publica e declara "
                        f"{PROPORCIONAL!r} sobre {entrada.flag!r}.\n"
                        "    O sujeito vem do `sub` do token, e rota publica nao "
                        "tem token: a queda de sessao nunca aconteceria, e isso "
                        "se pareceria com taxa zero."
                    )

    if problemas:
        raise FlagNaoDeclarada(
            "a `academus-api` nao pode subir:\n\n" + "\n\n".join(problemas)
        )


@dataclass
class Degradador:
    """Aplica a degradacao declarada. Montado uma vez, no boot.

    `seed` e CAMPO OBRIGATORIO, e nao lido do ambiente aqui dentro: quem monta o
    processo sabe onde o `.env` esta, e um adapter que fosse procurar arquivo
    repetiria a armadilha que a §3.2 do registro da Fase 2 mediu com
    `contracts/`. A recusa alta na ausencia acontece no boot — `random_seed()`
    levanta `SeedUnavailable` —, que e onde ela e visivel.

    `dormir` e parametro pela mesma razao que `now` e parametro no relogio e no
    token: o teste precisa afirmar que a latencia DECLARADA foi aplicada, e
    esperar 2,5 s de verdade para descobrir isso seria pagar o tempo do
    exercicio dentro da suite. Nao e duplo de biblioteca — e a costura de tempo
    que este projeto ja usa em tres lugares.

    **Nao ha mais campo mutavel aqui.** Era a `Cota`, e a P3-10 a removeu.
    """

    leitura: LeituraDeEstado
    seed: int
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep

    def _dispara(
        self,
        entrada: Degradacao,
        estado: SimulationState,
        rota: str,
        sujeito: str | None,
    ) -> bool:
        valor = estado.flags.get(entrada.flag)
        if entrada.condicao == LIGADA:
            return valor is True
        if sujeito is None:
            # Nao deveria ocorrer: `confere_flags_declaradas` recusa o boot de
            # rota publica com `proporcional`. Fica como falha FECHADA e nao
            # como `assert`, porque uma rota nova declarada errada nao pode
            # derrubar a aplicacao no meio da sala — ela deixa de degradar, e o
            # boot e quem grita.
            return False
        return cai(self.seed, rota, entrada.flag, sujeito, float(valor or 0.0))

    async def aplica(self, rota: RotaDeclarada, sujeito: str | None) -> None:
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
            if not self._dispara(entrada, estado, rota.path, sujeito):
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

    E e a ordem que torna o SUJEITO disponivel: `autoriza` resolve
    `request.state.escopo` a partir das claims verificadas, entao o `sub` que
    chega aqui e o de um token que ja foi conferido. Ler o cabecalho `Bearer`
    por conta propria seria confiar num `sub` nao verificado para decidir quem
    cai — e ai qualquer participante escolheria nao cair.
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
    if declarada is None:
        return

    escopo = getattr(request.state, "escopo", None)
    await degradador.aplica(declarada, None if escopo is None else escopo.sub)
