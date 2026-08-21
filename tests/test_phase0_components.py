from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.phase0_discovery import (
    CommandObservation,
    classify_reference,
    collect_docker,
    collect_host,
    collect_listeners,
    collect_recovery_constraints,
    collect_secret_references,
    collect_storage,
    collect_systemd,
    collect_tls_metadata,
    collect_vault_prerequisites,
)


def fake_obs(argv, stdout="", status="ok", returncode=0, stderr=""):
    return CommandObservation(
        argv=tuple(argv), status=status,
        returncode=returncode if status in {"ok", "error"} else None,
        stdout=stdout, stderr=stderr, duration_ms=1, truncated=False,
    )


class CollectorTests(unittest.TestCase):
    def test_collect_host_returns_sanitized_metadata(self) -> None:
        responses = {
            ("/usr/bin/uname", "-srmo"): fake_obs(["uname"], "Linux 6.12 x86_64 GNU/Linux\n"),
            ("/usr/bin/getconf", "_NPROCESSORS_ONLN"): fake_obs(["getconf"], "8\n"),
        }
        def runner(argv, timeout_s=5.0):
            return responses[tuple(argv)]
        with tempfile.TemporaryDirectory() as td:
            os_release = Path(td) / "os-release"
            os_release.write_text('ID=debian\nVERSION_ID="13"\nPRETTY_NAME="Debian GNU/Linux 13"\nSECRET=must-not-appear\n')
            meminfo = Path(td) / "meminfo"
            meminfo.write_text("MemTotal: 16384000 kB\nMemAvailable: 8192000 kB\nHugeSecret: must-not-appear\n")
            result = collect_host(runner=runner, os_release_path=os_release, meminfo_path=meminfo)
        serialized = json.dumps(result)
        self.assertEqual(result["os"]["id"], "debian")
        self.assertEqual(result["cpu_count"], 8)
        self.assertEqual(result["memory"]["total_kib"], 16384000)
        self.assertNotIn("must-not-appear", serialized)

    def test_storage_systemd_docker_and_listeners_use_closed_reads(self) -> None:
        storage_seen = []
        def storage_runner(argv, timeout_s=5.0):
            storage_seen.append(list(argv))
            return fake_obs(argv, "Filesystem 1-blocks Used Available Capacity Mounted on\n/dev/nvme0n1p1 1000 400 600 40% /\n/dev/nvme0n1p1 1000 400 600 40% /var\n")
        self.assertEqual(collect_storage(runner=storage_runner)["status"], "ok")
        self.assertEqual(storage_seen, [["/usr/bin/df", "-P", "-B1", "/", "/var"]])

        systemd_seen = []
        def systemd_runner(argv, timeout_s=5.0):
            systemd_seen.append(list(argv))
            return fake_obs(argv, "LoadState=loaded\nActiveState=active\nSubState=running\nUnitFileState=enabled\n")
        result = collect_systemd(runner=systemd_runner, system_units=("docker.service",), user_units=("hermes-gateway.service",), hermes_user="estourpm", current_user="estourpm")
        self.assertEqual(result["units"][1]["scope"], "user")
        flat = " ".join(" ".join(x) for x in systemd_seen)
        self.assertIn("--property=ActiveState", flat)
        self.assertNotIn("Environment", flat)

        docker_seen = []
        def docker_runner(argv, timeout_s=5.0):
            docker_seen.append(list(argv))
            if argv[1] == "version":
                return fake_obs(argv, "26.1.5\n")
            return fake_obs(argv, "hermes-mcp-bridge\tsha256:abc\tUp 2 hours (healthy)\n")
        docker = collect_docker(runner=docker_runner)
        self.assertEqual(docker["server_version"], "26.1.5")
        self.assertNotIn("inspect", " ".join(" ".join(x) for x in docker_seen))

        listener_seen = []
        def listener_runner(argv, timeout_s=5.0):
            listener_seen.append(list(argv))
            return fake_obs(argv, "LISTEN 0 4096 127.0.0.1:8642 0.0.0.0:*\n")
        listeners = collect_listeners(runner=listener_runner)
        self.assertEqual(listeners["listeners"][0]["local"], "127.0.0.1:8642")
        self.assertEqual(listener_seen, [["/usr/sbin/ss", "-H", "-ltn"]])


