"""O motor de projecao — itens 1 e 5 da DoD da Fase 9, e a P1-3.

O QUE ESTA SUITE JULGA
======================
`08_EVIDENCE_SIMULATOR.md` §1: cada fonte e **projecao deterministica de um fato
canonico**, e e isso que torna contradicao entre fontes *estruturalmente
impossivel* em vez de apenas improvavel. O motor e quem sustenta essa frase:

    projetar()  le a cobertura, chama UM gerador por fonte com APENAS os fatos
                daquela fonte, prefixa o banner, e RECUSA o gerador que inventa

A recusa e o que fecha o item 1. `elenco.py` (peca 1) sabe dizer quais enderecos
um texto contem e quais o ground truth autoriza; aqui essa diferenca deixa de ser
consulta e vira **porta**: gerador que escreve endereco fora do elenco nao produz
arquivo, produz excecao.

O MANIFESTO E VALIDADO CONTRA O CONTRATO REAL, E ISSO E A P1-3
===============================================================
`contracts/evidence.schema.yaml` existe desde a Fase 1 e nunca validou nada —
*"quem consome, hoje: o evidence-simulator da Fase 9, que ainda nao existe"*,
diz o proprio arquivo. Esta suite e o primeiro consumidor: o manifesto que
`montar()` produz e validado contra aquele schema, com os `$ref` resolvidos pelo
mesmo `Registry` que o loader usa.

E oraculo independente no sentido forte de R10 — quem julga a saida nao e outra
funcao deste modulo, e sim um contrato escrito oito fases antes, por outra razao.

OS GERADORES AQUI SAO DUBLES, E ISSO E DESENHO
===============================================
O motor e do CORE e nao conhece formato de fio; quem escreve `vpn.log` de
verdade e `domains/academus/evidence_generators/` (peca 3). Os dubles desta
suite existem para exercitar o CONTRATO do gerador — recebe fatos, devolve
corpo —, e dois deles existem para serem recusados: o que inventa endereco e o
que ignora os fatos que recebeu.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import unittest

from range_core.engine.loader import contract_source

#: Por `sys.modules`, e nao por `from pacote import submodulo` — a licao da
#: peca 1 (§2.4 do registro): o harness de mutacao substitui `sys.modules`, e o
#: atributo do pacote nao acompanha.
banner = importlib.import_module("range_core.evidence.banner")
projecao = importlib.import_module("range_core.evidence.projecao")
manifesto = importlib.import_module("range_core.evidence.manifesto")

CONTRATOS = contract_source.read_contracts()

#: A particao de `x-aurora-registry.fact_fields` — B1 da segunda auditoria.
CAMPOS = contract_source.campos_do_fato(CONTRATOS)

SEED = 424242
PACK = "ransomware-universidade"

#: Dois fatos, tres fontes. Os mesmos valores da fixture da peca 1: faixa de
#: documentacao (`05` §3), ator de servico, host fixo.
GT = {
    "facts": [
        {
            "fact_id": "GT-A-014",
            "fact_class": "initial_access",
            "exercise_time": "T-17d 02:14",
            "actor": "svc_academus",
            "action": "vpn_login",
            "source_ip": "198.51.100.42",
            "dest": "vpn-gw-01",
            # OS DOIS CAMPOS DE GABARITO, no fato que o caso positivo projeta —
            # B1 da segunda auditoria. Sem eles aqui, a guarda de veredito
            # passaria vacuamente: nao haveria o que ela pudesse encontrar, e
            # um motor que nunca a executasse ficaria verde.
            "credential_state": "compromised",
            "mfa": "absent",
            "discoverability": {
                "difficulty": "medium",
                "requires": "correlacionar horario fora de expediente com ausencia de MFA",
            },
            "projections": ["vpn", "identity_audit"],
        },
        {
            "fact_id": "GT-A-031",
            "fact_class": "exfiltration",
            "exercise_time": "T-15d 04:47",
            "actor": "svc_academus",
            "action": "bulk_export",
            "source_ip": "192.0.2.7",
            "records_affected": 2300,
            "projections": ["identity_audit"],
        },
        {
            # Invisivel ao time azul — `08` §2. Nao pode chegar a gerador nenhum.
            "fact_id": "GT-A-099",
            "fact_class": "lateral_discovery",
            "exercise_time": "T-16d 03:00",
            "actor": "conta_fantasma",
            "source_ip": "203.0.113.9",
        },
    ]
}


def gerador_fiel(fatos):
    """Escreve so campo PROJETAVEL — o gerador que os itens 1 e 5 admitem.

    A versao anterior escrevia `id={f['fact_class']}`, e `fact_class` e a
    classificacao do incidente na kill chain: gabarito. Ela passava porque nao
    havia guarda; hoje seria recusada, e e por isso que ela virou o caso
    negativo `gerador_que_classifica`.
    """
    return "\n".join(
        f"user={f.get('actor', '-')} src={f.get('source_ip', '-')} "
        f"action={f.get('action', '-')}"
        for f in fatos
    )


def gerador_que_inventa(fatos):
    """Acrescenta um endereco que o ground truth nao fixou."""
    return gerador_fiel(fatos) + "\nrelay=203.0.113.200"


def gerador_que_inventa_host(fatos):
    """Acrescenta um host de sufixo impecavel e rotulo que ninguem fixou.

    O sufixo E reservado (`05` §2), entao o predicado de IOC o aprova: quem tem
    de recusar e o elenco, e so ele — M2 da segunda auditoria.
    """
    return gerador_fiel(fatos) + "\nrelay=intranet-ti.example"


def gerador_que_entrega_o_veredito(fatos):
    """Escreve `credential_state` — o defeito exato do B1."""
    return "\n".join(
        f"user={f.get('actor', '-')} credential={f.get('credential_state', '-')}"
        for f in fatos
    )


def gerador_que_registra_o_campo_vazio(fatos):
    """Escreve a CHAVE `credential_state` com valor vazio, e mais nada.

    O valor nao vaza; a chave sim. `jsonl.py` ja tinha o argumento escrito: um
    campo presente com valor vazio *"afirmaria que o valor foi medido e e
    vazio — que e diferente de nao ter sido registrado. O time azul le a
    diferenca"*. A chave diz que a fonte RASTREIA o estado da credencial, e o
    time azul passa a procurar onde o gabarito ja disse que ha o que achar.
    """
    return "\n".join(
        json.dumps({"actor": f.get("actor"), "credential_state": ""}) for f in fatos
    )


def gerador_que_classifica(fatos):
    """Escreve `fact_class` — a leitura do gabarito sobre a kill chain."""
    return "\n".join(f"signature={f['fact_class']}" for f in fatos)


def gerador_que_carimba_o_fact_id(fatos):
    """Escreve o `fact_id` no registro — `05` §6, o gabarito na primeira linha."""
    return "\n".join(f"ref={f['fact_id']} user={f.get('actor', '-')}" for f in fatos)


def gerador_que_copia_a_dificuldade(fatos):
    """Copia a frase de `discoverability.requires` para o corpo do arquivo.

    E o caso que a busca por TOKEN nao pegaria: o valor tem espacos, e e a
    frase que literalmente diz ao leitor o que ha para descobrir.
    """
    return "\n".join(
        f"user={f.get('actor', '-')} nota: {(f.get('discoverability') or {}).get('requires', '-')}"
        for f in fatos
    )


def geradores_para(fontes, gerador=gerador_fiel):
    return {fonte: gerador for fonte in fontes}


class OBannerVemDoContrato(unittest.TestCase):
    """`05` §4 — banner em todo artefato gerado, na primeira linha."""

    def test_o_texto_e_LIDO_do_contrato_e_nao_reescrito(self):
        """A copia do texto num modulo seria a P1-13 de novo, por outra porta:
        duas fontes para a mesma norma, divergindo na terceira edicao."""
        self.assertEqual(
            banner.texto(CONTRATOS),
            CONTRATOS["evidence"]["x-aurora-security-constraints"]["banner_text"],
        )

    def test_syslog_e_cef_comentam_com_cerquilha(self):
        t = banner.texto(CONTRATOS)
        for formato in ("syslog_text", "cef_syslog"):
            self.assertTrue(banner.linha(formato, t).startswith("#"), formato)

    def test_jsonl_usa_objeto_JSON_VALIDO_e_nao_comentario(self):
        """JSONL nao tem comentario, e um `#` na primeira linha quebraria todo
        parser que o time azul apontar para o arquivo. O banner vira registro."""
        linha = banner.linha("jsonl", banner.texto(CONTRATOS))
        self.assertEqual(json.loads(linha)["_banner"], banner.texto(CONTRATOS))

    def test_rfc5322_usa_cabecalho_e_nao_cerquilha(self):
        """`.eml` nao tem comentario de linha; o idiomatico e um header."""
        linha = banner.linha("rfc5322", banner.texto(CONTRATOS))
        self.assertTrue(linha.startswith("X-"))
        self.assertIn(banner.texto(CONTRATOS), linha)

    def test_formato_desconhecido_e_RECUSADO(self):
        """Falha fechada: formato novo sem forma de banner declarada nao pode
        produzir arquivo sem banner em silencio."""
        with self.assertRaises(banner.FormatoSemBanner):
            banner.linha("pcap", banner.texto(CONTRATOS))

    def test_round_trip_reconhece_o_proprio_banner(self):
        t = banner.texto(CONTRATOS)
        for formato in ("syslog_text", "cef_syslog", "jsonl", "rfc5322"):
            conteudo = banner.linha(formato, t) + "\ncorpo"
            self.assertTrue(banner.tem_banner(conteudo, formato, t), formato)

    def test_conteudo_sem_banner_nao_passa(self):
        self.assertFalse(
            banner.tem_banner("corpo sem banner", "syslog_text", banner.texto(CONTRATOS))
        )

    def test_banner_fora_da_PRIMEIRA_linha_nao_conta(self):
        """`05` §4 diz *na primeira linha*, e a posicao e o requisito: banner no
        rodape nao avisa quem abre o arquivo e le as primeiras linhas."""
        t = banner.texto(CONTRATOS)
        conteudo = "corpo\n" + banner.linha("syslog_text", t)
        self.assertFalse(banner.tem_banner(conteudo, "syslog_text", t))


class OMotorProjeta(unittest.TestCase):
    def setUp(self):
        self.formatos = contract_source.formatos_por_fonte(CONTRATOS)

    def _projetar(self, gerador=gerador_fiel, gt=GT):
        return projecao.projetar(
            gt,
            geradores=geradores_para(("vpn", "identity_audit"), gerador),
            formatos=self.formatos,
            banner=banner.texto(CONTRATOS),
            campos_do_fato=CAMPOS,
        )

    def test_uma_fonte_por_entrada_da_cobertura(self):
        fontes = {f.fonte for f in self._projetar()}
        self.assertEqual(fontes, {"vpn", "identity_audit"})

    def test_cada_gerador_recebe_APENAS_os_fatos_da_sua_fonte(self):
        recebidos: dict[str, list[str]] = {}

        def espiao_de(fonte):
            def gerador(fatos):
                recebidos[fonte] = [f["fact_id"] for f in fatos]
                return gerador_fiel(fatos)

            return gerador

        projecao.projetar(
            GT,
            geradores={f: espiao_de(f) for f in ("vpn", "identity_audit")},
            formatos=self.formatos,
            banner=banner.texto(CONTRATOS),
            campos_do_fato=CAMPOS,
        )
        self.assertEqual(recebidos["vpn"], ["GT-A-014"])
        self.assertEqual(recebidos["identity_audit"], ["GT-A-014", "GT-A-031"])

    def test_fato_SEM_projections_nao_chega_a_gerador_nenhum(self):
        """`06` T13: *"fato sem `projections` nao aparece em nenhuma fonte"*."""
        for fonte in self._projetar():
            self.assertNotIn("conta_fantasma", fonte.conteudo, fonte.fonte)
            self.assertNotIn("203.0.113.9", fonte.conteudo, fonte.fonte)

    def test_o_banner_e_a_primeira_linha_de_TODA_fonte(self):
        t = banner.texto(CONTRATOS)
        for fonte in self._projetar():
            self.assertTrue(banner.tem_banner(fonte.conteudo, fonte.formato, t), fonte.fonte)

    def test_o_formato_de_cada_fonte_vem_do_CONTRATO(self):
        por_fonte = {f.fonte: f.formato for f in self._projetar()}
        self.assertEqual(por_fonte["vpn"], "syslog_text")
        self.assertEqual(por_fonte["identity_audit"], "jsonl")

    def test_gerador_AUSENTE_para_fonte_da_cobertura_e_recusado_nomeando_a_fonte(self):
        """Falha fechada: a fonte ficaria sem arquivo, e a cobertura de `08` §7
        passaria a mentir em silencio."""
        with self.assertRaises(projecao.GeradorAusente) as ctx:
            projecao.projetar(
                GT,
                geradores=geradores_para(("vpn",)),
                formatos=self.formatos,
                banner=banner.texto(CONTRATOS),
                campos_do_fato=CAMPOS,
            )
        self.assertIn("identity_audit", str(ctx.exception))

    def test_gerador_que_INVENTA_endereco_e_recusado(self):
        """**O item 1 virando porta.** `08` §2: *"projecao nao inventa entidade;
        consome o elenco fixado pelo ground truth"*."""
        with self.assertRaises(projecao.EntidadeInventada) as ctx:
            self._projetar(gerador_que_inventa)
        self.assertIn("203.0.113.200", str(ctx.exception))

    def test_a_recusa_NOMEIA_a_fonte_CERTA(self):
        """Mensagem que so diz "invalido" manda o autor do gerador procurar.

        **So uma fonte inventa**, e a outra e fiel — de proposito. Com as duas
        inventando, a asserção passaria nomeando qualquer uma das duas, e o que
        se quer provar e que a mensagem aponta a fonte em que o defeito esta.
        """
        with self.assertRaises(projecao.EntidadeInventada) as ctx:
            projecao.projetar(
                GT,
                geradores={"vpn": gerador_que_inventa, "identity_audit": gerador_fiel},
                formatos=self.formatos,
                banner=banner.texto(CONTRATOS),
                campos_do_fato=CAMPOS,
            )
        mensagem = str(ctx.exception)
        self.assertIn("vpn", mensagem)
        self.assertNotIn("identity_audit", mensagem)

    def test_gerador_que_INVENTA_host_e_recusado(self):
        """**M2 da segunda auditoria.** O sufixo e reservado, entao `05` §2 esta
        satisfeito e o predicado de IOC aprova. Quem tem de recusar e o elenco:
        `intranet-ti` nao e ator, destino nem endereco de fato nenhum.

        E ELE NAO PODIA SER PEGO DEPOIS. Um literal no gerador e determinista, e
        a reprojecao do `evidence verify` roda o MESMO gerador — os bytes batem
        das duas vezes. Ou a recusa e aqui, ou nao ha recusa.
        """
        with self.assertRaises(projecao.EntidadeInventada) as ctx:
            self._projetar(gerador_que_inventa_host)
        self.assertIn("intranet-ti.example", str(ctx.exception))

    def test_o_host_DERIVADO_do_elenco_passa(self):
        """O par positivo do anterior, e o que impede a guarda de proibir o
        unico jeito correto: `svc_academus` vira `svc-academus.example` porque
        `_` nao e valido em rotulo de host (RFC 1123)."""

        def deriva(fatos):
            return gerador_fiel(fatos) + "\nlink=https://svc-academus.example/x"

        self.assertEqual(len(self._projetar(deriva)), 2)

    def test_gerador_que_escreve_o_VEREDITO_do_gabarito_e_recusado(self):
        """**B1 da segunda auditoria, o defeito verbatim.**

        `credential_state` e `compromised` no fato real, e nenhum concentrador
        de VPN do mundo sabe disso — e atribuicao, e atribuicao e o achado que o
        exercicio mede. `00` §3 separa evidencia observavel de ground truth.
        """
        with self.assertRaises(projecao.VereditoDoGabarito) as ctx:
            self._projetar(gerador_que_entrega_o_veredito)
        self.assertIn("credential_state", str(ctx.exception))

    def test_gerador_que_escreve_a_CLASSE_do_fato_e_recusado(self):
        """`initial_access` e `exfiltration` sao a classificacao do incidente na
        kill chain — leitura do gabarito, nao sinal de sensor. Era a `signature`
        do `cef.log` ate o H1."""
        with self.assertRaises(projecao.VereditoDoGabarito) as ctx:
            self._projetar(gerador_que_classifica)
        self.assertIn("fact_class", str(ctx.exception))

    def test_o_INDICE_de_agulhas_responde_o_MESMO_que_a_busca(self):
        """A otimizacao do H1 da 4ª auditoria, com o oraculo sendo a versao lenta.

        Projetar a população inteira da Linha B levou `projetar` de menos de um
        segundo para **128 s**: a guarda rodava `re.search` sobre o conteúdo
        inteiro uma vez por agulha, e com 3.145 fatos isso é ~9 GB de varredura
        para responder pertinência. O índice de corridas máximas faz a mesma
        pergunta em uma passada — **0,36 s**.

        Otimização de guarda é onde um gate silenciosamente para de morder, então
        a equivalência é o que se testa, e não o ganho: para cada agulha, o
        índice e o `re.search` têm de concordar. O caso inclui as três formas que
        distinguem os dois caminhos — corrida pura, valor com espaço, e prefixo
        que NÃO deve casar.
        """
        conteudo = (
            '{"actor": "svc_academus", "ref": "GT-A-014"}\n'
            "user=svc_academus credential=compromised\n"
            "nota: correlacionar horario fora de expediente\n"
        )
        indice = projecao._indice_de_agulhas(conteudo)
        agulhas = [
            "svc_academus",
            "GT-A-014",
            "GT-A-01",  # PREFIXO: nao casa, e e o caso que a fronteira existe para
            "GT-A-0142",  # SUFIXO: idem
            "compromised",
            "credential",
            "credential_state",  # ausente
            "correlacionar horario fora de expediente",  # com espaco: cai no re.search
            "horario fora",
            "ausente_de_tudo",
        ]
        for agulha in agulhas:
            with self.subTest(agulha=agulha):
                cabe = projecao._CORRIDA.fullmatch(agulha) is not None
                pelo_indice = agulha in indice if cabe else projecao._ocorre(agulha, conteudo)
                self.assertEqual(
                    pelo_indice,
                    projecao._ocorre(agulha, conteudo),
                    "o indice e a busca divergiram — a guarda passou a responder "
                    "outra pergunta",
                )

    def test_a_CHAVE_do_campo_de_gabarito_tambem_e_recusada(self):
        """O valor nao vaza e a guarda morde mesmo assim — e o motivo esta
        escrito em `jsonl.py` desde a peca 3: campo presente com valor vazio
        **afirma que o valor foi medido**, e isso e diferente de nao ter sido
        registrado. A chave sozinha ja diz ao time azul onde procurar."""
        with self.assertRaises(projecao.VereditoDoGabarito) as ctx:
            self._projetar(gerador_que_registra_o_campo_vazio)
        self.assertIn("credential_state", str(ctx.exception))

    def test_gerador_que_carimba_o_FACT_ID_e_recusado(self):
        """`05` §6. `jsonl.py` ja excluia o campo em comentario, e comentario nao
        e mecanismo: a exclusao dependia de cada autor de gerador lembrar."""
        with self.assertRaises(projecao.VereditoDoGabarito) as ctx:
            self._projetar(gerador_que_carimba_o_fact_id)
        self.assertIn("GT-A-014", str(ctx.exception))

    def test_a_guarda_alcanca_valor_COM_ESPACO_dentro_de_mapa(self):
        """`discoverability.requires` e uma FRASE, e e a que diz o que ha para
        descobrir. Ela nao e um token — a guarda tem de alcanca-la inteira, e e
        por isso que a busca e por fronteira de palavra e nao por igualdade de
        token."""
        with self.assertRaises(projecao.VereditoDoGabarito) as ctx:
            self._projetar(gerador_que_copia_a_dificuldade)
        self.assertIn("ausencia de MFA", str(ctx.exception))

    def test_a_guarda_NAO_reclama_de_campo_projetavel(self):
        """O par negativo da guarda — sem ele, uma versao que recusasse todo
        campo passaria nos cinco testes acima e proibiria o `vpn.log` inteiro.

        `mfa` esta no fato e E projetavel: um concentrador de VPN registra se o
        segundo fator foi apresentado. O veredito sobre a credencial, nao.
        """

        def escreve_mfa(fatos):
            return "\n".join(f"mfa={f.get('mfa', '-')}" for f in fatos)

        fontes = self._projetar(escreve_mfa)
        self.assertIn("mfa=absent", fontes[0].conteudo)

    def test_nome_de_FONTE_no_conteudo_nao_e_veredito(self):
        """A exclusao declarada: `projections` carrega nomes de fonte, e eles
        sao vocabulario da camada de projecao. Procura-los em texto livre
        acusaria a palavra "email" no corpo de um e-mail."""

        def cita_a_fonte(fatos):
            return gerador_fiel(fatos) + "\ncomentario: consulte o vpn e o email"

        self.assertEqual(len(self._projetar(cita_a_fonte)), 2)

    # -- B1 da 3a auditoria: a fonte que entrega a resposta -------------------

    #: Um gabarito com CASO DECLARADO. `GT-A-014` e o unico `initial_access` do
    #: documento e o `line_b_cases` o cita — entao, dentro daquela especie, toda
    #: linha que as fontes dele carregam e caso.
    #:
    #: `GT-A-031` (`exfiltration`) fica de fora dos casos de proposito: e ele
    #: que mostra que a guarda julga POR ESPECIE. Se julgasse a fonte inteira, a
    #: presenca dele ja diluiria o vazamento — e o time azul nao confunde uma
    #: exfiltracao com um acesso inicial.
    GT_COM_CASOS = {
        "facts": GT["facts"],
        "line_b_cases": [
            {
                "case_id": "GC-001",
                "defensibility": 1.0,
                "set": "indevido_comprovado",
                "supporting_evidence": ["GT-A-014"],
            },
        ],
    }

    def test_a_fonte_que_projeta_SO_CASO_e_recusada(self):
        """**B1 da terceira auditoria.**

        O `database_audit.jsonl` levava as 67 linhas que `line_b_cases` cita
        como caso, e **so elas**, numa populacao de 3.145 alteracoes de nota. O
        participante nao precisava ler campo nenhum: se esta no arquivo, e caso.

        E a guarda e sobre COBERTURA, nao sobre conteudo — ela dispara antes de
        o gerador escrever o primeiro byte, porque o defeito esta na declaracao
        do gabarito e nao na escrita.
        """
        with self.assertRaises(projecao.RespostaEntregue) as ctx:
            self._projetar(gt=self.GT_COM_CASOS)
        mensagem = str(ctx.exception)
        self.assertIn("line_b_cases", mensagem)

        # A FONTE NOMEADA E A DE CLASSES MISTAS, e e isso que prova que o
        # julgamento e POR ESPECIE. `identity_audit` carrega `initial_access`
        # (so caso) e `exfiltration` (nenhum caso); uma guarda que olhasse a
        # fonte inteira a consideraria diluida e so acusaria `vpn`.
        self.assertIn("identity_audit", mensagem)
        self.assertIn("initial_access", mensagem)

    def test_a_fonte_com_caso_ENTRE_ruido_passa(self):
        """O par positivo, e ele e o que impede a guarda de proibir o desenho
        correto: um arquivo com 67 casos entre 3.145 linhas nao revela nada.

        Aqui basta UM fato da mesma especie que nao seja caso para a igualdade
        se desfazer — que e exatamente a forma de conserto que a mensagem da
        recusa recomenda.
        """
        com_ruido = {
            "facts": [
                *GT["facts"],
                {
                    "fact_id": "GT-A-777",
                    "fact_class": "initial_access",
                    "exercise_time": "T-14d 09:00",
                    "actor": "svc_academus",
                    "action": "vpn_login",
                    "source_ip": "198.51.100.42",
                    "projections": ["vpn", "identity_audit"],
                },
            ],
            "line_b_cases": self.GT_COM_CASOS["line_b_cases"],
        }
        self.assertEqual(len(self._projetar(gt=com_ruido)), 2)

    def test_gabarito_SEM_casos_nao_tem_o_que_entregar(self):
        """O limite declarado: a guarda so morde onde ha resposta escrita. Um
        pack sem `line_b_cases` nao declara caso nenhum."""
        self.assertEqual(len(self._projetar()), 2)

    def test_gerador_fiel_ao_elenco_passa(self):
        """O par positivo da recusa: sem ele, um motor que recusasse TUDO
        passaria no teste acima."""
        self.assertEqual(len(self._projetar()), 2)

    def test_o_manifesto_CARREGA_o_banner(self):
        """**L2 da terceira auditoria.** `05` §4 fala de todo artefato gerado, e
        o `MANIFEST.json` e o PRIMEIRO arquivo que o facilitador abre — e o que
        diz o que existe. Ele ficou de fora porque a producao do banner e por
        formato de fio, e o manifesto nao tem um."""
        doc = manifesto.montar(
            self._projetar(),
            banner=banner.texto(CONTRATOS),
            pack_id=PACK,
            ground_truth_bytes=b"facts: []\n",
            random_seed=SEED,
        )
        self.assertEqual(doc["_banner"], banner.texto(CONTRATOS))
        self.assertEqual(next(iter(doc)), "_banner")

    def test_os_fatos_chegam_em_ordem_ESTAVEL(self):
        """Determinismo (R7 §6): a saida e funcao das fontes e do seed, e ordem
        de iteracao de conjunto nao entra nela."""
        primeira = [f["fact_id"] for f in [GT["facts"][0], GT["facts"][1]]]
        recebidos = []

        def espiao(fatos):
            recebidos.append([f["fact_id"] for f in fatos])
            return gerador_fiel(fatos)

        for _ in range(3):
            projecao.projetar(
                GT,
                geradores={"identity_audit": espiao, "vpn": gerador_fiel},
                formatos=self.formatos,
                banner=banner.texto(CONTRATOS),
                campos_do_fato=CAMPOS,
            )
        self.assertEqual(recebidos, [primeira, primeira, primeira])

    def test_duas_projecoes_do_mesmo_ground_truth_sao_IDENTICAS(self):
        um = [(f.fonte, f.conteudo) for f in self._projetar()]
        outro = [(f.fonte, f.conteudo) for f in self._projetar()]
        self.assertEqual(um, outro)

    def test_ground_truth_sem_fato_visivel_nao_projeta_nada(self):
        vazio = {"facts": [GT["facts"][2]]}
        self.assertEqual(self._projetar(gt=vazio), [])


