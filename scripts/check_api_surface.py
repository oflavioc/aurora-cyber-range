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
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402

DOMAINS = REPO_ROOT / "domains"
CATALOGO = REPO_ROOT / "contracts" / "events.schema.yaml"

RULE = "superficie da api x rotas implementadas"

#: Metodos HTTP que contam como declaracao de rota. `websocket` entra com o
#: `range-api`: o canal e rota como qualquer outra, e deixa-lo fora faria a
#: unica superficie com WebSocket ser a unica sem a garantia das duas direcoes.
METODOS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "websocket"}
)

#: `websocket` no decorador, `WS` na declaracao — o YAML nao tem por que carregar
#: o nome do framework.
METODO_DECLARADO = {"websocket": "WS"}

#: Papeis de EXERCICIO — `03` §7. Recusados na superficie de dominio por nome.
#:
#: Nao e lista de palavras proibidas por precaucao: sao exatamente os tres que a
#: spec define, e a confusao entre eles e os de dominio e o que poe desenho de
#: exercicio dentro do adapter.
PAPEIS_DE_EXERCICIO = frozenset({"facilitador", "operador", "avaliador"})

#: As sete personas — `03` §6, que o spec-change `superficie-de-participante`
#: tornou FONTE NORMATIVA do conjunto, do mesmo modo que §7 e dos tres papeis.
#:
#: Sao a ancora da superficie de participante: `personas` do
#: `range-core/participant/api_surface.yaml` tem de ser IGUAL a este conjunto.
PERSONAS = frozenset(
    {"reitoria", "pro_reitoria", "ti", "dpo", "juridico", "pesquisa", "comunicacao"}
)

#: As duas ancoras nao se tocam, e a disjuncao da superficie de participante com
#: os papeis de facilitacao e CONSEQUENCIA disso — teorema, e nao segunda regra
#: que alguem precise lembrar de escrever. Afirmado aqui para que deixar de ser
#: verdade reprove na importacao, e nao em silencio.
assert not (PERSONAS & PAPEIS_DE_EXERCICIO), "persona colidindo com papel de facilitacao"

#: Onde as claims sao montadas. Caminho e nome sao constantes AQUI, e nao no
#: YAML da superficie: a tabela de quem-e-julgado-por-que e do verificador.
#:
#: O EMISSOR DO ADAPTER PASSOU A SER PROPRIO na peca do B1 da setima auditoria.
#: Antes esta constante apontava para `range-core/api/tokens.py`, e medido: aquele
#: modulo serve DOIS chamadores — o adapter e o gm-console
#: (`range-core/api/app.py:259`). Acrescentar `persona` ao `_payload` de la, que
#: e o que `01` §6 agora autoriza no adapter, poria a claim no token de
#: FACILITACAO. Mesmo movimento e mesmo motivo do emissor de participante.
MODULO_DO_TOKEN = "domains/academus/api/tokens.py"

#: O emissor da superficie de participante. Proprio, e nao o de cima: claims por
#: superficie e a decisao (b) da autenticacao da peca 3 — ver `fase_6.md`.
MODULO_DO_TOKEN_DE_PARTICIPANTE = "range-core/participant/api/tokens.py"
FUNCAO_DO_PAYLOAD = "_payload"

#: O que um PAPEL de rota do dominio nao pode se chamar — e e aqui que a
#: topologia de `01` §6 passou a morar.
#:
#: `persona` SAIU DO VOCABULARIO PROIBIDO DE CLAIM e entrou no de PAPEL, na peca
#: do B1 da setima auditoria. A troca nao afrouxa: ela move a guarda para o eixo
#: em que `01` §6 a coloca, na forma que o spec-change #52 lhe deu —
#:
#:   *"o que autoriza uma rota do adapter e papel de dominio, nunca persona"*
#:   *"persona como identidade que viaja para o envelope: permitida"*
#:
#: Como CLAIM, `persona` e legitima: `09` §1 exibe o envelope normativo com
#: `producer: academus-api` e `persona: ti`, e sem ela o adapter emite um
#: envelope que o contrato recusa. Como PAPEL, ela poria RBAC de exercicio dentro
#: do adapter — que e o buraco que esta lista sempre existiu para fechar.
#:
#: Sem esta segunda metade a mudanca seria afrouxamento: `papeis_de_dominio`
#: aceitaria `ti`, `emitir_token` assinaria papel de persona, e uma rota do
#: adapter passaria a autorizar por desenho de exercicio.
PAPEIS_PROIBIDOS_NO_DOMINIO = PAPEIS_DE_EXERCICIO | PERSONAS

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