class SecretReferenceTests(unittest.TestCase):
    def test_values_never_appear_in_inventory(self) -> None:
        values = ["ghp_SYNTHETIC_DO_NOT_EMIT_1234567890", "db-password-SYNTHETIC-42", "cloudflare-secret-SYNTHETIC", "transit-material-SYNTHETIC"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env_file = root / ".env"
            env_file.write_text(f"GITHUB_TOKEN={values[0]}\nDATABASE_PASSWORD={values[1]}\nPUBLIC_PORT=8765\n")
            compose = root / "compose.yaml"
            compose.write_text(f"services:\n  bridge:\n    environment:\n      HERMES_API_KEY: ${{HERMES_API_KEY}}\n      CLOUDFLARE_TOKEN: {values[2]}\n")
            unit = root / "hermes-gateway.service"
            unit.write_text(f'[Service]\nEnvironmentFile=-/home/estourpm/.hermes/.env\nEnvironment="SIGNING_KEY={values[3]}"\n')
            refs = collect_secret_references([env_file, compose, unit])
        serialized = json.dumps(refs)
        for value in values:
            self.assertNotIn(value, serialized)
        names = {item["name"] for item in refs}
        self.assertTrue({"GITHUB_TOKEN", "DATABASE_PASSWORD", "HERMES_API_KEY", "CLOUDFLARE_TOKEN", "SIGNING_KEY"}.issubset(names))
        self.assertNotIn("PUBLIC_PORT", names)
        self.assertTrue(all("value" not in item for item in refs))

    def test_classification_is_conservative(self) -> None:
        self.assertEqual(classify_reference("CLIENT_CERT", "env"), "pki")
        self.assertEqual(classify_reference("EVIDENCE_SIGNING_KEY", "env"), "transit")
        self.assertEqual(classify_reference("VAULT_ROOT_TOKEN", "env"), "bootstrap")
        self.assertEqual(classify_reference("DATABASE_PASSWORD", "env"), "static")


class PrerequisiteTests(unittest.TestCase):
    def test_tls_is_public_metadata_only_and_rejects_key_paths(self) -> None:
        seen = []
        def runner(argv, timeout_s=5.0):
            seen.append(list(argv))
            return fake_obs(argv, "subject=CN = hermes-vault\nissuer=CN = Hermes Lab CA\nserial=01AB\nnotBefore=Aug 16 00:00:00 2026 GMT\nnotAfter=Aug 16 00:00:00 2027 GMT\nsha256 Fingerprint=AA:BB:CC\n")
        result = collect_tls_metadata([Path("/etc/hermes/tls/public-cert.pem")], runner=runner)
        self.assertEqual(result["certificates"][0]["serial"], "01AB")
        flat = " ".join(" ".join(x) for x in seen)
        self.assertIn("openssl x509", flat)
        self.assertNotIn("-text", flat)
        rejected = collect_tls_metadata([Path("/etc/hermes/tls/server-key.pem")], runner=lambda *a, **k: None)
        self.assertEqual(rejected["certificates"][0]["reason"], "private_key_candidate")

    def test_vault_prerequisites_never_mutate(self) -> None:
        seen = []
        def runner(argv, timeout_s=5.0):
            seen.append(list(argv))
            if argv[0].endswith("/vault"):
                return fake_obs(argv, "Vault v1.21.4 (community)\n")
            return fake_obs(argv, "26.1.5\n")
        result = collect_vault_prerequisites(runner=runner, vault_binary="/usr/bin/vault")
        self.assertEqual(result["target"]["version"], "1.21.4")
        self.assertFalse(result["mutation_performed"])
        flat = " ".join(" ".join(x) for x in seen)
        for forbidden in ("operator init", "operator unseal", "secrets enable", "auth enable"):
            self.assertNotIn(forbidden, flat)

    def test_recovery_design_does_not_claim_runtime(self) -> None:
        result = collect_recovery_constraints()
        self.assertEqual(result["unseal"], {"mechanism": "shamir", "shares": 3, "threshold": 2, "material_boundary": "outside_hermes"})
        self.assertFalse(result["runtime_observed"])


if __name__ == "__main__":
    unittest.main()
