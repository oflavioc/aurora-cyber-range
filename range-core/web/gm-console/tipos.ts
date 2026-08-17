// O QUE O CONSOLE LE, E SO ELE — as duas projecoes AUTENTICADAS.
//
// Estes tipos moram aqui, e nao em `src/`, de proposito: `src/` e compartilhado
// com as duas telas PUBLICAS, e `tests/test_telas.py` afirma que nem `src/` nem
// as telas publicas mencionam o console. Um tipo de timeline em `src/` nao
// vazaria dado nenhum, mas dissolveria a fronteira que o teste guarda.

/** Uma entrada da timeline — `range-core/api/projecoes.py`, `timeline()`. */
export type EntradaDaTimeline = {
  event_id: string;
  epoch: number;
  exercise_time: string;
  tipo: string;
  /** Ja vem escrito pelo servidor: o console nao traduz `event_type`. */
  rotulo: string;
  inject_id?: string;
  rollback?: {
    motivo: string;
    para: string | null;
  };
};

export type Timeline = {
  entradas: EntradaDaTimeline[];
};

/** Um inject do pack, como `GET /injects` o entrega. `titulo` e o
 *  `titulo_operacional` — a narrativa de facilitacao nao chega aqui nesta fase. */
export type Inject = {
  id: string;
  t_relative: string;
  titulo: string;
  disparado: boolean;
};

export type ListaDeInjects = {
  injects: Inject[];
};
