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

from domains.academus.seed import carga, dataset, discriminantes, linha_b

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



def _linhas_por_conjunto(motor, conta_alvo: str) -> dict[str, list[dict]]:
    """As linhas da trilha, agrupadas por conjunto e achatadas em colunas.

    O `payload` e ABERTO em colunas — `student_id`, `previous_value`,
    `new_value`, `delta` —, porque e ali que dois dos seis vazamentos moraram. O
    teste varre coluna, e coluna dentro de JSON e coluna.
    """
    com_conjunto: dict[str, list[dict]] = {}
    with motor.begin() as conexao:
        todas = {
            linha[0]: linha
            for linha in conexao.execute(
                text(
                    "SELECT sequence, category, actor_user_id, source_ip, "
                    "user_agent, occurred_at, object_id, within_window, "
                    "authorization_id, payload FROM audit_trail"
                )
            )
        }
        for nome, consulta in linha_b.CONJUNTOS.items():
            sequencias = [
                l[0]
                for l in conexao.execute(
                    text(consulta), linha_b.parametros(conta_alvo)
                )
            ]
            com_conjunto[nome] = [
                {
                    "category": todas[s].category,
                    "actor_user_id": todas[s].actor_user_id,
                    "source_ip": todas[s].source_ip,
                    "user_agent": todas[s].user_agent,
                    "occurred_at": todas[s].occurred_at,
                    # A FAIXA e a hora; o minuto nunca e normativo. Achatados em
                    # colunas proprias porque a varredura e POR COLUNA, e o
                    # instante inteiro e valor de identidade.
                    "hora": todas[s].occurred_at.hour,
                    "minuto": todas[s].occurred_at.minute,
                    "object_id": todas[s].object_id,
                    "within_window": todas[s].within_window,
                    "authorization_id": todas[s].authorization_id,
                    "student_id": todas[s].payload["student_id"],
                    "previous_value": todas[s].payload["previous_value"],
                    "new_value": todas[s].payload["new_value"],
                    "delta": round(
                        todas[s].payload["new_value"]
                        - todas[s].payload["previous_value"],
                        2,
                    ),
                    "semester": todas[s].payload["semester"],
                }
                for s in sequencias
            ]
    return com_conjunto


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


