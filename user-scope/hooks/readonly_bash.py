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
    # `branch` SAIU dos subcomandos. Listar ramos se faz com for-each-ref, que
    # nao tem forma que mute. `git branch` muta o ref store COMPARTILHADO com o
    # repositorio principal por -m, -M, -f e -c, alem de -d/-D — negar so a
    # delecao era enumerar quatro quintos de uma familia (B1c da 11a auditoria).
    rf"^{SAFE_ENV_PREFIX}git\s+(diff|log|show|status|rev-parse|ls-files|cat-file|merge-base|for-each-ref)\b",
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
    # `(?:\s+2>/dev/null)?` admite so o descarte de stderr. A ancora `$` continua
    # sendo o ponto: nenhum outro caminho sob scripts/ e liberado, e nenhum outro
    # sufixo passa. Sem isto, rodar a PROVA CENTRAL com stderr suprimido era
    # falso bloqueio — um dos onze do P23, e o mais caro deles.
    rf"^{SAFE_ENV_PREFIX}python\s+scripts/phase0_negative_tests\.py(?:\s+2>\s*/dev/null)?\s*$",
    # Smoke tests de hook do PHASE_0_CHECKLIST. Nome de arquivo sem barra, entao
    # travessia como .claude/hooks/../../x.py nao casa.
    # NOME EXPLICITO, nao curinga. O curinga pre-autorizava o auditor a executar
    # qualquer .claude/hooks/*.py que um commit futuro acrescentasse — incluindo
    # um que escrevesse. Era o H1 da setima auditoria; a reversao do P23 o
    # reintroduziu, e o registro seguiu afirmando que estava fechado (H1 da nona).
    # Fechado no codigo em 2026-08-14, para o registro voltar a ser verdadeiro.
    # log_audit.py saiu da lista porque foi removido do projeto (M1 da nona).
    rf"^{SAFE_ENV_PREFIX}python\s+(?:~/|\$HOME/)?\.claude/hooks/"
    rf"(?:check_architecture|scenario_scope|scenario_bash)\.py(?:\s+2>\s*/dev/null)?\s*$",
    # `find` SAIU. Ele escreve por acao (-delete) e por flag (-fprint, -fprint0,
    # -fls) com alvo posicional arbitrario, e nao ha como policiar o alvo por
    # texto: `..`, caminho absoluto, `~` e `$HOME` sao a mesma escrita em quatro
    # grafias, e fechar uma revela a seguinte — foi o B1 da decima auditoria.
    # `git ls-files`, `rg` e `ls` cobrem o uso real de leitura. Superficie
    # grande demais para o valor; o desenho tokenizado da setima ja o removera.
    rf"^{SAFE_ENV_PREFIX}(ls|cat|head|tail|wc|grep|rg|tree|diff|stat)\b",
    # printf entra porque os smoke tests alimentam o hook por pipe
    # (printf '{...}' | python .claude/hooks/x.py) e cada segmento do pipe e
    # validado isoladamente. Sem escrita: redirecionamento ja e negado acima.
    # `env` SAIU, e era o pior buraco do arquivo: allowlistado sem nenhuma
    # restricao sobre o que invoca, ele e execucao arbitraria — `env python -c
    # "open(...,'w').write(...)"` escrevia em qualquer caminho, em qualquer
    # grafia, sem depender de flag nenhuma. O probe `python -c` bloqueia; bastava
    # prefixar com env. Era o B1a da 11a auditoria.
    #
    # A remocao nao custa nada: SAFE_ENV_PREFIX ja aceita VAR=valor antes do
    # comando, entao `PYTHONDONTWRITEBYTECODE=1 pytest` continua passando. `env`
    # sozinho, listando o ambiente, tambem deixa de passar — e melhor assim,
    # porque despeja variaveis de ambiente na transcricao da auditoria.
    rf"^{SAFE_ENV_PREFIX}(pwd|echo|printf|which)\b",
    # `git tag` SEM operando LISTA; com operando CRIA. O casamento textual
    # distingue os dois casos com precisao aqui, porque a forma de leitura e
    # fechada: nada depois de `tag`, ou apenas `--list`/`-l` com padrao.
    # `git tag v9.9.9` e `git tag -d` nao casam e seguem bloqueados. Eram dois
    # dos onze falsos bloqueios do P23, e o item 13 da DoD depende de listar tag.
    rf"^{SAFE_ENV_PREFIX}git\s+tag\s*$",
    rf"^{SAFE_ENV_PREFIX}git\s+tag\s+(?:--list|-l)\b",
    # FILTROS DE LEITURA. Nenhum escreve sem flag de saida, e as flags de saida
    # que eles tem (`sort -o`, `sort --output=`) ja caem na negacao de flags.
    #
    # `uniq` NAO entra: ele escreve por POSICIONAL — `uniq entrada saida` —, que
    # e a mesma familia do `find -fprint0` e nao tem flag para negar. `sort -u`
    # cobre o uso. O desenho da setima auditoria ja o removera pelo mesmo motivo;
    # o probe allowlist_e_a_revisada() forcou a revisao antes de ele voltar.
    # Sem eles, `git ls-files | sort` era falso bloqueio — o segundo segmento do
    # pipe nao casava nada, e pipeline com filtro e a forma normal de auditar.
    rf"^{SAFE_ENV_PREFIX}(sort|cut|tr|nl|rev|comm|join|column|fold|basename|dirname)\b",
]

