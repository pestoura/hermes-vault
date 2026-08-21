from pathlib import Path
import os
import subprocess

SCRIPT = Path("deployments/vault/scripts/prepare-restore-acceptance.sh")


def _src() -> str:
    return SCRIPT.read_text()


def test_staging_script_is_operator_gated_and_uses_only_recovery_jit():
    assert SCRIPT.is_file()
    src = _src()
    assert "VAULT_RESTORE_STAGE_OPERATOR_ACK" in src
    assert "VAULT_TOKEN" in src
    assert "VAULT_SNAPSHOT_PASSPHRASE" in src
    assert "VAULT_ADMIN_KEY_PEM" not in src
    assert "vault-admin-recovery" in src
    assert "token revoke -self" in src


def test_staging_uses_only_reserved_restore_acceptance_objects():
    src = _src()
    for marker in (
        "restore-acceptance-kv",
        "restore-acceptance-transit",
        "restore-acceptance-test",
        "auth/cert/certs/restore-acceptance",
        "restore-acceptance",
    ):
        assert marker in src
    for forbidden in ("hsl-transit", "hsl-signing", "sys/storage/raft/snapshot-force"):
        assert forbidden not in src

def test_staging_generates_disposable_client_cert_and_never_prints_fixture_values():
    src = _src()
    assert "openssl req -x509" in src
    assert "basicConstraints=critical,CA:FALSE" in src
    assert "extendedKeyUsage=clientAuth" in src
    assert "chmod 600" in src
    assert "ADR023_PRIMARY_OK" in src
    assert "ADR023_FORBIDDEN_OK" in src
    assert 'echo "ADR023_PRIMARY_OK"' not in src
    assert 'echo "ADR023_FORBIDDEN_OK"' not in src


def test_staging_orders_fixtures_before_snapshot_and_cleanup_after_snapshot():
    src = _src()
    fixture_pos = src.index("restore-acceptance-kv/primary")
    snapshot_pos = src.index("snapshot.sh")
    cleanup_pos = src.rindex("cleanup_live")
    assert fixture_pos < snapshot_pos < cleanup_pos
    assert "trap cleanup_on_exit EXIT" in src
    assert "VAULT_SNAPSHOT_OPERATOR_ACK=yes" in src
    assert "VAULT_BACKUP_DIR" in src


def test_staging_dry_invocation_fails_before_creating_run_dir(tmp_path):
    env = os.environ.copy()
    env.pop("VAULT_TOKEN", None)
    env.pop("VAULT_SNAPSHOT_PASSPHRASE", None)
    env.pop("VAULT_RESTORE_STAGE_OPERATOR_ACK", None)
    env["VAULT_RESTORE_RUN_ROOT"] = str(tmp_path / "runs")
    proc = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    assert proc.returncode != 0
    assert not (tmp_path / "runs").exists()
