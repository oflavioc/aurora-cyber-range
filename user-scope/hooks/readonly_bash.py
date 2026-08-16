#!/usr/bin/env python3
"""PreToolUse — Bash restrito do checkpoint-auditor."""
from __future__ import annotations

import json
import os
import re
import sys

SAFE_ENV_PREFIX = r"(?:(?:PYTHONDONTWRITEBYTECODE|PYTHONHASHSEED|NODE_ENV)=[^\s]+\s+)*"

#: COMANDOS ALLOWLISTADOS SEM NENHUMA FORMA DE ESCRITA — usados por UMA coisa
#: so: a isencao de alvo INEXISTENTE em `_alvo_nao_contido`. Ver o docstring de
#: la para o argumento; aqui fica o criterio de admissao, que e estreito.
#:
#: Entra quem nao escreve por acao, nem por flag, nem por posicional — nao
#: "quem eu nao lembro de ter visto escrever". Tres exclusoes deliberadas, e
#: cada uma tem a forma de escrita nomeada, porque exclusao sem motivo vira
#: inclusao na proxima leitura distraida:
#:
#:   `tree`  — `tree -o <arquivo>` grava a arvore. Nao esta no escopo da regra
#:             de flags de escrita, entao hoje quem o contem e a regra de alvo.
#:   `sort`  — `sort -o` e `sort --output=`. Estao no escopo da regra de flags,
#:             e mesmo assim ficam de fora: contencao por duas regras que se
#:             cobrem e o desenho, e apoiar-se so na outra e apostar que ela nao
#:             mude.
#:   `git`   — `git diff|log|show --output=<arquivo>`, ja provado por probe.
#:
#: `uniq` nao aparece aqui porque nao esta na allowlist: escreve por posicional
#: (`uniq entrada saida`), e foi rejeitado na revisao de 2026-08-14.
LEITORES_SEM_ESCRITA = (
    "ls", "cat", "head", "tail", "wc", "grep", "rg", "stat", "diff",
    "cut", "tr", "nl", "rev", "comm", "join", "column", "fold",
    "basename", "dirname", "pwd", "echo", "printf", "which",
)

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
    # A SUITE DA FASE 2 E `unittest`, E NAO `pytest`.
    #
    # A entrada acima existia desde a Fase 0, quando nao havia suite nenhuma. A
    # Fase 2 criou a primeira suite real do projeto — 154 testes — em `unittest`,
    # por decisao registrada: `pytest` nao e dependencia do projeto, e
    # acrescenta-lo seria fecho transitivo novo a pinar por T15. O resultado foi
    # que o auditor da Fase 2 nao conseguiu executar NENHUM teste da fase e
    # voltou a avaliar por leitura de codigo — B1 da auditoria de 16/08/2026, e
    # reincidencia do H3 da segunda auditoria da Fase 1.
    #
    # FORMA EXATA, e nao familia. `python -m unittest discover -s tests` e o
    # comando que o CI roda (`invariants.yml`), com `$` ancorando o fim: um
    # `python -m unittest <qualquer coisa>` continua bloqueado. Admitir a familia
    # daria ao auditor a capacidade de carregar modulo arbitrario por nome, que e
    # execucao arbitraria com outro nome — e `discover -s <dir>` livre alcancaria
    # qualquer diretorio.
    rf"^{SAFE_ENV_PREFIX}python\s+-m\s+unittest\s+discover\s+-s\s+tests\s*$",
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
    #
    # A Fase 1 acrescentou DUAS provas centrais da mesma natureza:
    # `check_contract_examples.py`, que executa os exemplos dos seis contratos
    # (item 1 da DoD), e `check_contract_examples_probes.py`, que prova que
    # aquele executor reprova contra defeito plantado. Sem elas na lista, o
    # auditor da Fase 1 nao pode executar o mecanismo que fecha o item 1 e volta
    # a avaliar por leitura de codigo — que e exatamente o modo de auditar que o
    # item existe para nao aceitar. Foi o H3 da segunda auditoria da Fase 1.
    #
    # NOMES EXPLICITOS EM ALTERNACAO, nao curinga sob scripts/. Um
    # `scripts/[A-Za-z0-9_]+\.py` pre-autorizaria o auditor a executar qualquer
    # script que um commit futuro acrescentasse, inclusive um que escrevesse —
    # e o curinga equivalente sob .claude/hooks/ foi o H1 da setima auditoria.
    # Script novo que precise ser executado pelo auditor entra aqui por nome, no
    # commit que o cria.
    #
    # SEM ARGUMENTO. `check_contract_examples.py` aceita um diretorio alternativo
    # de contratos, mas quem o usa e o probe, por subprocess de Python — que o
    # hook nao intercepta. O auditor roda as duas formas sem argumento, entao
    # admitir um token arbitrario afrouxaria a ancora `$` sem ganho nenhum.
    #
    # A FASE 2 ACRESCENTOU QUATRO VERIFICADORES E UM DEMO, e cada um entra por
    # nome com o seu motivo:
    #
    # `check_store_read_surface` — P2-2, a metade da garantia de `01` §4.1 que
    #   vive fora do fold: o store nao pode OFERECER filtro. Sem executa-lo, o
    #   auditor le a lista de metodos e infere.
    # `check_store_read_surface_probes` — prova que o anterior reprova. Entrada
    #   sem a prova negativa dela seria admitir um verificador sem saber se ele
    #   enxerga, que e o que a Fase 0 gastou dezenove rodadas para nao aceitar.
    # `check_core_contract_imports` — P2-15, a whitelist do que o core importa de
    #   `contracts/`.
    # `check_core_contract_imports_probes` — idem, a prova negativa.
    # `demo_fase2` — o DEMO SCRIPT que `07` exige da fase. Roda em memoria, sem
    #   banco e sem escrever arquivo; e o unico artefato que exercita a MONTAGEM
    #   ponta a ponta, e le-lo nao substitui roda-lo.
    #
    # `bench_reconstruction` FICA DE FORA, e a ausencia e decisao registrada:
    # ele exige Postgres, ESCREVE centenas de milhares de linhas e demora
    # minutos. O item 8 nao pede reproducao — pede a curva com maquina, data e
    # stack declaradas, e o script as gera POR CODIGO, o que e conferivel por
    # leitura. Admiti-lo daria ao auditor uma operacao de escrita longa para
    # confirmar um numero que a forma ja garante. Ver o limite declarado no
    # registro da Fase 2.
    rf"^{SAFE_ENV_PREFIX}python\s+scripts/"
    rf"(?:phase0_negative_tests|check_contract_examples|check_contract_examples_probes"
    rf"|check_spec_examples|check_spec_examples_probes"
    rf"|check_progress_consistency"
    rf"|check_store_read_surface|check_store_read_surface_probes"
    rf"|check_core_contract_imports|check_core_contract_imports_probes"
    # `check_gate_coverage` — P37. Sem executa-la, o auditor le a tabela de
    # classificacao e infere; com ela, mede. A prova negativa entra junto pelo
    # mesmo motivo das outras: verificador cuja prova nao roda e verificador
    # cuja propriedade o auditor aceita da palavra de quem o escreveu.
    rf"|check_gate_coverage|check_gate_coverage_probes"
    # `check_spec_flags` — Fase 3. Cruza flag citada na spec com flag declarada
    # no adapter. Sem executa-la, o auditor le duas listas e compara a olho, que
    # e a forma de auditar que o item existe para nao aceitar.
    rf"|check_spec_flags|check_spec_flags_probes"
    # `check_api_surface` — Fase 3, peca 2. E a checagem que responde "a API e o
    # que ela diz que e". Sem executa-la, o auditor compara YAML com codigo a
    # olho, sobre uma arvore que so cresce.
    rf"|check_api_surface|check_api_surface_probes"
    # `check_fold_authority` — Fase 3, peca 3. Responde "so o fold escreve
    # estado", que e a garantia de `01` secao 4.1 depois de a projecao ser
    # materializada. Sem executa-la, o auditor le a porta e confia no formato.
    rf"|check_fold_authority|check_fold_authority_probes"
    # `check_pinned_images` — Fase 3, peca 4, fechando a P3-1. Cruza o digest
    # das imagens entre o compose e o workflow. Sem executa-la, o auditor
    # compara dois sha256 de 64 caracteres a olho — que e exatamente como o
    # digest inventado da peca 3 passou pela minha propria revisao.
    rf"|check_pinned_images|check_pinned_images_probes"
    # `check_audit_base_probes` — P3-7. A guarda de base decide se uma auditoria
    # e PORTA ou LAUDO, isto e, e a checagem mais consequente do aparato; e ela
    # ficou fora da allowlist no commit que a criou, contra a regra escrita
    # acima. O resultado foi o M5 da quarta auditoria da Fase 3: os oito eixos
    # avaliados por LEITURA, no mecanismo que julga o proprio auditor.
    #
    # SO OS PROBES, e nao `check_audit_base.py`: o verificador exige argumentos
    # (`--phase`, `--default`) e esta forma da allowlist termina em `.py$` de
    # proposito. Admitir argumento para um script abriria superficie de
    # argumento — e o historico deste arquivo e uma lista de furos que entraram
    # exatamente assim. Os probes rodam sem argumento e provam os oito eixos,
    # que e o que o M5 cobra.
    rf"|check_audit_base_probes"
    rf"|demo_fase2)"
    rf"\.py(?:\s+2>\s*/dev/null)?\s*$",
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

