#!/usr/bin/env python3
"""`06` T9, primeiro criterio — todo hook declarado e EMITIDO por alguem.

O QUE ESTA CHECAGEM PROVA
-------------------------
T9 exige, com a etiqueta **(Fase 6)**: *"cada `event_type` declarado em
`observability_hooks.yaml` e emitido pela acao correspondente"*. Ate aqui nada
perguntava isso. `tools/check_contract_literals.py` confere que o `event_type` do
hook esta no CATALOGO; `scripts/check_api_surface.py` confere `emite` por ROTA
contra o catalogo. Nenhum dos dois pergunta se alguem o emite.

Entao um hook com `event_type` valido e produtor inexistente passava em TODOS os
gates — foi o B1 da quarta auditoria da Fase 6, com `vpn_access_revoked` e um
`producer: federated-identity-simulator` que e da Fase 11.

`04` §6.2 e `09` §4 chamam essa forma de "a falha mais cara possivel": o evento
que nunca dispara e que ninguem percebe ate o exercicio ao vivo. Um hook e uma
PROMESSA de instrumentacao — o objetivo que depender dele por evidencia `auto`
nunca pontua, e nada fica vermelho.

AS QUATRO DIRECOES, E POR QUE IGUALDADE E NAO INCLUSAO
-------------------------------------------------------
    (a) DECLARADO E NAO EMITIDO — o criterio de T9, literal;
    (b) EMITIDO E NAO DECLARADO — a direcao inversa, sem a qual o arquivo vira
        lista de desejos em vez de descricao do que existe. E a mesma forma que
        `check_api_surface.py` ja impoe as rotas, e pelo mesmo motivo: a
        inclusao num sentido so deixa o adapter emitir o que nao declarou;
    (c) PRODUTOR — o `producer` do hook bate com o `PRODUTOR` do modulo que
        emite. Sem isto, o hook pode nomear um servico que nao e quem grava, e a
        trilha diria uma coisa e o codigo outra;
    (d) `payload_fields` — as chaves do dicionario literal de `payload` sao
        EXATAMENTE as declaradas. Ate a Fase 6 isso existia so para
        `audit_query_performed`, num teste escrito a mao.

O QUE ELA VE, E O LIMITE — DECLARADO E NAO OMITIDO
---------------------------------------------------
Ela ve a CONSTRUCAO do evento: `EventDraft(event_type=<CONSTANTE>, ...)` em
`domains/`. Ela **nao** prova que uma rota chama o emissor — isso e analise de
fluxo, e e a P6-7, que segue aberta.

A fraqueza esta dita porque e uma fraqueza: um `Emissor` com metodo que ninguem
chama passa aqui. O que ela fecha e o buraco maior e mais barato de fechar — o
hook cujo produtor NAO EXISTE EM LUGAR NENHUM.

`payload` construido dinamicamente RECUSA em vez de degradar: sem dicionario
literal nao ha como conferir (d), e "nao consegui conferir" nao pode virar "ok".
E a mesma regra que `check_prova_do_seed.py` aplica a ausencia de arquivo.

POR QUE EM `scripts/` E NAO EM `tools/`
---------------------------------------
`01` §2 normatiza SEIS verificadores, todos em `tools/`. Um setimo ali
contradiria a contagem que a spec fixa — mesma decisao de
`check_store_read_surface.py` e `check_insumo_de_metrica.py`.

Roda no job `arquitetura`, que e stdlib puro — esta checagem tambem e.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import YamlError, parse_yaml  # noqa: E402

GERADAS = REPO_ROOT / "contracts" / "generated" / "events.py"


@dataclass(frozen=True)
class Produtor:
    """Uma raiz de instrumentacao: onde o arquivo esta e onde o tipo aparece.

    LISTA DECLARADA, e nao descoberta por varredura — mesmo motivo do `SERVICOS`
    de `check_fabrica_liga_emissor.py` e do `DECLARED_SURFACE` de
    `check_store_read_surface.py`: produtor novo tem de passar por aqui, e
    nenhuma heuristica preve o proximo layout.
    """

    #: Diretorio, relativo a raiz do repositorio.
    raiz: str
    #: Glob do arquivo de hooks dentro dele. Um por adapter em `domains/`; um so
    #: na `participant-api`, que e um servico e nao uma familia.
    padrao: str
    #: A CHAMADA que carrega o `event_type` neste produtor. **Por produtor, e nao
    #: uma constante do modulo** — foi o erro que `check_fabrica_liga_emissor.py`
    #: cometeu na primeira versao e registrou: exigir a convencao de um adapter do
    #: nucleo reprova o que esta certo, e e assim que um gate vira ruido que
    #: alguem desliga.
    #:
    #: No adapter e `EventDraft`, construido no proprio emissor com o tipo fixo.
    #: Na `participant-api` e `_declara` — o corpo comum das nove rotas, que
    #: recebe o `event_type` do handler e o repassa. Ali o `EventDraft` existe,
    #: mas com `event_type=event_type`: uma VARIAVEL, e nao a constante do
    #: catalogo. Procurar `EventDraft` la acharia zero e reprovaria as nove
    #: estando elas corretas.
    chamada: str


#: AS DUAS RAIZES — `09` §6, na forma que o spec-change #52 lhe deu: a
#: instrumentacao e declarada POR PRODUTOR, e nao por diretorio.
#:
#: A segunda entrou no H2 da setima auditoria. Ate ela, esta checagem varria so
#: `domains/` — e a `participant-api`, que e do core (`01` §6) e emite as NOVE
#: declaracoes de `03` §3.4, era estruturalmente invisivel. Medido: T9 cobria um
#: `event_type` de trinta e tres.
PRODUTORES: tuple[Produtor, ...] = (
    Produtor("domains", "*/observability_hooks.yaml", "EventDraft"),
    Produtor("range-core/participant", "observability_hooks.yaml", "_declara"),
)

#: O nome do modulo-constante que nomeia o servico produtor, `09` §1.1.
NOME_DO_PRODUTOR = "PRODUTOR"

RULE = "06 T9 - hook declarado x emissor real"


def _fail(mensagem: str) -> int:
    print(f"{RULE}: {mensagem}", file=sys.stderr)
    return 1


def _rotulo(caminho: Path) -> str:
    """Relativo ao repositorio quando dentro dele, absoluto fora.

    Fora acontece na prova negativa, que monta arvore em diretorio temporario.
    """
    try:
        return caminho.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return caminho.as_posix()


def _constantes_geradas(caminho: Path) -> dict[str, str]:
    """`NOME -> "event_type"`, lido do gerado por AST e nao por import.

    Por AST porque o job `arquitetura` nao instala a aplicacao, de proposito — um
    gate que depende do que ele julga deixa de ser gate. E porque importar o
    modulo gerado faria esta checagem enxergar o que o `sys.path` da maquina
    resolver, e nao o que esta na arvore.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
    constantes: dict[str, str] = {}
    for node in arvore.body:
        alvo = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            alvo, valor = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name):
                alvo, valor = node.targets[0].id, node.value
        if alvo and isinstance(valor, ast.Constant) and isinstance(valor.value, str):
            constantes[alvo] = valor.value
    return constantes


