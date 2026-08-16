# 20 — EPIC-03 repository evidence

## Purpose

Bind the EPIC-03 Vault contract to the exact companion implementation in `pestoura/hermes-mcp-bridge` while keeping repository evidence separate from live Vault state.

## Canonical topology

### `pestoura/hermes-vault`

- branch: `epic-03/vault-provider-contract`
- PR: `#18` — draft / open / unmerged
- stacked base: `epic-02/identity-kv-contracts`
- exact EPIC-02 base SHA: `28a86a407101a16a167695191323435b867ec737`

### `pestoura/hermes-mcp-bridge`

- branch: `epic-03/vault-credential-provider`
- PR: `#110` — draft / open / unmerged
- canonical base SHA: `3717bd5469b061a44294b27e1a7510d477d3752b`
- last accepted full GREEN: `da7d16b5e162b2f110062b40a5b510c1af23b4f8`
- verified review RED: `72f350590b0f24e1f235c95a462b37efea222306`
- first cleanup/error-redaction candidate: `152da7959781b47725bac20e91ff287e81a0a985`
- exception-context tests-only head: `f7f4f8f79ec5b7092fd49492539b6f206e710ffc`
- context-detachment implementation: `38b8163c651903ffaa89b9a74a6324c293545aac`
- apply/cleanup lifecycle tests-only head: `b5c61ebc3037feda2ca55e4d1ad9099dc81cd80a`
- prior Bridge implementation head (gateway fix lane): `c141245ecedc6fb093b3a4d9e95978ef33de81f9`
- final Bridge head (lint-only fix; exact final head this evidence binds to): `88cbd915a5158e1fa27d15eaa939ab29b1f5aba3`

The old `hermes-vault` PR #17 / `epic-03/credential-broker-core` remains **SUPERSEDED — DO NOT MERGE**.

## Architecture decision

EPIC-03 remains bound to ADR-018 / Option A:

```text
ProviderGateway
    -> ProviderCredentialBroker
    -> VaultCredentialProvider
    -> Vault capability client
    -> AuthorizationHandle
    -> provider adapter
    -> sanitized result + audit/evidence
    -> cleanup/revoke
```

No separate broker service, listener, sidecar or generic secret-path interface is introduced in the MVP.

## Historical accepted GREEN

The most recent full repository execution accepted before the security-review extensions is `da7d16b5e162b2f110062b40a5b510c1af23b4f8`:

- EPIC-03 broker/provider/hardening: `18/18 PASS`;
- Phase 7 integration acceptance: `36/36 PASS`;
- production activation: `24/24 PASS`;
- batch aggregate: `SUCCESS`;
- two successful parallel steps;
- distinct request-scoped grants;
- independent cleanup;
- synthetic sentinel absent from results and audit.

These PASS labels belong only to `da7d16b5...` until the final current lane receives fresh full-checkout evidence.

## Security review hardening — verified full-checkout RED

Exact Bridge checkout `72f350590b0f24e1f235c95a462b37efea222306` executed:

```text
PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_v2_epic03_vault_review_hardening.py
```

Result: **7 failed / 0 passed**, all feature-causal:

1. a broad/cross-domain provider-issued record was rejected without cleanup;
2. a provider-issued `ready=False` record was rejected without cleanup;
3. broker error conversion retained a secret-bearing backend exception;
4. Vault request error conversion retained a secret-bearing backend exception;
5. Vault revoke error conversion retained a secret-bearing backend exception;
6. request-scoped grant cleanup leaked the backend error;
7. gateway cleanup failure escaped before the required terminal sanitized audit outcome.

Classification: **VALID TDD RED**.

## First cleanup/error-redaction candidate

Candidate `152da7959781b47725bac20e91ff287e81a0a985` introduced only the behavior required by that RED:

- cleanup for provider-issued records rejected after issuance or marked `ready=False`;
- sanitized broker/provider backend error conversion;
- sanitized request-scoped grant `apply` / `revoke` callbacks;
- fail-closed invalid-grant handling;
- gateway cleanup-failure containment;
- read cleanup failure => `ERROR / E-CRED-UNAVAILABLE / payload={}`;
- write cleanup failure => `UNKNOWN / E-CRED-UNAVAILABLE / payload={}`.

