from pathlib import Path
import hashlib
import os
import subprocess

SCRIPT = Path("deployments/vault/scripts/restore-drill.sh")
IMAGE = "hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"


def _src() -> str:
    return SCRIPT.read_text()


def test_restore_drill_exposes_explicit_lifecycle_not_legacy_smoke():
    src = _src()
    for mode in ('--start', '--status', '--accept', '--teardown', '--offline-selftest'):
        assert mode in src
    assert '--smoke' not in src

def test_restore_start_contract_is_network_none_and_exact_digest():
    src = _src()
    assert IMAGE in src
    for marker in (
        '--network none', '--read-only', '--cap-drop ALL',
        'no-new-privileges', '--memory', '--cpus', '--pids-limit',
        '--tmpfs', '--user 100:1000', 'com.hexor.restore-run',
    ):
        assert marker in src
    docker_run = src.split('docker run -d', 1)[1].split('if ! cid=', 1)[0] if 'if ! cid=' in src.split('docker run -d', 1)[1] else src.split('docker run -d', 1)[1].split(')"; then', 1)[0]
    assert ' -p ' not in docker_run
    assert '--publish' not in docker_run


def test_start_section_never_initializes_unseals_or_restores():
    src = _src()
    section = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    for forbidden in ('operator init', 'operator unseal', 'snapshot restore', 'snapshot-force'):
        assert forbidden not in section


def test_acceptance_keeps_token_inside_isolated_container():
    src = _src()
    section = src.split('cmd_accept()', 1)[1].split('cmd_teardown()', 1)[0]
    assert 'vault login -method=cert' in section
    assert 'restore-acceptance-kv/primary' in section
    assert 'restore-acceptance-kv/forbidden' in section
    assert 'restore-acceptance-transit/keys/restore-acceptance' in section
    assert 'vault token revoke -self' in section
    assert 'echo "${VAULT_TOKEN}"' not in section

def test_bad_snapshot_checksum_fails_before_docker(tmp_path):
    run = tmp_path / "adr023-test-badsha"
    run.mkdir()
    snap = run / "vault-raft-test.snapshot"
    snap.write_bytes(b"synthetic")
    (run / "vault-raft-test.snapshot.sha256").write_text("0" * 64 + "  vault-raft-test.snapshot\n")
    (run / "vault-raft-test.snapshot.enc").write_bytes(b"enc")
    (run / "vault-raft-test.snapshot.enc.sha256").write_text(
        hashlib.sha256(b"enc").hexdigest() + "  vault-raft-test.snapshot.enc\n"
    )
    (run / "vault-raft-test.snapshot.meta.json").write_text("{}\n")
    (run / "restore-acceptance.pem").write_text("synthetic-public")
    (run / "restore-acceptance.key").write_text("synthetic-private")

    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    marker = tmp_path / "docker-called"
    docker = fakebin / "docker"
    docker.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 0\n')
    docker.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fakebin}:{env['PATH']}"
    proc = subprocess.run(["bash", str(SCRIPT), "--start", str(run)], env=env, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "checksum" in ((proc.stdout or "") + (proc.stderr or "")).lower()
    assert not marker.exists()


def test_teardown_requires_exact_restore_run_label():
    src = _src()
    section = src.split('cmd_teardown()', 1)[1].split('usage()', 1)[0]
    assert 'com.hexor.restore-run' in section
    assert 'docker rm -f' in section
    assert 'LABEL' in section or 'label' in section


def test_start_waits_for_running_uninitialized_vault_before_pass():
    src = _src()
    assert 'wait_for_uninitialized()' in src
    start = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    assert 'wait_for_uninitialized "${container}"' in start
    assert start.index('wait_for_uninitialized "${container}"') < start.index('RESTORE_START_PASS')


def test_restore_start_uses_supported_skip_chown_for_prepared_bind_mounts():
    src = _src()
    start = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    assert '-e SKIP_CHOWN=1' in start
    assert '-e SKIP_SETCAP=1' in start


def test_start_lets_pinned_entrypoint_load_restore_config_exactly_once():
    src = _src()
    start = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    assert '"${IMAGE}" server)' in start
    assert 'server -config=/vault/config/restore.hcl' not in start


def test_runtime_cleanup_releases_uid100_raft_permissions_without_root():
    src = _src()
    assert 'release_runtime_permissions()' in src
    helper = src.split('release_runtime_permissions()', 1)[1].split('wait_for_uninitialized()', 1)[0]
    for marker in ('--network none', '--read-only', '--cap-drop ALL', 'no-new-privileges', '--user 100:1000'):
        assert marker in helper
    assert '--user 0' not in helper
    assert 'find /cleanup -mindepth 1' in helper
    assert '-user 100' in helper
    assert '-exec chmod g+rwX' in helper
    start = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    teardown = src.split('cmd_teardown()', 1)[1].split('usage()', 1)[0]
    assert 'release_runtime_permissions "${runtime}"' in start
    assert 'release_runtime_permissions "${run}/runtime"' in teardown


def test_start_mounts_ephemeral_group_readable_runtime_snapshot_copy():
    src = _src()
    start = src.split('cmd_start()', 1)[1].split('cmd_status()', 1)[0]
    assert 'runtime_snap="${runtime}/input.snapshot"' in start
    assert 'install -m 0640 "${snap}" "${runtime_snap}"' in start
    assert '-v "${runtime_snap}:/vault/restore/input.snapshot:ro"' in start
    assert '-v "${snap}:/vault/restore/input.snapshot:ro"' not in start
