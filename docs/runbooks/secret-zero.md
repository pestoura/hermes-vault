# Secret-Zero Bootstrap Runbook — Wrapped AppRole SecretID (HITL)

**Scope:** Delivery of the *first* credential (AppRole SecretID) to the
`hsl-signer` consumer, operated by `hermes-vault`. This runbook records the
human procedure and the delivery *contract* only.

**Status:** `NOT_RUN` — live AppRole SecretID issuance, wrapping, and CIDR
binding are **operator-only (HITL)** and are **not executed by this repository,
CI, or any unattended task**. This file is documentation + contract.

**Image pin (HSL-validated digest):**
`hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569`

---

## HITL boundary (INV-8 / INV-10)

These steps are recorded for the operator. They MUST NOT be automated, coded,
or run by any unattended task:

- AppRole SecretID issuance (`vault write ... auth/approle/role/hsl-signer/secret-id`)
- SecretID wrapping (`-wrap-ttl=...`)
- CIDR binding (`token_bound_cidrs=...`)
- TLS private-key generation / custody
- production promotion sign-off

All issued SecretIDs, wrapping tokens, and CIDR bindings are recorded to
**out-of-band custody** and are **never** written to this repo, `.env` files,
state, logs, CI output, or GitHub.

---

## Delivery contract (spec §15, ADR-017, INV-8)

The first credential is delivered under the following constraints:

1. **Wrapped** — the SecretID is returned wrapped (`-wrap-ttl`), never in clear.
2. **Single-use** — the issuance sets `num_uses=1`, so the unwrapped SecretID
   can be used exactly once by the consumer bootstrap.
3. **Short-TTL** — the effective SecretID TTL is `<=300s`; this issuance sets
   `ttl=120`.
4. **CIDR-bound** — `cidr_list` restricts where the SecretID may be used for
   login, and `token_bound_cidrs` restricts where the resulting token may be
   used (synthetic example below).
5. **Never at rest in the repo** — no `.env`, no state file, no log, no commit.

The provider-neutral contract envelope (`CapabilityRequest` /
`CapabilityType.wrapped_secret`, `src/capability_contract/schema.py`) carries
**no secret value** by design: `extra="forbid"` rejects any secret payload.

---

## Operator procedure (NOT_RUN)

### 0. Preconditions (operator)

- Pinned Vault image running via `deployments/vault/docker-compose.yml` with
  TLS listener up (see B3 TLS provisioning, operator-only).
- `VAULT_ADDR` and `VAULT_CACERT` set in the operator shell.
- `hsl-signer` AppRole already enabled (see `deployments/vault/scripts/enable-hsl-signer.sh`,
  operator-run).
- Consumer egress CIDR known (example only, RFC 5737 documentation range):
  `203.0.113.0/24`.

### 1. Issue a wrapped, single-use, short-TTL, CIDR-bound SecretID (HITL)

```bash
# Operator-only. SYNTHETIC CIDR EXAMPLE — replace with the real consumer range.
vault write -f -wrap-ttl=60s \
  auth/approle/role/hsl-signer/secret-id \
  ttl=120 \
  num_uses=1 \
  cidr_list="203.0.113.0/24" \
  token_bound_cidrs="203.0.113.0/24"
```

- Capture the **wrapping token** from terminal output only.
- Record it to **out-of-band custody** immediately.
- Do **NOT** commit, paste, or log the wrapping token or the underlying SecretID.

### 2. Consumer bootstrap (controlled + audited — NOT "move secret to another file")

The consumer receives the **wrapping token** (not the raw SecretID). It unwraps
once, uses the SecretID a single time to authenticate, and discards it:

```bash
# Consumer-side, from the operator-delivered wrapping token ONLY.
# WRAPPED-TOKEN-EXAMPLE-NOT-REAL is a placeholder; the real value is delivered
# out-of-band and is never stored in this repo.
vault unwrap WRAPPED-TOKEN-EXAMPLE-NOT-REAL
```

- The unwrap is **single-use**: the wrapping token is consumed on first use.
- The resulting SecretID is used **once** (`secret_id_num_uses=1`) and then
  expires by TTL (`secret_id_ttl=120`).
- No step here writes the SecretID, wrapping token, or any secret value to a
  file, environment block that is committed, or log.

### 3. Audit (HITL — operator-only)

- Record the issuance event (role, wrapping-token id, CIDR, TTL, operator) in
  the out-of-band audit store.
- Confirm no secret material landed in repo / `.env` / state / logs.

---

## Why this is NOT "move the secret to another file"

The naive pattern — write the SecretID to `secret-zero.env` instead of
`config.env` — merely relocates the secret; it remains at rest, committable,
and loggable. This runbook instead delivers a **wrapped, single-use,
short-TTL, CIDR-bound** credential that is consumed exactly once and expires,
with every issuance audited out-of-band. The repo never holds the value.

---

## Fail-closed postures

- If any SecretID value shape (`SecretID=<value>`) is ever found in
  templates/ policies/ deployments/ src/ docs/ (excluding HITL-boundary prose),
  treat it as a leak: rotate and follow `SECURITY.md` → Suspected exposure.
- The canonical secret scan (`scripts/ci/run-gates.sh --scan-only`) flags the
  `SecretID=<value>` shape; HITL-boundary prose naming "AppRole SecretID" is
  permitted and is required by INV-10.
- This runbook never starts Vault, never reads/writes tokens/SecretIDs, and
  contains no usable secret material (synthetic placeholders only).
