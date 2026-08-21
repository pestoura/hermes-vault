from __future__ import annotations

import copy
import json
import unittest

from tools.phase0_discovery import REPORT_SCHEMA, build_report, evaluate_phase0
from tools.validate_phase0 import validate_report


def conclusive_sections() -> dict:
    return {
        "host": {"status": "ok", "available": True},
        "storage": {"status": "ok", "available": True, "filesystems": [{"mount": "/", "bytes_available": 10_000_000_000}]},
        "systemd": {"status": "ok", "available": True, "units": [{"name": "hermes-gateway.service", "status": "ok"}]},
        "docker": {"status": "ok", "available": True, "server_version": "26.1.5"},
        "listeners": {"status": "ok", "available": True, "listeners": []},
        "tls": {"status": "ok", "available": True, "certificates": [{"path": "/safe/cert.pem", "status": "ok"}]},
        "vault_prerequisites": {
            "observed": {"docker": {"status": "present", "server_version": "26.1.5"}, "vault": {"status": "not_observed", "reason": "binary_path_not_supplied"}},
            "target": {"version": "1.21.4", "edition": "community", "tls_required": True},
            "mutation_performed": False,
        },
    }


class Phase0ReportTests(unittest.TestCase):
    def test_report_has_stable_schema_and_no_authority_inference(self) -> None:
        report = build_report(sections=conclusive_sections(), secret_references=[{"name": "GITHUB_TOKEN", "source_type": "env"}], recovery_design={"source": "repository_target_design", "runtime_observed": False})
        self.assertEqual(report["schema"], REPORT_SCHEMA)
        self.assertEqual(report["mode"], "read_only")
        self.assertFalse(report["mutation_performed"])
        self.assertEqual(report["gates"]["DISCOVERY_COMPLETE"]["status"], "PASS")
        self.assertEqual(report["gates"]["NO_SECRET_IN_REPO"]["status"], "NOT_EVALUATED")
        self.assertEqual(report["gates"]["TARGET_ARCHITECTURE_APPROVED"]["status"], "NOT_EVALUATED")
        self.assertEqual(report["gates"]["RECOVERY_DESIGN_DEFINED"]["status"], "NOT_EVALUATED")

    def test_discovery_fails_closed_on_missing_or_inconclusive_section(self) -> None:
        sections = conclusive_sections()
        del sections["tls"]
        gates = evaluate_phase0(sections)
        self.assertEqual(gates["DISCOVERY_COMPLETE"]["status"], "FAIL")
        self.assertIn("tls", gates["DISCOVERY_COMPLETE"]["missing_or_inconclusive"])
        sections = conclusive_sections()
        sections["docker"] = {"status": "inconclusive", "available": False}
        gates = evaluate_phase0(sections)
        self.assertIn("docker", gates["DISCOVERY_COMPLETE"]["missing_or_inconclusive"])

    def test_validator_rejects_wrong_schema_and_mutation_claim(self) -> None:
        report = build_report(sections=conclusive_sections(), secret_references=[], recovery_design={"source": "repository_target_design", "runtime_observed": False})
        bad = copy.deepcopy(report)
        bad["schema"] = "wrong/v9"
        ok, errors = validate_report(bad)
        self.assertFalse(ok)
        self.assertTrue(any("schema" in error for error in errors))
        bad = copy.deepcopy(report)
        bad["mutation_performed"] = True
        ok, errors = validate_report(bad)
        self.assertFalse(ok)
        self.assertTrue(any("mutation" in error for error in errors))

    def test_serialized_report_contains_no_raw_command_fields(self) -> None:
        report = build_report(sections=conclusive_sections(), secret_references=[{"name": "HERMES_API_KEY", "source_type": "env"}], recovery_design={"source": "repository_target_design", "runtime_observed": False})
        serialized = json.dumps(report)
        self.assertNotIn("stdout", serialized)
        self.assertNotIn("stderr", serialized)
        self.assertNotIn("argv", serialized)


if __name__ == "__main__":
    unittest.main()
