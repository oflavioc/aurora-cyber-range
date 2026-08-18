#!/usr/bin/env python3
"""Os volumes da Linha B do gerador batem com `02_DOMAIN_ACADEMUS.md` secao 6.1.

POR QUE ISTO EXISTE — M2 da auditoria de checkpoint da Fase 5
--------------------------------------------------------------
Os cinco conjuntos plantados sao numeros da SPEC: 22 indevidos comprovados, 11
ambiguos, 34 legitimos de aparencia suspeita, ~60 de ruido e 18 de credenciais
compartilhadas. No gerador eles sao constantes, e o teste que os julgava lia as
CONSTANTES — quer dizer, comparava o gerador consigo mesmo.

**Isso satisfaz hoje e nao impede a deriva.** Trocar `INDEVIDOS = 22` por `20`
manteria o teste verde: ele afirmaria que o dataset tem 20 indevidos e que a
constante diz 20. A spec deixaria de ser cumprida sem nada ficar vermelho, e o
`GM_NOTES` gerado passaria a descrever um exercicio diferente do que `02` §6.1
descreve.

A CONFERENCIA A MAO SATISFAZ E NAO SEGURA. O auditor conferiu os cinco numeros e
eles estavam certos; a rodada seguinte depende de alguem conferir de novo.

A FORMA E A DE `check_spec_flags.py`
--------------------------------------
Ele cruza flag citada na spec com flag declarada no adapter, nas duas direcoes.
Aqui: volume escrito na TABELA de `02` §6.1 contra constante de
`domains/academus/seed/dataset.py`, tambem nas duas direcoes.

    (a) conjunto na tabela da spec sem constante correspondente   -> REPROVA
    (b) constante de volume sem linha na tabela da spec           -> REPROVA
    (c) numero divergente entre os dois                           -> REPROVA
    (d) a tabela deixou de ser legivel — zero conjuntos lidos     -> REPROVA

A (d) e a que impede a degradacao silenciosa: se `02` §6.1 mudar de forma e o
parser parar de casar, as outras tres passariam por vacuidade. Nao saber e
exatamente o caso em que nao se pode afirmar.

POR QUE O VERIFICADOR, E NAO SO O TESTE
-----------------------------------------
Os testes do seed EXIGEM Postgres e PULAM sem ele. O CI os roda, mas a checagem
de arquitetura roda sempre e sem banco — e e ela que deve responder "o gerador
ainda promete o que a spec pede". O teste continua existindo e passou a aferir
contra a spec, pela mesma leitura que este arquivo expoe.

A LEITURA DAS CONSTANTES E POR AST, e nao por import: `domains/` importa
`faker` e `sqlalchemy`, e um verificador do job `arquitetura` que precisasse
delas deixaria de ser stdlib pura — que e o que permite este job rodar antes de
qualquer instalacao.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "spec" / "02_DOMAIN_ACADEMUS.md"
GERADOR = REPO_ROOT / "domains" / "academus" / "seed" / "dataset.py"

RULE = "M2 - volumes da Linha B do gerador x 02_DOMAIN_ACADEMUS secao 6.1"

#: A LIGACAO ENTRE A LINHA DA TABELA E A CONSTANTE, e ela e escrita porque nao e
#: derivavel: a spec nomeia os conjuntos em portugues corrido ("Indevidos
#: comprovados") e o codigo os nomeia em constante ("INDEVIDOS"). O par vive
#: aqui, e a direcao (b) cobra que nenhuma constante fique sem par.
#:
#: `Legitimos normais` NAO tem constante, e a ausencia e declarada: `02` §6.1 lhe
#: da "milhares" em vez de numero, e o volume dele e parametro de `Escala` — o
#: unico dos seis que escala com o tamanho do dataset.
CONJUNTOS: dict[str, str | None] = {
    "Indevidos comprovados": "INDEVIDOS",
    "Ambíguos legítimos": "AMBIGUOS",
    "Legítimos suspeitos à primeira vista": "SUSPEITOS",
    "Ruído de manutenção": "RUIDO",
    "Credenciais compartilhadas": "DELEGADAS",
    "Legítimos normais": None,
}

#: `| **Indevidos comprovados** | 22 | Conta docente unica, ... |`
#:
#: O `~` de "~60" e absorvido: `02` §6.1 escreve o ruido como aproximado, e o
#: gerador o fixa. Aproximado na spec e fixo no codigo e coerente — o que nao
#: pode e o numero ser outro.
LINHA = re.compile(r"^\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|\s*~?([0-9]+|milhares)\s*\|")


def volumes_da_spec(texto: str) -> dict[str, str]:
    """`{nome do conjunto: volume}` lidos da tabela de `02` §6.1."""
    dentro = False
    lidos: dict[str, str] = {}
    for linha in texto.splitlines():
        if linha.startswith("### 6.1"):
            dentro = True
            continue
        if dentro and linha.startswith("#"):
            break
        if not dentro:
            continue
        if casado := LINHA.match(linha):
            nome, volume = casado.group(1).strip(), casado.group(2)
            if nome != "Conjunto":
                lidos[nome] = volume
    return lidos


def constantes(fonte: str) -> dict[str, int]:
    """As constantes de volume do gerador, por AST — ver o cabecalho."""
    alvo = {c for c in CONJUNTOS.values() if c}
    achadas: dict[str, int] = {}
    for no in ast.parse(fonte).body:
        if not isinstance(no, ast.Assign) or len(no.targets) != 1:
            continue
        nome = no.targets[0]
        if isinstance(nome, ast.Name) and nome.id in alvo:
            if isinstance(no.value, ast.Constant) and isinstance(no.value.value, int):
                achadas[nome.id] = no.value.value
    return achadas


def verifica(da_spec: dict[str, str], do_codigo: dict[str, int]) -> list[str]:
    """As quatro direcoes. Por parametro, para a prova negativa injetar."""
    problemas: list[str] = []

    if not da_spec:
        problemas.append(
            "a tabela de `02` §6.1 nao foi lida: zero conjuntos. Ou a secao mudou "
            "de forma, ou o parser parou de casar — e nos dois casos as outras "
            "direcoes passariam por VACUIDADE, que e a degradacao que esta "
            "checagem existe para nao ter."
        )
        return problemas

    for nome, volume in sorted(da_spec.items()):
        if nome not in CONJUNTOS:
            problemas.append(
                f"`02` §6.1 tem o conjunto {nome!r} e o registro deste verificador "
                "nao o conhece. Conjunto novo na spec sem par declarado e o "
                "gerador ficando para tras sem nada acusar."
            )
            continue
        constante = CONJUNTOS[nome]
        if constante is None:
            continue  # `Legitimos normais` — "milhares", e parametro de `Escala`
        if constante not in do_codigo:
            problemas.append(
                f"`02` §6.1 pede {volume} para {nome!r}, e o gerador nao declara a "
                f"constante `{constante}`."
            )
        elif str(do_codigo[constante]) != volume:
            problemas.append(
                f"{nome!r}: `02` §6.1 diz {volume} e `dataset.{constante}` diz "
                f"{do_codigo[constante]}.\n"
                "    A spec e a autoridade. Trocar a constante mantem o teste "
                "verde e faz o `GM_NOTES` gerado descrever um exercicio diferente "
                "do que `02` §6.1 descreve."
            )

    esperadas = {c for c in CONJUNTOS.values() if c}
    for orfa in sorted(esperadas - set(do_codigo)):
        if not any(orfa == CONJUNTOS.get(n) for n in da_spec):
            problemas.append(
                f"o registro espera a constante `{orfa}` e o gerador nao a tem."
            )
    for sobrando in sorted(set(do_codigo) - esperadas):
        problemas.append(
            f"`dataset.{sobrando}` e constante de volume sem linha na tabela de "
            "`02` §6.1. Volume que o gerador planta e a spec nao pede e conjunto "
            "que ninguem declarou."
        )

    return problemas


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    da_spec = volumes_da_spec(SPEC.read_text(encoding="utf-8"))
    do_codigo = constantes(GERADOR.read_text(encoding="utf-8"))
    problemas = verifica(da_spec, do_codigo)

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    pares = ", ".join(
        f"{c}={do_codigo[c]}" for n, c in CONJUNTOS.items() if c and c in do_codigo
    )
    print(
        f"{RULE}: {len(da_spec)} conjuntos na spec, {len(do_codigo)} constantes — "
        f"{pares}.\n"
        "  `Legitimos normais` nao tem constante por decisao: `02` §6.1 lhe da "
        "\"milhares\", e o volume dele e parametro de `Escala`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
