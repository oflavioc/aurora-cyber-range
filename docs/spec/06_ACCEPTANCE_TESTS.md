# 06 — CRITÉRIOS DE ACEITAÇÃO

Priorizados pelo que quebra durante exercício ao vivo. Cobertura ampla de unidade é secundária.

---

## T1 — Fronteira arquitetural (Fase 1)

- `range-core/` não contém import de `domains/`. Verificado por AST em `tools/check_core_boundary.py`, não por grep.
- Nenhum evento emitido pelo core ou pelo adapter carrega `objective_ids`. O binding evento→objetivo ocorre só na projeção. Verificado por `tools/check_event_envelope.py`.

## T2 — Contratos (Fases 1–3)

- Flag não declarada impede boot, com mensagem nomeando flag e arquivo esperado.
- `event_type` fora do catálogo é rejeitado na emissão e falha no CI.
- Nenhuma string literal de flag ou de `event_type` fora dos geradores. Verificado por `tools/check_contract_literals.py`.
- Constantes Python e TypeScript dessincronizadas → `tools/codegen.py --check` sai com código diferente de `0`. A comparação é feita **em memória** contra os artefatos em disco e **nunca escreve**; por isso `git diff --exit-code` depois dele é vacuoso e não serve como prova de sincronia.

## T3 — Estado, epoch e rollback (Fase 2)

- Aplicar o mesmo inject duas vezes produz projeção idêntica.
- `rollback_performed` incrementa `simulation_epoch` e **não remove** nenhum evento.
- Evento de `participant_action` gravado na epoch 0 continua legível após rollback, marcado com sua epoch.
- Reconstrução da projeção do zero para exercício de 4 h roda em < 3 s.
- Reinício do processo restaura a projeção corrente sem intervenção.
- Rollback com `reason: technical_failure` desconta o intervalo do cálculo de métricas; com `reason: rehearsal`, a epoch não entra no AAR.

## T4 — Relógios (Fase 2)

- Todo evento carrega `exercise_time`, `wall_timestamp` e `clock_multiplier`.
- Com multiplicador 5x, o intervalo de `wall_timestamp` entre dois eventos é ~1/5 do de `exercise_time`.
- Durante PAUSAR, `exercise_time` não avança e `wall_timestamp` avança.

## T5 — Vertical slice (Fase 4)

- A sequência do DEMO SCRIPT da Fase 4 completa sem intervenção manual.
- Wallboard reflete mudança de flag em < 1 s.
- Refresh do browser recupera estado corrente em wallboard e participant-view.

## T6 — Isolamento de papel (Fases 4–5)

**Teste de payload de API, não de interface.** Esconder campo no frontend passaria despercebido até alguém abrir o DevTools durante o exercício.

- Resposta de qualquer endpoint autenticado como `operador` **não contém**, em nenhum nível do JSON: `linha`, `descricao_facilitador`, `texto_para_plateia` completo, GM_NOTES, ground truth, `defensibility`, injects futuros, consequências de `decision_point`.
- Asserção por varredura recursiva de chaves sobre o corpo serializado.
- Acesso direto a endpoint de facilitador com token de operador retorna 403.

## T7 — Auditoria imutável (Fase 5)

- `UPDATE` e `DELETE` em `audit_trail` falham por trigger.
- A role da aplicação não possui `UPDATE`, `DELETE` ou `TRUNCATE` na tabela.
- Adulteração induzida faz `GET /audit/verify-chain` reportar a posição exata da quebra.

## T8 — Determinismo e gabarito (Fase 5)

- Duas execuções de seed com o mesmo `RANDOM_SEED` produzem dataset idêntico.
- Os seis conjuntos da Linha B aparecem nos volumes de `02_DOMAIN_ACADEMUS.md` §6.1.
- A query de referência do `GM_NOTES.md` retorna exatamente os 22 indevidos comprovados.
- **Todo fato mencionado em `GM_NOTES.md` existe em `ground_truth.yaml`.** Divergência é recusada pelo linter.

