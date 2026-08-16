#!/usr/bin/env python3
"""Probes externos: cada verificador da Fase 0 deve falhar contra uma violacao plantada."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
    # As duas provas centrais que a Fase 1 acrescentou. Sem elas na allowlist o
    # auditor nao consegue executar o mecanismo que fecha o item 1 da DoD e
    # volta a avaliar por leitura — foi o H3 da segunda auditoria da fase. Estao
    # aqui para que o bloqueio, se voltar, reprove o harness em vez de aparecer
    # so no relatorio do proximo auditor.
    ("executor de exemplos dos contratos",
     "python scripts/check_contract_examples.py"),
    ("teste negativo do executor de exemplos",
     "python scripts/check_contract_examples_probes.py"),
    ("verificador de exemplos da spec",
     "python scripts/check_spec_examples.py"),
    ("teste negativo do verificador de exemplos da spec",
     "python scripts/check_spec_examples_probes.py"),
    ("consistencia do registro de fase",
     "python scripts/check_progress_consistency.py"),
    # AS SEIS DA FASE 2. Cada entrada da allowlist tem prova aqui, e cada prova
    # aqui exige entrada la — as duas direcoes, porque entrada sem prova admite
    # sem saber o que admitiu, e prova sem entrada reprova o harness.
    #
    # Sem elas o auditor da Fase 2 nao executou NENHUM teste da fase e voltou a
    # avaliar por leitura de codigo: B1 da auditoria de 16/08/2026, reincidencia
    # do H3 da segunda auditoria da Fase 1.
    ("suite de testes do range-core", "python -m unittest discover -s tests"),
    ("superficie de leitura do store (P2-2)",
     "python scripts/check_store_read_surface.py"),
    ("teste negativo da superficie de leitura",
     "python scripts/check_store_read_surface_probes.py"),
    ("imports do core para contracts (P2-15)",
     "python scripts/check_core_contract_imports.py"),
    ("teste negativo dos imports do core",
     "python scripts/check_core_contract_imports_probes.py"),
    ("DEMO SCRIPT da Fase 2", "python scripts/demo_fase2.py"),
    # P37: a cobertura do gate e a prova negativa dela. Entram no commit que as
    # cria — a regra que o B1 da auditoria da Fase 2 cobrou, e que esta escrita
    # em `readonly_bash.py`.
    ("cobertura do gate spec_freeze (P37)",
     "python scripts/check_gate_coverage.py"),
    ("teste negativo da cobertura do gate",
     "python scripts/check_gate_coverage_probes.py"),
    ("executor de exemplos com stderr descartado",
     "python scripts/check_contract_examples.py 2>/dev/null"),
    ("git cat-file", "git cat-file -p HEAD"),
    ("git merge-base (comparacao contra main)", "git merge-base main HEAD"),
    ("git for-each-ref", "git for-each-ref --format='%(refname)' refs/heads"),
    # As SETE abaixo eram falso bloqueio declarado (P23) ate 2026-08-14 e
    # passaram para ca porque o hook foi corrigido, nao porque a exigencia caiu.
    # Cada uma custava capacidade de auditar: sem elas o auditor infere em vez de
    # medir, que e a degradacao que fez o H4 da primeira rodada ser HIGH.
    ("stderr descartado em /dev/null", "git rev-parse main 2>/dev/null"),
    ("prova central com stderr descartado",
     "python scripts/phase0_negative_tests.py 2>/dev/null"),
    ("verificador com stderr descartado",
     "python tools/check_core_boundary.py 2>/dev/null"),
    ("pipeline com filtro de leitura", "git ls-files | sort"),
    ("alternancia DENTRO de aspas nao e pipe", r'grep -n "fase 0\|phase 0"'),
    ("git tag listando", "git tag"),
    ("git tag --list", "git tag --list"),
    # Direcao reversa da mascara de citacao: separador citado nao parte o
    # comando, mas o comando segue precisando ser allowlistado.
    ("separador citado dentro de argumento de busca", 'grep -rn "x;y" tools/'),
    # `-o` de grep e rg e --only-matching, leitura pura. A regra de flags de
    # escrita nao era escopada por comando e os bloqueava: H1 da 14a auditoria,
    # e a divergencia estava DENTRO do commit que dizia ter atacado os falsos
    # bloqueios por causa. O comentario afirmava "fechada por comando" e a regex
    # nao mencionava comando nenhum.
    ("grep -o e leitura pura", 'grep -o "P2[0-9]" docs/progress/fase_0.md'),
    ("rg -o e leitura pura", 'rg -o "P3[0-9]" docs/progress/fase_0.md'),
    ("-o depois de pipe nao herda o escopo", "git log | grep -o foo"),
    # Parentese CITADO nao e substituicao e nao pode ser bloqueado.
    ("parentese dentro de aspas", 'grep -n "foo(bar)" tools/'),
    # `2>&1` e duplicacao de descritor, nao escrita. O separador partia em `&` e
    # deixava o segmento `1`, nao allowlistado. Era o H1 da 16a auditoria, e o
    # agravante era o registro: `2>&1` fora nomeado candidato a defeito afirmado
    # e depois SUMIU da lista sem ser corrigido nem declarado — literalmente o
    # modo de falha que a condicao 4(e) nomeia.
    ("duplicacao de descritor 2>&1", "git log --oneline -1 2>&1"),
    ("2>&1 no verificador", "python tools/check_core_boundary.py 2>&1"),
    # Aspas SIMPLES suprimem substituicao: e literal, e tem de passar.
    ("substituicao suprimida por aspas simples", "echo '$(whoami)'"),
    ("cifrao e parentese literais em aspas simples", "grep -n 'a$(b)c' tools/"),
    # `.env.example` e PERMITIDO por CLAUDE.md e EXIGIDO versionado por
    # 05_SECURITY_REQUIREMENTS §6. O hook o bloqueava pelo mesmo overmatch que a
    # P17 corrigiu em settings.json e que ficou intacto aqui — B1 da 15a.
    ("leitura do .env.example, que a norma permite", "cat .env.example"),
    ("grep no .env.example", "grep RANDOM_SEED .env.example"),
    # `nc` dentro de texto nao e acesso de rede: a fronteira de palavra casava
    # dentro de uma sequencia escapada. Era o L2 da 15a auditoria.
    ("nc como substring nao e rede", r'printf "%s" "\nc = 6"'),
]

#: MASCARA DE CITACAO — probes ADVERSARIAIS da correcao do P23.
#:
#: Ignorar separador entre aspas e a direcao fail-open: se o parse divergir do
#: bash, escrita passa. Estes probes exercitam exatamente as formas em que ele
#: poderia divergir. Sem eles, a correcao do P23 seria a mesma classe de
#: afirmacao nao medida que a 11a e a 13a puniram.
MASCARA_ADVERSARIAL = [
    ("separador citado com payload denylistado", 'git log "; rm -rf x"'),
    ("pipe citado com tee", 'git log "| tee f"'),
    ("and-and citado com rede", "git log '&& curl http://x'"),
    # Aspas ESCAPADAS: o parse pode divergir do bash, entao `_mascara_de_citacao`
    # devolve confiavel=False e o hook cai para o texto cru, que acha MAIS
    # separadores. Este probe prova que a queda acontece.
    ("aspas escapadas caem para o texto cru",
     "echo \\' ; python -c \"print(1)\""),
    # Aspas nao fechadas: mesma queda.
    ("aspas nao fechadas caem para o texto cru", "git log ' ; python -c \"print(1)\""),
]

#: FALSOS BLOQUEIOS conhecidos: leitura legitima que o hook recusa. Sao a
#: familia P8 -> P16 -> P23, agora com as vias que a oitava auditoria somou.
#: Estao aqui afirmados como BLOQUEADOS de proposito: enquanto o P23 estiver
#: aberto, este e o comportamento real, e o harness tem que dize-lo. Quando o
#: P23 for refeito, cada linha destas volta para LEITURA_LEGITIMA.
FALSOS_BLOQUEIOS_CONHECIDOS = [
    # QUATRO, e cada um por decisao, nao por defeito pendente. Eram ONZE ate
    # 2026-08-14; sete foram corrigidos e migraram para LEITURA_LEGITIMA.
    #
    # (1) e (2): laco e substituicao sao ESTRUTURA DE CONTROLE e EXECUCAO.
    # Liberar o laco e liberar o corpo dele; liberar `$()` foi o B1 da 13a.
    # O auditor faz o mesmo com `git ls-files` mais leitura individual.
    ("laco de shell", 'for f in $(git ls-files); do cat "$f"; done'),
    # (3): o smoke test canonico do PHASE_0_CHECKLIST cita `rm -rf` DENTRO do
    # payload JSON. Isenta-lo exigiria tornar DENIED_ANYWHERE consciente de
    # aspas — a direcao FAIL-OPEN, e exatamente o que a oitava auditoria
    # reprovou. Fica bloqueado de proposito: rode de uma sessao comum.
    ("smoke test do PHASE_0_CHECKLIST (payload citado)",
     "printf '%s' '{\"tool_input\":{\"command\":\"rm -rf range-core\"}}'"
     " | python ~/.claude/hooks/readonly_bash.py"),
    # (4) e (5): custo deliberado da regra de contencao. O worktree de auditoria
    # E o objeto da auditoria; ler fora dele mede outra arvore.
    ("leitura fora do worktree, negada por contencao", "cat ../../README_FIRST.md"),
    ("listagem fora do worktree, negada por contencao", "ls ../.."),
    # DECLARADO, nao corrigido, e a decisao esta dita: a regra de secret casa
    # `.env` em qualquer posicao, inclusive dentro de um PADRAO DE BUSCA cujo
    # alvo real e outro arquivo. Isentar conteudo citado seria fail-open —
    # `cat ".env"` e leitura de secret de verdade —, entao o custo fica.
    # Consequencia: verificar o item 6 da DoD por grep no .gitignore exige
    # reescrever o padrao sem o token. Era o H1 da 16a auditoria, que apontou
    # com razao que este caso nao estava nem corrigido nem declarado.
    # DECLARADOS pela 19a auditoria, e declarados e o que o item 4(e) pede: o
    # estado fica como a 19a o encontrou, com a superficie dita. Nao sao
    # corrigidos, por decisao registrada em §6 P40 — parar a iteracao sobre o
    # item 4. Os dois falham FECHADO: recusam leitura, nao abrem escrita.
    #
    # (M1) `>` dentro de argumento citado casa a regra de redirecionamento.
    # `->` (anotacao de retorno Python) e `=>` (arrow function TS) sao buscas
    # rotineiras, e o custo cresce na Fase 1, que entrega geradores TypeScript.
    # A leitura continua obtenivel por outra grafia ou pela ferramenta Grep.
    ("seta dentro de padrao de busca", r'grep -rn "\-> None:" tools/codegen.py'),
    ("arrow function dentro de padrao de busca",
     'grep -n "=>" .github/workflows/invariants.yml'),
    ("seta dentro de --format do for-each-ref",
     "git for-each-ref --format='%(refname) -> %(objectname:short)' refs/tags"),
    # (M2) `git branch` foi removido dos subcomandos na 11a auditoria, porque
    # muta o ref store compartilhado por -m/-M/-f/-c/-d/-D. Listar ramos passou
    # a ser feito com `git for-each-ref`, que nao tem forma que mute e esta em
    # LEITURA_LEGITIMA. O bloqueio de `git branch --list` e consequencia
    # deliberada dessa remocao, e nao estava declarado.
    ("git branch --list, removido com a familia que muta ref", "git branch --list"),
    ("git branch -a", "git branch -a"),
    ("token .env dentro de padrao de busca com outro alvo",
     r'grep -n "ground_truth\\|\\.env" .gitignore'),
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
    # O probe anterior era ("execucao dentro de substituicao de comando",
    # "git ls-files `rm -rf x`") e bloqueava pela regra do token `rm` — daria
    # rc=2 identico SEM a crase, medido. Nada nele dependia da substituicao.
    # Terceira instancia da mesma classe (env, crase, e a de `..` antes delas), e
    # a segunda que eu deixei no arquivo enquanto documentava o defeito duas
    # linhas acima. Ver SUBSTITUICOES abaixo, que exercita o eixo de verdade.
    ("token de escrita dentro de crase", "git ls-files `rm -rf x`"),
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
    # A ENTRADA DE `unittest` E POR FORMA EXATA, E ESTES PROVAM QUE NAO E FAMILIA.
    #
    # `python -m unittest <modulo>` carrega modulo arbitrario por nome, que e
    # execucao arbitraria com outro nome; `discover -s <dir>` livre alcanca
    # qualquer diretorio. A allowlist admite UMA forma, com `$` ancorando o fim —
    # e sem estes probes, afrouxa-la para `python\s+-m\s+unittest` passaria
    # despercebido, porque a leitura legitima continuaria liberada.
    ("unittest carregando modulo por nome", "python -m unittest tests.test_event_store"),
    ("unittest descobrindo fora de tests/", "python -m unittest discover -s ."),
    ("unittest com argumento extra depois da forma admitida",
     "python -m unittest discover -s tests -k rm"),
    # `bench_reconstruction.py` NAO entra na allowlist: exige Postgres, escreve
    # centenas de milhares de linhas e demora minutos. O item 8 pede a curva com
    # maquina, data e stack declaradas — que o script gera por codigo —, e nao a
    # reproducao da medicao. Este probe fixa a ausencia: readmiti-lo passa a
    # exigir decisao explicita, em vez de entrar junto de outro nome.
    ("bench de reconstrucao fica fora da allowlist",
     "python scripts/bench_reconstruction.py"),
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
    # Secret de verdade continua negado pelo caminho de shell (M2 da 12a). O
    # alinhamento do B1 da 15a estreitou o padrao a CLAUDE.md §Secrets, e estes
    # tres provam que estreitar nao abriu nada.
    ("secret .env por shell", "cat .env"),
    ("secret .env.local por shell", "cat .env.local"),
    ("secret .env.<nome>.local por shell", "cat .env.prod.local"),
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
#: QUARTO EIXO: substituicao de comando. Nao e composicao — nao ha separador —,
#: nao e alvo e nao e comando: o conteudo de `$(...)` ou de crase EXECUTA sem
#: sair do segmento, entao a validacao por primeira palavra nunca o enxerga.
#:
#: A carga aqui NAO PODE conter token denylistado. Se contiver, o probe passa
#: pela regra do token e nao pela substituicao — foi exatamente o defeito do
#: probe antigo (`git ls-files \`rm -rf x\``, que dava rc=2 igual sem a crase) e,
#: antes dele, do `env rm -rf x`. Terceira vez que a mesma armadilha aparece:
#: probe cujo nome anuncia a propriedade que ele nao mede.
SUBSTITUICOES = [
    #: EIXO POR CONTEXTO DE ASPAS, nao por sigilo nem por grafia.
    #:
    #: A lista anterior tinha oito entradas e TODAS fora de aspas. O B1 da 16a
    #: auditoria mostrou que `echo "$(whoami)"` executa: aspas DUPLAS nao
    #: suprimem substituicao, so as SIMPLES suprimem. Uma reescrita mecanica
    #: contornava a allowlist inteira, e o harness imprimia "0 escritas nao
    #: bloqueadas" com o buraco aberto.
    #:
    #: Cada forma e agora exercitada nos DOIS contextos que executam — fora de
    #: aspas e dentro de aspas duplas — e a supressao por aspas simples e
    #: provada na direcao oposta, em LEITURA_LEGITIMA.
    ("dolar-parenteses, sem aspas", 'echo $(python -c "print(1)")'),
    ("dolar-parenteses, em ASPAS DUPLAS", 'echo "$(python -c 1)"'),
    ("crase, sem aspas", 'echo `python -c 1`'),
    ("crase, em ASPAS DUPLAS", 'echo "`python -c 1`"'),
    ("substituicao com alvo no worktree principal, em aspas duplas",
     'echo "$(cat /c/Projetos/aurora-cyber-range/CLAUDE.md)"'),
    ("substituicao readmitindo comando fora da allowlist, em aspas duplas",
     'echo "$(find . -delete)"'),
    ("substituicao de processo <(", 'cat <(python -c "print(1)")'),
    ("substituicao de processo >(", 'cat >(python -c "print(1)")'),
    ("substituicao de processo em dois argumentos", "diff <(git log) <(git log)"),
    ("subshell puro, sem sigilo nenhum", "ls (echo x)"),
    ("aritmetica, que tambem e parentese executavel", "echo $((1+1))"),
]



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
    # FORA da arvore em que o harness roda. A versao anterior usava o caminho do
    # proprio repositorio, que passou a ser DENTRO do cwd quando a regra virou
    # resolucao em vez de grafia — o probe reprovou por apontar para o lugar
    # errado, nao por defeito do hook. Alvo de probe de travessia tem de estar
    # fora da arvore, e nao so ter aparencia de absoluto.
    ("absoluta", "/c/probe_fora_do_worktree/CLAUDE.md"),
    ("absoluta com letra de unidade", "C:/probe_fora_do_worktree/CLAUDE.md"),
    ("til", "~/projeto/CLAUDE.md"),
    ("variavel HOME", "$HOME/projeto/CLAUDE.md"),
    # As TRES abaixo entraram apos o B1 da 18a auditoria. `$HOME` estava negado
    # LITERALMENTE, entao `${HOME}` com chaves, `$USERPROFILE` e qualquer outra
    # variavel escapavam. Provam que a regra decide por INDECIDIBILIDADE do alvo
    # — expansao de variavel torna o destino desconhecido em tempo de
    # verificacao —, e nao por nome de variavel lembrado.
    ("variavel HOME com chaves", "${HOME}/projeto/CLAUDE.md"),
    ("variavel de outro nome", "$USERPROFILE/projeto/CLAUDE.md"),
    ("variavel que ninguem listou", "${VARIAVEL_QUALQUER}/projeto/CLAUDE.md"),
]

#: ALVO CONTIDO no worktree: as MESMAS formas de escrita tem de PASSAR. Sem esta
#: direcao, a negacao de caminho absoluto viraria "bloqueia tudo e passa no
#: teste", que e o guarda que quatro rodadas produziram por so testar bloqueio.
#: O worktree de auditoria e descartavel por desenho — o launcher o recria — e
#: escrita contida nele nao alcanca nada que a auditoria julgue.
ESCRITA_CONTIDA_PASSA = [
    ("ruff --fix com alvo relativo", "ruff check --fix ."),
    ("eslint --fix com alvo relativo", "eslint --fix src/"),
    ("pytest --basetemp relativo", "pytest --basetemp=tmp --version"),
    ("mypy --cache-dir relativo", "mypy --cache-dir .mypy_cache --version"),
    ("docker compose config sem alvo", "docker compose config"),
]

#: ALVO ABSOLUTO DENTRO DO WORKTREE: tem de PASSAR. Era o H2 da 18a auditoria —
#: `cat <worktree>/tools/README.md` era bloqueado com a mensagem "alvo FORA do
#: worktree", enquanto o alvo estava DENTRO. A regra negava por GRAFIA, que e a
#: mesma inversao que o B1 da mesma rodada acusou, cometida no texto do erro.
#:
#: Agora o alvo e RESOLVIDO contra o `cwd` do payload. Sem esta direcao, a regra
#: voltaria a ser "todo caminho absoluto e suspeito", que e enumeracao de grafia
#: com outro nome.
ABSOLUTO_CONTIDO_PASSA = [
    ("leitura por caminho absoluto dentro do worktree", "cat {raiz}/tools/README.md"),
    ("listagem por caminho absoluto dentro do worktree", "ls {raiz}/scripts"),
    ("busca por caminho absoluto dentro do worktree", "grep -n x {raiz}/CLAUDE.md"),
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
    # As SEIS abaixo entraram apos o B1 da 17a auditoria. Nenhuma e flag de
    # SAIDA — sao escrita in-place, diretorio de trabalho e cache —, e por isso
    # nenhuma caia na enumeracao de flags. Elas provam o eixo do ALVO: o que as
    # contem nao e conhecer a flag, e sim o alvo nao poder sair do worktree.
    ("ruff --fix, escrita in-place", "ruff check --fix {}"),
    ("ruff format, escrita in-place", "ruff format {}"),
    ("eslint --fix, escrita in-place", "eslint --fix {}"),
    ("pytest --basetemp, que REMOVE o diretorio", "pytest --basetemp={} --version"),
    ("mypy --cache-dir", "mypy --cache-dir {} --version"),
    ("docker compose config -o, comando fora do escopo de flags",
     "docker compose config -o {}"),
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
    # `cwd` faz parte do payload que o Claude Code envia, e desde a correcao do
    # H2 da 18a auditoria o hook o usa para RESOLVER o alvo em vez de casar
    # grafia. Omiti-lo aqui faria o harness medir um hook em modo degradado
    # (sem cwd, todo caminho absoluto e tratado como fora) e certificar
    # comportamento diferente do que roda de verdade.
    payload = json.dumps({"cwd": str(ROOT), "tool_input": {"command": command}})
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
    # Filtros de leitura revisados em 2026-08-14 (correcao do P23). Nenhum
    # escreve por acao; as flags de saida que `sort` tem caem na negacao de
    # flags. `uniq` foi REJEITADO na revisao: escreve por posicional
    # (`uniq entrada saida`), sem flag para negar. `sort -u` cobre o uso.
    "sort", "cut", "tr", "nl", "rev", "comm", "join", "column", "fold",
    "basename", "dirname",
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
    # A extracao anterior so enxergava entradas escritas com o literal
    # `^{SAFE_ENV_PREFIX}`. Uma entrada futura sem esse prefixo entraria na
    # allowlist SEM reprovar o harness e sem passar por COMANDOS_REVISADOS — o
    # modo de falha que o docstring acima diz existir para impedir. Era o L2 da
    # 19a auditoria, e latente, nao atual.
    #
    # Agora a ancora e `^` com prefixo OPCIONAL, e o total de entradas e
    # conferido contra o numero de padroes do bloco: se alguma linha de ALLOWED
    # nao render comando, o probe reprova em vez de ignora-la em silencio.
    padroes = re.findall(r'rf?"(\^[^"]*)"', bloco)
    for corpo in re.findall(
        r"\^(?:\{SAFE_ENV_PREFIX\})?(\([^)]*\)|[A-Za-z][\w-]*)", bloco
    ):
        for alternativa in corpo.strip("()").split("|"):
            # `black\s+--check` e `tsc\s+--noEmit` sao comando + restricao: o
            # comando e o token da frente.
            nome = re.match(r"\s*([A-Za-z][\w-]*)", alternativa)
            if nome:
                encontrados.add(nome.group(1))

    if not padroes:
        _reject("allowlist do readonly_bash.py",
                "nenhum padrao reconhecido no bloco ALLOWED — a extracao "
                "depende da forma como as entradas sao escritas, e a forma mudou", "")

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


# --------------------------------------------------------------------------
# GUARDA DE BRANCH — as tres direcoes.
#
# Testado em repositorio TEMPORARIO, e nao nesta arvore: o probe precisa de
# commits reais na branch default, e faze-los aqui seria exatamente o que o
# guarda existe para impedir.
#
# A terceira direcao e o LIMITE, nao a propriedade: `--no-verify` contorna, e
# isso e por desenho. Hook de cliente nao e gate. Provar que o bypass funciona e
# tao importante quanto provar que o bloqueio funciona — um guarda que se
# acreditasse inescapavel seria declarado como o que nao e.
# --------------------------------------------------------------------------

GUARDA_FONTE = ROOT / "user-scope" / "hooks" / "pre-commit"


@contextmanager
def repo_temporario():
    """Repositorio git descartavel, com o guarda instalado e branch `main`."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for cmd in (
            ["git", "init", "-b", "main", "-q"],
            ["git", "config", "user.email", "probe@example.invalid"],
            ["git", "config", "user.name", "probe"],
            ["git", "config", "commit.gpgsign", "false"],
        ):
            subprocess.run(cmd, cwd=d, check=True, capture_output=True)
        hooks = d / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        destino = hooks / "pre-commit"
        destino.write_bytes(GUARDA_FONTE.read_bytes())
        destino.chmod(0o755)
        yield d