DENIED_ANYWHERE = [
    # `/dev/null` e descarte, nao escrita: nada persiste. `&1`/`&2` sao
    # duplicacao de descritor, tambem sem arquivo. Sem estas isencoes, tres dos
    # onze falsos bloqueios do P23 vinham daqui — `2>/dev/null` no verificador,
    # no harness e no git — e cada um empurrava a auditoria para inferencia.
    # A negacao continua valendo para QUALQUER outro alvo.
    (r">>?\s*(?!/dev/null\b)(?!&[12]\b)\S", "redirecionamento de saida para arquivo"),
    (r"\|\s*tee\b", "escrita via tee"),
    (r"\b(rm|mv|cp|chmod|chown|mkdir|touch|truncate)\b", "comando de escrita"),
    # (?!-) impede que `merge-base` case como `merge`: o \b depois de "merge"
    # casa contra o hifen. Era o falso bloqueio registrado em P16, e merge-base
    # e justamente o que o auditor usa para comparar contra main.
    (r"\bgit\s+(commit|push|add|reset|checkout|switch|merge|rebase|clean|restore)\b(?!-)", "git que altera estado"),
    (r"\b(curl|wget|nc|ssh|scp)\b", "acesso de rede"),
    (r"\b(pip|npm)\s+install\b", "instalacao de pacote"),
    (r"\bsed\s+-i\b|\bperl\s+-i\b", "edicao in-place"),
    # CONTENCAO, nao enumeracao de flags. Medido em 2026-08-14: das 10 formas
    # afirmadas como buraco conhecido, 8 escreviam FORA do worktree de auditoria.
    # Sete delas eram a mesma familia — escrita por flag com alvo de caminho
    # (--junitxml=, --output-file, --junit-xml, -o, --outFile, -fprint0) — e
    # tentar listar as flags repete o erro que nove rodadas ja provaram inutil:
    # sempre falta uma. O invariante nao e a flag, e o ALVO.
    #
    # `..` em qualquer posicao sai do worktree. Provado por execucao:
    # `find . -fprint0 ../../tools/codegen.py`, rodado de dentro de
    # .aurora-worktrees/audit/, sobrescreveu o arquivo no worktree principal.
    #
    # Custo aceito: leitura legitima fora do worktree tambem passa a ser
    # bloqueada (`cat ../../README.md`). E o comportamento correto — o worktree
    # de auditoria E o objeto da auditoria, e ler fora dele mede outra arvore.
    # Afirmado em LEITURA_LEGITIMA_BLOQUEADA do harness.
    (r"\.\.[/\\]|(?:^|\s)\.\.(?:\s|$)", "travessia de caminho para fora do worktree"),
    # `git branch` listando e leitura legitima e nao pode ser negado inteiro;
    # so a deleção. O ref store e COMPARTILHADO com o worktree principal:
    # provado por execucao, `git branch -D` rodado de dentro do worktree de
    # auditoria apagou o ramo visivel do repositorio principal.
    (r"\bgit\s+branch\b[^;&|]*\s-{1,2}(?:[dD]|delete)\b", "git branch que apaga ref compartilhado"),
    # FLAGS DE ESCRITA dos comandos que continuam allowlistados porque rodar
    # teste e linter e o trabalho do auditor: pytest, ruff, mypy, eslint, tsc.
    #
    # Isto E enumeracao, e a enumeracao aqui e defensavel onde a de alvos nao
    # era: a superficie e FECHADA POR COMANDO — sao as flags de saida que essas
    # cinco ferramentas documentam —, enquanto a de alvos era aberta, porque
    # qualquer caminho tem infinitas grafias. Flag nova encontrada e finding
    # pelo item 4(d) da DoD, nao defeito aceito.
    # ESCOPADA POR COMANDO, de verdade. A versao anterior dizia no comentario que
    # a superficie era "fechada por comando" e a regex nao mencionava comando
    # nenhum: casava `-o` em qualquer posicao de qualquer comando, e bloqueava
    # `grep -o` e `rg -o`, que sao --only-matching, leitura pura. Desenho
    # declarado e mecanismo implementado divergiam — foi o H1 da 14a auditoria,
    # e a divergencia estava DENTRO do commit que se propunha a atacar os falsos
    # bloqueios por causa.
    #
    # O comando dono da flag tem de aparecer ANTES dela, no MESMO segmento: a
    # lacuna entre os dois nao atravessa separador, entao `git log | grep -o x`
    # nao casa e segue liberado.
    (r"\b(?:pytest|ruff|mypy|eslint|tsc|sort|git)\b[^;&|\n\r]*"
     r"(?:^|\s)(?:-o|--output-file|--outfile|--outFile|--out-dir|--outDir"
     r"|--junitxml|--junit-xml|--tsBuildInfoFile|--declarationDir"
     r"|--cobertura-xml-report|--html-report|--txt-report|--xml-report"
     r"|--linecount-report|--lineprecision-report|--any-exprs-report"
     r"|--xslt-html-report|--xslt-txt-report|--output)(?:[=\s]|$)",
     "flag de escrita em arquivo"),
    # SECRETS pelo caminho do Bash. `.claude/settings.json` nega `Read`/`Edit` de
    # `.env` e `secrets/`, mas essas regras valem para as FERRAMENTAS de arquivo
    # do Claude Code — nao para `cat`, `head`, `grep` ou `stat`, que estao
    # allowlistados aqui e liam tudo. Era o M2 da 12a auditoria: latente nesta
    # fase, porque nenhum desses arquivos existe ainda, e exposicao real na
    # Fase 1, cujo DoD poe RANDOM_SEED em `.env`.
    #
    # `CLAUDE.md` §Secrets diz "nunca leia", sem restringir a ferramenta.
    (r"(?:^|[\s=\"'/\\])\.env(?:\.[A-Za-z0-9_.-]+)?(?:[\s\"']|$)"
     r"|(?:^|[\s\"'/\\])secrets[/\\]",
     "leitura de secret por caminho de shell"),
    # SUBSTITUICAO DE COMANDO — quarto eixo, e o unico que nao e composicao nem
    # alvo nem comando: o conteudo de `$(...)` e de crase EXECUTA, mas fica
    # DENTRO do segmento, entao o segmento inteiro casa pela primeira palavra.
    # `echo $(python -c "...")` saia rc=0 e executava Python arbitrario, com o
    # processo resultante tendo permissao de escrita em tools/codegen.py do
    # worktree principal — o auditor podia reescrever os verificadores que audita.
    #
    # A oitava auditoria ja encontrara esta via no desenho tokenizado; a reversao
    # a reintroduziu SEM entra-la na lista de defeitos declarados. Regressao por
    # reversao que ninguem rastreou — e a razao de o harness agora exercitar o
    # eixo em vez de confiar na memoria de quem reverteu.
    #
    # A crase continua negada no texto CRU. As demais grafias saem daqui e viram
    # PROPRIEDADE, verificada em `_parentese_fora_de_aspas`: enumerar sigilos foi
    # o erro que a 14a auditoria expos — `$(` e crase estavam listados, `<(`
    # nao, e `cat <(python -c ...)` executava com permissao de escrita sobre
    # tools/codegen.py do worktree principal e sobre o hook instalado.
    (r"`", "substituicao de comando por crase"),
]


