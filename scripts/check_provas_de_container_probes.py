#!/usr/bin/env python3
"""Prova que `check_provas_de_container.py` RECUSA — e que ele APROVA o legitimo.

AS DUAS DIRECOES QUE A P4-10 EXIGE POR NOME
---------------------------------------------
A recomendacao da P4-10 tem uma condicao, e e ela que separa a opcao A de
atestacao: *"o auditor REPROVA se o SHA nao for o do worktree que ele esta
julgando"*. Uma condicao que nunca foi vista reprovando e uma frase.

    (b) SHA DIVERGENTE  -> recusa      <- a condicao da P4-10, exercida
    (a) ARQUIVO AUSENTE -> recusa      <- e nao "sai 0 por nao saber"

O eixo (a) e o que esta linhagem ja errou tres vezes em outro mecanismo: os dois
predicados de base que `check_audit_base.py` aposentou **degradaram para "ok"
quando nao sabiam**. Aqui, nao ter a evidencia e exatamente o caso em que nao se
pode afirmar que os itens 1 e 4 da DoD passam — entao ele recusa, e os dois itens
voltam a ser NAO VERIFICADO.

E O EIXO (c) E O QUE IMPEDE OS OUTROS DE VIRAREM SUPERSTICAO
--------------------------------------------------------------
Sao TREZE eixos, e **dez deles exigem RECUSA** — um verificador que negasse sempre
passaria nesses dez sem provar nada. Sao TRES os que exigem aprovacao, e contados
aqui na fonte: o (c), o (k) e o (m). O (c) e o principal: ele afirma duas coisas,
nao uma — que rc=0, e que **a saida integra das provas aparece**. Um verificador
que aprovasse em silencio trocaria um NAO VERIFICADO por um "confie na minha
checagem", que nao e o que a P4-10 comprou.

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


def _git(raiz: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(raiz), *IDENTIDADE, *args],
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


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


def documento(commit: str, **troca) -> dict:
    """Uma evidencia INTEIRA e legitima. Cada eixo estraga exatamente um campo."""
    doc = {
        "esquema": ESQUEMA,
        "commit": commit,
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
# (b) SHA DIVERGENTE — a condicao que a P4-10 nomeia, exercida reprovando.
# --------------------------------------------------------------------------
def eixo_b() -> bool:
    with arvore() as d:
        escreve(d, documento("0" * 40))
        rc, texto = _avalia_capturando(d)
        if rc == 0:
            print("FALHOU: [b - SHA divergente] APROVOU evidencia de outro commit.")
            return False
        head = _git(d, "rev-parse", "HEAD")
        # OS DOIS SHAs TEM DE APARECER. Recusar dizendo so "divergiu" obrigaria
        # quem le a descobrir de qual commit a evidencia fala — e o caso normal
        # e esquecer de rodar a auditoria depois de um commit novo.
        if "0" * 40 not in texto or head not in texto:
            print(f"FALHOU: [b] recusou sem imprimir os DOIS SHAs.\n{texto}")
            return False
        print("OK: [b - SHA divergente] recusou, nomeando o declarado e o julgado.")
        return True


# --------------------------------------------------------------------------
# (c) O PAR — sem ele, os outros nove passariam com um verificador que so nega.
# --------------------------------------------------------------------------
def eixo_c() -> bool:
    with arvore() as d:
        escreve(d, documento(_git(d, "rev-parse", "HEAD")))
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
        escreve(d, '{"esquema": "aurora.provas-de-container/1", "commit"')
        return eixo_recusa("d - JSON truncado", d, dizendo="nao e JSON legivel")


# --------------------------------------------------------------------------
# (e) ESQUEMA AUSENTE — o arquivo pode ser outra coisa com o mesmo nome.
# --------------------------------------------------------------------------
def eixo_e() -> bool:
    with arvore() as d:
        doc = documento(_git(d, "rev-parse", "HEAD"))
        del doc["esquema"]
        escreve(d, doc)
        return eixo_recusa("e - esquema ausente", d, dizendo="nao declara o esquema")


# --------------------------------------------------------------------------
# (f) SEM CAMPO `commit` — sem SHA nao ha amarra, e sem amarra e atestacao.
# --------------------------------------------------------------------------
def eixo_f() -> bool:
    with arvore() as d:
        doc = documento(_git(d, "rev-parse", "HEAD"))
        doc["commit"] = "nao-e-um-sha"
        escreve(d, doc)
        return eixo_recusa("f - commit invalido", d, dizendo="nao carrega um `commit` valido")


# --------------------------------------------------------------------------
# (g) VACUIDADE — `"provas": []` passaria por nao ter o que reprovar.
# --------------------------------------------------------------------------
def eixo_g() -> bool:
    with arvore() as d:
        escreve(d, documento(_git(d, "rev-parse", "HEAD"), provas=[]))
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
        doc = documento(_git(d, "rev-parse", "HEAD"))
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
        doc = documento(_git(d, "rev-parse", "HEAD"))
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
        escreve(d, documento(_git(d, "rev-parse", "HEAD")))
        _git(d, "add", "-f", "--", EVIDENCIA)
        _git(d, "commit", "-q", "-m", "evidencia commitada por engano")
        # O SHA MUDOU AO COMMITAR, e isso e o proprio argumento: um commit nao
        # contem o proprio SHA. O eixo (b) tambem reprovaria — este existe para
        # que a mensagem nomeie a causa provavel, que e engano e nao forja.
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
        escreve(d, documento(_git(d, "rev-parse", "HEAD")))

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
        doc = documento(_git(d, "rev-parse", "HEAD"))
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

        doc = documento(_git(d, "rev-parse", "HEAD"))
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


EIXOS = (eixo_a, eixo_b, eixo_c, eixo_d, eixo_e, eixo_f, eixo_g, eixo_h,
         eixo_i, eixo_j, eixo_k, eixo_l, eixo_m)


def main() -> int:
    print(
        "check_provas_de_container.py — treze eixos. O (b) e a condicao que a\n"
        "P4-10 nomeia; o (a) e a que nao pode degradar para 'ok'; o (c) e o par\n"
        "sem o qual os outros passariam com um verificador que so nega. O (l) e\n"
        "o (m) nao foram previstos — os dois sairam de execucao real.\n"
    )
    resultados = [eixo() for eixo in EIXOS]
    print()
    if all(resultados):
        print(
            f"Os {len(resultados)} eixos provam a checagem nas duas direcoes: ela "
            "recusa\nausencia, divergencia de SHA e vacuidade, e aprova — imprimindo "
            "a saida\nintegra — a evidencia legitima deste commit."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} eixos nao provaram nada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
