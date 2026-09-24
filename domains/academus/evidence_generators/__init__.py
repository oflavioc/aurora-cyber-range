"""Os geradores de evidencia do ACADEMUS — as quatro fontes de `08` §3.

O QUE ESTE PACOTE E
===================
A metade de DOMINIO do evidence-simulator. O motor (`range-core/evidence/`) sabe
projetar, validar elenco e montar manifesto, e **nao conhece formato de fio**;
aqui mora o como de cada fonte.

    email            rfc5322       phishing de recadastramento (origem da Linha A)
    vpn              syslog_text   autenticacao sem MFA, horario anomalo
    identity_audit   jsonl         conta de servico, sessao, escalada
    database_audit   jsonl         leitura em massa (A) e alteracao de nota (B)
    cef              cef_syslog    a mesma realidade em formato de SIEM

As quatro primeiras sao `08` §3. **`cef` esta aqui porque o gabarito o
declara**: os fatos da Linha A trazem `projections: [..., "cef"]` desde a P7-10,
e o motor recusa por falha fechada a cobertura que pede fonte sem gerador — um
pacote que parasse nas quatro nao projetaria o proprio gabarito do projeto.

O QUE `cef` AQUI NAO E: o telemetry-forwarder. O item 4 da DoD tem duas metades
— o ARQUIVO, que e esta, e `telemetry_emitted` indo para o event store, que e a
outra. As duas compartilham `range_core.telemetry.forwarder.programar`, e e isso
que `08` §2 quer dizer com *"um contrato so"*: nao dois geradores coerentes, e
sim UM produtor de payload com dois renderizadores. Ate o H1 da segunda
auditoria eram dois, e ja divergiam — ver o cabecalho de `cef.py`.

    precursor        jsonl         o sinal fraco que antecede o incidente

`precursor` entrou na peca 4 — e o item 3, e `08` §2 e explicito sobre ele:
*"deixa de ser artefato autoral: e GERADO como projecao"*. Ele e a unica fonte
que **omite** um campo de proposito (`actor`): atribuicao e o achado do
exercicio, nao o insumo. Ver o cabecalho de `precursor.py`.

O CONTRATO DE UM GERADOR E MINIMO, E DE PROPOSITO
==================================================
    gerar(fatos: Sequence[Mapping]) -> str      # o CORPO, sem banner

Ele recebe os fatos **ja filtrados pela cobertura e ordenados**, e devolve
texto. Nao recebe o ground truth, nao recebe o elenco, e nao escreve arquivo.

As tres ausencias sao o desenho do insumo tipado de `00` §3.2 — *nao ter por
onde buscar mais do que lhe foi dado*. Um gerador com o ground truth na mao
poderia projetar o fato invisivel, e a regra de `08` §2 passaria a depender de
ele se lembrar de nao fazer isso.

**O banner nao e responsabilidade daqui**, pela mesma razao: `05` §4 vale para
todo arquivo, e deixar cada gerador escreve-lo faria a norma depender de quatro
lembrancas em vez de uma.

NENHUM GERADOR INVENTA ENTIDADE, E QUEM IMPOE ISSO E O MOTOR
=============================================================
Todo valor escrito sai de um campo do fato. Onde um rotulo de host e necessario
— o dominio do link no `.eml` —, ele **deriva** de um valor do elenco em vez de
ser escrito a mao; ver o cabecalho de `email.py`, que e onde essa fresta do
item 1 fica fechada.
"""

from __future__ import annotations

from collections.abc import Callable

__all__ = ["geradores"]


def geradores(contratos: dict[str, dict]) -> dict[str, Callable]:
    """`fonte -> gerador`, a tabela que o motor recebe por injecao.

    **Fabrica, e nao constante de modulo**, porque `cef` precisa de um insumo do
    contrato (`05` §5.1 — vendor/product ficticios) e le-lo no import seria
    efeito colateral de importacao (R9 §1). Uma tabela pronta para quatro
    fontes e uma fabrica para a quinta seriam duas formas para a mesma coisa.

    AS CHAVES SAO AS FONTES DO CONTRATO (`x-aurora-registry.source_formats`), e
    o teste cruza as duas listas: um gerador para fonte que o contrato nao
    conhece escreveria arquivo que o manifesto nao sabe declarar.

    OS SUBMODULOS SAO RESOLVIDOS POR `import_module`, NA CHAMADA, e isso tem
    duas razoes que coincidem:

    1. **R9 §1** — nada executa na importacao do pacote;
    2. **a prova negativa depende disso.** `from domains.academus.
       evidence_generators import cef` resolve pelo ATRIBUTO do pacote, e o
       harness de mutacao substitui `sys.modules` — o atributo nao acompanha.
       Medido: as mutacoes em `cef` e em `jsonl` nao derrubavam teste nenhum.
       `import_module` consulta `sys.modules` primeiro, entao cada nome vem do
       modulo corrente, mutado ou nao.

       E o pacote NAO pode ser mutado ele mesmo: o harness carrega o arquivo
       como modulo avulso, sem `__path__`, e um `from <pacote> import cef` ali
       dentro falharia. Resolver por `import_module` dispensa muta-lo.
    """
    from importlib import import_module

    from domains.academus.telemetria import catalogo
    from range_core.engine.loader.contract_source import restricoes_de_evidencia

    def _modulo(nome: str):
        return import_module(f"{__name__}.{nome}")

    restricoes = restricoes_de_evidencia(contratos)
    return {
        "email": _modulo("email").gerar,
        "vpn": _modulo("vpn").gerar,
        "identity_audit": _modulo("identity_audit").gerar,
        "database_audit": _modulo("database_audit").gerar,
        "precursor": _modulo("precursor").gerar,
        # O CATALOGO ENTRA AQUI, e e o H1 da segunda auditoria: o `cef.log` e o
        # `telemetry_emitted` passam a sair de `programar`, com o MESMO
        # catalogo de `02` §10. Antes este gerador tinha mapeamento proprio, e
        # as duas saidas ja nasceram divergentes para o mesmo fato.
        "cef": _modulo("cef").fabricar(
            restricoes["cef_vendor"],
            restricoes["cef_product"],
            catalogo=catalogo(contratos),
        ),
    }