#: `efeito` — o que a rota faz com o EXERCICIO, e se tem volta. Vocabulario
#: fechado, pelo mesmo motivo do catalogo de `event_type`: valor que ninguem
#: implementou vira semantica que nao acontece.
EFEITO_NENHUM = "nenhum"
EFEITO_REVERSIVEL = "reversivel"
EFEITO_IRREVERSIVEL = "irreversivel"
EFEITO_DESTRUTIVO = "destrutivo"
EFEITOS_DE_EXERCICIO = frozenset(
    {EFEITO_NENHUM, EFEITO_REVERSIVEL, EFEITO_IRREVERSIVEL, EFEITO_DESTRUTIVO}
)

#: Os que exigem confirmacao explicita da interface. Confirmacao onde NAO ha o
#: que confirmar tambem reprova: treinar o operador a clicar "sim" e o caminho
#: para o clique que dispara inject por engano.
EXIGEM_CONFIRMACAO = frozenset({EFEITO_IRREVERSIVEL, EFEITO_DESTRUTIVO})

#: `09` §2 — comando de console e o facilitador agindo sobre a SIMULACAO.
CAMADA_DE_FACILITACAO = "facilitation"

#: As familias de regra que este verificador conhece. Cada perfil declara as
#: suas, e o probe da tabela exige que a uniao seja EXATAMENTE este conjunto:
#: familia que nenhum perfil reivindica e regra escrita que nunca roda, e um
#: nome digitado errado desligaria a familia em silencio.
FAMILIAS_CONHECIDAS = frozenset(
    {"flags", "degradacao", "escopo", "token", "imports",
     "eventos", "irreversibilidade", "canais"}
)


@dataclass(frozen=True)
class Perfil:
    """Como uma superficie e julgada. **Duas, e o conjunto e fechado.**

    A GENERALIZACAO E SOBRE AS SUPERFICIES, E NAO SOBRE AS REGRAS, e a diferenca
    e a que decide se o verificador enfraquece.

    Um verificador parametrizado que recebesse "papeis permitidos" e "papeis
    recusados" por argumento aceitaria o par vazio — e ficaria verde provando
    nada, que e a familia de defeito que este projeto ja pagou quatro vezes. Aqui
    nao ha par: ha UMA ancora, `PAPEIS_DE_EXERCICIO`, que vem de `03` §7, e cada
    perfil se relaciona com ela de um jeito fixo — o nucleo exige IGUALDADE, o
    dominio exige DISJUNCAO. Nenhum dos dois e argumento de chamada.

    `familias` tambem nao afrouxa: elas sao conferidas contra
    `FAMILIAS_CONHECIDAS` nas duas direcoes, e as chaves de rota sao whitelist
    por perfil — campo desconhecido reprova, e campo obrigatorio ausente
    tambem. Sem isso, apagar `degradacao:` de uma rota desligaria a familia
    inteira sem que nada acusasse: regra que so existe quando o campo existe e
    regra que se desliga apagando o campo.
    """

    nome: str
    #: O conjunto com que a lista declarada tem de ser IGUAL, ou `None` quando a
    #: lista e livre. Continua NAO sendo argumento de chamada: e um dos valores
    #: fechados do modulo, e cada perfil se relaciona com ele de um jeito fixo.
    #:
    #: Perfil sem ancora de igualdade ganha, no lugar, a DISJUNCAO com
    #: `PAPEIS_DE_EXERCICIO` — que e o caso do dominio.
    ancora_de_papeis: frozenset[str] | None
    chave_de_papeis: str
    #: O modulo que assina o token DESTA superficie, relativo a raiz. `None`
    #: quando a superficie nao emite token. Antes era a constante
    #: `MODULO_DO_TOKEN`, unica — e uma funcao unica assinando duas vocacoes poria
    #: `persona` tambem no token de facilitacao, que e o risco que o docstring
    #: daquela funcao guarda. Movimento irmao do `camadas_de_emissao`.
    modulo_do_token: str | None
    #: O que um claim DESTA superficie nao pode se chamar. Nao e o mesmo conjunto
    #: para todas: o token de participante carrega `persona` no lugar de `role`, e
    #: o de dominio carrega as duas — papel autoriza, persona identifica (`01`
    #: §6). Os tres papeis de FACILITACAO ficam proibidos nas duas.
    vocabulario_proibido_em_claim: frozenset[str]
    #: O que a lista de papeis DESTA superficie nao pode conter, quando o perfil
    #: se relaciona com a ancora por DISJUNCAO em vez de igualdade. `None` para
    #: quem tem `ancora_de_papeis`, porque igualdade ja decide tudo.
    papeis_proibidos: frozenset[str] | None
    #: As camadas de `truth_layer` que ESTA superficie pode emitir. E ancora do
    #: perfil, e nao argumento de chamada: o nucleo emite `facilitation` porque
    #: comando de console e o facilitador agindo sobre a SIMULACAO (`09` §2); o
    #: adapter e aplicacao instrumentada, e emite o que a equipe faz e o que o
    #: ambiente revela. Um verificador que recebesse "camadas permitidas" por
    #: argumento aceitaria o conjunto vazio e ficaria verde provando nada.
    camadas_de_emissao: frozenset[str]
    familias: frozenset[str]
    chaves_de_topo: frozenset[str]
    chaves_de_rota_obrigatorias: frozenset[str]
    chaves_de_rota_permitidas: frozenset[str]


