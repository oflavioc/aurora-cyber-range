#!/usr/bin/env python3
"""Prova que `check_audit_base.py` RECUSA nos sete eixos — e que passa nos dois legitimos.

O OITAVO EIXO, (h), NAO ESTAVA NA FORMULACAO: ele foi achado RODANDO o comando
antes de entrega-lo ao operador. Com `--base` apontando para a propria ancora, a
primeira versao imprimia "a auditoria e PORTA" com sete commits da fase ja em
`main` — o terceiro predicado degradando para "ok" no unico caminho em que o
operador ja declarou que nao sabe. O (g) nao o pegava: la o rc tambem e 0, e o
que distingue e o TEXTO.

O EIXO (c) E O DEFEITO REAL, e nao um caso hipotetico: e o que aconteceu nas
Fases 2 e 3. O predicado anterior perguntava "o candidato esta contido na base?",
e com cinco das seis pecas da Fase 3 ja em `main` a resposta era NAO — ele deixava
passar em silencio a auditoria que ja nao era porta. O eixo (c) e esse caso, e
foi escrito antes do predicado que o fecha.

CADA EIXO DECLARA QUAL METADE O PEGA, e isso e metade do valor deste arquivo. Se
o eixo (f1) fosse pego pela topologia, a metade de conteudo seria decoracao; se o
(c) fosse pego pelo conteudo, a ancora seria decoracao. Os probes afirmam o
CONJUNTO de eixos que dispara, entao redundancia silenciosa fica visivel:

    (b) degenerado     -> ii + iii-a
    (c) peca a peca    -> ii              <- so a topologia; conteudo nao ve
    (f1) squash        -> iii-a           <- so o conteudo; topologia nao ve
    (f2) cherry-pick   -> iii-b           <- idem
    (e) ancora         -> ancora, sozinha, e antes de qualquer outra coisa

E os dois que TEM de passar existem pelo motivo da §7.3 do registro da Fase 3:
uma guarda que recusasse sempre passaria em cinco destes eixos sem provar
nada. O (a) e o (d) sao a metade que impede a outra de virar supersticao — e o
(d) e o exato caso que o predicado anterior nao sabia distinguir.
"""

from __future__ import annotations

import io
import shlex
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_audit_base import ANCORAS, avalia, main  # noqa: E402

FASE = 4

#: Identidade fixa: o probe cria commits, e um repositorio de teste nao pode
#: depender da configuracao global de quem roda.
IDENTIDADE = [
    "-c",
    "user.email=probe@aurora.invalid",
    "-c",
    "user.name=probe",
    "-c",
    "commit.gpgsign=false",
]


def _git(repo: str, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", repo, *IDENTIDADE, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


def _commit(repo: str, arquivo: str, conteudo: str, msg: str) -> str:
    alvo = Path(repo) / arquivo
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    _git(repo, "add", arquivo)
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _ancora(repo: str, sha: str | None, fase: int = FASE) -> None:
    """Escreve o arquivo de ancoras. `sha=None` escreve arquivo SEM a linha."""
    caminho = Path(repo) / ANCORAS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = ["# ancoras de fase — probe"]
    if sha is not None:
        linhas.append(f"{fase}\t{sha}\tprobe")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _cenario(repo: str) -> tuple[str, str, str]:
    """A historia comum: `main` em c0, e a branch da fase com duas pecas.

    Devolve (c0, p1, p2). A ancora legitima e sempre c0.
    """
    _git(repo, "init", "-q")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    c0 = _commit(repo, "base.txt", "0\n", "base: antes da fase")
    _git(repo, "checkout", "-q", "-b", "fase")
    p1 = _commit(repo, "peca1.txt", "1\n", "fase-4: peca 1")
    p2 = _commit(repo, "peca2.txt", "2\n", "fase-4: peca 2")
    return c0, p1, p2


# ---------------------------------------------------------------------------
# Os cenarios. Cada um monta a historia, escreve a ancora, e devolve (base, head).
# ---------------------------------------------------------------------------


def cenario_a(repo: str) -> tuple[str, str]:
    """Caso normal: branch a frente da base, ancora gravada."""
    c0, _, p2 = _cenario(repo)
    _ancora(repo, c0)
    return "main", p2


def cenario_b(repo: str) -> tuple[str, str]:
    """Degenerado: a fase inteira ja mergeada, BASE == HEAD."""
    c0, _, p2 = _cenario(repo)
    _git(repo, "branch", "-f", "main", p2)
    _ancora(repo, c0)
    return "main", p2


def cenario_c(repo: str) -> tuple[str, str]:
    """PECA A PECA: parte da fase ja esta em `main`. O H2 da Fase 3."""
    c0, p1, p2 = _cenario(repo)
    _git(repo, "branch", "-f", "main", p1)
    _ancora(repo, c0)
    return "main", p2


def cenario_d(repo: str) -> tuple[str, str]:
    """`main` avancou com trabalho de OUTRA fase. Tem de passar."""
    c0, _, p2 = _cenario(repo)
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "outra.txt", "x\n", "fase-5: nada a ver com a fase 4")
    _git(repo, "checkout", "-q", "fase")
    _ancora(repo, c0)
    return "main", p2


