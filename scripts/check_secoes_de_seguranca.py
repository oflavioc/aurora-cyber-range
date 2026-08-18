#!/usr/bin/env python3
"""P4-12 — toda secao de `05_SECURITY_REQUIREMENTS.md` tem mecanismo OU destinatario.

O QUE ESTA CHECAGEM EXISTE PARA FECHAR
---------------------------------------
`05` §4 atravessou sete pecas da Fase 4 sem ser lida **porque nada apontava para
ela**. Isso foi consertado para as telas, com `check_banner_de_simulacao.py`. O
que nao foi consertado e a PROPRIEDADE: uma secao normativa pode existir sem
verificador, sem gatilho de leitura e **sem nada declarando que a ausencia e
deliberada**. A unica coisa que distinguiu a §4 foi uma fase ter produzido o
artefato que ela governa e um auditor ter olhado.

Isto nao e um gate que exija verificador para toda secao — cobrar mecanismo
antes de existir o artefato e o erro que a §7.3 do registro da Fase 3 nomeia. **O
que se cobra e a DECLARACAO.** Uma secao pode estar sem mecanismo, desde que o
registro diga qual fase o traz e por que ainda nao ha.

"NOMEADA" E MAIS GROSSO QUE "COBERTA", E A MEDICAO MUDOU O NUMERO
------------------------------------------------------------------
A P4-12 contou **cinco** secoes nomeadas por algum verificador (§1, §3, §4, §6,
§8) e **tres** sem ninguem (§2, §5, §7). Medido pelo universo abaixo, sao
**quatro e quatro**: a §6 nao e citada por verificador nenhum.

O que sustentava a contagem da §6 eram duas citacoes que nao sao escopo de
verificador — um comentario do `.github/workflows/invariants.yml` dizendo que o
`.gitignore` executa a secao, e um comentario de `contracts/ground_truth.schema.
yaml`. Nenhum dos dois e um verificador que varra a arvore procurando violacao da
§6, e nenhum dos dois fica vermelho quando ela e violada.

**A diferenca apareceu exatamente na clausula que a fase nova estreia** — *"`GM_
NOTES.md` e `ground_truth.yaml` excluidos do build servido aos participantes"* —,
que e a mesma forma do que aconteceu com a §4 na Fase 4, com outro digito.

O UNIVERSO, E POR QUE ELE E ESTE
---------------------------------
`verificador` aqui e o que o proprio repositorio ja chama assim: `tools/*.py` e
`scripts/check_*.py`, que e o conjunto que `check_readme_atual.py` conta e o
README publica. Nao foi inventado para esta checagem — usar uma definicao propria
seria escolher o universo que produz a resposta desejada.

**Citacao em artefato nao entra**, e o limite e declarado: migration, compose,
schema de contrato e comentario de workflow citam secoes de `05` o tempo todo, e
citacao nao e verificacao. Uma migration que diz *"nao ha `REVOKE` aqui; isso e
`05` §7, Fase 5"* cita a secao para dizer que NAO a implementa — conta-la como
cobertura inverteria o sentido da frase.

Um mecanismo declarado em `MECANISMOS` **pode** morar fora do universo, e a §2 e
a §5 sao o caso: quem fecha anexo em evidencia e o proprio contrato
(`contracts/evidence.schema.yaml`), cujos exemplos negativos sao executados por
`check_contract_examples.py`. O que a direcao (c) cobra desse caminho e que ele
exista, seja versionado e cite a secao. **O elo "e o CI executa aquele contrato"
nao e mecanizado aqui**, e esse limite esta dito em vez de suposto.

AS CINCO DIRECOES
-----------------
    (a) secao em `05` sem entrada no registro                    -> REPROVA
    (b) entrada para secao que `05` nao tem, ou com titulo que
        divergiu do da spec                                      -> REPROVA
    (c) mecanismo declarado que nao existe, nao e versionado
        ou nao cita a secao                                      -> REPROVA
    (d) verificador do universo que cita a secao e NAO esta
        declarado como mecanismo dela                            -> REPROVA
    (e) entrada sem mecanismo e sem destinatario, ou com
        destinatario apontando para fase que `07` nao tem        -> REPROVA

A (d) e a terceira direcao de `api_surface.yaml` aplicada aqui, e e ela que
impede `destinatario` de virar esconderijo: no dia em que um verificador citar a
§6, a entrada que ainda disser "Fase 5, planejada" fica vermelha e cobra a
promocao. E a (b) impede o registro de envelhecer afirmando uma secao que a spec
renomeou ou removeu.

O UNIVERSO E O QUE O `git` VE, E ISSO TEM UM LIMITE MEDIDO
------------------------------------------------------------
`_git_ls` lista arquivos **versionados**. Um verificador novo que exista apenas
na arvore de trabalho e INVISIVEL para a direcao (d): ele cita a secao, e o
registro nao e cobrado a promover a entrada.

Medido na peca 3 da Fase 5, ao exercer a (d) pela primeira vez:
`check_trilha_de_auditoria.py` recem-escrito nao disparou nada; **um `git add -N`
depois, disparou** com a mensagem da promocao.

**Nao e defeito a corrigir, e sim escopo a declarar.** Arquivo nao versionado nao
roda no CI de ninguem, entao trata-lo como mecanismo seria o registro afirmar
cobertura que nao existe em lugar nenhum. O que a medicao muda e o PROCEDIMENTO:
quem escreve verificador novo o adiciona ao indice antes de rodar a checagem —
no commit, isso e automatico, e no CI a arvore ja esta commitada.

ESTA CHECAGEM SE EXCLUI DO PROPRIO UNIVERSO, e a exclusao e necessaria
-----------------------------------------------------------------------
Ela cita as oito secoes por construcao — e o registro. Sem a exclusao, a direcao
(d) exigiria que cada entrada declarasse este arquivo como mecanismo de si mesma,
e o registro passaria a afirmar que ele proprio executa `05`. Ele nao executa:
**declara**. O `_probes.py` sai pelo mesmo motivo.

Stdlib pura, roda no job `arquitetura`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "spec" / "05_SECURITY_REQUIREMENTS.md"
FASES = REPO_ROOT / "docs" / "spec" / "07_IMPLEMENTATION_PHASES.md"

RULE = "P4-12 - secao de 05_SECURITY_REQUIREMENTS com mecanismo ou destinatario"

#: `## 4. Banner obrigatorio` — o numero e o titulo, como a spec os escreve.
SECAO_DA_SPEC = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)

#: `| 5 | Modelo de dados completo ... |` — a tabela de visao geral de `07`.
FASE_DE_07 = re.compile(r"^\|\s*(\d+)\s*\|", re.M)

#: `05 secao 6`, `05_SECURITY_REQUIREMENTS.md §7`, ``05` §4`, `05 secao 5.1`.
#:
#: O `(?<![0-9])` impede que `2005 secao 3` case. A subsecao e capturada e
#: DESCARTADA: `05` §5.1 e citacao da §5, e tratar as duas como coisas
#: diferentes faria a §5 parecer nao citada por quem cita a metade dela.
CITACAO = re.compile(
    r"(?<![0-9])05(?:_SECURITY_REQUIREMENTS(?:\.md)?)?[^A-Za-z0-9]{0,4}"
    r"(?:secao|seção|§)\s*(\d+)(?:\.\d+)?",
    re.I,
)

#: O universo de verificadores. Os mesmos pathspecs que `check_readme_atual.py`
#: conta e que o README publica — nao uma definicao propria desta checagem.
UNIVERSO = ("tools/*.py", "scripts/check_*.py")

#: Fora do universo, e a exclusao esta justificada no cabecalho: este arquivo
#: DECLARA as oito secoes, nao as executa.
AUTOEXCLUSAO = (
    "scripts/check_secoes_de_seguranca.py",
    "scripts/check_secoes_de_seguranca_probes.py",
)


@dataclass(frozen=True, slots=True)
class Entrada:
    """O que o registro afirma sobre uma secao de `05`.

    `titulo` e afirmacao sobre a spec, e por isso e conferido contra ela: secao
    renomeada obriga a reler a entrada, em vez de deixa-la apontando para uma
    norma que mudou de assunto.

    `mecanismos` e `destinatario` podem coexistir — cobertura parcial e o estado
    real da §2 e da §5, e um registro que so admitisse "coberta" ou "futura"
    obrigaria a mentir em uma das duas direcoes.
    """

    titulo: str
    mecanismos: tuple[str, ...]
    destinatario: tuple[int, str] | None
    nota: str


#: O REGISTRO. Uma entrada por secao de `05`, conferida nas cinco direcoes.
#:
#: Acrescentar mecanismo aqui e declarar que aquele arquivo executa aquela
#: secao; tirar um e declarar que deixou de executar. As duas coisas ficam no
#: diff, que e o ponto — hoje elas nao ficavam em lugar nenhum.
MECANISMOS: dict[int, Entrada] = {
    1: Entrada(
        titulo="Código proibido",
        mecanismos=("tools/check_security_constraints.py",),
        destinatario=None,
        nota="varre a arvore por comportamento ofensivo, sem proibir import de "
        "biblioteca criptografica por si so — `06` T15",
    ),
    2: Entrada(
        titulo="Evidências sintéticas",
        mecanismos=("contracts/evidence.schema.yaml",),
        destinatario=(
            9,
            "o evidence-simulator e `08` sao da Fase 9, e e la que existe gerador "
            "produzindo arquivo de evidencia para varrer. Hoje `scenarios/` esta "
            "vazio: um verificador de conteudo de evidencia nao teria sujeito",
        ),
        nota="COBERTURA PARCIAL, e a parte coberta e a que ja tem sujeito: o "
        "contrato fecha anexo, binario e macro por `additionalProperties: false`, "
        "e o exemplo negativo `anexo em evidencia: proibido por 05 secao 2` e "
        "executado por `check_contract_examples.py`. O que falta e a varredura do "
        "ARQUIVO gerado, que a Fase 9 traz",
    ),
    3: Entrada(
        titulo="Dados",
        mecanismos=(
            "tools/check_synthetic_data.py",
            "scripts/check_contract_examples.py",
            "scripts/check_spec_examples.py",
        ),
        destinatario=None,
        nota="tres arquivos, e nao um: o primeiro varre o dado, o segundo cruza as "
        "faixas do contrato contra as do primeiro (elas ja divergiram duas vezes) "
        "e o terceiro valida o exemplo normativo da propria secao",
    ),
    4: Entrada(
        titulo="Banner obrigatório",
        mecanismos=(
            "scripts/check_banner_de_simulacao.py",
            "scripts/check_banner_de_simulacao_probes.py",
        ),
        destinatario=None,
        nota="o texto do banner e extraido da spec e comparado letra por letra; o "
        "registro de classes (telas / evidencia / exportacao / relatorio) e "
        "conferido nas duas direcoes, e e o precedente de forma desta checagem",
    ),
    5: Entrada(
        titulo="Identificação de fornecedores e de atores de ameaça",
        mecanismos=(
            "contracts/ground_truth.schema.yaml",
            "contracts/scenario.schema.v2.yaml",
        ),
        destinatario=(
            7,
            "a §5.2 exige fonte publica citavel declarada em `ground_truth.yaml`, e "
            "o primeiro pack e da Fase 7. Sem pack nao ha ator declarado a conferir",
        ),
        nota="COBERTURA PARCIAL: os dois contratos carregam a distincao da §5.1 "
        "(fornecedor de produto sempre ficticio) e a forma do bloco `threat_actor` "
        "da §5.2. O que falta e verificador que confira o ator DECLARADO contra as "
        "exigencias da §5.2 — fonte citavel, TTP nao excedida, IOC ausente",
    ),
    6: Entrada(
        titulo="Deploy",
        mecanismos=("scripts/check_gabarito_fora_do_git.py",),
        destinatario=(
            12,
            "PROMOVIDA PELA METADE, e a metade que falta esta nomeada. O que a "
            "peca 5 da Fase 5 cobriu e a clausula de EXCLUSAO — `GM_NOTES.md` e "
            "`ground_truth.yaml` fora do repositorio e do build de participante. "
            "As outras quatro clausulas de `05` §6 — bind em `127.0.0.1`, acesso "
            "por tunel, nenhuma porta publicada em producao, destino syslog "
            "configuravel — seguem sem verificador, porque nenhuma fase de `07` "
            "produz o deploy que elas governam. A Fase 12 e a que traz "
            "observabilidade e documentacao, e e a candidata; a decisao e de la",
        ),
        nota="A CLAUSULA DE DEPLOY DESTA SECAO CARREGA O GATILHO DA P5-3, e e por "
        "isso que ele esta aqui e nao so na pendencia: `07` nao tem fase de "
        "deploy, entao nao ha item de DoD que o cobre, e prazo que ninguem ve na "
        "hora vence sozinho. O primeiro deploy destinado a exercicio com "
        "participante real precisa de credencial propria para a `academus-api` — "
        "sem ela, `REVOKE` nao alcanca a role que conecta. "
        "A SECAO QUE A P4-12 CONTOU COMO COBERTA E QUE A MEDICAO DERRUBOU. As "
        "duas citacoes que sustentavam a contagem sao comentarios — um do workflow, "
        "outro de `contracts/ground_truth.schema.yaml` — e nenhum dos dois fica "
        "vermelho quando a secao e violada. `.gitignore` e convencao: `git add -f` "
        "a atravessa, e e por isso que a peca 5 traz mecanismo e nao so a linha",
    ),
    7: Entrada(
        titulo="Integridade da trilha de auditoria",
        mecanismos=("scripts/check_trilha_de_auditoria.py",),
        destinatario=None,
        nota="PROMOVIDA na peca 3 da Fase 5, e a promocao foi COBRADA pela direcao "
        "(d) em vez de lembrada: com o verificador escrito e a entrada ainda "
        "dizendo 'sem mecanismo — Fase 5', esta checagem reprovou com a mensagem "
        "da promocao. A saida vermelha esta no registro da fase. Antes disso, as "
        "unicas citacoes da secao eram de migration — e uma delas a citava para "
        "dizer que NAO a implementava (`0002_business_state.py`: *nao ha `REVOKE`, "
        "role `INSERT`-only nem trigger; isso e Fase 5*). Contar aquilo como "
        "cobertura inverteria o sentido da frase",
    ),
    8: Entrada(
        titulo="Autenticação",
        mecanismos=(
            "scripts/check_api_surface.py",
            "scripts/check_telas_sem_vocabulario.py",
        ),
        destinatario=None,
        nota="a lista de excecao da secao e fechada pelo preambulo, e o verificador "
        "de superficie a aplica: caminho nao declarado como publico exige token por "
        "falha fechada. Foi a P4-9, que virou `spec-change` em vez de decisao de fase",
    ),
}


def _tolera_terminal_estreito() -> None:
    """A §8.4 da Fase 4, aplicada antes de custar uma rodada — e nao depois.

    Os titulos das secoes vem da spec em portugues, e as mensagens daqui citam
    `§`. Num terminal em `cp1252` isso sai como `UnicodeEncodeError` e rc=1
    SOBRE ARVORE LIMPA, e um verificador que morre nao diz "reprovou": ele nao
    diz nada. Perder um glifo e o custo; perder a saida inteira nao se compara.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")


