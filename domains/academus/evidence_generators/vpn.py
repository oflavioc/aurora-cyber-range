"""`vpn.log` — a projecao syslog do acesso remoto. `08` §3.

O QUE ESTA FONTE CARREGA
========================
`08` §3: *"autenticacao sem MFA, horario anomalo, geolocalizacao
inconsistente"*. As tres sao **leituras** que o time azul faz sobre os campos do
fato, e nao campos a mais: o horario esta em `exercise_time`, a ausencia de MFA
em `mfa`, e a inconsistencia de origem em `source_ip` — cruzado com o que se
espera de uma conta de servico.

A DESCOBERTA E TRABALHO DO PARTICIPANTE, e por isso a linha nao traz veredito.
Nao ha `suspicious=true` nem `anomaly_score`: `08` §2 poe a dificuldade em
`discoverability`, que e do gabarito e nao da evidencia. Um campo de julgamento
aqui entregaria a resposta e, pior, misturaria as camadas de `00` §3 — evidencia
observavel virando avaliacao.

O INSTANTE E `exercise_time`, E NAO UM RELOGIO DE PAREDE
=========================================================
O log carrega o tempo do EXERCICIO (`T-17d 02:14`), que e o que o fato declara.
Converter para data absoluta exigiria um T0, que so existe em execucao — e a
projecao e deterministica e anterior a qualquer sessao. `00` §5.6 tem tres
marcas; o ground truth usa a do exercicio, e a evidencia a espelha.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

__all__ = ["gerar"]

#: O daemon que assina a linha. Produto FICTICIO, `05` §5.1 — nunca nome de
#: fornecedor real de mercado, em campo nenhum.
PROCESSO = "auroravpnd"


def gerar(fatos: Sequence[Mapping]) -> str:
    """Uma linha syslog-like por fato.

    Campo ausente vira `-`, que e a convencao de syslog para *"nao registrado"*
    e nao se confunde com vazio medido.
    """
    linhas = []
    for fato in fatos:
        campos = [
            f"user={fato.get('actor', '-')}",
            f"src={fato.get('source_ip', '-')}",
            f"action={fato.get('action', '-')}",
            f"mfa={fato.get('mfa', '-')}",
            f"credential={fato.get('credential_state', '-')}",
        ]
        alvo = fato.get("dest", "-")
        linhas.append(
            f"{fato.get('exercise_time', '-')} {alvo} {PROCESSO}: " + " ".join(campos)
        )
    return "\n".join(linhas)
