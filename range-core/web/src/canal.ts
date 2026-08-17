// O CANAL, E O ESTADO QUE VEM INTEIRO
//
// Cada frame e o estado TOTAL (D3), entao aqui nao ha merge, nao ha reducer e
// nao ha acumulacao: o ultimo frame SUBSTITUI o anterior. E por isso que dar
// refresh no navegador recupera o estado corrente — o servidor manda tudo assim
// que a conexao abre (`_serve_canal`), e nao ha o que se perder.
//
// BINARIO, E NAO TEXTO: o canal entrega os MESMOS BYTES que o snapshot HTTP
// devolve. Converter no servidor seria uma segunda serializacao, que e a
// divergencia que a peca 2 existe para impedir.

import { useEffect, useState } from "react";

export type Ligacao<T> = {
  /** `null` ate o primeiro frame. Nao e "vazio": e "ainda nao chegou". */
  estado: T | null;
  ligado: boolean;
};

/** Reconecta sozinho: um exercicio dura horas, e uma tela que morre na primeira
 *  queda de rede exige alguem que a reabra — no meio da sala. */
const ESPERA_PARA_RELIGAR_MS = 1000;

export function useCanal<T>(caminho: string): Ligacao<T> {
  const [estado, setEstado] = useState<T | null>(null);
  const [ligado, setLigado] = useState(false);

  useEffect(() => {
    let vivo = true;
    let socket: WebSocket | null = null;
    let agendado: number | undefined;

    const liga = () => {
      const protocolo = location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocolo}//${location.host}${caminho}`);
      socket.binaryType = "arraybuffer";

      socket.onopen = () => {
        if (vivo) {
          setLigado(true);
        }
      };

      socket.onmessage = (evento: MessageEvent<ArrayBuffer>) => {
        if (!vivo) {
          return;
        }
        const texto = new TextDecoder("utf-8").decode(evento.data);
        setEstado(JSON.parse(texto) as T);
      };

      socket.onclose = () => {
        if (!vivo) {
          return;
        }
        setLigado(false);
        agendado = window.setTimeout(liga, ESPERA_PARA_RELIGAR_MS);
      };
    };

    liga();

    return () => {
      vivo = false;
      window.clearTimeout(agendado);
      if (socket) {
        socket.close();
      }
    };
  }, [caminho]);

  return { estado, ligado };
}
