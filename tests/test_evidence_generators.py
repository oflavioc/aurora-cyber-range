"""As quatro fontes de `08` §3, e a guarda de IOC — itens 1 e 5 da DoD.

O QUE ESTA SUITE FECHA
======================
`08_EVIDENCE_SIMULATOR.md` §3 enumera as fontes v1 e diz o que cada uma carrega:

    email.eml               phishing de recadastramento — origem da Linha A
    vpn.log                 autenticacao sem MFA, horario anomalo
    identity_audit.jsonl    conta de servico, criacao de sessao, escalada
    database_audit.jsonl    leitura em massa (Linha A) e alteracoes de nota
                            com IP e sessao (Linha B)

Ate a peca 2 o motor existia e nao havia o que projetar: os geradores eram
dubles. Aqui eles sao os de verdade, e a suite julga **a saida contra o fato**.

DUAS LACUNAS DO GABARITO QUE ESTA PECA FECHA
=============================================
A peca 1 mediu a primeira (§2.3 do registro): os fatos da **Linha B** nao
declaravam `projections`, enquanto `08` §3 diz que `database_audit.jsonl`
carrega *"alteracoes de nota com IP e sessao (Linha B)"*. A segunda apareceu ao
escrever esta peca e e da mesma familia: **nenhum fato declarava
`projections: [email]`**, e `08` §3 exige a fonte `email.eml` com origem na
Linha A — o gerador nao produzia o fato de phishing.

Nos dois casos a spec esta coerente e o **gerador** e que estava incompleto. Nao
e spec-change: `08` §3 e autoridade sobre o que cada fonte carrega, e quem
declara `projections` e o gabarito, que e mecanismo.

O ITEM 5, E POR QUE ELE REUSA O PREDICADO EXISTENTE
====================================================
*"Nenhum arquivo contem anexo, binario, IOC real ou dominio roteavel"* — e o
predicado que responde isso **ja existe**, em `dados_sinteticos`
(`achados_no_valor`), e ja e usado pelo loader de pack com entrada propria na
whitelist de imports do core.

Escrever um segundo detector no motor seria a **P1-13 pela terceira porta**: duas
respostas para *"este valor e sintetico?"*, divergindo na primeira faixa nova.
Aqui o motor consome o mesmo predicado, e o que o CI julga e o que o gerador
obedece.

O `.eml` TEM TRES NEGATIVAS, E ELAS SAO `05` §2 LITERAL
========================================================
*"O `.eml` de phishing contem texto e um link para dominio da faixa reservada de
documentacao. Nenhum anexo. Nenhuma URL clicavel para host existente."* Sao tres
afirmacoes separadas, e cada uma tem caso proprio: sem anexo, sem MIME
multipart, e o link em sufixo reservado.
"""

from __future__ import annotations

import importlib
import json
import unittest
from urllib.parse import urlsplit

from dados_sinteticos import achados_no_valor
from range_core.engine.loader import contract_source

#: Tudo o que a prova negativa muta e resolvido por `sys.modules`, e nunca por
#: `from <pacote> import <submodulo>` — o atributo do pacote nao acompanha a
#: substituicao que o harness faz. A licao e da peca 1 (§2.4 do registro), e
#: reincidiu aqui com `linha_a`: a mutacao do fato de phishing nao derrubava
#: teste nenhum porque este arquivo segurava o modulo original.
banner = importlib.import_module("range_core.evidence.banner")
projecao = importlib.import_module("range_core.evidence.projecao")
geradores_mod = importlib.import_module("domains.academus.evidence_generators")
linha_a = importlib.import_module("domains.academus.seed.linha_a")

CONTRATOS = contract_source.read_contracts()
SEED = 424242

#: As quatro de `08` §3. `cef` entra pela tabela porque o GABARITO o declara
#: (`projections` da Linha A desde a P7-10) e o motor recusa cobertura sem
#: gerador; `precursor` continua fora — e o item 3, com desenho proprio.
FONTES_DA_SECAO_3 = ("email", "vpn", "identity_audit", "database_audit")

GERADORES = geradores_mod.geradores(CONTRATOS)


def _fontes_que_o_gabarito_declara(fatos):
    """A cobertura esperada, DERIVADA do gabarito.

    Numero fixo aqui seria constante magica que envelhece: quando o gabarito
    ganhar uma fonte, o teste deve cobrar a fonte nova — nao falhar por
    contagem. Foi o que aconteceu quando o `cef` entrou nesta peca.
    """
    return {fonte for fato in fatos for fonte in (fato.get("projections") or ())}