A reduced semantic harness for these behaviors was GREEN. It is auxiliary evidence and is not promoted to full exact-head PASS.

## Additional review finding — Python exception `__context__`

The EPIC-03 secret boundary prohibits secret material in an exception object. Python `raise CredentialError(...) from None` clears explicit `__cause__` and suppresses rendering of the previous exception, but a caught backend exception remains reachable in `__context__` when the sanitized exception is raised from inside the `except` block.

Tests-only head `f7f4f8f79ec5b7092fd49492539b6f206e710ffc` added four `__context__ is None` assertions covering:

- broker provider request;
- Vault request;
- Vault revoke;
- per-grant cleanup.

No production code changed in that commit.

### Reduced causal RED / GREEN

Because the current session cannot obtain a full repository checkout and GitHub Actions remains blocked before runner allocation, the specific Python exception property was exercised with production-equivalent control flow and a synthetic sentinel.

Before the fix: **4/4 causal FAIL**. The sanitized `CredentialError` retained `RuntimeError("SYNTHETIC_EPIC03_ERROR_MATERIAL")` in `__context__`.

The context-detachment implementation was then added:

- `bac2ace30dfe190227636bb44d0ea38a1773129c` — broker/provider-call detachment;
- `7d6d2546ce0154f92167c531534f46be2b63ef96` — Vault/grant detachment;
- `38b8163c651903ffaa89b9a74a6324c293545aac` — restore the pre-existing rejected-record cleanup reason semantics while retaining context detachment.

The implementation constructs a sanitized `CredentialError` while handling the backend exception, returns it as a value, exits the `except` block, and raises it only afterwards.

After the fix: **4/4 PASS** in the same reduced targeted harness.

This is explicitly **reduced targeted evidence**, not a full repository-suite PASS.

## Additional lifecycle review — `handle.apply()` failure followed by cleanup

Static review of `ProviderGateway.invoke()` at `38b8163...` found an early return inside the post-resolution `handle.apply()` `CredentialError` path:

```text
handle resolved
-> credential_resolutions incremented
-> handle.apply() raises CredentialError
-> return self._refuse(...)
-> finally invokes handle.revoke()
-> function returns immediately
```

Although Python executes the `finally`, the return skipped the post-finally `cleanup_failed` processing and also used `_refuse()`, whose pre-credential counters report zero credential resolutions.

Consequences:

1. apply failure + successful cleanup returned a refusal but incorrectly reported `credential_resolutions=0`;
2. apply failure + cleanup failure returned a refusal and ignored the cleanup-failure override instead of producing the established cleanup-failure outcome.

Tests-only head `b5c61ebc3037feda2ca55e4d1ad9099dc81cd80a` now distinguishes the two cases:

- apply failure + cleanup success => `REFUSED`, provider calls `0`, credential resolutions `1`, one terminal audit;
- apply failure + cleanup failure => read outcome `ERROR / E-CRED-UNAVAILABLE`, provider calls `0`, credential resolutions `1`, one terminal audit after cleanup.

A reduced execution of the pre-fix control flow produced causal RED in both branches:

- cleanup success: `REFUSED` but `credential_resolutions=0`;
- cleanup failure: still `REFUSED`, `credential_resolutions=0`, cleanup override unreachable.

Classification: **feature-causal reduced RED for the gateway lifecycle property**.

## Current gateway fix

Current Bridge head:

`c141245ecedc6fb093b3a4d9e95978ef33de81f9`

Commit message: `EPIC-03: defer apply refusal audit until credential cleanup`.

The change is confined to the post-resolution provider-execution block in `src/hermes_mcp_bridge/v2/provider_gateway.py`:

- removes the early `_refuse()` return after `handle.apply()` fails;
- records a pending `REFUSED` outcome instead;
- does not call the provider adapter after apply failure;
- always completes `handle.revoke()` first;
- successful cleanup preserves `REFUSED` and the correct credential-resolution count;
- failed cleanup overrides the pending refusal to `ERROR` for reads or `UNKNOWN` for writes with `E-CRED-UNAVAILABLE`;
- terminal audit remains exactly once and after cleanup.

