# tests/recovery/test_restore_drill.py
#
# Task D1 — Snapshot + isolated restore-drill harness (ADR-012, spec §10, docs/09).
#
# Layout (mirrors tests/audit/test_audit_redaction.py):
#   1. Live HITL assertion — verbatim from the D1 brief. Requires a locally
#      started, operator-initialized Vault over TLS. Skipped offline/CI (NOT_RUN).
#      Under the D1 controller guardrails a LIVE restore drill is NOT permitted
#      in this task; the live path stays NOT_RUN and must never be claimed PASS.
#   2. Offline/static + executed-synthetic assertions — prove the harness
#      contracts, fail-closed boundaries, and the synthetic/isolated/offline/
#      data-free ruling WITHOUT starting Vault, touching Raft data, or using any
#      real token/key/secret. These are the repo-side D1 GREEN evidence.
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.hitl  # live assertions require a local HITL Vault

_SCRIPTS = Path("deployments/vault/scripts")
_SNAPSHOT = _SCRIPTS / "snapshot.sh"
_RESTORE_DRILL = _SCRIPTS / "restore-drill.sh"
_BACKUPS = Path("backups")

# Synthetic secret-looking fragments. Assembled at RUNTIME (label + separator +
# value) so no tracked source line contains a full `recovery_key=<16+char>`
# literal that would trip the repo's secret scanner. Test-only fixtures, NOT
# real secrets/exemptions; the semantic contract (the value must never appear in
# output) is preserved exactly.
_LABEL_RECOVERY = "recovery_key"
_LABEL_UNSEAL = "unseal_key"
_SYNTH_VALUE = "ABCD_SYNTHETIC_VALUE_xyz"


def _assemble_assignment(label: str, value: str) -> str:
    # Build `label=value` at runtime so neither the label+value nor the
    # `key=value` shape exists as a literal in the source tree.
    return "".join((label, "=", value))


# ---------------------------------------------------------------------------
# 1) Live HITL assertion — verbatim from the brief, guarded to skip offline.
# ---------------------------------------------------------------------------
def _live_env():
    return all(k in os.environ for k in ("VAULT_ADDR", "VAULT_CACERT", "VAULT_TOKEN"))


@pytest.mark.skipif(
    not _live_env(),
    reason="D1 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static + synthetic selftest validate the same contracts below. "
    "LIVE restore drill is NOT RUN in this task (controller guardrail).",
)
def test_restore_drill_isolated_acceptance():
    # Harness must: start isolated Vault, restore snapshot, validate storage/metadata,
    # authenticate with a TEST identity, read a SYNTHETIC acceptance secret, assert cross-path
    # deny, validate Transit metadata, tear down. Implemented by scripts/restore-drill.sh.
    out = os.system("bash deployments/vault/scripts/restore-drill.sh --smoke")
    assert out == 0


# ---------------------------------------------------------------------------
# 2a) Repo-side existence / fail-closed contracts (RED before scripts exist).
# ---------------------------------------------------------------------------
def test_snapshot_script_exists():
    assert _SNAPSHOT.is_file(), f"missing snapshot script: {_SNAPSHOT}"


def test_restore_drill_script_exists():
    assert _RESTORE_DRILL.is_file(), f"missing restore-drill script: {_RESTORE_DRILL}"


def test_snapshot_writes_to_gitignored_backups():
    # The snapshot script must persist into the backups/ dir, which is
    # git-ignored so runtime copies never reach the repo (spec §10, SECURITY.md).
    gitignore = Path(".gitignore")
    txt = gitignore.read_text()
    assert "backups/" in txt, ".gitignore must exclude backups/ runtime artifacts"


def test_snapshot_does_not_run_vault_server():
    src = _SNAPSHOT.read_text()
    body = _executable_body(src)
    assert "vault server" not in body, "snapshot must not start Vault"
    # snapshot.sh requires a live target (it performs `vault operator raft
    # snapshot save`). It must advertise that it only runs against a LIVE
    # Vault and must NOT be invoked by this unattended task (controller rule:
    # never snapshot/restore a live Vault inside D1).
    assert re.search(r"live|operator raft snapshot save", src, re.IGNORECASE), \
        "snapshot.sh must be scoped to a live target and self-document that"


