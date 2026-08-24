#!/usr/bin/env python3
"""Prova que `check_provas_de_container.py` RECUSA — e que ele APROVA o legitimo.

AS DUAS DIRECOES QUE A P4-10 EXIGE POR NOME
---------------------------------------------
A recomendacao da P4-10 tem uma condicao, e e ela que separa a opcao A de
atestacao: *"o auditor REPROVA se o objeto nao for o do worktree que ele esta
julgando"*. Uma condicao que nunca foi vista reprovando e uma frase.

    (b) ARVORE DIVERGENTE -> recusa    <- a condicao da P4-10, exercida
    (a) ARQUIVO AUSENTE   -> recusa    <- e nao "sai 0 por nao saber"

O OBJETO E A ARVORE, E NAO O COMMIT — P7-2
--------------------------------------------
Ate a P7-2 a condicao acima falava do SHA do commit, e por isso **todo
fechamento de fase invalidava a prova**: `WORKFLOW.md` fixa rebase e proibe
squash, e rebase reescreve SHA por definicao. O que ele preserva e a arvore.

Tres eixos nasceram dessa troca, e os dois primeiros sao o criterio dela:

    (n)  rebase reescreve o commit e NAO toca a arvore    -> APROVA
    (o)  arquivo RASTREADO alterado, a arvore muda        -> recusa
    (p)  artefato do esquema ANTERIOR, amarrado ao commit -> recusa nomeando
                                                             o formato

O (n) e o defeito original desta pendencia com o sinal invertido — com o campo
antigo ele reprovava. O (o) e o que impede a troca de virar afrouxamento: a
prova continua caindo quando o objeto medido muda de verdade. O (p) existe
porque o lancador COPIA o artefato entre arvores, entao encontrar um do formato
velho nao e hipotese — e sem o bump de esquema ele reprovaria pelo eixo do hash,
com mensagem culpando o gravador por uma mudanca de formato.

Os dois eixos de git checam que a condicao plantada ACONTECEU antes de julgar o
veredito. Um rebase que nao reescrevesse o commit faria o (n) passar sem provar
nada — e foi o que a primeira versao dele fez, medido.

O eixo (a) e o que esta linhagem ja errou tres vezes em outro mecanismo: os dois
predicados de base que `check_audit_base.py` aposentou **degradaram para "ok"
quando nao sabiam**. Aqui, nao ter a evidencia e exatamente o caso em que nao se
pode afirmar que os itens 1 e 4 da DoD passam — entao ele recusa, e os dois itens
voltam a ser NAO VERIFICADO.

E O EIXO (c) E O QUE IMPEDE OS OUTROS DE VIRAREM SUPERSTICAO
--------------------------------------------------------------
Sao DEZESSEIS eixos, e **doze deles exigem RECUSA** — um verificador que negasse
sempre passaria nesses doze sem provar nada. Sao QUATRO os que exigem aprovacao,
e contados aqui na fonte: o (c), o (k), o (m) e o (n). O (c) e o principal: ele
afirma duas coisas, nao uma — que rc=0, e que **a saida integra das provas
aparece**. Um verificador que aprovasse em silencio trocaria um NAO VERIFICADO
por um "confie na minha checagem", que nao e o que a P4-10 comprou.

A VACUIDADE TEM EIXO PROPRIO, E SAO DOIS TAMANHOS
---------------------------------------------------
`"provas": []` e a forma exata da §7.3 do registro da Fase 3 — a verificacao que
so parece existir. O (g) e o (h) sao os dois tamanhos dela: nenhuma prova, e uma
das duas. Sem eles, um gravador que deixasse de gravar o reinicio produziria um
verde que fala so do item 1.

O (k) NAO E SOBRE O ARQUIVO, E SOBRE QUEM APONTA
--------------------------------------------------
A raiz vem do `__file__`, e nao do `cwd`. Se viesse do diretorio corrente, quem
chama escolheria contra qual arvore a evidencia e comparada — que e a inversao
que a P3-4 fechou do lado dos pacotes, entrando aqui pela porta do chamador. O
eixo roda o script de um checkout temporario com o `cwd` na arvore REAL, e exige
que ele julgue o temporario.

O (l) E O (m) NAO FORAM PREVISTOS — OS DOIS SAIRAM DE EXECUCAO REAL
--------------------------------------------------------------------
E eles sao o mesmo defeito nas duas pontas de uma fronteira de texto, o que e
exatamente por que nenhum dos dois foi antecipado por leitura:

    (l)  o GRAVADOR nao DECODIFICA a saida do `docker compose` -> prova verde
         com evidencia vazia, e o verificador aprovava
    (m)  o VERIFICADOR nao CODIFICA a evidencia de volta       -> ele morria com
         rc=1 sobre evidencia legitima

As duas causas estao corrigidas nos dois scripts. Os eixos ficam porque **o que
se verifica nao e a causa**: e que a evidencia tenha conteudo, e que quem julga
consiga imprimi-la. Perder a saida tem mais de uma forma, e a proxima nao vai ser
a codificacao.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_provas_de_container import (  # noqa: E402
    ESQUEMA,
    EVIDENCIA,
    PROVAS,
    avalia,
    relata,
)

#: Identidade fixa: o probe cria commits, e um repositorio de teste nao pode
#: depender da configuracao global de quem roda.
IDENTIDADE = [
    "-c", "user.email=probe@aurora.invalid",
    "-c", "user.name=probe",
    "-c", "commit.gpgsign=false",
]

SAIDA_DO_DEMO = "telao reagiu ... saude 90, 2 destaques, 47 ms"
SAIDA_DO_REINICIO = "clock congelado ... T+3902s, o mesmo de antes do reinicio"


#: A DATA DO COMMITTER DO REBASE, FIXA — e ela e necessidade, nao enfeite.
#:
#: `git rebase` preserva a data do AUTOR e carimba a do COMMITTER com o agora. O
#: eixo (n) cria o commit e o reaplica no mesmo segundo, entao os dois objetos
#: saem byte-identicos e o git devolve o MESMO SHA: o rebase acontece e nao
#: reescreve nada. Medido — a primeira versao do eixo falhou assim, e teria
#: passado por acaso numa maquina mais lenta, que e a pior forma de teste verde.
#:
#: No rito real a distancia entre gravar a prova e mergear o PR e de minutos ou
#: horas, e o SHA sempre muda. Fixar a data reproduz isso por construcao.
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


def _arvore_de(raiz: Path) -> str:
    """O hash da ARVORE do `HEAD` — o que os documentos de prova declaram."""
    return _git(raiz, "rev-parse", "HEAD^{tree}")


@contextmanager
def arvore():
    """Repositorio descartavel com um commit — `HEAD` precisa resolver."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        subprocess.run(
            ["git", "init", "-b", "main", "-q", str(d)],
            capture_output=True, check=True,
        )
        (d / "algum_arquivo.txt").write_text("conteudo\n", encoding="utf-8")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "commit de probe")
        yield d


