# ADR-023 — Live isolated restore acceptance

- **Status:** `VERIFIED_ADR023_LIVE_ACCEPTED`
- **Date:** 2026-08-21
- **Run ID:** `adr023-20260821T193532Z-4168849`
- **Canonical repository SHA:** `76c2b7d955be88185496c7efc4636cb835e8447e`
- **Main CI:** run `32524570798`, exact SHA, `SUCCESS` — CI_EXACT_SHA_PASS

## Verified sequence

- recovery-only JIT promotion was already accepted before this run;
- strict-TLS CA repair was verified before staging;
- synthetic fixtures staged and live fixtures cleaned after snapshot;
- plaintext and encrypted Raft snapshot checksums verified;
- disposable Vault started with exact pinned image, `network=none` and zero published ports;
- temporary isolated initialization used Shamir 3/2 under operator-only HITL;
- `snapshot-force` completed inside the labelled disposable runtime only;
- restored snapshot was unsealed with the original production Shamir quorum under HITL;
- post-restore Vault reached `initialized=true`, `sealed=false`, Raft 1.21.4;
- `RESTORE_ACCEPTANCE_PASS` verified synthetic certificate login and the acceptance contract;
- allowed primary KV read passed and forbidden-path access was denied;
- Transit key metadata read passed;
- synthetic acceptance token self-revocation and reuse denial passed;
- `RESTORE_TEARDOWN_PASS` removed the disposable runtime and synthetic private key;
- post-teardown verification confirmed zero restore containers.

## Post-drill production verification

Production remained healthy throughout the drill and after teardown:

- `initialized=true`;
- `sealed=false`;
- `storage=raft`;
- version `1.21.4`;
- audit volume remained non-empty; metadata-only size observed: `224477` bytes.

Retained run artifacts remain mode `0600`; runtime data and the synthetic private key were removed. The canonical snapshot and encrypted copy both passed checksum verification after the drill.

## Harness defects found and corrected during the drill

- PR #37: canonical snapshot stays `0600`; a disposable `0640` runtime copy is mounted for UID 100/GID 1000.
- PR #38: acceptance certificate/key stay `0600`; disposable `0640` runtime copies are mounted for the isolated Vault user.

Both corrections passed TDD, Docker runtime proof, full non-HITL suite, fast gates, secret scan, exact-SHA CI and post-merge verification.

## Gate result

`RESTORE_DRILL_PASS` is **VERIFIED**.

First-consumer acceptance remains `NOT_RUN`; `UNSEALED_READY` is not promoted by this evidence alone.

No Shamir share, temporary initialization material, Vault credential, SecretID, private key, passphrase, or concrete custody location is recorded in this evidence.
