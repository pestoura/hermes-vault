from pathlib import Path

SPEC = Path("docs/specs/2026-08-18-hermes-shared-vault-service-design.md")
RECOVERY = Path("docs/09-bootstrap-recovery.md")
ROADMAP = Path("docs/12-implementation-roadmap.md")
RUNBOOK = Path("docs/runbooks/restore-drill.md")


def test_spec_records_adr022_live_acceptance_and_adr023_repo_ready_only():
    text = SPEC.read_text()
    top = "\n".join(text.splitlines()[:12])
    assert "VERIFIED_ADR022_LIVE_ACCEPTED" in top
    assert "ADR023_REPO_READY_LIVE_HITL_PENDING" in top
    assert "RESTORE_DRILL_PASS" in top and "NOT_RUN" in top
    assert "UNSEALED_READY" in top and "not" in top.lower()


def test_spec_recovery_model_is_network_none_and_force_restore_hitl_only():
    text = SPEC.read_text()
    section = text.split("## 10. Backup and recovery", 1)[1].split("## 11.", 1)[0]
    for marker in ("ADR-023", "network=none", "snapshot-force", "original Shamir", "docs/runbooks/restore-drill.md"):
        assert marker in section
    assert "automation enters Shamir" not in section

def test_recovery_doc_points_to_adr023_operator_handoff():
    text = RECOVERY.read_text()
    assert "ADR-023" in text
    assert "docs/runbooks/restore-drill.md" in text
    assert "network=none" in text
    assert "RESTORE_DRILL_PASS" in text
    assert "original Shamir" in text
    assert "HITL" in text


def test_roadmap_marks_harness_ready_but_live_restore_still_open():
    text = ROADMAP.read_text()
    assert "ADR023_REPO_READY_LIVE_HITL_PENDING" in text
    assert "isolated restore drill harness" in text.lower()
    assert "- [ ] restore drill efetuado;" in text
    assert "RESTORE_DRILL_PASS" in text


def test_runbook_never_claims_live_restore_before_hitl():
    text = RUNBOOK.read_text()
    assert "live restore remains `NOT_RUN`" in text
    assert "RESTORE_DRILL_PASS" in text
    assert "UNSEALED_READY" in text
    assert "snapshot-force" in text
    assert "original shares" in text
