# EPIC-03 VaultCredentialProvider — Implementation Plan

> **Execution rule:** design/spec → plan → TDD RED → minimal GREEN → hardening → CI/exact-SHA → PR/merge → post-merge verification. Never promote an unexecuted gate.

## Goal

Add a Vault-native credential backend to the existing Hermes MCP Bridge V2 without duplicating the broker architecture and without exposing secret material to the model, public payloads, audit or evidence.

## Canonical inputs

- `pestoura/hermes-vault@28a86a407101a16a167695191323435b867ec737`
- `pestoura/hermes-mcp-bridge@3717bd5469b061a44294b27e1a7510d477d3752b`
- ADR-018 / `docs/19-epic03-vault-credential-provider.md`
- existing Bridge V2 `ProviderCredentialBroker`, `AuthorizationHandle`, `ProviderGateway`, `V2Composition`

## Branches

- Vault contract branch: `epic-03/vault-provider-contract`
- Bridge implementation branch: `epic-03/vault-credential-provider`

The existing `hermes-vault` PR #17 / `epic-03/credential-broker-core` is superseded and must remain read-only until formally closed; do not cherry-pick its duplicated `broker/` or `bridge_v2/` code.

---

## Task 1 — TDD contract for VaultCredentialProvider

**Repository:** `pestoura/hermes-mcp-bridge`

**Create:** `tests/test_v2_epic03_vault_credentials.py`

### RED tests

Add tests that import a not-yet-implemented `VaultCredentialProvider` and exercise only synthetic values through an injectable fake client.

Required initial tests:

1. provider status is false when backend unavailable;
2. `github/github.read` request returns a broker-consumable opaque grant/record;
3. undeclared capability is refused;
4. cross-provider/tool request is refused;
5. public `repr`/`str` never exposes synthetic sentinel;
6. grant/handle rejects pickle/copy/json serialization;
7. request uses no caller-supplied Vault path.

### Execute RED

```bash
pytest -q tests/test_v2_epic03_vault_credentials.py
```

**Expected RED:** failure specifically because `VaultCredentialProvider`/provider binding behavior is absent. Import/syntax/environment failure is not accepted as feature RED.

Commit tests only after a causal RED has been captured.

---

## Task 2 — Minimal provider contract

**Repository:** `pestoura/hermes-mcp-bridge`

**Create:** `src/hermes_mcp_bridge/v2/vault_credentials.py`

**Modify:** `src/hermes_mcp_bridge/v2/provider_credentials.py`

### Design

Introduce a minimal capability-oriented port, not a secret-path API.

Expected shape:

```python
class VaultCapabilityClient(Protocol):
    def status(self, provider_id: str, credential_capability_id: str) -> bool: ...
    def request(self, provider_id: str, credential_capability_id: str) -> OpaqueGrant: ...
    def revoke(self, provider_id: str, credential_capability_id: str) -> None: ...
```

`OpaqueGrant` must expose behavior only (`apply`, `revoke`) and no material accessor. The concrete test fake may keep a synthetic sentinel internally.

`VaultCredentialProvider` validates a closed set of allowed `(provider_id, credential_capability_id)` pairs. Initial allowed pair:

```text
("github", "github.read")
```

Do not accept `path`, `secret_path`, mount or arbitrary Vault key from the caller.

Extend the broker minimally so that a credential capability can be backed by a provider while preserving static `CredentialRecord` support and all existing domain/scope checks.

### GREEN

Run:

```bash
pytest -q tests/test_v2_epic03_vault_credentials.py
pytest -q tests/test_v2_phase7_integration_acceptance.py
```

Do not proceed until both are green.

---

## Task 3 — Cleanup-aware AuthorizationHandle

**Modify:** `src/hermes_mcp_bridge/v2/provider_credentials.py`

Add an optional idempotent cleanup/revoke callback to `AuthorizationHandle` while keeping:

- single-use;
- deadline-bound;
- redacted `repr`/`str`;
- no copy/pickle/json;
- no material accessor.

`revoke()` must be idempotent and call provider cleanup at most once.

**Tests in:** `tests/test_v2_epic03_vault_credentials.py`

Prove:

- success cleanup once;
- repeated revoke cleanup once;
- expired/spent handle remains non-reusable;
- no sentinel in exceptions or rendering.

---

## Task 4 — Gateway cleanup on every exit path

**Modify:** `src/hermes_mcp_bridge/v2/provider_gateway.py`

Move handle lifecycle under a `try/finally` that begins immediately after broker resolution and covers authorization application plus provider adapter execution.

Add tests for:

1. authorization application failure;
2. provider refusal;
3. provider exception;
4. cancellation/interruption;
5. successful provider call.

