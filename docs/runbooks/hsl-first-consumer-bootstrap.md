# HSL first-consumer bootstrap — shared Hermes Vault

**Scope:** controlled transition from an operational shared Vault core to the
first HSL consumer. Repository implementation and live execution are separate.

```text
FIRST_CONSUMER_BOOTSTRAP=NOT_RUN
HSL_BOOTSTRAP_JIT_LIVE_PROMOTION=NOT_RUN
UNSEALED_READY=false
```

## Security invariants

- No root token is reintroduced; the initial root remains retired.
- No Shamir share, Vault token, certificate passphrase, SecretID or wrapping
  token is written to Git, logs, evidence, ChatGPT context or command history.
- JIT tokens are short-lived, orphaned, non-renewable and class-scoped.
- The HSL mount/key bootstrap class has no wildcard, delete or sudo capability.
- SecretID issuance/wrapping remains an operator-only HITL boundary.
- Repository GREEN never promotes `FIRST_CONSUMER_BOOTSTRAP` by itself.

## Preconditions

1. `VAULT_CORE_OPERATIONAL=VERIFIED` and Vault is initialized/unsealed.
2. Audit, scheduled backup and isolated restore evidence remain accepted.
3. The certificate JIT issuer is available from operator-controlled custody.
4. This repository revision containing the HSL bootstrap JIT class is merged
   and its exact-SHA CI is GREEN before any live promotion.

## Phase 1 — promote the bounded HSL bootstrap JIT class

Use two independent JIT tokens; never combine administrative classes.

1. Mint a token requesting only `vault-admin-policy`, then run:

```bash
export VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK=yes
bash deployments/vault/scripts/promote-hsl-bootstrap-admin.sh policy
unset VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK
unset VAULT_TOKEN
```

The script validates the exact class, writes only `vault-admin-hsl-bootstrap`
and self-revokes that JIT token.

2. Mint a fresh token requesting only `vault-admin-token`, then run the same
operator gate in `role` mode:

```bash
export VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK=yes
bash deployments/vault/scripts/promote-hsl-bootstrap-admin.sh role
unset VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK
unset VAULT_TOKEN
```

The role-mode token updates only the bounded `hermes-vault-admin` token-role
contract and self-revokes. No mount, key, AppRole or consumer credential is
created during this phase.

## Phase 2 — create only the HSL Transit mount/key

Mint a new JIT token requesting only `vault-admin-hsl-bootstrap`, then run:

```bash
export VAULT_HSL_TRANSIT_OPERATOR_ACK=yes
bash deployments/vault/scripts/enable-hsl-transit.sh
unset VAULT_HSL_TRANSIT_OPERATOR_ACK
vault token revoke -self
unset VAULT_TOKEN
```

Expected result: only `hsl-transit/` and `hsl-transit/keys/hsl-signing` are
created or confirmed idempotently. Other mounts remain outside this JIT class.

## Phase 3 — install policy and bind the HSL AppRole

Use separate JIT classes rather than one broad administrator:

1. Mint `vault-admin-policy`; write the committed `policies/hsl/hsl-signer.hcl`.
2. Self-revoke that token.
3. Mint `vault-admin-auth`; run `enable-hsl-signer.sh`.
4. Self-revoke that token.

The AppRole remains bounded to policy `hsl-signer`, whose only capabilities are
sign, verify and key-metadata read for `hsl-transit/hsl-signing`.

## Phase 4 — Secret-zero handoff (HITL)

The operator follows `docs/runbooks/secret-zero.md`. SecretID issuance and
wrapping are never automated here. The consumer receives a wrapped, single-use,
short-TTL credential out-of-band, consumes it once and does not persist it.

No SecretID, wrapping token or resulting Vault token may be pasted into ChatGPT
or recorded in repository/evidence output.

## Acceptance before cutover

The shared signer remains non-authoritative until fresh positive and negative
capability evidence passes and the separate HSL trust/promotion lifecycle is
approved. `FIRST_CONSUMER_BOOTSTRAP=NOT_RUN` remains until that execution occurs.
