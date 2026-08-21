# Hermes Vault — documentation index

**Repository status:** `VAULT_CORE_OPERATIONAL=VERIFIED`. The shared Vault core is DEPLOYED and live-accepted; consumer production enablement remains separately gated.

## Start here

| Order | Document | Purpose |
|---:|---|---|
| 1 | [`16-current-runtime-status.md`](16-current-runtime-status.md) | Canonical current runtime truth and open gates |
| 2 | [`../README.md`](../README.md) | Product/runtime overview and diagrams |
| 3 | [`01-reference-architecture.md`](01-reference-architecture.md) | Architecture and trust boundaries |
| 4 | [`03-identity-auth-policy.md`](03-identity-auth-policy.md) | Identity, auth and policy model |
| 5 | [`09-bootstrap-recovery.md`](09-bootstrap-recovery.md) | Shamir, bootstrap and recovery |
| 6 | [`runbooks/scheduled-snapshot.md`](runbooks/scheduled-snapshot.md) | Daily encrypted Raft snapshots |
| 7 | [`runbooks/restore-drill.md`](runbooks/restore-drill.md) | Isolated restore drill |
| 8 | [`runbooks/jit-admin-bootstrap.md`](runbooks/jit-admin-bootstrap.md) | Certificate JIT administration |
| 9 | [`13-security-decisions.md`](13-security-decisions.md) | Accepted security decisions / ADRs |
| 10 | [`../IMPLEMENTATION-CHECKLIST.md`](../IMPLEMENTATION-CHECKLIST.md) | Completed and remaining capabilities |
| 11 | [`../RESUME.md`](../RESUME.md) | Safe continuation checkpoint |

## Current state vocabulary

- **DESIGNED** — accepted architecture/contract exists.
- **IMPLEMENTED** — repository-side runtime/configuration exists.
- **DEPLOYED** — live runtime is installed/running.
- **VERIFIED** — executable acceptance evidence passed.
- **PRODUCTION_ENABLED** — capability is actively enabled for an intended consumer.

The core service is DEPLOYED + VERIFIED. HSL first-consumer enablement is still `NOT_RUN`, so it is not yet `PRODUCTION_ENABLED` for that consumer.

## Architecture and design set

| Document | Scope |
|---|---|
| `00-context-goals.md` | scope, goals and non-goals |
| `01-reference-architecture.md` | reference architecture |
| `02-vault-capabilities.md` | capability catalogue |
| `03-identity-auth-policy.md` | identities, auth methods and least privilege |
| `04-hermes-integration.md` | Hermes/Credential Broker integration design |
| `05-jit-privilege.md` | JIT privilege model |
| `06-pki-mtls.md` | future PKI/mTLS design |
| `07-transit-evidence.md` | Transit/signing/HMAC model |
| `08-audit-observability.md` | audit and observability |
| `10-operations-runbooks.md` | operating procedures catalogue |
| `11-migration-plan.md` | progressive consumer/secret migration |
| `12-implementation-roadmap.md` | phased delivery and gates |
| `14-references.md` | authoritative references |
| `15-delivery-operating-model.md` | delivery operating model |
| `15-threat-model.md` | threat model |

## Evidence hierarchy

When sources disagree, use this order:

1. current read-only/live observation;
2. dated acceptance evidence under `docs/evidence/`;
3. `16-current-runtime-status.md`;
4. accepted security decisions and specs;
5. roadmap/checklist;
6. historical assumptions or chat context.
