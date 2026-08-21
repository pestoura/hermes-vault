# Scheduled encrypted Raft snapshot

**Status:** `SCHEDULED_SNAPSHOT_PASS` VERIFIED on 2026-08-22.  
**Scope:** automated local Raft snapshot capture for the shared Hermes Vault core.

## Operating model

- user timer: `hermes-vault-snapshot.timer`;
- schedule: daily at `02:30` local time;
- retention: `14` local generations;
- workload identity: AppRole `vault-backup`;
- Vault token TTL: five minutes;
- token permissions: Raft snapshot read + self-revoke only;
- no default policy;
- encrypted credential delivery via `systemd-creds`;
- plaintext runtime credential files exist only inside a systemd-managed `RuntimeDirectory` and are removed after the oneshot service exits.

The scheduled path never uses root, Shamir material or an administrative JIT token.

## Files

- service: `deployments/vault/systemd/hermes-vault-snapshot.service`;
- timer: `deployments/vault/systemd/hermes-vault-snapshot.timer`;
- credential loader: `deployments/vault/scripts/run-scheduled-snapshot.sh`;
- snapshot implementation: `deployments/vault/scripts/scheduled-snapshot.py`;
- workload provisioning: `deployments/vault/scripts/enable-backup-snapshot.sh`;
- policy: `policies/backup/vault-backup-snapshot.hcl`.

## Expected success evidence

A successful run emits only sanitized status:

```text
SCHEDULED_SNAPSHOT_PASS captured=<UTC timestamp> sha256=<digest> encrypted_sha256=<digest>
```

Acceptance requires all of the following:

1. AppRole login succeeds with only `vault-backup-snapshot` policy.
2. Raft snapshot capture succeeds over strict loopback TLS.
3. plaintext snapshot is mode `0600`.
4. encrypted snapshot is mode `0600`.
5. plaintext SHA-256 verifies.
6. encrypted SHA-256 verifies.
7. metadata file contains no secret value.
8. token self-revoke succeeds.
9. runtime credentials are removed.
10. retention completes without deleting the newest generation.

The service fails closed if authentication, snapshot capture, encryption or self-revoke fails.

## Operator checks

Safe metadata-only checks:

```bash
systemctl --user status hermes-vault-snapshot.timer
systemctl --user status hermes-vault-snapshot.service
journalctl --user -u hermes-vault-snapshot.service -n 20 --no-pager
```

Checksums may be verified locally without exposing snapshot contents. Do not print, decode or upload snapshot bytes to chat/logging systems.

## Credential rotation

The `vault-backup` SecretID is bounded by use count and TTL. Rotation is an operator/HITL action. Generate a new SecretID only through the approved auth-admin path and encrypt it directly with `systemd-creds`; never store it in Git, shell history, `.env`, evidence or model context.

The snapshot encryption passphrase is also operator-custodied. Rotation requires an explicit retention/recovery decision because existing encrypted snapshots remain dependent on the previous passphrase.

## Recovery relationship

A scheduled snapshot is **not** considered a valid recovery capability merely because files exist. Recovery acceptance is independently governed by ADR-023 and [`restore-drill.md`](restore-drill.md). The live isolated restore drill is already `RESTORE_DRILL_PASS=VERIFIED`; future periodic drills should use a retained scheduled snapshot without weakening the Shamir/HITL boundary.
