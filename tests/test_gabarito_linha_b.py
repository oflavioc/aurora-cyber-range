"""A Linha B inteira em `database_audit`, e a ordem por instante — H1 da 5a auditoria.

POR QUE ESTE ARQUIVO E SEPARADO DE `test_gabarito.py`
=====================================================
`test_gabarito.py` tem uma classe que EXIGE Postgres e chama `gabarito.gerar`, o
que renderiza o `GM_NOTES.md` de um template IRMAO do modulo. O harness de
mutacao carrega o modulo de um diretorio TEMPORARIO: o template nao existe la, e
a ancora da prova negativa (`a suite esta verde sem mutacao`) reprovava — **so com
o banco no ar**, porque sem ele a classe pula e o defeito nao aparecia.

Medido: a suite dava 1147 OK sem Postgres e 5 falhas com Postgres. Um instrumento
que muda de veredito com o ambiente e pior que um que reprova sempre.

Entao o alvo do probe passa a ser **exatamente o que ele mede**: as quatro
propriedades da Linha B, que sao funcao das LINHAS da trilha e nao precisam de
banco nenhum. Ver `tests/test_gabarito_linha_b_probes.py`.

O QUE ESTE ARQUIVO PROVA
========================
As tres reversoes que o laudo da 5a rodada nomeou como invisiveis para a suite de
1139 testes, mais a especie por janela do M1 da mesma rodada.
"""

from __future__ import annotations

import importlib
import unittest

from domains.academus.seed import linha_b

#: Por `sys.modules`, e nao por `from <pacote> import <submodulo>` — a licao que
#: esta fase aprendeu quatro vezes: o harness substitui `sys.modules`, e o
#: atributo do pacote nao acompanha.
gabarito = importlib.import_module("domains.academus.seed.gabarito")

SEED = 20260818
PACK = "linha-b-academus"


class _ConexaoDeMentira:
    """Devolve as linhas do conjunto cuja subconsulta esta no SQL recebido."""

    def __init__(self, por_conjunto: dict[str, list[tuple]]) -> None:
        self._por_conjunto = por_conjunto

    def execute(self, clausula, _parametros):
        sql = str(clausula)
        casados = [n for n, q in linha_b.CONJUNTOS.items() if q in sql]
        # EXATAMENTE UM, e a assercao fica aqui: um dublê que devolvesse a lista
        # errada em silencio faria os casos abaixo medirem outra coisa. E a
        # mesma disciplina do harness de mutacao, que exige casamento unico.
        assert len(casados) == 1, f"o SQL nao identifica um conjunto so: {casados}"
        return list(self._por_conjunto[casados[0]])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _MotorDeMentira:
    def __init__(self, por_conjunto: dict[str, list[tuple]]) -> None:
        self._por_conjunto = por_conjunto

    def begin(self):
        return _ConexaoDeMentira(self._por_conjunto)


#: Uma linha da trilha, na forma que `_COLUNAS_DA_TRILHA` devolve:
#: `(sequence, actor, occurred_at, source_ip, payload, authorization_id,
#:   within_window)`.
def _linha(sequencia: int, instante: str, *, na_janela: bool):
    from datetime import datetime

    return (
        sequencia,
        "U-P-0783",
        datetime.fromisoformat(instante),
        "198.51.100.10",
        {"student_id": f"A-{sequencia:06d}"},
        None,
        na_janela,
    )


#: OS SEIS CONJUNTOS, com instantes EMBARALHADOS de proposito: o conjunto de
#: caso mais antigo vem depois de um legitimo normal, entao uma lista sem `sort`
#: nao pode sair ordenada por acidente.
#:
#: E os tres conjuntos de caso ficam FORA da janela, como `02` §6.1 descreve; os
#: tres restantes, dentro. E isso que faz `fact_class` discriminar.
POR_CONJUNTO = {
    "indevidos_comprovados": [
        _linha(101, "2026-08-06T22:12:00+00:00", na_janela=False),
        _linha(102, "2026-08-04T00:54:00+00:00", na_janela=False),
    ],
    "ambiguos_legitimos": [_linha(201, "2026-08-05T03:00:00+00:00", na_janela=False)],
    "legitimos_suspeitos": [_linha(301, "2026-08-02T01:00:00+00:00", na_janela=False)],
    "ruido_de_manutencao": [_linha(401, "2026-07-20T10:00:00+00:00", na_janela=True)],
    "credenciais_compartilhadas": [
        _linha(501, "2026-08-07T09:00:00+00:00", na_janela=True)
    ],
    "legitimos_normais": [
        _linha(601, "2026-07-15T08:00:00+00:00", na_janela=True),
        _linha(602, "2026-08-09T11:00:00+00:00", na_janela=True),
    ],
}