def _projetar(fatos, geradores=None):
    return projecao.projetar(
        {"facts": fatos},
        geradores=GERADORES if geradores is None else geradores,
        formatos=contract_source.formatos_por_fonte(CONTRATOS),
        banner=banner.texto(CONTRATOS),
    )


def _corpo(fonte):
    """O conteudo sem a linha de banner — o que o gerador de fato escreveu."""
    return fonte.conteudo.split("\n", 1)[1]


class OGabaritoDeclaraAsFontesQueA08SecaoTresExige(unittest.TestCase):
    def setUp(self):
        self.fatos = linha_a.facts(SEED)
        self.por_fonte: dict[str, list] = {}
        for fato in self.fatos:
            for fonte in fato.get("projections") or ():
                self.por_fonte.setdefault(fonte, []).append(fato)

    def test_a_linha_A_tem_fato_de_PHISHING_projetado_em_email(self):
        """`08` §3: *"phishing de recadastramento — origem da Linha A"*. Sem o
        fato, `email.eml` seria conteudo autoral em vez de projecao."""
        self.assertIn("email", self.por_fonte)

    def test_o_phishing_ANTECEDE_o_acesso_inicial_na_ordem_do_documento(self):
        """E a origem da Linha A: o e-mail vem antes do login que ele
        possibilitou. A ordem do documento e a ordem do incidente."""
        classes = [f["fact_class"] for f in self.fatos]
        self.assertLess(classes.index("phishing_delivery"), classes.index("initial_access"))

    def test_o_fato_de_phishing_e_DETERMINISTA_nas_duas_direcoes(self):
        um = [f for f in linha_a.facts(SEED) if f["fact_class"] == "phishing_delivery"]
        igual = [f for f in linha_a.facts(SEED) if f["fact_class"] == "phishing_delivery"]
        outro = [f for f in linha_a.facts(SEED + 1) if f["fact_class"] == "phishing_delivery"]
        self.assertEqual(um, igual)
        self.assertNotEqual(um, outro)

    def test_as_tres_fontes_da_linha_A_continuam_declaradas(self):
        for fonte in ("vpn", "identity_audit", "database_audit"):
            self.assertIn(fonte, self.por_fonte, fonte)


class ATabelaDeGeradores(unittest.TestCase):
    def test_as_quatro_fontes_da_secao_3_tem_gerador(self):
        for fonte in FONTES_DA_SECAO_3:
            self.assertIn(fonte, GERADORES, fonte)

    def test_a_tabela_nao_declara_fonte_FORA_do_registro_do_contrato(self):
        """`x-aurora-registry.source_formats` e conjunto FECHADO de v1: um
        gerador para fonte que o contrato nao conhece escreveria arquivo que o
        manifesto nao sabe declarar."""
        do_contrato = set(contract_source.formatos_por_fonte(CONTRATOS))
        self.assertEqual(set(GERADORES) - do_contrato, set())

    def test_a_tabela_cobre_TUDO_o_que_o_gabarito_declara(self):
        """A conjuncao que o motor cobra por falha fechada: se o gabarito
        declara uma fonte sem gerador, o `evidence build` nao roda. E como o
        `cef` entrou nesta peca — o gabarito ja o declarava desde a P7-10."""
        declaradas = {
            fonte
            for fato in linha_a.facts(SEED)
            for fonte in (fato.get("projections") or ())
        }
        self.assertEqual(declaradas - set(GERADORES), set())


class CadaGeradorProjetaOFato(unittest.TestCase):
    def setUp(self):
        self.fatos = linha_a.facts(SEED)
        self.fontes = {f.fonte: f for f in _projetar(self.fatos)}

    def test_o_vpn_log_traz_usuario_endereco_e_a_ausencia_de_MFA(self):
        """`08` §3: *"autenticacao sem MFA, horario anomalo"*."""
        acesso = next(f for f in self.fatos if f["fact_class"] == "initial_access")
        corpo = _corpo(self.fontes["vpn"])
        self.assertIn(acesso["actor"], corpo)
        self.assertIn(acesso["source_ip"], corpo)
        self.assertIn(acesso["mfa"], corpo)

    def test_o_identity_audit_e_JSONL_valido_com_um_objeto_por_fato(self):
        linhas = [l for l in _corpo(self.fontes["identity_audit"]).splitlines() if l.strip()]
        esperados = [f for f in self.fatos if "identity_audit" in (f.get("projections") or ())]
        self.assertEqual(len(linhas), len(esperados))
        for linha in linhas:
            json.loads(linha)

    def test_o_database_audit_traz_o_volume_da_leitura_em_massa(self):
        """`08` §3: *"leitura em massa (Linha A)"*. `records_affected` e o campo
        que o fato declara, e o que o time azul correlaciona."""
        exfil = next(f for f in self.fatos if f["fact_class"] == "exfiltration")
        corpo = _corpo(self.fontes["database_audit"])
        self.assertIn(str(exfil["records_affected"]), corpo)

    def test_todo_registro_JSONL_carrega_o_instante_do_fato(self):
        for fonte in ("identity_audit", "database_audit"):
            for linha in _corpo(self.fontes[fonte]).splitlines():
                if linha.strip():
                    self.assertIn("exercise_time", json.loads(linha), fonte)

    def test_NENHUMA_fonte_carrega_o_fact_id(self):
        """`05` §6 — o arquivo vai para o PARTICIPANTE, e `GT-A-014` numa linha
        de log entrega o gabarito.

        E a mesma razao pela qual a amarracao fato -> fonte e por CONTEUDO (o
        elenco, peca 1) em vez de por carimbo: o carimbo seria trivial de
        verificar e impossivel de publicar.
        """
        ids = {f["fact_id"] for f in self.fatos}
        for fonte in self.fontes.values():
            for fact_id in ids:
                self.assertNotIn(fact_id, fonte.conteudo, f"{fonte.fonte}: {fact_id}")


