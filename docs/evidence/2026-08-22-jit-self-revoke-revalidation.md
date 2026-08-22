# JIT self-revoke revalidation — live evidence

**Date:** 2026-08-22  
**Scope:** administrative JIT lifecycle revalidation only.  
**Secret handling:** no token, SecretID, Shamir share, private key or passphrase is recorded here.

## Trigger

Two operator-side cleanup attempts had previously returned HTTP 403 after otherwise successful JIT operations. Repository policy already granted `auth/token/revoke-self`, so the live state was explicitly revalidated before Vault closeout.

## Operator-side result

The operator authenticated through the approved certificate JIT path, refreshed the canonical administrative policies, and verified self-revoke independently for each JIT class.

```text
JIT_POLICY_SELF_REVOKE_PASS
JIT_CLASS_SELF_REVOKE_PASS vault-admin-policy
JIT_CLASS_SELF_REVOKE_PASS vault-admin-auth
JIT_CLASS_SELF_REVOKE_PASS vault-admin-token
JIT_CLASS_SELF_REVOKE_PASS vault-admin-secrets-engine
JIT_CLASS_SELF_REVOKE_PASS vault-admin-audit
JIT_CLASS_SELF_REVOKE_PASS vault-admin-recovery
JIT_SELF_REVOKE_REVALIDATION_PASS
```

## Independent safe verification

After the operator test:

- production Vault remained `initialized=true`, `sealed=false`, `standby=false`;
- Vault 1.21.4 remained healthy over strict loopback TLS;
- Docker restart policy remained `unless-stopped`;
- readiness and scheduled-snapshot timers remained enabled and active;
- the latest scheduled snapshot remained mode `0600`;
- zero labelled restore containers remained;
- audit volume metadata remained non-empty (`352 KiB` observed without reading audit contents).
## Decision

`JIT_SELF_REVOKE_REVALIDATION=VERIFIED`.

The earlier HTTP 403 observations are retained as troubleshooting provenance, but they no longer represent an active lifecycle blocker. The live administrative policies have been refreshed and all six JIT classes proved self-revocation.

This result does not promote HSL consumer acceptance. `FIRST_CONSUMER_BOOTSTRAP=NOT_RUN` and `UNSEALED_READY=false` remain separate cross-project gates.
