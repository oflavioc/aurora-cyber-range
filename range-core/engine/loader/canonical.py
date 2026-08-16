"""Forma canonica do pack, e o `content_hash` que o `exercise_started` fixa.

AUTORIDADE
----------
`04_SCENARIO_SCHEMA.md` §1 (estrutura do pacote) e §4 (versionamento);
`01_ARCHITECTURE.md` §4.1 (projecao reconstruivel do zero). A necessidade do
pino esta argumentada em `range-core/state/simulation_state.py`,
`Declarations`, e a retencao do pack antigo e a P2-8.

POR QUE O PINO EXISTE
---------------------
O pack e arquivo mutavel; o store nao e. Mesmo store com pack editado
reconstruiria um mundo diferente, EM SILENCIO, e a divergencia so apareceria no
AAR, fases adiante. `exercise_started` grava `pack_id`, `schema_version`,
`content_hash` e a etiqueta de canonicalizacao, e `project` recusa reconstruir
contra pack de hash diferente.

A ETIQUETA `v1` EXISTE PARA A REGRA PODER MUDAR
------------------------------------------------
Sem etiqueta, mudar a regra faria o mesmo nome significar outra coisa, e todo
exercicio anterior passaria a nao bater sem que nada dissesse por que. Com ela, a
recusa nomeia a etiqueta e o operador sabe que regra produziu o hash esperado.

A REGRA v1
----------
1. **Escopo** — os arquivos do pack que o CONTRATO declara como documento de
   maquina: as entradas de `x-aurora-registry.package_files` terminadas em
   `.yaml`, e apenas as presentes. Ficam de fora `GM_NOTES.md` (narrativa; nao
   alcanca resolucao), `evidence/` (gerado, fora do Git, reconstruido de ground
   truth + seed) e `media/` (nao parseado).
2. **Normalizacao** — cada arquivo e PARSEADO e reserializado em JSON
   determinista: UTF-8, chaves ordenadas, sem espaco insignificante.
   Reserializar em vez de hashear bytes evita recusa por comentario ou espaco,
   que seria recusa sem divergencia real.
3. **Concatenacao** — em ordem de caminho POSIX, com o caminho como prefixo de
   cada entrada. O prefixo importa: sem ele, mover conteudo de um arquivo para
   outro produziria o mesmo hash.
4. **SHA-256** sobre o resultado.

O ESCOPO E DERIVADO DO CONTRATO, E NAO DA VERSAO DO LOADER — decisao registrada
------------------------------------------------------------------------------
A primeira formulacao desta regra, em docstring de `simulation_state.py`, dizia
*"escopo sao os arquivos que o LOADER PARSEIA"*, com o criterio *"se o loader le,
pode mudar a resolucao; se nao le, nao pode"*.

O criterio esta certo e foi preservado; a formulacao envelheceu no dia em que
existiu um segundo loader. O da Fase 2 nao le `branches.yaml` — branching e
entregavel da Fase 7 —, e o da Fase 7 vai ler. Escopo definido pela versao do
loader faria o MESMO PACK ter hash diferente em duas fases, e todo exercicio da
Fase 2 deixaria de reconstruir na Fase 7 sem que ninguem tivesse tocado no pack.

Derivar do contrato preserva o criterio sem esse custo: `branches.yaml` E
documento de maquina — pode mudar resolucao — e por isso entra no escopo desde
agora, mesmo que so a Fase 7 o consuma.

O LIMITE, dito porque e limite
------------------------------
Arquivo `.yaml` presente no pack e AUSENTE de `package_files` nao entra no hash.
Pela regra isso e correto — documento que nenhum loader le nao muda resolucao —,
mas significa que o escopo depende de o contrato listar o que existe. Quando um
arquivo novo de pack for criado, ele entra em `package_files` no mesmo commit,
ou fica fora do pino sem que nada acuse.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

#: Etiqueta da regra vigente. Vai no payload de `exercise_started` e na mensagem
#: de recusa do fold.
CANONICALIZATION_V1 = "v1"


def scope_from_contract(scenario_contract: Mapping) -> tuple[str, ...]:
    """Os arquivos de pack que sao documento de maquina, segundo o contrato.

    Le `x-aurora-registry.package_files` — as tres listas, porque as tres
    descrevem arquivos legitimos do pacote: `required`,
    `required_for_complete_pack` e `optional`. O que separa o que entra do que
    nao entra nao e a obrigatoriedade, e o arquivo ser parseado: `GM_NOTES.md`
    e opcional e fica de fora, `manifest.yaml` e obrigatorio e entra.
    """
    registro = (scenario_contract.get("x-aurora-registry") or {}).get("package_files") or {}
    arquivos: set[str] = set()
    for grupo in registro.values():
        arquivos.update(entrada for entrada in grupo if entrada.endswith(".yaml"))
    return tuple(sorted(arquivos))


def content_hash_v1(documents: Mapping[str, Mapping]) -> str:
    """SHA-256 da forma canonica v1. `documents` e `caminho POSIX -> documento`.

    Recebe documento JA PARSEADO, e nao caminho: a funcao nao toca disco, entao
    o mesmo conteudo produz o mesmo hash independentemente de onde o pack esteja
    — e o hash de um pack recuperado do Git pode ser conferido sem escrever
    arquivo.

    `ensure_ascii=False` porque titulo e texto de plateia sao em portugues: com
    escape, o hash mudaria se a serializacao trocasse de politica de escape sem
    que o conteudo mudasse.
    """
    digest = hashlib.sha256()
    for caminho in sorted(documents):
        corpo = json.dumps(
            documents[caminho],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest.update(f"{caminho}\n{corpo}\n".encode("utf-8"))
    return digest.hexdigest()
