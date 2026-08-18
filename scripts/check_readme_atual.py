#!/usr/bin/env python3
"""O README e o BRIEFING nao podem afirmar estado que a arvore contradiz.

POR QUE ISTO EXISTE
-------------------
O README envelheceu DUAS VEZES no mesmo ponto. A frase "Fase 0 em fechamento"
sobreviveu as Fases 1 e 2, e `docs/BRIEFING.md` carregava a mesma frase, pela
mesma causa. As duas vezes foram pegas por LEITURA — alguem abriu o arquivo e
notou. Detecção por memoria nao e detecção, e a terceira ocorrencia so nao veio
porque alguem olhou de novo.

Nao houve descuido em momento nenhum: a frase era verdadeira quando nasceu e
ficou falsa quando OUTRO arquivo mudou. E a classe da secao 1.6 do registro da
Fase 1, e o antidoto dela ja existe neste repositorio —
`check_progress_consistency.py` nasceu do mesmo diagnostico e diz o motivo com
todas as letras: *"a regra sozinha nao segurou a propriedade"*.

Redacao nova nao impede a terceira vez. Isto impede.

O QUE ELE CRUZA
---------------
Cada predicado abaixo le uma AFIRMACAO do documento e a compara com uma FONTE
computada da arvore. A fonte e sempre o repositorio; o documento nunca e fonte
de si mesmo.

    ultima-fase-concluida  <- docs/progress/fase_<n>.md com status de conclusao
    proximo-checkpoint     <- a fase seguinte a ultima concluida
    total-de-fases         <- linhas da tabela de visao geral do `07`
    testes                 <- unittest.TestLoader().discover(), SEM executar
    comando-dos-testes     <- o mesmo comando que o job `contratos` roda
    spec-changes           <- git log spec-v1.0..HEAD
    relatorios-*           <- docs/progress/audit_*.md e o veredito de cada um
    verificadores-*        <- tools/*.py e scripts/check_*.py
    excecao-sem-probe      <- os verificadores de scripts/ sem `_probes.py`
    caminhos               <- git ls-files

AS TRES DECISOES DE DESENHO, E SAO ELAS QUE FAZEM ISTO SER GATE
----------------------------------------------------------------
**1. NAO ENCONTRADO REPROVA.** Se a expressao que ancora um predicado nao casa
com nada no documento, isto sai != 0. Reformular a frase e "sumir" com o
predicado e o modo de falha obvio de um verificador de prosa — e aqui ele fica
vermelho, em vez de degradar para "ok". Nao saber e exatamente o caso em que nao
se pode afirmar, e essa degradacao ja custou tres predicados a esta linhagem.

**2. PROVA NEGATIVA PAREADA, NAS DUAS DIRECOES.**
`check_readme_atual_probes.py` planta numero errado no documento e exige
reprovacao, E exige que o documento correto passe. Sem a segunda direcao nasce o
guarda que bloqueia tudo e passa no teste que so mede bloqueio.

**3. O QUE NAO E VERIFICAVEL FICA DECLARADO AQUI**, em `NAO_VERIFICAVEL`. A
ausencia de predicado passa a ser decisao escrita, e nao omissao. E a P4-12
aplicada antes de virar pendencia: tres secoes de `05` ficaram sem verificador e
sem NADA declarando que a ausencia era deliberada, que e o estado em que um
requisito morre sem que nada fique vermelho.

ONDE ELE RODA, E POR QUE NAO E NO `arquitetura`
------------------------------------------------
Roda no job `contratos`. O predicado dos testes conta por
`unittest.TestLoader().discover()`, que IMPORTA os modulos de teste — e eles
importam `range_core`. O `arquitetura` deliberadamente nao instala a aplicacao
("um gate que depende da aplicacao que ele julga deixa de ser gate",
`docs/process/WORKFLOW.md`), entao o predicado falharia la por ambiente, e nao
por defeito.

Isso nao enfraquece este gate como enfraqueceria os invariantes: eles existem
para ser independentes da aplicacao; este julga PROSA contra a arvore, e nao
perde sentido por rodar onde o pacote esta instalado. `contratos` e context
obrigatorio na branch protection, entao ele bloqueia merge. Job novo NAO e
opcao — context exigido antes de existir em `main` trava todo PR que nao o
produza, e foi a P1-18.

O QUE ELE NAO E
---------------
Nao julga se o texto esta BOM, nem se a descricao esta completa. Julga se os
numeros e os nomes que o texto afirma continuam sendo os da arvore. Documento
bem escrito e errado passa nos predicados que nao o tocam — e por isso a lista
de `NAO_VERIFICAVEL` importa tanto quanto a de predicados.

Stdlib pura, exceto `git`.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS = REPO_ROOT / "docs" / "progress"

RULE = "README e BRIEFING conferidos contra a arvore"

#: O comando que o job `contratos` roda, e que o README cita ao lado do numero.
#: Numero sem o comando que o produziu nao e medicao — e lembranca.
COMANDO_DOS_TESTES = "python -m unittest discover -s tests"

#: A tag do congelamento. `06_ACCEPTANCE_TESTS.md` e `WORKFLOW.md` a citam.
TAG_DO_FREEZE = "spec-v1.0"


# ---------------------------------------------------------------------------
# O QUE ESTE VERIFICADOR NAO ALCANCA — declarado, e nao omitido.
# ---------------------------------------------------------------------------
#: Cada entrada e uma afirmacao que os documentos fazem e que NENHUM predicado
#: confere. Estar aqui e decisao registrada; nao estar em lugar nenhum seria o
#: buraco que a P4-12 nomeia.
NAO_VERIFICAVEL: dict[str, str] = {
    "posicionamento e a secao do problema": "juizo sobre o mercado de tabletop "
    "exercises. Nao ha fonte na arvore contra a qual cruzar, e inventar uma "
    "seria pior que declarar o limite",
    "os numeros da UniAurora": "28.000 alunos, 1.200 professores, 5 campi sao "
    "dados de CENARIO, fixados em 00_MASTER_SPEC.md secao 1. Sao spec, e a spec "
    "ja tem gate proprio (`spec_freeze`) — cruzar aqui duplicaria autoridade",
    "a coluna `Estado` da tabela de componentes": "implementado / parcial / "
    "planejado e JUIZO sobre maturidade. O predicado `caminhos` prova que o "
    "diretorio citado existe; que ele esteja vazio ou completo nao e decidivel "
    "por contagem de arquivo sem inventar limiar",
    "a fase de destino de cada item planejado": "'planejado, Fase 6' e leitura "
    "do `07`, e casar prosa com a tabela de fases exigiria decidir o que uma "
    "frase em portugues afirma. Mesmo argumento que manteve a regra das "
    "citacoes `Fase <n>` fora de verificador, na D7 da Fase 4",
    "a latencia de 47 ms e o orcamento de 1 s": "medicao de uma execucao do "
    "DEMO, registrada em docs/progress/fase_4.md. Reproduzi-la aqui exigiria "
    "subir a stack — o que este gate nao faz, e o passo de CI do DEMO ja faz",
    "os 73 testes que pulam sem Postgres": "depende do ambiente, por desenho. O "
    "numero TOTAL e conferido; quantos pulam varia com o que esta no ar, e "
    "fixar isso aqui produziria falso bloqueio na maquina de quem tem a stack",
    "a fronteira publico/privado de cenarios": "descreve intencao sobre "
    "artefatos que ainda nao existem — `scenarios/` esta vazio. Vira "
    "verificavel no commit em que o primeiro pack nascer, e nao antes",
    "o quick start": "a sequencia de comandos e executada pelos passos de CI do "
    "DEMO e do build, e nao reexecutada aqui. O que este verificador confere "
    "dela e o que ela NOMEIA — caminhos e o comando dos testes",
    "o numero de rodadas de auditoria da Fase 0": "o README dizia 'dezesseis "
    "rodadas, dez reprovaram'. Contado na fonte em 17/08/2026, "
    "docs/progress/fase_0.md tem cabecalho da PRIMEIRA a DECIMA OITAVA "
    "auditoria, com 13 vereditos FAIL por cabecalho e a quinta ambigua "
    "('apenas um achado transmitido'). Os dois numeros do README divergiam da "
    "fonte, e por isso SAIRAM em vez de serem corrigidos: as seis primeiras "
    "rodadas sao anteriores ao mecanismo que persiste relatorio (P11) e nao tem "
    "arquivo proprio, entao 'rodadas' nao e contavel pela arvore. O que ficou "
    "no lugar e contavel: RELATORIOS versionados, e o veredito de cada um",
}


# ---------------------------------------------------------------------------
# FONTES — computadas da arvore, nunca do documento.
# ---------------------------------------------------------------------------

#: `**Status: CONCLUIDA ...` ou `**Status: AUDITADA — PASS ...`, no cabecalho.
STATUS_CONCLUIDO = re.compile(
    r"^\*\*Status:\s*(?:CONCLU[IÍ]DA|AUDITADA\s*[—\-]\s*PASS)", re.M
)
#: Qualquer linha de status no cabecalho, concluida ou nao.
STATUS_QUALQUER = re.compile(r"^\*\*Status:", re.M)

#: Quantas linhas do topo contam como "cabecalho" do registro de fase. Os
#: registros trazem `**Status: FECHADA ...` de PENDENCIA la embaixo, e uma
#: dessas linhas lida como status de fase inverteria o resultado.
CABECALHO = 80

VEREDITO_DO_RELATORIO = re.compile(r"^-\s*veredito detectado:\s*\*\*(\w+)\*\*", re.M)
FASE_DO_RELATORIO = re.compile(r"^-\s*fase:\s*\*\*(\d+)\*\*", re.M)


def _tolera_terminal_estreito() -> None:
    """A licao da secao 8.4 da Fase 4, aplicada antes de custar uma rodada.

    Os documentos sao em portugues, e as mensagens deste verificador citam o
    trecho que divergiu — com acento, travessao e aspa curva. Num terminal em
    `cp1252` isso sai como `UnicodeEncodeError` e rc=1 SOBRE DIVERGENCIA
    LEGITIMA, e um verificador que morre nao diz "reprovou": ele nao diz nada.

    Perder um glifo e o custo; perder a saida inteira nao se compara.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    ).stdout


