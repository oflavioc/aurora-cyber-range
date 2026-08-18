# Aurora Cyber Range — Briefing

**Autor:** Flavio Costa · Projeto pessoal
**Estado:** Fases 0 a 5 concluídas — especificação congelada, aparato de verificação operante, vertical slice rodando ponta a ponta, dataset em escala com trilha de auditoria encadeada. Próximo checkpoint: Fase 6
**Repositório:** github.com/oflavioc/aurora-cyber-range

---

## O problema

Tabletop exercises de crise cibernética são quase sempre conduzidos em slides. O facilitador narra um cenário, a mesa discute o que faria, e ao final produz-se uma ata com conclusões qualitativas.

Três limitações decorrem disso:

**Não há pressão real.** Ninguém decide sob a mesma tensão de uma crise quando o pior resultado possível é uma discussão que termina no horário.

**Não há medição defensável.** "A equipe respondeu bem" é opinião do facilitador. Não é comparável entre exercícios nem entre organizações, e não sustenta um plano de melhoria.

**A informação é simétrica.** Todos na sala ouvem a mesma narração ao mesmo tempo — o oposto de uma crise real, onde TI sabe uma coisa, a diretoria recebe outra, e a imprensa afirma uma terceira.

## A proposta

Uma plataforma onde o sistema **realmente degrada** durante o exercício.

Uma aplicação completa — o ERP de uma universidade fictícia — roda em tela. Quando o facilitador dispara um evento de cenário, a matrícula trava de verdade, as sessões de prova em andamento caem, o portal fica indisponível, e um feed social simulado começa a reagir. A plateia não imagina o impacto: ela vê.

Nenhum ataque é executado. Todos os efeitos são mudanças controladas de estado — a especificação proíbe código ofensivo funcional sem exceção.

## O que muda na medição

**Métricas pareadas.** Toda métrica de resposta tem duas versões: o que a equipe declarou e o que de fato aconteceu.

> *"Contenção declarada aos 31 minutos. Evento incompatível com contenção aos 38. Contenção verificável apenas aos 52."*

Isso mede qualidade da decisão, não velocidade de declaração. Declarar cedo não melhora a nota — e a diferença entre os dois números é frequentemente o achado mais útil do exercício.

**Rubricas comportamentais.** A avaliação usa escalas ancoradas em comportamento observável, versionadas e compartilhadas entre exercícios. "Comunicação nota 8" vira "comunicou fatos confirmados, incertezas declaradas, ações em curso e horário do próximo update" — nível 3 de 4, com definição idêntica em toda rodada.

**Calibração, não acerto.** Numa das linhas do cenário, a equipe precisa investigar um conjunto de casos suspeitos. O critério não é encontrar todos: é a confiança declarada corresponder à força real da evidência. Acusar com certeza um caso que não se sustenta pesa mais que deixar um caso duvidoso em aberto — porque numa organização real a falsa acusação tem custo maior.

**Assimetria de informação por desenho.** Cada participante entra com sua conta e vê apenas o que sua função veria. TI recebe um alerta técnico sem escopo; a diretoria recebe "possível vazamento"; comunicação recebe a imprensa afirmando um número que ninguém confirmou. O relatório final compara o que foi comunicado externamente com o que de fato ocorreu.

## O que o participante vive

Um cenário de 4 horas com duas linhas correndo em paralelo — e a equipe não sabe disso no início.

**Linha A, externa.** Credencial de docente obtida por infostealer, usada em VPN sem MFA. Escalada por conta de serviço, exfiltração da base de alunos e de projetos de pesquisa, ransomware na véspera do período de matrícula, dupla extorsão.

**Linha B, interna.** Um aluno vinha alterando notas há três semestres. Não tem relação nenhuma com a Linha A. É descoberto no meio da resposta, justamente porque a auditoria passou a ser lida com lupa.

O valor está no que isso testa: **triagem sob viés de narrativa**. A equipe vai tentar encaixar tudo num único ator, e vai errar. E a Linha B força uma decisão sem resposta boa — anular notas de três semestres afeta alunos já formados, alguns já contratados, alguns com bolsa vinculada a rendimento.

## O que a organização leva

Um relatório de debriefing com:

