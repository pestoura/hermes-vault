# HSL-owned deployment decommission / verify-retention runbook

**Status:** approved transition design. External HSL mutation/cutover remains `NOT_RUN`. Shared Vault deployment/start and TLS pre-init connectivity are `VERIFIED_PRE_INIT` (2026-08-21), while init/unseal/audit/consumer acceptance remain separately gated.

**Owner:** `pestoura/hermes-vault` owns the shared service. This runbook never writes to `pestoura/hermes-security-labs`. **hermes-vault does not modify pestoura/hermes-security-labs** under this runbook.

## Current ruling — controlled parallel-run

The current approved architecture is **controlled parallel-run** per ADR-018 and ADR-020. The shared Vault is tested in parallel without becoming a second authority for new signatures. After all acceptance gates pass, the state becomes `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY`: the shared signer signs new evidence and the legacy `hermes-lab-l1-signer` remains **verify-only** for historical evidence.

The earlier ruling **"direct ownership migration / NO parallel live Vault"** is **superseded** by the owner resolution of 2026-08-21. It remains mentioned here only as provenance and must not drive implementation.

## Historical observations — inherited, not re-verified

Earlier Task I1/I2 documentation carried two **historical observations** inherited from read-only inspection:

- the HSL Vault deployment was described as **never promoted**;
- HSL main was described as **no longer carries** `deployment/vault-lab-l1`.

These observations are **inherited** and **not re-verified** in this change. They do not override the approved key-continuity requirement because historical signatures may still require the legacy non-exportable key even if the deployment path is not currently present on HSL trunk. Live HSL state must be re-confirmed before any cross-repo execution.

## Key continuity — resolved

ADR-018 resolves the prior §25.1 owner decision:

- retain `hermes-lab-l1-signer` for historical verification only;
- no new legacy signing after cutover;
- do not use **bulk re-sign / bulk re-signing** to replace the original historical signature chain;
- retire the legacy verification surface only after retention/continuity sign-off.

This is now a **resolved** architectural decision, not an open choice.

## Transition states

1. `LEGACY_SIGN_ACTIVE` — historical pre-cutover state.
2. `PARALLEL_SHARED_PENDING_ACCEPTANCE` — shared service acceptance proceeds; legacy authority remains unchanged.
3. `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` — target transition state after all gates pass.
4. `LEGACY_VERIFY_RETIRED` — final state after continuity/retention sign-off.

## Mandatory cutover gates

Entry into `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` requires fresh evidence for at least:

```text
VAULT_HEALTH_PASS
VAULT_UNSEALED
AUDIT_PASS
RESTORE_DRILL_PASS
TLS_CONNECTIVITY_PASS
HSL_ISOLATION_PASS
SIGN_VERIFY_PASS
LEGACY_HISTORICAL_VERIFY_PASS
NO_SECRET_TO_MODEL
OWNER_CUTOVER_SIGNOFF
```

No missing gate may be treated as PASS.

## Decommission rules

The consumer-owned HSL deployment is not immediately deleted at cutover. Its signing capability is removed/disabled by the separate HSL-local change while only the minimum verification surface necessary for historical evidence is retained.

`LEGACY_VERIFY_RETIRED` requires explicit continuity/retention sign-off. Retirement is not based solely on elapsed time and cannot occur while historical evidence still requires the legacy verifier.

## Failure / rollback

Before cutover, a failed shared-service acceptance leaves the legacy state unchanged.

After cutover, automatic restoration of legacy signing is prohibited. Any return to legacy signing authority would be a new owner-gated authority transition and must be separately reviewed and evidenced.

## Scope boundary

- **No HSL mutation** is performed here; the actual change in `pestoura/hermes-security-labs` is **OUT OF SCOPE** and `NOT_RUN`.
- `hermes-vault` never writes to the consumer repository under this runbook.
- No deletion, freeze, cutover, or retirement command is executed by this document.
- No credentials, secret values, private material, or recovery material are present.

## Repo-side verification

Static tests verify that this runbook records the controlled parallel-run ruling, marks the previous `NO parallel live Vault` posture as superseded provenance, encodes ADR-018/ADR-020, preserves inherited observations as not re-verified, defines all transition states/gates, and keeps external execution `NOT_RUN`.
