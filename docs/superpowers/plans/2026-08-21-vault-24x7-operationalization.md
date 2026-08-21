# Hermes Vault 24x7 Operationalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans`; steps are tracked as TDD RED -> minimal GREEN -> hardening -> exact-SHA verification.

**Goal:** make the existing Hermes shared Vault a persistent 24x7 Jarvas service with secret-free readiness monitoring and scheduled encrypted Raft snapshots.

**Architecture:** Docker remains the sole runtime lifecycle owner with `restart: unless-stopped`. User-systemd timers provide read-only readiness assurance and scheduled backup. Shamir 3/2 remains manual after reboot; no auto-unseal is introduced.

**Tech Stack:** Docker Compose, HashiCorp Vault 1.21.4, Bash/Python stdlib, systemd 257 user services, systemd-creds, OpenSSL.

**Spec:** `docs/superpowers/specs/2026-08-21-vault-24x7-operationalization-design.md`

## Global constraints

- No secret value in Git, logs, evidence, argv or chat.
- Never automate Shamir unseal, root, TLS private-key custody or production sign-off.
- Keep `127.0.0.1:8200`, `hermes-security-plane`, `hermes-vault-admin` and exact image digest unchanged.
- Do not restart the live Vault merely to apply restart policy; use `docker update` after merge.
- `VAULT_CORE_OPERATIONAL` is distinct from `UNSEALED_READY` and first-consumer acceptance.
## Task 1 — Persistent runtime + readiness

**Files:** `deployments/vault/docker-compose.yml`, `deployments/vault/scripts/operational-readiness.sh`, `deployments/vault/systemd/hermes-vault-readiness.{service,timer}`, baseline tests.

- [ ] RED: require `restart: unless-stopped`, exact non-secret readiness checks and systemd timer contract.
- [ ] GREEN: implement compose restart policy and read-only readiness script using strict TLS health endpoint.
- [ ] GREEN: add user timer with boot + 5-minute checks; no Vault mutation.
- [ ] Verify targeted tests, `bash -n`, Compose config and secret scan.

## Task 2 — Dedicated backup workload identity

**Files:** `policies/backup/vault-backup-snapshot.hcl`, `deployments/vault/scripts/enable-backup-snapshot.sh`, admin/backup tests.

- [ ] RED: assert exact snapshot-read/self-revoke policy and bounded AppRole settings.
- [ ] GREEN: provision policy + `vault-backup` AppRole only; script requires JIT token and operator ack, emits RoleID only, never SecretID.
- [ ] Verify targeted policy/auth tests and no secret-shaped literals.

## Task 3 — Scheduled encrypted snapshot

**Files:** `deployments/vault/scripts/scheduled-snapshot.py`, `deployments/vault/systemd/hermes-vault-snapshot.{service,timer}`, recovery tests.

- [ ] RED: require systemd encrypted credentials, AppRole login, strict TLS snapshot, encryption, checksum, retention and token self-revoke.
- [ ] GREEN: implement daily 02:30 local snapshot with 14-run retention and no secret output.
- [ ] Verify offline failure is fail-closed when credentials/config are missing.
## Task 4 — Integration, live activation and evidence

**Files:** operational runbook/current-status docs and tests.

- [ ] Run full non-HITL suite, fast gates, secret scan, Compose validation and diff-check.
- [ ] Commit, PR, CI exact-SHA, merge and post-merge verification.
- [ ] Apply `docker update --restart unless-stopped vault-vault-1` without restarting the container.
- [ ] Link/enable readiness timer from canonical `main` and prove `VAULT_24X7_READY`.
- [ ] HITL: operator provisions backup AppRole SecretID and encrypted systemd credentials without exposing values.
- [ ] Enable snapshot timer; run one scheduled snapshot; verify encrypted artifact/checksums/retention and short-lived token self-revoke.
- [ ] Record sanitized evidence and declare `VAULT_CORE_OPERATIONAL` only if every executed gate passes.

## Task 5 — Documentation and ecosystem reconciliation

- [ ] Replace stale blueprint-only README/docs state with verified runtime truth and diagrams/badges.
- [ ] Update `RESUME.md`, implementation checklist, operational status and runbooks without rewriting dated evidence history.
- [ ] Reconcile `pestoura/hermes-ecosystem-architecture` human docs + machine inventories to the same evidence baseline.
- [ ] Validate both repos, PR/CI/exact-SHA merge, then return to Hermes Security Labs.