def cenario_e1(repo: str) -> tuple[str, str]:
    """Ancora AUSENTE: o arquivo existe e nao tem a linha da fase."""
    _, _, p2 = _cenario(repo)
    _ancora(repo, None)
    return "main", p2


def cenario_e2(repo: str) -> tuple[str, str]:
    """Ancora AUSENTE: nem o arquivo existe."""
    _, _, p2 = _cenario(repo)
    return "main", p2


def cenario_e3(repo: str) -> tuple[str, str]:
    """Ancora que NAO E ANCESTRAL do candidato — historia paralela."""
    _, _, p2 = _cenario(repo)
    _git(repo, "checkout", "-q", "--orphan", "outra-historia")
    solto = _commit(repo, "solto.txt", "z\n", "outra historia")
    _git(repo, "checkout", "-q", "fase")
    _ancora(repo, solto)
    return "main", p2


def cenario_f1(repo: str) -> tuple[str, str]:
    """SQUASH: `main` recebe as duas pecas num commit so. Arvores identicas."""
    c0, _, p2 = _cenario(repo)
    _git(repo, "checkout", "-q", "main")
    (Path(repo) / "peca1.txt").write_text("1\n", encoding="utf-8")
    (Path(repo) / "peca2.txt").write_text("2\n", encoding="utf-8")
    _git(repo, "add", "peca1.txt", "peca2.txt")
    _git(repo, "commit", "-q", "-m", "squash: fase-4 inteira num commit")
    _git(repo, "checkout", "-q", "fase")
    _ancora(repo, c0)
    return "main", p2


def cenario_f2(repo: str) -> tuple[str, str]:
    """CHERRY-PICK: `main` recebe UMA peca com outra identidade.

    `main` avanca ANTES do cherry-pick, e nao por enfeite: colhido direto sobre
    o proprio pai, o commit sai byte a byte identico — mesma arvore, mesmo pai,
    mesma mensagem, mesmas datas — e o SHA e o MESMO. O cenario viraria o (c) sem
    dizer, e o probe ficaria verde provando outra coisa. Medido escrevendo-o
    errado primeiro.
    """
    c0, p1, p2 = _cenario(repo)
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "outra.txt", "x\n", "fase-5: main andou antes do cherry-pick")
    _git(repo, "cherry-pick", p1)
    _git(repo, "checkout", "-q", "fase")
    _ancora(repo, c0)
    return "main", p2


#: `(rotulo, cenario, eixos esperados)`. Conjunto VAZIO = tem de passar.
PROBES = [
    ("(a) branch a frente da base, ancora gravada", cenario_a, set()),
    ("(b) degenerado: a fase inteira ja em `main`", cenario_b, {"ii", "iii-a"}),
    ("(c) PECA A PECA: parte da fase ja em `main`", cenario_c, {"ii"}),
    ("(d) `main` avancou com trabalho de outra fase", cenario_d, set()),
    ("(e1) ancora ausente: arquivo sem a linha da fase", cenario_e1, {"ancora"}),
    ("(e2) ancora ausente: arquivo inexistente", cenario_e2, {"ancora"}),
    ("(e3) ancora que nao e ancestral do candidato", cenario_e3, {"ancora"}),
    ("(f1) squash-merge: arvores identicas", cenario_f1, {"iii-a"}),
    ("(f2) cherry-pick de uma peca", cenario_f2, {"iii-b"}),
]


