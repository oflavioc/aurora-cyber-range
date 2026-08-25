#!/usr/bin/env python3
"""D16 — todo script de `scripts/` esta na allowlist do auditor ou declarado fora.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
A regra *"script novo que precise ser executado pelo auditor entra na allowlist
por nome, no commit que o cria"* esta escrita DENTRO do `readonly_bash.py`, e o
proprio arquivo documenta duas violacoes dela: o H3 da Fase 1 e o M5 da quarta
auditoria da Fase 3. O M1 da Fase 5 foi a terceira.

**Tres correcoes, e nenhuma impediu a seguinte.** A regra esta no lugar certo e
depende de alguem le-la na hora certa — que e a definicao de disciplina, e a §1.6
do registro da Fase 1 separa disciplina de impedimento.

O QUE ELA NAO E: um gate que exija allowlist para todo script. Metade deles fica
fora por decisao — o que se cobra e a DECLARACAO, com motivo, na forma do
`DESCRITIVO` de `check_gate_coverage.py`. O custo de acrescentar e uma frase, e e
ela que separa "decidimos que fica de fora" de "ninguem olhou".

ELE LE A FONTE VERSIONADA, E NAO A COPIA INSTALADA — declarado, nao suposto
-----------------------------------------------------------------------------
`HOOK` aponta para `user-scope/hooks/readonly_bash.py`, que e a fonte no
repositorio. **A copia que o Claude Code de fato executa vive em
`~/.claude/hooks/`, e este verificador nao a le.**

Sao duas perguntas, e ele responde uma:

    RESPONDE     "a FONTE declara este script?"
    NAO RESPONDE "o auditor consegue de fato executa-lo?"

A segunda depende da copia instalada estar em dia com a fonte, e isso e assunto
de outro mecanismo: `scripts/sincroniza_escopo_de_usuario.py`, que o lancador
roda antes de abrir a sessao — a **P6-9**. A deteccao da divergencia continua
com `phase0_negative_tests.py`, que compara as duas.

**A declaracao esta aqui porque a ausencia dela era a propria classe que a
pendencia mede.** Ate a P6-9 este cabecalho nao dizia qual das duas copias ele
lia, e quem o lesse concluiria que "a allowlist esta certa" significa "o auditor
roda o script" — que e a segunda pergunta, e ele nao a faz. Verificador que nao
declara a sua fronteira e lido como cobrindo mais do que cobre.

AS QUATRO DIRECOES
-------------------
    (a) script versionado em `scripts/` ausente da allowlist e sem
        entrada no registro de exclusao                            -> REPROVA
    (b) entrada do registro nomeando script que nao existe          -> REPROVA
    (c) exclusao declarada para script que ESTA na allowlist        -> REPROVA
    (d) a leitura da allowlist divergiu do matcher real             -> REPROVA

`*.sh` FICA FORA POR CLASSE DECLARADA, e nao por omissao do universo
---------------------------------------------------------------------
Ha um unico: `start_checkpoint_audit.sh`, o lancador. A exclusao e ESTRUTURAL e
nao de conveniencia — **ele abre a sessao do auditor**, entao roda-lo de dentro
dela seria recursao. Nenhum outro `.sh` existe, e se um nascer ele cai nesta
classe e precisa de decisao propria.

**Universo que exclui por nao incluir e a mesma forma de "coberto por nada" que a
§4 e a §6 de `05` tiveram** — e as duas custaram uma auditoria cada. Por isso a
classe esta escrita aqui, com motivo, em vez de o glob simplesmente nao pegar.

A (d) E A DIRECAO QUE A ESCOLHA POR REGEX EXIGE
------------------------------------------------
A extracao dos nomes e por REGEX sobre o fonte do hook — o padrao e uma f-string
concatenada, e o AST dela e menos direto do que parece. **Regex sobre codigo e
fragil na direcao que importa: pode deixar de casar quando o formato mudar, e
passar verde.** Extrair tres nomes de vinte passaria igual a extrair vinte.

Entao a leitura textual e cruzada com o MATCHER REAL: `ALLOWED` e importado do
proprio hook, e para cada script do universo compara-se "o matcher libera?" com
"a leitura textual o encontrou?". **Divergencia reprova por divergencia**, antes
de qualquer conclusao sobre classificacao — que e a mesma forma do
`check_gate_coverage.py`, que confere o proprio casamento contra o `git ls-files`.

P4-11 VALE AQUI, E ESTA E A TERCEIRA OCORRENCIA
-------------------------------------------------
Este verificador **mora na arvore que ele audita** e le o hook que constrange o
auditor. A direcao e ADITIVA — verificador novo, somente leitura, com prova
negativa ao lado —, entao a P4-11 nao dispara: o gatilho dela e *alteracao de
`readonly_bash.py` em direcao que nao seja estritamente aditiva*.

Mas a contagem importa, e esta registrada na §10.5 da Fase 5: e o **terceiro**
mecanismo nessa situacao. Pendencia com condicao de vencimento e nao com marco
parece inativa quando esta apenas esperando a direcao errada.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "user-scope" / "hooks" / "readonly_bash.py"

RULE = "D16 - scripts/ x allowlist do auditor"

#: A ALTERNACAO DE NOMES dentro do padrao de `python scripts/...`. O fonte traz
#: `rf"|nome|nome_probes"` em varias linhas, com comentarios entre elas — e a
#: PRIMEIRA abre o grupo com `rf"(?:nome|nome"`, que a primeira versao deste
#: regex nao casava. **A direcao (d) pegou isso na primeira execucao**, com
#: quatro nomes so no matcher e nenhum na leitura. Depois de corrigido, ela pegou
#: mais um: a ULTIMA entrada fecha o grupo — `rf"|demo_fase2)"` —, e o `)` fazia
#: o nome nao casar. Duas vezes na mesma sessao, e e exatamente a fragilidade que
#: a escolha por regex assume: e a razao de a (d) existir.
NOME = re.compile(r'rf"(?:\(\?:)?\|?((?:[a-z0-9_]+\|)*[a-z0-9_]+)\)?"')
ABERTURA = 'python\\s+scripts/'

#: EXCLUSAO POR CLASSE, com motivo. Ver o cabecalho: nao e o glob que exclui.
CLASSES_FORA: dict[str, str] = {
    "*.sh": "ha um unico, `start_checkpoint_audit.sh`, e a exclusao e "
    "ESTRUTURAL: ele ABRE a sessao do auditor, entao roda-lo de dentro dela "
    "seria recursao. `.sh` novo cai nesta classe e precisa de decisao propria",
}

#: EXCLUSAO POR NOME, com motivo. Metade dos scripts fica fora, e cada linha aqui
#: e uma decisao — nao uma omissao.
FORA: dict[str, str] = {
    "audit_report": "hook de sessao, disparado por `SubagentStop`. O auditor nao "
    "o invoca: ele roda no lado do harness, depois de o veredito sair",
    "bench_reconstruction": "exige Postgres, ESCREVE centenas de milhares de "
    "linhas e demora minutos. O item 8 da Fase 2 pede a curva com maquina, data "
    "e stack — geradas por codigo, e isso se confere por leitura",
    "check_audit_base": "exige argumentos (`--phase`, `--default`), e a forma da "
    "allowlist termina em `.py$` de proposito: admitir argumento abriria "
    "superficie de argumento. SO OS PROBES entram, e provam os oito eixos",
    "demo_fase4": "exige a stack de containers no ar. Rede e execucao de "
    "container na mao do julgador e o que a P2-19 recusou; a evidencia chega "
    "pelo `check_provas_de_container`, que le o arquivo do lancador",
    "grava_provas_de_container": "constroi imagem, sobe container e derruba "
    "stack — a P2-19 literal. O lancador o roda ANTES da sessao",
    "mede_cache_frio": "exige a stack no ar e faz vinte leituras concorrentes. O "
    "numero dele fechou a P3-2 e esta registrado com contexto",
    "prova_reinicio_de_container": "reinicia container: execucao de container na "
    "mao do julgador, pelo mesmo motivo do `demo_fase4`",
    "prova_seed_completo": "exige Postgres, escreve 3,5 M de linhas DUAS VEZES e "
    "~5 min; exige `AURORA_SEED_DATABASE_URL`, que `SAFE_ENV_PREFIX` nao admite; "
    "e o item 1 pede um NUMERO DE MAQUINA — reexecutar em outra produz outro "
    "numero e nao confirma o primeiro. Ver a §10.4 do registro da Fase 5",
    "reancorar_sessao": "ESCREVE o sentinela em `.git/`. Dar operacao de escrita "
    "ao julgador e a separacao de papeis que o auditor nao ter `Write` mantem",
    "sincroniza_escopo_de_usuario": "ESCREVE em `~/.claude/`, FORA da arvore — "
    "mesma classe do `reancorar_sessao`, e mais forte. Dar ao julgador uma "
    "operacao que reescreve o hook que o constrange e a separacao de papeis "
    "invertida. Quem o roda e o LANCADOR, antes de a sessao abrir",
    "sobe_sala": "sobe servidor HTTP em primeiro plano e nao termina. Processo "
    "de longa duracao e rede na sessao do auditor",
}


def _versionados(padrao: str) -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", padrao], capture_output=True, text=True,
        cwd=REPO_ROOT, check=True,
    )
    return [linha for linha in saida.stdout.splitlines() if linha]


def nomes_da_allowlist(fonte: str) -> set[str]:
    """Os nomes de script lidos do fonte do hook, por regex. Ver a direcao (d)."""
    inicio = fonte.find(ABERTURA)
    if inicio < 0:
        return set()
    # O bloco vai do `python scripts/` ate o fecho do grupo — a primeira linha
    # que abre outro padrao `rf"^` depois dele.
    resto = fonte[inicio:]
    fim = resto.find('rf"^', 1)
    bloco = resto[: fim if fim > 0 else len(resto)]
    lidos: set[str] = set()
    for casado in NOME.finditer(bloco):
        lidos |= {n for n in casado.group(1).split("|") if n}
    return lidos


def _matcher():
    """`ALLOWED` importado do proprio hook — a autoridade da direcao (d)."""
    spec = importlib.util.spec_from_file_location("readonly_bash_para_leitura", HOOK)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.ALLOWED


def verifica(
    scripts: list[str],
    lidos: set[str],
    liberados_pelo_matcher: set[str],
    fora: dict[str, str],
) -> list[str]:
    """As quatro direcoes. Tudo por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    # (d) PRIMEIRO: sem ela, as outras tres podem concluir sobre leitura errada.
    if not lidos:
        problemas.append(
            "a leitura da allowlist devolveu ZERO nomes. A forma do "
            f"`{HOOK.name}` mudou e o regex parou de casar — e as outras direcoes "
            "passariam por vacuidade."
        )
        return problemas
    if lidos != liberados_pelo_matcher:
        so_leitura = sorted(lidos - liberados_pelo_matcher)[:5]
        so_matcher = sorted(liberados_pelo_matcher - lidos)[:5]
        problemas.append(
            "a leitura textual DIVERGE do matcher real: so na leitura "
            f"{so_leitura}, so no matcher {so_matcher}.\n"
            "    Regex sobre codigo pode deixar de casar quando o formato muda e "
            "passar verde — extrair tres nomes de vinte passaria igual a extrair "
            "vinte. Enquanto isto nao fechar, a classificacao abaixo nao vale."
        )
        return problemas

    # (a)
    for nome in sorted(scripts):
        if nome not in liberados_pelo_matcher and nome not in fora:
            problemas.append(
                f"`scripts/{nome}.py` nao esta na allowlist do auditor e nao esta "
                "declarado fora dela.\n"
                "    Ou ele entra por nome — se o auditor precisar EXECUTA-LO para "
                "responder algo que nao se responde por leitura —, ou ganha uma "
                "linha de motivo aqui. A regra e a do proprio `readonly_bash.py`, "
                "e ela ja foi violada tres vezes."
            )

    # (b)
    for nome in sorted(fora):
        if nome not in scripts:
            problemas.append(
                f"o registro declara `{nome}` fora da allowlist, e esse script nao "
                "existe. Declaracao que sobrevive ao arquivo mente sobre uma "
                "decisao que nao tem mais objeto."
            )

    # (c)
    for nome in sorted(set(fora) & liberados_pelo_matcher):
        problemas.append(
            f"`{nome}` esta declarado FORA da allowlist e o matcher o libera. A "
            "declaracao esta sobrando e mente sobre o que acontece."
        )

    return problemas


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    scripts = [Path(c).stem for c in _versionados("scripts/*.py")]
    lidos = nomes_da_allowlist(HOOK.read_text(encoding="utf-8"))
    allowed = _matcher()
    liberados = {
        n for n in scripts
        if any(re.match(p, f"python scripts/{n}.py") for p in allowed)
    }
    # A leitura textual restrita ao universo: o hook allowlista nomes que nao
    # sao de `scripts/` em outros padroes, e compara-los aqui seria comparar
    # conjuntos de coisas diferentes.
    problemas = verifica(scripts, lidos & set(scripts), liberados, FORA)

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {len(scripts)} scripts em `scripts/`, {len(liberados)} na "
        f"allowlist e {len(FORA)} declarados fora, com motivo.\n"
        f"  Classes fora do universo: {', '.join(CLASSES_FORA)} — declaradas, e "
        "nao omitidas pelo glob.\n"
        "  A leitura textual bate com o matcher real do hook."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