def documento(arvore: str, **troca) -> dict:
    """Uma evidencia INTEIRA e legitima. Cada eixo estraga exatamente um campo."""
    doc = {
        "esquema": ESQUEMA,
        "tree": arvore,
        "quando": "2026-08-17T12:00:00Z",
        "gerado_por": "scripts/grava_provas_de_container.py",
        "stack": {"rc": 0, "segundos": 171.4, "saida": "Container aurora-provas-range-api Healthy"},
        "provas": [
            {"id": "demo", "item": PROVAS[0].item,
             "comando": ["python", "scripts/demo_fase4.py"],
             "rc": 0, "saida": SAIDA_DO_DEMO},
            {"id": "reinicio", "item": PROVAS[1].item,
             "comando": ["python", "scripts/prova_reinicio_de_container.py"],
             "rc": 0, "saida": SAIDA_DO_REINICIO},
        ],
    }
    doc.update(troca)
    return doc


def escreve(raiz: Path, doc: dict | str) -> None:
    texto = doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False)
    (raiz / EVIDENCIA).write_text(texto, encoding="utf-8")


def _avalia_capturando(raiz: Path) -> tuple[int, str]:
    """Roda o verificador inteiro — `avalia` e `relata` — e devolve (rc, texto)."""
    falhas, doc = avalia(raiz)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = relata(falhas, doc, raiz)
    return rc, out.getvalue() + err.getvalue()


