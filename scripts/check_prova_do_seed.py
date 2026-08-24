#!/usr/bin/env python3
"""M2 — a prova do seed completo e DESTA ARVORE, e ela existe.

O QUE ESTA CHECAGEM FECHA
--------------------------
Os itens 1 e 2 da DoD da Fase 5 sao NUMEROS DE MAQUINA: `< 5 min` e "dataset
byte-identico". O auditor nao pode reexecutar — o script exige Postgres, escreve
3,5 milhoes de linhas duas vezes e leva minutos, e reexecuta-lo em outra maquina
produziria OUTRO numero, que nao confirma o primeiro. A exclusao dele da
allowlist e decisao registrada, pelo mesmo criterio do `bench_reconstruction`.

**O que faltava nao era o auditor rodar: era a gravacao existir.** Ate aqui o
numero vivia so no registro da fase, e o registro trazia DOIS — 159,4 s e
144,3 s, de antes e depois do embaralhamento — sem nada dizendo a que objeto
cada um pertencia. Numero de desempenho sem o objeto que ele mediu fica ambiguo
assim que o conteudo anda uma vez, e ele andou.

E A MESMA FORMA DO `check_provas_de_container.py`, e pelo mesmo argumento da
P4-10: o que exige rede e volume acontece FORA da sessao do julgador, e o
resultado chega pronto — amarrado ao objeto por hash. Isso nao faz o auditor ver
a execucao; amarra a evidencia ao conteudo medido, que e a diferenca entre
"alguem rodou" e "rodou nisto".

AS SEIS DIRECOES, e a primeira e a que nao pode degradar
----------------------------------------------------------
    (a) o arquivo NAO EXISTE                                    -> REPROVA
    (b) a `tree` gravada diverge da arvore do `HEAD` daqui       -> REPROVA
    (c) o arquivo esta VERSIONADO                                -> REPROVA
    (d) falta maquina, data, python ou o numero de linhas        -> REPROVA
    (e) a prova gravada diz que um dos dois itens FALHOU         -> REPROVA
    (f) o arquivo nao declara o esquema que este verificador le  -> REPROVA

A **(a)** e a que este verificador existe para nao degradar: "nao ha prova" e
exatamente o caso em que nao se pode afirmar o item. Os dois predicados de base
aposentados da Fase 3 degradaram para "ok" quando nao sabiam, e cada um custou
uma auditoria que parecia gate.

A **(c)** e o espelho: o arquivo carrega o hash da arvore que ele mede, e **um
arquivo versionado nao contem o hash da arvore que o contem** — rastrea-lo muda
a arvore que ele teria de declarar. Versiona-lo tornaria a amarracao circular.

A **(d)** e `06` T3 virando predicado: numero de desempenho sem maquina, data e
stack envelhece sem que ninguem perceba.

A **(f)** NASCEU COM A P7-2, e nao e formalidade. O campo obrigatorio deixou de
ser `commit` e passou a ser `tree`. Sem um esquema declarado, um artefato do
formato anterior cairia na (b) como *"gravada sobre `None`"* — reprovaria, certo,
mas dizendo que o gravador falhou quando o fato e que o formato mudou. E o
lancador COPIA este artefato entre arvores (o transporte da H1), entao encontrar
um arquivo velho nao e hipotese.

ARVORE, E NAO COMMIT — P7-2
-----------------------------
Ate a P7-2 o campo era o SHA do commit, e **todo fechamento de fase o
invalidava**: `WORKFLOW.md` fixa rebase, nunca squash, e rebase reescreve SHA por
definicao. O que ele preserva e a arvore — medido em tres merges, tres pares,
nenhuma diferenca. A prova passa a nomear o que mediu, e nao onde aquilo estava.

Isso APAGA um laco que era proprio deste script: medir, registrar o numero e
commitar invalidava a propria medicao, porque commitar mudava o SHA. Com a prova
nomeando arvore, commitar so a invalida se algum arquivo RASTREADO mudar — e ai
ela deve mesmo ser invalidada, porque o objeto medido mudou.

O que a arvore NAO cobre, declarado: so o conteudo rastreado. Aqui isso quase nao
morde — o seed sai de `RANDOM_SEED` e do codigo, ambos rastreados —, e o caso
geral esta aberto como P7-3.

Stdlib pura. NAO roda no job `arquitetura` — ver o rodape.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCIA = ".aurora-prova-do-seed.json"

#: O ESQUEMA, criado na P7-2 — este artefato nao tinha nenhum, e o gemeo de
#: container tinha desde a origem. A assimetria so era invisivel porque nada
#: nunca mudara de formato; a P7-2 mudou, e ela apareceu.
#:
#: A DECLARACAO E UNICA, e `prova_seed_completo.py` a IMPORTA daqui — §1.4 do
#: checkpoint da Fase 2, a mesma razao pela qual o gravador de container importa
#: a lista `PROVAS` do seu verificador. Duas constantes sobre a mesma fronteira
#: divergem, e a que diverge em silencio e sempre a que ninguem esta olhando.
ESQUEMA = "aurora.prova-do-seed/1"

RULE = "M2 - a prova do seed completo e desta arvore"

#: `06` T3: maquina, data e stack AO LADO do numero, e nao em outro lugar.
CONTEXTO = ("maquina", "python", "data", "seed", "linhas")
ITENS = ("item_1_seed_em_menos_de_5_min", "item_2_byte_identico")


def _arvore(raiz: Path) -> str | None:
    """O hash da ARVORE do `HEAD`, e nao o SHA do commit — P7-2.

    `HEAD^{tree}` resolve o commit e devolve a arvore que ele aponta: o que o
    rebase preserva. Nao le o indice nem o diretorio de trabalho — a evidencia e
    ignorada pelo git, entao ela nao entra no hash que declara, e a amarracao nao
    e circular.

    DEGRADA PARA `None`, ao contrario do `_arvore` do gravador de container, que
    usa `check=True`. A assimetria e deliberada: la o worktree e criado pelo
    lancador a partir de um commit e nao resolver arvore significa pressuposto
    errado do chamador; aqui o verificador pode legitimamente rodar onde `HEAD`
    nao resolve, e `None` E a informacao que a `avalia` julga.
    """
    r = subprocess.run(
        ["git", "-C", str(raiz), "rev-parse", "--verify", "--quiet", "HEAD^{tree}"],
        capture_output=True, text=True, check=False,
    )
    arvore = r.stdout.strip()
    return arvore if len(arvore) == 40 else None


def _versionado(raiz: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(raiz), "ls-files", "--error-unmatch", EVIDENCIA],
        capture_output=True, text=True, check=False,
    )
    return r.returncode == 0


def avalia(doc: dict | None, arvore: str | None, versionado: bool) -> list[str]:
    """As seis direcoes. Por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    if versionado:
        problemas.append(
            f"`{EVIDENCIA}` esta VERSIONADO. Ele carrega o hash da arvore que "
            "mede, e um arquivo versionado nao contem o hash da arvore que o "
            "contem — rastrea-lo muda a arvore que ele teria de declarar. A "
            "amarracao vira circular e a evidencia deixa de dizer alguma coisa."
        )

    if doc is None:
        problemas.append(
            f"`{EVIDENCIA}` nao existe ou nao e JSON legivel. Os itens 1 e 2 da "
            "DoD ficam sem prova, e ISTO NAO DEGRADA PARA OK: nao ter a medicao e "
            "o caso em que nao se pode afirmar o item.\n"
            "    Rode, na maquina que vai medir:\n"
            "      AURORA_SEED_DATABASE_URL=... RANDOM_SEED=... \\\n"
            "          python scripts/prova_seed_completo.py"
        )
        return problemas

    # (f) O ESQUEMA VEM ANTES DE TUDO QUE LE CAMPO, e a ordem e a propriedade:
    # depois daqui os nomes de campo sao confiaveis. Um artefato do formato
    # anterior a P7-2 tem `commit` e nao tem `tree`, e sem este eixo ele
    # reprovaria pela (b) dizendo `None` — mensagem que culpa o gravador por uma
    # mudanca de formato.
    if doc.get("esquema") != ESQUEMA:
        declarado = doc.get("esquema")
        antigo = (
            " Este arquivo e do formato ANTERIOR a P7-2 — ele amarra a medicao ao"
            " SHA do COMMIT, que todo `gh pr merge --rebase` invalidava. Meca de"
            " novo neste checkout: o formato novo amarra a ARVORE, e a arvore"
            " atravessa o rebase."
            if declarado is None and "commit" in doc
            else ""
        )
        problemas.append(
            f"`{EVIDENCIA}` nao declara o esquema `{ESQUEMA}` (declara "
            f"{declarado!r}). Ou o arquivo nao e o que este verificador julga, ou "
            f"o formato mudou sem que a checagem acompanhasse.{antigo}"
        )
        return problemas

    if arvore is None:
        problemas.append(
            "este checkout nao resolve a arvore de um `HEAD` de git: sem o hash "
            "da arvore nao ha contra o que amarrar a evidencia."
        )
    elif doc.get("tree") != arvore:
        problemas.append(
            f"a prova foi gravada sobre a arvore `{doc.get('tree')}` e este "
            f"checkout e `{arvore}`. Ela mede OUTRO conteudo — e o numero de "
            "outro conteudo nao afirma nada sobre este. Algum arquivo RASTREADO "
            "mudou entre a medicao e agora; rebase e mudanca de mensagem de "
            "commit nao chegam aqui, porque nao mexem na arvore. Meca de novo."
        )

    for campo in CONTEXTO:
        if not doc.get(campo):
            problemas.append(
                f"a prova nao traz `{campo}`. `06` T3 exige maquina, data e stack "
                "ao lado do numero: sem o contexto, o numero envelhece sem que "
                "ninguem perceba."
            )

    for item in ITENS:
        if doc.get(item) is not True:
            problemas.append(
                f"a prova gravada diz que `{item}` NAO passou "
                f"({doc.get(item)!r}). O arquivo e escrito mesmo quando a medicao "
                "falha, de proposito: e assim que 'falhou' se distingue de "
                "'ninguem rodou'."
            )

    return problemas


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    caminho = REPO_ROOT / EVIDENCIA
    try:
        doc = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = None

    problemas = avalia(doc, _arvore(REPO_ROOT), _versionado(REPO_ROOT))

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    # A SAIDA INTEGRA, e nao "ok": aprovar em silencio trocaria um NAO VERIFICADO
    # por "confie na minha checagem" — a mesma exigencia que a P4-10 fez ao (c).
    print(f"{RULE}: prova da arvore `{doc['tree'][:12]}`, e este checkout e a mesma.")
    print(f"  maquina  {doc['maquina']}  ·  python {doc['python']}")
    print(f"  data     {doc['data']}  ·  seed {doc['seed']}")
    print(f"  linhas   {doc['linhas']:,}")
    print(
        f"  item 1   {doc['segundos'][0]:.1f} s e {doc['segundos'][1]:.1f} s, "
        f"orcamento {doc['orcamento_s']:.0f} s"
    )
    print(f"  item 2   {len(doc['digests'])} tabelas com SHA-256 igual nas duas")
    print(f"  audit_trail  {doc['digests']['audit_trail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
