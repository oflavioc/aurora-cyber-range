"""O helper materializa um pacote COMPLETO — e nunca em caminho versionado.

B1 DA AUDITORIA DA FASE 6, e esta suíte é a metade que prova que o mecanismo
respeita a norma que ele contorna.

`tests/fixtures/pack_completo.py` existe porque a fixture versionada afirma ser
um pacote completo sem ser: ela tem `injects.yaml` — o que a torna completa pelo
contrato — e não tem `ground_truth.yaml`, que `05` §6 põe fora do repositório
público.

**Mecanismo que contorna uma norma nasce com prova de que a respeita.** Por isso
a suíte tem duas metades:

1. o helper **monta** um pacote que o loader aceita como completo;
2. o helper **recusa** destino versionado, e o verificador do gabarito continua
   reprovando se um `ground_truth.yaml` aparecer versionado — sem exceção nenhuma
   por caminho.

A segunda é a que importa. Sem ela, o helper seria um caminho de escrita de
gabarito com a palavra de quem o escreveu como única garantia.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "fixtures"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _common import parse_yaml  # noqa: E402
from check_gabarito_fora_do_git import (  # noqa: E402
    MODULOS,
    SEED,
    TEMPLATE,
    verifica,
)
from pack_completo import (  # noqa: E402
    GABARITO,
    MINIMO,
    MaterializacaoFalhou,
    materializa,
)
from range_core.engine.loader import contract_source  # noqa: E402
from range_core.engine.loader.pack_loader import (  # noqa: E402
    AdapterFlags,
    PackError,
    PackSite,
    load_pack,
)

CONTRATOS = contract_source.read_contracts()
FLAGS = AdapterFlags.from_document(
    parse_yaml(REPO_ROOT / "domains" / "academus" / "flags.yaml"),
    source="domains/academus/flags.yaml",
)


def _fontes_reais() -> dict[str, str]:
    """As fontes que `verifica` exige — o template e os modulos do gerador.

    Injetadas REAIS e nao vazias: o eixo sob teste e o (a), do arquivo
    versionado, e um dicionario vazio faria a funcao morrer antes de chegar la —
    o teste passaria a medir a propria fixture do teste.
    """
    fontes = {TEMPLATE.name: TEMPLATE.read_text(encoding="utf-8")}
    fontes.update(
        {nome: (SEED / nome).read_text(encoding="utf-8") for nome in MODULOS}
    )
    return fontes


def carrega(diretorio):
    return load_pack(diretorio, contracts=CONTRATOS, adapter_flags=FLAGS)


class OHelperMontaUmPacoteCompleto(unittest.TestCase):
    def test_o_pacote_materializado_carrega(self):
        self.assertTrue(carrega(materializa()).pack_id)

    def test_ele_traz_o_documento_que_a_fixture_nao_pode_ter(self):
        self.assertIn(GABARITO, [p.name for p in Path(materializa()).iterdir()])
        self.assertFalse((MINIMO / GABARITO).exists())

    def test_a_fixture_versionada_SOZINHA_e_recusada_como_incompleta(self):
        """A razão de o helper existir, afirmada em vez de contada.

        Se um dia a fixture passar a carregar, este teste fica vermelho — e ou
        alguém versionou gabarito, ou o passo de completude parou de valer.
        """
        with self.assertRaises(PackError) as capturado:
            carrega(MINIMO)
        self.assertEqual(capturado.exception.site, PackSite.INCOMPLETE_PACK)

    def test_a_folha_do_predicado_e_uma_flag_que_a_fixture_MOVE(self):
        """Folha que a fixture não movesse faria o predicado nunca passar a valer.

        O pacote validaria e o avaliador ficaria eternamente em "não verificado" —
        a forma de defeito que a P6-2 corrigiu na spec, entrando por uma fixture.
        """
        pack = carrega(materializa())
        folhas = pack.verification_predicates["containment"]["all"]
        alvo = folhas[0]["flag_false"]
        movidas = {f for i in pack.injects for f, v in i.effects.items() if v is True}

        self.assertIn(alvo, movidas)


class OHelperNuncaEscreveEmCaminhoVersionado(unittest.TestCase):
    """A prova de que o mecanismo respeita a norma que ele contorna."""

    def test_destino_versionado_e_RECUSADO(self):
        with self.assertRaises(MaterializacaoFalhou) as capturado:
            materializa(MINIMO)
        self.assertIn("VERSIONADO", str(capturado.exception))

    def test_a_recusa_nomeia_o_documento_e_a_norma(self):
        """`06` T2 — detecção sem localização não permite intervir.

        A GRAFIA MUDOU COM A MIGRAÇÃO DA GUARDA, e a asserção acompanha o que
        ela afirma em vez do texto exato: a mensagem passou a nomear
        `05_SECURITY_REQUIREMENTS.md` §6 por extenso, em vez de `05` §6, porque
        ela agora é lida por quem roda `range-cli` e não só por quem edita esta
        fixture. Afirmar a grafia antiga faria o teste travar a melhora.
        """
        with self.assertRaises(MaterializacaoFalhou) as capturado:
            materializa(REPO_ROOT / "tests" / "fixtures")
        mensagem = str(capturado.exception)
        self.assertIn(GABARITO, mensagem)
        self.assertIn("§6", mensagem)
        self.assertIn("05_SECURITY_REQUIREMENTS", mensagem)

    def test_destino_NAO_versionado_e_aceito(self):
        """O positivo, sem o qual a recusa acima passaria por recusar tudo."""
        self.assertTrue(Path(materializa()).is_dir())

    def test_o_verificador_do_gabarito_reprova_se_o_helper_versionar(self):
        """A DIREÇÃO QUE FECHA: planta a saída do helper como versionada.

        Se alguém apontar o helper para um caminho rastreado e `git add` o
        resultado, `check_gabarito_fora_do_git.py` tem de reprovar — **sem
        exceção por caminho**, que é o que o cabeçalho dele fixa: `.gitignore` é
        convenção que `git add -f` atravessa.

        A injeção é por parâmetro, como a prova negativa daquele verificador já
        faz. Nada é escrito na árvore.
        """
        plantado = f"tests/fixtures/pack_completo/{GABARITO}"
        problemas = verifica(
            versionados=["README.md", plantado],
            gitignore=".aurora-pack/\nscenarios/\n",
            fontes=_fontes_reais(),
            documentos=None,
        )
        self.assertTrue(
            any(plantado in p and "VERSIONADO" in p for p in problemas),
            f"o verificador nao reprovou {plantado}: {problemas}",
        )

    def test_sem_o_plantio_o_verificador_nao_acusa_por_este_eixo(self):
        """O controle: sem ele, um verificador que reprovasse sempre passaria."""
        problemas = verifica(
            versionados=["README.md"],
            gitignore=".aurora-pack/\nscenarios/\n",
            fontes=_fontes_reais(),
            documentos=None,
        )
        self.assertFalse([p for p in problemas if "VERSIONADO" in p])


class OContratoDoGabaritoPASSAAValer(unittest.TestCase):
    """B1 — `ground_truth.yaml` entrou no mapa de validacao.

    Antes, o loader LIA o documento — folhas temporais, fatos com projecao,
    registros de integridade — e NUNCA o validava. Um pack completo sem
    `verification_predicates` carregava limpo, e `TTCV`/`TTRV` ficavam
    incomputaveis: a falha que `03` §3.1 diz que o pack nao pode ter, chegando em
    runtime em vez de na carga.
    """

    def monta(self, gabarito: str) -> Path:
        destino = Path(materializa())
        (destino / GABARITO).write_text(gabarito, encoding="utf-8")
        return destino

    def test_completo_sem_verification_predicates_RECUSA(self):
        """E a recusa NOMEIA o documento e o campo — `06` T2."""
        destino = self.monta(
            """facts:
  - fact_id: GT-FIXTURE-001
    fact_class: exfiltration
    exercise_time: 'T+00:05'
