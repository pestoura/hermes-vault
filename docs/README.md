# Hermes Vault — documentation index

**Repository status:** architecture/implementation blueprint; no production Vault deployment is claimed.

## Canonical reading path

| Order | Document | Purpose |
|---:|---|---|
| 1 | `00-context-goals.md` | Scope, goals and non-goals |
| 2 | `01-reference-architecture.md` | Target architecture and trust boundaries |
| 3 | `02-vault-capabilities.md` | Candidate Vault capability catalogue |
| 4 | `03-identity-auth-policy.md` | Identity, auth methods, policies and least privilege |
| 5 | `04-hermes-integration.md` | Credential Broker / Hermes integration design |
| 6 | `05-jit-privilege.md` | JIT privilege elevation model |
| 7 | `06-pki-mtls.md` | PKI and mTLS target design |
| 8 | `07-transit-evidence.md` | Transit/signing/HMAC and cryptographic evidence |
| 9 | `08-audit-observability.md` | Audit and monitoring model |
| 10 | `09-bootstrap-recovery.md` | Bootstrap, seal/unseal, recovery and break-glass |
| 11 | `10-operations-runbooks.md` | Planned operating procedures |
| 12 | `11-migration-plan.md` | Migration strategy for existing credentials |
| 13 | `12-implementation-roadmap.md` | Delivery phases, gates and acceptance |
| 14 | `13-security-decisions.md` | Security decisions/constraints |
| 15 | `14-references.md` | External authoritative references |
| 16 | `15-delivery-operating-model.md` | Delivery/wave operating model |
| 17 | `15-threat-model.md` | Threat model |

## Implementation entry points

- [`../RESUME.md`](../RESUME.md) — how a future session should resume safely.
- [`../IMPLEMENTATION-CHECKLIST.md`](../IMPLEMENTATION-CHECKLIST.md) — operational checklist for implementation progress.

## Evidence / status rules

The documentation uses the following distinction:

- **DESIGNED** — architecture/contract exists in docs;
- **IMPLEMENTED** — corresponding runtime/configuration exists;
- **TESTED** — executable acceptance evidence exists;
- **DEPLOYED** — runtime deployment evidence exists;
- **PRODUCTION_ENABLED** — the capability is explicitly active in the intended environment.

At the time of this review, the repository is primarily **DESIGNED**. Do not infer later states from design completeness.

## Truth hierarchy during implementation

When implementation begins, use this order if sources disagree:

1. current read-only observation of the real Jarvas/Hermes environment;
2. current accepted security decisions in this repository;
3. official HashiCorp documentation for the selected Vault version/edition;
4. implementation roadmap/checklist;
5. historical design assumptions or prior chat context.

## Documentation maintenance rule

Any document that changes from target design to implementation guidance should explicitly record which facts are **observed**, which are **chosen design decisions**, and which remain **open**. Never add real secret values to evidence, examples or troubleshooting notes.