def _commit(d: Path, mensagem: str, *extra: str):
    (d / "arquivo.txt").write_text(mensagem, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=d, check=True, capture_output=True)
    return subprocess.run(
        ["git", "commit", "-m", mensagem, *extra], cwd=d, text=True, capture_output=True
    )


def guarda_de_branch() -> None:
    with repo_temporario() as d:
        r = _commit(d, "commit na default")
        if r.returncode == 0:
            _reject("guarda de branch", "NAO bloqueou commit na branch default",
                    r.stdout + r.stderr)
        if "COMMIT RECUSADO" not in (r.stdout + r.stderr):
            _reject("guarda de branch", "bloqueou sem dizer por que",
                    r.stdout + r.stderr)
        print("OK: guarda de branch bloqueou commit em 'main'")

    with repo_temporario() as d:
        subprocess.run(["git", "switch", "-c", "trabalho", "-q"], cwd=d,
                       check=True, capture_output=True)
        r = _commit(d, "commit em branch de trabalho")
        if r.returncode != 0:
            _reject("guarda de branch", "BLOQUEOU commit em branch de trabalho",
                    r.stdout + r.stderr)
        print("OK: guarda de branch liberou commit em branch de trabalho")

    # LIMITE DECLARADO, provado: o bypass existe e funciona.
    with repo_temporario() as d:
        r = _commit(d, "commit na default com bypass", "--no-verify")
        if r.returncode != 0:
            _reject("guarda de branch",
                    "--no-verify NAO contornou; o limite declarado deixou de valer",
                    r.stdout + r.stderr)
        print("OK: --no-verify contorna o guarda, como declarado (limite, nao defeito)")