"""
        )
        with self.assertRaises(PackError) as capturado:
            carrega(destino)

        self.assertEqual(capturado.exception.site, PackSite.DOCUMENT_INVALID)
        mensagem = str(capturado.exception)
        self.assertIn(GABARITO, mensagem)
        self.assertIn("verification_predicates", mensagem)

    def test_a_recusa_cita_o_CONTRATO_do_gabarito_e_nao_o_do_cenario(self):
        """O mapa passou a admitir `$ref` para outro contrato, e a mensagem segue.

        Citar `scenario.schema.v2.yaml` mandaria quem le procurar a regra no
        arquivo errado.
        """
        destino = self.monta("facts: []\n")
        with self.assertRaises(PackError) as capturado:
            carrega(destino)
        self.assertIn("ground_truth.schema.json", str(capturado.exception))

    def test_objectives_yaml_tambem_entrou_no_mapa(self):
        """Foram DOIS e nao um: a varredura achou o segundo.

        `required_for_complete_pack` menos as chaves de `x-aurora-documents` dava
        `['ground_truth.yaml', 'objectives.yaml']` — o achado nomeava so o
        primeiro.
        """
        destino = Path(materializa())
        (destino / "objectives.yaml").write_text("objectives: 42\n", encoding="utf-8")
        with self.assertRaises(PackError) as capturado:
            carrega(destino)
        self.assertEqual(capturado.exception.site, PackSite.DOCUMENT_INVALID)
        self.assertIn("objectives.schema.json", str(capturado.exception))

    def test_o_pacote_completo_VALIDO_carrega(self):
        """O positivo, sem o qual as recusas acima passariam por recusar tudo."""
        self.assertTrue(carrega(materializa()).verification_predicates)


class ApenasManifestoContinuaSendoFormaLegitima(unittest.TestCase):
    """A RESSALVA do B1 — `04` §9, e o M1 da terceira auditoria.

    `vazamento-lgpd` e `pesquisa-comprometida` sao *"apenas manifesto, sem
    injects"*, e existem para provar que o loader lida com pacote incompleto.
    Endurecer `ground_truth.yaml` para TODO pack os recusaria.
    """

    def apenas_manifesto(self) -> Path:
        destino = Path(materializa())
        for arquivo in ("injects.yaml", "objectives.yaml", GABARITO):
            (destino / arquivo).unlink()
        return destino

    def test_pacote_apenas_manifesto_CARREGA(self):
        pack = carrega(self.apenas_manifesto())
        self.assertTrue(pack.pack_id)
        self.assertEqual(pack.injects, ())

    def test_ele_nao_tem_predicados_e_isso_NAO_e_defeito(self):
        """Sem gabarito nao ha predicado, e o `or {}` aqui e legitimo.

        O que o B1 tirou foi o `or {}` do caminho do pacote COMPLETO, onde
        ausencia virava vazio e escondia documento faltante. Aqui a ausencia E o
        fato.
        """
        self.assertEqual(carrega(self.apenas_manifesto()).verification_predicates, {})

    def test_O_NEGATIVO_DO_NEGATIVO_a_recusa_nao_dispara_para_apenas_manifesto(self):
        """Sem este caso, `_verify_completude` poderia recusar TUDO e passar.

        Ele e o controle da recusa de incompletude: a mesma funcao que reprova o
        meio-termo tem de deixar passar o apenas-manifesto, e as duas afirmacoes
        juntas sao o que prova que ela discrimina.
        """
        destino = self.apenas_manifesto()
        try:
            carrega(destino)
        except PackError as erro:
            self.fail(
                f"apenas-manifesto foi recusado por `{erro.site}`: {erro}. "
                "`04` §9 o declara forma legitima."
            )

    def test_o_MEIO_TERMO_e_o_que_a_recusa_pega(self):
        """Nem apenas-manifesto nem completo: com injects e sem gabarito.

        E exatamente o estado em que a fixture versionada estava, e que carregava
        limpo antes do B1.
        """
        destino = Path(materializa())
        (destino / GABARITO).unlink()
        with self.assertRaises(PackError) as capturado:
            carrega(destino)

        self.assertEqual(capturado.exception.site, PackSite.INCOMPLETE_PACK)
        self.assertIn(GABARITO, str(capturado.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