def _git_ls(*pathspecs: str) -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", "--", *pathspecs],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return [linha for linha in saida.stdout.splitlines() if linha]


def secoes_da_spec(texto: str) -> dict[int, str]:
    """`{numero: titulo}` das secoes de `05`, lidas da propria spec."""
    return {int(n): titulo for n, titulo in SECAO_DA_SPEC.findall(texto)}


def fases_de_07(texto: str) -> set[int]:
    """Os numeros de fase que `07` declara, lidos da tabela de visao geral."""
    return {int(n) for n in FASE_DE_07.findall(texto)}


def citacoes(texto: str) -> set[int]:
    """As secoes de `05` que um texto cita. Subsecao conta pela secao-mae."""
    return {int(n) for n in CITACAO.findall(texto)}


def verifica(
    secoes: dict[int, str],
    registro: dict[int, Entrada],
    citado_por: dict[str, set[int]],
    versionados: set[str],
    universo: set[str],
    fases: set[int],
) -> list[str]:
    """As cinco direcoes. Tudo entra por parametro para a prova negativa poder
    injetar estado que nao existe na arvore."""
    problemas: list[str] = []

    # (a) secao da spec sem entrada.
    for numero in sorted(secoes):
        if numero not in registro:
            problemas.append(
                f"`05` §{numero} ({secoes[numero]}) nao tem entrada em "
                f"{Path(__file__).name}. Secao normativa sem entrada e exatamente o "
                "estado em que a §4 passou sete pecas: sem gate, sem gatilho de "
                "leitura e sem nada dizendo que a ausencia e deliberada."
            )

    for numero in sorted(registro):
        entrada = registro[numero]

        # (b) entrada para secao que a spec nao tem, ou titulo que divergiu.
        if numero not in secoes:
            problemas.append(
                f"o registro tem entrada para `05` §{numero} e a spec nao tem essa "
                "secao. Ou ela foi removida e a entrada sobrou, ou a numeracao "
                "mudou — nos dois casos a entrada afirma algo falso."
            )
            continue
        if entrada.titulo != secoes[numero]:
            problemas.append(
                f"`05` §{numero}: o registro diz {entrada.titulo!r} e a spec diz "
                f"{secoes[numero]!r}. Titulo e afirmacao sobre a spec: divergiu, a "
                "entrada precisa ser RELIDA, porque a norma pode ter mudado de "
                "assunto sob uma declaracao que continuou parecendo certa."
            )

        # (c) mecanismo declarado que nao existe, nao e versionado ou nao cita.
        for caminho in entrada.mecanismos:
            if caminho not in versionados:
                problemas.append(
                    f"`05` §{numero} declara o mecanismo {caminho}, que nao esta "
                    "versionado. Mecanismo que o `git ls-files` nao ve nao roda no "
                    "CI de ninguem."
                )
                continue
            if numero not in citado_por.get(caminho, set()):
                problemas.append(
                    f"`05` §{numero} declara {caminho} como mecanismo, e o arquivo "
                    "NAO cita a secao. Ou o mecanismo mudou de escopo, ou a "
                    "declaracao esta errada — e um mecanismo que nao sabe que "
                    "executa a secao nao a executa por acaso."
                )

        # (e) nem mecanismo nem destinatario; ou destinatario para fase inexistente.
        if not entrada.mecanismos and entrada.destinatario is None:
            problemas.append(
                f"`05` §{numero} nao tem mecanismo nem destinatario. E o estado que "
                "esta checagem existe para tornar impossivel: 'ninguem olha, e "
                "ninguem disse que isso e decisao'."
            )
        if entrada.destinatario is not None:
            fase, motivo = entrada.destinatario
            if fase not in fases:
                problemas.append(
                    f"`05` §{numero} tem destinatario Fase {fase}, e `07` nao "
                    "declara essa fase. Destinatario que aponta para fase "
                    "inexistente e prazo que nunca vence."
                )
            if not motivo.strip():
                problemas.append(
                    f"`05` §{numero} tem destinatario sem motivo. Data sem motivo e "
                    "a forma de pendencia que atravessa a fase sem ninguem "
                    "conseguir julgar se ela ainda faz sentido."
                )

    # (d) citacao no universo que o registro nao declara.
    for caminho in sorted(universo):
        for numero in sorted(citado_por.get(caminho, set())):
            entrada = registro.get(numero)
            if entrada is None:
                continue  # ja acusado por (a)
            if caminho not in entrada.mecanismos:
                promocao = (
                    " A entrada diz que a secao espera a Fase "
                    f"{entrada.destinatario[0]}, e ja ha verificador citando-a: e a "
                    "promocao que esta faltando."
                    if not entrada.mecanismos and entrada.destinatario
                    else ""
                )
                problemas.append(
                    f"{caminho} cita `05` §{numero} e nao esta declarado como "
                    f"mecanismo dela.{promocao} Verificador que executa uma secao "
                    "sem constar do registro faz o registro subestimar a cobertura "
                    "— que e a direcao em que ele mente sem que nada acuse."
                )

    return problemas


