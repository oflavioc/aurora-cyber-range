"""Para onde o pack pode ser escrito — e a recusa que vem antes do primeiro byte.

AUTORIDADE
----------
`04_SCENARIO_SCHEMA.md` §8.1 (b) e (c), `00_MASTER_SPEC.md` §6 (o glossario fixa
`scenarios/<domain>/<pack_id>/`) e `05_SECURITY_REQUIREMENTS.md` §6.

POR QUE ESTE MODULO EXISTE, E POR QUE AQUI
===========================================
A guarda que decide *"este destino e rastreado?"* nasceu em
`tests/fixtures/pack_completo.py`, porque o primeiro que precisou dela foi uma
fixture. Producao nao importa de `tests/`, entao o produtor de pack — que e a
razao inteira de a guarda existir — nao a alcancava.

As saidas eram duas: copiar, ou mover. Copiar seria a D4 no exato mecanismo que
existe para impedir que o gabarito nasca no lugar errado: duas copias de uma
guarda de seguranca divergem, e a que diverge em silencio e a que ninguem esta
olhando. Entao ela MOVEU, e a fixture passou a usar esta.

**AQUI, e nao em `range_cli/`:** ela e agnostica de dominio e e sobre o PACK,
que `engine/` ja governa do lado da leitura (`engine/loader/`). Este e o lado da
escrita. Se morasse no CLI, a fixture de teste passaria a depender do CLI para
montar um pacote — e o CLI e superficie, nao biblioteca.

**E ela nao importa `contracts/`:** as formas dos dois segmentos chegam como
DADO, por parametro, pela regra de `04` §4.1. Quem le contrato e a raiz de
composicao, uma vez.

O QUE ELA NAO E
================
Nao e checagem de `.gitignore`. `.gitignore` e convencao, e `git add -f` a
atravessa; um `git add -A` num diretorio que alguem designorou localmente faz o
mesmo sem intencao nenhuma. A pergunta aqui e a unica que importa — *"o git
rastreia isto?"* — e quem responde e o git.

E nao e lista de caminhos proibidos. Lista nao preve o caminho que ninguem
previu, e o cabecalho de `scripts/check_gabarito_fora_do_git.py` ja registra que
a mesma afirmacao falsa apareceu em quatro lugares diferentes.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

#: O diretorio de topo dos packs — `00` §6, e `01` §2 na arvore do repositorio.
RAIZ_DOS_PACKS = "scenarios"


class DestinoInvalido(Exception):
    """O pack nao pode ser escrito ali, e nada foi escrito.

    Recusa ALTA e ANTES do primeiro byte, pelo mesmo argumento do `PackError` na
    carga: um destino meio-validado produz artefato no lugar errado, e o lugar
    errado aqui e o repositorio publico.
    """


def caminho_do_pack(
    raiz: Path | str,
    domain: str,
    pack_id: str,
    *,
    forma_domain: str,
    forma_pack_id: str,
) -> Path:
    """`<raiz>/scenarios/<domain>/<pack_id>` — `04` §8.1 (b).

    AS DUAS FORMAS CHEGAM COMO DADO, e nao como literal deste modulo: elas sao
    declaradas em `contracts/scenario.schema.v2.yaml` (`domain` e `pack_id`), e
    `04` §4.1 manda a constante derivada de contrato entrar no nucleo por
    parametro, lida uma vez na raiz de composicao. Escreve-las aqui criaria a
    segunda copia de uma forma que o contrato ja fixa — o defeito que o PR #59
    acabou de fechar para `case_id` e `fact_id`.

    A VALIDACAO VEM ANTES DA JUNCAO DO CAMINHO, e nao depois: `domain` com uma
    barra dentro escaparia de `scenarios/` por `Path` sem que nada acusasse, e
    um `..` sairia da arvore. As duas formas do contrato ja excluem os dois
    casos — `^[a-z][a-z0-9_]*$` e `^[a-z][a-z0-9-]*$` nao admitem separador nem
    ponto —, e e por isso que elas sao aplicadas ao SEGMENTO e nao ao caminho
    montado.
    """
    for rotulo, valor, forma in (
        ("domain", domain, forma_domain),
        ("pack_id", pack_id, forma_pack_id),
    ):
        if not re.fullmatch(forma, valor or ""):
            raise DestinoInvalido(
                f"`{rotulo}` invalido: {valor!r} nao casa {forma!r}.\n"
                "    A forma e a de `contracts/scenario.schema.v2.yaml`, e ela "
                "chega aqui como dado — `04` §4.1. `00_MASTER_SPEC.md` §6 fixa o "
                f"destino em `{RAIZ_DOS_PACKS}/<domain>/<pack_id>/`, e segmento "
                "fora de forma sairia dele sem que nada acusasse."
            )
    return Path(raiz) / RAIZ_DOS_PACKS / domain / pack_id


def _git(alvo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """`git` a partir do ancestral EXISTENTE mais proximo do alvo.

    O destino tipicamente ainda NAO existe — e o produtor que o cria. `cwd` num
    diretorio inexistente e `FileNotFoundError`, entao a pergunta e feita de
    onde da para faze-la, e o alvo vai como argumento absoluto.
    """
    partida = alvo
    while not partida.is_dir() and partida != partida.parent:
        partida = partida.parent
    return subprocess.run(
        ["git", *args, "--", str(alvo)],
        cwd=partida,
        capture_output=True,
        text=True,
    )


def e_versionado(alvo: Path | str) -> bool:
    """O `git` decide, e nao uma lista de caminhos escrita aqui.

    Perguntar ao `git` e o que torna a guarda valida para caminho que ninguem
    previu — inclusive um `tests/fixtures/pack_completo/` que alguem criasse por
    engano. Lista de proibidos nao preve a proxima palavra.

    FALHA RUIDOSAMENTE SE O `git` NAO RODA. Degradar para "segue sem verificar"
    poria o gabarito em caminho rastreado exatamente no ambiente em que ninguem
    consegue conferir — e `05` §6 nao admite. `05` §6 nao tem clausula de
    ambiente.
    """
    alvo = Path(alvo)
    try:
        exato = _git(alvo, "ls-files", "--error-unmatch")
    except OSError as erro:  # pragma: no cover - ambiente sem git
        raise DestinoInvalido(
            f"`git` nao pode ser executado para decidir se {alvo} e versionado: "
            f"{erro}. Sem essa decisao o produtor poderia gravar gabarito em "
            "caminho rastreado, e `05_SECURITY_REQUIREMENTS.md` §6 nao admite."
        ) from erro

    if exato.returncode == 0:
        return True

    # Diretorio: `--error-unmatch` so responde por arquivo. Se QUALQUER coisa
    # dentro dele for versionada, o destino e versionado.
    listagem = _git(alvo, "ls-files")
    return bool(listagem.stdout.strip())


def recusa_se_versionado(alvo: Path | str) -> None:
    """A guarda de `04` §8.1 (c), levantada ANTES de qualquer escrita.

    A mensagem nomeia `05` §6 e o verificador que a impoe no CI, porque deteccao
    sem localizacao nao permite intervir — e a mesma forma que `06` T2 fixa para
    a flag nao declarada.
    """
    if e_versionado(alvo):
        raise DestinoInvalido(
            f"{alvo} e VERSIONADO, e o pack carrega `ground_truth.yaml` e "
            "`GM_NOTES.md`.\n"
            "    `05_SECURITY_REQUIREMENTS.md` §6 e `CLAUDE.md` poem o gabarito "
            "fora do repositorio publico, e "
            "`scripts/check_gabarito_fora_do_git.py` reprova o PR que o "
            "versionar — sem excecao por caminho, de proposito.\n"
            "    Materialize em caminho coberto pelo `.gitignore`, ou em "
            "temporario."
        )