def eixo_recusa(rotulo: str, raiz: Path, *, dizendo: str) -> bool:
    rc, texto = _avalia_capturando(raiz)
    if rc == 0:
        print(f"FALHOU: [{rotulo}] o verificador APROVOU o que deveria recusar.")
        return False
    if dizendo.lower() not in texto.lower():
        print(f"FALHOU: [{rotulo}] recusou, mas sem dizer '{dizendo}'.\n{texto}")
        return False
    print(f"OK: [{rotulo}] recusou, e a mensagem nomeia a causa.")
    return True


# --------------------------------------------------------------------------
# (a) ARQUIVO AUSENTE — e nao "sai 0 por nao saber".
# --------------------------------------------------------------------------
def eixo_a() -> bool:
    with arvore() as d:
        return eixo_recusa("a - evidencia ausente", d, dizendo="EVIDENCIA AUSENTE")


# --------------------------------------------------------------------------
# (b) ARVORE DIVERGENTE — a condicao que a P4-10 nomeia, exercida reprovando.
# --------------------------------------------------------------------------
def eixo_b() -> bool:
    with arvore() as d:
        escreve(d, documento("0" * 40))
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [b - arvore divergente] APROVOU evidencia de outra arvore.")
            return False
        julgada = _arvore_de(d)
        # OS DOIS HASHES TEM DE APARECER. Recusar dizendo so "divergiu" obrigaria
        # quem le a descobrir de que conteudo a evidencia fala — e o caso normal
        # e esquecer de rodar a auditoria depois de mudar um arquivo rastreado.
        if "0" * 40 not in texto or julgada not in texto:
            print(f"FALHOU: [b] recusou sem imprimir os DOIS hashes.\n{texto}")
            return False
        print("OK: [b - arvore divergente] recusou, nomeando a declarada e a julgada.")
        return True


# --------------------------------------------------------------------------
# (c) O PAR — sem ele, os outros nove passariam com um verificador que so nega.
# --------------------------------------------------------------------------
def eixo_c() -> bool:
    with arvore() as d:
        escreve(d, documento(_arvore_de(d)))
        rc, texto = _avalia_capturando(d)
        if rc != 0:
            print(f"FALHOU: [c - o par] RECUSOU evidencia legitima.\n{texto}")
            return False
        # A SAIDA INTEGRA APARECE. Aprovar em silencio trocaria um NAO
        # VERIFICADO por "confie na minha checagem", e a P4-10 nao comprou isso.
        for trecho in (SAIDA_DO_DEMO, SAIDA_DO_REINICIO):
            if trecho not in texto:
                print(f"FALHOU: [c] aprovou sem imprimir a saida da prova.\n{texto}")
                return False
        if "NAO VIU RODAR" not in texto.upper():
            print("FALHOU: [c] aprovou sem declarar o limite — o auditor nao viu rodar.")
            return False
        print("OK: [c - o par] aprovou o legitimo, imprimiu a saida e declarou o limite.")
        return True


# --------------------------------------------------------------------------
# (d) JSON QUEBRADO — arquivo truncado e arquivo ausente pela metade.
# --------------------------------------------------------------------------
def eixo_d() -> bool:
    with arvore() as d:
        escreve(d, '{"esquema": "aurora.provas-de-container/2", "tree"')
        return eixo_recusa("d - JSON truncado", d, dizendo="nao e JSON legivel")


# --------------------------------------------------------------------------
# (e) ESQUEMA AUSENTE — o arquivo pode ser outra coisa com o mesmo nome.
# --------------------------------------------------------------------------
def eixo_e() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        del doc["esquema"]
        escreve(d, doc)
        return eixo_recusa("e - esquema ausente", d, dizendo="nao declara o esquema")


