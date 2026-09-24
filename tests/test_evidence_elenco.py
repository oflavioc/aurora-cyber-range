"""Item 1 da DoD da Fase 9 — o elenco e a cobertura, dirigidos por FATO.

O QUE ESTA SUITE JULGA
======================
`07` §Fase 9, item 1: *"toda fonte e projecao de `fact_id`; nenhum gerador
inventa entidade"*. `08` §2 diz as duas metades com todas as letras:

    Projecao NAO INVENTA ENTIDADE. Consome o elenco fixado pelo ground truth.
    Fato SEM `projections` e invisivel ao time azul — deliberado, e usado para
    ensinar limite de deteccao.

`06` T13 exige que o teste seja **dirigido por fato, nao por seed**, e e por isso
que quase todo caso aqui monta o proprio ground truth: o julgamento e sobre a
relacao fato -> projecao, e um teste que dependesse do seed julgaria o gerador.

AS TRES PERGUNTAS, E POR QUE ELAS SAO PURAS
============================================
    elenco_de      quais entidades as projecoes PODEM usar
    cobertura_de   fonte -> os `fact_id` que ela projeta
    enderecos_no   quais enderecos um texto de fato CONTEM

As duas primeiras sao funcao do ground truth e de mais nada — nem do seed, nem
do dominio, nem dos arquivos em disco. A terceira e funcao do texto. Nenhuma
executa gerador, e e isso que as torna ORACULO INDEPENDENTE (R10): um gerador
que inventasse entidade consistentemente passaria por qualquer comparacao
gerador-contra-gerador, e nao passa por estas.

A REDE DO `enderecos_no` E SOLIDA, E AS OUTRAS NAO SERIAM
==========================================================
Endereco IP tem forma fechada e reconhecivel sem ambiguidade: toda ocorrencia
num arquivo de evidencia ou esta no elenco, ou foi inventada. Ator e host nao
tem forma assim — `svc_academus` e `vpn-gw-01` sao reconheciveis, mas uma rede
lexica que os pegasse pegaria tambem palavra comum de prosa, e a mesma
sobre-inclusao que `citacoes.py` aceita de proposito para `fact_id` aqui
produziria ruido sobre o CORPO do log, que e texto livre.

**Entao a cobertura e assimetrica, e o limite fica declarado:** para endereco, a
suite afirma AUSENCIA de invencao; para ator e destino, ela afirma PRESENCA do
que o fato declara — que e a consistencia mutua que `06` T13 cobra (*"apresentam
usuario, IP e timestamp mutuamente consistentes"*). O que nenhuma das duas
alcanca e um ator inventado que nao colida com nada; esse fica para a
reprojecao determinista do `evidence verify` (item 2).

`fact_id` NAO VAZA PARA O ARQUIVO, e e por isso que a amarracao e o elenco
==========================================================================
A forma obvia de provar "este registro veio deste fato" seria carimbar o
`fact_id` no registro. Ela esta PROIBIDA pelo que o sistema e: o arquivo de
evidencia vai para o time azul, e `GT-A-014` num `vpn.log` entrega o gabarito na
primeira linha — `05` §6 e o proprio `check_gabarito_fora_do_git`. A amarracao
tem de ser por CONTEUDO, e o elenco e ela.
"""

from __future__ import annotations

import importlib
import unittest

#: RESOLVIDO POR `sys.modules`, E ISSO NAO E ESTILO — e o que faz a prova
#: negativa funcionar na suite COMPLETA.
#:
#: `from range_core.evidence import elenco as mod` liga `mod` ao ATRIBUTO do
#: pacote, e o harness de mutacao substitui a entrada em `sys.modules`, nunca o
#: atributo. Medido: isolada, esta suite matava os quatro mutantes; junto da
#: arvore inteira, os quatro "sobreviviam" — porque `test_evidence_elenco` ja
#: tinha sido importado, o atributo do pacote ja apontava para o original, e a
#: suite recarregada pelo harness o repegava de la.
#:
#: Falha de INSTRUMENTO lida como ausencia de deteccao, que e o espelho do que o
#: cabecalho de `test_queda_de_sessao_probes.py` descreve. `import_module`
#: consulta `sys.modules` primeiro, entao a suite recarregada ve o modulo mutado.
mod = importlib.import_module("range_core.evidence.elenco")

