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

    telas          COBERTA aqui — as tres de `01` §2 MAIS as tres da Fase 8
                   (`exam-mode`, `investigation-console`, `persona-panel`),
                   fonte e bundle. As telas academus-web JA EXISTEM e portanto
                   deixaram de ser deferidas: sao tela, e §4 nao abre excecao.
    evidencia      Fase 9 — `08_EVIDENCE_SIMULATOR.md`; §4 exige comentario na
                   PRIMEIRA LINHA, no formato do proprio arquivo
    exportacao     Fase 8/9 — os ARTEFATOS gerados por academus-web (historico,
                   diploma, PDF) ainda nao existem; a §4 pede banner no RODAPE
                   deles, o que e outra classe que a das telas que os produzem
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

#: Toda tela do range. As tres primeiras sao de `01` §2 — as MESMAS que
#: `range_core.api.app` serve. As tres seguintes sao as telas da Fase 8 (`07`
#: Fase 8), listadas em `range-core/web/vite.config.ts`: `exam-mode` e
#: `investigation-console` (`02` §7) e o `persona-panel` (dashboards por
#: persona). Sao autenticadas/casca, nao projecao publica sem token — mas `05`
#: §4 diz TODA tela, sem essa distincao: casca tambem e tela servida.
TELAS = (
    "wallboard-shell",
    "participant-view",
    "gm-console",
    "exam-mode",
    "investigation-console",
    "persona-panel",
)

#: O componente que cada tela tem de renderizar. Varredura lexica, com o mesmo
#: limite declarado que `01` §2 admite para TypeScript.
COMPONENTE = "BannerDeSimulacao"

#: `classe -> (coberta_aqui, dono)`. Ver o cabecalho.
CLASSES_DA_SECAO_4 = {
    "telas": (True, "`01` §2 + Fase 8 (`07`): exam-mode, investigation-console, persona-panel"),
    # COBERTA DESDE A FASE 9, e a mudanca de `False` para `True` e o M1 daquela
    # auditoria: a classe seguia declarada como PENDENTE com dono "Fase 9"
    # depois de a Fase 9 a entregar — o registro mentia sobre o estado da arvore,
    # e por construcao nao podia ficar vermelho quando o banner regredisse.
    #
    # O que a torna coberta NAO e a declaracao: e a varredura de
    # `ARQUIVOS_DE_EVIDENCIA` abaixo, sobre o `evidence/` versionado do pack de
    # exemplo.
    "evidencia": (True, "Fase 9: `range-core/evidence/banner.py`, primeira linha de cada arquivo"),
    "exportacao": (False, "a fase que construir os artefatos de `academus-web`: historico, diploma, PDF (P8-2)"),
    # O DONO ESTAVA ERRADO, e o M1 o pegou de raspao: `range-core/aar/` e
    # entregavel da FASE 10 (`07` §Fase 10 — "o AAR tem as doze secoes de `03`
    # §9"), nunca da 9. A Fase 9 nao produz relatorio.
    "relatorio": (False, "Fase 10 — `range-core/aar/`, o AAR de `03` §9"),
}

#: Os arquivos de evidencia VERSIONADOS — o objeto da classe `evidencia`.
#:
#: `scenarios/**/evidence/` fica fora do Git por decisao da Fase 5, entao o
#: unico objeto versionado e o do pack de EXEMPLO SANITIZADO, que e a isencao
#: declarada de `check_gabarito_fora_do_git`. Ele existe desde a Fase 9 e e o
#: mesmo objeto sobre o qual o CI roda `range-cli evidence verify`.
#:
#: DIRETORIO VAZIO OU AUSENTE NAO E "PASSOU": ver `verifica`.
EVIDENCIA_DO_EXEMPLO = REPO_ROOT / "tests" / "fixtures" / "pack_exemplo" / "evidence"

#: NAO HA ISENCAO — B1 da quarta auditoria.
#:
#: Havia: `SEM_BANNER = {"MANIFEST.json"}`, com a justificativa de que `05` §4
#: pede o banner *"como comentario na primeira linha, no formato do proprio
#: arquivo"* e que um JSON de indice **nao teria onde po-lo** sem deixar de
#: validar contra `evidence.schema.yaml` (`additionalProperties: false`).
#:
#: A justificativa era verdadeira quando foi escrita e o contrato a desmentiu no
#: L2 da terceira auditoria: `_banner` virou `required` na raiz do manifesto. A
#: isencao sobreviveu a norma que a sustentava — e foi ela que deixou o
#: `MANIFEST.json` versionado sem banner passar por este verificador enquanto o
#: `evidence verify` do CI reprovava.
#:
#: **A LICAO E SOBRE A FORMA DA ISENCAO, e nao sobre esta em particular.** Uma
#: excecao declarada por NOME DE ARQUIVO nao tem como envelhecer alto: ela nao
#: cita o que a justifica, entao nada fica vermelho quando aquilo muda. O que
#: substituiu foi uma regra por FORMATO — cada formato diz onde o banner mora, e
#: formato desconhecido e recusa (`_banner_de`).
#:
#: O QUE `05` §4 QUER, E ELE NAO FALA DE LINHA POR ACIDENTE: o aviso tem de ser
#: o primeiro que quem abre o arquivo le. Em JSON isso e a primeira CHAVE, e nao
#: a primeira linha — que e `{`. As duas leituras servem a mesma norma.
_PRIMEIRA_CHAVE_JSON = "_banner"

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


