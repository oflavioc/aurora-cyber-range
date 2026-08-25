#!/usr/bin/env python3
"""P6-9 — a copia instalada do escopo de usuario passa a ser sincronizada.

O DEFEITO QUE ESTE SCRIPT FECHA
================================
`bootstrap.sh` copia tres arquivos versionados para `~/.claude/`, e **ninguem os
mantinha em dia depois disso**. Editar a fonte deixava a copia para tras, e a
copia e a que o Claude Code de fato executa: o auditor rodava constrangido por um
hook que **nao era** o que a arvore declara.

**Tres ocorrencias, todas remediadas a mao.** A ultima foi o PR #56 — editar os
comentarios de `readonly_bash.py` fez `phase0_negative_tests.py` reprovar na hora,
e a correcao foi copiar de novo. O gatilho declarado era *"a proxima auditoria de
checkpoint"*, e nunca foi ele: a divergencia nasce de **qualquer edicao da
fonte**, e edicao da fonte acontece em trabalho comum.

**Deteccao ja existia; o que faltava era o conserto.** `phase0_negative_tests.py`
acusou nas tres vezes. Este script nao acrescenta um segundo detector — ele
**repara**, e reusa o predicado daquele harness.

AS TRES FORMAS, E POR QUE A PRIMEIRA
======================================
A Fase 6 mapeou tres, e o proprietario escolheu esta:

    (1) O LANCADOR SINCRONIZA          <- esta
    (2) o verificador acusa melhor      nao conserta: o harness JA acusa, e o
                                        que falta nao e deteccao
    (3) disciplina declarada            e o que falhou nas tres ocorrencias

POR QUE AQUI, E NAO NO `bootstrap.sh`
======================================
O `bootstrap.sh` roda **uma vez**, na preparacao da maquina. A divergencia nasce
depois, a cada edicao da fonte. O lancador roda **toda auditoria**, e e o unico
momento em que a copia instalada de fato importa: e ele que abre a sessao do
auditor, que e quem o hook constrange.

O CUSTO ACEITO, E ELE E ESTREITO
=================================
**O lancador passa a escrever fora da arvore.** Ate aqui ele so escrevia em
`.aurora-worktrees/`, no worktree e em `docs/progress/`. Agora escreve em
`~/.claude/`.

O precedente e o `bootstrap.sh`, e as guardas dele foram copiadas: escopo
verificado antes de escrever, destino DERIVADO e nunca parametrizavel, razao
declarada no ponto, e **smoke test depois de escrever** — ele nao confia que a
copia deu certo, ele a exercita.

O QUE FICA DE FORA, DECLARADO
==============================
`user-scope/hooks/pre-commit` -> `.git/hooks/pre-commit` **nao entra**. Ele vai
para DENTRO da arvore, e hook do GIT e nao do agente, e e o unico par em que
BYTES importam: `#!/bin/sh` com um CR no shebang fica inexecutavel, e
`sem_carriage_return` o afirma por `read_bytes()`. Sincroniza-lo por linha
apagaria a diferenca que importa nele. Ele continua sendo assunto do
`bootstrap.sh` e da assercao propria.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from phase0_negative_tests import divergem  # noqa: E402

#: O DESTINO E DERIVADO, e nunca parametrizavel — guarda do `bootstrap.sh`.
#:
#: Um destino que viesse de argumento ou de variavel de ambiente faria deste
#: script uma copiadora de arquivos arbitrarios rodando dentro do rito de
#: auditoria. `Path.home()` e a unica origem, e ela e a mesma que
#: `phase0_negative_tests.py` usa para achar a copia que julga.
ESCOPO_DE_USUARIO = Path.home() / ".claude"

#: `rotulo -> (fonte versionada, copia instalada)`.
#:
#: OS TRES PARES, e nao um. Consertar `readonly_bash.py` e deixar os irmaos vivos
#: seria a §9.6 — a correcao que fecha a instancia e deixa a classe viva.
PARES: dict[str, tuple[Path, Path]] = {
    "readonly_bash": (
        REPO_ROOT / "user-scope" / "hooks" / "readonly_bash.py",
        ESCOPO_DE_USUARIO / "hooks" / "readonly_bash.py",
    ),
    "sentinela de branch": (
        REPO_ROOT / "user-scope" / "hooks" / "sentinela_de_branch.py",
        ESCOPO_DE_USUARIO / "hooks" / "sentinela_de_branch.py",
    ),
    "agente checkpoint-auditor": (
        REPO_ROOT / "user-scope" / "agents" / "checkpoint-auditor.md",
        ESCOPO_DE_USUARIO / "agents" / "checkpoint-auditor.md",
    ),
}

#: O SMOKE TEST, na forma de `bootstrap.sh:123-129`: um payload sintetico que o
#: hook TEM de recusar. Nao basta o arquivo estar no lugar — ele tem de rodar.
#:
#: `checkpoint-auditor.md` nao tem smoke: e markdown de governanca, nao programa.
#: A ausencia esta declarada aqui em vez de o dicionario simplesmente nao o
#: trazer — universo que exclui por nao incluir e a forma de "coberto por nada"
#: que `check_allowlist_do_auditor.py` ja registra ter custado duas auditorias.
SMOKE: dict[str, str] = {
    "readonly_bash": '{"tool_input":{"command":"rm -rf range-core"}}',
    "sentinela de branch": (
        '{"hook_event_name":"PreToolUse","session_id":"sincronia",'
        '"tool_name":"Write","cwd":"%s","tool_input":{"file_path":"%s/x.txt"}}'
    ),
}


class SincroniaFalhou(Exception):
    """Nao deu para sincronizar, e a auditoria NAO segue.

    FALHA ALTO, SEMPRE. Degradar para "segue sem sincronizar" seria o defeito
    original com outra roupa: a auditoria abriria com a copia divergente, que e
    exatamente o que esta pendencia existe para impedir. `05` §6 nao tem clausula
    de ambiente, e esta guarda tambem nao.
    """


def _smoke_do_readonly(instalada: Path) -> None:
    """O hook TEM de recusar `rm -rf`. Se liberar, a copia nao serve."""
    resultado = subprocess.run(
        [sys.executable, str(instalada)],
        input=SMOKE["readonly_bash"],
        capture_output=True,
        text=True,
    )
    if resultado.returncode == 0:
        raise SincroniaFalhou(
            f"{instalada} NAO bloqueou `rm -rf range-core` depois de sincronizada.\n"
            "    A copia esta no lugar e nao funciona — e pior que a divergencia, "
            "porque o arquivo certo no lugar certo parece resolvido."
        )


def _smoke_do_sentinela(instalada: Path) -> None:
    """O sentinela tem de RESPONDER — e a resposta depende da branch.

    Ele libera na branch ancorada e recusa fora dela, entao exigir recusa aqui
    seria exigir um resultado que depende de onde quem roda esta. O que se
    afirma e que ele EXECUTA e decide: crash, `ImportError` ou saida vazia
    reprovam; `0` e `2` sao os dois vereditos legitimos.

    E a mesma leitura que `bootstrap.sh:110-119` faz, e pelo mesmo motivo — o
    comentario de la diz que as duas saidas sao corretas e que as direcoes de
    bloqueio sao provadas em repositorio temporario pelo harness negativo.
    """
    payload = SMOKE["sentinela de branch"] % (REPO_ROOT.as_posix(), REPO_ROOT.as_posix())
    resultado = subprocess.run(
        [sys.executable, str(instalada)],
        input=payload,
        capture_output=True,
        text=True,
    )
    if resultado.returncode not in (0, 2):
        raise SincroniaFalhou(
            f"{instalada} nao respondeu como hook: rc={resultado.returncode}.\n"
            f"    stderr: {resultado.stderr.strip()[:300]}\n"
            "    `0` (libera) e `2` (recusa) sao os dois vereditos legitimos; "
            "qualquer outro e o hook nao executando."
        )


SMOKES = {
    "readonly_bash": _smoke_do_readonly,
    "sentinela de branch": _smoke_do_sentinela,
}


def sincroniza(rotulo: str, fonte: Path, instalada: Path) -> str | None:
    """Copia SE precisar, exercita depois, e devolve o que fez — ou `None`.

    **ESCREVE SO QUANDO DIVERGE.** Copiar sempre seria barato e errado: apagaria
    a diferenca entre "estava em dia" e "foi consertado agora", e e essa
    diferenca que aparece na saida e vai para o registro da rodada.

    A ORDEM E: existe? -> diverge? -> copia -> EXERCITA. O smoke vem depois da
    escrita porque e ela que ele julga; antes, ele julgaria a copia velha.
    """
    if not fonte.is_file():
        raise SincroniaFalhou(
            f"a fonte versionada {fonte} nao existe. Sem ela nao ha o que "
            "sincronizar, e a copia instalada deixa de ter origem conferivel."
        )

    # AUSENCIA E DECIDIDA AQUI, e nao no predicado. Para o harness negativo,
    # copia ausente e ESPERADA — o CI nao tem escopo de usuario. Para o lancador,
    # ausente significa COPIAR. As duas leituras estao certas nos seus contextos,
    # e por isso `divergem` nao decide nenhuma das duas.
    if not instalada.exists():
        acao = "instalada (nao existia)"
    elif divergem(fonte, instalada):
        acao = "atualizada (divergia da fonte)"
    else:
        return None

    try:
        instalada.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonte, instalada)
    except OSError as erro:
        raise SincroniaFalhou(
            f"nao foi possivel escrever {instalada}: {erro}.\n"
            "    A auditoria NAO segue: ela abriria com a copia divergente, que "
            "e a P6-9 exatamente."
        ) from erro

    if smoke := SMOKES.get(rotulo):
        smoke(instalada)
    return acao


def main() -> int:
    feitas: list[str] = []
    try:
        for rotulo, (fonte, instalada) in PARES.items():
            if acao := sincroniza(rotulo, fonte, instalada):
                feitas.append(f"{rotulo}: {acao}")
    except SincroniaFalhou as erro:
        print(f"ERRO: escopo de usuario NAO sincronizado.\n\n  {erro}", file=sys.stderr)
        return 1

    if not feitas:
        print(f"Escopo de usuario em dia: {len(PARES)} copias conferidas, nenhuma tocada.")
        return 0

    print(f"Escopo de usuario SINCRONIZADO ({len(feitas)} de {len(PARES)}):")
    for linha in feitas:
        print(f"  {linha}")
    print("  smoke test passou em cada copia escrita que e programa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
