"""Prova negativa da telemetria: a unificacao e o replay, com defeito plantado.

R3 §5. As duas afirmacoes desta peca falham de jeitos opostos, e cada um tem o
seu modo de passar despercebido:

    **o item 4** falha por DIVERGENCIA — o evento e o arquivo deixam de dizer a
    mesma coisa, e os dois continuam validos. Ninguem ve ate o time azul achar
    a contradicao;
    **o item 6** falha por EXCESSO — o replay emite antes da hora, ou emite duas
    vezes. O event store aceita tudo, porque e append-only.

AS CINCO MUTACOES
==================
| mutacao | o que ela e | propriedade atacada |
|---|---|---|
| **o `src` sai do payload** | some `source_ip` do mapa CEF | item 4, unificacao |
| **a severidade vem do fato** | deixa de vir do catalogo | `08` §2, nao julgar |
| **o vencimento e ignorado** | `em_segundos > decorrido` some | item 6, (1) |
| **o replay reemite** | o conjunto do ja emitido some | item 6, (3) |
| **o payload nao e conferido** | `erros_de_payload` devolve `[]` | `05` §6, o enum |

A TERCEIRA COBRE A PAUSA SEM MUTAR A PAUSA
===========================================
Nao ha mutacao "o replay ignora a pausa", e isso e desenho e nao omissao: o
forwarder **nao sabe pausar**. Ele le `elapsed_seconds()`, e quem congela e o
clock (`01` §3). A propriedade (2) do item 6 — *"durante a pausa nada novo
vence"* — e CONSEQUENCIA da (1), e e por isso que mutar o vencimento derruba
tambem o caso da pausa.

Isso e informacao sobre o desenho: um forwarder que soubesse pausar teria duas
autoridades sobre o mesmo relogio, e ai a pausa precisaria de mutacao propria.

A QUINTA E A QUE TORNA O ENUM VERIFICADO, E NAO SO REFERENCIADO
================================================================
`erros_de_payload` resolve o `$ref` do enum pelo `$id` do documento. Passando o
sub-schema solto, `jsonschema` levanta `PointerToNowhere` — e um chamador que
silenciasse esse erro devolveria lista vazia para TUDO. A mutacao troca o
retorno por `[]`, que e exatamente como esse defeito se pareceria.

A PROVA ACHOU DOIS TESTES QUE NAO MORDIAM, e e o melhor que ela fez nesta peca:

1. **o caso da unificacao se auto-desligava.** Ele fazia
   `if valor: assertIn(...)`, entao remover `src` do mapa CEF nao derrubava
   nada — a chave sumia e a asserção era pulada. Reescrito para exigir que o
   campo ESTEJA no payload quando o fato o tem;
2. **nao havia caso para "a severidade vem do catalogo".**
   `records_affected % 11` da valores que VALIDAM contra o contrato, entao o
   caso de schema continuava verde. Nasceu
   `test_a_severidade_vem_do_CATALOGO_e_nao_do_fato`.

Nos dois, o gate estava frouxo e o verde nao dizia nada — e nenhuma leitura do
codigo teria mostrado.

OS CONJUNTOS SAO MEDIDOS, NAO PREVISTOS.
"""

from __future__ import annotations

from pathlib import Path

from mutation_harness import caso_de_prova_negativa

REPO_ROOT = Path(__file__).resolve().parent.parent
FORWARDER = REPO_ROOT / "range-core" / "telemetry" / "forwarder.py"
CATALOGO = REPO_ROOT / "range-core" / "telemetry" / "catalogo.py"
TESTES = REPO_ROOT / "tests" / "test_telemetry_forwarder.py"

MUTAVEIS = (
    ("catalogo", "range_core.telemetry.catalogo", CATALOGO),
    ("forwarder", "range_core.telemetry.forwarder", FORWARDER),
)

MAPA_CEF = '    ("source_ip", "src"),'

SEVERIDADE = '            "severity": entrada.severity,'

VENCIMENTO = "            if indice in self._emitidos or programado.em_segundos > decorrido:"

MARCA_EMITIDO = "            self._emitidos.add(indice)"

RETORNO_DOS_ERROS = '    return [f"{e.json_path}: {e.message}" for e in erros]'

MUTACOES = {
    "o `src` sai do payload de telemetria": (
        [("forwarder", MAPA_CEF, "")],
        {"test_os_VALORES_do_payload_aparecem_na_linha_CEF_do_mesmo_fato"},
    ),
    # A QUE PASSOU DESPERCEBIDA NA PRIMEIRA MEDICAO. `records_affected % 11` da
    # valores 0-10, que VALIDAM contra o contrato — entao o caso de schema
    # continuava verde. Nao havia caso nenhum afirmando que a severidade vem do
    # CATALOGO, e a prova negativa foi quem mostrou.
    "a severidade passa a vir do fato, e nao do catalogo": (
        [
            (
                "forwarder",
                SEVERIDADE,
                '            "severity": int(fato.get("records_affected", 1)) % 11,',
            )
        ],
        {"test_a_severidade_vem_do_CATALOGO_e_nao_do_fato"},
    ),
    "o vencimento e ignorado — tudo sai no primeiro tick": (
        [("forwarder", VENCIMENTO, "            if indice in self._emitidos:")],
        {
            "test_no_T0_so_o_pre_posicionado_vence",
            "test_o_tempo_de_EXERCICIO_e_que_faz_vencer",
            "test_DURANTE_A_PAUSA_nada_novo_vence",
            "test_depois_de_RETOMAR_o_que_venceu_sai",
            "test_NAO_REEMITE_o_que_ja_saiu",
        },
    ),
    # `test_DURANTE_A_PAUSA` acusa, e eu nao previa: com reemissao, o tick
    # durante a pausa reemite o que ja saiu e devolve 1 em vez de 0. O caso
    # afirma "nada NOVO vence", e reemitir viola isso pelo outro lado — a
    # deteccao e legitima, e mostra que aquele caso e mais forte do que o nome
    # sugere.
    "o replay reemite a cada tick": (
        [("forwarder", MARCA_EMITIDO, "            pass")],
        {
            "test_NAO_REEMITE_o_que_ja_saiu",
            "test_o_tick_devolve_QUANTOS_sairam",
            "test_o_tempo_de_EXERCICIO_e_que_faz_vencer",
            "test_depois_de_RETOMAR_o_que_venceu_sai",
            "test_DURANTE_A_PAUSA_nada_novo_vence",
        },
    ),
    "o payload nunca e conferido contra o contrato": (
        [("forwarder", RETORNO_DOS_ERROS, "    return []")],
        {
            "test_payload_INVALIDO_e_recusado_pelo_contrato",
            "test_o_ENUM_das_doze_e_de_fato_exercitado",
        },
    ),
}

ProvaNegativa = caso_de_prova_negativa(MUTAVEIS, TESTES, MUTACOES)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
