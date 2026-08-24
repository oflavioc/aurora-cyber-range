#!/usr/bin/env python3
"""Prova que `check_prova_do_seed.py` REPROVA — e a direcao (a) e a que importa.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

POR QUE A MAIORIA DOS PROBES INJETA O DOCUMENTO
-------------------------------------------------
O defeito central e a AUSENCIA do arquivo, e plantar ausencia exigiria apagar a
evidencia de quem esta rodando. `avalia()` recebe o documento, o hash da arvore e
o estado de versionamento por parametro para que esses probes nao toquem o disco.

A DIRECAO QUE MAIS IMPORTA E A PRIMEIRA: um verificador que degradasse para "ok"
por nao achar o arquivo trocaria um NAO VERIFICADO por um verde — e e exatamente
o que os dois predicados de base aposentados da Fase 3 faziam, cada um a sua
maneira.

E POR QUE DOIS PROBES PRECISAM DE GIT DE VERDADE — P7-2
---------------------------------------------------------
A P7-2 trocou o campo `commit` pelo hash da ARVORE, e a afirmacao que justifica a
troca **e sobre semantica de git**: *rebase reescreve o SHA e preserva a arvore*.
Injecao nao alcanca isso — ela prova o que `avalia()` faz com um valor, e nao que
o valor certo sobrevive ao rito que fecha a fase. `_arvore()` e a parte que fala
com o git, e os dois ultimos eixos a exercem contra um repositorio real:

    rebase que reescreve o commit e nao toca a arvore  -> APROVA
    arquivo RASTREADO alterado, arvore muda            -> REPROVA

O primeiro e o defeito original desta pendencia, com o sinal invertido: com o
campo antigo ele REPROVAVA, e era assim que todo fechamento de fase invalidava a
prova. O segundo e o que impede a troca de virar afrouxamento — a prova continua
recusando quando o objeto medido muda de verdade.

Os dois checam que a condicao plantada ACONTECEU antes de julgar o veredito. Um
rebase que nao reescrevesse o commit, ou uma edicao que nao mudasse a arvore,
fariam o eixo passar sem provar nada — que e a vacuidade de sempre, aqui na forma
de um probe que se auto-satisfaz.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_prova_do_seed import (  # noqa: E402
    ESQUEMA,
    EVIDENCIA,
    _arvore,
    avalia,
    main,
)

ARVORE = "a" * 40
OUTRA = "b" * 40

#: Identidade fixa: os dois eixos de git criam commits, e um repositorio de teste
#: nao pode depender da configuracao global de quem roda.
IDENTIDADE = [
    "-c", "user.email=probe@aurora.invalid",
    "-c", "user.name=probe",
    "-c", "commit.gpgsign=false",
]

VALIDO = {
    "esquema": ESQUEMA,
    "tree": ARVORE,
    "maquina": "Windows-11",
    "python": "3.12.10",
    "data": "2026-08-18T12:00:00+00:00",
    "seed": 20260818,
    "linhas": 3_543_783,
    "orcamento_s": 300.0,
    "segundos": [150.3, 159.4],
    "item_1_seed_em_menos_de_5_min": True,
    "item_2_byte_identico": True,
    "digests": {"audit_trail": "c" * 64, "students": "d" * 64},
}

#: O ARTEFATO DO FORMATO ANTERIOR A P7-2, inteiro e bem formado. Ele existe de
#: verdade nas maquinas que mediram antes desta mudanca, e o lancador COPIA este
#: arquivo entre arvores — entao encontrar um destes nao e hipotese.
FORMATO_ANTIGO = {k: v for k, v in VALIDO.items() if k not in ("esquema", "tree")}
FORMATO_ANTIGO["commit"] = ARVORE

PROBES = [
    (
        "(a) o arquivo NAO EXISTE — e isto nao pode degradar para ok",
        (None, ARVORE, False),
        "nao existe ou nao e JSON legivel",
    ),
    (
        "(b) a prova e de OUTRA arvore",
        (VALIDO | {"tree": OUTRA}, ARVORE, False),
        "Ela mede OUTRO conteudo",
    ),
    (
        "(b) o checkout nao resolve a arvore do HEAD",
        (VALIDO, None, False),
        "nao resolve a arvore de um `HEAD` de git",
    ),
    (
        "(c) o arquivo esta VERSIONADO — a amarracao viraria circular",
        (VALIDO, ARVORE, True),
        "esta VERSIONADO",
    ),
    (
        "(d) falta a maquina — `06` T3 exige o contexto ao lado do numero",
        ({k: v for k, v in VALIDO.items() if k != "maquina"}, ARVORE, False),
        "nao traz `maquina`",
    ),
    (
        "(d) falta a contagem de linhas",
        (VALIDO | {"linhas": 0}, ARVORE, False),
        "nao traz `linhas`",
    ),
    (
        "(e) a prova gravada diz que o item 1 FALHOU",
        (VALIDO | {"item_1_seed_em_menos_de_5_min": False}, ARVORE, False),
        "NAO passou",
    ),
    (
        "(e) e que o item 2 falhou",
        (VALIDO | {"item_2_byte_identico": False}, ARVORE, False),
        "NAO passou",
    ),
    (
        "(f) o arquivo nao declara esquema nenhum",
        ({k: v for k, v in VALIDO.items() if k != "esquema"}, ARVORE, False),
        "nao declara o esquema",
    ),
    (
        "(f) o arquivo e do FORMATO ANTIGO, amarrado ao commit — P7-2",
        (FORMATO_ANTIGO, ARVORE, False),
        "formato ANTERIOR a P7-2",
    ),
    (
        "controle: prova valida da arvore corrente",
        (VALIDO, ARVORE, False),
        None,
    ),
]


def roda(rotulo: str, argumentos: tuple, esperado: str | None) -> bool:
    problemas = avalia(*argumentos)

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': condicao plantada e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com condicao plantada - {rotulo}")
    return True


#: A DATA DO COMMITTER DO REBASE, FIXA — e ela e necessidade, nao enfeite.
#:
#: `git rebase` preserva a data do AUTOR e carimba a do COMMITTER com o agora. O
#: probe cria o commit e o reaplica no mesmo segundo, entao os dois objetos saem
#: byte-identicos e o git devolve o MESMO SHA — o rebase acontece e nao reescreve
#: nada. Medido: a primeira versao deste eixo falhou exatamente assim, e teria
#: passado por acaso numa maquina mais lenta, que e a pior forma de teste verde.
#:
#: No rito real a distancia entre gravar a prova e mergear o PR e de minutos ou
#: horas, e o SHA sempre muda. Fixar a data aqui reproduz isso por construcao em
#: vez de por sorte de relogio.
DATA_DO_REBASE = "2030-01-01T00:00:00Z"


def _git(raiz: Path, *args: str, data_de_committer: str | None = None) -> str:
    ambiente = None
    if data_de_committer is not None:
        ambiente = {**os.environ, "GIT_COMMITTER_DATE": data_de_committer}
    r = subprocess.run(
        ["git", "-C", str(raiz), *IDENTIDADE, *args],
        capture_output=True, text=True, check=True, env=ambiente,
    )
    return r.stdout.strip()


@contextmanager
def repositorio():
    """Repositorio descartavel com um commit e um arquivo RASTREADO."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        subprocess.run(
            ["git", "init", "-b", "main", "-q", str(d)],
            capture_output=True, check=True,
        )
        (d / "codigo.py").write_text("VALOR = 1\n", encoding="utf-8")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "a arvore que a prova mede")
        yield d


