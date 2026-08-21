from pathlib import Path

RUNBOOK = Path('docs/runbooks/jit-admin-bootstrap.md')
EVIDENCE = Path('docs/evidence/2026-08-21-adr-022-live-acceptance.md')


def test_runbook_marks_adr022_live_accepted_without_promoting_unsealed_ready():
    text = RUNBOOK.read_text()
    assert 'VERIFIED_ADR022_LIVE_ACCEPTED' in text
    assert 'restore drill' in text.lower()
    assert 'UNSEALED_READY' in text
    assert 'NOT_RUN' in text


def test_live_acceptance_evidence_is_safe_and_complete():
    assert EVIDENCE.is_file()
    text = EVIDENCE.read_text()
    required = [
        'VERIFIED_ADR022_LIVE_ACCEPTED',
        'AUDIT_PASS',
        'JIT_PROOF_PASS',
        'ROOT_REVOKED',
        'POST_REVOKE_SMOKE_PASS',
        'db0c98bfc7e5a8cf3d9b19394cc64be6c0dc643f',
        '32490916043',
        'restore drill',
        'consumer bootstrap',
    ]
    for item in required:
        assert item in text
    forbidden = ['hvs.', 'SecretID=', 'BEGIN PRIVATE KEY', 'BEGIN ENCRYPTED PRIVATE KEY']
    for item in forbidden:
        assert item not in text
