# 12 — Roadmap de implementação

## Filosofia

Executar por fases pequenas, com gates verificáveis. Avançar automaticamente quando as gates estiverem GREEN/PASS e parar perante blocker real ou decisão de risco.

## Phase 0 — Discovery & prerequisites

### Entregáveis

- inventário sanitizado de segredos e consumidores;
- inventário de serviços e identidades;
- decisão de versão/edição Vault;
- decisão de seal/unseal;
- decisão de storage;
- baseline de TLS;
- classificação de secrets estáticos/dinâmicos;
- desenho final de backup.

### Gate P0

```text
DISCOVERY_COMPLETE
NO_SECRET_IN_REPO
TARGET_ARCHITECTURE_APPROVED
RECOVERY_DESIGN_DEFINED
```

---

## Phase 1 — Vault baseline

### Entregáveis

- Vault instalado;
- TLS obrigatório;
- Integrated Storage;
- initialization controlada;
- recovery material armazenado fora do Hermes;
- audit device;
- snapshots;
- human admin normal criado;
- initial root revogado.

### Gate P1

```text
VAULT_HEALTH_PASS
VAULT_UNSEALED
AUDIT_PASS
SNAPSHOT_PASS
ROOT_REVOKED
```

---

## Phase 2 — Workload identity & policies

### Entregáveis

- auth method inicial;
- `hermes-runtime`;
- `hermes-controller`;
- identidade `jarvas-operations`;
- tool identity piloto;
- policy linting;
- positive/negative tests.

### Gate P2

```text
AUTH_PASS
LEAST_PRIVILEGE_PASS
NEGATIVE_TEST_PASS
NO_GLOBAL_WILDCARD
```

---

## Phase 3 — KV v2 pilot & migration framework

### Entregáveis

- estrutura de mounts/paths;
- primeiro secret não crítico migrado;
- versioning/rollback testado;
- rotation runbook;
- secret inventory atualizado;
- remoção do secret legado piloto.

### Gate P3

```text
KV_PILOT_PASS
ROTATION_PASS
LEGACY_SECRET_REMOVED
RESTART_PASS
```

---

## Phase 4 — Credential Broker MVP

### Entregáveis

- API interna do Broker;
- `capability.request/status/revoke`;
- redaction;
- correlation IDs;
- memory-only/wrapping delivery;
- integração com uma tool real;
- cancellation cleanup.

### Gate P4

```text
BROKER_ACCEPTANCE_PASS
NO_SECRET_TO_MODEL
LEASE_CLEANUP_PASS
CANCEL_CLEANUP_PASS
```

---

## Phase 5 — Hermes Bridge V2 integration

### Entregáveis

- fast path direct-tool execution;
- agent path compatível;
- batch execution multi-tool;
- policy/risk classification;
- evidence manifest;
- tool identities independentes.

### Gate P5

Teste obrigatório:

```text
1 request
  → GitHub read operation
  → Outlook/Planner safe operation or read
  → Grafana read
```

Critérios:

```text
BATCH_EXECUTION_PASS
SEPARATE_CAPABILITIES_PASS
NO_CROSS_TOOL_SECRET_ACCESS
SANITIZED_RESULT_PASS
```

---

## Phase 6 — Transit & signed evidence

### Entregáveis

- Transit keys separadas;
- execution signing;
- evidence signing;
- verify path;
- HMAC migration quando aplicável;
- key rotation test.

### Gate P6

```text
SIGN_VERIFY_PASS
EVIDENCE_TAMPER_TEST_PASS
TRANSIT_ROTATION_PASS
```

---

## Phase 7 — PKI & mTLS

### Entregáveis

- CA/intermediate design implementado;
- roles por workload;
- emissão e renovação automática;
- mTLS em pelo menos um caminho crítico;
- expiry monitoring;
- revocation test.

### Gate P7

```text
PKI_ISSUE_PASS
MTLS_PASS
AUTO_RENEW_PASS
REVOKE_PASS
```

---

## Phase 8 — JIT Vault administration

### Entregáveis

- classes de admin policies;
- integração approvals;
- TTL curto;
- plan hash binding;
- consume-once;
- revogação no fim;
- signed admin evidence.

### Gate P8

```text
JIT_ADMIN_PASS
EXPIRED_APPROVAL_DENY
PLAN_CHANGE_DENY
TOKEN_REVOKED_AFTER_USE
```

---

## Phase 9 — Dynamic secrets

### Entregáveis

- selecionar targets suportados;
- implementar um dynamic secrets pilot;
- lease lifecycle;
- cleanup/revocation;
- fallback/rollback.

### Gate P9

```text
DYNAMIC_SECRET_PASS
LEASE_EXPIRY_PASS
REVOCATION_PASS
```

---

## Phase 10 — Broad migration

Migrar integrações por risco e maturidade:

- Grafana;
- GitHub;
- Cloudflare;
- Home Assistant;
- Google;
- Microsoft Planner/Outlook;
- DBs;
- RITMO/dispatchers;
- outros MCPs.

### Gate P10

```text
LEGACY_SECRET_SURFACE_REDUCED
NO_UNMANAGED_HIGH_RISK_SECRET
ROTATION_RUNBOOKS_PASS
```

---

## Phase 11 — Assurance & recovery

**Recovery implementation checkpoint:** `ADR023_REPO_READY_LIVE_HITL_PENDING`. O isolated restore drill harness está repository-ready (`network=none`, zero published ports, exact image digest, synthetic acceptance + teardown), mas o live HITL restore ainda não executou e `RESTORE_DRILL_PASS` permanece pendente.

### Entregáveis

- `RB-VAULT-001` integrado no `jarvas-operations`;
- policy drift;
- X.509 expiry;
- lease cleanup;
- snapshot assurance;
- isolated restore drill harness repository-ready; live restore HITL pending;
- non-production failure/self-healing acceptance.

### Gate P11

```text
DAILY_ASSURANCE_PASS
DRIFT_PASS
RESTORE_DRILL_PASS
BREAK_GLASS_DRY_RUN_PASS
```

---

## Phase 12 — Production readiness

Checklist final:

- [ ] arquitetura implementada conforme baseline;
- [ ] root não persistente;
- [ ] recovery independente;
- [ ] restore drill efetuado;
- [ ] audit operacional;
- [ ] Grafana dashboard disponível;
- [ ] secrets críticos migrados;
- [ ] JIT admin validado;
- [ ] PKI/Transit conforme scope;
- [ ] direct-tool execution não expõe secrets;
- [ ] negative tests verdes;
- [ ] documentação operacional atualizada;
- [ ] versão/tag de produção criada.

Decisão final:

```text
HERMES_VAULT_PRODUCTION_READY
```

ou

```text
HERMES_VAULT_PRODUCTION_BLOCKED_<REASON>
```
