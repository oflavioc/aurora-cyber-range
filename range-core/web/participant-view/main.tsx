// A PLATEIA — `01_ARCHITECTURE.md` secao 6, `/plateia`: projecao separada, com
// o `texto_para_plateia` do inject corrente e nada mais.
//
// UM CAMPO, E A ESTREITEZA E A GARANTIA
// --------------------------------------
// O payload e `{"texto": "..."}`. `linha`, `descricao_facilitador`, `objectives`
// e `decision_point` nao estao ao alcance desta tela porque nao estao ao alcance
// da FUNCAO que a alimenta — `plateia()` recebe `inject_id -> texto`, e nao o
// inject (D6). Vazar aqui exigiria mudar o servidor, e nao esquecer um filtro.
//
// O QUE ESTA TELA AINDA NAO TEM, DECLARADO
// -----------------------------------------
// `01` secao 6 tambem pede cronometro de decisao e cronometro de deadline de
// midia. Nenhum dos dois esta no payload desta fase, e inventa-los no cliente
// seria pior que nao te-los: um relogio que o servidor nao conhece mostra a
// plateia um prazo que o exercicio nao esta contando. Eles vem quando a projecao
// os trouxer.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { BannerDeSimulacao } from "../src/banner";
import { useCanal } from "../src/canal";
import { type Plateia } from "../src/payload";
import "../src/estilo.css";

function Sala() {
  const { estado } = useCanal<Plateia>("/ws/plateia");
  const texto = estado === null ? "" : estado.texto;

  return (
    <div className="flex h-full flex-col bg-slate-950">
      <BannerDeSimulacao />
      <div className="flex flex-1 items-center justify-center p-[6vw]">
      {texto ? (
        <p className="max-w-[80vw] text-center text-[4.5vw] font-semibold leading-tight text-slate-100">
          {texto}
        </p>
      ) : (
        // Tela vazia e lida pela sala como "quebrou". Uma linha discreta diz que
        // o exercicio esta calmo, que e outra coisa.
        <p className="text-[2.5vw] text-slate-600">Universidade Aurora</p>
      )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Sala />
  </StrictMode>,
);
