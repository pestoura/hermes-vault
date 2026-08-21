# ADR-022 live acceptance evidence — 2026-08-21

## Result

**State:** `VERIFIED_ADR022_LIVE_ACCEPTED`

ADR-022 completed its live audit-first certificate JIT administration acceptance sequence on HermesJarvas. This evidence intentionally records only non-secret runtime and repository metadata.

## Repository baseline

- Canonical repository: `pestoura/hermes-vault`
- Accepted main SHA: `db0c98bfc7e5a8cf3d9b19394cc64be6c0dc643f`
- Post-merge GitHub Actions run: `32490916043` — `success`
- Vault image/runtime version: `1.21.4`

## Live gates

- `AUDIT_PASS` — file audit device enabled before JIT bootstrap; audit file independently observed non-empty after each major operation.
- `JIT_BOOTSTRAP_PASS` — administrative policies, `auth/cert`, JIT token role and certificate identity applied under operator HITL.
- `JIT_PROOF_PASS` — certificate login succeeded; issuer could not perform direct policy administration; a scoped JIT token performed its allowed policy operation, was denied audit administration, and self-revoked successfully.
- `ROOT_REVOKED` — the initial root token self-revoked only after the independent JIT proof; subsequent lookup using that token failed.
- `POST_REVOKE_SMOKE_PASS` — after root retirement, certificate login, fresh JIT issuance, allowed/denied operation checks and JIT self-revoke all passed.

## Independent runtime observations

After the post-revoke smoke, Desktop Commander independently observed:

- container healthy;
- `initialized=true`;
- `sealed=false`;
- storage type `raft`;
- Vault version `1.21.4`;
- audit file present and non-empty;
- Raft committed/applied index advancing through the acceptance sequence.

No audit log contents were read into this evidence.

## Safety boundary

No Shamir share, root/Vault token value, certificate private key, certificate passphrase, SecretID, recovery material, or concrete custody location is recorded here.

## Remaining live gates

ADR-022 acceptance does **not** promote `UNSEALED_READY` or production readiness.

- restore drill: `NOT_RUN`
- first consumer bootstrap: `NOT_RUN`
- consumer mount/policy/negative-capability acceptance: `NOT_RUN`

The next structural live gate is the restore drill, followed by the first consumer bootstrap according to the canonical service design.
