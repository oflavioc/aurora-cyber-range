# R7 — Determinismo por construção

Severidade: **bloqueante** (CI + `.gitattributes`).

O aurora já pratica boa parte desta regra — imagens e actions pinadas por
digest/SHA, `constraints.txt` fixando o fecho transitivo, `codegen.py --check`
que compara sem escrever, `.gitattributes` forçando LF em `*.sh` e
`user-scope/hooks/**` (com a lição documentada no próprio arquivo). Esta
página consolida o princípio e nomeia o que ainda é decisão pendente:

1. **LF em texto** — hoje coberto para `*.sh` e `user-scope/hooks/**`.
   **Pendente de decisão do operador**: estender para `* text=auto eol=lf`
   (política global do kit) exige commit de renormalização da árvore inteira —
   ver `docs/ADOCAO_ESTRUTURA_AGENTICA.md`. Até lá, hash de identidade se mede
   SEMPRE sobre blobs de HEAD (R2 §2, `gen_pins.py`), que é imune a CRLF de
   checkout.
2. **Geradores escrevem com `newline="\n"` e UTF-8 explícitos** — mesmo byte
   em qualquer SO.
3. **Verificação nunca escreve na árvore**: `codegen.py --check` compara em
   memória; os verificadores de `tools/` e `scripts/` são estáticos; todo
   stage novo prova `git status` inalterado ao final.
4. **Dependência de ambiente é declarada, nunca implícita** — o `env-doctor`
   (stage 0) valida a toolchain de `toolchain.json` ANTES das suítes; ausência
   vira WARN nomeado ou FAIL, jamais SKIP silencioso. O aurora já nomeia os
   pulos ("sem Postgres, 143 dos 835 pulam") — manter assim, nunca regredir.
5. **A plataforma canônica é o CI Linux** (`.github/workflows/invariants.yml`)
   — prova contínua em cada PR.
6. **Aleatoriedade e relógio não entram em artefato verificado** — o
   `RANDOM_SEED` é insumo declarado (mora no `.env`), nunca implícito; saída
   de gerador é função pura de fontes + seed.