CHAVES_COMUNS = frozenset({"method", "path", "status", "papeis", "publica"})

PERFIL_DOMINIO = Perfil(
    nome="dominio",
    ancora_de_papeis=None,
    chave_de_papeis="papeis_de_dominio",
    modulo_do_token=MODULO_DO_TOKEN,
    # `persona` NAO esta aqui — ver `PAPEIS_PROIBIDOS_NO_DOMINIO`. O que fica
    # proibido em claim sao os tres papeis de FACILITACAO: token de dominio que
    # carregasse `facilitador` seria console emitido pela porta do adapter.
    vocabulario_proibido_em_claim=PAPEIS_DE_EXERCICIO,
    papeis_proibidos=PAPEIS_PROIBIDOS_NO_DOMINIO,
    # `09` §2: `participant_action` e produzida pela APLICACAO INSTRUMENTADA, e
    # `observable_evidence` por projecoes de fato e pela aplicacao. `facilitation`
    # NAO entra: comando de facilitacao nao mora no adapter.
    camadas_de_emissao=frozenset({"participant_action", "observable_evidence"}),
    familias=frozenset(
        {"flags", "degradacao", "escopo", "token", "imports", "eventos"}
    ),
    chaves_de_topo=frozenset({"token", "papeis_de_dominio", "rotas"}),
    chaves_de_rota_obrigatorias=frozenset(
        {"method", "path", "status", "flags", "efeito"}
    ),
    chaves_de_rota_permitidas=CHAVES_COMUNS
    | {"flags", "degradacao", "escopo", "efeito", "emite"},
)

PERFIL_NUCLEO = Perfil(
    nome="nucleo",
    ancora_de_papeis=PAPEIS_DE_EXERCICIO,
    chave_de_papeis="papeis_de_exercicio",
    modulo_do_token=None,
    vocabulario_proibido_em_claim=frozenset(),
    papeis_proibidos=None,
    camadas_de_emissao=frozenset({CAMADA_DE_FACILITACAO}),
    familias=frozenset({"eventos", "irreversibilidade", "canais"}),
    chaves_de_topo=frozenset({"papeis_de_exercicio", "projecoes", "rotas"}),
    chaves_de_rota_obrigatorias=frozenset({"method", "path", "status", "efeito"}),
    chaves_de_rota_permitidas=CHAVES_COMUNS
    | {"efeito", "emite", "inverso", "confirmacao", "projecao", "snapshot"},
)

#: A TABELA, e ela e o que impede a generalizacao de virar frouxidao: superficie
#: em disco fora daqui REPROVA, e entrada daqui sem arquivo tambem. Sem as duas
#: direcoes, um `api_surface.yaml` novo seria julgado por um perfil padrao — e um
#: perfil padrao e o lugar onde a regra certa nao roda.
PERFIL_PARTICIPANTE = Perfil(
    nome="participante",
    # IGUALDADE com as sete de `03` §6. A disjuncao com os papeis de facilitacao
    # vem de graca: o `assert` do modulo afirma que os dois conjuntos nao se
    # tocam, entao ela e teorema e nao segunda regra.
    ancora_de_papeis=PERSONAS,
    chave_de_papeis="personas",
    modulo_do_token=MODULO_DO_TOKEN_DE_PARTICIPANTE,
    # `persona` NAO esta aqui: nesta superficie ele e o vocabulario correto. O
    # que fica proibido sao os tres papeis de FACILITACAO — token de participante
    # que carregasse `facilitador` seria console emitido pela porta do exercicio.
    vocabulario_proibido_em_claim=PAPEIS_DE_EXERCICIO,
    papeis_proibidos=None,
    # `participant_action`, e SO ela. Esta superficie nao emite facilitacao — que
    # e do console — nem evidencia observavel — que e projecao de fato.
    camadas_de_emissao=frozenset({"participant_action"}),
    # Sem `degradacao`, `escopo` nem `flags`: degradar declaracao de participante
    # seria a maquina de exercicio interferindo no ato que ela mede. Sem
    # `irreversibilidade` e `canais`: sao familias do console.
    familias=frozenset({"eventos", "token", "imports"}),
    chaves_de_topo=frozenset({"token", "personas", "rotas"}),
    chaves_de_rota_obrigatorias=frozenset({"method", "path", "status", "efeito"}),
    chaves_de_rota_permitidas=CHAVES_COMUNS | {"efeito", "emite"},
)

SUPERFICIES = {
    "range-core/api_surface.yaml": PERFIL_NUCLEO,
    "domains/academus/api_surface.yaml": PERFIL_DOMINIO,
    "range-core/participant/api_surface.yaml": PERFIL_PARTICIPANTE,
}