# --------------------------------------------------------------------------
# (f) SEM CAMPO `tree` — sem hash nao ha amarra, e sem amarra e atestacao.
# --------------------------------------------------------------------------
def eixo_f() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        doc["tree"] = "nao-e-um-hash"
        escreve(d, doc)
        return eixo_recusa("f - tree invalido", d, dizendo="nao carrega um `tree` valido")


# --------------------------------------------------------------------------
# (g) VACUIDADE — `"provas": []` passaria por nao ter o que reprovar.
# --------------------------------------------------------------------------
def eixo_g() -> bool:
    with arvore() as d:
        escreve(d, documento(_arvore_de(d), provas=[]))
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [g - lista vazia] APROVOU um arquivo sem prova nenhuma.")
            return False
        # AS DUAS TEM DE SER NOMEADAS. Reclamar de uma so deixaria a outra
        # invisivel, que e a vacuidade sobrevivendo dentro da mensagem de erro.
        for prova in PROVAS:
            if f"`{prova.id}`" not in texto:
                print(f"FALHOU: [g] nao nomeou a prova ausente `{prova.id}`.\n{texto}")
                return False
        print("OK: [g - lista vazia] recusou, nomeando as duas provas ausentes.")
        return True


# --------------------------------------------------------------------------
# (h) UMA DAS DUAS — o tamanho de vacuidade que passa despercebido.
# --------------------------------------------------------------------------
def eixo_h() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        doc["provas"] = [p for p in doc["provas"] if p["id"] != PROVAS[1].id]
        escreve(d, doc)
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print(f"FALHOU: [h] APROVOU sem a prova `{PROVAS[1].id}`.")
            return False
        if f"`{PROVAS[1].id}`" not in texto:
            print(f"FALHOU: [h] recusou sem dizer QUAL prova faltava.\n{texto}")
            return False
        print(f"OK: [h - prova faltando] recusou, nomeando `{PROVAS[1].id}`.")
        return True


# --------------------------------------------------------------------------
# (i) PROVA VERMELHA — e a saida dela tem de chegar a quem julga.
# --------------------------------------------------------------------------
def eixo_i() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        doc["provas"][0]["rc"] = 1
        doc["provas"][0]["saida"] = "a plateia nao recebeu texto_para_plateia"
        escreve(d, doc)
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [i - prova vermelha] APROVOU com uma prova em rc=1.")
            return False
        if "a plateia nao recebeu" not in texto:
            print(f"FALHOU: [i] recusou sem imprimir a saida da prova que falhou.\n{texto}")
            return False
        print("OK: [i - prova vermelha] recusou, e a saida da prova chegou junto.")
        return True


# --------------------------------------------------------------------------
# (j) EVIDENCIA VERSIONADA — o caso honesto, com a mensagem que nomeia a causa.
# --------------------------------------------------------------------------
def eixo_j() -> bool:
    with arvore() as d:
        escreve(d, documento(_arvore_de(d)))
        _git(d, "add", "-f", "--", EVIDENCIA)
        _git(d, "commit", "-q", "-m", "evidencia commitada por engano")
        # A ARVORE MUDOU AO RASTREAR O ARQUIVO, e isso e o proprio argumento: um
        # arquivo versionado nao contem o hash da arvore que o contem — poe-lo no
        # indice muda a arvore que ele teria de declarar. O eixo (b) tambem
        # reprovaria; este existe para que a mensagem nomeie a causa provavel,
        # que e engano e nao forja.
        #
        # E ELE FICOU MAIS FORTE COM A P7-2, e nao mais fraco: antes a
        # impossibilidade era do SHA FINAL, calculado depois de tudo; agora e do
        # CONTEUDO, que e o que a prova de fato mede.
        return eixo_recusa("j - evidencia versionada", d, dizendo="esta VERSIONADO")


