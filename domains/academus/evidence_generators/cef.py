"""`cef.log` — a telemetria CEF como PROJECAO. `08` §2 e `02` §10.

A FRASE QUE ESTE MODULO EXISTE PARA TORNAR VERDADEIRA
======================================================
`08` §2: *"a telemetria CEF e projecao, nao emissao independente. Isso unifica
evidence-simulator e telemetry-forwarder sob um contrato so."*

E ATE O H1 DA SEGUNDA AUDITORIA ELA ERA FALSA AQUI. Este modulo tinha o proprio
mapeamento — `signature` = `fact_class`, severidade fixa 5, sem `outcome`,
`credential_state` em `cs1` — enquanto `telemetry_emitted` saia do catalogo de
`02` §10. Para o MESMO fato, o arquivo dizia `initial_access|…|5` e o evento
dizia `SERVICE_ACCOUNT_ANOMALY`, severidade 7, `outcome=success`. Dois
caminhos, duas respostas, e um exercicio em que o time azul acharia a
contradicao no meio da sala.

"Um contrato so" nao e uma disciplina de escrita: e **um produtor so**. Este
modulo nao mapeia nada. Ele chama `forwarder.programar` — o mesmo que produz o
evento — e renderiza o payload resultante com `telemetry.cef.linha`. O que este
arquivo diz e o que o event store carrega, porque e o mesmo dicionario.

O QUE ESTE MODULO NAO E
=======================
Nao e o telemetry-forwarder. O item 4 da DoD tem duas metades, e esta e a do
ARQUIVO; a outra e `telemetry_emitted` indo para o event store, que e evento de
catalogo (`09` §4.1, `effect_class: machine`, `metric_side: none`). As duas
compartilham `programar`, e e exatamente isso que *"um contrato so"* significa.

VENDOR, PRODUCT E O CATALOGO CHEGAM POR PARAMETRO
==================================================
`05` §5.1 e categorico: vendor/product identificam produto **ficticio**, nunca
nome de fornecedor real de mercado, *"em nenhum campo, nem em documentacao de
exemplo"*. Os valores vivem em `contracts/evidence.schema.yaml`
(`x-aurora-security-constraints`), e o catalogo vive em
`domains/academus/telemetry_events.yaml`. Escrever qualquer um deles aqui seria
a P1-13 outra vez: duas fontes para a mesma norma, divergindo em silencio.

E E POR ISSO QUE O PACOTE EXPOE UMA FABRICA, e nao uma tabela pronta: este
gerador precisa de dois insumos carregados, e carrega-los no import seria efeito
colateral de importacao (R9 §1).

O FATO SEM ASSINATURA E RECUSA, E NAO LINHA A MENOS
====================================================
`programar` ignora, com razao, o fato cujo `fact_class` o catalogo nao mapeia —
`08` §2 poe o limite de deteccao no gabarito. Mas aqui o fato chegou porque o
GABARITO declarou `projections: [..., cef]`: ele mandou projetar em CEF um fato
que nao vira sinal. Cair fora em silencio faria o `MANIFEST.json` declarar o
`fact_id` em `projects_facts` de uma linha que nao existe — e a cobertura de
`08` §7 passaria a afirmar o que o arquivo nao tem. A contradicao e de autoria
de cenario, e a recusa nomeada e o que a mostra na hora do `evidence build`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from range_core.telemetry.cef import linha
from range_core.telemetry.catalogo import Catalogo
from range_core.telemetry.forwarder import programar

__all__ = ["fabricar", "FatoSemAssinatura", "ORIGEM"]

#: O host que assina a linha no prefixo syslog. Produto FICTICIO, `05` §5.1 —
#: e o coletor do SIEM simulado, nao um fornecedor de mercado.
ORIGEM = "aurora-siem-01"


class FatoSemAssinatura(Exception):
    """O gabarito manda projetar em CEF um fato que o catalogo nao mapeia."""


def fabricar(vendor: str, produto: str, *, catalogo: Catalogo) -> Callable:
    """Devolve o gerador de CEF com o vendor/product do CONTRATO e o catalogo.

    Fabrica, e nao modulo com constante: ver o cabecalho.
    """

    def gerar(fatos: Sequence[Mapping]) -> str:
        # UMA chamada, e a ordem do documento e preservada dos dois lados —
        # `programar` itera os fatos na ordem em que os recebe, e e a mesma
        # ordem do incidente que o motor de projecao ja fixou.
        programados = {p.fact_id: p for p in programar(fatos, catalogo=catalogo)}

        linhas = []
        for fato in fatos:
            fact_id = str(fato.get("fact_id", ""))
            programado = programados.get(fact_id)
            if programado is None:
                raise FatoSemAssinatura(
                    f"o gabarito projeta {fact_id!r} em `cef`, e o catalogo de "
                    f"`02` §10 nao tem assinatura para `fact_class` "
                    f"{fato.get('fact_class')!r}. Ou o fato nao devia declarar "
                    f"a projecao, ou o catalogo do adapter esta incompleto — "
                    f"linha a menos faria o MANIFEST declarar cobertura que o "
                    f"arquivo nao tem"
                )
            linhas.append(
                linha(
                    programado.payload,
                    vendor=vendor,
                    produto=produto,
                    nome=str(fato.get("action", "-")),
                    origem=ORIGEM,
                )
            )
        return "\n".join(linhas)

    return gerar
