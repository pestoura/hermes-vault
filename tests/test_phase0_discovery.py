from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.phase0_discovery import (
    MAX_CAPTURE_BYTES,
    run_command,
    sanitize_text,
    write_report_atomic,
)


class CommandContractTests(unittest.TestCase):
    def test_run_command_uses_argv_shell_false_and_timeout(self) -> None:
        completed = mock.Mock(returncode=0, stdout="ok", stderr="")
        with mock.patch("tools.phase0_discovery.subprocess.run", return_value=completed) as mocked:
            obs = run_command(["/usr/bin/uname", "-s"], timeout_s=1.25)
        self.assertEqual(obs.status, "ok")
        args, kwargs = mocked.call_args
        self.assertEqual(args[0], ["/usr/bin/uname", "-s"])
        self.assertIs(kwargs.get("shell"), False)
        self.assertEqual(kwargs["timeout"], 1.25)
        self.assertTrue(kwargs["text"])
        self.assertTrue(kwargs["capture_output"])

    def test_run_command_bounds_output(self) -> None:
        oversized = "x" * (MAX_CAPTURE_BYTES + 100)
        completed = mock.Mock(returncode=0, stdout=oversized, stderr=oversized)
        with mock.patch("tools.phase0_discovery.subprocess.run", return_value=completed):
            obs = run_command(["/bin/echo", "safe"])
        self.assertLessEqual(len(obs.stdout.encode()), MAX_CAPTURE_BYTES)
        self.assertLessEqual(len(obs.stderr.encode()), MAX_CAPTURE_BYTES)
        self.assertTrue(obs.truncated)

    def test_run_command_timeout_is_explicit(self) -> None:
        with mock.patch(
            "tools.phase0_discovery.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["x"], 1),
        ):
            obs = run_command(["/bin/false"], timeout_s=1)
        self.assertEqual(obs.status, "timeout")
        self.assertIsNone(obs.returncode)

    def test_sanitize_text_redacts_common_secret_shapes(self) -> None:
        raw = (
            "Authorization: Bearer abc.def.ghi\n"
            "password=swordfish\n"
            "TOKEN: super-secret-value\n"
            "-----BEGIN PRIVATE KEY-----\n"
            "abc123\n"
            "-----END PRIVATE KEY-----\n"
        )
        sanitized = sanitize_text(raw)
        for value in ("abc.def.ghi", "swordfish", "super-secret-value", "abc123"):
            self.assertNotIn(value, sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_atomic_report_is_mode_0600(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.json"
            write_report_atomic(path, {"schema": "x", "safe": True})
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"safe": True, "schema": "x"})


if __name__ == "__main__":
    unittest.main()
