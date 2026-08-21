# Cross-repo handoff to HSL (specifies HSL onboarding + #18; does NOT modify HSL)

**Task:** M1 (Cross-repo handoff specification — no execution)
**Source:** plan Group M (lines 1005-1025); spec §22, §15, §17, §25, INV-11
**Status:** DOCUMENTED ONLY — Action: NONE in this plan.

> **Provenance of HSL / #18 / GitHub current-state claims.** Every statement in
> this document about the current HSL Vault state, PR #18 (and #14-#17) state, or
> GitHub current state is an **INHERITED OBSERVATION** drawn from the canonical
> plan and spec. It was **NOT independently re-verified** against the live HSL
> deployment, the GitHub API, or any remote in M1; M1 performs no read of any
> Vault instance, remote repository, or GitHub API. The owner MUST re-confirm the
> live state before any execution. All of these remain **NOT_RUN**.

---

## 1. HSL onboarding contract — BUILT HERE (item 1)

The consumer onboarding contract for `pestoura/hermes-security-labs` (HSL) is
produced in this repository (`pestoura/hermes-vault`). HSL consumes the shared
service via:

- the dedicated `hsl-transit/` mount,
- the `hsl-signing` key under that mount,
- the `hsl-signer` AppRole,
- the exact-path policy granting only the scoped `hsl-transit/...` paths (no
  wildcard, no `sys/`/`auth/` reach),
- the negative-capability matrix produced by tasks E1 (mount), E2 (AppRole +
  exact-path policy), and E3 (negative-capability matrix).

These artifacts live in `pestoura/hermes-vault` only. HSL depends on the
contract; it never receives or owns these Vault objects.

## 2. HSL repo changes are OUT OF SCOPE (item 2)

Repointing HSL signing/evidence code from the historical
`deployment/vault-lab-l1` transit to the shared `hsl-transit/hsl-signing` — plus
the three owner decisions recorded in spec §25 — is a **SEPARATE HSL-local plan**
owned by `pestoura/hermes-security-labs`:

- **Key continuity — §25.1.** Owner decides retain-verify-only / re-sign / define
  verify-continuity policy for the non-exportable `hermes-lab-l1-signer` key.
- **Network exposure — §25.2.** Owner confirms exactly how HSL reaches the shared
  service (bind address, port, TLS).
- **Cutover vs parallel-run — §25.3.** Owner decides decommission / read-only
  verify / parallel-run for `deployment/vault-lab-l1`.

`hermes-vault` does not write to `pestoura/hermes-security-labs` or any other
repository (INV-11). The HSL repointing is specified here as a boundary, not
performed.

## 3. #18 deferred (item 3)

The concrete `VaultCredentialProvider` adapter reconciles in the PR chain against
the provider-neutral capability contract (A3 / F1); it is **deferred** and **not
built in this repo**. It becomes the contract's Community/OSS F1 implementation,
not a generic `secret.read` (ADR-005). `hermes-vault` leaves the #18
implementation to the PR-chain/governance work.

## 4. No live promotion (item 4)

HSL may use the shared service **only** after `RESTORE_DRILL_PASS` +
`AUDIT_PASS` + owner sign-off, and only via the contract (fail-closed). No live
promotion is performed or implied in M1; promotion remains **NOT_RUN**.

## 5. Verification handoff (item 5)

HSL-side conformance is validated by reusing the negative-capability matrix (E4)
against the shared `hsl-signer` identity. `hermes-vault` owns the shared service
(the mounts/AppRole/policy); HSL owns its application logic. The E4 framework is
reusable across consumers and requires no namespace or live credential.

## 6. INV-11 / non-mutation boundary

This document does not write to `pestoura/hermes-security-labs` or any other
repo. References to `hermes-security-labs` are descriptive ownership-boundary
notes only. **No remote-mutating command (push, PR, or API call) is performed or
instructed here.** No Vault runtime, token, Shamir share, SecretID, or TLS
private material is referenced, generated, or read. **No credentials** and **no
secrets** are used in M1.

## 7. State — NOT_RUN

- Executing HSL repo changes (repointing from `deployment/vault-lab-l1`, §25.1/§25.2/§25.3
  owner decisions), building the #18 adapter, PR-chain reconciliation (#14-#18),
  and every Vault live/HITL action (restore drill, audit enable, init/unseal/root
  handling, SecretID issuance/wrapping, TLS private-key custody, production
  promotion sign-off) remain **NOT_RUN** and owner-gated.
- Any HSL / #18 / GitHub current-state observation above is **INHERITED / NOT
  independently re-verified** in M1 and must be **re-confirmed** by the owner
  before execution.

---

**Verification (repo-side):** `tests/plans/test_hsl_handoff_doc.py` asserts the
existence and required content of this file (10 checks: existence; required
markers; onboarding contract built here; HSL changes out-of-scope + INV-11;
#18 deferred to provider-neutral contract; no live promotion; verification
handoff via E4; INV-11 no remote-mutating command; inherited/not-re-verified/
NOT_RUN; no live/secret operations). Offline; no remote contact.

**External state:** NOT_RUN — HSL changes / #18 / PR governance / Vault live and
HITL actions must be reconfirmed by the owner before any execution.
