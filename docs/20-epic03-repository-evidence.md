# 20 — EPIC-03 repository evidence

## Purpose

This document binds the EPIC-03 Vault contract in this repository to the exact companion implementation in `pestoura/hermes-mcp-bridge` without claiming that repository evidence is live Vault evidence.

## Canonical repository topology

### Vault contract / coordination

- repository: `pestoura/hermes-vault`
- branch: `epic-03/vault-provider-contract`
- stacked base: `epic-02/identity-kv-contracts`
- exact EPIC-02 base SHA: `28a86a407101a16a167695191323435b867ec737`

### Bridge implementation

- repository: `pestoura/hermes-mcp-bridge`
- PR: `#110` — `EPIC-03: add in-process VaultCredentialProvider backend`
- branch: `epic-03/vault-credential-provider`
- exact base SHA: `3717bd5469b061a44294b27e1a7510d477d3752b`
- exact current head SHA: `da7d16b5e162b2f110062b40a5b510c1af23b4f8`
- PR state: `draft / open / unmerged`

The old `hermes-vault` PR #17 / `epic-03/credential-broker-core` remains a superseded architecture and must not be merged into this lane.

## TDD evidence

### RED — provider-backed broker lifecycle

Exact test head:

`46ec7071067d279e4deeb770ba9e91cb266891e3`

Command:

```bash
pytest -q tests/test_v2_epic03_vault_credentials.py
```

Observed:

- `8 failed`;
- one distinct cause: missing `ProviderCredentialBroker.bind_provider`;
- no import/environment/credential failure.

Classification: **VALID FEATURE-CAUSAL RED**.

### GREEN — broker lifecycle

Head:

`599efcbd336f52a05addfc2effc501fb16329c2b`

Observed:

- EPIC-03 targeted: `8/8 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`.

### RED — concrete VaultCredentialProvider

Exact test head:

`3e76a9662a1847672c4d29055c09822c9a617ab0`

Observed:

- existing EPIC-03 lifecycle: `8/8 PASS`;
- concrete provider contracts: `8 FAIL`;
- one distinct cause: absent `hermes_mcp_bridge.v2.vault_credentials` module.

Classification: **VALID FEATURE-CAUSAL RED**.

### GREEN — concrete provider

Exact head:

`3503a4e89249ba324e82430192a52c8de0e7797c`

Observed:

- EPIC-03 broker/provider: `16/16 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`.

### Hardening content committed as current Bridge head

Current Bridge head:

`da7d16b5e162b2f110062b40a5b510c1af23b4f8`

Observed before final detached exact-head sweep:

- EPIC-03 broker/provider/hardening: `18/18 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`;
- production activation: `24/24 PASS`.

Batch hardening evidence:

- aggregate status `SUCCESS`;
- both steps `SUCCESS`;
- `max_observed_inflight >= 2`;
- exactly two credential requests;
- two distinct opaque grants;
- cleanup independently matched to each grant;
- two provider calls and two credential resolutions;
- synthetic sentinel absent from result projection and audit records.

The final detached exact-head sweep on `da7d16b...` for Ruff, compileall and the full test suite is still **NOT_RUN** while Hermes admission is in `gateway_state=draining`. It must not be inferred from the targeted results above.

## EPIC-03 repository-side gates

| Gate | State | Repository evidence |
|---|---|---|
| `BROKER_ACCEPTANCE_PASS` | PASS | real Bridge walking skeleton with `VaultCredentialProvider` and synthetic client |
| `NO_SECRET_TO_MODEL` | PASS | sentinel absent from public outcome and audit |
| `LEASE_CLEANUP_PASS` | PASS | success/error cleanup exactly once |
| `CANCEL_CLEANUP_PASS` | PASS | BaseException-style cancellation path executes cleanup |
| `BATCH_EXECUTION_PASS` | PASS | actual `BatchScheduler`, two successful steps, observed inflight >= 2 |
| `SEPARATE_CAPABILITIES_PASS` | PASS | two separate request-scoped opaque grants |
| `NO_CROSS_TOOL_SECRET_ACCESS` | PASS | broker/domain + provider allow-list deny cross-domain/undeclared capability |
| `SANITIZED_RESULT_PASS` | PASS | synthetic material absent from provider result/audit projection |
| `NO_SECRET_SERIALIZATION_PASS` | PASS | request handle remains non-copyable/non-pickleable/non-JSON-serializable/redacted |
| `FAIL_CLOSED_VAULT_UNAVAILABLE_PASS` | PASS | unavailable backend refuses; no adapter call and no file/env fallback |

These gates are repository-side behavioral properties exercised only with synthetic material. They do not prove live Vault readiness, bootstrap or policy deployment.

## Hosted CI

Bridge PR #110 triggered GitHub Actions on exact head `da7d16b5...`.

Observed CI run: `31969959458`.

The following jobs failed before runner execution:

- `test (3.11)`;
- `test (3.12)`;
- `secret scan (tree + history)`.

Evidence:

- `steps=[]`;
- `runner_id=0` / no runner name;
- GitHub check annotation states that the job was not started because recent account payments failed or the spending limit needs to be increased.

Classification:

`BLOCKED_EXTERNAL_BILLING`

This is **not** a code failure and **not** CI PASS. Dependent image/isolated acceptance/Trivy/SBOM was skipped and remains **NOT_RUN**.

## Live state — unchanged

Repository evidence does not change:

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

No live Vault authentication, init, unseal, SecretID unwrap/use, Vault token use, root-token use, secret migration or real credential resolution was performed while producing this evidence.

## Remaining repository work before merge

1. run a fresh detached exact-head sweep on Bridge `da7d16b5...`:
   - EPIC-03 targeted tests;
   - Phase 7 integration acceptance;
   - production activation;
   - Ruff;
   - compileall;
   - full pytest suite;
2. perform code review against base `3717bd...` and head `da7d16b5...`;
3. update PR evidence with the exact-head results;
4. do not merge while required hosted CI is blocked unless repository governance explicitly decides and records an alternative release gate.
