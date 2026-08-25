# R9 — Modularização (pré-condição da equipe multi-agente)

Severidade: **bloqueante** para módulo NOVO; o aurora já tem a fronteira
central mecanizada (core ↛ domains) — esta regra estende o princípio ao nível
de módulo.

"Um módulo por delegação" só funciona com "um dono por símbolo". Para todo
módulo novo:

1. **Escopo próprio e sem efeito colateral de import** — módulo/pacote Python
   com API explícita; nada executa na importação.
2. **Um ponto de contato público por módulo.** No aurora o padrão já existe e
   é mais forte que registro em manifesto: superfície DECLARADA e conferida
   nas duas direções (`api_surface.yaml` × rotas; whitelist de imports do
   core). Módulo novo declara sua superfície no mesmo padrão.
3. **Contrato inter-módulo só pela API declarada.** Proibido: ler estado
   interno alheio como canal de decisão; parsear saída renderizada.
4. **Proibido monkey-patch de função alheia.** Extensão via ponto de registro
   explícito, aprovado pelo tech-lead no `plan.md`.
5. **Estado canônico nunca nasce em camada derivada.** No aurora isso é norma
   viva: o fold é a única autoridade de estado (`check_fold_authority.py`);
   projeção materializada nunca é fonte. Dado novo declara o owner do estado
   na spec.
6. **Namespace por prefixo**: flags e eventos de domínio carregam o prefixo do
   domínio (`academus.*`, `prontus.*`) — já é desenho; vale para todo domínio
   novo.
7. **Orçamento de tamanho: ~600 linhas** por módulo ou justificativa
   registrada no plan.md; uma responsabilidade por módulo.
8. **Helper único por semântica de invariante** — limiar ou distinção usada em
   dois lugares vive num helper do dono (o aurora já pratica: `NewType` +
   ponto único de montagem por insumo de métrica, §3.2).
9. **Superfícies inseguras proibidas** (equivalente Python do lint de origem):
   SQL por concatenação de string, `eval`/`exec` sobre entrada, subprocess sem
   lista de argumentos, caminho sem aspas em shell.
