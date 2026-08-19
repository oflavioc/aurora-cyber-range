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
- Curva **volume de eventos → tempo de reconstrução** medida, com o ponto de quebra do orçamento de 3 s e a máquina, a data e a stack declaradas junto do número.
- Reinício do processo restaura a projeção corrente sem intervenção.
- Rollback com `reason: technical_failure` **registra no evento** o intervalo a descontar do cálculo de métricas, pelos seus **extremos** e marcados em **`exercise_timestamp`**.

> **O critério da reconstrução de 4 h saiu daqui no `spec-change` `item-8-volume-de-4h`, e não por arrumação.** Ele dizia *"reconstrução da projeção do zero para exercício de 4 h roda em < 3 s"*, nesta seção, que é a da Fase 2 — e a Fase 2 **não produz exercício de 4 h**: o pack de 4 h é entregável da Fase 7 (`04_SCENARIO_SCHEMA.md` §9). Repetia a forma do defeito que este documento já consertou duas vezes: cobrar de uma fase a verificação de artefato que ela não produz.
>
> **O requisito não foi enfraquecido, foi movido inteiro** — < 3 s, para exercício de 4 h — para T12, e a metade de telemetria para T13. `01_ARCHITECTURE.md` §7 continua enunciando a norma de desempenho sem alteração: o que se realocou foi quem a verifica.
>
> **O que ficou é o que a Fase 2 pode de fato provar:** a curva volume → tempo, com o ponto de quebra. Ela não prova o critério de 4 h — mostra que o motor aguenta N eventos, e não que 4 h cabem abaixo de N. Chamar uma de prova da outra seria atestação com um passo intermediário.
>
> **A máquina, a data e a stack entram no critério, e isso é exigência de forma.** Número de desempenho sem o contexto em que foi obtido envelhece sem que ninguém perceba, e medição é justamente o tipo de coisa que se cita sem repetir.
>
> Este critério dizia *"desconta o intervalo do cálculo de métricas"*, e esta seção é a da **Fase 2**, cujo NON-GOAL declarado é "métricas". Corrigido no `spec-change` `fase-2-escalacoes-e-exclusao`, junto com o item 7 da DoD daquela fase, que trazia a mesma exigência com as mesmas palavras. **O requisito não foi removido, foi realocado:** quem desconta é a Fase 6, por item próprio de DoD em `07_IMPLEMENTATION_PHASES.md` e por critério em T10. Corrigir só um dos dois lugares deixaria `06` e `07` se contradizendo sobre o escopo da mesma fase — dois documentos não-master em conflito, que é o que `CLAUDE.md` manda escalar.
>
> **A segunda metade saiu daqui pelo mesmo motivo, e não por arrumação.** Ela dizia *"com `reason: rehearsal`, a epoch não entra no AAR"*: critério sobre AAR etiquetado Fase 2, e o AAR é entregável da Fase 10. Repetia exatamente a forma do defeito que este `spec-change` conserta — cobrar de uma fase a verificação de artefato que ela não produz. E, ao sair, mostrou que era **duas** exigências e não uma: `09_EVENT_MODEL.md` §3.1 dá a `rehearsal` dois efeitos — "Nenhum evento da epoch entra em cálculo" e "Epoch descartada do AAR". Cada um foi para a fase que o entrega: o cálculo em T10, o descarte do AAR em T14. Nenhum dos dois ficou em duas fases.
>
> **Extremos, e em `exercise_timestamp`, é exigência de forma — e cabe aqui porque o campo que a carrega é contrato, e contrato não entra em `spec-change`.** Três formas erradas, e nenhuma delas dá erro: as três produzem número plausível, e só na Fase 6.
>
> **Duração, não.** Ela impede unir intervalos que se sobrepõem: dois congelamentos cruzados contam o trecho comum duas vezes, e a duração já somada não guarda com que detectar isso. É por isso que T10 pode exigir união em vez de soma.
>
> **`wall_timestamp`, não.** O PAUSAR avança o relógio de parede sem avançar o de exercício (`01_ARCHITECTURE.md` §3), e a métrica que sofre o desconto é medida em tempo de exercício.
>
> **O que o intervalo mede, e por que ele pode ser zero.** Tempo de exercício que **correu**: `01_ARCHITECTURE.md` §3 diz que na falha do range "o clock de exercício continua correndo; apenas a projeção de métricas desconta o intervalo". Falha técnica e PAUSAR são mecanismos distintos, e a primeira não congela o exercise-clock. Se o facilitador também pausar, o trecho pausado não avança `exercise_timestamp` — e não precisa: tempo pausado nunca entrou no cálculo, e descontá-lo seria descontar duas vezes. Um congelamento inteiramente contido numa pausa registra **zero**, que é o valor certo. Esta é a razão final de o campo ser `exercise_timestamp`: é o único dos três que exclui a pausa sem que ninguém tenha de subtraí-la depois.
>
> **`exercise_time`, também não — e este é o menos óbvio dos três.** O intervalo vai do inject falho até a retomada, e o `rollback_performed` incrementa `simulation_epoch` no meio dele (§4.2 de `01_ARCHITECTURE.md`): os dois extremos caem em epochs diferentes **por construção, em todo congelamento**. E `09_EVENT_MODEL.md` §1.1 diz que sem `exercise_timestamp` "evento de `simulation_epoch` 2 e evento de epoch 0 não são ordenáveis entre si na linha do exercício — só dentro da própria epoch". `exercise_time` é o rótulo `T+` que rebobina no rollback; `exercise_timestamp` é o que não rebobina, e foi acrescentado ao envelope exatamente para este problema. A união que T10 exige é operação de ordem total entre extremos de rollbacks distintos — com `exercise_time` ela herda o defeito inteiro.

