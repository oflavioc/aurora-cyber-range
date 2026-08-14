#!/usr/bin/env python3
"""Captura e persistencia do relatorio de auditoria de checkpoint.

Modulo compartilhado por dois chamadores:

- `scripts/start_checkpoint_audit.sh` usa a CLI. E o caminho REAL: o launcher
  invoca o auditor como agente de TOPO (`claude --agent`);
- `.claude/hooks/log_audit.py` importa as funcoes. E o caminho hipotetico, que
  so existe se o auditor um dia for despachado como SUBAGENTE.

Por que a captura vive no launcher e nao no hook
------------------------------------------------
`SubagentStop` so dispara para subagente despachado pela ferramenta Agent dentro
de uma sessao. O launcher invoca `claude --agent checkpoint-auditor`, que e
sessao de topo: o evento nunca ocorre, para nenhum valor de `agent_type`. Foi
por isso que nenhum `docs/progress/audit_*.md` jamais foi gravado, e cinco
rodadas precisaram de transcricao manual.

Como a saida de uma sessao INTERATIVA e capturada
-------------------------------------------------
Nao por pipe. O Claude Code entra em modo nao-interativo quando stdout nao e um
TTY (`--help`: "via -p, or when stdout is not a TTY, e.g. piped or redirected
output"). Canalizar a saida para captura-la destruiria justamente a
interatividade que a auditoria existe para ter — e o que sairia seria fluxo de
repaint de TUI, nao documento.

Em vez disso o launcher PRE-ATRIBUI o identificador da sessao (`--session-id`) e
aqui o transcript daquela sessao e lido depois que ela termina. A sessao
permanece 100% interativa, e o identificador deixa de ser descoberto por
heuristica ("arquivo mais recente do diretorio") — origem das tres confusoes de
ID — para ser imposto por quem lanca.

O transcript e localizado pelo NOME DO ARQUIVO (`<session-id>.jsonl`), varrendo
os diretorios de projeto. Reproduzir a regra de sanitizacao de caminho de
diretorio seria depender de convencao interna; o nome do arquivo e o UUID que o
proprio launcher escolheu.

Limite conhecido e sua mitigacao
--------------------------------
O formato do transcript JSONL e interno do Claude Code, sem contrato publico. Se
mudar, a extracao degrada. A mitigacao e a falha ser VISIVEL: registro com
`verdict: "sem_relatorio"` e o motivo, saida diferente de zero, e aviso impresso
em bloco dizendo que o veredito precisa ser transcrito a mao. Codigo de saida no
fim de script longo passa despercebido; a mensagem nao.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_REPORT_CHARS = 200_000

#: Estado do lancamento, gravado ANTES da sessao comecar. E o que torna a
#: captura recuperavel: se o processo do launcher morrer sem executar nada
#: depois da sessao — fechar a janela mata sem dar chance a trap EXIT — o
#: operador roda `--recover` e o arquivo diz qual sessao capturar.
#:
#: Fica FORA do Git (.gitignore). Arquivo de estado versionado sujaria a arvore
#: e bloquearia a verificacao de tree limpo do proprio launcher — foi
#: exatamente o que o audit_log.jsonj versionado + hook SubagentStop causaram.
SESSION_FILE_NAME = ".last_audit_session"


def session_file(root: Path) -> Path:
    return root / "docs" / "progress" / SESSION_FILE_NAME


def write_session(root: Path, info: dict) -> None:
    path = session_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def read_session(root: Path) -> dict | None:
    try:
        return json.loads(session_file(root).read_text(encoding="utf-8"))
    except Exception:
        return None


def git_toplevel(start: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            check=False, text=True, capture_output=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception:
        pass
    return start


def claude_config_dir() -> Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".claude"


def main_worktree_root(start: Path) -> Path:
    """Raiz do worktree PRINCIPAL, mesmo quando invocado de um worktree.

    A auditoria roda em .aurora-worktrees/audit, recriado a cada execucao.
    Gravar relativo ao cwd perde o registro junto com o worktree.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--git-common-dir"],
            check=False, text=True, capture_output=True, timeout=5,
        )
        common = result.stdout.strip()
        if result.returncode == 0 and common:
            path = Path(common)
            if not path.is_absolute():
                path = (start / path).resolve()
            return path.parent if path.name == ".git" else path
    except Exception:
        pass
    return start


