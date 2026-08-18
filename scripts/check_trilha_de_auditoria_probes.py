#!/usr/bin/env python3
"""Prova que `check_trilha_de_auditoria.py` REPROVA contra mecanismo removido.

Checagem que nunca ficou vermelha prova que roda, nao que detecta.

POR QUE OS PROBES INJETAM O CONTEUDO DAS MIGRATIONS
-----------------------------------------------------
Os defeitos que esta checagem pega sao **remocoes**: o `REVOKE` que saiu, o
trigger que virou condicional, a rota que voltou a `planejada`. Planta-los
exigiria editar migration ja aplicada — que e a coisa que `02` secao 4 item 6
proibe — ou reescrever a arvore para testar. `verifica()` recebe o conteudo por
parametro para nao precisar de nenhum dos dois.

O EIXO MAIS IMPORTANTE E O ULTIMO, e ele nao e sobre SQL: a migration precisa
declarar o que `REVOKE` e trigger NAO protegem. Um mecanismo cuja leitura errada
e cara — "REVOKE, logo imutavel" — precisa carregar a propria limitacao, e essa
frase e a unica coisa aqui que nenhum teste de Postgres pegaria.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_trilha_de_auditoria import (  # noqa: E402
    MIGRATIONS,
    MODELOS,
    SUPERFICIE,
    main,
    verifica,
)

REAIS = {
    caminho.name: caminho.read_text(encoding="utf-8")
    for caminho in sorted(MIGRATIONS.glob("*.py"))
}
SUPERFICIE_REAL = SUPERFICIE.read_text(encoding="utf-8")
MODELOS_REAL = MODELOS.read_text(encoding="utf-8")

TRILHA = "0004_trilha_de_auditoria.py"


def _sem(trecho: str, por: str = "") -> dict[str, str]:
    """As migrations reais, com um trecho da trilha removido ou trocado."""
    copia = dict(REAIS)
    assert trecho in copia[TRILHA], f"o probe nao ancorou: {trecho!r} nao esta la"
    copia[TRILHA] = copia[TRILHA].replace(trecho, por)
    return copia


PROBES = [
    (
        "o REVOKE explicito dos tres verbos sumiu, e sobrou so o `REVOKE ALL`",
        lambda: (
            _sem('op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_trail FROM {ROLE}")')
            | {},
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "nao revoga",
    ),
    (
        "todo REVOKE sumiu",
        lambda: (
            {
                nome: (
                    texto.replace("REVOKE ALL ON TABLE audit_trail FROM PUBLIC", "")
                    .replace(
                        'op.execute(f"REVOKE ALL ON TABLE audit_trail FROM {ROLE}")', ""
                    )
                    .replace(
                        'op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE '
                        'audit_trail FROM {ROLE}")',
                        "",
                    )
                    if nome == TRILHA
                    else texto
                )
                for nome, texto in REAIS.items()
            },
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "nao revoga",
    ),
    (
        "o GRANT devolve UPDATE a role restrita",
        lambda: (
            _sem(
                'GRANT INSERT, SELECT ON TABLE audit_trail TO {ROLE}',
                "GRANT INSERT, SELECT, UPDATE ON TABLE audit_trail TO {ROLE}",
            ),
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "concede",
    ),
    (
        "o trigger deixou de existir",
        lambda: (
            _sem("CREATE TRIGGER tg_audit_trail_imutavel", "CREATE VIEW v_audit AS SELECT 1"),
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "BEFORE UPDATE OR DELETE",
    ),
    (
        "o trigger existe e nao levanta excecao",
        lambda: (
            _sem("RAISE EXCEPTION", "RAISE NOTICE"),
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "nao levanta excecao",
    ),
    (
        "a coluna de encadeamento sumiu",
        lambda: (
            _sem('sa.Column("previous_hash", sa.Text(), nullable=False),'),
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "previous_hash",
    ),
    (
        "a migration deixou de declarar o que REVOKE nao protege",
        lambda: (
            {
                nome: (
                    texto.replace("superusuario", "administrador")
                    if nome == TRILHA
                    else texto
                )
                for nome, texto in REAIS.items()
            },
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "nao declara o que `REVOKE` e trigger NAO protegem",
    ),
    (
        "a rota voltou a `planejada`",
        lambda: (
            REAIS,
            SUPERFICIE_REAL.replace(
                "    path: /audit/verify-chain\n    papeis: [secretaria]\n"
                "    flags: []\n    degradacao: []\n    status: implementada",
                "    path: /audit/verify-chain\n    papeis: [secretaria]\n"
                "    flags: []\n    degradacao: []\n    status: planejada",
            ),
            MODELOS_REAL,
        ),
        "declarada como `planejada`",
    ),
    (
        "a rota sumiu da superficie",
        lambda: (
            REAIS,
            SUPERFICIE_REAL.replace("/audit/verify-chain", "/audit/nada"),
            MODELOS_REAL,
        ),
        "nao esta na superficie declarada",
    ),
    (
        "a trilha ganhou modelo ORM",
        lambda: (
            REAIS,
            SUPERFICIE_REAL,
            MODELOS_REAL + '\n\nclass AuditTrail(Base):\n    __tablename__ = "audit_trail"\n',
        ),
        "ganhou modelo declarativo",
    ),
    (
        "duas migrations criam a mesma tabela",
        lambda: (
            REAIS | {"0009_outra.py": REAIS[TRILHA]},
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "e criada em mais de uma migration",
    ),
    (
        "nenhuma migration cria a tabela",
        lambda: (
            {n: t for n, t in REAIS.items() if n != TRILHA},
            SUPERFICIE_REAL,
            MODELOS_REAL,
        ),
        "nenhuma migration cria",
    ),
    (
        "controle: a arvore real",
        lambda: (REAIS, SUPERFICIE_REAL, MODELOS_REAL),
        None,
    ),
]


def roda(rotulo: str, monta, esperado) -> bool:
    problemas = verifica(*monta())

    if esperado is None:
        if problemas:
            print(f"FALHA: probe '{rotulo}' devia passar e acusou: {problemas}")
            return False
        print(f"OK: passou como devia - {rotulo}")
        return True

    if not problemas:
        print(f"FALHA: probe '{rotulo}': mecanismo removido e nada acusou")
        return False
    if not any(esperado in p for p in problemas):
        print(f"FALHA: probe '{rotulo}' acusou por outro eixo: {problemas}")
        return False
    print(f"OK: reprovou com mecanismo removido - {rotulo}")
    return True


def main_probes() -> int:
    if main([]) != 0:
        print("FALHA: a arvore limpa ja reprova; os probes nao provariam nada")
        return 1
    resultados = [roda(*p) for p in PROBES]
    print()
    if all(resultados):
        print(
            f"check_trilha_de_auditoria.py reprova nos {len(resultados)} eixos: os "
            "cinco obrigatorios de `02` secao 4, a limitacao declarada, a rota nas "
            "duas direcoes, o modelo ORM proibido, a tabela duplicada e a ausente."
        )
        return 0
    print(f"{resultados.count(False)} de {len(resultados)} probes nao provaram o eixo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main_probes())
