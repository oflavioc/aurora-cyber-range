"""`RANDOM_SEED` — a leitura, e os fluxos derivados dela.

AUTORIDADE
----------
`00_MASTER_SPEC.md` §8 ("Determinismo — `RANDOM_SEED` fixo em `.env`.
Necessario, mas nao suficiente"); `02_DOMAIN_ACADEMUS.md` §6;
`05_SECURITY_REQUIREMENTS.md` §8; `06_ACCEPTANCE_TESTS.md` T8;
`08_EVIDENCE_SIMULATOR.md` §1; `07_IMPLEMENTATION_PHASES.md` Fase 2, item 2 da
DoD.

O ITEM 2 EXIGE UMA COISA ESPECIFICA
-----------------------------------
*"`RANDOM_SEED` lido de `.env` **por codigo do `range-core`**, nao por
atestacao."* O contraste do item nao e entre variavel de ambiente e arquivo — e
entre **codigo** e **afirmacao**. Ate aqui o seed existia em `.env.example` e em
cinco lugares da spec, e nada no repositorio o lia: a determinicidade era
propriedade declarada e nao exercida, que e a forma do B1 da primeira auditoria
da Fase 0 — o mecanismo existir nao e a propriedade valer.

**Esta fase nao consome o seed, e isso esta dito e nao escondido.** `event_id`
sai de `secrets` (§3.4 do registro), e nenhuma peca da Fase 2 sorteia coisa
alguma. Os consumidores tem data: o dataset da **Fase 5** (`06` T8), a projecao
de evidencia da **Fase 9** (`08` §1) e as senhas de seed de `05` §8. O que o
item cobra, e o que esta entregue, e **o caminho de leitura existindo e sendo
verificado** — nao um consumidor inventado para justifica-lo.

POR QUE MODULO NA RAIZ DE `range-core/`, e nao dentro de um consumidor
-----------------------------------------------------------------------
`01` §2 enumera os DIRETORIOS do core e o conteudo de cada um. O seed nao e de
nenhum deles: ele atravessa `evidence/` (projecao), o seed de dataset (que e de
adapter) e a geracao de senha. Guarda-lo dentro de um dos tres faria os outros
dois importarem de um lugar que nao os descreve.

Modulo na raiz nao acrescenta diretorio, entao nao contradiz o layout que a spec
fixa. Se um dia houver mais de um artefato desta natureza, a discussao e sobre
criar diretorio — e ai e `spec-change`, nao decisao de implementacao.

MESMO SEED NAO BASTA, E O CODIGO PRECISA REFLETIR ISSO
-------------------------------------------------------
`08` §1 e explicito: *"geradores independentes divergem semanticamente a
primeira mudanca de codigo **ou de ordem de geracao**"*.

Um `random.Random` unico compartilhado tem exatamente esse defeito: dois
geradores consumindo do mesmo fluxo ficam ACOPLADOS pela ordem, e acrescentar um
gerador novo desloca tudo o que vem depois dele. `06` T8 exige dataset
byte-identico entre duas execucoes; com fluxo unico, ele passa hoje e falha no
dia em que alguem acrescentar um gerador — por um motivo que ninguem localiza,
porque o defeito nao esta em quem quebrou.

Por isso `seeded_random` deriva um fluxo POR ESCOPO. Cada gerador pede o seu, e
a ordem entre eles deixa de existir como variavel.

A DERIVACAO NAO USA `hash()`, e isso nao e preciosismo
-------------------------------------------------------
`hash()` de string em Python e salgado por `PYTHONHASHSEED` e **muda entre
processos**. Derivar com ele produziria dataset diferente a cada execucao a
partir do mesmo `RANDOM_SEED` — o oposto exato do que T8 cobra, e uma falha que
so apareceria em execucao separada, nunca dentro da mesma.

SHA-256 aqui e funcao de derivacao determinista, e nao mecanismo de seguranca.
`05_SECURITY_REQUIREMENTS.md` §1 proibe comportamento ofensivo, nao import de
biblioteca criptografica — e `tools/check_security_constraints.py` foi escrito
para nao confundir os dois.
"""

from __future__ import annotations

import hashlib
import os
import random
from collections.abc import Mapping
from pathlib import Path

#: O nome da variavel. Uma so ocorrencia literal, aqui, pelo mesmo motivo que
#: flags e `event_type` vem de constante: nome escrito duas vezes diverge uma.
RANDOM_SEED = "RANDOM_SEED"


class SeedUnavailable(Exception):
    """Nao ha `RANDOM_SEED`, ou o valor nao e inteiro.

    RECUSA ALTA, E NUNCA VALOR PADRAO. Um seed inventado produziria dataset
    reproduzivel e ERRADO — reproduziria a si mesmo, e nao o exercicio que
    alguem declarou. E `05` §8 deriva senha de seed dali: um default silencioso
    seria senha previsivel gerada por omissao.
    """


