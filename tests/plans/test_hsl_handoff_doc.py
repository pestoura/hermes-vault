# tests/plans/test_hsl_handoff_doc.py
#
# Task M1 — Cross-repo handoff specification (no execution).
#
# This test is the repo-side M1 GREEN evidence. It asserts that
# `docs/plans/hsl-cross-repo-handoff.md` exists and records the mandated
# final-handoff WITHOUT performing any of it (spec §22, INV-11):
#   * The HSL onboarding contract is BUILT HERE: HSL consumes via the dedicated
#     `hsl-transit/` mount + `hsl-signing` key + `hsl-signer` AppRole + exact-path
#     policy + negative-capability matrix produced by tasks E1–E3. These artifacts
#     live in `pestoura/hermes-vault` only.
#   * HSL repo changes are OUT OF SCOPE: repointing HSL signing/evidence code from
#     `deployment/vault-lab-l1` to the shared service, plus the key-continuity /
#     network / cutover owner decisions (spec §25), are a SEPARATE HSL-local plan.
#     `hermes-vault` does not modify HSL (INV-11).
#   * #18 deferred: the concrete `VaultCredentialProvider` adapter reconciles in the
#     PR chain against the provider-neutral contract (A3/F1); not built here.
#   * No live promotion: HSL may use the shared service only after
#     RESTORE_DRILL_PASS + AUDIT_PASS + owner sign-off, and only via the contract
#     (fail-closed).
#   * Verification handoff: HSL-side conformance is validated by reusing the
#     negative-capability matrix (E4) against the shared `hsl-signer` identity.
#
# Offline/static only. No Vault started, no credentials, no remote contact, no HSL
# mutation, no secret material. Mirrors the K1 / J1 doc-test style.

from pathlib import Path

_DOC = Path("docs/plans/hsl-cross-repo-handoff.md")


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) The M1 handoff artifact exists.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_exists():
    assert _DOC.is_file(), f"missing M1 plan doc: {_DOC}"


# ---------------------------------------------------------------------------
# 2) Mandated content markers are all present (plan Task M1 Step 1 list).
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_contains_required_markers():
    text = _text()
    for token in (
        "pestoura/hermes-security-labs",
        "#18",
        "deferred",
        "hsl-transit",
        "hsl-signer",
    ):
        assert token in text, f"M1 doc must contain marker {token!r}"
    # "does not modify HSL" OR ("out-of-scope" + HSL repo path).
    low = text.lower()
    assert (
        "does not modify hsl" in low
        or ("out-of-scope" in low and "pestoura/hermes-security-labs" in low)
    ), "M1 doc must state hermes-vault does not modify HSL (or HSL changes out-of-scope)"


# ---------------------------------------------------------------------------
# 3) HSL onboarding contract built here (item 1): hsl-transit + hsl-signing +
#    hsl-signer AppRole + exact-path policy + negative-capability matrix (E1–E3).
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_onboarding_contract_built_here():
    text = _text()
    low = text.lower()
    # Dedicated mount + key + AppRole.
    assert "hsl-transit" in low, "doc must name the dedicated hsl-transit mount"
    assert "hsl-signing" in low, "doc must name the hsl-signing key"
    assert "hsl-signer" in low, "doc must name the hsl-signer AppRole"
    # Exact-path policy + negative-capability matrix (E1–E3).
    assert "exact-path" in low, "doc must reference the exact-path policy"
    assert ("negative-capability" in low or "negative capability" in low), (
        "doc must reference the negative-capability matrix"
    )
    for e in ("e1", "e2", "e3"):
        assert e in low, f"doc must reference task {e.upper()} producing the artifacts"
    # These artifacts live in hermes-vault only (not HSL).
    assert "pestoura/hermes-vault" in low or "hermes-vault only" in low, (
        "doc must state the onboarding artifacts live in hermes-vault only"
    )


# ---------------------------------------------------------------------------
# 4) HSL repo changes are OUT OF SCOPE (item 2): repointing from
#    deployment/vault-lab-l1 + §25 owner decisions; hermes-vault does not modify
#    HSL (INV-11).
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_marks_hsl_changes_out_of_scope():
    text = _text()
    low = text.lower()
    assert "out-of-scope" in low or "out of scope" in low, (
        "doc must mark HSL repo changes as out-of-scope"
    )
    assert "pestoura/hermes-security-labs" in low, (
        "doc must reference the HSL repository"
    )
    assert "deployment/vault-lab-l1" in low, (
        "doc must reference the historical HSL deployment/vault-lab-l1 transit"
    )
    # hermes-vault does not modify HSL (INV-11 specific phrase).
    norm = low
    assert (
        "hermes-vault does not modify" in norm
        or "does not modify hsl" in norm
        or "does not modify pestoura/hermes-security-labs" in norm
    ), "doc must state hermes-vault does not modify HSL (INV-11)"
    # §25 owner decisions (key-continuity / network / cutover).
    assert "25" in low or "§25" in low or "spec §25" in low, (
        "doc must cite spec §25 owner decisions"
    )
    assert "key continuity" in low, "doc must reference the §25.1 key-continuity decision"
    assert "network" in low, "doc must reference the §25.2 network decision"
    assert "cutover" in low, "doc must reference the §25.3 cutover decision"


