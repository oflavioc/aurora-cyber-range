"""JWT — emissao, verificacao, e o segredo que assina.

AUTORIDADE
----------
`07_IMPLEMENTATION_PHASES.md` Fase 3 (*"academus-api com JWT, RBAC"*);
`05_SECURITY_REQUIREMENTS.md` §8 (*"nenhum servico exposto sem autenticacao"*);
`00_MASTER_SPEC.md` §8. A decisao D3 do registro da Fase 3 fixa o que o token
carrega: `sub`, papel **de dominio**, expiracao.

ESTE MODULO NAO CONHECE PAPEL NENHUM, E E ISSO QUE FAZ A D2 VALER
------------------------------------------------------------------
`issue` recebe `role: str` e nao julga o valor. O vocabulario de papeis e do
ADAPTER — `domains/academus/api_surface.yaml`, campo `papeis_de_dominio` —, e e
o adapter que recusa o que nao esta la.

Nao e delegacao por comodidade: o core que conhecesse `aluno` e `professor`
estaria com dominio dentro, pela mesma porta que o invariante 1 fecha para
import. E um core que conhecesse `facilitador` teria desenho de exercicio, que e
a metade da D2 que nenhum verificador de import pega.

POR QUE `range-core/api/`, e nao um modulo na raiz
---------------------------------------------------
`01` §2 enumera `range-core/api/` no layout. O contraste com `determinism.py` —
que foi para a raiz porque nao era de diretorio nenhum — e o argumento: aqui ha
diretorio declarado pela spec, e usa-lo nao inventa layout.

POR QUE `PyJWT`, E NAO HS256 ESCRITO A MAO
-------------------------------------------
Assinar HS256 com `hmac` e `base64` sao vinte linhas, e o projeto ja tem o
habito de nao trazer dependencia por conforto. A diferenca aqui e que as vinte
linhas sao de **verificacao**, nao de assinatura, e os modos de falha conhecidos
sao dois:

- `alg: none` — um verificador escrito a mao que le o `alg` do proprio token e
  confia nele aceita qualquer coisa. `jwt.decode(..., algorithms=["HS256"])`
  recusa por construcao, e ha prova negativa disso na suite.
- comparacao de assinatura sem tempo constante.

`CLAUDE.md` permite criptografia legitima da aplicacao explicitamente, e
`tools/check_security_constraints.py` foi escrito para nao confundir import de
biblioteca criptografica com comportamento ofensivo. Fecho transitivo VAZIO —
`PyJWT` nao tem dependencia —, conferido por `pip download`.

O SEGREDO SEGUE A DISCIPLINA DO `RANDOM_SEED`, E NAO O VALOR DELE
------------------------------------------------------------------
Mesma forma de `determinism.random_seed`: ambiente primeiro, `.env` como fonte
local, **sem valor padrao**, recusa alta na ausencia, e lido por codigo do core.

O QUE NAO E A MESMA COISA, e o registro dizia errado ate este commit: derivar o
segredo de assinatura do `RANDOM_SEED` seria **publicar a chave**. O seed e um
valor reproduzivel, versionado em `.env.example` e impresso em log de exercicio
por desenho — `06` T8 exige que duas execucoes com o mesmo seed produzam dataset
identico. Uma chave HS256 derivada dele seria conhecida por quem tem o repo.

`05` §8 fala de **senha de seed** derivada do `RANDOM_SEED`, que e outra coisa:
credencial de persona sintetica dentro do exercicio. A §3 do registro da Fase 3
afirmava a leitura errada, e este commit a corrige.

O PLACEHOLDER VAZIO EM `.env.example`, e por que ele nao e descuido
--------------------------------------------------------------------
`AURORA_JWT_SECRET=` esta **vazio** no exemplo, e nao com um texto do tipo
"troque-por-valor-gerado-localmente".

O motivo e a assimetria entre os segredos daquele arquivo. Senha de banco
copiada do exemplo falha no `connect`, alto e na hora. Segredo de JWT copiado do
exemplo **funciona** — e o sistema sobe assinando com uma chave que esta
versionada neste repositorio. Um segredo errado que se anuncia e menos perigoso
que um que se comporta.

Deixando o placeholder vazio, "copiei o exemplo" e "nao configurei" viram o
MESMO caso, e a recusa que ja existe cobre os dois. `tests/test_api_tokens.py`
le `.env.example` e afirma que o valor de la e recusado — se alguem repuser um
texto ali, o teste fica vermelho.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import jwt

from range_core.determinism import read_dotenv

#: O nome da variavel. Uma so ocorrencia literal, pelo mesmo motivo de
#: `RANDOM_SEED`: nome escrito duas vezes diverge uma.
JWT_SECRET = "AURORA_JWT_SECRET"

#: HS256 e fixo, e nao negociado com o token. Ver o cabecalho.
ALGORITMO = "HS256"

#: Chave curta e forca bruta offline a partir de UM token capturado. 32 bytes e
#: o tamanho da propria saida do HMAC-SHA256: abaixo disso a chave e o elo mais
#: fraco do que ela assina.
TAMANHO_MINIMO = 32


class SecretUnavailable(Exception):
    """Nao ha `AURORA_JWT_SECRET`, ou o valor nao serve.

    RECUSA ALTA, E NUNCA VALOR PADRAO — a mesma regra de `SeedUnavailable`, e
    aqui ela e mais dura: um seed inventado reproduz a si mesmo, um segredo
    inventado **assina em nome de todo mundo**. Servico que sobe com chave
    padrao autentica quem tiver lido o codigo.
    """


class TokenInvalid(Exception):
    """Token ausente, expirado, adulterado, ou assinado com outra chave.

    UM TIPO SO, de proposito. Distinguir "expirado" de "assinatura invalida" na
    excecao convida a distinguir na RESPOSTA, e a resposta que explica por que o
    token nao serve informa quem esta tentando descobrir.
    """


def jwt_secret(
    env: Mapping[str, str] | None = None,
    *,
    dotenv_path: Path | str | None = None,
) -> str:
    """O segredo de assinatura, do ambiente ou de um `.env`. Levanta se nao houver.

    Ambiente primeiro e `dotenv_path` como PARAMETRO — as duas escolhas sao as
    de `random_seed`, pelos mesmos motivos: em container a variavel chega pelo
    ambiente, e o nucleo nao sai procurando `.env` a partir do CWD.
    """
    ambiente = os.environ if env is None else env
    bruto = ambiente.get(JWT_SECRET)

    if bruto is None and dotenv_path is not None:
        bruto = read_dotenv(Path(dotenv_path)).get(JWT_SECRET)

    if bruto is None or str(bruto).strip() == "":
        onde = f" nem em {dotenv_path}" if dotenv_path is not None else ""
        raise SecretUnavailable(
            f"{JWT_SECRET} nao esta no ambiente{onde}. Nao ha valor padrao de "
            "proposito: chave de assinatura embutida no codigo autentica quem "
            "leu o codigo. Gere localmente — `python -c \"import secrets; "
            "print(secrets.token_urlsafe(48))\"` — e nunca versione o valor. O "
            "placeholder em `.env.example` e VAZIO pelo mesmo motivo."
        )

    valor = str(bruto).strip()
    if len(valor) < TAMANHO_MINIMO:
        raise SecretUnavailable(
            f"{JWT_SECRET} tem {len(valor)} caracteres, e o minimo e "
            f"{TAMANHO_MINIMO}. Chave curta e quebrada offline a partir de um "
            "unico token capturado, sem tocar no servico."
        )
    return valor


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """O que o token carrega. **Papel de EXERCICIO nao esta aqui** — D2/D3.

    Tres campos, e nenhum a mais. Cada claim novo e superficie: vai para o
    `api_surface.yaml` e passa a ser conferido por `scripts/check_api_surface.py`
    nas duas direcoes, exatamente como rota.
    """

    sub: str
    role: str
    exp: int


def _payload(sub: str, role: str, exp: int) -> dict[str, object]:
    """As claims, num literal so.

    ESTE DICIONARIO E LIDO POR AST por `scripts/check_api_surface.py`, que exige
    igualdade com `token.claims` do `api_surface.yaml` nas duas direcoes. Claim
    acrescentado aqui e nao declarado la reprova — e e essa direcao que importa,
    porque e por ela que uma `persona` de exercicio entraria no token sem
    nenhum verificador de import notar.

    Por isso as chaves sao literais numa expressao unica, e nao montadas: a
    checagem enxerga `ast.Dict`, e nao adivinha `update()`.
    """
    return {"sub": sub, "role": role, "exp": exp}


def issue(
    sub: str,
    role: str,
    *,
    secret: str,
    valido_por: int = 3600,
    now: float | None = None,
) -> str:
    """Assina um token. **Nao julga `role`** — quem julga e o adapter.

    `now` e parametro para o teste fixar o instante sem congelar o relogio do
    processo. E hora de PAREDE, e nao `exercise_timestamp`: expiracao de sessao
    nao rebobina com rollback, e um token que voltasse a valer depois de um
    `simulation_epoch` novo seria credencial ressuscitada por evento de
    simulacao.
    """
    instante = time.time() if now is None else now
    return jwt.encode(
        _payload(sub, role, int(instante) + valido_por),
        secret,
        algorithm=ALGORITMO,
    )


def verify(token: str, *, secret: str, now: float | None = None) -> TokenClaims:
    """Verifica e devolve as claims. Levanta `TokenInvalid` para qualquer defeito.

    `algorithms=[ALGORITMO]` e o que recusa `alg: none` — a lista e do
    VERIFICADOR, e nao do token. `require` recusa token sem `exp`, que de outro
    jeito seria credencial eterna assinada corretamente.

    Com `now` passado, a expiracao e conferida AQUI e nao pela biblioteca: quem
    fixa o instante e o teste, e delegar a checagem a `PyJWT` neste caso faria o
    teste de expiracao depender do relogio da maquina, que e a forma de um teste
    passar por motivo errado.
    """
    try:
        bruto = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITMO],
            options={"require": ["sub", "role", "exp"], "verify_exp": now is None},
            leeway=0,
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalid(f"token recusado: {type(exc).__name__}") from exc

    exp = int(bruto["exp"])
    if now is not None and now >= exp:
        raise TokenInvalid("token expirado")

    return TokenClaims(sub=str(bruto["sub"]), role=str(bruto["role"]), exp=exp)
