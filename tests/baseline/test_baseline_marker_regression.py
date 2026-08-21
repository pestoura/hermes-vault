# tests/baseline/test_baseline_marker_regression.py
#
# FINAL FIX WAVE, item 3 (B2 marker): regression proof that the B2 baseline
# acceptance file keeps its 4 static/offline contract tests runnable under
# `pytest -m 'not hitl'` while deselecting exactly the 3 live HITL tests.
#
# Offline: invokes pytest as a subprocess against the acceptance file and
# parses the summary line (no live Vault, no secrets, no network).
import subprocess

import pytest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_ACCEPTANCE = _REPO / "tests" / "baseline" / "test_baseline_acceptance.py"


def _summary(tmp_path, *extra):
    env = dict(__import__("os").environ)
    r = subprocess.run(
        ["python3", "-m", "pytest", str(_ACCEPTANCE), "-q", *extra,
         "--co", "-q", "-p", "no:cacheprovider"],
        cwd=_REPO, capture_output=True, text=True, env=env,
    )
    return r


def _summary_run(tmp_path, *extra):
    env = dict(__import__("os").environ)
    r = subprocess.run(
        ["python3", "-m", "pytest", str(_ACCEPTANCE), "-q", *extra,
         "-p", "no:cacheprovider"],
        cwd=_REPO, capture_output=True, text=True, env=env,
    )
    return r


def _count(txt, label):
    # pytest summary: "N passed", "N deselected", "N skipped", "N tests collected".
    import re
    m = re.search(rf"(\d+)\s+{label}", txt)
    return int(m.group(1)) if m else 0


def _collect_count(txt):
    # `pytest --co -q` prints lines like:
    #   tests/baseline/test_baseline_acceptance.py: 7
    import re
    m = re.search(r"test_baseline_acceptance\.py:\s*(\d+)", txt)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s+tests?\s+collected", txt)
    if m:
        return int(m.group(1))
    return 0


def test_all_seven_collected_by_default(tmp_path):
    r = _summary(tmp_path)
    sel = _collect_count(r.stdout + r.stderr)
    # 3 live (skipif, still collected) + 4 static = 7.
    assert sel == 7, f"expected 7 collected, got {sel}\n{r.stdout}\n{r.stderr}"


def test_not_hitl_runs_static_and_deselects_live(tmp_path):
    # A real (offline) run under -m 'not hitl' must execute the 4 static
    # contract tests and deselect exactly the 3 live HITL tests.
    r = _summary_run(tmp_path, "-m", "not hitl")
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"static baseline tests failed\n{out}"
    # 4 static contract tests executed (passed); 3 live HITL deselected.
    assert _count(out, "passed") == 4, f"expected 4 passed, got {_count(out, 'passed')}\n{out}"
    assert _count(out, "deselected") == 3, f"expected 3 deselected, got {_count(out, 'deselected')}\n{out}"
