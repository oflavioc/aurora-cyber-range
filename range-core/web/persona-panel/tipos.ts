// O QUE O PAINEL DA PERSONA LE, E SO ELE.
//
// Aqui, e nao em `src/`, pelo mesmo motivo do `gm-console` e das telas irmas da
// Fase 8: `src/` e varrido como PUBLICO por `tests/test_telas.py`, e este painel
// usa `Authorization` (a view e autenticada e vinculada ao token da persona, D1).
//
// O SERVIDOR DERIVA, O CLIENTE PINTA — INV-7
// -------------------------------------------
// `GET /participant/view` devolve o frame TOTAL da camada `reported` DAQUELA
// persona (a do token, nunca a pedida no corpo). A isolacao — nunca ground truth,
// nunca a fatia de outra persona — e do SERVIDOR (`range-core/participant/
// reported.py`, T813). O cliente nao filtra, nao ordena, nao decide o que a
// persona pode ver: pinta o que veio.

/** Um evento da camada `reported`, como `GET /participant/view` o serializa
 *  (`range-core/participant/api/app.py`, `_serializa`): os campos minimos de
 *  `06` T14. O `payload` chega pronto do servidor; a tela nao o recompoe. */
export type EventoReportado = {
  event_id: string;
  truth_layer: string;
  persona: string;
  payload: Record<string, unknown>;
};

/** A resposta de `GET /participant/view`: a persona do token e o frame TOTAL. */
export type FrameReportado = {
  persona: string;
  reported: EventoReportado[];
};

/** A resposta de `POST /participant/continuity` — HOJE so o `event_id`.
 *
 *  O custo/tradeoff NAO volta nesta resposta 201. Ele chega pela camada
 *  `reported` da PROPRIA persona no proximo `GET /participant/view`: o evento
 *  `continuity_action_taken` e `participant_action` enderecado a `pro_reitoria`,
 *  entao entra no frame dela por construcao (ver `reported.py`). O painel
 *  re-consulta a view apos a acao e o custo aparece pintado ali — devolvido pelo
 *  servidor, nunca inventado no cliente (seria derivacao / INV-7). Ver o
 *  cabecalho de `main.tsx` e o relatorio desta tarefa (gap de eco no 201, T814). */
export type AcaoRegistrada = {
  event_id: string;
};

/** As SETE acoes de continuidade academica — `02_DOMAIN_ACADEMUS.md` §9. O `id`
 *  e o vocabulario FECHADO do enum de `$def continuity_action_taken_payload`
 *  (`contracts/events.schema.yaml`): e o corpo que `POST /participant/continuity`
 *  recebe, como `class_id` no `exam-mode` e `filter_user` no console. Nao e nome
 *  de flag (INV-5) nem `event_type` (INV-3) — a flag e o efeito ficam do lado do
 *  servidor, e so voltam pela `reported`, em tempo de execucao. O `rotulo` e o
 *  nome PT-BR da coluna "Acao" de `02` §9, para quem opera o painel. */
export const ACOES_DE_CONTINUIDADE: { id: string; rotulo: string }[] = [
  { id: "offline_exam", rotulo: "Prova offline" },
  { id: "freeze_grade_posting", rotulo: "Congelar lançamento de notas" },
  { id: "manual_enrollment", rotulo: "Matrícula manual" },
  { id: "enrollment_deadline_extension", rotulo: "Prorrogar prazo de matrícula" },
  { id: "exam_postponement", rotulo: "Adiar prova" },
  { id: "emergency_document_issuance", rotulo: "Emissão emergencial de documentos" },
  { id: "academic_recovery", rotulo: "Recuperação acadêmica" },
];

/** A UNICA persona que pode agir em continuidade — `03_EXERCISE_DESIGN.md` §6
 *  (painel da Pró-Reitoria Acadêmica). O SERVIDOR autoriza (403 para as demais);
 *  o painel apenas evita oferecer um botão que voltaria 403, lendo a persona que
 *  a view devolveu — nao deriva autorizacao, so a acompanha. */
export const PERSONA_DE_CONTINUIDADE = "pro_reitoria";