def find_transcript(session_id: str) -> Path | None:
    """Transcript da sessao, localizado pelo nome do arquivo.

    Busca por `<session-id>.jsonl` em vez de reconstruir o nome sanitizado do
    diretorio de projeto: o UUID e escolhido por quem lanca, a sanitizacao e
    convencao interna.
    """
    projects = claude_config_dir() / "projects"
    if not projects.is_dir():
        return None
    matches = sorted(projects.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def last_agent_text(transcript: Path) -> str:
    """Ultimo bloco de texto emitido pelo agente, do transcript JSONL."""
    latest = ""
    try:
        with transcript.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                texts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                joined = "\n".join(t for t in texts if t.strip())
                if joined.strip():
                    latest = joined
    except Exception:
        return ""
    return latest


#: Linha de veredito: inicio de linha, com ou sem `#` de titulo e com ou sem
#: enfase. Prosa que apenas mencione a palavra no meio de um paragrafo nao casa.
_VERDICT_LINE = re.compile(r"^\s{0,3}#{0,6}\s*\**\s*VEREDITO\b(.*)$", re.IGNORECASE)
_WORD_PASS = re.compile(r"\bPASS\b")
_WORD_FAIL = re.compile(r"\bFAIL\b")


def detect_verdict(report: str) -> tuple[str, str | None]:
    """Veredito extraido da LINHA de veredito. Devolve (veredito, motivo).

    A versao anterior contava presenca de "PASS"/"FAIL" no texto INTEIRO e, com
    os dois presentes, devolvia FAIL. O formato obrigatorio do auditor tem
    `## VEREDITO: PASS | FAIL` como linha literal — entao TODO relatorio contem
    as duas palavras, e todo PASS era arquivado como FAIL. O mecanismo que
    acabou de eliminar a transcricao manual registraria a primeira aprovacao
    capturada automaticamente como reprovacao.

    Agora o veredito sai da linha de veredito especificamente. Sem linha, ou com
    linha ambigua, grava-se `indeterminado` COM O MOTIVO — nunca um palpite. O
    relatorio segue sendo a fonte autoritativa; este campo e indice, e indice
    que chuta e pior que indice ausente.
    """
    if not report.strip():
        return "sem_relatorio", "relatorio vazio"

    achados: list[tuple[str, str]] = []
    for linha in report.splitlines():
        casou = _VERDICT_LINE.match(linha)
        if not casou:
            continue
        resto = re.sub(r"[*_`:#|]", " ", casou.group(1)).upper()
        tem_pass = bool(_WORD_PASS.search(resto))
        tem_fail = bool(_WORD_FAIL.search(resto))
        if tem_pass and tem_fail:
            return "indeterminado", f"linha de veredito cita PASS e FAIL: {linha.strip()[:120]}"
        if tem_fail:
            achados.append(("FAIL", linha.strip()))
        elif tem_pass:
            achados.append(("PASS", linha.strip()))
        else:
            return "indeterminado", f"linha de veredito sem PASS nem FAIL: {linha.strip()[:120]}"

    if not achados:
        return "indeterminado", "nenhuma linha de veredito encontrada no relatorio"
    distintos = {veredito for veredito, _ in achados}
    if len(distintos) > 1:
        return "indeterminado", (
            "linhas de veredito discordantes: "
            + " | ".join(linha[:60] for _, linha in achados)
        )
    return achados[0][0], None


def persist(root: Path, record: dict, report: str, stamp: str) -> Path | None:
    """Grava audit_<stamp>.md quando ha relatorio e anexa ao audit_log.jsonl."""
    progress = root / "docs" / "progress"
    progress.mkdir(parents=True, exist_ok=True)

    report_file: Path | None = None
    if report:
        report_file = progress / f"audit_{stamp}.md"
        header = (
            f"# Auditoria de checkpoint - {record['ts']}\n\n"
            f"- fase: **{record.get('phase')}**\n"
            f"- commit auditado: `{record.get('head_sha')}`\n"
            f"- session_id: `{record.get('session_id')}`\n"
            f"- modo: `{record.get('mode')}`\n"
            f"- veredito detectado: **{record['verdict']}**\n\n"
            "> Veredito detectado por melhor esforco a partir do relatorio "
            "abaixo, que e a fonte autoritativa.\n\n---\n\n"
        )
        report_file.write_text(header + report + "\n", encoding="utf-8")
        record["report_path"] = report_file.relative_to(root).as_posix()

    with (progress / "audit_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return report_file


def alerta_captura_falhou(motivo: str, session_id: str) -> None:
    """Aviso em bloco. Codigo de saida sozinho passa despercebido."""
    linhas = [
        "CAPTURA DO RELATORIO DE AUDITORIA FALHOU",
        "",
        f"Motivo: {motivo}",
        f"session_id: {session_id}",
        "",
        "A auditoria pode ter rodado normalmente - o que falhou foi a captura.",
        "O VEREDITO E OS FINDINGS PRECISAM SER TRANSCRITOS A MAO para",
        "docs/progress/fase_<n>.md antes de seguir.",
        "",
        "Registrado em docs/progress/audit_log.jsonl com verdict=sem_relatorio.",
        "",
        "Se a sessao ainda existir, tente recuperar antes de transcrever:",
        "    python scripts/audit_report.py --recover",
    ]
    # Largura dimensionada pelo conteudo: motivo longo nao pode quebrar a moldura,
    # que e justamente o que faz o aviso ser notado no fim de um script longo.
    largura = max(len(linha) for linha in linhas) + 6
    borda = "!" * largura
    print("\n" + borda, file=sys.stderr)
    for linha in linhas:
        print(f"!! {linha}".ljust(largura - 2) + "!!", file=sys.stderr)
    print(borda + "\n", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--begin", action="store_true",
                        help="Grava o estado do lancamento e sai. Chamado ANTES da sessao.")
    parser.add_argument("--recover", action="store_true",
                        help="Captura a ultima sessao lancada, lendo o estado gravado "
                             "por --begin. E o comando que o operador roda quando a "
                             "captura automatica nao aconteceu.")
    parser.add_argument("--root")
    parser.add_argument("--session-id")
    parser.add_argument("--phase")
    parser.add_argument("--head-sha")
    parser.add_argument("--mode", choices=["interactive", "headless"])
    parser.add_argument("--launcher-exit", type=int)
    parser.add_argument(
        "--fallback-text",
        help="Arquivo com a saida crua da sessao. So no modo headless, onde o "
             "stdout ja e o relatorio e nao depende do transcript.",
    )
    args = parser.parse_args()

    root = main_worktree_root(
        Path(args.root).resolve() if args.root else git_toplevel(Path.cwd())
    )

    if args.begin:
        write_session(root, {
            "session_id": args.session_id,
            "phase": args.phase,
            "head_sha": args.head_sha,
            "mode": args.mode,
            "fallback_text": args.fallback_text,
        })
        return 0

    if args.recover:
        saved = read_session(root)
        if not saved or not saved.get("session_id"):
            print(
                "Nao ha lancamento de auditoria registrado em "
                f"docs/progress/{SESSION_FILE_NAME}. Nada a recuperar.",
                file=sys.stderr,
            )
            return 1
        args.session_id = saved["session_id"]
        args.phase = saved.get("phase") or "0"
        args.head_sha = saved.get("head_sha") or "desconhecido"
        args.mode = saved.get("mode") or "interactive"
        if args.fallback_text is None:
            args.fallback_text = saved.get("fallback_text")

    faltando = [n for n, v in (("--session-id", args.session_id), ("--phase", args.phase),
                               ("--head-sha", args.head_sha), ("--mode", args.mode))
                if not v]
    if faltando:
        parser.error("faltam argumentos: " + ", ".join(faltando))
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    report = ""
    motivo = ""
    transcript = find_transcript(args.session_id)
    if transcript is None:
        motivo = f"transcript da sessao {args.session_id} nao encontrado"
    else:
        report = last_agent_text(transcript)[:MAX_REPORT_CHARS]
        if not report:
            motivo = f"transcript {transcript.name} nao rendeu texto de agente"

    if not report and args.fallback_text:
        bruto = Path(args.fallback_text)
        try:
            report = bruto.read_text(encoding="utf-8", errors="replace")[:MAX_REPORT_CHARS].strip()
        except Exception as exc:
            motivo = f"{motivo}; fallback ilegivel ({exc})"
        if report:
            motivo = ""

    veredito, veredito_motivo = (
        detect_verdict(report) if report else ("sem_relatorio", motivo or "relatorio vazio")
    )

    record = {
        "ts": now.isoformat(),
        "phase": int(args.phase),
        "head_sha": args.head_sha,
        "session_id": args.session_id,
        "mode": args.mode,
        "launcher_exit": args.launcher_exit,
        "recovered": bool(args.recover),
        "verdict": veredito,
        # Por que o veredito e o que e. Preenchido quando ele NAO saiu limpo de
        # uma linha de veredito — indice que chuta e pior que indice ausente.
        "verdict_reason": veredito_motivo,
        "report_path": None,
        "capture_error": motivo or None,
        "source": "launcher",
    }

    try:
        report_file = persist(root, record, report, stamp)
    except Exception as exc:
        alerta_captura_falhou(f"nao foi possivel gravar o registro ({exc})", args.session_id)
        return 1

    if not report:
        alerta_captura_falhou(motivo or "relatorio vazio", args.session_id)
        return 1

    print(f"\nRelatorio capturado: {report_file.relative_to(root).as_posix()}")
    print(f"Veredito detectado: {record['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
