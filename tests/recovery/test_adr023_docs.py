from pathlib import Path

SPEC = Path("docs/specs/2026-08-18-hermes-shared-vault-service-design.md")
RECOVERY = Path("docs/09-bootstrap-recovery.md")
ROADMAP = Path("docs/12-implementation-roadmap.md")
RUNBOOK = Path("docs/runbooks/restore-drill.md")
EVIDENCE = Path("docs/evidence/2026-08-21-adr-023-live-acceptance.md")


def test_spec_records_adr022_and_adr023_live_acceptance():
    text = SPEC.read_text()
    top = "\n".join(text.splitlines()[:12])
    assert "VERIFIED_ADR022_LIVE_ACCEPTED" in top
    assert "VERIFIED_ADR023_LIVE_ACCEPTED" in top
    assert "RESTORE_DRILL_PASS" in top and "VERIFIED" in top
    assert "first-consumer acceptance" in top and "NOT_RUN" in top
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


def test_roadmap_marks_live_restore_completed_and_consumer_still_open():
    text = ROADMAP.read_text()
    assert "VERIFIED_ADR023_LIVE_ACCEPTED" in text
    assert "isolated restore drill harness" in text.lower()
    assert "- [x] restore drill efetuado;" in text
    assert "RESTORE_DRILL_PASS" in text
    assert "first consumer" in text.lower()


def test_runbook_records_live_restore_completion_without_promoting_consumer():
    text = RUNBOOK.read_text()
    assert "VERIFIED_ADR023_LIVE_ACCEPTED" in text
    assert "RESTORE_DRILL_PASS" in text
    assert "first-consumer" in text
    assert "UNSEALED_READY" in text
    assert "snapshot-force" in text
    assert "original shares" in text


def test_adr023_live_evidence_is_sanitized_and_complete():
    text = EVIDENCE.read_text()
    for marker in (
        "VERIFIED_ADR023_LIVE_ACCEPTED",
        "RESTORE_DRILL_PASS",
        "RESTORE_ACCEPTANCE_PASS",
        "RESTORE_TEARDOWN_PASS",
        "CI_EXACT_SHA_PASS",
        "zero restore containers",
    ):
        assert marker in text
    for forbidden in ("Unseal Key", "Root Token", "VAULT_TOKEN=", "BEGIN PRIVATE KEY"):
        assert forbidden not in text
