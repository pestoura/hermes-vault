# ADR-022 Certificate JIT Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the initial Vault root token with a human-custodied certificate-authenticated issuer that can mint short-lived, non-renewable JIT admin tokens after audit is enabled.

**Architecture:** Bootstrap remains operator/HITL. Root is used only to enable audit, install narrowly-scoped admin policy classes, enable `auth/cert`, register an operator certificate role, and create token role `hermes-vault-admin`. The certificate login receives only `vault-admin-issuer`; that policy may call only `auth/token/create/hermes-vault-admin`. JIT tokens are orphaned, non-renewable, no-default-policy, and hard-capped at 10 minutes.

**Tech Stack:** Vault Community 1.21.4, HCL ACL policies, Bash operator-only scripts, pytest static/runtime-contract tests.

**Spec:** `docs/specs/2026-08-18-hermes-shared-vault-service-design.md`, ADR-022 in `docs/13-security-decisions.md`.

## Global Constraints

- Never read, print, persist, transmit or accept Shamir shares, initial root token, SecretID, or private keys.
- Root operations, certificate private-key generation/custody, cert login and root revocation remain operator-only HITL.
- Audit MUST be enabled before installing or using the post-root JIT administrative path.
- Certificate identity receives issuer capability only; it is not itself an admin token.
- JIT admin token role: `orphan=true`, `renewable=false`, `token_no_default_policy=true`, `token_explicit_max_ttl=10m`.
- No `root` policy, wildcard `path "*"`, permanent admin token, or secret material in Git/Context Core/logs.

---

### Task 1: ADR, policy contracts and RED tests
**Files:** modify `docs/13-security-decisions.md`; create `tests/admin/test_adr022_jit_admin.py`; create policy files under `policies/admin/`.
- [ ] Write tests requiring ADR-022, issuer exact path, classed admin policies, no root/wildcard, and exact 10-minute token role constraints.
- [ ] Run targeted tests and confirm RED because implementation artefacts do not exist.
- [ ] Add minimal ADR-022 and policy artefacts to satisfy the static contract.
- [ ] Re-run targeted tests to GREEN and commit.

### Task 2: Audit-first cert-auth bootstrap
**Files:** create `deployments/vault/scripts/bootstrap-jit-admin.sh`; update `deployments/vault/scripts/bootstrap-checklist.sh`; test `tests/admin/test_adr022_jit_admin.py`.
- [ ] Add RED tests requiring HITL acknowledgement, preflight `vault audit list`, refusal if audit absent, cert auth enablement, certificate-role registration from a public PEM path, token role creation, and no private-key handling.
- [ ] Run targeted test and confirm RED.
- [ ] Implement idempotent operator-only bootstrap script; it consumes `VAULT_ADMIN_CERT_PEM` public certificate only and an already-present operator token through the operator shell.
- [ ] Re-run targeted test to GREEN and commit.

### Task 3: Independent non-root acceptance and revoke ordering
**Files:** create `docs/runbooks/jit-admin-bootstrap.md`; update `docs/runbooks/vault-bootstrap.md`; update tests.
- [ ] Add RED tests requiring order `audit -> JIT bootstrap -> non-root cert login/test -> revoke initial root`, and explicit `ROOT_REVOKED` only after successful independent JIT proof.
- [ ] Run targeted test and confirm RED.
- [ ] Implement runbook/state wording without executable root-token handling.
- [ ] Run targeted and full non-HITL suites, secret scan, Compose config and exact-SHA CI.
- [ ] Merge only if all gates PASS; post-merge verify runtime remains healthy/unsealed and STOP before any root-token operation.
