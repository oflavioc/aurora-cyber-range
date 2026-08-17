// UMA TELA POR BUILD, e o motivo e mecanico e nao de gosto.
//
// `vite-plugin-singlefile` inlina JS e CSS dentro do proprio HTML, e para isso
// liga `output.inlineDynamicImports` — que o rollup RECUSA com mais de uma
// entrada. Entao em vez de um build com tres entradas, sao tres builds com uma
// entrada cada, selecionados por `--mode`.
//
// POR QUE ARQUIVO UNICO, E O QUE ISSO RETIRA
// -------------------------------------------
// Servir `dist/assets/*` exigiria uma rota de arquivo estatico no `range-api`, e
// rota de arquivo estatico e superficie de path traversal — num processo cujas
// outras rotas operam o exercicio. Com o bundle inteiro dentro do HTML, essa
// rota nao existe: cada tela e UM arquivo, servido por UMA rota declarada em
// `range-core/api_surface.yaml`.
//
// E a forma da peca 2 outra vez: em vez de guardar o caminho perigoso, retirar
// o material com que ele se escreve. O custo e ~200 KB por HTML, que numa rede
// de sala nao e custo nenhum.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

/** As tres telas de `01_ARCHITECTURE.md` secao 2. O `mode` e o diretorio. */
const TELAS = ["wallboard-shell", "participant-view", "gm-console"];

export default defineConfig(({ mode }) => {
  if (!TELAS.includes(mode)) {
    // Falha ALTA, e nao build vazio: `vite build` sem `--mode` valido cairia no
    // modo "production" e tentaria usar `range-core/web/` como raiz, onde nao ha
    // `index.html`. O erro apareceria como "could not resolve entry", longe da
    // causa.
    throw new Error(
      `--mode precisa ser uma das telas: ${TELAS.join(", ")} (recebido: ${mode})`,
    );
  }

  return {
    root: mode,
    // Relativo: o HTML e servido por rota do `range-api` (`/sala`, `/plateia`,
    // `/console`) e nao por um servidor de arquivos com prefixo.
    base: "./",
    plugins: [react(), viteSingleFile()],
    build: {
      outDir: `../dist/${mode}`,
      emptyOutDir: true,
      // O `range-api` le `dist/<tela>/index.html`. Sem `assetsInlineLimit` alto
      // o plugin ainda inlina, mas deixar explicito documenta a intencao.
      assetsInlineLimit: 100000000,
      chunkSizeWarningLimit: 100000000,
    },
  };
});
