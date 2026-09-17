// O QUE O CONSOLE DE INVESTIGACAO LE, E SO ELE.
//
// Aqui, e nao em `src/`, pelo mesmo motivo do `gm-console`: `src/` e varrido
// como PUBLICO por `tests/test_telas.py`, e esta tela usa `Authorization`.
//
// A CONSULTA FILTRADA E O QUE EMITE O MARCADOR — o cliente so monta a query e
// pinta o resultado. `audit_query_performed` (marcador `auto`) e gravado no
// SERVIDOR quando `GET /audit/grade-changes` roda (`domains/academus/api/
// app.py`, `alteracoes_de_nota`); o cliente nao emite nada, nao marca nada como
// suspeito e nao deriva — INV-7.

/** Uma linha da trilha filtrada — `domains/academus/api/repositorio.py`,
 *  `alteracoes_de_nota` (modo nao-agrupado). Ja vem serializada pelo servidor;
 *  a tela nao a recompoe. */
export type LinhaDeAuditoria = {
  sequence: number;
  actor_user_id: string;
  occurred_at: string;
  object_id: string;
  within_window: boolean | null;
  authorization_id: string | null;
};

/** A resposta de `GET /audit/grade-changes`. `total` chega como NUMERO — o
 *  cliente nao conta as linhas (a mesma razao do `omitidos` do telao). */
export type ResultadoDaConsulta = {
  linhas: LinhaDeAuditoria[];
  total: number;
};
