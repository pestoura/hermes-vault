# 15 — Delivery Operating Model

## Purpose

This document governs **how Hermes Vault work is delivered**. The implementation roadmap defines *what* must be built; this document defines the execution model used to turn that roadmap into usable, validated baselines quickly and safely.

The operating rule is:

```text
GREEN | PASS | SUPPORTED | ACCEPTED
                 ↓
        CONTINUE AUTOMATICALLY
```

A gate that did not execute is not GREEN. Work stops only for a real blocker: security or recovery risk, destructive ambiguity, missing required credential/human action, broken shared baseline, external dependency unavailable, or evidence insufficient to make a truthful support claim.

## Delivery objective

Optimize for **time to usable baseline**, not number of completed documents, branches, PRs, or theoretical phases.

Hermes Vault must be delivered incrementally:

```text
architecture/recovery contract
        ↓
non-production Vault baseline
        ↓
workload identity + least privilege
        ↓
first non-critical secret migration
        ↓
Credential Broker MVP
        ↓
Bridge V2 integration
        ↓
Transit / PKI / JIT / dynamic secrets
        ↓
broad migration + production readiness
```

Do not hold an early usable baseline until all later Vault capabilities are implemented.

## FAST DELIVERY topology

Normal execution uses:

```text
5–6 development lanes
+
1 Controller / Integration lane
```

Use fewer lanes when dependency chains make more parallelism artificial. Do not create parallel work that merely increases rebases, CI pressure, or architectural divergence.

### Controller / Integration lane

The controller owns throughput, not feature development. It continuously:

1. reconciles `main`, PRs, CI, runtime evidence and roadmap state;
2. identifies the current critical path;
3. classifies failures;
4. fixes or routes deterministic failures immediately;
5. integrates GREEN work;
6. revalidates the shared baseline;
7. launches the next independent wave;
8. maintains truthful evidence and support state.

A red lane does not freeze unrelated GREEN lanes unless it exposes a shared security, architecture, recovery, contract or `main` regression.

## Waves, not serial backlog execution

Work is grouped into **delivery waves** consisting of independent or weakly coupled outcomes.

Example:

```text
WAVE
├── lane A: Vault runtime/TLS baseline
├── lane B: audit + evidence
├── lane C: snapshot/restore mechanics
├── lane D: identity/policy contracts
├── lane E: observability
└── lane F: operator/runbook validation
                 ↓
        integration / acceptance
                 ↓
             baseline
```

The exact wave must be chosen from the live repository state. Never reopen already integrated work because an older plan mentions it.

## Vertical delivery slices

Prefer a thin end-to-end slice over broad unfinished foundations.

For Hermes Vault, a valuable slice proves:

```text
identity
  → policy
  → Vault capability
  → consumer/tool
  → sanitized result
  → audit/evidence
  → revoke/expiry/cleanup
```

A component that exists only in isolation is not considered a delivered capability.

## Fast gates before expensive gates

Every lane must run the cheapest deterministic gates before consuming expensive CI or runtime acceptance.

Order conceptually:

```text
syntax / format / lint
        ↓
static validation / policy lint
        ↓
targeted unit tests
        ↓
contract / docs / secret invariants
        ↓
security tests
        ↓
integration
        ↓
runtime acceptance
        ↓
recovery / rollback validation where required
```

Do not use remote CI as a basic linter when the same failure can be found before push.

Heavy jobs should depend on successful fast gates whenever the workflow supports it.

## Failure handling

Failures are classified immediately.

### Deterministic / local failure

Examples: lint, formatting, schema, policy syntax, docs consistency, simple typing, deterministic unit test.

```text
FAIL → inspect → patch → targeted retest → push → continue
```

Do not perform blind retries.

### Product/integration failure

Examples: Vault API behavior mismatch, lease cleanup failure, policy unexpectedly broad, consumer integration regression.

Isolate the lane, fix the root cause and continue independent lanes.

### Global blocker

Freeze promotion only for issues such as:

- recovery model unsafe or unproven;
- root/recovery material handling violation;
- secret exposure;
- fail-open authorization;
- broken `main` shared baseline;
- cross-tool credential isolation failure;
- destructive state ambiguity;
- required human/security decision.

## Definition of Delivery

A work item may be code-complete without being delivered.

A Hermes Vault capability is **delivered** only when the applicable chain is proven:

```text
IMPLEMENTED
+ TESTED
+ POLICY-VALIDATED
+ SECURITY-VALIDATED
+ INTEGRATED
+ EVIDENCED
+ OPERABLE/RECOVERABLE
= DELIVERED
```

Support labels must remain truthful. Use explicit states such as:

```text
PLANNED
IMPLEMENTED_NOT_ACCEPTED
MOCK_OR_ISOLATED_ONLY
SUPPORTED_NON_PRODUCTION
SUPPORTED
DEGRADED
BLOCKED
```

## Product-specific first delivery targets

### Delivery Target A — non-production Vault baseline

Minimum useful outcome:

- Vault starts under the selected deployment model;
- TLS enforced;
- audit device operational;
- health/readiness proven;
- snapshot created and validated;
- recovery design materially tested as far as the environment allows;
- no secret/recovery material committed or exposed to the model.

### Delivery Target B — workload identity slice

Prove one real workload identity with least privilege and negative tests.

### Delivery Target C — first secret migration

Migrate one non-critical secret end-to-end, prove consumer restart/use, rotation/rollback and legacy secret removal.

### Delivery Target D — Credential Broker MVP

Prove one real tool can request a bounded capability, consume it without exposing the underlying secret, and clean it up on success/cancellation.

These targets should be versionable independently instead of waiting for full Phase 12 completion.

## CI and repository rules

- Prefer PR validation for feature branches and full post-merge validation on `main`; avoid equivalent duplicate CI triggers.
- Separate fast quality gates from costly integration/runtime/security jobs where practical.
- Preserve mandatory security and recovery gates; FAST DELIVERY changes ordering and duplication, not assurance requirements.
- Merge automatically when all required gates are GREEN and no real blocker exists.
- After every merge, validate `main` before promoting the next dependent baseline.

## Evidence rule

Every promoted baseline must answer:

```text
WHAT changed?
WHICH commit/version?
WHICH gates executed?
WHAT evidence proves it?
WHAT remains unsupported/degraded?
HOW is rollback/recovery performed?
```

No executed gate means no claim of PASS.

## Conversation / agent restart rule

A new ChatGPT/Hermes execution session must not rely on remembered state. It must first reconcile:

```text
main + HEAD + PRs + CI + docs + runtime evidence
```

Then resume the highest-priority safe wave according to this operating model.

## Permanent execution algorithm

```text
DISCOVER
   ↓
RECONCILE LIVE STATE
   ↓
IDENTIFY CRITICAL PATH
   ↓
FORM DELIVERY WAVE
   ↓
PARALLEL IMPLEMENTATION
   ↓
FAST GATES
   ↓
FAIL? ── yes ──→ FIX / RETEST
   │
   no
   ↓
INTEGRATE
   ↓
FULL / RUNTIME / RECOVERY GATES
   ↓
BASELINE GREEN
   ↓
VERSION + EVIDENCE
   ↓
NEXT WAVE
```

This operating model remains active until explicitly superseded by a documented repository decision.