#: REDIRECIONAMENTO — a unica regra que NAO roda contra o comando cru, e o
#: motivo esta em `_redirecionamento_para_arquivo`. `/dev/null` e descarte,
#: nao escrita: nada persiste. `&1`/`&2` sao duplicacao de descritor, tambem sem
#: arquivo. Sem estas isencoes, tres dos onze falsos bloqueios do P23 vinham
#: daqui — `2>/dev/null` no verificador, no harness e no git — e cada um
#: empurrava a auditoria para inferencia. A negacao continua valendo para
#: QUALQUER outro alvo.
REDIRECIONAMENTO = r">>?\s*(?!/dev/null\b)(?!&[12]\b)\S"

DENIED_ANYWHERE = [
    (r"\|\s*tee\b", "escrita via tee"),
    (r"\b(rm|mv|cp|chmod|chown|mkdir|touch|truncate)\b", "comando de escrita"),
    # (?!-) impede que `merge-base` case como `merge`: o \b depois de "merge"
    # casa contra o hifen. Era o falso bloqueio registrado em P16, e merge-base
    # e justamente o que o auditor usa para comparar contra main.
    (r"\bgit\s+(commit|push|add|reset|checkout|switch|merge|rebase|clean|restore)\b(?!-)", "git que altera estado"),
    # A fronteira tem de ser INICIO DE COMANDO, nao `\b`: `\b` casava `nc` dentro
    # de `\nc` — a barra invertida conta como fronteira de palavra —, e um payload
    # com `\nc = 6` era recusado como "acesso de rede". Era o L2 da 15a auditoria.
    (r"(?:^|[\s;&|])(curl|wget|nc|ssh|scp)\b", "acesso de rede"),
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
    # CAMINHO ABSOLUTO — a outra metade da mesma propriedade, e a que faltava.
    #
    # A decima auditoria mostrou que negar `..` nao continha nada, porque o mesmo
    # alvo tem grafia absoluta. A conclusao que tirei entao foi "policiar
    # capacidade, nao alvo" — e SEIS RODADAS enumerando capacidade provaram que
    # ela e ilimitada: `-o`, `--junitxml`, `--output`, e agora `--fix`,
    # `format`, `--basetemp`, `--cache-dir`. Ferramenta de verdade escreve de
    # muitos jeitos, e a lista nunca fecha.
    #
    # Eu tinha abandonado a metade errada. O invariante util nao e "este comando
    # escreve?", que e indecidivel por texto; e "ESTE ALVO SAI DO WORKTREE?",
    # que tem exatamente tres grafias: relativa com `..`, absoluta, e `~`/$HOME.
    # As tres sao negaveis. Com as tres negadas, `ruff check --fix .` continua
    # passando e fica CONTIDO — o worktree de auditoria e descartavel por
    # desenho, e o launcher o recria a cada rodada.
    #
    # Isto fecha flag desconhecida e flag futura sem enumerar nenhuma: o que
    # importa deixa de ser como a ferramenta escreve, e passa a ser onde.
    #
    # Excecoes, as duas por necessidade e delimitadas:
    #   - `/dev/null`, que e descarte;
    #   - `~/.claude/hooks/` e `$HOME/.claude/hooks/`, que sao os smoke tests
    #     prescritos pelo PHASE_0_CHECKLIST e ja allowlistados por nome explicito.
    #
    # Custo aceito e declarado: leitura por caminho absoluto passa a ser
    # bloqueada. E o mesmo custo ja aceito para `..` — o worktree de auditoria E
    # o objeto da auditoria, e ler fora dele mede outra arvore.
    # (a regra de alvo saiu daqui: virou `_alvo_nao_contido`, que RESOLVE contra
    #  o cwd em vez de casar grafia. Ver o docstring de la.)
    # ATENCAO — este comentario dizia "`git branch` listando e leitura legitima e
    # nao pode ser negado inteiro; so a delecao". ISSO NAO E MAIS VERDADE, e
    # contradizia tanto o codigo quanto o comentario de :16-19 do mesmo arquivo.
    # Era o M2 da 19a auditoria.
    #
    # O que vale: `branch` FOI removido dos subcomandos allowlistados na 11a
    # auditoria, porque muta o ref store compartilhado por -m/-M/-f/-c alem de
    # -d/-D. `git branch` inteiro e negado pela allowlist, e listar ramos se faz
    # com `git for-each-ref`, que nao tem forma que mute.
    #
    # Esta regra fica como camada extra e redundante para a delecao — nao como
    # a fronteira, que e a allowlist. O ref store e COMPARTILHADO com o worktree
    # principal: provado por execucao, `git branch -D` rodado de dentro do
    # worktree de auditoria apagou o ramo visivel do repositorio principal.
    (r"\bgit\s+branch\b[^;&|]*\s-{1,2}(?:[dD]|delete)\b", "git branch que apaga ref compartilhado"),
    # FLAGS DE ESCRITA dos comandos que continuam allowlistados porque rodar
    # teste e linter e o trabalho do auditor: pytest, ruff, mypy, eslint, tsc.
    #
    # Isto E enumeracao, e a enumeracao aqui e defensavel onde a de alvos nao
    # era: a superficie e FECHADA POR COMANDO — sao as flags de saida que essas
    # cinco ferramentas documentam —, enquanto a de alvos era aberta, porque
    # qualquer caminho tem infinitas grafias. Flag nova encontrada e finding
    # pelo item 4(d) da DoD, nao defeito aceito.
    # ESCOPADA POR COMANDO, e agora com o que ela NAO cobre dito na cara.
    #
    # Esta regra enumera FLAGS DE SAIDA de seis comandos. Ela nao cobre, e nunca
    # cobriu, as outras formas de escrita dessas mesmas ferramentas: `--fix`,
    # `format`, `--basetemp`, `--cache-dir`, e o `-o` de `docker compose config`,
    # que nem esta entre os comandos escopados. Foi o B1 e o H1 da 17a auditoria,
    # e o comentario anterior afirmava fechamento onde nao havia — a mesma
    # divergencia entre desenho declarado e mecanismo implementado que o H1 da
    # 14a puniu, reincidindo dentro do texto que descrevia aquela correcao.
    #
    # O que de fato contem essas formas nao e esta regra: e a NEGACAO DE CAMINHO
    # ABSOLUTO acima. `ruff check --fix .` passa e fica contido no worktree
    # descartavel; `ruff check --fix /c/Projetos/...` e negado pelo alvo, nao
    # pela flag. Esta regra fica como camada extra para o caso contido, nao como
    # fronteira.
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
    # ALINHADO A CLAUDE.md §Secrets: `.env`, `.env.local`, `.env.*.local`.
    # A versao anterior era `\.env(?:\.[A-Za-z0-9_.-]+)?` e casava `.env.example`,
    # que a norma PERMITE explicitamente e que 05_SECURITY_REQUIREMENTS §6 exige
    # versionado. Era o MESMO overmatch da P17, corrigido em .claude/settings.json
    # no commit 0b425f1 e deixado intacto aqui: dois mecanismos implementando a
    # mesma norma, divergindo. Foi o B1 da 15a auditoria.
    (r"(?:^|[\s=\"'/\\])\.env(?:\.local|\.[A-Za-z0-9_.-]+\.local)?(?:[\s\"']|$)"
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
]


SEPARADORES = r"\|\||&&|;|\||\n|\r|(?<![>&])&(?![>&])"


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

    `>` e `<` entraram no conjunto neutralizado com a P3-8, e servem so a
    `_redirecionamento_para_arquivo`. Para `_segmentos` sao inertes: nunca
    foram separadores.
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
            saida.append("\x00" if ch in "|&;\n\r()<>" else ch)
    return "".join(saida), aspas is None


def _redirecionamento_para_arquivo(cmd: str) -> bool:
    """Ha redirecionamento, com a semantica de aspas que o BASH da a `>`.

    P3-8, e esta e a metade que precisa do argumento inteiro, porque ela parece
    o que a oitava auditoria da Fase 0 reprovou e nao e.

    O QUE FOI REPROVADO LA: mascarar o conteudo citado ANTES de procurar
    substituicao de comando. Aquilo era fail-open **porque o bash expande
    `$(...)` dentro de aspas duplas** — o texto mascarado nao executava menos
    do que o cru.

    `>` NAO E ASSIM. Dentro de aspas — simples ou duplas — ele nao redireciona
    coisa nenhuma: `echo "a > b"` imprime `a > b` e nao cria arquivo. Aplicar a
    regra ao texto cru nao era rigor, era ler outro shell que nao o bash — e o
    preco foram tres falsos bloqueios declarados desde a 19a auditoria da Fase 0
    (`->`, `=>`, e a seta dentro de `--format`), mais o `->` que a segunda
    auditoria da Fase 3 encontrou empurrando o achado dela para inferencia.

    E O MESMO CONSERTO DA 16a AUDITORIA, na direcao oposta. La,
    `_substituicao_ou_subshell` deixou de usar uma mascara unica e passou a
    implementar a semantica de aspas do PROPRIO construto — porque aspas simples
    e duplas nao fazem a mesma coisa com `$(`. A regra que sai das duas e uma so:
    **cada construto e decidido com a semantica que o bash lhe da**, e nao com
    uma mascara que serve para todos.

    O QUE SUSTENTA A SEGURANCA, e nao e a mascara: para um `>` citado virar
    redirecionamento de verdade, algum comando precisa reinterpretar a string
    como shell — `sh -c`, `bash -c`, `eval`, `xargs`, `python -c`. **Nenhum
    deles esta na allowlist**, e isso e propriedade de whitelist, nao
    enumeracao: comando novo nasce bloqueado. Os probes exercitam os cinco.

    PARSE DUVIDOSO CAI PARA O CRU, como em `_segmentos`: aspas escapadas ou nao
    fechadas voltam ao texto original, que acha MAIS redirecionamento. Falha
    fechada.
    """
    texto, confiavel = _mascara_de_citacao(cmd)
    return re.search(REDIRECIONAMENTO, texto if confiavel else cmd) is not None


SMOKE_TEST_HOOK = re.compile(r"^(?:~|\$\{?HOME\}?)/\.claude/hooks/[A-Za-z0-9_.-]+\.py$")


def _normaliza(caminho: str) -> str:
    """Grafias equivalentes de um mesmo caminho, no formato do Git Bash."""
    p = caminho.replace("\\", "/").rstrip("/")
    m = re.match(r"^([A-Za-z]):(/.*)?$", p)
    if m:
        p = "/" + m.group(1).lower() + (m.group(2) or "")
    return p.lower()


def _primeiro_comando(segmento: str) -> str:
    """A primeira palavra do segmento, sem o prefixo de ambiente seguro."""
    resto = re.sub(rf"^{SAFE_ENV_PREFIX}", "", segmento.strip())
    m = re.match(r"[A-Za-z][\w.-]*", resto)
    return m.group(0) if m else ""


def _existe_no_disco(alvo: str) -> bool:
    """O alvo existe como caminho? Indecidivel conta como EXISTE — falha fechada.

    AS DUAS GRAFIAS SAO TESTADAS, e a segunda e o defeito que este projeto
    cometeria sem medir: no Git Bash o caminho absoluto e `/c/Projetos/...`, e
    `os.path.exists` do Python de Windows resolve isso contra a raiz da unidade
    corrente — `C:\\c\\Projetos\\...`, que nao existe. Um teste de existencia
    ingenuo diria "nao existe" justamente para o caminho real da arvore
    principal, que e o alvo que a contencao mais precisa negar.
    """
    candidatos = [alvo]
    m = re.match(r"^/([A-Za-z])(/.*)?$", alvo)
    if m:
        candidatos.append(f"{m.group(1)}:{m.group(2) or '/'}")
    for candidato in candidatos:
        try:
            if os.path.exists(candidato):
                return True
        except (OSError, ValueError):
            return True
    return False


def _alvo_nao_contido(cmd: str, cwd: str | None, *, leitor_puro: bool = False) -> str | None:
    """RESOLVE o alvo contra o cwd. Nao casa grafia.

    A 17a auditoria me levou a "o invariante e o ALVO, nao a capacidade", e eu
    implementei... uma checagem de GRAFIA do alvo: neguei `~` e `$HOME`
    literalmente. A 18a chegou com `${HOME}`, `$USERPROFILE` e `$TEMP`, que sao o
    mesmo alvo em grafias que eu nao lembrei — **quarta reincidencia da mesma
    classe, dentro da correcao que a nomeou**.

    Duas mudancas, e as duas trocam enumeracao por decisao:

    1. **Expansao de variavel torna o alvo INDECIDIVEL, entao nega.** Nao importa
       o nome: `$X` pode valer qualquer coisa no momento da execucao, e um alvo
       que so se conhece em tempo de execucao nao pode ser provado contido. Isto
       cobre `$USERPROFILE` e a variavel que ninguem inventou ainda, sem lista.

    2. **Caminho absoluto e RESOLVIDO contra o cwd**, nao negado por comecar com
       `/`. Era o H2 da 18a: `cat /c/.../.aurora-worktrees/audit/tools/README.md`
       era bloqueado com a mensagem "alvo FORA do worktree" enquanto o alvo estava
       DENTRO. Negar por grafia e a mesma inversao que o B1 acusa, cometida no
       texto da mensagem de erro.

    Sem `cwd` no payload, todo caminho absoluto e tratado como fora: falha
    fechada, porque nao dar para resolver e o caso em que nao se pode afirmar
    contencao.

    Excecoes, as duas por necessidade e delimitadas: `/dev/null`, que e descarte;
    e o smoke test de hook que o PHASE_0_CHECKLIST prescreve, ja allowlistado por
    nome explicito.

    A TERCEIRA EXCECAO E A P3-8, e ela tem DUAS condicoes que valem juntas
    (`leitor_puro`): o alvo **nao existe como caminho** E o comando do segmento
    **nao tem forma de escrever**.

    O caso medido: `grep -n "/turmas/{turma_id}/diario" domains/...` — as tres
    rotas da DoD da Fase 3 comecam com `/`, entao o tokenizador as via como
    caminho absoluto, resolvia contra o cwd e recusava. Path de URL nao e alvo
    de arquivo, e a distincao **nao pode ser a citacao**: `cat "/etc/passwd"`
    tambem esta entre aspas e e alvo de verdade.

    Nenhuma das duas condicoes basta sozinha, e isso e o desenho:

      so inexistencia   — `pytest --basetemp=/c/outra/arvore` CRIA o diretorio;
      so leitor puro    — `cat /c/Projetos/...` le a arvore principal, e ler
                          fora do worktree mede outra arvore.

    O CUSTO, declarado: a propriedade "leitura fora do worktree e bloqueada"
    passa a valer "quando ha o que ler". `cat /nao/existe` deixa de ser
    recusado — e nao le nada, porque nao ha nada. E a decisao passa a depender
    do disco, o que e novo neste hook: o mesmo comando pode ser aceito numa
    maquina e recusado noutra. Fica dito porque e verdade, nao porque incomoda.

    `leitor_puro` chega do chamador, que o calcula POR SEGMENTO — o comando dono
    do alvo e o do segmento em que ele aparece, e `git log | grep /x` tem dois.
    Quando o parse de aspas nao e confiavel, o chamador manda `False`: sem saber
    onde os segmentos comecam, nao se sabe de quem e o alvo.
    """
    raiz = _normaliza(cwd) if cwd else None

    for token in re.findall(r"[^\s\"'=]+", cmd):
        alvo = token.lstrip("<>|&")
        if not alvo or alvo == "/dev/null" or SMOKE_TEST_HOOK.match(alvo):
            continue

        if "$" in alvo and re.search(r"\$\{?[A-Za-z_]", alvo):
            return f"expansao de variavel: alvo indecidivel em tempo de verificacao ({alvo})"

        if alvo.startswith("~"):
            return f"til: alvo fora do worktree de auditoria ({alvo})"

        eh_absoluto = alvo.startswith("/") or re.match(r"^[A-Za-z]:[/\\]", alvo)
        if not eh_absoluto:
            continue
        if raiz is None:
            return f"caminho absoluto sem cwd para resolver ({alvo})"
        if _normaliza(alvo).startswith(raiz):
            continue
        if leitor_puro and not _existe_no_disco(alvo):
            continue
        return f"caminho absoluto fora do worktree de auditoria ({alvo})"

    return None


def _substituicao_ou_subshell(cmd: str) -> bool:
    """Deteccao de EXECUCAO, com a semantica POSIX de aspas — nao com uma so.

    ASPAS SIMPLES suprimem tudo. ASPAS DUPLAS **nao suprimem** `$(...)` nem
    crase: `echo "$(whoami)"` executa. Essa e a unica distincao que importa
    aqui, e ignora-la foi o B1 da 16a auditoria.

    A versao anterior chamava `_mascara_de_citacao`, que trata os dois tipos de
    aspas igualmente, e perguntava se sobrara `(`. Como `"$( )"` era mascarado,
    a substituicao sumia antes do teste — e a allowlist inteira ficava
    contornavel por uma reescrita mecanica: `echo $(cmd)` bloqueado,
    `echo "$(cmd)"` liberado, com o mesmo efeito.

    **Este e o defeito que a oitava auditoria ja havia descrito**, no desenho
    tokenizado: apagar o conteudo citado antes de procurar substituicao, quando
    o bash expande dentro de aspas duplas. Eu li aquele registro, escrevi no
    docstring anterior que a ordem aqui era "a inversa" e portanto segura, e
    reintroduzi a mesma falha ao acrescentar a checagem de parentese sobre o
    texto mascarado. Terceira reincidencia da mesma classe nesta fase.

    O que cada contexto executa:

    | contexto        | `$(`  | crase | `(` sozinho |
    |-----------------|-------|-------|-------------|
    | fora de aspas   | exec  | exec  | subshell    |
    | aspas duplas    | exec  | exec  | literal     |
    | aspas simples   | literal | literal | literal   |

    Por isso `grep -n "foo(bar)"` e `--format='%(refname)'` seguem liberados: o
    parentese sozinho e literal nos dois tipos de aspas.

    Parse duvidoso — aspas escapadas ou nao fechadas — devolve True. A queda e
    para o lado FECHADO, ao contrario da queda em `_segmentos`: nao enxergar
    substituicao libera execucao; nao enxergar separador so bloqueia mais.

    LIMITE DECLARADO: `${ cmd; }` do bash 5.3 nao e coberto. Nao ha `(`, e a
    forma nao existia quando a allowlist foi desenhada. Fica dito aqui em vez de
    suposto ausente.
    """
    if re.search(r"\\['\"]", cmd):
        return True

    aspas: str | None = None
    i, n = 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if aspas == "'":
            if ch == "'":
                aspas = None
        elif aspas == '"':
            if ch == '"':
                aspas = None
            elif ch == "`":
                return True
            elif ch == "$" and i + 1 < n and cmd[i + 1] == "(":
                return True
        else:
            if ch in "\"'":
                aspas = ch
            elif ch == "`":
                return True
            elif ch in "()":
                return True
        i += 1

    return aspas is not None


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

    cwd = data.get("cwd")
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

    if _redirecionamento_para_arquivo(cmd):
        print(
            "BLOQUEADO: checkpoint-auditor sem escrita deliberada "
            "(redirecionamento de saida para arquivo).\n"
            f"Comando: {cmd}\nReporte o finding; nao corrija.",
            file=sys.stderr,
        )
        return 2

    # POR SEGMENTO, e nao sobre o comando inteiro: a isencao da P3-8 depende de
    # QUAL comando e dono do alvo, e `git log | grep /x` tem dois. A cobertura
    # nao muda — os segmentos particionam o comando —, muda o que se sabe sobre
    # cada token. Parse duvidoso derruba a isencao: `_segmentos` ja cai para o
    # texto cru, e sem saber onde um segmento comeca nao se sabe de quem e o alvo.
    _, citacao_confiavel = _mascara_de_citacao(cmd)
    for segmento in _segmentos(cmd):
        motivo_alvo = _alvo_nao_contido(
            segmento,
            cwd,
            leitor_puro=citacao_confiavel
            and _primeiro_comando(segmento) in LEITORES_SEM_ESCRITA,
        )
        if motivo_alvo:
            print(
                f"BLOQUEADO: checkpoint-auditor sem escrita deliberada ({motivo_alvo}).\n"
                f"Comando: {cmd}\n"
                "O worktree de auditoria E o objeto da auditoria; alvo fora dele mede\n"
                "outra arvore. Reporte o finding; nao corrija.",
                file=sys.stderr,
            )
            return 2

    if _substituicao_ou_subshell(cmd):
        print(
            "BLOQUEADO: checkpoint-auditor sem escrita deliberada "
            "(substituicao de comando ou subshell).\n"
            f"Comando: {cmd}\n"
            "Parentese literal entre aspas e permitido; $() e crase nao,\n"
            "nem dentro de aspas duplas. Reporte o finding; nao corrija.",
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
