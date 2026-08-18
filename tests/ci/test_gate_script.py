# tests/ci/test_gate_script.py
import subprocess, pathlib
def test_run_gates_script_exists_and_is_executable():
    p = pathlib.Path("scripts/ci/run-gates.sh")
    assert p.exists() and p.stat().st_mode & 0o111
    out = subprocess.run(["bash", str(p), "--dry"], capture_output=True, text=True)
    assert out.returncode == 0
