# 08 — EVIDENCE SIMULATOR

O que separa "TTX com dashboards excelentes" de cyber range defensivo investigativo.

---

## 1. Princípio: uma realidade, múltiplas projeções

**Errado:**

```
seed
 ├── gera vpn.log
 ├── gera identity_audit.jsonl
 ├── gera CEF
 └── gera trilha de auditoria
```

Mesmo seed é **necessário mas não suficiente**. Geradores independentes divergem semanticamente à primeira mudança de código ou de ordem de geração — e a divergência só aparece quando o time azul encontra a contradição, no meio do exercício.

**Certo:**

```
                GROUND TRUTH FACT
                       │
       ┌───────┬───────┼───────┬────────┐
       ↓       ↓       ↓       ↓        ↓
   vpn.log  identity  CEF   audit   precursor
             _audit         _trail   _events
```

Cada fonte é **projeção determinística de um fato canônico**. Contradição entre fontes torna-se estruturalmente impossível.

## 2. Fato canônico

`scenarios/<pack>/ground_truth.yaml`, invisível aos participantes:

```yaml
facts:
  - fact_id: GT-A-014
    fact_class: initial_access
    actor: svc_academus
    action: vpn_login
    source_ip: 198.51.100.42
    dest: vpn-gw-01
    exercise_time: "T-17d 02:14"
    credential_state: compromised
    mfa: absent
    projections: [vpn, identity_audit, cef]
    discoverability:
      difficulty: medium
      requires: "correlacionar horário fora de expediente com ausência de MFA"
```

Regras:

- Projeção **não inventa entidade**. Consome o elenco fixado pelo ground truth
- Fato sem `projections` é invisível ao time azul — deliberado, e usado para ensinar limite de detecção
- `precursor_events.jsonl` deixa de ser artefato autoral: é **gerado** como projeção
- A telemetria CEF é projeção, não emissão independente. Isso unifica evidence-simulator e telemetry-forwarder sob um contrato só

## 3. Fontes — v1

| Arquivo | Formato | O que carrega |
|---|---|---|
| `email.eml` | RFC 5322, sem anexo | Phishing de recadastramento — origem da Linha A |
| `vpn.log` | Texto syslog-like | Autenticação sem MFA, horário anômalo, geolocalização inconsistente |
| `identity_audit.jsonl` | JSONL | Conta de serviço, criação de sessão, escalada |
| `database_audit.jsonl` | JSONL | Leitura em massa (Linha A) e alterações de nota com IP e sessão (Linha B) |

## 4. Fontes — pós-MVP

`firewall.log`, `radius.log`, `web_application.log`, `saas_audit.jsonl`, `cloud_audit.jsonl`, `edr_timeline.json`.

**Cortadas da v1 deliberadamente:** DNS, proxy e DHCP. Para este ground truth provam pouco — a entrada é credencial phishada sobre VPN, não C2 por DNS. Entram quando houver pacote cujo ground truth as exija.

## 5. Modos de entrega

**Pré-posicionado** — disponível desde o start, em share simulado.

**Liberado por inject** — simula tempo real de obtenção de log de terceiro:

```yaml
evidence_release:
  - source: vpn
    window: "T-9d → T-8d"
```

**Sob requisição** — participante solicita pelo dashboard de TI; atraso configurável simula dependência de fornecedor. É o modo mais realista e o que melhor exercita OBJ-02.

## 6. Instrumentação

Abrir ou consultar fonte emite `evidence_source_opened` (`09_EVENT_MODEL.md`). O AAR reporta **quais fontes foram efetivamente consultadas e quais foram ignoradas** — frequentemente o achado mais útil do debriefing.

## 7. Saída

`scenarios/<domain>/<pack>/evidence/` com `MANIFEST.json`: cada arquivo, janela temporal, modo de entrega, hash, e os `fact_id` que projeta. O manifesto permite ao facilitador saber o que existe e ao teste verificar cobertura de projeção.

## 8. Restrições

Ver `05_SECURITY_REQUIREMENTS.md` §2. Sem anexo, sem binário, sem IOC real, sem domínio roteável, sem hash de malware real. IPs apenas de faixa de documentação ou privada.