# --------------------------------------------------------------------------
# (k) A RAIZ VEM DO `__file__`, E NAO DO `cwd`.
# --------------------------------------------------------------------------
def eixo_k() -> bool:
    with arvore() as d:
        (d / "scripts").mkdir()
        shutil.copy2(
            REPO_ROOT / "scripts" / "check_provas_de_container.py", d / "scripts"
        )
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "o verificador, no checkout temporario")
        escreve(d, documento(_arvore_de(d)))

        # O `cwd` e a ARVORE REAL. Se a raiz viesse dele, o verificador julgaria
        # este repositorio — onde a evidencia do commit temporario nao existe.
        r = subprocess.run(
            [sys.executable, str(d / "scripts" / "check_provas_de_container.py")],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            print(
                "FALHOU: [k - raiz pelo __file__] julgou pelo `cwd`, e nao pelo\n"
                f"        checkout que contem o script.\n{r.stdout}{r.stderr}"
            )
            return False
        print("OK: [k - raiz pelo __file__] julgou o checkout do script, nao o `cwd`.")
        return True


# --------------------------------------------------------------------------
# (l) PROVA VERDE E MUDA — e este eixo nao e hipotese: e o que a PRIMEIRA
#     execucao real do gravador produziu.
#
#     No Windows a captura de subprocesso roda em thread leitora. Uma
#     `UnicodeDecodeError` la nao propaga: `subprocess.run` devolve saida VAZIA
#     com o rc do processo. `rc: 0`, `saida: ""` — e o verificador, antes deste
#     eixo, aprovava.
#
#     A causa esta corrigida no gravador. O eixo fica porque o que se verifica
#     nao e a causa: e que a evidencia tenha conteudo. Perder a saida tem mais
#     de uma forma, e a proxima nao vai ser esta.
# --------------------------------------------------------------------------
def eixo_l() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        doc["provas"][1]["saida"] = "   \n"
        escreve(d, doc)
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [l - verde e muda] APROVOU uma prova sem saida nenhuma.")
            return False
        if f"`{PROVAS[1].id}`" not in texto or "SAIDA VAZIA" not in texto:
            print(f"FALHOU: [l] recusou sem nomear a prova muda.\n{texto}")
            return False
        print("OK: [l - verde e muda] recusou prova com rc=0 e saida vazia.")
        return True


# --------------------------------------------------------------------------
# (m) O VERIFICADOR NAO MORRE NO QUE IMPRIME — o par do (l), na outra direcao.
#
#     O (l) e sobre a evidencia chegar vazia; este e sobre ela chegar cheia e o
#     verificador nao conseguir imprimi-la. Tambem saiu de execucao real: as
#     barras de progresso do `docker compose --build` trazem caracteres fora de
#     `cp1252`, e ele saia com `UnicodeEncodeError` e rc=1 sobre evidencia
#     LEGITIMA. Um verificador que morre nao diz "reprovou" — nao diz nada.
#
#     PRECISA DE SUBPROCESSO: os outros eixos capturam por `StringIO`, que
#     aceita qualquer caractere. A codificacao do terminal so existe num
#     processo de verdade, e e ela que estava errada.
# --------------------------------------------------------------------------
def eixo_m() -> bool:
    with arvore() as d:
        (d / "scripts").mkdir()
        shutil.copy2(
            REPO_ROOT / "scripts" / "check_provas_de_container.py", d / "scripts"
        )
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "o verificador, no checkout temporario")

        doc = documento(_arvore_de(d))
        # `⣿` e o spinner do compose; `━` e a barra do build. Nenhum
        # dos dois existe em cp1252, e os dois aparecem na evidencia de verdade.
        doc["stack"]["saida"] = "⣿ Building ━━━ 42.0s"
        escreve(d, doc)

        # O PAI LE BYTES, E NAO TEXTO — e isto tambem foi achado RODANDO, no CI.
        #
        # A primeira versao usava `text=True`. O filho encoda em `cp1252` por
        # exigencia do proprio eixo, e o pai decodifica em UTF-8: no runner Linux
        # o byte 0x97 do travessao derrubou o PROBE com `UnicodeDecodeError`, com
        # o verificador funcionando perfeitamente. **Terceira vez que a mesma
        # fronteira de texto morde nesta pendencia**, agora dentro do eixo escrito
        # para ela — e por isso a saida aqui nao e decodificada: o que se afirma e
        # o `rc` e a AUSENCIA de um traceback, e nenhum dos dois precisa de texto.
        r = subprocess.run(
            [sys.executable, str(d / "scripts" / "check_provas_de_container.py")],
            cwd=str(d), capture_output=True, check=False,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        if r.returncode != 0 or b"UnicodeEncodeError" in r.stderr:
            print(
                "FALHOU: [m - saida tolerante] morreu imprimindo evidencia legitima\n"
                f"        (rc={r.returncode}).\n"
                f"{r.stderr[-600:].decode('utf-8', 'replace')}"
            )
            return False
        print("OK: [m - saida tolerante] imprimiu evidencia que o terminal nao tem.")
        return True


# --------------------------------------------------------------------------
# (n) A PROVA ATRAVESSA O REBASE — o defeito da P7-2, com o sinal invertido.
#
#     Enquanto a evidencia nomeava o SHA do commit, TODO fechamento de fase a
#     invalidava: `WORKFLOW.md` fixa `gh pr merge --rebase` e proibe squash, e
#     rebase reescreve SHA por definicao. Depois do #53 os dois verificadores
#     reprovaram na `main` sobre uma arvore que ninguem tinha tocado.
#
#     Este eixo e a prova de que a troca resolveu isso, e nao a afirmacao de que
#     resolveu. A topologia e a do rito: branch nascida da ancora, trabalho em
#     cima dela, rebase sobre a `main` que nao andou.
# --------------------------------------------------------------------------
def eixo_n() -> bool:
    with arvore() as d:
        _git(d, "checkout", "-q", "-b", "fase")
        (d / "algum_arquivo.txt").write_text("o trabalho da fase\n", encoding="utf-8")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "o trabalho da fase, sobre a ancora")

        antes_commit = _git(d, "rev-parse", "HEAD")
        antes_arvore = _arvore_de(d)
        escreve(d, documento(antes_arvore))

        _git(d, "rebase", "--no-ff", "main", data_de_committer=DATA_DO_REBASE)
        depois_commit = _git(d, "rev-parse", "HEAD")
        depois_arvore = _arvore_de(d)

        # A CONDICAO PLANTADA ACONTECEU? Um rebase que nao reescrevesse o commit
        # faria este eixo passar sem exercer nada — e foi o que a primeira
        # versao dele fez, antes da data de committer fixa.
        if depois_commit == antes_commit:
            print(
                "FALHOU: [n - atravessa o rebase] o rebase NAO reescreveu o "
                f"commit ({antes_commit[:12]}); o eixo seria vacuo."
            )
            return False
        if depois_arvore != antes_arvore:
            print(
                "FALHOU: [n] o rebase mudou a ARVORE — "
                f"{antes_arvore[:12]} -> {depois_arvore[:12]}. A premissa "
                "inteira da saida (b) da P7-2 seria falsa."
            )
            return False

        rc, texto = _avalia_capturando(d)
        if rc != 0:
            print(
                "FALHOU: [n] a evidencia gravada ANTES do rebase foi recusada "
                f"depois dele — e este e o defeito que a P7-2 fechou.\n{texto}"
            )
            return False
        print(
            f"OK: [n - atravessa o rebase] commit {antes_commit[:12]} -> "
            f"{depois_commit[:12]}, arvore {antes_arvore[:12]} intacta, e a "
            "prova continua valendo."
        )
        return True


