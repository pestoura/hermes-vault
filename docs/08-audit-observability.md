# 08 — Auditoria, observabilidade e deteção

## Objetivo

Garantir que o Vault e a sua integração com Hermes produzem telemetria suficiente para operação, deteção de abuso, investigação e assurance, sem expor segredos.

## Audit devices

Antes de migrar segredos relevantes, deve existir pelo menos um audit device funcional. Em produção, avaliar redundância de audit devices para evitar perda de evidência.

Eventos de interesse:

- autenticação e falhas de autenticação;
- criação e uso de tokens;
- acesso a secrets paths;
- emissão/renovação/revogação de leases;
- operações PKI;
- operações Transit;
- alterações de policies;
- alterações de auth methods;
- mount/unmount/tune de secrets engines;
- operações administrativas e recovery relevantes.

## Redaction

Os logs devem ser tratados como dados sensíveis de segurança.

Não enviar para Grafana/Loki em claro:

- tokens;
- passwords;
- SecretIDs;
- private keys;
- recovery/unseal keys;
- conteúdos de secrets;
- wrapped payloads utilizáveis.

## Métricas mínimas

### Saúde

```text
vault_up
vault_initialized
vault_sealed
vault_active
vault_standby
vault_storage_health
```

### Autenticação

```text
auth_success_total
auth_failure_total
token_creation_total
token_revocation_total
```

### Leases

```text
active_leases
lease_renewal_failures
expired_lease_cleanup
```

### PKI

```text
certificates_issued
certificate_renewal_failures
ca_expiry_seconds
cert_expiry_seconds
```

### Transit

```text
transit_sign_total
transit_verify_failures
transit_encrypt_total
transit_decrypt_failures
```

Os nomes concretos dependem das métricas expostas pela versão instalada e da transformação feita pela stack de observabilidade.

## Correlação Hermes ↔ Vault

Campos de correlação pretendidos:

```text
execution_id
plan_id
request_id
tool_call_id
principal
tool_identity
action
resource_scope
policy_decision
approval_id
lease_id (quando seguro)
vault_request_id (quando disponível)
```

## Dashboard Grafana proposta

Painéis:

1. **Vault Overview** — health, sealed state, requests, latency, storage.
2. **Authentication** — success/failure por auth method e identity.
3. **Secrets Access** — acessos agregados por mount/path lógico.
4. **Leases & Tokens** — ativos, expirados, renew/revoke.
5. **PKI** — emissão, expiração, renewal e falhas.
6. **Transit** — operações e falhas.
7. **Hermes Correlation** — runs/plan/tool calls relacionados com Vault.
8. **Admin/JIT** — elevações L3, approvals e duração.
9. **Assurance** — snapshots, restore tests, drift e policy checks.

## Deteções importantes

- aumento anómalo de falhas de autenticação;
- acesso de uma identity a path inesperado;
- tentativas de wildcard/admin fora de janela JIT;
- token com TTL superior ao baseline;
- lease que permanece ativo após execução concluída;
- emissão excessiva de certificados;
- alteração de policy sem approval/evidence;
- Vault sealed inesperadamente;
- audit device indisponível;
- snapshot atrasado ou restore test em falha;
- acesso a break-glass/recovery workflow.

## Alertas

A integração inicial pode focar-se em dashboards e consulta, mas o desenho deve ficar preparado para alertas futuros.

Prioridade de alertas quando ativados:

- Vault sealed/unavailable;
- audit device failure;
- CA perto de expirar;
- restore/backup failure;
- uso de admin JIT fora do fluxo autorizado;
- política ou auth method alterados sem baseline conhecido.

## Integração com jarvas-operations

Controlo diário futuro:

```text
RB-VAULT-001 — Vault Operational Assurance
```

Perguntas:

1. Vault está operacional, initialized e unsealed?
2. Audit está funcional?
3. Existem leases/tokens residuais anómalos?
4. PKI e certificados estão saudáveis?
5. Policies/auth methods divergem do baseline?
6. Snapshot recente existe e é válido?
7. Houve uso administrativo/JIT não esperado?
8. O Credential Broker consegue executar acceptance tests sem revelar secrets?
