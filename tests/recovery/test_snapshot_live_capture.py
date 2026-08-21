from pathlib import Path
import os
import stat
import subprocess

SCRIPT = Path("deployments/vault/scripts/snapshot.sh")


def _src() -> str:
    return SCRIPT.read_text()


def test_snapshot_uses_strict_loopback_https_without_host_vault_cli():
    src = _src()
    assert 'https://127.0.0.1:8200' in src
    assert '/v1/sys/storage/raft/snapshot' in src
    assert 'urllib.request' in src
    assert 'ssl.create_default_context' in src
    assert 'VAULT_CACERT' in src
    assert 'vault operator raft snapshot save' not in src
    assert '\nvault ' not in src


def test_snapshot_requires_operator_ack_and_all_secret_inputs_before_writes():
    src = _src()
    assert 'VAULT_SNAPSHOT_OPERATOR_ACK' in src
    for name in ('VAULT_ADDR', 'VAULT_CACERT', 'VAULT_TOKEN', 'VAULT_SNAPSHOT_PASSPHRASE'):
        assert name in src
    assert 'mkdir -p "${BACKUP_DIR}"' in src

def test_snapshot_never_puts_token_or_passphrase_on_command_arguments_or_output():
    src = _src()
    assert '-pass env:VAULT_SNAPSHOT_PASSPHRASE' in src
    assert 'X-Vault-Token' in src
    assert 'print(os.environ["VAULT_TOKEN"])' not in src
    assert 'echo "${VAULT_TOKEN}"' not in src
    assert 'echo "${VAULT_SNAPSHOT_PASSPHRASE}"' not in src
    assert 'VAULT_TOKEN=' not in '\n'.join(
        line for line in src.splitlines() if not line.lstrip().startswith('#')
    )


def test_snapshot_permissions_checksums_and_encryption_are_mandatory():
    src = _src()
    assert 'chmod 700 "${BACKUP_DIR}"' in src
    assert 'chmod 600 "${SNAP}"' in src
    assert 'sha256sum "${SNAP}"' in src
    assert 'sha256sum "${ENC}"' in src
    assert 'openssl enc -aes-256-cbc -salt -pbkdf2' in src
    assert 'encrypted independent copy SKIPPED' not in src
    assert 'os.replace' in src


def test_snapshot_refuses_without_hitl_env_before_creating_artifacts(tmp_path):
    backup = tmp_path / "backups"
    env = os.environ.copy()
    env.pop("VAULT_TOKEN", None)
    env.pop("VAULT_SNAPSHOT_PASSPHRASE", None)
    env.pop("VAULT_SNAPSHOT_OPERATOR_ACK", None)
    env["VAULT_BACKUP_DIR"] = str(backup)
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert not backup.exists()
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "VAULT_TOKEN" in combined or "operator" in combined.lower()


def test_snapshot_script_has_no_secret_shaped_literals():
    src = _src()
    forbidden = (
        "root_token=",
        "recovery_key=",
        "SecretID=",
        "hvs.",
    )
    for item in forbidden:
        assert item not in src

def test_snapshot_failure_removes_partial_run_artifacts(tmp_path):
    backup = tmp_path / "backups"
    ca = tmp_path / "ca.pem"
    ca.write_text("synthetic-ca")
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    py = fakebin / "python3"
    py.write_text('#!/bin/sh\nprintf synthetic-snapshot > "$3"\n')
    py.chmod(0o755)
    openssl = fakebin / "openssl"
    openssl.write_text('#!/bin/sh\nexit 9\n')
    openssl.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "PATH": f"{fakebin}:{env['PATH']}",
        "VAULT_BACKUP_DIR": str(backup),
        "VAULT_ADDR": "https://127.0.0.1:8200",
        "VAULT_CACERT": str(ca),
        "VAULT_TOKEN": "synthetic-test-token",
        "VAULT_SNAPSHOT_PASSPHRASE": "synthetic-test-passphrase",
        "VAULT_SNAPSHOT_OPERATOR_ACK": "yes",
    })
    proc = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    assert proc.returncode != 0
    assert backup.exists()
    assert list(backup.iterdir()) == []
