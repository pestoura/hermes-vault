# EPIC-03 — Credential Broker & Hermes Bridge V2 integration runbook

## Purpose

Define the operational boundary for integrating Vault-backed capabilities into Hermes Bridge V2 without exposing credential material to ChatGPT, public MCP results, evidence manifests or the Broker registry.

This repository slice implements the provider-neutral core only. A live Vault provider and live Hermes Bridge integration remain separate execution work.

## Core boundary

A request carries only authorization/context metadata:

```text
execution_id
plan_id
request_id
tool_call_id
principal
tool_identity
action
resource_scope
risk_class
requested_ttl_s
capability_type
```

The public response is a `CapabilityDescriptor` containing an opaque handle and safe lease/expiry/cleanup metadata. It never carries capability material.

Private provider material lives in `PrivateCapability.material` as a mutable `bytearray` and is available only inside a bounded `CapabilitySession` context. Cleanup overwrites that buffer before the private object is released.

### Important limitation

Python-level `bytearray` overwrite is **best-effort application-level zeroization**. It does not prove operating-system, allocator, swap, crash-dump or interpreter-copy erasure. Live deployment must therefore also use short TTLs, process isolation, no core dumps where appropriate, bounded logs and no persistent secret serialization.

## Capability types

The provider-neutral model supports:

```text
delegated_operation
dynamic_credential
wrapped_secret
memory_only
tmpfs_file
static_secret
```

Preferred delivery order remains:

```text
delegated
→ dynamic
→ wrapped
→ memory-only
→ tmpfs
→ static
```

The last two require explicit operational justification. This EPIC does not implement a tmpfs/static-secret provider.

## Broker lifecycle

### Request

```python
request = CapabilityRequest.from_dict({...})
descriptor = broker.request(request)
```

The Broker rejects:

- missing correlation identifiers;
- unknown capability types;
- TTL <= 0 or > 1800 seconds;
- duplicate `request_id`;
- duplicate provider capability handle;
- new requests for an execution already cancelled;
- provider identity/type mismatches.

The registry stores only the safe descriptor. Private material remains outside the registry.

### Session execution

Tools should normally use:

```python
with broker.session(request) as session:
    private = session.private_capability
    # tool/provider-specific use occurs here
```

On normal completion or exception, the context invokes revoke/cleanup and zeroizes the private buffer.

The public Bridge response must be built from sanitized tool output plus post-cleanup evidence. Do not return `PrivateCapability` or the raw provider result.

### Status and revoke

```python
broker.status(handle)
broker.revoke(handle, "completed")
```

Revoke is idempotent. Provider revoke executes at most once for an active capability. Cleanup failure is recorded as `cleanup_status=ERROR`; the private buffer is still overwritten best-effort.

### Cancellation

```python
broker.cancel_execution(execution_id)
```

Cancellation:

1. marks the execution cancelled before cleanup begins;
2. prevents issuance of any new capability for that execution;
3. revokes every active capability registered to that execution;
4. leaves unrelated executions untouched;
5. preserves only safe registry/evidence metadata.

## NO_SECRET_TO_MODEL

The redaction boundary recursively removes sensitive dictionary keys such as token, authorization, password, private-key and wrapped-payload fields. It also defensively redacts known capability material and selected high-confidence textual credential patterns.

This redaction is a **secondary control**. The primary control is architectural: secret material must never be included in public result structures in the first place.

The following are prohibited from public result/evidence/log fields:

- Vault token;
- AppRole SecretID;
- wrapping payload after unwrap;
- OAuth/client secret;
- API/PAT token;
- password;
- private key;
- recovery/unseal material;
- authorization/cookie credential data.

## Bridge V2 paths

### Direct path

```text
validated deterministic call
→ Broker capability session
→ tool executor with PrivateCapability
→ sanitize tool output
→ revoke/zeroize
→ safe evidence
→ public result
```

### Agent path

The lifecycle is identical, but the executor is an agent-aware adapter. Agent reasoning/output does not receive a serializable credential value.

### Batch path

The current repository contract executes each call through its own independent capability session and joins only sanitized results. Tests prove distinct handles/private objects/material per tool and cleanup for every call, including partial failure.

**This slice does not claim live parallel execution.** Parallel orchestration can be added at the Hermes runtime integration layer after cancellation/race semantics are validated under real load. The EPIC-03 repository gate proves multi-tool isolation, not concurrency performance.

## Evidence

Schema:

```text
hermes-vault-broker-evidence/v1
```

Safe fields include:

```text
execution_id
plan_id
request_id
tool_call_id
principal
tool_identity
action
resource_scope
risk_class
capability_type
capability_handle
lease_id (when non-sensitive)
expires_at
cleanup_required
final_status
capability_status
cleanup_status
error_category
```

Evidence never stores private capability material.

## Future Vault provider

The live adapter should implement `CapabilityProvider`:

```python
class CapabilityProvider(Protocol):
    def issue(self, request: CapabilityRequest) -> PrivateCapability: ...
    def revoke(self, capability: PrivateCapability) -> None: ...
```

Provider implementations may map requests to:

- delegated Transit/PKI operations;
- dynamic secret leases;
- response-wrapped KV material;
- bounded memory-only delivery.

Do not expose a generic ChatGPT-facing `secret.read(path=*)` API.

## Future Hermes Bridge integration

Before enabling live traffic:

1. map each Bridge tool to the EPIC-02 `tool_identity` contract;
2. bind action/resource schemas to allowed capabilities;
3. ensure `request_id`/`tool_call_id` are unique;
4. propagate execution/plan correlation IDs;
5. route cancellation into `broker.cancel_execution()`;
6. prove cleanup on success, tool exception, timeout and cancellation;
7. prove cross-tool capability isolation;
8. run NO_SECRET_TO_MODEL tests using synthetic and real provider-shaped fixtures;
9. confirm Vault audit correlation without copying credential data into evidence.

## Gates

Repository implementation may provide contract evidence, but the EPIC live gates remain `NOT_RUN` until the real Vault provider and Hermes Bridge execute on Jarvas:

```text
BROKER_ACCEPTANCE_PASS      = NOT_RUN
NO_SECRET_TO_MODEL          = NOT_RUN
LEASE_CLEANUP_PASS          = NOT_RUN
CANCEL_CLEANUP_PASS         = NOT_RUN
BATCH_EXECUTION_PASS        = NOT_RUN
SEPARATE_CAPABILITIES_PASS  = NOT_RUN
NO_CROSS_TOOL_SECRET_ACCESS = NOT_RUN
SANITIZED_RESULT_PASS       = NOT_RUN
```
