# tests/plans/test_hsl_boundary_doc.py
#
# HSL cross-repo migration boundary after owner resolutions ADR-018..ADR-021.
# Offline/static only. No Vault, credentials, remote mutation, or HSL write.
from pathlib import Path
import re

_DOC = Path("docs/plans/hsl-consumer-migration-boundary.md")


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


def test_hsl_boundary_doc_exists():
    assert _DOC.is_file(), f"missing HSL boundary doc: {_DOC}"


def test_hsl_boundary_doc_contains_resolved_target_contract():
    low = _text().lower()
    for token in (
        "pestoura/hermes-security-labs",
        "deployment/vault-lab-l1",
        "hsl-transit/hsl-signing",
        "verify-only",
        "hermes-security-plane",
        "hermes-vault",
        "controlled parallel-run",
        "not_run",
        "inv-11",
    ):
        assert token in low, f"boundary doc must contain marker {token!r}"


def test_hsl_boundary_doc_records_section_25_as_resolved():
    text = _text()
    low = text.lower()
    for ref in ("25.1", "25.2", "25.3", "25.4", "25.5"):
        assert ref in low
    for adr in ("ADR-018", "ADR-019", "ADR-020", "ADR-021"):
        assert adr.lower() in low
    assert "resolved" in low
    assert "owner decision required" not in low, (
        "the structural choices are now resolved; only live/HITL execution remains gated"
    )


def test_hsl_boundary_doc_marks_migration_separate_and_out_of_repo():
    low = _text().lower()
    assert "separate" in low
    assert "not implemented in hermes-vault" in low or "not implemented here" in low
    assert "deployment/vault-lab-l1" in low
    assert "hsl-transit/hsl-signing" in low
    assert "verify-only" in low


def test_hsl_boundary_doc_defines_acceptance_before_cutover():
    text = _text()
    for gate in (
        "AUDIT_PASS",
        "RESTORE_DRILL_PASS",
        "TLS_CONNECTIVITY_PASS",
        "HSL_ISOLATION_PASS",
        "SIGN_VERIFY_PASS",
    ):
        assert gate in text
    assert "SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY" in text
    assert "LEGACY_VERIFY_RETIRED" in text


def test_hsl_boundary_doc_hermes_vault_owns_and_does_not_modify_hsl():
    low = _text().lower()
    norm = re.sub(r"[`*]", "", re.sub(r"\s+", " ", low))
    assert "hermes-vault owns" in norm or "owns the shared service" in norm
    assert "hermes-vault does not modify pestoura/hermes-security-labs" in norm
    assert "inv-11" in norm


def test_hsl_boundary_doc_labels_hsl_state_inherited_not_reverified():
    low = _text().lower()
    assert "inherited" in low
    assert "not re-verified" in low or "not independently re-verified" in low
    assert "re-confirm" in low or "reconfirm" in low


def test_hsl_boundary_doc_no_mutation_no_credentials_no_secrets():
    low = _text().lower()
    assert "git push" not in low
    assert "gh api" not in low
    assert "git remote" not in low
    for token in (
        "vault operator init",
        "vault operator unseal",
        "vault_skip_verify",
        "vault token create",
        "hvs.",
        "root_token=",
        "secretid",
    ):
        assert token not in low, f"boundary doc must not carry live/secret operation: {token}"
    assert "no credentials" in low or "no secret" in low or "no live credentials" in low


def test_hsl_boundary_doc_inv11_no_remote_mutating_command_performed_or_instructed():
    low = _text().lower()
    norm = re.sub(r"[`*]", "", re.sub(r"\s+", " ", low))
    assert "no remote-mutating command" in norm
    assert "push, pr, or api call" in norm
    assert "performed" in norm and "instructed" in norm
