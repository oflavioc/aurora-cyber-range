#!/usr/bin/env python3
"""Prova negativa de `06` T9: a checagem reprova hook sem emissor, nas quatro direcoes.

Mesma doutrina do harness da Fase 0 e de `check_insumo_de_metrica_probes.py` —
checagem que nunca reprovou prova que a arvore passa, nao que ela enxerga. Aqui a
frase tem endereco: ate a Fase 6 NAO HAVIA checagem nenhuma sobre este eixo, e
`vpn_access_revoked` atravessou tres auditorias declarado e sem produtor.

O DEFEITO E PLANTADO EM ARVORE MONTADA, NUNCA EM `domains/`
------------------------------------------------------------
Cada caso escreve um `domains/` inteiro em diretorio temporario e aponta a
checagem para ele, pelo caminho opcional de CLI. Plantar no arquivo real e
restaurar depois e fragil pelo motivo obvio: falha no meio deixa a arvore suja.

O caso e uma arvore e nao um trecho mutado porque o objeto da checagem SAO DOIS
arquivos — o YAML e o Python que emite —, e o defeito mora na relacao entre eles.

O POSITIVO NAO E DECORACAO
---------------------------
Sem ele, uma checagem que reprovasse todo adapter passaria em todos os negativos.
Sao dois: o adapter coerente PASSA, e a arvore real PASSA — a segunda e a que
pega o probe que so exercita fixture e nunca olhou para `domains/` de verdade.

E o de VACUIDADE, que e o modo de falha proprio desta checagem: um `domains/` sem
`observability_hooks.yaml` nenhum nao pode sair 0. Nada a conferir teria de ser
recusa, e nao aprovacao — foi o que os dois predicados de base aposentados
fizeram errado, cada um a sua maneira.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_hooks_com_emissor as checagem  # noqa: E402
from check_hooks_com_emissor import Produtor, main  # noqa: E402

#: O PRODUTOR DO NUCLEO tem outra forma, e por isso tem casos proprios — H2 da
#: setima auditoria. Na `participant-api` o `event_type` nao chega ao
#: `EventDraft` como constante do catalogo: ele e o quarto POSICIONAL de
#: `_declara`, porque UMA funcao serve as nove rotas e quem escolhe o tipo e o
#: handler. Um probe que so exercitasse a forma do adapter deixaria essa metade
#: sem prova, e ela e justamente a que nasceu agora.
APP_DO_NUCLEO = '''
from contracts.generated.events import INCIDENT_DECLARED


async def _declara(request, corpo, rota, event_type):
    return event_type


async def declarar_incidente(corpo, request):
    return await _declara(request, corpo, "/participant/incident", INCIDENT_DECLARED)
'''

#: `PRODUTOR` vive no modulo IRMAO, e nao no que chama — e e o que
#: `_produtor_da_raiz` existe para alcancar. Sem ele a direcao (c) ficaria muda
#: neste produtor, e um hook poderia nomear um servico que nao e quem grava.
EMISSOR_DO_NUCLEO = '''
PRODUTOR = "participant-api"
'''

HOOK_DO_NUCLEO = """hooks:
  - event_type: incident_declared
    trigger: "POST /participant/incident"
    producer: participant-api
"""

#: O emissor coerente: constante do catalogo, `PRODUTOR` de modulo, payload
#: literal com os quatro campos que o hook declara.
EMISSOR_COERENTE = '''
from contracts.generated.events import AUDIT_QUERY_PERFORMED
from range_core.events.store import EventDraft

PRODUTOR = "academus-api"


def registrar_consulta(store, period_start, period_end, group_by, result_count):
    store.append(
        EventDraft(
            event_type=AUDIT_QUERY_PERFORMED,
            truth_layer="participant_action",
            producer=PRODUTOR,
            payload={
                "period_start": period_start,
                "period_end": period_end,
                "group_by": group_by,
                "result_count": result_count,
            },
        )
    )
'''

HOOK_COERENTE = """hooks:
  - event_type: audit_query_performed
    trigger: "GET /audit/grade-changes"
    producer: academus-api
    payload_fields: [period_start, period_end, group_by, result_count]
"""

#: `nome -> (yaml, python)`. Cada caso e um adapter inteiro.
CASOS: dict[str, tuple[str, str]] = {
    # (a) — O CASO DO B1, literal: hook declarado, produtor de outra fase.
    "hook declarado e ninguem emite": (
        HOOK_COERENTE
        + """  - event_type: vpn_access_revoked
    trigger: "POST /identity/revoke com escopo vpn"
    producer: federated-identity-simulator
    payload_fields: [scope, principal]
