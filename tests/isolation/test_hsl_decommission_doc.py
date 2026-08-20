# tests/isolation/test_hsl_decommission_doc.py
#
# Task I2 — Decommission/freeze of the HSL-owned deployment is DOCUMENTED ONLY.
#
# This test is the repo-side I2 GREEN evidence. It asserts that
# `docs/runbooks/hsl-decommission.md` exists and records:
#   * the three options: decommission / read-only verify / parallel-run;
#   * the current approved architectural ruling (direct ownership migration,
#     NO parallel live Vault, HSL deployment never promoted, HSL main no longer
#     carries `deployment/vault-lab-l1`);
#   * an explicit gate on the key-continuity OWNER DECISION / sign-off
#     (spec §21 risk row / §25.1) before any later freeze/decommission;
#   * that the actual HSL mutation is OUT OF SCOPE / NOT_RUN here.
#
# Offline/static only. No Vault started, no token/key/secret, no remote contact,
# no HSL mutation, nothing deleted. Placed next to the I1 ownership-boundary
# test because I2 is the same ownership-boundary concern (spec §15/§17, §17.4).
from pathlib import Path

_RUNBOOK = Path("docs/runbooks/hsl-decommission.md")


def _text() -> str:
    return _RUNBOOK.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) The documented-only artifact exists.
# ---------------------------------------------------------------------------
def test_hsl_decommission_runbook_exists():
    assert _RUNBOOK.is_file(), f"missing I2 runbook: {_RUNBOOK}"


# ---------------------------------------------------------------------------
# 2) The three options are all documented.
# ---------------------------------------------------------------------------
def test_runbook_lists_the_three_options():
    low = _text().lower()
    assert "decommission" in low, "runbook must document the decommission option"
    assert "read-only verify" in low, "runbook must document the read-only verify option"
    assert "parallel-run" in low or "parallel run" in low, (
        "runbook must document the parallel-run option"
    )


# ---------------------------------------------------------------------------
# 3) The current approved architectural ruling is stated.
# ---------------------------------------------------------------------------
def test_runbook_states_direct_ownership_migration_no_parallel_live_vault():
    text = _text()
    low = text.lower()
    assert "direct ownership migration" in low, (
        "runbook must state the approved ruling: direct ownership migration"
    )
    assert "no parallel live vault" in low, (
        "runbook must state the approved ruling: NO parallel live Vault"
    )
    assert "never promoted" in low, (
        "runbook must record that the HSL deployment was never promoted"
    )
    assert "deployment/vault-lab-l1" in text, (
        "runbook must name the HSL deployment path it rules on"
    )
    assert "no longer carries" in low, (
        "runbook must record that HSL main no longer carries deployment/vault-lab-l1"
    )


# ---------------------------------------------------------------------------
# 4) Key-continuity owner decision gate is explicit and blocks execution.
# ---------------------------------------------------------------------------
def test_runbook_gates_execution_on_key_continuity_owner_decision():
    low = _text().lower()
    assert "key-continuity" in low or "key continuity" in low, (
        "runbook must name the key-continuity decision"
    )
    assert "owner decision" in low, "runbook must require an owner decision"
    assert "sign-off" in low or "sign off" in low, "runbook must require owner sign-off"
    assert "§25.1" in _text() or "25.1" in _text(), (
        "runbook must cite the spec decision reference (§25.1)"
    )
    assert "gate" in low or "gated" in low, (
        "runbook must state the gate explicitly"
    )


# ---------------------------------------------------------------------------
# 5) Actual HSL mutation stays OUT OF SCOPE / NOT_RUN.
# ---------------------------------------------------------------------------
def test_runbook_keeps_hsl_mutation_out_of_scope_and_not_run():
    text = _text()
    low = text.lower()
    assert "not_run" in low or "not run" in low, (
        "runbook must record the live freeze/decommission as NOT_RUN"
    )
    assert "out of scope" in low or "out-of-scope" in low, (
        "runbook must record HSL mutation as out of scope"
    )
    assert "no hsl mutation" in low or "never writes" in low or "no hsl write" in low, (
        "runbook must state that no HSL mutation is performed"
    )
    assert "hermes-vault" in low, "runbook must name hermes-vault as the owner repo"


# ---------------------------------------------------------------------------
# 6) The runbook records only; it must not carry executable live/secret ops.
# ---------------------------------------------------------------------------
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