def eixo_rebase() -> bool:
    """O DEFEITO ORIGINAL DA P7-2, com o sinal invertido.

    O rito de fechamento e `gh pr merge --rebase` — `WORKFLOW.md` fixa rebase e
    proibe squash —, e rebase reescreve SHA por definicao. Enquanto a prova
    nomeava o commit, TODO fechamento de fase a invalidava: o arquivo falava de um
    commit que a `main` nao tinha mais. Este eixo exige o contrario.

    A TOPOLOGIA E A DO RITO: a branch nasce da ancora e leva trabalho em cima
    dela, e e esse commit que o merge reescreve. Um repositorio com um commit so
    nao serve — `fase` e `main` apontariam para o mesmo lugar, o rebase nao teria
    o que reaplicar e o eixo passaria sem exercer nada. Medido: foi o que ele fez
    na primeira versao.

    `--no-ff` porque a `main` nao andou desde a ancora, que e o caso dos tres
    merges medidos no registro. Sem ele o git faria fast-forward e nao
    reescreveria o commit; o que ele imprime — *"up to date, rebase forced"* — e
    exatamente o fechamento de uma fase cuja default nao recebeu nada no meio.
    """
    with repositorio() as d:
        _git(d, "checkout", "-q", "-b", "fase")
        (d / "codigo.py").write_text("VALOR = 1\nNOVO = 2\n", encoding="utf-8")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "o trabalho da fase, sobre a ancora")

        antes_commit = _git(d, "rev-parse", "HEAD")
        antes_arvore = _arvore(d)
        prova = VALIDO | {"tree": antes_arvore}

        _git(d, "rebase", "--no-ff", "main", data_de_committer=DATA_DO_REBASE)

        depois_commit = _git(d, "rev-parse", "HEAD")
        depois_arvore = _arvore(d)

        # A CONDICAO PLANTADA ACONTECEU? Um rebase que nao reescrevesse o commit
        # faria este eixo passar sem provar nada.
        if depois_commit == antes_commit:
            print(
                "FALHOU: [rebase] o rebase NAO reescreveu o commit "
                f"({antes_commit[:12]}); o eixo seria vacuo."
            )
            return False
        if depois_arvore != antes_arvore:
            print(
                "FALHOU: [rebase] o rebase mudou a ARVORE — "
                f"{antes_arvore[:12]} -> {depois_arvore[:12]}. "
                "A premissa inteira da saida (b) da P7-2 seria falsa."
            )
            return False

        problemas = avalia(prova, depois_arvore, False)
        if problemas:
            print(
                "FALHOU: [rebase] a prova gravada ANTES do rebase foi recusada "
                f"depois dele: {problemas}"
            )
            return False
        print(
            f"OK: [rebase] commit {antes_commit[:12]} -> {depois_commit[:12]}, "
            f"arvore {antes_arvore[:12]} intacta, e a prova ATRAVESSOU."
        )
        return True