def _fases_concluidas() -> list[int]:
    concluidas = []
    for caminho in sorted(PROGRESS.glob("fase_*.md")):
        casado = re.fullmatch(r"fase_(\d+)\.md", caminho.name)
        if casado is None:
            continue
        cabeca = "\n".join(
            caminho.read_text(encoding="utf-8").splitlines()[:CABECALHO]
        )
        if STATUS_CONCLUIDO.search(cabeca):
            concluidas.append(int(casado.group(1)))
    return sorted(concluidas)


def _status_da_proxima(proxima: int) -> str | None:
    """A guarda contra o envelhecimento SILENCIOSO deste proprio predicado.

    `_fases_concluidas` reconhece duas formas de status, porque os registros
    usam duas — `fase_2.md` diz CONCLUIDA e `fase_3.md` diz AUDITADA — PASS. Se
    a Fase 5 fechar numa TERCEIRA forma, a fonte continuaria dizendo 4, o
    documento continuaria dizendo 4, e os dois concordariam sobre um fato falso.

    Entao: se o registro da proxima fase existir e nao tiver linha de status
    nenhuma no cabecalho, isto reprova pedindo a forma — em vez de concluir.
    """
    caminho = PROGRESS / f"fase_{proxima}.md"
    if not caminho.exists():
        return None
    cabeca = "\n".join(caminho.read_text(encoding="utf-8").splitlines()[:CABECALHO])
    if STATUS_QUALQUER.search(cabeca):
        return None
    return (
        f"docs/progress/fase_{proxima}.md existe e NAO tem linha `**Status:` nas "
        f"primeiras {CABECALHO} linhas. Este verificador decide 'a fase fechou?' "
        "por essa linha, e sem ela ele nao consegue ver o fechamento — os "
        "documentos continuariam afirmando a fase anterior e nada ficaria "
        "vermelho. Escreva a linha de status no cabecalho do registro."
    )


