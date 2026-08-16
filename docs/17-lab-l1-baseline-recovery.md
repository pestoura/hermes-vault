# LAB_L1 baseline adoption, audit and recovery

## Status

Repository implementation for EPIC-01. This document prepares controlled execution but does not assert a live Vault deployment or any live gate.

## Immutable baseline

The LAB_L1 Vault deployment is not duplicated in this repository. The adopted source is pinned in `baseline/lab-l1-source.json` to:

```text
repository: pestoura/hermes-security-labs
commit: c63fee752bfd28868da54eb9650943e2b504f659
path: deployment/vault-lab-l1/
```

The manifest also pins the expected Git blob identities of the deployment README, Compose file, Vault HCL, bootstrap/verifier scripts and signer/observer policies.

## Audit extension

Compose the validated HSL deployment with `baseline/lab-l1-audit.compose.yaml`. The overlay adds only:

```text
named volume hermes-vault-lab-l1-audit -> /vault/audit
```

It does not change Vault networking, listener ports, Raft storage, TLS secrets or image identity.

During initial bootstrap, while the controlled bootstrap root credential is still active:

```bash
./operations/lab_l1_baseline.sh audit-status
./operations/lab_l1_baseline.sh audit-enable
```

Expected device:

```text
path: lab-l1-file/
type: file
file_path: /vault/audit/audit.log
mode: 0600
format: json
log_raw: false
hmac_accessor: true
elide_list_responses: true
```

The script is idempotent only for that exact configuration. A divergent device at the same path fails closed. The file audit backend does not rotate logs itself; host-side log rotation must be designed separately and must preserve the named-volume boundary.

## Backup identity

`baseline/policies/lab-l1-backup.hcl` grants only:

```hcl
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}
```

It intentionally has no restore/update/delete/sudo capability.

Bootstrap the bounded AppRole before revoking the initial root credential:

```bash
./operations/lab_l1_baseline.sh backup-role-configure
./operations/lab_l1_baseline.sh backup-role-id
./operations/lab_l1_baseline.sh backup-wrapped-secret-id
```

RoleID is a non-secret identifier. The response-wrapping token and unwrapped SecretID are credentials and must never be placed in Git, tickets, logs, evidence or chat.

## Snapshot save

Manual snapshots are the Community-edition backup mechanism for Integrated Storage/Raft. The snapshot must live outside the Vault Raft and audit volumes and should be copied to an independent custody location after validation.

Example host path outside the source repository:

```bash
mkdir -p "$HOME/.local/state/hermes-vault/snapshots"
chmod 700 "$HOME/.local/state/hermes-vault/snapshots"
./operations/lab_l1_baseline.sh snapshot-save \
  "$HOME/.local/state/hermes-vault/snapshots/lab-l1-$(date -u +%Y%m%dT%H%M%SZ).snap"
```

The operation:

1. uses `umask 077`;
2. writes into a same-filesystem temporary directory;
3. calls `vault operator raft snapshot save`;
4. validates the snapshot with `vault operator raft snapshot inspect`;
5. creates a SHA-256 sidecar;
6. moves the snapshot and sidecar to the final destination with mode `0600`.

Inspect later without restoring:

```bash
./operations/lab_l1_baseline.sh snapshot-inspect /absolute/path/lab-l1.snap
```

A `SNAPSHOT_PASS` gate needs live evidence of successful save, inspect, SHA-256 verification and independent custody. Repository presence alone is not enough.

## Isolated restore drill

A restore changes the entire Vault cluster state and is therefore destructive. It must never target the operational LAB_L1 instance as an automated test.

The restore drill uses a separately initialized scratch Vault with:

- independent Raft storage;
- independent audit storage;
- no production/LAB_L1 client network;
- no connection to the operational Vault peer or storage;
- an explicitly different `VAULT_ADDR`;
- operator access only through the controlled session.

Prepare and validate:

```bash
./operations/restore_drill.sh plan

export HERMES_VAULT_RESTORE_SCOPE=ISOLATED_SCRATCH
export HERMES_VAULT_RESTORE_NETWORK_ISOLATION_CONFIRMED=YES
export HERMES_VAULT_RESTORE_STORAGE_ISOLATED=YES
export VAULT_ADDR=https://<isolated-scratch-host>:<port>
export VAULT_CACERT=/secure/path/to/scratch-ca.pem

./operations/restore_drill.sh preflight /absolute/path/lab-l1.snap
```

`preflight` inspects the snapshot and proves the scratch Vault is online/unsealed. It **does not restore anything**.

## HITL destructive restore

Only after the preflight evidence has been reviewed and the operator explicitly authorizes the isolated destructive step may the operator perform the Vault-documented force restore against the scratch instance:

```bash
vault operator raft snapshot restore -force /absolute/path/lab-l1.snap
```

This command is intentionally absent from `operations/restore_drill.sh`. It is a Human-in-the-Loop (HITL) action.

After a force restore into reinitialized scratch storage, the original cluster unseal custody is required to unseal the restored state. Do not transmit those Shamir shares through Hermes, GitHub, CI, issues or chat.

## Restore acceptance

A restore drill is PASS only when sanitized evidence proves:

- scratch isolation before restore;
- snapshot SHA-256 integrity;
- successful snapshot inspection;
- explicit HITL authorization;
- restore performed only against scratch;
- restored Vault reaches expected initialized/unsealed state with the approved custody process;
- expected Transit/key/policy/audit metadata is present;
- production/LAB_L1 endpoint was not modified.

## EPIC-01 live gates

Repository readiness does not satisfy these gates:

```text
VAULT_HEALTH_PASS = NOT_RUN
VAULT_UNSEALED    = NOT_RUN
AUDIT_PASS        = NOT_RUN
SNAPSHOT_PASS     = NOT_RUN
ROOT_REVOKED      = NOT_RUN
```

They move only on sanitized live Jarvas evidence.