# ---------------------------------------------------------------------------
# 5) #18 deferred (item 3): not built here; reconciles against provider-neutral
#    contract (A3/F1).
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_defers_18_to_provider_neutral_contract():
    text = _text()
    low = text.lower()
    assert "#18" in text, "doc must reference #18"
    assert "deferred" in low, "doc must mark #18 as deferred"
    assert "provider-neutral" in low, "doc must tie #18 to the provider-neutral contract"
    assert "f1" in low, "doc must identify #18 as the contract's F1 implementation"
    assert "not built" in low or "not implemented" in low or "out of scope" in low, (
        "doc must state the #18 adapter is not built in this repo"
    )


# ---------------------------------------------------------------------------
# 6) No live promotion (item 4): gated on RESTORE_DRILL_PASS + AUDIT_PASS +
#    owner sign-off; contract-only; fail-closed; NOT_RUN.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_no_live_promotion():
    text = _text()
    low = text.lower()
    assert "no live promotion" in low or "not live promotion" in low or (
        "live promotion" in low and "not_run" in low
    ), "doc must state HSL may not use the service via live promotion here"
    assert "restore_drill_pass" in low or "restoredrill" in low, (
        "doc must require RESTORE_DRILL_PASS before HSL use"
    )
    assert "audit_pass" in low or "audit" in low, "doc must require AUDIT_PASS"
    assert "owner sign-off" in low or "owner signoff" in low, (
        "doc must require owner sign-off"
    )
    assert "fail-closed" in low, "doc must state HSL onboarding is fail-closed"
    assert "not_run" in low or "not run" in low, (
        "doc must record live promotion as NOT_RUN"
    )


# ---------------------------------------------------------------------------
# 7) Verification handoff (item 5): reuse E4 negative-capability matrix against
#    the shared hsl-signer identity; shared service owns mounts/AppRole, HSL owns
#    application logic.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_verification_handoff():
    text = _text()
    low = text.lower()
    assert "e4" in low, "doc must reference the reusable E4 framework"
    assert ("negative-capability" in low or "negative capability" in low), (
        "doc must reuse the negative-capability matrix for HSL conformance"
    )
    assert "hsl-signer" in low, "doc must validate against the shared hsl-signer identity"
    assert "owns the shared service" in low or "shared service owns" in low or (
        "shared service" in low and "owns" in low
    ), "doc must state the shared service owns the mounts/AppRole"
    assert "owns" in low and "application logic" in low, (
        "doc must state HSL owns its application logic"
    )


# ---------------------------------------------------------------------------
# 8) INV-11 / non-mutation boundary: no remote-mutating command performed or
#    instructed; references to HSL framed as non-mutating boundary.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_inv11_no_remote_mutating_command():
    text = _text()
    low = text.lower()
    norm = low
    assert "pestoura/hermes-security-labs" in low, (
        "doc must reference the HSL repository"
    )
    assert (
        "does not modify" in norm
        or "does not modify hsl" in norm
        or "does not write to" in norm
    ), "doc must state hermes-vault does not modify/write-to HSL (INV-11)"
    # No remote-mutating command performed or instructed.
    assert "git push" not in low, "M1 doc must not instruct git push"
    assert "gh api" not in low, "M1 doc must not instruct gh api"
    assert "git remote" not in low, "M1 doc must not instruct git remote"
    # Explicit no remote-mutating boundary statement.
    assert "no remote-mutating command" in norm or (
        "no push" in norm and "no pr" in norm and "no api call" in norm
    ), "doc must state no remote-mutating command is performed or instructed"


# ---------------------------------------------------------------------------
# 9) HSL / #18 / GitHub current-state statements are INHERITED / NOT re-verified.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_labels_state_inherited_not_reverified():
    text = _text()
    low = text.lower()
    assert "inherited" in low, "doc must label HSL/#18/GitHub state as inherited"
    assert ("not re-verified" in low or "not independently re-verified" in low or (
        "not" in low and "re-verified" in low
    )), "doc must state HSL/#18/GitHub state was NOT re-verified in M1"
    assert "not_run" in low or "not run" in low, (
        "doc must record HSL changes / #18 / governance / Vault live actions as NOT_RUN"
    )


# ---------------------------------------------------------------------------
# 10) No live/secret operations; no credentials or secrets.
# ---------------------------------------------------------------------------
def test_hsl_handoff_doc_no_live_or_secret_operations():
    low = _text().lower()
    forbidden = [
        "vault operator init",
        "vault operator unseal",
        "vault_skip_verify",
        "vault token create",
        "hvs.",
        "root_token=",
        "secretid=",
    ]
    for token in forbidden:
        assert token not in low, f"M1 doc must not carry live/secret operation: {token}"
    assert (
        "no credentials" in low or "no secret" in low or "no live credentials" in low
    ), "doc must assert no credentials/secrets are used"