class ALinhaBInteiraVaiParaOArquivo(unittest.TestCase):
    """As tres propriedades que a volta da Linha B precisa ter, sem banco."""

    @classmethod
    def setUpClass(cls) -> None:
        # `ground_truth_de`, E NAO `gerar`: e a costura do H1 da quinta
        # auditoria. As quatro propriedades sao funcao das LINHAS, e `gerar`
        # renderiza tambem o `GM_NOTES.md` a partir de um template IRMAO — que o
        # harness de mutacao nao encontra, porque carrega o modulo de um
        # temporario. Ver o docstring de `ground_truth_de`.
        cls.gt, cls.contagens = gabarito.ground_truth_de(
            _MotorDeMentira(POR_CONJUNTO), seed=SEED, conta_alvo="U-P-0783"
        )
        cls.da_linha_b = [
            f for f in cls.gt["facts"] if f["fact_id"].startswith("GT-LINHAB-")
        ]

    def test_os_SEIS_conjuntos_viram_fato(self):
        """A reversão (2): voltar o laço para `CONJUNTOS_DE_CASO` reduz a
        população aos casos, e é o defeito que o B1 da 3ª auditoria nomeou —
        arquivo que entrega quais linhas são caso."""
        esperados = sum(len(v) for v in POR_CONJUNTO.values())
        self.assertEqual(len(self.da_linha_b), esperados)

    def test_so_os_TRES_conjuntos_de_caso_viram_caso(self):
        """O par do anterior. Sem ele, um gerador que fizesse caso de tudo
        passaria acima e entregaria a resposta por outro lado."""
        de_caso = sum(
            len(POR_CONJUNTO[nome]) for nome, _ in gabarito.CONJUNTOS_DE_CASO
        )
        self.assertEqual(len(self.gt["line_b_cases"]), de_caso)
        citados = {
            f for c in self.gt["line_b_cases"] for f in c["supporting_evidence"]
        }
        self.assertTrue(citados < {f["fact_id"] for f in self.da_linha_b})

    def test_TODA_linha_declara_a_projecao_em_database_audit(self):
        """A reversão (3): sem `projections`, a Linha B some de toda fonte — era
        o estado de `cb8d123`, e a suíte estava verde nele. `08` §3 exige que o
        `database_audit.jsonl` carregue as alterações de nota."""
        for fato in self.da_linha_b:
            self.assertEqual(fato.get("projections"), ["database_audit"], fato["fact_id"])

    def test_os_fatos_saem_ORDENADOS_POR_INSTANTE(self):
        """**A reversão (1), e é a que o auditor chamou de "um único `sort` sem
        teste".**

        O motor preserva a ordem do documento, então a ordem daqui é a ordem do
        arquivo. Se ela for a dos conjuntos, a POSIÇÃO entrega a partição por
        defensibilidade sem que nenhum campo vaze — a variante por posição do
        mesmo BLOCKER da 3ª rodada.
        """
        instantes = [f["exercise_time"] for f in self.da_linha_b]
        self.assertEqual(instantes, sorted(instantes))

    def test_a_ordem_por_instante_MISTURA_os_conjuntos(self):
        """A anti-vacuidade do caso acima, e ela é necessária: uma lista já
        ordenada por acidente passaria naquele teste sem provar que o `sort`
        existe. A fixture embaralha os instantes de propósito, então aqui a
        primeira linha do arquivo **não** pode ser de um conjunto de caso."""
        primeiro = self.da_linha_b[0]["fact_id"]
        de_caso = {
            f for c in self.gt["line_b_cases"] for f in c["supporting_evidence"]
        }
        self.assertNotIn(primeiro, de_caso)

    def test_a_ESPECIE_sai_da_janela_de_retificacao(self):
        """**M1 da quinta auditoria.** Com a população inteira, ~3.000 alterações
        DENTRO da janela carregavam `grade_change_retroactive` — rótulo falso num
        documento que `00` §3 faz autoridade sobre o que ocorreu.

        E `fact_class` é a chave do catálogo de `02` §10: um pack que roteasse a
        Linha B para `cef` emitiria `GRADE_CHANGE_RETROACTIVE` por alteração
        normal.
        """
        por_classe: dict[str, set[bool]] = {}
        for nome, linhas in POR_CONJUNTO.items():
            for linha in linhas:
                fato = next(
                    f
                    for f in self.da_linha_b
                    if f["fact_id"].endswith(str(linha[0]))
                )
                por_classe.setdefault(fato["fact_class"], set()).add(linha[6])
        self.assertEqual(
            por_classe,
            {"grade_change_retroactive": {False}, "grade_change_within_window": {True}},
            "a especie deixou de discriminar a janela",
        )


if __name__ == "__main__":
    unittest.main()
