// O GM-CONSOLE — `01_ARCHITECTURE.md` secao 6, com UM papel (D5: `facilitador`).
//
// A CASCA E PUBLICA, O DADO NAO E — ver a D19 no registro da fase
// ----------------------------------------------------------------
// `GET /console` serve este arquivo sem token, porque nenhum navegador pode
// enviar `Authorization` numa navegacao — e a mesma razao pela qual `POST
// /session` ja e publica desde a peca 4. O que a casca contem e HTML, CSS e
// JavaScript: nenhum inject, nenhum texto de plateia, nenhuma credencial. Todo
// byte de exercicio atras dela exige token, e `tests/test_telas.py` afirma as
// duas metades.
//
// O TOKEN VIVE NA MEMORIA DA ABA, e nao em `localStorage`: recarregar pede a
// credencial de novo, e isso e o comportamento desejado num console que dispara
// inject sem desfazer. Persistir o token trocaria um incomodo de facilitador por
// uma credencial de exercicio esquecida no navegador da sala.
//
// CONFIRMACAO ONDE A SUPERFICIE PEDE, E SO ONDE ELA PEDE
// -------------------------------------------------------
// `range-core/api_surface.yaml` marca `confirmacao: true` em START, FIRE e
// ROLLBACK — os tres que nao tem volta. PAUSAR e CONTINUAR sao `reversivel` e
// NAO confirmam: confirmar o que tem volta treina o operador a clicar "sim", e e
// assim que a confirmacao do que nao tem volta deixa de ser lida.