## T4 — Relógios (Fase 2)

- Todo evento carrega `exercise_time`, `exercise_timestamp`, `wall_timestamp` e `clock_multiplier`.
- Com multiplicador 5x, o intervalo de `wall_timestamp` entre dois eventos é ~1/5 do de `exercise_time`.
- Durante PAUSAR, `exercise_time` e `exercise_timestamp` não avançam e `wall_timestamp` avança.

> O primeiro critério listava três das quatro marcas, omitindo `exercise_timestamp`. Corrigido no `spec-change` `fase-2-escalacoes-e-exclusao`, pelo mesmo motivo que levou o E2 a corrigir `wall_time` no item 1 da DoD desta fase: **é este critério que julga aquele item**, e a DoD passaria a exigir uma marca que o teste de aceitação não confere. `09_EVENT_MODEL.md` §1.1 é explícito sobre o custo da omissão — sem `exercise_timestamp`, eventos de epochs distintas não são ordenáveis entre si na linha do exercício —, e a Fase 2 é justamente a fase que cria as epochs.
>
> **O terceiro critério ganhou `exercise_timestamp` no mesmo `spec-change`, e por motivo próprio.** Que ele congela no PAUSAR não estava enunciado em lugar nenhum: era implicação de ele ser marca do exercise-clock, e `01_ARCHITECTURE.md` §3 passou a dizê-lo, junto de que ele não rebobina no rollback. T3 exige que os extremos do intervalo congelado sejam marcados nesse campo, e uma exigência apoiada em propriedade não enunciada é a mesma classe que este `spec-change` conserta em outros dois lugares. Aqui ela vira verificável na fase que constrói o relógio.

## T5 — Vertical slice (Fase 4)

- A sequência do DEMO SCRIPT da Fase 4 completa sem intervenção manual.
- Wallboard reflete mudança de flag em < 1 s.
- Refresh do browser recupera estado corrente em wallboard e participant-view.
- **Reinício do engine com o exercício pausado o restaura pausado; reinício depois da retomada o restaura correndo.** Os dois casos a partir do event store, sem intervenção.