@exige_banco
class NenhumaColunaForaDaListaSepara(unittest.TestCase):
    """B1, terceira rodada — a PROPRIEDADE, e nao mais N asserções por vetor.

    Seis vazamentos foram corrigidos um a um: identificador, ordem, valor, delta,
    infixo e indice. **A lista do que um laco fixa nao e enumeravel por
    inspecao**, entao corrigir vetor nunca terminava.

    Este teste inverte a pergunta. Em vez de "o prefixo vaza?", ele varre TODA
    coluna que o dataset escreve e exige, das que nao estao em
    `discriminantes.LISTA`, que nao separem conjunto. **Coluna nova entra na
    varredura sozinha** — e essa e a unica forma de o setimo vetor ser pego sem
    alguem se lembrar dele.

    O QUE A LISTA LICENCIA, E O QUE ELA NAO LICENCIA. `02` §6.1 exige a
    correlacao de alguns atributos — sem ela os indevidos deixam de ser
    indevidos. Cada entrada passou pela pergunta *"a spec exige a PROPRIEDADE ou
    o VALOR?"*, e o que a entrada licencia e so a propriedade: a classe de rede,
    nao o endereco; a faixa de horario, nao o horario; a concentracao do grupo,
    nao quais alunos.
    """

    @classmethod
    def setUpClass(cls) -> None:
        motor = _banco_vazio()
        cls.conta_a = _semeia(motor, SEED)
        cls.linhas_a = _linhas_por_conjunto(motor, cls.conta_a)
        motor = _banco_vazio()
        cls.conta_b = _semeia(motor, OUTRO_SEED)
        cls.linhas_b = _linhas_por_conjunto(motor, cls.conta_b)

    def test_a_lista_de_discriminantes_cobre_so_o_que_02_6_1_exige(self) -> None:
        """A lista nao pode virar esconderijo: toda entrada cita a propriedade.

        Sem isto, fechar um vazamento seria declarar a coluna discriminante — e a
        classe voltaria com o nome trocado.
        """
        for coluna, entrada in discriminantes.LISTA.items():
            self.assertTrue(
                entrada.propriedade.strip(),
                f"`{coluna}` esta na lista sem propriedade escrita",
            )
            self.assertTrue(
                entrada.conjuntos,
                f"`{coluna}` nao diz quais conjuntos licencia",
            )
            # E as constantes do dataset sao as UNICAS sem valor do seed.
            if not entrada.valor_do_seed.strip():
                self.assertIn(coluna, ("category", "semester"))

    def _varre(self, coluna: str, nome: str) -> tuple[set, set]:
        seus = {l[coluna] for l in self.linhas_a[nome]}
        outros = {
            l[coluna]
            for outro, ls in self.linhas_a.items()
            if outro != nome
            for l in ls
        }
        return seus, outros

    def test_nenhuma_coluna_separa_conjunto_QUE_ELA_NAO_LICENCIA(self) -> None:
        """A varredura, e ela respeita o campo `conjuntos` da lista.

        **A primeira versao ignorava esse campo**, e a medicao por mutacao pegou:
        com a hora do ruido fixa em 03h, ela passava — porque `occurred_at` esta
        na lista e ela isentava a coluna INTEIRA. A entrada licencia a faixa para
        indevidos e suspeitos, e para mais ninguem.

        Licenciar coluna para todos os conjuntos por comodidade e o esconderijo
        que a lista existe para nao ter.
        """
        for coluna in discriminantes.COLUNAS_DA_TRILHA:
            entrada = discriminantes.LISTA.get(coluna)
            for nome in self.linhas_a:
                if entrada is not None and nome in entrada.conjuntos:
                    continue
                seus, outros = self._varre(coluna, nome)
                # COLUNA DE IDENTIDADE NAO ENTRA na exclusividade: `object_id` e
                # `occurred_at` tem um valor por linha, e "todos exclusivos" e
                # verdade trivial. O que se exige delas e INTERCALACAO, e o teste
                # seguinte cobra isso. Medido: sem esta distincao, a varredura
                # reprovava contra timestamp, que nao e vazamento nenhum.
                distintos = len(seus | outros)
                if distintos > 0.9 * sum(len(l) for l in self.linhas_a.values()):
                    continue
                exclusivos = seus - outros
                self.assertFalse(
                    exclusivos and len(exclusivos) == len(seus),
                    f"a coluna `{coluna}` separa `{nome}`: todos os {len(seus)} "
                    f"valores dele sao exclusivos ({sorted(exclusivos)[:3]}). "
                    + (
                        f"A entrada da lista licencia `{coluna}` so para "
                        f"{entrada.conjuntos}."
                        if entrada
                        else "Coluna fora da lista nao pode dizer o conjunto."
                    ),
                )

    def test_nenhuma_coluna_ORDINAL_agrupa_conjunto_em_faixa(self) -> None:
        """A segunda metade, e a mutacao mediu que ela faltava.

        Exclusividade total nao pega assinatura PARCIAL: alunos sorteados de uma
        janela de indice contigua compartilham valores com os outros conjuntos e
        ainda assim se agrupam. O que se exige e INTERCALACAO — entre o menor e o
        maior valor do conjunto tem de haver linha de outro conjunto.
        """
        def ordinal(valor):
            if isinstance(valor, (int, float)):
                return float(valor)
            if isinstance(valor, str) and valor.rsplit("-", 1)[-1].isdigit():
                return float(valor.rsplit("-", 1)[-1])
            return None

        for coluna in discriminantes.COLUNAS_DA_TRILHA:
            entrada = discriminantes.LISTA.get(coluna)
            for nome, linhas in self.linhas_a.items():
                if entrada is not None and nome in entrada.conjuntos:
                    continue
                if len(linhas) < 3:
                    continue
                seus = [ordinal(l[coluna]) for l in linhas]
                if any(v is None for v in seus):
                    continue
                outros = [
                    ordinal(l[coluna])
                    for outro, ls in self.linhas_a.items()
                    if outro != nome
                    for l in ls
                ]
                outros = [v for v in outros if v is not None]
                dentro = [v for v in outros if min(seus) < v < max(seus)]
                self.assertTrue(
                    dentro,
                    f"a coluna `{coluna}` agrupa `{nome}` numa faixa contigua "
                    f"({min(seus)}..{max(seus)}) sem nenhuma linha de outro "
                    "conjunto no meio: a faixa separa o gabarito sozinha",
                )

    def test_o_object_id_nao_agrupa_o_conjunto_em_faixa(self) -> None:
        """A quarta instancia pelo outro lado: identidade unica e esperada, faixa
        contigua nao. Se as 22 menores forem os indevidos, contar resolve."""
        for nome, linhas in self.linhas_a.items():
            if len(linhas) < 2:
                continue
            seus = sorted(int(l["object_id"].rsplit("-", 1)[1]) for l in linhas)
            outros = sorted(
                int(l["object_id"].rsplit("-", 1)[1])
                for outro, ls in self.linhas_a.items()
                if outro != nome
                for l in ls
            )
            intercalados = [o for o in outros if seus[0] < o < seus[-1]]
            self.assertTrue(
                intercalados,
                f"`{nome}` ocupa uma faixa contigua de `object_id` "
                f"({seus[0]}..{seus[-1]}) sem nenhuma linha de outro conjunto no "
                "meio: a ordem voltou a denunciar",
            )

    def test_nenhuma_coluna_tem_o_MESMO_conteudo_nos_dois_seeds(self) -> None:
        """A varredura mais forte, e a que a medicao por mutacao exigiu.

        Exclusividade, intercalacao e concentracao sao aproximacoes: cada uma
        pega uma forma, e a mutacao de janela estreita passou pelas tres porque
        em escala reduzida a estatistica nao discrimina.

        **O que nao depende de escala e a comparacao entre SEEDS.** Qualquer
        coisa que o gerador fixe — janela de indice, hora, agente, faixa — produz
        o MESMO conteudo com qualquer seed. O que sai do pool nao produz.

        Vale por conjunto e por coluna, e so para o que a lista nao licencia: a
        conta unica dos indevidos muda entre seeds, mas continua unica, e a
        entrada dela e que diz isso.
        """
        for coluna in discriminantes.COLUNAS_DA_TRILHA:
            entrada = discriminantes.LISTA.get(coluna)
            if coluna in ("category", "semester"):
                continue  # constantes do dataset, e a lista as declara assim
            for nome in self.linhas_a:
                if entrada is not None and nome in entrada.conjuntos:
                    continue
                a = {l[coluna] for l in self.linhas_a[nome]}
                b = {l[coluna] for l in self.linhas_b[nome]}
                if len(a) < 3:
                    continue
                # VOCABULARIO PEQUENO NAO ENTRA, e a medicao exigiu a distincao:
                # com quatro user-agents sorteados para toda a Linha B, o
                # CONJUNTO de valores de qualquer grupo e o mesmo nos dois seeds
                # por natureza — o que muda e a atribuicao, e ela e coberta pela
                # exclusividade. A comparacao entre seeds so discrimina onde o
                # vocabulario e grande: ali, valor igual significa valor FIXADO.
                vocabulario = len(
                    {l[coluna] for ls in self.linhas_a.values() for l in ls}
                )
                if vocabulario < 0.2 * sum(len(l) for l in self.linhas_a.values()):
                    continue
                # COM LIMIAR, e nao `assertNotEqual`: comparar conjuntos por
                # igualdade e satisfeito por UM elemento de diferenca — que e
                # exatamente o defeito que o H1 apontou no teste anterior, e que
                # eu reproduzi aqui antes de a mutacao medir. Sobreposicao alta
                # e conteudo fixo com ruido em cima.
                # O LIMIAR E O DA INDEPENDENCIA, e nao uma fracao fixa: duas
                # amostras independentes de tamanho k sobre vocabulario V se
                # sobrepoem em ~k²/V por acaso. Limiar fixo reprovava `minuto`
                # (39 valores sobre 60 possiveis, 20 comuns) — que e MENOS que o
                # acaso prediz. Medido, e nao estimado.
                comuns = a & b
                esperado = len(a) * len(b) / max(1, vocabulario)
                self.assertLessEqual(
                    len(comuns),
                    max(2, 2 * esperado),
                    f"a coluna `{coluna}` repete {len(comuns)} de {len(a)} valores "
                    f"em `{nome}` entre dois seeds ({sorted(comuns)[:3]}): ela "
                    "esta fixada no gerador, e conteudo fixo e assinatura — "
                    "qualquer que seja a escala",
                )

    def test_nenhum_conjunto_alem_dos_indevidos_CONCENTRA_alunos(self) -> None:
        """A terceira forma da varredura, e a mutacao mediu que ela faltava.

        Exclusividade e intercalacao nao pegam CONCENTRACAO: alunos sorteados de
        uma janela estreita compartilham valores com os outros conjuntos e ficam
        intercalados — e ainda assim se repetem entre si, que e assinatura.

        A concentracao e licenciada **so para os indevidos**, e la ela e o
        discriminante normativo (`02` §6.1, "sempre no mesmo grupo"). Para os
        demais, o numero de alunos distintos tem de acompanhar o de linhas.
        """
        licenciados = discriminantes.LISTA["student_id"].conjuntos
        for nome, linhas in self.linhas_a.items():
            if nome in licenciados or len(linhas) < 8:
                continue
            distintos = len({l["student_id"] for l in linhas})
            self.assertGreater(
                distintos,
                len(linhas) // 2,
                f"`{nome}` concentra {len(linhas)} linhas em {distintos} alunos. "
                "A concentracao e licenciada so para os indevidos — repeticao "
                "aqui e assinatura, e ela passa por exclusividade e por "
                "intercalacao",
            )

    def test_a_ATRIBUICAO_de_cada_conjunto_difere_entre_dois_seeds(self) -> None:
        """H1 — e o `assertNotEqual` sobre uniao nao servia.

        Ele comparava uma tupla de conjuntos de atores e alunos: **um** elemento
        diferente entre milhares o satisfazia. Aqui a exigencia e por CONJUNTO e
        com limiar: a atribuicao de cada um dos seis tem de mudar de verdade.
        """
        for nome in self.linhas_a:
            def assinatura(linhas):
                return {
                    (l["student_id"], l["previous_value"], l["new_value"])
                    for l in linhas
                }

            a, b = assinatura(self.linhas_a[nome]), assinatura(self.linhas_b[nome])
            if len(a) < 5:
                continue
            comuns = a & b
            self.assertLess(
                len(comuns),
                max(1, len(a) // 4),
                f"`{nome}` tem {len(comuns)} de {len(a)} linhas identicas entre "
                "dois seeds: a atribuicao nao esta saindo do `RANDOM_SEED`",
            )

    def test_os_discriminantes_licenciam_a_PROPRIEDADE_e_nao_o_VALOR(self) -> None:
        """A pergunta que o operador aplicou a cada entrada, virada teste.

        Se o valor fosse fixo, a entrada seria vazamento com nome de
        discriminante. Tres casos, e os tres sao verificaveis:
        """
        # IP — a CLASSE e normativa; os hosts dos dois conjuntos que compartilham
        # a classe de laboratorio tem de se misturar.
        def hosts(nome):
            return {
                int(l["source_ip"].rsplit(".", 1)[1])
                for l in self.linhas_a[nome]
                if l["source_ip"].startswith(dataset.REDE_LABORATORIO)
            }

        ind, sus = hosts("indevidos_comprovados"), hosts("legitimos_suspeitos")
        self.assertTrue(
            ind and sus and not (max(ind) < min(sus) or max(sus) < min(ind)),
            f"os hosts de laboratorio nao se cruzam: indevidos {sorted(ind)[:4]}, "
            f"suspeitos {sorted(sus)[:4]} — sub-faixas disjuntas sao o mesmo "
            "vazamento com outro nome",
        )

        # HORARIO — a FAIXA e normativa; o minuto exato nao pode ser funcao do
        # indice, e a faixa noturna e compartilhada pelos dois conjuntos.
        minutos = {
            l["occurred_at"].minute for l in self.linhas_a["indevidos_comprovados"]
        }
        self.assertGreater(len(minutos), 1, "o minuto dos indevidos e constante")

        # GRUPO DE ALUNOS — a CONCENTRACAO e normativa, a identidade nao.
        alvo_a = {l["student_id"] for l in self.linhas_a["indevidos_comprovados"]}
        alvo_b = {l["student_id"] for l in self.linhas_b["indevidos_comprovados"]}
        self.assertLessEqual(len(alvo_a), 8, "o grupo alvo deixou de ser concentrado")
        self.assertNotEqual(
            alvo_a, alvo_b, "o grupo alvo e o mesmo com outro seed: nao sai do seed"
        )


if __name__ == "__main__":
    unittest.main()