All must revoke/cleanup exactly once.

Run:

```bash
pytest -q tests/test_v2_epic03_vault_credentials.py
pytest -q tests/test_v2_phase7_integration_acceptance.py
```

Target gates:

- `LEASE_CLEANUP_PASS`
- `CANCEL_CLEANUP_PASS`

---

## Task 5 — Walking skeleton github.read

Use the existing GitHub manifest distinction:

- operation capability `github.repo_read`;
- credential capability `github.read`.

Construct the real Bridge V2 objects in the test:

```text
ProviderRequest(github.repo_read)
→ ProviderGateway
→ ProviderCredentialBroker
→ VaultCredentialProvider(fake client)
→ AuthorizationHandle
→ GitHub-like provider adapter boundary
→ sanitized ProviderCallResult
→ IntegrationAuditLedger
→ cleanup
```

Assertions:

- exactly one credential resolution;
- exactly one provider call;
- sentinel exists only at fake/grant/header boundary;
- sentinel absent from outcome payload;
- sentinel absent from audit canonical representation;
- cleanup exactly once.

Target gates:

- `BROKER_ACCEPTANCE_PASS`
- `NO_SECRET_TO_MODEL`
- `SANITIZED_RESULT_PASS`

---

## Task 6 — Cross-tool/domain denial

Use existing `CredentialDomain` enforcement plus provider allowed-pair validation.

Tests:

- GitHub broker cannot request `jira.read`;
- GitHub Vault provider cannot issue another provider's capability;
- requested scopes wider than granted scopes still fail at broker before provider request;
- no provider request/adapter call on denial.

Target gate: `NO_CROSS_TOOL_SECRET_ACCESS`.

---

## Task 7 — Batch isolation

Exercise the existing V2 batch execution path or the closest accepted production composition path that invokes the ProviderGateway independently per item.

Prove at least two requests receive:

- different opaque grants;
- different AuthorizationHandle instances;
- independent cleanup;
- no reuse after one item fails;
- sanitized aggregate output.

Do not claim live parallelism unless actual concurrency is exercised.

Target gates:

- `BATCH_EXECUTION_PASS`
- `SEPARATE_CAPABILITIES_PASS`

---

## Task 8 — Vault unavailable fail-closed

Fake client reports unavailable or raises a stable provider-unavailable condition.

Expected:

- broker/gateway refusal;
- zero provider adapter calls;
- no fallback to `FileGitHubAuthorizationProvider`, env or another credential record;
- sanitized error/reason code;
- partial grant cleanup when applicable.

Target gate: `FAIL_CLOSED_VAULT_UNAVAILABLE_PASS`.

---

## Task 9 — Serialization and redaction hardening

Tests must attempt:

```python
repr(obj)
str(obj)
copy.copy(obj)
copy.deepcopy(obj)
pickle.dumps(obj)
json.dumps(obj)
```

for the opaque grant/handle as applicable.

Search result/audit/evidence projections for synthetic sentinel and secret-shaped keys.

Target gates:

- `NO_SECRET_SERIALIZATION_PASS`
- `NO_SECRET_TO_MODEL`
- `SANITIZED_RESULT_PASS`

---

## Task 10 — Regression verification

Run in this order and record exact output:

```bash
pytest -q tests/test_v2_epic03_vault_credentials.py
pytest -q tests/test_v2_phase7_integration_acceptance.py
pytest -q tests/test_v2_production_activation.py
ruff check src tests
python -m compileall -q src tests
pytest -q
```

If any command is unavailable, record it as `NOT_RUN` or blocker; never infer PASS.

Hosted GitHub Actions remains `BLOCKED_EXTERNAL_BILLING` unless a workflow run actually starts and completes.

---

## Task 11 — Exact-SHA evidence and PRs

After local GREEN/hardening:

1. commit Bridge changes;
2. record exact Bridge head SHA in the Vault spec/coordination branch;
3. run the verification commands again against that exact Bridge head;
4. open companion Bridge PR to `main`;
5. open/update Vault PR stacked onto `epic-02/identity-kv-contracts`;
6. PR descriptions list every gate as `PASS`, `FAIL`, or `NOT_RUN` and explicitly state hosted CI status;
7. request code review before merge;
8. merge only when all required repository-side gates are verified and no destructive/HITL boundary is crossed.

---

## Task 12 — Post-merge verification

After any eventual merge, fetch the merged exact SHAs and re-run the accepted verification set. Do not reuse pre-merge test output as post-merge evidence.

Live runtime remains independent and stays `NOT_RUN` until the Jarvas/Vault lane is explicitly executed through its own gates.