def _banner_de(caminho: Path, banner: str) -> list[str]:
    """Os problemas de banner deste arquivo, por FORMATO — ver `_PRIMEIRA_CHAVE_JSON`.

    DOIS FORMATOS, E A DISTINCAO E DE ONDE O AVISO MORA:

        `.json`   documento unico. O aviso e a PRIMEIRA CHAVE, porque a primeira
                  linha e `{` e ninguem le `{` como aviso
        o resto   `.log`, `.eml`, `.jsonl` — a PRIMEIRA LINHA, que e o que `05`
                  §4 escreve literalmente

    `.jsonl` cai no segundo caso de proposito: cada linha e um documento, e a
    primeira linha e o registro de banner inteiro (`banner.linha("jsonl", ...)`).

    FORMATO DESCONHECIDO NAO PASSA. Um `.pdf` ou um `.zip` aqui e artefato que
    este verificador nao sabe julgar, e nao sabe julgar e diferente de aprovar —
    e a forma que substituiu a isencao por nome de arquivo.
    """
    if caminho.suffix == ".json":
        import json

        try:
            documento = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as erro:
            return [f"{rel(caminho)} nao e JSON legivel: {erro}"]
        if not isinstance(documento, dict):
            return [
                f"{rel(caminho)} e JSON que nao e objeto — nao ha chave onde por "
                f"o banner de `05` §4"
            ]
        chaves = list(documento)
        if documento.get(_PRIMEIRA_CHAVE_JSON) != banner:
            return [
                f"{rel(caminho)} nao traz o banner em `{_PRIMEIRA_CHAVE_JSON}`.\n"
                f"    Valor: {documento.get(_PRIMEIRA_CHAVE_JSON)!r}\n"
                "    `05` §4 exige o aviso em todo artefato gerado, e "
                "`contracts/evidence.schema.yaml` o declara `required` na raiz "
                "do manifesto desde o L2 da 3a auditoria da Fase 9."
            ]
        if chaves[0] != _PRIMEIRA_CHAVE_JSON:
            return [
                f"{rel(caminho)} tem o banner, e nao na PRIMEIRA chave "
                f"(primeira: {chaves[0]!r}).\n"
                "    `05` §4 quer o aviso onde quem abre o arquivo o le antes "
                "de qualquer outra coisa; em JSON isso e a primeira chave."
            ]
        return []

    if caminho.suffix in (".log", ".eml", ".jsonl"):
        primeira = caminho.read_text(encoding="utf-8").split("\n", 1)[0]
        if banner not in primeira:
            return [
                f"{rel(caminho)} nao traz o banner na PRIMEIRA linha.\n"
                f"    Primeira linha: {primeira[:80]!r}\n"
                "    `05` §4 exige o banner como comentario na primeira linha, "
                "no formato do proprio arquivo — no rodape ele nao avisa quem "
                "abre o log e le as primeiras linhas."
            ]
        return []

    return [
        f"{rel(caminho)}: formato {caminho.suffix or '(sem extensao)'!r} sem "
        f"forma de banner declarada neste verificador.\n"
        "    Nao saber julgar e diferente de aprovar — foi uma isencao por NOME "
        "DE ARQUIVO que deixou o `MANIFEST.json` sem banner atravessar este "
        "verificador (B1 da 4a auditoria). Declare a forma do formato novo."
    ]


def _alvos_de_fonte() -> list[Path]:
    return [WEB / tela / "main.tsx" for tela in TELAS]


def _alvos_de_bundle() -> list[Path]:
    return [BUNDLE / tela / "index.html" for tela in TELAS]


#: O contrato que carrega o banner dos ARQUIVOS de evidencia — a segunda fonte
#: viva do mesmo texto normativo, nascida na Fase 9.
CONTRATO_DE_EVIDENCIA = REPO_ROOT / "contracts" / "evidence.schema.yaml"

_BANNER_DO_CONTRATO = re.compile(r"^\s*banner_text:\s*'([^']*)'", re.M)


def texto_do_contrato(contrato: Path | None = None) -> str | None:
    """O `banner_text` de `contracts/evidence.schema.yaml`, ou `None`.

    `None` quando o contrato nao existe ou nao declara a chave — e quem chama
    decide, porque as duas coisas sao problemas diferentes.

    LEITURA LEXICA, e nao parse de YAML: este verificador e stdlib pura e roda
    no job `seguranca`, que NAO instala a aplicacao (decisao registrada em
    `design-decisions.md` — gate que depende da aplicacao que julga deixa de ser
    gate). `parse_yaml` de `tools/` resolveria, mas a chave e uma linha de
    string simples e a regex a alcanca sem trazer dependencia.

    `spec=None` pelo mesmo motivo de `texto_normativo`: default de funcao e
    avaliado na definicao, e o probe precisa injetar.
    """
    alvo = CONTRATO_DE_EVIDENCIA if contrato is None else contrato
    if not alvo.is_file():
        return None
    achado = _BANNER_DO_CONTRATO.search(alvo.read_text(encoding="utf-8"))
    return achado.group(1) if achado else None