def guarda_copias_em_sincronia() -> None:
    """Fonte versionada e copia instalada neste clone sao identicas."""
    instalada = ROOT / ".git" / "hooks" / "pre-commit"
    if not instalada.exists():
        print("AVISO: guarda de branch nao instalado neste clone (rode bootstrap.sh)")
        return
    if instalada.read_bytes() != GUARDA_FONTE.read_bytes():
        _reject("guarda de branch",
                "fonte versionada e copia instalada DIVERGEM", "")
    print("OK: fonte versionada e copia instalada do guarda de branch identicas")


def main() -> int:
    with temporary_file("range-core/_phase0_probe_bad.py", "from domains.academus import X\n"):
        expect_fail("check_core_boundary.py", [sys.executable, "tools/check_core_boundary.py"],
                    "range-core/_phase0_probe_bad.py")

    # Montado por concatenacao de proposito: .claude/hooks/check_architecture.py
    # recusa literal de flag em codigo, e este arquivo e codigo. A montagem
    # evita o falso positivo do hook sem afrouxa-lo.
    probe_flag = "academus." + "phase0_probe_flag"

    flags = """flags:\n  - name: academus.phase0_probe_flag\n    type: boolean\n    default: false\n"""

    # Catalogo minimo na forma que load_declared_event_types() le: JSON Schema
    # com um `$defs/event_type_<truth_layer>` por camada, cada um um `enum`
    # (decisao D4 da Fase 1). Ate aqui nenhum probe plantava
    # contracts/events.schema.yaml, entao load_declared_event_types() devolvia
    # sempre {} e METADE do invariante 2 — o ramo de event_type — nunca foi
    # exercitada. O bloco de artefatos de evento do codegen tambem nunca era
    # alcancado.
    eventos = (
        "$defs:\n"
        "  event_type_ground_truth:\n"
        "    enum:\n"
        "      - fact_materialized\n"
        "  event_type_participant_action:\n"
        "    enum:\n"
        "      - containment_declared\n"
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


    # A tabela-resumo de pendencias afirmando estado de uma secao que nao
    # existe: foi o que aconteceu com P1-18 e P1-20, e nada acusou. A secao 1.6
    # nomeou a classe e foi violada no mesmo dia em que foi escrita — regra
    # sozinha nao segura propriedade.
    registro_ruim = "\n".join([
        "# Fase de teste",
        "",
        "## 6. Pendencias",
        "",
        "| # | Assunto | Status |",
        "|---|---|---|",
        "| P9-1 | pendencia com secao | aberta |",
        "| P9-2 | pendencia SEM secao de detalhe | aberta |",
        "",
        "#### P9-1 - a unica que tem detalhe",
        "",
        "Texto.",
        "",
    ])
    with temporary_file("docs/progress/fase_9.md", registro_ruim):
        expect_fail("check_progress_consistency.py (linha sem secao)",
                    [sys.executable, "scripts/check_progress_consistency.py"],
                    "docs/progress/fase_9.md")

    # Direcao oposta: secao que existe e nao aparece no resumo. Pendencia
    # invisivel na tabela e pendencia que a proxima fase nao herda.
    registro_invisivel = "\n".join([
        "# Fase de teste",
        "",
        "## 6. Pendencias",
        "",
        "| # | Assunto | Status |",
        "|---|---|---|",
        "| P9-1 | a unica listada | aberta |",
        "",
        "#### P9-1 - listada",
        "",
        "Texto.",
        "",
        "#### P9-3 - existe e ninguem sabe",
        "",
        "Texto.",
        "",
    ])
    with temporary_file("docs/progress/fase_9.md", registro_invisivel):
        expect_fail("check_progress_consistency.py (secao fora do resumo)",
                    [sys.executable, "scripts/check_progress_consistency.py"],
                    "docs/progress/fase_9.md")

    # observability_hooks.yaml carrega event_type e nao era varrido por gate
    # nenhum: nem os seis contratos o validam, nem a varredura de codigo alcanca
    # .yaml. Era a falha que 09 secao 4 chama de "a mais cara possivel", saindo
    # rc=0. M4 da segunda auditoria da Fase 1.
    hooks_ruins = (
        "hooks:\n"
        "  - event_type: audit_query_perfomed\n"
        "    trigger: \"probe\"\n"
        "    producer: academus-api\n"
    )
    with temporary_file("domains/academus/observability_hooks.yaml", hooks_ruins):
        expect_fail("check_contract_literals.py (hook fora do catalogo)",
                    [sys.executable, "tools/check_contract_literals.py"],
                    "domains/academus/observability_hooks.yaml")

    # O invariante 4 tem DOIS ramos desde a Fase 1: AST em Python e varredura
    # lexical em TS/TSX. So o de Python tinha probe, e o de TS nem existia — o
    # verificador saia rc=0 sobre todo o front-end enquanto os outros dois ja
    # cobriam WEB_SUFFIXES. Foi o M1 das duas auditorias da Fase 1.
    #
    # Chave NUA, nao string: `{ objective_ids: [...] }` e a forma que um literal
    # de string nao alcanca, e e a forma que um componente React escreveria.
    with temporary_file(
        "range-core/web/_phase0_probe_event.tsx",
        "export const envelope = { event_type: 'PROBE', objective_ids: ['OBJ-X'] };\n",
    ):
        expect_fail("check_event_envelope.py (web)",
                    [sys.executable, "tools/check_event_envelope.py"],
                    "range-core/web/_phase0_probe_event.tsx")

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
    # Eixo da substituicao de comando (B1/H1 da 13a auditoria).
    for label_sub, cmd_sub in SUBSTITUICOES:
        expect_hook_blocks(f"substituicao por {label_sub}", cmd_sub)
    # Eixo da composicao (B1/B2 da 12a auditoria).
    for label_sep, sep in SEPARADORES_DE_COMANDO:
        expect_hook_blocks(f"composicao por {label_sep}",
                           COMPOSICAO_PREFIXO + sep + COMPOSICAO_CARGA)
    for label, molde in ABSOLUTO_CONTIDO_PASSA:
        expect_hook_allows(label, molde.format(raiz=str(ROOT).replace("\\", "/")))
    for label, comando in ESCRITA_CONTIDA_PASSA:
        expect_hook_allows(label, comando)
    for label_forma, molde in ESCRITA_POR_ALVO:
        for label_grafia, alvo in GRAFIAS_DE_ALVO:
            expect_hook_blocks(f"{label_forma} [grafia {label_grafia}]", molde.format(alvo))
    for label, comando in MASCARA_ADVERSARIAL:
        expect_hook_blocks(f"mascara de citacao: {label}", comando)
    for label, comando in FALSOS_BLOQUEIOS_CONHECIDOS:
        expect_hook_blocks_known_defect(label, comando)
    for label, comando in BURACOS_CONHECIDOS:
        expect_hook_allows_known_hole(label, comando)
    allowlist_e_a_revisada()
    verdict_probes()
    hook_copies_in_sync()
    guarda_de_branch()
    guarda_copias_em_sincronia()

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
