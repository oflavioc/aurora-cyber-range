# 05 — REQUISITOS DE SEGURANÇA

Este documento não admite exceção, reinterpretação ou flexibilização em nenhuma fase, sob nenhuma justificativa técnica.

---

## 1. Código proibido

**NÃO implementar, em nenhuma hipótese:**

- exploits ou provas de conceito ofensivas
- malware ou ransomware funcional
- criptografia real de arquivos
- movimentação lateral
- payloads ofensivos
- persistência maliciosa ou backdoors
- vulnerabilidades exploráveis intencionais
- execução de shell a partir de entrada de usuário
- ferramenta de varredura, enumeração ou força bruta contra qualquer alvo

Todos os efeitos de "ataque" são simulados **exclusivamente por estado da aplicação**.

✅ Permitido:
```python
state.set("academus.enrollment_offline", True)
state.set("academus.portal_defaced", True)
```

❌ Proibido:
```python
encrypt_files()
shell_exec(...)
```

## 2. Evidências sintéticas

O evidence-simulator (`08_EVIDENCE_SIMULATOR.md`) gera **artefatos de log fictícios**, nunca amostras reais.

Proibido: hash de malware real, IOC de campanha real, IP roteável de terceiro, domínio registrado real, anexo executável de qualquer tipo, macro, script ou binário.

O `.eml` de phishing contém texto e um link para domínio da faixa reservada de documentação. Nenhum anexo. Nenhuma URL clicável para host existente.

## 3. Dados

Todos sintéticos, gerados com Faker pt_BR.

- CPFs devem **falhar** validação de dígito verificador
- Nenhum endereço, telefone ou e-mail real ou existente
- Domínios apenas de faixa reservada a documentação
- IPs apenas de faixas de documentação (RFC 5737 / RFC 3849) ou privadas

Nunca armazenar: fotos, biometria, geolocalização, documentos reais, endereços residenciais.

Registros simulando menores de idade:
```json
{ "is_synthetic": true, "age_range": "16-17" }
```

## 4. Banner obrigatório

Em toda tela e no rodapé de todo artefato gerado — PDF, histórico, diploma, relatório, exportação, arquivo de evidência:

```
AMBIENTE SIMULADO — DADOS FICTÍCIOS
```

Nos arquivos de evidência, como comentário na primeira linha, no formato do próprio arquivo.

## 5. Identificação de fornecedores

Vendor/product em CEF e em qualquer log identifica produto fictício (`UniAurora|ACADEMUS`). Nunca nome de fornecedor real de mercado, em nenhum campo, nem em documentação de exemplo.

O mesmo vale para atores de ameaça: usar designação fictícia no material do exercício. Referência a grupo real, se houver, fica restrita ao material de briefing do facilitador e claramente marcada como contexto, não como simulação.

## 6. Deploy

- Bind em `127.0.0.1`
- Acesso via túnel (WireGuard/SSH) ou VIP autenticado no firewall de borda
- Nenhuma porta publicada diretamente no compose de produção
- `.env.example` versionado; `.env` no `.gitignore`
- Destino syslog configurável, apontando para ambiente laboratorial
- `GM_NOTES.md` e `ground_truth.yaml` excluídos do build servido aos participantes

## 7. Integridade da trilha de auditoria

Requisito de segurança, não de funcionalidade. Implementação obrigatória em `02_DOMAIN_ACADEMUS.md` §4: role `INSERT`-only, `REVOKE UPDATE/DELETE`, trigger de bloqueio, encadeamento de hash, endpoint de verificação.

## 8. Autenticação

Nenhum serviço exposto sem autenticação, exceto `wallboard` e `participant-view`, que são projeções de sala e devem estar em rede isolada do exercício.

Senhas de seed nunca são valores triviais reutilizáveis; são geradas a partir do `RANDOM_SEED` e impressas apenas no log de seed local.
