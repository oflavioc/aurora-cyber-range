"""O loader de pack — item 9 da DoD, e os sitios em que o boot recusa.

O QUE ESTA SUITE PROVA
----------------------
Item 9: *"flag nao declarada impede boot do engine com mensagem clara"*, com a
definicao de "clara" que `06_ACCEPTANCE_TESTS.md` T2 da — **a mensagem nomeia a
flag e o arquivo esperado**. Um teste que so afirmasse "levantou excecao"
passaria com uma mensagem que nao permite intervir, que e a distincao entre
deteccao e localizacao que `scripts/check_contract_examples.py` ja registra.

POR QUE CONTRA O ADAPTER REAL, e nao contra flags sinteticas
-------------------------------------------------------------
`tests/test_simulation_state.py` usa flags sinteticas de proposito: o fold e do
`range-core` e nomear `academus.*` ali acoplaria o core a um adapter pelo teste.

Aqui e o contrario, e a diferenca e o que esta sob teste. O loader existe para
conferir PACK CONTRA ADAPTER; com flags inventadas dos dois lados, ele provaria
que casa nomes consigo mesmo. As flags sao lidas de
`domains/academus/flags.yaml` como DADO — do mesmo jeito que o boot faz —, e
nenhum nome de flag aparece literal nesta suite: os nomes vem do arquivo, e o
nome INEXISTENTE e derivado de um existente por sufixo, que e o erro de digitacao
que o item 9 existe para pegar.

FIXTURE COPIADA, NUNCA MUTADA NO LUGAR
--------------------------------------
Cada recusa e provada contra uma copia temporaria do pack com UM defeito
plantado. A arvore nao e tocada — mesma disciplina de
`scripts/check_contract_examples_probes.py`, e pelo mesmo motivo: prova que suja
a arvore e prova que alguem vai desligar.
"""

from __future__ import annotations

import shutil
import tempfile
import sys
import unittest
from pathlib import Path

import yaml

from contracts.generated.events import VPN_ACCESS_REVOKED
from range_core.engine.loader import contract_source
from range_core.engine.loader.canonical import CANONICALIZATION_V1, content_hash_v1
from range_core.engine.loader.pack_loader import (
    AdapterFlags,
    confere_folhas_temporais,
    confere_qualificador_since,
    PackError,
    PackSite,
    load_pack,
)
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "fixtures"))
from pack_completo import materializa  # noqa: E402

#: PACOTE COMPLETO materializado em temporario — B1 da Fase 6.
PACK = materializa()
FLAGS_DO_ADAPTER = Path("domains") / "academus" / "flags.yaml"

CONTRATOS = contract_source.read_contracts()
FLAGS = AdapterFlags.from_document(
    yaml.safe_load((REPO_ROOT / FLAGS_DO_ADAPTER).read_text(encoding="utf-8")),
    source=FLAGS_DO_ADAPTER.as_posix(),
)


def carrega(diretorio: Path = PACK, flags: AdapterFlags = FLAGS):
    return load_pack(diretorio, contracts=CONTRATOS, adapter_flags=flags)


class _ComCopia(unittest.TestCase):
    """Base: copia o pack para diretorio temporario e planta um defeito."""

    def copia(self) -> Path:
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        destino = Path(temporario.name) / "pack"
        shutil.copytree(PACK, destino)
        return destino

    def planta(self, destino: Path, arquivo: str, antes: str, depois: str) -> None:
        """Substitui EXATAMENTE UMA ocorrencia, ou falha alto.

        Casar zero vezes plantaria nada e o teste passaria por engano; casar
        duas plantaria outra coisa. E a mesma guarda de
        `check_contract_examples_probes.py`.
        """
        caminho = destino / arquivo
        texto = caminho.read_text(encoding="utf-8")
        self.assertEqual(
            texto.count(antes), 1, f"a ancora {antes!r} nao casa exatamente uma vez"
        )
        caminho.write_text(texto.replace(antes, depois), encoding="utf-8")

    def recusa(self, destino: Path, site: str) -> PackError:
        with self.assertRaises(PackError) as capturado:
            carrega(destino)
        self.assertEqual(capturado.exception.site, site)
        return capturado.exception


