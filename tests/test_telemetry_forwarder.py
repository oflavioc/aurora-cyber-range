"""Telemetria como PROJECAO, e o replay no clock — itens 4 e 6 da DoD.

O QUE ESTA SUITE JULGA
======================
`07` §Fase 9, item 4: *"telemetria CEF e projecao, nao emissao independente"*.
Item 6: *"replay respeita o clock de exercicio"*.

`08` §2 diz o porque do primeiro com todas as letras: *"a telemetria CEF e
projecao, nao emissao independente. Isso unifica evidence-simulator e
telemetry-forwarder sob **um contrato so**."* Telemetria gerada por um caminho
proprio divergiria do `vpn.log` e do `identity_audit.jsonl` na primeira mudanca
de codigo — e a divergencia so apareceria quando o time azul achasse a
contradicao, no meio do exercicio.

**A prova de que sao um contrato so nao e de estrutura, e de VALOR**: o mesmo
fato tem de produzir os mesmos valores no arquivo `cef.log` e no payload do
`telemetry_emitted`. Duas implementacoes coerentes hoje nao provam nada sobre
amanha; valores iguais medidos lado a lado, sim.

O REPLAY, E O QUE "RESPEITAR O CLOCK" SIGNIFICA
================================================
Tres propriedades, e cada uma tem caso proprio:

1. **so emite o que ja venceu** em tempo de EXERCICIO, nunca de parede;
2. **durante a pausa, nada novo vence** — `01` §3: o exercise-clock congela, e
   `elapsed_seconds()` para;
3. **nao reemite** — um tick que repetisse o ja emitido encheria o event store
   de duplicatas que a reconstrucao contaria como sinal.

A (2) e a que distingue este item de um agendador qualquer. Um forwarder preso
ao relogio de parede continuaria despejando telemetria numa sala parada — e o
`exercise_paused` existe justamente para que nada avance.

O LIMITE DO AGENDAMENTO, DECLARADO
===================================
Os fatos da Linha A sao do PASSADO do incidente (`T-17d 02:14`), e nao ha como
converter esse rotulo em segundos de exercicio: e a gramatica temporal que **nao
existe** (P6-3). Eles sao telemetria **pre-posicionada** — `08` §5 —, ja no SIEM
quando o exercicio comeca, e por isso vencem em `0`.

Agendamento derivado do `exercise_time` do fato fica para quando a P6-3 nascer.
O forwarder ja aceita o instante por parametro, entao o que falta e a conversao,
nao o mecanismo.
"""

from __future__ import annotations

import importlib
import unittest

from range_core.engine.loader import contract_source

catalogo_mod = importlib.import_module("range_core.telemetry.catalogo")
forwarder = importlib.import_module("range_core.telemetry.forwarder")
cef_mod = importlib.import_module("domains.academus.evidence_generators.cef")
linha_a = importlib.import_module("domains.academus.seed.linha_a")

#: O ATALHO E DO ADAPTER, e nao do nucleo. A primeira versao desta suite pedia
#: `catalogo.do_academus(...)`, e o modulo do nucleo que o servia foi
#: **bloqueado na escrita** pelo hook `check_architecture`: invariante 1,
#: `range-core/` nao importa de `domains/`. O atalho nao mudou de forma, mudou
#: de lado — e a fronteira foi defendida por mecanismo, nao por lembranca.
telemetria_do_academus = importlib.import_module("domains.academus.telemetria")

CONTRATOS = contract_source.read_contracts()
SEED = 424242


class ORelogioFalso:
    """Um `ExerciseClock` mínimo, controlado pelo teste.

    Dublê, e não o clock real, porque o que se julga aqui é o FORWARDER: com o
    relógio real, um caso de pausa dependeria de `time.monotonic` e viraria
    teste de tempo, que é a classe mais frágil que existe.
    """

    def __init__(self):
        self._decorrido = 0.0
        self._pausado = False

    def elapsed_seconds(self) -> float:
        return self._decorrido

    def is_paused(self) -> bool:
        return self._pausado

    def avanca(self, segundos: float) -> None:
        """So avanca se nao estiver pausado — e o contrato do exercise-clock."""
        if not self._pausado:
            self._decorrido += segundos

    def pausa(self) -> None:
        self._pausado = True

    def retoma(self) -> None:
        self._pausado = False


