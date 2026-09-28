#!/usr/bin/env python3
"""H2 — a prova do exercicio de 4 h e DESTA ARVORE e DESTE PACK, e ela existe.

O QUE ESTA CHECAGEM FECHA
--------------------------
O H2 da 2ª auditoria da Fase 7: os itens 6 e 9 da DoD chegavam ao auditor como
ATESTACAO — o pack de 4 h vive fora do Git (decisao da Fase 5), cinco dos sete
arquivos sao autoria e nao funcao de insumo versionado, e as afirmacoes do
registro ("lint sem achados", "4 caminhos", "0,025 s") nao tinham objeto
verificavel. E exatamente a classe que a P4-10 fechou para o container e a M2
fechou para o seed: **o que exige ambiente acontece fora da sessao do julgador,
e o resultado chega amarrado ao objeto por hash.**

A amarracao aqui e DUPLA, e a segunda perna e o que este objeto exige a mais:

    arvore  — o codigo que mediu (lint, travessia, harness) e o desta arvore;
    pack    — os SETE arquivos medidos, cada um com SHA-256 gravado na prova.

O pack nao esta na arvore (P7-9, decisao pendente do proprietario), entao a
perna dele tem dois modos, DECLARADOS: se `scenarios/<domain>/<pack>` existir
neste checkout, os hashes gravados sao conferidos contra o disco e divergencia
REPROVA — "o pack em disco nao e o pack medido"; se nao existir, a prova segue
valendo pelo que declara, e a saida integra o diz com todas as letras. Um
checkout sem o pack pode confiar na medicao; nao pode fingir que conferiu.

AS SETE DIRECOES
-----------------
    (a) o arquivo NAO EXISTE                                     -> REPROVA
    (b) a `tree` gravada diverge da arvore do `HEAD` daqui       -> REPROVA
    (c) o arquivo esta VERSIONADO                                -> REPROVA
    (d) falta contexto (maquina, data, python, pack, eventos)    -> REPROVA
    (e) a prova diz que lint, dryrun ou o item 9 FALHOU          -> REPROVA
    (f) o arquivo nao declara o esquema que este verificador le  -> REPROVA
    (g) o pack EXISTE no checkout e algum hash diverge           -> REPROVA

Stdlib pura. NAO roda no job `arquitetura` — como o gemeo do seed, ele julga
artefato local que o CI nao tem; quem o executa e o lancador da auditoria e a
varredura de fechamento.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCIA = ".aurora-prova-do-exercicio-4h.json"

#: A DECLARACAO E UNICA — `prova_do_exercicio_4h.py` importa daqui, pela mesma
#: razao do par do seed (§1.4 do checkpoint da Fase 2).
ESQUEMA = "aurora.prova-do-exercicio-4h/1"

RULE = "H2 - a prova do exercicio de 4 h e desta arvore e deste pack"

CONTEXTO = ("maquina", "python", "data", "stack", "pack_id", "content_hash", "eventos")
ITENS = (
    "lint_sem_achados",
    "item_6_dryrun_todos_os_caminhos",
    "item_9_reconstrucao_em_menos_de_3_s",
    # A SEGUNDA METADE, acrescentada na Fase 9 — `06` T13.
    #
    # O `spec-change item-8-volume-de-4h` dividiu o item 8 da Fase 2 em dois, e
    # disse por que: sem o criterio desta fase, T12 verificaria o requisito e
    # ele *"passaria a ser falso aqui, sem nada ficar vermelho — que e como um
    # requisito morre"*. Este nome na lista e o que impede isso.
    "item_7_reconstrucao_com_telemetria",
)


def _arvore(raiz: Path) -> str | None:
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


def hashes_do_pack_em_disco(raiz: Path, doc: dict) -> dict[str, str] | None:
    """Os SHA-256 dos arquivos do pack NESTE checkout, ou `None` se ausente.

    `None` e "o pack nao esta aqui" — o modo declarado em que a perna (g) nao
    se aplica. Dicionario vazio nunca sai daqui: diretorio presente com
    arquivo gravado faltando aparece como hash divergente (`ausente`), porque
    pack pela metade e exatamente o que a perna existe para pegar.
    """
    pack_dir = raiz / str(doc.get("pack_dir", ""))
    if not doc.get("pack_dir") or not pack_dir.is_dir():
        return None
    em_disco: dict[str, str] = {}
    for nome in doc.get("arquivos") or {}:
        caminho = pack_dir / nome
        em_disco[nome] = (
            hashlib.sha256(caminho.read_bytes()).hexdigest()
            if caminho.is_file()
            else "ausente"
        )
    return em_disco


def avalia(
    doc: dict | None,
    arvore: str | None,
    versionado: bool,
    em_disco: dict[str, str] | None,
) -> list[str]:
    """As sete direcoes. Por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    if versionado:
        problemas.append(
            f"`{EVIDENCIA}` esta VERSIONADO. Ele carrega o hash da arvore que "
            "mede, e um arquivo versionado nao contem o hash da arvore que o "
            "contem — a amarracao vira circular."
        )

    if doc is None:
        problemas.append(
            f"`{EVIDENCIA}` nao existe ou nao e JSON legivel. Os itens 6 e 9 da "
            "DoD ficam sem prova, e ISTO NAO DEGRADA PARA OK.\n"
            "    Rode, na maquina que vai medir:\n"
            "      AURORA_TEST_DATABASE_URL=... \\\n"
            "          python scripts/prova_do_exercicio_4h.py <dir-do-pack>"
        )
        return problemas

    if doc.get("esquema") != ESQUEMA:
        problemas.append(
            f"`{EVIDENCIA}` nao declara o esquema `{ESQUEMA}` (declara "
            f"{doc.get('esquema')!r}). Ou o arquivo nao e o que este verificador "
            "julga, ou o formato mudou sem que a checagem acompanhasse."
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
            f"checkout e `{arvore}`. O codigo que mediu e OUTRO — meca de novo."
        )

    for campo in CONTEXTO:
        if not doc.get(campo):
            problemas.append(
                f"a prova nao traz `{campo}`. `06` T12 exige maquina, data e "
                "stack ao lado do numero."
            )

    if not doc.get("arquivos"):
        problemas.append(
            "a prova nao traz os hashes dos arquivos do pack (`arquivos`). Sem "
            "eles a segunda perna da amarracao nao existe, e a prova afirma um "
            "numero sobre objeto nenhum."
        )

    for item in ITENS:
        if doc.get(item) is not True:
            problemas.append(
                f"a prova gravada diz que `{item}` NAO passou "
                f"({doc.get(item)!r}). O arquivo e escrito mesmo em falha, de "
                "proposito: e assim que 'falhou' se distingue de 'ninguem rodou'."
            )

    if em_disco is not None:
        for nome, gravado in sorted((doc.get("arquivos") or {}).items()):
            if em_disco.get(nome) != gravado:
                problemas.append(
                    f"`{nome}`: o pack em disco nao e o pack medido — a prova "
                    f"gravou `{str(gravado)[:12]}…` e o disco tem "
                    f"`{str(em_disco.get(nome))[:12]}…`. Ou o pack mudou depois "
                    "da medicao (meca de novo), ou este diretorio contem outra "
                    "coisa com o mesmo nome."
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

    em_disco = hashes_do_pack_em_disco(REPO_ROOT, doc) if doc else None
    problemas = avalia(doc, _arvore(REPO_ROOT), _versionado(REPO_ROOT), em_disco)

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    perna_do_pack = (
        f"conferidos contra o disco, {len(doc['arquivos'])} arquivos identicos"
        if em_disco is not None
        else "o pack NAO esta neste checkout; valem os hashes declarados na prova"
    )
    print(f"{RULE}: prova da arvore `{doc['tree'][:12]}`, e este checkout e a mesma.")
    print(f"  maquina  {doc['maquina']}  ·  python {doc['python']}")
    print(f"  data     {doc['data']}  ·  stack {doc['stack']}")
    print(f"  pack     {doc['pack_id']}  ·  content_hash {doc['content_hash'][:24]}…")
    print(f"  arquivos {perna_do_pack}")
    print(
        f"  fluxo    {doc['eventos']} eventos  ·  dryrun {doc['caminhos']} caminhos "
        f"em {doc['pontos']} pontos, todos percorridos"
    )
    print(
        f"  item 9   {doc['total_s']:.3f} s contra o orcamento de "
        f"{doc['orcamento_s']:.0f} s"
    )
    # A SEGUNDA METADE — Fase 9. Impressa com o VOLUME junto, e nao so com o
    # tempo: o numero sozinho nao diz contra o que ele passou, e e o volume que
    # o `spec-change item-8-volume-de-4h` poe no centro do criterio.
    com = doc.get("com_telemetria") or {}
    if com:
        print(
            f"  item 7   {com['total_s']:.3f} s contra o orcamento de "
            f"{com['orcamento_s']:.0f} s, com {com['eventos']} eventos "
            f"({com['telemetria']} telemetry_emitted, "
            f"{com['telemetria_por_minuto']}/min)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