Reduced control-flow GREEN after the fix:

- apply fail + cleanup success => `REFUSED`, provider calls `0`, credential resolutions `1`;
- apply fail + cleanup failure => `ERROR / E-CRED-UNAVAILABLE`, provider calls `0`, credential resolutions `1`.

Exact current source review confirms that the terminal audit is after cleanup and that no early return remains inside the `handle.apply()` refusal branch.

## Current change envelope

Comparison `38b8163... -> c141245...` is exactly three commits ahead and changes only:

- `src/hermes_mcp_bridge/v2/provider_gateway.py`;
- `tests/test_v2_epic03_vault_review_hardening.py`.

No architecture topology, public MCP tool surface, Vault path contract or live authority state is changed.

## Hosted CI — account-level external blocker (final head `88cbd915...`)

For final Bridge head `88cbd915a5158e1fa27d15eaa939ab29b1f5aba3`, GitHub Actions produced two pull_request runs, both concluded `failure`:

- `CI` run `31979987776` (2026-08-16T23:44:40Z): jobs `test (3.11)`, `secret scan (tree + history)`, `test (3.12)` all had `runner_id=0`, `steps=[]`, ~2s duration; dependent `image / isolated acceptance / trivy / sbom` skipped.
- `Release governance` run `31979987809` (2026-08-16T23:44:40Z): job `JDS-002 change / validation records` had `runner_id=0`, `steps=[]`, ~3s.

Every failed job carries GitHub's annotation: *"The job was not started because recent account payments have failed or your spending limit needs to be increased."* The Bridge repository was temporarily made public and the final commit was pushed after that, which did **not** clear the Actions restriction.

Classification: **`BLOCKED_EXTERNAL_BILLING`** — jobs never executed; not a code failure and not PASS.

No hosted-CI green exists for `88cbd915...`. PR #110 remains draft / open / unmerged pending a governance policy on hosted CI. The full repository-suite PASS results below were produced locally on the exact final head, not via hosted CI.

## Current gate state — exact final head `88cbd915a5158e1fa27d15eaa939ab29b1f5aba3`

Local exact-head verification was executed against `88cbd915...` (the lint-only final fix over `c141245...`). It is not hosted-CI output.

| Gate / verification | State |
|---|---|
| verified historical full RED at `72f3505...` | PASS as RED evidence |
| exception-context reduced RED/GREEN | PASS as targeted evidence |
| apply/cleanup lifecycle reduced RED/GREEN | PASS as targeted evidence |
| exact current modified-block source review | COMPLETE |
| review-hardening (exact-head) | 9 passed |
| EPIC-03 aggregate (exact-head) | 27 passed |
| Phase 7 acceptance (exact-head) | 36 passed |
| production activation (exact-head) | 24 passed |
| ruff check src tests | PASS |
| compileall | PASS |
| full pytest (exact-head) | 3080 passed, 2 pre-existing warnings, 0 failed |
| ShellCheck rollout tests | 3 passed |
| local secret scan `scripts/v2_phase9_secret_scan.py --history-commits 25` | scanned=true, finding_count=0, tree files=549, history commits=25 |
| synthetic EPIC-03 sentinels | 4 identifiers checked, all ABSENT from sanitized scope |
| TDD lint finding | initial ruff 8 violations; RED; minimal lint fix; GREEN; `88cbd915...` |
| formal final review after lint fix | no behavioral/security issue found |
| hosted CI | BLOCKED_EXTERNAL_BILLING |

No live Vault runtime operation occurred for `88cbd915...`.

## Required next repository sequence

1. local exact-head execution against `88cbd915...` is complete (see Current gate state above);
2. do not attribute any historical GREEN to the prior head without fresh exact-head evidence — resolved: exact-head runs executed;
3. perform no live Vault runtime operation;
4. do not merge while mandatory hosted CI remains externally blocked unless a separate governance decision explicitly defines an alternative release gate.

PR #18 remains draft / open / unmerged and must stay so pending the hosted-CI governance decision.

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
