#!/usr/bin/env python3
"""`05_SECURITY_REQUIREMENTS.md` secao 6 — o gabarito nao entra no repositorio.

O QUE ESTA CHECAGEM EXECUTA
----------------------------
A decisao do operador na peca 5 da Fase 5: `scenarios/` fica FORA do Git. Este
repositorio e publico, e `ground_truth.yaml` e `GM_NOTES.md` sao o gabarito —
quem os le antes da sala sabe quais casos sao indevidos.

**`.gitignore` e convencao, e `git add -f` a atravessa.** Um `git add -A` num
diretorio que alguem designorou localmente faz o mesmo sem intencao nenhuma.
Convencao nao reprova PR; isto reprova.

AS CINCO DIRECOES
------------------
    (a) `ground_truth.yaml` ou `GM_NOTES.md` VERSIONADO, em qualquer lugar
        da arvore                                                  -> REPROVA
    (b) a entrada de `scenarios/` sumiu do `.gitignore`, ou perdeu
        o motivo escrito                                           -> REPROVA
    (c) identificador com forma de GABARITO dentro do TEMPLATE ou dos
        MODULOS versionados do gerador                             -> REPROVA
    (d) o template perdeu placeholder que o gerador substitui —
        prosa que deveria ser concreta virou texto fixo            -> REPROVA
    (e) documento versionado AFIRMANDO que o gabarito e versionado
        (a linha "repositorio privado" que sobreviveu)             -> REPROVA

A (e) EXISTE PORQUE A MESMA AFIRMACAO FALSA JA APARECEU EM QUATRO LUGARES
--------------------------------------------------------------------------
`CLAUDE.md` foi corrigida em `3dd9d18` — de "repositorio privado" para "este
repositorio e publico". A mesma afirmacao vivia em mais TRES lugares, e ficou:

    .gitignore                          "intentionally versioned in this
                                         private repository"
    .claude/agents/scenario-designer.md  duas vezes, e esta INSTRUIA o subagente
                                         a versionar o gabarito
    docs/process/WORKFLOW.md             "sao versionados no repositorio privado"

E a classe do E1 — escalar sem varrer onde mais a exigencia vive. Varredura
manual acha a segunda ocorrencia; **nao impede a terceira**, e aqui ja houve
quatro. Isto impede.

E ELA CUSTOU DUAS VOLTAS, as duas do mesmo padrao: a regra reprovou contra o
texto CORRIGIDO — *"nao e versionado"* contem *"e versionado"* —, e depois contra
o proprio arquivo de prova, que precisa PLANTAR a afirmacao para testa-la. As
correcoes sao as de sempre: filtrar a negacao pela estrutura, e autoexcluir-se.

O CRITERIO E ESTREITO DE PROPOSITO: casa a AFIRMACAO de que os dois arquivos sao
versionados, e nao a palavra "privado". Documento que discute a decisao — o
registro de fase, a citacao historica no `.gitignore` — precisa poder citar a
frase antiga, e por isso ha allowlist declarada.

A (c) E A QUE FECHA O BURACO QUE A (a) NAO VE
-----------------------------------------------
O template E versionado, de proposito: a prosa dele reafirma `02` §6.1 e §6.2, e
a spec e publica. Mas e ali que o gabarito vazaria sem que nada visse — basta
alguem escrever "a conta e a U-P-0000" no meio de uma frase, e o arquivo continua
sendo "so o template".

O linter de T8 nao pega isso: ele confere que todo fato do `GM_NOTES` existe no
`ground_truth.yaml`, e um `case_id` escrito a mao no template EXISTE la. A
direcao que falta e esta.

O QUE ELE NAO PROVA, E O LIMITE E O MESMO DA D10.3
----------------------------------------------------
Ele julga a ARVORE. O artefato gerado com o `RANDOM_SEED` de producao — o que vai
para a sala — nunca e visto por CI nenhum, e nao precisa ser: a propriedade
provada e do GERADOR, e ela independe do valor do seed. Afirmar mais que isso
seria atestacao.

O que fica sem cobertura, dito em vez de suposto: nada impede alguem de publicar
o artefato renderizado FORA do Git — por e-mail, por anexo, por captura de tela.
Isso e disciplina de operacao, e nao propriedade de repositorio.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"
SEED = REPO_ROOT / "domains" / "academus" / "seed"
TEMPLATE = SEED / "GM_NOTES.template.md"

#: OS MODULOS VERSIONADOS DO GERADOR entram na varredura da direcao (c), e a
#: razao foi medida: `linha_b.py` nasceu com `CONTA_DOS_INDEVIDOS = "U-P-0000"`,
#: e essa linha entregava metade do gabarito a quem lesse o repositorio publico.
#: O template nao era o unico lugar por onde o concreto vazava.
MODULOS = ("linha_b.py", "dataset.py", "gabarito.py", "carga.py")

RULE = "05 secao 6 - gabarito fora do repositorio"

#: Os dois nomes de `05` secao 6 e de `CLAUDE.md`. Casados por NOME DE ARQUIVO
#: inteiro: `contracts/ground_truth.schema.yaml` e o schema, tem outro nome, e
#: continua versionado como deve.
PROIBIDOS = ("ground_truth.yaml", "GM_NOTES.md")

#: A entrada que executa a decisao, e a exigencia de que ela venha com motivo.
ENTRADA = "scenarios/"
MOTIVO_MINIMO = 400

#: A FORMA DE UM IDENTIFICADOR DE GABARITO. Os que o gerador produz:
#:
#:   GC-0001      caso da Linha B          U-P-0000     conta docente
#:   GT-LINHAB-1  fato do ground truth     A-000123     matricula
#:   AUT-AMB-000  autorizacao              PR-DEL-000   numero de processo
#:   DEL-000      delegacao                g-ind-000    objeto da trilha
IDENTIFICADORES = re.compile(
    r"\b(?:GC-[0-9]+|GT-[A-Z0-9]+-[0-9]+|U-P-[0-9]+|A-[0-9]{4,}"
    r"|AUT-[A-Z]+-[0-9]+|PR-[A-Z]+-[0-9]+|DEL-[0-9]+|g-[a-z]{3}-[0-9]+)\b"
)

#: A AFIRMACAO FALSA, na forma em que ela apareceu quatro vezes: um dos dois
#: nomes seguido, de perto, de "e/sao versionado(s)" ou "is/are versioned".
#:
#: `[^.]{0,80}` e nao `.{0,80}`: sem o corte na frase, a regra casaria um nome
#: numa sentenca e "versionado" na seguinte, e reprovaria texto que diz o
#: contrario em duas frases.
AFIRMACAO_DE_VERSIONADO = re.compile(
    r"(?:ground_truth\.yaml|GM_NOTES\.md)[^.]{0,80}?"
    r"(?:sao versionados|são versionados|e versionado|é versionado"
    r"|is versioned|are versioned|intentionally versioned)",
    re.I,
)

#: ONDE A CITACAO HISTORICA E DELIBERADA, com o motivo por entrada.
#:
#: Sem esta lista, a propria correcao seria reprovada: o `.gitignore` cita a
#: frase antiga para dizer que ela era falsa, e o registro de fase e historia.
CITACAO_PERMITIDA = {
    ".gitignore": "cita a frase antiga para declarar que ela ficou falsa",
    "docs/progress/": "registro de fase e relatorio de auditoria sao historia: "
    "dizem o que aconteceu, e nao o que vale",
    "scripts/check_gabarito_fora_do_git.py": "esta checagem CITA a afirmacao "
    "para descreve-la; sem a autoexclusao, ela reprova a si mesma",
    "scripts/check_gabarito_fora_do_git_probes.py": "a prova negativa PLANTA a "
    "afirmacao — e o material dela. Foi a SEXTA vez nesta fase que o texto que "
    "fala sobre a regra caiu nela, e a autoexclusao e a mesma que "
    "`check_secoes_de_seguranca.py` precisou pelo mesmo motivo",
}

#: Os placeholders que o gerador substitui. Se um sumir do template, o numero
#: correspondente virou texto fixo — e texto fixo envelhece na primeira mudanca
#: de escala, dizendo 22 quando o dataset tem outro numero.
PLACEHOLDERS = (
    "{{PACK}}", "{{SEED_ORIGEM}}", "{{N_INDEVIDOS}}", "{{N_AMBIGUOS}}",
    "{{N_SUSPEITOS}}", "{{N_RUIDO}}", "{{N_DELEGADAS}}", "{{N_NORMAIS}}",
    "{{QUERY_INDEVIDOS}}", "{{QUERY_AMBIGUOS}}", "{{TABELA_DE_CASOS}}",
)


def _versionados() -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
    )
    return [linha for linha in saida.stdout.splitlines() if linha]


def verifica(
    versionados: list[str],
    gitignore: str,
    fontes: dict[str, str],
    documentos: dict[str, str] | None = None,
) -> list[str]:
    """As cinco direcoes. Tudo por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    # (a)
    for caminho in versionados:
        if Path(caminho).name in PROIBIDOS:
            problemas.append(
                f"{caminho} esta VERSIONADO. `05` secao 6 e `CLAUDE.md` poem "
                "`ground_truth.yaml` e `GM_NOTES.md` fora do repositorio publico: "
                "eles sao o gabarito, e quem os le antes da sala sabe quais casos "
                "sao indevidos.\n"
                "    Se veio por `git add -f`, desfaca com `git rm --cached`. Se "
                "a decisao mudou, ela e do operador e muda no `.gitignore` e aqui "
                "— nao em silencio."
            )

    # (b)
    linhas = gitignore.splitlines()
    if not any(linha.strip() == ENTRADA for linha in linhas):
        problemas.append(
            f"o `.gitignore` nao tem a entrada `{ENTRADA}`. E ela que executa a "
            "decisao da D10; sem ela, o proximo `git add -A` versiona o gabarito "
            "e so esta checagem acusa — depois de o dano ja estar no historico."
        )
    else:
        indice = next(i for i, l in enumerate(linhas) if l.strip() == ENTRADA)
        comentario = []
        for anterior in reversed(linhas[:indice]):
            if anterior.startswith("#"):
                comentario.append(anterior)
            elif anterior.strip() == "":
                continue
            else:
                break
        if len("\n".join(comentario)) < MOTIVO_MINIMO:
            problemas.append(
                f"a entrada `{ENTRADA}` do `.gitignore` esta sem motivo escrito ao "
                "lado. Quem abre o `.gitignore` nao abre o registro da fase, e uma "
                "linha muda e indistinguivel de artefato de build ignorado por "
                "conveniencia. Escreva por que o diretorio sai, e o que continua "
                "versionado."
            )

    # (c) — no template E nos modulos versionados do gerador
    for nome, fonte in sorted(fontes.items()):
        achados = sorted(set(IDENTIFICADORES.findall(fonte)))
        if achados:
            problemas.append(
                f"{nome} tem identificador concreto de gabarito: {achados[:6]}. "
                "Ele e VERSIONADO num repositorio publico, e identificador escrito "
                "a mao ali e gabarito vazando por onde nenhuma outra checagem "
                "olha — o linter de T8 confere que todo fato do `GM_NOTES` existe "
                "no `ground_truth.yaml`, e um caso escrito a mao EXISTE la.\n"
                "    No template, tudo o que e concreto entra por `{{ }}`; nos "
                "modulos, por parametro derivado do `RANDOM_SEED`."
            )

    # (d)
    template = fontes[TEMPLATE.name]
    faltando = [p for p in PLACEHOLDERS if p not in template]
    if faltando:
        problemas.append(
            f"o template perdeu os placeholders {faltando}. O numero que eles "
            "trazem virou texto fixo, e texto fixo envelhece na primeira mudanca "
            "de escala — o facilitador leria 22 num dataset que tem outro numero."
        )

    # (e) — a afirmacao falsa que sobreviveu a correcao, em qualquer documento
    for caminho, texto in sorted((documentos or {}).items()):
        if any(caminho.startswith(p) for p in CITACAO_PERMITIDA):
            continue
        if casado := _afirmacao_positiva(texto):
            problemas.append(
                f"{caminho} afirma que o gabarito e versionado: "
                f"{casado.group(0)[:90]!r}.\n"
                "    `scenarios/` esta fora do Git desde a peca 5 da Fase 5. Esta "
                "mesma frase sobreviveu a correcao da `CLAUDE.md` em QUATRO "
                "lugares, e um deles instruia um subagente a versionar o "
                "gabarito — escalar sem varrer onde mais a exigencia vive e a "
                "classe do E1."
            )

    return problemas