import { StrictMode, useCallback, useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";

import { useCanal } from "../src/canal";
import { corDa, type Wallboard } from "../src/payload";
import { type Inject, type ListaDeInjects, type Timeline } from "./tipos";
import "../src/estilo.css";

/** `contracts/events.schema.yaml`, `rollback_reason`, tem quatro valores. O
 *  console usa UM.
 *
 *  `technical_failure` exige `frozen_interval` no payload — dado que o console
 *  nao tem; `rehearsal` e `adjudication` pertencem a papeis que esta fase nao
 *  entrega (NON-GOAL: tres papeis de facilitacao). Oferecer os quatro daria um
 *  botao que responde erro, que e pior que um botao a menos. */
const MOTIVO_DO_ROLLBACK = "facilitation";

type Comando = {
  metodo: "POST";
  caminho: string;
  corpo?: unknown;
};

async function chama(comando: Comando, token: string): Promise<string | null> {
  const resposta = await fetch(comando.caminho, {
    method: comando.metodo,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: comando.corpo === undefined ? "{}" : JSON.stringify(comando.corpo),
  });
  if (resposta.ok) {
    return null;
  }
  return `${resposta.status} — ${await resposta.text()}`;
}

async function le<T>(caminho: string, token: string): Promise<T> {
  const resposta = await fetch(caminho, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return (await resposta.json()) as T;
}

function Entrada({ token }: { token: (valor: string) => void }) {
  const [credencial, setCredencial] = useState("");
  const [erro, setErro] = useState("");

  const entra = async (evento: FormEvent) => {
    evento.preventDefault();
    setErro("");
    const resposta = await fetch("/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credencial }),
    });
    if (!resposta.ok) {
      setErro("credencial inválida");
      return;
    }
    const corpo = (await resposta.json()) as { token: string };
    token(corpo.token);
  };

  return (
    <form
      onSubmit={entra}
      className="mx-auto mt-32 flex w-80 flex-col gap-3 rounded border border-slate-700 bg-slate-800 p-6"
    >
      <h1 className="text-sm uppercase tracking-widest text-slate-400">
        Console de facilitação
      </h1>
      <input
        type="password"
        autoFocus
        value={credencial}
        onChange={(evento) => setCredencial(evento.target.value)}
        placeholder="credencial do facilitador"
        className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
      />
      <button
        type="submit"
        className="rounded bg-sky-600 px-3 py-2 font-semibold text-white hover:bg-sky-500"
      >
        Entrar
      </button>
      {erro ? <p className="text-sm text-rose-400">{erro}</p> : null}
    </form>
  );
}

function Console({ token }: { token: string }) {
  const [injects, setInjects] = useState<ListaDeInjects>({ injects: [] });
  const [timeline, setTimeline] = useState<Timeline>({ entradas: [] });
  const [erro, setErro] = useState("");
  // O MESMO canal publico que o telao consome. O console nao ganha uma projecao
  // propria de estado: duas projecoes do mesmo fato divergem, e a que diverge em
  // silencio e sempre a que ninguem esta olhando.
  const { estado } = useCanal<Wallboard>("/ws/wallboard");

  const recarrega = useCallback(async () => {
    setInjects(await le<ListaDeInjects>("/injects", token));
    setTimeline(await le<Timeline>("/timeline", token));
  }, [token]);

  useEffect(() => {
    void recarrega();
  }, [recarrega]);

  const executa = async (comando: Comando, confirmacao?: string) => {
    if (confirmacao !== undefined && !window.confirm(confirmacao)) {
      return;
    }
    setErro((await chama(comando, token)) ?? "");
    await recarrega();
  };

  const dispara = (inject: Inject) =>
    executa(
      { metodo: "POST", caminho: `/injects/${inject.id}/fire` },
      `Disparar ${inject.id} — ${inject.titulo}?\n\nNão há desfazer: o evento fica no store, e o efeito só sai por ROLLBACK.`,
    );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 text-slate-100">
      <header className="flex items-center gap-6 border-b border-slate-700 pb-4">
        <h1 className="text-sm uppercase tracking-widest text-slate-400">
          AURORA — console
        </h1>
        <span className="ml-auto text-3xl font-bold">
          {estado === null ? "—" : estado.indice_de_saude}
        </span>
        <div className="flex gap-2">
          {estado === null
            ? null
            : estado.paineis.map((bloco) => (
                <span
                  key={bloco.grupo}
                  title={`${bloco.grupo}: ${bloco.ativos}/${bloco.total}`}
                  className={`h-3 w-3 rounded-full ${bloco.ativos ? corDa(bloco.categoria) : "bg-slate-700"}`}
                />
              ))}
        </div>
      </header>

      <section className="flex flex-wrap gap-2">
        <button
          onClick={() =>
            executa(
              { metodo: "POST", caminho: "/exercise/start" },
              "Iniciar o exercício? O T0 é gravado agora e não há desfazer.",
            )
          }
          className="rounded bg-emerald-700 px-3 py-2 font-semibold hover:bg-emerald-600"
        >
          INICIAR
        </button>
        <button
          onClick={() => executa({ metodo: "POST", caminho: "/exercise/pause" })}
          className="rounded bg-slate-700 px-3 py-2 font-semibold hover:bg-slate-600"
        >
          PAUSAR
        </button>
        <button
          onClick={() => executa({ metodo: "POST", caminho: "/exercise/resume" })}
          className="rounded bg-slate-700 px-3 py-2 font-semibold hover:bg-slate-600"
        >
          CONTINUAR
        </button>
      </section>

      {erro ? (
        <p className="rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-300">
          {erro}
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <section>
          <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-400">
            Injects
          </h2>
          <ul className="flex flex-col gap-1">
            {injects.injects.map((inject) => (
              <li
                key={inject.id}
                className="flex items-center gap-3 rounded border border-slate-700 bg-slate-800 px-3 py-2"
              >
                <span className="w-16 font-mono text-xs text-slate-400">
                  {inject.t_relative}
                </span>
                <span className="font-mono text-xs text-sky-300">{inject.id}</span>
                <span className="flex-1 text-sm">{inject.titulo}</span>
                {inject.disparado ? (
                  <span className="text-xs uppercase text-slate-500">disparado</span>
                ) : (
                  <button
                    onClick={() => dispara(inject)}
                    className="rounded bg-rose-700 px-2 py-1 text-xs font-semibold hover:bg-rose-600"
                  >
                    DISPARAR
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-400">
            Timeline
          </h2>
          <ul className="flex flex-col gap-1">
            {timeline.entradas.map((entrada) => (
              <li
                key={entrada.event_id}
                className="flex items-center gap-3 rounded border border-slate-700 bg-slate-800 px-3 py-2"
              >
                <span className="w-16 font-mono text-xs text-slate-400">
                  {entrada.exercise_time}
                </span>
                <span className="w-10 font-mono text-xs text-slate-500">
                  e{entrada.epoch}
                </span>
                <span className="flex-1 text-sm">
                  {entrada.rotulo}
                  {entrada.inject_id ? ` — ${entrada.inject_id}` : ""}
                  {entrada.rollback ? ` (${entrada.rollback.motivo})` : ""}
                </span>
                <button
                  onClick={() =>
                    executa(
                      {
                        metodo: "POST",
                        caminho: "/exercise/rollback",
                        corpo: {
                          to_event_id: entrada.event_id,
                          reason: MOTIVO_DO_ROLLBACK,
                        },
                      },
                      `ROLLBACK até ${entrada.exercise_time} (${entrada.rotulo})?\n\nO estado corrente de simulação é descartado e uma epoch nova começa. Nenhum evento é apagado.`,
                    )
                  }
                  className="rounded border border-amber-700 px-2 py-1 text-xs font-semibold text-amber-300 hover:bg-amber-900"
                >
                  ROLLBACK
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function Aplicacao() {
  const [token, setToken] = useState<string | null>(null);
  return token === null ? <Entrada token={setToken} /> : <Console token={token} />;
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Aplicacao />
  </StrictMode>,
);
