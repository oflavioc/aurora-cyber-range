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

__all__ = ["FONTE", "VERSAO", "CHAVES_DO_CABECALHO", "linha"]

#: A FONTE DE EVIDENCIA que esta telemetria E — `08` §3 e o registro de
#: `x-aurora-registry.source_formats`.
#:
#: B2 DA TERCEIRA AUDITORIA. O nome mora aqui porque ele responde por uma
#: identidade, e nao por uma string solta: **o `telemetry_emitted` do event
#: store e a linha do `cef.log` sao a mesma fonte, vista de dois lugares**. O
#: arquivo era filtrado pela cobertura de projecao e o evento nao era filtrado
#: por nada — entao o SIEM do exercicio mostrava sinal de fato que nao tem linha
#: no arquivo, e ate de fato sem `projections`, que `08` §2 declara INVISIVEL ao
#: time azul.
#:
#: Quem consome: `pack_loader._telemetria_do_pack`, para pedir a `cobertura_de`
#: exatamente o mesmo conjunto que o motor entrega ao gerador.
FONTE = "cef"

#: A versao do cabecalho CEF. `CEF:0` e a unica publicada.
VERSAO = "CEF:0"

#: As chaves do payload que o CABECALHO consome — toda outra vira extensao.
#: Declaradas aqui e consumidas pelo laco, para que a regra "o resto vira
#: extensao" seja derivada de UMA lista e nao afirmada em dois lugares (R9 §8).
#:
#: `event_time` entrou com o H1 da terceira auditoria, e ele e o carimbo do
#: PREFIXO SYSLOG — nao uma extensao. Isso aperta a unificacao em vez de
#: afroxa-la: o instante que o arquivo escreve deixou de vir de fora do payload
#: e passou a sair dele, entao o que o `cef.log` carrega e, agora sem exceção,
#: o que o `telemetry_emitted` carrega.
CHAVES_DO_CABECALHO = ("signature", "severity", "event_time")

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
    origem: str,
    versao: str = "1.0",
) -> str:
    """A linha de fio deste payload de telemetria.

    `vendor` e `produto` vem do CONTRATO (`05` §5.1 — produto ficticio, nunca
    nome de fornecedor real de mercado, *"em nenhum campo"*); `nome` e `origem`
    sao, respectivamente, o verbo observado e o host que assina a linha.

    NENHUM DOS DOIS E CAMPO DE `02` §10, e por isso nenhum entra como extensao:
    a superficie de extensao e exatamente o payload.

    O CARIMBO DE SYSLOG SAI DO PAYLOAD desde o H1 da terceira auditoria — ele e
    `event_time`, a marca de `00` §5.6. Ate entao vinha por parametro, de fora,
    e era a ultima coisa no arquivo que o evento nao tinha.
    """
    instante = str(payload.get("event_time", "-"))
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
