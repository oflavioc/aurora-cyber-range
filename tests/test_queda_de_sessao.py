"""A P3-10 e a P3-11 — a queda de sessao sem memoria, e a guarda de boot.

O QUE A P3-10 ERA
------------------
`proporcional` era uma **cota acumulada** na instancia do `Degradador`,
chaveada por `(rota, flag)`. Duas consequencias, e a segunda e a que ninguem
veria:

1. **reinicio zera a cota** — estado mutavel fora das cinco camadas de `01` §4;
2. **rollback devolve a flag e nao devolve o acumulador** — o facilitador
   rebobina, a taxa volta ao valor anterior, e o conjunto de quem esta fora do ar
   passa a ser OUTRO. Nada fica vermelho. A sala vive um exercicio diferente do
   que o facilitador restaurou, e ninguem tem como perceber.

A D9 decidiu **eliminar** o estado, e nao realoca-lo. As tres propriedades sao
medidas aqui, e nenhuma delas e argumento:

    estavel no reinicio    processo NOVO, mesmo conjunto
    estavel no rollback    a taxa volta, e EXATAMENTE as mesmas sessoes voltam
    monotona na taxa       subir a taxa so acrescenta; nunca troca o conjunto

A SEGUNDA E MEDIDA COM ROLLBACK DE VERDADE
--------------------------------------------
`ROLLBACK_PERFORMED` no store real, ancorado num evento real, com o fold de
verdade recalculando as flags. Um teste que apenas escrevesse a taxa de volta
com um `set` provaria a aritmetica e mais nada: a cota acumulada tambem daria a
taxa certa depois disso — o que ela nao daria e o mesmo CONJUNTO, e conjunto so
aparece com sujeitos suficientes.

POR QUE A `secretaria` E NAO O PROFESSOR
------------------------------------------
A rota do diario declara `escopo: professor: titular`, e so `P-3001` e titular
de `T-2001`: com professores, todo sujeito que nao fosse ele receberia 404 e o
conjunto teria um elemento. A `secretaria` nao tem regra de escopo — le qualquer
turma —, entao cada `sub` distinto e uma sessao distinta, que e o que a flag
descreve.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from dataclasses import fields
from datetime import datetime
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from contracts.generated.events import (
    EXERCISE_STARTED,
    INJECT_FIRED,
    ROLLBACK_PERFORMED,
)
from domains.academus.api.app import montar
from domains.academus.api.auth import Autenticacao
from domains.academus.api.degradacao import (
    ESPACO,
    Degradador,
    FlagNaoDeclarada,
    LeituraDeEstado,
    cai,
    confere_flags_declaradas,
    fracao_do_sujeito,
)
from domains.academus.api.surface import Degradacao, RotaDeclarada, Superficie, carregar
from domains.academus.generated.flags import ACADEMUS_LMS_SESSION_DROP_RATE
from range_core.clock.exercise_clock import ExerciseClock
from range_core.engine.loader.pack_loader import AdapterFlags
from range_core.events.envelope import Correlation
from range_core.events.store import EventDraft, InMemoryEventStore
from range_core.state.cache import InMemoryProjectionCache
from range_core.state.simulation_state import (
    PACK_CANONICALIZATION,
    PACK_CONTENT_HASH,
    PACK_ID,
    PACK_SCHEMA_VERSION,
    TO_EVENT_ID,
    Declarations,
)

from _academus_app import emissor_de_teste
from _academus_banco import exige_banco, repositorio_limpo

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAGS_YAML = REPO_ROOT / "domains" / "academus" / "flags.yaml"
CALCULADOR = REPO_ROOT / "tests" / "_queda_de_sessao_em_outro_processo.py"

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"
SEED = 20260816

ROTA = "/classes/{class_id}/gradebook"
FLAG = ACADEMUS_LMS_SESSION_DROP_RATE

#: SUJEITOS SUFICIENTES PARA HAVER CONJUNTO. Com poucos, a fracao observada e
#: granulada pelo tamanho — e nao ha como distinguir "a taxa esta errada" de "o
#: conjunto e pequeno demais para mostrar a taxa".
MUITOS = tuple(f"S-{n:04d}" for n in range(1000))

#: O subconjunto que passa pelo HTTP. Mil requisicoes por assercao pagariam o
#: preco de mil idas ao stack ASGI para provar o que a funcao pura ja prova; o
#: que o caminho HTTP acrescenta e o WIRING, e 60 sujeitos ja fazem conjunto.
ALGUNS = MUITOS[:60]


def _derruba(taxa: float, sujeitos=MUITOS) -> set[str]:
    return {s for s in sujeitos if cai(SEED, ROTA, FLAG, s, taxa)}


class PropriedadesDaFuncao(unittest.TestCase):
    """As tres propriedades da D9 sobre a funcao pura. Sem HTTP e sem banco."""

    def test_MONOTONA_subir_a_taxa_so_acrescenta(self):
        """Nunca TROCA o conjunto — e o "nunca" e o que precisa de assercao.

        Uma implementacao por sorteio daria a fracao certa em cada taxa e
        trocaria quem cai a cada mudanca. O facilitador que sobe a taxa de 0,4
        para 0,6 veria participantes voltando ao ar enquanto o painel piora, e
        leria isso como o sistema se recuperando sozinho.
        """
        anterior: set[str] = set()
        for taxa in (0.0, 0.1, 0.25, 0.4, 0.6, 0.8, 1.0):
            with self.subTest(taxa=taxa):
                atual = _derruba(taxa)
                self.assertTrue(
                    anterior <= atual,
                    f"taxa {taxa} POUPOU {len(anterior - atual)} sessoes que a taxa "
                    "anterior derrubava: o conjunto trocou em vez de crescer",
                )
                anterior = atual

    def test_a_FRACAO_observada_segue_a_taxa(self):
        """A monotonicidade sozinha passaria com "derruba sempre" a partir de 0.

        Este e o par dela: o conjunto cresce, e cresce PARA a taxa declarada.
        """
        for taxa in (0.1, 0.25, 0.5, 0.75, 0.9):
            with self.subTest(taxa=taxa):
                observada = len(_derruba(taxa)) / len(MUITOS)
                self.assertAlmostEqual(
                    observada,
                    taxa,
                    delta=0.05,
                    msg=f"taxa declarada {taxa}, fracao observada {observada}",
                )

    def test_os_extremos_sao_exatos_e_nao_aproximados(self):
        """Zero e um nao admitem tolerancia: sao o mundo normal e o apagao."""
        self.assertEqual(_derruba(0.0), set())
        self.assertEqual(_derruba(1.0), set(MUITOS))

    def test_ESTAVEL_NO_REINICIO_processo_novo_produz_o_mesmo_conjunto(self):
        """A propriedade que `hash()` quebraria, e so entre processos.

        O filho nasce com outra salga de `PYTHONHASHSEED`. Uma derivacao por
        `hash()` seria estavel dentro de um processo e daria outro conjunto a
        cada boot do container — verde aqui se o teste fosse no mesmo
        interpretador, e errado na sala.
        """
        aqui = sorted(_derruba(0.4, ALGUNS))

        saida = subprocess.run(
            [sys.executable, str(CALCULADOR), str(SEED), ROTA, FLAG, "0.4", *ALGUNS],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(REPO_ROOT),
        )
        la = sorted(json.loads(saida.stdout))

        self.assertEqual(aqui, la)
        # O PAR QUE DISCRIMINA: um filho que devolvesse lista vazia — ou tudo —
        # casaria com um `aqui` degenerado sem que nada acusasse.
        self.assertTrue(0 < len(la) < len(ALGUNS))

    def test_flags_e_rotas_diferentes_nao_derrubam_o_MESMO_conjunto(self):
        """Dois fenomenos, dois conjuntos.

        Se a flag nao entrasse na derivacao, ligar a segunda flag proporcional de
        uma rota nao atingiria ninguem novo — e o facilitador leria isso como a
        flag nao funcionando. O mesmo vale para a rota: duas rotas degradadas na
        mesma taxa derrubariam exatamente as mesmas pessoas.
        """
        outra_flag = FLAG + "-de-mentira"
        por_flag = {s for s in ALGUNS if cai(SEED, ROTA, outra_flag, s, 0.5)}
        por_rota = {s for s in ALGUNS if cai(SEED, "/outra/rota", FLAG, s, 0.5)}
        base = _derruba(0.5, ALGUNS)

        self.assertNotEqual(base, por_flag)
        self.assertNotEqual(base, por_rota)

    def test_a_fracao_esta_no_intervalo_semiaberto(self):
        """`[0, 1)` — e o `1` aberto e o que faz `taxa=1` derrubar TODO mundo.

        Com a fracao podendo valer exatamente 1, o sujeito no topo sobreviveria a
        um apagao declarado como total, e a diferenca so apareceria no dia em que
        alguem ligasse a flag no maximo.
        """
        valores = [fracao_do_sujeito(SEED, ROTA, FLAG, s) for s in ALGUNS]
        self.assertTrue(all(0.0 <= v < 1.0 for v in valores))
        self.assertEqual(ESPACO, 2**64)

    def test_o_DEGRADADOR_nao_tem_mais_campo_mutavel(self):
        """A metade estrutural da P3-10: o material do defeito saiu.

        O teste de comportamento prova a propriedade hoje; este nomeia a causa.
        Um acumulador que voltasse apareceria como "ha um campo novo aqui", e nao
        como um conjunto de sessoes estranho tres testes adiante.
        """
        self.assertEqual(
            {campo.name for campo in fields(Degradador)},
            {"leitura", "seed", "dormir"},
        )


def _declaracoes(taxas: dict[str, float], sem: str | None = None) -> Declarations:
    """As flags do adapter, lidas do arquivo. `sem` remove uma — para a P3-11."""
    flags = AdapterFlags.from_document(
        yaml.safe_load(FLAGS_YAML.read_text(encoding="utf-8")),
        source=str(FLAGS_YAML),
    )
    defaults = dict(flags.defaults)
    if sem is not None:
        del defaults[sem]
    return Declarations(
        pack_id="pack-de-teste",
        schema_version=2,
        content_hash="0" * 64,
        canonicalization="v1",
        flag_defaults=defaults,
        inject_effects={nome: {FLAG: taxa} for nome, taxa in taxas.items()},
        option_effects={},
    )


@exige_banco
class EstavelNoRollback(unittest.TestCase):
    """A propriedade que um acumulador quebra em silencio, com rollback de verdade."""

    def setUp(self) -> None:
        parede = iter(range(1_000_000, 1_100_000))
        relogio = ExerciseClock(
            datetime(2026, 8, 17, 9, 0, 0), now=lambda: float(next(parede))
        )
        self.store = InMemoryEventStore(relogio)
        self.store.append(
            EventDraft(
                event_type=EXERCISE_STARTED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste"),
                payload={
                    PACK_ID: "pack-de-teste",
                    PACK_SCHEMA_VERSION: 2,
                    PACK_CONTENT_HASH: "0" * 64,
                    PACK_CANONICALIZATION: "v1",
                },
            )
        )
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.cliente = TestClient(
            montar(
                self.autenticacao,
                repositorio_limpo(),
                Degradador(
                    leitura=LeituraDeEstado(
                        store=self.store,
                        declarations=_declaracoes({"TAXA_04": 0.4, "TAXA_06": 0.6}),
                        cache=InMemoryProjectionCache(),
                    ),
                    seed=SEED,
                ),
                emissor_de_teste(),
            )
        )

    def _dispara(self, inject_id: str):
        return self.store.append(
            EventDraft(
                event_type=INJECT_FIRED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste", inject_id=inject_id),
            )
        )

    def _caidos(self, sujeitos=ALGUNS) -> set[str]:
        """Quem recebe 503 na rota do diario. UMA requisicao por sujeito."""
        caidos = set()
        for sub in sujeitos:
            cabecalho = {
                "Authorization": f"Bearer {self.autenticacao.emitir_token(sub, 'secretaria')}"
            }
            resposta = self.cliente.get("/classes/T-2001/gradebook", headers=cabecalho)
            if resposta.status_code == 503:
                caidos.add(sub)
        return caidos

    def test_rebobinar_devolve_EXATAMENTE_as_mesmas_sessoes(self):
        """O caso central da P3-10, e a razao de ele ser medido por HTTP.

        A cota acumulada passaria numa versao deste teste que so olhasse a
        QUANTIDADE: depois do rollback ela voltaria a derrubar a mesma fracao. O
        que ela nao devolveria e o mesmo CONJUNTO — o acumulador continuaria de
        onde parou, e o corte cairia sobre outras pessoas.
        """
        ancora = self._dispara("TAXA_04")
        antes = self._caidos()

        self._dispara("TAXA_06")
        depois = self._caidos()

        # SEM ESTA METADE o teste passaria com uma API que nunca degrada: o
        # conjunto vazio "volta" ao conjunto vazio perfeitamente.
        self.assertTrue(antes < depois, "subir a taxa nao acrescentou ninguem")

        self.store.append(
            EventDraft(
                event_type=ROLLBACK_PERFORMED,
                truth_layer="facilitation",
                producer="inject-engine",
                correlation=Correlation(scenario_id="pack-de-teste"),
                payload={TO_EVENT_ID: ancora.event_id, "reason": "facilitation"},
            )
        )

        self.assertEqual(
            self._caidos(),
            antes,
            "o rollback devolveu a taxa e NAO devolveu as mesmas sessoes: e o "
            "acumulador da P3-10 de volta, e ninguem na sala perceberia",
        )

    def test_a_ordem_das_requisicoes_nao_muda_quem_cai(self):
        """Sem memoria, nao ha dependencia de ordem — e isso e verificavel.

        A cota acumulada dependia da ordem por construcao: quem chegasse na
        requisicao certa caia. Aqui a mesma pergunta feita de tras para frente
        tem a mesma resposta.
        """
        self._dispara("TAXA_06")
        direto = self._caidos()
        invertido = self._caidos(tuple(reversed(ALGUNS)))

        self.assertEqual(direto, invertido)
        self.assertTrue(0 < len(direto) < len(ALGUNS))


def _rota(**kwargs) -> RotaDeclarada:
    base = dict(
        method="GET",
        path="/x",
        papeis=frozenset({"secretaria"}),
        publica=False,
        flags=(),
        degradacao=(),
        escopo={},
    )
    base.update(kwargs)
    return RotaDeclarada(**base)  # type: ignore[arg-type]


def _superficie(rota: RotaDeclarada) -> Superficie:
    return Superficie(
        papeis_de_dominio=frozenset({"secretaria"}),
        claims=("sub", "role", "exp"),
        rotas={(rota.method, rota.path): rota},
    )


class GuardaDeBoot(unittest.TestCase):
    """A P3-11 — flag citada e ausente do estado vira no-op silencioso.

    `estado.flags.get(nome)` devolvia `None`, e entao `ligada` nunca disparava e
    `proporcional` lia `0.0`. **A rota nao degradava, e nada avisava.** O gate do
    CI protege o repositorio; isto protege o exercicio em curso, que e outra
    coisa — a divergencia pode nascer do PACK carregado, e nao do commit.

    A forma e a que `06` T2 ja exige do loader do engine: *"flag nao declarada
    impede boot, com mensagem nomeando flag e arquivo esperado"*.
    """

    def test_o_PAR_a_arvore_de_hoje_NAO_e_recusada(self):
        """A metade sem a qual a outra nao vale nada.

        Uma guarda que sempre recusasse passaria no teste de recusa. Este afirma
        que a superficie real, contra as flags reais, **sobe** — e ele usa os dois
        arquivos de verdade, e nao uma fixture que os imite.
        """
        confere_flags_declaradas(carregar(), _declaracoes({}))

    def test_flag_CITADA_e_ausente_do_estado_recusa_o_boot(self):
        """A direcao decidivel hoje. A simetrica e a P4-4, e tem dono na Fase 8."""
        with self.assertRaises(FlagNaoDeclarada) as erro:
            confere_flags_declaradas(carregar(), _declaracoes({}, sem=FLAG))

        mensagem = str(erro.exception)
        self.assertIn(FLAG, mensagem)
        # O ARQUIVO, e nao so a flag: `06` T2 pede os dois, e quem le a recusa
        # precisa saber onde escrever a declaracao que falta.
        self.assertIn("flags.yaml", mensagem)
        self.assertIn(ROTA, mensagem)

    def test_a_lista_flags_e_lida_e_nao_so_as_entradas_de_degradacao(self):
        """As duas chaves, e nao so a segunda.

        Elas sao conjuntos iguais por gate, mas a guarda de RUNTIME nao pode
        depender do gate: `flags` sem `degradacao` chegaria por um pack, e nao
        por um commit — e ai o CI nunca viu o arquivo.
        """
        rota = _rota(flags=(FLAG,))
        with self.assertRaises(FlagNaoDeclarada) as erro:
            confere_flags_declaradas(_superficie(rota), _declaracoes({}, sem=FLAG))
        self.assertIn(FLAG, str(erro.exception))

    def test_rota_PUBLICA_com_proporcional_recusa_o_boot(self):
        """A segunda condicao, e ela nao e a primeira dita de outro jeito.

        A flag existe, esta declarada, e mesmo assim a queda nunca aconteceria:
        o sujeito vem do `sub` do token, e rota publica nao tem token. Em tempo
        de requisicao isso apareceria como "ninguem cai", que e indistinguivel de
        taxa zero — entao so o boot pode decidir.
        """
        rota = _rota(
            publica=True,
            papeis=frozenset(),
            flags=(FLAG,),
            degradacao=(
                Degradacao(
                    flag=FLAG,
                    condicao="proporcional",
                    efeito="recusa",
                    status=503,
                    mensagem="Sua sessao foi encerrada.",
                    segundos=0.0,
                ),
            ),
        )
        with self.assertRaises(FlagNaoDeclarada) as erro:
            confere_flags_declaradas(_superficie(rota), _declaracoes({}))
        self.assertIn("publica", str(erro.exception))

    def test_rota_publica_com_LIGADA_nao_recusa(self):
        """O par da anterior: `ligada` nao precisa de sujeito, entao ela pode.

        Sem esta metade, a regra seria "publica nao degrada", que e mais forte do
        que o problema justifica e proibiria uma degradacao legitima.
        """
        rota = _rota(
            publica=True,
            papeis=frozenset(),
            flags=(FLAG,),
            degradacao=(
                Degradacao(
                    flag=FLAG,
                    condicao="ligada",
                    efeito="latencia",
                    status=None,
                    mensagem="",
                    segundos=1.0,
                ),
            ),
        )
        confere_flags_declaradas(_superficie(rota), _declaracoes({}))


@exige_banco
class AGuardaRodaNoBoot(unittest.TestCase):
    """Nao basta a funcao existir: `montar` tem de chama-la. E a §7.3 outra vez."""

    def setUp(self) -> None:
        self.autenticacao = Autenticacao(superficie=carregar(), segredo=SEGREDO)
        self.repositorio = repositorio_limpo()

    def _degradador(self, declaracoes: Declarations) -> Degradador:
        return Degradador(
            leitura=LeituraDeEstado(
                store=InMemoryEventStore(ExerciseClock(datetime(2026, 8, 17, 9, 0, 0))),
                declarations=declaracoes,
                cache=InMemoryProjectionCache(),
            ),
            seed=SEED,
        )

    def test_montar_com_flag_ausente_RECUSA(self):
        with self.assertRaises(FlagNaoDeclarada):
            montar(
                self.autenticacao,
                self.repositorio,
                self._degradador(_declaracoes({}, sem=FLAG)),
                emissor_de_teste(),
            )

    def test_montar_com_a_arvore_de_hoje_SOBE(self):
        self.assertIsNotNone(
            montar(
                self.autenticacao,
                self.repositorio,
                self._degradador(_declaracoes({})),
                emissor_de_teste(),
            )
        )

    def test_SEM_degradador_a_guarda_nao_roda(self):
        """Sem degradador nenhuma flag e lida, entao nao ha no-op a impedir.

        A guarda existe para que *"a rota nao degrada e nada avisa"* deixe de
        acontecer. Uma API que nao degrada por DECLARACAO — `montar` sem
        degradador — nao esta nesse caso, e recusar ali seria exigir declaracao
        de flag de quem nao consulta flag nenhuma.
        """
        self.assertIsNotNone(
            montar(self.autenticacao, self.repositorio, None, emissor_de_teste())
        )


if __name__ == "__main__":
    unittest.main()