def roda(rotulo, cenario, esperados: set[str]) -> bool:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        base, head = cenario(tmp)
        obtidos = {f.eixo for f in avalia(tmp, FASE, base, head)}

    if obtidos == esperados:
        alvo = "PASSA" if not esperados else f"recusa por {sorted(obtidos)}"
        print(f"  ok    {rotulo} -> {alvo}")
        return True
    print(f"  FALHA {rotulo}: esperava {sorted(esperados)}, obteve {sorted(obtidos)}")
    return False


def _roda_cli(argv: list[str]) -> tuple[int, str, str]:
    saida, erro = io.StringIO(), io.StringIO()
    with redirect_stdout(saida), redirect_stderr(erro):
        rc = main(argv)
    return rc, saida.getvalue(), erro.getvalue()


def probe_g() -> bool:
    """(g) `--base` explicito: avisa e SEGUE, sobre o cenario que recusaria."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        default, head = cenario_c(tmp)
        comum = ["--phase", str(FASE), "--default", default, "--head", head, "--repo", tmp]
        recusa, _, _ = _roda_cli(comum)
        aviso, _, _ = _roda_cli([*comum, "--base", default])

    if recusa == 1 and aviso == 0:
        print("  ok    (g) --base explicito avisa (rc=0) onde a base implicita recusa (rc=1)")
        return True
    print(f"  FALHA (g): implicita rc={recusa} (esperado 1), explicita rc={aviso} (esperado 0)")
    return False


def probe_h() -> bool:
    """(h) `--base` NAO pode virar o veredito. O oitavo eixo, achado RODANDO.

    A primeira versao avaliava contra `--base`. Passando a propria ancora como
    base, o merge-base contra ela E a ancora por construcao — e a guarda imprimia
    "a auditoria e PORTA" com a fase mergeada. Trocar a base muda o que o auditor
    VE; nao muda o que ja esta mergeado.

    O eixo (g) sozinho nao pegava isto: la o rc tambem era 0. O que distingue e o
    TEXTO — laudo declarado ou porta declarada — e por isso este probe le a saida.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        _git(tmp, "init", "-q")
        _git(tmp, "symbolic-ref", "HEAD", "refs/heads/main")
        c0 = _commit(tmp, "base.txt", "0\n", "base: antes da fase")
        _git(tmp, "checkout", "-q", "-b", "fase")
        p1 = _commit(tmp, "peca1.txt", "1\n", "fase-4: peca 1")
        p2 = _commit(tmp, "peca2.txt", "2\n", "fase-4: peca 2")
        _git(tmp, "branch", "-f", "main", p1)  # peca a peca, como o cenario (c)
        _ancora(tmp, c0)
        rc, saida, erro = _roda_cli(
            ["--phase", str(FASE), "--default", "main", "--base", c0, "--head", p2, "--repo", tmp]
        )

    if rc == 0 and "PORTA" not in saida and "JA ESTA em" in erro:
        print("  ok    (h) --base na propria ancora nao declara PORTA: sai LAUDO")
        return True
    print(
        f"  FALHA (h): rc={rc}, saida={saida.strip()[:60]!r} — a base explicita "
        "mudou o veredito em vez de mudar so o diff"
    )
    return False


LANCADOR = REPO_ROOT / "scripts" / "start_checkpoint_audit.sh"


