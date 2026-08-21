# ADR-023 Isolated Restore Drill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an operator-gated, fully isolated Raft restore drill that proves snapshot recovery without exposing or mutating the production Vault during restore.

**Architecture:** Production-side JIT recovery can stage only reserved synthetic fixtures and read a Raft snapshot. Restore occurs only in a labelled `--network none` disposable container using the exact pinned image; temporary init/root and original Shamir-share unseal remain HITL. Acceptance uses a synthetic disposable cert identity embedded in the snapshot, then tears down all disposable secret material.

**Tech Stack:** Bash, Python 3 stdlib HTTPS, Docker 26, HashiCorp Vault 1.21.4 exact digest, OpenSSL, pytest.

**Spec:** `docs/superpowers/specs/2026-08-21-adr-023-isolated-restore-drill-design.md`

## Global Constraints

- Never handle or persist original Shamir shares, root/Vault tokens, SecretID, operator certificate private key or passphrase.
- Production JIT recovery must never receive `sys/storage/raft/snapshot-force`.
- Restore runtime must use Docker `--network none`, zero published ports and no production volumes/networks.
- Exact Vault image digest must remain identical to the canonical production image.
- All run-time recovery artifacts remain under gitignored `backups/`; private synthetic keys are deleted on teardown.
- `RESTORE_DRILL_PASS` is impossible until the HITL force-restore and original-share unseal execute successfully.
- Do not claim `UNSEALED_READY` from repository tests or synthetic/offline tests.

---
### Task 1: ADR-023 recovery JIT boundary

**Files:**
- Modify: `.gitignore`
- Modify: `docs/13-security-decisions.md`
- Create: `policies/admin/vault-admin-recovery.hcl`
- Create: `policies/recovery/restore-acceptance-test.hcl`
- Modify: `deployments/vault/scripts/bootstrap-jit-admin.sh`
- Create: `deployments/vault/scripts/promote-recovery-admin.sh`
- Create: `tests/recovery/test_adr023_recovery_policy.py`

**Interfaces:**
- Produces JIT class `vault-admin-recovery` and exact synthetic acceptance policy.
- Promotion consumes an operator JIT token already carrying `vault-admin-policy,vault-admin-token`.

- [ ] **Step 1: RED** — assert exact allowed paths, no wildcard production access, no `snapshot-force`, `revoke-self`, bootstrap allowlist inclusion, promotion HITL guard and `.worktrees/` ignore.
- [ ] **Step 2: Verify RED** — run `pytest tests/recovery/test_adr023_recovery_policy.py -q`; expected failure because recovery policy/scripts/ADR do not exist.
- [ ] **Step 3: GREEN** — implement only the exact paths from ADR-023 and add `VAULT_RECOVERY_PROMOTION_OPERATOR_ACK=yes` guard.
- [ ] **Step 4: Verify GREEN** — targeted recovery-policy tests PASS; existing ADR-022 tests remain PASS.
- [ ] **Step 5: Commit** — `feat: add ADR-023 recovery JIT boundary`.### Task 2: Strict-TLS snapshot capture without host Vault CLI

**Files:**
- Modify: `deployments/vault/scripts/snapshot.sh`
- Create: `tests/recovery/test_snapshot_live_capture.py`

**Interfaces:**
- Consumes `VAULT_ADDR`, `VAULT_CACERT`, `VAULT_TOKEN`, `VAULT_SNAPSHOT_PASSPHRASE`, optional `VAULT_BACKUP_DIR`.
- Produces one `.snapshot`, `.meta.json`, `.enc` and checksums in a mode-0700 backup directory.

- [ ] **Step 1: RED** — require strict TLS, canonical loopback, Python stdlib HTTPS `GET /v1/sys/storage/raft/snapshot`, no host `vault` CLI, token absent from argv/output, 0600 snapshot, SHA-256 metadata and mandatory encrypted copy.
- [ ] **Step 2: Verify RED** — run `pytest tests/recovery/test_snapshot_live_capture.py -q`; expected failure against current CLI-based optional-encryption script.
- [ ] **Step 3: GREEN** — stream the binary response with Python `urllib.request`/`ssl`, atomically rename the completed snapshot, checksum it, emit sanitized metadata, encrypt with `openssl enc -aes-256-cbc -salt -pbkdf2`, then checksum the encrypted copy.
- [ ] **Step 4: Verify GREEN** — targeted tests PASS and `bash deployments/vault/scripts/snapshot.sh` without HITL env exits non-zero without creating backup artifacts.
- [ ] **Step 5: Commit** — `feat: harden live Raft snapshot capture`.
### Task 3: Synthetic live acceptance staging

**Files:**
- Create: `deployments/vault/scripts/prepare-restore-acceptance.sh`
- Create: `tests/recovery/test_restore_acceptance_staging.py`

**Interfaces:**
- Consumes a `vault-admin-recovery` JIT token plus snapshot passphrase in the operator shell.
- Produces a gitignored run directory containing snapshot set and disposable acceptance cert/key.