class PackValido(unittest.TestCase):
    """O fixture carrega inteiro. Sem isto, nenhuma recusa abaixo significa nada."""

    def test_carrega_o_pack_minimo(self):
        pack = carrega()
        self.assertEqual(pack.pack_id, "pack-minimo-fase-2")
        self.assertEqual(pack.schema_version, 2)
        self.assertEqual(pack.canonicalization, CANONICALIZATION_V1)
        self.assertEqual(len(pack.injects), 3)

    def test_todo_inject_tem_entrada_em_inject_effects(self):
        """Inclusive o de ruido, que nao move flag nenhuma.

        O fold levanta `INJECT_NOT_IN_PACK` para inject ausente do mapeamento —
        entao "sem effects" precisa ser mapeamento VAZIO, e nao ausencia. Um
        inject de ruido disparado derrubaria a projecao inteira.
        """
        pack = carrega()
        self.assertEqual(
            set(pack.declarations.inject_effects), {i.id for i in pack.injects}
        )
        ruido = [i for i in pack.injects if i.noise]
        self.assertEqual(len(ruido), 1)
        self.assertEqual(dict(pack.declarations.inject_effects[ruido[0].id]), {})

    def test_effects_de_opcao_chegam_por_par_inject_opcao(self):
        pack = carrega()
        com_decisao = [i for i in pack.injects if i.decision_point is not None]
        self.assertEqual(len(com_decisao), 1)
        esperado = {
            (com_decisao[0].id, opcao.id) for opcao in com_decisao[0].decision_point.options
        }
        self.assertEqual(set(pack.declarations.option_effects), esperado)

    def test_flag_defaults_traz_o_adapter_inteiro(self):
        """Estado total: `01` §5.4, e a razao de `SimulationState` nao ter ausencia."""
        pack = carrega()
        self.assertEqual(set(pack.declarations.flag_defaults), set(FLAGS.specs))

    def test_t_relative_vira_segundos(self):
        pack = carrega()
        self.assertEqual(
            [i.t_relative_seconds for i in pack.injects],
            [5 * 60, 20 * 60, 35 * 60],
        )

    def test_o_pino_traz_as_quatro_chaves_que_o_fold_confere(self):
        """As chaves vem do CONSUMIDOR, e a afirmacao tambem.

        Comparar contra uma lista escrita aqui provaria que o loader concorda
        consigo mesmo. As constantes sao importadas de `simulation_state`, que e
        quem as exige: se o fold renomear uma, este teste fica vermelho — que e
        o unico jeito de a divergencia aparecer antes da reconstrucao.
        """
        pack = carrega()
        self.assertEqual(
            pack.pin_payload(),
            {
                PACK_ID: pack.pack_id,
                PACK_SCHEMA_VERSION: pack.schema_version,
                PACK_CONTENT_HASH: pack.content_hash,
                PACK_CANONICALIZATION: CANONICALIZATION_V1,
            },
        )