class OEmailDePhishingObedeceA05SecaoDois(unittest.TestCase):
    def setUp(self):
        self.fatos = linha_a.facts(SEED)
        self.eml = _corpo({f.fonte: f for f in _projetar(self.fatos)}["email"])

    def test_tem_os_cabecalhos_de_RFC_5322(self):
        for cabecalho in ("From:", "To:", "Subject:", "Date:"):
            self.assertIn(cabecalho, self.eml, cabecalho)

    def test_NAO_tem_anexo(self):
        """`05` §2: *"nenhum anexo"*, e a negativa e literal."""
        self.assertNotIn("Content-Disposition: attachment", self.eml)
        self.assertNotIn("filename=", self.eml)

    def test_NAO_e_multipart(self):
        """MIME multipart e o veiculo de anexo; sem ele, nao ha onde um caber."""
        self.assertNotIn("multipart/", self.eml)
        self.assertNotIn("boundary=", self.eml)

    def test_o_link_aponta_para_SUFIXO_RESERVADO_a_documentacao(self):
        """`05` §2: *"nenhuma URL clicavel para host existente"*. Quem julga e o
        mesmo predicado que o CI usa, e nao uma lista escrita aqui.

        Sobre o TOKEN da URL, e nao sobre o corpo inteiro — ver o caso de IOC.
        """
        urls = [t for t in self.eml.split() if t.startswith("http")]
        self.assertTrue(urls, "o phishing nao tem link, e `08` §3 o exige")
        for url in urls:
            self.assertEqual(achados_no_valor(url), [], url)

    def test_o_dominio_do_link_DERIVA_de_entidade_do_elenco(self):
        """Nao ha dominio inventado: ele sai de um valor que o fato declara,
        mais um sufixo reservado. Um dominio escrito a mao no gerador seria
        entidade que o ground truth nao fixou — o item 1 pela porta do texto,
        onde o oraculo de endereco nao olha (ele so tem forma fechada para IP).

        **SOBRE O HOST DA URL, e nao sobre o corpo.** A primeira versao deste
        caso so verificava que o ator aparecia em algum lugar do `.eml` — e ele
        aparece no `From:` de qualquer jeito, entao um host escrito a mao no
        link passaria inteiro. Medido pela prova negativa desta peca.
        """
        phishing = next(f for f in self.fatos if f["fact_class"] == "phishing_delivery")
        rotulo = phishing["actor"].replace("_", "-")
        urls = [t for t in self.eml.split() if t.startswith("http")]
        self.assertTrue(urls)
        for url in urls:
            host = urlsplit(url).hostname or ""
            self.assertTrue(
                host.startswith(rotulo), f"{host!r} nao deriva de {rotulo!r}"
            )