- [ ] **Step 1: RED** — assert exact reserved mounts/paths, disposable ClientAuth cert generation, snapshot-after-fixtures ordering, cleanup trap, no operator private-key use and no fixture values in output.
- [ ] **Step 2: Verify RED** — run `pytest tests/recovery/test_restore_acceptance_staging.py -q`; expected failure because staging script does not exist.
- [ ] **Step 3: GREEN** — generate synthetic cert/key; enable reserved KV/Transit mounts; write deterministic synthetic markers, acceptance policy and cert role; call hardened snapshot capture; remove live fixtures before exit.
- [ ] **Step 4: Verify GREEN** — targeted tests PASS; dry invocation without operator ack/token fails closed before mutation.
- [ ] **Step 5: Commit** — `feat: stage synthetic restore acceptance fixtures`.

### Task 4: Disposable network-none restore runtime

**Files:**
- Modify: `deployments/vault/scripts/restore-drill.sh`
- Create: `docs/runbooks/restore-drill.md`
- Modify: `tests/recovery/test_restore_drill.py`
- Create: `tests/recovery/test_restore_isolation.py`
**Interfaces:**
- `--offline-selftest` remains data-free and executable in CI/local gates.
- `--start "$RUN_DIR"` creates the isolated runtime and state/evidence skeleton.
- `--status "$RUN_DIR"` reports safe container/isolation/health metadata only.
- `--accept "$RUN_DIR"` runs synthetic cert/KV/deny/Transit/self-revoke acceptance after operator unseal.
- `--teardown "$RUN_DIR"` removes only exact labelled disposable resources and synthetic private keys.

- [ ] **Step 1: RED** — replace the old `--smoke` NOT_RUN assertion with tests requiring a real isolated lifecycle while still refusing any unattended init/unseal/restore.
- [ ] **Step 2: Verify RED** — run `pytest tests/recovery/test_restore_drill.py tests/recovery/test_restore_isolation.py -q`; expected failure because live lifecycle is absent.
- [ ] **Step 3: GREEN** — implement exact-digest `docker run --network none`, no `-p`, hardened flags/quotas, loopback-only ephemeral TLS/config, run labels, snapshot checksum preflight and safe state JSON.
- [ ] **Step 4: GREEN acceptance** — implement synthetic certificate login inside the isolated container, primary read, forbidden deny, Transit metadata read, self-revoke and sanitized evidence JSON.
- [ ] **Step 5: HITL runbook** — document temporary init/unseal, temporary-root `snapshot restore -force`, root clear, original 2/3 unseal, acceptance and teardown. No secret values/locations in the runbook.
- [ ] **Step 6: Verify GREEN** — offline selftest + recovery/isolation tests PASS; `--start` can be exercised only against synthetic test assets, never a production snapshot unattended.
- [ ] **Step 7: Commit** — `feat: implement isolated restore drill harness`.

### Task 5: Hardening, evidence and delivery gates

**Files:**
- Modify: `docs/specs/2026-08-18-hermes-shared-vault-service-design.md`
- Modify: `docs/09-bootstrap-recovery.md`
- Modify: `docs/12-implementation-roadmap.md`
- Create: `tests/recovery/test_adr023_docs.py`

- [ ] **Step 1: RED/GREEN** — require docs to distinguish repository-ready, live HITL pending and `RESTORE_DRILL_PASS`; forbid auto-promotion to `UNSEALED_READY`.
- [ ] **Step 2: Run targeted suites** — recovery + ADR-022/023 + lifecycle/evidence.- [ ] **Step 3: Full verification** — run `pytest -q -m 'not hitl'`, `bash scripts/ci/run-gates.sh --dry`, `bash scripts/ci/run-gates.sh --scan-only`, `docker compose ... config`, `git diff --check`.
- [ ] **Step 4: Commit** — `docs: align recovery state with ADR-023`.
- [ ] **Step 5: Push/PR** — push exact head SHA, create PR, require all fast-gates GREEN.
- [ ] **Step 6: Merge exact head** — merge only if PR head SHA equals locally verified SHA.
- [ ] **Step 7: Post-merge verification** — fast-forward canonical `main`, confirm CI success and production Vault remains healthy/unsealed/audit-active.
- [ ] **Step 8: Context Core** — record `ADR023_REPO_READY_LIVE_HITL_PENDING`; do not record secrets or custody locations.
- [ ] **Step 9: Stop at HITL** — present only the operator sequence required to promote recovery JIT, stage snapshot fixtures and execute temporary init/restore/original-share unseal.

## Completion Definition

Repository implementation is complete when all non-HITL tests and gates pass, PR is merged by exact SHA, production runtime remains unchanged/healthy, and the next state is explicitly `ADR023_REPO_READY_LIVE_HITL_PENDING`.

Live ADR-023 acceptance is complete only after one isolated run produces `RESTORE_DRILL_PASS` with the HITL sequence and teardown verified. Until then, `UNSEALED_READY=false`.