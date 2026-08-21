# tests/ci/test_gate_script.py
"""Gate-runner contract tests — the gate runner MUST be fail-closed.

Proven here:
  * a simulated real pytest failure (rc 1/2/3/4) can NOT be masked;
  * rc=5 ("no tests collected") is tolerated ONLY for explicitly named
    future-empty suites, and never for suites that must already be populated;
  * the secret scanner detects `hvs.` and legacy `s.` token shapes across the
    tracked tree, and NEVER echoes the matched value — only redacted text and
    the file path;
  * neither the shell runner nor the workflow uses `|| true` on gate execution;
  * the least-privilege workflow and the hvac>=2,<3 pin are preserved.

Deterministic and offline: failures are simulated with a fake `pytest` shim on
PATH inside a throwaway git sandbox. No live Vault, no network, no real secrets.
Any token-shaped string is assembled at runtime from harmless fragments, so this
test file is never itself a scan hit.
"""

import os
import pathlib
import shutil
import stat
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_REL = "scripts/ci/run-gates.sh"
SCRIPT = REPO_ROOT / SCRIPT_REL
WORKFLOW = REPO_ROOT / ".github/workflows/fast-gates.yml"

# Suites that are planned-but-not-yet-populated: rc=5 tolerated here only.
FUTURE_EMPTY_GATES = ("tests/lifecycle", "tests/evidence", "tests/secret_zero")
# Suites that already hold real tests: rc=5 must be a hard failure.
POPULATED_GATES = ("tests/policy_lint", "tests/contract")
INTEGRATION_GATES = ("tests/isolation", "tests/audit", "tests/recovery")

# Fake pytest: exit code chosen per invoked target via FAKE_MAP="needle=rc;...".
FAKE_PYTEST = """#!/usr/bin/env bash
args="$*"
if [ -n "${FAKE_MAP:-}" ]; then
  IFS=';' read -ra _pairs <<< "$FAKE_MAP"
  for _p in "${_pairs[@]}"; do
    [ -z "$_p" ] && continue
    _key="${_p%%=*}"
    _rc="${_p##*=}"
    case "$args" in
      *"$_key"*) exit "$_rc" ;;
    esac
  done
fi
exit "${FAKE_DEFAULT_RC:-0}"
"""

# Synthetic token-shaped values, assembled so they exist only at runtime.
SYNTH_HVS = "hvs" + "." + ("A" * 26)
SYNTH_LEGACY = "s" + "." + ("B" * 26)


def _make_sandbox(tmp_path):
    """Throwaway git repo mirroring the layout run-gates.sh depends on."""
    sb = tmp_path / "sandbox"
    (sb / "scripts" / "ci").mkdir(parents=True)
    shutil.copy2(SCRIPT, sb / SCRIPT_REL)
    (sb / SCRIPT_REL).chmod(0o755)

    for d in FUTURE_EMPTY_GATES + POPULATED_GATES + INTEGRATION_GATES + (
        "docs",
        "policies",
        "src",
        "templates",
        ".github/workflows",
    ):
        (sb / d).mkdir(parents=True, exist_ok=True)
        (sb / d / ".keep").write_text("placeholder\n")

    binp = sb / "fakebin"
    binp.mkdir()
    shim = binp / "pytest"
    shim.write_text(FAKE_PYTEST)
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    subprocess.run(["git", "init", "-q"], cwd=sb, check=True)
    subprocess.run(["git", "add", "-A", ":!fakebin"], cwd=sb, check=True)
    return sb


def _track(sb, relpath, content):
    p = sb / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    subprocess.run(["git", "add", "--", relpath], cwd=sb, check=True)


def _run(sb, *args, fake_map="", default_rc=0):
    env = dict(os.environ)
    env["PATH"] = f"{sb / 'fakebin'}{os.pathsep}{env['PATH']}"
    env["FAKE_MAP"] = fake_map
    env["FAKE_DEFAULT_RC"] = str(default_rc)
    return subprocess.run(
        ["bash", SCRIPT_REL, *args],
        cwd=sb,
        capture_output=True,
        text=True,
        env=env,
    )


