# ADR-023 — Isolated Raft restore drill

**Status:** repository harness only. A live restore remains `NOT_RUN` until the operator completes the HITL sequence below.

This runbook is for the disposable `network=none` Vault created by `restore-drill.sh`. It must never be applied to `vault-vault-1` or to a container attached to `hermes-security-plane` / `hermes-vault-admin`.

## Non-negotiable boundaries

- Disable shell tracing before any token/share step: `set +x`.
- Never paste or record Shamir shares, temporary root, Vault tokens, SecretID, private keys, passphrases or concrete custody locations.
- The assistant/automation may prepare, attest and tear down the disposable runtime; it does not enter recovery material.
- `snapshot-force` is used only inside the labelled disposable restore container.
- `RESTORE_DRILL_PASS` is impossible until original-share unseal, acceptance and teardown all pass.
- A failure never promotes `UNSEALED_READY` and never changes the production Vault.

## 1. Preconditions

Repository-side gates and ADR-022 live acceptance must be GREEN. The production Vault must remain healthy/unsealed/audit-active before and after the drill.

The recovery JIT class must already be promoted with `promote-recovery-admin.sh` using the operator's short-lived ADR-022 JIT path. A fresh `vault-admin-recovery` JIT token and the snapshot encryption passphrase remain only in the operator shell.
## 2. Stage synthetic fixtures and capture the live snapshot

Run from the canonical repository in the operator shell:

```bash
set +x
export VAULT_RESTORE_STAGE_OPERATOR_ACK=yes
bash deployments/vault/scripts/prepare-restore-acceptance.sh
unset VAULT_RESTORE_STAGE_OPERATOR_ACK
```

The script must finish with `ADR023_RESTORE_STAGE_PASS` and prints the non-secret run directory. It stages only the reserved synthetic KV/Transit/cert-policy fixtures, captures the encrypted/checksummed snapshot, removes all fixtures from production and self-revokes the recovery JIT.

Do not continue if staging or live-fixture cleanup fails.

## 3. Start and attest the disposable runtime

```bash
bash deployments/vault/scripts/restore-drill.sh --start "$RUN_DIR"
bash deployments/vault/scripts/restore-drill.sh --status "$RUN_DIR"
```

Required state before HITL: `STARTED_UNINITIALIZED`, `initialized=false`, `sealed=true`, `network=none`, zero published ports, exact pinned Vault image. `--start` never initializes, unseals or restores a snapshot.
## 4. HITL — temporary cluster and force restore

Derive the disposable container name from the run ID and enter it interactively. The operator keeps every value produced here out-of-band and does not copy it to chat/logs.

Inside the disposable container:

```bash
set +x
export VAULT_ADDR=https://127.0.0.1:8200
export VAULT_CACERT=/vault/certs/ca.pem
vault operator init -key-shares=3 -key-threshold=2
```

Preserve the **temporary** three shares and temporary root only for this drill, out-of-band. Unseal the temporary cluster with two temporary shares using interactive hidden input:

```bash
vault operator unseal
vault operator unseal
```

Load the temporary root into the shell with hidden input, perform the force restore, then immediately clear it:

```bash
read -rsp 'Temporary root token: ' VAULT_TOKEN; echo
export VAULT_TOKEN
vault operator raft snapshot restore -force /vault/restore/input.snapshot
unset VAULT_TOKEN
```

Do not reuse the temporary shares/root after the restore.
## 5. HITL — unseal the restored snapshot with original shares

After `snapshot restore -force`, the restored data is protected by the original Shamir seal. Two original shares are required because the canonical production quorum is 3/2.

Still inside the isolated container, with no Vault token in the shell:

```bash
unset VAULT_TOKEN
vault operator unseal
vault operator unseal
vault status
```

Each custodian enters their original share only at the hidden prompt. Continue only when status shows `initialized=true` and `sealed=false`.

Exit the container shell. Do not retain any temporary root/share material from the disposable initialization.

## 6. Acceptance and teardown

From the host operator shell:

```bash
bash deployments/vault/scripts/restore-drill.sh --status "$RUN_DIR"
bash deployments/vault/scripts/restore-drill.sh --accept "$RUN_DIR"
bash deployments/vault/scripts/restore-drill.sh --teardown "$RUN_DIR"
```

Acceptance must prove certificate login, primary synthetic KV read, forbidden-path deny, Transit metadata read, token self-revoke, `network=none` and zero ports. Teardown must remove the labelled container, restored Raft/audit runtime and synthetic private key.

Retained evidence may contain only checksums, image digest, public synthetic certificate and sanitized PASS/FAIL metadata. `RESTORE_DRILL_PASS` is recorded only after the complete sequence succeeds.