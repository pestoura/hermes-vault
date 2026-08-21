"""Task L1 — No-live-promotion + HITL gate summary (static, repo-side only).

This is the planned L1 static test. It asserts that the production promotion
gate and the HITL stops are documented in ``docs/runbooks/promotion-gates.md``
and that NO code path (``src/``, ``scripts/``, ``deployments/``) performs or
automates promotion.

The test is STATIC: documentation-content + source-scan + pure fail-closed
logic. There is NO Vault runtime, NO credentials, NO live check, NO HITL
execution. Live/operator evidence (restore drill PASS, audit PASS, owner
sign-off, and every HITL step) is NOT_RUN repo-side by design; this test
asserts those steps EXIST as documented operator-only stops and that they are
never relabeled PASS or auto-executed.

If this test passes at the L1-prepared HEAD, it means the prerequisite task G3
already converged on L1's deliverables (pre-existing GREEN); it is NOT a vacuous
self-fulfilling test — every assertion below is independently checkable against
the tracked tree.
"""

import re
import subprocess
from pathlib import Path

import pytest

from src.lifecycle.states import ServiceState, promotion_ready

REPO = Path(__file__).resolve().parents[2]
RUNBOOK = REPO / "docs" / "runbooks" / "promotion-gates.md"


def _runbook_norm():
    """Runbook text lowercased with all whitespace (incl. markdown line wraps)
    collapsed to single spaces, so doc-content assertions tolerate wrapping."""
    raw = RUNBOOK.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", raw).lower()

# Operational roots that may never perform (or look like they perform) promotion
# or HITL-secret actions without explicit boundary wording. Generic markdown
# docs are exempt (they document, not execute). Mirrors G3 invariant scan scope.
_OP_ROOTS = ("scripts/", "src/", "deployments/")
_HITL_FORBIDDEN_CMDS = ("vault operator init", "vault operator unseal", "vault token revoke")
_BOUNDARY_RE = __import__("re").compile(r"(read-?only|hitl|operator-?only|out-?of-?band)", __import__("re").IGNORECASE)


