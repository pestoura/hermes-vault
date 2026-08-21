# Resume Hermes Vault

This file is the safe continuation checkpoint for a future ChatGPT/Hermes session.

## Canonical checkpoint

```text
VAULT_CORE_OPERATIONAL=VERIFIED
VAULT_CORE_OPERATIONAL_RUNTIME_PASS=VERIFIED
RESTORE_DRILL_PASS=VERIFIED
SCHEDULED_SNAPSHOT_PASS=VERIFIED
JIT_SELF_REVOKE_REVALIDATION=PENDING
FIRST_CONSUMER_BOOTSTRAP=NOT_RUN
UNSEALED_READY=false
```

The Vault core is already installed, initialized, unsealed, audited, recoverable and running continuously on HermesJarvas. Do **not** restart at Phase 0, installation, TLS provisioning or initial bootstrap.

## Resume order

1. Read `docs/16-current-runtime-status.md`.
2. Read `README.md` and `IMPLEMENTATION-CHECKLIST.md`.
3. Verify current `main` and exact-SHA CI before any mutation.
4. Verify the live Vault health/readiness state without secrets.
5. Revalidate administrative JIT self-revoke against the Git policy baseline.
6. Continue to `FIRST_CONSUMER_BOOTSTRAP` for HSL when the JIT lifecycle gate is closed.
7. Preserve HSL legacy signing as verify-only during controlled migration.
8. Promote `UNSEALED_READY` only after the first-consumer acceptance gate actually passes.

## Guardrails

```text
NO SECRET TO THE MODEL
NO SHAMIR SHARE TO AUTOMATION
NO ROOT TOKEN PERSISTENCE
NOT_RUN != PASS
GREEN/PASS -> continue
HITL only for real secret/recovery boundaries
```

## Safe live checks

Safe checks include repository state, CI status, Docker container metadata, restart policy, network attachments, systemd timer status and the strict-TLS `/v1/sys/health` response. Audit contents, snapshots, private keys and encrypted credential contents are not inspection targets.

## Expected next technical sequence

```text
JIT_SELF_REVOKE_REVALIDATION
  -> FIRST_CONSUMER_BOOTSTRAP
  -> hsl-transit / hsl-signing
  -> hsl-signer policy + AppRole
  -> HSL positive/negative acceptance
  -> controlled consumer cutover
  -> UNSEALED_READY promotion only if evidenced
```

## Source of truth

If historical conversation context disagrees with the repository or live evidence, prefer:

1. current safe live observation;
2. dated evidence under `docs/evidence/`;
3. `docs/16-current-runtime-status.md`;
4. accepted ADRs/specs;
5. historical context.
