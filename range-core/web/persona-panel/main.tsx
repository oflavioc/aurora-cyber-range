// PAINEL DA PERSONA — `03_EXERCISE_DESIGN.md` §6, `07` Fase 8 itens 3 e 4.
//
// UM MODULO, PARAMETRIZADO PELA PERSONA (R9 §7)
// ----------------------------------------------
// Nao ha sete telas — ha UMA, e a persona e um parametro que chega do SERVIDOR,
// nunca escolhido pelo cliente. `GET /participant/view` e vinculada ao token
// (D1): quem apresenta a credencial de uma persona ve a fatia DAQUELA persona, e
// o corpo devolve `{"persona": <persona>, "reported": [...]}`. O painel pinta a
// persona que veio e o frame `reported` dela — o mesmo componente serve as sete.
//
// O SERVIDOR DERIVA, O CLIENTE PINTA — INV-7
// -------------------------------------------
// A isolacao (nunca ground truth, nunca a fatia de outra persona) e do servidor
// (`reported.py`, T813). Aqui nao ha filtro, ordenacao nem corte: o frame e TOTAL
// e a tela e funcao dele. `scripts/check_web_sem_derivacao.py` guarda a fronteira
// — as colecoes so sao consumidas por `.map(`.
//
// ITEM 4 — AS SETE ACOES DE CONTINUIDADE, E DE ONDE VEM O CUSTO
// -------------------------------------------------------------
// So a persona `pro_reitoria` age (`03` §6); o SERVIDOR autoriza (403 para as
// demais), e o painel apenas nao oferece o botao a quem voltaria 403. Cada botao
// dispara `POST /participant/continuity` com `{"action_id": ...}`.
//
// O custo/tradeoff da acao NAO volta na resposta 201 (que hoje traz so o
// `event_id` — ver o relatorio desta tarefa, gap de eco em T814). Ele NAO e
// inventado aqui: inventar o texto no cliente seria derivacao (INV-7). O evento
// `continuity_action_taken` e `participant_action` enderecado a `pro_reitoria`,
// entao entra na camada `reported` DELA por construcao (`reported.py`). Apos a
// acao o painel RE-CONSULTA `GET /participant/view`, e o custo aparece pintado no
// frame — devolvido pelo servidor, na fatia da propria persona.
//
// O TOKEN VIVE NA MEMORIA DA ABA — como no `gm-console` e nas telas irmas:
// recarregar pede a credencial de novo. `POST /participant/session` a troca por
// token; a porta de entrada aqui e o token colado.

import { StrictMode, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";

import { BannerDeSimulacao } from "../src/banner";
import {
  ACOES_DE_CONTINUIDADE,
  PERSONA_DE_CONTINUIDADE,
  type AcaoRegistrada,
  type EventoReportado,
  type FrameReportado,
} from "./tipos";
import "../src/estilo.css";

/** Pintura de um valor de payload, sem juizo sobre ele: o servidor ja decidiu o
 *  que a persona ve. Objeto vira JSON legivel; `null`/ausente vira travessao. */
function pinta(valor: unknown): string {
  if (valor === null || valor === undefined) {
    return "—";
  }
  if (typeof valor === "object") {
    return JSON.stringify(valor);
  }
  return String(valor);
}

async function leView(token: string): Promise<FrameReportado> {
  const resposta = await fetch("/participant/view", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resposta.ok) {
    throw new Error(`${resposta.status} — ${await resposta.text()}`);
  }
  return (await resposta.json()) as FrameReportado;
}

async function disparaContinuidade(
  token: string,
  actionId: string,
): Promise<AcaoRegistrada> {
  const resposta = await fetch("/participant/continuity", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action_id: actionId }),
  });
  if (!resposta.ok) {
    throw new Error(`${resposta.status} — ${await resposta.text()}`);
  }
  return (await resposta.json()) as AcaoRegistrada;
}

/** Um evento da camada `reported`, pintado como veio. Um `continuity_action_taken`
 *  traz `cost` no payload — e e assim que o custo da acao chega a tela, pela
 *  fatia da propria persona, e nao por texto assado no cliente. */
function Evento({
  evento,
  destacado,
}: {
  evento: EventoReportado;
  destacado: boolean;
}) {
  const borda = destacado ? "border-sky-400" : "border-slate-700";
  return (
    <li className={`flex flex-col gap-1 rounded border ${borda} bg-slate-800 px-3 py-2`}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs uppercase tracking-wider text-slate-400">
          {evento.truth_layer}
        </span>
        <span className="font-mono text-xs text-slate-500">{evento.event_id}</span>
      </div>
      <dl className="grid grid-cols-1 gap-1 md:grid-cols-2">
        {Object.entries(evento.payload).map(([chave, valor]) => (
          <div key={chave} className="flex gap-2 text-sm">
            <dt className="text-slate-400">{chave}:</dt>
            <dd className="text-slate-100">{pinta(valor)}</dd>
          </div>
        ))}
      </dl>
    </li>
  );
}

