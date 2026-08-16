#!/usr/bin/env python3
"""DEMO da Fase 2 — carregar pack, disparar, ler projecao, rollback, ler de novo.

`07_IMPLEMENTATION_PHASES.md` Fase 2: *"DEMO — via CLI: carregar pack, disparar
A01, ler projecao, rollback, ler projecao restaurada."*

POR QUE UM SCRIPT, E NAO `range-cli`
------------------------------------
`range-cli` e entregavel da **Fase 7** (`04_SCENARIO_SCHEMA.md` §8). Escrever um
CLI aqui para satisfazer a palavra "CLI" do roteiro anteciparia entregavel de
outra fase — e o `07` ja registra, na Fase 1, que roteiro de DEMO que exige peca
de fase futura nao e DEMO, e a saida certa e a demonstracao equivalente que ESTA
fase de fato entrega.

O QUE ELE DEMONSTRA ALEM DO ROTEIRO
------------------------------------
Duas coisas que sao itens de DoD e nao apareceriam so com o roteiro:

- **PAUSAR bloqueia disparo agendado** (item 3): o relogio atravessa o
  `t_relative` de um inject com o exercicio pausado, e nada dispara. Retomado,
  o mesmo inject aparece em atraso.
- **Rollback nao apaga** (item 5): a contagem de eventos no store SOBE depois do
  rollback, enquanto a projecao volta.

O TEMPO DE PAREDE E CONTROLADO, e isso nao e trapaca
-----------------------------------------------------
Os injects do pack estao em `00:05`, `00:20` e `00:35`. Uma demo que esperasse o
relogio do processo levaria 35 minutos e nao demonstraria nada a mais. O clock
recebe a fonte de tempo por injecao desde o inicio — decisao da §3.7 do registro
—, entao aqui ela e uma funcao que o roteiro avanca explicitamente, e cada
avanco esta impresso.

USO
    python scripts/demo_fase2.py [caminho-do-pack]
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

import yaml  # noqa: E402

from range_core.clock.exercise_clock import ExerciseClock  # noqa: E402
from range_core.engine.inject_engine import (  # noqa: E402
    Facilitator,
    InjectEngine,
)
from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import (  # noqa: E402
    AdapterFlags,
    PackError,
    load_pack,
)
from range_core.events.store import InMemoryEventStore  # noqa: E402

PACK_PADRAO = REPO_ROOT / "tests" / "fixtures" / "pack_minimo"

#: O adapter de que o pack depende. O caminho vive AQUI, no chamador, e nao no
#: nucleo: quem carrega o adapter entrega as flags como dado, e e por isso que
#: `AdapterFlags` carrega `source` — a mensagem de recusa do item 9 nomeia este
#: arquivo sem que o core saiba que `domains/` existe.
FLAGS_DO_ADAPTER = Path("domains") / "academus" / "flags.yaml"

T_ZERO = datetime(2026, 8, 15, 9, 0, 0)


class RelogioDeParede:
    """Fonte de tempo de parede controlada pelo roteiro."""

    def __init__(self) -> None:
        self._agora = 1_755_255_600.0  # instante arbitrario e fixo

    def __call__(self) -> float:
        return self._agora

    def avanca(self, segundos: float) -> None:
        self._agora += segundos


def titulo(texto: str) -> None:
    print(f"\n{'=' * 72}\n{texto}\n{'=' * 72}")


def mostra_estado(
    engine: InjectEngine, store: InMemoryEventStore, clock: ExerciseClock, rotulo: str
) -> None:
    """O store e o clock chegam por parametro, e nao pelo engine.

    O engine os recebe e nao os reexporta: quem monta o exercicio ja os tem na
    mao, e uma demonstracao que alcancasse o estado interno do engine mostraria
    um acoplamento que o chamador de verdade nao tem.
    """
    estado = engine.state()
    defaults = engine.pack.declarations.flag_defaults
    mudadas = {n: v for n, v in estado.flags.items() if v != defaults[n]}
    print(f"\n  {rotulo}")
    print(f"    epoch ............. {estado.simulation_epoch}")
    print(f"    posicao ........... {clock.marks().exercise_time}")
    print(f"    eventos no store .. {len(store.read_all())}")
    print(f"    flags fora do default ({len(mudadas)}):")
    for nome, valor in sorted(mudadas.items()):
        print(f"      {nome} = {valor!r}")
    if not mudadas:
        print("      (nenhuma)")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    caminho_pack = Path(argv[0]) if argv else PACK_PADRAO

    titulo("1. CARREGAR PACK")
    contratos = contract_source.read_contracts()
    caminho_flags = REPO_ROOT / FLAGS_DO_ADAPTER
    flags = AdapterFlags.from_document(
        yaml.safe_load(caminho_flags.read_text(encoding="utf-8")),
        source=FLAGS_DO_ADAPTER.as_posix(),
    )
    print(f"  adapter ........... {FLAGS_DO_ADAPTER.as_posix()} ({len(flags.specs)} flags)")

    try:
        pack = load_pack(caminho_pack, contracts=contratos, adapter_flags=flags)
    except PackError as exc:
        print(f"\nPACK RECUSADO — o engine nao sobe.\n\n{exc}\n", file=sys.stderr)
        return 1

    print(f"  pack .............. {pack.pack_id} (schema v{pack.schema_version})")
    print(f"  content_hash ...... {pack.content_hash}  [{pack.canonicalization}]")
    for inject in pack.injects:
        marca = " (ruido)" if inject.noise else ""
        decisao = f"  decisao {inject.decision_point.id}" if inject.decision_point else ""
        print(f"    {inject.id}  T+{inject.t_relative}  {inject.titulo_operacional}{marca}{decisao}")

    parede = RelogioDeParede()
    clock = ExerciseClock(T_ZERO, now=parede)
    store = InMemoryEventStore(clock)
    engine = InjectEngine(
        pack=pack,
        clock=clock,
        store=store,
        facilitator=Facilitator(user="facilitador-demo", role="control"),
        rollback_reasons=contract_source.rollback_reasons(contratos),
    )

    titulo("2. INICIAR — o pino do pack vai para o `exercise_started`")
    inicio = engine.start()
    print(f"  {inicio.event_type} {inicio.event_id}")
    print(f"    payload: {inicio.payload}")
    mostra_estado(engine, store, clock, "estado inicial (so defaults)")

    titulo("3. O RELOGIO CHEGA EM T+00:05 - A01 vence e dispara")
    parede.avanca(5 * 60)
    print(f"  em atraso: {engine.due_injects()}")
    disparados = engine.fire_due()
    for evento in disparados:
        print(f"  {evento.event_type} {evento.correlation.inject_id} em {evento.exercise_time}")
    a01 = disparados[0]
    mostra_estado(engine, store, clock, "depois de A01")

    titulo("4. PAUSAR - o relogio atravessa T+00:20 e NADA dispara (item 3)")
    pausa = engine.pause()
    print(f"  {pausa.event_type} em {pausa.exercise_time}")
    parede.avanca(15 * 60)
    print(f"  relogio de parede avancou 15 min com o exercicio pausado")
    print(f"  posicao ........... {clock.marks().exercise_time}  (congelada)")
    print(f"  em atraso ......... {engine.due_injects()}  <- bloqueado pela pausa")
    engine.resume()
    parede.avanca(15 * 60)
    print(f"  CONTINUAR e mais 15 min -> posicao {clock.marks().exercise_time}")
    print(f"  em atraso ......... {engine.due_injects()}")
    for evento in engine.fire_due():
        print(f"  {evento.event_type} {evento.correlation.inject_id} em {evento.exercise_time}")
    mostra_estado(engine, store, clock, "depois de A02")

    titulo("5. DECISAO - a opcao `monitorar` do DP-A01")
    decisao = engine.decide("A02", "monitorar", actor_id="user-ti-01", persona="ti")
    print(f"  {decisao.event_type} payload={decisao.payload} causation={decisao.correlation.causation_id}")
    mostra_estado(engine, store, clock, "depois da decisao")

    titulo("6. ROLLBACK ate o disparo de A01 - motivo `facilitation`")
    rollback = engine.rollback(to_event_id=a01.event_id, reason="facilitation")
    print(f"  {rollback.event_type} {rollback.event_id}")
    print(f"    payload: {rollback.payload}")
    mostra_estado(engine, store, clock, "projecao restaurada")

    titulo("7. O QUE O ROLLBACK NAO FEZ")
    eventos = store.read_all()
    print(f"  eventos no store: {len(eventos)} - nenhum removido")
    for evento in eventos:
        print(
            f"    epoch {evento.simulation_epoch}  {evento.exercise_time}  "
            f"{evento.event_type:<20} {evento.truth_layer}"
        )
    print("\n  a `decision_made` da epoch 0 continua legivel e marcada com a epoch dela;")
    print("  o que saiu foi o EFEITO dela sobre a flag, e so em `simulation_state`.")
    print(f"\n  em atraso agora: {engine.due_injects()}  <- a posicao voltou para T+00:05")
    parede.avanca(15 * 60)
    print(f"  o relogio anda de novo ate {clock.marks().exercise_time}")
    print(f"  em atraso: {engine.due_injects()}  <- A02 volta a vencer, na epoch nova")
    print("  A01 nao volta: o `t_relative` dele e anterior ao corte, e o disparo dele")
    print("  sobreviveu ao rollback.")

    print("\nDEMO concluida.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
