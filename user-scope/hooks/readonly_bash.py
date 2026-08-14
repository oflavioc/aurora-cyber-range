#!/usr/bin/env python3
"""PreToolUse — Bash restrito do checkpoint-auditor."""
from __future__ import annotations

import json
import re
import sys

SAFE_ENV_PREFIX = r"(?:(?:PYTHONDONTWRITEBYTECODE|PYTHONHASHSEED|NODE_ENV)=[^\s]+\s+)*"

ALLOWED = [
    # cat-file, merge-base e for-each-ref sao leitura pura e nao tem forma que
    # escreva: entram sem depender do desenho tokenizado que foi revertido.
    # `git tag` NAO entra: sem operando lista, com operando CRIA, e este
    # casamento textual nao distingue os dois — `git tag -d` passaria.
    rf"^{SAFE_ENV_PREFIX}git\s+(diff|log|show|status|branch|rev-parse|ls-files|cat-file|merge-base|for-each-ref)\b",
    rf"^{SAFE_ENV_PREFIX}(pytest|python\s+-m\s+pytest)\b",
    rf"^{SAFE_ENV_PREFIX}npm\s+(test|run\s+test|run\s+lint|run\s+typecheck)\b",
    rf"^{SAFE_ENV_PREFIX}(ruff|mypy|black\s+--check|eslint|tsc\s+--noEmit)\b",
    rf"^{SAFE_ENV_PREFIX}range-cli\s+scenario\s+(validate|lint|dryrun)\b",
    rf"^{SAFE_ENV_PREFIX}range-cli\s+evidence\s+verify\b",
    rf"^{SAFE_ENV_PREFIX}docker\s+compose\s+(ps|logs|config)\b",
    rf"^{SAFE_ENV_PREFIX}python\s+tools/(?:check_[A-Za-z0-9_.-]+\.py|codegen\.py\s+--check)\b",
    # O harness negativo e a prova central da Fase 0: um verificador que nunca
    # falhou contra violacao plantada e so um script que sai com zero. Sem esta
    # entrada o auditor nao consegue executa-lo e passa a auditar por inferencia
    # de leitura de codigo.
    #
    # Excecao deliberada e delimitada: este script PLANTA arquivos temporarios
    # fora dos verificadores e os remove ao terminar. E escrita instrumental do
    # proprio teste, nao escrita deliberada do auditor. Nenhum outro caminho sob
    # scripts/ e liberado.
    rf"^{SAFE_ENV_PREFIX}python\s+scripts/phase0_negative_tests\.py\s*$",
    # Smoke tests de hook do PHASE_0_CHECKLIST. Nome de arquivo sem barra, entao
    # travessia como .claude/hooks/../../x.py nao casa.
    rf"^{SAFE_ENV_PREFIX}python\s+(?:~/|\$HOME/)?\.claude/hooks/[A-Za-z0-9_.-]+\.py\s*$",
    rf"^{SAFE_ENV_PREFIX}(ls|cat|head|tail|wc|grep|rg|find|tree|diff|stat)\b",
    # printf entra porque os smoke tests alimentam o hook por pipe
    # (printf '{...}' | python .claude/hooks/x.py) e cada segmento do pipe e
    # validado isoladamente. Sem escrita: redirecionamento ja e negado acima.
    rf"^{SAFE_ENV_PREFIX}(pwd|echo|printf|which|env)\b",
]

DENIED_ANYWHERE = [
    (r">\s*\S|>>\s*\S", "redirecionamento de saida para arquivo"),
    (r"\|\s*tee\b", "escrita via tee"),
    (r"\b(rm|mv|cp|chmod|chown|mkdir|touch|truncate)\b", "comando de escrita"),
    # (?!-) impede que `merge-base` case como `merge`: o \b depois de "merge"
    # casa contra o hifen. Era o falso bloqueio registrado em P16, e merge-base
    # e justamente o que o auditor usa para comparar contra main.
    (r"\bgit\s+(commit|push|add|reset|checkout|switch|merge|rebase|clean|restore)\b(?!-)", "git que altera estado"),
    (r"\b(curl|wget|nc|ssh|scp)\b", "acesso de rede"),
    (r"\b(pip|npm)\s+install\b", "instalacao de pacote"),
    (r"\bsed\s+-i\b|\bperl\s+-i\b", "edicao in-place"),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = ((data.get("tool_input") or {}).get("command") or "").strip()
    if not cmd:
        return 0

    for pat, label in DENIED_ANYWHERE:
        if re.search(pat, cmd):
            print(
                f"BLOQUEADO: checkpoint-auditor sem escrita deliberada ({label}).\n"
                f"Comando: {cmd}\nReporte o finding; nao corrija.",
                file=sys.stderr,
            )
            return 2

    for segment in re.split(r"\|\||&&|;|\|", cmd):
        seg = segment.strip()
        if not seg:
            continue
        if not any(re.match(pattern, seg) for pattern in ALLOWED):
            print(
                "BLOQUEADO: comando fora da allowlist do auditor.\n"
                f"Segmento: {seg}\n"
                "Permitido: git de leitura, testes/linters, verificadores, range-cli de validacao e leitura de arquivo.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