# --------------------------------------------------------------------------
# static contract: no fail-open constructs
# --------------------------------------------------------------------------

def test_runner_has_no_bare_or_true_on_gate_execution():
    body = SCRIPT.read_text()
    offenders = [
        ln.strip()
        for ln in body.splitlines()
        if "|| true" in ln and not ln.strip().startswith("#")
    ]
    assert not offenders, f"fail-open `|| true` present: {offenders}"


def test_workflow_has_no_bare_or_true_and_is_least_privilege():
    body = WORKFLOW.read_text()
    offenders = [
        ln.strip()
        for ln in body.splitlines()
        if "|| true" in ln and not ln.strip().lstrip("-").strip().startswith("#")
    ]
    assert not offenders, f"workflow is fail-open: {offenders}"
    assert "permissions: read-all" in body
    assert 'hvac>=2,<3' in body


def test_workflow_parses_as_yaml_and_keeps_fail_closed_semantics():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(WORKFLOW.read_text())
    steps = doc["jobs"]["fast-gates"]["steps"]
    runs = "\n".join(s.get("run", "") for s in steps)
    # Every tolerated-empty suite must be gated on an explicit rc check that
    # tolerates only pytest rc=5 and propagates everything else.
    assert "rc" in runs and ('-eq 5' in runs or '-ne 5' in runs), \
        "workflow lacks explicit rc=5 handling"
    assert "|| true" not in runs


# --------------------------------------------------------------------------
# fail-closed behaviour under simulated pytest outcomes
# --------------------------------------------------------------------------

def test_dry_run_passes_when_everything_healthy(tmp_path):
    sb = _make_sandbox(tmp_path)
    r = _run(sb, "--dry", default_rc=0)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("rc", [1, 2, 3, 4])
@pytest.mark.parametrize("gate", FUTURE_EMPTY_GATES + POPULATED_GATES)
def test_real_pytest_failure_is_never_masked(tmp_path, rc, gate):
    """A genuine failure in ANY fast gate must propagate non-zero."""
    sb = _make_sandbox(tmp_path)
    r = _run(sb, "--dry", fake_map=f"{gate}={rc}", default_rc=0)
    assert r.returncode != 0, (
        f"gate {gate} masked pytest rc={rc}\n{r.stdout}\n{r.stderr}"
    )


@pytest.mark.parametrize("gate", FUTURE_EMPTY_GATES)
def test_rc5_tolerated_only_for_named_future_empty_suites(tmp_path, gate):
    sb = _make_sandbox(tmp_path)
    r = _run(sb, "--dry", fake_map=f"{gate}=5", default_rc=0)
    assert r.returncode == 0, (
        f"future-empty suite {gate} should tolerate rc=5\n{r.stdout}\n{r.stderr}"
    )


@pytest.mark.parametrize("gate", POPULATED_GATES)
def test_rc5_on_populated_suite_is_a_hard_failure(tmp_path, gate):
    sb = _make_sandbox(tmp_path)
    r = _run(sb, "--dry", fake_map=f"{gate}=5", default_rc=0)
    assert r.returncode != 0, (
        f"populated suite {gate} must not silently accept rc=5\n{r.stdout}"
    )


def test_tolerating_empty_suite_does_not_make_a_real_failure_green(tmp_path):
    """Empty-suite tolerance and failure propagation must coexist."""
    sb = _make_sandbox(tmp_path)
    fake_map = ";".join(
        [f"{g}=5" for g in FUTURE_EMPTY_GATES] + ["tests/policy_lint=1"]
    )
    r = _run(sb, "--dry", fake_map=fake_map, default_rc=0)
    assert r.returncode != 0, (
        "empty-suite tolerance masked a real failure\n" + r.stdout + r.stderr
    )


# --------------------------------------------------------------------------
# secret scanner
# --------------------------------------------------------------------------

