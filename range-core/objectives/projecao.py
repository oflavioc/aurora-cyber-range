"""A projeção `objective_evidence` — o binding evento → objetivo, e onde ele vive.

AUTORIDADE
----------
`03_EXERCISE_DESIGN.md` §1; `09_EVENT_MODEL.md` §1.2 e §6; `00_MASTER_SPEC.md`
§5.7 e §5.8.

O BINDING VIVE AQUI, E ISSO É O INVARIANTE 4
---------------------------------------------
`09` §1.2 proíbe `objective_ids` no envelope, e `tools/check_event_envelope.py`
o guarda por AST. O motivo não é de estilo: se a `academus-api` precisasse saber
que uma consulta satisfaz OBJ-03, o domínio passaria a conhecer o desenho de
exercício e a fronteira core/adapter vazaria.

A consequência é que o vínculo tem de ser **calculado**, e este módulo é onde.
Ele recebe o fluxo e o `objectives.yaml` do pack, e responde: quais evidências
`auto` de cada objetivo apareceram, quais faltam, e quais marcadores `observed`
o avaliador marcou.

Efeito colateral declarado por `09` §1.2, e ele é bom: permite reavaliar um
exercício antigo contra objetivos revisados, porque o fluxo não carrega a
opinião de então.

AS DUAS CLASSES, E NENHUMA TERCEIRA
------------------------------------
`03` §1.2: `auto` é emitida pela aplicação instrumentada; `observed` é marcada
por avaliador, sempre com pergunta explícita. **Não existe `derived`** — o que
esta projeção calcula é a *cobertura* das duas, nunca uma terceira classe de
evidência. Inferência é do AAR, a partir do que está aqui.

`00` §5.7: critério sem evidência observável associada não entra no AAR como
métrica. É o que torna `auto_ausente` um resultado de primeira classe e não um
detalhe: objetivo cuja evidência não apareceu **não é** objetivo mal pontuado, é
objetivo sem base para pontuar.

O QUE ESTA PROJEÇÃO NÃO FAZ, E POR QUE
---------------------------------------
**Não filtra epoch.** `01_ARCHITECTURE.md` §4.1 registra que quatro das cinco
projeções leem a epoch abandonada legitimamente, cada uma pelo motivo de `09`
§3.1, e que um filtro no caminho compartilhado faria as outras herdarem uma
perda que nenhuma escolheu. O descarte da epoch de `rehearsal` do AAR é
exigência de `06_ACCEPTANCE_TESTS.md` T14, que é da Fase 10 — e a exclusão do
cálculo de **métrica** é de T10, que é de outro consumidor. Aqui, filtrar seria
decidir por ambos.

**Não pontua.** Nota é da rubrica, e rubrica é `range-core/rubrics/`. O que este
módulo devolve é o que a nota pode se apoiar — e a regra que ele executa é a de
T9: *objetivo com evidência `auto` não satisfeita não é classificado como
`excellent`*.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from contracts.generated.events import OBSERVED_MARKER_SET
from range_core.events.envelope import Event

#: A classificação que exige cobertura `auto` completa — `06` T9.
#:
#: Só esta, e não "as melhores": `03` §1.1 mostra `excellent`, `adequate` e
#: `poor`, e a norma nomeia UMA. Estender a exigência a `adequate` seria
#: endurecer a spec por conta própria; um objetivo pode ser adequado com
#: evidência parcial, e é isso que `adequate` significa.
CLASSIFICACAO_QUE_EXIGE_AUTO_COMPLETA = "excellent"


class ObjectiveProjectionError(Exception):
    """O documento de objetivos não permite projetar.

    Distinto de "objetivo sem evidência": aqui o defeito é do pack, e nenhuma
    cobertura calculada em cima dele teria significado.
    """


@dataclass(frozen=True)
class MarcadorObservado:
    marker_id: str
    prompt_to_evaluator: str


@dataclass(frozen=True)
class Objetivo:
    """Um objetivo do pack, na forma de leitura.

    `rubric` carrega a VERSÃO — `incident_triage.v2` —, e carrega porque `03`
    §2.1 diz que comparabilidade vale apenas dentro da mesma versão. Guardar só
    a competência aqui perderia exatamente o que decide se duas pontuações podem
    ser comparadas.
    """

    objective_id: str
    title: str
    competency: str
    rubric: str
    auto: tuple[str, ...]
    observed: tuple[MarcadorObservado, ...]
    scoring: Mapping[str, str]
    metric_binding: str | None


@dataclass(frozen=True)
class EvidenciaDeObjetivo:
    """A cobertura de um objetivo. Não é nota, e não vira nota sozinha."""

    objective_id: str
    rubric: str
    auto_satisfeita: frozenset[str]
    auto_ausente: frozenset[str]
    observed_marcado: frozenset[str]
    observed_ausente: frozenset[str]

    @property
    def auto_completa(self) -> bool:
        return not self.auto_ausente

    def admite(self, classificacao: str) -> bool:
        """A classificação é sustentável pela evidência que apareceu?

        `06` T9: *objetivo com evidência `auto` não satisfeita não é
        classificado como `excellent`*. A regra é de ADMISSIBILIDADE e não de
        cálculo — quem classifica é a rubrica, com o avaliador; o que este
        método faz é recusar a classificação que a evidência não sustenta.

        Devolver `True` para o resto é deliberado: `03` §1.1 admite `adequate`
        com evidência parcial, e é isso que `adequate` quer dizer.
        """
        if classificacao == CLASSIFICACAO_QUE_EXIGE_AUTO_COMPLETA:
            return self.auto_completa
        return True


def objetivos_de(documento: Mapping | None) -> dict[str, Objetivo]:
    """`objectives.yaml` na forma de leitura, com `OBJ-NN -> Objetivo`.

    DOCUMENTO AUSENTE É DICIONÁRIO VAZIO, e não erro: pack sem `objectives.yaml`
    é recusado por `build_pack_registries` no momento em que um inject cita
    objetivo, e duplicar a recusa aqui daria duas mensagens para o mesmo defeito.
    """
    objetivos: dict[str, Objetivo] = {}
    for objective_id, corpo in sorted(
        ((documento or {}).get("objectives") or {}).items()
    ):
        evidencia = corpo.get("evidence") or {}
        marcadores = tuple(
            MarcadorObservado(m["id"], m["prompt_to_evaluator"])
            for m in (evidencia.get("observed") or [])
        )
        vistos = [m.marker_id for m in marcadores]
        if len(set(vistos)) != len(vistos):
            raise ObjectiveProjectionError(
                f"{objective_id}: marcador `observed` repetido.\n"
                "    O id do marcador é o que o avaliador marca; repetido, uma "
                "marcação satisfaz duas perguntas diferentes."
            )
        objetivos[objective_id] = Objetivo(
            objective_id=objective_id,
            title=corpo["title"],
            competency=corpo["competency"],
            rubric=corpo["rubric"],
            auto=tuple(evidencia.get("auto") or ()),
            observed=marcadores,
            scoring=MappingProxyType(dict(corpo.get("scoring") or {})),
            metric_binding=corpo.get("metric_binding"),
        )
    return objetivos


def _marcadores_marcados(eventos: Sequence[Event]) -> set[str]:
    """Ids de marcador que o avaliador marcou, por `observed_marker_set`.

    O id viaja no payload. Evento sem ele é ignorado em silêncio de propósito:
    a forma do payload é contrato de `09` §4, e reimplementar a validação aqui
    daria ao consumidor uma segunda opinião sobre o que o contrato já decide.
    """
    marcados: set[str] = set()
    for evento in eventos:
        if evento.event_type != OBSERVED_MARKER_SET:
            continue
        marcador = (evento.payload or {}).get("marker_id")
        if isinstance(marcador, str) and marcador:
            marcados.add(marcador)
    return marcados


def project(
    eventos: Sequence[Event], objetivos: Mapping[str, Objetivo]
) -> dict[str, EvidenciaDeObjetivo]:
    """`OBJ-NN -> EvidenciaDeObjetivo`, calculado do fluxo.

    O binding é por `event_type`: um marcador `auto` está satisfeito quando o
    fluxo tem ao menos um evento daquele tipo. É o que `09` §6 descreve — o hook
    mapeia AÇÃO DA APLICAÇÃO a `event_type`, e o pack liga `event_type` a
    objetivo. Nenhuma das duas pontas conhece a outra, e é isso que mantém o
    invariante 4 de pé.

    NÃO recebe o store, e não tem por onde consultá-lo: recebe o fluxo já lido,
    pela mesma forma do `project` de `simulation_state`.
    """
    tipos = {evento.event_type for evento in eventos}
    marcados = _marcadores_marcados(eventos)

    resultado: dict[str, EvidenciaDeObjetivo] = {}
    for objective_id, objetivo in sorted(objetivos.items()):
        auto = set(objetivo.auto)
        ids_observed = {m.marker_id for m in objetivo.observed}
        resultado[objective_id] = EvidenciaDeObjetivo(
            objective_id=objective_id,
            rubric=objetivo.rubric,
            auto_satisfeita=frozenset(auto & tipos),
            auto_ausente=frozenset(auto - tipos),
            observed_marcado=frozenset(ids_observed & marcados),
            observed_ausente=frozenset(ids_observed - marcados),
        )
    return resultado


def comparavel(a: EvidenciaDeObjetivo, b: EvidenciaDeObjetivo) -> bool:
    """Duas coberturas do mesmo objetivo são comparáveis entre si?

    `03` §2.1: *comparabilidade entre exercícios vale apenas dentro da mesma
    versão de rubrica; comparar `v1` com `v2` exige mapeamento declarado, ou o
    AAR recusa a comparação*.

    A recusa é aqui, e não no AAR, por um motivo: a versão usada é dado desta
    projeção, e o AAR da Fase 10 a RENDERIZA. Se a decisão morasse lá, cada
    consumidor que comparasse duas rodadas precisaria lembrar da regra — e
    `WORKFLOW.md` já registra que detecção por memória não é detecção.

    Não existe ainda mecanismo de mapeamento declarado entre versões, e por isso
    esta função não o consulta: quando existir, ele entra aqui, e o nome desta
    função é onde procurar.
    """
    return a.objective_id == b.objective_id and a.rubric == b.rubric
