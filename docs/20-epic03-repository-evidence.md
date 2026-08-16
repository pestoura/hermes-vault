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
- last previously accepted full GREEN: `da7d16b5e162b2f110062b40a5b510c1af23b4f8`
- verified review RED head: `72f350590b0f24e1f235c95a462b37efea222306`
- first cleanup/error-redaction candidate: `152da7959781b47725bac20e91ff287e81a0a985`
- exception-context tests-only head: `f7f4f8f79ec5b7092fd49492539b6f206e710ffc`
- current implementation head: `38b8163c651903ffaa89b9a74a6324c293545aac`

The old `hermes-vault` PR #17 / `epic-03/credential-broker-core` remains **SUPERSEDED — DO NOT MERGE**.

## Accepted historical GREEN

At `da7d16b5...` only:

- EPIC-03 broker/provider/hardening: `18/18 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`;
- production activation: `24/24 PASS`;
- batch: successful parallel requests, distinct request-scoped grants, independent cleanup and sanitized result/audit.

These PASS labels are not attributed to the current lane until fresh final-head verification exists.

## Verified review-hardening RED

Exact Bridge checkout `72f350590b0f24e1f235c95a462b37efea222306` executed:

```text
PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_v2_epic03_vault_review_hardening.py
```

Result: **7 failed / 0 passed**, all feature-causal:

1. broad/cross-domain provider-issued record rejected without cleanup;
2. `ready=False` provider-issued record rejected without cleanup;
3. broker retained secret-bearing backend error in the exception chain;
4. Vault request retained secret-bearing backend error in the exception chain;
5. Vault revoke retained secret-bearing backend error in the exception chain;
6. per-grant cleanup leaked the raw backend error;
7. gateway cleanup failure escaped before the terminal sanitized audit outcome.

Classification: **VALID TDD RED**.

## First minimal production candidate

`152da7959781b47725bac20e91ff287e81a0a985` added only the behavior required by that RED:

- cleanup of provider-issued records rejected after issuance or marked `ready=False`;
- sanitized broker/provider backend exception conversion;
- sanitized request-scoped grant `apply`/`revoke` callbacks;
- fail-closed invalid-grant handling;
- gateway cleanup-failure containment and terminal audit semantics;
- read cleanup failure => `ERROR / E-CRED-UNAVAILABLE / payload={}`;
- write cleanup failure => `UNKNOWN / E-CRED-UNAVAILABLE / payload={}`.

A reduced semantic harness for those original cases was GREEN. This was auxiliary evidence only, not full exact-head verification.

## Additional security finding — Python `__context__`

Review identified that `raise CredentialError(...) from None` clears explicit `__cause__` and suppresses display of the previous exception but still retains the caught backend exception in `__context__` when raised from inside the `except` block.

The EPIC-03 secret boundary prohibits secret material in an exception object, so a backend exception containing credential material must not remain reachable through `__context__`.

Tests-only head `f7f4f8f79ec5b7092fd49492539b6f206e710ffc` added four `__context__ is None` assertions covering:

- broker provider request;
- Vault request;
- Vault revoke;
- request-scoped grant cleanup.

No production code changed in that commit.

## Reduced causal RED/GREEN for exception context

The current ChatGPT runtime still cannot clone GitHub directly and the hosted Actions runner remains account-level billing blocked. The specific Python exception property was therefore exercised in a reduced harness using the production candidate behavior and a synthetic sentinel.

### RED

Before the context fix: **4/4 FAIL**.

Each sanitized `CredentialError` retained:

```text
RuntimeError("SYNTHETIC_EPIC03_ERROR_MATERIAL")
```

in `__context__`.

Classification: **feature-causal reduced RED for the exception-context property**. It is not labelled full exact-head suite execution.

### Minimal context fix

Commits:

- `bac2ace30dfe190227636bb44d0ea38a1773129c` — broker/provider-call context detachment;
- `7d6d2546ce0154f92167c531534f46be2b63ef96` — Vault/grant context detachment;
- `38b8163c651903ffaa89b9a74a6324c293545aac` — restore the prior rejected-record cleanup reason semantics while keeping detached exception context.

The implementation constructs the sanitized `CredentialError` while handling the backend exception, returns it as a value, exits the `except` block, and raises it only afterwards. This prevents Python from linking the backend exception into `__context__`.

### GREEN

The same four reduced checks after the fix: **4/4 PASS**.

No real secret, Vault token, SecretID, root token or credential material was used.

## Review of the context fix

Diff `f7f4f8... → 38b8163...` changes only:

- `src/hermes_mcp_bridge/v2/provider_credentials.py`;
- `src/hermes_mcp_bridge/v2/vault_credentials.py`.

Review found one unintended semantic deviation in the first helper version: rejected-record cleanup could preserve an arbitrary provider `CredentialError` reason. The pre-existing contract normalized all such cleanup failures to `E-CRED-UNAVAILABLE`. Commit `38b8163...` restores that behavior.

No new gateway change was required for the exception-context extension.

## Current verification state

At Bridge head `38b8163c651903ffaa89b9a74a6324c293545aac`:

| Gate | State |
|---|---|
| exception-context reduced RED/GREEN | PASS as reduced targeted evidence |
| full-checkout review-hardening | NOT_RUN current head |
| all EPIC-03 targeted | NOT_RUN current head |
| Phase 7 acceptance | NOT_RUN current head |
| production activation | NOT_RUN current head |
| Ruff | NOT_RUN current head |
| compileall | NOT_RUN current head |
| full pytest | NOT_RUN current head |

No historical PASS is promoted to this final candidate without fresh evidence.

## Hosted CI after temporary repository publication

The repository was temporarily made public and new commits were pushed afterwards.

For current head `38b8163...`, GitHub Actions created CI run `31976218931`, but:

- `test (3.11)` did not start a runner;
- `test (3.12)` did not start a runner;
- `secret scan (tree + history)` did not start a runner;
- dependent image / isolated acceptance / Trivy / SBOM was skipped.

The jobs have `steps=[]` and `runner_id=0`. GitHub's annotation still states that recent account payments failed or the spending limit must be increased.

Classification: **`BLOCKED_EXTERNAL_BILLING`** — neither code failure nor PASS.

Making the repository public did not clear the account-level Actions restriction.

The ChatGPT-side Hermes MCP binding is also not currently exposed in this session, so it cannot be used as the full-checkout executor at this checkpoint.

## Required next repository sequence

1. obtain an approved full-checkout executor;
2. run `tests/test_v2_epic03_vault_review_hardening.py` on exact current/final head;
3. run all EPIC-03 targeted tests + Phase 7 + production activation;
4. run Ruff + compileall + full pytest on exact final head;
5. perform formal final code review against canonical base/final head;
6. update this evidence with final exact-SHA results;
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

No live Vault authentication, init, unseal, SecretID unwrap/use, Vault/root-token use, secret migration or real credential resolution was performed while producing this evidence.
