# R11 — Entrada de evidência

Severidade: **bloqueante** (hook `guard-data`).

O aurora já tem a metade mais difícil desta regra decidida e mecanizada: o
gabarito (`ground_truth.yaml`, `GM_NOTES.md`) fica fora do Git
(`check_gabarito_fora_do_git.py`), a evidência de cenário
(`scenarios/**/evidence/`) é projeção determinista reconstruível por comando, e
`.env`/`secrets/` têm deny rules. Esta regra soma o restante:

1. **Toda geração de evidência/artefato de auditoria escreve em diretório
   ignorado** (`.aurora-pack/`, tmp) — nunca em diretório rastreado como
   efeito colateral de rodar uma ferramenta.
2. **A entrada de evidência binária no repositório é um passo explícito de
   promoção** — o repositório versiona manifesto de hashes, não bytes.
   (O aurora hoje quase não tem binário versionado; a regra existe para
   continuar assim.)
3. **`guard-data` bloqueia no commit**: arquivo casando padrão sensível do
   `boundary.json → dados` (ground_truth/GM_NOTES/scenarios como defesa em
   profundidade além do verificador de CI), **PDF novo**, padrão de segredo,
   **binário novo >200 KB** — inclusive dentro de `.claude/**`.
4. **Dado real não entra**: CPF que valida, endereço/telefone/e-mail
   existente, IOC operacional — já é norma de `05_SECURITY_REQUIREMENTS.md`
   §3/§5.2, com verificador; nunca em arquivo versionado, memória de agente,
   log ou mensagem.
5. Se um segredo aparecer em texto no chat: avisar que ficou no transcript e
   sugerir rotação.