def probe_i() -> bool:
    """(i) O veredito da guarda chega ao PROMPT — lido do prompt MONTADO.

    O B1 da terceira rodada da Fase 3 nao foi so a camada de permissao. No mesmo
    relatorio, no item 6 do que ele nao conseguiu verificar, o auditor escreveu:
    *"Deduzi que sim pela ausencia do bloco de AVISO no prompt"*. O aviso ia para
    o stderr do lancador e morria ali — ele auditou como GATE o que era LAUDO.

    Terceira vez na fase que a declaracao existe, esta correta, e nao chega a
    quem decide com ela: a primeira foi a ordem `autoriza -> degrada` provada em
    comentario, a segunda foi o eixo (h).

    ESTE PROBE EXECUTA A ATRIBUICAO REAL. Ele extrai o bloco `PROMPT=...` do
    proprio lancador e o roda com as variaveis definidas — nao e uma copia da
    linha, e sim a linha. Quem remover `$GUARDA_SAIDA` do prompt derruba isto.

    Limite declarado: a extracao e textual (acha o inicio e o fim do bloco), e o
    resto do lancador nao e exercido aqui — subir Docker e abrir sessao nao cabe
    num probe. A tecnica e a mesma que `check_gate_coverage.py` usa para ler os
    pathspecs do workflow em vez de repeti-los.
    """
    fonte = LANCADOR.read_text(encoding="utf-8")

    if "GUARDA_SAIDA=$(" not in fonte:
        print("  FALHA (i): o lancador nao CAPTURA a saida da guarda")
        return False

    linhas = fonte.splitlines()
    try:
        ini = next(i for i, l in enumerate(linhas) if l.startswith('PROMPT="'))
        fim = next(i for i, l in enumerate(linhas[ini:], ini) if l.rstrip().endswith('."'))
    except StopIteration:
        print("  FALHA (i): nao achei o bloco PROMPT= no lancador")
        return False

    bash = shutil.which("bash")
    if bash is None:
        print("  FALHA (i): este probe precisa de `bash` para montar o prompt de verdade")
        return False

    marca = "AVISO: parte do trabalho da fase 3 JA ESTA em 'x'. LAUDO, e nao porta."
    script = "\n".join(
        [
            "PHASE=3",
            "HEAD_SHA=aaaa",
            "BASE_SHA=bbbb",
            "BASE_REF=main",
            "SERVICOS=ATIVOS",
            f"GUARDA_SAIDA={shlex.quote(marca)}",
            *linhas[ini : fim + 1],
            'printf "%s" "$PROMPT"',
        ]
    )
    montado = subprocess.run(
        [bash, "-c", script], capture_output=True, text=True, check=False
    ).stdout

    if marca in montado:
        print("  ok    (i) o veredito da guarda aparece no PROMPT montado")
        return True
    print(f"  FALHA (i): o PROMPT montado NAO contem o veredito da guarda:\n        {montado[:200]!r}")
    return False


def probe_da_deteccao() -> bool:
    """O probe dos probes: a ancora legitima nao pode ser confundida com outra.

    Sem isto, um `avalia` que sempre devolvesse [] passaria em (a) e (d), e um
    que sempre devolvesse ["ancora"] passaria nos tres eixos (e). O que nenhum
    dos dois faz e DISTINGUIR — e e isso que este probe afirma: a mesma historia,
    com a ancora certa e com a ancora trocada, da resultados diferentes.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        c0, p1, p2 = _cenario(tmp)
        _ancora(tmp, c0)
        certa = {f.eixo for f in avalia(tmp, FASE, "main", p2)}
        _ancora(tmp, p1)
        trocada = {f.eixo for f in avalia(tmp, FASE, "main", p2)}

    if certa == set() and trocada == {"ii"}:
        print("  ok    (deteccao) a ancora trocada muda o veredito: [] -> ['ii']")
        return True
    print(f"  FALHA (deteccao): ancora certa {sorted(certa)}, trocada {sorted(trocada)}")
    return False


def main_probes() -> int:
    print("check_audit_base.py — sete eixos, o oitavo achado rodando, e a deteccao\n")
    resultados = [roda(*p) for p in PROBES]
    resultados.append(probe_g())
    resultados.append(probe_h())
    resultados.append(probe_i())
    resultados.append(probe_da_deteccao())

    print()
    if all(resultados):
        print(
            f"Os {len(resultados)} eixos provam o predicado, e o (c) — merge peca a "
            "peca — e o que o predicado anterior deixava passar em silencio."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
