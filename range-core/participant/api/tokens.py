"""O token da `participant-api` — emissor próprio, claims próprias.

AUTORIDADE
----------
`01_ARCHITECTURE.md` §6; `03_EXERCISE_DESIGN.md` §6; `05_SECURITY_REQUIREMENTS.md`
§8. A superfície que ele serve é `range-core/participant/api_surface.yaml`.

POR QUE UM SEGUNDO EMISSOR, E NÃO UMA CLAIM A MAIS NO PRIMEIRO
---------------------------------------------------------------
`range-core/api/tokens.py::_payload` assina `{sub, role, exp}` para o
gm-console, e o seu próprio docstring diz por que a checagem de claims existe:
*"é por ela que uma `persona` de exercício entraria no token sem nenhum
verificador de import notar"*.

Acrescentar `persona` àquele literal realizaria por desenho exatamente o risco
que ele guarda — uma função única assinando duas vocações, e a claim passando a
existir para as duas. Por isso o emissor é próprio, e
`scripts/check_api_surface.py` passa a comparar **cada emissor contra a
superfície dele**, que é o mesmo movimento que `camadas_de_emissao` fez com a
camada de emissão.

`persona` NO LUGAR DE `role`, E NÃO AO LADO
--------------------------------------------
Quem invoca esta superfície é participante, nunca facilitador. Um token daqui
que carregasse `role: facilitador` seria console emitido pela porta do
exercício — e o verificador o recusa por vocabulário proibido do perfil.

AS CREDENCIAIS SÃO DE AMBIENTE, UMA POR PERSONA — DISCIPLINA D5
----------------------------------------------------------------
Sete variáveis, sem default, recusa alta na ausência. É a mesma disciplina que a
Fase 4 aplicou ao console: credencial com default é credencial que vaza para
todo deploy que esqueceu de trocá-la.

**`actor_id` identifica credencial, não humano.** A consequência está declarada
em `docs/progress/fase_6.md`: a condição (4) do predicado de contrassinatura —
`actor_id` distintos — pega **reuso de credencial**, e não dualidade humana.
Dualidade é controle físico da facilitação, na distribuição das sete. Credencial
pessoal futura dá dentes àquela condição sem tocar a spec.
"""

from __future__ import annotations

import hmac
import os
import time
from dataclasses import dataclass

import jwt

from range_core.api.tokens import ALGORITMO, TokenInvalid

#: As sete de `03` §6. A lista vive no `api_surface.yaml`, que é o que o
#: verificador ancora contra `PERSONAS`; aqui ela é derivada do ambiente, e o
#: boot recusa se as duas divergirem — ver `credenciais_do_ambiente`.
PREFIXO_DA_CREDENCIAL = "AURORA_PERSONA_"


class CredencialAusente(Exception):
    """Persona declarada na superfície e sem credencial no ambiente.

    Recusa **alta**, e não degradação para "essa persona não entra": persona sem
    credencial é persona que não pode declarar, e um exercício que sobe assim
    descobre isso no meio da sala.
    """


@dataclass(frozen=True)
class Credenciais:
    """`persona -> segredo`, lido do ambiente e nunca de arquivo versionado."""

    por_persona: dict[str, str]

    def confere(self, persona: str, segredo: str) -> bool:
        """Comparação em tempo constante. `hmac.compare_digest`, nunca `==`."""
        esperado = self.por_persona.get(persona)
        if esperado is None:
            return False
        return hmac.compare_digest(esperado, segredo)


def credenciais_do_ambiente(personas: list[str]) -> Credenciais:
    """Uma variável por persona, sem default, recusa alta na ausência.

    `AURORA_PERSONA_TI`, `AURORA_PERSONA_DPO`, e assim por diante. A lista de
    personas chega como **dado** — vem do `api_surface.yaml`, que é onde o
    verificador a ancora — e não é reescrita aqui: duas listas sobre a mesma
    fronteira divergiriam, e a que diverge em silêncio é sempre a que ninguém
    está olhando.
    """
    encontradas: dict[str, str] = {}
    faltando: list[str] = []
    for persona in sorted(personas):
        valor = os.environ.get(f"{PREFIXO_DA_CREDENCIAL}{persona.upper()}")
        if valor:
            encontradas[persona] = valor
        else:
            faltando.append(persona)

    if faltando:
        nomes = ", ".join(f"{PREFIXO_DA_CREDENCIAL}{p.upper()}" for p in faltando)
        raise CredencialAusente(
            f"persona sem credencial no ambiente: {faltando}.\n"
            f"    Defina {nomes}. Sem default, por D5 — credencial com default é "
            "credencial que vai junto para todo deploy que esqueceu de trocá-la."
        )
    return Credenciais(encontradas)


def _payload(sub: str, persona: str, exp: int) -> dict[str, object]:
    """As claims desta superfície, num literal só.

    **Lido por AST** por `scripts/check_api_surface.py`, que exige igualdade com
    o `token.claims` de `range-core/participant/api_surface.yaml` nas duas
    direções — e é o `token.claims` **desta** superfície, não o do console.

    Por isso as chaves são literais numa expressão única, e não montadas: a
    checagem enxerga `ast.Dict`, e não adivinha `update()`.
    """
    return {"sub": sub, "persona": persona, "exp": exp}


@dataclass(frozen=True)
class ClaimsDeParticipante:
    """As claims verificadas. `persona`, nunca `role`."""

    sub: str
    persona: str
    exp: int


def issue(
    sub: str,
    persona: str,
    *,
    secret: str,
    valido_por: int = 3600,
    now: float | None = None,
) -> str:
    """Assina um token de participante. **Não julga `persona`** — quem julga é a rota.

    Mesma disciplina do emissor do console: `now` é parâmetro para o teste fixar
    o instante, e é hora de **parede** — expiração de sessão não rebobina com
    rollback, e um token que voltasse a valer depois de um `simulation_epoch`
    novo seria credencial ressuscitada por evento de simulação.

    `ALGORITMO` e `TokenInvalid` vêm do emissor do console porque são a mesma
    decisão criptográfica, e duplicá-los criaria duas respostas para `alg: none`.
    O que **não** se compartilha é o `_payload`: é ele que carrega a vocação.
    """
    instante = time.time() if now is None else now
    return jwt.encode(
        _payload(sub, persona, int(instante) + valido_por),
        secret,
        algorithm=ALGORITMO,
    )


def verify(
    token: str, *, secret: str, now: float | None = None
) -> ClaimsDeParticipante:
    """Verifica e devolve as claims. `TokenInvalid` para qualquer defeito.

    `require` inclui `persona`: token sem ela é token de outra superfície, e
    aceitá-lo aqui faria o RBAC por persona resolver contra `None`.
    """
    try:
        bruto = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITMO],
            options={"require": ["sub", "persona", "exp"], "verify_exp": now is None},
            leeway=0,
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalid(f"token recusado: {type(exc).__name__}") from exc

    exp = int(bruto["exp"])
    if now is not None and now >= exp:
        raise TokenInvalid("token expirado")
    return ClaimsDeParticipante(str(bruto["sub"]), str(bruto["persona"]), exp)
