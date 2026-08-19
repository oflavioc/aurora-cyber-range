#!/usr/bin/env python3
"""Prova que `check_readme_atual.py` REPROVA contra afirmacao plantada.

Checagem que nunca ficou vermelha prova que roda, nao que detecta — a doutrina
da Fase 0, repetida por todo `*_probes.py` deste repositorio.

AS DUAS DIRECOES, E A SEGUNDA E A QUE FALTA COM MAIS FREQUENCIA
----------------------------------------------------------------
Um verificador de prosa que reprovasse SEMPRE passaria em qualquer teste que so
medisse bloqueio. Por isso o primeiro probe daqui e o caso VERDE: os documentos
como estao na arvore precisam passar. Foi o buraco que quatro rodadas da Fase 0
produziram por so testar bloqueio, e a licao esta no registro daquela fase.

POR QUE OS PROBES INJETAM DOCUMENTO E FONTE
--------------------------------------------
`verifica(docs, fontes)` recebe os dois lados de proposito. O modo de falha real
tem duas formas, e cada uma entra por um lado:

  - o DOCUMENTO envelhece — alguem fecha a Fase 6 e o README continua dizendo 5.
    Estes probes plantam no texto.
  - a ARVORE muda e o documento nao — verificador novo sem `_probes.py`, fase
    nova no `07`, caminho renomeado. Estes probes plantam na fonte.

Nenhum dos dois exige escrever na arvore para ser exercido.

O EIXO QUE NAO E NUMERO
------------------------
O terceiro grupo de probes ataca o proprio mecanismo: afirmacao REESCRITA, que
faz a expressao nao casar com nada. Esse e o modo de falha especifico de um
verificador de prosa — e o unico em que "nada encontrado" poderia ser lido como
"nada errado". Ele tem de reprovar, e por isso tem probe proprio.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_readme_atual import (  # noqa: E402
    NAO_VERIFICAVEL,
    PREDICADOS,
    _status_da_proxima,
    fontes,
    main,
    verifica,
)

DOCS_REAIS = {
    nome: (REPO_ROOT / nome).read_text(encoding="utf-8")
    for nome in ("README.md", "docs/BRIEFING.md")
}


def _com(docs: dict[str, str], arquivo: str, de: str, para: str) -> dict[str, str]:
    """Copia dos documentos com uma substituicao plantada.

    Se a substituicao nao ancorar, o probe FALHA em vez de passar: um probe que
    planta nada e um probe que sempre passa, e este repositorio ja pagou por um.
    """
    novo = dict(docs)
    if de not in novo[arquivo]:
        raise AssertionError(
            f"o probe nao ancorou em {arquivo}: {de!r} nao esta la. A forma do "
            "documento mudou, e este probe precisa acompanhar."
        )
    novo[arquivo] = novo[arquivo].replace(de, para, 1)
    return novo


def probe_verde(f) -> bool:
    problemas = verifica(DOCS_REAIS, f)
    if problemas:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada:")
        for p in problemas:
            print(f"    {p}")
        return False
    print("OK: passou como devia - documentos da arvore, sem plantio")
    return True


def roda(rotulo: str, docs: dict[str, str], f: dict, esperado: str) -> bool:
    problemas = verifica(docs, f)
    if not problemas:
        print(f"FALHA: probe '{rotulo}': afirmacao plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou, mas nao pelo eixo esperado:")
        for p in problemas:
            print(f"    {p}")
        return False
    print(f"OK: reprovou com afirmacao plantada - {rotulo}")
    return True


def probes_de_documento(f) -> list[bool]:
    """O documento envelhece: os numeros dele param de bater com a arvore."""
    casos = [
        (
            "fase corrente desatualizada - a classe que ocorreu duas vezes",
            _com(DOCS_REAIS, "README.md", "Fases 0 a 5 conclu", "Fases 0 a 4 conclu"),
            "`ultima_fase_concluida` afirma",
        ),
        (
            "proximo checkpoint apontando para fase ja fechada",
            _com(
                DOCS_REAIS,
                "README.md",
                "Próximo checkpoint: **Fase 6",
                "Próximo checkpoint: **Fase 5",
            ),
            "`proximo_checkpoint` afirma",
        ),
        (
            "contagem de testes velha",
            _com(DOCS_REAIS, "README.md", "**426 testes**", "**450 testes**"),
            "`testes` afirma",
        ),
        (
            "o BRIEFING desatualizado enquanto o README esta certo",
            _com(
                DOCS_REAIS,
                "docs/BRIEFING.md",
                "Fases 0 a 5 conclu",
                "Fases 0 a 2 conclu",
            ),
            "docs/BRIEFING.md: `ultima_fase_concluida` afirma",
        ),
        (
            "caminho de componente que nao existe na arvore",
            _com(
                DOCS_REAIS,
                "README.md",
                "`range-core/clock/`",
                "`range-core/relogio/`",
            ),
            "que a arvore nao contem",
        ),
        (
            "o comando que produziu o numero, trocado por outro",
            _com(
                DOCS_REAIS,
                "README.md",
                "`python -m unittest discover -s tests`",
                "`pytest tests/`",
            ),
            "o comando dos testes",
        ),
    ]
    return [roda(rotulo, docs, f, esperado) for rotulo, docs, esperado in casos]


def probes_de_fonte(f) -> list[bool]:
    """A arvore muda e o documento nao acompanha."""
    resultados = []

    fase_nova = dict(f)
    fase_nova["ultima_fase_concluida"] = 6
    fase_nova["proximo_checkpoint"] = 7
    resultados.append(
        roda(
            "a Fase 6 fechou e os documentos nao souberam",
            DOCS_REAIS,
            fase_nova,
            "`ultima_fase_concluida` afirma",
        )
    )

    roadmap = dict(f)
    roadmap["total_de_fases"] = 13
    resultados.append(
        roda(
            "um spec-change acrescentou fase ao roadmap",
            DOCS_REAIS,
            roadmap,
            "`total_de_fases` afirma",
        )
    )

    sem_probe = dict(f)
    sem_probe["verificadores_sem_probe"] = [
        "check_progress_consistency.py",
        "check_coisa_nova.py",
    ]
    sem_probe["verificadores_scripts"] = int(f["verificadores_scripts"]) + 1
    resultados.append(
        roda(
            "verificador novo SEM prova negativa, e o texto nao o nomeia",
            DOCS_REAIS,
            sem_probe,
            "nao virar esconderijo",
        )
    )

    carga = dict(f)
    carga["erros_de_carga"] = [("tests.test_inventado", "ImportError")]
    resultados.append(
        roda(
            "modulo de teste que nao importa - a contagem deixa de valer",
            DOCS_REAIS,
            carga,
            "erro de carga",
        )
    )

    return resultados


def probes_da_guarda_de_forma() -> list[bool]:
    """A guarda contra o envelhecimento silencioso do PROPRIO predicado.

    `_status_da_proxima` responde "consigo ver se esta fase fechou?". Ela e
    exercida aqui contra os registros REAIS, nas tres direcoes, sem escrever
    nada na arvore:

      - `fase_1.md` existe e nao tem linha de status no cabecalho -> avisa;
      - `fase_2.md` tem `**Status: CONCLUIDA` na terceira linha -> silencio;
      - uma fase que nao existe -> silencio, porque nao ha o que ver.

    Sem a primeira direcao, uma Fase 6 fechada numa forma de status nova faria
    fonte e documento concordarem sobre um fato falso — os dois diriam 4, e
    nada ficaria vermelho.
    """
    resultados = []

    aviso = _status_da_proxima(1)
    if aviso is None or "nao consegue ver o fechamento" not in aviso:
        print(
            "FALHA: registro sem linha de status no cabecalho nao produziu aviso. "
            f"Devolveu {aviso!r}"
        )
        resultados.append(False)
    else:
        resultados.append(
            roda(
                "registro de fase sem linha de status: a guarda de forma dispara",
                DOCS_REAIS,
                {**fontes(), "aviso_da_proxima": aviso},
                "nao consegue ver o fechamento",
            )
        )

    for fase, rotulo in ((2, "registro COM status reconhecido"), (99, "fase inexistente")):
        if _status_da_proxima(fase) is not None:
            print(f"FALHA: {rotulo} (fase {fase}) avisou, e nao devia - falso bloqueio")
            resultados.append(False)
        else:
            print(f"OK: nao avisou, como devia - {rotulo}")
            resultados.append(True)

    return resultados


def probe_afirmacao_reescrita(f) -> bool:
    """O eixo proprio de um verificador de prosa: a ancora some.

    Apaga a frase inteira que carrega a fase corrente. Nao ha numero errado —
    ha AUSENCIA de numero. Um verificador que lesse "nada casou" como "nada
    errado" passaria aqui, e passaria justamente no caso em que ele parou de
    verificar.
    """
    docs = _com(DOCS_REAIS, "README.md", "**Fases 0 a 5 concluídas.**", "")
    return roda(
        "a afirmacao foi reescrita e a ancora sumiu",
        docs,
        f,
        "NAO ENCONTRADO REPROVA",
    )


def probe_declaracao_do_nao_verificavel() -> bool:
    """A lista de limites nao pode esvaziar sem que alguem note.

    Ela e a metade da P4-12 que este verificador entrega: ausencia de predicado
    tem de ser decisao escrita. Uma lista vazia significaria que tudo esta
    coberto — o que seria falso, e ninguem estaria olhando.
    """
    if len(NAO_VERIFICAVEL) < 5:
        print(
            "FALHA: NAO_VERIFICAVEL tem menos de 5 entradas. Ou a cobertura "
            "cresceu muito, ou alguem esvaziou a declaracao dos limites."
        )
        return False
    if any(not motivo.strip() for motivo in NAO_VERIFICAVEL.values()):
        print("FALHA: ha entrada em NAO_VERIFICAVEL sem motivo escrito.")
        return False
    print(f"OK: {len(NAO_VERIFICAVEL)} limites declarados, cada um com motivo")
    return True


def main_probes() -> int:
    if main() != 0:
        print("\nFALHA: a arvore limpa reprova no verificador principal.")
        return 1
    print()

    f = fontes()
    resultados = [probe_verde(f)]
    resultados += probes_de_documento(f)
    resultados += probes_de_fonte(f)
    resultados += probes_da_guarda_de_forma()
    resultados.append(probe_afirmacao_reescrita(f))
    resultados.append(probe_declaracao_do_nao_verificavel())

    print()
    if all(resultados):
        print(
            f"check_readme_atual.py reprova nos {len(resultados)} eixos, sobre "
            f"{len(PREDICADOS)} predicados: documento envelhecido, arvore que "
            "andou, ancora reescrita e limites declarados - mais o caso verde de "
            "controle."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
