"""`email.eml` — o phishing de recadastramento. `08` §3 e `05` §2.

O QUE `05` §2 EXIGE, E SAO TRES NEGATIVAS
==========================================
    O `.eml` de phishing contem texto e um link para dominio da faixa reservada
    de documentacao. NENHUM ANEXO. Nenhuma URL clicavel para host existente.

Sao tres afirmacoes separadas, e este modulo as satisfaz por CONSTRUCAO, nao por
verificacao posterior:

1. **sem anexo** — nao ha `Content-Disposition`, e nao ha o que anexar;
2. **sem MIME multipart** — `Content-Type: text/plain` e o unico; multipart e o
   veiculo de anexo, e sem ele nao ha onde um caber;
3. **link em sufixo reservado** — a URL e montada do valor que o fato declara,
   mais `.example`.

O DOMINIO DERIVA DO ELENCO, E ISSO FECHA UMA FRESTA DO ITEM 1
==============================================================
O oraculo de `elenco.py` afirma ausencia de invencao **para endereco IP**, que
tem forma fechada. Dominio nao tem: uma rede lexica que o pegasse pegaria
palavra comum do corpo do texto. Entao um dominio escrito a mao aqui seria
entidade inventada passando exatamente onde o oraculo nao olha.

A saida e nao escrever nenhum: o rotulo de host sai de `actor` (o remetente
forjado, declarado no fato), e o sufixo e reservado. **Nada no texto nomeia host
que o ground truth nao tenha fixado.**

`_` VIRA `-` NO ROTULO DE HOST, e a troca e de forma e nao de identidade: `_`
nao e valido em hostname, e `svc_academus` e ator legitimo que nunca deveria
virar dominio sem sanitizacao. A identidade continua legivel — `svc-academus` —
e o participante correlaciona sem esforco.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

__all__ = ["gerar", "SUFIXO_RESERVADO"]

#: `05` §2 e §3 — dominio apenas de faixa reservada a documentacao.
#: `contracts/evidence.schema.yaml` o lista em `allowed_domain_suffixes`, e
#: `dados_sinteticos.hostname_permitido` e quem julga; `.example` e o de RFC 2606
#: e o mais neutro dos declarados.
SUFIXO_RESERVADO = ".example"

ASSUNTO = "Recadastramento obrigatorio de credenciais - acao necessaria"


def _rotulo(valor: str) -> str:
    """O valor do elenco como rotulo de host — ver o cabecalho."""
    return valor.replace("_", "-")


def gerar(fatos: Sequence[Mapping]) -> str:
    """Uma mensagem RFC 5322 por fato de phishing.

    Mensagens multiplas sao separadas por linha em branco. Nao ha `mbox` nem
    envelope: o arquivo e leitura, e um formato de caixa postal exigiria um
    separador que os parsers tratam de formas diferentes.
    """
    mensagens = []
    for fato in fatos:
        remetente = fato.get("actor", "ti")
        destinatario = fato.get("dest", "usuario")
        host = f"{_rotulo(remetente)}{SUFIXO_RESERVADO}"
        mensagens.append(
            "\n".join(
                (
                    f"From: Suporte de TI <{remetente}@{host}>",
                    f"To: <{destinatario}@{_rotulo(destinatario)}{SUFIXO_RESERVADO}>",
                    f"Subject: {ASSUNTO}",
                    f"Date: {fato.get('exercise_time', '-')}",
                    f"X-Originating-IP: {fato.get('source_ip', '-')}",
                    "MIME-Version: 1.0",
                    'Content-Type: text/plain; charset="utf-8"',
                    "",
                    "Prezado(a) usuario(a),",
                    "",
                    "Identificamos que suas credenciais de acesso precisam ser",
                    "recadastradas ate o fim desta semana. Contas nao recadastradas",
                    "serao suspensas automaticamente.",
                    "",
                    f"Acesse: https://{host}/recadastro",
                    "",
                    "Atenciosamente,",
                    "Equipe de Suporte",
                )
            )
        )
    return "\n\n".join(mensagens)
