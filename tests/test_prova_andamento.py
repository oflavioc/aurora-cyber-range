"""Gate do item 1 da DoD da Fase 8 (T805): o Modo "Prova em andamento" perde
sessoes conforme `academus.lms_session_drop_rate`, **por minuto de exercicio**.

O QUE ESTE GATE COBRA, E O QUE ELE NAO E
-----------------------------------------
A P4-6 (`degradacao.py:72-77`) registrou a divergencia: `fracao_do_sujeito`/`cai`
derrubam quem cai o exercicio INTEIRO, de uma vez; o `effect_ui` da flag termina
em *"por minuto"*, que aquela funcao **nao implementa**. O consumidor que da
sentido a cadencia e o Modo "Prova em andamento" de `07` Fase 8, e a T810
(data-engineer) vai escreve-lo em `domains/academus/api/prova_andamento.py` —
que NAO existe ainda. Por isso este arquivo esta RED: o import do modulo alvo
falha (`_modulo()`), e toda a suite de propriedades erra. Esse e o red exigido
por R3 §4, e ele e commitado.

A CADENCIA QUE ESTE ORACULO FIXA (o alvo preciso da T810)
---------------------------------------------------------
`taxa` e a fracao de sessoes AINDA VIVAS que cai a cada minuto de exercicio.
Cumulativamente, ate o minuto `m`, a fracao derrubada e um MODELO DE SOBREVIVENCIA:

    corte(taxa, m) = 1 - (1 - taxa) ** m       para 0 < taxa < 1, m >= 1

com os limites `corte = 0` no minuto 0 (o exercicio comeca sem ninguem fora do
ar) e `corte = 1` a partir do minuto 1 quando `taxa = 1` (apagao total). Uma
sessao esta derrubada no minuto `m` sse a sua posicao fixa cai abaixo do corte:

    fracao_do_sujeito(seed, rota, flag, sujeito) < corte(taxa, m)

Isto REUSA `fracao_do_sujeito` (existente e ja testada em `test_queda_de_sessao`)
como base determinista, em vez de duplicar a derivacao — a cadencia so move o
CORTE ao longo do tempo. As propriedades caem por construcao e sao medidas:

    monotona no tempo    o corte cresce com o minuto => o conjunto so acrescenta
    monotona na taxa     o corte cresce com a taxa   => idem
    determinista         funcao pura de (seed, rota, flag, sujeitos, taxa, minuto)
    estavel no reinicio  derive_seed (SHA-256), nunca hash() nem relogio de parede
    frame TOTAL          descreve TODAS as sessoes (alive/dropped), nao um delta

O ORACULO E INDEPENDENTE DA IMPLEMENTACAO
------------------------------------------
As propriedades (monotonia no tempo/taxa, fronteiras, frame total, sensibilidade
a entrada, estabilidade entre processos) sao invariantes checados sobre a SAIDA
do modulo, nao sobre a formula. Alem delas, `test_conjunto_EXATO_bate_com_o_oraculo`
fixa a semantica exata comparando com `_oracle`, escrito aqui — para a T810 ter
alvo preciso. A matriz gate<->mutante (classe `MatrizDeMutantes`) prova, sem
depender do modulo alvo, que cada assercao central MATA o mutante correspondente.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from domains.academus.api.degradacao import fracao_do_sujeito
from domains.academus.generated.flags import ACADEMUS_LMS_SESSION_DROP_RATE

REPO_ROOT = Path(__file__).resolve().parent.parent
CALCULADOR = REPO_ROOT / "tests" / "_prova_andamento_em_outro_processo.py"

SEED = 20260914
ROTA = "/exam/session-status"
FLAG = ACADEMUS_LMS_SESSION_DROP_RATE

#: SUJEITOS SUFICIENTES PARA HAVER CONJUNTO. Com poucos, a fracao observada e
#: granulada pelo tamanho — e nao ha como distinguir "a cadencia esta errada" de
#: "o conjunto e pequeno demais para mostrar a fracao". Mesma licao de
#: `test_queda_de_sessao`.
MUITOS = tuple(f"S-{n:04d}" for n in range(1000))

#: O subconjunto para o caminho por subprocess: um processo novo por assercao ja
#: prova a estabilidade entre processos, e 60 sujeitos ja fazem conjunto.
ALGUNS = MUITOS[:60]

MINUTOS = (0, 1, 2, 5, 10, 20, 45, 90)

#: O vocabulario do frame. Local de proposito: a matriz de mutantes precisa
#: rodar sem o modulo alvo (que ainda nao existe), e um teste real confere que o
#: modulo exporta exatamente estes literais.
ESTADOS_VALIDOS = frozenset({"alive", "dropped"})


def _modulo():
    """O modulo alvo da T810 — importado TARDE, para o red ser localizado.

    Enquanto `prova_andamento.py` nao existe, isto levanta `ModuleNotFoundError`
    e as classes de propriedade erram no `setUp` — o red de R3 §4. A matriz de
    mutantes nao chama isto, entao ela roda e mata os mutantes desde ja.
    """
    return importlib.import_module("domains.academus.api.prova_andamento")


# --------------------------------------------------------------------------- #
# ORACULO — a semantica exata da cadencia, escrita aqui (alvo da T810).
# --------------------------------------------------------------------------- #
def _corte_cumulativo(taxa: float, minuto: int) -> float:
    """Fracao cumulativa derrubada ate `minuto` — modelo de sobrevivencia.

    Monotona no minuto e na taxa por construcao; 0 no minuto 0; teto 1 em
    taxa 1 a partir do minuto 1.
    """
    if minuto <= 0:
        return 0.0
    if taxa <= 0.0:
        return 0.0
    if taxa >= 1.0:
        return 1.0
    return 1.0 - (1.0 - taxa) ** minuto


def _oracle(seed: int, rota: str, flag: str, sujeitos, taxa: float, minuto: int) -> set:
    corte = _corte_cumulativo(taxa, minuto)
    return {s for s in sujeitos if fracao_do_sujeito(seed, rota, flag, s) < corte}


# --------------------------------------------------------------------------- #
# CHECADORES DE PROPRIEDADE — levantam Assertionova ao serem violados. Usados
# pelos testes reais (nao devem levantar) E pela matriz de mutantes (devem).
# `raise AssertionError` explicito, nunca `assert` (imune a `python -O`).
# --------------------------------------------------------------------------- #
class PropriedadeViolada(AssertionError):
    """Uma propriedade central da cadencia foi quebrada. O mutante morre aqui."""


def _exige_monotona_no_tempo(derr, minutos) -> None:
    """`derr(minuto) -> set`. O conjunto do minuto N contem o de N-1."""
    anterior: set = set()
    for m in minutos:
        atual = derr(m)
        ressuscitadas = anterior - atual
        if ressuscitadas:
            raise PropriedadeViolada(
                f"minuto {m} ressuscitou {len(ressuscitadas)} sessoes ja caidas: "
                "a cadencia trocou o conjunto em vez de acrescentar"
            )
        anterior = atual


def _exige_monotona_na_taxa(derr, taxas) -> None:
    """`derr(taxa) -> set`. Taxa maior derruba ao menos tantas quanto a menor."""
    anterior: set = set()
    for taxa in taxas:
        atual = derr(taxa)
        poupadas = anterior - atual
        if poupadas:
            raise PropriedadeViolada(
                f"taxa {taxa} poupou {len(poupadas)} sessoes que a taxa menor "
                "derrubava: o conjunto trocou em vez de crescer"
            )
        anterior = atual


def _exige_frame_total(frame_dict, sujeitos) -> None:
    """O frame descreve TODAS as sessoes, com estado do vocabulario fechado."""
    chaves = set(frame_dict)
    esperado = set(sujeitos)
    if chaves != esperado:
        raise PropriedadeViolada(
            f"frame NAO e total: faltam {len(esperado - chaves)} sessoes, "
            f"sobram {len(chaves - esperado)} — parece um delta, nao o frame"
        )
    invalidos = {s: e for s, e in frame_dict.items() if e not in ESTADOS_VALIDOS}
    if invalidos:
        raise PropriedadeViolada(f"estados fora do vocabulario: {invalidos}")


def _exige_sensivel_a_entrada(derr, chaves) -> None:
    """`derr(chave) -> set`. Entradas diferentes => conjuntos diferentes.

    A licao de `dataset.py`: uma implementacao que ignora a entrada e
    determinista, monotona e do tamanho certo — e mesmo assim errada.
    """
    conjuntos = {chave: frozenset(derr(chave)) for chave in chaves}
    if len(set(conjuntos.values())) == 1:
        raise PropriedadeViolada(
            "conjuntos IDENTICOS para entradas diferentes: a implementacao "
            "ignora a entrada e passaria sem derivar de nada"
        )


# --------------------------------------------------------------------------- #
# TESTES REAIS — contra o modulo alvo. RED ate a T810 existir.
# --------------------------------------------------------------------------- #
class PropriedadesDaCadencia(unittest.TestCase):
    """As propriedades da cadencia por minuto, medidas sobre a saida do modulo."""

    def setUp(self) -> None:
        self.mod = _modulo()

    def _derr(self, taxa: float, minuto: int, sujeitos=MUITOS) -> set:
        return set(self.mod.derrubadas(SEED, ROTA, FLAG, sujeitos, taxa, minuto))

    def test_o_vocabulario_do_frame_e_alive_dropped(self):
        """Vocabulario FECHADO — o `_exige_frame_total` depende destes literais."""
        self.assertEqual(self.mod.ALIVE, "alive")
        self.assertEqual(self.mod.DROPPED, "dropped")

    def test_MONOTONA_no_tempo_o_minuto_N_contem_o_N_menos_1(self):
        """A propriedade CENTRAL da cadencia: quem caiu nao ressuscita.

        Uma implementacao que re-sorteia a cada minuto daria a fracao certa e
        trocaria quem esta fora do ar — a sala veria participantes voltando
        enquanto o painel piora, e leria isso como recuperacao espontanea.
        """
        _exige_monotona_no_tempo(lambda m: self._derr(0.3, m), MINUTOS)

    def test_o_conjunto_CRESCE_de_fato_com_o_minuto(self):
        """Par da monotonia: "derruba tudo sempre" tambem seria monotono.

        Para taxa intermediaria, um minuto tardio derruba ESTRITAMENTE mais que
        um cedo, e ainda ha sobreviventes — nem tudo cai no minuto 1 nem sobra
        tudo no minuto tardio.

        A JANELA E ANCORADA NO PROPRIO CONJUNTO, nao numa constante magica: o
        corte tardio precisa ficar abaixo do maior `fracao_do_sujeito` do
        conjunto (com folga) para que EXISTAM sobreviventes neste seed. A versao
        anterior fixava minuto 30 (corte 0,9988), acima do maior fracao deste
        seed pinado — e ~29% dos seeds (`corte**1000`) a fariam vermelha por
        SATURACAO, nao por defeito: era a assercao que nao era robusta, nao a
        cadencia. Minuto 1 vs 10 em taxa 0,2 da corte tardio 0,893, folgado
        abaixo do maior fracao, e a probabilidade de saturacao espuria cai para
        ~0,893**1000.
        """
        taxa, m_cedo, m_tarde = 0.2, 1, 10
        cedo = self._derr(taxa, m_cedo)
        tarde = self._derr(taxa, m_tarde)

        # A janela deixa sobreviventes POR CONSTRUCAO: o corte tardio fica
        # abaixo do maior fracao do conjunto. Este oraculo-lado (independente de
        # `derrubadas`) e o que torna a assercao robusta ao seed — se algum seed
        # futuro violar isto, o defeito e da janela, e a mensagem o diz.
        maior_fracao = max(fracao_do_sujeito(SEED, ROTA, FLAG, s) for s in MUITOS)
        self.assertLess(
            _corte_cumulativo(taxa, m_tarde), maior_fracao,
            "janela mal escolhida: o corte tardio satura o conjunto neste seed",
        )

        self.assertTrue(cedo < tarde, "o conjunto nao cresceu estritamente com o minuto")
        self.assertTrue(0 < len(cedo), "ninguem caiu no minuto 1 com taxa 0,2")
        self.assertTrue(
            len(tarde) < len(MUITOS), "tudo caiu — nenhum sobrevivente na janela"
        )

    def test_MONOTONA_na_taxa_no_mesmo_minuto(self):
        """Taxa maior derruba ao menos tantas quanto a menor, no mesmo minuto."""
        _exige_monotona_na_taxa(
            lambda taxa: self._derr(taxa, 5), (0.0, 0.1, 0.25, 0.4, 0.6, 0.8, 1.0)
        )

    def test_a_FRACAO_cumulativa_segue_a_taxa_e_o_minuto(self):
        """A fracao observada bate com o corte cumulativo — a cadencia declarada."""
        for taxa, minuto in ((0.1, 1), (0.1, 5), (0.3, 3), (0.2, 10), (0.5, 2)):
            with self.subTest(taxa=taxa, minuto=minuto):
                observada = len(self._derr(taxa, minuto)) / len(MUITOS)
                self.assertAlmostEqual(
                    observada, _corte_cumulativo(taxa, minuto), delta=0.05,
                    msg=f"taxa {taxa}, minuto {minuto}: fracao observada {observada}",
                )

    def test_conjunto_EXATO_bate_com_o_oraculo(self):
        """Fixa a semantica exata: o conjunto, e nao so o tamanho.

        Este e o alvo preciso da T810 — o corte cumulativo sobre
        `fracao_do_sujeito`. Sem ele, "aproximadamente a fracao certa" passaria
        com um conjunto errado.
        """
        for taxa, minuto in ((0.3, 4), (0.15, 12), (0.6, 2), (0.05, 40)):
            with self.subTest(taxa=taxa, minuto=minuto):
                self.assertEqual(
                    self._derr(taxa, minuto, ALGUNS),
                    _oracle(SEED, ROTA, FLAG, ALGUNS, taxa, minuto),
                )

    def test_os_extremos(self):
        """taxa 0 => ninguem em minuto nenhum; taxa 1 => teto em todas."""
        for minuto in MINUTOS:
            with self.subTest(taxa=0.0, minuto=minuto):
                self.assertEqual(self._derr(0.0, minuto), set())
        self.assertEqual(self._derr(1.0, 0), set(), "taxa 1 derrubou no minuto 0")
        for minuto in (1, 5, 90):
            with self.subTest(taxa=1.0, minuto=minuto):
                self.assertEqual(self._derr(1.0, minuto), set(MUITOS))

    def test_DETERMINISTA_mesma_entrada_mesmo_conjunto(self):
        """Funcao pura: duas chamadas iguais devolvem o conjunto identico."""
        self.assertEqual(self._derr(0.4, 7), self._derr(0.4, 7))

    def test_SENSIVEL_a_seed_rota_e_flag(self):
        """Entradas diferentes => conjuntos diferentes (licao de `dataset.py`)."""
        _exige_sensivel_a_entrada(
            lambda seed: self.mod.derrubadas(seed, ROTA, FLAG, ALGUNS, 0.5, 8),
            (SEED, SEED + 1, SEED + 2),
        )
        base = self._derr(0.5, 8, ALGUNS)
        por_rota = set(self.mod.derrubadas(SEED, "/outra/rota", FLAG, ALGUNS, 0.5, 8))
        por_flag = set(self.mod.derrubadas(SEED, ROTA, FLAG + "-x", ALGUNS, 0.5, 8))
        self.assertNotEqual(base, por_rota)
        self.assertNotEqual(base, por_flag)

    def test_FRAME_total_descreve_todas_as_sessoes(self):
        """INV-7: o frame e estado TOTAL, nunca delta; e coerente com `derrubadas`."""
        f = self.mod.frame(SEED, ROTA, FLAG, ALGUNS, 0.4, 10)
        _exige_frame_total(f, ALGUNS)
        caidos_no_frame = {s for s, e in f.items() if e == self.mod.DROPPED}
        self.assertEqual(caidos_no_frame, self._derr(0.4, 10, ALGUNS))

    def test_ESTAVEL_no_reinicio_processo_novo_produz_o_mesmo_conjunto(self):
        """A propriedade que `hash()` quebraria, e so entre processos.

        O filho nasce com outra salga de `PYTHONHASHSEED`. Uma cadencia por
        `hash()` seria estavel dentro deste processo e daria outro conjunto a
        cada boot — verde aqui, errada na sala.
        """
        aqui = sorted(self._derr(0.4, 6, ALGUNS))

        saida = subprocess.run(
            [
                sys.executable, str(CALCULADOR),
                str(SEED), ROTA, FLAG, "0.4", "6", *ALGUNS,
            ],
            capture_output=True, text=True, check=True, cwd=str(REPO_ROOT),
        )
        la = sorted(json.loads(saida.stdout))

        self.assertEqual(aqui, la)
        # O PAR QUE DISCRIMINA: um filho que devolvesse vazio — ou tudo — casaria
        # com um `aqui` degenerado sem que nada acusasse.
        self.assertTrue(0 < len(la) < len(ALGUNS))


# --------------------------------------------------------------------------- #
# MATRIZ GATE <-> MUTANTE — auto-contida, roda mesmo sem o modulo alvo.
# Cada mutante e uma implementacao ERRADA; o teste prova que a assercao central
# correspondente o MATA. R3 §5 / R10 §Nascimento.
# --------------------------------------------------------------------------- #
class MatrizDeMutantes(unittest.TestCase):
    """Cada teste demonstra o poder discriminante de uma assercao do gate."""

    def test_M1_nao_monotono_no_tempo_e_morto_pela_monotonia(self):
        """Mutante que re-sorteia a cada minuto: a fracao certa, o conjunto trocado."""
        def mutante(minuto: int) -> set:
            corte = _corte_cumulativo(0.3, minuto)
            # ERRO: mistura o minuto na derivacao => conjunto novo a cada minuto.
            return {
                s for s in MUITOS
                if fracao_do_sujeito(SEED, ROTA, f"{FLAG}|min{minuto}", s) < corte
            }

        with self.assertRaises(PropriedadeViolada):
            _exige_monotona_no_tempo(mutante, MINUTOS)
        # O par: o oraculo correto NAO e morto pela mesma assercao.
        _exige_monotona_no_tempo(
            lambda m: _oracle(SEED, ROTA, FLAG, MUITOS, 0.3, m), MINUTOS
        )

    def test_M2_hash_e_instavel_entre_processos(self):
        """Mutante por `hash()`: dois processos novos, dois conjuntos.

        E o `test_ESTAVEL_no_reinicio` que o mata contra o modulo real. Aqui a
        prova e concreta e sem o modulo: `hash()` de string e salgado por
        `PYTHONHASHSEED`, entao dois interpretadores frescos derrubam conjuntos
        diferentes — a igualdade entre processos os separa.
        """
        prog = (
            "import json\n"
            "sujeitos=[f'S-{n:04d}' for n in range(60)]\n"
            "corte=1-(1-0.4)**5\n"
            "print(json.dumps(sorted(s for s in sujeitos "
            "if (abs(hash(s))%10**9)/10**9<corte)))\n"
        )
        r1 = subprocess.run(
            [sys.executable, "-c", prog], capture_output=True, text=True, check=True
        )
        r2 = subprocess.run(
            [sys.executable, "-c", prog], capture_output=True, text=True, check=True
        )
        self.assertNotEqual(
            r1.stdout, r2.stdout,
            "hash() varia entre processos; o gate de reinicio (conjunto identico "
            "em processo novo) mata uma cadencia por hash()",
        )

    def test_M3_delta_em_vez_de_frame_total_e_morto(self):
        """Mutante que devolve so o que caiu NESTE minuto: frame incompleto."""
        def mutante_frame(minuto: int) -> dict:
            agora = _oracle(SEED, ROTA, FLAG, ALGUNS, 0.4, minuto)
            antes = _oracle(SEED, ROTA, FLAG, ALGUNS, 0.4, minuto - 1) if minuto else set()
            # ERRO: so o delta do minuto, sem alive e sem os ja caidos.
            return {s: "dropped" for s in (agora - antes)}

        with self.assertRaises(PropriedadeViolada):
            _exige_frame_total(mutante_frame(10), ALGUNS)
        # O par: um frame total legitimo NAO e morto.
        legitimo = {
            s: ("dropped" if s in _oracle(SEED, ROTA, FLAG, ALGUNS, 0.4, 10) else "alive")
            for s in ALGUNS
        }
        _exige_frame_total(legitimo, ALGUNS)

    def test_M4_ignora_a_entrada_e_morto_pela_sensibilidade(self):
        """Mutante que corta os N primeiros sujeitos, ignorando seed/rota/flag."""
        def mutante(seed: int) -> set:
            corte = _corte_cumulativo(0.5, 8)
            k = round(corte * len(ALGUNS))
            # ERRO: nao deriva de nada — mesmo conjunto para qualquer seed.
            return set(sorted(ALGUNS)[:k])

        with self.assertRaises(PropriedadeViolada):
            _exige_sensivel_a_entrada(mutante, (SEED, SEED + 1, SEED + 2))
        # O par: o oraculo correto varia com o seed e NAO e morto.
        _exige_sensivel_a_entrada(
            lambda seed: _oracle(seed, ROTA, FLAG, ALGUNS, 0.5, 8),
            (SEED, SEED + 1, SEED + 2),
        )


if __name__ == "__main__":
    unittest.main()
