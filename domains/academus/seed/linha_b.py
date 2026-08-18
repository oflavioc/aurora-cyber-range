"""As seis consultas que separam os conjuntos da Linha B — `02` §6.1.

POR QUE AS CONSULTAS MORAM AQUI, E NAO NO TESTE
-------------------------------------------------
Elas sao o **produto** da peca 4, e nao aparato de verificacao. `02` §6.3 manda o
`GM_NOTES.md` trazer *"a query de referencia que separa indevidos de ambiguos"*,
e `06` T8 exige que ela devolva exatamente os 22 comprovados. Escritas dentro do
teste, seriam inacessiveis ao gerador do `GM_NOTES` da peca 5 — e a alternativa,
escreve-las duas vezes, e a classe de defeito que este projeto ja pagou.

O QUE "DISTINGUIVEL" SIGNIFICA AQUI, E E MAIS FORTE QUE "CADA UMA DEVOLVE N"
-----------------------------------------------------------------------------
Seis consultas que devolvessem as contagens certas ainda poderiam se sobrepor —
uma linha contada em dois conjuntos, e outra em nenhum. O que o teste prova e que
elas **particionam** a trilha:

    contagem     cada consulta devolve o numero de `02` §6.1
    disjuncao    nenhuma linha aparece em dois conjuntos
    cobertura    a uniao e a trilha inteira, sem sobra

Sem as duas ultimas, dois conjuntos indistinguiveis passariam — o exercicio teria
cinco em vez de seis, e ninguem descobriria ate a sala.

A CONSULTA DOS AMBIGUOS E A QUE CARREGA O DESENHO
---------------------------------------------------
`02` §6.1 diz que o aprovador dos ambiguos *"tambem aparece nos indevidos"*. Como
os indevidos nao tem autorizacao nenhuma, a ligacao so pode ser pela CONTA: o
aprovador das 11 autorizacoes e a mesma conta docente que assina os 22. E isso
que os torna genuinamente inconclusivos, e e por isso que a consulta deles
referencia a conta dos indevidos em vez de um campo proprio.
"""

from __future__ import annotations

from domains.academus.seed.dataset import SVC_MIGRATION

#: A conta docente unica dos indevidos. Derivada do dataset — `professors[0]`.
CONTA_DOS_INDEVIDOS = "U-P-0000"

#: 1. INDEVIDOS COMPROVADOS — `defensibility` 1.0 em `02` §6.2.
INDEVIDOS = """
SELECT sequence FROM audit_trail
 WHERE within_window = false
   AND authorization_id IS NULL
   AND actor_user_id = :conta_alvo
"""

#: 2. AMBIGUOS LEGITIMOS — autorizacao aprovada pela conta dos indevidos.
AMBIGUOS = """
SELECT t.sequence FROM audit_trail t
  JOIN rectification_authorizations a
    ON a.authorization_id = t.authorization_id
 WHERE a.approver_user_id = :conta_alvo
"""

#: 3. LEGITIMOS SUSPEITOS — autorizacao solida, aprovador da coordenacao.
SUSPEITOS = """
SELECT t.sequence FROM audit_trail t
  JOIN rectification_authorizations a
    ON a.authorization_id = t.authorization_id
 WHERE a.approver_user_id <> :conta_alvo
"""

#: 4. RUIDO DE MANUTENCAO — a conta de servico.
RUIDO = """
SELECT sequence FROM audit_trail WHERE actor_user_id = :svc
"""

#: 5. CREDENCIAIS COMPARTILHADAS — delegacao formal valida NA DATA.
#:
#: E a consulta que so existe porque a delegacao virou TABELA: como campo da
#: linha de trilha, nao haveria como perguntar por validade em data nenhuma.
DELEGADAS = """
SELECT t.sequence FROM audit_trail t
 WHERE t.actor_user_id <> :svc
   AND EXISTS (
        SELECT 1 FROM access_delegations d
         WHERE d.delegating_user_id = t.actor_user_id
           AND t.occurred_at::date BETWEEN d.valid_from AND d.valid_until)
"""

#: 6. LEGITIMOS NORMAIS — dentro da janela, sem delegacao, sem conta de servico.
NORMAIS = """
SELECT t.sequence FROM audit_trail t
 WHERE t.within_window = true
   AND t.actor_user_id <> :svc
   AND NOT EXISTS (
        SELECT 1 FROM access_delegations d
         WHERE d.delegating_user_id = t.actor_user_id
           AND t.occurred_at::date BETWEEN d.valid_from AND d.valid_until)
"""

#: O nome de cada conjunto, na ordem de `02` §6.1.
CONJUNTOS: dict[str, str] = {
    "indevidos_comprovados": INDEVIDOS,
    "ambiguos_legitimos": AMBIGUOS,
    "legitimos_suspeitos": SUSPEITOS,
    "ruido_de_manutencao": RUIDO,
    "credenciais_compartilhadas": DELEGADAS,
    "legitimos_normais": NORMAIS,
}

PARAMETROS = {"conta_alvo": CONTA_DOS_INDEVIDOS, "svc": SVC_MIGRATION}