# ---------------------------------------------------------------------------
# Ground truths de fixture. Dirigidos por fato: cada um existe para um caso, e
# nenhum depende de seed. Os valores sao de faixa de documentacao (`05` §3).
# ---------------------------------------------------------------------------

#: Dois fatos, tres fontes, um ator comum e dois enderecos.
GT_BASE = {
    "facts": [
        {
            "fact_id": "GT-A-014",
            "fact_class": "initial_access",
            "exercise_time": "T-17d 02:14",
            "actor": "svc_academus",
            "action": "vpn_login",
            "source_ip": "198.51.100.42",
            "dest": "vpn-gw-01",
            "projections": ["vpn", "identity_audit", "cef"],
        },
        {
            "fact_id": "GT-A-031",
            "fact_class": "exfiltration",
            "exercise_time": "T-15d 04:47",
            "actor": "svc_academus",
            "action": "bulk_export",
            "source_ip": "192.0.2.7",
            "records_affected": 2300,
            "projections": ["database_audit", "cef"],
        },
    ]
}

#: O fato invisivel: existe no ground truth e NAO projeta em lugar nenhum.
GT_COM_FATO_INVISIVEL = {
    "facts": [
        GT_BASE["facts"][0],
        {
            "fact_id": "GT-A-099",
            "fact_class": "lateral_discovery",
            "exercise_time": "T-16d 03:00",
            "actor": "conta_fantasma",
            "source_ip": "203.0.113.9",
            "dest": "host-sem-log",
            # sem `projections` — o limite de deteccao de `08` §2
        },
    ]
}


class OElenco(unittest.TestCase):
    """Quais entidades as projecoes podem usar."""

    def test_reune_ator_destino_e_endereco_de_todos_os_fatos(self):
        e = mod.elenco_de(GT_BASE)
        self.assertEqual(e.atores, frozenset({"svc_academus"}))
        self.assertEqual(e.destinos, frozenset({"vpn-gw-01"}))
        self.assertEqual(e.enderecos, frozenset({"198.51.100.42", "192.0.2.7"}))

    def test_o_elenco_NAO_carrega_escalar_nem_rotulo(self):
        """`records_affected`, `exercise_time`, `action` e `fact_class` NAO sao
        entidade. Se entrassem, o oraculo passaria a aceitar qualquer numero ou
        verbo que o gerador escrevesse — e o item 1 deixaria de morder."""
        todos = mod.elenco_de(GT_BASE).todos
        for nao_entidade in ("2300", "T-17d 02:14", "vpn_login", "initial_access"):
            self.assertNotIn(nao_entidade, todos, nao_entidade)

    def test_fato_invisivel_ENTRA_no_elenco(self):
        """O fato sem `projections` nao projeta — mas as entidades dele sao do
        mundo, e outro fato pode legitimamente cita-las. Exclui-lo do elenco
        faria o oraculo recusar projecao correta."""
        e = mod.elenco_de(GT_COM_FATO_INVISIVEL)
        self.assertIn("conta_fantasma", e.atores)
        self.assertIn("203.0.113.9", e.enderecos)

    def test_ground_truth_sem_fato_da_elenco_vazio(self):
        e = mod.elenco_de({"facts": []})
        self.assertEqual(e.todos, frozenset())

    def test_fato_sem_campo_de_entidade_nao_quebra(self):
        """`04` §3 exige so `fact_id`, `fact_class` e `exercise_time`."""
        e = mod.elenco_de(
            {"facts": [{"fact_id": "GT-A-001", "fact_class": "x", "exercise_time": "T+0"}]}
        )
        self.assertEqual(e.todos, frozenset())


