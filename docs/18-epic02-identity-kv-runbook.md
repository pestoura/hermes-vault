# EPIC-02 — Workload identities, policies and KV pilot handoff

## Purpose

Prepare the initial Vault workload identities and KV v2 boundary without selecting or migrating a real secret before the live Jarvas inventory is complete.

This repository slice **não seleciona** GitHub or any other provider as the real migration pilot. `github-tool` is the first concrete tool identity because its canonical path/policy is already defined in the architecture; pilot selection is a later evidence-driven decision.

## Repository contracts

Initial AppRoles:

```text
hermes-runtime
hermes-controller
jarvas-operations
github-tool
```

All roles use:

```text
token_no_default_policy = true
secret_id_num_uses      = 1
secret_id_ttl           = 10m
wrap_ttl                = 5m
token_max_ttl           <= 30m
```

`hermes-runtime`, `hermes-controller` and `jarvas-operations` receive no direct KV path in EPIC-02. They can inspect their own token and ask Vault for their own capabilities.

`github-tool` can read only:

```text
secret/data/jarvas/github/runtime
secret/metadata/jarvas/github/runtime
```

No wildcard is required.

## Bootstrap order

Run only after the EPIC-01 Vault baseline is live, initialized/unsealed and the controlled bootstrap root credential is active:

```bash
./operations/epic02_identity_kv.sh preflight
./operations/epic02_identity_kv.sh kv-status
./operations/epic02_identity_kv.sh kv-enable
./operations/epic02_identity_kv.sh configure-policies
./operations/epic02_identity_kv.sh configure-roles
```

`kv-enable` accepts an existing `secret/` mount only when it is exactly KV v2. A divergent mount fails closed.

Role provisioning examples:

```bash
./operations/epic02_identity_kv.sh role-id github-tool
./operations/epic02_identity_kv.sh wrapped-secret-id github-tool
```

RoleID is an identifier. The wrapped response and unwrapped SecretID are credential material and must stay outside Git, issues, chat and persistent logs.

## Capability proof

After a workload authenticates through AppRole and its resulting token is present in the normal Vault client environment, run:

```bash
./operations/epic02_identity_kv.sh capability-check github-tool
```

The command first verifies that the current token carries exactly the expected policy, then executes the positive and negative matrix from `identity/negative-capability-matrix.json` using self-capability queries.

Required repository/live properties:

- `github-tool` can read its exact data/metadata path;
- it cannot read Grafana, Cloudflare or Microsoft Planner KV paths;
- runtime/controller/operations cannot read the GitHub KV path;
- all roles are denied policy/auth/mount administration;
- no role has `sudo` or wildcard paths.

## KV pilot: wait for live discovery

`templates/kv-pilot-handoff.json` remains `AWAITING_LIVE_DISCOVERY` until Phase 0 has identified a real candidate and its owner/consumer/rollback facts.

The pilot selection criteria are:

1. inventário live identifies the reference and consumer;
2. owner and provider are known;
3. credential is low impact and easy to regenerate;
4. classification says static KV is appropriate;
5. acceptance test is defined;
6. rollback is defined;
7. rotation is supported or the limitation is explicitly accepted.

Do not start with root/recovery credentials, IAM-critical credentials, an integration without rollback, or a credential whose owner is unknown.

## Live migration sequence

Only after the handoff is fully populated from live evidence:

```text
inventory validation
→ owner validation
→ target path/policy validation
→ write credential to KV using a controlled secret-safe operator path
→ configure consumer for Vault
→ positive acceptance test
→ negative access test
→ short tracked rollback window
→ rotate/revoke legacy provider credential
→ restart/reboot acceptance
→ remove legacy reference/store
→ secret scan
→ sanitized evidence
```

No real secret value is to be placed in a command line, GitHub issue, PR, chat response or evidence record.

## Rollback

Before cutover, the handoff must contain an explicit `rollback_ref`. During the short rollback window, restoring the previous consumer reference is permitted only until the legacy provider credential is rotated/revoked. After rotation, rollback must use a newly governed credential rather than resurrecting a revoked secret.

## Live gates

Repository readiness does not satisfy:

```text
AUTH_PASS             = NOT_RUN
LEAST_PRIVILEGE_PASS  = NOT_RUN
NEGATIVE_TEST_PASS    = NOT_RUN
NO_GLOBAL_WILDCARD    = repository-contract prepared; live acceptance pending
KV_PILOT_PASS         = NOT_RUN
ROTATION_PASS         = NOT_RUN
LEGACY_SECRET_REMOVED = NOT_RUN
RESTART_PASS          = NOT_RUN
```

These gates move only with sanitized live Vault/Jarvas evidence.