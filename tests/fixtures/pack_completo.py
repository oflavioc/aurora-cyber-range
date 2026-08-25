"""O ponto ÚNICO de montagem de um pack COMPLETO para teste, demo e container.

POR QUE ELE EXISTE — B1 DA AUDITORIA DA FASE 6
-----------------------------------------------
`tests/fixtures/pack_minimo/` **afirma ser o que não é**. Ele carrega
`injects.yaml`, e por `contracts/scenario.schema.v2.yaml`
(`x-aurora-registry.package_files.required_for_complete_pack`) um pacote com
injects é um pacote **completo** — que exige `ground_truth.yaml` e
`objectives.yaml`. Ele não tem o primeiro.

Enquanto `required_for_complete_pack` era prosa citada em docstring, ninguém
podia acusar isso. O B1 tornou o registro executável, e a fixture inconsistente
apareceu.

**A colisão não é entre duas normas.** `05` §6 proíbe versionar
`ground_truth.yaml` — é o gabarito, e o repositório é público — e o contrato
exige o documento do pacote completo. As duas continuam valendo inteiras: o que
estava errado era a fixture, que se apresentava como pacote completo sem o ser.
Materializar corrige a **fixture**, e não a norma.

**Nenhuma exceção foi aberta em `check_gabarito_fora_do_git.py`**, e não podia
ser: o cabeçalho dele registra que a direção (a) é sem exceção porque
`.gitignore` é convenção que `git add -f` atravessa, e que a mesma afirmação
falsa já apareceu em quatro lugares. Exceção por caminho é a forma que o próprio
verificador recusa.

UM HELPER, UM PONTO DE MONTAGEM
--------------------------------
Os sete sítios que precisam de um pacote completo chamam **este** — quatro
módulos de teste, dois scripts e o `docker-compose.yml` (por caminho
materializado). Sete materializações locais divergiriam, e é a classe D4: o
mesmo argumento que fez `PREFIXO_DO_VENV` ser constante única em vez de duas
listas de sufixos.

O SINTÉTICO NASCE FORA DO GIT, E O HELPER RECUSA O CONTRÁRIO
--------------------------------------------------------------
Sem destino, ele materializa em **diretório temporário**. Com destino — o caso do
container, que precisa de caminho fixo para montar —, ele **recusa alto** se o
alvo for versionado, perguntando ao próprio `git`. Um helper que pudesse gravar
gabarito em caminho rastreado seria um mecanismo que contorna a norma que diz
respeitar.

COMPORTAMENTO EM FALHA: RUIDOSO, NUNCA SILENCIOSO
---------------------------------------------------
`scripts/demo_fase2.py` roda no CI, então esta materialização está em **caminho
de gate**. Toda falha de ambiente — `git` ausente, destino não gravável, fixture
incompleta — levanta `MaterializacaoFalhou` com o motivo nomeado.

Degradar para "segue sem o gabarito" produziria exatamente o pacote incompleto
que o B1 fechou, e o gate ficaria verde sobre ele. É a P2-19 aplicada aqui:
degradar é decisão, degradar em silêncio é defeito.

O GABARITO SINTÉTICO NÃO É GABARITO DE NADA
---------------------------------------------
Ele declara um fato e os dois predicados de verificação que `03` §3.1 exige, sobre
as flags que o próprio `pack_minimo` move. Não há Linha B, não há caso, não há
`RANDOM_SEED` — não existe exercício do qual isto seja a resposta. É por isso que
gerá-lo em runtime não recria o problema que `05` §6 fecha; e é por isso, também,
que ele continua fora do Git.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from range_core.engine import destino as destino_de_pack

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MINIMO = REPO_ROOT / "tests" / "fixtures" / "pack_minimo"

#: O nome do documento que falta à fixture. Ele é o proibido de `05` §6 — e é
#: por isso que este módulo existe em vez de o arquivo estar ali do lado.
GABARITO = "ground_truth.yaml"

#: Os arquivos que a fixture versionada traz, e que são copiados verbatim.
#: Lista derivada do diretório, e não escrita aqui: arquivo novo na fixture entra
#: sem que ninguém precise lembrar de o acrescentar em dois lugares.
def _versionados_da_fixture() -> list[Path]:
    return sorted(p for p in MINIMO.iterdir() if p.is_file())


class MaterializacaoFalhou(RuntimeError):
    """O pacote completo não pôde ser montado. Falha ALTO — ver o cabeçalho."""


def materializa(destino: Path | str | None = None) -> Path:
    """Um pacote COMPLETO em disco. Devolve o diretório.

    Sem `destino`, em temporário — o caso de teste e de demo. Com `destino`, no
    caminho pedido, que **não pode ser versionado**: é o caso do container, que
    monta por caminho fixo.

    O chamador é dono do temporário: este módulo não o remove, porque o teste que
    falha precisa poder olhar o que foi montado.
    """
    if not MINIMO.is_dir():
        raise MaterializacaoFalhou(
            f"a fixture {MINIMO} nao existe. Sem ela nao ha o que completar."
        )

    alvo = Path(destino) if destino is not None else Path(
        tempfile.mkdtemp(prefix="aurora-pack-completo-")
    )

    # A GUARDA MOROU AQUI E MUDOU DE CASA. Ela é a mesma que o produtor de pack
    # usa (`range-cli scenario materialize`), e produção não importa de `tests/`
    # — então ela foi para `range-core/engine/destino.py`, e este módulo passou a
    # USÁ-LA. Manter uma cópia aqui seria a D4 dentro do exato mecanismo que
    # existe para o gabarito não nascer no lugar errado.
    #
    # O TIPO DO ERRO CONTINUA SENDO O DESTE MÓDULO, e a tradução é deliberada:
    # sete sítios tratam `MaterializacaoFalhou`, e trocar a exceção faria a
    # mudança de casa vazar para lugares que nada têm com ela. A MENSAGEM é a de
    # lá — continua havendo uma só, que é o ponto da migração.
    try:
        destino_de_pack.recusa_se_versionado(alvo)
    except destino_de_pack.DestinoInvalido as erro:
        raise MaterializacaoFalhou(str(erro)) from erro

    try:
        alvo.mkdir(parents=True, exist_ok=True)
        for arquivo in _versionados_da_fixture():
            shutil.copy2(arquivo, alvo / arquivo.name)
        (alvo / GABARITO).write_text(_gabarito_sintetico(), encoding="utf-8")
    except OSError as erro:
        raise MaterializacaoFalhou(
            f"nao foi possivel montar o pacote completo em {alvo}: {erro}"
        ) from erro

    return alvo


def _flag_que_a_fixture_move() -> str:
    """A flag que o primeiro inject da fixture liga — DERIVADA, não escrita.

    Duas razões, e as duas importam. **Invariante 2:** nome de flag literal em
    código é proibido fora dos geradores de constante, e `tests/` é varrido.
    **Fidelidade:** folha de predicado apontando para flag que a fixture não move
    faria o pacote validar e o avaliador nunca sair de *"não verificado"* — o
    predicado nasceria vazio, que é a forma do defeito que a P6-2 corrigiu na
    spec.

    Lê `injects.yaml` da própria fixture, que é a fonte de quem move o quê.
    """
    # O PARSER DO LOADER, e não o estrito de `tools/_common.py`. Medido: o
    # estrito recusa escalar multilinha, e `injects.yaml` usa `>-` na descrição
    # do facilitador — forma legítima de pack. Aplicar ali o parser dos contratos
    # seria exigir do pack a disciplina que só os contratos têm.
    from range_core.engine.loader import contract_source

    documento = contract_source.parse_document(MINIMO / "injects.yaml") or {}
    for inject in documento.get("injects") or []:
        for flag, valor in (inject.get("effects") or {}).items():
            if valor is True:
                return str(flag)
    raise MaterializacaoFalhou(
        f"nenhum inject de {MINIMO / 'injects.yaml'} liga uma flag. O predicado "
        "de contencao nao teria folha, e o pacote validaria com um predicado que "
        "nunca passa a valer."
    )


def _gabarito_sintetico() -> str:
    """O `ground_truth.yaml` mínimo que `ground_truth.schema.yaml` aceita.

    `facts` e `verification_predicates` são os dois `required` do contrato, e os
    predicados são os dois que `03` §3.1 nomeia. `service_restoration` usa
    `not_applicable` — a D5 da Fase 1 — porque a fixture não modela restauração,
    e um predicado trivialmente satisfeito seria pior que ausente: viraria
    métrica que sempre zera.

    NÃO HÁ `line_b_cases`: o contrato os declara opcionais, e inventar casos aqui
    seria escrever gabarito de um exercício que não existe.

    A CONTENÇÃO USA A FORMA NORMATIVA de `03` §3.1 — `absence_of` com
    `since: self` — e não uma que a evite. A fixture do pacote completo é o
    pack que o loader carrega nos testes de carga: se ela contornar a forma que
    a spec escreve, a guarda de `since` fica provada só contra árvores montadas
    à mão, e a forma que o exercício real usa nunca atravessa o loader. Era o
    ponto do H1 da quarta auditoria — a divergência sobreviveu a 684 testes
    verdes porque nenhum deles exercitava o campo.
    """
    flag = _flag_que_a_fixture_move()
    return (
        "# GERADO EM RUNTIME por tests/fixtures/pack_completo.py — NAO VERSIONE.\n"
        "#\n"
        "# `05` secao 6 poe `ground_truth.yaml` fora do repositorio publico. Este\n"
        "# arquivo existe porque um pacote COMPLETO exige o documento, e a\n"
        "# fixture versionada nao pode traze-lo. Ele nao e gabarito de exercicio\n"
        "# nenhum: nao ha Linha B, nao ha caso, nao ha `RANDOM_SEED`.\n"
        "facts:\n"
        "  - fact_id: GT-FIXTURE-001\n"
        "    fact_class: exfiltration\n"
        "    exercise_time: 'T+00:05'\n"
        "verification_predicates:\n"
        "  containment:\n"
        "    all:\n"
        f"      - flag_false: {flag}\n"
        "      - absence_of:\n"
        "          fact_class: exfiltration\n"
        "          since: self\n"
        "  service_restoration:\n"
        "    not_applicable: 'A fixture nao modela restauracao de servico.'\n"
    )


# ---------------------------------------------------------------------------
# CLI — o caso do CONTAINER.
#
# `docker-compose.yml` monta o pack por VOLUME (D13: trocar de cenario nao pode
# exigir reconstruir a imagem), e volume exige CAMINHO FIXO em disco antes de o
# container subir. Temporario aleatorio nao serve.
#
# O destino fica coberto pelo `.gitignore`, e a guarda de `_e_versionado`
# continua valendo: ela pergunta ao `git`, e nao a uma lista. Se alguem apontar
# este CLI para caminho rastreado, ele RECUSA.
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 2:
        print(f"uso: {sys.argv[0]} <destino>", file=sys.stderr)
        raise SystemExit(2)
    try:
        print(materializa(sys.argv[1]))
    except MaterializacaoFalhou as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        raise SystemExit(1) from erro
