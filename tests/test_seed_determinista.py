"""`06` T8 — determinismo e gabarito, contra Postgres real.

    duas execucoes com o MESMO `RANDOM_SEED` produzem dataset identico
    os seis conjuntos da Linha B aparecem nos volumes de `02` §6.1
    a query de referencia devolve exatamente os 22 indevidos comprovados

AS DUAS DIRECOES DO DETERMINISMO, E A SEGUNDA E A QUE DISCRIMINA
------------------------------------------------------------------
"Duas execucoes iguais" e verdade trivial para um gerador que ignore o seed: ele
sempre produz a mesma coisa, e passaria. **Seeds diferentes tem de produzir SHAs
diferentes**, e e esse par que prova que o seed e de fato o insumo.

ESCALA REDUZIDA, MESMA LOGICA
------------------------------
O volume de fundo cai para a suite rodar em segundos; **a Linha B nao cai** —
22, 11, 34, 60 e 18 sao numeros de `02` §6.1, e reduzi-los faria o teste medir
outra coisa. O dataset COMPLETO e medido por `scripts/prova_seed_completo.py`,
com maquina, data e stack declaradas, como a D7 exige.
"""

from __future__ import annotations

import unittest

from sqlalchemy import text

from domains.academus.seed import carga, dataset, linha_b

from _academus_banco import TABELAS, engine, exige_banco

SEED = 20260818
OUTRO_SEED = 987654


def _semeia(motor, seed: int) -> str:
    """Carrega e devolve a `conta_alvo` sorteada — ela e parametro das consultas."""
    dados = dataset.gerar(dataset.ESCALA_REDUZIDA, seed=seed)
    carga.carregar(motor, dados)
    return dados.conta_alvo


def _banco_vazio():
    """Trunca tudo, e NAO recarrega a fixture de demonstracao.

    `banco_limpo()` recarrega os seis registros do DEMO, e eles poluiriam a
    contagem dos conjuntos: a fixture escreve em `students` e `classes` com
    identificadores proprios. Aqui o banco precisa ter so o que o seed poe.
    """
    motor = engine()
    with motor.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY"))
    return motor


