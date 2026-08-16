from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "identity" / "workload-roles.json"
POLICY_DIR = ROOT / "identity" / "policies"
MATRIX = ROOT / "identity" / "negative-capability-matrix.json"
PILOT = ROOT / "templates" / "kv-pilot-handoff.json"
SCRIPT = ROOT / "operations" / "epic02_identity_kv.sh"
RUNBOOK = ROOT / "docs" / "18-epic02-identity-kv-runbook.md"
IDENTITY_VALIDATOR = ROOT / "tools" / "validate_identity_contract.py"
POLICY_LINTER = ROOT / "tools" / "lint_vault_policies.py"

EXPECTED_ROLES = {
    "hermes-runtime",
    "hermes-controller",
    "jarvas-operations",
    "github-tool",
}
SELF_PATHS = {
    "auth/token/lookup-self": ["read"],
    "sys/capabilities-self": ["update"],
}
GITHUB_DATA = "secret/data/jarvas/github/runtime"
GITHUB_METADATA = "secret/metadata/jarvas/github/runtime"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IdentityManifestTests(unittest.TestCase):
    def test_manifest_has_exact_separate_bounded_roles(self) -> None:
        data = json.loads(ROLES.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "hermes-vault-workload-identities/v1")
        self.assertEqual(data["auth_method"], "approle")
        roles = data["roles"]
        self.assertEqual(set(roles), EXPECTED_ROLES)
        policies = set()
        for name, role in roles.items():
            self.assertEqual(role["policy"], name)
            self.assertNotIn(role["policy"], policies)
            policies.add(role["policy"])
            self.assertTrue(role["token_no_default_policy"])
            self.assertEqual(role["secret_id_num_uses"], 1)
            self.assertEqual(role["secret_id_ttl"], "10m")
            self.assertEqual(role["wrap_ttl"], "5m")
            self.assertRegex(role["token_ttl"], r"^\d+m$")
            self.assertRegex(role["token_max_ttl"], r"^\d+m$")
            self.assertLessEqual(int(role["token_max_ttl"][:-1]), 30)
            self.assertLessEqual(int(role["token_ttl"][:-1]), int(role["token_max_ttl"][:-1]))
        self.assertFalse(roles["hermes-runtime"]["direct_kv"])
        self.assertFalse(roles["hermes-controller"]["direct_kv"])
        self.assertFalse(roles["jarvas-operations"]["direct_kv"])
        self.assertTrue(roles["github-tool"]["direct_kv"])
        self.assertEqual(roles["github-tool"]["kv_data_path"], GITHUB_DATA)
        self.assertEqual(roles["github-tool"]["kv_metadata_path"], GITHUB_METADATA)

    def test_identity_validator_rejects_unbounded_or_admin_roles(self) -> None:
        validator = _load(IDENTITY_VALIDATOR, "identity_validator")
        data = json.loads(ROLES.read_text(encoding="utf-8"))
        ok, errors = validator.validate_identity_contract(data)
        self.assertTrue(ok, errors)

        bad = json.loads(json.dumps(data))
        bad["roles"]["hermes-runtime"]["secret_id_num_uses"] = 0
        ok, errors = validator.validate_identity_contract(bad)
        self.assertFalse(ok)
        self.assertTrue(any("secret_id_num_uses" in error for error in errors))

        bad = json.loads(json.dumps(data))
        bad["roles"]["hermes-vault-admin"] = bad["roles"].pop("github-tool")
        ok, errors = validator.validate_identity_contract(bad)
        self.assertFalse(ok)
        self.assertTrue(any("roles" in error for error in errors))