#: Diretorios que a varredura de superficies ignora — nao sao a arvore.
IGNORADOS = (".git", ".aurora-worktrees", "node_modules", ".venv", "__pycache__")

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


def superficies_em_disco() -> set[str]:
    """Todo `api_surface.yaml` da arvore, em caminho relativo POSIX."""
    achadas = set()
    for caminho in REPO_ROOT.rglob("api_surface.yaml"):
        relativo = caminho.relative_to(REPO_ROOT)
        if any(parte in IGNORADOS for parte in relativo.parts):
            continue
        achadas.add(relativo.as_posix())
    return achadas


def verifica_tabela(em_disco: set[str]) -> list[str]:
    """A tabela de perfis e exatamente as superficies que existem.

    E o eixo que a generalizacao exige e que a versao de uma superficie so nao
    precisava ter. Sem ele, a classificacao errada — ou ausente — de uma
    superficie nova seria SILENCIOSA, e o custo e verificar com as regras do
    outro perfil.
    """
    problemas: list[str] = []
    for caminho in sorted(em_disco - set(SUPERFICIES)):
        problemas.append(
            f"{caminho}: superficie em disco e ausente da tabela de perfis.\n"
            "    Classifique-a em `SUPERFICIES` no commit que a cria. Perfil "
            "ausente nao degrada para um perfil padrao: sem saber quais regras "
            "valem, nao se pode dizer que alguma valeu."
        )
    for caminho in sorted(set(SUPERFICIES) - em_disco):
        problemas.append(
            f"{caminho}: declarada na tabela de perfis e ausente do disco. "
            "A tabela envelheceu."
        )

    reivindicadas = frozenset().union(*(p.familias for p in SUPERFICIES.values()))
    for familia in sorted(FAMILIAS_CONHECIDAS - reivindicadas):
        problemas.append(
            f"familia de regra {familia!r} nao e reivindicada por perfil nenhum: "
            "ela nunca roda.\n"
            "    Regra escrita que nao e exercida e a §7.3 da Fase 3 — ela parece "
            "pronta ate alguem precisar dela."
        )
    for familia in sorted(reivindicadas - FAMILIAS_CONHECIDAS):
        problemas.append(
            f"perfil reivindica familia desconhecida {familia!r}: nome digitado "
            "errado desliga a familia em silencio."
        )
    return problemas


def catalogo_de_eventos(caminho: Path) -> dict[str, str]:
    """`event_type -> truth_layer`, lido de `contracts/events.schema.yaml`.

    O catalogo e registro FECHADO (`09` §4), e a superficie do nucleo e a quarta
    porta pela qual um nome de evento entra no sistema — depois do codigo, do
    pack e da spec. As outras tres ja tem guarda; esta passa a ter a mesma.
    """
    documento = parse_yaml(caminho) or {}
    catalogo: dict[str, str] = {}
    for nome, corpo in (documento.get("$defs") or {}).items():
        if not nome.startswith("event_type_"):
            continue
        camada = nome[len("event_type_"):]
        for tipo in (corpo or {}).get("enum") or []:
            catalogo[str(tipo)] = camada
    return catalogo


def verifica_chaves(documento: dict, declaradas: list[dict], perfil: Perfil) -> list[str]:
    """Whitelist de chaves, no topo e na rota. **Nas duas direcoes.**

    A direcao que importa e a ausencia: uma regra que so roda quando o campo
    existe se desliga quando alguem apaga o campo. Com a chave obrigatoria
    declarada por perfil, apagar `flags:` de uma rota de dominio deixa de ser
    "essa rota nao tem flags" e passa a ser reprovacao.

    A outra direcao pega o campo que ninguem le: `degradacao` foi PROSA no
    `api_surface.yaml` da Fase 3 ate a peca 5, e prosa nao executa.
    """
    problemas: list[str] = []

    for chave in sorted(set(documento) - perfil.chaves_de_topo):
        problemas.append(
            f"chave de topo {chave!r} desconhecida no perfil {perfil.nome!r}.\n"
            "    Campo que nenhum verificador le e promessa que ninguem cumpre."
        )
    for chave in sorted(perfil.chaves_de_topo - set(documento)):
        problemas.append(
            f"chave de topo {chave!r} ausente, e o perfil {perfil.nome!r} a exige."
        )

    for rota in declaradas:
        chave_rota = f"{str(rota.get('method', '')).upper()} {rota.get('path')}"
        for campo in sorted(set(rota) - perfil.chaves_de_rota_permitidas):
            problemas.append(
                f"{chave_rota}: campo {campo!r} nao existe no perfil "
                f"{perfil.nome!r}.\n"
                "    Os dois perfis nao compartilham vocabulario por acaso: "
                "`flags` na superficie do nucleo seria nome de dominio dentro do "
                "core. `emite` passou a existir tambem no adapter na peca 3 da "
                "Fase 6, quando a instrumentacao chegou — era a P4-2, e o gatilho "
                "dela era o primeiro `append` fora do inject-engine."
            )
        for campo in sorted(perfil.chaves_de_rota_obrigatorias - set(rota)):
            problemas.append(
                f"{chave_rota}: campo obrigatorio {campo!r} ausente. Regra que so "
                "vale quando o campo existe se desliga apagando o campo."
            )
    return problemas