def _hooks(caminho: Path) -> list[dict]:
    documento = parse_yaml(caminho) or {}
    return list(documento.get("hooks") or [])


class _Emissao:
    """Uma construcao de evento achada na arvore do adapter."""

    def __init__(
        self,
        event_type: str,
        arquivo: Path,
        linha: int,
        produtor: str | None,
        payload: frozenset[str] | None,
    ) -> None:
        self.event_type = event_type
        self.arquivo = arquivo
        self.linha = linha
        self.produtor = produtor
        #: `None` quando o `payload` nao e dicionario literal — ver o cabecalho.
        self.payload = payload


def _produtor_da_raiz(raiz: Path) -> str | None:
    """O `PRODUTOR` da raiz, quando ele e UNICO nela.

    Existe para a `participant-api`, onde a chamada que carrega o tipo esta em
    `api/app.py` e a constante `PRODUTOR` em `api/emissor.py` — modulos irmaos do
    mesmo servico. Sem isto a direcao (c) ficaria muda ali, e um hook poderia
    nomear um servico que nao e quem grava.

    **Unico, ou nada.** Dois `PRODUTOR` distintos sob a mesma raiz nao dizem qual
    vale, e escolher um faria a checagem afirmar o que nao sabe.
    """
    achados = set()
    for caminho in sorted(raiz.rglob("*.py")):
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
        except (OSError, SyntaxError):
            continue
        nome = _produtor_do_modulo(arvore)
        if nome is not None:
            achados.add(nome)
    return achados.pop() if len(achados) == 1 else None