# --------------------------------------------------------------------------
# (o) E O PAR QUE IMPEDE A TROCA DE VIRAR AFROUXAMENTO.
#
#     Atravessar o rebase so vale se a prova continuar CAINDO quando o objeto
#     medido muda de verdade. Sem este eixo, um verificador que aprovasse
#     qualquer coisa passaria no (n) — e o (n) sozinho nao distingue "amarrado
#     ao conteudo" de "amarrado a nada".
# --------------------------------------------------------------------------
def eixo_o() -> bool:
    with arvore() as d:
        antes = _arvore_de(d)
        escreve(d, documento(antes))

        (d / "algum_arquivo.txt").write_text("outro conteudo\n", encoding="utf-8")
        # SO O ARQUIVO RASTREADO, e nao `add -A`. A evidencia ja esta no disco e
        # NAO esta no `.gitignore` deste repositorio descartavel: `add -A` a
        # varreria para dentro do commit, e o verificador recusaria pelo eixo (b)
        # — versionada — em vez do (d), que e o que este eixo existe para medir.
        # Achado rodando, e e a forma exata do defeito que o (j) planta de
        # proposito, entrando aqui pela porta do setup.
        _git(d, "add", "--", "algum_arquivo.txt")
        _git(d, "commit", "-q", "-m", "o conteudo medido mudou")
        depois = _arvore_de(d)

        if depois == antes:
            print(
                "FALHOU: [o] a arvore NAO mudou ao alterar um arquivo rastreado; "
                "o eixo seria vacuo."
            )
            return False

        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [o - arvore mudou] APROVOU prova de outro conteudo.")
            return False
        if antes not in texto or depois not in texto:
            print(f"FALHOU: [o] recusou sem imprimir as DUAS arvores.\n{texto}")
            return False
        print(
            f"OK: [o - arvore mudou] {antes[:12]} -> {depois[:12]}, e a prova "
            "antiga foi RECUSADA."
        )
        return True


