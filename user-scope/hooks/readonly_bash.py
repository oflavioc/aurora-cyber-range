#!/usr/bin/env python3
"""PreToolUse — Bash restrito do checkpoint-auditor.

Tokenizar foi acerto para PARSEAR. O erro foi usar a tokenizacao para
CLASSIFICAR operadores com mais precisao, em vez de IDENTIFICA-los com mais
confiabilidade e bloquear todos.

A versao em regex era falso-positiva: bloqueava `>&` por acidente, sem saber o
que era. Irritante, mas fechada. A versao que a substituiu sabia que `>&` era
duplicacao de descritor, criou um caminho proprio para ele e pulou o alvo sem
validar — falso-negativa. Precisao de classificacao virou justificativa para
liberar. `ls >& ../../CLAUDE.md` passava.

Dois principios agora, os dois default-deny:

1. TODO token de redirecionamento bloqueia. Sem distinguir >, >>, >&, &>, &>>,
   >|, <, <<, <&, <>. Excecao apenas para duas sequencias EXATAS de token:
   `2>/dev/null` e `2>&1`. Forma desconhecida e bloqueada, nunca liberada.
   Token de pontuacao que nao decompoe em operador conhecido tambem bloqueia
   EXPLICITAMENTE — nao por acidente de virar palavra de comando desconhecida.
   Acidente nao e garantia, e foi assim que `>&` passou.

2. Allowlist de FLAGS por comando, nao so de comandos. Comando permitido com
   flag nao reconhecida bloqueia. Sem isto, `sort -o`, `pytest --junitxml`,
   `ruff --output-file`, `eslint -o` e `tsc --outFile` escrevem sem usar
   redirecionamento nenhum. Posicionais tambem sao limitados onde o comando
   escreve por posicao.

`find` e `uniq` sairam da allowlist: superficie grande demais para o valor que
entregam. `git ls-files` e `rg` cobrem `find`; `sort -u` cobre `uniq`.

Scripts de hook sao allowlistados por NOME, nao por curinga. Allowlistar
`.claude/hooks/*.py` deixava o commit sob auditoria definir o comportamento de
um comando que o auditor esta pre-autorizado a rodar — o mesmo argumento que
mantem o checkpoint-auditor fora do repositorio.

Limite declarado, nao fechado: `pytest` roda testes do commit auditado e
`tools/check_*.py` e codigo do commit auditado. A propriedade e inerente a
auditoria e nao da para eliminar. A linha que da para segurar e: script cujo
proposito e VERIFICAR, sim; script que ESCREVE, nao.

Falha fechada: entrada que nao tokeniza e negada.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

_PUNCTUATION = set("|&;<>()")
_OPERATORS = (
    "&>>", "<<<", "||", "&&", ">>", ">&", "<<", "<&", "&>", ">|", "<>",
    "|", "&", ";", "<", ">", "(", ")",
)
_SEGMENT_SEPARATORS = {"|", "||", "&&", ";", "&", "(", ")"}
_REDIRECTIONS = {">", ">>", ">&", "&>", "&>>", ">|", "<", "<<", "<&", "<>", "<<<"}

#: As DUAS unicas formas toleradas, casadas como sequencia exata de tokens.
#: `2>/dev/null` tokeniza em ('2','>','/dev/null'); a comparacao por tupla nao
#: admite `2>/dev/null/../x` nem espacamento criativo. `>/dev/null` sem fd NAO
#: entra de proposito: acrescentar excecao "obvia" e como a familia P8/P16/P23
#: nasceu. Se o auditor precisar, ele bate no bloqueio e o operador decide.
_ALLOWED_REDIRECTS = (
    ("2", ">", "/dev/null"),
    ("2", ">&", "1"),
)

_WORD_LIST_KEYWORDS = {"for", "case", "select"}
_SHELL_KEYWORDS = {
    "do", "done", "then", "else", "elif", "fi", "esac",
    "while", "until", "if", "{", "}", "!", "time",
}

_SAFE_ENV_VARS = {"PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "NODE_ENV"}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NUMERIC_SHORT = re.compile(r"^-\d+$")

#: Hooks-guarda: leem stdin e imprimem. `log_audit.py` NAO esta aqui — ele
#: grava, e allowlistar um script e allowlistar o que ele faz.
_GUARD_HOOKS = {
    "check_architecture.py",
    "readonly_bash.py",
    "scenario_scope.py",
    "scenario_bash.py",
}
_HOOK_PATH = re.compile(r"^(?:~/|\$HOME/)?(?:\.claude|user-scope)/hooks/([A-Za-z0-9_.-]+\.py)$")
_TOOLS_CHECKER = re.compile(r"^tools/check_[A-Za-z0-9_.-]+\.py$")


def _spec(long=(), short="", long_value=(), short_value="",
          max_positional=None, numeric_short=False):
    return {
        "long": set(long),
        "short": set(short),
        "long_value": set(long_value),
        "short_value": set(short_value),
        "max_positional": max_positional,
        "numeric_short": numeric_short,
    }


_GIT_SUBCOMMANDS = {
    "log": _spec(
        long=("--oneline", "--stat", "--numstat", "--shortstat", "--graph", "--format",
              "--pretty", "--date", "--max-count", "--reverse", "--name-only",
              "--name-status", "--no-merges", "--merges", "--author", "--since",
              "--until", "--follow", "--patch", "--no-patch", "--first-parent", "--all"),
        short="npS", short_value="nS",
        long_value=("--max-count", "--author", "--since", "--until"),
        numeric_short=True,
    ),
    "diff": _spec(
        long=("--stat", "--numstat", "--shortstat", "--name-only", "--name-status",
              "--cached", "--staged", "--unified", "--no-color", "--word-diff",
              "--find-renames", "--quiet"),
        short="U", short_value="U", long_value=("--unified",),
    ),
    "show": _spec(
        long=("--stat", "--name-only", "--name-status", "--format", "--pretty",
              "--oneline", "--no-patch", "--numstat"),
        short="s",
    ),
    "status": _spec(
        long=("--short", "--porcelain", "--branch", "--untracked-files", "--no-color"),
        short="sbu", long_value=("--untracked-files",),
    ),
    #: -d/-D/-m/-M/-c/-C e --delete/--move/--copy simplesmente nao estao aqui:
    #: default-deny torna a lista de flags destrutivas desnecessaria.
    "branch": _spec(
        long=("--list", "--all", "--remotes", "--verbose", "--contains",
              "--merged", "--no-merged", "--show-current", "--format"),
        short="lavr", long_value=("--contains", "--merged", "--no-merged"),
    ),
    "rev-parse": _spec(
        long=("--short", "--verify", "--abbrev-ref", "--show-toplevel", "--git-dir",
              "--git-common-dir", "--is-inside-work-tree", "--quiet"),
        short="q",
    ),
    "ls-files": _spec(
        long=("--others", "--exclude-standard", "--cached", "--modified", "--deleted",
              "--error-unmatch", "--full-name"),
        short="ocmdz",
    ),
}

_COMMANDS = {
    "ls": _spec(long=("--all", "--long", "--human-readable", "--reverse", "--recursive",
                      "--color", "--almost-all"), short="laAhrtRS1FdU"),
    "cat": _spec(long=("--number", "--show-ends"), short="nAE"),
    "head": _spec(long=("--lines", "--bytes"), short="nc", short_value="nc",
                  long_value=("--lines", "--bytes"), numeric_short=True),
    "tail": _spec(long=("--lines", "--bytes"), short="nc", short_value="nc",
                  long_value=("--lines", "--bytes"), numeric_short=True),
    "wc": _spec(long=("--lines", "--words", "--chars", "--bytes"), short="lwmc"),
    "grep": _spec(
        long=("--line-number", "--recursive", "--extended-regexp", "--fixed-strings",
              "--ignore-case", "--invert-match", "--count", "--files-with-matches",
              "--only-matching", "--word-regexp", "--after-context", "--before-context",
              "--context", "--include", "--exclude", "--exclude-dir", "--color",
              "--regexp", "--no-messages"),
        short="nrREFivclowABCes", short_value="ABCe",
        long_value=("--after-context", "--before-context", "--context", "--include",
                    "--exclude", "--exclude-dir", "--regexp"),
    ),
    "rg": _spec(
        long=("--line-number", "--no-heading", "--fixed-strings", "--ignore-case",
              "--invert-match", "--count", "--files-with-matches", "--only-matching",
              "--word-regexp", "--glob", "--type", "--hidden", "--no-ignore",
              "--context", "--color", "--multiline", "--max-count"),
        short="nFivclowgtSU", short_value="gtC",
        long_value=("--glob", "--type", "--context", "--max-count"),
    ),
    "tree": _spec(long=("--dirsfirst", "--level"), short="daLfi", short_value="L",
                  long_value=("--level",)),
    "diff": _spec(long=("--unified", "--recursive", "--brief", "--side-by-side"),
                  short="urqy", short_value="u", long_value=("--unified",)),
    "stat": _spec(long=("--format", "--terse"), short="ct", short_value="c",
                  long_value=("--format",)),
    "pwd": _spec(),
    "echo": _spec(short="ne"),
    "printf": _spec(),
    "which": _spec(short="a"),
    #: -o/--output nao estao aqui. Era por ali que `sort` escrevia.
    "sort": _spec(long=("--numeric-sort", "--reverse", "--unique", "--key",
                        "--field-separator", "--version-sort", "--ignore-case"),
                  short="nruktVf", short_value="kt",
                  long_value=("--key", "--field-separator")),
    "cut": _spec(long=("--fields", "--delimiter", "--characters", "--bytes"),
                 short="fdcb", short_value="fdcb",
                 long_value=("--fields", "--delimiter", "--characters", "--bytes")),
    "tr": _spec(long=("--delete", "--squeeze-repeats"), short="dsc"),
    "pytest": _spec(long=("--quiet", "--verbose", "--tb", "--maxfail", "--no-header",
                          "--color", "--durations", "--last-failed", "--exitfirst"),
                    short="qvxsk", short_value="k",
                    long_value=("--maxfail", "--durations")),
    "ruff": _spec(long=("--select", "--ignore", "--statistics", "--quiet",
                        "--no-cache", "--output-format", "--config"),
                  short="q", long_value=("--select", "--ignore", "--output-format",
                                         "--config")),
    "mypy": _spec(long=("--strict", "--ignore-missing-imports", "--no-error-summary",
                        "--show-error-codes", "--pretty", "--config-file"),
                  long_value=("--config-file",)),
    "eslint": _spec(long=("--ext", "--format", "--max-warnings", "--no-eslintrc",
                          "--quiet"),
                    long_value=("--ext", "--format", "--max-warnings")),
    "black": _spec(long=("--check", "--diff", "--quiet"), short="q"),
    "tsc": _spec(long=("--noEmit", "--project", "--pretty", "--strict"),
                 short="p", short_value="p", long_value=("--project",)),
    "npm": _spec(long=("--silent", "--if-present"), short="s"),
    "docker": _spec(long=("--tail", "--no-color", "--follow"), short="f",
                    long_value=("--tail",)),
    "range-cli": _spec(),
    "env": _spec(max_positional=0),
}


def _blank_quoted(raw: str) -> str:
    """`raw` com conteudo entre aspas trocado por espaco."""
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
    """Quebra token de pontuacao nos operadores que o compoem.

    Token que NAO decompoe inteiramente e devolvido intacto e sera bloqueado
    explicitamente por `_unknown_punctuation`.
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
            return [token]
    return parts


