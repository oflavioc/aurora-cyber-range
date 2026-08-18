# Aurora Cyber Range

Motor reutilizável de exercícios de crise cibernética, com domínios de negócio acopláveis. **Nenhum ataque é executado.**

[![invariantes](https://github.com/oflavioc/aurora-cyber-range/actions/workflows/invariants.yml/badge.svg)](https://github.com/oflavioc/aurora-cyber-range/actions/workflows/invariants.yml)

<!-- identidade visual: sem asset versionado. Ponto marcado para inclusão futura. -->

---

## O problema

A maior parte dos tabletop exercises acontece em slides. Alguém narra *"imagine que o sistema de matrícula caiu"*, e a mesa discute o que faria. Ninguém consulta nada, porque não há nada para consultar; ninguém descobre nada, porque a informação já está no enunciado. O exercício mede a capacidade de argumentar sobre uma hipótese — que é uma habilidade real, e não é a que a crise cobra.

O Aurora move o incidente para dentro de um sistema que responde. Um facilitador dispara um evento de cenário e o endpoint de matrícula passa a devolver `503` de verdade, para todo mundo, até que alguém o restaure. As telas da sala mudam porque o estado mudou, não porque o slide virou. O que a equipe sabe passa a depender do que ela foi procurar.

A diferença que isso produz não é dramaticidade: é **medição**. Quando o sistema tem estado próprio, existe um fato contra o qual comparar o que a equipe declarou — e a distância entre os dois é o achado do debriefing.

## O que é

Um motor (`range-core/`) e domínios de negócio acopláveis (`domains/`). O motor não sabe o que é uma matrícula; o domínio não sabe o que é um inject.

| Peça | O que faz |
|---|---|
| **Engine** | relógio de exercício com pausa e multiplicador, event store append-only, projeção de estado de simulação, disparo de inject, rollback com epoch |
| **Adapter de domínio** | a aplicação que degrada — entidades, regras, telas, dados sintéticos |
| **Cenário** | pacote versionado com injects, ground truth, objetivos e ramificações |
| **gm-console** | o facilitador: lista de injects, disparo, rollback, controle do relógio |
| **wallboard** | o telão da sala, sem login: índice de saúde institucional e o que está degradado |
| **participant-view** | a projeção do participante, com a narrativa e nada além dela |
| **AAR** | o debriefing, com o que foi declarado ao lado do que foi verificado |

**Nenhum ataque é executado, e isso é restrição de projeto, não postura.** Não há exploit, malware, ransomware funcional, criptografia real de arquivo, movimentação lateral, payload ofensivo nem vulnerabilidade intencional. Todo efeito de incidente é uma flag de estado da aplicação — `academus.enrollment_offline: true` faz a matrícula cair, e é literalmente isso que acontece.

## Como funciona

```text
    facilitador              participantes            telão da sala
         │                        │                        │
    gm-console            participant-view          wallboard-shell     range-core/web/
         └────────────────────────┴────────────────────────┘
                                  │  HTTP + WebSocket
                                  │  (frame de estado TOTAL, nunca delta)
                        ┌─────────┴──────────┐
                        │      range-api     │                          range-core/api/
                        ├────────────────────┤
                        │ exercise-clock     │  inject-engine           range-core/
                        │ event store        │  projeção de simulação
                        └─────────┬──────────┘
                                  │
                           ┌──────┴───────┐    eventos append-only
                           │  PostgreSQL  │    + business state
                           └──────┬───────┘
                                  │  lê a projeção, degrada por flag
                        ┌─────────┴──────────┐
                        │    academus-api    │                          domains/academus/
                        └────────────────────┘
```

Duas propriedades desse desenho valem ser ditas, porque explicam quase todo o resto:

**Toda derivação é do servidor.** Painéis, índice de saúde, timeline e o texto que a plateia lê são calculados em Python e verificados em Python. O cliente recebe pronto e pinta. Lógica que descesse para o navegador sairia do alcance dos testes.

**O frame é estado total, nunca incremento.** Um `refresh` do browser recupera o estado corrente porque não há o que acumular — a recuperação é propriedade do protocolo, e não disciplina do cliente.

## O modelo das quatro verdades

É a estrutura normativa do projeto. Confundir duas destas camadas invalida o debriefing.

```text
GROUND TRUTH           o que de fato ocorreu
      ↓
OBSERVABLE EVIDENCE    o que pode ser descoberto
      ↓
PARTICIPANT BELIEF     o que a equipe crê e declara
      ↓
EVALUATOR ASSESSMENT   o que o avaliador julgou
```

**Declaração não é verdade.** Registrar que a equipe *afirma* ter contido o incidente nunca altera o ground truth. Se alterasse, declarar cedo melhoraria a nota mesmo com a contenção errada — e o exercício passaria a treinar exatamente isso.

Disso saem os quatro eixos que o projeto pretende avaliar:

- **Métricas pareadas** — cada métrica de resposta tem duas: o que foi declarado e o que foi verificado por predicado objetivo. Se a equipe declara contenção aos 31 minutos e o incidente só é verificavelmente contido aos 52, o relatório mostra os dois números e os eventos incompatíveis no intervalo.
- **Calibração** — a confiança declarada corresponde à força real da evidência? Acusar com certeza um caso que não se sustenta pesa mais do que deixar um caso duvidoso em aberto.
- **Assimetria de informação** — cada persona recebe uma projeção diferente do ground truth, com defasagem e confiança distintas. Ninguém tem o quadro completo, que é a característica definidora de uma crise real.
- **Integridade × disponibilidade** — o sistema voltou, mas dá para confiar no dado que está nele?

Há ainda um quinto valor de camada, `facilitation`, para os eventos da máquina de exercício — disparo, rollback, pausa. Eles não afirmam nada sobre o incidente, e por isso não são uma quinta verdade: entram no debriefing como linha de operação, nunca como desempenho da equipe.

> Os quatro eixos acima são **desenho normativo**, especificado e ainda não implementado. Métricas pareadas e calibração são da Fase 6; assimetria e AAR, da Fase 10. Ver [o que já existe](#o-que-já-existe).

## Primeiro domínio — UniAurora

**Universidade Aurora (UniAurora)** — 28.000 alunos, 1.200 professores, 5 campi, ensino presencial e EAD, pesquisa com ambiente HPC e identidade federada. O ERP acadêmico chama-se **ACADEMUS**.

A escolha não é temática. Uma universidade tem calendário rígido com janelas irreversíveis, uma população que não pode ser desligada, obrigação regulatória de guarda documental e um sistema acadêmico onde integridade importa mais que disponibilidade — o diploma errado é pior que o portal fora do ar.

Um segundo adapter hospitalar — **Hospital Regional Aurora**, sistema **PRONTUS** — existe como **stub declarado**: duas flags e um documento, sem modelo, tela ou cenário. Ele existe para que a fronteira arquitetural seja verificável em vez de afirmada: `academus.enrollment_offline` e `prontus.admission_offline` são a mesma classe de efeito em domínios diferentes, e sem o prefixo colidiriam.

## Estado atual

**Fases 0 a 5 concluídas.** Próximo checkpoint: **Fase 6 — Objetivos, rubricas, métricas**. O roadmap tem **12 fases**.

A Fase 4 é o *vertical slice*: o caminho ponta a ponta mínimo, exigido cedo de propósito, para que a arquitetura falhe antes de haver o que reescrever. O que ele prova, contra dois containers, Postgres e Redis reais:

```text
GM clica o inject A01
   → engine grava o evento e muda a projeção
   → academus-api degrada o endpoint de matrícula
   → wallboard reage em < 1 s via WebSocket
   → participant-view exibe o texto da plateia
   → GM clica ROLLBACK
   → estado restaurado; evento de rollback anotado na timeline
```

A asserção que discrimina é o par em volta do rollback: **a mesma** requisição de matrícula responde `503` depois do disparo e `201` depois da restauração. Uma API que nunca degradasse passaria na segunda; uma que degradasse sempre passaria na primeira. Só as duas juntas dizem que o estado voltou.

Números, com a forma que os mediu:

| | |
|---|---|
| **402 testes** | `python -m unittest discover -s tests`, em 18/08/2026. 140 exigem Postgres ou containers e pulam sem a stack no ar |
| **latência do frame** | 47 ms medidos ponta a ponta no DEMO, contra um orçamento de 1 s |
| **reinício** | provado com `docker restart` real, comparando `StartedAt` antes e depois — pausado restaura pausado, retomado restaura correndo |

Nenhum exercício real foi conduzido com o sistema. Nenhum pacote de cenário existe ainda — `scenarios/` está vazio, e o primeiro pack é da Fase 7.

## O que já existe

Derivado da árvore de código, não da especificação. Diretório que existe vazio conta como **planejado**.

| Componente | Onde | Estado |
|---|---|---|
| exercise-clock — pausa, multiplicador, três marcas temporais | `range-core/clock/` | implementado |
| event store append-only, envelope universal, `simulation_epoch` | `range-core/events/` | implementado |
| projeção de simulação e cache | `range-core/state/` | implementado |
| inject-engine — carga de pack, effects declarativos, rollback | `range-core/engine/` | implementado |
| range-api — HTTP, WebSocket, autenticação do console | `range-core/api/` | implementado |
| gm-console, wallboard, participant-view | `range-core/web/` | implementado no mínimo da Fase 4 |
| academus-api — JWT, RBAC, três entidades, degradação por flag | `domains/academus/api/` | implementado no mínimo da Fase 3 |
| business state em PostgreSQL | `domains/academus/models/`, `alembic/` | parcial — quatro tabelas e migration, sem seed em escala |
| adapter hospitalar PRONTUS | `domains/prontus/` | stub declarado — duas flags e um documento |
| trilha de auditoria com hash encadeado | `domains/academus/audit/` | implementado na Fase 5 — `INSERT`-only por role e por trigger, com `GET /audit/verify-chain` |
| objetivos e binding evento→objetivo | `range-core/objectives/` | planejado, Fase 6 |
| rubricas BARS versionadas | `range-core/rubrics/` | planejado, Fase 6 |
| métricas pareadas e calibração | `range-core/metrics/` | planejado, Fase 6 |
| branching de cenário e `range-cli` | `range-core/engine/branching/` | planejado, Fase 7 |
| pacote de cenário | `scenarios/` | vazio, Fase 7 |
| dashboards por persona, feed social, ações de continuidade | — | planejado, Fase 8 |
| evidence-simulator | `range-core/evidence/` | planejado, Fase 9 |
| telemetry-forwarder | `range-core/telemetry/` | planejado, Fase 9 |
| assimetria de informação e AAR completo | `range-core/aar/` | planejado, Fase 10 |

## Roadmap

As 12 fases estão em [`docs/spec/07_IMPLEMENTATION_PHASES.md`](docs/spec/07_IMPLEMENTATION_PHASES.md), ordenadas para reduzir risco e não por afinidade temática. Por isso o vertical slice vem na Fase 4, antes de qualquer expansão.

| | Fases | O que entra |
|---|---|---|
| **Fundação** ✅ | 1 – 4 | contratos e esqueleto · clock, eventos, estado, engine · API mínima com degradação por flag · **vertical slice ponta a ponta** |
| **Avaliação** | 5 – 7 | modelo de dados e trilha de auditoria com hash · objetivos, rubricas, métricas pareadas, calibração · pack completo, branching e `range-cli` |
| **Escala** | 8 – 12 | web completo e continuidade · projeção de evidência e telemetria · assimetria de informação e AAR · serviços externos e segundo pack · observabilidade |

## Segurança por desenho

As restrições vivem em [`docs/spec/05_SECURITY_REQUIREMENTS.md`](docs/spec/05_SECURITY_REQUIREMENTS.md), que não admite exceção nem flexibilização silenciosa.

- **Nenhum código ofensivo funcional.** Sem exploit, malware, ransomware, criptografia real de arquivo, movimentação lateral, payload, backdoor ou vulnerabilidade intencional. Efeito de incidente é mudança de estado, e nada além disso.
- **Dados sintéticos por construção.** CPFs **falham** validação de dígito verificador de propósito; domínios e IPs ficam em faixas reservadas a documentação (RFC 5737, RFC 3849) ou privadas. Nenhum endereço, telefone ou e-mail existente.
- **Sem IOC operacional.** Cenários podem usar atores de ameaça reais e publicamente documentados, com fonte citável declarada no ground truth — sem hash de amostra, sem infraestrutura real, sem instrução acionável de execução.
- **Banner obrigatório** de ambiente simulado em toda tela e no rodapé de todo artefato gerado, com verificador que confere fonte **e** bundle construído.
- **Separação de funções.** Ground truth e notas do facilitador são fontes de máquina, excluídas de tudo que chega ao participante. A narrativa é carregada por superfície, com whitelist: vazar deixa de ser esquecer um filtro e passa a exigir escrever um caminho novo.
- **Falha fechada.** Caminho que ninguém declarou público exige token. As superfícies sem autenticação são exatamente as que a especificação isenta, e há teste de que uma rota inexistente responde `401`.

**O alcance, dito com precisão:** os verificadores são estáticos e analisam a árvore versionada. Eles provam que este repositório não contém as construções proibidas; não provam nada sobre o comportamento de um deploy configurado por terceiros, nem substituem revisão de quem for operar o range.

## Desenvolvimento verificado

O projeto é construído com assistência de IA sob um regime de verificação explícito, e o regime é parte do produto.

**A especificação é congelada.** A tag `spec-v1.0` marca o ponto em que `docs/spec/` virou imutável durante a implementação. Ela mudou **15 vezes** desde então, e nenhuma delas junto com código: cada uma exigiu PR próprio com título `spec-change:`, com um gate de CI que reprova o PR que toca a norma e o mecanismo ao mesmo tempo. Se o código não bate com a spec, o código está errado.

**Os invariantes são gate, não convenção.** Quatro regras arquiteturais — o core não importa domínio, nenhuma string solta de nome de flag, nenhum `event_type` fora do catálogo, nenhum evento carregando `objective_ids` — têm hook local para feedback rápido e teste de CI como porta real.

**Cada verificador tem prova negativa.** São **6** verificadores em [`tools/`](tools/) e **22** em [`scripts/`](scripts/), e **21** destes últimos têm um `_probes.py` pareado que planta a violação de propósito e exige que a checagem reprove — nas duas direções, porque um guarda que bloqueia tudo também passa no teste que só mede bloqueio. A exceção é `check_progress_consistency.py`, que ainda não tem prova negativa própria. Um verificador que nunca ficou vermelho contra uma violação plantada prova que roda, não que detecta.

**Cada checkpoint de fase é auditado por um agente adversarial**, em contexto isolado, num worktree fixado no commit candidato, sem ferramentas de escrita, emitindo PASS ou FAIL contra a especificação. Ele vive fora deste repositório de propósito: um auditor definido pelo commit que ele audita pode ser enfraquecido por esse mesmo commit.

**As reprovações não são apagadas.** São **34 relatórios** de auditoria versionados em [`docs/progress/`](docs/progress/), cobrindo as Fases 0 a 5, e a maioria é de rodadas que falharam. Cada registro de fase traz as decisões, as pendências com destinatário, os limites declarados e os defeitos que o próprio aparato de verificação teve — inclusive um verificador que aprovava uma prova vazia, e uma correção que reintroduziu a classe de erro que fechava.

## Estrutura do repositório

```text
contracts/      schemas de flags, eventos, cenário, ground truth, objetivos, evidência
range-core/     o motor: clock, events, state, engine, api, web
domains/        adapters de domínio: academus (implementado), prontus (stub)
scenarios/      pacotes de cenário — vazio até a Fase 7
scripts/        verificadores de CI, DEMOs executáveis, lançador de auditoria
tools/          os seis verificadores de invariante
tests/          a suíte
alembic/        migrations
docs/spec/      a especificação — autoridade normativa
docs/process/   workflow, âncoras de fase, bootstrap
docs/progress/  registro por fase e relatórios de auditoria
user-scope/     fonte versionada dos hooks e do auditor instalados fora da árvore
```

## Quick start

Roda hoje, verificado. Requer Docker, Docker Compose e Python 3.12.

```bash
cp .env.example .env
# preencha AURORA_JWT_SECRET e AURORA_GM_PASSWORD — os placeholders são vazios
# de propósito: um segredo errado que se anuncia é menos perigoso que um que funciona

docker compose --profile build run --rm web-build        # constrói as três telas
docker compose up -d --build --wait range-api academus-api

python scripts/demo_fase4.py                             # a sequência do DEMO, com asserção em cada passo
```

Depois disso, no host:

| | |
|---|---|
| `http://127.0.0.1:8000/sala` | wallboard — o telão, sem login |
| `http://127.0.0.1:8000/plateia` | participant-view — a narrativa |
| `http://127.0.0.1:8000/console` | gm-console — autenticado |

Para olhar a sala sem containers, com store em memória e sem persistência:

```bash
AURORA_GM_PASSWORD=<credencial local> python scripts/sobe_sala.py
```

O build das telas é obrigatório: `range-core/web/dist/` não é versionado, e um clone limpo não tem tela construída.

A suíte:

```bash
python -m unittest discover -s tests
```

Sem Postgres no ar, 140 dos 402 testes pulam — os que exigem banco ou container.

## Maturidade

Motor em construção, com um caminho ponta a ponta funcionando. O que existe hoje é uma sala mínima: um inject, uma degradação real, três telas e um rollback.

O que ainda **não** existe é a maior parte do que torna um exercício avaliável — trilha de auditoria com hash, objetivos, rubricas, métricas pareadas, calibração, evidência para Blue Team, assimetria de informação e AAR. Nenhum pacote de cenário foi escrito, e nenhum exercício real foi conduzido com o sistema.

Não é software pronto para produção, e não há compromisso de estabilidade de API ou de contrato entre fases.

## Cenários públicos e privados

A fronteira pretendida separa o que pode ser distribuído do que precisa ficar fora do alcance de quem participa do exercício.

| Público | Fora da distribuição a participantes |
|---|---|
| engine, contratos, schemas, adapters | `ground_truth.yaml` — o gabarito legível por máquina |
| exemplos de pack **sanitizados** | `GM_NOTES.md` — a narrativa do facilitador |
| documentação e especificação | gabaritos de objetivo, defensibilidade e rubricas resolvidas |

A regra que a sustenta é de mecanismo, não de disciplina: a narrativa é carregada por superfície com whitelist, e a evidência gerada em `scenarios/**/evidence/` fica fora do Git por ser projeção determinista de `ground_truth.yaml` mais o `RANDOM_SEED` — reconstruída por comando, nunca versionada.

**Decidido na Fase 5:** `scenarios/` fica **fora do Git**. Este repositório é público, e a distinção que sustenta a decisão é entre o que a spec já publica e o que só o seed produz — `02_DOMAIN_ACADEMUS.md` §6.1 descreve os seis conjuntos da Linha B em detalhe, então a descrição não é gabarito; gabarito é **quais casos**, e eles saem do `RANDOM_SEED`, que mora no `.env`. Versionado fica o **gerador**, a **query de referência** e o **template de prosa** do `GM_NOTES`; os dois artefatos nascem por comando, na máquina de quem tem o seed. Um verificador reprova o PR que versionar qualquer um dos dois, e reprova também identificador concreto escrito à mão no template.

## Licença e origem

Projeto pessoal de Flavio Costa.

Agnóstico de fornecedor por desenho: a especificação proíbe explicitamente conteúdo de portfólio dentro do cenário. Lacunas de capacidade identificadas durante um exercício são registradas por **função de controle**, nunca por produto.

**Decisão pendente: escolher licença do projeto.**