def _total_de_fases() -> int:
    texto = (REPO_ROOT / "docs" / "spec" / "07_IMPLEMENTATION_PHASES.md").read_text(
        encoding="utf-8"
    )
    casado = re.search(r"##\s+Vis[ãa]o geral(.*?)^---", texto, re.S | re.M)
    if casado is None:
        raise SystemExit(
            f"{RULE}: nao achei a tabela de visao geral em "
            "07_IMPLEMENTATION_PHASES.md. A forma do documento mudou, e este "
            "predicado precisa acompanhar."
        )
    return len(re.findall(r"^\|\s*(\d+)\s*\|", casado.group(1), re.M))


def _testes() -> tuple[int, list]:
    """Conta por descoberta, SEM executar. Nao precisa de Postgres nem Docker.

    E a mesma descoberta que `python -m unittest discover -s tests` faz — o
    comando que o job roda e que o documento cita —, e por isso o numero e o
    mesmo que aparece em `Ran N tests`, pulos incluidos.
    """
    carregador = unittest.TestLoader()
    suite = carregador.discover(start_dir=str(REPO_ROOT / "tests"))

    def conta(no) -> int:
        if isinstance(no, unittest.TestSuite):
            return sum(conta(filho) for filho in no)
        return 1 if isinstance(no, unittest.TestCase) else 0

    return conta(suite), list(carregador.errors)