- Desempenho por objetivo de aprendizagem, com as evidências que sustentam cada avaliação
- Métricas pareadas, com as janelas de asseguração prematura explicitadas
- Comparação entre o que foi comunicado externamente e o que de fato ocorreu
- Timeline completa das decisões, com quem decidiu e em quanto tempo
- **Lacunas de capacidade nomeadas** — onde a resposta travou por ausência de mecanismo

O último ponto merece destaque. Quando uma equipe responde "não conseguimos fazer isso no tempo do exercício porque não temos o mecanismo", isso é registrado como dado, não como desistência. É frequentemente o achado mais acionável da rodada.

**Neutralidade é requisito de especificação.** Lacunas são nomeadas por função de controle — *"ausência de revogação centralizada de sessão federada"* — nunca por produto. Um exercício em que a resposta certa aponta para um fornecedor deixa de medir a capacidade da equipe e passa a medir se ela adivinhou o vendor. A conversa sobre como fechar a lacuna é legítima, mas acontece depois, conduzida por pessoas, fora do relatório.

## Reusabilidade

O motor é agnóstico de domínio, com fronteira arquitetural verificada automaticamente. A universidade é o primeiro adapter; um adapter hospitalar existe como stub para provar que a separação funciona.

Implementar um segundo vertical — energia, financeiro, saúde — significa escrever o domínio, não refazer o motor. O relógio de exercício, o modelo de eventos, as métricas, as rubricas e o relatório são compartilhados.

## Rigor de construção

A Fase 0 do projeto não produziu nenhuma linha de aplicação. Produziu o aparato que vigia a construção: 6 verificadores automáticos que aplicam as regras arquiteturais por análise de árvore sintática, e um agente auditor independente que revisa cada checkpoint contra a especificação, em contexto isolado e sem ferramentas de escrita.

**Só a Fase 0 respondeu por 14 relatórios de auditoria versionados, e 13 deles reprovaram.** As primeiras rodadas dela são anteriores ao mecanismo que persiste o relatório, e por isso não têm arquivo próprio — o que também está registrado.

Isso é o resultado esperado de um aparato que funciona, e vale detalhar por quê. A primeira rodada encontrou um teste que **passava sem exercitar a fronteira que deveria verificar**: o probe estava plantado dentro da região que o verificador já enxergava. Teste verde, requisito não provado.

As rodadas seguintes encontraram, entre outras coisas, um probe que passava **pelo motivo errado** — carregando o nome da propriedade que não media —, uma pendência que sobreviveu seis rodadas sobre uma **premissa falsa que nenhuma auditoria mediu**, e dois casos em que a correção **reintroduziu a classe de erro que ela fechava**.

Nada disso foi apagado ou suavizado. Cada rodada tem relatório versionado, com veredito, evidência e encaminhamento — inclusive as decisões tomadas apesar de uma reprovação, com as condições explícitas que as sustentam e que precisam valer juntas em qualquer repetição futura.

A especificação está congelada em `spec-v1.0`. Alterações exigem processo formal, e o mecanismo que garante isso foi demonstrado funcionando **antes** de ser ligado.

## Estado e próximos passos

São 12 fases planejadas, 5 concluídas. Próximo checkpoint: **Fase 6 — objetivos, rubricas versionadas, métricas pareadas e calibração**.

A Fase 4, o vertical slice, está concluída e é o primeiro marco demonstrável: o console do facilitador dispara um inject, o endpoint de matrícula devolve `503` de verdade, o wallboard reage em menos de um segundo, e o rollback restaura o estado com a mesma requisição voltando a `201`. É o suficiente para uma conversa de "é isto que estou construindo" com o sistema no ar.

**O que ainda não existe** é a maior parte do que este briefing descreve como proposta: rubricas, métricas pareadas, calibração, assimetria de informação e o relatório de debriefing são das Fases 6 a 10. Nenhum pacote de cenário foi escrito, e nenhum exercício real foi conduzido.

O primeiro pacote de cenário completo será o de ransomware universitário, desenhado para audiência executiva, na Fase 7.

---

## Origem

Projeto pessoal, desenvolvido de forma independente. Agnóstico de fornecedor por desenho — a proibição de conteúdo de portfólio dentro do cenário é regra de especificação, não escolha editorial.

Proposto para uso em exercícios de crise com quaisquer organizações e em atividades de formação.