def _produtor_do_modulo(arvore: ast.Module) -> str | None:
    for node in arvore.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            alvo = node.targets[0]
            if (
                isinstance(alvo, ast.Name)
                and alvo.id == NOME_DO_PRODUTOR
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                return node.value.value
    return None


def _emissoes(
    raiz: Path, constantes: dict[str, str], chamada: str
) -> list[_Emissao]:
    """Toda `<chamada>(...)` sob `raiz` que carregue uma constante do catalogo.

    O TIPO E PROCURADO NAS DUAS POSICOES, e a razao e o segundo produtor. No
    adapter ele vem por palavra-chave — `EventDraft(event_type=AUDIT_QUERY_...)`.
    Na `participant-api` ele e o quarto POSICIONAL de `_declara(request, corpo,
    rota, INCIDENT_DECLARED)`, porque quem escolhe o tipo e o handler da rota.

    Ler so a palavra-chave acharia zero no segundo e reprovaria as nove estando
    elas corretas — o defeito que a primeira versao de
    `check_fabrica_liga_emissor.py` cometeu e registrou.

    O `payload` continua sendo lido so por palavra-chave: quando o tipo chega
    posicionalmente, nao ha dicionario literal ao alcance, e a direcao (d) fica
    `None` — "nao ha o que conferir", que e diferente de "nao consegui conferir".
    """
    achadas: list[_Emissao] = []
    produtor_da_raiz = _produtor_da_raiz(raiz)
    for caminho in sorted(raiz.rglob("*.py")):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
        produtor = _produtor_do_modulo(arvore) or produtor_da_raiz
        for node in ast.walk(arvore):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == chamada
            ):
                continue
            argumentos = {
                kw.arg: kw.value for kw in node.keywords if kw.arg is not None
            }
            tipo = argumentos.get("event_type")
            if not (isinstance(tipo, ast.Name) and tipo.id in constantes):
                # Literal de `event_type` ja e barrado pelo invariante 2, em
                # `tools/check_contract_literals.py`. Segunda autoridade sobre o
                # mesmo fato daria duas mensagens para um defeito so.
                tipo = _constante_posicional(node, constantes)
            if tipo is None:
                continue
            achadas.append(
                _Emissao(
                    event_type=constantes[tipo.id],
                    arquivo=caminho,
                    linha=node.lineno,
                    produtor=produtor,
                    payload=_chaves_do_payload(argumentos.get("payload")),
                )
            )
    return achadas


def _constante_posicional(
    node: ast.Call, constantes: dict[str, str]
) -> ast.Name | None:
    """A UNICA constante do catalogo entre os argumentos posicionais.

    Exige unicidade: duas numa chamada so seriam ambiguidade, e escolher a
    primeira faria a checagem afirmar sobre um tipo que ela nao sabe ser o
    emitido. Nenhuma e o caso normal de uma chamada que nao emite.
    """
    achadas = [
        arg
        for arg in node.args
        if isinstance(arg, ast.Name) and arg.id in constantes
    ]
    return achadas[0] if len(achadas) == 1 else None


def _chaves_do_payload(no: ast.AST | None) -> frozenset[str] | None:
    """As chaves do dicionario LITERAL. `None` quando nao ha como saber."""
    if not isinstance(no, ast.Dict):
        return None
    chaves = set()
    for chave in no.keys:
        if not isinstance(chave, ast.Constant) or not isinstance(chave.value, str):
            return None
        chaves.add(chave.value)
    return frozenset(chaves)


