# HSL consumer migration boundary — resolved architecture, execution separate

**Status:** documented boundary only. External migration remains `NOT_RUN`.

**Owner model:** `hermes-vault` owns the shared service. `hermes-vault does not modify pestoura/hermes-security-labs`; the actual HSL repointing is a **SEPARATE** cross-repo implementation and is not implemented in hermes-vault.

## Provenance

Current-state claims about the HSL deployment, mounts or historical signer are **INHERITED** from earlier read-only documentation and were **NOT independently re-verified** in this change. Live HSL state must be re-confirmed before execution. These inherited observations do not reopen the structural choices resolved on 2026-08-21.

## Resolved §25 decisions

The former owner-decision block is now resolved:

- **§25.1 / ADR-018 — key continuity:** retain legacy `hermes-lab-l1-signer` as **verify-only** after cutover; no bulk re-signing of historical evidence.
- **§25.2 / ADR-019 — network exposure:** shared Vault remains host-loopback only and consumers connect through Docker network `hermes-security-plane` using TLS endpoint `hermes-vault:8200`.
- **§25.3 / ADR-020 — cutover vs parallel-run:** use **controlled parallel-run**; the shared service is non-authoritative while acceptance is pending, then becomes sole signer for new evidence while legacy becomes verify-only.
- **§25.4 / ADR-021 — recovery custody:** Shamir 3/2 with independent out-of-band custody; concrete custody locators are never recorded in GitHub, Hermes or Jarvas.
- **§25.5 — image:** official pinned `hashicorp/vault:1.21.4` digest already defined by the baseline.

The phrase **owner decision required** no longer applies to these structural choices. What remains owner/HITL gated is the live execution itself.

## Current and target boundaries

Historical deployment reference: `deployment/vault-lab-l1` in `pestoura/hermes-security-labs`.

Target shared capability: `hsl-transit/hsl-signing` in `pestoura/hermes-vault`, reached on `hermes-security-plane` through the `hermes-vault` DNS alias.

The actual HSL configuration/repointing is **not implemented here**. No consumer code, deployment or runtime is changed by this document.

## Controlled migration sequence

The separate HSL-local implementation follows these states:

1. `LEGACY_SIGN_ACTIVE` — historical pre-cutover state.
2. `PARALLEL_SHARED_PENDING_ACCEPTANCE` — shared Vault is tested without becoming signing authority.
3. `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` — shared Vault signs new evidence; legacy path is verify-only.
4. `LEGACY_VERIFY_RETIRED` — legacy verification is removed only after continuity/retention sign-off.

Entry into `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` requires fresh evidence for:

```text
VAULT_HEALTH_PASS
VAULT_UNSEALED
AUDIT_PASS
RESTORE_DRILL_PASS
TLS_CONNECTIVITY_PASS
HSL_ISOLATION_PASS
SIGN_VERIFY_PASS
LEGACY_HISTORICAL_VERIFY_PASS
NO_SECRET_TO_MODEL
OWNER_CUTOVER_SIGNOFF
```

No missing or unexecuted gate may be called PASS.

## Cross-repo responsibilities

### `pestoura/hermes-vault`

- owns the Vault deployment/lifecycle and `hermes-security-plane` service endpoint;
- owns the shared HSL capability contract and exact-path isolation;
- produces acceptance evidence for the shared signer and recovery/audit gates;
- does not mutate HSL in this plan.

### `pestoura/hermes-security-labs`

The separate HSL implementation will eventually repoint signing/evidence consumption from the historical `deployment/vault-lab-l1` context to `hsl-transit/hsl-signing`, preserve legacy verification according to ADR-018, and remove legacy signing after cutover. None of those changes are executed in this repository.

## INV-11 / non-mutation boundary

`INV-11` remains mandatory. There is **no remote-mutating command** in this document. A remote-mutating action category such as **push, PR, or API call** is neither **performed** nor **instructed** here.

No credentials and no secrets are used by this documented-only boundary. No live private/recovery material is generated, read or transferred.

## External execution state

- HSL repointing: `NOT_RUN`.
- Legacy signing disablement: `NOT_RUN`.
- Legacy verify-retention activation: `NOT_RUN`.
- Shared signing cutover: `NOT_RUN`.
- Legacy verifier retirement: `NOT_RUN`.

The live state must be re-confirmed immediately before the separate cross-repo execution, but the structural decisions above remain resolved unless new evidence forces a new ADR.