> O último critério entrou no `spec-change` `exercise-resumed`. Ele não acrescenta escopo à Fase 4: o item de DoD dela em `07_IMPLEMENTATION_PHASES.md` já manda o reinício restaurar **o exercício** a partir do event store, e o estado de pausa é parte do exercício. O que faltava era a forma **verificável** — e sem ela o `exercise_resumed` seria evento novo que nenhuma checklist cobra, que é como um requisito morre sem nada ficar vermelho. Mesma correção que T10 recebeu no `spec-change` anterior, e pelo mesmo motivo.
>
> **Os dois casos, e não um.** Um teste que só verificasse o reinício pausado passaria com um engine que sobe sempre pausado; o par é o que discrimina.

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
- Métricas descontam o intervalo registrado por `rollback_performed` com `reason: technical_failure`. O desconto usa a **união** dos intervalos registrados, nunca a soma das durações.
- Nenhum evento de epoch com `reason: rehearsal` entra em cálculo de métrica.
- A classificação das nove siglas obtida pelo critério de `00_MASTER_SPEC.md` §3.2 é igual à de `03_EXERCISE_DESIGN.md` §3.0. Divergência reprova a tabela, nunca o critério.
- Todo `event_type` do catálogo tem `metric_side`, e os quatro lados são disjuntos — checado sobre o atributo, junto da cobertura de `effect_class`.
- A folha `event` de predicado obedece à conjunção de `09_EVENT_MODEL.md` §4.0, e o probe planta as três formas de violação mais o controle positivo.
- Métrica simples plantada computando seu instante a partir do lado de verificação reprova, nomeando a sigla e a referência.
- Metade de declaração de um par plantada computando-se a partir da metade de verificação reprova.
- **A recusa é estrutural, não por detecção de referência no corpo do cálculo.** Insumo de cada lado com tipo próprio, `Sequence[Event]` recusado, sem parâmetro por onde entrem fluxo total, store ou pack como objeto, escalares pelo insumo tipado, construtor só no ponto de montagem.
- **O desconto por união, a exclusão de `rehearsal` e a seleção de start são computação do consumidor.** Os eventos de lado `epoch` chegam aos dois computadores e os atributos de inject chegam no payload; o teste falha se o número certo aparecer por ausência de insumo em vez de por cálculo.
- `inject_fired` emite no payload os marcadores que os starts exigem, e o teste de emissão os cobra.
- Todo verificador tem teste negativo próprio.

> Os critérios do desconto por `technical_failure` e da exclusão por `rehearsal` entraram no `spec-change` `fase-2-escalacoes-e-exclusao` — eram os dois últimos até o `spec-change` `particao-das-metricas-pareadas` acrescentar os seguintes. **O primeiro é o destino do que a Fase 2 deixou de calcular**: T3 e o item 7 da DoD da Fase 2 passaram a exigir apenas que o intervalo seja *registrado*, e sem este critério o desconto ficaria registrado e nunca verificado — norma viva em `09_EVENT_MODEL.md` §3.1, em `01_ARCHITECTURE.md` §3 e em `03_EXERCISE_DESIGN.md` §3.5, sem nenhuma fase obrigada a executá-la.
>
> **O segundo veio de T3, e chegou aqui pela metade.** `rehearsal` tem *dois* efeitos declarados em `09_EVENT_MODEL.md` §3.1 — "Nenhum evento da epoch entra em cálculo" e "Epoch descartada do AAR" —, e o critério original de T3 os tratava como um só. São duas exigências, com duas fases: o cálculo é Fase 6 e está aqui; o descarte do AAR é Fase 10 e está em T14. Mandar as duas para cá manteria, com outro nome, o defeito que T3 acabou de perder — critério de AAR cobrado de uma fase que não o entrega.
>
> A união em vez da soma é a metade que o registro por extremos torna possível, e é por isso que T3 exige extremos: com duração, dois congelamentos sobrepostos contam o trecho comum duas vezes e nada acusa.

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
- **Opção com `capability_gap` referenciando objetivo inexistente é recusada pelo linter**, com a posição no arquivo.
- `dryrun` percorre todos os caminhos sem erro.
- **Reconstrução da projeção do zero para o exercício de 4 h do `ransomware-universidade` roda em < 3 s**, com máquina, data e stack declaradas.