""",
        EMISSOR_COERENTE,
    ),
    # (b) — a direcao inversa: o adapter emite o que nao declarou.
    "emissao que o arquivo de hooks nao declara": (
        HOOK_COERENTE,
        EMISSOR_COERENTE
        + '''
from contracts.generated.events import VPN_ACCESS_REVOKED


def revogar(store):
    store.append(
        EventDraft(
            event_type=VPN_ACCESS_REVOKED,
            truth_layer="participant_action",
            producer=PRODUTOR,
            payload={"scope": "vpn", "principal": "svc"},
        )
    )
''',
    ),
    # (c) — o hook nomeia um servico que nao e quem grava.
    "producer declarado diverge de quem emite": (
        HOOK_COERENTE.replace("producer: academus-api", "producer: range-api"),
        EMISSOR_COERENTE,
    ),
    # (d) — campo a mais no emissor: o hook descreve um evento que nao e o emitido.
    "payload emitido tem campo que o hook nao declara": (
        HOOK_COERENTE,
        EMISSOR_COERENTE.replace(
            '"result_count": result_count,',
            '"result_count": result_count,\n                "escopo": "tudo",',
        ),
    ),
    # (d) — campo a menos: a declaracao promete o que a emissao nao entrega.
    "payload_fields declara campo que o emissor nao escreve": (
        HOOK_COERENTE.replace(
            "payload_fields: [period_start, period_end, group_by, result_count]",
            "payload_fields: [period_start, period_end, group_by, result_count, motivo]",
        ),
        EMISSOR_COERENTE,
    ),
    # (d) — RECUSA EM VEZ DE DEGRADAR: sem dicionario literal nao ha o que
    # conferir, e "nao consegui" nao pode virar "ok".
    "payload construido dinamicamente": (
        HOOK_COERENTE,
        EMISSOR_COERENTE.replace(
            """            payload={
                "period_start": period_start,
                "period_end": period_end,
                "group_by": group_by,
                "result_count": result_count,
            },""",
            "            payload=dict(zip(campos, valores)),",
        ),
    ),
}


#: `nome -> (yaml, app, emissor)`. Cada caso e um SERVICO do nucleo inteiro.
CASOS_DO_NUCLEO: dict[str, tuple[str, str, str]] = {
    # (a) — hook declarado e a chamada que carregaria o tipo nao existe.
    "nucleo: hook declarado e ninguem emite": (
        HOOK_DO_NUCLEO,
        APP_DO_NUCLEO.replace("await _declara(", "await _outra_coisa("),
        EMISSOR_DO_NUCLEO,
    ),
    # (b) — a direcao inversa, com o tipo chegando POSICIONALMENTE.
    "nucleo: emissao posicional que o arquivo de hooks nao declara": (
        HOOK_DO_NUCLEO.replace("incident_declared", "containment_declared").replace(
            "/participant/incident", "/participant/containment"
        ),
        APP_DO_NUCLEO,
        EMISSOR_DO_NUCLEO,
    ),
    # (c) — o `PRODUTOR` do modulo IRMAO diverge do hook. E o caso que prova
    # `_produtor_da_raiz`: sem ele a checagem nao acharia produtor nenhum e esta
    # direcao passaria calada.
    "nucleo: producer do hook diverge do PRODUTOR do servico": (
        HOOK_DO_NUCLEO.replace("producer: participant-api", "producer: range-api"),
        APP_DO_NUCLEO,
        EMISSOR_DO_NUCLEO,
    ),
}


def _servico_do_nucleo(raiz: Path, yaml: str, app: str, emissor: str) -> Path:
    """Monta a forma da `participant-api`: hooks na raiz, codigo em `api/`."""
    (raiz / "api").mkdir(parents=True)
    (raiz / "observability_hooks.yaml").write_text(yaml, encoding="utf-8")
    (raiz / "api" / "app.py").write_text(app, encoding="utf-8")
    (raiz / "api" / "emissor.py").write_text(emissor, encoding="utf-8")
    return raiz


def _com_produtores(tabela: tuple[Produtor, ...]) -> int:
    """Roda a checagem contra uma tabela de raizes substituida, e restaura.

    A SUBSTITUICAO E A UNICA FORMA DE ALCANCAR A SEGUNDA RAIZ, e o motivo e o
    contrato de CLI: o caminho opcional que os casos de adapter usam assume a
    forma de `domains/` — um diretorio de adapters, com `EventDraft`. Acrescentar
    um segundo argumento de CLI para a `chamada` faria a checagem receber a
    convencao por argumento, que e como um verificador aceita o par vazio e fica
    verde provando nada.

    `PRODUTORES` e tabela DECLARADA, e trocar a declaracao por outra em memoria
    exercita o mesmo codigo com outra entrada — sem abrir porta nenhuma no
    produto.
    """
    anterior = checagem.PRODUTORES
    checagem.PRODUTORES = tabela
    try:
        return main([])
    finally:
        checagem.PRODUTORES = anterior


def _adapter(raiz: Path, nome: str, yaml: str, python: str) -> Path:
    """Monta `<raiz>/<nome>/` com os dois arquivos, e devolve a raiz de `domains/`."""
    destino = raiz / nome
    destino.mkdir(parents=True)
    (destino / "observability_hooks.yaml").write_text(yaml, encoding="utf-8")
    (destino / "emissor.py").write_text(python, encoding="utf-8")
    return raiz


def main_probes() -> int:
    falhas: list[str] = []

    with tempfile.TemporaryDirectory() as temporario:
        for indice, (nome, (yaml, python)) in enumerate(CASOS.items()):
            raiz = Path(temporario) / f"caso{indice}"
            domains = _adapter(raiz, "academus", yaml, python)
            if main([str(domains)]) == 0:
                falhas.append(f"{nome}: defeito plantado e a checagem PASSOU")
            else:
                print(f"  reprovou como devia: {nome}")

        # POSITIVO 1 — o adapter coerente passa. Sem ele, uma checagem que
        # reprovasse todo adapter passaria em todos os negativos acima.
        raiz = Path(temporario) / "positivo"
        domains = _adapter(raiz, "academus", HOOK_COERENTE, EMISSOR_COERENTE)
        if main([str(domains)]) != 0:
            falhas.append(
                "adapter coerente foi REPROVADO: a checagem nao discrimina, e "
                "todos os negativos acima passam por reprovar tudo."
            )
        else:
            print("  passou como devia: adapter com hook, emissor, produtor e payload batendo")

        # POSITIVO 2 — VACUIDADE. `domains/` sem hook nenhum nao pode sair 0:
        # "nada a conferir" e recusa, e nao aprovacao.
        vazio = Path(temporario) / "vazio"
        (vazio / "adapter_sem_hooks").mkdir(parents=True)
        if main([str(vazio)]) == 0:
            falhas.append(
                "`domains/` SEM `observability_hooks.yaml` passou. A checagem "
                "aprova por vacuidade, que e o modo de falha dela."
            )
        else:
            print("  reprovou como devia: `domains/` sem hook nenhum (vacuidade)")

        # -------------------------------------------------------------------
        # O PRODUTOR DO NUCLEO — H2 da setima auditoria.
        # -------------------------------------------------------------------
        for indice, (nome, (yaml, app, emissor)) in enumerate(
            CASOS_DO_NUCLEO.items()
        ):
            raiz = _servico_do_nucleo(
                Path(temporario) / f"nucleo{indice}", yaml, app, emissor
            )
            tabela = (Produtor(str(raiz), "observability_hooks.yaml", "_declara"),)
            if _com_produtores(tabela) == 0:
                falhas.append(f"{nome}: defeito plantado e a checagem PASSOU")
            else:
                print(f"  reprovou como devia: {nome}")

        # POSITIVO — o servico do nucleo coerente passa, com o tipo chegando
        # POSICIONALMENTE. Sem ele, os tres negativos acima seriam satisfeitos
        # por uma checagem que nao enxerga `_declara` e reprova tudo.
        raiz = _servico_do_nucleo(
            Path(temporario) / "nucleo_positivo",
            HOOK_DO_NUCLEO,
            APP_DO_NUCLEO,
            EMISSOR_DO_NUCLEO,
        )
        tabela = (Produtor(str(raiz), "observability_hooks.yaml", "_declara"),)
        if _com_produtores(tabela) != 0:
            falhas.append(
                "servico do nucleo COERENTE foi reprovado: a checagem nao "
                "enxerga o `event_type` posicional, e os negativos do nucleo "
                "passam por reprovar tudo."
            )
        else:
            print(
                "  passou como devia: servico do nucleo com `event_type` "
                "posicional em `_declara` e `PRODUTOR` no modulo irmao"
            )

        # VACUIDADE POR RAIZ — a direcao nova, e a que o total esconderia. Uma
        # raiz declarada sem arquivo de hooks e produtor cuja instrumentacao
        # SUMIU; conferida no total, a outra raiz a cobriria.
        raiz = Path(temporario) / "nucleo_sem_hooks"
        (raiz / "api").mkdir(parents=True)
        (raiz / "api" / "emissor.py").write_text(EMISSOR_DO_NUCLEO, encoding="utf-8")
        tabela = (
            Produtor("domains", "*/observability_hooks.yaml", "EventDraft"),
            Produtor(str(raiz), "observability_hooks.yaml", "_declara"),
        )
        if _com_produtores(tabela) == 0:
            falhas.append(
                "raiz declarada SEM arquivo de hooks passou porque a outra raiz "
                "tinha arquivos. A vacuidade tem de ser conferida POR RAIZ."
            )
        else:
            print("  reprovou como devia: raiz declarada sem hook nenhum (vacuidade por raiz)")

    # POSITIVO 3 — A ARVORE REAL. E o que pega o probe que so exercita fixture.
    if main([]) != 0:
        falhas.append(
            "a arvore real reprova — a checagem esta quebrada, ou o hook voltou "
            "sem o emissor dele."
        )

    if falhas:
        for falha in falhas:
            print(f"PROVA NEGATIVA FALHOU: {falha}", file=sys.stderr)
        return 1

    plantados = len(CASOS) + len(CASOS_DO_NUCLEO) + 2  # +2: as duas vacuidades
    print(
        f"{plantados} defeitos plantados, {plantados} reprovados (as quatro "
        "direcoes nas DUAS formas de produtor, mais a vacuidade por raiz); o "
        "adapter coerente passa, o servico do nucleo coerente passa, e a arvore "
        "real passa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