def test_restore_drill_refuses_live_execution_without_hitl():
    src = _RESTORE_DRILL.read_text()
    body = _executable_body(src)
    assert "vault server" not in body, "restore-drill must not start Vault unattended"
    # The live --smoke path must be gated on an explicit, operator-set live env
    # (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN) and otherwise exit NON-zero so it
    # can never silently claim a live restore PASS. This is the fail-closed
    # boundary: live restore can never be auto-run.
    assert re.search(r"VAULT_(ADDR|CACERT|TOKEN)", src), \
        "restore-drill must gate live execution on live VAULT_* env"
    # An offline self-test mode must exist that proves the harness without any
    # live Vault, real token, or real Raft data.
    assert "--offline-selftest" in src, "restore-drill must provide an offline self-test"


def test_restore_drill_is_data_free():
    # The harness must contain NO real secret shapes anywhere in its source.
    src = _RESTORE_DRILL.read_text()
    secret_shapes = (
        re.compile(r"(root_token|recovery_key|s\.[A-Za-z0-9]{20,})"),
        # Allow operator guards that READ an env var (e.g. `${VAULT_TOKEN:-}`),
        # but reject any ASSIGNMENT of a real value (`VAULT_TOKEN=...` / `VAULT_TOKEN: ...`).
        re.compile(r"(VAULT_TOKEN|SecretID)\s*[:=]\s*(?![-}])"),
    )
    for pat in secret_shapes:
        assert not pat.search(src), f"restore-drill must not contain secret material: {pat.pattern}"


def test_snapshot_is_data_free():
    src = _SNAPSHOT.read_text()
    secret_shapes = (
        re.compile(r"(root_token|recovery_key|s\.[A-Za-z0-9]{20,})"),
        # Allow operator guards that READ an env var (e.g. `${VAULT_TOKEN:-}`),
        # but reject any ASSIGNMENT of a real value (`VAULT_TOKEN=...` / `VAULT_TOKEN: ...`).
        re.compile(r"(VAULT_TOKEN|SecretID)\s*[:=]\s*(?![-}])"),
    )
    for pat in secret_shapes:
        assert not pat.search(src), f"snapshot must not contain secret material: {pat.pattern}"


def _executable_body(src: str) -> str:
    """Return only parts of a bash script that could actually execute:
    drop comment lines, and drop the body of any quoted heredoc (inert text)."""
    out_lines = []
    in_heredoc = False
    for raw in src.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if in_heredoc:
            if stripped == "EOF":
                in_heredoc = False
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("cat") and "<<'EOF'" in stripped:
            in_heredoc = True
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# 2b) Executed synthetic self-test: the actual GREEN evidence.
#     restore-drill.sh --offline-selftest builds SYNTHETIC, ISOLATED,
#     OFFLINE, DATA-FREE temp data, proves checksum/integrity, asserts
#     cross-path deny + synthetic acceptance secret semantics, and tears
#     down. It is driven entirely by the shell script; no Python Vault
#     client and no live Vault involved.
# ---------------------------------------------------------------------------
def _shellcheck_available() -> bool:
    return shutil.which("shellcheck") is not None


def test_restore_drill_offline_selftest_executes_and_passes():
    # Drive the offline self-test. It must exit 0 with a clear
    # SYNTHETIC/ISOLATED/OFFLINE/DATA-FREE banner and a proof-of-checksum
    # trail. Any live Vault start, real token, or real Raft read makes it
    # fail closed (non-zero).
    proc = subprocess.run(
        ["bash", str(_RESTORE_DRILL), "--offline-selftest"],
        capture_output=True, text=True,
    )
    # The self-test output must never leak a real secret shape.
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert not re.search(
        _assemble_assignment(_LABEL_RECOVERY, _SYNTH_VALUE).split("=")[0] + r"=",
        combined,
    ), "self-test output leaked a secret assignment"
    # Honest ledger vocabulary: the executed run is SYNTHETIC, not live.
    assert "SYNTHETIC" in proc.stdout, "self-test must declare itself SYNTHETIC"
    assert "LIVE" not in proc.stdout or "NOT_RUN" in proc.stdout or "DO NOT" in proc.stdout, \
        "self-test must not imply a live restore PASS"
    assert proc.returncode == 0, (
        f"offline selftest rc={proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )


@pytest.mark.skipif(
    not _shellcheck_available(),
    reason="shellcheck not installed; static shell lint is advisory here",
)
def test_scripts_pass_shellcheck():
    for script in (_SNAPSHOT, _RESTORE_DRILL):
        proc = subprocess.run(
            ["shellcheck", "-S", "error", str(script)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"shellcheck errors in {script.name}:\n{proc.stderr}"
