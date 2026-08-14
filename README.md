# Aurora Cyber Range

Motor reutilizável para exercícios de crise cibernética, com domínios de negócio acopláveis.

A maior parte dos tabletop exercises acontece em slides: alguém narra "imagine que o sistema caiu" e a mesa discute o que faria. O Aurora inverte isso. O sistema **cai de verdade** — uma aplicação real degrada em tempo real enquanto o exercício corre, e a plateia vê a fila crescer, a matrícula travar, o feed social virar hostil.

Nenhum ataque é executado. Todos os efeitos são simulações de estado.

---

## Como funciona

Um facilitador dispara eventos de cenário a partir de um console. Cada evento altera o estado da aplicação de forma declarativa, e três superfícies reagem:

- **Wallboard** — telão para a plateia: fila de provas em andamento, ocupação, status dos campi, feed social e um índice de saúde institucional
- **Tela da plateia** — o evento corrente e os cronômetros de decisão
- **Dashboards por persona** — cada participante entra com sua conta e vê apenas o que sua função veria

O exercício produz um relatório de debriefing com métricas, evidências coletadas e as decisões tomadas — não apenas uma lista de conclusões.

## O que ele mede

Velocidade não é o único eixo. Cada métrica de resposta é **pareada**: uma para o que a equipe declarou, outra para o que de fato aconteceu.

Se a equipe declara contenção aos 31 minutos e o incidente só foi verificavelmente contido aos 52, o relatório mostra os dois números e os eventos incompatíveis no intervalo. Declarar cedo não melhora a nota.

Outros eixos avaliados:

- **Calibração** — a confiança declarada corresponde à força real da evidência? Acusar com certeza um caso que não se sustenta pesa mais que deixar um caso duvidoso em aberto
- **Assimetria de informação** — cada persona recebe uma versão diferente da verdade, com defasagem e confiança distintas. Ninguém tem o quadro completo, que é a característica definidora de uma crise real
- **Integridade × disponibilidade** — o sistema voltou, mas dá para confiar no dado que está nele?

## A organização simulada

**Universidade Aurora (UniAurora)** — 28.000 alunos, 1.200 professores, 5 campi, ensino presencial e EAD, pesquisa com ambiente HPC, identidade federada. O ERP acadêmico chama-se **ACADEMUS**.

O motor é agnóstico de domínio. Um segundo adapter hospitalar (**Hospital Regional Aurora**, sistema **PRONTUS**) existe como stub, para provar que a fronteira arquitetural funciona.

---

## Arquitetura

Duas camadas com fronteira rígida, verificada automaticamente:

| Camada | Conteúdo |
|---|---|
| `range-core/` | Motor: relógio de exercício, event store, engine de cenário, métricas, telemetria, relatório |
| `domains/` | Domínio de negócio: entidades, telas, painéis, dados sintéticos |

O core não conhece o domínio. Implementar um segundo vertical não toca no motor.

**Modelo das quatro verdades** — a estrutura normativa do projeto:

```
GROUND TRUTH          o que de fato ocorreu
      ↓
OBSERVABLE EVIDENCE   o que pode ser descoberto
      ↓
PARTICIPANT BELIEF    o que a equipe crê e declara
      ↓
EVALUATOR ASSESSMENT  o que o avaliador julgou
```

Confundir duas dessas camadas invalida o relatório. Declaração de participante nunca altera ground truth — caso contrário, declarar cedo melhoraria a métrica mesmo com a decisão errada.

## Segurança

Restrições que a especificação trata como inegociáveis:

- Nenhum exploit, malware ou payload ofensivo funcional. Todos os efeitos de incidente são flags de estado
- Nenhuma criptografia real de arquivo, nenhuma movimentação lateral, nenhuma vulnerabilidade intencional
- Todos os dados são sintéticos. CPFs falham validação de dígito verificador por construção; IPs e domínios ficam em faixas reservadas a documentação
- Cenários podem usar atores de ameaça reais e documentados publicamente, sem reproduzir IOC operacional
- Banner de ambiente simulado em toda tela e em todo artefato gerado

Seis verificadores automáticos aplicam essas regras no CI, por análise de árvore sintática. Cada um é testado contra violações plantadas de propósito — um verificador que nunca falhou contra uma violação plantada não é um verificador.

---

## Estado

**Fase 0 em fechamento.** A especificação está congelada na tag `spec-v1.0`, os seis verificadores estão implementados e o CI roda com proteção de branch e `enforce_admins`. Nenhuma linha de código de aplicação foi escrita ainda — é assim por desenho.

A fase **não está declarada concluída**: dois itens da Definition of Done seguem abertos e cinco estão fechados por atestação do operador, não por verificação independente. O estado item a item está em [`docs/progress/fase_0.md`](docs/progress/fase_0.md), incluindo o que **não** foi possível verificar e por quê.

O roadmap tem doze fases. A Fase 4 é o primeiro marco visível: o console do facilitador dispara um evento e o wallboard reage ao vivo.

A especificação vive em [`docs/spec/`](docs/spec/) e é imutável a partir da tag — alterações exigem PR próprio, sem código junto, com o gate demonstrado antes de ser ligado.

## Como este repositório é construído

O projeto é desenvolvido com assistência de IA sob um regime de verificação explícito, e o regime é parte do produto.

Cada checkpoint de fase é auditado por um agente adversarial em contexto isolado, que roda num worktree fixado no commit candidato, não recebe ferramentas de escrita e emite PASS/FAIL contra a especificação. Ele vive fora do repositório de propósito: **um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit.**

A Fase 0 passou por **dezesseis rodadas dessas. Dez reprovaram.** O aparato encontrou defeitos reais no próprio aparato — entre eles um teste que passava sem exercitar a fronteira que deveria verificar, um probe que passava pelo motivo errado carregando o nome da propriedade que não media, e dois casos em que a correção reintroduziu a classe de erro que ela fechava.

Nada disso foi apagado. Cada rodada tem relatório versionado em `docs/progress/`, com veredito, evidência e encaminhamento — inclusive as reprovações, as premissas falsas que sobreviveram seis rodadas e as decisões tomadas apesar de um FAIL, com as condições que as sustentam.

## Licença e origem

Projeto pessoal de Flavio Costa.

Agnóstico de fornecedor por desenho: a especificação proíbe explicitamente conteúdo de portfólio dentro do cenário. Lacunas de capacidade identificadas durante um exercício são registradas por **função de controle**, nunca por produto.
