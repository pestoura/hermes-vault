from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "baseline" / "lab-l1-source.json"
OVERLAY = ROOT / "baseline" / "lab-l1-audit.compose.yaml"
BACKUP_POLICY = ROOT / "baseline" / "policies" / "lab-l1-backup.hcl"
BASELINE_SCRIPT = ROOT / "operations" / "lab_l1_baseline.sh"
RESTORE_SCRIPT = ROOT / "operations" / "restore_drill.sh"
RECOVERY_DOC = ROOT / "docs" / "17-lab-l1-baseline-recovery.md"
VALIDATOR = ROOT / "tools" / "validate_lab_l1_source.py"

EXPECTED_COMMIT = "c63fee752bfd28868da54eb9650943e2b504f659"
EXPECTED_FILES = {
    "README.md": "6aeed8724876ddf6a2c7ae376a0b1bfb3ee9f5ee",
    "compose.yaml": "ba775ef75253737cd7a17e0e85e5bb69401defa1",
    "config/vault.hcl": "48127d7a72a356d33844cf74af1927f83864800c",
    "bootstrap/bootstrap.sh": "071e5b9826ef33a0fbeafd9481bc714833ed8d0f",
    "bootstrap/verify-capability.sh": "7b16f61601cdc1ae6a8dfc5403779920813a3911",
    "policies/operator-observer.hcl": "5d6c51f558739738bf9db29f6613cadfc383ccdc",
    "policies/signer.hcl": "bcc23eaec0381d5820c7573be9592bef0cc2913f",
}


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_lab_l1_source", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpstreamAdoptionTests(unittest.TestCase):
    def test_manifest_pins_exact_upstream_commit_and_blobs(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "hermes-vault-lab-l1-source/v1")
        source = data["source"]
        self.assertEqual(source["repository"], "pestoura/hermes-security-labs")
        self.assertEqual(source["commit"], EXPECTED_COMMIT)
        self.assertEqual(source["path"], "deployment/vault-lab-l1")
        self.assertEqual(source["files"], EXPECTED_FILES)
        self.assertNotIn("branch", source)
        self.assertNotIn("tag", source)

    def test_validator_rejects_mutable_or_incomplete_source(self) -> None:
        validator = load_validator()
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ok, errors = validator.validate_manifest(data)
        self.assertTrue(ok, errors)

        mutable = json.loads(json.dumps(data))
        mutable["source"]["commit"] = "main"
        ok, errors = validator.validate_manifest(mutable)
        self.assertFalse(ok)
        self.assertTrue(any("commit" in error for error in errors))

        incomplete = json.loads(json.dumps(data))
        incomplete["source"]["files"].pop("compose.yaml")
        ok, errors = validator.validate_manifest(incomplete)
        self.assertFalse(ok)
        self.assertTrue(any("files" in error for error in errors))


class AuditOverlayTests(unittest.TestCase):
    def test_overlay_adds_only_named_audit_volume(self) -> None:
        text = OVERLAY.read_text(encoding="utf-8")
        self.assertIn("vault-lab-l1-audit:/vault/audit", text)
        self.assertIn("name: hermes-vault-lab-l1-audit", text)
        self.assertNotRegex(text, r"(?m)^\s*-\s*[./~][^:]*:/vault/audit")
        self.assertNotIn("/vault/data", text)
        self.assertNotIn("ports:", text)
        self.assertNotIn("networks:", text)

    def test_audit_commands_are_explicit_secret_safe_and_fail_closed(self) -> None:
        text = BASELINE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("audit-status", text)
        self.assertIn("audit-enable", text)
        self.assertIn("vault audit list -format=json", text)
        self.assertIn("-path=lab-l1-file", text)
        self.assertIn("file_path=/vault/audit/audit.log", text)
        self.assertIn("mode=0600", text)
        self.assertIn("format=json", text)
        self.assertIn("log_raw=false", text)
        self.assertIn("elide_list_responses=true", text)
        for forbidden in ("VAULT_TOKEN=", "echo $VAULT_TOKEN", "set -x", "audit disable"):
            self.assertNotIn(forbidden, text)


class SnapshotTests(unittest.TestCase):
    def test_backup_policy_is_exactly_read_only_snapshot(self) -> None:
        text = BACKUP_POLICY.read_text(encoding="utf-8")
        self.assertIn('path "sys/storage/raft/snapshot"', text)
        capabilities = re.findall(r'"(create|read|update|patch|delete|list|sudo|deny)"', text)
        self.assertEqual(capabilities, ["read"])
        self.assertNotIn("*", text)

    def test_snapshot_save_is_atomic_local_and_never_restore(self) -> None:
        text = BASELINE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("snapshot-save", text)
        self.assertIn("snapshot-inspect", text)
        self.assertIn("vault operator raft snapshot save", text)
        self.assertIn("vault operator raft snapshot inspect", text)
        self.assertIn("sha256sum", text)
        self.assertIn("umask 077", text)
        self.assertIn("mktemp -d", text)
        self.assertIn("/vault/data", text)
        self.assertIn("/vault/audit", text)
        self.assertNotIn("snapshot restore", text)


class RestoreGuardrailTests(unittest.TestCase):
    def test_restore_script_is_preflight_only_and_requires_isolated_scope(self) -> None:
        text = RESTORE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("HERMES_VAULT_RESTORE_SCOPE", text)
        self.assertIn("ISOLATED_SCRATCH", text)
        self.assertIn("HERMES_VAULT_RESTORE_NETWORK_ISOLATION_CONFIRMED", text)
        self.assertIn("HERMES_VAULT_RESTORE_STORAGE_ISOLATED", text)
        self.assertIn("vault operator raft snapshot inspect", text)
        self.assertNotIn("vault operator raft snapshot restore", text)
        for production_addr in ("https://127.0.0.1:18200", "https://localhost:18200", "https://vault:8200"):
            self.assertIn(production_addr, text)

    def test_recovery_doc_keeps_force_restore_as_hitl(self) -> None:
        text = RECOVERY_DOC.read_text(encoding="utf-8")
        self.assertIn("HITL", text)
        self.assertIn("vault operator raft snapshot restore -force", text)
        self.assertIn("isolated", text.lower())
        self.assertIn("independent", text.lower())


if __name__ == "__main__":
    unittest.main()
