#!/usr/bin/env python3
"""A superficie da `academus-api` e exatamente a declarada — nas duas direcoes.

O QUE ESTA CHECAGEM EXISTE PARA IMPEDIR
----------------------------------------
Uma lista de rotas escrita antes do codigo **subestima**, e uma checagem que so
compara "o declarado existe?" transforma a lista em documentacao com sintaxe de
verificador: ela fica verde enquanto a rota que ninguem previu passa ao lado.

Por isso a igualdade e nos DOIS SENTIDOS, e o sentido que importa e o inverso do
obvio:

  rota IMPLEMENTADA e ausente da declaracao         -> reprova
  rota declarada `implementada` e ausente do codigo -> reprova
  rota declarada `planejada` que JA existe no codigo -> reprova

O terceiro eixo e o que impede `planejada` de virar esconderijo permanente:
assim que a rota nasce, a entrada e promovida no mesmo commit. Sem ele, bastaria
declarar tudo como planejado para a checagem nunca cobrar nada.

E o mesmo desenho de `check_store_read_surface.py`, e pelo mesmo motivo — foi a
igualdade nas duas direcoes que fez aquela funcionar.

O QUE MAIS ELA COBRA
--------------------
- **flag de rota existe no adapter.** Mesma regra que o loader aplica ao pack e
  que `check_spec_flags.py` aplica a spec: a terceira porta pela qual um nome de
  flag entra no sistema passa a ter a mesma guarda que as outras duas.
- **papel de rota existe na lista de papeis de dominio.** Papel de EXERCICIO —
  facilitador, operador, avaliador (`03` §7) — e recusado por nome: se aparecer
  aqui, o adapter passou a conhecer desenho de exercicio.

O QUE A PECA 4 ACRESCENTOU, e por que como EXTENSAO e nao como checagem nova
-----------------------------------------------------------------------------
O JWT e a segunda porta pela qual desenho de exercicio entra no adapter, e
nenhum verificador de import a enxerga: um token com `persona: facilitador` nao
importa nada de lugar nenhum. Escrever um segundo verificador para o claim
criaria duas listas sobre a MESMA fronteira — a classe D4 do catalogo —, e a que
diverge em silencio e sempre a que ninguem esta olhando.

- **papel de EXERCICIO dentro de `papeis_de_dominio`.** Era o buraco da peca 2:
  ela recusava o papel na ROTA, e a lista de origem passava. Agora que
  `emitir_token` LE essa lista em tempo de execucao, o buraco virou caminho — e
  fechado aqui, `emitir_token(sub, "facilitador")` deixa de ser proibido e passa
  a ser inexprimivel.
- **`token.claims` == as chaves que o codigo assina**, nas duas direcoes, por AST
  sobre `range-core/api/tokens.py::_payload`. Claim escrito e nao declarado
  reprova, que e a direcao que importa.
- **a funcao que monta o payload precisa existir.** Sem esta assercao, renomear
  `_payload` faria o laco nao casar com nada e a checagem devolver "as claims
  batem" — verdadeiro por vacuidade. Foi o terceiro defeito que os probes da
  peca 3 acharam, na propria checagem daquela peca, e esta linha existe porque
  aquilo aconteceu.
- **`publica` x `papeis`.** `papeis: []` significa NINGUEM. Rota aberta se
  declara com `publica: true`, e as duas incoerencias reprovam.
- **degradacao nao vaza para a peca 4.** Enquanto nenhuma rota IMPLEMENTADA
  declarar flag, nenhum modulo de `api/` pode importar `range_core.state`. E a
  D4 sendo guardada em vez de prometida: no dia em que a peca 5 implementar a
  primeira rota com flag, a regra sai de cena sozinha.

COMO ELA ENXERGA A ROTA IMPLEMENTADA
-------------------------------------
Por **AST**, sobre `domains/<adapter>/api/`, procurando decorador de rota na
forma `@algo.<metodo>("/caminho")` — a forma do FastAPI, que `02` §7 fixa como a
stack da `academus-api`. Nao ha rota nenhuma hoje, e a checagem ja roda: e a
diferenca entre escrever a obrigacao antes e escrever a lista antes.

**O limite, declarado:** rota registrada em tempo de execucao — `add_api_route`
com caminho calculado — nao e vista por AST. E a mesma excecao que
`01` §2 admite para varredura lexica de TypeScript: a alternativa seria importar
a aplicacao dentro do verificador, e um gate que importa o que julga deixa de ser
gate. A forma decorada e a unica usada, e esta checagem so vale enquanto isso
continuar verdade.

Stdlib pura — le YAML pelo parser estrito de `tools/`. Roda no job `arquitetura`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

DOMAINS = REPO_ROOT / "domains"

RULE = "superficie da api x rotas implementadas"

#: Metodos HTTP que contam como declaracao de rota.
METODOS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

#: Papeis de EXERCICIO — `03` §7. Recusados na superficie de dominio por nome.
#:
#: Nao e lista de palavras proibidas por precaucao: sao exatamente os tres que a
#: spec define, e a confusao entre eles e os de dominio e o que poe desenho de
#: exercicio dentro do adapter.
PAPEIS_DE_EXERCICIO = frozenset({"facilitador", "operador", "avaliador"})

#: Onde as claims sao montadas. Caminho e nome sao constantes AQUI, e nao no
#: YAML do adapter: um arquivo de `domains/` apontando para dentro do core
#: inverteria a direcao que o invariante 1 protege.
MODULO_DO_TOKEN = "range-core/api/tokens.py"
FUNCAO_DO_PAYLOAD = "_payload"

#: O que um claim NAO pode se chamar. Os tres papeis, mais a palavra com que
#: `03` §7 nomeia o participante do exercicio.
VOCABULARIO_DE_EXERCICIO = PAPEIS_DE_EXERCICIO | {"persona"}

#: O modulo do core que so o motor de degradacao pode importar. Ver o cabecalho.
ESTADO_DE_SIMULACAO = "range_core.state"

#: O UNICO modulo de `api/` autorizado a ler estado de simulacao.
MOTOR_DA_DEGRADACAO = "degradacao.py"

#: Vocabulario FECHADO da degradacao declarativa — peca 5, D4.
CONDICOES = frozenset({"ligada", "proporcional"})
EFEITOS = frozenset({"recusa", "latencia"})

#: `condicao -> tipo de flag que ela exige`, conferido contra `flags.yaml`.
#:
#: Sem isto, `ligada` sobre uma flag de 0 a 1 degradaria com `0.0` — que e o
#: mundo normal —, e o efeito ficaria ligado o exercicio inteiro sem ninguem
#: entender por que. E o unico ponto desta fase em que o TIPO da flag muda a
#: forma do efeito, e por isso ele e conferido em vez de lembrado.
TIPO_EXIGIDO = {"ligada": "boolean", "proporcional": "number"}

#: As duas regras de escopo de objeto — P3-3. Nao ha uma terceira.
REGRAS_DE_ESCOPO = frozenset({"proprio", "titular"})

#: PALAVRAS QUE A MENSAGEM AO PARTICIPANTE NAO PODE CONTER.
#:
#: A sala precisa VER o sistema cair, e nao ler um aviso dizendo que ele foi
#: derrubado. Uma resposta que se explica transforma exercicio em demonstracao e
#: destroi a assimetria que `00` §5 chama de desenho.
#:
#: A lista e curta e nomeia o mecanismo, nao o assunto: "indisponivel" e
#: legitimo, "flag" nao e.
VOCABULARIO_DE_MECANISMO = (
    "flag",
    "simulac",
    "simulaç",
    "exercicio",
    "exercício",
    "inject",
    "aurora",
    "range",
    "cenario",
    "cenário",
)


def _superficies() -> list[tuple[str, Path, dict]]:
    """`(adapter, caminho, documento)` para cada `api_surface.yaml` declarado."""
    achadas = []
    for caminho in sorted(DOMAINS.glob("*/api_surface.yaml")):
        achadas.append((caminho.parent.name, caminho, parse_yaml(caminho) or {}))
    return achadas


def _flags_declaradas(adapter: str) -> dict[str, str]:
    """`nome -> type` de cada flag do adapter.

    O TIPO passou a importar na peca 5: `condicao: ligada` sobre flag `number` e
    o defeito que a checagem precisa enxergar, e um `set` de nomes nao teria com
    que compara-lo.
    """
    caminho = DOMAINS / adapter / "flags.yaml"
    if not caminho.is_file():
        return {}
    return {
        f["name"]: str(f.get("type", ""))
        for f in (parse_yaml(caminho) or {}).get("flags") or []
    }


def rotas_implementadas(raiz_api: Path) -> set[tuple[str, str]]:
    """`(METODO, caminho)` de cada rota decorada sob `api/`.

    Aceita `@app.get("/x")`, `@router.post("/x")` e qualquer receptor: o que
    identifica a rota e o ATRIBUTO ser um metodo HTTP e o primeiro argumento ser
    string literal. Caminho calculado nao e visto — ver o limite no cabecalho.
    """
    achadas: set[tuple[str, str]] = set()
    if not raiz_api.is_dir():
        return achadas

    for arquivo in sorted(raiz_api.rglob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), str(arquivo))
        for node in ast.walk(arvore):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorador in node.decorator_list:
                if not isinstance(decorador, ast.Call):
                    continue
                func = decorador.func
                if not isinstance(func, ast.Attribute) or func.attr not in METODOS:
                    continue
                if not decorador.args:
                    continue
                primeiro = decorador.args[0]
                if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                    achadas.add((func.attr.upper(), primeiro.value))
    return achadas


def claims_assinadas(caminho: Path) -> list[str] | None:
    """As chaves do dicionario que `_payload` devolve. `None` se ela nao existe.

    `None` E DISTINTO DE LISTA VAZIA, e a diferenca e a anti-vacuidade: funcao
    ausente precisa reprovar, e uma funcao que devolvesse `[]` faria a
    comparacao "nenhum claim escrito" parecer um estado legitimo.

    Le o `ast.Dict` de um `return` — literal numa expressao unica. Payload
    montado com `update()` nao e visto, e o docstring de `_payload` diz isso do
    outro lado.
    """
    if not caminho.is_file():
        return None

    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
    for node in ast.walk(arvore):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != FUNCAO_DO_PAYLOAD:
            continue
        for filho in ast.walk(node):
            if isinstance(filho, ast.Return) and isinstance(filho.value, ast.Dict):
                return [
                    chave.value
                    for chave in filho.value.keys
                    if isinstance(chave, ast.Constant) and isinstance(chave.value, str)
                ]
        return []
    return None


def modulos_que_importam(raiz_api: Path, prefixo: str) -> set[str]:
    """Modulos de `api/` que importam `prefixo` ou algo abaixo dele, por AST.

    Cobre `import a.b...` e `from a.b... import`, que e o alcance honesto:
    import dinamico por `importlib` nao e visto, e o limite esta declarado aqui
    pelo mesmo motivo que o limite de rota dinamica esta no cabecalho.
    """
    achados: set[str] = set()
    if not raiz_api.is_dir():
        return achados

    for arquivo in sorted(raiz_api.rglob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), str(arquivo))
        for node in ast.walk(arvore):
            alvos: list[str] = []
            if isinstance(node, ast.Import):
                alvos = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                alvos = [node.module or ""]
            for alvo in alvos:
                if alvo == prefixo or alvo.startswith(f"{prefixo}."):
                    achados.add(arquivo.name)
    return achados


def verifica_token(
    claims_declaradas: list[str],
    claims_no_codigo: list[str] | None,
) -> list[str]:
    """`token.claims` x o que o codigo assina. Tudo por parametro."""
    problemas: list[str] = []

    if claims_no_codigo is None:
        return [
            f"{MODULO_DO_TOKEN}: `{FUNCAO_DO_PAYLOAD}` nao existe.\n"
            "    Sem ela a comparacao de claims nao casa com nada e a checagem "
            "passa por VACUIDADE. Renomeou? Atualize a declaracao."
        ]

    for claim in sorted(set(claims_no_codigo) - set(claims_declaradas)):
        problemas.append(
            f"claim {claim!r} e assinado por {MODULO_DO_TOKEN} e ausente de "
            "`token.claims`.\n"
            "    E a direcao que importa: e por ela que persona de exercicio "
            "entraria no token sem nenhum verificador de import notar."
        )

    for claim in sorted(set(claims_declaradas) - set(claims_no_codigo)):
        problemas.append(
            f"claim {claim!r} declarado em `token.claims` e o codigo nao o "
            "assina. Declaracao orfa reprova."
        )

    for claim in sorted(set(claims_declaradas) | set(claims_no_codigo)):
        if claim.lower() in VOCABULARIO_DE_EXERCICIO:
            problemas.append(
                f"claim {claim!r} e vocabulario de EXERCICIO (`03` §7). Token de "
                "dominio nao carrega persona de exercicio — D2."
            )

    return problemas


def verifica_degradacao(
    declaradas: list[dict],
    tipos_de_flag: dict[str, str],
) -> list[str]:
    """A degradacao declarativa da peca 5 — D4. Tudo por parametro.

    ESTA FUNCAO SUBSTITUIU a regra de transicao da peca 4, que dizia *"enquanto
    nenhuma rota implementada declarar flag, `api/` nao le estado"*. Aquela era a
    cerca de uma peca que nao degradava, e ela **se calaria sozinha** no momento
    em que a peca 5 declarasse a primeira flag — o que e exatamente o problema:
    uma regra que evapora no dia em que o assunto dela comeca a existir.

    O que ficou no lugar e permanente e mais estreito: `verifica_imports` diz
    que SO o motor de degradacao le estado, e nenhum modulo de `api/` importa
    constante de flag. A cerca virou porta.
    """
    problemas: list[str] = []

    for rota in declaradas:
        chave = f"{str(rota.get('method', '')).upper()} {rota.get('path')}"
        entradas = rota.get("degradacao") or []

        if not isinstance(entradas, list):
            problemas.append(
                f"{chave}: `degradacao` e prosa, e prosa nao executa.\n"
                "    Desde a peca 5 e lista de entradas com `flag`, `condicao`, "
                "`efeito` — a mesma familia dos `effects` do pack."
            )
            continue

        declaradas_na_rota = set(rota.get("flags") or [])
        usadas = {str(e.get("flag")) for e in entradas}

        for flag in sorted(usadas - declaradas_na_rota):
            problemas.append(
                f"{chave}: degrada por {flag!r}, que nao esta em `flags`.\n"
                "    E a porta que a conferencia de nome de flag existe para "
                "fechar: efeito sobre flag nao declarada nao passa por ela."
            )
        for flag in sorted(declaradas_na_rota - usadas):
            problemas.append(
                f"{chave}: declara {flag!r} em `flags` e nao diz o que ela faz.\n"
                "    Flag consumida sem efeito e promessa que ninguem cumpre — e "
                "a rota apareceria no wallboard como degradada sem degradar."
            )

        for entrada in entradas:
            problemas.extend(_verifica_entrada(chave, entrada, tipos_de_flag))

    return problemas


def _verifica_entrada(chave: str, entrada: dict, tipos_de_flag: dict[str, str]) -> list[str]:
    """Uma entrada de `degradacao:` — vocabulario, tipo da flag, e a mensagem."""
    problemas: list[str] = []
    flag = str(entrada.get("flag"))
    condicao = entrada.get("condicao")
    efeito = entrada.get("efeito")

    if condicao not in CONDICOES:
        problemas.append(
            f"{chave}: `condicao: {condicao!r}` fora de {sorted(CONDICOES)}. "
            "Vocabulario fechado, como o catalogo de `event_type`: valor que "
            "ninguem implementou vira degradacao que nao acontece."
        )
    if efeito not in EFEITOS:
        problemas.append(
            f"{chave}: `efeito: {efeito!r}` fora de {sorted(EFEITOS)}."
        )

    tipo_real = tipos_de_flag.get(flag)
    exigido = TIPO_EXIGIDO.get(str(condicao))
    if tipo_real and exigido and tipo_real != exigido:
        problemas.append(
            f"{chave}: `{condicao}` exige flag `{exigido}`, e {flag!r} e "
            f"`{tipo_real}`.\n"
            "    `ligada` sobre flag de 0 a 1 degradaria com 0.0, que e o mundo "
            "normal — e o efeito ficaria ligado o exercicio inteiro."
        )

    if efeito == "recusa":
        status = entrada.get("status")
        if not isinstance(status, int) or not 400 <= status <= 599:
            problemas.append(
                f"{chave}: `recusa` com `status: {status!r}`, que nao e codigo de "
                "erro HTTP."
            )
        if not str(entrada.get("mensagem") or "").strip():
            problemas.append(
                f"{chave}: `recusa` sem `mensagem`.\n"
                "    O item 2 da DoD pede mensagem de NEGOCIO, e nao 403 seco: "
                "quem recebe e um professor no meio de um lancamento."
            )
    elif efeito == "latencia":
        if not isinstance(entrada.get("segundos"), (int, float)) or entrada["segundos"] <= 0:
            problemas.append(
                f"{chave}: `latencia` com `segundos: {entrada.get('segundos')!r}`. "
                "Latencia de zero e degradacao que nao se observa."
            )

    problemas.extend(_verifica_mensagem(chave, entrada, tipos_de_flag))
    return problemas


def _verifica_mensagem(chave: str, entrada: dict, tipos_de_flag: dict[str, str]) -> list[str]:
    """A mensagem nao pode explicar a si mesma. Ver o cabecalho."""
    mensagem = str(entrada.get("mensagem") or "")
    if not mensagem:
        return []

    problemas: list[str] = []
    baixa = mensagem.lower()

    for nome in sorted(tipos_de_flag):
        if nome.lower() in baixa:
            problemas.append(
                f"{chave}: a mensagem nomeia a flag {nome!r}.\n"
                "    A sala precisa VER o sistema cair, nao ler um aviso dizendo "
                "que ele foi derrubado."
            )

    for palavra in VOCABULARIO_DE_MECANISMO:
        if palavra in baixa:
            problemas.append(
                f"{chave}: a mensagem contem {palavra!r}, que e vocabulario de "
                "MECANISMO.\n"
                "    Resposta que se explica transforma exercicio em "
                "demonstracao. `flags.yaml` ja escreve a apresentacao em "
                "linguagem de negocio, no campo `effect_ui` — e essa a lingua."
            )

    return problemas


def verifica_escopo(declaradas: list[dict]) -> list[str]:
    """A regra de objeto — P3-3. Papel do mapa tem de ser papel da rota."""
    problemas: list[str] = []
    for rota in declaradas:
        chave = f"{str(rota.get('method', '')).upper()} {rota.get('path')}"
        papeis = set(rota.get("papeis") or [])
        for papel, regra in (rota.get("escopo") or {}).items():
            if regra not in REGRAS_DE_ESCOPO:
                problemas.append(
                    f"{chave}: escopo {regra!r} fora de {sorted(REGRAS_DE_ESCOPO)}.\n"
                    "    Sao duas regras e nao ha uma terceira: `proprio` (o "
                    "recurso E o sujeito) e `titular` (o recurso PERTENCE a ele)."
                )
            if papel not in papeis:
                problemas.append(
                    f"{chave}: escopo declarado para {papel!r}, que nao esta nos "
                    "papeis da rota.\n"
                    "    Regra que nunca sera avaliada e regra que parece "
                    "proteger e nao protege."
                )
    return problemas


def verifica_imports(
    modulos_com_estado: set[str],
    modulos_com_flags_geradas: set[str],
) -> list[str]:
    """O handler nao tem flag ao alcance. E isso e o que faz a D4 valer.

    Detectar `if flag:` num handler seria a checagem obvia e a fraca — bastaria
    escrever o `if` de outro jeito. O que esta afirmado aqui e mais forte: o
    handler **nao tem por onde** obter uma flag. Nao ha estado de simulacao no
    modulo, e nao ha constante de flag importada.
    """
    problemas: list[str] = []

    for modulo in sorted(modulos_com_estado - {MOTOR_DA_DEGRADACAO}):
        problemas.append(
            f"{modulo}: importa `{ESTADO_DE_SIMULACAO}`, e so "
            f"`{MOTOR_DA_DEGRADACAO}` pode.\n"
            "    Estado ao alcance do handler e `if flag:` esperando para "
            "acontecer. A degradacao e declarada na rota e aplicada por "
            "dependencia global."
        )

    for modulo in sorted(modulos_com_flags_geradas):
        problemas.append(
            f"{modulo}: importa as constantes de flag geradas.\n"
            "    O nome da flag chega como DADO da declaracao, e nao por import "
            "— a mesma forma que faz o core receber `flag_defaults` em vez de "
            "conhecer flag de dominio."
        )

    return problemas


def verifica(
    declaradas: list[dict],
    implementadas: set[tuple[str, str]],
    papeis_de_dominio: set[str],
    flags_do_adapter: set[str],
) -> list[str]:
    """As asserções sobre rota. Tudo por parametro, para a prova negativa injetar."""
    problemas: list[str] = []
    por_chave = {(r["method"].upper(), r["path"]): r for r in declaradas}

    # A LISTA DE ORIGEM, e nao so o uso dela. Era o buraco da peca 2: papel de
    # exercicio na rota reprovava, e em `papeis_de_dominio` passava. Agora que
    # `emitir_token` le esta lista em tempo de execucao, o buraco e caminho.
    for papel in sorted(papeis_de_dominio & PAPEIS_DE_EXERCICIO):
        problemas.append(
            f"`papeis_de_dominio` contem {papel!r}, que e papel de EXERCICIO "
            "(`03` §7).\n"
            "    Esta lista e o vocabulario que `emitir_token` aceita: um papel "
            "de exercicio aqui vira token de exercicio emitido pelo adapter."
        )

    for chave in sorted(implementadas - set(por_chave)):
        problemas.append(
            f"{chave[0]} {chave[1]}: IMPLEMENTADA e ausente de `api_surface.yaml`.\n"
            "    E a direcao que importa: lista escrita antes do codigo "
            "subestima, e checagem que so confere o inverso vira documentacao "
            "com sintaxe de verificador."
        )

    for chave, rota in sorted(por_chave.items()):
        status = rota.get("status")
        existe = chave in implementadas

        if status == "implementada" and not existe:
            problemas.append(
                f"{chave[0]} {chave[1]}: declarada `implementada` e ausente do "
                "codigo. A declaracao envelheceu — promova de volta a "
                "`planejada` ou remova."
            )
        elif status == "planejada" and existe:
            problemas.append(
                f"{chave[0]} {chave[1]}: declarada `planejada` e JA existe no "
                "codigo. Promova a `implementada` no commit que a criou — senao "
                "`planejada` vira esconderijo permanente."
            )
        elif status not in ("planejada", "implementada"):
            problemas.append(
                f"{chave[0]} {chave[1]}: `status: {status!r}` fora de "
                "`planejada`/`implementada`."
            )

        papeis = rota.get("papeis") or []
        publica = bool(rota.get("publica", False))

        if publica and papeis:
            problemas.append(
                f"{chave[0]} {chave[1]}: `publica: true` com papeis declarados. "
                "Ou a rota e aberta, ou ela exige papel."
            )

        # M2 DA AUDITORIA DA FASE 3 — a metade estrutural.
        #
        # A ordem `autoriza` -> `degrada` garante que estado de simulacao nao
        # chega a quem nao tem token. Rota PUBLICA com degradacao declarada
        # contorna a garantia sem inverter a ordem: `autoriza` deixa passar por
        # ser publica, e `degrada` responde 503 ou latencia para qualquer um na
        # rede. O teste de comportamento cobre a inversao; este eixo cobre a
        # configuracao, que e o outro caminho para o mesmo lugar.
        if publica and (rota.get("degradacao") or []):
            problemas.append(
                f"{chave[0]} {chave[1]}: `publica: true` com degradacao declarada.\n"
                "    Rota aberta que degrada entrega o estado da simulacao a quem "
                "nem token tem — um 503 responde 'a flag esta ligada' para a rede "
                "inteira. Se a rota precisa mesmo ser publica, ela nao degrada."
            )
        elif not publica and not papeis:
            problemas.append(
                f"{chave[0]} {chave[1]}: sem papeis e sem `publica`.\n"
                "    Lista vazia significa NINGUEM, de proposito: se ela "
                "significasse todo mundo, uma rota que perdesse seus papeis numa "
                "edicao descuidada ficaria aberta. Declare `publica: true` se a "
                "intencao e abrir."
            )

        for papel in papeis:
            if papel in PAPEIS_DE_EXERCICIO:
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} e papel de "
                    "EXERCICIO (`03` §7), nao de dominio. O adapter passaria a "
                    "conhecer desenho de exercicio — a fronteira do invariante 1 "
                    "por onde o verificador nao olha."
                )
            elif papel not in papeis_de_dominio:
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} nao esta em "
                    "`papeis_de_dominio`."
                )

        for flag in rota.get("flags") or []:
            if flag not in flags_do_adapter:
                problemas.append(
                    f"{chave[0]} {chave[1]}: consome {flag!r}, que o adapter nao "
                    "declara. Mesma regra que o loader aplica ao pack e que "
                    "`check_spec_flags.py` aplica a spec."
                )

    return problemas


def main(argv: list[str] | None = None) -> int:
    superficies = _superficies()
    if not superficies:
        print(f"{RULE}: nenhum `api_surface.yaml` em {DOMAINS}", file=sys.stderr)
        return 2

    problemas: list[str] = []
    total_rotas = total_implementadas = 0

    for adapter, caminho, documento in superficies:
        declaradas = documento.get("rotas") or []
        implementadas = rotas_implementadas(DOMAINS / adapter / "api")
        total_rotas += len(declaradas)
        total_implementadas += len(implementadas)

        tipos_de_flag = _flags_declaradas(adapter)
        raiz_api = DOMAINS / adapter / "api"

        achados = verifica(
            declaradas,
            implementadas,
            set(documento.get("papeis_de_dominio") or []),
            set(tipos_de_flag),
        )
        achados += verifica_token(
            list((documento.get("token") or {}).get("claims") or []),
            claims_assinadas(REPO_ROOT / MODULO_DO_TOKEN),
        )
        achados += verifica_degradacao(declaradas, tipos_de_flag)
        achados += verifica_escopo(declaradas)
        achados += verifica_imports(
            modulos_que_importam(raiz_api, ESTADO_DE_SIMULACAO),
            modulos_que_importam(raiz_api, f"domains.{adapter}.generated"),
        )

        for problema in achados:
            problemas.append(f"{caminho.relative_to(REPO_ROOT).as_posix()}: {problema}")

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    planejadas = total_rotas - total_implementadas
    claims = claims_assinadas(REPO_ROOT / MODULO_DO_TOKEN) or []
    print(
        f"{RULE}: {total_rotas} rotas declaradas — {total_implementadas} "
        f"implementadas e conferidas por AST, {planejadas} planejadas. "
        "Nenhuma rota fora da declaracao. "
        f"{len(claims)} claims assinadas, todas declaradas; nenhum papel de "
        "exercicio no vocabulario do token."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