class OCefEProjecaoDoMesmoFato(unittest.TestCase):
    """`08` §2: *"a telemetria CEF e projecao, nao emissao independente"*."""

    def setUp(self):
        self.fatos = linha_a.facts(SEED)
        self.cef = _corpo({f.fonte: f for f in _projetar(self.fatos)}["cef"])

    def test_o_vendor_e_o_product_vem_do_CONTRATO(self):
        """`05` §5.1 — produto FICTICIO, nunca fornecedor real de mercado. Os
        valores vivem no contrato, e escreve-los no modulo seria a P1-13."""
        restricoes = contract_source.restricoes_de_evidencia(CONTRATOS)
        for linha in self.cef.splitlines():
            partes = linha.split("|")
            self.assertEqual(partes[1], restricoes["cef_vendor"])
            self.assertEqual(partes[2], restricoes["cef_product"])

    def test_o_cabecalho_tem_os_sete_campos_do_formato(self):
        for linha in self.cef.splitlines():
            self.assertGreaterEqual(len(linha.split("|")), 7, linha)

    def test_o_mesmo_fato_aparece_no_CEF_e_na_outra_fonte_dele(self):
        """A unificacao sendo verificada: `initial_access` projeta em `vpn` e em
        `cef`, e o endereco que aparece nos dois e o MESMO — porque sai do mesmo
        fato, e nao de dois geradores independentes."""
        acesso = next(f for f in self.fatos if f["fact_class"] == "initial_access")
        fontes = {f.fonte: _corpo(f) for f in _projetar(self.fatos)}
        self.assertIn(acesso["source_ip"], fontes["vpn"])
        self.assertIn(acesso["source_ip"], fontes["cef"])

    def test_NAO_julga_severidade_por_fato(self):
        """Severidade variavel seria avaliacao embutida na evidencia — a
        confusao de camadas de `00` §3 que este projeto existe para evitar."""
        severidades = {linha.split("|")[6] for linha in self.cef.splitlines()}
        self.assertEqual(len(severidades), 1)


class NenhumaFonteCarregaIOC(unittest.TestCase):
    """Item 5, com o predicado que o CI ja usa."""

    def test_nenhuma_fonte_tem_achado_de_dado_nao_sintetico(self):
        """**Token a token, e a tokenizacao aqui e por `split()` de proposito.**

        `achados_no_valor` opera sobre UM VALOR DE CAMPO: texto com espaco no
        meio ele descarta e devolve lista vazia. Chamado sobre o conteudo
        inteiro do arquivo, ele passa VACUAMENTE — foi o que a primeira versao
        desta suite fazia, e o que a primeira versao da guarda do motor fazia.

        O motor tokeniza por uma regex que tambem corta pontuacao; aqui e
        `split()` puro. **As duas tokenizacoes sao diferentes de proposito**: um
        teste que reusasse a do motor deixaria de ser oraculo independente e
        aprovaria um defeito na propria tokenizacao.
        """
        for fonte in _projetar(linha_a.facts(SEED)):
            for token in fonte.conteudo.split():
                self.assertEqual(achados_no_valor(token), [], f"{fonte.fonte}: {token}")

    def test_o_motor_RECUSA_gerador_que_escreve_dominio_roteavel(self):
        """A guarda no motor, e nao so no CI: o arquivo nao chega a existir."""
        with self.assertRaises(projecao.IOCEncontrado) as ctx:
            _projetar(
                linha_a.facts(SEED),
                geradores={
                    **GERADORES,
                    "vpn": lambda fatos: "visite https://www.bancoreal.com.br/login",
                },
            )
        self.assertIn("vpn", str(ctx.exception))

    def test_o_par_positivo_os_geradores_reais_passam(self):
        """Sem ele, um motor que recusasse TUDO passaria no teste acima."""
        fatos = linha_a.facts(SEED)
        self.assertEqual(
            {f.fonte for f in _projetar(fatos)}, _fontes_que_o_gabarito_declara(fatos)
        )


class ADeterminismoDaProjecao(unittest.TestCase):
    def test_duas_projecoes_do_mesmo_ground_truth_sao_IDENTICAS(self):
        um = [(f.fonte, f.conteudo) for f in _projetar(linha_a.facts(SEED))]
        outro = [(f.fonte, f.conteudo) for f in _projetar(linha_a.facts(SEED))]
        self.assertEqual(um, outro)

    def test_seeds_diferentes_produzem_projecoes_diferentes(self):
        """A prova negativa do determinismo — a licao de `dataset.py` que o
        `test_linha_a` ja registra: sem ela, um gerador que ignorasse o fato
        passaria no teste acima."""
        um = [(f.fonte, f.conteudo) for f in _projetar(linha_a.facts(SEED))]
        outro = [(f.fonte, f.conteudo) for f in _projetar(linha_a.facts(SEED + 1))]
        self.assertNotEqual(um, outro)

    def test_nenhum_gerador_inventa_entidade(self):
        """O item 1 sobre os geradores REAIS: se algum inventasse, `projetar`
        teria levantado `EntidadeInventada` antes de devolver as fontes."""
        fatos = linha_a.facts(SEED)
        self.assertEqual(
            {f.fonte for f in _projetar(fatos)}, _fontes_que_o_gabarito_declara(fatos)
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
