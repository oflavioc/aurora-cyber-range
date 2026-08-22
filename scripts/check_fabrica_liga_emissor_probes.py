#!/usr/bin/env python3
"""Prova negativa da P6-7: a checagem da fabrica reprova defeito plantado.

Mesma doutrina do harness da Fase 0 — checagem que nunca reprovou prova que a
arvore passa, nao que ela enxerga. Aqui a frase tem endereco e data: o defeito
que esta checagem existe para pegar atravessou TRES auditorias como pendencia
declarada (P6-7) e virou o B2 da sexta.

A ARVORE E MONTADA, NUNCA MUTADA NO LUGAR
------------------------------------------
Cada caso escreve os quatro arquivos que a checagem le — as duas fabricas e as
duas superficies — em diretorio temporario, e aponta a checagem para a raiz dele
pelo caminho opcional de CLI.

AS DIRECOES, E POR QUE A TERCEIRA NAO E OBVIA
----------------------------------------------
    (a) fabrica SEM o produtor, superficie declarando `emite`  -> reprova
    (b) fabrica COM o produtor                                  -> passa
    (c) superficie SEM `emite`                                  -> nao exige
    (d) servico declarado sem produtor que GANHA uma fabrica    -> reprova
    (e) caminho declarado que sumiu                             -> reprova

A (c) e a que impede a checagem de virar "toda fabrica precisa de emissor": um
servico cuja superficie nao promete evento nenhum nao deve nada. Sem ela, a
checagem passaria em (a) por reprovar tudo.

A (d) e o gatilho do `participant-api`, que hoje tem `montar` e nao tem fabrica.
Ele nao e defeito — e estado declarado. O defeito seria ele nascer servico sem
que ninguem decidisse quem grava os eventos que a superficie dele promete.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_fabrica_liga_emissor import SERVICOS, main  # noqa: E402

SUPERFICIE_COM_EMITE = """rotas:
  - method: get
    path: /audit/grade-changes
    status: implementada
    emite: audit_query_performed
"""

SUPERFICIE_SEM_EMITE = """rotas:
  - method: get
    path: /students/{student_id}
    status: implementada
"""

#: A superficie do `range-api` nao muda entre os casos: o eixo sob teste e o
#: `academus-api`, e o outro servico entra so para a checagem nao ficar com um
#: elemento so.
SUPERFICIE_DO_NUCLEO = """rotas:
  - method: post
    path: /exercise/start
    status: implementada
    emite: exercise_started
"""

FABRICA_COM_PRODUTOR = '''
def criar():
    """A fabrica que o uvicorn chama."""
    store = PostgresEventStore(clock, dsn)
    return montar(autenticacao, repositorio, None, emissor=Emissor(store=store))
'''

FABRICA_SEM_PRODUTOR = '''
def criar():
    """A fabrica que monta sem produtor — o B2 da sexta auditoria."""
    store = PostgresEventStore(clock, dsn)
    return montar(autenticacao, repositorio, None)
'''

FABRICA_DO_NUCLEO = '''
def criar():
    """O nucleo emite pelo engine, e nao por um argumento `emissor`."""
    exercicio = Exercicio(engine=InjectEngine(pack=pack, store=store))
    return montar(exercicio)
'''

#: Sem `criar`. E a forma do `participant-api` de hoje.
MODULO_SEM_FABRICA = '''
def montar(superficie, segredo, emissor=None):
    """So a montagem. Nao ha servico, e nao ha fabrica."""
    return object()
'''


def _arvore(
    raiz: Path,
    *,
    fabrica_academus: str,
    superficie_academus: str,
    participante: str = MODULO_SEM_FABRICA,
) -> Path:
    """Escreve os arquivos que `SERVICOS` declara, e devolve a raiz."""
    conteudos = {
        SERVICOS["academus-api"][0]: fabrica_academus,
        SERVICOS["academus-api"][1]: superficie_academus,
        SERVICOS["range-api"][0]: FABRICA_DO_NUCLEO,
        SERVICOS["range-api"][1]: SUPERFICIE_DO_NUCLEO,
        SERVICOS["participant-api"][0]: participante,
        SERVICOS["participant-api"][1]: SUPERFICIE_SEM_EMITE,
    }
    for relativo, texto in conteudos.items():
        destino = raiz / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return raiz


def main_probes() -> int:
    falhas: list[str] = []

    with tempfile.TemporaryDirectory() as temporario:
        base = Path(temporario)

        # (a) — o caso do B2.
        raiz = _arvore(
            base / "a",
            fabrica_academus=FABRICA_SEM_PRODUTOR,
            superficie_academus=SUPERFICIE_COM_EMITE,
        )
        if main([str(raiz)]) == 0:
            falhas.append("fabrica SEM o produtor e superficie com `emite`: PASSOU")
        else:
            print("  reprovou como devia: fabrica sem o produtor declarado")

        # (b) — o positivo. Sem ele, (a) passaria por reprovar tudo.
        raiz = _arvore(
            base / "b",
            fabrica_academus=FABRICA_COM_PRODUTOR,
            superficie_academus=SUPERFICIE_COM_EMITE,
        )
        if main([str(raiz)]) != 0:
            falhas.append(
                "fabrica COM o produtor foi reprovada: a checagem nao "
                "discrimina, e o negativo acima nao prova nada."
            )
        else:
            print("  passou como devia: fabrica que constroi o produtor")

        # (c) — superficie que nao promete evento nenhum nao deve nada.
        raiz = _arvore(
            base / "c",
            fabrica_academus=FABRICA_SEM_PRODUTOR,
            superficie_academus=SUPERFICIE_SEM_EMITE,
        )
        if main([str(raiz)]) != 0:
            falhas.append(
                "superficie SEM `emite` exigiu produtor: a checagem virou "
                "'toda fabrica precisa de emissor', que nao e a regra."
            )
        else:
            print("  passou como devia: superficie sem `emite` nao exige produtor")

        # (d) — o servico sem produtor declarado que ganha fabrica.
        raiz = _arvore(
            base / "d",
            fabrica_academus=FABRICA_COM_PRODUTOR,
            superficie_academus=SUPERFICIE_COM_EMITE,
            participante=FABRICA_COM_PRODUTOR,
        )
        if main([str(raiz)]) == 0:
            falhas.append(
                "servico declarado SEM produtor ganhou `criar` e a checagem "
                "PASSOU. O gatilho da decisao nao dispara."
            )
        else:
            print("  reprovou como devia: servico sem produtor declarado ganhou fabrica")

        # (e) — caminho declarado que sumiu.
        raiz = base / "e"
        (raiz / "domains").mkdir(parents=True)
        if main([str(raiz)]) == 0:
            falhas.append(
                "arvore SEM os arquivos declarados passou. A checagem aprova por "
                "ausencia do proprio objeto."
            )
        else:
            print("  reprovou como devia: caminho declarado que nao existe")

    # POSITIVO FINAL — a arvore real. E o que pega o probe que so exercita
    # fixture e nunca olhou para o repositorio.
    if main([]) != 0:
        falhas.append("a arvore real reprova — a checagem esta quebrada, ou ha defeito")

    if falhas:
        for falha in falhas:
            print(f"PROVA NEGATIVA FALHOU: {falha}", file=sys.stderr)
        return 1

    print(
        "5 direcoes provadas (fabrica sem produtor, com produtor, superficie sem "
        "`emite`, servico que ganha fabrica, caminho ausente); a arvore real passa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probes())
