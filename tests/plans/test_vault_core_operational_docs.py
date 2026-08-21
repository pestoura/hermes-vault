from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOCS_INDEX = ROOT / "docs" / "README.md"
RUNTIME = ROOT / "docs" / "16-current-runtime-status.md"
EVIDENCE = ROOT / "docs" / "evidence" / "2026-08-22-vault-core-operational.md"
BACKUP_RUNBOOK = ROOT / "docs" / "runbooks" / "scheduled-snapshot.md"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_root_readme_declares_verified_core_runtime_not_blueprint():
    src = text(README)
    for marker in (
        "VAULT_CORE_OPERATIONAL",
        "Vault 1.21.4",
        "RESTORE_DRILL_PASS",
        "SCHEDULED_SNAPSHOT_PASS",
        "restart: unless-stopped",
        "FIRST_CONSUMER_BOOTSTRAP",
        "```mermaid",
        "actions/workflows/fast-gates.yml/badge.svg",
    ):
        assert marker in src
    assert "Production implementation has not started" not in src
    assert "architecture blueprint / not deployed" not in src


def test_runtime_ledger_and_live_evidence_are_canonical_and_sanitized():
    runtime = text(RUNTIME)
    evidence = text(EVIDENCE)
    for marker in (
        "VAULT_CORE_OPERATIONAL",
        "e4659af02898513eeebed6f68ca37cf7485ac979",
        "32537626664",
        "SCHEDULED_SNAPSHOT_PASS",
        "RESTORE_DRILL_PASS",
        "FIRST_CONSUMER_BOOTSTRAP",
        "JIT_SELF_REVOKE_REVALIDATION",
    ):
        assert marker in runtime
    for marker in (
        "VAULT_CORE_OPERATIONAL_RUNTIME_PASS",
        "SCHEDULED_SNAPSHOT_PASS",
        "VAULT_24X7_READY",
        "restart=unless-stopped",
        "zero runtime credential residue",
    ):
        assert marker in evidence
    import re
    combined = runtime + evidence
    patterns = (
        r"(?<![A-Za-z0-9_])hvs\.[A-Za-z0-9_-]{12,}",
        r"(?<![A-Za-z0-9_])s\.[A-Za-z0-9_-]{12,}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"Unseal Key \d+:",
    )
    for pattern in patterns:
        assert re.search(pattern, combined) is None


def test_resume_checklist_and_docs_index_match_current_state():
    resume = text(ROOT / "RESUME.md")
    checklist = text(ROOT / "IMPLEMENTATION-CHECKLIST.md")
    index = text(DOCS_INDEX)
    for marker in ("VAULT_CORE_OPERATIONAL", "FIRST_CONSUMER_BOOTSTRAP", "UNSEALED_READY"):
        assert marker in resume
    assert "Executar **Phase 0 — Discovery & prerequisites**" not in resume
    for marker in (
        "- [x] Configurar TLS.",
        "- [x] Configurar Integrated Storage.",
        "- [x] Configurar audit device.",
        "- [x] Snapshot automático.",
        "- [x] Restore drill isolado.",
    ):
        assert marker in checklist
    for marker in ("DEPLOYED", "VERIFIED", "VAULT_CORE_OPERATIONAL", "16-current-runtime-status.md"):
        assert marker in index


def test_current_recovery_and_backup_runbooks_are_not_stale():
    recovery = text(ROOT / "docs" / "09-bootstrap-recovery.md")
    backup = text(BACKUP_RUNBOOK)
    assert "VERIFIED_ADR023_LIVE_ACCEPTED" in recovery
    assert "RESTORE_DRILL_PASS" in recovery
    assert "02:30" in backup
    assert "vault-backup" in backup
    assert "systemd-creds" in backup
    assert "14" in backup
    assert "SCHEDULED_SNAPSHOT_PASS" in backup
