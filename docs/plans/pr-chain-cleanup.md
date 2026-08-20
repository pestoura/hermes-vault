# PR-chain cleanup strategy (#14–#16 harvest, #17 governance, #18 deferred)

**Task:** J1 (Record PR-chain reconciliation — no execution)
**Source:** plan §18 / Group J (lines 944-966); spec §14, §18; ADR-005, ADR-013
**Status:** DOCUMENTED ONLY — Action: NONE in this plan.

> **Provenance of PR-state claims.** Every statement about the current state of
> PRs #14, #15, #16, #17, or #18 in this document is an **INHERITED OBSERVATION**
> drawn from the canonical plan / spec §18. It was **NOT re-verified** against the
> current GitHub state during Task J1, and J1 performs no read of any remote API.
> The owner MUST reconfirm the live PR state in the respective repository before
> any governance action. Reconciliation/closure execution stays **NOT_RUN** and is
> owner-gated.

---

## 1. Harvest #14 -> #15 -> #16 (concepts only, do NOT merge)

Review the stacked PRs `#14 → #15 → #16`. Extract reusable artifacts — policy
patterns, contract-schema ideas, HCL, and test scaffolding — and **cherry-pick**
the *concepts* into this `hermes-vault` baseline where they align with the
**shared-service / provider-neutral** design.

- Do **not merge** branches. Branch merge is out of scope for J1.
- Keep only what maps to the shared-service ownership boundary (spec §15, §17) and
  the provider-neutral capability contract (spec §14).
- Discard anything that re-asserts lab-dedicated (HSL) ownership — that is out of
  scope (see §6).

This harvest is recorded here as strategy only. Action: NONE in this plan.

## 2. #17 governance — SUPERSEDED ARCHITECTURE, DO NOT MERGE

`#17` (`epic-03/credential-broker-core`) is marked **SUPERSEDED ARCHITECTURE —
DO NOT MERGE**.

- Its closure / supersession is a **governance action** in the respective repo:
  close-as-superseded with rationale citing this spec's ownership boundary
  (spec §15, §17). It is **not an implementation step** here.
- The reconciling owner must record the supersession with the cross-reference to
  this `hermes-vault` plan so the architecture divergence is auditable.
- This document records the strategy only. Action: NONE in this plan.

## 3. #18 deferred — align to provider-neutral F1 contract, NOT secret.read / ADR-005

`VaultCredentialProvider` (#18) is **deferred** from this `hermes-vault`
implementation.

- When picked up later, #18 MUST align with the **provider-neutral capability
  contract** (spec §14): it becomes the contract's Community/OSS implementation
  (**F1**), not a generic `secret.read` (ADR-005).
- The generic `secret.read` shape (ADR-005) is explicitly rejected: a concrete
  Vault adapter is a contract implementation, not a provider-leaking read.
- No adapter is fabricated in J1. Action: NONE in this plan.

## 4. hermes-vault owns the shared service

`hermes-vault` owns the shared service; consumers depend on the contract only
(spec §3, §15, §17, ADR-013). Any PR that re-asserts lab-dedicated ownership is
**out of scope** for this baseline.

## 5. Action: NONE in this plan

The implementer reconciles the chain in the respective repositories with owner
approval. This document is the recorded strategy only. **Action: NONE in this
plan.**

## 6. INV-11 / non-mutation boundary

This document does not modify `pestoura/hermes-security-labs` or any other repo.
References to `hermes-security-labs` are descriptive ownership-boundary notes
only. No remote-mutating command (push, PR, or API call) is performed or
instructed.

## 7. Live/HITL and external PR governance — NOT_RUN

- Closing #17 as superseded, reconciling #14–#16, and scheduling #18 are
  **governance** actions owned by the respective repo owner. All three remain
  **NOT_RUN** in J1.
- No Vault runtime, token, SecretID, Shamir share, or TLS private material is
  referenced, generated, or read. No secret value appears in this document.

---

**Verification (repo-side):** `tests/plans/test_pr_chain_doc.py` asserts the
existence and required content of this file (10 checks: markers, harvest
concept-only, #17 superseded/do-not-merge, #18 deferred/provider-neutral/F1 vs
`secret.read`/ADR-005, ownership, Action: NONE, inherited/not-re-verified/NOT_RUN,
INV-11 non-mutation, no live/secret ops). Offline; no remote contact.

**External PR governance state:** NOT_RUN — must be reconfirmed by the owner
against live GitHub before any closure/merge.