> O último critério veio de T3 no `spec-change` `item-8-volume-de-4h`, com a exigência intacta. Ele chega aqui porque esta é a fase que produz o insumo: o pack de 4 h é o `ransomware-universidade` (`04_SCENARIO_SCHEMA.md` §9), e sem ele não existe "exercício de 4 h" a medir.
>
> A Fase 2 entrega a curva volume → tempo com o ponto de quebra, e é contra ela que este número se lê. **Passar do envelope medido lá é sinal; o veredito é este critério.**

## T13 — Projeção de evidência (Fase 9)

- Para cada `fact_id`, todas as projeções declaradas existem e apresentam usuário, IP e timestamp mutuamente consistentes. Teste dirigido por fato, não por seed.
- Fato sem `projections` não aparece em nenhuma fonte.
- `precursor_events.jsonl` é reproduzível a partir do ground truth; edição manual é detectada por hash no `MANIFEST.json`.
- Nenhum arquivo contém anexo, binário, hash de malware real, IOC real ou domínio roteável.
- Banner de ambiente simulado na primeira linha de cada arquivo.
- **A reconstrução da projeção continua em < 3 s** com `telemetry_emitted` no volume de um exercício de 4 h.

> O último critério é a **segunda metade** da realocação do item 8 da Fase 2, no mesmo `spec-change`. `telemetry_emitted` é `event_type` do catálogo e vai para o event store como qualquer outro — entra na leitura total que a reconstrução percorre —, e é a única fonte com ordem de grandeza diferente das demais: injects são dezenas, ações de participante são centenas, telemetria pode chegar às centenas de milhares sozinha.
>
> Por isso o exercício de 4 h de T12 **não é o de 4 h daqui**: lá se mede o volume que o pack produz, aqui o que o range produz. Sem este critério, T12 verificaria o requisito e ele passaria a ser falso nesta fase sem nada ficar vermelho.

## T14 — Assimetria e AAR (Fase 10)

- Persona recebe apenas o conteúdo definido em `information_distribution.yaml`; endpoint de persona não vaza ground truth.
- AAR detecta automaticamente comunicação externa de número divergente do ground truth via `fact_check_against`.
- Timeline do AAR renderiza epochs separadas, com motivo de rollback.
- Epoch de rollback com `reason: rehearsal` é descartada do AAR.
- Notas do facilitador aparecem rotuladas como qualitativas, fora do bloco de métricas.
- Opção com `capability_gap` escolhida emite `decision_made` **e** `capability_gap_declared`; a lacuna aparece na seção 12 do AAR com função de controle, objetivo afetado e métrica impactada.

> O critério de `rehearsal` entrou no `spec-change` `fase-2-escalacoes-e-exclusao`. Ele estava em T3, etiquetado Fase 2, colado ao critério de `technical_failure` e falando de AAR — artefato que a Fase 2 não produz. `09_EVENT_MODEL.md` §3.1 dá a `rehearsal` dois efeitos, e eles pertencem a fases diferentes: o de cálculo está em T10, este é o de renderização, e é desta fase. Nenhuma exigência ficou nos dois lugares.

## T15 — Segurança transversal (todas as fases)

- Nenhuma dependência não pinada.
- Nenhum serviço exposto sem autenticação, exceto wallboard e participant-view.
- `GM_NOTES.md` e `ground_truth.yaml` ausentes do build servido a participantes.
- Nenhum CPF sintético passa validação de dígito verificador.
- Nenhum IP fora de faixa privada ou de documentação em dado sintético.
- `tools/check_security_constraints.py` falha contra violação plantada de `05_SECURITY_REQUIREMENTS.md` §1, sem proibir import de biblioteca criptográfica por si só.
- `tools/check_synthetic_data.py` falha contra IP, domínio ou identificador fora das faixas sintéticas de `05_SECURITY_REQUIREMENTS.md` §3.