class PolicyTests(unittest.TestCase):
    def test_runtime_controller_operations_have_self_introspection_only(self) -> None:
        for name in ("hermes-runtime", "hermes-controller", "jarvas-operations"):
            text = (POLICY_DIR / f"{name}.hcl").read_text(encoding="utf-8")
            self.assertIn('path "auth/token/lookup-self"', text)
            self.assertIn('path "sys/capabilities-self"', text)
            self.assertNotIn("secret/data/", text)
            self.assertNotIn("secret/metadata/", text)

    def test_github_tool_is_exact_read_only_and_cross_tool_denied_by_absence(self) -> None:
        text = (POLICY_DIR / "github-tool.hcl").read_text(encoding="utf-8")
        self.assertIn(f'path "{GITHUB_DATA}"', text)
        self.assertIn(f'path "{GITHUB_METADATA}"', text)
        self.assertEqual(text.count('capabilities = ["read"]'), 3)
        self.assertIn('capabilities = ["update"]', text)
        for foreign in ("grafana", "cloudflare", "microsoft", "planner", "outlook", "google"):
            self.assertNotIn(foreign, text.lower())
        for capability in ("create", "patch", "delete", "sudo"):
            self.assertNotRegex(text, rf'"{capability}"')

    def test_policy_linter_accepts_canonical_and_rejects_dangerous_patterns(self) -> None:
        linter = _load(POLICY_LINTER, "policy_linter")
        for name in EXPECTED_ROLES:
            text = (POLICY_DIR / f"{name}.hcl").read_text(encoding="utf-8")
            self.assertEqual(linter.lint_policy_text(name, text), [])

        bad_samples = {
            "global": 'path "*" { capabilities = ["read"] }',
            "sudo": 'path "sys/mounts/*" { capabilities = ["sudo", "update"] }',
            "kv_wildcard": 'path "secret/data/jarvas/github/*" { capabilities = ["read"] }',
            "admin": 'path "sys/policies/acl/x" { capabilities = ["update"] }',
        }
        for label, text in bad_samples.items():
            self.assertTrue(linter.lint_policy_text("github-tool", text), label)


class BootstrapScriptTests(unittest.TestCase):
    def test_script_configures_only_auth_policies_roles_and_empty_kv_mount(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for command in (
            "preflight",
            "kv-status",
            "kv-enable",
            "configure-policies",
            "configure-roles",
            "role-id",
            "wrapped-secret-id",
            "capability-check",
        ):
            self.assertIn(command, text)
        self.assertIn("vault secrets list -detailed -format=json", text)
        self.assertIn("vault secrets enable -path=secret -version=2 kv", text)
        self.assertIn("token_no_default_policy=true", text)
        self.assertIn("secret_id_num_uses=1", text)
        self.assertIn("-wrap-ttl=5m", text)
        for forbidden in ("vault kv put", "vault write secret/", "secret/data/jarvas/github/runtime value=", "set -x"):
            self.assertNotIn(forbidden, text)

    def test_script_never_accepts_secret_values_as_positional_arguments(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)(password|token|secret[_-]?value|client[_-]?secret)=\$\{[23456789]")
        self.assertIn("current Vault token", text)
        self.assertIn("response-wrapped SecretID", text)


class NegativeMatrixAndPilotTests(unittest.TestCase):
    def test_negative_matrix_has_cross_tool_and_admin_denies(self) -> None:
        data = json.loads(MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "hermes-vault-negative-capability-matrix/v1")
        self.assertEqual(set(data["identities"]), EXPECTED_ROLES)
        for name, entry in data["identities"].items():
            denied_paths = {item["path"] for item in entry["negative"]}
            self.assertIn("sys/policies/acl", denied_paths)
            self.assertIn("sys/auth", denied_paths)
            self.assertIn("sys/mounts", denied_paths)
            self.assertIn("secret/data/jarvas/microsoft/planner/runtime", denied_paths)
            if name != "github-tool":
                self.assertIn(GITHUB_DATA, denied_paths)
        github_positive = {item["path"] for item in data["identities"]["github-tool"]["positive"]}
        self.assertIn(GITHUB_DATA, github_positive)
        self.assertIn(GITHUB_METADATA, github_positive)

    def test_pilot_template_is_reference_only_and_not_preselected(self) -> None:
        data = json.loads(PILOT.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "hermes-vault-kv-pilot-handoff/v1")
        self.assertEqual(data["status"], "AWAITING_LIVE_DISCOVERY")
        for key in ("inventory_id", "owner", "consumer", "provider", "classification", "target_path", "acceptance_test_ref", "rollback_ref", "legacy_reference"):
            self.assertIsNone(data[key])
        serialized = json.dumps(data).lower()
        for forbidden in ("secret_value", "password_value", "token_value", "private_key_value"):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(data["live_gates"]["KV_PILOT_PASS"])
        self.assertFalse(data["live_gates"]["ROTATION_PASS"])
        self.assertFalse(data["live_gates"]["LEGACY_SECRET_REMOVED"])
        self.assertFalse(data["live_gates"]["RESTART_PASS"])

    def test_runbook_requires_inventory_before_pilot_and_removal_after_rotation(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8").lower()
        self.assertIn("inventário", text)
        self.assertIn("rollback", text)
        self.assertIn("rotação", text)
        self.assertIn("restart", text)
        self.assertIn("legacy", text)
        self.assertIn("não seleciona", text)


if __name__ == "__main__":
    unittest.main()
