# 16 — Current runtime status

This document is the canonical human-readable ledger for the **current Hermes Vault runtime state**. It summarizes verified live evidence; it does not contain secret material.

## Current checkpoint

```text
VAULT_CORE_OPERATIONAL=VERIFIED
VAULT_CORE_OPERATIONAL_RUNTIME_PASS=VERIFIED
FIRST_CONSUMER_BOOTSTRAP=NOT_RUN
UNSEALED_READY=false
JIT_SELF_REVOKE_REVALIDATION=PENDING
```

**Accepted runtime implementation SHA:** `e4659af02898513eeebed6f68ca37cf7485ac979`  
**Exact-SHA main CI:** `32537626664` — `SUCCESS`  
**Live evidence:** [`evidence/2026-08-22-vault-core-operational.md`](evidence/2026-08-22-vault-core-operational.md)

## Runtime baseline

| Control | Verified state |
|---|---|
| Vault | `1.21.4`, exact-digest pinned |
| Storage | single-node Integrated Storage / Raft |
| Initialization | initialized |
| Seal | Shamir 3/2, currently unsealed |
| Auto-unseal | disabled by decision |
| TLS | strict, loopback/admin + private consumer topology |
| Docker lifecycle | `restart: unless-stopped` |
| Health | healthy, active/non-standby |

## Network and trust boundaries

| Boundary | Current state |
|---|---|
| Host admin endpoint | `https://127.0.0.1:8200` only |
| Consumer plane | `hermes-security-plane`, Docker `internal: true` |
| Consumer alias | `hermes-vault` |
| Local admin network | `hermes-vault-admin` |
| Cluster port | not published on host |
| Vault UI | disabled |
| Runtime user/capabilities | non-root runtime, capabilities dropped |

The service is designed to remain running continuously on HermesJarvas. Docker starts with the host and the Vault container uses `restart: unless-stopped`. A host reboot starts the container automatically, but **does not bypass Shamir**: after a reboot requiring reseal recovery, operator quorum 2/3 remains HITL.

## Administration

- ADR-022: `VERIFIED_ADR022_LIVE_ACCEPTED`.
- File audit: PASS before administrative bootstrap.
- Certificate-authenticated JIT administration: VERIFIED.
- Initial root token retirement: VERIFIED.
- Persistent root token: prohibited.
- Administrative tokens: short-lived, class-scoped, no default policy.

`JIT_SELF_REVOKE_REVALIDATION=PENDING`: operator-side cleanup attempts exposed a live/runtime drift candidate for administrative JIT self-revoke. The repository policy grants `auth/token/revoke-self`; live policy refresh/revalidation is required before this invariant is closed again.

## Recovery

- ADR-023: `VERIFIED_ADR023_LIVE_ACCEPTED`.
- `RESTORE_DRILL_PASS`: VERIFIED.
- Restore environment: disposable, exact image, `network=none`, zero published ports.
- Original production Shamir quorum was used only by the operator/HITL after snapshot restore.
- Positive synthetic read, forbidden-path deny, Transit metadata read and token self-revoke passed.
- Restore runtime and synthetic private key were removed during teardown.

## Scheduled snapshots

```text
SCHEDULED_SNAPSHOT_PASS=VERIFIED
schedule=02:30 local daily
retention=14
identity=vault-backup
```

The backup identity can read the Raft snapshot endpoint and revoke only its own token. Its SecretID and the snapshot encryption passphrase are held as encrypted user-scoped credentials outside Git. The oneshot loader decrypts them only inside a systemd-managed runtime directory and removes all runtime credential material on exit.

The first live scheduled snapshot produced plaintext and encrypted artefacts with independent SHA-256 verification and mode `0600`. No secret values are written to service logs or repository evidence.

## Continuous assurance

`hermes-vault-readiness.timer` is enabled and active. The read-only readiness check proves the expected image/topology, restart policy, strict-TLS health and sealed state without using a Vault token.

Expected operational states:

| State | Meaning |
|---|---|
| `VAULT_24X7_READY` | container/topology correct and Vault initialized + unsealed |
| `SEALED_NEEDS_QUORUM` | service started but Shamir operator quorum is required |
| `FAIL` | topology, TLS, container or health invariant is not satisfied |

No autonomous process may unseal Vault, reconstruct Shamir material or generate a replacement root token.

## Consumer boundary

The core service is operational, but **consumer production enablement is separate**. HSL is the first planned consumer with:

- Transit mount `hsl-transit/`;
- key `hsl-signing`;
- AppRole `hsl-signer`;
- legacy HSL signing path retained verify-only during controlled cutover.

`FIRST_CONSUMER_BOOTSTRAP=NOT_RUN` means the consumer acceptance gate has not yet been completed. Therefore `UNSEALED_READY=false` remains the canonical cross-project promotion state even though `VAULT_CORE_OPERATIONAL=VERIFIED`.

## Truth rule

`NOT_RUN` is never equivalent to PASS. Runtime evidence, repository state and cross-project promotion state must remain separately identifiable.
