// CONSOLE DE INVESTIGACAO — `02_DOMAIN_ACADEMUS.md` §7:124, `07` Fase 8 item 2.
//
// OS CINCO FILTROS, E QUEM DECIDE O QUE ELES ACHAM
// -------------------------------------------------
// Periodo, usuario, IP, janela e autorizacao. A tela MONTA a query com os
// filtros e dispara `GET /audit/grade-changes`; **a propria consulta filtrada e
// o que emite o marcador `auto` (`audit_query_performed`) no servidor**
// (`domains/academus/api/app.py`, `alteracoes_de_nota`). O cliente nao emite,
// nao marca nada como suspeito e nao conta: pinta as linhas e o `total` que
// vieram prontos — INV-7. Distinguir alteracao indevida de legitima e o trabalho
// analitico de quem investiga, e nao um juizo que a tela assa.
//
// NOMES DE PARAMETRO == NOMES DE CAMPO — a convencao herdada de
// `period_start`/`period_end`: `filter_user`, `filter_ip`, `filter_window`,
// `filter_authorization`. Filtro vazio nao vira parametro: mandar `filter_user=""`
// registraria na trilha um filtro que nao foi aplicado.
//
// O TOKEN VIVE NA MEMORIA DA ABA. `POST /auth/token` ainda e `planejada`
// (`academus/api_surface.yaml`), entao a porta de entrada e o token colado — a
// decisao esta no relatorio desta tarefa.

import { StrictMode, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";

import { BannerDeSimulacao } from "../src/banner";
import { type ResultadoDaConsulta } from "./tipos";
import "../src/estilo.css";

/** Pintura sobre o valor que veio, e nao um juizo: a janela ja e um fato da
 *  trilha. */
function rotuloDaJanela(dentro: boolean | null): string {
  if (dentro === null) {
    return "—";
  }
  return dentro ? "dentro da janela" : "fora da janela";
}

type Filtros = {
  token: string;
  periodStart: string;
  periodEnd: string;
  user: string;
  ip: string;
  window: string;
  authorization: string;
};

const VAZIO: Filtros = {
  token: "",
  periodStart: "",
  periodEnd: "",
  user: "",
  ip: "",
  window: "",
  authorization: "",
};

async function consultaTrilha(filtros: Filtros): Promise<ResultadoDaConsulta> {
  const parametros = new URLSearchParams();
  parametros.set("period_start", filtros.periodStart);
  parametros.set("period_end", filtros.periodEnd);
  if (filtros.user) {
    parametros.set("filter_user", filtros.user);
  }
  if (filtros.ip) {
    parametros.set("filter_ip", filtros.ip);
  }
  if (filtros.window) {
    parametros.set("filter_window", filtros.window);
  }
  if (filtros.authorization) {
    parametros.set("filter_authorization", filtros.authorization);
  }
  const resposta = await fetch(`/audit/grade-changes?${parametros.toString()}`, {
    headers: { Authorization: `Bearer ${filtros.token}` },
  });
  if (!resposta.ok) {
    throw new Error(`${resposta.status} — ${await resposta.text()}`);
  }
  return (await resposta.json()) as ResultadoDaConsulta;
}

function Console() {
  const [filtros, setFiltros] = useState<Filtros>(VAZIO);
  const [estado, setEstado] = useState<ResultadoDaConsulta | null>(null);
  const [erro, setErro] = useState("");

  const define = (campo: keyof Filtros) => (valor: string) =>
    setFiltros((atual) => ({ ...atual, [campo]: valor }));

  const consulta = async (evento: FormEvent) => {
    evento.preventDefault();
    setErro("");
    try {
      setEstado(await consultaTrilha(filtros));
    } catch (falha) {
      setEstado(null);
      setErro(falha instanceof Error ? falha.message : "falha na consulta");
    }
  };

  const campo = (
    rotulo: string,
    valor: string,
    ao: (valor: string) => void,
    tipo = "text",
  ) => (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wider text-slate-400">
        {rotulo}
      </span>
      <input
        type={tipo}
        value={valor}
        onChange={(evento) => ao(evento.target.value)}
        className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
      />
    </label>
  );

  return (
    <div className="min-h-screen bg-slate-900">
      {/* `05` §4: em TODA tela, sem excecao. */}
      <BannerDeSimulacao />
      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 text-slate-100">
        <header className="border-b border-slate-700 pb-4">
          <h1 className="text-sm uppercase tracking-widest text-slate-400">
            AURORA — console de investigação
          </h1>
        </header>

        <form
          onSubmit={consulta}
          className="flex flex-col gap-4 rounded border border-slate-700 bg-slate-800 p-4"
        >
          {campo("token do investigador", filtros.token, define("token"), "password")}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {campo("período — início", filtros.periodStart, define("periodStart"), "datetime-local")}
            {campo("período — fim", filtros.periodEnd, define("periodEnd"), "datetime-local")}
            {campo("usuário", filtros.user, define("user"))}
            {campo("IP", filtros.ip, define("ip"))}
            {campo("janela", filtros.window, define("window"))}
            {campo("autorização", filtros.authorization, define("authorization"))}
          </div>
          <button
            type="submit"
            className="rounded bg-sky-600 px-3 py-2 font-semibold text-white hover:bg-sky-500"
          >
            Consultar trilha
          </button>
        </form>

        {erro ? (
          <p className="rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-300">
            {erro}
          </p>
        ) : null}

        {estado === null ? (
          <p className="text-sm text-slate-500">
            Defina o período e dispare a consulta.
          </p>
        ) : (
          <section>
            <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-400">
              {/* `total` chega como NUMERO — o cliente nao conta as linhas. */}
              Resultado — {estado.total} alterações
            </h2>
            {estado.total === 0 ? (
              <p className="text-sm text-slate-500">
                Nenhuma alteração de nota no filtro aplicado.
              </p>
            ) : (
              <ul className="flex flex-col gap-1">
                {estado.linhas.map((linha) => (
                  <li
                    key={linha.sequence}
                    className="grid grid-cols-1 gap-2 rounded border border-slate-700 bg-slate-800 px-3 py-2 md:grid-cols-6"
                  >
                    <span className="font-mono text-xs text-slate-500">
                      #{linha.sequence}
                    </span>
                    <span className="font-mono text-xs text-sky-300">
                      {linha.actor_user_id}
                    </span>
                    <span className="text-xs text-slate-400 md:col-span-2">
                      {linha.occurred_at}
                    </span>
                    <span className="text-xs">{rotuloDaJanela(linha.within_window)}</span>
                    <span className="text-right text-xs text-slate-400">
                      {linha.authorization_id ?? "sem autorização"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Console />
  </StrictMode>,
);
