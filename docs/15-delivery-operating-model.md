# 15 — Delivery Operating Model

## Purpose

This document governs **how Hermes Vault work is delivered**. The implementation roadmap defines *what* must be built; this document defines how that roadmap is turned into usable, validated baselines quickly and safely.

It follows the portfolio-level JDS-001 principles: small batches, vertical slices, walking skeletons, bounded WIP, fast feedback, evidence-based promotion, secure delivery and recovery-aware releases.

Permanent rule:

```text
GREEN | PASS | SUPPORTED | ACCEPTED
                 ↓
        CONTINUE AUTOMATICALLY
```

A gate that did not execute is not GREEN. Work stops only for a real blocker: security/recovery risk, destructive ambiguity, missing required human action or credential, broken shared baseline, external dependency unavailable, or insufficient evidence for a truthful support claim.

## Delivery objective

Optimize for **time to usable baseline**, not number of documents, branches, PRs or theoretical phases.

Preferred incremental progression:

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

Do not hold an early useful baseline until every later Vault capability exists.

## Work topology and WIP

The project does **not** require a fixed number of lanes or agents.

Parallel work is created only when outcomes are materially independent and reduce critical-path time. For the current Jarvas/Hermes environment, the default upper bound is:

```text
active development WIP <= 5–6 lanes
```

Use fewer lanes whenever dependency chains make more parallelism artificial. A lane may be executed by a human, agent, automation, CI job or other implementation mechanism.

### Integration Controller role

For concurrent delivery, one role owns integration throughput rather than feature volume. This is a role, not necessarily an agent.

It continuously:

1. reconciles `main`, PRs, CI, runtime evidence and roadmap state;
2. identifies the critical path and next usable baseline;
3. keeps WIP bounded;
4. classifies failures;
5. fixes/routes deterministic failures immediately;
6. integrates GREEN work;
7. revalidates the shared baseline;
8. opens the next safe work only when capacity exists;
9. keeps support/evidence state truthful.

A red lane does not freeze unrelated GREEN work unless it exposes a shared security, architecture, recovery, contract or `main` regression.

## Waves and vertical slices

Work may be grouped into delivery waves when several independent outcomes compose one baseline. Waves are a convenience, not a mandatory development structure.

Prefer thin end-to-end slices. For Hermes Vault, a valuable slice proves:

```text
identity
  → policy
  → Vault capability
  → consumer/tool
  → sanitized result
  → audit/evidence
  → revoke/expiry/cleanup
```

A component that exists only in isolation is not a delivered capability.

The first implementation should behave as a walking skeleton: the smallest safe end-to-end path through identity, policy, Vault and one real consumer before breadth is added.

## Fast gates before expensive gates

Run the cheapest deterministic gates before costly CI/runtime acceptance:

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

Do not use remote CI as a basic linter when the same failure can be found before push. Heavy jobs should depend on successful fast gates whenever practical.

## Failure handling

### Deterministic/local failure

Examples: lint, formatting, schema, policy syntax, docs consistency, simple typing, deterministic unit test.

```text
FAIL → inspect → root cause → patch → targeted retest → continue
```

No blind retries.

### Product/integration failure

Examples: Vault API mismatch, lease cleanup failure, policy unexpectedly broad, consumer integration regression.

Isolate the affected work, fix root cause and continue independent work if the shared baseline remains safe.

### Global blocker

Freeze promotion only for issues such as:

- recovery model unsafe or unproven;
- root/recovery material handling violation;
- secret exposure;
- fail-open authorization;
- broken `main` baseline;
- cross-tool credential isolation failure;
- destructive state ambiguity;
- required human/security decision.

## Definition of Delivery

Code completion is not delivery.

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

Use truthful states such as:

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

### A — non-production Vault baseline

Prove Vault startup, TLS, audit, health/readiness, snapshot and recovery design without exposing secret/recovery material.

### B — workload identity slice

Prove one real workload identity with least privilege and negative tests.

### C — first secret migration

Migrate one non-critical secret end to end, prove consumer use/restart, rotation/rollback and legacy-secret removal.

### D — Credential Broker MVP

Prove one real tool can request a bounded capability, consume it without exposing the underlying secret, and clean it up on success/cancellation.

Each target should be independently versionable rather than waiting for full production scope.

## CI and integration rules

- Prefer short-lived branches and PR validation.
- Avoid equivalent duplicate `push` + `pull_request` CI where repository protection permits.
- Separate fast quality gates from expensive integration/runtime jobs.
- Preserve security and recovery gates; acceleration changes ordering/duplication, not assurance.
- When concurrent GREEN PRs can invalidate each other, use merge-queue or equivalent serialized integration validation where available.
- Merge automatically only when required gates actually executed and are GREEN.
- Revalidate `main` after material integration.

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

## Resume rule

A resumed ChatGPT/Hermes/developer session first reconciles:

```text
main + HEAD + PRs + CI + docs + runtime evidence
```

Conversation memory is advisory only.

## Permanent algorithm

```text
DISCOVER
   ↓
RECONCILE LIVE STATE
   ↓
IDENTIFY NEXT USABLE BASELINE / CRITICAL PATH
   ↓
FORM MINIMUM USEFUL WORK SET
   ↓
BOUNDED PARALLEL IMPLEMENTATION
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
NEXT BASELINE
```

This operating model remains active until explicitly superseded by a documented repository decision.