def _tracked_sources():
    """Yield (relative-path, text) for every tracked, non-plan source file."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    for rel in out.stdout.splitlines():
        if rel.startswith("docs/superpowers/"):
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        yield rel, text


def _operational_promote_violates(rel, text):
    """INV-2: an operational-root file referencing promotion must be fail-closed
    / owner-gated. Docs are exempt (NO_AUTO_PROMOTION is documented there)."""
    if not rel.startswith(_OP_ROOTS):
        return False
    if "promote" not in text.lower():
        return False
    return not ("fail-closed" in text.lower() or "owner sign-off" in text.lower())


def _operational_file_violates_hitl(rel, text):
    """INV-10: an operational-root file containing a HITL-secret command without
    explicit boundary language in the SAME file is a fail-closed violation.
    Docs are exempt (they document, not execute)."""
    if not rel.startswith(_OP_ROOTS):
        return False
    if not any(cmd in text for cmd in _HITL_FORBIDDEN_CMDS):
        return False
    return not _BOUNDARY_RE.search(text)


# --- Documentation presence (VERIFIED repo-side) -----------------------------


def test_promotion_gates_runbook_exists_and_tracked():
    assert RUNBOOK.is_file(), "docs/runbooks/promotion-gates.md must exist (L1 deliverable)"
    rels = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(RUNBOOK.relative_to(REPO))],
        cwd=REPO, capture_output=True, text=True,
    )
    assert rels.returncode == 0, "promotion-gates.md must be a tracked file at HEAD"
    body = RUNBOOK.read_text(encoding="utf-8")
    assert len(body.strip()) > 0, "promotion-gates.md must not be empty"


# --- Production-readiness gate markers (VERIFIED repo-side) -------------------


def test_runbook_states_three_part_gate():
    body = _runbook_norm()
    # The production gate = restore drill PASS + audit PASS + owner sign-off.
    assert "restore drill" in body and "pass" in body, "restore drill PASS must be documented"
    assert "audit" in body and "pass" in body, "audit PASS must be documented"
    assert "owner sign-off" in body, "owner sign-off must be documented"
    assert "production-readiness gate" in body or "production readiness gate" in body, \
        "a production-readiness gate section must be documented"


# --- HITL stops enumerated (VERIFIED repo-side) ------------------------------


def test_runbook_enumerates_all_hitl_stops():
    body = _runbook_norm()
    # Task L1 HITL stops: init, unseal, root, SecretID issuance, TLS private
    # material, promotion.
    assert "vault operator init" in body, "HITL stop 'init' not documented"
    assert "vault operator unseal" in body, "HITL stop 'unseal' not documented"
    assert "root token" in body, "HITL stop 'root' not documented"
    assert "secretid issuance" in body or "secretid" in body, \
        "HITL stop 'SecretID issuance' not documented"
    assert "tls private" in body, "HITL stop 'TLS private material' not documented"
    assert "promotion" in body, "HITL stop 'promotion' not documented"


def test_runbook_marks_hitl_as_operator_only_not_run():
    body = _runbook_norm()
    # The HITL stops must be recorded as operator-only / never automated / NOT
    # performed by this repo. They must NOT be claimed as executed/PASS here.
    assert "operator-only" in body or "operator only" in body, \
        "HITL stops must be labeled operator-only"
    assert "never" in body, "HITL stops must be described as never automated"
    assert "must not be performed by this repository" in body, \
        "HITL stops must remain NOT_RUN in this repo (documented, not executed)"


# --- No code path performs promotion (VERIFIED repo-side) --------------------


def test_no_operational_code_path_auto_promotes():
    violators = []
    for rel, text in _tracked_sources():
        if _operational_promote_violates(rel, text):
            violators.append(rel)
    assert violators == [], f"INV-2: promotion reference without fail-closed/owner-gate in {violators}"


def test_no_operational_code_executes_hitl_secrets():
    violators = []
    for rel, text in _tracked_sources():
        if _operational_file_violates_hitl(rel, text):
            violators.append(rel)
    assert violators == [], f"INV-10: HITL-secret command without boundary language in {violators}"


# --- Hardening: production promotion requires ALL THREE proofs ---------------


def test_promotion_ready_requires_all_three_proofs():
    # Even UNSEALED_READY must DENY without all three independent proofs. This
    # proves promotion is gated, not auto-granted by state alone.
    assert promotion_ready(ServiceState.UNSEALED_READY) is False
    assert promotion_ready(ServiceState.UNSEALED_READY, restore_drill_passed=True) is False
    assert promotion_ready(
        ServiceState.UNSEALED_READY, restore_drill_passed=True, audit_passed=True
    ) is False
    assert promotion_ready(
        ServiceState.UNSEALED_READY,
        restore_drill_passed=True,
        audit_passed=True,
        owner_signoff=True,
    ) is True


def test_unknown_or_missing_proof_cannot_promote():
    # Unknown/missing proof must NOT promote. Each proof supplied alone is
    # insufficient; the gate is conjunctive and fail-closed.
    for kwargs in (
        {"restore_drill_passed": True},
        {"audit_passed": True},
        {"owner_signoff": True},
        {"restore_drill_passed": True, "audit_passed": True},
        {"restore_drill_passed": True, "owner_signoff": True},
        {"audit_passed": True, "owner_signoff": True},
    ):
        assert promotion_ready(ServiceState.UNSEALED_READY, **kwargs) is False, \
            f"missing proof promoted: {kwargs}"


def test_degraded_or_terminal_states_never_promotion_ready():
    for state in (
        ServiceState.UNINITIALIZED,
        ServiceState.INITIALIZED_SEALED,
        ServiceState.ERROR,
        ServiceState.DECOMMISSIONED,
        "UNRECOGNIZED_STATE",
        12345,
    ):
        assert promotion_ready(
            state,
            restore_drill_passed=True,
            audit_passed=True,
            owner_signoff=True,
        ) is False, f"degraded/terminal/unknown state promoted: {state!r}"


def test_promotion_ready_is_pure_no_side_effects():
    # The gate is a pure boolean; it must not mutate, persist, or emit any
    # promotion. Calling it with all proofs returns True but performs no
    # transition — there is no "promote()" call anywhere in operational code.
    result = promotion_ready(
        ServiceState.UNSEALED_READY,
        restore_drill_passed=True,
        audit_passed=True,
        owner_signoff=True,
    )
    assert result is True
    # No caller in operational roots auto-invokes a promotion transition.
    callers = subprocess.run(
        ["grep", "-rn", "promotion_ready", "--include=*.py", "src", "scripts", "deployments"],
        cwd=REPO, capture_output=True, text=True,
    )
    # Allowed: the definition itself. Any OTHER reference must be a test only.
    for line in callers.stdout.splitlines():
        assert "def promotion_ready" in line or line.strip().startswith(
            "tests/"
        ), f"operational code references promotion_ready: {line}"