def _spec_changes() -> int:
    linhas = _git("log", "--format=%s", f"{TAG_DO_FREEZE}..HEAD").splitlines()
    return sum(1 for linha in linhas if linha.startswith("spec-change:"))


def _relatorios() -> dict[str, int]:
    total = fase0 = fase0_fail = 0
    for caminho in sorted(PROGRESS.glob("audit_*.md")):
        total += 1
        texto = caminho.read_text(encoding="utf-8")
        fase = FASE_DO_RELATORIO.search(texto)
        veredito = VEREDITO_DO_RELATORIO.search(texto)
        if fase is not None and fase.group(1) == "0":
            fase0 += 1
            if veredito is not None and veredito.group(1).upper() == "FAIL":
                fase0_fail += 1
    return {"total": total, "fase0": fase0, "fase0_fail": fase0_fail}


def _verificadores() -> dict[str, object]:
    ferramentas = sorted(
        p.name
        for p in (REPO_ROOT / "tools").glob("*.py")
        if not p.name.startswith("_")
    )
    principais = sorted(
        p.name
        for p in (REPO_ROOT / "scripts").glob("check_*.py")
        if not p.name.endswith("_probes.py")
    )
    sem_probe = [
        nome
        for nome in principais
        if not (REPO_ROOT / "scripts" / f"{nome[:-3]}_probes.py").exists()
    ]
    return {
        "tools": len(ferramentas),
        "scripts": len(principais),
        "com_probe": len(principais) - len(sem_probe),
        "sem_probe": sem_probe,
    }


def fontes() -> dict[str, object]:
    """Tudo o que a arvore diz, num dicionario — para os probes poderem injetar."""
    concluidas = _fases_concluidas()
    if not concluidas:
        raise SystemExit(
            f"{RULE}: nenhum registro de fase declara conclusao. A forma da linha "
            "de status mudou, e este verificador nao consegue mais decidir qual "
            "fase fechou."
        )
    ultima = max(concluidas)
    quantidade, erros_de_carga = _testes()
    relatorios = _relatorios()
    verificadores = _verificadores()
    return {
        "ultima_fase_concluida": ultima,
        "proximo_checkpoint": ultima + 1,
        "aviso_da_proxima": _status_da_proxima(ultima + 1),
        "total_de_fases": _total_de_fases(),
        "testes": quantidade,
        "erros_de_carga": erros_de_carga,
        "spec_changes": _spec_changes(),
        "relatorios": relatorios["total"],
        "relatorios_fase0": relatorios["fase0"],
        "relatorios_fase0_fail": relatorios["fase0_fail"],
        "verificadores_tools": verificadores["tools"],
        "verificadores_scripts": verificadores["scripts"],
        "verificadores_com_probe": verificadores["com_probe"],
        "verificadores_sem_probe": verificadores["sem_probe"],
        "caminhos_versionados": sorted(_git("ls-files").splitlines()),
    }