def _confere(adapter: str, hooks: list[dict], emissoes: list[_Emissao]) -> list[str]:
    problemas: list[str] = []
    declarados = {}
    for indice, hook in enumerate(hooks):
        tipo = hook.get("event_type")
        if not isinstance(tipo, str):
            problemas.append(
                f"{adapter}: hook #{indice} sem `event_type` legivel. O arquivo e "
                "o mapa entre acao e catalogo; entrada sem tipo nao mapeia nada."
            )
            continue
        declarados[tipo] = hook

    emitidos: dict[str, list[_Emissao]] = {}
    for emissao in emissoes:
        emitidos.setdefault(emissao.event_type, []).append(emissao)

    # (a) DECLARADO E NAO EMITIDO — o criterio de T9.
    for tipo in sorted(set(declarados) - set(emitidos)):
        produtor = declarados[tipo].get("producer")
        problemas.append(
            f"{adapter}: `{tipo}` e declarado em `observability_hooks.yaml` "
            f"(producer: {produtor!r}) e NINGUEM o emite.\n"
            f"    `06` T9 exige que todo `event_type` do arquivo seja emitido "
            "pela acao correspondente. Hook sem emissor e promessa de "
            "instrumentacao: o objetivo que dependa dele por evidencia `auto` "
            "nunca pontua, e nada fica vermelho ate o exercicio ao vivo "
            "(`04` §6.2, `09` §4).\n"
            "    Ou a acao chega neste commit, ou o hook sai do arquivo e volta "
            "com o produtor dela."
        )

    # (b) EMITIDO E NAO DECLARADO — a direcao inversa.
    for tipo in sorted(set(emitidos) - set(declarados)):
        onde = emitidos[tipo][0]
        problemas.append(
            f"{adapter}: `{tipo}` e emitido em "
            f"{_rotulo(onde.arquivo)}:{onde.linha} e NAO esta declarado em "
            "`observability_hooks.yaml`.\n"
            "    `09` §6 poe o mapa acao -> `event_type` naquele arquivo. "
            "Emissao nao declarada faz o mapa descrever menos do que o adapter "
            "faz, e o que nao esta no mapa nao chega ao desenho de exercicio."
        )

    for tipo in sorted(set(declarados) & set(emitidos)):
        hook = declarados[tipo]
        for emissao in emitidos[tipo]:
            # (c) PRODUTOR.
            declarado = hook.get("producer")
            if emissao.produtor is not None and declarado != emissao.produtor:
                problemas.append(
                    f"{adapter}: `{tipo}` declara `producer: {declarado!r}` e "
                    f"quem emite e {emissao.produtor!r} "
                    f"({_rotulo(emissao.arquivo)}:{emissao.linha}).\n"
                    "    `09` §1.1 poe o servico no envelope; hook que nomeia "
                    "outro faz a trilha dizer uma coisa e o codigo outra."
                )

            # (d) `payload_fields`.
            campos = hook.get("payload_fields")
            if campos is None:
                continue
            if emissao.payload is None:
                problemas.append(
                    f"{adapter}: `{tipo}` declara `payload_fields` e o `payload` "
                    f"de {_rotulo(emissao.arquivo)}:{emissao.linha} nao e "
                    "dicionario literal — nao ha como conferir.\n"
                    "    RECUSA em vez de degradar: 'nao consegui conferir' "
                    "virando 'ok' e como o hook passa a descrever um evento que "
                    "nao e o emitido."
                )
                continue
            declarados_campos = frozenset(campos)
            if declarados_campos != emissao.payload:
                faltando = sorted(declarados_campos - emissao.payload)
                sobrando = sorted(emissao.payload - declarados_campos)
                problemas.append(
                    f"{adapter}: `{tipo}` — `payload_fields` e o payload emitido "
                    f"divergem em {_rotulo(emissao.arquivo)}:{emissao.linha}. "
                    f"Declarado e nao emitido: {faltando}. "
                    f"Emitido e nao declarado: {sobrando}.\n"
                    "    Acrescentar campo no emissor sem declarar aqui faz o "
                    "hook descrever um evento que nao e o emitido."
                )
    return problemas


