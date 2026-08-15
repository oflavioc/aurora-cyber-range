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
CONTRACTS_DIR = REPO_ROOT / "contracts"

#: Blocos yaml/json de `docs/spec/` que NAO sao instancia de contrato. Cada um
#: com motivo: lista de ignorados sem justificativa vira lugar onde defeito se
#: esconde.
IGNORADOS = {
    ("01_ARCHITECTURE.md", "3. Relógios", 0):
        "fragmento do envelope — so as marcas temporais, sem os campos obrigatorios",
    ("02_DOMAIN_ACADEMUS.md", "6.2 Avaliação por calibração, não por recall", 0):
        "submissao de assessment: artefato de runtime da Fase 6, sem contrato",
    ("03_EXERCISE_DESIGN.md", "2.2 Formato", 0):
        "rubrica BARS: artefato de range-core/rubrics/, chega na Fase 6",
    ("03_EXERCISE_DESIGN.md", "4. Ground truth, observável e reportado", 0):
        "information_distribution.yaml: arquivo de pack sem contrato — ver P1-20",
    ("03_EXERCISE_DESIGN.md", "5.1 Submissão", 0):
        "submissao de assessment: artefato de runtime da Fase 6, sem contrato",
    ("05_SECURITY_REQUIREMENTS.md", "3. Dados", 0):
        "fragmento de uma linha, ilustrando marcacao de dado sintetico",
    ("09_EVENT_MODEL.md", "6. Instrumentação", 0):
        "observability_hooks.yaml: sem contrato proprio; o event_type e guardado "
        "por tools/check_contract_literals.py",
    ("09_EVENT_MODEL.md", "6. Instrumentação", 1):
        "segundo bloco da mesma secao: continuacao do exemplo de hooks",
}


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
                    lang, buf, inicio = (cerca.group(1) or "text"), [], numero
            elif linha.strip() == "```":
                if lang in ("yaml", "json"):
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

    falhas: list[str] = []
    validados = 0
    vistos: set[tuple] = set()

    for doc, heading, indice, lang, texto, linha in blocos_da_spec():
        chave = (doc, heading, indice)
        vistos.add(chave)
        sufixo = f" [bloco {indice}]" if indice else ""
        origem = f"docs/spec/{doc}:{linha} §{heading}{sufixo}"

        if chave in IGNORADOS:
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
