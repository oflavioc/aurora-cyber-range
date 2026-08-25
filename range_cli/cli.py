"""`range-cli` — a superficie de cenario. Dois verbos: `materialize` e `lint`.

`04_SCENARIO_SCHEMA.md` §8 declara sete subcomandos; estes sao os dois que
existem. Os demais tem fase: `dryrun` e a peca 4 desta fase, `evidence build` e
`evidence verify` sao da Fase 9, e `validate` nao tem entrega propria enquanto
`lint` o cobre por dentro — ver `range_cli/lint.py`.

**A ORDEM EM QUE ELES NASCERAM E A DA FRONTEIRA DE ESCRITA**, e ela e propriedade
a preservar: `04` §8.1 (a) registra que as allowlists de quem opera o repositorio
liberam os subcomandos que so LEEM — `validate`, `lint`, `dryrun`,
`evidence verify` — e param ai. `materialize` escreve e fica fora delas;
`lint` le e entra. Um verbo novo nao herda a classificacao do irmao por comecar
com o mesmo prefixo.

--------------------------------------------------------------------------------
`range-cli scenario materialize <domain> <pack_id>` — o produtor do pack.

O QUE ELE FECHA
================
A **P5-6**: *"o gabarito e produzido e julgado em memoria, e nada o escreve em
`scenarios/`"*, cujo gatilho declarado e *"o commit em que `range-cli` ganhar o
subcomando que escreve o pack"*. Ate aqui quem fosse facilitar tinha o gerador e
nao tinha o arquivo.

A ORDEM DOS PASSOS E A GARANTIA, e ela e a mesma de `load_pack`
================================================================
1. **Forma dos segmentos** — as duas vem do contrato, e caminho fora de forma e
   recusado antes de existir.
2. **Destino nao rastreado** — `04` §8.1 (c). ANTES do primeiro byte.
3. **Geracao** — o gerador do dominio produz o par, e o linter de `02` §6.3 roda
   DENTRO dele: `GM_NOTES` divergente nao chega a existir.
4. **Escrita** — so agora, e os dois arquivos juntos.

Nada e escrito pela metade: ou o par nasce inteiro, ou nao nasce. Um
`ground_truth.yaml` sem o `GM_NOTES.md` ao lado seria pack que carrega e nao
facilita, e a janela entre as duas escritas e onde alguem copia o primeiro.

O LINTER NAO E REIMPLEMENTADO AQUI, e a ausencia e deliberada
==============================================================
`gabarito.gerar` chama `conferir` internamente, e o docstring de
`GabaritoDivergente` diz por que: *"se rodasse depois, existiria um artefato
invalido no disco entre a escrita e a conferencia — e e nessa janela que alguem
o copia"*. Conferir de novo aqui seria a segunda implementacao da mesma
pergunta; nao conferir e herdar a garantia.

DETERMINISMO E INVARIANTE, E TEM PROVA
=======================================
Mesmos insumos — mesmo `RANDOM_SEED`, mesmo banco, mesmo `domain`/`pack_id` —,
mesmos BYTES. Nada aqui carimba hora, nem ordena por `set`, nem gera
identificador de execucao.

`yaml.safe_dump` com `sort_keys=True` e `allow_unicode=True` fixa a serializacao:
sem `sort_keys`, a ordem de insercao do dicionario vazaria para o arquivo e dois
gabaritos identicos produziriam bytes diferentes. Isso e o que faz a **P7-3**
poder deixar de ser buraco: um pack cujo conteudo e funcao dos insumos pode ser
hasheado e comparado, e um que carimba hora nao pode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from range_cli import lint as lint_de_cenario
from range_core.engine import destino as destino_de_pack
from range_core.engine.loader import contract_source
from range_core.engine.loader.contract_source import ContractSourceError
from range_core.engine.loader.pack_loader import PackError

#: Os dois arquivos do par, na ordem em que `04` §1 os lista.
GROUND_TRUTH = "ground_truth.yaml"
GM_NOTES = "GM_NOTES.md"


class ComandoRecusado(Exception):
    """O comando nao executa, e nada foi escrito."""


def _gerador_do_dominio(domain: str):
    """O gerador de gabarito daquele dominio, resolvido por NOME.

    IMPORT TARDIO E POR NOME, e as duas coisas sao decididas. Tardio porque
    importar todos os dominios no topo faria `range-cli --help` pagar o custo de
    carregar SQLAlchemy; por nome porque um mapa `{"academus": modulo}` escrito
    aqui seria a lista que nao preve o proximo adapter — `01` §2 ja tem
    `prontus/` como stub, e ele vai precisar do seu.

    A RECUSA NOMEIA O QUE FALTA. Dominio sem gerador nao e erro de digitacao do
    operador necessariamente: pode ser adapter que ainda nao tem Linha B, e a
    mensagem separa os dois casos.
    """
    from importlib import import_module

    try:
        return import_module(f"domains.{domain}.seed.gabarito")
    except ModuleNotFoundError as erro:
        raise ComandoRecusado(
            f"o dominio {domain!r} nao tem gerador de gabarito: "
            f"`domains/{domain}/seed/gabarito.py` nao existe ({erro}).\n"
            "    Um adapter sem Linha B nao tem gabarito a materializar — o "
            "`prontus` e esse caso hoje. Se o dominio deveria te-lo, o que falta "
            "e o gerador, e nao este comando."
        ) from erro


def materialize(
    domain: str,
    pack_id: str,
    *,
    raiz: Path,
    abre_motor,
    seed: int,
    conta_alvo: str,
) -> Path:
    """Escreve o par, e devolve o diretorio. Levanta antes de escrever nada.

    `raiz` e parametro em vez de derivada do processo pelo mesmo argumento de
    `04` §8.2 sobre `domain` e `pack_id`: destino de escrita de gabarito nao se
    descobre por contexto. Quem a passa e `main`, e la ela e a raiz do
    repositorio.

    `abre_motor` E FABRICA, E NAO O MOTOR PRONTO, e a diferenca e de ORDEM.
    Recebendo o motor, quem chama tem de abri-lo ANTES — e a primeira versao
    deste comando fazia isso, entao `range-cli scenario materialize Academus x`
    tentava conectar no banco antes de descobrir que `Academus` nao casa a forma
    do contrato. O defeito nao aparecia em teste de unidade, porque teste chama
    esta funcao direto e pula o `main`; apareceu na primeira execucao do
    executavel de verdade.

    Com a fabrica, a conexao so acontece depois das recusas — e as recusas
    passam a ser realmente as primeiras, como o cabecalho deste modulo afirma.
    """
    forma_domain, forma_pack_id = contract_source.formas_do_destino(
        contract_source.read_contracts()
    )
    alvo = destino_de_pack.caminho_do_pack(
        raiz,
        domain,
        pack_id,
        forma_domain=forma_domain,
        forma_pack_id=forma_pack_id,
    )

    # ANTES DO PRIMEIRO BYTE — `04` §8.1 (c).
    destino_de_pack.recusa_se_versionado(alvo)

    gerador = _gerador_do_dominio(domain)
    # SO AGORA a conexao e aberta: as tres recusas ja passaram.
    # `conferir` roda DENTRO de `gerar`: o linter de `02` §6.3 recusa aqui, e um
    # `GM_NOTES` divergente nao chega a existir em disco.
    gabarito = gerador.gerar(
        abre_motor(), pack=pack_id, seed=seed, conta_alvo=conta_alvo
    )

    alvo.mkdir(parents=True, exist_ok=True)
    (alvo / GROUND_TRUTH).write_text(
        yaml.safe_dump(
            gabarito.ground_truth,
            sort_keys=True,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    (alvo / GM_NOTES).write_text(gabarito.gm_notes, encoding="utf-8", newline="\n")
    return alvo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="range-cli", description="Aurora Cyber Range — utilitarios de cenario"
    )
    grupos = parser.add_subparsers(dest="grupo", required=True)

    scenario = grupos.add_parser("scenario", help="operacoes sobre pacote de cenario")
    verbos = scenario.add_subparsers(dest="verbo", required=True)

    mat = verbos.add_parser(
        "materialize",
        help=f"escreve {GROUND_TRUTH} + {GM_NOTES} em scenarios/<domain>/<pack_id>/",
    )
    # POSICIONAIS, e nao opcoes com default: `04` §8.2 exige os dois
    # EXPLICITOS, e opcao com default seria derivacao de contexto com outro
    # nome — o operador deixaria de escrever e o comando escolheria por ele.
    mat.add_argument("domain")
    mat.add_argument("pack_id")
    mat.add_argument("--seed", type=int, required=True, help="RANDOM_SEED da geracao")
    mat.add_argument(
        "--conta-alvo", required=True, help="a conta comprometida, do dataset semeado"
    )

    verbo_lint = verbos.add_parser(
        "lint",
        help="confere um pacote de cenario e relata TODAS as recusas, com posicao",
    )
    verbo_lint.add_argument("path", help="o diretorio do pacote")
    # `--flags` E OPCIONAL, e o default sai do `domain` do MANIFESTO. A razao de
    # isso nao contradizer `04` §8.2 esta em `lint.flags_do_pack`: ali o dominio
    # e campo declarado do arquivo que se pediu para conferir, e nao contexto de
    # onde o comando correu.
    verbo_lint.add_argument(
        "--flags",
        default=None,
        help="o `flags.yaml` do adapter; o default vem do `domain` do manifesto",
    )
    return parser


#: `0` limpo, `2` recusado. O `2` e o mesmo de `materialize` desde a peca 2, e a
#: uniformidade importa porque `04` §8 poe `lint` no CI: um verbo que sinalizasse
#: recusa com `1` e outro com `2` faria o job depender de qual deles falhou.
LIMPO, RECUSADO = 0, 2


def _lint(args) -> int:
    """`range-cli scenario lint <path>`. Le, nao escreve, e nao sobe engine.

    NAO CARREGA O PACK — `varre_pack` roda a mesma lista de passos que
    `load_pack`, e para ai. Construir `LoadedPack` exigiria pack VALIDO, que e
    exatamente o que nao se pode supor de um pacote que se pediu para conferir.
    """
    raiz = Path.cwd()
    pack_dir = Path(args.path)
    try:
        flags = (
            lint_de_cenario.carrega_flags(Path(args.flags))
            if args.flags
            else lint_de_cenario.flags_do_pack(pack_dir, raiz)
        )
        achados = lint_de_cenario.lint(
            pack_dir,
            contracts=contract_source.read_contracts(),
            adapter_flags=flags,
        )
    except (lint_de_cenario.LintRecusado, ContractSourceError) as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO
    except PackError as erro:
        # As recusas de `_abre` — diretorio, `manifest.yaml` ausente, documento
        # ilegivel. Elas nao sao colhidas com as demais, e o docstring de `_abre`
        # diz por que: sem elas nao ha pack sobre o qual relatar coisa alguma.
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO

    if not achados:
        print(f"{pack_dir}: sem achados.")
        return LIMPO

    for linha in lint_de_cenario.relatorio(achados):
        print(linha, file=sys.stderr)
    plural = "achado" if len(achados) == 1 else "achados"
    print(f"{pack_dir}: {len(achados)} {plural}.", file=sys.stderr)
    return RECUSADO


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if (args.grupo, args.verbo) == ("scenario", "lint"):
        return _lint(args)

    if (args.grupo, args.verbo) != ("scenario", "materialize"):  # pragma: no cover
        print(f"subcomando nao implementado: {args.grupo} {args.verbo}", file=sys.stderr)
        return 2

    def abre_motor():
        """A conexao, aberta SO se as recusas passarem.

        `DATABASE_URL` e lida aqui e nao no topo pelo mesmo motivo: um comando
        recusado por forma de `domain` nao deve exigir banco configurado. E ela
        NAO TEM DEFAULT — `engine_do_ambiente` recusa URL ausente por desenho, e
        inventar uma aqui poria o comando a semear contra o banco errado.
        """
        import os

        from domains.academus.api.repositorio import engine_do_ambiente

        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise ComandoRecusado(
                "DATABASE_URL ausente. O gabarito e LIDO da trilha semeada — "
                "`gabarito.gerar` descreve o que EXISTE no banco, e nao o que o "
                "gerador pretendia semear —, entao materializar exige o banco do "
                "exercicio no ar e com o dataset carregado."
            )
        return engine_do_ambiente(url)

    try:
        alvo = materialize(
            args.domain,
            args.pack_id,
            raiz=Path.cwd(),
            abre_motor=abre_motor,
            seed=args.seed,
            conta_alvo=args.conta_alvo,
        )
    except (ComandoRecusado, destino_de_pack.DestinoInvalido) as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return 2

    print(f"{alvo}: {GROUND_TRUTH} e {GM_NOTES} escritos.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