class ContentHash(_ComCopia):
    """O pino existe para recusar pack editado. Testar so a igualdade nao basta."""

    def test_o_mesmo_conteudo_produz_o_mesmo_hash(self):
        self.assertEqual(carrega().content_hash, carrega(self.copia()).content_hash)

    def test_comentario_e_espaco_NAO_mudam_o_hash(self):
        """A regra v1 reserializa em vez de hashear bytes.

        Recusar um pack por comentario acrescentado seria recusa sem divergencia
        real — e recusa que nao corresponde a diferenca ensina a ignorar recusa.
        """
        destino = self.copia()
        caminho = destino / "manifest.yaml"
        caminho.write_text(
            caminho.read_text(encoding="utf-8") + "\n# comentario acrescentado\n",
            encoding="utf-8",
        )
        self.assertEqual(carrega(destino).content_hash, carrega().content_hash)

    def test_mudanca_de_VALOR_muda_o_hash(self):
        destino = self.copia()
        self.planta(destino, "injects.yaml", 't_relative: "00:05"', 't_relative: "00:06"')
        self.assertNotEqual(carrega(destino).content_hash, carrega().content_hash)

    def test_arquivo_que_o_loader_da_fase_2_NAO_consome_entra_no_hash(self):
        """`branches.yaml` e documento de maquina e muda resolucao na Fase 7.

        Escopo definido pela versao do loader faria o mesmo pack ter hash
        diferente em duas fases, e todo exercicio desta fase deixaria de
        reconstruir na proxima sem que ninguem tocasse no pack. Ver
        `canonical.py`.
        """
        destino = self.copia()
        (destino / "branches.yaml").write_text("branches: []\n", encoding="utf-8")
        self.assertNotEqual(carrega(destino).content_hash, carrega().content_hash)

    def test_o_MESMO_documento_sob_outro_nome_muda_o_hash(self):
        """O caminho e prefixo de cada entrada, e este teste e a razao disso.

        `canonical.py` afirma que sem o prefixo "mover conteudo de um arquivo
        para outro produziria o mesmo hash". A afirmacao vivia so na docstring, e
        a prova negativa mostrou: remover o prefixo nao derrubava nada.

        **A primeira versao deste teste tambem nao derrubava.** Ela trocava DOIS
        documentos de lugar entre `a.yaml` e `b.yaml` — e isso muda o hash mesmo
        sem prefixo, porque a ordem de concatenacao e por caminho e os corpos
        trocam de posicao. O caso que isola o prefixo e UM documento so, sob dois
        nomes: sem prefixo, as duas entradas sao byte a byte iguais.
        """
        documento = {"chave": 1}
        self.assertNotEqual(
            content_hash_v1({"a.yaml": documento}),
            content_hash_v1({"b.yaml": documento}),
        )

    def test_a_ORDEM_das_chaves_no_arquivo_nao_muda_o_hash(self):
        """`sort_keys=True` — reserializar em vez de hashear bytes.

        Recusar um pack porque alguem reordenou duas chaves do manifesto seria
        recusa sem divergencia real. O teste que existia — mesmo conteudo, mesmo
        hash — nao provava isto: os dois lados vinham do MESMO texto YAML, entao
        a ordem de insercao ja era igual e `sort_keys` nao tinha o que fazer.
        """
        self.assertEqual(
            content_hash_v1({"a.yaml": {"x": 1, "y": 2}}),
            content_hash_v1({"a.yaml": {"y": 2, "x": 1}}),
        )

    def test_GM_NOTES_fica_fora_do_hash(self):
        """Narrativa para o facilitador nao alcanca resolucao — `04` §1."""
        destino = self.copia()
        (destino / "GM_NOTES.md").write_text("# notas\n", encoding="utf-8")
        self.assertEqual(carrega(destino).content_hash, carrega().content_hash)


