#!/usr/bin/env python3
"""Valida os blocos de exemplo de `docs/spec/` contra os contratos.

A CAMADA QUE FALTAVA
--------------------
A terceira auditoria da Fase 1 mediu o problema: cinco divergencias entre
contrato e spec, e a suite de exemplos encontrou ZERO delas. O motivo e
estrutural, nao circunstancial — `scripts/check_contract_examples.py` valida
cada contrato contra fixtures que vivem DENTRO do proprio contrato, escritas
pelo mesmo autor no mesmo commit. Laco fechado: prova consistencia interna e nao
tem como provar fidelidade, porque a spec nunca foi entrada dele.

Este script inverte a direcao. A spec entra na MAQUINA, e nao na cabeca de quem
escreve o contrato.

ALCANCE, DECLARADO
------------------
Pega o subconjunto EXPRESSAVEL EM EXEMPLO. Teria pego os quatro defeitos da
terceira auditoria — `evidence_release`, `reveals`, `note_to_facilitator` e o
padrao de id que recusava `A09B` — e o `simulation_epoch: minimum: 1` da
segunda. NAO pega divergencia que a spec so declara em prosa ou em tabela: o
`package_files.required` contra 04 secao 9 e o `metric_binding` contra a tabela
de 03 secao 1.3 continuam fora do alcance de qualquer verificador de exemplo.

QUEM DECLARA O QUE
------------------
O CONTRATO declara quais blocos da spec ele governa, em `x-aurora-spec-examples`.
A alternativa — mapa dentro deste script — envelheceria longe do schema; e
inferir o contrato pela forma do bloco erra em silencio.

Ancora por TEXTO DE CABECALHO, nunca por linha. Se a secao for renomeada, este
script falha alto, que e o comportamento certo: cabecalho que muda significa spec
que mudou.

BLOCO NAO REIVINDICADO REPROVA. E o eixo que a auditoria nomeou como ausente —
"existe campo da spec sem fixture nenhuma?" vira "existe bloco normativo que
nenhum contrato reivindica?". Blocos que legitimamente nao sao instancia de
contrato ficam em IGNORADOS, cada um com motivo escrito.

POR QUE OUTRO PARSER YAML
-------------------------
Este script usa `yaml.safe_load` do PyYAML, e nao
`tools/_common.py::parse_yaml`, que o resto do CI usa. NAO e inconsistencia: sao
duas fontes com regras diferentes de autoria.

  - `contracts/*.yaml` sao NOSSOS, escritos no subconjunto estrito por regra
    nossa, e lidos pelo parser da Fase 0 — que e stdlib porque o gate nao pode
    depender da aplicacao que julga.
  - `docs/spec/*.md` e escrito por humanos em YAML completo, com mapeamento em
    fluxo (`{ principal: svc_academus }`), que aquele parser recusa por
    construcao.

Aplicar o parser estrito a spec seria exigir que o documento normativo se
dobrasse a limitacao da ferramenta. `safe_load`, nunca `load`: nada em
`docs/spec/` deve poder instanciar objeto Python.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml, rel  # noqa: E402

try:
    import yaml
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover
    print(
        "ERRO: dependencias ausentes.\n"
        "      python -m pip install -e . -c constraints.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)


SPEC_DIR = REPO_ROOT / "docs" / "spec"

#: Rotulos de cerca que CARREGAM instancia de contrato.
ROTULOS_DE_INSTANCIA = ("yaml", "yml", "json")

#: Rotulos que estruturalmente NAO sao instancia: codigo e diagrama. Conjunto
#: FECHADO, e essa e a questao — rotulo novo reprova em vez de sumir. A versao
#: anterior olhava so `yaml` e `json`, entao um bloco normativo escrito com
#: outro rotulo simplesmente NAO EXISTIA para o verificador: nao virava "bloco
#: sem dono", virava nada. M2 da quarta auditoria.
ROTULOS_ESTRUTURAIS = ("python", "bash", "sh", "text", "console", "diff")
CONTRACTS_DIR = REPO_ROOT / "contracts"

#: Blocos yaml/json de `docs/spec/` que NAO sao instancia de contrato. Cada um
#: com motivo: lista de ignorados sem justificativa vira lugar onde defeito se
#: esconde.
IGNORADOS = {
    ("01_ARCHITECTURE.md", "3. Relógios", 0): {
        "motivo": "fragmento do envelope — so as marcas temporais, sem os campos obrigatorios",
    },
    ("02_DOMAIN_ACADEMUS.md", "6.2 Avaliação por calibração, não por recall", 0): {
        "motivo": "submissao de assessment: artefato de runtime da Fase 6, sem contrato",
    },
    # `03` §2.2 SAIU DAQUI na Fase 6. O motivo escrito era "chega na Fase 6", e a
    # Fase 6 chegou: `contracts/rubrics.schema.yaml` existe e REIVINDICA o bloco.
    # Ignorado com motivo que ja nao vale e ignorado sem motivo — e ninguem
    # reabre um IGNORADOS para conferir se a condicao ainda se sustenta.
    ("03_EXERCISE_DESIGN.md", "4. Ground truth, observável e reportado", 0): {
        "motivo": "information_distribution.yaml: arquivo de pack sem contrato — ver P1-20",
    },
    ("03_EXERCISE_DESIGN.md", "5.1 Submissão", 0): {
        "motivo": "submissao de assessment: artefato de runtime da Fase 6, sem contrato",
    },
    ("05_SECURITY_REQUIREMENTS.md", "3. Dados", 0): {
        "motivo": "fragmento de uma linha, ilustrando marcacao de dado sintetico",
        # `evidence` reivindica 05 secao 3 como autoridade — das FAIXAS de dado
        # sintetico, que ele guarda em x-aurora-security-constraints. Este bloco
        # nao e MANIFEST.json: e `{is_synthetic, age_range}`, marcacao de registro
        # de dominio, sem `generated_from` nem `sources`.
        "nao_e_instancia_de": "evidence",
    },
    ("09_EVENT_MODEL.md", "6. Instrumentação", 0): {
        "motivo": "observability_hooks.yaml: o event_type e guardado por "
                  "tools/check_contract_literals.py, com probe no harness",
        # `objectives` reivindica 09 secao 6 como autoridade — do BINDING
        # evento->objetivo, que e o bloco de indice 1. Este e
        # observability_hooks.yaml, arquivo de adapter: tem `hooks`, `trigger` e
        # `payload_fields`, e nenhum dos seis contratos o cobre.
        "nao_e_instancia_de": "objectives",
    },
}


def _secao_de(heading: str):
    """Numero da secao de topo a partir do cabecalho: '3.1 Predicados' -> 3."""
    m = re.match(r"^(\d+)", heading.strip())
    return int(m.group(1)) if m else None


def autoridades(contratos: dict) -> dict:
    """(doc, secao_de_topo) -> [contratos que se declaram autoridade].

    A `Autoridade` vivia em COMENTARIO no cabecalho de cada contrato. Comentario
    nao e dado, e foi por isso que um bloco normativo de secao reivindicada foi
    parar em IGNORADOS com motivo falso, sem que nada notasse. Agora e
    `x-aurora-authority`, e este mapa e o gatilho de revisao.
    """
    mapa: dict = {}
    for nome, schema in sorted(contratos.items()):
        for entrada in schema.get("x-aurora-authority") or []:
            for secao in entrada.get("sections") or []:
                mapa.setdefault((entrada["doc"], secao), []).append(nome)
    return mapa


def blocos_da_spec():
    """Todo bloco cercado yaml/json, com o cabecalho que o precede."""
    for doc in sorted(SPEC_DIR.glob("*.md")):
        por_secao: dict[str, int] = {}
        heading = ""
        lang = None
        buf: list[str] = []
        for numero, linha in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if lang is None:
                cabecalho = re.match(r"^#{2,4}\s+(.*)$", linha)
                if cabecalho:
                    heading = cabecalho.group(1).strip()
                cerca = re.match(r"^```(\w*)\s*$", linha)
                if cerca:
                    lang, buf, inicio = (cerca.group(1) or ""), [], numero
            elif linha.strip() == "```":
                if lang in ROTULOS_ESTRUTURAIS:
                    lang = None
                    continue
                if lang not in ROTULOS_DE_INSTANCIA:
                    # Rotulo fora dos dois conjuntos fechados, ou cerca sem
                    # rotulo. Sem rotulo so vira problema se o conteudo parecer
                    # ESTRUTURA DE DADOS: diagrama e arvore de diretorio nao
                    # parseiam como mapeamento. Medido contra as 14 cercas sem
                    # rotulo de docs/spec/ — ruido zero hoje, e pega o bloco
                    # normativo futuro que esquecer o rotulo.
                    parece_dado = False
                    if not lang:
                        try:
                            carregado = yaml.safe_load("\n".join(buf))
                            parece_dado = isinstance(carregado, (dict, list)) and bool(carregado)
                        except Exception:
                            parece_dado = False
                    if lang or parece_dado:
                        yield doc.name, heading, None, lang, None, inicio
                    lang = None
                    continue
                if True:
                    # INDICE DENTRO DA SECAO. Sem ele, dois blocos sob o mesmo
                    # cabecalho colapsariam na mesma chave e o segundo ficaria
                    # sem validacao EM SILENCIO — a classe de defeito que este
                    # script existe para fechar, reproduzida dentro dele.
                    indice = por_secao.get(heading, 0)
                    por_secao[heading] = indice + 1
                    yield doc.name, heading, indice, lang, "\n".join(buf), inicio
                lang = None
            else:
                buf.append(linha)


def carrega(lang: str, texto: str):
    # safe_load: nada em docs/spec/ deve poder instanciar objeto Python.
    return json.loads(texto) if lang == "json" else yaml.safe_load(texto)


def desembrulha(dados, form: str, rotulo: str):
    """Extrai do bloco a parte que o ponteiro valida."""
    if form == "document":
        return dados
    if form == "sequence-item":
        if not isinstance(dados, list) or not dados:
            raise ValueError(f"{rotulo}: form `sequence-item` mas o bloco nao e sequencia")
        return dados[0]
    if form.startswith("property:"):
        chave = form.split(":", 1)[1].strip()
        if not isinstance(dados, dict) or chave not in dados:
            raise ValueError(f"{rotulo}: form `{form}` mas o bloco nao tem a chave")
        return dados[chave]
    raise ValueError(f"{rotulo}: form desconhecido `{form}`")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # Diretorio alternativo de contratos, usado por
    # scripts/check_spec_examples_probes.py para rodar contra copias com defeito
    # plantado. A spec permanece a real: e ela que este script trata como fonte.
    raiz = Path(argv[0]).resolve() if argv else CONTRACTS_DIR
    # Segundo argumento: diretorio alternativo de SPEC. Sem ele, as regras que
    # dependem do conteudo da spec — rotulo de cerca desconhecido e entrada orfa
    # em IGNORADOS — nao teriam como ser provadas por defeito plantado, e regra
    # sem probe e o defeito que este projeto passou a fase inteira punindo.
    global SPEC_DIR
    if len(argv) > 1:
        SPEC_DIR = Path(argv[1]).resolve()

    contratos, por_id = {}, {}
    for caminho in sorted(raiz.glob("*.yaml")):
        schema = parse_yaml(caminho)
        contratos[schema.get("x-aurora-contract") or caminho.stem] = schema
        if "$id" in schema:
            por_id[schema["$id"]] = schema

    registry = Registry().with_resources(
        [(i, Resource.from_contents(s)) for i, s in sorted(por_id.items())]
    )

    # (doc, anchor) -> (contrato, declaracao)
    reivindicados: dict[tuple, tuple] = {}
    for nome, schema in sorted(contratos.items()):
        for decl in schema.get("x-aurora-spec-examples") or []:
            chave = (decl["doc"], decl["anchor"], decl.get("index", 0))
            if chave in reivindicados:
                outro = reivindicados[chave][0]
                print(
                    f"ERRO: '{decl['doc']} §{decl['anchor']}' reivindicado por "
                    f"'{nome}' e por '{outro}'",
                    file=sys.stderr,
                )
                return 1
            reivindicados[chave] = (nome, schema, decl)

    # -----------------------------------------------------------------------
    # x-aurora-spec-examples SUBCONJUNTO DE x-aurora-authority.
    #
    # Reivindicar um bloco de uma secao sem se declarar autoridade dela deixa a
    # lista de autoridade INCOMPLETA — e e ela que dispara a exigencia de
    # justificativa sobre IGNORADOS. Autoridade incompleta significa gatilho que
    # nao dispara, que e como o B1 sobreviveu.
    #
    # Medido na quinta auditoria: `scenario` reivindicava bloco em 08 secao 5 sem
    # declarar autoridade sobre 08, enquanto `evidence` declarava autoridade
    # sobre 08 secao 5 e nao reivindicava bloco nenhum. Ninguem reclamava. M1.
    # -----------------------------------------------------------------------
    falhas: list[str] = []
    validados = 0
    vistos: set[tuple] = set()
    ignorados_usados: set[tuple] = set()
    mapa_autoridade = autoridades(contratos)

    for nome, schema in sorted(contratos.items()):
        declarada = {
            (e["doc"], secao)
            for e in (schema.get("x-aurora-authority") or [])
            for secao in (e.get("sections") or [])
        }
        for decl in schema.get("x-aurora-spec-examples") or []:
            chave_auth = (decl["doc"], _secao_de(decl["anchor"]))
            if chave_auth not in declarada:
                falhas.append(
                    f"contracts/{nome}: reivindica bloco em "
                    f"{decl['doc']} §{decl['anchor']} sem declarar autoridade "
                    f"sobre essa secao em `x-aurora-authority`."
                )

    for doc, heading, indice, lang, texto, linha in blocos_da_spec():
        if indice is None:
            # Rotulo desconhecido ou cerca sem rotulo com cara de dado. Reprova
            # com mensagem propria: a versao anterior nem enxergava esses
            # blocos — eles nao viravam "sem dono", viravam nada. M2.
            falhas.append(
                f"docs/spec/{doc}:{linha} §{heading}\n"
                f"    cerca com rotulo {lang or '<ausente>'} que parece carregar "
                f"estrutura de dados.\n    Rotule como `yaml`/`json` para que seja "
                f"verificada, ou como um dos rotulos estruturais declarados."
            )
            continue
        chave = (doc, heading, indice)
        vistos.add(chave)
        sufixo = f" [bloco {indice}]" if indice else ""
        origem = f"docs/spec/{doc}:{linha} §{heading}{sufixo}"

        if chave in IGNORADOS:
            ignorados_usados.add(chave)
            entrada = IGNORADOS[chave]
            donos = mapa_autoridade.get((doc, _secao_de(heading)), [])
            declarado = entrada.get("nao_e_instancia_de")
            if donos and not declarado:
                # EXIGENCIA DE FORMA, nao falha automatica. O bloco esta sob
                # secao que algum contrato reivindica como autoridade, entao o
                # motivo precisa dizer por que ele NAO e instancia daquele
                # contrato — o que obriga a ler o bloco. Era o passo que faltou
                # no B1 da quarta auditoria.
                falhas.append(
                    f"{origem}\n    ignorado sob secao reivindicada por "
                    f"{donos} como autoridade, e o motivo nao diz por que o "
                    f"bloco nao e instancia desse contrato.\n    Declare "
                    f"`nao_e_instancia_de` depois de LER o bloco."
                )
            elif declarado and declarado not in donos:
                falhas.append(
                    f"{origem}\n    declara `nao_e_instancia_de: {declarado}`, "
                    f"mas esse contrato nao reivindica esta secao "
                    f"(reivindicam: {donos or 'nenhum'})."
                )
            continue

        if chave not in reivindicados:
            falhas.append(
                f"{origem}\n    bloco {lang} que nenhum contrato reivindica e que "
                f"nao esta em IGNORADOS.\n    Ou um contrato o declara em "
                f"`x-aurora-spec-examples`, ou ele entra em IGNORADOS com motivo."
            )
            continue

        nome, schema, decl = reivindicados[chave]
        try:
            instancia = desembrulha(carrega(lang, texto), decl.get("form", "document"), origem)
        except Exception as exc:
            falhas.append(f"{origem}\n    nao foi possivel extrair a instancia: {exc}")
            continue

        ponteiro = decl.get("pointer", "#")
        alvo = {"$ref": f"{schema['$id']}{ponteiro}"}
        erros = sorted(Draft202012Validator(alvo, registry=registry).iter_errors(instancia),
                       key=str)
        validados += 1
        for e in erros:
            falhas.append(
                f"{origem}\n    o exemplo NORMATIVO e recusado por "
                f"contracts/{nome}*.yaml{ponteiro}\n"
                f"    {e.json_path}: {e.message}"
            )

    # Reivindicacao para ancora que nao existe mais: a spec mudou de cabecalho.
    for (doc, anchor, indice), (nome, _, _) in sorted(reivindicados.items()):
        if (doc, anchor, indice) not in vistos:
            falhas.append(
                f"contracts/{nome}: reivindica '{doc} §{anchor}', que nao existe "
                f"em docs/spec/.\n    Cabecalho renomeado ou bloco removido."
            )

    # L3 — entrada morta em IGNORADOS. Reivindicacao para ancora inexistente ja
    # falhava alto; a lista de ignorados nao, e ela e justamente onde a quarta
    # auditoria mostrou que defeito se esconde.
    for chave in sorted(set(IGNORADOS) - ignorados_usados):
        falhas.append(
            f"IGNORADOS: entrada para '{chave[0]} §{chave[1]}' [bloco {chave[2]}] "
            f"que nao existe mais em docs/spec/.\n    Bloco removido ou "
            f"cabecalho renomeado — a entrada ficou orfa."
        )

    print(f"Blocos yaml/json em docs/spec/: {len(vistos)}")
    print(f"  reivindicados por contrato e validados: {validados}")
    print(f"  ignorados com motivo declarado: {len(IGNORADOS)}")

    if falhas:
        print(f"\nFALHAS: {len(falhas)}\n", file=sys.stderr)
        for f in falhas:
            print(f"  {f}\n", file=sys.stderr)
        return 1

    print("\nTodo exemplo normativo da spec e aceito pelo contrato que o governa.")
    print("Nenhum bloco sem reivindicacao e sem motivo declarado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
