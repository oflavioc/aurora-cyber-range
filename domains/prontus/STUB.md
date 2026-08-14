# PRONTUS — adapter hospitalar (stub)

**Hospital Regional Aurora**, sistema **PRONTUS**.

Este adapter existe para **provar a fronteira arquitetural**, não para ser usado. `00_MASTER_SPEC.md` §1 e `01_ARCHITECTURE.md` §1: `academus` é implementado completo; `prontus` é stub mais interface.

## O que ele prova

**Que o core não conhece o domínio.** Se `range-core/` precisasse saber o que é uma matrícula, um segundo adapter com vocabulário diferente — admissão, prontuário, triagem — quebraria. `tools/check_core_boundary.py` verifica por AST, e a existência deste diretório é o que dá sentido à verificação.

**Que o namespace de flags resolve colisão real.** `01_ARCHITECTURE.md` §5.1 exige `<adapter>.*`. Aqui isso deixa de ser hipótese: `academus.enrollment_offline` e `prontus.admission_offline` são a mesma classe de efeito — serviço de entrada indisponível — em domínios diferentes. Sem prefixo, colidiriam.

**Que a taxonomia é reusável.** As duas flags declaradas usam as mesmas `category` e `domain_area` do contrato, sem campo novo. Se a taxonomia fosse específica de universidade, isso não fecharia.

## O que ele não é

Não há modelo, tela, seed, painel ou cenário. Implementar um segundo vertical significa escrever o domínio, não refazer o motor — e é exatamente essa afirmação que este stub existe para manter honesta.

Conteúdo atual: `flags.yaml` com duas flags, e este documento.
