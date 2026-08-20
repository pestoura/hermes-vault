# tests/plans/test_hsl_boundary_doc.py
#
# Task K1 — Document the HSL consumer migration boundary (no execution).
#
# This test is the repo-side K1 GREEN evidence. It asserts that
# `docs/plans/hsl-consumer-migration-boundary.md` exists and records the
# mandated boundary WITHOUT performing any of it (spec §17, §19, §25):
#   * The actual HSL migration (repoint HSL signing/evidence from the historical
#     `deployment/vault-lab-l1` transit to the shared `hsl-transit/hsl-signing`,
#     OR retain a verify-only mount during transition) is a SEPARATE
#     cross-repo implementation plan in `pestoura/hermes-security-labs`.
#   * It is NOT implemented in hermes-vault (spec §17.5, §19, §25.1/§25.3).
#   * The three owner decisions required before execution are recorded:
#       - key continuity (spec §25.1)
#       - network exposure (spec §25.2)
#       - cutover vs parallel-run (spec §25.3)
#   * hermes-vault owns the shared service and never modifies HSL (INV-11).
#   * External migration execution stays NOT_RUN and owner-gated.
#   * Any HSL current-state observation is labelled INHERITED / NOT independently
#     re-verified in K1 and must be re-confirmed before execution.
#
# Offline/static only. No Vault started, no credentials, no remote contact, no HSL
# mutation, no secret material. Mirrors the J1 doc-test style.
from pathlib import Path
import re

_DOC = Path("docs/plans/hsl-consumer-migration-boundary.md")


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) The K1 boundary artifact exists.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_exists():
    assert _DOC.is_file(), f"missing K1 plan doc: {_DOC}"


# ---------------------------------------------------------------------------
# 2) Mandated content markers are all present (plan Task K1 content list).
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_contains_required_markers():
    text = _text()
    for token in (
        "pestoura/hermes-security-labs",
        "deployment/vault-lab-l1",
        "hsl-transit/hsl-signing",
        "verify-only",
        "not implemented in hermes-vault",
        "hermes-vault owns",
        "key continuity",
        "network exposure",
        "cutover vs parallel-run",
        "not_run",
        "inv-11",
    ):
        assert token in text.lower(), f"K1 doc must contain marker {token!r}"


# ---------------------------------------------------------------------------
# 3) Migration is SEPARATE cross-repo plan in HSL; not implemented in hermes-vault.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_marks_migration_separate_and_out_of_repo():
    text = _text()
    low = text.lower()
    assert "pestoura/hermes-security-labs" in low, (
        "doc must place the migration in pestoura/hermes-security-labs"
    )
    assert "separate" in low, "doc must call the migration a SEPARATE plan"
    assert "not implemented in hermes-vault" in low or "not implemented here" in low, (
        "doc must state the migration is NOT implemented in hermes-vault"
    )
    assert "deployment/vault-lab-l1" in low, (
        "doc must reference the historical HSL deployment/vault-lab-l1 transit"
    )
    assert "hsl-transit/hsl-signing" in low, (
        "doc must reference the shared hsl-transit/hsl-signing target"
    )
    assert "verify-only" in low, (
        "doc must enumerate the retained verify-only mount alternative"
    )


# ---------------------------------------------------------------------------
# 4) The three owner decisions (§25.1 / §25.2 / §25.3 aren't executed here).
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_records_three_owner_decisions():
    text = _text()
    low = text.lower()
    # key continuity §25.1
    assert "key continuity" in low, "doc must record the §25.1 key-continuity decision"
    assert "25.1" in low, "doc must cite spec §25.1"
    # network exposure §25.2
    assert "network exposure" in low, "doc must record the §25.2 network-exposure decision"
    assert "25.2" in low, "doc must cite spec §25.2"
    # cutover vs parallel-run §25.3
    assert "cutover vs parallel-run" in low, (
        "doc must record the §25.3 cutover vs parallel-run decision"
    )
    assert "25.3" in low, "doc must cite spec §25.3"
    assert "owner" in low, "doc must require owner decision for these gates"