class OCatalogoDoDominio(unittest.TestCase):
    """`02` §10 — `domains/academus/telemetry_events.yaml`."""

    def setUp(self):
        self.catalogo = telemetria_do_academus.catalogo(CONTRATOS)

    def test_declara_os_DOZE_eventos_de_02_secao_10(self):
        """A lista e fechada na spec, e o contrato a carrega como enum."""
        do_contrato = set(catalogo_mod.assinaturas_do_contrato(CONTRATOS))
        self.assertEqual(len(do_contrato), 12)
        self.assertEqual(set(self.catalogo.assinaturas()), do_contrato)

    def test_toda_assinatura_declarada_esta_no_ENUM_do_contrato(self):
        """Assinatura fora do catalogo e `event_type` com erro de digitacao com
        outro nome: nunca dispara, e ninguem percebe ate o exercicio."""
        do_contrato = set(catalogo_mod.assinaturas_do_contrato(CONTRATOS))
        for assinatura in self.catalogo.assinaturas():
            self.assertIn(assinatura, do_contrato, assinatura)

    def test_resolve_fact_class_para_assinatura(self):
        self.assertEqual(
            self.catalogo.assinatura_de("grade_change_retroactive"),
            "GRADE_CHANGE_RETROACTIVE",
        )

    def test_fact_class_sem_assinatura_devolve_None_e_nao_levanta(self):
        """Fato que nao gera telemetria e caso NORMAL, nao erro: `08` §2 poe o
        limite de deteccao no gabarito, e nem todo fato chega ao SIEM."""
        self.assertIsNone(self.catalogo.assinatura_de("fact_class_inexistente"))


