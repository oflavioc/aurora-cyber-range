"""A LISTA — o que pode correlacionar com o conjunto da Linha B, e por quê.

POR QUE ESTA LISTA EXISTE, E POR QUE ELA E O CONSERTO
------------------------------------------------------
A Fase 5 corrigiu SEIS vazamentos da mesma familia — identificador, ordem, valor,
delta, infixo e indice — um a um. Cinco correcoes pontuais e o defeito voltou por
um vetor que nenhuma alcancava.

**A propriedade que permitia**: o conjunto era a PRIMEIRA coisa decidida — um
laco por conjunto —, e todo atributo era escrito de dentro dele. Vazar era o caso
normal; nao vazar era o acidente. E a lista do que um laco fixa nao e enumeravel
por inspecao: por isso corrigir vetor nunca terminava.

**A propriedade que fecha** nao e "nada depende do conjunto" — isso destruiria a
Linha B, porque `02` §6.1 EXIGE a correlacao e sem ela os indevidos deixam de ser
indevidos. E esta:

    a particao dos atributos e DECLARADA, e tudo que nao esta nesta lista
    e sorteado por um caminho que nao conhece o conjunto.

Nao e o pool que fecha a classe: e o pool MAIS a lista, porque e a lista que
torna a fronteira verificavel em vez de intencional.

O TESTE DE CADA ENTRADA: A SPEC EXIGE A PROPRIEDADE OU O VALOR?
-----------------------------------------------------------------
Toda entrada passou por essa pergunta, e a resposta esta em `valor_do_seed`.
**Entrada que so se sustenta fixando o valor e vazamento com nome de
discriminante** — e foi assim que tres vetores novos apareceram ao escrever esta
lista, antes de qualquer teste:

    `lote` no payload    so o ruido tinha a chave: classificador perfeito. `02`
                         §6.1 marca o ruido pelo USUARIO, e nao por marcador de
                         payload. SAIU.
    `user_agent`         era `batch/1.0` so no ruido e `Mozilla/5.0` no resto.
                         `02` §4.1 exige registrar user-agent; nao o faz
                         discriminante. FOI PARA O POOL.
    hora do ruido        fixa em 03h. `02` §6.1 nao da horario ao ruido — a
                         faixa noturna e dos indevidos e dos suspeitos. FOI PARA
                         O POOL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Discriminante:
    """Uma entrada da lista, com as tres coisas que a tornam verificavel."""

    #: O que `02` §6.1 exige que correlacione. Citado, e nao parafraseado.
    propriedade: str
    #: O que, dentro dessa coluna, TEM de sair do `RANDOM_SEED`. Vazio significa
    #: que a coluna inteira e normativa — e so `category` e `semester` estao
    #: nesse caso, porque sao constantes do dataset.
    valor_do_seed: str
    #: Os conjuntos que a propriedade licencia. Os demais continuam sujeitos a
    #: varredura por coluna: licenciar "todos" por comodidade seria o
    #: esconderijo que esta lista existe para nao ter.
    conjuntos: tuple[str, ...]


#: OS CONJUNTOS, pelos nomes de `linha_b.CONJUNTOS`.
INDEVIDOS = "indevidos_comprovados"
AMBIGUOS = "ambiguos_legitimos"
SUSPEITOS = "legitimos_suspeitos"
RUIDO = "ruido_de_manutencao"
DELEGADAS = "credenciais_compartilhadas"
NORMAIS = "legitimos_normais"

TODOS = (INDEVIDOS, AMBIGUOS, SUSPEITOS, RUIDO, DELEGADAS, NORMAIS)

#: A LISTA. Toda coluna do dataset que NAO estiver aqui e varrida pelo teste de
#: coluna, e nenhuma delas pode separar conjunto.
LISTA: dict[str, Discriminante] = {
    "within_window": Discriminante(
        propriedade="estar dentro ou fora da janela de retificacao — `02` §6.1 "
        "define quatro dos seis conjuntos por isso, e `02` §2 diz que sem o "
        "calendario a Linha B nao e detectavel",
        valor_do_seed="a DATA exata dentro da regiao permitida, que vem do pool",
        conjuntos=TODOS,
    ),
    "authorization_id": Discriminante(
        propriedade="a PRESENCA ou AUSENCIA de autorizacao, e a identidade do "
        "aprovador — os indevidos nao tem, os ambiguos tem com aprovador que "
        "coincide com a conta dos indevidos, os suspeitos tem com aprovador da "
        "coordenacao (`02` §6.1)",
        valor_do_seed="QUAL autorizacao, e o numero de processo — sequenciais e "
        "comuns aos conjuntos desde a quinta instancia do B1",
        conjuntos=(INDEVIDOS, AMBIGUOS, SUSPEITOS),
    ),
    "actor_user_id": Discriminante(
        propriedade="a UNICIDADE da conta docente nos indevidos; ser conta de "
        "SERVICO no ruido; ter delegacao formal valida nas credenciais "
        "compartilhadas (`02` §6.1)",
        valor_do_seed="QUAL conta em cada caso — sorteada. A excecao e "
        "`svc_migration`, e ela e do seed no sentido inverso: `02` §6.1 escreve "
        "o nome literalmente, entao o VALOR e que e normativo",
        conjuntos=(INDEVIDOS, RUIDO, DELEGADAS),
    ),
    "source_ip": Discriminante(
        propriedade="a CLASSE de rede — laboratorio compartilhado nos indevidos e "
        "nos suspeitos, campus nos demais (`02` §6.1)",
        valor_do_seed="QUAL endereco dentro da classe. Os dois conjuntos que "
        "compartilham a classe tem de compartilhar tambem a faixa de hosts: "
        "sub-faixas disjuntas seriam o mesmo vazamento com outro nome",
        conjuntos=(INDEVIDOS, SUSPEITOS),
    ),
    "hora": Discriminante(
        propriedade="a FAIXA de horario — 22h-02h nos indevidos, noturno nos "
        "suspeitos (`02` §6.1). Os demais nao tem faixa normativa",
        valor_do_seed="o MINUTO e o dia — do pool, e varridos como colunas "
        "proprias. A entrada e sobre a FAIXA, entao ela nomeia a coluna `hora` e "
        "nao o instante inteiro: `occurred_at` completo e valor de identidade, e "
        "exclusividade de timestamp nao diz nada",
        conjuntos=(INDEVIDOS, SUSPEITOS),
    ),
    "student_id": Discriminante(
        propriedade="a CONCENTRACAO, e nao a identidade. `02` §6.1 pede que os "
        "indevidos recaiam SEMPRE NO MESMO GRUPO de alunos, e `02` §6.2 manda "
        "investigar exatamente isso",
        valor_do_seed="QUAIS alunos formam o grupo — sorteados. E os demais "
        "conjuntos nao tem concentracao nenhuma: eram cinco janelas de indice "
        "disjuntas, que foi o SEXTO vetor",
        conjuntos=(INDEVIDOS,),
    ),
    "delta": Discriminante(
        propriedade="a DIRECAO — os indevidos SEMPRE ELEVAM a nota (`02` §6.1)",
        valor_do_seed="a MAGNITUDE, e as faixas dos conjuntos tem de se cruzar: "
        "delta fixo por conjunto foi a segunda instancia do B1",
        conjuntos=(INDEVIDOS,),
    ),
    "category": Discriminante(
        propriedade="constante do dataset — toda linha da Linha B e alteracao de "
        "nota (`02` §4.1). Nao separa conjunto porque nao varia",
        valor_do_seed="",
        conjuntos=TODOS,
    ),
    "semester": Discriminante(
        propriedade="constante do dataset — a Linha B inteira e do semestre alvo",
        valor_do_seed="",
        conjuntos=TODOS,
    ),
}

#: AS COLUNAS QUE O DATASET ESCREVE na trilha, e que o teste varre. Escrita, e
#: nao derivada: derivada, ela concordaria com qualquer coisa que o gerador
#: escrevesse — inclusive com uma coluna nova que nasce vazando.
COLUNAS_DA_TRILHA = (
    "category",
    "hora",
    "minuto",
    "actor_user_id",
    "source_ip",
    "user_agent",
    "occurred_at",
    "object_id",
    "within_window",
    "authorization_id",
    "student_id",
    "previous_value",
    "new_value",
    "delta",
    "semester",
)

#: O QUE NAO E DISCRIMINANTE, derivado — e a direcao que importa: coluna nova
#: entra aqui sozinha, e o teste passa a exigir dela a nao-separacao.
def nao_discriminantes() -> tuple[str, ...]:
    return tuple(c for c in COLUNAS_DA_TRILHA if c not in LISTA)
