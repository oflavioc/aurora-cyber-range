#!/usr/bin/env python3
"""PreToolUse — Bash restrito do checkpoint-auditor.

Decisao por TOKENS, nao por casamento textual sobre a string bruta.

A versao anterior decidia com regex sobre o comando cru. Isso rendeu quatro
rodadas consecutivas de falsos bloqueios, todos com a MESMA causa: a string
bruta nao distingue sintaxe de shell de conteudo de argumento.

    git rev-parse main 2>/dev/null    ">" casou como redirecionamento
    git ls-files | sort               "sort" fora da allowlist
    grep -n "fase 0\\|phase 0"         split em "|" DENTRO das aspas
    for f in ...; do                  palavra-chave de shell lida como comando
    printf '{"command":"rm -rf x"}'   "rm -rf" casado DENTRO de payload citado

O ultimo modo e o mais grave: e o smoke test prescrito em
PHASE_0_CHECKLIST.md para validar o item 4 da DoD. O auditor ficava impedido de
executar o teste canonico do proprio item que ele audita.

Corrigir modo a modo continuaria rendendo achados, porque cada correcao trata
sintoma. Aqui a causa e trocada: `shlex` tokeniza respeitando aspas,
`punctuation_chars=True` transforma operadores de shell em tokens proprios, e a
decisao passa a olhar a PALAVRA DE COMANDO de cada segmento. Conteudo de
argumento nunca mais e interpretado como comando.

Direcao inversa preservada: escrita deliberada continua bloqueada. A allowlist e
POSITIVA — o que nao esta nela e negado — e o redirecionamento de saida so passa
para /dev/null.

Falha fechada: entrada que nao tokeniza (aspas desbalanceadas) e negada, nao
ignorada.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

# Operadores reconhecidos, mais longos primeiro: `_explode` casa gulosamente.
_PUNCTUATION = set("|&;<>()")
_OPERATORS = (
    "&>>", "||", "&&", ">>", ">&", "<<", "<&", "&>",
    "|", "&", ";", "<", ">", "(", ")",
)

# `(` e `)` separam porque delimitam substituicao de comando: o que estiver
# dentro vira segmento proprio e e validado como comando, nao ignorado.
_SEGMENT_SEPARATORS = {"|", "||", "&&", ";", "&", "(", ")"}

_REDIRECT_OUT = {">", ">>", "&>", "&>>"}
_REDIRECT_DUP = {">&", "<&"}
_REDIRECT_IN = {"<", "<<"}
#: Unico destino de escrita tolerado: descarte. Qualquer outro alvo e arquivo.
_NULL_TARGETS = {"/dev/null"}

#: Cabecalhos cujas palavras seguintes sao DADOS, nao comandos. Um `$(...)`
#: embutido neles ja virou segmento proprio na etapa de separacao.
_WORD_LIST_KEYWORDS = {"for", "case", "select"}
_SHELL_KEYWORDS = {
    "do", "done", "then", "else", "elif", "fi", "esac",
    "while", "until", "if", "{", "}", "!", "time",
}

_SAFE_ENV_VARS = {"PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "NODE_ENV"}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

_GIT_READ_SUBCOMMANDS = {"diff", "log", "show", "status", "branch", "rev-parse", "ls-files"}
_GIT_BRANCH_DESTRUCTIVE = {
    "-d", "-D", "-m", "-M", "-c", "-C",
    "--delete", "--move", "--copy", "--edit-description", "--set-upstream-to",
}

#: Leitura pura. `sort`/`uniq`/`cut`/`tr` entram porque pipeline de leitura
#: precisa deles (modo b). Filtros que executam ou escrevem ficam de fora de
#: proposito: `awk` tem system(), `sed` tem o comando `w`, `xargs` executa.
_PLAIN_READ = {
    "ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "tree", "diff", "stat",
    "pwd", "echo", "printf", "which",
    "sort", "uniq", "cut", "tr",
}

_FIND_EXECUTING = {"-exec", "-execdir", "-delete", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}

#: Nome de arquivo sem barra: travessia como .claude/hooks/../../x.py nao casa.
_PY_HOOK = re.compile(r"^(?:~/|\$HOME/)?(?:\.claude|user-scope)/hooks/[A-Za-z0-9_.-]+\.py$")
_PY_CHECKER = re.compile(r"^tools/check_[A-Za-z0-9_.-]+\.py$")

_DENIED_COMMANDS = {
    "rm": "comando de escrita", "mv": "comando de escrita", "cp": "comando de escrita",
    "chmod": "comando de escrita", "chown": "comando de escrita", "mkdir": "comando de escrita",
    "touch": "comando de escrita", "truncate": "comando de escrita", "dd": "comando de escrita",
    "ln": "comando de escrita", "shred": "comando de escrita",
    "tee": "escrita via tee",
    "curl": "acesso de rede", "wget": "acesso de rede", "nc": "acesso de rede",
    "ssh": "acesso de rede", "scp": "acesso de rede",
    "sed": "edicao in-place possivel (comando `w`)", "perl": "execucao arbitraria",
    "awk": "execucao arbitraria (system())", "xargs": "execucao arbitraria",
    "bash": "execucao arbitraria", "sh": "execucao arbitraria", "zsh": "execucao arbitraria",
    "eval": "execucao arbitraria", "source": "execucao arbitraria",
}


def _blank_quoted(raw: str) -> str:
    """`raw` com todo conteudo entre aspas trocado por espaco.

    Serve para procurar sintaxe (crase) sem casar dentro de payload citado —
    que e exatamente o erro que o modo (e) expunha.
    """
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for char in raw:
        if escaped:
            out.append(" ")
            escaped = False
        elif quote is None and char == "\\":
            escaped = True
            out.append(" ")
        elif quote is not None:
            quote = None if char == quote else quote
            out.append(" ")
        elif char in "'\"":
            quote = char
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def _explode(token: str) -> list[str]:
    """Quebra um token so de pontuacao nos operadores que o compoem.

    `shlex` agrupa pontuacao adjacente: `);` chega como um token unico.
    """
    if not token or not set(token) <= _PUNCTUATION:
        return [token]
    parts: list[str] = []
    index = 0
    while index < len(token):
        for operator in _OPERATORS:
            if token.startswith(operator, index):
                parts.append(operator)
                index += len(operator)
                break
        else:
            return [token]  # desconhecido: devolve intacto, sera negado adiante
    return parts


def _tokenize(raw: str) -> list[str]:
    """Tokens de shell. Levanta ValueError com aspas desbalanceadas."""
    lexer = shlex.shlex(raw, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    # `#` so inicia comentario em inicio de palavra no shell; o shlex cortaria no
    # meio de um argumento (--format=%h#%s). Sem comentarios, nada e descartado.
    lexer.commenters = ""
    tokens: list[str] = []
    for token in lexer:
        tokens.extend(_explode(token))
    return tokens


def _segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SEGMENT_SEPARATORS:
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return [segment for segment in segments if segment]


def _validate_python(args: list[str]) -> str | None:
    if not args:
        return "python sem script abre REPL"
    if args[0] == "-m":
        return None if args[1:2] == ["pytest"] else "python -m fora de pytest"
    if args[0].startswith("-"):
        return f"python {args[0]}: apenas -m pytest ou script explicito"

    script = args[0]
    rest = args[1:]
    if _PY_HOOK.match(script):
        return None if not rest else "hook com argumento extra"
    if _PY_CHECKER.match(script):
        return None
    if script == "tools/codegen.py":
        return None if "--check" in rest else "codegen.py sem --check reescreve artefato"
    # Excecao deliberada e delimitada: o harness negativo PLANTA arquivos
    # temporarios fora dos verificadores e os remove ao terminar. E escrita
    # instrumental do proprio teste, nao escrita deliberada do auditor. Nenhum
    # outro caminho sob scripts/ e liberado.
    if script == "scripts/phase0_negative_tests.py":
        return None if not rest else "harness negativo nao aceita argumento"
    return f"python {script}: script fora da allowlist"


def _validate_command(words: list[str]) -> str | None:
    command = words[0]
    args = words[1:]

    if command in _DENIED_COMMANDS:
        return _DENIED_COMMANDS[command]

    if command in {"pip", "pip3", "npm"} and args[:1] == ["install"]:
        return "instalacao de pacote"

    if command == "git":
        if not args:
            return "git sem subcomando"
        subcommand = args[0]
        if subcommand not in _GIT_READ_SUBCOMMANDS:
            return f"git {subcommand}: fora do conjunto de leitura"
        if subcommand == "branch" and any(a in _GIT_BRANCH_DESTRUCTIVE for a in args[1:]):
            return "git branch com flag destrutiva"
        return None

    if command in {"python", "python3"}:
        return _validate_python(args)

    if command == "npm":
        if args[:1] == ["test"]:
            return None
        if args[:1] == ["run"] and args[1:2] and args[1] in {"test", "lint", "typecheck"}:
            return None
        return "npm fora de test/lint/typecheck"

    if command == "range-cli":
        if args[:1] == ["scenario"] and args[1:2] and args[1] in {"validate", "lint", "dryrun"}:
            return None
        if args[:2] == ["evidence", "verify"]:
            return None
        return "range-cli fora dos subcomandos de validacao"

    if command == "docker":
        if args[:1] == ["compose"] and args[1:2] and args[1] in {"ps", "logs", "config"}:
            return None
        return "docker fora de compose ps/logs/config"

    if command == "env":
        # `env CMD` executa CMD, escapando a allowlist inteira. So `env` puro.
        return None if not args else "env com operando executa comando arbitrario"

    if command == "find":
        found = [a for a in args if a in _FIND_EXECUTING]
        return f"find com acao de escrita/execucao ({found[0]})" if found else None

    if command == "black":
        return None if "--check" in args else "black sem --check reescreve arquivo"

    if command == "tsc":
        return None if "--noEmit" in args else "tsc sem --noEmit emite arquivo"

    if command in {"pytest", "ruff", "mypy", "eslint"}:
        return None

    if command in _PLAIN_READ:
        return None

    return f"'{command}' fora da allowlist do auditor"


def _check_segment(segment: list[str]) -> str | None:
    words: list[str] = []
    index = 0
    while index < len(segment):
        token = segment[index]
        if token == "$":
            # Sobra de `$(`; o conteudo ja virou segmento proprio.
            index += 1
        elif token in _REDIRECT_OUT:
            target = segment[index + 1] if index + 1 < len(segment) else ""
            if target not in _NULL_TARGETS:
                return f"redirecionamento de saida para arquivo ({target or 'alvo ausente'})"
            index += 2
        elif token in _REDIRECT_DUP or token in _REDIRECT_IN:
            index += 2
        else:
            words.append(token)
            index += 1

    if not words:
        return None
    if words[0] in _WORD_LIST_KEYWORDS:
        return None
    while words and words[0] in _SHELL_KEYWORDS:
        words.pop(0)
    while words and _ASSIGNMENT.match(words[0]):
        name = words[0].split("=", 1)[0]
        if name not in _SAFE_ENV_VARS:
            return f"atribuicao de ambiente '{name}' antes do comando"
        words.pop(0)
    if not words:
        return None
    return _validate_command(words)


def _block(command: str, motivo: str) -> int:
    print(
        f"BLOQUEADO: checkpoint-auditor sem escrita deliberada ({motivo}).\n"
        f"Comando: {command}\n"
        "Permitido: git de leitura, testes/linters, verificadores, range-cli de "
        "validacao, leitura de arquivo e filtros de texto.\n"
        "Reporte o finding; nao corrija.",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    command = ((data.get("tool_input") or {}).get("command") or "").strip()
    if not command:
        return 0

    if "`" in _blank_quoted(command):
        return _block(command, "substituicao de comando por crase")

    try:
        tokens = _tokenize(command)
    except ValueError as exc:
        return _block(command, f"nao tokeniza ({exc})")

    for segment in _segments(tokens):
        motivo = _check_segment(segment)
        if motivo:
            return _block(command, motivo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
