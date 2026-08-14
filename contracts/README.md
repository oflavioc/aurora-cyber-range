# Contratos

Os seis contratos deste diretório são **JSON Schema 2020-12**, autorados em YAML.

Decisão D4 da Fase 1, registrada em `docs/progress/fase_1.md`. A forma anterior era
YAML descritivo com vocabulário próprio (`required_fields`, `types`,
`conditional_fields`), que nenhum validador pronto lê e que obrigaria a um
interpretador escrito à mão nas Fases 2 e 7.

## Por que YAML e não JSON

Os comentários. Boa parte do valor destes arquivos é a justificativa ancorada na
spec ao lado de cada regra, e JSON não os comporta. O validador opera sobre o
documento já parseado — a sintaxe de superfície é indiferente a ele.

## Subconjunto YAML obrigatório

`tools/_common.py::parse_yaml` é um parser de subconjunto, escrito com stdlib
porque o CI da Fase 0 não pode depender da aplicação. Ele lê estes arquivos, e
por isso o subconjunto é regra de autoria, não preferência de estilo:

- mapeamentos e sequências **em bloco**; sequências em fluxo (`[a, b]`) permitidas;
- **mapeamento em fluxo (`{a: b}`) é recusado** — use bloco;
- sem âncoras, aliases, merge keys, escalares multilinha ou múltiplos documentos;
- **todo regex em aspas simples.** O parser da Fase 0 devolve o texto cru entre
  aspas, sem processar escapes; um parser YAML real processa escapes em aspas
  duplas. Em aspas simples os dois concordam, e `'\.'` é um ponto literal nos
  dois. Em aspas duplas seria `"\\."` para um e `\\.` — backslash literal — para
  o outro.

## Extensões `x-aurora-*`

JSON Schema valida **um documento contra si mesmo**. Ele não expressa integridade
referencial entre arquivos, que é onde estão as falhas caras deste projeto: um
`event_type` com erro de digitação nunca dispara, o objetivo nunca é satisfeito, e
ninguém percebe até o exercício ao vivo (`09_EVENT_MODEL.md` §4).

Essas regras vivem num conjunto **fechado** de anotações. Palavras-chave
`x-aurora-*` são ignoradas por qualquer validador JSON Schema conforme; quem as
executa é o loader de pack (Fase 2) e o `range-cli scenario validate` (Fase 7).
Nome fora deste conjunto é erro de autoria.

### Resolução de referência

`x-aurora-ref: <registro>` — todo valor string aqui deve existir no registro.

| Registro | Fonte |
|---|---|
| `event_catalog` | `contracts/events.schema.yaml`, `$defs/event_type_*` |
| `adapter_flags` | `domains/<adapter>/flags.yaml` |
| `pack_facts` | `ground_truth.yaml` do próprio pack, `facts[].fact_id` |
| `pack_objectives` | `objectives.yaml` do próprio pack |
| `pack_injects` | `injects.yaml` do próprio pack, `injects[].id` |
| `pack_decision_options` | `options[].id` do `decision_point` indicado |

Aplicável a um `string`, aos itens de um `array`, ou a `propertyNames` — nos três
casos significa a mesma coisa.

### Unicidade

`x-aurora-unique: true` — o valor deste campo é único dentro do documento.
`uniqueItems` do JSON Schema cobre itens de array inteiros; isto cobre **um campo**
de objetos dentro de um array (`fact_id`, `case_id`, `id` de inject).

### Tipagem cruzada

`x-aurora-effects-match-flag-types: true` — em `effects` de inject, cada valor
respeita o tipo declarado para aquela flag em `domains/<adapter>/flags.yaml`.
Precisa do registro de flags e do tipo declarado lá, e por isso não é expressável
em JSON Schema.

### Documentos irmãos

`x-aurora-documents` — mapeia arquivo do pack para o ponteiro que o valida, quando
um contrato governa mais de um arquivo. Só `scenario.schema.v2.yaml` usa.

### Anotações que NÃO são regra executável

Declaradas como tal, para que ninguém as leia como garantia:

- `x-aurora-linter-rules` — obrigações do `range-cli scenario lint` (Fase 7) que
  dependem de julgamento estrutural fora do alcance de schema. Prosa.
- `x-aurora-registry` / `x-aurora-security-constraints` — vocabulários e limites
  consumidos por geradores e verificadores, não por validação de instância.
- `x-aurora-contract`, `x-aurora-schema-version` — metadado de identificação.

## Exemplos

`examples` é palavra-chave padrão do JSON Schema: cada item **deve validar**.

`x-aurora-invalid-examples` é a contraparte: cada item tem `reason`, `rejected_by` e
`instance`, e a instância **deve falhar** a validação. Contrato sem exemplo negativo
não prova que recusa nada.

Duas regras de autoria, e as duas existem porque a alternativa é uma fixture que
falha pelo motivo errado e dá por provado o que não provou:

- **Instância completa com um defeito.** Instância parcial falha por campo
  obrigatório ausente, não pelo motivo que nomeia.
- **`rejected_by` nomeia quem recusa** — `schema` para JSON Schema puro, ou a
  anotação responsável (`x-aurora-ref:event_catalog`, `x-aurora-unique`, …). Um
  `event_type` com erro de digitação é uma string perfeitamente válida para o
  JSON Schema; quem o recusa é a resolução de referência. Um executor que rodasse
  só o schema marcaria essa fixture como aprovada sem ter verificado nada.

Quando um contrato governa mais de um arquivo do pack, o exemplo declara
`pointer` — o ponteiro JSON do schema contra o qual ele valida. Ausente significa
a raiz. Exemplos positivos de documentos irmãos ficam em
`x-aurora-document-examples`, com o mesmo campo; `examples` continua sendo, por
palavra-chave padrão, o exemplo da raiz.

Nada é declarado aqui se nenhuma das duas camadas o recusa. Restrição guardada
fora dos contratos — faixa de IP sintético, por exemplo, que é de
`tools/check_synthetic_data.py` — fica em `x-aurora-linter-rules`, nunca em
`x-aurora-invalid-examples`.

## Quem executa isto

`scripts/check_contract_examples.py`, no job `contratos` de
`.github/workflows/invariants.yml` — o único que instala dependência. Os jobs
`arquitetura` e `seguranca` seguem stdlib puro: o gate que a Fase 0 construiu não
depende da aplicação que ele julga.

O executor roda as **duas** camadas e cobra a correspondência com `rejected_by`.
Uma fixture que declara `x-aurora-*` mas que o schema já recusa é reprovada — ela
passaria mesmo se a regra que diz provar fosse removida.

`scripts/check_contract_examples_probes.py` prova que o executor **reprova**,
plantando defeito nos seis eixos possíveis de fixture mentirosa. Executor que
nunca falhou contra defeito plantado prova que a árvore passa, não que ele enxerga.

### Registros de fixture

`event_catalog` e `adapter_flags` vêm das fontes canônicas. Os registros `pack_*`
vêm dos **exemplos positivos dos próprios contratos**: eles formam um mini-pacote
sintético, e é contra ele que as referências cruzadas resolvem. Isso obriga os
exemplos dos seis contratos a serem **coerentes entre si** — um `projects_facts`
que cite fato que nenhum exemplo declara é reprovado, que é a própria falha que o
contrato diz recusar. Nenhum pacote de cenário existe antes da Fase 7, e inventar
um só para o teste seria dado não versionado guiando verificação.