@exige_banco
class Determinismo(unittest.TestCase):
    """T8, criterio 1 — e a direcao inversa, que e a que discrimina."""

    def test_o_mesmo_seed_produz_o_mesmo_dump(self) -> None:
        motor = _banco_vazio()
        carga.carregar(motor, dataset.gerar(dataset.ESCALA_REDUZIDA, seed=SEED))
        primeiro = carga.dump_canonico(motor)

        motor = _banco_vazio()
        carga.carregar(motor, dataset.gerar(dataset.ESCALA_REDUZIDA, seed=SEED))
        segundo = carga.dump_canonico(motor)

        self.assertEqual(primeiro, segundo)
        # E O DUMP NAO PODE SER VAZIO: vinte tabelas com o mesmo SHA de "nada"
        # tambem seriam iguais entre si.
        self.assertEqual(20, len(primeiro))

    def test_seeds_DIFERENTES_produzem_dumps_diferentes(self) -> None:
        """A direcao que impede o gerador de ignorar o seed e passar mesmo assim.

        Nem toda tabela precisa mudar — `academic_calendar` deriva de `ANO_BASE`
        e nao do seed, e mudaria so se o calendario passasse a ser sorteado. O
        que se exige e que as tabelas SORTEADAS mudem.
        """
        motor = _banco_vazio()
        carga.carregar(motor, dataset.gerar(dataset.ESCALA_REDUZIDA, seed=SEED))
        com_seed = carga.dump_canonico(motor)

        motor = _banco_vazio()
        carga.carregar(motor, dataset.gerar(dataset.ESCALA_REDUZIDA, seed=OUTRO_SEED))
        com_outro = carga.dump_canonico(motor)

        for tabela in ("students", "users", "grades", "audit_trail"):
            self.assertNotEqual(
                com_seed[tabela],
                com_outro[tabela],
                f"`{tabela}` nao mudou com outro seed: o gerador esta ignorando o "
                "`RANDOM_SEED`, e o teste de determinismo passaria por vacuidade",
            )

        # O CALENDARIO NAO MUDA, e isso e afirmado em vez de tolerado: ele deriva
        # de `ANO_BASE`, e um calendario sorteado poria a janela de retificacao em
        # data aleatoria — `within_window` deixaria de ser comparavel entre packs.
        self.assertEqual(com_seed["academic_calendar"], com_outro["academic_calendar"])

    def test_o_gerador_nao_le_relogio(self) -> None:
        """A regra 1 da D6, afirmada sobre o FONTE e nao sobre o resultado.

        Duas execucoes no mesmo segundo passariam no teste de igualdade mesmo com
        `now()` no caminho — o defeito so apareceria na virada do dia, longe da
        causa. Isto pega a CHAMADA.

        POR AST, E NAO POR TEXTO, e a razao foi medida: a primeira versao
        procurava a string `datetime.now(` no fonte e reprovou contra o proprio
        DOCSTRING do gerador, que cita a chamada para dizer que ela nao existe.
        E a mesma razao pela qual `06` T1 exige que a fronteira core/adapter seja
        verificada por AST — "nao por grep".
        """
        import ast
        from pathlib import Path

        proibidas = {("datetime", "now"), ("date", "today"), ("time", "time")}
        arvore = ast.parse(Path(dataset.__file__).read_text(encoding="utf-8"))
        achadas = [
            f"{no.func.value.id}.{no.func.attr} (linha {no.lineno})"
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and isinstance(no.func.value, ast.Name)
            and (no.func.value.id, no.func.attr) in proibidas
        ]
        self.assertEqual(
            [],
            achadas,
            f"leitura de relogio no gerador: {achadas}. `06` T8 exige dataset "
            "byte-identico, e relogio o torna insatisfazivel",
        )