# ---------------------------------------------------------------------------
# PREDICADOS — `(fonte, arquivo, expressao)`. A expressao tem UM grupo, e todos
# os casamentos dela precisam bater com a fonte. Zero casamento REPROVA.
# ---------------------------------------------------------------------------
PREDICADOS: list[tuple[str, str, str]] = [
    ("ultima_fase_concluida", "README.md", r"Fases 0 a (\d+) conclu"),
    ("ultima_fase_concluida", "docs/BRIEFING.md", r"Fases 0 a (\d+) conclu"),
    ("ultima_fase_concluida", "docs/BRIEFING.md", r"planejadas, (\d+) conclu"),
    ("proximo_checkpoint", "README.md", r"Pr[óo]ximo checkpoint: \*\*Fase (\d+)"),
    ("proximo_checkpoint", "docs/BRIEFING.md", r"Pr[óo]ximo checkpoint: \*{0,2}Fase (\d+)"),
    ("total_de_fases", "README.md", r"(\d+) fases"),
    ("total_de_fases", "docs/BRIEFING.md", r"(\d+) fases planejadas"),
    ("testes", "README.md", r"\*\*(\d+) testes\*\*"),
    ("testes", "README.md", r"dos (\d+) testes pulam"),
    ("spec_changes", "README.md", r"mudou \*\*(\d+) vezes\*\*"),
    ("relatorios", "README.md", r"\*\*(\d+) relat[óo]rios\*\* de auditoria"),
    ("relatorios_fase0", "docs/BRIEFING.md", r"por (\d+) relat[óo]rios de auditoria"),
    ("relatorios_fase0_fail", "docs/BRIEFING.md", r"e (\d+) deles reprovaram"),
    ("verificadores_tools", "README.md", r"S[ãa]o \*\*(\d+)\*\* verificadores"),
    ("verificadores_tools", "docs/BRIEFING.md", r"(\d+) verificadores autom[áa]ticos"),
    ("verificadores_scripts", "README.md", r"e \*\*(\d+)\*\* em \[`scripts/`\]"),
    ("verificadores_com_probe", "README.md", r"e \*\*(\d+)\*\* destes [úu]ltimos"),
]

#: A tag do freeze precisa ser citada pelo nome e existir de fato.
CITA_A_TAG = ("README.md", r"`(spec-v1\.0)`")

#: O comando dos testes, citado ao lado do numero.
CITA_O_COMANDO = ("README.md", r"`(python -m unittest discover -s tests)`")

#: A excecao sem prova negativa e NOMEADA no documento, e o nome tem de ser
#: exatamente o conjunto que a arvore produz. Se alguem acrescentar um segundo
#: verificador sem probe, o conjunto diverge e isto reprova — que e o ponto:
#: a lista nao pode virar esconderijo.
CITA_A_EXCECAO = ("README.md", r"A exce[çc][ãa]o [ée] `([a-z0-9_]+\.py)`")


# ---------------------------------------------------------------------------
# CAMINHOS
# ---------------------------------------------------------------------------
RAIZES = (
    "contracts",
    "range-core",
    "domains",
    "scenarios",
    "scripts",
    "tools",
    "tests",
    "alembic",
    "docs",
    "user-scope",
)
#: Tres formas, e a terceira e a arvore de diretorios do README: `caminho`,
#: `](caminho)` e caminho no INICIO da linha. Sem a terceira, o bloco que
#: desenha a estrutura do repositorio ficaria fora da conferencia — e ele e
#: justamente o lugar onde um diretorio renomeado passa despercebido.
CAMINHO = re.compile(
    r"(?:^|`|\]\()((?:" + "|".join(re.escape(r) for r in RAIZES) + r")/[^`\s)\]]*)",
    re.M,
)

#: Caminhos que os documentos citam de proposito SEM que a arvore os contenha.
#: Cada um com o motivo, na forma da whitelist declarada de
#: `check_gate_coverage.py`: o custo de acrescentar aqui e uma conversa.
CAMINHOS_DECLARADOS: dict[str, str] = {
    "scenarios/": "diretorio VAZIO. `git` nao versiona diretorio vazio, entao "
    "ele nao existe num clone limpo — e e exatamente isso que o README afirma "
    "sobre ele. O primeiro pack e da Fase 7",
    "range-core/web/dist/": "artefato de build, no .gitignore. O README o cita "
    "para dizer que ele NAO e versionado e que o build e obrigatorio",
    "scenarios/**/evidence/": "padrao do .gitignore citado como padrao, e nao "
    "como caminho existente",
}


def _caminhos_do_documento(texto: str) -> set[str]:
    return set(CAMINHO.findall(texto))


def _existe(caminho: str, versionados: list[str]) -> bool:
    alvo = caminho.rstrip("/")
    return any(v == alvo or v.startswith(alvo + "/") for v in versionados)