class FlagNaoDeclarada(_ComCopia):
    """ITEM 9 DA DoD. A recusa, o sitio, e as duas metades da mensagem."""

    def flag_inexistente(self) -> tuple[str, str]:
        """`(declarada, inexistente)` — a segunda derivada da primeira por sufixo.

        Nao ha nome de flag literal nesta suite. O nome inexistente e o ERRO DE
        DIGITACAO real: casa com o padrao de flag do adapter, nao esta declarado,
        e em runtime viraria escrita em flag que ninguem le.
        """
        declarada = sorted(carrega().injects[0].effects)[0]
        return declarada, f"{declarada}_inexistente"

    def planta_no_primeiro_inject(self) -> tuple[Path, str]:
        """Troca a flag nos `effects` de A01 — e SO neles.

        A mesma flag aparece nos effects de uma opcao de decisao, com outra
        indentacao. A ancora inclui a indentacao de `effects` de inject
        justamente para que a guarda de "casar uma vez" nao vire tentacao de
        afrouxar para "casar a primeira".
        """
        declarada, inexistente = self.flag_inexistente()
        destino = self.copia()
        self.planta(
            destino,
            "injects.yaml",
            f"\n      {declarada}: true",
            f"\n      {inexistente}: true",
        )
        return destino, inexistente

    def test_impede_o_boot(self):
        destino, _ = self.planta_no_primeiro_inject()
        self.recusa(destino, PackSite.UNDECLARED_FLAG)

    def test_a_mensagem_nomeia_a_flag(self):
        destino, inexistente = self.planta_no_primeiro_inject()
        erro = self.recusa(destino, PackSite.UNDECLARED_FLAG)
        self.assertIn(inexistente, str(erro))

    def test_a_mensagem_nomeia_o_arquivo_esperado(self):
        """T2: *"mensagem nomeando flag E ARQUIVO ESPERADO"*.

        O nucleo nao conhece `domains/`. O caminho vem de `AdapterFlags.source`,
        que quem carregou o adapter declarou — e e por isso que a mensagem pode
        nomea-lo sem que o invariante 1 seja tocado.
        """
        destino, _ = self.planta_no_primeiro_inject()
        erro = self.recusa(destino, PackSite.UNDECLARED_FLAG)
        self.assertIn(FLAGS.source, str(erro))

    def test_vale_para_required_flags_do_manifesto(self):
        """Nao so para `effects`: o manifesto declara as flags de que o pack depende."""
        declarada, inexistente = self.flag_inexistente()
        destino = self.copia()
        self.planta(
            destino, "manifest.yaml", f"  - {declarada}\n", f"  - {inexistente}\n"
        )
        erro = self.recusa(destino, PackSite.UNDECLARED_FLAG)
        self.assertIn(inexistente, str(erro))

    def test_vale_para_effects_de_opcao_de_decisao(self):
        """`effects` de opcao nao vive em inject, e sem esta cobertura a decisao
        poderia escrever flag que ninguem declarou."""
        pack = carrega()
        opcao = pack.injects[1].decision_point.options[1]
        declarada = sorted(opcao.effects)[0]
        destino = self.copia()
        self.planta(
            destino, "injects.yaml", f"            {declarada}: false", f"            {declarada}_inexistente: false"
        )
        self.recusa(destino, PackSite.UNDECLARED_FLAG)


