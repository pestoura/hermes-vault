# tests/audit/test_audit_redaction_marker_guard.py
#
# FINAL FIX WAVE 2 — TDD regression guard.
#
# Repo-side hardening: tests/audit/test_audit_redaction.py must keep the 9
# static/redaction-proof tests collectable under the unattended marker
# `-m 'not hitl'`. Only the 2 live-Vault HITL tests
# (test_audit_device_enabled, test_audit_redacts_secret_material) may carry
# the @pytest.mark.hitl marker. A module-level `pytestmark = pytest.mark.hitl`
# previously deselected ALL 11 audit tests under `-m 'not hitl'`, so the 9
# static redaction contracts were never executed in unattended/CI runs.
#
# This guard fails now (RED) and passes after the module-level marker is
# removed and the 2 live tests are individually annotated.
#
# No Vault runtime, no secrets, no scanner-sensitive literals.
import pytest


# The two tests that genuinely require a live operator-initialized Vault.
_LIVE_HITL_TESTS = {
    "test_audit_device_enabled",
    "test_audit_redacts_secret_material",
}

# The 9 static/offline redaction + audit-path contracts that MUST run under
# `-m 'not hitl'` (no Vault, no token, no secret material handled).
_STATIC_AUDIT_TESTS = {
    "test_enable_audit_script_present_and_idempotent",
    "test_enable_audit_script_is_operator_hitl_only",
    "test_redaction_layer_redacts_secret_material",
    "test_synthetic_audit_sample_redacts_no_secret_leakage",
    "test_synthetic_audit_sample_is_explicitly_fictitious",
    "test_redact_removes_recovery_key_value",
    "test_redact_removes_unseal_key_value",
    "test_redact_removes_unseal_key_1_value",
    "test_redact_removes_private_key_pem_value",
}


def _collect_not_hitl(target):
    import subprocess
    import sys

    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            "not hitl",
            target,
        ],
        capture_output=True,
        text=True,
    )
    names = set()
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith(target + "::"):
            names.add(line.split("::", 1)[1])
    return names


def test_static_audit_redaction_tests_collected_under_not_hitl():
    # The 9 static redaction proofs must be collected when running the
    # unattended marker `-m 'not hitl'`. If the module-level HITL marker is
    # reintroduced, this fails (all 11 deselected).
    collected = _collect_not_hitl("tests/audit/test_audit_redaction.py")
    missing = _STATIC_AUDIT_TESTS - collected
    assert not missing, f"static audit tests deselected under -m 'not hitl': {sorted(missing)}"


def test_only_live_vault_audit_tests_are_hitl():
    # Under `-m 'hitl'` only the 2 live-Vault tests should be selected; the 9
    # static tests must NOT be marked HITL.
    import subprocess
    import sys

    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            "hitl",
            "tests/audit/test_audit_redaction.py",
        ],
        capture_output=True,
        text=True,
    )
    hitl = set()
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("tests/audit/test_audit_redaction.py::"):
            hitl.add(line.split("::", 1)[1])

    assert hitl == _LIVE_HITL_TESTS, (
        f"unexpected HITL audit test set: got {sorted(hitl)}, "
        f"expected {sorted(_LIVE_HITL_TESTS)}"
    )
