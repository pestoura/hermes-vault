# Hermes Vault — VAULT_CORE_OPERATIONAL evidence

**Evidence date:** 2026-08-22 (Europe/Lisbon)  
**Scope:** shared Vault core runtime on HermesJarvas; no consumer cutover is claimed.  
**Runtime implementation SHA:** `e4659af02898513eeebed6f68ca37cf7485ac979`  
**Exact-SHA main CI:** run `32537626664` — `SUCCESS`.

## Verified runtime facts

- `vault-vault-1` is running and Docker health is `healthy`.
- Vault version is `1.21.4`, initialized and unsealed, Raft storage, active/non-standby.
- Runtime image remains exact-digest pinned by repository policy.
- Host publication is only `127.0.0.1:8200`; cluster port is not host-published.
- Docker restart policy is `restart=unless-stopped`.
- `hermes-security-plane` remains the private consumer network.
- `hermes-vault-admin` remains the local administration network.
- TLS verification is strict; no `VAULT_SKIP_VERIFY` is used.
- File audit remains enabled; audit contents were not inspected for this evidence.

`VAULT_24X7_READY` was observed from the secret-free readiness service.

## Scheduled snapshot proof

The first live scheduled snapshot run completed through the installed systemd service:

```text
SCHEDULED_SNAPSHOT_PASS
captured=20260821T233945Z
```

Verified properties:

- dedicated AppRole: `vault-backup`;
- token policy permits snapshot read and self-revoke only;
- AppRole login succeeded and its short-lived token self-revoked successfully;
- encrypted SecretID and snapshot passphrase remain outside Git and model context;
- plaintext snapshot mode: `0600`;
- encrypted snapshot mode: `0600`;
- metadata/checksum files mode: `0600`;
- plaintext checksum: PASS;
- encrypted checksum: PASS;
- encryption: AES-256-CBC with PBKDF2 and runtime credential delivery;
- retention setting: 14 local generations;
- zero runtime credential residue after the oneshot service completed.

## Recovery and assurance

- ADR-022 live acceptance remains VERIFIED: audit-first certificate JIT administration and initial-root retirement passed.
- ADR-023 live acceptance remains VERIFIED: `RESTORE_DRILL_PASS` completed with isolated `network=none` restore, original Shamir quorum HITL, positive/negative acceptance and teardown.
- `hermes-vault-readiness.timer` is enabled and active.
- `hermes-vault-snapshot.timer` is enabled and active; next scheduled run is daily at approximately 02:30 local time.
- production remained initialized, unsealed and healthy after the snapshot proof.

## Open revalidation

`JIT_SELF_REVOKE_REVALIDATION=PENDING`.

Two operator-side administrative JIT cleanup attempts returned HTTP 403 after their intended provisioning operations had already succeeded. Those tokens were bounded to a maximum 10-minute TTL and are not used by the scheduled backup path. The scheduled backup token self-revoke is independently VERIFIED. The live administrative policy must be compared/refreshed against the Git baseline before declaring this specific lifecycle invariant revalidated.

## Scope boundary

`VAULT_CORE_OPERATIONAL_RUNTIME_PASS=VERIFIED`.

`FIRST_CONSUMER_BOOTSTRAP=NOT_RUN` remains a separate gate. `UNSEALED_READY` is not promoted by core-runtime evidence alone.

No root token, Vault token, SecretID, Shamir share, private key, private-key passphrase, snapshot passphrase or custody location is recorded in this evidence.