class ATelemetriaEProjecaoDoMesmoFato(unittest.TestCase):
    """Item 4 — a prova e de VALOR, não de estrutura."""

    def setUp(self):
        #: OS FATOS QUE O GABARITO ROTEIA PARA `cef`, e nao todos — e a mesma
        #: filtragem que `projetar` faz pela cobertura. Passar todos aqui
        #: mediria uma composicao que nao existe: `phishing_delivery` projeta em
        #: `email` e `precursor`, nunca em `cef`.
        self.fatos = [
            f for f in linha_a.facts(SEED) if "cef" in (f.get("projections") or ())
        ]
        self.catalogo = telemetria_do_academus.catalogo(CONTRATOS)
        self.programados = forwarder.programar(self.fatos, catalogo=self.catalogo)
        restricoes = contract_source.restricoes_de_evidencia(CONTRATOS)
        self.cef = cef_mod.fabricar(
            restricoes["cef_vendor"],
            restricoes["cef_product"],
            catalogo=self.catalogo,
        )(self.fatos)

    def test_cada_evento_programado_vem_de_UM_fato(self):
        classes = {f["fact_class"] for f in self.fatos}
        for programado in self.programados:
            self.assertIn(programado.fact_class, classes)

    def test_o_payload_carrega_os_campos_do_FATO(self):
        """**A metade que a unificacao NAO pode provar, e por construcao.**

        Desde que o arquivo e o evento saem do mesmo `programar`, comparar um
        com o outro deixa de guardar CONTEUDO: um campo que suma do payload
        some dos dois, e a igualdade continua verdadeira. Medido — a mutacao
        *"o `src` sai do payload"* deixou de derrubar qualquer teste no momento
        em que as duas metades se unificaram.

        Entao a segunda afirmacao tem de ser contra o FATO, e o mapa esta
        escrito aqui a mao: `02` §10 nomeia `src`, `dst`, `suser` e `cnt`, e ler
        `forwarder.CAMPO_PARA_CEF` faria o teste concordar com a implementacao
        por construcao — mutar o mapa mudaria os dois lados.
        """
        por_fato = {f["fact_id"]: f for f in self.fatos}
        vistos = 0
        for programado in self.programados:
            fato = por_fato[programado.fact_id]
            for campo, chave in (
                ("source_ip", "src"),
                ("dest", "dst"),
                ("actor", "suser"),
                ("records_affected", "cnt"),
            ):
                if campo not in fato:
                    continue
                self.assertIn(
                    chave, programado.payload, f"{chave} ausente do payload"
                )
                self.assertEqual(programado.payload[chave], fato[campo])
                vistos += 1
        # ANTI-VACUIDADE: sem isto, um `programar` que devolvesse payloads
        # vazios passaria — nao haveria campo para conferir.
        self.assertGreaterEqual(vistos, len(self.programados))

    def test_a_linha_CEF_e_o_payload_sao_o_MESMO_dicionario(self):
        """**H1 da segunda auditoria — a unificacao, medida por INTEIRO.**

        As duas versoes anteriores deste caso comparavam `src` e `suser`, e
        localizavam a linha CEF pela `fact_class`. Ou seja: **dependiam da
        divergencia para funcionar**, porque so o gerador antigo punha a classe
        do fato no campo de assinatura. Um par que compara dois campos de sete e
        acha a linha pelo que difere nao prova unificacao nenhuma.

        O que este caso afirma agora e igualdade TOTAL, nos dois sentidos: todo
        campo do payload aparece na linha com o mesmo valor, e a linha nao tem
        extensao nenhuma que o payload nao tenha. Campo novo no contrato de
        telemetria entra nas duas pontas ou o teste cai.
        """
        linhas = [l for l in self.cef.splitlines() if "|" in l]
        self.assertEqual(len(linhas), len(self.programados))

        for programado, linha in zip(self.programados, linhas, strict=True):
            cabecalho, _, extensoes = linha.rpartition("|")
            partes = cabecalho.split("|")
            payload = dict(programado.payload)

            # As DUAS chaves que o cabecalho consome, no lugar que o formato
            # fixa: `signature` e o Device Event Class ID (campo 5) e
            # `severity` e o campo 7.
            self.assertEqual(partes[4], payload.pop("signature"))
            self.assertEqual(partes[6], str(payload.pop("severity")))

            # E TODO O RESTO, nos dois sentidos.
            na_linha = dict(
                par.split("=", 1) for par in extensoes.split() if "=" in par
            )
            self.assertEqual(
                na_linha,
                {chave: str(valor) for chave, valor in payload.items()},
                f"{programado.fact_id}: a linha e o payload divergem",
            )

    def test_a_assinatura_da_linha_CEF_vem_do_CATALOGO(self):
        """B1/H1 no mesmo ponto: `initial_access` como `signature` era a
        classificacao do gabarito na kill chain viajando como sinal de SIEM."""
        classes = {f["fact_class"] for f in self.fatos}
        assinaturas = {l.split("|")[4] for l in self.cef.splitlines() if "|" in l}
        self.assertEqual(assinaturas & classes, set())
        self.assertTrue(assinaturas <= set(self.catalogo.assinaturas()))

    def test_nenhuma_extensao_da_linha_usa_cs1_a_cs4(self):
        """`02` §10 reserva `cs1`-`cs4` para contexto do DOMINIO (campus, curso,
        semestre, disciplina). A versao anterior punha `credential_state` em
        `cs1` e `mfa` em `cs2` — campo reservado usado para o que coubesse, e
        ainda com o veredito do gabarito dentro (B1)."""
        for linha in self.cef.splitlines():
            for reservado in ("cs1=", "cs2=", "cs3=", "cs4="):
                self.assertNotIn(reservado, linha)

    def test_a_severidade_vem_do_CATALOGO_e_nao_do_fato(self):
        """`08` §2 — a telemetria nao julga.

        `severity` e atributo do TIPO de sinal: dois `GRADE_CHANGE_RETROACTIVE`
        tem a mesma severidade, aconteca o que acontecer no exercicio. Derivada
        do fato, ela viraria avaliacao embutida na evidencia — a confusao de
        camadas de `00` §3 que este projeto existe para evitar.

        Sem este caso, uma severidade derivada de `records_affected` passava:
        ela continua no intervalo do contrato, e o payload segue valido.
        """
        for programado in self.programados:
            entrada = self.catalogo.entrada_de(programado.fact_class)
            self.assertEqual(programado.payload["severity"], entrada.severity)

    def test_o_payload_carrega_a_assinatura_do_catalogo(self):
        for programado in self.programados:
            self.assertEqual(
                programado.payload["signature"],
                self.catalogo.assinatura_de(programado.fact_class),
            )

    def test_o_payload_VALIDA_contra_o_contrato_do_evento(self):
        for programado in self.programados:
            erros = forwarder.erros_de_payload(programado.payload, CONTRATOS)
            self.assertEqual(erros, [], erros)

    def test_payload_INVALIDO_e_recusado_pelo_contrato(self):
        """O par negativo, e sem ele o caso positivo nao afirma nada: um
        validador que nunca recusa tambem devolve lista vazia — a licao da
        peca 2.

        Quatro defeitos, cada um numa clausula diferente. **O terceiro e o que
        importa para `05` §6**: `fact_id` e INEXPRESSAVEL no payload, porque
        `additionalProperties: false` o recusa — o participante ve a telemetria,
        e o identificador de gabarito ali entregaria o gabarito.
        """
        casos = (
            ({"signature": "INVENTADA", "severity": 3}, "$.signature"),
            ({"signature": "AUTH_FAIL", "severity": 99}, "$.severity"),
            ({"signature": "AUTH_FAIL", "severity": 3, "fact_id": "GT-A-014"}, "fact_id"),
            ({"severity": 3}, "signature"),
        )
        for payload, esperado in casos:
            erros = forwarder.erros_de_payload(payload, CONTRATOS)
            self.assertTrue(erros, payload)
            self.assertIn(esperado, " ".join(erros), payload)

    def test_o_ENUM_das_doze_e_de_fato_exercitado(self):
        """O `$ref` para `$defs/telemetry_signature` e de OUTRO nivel do mesmo
        documento, e resolve-lo exige o alvo pelo `$id`.

        Medido: com o sub-schema passado solto, `jsonschema` levanta
        `PointerToNowhere` — e se o erro fosse silenciado, o enum deixaria de
        ser conferido e assinatura inventada passaria. Este caso existe para
        que o enum seja exercitado, e nao so referenciado.
        """
        erros = forwarder.erros_de_payload(
            {"signature": "NAO_EXISTE", "severity": 1}, CONTRATOS
        )
        self.assertTrue(any("AUTH_FAIL" in e for e in erros), erros)

    def test_fato_sem_assinatura_NAO_vira_telemetria(self):
        forjado = [{"fact_id": "GT-A-500", "fact_class": "nada", "exercise_time": "T+0"}]
        self.assertEqual(forwarder.programar(forjado, catalogo=self.catalogo), ())

    def test_a_programacao_e_DETERMINISTA(self):
        outra = forwarder.programar(self.fatos, catalogo=self.catalogo)
        self.assertEqual(self.programados, outra)