class OManifesto(unittest.TestCase):
    """`08` §7 e `contracts/evidence.schema.yaml` — a P1-3."""

    def setUp(self):
        self.formatos = contract_source.formatos_por_fonte(CONTRATOS)
        self.fontes = projecao.projetar(
            GT,
            geradores=geradores_para(("vpn", "identity_audit")),
            formatos=self.formatos,
            banner=banner.texto(CONTRATOS),
            campos_do_fato=CAMPOS,
        )
        self.gt_bytes = b"facts: []\n"
        self.doc = manifesto.montar(
            self.fontes,
            banner=banner.texto(CONTRATOS),
            pack_id=PACK,
            ground_truth_bytes=self.gt_bytes,
            random_seed=SEED,
        )

    def test_o_manifesto_VALIDA_contra_o_contrato_real(self):
        """A P1-3 sendo fechada: `evidence.schema.yaml` valida um artefato de
        verdade pela primeira vez desde a Fase 1."""
        erros = manifesto.erros_de_schema(self.doc, CONTRATOS)
        self.assertEqual(erros, [], erros)

    def test_generated_from_carrega_pack_hash_e_seed(self):
        g = self.doc["generated_from"]
        self.assertEqual(g["pack_id"], PACK)
        self.assertEqual(g["random_seed"], SEED)
        self.assertEqual(
            g["ground_truth_hash"], "sha256:" + hashlib.sha256(self.gt_bytes).hexdigest()
        )

    def test_cada_fonte_declara_os_fact_id_que_projeta(self):
        por_arquivo = {s["file"]: set(s["projects_facts"]) for s in self.doc["sources"]}
        self.assertEqual(por_arquivo["vpn.log"], {"GT-A-014"})
        self.assertEqual(por_arquivo["identity_audit.jsonl"], {"GT-A-014", "GT-A-031"})

    def test_o_sha256_de_cada_fonte_confere_com_o_conteudo(self):
        por_arquivo = {s["file"]: s["sha256"] for s in self.doc["sources"]}
        for fonte in self.fontes:
            esperado = hashlib.sha256(fonte.conteudo.encode("utf-8")).hexdigest()
            self.assertEqual(por_arquivo[fonte.nome_do_arquivo], esperado, fonte.fonte)

    def test_toda_fonte_tem_window(self):
        """L3 da terceira auditoria: `window` e obrigatoria em TODA fonte, e nao
        so no modo liberado por inject — sem ela o facilitador nao sabe o que o
        arquivo abrange."""
        for s in self.doc["sources"]:
            self.assertTrue(s["window"], s["file"])

    def test_o_manifesto_NAO_carrega_fato_que_nao_projeta(self):
        citados = {f for s in self.doc["sources"] for f in s["projects_facts"]}
        self.assertNotIn("GT-A-099", citados)

    def test_o_nome_do_arquivo_segue_o_formato_da_fonte(self):
        arquivos = {s["file"] for s in self.doc["sources"]}
        self.assertEqual(arquivos, {"vpn.log", "identity_audit.jsonl"})

    def test_manifesto_INVALIDO_e_recusado_com_o_caminho(self):
        """O par negativo, e sem ele o teste positivo nao afirma nada: um
        validador que nunca recusa tambem devolve lista vazia.

        Quatro defeitos de uma vez, cada um numa clausula diferente do contrato
        — formato fora do enum v1, hash curto, sha invalido e `fact_id` fora da
        forma. O caminho vem junto (`$.sources[0].format`), que e o que permite
        ao autor do pack achar o defeito sem reler o manifesto inteiro.
        """
        ruim = {
            "generated_from": {
                "pack_id": PACK,
                "ground_truth_hash": "sha256:0",
                "random_seed": SEED,
            },
            "sources": [
                {
                    "file": "vpn.log",
                    "format": "pcap",
                    "delivery_mode": "pre_positioned",
                    "window": "T-17d → T-15d",
                    "projects_facts": ["gt-a-014"],
                    "sha256": "zz",
                }
            ],
        }
        erros = manifesto.erros_de_schema(ruim, CONTRATOS)
        caminhos = " ".join(erros)
        self.assertIn("$.sources[0].format", caminhos)
        self.assertIn("$.generated_from.ground_truth_hash", caminhos)
        self.assertIn("$.sources[0].sha256", caminhos)

    def test_o_ref_CRUZADO_para_o_contrato_de_ground_truth_resolve(self):
        """`projects_facts.items` faz `$ref` para
        `ground_truth.schema.json#/$defs/fact_id_pattern`, e resolver isso exige
        o `Registry` montado com os DOIS contratos.

        Sem o registry, `jsonschema` levantaria erro de resolucao — ou, pior,
        um validador mal montado ignoraria a clausula e o teste acima passaria
        pelos outros tres defeitos sem nunca exercitar este.
        """
        ruim = dict(self.doc)
        ruim["sources"] = [dict(self.doc["sources"][0], projects_facts=["gt-a-014"])]
        erros = manifesto.erros_de_schema(ruim, CONTRATOS)
        self.assertTrue(
            any("^GT-" in e for e in erros),
            f"a forma de `fact_id` nao foi exercitada: {erros}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
