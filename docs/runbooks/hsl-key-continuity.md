# HSL key continuity and controlled signing cutover

**Status:** approved transition design. Shared Vault deployment/start and TLS connectivity are verified; initialization is `VERIFIED_INITIALIZED_SEALED`; unseal is `VERIFIED_UNSEALED_HEALTHY`, with `VAULT_HEALTH_PASS` and `VAULT_UNSEALED` verified on 2026-08-21. Audit, restore, HSL migration/cutover and remaining acceptance gates stay `NOT_RUN`.

**Owner boundary:** `pestoura/hermes-vault` owns the shared Vault service. `pestoura/hermes-security-labs` is a consumer and is not modified by this runbook.

## Decision

ADR-018 and ADR-020 resolve the previous HSL key-continuity and cutover choices:

- the legacy Transit key `hermes-lab-l1-signer` remains available only for historical signature verification after cutover;
- the legacy key is never exported and is never used for new signing after cutover;
- historical evidence is not subjected to **bulk re-signing / bulk re-sign** as a substitute for preserving the original signature chain;
- the shared `hsl-transit/hsl-signing` key becomes the sole signing authority for new evidence only after the live acceptance gates pass;
- the transition uses a controlled parallel-run, but never two concurrent authorities for new signatures.

## Transition states

### `LEGACY_SIGN_ACTIVE`

Historical pre-cutover state. The existing HSL signing path remains authoritative while the shared service is not yet accepted. This label describes the legacy state; this runbook does not activate or modify it.

### `PARALLEL_SHARED_PENDING_ACCEPTANCE`

The shared Vault may be stood up and tested under the separate HITL/live implementation procedure, while the legacy signing authority remains unchanged. The shared path is not yet authoritative for production/new HSL evidence.

Entry to this state never implies production readiness. Tests may validate the new path with synthetic evidence only.

### `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY`

Target transition state. Entry is permitted only when all mandatory gates below are freshly verified:

```text
VAULT_HEALTH_PASS
VAULT_UNSEALED
AUDIT_PASS
RESTORE_DRILL_PASS
TLS_CONNECTIVITY_PASS
HSL_ISOLATION_PASS
SIGN_VERIFY_PASS
LEGACY_HISTORICAL_VERIFY_PASS
NO_CROSS_TOOL_SECRET_ACCESS
NO_SECRET_TO_MODEL
OWNER_CUTOVER_SIGNOFF
```

At entry:

- `hsl-transit/hsl-signing` becomes the sole authority for new HSL signatures;
- legacy `hermes-lab-l1-signer` becomes **verify-only**;
- any new legacy signing is prohibited;
- failure to validate the shared signer fails closed and blocks cutover rather than silently returning to a broader/static credential path.

### `LEGACY_VERIFY_RETIRED`

Final state. The legacy verification surface is removed only after the retention/continuity obligation for historical evidence is explicitly satisfied and owner sign-off is recorded. Retirement is never inferred from elapsed time alone.

## Network/TLS contract

The shared Vault endpoint for container consumers is `https://hermes-vault:8200` on Docker network `hermes-security-plane`. The host operator endpoint remains loopback-only at `https://127.0.0.1:8200` / `https://localhost:8200`.

The server certificate must validate the minimum SAN set:

```text
DNS:hermes-vault
DNS:localhost
IP:127.0.0.1
```

TLS private-key generation and custody remain operator-only HITL.

## Verification semantics

Historical verification must bind each evidence record to the original signature/key context. The transition must prove both:

1. a representative historical evidence signature still verifies against the legacy verify-only path; and
2. newly generated synthetic acceptance evidence signs and verifies against `hsl-transit/hsl-signing`.

Passing only the new signer is insufficient to retire historical verification.

## Failure and rollback rules

Before cutover, a failed shared-service acceptance leaves the legacy authority unchanged.

After entry into `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY`, automatic rollback to legacy signing is forbidden. Restoring legacy signing authority would create a second/new authority transition and therefore requires a new owner-gated decision with evidence and audit trail.

## Out of scope / NOT_RUN

This runbook does not execute any of the following:

- HSL repository/configuration mutation — `NOT_RUN`;
- live Vault start/TLS — `VERIFIED_PRE_INIT` (2026-08-21); init — `VERIFIED_INITIALIZED_SEALED`; unseal/health — `VERIFIED_UNSEALED_HEALTHY` (`VAULT_UNSEALED`, `VAULT_HEALTH_PASS` verified);
- Transit mount/key creation — `NOT_RUN`;
- AppRole/SecretID/token issuance — `NOT_RUN`;
- TLS private-key generation — `VERIFIED_PROVISIONED` (2026-08-21); material remains operator-custodied, git-ignored and absent from this document;
- production cutover — `NOT_RUN`.

The actual cross-repo HSL change is a separate implementation in `pestoura/hermes-security-labs` after the shared service acceptance gates are met.