class ACobertura(unittest.TestCase):
    """Fonte -> os `fact_id` que ela projeta."""

    def test_cada_fonte_recebe_exatamente_os_fatos_que_a_declaram(self):
        self.assertEqual(
            mod.cobertura_de(GT_BASE),
            {
                "vpn": frozenset({"GT-A-014"}),
                "identity_audit": frozenset({"GT-A-014"}),
                "cef": frozenset({"GT-A-014", "GT-A-031"}),
                "database_audit": frozenset({"GT-A-031"}),
            },
        )

    def test_fato_SEM_projections_nao_aparece_em_fonte_nenhuma(self):
        """`06` T13, criterio proprio: *"fato sem `projections` nao aparece em
        nenhuma fonte"*. E o limite de deteccao deliberado de `08` §2."""
        cobertura = mod.cobertura_de(GT_COM_FATO_INVISIVEL)
        for fonte, fatos in cobertura.items():
            self.assertNotIn("GT-A-099", fatos, fonte)

    def test_projections_VAZIA_e_tratada_como_ausente(self):
        """Lista vazia e ausencia dizem a mesma coisa — o fato nao projeta. O
        contrato torna o campo opcional justamente para nao exigir a forma
        vazia, mas quem escreve o ground truth pode usa-la."""
        gt = {
            "facts": [
                {
                    "fact_id": "GT-A-002",
                    "fact_class": "x",
                    "exercise_time": "T+0",
                    "projections": [],
                }
            ]
        }
        self.assertEqual(mod.cobertura_de(gt), {})

    def test_a_cobertura_nao_inventa_fonte(self):
        """So aparecem fontes que algum fato declarou — nunca o enum inteiro do
        contrato com conjuntos vazios. Fonte com zero fatos e arquivo que o
        `evidence build` nao tem por que escrever."""
        self.assertNotIn("email", mod.cobertura_de(GT_BASE))

    def test_e_funcao_do_ground_truth_e_de_mais_nada(self):
        """Dirigido por fato, nao por seed (`06` T13): duas chamadas sobre o
        mesmo ground truth devolvem o mesmo resultado, e nenhuma delas recebe
        seed."""
        self.assertEqual(mod.cobertura_de(GT_BASE), mod.cobertura_de(GT_BASE))
        self.assertEqual(mod.elenco_de(GT_BASE).todos, mod.elenco_de(GT_BASE).todos)


class OsEnderecosNoTexto(unittest.TestCase):
    """A rede solida do 'nao inventa entidade'."""

    def test_acha_ipv4_em_linha_de_syslog(self):
        linha = "Aug 13 02:14:07 vpn-gw-01 vpnd: user=svc_academus src=198.51.100.42 mfa=none"
        self.assertEqual(mod.enderecos_no(linha), {"198.51.100.42"})

    def test_acha_ipv6_de_documentacao(self):
        self.assertEqual(mod.enderecos_no("src=2001:db8::1 ok"), {"2001:db8::1"})

    def test_acha_varios_e_deduplica(self):
        texto = "a=192.0.2.7 b=198.51.100.42 c=192.0.2.7"
        self.assertEqual(mod.enderecos_no(texto), {"192.0.2.7", "198.51.100.42"})

    def test_NAO_confunde_versao_nem_sequencia_de_numeros_com_endereco(self):
        """Adversarial: os defeitos classicos da regex ingenua de IP.

        Cada isca e um vizinho proximo que aparece de verdade em arquivo de log,
        e por isso esta aqui e nao num comentario:

            versao 1.2.3        tres componentes, nao quatro
            999.1.1.1           casa a FORMA e nao e endereco — quem decide e
                                `ipaddress`, e nao a regex
            1.2.3.4.5           sem a fronteira da direita, doaria `1.2.3.4`
            2026.09.18          data com ponto
            00:1A:2B:3C:4D:5E   MAC — seis grupos hex, que e o vizinho do IPv6
            2026-09-18T02:14:07 timestamp ISO, com `:` colado em `\\w`
            Aug 13 02:14:07     timestamp de syslog, com `:` apos espaco — o
                                caso que a fronteira do IPv6 tem de segurar
        """
        for isca in (
            "versao 1.2.3 do agente",
            "999.1.1.1",
            "1.2.3.4.5",
            "2026.09.18",
            "mac 00:1A:2B:3C:4D:5E",
            "ts 2026-09-18T02:14:07Z",
            "Aug 13 02:14:07 vpn-gw-01",
        ):
            self.assertEqual(mod.enderecos_no(isca), set(), isca)

    def test_texto_sem_endereco_devolve_conjunto_vazio(self):
        self.assertEqual(mod.enderecos_no("nenhum endereco aqui"), set())


