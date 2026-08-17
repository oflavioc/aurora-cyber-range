// O PAYLOAD, COMO ELE VEM — os tipos espelham `range-core/api/projecoes.py`.
//
// Nao ha tipo "estado da tela" ao lado destes: o frame e TOTAL (D3), entao a
// tela e uma funcao do payload e nao ha o que acumular. Um segundo tipo, montado
// no cliente, seria o lugar onde a divergencia com o servidor comeca.
//
// O QUE NAO ESTA AQUI, E POR QUE
// -------------------------------
// Nenhum nome de flag, nenhum `severity_weight` bruto de contrato, nenhum
// `event_type`. O que chega e o que a projecao ja decidiu mostrar: `rotulo` sai
// do `effect_ui`, e a selecao dos tres destaques e do servidor (D16/D17).
//
// `scripts/check_web_sem_derivacao.py` guarda a outra metade: estas colecoes so
// podem ser consumidas por `.map(`. Ordenar, filtrar ou cortar aqui trocaria
// QUAIS itens aparecem no telao, e o teste de orcamento continuaria verde —
// porque ele mede o payload, e o payload continuaria certo.

/** Um painel do telao: responde *onde*, e nao *o que*. */
export type Bloco = {
  grupo: string;
  ativos: number;
  total: number;
  /** Do PIOR ativo do grupo. Vazia quando nada esta ativo ali. */
  categoria: string;
  severidade: number;
};

/** Um dos `DESTAQUES_NO_TELAO` piores ativos, em texto. */
export type Destaque = {
  rotulo: string;
  categoria: string;
  severidade: number;
};

export type Wallboard = {
  indice_de_saude: number;
  paineis: Bloco[];
  destaques: Destaque[];
  /** Quantos ativos ficaram FORA dos destaques. Numero, e nao lista: o cliente
   *  nao precisa contar, e por isso nao pode. */
  omitidos: number;
};

/** `01_ARCHITECTURE.md` secao 6: a plateia recebe um campo, e so. */
export type Plateia = {
  texto: string;
};

/** `category` e vocabulario FECHADO de `01_ARCHITECTURE.md` secao 5.2 — sete
 *  valores. A codificacao visual e por ele (secao 5.3), e a 10 m a cor e lida
 *  antes do texto.
 *
 *  ISTO NAO E DERIVACAO: nao escolhe o que aparece nem em que ordem, so pinta o
 *  que ja veio escolhido. E ha fallback para categoria desconhecida — vocabulario
 *  que crescer aparece cinza, e nao some. */
export const COR_DA_CATEGORIA: Record<string, string> = {
  availability: "bg-amber-400",
  integrity: "bg-rose-500",
  confidentiality: "bg-fuchsia-500",
  identity: "bg-sky-400",
  performance: "bg-orange-400",
  narrative: "bg-violet-400",
  regulatory: "bg-emerald-400",
};

export const COR_NEUTRA = "bg-slate-700";

export function corDa(categoria: string): string {
  return COR_DA_CATEGORIA[categoria] ?? COR_NEUTRA;
}
