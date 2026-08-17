#!/usr/bin/env python3
"""Nenhuma tela carrega vocabulario de mecanismo nem texto de cenario.

POR QUE ISTO EXISTE, E O QUE ELE CORRIGE
-----------------------------------------
A D19 decidiu servir a casca do `gm-console` **sem token**, e a tabela daquela
decisao afirmava que *"a casca nao carrega dado de exercicio"* com teste. **A
afirmacao estava errada.** O que `tests/test_telas.py` provava era a direcao
INVERSA — que as telas publicas nao mencionam o console —, e ninguem olhava para
nome de flag, id de inject ou texto de cenario dentro do cliente.

E o buraco tinha uma metade que nem no codigo-fonte existia:

    fonte .ts/.tsx    nome de flag JA e coberto — invariante 2,
                      `tools/check_contract_literals.py`
    bundle .html      coberto por NADA: `.html` nao esta em `WEB_SUFFIXES`
    id de inject      coberto por nada, em lugar nenhum
    texto de cenario  coberto por nada, em lugar nenhum

Casca publica que vaza vocabulario e o mesmo canal lateral que o `403 x 404` da
peca 1 da Fase 3 fechou: nao e o dado que vaza, e a EXISTENCIA dele. Um telao que
carrega `academus.grade_integrity_suspect` no HTML entrega o nome da alavanca a
quem abrir o DevTools na sala — e as tres telas sao servidas sem token ou por
casca sem token.

O QUE ELE VARRE
---------------
Todo arquivo de cliente sob `range-core/web/` — **fonte E bundle**. O bundle e o
alvo que faltava: ele e uma transformacao da fonte, mas e ELE que vai ao
navegador, e nenhum gate olhava para ele.

O VOCABULARIO SAI DAS FONTES REAIS, e nao de uma lista escrita a mao: os nomes de
flag de `domains/*/flags.yaml`, e os campos de narrativa de todo pack que o
repositorio tiver — o fixture de hoje e os packs de `scenarios/` quando a Fase 7
os trouxer. Lista escrita a mao envelhece calada; esta cresce sozinha.

AS TRES CLASSES DE TERMO, E POR QUE NAO E TUDO SUBSTRING
---------------------------------------------------------
Um bundle minificado tem ~156 kB de JavaScript de biblioteca. Procurar `"A"`
dentro dele acha alguma coisa **sempre**, e bloqueio indevido tambem e defeito —
`docs/process/WORKFLOW.md` classifica assim desde o H4 da Fase 0. Entao:

    >= 6 caracteres   substring direto. Sao especificos o bastante.
    2 a 5             so entre ASPAS (`"A01"`, `'A01'`, `` `A01` ``): um
                      vazamento real e literal de string, e `A01` solto casaria
                      com qualquer hash de asset.
    1                 IGNORADO, e a contagem e IMPRESSA. `linha: A` do fixture e
                      um caractere: vazar "A" nao conta nada a ninguem, e
                      procura-lo reprovaria tudo.

**O limite, declarado:** id curto montado por concatenacao (`"A" + "01"`) escapa
da segunda classe. E o mesmo limite de varredura lexica que `01` §2 admite para
TypeScript, e o que sustenta a propriedade nao e esta varredura — e o payload: a
narrativa chega por rota autenticada em tempo de execucao, e nao ha pack ao
alcance do build.

Stdlib pura. Roda no job `arquitetura` sobre a fonte, e no `contratos` DEPOIS do
build com `--exige-bundle`, que e onde o artefato existe.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

RULE = "as telas nao carregam vocabulario de mecanismo nem texto de cenario"

WEB = REPO_ROOT / "range-core" / "web"
BUNDLE = WEB / "dist"

EXTENSOES = (".ts", ".tsx", ".js", ".jsx", ".html", ".css")
PODADOS = ("node_modules",)

#: Os campos de narrativa e de identidade de um inject. `descricao_facilitador`
#: e `texto_para_plateia` sao os dois que `05` §8 e `06` T6 tratam como
#: sensiveis; `id`, `linha` e `titulo_operacional` sao identidade de cenario, e
#: entregam a ESTRUTURA do exercicio mesmo sem entregar o texto.
CAMPOS_DE_INJECT = (
    "id",
    "linha",
    "titulo_operacional",
    "descricao_facilitador",
    "texto_para_plateia",
)

#: Abaixo disto, so entre aspas. Ver o cabecalho.
MINIMO_PARA_SUBSTRING = 6

#: Abaixo disto, nem entre aspas — e a contagem sai impressa.
MINIMO_ABSOLUTO = 2

#: As tres telas. Um bundle que perdesse uma tela passaria por nao ter o que
#: varrer, e e por isso que `--exige-bundle` conta.
TELAS = ("wallboard-shell", "participant-view", "gm-console")


def nomes_de_flag(raiz: Path) -> set[str]:
    """Todo `name:` de todo `domains/*/flags.yaml`."""
    achados: set[str] = set()
    for caminho in sorted((raiz / "domains").glob("*/flags.yaml")):
        documento = parse_yaml(caminho) or {}
        for flag in documento.get("flags") or []:
            nome = (flag or {}).get("name")
            if isinstance(nome, str) and nome:
                achados.add(nome)
    return achados


def _packs(raiz: Path) -> list[Path]:
    """Todo diretorio com `injects.yaml` — fixture de hoje, `scenarios/` amanha.

    Descoberta, e nao lista: o pack real e entregavel da Fase 7 (D13), e uma
    lista escrita hoje nao o incluiria — e ninguem descobriria, porque a
    varredura continuaria verde.
    """
    return sorted(
        caminho.parent
        for caminho in raiz.rglob("injects.yaml")
        if not any(parte in PODADOS or parte == ".git" for parte in caminho.parts)
    )


_CAMPO = re.compile(
    r"^\s*-?\s*(" + "|".join(CAMPOS_DE_INJECT) + r"|pack_id)\s*:\s*(.*)$"
)


def _termos_do_arquivo(texto: str) -> set[str]:
    """Os valores dos campos de narrativa, por varredura de LINHA.

    POR QUE NAO `parse_yaml` — medido, e nao suposto
    -------------------------------------------------
    O analisador estrito de `tools/_common.py` levanta *"escalar multilinha nao
    suportado"* em `injects.yaml:27`, que e exatamente onde mora
    `descricao_facilitador: >-`. **Os dois campos que mais importam aqui sao
    justamente os que ele nao le**, e trocar por PyYAML poria dependencia
    instalada num gate do job `arquitetura` — a fronteira que a Fase 0 construiu.

    Entao a varredura e de linha, com a mesma declaracao de limite que
    `check_pinned_images.py` faz: ela pode capturar um valor a mais (um campo
    comentado, por exemplo), e o custo disso e uma justificativa humana. O que
    ela nao faz e PERDER um valor, que seria o falso negativo.

    O escalar dobrado entra DUAS vezes — junto e linha a linha —, porque um
    vazamento pode carregar so um pedaco do paragrafo, e a juncao com espaco nao
    reproduz toda variacao de `>-` e `|-`.
    """
    achados: set[str] = set()
    linhas = texto.splitlines()
    for numero, linha in enumerate(linhas):
        casou = _CAMPO.match(linha)
        if not casou:
            continue
        valor = casou.group(2).strip()

        if valor and valor[0] not in (">", "|"):
            achados.add(valor.strip("'\"").strip())
            continue

        # Escalar dobrado: as linhas seguintes, mais indentadas.
        recuo = len(linha) - len(linha.lstrip())
        pedacos: list[str] = []
        for seguinte in linhas[numero + 1:]:
            if not seguinte.strip():
                break
            if len(seguinte) - len(seguinte.lstrip()) <= recuo:
                break
            pedacos.append(seguinte.strip())
        achados.update(pedacos)
        if pedacos:
            achados.add(" ".join(pedacos))
    return achados


def vocabulario_de_cenario(raiz: Path) -> set[str]:
    achados: set[str] = set()
    for pack in _packs(raiz):
        for nome in ("injects.yaml", "manifest.yaml"):
            caminho = pack / nome
            if caminho.is_file():
                achados |= _termos_do_arquivo(caminho.read_text(encoding="utf-8"))
    return {termo for termo in achados if termo}


def arquivos_de_cliente(web: Path) -> list[Path]:
    """Fonte E bundle. O `dist/` entra de proposito — e o que vai ao navegador."""
    if not web.is_dir():
        return []
    return sorted(
        caminho
        for caminho in web.rglob("*")
        if caminho.is_file()
        and caminho.suffix in EXTENSOES
        and not any(parte in PODADOS for parte in caminho.parts)
    )


def _citado(termo: str) -> list[str]:
    return [f'"{termo}"', f"'{termo}'", f"`{termo}`"]


def verifica(
    arquivos: list[Path],
    vocabulario: set[str],
    raiz: Path = REPO_ROOT,
) -> list[str]:
    """Os achados. Tudo por parametro, para o probe injetar."""
    problemas: list[str] = []
    for caminho in arquivos:
        try:
            texto = caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            exibe = caminho.relative_to(raiz).as_posix()
        except ValueError:
            exibe = caminho.as_posix()

        for termo in sorted(vocabulario):
            if len(termo) < MINIMO_ABSOLUTO:
                continue
            if len(termo) >= MINIMO_PARA_SUBSTRING:
                if termo not in texto:
                    continue
                forma = "literal"
            else:
                citacoes = [c for c in _citado(termo) if c in texto]
                if not citacoes:
                    continue
                forma = f"entre aspas ({citacoes[0]})"

            problemas.append(
                f"{exibe}\n"
                f"    carrega `{termo[:60]}` {forma}.\n"
                "    As tres telas sao servidas sem token, ou por casca sem token\n"
                "    (D19). Nome de flag e vocabulario de MECANISMO; id e texto de\n"
                "    inject sao a estrutura do exercicio. O que a sala ve tem de\n"
                "    chegar pela projecao, em tempo de execucao — nao assado no\n"
                "    bundle, onde qualquer DevTools o le antes de o exercicio\n"
                "    comecar."
            )
    return problemas


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    exige_bundle = "--exige-bundle" in argumentos

    vocabulario = nomes_de_flag(REPO_ROOT) | vocabulario_de_cenario(REPO_ROOT)
    arquivos = arquivos_de_cliente(WEB)

    # ANTI-VACUIDADE, nos dois lados. Um `flags.yaml` que mudasse de lugar, ou um
    # `range-core/web/` vazio, fariam esta checagem imprimir "nenhum problema" —
    # que e a forma exata de passar verde por nao enxergar, e o que os probes da
    # peca 6 acharam no verificador vizinho.
    if not vocabulario:
        print(
            f"{RULE}: vocabulario VAZIO. `domains/*/flags.yaml` e os packs "
            "mudaram de lugar, ou o analisador deixou de le-los.",
            file=sys.stderr,
        )
        return 2
    if not arquivos:
        print(
            f"{RULE}: nenhum arquivo de cliente em range-core/web/.",
            file=sys.stderr,
        )
        return 2

    if exige_bundle:
        # No job `contratos`, DEPOIS do build. Sem esta guarda, o passo passaria
        # verde no dia em que o build parasse de produzir `dist/` — varrendo so a
        # fonte, e dizendo que varreu o artefato.
        faltando = [t for t in TELAS if not (BUNDLE / t / "index.html").is_file()]
        if faltando:
            print(
                f"{RULE}: --exige-bundle, e faltam telas construidas: "
                f"{', '.join(faltando)}.\n"
                "Este modo roda DEPOIS do passo de build; sem o artefato ele "
                "varreria so a fonte e diria que varreu o bundle.",
                file=sys.stderr,
            )
            return 2

    problemas = verifica(arquivos, vocabulario)
    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    curtos = sum(1 for t in vocabulario if len(t) < MINIMO_ABSOLUTO)
    citados = sum(1 for t in vocabulario if MINIMO_ABSOLUTO <= len(t) < MINIMO_PARA_SUBSTRING)
    do_bundle = sum(1 for c in arquivos if BUNDLE in c.parents)
    print(
        f"{RULE}: {len(arquivos)} arquivos de cliente varridos "
        f"({do_bundle} do bundle), {len(vocabulario)} termos "
        f"({citados} procurados so entre aspas, {curtos} de 1 caractere "
        "IGNORADOS por serem curtos demais para significar vazamento)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
