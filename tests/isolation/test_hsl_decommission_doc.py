# tests/isolation/test_hsl_decommission_doc.py
#
# HSL decommission/continuity governance after owner resolution on 2026-08-21.
# Offline/static only: no Vault, no secrets, no remote HSL mutation.
from pathlib import Path


_RUNBOOK = Path("docs/runbooks/hsl-decommission.md")


def _text() -> str:
    return _RUNBOOK.read_text(encoding="utf-8")


def test_hsl_decommission_runbook_exists():
    assert _RUNBOOK.is_file(), f"missing runbook: {_RUNBOOK}"


def test_runbook_states_controlled_parallel_run_as_current_ruling():
    text = _text()
    low = text.lower()
    assert "controlled parallel-run" in low or "parallel-run controlado" in low
    assert "shared_sign_active_legacy_verify_only" in low
    assert "verify-only" in low
    assert "adr-020" in low
    assert "superseded" in low
    assert "no parallel live vault" in low, (
        "historical direct-migration ruling must remain visible as superseded provenance"
    )


def test_runbook_records_key_continuity_as_resolved_not_open():
    low = _text().lower()
    assert "adr-018" in low
    assert "resolved" in low
    assert "hermes-lab-l1-signer" in low
    assert "verify-only" in low
    assert "bulk re-sign" in low or "bulk re-signing" in low


def test_runbook_preserves_old_hsl_observations_as_historical_unverified_context():
    low = _text().lower()
    assert "historical observation" in low or "historical observations" in low
    assert "inherited" in low
    assert "not re-verified" in low or "not reverified" in low
    assert "never promoted" in low
    assert "no longer carries" in low
    assert "does not override" in low or "do not override" in low


def test_runbook_defines_cutover_acceptance_and_retirement_boundaries():
    text = _text()
    for gate in (
        "AUDIT_PASS",
        "RESTORE_DRILL_PASS",
        "TLS_CONNECTIVITY_PASS",
        "HSL_ISOLATION_PASS",
        "SIGN_VERIFY_PASS",
    ):
        assert gate in text
    assert "LEGACY_VERIFY_RETIRED" in text
    assert "new legacy signing" in text.lower() or "legacy signing" in text.lower()


def test_runbook_keeps_hsl_mutation_out_of_scope_and_not_run():
    low = _text().lower()
    assert "not_run" in low or "not run" in low
    assert "out of scope" in low or "out-of-scope" in low
    assert "no hsl mutation" in low or "never writes" in low or "no hsl write" in low
    assert "pestoura/hermes-security-labs" in low


def test_runbook_carries_no_live_or_secret_operations():
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
        assert token not in low, f"runbook must not carry live/secret operation: {token}"
