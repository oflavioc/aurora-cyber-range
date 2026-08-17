#!/usr/bin/env python3
"""O banner de `05_SECURITY_REQUIREMENTS.md` §4 esta em toda tela e em todo artefato.

POR QUE ISTO EXISTE — B1 DA PRIMEIRA AUDITORIA DA FASE 4
---------------------------------------------------------
`05` §4 exige, *"em toda tela e no rodape de todo artefato gerado"*, o texto
`AMBIENTE SIMULADO — DADOS FICTICIOS`. **A Fase 4 entregou tres telas sem ele.**

E o achado nao foi uma linha esquecida: `05` §4 **nao aparece uma vez** no
registro da fase, e **nenhum verificador cobria a secao** —
`check_security_constraints.py` declara escopo §1 e `check_synthetic_data.py`
cobre §3. A secao inteira estava fora de todo mecanismo, e por isso a ausencia
atravessou sete pecas sem nada acusar.

**Presenca de banner e propriedade do DOM, e nao de renderizacao.** Ela caiu no
limite declarado da §2.2 — *"renderizacao, contraste e legibilidade a 10 m"* —
por acidente, e nao por decisao: o que se afirma aqui e que o texto ESTA no
documento servido, o que qualquer varredura le sem navegador. O que continua sem
teste e se ele e legivel a 10 m, e isso sim e a pergunta fisica.

O TEXTO VEM DA SPEC, E NAO DE UMA COPIA AQUI
----------------------------------------------
Ele e extraido do bloco de codigo da §4. Escrever o literal neste arquivo criaria
uma segunda fonte para um texto NORMATIVO, e a que divergisse em silencio seria a
que ninguem esta olhando — a classe P3-1, que esta fase ja pagou duas vezes.

Consequencia deliberada: mudar o texto na spec **reprova** ate o cliente
acompanhar. E o que se quer — o banner e a spec, e nao a nossa lembranca dela.

O QUE A §4 ALCANCA, E QUEM E O DONO DE CADA CLASSE
----------------------------------------------------
A §4 nomeia PDF, historico, diploma, relatorio, exportacao e arquivo de
evidencia. **Esta fase produz uma unica classe: telas.** As outras nao existem
ainda, e o registro abaixo diz quem as traz — **declarado, e nao omitido**, para
que a fase que as criar nao precise redescobrir a §4:

    telas          COBERTA aqui — as tres de `01` §2, fonte e bundle
    evidencia      Fase 8 — `08_EVIDENCE_SIMULATOR.md`; §4 exige comentario na
                   PRIMEIRA LINHA, no formato do proprio arquivo
    exportacao     Fase 8 — `academus-web` completo, historico e diploma
    relatorio/AAR  Fase 9 — `range-core/aar/`

**O registro e verificado nas duas direcoes:** classe COBERTA sem alvo no disco
reprova (seria varredura vazia passando por nao ter o que olhar), e alvo no disco
sem classe declarada tambem — que e o eixo que impede a proxima fase de produzir
PDF sem passar por aqui.

Stdlib pura. Roda no job `arquitetura` sobre a fonte, e no `contratos` depois do
build com `--exige-bundle`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# `rel` E O HELPER COMPARTILHADO, e usa-lo aqui nao e estilo. `relative_to`
# LEVANTA fora da raiz, e os probes apontam os alvos para um diretorio
# temporario justamente para exercitar o caminho de REPROVACAO — entao a
# mensagem de erro estourava antes de ser impressa.
#
# **E a terceira vez que esta linhagem paga por isso**: a peca 6 achou o mesmo
# defeito em `check_web_sem_derivacao._exibe`, e `check_telas_sem_vocabulario`
# nasceu com a guarda. Escrevi este verificador sem reusar o helper e reintroduzi
# o defeito — falha de instrumento no caminho de reprovacao so aparece quando o
# verificador esta certo, e ate la o probe nao consegue afirmar nada.
from _common import rel  # noqa: E402

RULE = "05 §4 — banner de simulacao em toda tela e em todo artefato gerado"

SPEC = REPO_ROOT / "docs" / "spec" / "05_SECURITY_REQUIREMENTS.md"
WEB = REPO_ROOT / "range-core" / "web"
BUNDLE = WEB / "dist"
FONTE_DO_BANNER = WEB / "src" / "banner.tsx"

#: As tres telas de `01` §2. Sao as MESMAS que `range_core.api.app` serve.
TELAS = ("wallboard-shell", "participant-view", "gm-console")

#: O componente que cada tela tem de renderizar. Varredura lexica, com o mesmo
#: limite declarado que `01` §2 admite para TypeScript.
COMPONENTE = "BannerDeSimulacao"

#: `classe -> (coberta_aqui, dono)`. Ver o cabecalho.
CLASSES_DA_SECAO_4 = {
    "telas": (True, "esta fase — `01` §2"),
    "evidencia": (False, "Fase 8 — `08_EVIDENCE_SIMULATOR.md`, comentario na primeira linha"),
    "exportacao": (False, "Fase 8 — `academus-web`: historico, diploma, PDF"),
    "relatorio": (False, "Fase 9 — `range-core/aar/`"),
}

_BLOCO = re.compile(r"^## 4\..*?```\s*\n(.*?)\n```", re.S | re.M)


def texto_normativo(spec: Path | None = None) -> str:
    """O banner, extraido do bloco de codigo da §4. Fonte unica.

    `spec=None` resolve o GLOBAL na chamada, e nao no `def`. A primeira versao
    tinha `spec: Path = SPEC` como default, e um default de funcao e avaliado uma
    vez, na definicao: o probe que aponta `SPEC` para uma spec sem bloco nao
    mudava nada, e a checagem seguia lendo a spec real. **Falha de instrumento no
    caminho de anti-vacuidade** — e ela foi pega pelo proprio probe, que reprovou
    por nao conseguir provocar o `rc=2` que exigia.
    """
    achado = _BLOCO.search((SPEC if spec is None else spec).read_text(encoding="utf-8"))
    return achado.group(1).strip() if achado else ""


def _alvos_de_fonte() -> list[Path]:
    return [WEB / tela / "main.tsx" for tela in TELAS]


def _alvos_de_bundle() -> list[Path]:
    return [BUNDLE / tela / "index.html" for tela in TELAS]


def verifica(banner: str, fonte_do_banner: Path, telas: list[Path], bundles: list[Path]) -> list[str]:
    """Os tres eixos. Tudo por parametro, para o probe injetar."""
    problemas: list[str] = []

    if not fonte_do_banner.is_file():
        problemas.append(
            f"{fonte_do_banner} nao existe: o componente do banner e a UNICA "
            "copia do texto normativo no cliente."
        )
    elif banner not in fonte_do_banner.read_text(encoding="utf-8"):
        problemas.append(
            f"{fonte_do_banner.name} nao contem o texto normativo `{banner}`.\n"
            "    Ele e extraido de `05` §4 e comparado LETRA POR LETRA: se a spec "
            "mudou, o cliente acompanha; se o cliente mudou, ele esta errado."
        )

    for caminho in telas:
        if not caminho.is_file():
            problemas.append(f"{caminho} nao existe: tela declarada e ausente do disco.")
        elif COMPONENTE not in caminho.read_text(encoding="utf-8"):
            problemas.append(
                f"{rel(caminho)} nao renderiza "
                f"`{COMPONENTE}`.\n"
                "    `05` §4 diz TODA tela, sem excecao para tela pequena — e o "
                "custo no orcamento do telao esta declarado na D16."
            )

    for caminho in bundles:
        if not caminho.is_file():
            problemas.append(
                f"{caminho} nao existe, e `--exige-bundle` foi pedido: o artefato "
                "servido ao navegador nao foi construido."
            )
        elif banner not in caminho.read_text(encoding="utf-8"):
            problemas.append(
                f"{rel(caminho)} nao carrega o banner.\n"
                "    A fonte pode te-lo e o BUNDLE nao — e o bundle e o que vai ao "
                "navegador. Presenca no DOM e a propriedade; renderizacao e outra."
            )

    return problemas


def _registro_coerente() -> list[str]:
    """As duas direcoes do registro de classes. Ver o cabecalho."""
    problemas: list[str] = []
    cobertas = [c for c, (coberta, _) in CLASSES_DA_SECAO_4.items() if coberta]
    if not cobertas:
        problemas.append(
            "nenhuma classe da §4 esta marcada como coberta: a checagem passaria "
            "por nao ter o que olhar."
        )
    if "telas" in cobertas and not any(c.is_file() for c in _alvos_de_fonte()):
        problemas.append(
            "a classe `telas` esta COBERTA e nao ha nenhuma tela no disco."
        )
    return problemas


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    exige_bundle = "--exige-bundle" in argumentos

    banner = texto_normativo()
    if not banner:
        print(
            f"{RULE}: nao consegui extrair o texto da §4 de "
            f"{rel(SPEC)}. A secao mudou de forma, ou "
            "a varredura deixou de enxergar o bloco — e um banner vazio faria "
            "TODOS os eixos passarem.",
            file=sys.stderr,
        )
        return 2

    problemas = _registro_coerente()
    problemas += verifica(
        banner,
        FONTE_DO_BANNER,
        _alvos_de_fonte(),
        _alvos_de_bundle() if exige_bundle else [],
    )

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    adiadas = [
        f"{classe} ({dono})"
        for classe, (coberta, dono) in sorted(CLASSES_DA_SECAO_4.items())
        if not coberta
    ]
    print(
        f"{RULE}: `{banner}` em {len(TELAS)} telas"
        + (f" e em {len(TELAS)} bundles" if exige_bundle else " (fonte)")
        + f". Classes ainda sem artefato, com dono: {'; '.join(adiadas)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
