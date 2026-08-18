# GM_NOTES — Linha B, {{PACK}}

> **AMBIENTE SIMULADO — DADOS FICTÍCIOS**
>
> Documento de facilitação. **Não entra em build, bundle, API ou export servido a
> participantes** — `05_SECURITY_REQUIREMENTS.md` §6.

<!--
  ESTE ARQUIVO É UM TEMPLATE VERSIONADO. O artefato renderizado a partir dele
  NÃO é versionado: `scenarios/` está fora do Git, e o motivo está no
  `.gitignore`.

  A REGRA QUE MANTÉM ESTA METADE SEGURA: nenhum identificador concreto pode ser
  escrito aqui à mão. Nem `case_id`, nem conta, nem matrícula, nem número de
  processo. Tudo o que é concreto entra por `{{ }}`, e
  `scripts/check_gabarito_fora_do_git.py` reprova se um identificador com forma
  de gabarito aparecer neste arquivo.

  A prosa abaixo pode ser lida por qualquer um sem custo: ela reafirma o que
  `02_DOMAIN_ACADEMUS.md` §6.1 e §6.2 já publicam, e a spec é pública. O que
  não pode vazar é QUAIS CASOS — e isso só existe depois do `RANDOM_SEED`.
-->

Gerado de `{{SEED_ORIGEM}}` em uma execução determinista. Mesma origem, mesmo
conteúdo. **Este arquivo não é fonte**: a fonte é `ground_truth.yaml`, e nenhum
fato aqui pode faltar lá.

---

## O que a Linha B é, e o que ela não é

Encontrar quarenta eventos estranhos é trivial depois que alguém abre a trilha de
auditoria. **O exercício não é esse.** O exercício é demonstrar, com confiança
declarada, quais eventos são indevidos — e o critério de avaliação é a relação
entre a confiança declarada e a força real da evidência, não a contagem de
acertos.

O erro mais interessante deste cenário é a **superconfiança**. Declarar alta
confiança sobre os casos legítimos de aparência suspeita leva à anulação de notas
de formandos inocentes — custo institucional maior que deixar um caso duvidoso em
aberto. O AAR trata superconfiança e falso negativo separadamente e não os
compensa entre si.

## Os seis conjuntos

| Conjunto | Volume | Por que ele existe |
|---|---|---|
| Indevidos comprovados | {{N_INDEVIDOS}} | O que de fato aconteceu. Conta docente única, IP de laboratório compartilhado, fora da janela de retificação, **sem** autorização, sempre elevando nota, sempre no mesmo grupo de alunos, sempre na madrugada. `defensibility` 1.0 |
| Ambíguos legítimos | {{N_AMBIGUOS}} | Fora da janela, **com** autorização — mas a justificativa é genérica e o aprovador é a mesma conta que assina os indevidos. Genuinamente inconclusivos. `defensibility` 0.5 |
| Legítimos de aparência suspeita | {{N_SUSPEITOS}} | Fora da janela, com autorização sólida, IP de laboratório, horário noturno. **Parecem fraude; não são.** É onde a superconfiança cobra o preço. `defensibility` 0.0 |
| Ruído de manutenção | {{N_RUIDO}} | Correção em lote por migração de sistema, sob conta de serviço. Volume que obriga a equipe a filtrar antes de concluir |
| Credenciais compartilhadas | {{N_DELEGADAS}} | Monitor usando a conta do professor, **com registro formal de delegação**. Sem o registro, seriam indistinguíveis dos indevidos |
| Legítimos normais | {{N_NORMAIS}} | Dentro da janela. O mundo normal, e o que dá escala ao problema |

**A razão de os de aparência suspeita parecerem suspeitos** é que eles têm quatro
das seis características dos indevidos — fora da janela, IP de laboratório,
horário noturno, elevação de nota. O que falta neles é o que decide: a
autorização é sólida e o aprovador não é a conta comprometida.

## A query de referência

Ela separa **indevidos de ambíguos**, que é a distinção que o exercício mede. Os
dois conjuntos estão fora da janela e os dois elevam nota; o que os separa é a
autorização e de quem ela veio.

```sql
{{QUERY_INDEVIDOS}}
```

Com a conta comprometida em `:conta_alvo`, ela devolve **{{N_INDEVIDOS}}** linhas
e nenhuma dos ambíguos. A dos ambíguos é a mesma pergunta pelo outro lado:

```sql
{{QUERY_AMBIGUOS}}
```

## Os casos, por conjunto

{{TABELA_DE_CASOS}}

## Como conduzir

- **Não entregue a query.** Ela é o gabarito; entregá-la é dar a resposta.
- A equipe declara o **escopo revisado** — período, população, critério — antes
  de submeter. É o que separa erro de julgamento de lacuna de cobertura.
- Um caso dentro do escopo e não avaliado conta como confiança zero. Um indevido
  comprovado **fora** do escopo revisado é lacuna de cobertura, e não falso
  negativo.
- Se alguém questionar se a própria trilha foi adulterada, a resposta é
  `GET /audit/verify-chain`. A cadeia de hash responde, e o exercício ensina que
  trilha de auditoria não é log.
