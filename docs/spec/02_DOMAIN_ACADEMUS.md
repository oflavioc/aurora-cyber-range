# 02 — DOMÍNIO ACADEMUS

Universidade Aurora — 28.000 alunos, 1.200 professores, 60 cursos, 5 campi, presencial e EAD, pesquisa com HPC, identidade federada.

---

## 1. Entidades

Aluno, Professor, Curso, Disciplina, Turma, Matrícula, Diário, Nota, HistóricoEscolar, Diploma, Bolsa, ContratoFinanciamento, QuestãoVestibular, ProjetoPesquisa, JobHPC, Usuário, **CalendarioAcademico**, **AutorizacaoRetificacao**, **Incidente**, **Declaracao**.

## 2. CalendarioAcademico

Sem esta entidade a Linha B não é detectável.

Campos: semestre, início e fim de aulas, janela de lançamento de notas, **janela de retificação**, período de matrícula, data de colação, período de vestibular.

Seed popula 8 semestres coerentes. Toda alteração de nota calcula `within_window` contra ela no momento da gravação.

## 3. AutorizacaoRetificacao

Entidade que torna a Linha B realista. Registra retificação **legítima** fora da janela: solicitante, coordenador aprovador, justificativa, número de processo, data.

Sem ela, "fora da janela = fraude" e o exercício vira busca por filtro `WHERE within_window = false`.

## 4. Trilha de auditoria — mecanismo, não convenção

"Append-only e imutável" exige implementação. PostgreSQL não garante nada por si.

**Obrigatório:**

1. Tabela dedicada `audit_trail`, separada das tabelas operacionais
2. Role `academus_app` com `INSERT` apenas; `REVOKE UPDATE, DELETE, TRUNCATE`
3. Trigger `BEFORE UPDATE OR DELETE` que levanta exceção incondicionalmente
4. **Encadeamento de hash**: cada linha grava `prev_hash` e `row_hash = SHA256(prev_hash || payload_canônico)`
5. Endpoint `GET /audit/verify-chain` que percorre e reporta a primeira quebra
6. Migration controlada; nenhuma alteração de schema da tabela sem nova migration versionada

**Valor pedagógico:** permite um inject em que alguém questiona se a própria trilha foi adulterada. A cadeia de hash responde — e o exercício ensina que trilha de auditoria não é log.

### 4.1 O que registrar

**Alteração de nota** — nota anterior, nova nota, usuário, IP, user-agent, timestamp duplo, semestre, disciplina, `within_window`, `authorization_id` (nulo quando não houver).

**Emissão de diploma** — usuário, horário, campus, curso, aluno.

**Banco de questões** — acesso, pesquisa, exportação, impressão.

**Pesquisa acadêmica** — leitura massiva, download, alteração.

**Declarações do exercício** — todas as ações de `declare_*` (`03_EXERCISE_DESIGN.md` §3.1).

---

## 5. Dataset

28.000 alunos, 1.200 professores, 60 cursos, 8 semestres. Distribuição plausível de CR, reprovação, evasão e bolsas.

**Desempenho:** volume passa de milhões de registros de nota. Seed via `COPY` / `executemany`, nunca ORM linha a linha. Alvo: < 5 min.

**Determinismo:** `RANDOM_SEED` fixo. Mesmo seed → mesmo dataset, mesma Linha B, mesmas evidências.

---

## 6. Linha B — desenho de dificuldade

Encontrar 40 eventos estranhos é trivial depois que alguém abre o audit log. O exercício não é esse. O exercício é **demonstrar, com confiança declarada, quais eventos são indevidos.**

### 6.1 População plantada

| Conjunto | Volume | Características |
|---|---|---|
| **Indevidos comprovados** | 22 | Conta docente única, IP de laboratório compartilhado, fora da janela, **sem** `AutorizacaoRetificacao`, sempre elevando nota, sempre no mesmo grupo de alunos, sempre entre 22h e 02h |
| **Ambíguos legítimos** | 11 | Fora da janela, **com** autorização, mas justificativa genérica e aprovador que também aparece nos indevidos. Genuinamente inconclusivos |
| **Legítimos suspeitos à primeira vista** | 34 | Fora da janela, com autorização sólida, IP de laboratório, horário noturno. Parecem fraude; não são |
| **Ruído de manutenção** | ~60 | Correções em lote por migração de sistema, marcadas com usuário `svc_migration` |
| **Credenciais compartilhadas** | 18 | Monitor/assistente usando conta do professor com registro formal de delegação |
| **Legítimos normais** | milhares | Dentro da janela |

### 6.2 Avaliação por calibração, não por recall

O critério **não** é encontrar 40 de 40. É a relação entre confiança declarada e força real da evidência.

Cada caso carrega `defensibility ∈ [0,1]` em `ground_truth.yaml`: 1.0 para indevido comprovado, 0.5 para ambíguo, 0.0 para legítimo (inclusive os de aparência suspeita, manutenção e delegação).

A equipe submete, por caso:

```yaml
assessment:
  case_id: GC-029
  classification: suspicious
  confidence: 72
  evidence: [DBA-28391, DBA-28402]
  rationale: "Alteração fora da janela, sem autorização, conta incompatível
              com a disciplina, horário fora de expediente."
```

E declara previamente o **escopo revisado** (período, população, critério), o que separa erro de julgamento de lacuna de cobertura.

Escore de Brier e sinalizações comportamentais: `03_EXERCISE_DESIGN.md` §5.

**Overconfidence é o erro mais interessante deste cenário.** Declarar alta confiança sobre os 34 legítimos de aparência suspeita leva à anulação de notas de formandos inocentes — custo institucional maior que deixar um caso duvidoso em aberto. O AAR trata overconfidence e falso negativo separadamente e não os compensa entre si.

Liga a OBJ-04 (viés de confirmação) e OBJ-07 (integridade).

### 6.3 Gabarito: máquina e humano

`ground_truth.yaml` contém os casos com `case_id`, `set`, `defensibility` e evidências de suporte. É a fonte autoritativa, lida pelo motor de calibração.

`GM_NOTES.md` explica ao facilitador por que cada conjunto existe, com a query de referência que separa indevidos de ambíguos e a razão de os 34 parecerem suspeitos. **Não pode conter fato ausente do ground truth** — o linter compara e recusa divergência.

Ambos excluídos do build servido aos participantes.

## 7. Aplicação

**academus-api** — FastAPI + SQLAlchemy. Consome o flag registry do core para degradar respostas (latência, 503, readonly, falha de autenticação).

**academus-web**
- Portal do Aluno: matrícula, notas, histórico, financeiro, solicitações
- Portal do Professor: diário, frequência, lançamento de notas
- Secretaria: relatórios, diplomas, históricos
- Financeiro: contratos, bolsas, inadimplência
- AVA simplificado: disciplinas, conteúdos, provas
- **Modo "Prova em andamento"**: cronômetro, autosave, monitoramento de sessões. Principal alvo das degradações e maior gerador de impacto visível
- **Console de investigação**: consulta à trilha de auditoria com filtros de período, usuário, IP, janela e autorização. É onde os marcadores `auto` de evidência são emitidos

**Dashboards por persona** — ver `03_EXERCISE_DESIGN.md` §5.

**federated-identity-simulator** — Entra ID, Google Workspace, SAML, Shibboleth fictícios. Injects: `academus.sso_unavailable`, `academus.token_validation_delay`, `academus.federation_anomaly`.

**mec-gateway** — consulta de diplomas, calendário regulatório, indicadores. Injects: `academus.mec_gateway_unavailable`, `academus.regulatory_inquiry`.

---

## 8. Ecossistema externo simulado

Cada um é um serviço stub com status próprio e flag correspondente:

`lms_vendor` (fornecedor de AVA), `workspace_provider` (M365/Workspace fictício), `payment_gateway`, `digital_library`, `admissions_platform` (vestibular), `ead_partner`, `research_consortium`, `cloud_provider`.

Valor: a instituição descobre que parte da resposta não está sob seu controle — e que contrato, SLA e canal de escalonamento com terceiro fazem parte do plano de crise.

---

## 9. Ações de continuidade acadêmica

Ações reais disponíveis nos dashboards, cada uma com custo e efeito mecânico:

| Ação | Efeito | Custo |
|---|---|---|
| Aplicação de prova offline | Restaura avaliação | Logística, atraso, risco de integridade |
| Congelamento de lançamento de notas | Impede propagação de adulteração | Trava o calendário |
| Matrícula manual | Mantém período aberto | Capacidade limitada, fila física |
| Extensão do prazo de matrícula | Alivia pressão | Impacto em calendário e repasse |
| Adiamento de prova | Preserva integridade da avaliação | Conflito com colação |
| Emissão emergencial de documentos | Atende formandos | Risco de emitir sobre dado não validado |
| Recuperação acadêmica | Remedia perda de avaliação | Custo docente |

**A pergunta que o range deve provocar:** *a infraestrutura voltou — podemos liberar o lançamento de notas?*

Isso é OBJ-10 e é medido por `TTV − TTRS`. Muito mais interessante que "o servidor voltou".

---

## 10. Eventos de telemetria do adapter

`domains/academus/telemetry_events.yaml`:

`AUTH_FAIL`, `AUTH_BRUTE`, `BULK_STUDENT_EXPORT`, `EXAM_BANK_ACCESS`, `GRADE_CHANGE_RETROACTIVE`, `SSO_FEDERATION_ANOMALY`, `RADIUS_IMPOSSIBLE_TRAVEL`, `HPC_JOB_ANOMALY`, `DIPLOMA_ISSUE_OFFHOURS`, `MASS_ENROLLMENT_CHANGE`, `SERVICE_ACCOUNT_ANOMALY`, `RESEARCH_REPO_BULK_READ`.

Campos CEF: `src`, `dst`, `suser`, `severity`, `outcome`, `cnt`, `cs1`–`cs4` com contexto do domínio (campus, curso, semestre, disciplina).