## T9 — Objetivos e evidência (Fase 6)

- Cada `event_type` declarado em `observability_hooks.yaml` é emitido pela ação correspondente.
- Objetivo com evidência `auto` não satisfeita não é classificado como `excellent`.
- Rubrica ausente **ou em versão diferente** da declarada em `required_rubrics` impede carga do pack.
- AAR grava a versão de rubrica usada; comparação entre versões distintas é recusada sem mapeamento declarado.

## T10 — Métricas pareadas (Fase 6)

- Cada par (TTCD/TTCV, TTRD/TTRV, TTID/TTIV) é disparável em teste.
- Declaração de contenção **não** altera nenhum valor de `ground_truth`.
- Com contenção declarada antes do predicado ser satisfeito, o AAR lista os eventos de ground truth ocorridos na janela como incompatíveis com a declaração.
- Com contenção declarada depois do predicado, o AAR marca lacuna de consciência situacional.
- Pack sem `verification_predicates` não carrega.
- `TTIV` é computado por limiar de calibração, não por predicado de estado do mundo.

## T11 — Calibração (Fase 6)

- Brier calculado apenas sobre casos dentro do escopo revisado declarado.
- Caso dentro do escopo e não avaliado conta como `confidence = 0`.
- Indevido comprovado fora do escopo revisado é reportado como lacuna de cobertura, não como falso negativo.
- `confidence ≥ 80` sobre `defensibility ≤ 0.2` gera sinal de overconfidence.
- Overconfidence e falso negativo aparecem separados e não se compensam.

## T12 — Schema e branching (Fase 7)

- Pack em `schema_version` N-1 carrega com migração e aviso; anterior a N-1 é recusado com instrução.
- `branch_policy` do manifesto é aplicada: excesso de pontos ou de caminhos é recusado.
- Branch sem `reconverge_at` é recusado.
- **`event_type` inexistente em condição de branch é recusado pelo linter**, com a posição no arquivo.
- Condição que dependa de juízo do facilitador é recusada.
- Inject sem `objectives` e sem `noise: true` é recusado.
- `dryrun` percorre todos os caminhos sem erro.

## T13 — Projeção de evidência (Fase 9)

- Para cada `fact_id`, todas as projeções declaradas existem e apresentam usuário, IP e timestamp mutuamente consistentes. Teste dirigido por fato, não por seed.
- Fato sem `projections` não aparece em nenhuma fonte.
- `precursor_events.jsonl` é reproduzível a partir do ground truth; edição manual é detectada por hash no `MANIFEST.json`.
- Nenhum arquivo contém anexo, binário, hash de malware real, IOC real ou domínio roteável.
- Banner de ambiente simulado na primeira linha de cada arquivo.

## T14 — Assimetria e AAR (Fase 10)

- Persona recebe apenas o conteúdo definido em `information_distribution.yaml`; endpoint de persona não vaza ground truth.
- AAR detecta automaticamente comunicação externa de número divergente do ground truth via `fact_check_against`.
- Timeline do AAR renderiza epochs separadas, com motivo de rollback.
- Notas do facilitador aparecem rotuladas como qualitativas, fora do bloco de métricas.

## T15 — Segurança transversal (todas as fases)

- Nenhuma dependência não pinada.
- Nenhum serviço exposto sem autenticação, exceto wallboard e participant-view.
- `GM_NOTES.md` e `ground_truth.yaml` ausentes do build servido a participantes.
- Nenhum CPF sintético passa validação de dígito verificador.
- Nenhum IP fora de faixa privada ou de documentação em dado sintético.
- `tools/check_security_constraints.py` falha contra violação plantada de `05_SECURITY_REQUIREMENTS.md` §1, sem proibir import de biblioteca criptográfica por si só.
- `tools/check_synthetic_data.py` falha contra IP, domínio ou identificador fora das faixas sintéticas de `05_SECURITY_REQUIREMENTS.md` §3.
