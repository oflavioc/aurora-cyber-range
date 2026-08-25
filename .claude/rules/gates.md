# R10 — Gates e suítes

Severidade: **bloqueante**. Dono: `qa-engineer`.

## Nascimento de um gate

Todo gate novo tem: caso positivo canônico + negativo + adversarial + regressão;
**oracle independente da implementação** sempre que possível; e um **mutante que
ele mata** (R3 §5). Namespace da fase/marco corrente — nunca continuar numeração
de fase alheia, nunca gate de um marco vivendo em arquivo de outro.

## Proibições (cada uma pagou um custo real no projeto de origem)

1. **Nunca enfraquecer o gate para passar.** Divergência fonte↔gerado exige
   decidir a direção (a spec mudou? o artefato foi editado?) — nunca afrouxar a
   asserção.
2. **SKIP silencioso é FAIL** (lição de origem: 23 gates visuais pulavam com
   exit 0 por ambiente ausente). Ambiente ausente → o relatório da suíte NOMEIA
   o não executado; o registro canônico (`expected_suites.json`) tolera só o
   intervalo declarado.
3. **Contagens pinadas vivem no registro canônico**, não em prosa nem no corpo
   do gate. O stage `suites` compara execução real contra
   `expected_suites.json`; suíte nova entra no registro **no mesmo PR** (ou em
   exceção nominal com prazo).
4. **Hash pinado em teste lê do registry** (R8); pin inline novo é proibido.
5. **Âncora de regressão é commit imutável + SHA**, nunca `HEAD:`/branch
   (lição de origem: um gate ancorado em HEAD morreu permanentemente vermelho).
6. **Gate não spawna outra suíte** nem usa regex sobre stdout como oráculo —
   orquestração e agregação pertencem ao pipeline.
7. **Oráculo que invoca processo externo**: caminho entre aspas, dependência
   declarada no env-doctor.
8. **Teste não escreve em arquivo versionado** (R7 §3).
9. **Checagem nova entra no `pipeline.yaml`**, nunca no prompt de um agente.
10. **Scanner de padrão proibido tem auto-exclusão nominal** — senão falha no
    próprio gate.