def verifica_eventos(
    declaradas: list[dict], catalogo: dict[str, str], perfil: Perfil
) -> list[str]:
    """`emite` e nome de evento do CATALOGO, e de camada que ESTE perfil admite.

    A familia rodava so no nucleo, e a P4-2 nomeou o buraco: emitir sem declarar
    `emite` nao tinha guarda em lugar nenhum, e o gatilho declarado era **o
    primeiro `append` fora do inject-engine**. A peca 3 da Fase 6 e esse append —
    `audit_query_performed` e as acoes de declaracao —, entao a familia passa a
    rodar tambem no perfil de dominio.

    A camada admitida vem do PERFIL. Antes era a constante `facilitation`, que e
    a certa para o console e a errada para o adapter: a `academus-api` emite o
    que a equipe declara e o que o ambiente revela, nunca comando de facilitacao.
    """
    problemas: list[str] = []
    for rota in declaradas:
        chave = f"{str(rota.get('method', '')).upper()} {rota.get('path')}"
        emite = rota.get("emite")
        efeito = rota.get("efeito")

        if emite is None:
            if efeito != EFEITO_NENHUM:
                problemas.append(
                    f"{chave}: `efeito: {efeito!r}` e nao declara `emite`.\n"
                    "    Comando de facilitacao sem rastro e excecao nao "
                    "declarada: `00` §5.5 apoia tudo em o registro reconstruir o "
                    "exercicio, e foi esse o argumento do `exercise_resumed`."
                )
            continue

        if efeito == EFEITO_NENHUM:
            problemas.append(
                f"{chave}: `efeito: nenhum` e emite {emite!r}. Rota que grava "
                "evento MOVE o exercicio, por definicao."
            )

        camada = catalogo.get(str(emite))
        if camada is None:
            problemas.append(
                f"{chave}: emite {emite!r}, que nao esta no catalogo de "
                "`contracts/events.schema.yaml`.\n"
                "    E a quarta porta pela qual um `event_type` entra no sistema, "
                "e `09` §4 diz por que o catalogo e fechado: tipo com erro de "
                "digitacao nunca dispara, e ninguem percebe ate o exercicio ao "
                "vivo."
            )
        elif camada not in perfil.camadas_de_emissao:
            admitidas = ", ".join(f"`{c}`" for c in sorted(perfil.camadas_de_emissao))
            problemas.append(
                f"{chave}: emite {emite!r}, que e `{camada}`, e a superficie "
                f"{perfil.nome!r} so admite {admitidas}.\n"
                "    Comando do console e o facilitador agindo sobre a SIMULACAO "
                "(`09` §2); o adapter e aplicacao INSTRUMENTADA. Trocar as duas "
                "misturaria maquina de exercicio com fato do incidente — a "
                "confusao que `00` §3 existe para impedir."
            )
    return problemas


def verifica_irreversibilidade(declaradas: list[dict]) -> list[str]:
    """O que tem volta, o que nao tem, e o que descarta estado — `01` §4.2.

    O par PAUSAR/CONTINUAR e conferido nos DOIS sentidos: se A declara B como
    inverso, B tem de declarar A. Uma seta so faria "reversivel" virar rotulo, e
    e justamente o rotulo que a interface vai ler para decidir se pede
    confirmacao.
    """
    problemas: list[str] = []
    por_chave = {
        f"{str(r.get('method', '')).upper()} {r.get('path')}": r for r in declaradas
    }

    for chave, rota in sorted(por_chave.items()):
        efeito = rota.get("efeito")
        inverso = rota.get("inverso")
        confirmacao = rota.get("confirmacao")

        if efeito not in EFEITOS_DE_EXERCICIO:
            problemas.append(
                f"{chave}: `efeito: {efeito!r}` fora de "
                f"{sorted(EFEITOS_DE_EXERCICIO)}."
            )
            continue

        if efeito != EFEITO_NENHUM and rota.get("publica"):
            problemas.append(
                f"{chave}: `publica: true` e move o exercicio (`{efeito}`).\n"
                "    `05` §8 isenta de autenticacao apenas wallboard e "
                "participant-view, que OLHAM o exercicio. Operar sem token seria "
                "entregar o console a rede."
            )

        if efeito == EFEITO_REVERSIVEL:
            if not inverso:
                problemas.append(
                    f"{chave}: `reversivel` sem `inverso`. Reversivel por qual "
                    "comando? Sem a resposta, o rotulo nao e verificavel."
                )
            elif inverso not in por_chave:
                problemas.append(
                    f"{chave}: `inverso: {inverso!r}` nao e rota declarada."
                )
            else:
                volta = por_chave[inverso]
                if volta.get("inverso") != chave:
                    problemas.append(
                        f"{chave}: declara {inverso!r} como inverso, e "
                        f"{inverso!r} nao declara {chave!r} de volta.\n"
                        "    Uma seta so nao e reversibilidade: e um rotulo."
                    )
                if volta.get("efeito") != EFEITO_REVERSIVEL:
                    problemas.append(
                        f"{chave}: o inverso {inverso!r} tem "
                        f"`efeito: {volta.get('efeito')!r}`, e nao `reversivel`."
                    )
        elif inverso is not None:
            problemas.append(
                f"{chave}: `efeito: {efeito}` com `inverso` declarado. Se ha "
                "comando que desfaz, o efeito e `reversivel`."
            )

        if efeito in EXIGEM_CONFIRMACAO and confirmacao is not True:
            problemas.append(
                f"{chave}: `{efeito}` sem `confirmacao: true`.\n"
                "    Um clique que dispara inject nao tem desfazer, e `01` §4.2 "
                "da ao console quatro comandos com semanticas muito diferentes. "
                "A interface precisa saber quais pedem confirmacao, e saber pela "
                "declaracao — nao pela lembranca de quem a escreve."
            )
        if efeito not in EXIGEM_CONFIRMACAO and confirmacao is not None:
            problemas.append(
                f"{chave}: `confirmacao` declarada com `efeito: {efeito}`.\n"
                "    Confirmar o que tem volta treina o operador a clicar 'sim', "
                "e e assim que a confirmacao do que NAO tem volta deixa de ser "
                "lida."
            )
    return problemas