function Painel() {
  const [token, setToken] = useState("");
  const [frame, setFrame] = useState<FrameReportado | null>(null);
  const [erro, setErro] = useState("");
  const [ultimaAcao, setUltimaAcao] = useState<AcaoRegistrada | null>(null);
  const [acaoErro, setAcaoErro] = useState("");

  const carrega = async (evento: FormEvent) => {
    evento.preventDefault();
    setErro("");
    setAcaoErro("");
    setUltimaAcao(null);
    try {
      setFrame(await leView(token));
    } catch (falha) {
      setFrame(null);
      setErro(falha instanceof Error ? falha.message : "falha ao carregar a view");
    }
  };

  const age = async (actionId: string) => {
    setAcaoErro("");
    try {
      const registrada = await disparaContinuidade(token, actionId);
      setUltimaAcao(registrada);
      // RE-CONSULTA: o custo da acao chega pela `reported` da persona, e nao pela
      // resposta 201 — o servidor derivou, a tela repinta o frame TOTAL.
      setFrame(await leView(token));
    } catch (falha) {
      setAcaoErro(falha instanceof Error ? falha.message : "falha ao disparar a ação");
    }
  };

  const podeAgir = frame !== null && frame.persona === PERSONA_DE_CONTINUIDADE;

  return (
    <div className="min-h-screen bg-slate-900">
      {/* `05` §4: em TODA tela, sem excecao. Fica acima de tudo. */}
      <BannerDeSimulacao />
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6 text-slate-100">
        <header className="border-b border-slate-700 pb-4">
          <h1 className="text-sm uppercase tracking-widest text-slate-400">
            AURORA — painel da persona
          </h1>
        </header>

        <form
          onSubmit={carrega}
          className="grid grid-cols-1 gap-3 rounded border border-slate-700 bg-slate-800 p-4 md:grid-cols-3"
        >
          <input
            type="password"
            value={token}
            onChange={(evento) => setToken(evento.target.value)}
            placeholder="token da persona"
            className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 md:col-span-2"
          />
          <button
            type="submit"
            className="rounded bg-sky-600 px-3 py-2 font-semibold text-white hover:bg-sky-500"
          >
            Carregar painel
          </button>
        </form>

        {erro ? (
          <p className="rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-300">
            {erro}
          </p>
        ) : null}

        {frame === null ? (
          <p className="text-sm text-slate-500">
            Cole o token da persona para carregar o painel.
          </p>
        ) : (
          <>
            <section className="flex flex-wrap items-baseline gap-6">
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-400">
                  Persona
                </p>
                <p className="font-mono text-lg text-sky-300">{frame.persona}</p>
              </div>
            </section>

            {podeAgir ? (
              <section className="flex flex-col gap-3 rounded border border-slate-700 bg-slate-800 p-4">
                <h2 className="text-xs uppercase tracking-widest text-slate-400">
                  Ações de continuidade
                </h2>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  {ACOES_DE_CONTINUIDADE.map((acao) => (
                    <button
                      key={acao.id}
                      type="button"
                      onClick={() => age(acao.id)}
                      className="rounded bg-slate-700 px-3 py-2 text-left text-sm font-semibold text-slate-100 hover:bg-slate-600"
                    >
                      {acao.rotulo}
                    </button>
                  ))}
                </div>
                {acaoErro ? (
                  <p className="rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-300">
                    {acaoErro}
                  </p>
                ) : null}
                {ultimaAcao !== null ? (
                  <p className="text-xs text-slate-400">
                    Ação registrada — o custo aparece na fatia abaixo (evento{" "}
                    <span className="font-mono text-sky-300">
                      {ultimaAcao.event_id}
                    </span>
                    ).
                  </p>
                ) : null}
              </section>
            ) : null}

            <section>
              <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-400">
                Camada reportada
              </h2>
              {frame.reported[0] === undefined ? (
                <p className="text-sm text-slate-500">
                  Nenhum evento na camada reportada desta persona.
                </p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {frame.reported.map((evento) => (
                    <Evento
                      key={evento.event_id}
                      evento={evento}
                      destacado={
                        ultimaAcao !== null && evento.event_id === ultimaAcao.event_id
                      }
                    />
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Painel />
  </StrictMode>,
);