#: As negacoes que transformam a afirmacao no seu contrario.
NEGACOES = ("nao ", "não ", "not ", "never ", "nunca ")


def _afirmacao_positiva(texto: str):
    """A afirmacao SEM negacao na janela imediatamente anterior ao verbo.

    A NEGACAO E FILTRADA EM PYTHON, e nao no regex, e a razao e mecanica: em
    Python o lookbehind e de largura fixa, e as negacoes tem larguras diferentes
    e vem cercadas de marcacao (`**nao** e versionado`). Um regex tentando cobrir
    isso vira ilegivel antes de virar correto.

    E ELA EXISTE PORQUE A REGRA REPROVOU CONTRA O PROPRIO TEXTO CORRIGIDO —
    *"`ground_truth.yaml` **nao e versionado**"* contem "e versionado". Foi a
    QUINTA vez nesta fase que o texto que fala sobre a regra caiu nela, e a
    correcao e a de sempre: a checagem olha a estrutura, e nao a substring.
    """
    for casado in AFIRMACAO_DE_VERSIONADO.finditer(texto):
        janela = texto[max(0, casado.start()) : casado.end()].lower()
        if any(n in janela for n in NEGACOES):
            continue
        return casado
    return None


def _documentos() -> dict[str, str]:
    """Os versionados em que a afirmacao caberia: markdown, YAML de agente, texto."""
    lidos = {}
    for caminho in _versionados():
        if not caminho.endswith((".md", ".yaml", ".yml", ".txt", ".py", ".sh")):
            continue
        alvo = REPO_ROOT / caminho
        try:
            lidos[caminho] = alvo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return lidos


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    fontes = {TEMPLATE.name: TEMPLATE.read_text(encoding="utf-8")}
    fontes.update({nome: (SEED / nome).read_text(encoding="utf-8") for nome in MODULOS})
    problemas = verifica(
        _versionados(),
        GITIGNORE.read_text(encoding="utf-8"),
        fontes,
        _documentos(),
    )

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: nenhum `ground_truth.yaml` nem `GM_NOTES.md` versionado; "
        f"`{ENTRADA}` no `.gitignore` com motivo; o template sem identificador "
        f"concreto e com os {len(PLACEHOLDERS)} placeholders.\n"
        "  O que isto NAO prova: o artefato gerado com o seed de PRODUCAO nunca e "
        "visto por CI nenhum. A propriedade provada e do gerador, e independe do "
        "valor do seed — afirmar mais seria atestacao."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
