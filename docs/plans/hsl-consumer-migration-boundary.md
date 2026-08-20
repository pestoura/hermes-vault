# HSL consumer migration boundary (cross-repo plan, not executed here)

**Task:** K1 (Document HSL migration boundary — no execution)
**Source:** plan Group K (lines 968-983); spec §17, §17.5, §19, §25.1/§25.2/§25.3
**Status:** DOCUMENTED ONLY — Action: NONE in this plan.

> **Provenance of HSL current-state claims.** Every statement in this document
> about the current HSL Vault mounts, signing keys, or ownership is an
> **INHERITED OBSERVATION** drawn from the canonical spec (§17, §19, §25). It was
> **NOT independently re-verified** against the live HSL deployment during Task
> K1, and K1 performs no read of any Vault instance or remote repository. The
> owner MUST re-confirm the live HSL state (mounts, key `hermes-lab-l1-signer`,
> ownership) before any migration execution. External migration execution stays
> **NOT_RUN** and is owner-gated.

---

## 1. Migration is a SEPARATE cross-repo plan in `pestoura/hermes-security-labs`

The actual HSL migration — repointing HSL signing/evidence paths from the
historical `deployment/vault-lab-l1` transit to the shared
`hsl-transit/hsl-signing` (or retaining a verify-only mount during transition)
— is a **SEPARATE cross-repo implementation plan** owned by
`pestoura/hermes-security-labs`. It is **NOT implemented in hermes-vault** (spec
§17.5, §19, §25.1/§25.3).

This document only enumerates that boundary. It performs none of the migration
steps.

## 2. Current state (INHERITED, not re-verified)

- HSL owns a Vault deployment under `deployment/vault-lab-l1/` (single-node
  Raft, TLS, AppRole signer, transit key `hermes-lab-l1-signer`). Inherited from
  spec §17; **NOT independently re-verified** in K1.
- Target state: `hermes-vault` owns the shared service; HSL consumes via the
  contract with a dedicated `hsl-transit/` mount + `hsl-signing` key +
  `hsl-signer` AppRole (spec §17, §15).

## 3. Migration steps (out-of-repo, enumerated only)

These steps are executed as a separate HSL-local plan, not here:

1. Stand up the shared service per this spec before HSL depends on it (spec §17.1).
2. Create HSL's dedicated mount/key/AppRole under the shared service and verify
   with negative-capability tests (spec §17.2).
3. Repoint HSL's signing/evidence path from `deployment/vault-lab-l1` transit to
   the shared `hsl-transit/hsl-signing` — **or** retain a verify-only mount
   during transition (spec §17.3, §19).
4. Decommission or freeze the HSL-owned deployment only after the shared path is
   validated and the key-continuity decision is made (spec §17.4, §25.1).

## 4. Three owner decisions required before execution

These are structural choices the spec deliberately does not decide (spec §25);
each must be resolved by the owner before/during the HSL-local migration:

- **Key continuity — §25.1.** The current HSL transit key `hermes-lab-l1-signer`
  is non-exportable (`exportable=false`, `allow_plaintext_backup=false`) and
  cannot be migrated as material to `hsl-transit`. Owner decides: (a) retain the
  old HSL mount read-only for `verify` during a transition window; (b) accept
  that historical signatures become unverifiable and re-sign with the new key;
  or (c) define a verify-continuity policy.
- **Network exposure — §25.2.** Design assumes Vault is reached by consumers via
  loopback/container-network TLS on the Jarvas host. Owner must confirm the
  exact bind address, port, and how HSL (a separate deployment/repo) connects to
  the shared service.
- **Cutover vs parallel-run — §25.3.** Owner must decide whether
  `deployment/vault-lab-l1` is decommissioned after migration, kept read-only for
  verify, or run in parallel during transition.

## 5. hermes-vault owns the shared service; never modifies HSL

`hermes-vault` owns the shared service (deployment/lifecycle); consumers depend
on the contract only (spec §3, §15, §17, ADR-013). **hermes-vault does not
modify `pestoura/hermes-security-labs`** or any other repository (INV-11). The
cross-repo HSL repointing is specified here as a boundary, not performed.

## 6. INV-11 / non-mutation boundary

This document does not write to `pestoura/hermes-security-labs` or any other
repo. References to `hermes-security-labs` are descriptive ownership-boundary
notes only. No remote-mutating command (push, PR, or API call) is performed or
instructed here. No Vault runtime, token, Shamir share, or TLS private
  material is referenced, generated, or read. **No credentials** and **no secrets**
  are used in K1.

## 7. External migration state — NOT_RUN

- Executing the HSL repointing, resolving §25.1/§25.2/§25.3, and decommissioning
  `deployment/vault-lab-l1` are SEPARATE cross-repo actions owned by the HSL
  repository owner. All remain **NOT_RUN** in K1.
- Any HSL current-state observation above is **INHERITED / NOT independently
  re-verified** in K1 and must be **re-confirmed** by the owner against live HSL
  before execution.

---

**Verification (repo-side):** `tests/plans/test_hsl_boundary_doc.py` asserts the
existence and required content of this file (8 checks: existence; required
markers; SEPARATE cross-repo + not-implemented-in-hermes-vault + verify-only
alternative; three owner decisions §25.1/§25.2/§25.3; hermes-vault owns + INV-11
non-mutation; external NOT_RUN; inherited/not-re-verified/re-confirm; no
mutation/credentials/secrets). Offline; no remote contact.

**External HSL migration state:** NOT_RUN — must be reconfirmed by the owner
against live HSL before any execution.
