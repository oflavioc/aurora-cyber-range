"""JWT e RBAC da `academus-api` — a decisao de negar, e onde ela mora.

AS DUAS METADES DA D2, E A SEGUNDA E A QUE FALTAVA
---------------------------------------------------
`03` §7 tem `facilitador`, `operador` e `avaliador`. Esta API tem `aluno`,
`professor`, `secretaria` e `financeiro`. A peca 2 ja recusava papel de
exercicio NA ROTA; o token e a outra porta, e nenhum verificador de import
enxerga um claim.

A guarda e a MESMA, estendida — e nao uma segunda. O motivo e a D4 do catalogo
de classes recorrentes: duas listas sobre a mesma fronteira divergem, e a que
diverge silenciosamente e sempre a que ninguem esta olhando.

O mecanismo, inteiro:

1. `emitir_token` so aceita papel que esteja em `papeis_de_dominio` — a lista
   lida do `api_surface.yaml`, em tempo de execucao.
2. `scripts/check_api_surface.py` recusa papel de exercicio DENTRO de
   `papeis_de_dominio`.

Junto, isso torna `emitir_token(sub, "facilitador")` **inexprimivel**, e nao
apenas proibido: para o token existir, `facilitador` precisaria estar na lista;
para estar na lista, precisaria passar pelo gate que o recusa por nome.

ONDE A NEGACAO ACONTECE, E POR QUE O LUGAR E A GARANTIA
--------------------------------------------------------
`autoriza` e dependencia GLOBAL da aplicacao: roda antes de qualquer path
operation. A assinatura dela recebe `Request` e mais nada — **nao ha repositorio
ao alcance**, entao a decisao de negar nao tem como depender de o recurso
existir.

Isso responde a pergunta de 403 x 404 num lugar melhor que o codigo de status.

403 CONFIRMA QUE O RECURSO EXISTE — SE E SO SE A NEGACAO O CONSULTOU
---------------------------------------------------------------------
O canal de inferencia que preocupa num exercicio sobre assimetria de informacao
nao esta no numero: esta em a resposta VARIAR com a existencia do recurso. Uma
API que negue com 404 mas so depois de procurar vaza pelo tempo; uma que negue
com 403 sem procurar nao vaza nada.

Entao a propriedade e **indistinguibilidade**, e ela e verificavel: negacao para
recurso existente e para inexistente sao identicas — mesmo status, mesmo corpo.
`tests/test_api_rbac.py` afirma isso comparando as duas respostas.

Fechada essa porta, o codigo de status fica livre para seguir a spec, e ela tem
opiniao: `06` T6 fixa **403** para acesso a endpoint fora do papel. Escolher 404
aqui criaria duas politicas de negacao no mesmo produto — e a diferenca entre
elas seria, ela propria, informacao inferivel.

- **401** — sem token, ou token que nao verifica. Com `WWW-Authenticate`.
- **403** — token valido, papel que a rota nao admite.
- **404** — so para quem TEM direito de saber que o recurso nao existe.

O 401 nao distingue "expirado" de "assinatura invalida": a mensagem que explica
por que o token nao serve ajuda quem esta tentando descobrir.

FALHA FECHADA
-------------
Rota que o FastAPI serve e o `api_surface.yaml` nao declara e NEGADA em tempo de
execucao, alem de reprovar no CI. Sao dois mecanismos independentes, e o de
runtime fecha em vez de abrir — o gate protege o repositorio, isto protege o
exercicio em curso.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

from range_core.api.tokens import TokenClaims, TokenInvalid, issue, jwt_secret, verify

from domains.academus.api.surface import Superficie, carregar

PREFIXO = "Bearer "

#: Corpo unico de negacao por papel. TEXTO FIXO, sem o recurso pedido: uma
#: mensagem que repetisse o `aluno_id` devolveria pela resposta a informacao que
#: a negacao existe para nao dar.
NEGADO = "acesso negado para este papel"


class PapelDesconhecido(Exception):
    """Pedido de token para papel que nao esta em `papeis_de_dominio`."""


@dataclass(frozen=True, slots=True)
class Autenticacao:
    """O que a aplicacao precisa para autenticar. Montado uma vez, no boot.

    `segredo` chega PRONTO, e nao e lido aqui dentro: quem monta o processo sabe
    onde o `.env` esta, e um adapter que fosse procurar arquivo repetiria a
    armadilha que a §3.2 da Fase 2 mediu. A recusa alta na ausencia acontece no
    boot, que e onde ela e visivel.
    """

    superficie: Superficie
    segredo: str

    def emitir_token(self, sub: str, papel: str, **kwargs) -> str:
        """Assina um token para um papel de DOMINIO. Recusa qualquer outro.

        E aqui que a D2 vira comportamento: o core assina o que mandarem, e este
        e o unico lugar do produto que decide se um papel pode virar token.
        """
        if papel not in self.superficie.papeis_de_dominio:
            raise PapelDesconhecido(
                f"{papel!r} nao esta em `papeis_de_dominio` de `api_surface.yaml`. "
                "Papel de EXERCICIO (`03` §7 — facilitador, operador, avaliador) "
                "nunca entra: `scripts/check_api_surface.py` o recusa da lista, e "
                "por isso ele nao tem como chegar a um token."
            )
        return issue(sub, papel, secret=self.segredo, **kwargs)


def autenticacao_do_ambiente(superficie: Superficie | None = None) -> Autenticacao:
    """Monta a partir do ambiente. Levanta se `AURORA_JWT_SECRET` nao existir."""
    return Autenticacao(
        superficie=carregar() if superficie is None else superficie,
        segredo=jwt_secret(os.environ),
    )


async def autoriza(request: Request) -> TokenClaims | None:
    """Dependencia GLOBAL: nenhuma rota escapa, e nenhuma a declara.

    Nao receber o repositorio e a garantia, e nao um detalhe de assinatura — ver
    o cabecalho. Devolve as claims para quem quiser, e `None` em rota publica.
    """
    autenticacao: Autenticacao = request.app.state.autenticacao
    rota = request.scope.get("route")
    declarada = (
        None
        if rota is None
        else autenticacao.superficie.rota(request.method, getattr(rota, "path", ""))
    )

    if declarada is None:
        raise HTTPException(status_code=403, detail=NEGADO)

    if declarada.publica:
        return None

    cabecalho = request.headers.get("authorization") or ""
    if not cabecalho.startswith(PREFIXO):
        raise HTTPException(
            status_code=401,
            detail="autenticacao exigida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify(cabecalho[len(PREFIXO):], secret=autenticacao.segredo)
    except TokenInvalid:
        raise HTTPException(
            status_code=401,
            detail="autenticacao exigida",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if claims.role not in declarada.papeis:
        raise HTTPException(status_code=403, detail=NEGADO)

    return claims
