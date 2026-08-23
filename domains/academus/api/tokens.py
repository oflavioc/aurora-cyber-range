"""O token da `academus-api` — emissor próprio, e `persona` ao lado de `role`.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §6, na forma que o `spec-change` #52 lhe deu;
`09_EVENT_MODEL.md` §1 e §1.1; `05_SECURITY_REQUIREMENTS.md` §8. A superfície
que ele serve é `domains/academus/api_surface.yaml`.

POR QUE UM TERCEIRO EMISSOR, E NÃO UMA CLAIM A MAIS NO PRIMEIRO
----------------------------------------------------------------
`range-core/api/tokens.py::_payload` assina `{sub, role, exp}`, e **medido: ele
serve DOIS chamadores** — este adapter e o gm-console
(`range-core/api/app.py:259`). Acrescentar `persona` àquele literal poria a
claim no token de **facilitação**, que é exatamente o risco que o docstring
daquela função guarda: *"é por ela que uma `persona` de exercício entraria no
token sem nenhum verificador de import notar"*.

O movimento é o mesmo que `range-core/participant/api/tokens.py` fez na peça 3,
e pelo mesmo motivo: **uma função única assinando duas vocações**. O que se
compartilha é a decisão criptográfica — `ALGORITMO` e `TokenInvalid` —, porque
duplicá-la criaria duas respostas para `alg: none`. O que **não** se compartilha
é o `_payload`: é ele que carrega a vocação.

`persona` AO LADO DE `role`, E NÃO NO LUGAR DELE
------------------------------------------------
É a diferença para a superfície de participante, e ela é do desenho. Lá a
persona **é** a autorização: `persona` entra no lugar de `role` porque quem
invoca aquela superfície é participante e nada mais.

Aqui os dois coexistem porque respondem a perguntas distintas:

- `role` é **papel de domínio** — `aluno`, `professor`, `secretaria`,
  `financeiro` —, e é ele que autoriza a rota. `01` §6: *"o que autoriza uma
  rota do adapter é papel de domínio, nunca persona"*;
- `persona` é **quem age no exercício**, e existe para o envelope. `09` §1.1
  torna `actor_id` e `persona` obrigatórios na camada `participant_action`, e
  `09` §1 exibe como exemplo normativo do envelope universal justamente um
  `audit_query_performed` com `producer: academus-api` e `persona: ti`.

**O adapter não decide nada com `persona`.** Ele a transporta até o envelope. É
o que separa esta claim de vazamento de desenho de exercício para dentro do
domínio — e é a distinção que o `spec-change` #52 escreveu em `01` §6, depois de
a forma anterior ter sido lida isolada duas vezes.

`persona` É OBRIGATÓRIA, E ISSO É DESENHO
------------------------------------------
`verify` a exige, como a superfície de participante exige a dela. Token de
domínio sem `persona` é token cujos atos não têm a quem ser atribuídos — e, na
camada de `09` §2 em que este adapter emite, é envelope que o contrato recusa.

**Não há default**, pela mesma disciplina D5 das credenciais de persona: um
default silencioso carimbaria no store append-only uma persona que não agiu, e
é a classe de defeito que não se corrige retroativamente. Quem emite o token
diz qual persona é.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt

from range_core.api.tokens import ALGORITMO, TokenInvalid

#: As claims exigidas na verificação. Lista do VERIFICADOR, e não do token.
EXIGIDAS = ["sub", "role", "persona", "exp"]


@dataclass(frozen=True, slots=True)
class ClaimsDeDominio:
    """O que o token da `academus-api` carrega.

    Quatro campos. Cada claim nova é superfície: vai para o `api_surface.yaml` e
    passa a ser conferida por `scripts/check_api_surface.py` nas duas direções,
    exatamente como rota.
    """

    sub: str
    role: str
    persona: str
    exp: int


def _payload(sub: str, role: str, persona: str, exp: int) -> dict[str, object]:
    """As claims desta superfície, num literal só.

    **Lido por AST** por `scripts/check_api_surface.py`, que exige igualdade com
    o `token.claims` de `domains/academus/api_surface.yaml` nas duas direções — e
    é o `token.claims` **desta** superfície, não o do console.

    Por isso as chaves são literais numa expressão única, e não montadas: a
    checagem enxerga `ast.Dict`, e não adivinha `update()`.
    """
    return {"sub": sub, "role": role, "persona": persona, "exp": exp}


def issue(
    sub: str,
    role: str,
    persona: str,
    *,
    secret: str,
    valido_por: int = 3600,
    now: float | None = None,
) -> str:
    """Assina um token de domínio. **Não julga `role` nem `persona`.**

    Quem julga `role` é `Autenticacao.emitir_token`, contra `papeis_de_dominio`
    da superfície — é lá que a D2 vira comportamento, e não aqui.

    `now` é parâmetro para o teste fixar o instante sem congelar o relógio do
    processo, e é hora de **parede**: expiração de sessão não rebobina com
    rollback, e um token que voltasse a valer depois de um `simulation_epoch`
    novo seria credencial ressuscitada por evento de simulação.
    """
    instante = time.time() if now is None else now
    return jwt.encode(
        _payload(sub, role, persona, int(instante) + valido_por),
        secret,
        algorithm=ALGORITMO,
    )


def verify(
    token: str, *, secret: str, now: float | None = None
) -> ClaimsDeDominio:
    """Verifica e devolve as claims. `TokenInvalid` para qualquer defeito.

    `algorithms=[ALGORITMO]` é o que recusa `alg: none` — a lista é do
    VERIFICADOR, e não do token.

    `require` inclui `persona`: token sem ela é token de outra superfície — o do
    console tem `{sub, role, exp}` —, e aceitá-lo aqui faria a rota instrumentada
    gravar um envelope sem o campo que `09` §1.1 torna obrigatório.

    Com `now` passado, a expiração é conferida AQUI e não pela biblioteca: quem
    fixa o instante é o teste, e delegar a checagem faria o teste de expiração
    depender do relógio da máquina.
    """
    try:
        bruto = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITMO],
            options={"require": EXIGIDAS, "verify_exp": now is None},
            leeway=0,
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalid(f"token recusado: {type(exc).__name__}") from exc

    exp = int(bruto["exp"])
    if now is not None and now >= exp:
        raise TokenInvalid("token expirado")

    return ClaimsDeDominio(
        sub=str(bruto["sub"]),
        role=str(bruto["role"]),
        persona=str(bruto["persona"]),
        exp=exp,
    )
