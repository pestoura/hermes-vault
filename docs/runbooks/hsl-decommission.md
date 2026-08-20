# HSL-Owned Deployment Decommission / Freeze — Options & Owner Gate (Task I2)

Provenance:
  source_plan: docs/superpowers/plans/2026-08-18-hermes-shared-vault-service.md (Task I2)
  spec: docs/specs/2026-08-18-hermes-shared-vault-service-design.md (§17 migration, §20 key-continuity risk row, §25.1 unresolved owner decision, §25.3 cutover vs parallel-run)
  reference_read_only: pestoura/hermes-security-labs `deployment/vault-lab-l1`
  inherited_observations: HSL-state claims below are inherited from Task I1 /
        earlier read-only verification and are NOT re-verified in Task I2.
  worktree: hermes-shared-vault-service-implementation
  mode: DOCUMENTED ONLY — repo-side / static. No Vault started, no HSL mutation,
        no deletion, no credential or secret material, no remote contact.

## Headline / scope

`hermes-vault` owns the shared Vault service lifecycle (spec §3, §15, §17).
This runbook **records** the options for retiring the consumer-owned HSL Vault
deployment `deployment/vault-lab-l1` and the gate that must be satisfied before
any of them is executed.

This runbook does **not** execute anything. The actual HSL freeze/decommission
mutation is **OUT OF SCOPE** here and is recorded as **NOT_RUN**. `hermes-vault`
never writes to `pestoura/hermes-security-labs` (INV-11); the HSL reference is
read-only.

## Current approved architectural ruling

The approved ruling in force for this migration is:

- **Direct ownership migration, with NO parallel live Vault.**
- Basis: two structural **observations inherited from Task I1 / earlier
  read-only verification**. They are recorded here as **inherited observations,
  NOT re-verified in Task I2** (this task performs no remote contact, no HSL
  read, and no cross-repo inspection), and they must not be read as facts newly
  established or re-confirmed by I2:
  - *Observation (inherited from I1, read-only, not re-verified in I2):* the HSL
    Vault deployment was **never promoted** — it never reached a
    promoted/production state, so on that basis there is no promoted live
    instance whose continuity must be preserved across a transition window.
  - *Observation (inherited from I1, read-only, not re-verified in I2):* HSL
    `main` **no longer carries** `deployment/vault-lab-l1` — the directory was
    not tracked on HSL trunk at the time of that read-only verification, so on
    that basis there is no live consumer-owned deployment left in the trunk line
    to run in parallel or to decommission on trunk.
  - Both observations must be **re-confirmed by the owner against live HSL state
    before ANY execution**; if either no longer holds, the ruling's basis must be
    revisited.
- Consequence: option B (read-only verify) and option C (parallel-run) below are
  documented for completeness and for the historical-signature case only; they
  are **not** the approved path. The approved path is option A framing as a
  direct ownership migration to `deployments/vault/` in `hermes-vault`, without
  standing up or maintaining a second live Vault.

This ruling settles the *structural posture*. It does **not** settle the
key-continuity decision, which remains owner-gated (next section).

## Owner decision gate (blocking, before ANY execution)

Any later freeze/decommission execution is **gated** on the **key-continuity
owner decision / sign-off** (spec §20 risk row, spec **§25.1**).

The HSL transit key `hermes-lab-l1-signer` is non-exportable
(`exportable=false`, `allow_plaintext_backup=false`) and therefore cannot be
migrated as key material into the shared `hsl-transit` mount. The owner must
decide, and sign off, one of:

1. Retain the old HSL mount **read-only for `verify`** during a transition window.
2. Accept that historical signatures become unverifiable and **re-sign** the
   affected evidence with the new shared `hsl-transit/hsl-signing` key.
3. Define an explicit **verify-continuity policy** covering historical evidence.

Gate rules:

- No freeze, no decommission, no deletion, no seal, and no mount removal may be
  executed until this owner decision is recorded **and** signed off by the owner.
- Absent an owner decision, the state is **fail-closed**: nothing is executed and
  the HSL deployment is left exactly as-is.
