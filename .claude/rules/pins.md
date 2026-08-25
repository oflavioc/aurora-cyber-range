# R8 — Registry único de pins

Severidade: **bloqueante** (stage `baseline` + classe `registry` do boundary).

Identidade de artefato vive em UM lugar: `.claude/verify/pins.json`, gerado por
`gen_pins.py` a partir dos **blobs de HEAD** (à prova de CRLF/plataforma).

> Lição de origem: hashes duplicados em 6+ lugares, com repins manuais que
> falharam duas vezes — e um manifesto legado nunca regenerado, sempre vermelho,
> logo nunca rodado (gate que falha pelo motivo errado vira gate morto).

## Regras

1. **Alterar arquivo pinado exige regenerar o registry no MESMO PR**, com o
   motivo na mensagem de commit. O stage `baseline` falha em divergência e em
   arquivo rastreado sem pin — o esquecimento é impossível de silenciar.
2. **Repin em gate legado** (pins inline que ainda existam em suítes congeladas):
   mudança acompanhada de comentário-trilha — motivo, data, "Identidade
   anterior: <hash>".
3. **Pins declarativos** (`declared`): identidades de governança (ex.: a régua
   da superfície congelada da R1). Mudá-los é ato de governança, nunca efeito
   colateral.
4. Manifestos de identidade aposentados são **legado congelado** (classe
   `legacy`): não são fonte, não são editados.
5. O registry **não pina a si mesmo**; suas exclusões estão declaradas no
   próprio arquivo, em `_meta.exclusoes`. Estado de processo
   (`.claude/project-memory/**`) não se pina: muda por desenho, é validado pelo
   stage `state`, e a trilha é o git.
