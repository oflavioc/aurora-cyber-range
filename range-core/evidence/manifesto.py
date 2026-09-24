"""O `MANIFEST.json` da evidencia projetada — `08` §7, e a P1-3.

AUTORIDADE
----------
`08_EVIDENCE_SIMULATOR.md` §7 e `contracts/evidence.schema.yaml`.

PARA QUE O MANIFESTO EXISTE
============================
`08` §7 da duas razoes, e elas sao de leitores diferentes:

    o facilitador   saber O QUE EXISTE — arquivo, janela, modo de entrega
    o teste         verificar COBERTURA DE PROJECAO — todo fato com
                    `projections` tem os arquivos correspondentes

E o contrato acrescenta a terceira, em comentario: `ground_truth_hash` **amarra
o manifesto ao ground truth exato de que ele saiu**, e e isso que torna *"ground
truth editado sem rebuild"* detectavel em vez de invisivel.

A P1-3, QUE ESTE MODULO FECHA
==============================
`contracts/evidence.schema.yaml` nasceu na Fase 1 porque a DoD daquela fase o
exigia, e ficou **oito fases sem validar nada** — o proprio arquivo diz *"quem
consome, hoje: o evidence-simulator da Fase 9, que ainda nao existe"*. Este e o
consumidor. `erros_de_schema` valida o documento produzido contra aquele schema,
com os `$ref` resolvidos pelo mesmo `Registry` que o loader de pack usa.

**O schema e oraculo independente no sentido forte da R10**: quem julga a saida
deste modulo nao e outra funcao deste modulo — e um contrato escrito oito fases
antes, por outra razao, com exemplo positivo e nove negativos ja dentro dele.

O HASH E SOBRE BYTES, E O GERADOR ESCREVE LF
=============================================
`ground_truth_hash` e `sha256` das fontes sao calculados sobre **bytes**, e o
gerador escreve com `newline="\\n"` e UTF-8 explicitos (R7 §2). A licao de
origem esta na R2 §2: 56 de 74 hashes "falharam" num checkout Windows e era
CRLF, nao divergencia. Aqui nao ha blob de Git a que recorrer — `scenarios/`
esta fora do Git desde a Fase 5 —, entao a disciplina tem de estar no produtor.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from range_core.evidence.projecao import FonteProjetada

__all__ = ["montar", "erros_de_schema", "hash_do_conteudo", "hash_do_ground_truth"]

#: `08` §5 — o modo default. Pre-posicionado e o unico que nao depende de
#: decisao de cenario: liberado por inject exige o inject, e sob requisicao
#: exige o atraso. Quem tem essa informacao e o pack, e ela chega por `entrega`.
MODO_PADRAO = "pre_positioned"


def hash_do_conteudo(conteudo: str) -> str:
    """`sha256` do conteudo, em UTF-8 — a forma que o contrato exige (64 hex)."""
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def hash_do_ground_truth(ground_truth_bytes: bytes) -> str:
    """`sha256:<64 hex>` — a forma que o contrato exige em `generated_from`.

    Recebe BYTES, e nao o documento parseado: o que se quer detectar e a edicao
    do ARQUIVO. Hash da estrutura parseada seria insensivel a reordenacao de
    chave e a comentario, e comentario em `ground_truth.yaml` e onde o autor
    escreve o que o gabarito significa.
    """
    return "sha256:" + hashlib.sha256(ground_truth_bytes).hexdigest()


def montar(
    fontes: Sequence[FonteProjetada],
    *,
    pack_id: str,
    ground_truth_bytes: bytes,
    random_seed: int,
    banner: str,
    entrega: Mapping[str, str] | None = None,
    atrasos: Mapping[str, int] | None = None,
) -> dict:
    """O documento do `MANIFEST.json`, conforme `contracts/evidence.schema.yaml`.

    `entrega` e `atrasos` vem do pack (`08` §5: `evidence_release`), e ausentes
    significam pre-posicionado. O contrato PROIBE `requires_request_delay_minutes`
    fora do modo `on_request` — campo que nao produz efeito —, e esta funcao
    respeita isso em vez de deixar o schema recusar depois: erro que o produtor
    pode nao cometer e melhor que erro que o validador precisa pegar.
    """
    entrega = entrega or {}
    atrasos = atrasos or {}

    sources = []
    for fonte in fontes:
        modo = entrega.get(fonte.fonte, MODO_PADRAO)
        source = {
            "file": fonte.nome_do_arquivo,
            "format": fonte.formato,
            "delivery_mode": modo,
            "window": fonte.janela,
            "projects_facts": list(fonte.projects_facts),
            "sha256": hash_do_conteudo(fonte.conteudo),
        }
        if modo == "on_request" and fonte.fonte in atrasos:
            source["requires_request_delay_minutes"] = atrasos[fonte.fonte]
        sources.append(source)

    return {
        # O BANNER DO PROPRIO MANIFESTO — `05` §4, L2 da 3a auditoria.
        #
        # Ele ficou de fora porque a producao do banner e por FORMATO DE FIO, e
        # o manifesto nao tem formato de fio: nao e fonte de evidencia e nao
        # passa por `projetar`. A razao explica a omissao e nao a justifica — o
        # facilitador abre este arquivo ANTES de qualquer outro, porque e ele
        # que diz o que existe.
        #
        # PRIMEIRA CHAVE do documento, e nao em qualquer lugar: `05` §4 diz *na
        # primeira linha*, e `json.dumps` com `sort_keys=False` preserva a ordem
        # de insercao. O aviso e o que se le sem rolar.
        "_banner": banner,
        "generated_from": {
            "pack_id": pack_id,
            "ground_truth_hash": hash_do_ground_truth(ground_truth_bytes),
            "random_seed": random_seed,
        },
        "sources": sources,
    }


def erros_de_schema(documento: Mapping, contratos: dict[str, dict]) -> list[str]:
    """Os erros do documento contra `contracts/evidence.schema.yaml`.

    Lista, e nao excecao: quem chama decide o que fazer. O `evidence build`
    recusa; um relatorio de `evidence verify` enumera. Mesma razao pela qual o
    linter de pack valida por documento em vez de parar no primeiro.

    ORDENADOS por `str`, como o loader faz, para a saida ser estavel entre
    execucoes — mensagem de erro que muda de ordem e ruido em diff de log.
    """
    from jsonschema import Draft202012Validator

    from range_core.engine.loader.contract_source import registry_for

    alvo = contratos.get("evidence")
    if not alvo:
        return ["contracts/evidence.schema.yaml ausente dos contratos lidos"]

    erros = sorted(
        Draft202012Validator(alvo, registry=registry_for(contratos)).iter_errors(documento),
        key=str,
    )
    return [f"{e.json_path}: {e.message}" for e in erros]
