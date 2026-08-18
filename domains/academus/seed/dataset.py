"""O dataset em escala — `02` §5 e §6.1, `06` T8, `07` Fase 5.

O QUE ESTE MODULO PRODUZ, E O QUE E O PRODUTO DE VERDADE
----------------------------------------------------------
Volume e a parte facil. **Os seis conjuntos da Linha B sao o produto**: banco
populado sem eles e banco populado; com eles, o exercicio e investigavel. `02`
§6.2 diz o criterio — *"o exercicio nao e encontrar 40 eventos estranhos; e
demonstrar, com confianca declarada, quais eventos sao indevidos"*.

Por isso cada conjunto e gerado com uma ASSINATURA propria, e ha teste provando
que as seis consultas os separam **sem sobreposicao e sem sobra**. Dois conjuntos
indistinguiveis no dado fariam o exercicio ter cinco, e ninguem descobriria ate a
sala.

DETERMINISMO — a D6, e as DUAS direcoes
-----------------------------------------
`06` T8 exige dataset byte-identico entre duas execucoes com o mesmo
`RANDOM_SEED`. Duas regras sustentam isso, e a segunda e a que costuma faltar:

1. **NADA aqui le relogio.** Nao ha `now()`, `date.today()` nem `datetime.now()`:
   toda data deriva do `CalendarioAcademico`, que deriva de `ANO_BASE`. Uma unica
   leitura de relogio tornaria o item 2 da DoD insatisfazivel, e o defeito
   apareceria como diferenca de um campo em milhoes de linhas.

2. **Um fluxo por escopo**, via `seeded_random`. Geradores que compartilham fluxo
   ficam acoplados pela ORDEM: acrescentar um gerador desloca tudo o que vem
   depois, e o dataset muda por um motivo que ninguem localiza. `08` §1 nomeia
   isso.

**A direcao inversa tambem e provada**: seeds DIFERENTES produzem SHAs
diferentes. Sem ela, um gerador que ignorasse o seed passaria no primeiro teste —
"duas execucoes iguais" e verdade trivial para quem sempre produz a mesma coisa.

O SEPARADOR DO ESCOPO E `:`, e a razao esta no core: `academus.alunos` tem a
forma de um nome de flag, e o invariante 2 a recusa dentro de `domains/`. O hook
bloqueou na primeira escrita deste arquivo, e `range_core.determinism` passou a
documentar `academus:alunos`.

ESCALA E PARAMETRO, e a Linha B NAO escala
--------------------------------------------
`Escala` existe para a suite rodar em segundos sobre a mesma logica que produz o
dataset completo. O que escala e o volume de fundo — alunos, matriculas, notas,
legitimos normais. **Os cinco conjuntos plantados nao escalam**: 22, 11, 34, ~60
e 18 sao numeros de `02` §6.1, e reduzi-los faria o teste medir outra coisa.

`05` §3 — DADOS SINTETICOS
---------------------------
Nomes por Faker pt_BR, pinado. IPs so das faixas de documentacao (RFC 5737):
`198.51.100.0/24` para laboratorio e `203.0.113.0/24` para rede de campus.
Nenhum e-mail, telefone, endereco ou CPF — o modelo nao tem essas colunas, e
acrescenta-las so para preencher seria criar superficie de dado pessoal
sintetico sem consumidor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from domains.academus.audit import trilha
from range_core.determinism import derive_seed, seeded_random
from range_core.events.integrity import GENESIS_HASH, chained_hash

#: O ANO DO PRIMEIRO SEMESTRE. Constante, e nao `date.today().year`: o dataset
#: precisa ser o mesmo em 2026 e em 2030 para o mesmo seed.
ANO_BASE = 2023

#: `02` §6.1 — os cinco conjuntos PLANTADOS. Nao escalam.
INDEVIDOS = 22
AMBIGUOS = 11
SUSPEITOS = 34
RUIDO = 60
DELEGADAS = 18

#: A conta de servico de `02` §6.1 — "correcoes em lote por migracao de sistema".
SVC_MIGRATION = "svc_migration"

#: A coordenacao que aprova retificacao — `02` §3.
COORDENACAO = "U-COORD-0"

#: `05` §3 — RFC 5737. Laboratorio compartilhado e rede de campus, e a distincao
#: entre as duas e uma das caracteristicas que `02` §6.1 da aos indevidos.
REDE_LABORATORIO = "198.51.100."
REDE_CAMPUS = "203.0.113."

CAMPI = (
    "Campus Central",
    "Campus Norte",
    "Campus Sul",
    "Campus Litoral",
    "Campus EAD",
)


@dataclass(frozen=True, slots=True)
class Escala:
    """O volume de fundo. A Linha B nao esta aqui, e a ausencia e desenho."""

    alunos: int
    professores: int
    cursos: int
    disciplinas_por_curso: int
    semestres: int
    disciplinas_por_semestre: int
    normais_na_trilha: int


#: `02` §5 e o preambulo de `02`: 28.000 alunos, 1.200 professores, 60 cursos,
#: 8 semestres. `02` §6.1 poe "milhares" nos legitimos normais.
ESCALA_COMPLETA = Escala(
    alunos=28_000,
    professores=1_200,
    cursos=60,
    disciplinas_por_curso=8,
    semestres=8,
    disciplinas_por_semestre=5,
    normais_na_trilha=3_000,
)

#: Para a suite. Mesma logica, mesmo codigo, volume que roda em segundos.
ESCALA_REDUZIDA = Escala(
    alunos=120,
    professores=12,
    cursos=4,
    disciplinas_por_curso=4,
    semestres=8,
    disciplinas_por_semestre=3,
    normais_na_trilha=40,
)


@dataclass(frozen=True, slots=True)
class Dataset:
    """As tabelas prontas para `COPY`, mais o que a Linha B sorteou.

    `conta_alvo` E GABARITO, e por isso ela vive AQUI e nao num arquivo
    versionado: e a conta docente unica dos indevidos comprovados, sorteada a
    partir do `RANDOM_SEED`. Quem tem o seed a reproduz; quem so tem o
    repositorio, nao.
    """

    tabelas: dict[str, tuple[tuple, ...]]
    conta_alvo: str

    def total(self) -> int:
        return sum(len(linhas) for linhas in self.tabelas.values())


def _semestres(quantos: int) -> list[str]:
    """`2023.1`, `2023.2`, ... — rotulos estaveis, derivados de `ANO_BASE`."""
    return [f"{ANO_BASE + i // 2}.{i % 2 + 1}" for i in range(quantos)]


def _calendario(semestre: str) -> tuple:
    """As onze datas de `02` §2, derivadas do rotulo do semestre.

    A JANELA DE RETIFICACAO VEM DEPOIS DO LANCAMENTO, e a ordem nao e enfeite:
    `within_window` e calculado contra ela, e uma janela que comecasse antes do
    lancamento tornaria "fora da janela" verdadeiro para o mundo normal — a Linha
    B inteira nasceria indistinguivel.
    """
    ano, metade = semestre.split(".")
    base = date(int(ano), 2, 1) if metade == "1" else date(int(ano), 8, 1)
    return (
        semestre,
        base,                          # classes_start
        base + timedelta(days=130),    # classes_end
        base + timedelta(days=133),    # grade_entry_start
        base + timedelta(days=145),    # grade_entry_end
        base + timedelta(days=160),    # rectification_start
        base + timedelta(days=174),    # rectification_end
        base - timedelta(days=21),     # enrollment_start
        base - timedelta(days=3),      # enrollment_end
        base + timedelta(days=200),    # graduation_date
        base + timedelta(days=95),     # admission_exam_start
        base + timedelta(days=96),     # admission_exam_end
    )


def gerar(escala: Escala, *, seed: int) -> Dataset:
    """O dataset inteiro, em memoria, pronto para `COPY`. Sem tocar no banco."""
    fake = Faker("pt_BR")
    fake.seed_instance(derive_seed(seed, "academus:nomes"))

    r_curso = seeded_random("academus:cursos", seed=seed)
    r_aluno = seeded_random("academus:alunos", seed=seed)
    r_nota = seeded_random("academus:notas", seed=seed)
    r_linha_b = seeded_random("academus:linha_b", seed=seed)

    semestres = _semestres(escala.semestres)
    calendario = [_calendario(s) for s in semestres]
    janelas = {linha[0]: (linha[5], linha[6]) for linha in calendario}

    # -- cursos, disciplinas, professores, usuarios ---------------------------
    cursos, disciplinas = [], []
    for i in range(escala.cursos):
        curso_id = f"C-{i:04d}"
        sufixo = r_curso.choice(("Aplicada", "Geral", "Integrada"))
        cursos.append(
            (curso_id, f"{fake.word().capitalize()} {sufixo}", "graduacao",
             CAMPI[i % len(CAMPI)])
        )
        for j in range(escala.disciplinas_por_curso):
            disciplinas.append(
                (f"D-{i:04d}-{j:02d}", f"{fake.word().capitalize()} {j + 1}", curso_id, 60)
            )

    usuarios, professores = [], []
    for i in range(escala.professores):
        nome = fake.name()
        user_id = f"U-P-{i:04d}"
        usuarios.append((user_id, f"prof{i:04d}", nome, "professor", None, True))
        professores.append((f"P-{i:04d}", nome, user_id, None))

    # A CONTA DE SERVICO de `02` §6.1. `role` = `servico`: nao e papel de dominio
    # de `api_surface.yaml`, e conta de servico nao faz login.
    usuarios.append(
        (SVC_MIGRATION, SVC_MIGRATION, "Servico de Migracao", "servico", None, True)
    )
    usuarios.append((COORDENACAO, "coord0", fake.name(), "secretaria", None, True))

    # -- alunos ---------------------------------------------------------------
    alunos = []
    for i in range(escala.alunos):
        # `02` §5 — evasao com distribuicao plausivel.
        situacao = "evadido" if r_aluno.random() < 0.08 else "ativo"
        alunos.append(
            (f"A-{i:06d}", fake.name(), cursos[i % len(cursos)][0], situacao,
             semestres[i % len(semestres)])
        )

    # -- turmas, matriculas, notas, historico, frequencia ---------------------
    turmas = [
        (f"T-{semestre}-{d:04d}", disciplina[0], semestre,
         professores[d % len(professores)][0])
        for semestre in semestres
        for d, disciplina in enumerate(disciplinas)
    ]
    por_semestre: dict[str, list[tuple]] = {}
    for turma in turmas:
        por_semestre.setdefault(turma[2], []).append(turma)

    matriculas, notas, historico = [], [], []
    for indice, aluno in enumerate(alunos):
        for semestre in semestres:
            do_semestre = por_semestre[semestre]
            for k in range(escala.disciplinas_por_semestre):
                turma = do_semestre[(indice + k * 7) % len(do_semestre)]
                matriculas.append((aluno[0], turma[0], "matriculado"))
                # `02` §5 — distribuicao plausivel de reprovacao.
                valor = min(10.0, max(0.0, round(r_nota.gauss(7.0, 1.8), 1)))
                notas.append((aluno[0], turma[0], valor))
                historico.append(
                    (aluno[0], turma[1], semestre, valor,
                     "aprovado" if valor >= 6.0 else "reprovado")
                )

    # FREQUENCIA so do ULTIMO semestre, e o corte esta declarado: uma linha por
    # matricula por sessao daria dezenas de milhoes, e `02` nao pede volume de
    # frequencia em lugar nenhum. O que a peca 2 exigiu foi que a tabela nao
    # nascesse vazia.
    ultimo = semestres[-1]
    frequencia = [
        (m[1], m[0], janelas[ultimo][0], True)
        for m in matriculas
        if m[1].startswith(f"T-{ultimo}-")
    ]

    # -- volume minimo coerente, e o criterio esta na §4.2 do registro --------
    formandos = [a for a in alunos if a[3] == "ativo"][: max(1, escala.alunos // 20)]
    diplomas = [
        (f"DIP-{i:05d}", aluno[0], aluno[2], CAMPI[i % len(CAMPI)],
         calendario[-1][9], COORDENACAO)
        for i, aluno in enumerate(formandos)
    ]
    bolsas = [
        (f"BOL-{i:05d}", aluno[0], "merito" if i % 2 else "socioeconomica",
         50 if i % 2 else 100, semestres[0], None)
        for i, aluno in enumerate(alunos[: max(1, escala.alunos // 10)])
    ]
    contratos = [
        (f"CTR-{i:05d}", aluno[0], "financiamento", 850.0, "ativo", calendario[0][1])
        for i, aluno in enumerate(alunos[: max(1, escala.alunos // 25)])
    ]
    questoes = [
        (f"Q-{i:05d}", ("Matematica", "Linguagens", "Humanas", "Natureza")[i % 4],
         ANO_BASE + i % 4, ("facil", "media", "dificil")[i % 3],
         f"Enunciado sintetico {i:05d}")
        for i in range(max(20, escala.cursos * 5))
    ]
    projetos = [
        (f"PRJ-{i:04d}", f"Projeto sintetico {i:04d}",
         professores[i % len(professores)][2], "agencia-ficticia",
         calendario[0][1], None)
        for i in range(max(5, escala.professores // 20))
    ]
    jobs = [
        (f"JOB-{i:05d}", projetos[i % len(projetos)][0],
         projetos[i % len(projetos)][2],
         datetime.combine(calendario[0][1], datetime.min.time(), tzinfo=timezone.utc)
         + timedelta(hours=i),
         float(4 * (i % 12 + 1)), "concluido")
        for i in range(max(10, escala.professores // 10))
    ]

    autorizacoes, delegacoes, eventos, conta_alvo = _linha_b(
        escala, r_linha_b, semestres, janelas, alunos, professores
    )

    return Dataset(
        conta_alvo=conta_alvo,
        tabelas={
            "academic_calendar": tuple(calendario),
            "users": tuple(usuarios),
            "courses": tuple(cursos),
            "professors": tuple(professores),
            "subjects": tuple(disciplinas),
            "students": tuple(alunos),
            "classes": tuple(turmas),
            "enrollments": tuple(matriculas),
            "grades": tuple(notas),
            "academic_transcripts": tuple(historico),
            "attendance_records": tuple(frequencia),
            "diplomas": tuple(diplomas),
            "scholarships": tuple(bolsas),
            "financing_contracts": tuple(contratos),
            "exam_questions": tuple(questoes),
            "research_projects": tuple(projetos),
            "hpc_jobs": tuple(jobs),
            "rectification_authorizations": tuple(autorizacoes),
            "access_delegations": tuple(delegacoes),
            "audit_trail": tuple(eventos),
        }
    )


def _linha_b(escala, aleatorio, semestres, janelas, alunos, professores):
    """Os seis conjuntos de `02` §6.1, com assinatura propria cada um.

    AS ASSINATURAS SAO O PRODUTO. Cada conjunto e separavel dos outros por uma
    consulta, e `tests/test_seed_determinista.py` prova que as seis consultas
    PARTICIONAM a trilha — sem sobreposicao e sem sobra.

        indevidos   fora da janela, SEM autorizacao, conta docente unica,
                    IP de laboratorio, 22h-02h, sempre ELEVANDO, mesmo grupo
        ambiguos    fora da janela, COM autorizacao de justificativa generica,
                    aprovada pela MESMA conta que assina os indevidos
        suspeitos   fora da janela, COM autorizacao solida de outro aprovador,
                    IP de laboratorio, horario noturno — parecem, e nao sao
        ruido       conta de servico `svc_migration`, correcao em lote
        delegadas   dentro da janela, conta de professor COM delegacao formal
                    valida na data
        normais     dentro da janela, IP de campus, horario comercial

    O APROVADOR DOS AMBIGUOS E A CONTA DOS INDEVIDOS, e e isso que os torna
    genuinamente inconclusivos: `02` §6.1 pede "aprovador que tambem aparece nos
    indevidos". Sem essa ligacao, os 11 seriam apenas "fora da janela com
    autorizacao" — indistinguiveis dos 34, e o exercicio teria cinco conjuntos.
    """
    semestre_alvo = semestres[-2]
    inicio_janela, fim_janela = janelas[semestre_alvo]

    # AS IDENTIDADES SAO SORTEADAS, E NAO POSICIONAIS — e esta linha e a que
    # sustenta a D10 inteira.
    #
    # A primeira versao usava `professores[0]` e `alunos[:8]`: com isso, a conta
    # comprometida era SEMPRE a PRIMEIRA da lista e o grupo alvo eram os oito
    # primeiros, qualquer que fosse o `RANDOM_SEED`. O gabarito deixava de
    # depender do seed — e quem lesse este repositorio publico saberia quais sao
    # os casos sem nunca ver o `.env`.
    #
    # Foi `test_os_fatos_sao_DISTINTOS_entre_os_dois_seeds` que descobriu, e ele
    # so existe porque o operador pediu a direcao inversa da prova.
    conta_alvo = aleatorio.choice(professores)[2]
    grupo_alvo = [a[0] for a in aleatorio.sample(alunos, 8)]

    # OS OUTROS PAPEIS SAIEM DO MESMO SORTEIO, e nunca reusam a conta alvo: um
    # aprovador que fosse por acaso a conta comprometida embaralharia os
    # conjuntos 2 e 1, e a particao deixaria de valer.
    restantes = [p for p in professores if p[2] != conta_alvo]
    aprovados = [p[2] for p in aleatorio.sample(restantes, min(3, len(restantes)))]
    suspeitos = [p[2] for p in aleatorio.sample(restantes, min(5, len(restantes)))]

    fora = fim_janela + timedelta(days=10)
    dentro = inicio_janela + timedelta(days=3)

    def instante(dia: date, hora: int, minuto: int) -> datetime:
        return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=timezone.utc)

    def par(menor: float, maior: float) -> tuple[float, float]:
        """Nota anterior e nova, SORTEADAS, com faixa de variacao que se cruza.

        B1 da segunda auditoria, segunda instancia. Cada conjunto tinha um par
        FIXO — ambiguos 5,0 -> 6,5, suspeitos 5,5 -> 7,0, ruido 7,0 -> 7,0 —, e
        um `GROUP BY previous_value, new_value` devolvia o gabarito inteiro. Isso
        passa por qualquer varredura de identificador, porque nao ha string.

        A FAIXA E PARAMETRO E AS FAIXAS SE CRUZAM: se a de um conjunto nao
        tocasse a de nenhum outro, `new - previous` voltaria a separar sozinho.
        `02` §6.1 exige dos indevidos apenas que SEMPRE ELEVEM — e elevar nao os
        distingue, porque a maioria dos outros tambem eleva.
        """
        anterior = round(3.0 + aleatorio.random() * 5.0, 1)
        delta = round(menor + aleatorio.random() * (maior - menor), 1)
        return anterior, round(min(10.0, max(0.0, anterior + delta)), 1)

    autorizacoes, delegacoes, registros = [], [], []

    # O NUMERO DE PROCESSO NAO NOMEIA O CONJUNTO — quinta instancia do B1, achada
    # pelo verificador depois de o H1 ser corrigido.
    #
    # Eles traziam o INFIXO DO CONJUNTO no meio do identificador, e ele dizia
    # a que grupo a autorizacao pertencia
    # em `rectification_authorizations`, que e tabela que o participante LE. A
    # mesma familia do prefixo de `object_id`, e pelo mesmo caminho — a coluna.
    #
    # O contador e sequencial e comum aos tres conjuntos, entao o numero nao
    # separa nada; e determinista porque nao depende de sorteio.
    contador = iter(range(1, 10_000))

    def proximo_processo() -> int:
        return next(contador)

    # 1. INDEVIDOS COMPROVADOS (22)
    for i in range(INDEVIDOS):
        anterior, novo = par(0.5, 3.0)   # SEMPRE positivo — `02` §6.1
        registros.append(
            (
                conta_alvo,
                f"{REDE_LABORATORIO}{10 + i % 5}",
                # 22h-02h: os impares antes da meia-noite, os pares depois.
                instante(fora, 22 + i % 2, 10 + i) if i % 2
                else instante(fora + timedelta(days=1), i % 2, 10 + i),
                None,  # o `object_id` e atribuido depois do embaralhamento
                {
                    # SEMPRE ELEVANDO — `02` §6.1. A faixa cruza a dos outros
                    # conjuntos, entao elevar nao denuncia: quase todos elevam.
                    "previous_value": anterior,
                    "new_value": novo,
                    "student_id": grupo_alvo[i % len(grupo_alvo)],
                    "semester": semestre_alvo,
                },
                False,
                None,
            )
        )

    # 2. AMBIGUOS LEGITIMOS (11)
    for i in range(AMBIGUOS):
        anterior, novo = par(-1.0, 2.5)
        auth = f"AUT-{proximo_processo():05d}"
        autorizacoes.append(
            (auth, COORDENACAO, conta_alvo, "Ajuste solicitado.",
             f"PR-{proximo_processo():05d}", fora)
        )
        registros.append(
            (
                aprovados[i % len(aprovados)],
                f"{REDE_CAMPUS}{20 + i}",
                instante(fora, 14, i),
                None,  # o `object_id` e atribuido depois do embaralhamento
                {"previous_value": anterior, "new_value": novo,
                 "student_id": alunos[(100 + i) % len(alunos)][0],
                 "semester": semestre_alvo},
                False,
                auth,
            )
        )

    # 3. LEGITIMOS SUSPEITOS (34)
    for i in range(SUSPEITOS):
        anterior, novo = par(-1.5, 3.0)
        auth = f"AUT-{proximo_processo():05d}"
        autorizacoes.append(
            (auth, COORDENACAO, COORDENACAO,
             "Erro de digitacao no lancamento, conferido contra a prova fisica "
             "arquivada e a ata da banca.",
             f"PR-{proximo_processo():05d}", fora)
        )
        registros.append(
            (
                suspeitos[i % len(suspeitos)],
                f"{REDE_LABORATORIO}{30 + i % 20}",   # IP de laboratorio
                instante(fora, 23, i % 60),           # horario noturno
                None,  # o `object_id` e atribuido depois do embaralhamento
                {"previous_value": anterior, "new_value": novo,
                 "student_id": alunos[(200 + i) % len(alunos)][0],
                 "semester": semestre_alvo},
                False,
                auth,
            )
        )

    # 4. RUIDO DE MANUTENCAO (~60)
    for i in range(RUIDO):
        anterior, novo = par(-2.0, 2.0)
        registros.append(
            (
                SVC_MIGRATION,
                f"{REDE_CAMPUS}{200 + i % 50}",
                instante(fora, 3, i % 60),
                None,  # o `object_id` e atribuido depois do embaralhamento
                {"previous_value": anterior, "new_value": novo,
                 "student_id": alunos[(300 + i) % len(alunos)][0],
                 "semester": semestre_alvo, "lote": "migracao-2024"},
                False,
                None,
            )
        )

    # 5. CREDENCIAIS COMPARTILHADAS (18)
    delegantes = [p[2] for p in aleatorio.sample(restantes, 3)]
    for i, conta in enumerate(delegantes):
        delegacoes.append(
            (f"DEL-{i:03d}", conta, COORDENACAO, f"PR-{proximo_processo():05d}",
             inicio_janela, fim_janela,
             "Monitoria de disciplina, com registro na coordenacao.")
        )
    for i in range(DELEGADAS):
        anterior, novo = par(-1.0, 2.0)
        registros.append(
            (
                delegantes[i % len(delegantes)],
                f"{REDE_CAMPUS}{100 + i}",
                instante(dentro, 15, i % 60),
                None,  # o `object_id` e atribuido depois do embaralhamento
                {"previous_value": anterior, "new_value": novo,
                 "student_id": alunos[(400 + i) % len(alunos)][0],
                 "semester": semestre_alvo},
                True,
                None,
            )
        )

    # 6. LEGITIMOS NORMAIS (milhares)
    reservadas = set(delegantes) | {conta_alvo} | set(aprovados) | set(suspeitos)
    normais = [p[2] for p in professores if p[2] not in reservadas]
    for i in range(escala.normais_na_trilha):
        anterior, novo = par(-2.0, 3.0)
        registros.append(
            (
                normais[i % len(normais)],
                f"{REDE_CAMPUS}{i % 200}",
                instante(dentro, 9 + i % 8, i % 60),
                None,  # idem
                {"previous_value": anterior, "new_value": novo,
                 "student_id": alunos[i % len(alunos)][0],
                 "semester": semestre_alvo},
                True,
                None,
            )
        )

    # A ORDEM DA TRILHA E EMBARALHADA, e este e o terceiro vazamento de gabarito
    # que a peca 5 fechou — o mais silencioso dos tres.
    #
    # Sem isto, os conjuntos sao gravados em BLOCO e na ordem em que este arquivo
    # os escreve: as 22 primeiras linhas de `audit_trail` seriam sempre os
    # indevidos comprovados, as 11 seguintes os ambiguos, e assim por diante.
    # Quem lesse este repositorio publico saberia ler o gabarito na PROPRIA
    # TRILHA, que e o artefato que o participante investiga — sem nunca ver o
    # `.env`.
    #
    # Foi `test_o_MAPEAMENTO_caso_para_fato_muda_com_o_seed` que expos: o
    # mapeamento caso -> fato era identico entre dois seeds, porque o fato deriva
    # da POSICAO na trilha e a posicao era fixa.
    #
    # O embaralhamento e do fluxo semeado, entao continua determinista: mesmo
    # seed, mesma ordem.
    aleatorio.shuffle(registros)

    # O `object_id` E ATRIBUIDO AQUI, DEPOIS DO EMBARALHAMENTO — B1 da segunda
    # auditoria, e o QUARTO vazamento da mesma familia.
    #
    # Ele trazia `g-ind-`, `g-amb-`, `g-sus-`, `g-mnt-`, `g-del-` e `g-nrm-`: o
    # prefixo NOMEAVA o conjunto, na coluna que o participante le. Pior que o
    # vazamento de ordem, que ao menos exigia contar linhas — aqui bastava olhar.
    #
    # Atribuido depois do `shuffle` e em ordem de trilha, ele nao carrega nem o
    # conjunto nem a posicao de origem: e identidade de linha, e nada mais.
    numerados = [
        (ator, ip, quando, f"g-{n:06d}", payload, janela, auth)
        for n, (ator, ip, quando, _, payload, janela, auth) in enumerate(registros, 1)
    ]
    return autorizacoes, delegacoes, _encadeia(numerados), conta_alvo


def _encadeia(registros: list[tuple]) -> list[tuple]:
    """Aplica a cadeia de hash de `02` §4 item 4 sobre a trilha inteira.

    A SEQUENCIA E DA APLICACAO (D12), e e isso que torna esta funcao possivel: a
    cadeia inteira e calculada em memoria, na ordem, e vai ao banco num `COPY`
    so. Com `BIGSERIAL` seria preciso inserir linha a linha para saber o numero
    de cada uma antes de hashear a seguinte.

    A ORDEM AQUI E A DE INSERCAO, e nao a cronologica: a cadeia e sobre a ordem
    em que as linhas foram gravadas. `occurred_at` fora de ordem e normal — carga
    retroativa existe, e e o que a trilha registra.
    """
    encadeados = []
    anterior = GENESIS_HASH
    for i, (ator, ip, quando, objeto, payload, janela, auth) in enumerate(
        registros, start=1
    ):
        linha = trilha.Registro(
            category=trilha.ALTERACAO_DE_NOTA,
            actor_user_id=ator,
            source_ip=ip,
            user_agent="Mozilla/5.0",
            object_type="grade",
            object_id=objeto,
            occurred_at=quando,
            payload=payload,
            within_window=janela,
            authorization_id=auth,
        )
        atual = chained_hash(linha.forma_canonica(i), anterior)
        encadeados.append(
            (i, trilha.ALTERACAO_DE_NOTA, ator, ip, "Mozilla/5.0", quando, quando,
             "grade", objeto, payload, janela, auth, anterior, atual)
        )
        anterior = atual
    return encadeados