def main(argv: list[str] | None = None) -> int:
    """Sem argumento, confere a arvore real. Com um caminho, confere aquele `domains/`.

    O CAMINHO OPCIONAL EXISTE PARA A PROVA NEGATIVA, e nao afeta garantia
    nenhuma: e parametro de CLI. A alternativa era o probe plantar o defeito no
    arquivo REAL e restaurar — fragil pelo motivo obvio, e falha no meio deixa a
    arvore suja.
    """
    argv = sys.argv[1:] if argv is None else argv

    # O CAMINHO DE CLI SUBSTITUI AS RAIZES POR UMA, na forma de `domains/`. E o
    # contrato que a prova negativa usa desde a peca 3A, e ele nao muda com a
    # segunda raiz: o probe monta um adapter inteiro em temporario e aponta a
    # checagem para ele. Manter a forma de `domains/` aqui e o que faz o probe
    # continuar exercitando as quatro direcoes sem conhecer a tabela.
    produtores = (
        (Produtor(argv[0], "*/observability_hooks.yaml", "EventDraft"),)
        if argv
        else PRODUTORES
    )

    try:
        constantes = _constantes_geradas(GERADAS)
    except (OSError, SyntaxError) as erro:
        return _fail(f"nao consegui ler {_rotulo(GERADAS)}: {erro}")
    if not constantes:
        return _fail(
            f"{_rotulo(GERADAS)} nao declara constante nenhuma. Sem elas esta "
            "checagem nao reconheceria emissao alguma e passaria por vacuidade."
        )

    # A VACUIDADE E CONFERIDA POR RAIZ, e nao no total. Raiz declarada que nao
    # devolve arquivo nenhum e produtor cujo arquivo SUMIU — e no total ela seria
    # coberta pela outra, que e como a instrumentacao de um servico inteiro
    # desapareceria sem nada acusar.
    achados: list[tuple[Produtor, Path]] = []
    for produtor in produtores:
        base = Path(produtor.raiz)
        if not base.is_absolute():
            base = REPO_ROOT / base
        if not base.is_dir():
            return _fail(
                f"{_rotulo(base)} nao existe, e a tabela PRODUTORES o declara. "
                "Se o servico mudou de lugar, atualize a tabela — silencio aqui "
                "seria a checagem passando por ausencia do proprio objeto."
            )
        arquivos = sorted(base.glob(produtor.padrao))
        if not arquivos:
            return _fail(
                f"nenhum `observability_hooks.yaml` em {_rotulo(base)} "
                f"(padrao {produtor.padrao!r}). A checagem passaria por "
                "vacuidade, que e o modo de falha que ela existe para nao ter."
            )
        achados.extend((produtor, caminho) for caminho in arquivos)

    problemas: list[str] = []
    total_hooks = 0
    total_emissoes = 0
    for produtor, caminho in achados:
        adapter = caminho.parent.name
        try:
            hooks = _hooks(caminho)
        except YamlError as erro:
            problemas.append(f"{adapter}: {erro}")
            continue
        try:
            emissoes = _emissoes(caminho.parent, constantes, produtor.chamada)
        except (OSError, SyntaxError) as erro:
            problemas.append(f"{adapter}: nao consegui varrer o adapter ({erro})")
            continue
        total_hooks += len(hooks)
        total_emissoes += len(emissoes)
        problemas.extend(_confere(adapter, hooks, emissoes))

    if problemas:
        for problema in problemas:
            print(f"{RULE}: {problema}", file=sys.stderr)
        return 1

    print(
        f"{RULE}: {total_hooks} hook(s) em {len(achados)} produtor(es), "
        f"{total_emissoes} emissao(oes) achada(s); declaracao e emissao batem nas "
        "quatro direcoes (declarado x emitido, produtor, payload)."
    )
    print(
        "  O que isto NAO prova: que alguma ROTA chame o emissor. A checagem ve "
        "a CONSTRUCAO do evento, e nao o fluxo que a alcanca — e a P6-7."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
