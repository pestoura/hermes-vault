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
- last previously accepted GREEN head: `da7d16b5e162b2f110062b40a5b510c1af23b4f8`
- first review-tests / verified RED head: `72f350590b0f24e1f235c95a462b37efea222306`
- minimal production candidate: `152da7959781b47725bac20e91ff287e81a0a985`
- current tests-only review head: `f7f4f8f79ec5b7092fd49492539b6f206e710ffc`

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

These PASS labels belong only to `da7d16b5...` until the final current lane receives fresh exact-head verification.

## Security review hardening — verified causal RED

Tests at exact head `72f350590b0f24e1f235c95a462b37efea222306` covered cleanup and error redaction.

Exact checkout execution:

```text
PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_v2_epic03_vault_review_hardening.py
```

Result: **7 failed / 0 passed**. All seven failures were feature-causal:

- broad rejected record cleanup count `0`, expected `1`;
- `ready=False` record cleanup count `0`, expected `1`;
- broker preserved synthetic backend `RuntimeError` as `__cause__`;
- Vault request preserved synthetic backend `RuntimeError` as `__cause__`;
- Vault revoke preserved synthetic backend `RuntimeError` as `__cause__`;
- per-grant `revoke()` leaked the synthetic backend `RuntimeError`;
- gateway cleanup failure leaked the synthetic backend `RuntimeError` before the required terminal outcome.

The only warning was an unrelated pytest configuration warning for `asyncio_mode`.

Classification: **VALID TDD RED**.

## Minimal production candidate

The production candidate is:

`152da7959781b47725bac20e91ff287e81a0a985`

It is exactly three commits ahead of the verified RED head and changes only:

- `src/hermes_mcp_bridge/v2/provider_credentials.py`;
- `src/hermes_mcp_bridge/v2/vault_credentials.py`;
- `src/hermes_mcp_bridge/v2/provider_gateway.py`.

Candidate behavior:

- cleans provider-issued records rejected after issuance or marked `ready=False`;
- suppresses explicit backend exception chaining at broker/provider boundaries;
- wraps request-scoped grant `apply`/`revoke` with sanitized `CredentialError` conversion;
- fails closed on invalid grants with best-effort cleanup;
- contains gateway cleanup failure and preserves terminal audit flow;
- read cleanup failure => `ERROR / E-CRED-UNAVAILABLE / payload={}`;
- write cleanup failure => `UNKNOWN / E-CRED-UNAVAILABLE / payload={}`.

A reconstructed semantic harness covering the original seven review cases is GREEN. This is **auxiliary evidence only** and is not treated as repository exact-head PASS.

## Additional review finding — secret-bearing `__context__`

The canonical EPIC-03 secret boundary prohibits secret material in an `exception`, not only in audit/result serialization.

Python `raise CredentialError(...) from None` removes the explicit `__cause__` and suppresses rendering of the previous exception, but the caught backend exception remains reachable in `__context__` while raising inside the `except` block.

Therefore a backend exception containing credential material can remain attached to the supposedly sanitized exception object.

A tests-only commit was added:

`f7f4f8f79ec5b7092fd49492539b6f206e710ffc`

It is one commit ahead of `152da795...` and changes only `tests/test_v2_epic03_vault_review_hardening.py`, adding four `__context__ is None` assertions to the broker, Vault request, Vault revoke and per-grant cleanup exception-redaction cases.

No production code was changed after this finding.

Current state:

- semantic expectation: the four new assertions fail against `152da795...`;
- exact-head exception-context RED: **NOT_RUN**;
- production fix for exception context: **NOT_STARTED**.

TDD requires a genuine causal RED before any production correction.

## Current exact-head gate state

At current Bridge head `f7f4f8...`:

| Gate | State |
|---|---|
| exception-context RED | NOT_RUN exact-head |
| review-hardening GREEN | NOT_RUN exact-head |
| all EPIC-03 targeted | NOT_RUN exact-head |
| Phase 7 acceptance | NOT_RUN exact-head |
| production activation | NOT_RUN exact-head |
| Ruff | NOT_RUN exact-head |
| compileall | NOT_RUN exact-head |
| full pytest | NOT_RUN exact-head |

The prior repository-side PASS gates remain evidence for `da7d16b5...`, not for the current lane.

## Hosted CI — current tests-only head

GitHub Actions created CI run `31975682497` for `f7f4f8f79ec5b7092fd49492539b6f206e710ffc`.

Observed:

- `test (3.11)`: job did not start, `steps=[]`;
- `test (3.12)`: job did not start, `steps=[]`;
- `secret scan (tree + history)`: job did not start, `steps=[]`;
- image / isolated acceptance / Trivy / SBOM: skipped.

GitHub annotation states that the jobs were not started because recent account payments failed or the spending limit needs to be increased.

Classification: **`BLOCKED_EXTERNAL_BILLING`** — neither code failure nor PASS.

A repository search found no declared `self-hosted` Actions lane or alternate remote test harness. No ad-hoc runner lane is introduced as part of EPIC-03.

The ChatGPT-side Hermes MCP binding also became unavailable/disabled while attempting execution. That is an executor/control-plane blocker, not a repository PASS or failure.

## Required next repository sequence

1. execute `tests/test_v2_epic03_vault_review_hardening.py` on exact current head `f7f4f8...` and capture the exception-context causal RED;
2. only after that RED, implement the minimal exception-context sanitization fix;
3. run review-hardening GREEN + all EPIC-03 targeted tests + Phase 7 + production activation;
4. perform fresh exact-head Ruff + compileall + full pytest;
5. perform formal code review against exact canonical base/final head;
6. update this evidence with the final verified SHA;
7. do not merge while mandatory hosted CI is externally blocked unless a separate governance decision explicitly defines an alternative release gate.

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
