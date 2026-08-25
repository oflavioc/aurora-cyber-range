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


def predicados_de_verificacao() -> dict:
    """`verification_predicates` do gabarito da Linha B — `03` §3.1.

    E FUNCAO DE MODULO, e nao literal enterrado em `gerar`. A arvore nao depende
    do seed nem do banco: ela e a mesma em toda execucao. Enquanto morava dentro
    de `gerar`, a unica forma de exercita-la era subir Postgres e semear — entao
    a guarda de carga que a julga (`pack_loader.confere_qualificador_since`)
    nunca era exercida contra ELA, so contra arvores montadas a mao no teste.

    E o mesmo argumento que `tests/fixtures/pack_completo.py` escreve sobre a
    propria fixture: a forma que a spec escreve tem de atravessar o loader, ou a
    guarda fica provada contra o duplo em vez de contra o artefato.

    Devolve estrutura NOVA a cada chamada: constante de modulo seria mapeamento
    mutavel compartilhado entre gabaritos, e o `ground_truth` que `gerar`
    devolve e dicionario comum que qualquer chamador pode alterar.
    """
    return {
        # CONTIDO = a conta comprometida parou. Predicado sobre o mundo, e
        # nao sobre declaracao — `09` §4.0.
        "containment": {
            "absence_of": {
                "fact_class": "grade_change_retroactive",
                # `SINCE_SELF` do loader, escrito como literal e nao importado:
                # `domains/` nao importa de `range_core.engine.loader` em lugar
                # nenhum, e criar a primeira dependencia para reusar uma string
                # de quatro letras trocaria um acoplamento barato por um caro.
                #
                # ESTE CAMPO E QUALIFICADOR DE INSTANTE, e nao referencia a
                # evento. Ele dizia `containment_declared`, e a confusao era de
                # ESPECIE: `03` §3.1 define `self` como *"a partir do instante
                # em que este predicado passou a ser avaliado na linhagem
                # corrente"*, e `containment_declared` e `event_type` de camada
                # `declaration` (`09` §4.0) — o que a equipe AFIRMA, que `00`
                # §3 proibe de tocar ground truth. O contrato deixa o campo como
                # string livre, entao nada acusava; quem recusa e a guarda de
                # carga, e ela recusava o pack inteiro.
                "since": "self",
            }
        },
        "service_restoration": {
            "not_applicable": "a Linha B nao derruba servico: o incidente e "
            "de integridade, e restauracao nao e a pergunta"
        },
    }


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
        "verification_predicates": predicados_de_verificacao(),
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

    A METADE DE `GT-` SUBIU PARA O NUCLEO, e esta funcao a CHAMA
    -------------------------------------------------------------
    `range_core.engine.citacoes` confere fato citado contra `facts`, e faz isso
    para os TRES lados que citam — `GM_NOTES.md`, `materializes_facts` e
    `projects_facts`. A pergunta e agnostica de dominio: a forma do `fact_id`
    tem o segmento do meio CURINGA (`^GT-[A-Z0-9]+-[0-9]+$`), entao o nucleo a
    extrai sem saber o que e ACADEMUS.

    **Manter aqui uma segunda implementacao seria a D4** dentro do mecanismo que
    existe para citacao e declaracao nao divergirem — e ele so tem valor se
    houver uma pergunta so.

    A METADE DE `GC-` FICA, porque e outra pergunta
    ------------------------------------------------
    Caso da Linha B confere contra o conjunto que o DATASET semeado produziu, e
    nao contra o ground truth em geral. Quem conhece o dataset e este modulo;
    subir isso para o nucleo seria acoplamento de dominio entrando pela porta de
    uma funcao util.

    E A PERNA CONTRA VACUIDADE FICA AQUI TAMBEM, pelo mesmo criterio: exigir que
    o `GM_NOTES` cite ALGUM identificador e exigencia sobre o GABARITO — `02`
    §6.3 o descreve como o que EXPLICA cada conjunto —, e nao sobre pack em
    geral. Um `GM_NOTES` de um pack sem Linha B pode legitimamente nao citar
    caso nenhum.
    """
    from range_core.engine.citacoes import CitacaoInvalida, confere_citacoes_de_fato
    from range_core.engine.loader import contract_source

    # --- os fatos: a pergunta do NUCLEO, com a forma vinda do contrato -------
    try:
        confere_citacoes_de_fato(
            declarados={f["fact_id"] for f in gabarito.ground_truth["facts"]},
            fontes={"GM_NOTES.md": gabarito.gm_notes},
            forma=contract_source.fact_id_pattern(contract_source.read_contracts()),
        )
    except CitacaoInvalida as erro:
        raise GabaritoDivergente(str(erro)) from erro

    # --- os casos: a pergunta do DOMINIO ------------------------------------
    citados = casos_citados(gabarito.gm_notes)
    declarados = {c["case_id"] for c in gabarito.ground_truth["line_b_cases"]}

    if orfaos := sorted(citados - declarados):
        raise GabaritoDivergente(
            f"o `GM_NOTES` cita {orfaos[:5]} e o `ground_truth` nao os tem. "
            "`02` §6.3: a narrativa explica, e nao inventa — caso ausente do "
            "ground truth invalida o gabarito inteiro, porque o motor de "
            "calibracao le um e o facilitador conduz pelo outro."
        )
    if not citados:
        raise GabaritoDivergente(
            "o `GM_NOTES` nao cita caso nenhum. A conferencia passaria por "
            "vacuidade, e o documento nao seria gabarito de coisa alguma — "
            "`02` §6.3 o descreve como o que EXPLICA cada conjunto ao facilitador."
        )


def casos_citados(gm_notes: str) -> set[str]:
    """Os `case_id` que o `GM_NOTES` menciona — a metade de DOMINIO do linter.

    Chamava-se `fatos_citados` e cobria `GC-` e `GT-` juntos. A metade de `GT-`
    subiu para `range_core.engine.citacoes`, e o nome mudou junto: uma funcao
    que so olha caso e se chama "fatos" e a prosa envelhecendo dentro do codigo.

    A extracao e por FORMA do identificador, e nao por posicao no texto: o
    facilitador pode citar um caso em qualquer frase, e um linter que so olhasse
    a tabela deixaria passar exatamente a citacao solta que envelhece.
    """
    import re

    return set(re.findall(r"\bGC-[0-9]+\b", gm_notes))