class OutrasRecusas(_ComCopia):
    """Os demais sitios. Cada um com o seu, para o teste afirmar QUAL recusa."""

    def test_sem_manifesto_nao_ha_pack(self):
        destino = self.copia()
        (destino / "manifest.yaml").unlink()
        erro = self.recusa(destino, PackSite.REQUIRED_FILE_MISSING)
        self.assertIn("manifest.yaml", str(erro))

    def test_diretorio_inexistente(self):
        with self.assertRaises(PackError) as capturado:
            carrega(PACK / "nao-existe")
        self.assertEqual(capturado.exception.site, PackSite.PACK_DIR_MISSING)

    def test_yaml_ilegivel_nomeia_o_arquivo(self):
        destino = self.copia()
        (destino / "injects.yaml").write_text("injects: [\n  - id: A01\n", encoding="utf-8")
        erro = self.recusa(destino, PackSite.DOCUMENT_UNREADABLE)
        self.assertIn("injects.yaml", str(erro))

    def test_schema_version_nao_suportada_traz_instrucao(self):
        """Antes da validacao de schema, de proposito: um pack v1 precisa da
        instrucao de migracao, e nao de uma mensagem sobre `const: 2`."""
        destino = self.copia()
        self.planta(destino, "manifest.yaml", "schema_version: 2", "schema_version: 1")
        erro = self.recusa(destino, PackSite.UNSUPPORTED_SCHEMA_VERSION)
        self.assertIn("Fase 7", str(erro))

    def test_engine_velho_demais_para_o_pack(self):
        destino = self.copia()
        self.planta(
            destino, "manifest.yaml", 'min_engine_version: "1.0"', 'min_engine_version: "9.9"'
        )
        self.recusa(destino, PackSite.ENGINE_TOO_OLD)

    def test_documento_invalido_contra_o_schema(self):
        """Inject sem `objectives` e sem `noise: true` — `00` §4."""
        destino = self.copia()
        self.planta(destino, "injects.yaml", "    objectives: [OBJ-01]\n", "")
        erro = self.recusa(destino, PackSite.DOCUMENT_INVALID)
        self.assertIn("injects.yaml", str(erro))

    def test_objetivo_inexistente_e_violacao_de_regra_e_nao_de_flag(self):
        """Discrimina os dois sitios: nem toda violacao `x-aurora` e flag.

        Sem esta afirmacao, `UNDECLARED_FLAG` poderia estar sendo devolvido para
        qualquer violacao, e o teste do item 9 passaria sem provar a
        classificacao.
        """
        destino = self.copia()
        self.planta(destino, "injects.yaml", "objectives: [OBJ-01]\n", "objectives: [OBJ-99]\n")
        erro = self.recusa(destino, PackSite.RULE_VIOLATION)
        self.assertIn("pack_objectives", str(erro))

    def test_objectives_yaml_ausente_recusa_o_pack_como_INCOMPLETO(self):
        """A recusa MUDOU DE SITIO no B1 da Fase 6, e mais cedo e melhor.

        Antes, um pack com `injects.yaml` e sem `objectives.yaml` chegava a
        integridade referencial e era recusado por `RULE_VIOLATION` — o inject
        citava um objetivo que o registro vazio nao tinha. A recusa era certa
        pelo motivo errado: o defeito nao e o inject, e o PACOTE, que se apresenta
        como completo e nao traz o que o contrato exige do completo.

        `required_for_complete_pack` passou a ser lido por codigo, e agora o
        sitio e `INCOMPLETE_PACK`. A mensagem nomeia o DOCUMENTO que falta em vez
        do objetivo que sobrou.
        """
        destino = self.copia()
        (destino / "objectives.yaml").unlink()
        erro = self.recusa(destino, PackSite.INCOMPLETE_PACK)
        self.assertIn("objectives.yaml", str(erro))

    def test_registro_vazio_de_objetivos_continua_sendo_recusa(self):
        """A propriedade que o teste acima media, agora por caminho proprio.

        `build_pack_registries` trata registro vazio como RECUSA e nao como
        permissao. Com `objectives.yaml` PRESENTE e sem o objetivo citado, o pack
        e completo — passa pelo passo novo — e a integridade referencial
        continua sendo quem o pega.
        """
        destino = self.copia()
        (destino / "objectives.yaml").write_text("objectives: {}\n", encoding="utf-8")
        self.recusa(destino, PackSite.DOCUMENT_INVALID)

    def test_t_relative_fora_do_formato(self):
        destino = self.copia()
        self.planta(destino, "injects.yaml", 't_relative: "00:05"', 't_relative: "cinco minutos"')
        erro = self.recusa(destino, PackSite.T_RELATIVE_MALFORMED)
        self.assertIn("HH:MM", str(erro))

    def test_id_de_inject_duplicado(self):
        """`x-aurora-unique` — a regra que o schema nao expressa."""
        destino = self.copia()
        self.planta(destino, "injects.yaml", "  - id: A02", "  - id: A01")
        self.recusa(destino, PackSite.RULE_VIOLATION)

    # -- `04` §2: rubrica ausente OU em versao diferente impede a carga --------
    #
    # As duas metades da mesma frase, uma por teste. Sao a mesma regra por
    # construcao — a versao esta dentro do id —, e por isso a segunda existe:
    # se um dia alguem separar id de versao em dois campos, ela fica vermelha,
    # que e o aviso certo.
    #
    # A prova de que a regra DISPARA esta nas fixtures de
    # `contracts/scenario.schema.v2.yaml`; o que estes dois acrescentam e que o
    # LOADER de producao recusa igual — a §1.4 do checkpoint da Fase 2 existe
    # para que gate e loader nao divirjam, e teste que so exercita o gate nao
    # prova a outra metade.

    def test_rubrica_ausente_da_biblioteca_impede_a_carga(self):
        destino = self.copia()
        self.planta(
            destino, "manifest.yaml", "  - incident_triage.v2", "  - threat_hunting.v1"
        )
        erro = self.recusa(destino, PackSite.RULE_VIOLATION)
        self.assertIn("rubric_library", str(erro))

    def test_rubrica_em_versao_que_a_biblioteca_nao_tem_impede_a_carga(self):
        destino = self.copia()
        self.planta(
            destino, "manifest.yaml", "  - incident_triage.v2", "  - incident_triage.v1"
        )
        erro = self.recusa(destino, PackSite.RULE_VIOLATION)
        self.assertIn("rubric_library", str(erro))