# ---------------------------------------------------------------------------
# 5) hermes-vault owns the shared service; never modifies HSL (INV-11).
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_hermes_vault_owns_and_does_not_modify_hsl():
    text = _text()
    low = text.lower()
    # hermes-vault owns the shared service (spec §3, §15, §17, ADR-013).
    assert "hermes-vault owns" in low or "owns the shared service" in low, (
        "doc must state hermes-vault owns the shared service"
    )
    # Specific semantic phrase tying hermes-vault to "does not modify"
    # pestoura/hermes-security-labs (INV-11) — no loose precedence.
    norm = re.sub(r"[`*]", "", re.sub(r"\s+", " ", low))
    phrase = "hermes-vault does not modify pestoura/hermes-security-labs"
    assert phrase in norm, (
        "doc must state hermes-vault does not modify pestoura/hermes-security-labs (INV-11)"
    )
    assert "inv-11" in low, "doc must reference INV-11 scope boundary"


# ---------------------------------------------------------------------------
# 6) External migration execution is NOT_RUN and owner-gated.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_external_execution_is_not_run():
    text = _text()
    low = text.lower()
    assert "not_run" in low or "not run" in low, (
        "doc must record external migration execution as NOT_RUN"
    )
    assert "owner" in low, "doc must gate execution on owner decision/confirmation"


# ---------------------------------------------------------------------------
# 7) HSL current-state observations are INHERITED / NOT independently re-verified.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_labels_hsl_state_inherited_not_reverified():
    text = _text()
    low = text.lower()
    assert "inherited" in low, (
        "doc must label HSL current-state observations as inherited"
    )
    assert "not re-verified" in low or "not independently re-verified" in low or (
        "not independently" in low and "re-verified" in low
    ), "doc must state HSL state was NOT independently re-verified in K1"
    assert "re-confirm" in low or "reconfirm" in low or "re-confirmed" in low, (
        "doc must require re-confirmation before execution"
    )


# ---------------------------------------------------------------------------
# 8) No HSL/remote/Vault mutation; no credentials/secrets.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_no_mutation_no_credentials_no_secrets():
    low = _text().lower()
    # No remote-mutating instructions / HSL write.
    assert "git push" not in low, "K1 doc must not instruct git push"
    assert "gh api" not in low, "K1 doc must not instruct gh api"
    assert "git remote" not in low, "K1 doc must not instruct git remote"
    # No credentials / secret material.
    forbidden = [
        "vault operator init",
        "vault operator unseal",
        "vault_skip_verify",
        "vault token create",
        "hvs.",
        "root_token=",
        "secretid",
    ]
    for token in forbidden:
        assert token not in low, f"K1 doc must not carry live/secret operation: {token}"
    # Explicit no-credential / no-secret assertion.
    assert "no credentials" in low or "no secret" in low or "no live credentials" in low, (
        "doc must assert no credentials/secrets are used"
    )


# ---------------------------------------------------------------------------
# 9) INV-11 / non-mutation: no remote-mutating command is performed OR instructed.
# ---------------------------------------------------------------------------
def test_hsl_boundary_doc_inv11_no_remote_mutating_command_performed_or_instructed():
    low = _text().lower()
    norm = re.sub(r"[`*]", "", re.sub(r"\s+", " ", low))
    # INV-11 explicitly and grammatically states no remote-mutating command
    # (push, PR, or API call) is performed OR instructed here.
    assert "no remote-mutating command" in norm, (
        "INV-11 must state the no remote-mutating command boundary"
    )
    assert "push, pr, or api call" in norm, (
        "INV-11 must enumerate push / PR / API call as remote-mutating kinds"
    )
    assert ("performed" in norm and "instructed" in norm), (
        "INV-11 must state such commands are neither performed nor instructed here"
    )