def parse_dotenv(texto: str) -> dict[str, str]:
    """`.env` no subconjunto que este projeto usa: `CHAVE=valor`, um por linha.

    Aceita linha em branco, comentario com `#` e aspas em volta do valor. **Nao**
    faz interpolacao de `${OUTRA}`, nao aceita valor em varias linhas e nao
    interpreta escapes.

    LIMITE DECLARADO, e a saida esta nomeada. Isto nao e um parser compativel
    com `dotenv`: e o subconjunto de `.env.example`, que e o formato que este
    repositorio de fato escreve. Se `.env` passar a precisar de interpolacao, a
    resposta e `python-dotenv` pinado em `constraints.txt`, e nao esticar isto —
    a mesma linha que `fase_1.md` §7.4 declara sobre `tools/_common.py`, agora
    dita antes de custar em vez de depois.
    """
    valores: dict[str, str] = {}
    for linha in texto.splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#") or "=" not in limpa:
            continue
        chave, _, valor = limpa.partition("=")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[chave.strip()] = valor
    return valores


def read_dotenv(caminho: Path) -> dict[str, str]:
    """Le um arquivo no formato `.env`. Arquivo ausente devolve vazio.

    Ausencia nao e erro AQUI: quem decide se a ausencia importa e
    `random_seed`, que e onde a mensagem pode dizer as duas fontes possiveis.
    """
    try:
        return parse_dotenv(Path(caminho).read_text(encoding="utf-8"))
    except OSError:
        return {}


def random_seed(
    env: Mapping[str, str] | None = None,
    *,
    dotenv_path: Path | str | None = None,
) -> int:
    """O `RANDOM_SEED`, do ambiente ou de um `.env`. Levanta se nao houver.

    A ORDEM E AMBIENTE PRIMEIRO, e ela tem consequencia operacional: em
    container as variaveis chegam pelo ambiente — o `docker-compose.yml` as
    injeta —, e o `.env` e o caso de desenvolvimento local. Ambiente vencendo
    significa que quem exporta a variavel para rodar um caso pontual nao precisa
    editar arquivo, e que o container nao depende de `.env` existir la dentro.

    `dotenv_path` e PARAMETRO, e nao descoberta. O nucleo nao sai procurando
    `.env` a partir do CWD: seria a mesma armadilha que a §3.2 do registro
    mediu com `contracts` — funciona na raiz do repositorio e falha no
    container, e a falha aparece longe da causa. Quem monta o processo sabe onde
    o arquivo esta.
    """
    ambiente = os.environ if env is None else env
    bruto = ambiente.get(RANDOM_SEED)

    if bruto is None and dotenv_path is not None:
        bruto = read_dotenv(Path(dotenv_path)).get(RANDOM_SEED)

    if bruto is None or str(bruto).strip() == "":
        onde = f" nem em {dotenv_path}" if dotenv_path is not None else ""
        raise SeedUnavailable(
            f"{RANDOM_SEED} nao esta no ambiente{onde}. `00_MASTER_SPEC.md` §8 o "
            "exige fixo em `.env`, e `.env.example` traz o placeholder. Nao ha "
            "valor padrao de proposito: seed inventado reproduz a si mesmo, nao "
            "o exercicio declarado."
        )

    try:
        return int(str(bruto).strip())
    except ValueError as exc:
        raise SeedUnavailable(
            f"{RANDOM_SEED}={bruto!r} nao e inteiro. `random.Random` aceitaria a "
            "string e produziria fluxo diferente do que o mesmo numero produz — "
            "dois exercicios 'com o mesmo seed' e datasets distintos."
        ) from exc


def derive_seed(seed: int, escopo: str) -> int:
    """Sub-seed estavel para um escopo. Mesma entrada, mesma saida, sempre.

    Estavel ENTRE PROCESSOS, que e a parte que `hash()` nao daria — ver o
    cabecalho do modulo.
    """
    digest = hashlib.sha256(f"{seed}:{escopo}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def seeded_random(escopo: str, *, seed: int | None = None) -> random.Random:
    """Um `random.Random` proprio do escopo, derivado do `RANDOM_SEED`.

    O SEPARADOR E `:` E NAO `.`, e a troca foi medida em vez de escolhida. Esta
    linha dizia `academus.alunos`, e essa forma e **inexprimivel dentro de
    `domains/`**: o invariante 2 recusa toda string `(academus|prontus|core).algo`
    fora dos geradores de constante, porque e a forma de um nome de flag. A peca
    4 da Fase 5 foi o primeiro consumidor real do seed por escopo, e o hook
    bloqueou na primeira escrita — feedback rapido funcionando como devia.

    Com `:`, o escopo continua dizendo de quem ele e e deixa de colidir. Trocar
    o separador MUDA os sub-seeds derivados, e isso e inofensivo aqui: nao havia
    consumidor antes desta peca.

    `escopo` e o nome de quem gera — `academus:alunos`, `evidence:vpn`. Dois
    escopos distintos nunca compartilham fluxo, entao acrescentar um gerador
    novo nao desloca o que os outros produzem.

    `seed` omitido le do ambiente. Passado, e usado como esta — o que permite a
    um chamador que ja leu o seed uma vez nao reler, e a um teste fixar o valor
    sem tocar no ambiente do processo.
    """
    return random.Random(derive_seed(random_seed() if seed is None else seed, escopo))
