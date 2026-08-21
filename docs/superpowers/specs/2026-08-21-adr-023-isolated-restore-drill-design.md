# ADR-023 — Isolated Raft Restore Drill Design

**Status:** Approved design — Option A selected by owner on 2026-08-21.

## 1. Objective

Prove that a live Hermes Vault Raft snapshot can be restored and accepted without ever restoring into, joining, or exposing the production Vault runtime.

ADR-023 implements ADR-012 with a disposable Vault container that is fully network-isolated, uses the exact pinned Vault image, publishes zero ports, and is destroyed after acceptance.

The drill is a recovery proof only. It does not promote production readiness by itself and does not bootstrap the first consumer.

## 2. Hard security boundaries

- The production container `vault-vault-1` is never stopped, restored, reinitialized, or attached to the drill.
- The restore container uses Docker `--network none` and publishes no ports.
- No Docker socket, production Raft volume, production audit volume, or Hermes security network is mounted into the restore container.
- The exact Vault image is `hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569`.
- Restore storage and audit paths are disposable run-scoped host directories owned by the operator UID/GID.
- The container is read-only apart from explicit restore data/audit mounts and a bounded `/tmp` tmpfs.
- Capabilities are dropped, `no-new-privileges` is set, and CPU/memory/PID quotas are applied.
- `snapshot-force` is never granted to a production JIT policy.
## 3. Production-side recovery capability

A new JIT class `vault-admin-recovery` exists only to prepare a recovery test and capture a snapshot.

It may:
- read `sys/storage/raft/snapshot` to capture a Raft snapshot;
- manage only the reserved mounts `restore-acceptance-kv` and `restore-acceptance-transit`;
- manage only the policy `restore-acceptance-test`;
- manage only the cert role `restore-acceptance`;
- write/read/delete only synthetic fixtures under the reserved acceptance paths;
- revoke its own token.

It may not:
- write `sys/storage/raft/snapshot`;
- access `sys/storage/raft/snapshot-force`;
- restore production storage;
- access any consumer path;
- manage arbitrary policies, mounts, auth roles, tokens, audit devices, or identities.

For a fresh deployment, `vault-admin-recovery` is included in the canonical JIT role allowlist. For the already-running Vault, promotion is a separate HITL action performed with a short-lived JIT token carrying only `vault-admin-policy` and `vault-admin-token`.

## 4. Synthetic acceptance fixtures

Before the snapshot, an operator-authorized recovery JIT run creates temporary fixtures in the live Vault:

1. a KV v2 mount `restore-acceptance-kv/`;
2. a deterministic synthetic marker at `restore-acceptance-kv/data/primary`;
3. a separate forbidden marker at `restore-acceptance-kv/data/forbidden`;
4. a Transit mount `restore-acceptance-transit/` and key `restore-acceptance`;
5. policy `restore-acceptance-test`, allowing primary read and Transit key metadata read while explicitly denying the forbidden path;
6. cert role `restore-acceptance` bound to a disposable, synthetic ClientAuth certificate.

The synthetic certificate/key pair is generated into the git-ignored recovery run directory. It is test-only, never used by the production administrative identity, and its private key is deleted on successful drill teardown.

The snapshot is captured only after all fixtures exist. Immediately after snapshot capture, the fixtures are removed from the live Vault. Cleanup failure is fail-closed and blocks the drill from being considered prepared.
## 5. Snapshot capture

The host Vault CLI is not a dependency. `snapshot.sh` uses the Vault HTTPS API over the canonical strict-TLS loopback endpoint and reads the operator-provided `VAULT_TOKEN` only from process environment memory.

The snapshot is written mode `0600`, checksummed, accompanied by non-secret metadata, and encrypted with AES-256-CBC/PBKDF2 using an operator-supplied out-of-band passphrase. Live drill preparation refuses to proceed without the encrypted independent copy.

## 6. Disposable restore runtime

`restore-drill.sh --start "$RUN_DIR"` verifies the snapshot checksum and starts one uniquely named container labelled for that run.

The container:
- has `NetworkMode=none`;
- has no published or exposed host ports;
- has no connection to `hermes-security-plane` or `hermes-vault-admin`;
- runs with the operator UID/GID, all Linux capabilities dropped, read-only root filesystem and `no-new-privileges`;
- mounts only run-scoped configuration/TLS/acceptance assets, the snapshot read-only, and disposable data/audit directories;
- uses an ephemeral TLS CA/server certificate valid only for loopback inside the container;
- uses bounded memory, CPU, PID and tmpfs resources.

The runtime starts uninitialized. No init, temporary root, Shamir share, restore or original-share unseal is automated.
## 7. HITL restore sequence

The operator performs the following only inside the labelled disposable container:

1. initialize a temporary Shamir 3/2 cluster and keep its temporary shares/root out-of-band;
2. unseal the temporary cluster with two temporary shares;
3. use the temporary root only to run `vault operator raft snapshot restore -force /vault/restore/input.snapshot`;
4. clear the temporary root from the shell;
5. after restore, enter two original Shamir shares interactively to unseal the restored snapshot.

Neither temporary nor original recovery material is recorded in Git, logs, Context Core, run state, command arguments or assistant-visible tools.

## 8. Post-restore acceptance

After the restored instance is unsealed, `restore-drill.sh --accept "$RUN_DIR"` authenticates with the synthetic disposable certificate preserved in the snapshot and proves:

- certificate authentication succeeds;
- the synthetic primary KV marker is readable;
- the forbidden KV path returns access denied;
- the synthetic Transit key metadata is readable;
- the acceptance token can self-revoke;
- production networks remain absent and no ports have appeared.

Only PASS/FAIL metadata is persisted. Synthetic secret values and token values are never written to evidence.
## 9. Teardown and retained evidence

On successful acceptance, teardown removes only resources carrying the exact run label and only disposable paths inside the run directory. It deletes synthetic client/server private keys and restored Raft/audit data.

The retained backup set is limited to:
- the mode-0600 Raft snapshot;
- its checksum/non-secret metadata;
- its independently encrypted copy;
- public synthetic certificate if useful for evidence;
- a sanitized acceptance evidence JSON containing hashes, image digest, isolation assertions and PASS/FAIL results.

Teardown refuses to remove a container whose labels do not match the requested run ID.

## 10. Failure behavior

Any checksum mismatch, unexpected network attachment, published port, image mismatch, fixture cleanup failure, authentication failure, policy overreach, restore failure or acceptance failure is fail-closed.

A failed drill does not alter `UNSEALED_READY`. The disposable environment may be retained only long enough for operator diagnosis; no production workaround is permitted.

## 11. Acceptance gate

`RESTORE_DRILL_PASS` requires all of the following in the same run:
- live snapshot capture with checksum and encrypted copy;
- live fixture cleanup PASS;
- isolated runtime attestation PASS;
- operator-confirmed temporary init/force-restore/original-share unseal sequence;
- synthetic cert authentication PASS;
- positive KV read PASS;
- cross-path deny PASS;
- Transit metadata PASS;
- acceptance-token self-revoke PASS;
- teardown PASS.

Only after this gate may the project proceed to first-consumer bootstrap. `UNSEALED_READY` remains dependent on the remaining canonical consumer gates.