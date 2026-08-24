#!/usr/bin/env python3
"""Prova que o interpretador do checkout auditado e alcancavel — e so ele.

O QUE ESTA PROVA EXISTE PARA FECHAR
------------------------------------
O B1 da auditoria da Fase 6: o auditor nao conseguiu executar a suite e voltou a
avaliar por leitura. A FORMA estava admitida — `python -m unittest discover -s
tests` casa na allowlist desde a Fase 2 — e o INTERPRETADOR nao era alcancavel: o
venv nascia fora do worktree e o lancador o exportava por `PATH`, que nao
atravessa para a ferramenta de Bash do auditor.

A correcao move o venv para dentro do worktree e admite o caminho literal dele na
allowlist. **Sem esta prova, a proxima auditoria descobriria o mesmo buraco de
novo** — que foi o que aconteceu tres vezes: H3 da Fase 1 (comando ausente da
lista), B1 da Fase 2 (forma ausente da lista), B1 da Fase 6 (interpretador
inalcancavel com a forma presente).

AS DUAS DIRECOES, E A SEGUNDA E A QUE PROVA QUE A PRIMEIRA GENERALIZA
----------------------------------------------------------------------
So a direcao positiva seria *"o comando que eu escrevi funciona"*, que nao afirma
nada sobre o que continua fechado. Um `(?:.*/)?python` teria passado nela e
aberto a porta para qualquer interpretador da maquina.

O QUE A CONTENCAO DECIDE, MEDIDO E NAO SUPOSTO
-----------------------------------------------
`_alvo_nao_contido` julga **caminho absoluto**, e trata relativo como contido por
construcao — porque o cwd E o worktree, e o lancador o garante com `cd "$WT"`.

Entao os dois portoes se dividem assim, e a prova exercita os dois:

  - a **allowlist** recusa toda grafia que nao seja a literal: `..`, absoluto, e
    o sufixo fora da forma exata;
  - a **contencao** recusa o absoluto que aponte para fora do worktree, inclusive
    um venv HOMONIMO em outra arvore.

O limite fica dito: a grafia relativa e contida **porque o cwd e o worktree**.
Essa propriedade e anterior a esta correcao e nao foi afrouxada por ela — o que
se acrescentou foi um caminho literal, e nao uma excecao.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "user-scope" / "hooks" / "readonly_bash.py"

RULE = "B1 da Fase 6 - o interpretador do checkout auditado"

#: O worktree que o lancador cria. Os casos absolutos sao resolvidos contra ele.
WORKTREE = (REPO_ROOT / ".aurora-worktrees" / "audit").as_posix()

#: O caminho do venv DENTRO do worktree — o mesmo que
#: `start_checkpoint_audit.sh` cria em `$WT/.aurora-audit/venv`.
DENTRO = ".aurora-audit/venv"


def carrega_hook():
    """A FONTE VERSIONADA, e nao a copia instalada.

    O que esta sob prova e a regra que este PR altera. A divergencia entre a
    fonte e a copia de `~/.claude/hooks/` tem verificador proprio, no harness
    negativo da Fase 0.
    """
    spec = importlib.util.spec_from_file_location("readonly_bash_para_prova", HOOK)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def permitido(hook, comando: str) -> bool:
    """A allowlist, com o prefixo de ambiente removido como o hook faz."""
    resto = re.sub(rf"^{hook.SAFE_ENV_PREFIX}", "", comando.strip())
    return any(re.match(padrao, resto) for padrao in hook.ALLOWED)


#: DIRECAO POSITIVA — o interpretador do checkout, nas formas que o lancador
#: imprime. `bin` e `Scripts` porque o venv nomeia o diretorio conforme o SO, e
#: uma prova que so cobrisse um passaria no CI e falharia na maquina do operador.
ALCANCAVEIS = (
    f"{DENTRO}/bin/python -m unittest discover -s tests",
    f"{DENTRO}/Scripts/python -m unittest discover -s tests",
    f"{DENTRO}/bin/python tools/check_core_boundary.py",
    f"{DENTRO}/Scripts/python tools/codegen.py --check",
    f"{DENTRO}/bin/python scripts/phase0_negative_tests.py",
    # O `python` nu continua admitido: o prefixo e OPCIONAL, e retirar a forma
    # antiga quebraria todo comando que o auditor ja sabe escrever.
    "python -m unittest discover -s tests",
)

#: DIRECAO NEGATIVA — o que a ALLOWLIST recusa, por grafia.
#:
#: Cada linha e uma forma que um `(?:.*/)?python` teria admitido. Elas sao a
#: diferenca entre "caminho literal" e "qualquer caminho", e sao o motivo de a
#: doutrina do arquivo ser FORMA EXATA e nao familia.
RECUSADOS_PELA_ALLOWLIST = {
    "caminho relativo saindo do worktree":
        f"../{DENTRO}/bin/python -m unittest discover -s tests",
    "caminho absoluto, mesmo apontando para dentro":
        f"{WORKTREE}/{DENTRO}/bin/python -m unittest discover -s tests",
    "interpretador da maquina por caminho":
        "/usr/bin/python -m unittest discover -s tests",
    "py launcher, recusado por dar interpretador da maquina":
        "py -3.12 -m unittest discover -s tests",
    "venv com outro nome, dentro do worktree":
        ".venv/bin/python -m unittest discover -s tests",
    "diretorio de binarios inventado":
        f"{DENTRO}/libexec/python -m unittest discover -s tests",
    "sufixo fora da forma exata do unittest":
        f"{DENTRO}/bin/python -m unittest discover -s /outra/arvore",
    "modulo arbitrario por nome":
        f"{DENTRO}/bin/python -m http.server",
    "script de scripts/ que nao esta na allowlist":
        f"{DENTRO}/bin/python scripts/apaga_tudo.py",
}

#: DIRECAO NEGATIVA — o que a CONTENCAO recusa, por resolucao contra o cwd.
#:
#: O VENV HOMONIMO FORA DO WORKTREE e o caso que importa: mesma grafia de
#: diretorio, arvore diferente. Se a contencao nao o pegasse, o auditor mediria o
#: commit errado com um caminho que parece certo — a classe do
#: `check_prova_do_seed` medindo outra arvore.
RECUSADOS_PELA_CONTENCAO = {
    "venv HOMONIMO em outra arvore":
        f"/c/outra-arvore/{DENTRO}/bin/python -m unittest discover -s tests",
    "venv da arvore principal, fora do worktree":
        f"{REPO_ROOT.as_posix()}/{DENTRO}/bin/python -m unittest discover -s tests",
    "leitura de diagnostico fora do worktree":
        "cat /c/outra-arvore/.aurora-audit/stack.log",
}


def main() -> int:
    hook = carrega_hook()
    falhas: list[str] = []

    for comando in ALCANCAVEIS:
        if permitido(hook, comando):
            print(f"  alcancavel, como devia: {comando}")
        else:
            falhas.append(f"a allowlist RECUSA o interpretador do checkout: {comando}")

    for nome, comando in RECUSADOS_PELA_ALLOWLIST.items():
        if permitido(hook, comando):
            falhas.append(f"a allowlist ADMITE o que nao devia — {nome}: {comando}")
        else:
            print(f"  recusado pela allowlist, como devia: {nome}")

    for nome, comando in RECUSADOS_PELA_CONTENCAO.items():
        if hook._alvo_nao_contido(comando, WORKTREE) is None:
            falhas.append(f"a contencao ACEITA o que nao devia — {nome}: {comando}")
        else:
            print(f"  recusado pela contencao, como devia: {nome}")

    # O POSITIVO DA CONTENCAO, e ele existe para a prova nao passar por uma
    # contencao que recusasse tudo: o alvo absoluto DENTRO do worktree passa.
    dentro_absoluto = f"{WORKTREE}/{DENTRO}/bin/python"
    if hook._alvo_nao_contido(dentro_absoluto, WORKTREE) is not None:
        falhas.append(
            "a contencao recusa alvo absoluto DENTRO do worktree: ela reprova "
            "tudo, e as recusas acima nao provam nada"
        )
    else:
        print("  aceito pela contencao, como devia: alvo absoluto dentro do worktree")

    if falhas:
        print(file=sys.stderr)
        for falha in falhas:
            print(f"{RULE}: {falha}", file=sys.stderr)
        return 1

    print()
    print(
        f"{len(ALCANCAVEIS)} formas alcancaveis, "
        f"{len(RECUSADOS_PELA_ALLOWLIST)} recusadas pela allowlist, "
        f"{len(RECUSADOS_PELA_CONTENCAO)} pela contencao, mais o positivo dela."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