# ---------------------------------------------------------------------------
# A VERIFICACAO
# ---------------------------------------------------------------------------
def verifica(docs: dict[str, str], f: dict[str, object]) -> list[str]:
    """Recebe os documentos e as fontes para os probes poderem injetar os dois."""
    problemas: list[str] = []

    if f.get("erros_de_carga"):
        problemas.append(
            "a descoberta de testes acusou erro de carga: "
            f"{[str(e[0]) for e in f['erros_de_carga']][:3]}. A contagem nao vale "
            "enquanto isso nao fechar — modulo que nao importa vira um caso de "
            "falha e mantem o total parecido com o certo."
        )

    if f.get("aviso_da_proxima"):
        problemas.append(str(f["aviso_da_proxima"]))

    for fonte, arquivo, expressao in PREDICADOS:
        texto = docs.get(arquivo)
        if texto is None:
            problemas.append(f"{arquivo}: documento ausente.")
            continue

        casados = re.findall(expressao, texto)
        if not casados:
            problemas.append(
                f"{arquivo}: nada casou com /{expressao}/, que ancora o predicado "
                f"`{fonte}`.\n    NAO ENCONTRADO REPROVA: a afirmacao pode ter "
                "sido reescrita, e um predicado que nao acha o que confere deixa "
                "de conferir em silencio. Reancore a expressao ou remova o "
                "predicado por decisao."
            )
            continue

        esperado = str(f[fonte])
        divergentes = sorted({c for c in casados if c != esperado})
        if divergentes:
            problemas.append(
                f"{arquivo}: `{fonte}` afirma {divergentes} e a arvore diz "
                f"{esperado!r}."
            )

    for rotulo, (arquivo, expressao), esperado in (
        ("a tag do freeze", CITA_A_TAG, TAG_DO_FREEZE),
        ("o comando dos testes", CITA_O_COMANDO, COMANDO_DOS_TESTES),
    ):
        casados = re.findall(expressao, docs.get(arquivo, ""))
        if not casados:
            problemas.append(
                f"{arquivo}: {rotulo} nao aparece. O documento afirma um numero "
                "sem dizer o que o produziu, e numero sem procedencia nao e "
                "medicao."
            )
        elif any(c != esperado for c in casados):
            problemas.append(f"{arquivo}: {rotulo} diverge de {esperado!r}.")

    arquivo, expressao = CITA_A_EXCECAO
    nomeados = set(re.findall(expressao, docs.get(arquivo, "")))
    sem_probe = set(f["verificadores_sem_probe"])  # type: ignore[arg-type]
    if nomeados != sem_probe:
        problemas.append(
            f"{arquivo}: os verificadores sem prova negativa sao {sorted(sem_probe)} "
            f"e o documento nomeia {sorted(nomeados)}.\n    A lista existe para "
            "nao virar esconderijo: verificador novo sem `_probes.py` tem de "
            "aparecer no texto, ou ganhar a prova negativa."
        )

    versionados = f["caminhos_versionados"]  # type: ignore[assignment]
    for nome, texto in docs.items():
        for caminho in sorted(_caminhos_do_documento(texto)):
            if caminho in CAMINHOS_DECLARADOS:
                continue
            if not _existe(caminho, versionados):  # type: ignore[arg-type]
                problemas.append(
                    f"{nome}: cita `{caminho}`, que a arvore nao contem. "
                    "Ou o caminho mudou de nome, ou ele nunca existiu — e "
                    "caminho errado num README e a forma mais barata de fazer "
                    "alguem desistir."
                )

    return problemas


def main() -> int:
    _tolera_terminal_estreito()
    docs = {}
    for nome in ("README.md", "docs/BRIEFING.md"):
        caminho = REPO_ROOT / nome
        if caminho.exists():
            docs[nome] = caminho.read_text(encoding="utf-8")

    f = fontes()
    problemas = verifica(docs, f)

    print(f"{RULE}")
    print(f"  ultima fase concluida: {f['ultima_fase_concluida']}")
    print(f"  proximo checkpoint:    {f['proximo_checkpoint']}")
    print(f"  fases no roadmap:      {f['total_de_fases']}")
    print(f"  testes descobertos:    {f['testes']}")
    print(f"  spec-changes:          {f['spec_changes']}")
    print(f"  relatorios:            {f['relatorios']}")
    print(
        f"  verificadores:         {f['verificadores_tools']} em tools/, "
        f"{f['verificadores_scripts']} em scripts/ "
        f"({f['verificadores_com_probe']} com prova negativa)"
    )
    print(f"  nao verificavel:       {len(NAO_VERIFICAVEL)} itens declarados")

    if problemas:
        print(f"\nFALHAS: {len(problemas)}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(f"\n{len(PREDICADOS)} predicados conferem, e os caminhos citados existem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
