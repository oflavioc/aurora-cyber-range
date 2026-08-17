#!/usr/bin/env python3
"""As provas de container rodaram, e rodaram NESTE commit? — P4-10, opcao A.

O QUE ESTE VERIFICADOR EXISTE PARA FECHAR
------------------------------------------
Os itens 1 e 4 da DoD da Fase 4 sao os dois mais caros dela:

    1  a sequencia do DEMO roda ponta a ponta sem intervencao manual
    4  reinicio do CONTAINER do engine restaura o exercicio a partir do store

Os dois exigem Docker e uma stack no ar, e `docker` esta FORA da allowlist do
auditor pelo argumento da P2-19: rede e execucao de container na mao do julgador
e superficie permanente para resolver um problema de uma vez. Na primeira
auditoria da Fase 4 os dois chegaram ao veredito como NAO VERIFICADO.

A FORMA E A MESMA QUE A P2-19 JA RESOLVEU UMA VEZ: **o que exige rede acontece
no LANCADOR, antes da sessao, e o resultado chega pronto.** O lancador sobe a
stack a partir do worktree auditado, roda as duas provas, e grava a saida
integra num arquivo. O auditor LE esse arquivo.

E POR QUE ISSO NAO E ATESTACAO
-------------------------------
Porque o arquivo carrega o **SHA do commit**, e este verificador **reprova** se
ele nao for o do checkout que o auditor esta julgando. O auditor continua nao
tendo visto a execucao — isso e verdade e esta dito —, mas a evidencia fica
**amarrada ao objeto**, que e a diferenca entre *"alguem rodou"* e *"rodou
nisto"*.

A condicao e forte por um motivo mecanico, e nao por confianca: **um commit nao
pode conter o proprio SHA.** Um arquivo de evidencia versionado JUNTO com o
codigo — a forma obvia de forjar — nao tem como carregar o hash do commit que o
contem. Por isso a checagem de SHA nao e uma formalidade: ela e o que torna a
forja impossivel, e nao apenas dificil.

A segunda condicao e mais barata e pega o caso honesto: **evidencia VERSIONADA
reprova**, sem nem olhar o SHA. Ela nao acrescenta seguranca sobre a primeira —
acrescenta diagnostico, porque o caso provavel nao e forja, e alguem commitar o
arquivo por engano e passar meses sem entender por que a evidencia envelheceu.

AUSENCIA REPROVA. NAO HA "SAI 0 POR NAO SABER"
-----------------------------------------------
Arquivo ausente, ilegivel, sem SHA, com lista de provas vazia, com uma das duas
provas faltando, ou com qualquer prova em `rc != 0`: **rc=2**, sempre.

Nao ha degradacao para "ok", e a razao e a mesma que fez `check_audit_base.py`
recusar quando nao sabe: *nao ter a evidencia* e exatamente o caso em que nao se
pode afirmar que os dois itens de DoD passam. Os dois predicados que esta
linhagem ja aposentou degradaram para "ok" quando nao sabiam, cada um a sua
maneira, e cada um custou uma auditoria que parecia gate e nao era.

Quando ele reprova por ausencia, os itens 1 e 4 voltam a ser NAO VERIFICADO — o
que e a opcao C da P4-10, e e honesto. O que ele nao faz e deixar o auditor
concluir "verde" de um silencio.

O QUE ELE NAO PROVA, DECLARADO
-------------------------------
- **O auditor nao viu rodar.** Ele le uma saida gravada por um processo que nao
  e o dele. A procedencia e melhor que a de uma frase de registro — ha SHA, ha
  saida integra, e o texto e o do proprio script —, e continua sendo leitura.
- **A saida integra e do script, e o script pode estar errado.** Isso nao muda
  aqui: `demo_fase4.py` e `prova_reinicio_de_container.py` sao codigo do commit
  auditado e o auditor pode le-los, que e o mesmo estatuto do `demo_fase2.py`
  desde a Fase 2.
- **Nada sobre o CI.** Um verde de CI e de outro commit ate que se prove o
  contrario, e foi o L1 da primeira auditoria da Fase 4.

Stdlib pura, SEM ARGUMENTO — a allowlist do auditor ancora em `.py$`, e admitir
argumento abriria superficie de argumento num script que ele executa. A raiz vem
do PROPRIO ARQUIVO, e nao do diretorio de onde ele foi chamado: o objeto da
auditoria e o checkout que contem este script, e deixar a raiz depender do `cwd`
daria ao chamador como apontar a checagem para outra arvore.

Exercido por `scripts/check_provas_de_container_probes.py` em TREZE eixos — dez
que exigem recusa e tres que exigem aprovacao.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REGRA = "P4-10 - as provas de container rodaram sobre ESTE commit"

#: O nome comeca com ponto e esta no `.gitignore`. As duas coisas sao
#: consequencia e nao desenho: o worktree de auditoria E o objeto da auditoria, e
#: um arquivo que o lancador escreve dentro dele nao pode aparecer como sujeira
#: em `git status --short`.
EVIDENCIA = ".aurora-provas-de-container.json"

ESQUEMA = "aurora.provas-de-container/1"

_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Prova:
    """Uma prova esperada, e o item de DoD que ela fecha."""

    id: str
    item: str
    comando: tuple[str, ...]


#: A LISTA DE PROVAS ESPERADAS VIVE AQUI, E O GRAVADOR A IMPORTA.
#:
#: Uma declaracao, dois consumidores — a §1.4 do checkpoint da Fase 2. Duas
#: listas sobre a mesma fronteira divergem, e a que diverge em silencio e sempre
#: a que ninguem esta olhando: um gravador com a sua propria lista poderia deixar
#: de gravar uma prova e este verificador nunca saberia que ela existia.
#:
#: E e ela que fecha a VACUIDADE. Sem a lista, um arquivo com `"provas": []`
#: passaria por nao ter o que reprovar — que e a forma exata da §7.3 do registro
#: da Fase 3: a verificacao que parece existir.
PROVAS: tuple[Prova, ...] = (
    Prova(
        "demo",
        "item 1 da DoD - a sequencia do DEMO ponta a ponta, sem intervencao manual",
        ("python", "scripts/demo_fase4.py"),
    ),
    Prova(
        "reinicio",
        "item 4 da DoD e o par de T5 - reinicio do CONTAINER do engine",
        ("python", "scripts/prova_reinicio_de_container.py"),
    ),
)


@dataclass(frozen=True, slots=True)
class Falha:
    """Uma condicao que nao vale, com o texto que o auditor precisa ler."""

    eixo: str
    texto: str


def _git(raiz: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(raiz), *args], capture_output=True, text=True, check=False
    )


def _head(raiz: Path) -> str | None:
    r = _git(raiz, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    sha = r.stdout.strip()
    return sha if _SHA.match(sha) else None


def _versionado(raiz: Path, relativo: str) -> bool:
    """O arquivo esta RASTREADO pelo git desta arvore?

    `--error-unmatch` transforma "nao rastreado" em rc != 0, que e o que
    distingue rastreado de ignorado — `git ls-files <path>` sozinho sai 0 com
    saida vazia nos dois casos, e a diferenca e justamente o que se quer medir.
    """
    return _git(raiz, "ls-files", "--error-unmatch", "--", relativo).returncode == 0


def avalia(raiz: Path) -> tuple[list[Falha], dict | None]:
    """As condicoes, na ordem em que a mensagem fica mais util.

    Devolve (falhas, documento). Lista vazia = as duas provas rodaram sobre este
    commit. O documento volta junto para que o chamador imprima a saida integra —
    o auditor precisa LER o que rodou, e nao so saber que rodou.
    """
    caminho = raiz / EVIDENCIA

    head = _head(raiz)
    if head is None:
        return [
            Falha(
                "arvore",
                f"'{raiz}' nao resolve um HEAD de git.\n"
                f"    Sem o SHA do checkout nao ha contra o que amarrar a evidencia,\n"
                f"    e amarrar a evidencia ao objeto e a unica coisa que separa\n"
                f"    esta checagem de atestacao.",
            )
        ], None

    # ------------------------------------------------------------------
    # (a) AUSENCIA. Este e o eixo que nao pode degradar para "ok".
    # ------------------------------------------------------------------
    if not caminho.is_file():
        return [
            Falha(
                "a",
                f"EVIDENCIA AUSENTE — `{EVIDENCIA}` nao existe nesta arvore.\n"
                f"    Os itens 1 e 4 da DoD ficam NAO VERIFICADO, e este verificador\n"
                f"    RECUSA em vez de sair 0: nao ter a evidencia e exatamente o caso\n"
                f"    em que nao se pode afirmar que eles passam.\n"
                f"    Quem a produz e o lancador, antes da sessao:\n"
                f"        bash scripts/start_checkpoint_audit.sh 4",
            )
        ], None

    # ------------------------------------------------------------------
    # (b) EVIDENCIA VERSIONADA. Nao reforca o eixo do SHA — diagnostica.
    # ------------------------------------------------------------------
    if _versionado(raiz, EVIDENCIA):
        return [
            Falha(
                "b",
                f"`{EVIDENCIA}` esta VERSIONADO nesta arvore.\n"
                f"    Evidencia que vem dentro do commit nao pode falar sobre ele: um\n"
                f"    commit nao contem o proprio SHA. O eixo do SHA ja reprovaria\n"
                f"    isto; este existe porque o caso provavel nao e forja, e alguem\n"
                f"    ter commitado o arquivo por engano — e esse merece a mensagem\n"
                f"    que nomeia a causa. Acrescente-o ao `.gitignore` e remova-o do\n"
                f"    indice.",
            )
        ], None

    # ------------------------------------------------------------------
    # (c) LEGIBILIDADE. Arquivo truncado e arquivo ausente pela metade.
    # ------------------------------------------------------------------
    try:
        doc = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        return [
            Falha(
                "c",
                f"`{EVIDENCIA}` nao e JSON legivel: {erro}.\n"
                f"    Tipicamente o gravador foi interrompido no meio. Rode a\n"
                f"    auditoria de novo; evidencia pela metade nao vale meia prova.",
            )
        ], None

    if not isinstance(doc, dict) or doc.get("esquema") != ESQUEMA:
        return [
            Falha(
                "c",
                f"`{EVIDENCIA}` nao declara o esquema `{ESQUEMA}`.\n"
                f"    Ou o arquivo nao e o que este verificador julga, ou o formato\n"
                f"    mudou sem que a checagem acompanhasse.",
            )
        ], None

    # ------------------------------------------------------------------
    # (d) O SHA. A condicao que separa isto de atestacao.
    # ------------------------------------------------------------------
    declarado = doc.get("commit")
    if not isinstance(declarado, str) or not _SHA.match(declarado):
        return [
            Falha(
                "d",
                f"`{EVIDENCIA}` nao carrega um `commit` valido: {declarado!r}.\n"
                f"    Sem o SHA a evidencia nao esta amarrada a objeto nenhum, e\n"
                f"    passa a ser exatamente a atestacao que a P4-10 recusou.",
            )
        ], doc

    if declarado != head:
        return [
            Falha(
                "d",
                f"a evidencia e de OUTRO COMMIT.\n"
                f"        declarado no arquivo : {declarado}\n"
                f"        checkout que se julga: {head}\n"
                f"    As provas rodaram — mas nao sobre isto. Um verde que fala de\n"
                f"    outro commit e a forma de atestacao que o L1 da primeira\n"
                f"    auditoria desta fase ja custou uma rodada.",
            )
        ], doc

    # ------------------------------------------------------------------
    # (e) COBERTURA. Cada prova esperada esta la, e passou.
    # ------------------------------------------------------------------
    falhas: list[Falha] = []
    registradas = doc.get("provas")
    if not isinstance(registradas, list):
        return [Falha("e", f"`{EVIDENCIA}` nao tem lista `provas`.")], doc

    por_id = {
        p.get("id"): p for p in registradas if isinstance(p, dict) and p.get("id")
    }
    for prova in PROVAS:
        registro = por_id.get(prova.id)
        if registro is None:
            falhas.append(
                Falha(
                    "e",
                    f"a prova `{prova.id}` NAO FOI GRAVADA.\n"
                    f"        {prova.item}\n"
                    f"    Lista vazia ou incompleta passaria por nao ter o que\n"
                    f"    reprovar, que e a verificacao que so parece existir.",
                )
            )
            continue
        rc = registro.get("rc")
        if rc != 0:
            falhas.append(
                Falha(
                    "e",
                    f"a prova `{prova.id}` REPROVOU com rc={rc!r}.\n"
                    f"        {prova.item}\n"
                    f"    A saida integra dela esta impressa abaixo.",
                )
            )
            continue
        # ------------------------------------------------------------------
        # (f) PROVA VERDE E MUDA. Achado RODANDO o gravador, e nao lendo.
        #
        # No Windows a captura de subprocesso roda em thread leitora, e uma
        # decodificacao que falha la morre na thread: `subprocess.run` devolve
        # **saida vazia com o rc do processo**. O gravador escreveria `rc: 0` e
        # `saida: ""`, este verificador aprovaria, e o auditor leria um arquivo
        # que nao mostra nada — trocando o NAO VERIFICADO por um verde pior, que
        # e o verde que parece ter evidencia.
        #
        # A causa esta corrigida no gravador (codificacao explicita nos dois
        # lados). Este eixo fica porque a CAUSA nao e o que se verifica: o que se
        # verifica e que a evidencia tem conteudo. Qualquer outra forma de perder
        # a saida — e ha mais de uma — cai aqui.
        # ------------------------------------------------------------------
        if not str(registro.get("saida") or "").strip():
            falhas.append(
                Falha(
                    "f",
                    f"a prova `{prova.id}` passou com SAIDA VAZIA.\n"
                    f"        {prova.item}\n"
                    f"    Prova verde e muda nao e evidencia: nao ha o que o auditor\n"
                    f"    leia, e ele nao viu rodar. Um `rc` sem saida e a forma de\n"
                    f"    verde que PARECE ter evidencia, que e pior que a ausencia\n"
                    f"    dela — esta reprova ao menos se anuncia.",
                )
            )

    return falhas, doc


def _imprime_saidas(doc: dict) -> None:
    """A saida integra, porque o auditor precisa LER o que rodou.

    Um verificador que so dissesse "as duas provas passaram" transferiria para
    ele proprio a leitura que o auditor tem de fazer — e a P4-10 nao troca um
    NAO VERIFICADO por um "confie na minha checagem".
    """
    stack = doc.get("stack") or {}
    if stack.get("saida"):
        print("\n--- a stack de containers, subindo -----------------------------")
        print(str(stack["saida"]).rstrip())

    for registro in doc.get("provas") or []:
        if not isinstance(registro, dict):
            continue
        rotulo = registro.get("id", "?")
        comando = " ".join(registro.get("comando") or [])
        print(f"\n--- prova `{rotulo}`  (rc={registro.get('rc')!r})  {comando}")
        print(str(registro.get("saida", "")).rstrip())


def relata(falhas: list[Falha], doc: dict | None, raiz: Path) -> int:
    if not falhas:
        assert doc is not None
        print(
            f"{REGRA}: {len(PROVAS)} provas, commit {doc['commit'][:12]}, "
            f"gravadas por {doc.get('gerado_por', '?')} em {doc.get('quando', '?')}."
        )
        for prova in PROVAS:
            print(f"  [OK] {prova.id} — {prova.item}")
        _imprime_saidas(doc)
        print(
            "\nO AUDITOR NAO VIU RODAR, e isto esta dito de proposito: a evidencia\n"
            "acima foi produzida pelo lancador, na maquina do operador. O que a\n"
            "separa de atestacao e o SHA — ela e deste commit, e nao de um anterior."
        )
        return 0

    corpo = "\n".join(f"  [{f.eixo}] {f.texto}" for f in falhas)
    print(
        f"\nERRO: as provas de container nao sustentam os itens 1 e 4 da DoD.\n\n"
        f"{corpo}\n\n"
        f"Arvore julgada: {raiz}\n\n"
        "Isto NAO degrada para 'ok'. Enquanto esta checagem reprovar, os itens 1 e\n"
        "4 da DoD sao NAO VERIFICADO — que e honesto — e nunca PASS por silencio.\n",
        file=sys.stderr,
    )
    if doc is not None:
        _imprime_saidas(doc)
    return 2


def _saida_tolerante() -> None:
    """A saida do verificador nao pode morrer no que ela imprime.

    ACHADO RODANDO, e e o par exato do defeito que o gravador teve: la a leitura
    falhava porque a codepage do locale nao DECODIFICA a saida do `docker
    compose`; aqui a impressao falhava porque ela nao a CODIFICA de volta. As
    barras de progresso do build trazem caracteres fora de `cp1252`, e o
    verificador saia com `UnicodeEncodeError` e rc=1 sobre evidencia LEGITIMA.

    Um verificador que morre nao diz "reprovou" — ele nao diz nada, e o auditor
    fica com um traceback no lugar do veredito. `errors="replace"` troca o
    caractere que o terminal nao tem por `?`; perder um glifo de barra de
    progresso e o custo, e ele nao se compara ao de perder a saida inteira.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")


def main() -> int:
    _saida_tolerante()
    # A RAIZ VEM DO PROPRIO ARQUIVO, e nao do `cwd`. O objeto da auditoria e o
    # checkout que contem este script; derivar do diretorio corrente daria ao
    # chamador como apontar a checagem para outra arvore, que e a inversao que a
    # P3-4 fechou do lado dos pacotes.
    raiz = Path(__file__).resolve().parent.parent
    falhas, doc = avalia(raiz)
    return relata(falhas, doc, raiz)


if __name__ == "__main__":
    raise SystemExit(main())