SEPARADORES = r"\|\||&&|;|\||\n|\r|&"


def _mascara_de_citacao(cmd: str) -> tuple[str, bool]:
    """Devolve (texto com separadores DENTRO de aspas neutralizados, confiavel).

    O `|` de `grep -n "a\\|b"` nunca foi pipe: e conteudo citado. Tratar todo
    `|` como separador foi a raiz de P8 -> P16 -> P23, cinco rodadas de falso
    bloqueio, e cada falso bloqueio empurra a auditoria de medicao para
    inferencia — a degradacao que fez o H4 da primeira rodada ser HIGH.

    A mascara serve APENAS para achar onde os segmentos comecam e terminam.
    `DENIED_ANYWHERE` continua rodando contra o comando CRU, entao nada que
    aconteca aqui pode liberar escrita que a negacao pegaria — inclusive
    `$(...)` e crase dentro de aspas, negados desde a 13a auditoria.

    A oitava auditoria reprovou a tentativa anterior de fazer isto porque ela
    apagava o conteudo citado ANTES de procurar substituicao, e o bash expande
    `$()` dentro de aspas duplas. Aqui a ordem e a inversa: nega primeiro no
    cru, mascara depois, e so para delimitar.

    Devolve confiavel=False quando o parse pode divergir do bash — aspas nao
    fechadas ou aspas escapadas com barra invertida. Nesses casos o chamador
    usa o texto cru, que acha MAIS separadores: falha para o lado seguro.
    """
    if re.search(r"\\['\"]", cmd):
        return cmd, False

    saida: list[str] = []
    aspas: str | None = None
    for ch in cmd:
        if aspas is None:
            if ch in "\"'":
                aspas = ch
            saida.append(ch)
        elif ch == aspas:
            aspas = None
            saida.append(ch)
        else:
            saida.append("\x00" if ch in "|&;\n\r()" else ch)
    return "".join(saida), aspas is None


