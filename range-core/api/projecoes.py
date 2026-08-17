"""As projecoes de sala — wallboard, plateia e timeline — e o UNICO serializador.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §5.3 (painel por convencao a partir de `wallboard_group`,
codificacao visual por `category`, indice de saude a partir dos
`severity_weight`) e §6 (wallboard e narrativa para a plateia; participant-view
so com `texto_para_plateia`); `07_IMPLEMENTATION_PHASES.md` Fase 4, itens 2, 3,
5 e 6 da DoD; `06_ACCEPTANCE_TESTS.md` T5 e T6.

POR QUE ESTAS FUNCOES DEVOLVEM `bytes`
---------------------------------------
D3: **o frame do WebSocket e o snapshot HTTP tem de ser o mesmo payload, byte a
byte, para o mesmo estado.** Se divergirem, quem esta na sala e quem acabou de
dar refresh veem coisas diferentes — e ninguem percebe, porque cada um dos dois
esta certo sozinho.

Devolver `dict` e deixar cada rota serializar seria o mesmo fato escrito duas
vezes: o `JSONResponse` do FastAPI nao ordena chaves nem usa os mesmos
separadores que um `json.dumps` escrito a mao, e a diferenca nao aparece em
teste nenhum que compare *estruturas*. Entao a serializacao acontece **aqui, uma
vez**, e as duas rotas entregam os bytes verbatim. E a mesma forma da porta da
peca 3 da Fase 3: em vez de detectar a divergencia, retirar o material com que
ela se escreve.

O SERIALIZADOR E CANONICO, e cada opcao fecha um caminho de divergencia:

    sort_keys=True          ordem de insercao deixa de importar
    separators=(",", ":")   sem espaco, sem variacao de estilo
    ensure_ascii=False      acento vira UTF-8, e nao `\\uXXXX`
    .encode("utf-8")        a fronteira e byte, e nao str

NADA AQUI SABE QUE HORAS SAO
-----------------------------
O payload **nao carrega quando foi gerado**, e isso e decisao e nao omissao: um
carimbo de geracao faz duas serializacoes do MESMO estado diferirem, que e
exatamente a propriedade que esta peca existe para garantir. A sala tambem nao
precisa dele — o que ela le e o estado, nao a hora em que o servidor o montou.

O relogio do exercicio e outra coisa, e vem do evento quando for preciso: ele e
dado do fluxo, nao do momento da montagem.

`tests/test_projecoes.py` afirma isso por ESTRUTURA — este modulo nao importa
`time`, `datetime` nem `random` —, porque afirmar por comportamento exigiria
observar duas montagens em instantes diferentes e concluir por ausencia.

O QUE A SALA NAO PODE VER
--------------------------
`06` T6 e teste de PAYLOAD, e nao de interface: esconder campo no frontend
passaria despercebido ate alguem abrir o DevTools durante o exercicio. As duas
superficies desta peca sao as que `05` §8 isenta de autenticacao — nao ha token
entre elas e a rede —, e por isso a varredura recursiva de chaves roda sobre o
que elas produzem.

**O wallboard nao carrega nome de flag.** `academus.enrollment_offline` e
vocabulario de mecanismo, e a sala precisa VER o sistema cair, nao ler o nome da
alavanca. O que vai para o painel e o `effect_ui`, que `flags.yaml` ja escreve em
linguagem de negocio desde a Fase 1 — a mesma lingua que a peca 5 daquela fase
usou nas mensagens de degradacao.

**A plateia recebe uma unica coisa, e ela chega como `Mapping[str, str]`.** A
funcao nao recebe o inject: recebe `inject_id -> texto_para_plateia`, e nada
mais. `linha`, `descricao_facilitador`, `objectives`, `effects` e
`decision_point` nao estao ao alcance — vazar exigiria mudar o CHAMADOR, e nao
esquecer um filtro aqui. E a D6, e e por isso que `pack_loader.Inject` continua
sem esses campos.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from contracts.generated.events import (
    EXERCISE_PAUSED,
    EXERCISE_RESUMED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from range_core.events.envelope import Event
from range_core.state.simulation_state import SimulationState

#: As chaves do payload. Constantes porque o cliente TypeScript vai le-las e
#: porque teste que compara string solta envelhece sem avisar.
PAINEIS = "paineis"
INDICE_DE_SAUDE = "indice_de_saude"
GRUPO = "grupo"
ITENS = "itens"
ROTULO = "rotulo"
CATEGORIA = "categoria"
SEVERIDADE = "severidade"
ATIVA = "ativa"
INTENSIDADE = "intensidade"
ESTADO = "estado"
TEXTO = "texto"
ENTRADAS = "entradas"

#: O indice de uma sala sem nenhuma flag fora do default.
SAUDE_PLENA = 100

#: `event_type -> rotulo` da timeline. Fechado: evento novo aparece como o
#: proprio `event_type`, e nao some da timeline por nao estar aqui.
ROTULOS = {
    INJECT_FIRED: "inject disparado",
    ROLLBACK_PERFORMED: "ROLLBACK",
    EXERCISE_PAUSED: "exercicio pausado",
    EXERCISE_RESUMED: "exercicio retomado",
}


def serializa(documento: Any) -> bytes:
    """O UNICO serializador. Ver o cabecalho para cada opcao."""
    return json.dumps(
        documento, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def esta_ativa(spec: Mapping, valor: Any) -> bool:
    """A flag saiu do default. **Nao e `valor is True`.**

    `academus.federated_session_active` tem default `true`: quando ela CAI, as
    sessoes federadas foram revogadas e a instituicao esta pior. Ler "ativa" como
    "verdadeira" inverteria o sinal exatamente na flag de identidade — o indice
    de saude MELHORARIA quando o defensor revoga acesso.

    `tests/test_projecoes.py` fixa o sinal com uma flag de default `true` e uma
    de default `false`, exigindo que as duas contribuam na MESMA direcao.
    """
    return valor != spec.get("default")


def intensidade(spec: Mapping, valor: Any) -> float:
    """Quanto da severidade a flag reivindica, entre 0 e 1.

    `boolean` e `enum` sao liga-desliga: fora do default, o peso inteiro.
    `number` e proporcional, normalizado pelos `min`/`max` do contrato — uma
    fracao de sessoes derrubadas de 0,4 nao pesa o mesmo que 1,0.
    """
    if not esta_ativa(spec, valor):
        return 0.0
    if spec.get("type") != "number":
        return 1.0

    minimo = float(spec.get("min", 0))
    maximo = float(spec.get("max", 1))
    if maximo <= minimo:
        return 1.0
    fracao = (float(valor) - minimo) / (maximo - minimo)
    return min(1.0, max(0.0, fracao))


def indice_de_saude(estado: SimulationState, specs: Mapping[str, Mapping]) -> int:
    """`100` menos a fracao do peso total que esta ativa — `01` §5.3.

    A FORMULA E INVENTADA AQUI, e por isso esta escrita aqui: `01` §5.3 pede
    *"numero unico no telao, a partir dos `severity_weight` ativos"* e nao diz
    como. Numero no telao que ninguem sabe reproduzir e pior que numero nenhum.

    Tres propriedades, e as tres tem teste: sem nada fora do default o indice e
    100; peso maior baixa mais; e o resultado sai de `flags.yaml` mais o estado,
    sem nada guardado em lugar nenhum.
    """
    total = sum(float(spec.get("severity_weight", 0)) for spec in specs.values())
    if total <= 0:
        return SAUDE_PLENA

    ativo = sum(
        float(spec.get("severity_weight", 0))
        * intensidade(spec, estado.flags.get(nome, spec.get("default")))
        for nome, spec in specs.items()
    )
    return SAUDE_PLENA - round(SAUDE_PLENA * ativo / total)


def paineis(estado: SimulationState, specs: Mapping[str, Mapping]) -> list[dict]:
    """Os paineis, DERIVADOS de `wallboard_group` — `01` §5.3.

    *"Adicionar flag nao exige tocar no wallboard"* e a promessa da secao, e ela
    so vale se nada aqui souber que paineis existem. Nao ha lista de grupos: eles
    saem do proprio conjunto de flags recebido.

    `tests/test_projecoes.py` planta uma flag com um `wallboard_group` que NAO
    existe e exige o painel novo. Plantar num grupo existente provaria menos: o
    item apareceria por herdar um painel que ja estava la, e uma lista fixa de
    grupos passaria no teste.
    """
    por_grupo: dict[str, list[dict]] = {}
    for nome, spec in specs.items():
        valor = estado.flags.get(nome, spec.get("default"))
        item = {
            # O `effect_ui`, e NAO o nome da flag: a sala le negocio, nao
            # mecanismo. Sem `effect_ui` o item nao entra — flag sem
            # apresentacao nao tem o que mostrar no telao.
            ROTULO: str(spec.get("effect_ui") or ""),
            CATEGORIA: str(spec.get("category") or ""),
            SEVERIDADE: int(spec.get("severity_weight", 0)),
            ATIVA: esta_ativa(spec, valor),
        }
        if not item[ROTULO]:
            continue
        if spec.get("type") == "number":
            item[INTENSIDADE] = intensidade(spec, valor)
        elif spec.get("type") == "enum":
            item[ESTADO] = str(valor)
        por_grupo.setdefault(str(spec.get("wallboard_group") or ""), []).append(item)

    return [
        {GRUPO: grupo, ITENS: sorted(itens, key=lambda i: i[ROTULO])}
        for grupo, itens in sorted(por_grupo.items())
        if grupo
    ]


def wallboard(estado: SimulationState, specs: Mapping[str, Mapping]) -> bytes:
    """A projecao do telao. Sem login, sem nome de flag, sem hora de geracao."""
    return serializa(
        {
            PAINEIS: paineis(estado, specs),
            INDICE_DE_SAUDE: indice_de_saude(estado, specs),
        }
    )


def plateia(eventos: Sequence[Event], textos: Mapping[str, str]) -> bytes:
    """`texto_para_plateia` do inject corrente, e mais nada — `01` §6.

    O inject corrente e o ULTIMO `inject_fired` da epoch corrente. Depois de um
    rollback a plateia volta ao texto do inject que ficou, e nao ao do inject
    descartado: e a mesma linha temporal que o fold reconstroi, lida aqui.

    `textos` e `Mapping[str, str]`, e a estreiteza e a garantia: nao ha
    `descricao_facilitador` ao alcance desta funcao para vazar.
    """
    epoch = max((e.simulation_epoch for e in eventos), default=0)
    corrente = ""
    for evento in eventos:
        if (
            evento.event_type == INJECT_FIRED
            and evento.simulation_epoch == epoch
            and evento.correlation.inject_id is not None
        ):
            corrente = textos.get(evento.correlation.inject_id, "")
    return serializa({TEXTO: corrente})


def timeline(eventos: Sequence[Event]) -> bytes:
    """A linha do tempo do console, com o ROLLBACK anotado — item 5 da DoD.

    A anotacao nao e um rotulo: a entrada carrega o motivo e o ponto de corte, que
    e o que permite ao console renderizar epochs separadas. `09` §3 desenha
    exatamente isso — os eventos da epoch abandonada permanecem, marcados.

    E autenticada (`facilitador`), entao aqui nao ha varredura de vazamento: `03`
    §7 da ao facilitador a timeline integral. O que a sala ve sao as outras duas.
    """
    entradas = []
    for evento in eventos:
        entrada = {
            "epoch": evento.simulation_epoch,
            "exercise_time": evento.exercise_time,
            "tipo": evento.event_type,
            ROTULO: ROTULOS.get(evento.event_type, evento.event_type),
        }
        if evento.correlation.inject_id:
            entrada["inject_id"] = evento.correlation.inject_id
        if evento.event_type == ROLLBACK_PERFORMED:
            entrada["rollback"] = {
                "motivo": evento.payload.get("reason"),
                "para": evento.payload.get("to_inject_id"),
            }
        entradas.append(entrada)
    return serializa({ENTRADAS: entradas})
