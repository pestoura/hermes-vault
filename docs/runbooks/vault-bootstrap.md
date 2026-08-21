# Vault Bootstrap Runbook — Shamir / audit / JIT admin / root retirement

**Scope:** Hermes shared Vault single-node, Raft, TLS, manual Shamir 3/2.

**Runtime checkpoint (2026-08-21):** init and quorum unseal are verified; Vault is healthy/unsealed. Audit enablement, ADR-022 JIT bootstrap and initial-root revocation remain separately operator-only HITL until executed and evidenced.

The canonical post-unseal order is **audit → JIT certificate administration → independent non-root proof → revoke initial root**. See `docs/runbooks/jit-admin-bootstrap.md`.

## HITL boundary

The following remain human/operator operations and are never executed by CI or unattended agents:

- `vault operator init` and `vault operator unseal` when initialization/recovery requires them;
- Shamir material and initial root handling under **out-of-band custody**;
- encrypted administrative certificate secret-key generation/custody;
- live audit enablement and JIT bootstrap using bootstrap root;
- final root self-revocation after independent JIT proof;
- AppRole SecretID issuance/wrapping and production promotion sign-off.

No share, token value, SecretID, passphrase, recovery locator or certificate secret key belongs in Git, Hermes state, Context Core, logs or prompts.

## Current sequence

1. `INIT` — `VERIFIED_INITIALIZED` for the current runtime.
2. `UNSEAL` — `VAULT_UNSEALED` and `VAULT_HEALTH_PASS` verified for the current runtime.
3. `AUDIT` — operator-only; must pass before post-root administration is installed.
4. `ADR-022 JIT` — install `vault-admin-issuer` + `hermes-vault-admin`; prove positive and negative capabilities with root absent.
5. `REVOKE` — reload initial root only from out-of-band custody and use `vault token revoke -self`; never pass its value as an argument.
6. `ROOT_REVOKED` — record only after revoked-token self-lookup fails and post-revoke JIT smoke succeeds.

Fail closed if any stage is not evidenced.
