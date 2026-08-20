# Production Promotion Gates — No Auto-Promotion (HITL)

**Scope:** Hermes shared Vault service (`deployments/vault/`). This runbook
records the production-readiness gate and the HITL stops only. It is
documentation; no code path in this repository performs promotion.

**Invariant:** `NO_AUTO_PROMOTION` — the service is NEVER auto-promoted to
production use. Operator sign-off is required in addition to the two objective
proofs (spec §10, §16.3, ADR-012, INV-2).

---

## Production-readiness gate (mandatory, fail-closed)

Promotion to production use requires ALL of the following, independently
verified:

1. **Restore drill PASS** — `RESTORE_DRILL_PASS` recorded from an isolated
   restore-drill (`deployments/vault/scripts/restore-drill.sh`) in a
   non-production environment (spec §10, ADR-012).
2. **Audit PASS** — at least one audit device enabled and functional, with
   redaction verified, before any real consumer secret is migrated
   (spec §9, ADR-011, INV-7/INV-9).
3. **Owner sign-off** — explicit human owner approval. This is never derived
   from code, CI status, or runtime state.

The lifecycle gate `promotion_ready(state, restore_drill_passed,
audit_passed, owner_signoff)` encodes this exactly and returns `False`
unless `UNSEALED_READY` AND all three proofs are `True`. Degraded/terminal
states (`ERROR`, `DECOMMISSIONED`, `INITIALIZED_SEALED`, `UNINITIALIZED`) are
never promotion-ready regardless of proof (INV-6).

---

## HITL stops (never automated, never coded)

The following are operator-only steps and MUST NOT be performed by this
repository, CI, or any unattended task (INV-10):

- `vault operator init` (Shamir 3/2)
- `vault operator unseal` ×2 by quorum
- Initial root token handling / revoke
- AppRole SecretID issuance / wrapping
- TLS private-key generation / custody
- Production promotion sign-off

All Shamir shares, root token, and recovery keys are recorded to **out-of-band
custody** and are never written to this repo, logs, CI output, or evidence
bundles (INV-1, ADR-014).
