"""O gabarito da Linha A: o ground truth do INCIDENTE (ransomware), sintetizado.

P7-10 — POR QUE ESTE MODULO EXISTE, E A DECISAO QUE ELE CARREGA
================================================================
O gerador da Linha B (`gabarito.py` + `linha_b.py`) LE do banco: os
`grade_change_retroactive` sao dados academicos reais, semeados, e o gabarito
descreve o que EXISTE. A Linha A e de outra natureza — o acesso inicial por
credencial comprometida, a escalacao de privilegio, a exfiltracao — e **nao e
dado academico**: e o incidente sobreposto. Nao ha, nem deve haver, tabela de
VPN ou de exfiltracao no Postgres do Academus; isso seria evidencia, e evidencia
e projecao de fato (Fase 9, `08_EVIDENCE_SIMULATOR.md`), nao business state.

Entao a Linha A e **sintetizada deterministicamente do seed**, e nao lida do
banco. A decisao, na altitude do registro da Fase 7 §5.2 (a spec fixa a FORMA; o
conteudo determinista e reversivel e escolha do gerador, documentada):

- **Sintetizar, nao semear tabela de incidente.** Semear VPN/exfiltracao no
  banco anteciparia o evidence-simulator da Fase 9 e poria incidente dentro do
  business state — a fronteira que `01` §2 separa. O incidente e overlay, e o
  overlay nasce do seed.
- **A forma e a de `04` §3 e do exemplo positivo de `contracts/ground_truth.schema.yaml`**
  — `initial_access` (vpn_login, `source_ip` de faixa de documentacao,
  `credential_state`, `mfa`, `projections`, `discoverability`),
  `privilege_escalation`, `exfiltration`. Nao invento campo: caso o exemplo do
  contrato mude, este modulo diverge alto no teste de forma.
- **O ator e uma conta de SERVICO comprometida** (`svc_academus`, como o exemplo
  do contrato), e nao a `conta_alvo` da Linha B. Sao dois vetores distintos: a
  Linha B e adulteracao de nota por conta docente comprometida; a Linha A e o
  ransomware por credencial de servico. Conflati-los faria as duas metricas
  medirem o mesmo ator.

O QUE ISTO CORRIGE
==================
Antes da P7-10, `gabarito.predicados_de_verificacao` devolvia `containment` sobre
`grade_change_retroactive` — a contencao da Linha B — e `service_restoration:
not_applicable`. Mas `04` §3, `03` §3.1 e o exemplo do contrato definem a
contencao do PACK como a do INCIDENTE: `vpn_access_revoked` +
`identity_scope_disabled` + ausencia de exfiltracao. A consequencia media na
autoria do pack de 4 h (Fase 7): `TTCV`/`TTRV` incomputaveis, o par de contencao
medindo integridade. Os `verification_predicates` do pack passam a ser os do
incidente; os casos `GC-` da Linha B seguem sendo a linha de INTEGRIDADE (TTIV),
que e outra pergunta.
"""

from __future__ import annotations

from contracts.generated.events import (
    IDENTITY_SCOPE_DISABLED,
    VPN_ACCESS_REVOKED,
)
from domains.academus.generated.flags import (
    ACADEMUS_ENROLLMENT_OFFLINE,
    ACADEMUS_LMS_DEGRADED,
)
from range_core.determinism import seeded_random

#: A conta de servico comprometida — o ator do incidente. `04` §3 e o exemplo do
#: contrato usam `svc_academus`. Nao e a `conta_alvo` da Linha B (conta docente):
#: sao dois vetores.
ATOR_DO_INCIDENTE = "svc_academus"

#: `^GT-[A-Z0-9]+-[0-9]+$` (`ground_truth.schema.yaml`). `A` de Linha A; o sufixo
#: e numero. O `check_gabarito_fora_do_git` reconhece esta forma como gabarito, e
#: por isso o `{n}` NUNCA e escrito como digito literal aqui — so por format.
FATO = "GT-A-{:03d}"

#: `05` §3 e RFC 5737: IP so de faixa de documentacao. `check_synthetic_data`
#: recusa qualquer outra. O octeto final e sorteado do seed.
REDE_DE_DOCUMENTACAO = "198.51.100.{}"

#: O remetente forjado do phishing — `08` §3: *"phishing de recadastramento,
#: origem da Linha A"*.
#:
#: E ELE QUE O DOMINIO DO LINK DERIVA, e essa dependencia e deliberada: o
#: gerador de `email.eml` monta a URL a partir deste valor mais um sufixo
#: reservado a documentacao (`05` §2). Um dominio escrito a mao no gerador seria
#: entidade que o ground truth nao fixou — o item 1 entrando pela porta do
#: texto, onde o oraculo de endereco nao olha.
#:
#: SEM `_`, e a restricao vem do uso: o valor vira rotulo de host, e `_` nao e
#: valido em hostname. `svc_academus` pode te-lo porque e ator e nunca vira
#: dominio.
REMETENTE_FORJADO = "ti-recadastro"


