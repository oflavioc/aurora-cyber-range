// O TELAO — `01_ARCHITECTURE.md` secao 6: sem login, WebSocket, alto contraste,
// legivel a 10 m, renderizado por convencao a partir da taxonomia.
//
// O QUE ESTA TELA NAO FAZ
// ------------------------
// Nao seleciona, nao ordena e nao conta. O indice, os blocos, QUAIS tres
// destaques aparecem e quantos ficaram de fora chegam decididos — D16 e D17 —, e
// `scripts/check_web_sem_derivacao.py` reprova quem tentar refazer qualquer uma
// dessas quatro coisas aqui.
//
// A conta que decidiu o tamanho da letra esta em `projecoes.py`, na constante
// `DESTAQUES_NO_TELAO`: a 10 m cabem 7 a 8 linhas na tela inteira. Por isso as
// medidas sao em `vw` e nao em `px` — a mesma tela precisa caber no monitor de
// quem desenvolve e no telao da sala.
//
// NAO OPERA O EXERCICIO: nao dispara, nao rebobina, nao pede token. As duas
// projecoes publicas de `05_SECURITY_REQUIREMENTS.md` secao 8 sao as unicas
// coisas que ela conhece.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { useCanal } from "../src/canal";
import { corDa, type Wallboard } from "../src/payload";
import "../src/estilo.css";

/** A cor do numero. Pintura sobre o valor que veio, e nao um segundo criterio de
 *  saude: o numero em si e do servidor. */
function corDoIndice(saude: number): string {
  if (saude >= 80) {
    return "text-emerald-400";
  }
  if (saude >= 50) {
    return "text-amber-400";
  }
  return "text-rose-500";
}

function Telao() {
  const { estado, ligado } = useCanal<Wallboard>("/ws/wallboard");

  if (estado === null) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-950 text-[3vw] text-slate-500">
        aguardando o exercício…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-[1.5vw] bg-slate-950 p-[2vw] text-slate-100">
      <header className="flex items-baseline gap-[2vw]">
        <h1 className="text-[1.8vw] uppercase tracking-[0.3em] text-slate-400">
          Universidade Aurora
        </h1>
        <span
          className={`ml-auto text-[1.2vw] ${ligado ? "text-slate-500" : "text-rose-400"}`}
        >
          {ligado ? "ao vivo" : "reconectando…"}
        </span>
      </header>

      <div className="flex items-center gap-[3vw]">
        <div
          className={`text-[16vw] font-black leading-none ${corDoIndice(estado.indice_de_saude)}`}
        >
          {estado.indice_de_saude}
        </div>

        <div className="flex flex-1 flex-wrap gap-[1vw]">
          {estado.paineis.map((bloco) => (
            <section
              key={bloco.grupo}
              className="min-w-[14vw] flex-1 rounded-[0.6vw] border border-slate-800 bg-slate-900 p-[0.9vw]"
            >
              <div className="flex items-center gap-[0.6vw]">
                <span
                  className={`h-[1vw] w-[1vw] rounded-full ${corDa(bloco.categoria)}`}
                />
                <h2 className="text-[1.3vw] uppercase tracking-wider text-slate-400">
                  {bloco.grupo}
                </h2>
              </div>
              <p className="text-[2.6vw] font-bold leading-tight">
                {bloco.ativos}
                <span className="text-[1.6vw] font-normal text-slate-500">
                  /{bloco.total}
                </span>
              </p>
            </section>
          ))}
        </div>
      </div>

      <ul className="flex flex-col gap-[0.8vw]">
        {estado.destaques.map((destaque) => (
          <li key={destaque.rotulo} className="flex items-center gap-[1.2vw]">
            <span
              className={`h-[1.6vw] w-[1.6vw] shrink-0 rounded-full ${corDa(destaque.categoria)}`}
            />
            <span className="text-[3vw] leading-tight">{destaque.rotulo}</span>
          </li>
        ))}
      </ul>

      {/* `omitidos` chega como NUMERO. O corte se anuncia: sem esta linha a sala
          leria "tres problemas" onde ha treze. */}
      {estado.omitidos > 0 ? (
        <p className="text-[1.8vw] text-slate-500">
          + {estado.omitidos} outros efeitos ativos
        </p>
      ) : null}
    </div>
  );
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Telao />
  </StrictMode>,
);
