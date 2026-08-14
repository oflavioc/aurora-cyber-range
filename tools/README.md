# Verificadores de invariante

Os **seis** verificadores desta pasta são o gate real da Fase 0. O CI os executa em todo push e PR, e eles saem `rc=0` em árvore limpa.

| Script | Invariante | Técnica |
|---|---|---|
| `check_core_boundary.py` | `range-core/` não importa de `domains/` | AST: `Import`, `ImportFrom` (inclusive relativo resolvido), `importlib.import_module` e `__import__` com literal |
| `check_contract_literals.py` | nenhum literal de flag ou `event_type` fora dos geradores | leitura dos contratos + AST sobre `ast.Constant`, em Python e TypeScript |
| `check_event_envelope.py` | nenhum evento emitido carrega `objective_ids` | AST no caminho de emissão, com isenção de projeção ancorada na raiz |
| `check_security_constraints.py` | restrições funcionais de `05_SECURITY_REQUIREMENTS.md` §1 | AST sobre `ast.Call` — detecta por chamada, não por texto, para não marcar `eval(` dentro de string |
| `check_synthetic_data.py` | IPs, domínios e identificadores em faixas sintéticas | parse estruturado (json/jsonl/csv/YAML) + `ipaddress`; CPF verificado por dígito |
| `codegen.py --check` | constantes Python/TypeScript sincronizadas com os contratos | geração em memória e comparação com o disco; **nunca escreve** neste modo |

`_common.py` concentra o parser YAML de subconjunto estrito, a varredura determinista, a leitura de contrato e o relatório.

## Contrato de execução

Todos seguem `docs/process/PHASE_0_CHECKLIST.md` §Interfaces obrigatórias: `rc=0` em árvore válida, `rc` diferente de zero em violação, impressão de caminho e motivo, **apenas stdlib**, nenhuma escrita em disco, determinismo.

`sys.dont_write_bytecode = True` nos seis pontos de entrada — sem isso o import de `_common` criava `tools/__pycache__`, que viola o requisito de não modificar arquivos em modo de verificação.

## A prova que importa

```bash
python scripts/phase0_negative_tests.py
```

> Um verificador que nunca falhou contra uma violação plantada não é um verificador; é um script que sai com zero.

O harness planta violações **fora** dos verificadores e exige que cada um falhe com `rc=1` **e** cite o arquivo plantado — `rc=2`, que é crash de ferramenta, é rejeitado explicitamente. Ele roda no CI, dentro do job `arquitetura`, para que enfraquecer um verificador não passe despercebido.

*(Este arquivo dizia que os seis não existiam e eram a tarefa a fazer. Era a pendência P21, aberta na terceira auditoria e reconfirmada até a décima nona — documentação que sobreviveu à entrega e a contradizia.)*
