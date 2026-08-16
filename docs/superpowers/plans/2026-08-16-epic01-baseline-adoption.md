# EPIC-01 LAB_L1 Baseline Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt the already validated LAB_L1 Vault deployment from `pestoura/hermes-security-labs` by immutable provenance and add only the EPIC-01 gaps: audit persistence, manual Raft snapshots, backup least privilege and an isolated restore-drill contract.

**Architecture:** `hermes-vault` remains the Vault governance/operations source and does not fork the HSL deployment. A provenance manifest pins the upstream repository, exact commit and expected blob identities. A small Compose overlay adds only a named audit volume. Operator scripts configure the file audit device and save/inspect snapshots using a dedicated read-only backup policy. Restore is never automatic: the repository provides a fail-closed isolated-restore preflight/runbook, while the actual `snapshot restore -force` remains an explicit HITL operation against a separately initialized scratch Vault.

**Tech Stack:** JSON, Python 3.12 standard library/unittest, Bash, Docker Compose overlay, Vault CLI 1.21.4.

## Global Constraints

- Upstream deployment source is immutable: `pestoura/hermes-security-labs@c63fee752bfd28868da54eb9650943e2b504f659`, path `deployment/vault-lab-l1/`.
- Do not copy or fork upstream deployment files into `hermes-vault`.
- Vault target remains Community 1.21.4, single-node LAB_L1, Integrated Storage/Raft, mandatory TLS, Shamir 3/2.
- File audit device writes to `/vault/audit/audit.log` on a dedicated named volume, mode `0600`, `log_raw=false`.
- Snapshot save is supported with a dedicated policy limited to `read` on `sys/storage/raft/snapshot`; restore authority is not granted to that identity.
- Snapshot files are written outside the Raft volume and must be copied to an independent custody location.
- Restore is destructive and never automatic. No script may invoke `vault operator raft snapshot restore` unless an explicit isolated-scratch HITL gate is satisfied in a later live execution procedure.
- No Shamir share, root token, SecretID, wrapping token or Vault client token may enter Git, CI logs, issues or chat.
- EPIC-01 repository readiness must not claim `VAULT_HEALTH_PASS`, `VAULT_UNSEALED`, `AUDIT_PASS`, `SNAPSHOT_PASS` or `ROOT_REVOKED` without live evidence.

---

### Task 1: Immutable upstream adoption contract

**Files:**
- Create: `baseline/lab-l1-source.json`
- Create: `tools/validate_lab_l1_source.py`
- Create: `tests/test_lab_l1_baseline.py`

- [ ] Write RED tests requiring exact repository/commit/path and expected upstream blob SHA values for README, Compose, Vault HCL, bootstrap, verifier and signer/observer policies.
- [ ] Implement the manifest and local contract validator.
- [ ] Assert no mutable branch/tag is accepted as source authority.
- [ ] Run targeted tests to GREEN.

### Task 2: Audit persistence overlay and bootstrap contract

**Files:**
- Create: `baseline/lab-l1-audit.compose.yaml`
- Create: `operations/lab_l1_baseline.sh`
- Modify: `tests/test_lab_l1_baseline.py`

- [ ] Write RED tests requiring a dedicated named volume mounted only at `/vault/audit` and no host bind mount.
- [ ] Require `audit-enable` to use an explicit path, file backend, `/vault/audit/audit.log`, `mode=0600`, `format=json`, `log_raw=false`, bounded output and no secret argv.
- [ ] Implement idempotent `audit-status`/`audit-enable`; already-enabled exact configuration is accepted, divergent configuration fails closed.
- [ ] Run targeted tests to GREEN.

### Task 3: Least-privilege backup identity and snapshot commands

**Files:**
- Create: `baseline/policies/lab-l1-backup.hcl`
- Modify: `operations/lab_l1_baseline.sh`
- Modify: `tests/test_lab_l1_baseline.py`

- [ ] Write RED tests requiring exactly `read` on `sys/storage/raft/snapshot` and no update/delete/sudo/wildcard capability.
- [ ] Add `snapshot-save OUTPUT.snap` with destination preflight, `umask 077`, atomic temporary path, Vault CLI save, local `snapshot inspect`, SHA-256 sidecar and final mode `0600`.
- [ ] Add `snapshot-inspect SNAPSHOT.snap` read-only verification.
- [ ] Reject snapshot destinations under the Raft/audit volumes or repository tree.
- [ ] Run targeted tests to GREEN.

### Task 4: Isolated restore-drill guardrail

**Files:**
- Create: `operations/restore_drill.sh`
- Create: `docs/17-lab-l1-baseline-recovery.md`
- Modify: `tests/test_lab_l1_baseline.py`

- [ ] Write RED tests proving default restore execution is blocked and production/default LAB_L1 addresses are refused.
- [ ] Implement `plan` and `preflight` only; these verify a snapshot with `vault operator raft snapshot inspect`, require `HERMES_VAULT_RESTORE_SCOPE=ISOLATED_SCRATCH`, require an explicitly different scratch `VAULT_ADDR`, and emit no credentials.
- [ ] Do not implement automatic force restore in this repository slice; document the later HITL command and prerequisites from official Vault guidance.
- [ ] Run targeted tests to GREEN.

### Task 5: Repository acceptance and stacked PR

**Files:**
- Modify: `IMPLEMENTATION-CHECKLIST.md`

- [ ] Run the full local suite inherited from EPIC-00 plus EPIC-01 tests and compile checks.
- [ ] Open a stacked PR with base `epic-00/discovery-prerequisites`, linked to #3.
- [ ] Record hosted CI as `BLOCKED_EXTERNAL_BILLING` if GitHub still refuses to start runners; never call that PASS.
- [ ] Do not merge before parent PR #14 and an independent exact-head CI gate are green.
- [ ] Keep #3 open for live Vault health/unseal/audit/snapshot/root evidence and the isolated restore drill.