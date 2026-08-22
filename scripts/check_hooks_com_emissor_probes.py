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

from check_hooks_com_emissor import main  # noqa: E402

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

    print(
        f"{len(CASOS) + 1} defeitos plantados, {len(CASOS) + 1} reprovados "
        "(as quatro direcoes, mais a vacuidade); o adapter coerente passa e a "
        "arvore real passa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
