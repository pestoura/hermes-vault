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
#     (spec §20 key-continuity risk row / §25.1) before any later
#     freeze/decommission. Normative reference is spec §20 (the risk table that
#     carries the key-continuity row) plus §25.1 (the unresolved owner
#     decision); the "(§21)" pointer inside that spec table cell points at the
#     testing section and is not the location of the row itself. The runbook
#     Provenance block and this test both use §20/§25.1;
#   * that the two structural claims ("never promoted", "HSL main no longer
#     carries deployment/vault-lab-l1") are labelled as OBSERVATIONS inherited
#     from Task I1 / earlier read-only verification and explicitly NOT
#     re-verified in Task I2;
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
# 3b) The two structural claims must be labelled as INHERITED OBSERVATIONS
#     (from I1 / earlier read-only verification), explicitly NOT re-verified in
#     Task I2. They must not be presented as newly verified facts.
# ---------------------------------------------------------------------------
def test_runbook_labels_structural_claims_as_inherited_unverified_observations():
    text = _text()
    low = text.lower()

    assert "observation" in low, (
        "runbook must label the structural claims as observations, not verified facts"
    )
    assert "inherited" in low, (
        "runbook must state the observations are inherited (from I1 / earlier "
        "read-only verification), not established in I2"
    )
    assert "task i1" in low or "i1" in text, (
        "runbook must attribute the observations to Task I1 / earlier read-only "
        "verification"
    )
    assert "read-only" in low, (
        "runbook must state the observations came from read-only verification"
    )
    assert "not re-verified" in low or "not reverified" in low, (
        "runbook must state the observations were NOT re-verified in Task I2"
    )
    assert "i2" in low, (
        "runbook must scope the non-re-verification to Task I2"
    )

    # The claims must not be asserted as freshly verified facts in I2.
    for bad in (
        "structural facts, verified read-only",
        "newly verified",
    ):
        assert bad not in low, (
            f"runbook must not present the inherited observations as {bad!r}"
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
    assert "§20" in _text() or "§ 20" in _text(), (
        "runbook must cite the spec key-continuity risk reference (§20), not §21"
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
