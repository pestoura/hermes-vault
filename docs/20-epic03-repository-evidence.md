# 20 — EPIC-03 repository evidence

## Purpose

Bind the EPIC-03 Vault contract to the exact companion implementation in `pestoura/hermes-mcp-bridge` while keeping repository evidence separate from live Vault state.

## Canonical topology

### `pestoura/hermes-vault`

- branch: `epic-03/vault-provider-contract`
- PR: `#18` (draft / open / unmerged)
- stacked base: `epic-02/identity-kv-contracts`
- exact EPIC-02 base SHA: `28a86a407101a16a167695191323435b867ec737`

### `pestoura/hermes-mcp-bridge`

- branch: `epic-03/vault-credential-provider`
- PR: `#110` (draft / open / unmerged)
- exact base SHA: `3717bd5469b061a44294b27e1a7510d477d3752b`
- **last accepted GREEN head:** `da7d16b5e162b2f110062b40a5b510c1af23b4f8`
- **current tests-only review head:** `72f350590b0f24e1f235c95a462b37efea222306`

The old `hermes-vault` PR #17 / `epic-03/credential-broker-core` is **SUPERSEDED** architecture and must not be merged into this lane.

## Accepted TDD evidence through `da7d16b5...`

### RED 1 — provider-backed broker lifecycle

Exact test head `46ec7071067d279e4deeb770ba9e91cb266891e3`:

- `8 failed`;
- all failures caused by missing `ProviderCredentialBroker.bind_provider`;
- no environment/import failure.

Classification: **VALID FEATURE-CAUSAL RED**.

### GREEN 1

Head `599efcbd336f52a05addfc2effc501fb16329c2b`:

- EPIC-03 targeted: `8/8 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`.

### RED 2 — concrete VaultCredentialProvider

Exact test head `3e76a9662a1847672c4d29055c09822c9a617ab0`:

- existing lifecycle tests: `8/8 PASS`;
- concrete provider tests: `8 FAIL`;
- all new failures caused by absent `hermes_mcp_bridge.v2.vault_credentials`.

Classification: **VALID FEATURE-CAUSAL RED**.

### GREEN 2

Head `3503a4e89249ba324e82430192a52c8de0e7797c`:

- EPIC-03 broker/provider: `16/16 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`.

### Hardening GREEN

Content committed as `da7d16b5e162b2f110062b40a5b510c1af23b4f8`:

- EPIC-03 broker/provider/hardening: `18/18 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`;
- production activation: `24/24 PASS`.

Batch evidence:

- aggregate `SUCCESS`;
- both steps `SUCCESS`;
- `max_observed_inflight >= 2`;
- two distinct request-scoped grants;
- independent cleanup for each grant;
- two provider calls / two credential resolutions;
- synthetic sentinel absent from results and audit.

## Security review hardening — current tests-only head

Static review of PR #110 identified additional lifecycle/error-redaction cases not covered by the accepted GREEN head:

1. a provider-issued record rejected as broad/cross-domain must be cleaned up before refusal;
2. a provider-issued record with `ready=False` must be cleaned up before refusal;
3. backend exceptions must not remain attached as secret-bearing exception causes;
4. per-grant cleanup exceptions must be normalized and sanitized;
5. cleanup failure must still produce exactly one terminal sanitized audit outcome rather than escape the gateway `finally`.

Tests for these cases are committed at exact head:

`72f350590b0f24e1f235c95a462b37efea222306`

This head changes tests only. The new review-hardening tests are currently:

`RED = NOT_RUN`

Reason: Hermes upstream admission is `gateway_state=draining` / `accepting_new_work=false`. Production code has **not** been changed for these new tests. The previous GREEN evidence must not be attributed to `72f3505...`.

## EPIC-03 gate status

At the last accepted GREEN head `da7d16b5...`:

| Gate | State |
|---|---|
| `BROKER_ACCEPTANCE_PASS` | PASS |
| `NO_SECRET_TO_MODEL` | PASS |
| `LEASE_CLEANUP_PASS` | PASS — original success/error lifecycle; review tests will tighten rejected-grant coverage |
| `CANCEL_CLEANUP_PASS` | PASS |
| `BATCH_EXECUTION_PASS` | PASS |
| `SEPARATE_CAPABILITIES_PASS` | PASS |
| `NO_CROSS_TOOL_SECRET_ACCESS` | PASS |
| `SANITIZED_RESULT_PASS` | PASS |
| `NO_SECRET_SERIALIZATION_PASS` | PASS |
| `FAIL_CLOSED_VAULT_UNAVAILABLE_PASS` | PASS |

Merge remains blocked until the review-hardening TDD cycle is executed and a new exact-head verification is produced.

## Hosted CI

GitHub Actions on the current tests-only head `72f350590b0f24e1f235c95a462b37efea222306` created CI run `31970284770`.

Observed:

- `test (3.11)`: failure before execution, `steps=[]`, `runner_id=0`;
- `test (3.12)`: failure before execution, `steps=[]`, `runner_id=0`;
- `secret scan (tree + history)`: failure before execution, `steps=[]`, `runner_id=0`;
- image / isolated acceptance / Trivy / SBOM: skipped.

GitHub annotation states that the job was not started because recent account payments failed or the spending limit needs to be increased.

Classification: **`BLOCKED_EXTERNAL_BILLING`**.

This is neither code failure nor CI PASS.

## Required next repository sequence

1. execute `tests/test_v2_epic03_vault_review_hardening.py` on exact `72f3505...` and capture a feature-causal RED;
2. only after RED, implement the minimal cleanup/error-redaction fix;
3. run review-hardening GREEN + all EPIC-03 targeted tests + Phase 7 + production activation;
4. commit and run fresh detached exact-head verification:
   - EPIC-03 targeted;
   - Phase 7;
   - production activation;
   - Ruff;
   - compileall;
   - full pytest suite;
5. perform formal code review against exact base/head;
6. do not merge while mandatory hosted CI is externally blocked unless a separate governance decision explicitly defines an alternative release gate.

## Live state — unchanged

```text
Vault runtime       = NOT_RUN
signer decision     = NO_DECISION
supplier            = NO_SELECTION
trust               = UNBOUND
promotion_allowed   = false
runtime_status      = NOT_RUN
execution_authority = NONE
campaign            = BLOCKED / HOLD
```

No live Vault authentication, init, unseal, SecretID unwrap/use, Vault token/root-token use, secret migration or real credential resolution was performed while producing this evidence.
