"""`evidence build` e `evidence verify` — o pacote em disco. `08` §7.

AUTORIDADE
----------
`08_EVIDENCE_SIMULATOR.md` §7, `06_ACCEPTANCE_TESTS.md` T13, e os itens 2 e 3
da DoD da Fase 9.

OS DOIS VERBOS SAO O MESMO MECANISMO
=====================================
    construir   projeta, escreve os arquivos e o MANIFEST.json
    conferir    REPROJETA em memoria e compara com o disco

Nao ha regra de validacao escrita a mao em `conferir`. **A projecao e funcao
pura de (ground truth, geradores)**, entao o oraculo da conferencia e o proprio
produtor, rodado de novo — e um verificador que reimplementasse as regras
divergiria do produtor na primeira mudanca, que e o defeito que `08` §1 existe
para impedir, um nivel acima.

E ISSO ALCANCA O QUE O ELENCO NAO ALCANCA. `elenco.py` declara o proprio limite:
ele afirma ausencia de invencao para ENDERECO, que tem forma fechada; um ator
inventado que nao colidisse com nada passaria. A reprojecao o pega, porque o
byte diverge — qualquer que seja a natureza da diferenca. O limite da peca 1
fecha aqui, e nao por acrescimo de regra.

O QUE `conferir` DEVOLVE, E POR QUE E LISTA
============================================
Lista de achados, e nao excecao na primeira divergencia. Quem confere um pacote
quer saber **tudo** o que divergiu — e a mesma razao pela qual o linter de pack
valida por documento em vez de parar no primeiro erro. `range-cli` transforma a
lista em saida e codigo de retorno.

`conferir` NAO ESCREVE NADA. `04` §8.1 (a) nomeia `evidence verify` entre os
subcomandos que so LEEM, e as allowlists de quem opera o repositorio dependem
dessa classificacao. R7 §3 diz o mesmo para todo stage de verificacao.

BYTES, LF E UTF-8 — R7 §2
==========================
Os arquivos sao escritos com `newline="\\n"` e UTF-8 explicitos, e os hashes sao
sobre BYTES. A licao de origem e a R2 §2: 56 de 74 hashes "falharam" num
checkout Windows e era CRLF, nao divergencia. Aqui **nao ha blob de Git a que
recorrer** — `scenarios/` esta fora do Git desde a Fase 5 —, entao a disciplina
tem de estar no produtor.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from range_core.evidence.manifesto import hash_do_ground_truth, montar
from range_core.evidence.projecao import projetar

__all__ = ["MANIFESTO", "construir", "conferir"]

#: `08` §7 nomeia o arquivo. Maiusculo, como `README` — e indice, nao dado.
MANIFESTO = "MANIFEST.json"


def _documento(ground_truth_bytes: bytes) -> Mapping:
    """O ground truth parseado. YAML, como o loader de pack le."""
    import yaml

    return yaml.safe_load(ground_truth_bytes.decode("utf-8")) or {}


def _escreve(alvo: Path, conteudo: str) -> None:
    """Texto em UTF-8 com LF — ver o cabecalho.

    `newline=""` desliga a traducao de fim de linha do Python: sem ele, no
    Windows, `\\n` vira `\\r\\n` na escrita e o hash do manifesto deixa de bater
    com o arquivo no mesmo commit que o escreveu.
    """
    alvo.write_text(conteudo, encoding="utf-8", newline="")


def construir(
    ground_truth_bytes: bytes,
    *,
    destino: Path,
    geradores: Mapping,
    formatos: Mapping[str, str],
    banner: str,
    pack_id: str,
    random_seed: int,
    entrega: Mapping[str, str] | None = None,
    atrasos: Mapping[str, int] | None = None,
) -> dict:
    """Projeta, escreve e devolve o manifesto.

    O diretorio e criado se nao existir. **Nada e escrito antes de a projecao
    inteira passar**: `projetar` levanta em gerador ausente, entidade inventada
    ou IOC, e um pacote escrito pela metade seria pior que nenhum — o
    facilitador teria arquivos coerentes ao lado de arquivos que nao existem, e
    o manifesto faltando para dizer qual e qual. E a mesma ordem que
    `materialize` fixa para o par `ground_truth`/`GM_NOTES`.
    """
    fontes = projetar(
        _documento(ground_truth_bytes),
        geradores=geradores,
        formatos=formatos,
        banner=banner,
    )

    manifesto = montar(
        fontes,
        pack_id=pack_id,
        ground_truth_bytes=ground_truth_bytes,
        random_seed=random_seed,
        entrega=entrega,
        atrasos=atrasos,
    )

    destino.mkdir(parents=True, exist_ok=True)
    for fonte in fontes:
        _escreve(destino / fonte.nome_do_arquivo, fonte.conteudo)

    # `indent=2` e `ensure_ascii=False` sao FORMA FIXA, e nao estilo: o
    # manifesto e lido por humano (o facilitador) e comparado byte a byte por
    # maquina. Uma forma que mudasse entre execucoes faria o diff acusar
    # mudanca onde nao houve.
    _escreve(
        destino / MANIFESTO,
        json.dumps(manifesto, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
    )
    return manifesto


def conferir(
    destino: Path,
    ground_truth_bytes: bytes,
    *,
    geradores: Mapping,
    formatos: Mapping[str, str],
    banner: str,
    contratos: dict[str, dict],
) -> list[str]:
    """Os achados do pacote em disco. Lista vazia significa integro.

    A ORDEM DAS CHECAGENS E A DA DEPENDENCIA, e cada degrau so faz sentido se o
    anterior passou: sem manifesto nao ha o que conferir; com o ground truth
    errado, toda divergencia de arquivo seria consequencia dele e reportar as
    duas coisas enterraria a causa no ruido.
    """
    achados: list[str] = []

    caminho_do_manifesto = destino / MANIFESTO
    if not caminho_do_manifesto.exists():
        return [
            f"{MANIFESTO} ausente em {destino}: sem ele nao ha o que conferir — "
            f"`08` §7 o exige para o facilitador saber o que existe e para o "
            f"teste verificar cobertura de projecao"
        ]

    try:
        em_disco = json.loads(caminho_do_manifesto.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        return [f"{MANIFESTO} ilegivel: {erro}"]

    from range_core.evidence.manifesto import erros_de_schema

    for erro in erros_de_schema(em_disco, contratos):
        achados.append(f"{MANIFESTO} nao valida contra o contrato — {erro}")
    if achados:
        return achados

    esperado = hash_do_ground_truth(ground_truth_bytes)
    declarado = em_disco["generated_from"]["ground_truth_hash"]
    if declarado != esperado:
        return [
            f"ground_truth mudou desde o build: o manifesto declara {declarado} "
            f"e o documento tem {esperado}. Rode `evidence build` de novo — as "
            f"fontes em disco projetam OUTRO gabarito"
        ]

    # A REPROJECAO. Daqui em diante o oraculo e o produtor, rodado de novo.
    fontes = projetar(
        _documento(ground_truth_bytes),
        geradores=geradores,
        formatos=formatos,
        banner=banner,
    )
    por_arquivo = {f.nome_do_arquivo: f for f in fontes}

    declarados = {s["file"] for s in em_disco["sources"]}
    if declarados != set(por_arquivo):
        faltam = sorted(set(por_arquivo) - declarados)
        sobram = sorted(declarados - set(por_arquivo))
        if faltam:
            achados.append(
                f"{MANIFESTO} nao declara fonte que o ground truth projeta: "
                f"{', '.join(faltam)}"
            )
        if sobram:
            achados.append(
                f"{MANIFESTO} declara fonte que o ground truth NAO projeta: "
                f"{', '.join(sobram)}"
            )

    for source in em_disco["sources"]:
        nome = source["file"]
        alvo = destino / nome
        if not alvo.exists():
            achados.append(f"{nome}: declarado no {MANIFESTO} e AUSENTE do disco")
            continue

        bruto = alvo.read_bytes()
        em_hash = hashlib.sha256(bruto).hexdigest()
        if em_hash != source["sha256"]:
            achados.append(
                f"{nome}: o conteudo em disco nao e o que o {MANIFESTO} declara "
                f"(sha256 {em_hash[:12]}… contra {source['sha256'][:12]}…). "
                f"Edicao manual, ou build de outro gabarito"
            )
            continue

        fonte = por_arquivo.get(nome)
        if fonte is not None and bruto != fonte.conteudo.encode("utf-8"):
            achados.append(
                f"{nome}: o hash confere com o {MANIFESTO}, mas o conteudo NAO e "
                f"o que o ground truth projeta — manifesto e arquivo foram "
                f"alterados juntos"
            )

    # ARQUIVO A MAIS: conteudo autoral entrando pela porta dos fundos. A
    # cobertura de `08` §7 deixaria de descrever o que existe, que e metade da
    # razao de o manifesto existir.
    for caminho in sorted(destino.iterdir()):
        if caminho.is_file() and caminho.name != MANIFESTO and caminho.name not in declarados:
            achados.append(
                f"{caminho.name}: existe no diretorio e NAO e declarado no "
                f"{MANIFESTO} — evidencia nao declarada e conteudo autoral"
            )

    return achados
