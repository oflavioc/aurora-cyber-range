#!/usr/bin/env python3
"""P6-7 — a fabrica de producao liga o emissor que a superficie declara.

O QUE ESTA CHECAGEM PROVA
-------------------------
Que a fabrica ASGI de cada servico — a funcao que o `uvicorn --factory` chama no
boot — passa `emissor=` para `montar(...)`, quando a superficie daquele servico
declara ao menos uma rota IMPLEMENTADA com `emite`.

E A P6-7 FECHADA, E A PERGUNTA MUDOU DE FORMA
----------------------------------------------
A pendencia foi aberta assim: *"rota nova pode declarar `emite` e nao chamar
emissor nenhum"*. Escrita desse jeito, a resposta exige ANALISE DE FLUXO — achar,
entre nove handlers, quem chama o quê —, e foi por isso que ela ficou aberta
tres auditorias.

O B2 da sexta auditoria mostrou que a pergunta cara nao era a que faltava. O
defeito real foi mais simples e mais grave: `criar()` da `academus-api` montava
**sem emissor nenhum**, e a unica rota instrumentada da fase respondia normalmente
sem gravar nada. Isso e uma pergunta sobre A FABRICA — um `ast.Call` com uma
palavra-chave —, e e decidivel.

A DIFERENCA, DITA: esta checagem NAO prova que um handler chama o emissor. Ela
prova que o emissor CHEGA na aplicacao. A outra metade continua sendo a P6-7 na
forma original, e o teste que a cobre hoje e
`tests/test_api_emissao_pela_rota.py`, que exercita a rota real.

Junto com `check_hooks_com_emissor.py` — que responde *"alguem constroi este
evento?"* — as tres camadas ficam: o hook declara, alguem emite, e a fabrica
liga. Nenhuma substitui as outras.

POR QUE A GUARDA DE BOOT NAO BASTA
-----------------------------------
`domains/academus/api/app.py::confere_emissor_declarado` recusa o boot quando
falta emissor, e ela e mais forte que esta checagem: roda em execucao. Mas ela so
morde QUANDO O PROCESSO SOBE — e o B1 mostrou o que acontece quando a guarda
esta quebrada: ela nao recusou nada, e o defeito atravessou tres rodadas atras de
testes que pulavam.

Gate estatico e guarda de execucao falham por motivos independentes. E a mesma
razao pela qual `check_api_surface.py` existe ao lado dos testes de rota.

POR QUE EM `scripts/` E NAO EM `tools/`
---------------------------------------
`01` §2 normatiza SEIS verificadores em `tools/`. Um setimo ali contradiria a
contagem que a spec fixa.

Roda no job `arquitetura`, que e stdlib puro — esta checagem tambem e.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Requisito 5 da Fase 0: verificacao nao modifica arquivo algum.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

#: `rotulo -> (fabrica, superficie, produtor)`, relativos a raiz.
#:
#: `produtor` e a CLASSE que a fabrica tem de construir para que as rotas que
#: declaram `emite` gravem de verdade. `None` significa "nao ha servico ainda", e
#: a checagem entao exige que a fabrica NAO exista — servico que nasce sem
#: produtor declarado reprova, que e o gatilho util.
#:
#: A CLASSE E POR SERVICO, e a primeira versao desta checagem errou aqui: ela
#: exigia `emissor=` de todo mundo e reprovou o `range-api`, que emite pelo
#: `InjectEngine` e nao por um argumento `emissor`. Reprovar a arvore por uma
#: convencao que so um servico segue e o defeito que `check_api_surface.py`
#: chama de "lista que descreve o que se deseja".
#:
#: LISTA DECLARADA e nao descoberta por varredura, pelo mesmo motivo do
#: `DECLARED_SURFACE` de `check_store_read_surface.py`: servico novo tem de
#: passar por aqui, e nenhuma heuristica preve o proximo nome de arquivo.
SERVICOS: dict[str, tuple[str, str, str | None]] = {
    # O B2 da sexta auditoria: a fabrica montava sem `Emissor`, e a unica rota
    # instrumentada da fase respondia sem gravar nada.
    "academus-api": (
        "domains/academus/api/processo.py",
        "domains/academus/api_surface.yaml",
        "Emissor",
    ),
    # Quem grava os eventos de exercicio e o `InjectEngine` — `09` §1.1 poe o
    # `inject-engine` como produtor. Nao ha argumento `emissor` aqui, e exigi-lo
    # seria impor a convencao de um adapter ao nucleo.
    "range-api": (
        "range-core/api/processo.py",
        "range-core/api_surface.yaml",
        "InjectEngine",
    ),
    # SEM SERVICO AINDA: `range-core/participant/api/app.py` tem `montar`, e nao
    # tem fabrica — nao ha entrada dele no `docker-compose.yml`. O dia em que
    # nascer um `criar` ali, esta checagem reprova ate que o produtor seja
    # declarado acima, que e exatamente quando a decisao precisa acontecer.
    "participant-api": (
        "range-core/participant/api/app.py",
        "range-core/participant/api_surface.yaml",
        None,
    ),
}

#: A funcao que o `uvicorn --factory` chama.
FABRICA = "criar"

RULE = "P6-7 - a fabrica liga o emissor que a superficie declara"


def _fail(mensagem: str) -> int:
    print(f"{RULE}: {mensagem}", file=sys.stderr)
    return 1


def _rotas_que_emitem(caminho: Path) -> list[str]:
    """As rotas IMPLEMENTADAS que declaram `emite`."""
    documento = parse_yaml(caminho) or {}
    achadas = []
    for rota in documento.get("rotas") or []:
        if rota.get("emite") and rota.get("status") == "implementada":
            achadas.append(
                f"{str(rota.get('method', '')).upper()} {rota.get('path')}"
            )
    return achadas


def _construidos_na_fabrica(arvore: ast.Module) -> set[str] | None:
    """Nomes de classe invocados DENTRO de `criar`. `None` se ela nao existe.

    Distinguir "nao ha fabrica" de "a fabrica nao constroi" e o ponto: a
    primeira e estado declarado, e a segunda e defeito.
    """
    for node in ast.walk(arvore):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name == FABRICA
        ):
            return {
                filho.func.id
                for filho in ast.walk(node)
                if isinstance(filho, ast.Call) and isinstance(filho.func, ast.Name)
            }
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    raiz = Path(argv[0]).resolve() if argv else REPO_ROOT

    problemas: list[str] = []
    conferidos = 0

    for rotulo, (fabrica_rel, superficie_rel, produtor) in sorted(SERVICOS.items()):
        fabrica = raiz / fabrica_rel
        superficie = raiz / superficie_rel

        if not fabrica.is_file() or not superficie.is_file():
            problemas.append(
                f"{rotulo}: `{fabrica_rel}` ou `{superficie_rel}` nao existe. A "
                "lista SERVICOS descreve o que ha; se o servico mudou de lugar, "
                "atualize-a — silencio aqui seria a checagem passando por "
                "ausencia do proprio objeto."
            )
            continue

        arvore = ast.parse(fabrica.read_text(encoding="utf-8"), str(fabrica))
        construidos = _construidos_na_fabrica(arvore)
        conferidos += 1

        if produtor is None:
            if construidos is not None:
                problemas.append(
                    f"{rotulo}: `{fabrica_rel}` GANHOU uma fabrica `{FABRICA}`, e "
                    "SERVICOS o declara sem produtor.\n"
                    "    O servico nasceu: declare ali qual classe grava os "
                    "eventos que a superficie dele promete, ou a primeira rota "
                    "instrumentada subira muda."
                )
            continue

        emitentes = _rotas_que_emitem(superficie)
        if not emitentes:
            continue

        if construidos is None:
            problemas.append(
                f"{rotulo}: a superficie declara `emite` em "
                f"{', '.join(emitentes)}, e `{fabrica_rel}` nao tem `{FABRICA}`. "
                "Ou o servico perdeu a fabrica, ou SERVICOS envelheceu."
            )
            continue

        if produtor not in construidos:
            problemas.append(
                f"{rotulo}: a superficie declara `emite` em "
                f"{', '.join(emitentes)}, e `{FABRICA}` de `{fabrica_rel}` NAO "
                f"constroi `{produtor}`.\n"
                "    As rotas responderiam normalmente e nao gravariam nada. "
                "`00` §5.5: rota instrumentada em silencio e pior que rota nao "
                "instrumentada, porque a ausencia nao aparece — foi o B2 da "
                "sexta auditoria da Fase 6."
            )

    if problemas:
        for problema in problemas:
            print(f"{RULE}: {problema}", file=sys.stderr)
        return 1

    if not conferidos:
        return _fail(
            "nenhum servico conferido. A checagem passaria por vacuidade, que e "
            "o modo de falha dela."
        )

    print(
        f"{RULE}: {conferidos} servico(s) conferido(s); toda fabrica cuja "
        "superficie declara `emite` monta com emissor."
    )
    print(
        "  O que isto NAO prova: que um HANDLER chame o emissor. A checagem ve "
        "a montagem, e nao o fluxo dentro dela — a outra metade da P6-7 e "
        "coberta por `tests/test_api_emissao_pela_rota.py`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