def facts(seed: int) -> list[dict]:
    """Os fatos do incidente, sintetizados do seed — a forma de `04` §3.

    Determinista: mesmo seed, mesmos fatos; a prova negativa (dois seeds
    diferem) e a de `prova_seed_completo` estendida no teste desta peca.
    """
    r = seeded_random("academus:linha_a", seed=seed)

    # O acesso inicial: login VPN da credencial de servico, fora de expediente,
    # sem MFA. Os instantes sao relativos ao exercicio (`T-<n>d HH:MM`), a forma
    # que `04` §3 usa para o timeline do incidente ANTES do T0 do exercicio.
    dia_acesso = r.randint(15, 20)
    hora_acesso = r.randint(0, 4)
    minuto_acesso = r.randint(0, 59)
    octeto = r.randint(10, 250)
    registros_exfiltrados = r.randrange(800, 4000, 100)

    # O phishing ANTECEDE o acesso inicial, e e o que o possibilita — `08` §3 o
    # chama de "origem da Linha A". Dois a cinco dias antes: e a janela em que a
    # credencial e colhida e usada, curta o bastante para a correlacao ser
    # descobrivel e longa o bastante para nao ser obvia.
    dias_antes_do_acesso = r.randint(2, 5)
    hora_phishing = r.randint(9, 17)
    octeto_do_mta = r.randint(10, 250)

    return [
        {
            # A ORIGEM. Sem este fato, `email.eml` seria conteudo autoral em vez
            # de projecao, e `08` §3 exige a fonte com origem na Linha A.
            "fact_id": FATO.format(1),
            "fact_class": "phishing_delivery",
            "actor": REMETENTE_FORJADO,
            "action": "credential_phishing_email",
            "source_ip": REDE_DE_DOCUMENTACAO.format(octeto_do_mta),
            # O DESTINATARIO e a conta que sera comprometida: e o que liga o
            # phishing ao `initial_access` sem precisar de campo de referencia,
            # que o contrato nao tem.
            "dest": ATOR_DO_INCIDENTE,
            "exercise_time": (
                f"T-{dia_acesso + dias_antes_do_acesso}d {hora_phishing:02d}:11"
            ),
            "projections": ["email"],
            "discoverability": {
                "difficulty": "low",
                "requires": "ler o cabecalho do e-mail e conferir o dominio do link",
            },
        },
        {
            "fact_id": FATO.format(14),
            "fact_class": "initial_access",
            "actor": ATOR_DO_INCIDENTE,
            "action": "vpn_login",
            "source_ip": REDE_DE_DOCUMENTACAO.format(octeto),
            "dest": "vpn-gw-01",
            "exercise_time": f"T-{dia_acesso}d {hora_acesso:02d}:{minuto_acesso:02d}",
            "credential_state": "compromised",
            "mfa": "absent",
            "projections": ["vpn", "identity_audit", "cef"],
            "discoverability": {
                "difficulty": "medium",
                "requires": "correlacionar horario fora de expediente com ausencia de MFA",
            },
        },
        {
            "fact_id": FATO.format(19),
            "fact_class": "privilege_escalation",
            "actor": ATOR_DO_INCIDENTE,
            "action": "identity_scope_expanded",
            "exercise_time": f"T-{dia_acesso - 1}d {(hora_acesso + 1) % 24:02d}:02",
            "projections": ["identity_audit"],
        },
        {
            "fact_id": FATO.format(31),
            "fact_class": "exfiltration",
            "actor": ATOR_DO_INCIDENTE,
            "action": "bulk_export",
            "exercise_time": f"T-{dia_acesso - 2}d {(hora_acesso + 2) % 24:02d}:47",
            "records_affected": registros_exfiltrados,
            "projections": ["database_audit", "cef"],
        },
    ]


def predicados_de_verificacao() -> dict:
    """`containment` e `service_restoration` do INCIDENTE — `04` §3, `03` §3.1.

    E o par que a Fase 7 media como ausente: contencao do pack e a do ransomware,
    e nao a da Linha B. `containment` e sobre estado OBSERVAVEL do mundo (`09`
    §4.0) — a VPN revogada, o escopo desabilitado, e nenhuma exfiltracao nova
    desde que o predicado passou a ser avaliado.

    Estrutura NOVA a cada chamada, pelo mesmo motivo de `gabarito`: o
    `ground_truth` devolvido e dict comum que o chamador pode alterar.
    """
    return {
        "containment": {
            "all": [
                {"event": VPN_ACCESS_REVOKED},
                {
                    "event": IDENTITY_SCOPE_DISABLED,
                    "payload": {"principal": ATOR_DO_INCIDENTE},
                },
                # `since: self` literal, e nao importado: `domains/` nao importa
                # de `range_core.engine.loader` — mesma decisao de `gabarito.py`.
                {"absence_of": {"fact_class": "exfiltration", "since": "self"}},
            ]
        },
        "service_restoration": {
            "all": [
                {"flag_false": ACADEMUS_ENROLLMENT_OFFLINE},
                {"flag_false": ACADEMUS_LMS_DEGRADED},
            ]
        },
    }
