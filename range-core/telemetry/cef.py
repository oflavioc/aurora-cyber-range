"""A linha CEF — a MESMA projecao que vai para o event store, em formato de fio.

AUTORIDADE
----------
`08_EVIDENCE_SIMULATOR.md` §1 e §2, `02_DOMAIN_ACADEMUS.md` §10, e o item 4 da
DoD da Fase 9.

H1 DA SEGUNDA AUDITORIA — O QUE ESTE MODULO EXISTE PARA IMPEDIR
================================================================
`08` §2 diz que a telemetria CEF e projecao, *"e isso unifica evidence-simulator
e telemetry-forwarder sob um contrato so"*. A primeira implementacao tinha
**dois** caminhos: o arquivo `cef.log` era escrito por um gerador de dominio com
tabela propria, e o `telemetry_emitted` saia de `forwarder.programar` com o
catalogo de `02` §10. Para o mesmo fato, o arquivo dizia `initial_access|…|5` e
o evento dizia `SERVICE_ACCOUNT_ANOMALY`, severidade 7, `outcome=success`.

Duas implementacoes coerentes hoje nao provam nada sobre amanha — e estas duas
ja nasceram divergentes. Pior: o teste que deveria pegar isso **localizava a
linha CEF pela `fact_class`**, ou seja, dependia da divergencia para funcionar.

A saida nao e um terceiro verificador comparando os dois. E ter **um produtor
so**: `programar` monta o payload, e este modulo o RENDERIZA. O que o arquivo
diz e o que o evento carrega, byte a byte, porque e o mesmo dicionario.

O CABECALHO CONSOME DUAS CHAVES; O RESTO VIRA EXTENSAO
=======================================================
    CEF:0|vendor|product|version|<signature>|<name>|<severity>|<extensoes>

`signature` e `severity` sao campos do CABECALHO no formato, entao saem do
payload e entram ali. **Toda outra chave do payload vira extensao, na ordem em
que o payload a traz** — a regra e total e nao tem tabela: chave nova no
contrato de telemetria aparece na linha sem que ninguem precise lembrar, que e
o oposto do mapa paralelo que produziu o H1.

`cs1`-`cs4` nao aparecem aqui, e a ausencia e a norma: `02` §10 os reserva para
contexto do DOMINIO (campus, curso, semestre, disciplina). A versao anterior
punha `credential_state` em `cs1` — campo reservado usado para o que coubesse,
e ainda por cima com o veredito do gabarito dentro (B1).

O INSTANTE VIAJA NO PREFIXO SYSLOG, E NAO NUMA EXTENSAO
========================================================
CEF viaja sobre syslog, e o cabecalho de syslog e quem carrega o carimbo de
recebimento. Poe-lo aqui, e nao num `rt=`, e o que mantem a parte CEF **inteira**
derivada do payload: o que o arquivo tem a mais que o evento e o carimbo do
transporte, e nao um campo com outro valor. O evento nao precisa dele — o store
carimba o proprio no append (`09` §2).

O instante e `exercise_time`, pela mesma razao de `vpn.py`: o gabarito o declara
em tempo de exercicio, e converter para data absoluta exigiria um T0 que so
existe em execucao.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["VERSAO", "CHAVES_DO_CABECALHO", "linha"]

#: A versao do cabecalho CEF. `CEF:0` e a unica publicada.
VERSAO = "CEF:0"

#: As chaves do payload que o CABECALHO consome — toda outra vira extensao.
#: Declaradas aqui e consumidas pelo laco, para que a regra "o resto vira
#: extensao" seja derivada de UMA lista e nao afirmada em dois lugares (R9 §8).
CHAVES_DO_CABECALHO = ("signature", "severity")

#: `|` e `=` sao separadores do formato e precisam de escape; a ordem importa,
#: porque escapar `\` depois criaria escape duplo.
_ESCAPES = (("\\", "\\\\"), ("|", "\\|"), ("=", "\\="))


def _escapar(valor: object) -> str:
    texto = str(valor)
    for alvo, substituto in _ESCAPES:
        texto = texto.replace(alvo, substituto)
    return texto


def linha(
    payload: Mapping,
    *,
    vendor: str,
    produto: str,
    nome: str,
    instante: str,
    origem: str,
    versao: str = "1.0",
) -> str:
    """A linha de fio deste payload de telemetria.

    `vendor` e `produto` vem do CONTRATO (`05` §5.1 — produto ficticio, nunca
    nome de fornecedor real de mercado, *"em nenhum campo"*); `nome`, `instante`
    e `origem` sao do fato, e sao o que o transporte acrescenta ao payload:
    respectivamente o verbo observado, o carimbo de syslog e o host que assina a
    linha.

    NENHUM DOS TRES E CAMPO DE `02` §10, e por isso nenhum entra como extensao:
    a superficie de extensao e exatamente o payload.
    """
    cabecalho = "|".join(
        (
            VERSAO,
            _escapar(vendor),
            _escapar(produto),
            _escapar(versao),
            _escapar(payload.get("signature", "event")),
            _escapar(nome),
            str(payload.get("severity", "")),
        )
    )
    extensoes = " ".join(
        f"{chave}={_escapar(valor)}"
        for chave, valor in payload.items()
        if chave not in CHAVES_DO_CABECALHO
    )
    return f"{instante} {origem} {cabecalho}|{extensoes}"
