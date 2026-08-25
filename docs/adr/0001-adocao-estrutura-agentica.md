# ADR 0001 — Adoção da Estrutura Agêntica (Ondas 0–1) por integração

> Critérios (R12): difícil de reverter + surpreendente sem contexto + trade-off
> real.

- **Status**: proposta
- **Data**: 2026-08-25
- **Decisores**: operador (ratificação pendente) + agente de integração

## Contexto

O aurora já tem um regime de verificação maduro e idiossincrático: spec
congelada com gate de CI, verificadores com prova negativa pareada, auditoria
adversarial de checkpoint, invariantes arquiteturais com hook e CI. O starter
kit da Estrutura Agêntica (destilado do projeto QuickScan) traz peças que o
aurora NÃO tem: registry de pins, boundary como dado, máquina SDD de 7 fases
para demandas fora do roadmap, contrato de resposta de subagente, pipeline
local declarativo e auditoria da própria configuração agêntica. O risco da
adoção é criar segunda autoridade para fatos que o aurora já governa melhor.

## Decisão

Adotar por **integração aditiva**, não por substituição: instalar as Ondas 0–1
do kit (regras, templates, skills, verify skeleton com pins semeados, hooks)
**adaptadas** ao processo vigente; onde o kit colide com o existente, o
existente prevalece e o conflito é registrado em
`docs/ADOCAO_ESTRUTURA_AGENTICA.md` para decisão do operador. A R1
(invariantes de produto) nasce como PROPOSTA pendente de ratificação.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Instalar o kit inteiro como está | Colide com o fluxo de fases, o gate spec_freeze e os agentes existentes; criaria duas autoridades para spec e para merge |
| Não adotar nada | O aurora ficaria sem registry de identidade, sem processo formal para demanda fora do roadmap e sem auditoria da própria configuração agêntica |
| Adotar só documentação (sem hooks/pipeline) | Regra sem gate é prosa — a lição central do projeto de origem |

## Consequências

- Fica mais fácil: abrir demanda fora do roadmap com processo auditável;
  detectar drift de identidade (pins × HEAD); auditar a própria configuração.
- Fica mais difícil: alterar arquivo pinado passa a exigir `gen_pins.py` no
  mesmo PR (disciplina R8) — o custo é deliberado e as exclusões são ajustáveis.
- Passa a ser proibido: editar `contracts/generated/*` e `pins.json` à mão
  (hook + deny).
- Pendente do operador: ratificar a R1; decidir `.gitattributes` global LF;
  decidir se o pipeline mínimo entra no CI; instanciar a Onda 2 (8 papéis).