def estado(registro: dict[int, Entrada]) -> tuple[int, int]:
    com = sum(1 for e in registro.values() if e.mecanismos)
    return com, len(registro) - com


def main(argv: list[str] | None = None) -> int:
    _tolera_terminal_estreito()
    texto_spec = SPEC.read_text(encoding="utf-8")
    secoes = secoes_da_spec(texto_spec)
    if not secoes:
        print(
            f"{RULE}: nao achei nenhuma secao em {SPEC.name}. A forma dos "
            "cabecalhos mudou, e este verificador precisa acompanhar — sem isso "
            "ele aprovaria qualquer registro por nao ver secao nenhuma.",
            file=sys.stderr,
        )
        return 2

    fases = fases_de_07(FASES.read_text(encoding="utf-8"))
    if not fases:
        print(
            f"{RULE}: nao achei nenhuma fase na tabela de {FASES.name}.",
            file=sys.stderr,
        )
        return 2

    versionados = set(_git_ls("."))
    universo = {c for c in _git_ls(*UNIVERSO) if c not in AUTOEXCLUSAO}

    alvos = universo | {
        caminho for e in MECANISMOS.values() for caminho in e.mecanismos
    }
    citado_por = {
        caminho: citacoes((REPO_ROOT / caminho).read_text(encoding="utf-8"))
        for caminho in sorted(alvos)
        if (REPO_ROOT / caminho).is_file()
    }

    problemas = verifica(
        secoes, MECANISMOS, citado_por, versionados, universo, fases
    )

    if problemas:
        print(f"{RULE}\n", file=sys.stderr)
        for problema in problemas:
            print(f"  {problema}\n", file=sys.stderr)
        return 1

    com, sem = estado(MECANISMOS)
    print(f"{RULE}: {len(secoes)} secoes, todas declaradas.")
    for numero in sorted(MECANISMOS):
        entrada = MECANISMOS[numero]
        if entrada.mecanismos:
            marca = ", ".join(Path(c).name for c in entrada.mecanismos)
            sufixo = (
                f" (+ Fase {entrada.destinatario[0]})" if entrada.destinatario else ""
            )
        else:
            marca = f"sem mecanismo — Fase {entrada.destinatario[0]}"
            sufixo = ""
        print(f"  §{numero} {entrada.titulo}: {marca}{sufixo}")
    print(
        f"\n{com} com mecanismo, {sem} declaradas sem — e nenhuma sem declaracao. "
        f"Universo conferido: {len(universo)} verificadores."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
