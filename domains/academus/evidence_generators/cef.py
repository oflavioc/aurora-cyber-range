"""`cef.log` — a telemetria CEF como PROJECAO. `08` §2 e `02` §10.

A FRASE QUE ESTE MODULO EXISTE PARA TORNAR VERDADEIRA
======================================================
`08` §2: *"a telemetria CEF e projecao, nao emissao independente. Isso unifica
evidence-simulator e telemetry-forwarder sob um contrato so."*

Telemetria gerada por um caminho proprio divergiria do `vpn.log` e do
`identity_audit.jsonl` na primeira mudanca de codigo — e a divergencia so
apareceria quando o time azul achasse a contradicao, no meio do exercicio. Aqui
o CEF sai **do mesmo fato** que as outras fontes, pelo mesmo motor.

O QUE ESTE MODULO NAO E
=======================
Nao e o telemetry-forwarder. O item 4 da DoD tem duas metades, e esta e a do
ARQUIVO; a outra e `telemetry_emitted` indo para o event store, que e evento de
catalogo (`09` §4.1, `effect_class: machine`, `metric_side: none`) e tem peca
propria. As duas compartilham este gerador, que e exatamente o que *"um contrato
so"* significa.

VENDOR E PRODUCT SAO LIDOS DO CONTRATO
=======================================
`05` §5.1 e categorico: vendor/product identificam produto **ficticio**, nunca
nome de fornecedor real de mercado, *"em nenhum campo, nem em documentacao de
exemplo"*. O proposito e tecnico — impedir que evidencia sintetica seja
confundida com telemetria real de um produto, dentro ou fora do exercicio.

Os valores vivem em `contracts/evidence.schema.yaml`
(`x-aurora-security-constraints.cef_vendor` / `cef_product`) e chegam aqui por
**parametro**. Escreve-los no modulo seria a P1-13 outra vez: duas fontes para a
mesma norma de seguranca, divergindo em silencio.

E E POR ISSO QUE O PACOTE EXPOE UMA FABRICA, e nao uma tabela pronta: este
gerador precisa de um insumo do contrato, e ler o contrato no import seria
efeito colateral de importacao (R9 §1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

__all__ = ["fabricar", "CEF_VERSAO", "SEVERIDADE_PADRAO"]

#: A versao do cabecalho CEF. `CEF:0` e a unica publicada.
CEF_VERSAO = "CEF:0"

#: `02` §10 lista `severity` entre os campos. Sem escala declarada na spec, a
#: projecao usa um valor unico e NAO julga: severidade variavel por fato seria
#: avaliacao embutida na evidencia — a mesma confusao de camadas que `vpn.py`
#: recusa ao nao escrever `suspicious=true`.
SEVERIDADE_PADRAO = 5

#: `|` e `=` sao separadores do formato e precisam de escape no CEF; a ordem
#: importa, porque escapar `\` depois criaria escape duplo.
_ESCAPES = (("\\", "\\\\"), ("|", "\\|"), ("=", "\\="))


def _escapar(valor: object) -> str:
    texto = str(valor)
    for alvo, substituto in _ESCAPES:
        texto = texto.replace(alvo, substituto)
    return texto


def fabricar(vendor: str, produto: str, versao: str = "1.0") -> Callable:
    """Devolve o gerador de CEF com o vendor/product do CONTRATO.

    Fabrica, e nao modulo com constante: ver o cabecalho.
    """

    def gerar(fatos: Sequence[Mapping]) -> str:
        linhas = []
        for fato in fatos:
            # A `signature` e a CLASSE do fato e o `name` e a acao — os dois
            # saem do fato, nunca de uma tabela de rotulos aqui. Uma tabela
            # exigiria manutencao paralela ao gabarito, e o rotulo errado num
            # SIEM e pior que rotulo ausente.
            assinatura = _escapar(fato.get("fact_class", "event"))
            nome = _escapar(fato.get("action", "-"))
            cabecalho = "|".join(
                (
                    CEF_VERSAO,
                    _escapar(vendor),
                    _escapar(produto),
                    _escapar(versao),
                    assinatura,
                    nome,
                    str(SEVERIDADE_PADRAO),
                )
            )
            extensoes = []
            for chave, campo in (
                ("src", "source_ip"),
                ("suser", "actor"),
                ("dst", "dest"),
                ("cnt", "records_affected"),
                ("cs1", "credential_state"),
                ("cs2", "mfa"),
                ("rt", "exercise_time"),
            ):
                if campo in fato:
                    extensoes.append(f"{chave}={_escapar(fato[campo])}")
            linhas.append(cabecalho + "|" + " ".join(extensoes))
        return "\n".join(linhas)

    return gerar