def verifica(
    banner: str,
    fonte_do_banner: Path,
    telas: list[Path],
    bundles: list[Path],
    contrato: Path | None = None,
    evidencia: Path | None = None,
) -> list[str]:
    """Os tres eixos, mais o cruzamento com o contrato de evidencia.

    Tudo por parametro, para o probe injetar.
    """
    problemas: list[str] = []

    # ------------------------------------------------------------------
    # O QUARTO EIXO — `05` §4 x `contracts/evidence.schema.yaml`.
    #
    # H2 da auditoria da Fase 9. Ate ela, o texto do banner tinha UMA fonte
    # normativa (`05` §4) e um consumidor conferido (o componente das telas).
    # A Fase 9 criou a SEGUNDA fonte viva: `banner_text` no contrato de
    # evidencia, que e o que `range-core/evidence/banner.py` le para carimbar
    # TODO arquivo entregue ao time azul.
    #
    # E NADA CRUZAVA AS DUAS. O teste que parecia fechar isso era tautologico —
    # comparava `banner.texto(CONTRATOS)` com o proprio valor do contrato, que e
    # o que aquela funcao devolve. Ele provava que o produtor nao reescreve; nao
    # provava que o valor e o de `05` §4.
    #
    # Consequencia medida: editar `banner_text` mudava o banner de toda a
    # evidencia, a suite seguia verde (1082/1082) e este verificador tambem,
    # porque so olhava telas. E a P1-13 pela porta que a Fase 9 abriu — e o
    # cabecalho de `banner.py` invoca justamente a P1-13 como razao para ler do
    # contrato em vez de copiar.
    # ------------------------------------------------------------------
    alvo_do_contrato = CONTRATO_DE_EVIDENCIA if contrato is None else contrato
    do_contrato = texto_do_contrato(alvo_do_contrato)
    if do_contrato is None:
        problemas.append(
            f"{alvo_do_contrato} nao declara "
            "`x-aurora-security-constraints.banner_text`. Ele e a fonte que "
            "`range-core/evidence/banner.py` le para carimbar todo arquivo de "
            "evidencia — sem ela, o motor nao tem texto e o banner de `05` §4 "
            "deixa de existir no artefato gerado."
        )
    elif do_contrato != banner:
        problemas.append(
            f"o banner do contrato de evidencia diverge de `05` §4:\n"
            f"    `05` §4:   {banner!r}\n"
            f"    contrato:  {do_contrato!r}\n"
            "    Sao duas fontes VIVAS do mesmo texto normativo — a spec manda "
            "nas telas, o contrato manda nos ARQUIVOS de evidencia. Divergindo, "
            "o participante ve um banner na tela e outro no log, e nenhum teste "
            "da suite acusa."
        )

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

    # ------------------------------------------------------------------
    # A CLASSE `evidencia` — `05` §4: *"nos arquivos de evidencia, como
    # comentario na PRIMEIRA LINHA, no formato do proprio arquivo"*.
    #
    # DIRETORIO AUSENTE OU VAZIO REPROVA, e isto e o ponto: a classe esta
    # marcada COBERTA no registro, e cobertura sem objeto e a forma exata do
    # SKIP SILENCIOSO que a R10 §2 chama de FAIL. Se o `evidence/` do pack de
    # exemplo sumir, este verificador tem de ficar vermelho — e nao passar por
    # nao ter o que olhar.
    #
    # A POSICAO E O REQUISITO, e nao a presenca: banner no rodape nao avisa
    # quem abre o arquivo e le as primeiras linhas, que e o que alguem faz com
    # um log de 40 mil registros.
    # ------------------------------------------------------------------
    alvo_de_evidencia = EVIDENCIA_DO_EXEMPLO if evidencia is None else evidencia
    if CLASSES_DA_SECAO_4["evidencia"][0]:
        arquivos = (
            sorted(p for p in alvo_de_evidencia.iterdir() if p.is_file())
            if alvo_de_evidencia.is_dir()
            else []
        )
        candidatos = list(arquivos)
        if not candidatos:
            problemas.append(
                f"a classe `evidencia` esta COBERTA e nao ha arquivo de evidencia "
                f"em {rel(alvo_de_evidencia)}.\n"
                "    Cobertura sem objeto e skip silencioso: o verificador "
                "passaria por nao ter o que olhar. Rode "
                "`range-cli evidence build tests/fixtures/pack_exemplo --seed <n>`."
            )
        for caminho in candidatos:
            problemas.extend(_banner_de(caminho, banner))

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
