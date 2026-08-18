# Vault Bootstrap Runbook — Init / Unseal / Root (HITL)

**Scope:** Hermes shared Vault single-node (Raft, TLS, Shamir 3/2) under
`deployments/vault/`. This runbook records the human procedure only.

**Status:** `NOT_RUN` — live `vault operator init`, `vault operator unseal`,
initial root token handling, and revoke-root are **operator-only (HITL)** and
are **not executed by this repository, CI, or any unattended task**. This file
is documentation.

**Image pin (HSL-validated digest):**
`hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569`

---

## HITL boundary

The following steps are recorded here for the operator. They MUST NOT be
automated, coded, or run by any unattended task:

- `vault operator init`
- `vault operator unseal`
- initial root token handling / revoke
- AppRole SecretID issuance / wrapping
- TLS private-key generation / custody
- production promotion sign-off

All Shamir shares, the root token, and the recovery keys are recorded to
**out-of-band custody** (a physical/separate secret store) and are **never**
written to this repo, logs, CI output, or evidence bundles.

---

## Operator procedure

### 0. Preconditions (operator)

- The pinned Vault image is running via `deployments/vault/docker-compose.yml`
  with TLS listener up (see B3 TLS provisioning, operator-only).
- `VAULT_ADDR` and `VAULT_CACERT` are set in the operator shell.
- A quorum of at least 2 credentialed operators is present.

### 1. Init (HITL — operator only)

```bash
vault operator init -key-shares=3 -key-threshold=2
```

- Capture the **3 unseal keys (Shamir shares)** and the **initial root token**
  exactly as printed.
- Record them to **out-of-band custody** immediately.
- Do **NOT** commit, paste, or log these values anywhere in the repo.

### 2. Unseal — quorum (HITL — operator only, x2)

Each of the `key-threshold=2` operators presents one distinct unseal key:

```bash
vault operator unseal <UNSEAL_KEY_1>   # operator A
vault operator unseal <UNSEAL_KEY_2>   # operator B
```

- Threshold reached → Vault becomes unsealed.
- Keys are entered interactively; nothing is stored in automation.

### 3. Revoke initial root after bootstrap (HITL — operator only)

Once a properly-scoped admin identity/policy is in place, revoke the initial
root token out-of-band:

```bash
vault token revoke <INITIAL_ROOT_TOKEN>
```

- Performed by the operator against the out-of-band-custodied root token.
- Never automated.

### 4. Enable audit device (HITL — operator only)

```bash
vault audit enable file file_path=/vault/logs/audit.log
```

---

## Fail-closed postures

- If init output is ever written to a tracked path, treat the secret as
  compromised (see `SECURITY.md` → Suspected exposure) and rotate.
- Unseal keys and root token are **out-of-band custody** only.
- This runbook never starts Vault, never reads/writes tokens/shares/keys, and
  contains no usable secret material.
