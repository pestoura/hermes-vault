# tests/plans/test_pr_chain_doc.py
#
# Task J1 — Record PR-chain reconciliation (no execution).
#
# This test is the repo-side J1 GREEN evidence. It asserts that
# `docs/plans/pr-chain-cleanup.md` exists and records the mandated reconciliation
# strategy WITHOUT performing any of it (spec §18):
#   * Harvest reusable concepts from #14 -> #15 -> #16 (cherry-pick concepts only;
#     do NOT merge branches); align with the shared-service / provider-neutral design.
#   * #17 (`epic-03/credential-broker-core`) is SUPERSEDED ARCHITECTURE — DO NOT
#     MERGE; its closure/supersession is a governance action in the respective repo,
#     not an implementation step here.
#   * #18 (VaultCredentialProvider) is deferred and must align with the
#     provider-neutral capability contract (spec §14) — it becomes the contract's
#     Community/OSS implementation (F1), NOT a generic `secret.read` (ADR-005).
#   * hermes-vault owns the shared service; any PR re-asserting lab-dedicated
#     ownership is out of scope.
#   * Action: NONE in this plan.
#   * Every PR-state observation is labelled INHERITED from plan/spec §18 and
#     explicitly NOT re-verified against current GitHub state in J1; governance
#     execution stays NOT_RUN and owner-gated.
#
# Offline/static only. No Vault started, no credentials, no remote contact, no PR
# mutation, no secret material. Mirrors the I2 doc-test style (inherited / not
# re-verified / NOT_RUN observations, INV-11 non-mutating HSL boundary).
from pathlib import Path

_DOC = Path("docs/plans/pr-chain-cleanup.md")


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) The J1 strategy artifact exists.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_exists():
    assert _DOC.is_file(), f"missing J1 plan doc: {_DOC}"


# ---------------------------------------------------------------------------
# 2) The mandated content markers are all present (plan Step 1 list).
# ---------------------------------------------------------------------------
def test_pr_chain_doc_contains_required_markers():
    text = _text()
    for token in ("#14", "#15", "#16", "#17", "SUPERSEDED", "#18",
                  "provider-neutral", "deferred"):
        assert token in text, f"J1 doc must contain marker {token!r}"


# ---------------------------------------------------------------------------
# 3) #14 -> #15 -> #16 harvest is concept-only (no branch merge).
# ---------------------------------------------------------------------------
def test_pr_chain_doc_harvest_is_concept_only():
    text = _text()
    low = text.lower()
    assert "#14" in text and "#15" in text and "#16" in text, (
        "doc must reference the stacked PRs #14 -> #15 -> #16"
    )
    assert "harvest" in low, "doc must state the harvest intent"
    assert "cherry-pick" in low or "cherry pick" in low, (
        "doc must state concepts are cherry-picked, not merged"
    )
    assert "do not merge" in low or "not merge" in low or "without merging" in low, (
        "doc must state branches are NOT merged"
    )
    assert "provider-neutral" in low, (
        "doc must align the harvest with the provider-neutral design"
    )


# ---------------------------------------------------------------------------
# 4) #17 is SUPERSEDED ARCHITECTURE — DO NOT MERGE; governance-only closure.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_marks_17_superseded_do_not_merge():
    text = _text()
    low = text.lower()
    assert "superseded" in low, "doc must mark #17 as SUPERSEDED"
    assert "do not merge" in low, "doc must state #17 is DO NOT MERGE"
    assert "governance" in low, (
        "doc must frame #17 closure/supersession as a governance action"
    )
    assert "respective repo" in low or "respective repository" in low, (
        "doc must scope the #17 governance action to the respective repo"
    )
    assert "not an implementation step" in low or "not an implementation" in low, (
        "doc must state #17 closure is not an implementation step here"
    )


# ---------------------------------------------------------------------------
# 5) #18 deferred; aligns to provider-neutral F1 contract, NOT secret.read/ADR-005.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_defers_18_to_provider_neutral_contract():
    text = _text()
    low = text.lower()
    assert "#18" in text, "doc must reference #18"
    assert "deferred" in low, "doc must mark #18 as deferred"
    assert "provider-neutral" in low, "doc must tie #18 to the provider-neutral contract"
    assert "f1" in low, "doc must identify #18 as the contract's Community/OSS F1 impl"
    assert "secret.read" in low or "secret read" in low, (
        "doc must contrast #18 against a generic secret.read (ADR-005)"
    )
    assert "adr-005" in low, "doc must cite ADR-005 as the rejected alternative"


# ---------------------------------------------------------------------------
# 6) hermes-vault owns the shared service; lab-dedicated ownership PRs out of scope.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_hermes_vault_owns_shared_service():
    text = _text()
    low = text.lower()
    assert "owns the shared service" in low or "hermes-vault owns" in low, (
        "doc must state hermes-vault owns the shared service"
    )
    assert "out of scope" in low or "out-of-scope" in low, (
        "doc must mark lab-dedicated ownership PRs as out of scope"
    )


# ---------------------------------------------------------------------------
# 7) Action: NONE in this plan.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_action_is_none():
    text = _text()
    low = text.lower()
    assert "action: none" in low or "action: none in this plan" in low, (
        "doc must record 'Action: NONE in this plan'"
    )


# ---------------------------------------------------------------------------
# 8) All PR-state claims are INHERITED / NOT re-verified / NOT_RUN, owner-gated.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_labels_pr_state_as_inherited_not_reverified():
    text = _text()
    low = text.lower()
    assert "inherited" in low, (
        "doc must label PR-state observations as inherited from plan/spec §18"
    )
    assert "not re-verified" in low or "not reverified" in low, (
        "doc must state PR-state was NOT re-verified against current GitHub state"
    )
    assert "§18" in text or "spec §18" in low or "spec 18" in low, (
        "doc must cite spec §18 as the source of the inherited observations"
    )
    assert "not_run" in low or "not run" in low, (
        "doc must record governance execution as NOT_RUN"
    )
    assert "owner" in low, "doc must require owner reconfirmation before governance"


# ---------------------------------------------------------------------------
# 9) INV-11: HSL is referenced read-only / non-mutating.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_does_not_mutate_hsl():
    text = _text()
    low = text.lower()
    if "hermes-security-labs" in low:
        assert ("does not" in low or "does not modify" in low
                or "no hsl mutation" in low or "no hsl write" in low
                or "not modify" in low), (
            "INV-11: HSL reference must be framed as non-mutating boundary"
        )


# ---------------------------------------------------------------------------
# 10) The doc records only; it must not carry executable live/secret ops.
# ---------------------------------------------------------------------------
def test_pr_chain_doc_carries_no_live_or_secret_operations():
    low = _text().lower()
    forbidden = [
        "vault operator init",
        "vault operator unseal",
        "vault_skip_verify",
        "vault token create",
        "hvs.",
        "root_token=",
    ]
    for token in forbidden:
        assert token not in low, f"J1 doc must not carry live/secret operation: {token}"
