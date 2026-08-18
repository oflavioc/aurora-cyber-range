#!/usr/bin/env python3
"""`05_SECURITY_REQUIREMENTS.md` secao 7 — integridade da trilha de auditoria.

A SECAO QUE ESTA FASE TIROU DE "PLAUSIVELMENTE FUTURA"
-------------------------------------------------------
`05` secao 7 e requisito de SEGURANCA, nao de funcionalidade, e ate a peca 3 da
Fase 5 nenhum verificador a nomeava — foi a medicao da P4-12 que mostrou isso, e
mostrou tambem que a §6 estava na mesma situacao sem ninguem ter percebido.

A secao remete a `02_DOMAIN_ACADEMUS.md` secao 4 e exige cinco coisas: role
`INSERT`-only, `REVOKE UPDATE/DELETE`, trigger de bloqueio, encadeamento de hash
e endpoint de verificacao. **Este verificador confere que elas continuam
declaradas**; que elas FUNCIONAM e o que os testes de `06` T7 provam contra
Postgres real.

A DIVISAO ENTRE OS DOIS NAO E ARBITRARIA. Um teste prova o comportamento do banco
que ele tem na frente; este verificador prova que o MECANISMO nao saiu da arvore.
Sao falhas diferentes: apagar o `REVOKE` de uma migration futura nao derruba
nenhum teste que rode sobre um banco ja migrado — a tabela ja existe com as
permissoes de ontem —, e o defeito viajaria ate alguem recriar a base.

O QUE ELE NAO PROVA, e a assimetria precisa estar dita
-------------------------------------------------------
`REVOKE` e trigger nao alcancam quem nao passa pela role: superusuario e DONO da
tabela. O dono re-concede privilegio a si mesmo e pode `ALTER TABLE ... DISABLE
TRIGGER`. Quem cobre esse caso e a CADEIA DE HASH, por deteccao — e ela tambem
tem limite: nao pega truncamento da cauda, nem adversario que recompute a cadeia
inteira. Os dois limites estao declarados em `range-core/events/integrity.py`
desde a Fase 2.

Ler `REVOKE` como garantia total e o erro que esta divisao existe para impedir, e
por isso o verificador exige que a migration CARREGUE essa explicacao: um
mecanismo cuja leitura errada e cara precisa dizer o que nao faz.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = REPO_ROOT / "alembic" / "versions"
SUPERFICIE = REPO_ROOT / "domains" / "academus" / "api_surface.yaml"
MODELOS = REPO_ROOT / "domains" / "academus" / "models" / "registros.py"

RULE = "05 secao 7 - integridade da trilha de auditoria"

TABELA = "audit_trail"
ROTA = "/audit/verify-chain"

#: `REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_trail FROM <role>` — os tres
#: verbos que `02` secao 4 nomeia, em qualquer ordem.
REVOKE = re.compile(
    r"REVOKE\s+(?P<verbos>[A-Z,\s]+?)\s+ON\s+TABLE\s+" + TABELA + r"\s+FROM",
    re.I,
)
GRANT = re.compile(
    r"GRANT\s+(?P<verbos>[A-Z,\s]+?)\s+ON\s+TABLE\s+" + TABELA + r"\s+TO", re.I
)
TRIGGER = re.compile(
    r"CREATE\s+TRIGGER\s+\w+\s+BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+" + TABELA,
    re.I,
)
RAISE = re.compile(r"RAISE\s+EXCEPTION", re.I)

#: Os verbos que a role da aplicacao NAO pode ter. `02` secao 4 item 2.
PROIBIDOS = {"UPDATE", "DELETE", "TRUNCATE"}

#: As duas colunas do encadeamento — `02` secao 4 item 4.
COLUNAS_DE_CADEIA = ("previous_hash", "row_hash")


def _verbos(texto: str) -> set[str]:
    return {v.strip().upper() for v in texto.split(",") if v.strip()}


def verifica(migrations: dict[str, str], superficie: str, modelos: str) -> list[str]:
    """Recebe o conteudo por parametro para a prova negativa injetar hipotese."""
    problemas: list[str] = []

    criadoras = [
        nome for nome, texto in migrations.items()
        if re.search(r'create_table\(\s*["\']' + TABELA, texto)
    ]
    if not criadoras:
        problemas.append(
            f"nenhuma migration cria `{TABELA}`. `02` secao 4 item 1 exige tabela "
            "DEDICADA, separada das operacionais — sem ela nao ha trilha, e `05` "
            "secao 7 nao tem objeto."
        )
        return problemas
    if len(criadoras) > 1:
        problemas.append(
            f"`{TABELA}` e criada em mais de uma migration ({sorted(criadoras)}): "
            "duas definicoes do mesmo esquema divergem, e a segunda vence em "
            "silencio."
        )

    fonte = migrations[criadoras[0]]

    # 4. as colunas do encadeamento
    for coluna in COLUNAS_DE_CADEIA:
        if f'"{coluna}"' not in fonte:
            problemas.append(
                f"`{TABELA}` nao declara a coluna `{coluna}`. `02` secao 4 item 4 "
                "exige `row_hash = SHA256(prev_hash || payload canonico)`, e sem "
                "as duas colunas nao ha cadeia: adulteracao deixa de ser visivel."
            )

    # 2. o REVOKE, com os tres verbos
    revogados: set[str] = set()
    for casado in REVOKE.finditer(fonte):
        revogados |= _verbos(casado.group("verbos"))
    if not PROIBIDOS <= revogados:
        faltando = sorted(PROIBIDOS - revogados)
        problemas.append(
            f"a migration de `{TABELA}` nao revoga {faltando} da role da "
            "aplicacao. `02` secao 4 item 2 exige `REVOKE UPDATE, DELETE, "
            "TRUNCATE`, e `05` secao 7 a repete como requisito de seguranca.\n"
            "    `REVOKE ALL` NAO BASTA AQUI, e a exigencia e de forma: `ALL` "
            "revoga os tres de fato, e nao diz quais. Nomeados, o diff fala a "
            "lingua da spec e a remocao de um deles fica visivel em revisao — "
            "com `ALL`, trocar a linha por `REVOKE UPDATE` passaria como "
            "'ajuste', e as outras duas sairiam sem que nada mudasse de nome. "
            "Foi o probe do `REVOKE` que mediu isso: com `ALL` presente, apagar "
            "a linha explicita nao acusava nada."
        )

    # 2b. e o GRANT nao pode devolver o que o REVOKE tirou
    for casado in GRANT.finditer(fonte):
        concedidos = _verbos(casado.group("verbos"))
        if excesso := sorted((concedidos & PROIBIDOS) | ({"ALL"} & concedidos)):
            problemas.append(
                f"a migration concede {excesso} sobre `{TABELA}`. A role da "
                "aplicacao e `INSERT`-only por `02` secao 4 item 2 — `SELECT` "
                "entra porque a cadeia precisa ler a linha anterior, e nada alem."
            )

    # 3. o trigger, incondicional
    if not TRIGGER.search(fonte):
        problemas.append(
            f"nao ha `CREATE TRIGGER ... BEFORE UPDATE OR DELETE ON {TABELA}`. "
            "`02` secao 4 item 3 o exige, e ele e o que cobre quem NAO passa pela "
            "role — `REVOKE` sozinho nao alcanca o dono da tabela."
        )
    elif not RAISE.search(fonte):
        problemas.append(
            "o trigger existe e nao levanta excecao. `02` secao 4 item 3 diz "
            "INCONDICIONALMENTE: um trigger que apenas registra deixa a "
            "reescrita acontecer, e a trilha passa a ser append-only so no nome."
        )

    # 5. o endpoint
    if ROTA not in superficie:
        problemas.append(
            f"`{ROTA}` nao esta na superficie declarada. `02` secao 4 item 5 e "
            "`06` T7 exigem endpoint que percorra a cadeia e reporte a PRIMEIRA "
            "quebra — sem ele, a deteccao existe e ninguem consegue exerce-la."
        )
    elif re.search(re.escape(ROTA) + r"[\s\S]{0,400}?status:\s*planejada", superficie):
        problemas.append(
            f"`{ROTA}` esta declarada como `planejada`. A rota existe: promova a "
            "entrada no mesmo commit, que e a terceira direcao de "
            "`check_api_surface.py`."
        )

    # E O QUE ELE NAO PROTEGE, dito na propria migration
    if "superusuario" not in fonte.lower() and "superuser" not in fonte.lower():
        problemas.append(
            f"a migration de `{TABELA}` nao declara o que `REVOKE` e trigger NAO "
            "protegem. Os dois nao alcancam superusuario nem o DONO da tabela, e "
            "quem cobre esse caso e a cadeia de hash, por deteccao. Sem essa "
            "linha, o proximo leitor conclui `REVOKE` = imutavel — que e a "
            "leitura errada mais cara desta secao."
        )

    # A TRILHA NAO TEM MODELO ORM, e a ausencia e mecanismo
    if f'__tablename__ = "{TABELA}"' in modelos:
        problemas.append(
            f"`{TABELA}` ganhou modelo declarativo em {MODELOS.name}. Ela e "
            "`INSERT`-only: com modelo, um `session.merge()` distraido vira "
            "`UPDATE`, e o defeito so aparece quando o trigger o recusa em "
            "producao. O acesso e por SQL cru em `domains/academus/audit/"
            "trilha.py`, como o do `event_store`."
        )

    return problemas


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    migrations = {
        caminho.name: caminho.read_text(encoding="utf-8")
        for caminho in sorted(MIGRATIONS.glob("*.py"))
    }
    problemas = verifica(
        migrations,
        SUPERFICIE.read_text(encoding="utf-8"),
        MODELOS.read_text(encoding="utf-8"),
    )

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    print(
        f"{RULE}: tabela dedicada, role sem UPDATE/DELETE/TRUNCATE, trigger "
        f"incondicional, colunas de cadeia e `{ROTA}` implementada.\n"
        "  O que isto NAO prova: que o banco em producao aplica — os testes de "
        "`06` T7 provam contra Postgres real. E `REVOKE` e trigger nao alcancam "
        "dono nem superusuario; quem cobre esse caso e a cadeia, por deteccao."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
