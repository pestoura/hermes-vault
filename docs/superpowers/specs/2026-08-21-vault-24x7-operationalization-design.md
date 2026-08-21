# Hermes Vault 24x7 Operationalization Design

- **Status:** Approved implementation direction — owner requested completion before returning to Hermes Security Labs.
- **Date:** 2026-08-21
- **Scope:** shared `hermes-vault` service on HermesJarvas.

## Goal

Make the existing shared Vault a persistent 24x7 Jarvas service rather than a manually started acceptance runtime, without weakening the approved Shamir 3/2, TLS, network, JIT or secret-zero boundaries.

## Current verified baseline

- Vault `1.21.4` exact digest, Docker, single-node Raft.
- Strict TLS, `127.0.0.1:8200` admin and internal `hermes-security-plane` consumer path.
- Production runtime initialized, unsealed and healthy.
- Audit/JIT/root-retirement ADR-022 accepted.
- Isolated Raft restore ADR-023 accepted with `RESTORE_DRILL_PASS`.
- Docker daemon is enabled at host boot.
- Current container restart policy is `no`; this is not 24x7-complete.
## Runtime permanence

The Compose service uses `restart: unless-stopped`. The existing live container receives the same restart policy with `docker update`, avoiding a restart/reseal merely to apply the policy.

Host Docker remains the lifecycle owner. No second systemd service starts/stops Vault and no competing supervisor is introduced.

After a host or Docker restart, the container starts automatically but Vault is expected to return **sealed** because auto-unseal remains prohibited by the MVP decision. This is a controlled state, not an automation failure:

```text
container auto-start
  -> TLS listener / Raft available
  -> SEALED_NEEDS_QUORUM
  -> operator/custodians perform Shamir 2/3 HITL
  -> RUNTIME_UNSEALED_HEALTHY
```

Automation must never receive or enter Shamir shares.

## Readiness and assurance

A secret-free readiness script validates Docker/container/image/restart/network/volume/TLS state and queries only the unauthenticated Vault health endpoint over strict TLS. It emits sanitized state markers only.
The user systemd manager is enabled with lingering on HermesJarvas. A user timer may run the readiness check periodically and at boot without requiring sudo. The timer never mutates Vault and never unseals it.

Readiness states are operational observations only and do not overwrite the canonical lifecycle state machine:

- `VAULT_24X7_READY` — running, exact image, restart policy, expected networks/volumes and strict-TLS health 200.
- `VAULT_24X7_SEALED_NEEDS_QUORUM` — container is running but Vault health reports sealed; operator HITL required.
- any topology/image/TLS/storage mismatch — fail closed.

## Snapshot operation

Scheduled Raft snapshots remain mandatory operational recovery hygiene. The scheduler must not use root, JIT administration or a reusable token embedded in repository configuration.

A dedicated `vault-backup` workload identity is limited to `read` on `sys/storage/raft/snapshot` plus token self-revoke. The scheduler exchanges its out-of-band bootstrap credential for a short-lived Vault token in memory, captures the snapshot over strict loopback TLS, then revokes/forgets the token.

The bootstrap credential itself remains outside Git, chat, evidence and model context. Provisioning or rotating that secret-zero is HITL. The implementation may validate its presence/permissions but never print or inspect its value.
### Backup identity contract

`vault-backup` AppRole is provisioned by one bounded JIT change using exactly `vault-admin-policy` + `vault-admin-auth`.

- policy: `vault-backup-snapshot`;
- allowed Vault paths: `sys/storage/raft/snapshot` read, `auth/token/revoke-self` update;
- AppRole token: no default policy, TTL/max TTL 5 minutes, two uses, non-renewable service token;
- SecretID: maximum 40 uses and 35-day TTL, rotated before expiry;
- RoleID is non-secret configuration;
- SecretID and snapshot encryption passphrase are stored as **user-scoped encrypted systemd credentials**, not plaintext files or environment files.

The daily snapshot service receives decrypted credentials only via `$CREDENTIALS_DIRECTORY`, performs AppRole login and snapshot capture, encrypts the snapshot, self-revokes the short-lived token, applies retention, and emits only metadata/checksums.

## Completion boundary

`VAULT_CORE_OPERATIONAL` may be declared when runtime permanence, readiness monitoring and scheduled backup are live and verified alongside the already accepted TLS/Raft/audit/JIT/restore controls.

This state does **not** claim `UNSEALED_READY`, first-consumer acceptance, HSL cutover, Credential Broker completion, PKI rollout or broad secret migration. Those remain separate consumer/platform phases.