def test_secret_scan_clean_tree_passes_full_run(tmp_path):
    sb = _make_sandbox(tmp_path)
    r = _run(sb, default_rc=0)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "secret-scan" in r.stdout


@pytest.mark.parametrize(
    "relpath",
    [
        "leaked.txt",                 # repository root
        ".github/workflows/x.yml",
        "scripts/leak.sh",
        "docs/leak.md",
        "policies/leak.hcl",
        "src/leak.py",
        "templates/leak.tmpl",
    ],
)
def test_secret_scan_detects_hvs_shape_across_tracked_tree(tmp_path, relpath):
    sb = _make_sandbox(tmp_path)
    _track(sb, relpath, f"token = {SYNTH_HVS}\n")
    r = _run(sb, default_rc=0)
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"scanner missed {relpath}\n{out}"
    assert SYNTH_HVS not in out, "scanner leaked the matched secret value"
    assert relpath in out, "scanner should report the safe file path"


def test_secret_scan_detects_legacy_shape(tmp_path):
    sb = _make_sandbox(tmp_path)
    _track(sb, "policies/legacy.hcl", f"vault_token = {SYNTH_LEGACY}\n")
    r = _run(sb, default_rc=0)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    assert SYNTH_LEGACY not in out


# --------------------------------------------------------------------------
# Canonical secret-scan SCOPE regression (FINAL FIX WAVE, item 2).
# The tracked scan must cover tests/ so future secret-shaped test fixtures are
# not exempt from the scanner. These tests fail RED until run-gates.sh adds
# ':(top)tests/**' to the secret_scan pathspec, then go GREEN. Output stays
# redacted and fail-closed (no matched value echoed).
# --------------------------------------------------------------------------
def test_canonical_scan_scope_includes_tests_in_source():
    # Documentary + cheap: the canonical tracked-file selection must name tests/.
    body = SCRIPT.read_text()
    assert ":(top)tests/**" in body, "secret_scan pathspec omits tests/**"


@pytest.mark.parametrize(
    "relpath",
    [
        "tests/leak.py",           # a synthetic secret-shaped tracked test file
        "tests/audit/leak.json",
        "tests/ci/leak.sh",
        "tests/baseline/leak.tf",
    ],
)
def test_secret_scan_rejects_synthetic_secret_in_tracked_tests(tmp_path, relpath):
    # Behavioural proof: a secret-shaped string committed into a tracked test
    # file MUST be caught by the canonical scan. This is the fail-closed
    # guarantee that test fixtures are not scanner-blind.
    sb = _make_sandbox(tmp_path)
    _track(sb, relpath, f"token = {SYNTH_HVS}\n")
    r = _run(sb, default_rc=0)
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"canonical scan missed {relpath}\n{out}"
    assert SYNTH_HVS not in out, "scanner leaked the matched secret value"
    assert relpath in out, "scanner should report the safe file path"


def test_secret_scan_ignores_untracked_and_gitignored_material(tmp_path):
    sb = _make_sandbox(tmp_path)
    (sb / "vault-data").mkdir()
    (sb / "vault-data" / "runtime.json").write_text(f"root_token = {SYNTH_HVS}\n")
    (sb / "untracked.txt").write_text(f"token = {SYNTH_HVS}\n")
    r = _run(sb, default_rc=0)
    assert r.returncode == 0, (
        "scanner must ignore untracked/runtime material\n" + r.stdout + r.stderr
    )


def test_scanner_does_not_flag_the_tracked_repository_itself():
    """The real tracked tree must be scan-clean, including this test file."""
    r = subprocess.run(
        ["bash", SCRIPT_REL, "--scan-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------------------
# original smoke contract (kept)
# --------------------------------------------------------------------------

def test_run_gates_script_exists_and_is_executable():
    assert SCRIPT.exists() and SCRIPT.stat().st_mode & 0o111
    out = subprocess.run(
        ["bash", SCRIPT_REL, "--dry"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert out.returncode == 0, out.stdout + out.stderr


def test_bash_syntax_is_valid():
    r = subprocess.run(["bash", "-n", SCRIPT_REL], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