@exige_banco
class SeisConjuntosDaLinhaB(unittest.TestCase):
    """T8, criterio 2 — e o que "distinguivel" significa: uma PARTICAO."""

    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(cls, "_pulado"):
            motor = _banco_vazio()
            cls.conta_alvo = _semeia(motor, SEED)
            cls.motor = motor

    def _sequencias(self, consulta: str) -> set[int]:
        with self.motor.begin() as conexao:
            return {
                linha[0]
                for linha in conexao.execute(text(consulta), linha_b.parametros(self.conta_alvo))
            }

    def test_os_volumes_sao_os_de_02_secao_6_1(self) -> None:
        """E ele LE A SPEC, e nao as constantes — M2 da auditoria de checkpoint.

        A versao anterior comparava o dataset com `dataset.INDEVIDOS`, quer
        dizer, o gerador consigo mesmo: trocar a constante por 20 mantinha o
        teste verde e fazia o dataset deixar de cumprir `02` §6.1. **O nome
        prometia "os de `02` §6.1" e entregava "os do gerador"** — nome que
        promete o que nao entrega e a classe da §7.3 da Fase 3, e por isso o
        nome ficou e a leitura mudou.

        A autoridade e a spec. `check_volumes_da_linha_b.py` cruza os dois em
        CI sem banco; aqui a spec e lida pelo mesmo parser, e o que se afere e o
        DADO SEMEADO contra ela.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from check_volumes_da_linha_b import SPEC, volumes_da_spec

        da_spec = volumes_da_spec(SPEC.read_text(encoding="utf-8"))
        esperado = {
            "indevidos_comprovados": int(da_spec["Indevidos comprovados"]),
            "ambiguos_legitimos": int(da_spec["Ambíguos legítimos"]),
            "legitimos_suspeitos": int(
                da_spec["Legítimos suspeitos à primeira vista"]
            ),
            "ruido_de_manutencao": int(da_spec["Ruído de manutenção"]),
            "credenciais_compartilhadas": int(da_spec["Credenciais compartilhadas"]),
            # O UNICO QUE NAO VEM DA SPEC, e a excecao esta declarada la e aqui:
            # `02` §6.1 lhe da "milhares", e o volume e parametro de `Escala`.
            "legitimos_normais": dataset.ESCALA_REDUZIDA.normais_na_trilha,
        }
        medido = {
            nome: len(self._sequencias(consulta))
            for nome, consulta in linha_b.CONJUNTOS.items()
        }
        self.assertEqual(esperado, medido)

    def test_os_conjuntos_sao_DISJUNTOS(self) -> None:
        """Nenhuma linha em dois conjuntos.

        Sem isto, seis consultas com as contagens certas ainda poderiam se
        sobrepor — e dois conjuntos que se sobrepoem sao, na pratica, um so.
        """
        conjuntos = {
            nome: self._sequencias(consulta)
            for nome, consulta in linha_b.CONJUNTOS.items()
        }
        nomes = sorted(conjuntos)
        for i, primeiro in enumerate(nomes):
            for segundo in nomes[i + 1 :]:
                comum = conjuntos[primeiro] & conjuntos[segundo]
                self.assertEqual(
                    set(),
                    comum,
                    f"`{primeiro}` e `{segundo}` compartilham {sorted(comum)[:5]}: "
                    "os dois nao sao distinguiveis no dado, e o exercicio tem "
                    "cinco conjuntos em vez de seis",
                )

    def test_a_uniao_e_a_trilha_INTEIRA(self) -> None:
        """Sem sobra: toda linha pertence a exatamente um conjunto.

        Uma linha fora dos seis seria um caso que o gabarito nao classifica — e
        o participante que a encontrasse estaria certo sem que o `ground_truth`
        soubesse dizer.
        """
        uniao: set[int] = set()
        for consulta in linha_b.CONJUNTOS.values():
            uniao |= self._sequencias(consulta)
        with self.motor.begin() as conexao:
            todas = {
                linha[0]
                for linha in conexao.execute(text("SELECT sequence FROM audit_trail"))
            }
        self.assertEqual(todas, uniao, f"fora dos seis: {sorted(todas - uniao)[:10]}")

    def test_a_query_de_referencia_devolve_os_22_e_nenhum_ambiguo(self) -> None:
        """T8, criterio 3 — *"exatamente os 22 indevidos comprovados"*.

        As duas metades: **22**, e **nenhum dos 11**. A segunda e o que `02` §6.3
        chama de "a query que SEPARA indevidos de ambiguos" — uma consulta que
        devolvesse 33 tambem devolveria 22 quando alguem contasse errado.
        """
        indevidos = self._sequencias(linha_b.INDEVIDOS)
        ambiguos = self._sequencias(linha_b.AMBIGUOS)
        self.assertEqual(dataset.INDEVIDOS, len(indevidos))
        self.assertEqual(set(), indevidos & ambiguos)

    def test_as_caracteristicas_de_02_secao_6_1_estao_no_dado(self) -> None:
        """As assinaturas, e nao so as contagens.

        `02` §6.1 descreve os indevidos por SEIS caracteristicas. Um gerador que
        produzisse 22 linhas sem elas passaria na contagem e daria a sala um
        conjunto que nao se parece com o que o `GM_NOTES` descreve.
        """
        with self.motor.begin() as conexao:
            linhas = conexao.execute(
                text(
                    "SELECT source_ip, occurred_at, payload, authorization_id,"
                    "       within_window, actor_user_id"
                    "  FROM audit_trail WHERE sequence IN ("
                    + linha_b.INDEVIDOS.replace("SELECT sequence FROM", "SELECT sequence FROM")
                    + ")"
                ),
                linha_b.parametros(self.conta_alvo),
            ).all()

        self.assertEqual(dataset.INDEVIDOS, len(linhas))
        alunos = set()
        for ip, quando, payload, auth, janela, ator in linhas:
            self.assertTrue(ip.startswith(dataset.REDE_LABORATORIO))  # IP de lab
            self.assertIn(quando.hour, {22, 23, 0, 1})                # 22h-02h
            self.assertGreater(payload["new_value"], payload["previous_value"])
            self.assertIsNone(auth)                                   # sem autorizacao
            self.assertFalse(janela)                                  # fora da janela
            self.assertEqual(self.conta_alvo, ator)                   # conta unica
            alunos.add(payload["student_id"])
        # SEMPRE NO MESMO GRUPO DE ALUNOS — a sexta caracteristica.
        self.assertLessEqual(len(alunos), 8)

    def test_a_LINHA_DA_TRILHA_nao_diz_a_que_conjunto_pertence(self) -> None:
        """B1 da segunda auditoria — o QUARTO vazamento da mesma familia.

        Os tres anteriores estavam no gerador, na posicao e na ordem. Este esta na
        PROPRIA LINHA: `object_id` trazia `g-ind-`, `g-amb-`, `g-sus-`, `g-mnt-`,
        `g-del-` e `g-nrm-`, e o prefixo NOMEIA o conjunto.

        **E pior que o terceiro**: aquele exigia ler o repositorio e contar
        linhas; este basta olhar a coluna. O participante investiga a trilha.

        A LACUNA NAO ERA O PREFIXO, ERA A DIRECAO. A bateria anti-vazamento
        inteira aponta para o `GM_NOTES` e para o repositorio — nenhum teste
        perguntava se a LINHA se denuncia. Esta e a pergunta.
        """
        with self.motor.begin() as conexao:
            linhas = conexao.execute(
                text("SELECT sequence, object_id FROM audit_trail")
            ).all()
        por_conjunto = {
            nome: self._sequencias(consulta)
            for nome, consulta in linha_b.CONJUNTOS.items()
        }
        objeto = {seq: obj for seq, obj in linhas}

        # UM PREFIXO SO PARA TODOS. Se cada conjunto tiver o seu, o prefixo E o
        # gabarito — e a consulta que o le nao precisa de mais nada.
        prefixos = {obj.rsplit("-", 1)[0] for obj in objeto.values()}
        self.assertEqual(
            1,
            len(prefixos),
            f"os `object_id` tem {len(prefixos)} prefixos distintos ({sorted(prefixos)}): "
            "a linha da trilha diz a que conjunto pertence, e o participante le "
            "isso na coluna",
        )

        # E O PREFIXO NAO PODE SER EXCLUSIVO DE NENHUM CONJUNTO, que e a mesma
        # propriedade dita do outro lado — vale mesmo se alguem trocar a forma.
        for nome, sequencias in por_conjunto.items():
            do_conjunto = {objeto[s].rsplit("-", 1)[0] for s in sequencias}
            dos_outros = {
                objeto[s].rsplit("-", 1)[0]
                for outro, seqs in por_conjunto.items()
                if outro != nome
                for s in seqs
            }
            self.assertTrue(
                do_conjunto <= dos_outros,
                f"`{nome}` tem prefixo de `object_id` que nenhum outro conjunto "
                f"tem: {sorted(do_conjunto - dos_outros)}",
            )

    def test_o_NUMERO_DE_PROCESSO_nao_diz_a_que_conjunto_pertence(self) -> None:
        """A QUINTA instancia do B1, achada pelo H1 depois de corrigido.

        `rectification_authorizations` e tabela que o participante LE, e os
        identificadores traziam infixo de conjunto — a autorizacao dizia se era
        de ambiguo ou de suspeito antes de qualquer analise. Mesma familia do
        prefixo de `object_id`, e pelo mesmo caminho: a coluna.
        """
        with self.motor.begin() as conexao:
            autorizacoes = conexao.execute(
                text(
                    "SELECT authorization_id, process_number "
                    "FROM rectification_authorizations"
                )
            ).all()
            delegacoes = conexao.execute(
                text("SELECT process_number FROM access_delegations")
            ).all()

        for coluna, valores in (
            ("authorization_id", [a[0] for a in autorizacoes]),
            ("process_number", [a[1] for a in autorizacoes] + [d[0] for d in delegacoes]),
        ):
            prefixos = {v.rsplit("-", 1)[0] for v in valores}
            self.assertLessEqual(
                len(prefixos),
                1,
                f"`{coluna}` tem {len(prefixos)} prefixos ({sorted(prefixos)}): o "
                "identificador diz a que conjunto a autorizacao pertence, e o "
                "participante le isso na tabela",
            )

    def test_o_PAR_DE_VALORES_nao_identifica_o_conjunto(self) -> None:
        """A segunda instancia do B1 — e ela passa por qualquer teste de string.

        Cada conjunto tinha um par FIXO: os ambiguos sempre 5,0 -> 6,5, os
        suspeitos sempre 5,5 -> 7,0, o ruido sempre 7,0 -> 7,0. Um `GROUP BY
        previous_value, new_value` devolve o gabarito inteiro, e nenhuma varredura
        de identificador ve isso.

        O QUE SE EXIGE: que o par nao seja constante por conjunto. Com valores
        sorteados, exigir que os pares COINCIDAM entre conjuntos seria impossivel
        — o que se pode exigir e que nenhum conjunto tenha assinatura unica.
        """
        with self.motor.begin() as conexao:
            valores = {
                linha[0]: (linha[1]["previous_value"], linha[1]["new_value"])
                for linha in conexao.execute(
                    text("SELECT sequence, payload FROM audit_trail")
                )
            }
        for nome, consulta in linha_b.CONJUNTOS.items():
            sequencias = self._sequencias(consulta)
            if len(sequencias) < 2:
                continue
            distintos = {valores[s] for s in sequencias}
            self.assertGreater(
                len(distintos),
                1,
                f"`{nome}` tem UM par de valores para {len(sequencias)} linhas "
                f"({distintos}): um `GROUP BY previous_value, new_value` devolve o "
                "conjunto inteiro, e nenhuma varredura de identificador ve isso",
            )

    def test_a_VARIACAO_de_nota_nao_separa_os_conjuntos(self) -> None:
        """A terceira forma da mesma pergunta: o DELTA como assinatura.

        Pares distintos ainda deixariam a faixa de variacao denunciar — se os
        indevidos sempre somassem exatamente 3,0 e mais ninguem, `new - previous`
        seria o gabarito. Exige-se que a faixa de cada conjunto CRUZE a de outro.
        """
        with self.motor.begin() as conexao:
            deltas = {
                linha[0]: round(
                    linha[1]["new_value"] - linha[1]["previous_value"], 2
                )
                for linha in conexao.execute(
                    text("SELECT sequence, payload FROM audit_trail")
                )
            }
        faixas = {}
        for nome, consulta in linha_b.CONJUNTOS.items():
            sequencias = self._sequencias(consulta)
            if sequencias:
                seus = [deltas[s] for s in sequencias]
                faixas[nome] = (min(seus), max(seus))

        for nome, (menor, maior) in faixas.items():
            cruza = any(
                outro != nome and not (maior < o_menor or o_maior < menor)
                for outro, (o_menor, o_maior) in faixas.items()
            )
            self.assertTrue(
                cruza,
                f"a faixa de variacao de `{nome}` ({menor}..{maior}) nao cruza a "
                "de nenhum outro conjunto: `new_value - previous_value` separa o "
                "gabarito sozinho",
            )

    def test_a_trilha_semeada_e_integra(self) -> None:
        """A cadeia calculada em memoria fecha quando lida do banco.

        E o par que liga a peca 4 a peca 3: o seed encadeia offline, e quem
        verifica e o mesmo `verificar` que a rota usa. Se as duas formas
        canonicas divergissem, isto ficaria vermelho.
        """
        from domains.academus.api.repositorio import Repositorio

        resultado = Repositorio(self.motor).verificar_trilha()
        self.assertTrue(resultado.integra, str(resultado.quebra))


if __name__ == "__main__":
    unittest.main()