- Sign-off is an operator/HITL step. It is never coded, never inferred from CI,
  and never auto-executed by any task in this plan (spec §16.3, no
  auto-promotion).

## Options (recorded for the owner decision)

### Option A — Decommission (approved framing: direct ownership migration)

- Intent: retire the consumer-owned deployment entirely; `deployments/vault/` in
  `hermes-vault` is the single canonical service.
- Preconditions: shared path validated (mount/key/AppRole + negative-capability
  tests green), restore drill PASS, audit PASS, **and** key-continuity owner
  sign-off per the gate above.
- Notes: on the basis of the two inherited observations above (never promoted;
  HSL trunk no longer carries `deployment/vault-lab-l1`) — **inherited from I1,
  not re-verified in I2** — this is the approved path and requires **no
  parallel live Vault**.
- Historical evidence: only safe once the owner selects re-sign or an explicit
  verify-continuity policy (options 2/3 of the gate).
- Status here: **NOT_RUN** — execution is a separate, owner-gated effort.

### Option B — Freeze as read-only verify

- Intent: keep the old transit mount reachable for `verify` only (no `sign`), so
  historical HSL-signed evidence stays verifiable during a transition window.
- Preconditions: owner selects gate option 1; exact-path policy restricted to
  `verify` (no `sign`, no wildcard, no `sudo`); audit device active.
- Cost: keeps a second Vault surface alive, which the approved ruling avoids
  unless the owner explicitly requires verify continuity.
- Status here: **NOT_RUN** — documented option only.

### Option C — Parallel-run during transition

- Intent: run the consumer-owned deployment and the shared service concurrently
  while consumers are repointed.
- Explicitly **NOT the approved path**: the current ruling is direct ownership
  migration with **NO parallel live Vault**. Recorded only because spec §25.3
  lists cutover-vs-parallel-run as an owner-visible choice.
- Cost/risk: doubled blast radius, doubled unseal/audit/custody burden, ambiguous
  signing authority.
- Status here: **NOT_RUN** — documented option only, not recommended.

## Ownership boundary (must hold)

- `deployments/vault/` is the canonical, provider-owned service in `hermes-vault`.
- No `deployment/vault-lab-l1` replica is created in this repo
  (`tests/isolation/test_ownership_boundary.py` asserts absence).
- HSL consumes via the published contract (`hsl-transit/hsl-signing`,
  `hsl-signer` AppRole). Cross-repo HSL repointing/handoff (K1/M1) is specified,
  not performed.
- **No HSL mutation** is performed by this runbook or by Task I2. `hermes-vault`
  does not modify `pestoura/hermes-security-labs` (INV-11); the HSL reference is
  read-only and descriptive of the ownership boundary only.

## NOT_RUN / out-of-scope (by design — never executed here)

- Freeze, decommission, deletion, seal, or mount removal of HSL
  `deployment/vault-lab-l1` — **NOT_RUN**, out of scope, owner-gated.
- Any HSL repository write (branch, commit, PR, delete) — **NOT_RUN**.
- Starting, unsealing, or configuring any Vault instance — **NOT_RUN**.
- Live key/mount/AppRole/SecretID operations, TLS private-key custody — operator
  HITL only, **NOT_RUN**.
- Production promotion sign-off (restore drill PASS + audit PASS + owner
  sign-off) — **NOT_RUN**.

## Repo-side verification for Task I2

- `tests/isolation/test_hsl_decommission_doc.py` asserts this runbook exists,
  lists the three options, states the approved ruling (direct ownership
  migration / no parallel live Vault), keeps the two structural claims
  ("never promoted", "HSL main no longer carries the path") labelled as
  observations inherited from I1 / earlier read-only verification and **not
  re-verified in I2**, gates execution on the key-continuity owner decision and
  sign-off, and keeps HSL mutation out of scope / NOT_RUN.
- Repo-side VERIFIED in I2: only the static/textual properties of this runbook.
  The inherited HSL-state observations are **NOT_RUN / not re-verified** in I2
  and remain owner-gated against live HSL state.
- Offline/static only; no Vault, no secrets, no remotes.