class FolhasTemporais(unittest.TestCase):
    """P6-3 — a gramatica as admite, e o avaliador ainda nao as implementa.

    A recusa muda de INSTANTE: na carga, enquanto da para consertar o pack, e
    nao na avaliacao, no meio do exercicio. E o padrao da guarda de boot do
    emissor, e a mensagem nomeia A FOLHA, como `06` T2 exige da flag.
    """

    def test_folha_before_recusa_a_carga_nomeando_a_folha(self):
        with self.assertRaises(PackError) as capturado:
            confere_folhas_temporais(
                {
                    "verification_predicates": {
                        "containment": {
                            "all": [
                                {"event": VPN_ACCESS_REVOKED},
                                {"before": "T+01:00"},
                            ]
                        }
                    }
                }
            )
        erro = capturado.exception
        self.assertEqual(erro.site, PackSite.TEMPORAL_LEAF_UNSUPPORTED)
        self.assertIn("containment.all[1].before", str(erro))
        self.assertIn("P6-3", str(erro))

    def test_folha_after_aninhada_tambem_e_achada(self):
        with self.assertRaises(PackError):
            confere_folhas_temporais(
                {"verification_predicates": {"x": {"not": {"after": "T+02:00"}}}}
            )

    def test_predicado_sem_folha_temporal_passa(self):
        """Sem o positivo, a recusa acima nao prova que ela discrimina."""
        self.assertIsNone(
            confere_folhas_temporais(
                {"verification_predicates": {"x": {"all": [{"event": "a"}]}}}
            )
        )

    def test_pack_sem_ground_truth_nao_levanta_aqui(self):
        """A ausencia e recusada por `required` do contrato, e nao por esta guarda.

        Duas recusas para o mesmo defeito dariam duas mensagens, e a segunda
        chegaria com o vocabulario errado.
        """
        self.assertIsNone(confere_folhas_temporais(None))


