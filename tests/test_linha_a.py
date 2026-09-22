"""P7-10 — o gabarito da Linha A: o incidente, sintetizado do seed.

O que esta suite prova:

1. **determinismo nas duas direcoes** — mesmo seed, mesmos fatos; seeds
   diferentes, fatos diferentes. Sem a segunda perna, um gerador que ignorasse
   o seed passaria no primeiro teste (a licao de `dataset.py`);
2. a **forma** dos fatos e a de `04` §3 / do exemplo de `ground_truth.schema.yaml`
   — `initial_access`, `privilege_escalation`, `exfiltration`, com os campos que
   o exemplo mostra;
3. o `source_ip` fica em **faixa de documentacao** (RFC 5737), o que
   `check_synthetic_data` exige;
4. os `verification_predicates` sao os do **incidente** (VPN revogada, escopo
   desabilitado, ausencia de exfiltracao), e nao a contencao da Linha B — a
   correcao que a P7-10 e.

Sao unitarios: `linha_a` sintetiza do seed, sem banco. O teste end-to-end (a
materializacao contra o banco semeado) e a prova do exercicio de 4 h.
"""

from __future__ import annotations

import ipaddress
import unittest

from contracts.generated.events import IDENTITY_SCOPE_DISABLED, VPN_ACCESS_REVOKED
from domains.academus.generated.flags import (
    ACADEMUS_ENROLLMENT_OFFLINE,
    ACADEMUS_LMS_DEGRADED,
)
from domains.academus.seed import linha_a

SEED = 424242
REDE_DOC = ipaddress.ip_network("198.51.100.0/24")


class ODeterminismo(unittest.TestCase):
    def test_mesmo_seed_mesmos_fatos(self):
        self.assertEqual(linha_a.facts(SEED), linha_a.facts(SEED))

    def test_seeds_diferentes_fatos_diferentes(self):
        self.assertNotEqual(linha_a.facts(SEED), linha_a.facts(SEED + 1))


class AFormaDosFatos(unittest.TestCase):
    def setUp(self) -> None:
        self.fatos = linha_a.facts(SEED)

    def test_as_fases_do_incidente_na_ordem_do_incidente(self):
        """A ORDEM E A DO INCIDENTE, e ela e a ordem do documento — o motor de
        projecao a herda para escrever cada log (`08` §1).

        `phishing_delivery` entrou na peca 3 da Fase 9, e NAO afrouxa este
        caso: ele continua fixando a lista INTEIRA e em ordem. `08` §3 exige a
        fonte `email.eml` com *"phishing de recadastramento — origem da Linha
        A"*, e sem o fato ela seria conteudo autoral em vez de projecao.
        """
        self.assertEqual(
            [f["fact_class"] for f in self.fatos],
            [
                "phishing_delivery",
                "initial_access",
                "privilege_escalation",
                "exfiltration",
            ],
        )

    def test_o_phishing_ANTECEDE_o_acesso_que_ele_possibilita(self):
        """A origem vem antes. Sem esta asserção, a lista acima poderia ser
        reordenada e continuar "completa"."""
        classes = [f["fact_class"] for f in self.fatos]
        self.assertLess(classes.index("phishing_delivery"), classes.index("initial_access"))

    def test_o_acesso_inicial_tem_os_campos_de_04_secao_3(self):
        acesso = next(f for f in self.fatos if f["fact_class"] == "initial_access")
        for campo in (
            "fact_id", "actor", "action", "source_ip", "exercise_time",
            "credential_state", "mfa", "projections", "discoverability",
        ):
            self.assertIn(campo, acesso, campo)
        self.assertEqual(acesso["credential_state"], "compromised")

    def test_os_fact_ids_casam_a_forma_do_contrato(self):
        import re
        for f in self.fatos:
            self.assertRegex(f["fact_id"], r"^GT-[A-Z0-9]+-[0-9]+$")

    def test_o_source_ip_e_faixa_de_documentacao(self):
        """TODOS os fatos, e nao so o primeiro. O caso antigo olhava
        `self.fatos[0]`, e com um fato novo na frente ele passaria a julgar
        outro fato sem que nada dissesse — indice posicional em teste de forma
        e a mesma fragilidade que a lista de `fact_class` tem, sem o mesmo
        aviso."""
        for fato in self.fatos:
            if "source_ip" not in fato:
                continue
            ip = ipaddress.ip_address(fato["source_ip"])
            self.assertIn(
                ip, REDE_DOC, f"{fato['fact_class']}: source_ip fora da faixa — 05 §3"
            )

    def test_ha_um_fato_de_exfiltracao_para_a_ausencia_referenciar(self):
        """`containment` exige `absence_of exfiltration since self`; sem um fato
        de exfiltracao no gabarito, o predicado nao teria contra o que se medir."""
        self.assertTrue(any(f["fact_class"] == "exfiltration" for f in self.fatos))


class OsPredicadosSaoDoIncidente(unittest.TestCase):
    """A correcao da P7-10: a contencao do pack e a do ransomware, nao da Linha B."""

    def setUp(self) -> None:
        self.pred = linha_a.predicados_de_verificacao()

    def test_contencao_e_o_incidente_e_nao_grade_change(self):
        folhas = self.pred["containment"]["all"]
        eventos = {f["event"] for f in folhas if "event" in f}
        self.assertEqual(eventos, {VPN_ACCESS_REVOKED, IDENTITY_SCOPE_DISABLED})
        ausencias = [f["absence_of"] for f in folhas if "absence_of" in f]
        self.assertEqual(ausencias[0]["fact_class"], "exfiltration")
        self.assertEqual(ausencias[0]["since"], "self")

    def test_restauracao_e_as_duas_flags(self):
        folhas = self.pred["service_restoration"]["all"]
        flags = {f["flag_false"] for f in folhas}
        self.assertEqual(flags, {ACADEMUS_ENROLLMENT_OFFLINE, ACADEMUS_LMS_DEGRADED})

    def test_estrutura_nova_a_cada_chamada(self):
        """Constante de modulo seria mapa mutavel compartilhado entre gabaritos."""
        self.assertIsNot(
            linha_a.predicados_de_verificacao(),
            linha_a.predicados_de_verificacao(),
        )


if __name__ == "__main__":
    unittest.main()