# --------------------------------------------------------------------------
# (p) O ARTEFATO DO FORMATO ANTERIOR A P7-2, e por que o bump de esquema e
#     mecanismo e nao formalidade.
#
#     Sem o bump, um arquivo com `commit` e sem `tree` cairia no eixo (d) como
#     *"nao carrega um `tree` valido: None"*: reprovaria — certo —, mas dizendo
#     que o gravador falhou quando o fato e que o formato mudou. Mensagem que
#     mente sobre a causa custa a mesma auditoria que a ausencia de mensagem.
#
#     E o caso nao e hipotetico: o lancador COPIA o artefato do seed entre
#     arvores, e as maquinas que mediram antes desta mudanca tem o formato velho
#     no disco.
# --------------------------------------------------------------------------
def eixo_p() -> bool:
    with arvore() as d:
        doc = documento(_arvore_de(d))
        doc["esquema"] = "aurora.provas-de-container/1"
        doc["commit"] = doc.pop("tree")
        escreve(d, doc)
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [p - formato antigo] APROVOU artefato do esquema /1.")
            return False
        if "esquema ANTERIOR a P7-2" not in texto:
            print(
                "FALHOU: [p] recusou sem dizer que o FORMATO mudou — a mensagem "
                f"culpa o gravador por uma migracao.\n{texto}"
            )
            return False
        print("OK: [p - formato antigo] recusou nomeando o esquema, e nao o hash.")
        return True


EIXOS = (eixo_a, eixo_b, eixo_c, eixo_d, eixo_e, eixo_f, eixo_g, eixo_h,
         eixo_i, eixo_j, eixo_k, eixo_l, eixo_m, eixo_n, eixo_o, eixo_p)


def main() -> int:
    print(
        "check_provas_de_container.py — dezesseis eixos. O (b) e a condicao que\n"
        "a P4-10 nomeia; o (a) e a que nao pode degradar para 'ok'; o (c) e o par\n"
        "sem o qual os outros passariam com um verificador que so nega. O (l) e\n"
        "o (m) nao foram previstos — os dois sairam de execucao real. O (n) e o\n"
        "(o) sao o criterio da P7-2: a prova atravessa o rebase, e cai quando um\n"
        "arquivo rastreado muda.\n"
    )
    resultados = [eixo() for eixo in EIXOS]
    print()
    if all(resultados):
        print(
            f"Os {len(resultados)} eixos provam a checagem nas duas direcoes: ela "
            "recusa\nausencia, divergencia de arvore, formato anterior e vacuidade, "
            "e aprova —\nimprimindo a saida integra — a evidencia legitima desta "
            "arvore, inclusive\ndepois de um rebase ter reescrito o commit que a "
            "produziu."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} eixos nao provaram nada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