def _unknown_punctuation(token: str) -> bool:
    """Token so de pontuacao que nao e operador conhecido."""
    return bool(token) and set(token) <= _PUNCTUATION and token not in _OPERATORS


def _tokenize(raw: str) -> list[str]:
    lexer = shlex.shlex(raw, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens: list[str] = []
    for token in lexer:
        tokens.extend(_explode(token))
    return tokens


def _strip_allowed_redirects(tokens: list[str]) -> list[str]:
    out: list[str] = []
    index = 0
    while index < len(tokens):
        for pattern in _ALLOWED_REDIRECTS:
            if tuple(tokens[index:index + len(pattern)]) == pattern:
                index += len(pattern)
                break
        else:
            out.append(tokens[index])
            index += 1
    return out


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


def _check_flags(label: str, spec: dict, args: list[str]) -> str | None:
    positional = 0
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            positional += len(args) - index - 1
            break
        if token.startswith("--"):
            name, separator, _ = token.partition("=")
            if name not in spec["long"]:
                return f"{label}: flag '{name}' fora da allowlist"
            if not separator and name in spec["long_value"]:
                index += 1
        elif token.startswith("-") and len(token) > 1:
            if spec["numeric_short"] and _NUMERIC_SHORT.match(token):
                index += 1
                continue
            letters = token[1:]
            position = 0
            while position < len(letters):
                letter = letters[position]
                if letter not in spec["short"]:
                    return f"{label}: flag '-{letter}' fora da allowlist"
                if letter in spec["short_value"]:
                    if position + 1 == len(letters):
                        index += 1  # valor vem no proximo token
                    break            # resto do token e o valor
                position += 1
        else:
            positional += 1
        index += 1
    maximum = spec["max_positional"]
    if maximum is not None and positional > maximum:
        return f"{label}: {positional} argumentos posicionais, maximo {maximum}"
    return None


def _validate_python(args: list[str]) -> str | None:
    if not args:
        return "python sem script abre REPL"
    if args[0] == "-m":
        if args[1:2] != ["pytest"]:
            return "python -m fora de pytest"
        return _check_flags("pytest", _COMMANDS["pytest"], args[2:])
    if args[0].startswith("-"):
        return f"python {args[0]}: apenas -m pytest ou script explicito"

    script, rest = args[0], args[1:]

    hook = _HOOK_PATH.match(script)
    if hook:
        if hook.group(1) not in _GUARD_HOOKS:
            return (f"python {script}: script de hook fora da lista de guardas "
                    "(guarda le stdin e imprime; script que grava nao entra)")
        return None if not rest else "hook-guarda nao aceita argumento"

    if _TOOLS_CHECKER.match(script):
        return None
    if script == "tools/codegen.py":
        return None if "--check" in rest else "codegen.py sem --check reescreve artefato"
    # Excecao deliberada e delimitada: o harness negativo planta arquivos
    # temporarios fora dos verificadores e os remove ao terminar.
    if script == "scripts/phase0_negative_tests.py":
        return None if not rest else "harness negativo nao aceita argumento"
    return f"python {script}: script fora da allowlist"


def _validate_command(words: list[str]) -> str | None:
    command, args = words[0], words[1:]

    if command in {"python", "python3"}:
        return _validate_python(args)

    if command == "git":
        if not args:
            return "git sem subcomando"
        subcommand = args[0]
        spec = _GIT_SUBCOMMANDS.get(subcommand)
        if spec is None:
            return f"git {subcommand}: fora do conjunto de leitura"
        return _check_flags(f"git {subcommand}", spec, args[1:])

    if command == "npm":
        if args[:1] == ["test"]:
            return _check_flags("npm test", _COMMANDS["npm"], args[1:])
        if args[:1] == ["run"] and args[1:2] and args[1] in {"test", "lint", "typecheck"}:
            return _check_flags("npm run", _COMMANDS["npm"], args[2:])
        return "npm fora de test/lint/typecheck"

    if command == "range-cli":
        if args[:1] == ["scenario"] and args[1:2] and args[1] in {"validate", "lint", "dryrun"}:
            return _check_flags("range-cli scenario", _COMMANDS["range-cli"], args[2:])
        if args[:2] == ["evidence", "verify"]:
            return _check_flags("range-cli evidence", _COMMANDS["range-cli"], args[2:])
        return "range-cli fora dos subcomandos de validacao"

    if command == "docker":
        if args[:1] == ["compose"] and args[1:2] and args[1] in {"ps", "logs", "config"}:
            return _check_flags("docker compose", _COMMANDS["docker"], args[2:])
        return "docker fora de compose ps/logs/config"

    if command == "ruff":
        if args[:1] not in ([], ["check"], ["format"]):
            return "ruff fora de check/format"
        rest = args[1:] if args[:1] in (["check"], ["format"]) else args
        if args[:1] == ["format"] and "--check" not in rest and "--diff" not in rest:
            return "ruff format sem --check reescreve arquivo"
        return _check_flags("ruff", _COMMANDS["ruff"], rest)

    if command == "black":
        if "--check" not in args and "--diff" not in args:
            return "black sem --check reescreve arquivo"
        return _check_flags("black", _COMMANDS["black"], args)

    if command == "tsc":
        if "--noEmit" not in args:
            return "tsc sem --noEmit emite arquivo"
        return _check_flags("tsc", _COMMANDS["tsc"], args)

    spec = _COMMANDS.get(command)
    if spec is None:
        return f"'{command}' fora da allowlist do auditor"
    return _check_flags(command, spec, args)


def _check_segment(segment: list[str]) -> str | None:
    for token in segment:
        if _unknown_punctuation(token):
            return f"pontuacao de shell nao reconhecida ({token})"

    remaining = _strip_allowed_redirects(segment)
    for token in remaining:
        if token in _REDIRECTIONS:
            return (f"redirecionamento ({token}); so `2>/dev/null` e `2>&1` sao "
                    "tolerados, em forma exata")

    words = [token for token in remaining if token != "$"]
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
        "A allowlist e de COMANDOS e de FLAGS: comando permitido com flag nao\n"
        "reconhecida tambem bloqueia. Se a flag for de leitura e faltar na lista,\n"
        "reporte como finding em vez de contornar; nao corrija.",
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