def _parentese_fora_de_aspas(cmd: str) -> bool:
    """PROPRIEDADE, nao lista de sigilos.

    Toda forma de substituicao e de subshell do bash exige PARENTESE NAO CITADO:
    `$(cmd)`, `<(cmd)`, `>(cmd)`, `(cmd)`, `$((...))`. Enumerar os sigilos
    produziu exatamente o padrao que treze rodadas ja tinham ensinado — a 13a
    listou `$(` e crase, a 14a chegou com `<(` e com subshell puro `(cmd)`.

    O auditor nao precisa de parentese fora de aspas em nenhum comando legitimo:
    `--format='%(refname)'` e `grep -n "foo(bar)"` tem os parenteses DENTRO de
    aspas, e continuam passando.

    Parse duvidoso — aspas escapadas ou nao fechadas — bloqueia. Aqui a queda e
    para o lado FECHADO, ao contrario da queda em `_segmentos`: nao enxergar um
    parentese e liberar execucao, e nao enxergar um separador e so bloquear mais.
    """
    mascarado, confiavel = _mascara_de_citacao(cmd)
    if not confiavel:
        return True
    return "(" in mascarado or ")" in mascarado


def _segmentos(cmd: str) -> list[str]:
    base, confiavel = _mascara_de_citacao(cmd)
    if not confiavel:
        base = cmd
    partes: list[str] = []
    inicio = 0
    for m in re.finditer(SEPARADORES, base):
        partes.append(cmd[inicio:m.start()])
        inicio = m.end()
    partes.append(cmd[inicio:])
    return partes


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

    if _parentese_fora_de_aspas(cmd):
        print(
            "BLOQUEADO: checkpoint-auditor sem escrita deliberada "
            "(parentese fora de aspas: substituicao ou subshell).\n"
            f"Comando: {cmd}\n"
            "Parentese dentro de aspas e permitido. Reporte o finding; nao corrija.",
            file=sys.stderr,
        )
        return 2

    # SEPARADORES QUE O BASH HONRA. `\n`, `\r` e `&` faltavam, e a omissao era
    # total: como cada segmento e validado isoladamente, bastava a PRIMEIRA
    # palavra ser allowlistada para todo o resto passar sem validacao nenhuma.
    # `pytest --version\npython -c "open(<qualquer caminho>,'w')"` saia rc=0.
    # Era o B1 da 12a auditoria, e nem a regra de `..` nem a de flags de saida
    # alcancavam: o alvo e absoluto e nao ha flag.
    #
    # Alternancia ordenada do mais longo para o mais curto: `||` antes de `|`,
    # `&&` antes de `&`. O custo que isto tinha — separador dentro de aspas
    # partindo o comando — deixou de existir: `_segmentos` ignora separador
    # citado, e cai para o texto cru quando o parse pode divergir do bash.
    for segment in _segmentos(cmd):
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
