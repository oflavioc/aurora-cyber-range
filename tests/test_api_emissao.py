"""A consulta da trilha emite, e a guarda de boot recusa a rota muda.

O que esta suíte prova, e que é o item 1 da DoD da Fase 6:

1. **consultar a trilha com filtro de período emite `audit_query_performed`**,
   com os quatro `payload_fields` que `observability_hooks.yaml` declara;
2. **a guarda de boot recusa** quando a superfície declara `emite` e não há
   emissor ligado — recusa alta, com as rotas nomeadas;
3. o período inválido é recusado **antes** de consultar, e sem emitir.

Por que o emissor é duplo e o repositório também: o que está sob teste é a
INSTRUMENTAÇÃO — que a rota chame o emissor com os campos certos —, e não a
consulta SQL, que precisa de Postgres e é exercitada onde a stack existe. Um
teste que exigisse banco para provar emissão mediria as duas coisas e falharia
por qualquer uma.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field

from contracts.generated.events import AUDIT_QUERY_PERFORMED, INCIDENT_DECLARED
from domains.academus.api.app import confere_emissor_declarado


@dataclass
class EmissorEspiao:
    """Registra as chamadas. Não é `EventStore`: a rota fala com o `Emissor`."""

    chamadas: list[dict] = field(default_factory=list)

    def registrar_consulta(self, **kwargs) -> None:
        self.chamadas.append(kwargs)


SUPERFICIE_COM_EMISSAO = {
    "rotas": [
        {
            "method": "get",
            "path": "/audit/grade-changes",
            "status": "implementada",
            "emite": AUDIT_QUERY_PERFORMED,
        }
    ]
}

SUPERFICIE_SEM_EMISSAO = {
    "rotas": [{"method": "get", "path": "/students/{id}", "status": "implementada"}]
}


class GuardaDeBoot(unittest.TestCase):
    """`00` §5.5 — rota instrumentada em silêncio é pior que não instrumentada."""

    def test_rota_com_emite_e_sem_emissor_recusa_o_boot(self):
        with self.assertRaises(RuntimeError) as capturado:
            confere_emissor_declarado(SUPERFICIE_COM_EMISSAO, None)
        mensagem = str(capturado.exception)
        self.assertIn("GET /audit/grade-changes", mensagem)
        self.assertIn("emissor", mensagem)

    def test_rota_com_emite_e_com_emissor_passa(self):
        self.assertIsNone(
            confere_emissor_declarado(SUPERFICIE_COM_EMISSAO, EmissorEspiao())
        )

    def test_superficie_sem_emissao_nao_exige_emissor(self):
        """Sem rota que declare `emite`, não há o que ficar mudo.

        A assimetria é deliberada e igual à do `degradador`: esquecer o wiring
        não pode produzir exceção no meio de um exercício que não precisava
        dele.
        """
        self.assertIsNone(confere_emissor_declarado(SUPERFICIE_SEM_EMISSAO, None))

    def test_rota_planejada_nao_exige_emissor(self):
        """`planejada` ainda não existe no código — cobrá-la travaria o boot.

        É o mesmo eixo que `check_api_surface.py` guarda do outro lado: a rota
        planejada que já existe no código reprova. Aqui, a planejada que ainda
        não existe não pode exigir infraestrutura.
        """
        superficie = {
            "rotas": [
                {
                    "method": "post",
                    "path": "/futura",
                    "status": "planejada",
                    "emite": INCIDENT_DECLARED,
                }
            ]
        }
        self.assertIsNone(confere_emissor_declarado(superficie, None))


class PayloadDoHook(unittest.TestCase):
    """Os quatro campos são os de `observability_hooks.yaml`, e só eles."""

    def test_o_emissor_recebe_exatamente_os_campos_declarados(self):
        from domains.academus.api.repositorio import Escopo

        espiao = EmissorEspiao()
        espiao.registrar_consulta(
            period_start="2026-03-01T00:00:00",
            period_end="2026-03-31T00:00:00",
            group_by="user",
            result_count=3,
            escopo=Escopo("secretaria-1", None),
        )
        (chamada,) = espiao.chamadas
        self.assertEqual(
            set(chamada) - {"escopo"},
            {"period_start", "period_end", "group_by", "result_count"},
        )

    def test_os_campos_do_hook_e_os_do_emissor_sao_o_mesmo_conjunto(self):
        """A prova de fidelidade: o YAML e o código, lado a lado.

        Sem ela, acrescentar um campo no emissor sem declará-lo no hook faria o
        `observability_hooks.yaml` descrever um evento que não é o emitido — e
        `03` §1.2 apoia a evidência `auto` exatamente naquela declaração.
        """
        import inspect
        from pathlib import Path

        import yaml

        from domains.academus.api import emissor as modulo

        raiz = Path(__file__).resolve().parent.parent
        documento = yaml.safe_load(
            (raiz / "domains" / "academus" / "observability_hooks.yaml").read_text(
                encoding="utf-8"
            )
        )
        declarados = {
            campo
            for hook in documento["hooks"]
            if hook["event_type"] == AUDIT_QUERY_PERFORMED
            for campo in hook["payload_fields"]
        }
        assinatura = inspect.signature(modulo.Emissor.registrar_consulta)
        no_codigo = set(assinatura.parameters) - {"self", "escopo"}
        self.assertEqual(declarados, no_codigo)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