class AConjuncaoQueDecideOItem1(unittest.TestCase):
    """O uso real: texto projetado x elenco do ground truth."""

    def test_endereco_de_FORA_do_elenco_e_detectado(self):
        """Um gerador que inventa endereco e pego pela diferenca. E esta a
        afirmacao de AUSENCIA que o item 1 cobra."""
        e = mod.elenco_de(GT_BASE)
        linha = "src=198.51.100.42 relay=203.0.113.200"
        self.assertEqual(mod.enderecos_no(linha) - e.enderecos, {"203.0.113.200"})

    def test_projecao_fiel_nao_deixa_residuo(self):
        e = mod.elenco_de(GT_BASE)
        linha = "src=198.51.100.42 dst=192.0.2.7"
        self.assertEqual(mod.enderecos_no(linha) - e.enderecos, set())

    def test_o_elenco_responde_por_ator_e_destino_pela_PRESENCA(self):
        """A outra metade, e ela e assimetrica de proposito — ver o cabecalho.
        O que se afirma de ator e destino e que o valor do fato APARECE na
        projecao, que e a consistencia mutua de `06` T13."""
        e = mod.elenco_de(GT_BASE)
        self.assertTrue(e.contem("svc_academus"))
        self.assertTrue(e.contem("vpn-gw-01"))
        self.assertFalse(e.contem("prof.inexistente"))

    # -- hostname: a segunda forma fechada, M2 da segunda auditoria ----------

    def test_host_DERIVADO_do_elenco_nao_e_invencao(self):
        """`svc_academus` vira `svc-academus` porque `_` nao e valido em rotulo
        de host (RFC 1123). A normalizacao e de sintaxe, nao de identidade."""
        e = mod.elenco_de(GT_BASE)
        texto = "Acesse: https://svc-academus.example/x"
        self.assertEqual(mod.hosts_inventados(texto, e), [])

    def test_host_com_rotulo_QUE_NINGUEM_FIXOU_e_invencao(self):
        """O sufixo e reservado — `05` §2 esta satisfeito e o predicado de IOC
        aprova. Quem recusa e o elenco, e so ele."""
        e = mod.elenco_de(GT_BASE)
        texto = "Acesse: https://intranet-ti.example/x"
        self.assertEqual(mod.hosts_inventados(texto, e), ["intranet-ti.example"])

    def test_o_SUFIXO_reservado_nao_precisa_estar_no_elenco(self):
        """Exigi-lo obrigaria todo gabarito a declarar `.example` como se fosse
        um ator — norma de seguranca virando entidade do mundo simulado."""
        e = mod.elenco_de(GT_BASE)
        self.assertNotIn("example", e.rotulos_de_host)
        self.assertEqual(mod.hosts_inventados("svc-academus.example", e), [])

    def test_host_FORA_de_faixa_reservada_NAO_e_reportado_aqui(self):
        """A omissao e deliberada: dominio roteavel e IOC, e quem o nomeia e
        `dados_sinteticos` na guarda seguinte. Reportar "entidade inventada"
        mandaria o autor do gerador procurar no elenco o que e `05` §3."""
        e = mod.elenco_de(GT_BASE)
        self.assertEqual(mod.hosts_inventados("https://exemplo-real.com.br/x", e), [])

    def test_nome_de_arquivo_nao_vira_hostname(self):
        """`vpn.log` e `identity_audit.jsonl` aparecem em prosa de manifesto e
        de comentario. Quem decide o que tem forma de host e `dados_sinteticos`,
        e ele exclui sufixo de arquivo — reusar o julgamento e o que impede a
        segunda resposta para a mesma pergunta."""
        self.assertEqual(mod.hostnames_no("vpn.log identity_audit.jsonl"), set())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