class QualificadorSince(unittest.TestCase):
    """As duas pernas da guarda de `since` — `03` §3.1, spec-change #49.

    A secao define `self` como a UNICA forma de v1, e exige `since: self` no
    predicado de contencao. As duas pernas sao defeitos legitimos e permanentes:
    valor nao definido nao vira semantica por adivinhacao, e contencao sem
    `since` cai no defeito que o #49 corrigiu — o predicado passaria a exigir
    ausencia TOTAL, e o pack que materializa exfiltracao antes da resposta nunca
    verificaria contencao. A correcao da spec nao alcanca quem nao escreve o
    campo; a guarda alcanca.

    NAO HA PERNA PARA `self`: o avaliador o implementa (`verificacao.py`), e
    recusar a forma normativa na carga faria o cenario canonico da propria spec
    deixar de rodar — pior que o defeito que corrigiria.
    """

    CONTENCAO_NORMATIVA = {
        "verification_predicates": {
            "containment": {
                "all": [
                    {"event": VPN_ACCESS_REVOKED},
                    {"absence_of": {"fact_class": "exfiltration", "since": "self"}},
                ]
            },
            "service_restoration": {"all": [{"flag_false": "x"}]},
        }
    }

    def test_valor_nao_definido_recusa_a_carga_nomeando_a_folha_e_o_valor(self):
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(
                {
                    "verification_predicates": {
                        "containment": {
                            "all": [
                                {
                                    "absence_of": {
                                        "fact_class": "exfiltration",
                                        "since": "exercise_start",
                                    }
                                }
                            ]
                        }
                    }
                }
            )
        erro = capturado.exception
        self.assertEqual(erro.site, PackSite.SINCE_UNDEFINED_VALUE)
        self.assertIn("containment.all[0].absence_of", str(erro))
        self.assertIn("exercise_start", str(erro))
        self.assertIn("self", str(erro))

    def test_contencao_com_absence_of_sem_since_recusa(self):
        """A forma normativa da §3.1 exige o campo; sem ele, ausencia TOTAL."""
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(
                {
                    "verification_predicates": {
                        "containment": {
                            "all": [{"absence_of": {"fact_class": "exfiltration"}}]
                        }
                    }
                }
            )
        erro = capturado.exception
        self.assertEqual(erro.site, PackSite.CONTAINMENT_ABSENCE_WITHOUT_SINCE)
        self.assertIn("containment.all[0].absence_of", str(erro))
        self.assertIn("since: self", str(erro))

    def test_a_forma_CURTA_em_string_na_contencao_tambem_recusa(self):
        """Sem esta direcao, a forma curta e o desvio: ela nao carrega `since`.

        `absence_of: exfiltration` valida no contrato (`predicate_absence_of`
        admite string), e a exigencia da §3.1 seria contornavel por escrita.
        """
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(
                {
                    "verification_predicates": {
                        "containment": {"all": [{"absence_of": "exfiltration"}]}
                    }
                }
            )
        self.assertEqual(
            capturado.exception.site, PackSite.CONTAINMENT_ABSENCE_WITHOUT_SINCE
        )

    def test_fora_da_contencao_a_ausencia_TOTAL_continua_legitima(self):
        """`03` §3.1: a forma sem `since` e legitima para outros usos.

        Sem este positivo, a perna acima nao prova que ela discrimina — provaria
        so que a guarda reprova todo `absence_of`.
        """
        self.assertIsNone(
            confere_qualificador_since(
                {
                    "verification_predicates": {
                        "containment": {"all": [{"event": VPN_ACCESS_REVOKED}]},
                        "service_restoration": {
                            "all": [{"absence_of": {"fact_class": "data_loss"}}]
                        },
                    }
                }
            )
        )

    def test_a_forma_NORMATIVA_passa(self):
        """O controle positivo: o predicado que a §3.1 escreve carrega."""
        self.assertIsNone(confere_qualificador_since(self.CONTENCAO_NORMATIVA))

    def test_valor_nao_definido_FORA_da_contencao_tambem_recusa(self):
        """`self` e a unica forma definida em v1 — a regra e da folha, nao da chave."""
        with self.assertRaises(PackError) as capturado:
            confere_qualificador_since(
                {
                    "verification_predicates": {
                        "service_restoration": {
                            "not": {
                                "absence_of": {
                                    "fact_class": "data_loss",
                                    "since": "T+01:00",
                                }
                            }
                        }
                    }
                }
            )
        self.assertEqual(capturado.exception.site, PackSite.SINCE_UNDEFINED_VALUE)
        self.assertIn("service_restoration.not.absence_of", str(capturado.exception))

    def test_pack_sem_ground_truth_nao_levanta_aqui(self):
        self.assertIsNone(confere_qualificador_since(None))


class DoisParsers(unittest.TestCase):
    """PyYAML e `tools/_common.py::parse_yaml` leem os contratos igual.

    O loader passou a ler `contracts/` com PyYAML, enquanto o gate de CI os le
    com o parser estrito de `tools/`. Dois parsers sobre o mesmo artefato e risco
    de divergencia real: o gate aprovaria uma arvore que o loader le de outro
    jeito, e nada acusaria.

    Fecha tambem, por consequencia, um limite que `fase_1.md` §7.4 declarou sem
    verificar: `parse_yaml` nunca tinha sido comparado com parser conforme.

    O teste vive em `tests/` — e nao no nucleo — porque importa de `tools/`, e o
    nucleo nao pode.
    """

    def test_todo_contrato_e_lido_igual_pelos_dois_parsers(self):
        import sys

        sys.path.insert(0, str(REPO_ROOT / "tools"))
        from _common import parse_yaml  # noqa: E402

        caminhos = sorted((REPO_ROOT / "contracts").glob("*.yaml"))
        # O nome e a asercao carregavam o numero SEIS, e ele envelheceu na Fase 6
        # com `rubrics.schema.yaml`. Contagem inscrita e afirmacao de estado que
        # so o proprio teste verifica — mesma classe do "32 tipos" de
        # `contract_rules.py`. O que importa e que HAJA contrato e que os dois
        # parsers concordem sobre TODOS; o numero e do `glob`.
        self.assertGreater(len(caminhos), 0)
        for caminho in caminhos:
            with self.subTest(contrato=caminho.name):
                self.assertEqual(
                    yaml.safe_load(caminho.read_text(encoding="utf-8")),
                    parse_yaml(caminho),
                )


if __name__ == "__main__":
    unittest.main()