def eixo_conteudo() -> bool:
    """E o par que impede a troca de virar afrouxamento.

    A arvore atravessar o rebase so vale se ela continuar RECUSANDO quando o
    objeto medido muda de verdade. Um arquivo rastreado alterado muda a arvore, e
    a prova antiga passa a falar de outro conteudo — que e exatamente o caso em
    que ela nao pode valer.
    """
    with repositorio() as d:
        prova = VALIDO | {"tree": _arvore(d)}

        (d / "codigo.py").write_text("VALOR = 2\n", encoding="utf-8")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "o conteudo medido mudou")
        depois = _arvore(d)

        if depois == prova["tree"]:
            print(
                "FALHOU: [conteudo] a arvore NAO mudou ao alterar um arquivo "
                "rastreado; o eixo seria vacuo."
            )
            return False

        problemas = avalia(prova, depois, False)
        if not any("OUTRO conteudo" in p for p in problemas):
            print(
                "FALHOU: [conteudo] a arvore mudou e o verificador NAO recusou "
                f"por isso: {problemas}"
            )
            return False
        print(
            f"OK: [conteudo] arvore {prova['tree'][:12]} -> {depois[:12]}, "
            "e a prova antiga foi RECUSADA."
        )
        return True


EIXOS_DE_GIT = (eixo_rebase, eixo_conteudo)


def main_probes() -> int:
    resultados = [roda(*p) for p in PROBES]
    print()
    resultados += [eixo() for eixo in EIXOS_DE_GIT]
    # O ESTADO REAL DESTE CHECKOUT e informativo, e nao um eixo: a evidencia so
    # existe na maquina que mediu, e o CI nunca a tem — pelo mesmo motivo do
    # `check_provas_de_container`, que tambem so roda os probes no CI.
    print(f"\n  neste checkout: `{EVIDENCIA}` "
          f"{'existe' if (REPO_ROOT / EVIDENCIA).exists() else 'NAO existe'}, "
          f"e `main()` retorna {main([])}")
    if all(resultados):
        print(
            f"\ncheck_prova_do_seed.py reprova nos {len(resultados)} eixos: "
            "ausencia, arvore divergente, arvore irresolvivel, arquivo "
            "versionado, contexto incompleto em duas formas, os dois itens "
            "falhos, esquema ausente, formato anterior a P7-2, o controle verde, "
            "e os dois de git — a prova atravessa o rebase e cai quando um "
            "arquivo rastreado muda."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
