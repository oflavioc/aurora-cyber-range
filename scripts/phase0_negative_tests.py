#!/usr/bin/env python3
"""Probes externos: cada verificador da Fase 0 deve falhar contra uma violacao plantada."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: readonly_bash.py vive em duas copias: a versionada (fonte) e a instalada em
#: ~/.claude/hooks/, que e a que o Claude Code realmente executa. Os probes
#: rodam contra a FONTE, e `hook_copies_in_sync` cobre a diferenca entre as duas.
READONLY_HOOK_SOURCE = ROOT / "user-scope" / "hooks" / "readonly_bash.py"
READONLY_HOOK_INSTALLED = Path.home() / ".claude" / "hooks" / "readonly_bash.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


@contextmanager
def temporary_file(relative: str, content: str):
    path = ROOT / relative
    backup = None
    existed = path.exists()
    if existed:
        backup = path.read_bytes()

    created_dirs: list[Path] = []
    parent = path.parent
    missing: list[Path] = []
    while parent != ROOT and not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir()
        created_dirs.append(directory)

    path.write_text(content, encoding="utf-8")
    try:
        yield path
    finally:
        if existed:
            path.write_bytes(backup or b"")
        else:
            path.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass


def _reject(label: str, motivo: str, saida: str) -> None:
    print(f"FAIL: {label} {motivo}")
    if saida.strip():
        print(saida.strip())
    raise SystemExit(1)


def expect_fail(label: str, command: list[str], planted: str) -> None:
    """Exige DETECCAO, nao apenas saida diferente de zero.

    Aceitar qualquer rc != 0 torna crash de ferramenta (rc=2, contrato
    malformado, arquivo ilegivel) indistinguivel de deteccao (rc=1). Um
    verificador que quebra ao ser executado passaria no teste negativo sem
    nunca ter enxergado a violacao.

    Por isso sao tres exigencias: rc exatamente 1, saida nao vazia, e mencao
    explicita ao arquivo plantado.
    """
    result = run(*command)
    saida = (result.stdout or "") + (result.stderr or "")

    if result.returncode == 0:
        _reject(label, "nao detectou a violacao plantada", saida)

    if result.returncode != 1:
        _reject(
            label,
            f"saiu com rc={result.returncode}, esperado 1. "
            "rc diferente de 1 indica erro de ferramenta, nao deteccao",
            saida,
        )

    if planted not in saida.replace("\\", "/"):
        _reject(
            label,
            f"saiu com rc=1 mas nao citou o arquivo plantado '{planted}'. "
            "Deteccao sem localizacao nao permite intervir",
            saida,
        )

    print(f"OK: {label} detectou violacao em {planted} (rc=1)")


# --------------------------------------------------------------------------
# Probes do hook readonly_bash.py — NAS DUAS DIRECOES.
#
# So testar bloqueio produz um guarda que bloqueia tudo e passa no teste. Foi
# assim que quatro rodadas seguidas renderam falso bloqueio sem nenhum teste
# reprovar: o harness cobria "nega escrita" e nunca "libera leitura".
# --------------------------------------------------------------------------

#: Estado MEDIDO do hook, nas quatro combinacoes possiveis. Depois da reversao
#: do P23 (ver fase_0.md, P23 reaberto) o hook volta ao casamento textual, que
#: erra nas DUAS direcoes. Registrar so o que ele acerta seria a mesma falha que
#: o H2 puniu: harness que passa verde declarando propriedade que nao tem.
#:
#: As quatro listas afirmam o comportamento REAL. Qualquer mudanca — correcao
#: acidental ou regressao — faz o harness reprovar, que e o ponto.

#: Leitura legitima que o hook DE FATO libera.
LEITURA_LEGITIMA = [
    ("verificador com prefixo de ambiente seguro",
     "PYTHONDONTWRITEBYTECODE=1 python tools/check_core_boundary.py"),
    ("harness negativo (este arquivo)", "python scripts/phase0_negative_tests.py"),
    ("git cat-file", "git cat-file -p HEAD"),
    ("git merge-base (comparacao contra main)", "git merge-base main HEAD"),
    ("git for-each-ref", "git for-each-ref --format='%(refname)' refs/heads"),
]

#: FALSOS BLOQUEIOS conhecidos: leitura legitima que o hook recusa. Sao a
#: familia P8 -> P16 -> P23, agora com as vias que a oitava auditoria somou.
#: Estao aqui afirmados como BLOQUEADOS de proposito: enquanto o P23 estiver
#: aberto, este e o comportamento real, e o harness tem que dize-lo. Quando o
#: P23 for refeito, cada linha destas volta para LEITURA_LEGITIMA.
FALSOS_BLOQUEIOS_CONHECIDOS = [
    ("(a) redirecao de stderr para /dev/null", "git rev-parse main 2>/dev/null"),
    ("(b) pipeline com filtro de texto", "git ls-files | sort"),
    ("(c) alternancia dentro de aspas", r'grep -n "fase 0\|phase 0"'),
    ("(d) laco de shell", 'for f in $(git ls-files); do cat "$f"; done'),
    ("(e) smoke test do PHASE_0_CHECKLIST (payload citado)",
     "printf '%s\n' '{\"tool_input\":{\"command\":\"rm -rf range-core\"}}'"
     " | python ~/.claude/hooks/readonly_bash.py"),
    ("prova central com stderr suprimido",
     "python scripts/phase0_negative_tests.py 2>/dev/null"),
    ("verificador com stderr suprimido",
     "python tools/check_core_boundary.py 2>/dev/null"),
    ("git tag listando", "git tag"),
    ("git tag --list", "git tag --list"),
    # Custo ACEITO da regra de contencao introduzida em 2026-08-14. Nao e
    # defeito de casamento textual como os de cima: e consequencia deliberada
    # de negar `..`. Fica aqui porque continua sendo leitura legitima recusada,
    # e a lista tem que dizer o estado real — mas a correcao NAO e afrouxar a
    # regra. O worktree de auditoria E o objeto da auditoria; ler fora dele mede
    # outra arvore. Ver fase_0.md §6 P32.
    ("leitura fora do worktree, negada por contencao", "cat ../../README_FIRST.md"),
    ("listagem fora do worktree, negada por contencao", "ls ../.."),
]

#: Escrita deliberada que o hook DE FATO bloqueia.
ESCRITA_DELIBERADA = [
    ("remocao real", "rm -rf range-core"),
    ("git que altera estado", "git commit -m x"),
    ("redirecionamento para arquivo", "git log > out.txt"),
    ("escrita via tee", "git ls-files | tee out.txt"),
    ("instalacao de pacote", "pip install requests"),
    ("acesso de rede", "curl https://example.com"),
    ("execucao arbitraria via python -c", "python -c 'import os'"),
    ("edicao in-place", "sed -i s/a/b/ file"),
    ("escrita no corpo de um laco", "for f in a; do rm $f; done"),
    ("execucao dentro de substituicao de comando", "git ls-files `rm -rf x`"),
    # O probe anterior era `env rm -rf x` e levava este mesmo rotulo. Ele passava
    # pela regra do token `rm` — nada nele exercitava `env`. Probe que passa pelo
    # motivo errado carrega o nome da propriedade que NAO mede: era o B2 da 11a
    # auditoria, e o trampolim real estava aberto. Agora o comando invocado por
    # `env` nao e negado por si; so a remocao de `env` da allowlist bloqueia.
    ("env como trampolim de execucao arbitraria", "env python -c \"print('x')\""),
    ("env como trampolim de escrita", "env python -c \"open('x','w')\""),
    ("env como trampolim de shell", "env sh -c 'echo oi'"),
    ("git branch -m muta ref compartilhado", "git branch -m aaa bbb"),
    ("git branch -f muta ref compartilhado", "git branch -f main HEAD"),
    ("git branch -c muta ref compartilhado", "git branch -c aaa bbb"),
    ("git diff --output escreve arquivo", "git diff --output=out.txt HEAD~1 HEAD"),
    ("git log --output escreve arquivo", "git log --output=out.txt"),
    ("git show --output escreve arquivo", "git show --output=out.txt HEAD"),
    ("redirecionamento na forma >&", "ls >& out.txt"),
    ("redirecionamento na forma &>", "ls &> out.txt"),
    ("redirecionamento na forma &>>", "ls &>> out.txt"),
    ("redirecionamento na forma >|", "ls >| out.txt"),
    ("redirecionamento na forma <>", "ls <> out.txt"),
    ("escrita por flag: sort -o", "git ls-files | sort -o out.txt"),
    ("escrita por flag: sort --output=", "git ls-files | sort --output=../../CLAUDE.md"),
    ("escrita posicional: uniq", "uniq entrada.txt ../../CLAUDE.md"),
    ("travessia via >&", "ls >& ../../CLAUDE.md"),
    ("travessia via sort -o", "git ls-files | sort -o ../../CLAUDE.md"),
    ("git tag com operando cria tag", "git tag v9.9.9"),
    ("git tag -d apaga tag", "git tag -d v1.0"),
    ("git tag --delete apaga tag", "git tag --delete v1.0"),
    ("git branch -D apaga ref compartilhado com o worktree principal",
     "git branch -D main"),
]

#: PROBES POR INVARIANTE, NAO POR GRAFIA. Foi o B2 da decima auditoria: as oito
#: provas de travessia usavam todas o literal `../../` e certificavam a grafia,
#: nao a propriedade. Trocando `../../X` pelo caminho absoluto do mesmo arquivo,
#: as sete de escrita por flag reabriam e o harness seguia verde.
#:
#: A licao e a mesma das nove rodadas anteriores, cometida dentro da correcao
#: que deveria encerra-la: um alvo tem infinitas grafias, entao policiar alvo e
#: sempre refutavel. O que se verifica e a AUSENCIA DE CAPACIDADE DE ESCRITA no
#: comando allowlistado — `find` saiu da allowlist, e as flags de saida das
#: cinco ferramentas que ficaram estao negadas.
#:
#: Cada forma abaixo e testada nas QUATRO grafias do mesmo alvo. Um probe que
#: so cobre a grafia lembrada nao prova ausencia das grafias esquecidas.
#: TERCEIRO EIXO: composicao. As 33 provas de escrita e as 32 de grafia eram
#: todas de SEGMENTO UNICO. O eixo do alvo estava coberto, o eixo do comando
#: passou a estar com allowlist_e_a_revisada(), e o de COMO OS COMANDOS SAO
#: ENCADEADOS nao era exercitado por probe nenhum — foi por ele que passou o B1
#: da 12a auditoria: `\n`, `\r` e `&` nao estavam no separador de segmentos, e
#: como cada segmento e validado isoladamente, bastava a primeira palavra ser
#: allowlistada para o resto passar inteiro.
#:
#: Cada separador que o bash honra e testado com um prefixo LEGITIMO seguido de
#: carga de escrita. O prefixo legitimo e o ponto: sem ele o probe passaria pela
#: regra do proprio comando de escrita, e nao pela composicao — que foi o defeito
#: do probe `env rm -rf x` punido pelo B2 da 11a rodada.
SEPARADORES_DE_COMANDO = [
    ("ponto e virgula", ";"),
    ("pipe", "|"),
    ("and-and", "&&"),
    ("or-or", "||"),
    ("nova linha", "\n"),
    ("retorno de carro", "\r"),
    ("e-comercial (background)", " & "),
]

#: Prefixo allowlistado + carga que DEVE ser bloqueada, qualquer que seja o
#: separador entre os dois.
COMPOSICAO_PREFIXO = "git status"
COMPOSICAO_CARGA = "python -c \"open('/tmp/aurora_probe','w')\""

GRAFIAS_DE_ALVO = [
    ("relativa", "../../CLAUDE.md"),
    ("absoluta", "/c/Projetos/aurora-cyber-range/CLAUDE.md"),
    ("til", "~/.claude/hooks/readonly_bash.py"),
    ("variavel de ambiente", "$HOME/.claude/hooks/readonly_bash.py"),
]

#: Formas de escrita parametrizadas pelo alvo. `{}` recebe cada grafia.
ESCRITA_POR_ALVO = [
    ("find -fprint0 (find fora da allowlist)", "find . -fprint0 {}"),
    ("find -delete com alvo explicito", "find {} -delete"),
    ("pytest --junitxml", "pytest --junitxml={}"),
    ("python -m pytest --junitxml", "python -m pytest --junitxml={}"),
    ("ruff --output-file", "ruff check --output-file {} ."),
    ("mypy --junit-xml", "mypy --junit-xml {} ."),
    ("eslint -o", "eslint -o {} ."),
    ("tsc --outFile", "tsc --noEmit --outFile {}"),
]

#: BURACOS conhecidos: escrita deliberada que o hook NAO bloqueia. Afirmados
#: como NAO BLOQUEADOS porque e o estado real, e esconde-lo seria repetir o H2.
#:
#: CRITERIO DE ADMISSAO, desde 2026-08-14: uma forma so pode ser declarada aqui
#: se sua escrita permanecer CONTIDA no worktree de auditoria. Escrita que
#: alcanca o worktree principal e finding, nao defeito aceito — ela derrota o
#: proposito declarado do hook, que e impedir correcao acidental, e nao apenas
#: conter adversario.
#:
#: A lista tinha 10 entradas. A medicao (fase_0.md §6 P32) mostrou que 8
#: escreviam fora do worktree e foram FECHADAS, migrando para
#: ESCRITA_DELIBERADA. Restam as duas contidas. Declarar as outras oito teria
#: sido usar a disciplina de declaracao para legitimar exatamente o que ela
#: existe para impedir.
#: VAZIA desde 2026-08-14, e isso e resultado, nao omissao. As duas ultimas
#: entradas — `find . -delete` e `find . -fprint0 out.txt` — eram declaradas
#: como contidas no worktree. O B2 da decima auditoria mostrou que a mesma
#: allowlist aprovava os gemeos NAO contidos com alvo absoluto, entao a
#: declaracao de contencao era falsa: usava-se a honestidade da lista para
#: legitimar exatamente o que o criterio de admissao proibia.
#:
#: Resolvido tirando `find` da allowlist, nao ajustando a declaracao. Nenhuma
#: forma de escrita conhecida passa hoje. Se uma aparecer, entra aqui SOMENTE
#: se passar no criterio de admissao acima; caso contrario e finding.
BURACOS_CONHECIDOS: list[tuple[str, str]] = []


def _hooks_sob_teste() -> list[tuple[str, Path]]:
    """Fonte versionada SEMPRE; copia instalada TAMBEM, quando existir.

    Era o H4 da decima auditoria: todos os probes rodavam so contra
    READONLY_HOOK_SOURCE. Combinado com o B1 — que permitia sobrescrever
    ~/.claude/hooks/readonly_bash.py —, o harness podia passar verde contra uma
    fonte integra enquanto o hook EM EXECUCAO fora alterado. A fonte nao e o
    que roda; a copia instalada e.

    Em CI nao ha escopo de usuario e so a fonte e testada, o que fica dito na
    saida em vez de suposto.
    """
    alvos = [("fonte versionada", READONLY_HOOK_SOURCE)]
    if READONLY_HOOK_INSTALLED.exists():
        alvos.append(("copia instalada", READONLY_HOOK_INSTALLED))
    return alvos


def _run_readonly_hook(command: str, hook: Path | None = None) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(hook or READONLY_HOOK_SOURCE)],
        cwd=ROOT, input=payload, text=True, capture_output=True,
    )


def expect_hook_allows(label: str, command: str) -> None:
    for origem, hook in _hooks_sob_teste():
        result = _run_readonly_hook(command, hook)
        if result.returncode != 0:
            _reject(
                f"readonly_bash.py [{origem}] {label}",
                f"BLOQUEOU leitura legitima (rc={result.returncode}). "
                f"Comando: {command}",
                (result.stdout or "") + (result.stderr or ""),
            )
    print(f"OK: readonly_bash.py liberou leitura legitima - {label}")


def expect_hook_blocks(label: str, command: str) -> None:
    for origem, hook in _hooks_sob_teste():
        result = _run_readonly_hook(command, hook)
        saida = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 2:
            _reject(
                f"readonly_bash.py [{origem}] {label}",
                f"NAO bloqueou escrita deliberada (rc={result.returncode}, esperado 2). "
                f"Comando: {command}",
                saida,
            )
        if not saida.strip():
            _reject(f"readonly_bash.py [{origem}] {label}",
                    "bloqueou sem explicar o motivo", saida)
    print(f"OK: readonly_bash.py bloqueou escrita deliberada - {label}")


#: Veredito gravado no registro VERSIONADO. Sem probe, o registro afirmava
#: cobertura que nao existia — M2 da oitava auditoria. O caso que motivou o
#: achado original e o terceiro: PASS que cita "FAIL" no corpo.
CASOS_DE_VEREDITO = [
    ("PASS simples", "# AUDITORIA\n\n## VEREDITO: **PASS**\n\n0 BLOCKER.\n", "PASS"),
    ("FAIL simples", "## VEREDITO: **FAIL**\n\n1 BLOCKER.\n", "FAIL"),
    ("PASS citando FAIL no corpo",
     "## VEREDITO: PASS\n\nNenhum item devolveu FAIL.\nRegra: BLOCKER e FAIL.\n", "PASS"),
    ("FAIL citando PASS no corpo",
     "## VEREDITO: **FAIL**\n\nItens 1 e 2 estao PASS.\n", "FAIL"),
    ("template nao preenchido", "## VEREDITO: PASS | FAIL\n", "indeterminado"),
    ("sem linha de veredito", "# AUDITORIA\n\nAchei tres coisas.\n", "indeterminado"),
    ("linhas discordantes", "## VEREDITO: PASS\n\n...\n\n## VEREDITO: FAIL\n", "indeterminado"),
    ("relatorio vazio", "", "sem_relatorio"),
]


def verdict_probes() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from audit_report import detect_verdict, select_report

    for label, texto, esperado in CASOS_DE_VEREDITO:
        obtido, motivo = detect_verdict(texto)
        if obtido != esperado:
            _reject("audit_report.detect_verdict",
                    f"{label}: devolveu '{obtido}', esperado '{esperado}'", "")
        if obtido == "indeterminado" and not motivo:
            _reject("audit_report.detect_verdict",
                    f"{label}: indeterminado SEM motivo. Indice que chuta e pior "
                    "que indice ausente, mas indeterminado mudo nao permite agir", "")
    print(f"OK: detect_verdict correto nos {len(CASOS_DE_VEREDITO)} casos de veredito")

    # select_report: numa sessao interativa o operador pergunta DEPOIS do
    # relatorio, entao o ultimo bloco do agente nao e o relatorio. Foi o que
    # aconteceu na oitava rodada: relatorio no bloco 8 de 11.
    blocos = ["preambulo", "## VEREDITO: **FAIL**\n\nrelatorio inteiro", "resposta a pergunta"]
    escolhido, degradacao = select_report(blocos)
    if "relatorio inteiro" not in escolhido or degradacao is not None:
        _reject("audit_report.select_report",
                "nao escolheu o bloco com linha de veredito quando ele existe", "")
    escolhido, degradacao = select_report(["so conversa", "mais conversa"])
    if escolhido != "mais conversa" or not degradacao:
        _reject("audit_report.select_report",
                "sem bloco de veredito, deve cair no ultimo E registrar a degradacao", "")
    print("OK: select_report escolhe o bloco do relatorio, nao o ultimo da sessao")


def expect_hook_blocks_known_defect(label: str, command: str) -> None:
    """Afirma um FALSO BLOQUEIO conhecido: leitura legitima que o hook recusa.

    Se um dia passar a ser liberada, este probe reprova — e e o sinal certo,
    porque significa que o P23 foi refeito e a linha deve migrar para
    LEITURA_LEGITIMA. Defeito documentado nao pode virar defeito esquecido.
    """
    # M1 da 11a auditoria: estas duas familias rodavam so contra a fonte
    # versionada. O argumento do H4 — a fonte nao e o que roda — vale igual
    # para afirmacao de defeito conhecido. A copia instalada manda.
    result = _run_readonly_hook(command, _hooks_sob_teste()[-1][1])
    if result.returncode == 0:
        _reject(
            f"readonly_bash.py [falso bloqueio conhecido] {label}",
            "passou a LIBERAR esta leitura. Se o P23 foi refeito, mova a linha "
            "de FALSOS_BLOQUEIOS_CONHECIDOS para LEITURA_LEGITIMA",
            "",
        )
    print(f"AINDA BLOQUEADO (defeito aberto, P23): {label}")


def expect_hook_allows_known_hole(label: str, command: str) -> None:
    """Afirma um BURACO conhecido: escrita deliberada que o hook NAO bloqueia.

    Mesma logica invertida: se passar a bloquear, o probe reprova e a linha deve
    migrar para ESCRITA_DELIBERADA. O harness deixa de poder declarar "a
    protecao nao afrouxou" sem dizer de que protecao esta falando.
    """
    # M1 da 11a auditoria: estas duas familias rodavam so contra a fonte
    # versionada. O argumento do H4 — a fonte nao e o que roda — vale igual
    # para afirmacao de defeito conhecido. A copia instalada manda.
    result = _run_readonly_hook(command, _hooks_sob_teste()[-1][1])
    if result.returncode == 2:
        _reject(
            f"readonly_bash.py [buraco conhecido] {label}",
            "passou a BLOQUEAR esta escrita. Mova a linha de "
            "BURACOS_CONHECIDOS para ESCRITA_DELIBERADA",
            "",
        )
    print(f"AINDA ABERTO (buraco documentado, P23): {label}")


#: Conjunto REVISADO de comandos allowlistados. Cada nome aqui foi examinado
#: quanto a capacidade de escrita; a lista e o registro dessa revisao.
COMANDOS_REVISADOS = {
    "git", "pytest", "python", "npm", "ruff", "mypy", "black", "eslint", "tsc",
    "range-cli", "docker", "ls", "cat", "head", "tail", "wc", "grep", "rg",
    "tree", "diff", "stat", "pwd", "echo", "printf", "which",
}


def allowlist_e_a_revisada() -> None:
    """Afirma o CONJUNTO da allowlist, nao apenas comandos lembrados.

    Onze rodadas mostraram o mesmo padrao: o harness prova as formas que quem
    escreveu lembrou, e a auditoria seguinte encontra uma que ele nao lembrou.
    A matriz de grafias corrigiu isso no eixo do ALVO e manteve fixo o eixo do
    COMANDO — foi o B2 da 11a auditoria, que encontrou `env`, `git --output` e
    `git branch -m` fora de qualquer probe.

    "Lembrei de todos os comandos?" nao e decidivel. "A allowlist e o conjunto
    que foi revisado?" e. Este probe troca a pergunta indecidivel pela
    decidivel: acrescentar comando a allowlist REPROVA o harness ate que o
    comando entre em COMANDOS_REVISADOS, o que forca a revisao de capacidade de
    escrita a acontecer no momento da mudanca, e nao na auditoria seguinte.
    """
    fonte = READONLY_HOOK_SOURCE.read_text(encoding="utf-8")
    bloco = fonte.split("ALLOWED = [", 1)[1].split("\n]", 1)[0]

    # So a PRIMEIRA posicao de cada padrao e um comando; o que vem depois sao
    # subcomandos (docker compose ps, range-cli scenario validate) e nao abrem
    # processo novo. Extrair sem essa distincao acusa `config` e `dryrun` como
    # comandos nao revisados, que foi o primeiro resultado deste probe.
    encontrados: set[str] = set()
    for corpo in re.findall(r"\^\{SAFE_ENV_PREFIX\}(\([^)]*\)|[A-Za-z][\w-]*)", bloco):
        for alternativa in corpo.strip("()").split("|"):
            # `black\s+--check` e `tsc\s+--noEmit` sao comando + restricao: o
            # comando e o token da frente.
            nome = re.match(r"\s*([A-Za-z][\w-]*)", alternativa)
            if nome:
                encontrados.add(nome.group(1))

    novos = encontrados - COMANDOS_REVISADOS
    if novos:
        _reject(
            "allowlist do readonly_bash.py",
            f"contem comando(s) NAO REVISADO(S): {sorted(novos)}. "
            "Acrescente a COMANDOS_REVISADOS somente apos examinar se o comando "
            "tem caminho de escrita — por acao, por flag ou por invocacao de "
            "outro processo. Foi assim que `env` passou onze rodadas",
            "",
        )
    sumidos = COMANDOS_REVISADOS - encontrados
    print(
        f"OK: allowlist e o conjunto revisado ({len(encontrados)} comandos)"
        + (f"; removidos desde a ultima revisao: {sorted(sumidos)}" if sumidos else "")
    )


def hook_copies_in_sync() -> None:
    """A copia instalada e a que roda. Divergencia silenciosa e o pior caso."""
    if not READONLY_HOOK_INSTALLED.exists():
        print(
            "AVISO: ~/.claude/hooks/readonly_bash.py ausente — checagem de drift "
            "pulada (esperado em CI, onde nao ha escopo de usuario)."
        )
        return
    fonte = READONLY_HOOK_SOURCE.read_text(encoding="utf-8").splitlines()
    instalada = READONLY_HOOK_INSTALLED.read_text(encoding="utf-8").splitlines()
    if fonte != instalada:
        _reject(
            "readonly_bash.py",
            "fonte versionada e copia instalada DIVERGEM. "
            f"Copie {READONLY_HOOK_SOURCE.relative_to(ROOT).as_posix()} "
            "para ~/.claude/hooks/",
            "",
        )
    print("OK: fonte versionada e copia instalada de readonly_bash.py identicas")


def main() -> int:
    with temporary_file("range-core/_phase0_probe_bad.py", "from domains.academus import X\n"):
        expect_fail("check_core_boundary.py", [sys.executable, "tools/check_core_boundary.py"],
                    "range-core/_phase0_probe_bad.py")

    # Montado por concatenacao de proposito: .claude/hooks/check_architecture.py
    # recusa literal de flag em codigo, e este arquivo e codigo. A montagem
    # evita o falso positivo do hook sem afrouxa-lo.
    probe_flag = "academus." + "phase0_probe_flag"

    flags = """flags:\n  - name: academus.phase0_probe_flag\n    type: boolean\n    default: false\n"""

    # Catalogo minimo no formato de 09_EVENT_MODEL.md secao 4.1, agrupado por
    # truth_layer. Ate aqui nenhum probe plantava contracts/events.schema.yaml,
    # entao load_declared_event_types() devolvia sempre {} e METADE do
    # invariante 2 — o ramo de event_type — nunca foi exercitada. O bloco de
    # artefatos de evento do codegen tambem nunca era alcancado.
    eventos = (
        "event_types:\n"
        "  ground_truth:\n"
        "    - fact_materialized\n"
        "  participant_action:\n"
        "    - containment_declared\n"
    )
    probe_event_type = "containment_declared"
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/_phase0_probe_literal.py", "FLAG = 'academus.phase0_probe_flag'\n"
    ):
        expect_fail("check_contract_literals.py", [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/_phase0_probe_literal.py")

    # TypeScript e gate real, nao so hook: 01_ARCHITECTURE.md secao 5.4 exige
    # constante gerada para Python E TypeScript, e o layout da secao 2 coloca
    # o front-end de core e adapter em .ts/.tsx.
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/web/_phase0_probe_literal.tsx",
        "export const FLAG = " + '"' + probe_flag + '";\n',
    ):
        expect_fail("check_contract_literals.py (TypeScript)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/web/_phase0_probe_literal.tsx")

    # Plantado em range-core/engine/, NAO em um diretorio "api"/"events": a
    # versao anterior do verificador so varria esses dois segmentos e o probe
    # antigo passava sem nunca tocar a fronteira real. 01_ARCHITECTURE.md
    # secao 6 declara o inject-engine como emissor de eventos de effect.
    with temporary_file(
        "range-core/engine/_phase0_probe_event.py",
        "event = {'event_type': 'PROBE', 'objective_ids': ['OBJ-X']}\n",
    ):
        expect_fail("check_event_envelope.py", [sys.executable, "tools/check_event_envelope.py"],
                    "range-core/engine/_phase0_probe_event.py")

    # Isencao de projecao e ANCORADA. Este caminho tem um segmento "metrics" no
    # meio, mas e caminho de emissao de adapter: so range-core/metrics/ e
    # projecao. Isencao casando segmento em qualquer profundidade anulava o
    # invariante 4 justamente onde ele passou a ser a unica fronteira.
    with temporary_file(
        "domains/academus/api/metrics/emit.py",
        "event = {'event_type': 'PROBE', 'objective_ids': ['OBJ-X']}\n",
    ):
        expect_fail("check_event_envelope.py (isencao ancorada)",
                    [sys.executable, "tools/check_event_envelope.py"],
                    "domains/academus/api/metrics/emit.py")

    # Mesma correcao no invariante 2: um segmento "contracts" no meio do
    # caminho nao autoriza literal de flag.
    with temporary_file("domains/academus/flags.yaml", flags), temporary_file(
        "domains/academus/api/contracts/handler.py",
        "FLAG = " + repr(probe_flag) + "\n",
    ):
        expect_fail("check_contract_literals.py (isencao ancorada)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/api/contracts/handler.py")

    # O invariante 2 tem DOIS ramos: literal de flag e literal de event_type.
    # So o de flag tinha probe.
    with temporary_file("contracts/events.schema.yaml", eventos), temporary_file(
        "domains/academus/api/handler.py",
        "EVENT = " + repr(probe_event_type) + "\n",
    ):
        expect_fail("check_contract_literals.py (event_type)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/api/handler.py")

    with temporary_file("range-core/_phase0_probe_security.py", "value = eval('1 + 1')\n"):
        expect_fail("check_security_constraints.py", [sys.executable, "tools/check_security_constraints.py"],
                    "range-core/_phase0_probe_security.py")

    with temporary_file(
        "scenarios/_phase0_probe/fixture.jsonl",
        '{"src":"8.8.8.8","domain":"google.com"}\n',
    ):
        expect_fail("check_synthetic_data.py", [sys.executable, "tools/check_synthetic_data.py"],
                    "scenarios/_phase0_probe/fixture.jsonl")

    # 123.456.789-09 e o CPF de exemplo canonico: sequencia crescente com os
    # digitos verificadores corretos. Nao e numero plausivelmente emitido, e
    # serve exatamente para provar que CPF VALIDO e recusado em dado sintetico
    # (05_SECURITY_REQUIREMENTS secao 3).
    with temporary_file(
        "scenarios/_phase0_probe_cpf/alunos.jsonl",
        '{"nome":"Fulano de Tal","cpf":"123.456.789-09"}\n',
    ):
        expect_fail("check_synthetic_data.py (identificador)",
                    [sys.executable, "tools/check_synthetic_data.py"],
                    "scenarios/_phase0_probe_cpf/alunos.jsonl")

    # codegen --check deve detectar contrato novo sem artefato gerado correspondente.
    with temporary_file("domains/_phase0_codegen_probe/flags.yaml", flags):
        expect_fail("codegen.py --check (artefato ausente)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "domains/_phase0_codegen_probe/flags.yaml")

    # Ausencia e divergencia sao ramos DIFERENTES do verificador, e T2 de
    # 06_ACCEPTANCE_TESTS.md fala de constantes DESSINCRONIZADAS — que e o ramo
    # de divergencia. Ele nao era exercitado por probe nenhum.
    #
    # Os dois artefatos sao plantados, e ambos divergentes: com .py e .ts
    # presentes, o ramo de ausencia nao pode disparar, entao a deteccao so pode
    # vir da comparacao de conteudo.
    with temporary_file("domains/_phase0_divergent_probe/flags.yaml", flags), temporary_file(
        "domains/_phase0_divergent_probe/generated/flags.py",
        "# artefato fora de sincronia com o contrato\n",
    ), temporary_file(
        "domains/_phase0_divergent_probe/generated/flags.ts",
        "// artefato fora de sincronia com o contrato\n",
    ):
        expect_fail("codegen.py --check (artefato divergente)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "domains/_phase0_divergent_probe/generated/flags.py")

    # O codegen tem dois blocos de contrato: flags por adapter e o catalogo de
    # eventos. O bloco de eventos nunca era alcancado, porque nenhum probe
    # plantava contracts/events.schema.yaml. O ramo de divergencia de conteudo e
    # o mesmo codigo ja exercitado pelo probe de flags acima; aqui o que se
    # prova e que o catalogo de eventos gera expectativa de artefato.
    with temporary_file("contracts/events.schema.yaml", eventos):
        expect_fail("codegen.py --check (artefatos de evento)",
                    [sys.executable, "tools/codegen.py", "--check"],
                    "contracts/events.schema.yaml")

    for label, comando in LEITURA_LEGITIMA:
        expect_hook_allows(label, comando)
    for label, comando in ESCRITA_DELIBERADA:
        expect_hook_blocks(label, comando)
    # O invariante nas quatro grafias do mesmo alvo (B2 da decima auditoria).
    # Eixo da composicao (B1/B2 da 12a auditoria).
    for label_sep, sep in SEPARADORES_DE_COMANDO:
        expect_hook_blocks(f"composicao por {label_sep}",
                           COMPOSICAO_PREFIXO + sep + COMPOSICAO_CARGA)
    for label_forma, molde in ESCRITA_POR_ALVO:
        for label_grafia, alvo in GRAFIAS_DE_ALVO:
            expect_hook_blocks(f"{label_forma} [grafia {label_grafia}]", molde.format(alvo))
    for label, comando in FALSOS_BLOQUEIOS_CONHECIDOS:
        expect_hook_blocks_known_defect(label, comando)
    for label, comando in BURACOS_CONHECIDOS:
        expect_hook_allows_known_hole(label, comando)
    allowlist_e_a_revisada()
    verdict_probes()
    hook_copies_in_sync()

    print(
        "\nTodos os seis verificadores falharam contra probes independentes.\n"
        f"readonly_bash.py: libera {len(LEITURA_LEGITIMA)} leituras legitimas e "
        f"bloqueia {len(ESCRITA_DELIBERADA)} escritas deliberadas, mais "
        f"{len(ESCRITA_POR_ALVO)} formas x {len(GRAFIAS_DE_ALVO)} grafias de alvo "
        f"= {len(ESCRITA_POR_ALVO) * len(GRAFIAS_DE_ALVO)} provas de invariante.\n"
        f"Hooks exercitados: {', '.join(o for o, _ in _hooks_sob_teste())}.\n"
        f"DEFEITOS ABERTOS, afirmados e nao escondidos (P23 reaberto): "
        f"{len(FALSOS_BLOQUEIOS_CONHECIDOS)} leituras legitimas bloqueadas e "
        f"{len(BURACOS_CONHECIDOS)} escritas nao bloqueadas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