class OReplayRespeitaOClock(unittest.TestCase):
    """Item 6."""

    def setUp(self):
        self.clock = ORelogioFalso()
        self.emitidos: list[dict] = []
        self.programados = (
            forwarder.Programado("a", "A", 0, {"signature": "AUTH_FAIL", "severity": 3}),
            forwarder.Programado("b", "B", 30, {"signature": "AUTH_BRUTE", "severity": 5}),
            forwarder.Programado("c", "C", 90, {"signature": "HPC_JOB_ANOMALY", "severity": 4}),
        )
        self.replay = forwarder.Replay(
            self.programados, clock=self.clock, emissor=self.emitidos.append
        )

    def test_no_T0_so_o_pre_posicionado_vence(self):
        self.assertEqual(self.replay.tick(), 1)
        self.assertEqual(len(self.emitidos), 1)

    def test_o_tempo_de_EXERCICIO_e_que_faz_vencer(self):
        self.replay.tick()
        self.clock.avanca(30)
        self.assertEqual(self.replay.tick(), 1)
        self.clock.avanca(60)
        self.assertEqual(self.replay.tick(), 1)
        self.assertEqual(len(self.emitidos), 3)

    def test_DURANTE_A_PAUSA_nada_novo_vence(self):
        """`01` §3 — o exercise-clock congela no PAUSAR. Um forwarder preso ao
        relogio de parede continuaria despejando telemetria numa sala parada."""
        self.replay.tick()
        self.clock.pausa()
        self.clock.avanca(3600)  # uma hora de parede, zero de exercicio
        self.assertEqual(self.replay.tick(), 0)
        self.assertEqual(len(self.emitidos), 1)

    def test_depois_de_RETOMAR_o_que_venceu_sai(self):
        self.replay.tick()
        self.clock.pausa()
        self.clock.avanca(3600)
        self.replay.tick()
        self.clock.retoma()
        self.clock.avanca(30)
        self.assertEqual(self.replay.tick(), 1)

    def test_NAO_REEMITE_o_que_ja_saiu(self):
        """Duplicata no event store e sinal para a reconstrucao — ela nao sabe
        distinguir telemetria repetida de telemetria de verdade."""
        self.replay.tick()
        self.replay.tick()
        self.replay.tick()
        self.assertEqual(len(self.emitidos), 1)

    def test_o_tick_devolve_QUANTOS_sairam(self):
        self.clock.avanca(120)
        self.assertEqual(self.replay.tick(), 3)
        self.assertEqual(self.replay.tick(), 0)

    def test_a_ORDEM_de_emissao_e_a_do_vencimento(self):
        self.clock.avanca(120)
        self.replay.tick()
        self.assertEqual(
            [e["signature"] for e in self.emitidos],
            ["AUTH_FAIL", "AUTH_BRUTE", "HPC_JOB_ANOMALY"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