def verifica_canais(declaradas: list[dict], projecoes: list[str]) -> list[str]:
    """Canal e snapshot sao a MESMA projecao, com a MESMA visibilidade — D3.

    O frame do WebSocket e o snapshot HTTP tem de ser o mesmo payload para o
    mesmo estado. Antes de existir codigo, o que da para afirmar e a declaracao;
    e ela ja pega o caso que ninguem veria depois: canal e snapshot com
    visibilidades diferentes fazem a sala e quem reconecta verem coisas
    diferentes pela porta da AUTORIZACAO, e cada um dos dois esta certo sozinho.
    """
    problemas: list[str] = []
    por_chave = {
        f"{str(r.get('method', '')).upper()} {r.get('path')}": r for r in declaradas
    }
    declaradas_no_topo = set(projecoes)
    usadas: set[str] = set()

    for chave, rota in sorted(por_chave.items()):
        projecao = rota.get("projecao")
        snapshot = rota.get("snapshot")
        e_canal = str(rota.get("method", "")).upper() == "WS"

        if projecao is not None:
            usadas.add(str(projecao))
            if projecao not in declaradas_no_topo:
                problemas.append(
                    f"{chave}: `projecao: {projecao!r}` nao esta em `projecoes`."
                )

        if e_canal:
            if not projecao:
                problemas.append(f"{chave}: canal sem `projecao`.")
            if not snapshot:
                problemas.append(
                    f"{chave}: canal sem `snapshot`.\n"
                    "    Sem a rota de snapshot, 'refresh recupera o estado "
                    "corrente' — item 3 da DoD — nao tem por onde acontecer."
                )
        elif snapshot is not None:
            problemas.append(
                f"{chave}: `snapshot` declarado numa rota que nao e canal."
            )

        if not snapshot:
            continue
        if snapshot not in por_chave:
            problemas.append(f"{chave}: `snapshot: {snapshot!r}` nao e rota declarada.")
            continue

        alvo = por_chave[snapshot]
        if not snapshot.startswith("GET "):
            problemas.append(f"{chave}: o snapshot {snapshot!r} nao e um GET.")
        if alvo.get("projecao") != projecao:
            problemas.append(
                f"{chave}: canal projeta {projecao!r} e o snapshot {snapshot!r} "
                f"projeta {alvo.get('projecao')!r}.\n"
                "    Duas serializacoes do mesmo fato divergem, e a que diverge "
                "em silencio e sempre a que ninguem esta olhando."
            )
        if bool(alvo.get("publica")) != bool(rota.get("publica")) or (
            set(alvo.get("papeis") or []) != set(rota.get("papeis") or [])
        ):
            problemas.append(
                f"{chave}: canal e snapshot {snapshot!r} tem visibilidades "
                "diferentes.\n"
                "    A sala e quem reconecta veriam coisas diferentes pela porta "
                "da autorizacao, e cada um dos dois estaria certo sozinho."
            )

    for orfa in sorted(declaradas_no_topo - usadas):
        problemas.append(
            f"projecao {orfa!r} declarada e nao usada por rota nenhuma."
        )

    for projecao in sorted(usadas & declaradas_no_topo):
        canais = [
            c for c, r in por_chave.items()
            if r.get("projecao") == projecao and str(r.get("method", "")).upper() == "WS"
        ]
        snapshots = [
            c for c, r in por_chave.items()
            if r.get("projecao") == projecao and str(r.get("method", "")).upper() == "GET"
        ]
        if len(canais) != 1 or len(snapshots) != 1:
            problemas.append(
                f"projecao {projecao!r}: {len(canais)} canal(is) e "
                f"{len(snapshots)} snapshot(s), e o par tem de ser exatamente um "
                "de cada.\n"
                "    Dois produtores do mesmo payload e a divergencia esperando "
                "para acontecer; nenhum canal e um snapshot que ninguem atualiza."
            )
    return problemas


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
                    metodo = METODO_DECLARADO.get(func.attr, func.attr.upper())
                    achadas.add((metodo, primeiro.value))
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
    perfil: Perfil,
) -> list[str]:
    """`token.claims` x o que o EMISSOR DESTA superficie assina.

    Antes comparava a unica `_payload` contra toda superficie que declarasse
    `token`. Com dois emissores isso reprova por construcao: o claim `role` do
    console apareceria como "assinado e nao declarado" na superficie de
    participante, e `persona` como "declarado e nao assinado" na de dominio.

    O modulo e o vocabulario proibido passam a vir do PERFIL — o mesmo movimento
    que `camadas_de_emissao` fez com a camada.
    """
    modulo = perfil.modulo_do_token or MODULO_DO_TOKEN
    problemas: list[str] = []

    if claims_no_codigo is None:
        return [
            f"{modulo}: `{FUNCAO_DO_PAYLOAD}` nao existe.\n"
            "    Sem ela a comparacao de claims nao casa com nada e a checagem "
            "passa por VACUIDADE. Renomeou? Atualize a declaracao."
        ]

    for claim in sorted(set(claims_no_codigo) - set(claims_declaradas)):
        problemas.append(
            f"claim {claim!r} e assinado por {modulo} e ausente de "
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
        if claim.lower() in perfil.vocabulario_proibido_em_claim:
            problemas.append(
                f"claim {claim!r} nao pode existir no token da superficie "
                f"{perfil.nome!r}.\n"
                "    Cada superficie tem o seu vocabulario proibido: `persona` "
                "no token de dominio seria desenho de exercicio dentro do "
                "adapter (D2); papel de facilitacao no de participante seria "
                "console emitido pela porta do exercicio."
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
    papeis_declarados: set[str],
    flags_do_adapter: set[str],
    perfil: Perfil,
) -> list[str]:
    """As asserções sobre rota. Tudo por parametro, para a prova negativa injetar.

    `perfil` NAO e um par de listas: e um dos dois valores fechados do modulo, e
    a relacao de cada um com `PAPEIS_DE_EXERCICIO` — igualdade ou disjuncao — e
    fixa. Ver o docstring de `Perfil`.
    """
    problemas: list[str] = []
    por_chave = {(r["method"].upper(), r["path"]): r for r in declaradas}

    if perfil.ancora_de_papeis is not None:
        # IGUALDADE nas duas direcoes, contra a ancora DO PERFIL. Sobrando, a
        # superficie conheceria papel que a spec nao define; faltando, a lista
        # deixaria de ancorar a disjuncao do outro lado.
        fonte = (
            "`03` §7"
            if perfil.ancora_de_papeis == PAPEIS_DE_EXERCICIO
            else "`03` §6"
        )
        for papel in sorted(papeis_declarados - perfil.ancora_de_papeis):
            problemas.append(
                f"`{perfil.chave_de_papeis}` contem {papel!r}, que nao esta em "
                f"{fonte}.\n"
                "    Papel de DOMINIO aqui poria vocabulario de negocio dentro do "
                "core — a mesma fronteira do invariante 1, lida no sentido "
                "inverso ao do adapter."
            )
        for papel in sorted(perfil.ancora_de_papeis - papeis_declarados):
            problemas.append(
                f"`{perfil.chave_de_papeis}` nao declara {papel!r}, que {fonte} "
                "define.\n"
                "    A lista e ancora de disjuncao para as outras superficies: "
                "encolhe-la aqui afrouxaria a guarda do outro lado sem tocar nele."
            )
    else:
        # DOMINIO: disjuncao. Era o buraco da peca 2 — papel de exercicio na rota
        # reprovava, e em `papeis_de_dominio` passava. Agora que `emitir_token` le
        # esta lista em tempo de execucao, o buraco e caminho.
        #
        # O CONJUNTO PROIBIDO GANHOU AS SETE PERSONAS na peca do B1 da setima
        # auditoria, quando `persona` deixou de ser proibida como CLAIM. E o que
        # impede a mudanca de ser afrouxamento: a topologia de `01` §6 — "o que
        # autoriza uma rota do adapter e papel de dominio, nunca persona" — passou
        # a ser imposta aqui, no eixo em que ela de fato vale.
        for papel in sorted(papeis_declarados & (perfil.papeis_proibidos or frozenset())):
            familia = (
                "papel de EXERCICIO (`03` §7)"
                if papel in PAPEIS_DE_EXERCICIO
                else "PERSONA (`03` §6)"
            )
            problemas.append(
                f"`{perfil.chave_de_papeis}` contem {papel!r}, que e {familia}.\n"
                "    Esta lista e o vocabulario que `emitir_token` aceita, e e o "
                "que AUTORIZA rota do adapter. Papel de exercicio aqui vira token "
                "de facilitacao emitido pelo adapter; persona aqui poe RBAC de "
                "exercicio dentro do dominio — `01` §6: persona identifica no "
                "envelope, e nunca autoriza rota."
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
            # Papel de facilitacao numa ROTA de superficie que nao e a do
            # console. Vale para o dominio e para a de participante: as duas tem
            # ancora distinta de `PAPEIS_DE_EXERCICIO`, e nas duas um papel de
            # facilitacao na rota seria desenho de exercicio no lugar errado.
            if (
                perfil.ancora_de_papeis != PAPEIS_DE_EXERCICIO
                and papel in PAPEIS_DE_EXERCICIO
            ):
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} e papel de "
                    "EXERCICIO (`03` §7), nao de dominio. O adapter passaria a "
                    "conhecer desenho de exercicio — a fronteira do invariante 1 "
                    "por onde o verificador nao olha."
                )
            elif papel not in papeis_declarados:
                problemas.append(
                    f"{chave[0]} {chave[1]}: papel {papel!r} nao esta em "
                    f"`{perfil.chave_de_papeis}`."
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
    em_disco = superficies_em_disco()
    problemas: list[str] = list(verifica_tabela(em_disco))
    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    catalogo = catalogo_de_eventos(CATALOGO)
    total_rotas = total_implementadas = 0
    por_perfil: dict[str, int] = {}

    for relativo, perfil in sorted(SUPERFICIES.items()):
        caminho = REPO_ROOT / relativo
        documento = parse_yaml(caminho) or {}
        declaradas = documento.get("rotas") or []
        raiz_api = caminho.parent / "api"
        implementadas = rotas_implementadas(raiz_api)
        total_rotas += len(declaradas)
        total_implementadas += len(implementadas)
        por_perfil[perfil.nome] = por_perfil.get(perfil.nome, 0) + len(declaradas)

        # `flags.yaml` e do adapter e so existe no perfil de dominio. No nucleo o
        # dicionario vem vazio, e e por isso que a familia `flags` nao esta nas
        # familias dele: regra sobre conjunto vazio passa sempre.
        tipos_de_flag = _flags_declaradas(caminho.parent.name) if "flags" in perfil.familias else {}

        achados = verifica_chaves(documento, declaradas, perfil)
        achados += verifica(
            declaradas,
            implementadas,
            set(documento.get(perfil.chave_de_papeis) or []),
            set(tipos_de_flag),
            perfil,
        )
        if "token" in perfil.familias:
            achados += verifica_token(
                list((documento.get("token") or {}).get("claims") or []),
                claims_assinadas(REPO_ROOT / (perfil.modulo_do_token or MODULO_DO_TOKEN)),
                perfil,
            )
        if "degradacao" in perfil.familias:
            achados += verifica_degradacao(declaradas, tipos_de_flag)
        if "escopo" in perfil.familias:
            achados += verifica_escopo(declaradas)
        if "imports" in perfil.familias:
            achados += verifica_imports(
                modulos_que_importam(raiz_api, ESTADO_DE_SIMULACAO),
                modulos_que_importam(
                    raiz_api, f"domains.{caminho.parent.name}.generated"
                ),
            )
        if "eventos" in perfil.familias:
            achados += verifica_eventos(declaradas, catalogo, perfil)
        if "irreversibilidade" in perfil.familias:
            achados += verifica_irreversibilidade(declaradas)
        if "canais" in perfil.familias:
            achados += verifica_canais(declaradas, list(documento.get("projecoes") or []))

        for problema in achados:
            problemas.append(f"{relativo} [{perfil.nome}]: {problema}")

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    planejadas = total_rotas - total_implementadas
    claims = claims_assinadas(REPO_ROOT / MODULO_DO_TOKEN) or []
    resumo = ", ".join(f"{n}: {q}" for n, q in sorted(por_perfil.items()))
    print(
        f"{RULE}: {len(SUPERFICIES)} superficies ({resumo}), {total_rotas} rotas "
        f"declaradas — {total_implementadas} implementadas e conferidas por AST, "
        f"{planejadas} planejadas. Nenhuma rota fora da declaracao. "
        f"{len(claims)} claims assinadas, todas declaradas; nenhum papel de "
        f"exercicio no vocabulario do token. {len(catalogo)} `event_type` no "
        "catalogo, e todo `emite` sai dele."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
