"""`range-cli` — a superficie de cenario. Tres verbos: `materialize`, `lint` e
`dryrun`.

`04_SCENARIO_SCHEMA.md` §8 declara sete subcomandos; estes sao os tres que
existem. Os demais tem fase: `evidence build` e `evidence verify` sao da Fase
9, e `validate` nao tem entrega propria enquanto `lint` o cobre por dentro —
ver `range_cli/lint.py`.

`dryrun` PERCORRE E NAO AVALIA: ele enumera todos os caminhos de branch (`06`
T12) e recusa o que nao consegue percorrer — quem avalia condicao em exercicio
e o engine. E ele linta ANTES de andar: travessia sobre pack com achados nao
afirma nada, porque os proprios ids e tempos que ela pisa podem ser o defeito.

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
from collections.abc import Mapping
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

#: `08` §7 — `scenarios/<domain>/<pack_id>/evidence/` com o `MANIFEST.json`.
EVIDENCE = "evidence"
MANIFESTO = "MANIFEST.json"

#: O documento que carrega `evidence_release` — `04` §5 e `08` §5.
INJECTS = "injects.yaml"

#: O modo de entrega que um `evidence_release` produz. O valor e do enum
#: `delivery_mode` de `contracts/evidence.schema.yaml`, e o schema recusa
#: qualquer outro — escrever errado aqui falharia na validacao do manifesto,
#: que e o comportamento certo mas a mensagem erraria o endereco.
LIBERADO_POR_INJECT = "released_by_inject"


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
            # SEM quebra de linha por largura: o safe_dump quebraria string
            # longa em flow scalar de duas linhas, e o parser estrito de
            # `tools/` — que `check_synthetic_data.py` (INV-1) aplica sobre
            # `scenarios/` — recusa escalar multilinha por construcao. O
            # produtor nao pode escrever o que o verificador do invariante
            # nao le. Achado da varredura de fechamento da Fase 7, invisivel
            # ate existir um pack em disco (P7-9).
            width=1_000_000,
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

    verbo_dryrun = verbos.add_parser(
        "dryrun",
        help="percorre todos os caminhos de branch, sem UI; recusa o que nao anda",
    )
    verbo_dryrun.add_argument("path", help="o diretorio do pacote")
    # Mesmo contrato de `lint`, pelo mesmo argumento de `lint.flags_do_pack`.
    verbo_dryrun.add_argument(
        "--flags",
        default=None,
        help="o `flags.yaml` do adapter; o default vem do `domain` do manifesto",
    )

    # ---------------------------------------------------------------------
    # `evidence` — o grupo da Fase 9. `08` §7.
    #
    # DOIS VERBOS DE CLASSES DIFERENTES, e a distincao e a de `04` §8.1 (a):
    # `build` ESCREVE (como `materialize`) e fica fora das allowlists de quem
    # opera o repositorio; `verify` so LE e entra nelas — e e por isso que ele
    # nao pode escrever nem "para comparar".
    # ---------------------------------------------------------------------
    evidence = grupos.add_parser("evidence", help="projecao de evidencia — `08`")
    verbos_de_evidencia = evidence.add_subparsers(dest="verbo", required=True)

    verbo_build = verbos_de_evidencia.add_parser(
        "build",
        help=f"projeta o {GROUND_TRUTH} do pack em <pack>/{EVIDENCE}/, com {MANIFESTO}",
    )
    verbo_build.add_argument("path", help="o diretorio do pacote")
    verbo_build.add_argument(
        "--seed",
        type=int,
        required=True,
        help="o RANDOM_SEED que gerou o gabarito; vai para o manifesto",
    )

    verbo_verify = verbos_de_evidencia.add_parser(
        "verify",
        help="confere o pacote de evidencia contra o ground truth; NAO escreve",
    )
    verbo_verify.add_argument("path", help="o diretorio do pacote")
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


def _dryrun(args) -> int:
    """`range-cli scenario dryrun <path>`. Le, nao escreve, e nao sobe engine.

    LINT PRIMEIRO, TRAVESSIA DEPOIS — e a ordem e a garantia. Os achados saem
    no mesmo formato do `lint`, para o autor consertar uma vez; so um pack sem
    achados tem caminhos cuja enumeracao afirma alguma coisa. A recusa de
    travessia (`branch_walk_impossible`) e o que ESTE verbo acrescenta: a
    branch bem-formada que nenhuma camada anterior ve e que nao ensaia.
    """
    from range_core.engine.loader import branching
    from range_core.engine.loader import pack_loader

    raiz = Path.cwd()
    pack_dir = Path(args.path)
    contracts = contract_source.read_contracts()
    try:
        flags = (
            lint_de_cenario.carrega_flags(Path(args.flags))
            if args.flags
            else lint_de_cenario.flags_do_pack(pack_dir, raiz)
        )
        achados = lint_de_cenario.lint(
            pack_dir, contracts=contracts, adapter_flags=flags
        )
    except (lint_de_cenario.LintRecusado, ContractSourceError, PackError) as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO

    if achados:
        for linha in lint_de_cenario.relatorio(achados):
            print(linha, file=sys.stderr)
        plural = "achado" if len(achados) == 1 else "achados"
        print(
            f"{pack_dir}: dryrun recusado — {len(achados)} {plural} de lint. "
            "Travessia sobre pack com achados nao afirma nada.",
            file=sys.stderr,
        )
        return RECUSADO

    documentos = pack_loader.le_documentos(pack_dir, contracts)
    try:
        caminhos = branching.percorre(
            documentos.get("injects.yaml"), documentos.get("branches.yaml")
        )
    except PackError as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO

    if not caminhos:
        print(f"{pack_dir}: sem branches — nenhum caminho a percorrer.")
        return LIMPO

    pontos = []
    for caminho in caminhos:
        if caminho.ponto not in pontos:
            pontos.append(caminho.ponto)
            rotulo = f"linha {caminho.ponto.line!r}" if caminho.ponto.line is not None else "sem linha"
            print(
                f"{caminho.ponto.id} [{rotulo}] @ {caminho.ponto.at_inject} "
                f"-> reconverge {caminho.ponto.reconverge_at}"
            )
        marca = " (default)" if caminho.braco.default else ""
        print(f"  {caminho.braco.id}{marca}: " + " -> ".join(caminho.sequencia))
    plural_p = "ponto" if len(pontos) == 1 else "pontos"
    plural_c = "caminho" if len(caminhos) == 1 else "caminhos"
    print(
        f"{pack_dir}: {len(pontos)} {plural_p} de ramificacao, "
        f"{len(caminhos)} {plural_c}, todos percorridos."
    )
    return LIMPO


def _contexto_de_evidencia(contratos):
    """Os tres insumos do motor, montados do CONTRATO e do dominio.

    O `domain` sai do pack? **Nao, e isto e limite declarado.** Hoje ha um
    adapter com geradores (`academus`), e resolver o pacote de geradores pelo
    `domain` do manifesto exigiria um registro dominio -> pacote que ainda nao
    existe. Quando o segundo adapter tiver geradores, este e o ponto a mudar —
    e o teste que o cobra e o de cobertura da tabela.
    """
    from domains.academus.evidence_generators import geradores

    return {
        "geradores": geradores(contratos),
        "formatos": contract_source.formatos_por_fonte(contratos),
        "banner": contratos["evidence"]["x-aurora-security-constraints"]["banner_text"],
        "campos_do_fato": contract_source.campos_do_fato(contratos),
    }


def _le_ground_truth(pack_dir: Path) -> bytes:
    """Os BYTES do `ground_truth.yaml` — e sobre eles que o hash e feito."""
    alvo = pack_dir / GROUND_TRUTH
    if not alvo.exists():
        raise ComandoRecusado(
            f"{alvo} ausente. A evidencia e PROJECAO do gabarito (`00` §5.3), "
            f"entao sem ele nao ha o que projetar — rode "
            f"`range-cli scenario materialize` antes"
        )
    return alvo.read_bytes()


def _fontes_projetadas(ground_truth_bytes: bytes) -> set[str]:
    """As fontes que este gabarito projeta — pela MESMA funcao que o motor usa.

    `cobertura_de`, e nao uma varredura propria de `projections`: a pergunta
    *"quais fontes este gabarito projeta?"* ja tem dono, e uma segunda resposta
    divergiria dele na primeira regra nova (fato sem `fact_id`, lista vazia,
    `projections` ausente — os tres casos que `cobertura_de` ja decide).
    """
    from importlib import import_module

    elenco = import_module("range_core.evidence.elenco")
    documento = yaml.safe_load(ground_truth_bytes.decode("utf-8")) or {}
    return set(elenco.cobertura_de(documento))


def _entrega_declarada(pack_dir: Path, fontes_projetadas: set[str]) -> dict[str, str]:
    """`fonte -> delivery_mode`, LIDO dos injects do pack — `08` §5.

    M3 DA SEGUNDA AUDITORIA. `montar` sempre soube receber `entrega`, e o CLI
    nunca a passava: **todo manifesto saia `pre_positioned`**, inclusive o de um
    pack cujos injects liberam fonte por `evidence_release`. O manifesto e o que
    o facilitador le para saber o que existe e desde quando (`08` §7), e ele
    afirmava disponibilidade desde o start para fonte que so chega no meio do
    exercicio.

    A LEITURA E DIRETA, E NAO POR `load_pack`. O `evidence build` nao carrega o
    pack: ele projeta o gabarito, e exigir a carga inteira aqui acoplaria a
    projecao a validacao de objetivos, ramificacoes e flags de adapter — coisas
    que nao tem nada a ver com escrever um `.log`. O que se le e UM campo, cuja
    forma o contrato de cenario fixa (`$defs/evidence_release_item`).

    `on_request` NAO TEM COMO SER PRODUZIDO AQUI, e o limite e do contrato, nao
    desta funcao: `evidence_release_item` tem `source` e `window`, e nenhum
    campo de atraso. `08` §5 descreve o terceiro modo, e a forma que o
    expressaria num pack ainda nao existe — quando existir, `atrasos` ja e
    parametro de `montar` e entra por aqui.
    """
    import yaml

    alvo = pack_dir / INJECTS
    if not alvo.exists():
        return {}

    documento = yaml.safe_load(alvo.read_text(encoding="utf-8")) or {}
    entrega: dict[str, str] = {}
    for inject in documento.get("injects") or ():
        if not isinstance(inject, Mapping):
            continue
        for item in inject.get("evidence_release") or ():
            if not isinstance(item, Mapping):
                continue
            fonte = item.get("source")
            if not isinstance(fonte, str):
                continue
            # FONTE LIBERADA QUE O GABARITO NAO PROJETA E RECUSA, e ela e barata
            # de cometer: `evidence_release` e escrito no roteiro de facilitacao,
            # e `projections` no gabarito, por autores e em momentos diferentes.
            # Um inject que libera `firewall` num pack sem fato de firewall
            # promete ao participante um arquivo que nao existe — e a promessa
            # so falha na sala.
            if fonte not in fontes_projetadas:
                raise ComandoRecusado(
                    f"o inject {inject.get('id')!r} libera a fonte {fonte!r} por "
                    f"`evidence_release`, e o ground truth nao projeta nada "
                    f"nela. `08` §5 libera o que existe — as fontes projetadas "
                    f"sao: {', '.join(sorted(fontes_projetadas)) or 'nenhuma'}"
                )
            entrega[fonte] = LIBERADO_POR_INJECT
    return entrega


def _motor_de_evidencia():
    """O modulo `range_core.evidence.build`, resolvido por `sys.modules`.

    **`import_module`, e nao `from range_core.evidence import build`** — pelo
    mesmo motivo que a fabrica de geradores adotou a mesma forma na peca 3, e
    aqui a causa foi medida de novo na correcao da segunda auditoria.

    `from <pacote> import <submodulo>` resolve pelo ATRIBUTO do pacote quando
    ele ja existe, e o harness de prova negativa substitui `sys.modules`. O
    atributo nao acompanha — entao o CLI rodava o modulo ORIGINAL enquanto o
    resto da suite rodava o mutado. O efeito era pior que nao detectar: o
    conjunto vermelho declarado passou a depender da ORDEM em que a suite
    importou o pacote, e a prova negativa ficou intermitente.

    `import_module` consulta `sys.modules` primeiro, entao o modulo vem sempre
    do lugar corrente. Em producao as duas formas sao equivalentes; sob
    substituicao, so uma delas e determinista.
    """
    from importlib import import_module

    return import_module("range_core.evidence.build")


def _evidence_build(args) -> int:
    """`range-cli evidence build <path> --seed N`. ESCREVE."""
    build_de_evidencia = _motor_de_evidencia()

    pack_dir = Path(args.path)
    contratos = contract_source.read_contracts()
    try:
        ground_truth_bytes = _le_ground_truth(pack_dir)
        manifesto = build_de_evidencia.construir(
            ground_truth_bytes,
            destino=pack_dir / EVIDENCE,
            pack_id=pack_dir.name,
            random_seed=args.seed,
            entrega=_entrega_declarada(
                pack_dir, _fontes_projetadas(ground_truth_bytes)
            ),
            **_contexto_de_evidencia(contratos),
        )
    except (ComandoRecusado, ContractSourceError) as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO
    except Exception as erro:  # noqa: BLE001 — as recusas do motor, nomeadas
        # `projetar` levanta `GeradorAusente`, `FonteSemFormato`,
        # `EntidadeInventada` e `IOCEncontrado`. Elas nao herdam de um tronco
        # comum de proposito: cada uma nomeia uma norma diferente, e um tronco
        # convidaria a captura generica que apaga qual delas disparou. Aqui a
        # captura e generica porque este e o LIMITE do processo, e a mensagem
        # original vai inteira para o operador.
        print(f"RECUSADO: {type(erro).__name__}: {erro}", file=sys.stderr)
        return RECUSADO

    print(
        f"{pack_dir / EVIDENCE}: {len(manifesto['sources'])} fonte(s) e {MANIFESTO} "
        f"escritos."
    )
    return LIMPO


def _evidence_verify(args) -> int:
    """`range-cli evidence verify <path>`. SO LE — `04` §8.1 (a)."""
    build_de_evidencia = _motor_de_evidencia()

    pack_dir = Path(args.path)
    contratos = contract_source.read_contracts()
    try:
        achados = build_de_evidencia.conferir(
            pack_dir / EVIDENCE,
            _le_ground_truth(pack_dir),
            contratos=contratos,
            **_contexto_de_evidencia(contratos),
        )
    except (ComandoRecusado, ContractSourceError) as erro:
        print(f"RECUSADO: {erro}", file=sys.stderr)
        return RECUSADO
    except Exception as erro:  # noqa: BLE001 — as recusas do motor, nomeadas
        # L1 DA AUDITORIA DA FASE 9. `conferir` chama `projetar` para reprojetar,
        # e `projetar` levanta `GeradorAusente`, `FonteSemFormato`,
        # `EntidadeInventada` e `IOCEncontrado`. Sem esta captura, um pack cujo
        # gabarito dispare qualquer das quatro devolvia TRACEBACK em vez de
        # `RECUSADO` + rc=2.
        #
        # E o mesmo tratamento que `_evidence_build` ja tinha, pelo mesmo motivo
        # e com a mesma forma: o tipo da excecao vai na mensagem, porque as
        # quatro nomeiam normas diferentes e uma saida generica mandaria o autor
        # do pack procurar.
        #
        # `04` §8.1 (a) poe `evidence verify` na classe dos que SO LEEM, e
        # allowlist de operador depende de codigo de saida estavel — traceback
        # sai com rc=1 e nao distingue "recusado" de "quebrou".
        print(f"RECUSADO: {type(erro).__name__}: {erro}", file=sys.stderr)
        return RECUSADO

    if not achados:
        print(f"{pack_dir / EVIDENCE}: sem achados.")
        return LIMPO

    for achado in achados:
        print(f"  {achado}", file=sys.stderr)
    plural = "achado" if len(achados) == 1 else "achados"
    print(f"{pack_dir / EVIDENCE}: {len(achados)} {plural}.", file=sys.stderr)
    return RECUSADO


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if (args.grupo, args.verbo) == ("evidence", "build"):
        return _evidence_build(args)

    if (args.grupo, args.verbo) == ("evidence", "verify"):
        return _evidence_verify(args)

    if (args.grupo, args.verbo) == ("scenario", "lint"):
        return _lint(args)

    if (args.grupo, args.verbo) == ("scenario", "dryrun"):
        return _dryrun(args)

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
