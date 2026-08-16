# EPIC-03 Credential Broker Core & Bridge V2 Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the provider-neutral Credential Broker and Hermes Bridge V2 execution contracts that prove NO_SECRET_TO_MODEL, lifecycle cleanup, cancellation cleanup, separate tool capabilities and sanitized batch results without requiring live Vault credentials.

**Architecture:** The Broker owns capability lifecycle and exposes only safe descriptors. Provider adapters may hold temporary credential material inside a non-serializable `PrivateCapability` containing a mutable byte buffer; Bridge/tool execution receives that private object only inside a bounded session context and the buffer is zeroized on cleanup. A registry tracks only opaque capability handle, correlation identifiers, lease/reference metadata and cleanup state. Bridge V2 implements direct, agent and batch execution against ports, never serializing private material.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `enum`, `uuid`, `datetime`, `typing`, `unittest`), JSON evidence manifests. No network or Vault SDK dependency in this slice.

## Global Constraints

- Parent branch is EPIC-02 exact head `cdb712e77495f1d04914149f16b648774b698e57`.
- Capability types: `delegated_operation`, `dynamic_credential`, `wrapped_secret`, `memory_only`, `tmpfs_file`, `static_secret`.
- Delivery preference remains delegated > dynamic > wrapped > memory-only > tmpfs > static.
- Public Broker responses never contain token, SecretID, password, private key, authorization header, wrapped payload after unwrap or recovery/unseal material.
- `PrivateCapability` is deliberately non-JSON-serializable and owns mutable `bytearray` material that is zeroized at cleanup.
- Registry/evidence never store private material.
- Every request carries `execution_id`, `plan_id`, `request_id`, `tool_call_id`, `principal`, `tool_identity`, `action`, `resource_scope`, `risk_class`, `requested_ttl_s`.
- Capability handle is opaque random UUID-derived identity and is not a credential.
- Default requested TTL <=300s; hard maximum <=1800s.
- Cancellation blocks new issue operations for the execution and revokes/cleans every active capability for that execution.
- Batch execution issues one independent capability per tool call and always joins only sanitized results.
- Live Vault/Bridge integration, dynamic credential engines and real secrets remain NOT_RUN.

---

### Task 1: Model, correlation and safe serialization

**Files:**
- Create: `broker/model.py`
- Create: `broker/redaction.py`
- Create: `tests/test_epic03_broker.py`

**Interfaces:**
- `CapabilityRequest.from_dict(data) -> CapabilityRequest`
- `CapabilityDescriptor.to_public_dict() -> dict`
- `PrivateCapability.zeroize() -> None`
- `sanitize(value) -> JSON-safe value`

- [ ] Write RED tests for mandatory correlation fields, TTL bounds, allowed capability types and stable public descriptor fields.
- [ ] Prove `PrivateCapability` raises on JSON serialization and zeroizes every material byte.
- [ ] Prove recursive sanitizer redacts sensitive keys/patterns but preserves correlation/lease metadata.
- [ ] Implement minimal model/redaction modules and run targeted tests GREEN.

### Task 2: Provider port, lifecycle registry and Broker API

**Files:**
- Create: `broker/ports.py`
- Create: `broker/registry.py`
- Create: `broker/service.py`
- Modify: `tests/test_epic03_broker.py`

**Interfaces:**
- `CapabilityProvider.issue(request) -> PrivateCapability`
- `CapabilityProvider.revoke(private_capability) -> None`
- `CapabilityRegistry.register(...)`, `status(handle)`, `active_for_execution(execution_id)`
- `CredentialBroker.request(request) -> CapabilityDescriptor`
- `CredentialBroker.status(handle) -> CapabilityDescriptor`
- `CredentialBroker.revoke(handle, reason) -> CapabilityDescriptor`
- `CredentialBroker.cancel_execution(execution_id) -> list[CapabilityDescriptor]`

- [ ] RED tests prove registry stores no `material` field and refuses duplicate handle/request IDs.
- [ ] RED tests prove request/status/revoke transitions `ACTIVE -> REVOKED`, provider revoke executes once, material is zeroized and status is safe.
- [ ] RED tests prove cancellation revokes all active capabilities for exactly one execution, blocks subsequent request for that execution and leaves other executions untouched.
- [ ] Implement provider Protocol, registry and Broker service; run targeted tests GREEN.

### Task 3: Tool execution session and NO_SECRET_TO_MODEL boundary

**Files:**
- Create: `broker/session.py`
- Modify: `broker/service.py`
- Modify: `tests/test_epic03_broker.py`

**Interfaces:**
- `CredentialBroker.session(request) -> CapabilitySession` context manager.
- `CapabilitySession.private_capability` available only inside context.
- Context cleanup revokes/zeroizes on normal completion and exception.

- [ ] RED tests use a synthetic secret marker and prove it reaches only the fake tool executor's private buffer, never descriptor/evidence/result/exception text.
- [ ] RED tests prove exception cleanup and cancellation cleanup are idempotent.
- [ ] Implement session context and safe exception wrapping; run targeted tests GREEN.

### Task 4: Hermes Bridge V2 direct, agent and batch paths

**Files:**
- Create: `bridge_v2/runtime.py`
- Create: `bridge_v2/evidence.py`
- Create: `tests/test_epic03_bridge.py`

**Interfaces:**
- `BridgeV2.execute_direct(call, executor) -> dict`
- `BridgeV2.execute_agent(call, agent_executor) -> dict`
- `BridgeV2.execute_batch(calls, executor) -> dict`
- Each call includes a `CapabilityRequest`; executors accept `(call, PrivateCapability)` and return arbitrary tool data which is sanitized before public return.

- [ ] RED tests prove direct and agent paths receive private capability but public result is sanitized.
- [ ] RED batch test issues independent github/outlook/grafana capabilities and proves distinct handles/material; one tool cannot access another tool's capability object.
- [ ] RED partial-failure test proves each session cleanup runs and joined result contains sanitized per-tool status only.
- [ ] Implement Bridge runtime and evidence builder; run targeted tests GREEN.

### Task 5: Evidence manifests and repository acceptance

**Files:**
- Create: `broker/evidence.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `IMPLEMENTATION-CHECKLIST.md`
- Create: `docs/19-epic03-credential-broker-runbook.md`

**Interfaces:**
- Evidence schema `hermes-vault-broker-evidence/v1`.
- Fields: correlation IDs, principal, tool identity, action/resource, capability type/handle, lease_id when safe, timestamps, cleanup_required, final status, cleanup status, sanitized error category.

- [ ] RED tests reject evidence containing sensitive-key names or known synthetic secret marker.
- [ ] Implement evidence builder and runbook for future Vault provider/Bridge integration.
- [ ] Extend CI to compile broker/bridge modules and run full repository tests.
- [ ] Run local combined suite, compileall and Bash syntax.
- [ ] Open stacked draft PR against `epic-02/identity-kv-contracts`, linked to #5.
- [ ] If GitHub runner remains billing-blocked, record `BLOCKED_EXTERNAL_BILLING`, never PASS; keep PR unmerged and all live EPIC-03 gates NOT_RUN.