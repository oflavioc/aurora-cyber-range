// O QUE O MODO "PROVA EM ANDAMENTO" LE, E SO ELE.
//
// Estes tipos moram aqui, e nao em `src/`, pelo mesmo motivo do `gm-console`:
// `src/` e compartilhado com as telas PUBLICAS, e `tests/test_telas.py` varre
// `src/` procurando `Authorization` — o cabecalho que esta tela usa. Um tipo
// desta tela em `src/` nao vazaria dado, mas dissolveria a fronteira que o teste
// guarda.
//
// O FRAME E ESTADO TOTAL — INV-7. O servidor (`domains/academus/api/
// prova_andamento.py`) deriva `alive`/`dropped` por MINUTO de exercicio; esta
// tela so pinta. Nao ha contagem, nao ha corte, nao ha relogio de parede aqui:
// quem caiu ja veio decidido.

/** O vocabulario FECHADO do frame — `prova_andamento.py`, `ALIVE`/`DROPPED`.
 *  Duas palavras e nada mais: valor fora delas seria estado que a tela nao sabe
 *  pintar, pelo mesmo motivo que o catalogo de `event_type` e fechado. */
export type EstadoDaSessao = "alive" | "dropped";

/** A resposta de `GET /exam/session-status` — `domains/academus/api/app.py`,
 *  `status_das_sessoes`. `sessions` e o frame TOTAL: TODA sessao presente, cada
 *  uma com o seu estado no minuto corrente. */
export type FrameDaProva = {
  class_id: string;
  /** O minuto de EXERCICIO que o servidor ecoa — o cronometro e este valor, e
   *  nao um relogio que o cliente conta (a plateia ja aprendeu isso: um relogio
   *  que o servidor nao conhece mostra um prazo que o exercicio nao esta
   *  contando). */
  exercise_minute: number;
  sessions: Record<string, EstadoDaSessao>;
};
