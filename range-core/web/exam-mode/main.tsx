// MODO "PROVA EM ANDAMENTO" — `02_DOMAIN_ACADEMUS.md` §7:123, `07` Fase 8 item 1.
//
// O QUE ESTA TELA FAZ, E O QUE ELA NAO DECIDE
// --------------------------------------------
// Ela pinta o frame TOTAL de `GET /exam/session-status`: cronometro (o minuto de
// exercicio que o servidor ECOA), autosave e monitoramento das sessoes, cada uma
// `alive` ou `dropped` no minuto corrente. A queda e derivada no servidor
// (`domains/academus/api/prova_andamento.py`) — INV-7: o cliente PINTA, nunca
// recalcula. Nao ha contagem, nao ha corte e nao ha relogio de parede aqui.
//
// O MINUTO E UM INSUMO, E POR ISSO ELE E CAMPO DO FORMULARIO
// ----------------------------------------------------------
// A rota exige `exercise_minute` sem default — o minuto do relogio de exercicio
// e um insumo declarado, nao um relogio de parede (R7 §6). Quem opera informa o
// minuto e consulta; um `setInterval` que incrementasse o minuto no cliente seria
// derivar o tempo, e mostraria um frame de um instante que o exercicio nao pediu.
//
// O TOKEN VIVE NA MEMORIA DA ABA — como no `gm-console`: recarregar pede a
// credencial de novo. `POST /auth/token` ainda e `planejada`
// (`academus/api_surface.yaml`), entao a porta de entrada e o token colado; a
// decisao esta no relatorio desta tarefa.

import { StrictMode, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";

import { BannerDeSimulacao } from "../src/banner";
import { type EstadoDaSessao, type FrameDaProva } from "./tipos";
import "../src/estilo.css";

/** Pintura sobre o vocabulario fechado, e nao um segundo criterio: a queda ja
 *  veio decidida do servidor. Mesmo desenho de `corDa` em `src/payload.ts`. */
const COR_DO_ESTADO: Record<EstadoDaSessao, string> = {
  alive: "bg-emerald-500",
  dropped: "bg-rose-500",
};

/** O rotulo de autosave por estado — tambem pintura do vocabulario fechado. */
const AUTOSAVE_DO_ESTADO: Record<EstadoDaSessao, string> = {
  alive: "autosave ativo",
  dropped: "sem autosave — sessão caiu",
};

const ESTADO_DESCONHECIDO = "bg-slate-700";

function corDoEstado(estado: string): string {
  return COR_DO_ESTADO[estado as EstadoDaSessao] ?? ESTADO_DESCONHECIDO;
}

function autosaveDoEstado(estado: string): string {
  return AUTOSAVE_DO_ESTADO[estado as EstadoDaSessao] ?? "estado desconhecido";
}

type Consulta = {
  token: string;
  classId: string;
  minuto: string;
};

async function leFrame(consulta: Consulta): Promise<FrameDaProva> {
  const parametros = new URLSearchParams({
    class_id: consulta.classId,
    exercise_minute: consulta.minuto,
  });
  const resposta = await fetch(`/exam/session-status?${parametros.toString()}`, {
    headers: { Authorization: `Bearer ${consulta.token}` },
  });
  if (!resposta.ok) {
    throw new Error(`${resposta.status} — ${await resposta.text()}`);
  }
  return (await resposta.json()) as FrameDaProva;
}

function Monitor() {
  const [token, setToken] = useState("");
  const [classId, setClassId] = useState("");
  const [minuto, setMinuto] = useState("0");
  const [estado, setEstado] = useState<FrameDaProva | null>(null);
  const [erro, setErro] = useState("");

  const consulta = async (evento: FormEvent) => {
    evento.preventDefault();
    setErro("");
    try {
      setEstado(await leFrame({ token, classId, minuto }));
    } catch (falha) {
      setEstado(null);
      setErro(falha instanceof Error ? falha.message : "falha na consulta");
    }
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* `05` §4: em TODA tela, sem excecao. Fica acima de tudo. */}
      <BannerDeSimulacao />
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6 text-slate-100">
        <header className="border-b border-slate-700 pb-4">
          <h1 className="text-sm uppercase tracking-widest text-slate-400">
            AURORA — prova em andamento
          </h1>
        </header>

        <form
          onSubmit={consulta}
          className="grid grid-cols-1 gap-3 rounded border border-slate-700 bg-slate-800 p-4 md:grid-cols-4"
        >
          <input
            type="password"
            value={token}
            onChange={(evento) => setToken(evento.target.value)}
            placeholder="token do facilitador"
            className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 md:col-span-2"
          />
          <input
            value={classId}
            onChange={(evento) => setClassId(evento.target.value)}
            placeholder="turma (class_id)"
            className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
          />
          <input
            type="number"
            min={0}
            value={minuto}
            onChange={(evento) => setMinuto(evento.target.value)}
            placeholder="minuto de exercício"
            className="rounded border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
          />
          <button
            type="submit"
            className="rounded bg-sky-600 px-3 py-2 font-semibold text-white hover:bg-sky-500 md:col-span-4"
          >
            Consultar sessões
          </button>
        </form>

        {erro ? (
          <p className="rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-300">
            {erro}
          </p>
        ) : null}

        {estado === null ? (
          <p className="text-sm text-slate-500">
            Informe a turma e o minuto de exercício para ver as sessões.
          </p>
        ) : (
          <>
            <section className="flex flex-wrap items-baseline gap-6">
              {/* O CRONOMETRO E O MINUTO QUE O SERVIDOR ECOOU — nao um relogio
                  do cliente. */}
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-400">
                  Cronômetro (minuto de exercício)
                </p>
                <p className="text-4xl font-bold tabular-nums">
                  {estado.exercise_minute}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-400">
                  Turma
                </p>
                <p className="font-mono text-lg text-sky-300">{estado.class_id}</p>
              </div>
            </section>

            <section>
              <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-400">
                Monitoramento de sessões
              </h2>
              <ul className="flex flex-col gap-1">
                {Object.entries(estado.sessions).map(([sessao, situacao]) => (
                  <li
                    key={sessao}
                    className="flex items-center gap-3 rounded border border-slate-700 bg-slate-800 px-3 py-2"
                  >
                    <span
                      className={`h-3 w-3 shrink-0 rounded-full ${corDoEstado(situacao)}`}
                    />
                    <span className="flex-1 font-mono text-sm">{sessao}</span>
                    <span className="text-xs uppercase tracking-wider text-slate-400">
                      {situacao}
                    </span>
                    <span className="w-56 text-right text-xs text-slate-500">
                      {autosaveDoEstado(situacao)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("raiz") as HTMLElement).render(
  <StrictMode>
    <Monitor />
  </StrictMode>,
);
