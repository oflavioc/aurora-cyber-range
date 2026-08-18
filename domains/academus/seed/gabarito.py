"""O gabarito da Linha B: `ground_truth.yaml` e `GM_NOTES.md`, gerados.

O QUE E GERADO E O QUE E ESCRITO A MAO — a pergunta que decide a fronteira
---------------------------------------------------------------------------
`GM_NOTES.md` e narrativa para o facilitador (`02` §6.3), entao parte dele e
prosa que nenhum gerador escreve sozinho. A divisao:

    ESCRITO A MAO     a prosa de `GM_NOTES.template.md` — por que cada conjunto
    (versionado)      existe, por que os 34 parecem suspeitos, como conduzir.
                      NADA disso e gabarito: e reafirmacao de `02` §6.1 e §6.2,
                      e a spec e publica. E a query de referencia, em
                      `linha_b.py`, pelo mesmo motivo — `02` §6.1 publica as
                      caracteristicas que ela filtra.

    GERADO            todo fato concreto: `case_id`, a conta comprometida, o
    (fora do Git)     grupo de alunos, os numeros de processo, as datas, os
                      volumes. Gabarito e QUAIS CASOS, e isso so existe depois
                      do `RANDOM_SEED`.

**A METADE ESCRITA A MAO E ONDE O GABARITO VAZARIA SEM A CHECAGEM VER**, e por
isso ela tem duas guardas, e a segunda e derivada em vez de declarada:

  1. estatica — `check_gabarito_fora_do_git.py` recusa token com forma de
     identificador de gabarito dentro do template versionado;
  2. dinamica — renderizar com DOIS seeds e exigir que nenhum identificador
     sobreviva aos dois. O que sobrevive aos dois esta no template, por
     construcao: e assim que o teste DESCOBRE o que e escrito a mao, em vez de
     confiar na declaracao acima.

O `ground_truth.yaml` GERADO VALIDA CONTRA O CONTRATO
-------------------------------------------------------
`contracts/ground_truth.schema.yaml` exige `facts` e `verification_predicates`, e
`line_b_case.set` e enum FECHADO em tres valores — `indevido_comprovado`,
`ambiguo`, `legitimo_aparencia_suspeita`.

**Os seis conjuntos de `02` §6.1 nao cabem nos tres**, e a decisao esta declarada
em vez de forcada: ruido de manutencao e credenciais compartilhadas ficam no
DATASET e fora de `line_b_cases`. Rotula-los `legitimo_aparencia_suspeita` faria
o gabarito afirmar algo falso — que eles parecem suspeitos a primeira vista —, e
a calibracao da Fase 6 os trataria como os 34. Alargar o enum seria mudar
semantica dentro da mesma `schema_version`, que `04` §4 proibe.

E a **P5-4**, com destinatario na Fase 7, que e a dona do pack.

`containment` E PREDICADO DE VERDADE, e nao invencao de conteudo de pack: contido
= nenhuma alteracao retroativa nova pela conta comprometida. E o que `09` §4.0
exige — predicado sobre estado observavel do mundo, e nao sobre declaracao.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.generated.events import CONTAINMENT_DECLARED
from domains.academus.seed import dataset, linha_b
from range_core.events.integrity import canonical_json

#: `contracts/ground_truth.schema.yaml`: `^GC-[0-9]+$`.
CASO = "GC-{:04d}"
#: `^GT-[A-Z0-9]+-[0-9]+$`.
FATO = "GT-LINHAB-{}"

#: `02` §6.2 — 1.0 para indevido comprovado, 0.5 para ambiguo, 0.0 para legitimo.
DEFENSIBILIDADE = {
    "indevido_comprovado": 1.0,
    "ambiguo": 0.5,
    "legitimo_aparencia_suspeita": 0.0,
}

#: Os tres conjuntos que viram CASO, e os nomes do enum do contrato. A ordem e a
#: de `02` §6.1, e ela decide a numeracao dos `case_id`.
CONJUNTOS_DE_CASO = (
    ("indevidos_comprovados", "indevido_comprovado"),
    ("ambiguos_legitimos", "ambiguo"),
    ("legitimos_suspeitos", "legitimo_aparencia_suspeita"),
)


@dataclass(frozen=True, slots=True)
class Gabarito:
    ground_truth: dict
    gm_notes: str


def _consulta(motor, sql: str, conta_alvo: str) -> list:
    from sqlalchemy import text

    with motor.begin() as conexao:
        return list(conexao.execute(text(sql), linha_b.parametros(conta_alvo)))


def gerar(motor, *, pack: str, seed: int, conta_alvo: str) -> Gabarito:
    """Le a trilha SEMEADA e produz os dois artefatos.

    LE DO BANCO, e nao do gerador em memoria: o gabarito descreve o que EXISTE, e
    um gabarito derivado do gerador afirmaria o que ele pretendia semear. Se a
    carga perdesse linhas, o gabarito mentiria junto — e T8 exige que a query de
    referencia devolva exatamente os 22 que estao la.
    """
    from sqlalchemy import text

    casos, fatos = [], []
    contagens: dict[str, int] = {}
    numero = 0

    for nome, rotulo in CONJUNTOS_DE_CASO:
        linhas = _consulta(
            motor,
            "SELECT t.sequence, t.actor_user_id, t.occurred_at, t.source_ip,"
            "       t.payload, t.authorization_id"
            "  FROM audit_trail t WHERE t.sequence IN ("
            + linha_b.CONJUNTOS[nome]
            + ") ORDER BY t.sequence",
            conta_alvo,
        )
        contagens[nome] = len(linhas)
        for sequencia, ator, quando, ip, payload, autorizacao in linhas:
            numero += 1
            caso = CASO.format(numero)
            fato = FATO.format(sequencia)
            casos.append(
                {
                    "case_id": caso,
                    "set": rotulo,
                    "defensibility": DEFENSIBILIDADE[rotulo],
                    "supporting_evidence": [fato],
                }
            )
            fatos.append(
                {
                    "fact_id": fato,
                    "fact_class": "grade_change_retroactive",
                    # `exercise_time` e do envelope de exercicio; aqui ele marca
                    # o instante do fato no mundo simulado, e nao no exercicio —
                    # o pack da Fase 7 e quem o ancora numa linha `T+`.
                    "exercise_time": quando.isoformat(),
                    "actor": ator,
                    "action": "grade_change",
                    "source_ip": ip,
                    "records_affected": 1,
                    "dest": payload["student_id"],
                }
            )

    for nome in ("ruido_de_manutencao", "credenciais_compartilhadas", "legitimos_normais"):
        contagens[nome] = len(_consulta(motor, linha_b.CONJUNTOS[nome], conta_alvo))

    ground_truth = {
        "facts": fatos,
        "line_b_cases": casos,
        "verification_predicates": {
            # CONTIDO = a conta comprometida parou. Predicado sobre o mundo, e
            # nao sobre declaracao — `09` §4.0.
            "containment": {
                "absence_of": {
                    "fact_class": "grade_change_retroactive",
                    # A CONSTANTE GERADA, e nao a string: o invariante 2 recusa
                    # `event_type` literal fora dos geradores, e recusou este —
                    # `02` §6.3 nao me livra de `09` §4.
                    "since": CONTAINMENT_DECLARED,
                }
            },
            "service_restoration": {
                "not_applicable": "a Linha B nao derruba servico: o incidente e "
                "de integridade, e restauracao nao e a pergunta"
            },
        },
    }

    produzido = Gabarito(
        ground_truth=ground_truth,
        gm_notes=_renderiza(pack=pack, seed=seed, contagens=contagens, casos=casos),
    )
    # O LINTER RECUSA AQUI, e nao depois: artefato divergente nao chega a existir.
    conferir(produzido)
    return produzido


def _renderiza(*, pack: str, seed: int, contagens: dict[str, int], casos: list) -> str:
    """Substitui os `{{ }}` do template versionado. Nenhuma prosa nasce aqui."""
    import re
    from pathlib import Path

    template = (Path(__file__).parent / "GM_NOTES.template.md").read_text(
        encoding="utf-8"
    )

    por_conjunto: dict[str, list[str]] = {}
    for caso in casos:
        por_conjunto.setdefault(caso["set"], []).append(caso["case_id"])

    tabela = "\n".join(
        f"**{rotulo}** ({len(ids)}) — {', '.join(ids)}\n"
        for rotulo, ids in por_conjunto.items()
    )

    valores = {
        "PACK": pack,
        # O SEED NAO ENTRA NO ARQUIVO, e a ausencia e o ponto: quem tiver o
        # numero reproduz o gabarito inteiro. O que entra e a PROCEDENCIA.
        "SEED_ORIGEM": f"RANDOM_SEED (sha-8 {canonical_json({'s': seed})[-8:]})",
        "N_INDEVIDOS": contagens["indevidos_comprovados"],
        "N_AMBIGUOS": contagens["ambiguos_legitimos"],
        "N_SUSPEITOS": contagens["legitimos_suspeitos"],
        "N_RUIDO": contagens["ruido_de_manutencao"],
        "N_DELEGADAS": contagens["credenciais_compartilhadas"],
        "N_NORMAIS": contagens["legitimos_normais"],
        "QUERY_INDEVIDOS": linha_b.INDEVIDOS.strip(),
        "QUERY_AMBIGUOS": linha_b.AMBIGUOS.strip(),
        "TABELA_DE_CASOS": tabela,
    }

    for chave, valor in valores.items():
        template = template.replace("{{" + chave + "}}", str(valor))

    # OS COMENTARIOS HTML SAIEM DO ARTEFATO, e ficam so no template. Eles falam
    # com quem EDITA o template — a regra de nao escrever identificador a mao —,
    # e o facilitador que abre o `GM_NOTES` nao e esse leitor.
    template = re.sub(r"<!--.*?-->\n?", "", template, flags=re.S)

    # A GUARDA CASA A FORMA DO PLACEHOLDER, e nao a abertura `{{`: o template
    # CITA `{{ }}` na instrucao de edicao, e a primeira versao disto reprovou
    # contra a propria explicacao. Mesma classe do teste de relogio que reprovou
    # contra o docstring — comparacao por texto pega o texto que fala sobre ela.
    if sobrando := re.findall(r"\{\{[A-Z_]+\}\}", template):
        raise ValueError(
            f"placeholder nao substituido: {sobrando}. Ele vai para o artefato "
            "como texto, e o facilitador le `{{N_INDEVIDOS}}` no lugar do numero."
        )
    return template


class GabaritoDivergente(Exception):
    """O `GM_NOTES` cita fato que o `ground_truth` nao tem — `02` §6.3.

    RECUSA ALTA, e e o que `06` T8 exige com todas as letras: *"Divergencia e
    RECUSADA pelo linter"*. Comparacao de conjuntos num teste satisfaz a leitura
    e nao satisfaz o verbo: teste compara e relata; linter RECUSA, e recusa no
    caminho que produz o artefato.

    E por isso que `conferir` roda DENTRO de `gerar`: um `GM_NOTES` divergente
    nao chega a existir. Se rodasse depois, existiria um artefato invalido no
    disco entre a escrita e a conferencia — e e nessa janela que alguem o copia.
    """


def conferir(gabarito: "Gabarito") -> None:
    """O LINTER de `02` §6.3 e `06` T8. Levanta na primeira divergencia.

    *"`GM_NOTES.md` nao pode conter fato ausente do ground truth — o linter
    compara e recusa divergencia."*

    AS DUAS DIRECOES, e a segunda impede a recusa por vacuidade: fato citado e
    ausente do ground truth RECUSA; e um `GM_NOTES` que nao cita fato nenhum
    tambem recusa, porque ele passaria trivialmente e nao seria gabarito de coisa
    alguma.
    """
    citados = fatos_citados(gabarito.gm_notes)
    declarados = {c["case_id"] for c in gabarito.ground_truth["line_b_cases"]}
    declarados |= {f["fact_id"] for f in gabarito.ground_truth["facts"]}

    if orfaos := sorted(citados - declarados):
        raise GabaritoDivergente(
            f"o `GM_NOTES` cita {orfaos[:5]} e o `ground_truth` nao os tem. "
            "`02` §6.3: a narrativa explica, e nao inventa — fato ausente do "
            "ground truth invalida o gabarito inteiro, porque o motor de "
            "calibracao le um e o facilitador conduz pelo outro."
        )
    if not citados:
        raise GabaritoDivergente(
            "o `GM_NOTES` nao cita fato nenhum. A conferencia passaria por "
            "vacuidade, e o documento nao seria gabarito de coisa alguma — "
            "`02` §6.3 o descreve como o que EXPLICA cada conjunto ao facilitador."
        )


def fatos_citados(gm_notes: str) -> set[str]:
    """Os `fact_id` e `case_id` que o `GM_NOTES` menciona — para o linter de T8.

    *"Todo fato mencionado em `GM_NOTES.md` existe em `ground_truth.yaml`."* A
    extracao e por FORMA do identificador, e nao por posicao no texto: o
    facilitador pode citar um caso em qualquer frase, e um linter que so olhasse
    a tabela deixaria passar exatamente a citacao solta que envelhece.
    """
    import re

    return set(re.findall(r"\bG[CT]-[A-Z0-9-]*[0-9]+\b", gm_notes))
